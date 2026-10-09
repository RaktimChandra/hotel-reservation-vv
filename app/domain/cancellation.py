"""Cancellation & refund policy (FR-07) and late check-out fee (FR-14).

Decision table (conditions → actions) for refund_decision:

  C1 hotel-initiated?          Y  N  N  N  N  N  N  N
  C2 refundable rate?          -  N  Y  Y  Y  Y  Y  Y
  C3 days before check-in      -  -  ≥7 2-6 2-6 0-1 0-1 <0
  C4 PLATINUM member?          -  -  -  N  Y  N  Y  -
  ---------------------------------------------------
  A1 refund %                 100 0 100 50 75  0  25  —
  A2 processing fee (INR)      0  0  0 200  0  0   0  —
  A3 compensation voucher      Y  N  N  N  N  N   N  —
  A4 reject (already started)  N  N  N  N  N  N   N  Y
"""
from dataclasses import dataclass
from datetime import time
from decimal import ROUND_HALF_UP, Decimal

from .errors import ValidationError

FULL_REFUND_DAYS = 7
PARTIAL_REFUND_DAYS = 2
PROCESSING_FEE = 200


@dataclass(frozen=True)
class RefundDecision:
    refund_pct: int
    fee: int
    voucher: bool
    rule: str

    def refund_amount(self, paid) -> Decimal:
        paid = Decimal(paid)
        amount = paid * self.refund_pct / 100 - self.fee
        amount = max(amount, Decimal("0"))
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def refund_decision(refundable: bool, days_before: int, hotel_initiated: bool = False,
                    tier: str = "NONE") -> RefundDecision:
    if hotel_initiated:
        return RefundDecision(100, 0, True, "R1")
    if days_before < 0:
        raise ValidationError("CANCEL_AFTER_CHECKIN", "Stay already started; cancellation not possible")
    if not refundable:
        return RefundDecision(0, 0, False, "R2")
    platinum = (tier or "NONE").upper() == "PLATINUM"
    if days_before >= FULL_REFUND_DAYS:
        return RefundDecision(100, 0, False, "R3")
    if days_before >= PARTIAL_REFUND_DAYS:
        if platinum:
            return RefundDecision(75, 0, False, "R5")
        return RefundDecision(50, PROCESSING_FEE, False, "R4")
    if platinum:
        return RefundDecision(25, 0, False, "R7")
    return RefundDecision(0, 0, False, "R6")


STANDARD_CHECKOUT = time(12, 0)
LATE_BANDS = ((time(15, 0), 25), (time(18, 0), 50))


def late_checkout_fee(nightly_rate, checkout_at: time) -> Decimal:
    """Fee for leaving after 12:00.

    ≤12:00 → 0 ; 12:01–15:00 → 25 % ; 15:01–18:00 → 50 % ; after 18:00 → 100 %.
    """
    rate = Decimal(nightly_rate)
    if rate < 0:
        raise ValidationError("TARIFF_NEGATIVE", "Tariff cannot be negative")
    if checkout_at <= STANDARD_CHECKOUT:
        pct = 0
    elif checkout_at <= LATE_BANDS[0][0]:
        pct = LATE_BANDS[0][1]
    elif checkout_at <= LATE_BANDS[1][0]:
        pct = LATE_BANDS[1][1]
    else:
        pct = 100
    return (rate * pct / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
