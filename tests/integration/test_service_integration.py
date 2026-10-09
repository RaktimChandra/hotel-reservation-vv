"""Integration testing: HotelService ↔ domain rules ↔ SQLite (bottom-up integration).

The payment gateway is a stub with fault-injection (top-down style stub), so
gateway failures can be simulated deterministically.
"""
import threading
from datetime import date, datetime, time, timedelta

import pytest

from app import gateway
from app.db import Database
from app.domain.errors import StateError, ValidationError
from app.services import AuthError, Clock, Forbidden, HotelService
from tests.tclib import cases, tc

NOW = datetime(2026, 10, 8, 10, 0)
CARD = {"number": "4111111111111111", "exp_month": 12, "exp_year": 2030, "cvv": "123"}
INT = dict(level="Integration", module="Booking", requirement="FR-05")


@pytest.fixture
def service(tmp_path):
    gateway.FAULT["mode"] = None
    s = HotelService(Database(str(tmp_path / "hrrs.db")), Clock(NOW))
    s.register("Front Desk Admin", "admin@hrrs.test", "9876543210", 30, "Admin@123", role="admin")
    yield s
    gateway.FAULT["mode"] = None


def guest(service, n=1, tier="NONE"):
    u = service.register(f"Guest Person {chr(64 + n)}", f"g{n}@mail.com", "9876500000", 25, "Hotel@2026", tier=tier)
    return u


def admin(service):
    return service.user_for_token(service.login("admin@hrrs.test", "Admin@123"))


CI, CO = date(2026, 11, 2), date(2026, 11, 5)


@tc("TC-INT-001", "Booking persists booking row + room allocation in DB", technique="Integration (bottom-up)",
    priority="P1", inputs={"room": "DELUXE", "dates": "2-5 Nov 2026"}, expected="status PENDING, 1 room allocated", **INT)
def test_booking_persisted(service):
    u = guest(service)
    b = service.create_booking(u, "DELUXE", CI, CO, adults=2)
    row = service.db.conn.execute("SELECT status FROM bookings WHERE id=?", (b["id"],)).fetchone()
    assert row["status"] == "PENDING" and len(b["room_numbers"]) == 1


@tc("TC-INT-002", "Availability decreases after a booking and returns after cancellation",
    technique="Integration (bottom-up)", priority="P1", inputs={"room": "SUITE"},
    expected="3 → 2 → 3 free suites", **INT)
def test_availability_round_trip(service):
    u = guest(service)
    before = len(service.free_rooms("SUITE", CI, CO))
    b = service.create_booking(u, "SUITE", CI, CO, adults=2)
    during = len(service.free_rooms("SUITE", CI, CO))
    service.cancel(u, b["id"])
    after = len(service.free_rooms("SUITE", CI, CO))
    assert (before, during, after) == (3, 2, 3)


@tc("TC-INT-003", "Overlapping stays share no room; back-to-back stays may reuse the same room",
    technique="Integration (bottom-up)", priority="P1",
    inputs={"A": "2-5 Nov", "B": "5-7 Nov (touching)", "C": "4-6 Nov (overlap)"},
    expected="B reuses A's room; C gets a different room", **INT)
def test_overlap_rules(service):
    u = guest(service)
    a = service.create_booking(u, "SUITE", CI, CO, adults=1)
    b = service.create_booking(u, "SUITE", CO, CO + timedelta(days=2), adults=1)
    c = service.create_booking(u, "SUITE", date(2026, 11, 4), date(2026, 11, 6), adults=1)
    assert a["room_numbers"] == b["room_numbers"]
    assert c["room_numbers"] != a["room_numbers"]


@tc("TC-INT-004", "Booking the last room fails with NO_AVAILABILITY once inventory is exhausted",
    technique="Integration (bottom-up)", priority="P1", inputs={"room": "SUITE", "bookings": 4},
    expected="3 succeed, 4th → NO_AVAILABILITY", **INT)
def test_inventory_exhausted(service):
    u = guest(service)
    for _ in range(3):
        service.create_booking(u, "SUITE", CI, CO)
    with pytest.raises(ValidationError) as e:
        service.create_booking(u, "SUITE", CI, CO)
    assert e.value.code == "NO_AVAILABILITY"


