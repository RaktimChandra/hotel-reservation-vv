"""Black-box: Equivalence Class Partitioning (ECP).

Each input domain is split into valid (V) and invalid (I) classes; one
representative value per class is enough because the system is assumed to
treat every member of a class the same way. Weak-normal ECP for valid
classes, one-invalid-at-a-time for invalid classes.
"""
from datetime import date

import pytest

from app.domain import payment as pay
from app.domain import pricing as pr
from app.domain import validation as v
from app.domain.errors import ValidationError
from app.domain.rooms import get_room_type
from tests.tclib import cases

TODAY = date(2026, 10, 8)
OK = "ACCEPT"


def run(fn, *args):
    try:
        fn(*args)
        return OK
    except ValidationError as e:
        return e.code


def rows(prefix, start, spec):
    return [{"id": f"{prefix}-{i:03d}", "title": f"[{cls}] {title}", "inputs": {"value": val},
             "expected": exp, "eq_class": cls} for i, (cls, title, val, exp) in enumerate(spec, start)]


EMAIL = rows("TC-REG-ECP", 1, [
    ("V1", "Simple address", "raktim@srmist.edu.in", OK),
    ("V2", "Plus-tag and dots in local part", "rc.8823+hotel@gmail.com", OK),
    ("V3", "Upper-case letters", "Ananya.Rao@Example.COM", OK),
    ("I1", "Missing @", "raktim.srmist.edu.in", "EMAIL_INVALID"),
    ("I2", "Missing local part", "@srmist.edu.in", "EMAIL_INVALID"),
    ("I3", "Missing domain", "raktim@", "EMAIL_INVALID"),
    ("I4", "Missing TLD", "raktim@srmist", "EMAIL_INVALID"),
    ("I5", "One-letter TLD", "raktim@srmist.c", "EMAIL_INVALID"),
    ("I6", "Embedded space", "rak tim@srmist.edu.in", "EMAIL_INVALID"),
    ("I7", "Two @ signs", "rak@tim@srmist.edu.in", "EMAIL_INVALID"),
    ("I8", "Empty string", "", "EMAIL_INVALID"),
    ("I9", "Not a string (None)", None, "EMAIL_INVALID"),
])

PHONE = rows("TC-REG-ECP", 13, [
    ("V1", "10 digits starting with 9", "9832288101", OK),
    ("V2", "10 digits starting with 6", "6000000000", OK),
    ("V3", "With +91 country code", "+919832288101", OK),
    ("I1", "Starts with 5 (not a mobile series)", "5832288101", "PHONE_INVALID"),
    ("I2", "9 digits", "983228810", "PHONE_INVALID"),
    ("I3", "11 digits", "98322881011", "PHONE_INVALID"),
    ("I4", "Contains letters", "98322ABCDE", "PHONE_INVALID"),
    ("I5", "Contains spaces inside", "98322 88101", "PHONE_INVALID"),
    ("I6", "Empty string", "", "PHONE_INVALID"),
])

NAME_CHARS = rows("TC-REG-ECP", 22, [
    ("V1", "Letters and single space", "Meera Iyer", OK),
    ("V2", "Apostrophe", "D'Souza Maria", OK),
    ("V3", "Hyphenated surname", "Kabir Mehta-Roy", OK),
    ("V4", "Initial with dot", "R. Chandra", OK),
    ("I1", "Digits", "Raktim2", "NAME_CHARS"),
    ("I2", "Symbol @", "Raktim@Chandra", "NAME_CHARS"),
    ("I3", "Emoji", "Ananya 🙂", "NAME_CHARS"),
    ("I4", "Only spaces", "     ", "NAME_TOO_SHORT"),
    ("I5", "HTML/script payload", "<script>alert(1)</script>", "NAME_CHARS"),
])

PASSWORD = rows("TC-AUTH-ECP", 1, [
    ("V1", "Upper+lower+digit+special, 10 chars", "Hotel@2026", OK),
    ("I1", "No upper-case letter", "hotel@2026", "PWD_NO_UPPER"),
    ("I2", "No lower-case letter", "HOTEL@2026", "PWD_NO_LOWER"),
    ("I3", "No digit", "Hotel@Stay", "PWD_NO_DIGIT"),
    ("I4", "No special character", "Hotel2026x", "PWD_NO_SPECIAL"),
    ("I5", "Contains whitespace", "Hotel @2026", "PWD_WHITESPACE"),
    ("I6", "Not a string", 12345678, "PWD_TYPE"),
])

ROOM = rows("TC-ROOM-ECP", 1, [
    ("V1", "STANDARD", "STANDARD", OK), ("V2", "DELUXE", "DELUXE", OK), ("V3", "FAMILY", "FAMILY", OK),
    ("V4", "SUITE", "SUITE", OK), ("V5", "Lower-case code", "suite", OK),
    ("I1", "Unknown type", "PENTHOUSE", "ROOM_TYPE_INVALID"), ("I2", "Empty", "", "ROOM_TYPE_INVALID"),
    ("I3", "None", None, "ROOM_TYPE_INVALID"), ("I4", "Integer", 101, "ROOM_TYPE_INVALID"),
])

TIER = rows("TC-PRC-ECP", 1, [
    ("V1", "NONE → 0 %", "NONE", "0"), ("V2", "SILVER → 5 %", "SILVER", "0.05"),
    ("V3", "GOLD → 10 %", "GOLD", "0.10"), ("V4", "PLATINUM → 15 %", "PLATINUM", "0.15"),
    ("V5", "Lower-case gold", "gold", "0.10"), ("V6", "Missing tier treated as NONE", None, "0"),
    ("I1", "Unknown tier", "DIAMOND", "LOYALTY_INVALID"),
])

