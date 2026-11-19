from abc import ABC, abstractmethod
from decimal import Decimal
from exceptions import ValidationError
from utils import identifier, money
from transaction import Transaction
from customer import Customer

class Account(ABC):
    # Abstraction: subclasses must implement interest and withdrawal policy.
    def __init__(self, account_number, customer, balance="0"):
        self._account_number = identifier(account_number)
        if not isinstance(customer, Customer):
            raise ValidationError("An account requires a Customer object.")
        self._customer = customer
        self._balance = money(balance)
        self._transactions = []

    # Encapsulation: balances and ledger have read-only public access.
    @property
    def account_number(self):
        return self._account_number

    @property
    def customer(self):
        return self._customer

    @property
    def balance(self):
        return self._balance

    @property
    def transactions(self):
        return tuple(self._transactions)

    def _record(self, kind, amount, counterparty="", period="", transaction_id=None):
        transaction = Transaction.create(
            self, kind, amount, counterparty, period, transaction_id
        )
        self._transactions.append(transaction)

    def deposit(self, amount):
        amount = money(amount, positive=True)
        new_balance = money(self.balance + amount)
        self._balance = new_balance
        self._record("DEPOSIT", amount)

    @abstractmethod
    def withdraw(self, amount):
        pass

    @abstractmethod
    def calculate_interest(self, months):
        pass

    def transfer(self, target, amount):
        if not isinstance(target, Account) or target is self or target.account_number == self.account_number:
            raise ValidationError("Choose a different valid destination account.")
        amount = money(amount, positive=True)
        money(target.balance + amount)
        old_balance, old_target = self.balance, target.balance
        old_len, target_len = len(self._transactions), len(target._transactions)
        try:
            self.withdraw(amount)  # Polymorphism chooses the account-specific policy.
            self._transactions.pop()
            target._balance += amount
            from uuid import uuid4
            transfer_id = uuid4().hex
            self._record("TRANSFER_OUT", amount, target.account_number, transaction_id=transfer_id)
            target._record("TRANSFER_IN", amount, self.account_number, transaction_id=transfer_id)
        except BaseException:
            self._balance, target._balance = old_balance, old_target
            del self._transactions[old_len:]
            del target._transactions[target_len:]
            raise

    def statement(self):
        lines = [f"Account statement: {self.account_number}", f"Customer: {self.customer.name}",
                 "Date | Transaction ID | Account | Type | Amount | Balance | Counterparty | Period"]
        for t in self.transactions:
            lines.append(" | ".join(str(v) for v in t.to_dict().values()))
        lines.append(f"Closing balance: {self.balance:.2f}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def validate_months(months):
        if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= 120:
            raise ValidationError("Duration requires 1-120 whole months.")
        return Decimal(months)
