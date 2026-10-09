"""Black-box: Boundary Value Analysis (BVA).

For a variable with valid range [min, max] robust BVA tests
    min-1, min, min+1, nominal, max-1, max, max+1      (6n + 1 values for n variables)
Single-variable robust BVA is used for every bounded input in the SRS; a
two-variable normal BVA (4n+1) and a worst-case BVA (5^n) are generated for
(nights × rooms) to show multi-variable techniques.
"""
from datetime import date, time, timedelta
from decimal import Decimal
from itertools import product

import pytest

from app.domain import cancellation as cx
from app.domain import payment as pay
from app.domain import pricing as pr
from app.domain import validation as v
from app.domain.errors import ValidationError
from tests.tclib import cases

TODAY = date(2026, 10, 8)
OK = "ACCEPT"


def run(fn, *args):
    try:
        fn(*args)
        return OK
    except ValidationError as e:
        return e.code


def row(id, title, inputs, expected, **kw):
    return {"id": id, "title": title, "inputs": inputs, "expected": expected, **kw}


# ----------------------------------------------------------------- name length 2..50
NAME = [row(f"TC-REG-BVA-{i:03d}", f"Guest name length {n} ({tag})", {"length": n}, exp)
        for i, (n, tag, exp) in enumerate([
            (1, "min-1", "NAME_TOO_SHORT"), (2, "min", OK), (3, "min+1", OK), (25, "nominal", OK),
            (49, "max-1", OK), (50, "max", OK), (51, "max+1", "NAME_TOO_LONG")], 1)]


@pytest.mark.parametrize("c", cases(NAME, module="Registration", requirement="FR-01", technique="BVA",
                                    priority="P1"))
def test_name_length(c):
    n = c["inputs"]["length"]
    name = ("Ab" * 30)[:n]
    assert run(v.validate_name, name) == c["expected"]


# ----------------------------------------------------------------- age 18..120
AGE = [row(f"TC-REG-BVA-{i:03d}", f"Primary guest age {a} ({tag})", {"age": a}, exp)
       for i, (a, tag, exp) in enumerate([
           (17, "min-1", "AGE_UNDER"), (18, "min", OK), (19, "min+1", OK), (60, "nominal", OK),
           (119, "max-1", OK), (120, "max", OK), (121, "max+1", "AGE_OVER")], 8)]


@pytest.mark.parametrize("c", cases(AGE, module="Registration", requirement="FR-01", technique="BVA",
                                    priority="P1"))
def test_age(c):
    assert run(v.validate_age, c["inputs"]["age"]) == c["expected"]


# ----------------------------------------------------------------- password length 8..20
PWD = [row(f"TC-AUTH-BVA-{i:03d}", f"Password length {n} ({tag})", {"length": n}, exp)
       for i, (n, tag, exp) in enumerate([
           (7, "min-1", "PWD_TOO_SHORT"), (8, "min", OK), (9, "min+1", OK), (14, "nominal", OK),
           (19, "max-1", OK), (20, "max", OK), (21, "max+1", "PWD_TOO_LONG")], 1)]


@pytest.mark.parametrize("c", cases(PWD, module="Authentication", requirement="FR-02", technique="BVA",
                                    priority="P1"))
def test_password_length(c):
    n = c["inputs"]["length"]
    pwd = ("Aa1@" + "x" * 30)[:n]
    assert run(v.validate_password, pwd) == c["expected"]


# ----------------------------------------------------------------- nights 1..30
NIGHTS = [row(f"TC-SRCH-BVA-{i:03d}", f"Length of stay {n} night(s) ({tag})", {"nights": n}, exp)
          for i, (n, tag, exp) in enumerate([
              (0, "min-1", "STAY_TOO_SHORT"), (1, "min", OK), (2, "min+1", OK), (15, "nominal", OK),
              (29, "max-1", OK), (30, "max", OK), (31, "max+1", "STAY_TOO_LONG")], 1)]


@pytest.mark.parametrize("c", cases(NIGHTS, module="Search & Availability", requirement="FR-03",
                                    technique="BVA", priority="P1"))
def test_nights(c):
    ci = TODAY + timedelta(days=10)
    assert run(v.validate_stay, ci, ci + timedelta(days=c["inputs"]["nights"]), TODAY) == c["expected"]


