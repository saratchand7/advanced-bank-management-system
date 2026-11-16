from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
from customer import Customer
from savings_account import SavingsAccount
from current_account import CurrentAccount
from exceptions import AccountNotFoundError, DuplicateAccountError, ValidationError, StorageError
from utils import identifier, money

class Bank:
    def __init__(self, data_dir="data"):
        from storage import Storage
        self.storage = Storage(data_dir)
        self.customers, self.accounts = self.storage.load()

    def _commit(self, operation):
        # Snapshot rollback preserves live object identities after save failure.
        customers, accounts = dict(self.customers), dict(self.accounts)
        states = {key: deepcopy(value.__dict__) for key, value in accounts.items()}
        try:
            result = operation()
            self.storage.save(self.customers, self.accounts)
            return result
        except BaseException:
            self.customers, self.accounts = customers, accounts
            for key, state in states.items():
                accounts[key].__dict__.clear()
                accounts[key].__dict__.update(state)
            raise

    def create_customer(self, customer_id, name, phone, email):
        customer = Customer(customer_id, name, phone, email)
        if customer_id in self.customers:
            raise ValidationError("Customer ID already exists.")
        def operation():
            self.customers[customer_id] = customer
            return customer
        return self._commit(operation)

    def open_account(self, kind, account_number, customer_id, balance="0", **options):
        if account_number in self.accounts:
            raise DuplicateAccountError("Account number already exists.")
        if customer_id not in self.customers:
            raise ValidationError("Customer ID does not exist.")
        if kind not in ("savings", "current"):
            raise ValidationError("Choose savings or current.")
        if money(balance) < 0:
            raise ValidationError("Opening balance cannot be negative.")
        cls = SavingsAccount if kind == "savings" else CurrentAccount
        account = cls(account_number, self.customers[customer_id], balance, **options)
        account._record("OPENING", account.balance)
        def operation():
            self.accounts[account_number] = account
            return account
        return self._commit(operation)

    def get_account(self, number):
        try: return self.accounts[number]
        except KeyError: raise AccountNotFoundError(f"Account {number} not found.") from None

    def deposit(self, number, amount):
        return self._commit(lambda: self.get_account(number).deposit(amount))

    def withdraw(self, number, amount):
        return self._commit(lambda: self.get_account(number).withdraw(amount))

    def transfer(self, source, target, amount):
        sender, receiver = self.get_account(source), self.get_account(target)
        return self._commit(lambda: sender.transfer(receiver, amount))

    def calculate_interest(self, number, months):
        return self.get_account(number).calculate_interest(months)

    def credit_interest(self, number, months, period, confirmed=False):
        account = self.get_account(number)
        identifier(period)
        amount = account.calculate_interest(months)
        if not confirmed:
            raise ValidationError("Explicit confirmation is required to credit interest.")
        if any(t.period == period for t in account.transactions if t.type == "INTEREST"):
            raise ValidationError("Interest already credited for this period.")
        money(amount, positive=True)
        def operation():
            account._balance = money(account.balance + amount)
            account._record("INTEREST", amount, period=period)
            return amount
        return self._commit(operation)

    def export_statement(self, number, path):
        try:
            Path(path).write_text(self.get_account(number).statement(), encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Cannot export statement: {exc}") from exc
