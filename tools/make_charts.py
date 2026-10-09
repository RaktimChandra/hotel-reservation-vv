"""Render every figure used in the report and deck from the real run artefacts in reports/."""
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"
OUT = ROOT / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# validated reference palette (dataviz skill, light mode)
S1, S2, S3, S4, S5, S6, S7, S8 = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7",
                                  "#e34948")
GOOD, WARN, SERIOUS, CRIT = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0", "#fcfcfb"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

for f in font_manager.findSystemFonts():
    if "Inter" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Inter", "font.size": 10.5, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titleweight": "bold", "axes.titlesize": 13,
    "axes.titlecolor": INK, "axes.titlelocation": "left", "axes.titlepad": 14, "figure.facecolor": SURF,
    "axes.facecolor": SURF, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "savefig.dpi": 200,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def subtitle(ax, text):
    ax.set_title(ax.get_title(loc="left"), loc="left", pad=30)
    ax.text(0, 1.02, text, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


results = json.loads((R / "results.json").read_text())
perf = json.loads((R / "perf.json").read_text())
perf0 = json.loads((R / "perf_before_tuning.json").read_text())
mut = json.loads((R / "mutation.json").read_text())
cov = json.loads((R / "coverage.json").read_text())
cov0 = json.loads((R / "coverage_iter1.json").read_text())
seed = json.loads((R / "fault_seeding.json").read_text())
reqs = json.loads((ROOT / "docs" / "requirements.json").read_text())


# ------------------------------------------------------------------ 1. test pyramid
def pyramid():
    lv = Counter(r["level"] for r in results)
    rows = [("Acceptance (UAT)", lv["Acceptance (UAT)"]), ("E2E UI", lv["System (E2E UI)"]),
            ("System / API", lv["System"]), ("Integration", lv["Integration"]), ("Unit", lv["Unit"])]
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(rows))
    ax.axis("off")
    colors = [S7, S5, S3, S2, S1]
    for i, (name, n) in enumerate(rows):
        y0, y1 = len(rows) - i - 1, len(rows) - i
        w0, w1 = 1 + 1.6 * (i + 1), 1 + 1.6 * i
        poly = Polygon([(5 - w0 / 2, y0 + 0.06), (5 + w0 / 2, y0 + 0.06), (5 + w1 / 2, y1 - 0.06), (5 - w1 / 2, y1 - 0.06)],
                       closed=True, fc=colors[i], ec=SURF, lw=2)
        ax.add_patch(poly)
        ax.text(5, (y0 + y1) / 2, f"{n}", ha="center", va="center", color="white", fontsize=15, fontweight="bold")
        ax.text(9.95, (y0 + y1) / 2, name, ha="right", va="center", color=INK, fontsize=11)
    ax.set_title(f"Test pyramid — {len(results)} catalogued test cases executed")
    save(fig, "test_pyramid")


# ------------------------------------------------------------------ 2. techniques
FAMILY = [("Black-box", ["BVA", "ECP", "Decision", "Cause", "State", "Pairwise", "Use-case", "BDD", "Negative",
                         "Contract", "Smoke", "End-to-end", "Regression"]),
          ("White-box", ["Basis", "Statement", "Branch", "Condition", "MC/DC", "Loop", "Data-flow", "Coverage",
                         "Mutation", "White-box"]),
          ("Experience-based", ["Error Guessing", "Property"]),
          ("Non-functional", ["Security", "Performance", "Accessibility", "Compatibility", "Fault", "Integration"])]


def family(t):
    for name, keys in FAMILY:
        if any(t.startswith(k) or k in t for k in keys):
            return name
    return "Other"


def techniques():
    c = Counter()
    for r in results:
        t = r["technique"].split(" (")[0].split(" +")[0]
        t = {"BVA": "Boundary Value Analysis", "ECP": "Equivalence Class Partitioning"}.get(t, t)
        c[t] += 1
    top = c.most_common(18)[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 6.6))
    ax.barh([k for k, _ in top], [v for _, v in top], color=S1, height=0.62)
    for i, (_, v) in enumerate(top):
        ax.text(v + 1.5, i, str(v), va="center", color=INK2, fontsize=9.5)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("test cases")
    ax.set_title("Test cases by design technique (top 18)")
    save(fig, "techniques")


