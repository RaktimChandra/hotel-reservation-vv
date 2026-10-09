"""Fault seeding (defect injection) experiment — estimates suite effectiveness and latent defects.

Each seeded fault is a realistic, hand-written bug injected into a sandbox copy of
the application. The FULL suite (unit → E2E) is run against each one.

Mills' seeding estimator
    N̂_native_total = n_native_found × S_seeded / s_seeded_found
    latent ≈ N̂ − n_native_found
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAULTS = [
    ("SF-01", "app/domain/validation.py", "NAME_MIN, NAME_MAX = 2, 50", "NAME_MIN, NAME_MAX = 2, 49",
     "Off-by-one on maximum name length", "Unit"),
    ("SF-02", "app/domain/pricing.py", "return night.weekday() in (4, 5)", "return night.weekday() in (5, 6)",
     "Weekend surcharge applied to Sat/Sun instead of Fri/Sat", "Unit"),
    ("SF-03", "app/domain/pricing.py", "if tariff <= GST_LOWER_SLAB_MAX:", "if tariff < GST_LOWER_SLAB_MAX:",
     "GST slab boundary ₹7,500 taxed at 18 %", "Unit"),
    ("SF-04", "app/domain/pricing.py", "capped = raw_discount > cap", "capped = False",
     "30 % discount cap never enforced", "Unit"),
    ("SF-05", "app/domain/cancellation.py", 'return RefundDecision(75, 0, False, "R5")',
     'return RefundDecision(75, PROCESSING_FEE, False, "R5")', "Processing fee wrongly charged to PLATINUM", "Unit"),
    ("SF-06", "app/services.py", "AND b.check_in < ? AND b.check_out > ?)", "AND b.check_in <= ? AND b.check_out >= ?)",
     "Back-to-back stays treated as overlapping (lost inventory)", "Integration"),
    ("SF-07", "app/services.py", 'if user["role"] != "admin" and row["user_id"] != user["id"]:',
     'if False and row["user_id"] != user["id"]:', "Object-level authorisation removed (IDOR)", "Integration"),
    ("SF-08", "app/services.py", "if prior:\n", "if False:\n", "Idempotency check removed (double charge)",
     "Integration"),
    ("SF-09", "app/domain/state.py", '"cancel": {PENDING: CANCELLED, CONFIRMED: CANCELLED},',
     '"cancel": {PENDING: CANCELLED, CONFIRMED: CANCELLED, CHECKED_IN: CANCELLED},',
     "Cancellation allowed after check-in", "Unit"),
    ("SF-10", "app/main.py", "def metrics(day: date | None = None, admin=Depends(admin_user)):",
     "def metrics(day: date | None = None, admin=Depends(current_user)):", "Admin report exposed to guests",
     "System"),
    ("SF-11", "app/static/index.html", "d.textContent = text;", "d.innerHTML = text;",
     "Server text rendered as HTML (DOM XSS)", "E2E"),
    ("SF-12", "app/services.py", "MAX_FAILED_LOGINS = 3", "MAX_FAILED_LOGINS = 4",
     "Lock-out threshold weakened to 4 attempts", "Integration"),
]


def main(only=None):
    box = Path(tempfile.mkdtemp(prefix="seed_"))
    for d in ("app", "tests", "tools"):
        shutil.copytree(ROOT / d, box / d, ignore=shutil.ignore_patterns("__pycache__", "node_modules")
                        if d != "tools" else None)
    out = []
    for fid, rel, old, new, desc, level in FAULTS:
        if only and fid not in only:
            continue
        f = box / rel
        original = f.read_text()
        assert old in original, (fid, old)
        f.write_text(original.replace(old, new, 1))
        t0 = time.perf_counter()
        env = {**os.environ, "HRRS_RESULTS": f"seed_{fid}.json"}
        r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", "-p",
                            "no:warnings", "--hypothesis-seed=0"], cwd=box, env=env, capture_output=True, text=True,
                           timeout=900)
        f.write_text(original)
        failed = [line.split("::")[-1].split(" ")[0] for line in r.stdout.splitlines() if line.startswith("FAILED")]
        ids = sorted({x[x.find("[") + 1:x.find("]")] if "[" in x else x for x in failed})
        out.append({"id": fid, "file": rel, "description": desc, "expected_level": level,
                    "detected": bool(failed), "failing_tests": len(failed), "detected_by": ids[:12],
                    "seconds": round(time.perf_counter() - t0, 1)})
        print(fid, "DETECTED" if failed else "MISSED", len(failed), ids[:4])
    shutil.rmtree(box, ignore_errors=True)
    if only:
        print(json.dumps(out, indent=1))
        return out
    S = len(out)
    s = sum(o["detected"] for o in out)
    native = len(json.loads((ROOT / "reports" / "defects_found.json").read_text()))
    est = native * S / s if s else None
    summary = {"seeded": S, "seeded_detected": s, "detection_pct": round(100 * s / S, 1), "native_found": native,
               "mills_estimated_native_total": round(est, 2) if est else None,
               "estimated_latent": round(est - native, 2) if est else None}
    (ROOT / "reports" / "fault_seeding.json").write_text(json.dumps({"summary": summary, "faults": out}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
