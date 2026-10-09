"""Release / packaging checks — regression protection for DEF-006 … DEF-010.

    python tools/check_package.py          exit 0 when every check passes
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_BUILTINS = {"fs", "path", "os", "child_process", "util", "crypto", "zlib", "stream", "url"}
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


# DEF-006 — the accessibility test must not depend on node_modules
axe = ROOT / "tests" / "e2e" / "vendor" / "axe.min.js"
src = (ROOT / "tests" / "e2e" / "test_ui_e2e.py").read_text()
check("DEF-006 axe-core vendored with the tests", axe.exists() and "node_modules" not in src, str(axe.relative_to(ROOT)))

# DEF-007 — every README shell line is one runnable command (no '| -m' alternatives)
readme = (ROOT / "README.md").read_text()
blocks = re.findall(r"```bash\n(.*?)```", readme, re.S)
bad = [ln for b in blocks for ln in b.splitlines() if re.search(r"\|\s*-m\b", ln)]
check("DEF-007 README commands are runnable as written", not bad, "; ".join(bad))

# DEF-008 — partial runs must not overwrite results.json; the evidence file holds the full catalogue
conf = (ROOT / "tests" / "conftest.py").read_text()
rows = json.loads((ROOT / "reports" / "results.json").read_text())
check("DEF-008 partial runs go to results_partial.json", "results_partial.json" in conf and "full_run" in conf)
check("DEF-008 results.json holds a full run", len(rows) >= 550, f"{len(rows)} rows")

# DEF-009 — mutation.py writes every field the generators read
mt = (ROOT / "tools" / "mutation.py").read_text()
need = ["equivalent", "mutation_score_pct", "iterations"]
check("DEF-009 mutation.py emits equivalent / score / iterations", all(f'"{k}"' in mt or f"[\"{k}\"]" in mt for k in need))
summ = json.loads((ROOT / "reports" / "mutation.json").read_text())["summary"]
check("DEF-009 reports/mutation.json has the fields", all(k in summ for k in need))

# DEF-010 — no hard dependency on lab-only paths; Node packages declared
offenders = []
for f in list((ROOT / "tools").rglob("*.py")) + list((ROOT / "tools").rglob("*.js")):
    if "node_modules" in f.parts or f.name == "check_package.py":
        continue
    for i, ln in enumerate(f.read_text(errors="ignore").splitlines(), 1):
        if re.search(r"""["'](/mnt/skills|/tmp/)""", ln) and "HELPER" not in ln:
            offenders.append(f"{f.relative_to(ROOT)}:{i}")
check("DEF-010 no hard-coded lab-only paths", not offenders, ", ".join(offenders))
pkg = json.loads((ROOT / "package.json").read_text())["dependencies"]
required = set()
for f in (ROOT / "tools").rglob("*.js"):
    if "node_modules" in f.parts:
        continue
    for m in re.findall(r"""require\(["']([^"'./][^"']*)["']\)""", f.read_text()):
        required.add(m.split("/")[0] if not m.startswith("@") else "/".join(m.split("/")[:2]))
missing = sorted(required - NODE_BUILTINS - set(pkg))
check("DEF-010 package.json declares every Node package used", not missing, ", ".join(missing))
check("DEF-010 README tells the reader to run npm install", "npm install" in readme)

width = max(len(n) for n, _, _ in checks)
for n, ok, d in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {n.ljust(width)}  {d}")
failed = sum(not ok for _, ok, _ in checks)
print(f"\n{len(checks) - failed}/{len(checks)} packaging checks passed")
sys.exit(1 if failed else 0)
