"""Input validation rules (FR-01, FR-02, FR-03, FR-04, FR-05).

Every boundary below is a named constant so test designers can derive
Boundary Value Analysis (BVA) and Equivalence Class Partitioning (ECP)
cases directly from it.
"""
import re
from datetime import date, timedelta

from .errors import ValidationError
from .rooms import EXTRA_BED_CAPACITY, get_room_type

# ---- FR-01 Guest profile -------------------------------------------------
NAME_MIN, NAME_MAX = 2, 50
AGE_MIN, AGE_MAX = 18, 120
_NAME_RE = re.compile(r"^[A-Za-z]+(?:(?:\. |[ .'-])[A-Za-z]+)*$")  # DEF-001: allow "R. Chandra"
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
_PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian mobile: 10 digits, starts 6-9

# ---- FR-02 Credentials ---------------------------------------------------
PASSWORD_MIN, PASSWORD_MAX = 8, 20
_SPECIALS = set("!@#$%^&*()-_=+[]{};:,.<>/?")

# ---- FR-03 Search / stay -------------------------------------------------
NIGHTS_MIN, NIGHTS_MAX = 1, 30
ADVANCE_DAYS_MAX = 365
GUESTS_MIN, GUESTS_MAX = 1, 10

# ---- FR-05 Booking ------------------------------------------------------
ROOMS_MIN, ROOMS_MAX = 1, 5


def validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValidationError("NAME_TYPE", "Name must be text")
    cleaned = " ".join(name.split())
    if len(cleaned) < NAME_MIN:
        raise ValidationError("NAME_TOO_SHORT", f"Name must be at least {NAME_MIN} characters")
    if len(cleaned) > NAME_MAX:
        raise ValidationError("NAME_TOO_LONG", f"Name must be at most {NAME_MAX} characters")
    if not _NAME_RE.match(cleaned):
        raise ValidationError("NAME_CHARS", "Name may contain letters, spaces, . ' - only")
    return cleaned


def validate_email(email: str) -> str:
    if not isinstance(email, str) or len(email) > 254 or not _EMAIL_RE.match(email.strip()):
        raise ValidationError("EMAIL_INVALID", "Enter a valid email address")
    return email.strip().lower()


def validate_phone(phone: str) -> str:
    if not isinstance(phone, str):
        raise ValidationError("PHONE_INVALID", "Phone must be text")
    digits = phone.strip()
    if digits.startswith("+91"):
        digits = digits[3:]
    if not _PHONE_RE.match(digits):
        raise ValidationError("PHONE_INVALID", "Phone must be a 10-digit Indian mobile number")
    return digits


def validate_age(age: int) -> int:
    if isinstance(age, bool) or not isinstance(age, int):
        raise ValidationError("AGE_TYPE", "Age must be a whole number")
    if age < AGE_MIN:
        raise ValidationError("AGE_UNDER", f"Primary guest must be at least {AGE_MIN}")
    if age > AGE_MAX:
        raise ValidationError("AGE_OVER", f"Age must be at most {AGE_MAX}")
    return age


def password_strength(password: str) -> list[str]:
    """Return the list of violated password rules (empty list = strong)."""
    problems = []
    if not isinstance(password, str):
        return ["PWD_TYPE"]
    if len(password) < PASSWORD_MIN:
        problems.append("PWD_TOO_SHORT")
    if len(password) > PASSWORD_MAX:
        problems.append("PWD_TOO_LONG")
    if not any(c.isupper() for c in password):
        problems.append("PWD_NO_UPPER")
    if not any(c.islower() for c in password):
        problems.append("PWD_NO_LOWER")
    if not any(c.isdigit() for c in password):
        problems.append("PWD_NO_DIGIT")
    if not any(c in _SPECIALS for c in password):
        problems.append("PWD_NO_SPECIAL")
    if any(c.isspace() for c in password):
        problems.append("PWD_WHITESPACE")
    return problems


def validate_password(password: str) -> str:
    problems = password_strength(password)
    if problems:
        raise ValidationError(problems[0], "Password does not meet the policy: " + ", ".join(problems))
    return password


def validate_stay(check_in: date, check_out: date, today: date) -> int:
    """Validate a stay window and return the number of nights."""
    if not isinstance(check_in, date) or not isinstance(check_out, date):
        raise ValidationError("DATE_TYPE", "Dates must be calendar dates")
    if check_in < today:
        raise ValidationError("CHECKIN_PAST", "Check-in cannot be in the past")
    if check_in > today + timedelta(days=ADVANCE_DAYS_MAX):
        raise ValidationError("CHECKIN_TOO_FAR", f"Bookings open only {ADVANCE_DAYS_MAX} days ahead")
    nights = (check_out - check_in).days
    if nights < NIGHTS_MIN:
        raise ValidationError("STAY_TOO_SHORT", "Check-out must be after check-in")
    if nights > NIGHTS_MAX:
        raise ValidationError("STAY_TOO_LONG", f"Maximum stay is {NIGHTS_MAX} nights")
    return nights


def validate_occupancy(room_type: str, adults: int, children: int, extra_bed: bool = False) -> int:
    """Validate occupants for ONE room and return the head-count."""
    rt = get_room_type(room_type)
    for value, label in ((adults, "Adults"), (children, "Children")):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("OCCUPANCY_TYPE", f"{label} must be a whole number")
    if adults < 1:
        raise ValidationError("ADULTS_MIN", "At least one adult is required per room")
    if children < 0:
        raise ValidationError("CHILDREN_NEGATIVE", "Children cannot be negative")
    if extra_bed and not rt.extra_bed_allowed:
        raise ValidationError("EXTRA_BED_NOT_ALLOWED", f"{rt.name} does not allow an extra bed")
    limit = rt.capacity + (EXTRA_BED_CAPACITY if extra_bed else 0)
    total = adults + children
    if total > limit:
        raise ValidationError("OCCUPANCY_EXCEEDED", f"{rt.name} holds at most {limit} guests")
    return total


def validate_guest_count(total_guests: int) -> int:
    if isinstance(total_guests, bool) or not isinstance(total_guests, int):
        raise ValidationError("GUESTS_TYPE", "Guest count must be a whole number")
    if total_guests < GUESTS_MIN:
        raise ValidationError("GUESTS_MIN", f"At least {GUESTS_MIN} guest is required")
    if total_guests > GUESTS_MAX:
        raise ValidationError("GUESTS_MAX", f"At most {GUESTS_MAX} guests per booking")
    return total_guests


def validate_room_count(rooms: int) -> int:
    if isinstance(rooms, bool) or not isinstance(rooms, int):
        raise ValidationError("ROOMS_TYPE", "Room count must be a whole number")
    if rooms < ROOMS_MIN:
        raise ValidationError("ROOMS_MIN", f"Book at least {ROOMS_MIN} room")
    if rooms > ROOMS_MAX:
        raise ValidationError("ROOMS_MAX", f"At most {ROOMS_MAX} rooms per booking")
    return rooms
