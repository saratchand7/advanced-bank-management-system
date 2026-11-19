from decimal import Decimal, ROUND_HALF_UP
from account import Account
from utils import money
from exceptions import ValidationError, InsufficientFundsError

class SavingsAccount(Account):
    # Inheritance reuses the account ledger and deposit behavior.
    def __init__(self, account_number, customer, balance="0", minimum_balance="0", annual_rate="4"):
        super().__init__(account_number, customer, balance)
        self.minimum_balance = money(minimum_balance)
        self.annual_rate = money(annual_rate)
        if self.minimum_balance < 0 or self.balance < self.minimum_balance or not 0 <= self.annual_rate <= 100:
            raise ValidationError("Invalid savings balance, minimum or annual rate (0-100%).")

    # Method overriding supplies the savings withdrawal rule.
    def withdraw(self, amount):
        amount = money(amount, positive=True)
        if self.balance - amount < self.minimum_balance:
            raise InsufficientFundsError("Savings minimum balance would be breached.")
        self._balance -= amount
        self._record("WITHDRAWAL", amount)

    def calculate_interest(self, months):
        duration = self.validate_months(months)
        interest = self.balance * self.annual_rate * duration / Decimal("1200")
        return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
