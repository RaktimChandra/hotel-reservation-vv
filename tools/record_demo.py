"""Record a slow, human-paced demo of the guest journey (for the demo video). Not a test."""
import shutil
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import uvicorn
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import create_app  # noqa: E402
from app.services import Clock  # noqa: E402

OUT = ROOT / "reports" / "demo_recording"


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    app = create_app(":memory:", Clock(datetime(2026, 10, 8, 10, 0)))
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    while not srv.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{port}"
    with sync_playwright() as p:
        b = p.chromium.launch(slow_mo=260)
        c = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(OUT),
                          record_video_size={"width": 1280, "height": 720})
        page = c.new_page()
        pause = lambda s=0.9: page.wait_for_timeout(int(s * 1000))  # noqa: E731

        def show(sel):
            page.locator(sel).scroll_into_view_if_needed()
            pause(0.5)

        page.goto(base); pause(1.5)
        page.get_by_test_id("tab-register").click(); pause()
        for tid, val in (("reg-name", "Kabir Mehta"), ("reg-email", "kabir@example.in"), ("reg-phone", "9876543201"),
                         ("reg-age", "21"), ("reg-password", "hotel2026")):
            page.get_by_test_id(tid).type(val, delay=45)
        page.get_by_test_id("reg-submit").click(); pause(1.8)          # weak password message
        page.get_by_test_id("reg-password").fill(""); page.get_by_test_id("reg-password").type("Hotel@2026", delay=45)
        page.get_by_test_id("reg-submit").click(); pause(1.5)
        page.get_by_test_id("login-password").type("Hotel@2026", delay=45)
        page.get_by_test_id("login-submit").click(); pause(1.2)
        show("#search")
        page.get_by_test_id("check-in").fill("2026-11-02"); page.get_by_test_id("check-out").fill("2026-11-05")
        page.get_by_test_id("search-submit").click(); pause(2)
        page.get_by_test_id("select-DELUXE").click(); pause()
        page.get_by_test_id("adults").fill("2"); page.get_by_test_id("quote-btn").click(); pause(2.2)
        page.get_by_test_id("book-submit").click(); pause(1.2)
        show("#pay")
        page.get_by_test_id("card-number").type("4111 1111 1111 1111", delay=40)
        page.get_by_test_id("card-month").type("12"); page.get_by_test_id("card-year").type("2030"); page.get_by_test_id("card-cvv").type("123")
        page.get_by_test_id("pay-submit").click()
        expect(page.locator("#pay-msg")).to_contain_text("CONFIRMED"); pause(1.8)
        show("#mine"); pause(1.2)
        ref = page.get_by_test_id("pay-ref").inner_text()
        page.get_by_test_id(f"cancel-{ref}").click()
        expect(page.locator("#mine-msg")).to_contain_text("rule R3"); pause(2.5)
        c.close(); b.close()
    srv.should_exit = True
    vid = next(OUT.glob("*.webm"))
    vid.rename(OUT / "guest_journey.webm")
    print(OUT / "guest_journey.webm")


if __name__ == "__main__":
    main()
