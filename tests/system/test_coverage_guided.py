"""Coverage-guided tests: written after the first full run's coverage report showed
these statements/branches were never executed (gap analysis from reports/coverage.json).
"""
from datetime import datetime

from fastapi.testclient import TestClient

from app.domain import validation as v
from app.domain.errors import ValidationError
from app.main import create_app
from app.services import Clock
from tests.tclib import tc

CG = dict(level="System", technique="Coverage-guided (closes uncovered branch)", priority="P2", type="Negative")
CARD = {"method": "card", "number": "4111111111111111", "exp_month": 12, "exp_year": 2030, "cvv": "123"}
STAY = {"room_type": "DELUXE", "check_in": "2026-11-02", "check_out": "2026-11-05", "adults": 1}


def _book(client, auth, **over):
    return client.post("/api/bookings", json={**STAY, **over}, headers=auth).json()


@tc("TC-COV-001", "Paying an already CONFIRMED booking with a new key → HTTP 409 TRANSITION_INVALID",
    module="Payment", requirement="FR-09", inputs="second pay, different Idempotency-Key",
    expected="409 TRANSITION_INVALID (StateError handler)", **CG)
def test_pay_twice_409(client, auth):
    b = _book(client, auth)
    assert client.post(f"/api/bookings/{b['id']}/pay", json=CARD, headers={**auth, "Idempotency-Key": "a"}).status_code == 200
    r = client.post(f"/api/bookings/{b['id']}/pay", json=CARD, headers={**auth, "Idempotency-Key": "b"})
    assert r.status_code == 409 and r.json()["error"] == "TRANSITION_INVALID"


@tc("TC-COV-002", "Idempotency-Key reused for a different booking → 422 IDEMPOTENCY_REUSED",
    module="Payment", requirement="FR-08", inputs="same key on booking #1 and #2", expected="422", **CG)
def test_key_reuse(client, auth):
    b1, b2 = _book(client, auth), _book(client, auth)
    client.post(f"/api/bookings/{b1['id']}/pay", json=CARD, headers={**auth, "Idempotency-Key": "shared"})
    r = client.post(f"/api/bookings/{b2['id']}/pay", json=CARD, headers={**auth, "Idempotency-Key": "shared"})
    assert r.status_code == 422 and r.json()["error"] == "IDEMPOTENCY_REUSED"


@tc("TC-COV-003", "Unsupported payment method 'cash' → 422 PAYMENT_METHOD",
    module="Payment", requirement="FR-08", inputs={"method": "cash"}, expected="422 PAYMENT_METHOD", **CG)
def test_bad_method(client, auth):
    b = _book(client, auth)
    r = client.post(f"/api/bookings/{b['id']}/pay", json={"method": "cash"}, headers={**auth, "Idempotency-Key": "c"})
    assert r.status_code == 422 and r.json()["error"] == "PAYMENT_METHOD"


@tc("TC-COV-004", "Fewer adults than rooms and more extra beds than rooms are refused at booking",
    module="Booking", requirement="FR-04, FR-05", inputs="rooms=2, adults=1; rooms=1, extra_beds=2",
    expected="422 ADULTS_MIN; 422 EXTRA_BED_COUNT", **CG)
def test_booking_guards(client, auth):
    r1 = client.post("/api/bookings", json={**STAY, "rooms": 2, "adults": 1}, headers=auth)
    r2 = client.post("/api/bookings", json={**STAY, "extra_beds": 2}, headers=auth)
    assert (r1.json()["error"], r2.json()["error"]) == ("ADULTS_MIN", "EXTRA_BED_COUNT")


@tc("TC-COV-005", "Check-in attempted after the stay window has ended → 409 CHECKIN_TOO_LATE",
    module="Check-in/Check-out", requirement="FR-09", inputs="stay 8→9 Oct, clock moved to 9 Oct",
    expected="409 CHECKIN_TOO_LATE", **CG)
def test_checkin_too_late(app, client, auth, admin_auth):
    b = _book(client, auth, check_in="2026-10-08", check_out="2026-10-09")
    client.post(f"/api/bookings/{b['id']}/pay", json=CARD, headers={**auth, "Idempotency-Key": "late"})
    app.state.svc.clock.fixed = datetime(2026, 10, 9, 9, 0)
    r = client.post(f"/api/bookings/{b['id']}/check-in", json={"id_verified": True}, headers=admin_auth)
    assert r.status_code == 409 and r.json()["error"] == "CHECKIN_TOO_LATE"


@tc("TC-COV-006", "Admin sets tier on a non-existent user → 404 NOT_FOUND",
    module="Administration", requirement="FR-13", inputs={"user_id": 999}, expected="404", **CG)
def test_tier_unknown_user(client, admin_auth):
    assert client.patch("/api/admin/users/999/tier", json={"tier": "GOLD"}, headers=admin_auth).status_code == 404


@tc("TC-COV-007", "Quote with an invalid bearer token is served anonymously (no tier discount, no error)",
    module="Pricing & Tax", requirement="FR-06", inputs={"Authorization": "Bearer forged"},
    expected="200, loyalty_discount 0", **CG)
def test_quote_forged_token(client):
    r = client.post("/api/quote", json={k: STAY[k] for k in ("room_type", "check_in", "check_out")},
                    headers={"Authorization": "Bearer forged"})
    assert r.status_code == 200 and r.json()["loyalty_discount"] == 0


@tc("TC-COV-008", "Admin expiry endpoint expires stale PENDING bookings", module="Booking Life-cycle",
    requirement="FR-09", inputs="1 booking, clock +20 min, POST /api/admin/expire-pending", expected="{expired: 1}", **CG)
def test_expire_endpoint(app, client, auth, admin_auth):
    _book(client, auth)
    app.state.svc.clock.fixed = datetime(2026, 10, 8, 10, 20)
    assert client.post("/api/admin/expire-pending", headers=admin_auth).json() == {"expired": 1}


@tc("TC-COV-009", "Restarting the app on an existing DB does not fail on the already-seeded admin",
    module="Platform", requirement="NFR-REL-02", inputs="create_app twice on the same file", expected="health 200",
    **{**CG, "type": "Recovery"})
def test_restart_seed(tmp_path):
    path = str(tmp_path / "x.db")
    create_app(path, Clock(datetime(2026, 10, 8, 10)))
    again = TestClient(create_app(path, Clock(datetime(2026, 10, 8, 10))))
    assert again.get("/api/health").status_code == 200


@tc("TC-COV-010", "Non-text name and phone values are rejected with type errors", module="Registration",
    requirement="FR-01", inputs={"name": 123, "phone": 9832288101}, expected="NAME_TYPE, PHONE_INVALID",
    **{**CG, "level": "Unit"})
def test_type_guards():
    for fn, val, code in ((v.validate_name, 123, "NAME_TYPE"), (v.validate_phone, 9832288101, "PHONE_INVALID")):
        try:
            fn(val)
            got = "ACCEPT"
        except ValidationError as e:
            got = e.code
        assert got == code
