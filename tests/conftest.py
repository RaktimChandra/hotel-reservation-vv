import json
import os
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import gateway
from app.main import create_app
from app.services import Clock

REPORTS = Path(__file__).resolve().parent.parent / "reports"
_RESULTS: dict[str, dict] = {}

# A fixed "today" so every date-based expectation is reproducible.
FROZEN_NOW = datetime(2026, 10, 8, 10, 0, 0)


def pytest_configure(config):
    config.addinivalue_line("markers", "tc(**meta): test-case metadata (id, title, technique …)")
    for m in ("smoke", "regression", "security", "performance", "e2e", "recovery", "concurrency", "a11y"):
        config.addinivalue_line("markers", f"{m}: {m} suite")


def pytest_addoption(parser):
    parser.addoption("--tc", action="store_true", help="live demo: print each test case's ID and objective as it runs")


_TC_META: dict[str, dict] = {}


def pytest_collection_modifyitems(config, items):
    for it in items:
        m = it.get_closest_marker("tc")
        if m is not None:
            _TC_META[it.nodeid] = m.kwargs


def pytest_report_teststatus(report, config):
    # with --tc the per-test line below replaces pytest's progress dots
    if config.getoption("--tc") and report.nodeid in _TC_META and report.when == "call":
        return report.outcome, "", report.outcome.upper()


def pytest_runtest_logreport(report):
    cfg = _CFG.get("config")
    if cfg is None or not cfg.getoption("--tc") or report.nodeid not in _TC_META:
        return
    if report.when == "call" or (report.when == "setup" and not report.passed):
        meta = _TC_META[report.nodeid]
        tr = cfg.pluginmanager.get_plugin("terminalreporter")
        status = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIPPED"}[report.outcome]
        colour = {"PASS": {"green": True}, "FAIL": {"red": True, "bold": True}, "SKIPPED": {"yellow": True}}[status]
        tr.ensure_newline()
        tr.write(f"  {meta['id']:<22} {meta.get('title', '')[:78]:<80} ")
        tr.write(f"{status:<7}", **colour)
        tr.write(f" {report.duration * 1000:7.1f} ms\n")


_CFG: dict = {}


def pytest_sessionstart(session):
    _CFG["config"] = session.config


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    marker = item.get_closest_marker("tc")
    if marker is None:
        return
    meta = dict(marker.kwargs)
    tid = meta["id"]
    entry = _RESULTS.setdefault(tid, {**meta, "nodeid": item.nodeid, "status": "NOT RUN",
                                      "duration_ms": 0.0, "message": "",
                                      "suites": sorted(m.name for m in item.iter_markers() if m.name != "tc"
                                                       and m.name != "parametrize")})
    if rep.when == "call" or (rep.when == "setup" and rep.outcome != "passed"):
        if entry["status"] == "FAIL":      # one test-case id may run several examples; any failure sticks
            return
        entry["duration_ms"] = round(entry.get("duration_ms", 0) + rep.duration * 1000, 3)
        if rep.passed:
            entry["status"] = "PASS"
        elif rep.skipped:
            entry["status"] = "SKIPPED"
            entry["message"] = str(rep.longrepr[-1]) if isinstance(rep.longrepr, tuple) else ""
        else:
            entry["status"] = "FAIL"
            entry["message"] = (rep.longreprtext or "")[-600:]
        entry["executed_at"] = datetime.now().isoformat(timespec="seconds")


def pytest_sessionfinish(session, exitstatus):
    if not _RESULTS:
        return
    REPORTS.mkdir(exist_ok=True)
    cfg = session.config
    full_run = (not cfg.getoption("markexpr") and not cfg.getoption("keyword")
                and getattr(cfg, "args_source", None) == pytest.Config.ArgsSource.TESTPATHS)
    # A partial run (-m smoke, -k …, a single file) must never overwrite the full-suite evidence.
    name = os.environ.get("HRRS_RESULTS", "results.json" if full_run else "results_partial.json")
    path = REPORTS / name
    existing = {}
    if path.exists() and os.environ.get("HRRS_RESULTS_APPEND"):
        existing = {r["id"]: r for r in json.loads(path.read_text())}
    existing.update(_RESULTS)
    path.write_text(json.dumps(sorted(existing.values(), key=lambda r: r["id"]), indent=1))


# ------------------------------------------------------------------ fixtures
@pytest.fixture
def clock():
    return Clock(FROZEN_NOW)


@pytest.fixture
def app(clock):
    gateway.FAULT["mode"] = None
    application = create_app(":memory:", clock)
    yield application
    gateway.FAULT["mode"] = None


@pytest.fixture
def svc(app):
    return app.state.svc


@pytest.fixture
def client(app):
    return TestClient(app)


GUEST = dict(name="Raktim Chandra", email="raktim@example.in", phone="9832288101", age=21,
             password="Hotel@2026")


@pytest.fixture
def guest_token(client):
    assert client.post("/api/auth/register", json=GUEST).status_code == 201
    return client.post("/api/auth/login", json={"email": GUEST["email"], "password": GUEST["password"]}).json()["token"]


@pytest.fixture
def auth(guest_token):
    return {"Authorization": f"Bearer {guest_token}"}


@pytest.fixture
def admin_auth(client):
    tok = client.post("/api/auth/login", json={"email": "admin@hrrs.test", "password": "Admin@123"}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def make_guest(client, n: int, tier: str | None = None, admin_auth=None):
    body = {**GUEST, "email": f"guest{n}@example.in", "name": f"Guest Number {chr(65 + n % 26)}"}
    uid = client.post("/api/auth/register", json=body).json()["id"]
    if tier and admin_auth:
        client.patch(f"/api/admin/users/{uid}/tier", json={"tier": tier}, headers=admin_auth)
    tok = client.post("/api/auth/login", json={"email": body["email"], "password": GUEST["password"]}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}, uid


@pytest.fixture
def timer():
    t0 = time.perf_counter()
    yield lambda: (time.perf_counter() - t0) * 1000