@pytest.mark.concurrency
@tc("TC-INT-005", "Concurrency: 20 threads race for 3 suites — exactly 3 bookings succeed (no overbooking)",
    technique="Integration / Concurrency", type="Reliability", priority="P1", module="Booking",
    requirement="FR-10", level="Integration", inputs={"threads": 20, "inventory": 3},
    expected="3 successes, 17 NO_AVAILABILITY, no room double-allocated")
def test_no_overbooking_under_race(service):
    users = [guest(service, n) for n in range(1, 21)]
    results, barrier = [], threading.Barrier(20)

    def attempt(u):
        barrier.wait()
        try:
            service.create_booking(u, "SUITE", CI, CO)
            results.append("ok")
        except ValidationError as e:
            results.append(e.code)

    threads = [threading.Thread(target=attempt, args=(u,)) for u in users]
    [t.start() for t in threads]
    [t.join() for t in threads]
    rooms = [r[0] for r in service.db.conn.execute("SELECT room_no FROM booking_rooms")]
    assert results.count("ok") == 3 and results.count("NO_AVAILABILITY") == 17
    assert len(rooms) == len(set(rooms)) == 3


@tc("TC-INT-006", "Payment confirms booking and stores only the masked card", technique="Integration (top-down, stubbed gateway)",
    priority="P1", module="Payment", requirement="FR-08", level="Integration", type="Functional",
    inputs={"card": "4111…1111"}, expected="CONFIRMED; payments.masked = '**** **** **** 1111'")
def test_payment_confirms(service):
    u = guest(service)
    b = service.create_booking(u, "STANDARD", CI, CO)
    r = service.pay(u, b["id"], "card", CARD, "key-1")
    masked = service.db.conn.execute("SELECT masked FROM payments").fetchone()[0]
    assert r["booking"]["status"] == "CONFIRMED" and masked == "**** **** **** 1111"
    dump = "\n".join(service.db.conn.iterdump())
    assert "4111111111111111" not in dump and "123'" not in dump.split("payments")[-1][:200]


@tc("TC-INT-007", "Idempotency: replaying the same Idempotency-Key does not double-charge",
    technique="Integration", type="Reliability", priority="P1", module="Payment", requirement="FR-08",
    level="Integration", inputs={"key": "same key twice"}, expected="1 payment row; second response replayed=True")
def test_idempotent_payment(service):
    u = guest(service)
    b = service.create_booking(u, "STANDARD", CI, CO)
    first = service.pay(u, b["id"], "card", CARD, "dup-key")
    second = service.pay(u, b["id"], "card", CARD, "dup-key")
    n = service.db.conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    assert (first["replayed"], second["replayed"], n) == (False, True, 1)


@pytest.mark.recovery
@tc("TC-INT-008", "Recovery: gateway timeout leaves booking PENDING; retry succeeds after recovery",
    technique="Fault Injection", type="Recovery", priority="P1", module="Payment", requirement="FR-08",
    level="Integration", inputs={"fault": "timeout then none"}, expected="GatewayError, still PENDING, retry → CONFIRMED")
def test_gateway_timeout_recovery(service):
    u = guest(service)
    b = service.create_booking(u, "STANDARD", CI, CO)
    gateway.FAULT["mode"] = "timeout"
    with pytest.raises(gateway.GatewayError):
        service.pay(u, b["id"], "card", CARD, "k-timeout")
    assert service.get_booking(u, b["id"])["status"] == "PENDING"
    assert service.db.conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0
    gateway.FAULT["mode"] = None
    assert service.pay(u, b["id"], "card", CARD, "k-timeout")["booking"]["status"] == "CONFIRMED"


@pytest.mark.recovery
@tc("TC-INT-009", "Recovery: data survives a process restart (new service on the same DB file)",
    technique="Fault Injection", type="Recovery", priority="P2", module="Booking", requirement="NFR-REL-02",
    level="Integration", inputs={"restart": "re-open DB"}, expected="Booking still CONFIRMED after restart")
def test_restart_persistence(service, tmp_path):
    u = guest(service)
    b = service.create_booking(u, "STANDARD", CI, CO)
    service.pay(u, b["id"], "card", CARD, "k-restart")
    reborn = HotelService(Database(service.db.path), Clock(NOW))
    assert reborn.get_booking(admin(reborn), b["id"])["status"] == "CONFIRMED"


@tc("TC-INT-010", "Unpaid booking older than 15 minutes cannot be paid and becomes EXPIRED",
    technique="Integration + State Transition", priority="P1", module="Booking Life-cycle", requirement="FR-09",
    level="Integration", inputs={"elapsed": "16 min"}, expected="PAYMENT_WINDOW_EXPIRED; status EXPIRED; room released")
