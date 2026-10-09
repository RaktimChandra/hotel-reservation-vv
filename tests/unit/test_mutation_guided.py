"""Tests added after mutation-testing iteration 1 (mutation-guided test improvement).

Each test names the surviving mutant(s) it was written to kill. Metrics
(Occupancy, ADR, RevPAR) also get unit-level BVA/ECP — iteration 1 showed
all 23 metrics mutants survived because only integration tests covered them.
"""
import dataclasses
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app.domain import cancellation as cx
from app.domain import metrics as mt
from app.domain import pricing as pr
from app.domain import validation as v
from app.domain.errors import ValidationError
from tests.tclib import cases, tc

MG = dict(level="Unit", technique="Mutation-guided (kills surviving mutant)", priority="P3")


def code_of(fn, *a, **k):
    try:
        fn(*a, **k)
        return "ACCEPT"
    except ValidationError as e:
        return e.code


@tc("TC-MUT-001", "E-mail length boundary: 254 chars accepted, 255 rejected (kills validation-008/010/011)",
    module="Registration", requirement="FR-01", inputs={"lengths": "254, 255"}, expected="ACCEPT, EMAIL_INVALID",
    **{**MG, "technique": "BVA (mutation-guided)"})
def test_email_length_boundary():
    def mk(n):
        return "a" * (n - len("@hrrs.in")) + "@hrrs.in"
    assert len(mk(254)) == 254
    assert code_of(v.validate_email, mk(254)) == "ACCEPT"
    assert code_of(v.validate_email, mk(255)) == "EMAIL_INVALID"


@tc("TC-MUT-002", "Only ONE date argument of the wrong type is still rejected (kills validation-032 or→and)",
    module="Search & Availability", requirement="FR-03", inputs={"check_out": None}, expected="DATE_TYPE", **MG)
def test_one_bad_date():
    assert code_of(v.validate_stay, date(2026, 11, 2), None, date(2026, 10, 8)) == "DATE_TYPE"
    assert code_of(v.validate_stay, "2026-11-02", date(2026, 11, 3), date(2026, 10, 8)) == "DATE_TYPE"


@tc("TC-MUT-003", "Default extra_bed=False: 4 guests in DELUXE without the flag is refused (kills validation-045)",
    module="Booking", requirement="FR-04", inputs={"room": "DELUXE", "adults": 3, "children": 1},
    expected="OCCUPANCY_EXCEEDED", **MG)
def test_occupancy_default_flag():
    assert code_of(v.validate_occupancy, "DELUXE", 3, 1) == "OCCUPANCY_EXCEEDED"


@tc("TC-MUT-004", "Boolean / float head-counts are type errors (kills validation-046, validation-062)",
    module="Booking", requirement="FR-04, FR-05", inputs={"adults": True, "guests": "True, 3.0"},
    expected="OCCUPANCY_TYPE, GUESTS_TYPE ×2", **MG)
def test_bool_counts():
    assert code_of(v.validate_occupancy, "DELUXE", True, 0) == "OCCUPANCY_TYPE"
    assert code_of(v.validate_guest_count, True) == "GUESTS_TYPE"
    assert code_of(v.validate_guest_count, 3.0) == "GUESTS_TYPE"


@tc("TC-MUT-005", "compute_quote with 0 rooms is rejected even if called directly (kills pricing-047)",
    module="Pricing & Tax", requirement="FR-05", inputs={"rooms": 0}, expected="ROOMS_MIN", **MG)
def test_quote_zero_rooms():
    ci = date(2026, 11, 2)
    assert code_of(pr.compute_quote, "STANDARD", ci, ci + timedelta(days=1), 0) == "ROOMS_MIN"


@tc("TC-MUT-006", "Discounts summing to EXACTLY 30 % are not flagged as capped (kills pricing-068 > → >=)",
    module="Pricing & Tax", requirement="FR-06", inputs={"nights": 14, "tier": "PLATINUM", "promo": None},
    expected="discount = 30 % of subtotal, discount_capped = False", **{**MG, "technique": "BVA (mutation-guided)"})
def test_exact_cap():
    ci = date(2026, 11, 2)
    q = pr.compute_quote("STANDARD", ci, ci + timedelta(days=14), 1, 0, "PLATINUM")  # 15 % long stay + 15 % tier
    assert q.discount == pr.money(q.subtotal * Decimal("0.30")) and q.discount_capped is False


@tc("TC-MUT-007", "Refund decisions are immutable value objects (kills cancellation-003 frozen=True→False)",
    module="Cancellation", requirement="FR-07", inputs="assign to refund_pct", expected="FrozenInstanceError", **MG)
