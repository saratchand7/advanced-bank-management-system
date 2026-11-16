"""Domain errors let the CLI handle expected banking failures."""
class BankingError(Exception): pass
class InvalidAmountError(BankingError): pass
class InsufficientFundsError(BankingError): pass
class AccountNotFoundError(BankingError): pass
class DuplicateAccountError(BankingError): pass
class ValidationError(BankingError): pass
class StorageError(BankingError): pass
