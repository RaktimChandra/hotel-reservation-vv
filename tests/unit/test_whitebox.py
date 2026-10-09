"""White-box (structural) testing.

Targets and the coverage criterion applied to each:

  refund_decision      basis-path testing, V(G) = 7 decisions + 1 = 8 independent paths
  late_checkout_fee    basis paths V(G) = 5 + data-flow all-defs / all-uses on `pct`
  gst_rate             basis paths V(G) = 4
  promo_amount         statement vs. branch vs. condition vs. MC/DC on
                       `cap is not None and amount > cap`; data-flow on `amount`
  is_peak_night        MC/DC on (A ∧ B) ∨ (C ∧ D)
  compute_quote        simple-loop testing on the per-night loop (skip, 1, 2, m, n-1, n)
  luhn_valid           loop + both arms of `d > 9`
  password_strength    statement (1 test) vs. branch (2 tests) coverage contrast
"""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app.domain import cancellation as cx
from app.domain import payment as pay
from app.domain import pricing as pr
from app.domain import validation as v
from app.domain.errors import ValidationError
from tests.tclib import tc

M = dict(level="Unit")


# ============================================================ refund_decision — basis paths
BASIS = [
    # id, path description (decision outcomes), args, expected rule / error
    ("P1", "D1=T", (True, 5, True, "NONE"), "R1"),
    ("P2", "D1=F, D2=T (days<0)", (True, -1, False, "NONE"), "CANCEL_AFTER_CHECKIN"),
    ("P3", "D1=F, D2=F, D3=T (non-refundable)", (False, 9, False, "NONE"), "R2"),
    ("P4", "D3=F, D4=T (≥7 days)", (True, 7, False, "NONE"), "R3"),
    ("P5", "D4=F, D5=T, D6=T (2-6 days, PLATINUM)", (True, 2, False, "PLATINUM"), "R5"),
    ("P6", "D4=F, D5=T, D6=F (2-6 days, other tier)", (True, 6, False, "SILVER"), "R4"),
    ("P7", "D5=F, D7=T (0-1 day, PLATINUM)", (True, 0, False, "PLATINUM"), "R7"),
    ("P8", "D5=F, D7=F (0-1 day, other tier)", (True, 1, False, "GOLD"), "R6"),
]


def _basis_params():
    out = []
    for i, (pid, desc, args, exp) in enumerate(BASIS, 1):
        out.append(pytest.param(args, exp, id=f"TC-WB-PATH-{i:03d}", marks=pytest.mark.tc(
            id=f"TC-WB-PATH-{i:03d}", title=f"refund_decision basis path {pid}: {desc}",
            module="Cancellation", requirement="FR-07", level="Unit", type="Structural",
            technique="Basis Path (McCabe V(G)=8)", priority="P1", preconditions="—",
            inputs=f"refundable={args[0]}, days_before={args[1]}, hotel_initiated={args[2]}, tier={args[3]}",
            steps="Call refund_decision(); record executed path", expected=f"Exits through {exp}")))
    return out


@pytest.mark.parametrize("args,exp", _basis_params())
def test_refund_basis_path(args, exp):
    try:
        got = cx.refund_decision(*args).rule
    except ValidationError as e:
        got = e.code
    assert got == exp


# ============================================================ late_checkout_fee — paths + data flow
LATE_PATHS = [
    ("negative tariff → error (def rate, p-use rate<0 true)", -1, "11:00", "TARIFF_NEGATIVE"),
    ("on time → pct def#1 = 0 → c-use in return", 3000, "12:00", "0.00"),
    ("12:01–15:00 → pct def#2 = 25", 3000, "13:30", "750.00"),
    ("15:01–18:00 → pct def#3 = 50", 3000, "16:00", "1500.00"),
    ("after 18:00 → pct def#4 = 100", 3000, "20:00", "3000.00"),
]


def _late_params():
    out = []
    for i, (desc, rate, t, exp) in enumerate(LATE_PATHS, 1):
        out.append(pytest.param(rate, t, exp, id=f"TC-WB-DF-{i:03d}", marks=pytest.mark.tc(
            id=f"TC-WB-DF-{i:03d}", title=f"late_checkout_fee path/du-pair: {desc}", module="Check-in/Check-out",
            requirement="FR-14", technique="Data-flow (all-defs, all-uses) + Basis Path V(G)=5",
            type="Structural", priority="P2", inputs=f"nightly_rate={rate}, checkout_at={t}", expected=exp, **M,
            preconditions="—", steps="Call late_checkout_fee()")))
    return out


@pytest.mark.parametrize("rate,t,exp", _late_params())
def test_late_fee_paths(rate, t, exp):
    try:
        got = str(cx.late_checkout_fee(rate, time.fromisoformat(t)))
    except ValidationError as e:
        got = e.code
    assert got == exp