def test_refund_immutable():
    d = cx.refund_decision(True, 10)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.refund_pct = 0


@tc("TC-MUT-008", "Late-fee tariff boundary ₹0 is valid (kills cancellation-023 < → <=, cancellation-025 0 → 1)",
    module="Check-in/Check-out", requirement="FR-14", inputs={"nightly": "0 and 0.5", "time": "20:00"},
    expected="₹0.00 and ₹0.50", **{**MG, "technique": "BVA (mutation-guided)"})
def test_late_fee_zero_tariff():
    assert str(cx.late_checkout_fee(0, time(20, 0))) == "0.00"
    assert str(cx.late_checkout_fee("0.5", time(20, 0))) == "0.50"


# ------------------------------------------------------------------ metrics unit tests (BVA + ECP)
OCC = [
    ("TC-RPT-BVA-001", "Occupancy with 0 rooms sold (min)", (0, 20), "0.00"),
    ("TC-RPT-BVA-002", "Occupancy with 1 room sold (min+1)", (1, 20), "5.00"),
    ("TC-RPT-BVA-003", "Occupancy 19 of 20 (max-1)", (19, 20), "95.00"),
    ("TC-RPT-BVA-004", "Occupancy 20 of 20 (max)", (20, 20), "100.00"),
    ("TC-RPT-BVA-005", "Occupancy 21 of 20 (max+1) rejected", (21, 20), "METRIC_SOLD_RANGE"),
    ("TC-RPT-BVA-006", "Rooms sold −1 (min-1) rejected", (-1, 20), "METRIC_SOLD_RANGE"),
    ("TC-RPT-BVA-007", "No inventory (0 available) rejected", (0, 0), "METRIC_NO_INVENTORY"),
    ("TC-RPT-BVA-008", "Rounding: 1 of 3 = 33.33 %", (1, 3), "33.33"),
    ("TC-RPT-BVA-009", "Rounding half-up: 2 of 3 = 66.67 %", (2, 3), "66.67"),
    ("TC-RPT-BVA-010", "Single-room property: 1 of 1 sold (available = 1 boundary)", (1, 1), "100.00"),
]
OCC_ROWS = [{"id": i, "title": t, "inputs": {"sold": a[0], "available": a[1]}, "expected": e} for i, t, a, e in OCC]


@pytest.mark.parametrize("c", cases(OCC_ROWS, module="Reports", requirement="FR-12", technique="BVA", priority="P2"))
def test_occupancy_bva(c):
    try:
        got = str(mt.occupancy_pct(c["inputs"]["sold"], c["inputs"]["available"]))
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]


ADR = [
    ("TC-RPT-ECP-001", "ADR = revenue / rooms sold", ("12500", 3), "4166.67"),
    ("TC-RPT-ECP-002", "ADR with 0 rooms sold is 0 (no division by zero)", ("0", 0), "0.00"),
    ("TC-RPT-ECP-003", "ADR with negative sold treated as no sales", ("100", -2), "0.00"),
    ("TC-RPT-ECP-004", "RevPAR = revenue / rooms available", ("12500", 20), "625.00"),
    ("TC-RPT-ECP-005", "RevPAR with 0 available rejected", ("100", 0), "METRIC_NO_INVENTORY"),
    ("TC-RPT-ECP-006", "Identity RevPAR = ADR × Occupancy", ("12500", 3), "625.00"),
    ("TC-RPT-BVA-011", "ADR with exactly 1 room sold (sold = 1 boundary)", ("4000", 1), "4000.00"),
    ("TC-RPT-BVA-012", "RevPAR with exactly 1 room available (available = 1 boundary)", ("4000", 1), "4000.00"),
]
ADR_ROWS = [{"id": i, "title": t, "inputs": {"revenue": a[0], "n": a[1]}, "expected": e} for i, t, a, e in ADR]


@pytest.mark.parametrize("c", cases(ADR_ROWS, module="Reports", requirement="FR-12", technique="ECP", priority="P2"))
def test_adr_revpar(c):
    rev, n = c["inputs"]["revenue"], c["inputs"]["n"]
    try:
        if c["title"].startswith("ADR"):
            got = str(mt.adr(rev, n))
        elif "Identity" in c["title"]:
            a, occ = mt.adr(rev, n), mt.occupancy_pct(n, 20)
            got = str((a * occ / 100).quantize(Decimal("0.01")))
            assert abs(Decimal(got) - mt.revpar(rev, 20)) <= Decimal("0.01")
            got = str(mt.revpar(rev, 20))
        else:  # RevPAR rows
            got = str(mt.revpar(rev, n))
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]
