"""Black-box: Decision Table testing and Cause-Effect Graphing.

DT-1  Cancellation refund policy (FR-07) — limited-entry table (8 rules) plus
      extended-entry expansion over every loyalty tier.
DT-2  Complimentary benefits (FR-15) — exhaustive 2^4 = 16 rules derived from
      the cause-effect graph.
CEG   Reduced test set obtained by back-tracking each effect through the
      cause-effect graph (one test per effect activation + boundary of each
      AND/OR node), and a surcharge CEG (weekend ∧ peak).
"""
from datetime import date
from itertools import product

import pytest

from app.domain.cancellation import refund_decision
from app.domain.errors import ValidationError
from app.domain.pricing import complimentary_benefits, night_multiplier
from tests.tclib import cases

# --------------------------------------------------------------------- DT-1
BAND_DAYS = {"<0": -1, "0-1": 1, "2-6": 4, ">=7": 10}

LIMITED = [
    # rule, hotel, refundable, band, tier, (pct, fee, voucher)
    ("R1", True, None, None, None, (100, 0, True)),
    ("R2", False, False, ">=7", "NONE", (0, 0, False)),
    ("R3", False, True, ">=7", "NONE", (100, 0, False)),
    ("R4", False, True, "2-6", "NONE", (50, 200, False)),
    ("R5", False, True, "2-6", "PLATINUM", (75, 0, False)),
    ("R6", False, True, "0-1", "NONE", (0, 0, False)),
    ("R7", False, True, "0-1", "PLATINUM", (25, 0, False)),
    ("R8", False, True, "<0", "NONE", "CANCEL_AFTER_CHECKIN"),
]

DT1 = []
for i, (rule, hotel, refundable, band, tier, exp) in enumerate(LIMITED, 1):
    DT1.append({"id": f"TC-CAN-DT-{i:03d}",
                "title": f"Decision-table rule {rule}: hotel={'Y' if hotel else 'N'}, "
                         f"refundable={'-' if refundable is None else ('Y' if refundable else 'N')}, "
                         f"band={band or '-'}, tier={tier or '-'}",
                "inputs": {"hotel_initiated": hotel, "refundable": True if refundable is None else refundable,
                           "days_before": BAND_DAYS.get(band, 3), "tier": tier or "GOLD"},
                "expected": exp if isinstance(exp, str) else {"refund_pct": exp[0], "fee": exp[1], "voucher": exp[2]},
                "rule": rule})

# Extended-entry expansion: refundable × valid band × every tier (shows that SILVER/GOLD behave like NONE)
EXPECT = {(">=7", False): (100, 0), ("2-6", False): (50, 200), ("0-1", False): (0, 0),
          (">=7", True): (100, 0), ("2-6", True): (75, 0), ("0-1", True): (25, 0)}
for band, tier in product((">=7", "2-6", "0-1"), ("NONE", "SILVER", "GOLD", "PLATINUM")):
    pct, fee = EXPECT[(band, tier == "PLATINUM")]
    DT1.append({"id": f"TC-CAN-DT-{len(DT1) + 1:03d}",
                "title": f"Extended entry: refundable, {band} days, tier {tier}",
                "inputs": {"hotel_initiated": False, "refundable": True, "days_before": BAND_DAYS[band], "tier": tier},
                "expected": {"refund_pct": pct, "fee": fee, "voucher": False}})
DT1.append({"id": f"TC-CAN-DT-{len(DT1) + 1:03d}",
            "title": "Precedence: hotel-initiated cancellation after stay start still refunds 100 %",
            "inputs": {"hotel_initiated": True, "refundable": False, "days_before": -2, "tier": "NONE"},
            "expected": {"refund_pct": 100, "fee": 0, "voucher": True}})
DT1.append({"id": f"TC-CAN-DT-{len(DT1) + 1:03d}",
            "title": "Precedence: non-refundable PLATINUM member inside 2 days gets 0 %",
            "inputs": {"hotel_initiated": False, "refundable": False, "days_before": 1, "tier": "PLATINUM"},
            "expected": {"refund_pct": 0, "fee": 0, "voucher": False}})


@pytest.mark.parametrize("c", cases(DT1, module="Cancellation", requirement="FR-07", technique="Decision Table",
                                    priority="P1"))
def test_refund_decision_table(c):
    i = c["inputs"]
    try:
        d = refund_decision(i["refundable"], i["days_before"], i["hotel_initiated"], i["tier"])
        got = {"refund_pct": d.refund_pct, "fee": d.fee, "voucher": d.voucher}
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]


def test_refund_amount_never_negative():
    """Fee larger than the refund must clamp to zero (tiny booking)."""
    d = refund_decision(True, 3)
    assert str(d.refund_amount(100)) == "0.00"       # 50 % of 100 = 50 − 200 fee → 0
    assert str(d.refund_amount(1000)) == "300.00"    # 500 − 200


