"""End-to-end UI testing with Playwright (real Chromium against a live uvicorn server).

Also: automated accessibility audit (axe-core, WCAG 2.1 A/AA rules), keyboard-only
operation, responsive / device-emulation compatibility, cross-browser matrix and
a stored-XSS rendering check. Every run records video and step screenshots.
"""
import json
import os
import shutil
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from app.main import create_app
from app.services import Clock
from tests.tclib import tc

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "reports" / "screenshots"
VIDEOS = ROOT / "reports" / "e2e_videos"
AXE = Path(__file__).resolve().parent / "vendor" / "axe.min.js"   # vendored axe-core 4.14.0 (MPL-2.0)
E = dict(level="System (E2E UI)", module="Web UI")


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server():
    app = create_app(":memory:", Clock(datetime(2026, 10, 8, 10, 0)))
    # seed one guest for login-only tests
    app.state.svc.register("Ananya Rao", "ananya@example.in", "9123456780", 21, "Hotel@2026")
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}", app
    srv.should_exit = True
    t.join(timeout=5)


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


def new_page(pw, name, browser="chromium", slow=0, **ctx):
    SHOTS.mkdir(parents=True, exist_ok=True)
    VIDEOS.mkdir(parents=True, exist_ok=True)
    # Live demo: HRRS_HEADED=1 opens a visible browser window; HRRS_SLOWMO=<ms> slows every action down.
    headed = os.environ.get("HRRS_HEADED") == "1"
    slow = max(slow, int(os.environ.get("HRRS_SLOWMO", "500" if headed else "0")))
    shutil.rmtree(VIDEOS / name, ignore_errors=True)       # keep only the latest recording per test
    b = getattr(pw, browser).launch(headless=not headed, slow_mo=slow)
    c = b.new_context(record_video_dir=str(VIDEOS / name), record_video_size={"width": 1280, "height": 800},
                      viewport=ctx.pop("viewport", {"width": 1280, "height": 800}), **ctx)
    page = c.new_page()
    return b, c, page


def shot(page, name):
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


def login(page, base, email="ananya@example.in", pwd="Hotel@2026"):  # noqa: S107 — test fixture credentials
    page.goto(base)
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(pwd)
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("who")).to_contain_text("Signed in")


@pytest.mark.e2e
@pytest.mark.smoke
@tc("TC-E2E-001", "Guest journey in the browser: register → sign in → search → price → reserve → pay → cancel",
    requirement="FR-01..FR-09", technique="End-to-end scenario (UI automation)", priority="P1",
    preconditions="Live server, empty inventory", inputs="Kabir Mehta, DELUXE, 2→5 Nov 2026, Visa 4111…",
    steps="1 Register 2 Sign in 3 Search 4 Select DELUXE 5 Get price 6 Reserve 7 Pay 8 Verify CONFIRMED 9 Cancel",
    expected="Status CONFIRMED then CANCELLED with refund rule R3", **E)