# ============================================================ gst_rate — paths
@pytest.mark.parametrize("tariff,exp", [
    pytest.param(t, e, id=f"TC-WB-PATH-{8 + i:03d}", marks=pytest.mark.tc(
        id=f"TC-WB-PATH-{8 + i:03d}", title=f"gst_rate basis path {i}: tariff ₹{t}", module="Pricing & Tax",
        requirement="FR-06", technique="Basis Path (V(G)=4)", type="Structural", priority="P2",
        inputs=f"tariff={t}", expected=e, preconditions="—", steps="Call gst_rate()", **M))
    for i, (t, e) in enumerate([(-5, "TARIFF_NEGATIVE"), (500, "0"), (5000, "0.05"), (12000, "0.18")], 1)])
def test_gst_paths(tariff, exp):
    try:
        got = str(pr.gst_rate(tariff))
    except ValidationError as e:
        got = e.code
    assert got == exp


# ============================================================ promo_amount — coverage criteria ladder
@tc("TC-WB-STMT-001", "promo_amount: ONE test reaching 100 % statement coverage of the PCT+cap path",
    module="Pricing & Tax", requirement="FR-06", type="Structural", technique="Statement Coverage",
    inputs={"code": "WELCOME10", "subtotal": 50000}, expected="₹1000 (cap applied)")
def test_promo_statement():
    assert pr.promo_amount("WELCOME10", Decimal(50000)) == Decimal(1000)


@tc("TC-WB-BR-001", "promo_amount: cap condition FALSE branch (amount below cap)",
    module="Pricing & Tax", requirement="FR-06", type="Structural", technique="Branch (Decision) Coverage",
    inputs={"code": "WELCOME10", "subtotal": 4000}, expected="₹400 (cap not applied)")
def test_promo_branch_false():
    assert pr.promo_amount("WELCOME10", Decimal(4000)) == Decimal(400)


@tc("TC-WB-COND-001", "promo_amount: condition `cap is not None` = FALSE (FLAT500 has no cap)",
    module="Pricing & Tax", requirement="FR-06", type="Structural", technique="Condition Coverage",
    inputs={"code": "FLAT500", "subtotal": 9000}, expected="₹500")
def test_promo_condition_cap_none():
    assert pr.promo_amount("FLAT500", Decimal(9000)) == Decimal(500)


MCDC_PROMO = [
    ("TC-WB-MCDC-001", "A=T, B=T → cap applied (pairs with 002 for B, with 003 for A)", "WELCOME10", 20000, 1000),
    ("TC-WB-MCDC-002", "A=T, B=F → not applied (B independently flips outcome)", "WELCOME10", 5000, 500),
    ("TC-WB-MCDC-003", "A=F, B=– → not applied (A independently flips outcome)", "FLAT500", 20000, 500),
]


@pytest.mark.parametrize("code,sub,exp", [
    pytest.param(c, s, e, id=i, marks=pytest.mark.tc(
        id=i, title=f"MC/DC on `cap is not None and amount > cap`: {t}", module="Pricing & Tax",
        requirement="FR-06", technique="MC/DC (N+1 = 3 tests)", type="Structural", priority="P2",
        inputs=f"code={c}, subtotal={s}", expected=f"₹{e}", preconditions="—", steps="Call promo_amount()", **M))
    for i, t, c, s, e in MCDC_PROMO])
def test_promo_mcdc(code, sub, exp):
    assert pr.promo_amount(code, Decimal(sub)) == Decimal(exp)


# ============================================================ is_peak_night — MC/DC on (A∧B)∨(C∧D)
# A: month==12  B: day>=20  C: month==1  D: day<=5
MCDC_PEAK = [
    ("TC-WB-MCDC-004", date(2026, 12, 25), True, "A=T B=T C=F D=F → T"),
    ("TC-WB-MCDC-005", date(2026, 12, 10), False, "A=T B=F C=F D=F → F  (pairs with 004: B independent)"),
    ("TC-WB-MCDC-006", date(2026, 11, 25), False, "A=F B=T C=F D=F → F  (pairs with 004: A independent)"),
    ("TC-WB-MCDC-007", date(2027, 1, 3), True, "A=F B=F C=T D=T → T"),
    ("TC-WB-MCDC-008", date(2027, 1, 10), False, "A=F B=F C=T D=F → F  (pairs with 007: D independent)"),
    ("TC-WB-MCDC-009", date(2026, 11, 3), False, "A=F B=F C=F D=T → F  (pairs with 007: C independent)"),
]


@pytest.mark.parametrize("night,exp", [
    pytest.param(d, e, id=i, marks=pytest.mark.tc(
        id=i, title=f"MC/DC is_peak_night: {t}", module="Pricing & Tax", requirement="FR-06",
        technique="MC/DC", type="Structural", priority="P2", inputs=f"night={d}", expected=str(e),
        preconditions="—", steps="Call is_peak_night()", **M))
    for i, d, e, t in MCDC_PEAK])
def test_peak_mcdc(night, exp):
    assert pr.is_peak_night(night) is exp


# ============================================================ compute_quote — simple loop testing
LOOPS = [("skip (0 iterations → rejected)", 0), ("1 iteration (min)", 1), ("2 iterations", 2),
         ("m = 15 typical", 15), ("n-1 = 29", 29), ("n = 30 (max)", 30)]