def test_payment_window(service):
    u = guest(service)
    b = service.create_booking(u, "SUITE", CI, CO)
    service.clock.fixed = NOW + timedelta(minutes=16)
    with pytest.raises(StateError) as e:
        service.pay(u, b["id"], "card", CARD, "late")
    assert e.value.code == "PAYMENT_WINDOW_EXPIRED"
    assert service.get_booking(u, b["id"])["status"] == "EXPIRED"
    assert len(service.free_rooms("SUITE", CI, CO)) == 3


@tc("TC-INT-011", "Expiry job expires only PENDING bookings older than 15 min",
    technique="Integration", priority="P2", module="Booking Life-cycle", requirement="FR-09", level="Integration",
    inputs={"bookings": "1 old pending, 1 new pending, 1 paid"}, expected="exactly 1 expired")
def test_expiry_job(service):
    u = guest(service)
    old = service.create_booking(u, "STANDARD", CI, CO)
    paid = service.create_booking(u, "STANDARD", CI, CO)
    service.pay(u, paid["id"], "card", CARD, "p1")
    service.clock.fixed = NOW + timedelta(minutes=20)
    new = service.create_booking(u, "STANDARD", CI, CO)
    assert service.expire_pending() == 1
    statuses = [service.get_booking(u, x["id"])["status"] for x in (old, paid, new)]
    assert statuses == ["EXPIRED", "CONFIRMED", "PENDING"]


@tc("TC-INT-012", "Cancellation 3 days before check-in applies 50 % refund minus ₹200 fee end-to-end",
    technique="Integration + Decision Table", priority="P1", module="Cancellation", requirement="FR-07",
    level="Integration", inputs={"days_before": 3, "tier": "NONE"}, expected="refund = 0.5 × total − 200")
def test_cancel_refund_integration(service):
    u = guest(service)
    b = service.create_booking(u, "DELUXE", date(2026, 10, 11), date(2026, 10, 13))
    service.pay(u, b["id"], "card", CARD, "c1")
    r = service.cancel(u, b["id"])
    assert r["rule"] == "R4" and r["refund"] == round(b["total"] * 0.5 - 200, 2)


@tc("TC-INT-013", "PLATINUM tier read from the DB changes the refund rule (75 %, no fee)",
    technique="Integration + Decision Table", priority="P2", module="Cancellation", requirement="FR-07",
    level="Integration", inputs={"days_before": 3, "tier": "PLATINUM"}, expected="rule R5, refund 75 %")
def test_cancel_platinum(service):
    u = guest(service, tier="PLATINUM")
    b = service.create_booking(u, "DELUXE", date(2026, 10, 11), date(2026, 10, 13))
    service.pay(u, b["id"], "card", CARD, "c2")
    r = service.cancel(u, b["id"])
    assert r["rule"] == "R5" and r["refund"] == round(b["total"] * 0.75, 2)


@tc("TC-INT-014", "Loyalty tier stored on the user is applied to the booking price",
    technique="Integration", priority="P2", module="Pricing & Tax", requirement="FR-06", level="Integration",
    inputs={"tier": "GOLD"}, expected="discount = 10 % of subtotal")
def test_tier_discount_applied(service):
    u = guest(service, tier="GOLD")
    b = service.create_booking(u, "STANDARD", CI, CO)
    assert b["discount"] == round(b["subtotal"] * 0.10, 2)


@tc("TC-INT-015", "Security: guest cannot read another guest's booking (IDOR) — Forbidden",
    technique="Integration", type="Security", priority="P1", module="Security", requirement="NFR-SEC-03",
    level="Integration", inputs={"actor": "guest B", "target": "guest A booking"}, expected="Forbidden")
def test_idor(service):
    a, b = guest(service, 1), guest(service, 2)
    bk = service.create_booking(a, "STANDARD", CI, CO)
    with pytest.raises(Forbidden):
        service.get_booking(b, bk["id"])
    assert service.get_booking(admin(service), bk["id"])["id"] == bk["id"]


