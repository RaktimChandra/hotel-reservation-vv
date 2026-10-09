"""Payment input validation (FR-08)."""
import re
from datetime import date
from decimal import Decimal

from .errors import ValidationError

AMOUNT_MIN = Decimal("1")
AMOUNT_MAX = Decimal("500000")
_UPI_RE = re.compile(r"^[A-Za-z0-9._-]{2,256}@[A-Za-z]{2,64}$")


def luhn_valid(number: str) -> bool:
    """Luhn (mod-10) checksum used by every card network."""
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_card(number: str, exp_month: int, exp_year: int, cvv: str, today: date) -> str:
    digits = (number or "").replace(" ", "").replace("-", "")
    if not digits.isdigit() or len(digits) != 16:
        raise ValidationError("CARD_LENGTH", "Card number must have 16 digits")
    if not luhn_valid(digits):
        raise ValidationError("CARD_CHECKSUM", "Card number failed the checksum")
    if not (1 <= exp_month <= 12):
        raise ValidationError("CARD_EXP_MONTH", "Expiry month must be 1-12")
    if (exp_year, exp_month) < (today.year, today.month):
        raise ValidationError("CARD_EXPIRED", "Card has expired")
    if exp_year > today.year + 20:
        raise ValidationError("CARD_EXP_YEAR", "Expiry year is not plausible")
    if not (isinstance(cvv, str) and cvv.isdigit() and len(cvv) == 3):
        raise ValidationError("CARD_CVV", "CVV must be 3 digits")
    return "**** **** **** " + digits[-4:]


def validate_upi(vpa: str) -> str:
    if not isinstance(vpa, str) or not _UPI_RE.match(vpa.strip()):
        raise ValidationError("UPI_INVALID", "Enter a valid UPI ID, e.g. name@bank")
    return vpa.strip().lower()


def validate_amount(amount) -> Decimal:
    try:
        value = Decimal(str(amount))
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("AMOUNT_TYPE", "Amount must be numeric") from exc
    if value < AMOUNT_MIN:
        raise ValidationError("AMOUNT_MIN", f"Minimum payment is ₹{AMOUNT_MIN}")
    if value > AMOUNT_MAX:
        raise ValidationError("AMOUNT_MAX", f"Maximum single payment is ₹{AMOUNT_MAX}")
    return value
