"""Tool-assisted execution of the manual cases that can be run without human participants.

Runs a live server and a real Chromium browser, collects evidence (screenshots, captured API
requests, the accessibility tree, keyboard tab order) into reports/manual/, and writes the
observations to reports/manual/manual_exec.json. Pass/fail is then judged against each case's
expected result and recorded in docs/manual_and_static.json.

    python tools/manual_exec.py
"""
import json
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import create_app  # noqa: E402
from app.services import Clock  # noqa: E402

OUT = ROOT / "reports" / "manual"


def start_server():
    app = create_app(":memory:", Clock(datetime(2026, 10, 8, 10, 0)))
    app.state.svc.register("Ananya Rao", "ananya@example.in", "9123456780", 21, "Hotel@2026")
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    return srv, f"http://127.0.0.1:{port}"


def login(page, base):
    page.goto(base)
    page.get_by_test_id("login-email").fill("ananya@example.in")
    page.get_by_test_id("login-password").fill("Hotel@2026")
    page.get_by_test_id("login-submit").click()
    page.get_by_text("Signed in").wait_for()


def l10n_001(browser, base):
    """Quote a long multi-room FAMILY stay and read every amount shown."""
    ctx = browser.new_context(locale="en-IN", viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    login(page, base)
    page.get_by_test_id("check-in").fill("2026-12-01")
    page.get_by_test_id("check-out").fill("2026-12-31")          # 30 nights (the maximum)
    page.get_by_test_id("search-submit").click()
    page.get_by_test_id("select-FAMILY").click()
    page.get_by_test_id("rooms").fill("2")
    page.get_by_test_id("adults").fill("4")
    page.get_by_test_id("quote-btn").click()
    page.get_by_test_id("quote").get_by_text("₹").first.wait_for()
    quote = page.get_by_test_id("quote")
    quote.scroll_into_view_if_needed()
    quote.screenshot(path=str(OUT / "L10N-001_quote.png"))
    page.screenshot(path=str(OUT / "L10N-001_page.png"), full_page=True)
    text = quote.inner_text()
    import re
    amounts = re.findall(r"-?₹[\d,]+\.\d{2}", text)
    lakh = re.compile(r"^-?₹(\d{1,2},)?(\d{2},)*\d{1,3}\.\d{2}$")   # Indian grouping: 1,23,45,678.00
    big = [a for a in amounts if float(a.replace("₹", "").replace(",", "")) >= 100000]
    ctx.close()
    return {"quote_text": text, "amounts": amounts, "amounts_at_least_1_lakh": big,
            "all_indian_grouping": all(lakh.match(a) for a in amounts),
            "all_two_decimals": all(a.split(".")[-1].isdigit() and len(a.split(".")[-1]) == 2 for a in amounts)}


def l10n_002(pw, base):
    """Date fields under en-IN vs en-US; capture what the API actually receives.
    A native <input type=date> takes its display order from the browser's UI language, so each
    locale gets its own browser started with --lang (as a real user's browser would be)."""
    res = {}
    for loc in ("en-IN", "en-US"):
        browser = pw.chromium.launch(args=[f"--lang={loc}"], env={"LANG": loc.replace("-", "_") + ".UTF-8", "LANGUAGE": loc.replace("-", "_")})
        ctx = browser.new_context(locale=loc, viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        login(page, base)
        ci = page.get_by_test_id("check-in")
        ci.click()
        page.keyboard.type("15112026" if loc == "en-IN" else "11152026")   # typed in the order the locale shows
        page.get_by_test_id("check-out").click()
        page.keyboard.type("18112026" if loc == "en-IN" else "11182026")
        form = page.get_by_test_id("search-form")
        form.screenshot(path=str(OUT / f"L10N-002_dates_{loc}.png"))
        values = (ci.input_value(), page.get_by_test_id("check-out").input_value())
        with page.expect_request(lambda r: "/api/availability" in r.url) as rq:
            page.get_by_test_id("search-submit").click()
        r = rq.value
        res[loc] = {"navigator_language": page.evaluate("navigator.language"),
                    "input_values": values, "api_request": r.method + " " + r.url.split("127.0.0.1")[-1],
                    "api_body": r.post_data}
        ctx.close()
        browser.close()
    return res


def a11y_proxy(browser, base):
    """What a screen reader would get: accessible names, roles, live regions and keyboard order."""
    ctx = browser.new_context(locale="en-IN", viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(base)
    controls = page.evaluate("""() => [...document.querySelectorAll('input,select,button,a[href],textarea')]
        .map(e => { const lab = e.labels && e.labels[0] ? e.labels[0].innerText.trim() : '';
                    return {tag: e.tagName.toLowerCase(), type: e.type || '', role: e.getAttribute('role') || '', testid: e.dataset.testid || '',
                            name: (e.getAttribute('aria-label') || lab || e.innerText || e.title || e.placeholder || '').trim().slice(0, 60)}; })""")
    live = page.evaluate("""() => [...document.querySelectorAll('[aria-live],[role=status],[role=alert]')]
        .map(e => ({testid: e.dataset.testid || e.id, live: e.getAttribute('aria-live') || e.getAttribute('role')}))""")
    order = []
    page.locator("body").click(position={"x": 2, "y": 2})
    for _ in range(14):
        page.keyboard.press("Tab")
        order.append(page.evaluate("(() => { const e = document.activeElement; return (e.dataset.testid || e.tagName) + "
                                   "' | outline=' + getComputedStyle(e).outlineStyle })()"))
    snap = page.locator("body").aria_snapshot()          # the accessibility tree a screen reader reads
    (OUT / "A11Y-001_aria_snapshot.yaml").write_text(snap)
    headers = page.evaluate("""() => [...document.querySelectorAll('th')].map(th => ({text: th.innerText.trim(),
        hidden_from_at: getComputedStyle(th.firstElementChild || th).display === 'none'}))""")
    # does an error message get announced? submit a bad login and see where the message lands
    page.get_by_test_id("login-email").fill("ananya@example.in")
    page.get_by_test_id("login-password").fill("wrong")
    page.get_by_test_id("login-submit").click()
    page.wait_for_timeout(400)
    err = page.evaluate("""() => { const e = document.querySelector('[data-testid=msg-error]');
        if (!e) return null; const host = e.closest('[aria-live],[role=alert],[role=status]');
        return {text: e.innerText, announced_via: host ? (host.getAttribute('aria-live') || host.getAttribute('role')) : null,
                own_role: e.getAttribute('role')}; }""")
    page.screenshot(path=str(OUT / "A11Y-001_login_error.png"), full_page=True)
    ctx.close()
    return {"controls": controls, "unnamed_controls": [c for c in controls if not c["name"]],
            "live_regions": live, "tab_order": order, "login_error": err, "table_headers": headers}


def heuristic_screens(browser, base):
    """Screens for the heuristic walkthrough (desktop + 375 px mobile)."""
    for name, vp in (("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 375, "height": 812})):
        ctx = browser.new_context(locale="en-IN", viewport=vp)
        page = ctx.new_page()
        login(page, base)
        page.get_by_test_id("check-in").fill("2026-11-02")
        page.get_by_test_id("check-out").fill("2026-11-01")         # deliberately reversed
        page.get_by_test_id("search-submit").click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / f"USE-001_{name}_error.png"), full_page=True)
        page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click()
        page.get_by_test_id("select-DELUXE").click()
        page.get_by_test_id("quote-btn").click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / f"USE-001_{name}_quote.png"), full_page=True)
        ctx.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv, base = start_server()
    results = {"executed_at": datetime.now().isoformat(timespec="seconds"), "browser": None}
    with sync_playwright() as p:
        b = p.chromium.launch()
        results["browser"] = f"Chromium {b.version} (headless)"
        results["L10N-001"] = l10n_001(b, base)
        results["L10N-002"] = l10n_002(p, base)
        results["A11Y-001"] = a11y_proxy(b, base)
        heuristic_screens(b, base)
        b.close()
    srv.should_exit = True
    (OUT / "manual_exec.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in results.items() if k != "A11Y-001"}, indent=1, ensure_ascii=False))
    a = results["A11Y-001"]
    print("unnamed:", a["unnamed_controls"]); print("live:", a["live_regions"]); print("tab:", a["tab_order"])
    print("login error:", a["login_error"])


if __name__ == "__main__":
    main()