PROMO = rows("TC-PRC-ECP", 8, [
    ("V1", "No promo code", None, "0"), ("V2", "WELCOME10 percentage (capped)", "WELCOME10", "1000"),
    ("V3", "FLAT500 fixed amount", "FLAT500", "500"), ("V4", "Lower-case code with spaces", " welcome10 ", "1000"),
    ("I1", "Unknown promo", "FREE100", "PROMO_INVALID"),
])

UPI = rows("TC-PAY-ECP", 1, [
    ("V1", "name@bank", "raktim@okaxis", OK), ("V2", "Dots, dash, underscore", "r.c-88_23@ybl", OK),
    ("I1", "No @", "raktimokaxis", "UPI_INVALID"), ("I2", "Empty handle", "@okaxis", "UPI_INVALID"),
    ("I3", "Empty bank", "raktim@", "UPI_INVALID"), ("I4", "Digit in bank", "raktim@bank1", "UPI_INVALID"),
    ("I5", "Handle too short", "r@okaxis", "UPI_INVALID"),
])

CARD = rows("TC-PAY-ECP", 8, [
    ("V1", "Visa test number", "4111111111111111", OK),
    ("V2", "MasterCard test number", "5555555555554444", OK),
    ("V3", "Grouped with spaces", "4111 1111 1111 1111", OK),
    ("V4", "Grouped with dashes", "5555-5555-5555-4444", OK),
    ("I1", "Fails Luhn checksum", "4111111111111112", "CARD_CHECKSUM"),
    ("I2", "15 digits", "411111111111111", "CARD_LENGTH"),
    ("I3", "17 digits", "41111111111111111", "CARD_LENGTH"),
    ("I4", "Contains letters", "4111abcd11111111", "CARD_LENGTH"),
    ("I5", "Empty", "", "CARD_LENGTH"),
])

CVV = rows("TC-PAY-ECP", 17, [
    ("V1", "3 digits", "123", OK), ("I1", "2 digits", "12", "CARD_CVV"), ("I2", "4 digits", "1234", "CARD_CVV"),
    ("I3", "Letters", "1a3", "CARD_CVV"),
])

WEEKDAY = rows("TC-PRC-ECP", 13, [
    ("V-weekday", "Monday night", "2026-11-02", False), ("V-weekday", "Tuesday night", "2026-11-03", False),
    ("V-weekday", "Wednesday night", "2026-11-04", False), ("V-weekday", "Thursday night", "2026-11-05", False),
    ("V-weekend", "Friday night", "2026-11-06", True), ("V-weekend", "Saturday night", "2026-11-07", True),
    ("V-weekday", "Sunday night (check-out Monday)", "2026-11-08", False),
])

D = dict(level="Unit", technique="ECP")


@pytest.mark.parametrize("c", cases(EMAIL, module="Registration", requirement="FR-01", priority="P1", **D))
def test_email(c):
    assert run(v.validate_email, c["inputs"]["value"]) == c["expected"]


@pytest.mark.parametrize("c", cases(PHONE, module="Registration", requirement="FR-01", **D))
def test_phone(c):
    assert run(v.validate_phone, c["inputs"]["value"]) == c["expected"]


@pytest.mark.parametrize("c", cases(NAME_CHARS, module="Registration", requirement="FR-01", **D))
def test_name_chars(c):
    assert run(v.validate_name, c["inputs"]["value"]) == c["expected"]


@pytest.mark.parametrize("c", cases(PASSWORD, module="Authentication", requirement="FR-02", priority="P1", **D))
def test_password_classes(c):
    assert run(v.validate_password, c["inputs"]["value"]) == c["expected"]


@pytest.mark.parametrize("c", cases(ROOM, module="Room Catalogue", requirement="FR-04", **D))
def test_room_type(c):
    assert run(get_room_type, c["inputs"]["value"]) == c["expected"]


@pytest.mark.parametrize("c", cases(TIER, module="Pricing & Tax", requirement="FR-06", **D))
def test_loyalty(c):
    try:
        got = str(pr.loyalty_pct(c["inputs"]["value"]))
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]


@pytest.mark.parametrize("c", cases(PROMO, module="Pricing & Tax", requirement="FR-06", **D))
def test_promo(c):
    from decimal import Decimal
    try:
        got = pr.promo_amount(c["inputs"]["value"], Decimal("20000"))
    except ValidationError as e:
        got = e.code
    expected = c["expected"]
    assert got == (Decimal(expected) if expected[0].isdigit() else expected)


@pytest.mark.parametrize("c", cases(UPI, module="Payment", requirement="FR-08", **D))
def test_upi(c):
    assert run(pay.validate_upi, c["inputs"]["value"]) == c["expected"]


@pytest.mark.parametrize("c", cases(CARD, module="Payment", requirement="FR-08", priority="P1", **D))
def test_card_number(c):
    assert run(pay.validate_card, c["inputs"]["value"], 12, 2030, "123", TODAY) == c["expected"]


@pytest.mark.parametrize("c", cases(CVV, module="Payment", requirement="FR-08", **D))
def test_cvv(c):
    assert run(pay.validate_card, "4111111111111111", 12, 2030, c["inputs"]["value"], TODAY) == c["expected"]


@pytest.mark.parametrize("c", cases(WEEKDAY, module="Pricing & Tax", requirement="FR-06", **D))
def test_weekend_classes(c):
    assert pr.is_weekend_night(date.fromisoformat(c["inputs"]["value"])) is c["expected"]
