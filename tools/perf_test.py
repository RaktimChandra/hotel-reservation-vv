"""Non-functional performance test harness for HRRS.

Runs against a live uvicorn server (separate process) with a file-backed SQLite DB:

  baseline   1 virtual user, sequential requests        → reference latency
  load       25 VUs, mixed realistic workload            → SLA check (p95 < 300 ms, errors < 1 %)
  stress     step load 10 → 25 → 50 → 100 → 200 VUs     → throughput knee / breaking point
  spike      idle → sudden 150 VUs burst                  → elasticity + recovery
  soak       20 VUs for SOAK_SECONDS                      → latency drift, RSS memory growth
  volume     5 000 extra bookings in DB, re-measure      → data-volume sensitivity

Results are written to reports/perf.json (consumed by the charts, report and deck).
"""
import json
import os
import random
import socket
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "perf.json"
SOAK_SECONDS = int(os.environ.get("SOAK_SECONDS", "60"))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def pct(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(values) - 1)
    return values[f] + (values[c] - values[f]) * (k - f)


class Server:
    def __init__(self, db):
        self.port = free_port()
        env = {**os.environ, "HRRS_DB": str(db), "PYTHONPATH": str(ROOT)}
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(self.port),
                                      "--log-level", "warning"], cwd=ROOT, env=env)
        self.base = f"http://127.0.0.1:{self.port}"
        for _ in range(200):
            try:
                if httpx.get(self.base + "/api/health", timeout=0.5).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def rss_mb(self):
        try:
            with open(f"/proc/{self.proc.pid}/status") as f:
                for line in f:
                    if line.startswith("VmRSS"):
                        return int(line.split()[1]) / 1024
        except OSError:
            return 0.0

    def stop(self):
        self.proc.terminate()
        self.proc.wait(5)


class Workload:
    """Realistic mix: 50 % availability, 30 % quote, 15 % book+pay, 5 % list bookings."""

    def __init__(self, base, n_users=40):
        self.base = base
        self.tokens = []
        with httpx.Client(base_url=base, timeout=30) as c:
            for i in range(n_users):
                email = f"perf{i}_{random.randint(0, 10**9)}@load.test"
                c.post("/api/auth/register", json={"name": "Load Tester", "email": email, "phone": "9876543210",
                                                   "age": 30, "password": "Hotel@2026"})
                self.tokens.append(c.post("/api/auth/login", json={"email": email, "password": "Hotel@2026"}).json()["token"])

    def one(self, client: httpx.Client, rng: random.Random):
        ci = date.today() + timedelta(days=rng.randint(1, 300))
        co = ci + timedelta(days=rng.randint(1, 7))
        auth = {"Authorization": "Bearer " + rng.choice(self.tokens)}
        r = rng.random()
        t0 = time.perf_counter()
        if r < 0.50:
            resp = client.get("/api/availability", params={"check_in": ci.isoformat(), "check_out": co.isoformat()})
            kind = "availability"
        elif r < 0.80:
            resp = client.post("/api/quote", json={"room_type": rng.choice(["STANDARD", "DELUXE", "FAMILY", "SUITE"]),
                                                   "check_in": ci.isoformat(), "check_out": co.isoformat()})
            kind = "quote"
        elif r < 0.95:
            resp = client.post("/api/bookings", json={"room_type": rng.choice(["STANDARD", "DELUXE"]),
                                                      "check_in": ci.isoformat(), "check_out": co.isoformat()},
                               headers=auth)
            kind = "book"
            if resp.status_code == 201:
                bid = resp.json()["id"]
                resp = client.post(f"/api/bookings/{bid}/pay", headers={**auth, "Idempotency-Key": f"p{bid}"},
                                   json={"method": "upi", "vpa": "load@okaxis"})
        else:
            resp = client.get("/api/bookings", headers=auth)
            kind = "list"
        ms = (time.perf_counter() - t0) * 1000
        # 422 NO_AVAILABILITY is a correct business answer under load, not an error
        ok = resp.status_code < 400 or (resp.status_code == 422 and "NO_AVAILABILITY" in resp.text)
        return kind, ms, ok


