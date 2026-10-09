"""Booking life-cycle state machine (FR-09)."""
from .errors import StateError

PENDING, CONFIRMED, CHECKED_IN, CHECKED_OUT, CANCELLED, EXPIRED = (
    "PENDING", "CONFIRMED", "CHECKED_IN", "CHECKED_OUT", "CANCELLED", "EXPIRED")

STATES = (PENDING, CONFIRMED, CHECKED_IN, CHECKED_OUT, CANCELLED, EXPIRED)
FINAL_STATES = {CHECKED_OUT, CANCELLED, EXPIRED}

# event -> {from_state: to_state}
TRANSITIONS = {
    "pay": {PENDING: CONFIRMED},
    "expire": {PENDING: EXPIRED},
    "cancel": {PENDING: CANCELLED, CONFIRMED: CANCELLED},
    "check_in": {CONFIRMED: CHECKED_IN},
    "check_out": {CHECKED_IN: CHECKED_OUT},
}

PAYMENT_WINDOW_MINUTES = 15


def next_state(current: str, event: str) -> str:
    if current not in STATES:
        raise StateError("STATE_UNKNOWN", f"Unknown state {current!r}")
    if event not in TRANSITIONS:
        raise StateError("EVENT_UNKNOWN", f"Unknown event {event!r}")
    table = TRANSITIONS[event]
    if current not in table:
        raise StateError("TRANSITION_INVALID", f"Cannot {event} a booking that is {current}")
    return table[current]


def allowed_events(current: str) -> list[str]:
    return [e for e, t in TRANSITIONS.items() if current in t]