def test_full_guest_journey(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-001", slow=150)
    try:
        page.goto(base)
        shot(page, "01_home")
        page.get_by_test_id("tab-register").click()
        page.get_by_test_id("reg-name").fill("Kabir Mehta")
        page.get_by_test_id("reg-email").fill("kabir@example.in")
        page.get_by_test_id("reg-phone").fill("9876543201")
        page.get_by_test_id("reg-age").fill("21")
        page.get_by_test_id("reg-password").fill("Hotel@2026")
        page.get_by_test_id("reg-submit").click()
        expect(page.get_by_test_id("msg-ok")).to_contain_text("Account created")
        shot(page, "02_registered")
        page.get_by_test_id("login-password").fill("Hotel@2026")
        page.get_by_test_id("login-submit").click()
        expect(page.get_by_test_id("who")).to_contain_text("Kabir Mehta")
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        expect(page.get_by_test_id("room-DELUXE")).to_contain_text("6 left")
        shot(page, "03_search_results")
        page.get_by_test_id("select-DELUXE").click()
        page.get_by_test_id("adults").fill("2")
        page.get_by_test_id("quote-btn").click()
        expect(page.get_by_test_id("quote")).to_contain_text("₹12,600.00")
        shot(page, "04_quote")
        page.get_by_test_id("book-submit").click()
        expect(page.locator("#book-msg")).to_contain_text("Rooms held")
        page.get_by_test_id("card-number").fill("4111 1111 1111 1111")
        page.get_by_test_id("card-month").fill("12")
        page.get_by_test_id("card-year").fill("2030")
        page.get_by_test_id("card-cvv").fill("123")
        page.get_by_test_id("pay-submit").click()
        expect(page.locator("#pay-msg")).to_contain_text("CONFIRMED")
        expect(page.get_by_test_id("mine-body").get_by_test_id("status").first).to_have_text("CONFIRMED")
        shot(page, "05_paid")
        ref = page.get_by_test_id("pay-ref").inner_text()
        page.get_by_test_id(f"cancel-{ref}").click()
        expect(page.locator("#mine-msg")).to_contain_text("rule R3")
        expect(page.get_by_test_id("mine-body").get_by_test_id("status").first).to_have_text("CANCELLED")
        shot(page, "06_cancelled")
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@tc("TC-E2E-002", "UI shows a clear validation message for a weak password at registration",
    requirement="FR-02", technique="Negative UI test", type="Usability", priority="P2",
    inputs={"password": "hotel2026"}, expected="Error banner mentions PWD_NO_UPPER", **E)
def test_weak_password_message(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-002")
    try:
        page.goto(base)
        page.get_by_test_id("tab-register").click()
        for tid, val in (("reg-name", "Meera Iyer"), ("reg-email", "meera@example.in"),
                         ("reg-phone", "9876543202"), ("reg-age", "21"), ("reg-password", "hotel2026")):
            page.get_by_test_id(tid).fill(val)
        page.get_by_test_id("reg-submit").click()
        expect(page.get_by_test_id("msg-error")).to_contain_text("PWD_NO_UPPER")
        shot(page, "07_weak_password")
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@pytest.mark.security
@tc("TC-E2E-003", "Reflected/DOM XSS: server messages that echo user input are rendered as text, never executed",
    requirement="NFR-SEC-04", technique="Security – XSS (UI)", type="Security", priority="P1",
    inputs={"login email": "<img src=x onerror=window.pwned=1>", "promo code": "<img src=x onerror=window.pwned=2>"},
    expected="window.pwned undefined; no <img> injected in any status region",
    preconditions="Rev B (after fault-seeding SF-11): the promo path is used because its error message reflects input",
    **E)
def test_dom_xss(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-003")
    try:
        page.goto(base)
        page.evaluate("document.querySelector('[data-testid=login-email]').type='text'")
        page.get_by_test_id("login-email").fill("<img src=x onerror=window.pwned=1>")
        page.get_by_test_id("login-password").fill("whatever")
        page.get_by_test_id("login-submit").click()
        expect(page.get_by_test_id("msg-error")).to_be_visible()
        # promo-code error reflects the raw input back from the server: the real XSS vector
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        page.get_by_test_id("select-DELUXE").click()
        page.get_by_test_id("promo").fill("<img src=x onerror=window.pwned=2>")
        page.get_by_test_id("quote-btn").click()
        expect(page.locator("#book-msg")).to_contain_text("is not valid")
        page.wait_for_timeout(300)
        assert page.evaluate("window.pwned") is None
        assert page.locator("#auth-msg img, #book-msg img").count() == 0
        assert "<img" in page.locator("#book-msg").inner_text()      # shown literally as text
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@pytest.mark.a11y
@tc("TC-E2E-004", "Accessibility audit (axe-core, WCAG 2.1 A + AA rules) finds no serious/critical violations",
    requirement="NFR-USE-02", technique="Accessibility testing (automated)", type="Accessibility", priority="P2",
    inputs="Home page after search", expected="0 critical, 0 serious violations; report saved", **E)
def test_accessibility(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-004")
    try:
        page.goto(base)
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        expect(page.get_by_test_id("room-SUITE")).to_be_visible()
        page.add_script_tag(path=str(AXE))
        result = page.evaluate("""async () => await axe.run(document, {runOnly: {type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}})""")
        summary = {"passes": len(result["passes"]), "incomplete": len(result["incomplete"]),
                   "violations": [{"id": v["id"], "impact": v["impact"], "help": v["help"], "nodes": len(v["nodes"])}
                                  for v in result["violations"]]}
        (ROOT / "reports" / "a11y_axe.json").write_text(json.dumps(summary, indent=1))
        bad = [v for v in summary["violations"] if v["impact"] in ("serious", "critical")]
        assert not bad, bad
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@pytest.mark.a11y
@tc("TC-E2E-005", "Keyboard-only: sign in using Tab / typing / Enter without a mouse",
    requirement="NFR-USE-02", technique="Accessibility testing (manual-style, automated)", type="Accessibility",
    priority="P2", inputs="Tab order: Sign in tab → Register tab → Email → Password → Enter",
    expected="Signed in; focus outline visible", **E)
def test_keyboard_only(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-005")
    try:
        page.goto(base)
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.type("ananya@example.in")
        page.keyboard.press("Tab")
        page.keyboard.type("Hotel@2026")
        page.keyboard.press("Enter")
        expect(page.get_by_test_id("who")).to_contain_text("Ananya Rao")
    finally:
        c.close()
        b.close()


DEVICES = ["iPhone 13", "Pixel 7", "iPad (gen 7)", "Desktop Chrome"]


@pytest.mark.e2e
@pytest.mark.parametrize("device", [
    pytest.param(d, id=f"TC-E2E-{6 + i:03d}", marks=pytest.mark.tc(
        id=f"TC-E2E-{6 + i:03d}", title=f"Responsive layout on {d}: search usable, no horizontal scroll",
        requirement="NFR-COMP-01", technique="Compatibility – device emulation", type="Compatibility",
        priority="P2", preconditions="Chromium device emulation", inputs=f"device={d}",
        steps="Open home, search 2→5 Nov, screenshot", expected="Results visible; scrollWidth ≤ viewport", **E))
    for i, d in enumerate(DEVICES)])
def test_responsive(server, pw, device):
    base, _ = server
    profile = dict(pw.devices[device])
    profile.pop("default_browser_type", None)
    viewport = profile.pop("viewport")
    b, c, page = new_page(pw, f"device-{device.replace(' ', '_')}", viewport=viewport, **profile)
    try:
        page.goto(base)
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        expect(page.get_by_test_id("room-FAMILY")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth") <= viewport["width"] + 1
        shot(page, f"08_device_{device.replace(' ', '_').replace('(', '').replace(')', '')}")
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@pytest.mark.parametrize("browser", [
    pytest.param(name, id=f"TC-E2E-{10 + i:03d}", marks=pytest.mark.tc(
        id=f"TC-E2E-{10 + i:03d}", title=f"Cross-browser: sign-in and search work in {name}",
        requirement="NFR-COMP-02", technique="Compatibility – cross-browser", type="Compatibility", priority="P2",
        preconditions=f"{name} installed", inputs=f"browser={name}", steps="Sign in, search",
        expected="Signed in, results shown", **E))
    for i, name in enumerate(["chromium", "firefox", "webkit"])])
def test_cross_browser(server, pw, browser):
    base, _ = server
    try:
        getattr(pw, browser).launch().close()
    except Exception:  # noqa: BLE001
        pytest.skip(f"{browser} binary not installable in this sandbox; run `playwright install {browser}` locally")
    b, c, page = new_page(pw, f"browser-{browser}", browser=browser)
    try:
        login(page, base)
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        expect(page.get_by_test_id("room-STANDARD")).to_be_visible()
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@tc("TC-E2E-013", "Page load performance: DOMContentLoaded under 1 s on local server", requirement="NFR-PERF-03",
    technique="Performance (client-side)", type="Performance", priority="P3", inputs="Navigation Timing API",
    expected="domContentLoaded < 1000 ms", **E)
def test_page_load(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-013")
    try:
        page.goto(base)
        t = page.evaluate("performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd")
        assert t < 1000
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@pytest.mark.regression
@tc("TC-E2E-014", "Regression DEF-002: every booking-form field stays inside its card at 1280 px",
    requirement="NFR-USE-01", technique="Regression (visual layout)", type="Regression", priority="P3",
    inputs="viewport 1280×800, booking panel visible", expected="field.right ≤ card.right for all fields", **E)
def test_regression_layout(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-014")
    try:
        login(page, base)
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        page.get_by_test_id("select-DELUXE").click()
        overflow = page.evaluate("""() => { const card = document.querySelector('#book').getBoundingClientRect();
            return [...document.querySelectorAll('#book input, #book select')]
              .map(e => e.getBoundingClientRect().right - card.right).filter(d => d > 0.5); }""")
        assert overflow == []
        shot(page, "09_regression_layout")
    finally:
        c.close()
        b.close()


@pytest.mark.e2e
@pytest.mark.regression
@tc("TC-E2E-015", "Regression DEF-003: zero discount is displayed as ₹0.00 (never ₹-0.00)",
    requirement="FR-06", technique="Regression (UI formatting)", type="Regression", priority="P3",
    inputs="DELUXE 2→5 Nov, no promo, tier NONE", expected="Discount cell = '₹0.00'", **E)
def test_regression_zero_discount(server, pw):
    base, _ = server
    b, c, page = new_page(pw, "TC-E2E-015")
    try:
        login(page, base)
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        page.get_by_test_id("select-DELUXE").click()
        page.get_by_test_id("quote-btn").click()
        expect(page.get_by_test_id("quote-discount")).to_contain_text("₹0.00")
        assert "-0.00" not in page.get_by_test_id("quote").inner_text()
    finally:
        c.close()
        b.close()
