import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from bank import Bank
from account import Account
from customer import Customer
from savings_account import SavingsAccount
from current_account import CurrentAccount
from exceptions import *
from utils import money

class BankingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bank = Bank(self.temp.name)
        self.customer = self.bank.create_customer("C1", "Ravi Kumar", "9876543210", "ravi@example.com")
        self.s = self.bank.open_account("savings", "S1", "C1", "1000", minimum_balance="100", annual_rate="6")
        self.c = self.bank.open_account("current", "A1", "C1", "200", overdraft_limit="500")

    def test_customer_and_validation(self):
        self.assertEqual(self.customer.name, "Ravi Kumar")
        for args in [("", "Name", "9876543210", "a@b.com"), ("X", "", "9876543210", "a@b.com"),
                     ("X", "Name", "abc", "a@b.com"), ("X", "Name", "9876543210", "bad")]:
            with self.subTest(args=args), self.assertRaises(ValidationError): Customer(*args)

    def test_abstraction(self):
        with self.assertRaises(TypeError): Account("X", self.customer)

    def test_polymorphism(self):
        self.assertIsInstance(self.s, Account)
        self.assertIsInstance(self.c, Account)
        self.assertEqual([a.calculate_interest(12) for a in (self.s, self.c)], [Decimal("60"), Decimal("0")])

    def test_balance_read_only(self):
        with self.assertRaises(AttributeError): self.s.balance = Decimal("9999")
        self.assertIsInstance(self.s.transactions, tuple)

    def test_deposit_withdraw(self):
        self.bank.deposit("S1", "50.25")
        self.bank.withdraw("S1", "20.10")
        self.assertEqual(self.s.balance, Decimal("1030.15"))
        self.assertEqual(self.s.transactions[-1].type, "WITHDRAWAL")

    def test_invalid_money(self):
        for value in ["0", "-1", "0.001", "NaN", "Infinity", "-Infinity", "bad", 1.2, True, None, "1e999999"]:
            with self.subTest(value=value), self.assertRaises(InvalidAmountError): self.bank.deposit("S1", value)
        self.assertEqual(self.s.balance, Decimal("1000"))

    def test_savings_minimum(self):
        self.bank.withdraw("S1", "900")
        with self.assertRaises(InsufficientFundsError): self.bank.withdraw("S1", "0.01")
        self.assertEqual(self.s.balance, Decimal("100"))

    def test_overdraft(self):
        self.bank.withdraw("A1", "700")
        self.assertEqual(self.c.balance, Decimal("-500"))
        with self.assertRaises(InsufficientFundsError): self.bank.withdraw("A1", "0.01")

    def test_invalid_account_configuration(self):
        for kind, opts in [("savings", {"minimum_balance": "1100"}), ("savings", {"annual_rate": "101"}),
                           ("current", {"overdraft_limit": "-1"})]:
            with self.subTest(kind=kind, opts=opts), self.assertRaises(ValidationError):
                self.bank.open_account(kind, "NEW", "C1", "1000", **opts)
        with self.assertRaises(ValidationError): self.bank.open_account("other", "X", "C1")
        with self.assertRaises(ValidationError): self.bank.open_account("current", "X", "missing")
        with self.assertRaises(ValidationError): self.bank.open_account("current", "X", "C1", "-1")

    def test_transfer(self):
        self.bank.transfer("S1", "A1", "123.45")
        self.assertEqual(self.s.balance, Decimal("876.55"))
        self.assertEqual(self.c.balance, Decimal("323.45"))
        a, b = self.s.transactions[-1], self.c.transactions[-1]
        self.assertEqual(a.transaction_id, b.transaction_id)
        self.assertEqual((a.counterparty, b.counterparty), ("A1", "S1"))
        self.assertEqual(Bank(self.temp.name).get_account("A1").balance, self.c.balance)

    def test_failed_transfer(self):
        before = self.bank.storage.path.read_bytes()
        for source, target, amount, error in [("S1", "S1", "1", ValidationError), ("S1", "missing", "1", AccountNotFoundError),
                                             ("S1", "A1", "901", InsufficientFundsError), ("S1", "A1", "-1", InvalidAmountError)]:
            with self.subTest(target=target, amount=amount), self.assertRaises(error): self.bank.transfer(source, target, amount)
        self.assertEqual(before, self.bank.storage.path.read_bytes())

    def test_interest_confirmation_and_duplicates(self):
        self.assertEqual(self.bank.calculate_interest("S1", 6), Decimal("30"))
        self.assertEqual(self.s.balance, Decimal("1000"))
        with self.assertRaises(ValidationError): self.bank.credit_interest("S1", 6, "2026-H1")
        self.bank.credit_interest("S1", 6, "2026-H1", confirmed=True)
        restarted = Bank(self.temp.name)
        with self.assertRaises(ValidationError): restarted.credit_interest("S1", 6, "2026-H1", confirmed=True)
        self.assertEqual(restarted.get_account("S1").balance, Decimal("1030"))
        with self.assertRaises(InvalidAmountError): self.bank.credit_interest("A1", 6, "2026-H1", confirmed=True)

    def test_interest_rounding_and_duration(self):
        self.s.annual_rate = Decimal("4.01")
        self.assertEqual(self.s.calculate_interest(1), Decimal("3.34"))
        for value in [0, -1, 121, True, "12", 1.5]:
            with self.subTest(value=value), self.assertRaises(ValidationError): self.s.calculate_interest(value)

    def test_duplicate_ids(self):
        with self.assertRaises(DuplicateAccountError): self.bank.open_account("current", "S1", "C1")
        with self.assertRaises(ValidationError): self.bank.create_customer("C1", "Other", "9876543210", "x@y.com")

    def test_statement_export(self):
        self.bank.transfer("S1", "A1", "10")
        output = Path(self.temp.name) / "statement.txt"
        self.bank.export_statement("S1", output)
        text = output.read_text(encoding="utf-8")
        for part in ["Ravi Kumar", "TRANSFER_OUT", "990.00", "A1", "Transaction ID"]: self.assertIn(part, text)
        with self.assertRaises(StorageError): self.bank.export_statement("S1", output / "bad.txt")

    def test_restart_preserves_state(self):
        self.bank.withdraw("A1", "300")
        loaded = Bank(self.temp.name)
        self.assertEqual(loaded.customers, self.bank.customers)
        for number in self.bank.accounts:
            self.assertEqual(loaded.get_account(number).balance, self.bank.get_account(number).balance)
            self.assertEqual(loaded.get_account(number).transactions, self.bank.get_account(number).transactions)

    def test_save_failure_rolls_back_live_objects(self):
        original = self.bank.storage.path.read_bytes()
        with patch("storage.os.replace", side_effect=OSError("disk unavailable")):
            with self.assertRaises(StorageError): self.bank.transfer("S1", "A1", "100")
            with self.assertRaises(StorageError): self.bank.deposit("S1", "100")
            with self.assertRaises(StorageError): self.bank.create_customer("C2", "Other", "9876543210", "x@y.com")
        self.assertIs(self.s, self.bank.get_account("S1"))
        self.assertEqual((self.s.balance, self.c.balance), (Decimal("1000"), Decimal("200")))
        self.assertNotIn("C2", self.bank.customers)
        self.assertEqual(original, self.bank.storage.path.read_bytes())
        self.assertEqual(list(Path(self.temp.name).glob("*.tmp")), [])

    def test_corruption_preserves_original(self):
        for text in ["{bad", '{"version": 1, "version": 1}', '{"version": 99, "customers": [], "accounts": []}']:
            self.bank.storage.path.write_text(text, encoding="utf-8")
            with self.assertRaises(StorageError): Bank(self.temp.name)
            self.assertEqual(self.bank.storage.path.read_text(encoding="utf-8"), text)

    def test_ledger_tampering(self):
        original = json.loads(self.bank.storage.path.read_text(encoding="utf-8"))
        from copy import deepcopy
        for change in (lambda d: d["accounts"][0].update(balance="9999"),
                       lambda d: d["accounts"].append(deepcopy(d["accounts"][0])),
                       lambda d: d["accounts"][0]["transactions"][0].update(type="UNKNOWN"),
                       lambda d: d["accounts"][0]["transactions"][0].update(amount="NaN")):
            state = deepcopy(original)
            change(state)
            self.bank.storage.path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaises(StorageError): Bank(self.temp.name)

    def test_partial_transfer_rejected(self):
        self.bank.transfer("S1", "A1", "10")
        state = json.loads(self.bank.storage.path.read_text(encoding="utf-8"))
        state["accounts"][1]["transactions"].pop()
        state["accounts"][1]["balance"] = "200.00"
        self.bank.storage.path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(StorageError): Bank(self.temp.name)

    def test_cli_invalid_input_and_eof(self):
        result = subprocess.run([sys.executable, "main.py", "--data-dir", self.temp.name], input="bad\n7\nmissing\n", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Choose a menu option", result.stdout)
        self.assertIn("not found", result.stdout)
        self.assertIn("Session ended safely", result.stdout)

if __name__ == "__main__": unittest.main()
