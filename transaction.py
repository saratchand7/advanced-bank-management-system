from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from uuid import uuid4

@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    date: str
    account_number: str
    type: str
    amount: str
    balance: str
    counterparty: str = ""
    period: str = ""

    @classmethod
    def create(cls, account, kind, amount, counterparty="", period="", transaction_id=None):
        return cls(transaction_id or uuid4().hex, datetime.now(timezone.utc).isoformat(),
                   account.account_number, kind, str(amount), str(account.balance), counterparty, period)

    def to_dict(self):
        return asdict(self)
