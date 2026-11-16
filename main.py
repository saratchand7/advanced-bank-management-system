"""Run: python main.py. Application dependencies: Python standard library only."""
import argparse
from pathlib import Path
from bank import Bank
from exceptions import BankingError, ValidationError

MENU = """
1 Create Customer          2 Open Savings Account
3 Open Current Account     4 Deposit
5 Withdraw                 6 Transfer Funds
7 Check Balance            8 Calculate Interest
9 Credit Interest         10 View Account Statement
11 Export Statement       12 View Customer Details
13 List Accounts          14 Exit
"""

def ask(label): return input(label + ": ").strip()

def duration():
    try: return int(ask("Whole months (1-120)"))
    except ValueError: raise ValidationError("Enter a whole number of months.") from None

def run(bank):
    while True:
        try:
            print(MENU)
            choice = ask("Choice")
            if choice == "14":
                print("Goodbye.")
                return
            if choice == "1":
                c = bank.create_customer(ask("Customer ID"), ask("Name"), ask("Phone"), ask("Email"))
                print(f"Customer created: {c.customer_id}")
            elif choice in ("2", "3"):
                number, customer, opening = ask("Account number"), ask("Customer ID"), ask("Opening balance")
                options = ({"minimum_balance": ask("Minimum balance"), "annual_rate": ask("Annual rate (%)")}
                           if choice == "2" else {"overdraft_limit": ask("Overdraft limit")})
                a = bank.open_account("savings" if choice == "2" else "current", number, customer, opening, **options)
                print(f"Account opened: {a.account_number}")
            elif choice in ("4", "5"):
                number, amount = ask("Account number"), ask("Amount")
                (bank.deposit if choice == "4" else bank.withdraw)(number, amount)
                print(f"Success. Balance: {bank.get_account(number).balance:.2f}")
            elif choice == "6":
                bank.transfer(ask("Source account"), ask("Destination account"), ask("Amount"))
                print("Transfer completed.")
            elif choice == "7": print(f"Balance: {bank.get_account(ask('Account number')).balance:.2f}")
            elif choice in ("8", "9"):
                number, months = ask("Account number"), duration()
                amount = bank.calculate_interest(number, months)
                print(f"Calculated interest: {amount:.2f}")
                if choice == "9":
                    period = ask("Unique period label (for example 2026-Q1)")
                    if ask("Credit this amount? Type YES") == "YES":
                        bank.credit_interest(number, months, period, confirmed=True)
                        print("Interest credited.")
                    else: print("Credit cancelled.")
            elif choice == "10": print(bank.get_account(ask("Account number")).statement())
            elif choice == "11":
                bank.export_statement(ask("Account number"), ask("Output TXT path"))
                print("Statement exported.")
            elif choice == "12":
                customer_id = ask("Customer ID")
                if customer_id not in bank.customers: raise ValidationError("Customer not found.")
                c = bank.customers[customer_id]
                print(f"ID: {c.customer_id}\nName: {c.name}\nPhone: {c.phone}\nEmail: {c.email}")
            elif choice == "13":
                if not bank.accounts: print("No accounts.")
                for a in bank.accounts.values():
                    print(f"{a.account_number}  {type(a).__name__}  {a.customer.name}  {a.balance:.2f}")
            else: print("Choose a menu option from 1 to 14.")
        except BankingError as exc: print(f"Error: {exc}")
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended safely.")
            return

def main():
    parser = argparse.ArgumentParser(description="Advanced Bank Management System Using OOP")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--demo-data", action="store_true", help="Create explicit example records in an empty data directory and exit")
    args = parser.parse_args()
    try:
        bank = Bank(args.data_dir)
        if args.demo_data:
            if bank.customers or bank.accounts:
                raise ValidationError("Demo data requires an empty data directory.")
            bank.create_customer("DEMO1", "Demo Customer", "9000000000", "demo@example.com")
            bank.open_account("savings", "S100", "DEMO1", "1000", minimum_balance="100", annual_rate="4")
            bank.open_account("current", "C100", "DEMO1", "500", overdraft_limit="1000")
            print("Demo accounts created: S100 and C100.")
        else:
            run(bank)
    except BankingError as exc:
        print(f"Startup error: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError): print("\nSession ended safely.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
