"""Mutation testing engine for the HRRS domain layer (built for this project).

Generates first-order mutants with classic operators, runs the unit-level suite
against each mutant in parallel sandboxes and reports the mutation score:

    MS = killed / (total − equivalent)

Operators
  ROR  relational operator replacement   <  <=  >  >=  ==  !=
  AOR  arithmetic operator replacement   + ↔ −, * ↔ /
  LCR  logical connector replacement     and ↔ or
  UOD  unary operator deletion           not x → x
  CRP  constant replacement              integer k → k+1 / k−1 (k in comparisons & returns)
  BRV  boolean return/literal flip       True ↔ False
"""
import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Survivors proven equivalent (no input can distinguish them from the original). key: (file, line, change)
EQUIVALENT = {
    ("app/domain/pricing.py", 105, "> → >="): "amount > cap vs amount >= cap: when amount == cap both branches yield "
                                               "amount == cap → no observable difference.",
    ("app/domain/payment.py", 20, "> → >="): "d > 9 vs d >= 9 in Luhn: a doubled digit is always even (0..18) so d is "
                                              "never exactly 9.",
    ("app/domain/payment.py", 20, "9 → 8"): "d > 9 vs d > 8: doubled digit is even; no even value lies in (8, 9] → "
                                             "identical behaviour.",
}
# mutation-guided tests written after each iteration (iteration 1 = baseline suite)
HISTORY_TESTS_ADDED = {1: 0, 2: 23, 3: 3}
TARGETS = ["app/domain/validation.py", "app/domain/pricing.py", "app/domain/cancellation.py",
           "app/domain/payment.py", "app/domain/state.py", "app/domain/metrics.py"]
TESTS = ["tests/unit"]

ROR = {ast.Lt: [ast.LtE, ast.Gt], ast.LtE: [ast.Lt, ast.GtE], ast.Gt: [ast.GtE, ast.Lt], ast.GtE: [ast.Gt, ast.LtE],
       ast.Eq: [ast.NotEq], ast.NotEq: [ast.Eq], ast.In: [ast.NotIn], ast.NotIn: [ast.In]}
AOR = {ast.Add: [ast.Sub], ast.Sub: [ast.Add], ast.Mult: [ast.Div], ast.Div: [ast.Mult]}
SYM = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=", ast.Add: "+",
       ast.Sub: "-", ast.In: "in", ast.NotIn: "not in", ast.Mult: "*", ast.Div: "/", ast.And: "and", ast.Or: "or"}


class Collector(ast.NodeVisitor):
    """Find every mutation point as (node path, description, operator)."""

    def __init__(self):
        self.points = []
        self._in_docstring = False

    def generic_visit(self, node):
        for _field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self._visit_child(item)
            elif isinstance(value, ast.AST):
                self._visit_child(value)

    def _visit_child(self, node):
        self.visit(node)

    def visit_Compare(self, node):
        for i, op in enumerate(node.ops):
            for repl in ROR.get(type(op), []):
                self.points.append(("ROR", node, i, repl, f"{SYM[type(op)]} → {SYM[repl]}"))
        for c in [node.left, *node.comparators]:
            if isinstance(c, ast.Constant) and isinstance(c.value, int) and not isinstance(c.value, bool):
                for d in (1, -1):
                    self.points.append(("CRP", c, None, c.value + d, f"{c.value} → {c.value + d}"))
        self.generic_visit(node)

    def visit_BinOp(self, node):
        for repl in AOR.get(type(node.op), []):
            self.points.append(("AOR", node, None, repl, f"{SYM[type(node.op)]} → {SYM[repl]}"))
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        repl = ast.Or if isinstance(node.op, ast.And) else ast.And
        self.points.append(("LCR", node, None, repl, f"{SYM[type(node.op)]} → {SYM[repl]}"))
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            self.points.append(("UOD", node, None, None, "not x → x"))
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            self.points.append(("BRV", node, None, not node.value, f"{node.value} → {not node.value}"))


def mutants_for(path: Path):
    src = path.read_text()
    tree = ast.parse(src)
    col = Collector()
    col.visit(tree)
    out = []
    for idx, (op, node, i, repl, desc) in enumerate(col.points):
        mtree = copy.deepcopy(tree)
        # locate the twin node by walking both trees in the same order
        twin = [n for n in ast.walk(mtree)][[n for n in ast.walk(tree)].index(node)]
        if op == "ROR":
            twin.ops[i] = repl()
        elif op == "AOR":
            twin.op = repl()
        elif op == "LCR":
            twin.op = repl()
        elif op == "UOD":
            parent = next(p for p in ast.walk(mtree) for f, v in ast.iter_fields(p)
                          if v is twin or (isinstance(v, list) and twin in v))
            for f, v in ast.iter_fields(parent):
                if v is twin:
                    setattr(parent, f, twin.operand)
                elif isinstance(v, list) and twin in v:
                    v[v.index(twin)] = twin.operand
        elif op in ("CRP", "BRV"):
            twin.value = repl
        try:
            code = ast.unparse(ast.fix_missing_locations(mtree))
        except Exception:  # noqa: BLE001, S112 — unparsable mutant is simply skipped
            continue
        out.append({"id": f"{path.stem}-{idx:03d}", "file": str(path.relative_to(ROOT)), "line": node.lineno,
                    "operator": op, "change": desc, "source": code})
    return out


