"""Hotel performance metrics (FR-12).

Occupancy % = rooms_sold / rooms_available × 100
ADR         = room_revenue / rooms_sold            (Average Daily Rate)
RevPAR      = room_revenue / rooms_available = ADR × Occupancy
"""
from decimal import ROUND_HALF_UP, Decimal

from .errors import ValidationError


def _q(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def occupancy_pct(rooms_sold: int, rooms_available: int) -> Decimal:
    if rooms_available <= 0:
        raise ValidationError("METRIC_NO_INVENTORY", "Rooms available must be positive")
    if rooms_sold < 0 or rooms_sold > rooms_available:
        raise ValidationError("METRIC_SOLD_RANGE", "Rooms sold must be between 0 and available")
    return _q(Decimal(rooms_sold) * 100 / rooms_available)


def adr(room_revenue, rooms_sold: int) -> Decimal:
    if rooms_sold <= 0:
        return Decimal("0.00")
    return _q(Decimal(room_revenue) / rooms_sold)


def revpar(room_revenue, rooms_available: int) -> Decimal:
    if rooms_available <= 0:
        raise ValidationError("METRIC_NO_INVENTORY", "Rooms available must be positive")
    return _q(Decimal(room_revenue) / rooms_available)
