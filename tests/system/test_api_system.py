"""System testing through the public REST API (black-box, whole application).

Covers functional end-to-end flows, API contract, negative/robustness,
security (OWASP-oriented), recovery and smoke/sanity suites.
"""

import pytest

from app import gateway
from tests.conftest import GUEST, make_guest
from tests.tclib import cases, tc

S = dict(level="System")
CARD = {"method": "card", "number": "4111111111111111", "exp_month": 12, "exp_year": 2030, "cvv": "123"}
STAY = {"room_type": "DELUXE", "check_in": "2026-11-02", "check_out": "2026-11-05", "adults": 2}


def book(client, auth, **over):
    r = client.post("/api/bookings", json={**STAY, **over}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def pay(client, auth, bid, key="k"):
    return client.post(f"/api/bookings/{bid}/pay", json=CARD, headers={**auth, "Idempotency-Key": key})


# ===================================================================== smoke
@pytest.mark.smoke
@tc("TC-SYS-SMK-001", "Smoke: health endpoint up and DB reachable", module="Platform", requirement="NFR-AVL-01",
    technique="Smoke", type="Smoke", priority="P1", inputs="GET /api/health", expected="200 {status: ok}", **S)
def test_smoke_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.smoke
@tc("TC-SYS-SMK-002", "Smoke: web UI served at /", module="Platform", requirement="NFR-USE-01", technique="Smoke",
    type="Smoke", priority="P1", inputs="GET /", expected="200 text/html with booking form", **S)
def test_smoke_ui(client):
    r = client.get("/")
    assert r.status_code == 200 and "search-form" in r.text


@pytest.mark.smoke
@tc("TC-SYS-SMK-003", "Smoke: room catalogue lists 4 room types", module="Room Catalogue", requirement="FR-04",
    technique="Smoke", type="Smoke", priority="P1", inputs="GET /api/rooms/types", expected="4 types", **S)
def test_smoke_rooms(client):
    assert {r["code"] for r in client.get("/api/rooms/types").json()} == {"STANDARD", "DELUXE", "FAMILY", "SUITE"}


# ===================================================================== functional flows
@pytest.mark.smoke
@tc("TC-SYS-FN-001", "Happy path: register → login → search → quote → book → pay → confirmed",
    module="Booking", requirement="FR-01..FR-09", technique="Use-case / Scenario", priority="P1",
    preconditions="Fresh system", inputs=STAY, expected="Each step 2xx; final status CONFIRMED", **S)
def test_happy_path(client, auth):
    avail = client.get("/api/availability", params={"check_in": "2026-11-02", "check_out": "2026-11-05"}).json()
    assert {a["room_type"]: a["available"] for a in avail} == {"STANDARD": 8, "DELUXE": 6, "FAMILY": 3, "SUITE": 3}
    q = client.post("/api/quote", json={k: STAY[k] for k in ("room_type", "check_in", "check_out")}, headers=auth).json()
    b = book(client, auth)
    assert b["total"] == q["total"] == 12600.0   # 3 weekday nights × ₹4000 + 5 % GST
    r = pay(client, auth, b["id"])
    assert r.status_code == 200 and r.json()["booking"]["status"] == "CONFIRMED"
    assert client.get("/api/bookings", headers=auth).json()[0]["status"] == "CONFIRMED"


@tc("TC-SYS-FN-002", "Quote shows weekend + peak surcharges, long-stay discount and 18 % GST for suite+bed",
    module="Pricing & Tax", requirement="FR-06", technique="Use-case / Scenario", priority="P1",
    inputs={"room": "SUITE", "extra_beds": 1, "stay": "20 Dec 2026 → 3 Jan 2027 (14 nights)"},
    expected="gst_rate 0.18; long-stay 15 %; total = taxable + gst", **S)
def test_quote_peak(client):
    q = client.post("/api/quote", json={"room_type": "SUITE", "check_in": "2026-12-20", "check_out": "2027-01-03",
                                         "extra_beds": 1}).json()
    assert q["gst_rate"] == 0.18 and q["nights"] == 14
    assert q["long_stay_discount"] == round(q["subtotal"] * 0.15, 2)
    assert round(q["taxable"] + q["gst"], 2) == q["total"]
    assert all(line["multiplier"] >= 1.3 for line in q["night_lines"])


@tc("TC-SYS-FN-003", "Promo FLAT500 reduces payable total by ₹500 before GST", module="Pricing & Tax",
    requirement="FR-06", technique="Use-case / Scenario", priority="P2",
    inputs={"promo": "FLAT500", "subtotal": "≥ ₹5000"}, expected="discount 500", **S)
def test_promo_flat(client, auth):
    b = book(client, auth, promo="FLAT500")
    assert b["discount"] == 500.0


@tc("TC-SYS-FN-004", "Guest lists only their own bookings; admin lists all", module="Booking History", requirement="FR-11",
    technique="Use-case / Scenario", priority="P2", inputs="2 guests, 1 booking each", expected="1, 1, 2", **S)
def test_listing_scope(client, auth, admin_auth):
    other, _ = make_guest(client, 7)
    book(client, auth)
    book(client, other)
    assert len(client.get("/api/bookings", headers=auth).json()) == 1
    assert len(client.get("/api/bookings", headers=other).json()) == 1
    assert len(client.get("/api/bookings", headers=admin_auth).json()) == 2


@tc("TC-SYS-FN-005", "Full stay: admin checks in and checks out a confirmed booking", module="Check-in/Check-out",
    requirement="FR-09", technique="Use-case / Scenario", priority="P1",
    inputs={"stay": "8-10 Oct", "checkout": "11:00"}, expected="CHECKED_IN → CHECKED_OUT, late fee 0", **S)
def test_full_stay(client, auth, admin_auth):
    b = book(client, auth, check_in="2026-10-08", check_out="2026-10-10")
    pay(client, auth, b["id"])
    assert client.post(f"/api/bookings/{b['id']}/check-in", json={"id_verified": True},
                       headers=admin_auth).json()["status"] == "CHECKED_IN"
    out = client.post(f"/api/bookings/{b['id']}/check-out", json={"at": "11:00:00"}, headers=admin_auth).json()
    assert out["status"] == "CHECKED_OUT" and out["late_fee"] == 0


@tc("TC-SYS-FN-006", "Hotel-initiated cancellation (admin) refunds 100 % and issues voucher",
    module="Cancellation", requirement="FR-07", technique="Use-case / Scenario", priority="P2",
    inputs={"hotel_initiated": True}, expected="refund = total, voucher True", **S)
def test_hotel_cancel(client, auth, admin_auth):
    b = book(client, auth, check_in="2026-10-09", check_out="2026-10-10")
    pay(client, auth, b["id"])
    r = client.post(f"/api/bookings/{b['id']}/cancel", json={"hotel_initiated": True}, headers=admin_auth).json()
    assert r["refund"] == b["total"] and r["voucher"] is True and r["rule"] == "R1"


@tc("TC-SYS-FN-007", "Admin metrics endpoint returns occupancy/ADR/RevPAR", module="Reports", requirement="FR-12",
    technique="Use-case / Scenario", priority="P3", inputs="1 confirmed DELUXE on 2 Nov", expected="occupancy 5 %", **S)
def test_metrics_api(client, auth, admin_auth):
    pay(client, auth, book(client, auth)["id"])
    m = client.get("/api/admin/metrics", params={"day": "2026-11-02"}, headers=admin_auth).json()
    assert m["occupancy_pct"] == 5.0 and m["adr"] == 4000.0 and m["revpar"] == 200.0


# ===================================================================== API contract & negative
NEG = [
    ("Register with weak password → 422 PWD_NO_SPECIAL", "post", "/api/auth/register",
     {**GUEST, "email": "w@x.in", "password": "Hotel2026"}, None, 422, "PWD_NO_SPECIAL"),
    ("Register under-age guest → 422 AGE_UNDER", "post", "/api/auth/register",
     {**GUEST, "email": "kid@x.in", "age": 17}, None, 422, "AGE_UNDER"),
    ("Availability with check-out before check-in → 422", "get",
     "/api/availability?check_in=2026-11-05&check_out=2026-11-02", None, None, 422, "STAY_TOO_SHORT"),
    ("Availability in the past → 422 CHECKIN_PAST", "get",
     "/api/availability?check_in=2026-10-01&check_out=2026-10-03", None, None, 422, "CHECKIN_PAST"),
    ("Malformed date → 422 schema error", "get", "/api/availability?check_in=02-11-2026&check_out=x",
     None, None, 422, None),
    ("Booking without token → 401 AUTH_REQUIRED", "post", "/api/bookings", STAY, None, 401, "AUTH_REQUIRED"),
    ("Booking with bogus token → 401", "post", "/api/bookings", STAY, {"Authorization": "Bearer nope"}, 401,
     "AUTH_REQUIRED"),
    ("Unknown booking id → 404", "get", "/api/bookings/9999", None, "admin", 404, "NOT_FOUND"),
    ("Unknown route → 404", "get", "/api/nothing-here", None, None, 404, None),
    ("Wrong HTTP method → 405", "delete", "/api/rooms/types", None, None, 405, None),
    ("Invalid JSON body → 422", "post_raw", "/api/auth/login", "{not json", None, 422, None),
    ("Room type unknown → 422 ROOM_TYPE_INVALID", "post", "/api/quote",
     {"room_type": "PENTHOUSE", "check_in": "2026-11-02", "check_out": "2026-11-03"}, None, 422, "ROOM_TYPE_INVALID"),
    ("6 rooms in one booking → 422 ROOMS_MAX", "post", "/api/bookings", {**STAY, "rooms": 6, "adults": 6}, "guest",
     422, "ROOMS_MAX"),
    ("Extra bed in STANDARD → 422", "post", "/api/bookings", {**STAY, "room_type": "STANDARD", "extra_beds": 1,
                                                                "adults": 1}, "guest", 422, "EXTRA_BED_NOT_ALLOWED"),
    ("Invalid promo → 422 PROMO_INVALID", "post", "/api/quote",
     {"room_type": "DELUXE", "check_in": "2026-11-02", "check_out": "2026-11-03", "promo": "FREE"}, None, 422,
     "PROMO_INVALID"),
    ("Admin metrics as guest → 403", "get", "/api/admin/metrics", None, "guest", 403, "FORBIDDEN"),
    ("Admin check-in as guest → 403", "post", "/api/bookings/1/check-in", {"id_verified": True}, "guest", 403,
     "FORBIDDEN"),
]
NEG_ROWS = [{"id": f"TC-SYS-NEG-{i:03d}", "title": t, "inputs": {"method": m.upper(), "path": p},
             "expected": f"HTTP {sc}" + (f" error={code}" if code else ""), "req": (m, p, body, who, sc, code)}
            for i, (t, m, p, body, who, sc, code) in enumerate(NEG, 1)]


@pytest.mark.parametrize("c", cases(NEG_ROWS, module="REST API", requirement="NFR-API-01", level="System",
                                    technique="Negative testing / API contract", type="Negative", priority="P2"))
def test_api_negative(client, auth, admin_auth, c):
    m, p, body, who, sc, code = c["req"]
    headers = auth if who == "guest" else admin_auth if who == "admin" else (who or {})
    if m == "post_raw":
        r = client.post(p, content=body, headers={"Content-Type": "application/json"})
    elif m in ("get", "delete"):
        r = getattr(client, m)(p, headers=headers)
    else:
        r = client.post(p, json=body, headers=headers)
    assert r.status_code == sc, r.text
    if code:
        assert r.json()["error"] == code


@tc("TC-SYS-API-001", "OpenAPI contract published and lists every business endpoint", module="REST API",
    requirement="NFR-API-01", technique="Contract testing", type="Interface", priority="P2",
    inputs="GET /openapi.json", expected="≥ 15 operations incl. bookings/pay/cancel", **S)
def test_openapi_contract(client):
    spec = client.get("/openapi.json").json()
    ops = [(m.upper(), p) for p, item in spec["paths"].items() for m in item]
    assert len(ops) >= 15
    for path in ("/api/bookings", "/api/bookings/{booking_id}/pay", "/api/bookings/{booking_id}/cancel",
                 "/api/availability", "/api/quote"):
        assert path in spec["paths"]


@tc("TC-SYS-API-002", "Response schema: booking object has all contract fields with correct types",
    module="REST API", requirement="NFR-API-01", technique="Contract testing", type="Interface", priority="P2",
    inputs="POST /api/bookings", expected="ref str, total float, room_numbers list, allowed_actions list", **S)
def test_booking_schema(client, auth):
    b = book(client, auth)
    types = {"id": int, "ref": str, "status": str, "total": float, "gst": float, "room_numbers": list,
             "allowed_actions": list, "check_in": str, "refundable": bool}
    for k, t in types.items():
        assert isinstance(b[k], t), k
    assert b["ref"].startswith("HRR-") and len(b["ref"]) == 12


# ===================================================================== security
@pytest.mark.security
@tc("TC-SEC-001", "SQL injection in login e-mail is neutralised (parameterised queries)", module="Security",
    requirement="NFR-SEC-02", technique="Security – Injection (OWASP A03)", type="Security", priority="P1",
    inputs={"email": "' OR '1'='1' --"}, expected="401 AUTH_FAILED, no login", **S)
def test_sqli_login(client):
    r = client.post("/api/auth/login", json={"email": "' OR '1'='1' --", "password": "x"})
    assert r.status_code == 401 and r.json()["error"] == "AUTH_FAILED"


@pytest.mark.security
@tc("TC-SEC-002", "SQL injection in admin login password field fails", module="Security", requirement="NFR-SEC-02",
    technique="Security – Injection (OWASP A03)", type="Security", priority="P1",
    inputs={"email": "admin@hrrs.test", "password": "' OR 1=1 --"}, expected="401", **S)
def test_sqli_password(client):
    assert client.post("/api/auth/login", json={"email": "admin@hrrs.test", "password": "' OR 1=1 --"}).status_code == 401


@pytest.mark.security
@tc("TC-SEC-003", "Path parameter injection `1 OR 1=1` rejected by type validation", module="Security",
    requirement="NFR-SEC-02", technique="Security – Injection", type="Security", priority="P2",
    inputs="GET /api/bookings/1%20OR%201=1", expected="422", **S)
def test_sqli_path(client, auth):
    assert client.get("/api/bookings/1%20OR%201=1", headers=auth).status_code == 422


@pytest.mark.security
@tc("TC-SEC-004", "Stored XSS: script in name is rejected at input validation", module="Security",
    requirement="NFR-SEC-04", technique="Security – XSS (OWASP A03)", type="Security", priority="P1",
    inputs={"name": "<img src=x onerror=alert(1)>"}, expected="422 NAME_CHARS", **S)
def test_xss_rejected(client):
    r = client.post("/api/auth/register", json={**GUEST, "email": "x@x.in", "name": "<img src=x onerror=alert(1)>"})
    assert r.status_code == 422 and r.json()["error"] == "NAME_CHARS"


@pytest.mark.security
@tc("TC-SEC-005", "Broken access control: guest B cannot view, pay or cancel guest A's booking (IDOR)",
    module="Security", requirement="NFR-SEC-03", technique="Security – Access Control (OWASP A01)", type="Security",
    priority="P1", inputs="guest B uses guest A's booking id", expected="403 on GET, pay, cancel", **S)
def test_idor_api(client, auth):
    b = book(client, auth)
    other, _ = make_guest(client, 9)
    assert client.get(f"/api/bookings/{b['id']}", headers=other).status_code == 403
    assert pay(client, other, b["id"], "x").status_code == 403
    assert client.post(f"/api/bookings/{b['id']}/cancel", json={}, headers=other).status_code == 403
    assert client.get(f"/api/bookings/{b['id']}", headers=auth).json()["status"] == "PENDING"


@pytest.mark.security
@tc("TC-SEC-006", "Privilege escalation: guest cannot set own loyalty tier or force hotel-initiated refund",
    module="Security", requirement="FR-13, NFR-SEC-03", technique="Security – Access Control (OWASP A01)",
    type="Security", priority="P1", inputs="PATCH tier; cancel hotel_initiated=true as guest", expected="403, 403", **S)
def test_privilege_escalation(client, auth):
    me = client.get("/api/me", headers=auth).json()
    assert client.patch(f"/api/admin/users/{me['id']}/tier", json={"tier": "PLATINUM"}, headers=auth).status_code == 403
    b = book(client, auth)
    assert client.post(f"/api/bookings/{b['id']}/cancel", json={"hotel_initiated": True},
                       headers=auth).status_code == 403


@pytest.mark.security
@tc("TC-SEC-007", "Brute force: 3 wrong passwords lock the account (HTTP 423) even for the right password",
    module="Security", requirement="FR-02", technique="Security – Auth Failures (OWASP A07)", type="Security",
    priority="P1", inputs="3 × wrong password, then correct", expected="401, 401, 423, 423", **S)
def test_bruteforce_lockout(client, guest_token):
    codes = [client.post("/api/auth/login", json={"email": GUEST["email"], "password": "Wrong@123"}).status_code
             for _ in range(3)]
    codes.append(client.post("/api/auth/login", json={"email": GUEST["email"], "password": GUEST["password"]}).status_code)
    assert codes == [401, 401, 423, 423]


@pytest.mark.security
@tc("TC-SEC-008", "No user enumeration: unknown e-mail and wrong password give identical responses",
    module="Security", requirement="NFR-SEC-01", technique="Security – Auth Failures (OWASP A07)", type="Security",
    priority="P2", inputs="unknown e-mail vs wrong password", expected="same status and message", **S)
def test_no_enumeration(client, guest_token):
    a = client.post("/api/auth/login", json={"email": "ghost@x.in", "password": "Wrong@123"})
    b = client.post("/api/auth/login", json={"email": GUEST["email"], "password": "Wrong@123"})
    assert (a.status_code, a.json()) == (b.status_code, b.json())


@pytest.mark.security
@tc("TC-SEC-009", "Session invalid after logout", module="Security", requirement="NFR-SEC-01",
    technique="Security – Session Management", type="Security", priority="P2", inputs="logout then GET /api/me",
    expected="401", **S)
def test_logout(client, auth):
    assert client.get("/api/me", headers=auth).status_code == 200
    client.post("/api/auth/logout", headers=auth)
    assert client.get("/api/me", headers=auth).status_code == 401


@pytest.mark.security
@tc("TC-SEC-010", "Security headers present (CSP, X-Frame-Options, nosniff, Referrer-Policy)", module="Security",
    requirement="NFR-SEC-06", technique="Security – Misconfiguration (OWASP A05)", type="Security", priority="P2",
    inputs="GET /", expected="all four headers", **S)
def test_security_headers(client):
    h = client.get("/").headers
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in h["content-security-policy"] and h["referrer-policy"] == "no-referrer"


@pytest.mark.security
@tc("TC-SEC-011", "Sensitive data exposure: API never returns password hash, full card number or CVV",
    module="Security", requirement="NFR-SEC-01", technique="Security – Data Exposure (OWASP A02)", type="Security",
    priority="P1", inputs="register, login, book, pay responses", expected="no hash / PAN / CVV in any body", **S)
def test_no_sensitive_leak(client):
    bodies = [client.post("/api/auth/register", json=GUEST).text]
    login = client.post("/api/auth/login", json={"email": GUEST["email"], "password": GUEST["password"]})
    bodies.append(login.text)
    auth = {"Authorization": "Bearer " + login.json()["token"]}
    b = book(client, auth)
    bodies.append(pay(client, auth, b["id"]).text)
    bodies.append(client.get("/api/me", headers=auth).text)
    blob = "".join(bodies)
    assert "pbkdf2" not in blob and "password" not in blob.replace('"password_hash"', "")
    assert "4111111111111111" not in blob and '"cvv"' not in blob


@pytest.mark.security
@tc("TC-SEC-012", "Error responses do not leak stack traces or SQL", module="Security", requirement="NFR-SEC-06",
    technique="Security – Misconfiguration (OWASP A05)", type="Security", priority="P3",
    inputs="several invalid requests", expected="no 'Traceback' / 'sqlite' in bodies", **S)
def test_no_stack_traces(client, auth):
    texts = [client.post("/api/bookings", json={**STAY, "room_type": "X"}, headers=auth).text,
             client.get("/api/bookings/0", headers=auth).text,
             client.post("/api/auth/login", content="{", headers={"Content-Type": "application/json"}).text]
    assert not any("Traceback" in t or "sqlite" in t.lower() for t in texts)


@pytest.mark.security
@tc("TC-SEC-013", "Payment requires an Idempotency-Key header (replay protection)", module="Security",
    requirement="FR-08", technique="Security – Integrity", type="Security", priority="P2",
    inputs="POST pay without header", expected="422 IDEMPOTENCY_KEY", **S)
def test_idempotency_required(client, auth):
    b = book(client, auth)
    r = client.post(f"/api/bookings/{b['id']}/pay", json=CARD, headers=auth)
    assert r.status_code == 422 and r.json()["error"] == "IDEMPOTENCY_KEY"


# ===================================================================== recovery / reliability
@pytest.mark.recovery
@tc("TC-SYS-REC-001", "Gateway outage returns 502 and the booking can still be paid after recovery",
    module="Payment", requirement="NFR-REL-01", technique="Fault Injection", type="Recovery", priority="P1",
    inputs="FAULT=timeout, then FAULT=None", expected="502, then 200 CONFIRMED", **S)
def test_gateway_502(client, auth):
    b = book(client, auth)
    gateway.FAULT["mode"] = "timeout"
    assert pay(client, auth, b["id"], "r1").status_code == 502
    gateway.FAULT["mode"] = None
    assert pay(client, auth, b["id"], "r1").json()["booking"]["status"] == "CONFIRMED"


# ===================================================================== regression (one per fixed defect)
@pytest.mark.regression
@tc("TC-REG-RGN-001", "Regression for DEF-001: name with initial 'R. Chandra' can register via API",
    module="Registration", requirement="FR-01", technique="Regression", type="Regression", priority="P2",
    inputs={"name": "R. Chandra"}, expected="201 Created", **S)
def test_regression_def001(client):
    assert client.post("/api/auth/register", json={**GUEST, "name": "R. Chandra"}).status_code == 201


@tc("TC-SYS-FN-008", "Admin upgrades a guest to GOLD; the next quote applies the 10 % loyalty discount",
    module="Administration", requirement="FR-13", technique="Use-case / Scenario", priority="P2",
    inputs={"tier": "GOLD"}, expected="tier GOLD; loyalty_discount = 10 % of subtotal", **S)
def test_admin_sets_tier(client, auth, admin_auth):
    me = client.get("/api/me", headers=auth).json()
    r = client.patch(f"/api/admin/users/{me['id']}/tier", json={"tier": "gold"}, headers=admin_auth)
    assert r.status_code == 200 and r.json()["tier"] == "GOLD"
    q = client.post("/api/quote", json={k: STAY[k] for k in ("room_type", "check_in", "check_out")}, headers=auth).json()
    assert q["loyalty_discount"] == round(q["subtotal"] * 0.10, 2)
    bad = client.patch(f"/api/admin/users/{me['id']}/tier", json={"tier": "DIAMOND"}, headers=admin_auth)
    assert bad.status_code == 422 and bad.json()["error"] == "LOYALTY_INVALID"


@tc("TC-SYS-FN-009", "Availability counts drop for the dates of a confirmed booking only",
    module="Search & Availability", requirement="FR-03, FR-10", technique="Use-case / Scenario", priority="P2",
    inputs="DELUXE booked 2→5 Nov; search 3→4 Nov and 5→6 Nov", expected="5 free on 3 Nov, 6 free on 5 Nov", **S)
def test_availability_dates(client, auth):
    pay(client, auth, book(client, auth)["id"])
    a = {r["room_type"]: r["available"] for r in client.get(
        "/api/availability", params={"check_in": "2026-11-03", "check_out": "2026-11-04"}).json()}
    b = {r["room_type"]: r["available"] for r in client.get(
        "/api/availability", params={"check_in": "2026-11-05", "check_out": "2026-11-06"}).json()}
    assert a["DELUXE"] == 5 and b["DELUXE"] == 6
