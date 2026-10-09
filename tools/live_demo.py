"""Guided live demo for the viva / presentation.

Runs the test suites one stage at a time, printing each test case ID, objective and result live.
Press Enter to start each stage (or pass --auto to run straight through).

    python tools/live_demo.py            # guided, browser tests open a visible Chrome window
    python tools/live_demo.py --auto     # no pauses
    python tools/live_demo.py --stage 4  # start from stage 4
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

STAGES = [
    ("Smoke suite — is the build worth testing?", "5 critical checks: health, UI loads, rooms, booking happy path, browser journey.",
     ["-m", "smoke"]),
    ("Black-box: Boundary Value Analysis", "Values at min-1, min, min+1, nominal, max-1, max, max+1 for age, nights, rooms, password …",
     ["tests/unit/test_bva.py"]),
    ("Black-box: Equivalence Class Partitioning", "One value per valid / invalid class — this suite found DEF-001 (\"R. Chandra\").",
     ["tests/unit/test_ecp.py"]),
    ("Black-box: Decision tables + cause-effect graph", "Each rule column of the refund / benefits tables becomes one test case.",
     ["tests/unit/test_decision_tables.py"]),
    ("Black-box: State transition", "Booking life cycle PENDING → CONFIRMED → CANCELLED / EXPIRED, valid and invalid transitions.",
     ["tests/unit/test_state_transition.py"]),
    ("White-box: statement, branch, condition, MC/DC, basis paths, loops, data flow",
     "Tests derived from the code's control-flow graph.", ["tests/unit/test_whitebox.py"]),
    ("Integration level", "Service + SQLite + payment-gateway stub, incl. a 20-thread overbooking race.",
     ["tests/integration"]),
    ("System level: API, negative, contract, security", "SQL injection, XSS, IDOR, privilege escalation, brute-force lock-out …",
     ["tests/system/test_api_system.py"]),
    ("End-to-end UI in a real browser", "Watch the browser: register → sign in → search → price → reserve → pay → cancel.",
     ["-m", "e2e"]),
    ("Acceptance (UAT) — Gherkin scenarios", "Business-readable Given/When/Then scenarios executed by pytest-bdd.",
     ["tests/acceptance"]),
    ("Full regression run with coverage", "All 554 test cases, statement + branch coverage, HTML report.",
     ["--cov=app", "--cov-branch", "--cov-report=term", "--html=reports/test_report.html", "--self-contained-html"]),
]


def banner(n, title, note):
    line = "═" * 100
    print(f"\n\033[1;36m{line}\n  STAGE {n}/{len(STAGES)} · {title}\n\033[0m  {note}\n\033[1;36m{line}\033[0m")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="run without pausing")
    ap.add_argument("--stage", type=int, default=1, help="start from this stage")
    ap.add_argument("--headless", action="store_true", help="do not open a visible browser for the UI stage")
    a = ap.parse_args()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if not a.headless:
        env["HRRS_HEADED"] = "1"
        env.setdefault("HRRS_SLOWMO", "400")
    t0 = time.time()
    for n, (title, note, args) in enumerate(STAGES, 1):
        if n < a.stage:
            continue
        banner(n, title, note)
        if not a.auto:
            input("  ▶ press Enter to run … ")
        cmd = [PY, "-m", "pytest", "-q", "--tc", "-W", "ignore", *args]
        print(f"  $ pytest {' '.join(cmd[4:])}\n")
        subprocess.run(cmd, cwd=ROOT, env=env)
    print(f"\n\033[1;32mDemo finished in {time.time() - t0:.0f} s. Open reports/test_report.html for the full report.\033[0m")


if __name__ == "__main__":
    main()
