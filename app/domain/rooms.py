"""Room catalogue (FR-04)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RoomType:
    code: str
    name: str
    capacity: int          # max occupants (adults + children), excluding extra bed
    base_rate: int         # INR per night
    extra_bed_allowed: bool


ROOM_TYPES = {
    "STANDARD": RoomType("STANDARD", "Standard Room", 2, 2500, False),
    "DELUXE": RoomType("DELUXE", "Deluxe Room", 3, 4000, True),
    "FAMILY": RoomType("FAMILY", "Family Room", 6, 6000, False),
    "SUITE": RoomType("SUITE", "Executive Suite", 4, 7500, True),
}

EXTRA_BED_RATE = 800        # INR per night
EXTRA_BED_CAPACITY = 1      # one extra occupant per extra bed


def get_room_type(code: str) -> RoomType:
    from .errors import ValidationError

    if not isinstance(code, str) or code.upper() not in ROOM_TYPES:
        raise ValidationError("ROOM_TYPE_INVALID", f"Unknown room type: {code!r}")
    return ROOM_TYPES[code.upper()]
