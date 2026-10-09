"""Pairwise (all-pairs) combinatorial testing, property-based testing and error guessing.

Pairwise: 5 parameters (4 × 4 × 3 × 2 × 3 = 288 full combinations) reduced by a
greedy all-pairs generator to a set where every pair of values appears at least once.
Each case is checked against an *independent test oracle* — a second, deliberately
naive implementation of the pricing formula written from the SRS, not from the code.
"""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations, product

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as s

from app.domain import cancellation as cx
from app.domain import payment as pay
from app.domain import pricing as pr
from app.domain import state as st
from app.domain import validation as v
from app.domain.errors import StateError, ValidationError
from tests.tclib import cases, tc

PARAMS = {
    "room": ["STANDARD", "DELUXE", "FAMILY", "SUITE"],
    "tier": ["NONE", "SILVER", "GOLD", "PLATINUM"],
    "promo": [None, "WELCOME10", "FLAT500"],
    "extra_bed": [0, 1],
    "stay": ["weekday", "weekend", "peak"],
}
STAYS = {"weekday": (date(2026, 11, 2), 3), "weekend": (date(2026, 11, 6), 2), "peak": (date(2026, 12, 24), 8)}


def all_pairs(params: dict) -> list[dict]:
    """Greedy all-pairs: repeatedly pick the full combination covering most uncovered pairs."""
    keys = list(params)
    uncovered = {((a, va), (b, vb)) for a, b in combinations(keys, 2) for va in params[a] for vb in params[b]}
    pool = [dict(zip(keys, combo)) for combo in product(*params.values())]
    chosen = []
    while uncovered:
        best = max(pool, key=lambda c: sum(((a, c[a]), (b, c[b])) in uncovered for a, b in combinations(keys, 2)))
        chosen.append(best)
        uncovered -= {((a, best[a]), (b, best[b])) for a, b in combinations(keys, 2)}
        pool.remove(best)
    return chosen


