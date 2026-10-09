"""Tariff, discount and tax computation (FR-06, FR-15).

Total payable (per booking)

    subtotal  = Σ_nights Σ_rooms tariff × (1 + weekend_pct + peak_pct)
    discount  = min( subtotal × (long_stay_pct + loyalty_pct) + promo_amount,
                     subtotal × MAX_DISCOUNT_PCT )
    taxable   = subtotal − discount
    gst       = taxable × gst_rate(tariff)
    total     = taxable + gst
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .errors import ValidationError
from .rooms import EXTRA_BED_RATE, get_room_type

WEEKEND_SURCHARGE = Decimal("0.20")   # Friday and Saturday nights
PEAK_SURCHARGE = Decimal("0.30")      # 20 Dec .. 5 Jan (inclusive)
MAX_DISCOUNT_PCT = Decimal("0.30")

LOYALTY_DISCOUNT = {
    "NONE": Decimal("0"),
    "SILVER": Decimal("0.05"),
    "GOLD": Decimal("0.10"),
    "PLATINUM": Decimal("0.15"),
}

# Long-stay discount bands: (min_nights, pct)
LONG_STAY_BANDS = ((14, Decimal("0.15")), (7, Decimal("0.10")))

PROMO_CODES = {
    # code: (kind, value, min_subtotal, cap)
    "WELCOME10": ("PCT", Decimal("0.10"), Decimal("3000"), Decimal("1000")),
    "FLAT500": ("AMT", Decimal("500"), Decimal("5000"), None),
}

# GST on hotel accommodation, per night declared tariff (India, rates effective 22-Sep-2025)
GST_EXEMPT_BELOW = 1000
GST_LOWER_SLAB_MAX = 7500
GST_LOWER_RATE = Decimal("0.05")
GST_HIGHER_RATE = Decimal("0.18")

UPGRADE_PATH = {"STANDARD": "DELUXE", "DELUXE": "FAMILY", "FAMILY": "SUITE"}


def money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def gst_rate(tariff_per_night) -> Decimal:
    tariff = Decimal(tariff_per_night)
    if tariff < 0:
        raise ValidationError("TARIFF_NEGATIVE", "Tariff cannot be negative")
    if tariff < GST_EXEMPT_BELOW:
        return Decimal("0")
    if tariff <= GST_LOWER_SLAB_MAX:
        return GST_LOWER_RATE
    return GST_HIGHER_RATE


def is_weekend_night(night: date) -> bool:
    """A night is a weekend night if it starts on a Friday or Saturday."""
    return night.weekday() in (4, 5)


def is_peak_night(night: date) -> bool:
    return (night.month == 12 and night.day >= 20) or (night.month == 1 and night.day <= 5)


def night_multiplier(night: date) -> Decimal:
    pct = Decimal("1")
    if is_weekend_night(night):
        pct += WEEKEND_SURCHARGE
    if is_peak_night(night):
        pct += PEAK_SURCHARGE
    return pct


def long_stay_pct(nights: int) -> Decimal:
    for min_nights, pct in LONG_STAY_BANDS:
        if nights >= min_nights:
            return pct
    return Decimal("0")


def loyalty_pct(tier: str) -> Decimal:
    key = (tier or "NONE").upper()
    if key not in LOYALTY_DISCOUNT:
        raise ValidationError("LOYALTY_INVALID", f"Unknown loyalty tier {tier!r}")
    return LOYALTY_DISCOUNT[key]


def promo_amount(code: str | None, subtotal: Decimal) -> Decimal:
    if not code:
        return Decimal("0")
    key = code.strip().upper()
    if key not in PROMO_CODES:
        raise ValidationError("PROMO_INVALID", f"Promo code {code!r} is not valid")
    kind, value, min_subtotal, cap = PROMO_CODES[key]
    if subtotal < min_subtotal:
        raise ValidationError("PROMO_MIN_SPEND", f"{key} needs a subtotal of at least ₹{min_subtotal}")
    amount = subtotal * value if kind == "PCT" else value
    if cap is not None and amount > cap:
        amount = cap
    return amount


@dataclass
class Quote:
    room_type: str
    nights: int
    rooms: int
    tariff_per_night: Decimal
    subtotal: Decimal
    long_stay_discount: Decimal
    loyalty_discount: Decimal
    promo_discount: Decimal
    discount: Decimal
    discount_capped: bool
    taxable: Decimal
    gst_rate: Decimal
    gst: Decimal
    total: Decimal
    night_lines: list = field(default_factory=list)

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
        d["night_lines"] = [{"date": n.isoformat(), "multiplier": float(m)} for n, m in self.night_lines]
        return d


def compute_quote(room_type: str, check_in: date, check_out: date, rooms: int = 1,
                  extra_beds: int = 0, loyalty: str = "NONE", promo: str | None = None) -> Quote:
    rt = get_room_type(room_type)
    nights = (check_out - check_in).days
    if nights < 1:
        raise ValidationError("STAY_TOO_SHORT", "Check-out must be after check-in")
    if rooms < 1:
        raise ValidationError("ROOMS_MIN", "At least one room")
    if extra_beds < 0 or extra_beds > rooms:
        raise ValidationError("EXTRA_BED_COUNT", "At most one extra bed per room")
    if extra_beds and not rt.extra_bed_allowed:
        raise ValidationError("EXTRA_BED_NOT_ALLOWED", f"{rt.name} does not allow an extra bed")

    room_nightly = Decimal(rt.base_rate) * rooms + Decimal(EXTRA_BED_RATE) * extra_beds
    tariff = Decimal(rt.base_rate) + (Decimal(EXTRA_BED_RATE) if extra_beds else 0)

    subtotal = Decimal("0")
    lines = []
    for i in range(nights):
        night = check_in + timedelta(days=i)
        m = night_multiplier(night)
        lines.append((night, m))
        subtotal += room_nightly * m
    subtotal = money(subtotal)

    ls = subtotal * long_stay_pct(nights)
    lo = subtotal * loyalty_pct(loyalty)
    pr = promo_amount(promo, subtotal)
    raw_discount = ls + lo + pr
    cap = subtotal * MAX_DISCOUNT_PCT
    capped = raw_discount > cap
    discount = money(cap if capped else raw_discount)

    taxable = money(subtotal - discount)
    rate = gst_rate(tariff)
    gst = money(taxable * rate)
    return Quote(rt.code, nights, rooms, tariff, subtotal, money(ls), money(lo), money(pr),
                 discount, capped, taxable, rate, gst, money(taxable + gst), lines)


def complimentary_benefits(tier: str, nights: int, days_in_advance: int, room_type: str) -> dict:
    """FR-15 cause-effect rule.

    C1 tier is GOLD or PLATINUM, C2 stay ≥ 3 nights, C3 booked ≥ 30 days ahead,
    C4 room is not a SUITE.
    E1 upgrade  = C1 ∧ C2 ∧ C4
    E2 breakfast = C1 ∨ (C2 ∧ C3)
    E3 none      = ¬E1 ∧ ¬E2
    """
    c1 = (tier or "NONE").upper() in ("GOLD", "PLATINUM")
    c2 = nights >= 3
    c3 = days_in_advance >= 30
    c4 = get_room_type(room_type).code != "SUITE"
    upgrade = c1 and c2 and c4
    breakfast = c1 or (c2 and c3)
    return {
        "upgrade": upgrade,
        "upgrade_to": UPGRADE_PATH.get(room_type.upper()) if upgrade else None,
        "breakfast": breakfast,
        "none": not upgrade and not breakfast,
    }