# ------------------------------------------------------------------ 3. coverage before / after
def coverage():
    files = [f for f in cov["files"] if cov["files"][f]["summary"]["num_statements"]]
    names = [f.replace("app/", "").replace("domain/", "d/").replace(".py", "") for f in files]
    before = [cov0["files"][f]["summary"]["percent_covered"] for f in files]
    after = [cov["files"][f]["summary"]["percent_covered"] for f in files]
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    x = range(len(files))
    ax.bar([i - 0.2 for i in x], before, 0.38, color=S2, label="First full run")
    ax.bar([i + 0.2 for i in x], after, 0.38, color=S1, label="After coverage-guided tests")
    ax.set_xticks(list(x), names, rotation=30, ha="right")
    ax.set_ylim(90, 100.8)
    ax.set_ylabel("statement + branch coverage %")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncols=2)
    ax.grid(axis="x", visible=False)
    t0, t1 = cov0["totals"]["percent_covered"], cov["totals"]["percent_covered"]
    ax.set_title(f"Code coverage per module — total {t0:.1f}% → {t1:.1f}%")
    subtitle(ax, "y-axis starts at 90 % to make the gaps visible; every module ends at ≥ 99 %")
    save(fig, "coverage")


# ------------------------------------------------------------------ 4. mutation iterations
def mutation():
    it = mut["summary"]["iterations"]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    labels = [f"Iteration {i['iteration']}\n(+{i['tests_added']} tests)" for i in it]
    k = [i["killed"] for i in it]
    s = [i["survived"] for i in it]
    ax.bar(labels, k, color=S1, width=0.55, label="Killed")
    ax.bar(labels, s, bottom=[a + 2 for a in k], color=S2, width=0.55, label="Survived")
    for i, row in enumerate(it):
        ax.text(i, row["killed"] + row["survived"] + 8, f"{row['raw_score_pct']:.1f}%", ha="center", fontweight="bold",
                color=INK)
    ax.set_ylim(0, 300)
    ax.set_ylabel("mutants (of 270)")
    ax.legend(loc="lower right", ncols=2)
    ax.grid(axis="x", visible=False)
    ax.set_title("Mutation testing — score rises as surviving mutants guide new tests")
    subtitle(ax, "Final 3 survivors proven equivalent → mutation score = 267 / (270 − 3) = 100 %")
    save(fig, "mutation_iterations")

    by = mut["summary"]["by_operator"]
    ops = sorted(by, key=lambda o: -by[o]["total"])
    eq = Counter(m["operator"] for m in mut["mutants"] if m["status"] == "EQUIVALENT")
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.barh(ops[::-1], [by[o]["killed"] for o in ops[::-1]], color=S1, label="Killed", height=0.6)
    ax.barh(ops[::-1], [eq[o] for o in ops[::-1]], left=[by[o]["killed"] + 1 for o in ops[::-1]], color=MUTED,
            label="Equivalent", height=0.6)
    for i, o in enumerate(ops[::-1]):
        ax.text(by[o]["total"] + 3, i, f"{by[o]['killed']}/{by[o]['total']}", va="center", color=INK2, fontsize=9.5)
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("mutants")
    ax.set_title("Mutants by operator (ROR, CRP, AOR, UOD, LCR, BRV)")
    save(fig, "mutation_operators")