# --------------------------------------------------------------------- DT-2 from cause-effect graph
C_VALUES = {"C1": ("GOLD", "SILVER"), "C2": (3, 2), "C3": (30, 29), "C4": ("DELUXE", "SUITE")}


def benefit_expectation(c1, c2, c3, c4):
    e1 = c1 and c2 and c4
    e2 = c1 or (c2 and c3)
    return {"upgrade": e1, "breakfast": e2, "none": not e1 and not e2}


DT2 = []
for i, bits in enumerate(product((True, False), repeat=4), 1):
    c1, c2, c3, c4 = bits
    flags = "".join("T" if b else "F" for b in bits)
    DT2.append({"id": f"TC-BEN-DT-{i:03d}",
                "title": f"Benefits rule {i:02d}: C1C2C3C4={flags}",
                "inputs": {"tier": C_VALUES["C1"][0 if c1 else 1], "nights": C_VALUES["C2"][0 if c2 else 1],
                           "days_in_advance": C_VALUES["C3"][0 if c3 else 1],
                           "room_type": C_VALUES["C4"][0 if c4 else 1]},
                "expected": benefit_expectation(c1, c2, c3, c4)})


@pytest.mark.parametrize("c", cases(DT2, module="Pricing & Benefits", requirement="FR-15",
                                    technique="Decision Table (from CEG)", priority="P2"))
def test_benefits_decision_table(c):
    i = c["inputs"]
    got = complimentary_benefits(i["tier"], i["nights"], i["days_in_advance"], i["room_type"])
    assert {k: got[k] for k in ("upgrade", "breakfast", "none")} == c["expected"]


# --------------------------------------------------------------------- CEG reduced set
CEG = [
    ("E1 upgrade fires: C1∧C2∧C4 all true", ("PLATINUM", 5, 0, "STANDARD"), {"upgrade": True, "upgrade_to": "DELUXE"}),
    ("E1 blocked by ¬C1 (AND node, cause 1 false)", ("NONE", 5, 0, "STANDARD"), {"upgrade": False}),
    ("E1 blocked by ¬C2 (AND node, cause 2 false)", ("GOLD", 2, 0, "STANDARD"), {"upgrade": False}),
    ("E1 blocked by ¬C4 (AND node, cause 4 false — suite cannot be upgraded)", ("GOLD", 5, 0, "SUITE"),
     {"upgrade": False, "breakfast": True}),
    ("E2 via C1 alone (OR node, first input)", ("GOLD", 1, 0, "SUITE"), {"breakfast": True, "upgrade": False}),
    ("E2 via C2∧C3 alone (OR node, second input)", ("NONE", 3, 30, "STANDARD"), {"breakfast": True, "upgrade": False}),
    ("E2 off when C2 true but C3 false and ¬C1", ("SILVER", 3, 29, "STANDARD"), {"breakfast": False}),
    ("E3 none: every cause false", ("NONE", 1, 0, "SUITE"), {"none": True}),
    ("Upgrade path FAMILY → SUITE", ("PLATINUM", 4, 40, "FAMILY"), {"upgrade_to": "SUITE", "breakfast": True}),
    ("Upgrade path DELUXE → FAMILY", ("GOLD", 3, 0, "DELUXE"), {"upgrade_to": "FAMILY"}),
]
CEG_ROWS = [{"id": f"TC-BEN-CEG-{i:03d}", "title": t,
             "inputs": {"tier": a[0], "nights": a[1], "days_in_advance": a[2], "room_type": a[3]}, "expected": e}
            for i, (t, a, e) in enumerate(CEG, 1)]


@pytest.mark.parametrize("c", cases(CEG_ROWS, module="Pricing & Benefits", requirement="FR-15",
                                    technique="Cause-Effect Graph", priority="P2"))
def test_benefits_cause_effect(c):
    i = c["inputs"]
    got = complimentary_benefits(i["tier"], i["nights"], i["days_in_advance"], i["room_type"])
    for k, val in c["expected"].items():
        assert got[k] == val, k


SURCHARGE = [
    ("Weekday, off-peak → ×1.00", "2026-11-03", "1.00"),
    ("Weekend (Fri), off-peak → ×1.20", "2026-11-06", "1.20"),
    ("Weekday, peak (Thu 24 Dec) → ×1.30", "2026-12-24", "1.30"),
    ("Weekend (Sat 26 Dec), peak → ×1.50 (additive)", "2026-12-26", "1.50"),
]
SUR_ROWS = [{"id": f"TC-PRC-CEG-{i:03d}", "title": t, "inputs": {"night": d}, "expected": e}
            for i, (t, d, e) in enumerate(SURCHARGE, 1)]


@pytest.mark.parametrize("c", cases(SUR_ROWS, module="Pricing & Tax", requirement="FR-06",
                                    technique="Cause-Effect Graph"))
def test_surcharge_causes(c):
    from decimal import Decimal
    assert night_multiplier(date.fromisoformat(c["inputs"]["night"])) == Decimal(c["expected"])