def make_sandbox(n):
    d = Path(tempfile.mkdtemp(prefix=f"mut{n}_"))
    shutil.copytree(ROOT / "app", d / "app")
    shutil.copytree(ROOT / "tests", d / "tests", ignore=shutil.ignore_patterns("e2e", "__pycache__"))
    return d


def run_tests(sandbox: Path, timeout=120):
    env = {**os.environ, "HRRS_RESULTS": "mut_ignore.json", "PYTHONDONTWRITEBYTECODE": "1"}
    t0 = time.perf_counter()
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-x", "-q", "-p", "no:cacheprovider",
                            "-p", "no:warnings", "--hypothesis-seed=0"],
                           cwd=sandbox, env=env, capture_output=True, text=True, timeout=timeout)
        status = "SURVIVED" if r.returncode == 0 else "KILLED"
        killer = ""
        for line in r.stdout.splitlines():
            if line.startswith("FAILED"):
                killer = line.split("::")[-1].split(" ")[0]
                break
    except subprocess.TimeoutExpired:
        status, killer = "TIMEOUT(KILLED)", ""
    return status, killer, round(time.perf_counter() - t0, 2)


def main():
    all_mutants = []
    for t in TARGETS:
        all_mutants += mutants_for(ROOT / t)
    print(f"{len(all_mutants)} mutants")
    workers = max(2, (os.cpu_count() or 2))
    boxes = [make_sandbox(i) for i in range(workers)]
    originals = {t: (ROOT / t).read_text() for t in TARGETS}
    free = list(range(workers))
    import threading
    lock = threading.Lock()

    def job(m):
        with lock:
            k = free.pop()
        box = boxes[k]
        target = box / m["file"]
        target.write_text(m["source"])
        try:
            status, killer, secs = run_tests(box)
        finally:
            target.write_text(originals[m["file"]])
            with lock:
                free.append(k)
        m.update(status=status, killed_by=killer, seconds=secs)
        return m

    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        done = []
        for i, m in enumerate(ex.map(job, all_mutants), 1):
            done.append(m)
            if i % 25 == 0:
                print(f"  {i}/{len(all_mutants)}  {time.time() - t0:.0f}s")
    for b in boxes:
        shutil.rmtree(b, ignore_errors=True)
    for m in done:
        m.pop("source")
        # survivors that were proven equivalent by manual analysis (see EQUIVALENT above)
        if m["status"] == "SURVIVED" and (m["file"], m["line"], m["change"]) in EQUIVALENT:
            m["status"] = "EQUIVALENT"
            m["equivalence_reason"] = EQUIVALENT[(m["file"], m["line"], m["change"])]
    killed = sum(m["status"] == "KILLED" for m in done)
    equivalent = sum(m["status"] == "EQUIVALENT" for m in done)
    survived = len(done) - killed - equivalent
    summary = {"total": len(done), "killed": killed, "survived": survived,
               "raw_score_pct": round(100 * killed / len(done), 2), "minutes": round((time.time() - t0) / 60, 1),
               "by_operator": {}, "by_file": {}, "equivalent": equivalent,
               "mutation_score_pct": round(100 * killed / max(1, len(done) - equivalent), 2)}
    for key, field in (("by_operator", "operator"), ("by_file", "file")):
        for m in done:
            d = summary[key].setdefault(m[field], {"total": 0, "killed": 0})
            d["total"] += 1
            d["killed"] += m["status"] == "KILLED"
    # improvement history: earlier iterations are kept in reports/mutation_iter<N>.json
    iters = []
    for f in sorted((ROOT / "reports").glob("mutation_iter*.json")):
        s = json.loads(f.read_text())["summary"]
        iters.append({"iteration": len(iters) + 1, "killed": s["killed"], "survived": s["total"] - s["killed"],
                      "raw_score_pct": s["raw_score_pct"], "tests_added": s.get("tests_added", 0)})
    iters.append({"iteration": len(iters) + 1, "killed": killed, "survived": len(done) - killed,
                  "raw_score_pct": summary["raw_score_pct"], "tests_added": HISTORY_TESTS_ADDED.get(len(iters) + 1, 0)})
    for it in iters:
        it["tests_added"] = HISTORY_TESTS_ADDED.get(it["iteration"], it["tests_added"])
    summary["iterations"] = iters
    (ROOT / "reports" / "mutation.json").write_text(json.dumps({"summary": summary, "mutants": done}, indent=1,
                                                                ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