# ----------------------------------------------------------------- advance window 0..365 days
ADV = [row(f"TC-SRCH-BVA-{i:03d}", f"Check-in {d} day(s) from today ({tag})", {"days_ahead": d}, exp)
       for i, (d, tag, exp) in enumerate([
           (-1, "min-1", "CHECKIN_PAST"), (0, "min", OK), (1, "min+1", OK), (180, "nominal", OK),
           (364, "max-1", OK), (365, "max", OK), (366, "max+1", "CHECKIN_TOO_FAR")], 8)]


@pytest.mark.parametrize("c", cases(ADV, module="Search & Availability", requirement="FR-03",
                                    technique="BVA", priority="P1"))
def test_advance_window(c):
    ci = TODAY + timedelta(days=c["inputs"]["days_ahead"])
    assert run(v.validate_stay, ci, ci + timedelta(days=2), TODAY) == c["expected"]


# ----------------------------------------------------------------- guests per booking 1..10
GUESTS = [row(f"TC-BOOK-BVA-{i:03d}", f"Total guests {g} ({tag})", {"guests": g}, exp)
          for i, (g, tag, exp) in enumerate([
              (0, "min-1", "GUESTS_MIN"), (1, "min", OK), (2, "min+1", OK), (5, "nominal", OK),
              (9, "max-1", OK), (10, "max", OK), (11, "max+1", "GUESTS_MAX")], 1)]


@pytest.mark.parametrize("c", cases(GUESTS, module="Booking", requirement="FR-05", technique="BVA"))
def test_guest_count(c):
    assert run(v.validate_guest_count, c["inputs"]["guests"]) == c["expected"]


# ----------------------------------------------------------------- rooms per booking 1..5
ROOMS = [row(f"TC-BOOK-BVA-{i:03d}", f"Rooms per booking {r} ({tag})", {"rooms": r}, exp)
         for i, (r, tag, exp) in enumerate([
             (0, "min-1", "ROOMS_MIN"), (1, "min", OK), (2, "min+1", OK), (3, "nominal", OK),
             (4, "max-1", OK), (5, "max", OK), (6, "max+1", "ROOMS_MAX")], 8)]


@pytest.mark.parametrize("c", cases(ROOMS, module="Booking", requirement="FR-05", technique="BVA"))
def test_room_count(c):
    assert run(v.validate_room_count, c["inputs"]["rooms"]) == c["expected"]


# ----------------------------------------------------------------- occupancy per room (capacity)
OCC = [row(f"TC-BOOK-BVA-{i:03d}", f"{rt} occupancy {a}A+{ch}C extra_bed={eb} ({tag})",
           {"room_type": rt, "adults": a, "children": ch, "extra_bed": eb}, exp)
       for i, (rt, a, ch, eb, tag, exp) in enumerate([
           ("DELUXE", 0, 1, False, "adults min-1", "ADULTS_MIN"),
           ("DELUXE", 1, 0, False, "adults min", OK),
           ("DELUXE", 2, 1, False, "capacity max", OK),
           ("DELUXE", 3, 1, False, "capacity max+1", "OCCUPANCY_EXCEEDED"),
           ("DELUXE", 3, 1, True, "capacity+bed max", OK),
           ("DELUXE", 3, 2, True, "capacity+bed max+1", "OCCUPANCY_EXCEEDED"),
           ("STANDARD", 2, 0, False, "capacity max", OK),
           ("STANDARD", 2, 1, False, "capacity max+1", "OCCUPANCY_EXCEEDED"),
           ("FAMILY", 2, 4, False, "capacity max", OK),
           ("FAMILY", 2, 5, False, "capacity max+1", "OCCUPANCY_EXCEEDED"),
           ("SUITE", 1, -1, False, "children min-1", "CHILDREN_NEGATIVE"),
       ], 15)]


@pytest.mark.parametrize("c", cases(OCC, module="Booking", requirement="FR-04", technique="BVA",
                                    priority="P1"))
def test_occupancy(c):
    i = c["inputs"]
    assert run(v.validate_occupancy, i["room_type"], i["adults"], i["children"], i["extra_bed"]) == c["expected"]


