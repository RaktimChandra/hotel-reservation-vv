"""Black-box: State Transition testing of the booking life-cycle (FR-09).

0-switch coverage: every (state, event) pair in the full 6 × 5 state table —
6 valid transitions and 24 invalid ones that must be rejected.
1-switch / path coverage: complete life-cycle sequences.
"""
import pytest

from app.domain import state as st
from app.domain.errors import StateError
from tests.tclib import cases

EVENTS = list(st.TRANSITIONS)

TABLE = []
for s in st.STATES:
    for e in EVENTS:
        target = st.TRANSITIONS[e].get(s)
        TABLE.append({
            "id": f"TC-STM-{len(TABLE) + 1:03d}",
            "title": (f"Valid: {s} --{e}--> {target}" if target else f"Invalid: '{e}' from {s} is rejected"),
            "inputs": {"state": s, "event": e},
            "expected": target or "TRANSITION_INVALID",
            "priority": "P1" if target else "P2",
        })

SEQUENCES = [
    ("Happy path: book → pay → check-in → check-out", ["pay", "check_in", "check_out"], "CHECKED_OUT"),
    ("Abandoned cart: unpaid booking expires", ["expire"], "EXPIRED"),
    ("Guest cancels before paying", ["cancel"], "CANCELLED"),
    ("Guest cancels after paying", ["pay", "cancel"], "CANCELLED"),
    ("Cannot cancel after check-in", ["pay", "check_in", "cancel"], "TRANSITION_INVALID"),
    ("Cannot pay twice", ["pay", "pay"], "TRANSITION_INVALID"),
    ("Expired booking cannot be paid", ["expire", "pay"], "TRANSITION_INVALID"),
    ("Final state CHECKED_OUT accepts nothing", ["pay", "check_in", "check_out", "check_in"], "TRANSITION_INVALID"),
]
SEQ = [{"id": f"TC-STM-SEQ-{i:03d}", "title": t, "inputs": {"from": "PENDING", "events": ev}, "expected": exp}
       for i, (t, ev, exp) in enumerate(SEQUENCES, 1)]


@pytest.mark.parametrize("c", cases(TABLE, module="Booking Life-cycle", requirement="FR-09",
                                    technique="State Transition (0-switch)"))
def test_state_table(c):
    try:
        got = st.next_state(c["inputs"]["state"], c["inputs"]["event"])
    except StateError as e:
        got = e.code
    assert got == c["expected"]


@pytest.mark.parametrize("c", cases(SEQ, module="Booking Life-cycle", requirement="FR-09",
                                    technique="State Transition (n-switch / path)", priority="P1"))
def test_state_sequences(c):
    s = c["inputs"]["from"]
    try:
        for e in c["inputs"]["events"]:
            s = st.next_state(s, e)
        got = s
    except StateError as e:
        got = e.code
    assert got == c["expected"]


def test_unknown_state_and_event():
    with pytest.raises(StateError) as e1:
        st.next_state("ON_HOLD", "pay")
    with pytest.raises(StateError) as e2:
        st.next_state("PENDING", "refund")
    assert (e1.value.code, e2.value.code) == ("STATE_UNKNOWN", "EVENT_UNKNOWN")


def test_final_states_have_no_exits():
    for s in st.FINAL_STATES:
        assert st.allowed_events(s) == []
