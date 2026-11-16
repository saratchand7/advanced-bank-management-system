from decimal import Decimal, InvalidOperation
import re
from exceptions import InvalidAmountError, ValidationError

def money(value, *, positive=False):
    if isinstance(value, (float, bool)):
        raise InvalidAmountError("Use a decimal string or Decimal, never float.")
    try:
        result = Decimal(value)
        if not result.is_finite() or abs(result) > Decimal("999999999999.99"):
            raise InvalidOperation
        rounded = result.quantize(Decimal("0.01"))
        if result != rounded or (positive and result <= 0):
            raise InvalidOperation
        return rounded
    except (InvalidOperation, ValueError, TypeError):
        raise InvalidAmountError("Enter a finite amount with at most two decimal places.") from None

def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value):
        raise ValidationError("IDs require 1-40 letters, digits, underscores or hyphens.")
    return value