# ------------------------------------------------------------------ 5. performance
def performance():
    vus = [s["vus"] for s in perf["stress"]]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.plot(vus, [s["p95_ms"] for s in perf0["stress"]], color=S2, lw=2, marker="o", ms=7, label="Before tuning")
    ax.plot(vus, [s["p95_ms"] for s in perf["stress"]], color=S1, lw=2, marker="o", ms=7, label="After WAL tuning")
    ax.axhline(300, color=CRIT, lw=1.2, ls="--")
    ax.text(205, 330, "SLA p95 300 ms", color=CRIT, fontsize=9, ha="right")
    ax.set_xscale("log")
    ax.set_xticks(vus, [str(v) for v in vus])
    ax.minorticks_off()
    ax.set_xlabel("concurrent virtual users (log scale)")
    ax.set_ylabel("p95 latency (ms)")
    ax.legend(loc="upper left")
    ax.set_title("Stress test — p95 latency vs. load")
    subtitle(ax, "SLA knee moves from ~25 to ~50 concurrent users after tuning; 0 % errors at every step")
    save(fig, "stress_latency")

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.plot(vus, [s["throughput_rps"] for s in perf0["stress"]], color=S2, lw=2, marker="o", ms=7, label="Before tuning")
    ax.plot(vus, [s["throughput_rps"] for s in perf["stress"]], color=S1, lw=2, marker="o", ms=7, label="After WAL tuning")
    ax.set_xscale("log")
    ax.set_xticks(vus, [str(v) for v in vus])
    ax.minorticks_off()
    ax.set_ylim(0, None)
    ax.set_xlabel("concurrent virtual users (log scale)")
    ax.set_ylabel("requests / second")
    ax.legend(loc="lower left")
    ax.set_title("Stress test — throughput vs. load (single uvicorn worker)")
    save(fig, "stress_throughput")

    eps = ["availability", "quote", "list", "book"]
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    x = range(len(eps))
    ax.bar([i - 0.2 for i in x], [perf0["load"]["by_endpoint_p95"][e] for e in eps], 0.38, color=S2, label="Before")
    ax.bar([i + 0.2 for i in x], [perf["load"]["by_endpoint_p95"][e] for e in eps], 0.38, color=S1, label="After")
    ax.axhline(300, color=CRIT, lw=1.2, ls="--")
    ax.set_xticks(list(x), ["availability", "quote", "list bookings", "book + pay"])
    ax.set_ylabel("p95 latency at 25 VUs (ms)")
    ax.legend(loc="upper left", ncols=2)
    ax.grid(axis="x", visible=False)
    ax.set_title("Load test (25 VUs) — DEF-004 found and fixed")
    subtitle(ax, f"book + pay p95 {perf0['load']['by_endpoint_p95']['book']:.0f} → "
                 f"{perf['load']['by_endpoint_p95']['book']:.0f} ms; dashed line = 300 ms SLA")
    save(fig, "load_endpoints")

    w = perf["soak"]["windows"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    t = [(i + 1) * perf["soak"]["seconds"] / len(w) for i in range(len(w))]
    axes[0].plot(t, [x["p95_ms"] for x in w], color=S1, lw=2, marker="o", ms=7)
    axes[0].set_ylim(0, 200)
    axes[0].set_xlabel("elapsed (s)")
    axes[0].set_ylabel("p95 (ms)")
    axes[0].set_title("Soak — latency drift")
    axes[1].plot(t, [x["rss_mb"] for x in w], color=S3, lw=2, marker="o", ms=7)
    axes[1].set_ylim(0, 120)
    axes[1].set_xlabel("elapsed (s)")
    axes[1].set_ylabel("server RSS (MB)")
    axes[1].set_title("Soak — memory")
    save(fig, "soak")

    sp = perf["spike"]
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    labels = ["Before (5 VUs)", "Burst (150 VUs)", "After (5 VUs)"]
    vals = [sp["before"]["p95_ms"], sp["burst"]["p95_ms"], sp["after"]["p95_ms"]]
    ax.bar(labels, vals, color=[S1, S2, S1], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 30, f"{v:.0f} ms", ha="center", color=INK2)
    ax.set_ylabel("p95 latency (ms)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Spike test — degrades under burst, recovers immediately")
    subtitle(ax, "0 failed requests during the 150-user burst")
    save(fig, "spike")


# ------------------------------------------------------------------ 6. RTM heatmap
def rtm():
    levels = ["Unit", "Integration", "System", "System (E2E UI)", "Acceptance (UAT)"]
    short = ["Unit", "Integration", "System/API", "E2E UI", "UAT"]
    grid = defaultdict(Counter)
    for r in results:
        for rid in [x["id"] for x in reqs]:
            if rid_matches(rid, r["requirement"]):
                grid[rid][r["level"]] += 1
    ids = [x["id"] for x in reqs]
    data = [[grid[i][lv] for lv in levels] for i in ids]
    fig, ax = plt.subplots(figsize=(7.2, 10.5))
    mx = max(max(row) for row in data)

    def colour(v):
        if v == 0:
            return "#f1f0ec"
        step = min(len(SEQ) - 1, int((v / mx) ** 0.5 * (len(SEQ) - 1)))
        return SEQ[step]

    for i, row in enumerate(data):
        for j, v in enumerate(row):
            ax.add_patch(FancyBboxPatch((j + 0.05, i + 0.08), 0.9, 0.84, boxstyle="round,pad=0,rounding_size=0.08",
                                        fc=colour(v), ec=SURF, lw=2))
            if v:
                ax.text(j + 0.5, i + 0.5, str(v), ha="center", va="center", fontsize=8.5,
                        color="white" if v / mx > 0.25 else INK)
    ax.set_xlim(0, len(levels))
    ax.set_ylim(len(ids), 0)
    ax.set_xticks([j + 0.5 for j in range(len(levels))], short)
    ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(ids))], ids, fontsize=8.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Requirements traceability — executed test cases per requirement and level", pad=30)
    save(fig, "rtm_heatmap")