@pytest.mark.parametrize("nights", [
    pytest.param(n, id=f"TC-WB-LOOP-{i:03d}", marks=pytest.mark.tc(
        id=f"TC-WB-LOOP-{i:03d}", title=f"compute_quote per-night loop: {t}", module="Pricing & Tax",
        requirement="FR-06", technique="Loop Testing (simple loop)", type="Structural", priority="P3",
        inputs=f"nights={n}", expected="STAY_TOO_SHORT" if n == 0 else f"{n} night lines; subtotal = Σ lines",
        preconditions="—", steps="Call compute_quote() for a STANDARD room from 2 Nov 2026", **M))
    for i, (t, n) in enumerate(LOOPS, 1)])
def test_quote_loop(nights):
    ci = date(2026, 11, 2)
    if nights == 0:
        with pytest.raises(ValidationError):
            pr.compute_quote("STANDARD", ci, ci)
        return
    q = pr.compute_quote("STANDARD", ci, ci + timedelta(days=nights))
    assert len(q.night_lines) == nights
    assert q.subtotal == pr.money(sum(Decimal(2500) * m for _, m in q.night_lines))


@tc("TC-WB-LOOP-007", "luhn_valid: loop over 16 digits exercising both arms of `d > 9`",
    module="Payment", requirement="FR-08", type="Structural", technique="Loop + Branch Coverage",
    inputs={"number": "4111111111111111 / 4012888888881881"}, expected="True for both, False after 1-digit change")
def test_luhn_loop():
    assert pay.luhn_valid("4111111111111111")
    assert pay.luhn_valid("4012888888881881")      # contains doubled digits > 9
    assert not pay.luhn_valid("4012888888881882")


# ============================================================ promo_amount data flow on `amount`
@tc("TC-WB-DF-006", "promo_amount du-path: amount def (PCT) → p-use (> cap) → c-use (return), cap applied",
    module="Pricing & Tax", requirement="FR-06", type="Structural", technique="Data-flow (all-du-paths)",
    inputs={"code": "WELCOME10", "subtotal": 15000}, expected="₹1000")
def test_df_amount_pct_capped():
    assert pr.promo_amount("WELCOME10", Decimal(15000)) == Decimal(1000)


@tc("TC-WB-DF-007", "promo_amount du-path: amount def (AMT) → c-use (return), cap is None",
    module="Pricing & Tax", requirement="FR-06", type="Structural", technique="Data-flow (all-du-paths)",
    inputs={"code": "FLAT500", "subtotal": 6000}, expected="₹500")
def test_df_amount_amt():
    assert pr.promo_amount("FLAT500", Decimal(6000)) == Decimal(500)


# ============================================================ password_strength statement vs branch
@tc("TC-WB-STMT-002", "password_strength: single all-violations input executes every append statement",
    module="Authentication", requirement="FR-02", type="Structural", technique="Statement Coverage",
    inputs={"password": "' '"}, expected="7 violations except PWD_TOO_LONG")
def test_pwd_statement():
    got = v.password_strength(" ")
    assert set(got) == {"PWD_TOO_SHORT", "PWD_NO_UPPER", "PWD_NO_LOWER", "PWD_NO_DIGIT",
                        "PWD_NO_SPECIAL", "PWD_WHITESPACE"}


@tc("TC-WB-BR-002", "password_strength: strong + over-long inputs add the FALSE arms → 100 % branch",
    module="Authentication", requirement="FR-02", type="Structural", technique="Branch (Decision) Coverage",
    inputs={"password": "Hotel@2026 / 'Aa1@'*6"}, expected="[] and ['PWD_TOO_LONG']")
def test_pwd_branch():
    assert v.password_strength("Hotel@2026") == []
    assert v.password_strength("Aa1@" * 6) == ["PWD_TOO_LONG"]
    assert v.password_strength(None) == ["PWD_TYPE"]


# ============================================================ compute_quote guard MC/DC
GUARD = [("TC-WB-MCDC-010", "extra_beds<0 = T → reject", -1, 1, "EXTRA_BED_COUNT"),
         ("TC-WB-MCDC-011", "extra_beds<0 = F, extra_beds>rooms = T → reject", 2, 1, "EXTRA_BED_COUNT"),
         ("TC-WB-MCDC-012", "both F → accepted", 1, 1, "ACCEPT")]


@pytest.mark.parametrize("beds,rooms,exp", [
    pytest.param(b, r, e, id=i, marks=pytest.mark.tc(
        id=i, title=f"MC/DC `extra_beds < 0 or extra_beds > rooms`: {t}", module="Pricing & Tax",
        requirement="FR-04", technique="MC/DC", type="Structural", priority="P3",
        inputs=f"extra_beds={b}, rooms={r}", expected=e, preconditions="—", steps="compute_quote(DELUXE, …)", **M))
    for i, t, b, r, e in GUARD])
def test_extra_bed_guard(beds, rooms, exp):
    ci = date(2026, 11, 2)
    try:
        pr.compute_quote("DELUXE", ci, ci + timedelta(days=1), rooms=rooms, extra_beds=beds)
        got = "ACCEPT"
    except ValidationError as e:
        got = e.code
    assert got == exp
