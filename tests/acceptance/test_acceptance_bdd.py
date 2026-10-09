"""Acceptance testing (UAT) — executable Gherkin specifications via pytest-bdd."""
from datetime import date, timedelta

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.conftest import GUEST
from tests.tclib import tc

FEATURE = "features/booking.feature"
A = dict(level="Acceptance (UAT)", module="Booking", technique="BDD / Gherkin acceptance criteria",
         type="Acceptance", priority="P1")
TODAY = date(2026, 10, 8)


@tc("TC-UAT-001", "UAT-01 Guest books and pays for a deluxe room", requirement="FR-05, FR-08",
    inputs="DELUXE, 2→5 Nov, 2 adults, Visa", expected="CONFIRMED, ₹12,600.00 charged", **A)
@scenario(FEATURE, "Guest books and pays for a deluxe room")
def test_uat_book_and_pay():
    pass


@tc("TC-UAT-002", "UAT-02 The last suite cannot be sold twice", requirement="FR-10",
    inputs="3 suites pre-booked; overlapping request", expected="NO_AVAILABILITY", **A)
@scenario(FEATURE, "The last suite cannot be sold twice")
def test_uat_no_double_sale():
    pass


@tc("TC-UAT-003", "UAT-03 Refund depends on how early the guest cancels (3 examples)", requirement="FR-07",
    inputs="days 10 / 4 / 1", expected="100 % R3 / 50 % R4 / 0 % R6", **A)
@scenario(FEATURE, "Refund depends on how early the guest cancels")
def test_uat_refund_outline():
    pass


@tc("TC-UAT-004", "UAT-04 A non-refundable saver rate gives no refund", requirement="FR-07",
    inputs="non-refundable STANDARD, 20 days ahead", expected="0 % under R2", **A)
@scenario(FEATURE, "A non-refundable saver rate gives no refund")
def test_uat_non_refundable():
    pass


# ---------------------------------------------------------------- steps
@pytest.fixture
def ctx():
    return {}


@given("the hotel has 20 rooms and today is 8 October 2026")
def hotel(client, ctx):
    rooms = client.get("/api/availability", params={"check_in": "2026-11-02", "check_out": "2026-11-03"}).json()
    assert sum(r["available"] for r in rooms) == 20
    ctx["client"] = client


@given(parsers.parse('a registered guest "{name}" is signed in'))
def signed_in(client, ctx, name):
    body = {**GUEST, "name": name, "email": "uat@example.in"}
    client.post("/api/auth/register", json=body)
    tok = client.post("/api/auth/login", json={"email": body["email"], "password": body["password"]}).json()["token"]
    ctx["auth"] = {"Authorization": f"Bearer {tok}"}


def _reserve(ctx, room, ci, co, adults, refundable=True):
    r = ctx["client"].post("/api/bookings", json={"room_type": room, "check_in": ci, "check_out": co,
                                                  "adults": adults, "refundable": refundable}, headers=ctx["auth"])
    ctx["last"] = r
    if r.status_code == 201:
        ctx["booking"] = r.json()
    return r


@when(parsers.parse('the guest reserves {n:d} "{room}" room from "{ci}" to "{co}" for {adults:d} adults'))
@when(parsers.parse('the guest tries to reserve {n:d} "{room}" room from "{ci}" to "{co}" for {adults:d} adults'))
def reserve(ctx, n, room, ci, co, adults):
    _reserve(ctx, room, ci, co, adults)


@given(parsers.parse('every "{room}" is already booked from "{ci}" to "{co}"'))
def fill(ctx, room, ci, co):
    for _ in range(3):
        assert _reserve(ctx, room, ci, co, 1).status_code == 201


def _pay(ctx, number="4111111111111111"):
    b = ctx["booking"]
    r = ctx["client"].post(f"/api/bookings/{b['id']}/pay",
                           json={"method": "card", "number": number, "exp_month": 12, "exp_year": 2030, "cvv": "123"},
                           headers={**ctx["auth"], "Idempotency-Key": f"uat-{b['id']}"})
    assert r.status_code == 200, r.text
    ctx["booking"] = r.json()["booking"]


@when(parsers.parse('pays with card "{number}"'))
def pays(ctx, number):
    _pay(ctx, number)


@then(parsers.parse('the booking status is "{status}"'))
def status_is(ctx, status):
    assert ctx["booking"]["status"] == status


@then(parsers.parse("the amount charged is {amount:f} rupees"))
def charged(ctx, amount):
    assert ctx["booking"]["total"] == amount


@then(parsers.parse('the reservation is refused with "{code}"'))
def refused(ctx, code):
    assert ctx["last"].status_code == 422 and ctx["last"].json()["error"] == code


@given(parsers.parse('the guest holds a paid {kind} "{room}" booking starting {days:d} days from today'))
def paid_booking(ctx, kind, room, days):
    ci = TODAY + timedelta(days=days)
    assert _reserve(ctx, room, ci.isoformat(), (ci + timedelta(days=2)).isoformat(), 1,
                    refundable=(kind == "refundable")).status_code == 201
    _pay(ctx)


@when("the guest cancels the booking")
def cancel(ctx):
    ctx["cancel"] = ctx["client"].post(f"/api/bookings/{ctx['booking']['id']}/cancel", json={},
                                       headers=ctx["auth"]).json()


@then(parsers.parse('{percent:d} percent of the payment is refunded under rule "{rule}"'))
def refunded(ctx, percent, rule):
    c = ctx["cancel"]
    assert c["rule"] == rule and c["refund_pct"] == percent