# ----------------------------------------------------------------- GST slab on tariff
GST = [row(f"TC-PRC-BVA-{i:03d}", f"GST slab for nightly tariff ₹{t}", {"tariff": t}, exp)
       for i, (t, exp) in enumerate([
           (0, "0"), (998, "0"), (999, "0"), (1000, "0.05"), (1001, "0.05"), (4000, "0.05"),
           (7499, "0.05"), (7500, "0.05"), (7501, "0.18"), (8300, "0.18"), (-1, "TARIFF_NEGATIVE")], 1)]


@pytest.mark.parametrize("c", cases(GST, module="Pricing & Tax", requirement="FR-06", technique="BVA",
                                    priority="P1"))
def test_gst_slab(c):
    try:
        got = str(pr.gst_rate(c["inputs"]["tariff"]))
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]


# ----------------------------------------------------------------- long-stay discount bands
LS = [row(f"TC-PRC-BVA-{i:03d}", f"Long-stay discount for {n} nights", {"nights": n}, exp)
      for i, (n, exp) in enumerate([(1, "0"), (6, "0"), (7, "0.10"), (8, "0.10"), (13, "0.10"),
                                     (14, "0.15"), (15, "0.15"), (30, "0.15")], 12)]


@pytest.mark.parametrize("c", cases(LS, module="Pricing & Tax", requirement="FR-06", technique="BVA"))
def test_long_stay(c):
    assert str(pr.long_stay_pct(c["inputs"]["nights"])) == c["expected"]


# ----------------------------------------------------------------- peak season edges
PEAK = [row(f"TC-PRC-BVA-{i:03d}", f"Peak-season flag on {d.isoformat()}", {"night": d.isoformat()}, exp)
        for i, (d, exp) in enumerate([
            (date(2026, 12, 19), False), (date(2026, 12, 20), True), (date(2026, 12, 21), True),
            (date(2026, 12, 31), True), (date(2027, 1, 1), True), (date(2027, 1, 4), True),
            (date(2027, 1, 5), True), (date(2027, 1, 6), False)], 20)]


@pytest.mark.parametrize("c", cases(PEAK, module="Pricing & Tax", requirement="FR-06", technique="BVA"))
def test_peak_season(c):
    assert pr.is_peak_night(date.fromisoformat(c["inputs"]["night"])) is c["expected"]


# ----------------------------------------------------------------- promo minimum spend & cap
PROMO = [row(f"TC-PRC-BVA-{i:03d}", f"WELCOME10 on subtotal ₹{s}", {"subtotal": s}, exp)
         for i, (s, exp) in enumerate([
             ("2999.99", "PROMO_MIN_SPEND"), ("3000", "300.00"), ("3000.01", "300.00"),
             ("9999.90", "999.99"), ("10000", "1000.00"), ("10000.10", "1000.00")], 28)]


@pytest.mark.parametrize("c", cases(PROMO, module="Pricing & Tax", requirement="FR-06", technique="BVA"))
def test_promo_bounds(c):
    try:
        got = str(pr.money(pr.promo_amount("WELCOME10", Decimal(c["inputs"]["subtotal"]))))
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]


# ----------------------------------------------------------------- refund bands by days before check-in
REF = [row(f"TC-CAN-BVA-{i:03d}", f"Refund when cancelling {d} day(s) before check-in", {"days_before": d}, exp)
       for i, (d, exp) in enumerate([
           (-1, "CANCEL_AFTER_CHECKIN"), (0, 0), (1, 0), (2, 50), (3, 50), (6, 50), (7, 100), (8, 100)], 1)]


@pytest.mark.parametrize("c", cases(REF, module="Cancellation", requirement="FR-07", technique="BVA",
                                    priority="P1"))
def test_refund_band(c):
    try:
        got = cx.refund_decision(True, c["inputs"]["days_before"]).refund_pct
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]


# ----------------------------------------------------------------- late checkout clock boundaries
LATE = [row(f"TC-CHK-BVA-{i:03d}", f"Late check-out at {t}", {"time": t, "nightly": 4000}, exp)
        for i, (t, exp) in enumerate([
            ("11:59", "0.00"), ("12:00", "0.00"), ("12:01", "1000.00"), ("14:59", "1000.00"),
            ("15:00", "1000.00"), ("15:01", "2000.00"), ("17:59", "2000.00"), ("18:00", "2000.00"),
            ("18:01", "4000.00"), ("23:59", "4000.00")], 1)]


