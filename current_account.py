from decimal import Decimal
from account import Account
from utils import money
from exceptions import ValidationError, InsufficientFundsError

class CurrentAccount(Account):
    def __init__(self, account_number, customer, balance="0", overdraft_limit="1000"):
        super().__init__(account_number, customer, balance)
        self.overdraft_limit = money(overdraft_limit)
        if self.overdraft_limit < 0 or self.balance < -self.overdraft_limit:
            raise ValidationError("Invalid overdraft limit or opening balance.")

    def withdraw(self, amount):
        amount = money(amount, positive=True)
        if self.balance - amount < -self.overdraft_limit:
            raise InsufficientFundsError("Current account overdraft limit exceeded.")
        self._balance -= amount
        self._record("WITHDRAWAL", amount)

    def calculate_interest(self, months):
        self.validate_months(months)
        return Decimal("0.00")
