"""Build the interactive results dashboard (single self-contained HTML) from the run artefacts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"


def J(p):
    return json.loads((ROOT / p).read_text())



results = J("reports/results.json")
cov = J("reports/coverage.json")["totals"]
mut = J("reports/mutation.json")["summary"]
seed = J("reports/fault_seeding.json")["summary"]
perf, perf0 = J("reports/perf.json"), J("reports/perf_before_tuning.json")
defects = J("reports/defects_found.json") + (J("reports/defects_manual.json") if (R / "defects_manual.json").exists() else [])
ms = J("docs/manual_and_static.json")

before = {s["vus"]: s["p95_ms"] for s in perf0["stress"]}
DATA = {
    "executed": results[0]["executed_at"][:10],
    "results": [{k: r.get(k) for k in ("id", "title", "module", "requirement", "technique", "level", "status", "duration_ms", "expected")}
                for r in results],
    "cov": {"stmt": round(cov["percent_statements_covered"], 1), "branch": round(cov["percent_branches_covered"], 1)},
    "mut": {"score": mut["mutation_score_pct"]},
    "seed": seed["detection_pct"],
    "perf": {"p95": round(perf["load"]["p95_ms"]),
             "stress": [{"vus": s["vus"], "before": before.get(s["vus"]), "after": s["p95_ms"]} for s in perf["stress"]]},
    "defects": [{k: d[k] for k in ("id", "title", "severity", "technique", "status")} for d in defects],
    "manual": [{k: m.get(k, "") for k in ("id", "title", "type", "status", "tester")} for m in ms["manual_cases"]],
}
tpl = (ROOT / "tools" / "dashboard_template.html").read_text()
out = ROOT / "deliverables" / "HRRS_Test_Results_Dashboard.html"
out.write_text(tpl.replace("/*DATA*/null", json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/")))
print("wrote", out)
