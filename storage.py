"""One UTF-8 JSON snapshot in bank.txt is the authoritative state."""
import json
import os
import tempfile
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from customer import Customer
from savings_account import SavingsAccount
from current_account import CurrentAccount
from transaction import Transaction
from utils import money, identifier
from exceptions import BankingError, StorageError

class Storage:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "bank.txt"

    def save(self, customers, accounts):
        records = []
        for a in accounts.values():
            record = {"kind": "savings" if isinstance(a, SavingsAccount) else "current",
                      "account_number": a.account_number, "customer_id": a.customer.customer_id,
                      "balance": str(a.balance), "transactions": [asdict(t) for t in a.transactions]}
            if isinstance(a, SavingsAccount):
                record.update(minimum_balance=str(a.minimum_balance), annual_rate=str(a.annual_rate))
            else:
                record["overdraft_limit"] = str(a.overdraft_limit)
            records.append(record)
        state = {"version": 1, "customers": [asdict(c) for c in customers.values()], "accounts": records}
        temp_path = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             suffix=".tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                json.dump(state, handle, indent=2, ensure_ascii=False, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        except OSError as exc:
            raise StorageError(f"Save failed: {exc}") from exc
        finally:
            if temp_path is not None and temp_path.exists():
                try: temp_path.unlink()
                except OSError: pass

    def load(self):
        try:
            if not self.path.exists(): return {}, {}
            def unique_keys(pairs):
                result = {}
                for key, value in pairs:
                    if key in result: raise ValueError("Duplicate JSON key")
                    result[key] = value
                return result
            state = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
            if set(state) != {"version", "customers", "accounts"} or type(state["version"]) is not int or state["version"] != 1:
                raise ValueError("Unsupported snapshot")
            if not isinstance(state["customers"], list) or not isinstance(state["accounts"], list):
                raise ValueError("Records must be arrays")
            customers, accounts, ids = {}, {}, {}
            for row in state["customers"]:
                customer = Customer(**row)
                if customer.customer_id in customers: raise ValueError("Duplicate customer")
                customers[customer.customer_id] = customer
            for raw in state["accounts"]:
                row = dict(raw)
                kind, number = row.pop("kind"), row.pop("account_number")
                owner, transactions = customers[row.pop("customer_id")], row.pop("transactions")
                if kind not in ("savings", "current") or number in accounts:
                    raise ValueError("Unknown type or duplicate account")
                cls = SavingsAccount if kind == "savings" else CurrentAccount
                account = cls(number, owner, **row)
                running, periods = Decimal("0.00"), set()
                if not transactions: raise ValueError("Missing opening ledger")
                for index, entry in enumerate(transactions):
                    t = Transaction(**entry)
                    identifier(t.transaction_id)
                    stamp = datetime.fromisoformat(t.date)
                    if stamp.tzinfo is None or t.account_number != number: raise ValueError("Invalid ledger identity")
                    if not isinstance(t.counterparty, str) or not isinstance(t.period, str): raise ValueError("Invalid ledger fields")
                    if (index == 0) != (t.type == "OPENING"): raise ValueError("Invalid opening entry")
                    amount = money(t.amount, positive=t.type != "OPENING")
                    if amount < 0: raise ValueError("Negative opening")
                    if t.type in ("WITHDRAWAL", "TRANSFER_OUT"): running -= amount
                    elif t.type in ("OPENING", "DEPOSIT", "TRANSFER_IN", "INTEREST"): running += amount
                    else: raise ValueError("Invalid transaction type")
                    if running != money(t.balance): raise ValueError("Ledger balance mismatch")
                    floor = account.minimum_balance if kind == "savings" else -account.overdraft_limit
                    if running < floor: raise ValueError("Historical limit breach")
                    if t.type == "INTEREST":
                        identifier(t.period)
                        if kind != "savings" or t.period in periods: raise ValueError("Invalid interest entry")
                        periods.add(t.period)
                    elif t.period: raise ValueError("Unexpected period")
                    if t.type.startswith("TRANSFER_"):
                        identifier(t.counterparty)
                        if t.counterparty == number: raise ValueError("Self transfer")
                    elif t.counterparty: raise ValueError("Unexpected counterparty")
                    ids.setdefault(t.transaction_id, []).append(t)
                    account._transactions.append(t)
                if running != account.balance: raise ValueError("Closing balance mismatch")
                accounts[number] = account
            for group in ids.values():
                if group[0].type.startswith("TRANSFER_"):
                    if len(group) != 2: raise ValueError("Incomplete transfer")
                    out = next(t for t in group if t.type == "TRANSFER_OUT")
                    incoming = next(t for t in group if t.type == "TRANSFER_IN")
                    if out.amount != incoming.amount or out.counterparty != incoming.account_number or incoming.counterparty != out.account_number:
                        raise ValueError("Transfer mismatch")
                elif len(group) != 1: raise ValueError("Duplicate transaction ID")
            return customers, accounts
        except (OSError, ValueError, TypeError, KeyError, AttributeError, StopIteration, BankingError) as exc:
            raise StorageError(f"Cannot load {self.path}. Original file preserved. {exc}") from exc