@pytest.mark.parametrize("c", cases(LATE, module="Check-in/Check-out", requirement="FR-14", technique="BVA",
                                    priority="P2"))
def test_late_checkout(c):
    t = time.fromisoformat(c["inputs"]["time"])
    assert str(cx.late_checkout_fee(c["inputs"]["nightly"], t)) == c["expected"]


# ----------------------------------------------------------------- payment amount 1..500000
AMT = [row(f"TC-PAY-BVA-{i:03d}", f"Payment amount ₹{a}", {"amount": a}, exp)
       for i, (a, exp) in enumerate([
           ("0.99", "AMOUNT_MIN"), ("1", OK), ("1.01", OK), ("250000", OK), ("499999.99", OK),
           ("500000", OK), ("500000.01", "AMOUNT_MAX")], 1)]


@pytest.mark.parametrize("c", cases(AMT, module="Payment", requirement="FR-08", technique="BVA",
                                    priority="P1"))
def test_payment_amount(c):
    assert run(pay.validate_amount, c["inputs"]["amount"]) == c["expected"]


# ----------------------------------------------------------------- card expiry around current month
EXP = [row(f"TC-PAY-BVA-{i:03d}", f"Card expiring {m:02d}/{y} (today 10/2026)", {"month": m, "year": y}, exp)
       for i, (m, y, exp) in enumerate([
           (9, 2026, "CARD_EXPIRED"), (10, 2026, OK), (11, 2026, OK), (12, 2046, OK), (1, 2047, "CARD_EXP_YEAR"),
           (0, 2027, "CARD_EXP_MONTH"), (1, 2027, OK), (12, 2027, OK), (13, 2027, "CARD_EXP_MONTH")], 8)]


@pytest.mark.parametrize("c", cases(EXP, module="Payment", requirement="FR-08", technique="BVA"))
def test_card_expiry(c):
    i = c["inputs"]
    assert run(pay.validate_card, "4111111111111111", i["month"], i["year"], "123", TODAY) == c["expected"]


# ----------------------------------------------------------------- multi-variable BVA (nights x rooms)
def _bva_values(lo, hi, nominal):
    return [lo, lo + 1, nominal, hi - 1, hi]


def _two_var_normal():
    """4n+1 = 9 cases: one variable at each boundary value, the other at nominal."""
    n_vals, r_vals = _bva_values(1, 30, 15), _bva_values(1, 5, 3)
    combos = {(15, 3)}
    combos |= {(n, 3) for n in n_vals} | {(15, r) for r in r_vals}
    return sorted(combos)


NORMAL_2V = [row(f"TC-QTE-BVA2-{i:03d}", f"Quote with {n} nights × {r} rooms (normal BVA 4n+1)",
                 {"nights": n, "rooms": r}, "Valid quote; total = taxable + GST")
             for i, (n, r) in enumerate(_two_var_normal(), 1)]

WORST_2V = [row(f"TC-QTE-WC-{i:03d}", f"Quote with {n} nights × {r} rooms (worst-case BVA 5^n)",
                {"nights": n, "rooms": r}, "Valid quote; total = taxable + GST")
            for i, (n, r) in enumerate(product(_bva_values(1, 30, 15), _bva_values(1, 5, 3)), 1)]


@pytest.mark.parametrize("c", cases(NORMAL_2V + WORST_2V, module="Pricing & Tax", requirement="FR-06",
                                    technique="BVA (multi-variable)", priority="P3"))
def test_quote_two_variable_bva(c):
    n, r = c["inputs"]["nights"], c["inputs"]["rooms"]
    ci = date(2026, 11, 2)  # a Monday outside peak season
    q = pr.compute_quote("STANDARD", ci, ci + timedelta(days=n), rooms=r)
    assert q.nights == n and q.rooms == r
    assert q.total == q.taxable + q.gst
    assert q.subtotal >= Decimal(2500) * n * r          # surcharges only increase the price
    assert q.discount <= q.subtotal * pr.MAX_DISCOUNT_PCT