def oracle(room, tier, promo, extra_bed, check_in, nights):
    """Independent oracle written from SRS FR-06 text."""
    base = {"STANDARD": 2500, "DELUXE": 4000, "FAMILY": 6000, "SUITE": 7500}[room]
    tariff = base + (800 if extra_bed else 0)
    sub = Decimal(0)
    for i in range(nights):
        d = check_in + timedelta(days=i)
        pct = Decimal(1)
        if d.weekday() in (4, 5):
            pct += Decimal("0.2")
        if (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 5):
            pct += Decimal("0.3")
        sub += tariff * pct
    sub = sub.quantize(Decimal("0.01"), ROUND_HALF_UP)
    pct = {"NONE": 0, "SILVER": 5, "GOLD": 10, "PLATINUM": 15}[tier]
    pct += 15 if nights >= 14 else 10 if nights >= 7 else 0
    disc = sub * pct / 100
    if promo == "WELCOME10" and sub >= 3000:
        disc += min(sub / 10, Decimal(1000))
    if promo == "FLAT500" and sub >= 5000:
        disc += 500
    disc = min(disc, sub * Decimal("0.3")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    taxable = sub - disc
    rate = Decimal(0) if tariff < 1000 else Decimal("0.05") if tariff <= 7500 else Decimal("0.18")
    gst = (taxable * rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return taxable + gst


PAIRWISE = []
for i, c in enumerate(all_pairs(PARAMS), 1):
    allowed = c["room"] in ("DELUXE", "SUITE") or not c["extra_bed"]
    PAIRWISE.append({"id": f"TC-QTE-PW-{i:03d}",
                     "title": f"Pairwise #{i}: {c['room']}, {c['tier']}, promo={c['promo']}, bed={c['extra_bed']}, {c['stay']}",
                     "inputs": c, "expected": "Total equals independent oracle" if allowed else "EXTRA_BED_NOT_ALLOWED"})


@pytest.mark.parametrize("c", cases(PAIRWISE, module="Pricing & Tax", requirement="FR-06",
                                    technique="Pairwise / Combinatorial + Test Oracle", priority="P2"))
def test_pairwise_quote(c):
    i = c["inputs"]
    ci, nights = STAYS[i["stay"]]
    try:
        q = pr.compute_quote(i["room"], ci, ci + timedelta(days=nights), 1, i["extra_bed"], i["tier"], i["promo"])
    except ValidationError as e:
        assert e.code == c["expected"]
        return
    assert q.total == oracle(i["room"], i["tier"], i["promo"], i["extra_bed"], ci, nights)


def test_pairwise_set_is_complete_and_small():
    rows = all_pairs(PARAMS)
    keys = list(PARAMS)
    needed = {((a, va), (b, vb)) for a, b in combinations(keys, 2) for va in PARAMS[a] for vb in PARAMS[b]}
    got = {((a, r[a]), (b, r[b])) for r in rows for a, b in combinations(keys, 2)}
    assert needed <= got
    assert len(rows) < 30 < 288


# ============================================================ property-based (Hypothesis)
dates = s.dates(min_value=date(2026, 10, 8), max_value=date(2027, 9, 30))
PB = dict(module="Pricing & Tax", requirement="FR-06", type="Functional", technique="Property-based (Hypothesis)",
          priority="P2", steps="Hypothesis generates 200 random examples and shrinks failures")


@tc("TC-PBT-001", "Invariant: total = taxable + GST and every amount ≥ 0 for any valid stay",
    inputs="random room, check-in, 1-30 nights, rooms 1-5, tier, promo", expected="Invariant holds", **PB)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(room=s.sampled_from(PARAMS["room"]), ci=dates, nights=s.integers(1, 30), rooms=s.integers(1, 5),
       tier=s.sampled_from(PARAMS["tier"]), promo=s.sampled_from([None, "WELCOME10", "FLAT500"]))
def test_prop_total_identity(room, ci, nights, rooms, tier, promo):
    try:
        q = pr.compute_quote(room, ci, ci + timedelta(days=nights), rooms, 0, tier, promo)
    except ValidationError as e:
        assert e.code == "PROMO_MIN_SPEND"
        return
    assert q.total == q.taxable + q.gst
    assert min(q.subtotal, q.discount, q.taxable, q.gst) >= 0


@tc("TC-PBT-002", "Invariant: total discount never exceeds 30 % of subtotal (cap)",
    inputs="random stay ≥ 14 nights, PLATINUM, WELCOME10", expected="discount ≤ 0.30 × subtotal", **PB)
@settings(max_examples=200)
@given(room=s.sampled_from(PARAMS["room"]), ci=dates, nights=s.integers(14, 30))
def test_prop_discount_cap(room, ci, nights):
    q = pr.compute_quote(room, ci, ci + timedelta(days=nights), 1, 0, "PLATINUM", "WELCOME10")
    assert q.discount <= (q.subtotal * pr.MAX_DISCOUNT_PCT).quantize(Decimal("0.01")) + Decimal("0.01")
    assert q.discount_capped  # 15 % + 15 % + promo > 30 %


@tc("TC-PBT-003", "Metamorphic: adding one night never lowers the subtotal",
    inputs="random stay n and n+1 nights", expected="subtotal(n+1) > subtotal(n)", **PB)
@settings(max_examples=200)
@given(room=s.sampled_from(PARAMS["room"]), ci=dates, nights=s.integers(1, 29))
def test_prop_monotonic_nights(room, ci, nights):
    a = pr.compute_quote(room, ci, ci + timedelta(days=nights))
    b = pr.compute_quote(room, ci, ci + timedelta(days=nights + 1))
    assert b.subtotal > a.subtotal


@tc("TC-PBT-004", "Metamorphic: k rooms cost exactly k × one room before discounts",
    inputs="random stay, rooms 1-5", expected="subtotal(k) = k × subtotal(1)", **PB)
@settings(max_examples=200)
@given(room=s.sampled_from(PARAMS["room"]), ci=dates, nights=s.integers(1, 30), k=s.integers(1, 5))
def test_prop_linear_rooms(room, ci, nights, k):
    one = pr.compute_quote(room, ci, ci + timedelta(days=nights), 1)
    many = pr.compute_quote(room, ci, ci + timedelta(days=nights), k)
    assert many.subtotal == pr.money(one.subtotal * k)


@tc("TC-PBT-005", "Refund amount is always within [0, amount paid]",
    module="Cancellation", requirement="FR-07", technique="Property-based (Hypothesis)", priority="P1",
    inputs="random paid ₹1–5,00,000, days 0–400, tier, refundable", expected="0 ≤ refund ≤ paid")
@settings(max_examples=300)
@given(paid=s.decimals(min_value=1, max_value=500000, places=2), days=s.integers(0, 400),
       tier=s.sampled_from(PARAMS["tier"]), refundable=s.booleans(), hotel=s.booleans())
def test_prop_refund_bounds(paid, days, tier, refundable, hotel):
    amt = cx.refund_decision(refundable, days, hotel, tier).refund_amount(paid)
    assert Decimal(0) <= amt <= paid


@tc("TC-PBT-006", "Valid Luhn numbers stay valid; changing any single digit breaks the checksum",
    module="Payment", requirement="FR-08", technique="Property-based (Hypothesis)", priority="P2",
    inputs="random 15-digit prefix + computed check digit", expected="valid → mutated invalid")
@settings(max_examples=200)
@given(prefix=s.text(alphabet="0123456789", min_size=15, max_size=15), pos=s.integers(0, 15), delta=s.integers(1, 9))
def test_prop_luhn(prefix, pos, delta):
    check = next(d for d in "0123456789" if pay.luhn_valid(prefix + d))
    number = prefix + check
    mutated = number[:pos] + str((int(number[pos]) + delta) % 10) + number[pos + 1:]
    assert pay.luhn_valid(number) and not pay.luhn_valid(mutated)


@tc("TC-PBT-007", "Random event sequences never leave the 6 defined states (state-machine fuzzing)",
    module="Booking Life-cycle", requirement="FR-09", technique="Property-based (Hypothesis)", priority="P2",
    inputs="random sequence of up to 10 events", expected="state ∈ STATES; final states absorbing")
@settings(max_examples=300)
@given(events=s.lists(s.sampled_from(list(st.TRANSITIONS)), max_size=10))
def test_prop_state_machine(events):
    state = st.PENDING
    for e in events:
        try:
            nxt = st.next_state(state, e)
        except StateError:
            continue
        assert state not in st.FINAL_STATES
        state = nxt
    assert state in st.STATES


@tc("TC-PBT-008", "Any accepted password satisfies every composition rule (fuzzed strings)",
    module="Authentication", requirement="FR-02", technique="Property-based (Hypothesis)", priority="P2",
    inputs="random printable strings 0-30 chars", expected="accepted ⇒ all rules hold")
@settings(max_examples=400)
@given(pwd=s.text(min_size=0, max_size=30))
def test_prop_password(pwd):
    if not v.password_strength(pwd):
        assert 8 <= len(pwd) <= 20
        assert any(c.isupper() for c in pwd) and any(c.islower() for c in pwd) and any(c.isdigit() for c in pwd)


# ============================================================ error guessing
EG = [
    ("Leap-year stay 423 days ahead is outside the 365-day window", lambda: v.validate_stay(
        date(2028, 2, 28), date(2028, 3, 1), date(2027, 1, 1)), "CHECKIN_TOO_FAR"),
    ("Leap-day stay within window", lambda: v.validate_stay(
        date(2028, 2, 28), date(2028, 3, 1), date(2027, 12, 1)), 2),
    ("Year-end stay 31 Dec → 2 Jan crosses year boundary", lambda: pr.compute_quote(
        "STANDARD", date(2026, 12, 31), date(2027, 1, 2)).nights, 2),
    ("Check-out before check-in", lambda: v.validate_stay(date(2026, 11, 10), date(2026, 11, 9), date(2026, 10, 8)),
     "STAY_TOO_SHORT"),
    ("Boolean passed as age (True == 1 in Python)", lambda: v.validate_age(True), "AGE_TYPE"),
    ("Float passed as rooms", lambda: v.validate_room_count(2.0), "ROOMS_TYPE"),
    ("SQL-looking name is rejected by the name rule", lambda: v.validate_name("Robert'); DROP TABLE users;--"),
     "NAME_CHARS"),
    ("Extremely long email (300 chars)", lambda: v.validate_email("a" * 290 + "@mail.com"), "EMAIL_INVALID"),
    ("Name with leading/trailing and double spaces is normalised", lambda: v.validate_name("  Ananya   Rao  "),
     "Ananya Rao"),
    ("Unicode digits in phone", lambda: v.validate_phone("٩٨٣٢٢٨٨١٠١"), "PHONE_INVALID"),
    ("Amount as non-numeric text", lambda: pay.validate_amount("five hundred"), "AMOUNT_TYPE"),
    ("Negative nightly tariff for late fee", lambda: cx.late_checkout_fee(-100, __import__("datetime").time(13)),
     "TARIFF_NEGATIVE"),
]
EG_ROWS = [{"id": f"TC-EG-{i:03d}", "title": t, "inputs": "see title", "expected": e, "fn": f}
           for i, (t, f, e) in enumerate(EG, 1)]


@pytest.mark.parametrize("c", cases(EG_ROWS, module="Cross-cutting", requirement="FR-01..FR-14",
                                    technique="Error Guessing", priority="P2", type="Negative/Robustness"))
def test_error_guessing(c):
    try:
        got = c["fn"]()
    except ValidationError as e:
        got = e.code
    assert got == c["expected"]