def run_phase(wl, vus, requests_per_vu=None, duration=None, seed=1):
    lat, errors, kinds = [], 0, {}
    lock = threading.Lock()
    stop_at = time.perf_counter() + duration if duration else None

    def worker(i):
        nonlocal errors
        rng = random.Random(seed * 1000 + i)
        with httpx.Client(base_url=wl.base, timeout=60) as c:
            n = 0
            while True:
                if requests_per_vu is not None and n >= requests_per_vu:
                    break
                if stop_at and time.perf_counter() >= stop_at:
                    break
                try:
                    kind, ms, ok = wl.one(c, rng)
                except httpx.HTTPError:
                    kind, ms, ok = "transport", 0.0, False
                with lock:
                    lat.append(ms)
                    kinds.setdefault(kind, []).append(ms)
                    errors += 0 if ok else 1
                n += 1

    t0 = time.perf_counter()
    with ThreadPoolExecutor(vus) as ex:
        list(ex.map(worker, range(vus)))
    wall = time.perf_counter() - t0
    n = len(lat)
    return {"vus": vus, "requests": n, "seconds": round(wall, 2), "throughput_rps": round(n / wall, 1),
            "p50_ms": round(pct(lat, 50), 1), "p90_ms": round(pct(lat, 90), 1), "p95_ms": round(pct(lat, 95), 1),
            "p99_ms": round(pct(lat, 99), 1), "max_ms": round(max(lat or [0]), 1),
            "mean_ms": round(statistics.fmean(lat) if lat else 0, 1),
            "error_rate_pct": round(100 * errors / max(n, 1), 2),
            "by_endpoint_p95": {k: round(pct(v, 95), 1) for k, v in kinds.items()}}


def seed_volume(db_path, n):
    import sqlite3
    conn = sqlite3.connect(db_path)
    uid = conn.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
    start = date.today() + timedelta(days=400)  # far future: does not reduce real availability
    rows = []
    for i in range(n):
        ci = start + timedelta(days=i % 300)
        rows.append((f"VOL-{i:06d}", uid, "STANDARD", ci.isoformat(), (ci + timedelta(days=2)).isoformat(), 1, 1, 0,
                     0, 1, None, "CONFIRMED", 5000, 0, 250, 5250, "2026-01-01T00:00:00"))
    conn.executemany("""INSERT INTO bookings(ref,user_id,room_type,check_in,check_out,rooms,adults,children,
        extra_beds,refundable,promo,status,subtotal,discount,gst,total,created_at) VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    conn.commit()
    ids = [r[0] for r in conn.execute("SELECT id FROM bookings WHERE ref LIKE 'VOL-%'")]
    conn.executemany("INSERT INTO booking_rooms(booking_id, room_no) VALUES (?, ?)",
                     [(bid, f"1{(k % 8) + 1:02d}") for k, bid in enumerate(ids)])
    conn.commit()
    conn.close()


def main():
    tmp = ROOT / "reports" / "perf_db.sqlite"
    if tmp.exists():
        tmp.unlink()
    srv = Server(tmp)
    results = {"environment": {"python": sys.version.split()[0], "cpus": os.cpu_count(),
                               "server": "uvicorn (1 worker) + SQLite file DB", "date": date.today().isoformat()}}
    try:
        wl = Workload(srv.base)
        print("baseline …")
        results["baseline"] = run_phase(wl, 1, requests_per_vu=200)
        print("load …")
        results["load"] = run_phase(wl, 25, requests_per_vu=40, seed=2)
        print("stress …")
        results["stress"] = [run_phase(wl, v, requests_per_vu=max(10, 800 // v), seed=3 + v)
                             for v in (10, 25, 50, 100, 200)]
        print("spike …")
        time.sleep(2)
        pre = run_phase(wl, 5, requests_per_vu=20, seed=50)
        burst = run_phase(wl, 150, requests_per_vu=5, seed=51)
        post = run_phase(wl, 5, requests_per_vu=20, seed=52)
        results["spike"] = {"before": pre, "burst": burst, "after": post}
        print(f"soak {SOAK_SECONDS}s …")
        rss0 = srv.rss_mb()
        windows = []
        slice_s = max(5, SOAK_SECONDS // 6)
        for w in range(SOAK_SECONDS // slice_s):
            r = run_phase(wl, 20, duration=slice_s, seed=100 + w)
            r["rss_mb"] = round(srv.rss_mb(), 1)
            windows.append(r)
        results["soak"] = {"seconds": SOAK_SECONDS, "rss_start_mb": round(rss0, 1), "windows": windows}
        print("volume …")
        before = run_phase(wl, 10, requests_per_vu=30, seed=200)
        seed_volume(str(tmp), 5000)
        after = run_phase(wl, 10, requests_per_vu=30, seed=201)
        results["volume"] = {"extra_bookings": 5000, "before": before, "after": after}
    finally:
        srv.stop()
        if tmp.exists():
            tmp.unlink()
    load = results["load"]
    results["sla"] = {"p95_target_ms": 300, "error_target_pct": 1.0,
                      "p95_met": load["p95_ms"] < 300, "errors_met": load["error_rate_pct"] < 1.0}
    OUT.write_text(json.dumps(results, indent=1))
    print(json.dumps({k: results[k] for k in ("baseline", "load", "sla")}, indent=1))


if __name__ == "__main__":
    main()