LOGIN_DT = [
    ("Unknown e-mail", "nobody@mail.com", "Hotel@2026", 0, "AUTH_FAILED"),
    ("Known e-mail, correct password", "g1@mail.com", "Hotel@2026", 0, "TOKEN"),
    ("Wrong password, 1st failure", "g1@mail.com", "Wrong@2026", 0, "AUTH_FAILED"),
    ("Wrong password, 3rd consecutive failure → lock", "g1@mail.com", "Wrong@2026", 2, "ACCOUNT_LOCKED"),
    ("Correct password while locked", "g1@mail.com", "Hotel@2026", 3, "ACCOUNT_LOCKED"),
    ("Correct password after lock expires (16 min)", "g1@mail.com", "Hotel@2026", "expired", "TOKEN"),
]
LOGIN_ROWS = [{"id": f"TC-AUTH-DT-{i:03d}", "title": f"Login decision table: {t}",
               "inputs": {"email": e, "password": p, "prior_failures": f}, "expected": x}
              for i, (t, e, p, f, x) in enumerate(LOGIN_DT, 1)]


@pytest.mark.parametrize("c", cases(LOGIN_ROWS, module="Authentication", requirement="FR-02", level="Integration",
                                    technique="Decision Table", type="Security", priority="P1"))
def test_login_decision_table(service, c):
    guest(service)
    i = c["inputs"]
    prior = i["prior_failures"]
    n = 3 if prior == "expired" else prior
    for _ in range(n):
        try:
            service.login("g1@mail.com", "Wrong@2026")
        except AuthError:
            pass
    if prior == "expired":
        service.clock.fixed = NOW + timedelta(minutes=16)
    try:
        got = "TOKEN" if service.login(i["email"], i["password"]) else "?"
    except AuthError as e:
        got = e.code
    assert got == c["expected"]


@tc("TC-INT-016", "Passwords are stored as salted PBKDF2 hashes, never plaintext",
    technique="Integration", type="Security", priority="P1", module="Security", requirement="NFR-SEC-01",
    level="Integration", inputs={"password": "Hotel@2026"}, expected="hash starts 'pbkdf2$'; two users differ")
def test_password_hashing(service):
    guest(service, 1)
    guest(service, 2)
    hashes = [r[0] for r in service.db.conn.execute("SELECT password_hash FROM users WHERE role='guest'")]
    assert all(h.startswith("pbkdf2$120000$") for h in hashes) and hashes[0] != hashes[1]
    assert all("Hotel@2026" not in h for h in hashes)


@tc("TC-INT-017", "Audit log records register, login, booking, payment and cancel events",
    technique="Integration", type="Security", priority="P3", module="Security", requirement="NFR-SEC-05",
    level="Integration", inputs="full flow", expected="5 distinct audit actions")
def test_audit_log(service):
    u = guest(service)
    service.login("g1@mail.com", "Hotel@2026")
    b = service.create_booking(u, "STANDARD", CI, CO)
    service.pay(u, b["id"], "card", CARD, "a1")
    service.cancel(u, b["id"])
    actions = {r[0] for r in service.db.conn.execute("SELECT action FROM audit_log")}
    assert {"register", "login", "booking_created", "payment", "cancel"} <= actions


@tc("TC-INT-018", "Check-in requires verified ID and the arrival date; check-out after 15:00 charges 50 %",
    technique="Integration + State Transition", priority="P1", module="Check-in/Check-out", requirement="FR-14",
    level="Integration", inputs={"id_verified": "False then True", "check_out": "16:30"},
    expected="ID_NOT_VERIFIED, then CHECKED_IN, then CHECKED_OUT with late_fee = 50 % of nightly")
def test_checkin_checkout(service):
    u = guest(service)
    b = service.create_booking(u, "DELUXE", date(2026, 10, 8), date(2026, 10, 10))
    service.pay(u, b["id"], "card", CARD, "ci")
    adm = admin(service)
    with pytest.raises(ValidationError):
        service.check_in(adm, b["id"], id_verified=False)
    assert service.check_in(adm, b["id"], id_verified=True)["status"] == "CHECKED_IN"
    out = service.check_out(adm, b["id"], time(16, 30))
    assert out["status"] == "CHECKED_OUT" and out["late_fee"] == round(b["subtotal"] / 2 * 0.5, 2)


@tc("TC-INT-019", "Check-in before arrival date is refused", technique="Integration + State Transition",
    priority="P2", module="Check-in/Check-out", requirement="FR-09", level="Integration",
    inputs={"today": "8 Oct", "check_in": "2 Nov"}, expected="CHECKIN_TOO_EARLY")
