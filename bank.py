from copy import deepcopy
from pathlib import Path
from uuid import uuid4
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
        try:
            return self.accounts[number]
        except KeyError:
            raise AccountNotFoundError(f"Account {number} not found.") from None

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

    def export_statement(self, number, path=None):
        """Export to a new TXT file without replacing bank data or other files."""
        statement = self.get_account(number).statement()
        try:
            if path is None or path == "":
                directory = self.storage.directory / "statements"
                destination = directory / f"{number}_{uuid4().hex}.txt"
            else:
                destination = Path(path)
            destination = destination.absolute()
            snapshot = self.storage.path.resolve()

            # resolve() catches relative, .., case and symbolic-link aliases.
            if destination.resolve() == snapshot:
                raise ValidationError("Cannot export over the active bank data file.")
            # samefile() also recognizes hard links to an existing snapshot.
            if destination.exists() and snapshot.exists() and destination.samefile(snapshot):
                raise ValidationError("Cannot export over the active bank data file.")
            if destination.suffix.lower() != ".txt":
                raise ValidationError("Choose a TXT export filename ending in .txt.")

            if path is None or path == "":
                destination.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation refuses existing files, including symbolic links.
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(statement)
            return destination
        except FileExistsError:
            raise ValidationError(
                "Export destination already exists. Choose a new filename "
                "or leave the path blank for a unique export."
            ) from None
        except (OSError, ValueError, RuntimeError) as exc:
            raise StorageError(f"Cannot export statement: {exc}") from exc
