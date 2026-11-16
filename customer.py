from dataclasses import dataclass
import re
from exceptions import ValidationError
from utils import identifier

@dataclass(frozen=True)
class Customer:
    # Constructor validation and immutable fields protect customer identity.
    customer_id: str
    name: str
    phone: str
    email: str

    def __post_init__(self):
        identifier(self.customer_id)
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 100 or any(c in self.name for c in "\n\r\t"):
            raise ValidationError("Enter a name of 1-100 characters.")
        if not isinstance(self.phone, str) or not re.fullmatch(r"\+?[0-9]{7,15}", self.phone):
            raise ValidationError("Phone requires 7-15 digits with optional leading +.")
        if not isinstance(self.email, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email):
            raise ValidationError("Enter a valid email address.")