def test_checkin_too_early(service):
    u = guest(service)
    b = service.create_booking(u, "DELUXE", CI, CO)
    service.pay(u, b["id"], "card", CARD, "early")
    with pytest.raises(StateError) as e:
        service.check_in(admin(service), b["id"], True)
    assert e.value.code == "CHECKIN_TOO_EARLY"


@tc("TC-INT-020", "Occupancy, ADR and RevPAR computed from confirmed bookings in the DB",
    technique="Integration", priority="P2", module="Reports", requirement="FR-12", level="Integration",
    inputs={"bookings": "2 STANDARD + 1 SUITE confirmed for 2 Nov (Mon)"},
    expected="occupancy 15 %, ADR = revenue/3, RevPAR = revenue/20")
def test_metrics(service):
    u = guest(service)
    for room, rooms in (("STANDARD", 2), ("SUITE", 1)):
        b = service.create_booking(u, room, CI, CO, rooms=rooms, adults=rooms)
        service.pay(u, b["id"], "card", CARD, f"m-{room}")
    unpaid = service.create_booking(u, "DELUXE", CI, CO)  # PENDING — must not count
    m = service.metrics(CI)
    revenue = 2 * 2500 + 7500
    assert unpaid["status"] == "PENDING"
    assert (m["rooms_sold"], m["occupancy_pct"], m["revenue"]) == (3, 15.0, revenue)
    assert m["adr"] == round(revenue / 3, 2) and m["revpar"] == round(revenue / 20, 2)


@tc("TC-INT-021", "Party split across rooms: 5 adults + 2 children in 2 FAMILY rooms is accepted",
    technique="Integration", priority="P2", module="Booking", requirement="FR-04", level="Integration",
    inputs={"rooms": 2, "adults": 5, "children": 2}, expected="Booking created with 2 rooms")
def test_party_split(service):
    u = guest(service)
    assert len(service.create_booking(u, "FAMILY", CI, CO, rooms=2, adults=5, children=2)["room_numbers"]) == 2


@tc("TC-INT-022", "Party too large for the rooms requested is refused",
    technique="Integration", priority="P2", module="Booking", requirement="FR-04", level="Integration",
    inputs={"rooms": 1, "room": "STANDARD", "adults": 2, "children": 1}, expected="OCCUPANCY_EXCEEDED")
def test_party_too_large(service):
    u = guest(service)
    with pytest.raises(ValidationError) as e:
        service.create_booking(u, "STANDARD", CI, CO, rooms=1, adults=2, children=1)
    assert e.value.code == "OCCUPANCY_EXCEEDED"


@tc("TC-INT-023", "Duplicate e-mail registration is rejected (case-insensitive)",
    technique="Integration", priority="P1", module="Registration", requirement="FR-01", level="Integration",
    inputs={"email": "G1@MAIL.COM after g1@mail.com"}, expected="EMAIL_TAKEN")
def test_duplicate_email(service):
    guest(service)
    with pytest.raises(ValidationError) as e:
        service.register("Another Person", "G1@MAIL.COM", "9876500001", 30, "Hotel@2026")
    assert e.value.code == "EMAIL_TAKEN"


@tc("TC-INT-024", "Declined card leaves no payment record and booking stays PENDING",
    technique="Fault Injection", type="Recovery", priority="P2", module="Payment", requirement="FR-08",
    level="Integration", inputs={"fault": "decline"}, expected="GatewayError; 0 payments; PENDING")
def test_gateway_decline(service):
    u = guest(service)
    b = service.create_booking(u, "STANDARD", CI, CO)
    gateway.FAULT["mode"] = "decline"
    with pytest.raises(gateway.GatewayError):
        service.pay(u, b["id"], "upi", {"vpa": "raktim@okaxis"}, "dec")
    assert service.get_booking(u, b["id"])["status"] == "PENDING"


@pytest.mark.security
@tc("TC-INT-025", "SA-01 hardening: dynamic UPDATE only accepts allow-listed columns",
    technique="White-box negative test (static-analysis follow-up)", type="Security", priority="P3",
    module="Security", requirement="NFR-SEC-02", level="Integration",
    inputs={"column": "status; DROP TABLE users"}, expected="ValueError; table intact")
def test_update_allow_list(service):
    u = guest(service)
    b = service.create_booking(u, "STANDARD", CI, CO)
    with pytest.raises(ValueError):
        service._transition(b["id"], "pay", **{"status; DROP TABLE users": 1})
    assert service.db.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
