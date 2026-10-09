"""Performance checks that run inside the normal suite (micro-benchmarks with budgets).

The full load / stress / spike / soak / volume campaign lives in tools/perf_test.py.
"""
import statistics
import time
from datetime import date, timedelta

import pytest

from app.domain.pricing import compute_quote
from app.services import hash_password
from tests.tclib import tc

P = dict(module="Performance", type="Performance", priority="P2")


def p95(samples):
    return statistics.quantiles(samples, n=20)[18]


@pytest.mark.performance
@tc("TC-PERF-001", "Quote engine: p95 of 1 000 computations of a 30-night quote under 5 ms",
    requirement="NFR-PERF-02", level="Unit", technique="Performance – micro-benchmark",
    inputs="SUITE, 30 nights, PLATINUM, WELCOME10 × 1000", expected="p95 < 5 ms", **P)
def test_quote_speed():
    ci = date(2026, 12, 15)
    samples = []
    for _ in range(1000):
        t0 = time.perf_counter()
        compute_quote("SUITE", ci, ci + timedelta(days=30), 2, 1, "PLATINUM", "WELCOME10")
        samples.append((time.perf_counter() - t0) * 1000)
    assert p95(samples) < 5


@pytest.mark.performance
@tc("TC-PERF-002", "Availability API: p95 under 50 ms (in-process) with 300 existing bookings",
    requirement="NFR-PERF-01", level="System", technique="Performance – latency budget",
    inputs="300 bookings seeded; 200 GET /api/availability", expected="p95 < 50 ms", **P)
def test_availability_latency(client, auth):
    for i in range(300):
        ci = date(2026, 11, 1) + timedelta(days=i % 90)
        client.post("/api/bookings", json={"room_type": "STANDARD", "check_in": ci.isoformat(),
                                           "check_out": (ci + timedelta(days=1)).isoformat()}, headers=auth)
    samples = []
    for i in range(200):
        ci = date(2026, 11, 1) + timedelta(days=i % 90)
        t0 = time.perf_counter()
        r = client.get("/api/availability", params={"check_in": ci.isoformat(),
                                                    "check_out": (ci + timedelta(days=3)).isoformat()})
        samples.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200
    assert p95(samples) < 50


@pytest.mark.performance
@pytest.mark.security
@tc("TC-PERF-003", "Password hashing is deliberately slow (≥ 20 ms) to resist offline brute force",
    requirement="NFR-SEC-01", level="Unit", technique="Performance – security budget",
    inputs="PBKDF2-SHA256, 120 000 rounds", expected="≥ 20 ms per hash", **{**P, "type": "Security"})
def test_hash_cost():
    t0 = time.perf_counter()
    hash_password("Hotel@2026")
    assert (time.perf_counter() - t0) * 1000 >= 20