def rid_matches(rid, ref):
    ref = ref.replace("–", "-")
    for part in [p.strip() for p in ref.split(",")]:
        if part == rid:
            return True
        if ".." in part and rid.startswith("FR-") and part.startswith("FR-"):
            a, b = part.split("..")
            if int(a[3:]) <= int(rid[3:]) <= int(b[3:]):
                return True
    return False


# ------------------------------------------------------------------ 7. ECP / BVA number lines
def number_lines():
    specs = [("Primary guest age (FR-01)", [17, 18, 19, 60, 119, 120, 121], "years"),
             ("Length of stay (FR-03)", [0, 1, 2, 15, 29, 30, 31], "nights"),
             ("Rooms per booking (FR-05)", [0, 1, 2, 3, 4, 5, 6], "rooms")]
    tags = ["min−1", "min", "min+1", "nominal", "max−1", "max", "max+1"]
    fig, axes = plt.subplots(3, 1, figsize=(9.6, 6.2))
    for ax, (title, pts, unit) in zip(axes, specs):
        ax.set_xlim(-0.8, 6.8)
        ax.set_ylim(-1.3, 1.5)
        ax.axis("off")
        for x0, x1, fc in ((-0.7, 0.5, "#f8d7d3"), (0.5, 5.5, "#cfeedd"), (5.5, 6.7, "#f8d7d3")):
            ax.add_patch(FancyBboxPatch((x0 + 0.04, -0.2), x1 - x0 - 0.08, 0.4, boxstyle="round,pad=0,rounding_size=0.12",
                                        fc=fc, ec="none"))
        ax.text(-0.1, 0.38, "I1 invalid", ha="center", fontsize=8.5, color=CRIT)
        ax.text(3, 0.38, "V1 valid class", ha="center", fontsize=8.5, color=GOOD)
        ax.text(6.1, 0.38, "I2 invalid", ha="center", fontsize=8.5, color=CRIT)
        for i, (p, tg) in enumerate(zip(pts, tags)):
            ok = 0 < i < 6
            ax.plot([i], [0], marker="o", ms=10, color=S1 if ok else S8, mec=SURF, mew=1.5)
            ax.text(i, -0.62, str(p), ha="center", fontsize=10, color=INK, fontweight="bold")
            ax.text(i, -1.05, tg, ha="center", fontsize=8, color=INK2)
        ax.text(-0.7, 1.05, f"{title}: valid {pts[1]}–{pts[5]} {unit}", fontsize=10.5, fontweight="bold", color=INK)
    fig.suptitle("ECP classes (bands) and robust BVA test points — blue accepted, red rejected (ordinal spacing)",
                 x=0.02, ha="left", fontsize=12.5, fontweight="bold", color=INK)
    save(fig, "ecp_bva_lines")


# ------------------------------------------------------------------ 8. fault seeding
def fault_seeding():
    faults = seed["faults"]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    names = [f"{f['id']}  {f['description']}" for f in faults][::-1]
    vals = [f["failing_tests"] for f in faults][::-1]
    lv = [f["expected_level"] for f in faults][::-1]
    col = {"Unit": S1, "Integration": S2, "System": S3, "E2E": S7}
    ax.barh(names, vals, color=[col[x] for x in lv], height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + 0.12, i, f"{v} failing", va="center", fontsize=8.5, color=INK2)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=f"caught at {k}") for k, c in col.items()], loc="lower right")
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("tests that failed against the seeded fault")
    ax.set_title("Fault seeding — 12/12 injected bugs detected (Rev B)")
    subtitle(ax, "SF-11 (DOM XSS) was missed in Rev A until TC-E2E-003 was strengthened")
    save(fig, "fault_seeding")


for fn in (pyramid, techniques, coverage, mutation, performance, rtm, number_lines, fault_seeding):
    fn()
print("figures:", sorted(p.name for p in OUT.glob("*.png")))
