"""Build the master test-case workbook (Excel) from the real execution artefacts."""
import json
import subprocess
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
R, D = ROOT / "reports", ROOT / "docs"
OUT = ROOT / "deliverables"
OUT.mkdir(exist_ok=True)
FILE = OUT / "HRRS_Test_Case_Workbook_Raktim.xlsx"

results = json.loads((R / "results.json").read_text())
reqs = json.loads((D / "requirements.json").read_text())
defects = json.loads((R / "defects_found.json").read_text())
defects_manual = json.loads((R / "defects_manual.json").read_text()) if (R / "defects_manual.json").exists() else []
ms = json.loads((D / "manual_and_static.json").read_text())
mut = json.loads((R / "mutation.json").read_text())
seed = json.loads((R / "fault_seeding.json").read_text())
perf, perf0 = json.loads((R / "perf.json").read_text()), json.loads((R / "perf_before_tuning.json").read_text())
cov, cov0 = json.loads((R / "coverage.json").read_text()), json.loads((R / "coverage_iter1.json").read_text())
raw = json.loads(subprocess.run(["radon", "raw", "app", "-j"], cwd=ROOT, capture_output=True, text=True).stdout)
SLOC = sum(v["sloc"] for v in raw.values())

F = "Arial"
NAVY, TEAL, PALE, GREYF = "14213D", "0F6E78", "EEF4FB", "F4F2EC"
thin = Side(style="thin", color="D5D2C8")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
H_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
H_FILL = PatternFill("solid", fgColor=NAVY)
BODY = Font(name=F, size=9.5)
INPUT = Font(name=F, size=9.5, color="0000FF")
LINK = Font(name=F, size=9.5, color="008000")
WRAP = Alignment(wrap_text=True, vertical="top")
PASS_FILL, FAIL_FILL, SKIP_FILL = PatternFill("solid", fgColor="DCF3EA"), PatternFill("solid", fgColor="FBE1E1"), \
    PatternFill("solid", fgColor="FFF3D6")
FILL_ME = PatternFill("solid", fgColor="FFFF00")

wb = Workbook()


def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = Font(name=F, bold=True, size=15, color=NAVY)
    if sub:
        ws["A2"] = sub
        ws["A2"].font = Font(name=F, italic=True, size=9.5, color="52514E")


def header(ws, row, cols, widths=None):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=j, value=c)
        cell.font, cell.fill, cell.border = H_FONT, H_FILL, BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    ws.row_dimensions[row].height = 30


def rows(ws, start, data, font=BODY):
    for i, r in enumerate(data):
        for j, v in enumerate(r, 1):
            cell = ws.cell(row=start + i, column=j, value=v)
            cell.font, cell.border, cell.alignment = font, BORDER, WRAP
    return start + len(data)


def table(ws, ref, name):
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(t)


# ===================================================================== 1. Cover / dashboard
ws = wb.active
ws.title = "Summary"
title(ws, "Hotel Room Reservation System (HRRS) — Test Case Workbook",
      "Raktim Chandra · Software Verification & Validation · SRM Institute of Science and Technology · generated from the real test run")
info = [("Course", "Software Verification and Validation — B.Tech CSE (Software Engineering), Sem 7, AI2, CINTEL"),
        ("Faculty", "Mr. Kaviyaraj R."),
        ("Author", "Raktim Chandra (RA2311033010038)"),
        ("System under test", "HRRS v1.0 — FastAPI + SQLite + Web UI (repository folder hrrs/)"),
        ("Execution date", results[0]["executed_at"][:10]),
        ("Environment", "Python 3.13 · pytest 9.1 · Playwright/Chromium 141 · Linux x86-64 (2 vCPU)")]
for i, (k, v) in enumerate(info, 4):
    ws.cell(row=i, column=1, value=k).font = Font(name=F, bold=True, size=10)
    ws.cell(row=i, column=2, value=v).font = Font(name=F, size=10)
    ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=8)

ws["A11"] = "Execution summary (live formulas over the 'Test Cases' sheet)"
ws["A11"].font = Font(name=F, bold=True, size=12, color=TEAL)
levels = ["Unit", "Integration", "System", "System (E2E UI)", "Acceptance (UAT)"]
header(ws, 12, ["Test level", "Designed", "Executed", "Passed", "Failed", "Skipped", "Pass rate", "Share of suite"],
       [26, 13, 13, 13, 13, 13, 13, 15])
for i, lv in enumerate(levels, 13):
    ws.cell(row=i, column=1, value=lv)
    ws.cell(row=i, column=2, value=f"=COUNTIF('Test Cases'!$F:$F,A{i})")
    ws.cell(row=i, column=3, value=f"=B{i}-F{i}")
    ws.cell(row=i, column=4, value=f'=COUNTIFS(\'Test Cases\'!$F:$F,A{i},\'Test Cases\'!$P:$P,"PASS")')
    ws.cell(row=i, column=5, value=f'=COUNTIFS(\'Test Cases\'!$F:$F,A{i},\'Test Cases\'!$P:$P,"FAIL")')
    ws.cell(row=i, column=6, value=f'=COUNTIFS(\'Test Cases\'!$F:$F,A{i},\'Test Cases\'!$P:$P,"SKIPPED")')
    ws.cell(row=i, column=7, value=f"=IF(C{i}=0,0,D{i}/C{i})")
    ws.cell(row=i, column=8, value=f"=B{i}/$B$18")
tot = 18
ws.cell(row=tot, column=1, value="TOTAL")
for j in range(2, 7):
    c = get_column_letter(j)
    ws.cell(row=tot, column=j, value=f"=SUM({c}13:{c}17)")
ws.cell(row=tot, column=7, value=f"=IF(C{tot}=0,0,D{tot}/C{tot})")
ws.cell(row=tot, column=8, value=f"=B{tot}/$B$18")
for r in range(13, tot + 1):
    for c in range(1, 9):
        cell = ws.cell(row=r, column=c)
        cell.border, cell.font = BORDER, Font(name=F, size=10, bold=(r == tot))
    ws.cell(row=r, column=7).number_format = "0.0%"
    ws.cell(row=r, column=8).number_format = "0.0%"

ws["A21"] = "Quality metrics"
ws["A21"].font = Font(name=F, bold=True, size=12, color=TEAL)
header(ws, 22, ["Metric", "Value", "Formula / definition", "", "", "", "", ""])
ws.merge_cells("C22:H22")
cs, cb = cov["totals"], cov0["totals"]
mm = mut["summary"]
metric_rows = [
    ("Source lines of code (SLOC, app/)", SLOC, "Input — radon raw app (blue = hard-coded measurement)", True),
    ("Product defects found before release", sum(1 for d in defects if d["module"] != "Test suite (TC-E2E-003)"),
     "Input — Defect Log rows excluding test-suite defects", True),
    ("Defects found after release (so far)", 0, "Input — none reported yet; update during beta", True),
    ("Defect density (defects / KLOC)", "=B24/(B23/1000)", "defects ÷ (SLOC ÷ 1000)", False),
    ("Defect Removal Efficiency (DRE)", "=B24/(B24+B25)", "pre-release ÷ (pre + post-release)", False),
    ("Statement coverage", cs["covered_lines"] / cs["num_statements"], "Input — coverage.py (covered ÷ statements)", True),
    ("Branch coverage", cs["covered_branches"] / cs["num_branches"], "Input — coverage.py (covered ÷ branches)", True),
    ("Mutants generated", mm["total"], "Input — tools/mutation.py", True),
    ("Mutants killed", mm["killed"], "Input — tools/mutation.py", True),
    ("Equivalent mutants", mm["equivalent"], "Input — manual analysis (see Mutation sheet)", True),
    ("Mutation score", "=B31/(B30-B32)", "killed ÷ (total − equivalent)", False),
    ("Seeded faults (S)", seed["summary"]["seeded"], "Input — tools/fault_seeding.py", True),
    ("Seeded faults detected (s)", seed["summary"]["seeded_detected"], "Input — Rev B run", True),
    ("Mills estimate of native defects N̂", "=B24*B34/B35", "n × S ÷ s", False),
    ("Estimated latent defects", "=B36-B24", "N̂ − n", False),
    ("Requirements with ≥ 1 executed test", "=COUNTIF(RTM!$E:$E,\">0\")", "from RTM sheet", False),
    ("Requirement coverage", f"=B38/COUNTA(RTM!$A$5:$A${4 + len(reqs)})", "covered ÷ total requirements", False),
    ("Load-test p95 (25 VUs, ms)", perf["load"]["p95_ms"], "Input — tools/perf_test.py after tuning (SLA < 300)", True),
]
for i, (k, v, d, is_input) in enumerate(metric_rows, 23):
    ws.cell(row=i, column=1, value=k).font = Font(name=F, size=10)
    c = ws.cell(row=i, column=2, value=v)
    c.font = INPUT if is_input else Font(name=F, size=10)
    ws.cell(row=i, column=3, value=d).font = Font(name=F, size=9, color="52514E")
    ws.merge_cells(start_row=i, start_column=3, end_row=i, end_column=8)
    for cc in range(1, 9):
        ws.cell(row=i, column=cc).border = BORDER
for r in (26, 27, 28, 29, 33, 39):
    ws.cell(row=r, column=2).number_format = "0.0%" if r != 26 else "0.00"
ws.cell(row=36, column=2).number_format = "0.00"
ws.cell(row=37, column=2).number_format = "0.00"
ws["A43"] = "Legend: blue numbers are measured inputs from the run artefacts; black cells are formulas."
ws["A43"].font = Font(name=F, italic=True, size=9, color="52514E")
ws.freeze_panes = "A4"

# ===================================================================== 2. Test Cases
ws = wb.create_sheet("Test Cases")
cols = ["TC ID", "Title / objective", "Module", "Requirement", "Technique", "Level", "Type", "Priority",
        "Pre-conditions", "Test data / inputs", "Steps", "Expected result", "Actual result", "Automated test (pytest node)",
        "Duration (ms)", "Status", "Executed at"]
title(ws, "Test Cases — designed, automated and executed",
      f"{len(results)} cases · status and actual result are written by the test run (conftest.py), not by hand")
header(ws, 4, cols, [17, 46, 18, 13, 24, 15, 13, 8, 22, 34, 26, 30, 30, 44, 10, 9, 17])
order = {lv: i for i, lv in enumerate(levels)}
data = []
for r in sorted(results, key=lambda r: (order.get(r["level"], 9), r["id"])):
    actual = ("As expected" if r["status"] == "PASS" else
              ("Not run: " + r["message"].split("Skipped: ")[-1][:200]) if r["status"] == "SKIPPED" else r["message"][:300])
    data.append([r["id"], r["title"], r["module"], r["requirement"], r["technique"], r["level"], r["type"],
                 r["priority"], r["preconditions"], r["inputs"], r["steps"], r["expected"], actual, r["nodeid"],
                 r["duration_ms"], r["status"], r.get("executed_at", "")])
end = rows(ws, 5, data)
table(ws, f"A4:Q{end - 1}", "TestCases")
ws.conditional_formatting.add(f"P5:P{end}", CellIsRule(operator="equal", formula=['"PASS"'], fill=PASS_FILL))
ws.conditional_formatting.add(f"P5:P{end}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=FAIL_FILL))
ws.conditional_formatting.add(f"P5:P{end}", CellIsRule(operator="equal", formula=['"SKIPPED"'], fill=SKIP_FILL))
ws.freeze_panes = "C5"

# ===================================================================== 3. Manual & exploratory
ws = wb.create_sheet("Manual & Exploratory")
title(ws, "Manual test cases and exploratory charters — execution record",
      "Results are recorded only where a case was really executed. Yellow cells: still to be executed "
      "(needs real participants or devices) — kits in HRRS_Manual_Test_Execution_Kit_Raktim.docx")
header(ws, 4, ["ID", "Title / charter", "Type", "Requirement / timebox", "Steps", "Expected", "Tester",
               "Environment", "Actual result", "Status", "Date", "Evidence / defects"],
       [16, 44, 14, 14, 34, 30, 26, 30, 60, 13, 11, 34])
mrows = []
for m in ms["manual_cases"]:
    ev = m.get("evidence", "") + (f" · Defects: {m['defects']}" if m.get("defects") else "")
    mrows.append([m["id"], m["title"], m["type"], m["requirement"], m["steps"], m["expected"], m.get("tester", ""),
                  m.get("environment", ""), m.get("actual", ""), m.get("status", ""), m.get("date", ""), ev])
for x in ms["exploratory_charters"]:
    mrows.append([x["id"], x["charter"], "Exploratory", x["timebox"], "Session-based test management (SBTM)",
                  "Session sheet with notes, bugs, issues", x["tester"], "", x.get("result", ""), x["status"], "", ""])
end = rows(ws, 5, mrows)
for r in range(5, 5 + len(ms["manual_cases"])):
    st = ws.cell(row=r, column=10).value or ""
    if st in ("NOT RUN", "IN PROGRESS", ""):
        for c in (7, 9, 10, 11):
            ws.cell(row=r, column=c).fill = FILL_ME if st == "NOT RUN" else SKIP_FILL
for rule, fill in (('"PASS"', PASS_FILL), ('"PASS (retest)"', PASS_FILL), ('"FAIL"', FAIL_FILL)):
    ws.conditional_formatting.add(f"J5:J{end}", CellIsRule(operator="equal", formula=[rule], fill=fill))
ws.freeze_panes = "B5"

# heuristic evaluation and usability observations (from TC-MAN-USE-001)
use = next(m for m in ms["manual_cases"] if m["id"] == "TC-MAN-USE-001")
r0 = end + 2
ws.cell(row=r0, column=1, value="TC-MAN-USE-001 — Nielsen heuristic scores, evaluator 1 (0 = no problem … 4 = catastrophe)").font = \
    Font(name=F, bold=True, size=11, color=TEAL)
header(ws, r0 + 1, ["Heuristic", "Severity (eval. 1)", "Severity (eval. 2)", "Notes"])
hend = rows(ws, r0 + 2, [[h, sc, None, note] for h, sc, note in use["heuristic_scores"]])
for r in range(r0 + 2, hend):
    ws.cell(row=r, column=3).fill = FILL_ME
ws.cell(row=hend, column=1, value="Highest severity (eval. 1)")
ws.cell(row=hend, column=2, value=f"=MAX(B{r0 + 2}:B{hend - 1})")
ws.cell(row=hend, column=3, value=f'=IF(COUNT(C{r0 + 2}:C{hend - 1})=0,"pending",MAX(C{r0 + 2}:C{hend - 1}))')
ws.cell(row=hend, column=4, value=f'=IF(MAX(B{r0 + 2}:B{hend - 1},C{r0 + 2}:C{hend - 1})>=3,"FAIL — major problem","No heuristic ≥ 3")')
for c in range(1, 5):
    ws.cell(row=hend, column=c).font = Font(name=F, bold=True, size=9.5)
r1 = hend + 2
ws.cell(row=r1, column=1, value="Usability / accessibility observations (backlog, not release-blocking)").font = \
    Font(name=F, bold=True, size=11, color=TEAL)
header(ws, r1 + 1, ["ID", "Observation", "Severity", "Disposition"])
rows(ws, r1 + 2, use["observations"])

# ===================================================================== 4. RTM
ws = wb.create_sheet("RTM")
title(ws, "Requirements Traceability Matrix (forward + backward)",
      "Counts are live COUNTIF formulas over 'Test Cases'!D (requirement) — a requirement listed in a range such as FR-01..FR-09 is counted via the helper column")
header(ws, 4, ["Req ID", "Type", "Area", "Requirement", "Executed tests", "Unit", "Integration", "System",
               "E2E UI", "UAT", "Passed", "Status", "Sample test IDs"], [12, 13, 20, 60, 10, 8, 10, 8, 8, 7, 9, 12, 46])


def matches(rid, ref):
    ref = ref.replace("–", "-")
    for part in [p.strip() for p in ref.split(",")]:
        if part == rid:
            return True
        if ".." in part and rid.startswith("FR-") and part.startswith("FR-"):
            a, b = part.split("..")
            if int(a[3:]) <= int(rid[3:]) <= int(b[3:]):
                return True
    return False


for i, q in enumerate(reqs, 5):
    hits = [r for r in results if matches(q["id"], r["requirement"])]
    lv = Counter(r["level"] for r in hits)
    vals = [q["id"], q["type"], q["area"], q["text"], f"=SUM(F{i}:J{i})", lv["Unit"], lv["Integration"],
            lv["System"], lv["System (E2E UI)"], lv["Acceptance (UAT)"], sum(r["status"] == "PASS" for r in hits),
            f'=IF(E{i}=0,"NOT COVERED",IF(K{i}=E{i},"COVERED","PARTIAL"))',
            ", ".join(r["id"] for r in hits[:6]) + (" …" if len(hits) > 6 else "")]
    for j, v in enumerate(vals, 1):
        c = ws.cell(row=i, column=j, value=v)
        c.font, c.border, c.alignment = (INPUT if 6 <= j <= 11 else BODY), BORDER, WRAP
end = 5 + len(reqs)
ws.conditional_formatting.add(f"F5:J{end}", ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                                                            end_type="max", end_color="6DA7EC"))
ws.conditional_formatting.add(f"L5:L{end}", CellIsRule(operator="equal", formula=['"COVERED"'], fill=PASS_FILL))
ws["A" + str(end + 1)] = "Per-level counts and 'Passed' are measured from reports/results.json (blue)."
ws["A" + str(end + 1)].font = Font(name=F, italic=True, size=9, color="52514E")
ws.freeze_panes = "B5"

# ===================================================================== 5. Defect log
ws = wb.create_sheet("Defect Log")
title(ws, "Defect log — every defect found during this campaign (none invented)")
dcols = ["ID", "Category", "Title", "Found by", "Technique", "Module", "Requirement", "Severity", "Priority", "Steps",
         "Expected", "Actual (before fix)", "Root cause", "Fix", "Status"]
header(ws, 4, dcols, [9, 16, 40, 30, 22, 16, 12, 9, 8, 26, 22, 26, 40, 40, 16])
rows(ws, 5, [[d["id"], d.get("category", "Product / test suite"), d["title"], d["found_by"], d["technique"], d["module"],
              d["requirement"], d["severity"], d["priority"], d["steps"], d["expected"], d["actual_before_fix"],
              d["root_cause"], d["fix"], d["status"]] for d in defects + defects_manual])

# ===================================================================== 6. Decision tables
ws = wb.create_sheet("Decision Tables")
title(ws, "Decision tables used for test design")
ws["A4"] = "DT-1  Cancellation refund (FR-07) — limited entry"
ws["A4"].font = Font(name=F, bold=True, size=11, color=TEAL)
dt1 = [["Condition / Action", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"],
       ["C1 Hotel-initiated?", "Y", "N", "N", "N", "N", "N", "N", "N"],
       ["C2 Refundable rate?", "–", "N", "Y", "Y", "Y", "Y", "Y", "Y"],
       ["C3 Days before check-in", "–", "≥0", "≥7", "2–6", "2–6", "0–1", "0–1", "<0"],
       ["C4 PLATINUM member?", "–", "–", "–", "N", "Y", "N", "Y", "–"],
       ["A1 Refund %", 100, 0, 100, 50, 75, 0, 25, "reject"],
       ["A2 Processing fee ₹", 0, 0, 0, 200, 0, 0, 0, "–"],
       ["A3 Compensation voucher", "X", "", "", "", "", "", "", ""],
       ["Test case", "TC-CAN-DT-001", "-002", "-003", "-004", "-005", "-006", "-007", "-008"]]
header(ws, 5, dt1[0], [30] + [14] * 16)
rows(ws, 6, dt1[1:])
ws["A16"] = "DT-2  Complimentary benefits (FR-15) — exhaustive 2⁴ = 16 rules, derived from the cause-effect graph"
ws["A16"].font = Font(name=F, bold=True, size=11, color=TEAL)
from itertools import product  # noqa: E402

combos = list(product((True, False), repeat=4))
header(ws, 17, ["Cause / Effect"] + [f"R{i}" for i in range(1, 17)])
yn = lambda b: "T" if b else "F"  # noqa: E731
dt2 = [["C1 tier ∈ {GOLD, PLATINUM}"] + [yn(c[0]) for c in combos],
       ["C2 stay ≥ 3 nights"] + [yn(c[1]) for c in combos],
       ["C3 booked ≥ 30 days ahead"] + [yn(c[2]) for c in combos],
       ["C4 room ≠ SUITE"] + [yn(c[3]) for c in combos],
       ["E1 upgrade = C1∧C2∧C4"] + ["X" if c[0] and c[1] and c[3] else "" for c in combos],
       ["E2 breakfast = C1∨(C2∧C3)"] + ["X" if c[0] or (c[1] and c[2]) else "" for c in combos],
       ["E3 none"] + ["X" if not (c[0] and c[1] and c[3]) and not (c[0] or (c[1] and c[2])) else "" for c in combos],
       ["Test case"] + [f"TC-BEN-DT-{i:03d}" for i in range(1, 17)]]
rows(ws, 18, dt2)
ws["A28"] = "DT-3  Sign-in / lock-out (FR-02)"
ws["A28"].font = Font(name=F, bold=True, size=11, color=TEAL)
header(ws, 29, ["Condition / Action", "R1", "R2", "R3", "R4", "R5", "R6"])
rows(ws, 30, [["E-mail registered?", "N", "Y", "Y", "Y", "Y", "Y"],
              ["Password correct?", "–", "Y", "N", "N", "Y", "Y"],
              ["Prior consecutive failures", "–", "0", "0", "2", "3 (locked)", "3, lock expired"],
              ["Outcome", "401 AUTH_FAILED", "token", "401 AUTH_FAILED", "423 LOCKED", "423 LOCKED", "token"],
              ["Test case", "TC-AUTH-DT-001", "-002", "-003", "-004", "-005", "-006"]])

# ===================================================================== 7. ECP / BVA design
ws = wb.create_sheet("ECP & BVA Design")
title(ws, "Equivalence classes and boundary values (design worksheet)",
      "BVA counts: normal 4n+1 · robust 6n+1 · worst-case 5ⁿ · robust worst-case 7ⁿ (n = number of variables)")
header(ws, 4, ["Input (req)", "Valid class(es)", "Invalid class(es)", "Robust BVA test values", "TC range"],
       [26, 34, 44, 42, 26])
rows(ws, 5, [
    ["Guest name length (FR-01)", "V1: 2–50 chars", "I1: < 2 · I2: > 50", "1, 2, 3, 25, 49, 50, 51", "TC-REG-BVA-001..007"],
    ["Guest name characters (FR-01)", "V1 letters+space · V2 ' · V3 - · V4 initial '. '", "I1 digits · I2 symbols · I3 emoji · I4 blank · I5 HTML", "—", "TC-REG-ECP-022..030"],
    ["Age (FR-01)", "V1: 18–120", "I1: < 18 · I2: > 120 · I3 non-integer/bool", "17, 18, 19, 60, 119, 120, 121", "TC-REG-BVA-008..014"],
    ["E-mail (FR-01)", "V1 simple · V2 plus-tag · V3 upper-case", "I1 no @ · I2 no local · I3 no domain · I4 no TLD · I5 1-char TLD · I6 space · I7 two @ · I8 empty · I9 None", "254 / 255 chars", "TC-REG-ECP-001..012, TC-MUT-001"],
    ["Mobile (FR-01)", "V1 9xxxxxxxxx · V2 6xxxxxxxxx · V3 +91 prefix", "I1 starts 0–5 · I2 9 digits · I3 11 digits · I4 letters · I5 spaces · I6 empty", "—", "TC-REG-ECP-013..021"],
    ["Password length (FR-02)", "V1: 8–20", "I1: < 8 · I2: > 20", "7, 8, 9, 14, 19, 20, 21", "TC-AUTH-BVA-001..007"],
    ["Password composition (FR-02)", "V1 upper+lower+digit+special", "I1 no upper · I2 no lower · I3 no digit · I4 no special · I5 whitespace · I6 non-string", "—", "TC-AUTH-ECP-001..007"],
    ["Nights (FR-03)", "V1: 1–30", "I1: ≤ 0 · I2: > 30", "0, 1, 2, 15, 29, 30, 31", "TC-SRCH-BVA-001..007"],
    ["Days ahead (FR-03)", "V1: 0–365", "I1: past · I2: > 365", "−1, 0, 1, 180, 364, 365, 366", "TC-SRCH-BVA-008..014"],
    ["Guests (FR-05)", "V1: 1–10", "I1: 0 · I2: > 10", "0, 1, 2, 5, 9, 10, 11", "TC-BOOK-BVA-001..007"],
    ["Rooms (FR-05)", "V1: 1–5", "I1: 0 · I2: > 5", "0, 1, 2, 3, 4, 5, 6", "TC-BOOK-BVA-008..014"],
    ["GST slab tariff (FR-06)", "V1 < 1000 → 0 % · V2 1000–7500 → 5 % · V3 > 7500 → 18 %", "I1 negative", "−1, 0, 998, 999, 1000, 1001, 4000, 7499, 7500, 7501, 8300", "TC-PRC-BVA-001..011"],
    ["Long-stay nights (FR-06)", "V1 1–6 → 0 % · V2 7–13 → 10 % · V3 ≥ 14 → 15 %", "—", "1, 6, 7, 8, 13, 14, 15, 30", "TC-PRC-BVA-012..019"],
    ["Refund days (FR-07)", "V1 ≥ 7 · V2 2–6 · V3 0–1", "I1 < 0", "−1, 0, 1, 2, 3, 6, 7, 8", "TC-CAN-BVA-001..008"],
    ["Late check-out time (FR-14)", "V1 ≤ 12:00 · V2 12:01–15:00 · V3 15:01–18:00 · V4 > 18:00", "I1 negative tariff", "11:59, 12:00, 12:01, 14:59, 15:00, 15:01, 17:59, 18:00, 18:01, 23:59", "TC-CHK-BVA-001..010"],
    ["Payment amount (FR-08)", "V1: ₹1 – ₹5,00,000", "I1 < 1 · I2 > 5,00,000 · I3 non-numeric", "0.99, 1, 1.01, 250000, 499999.99, 500000, 500000.01", "TC-PAY-BVA-001..007"],
    ["Card / UPI (FR-08)", "V1 Visa · V2 MasterCard · V3 spaced · V4 dashed · UPI name@bank", "I1 Luhn fail · I2 15 digits · I3 17 digits · I4 letters · I5 empty · CVV 2/4/alpha", "—", "TC-PAY-ECP-001..020"],
    ["nights × rooms (multi-variable)", "1–30 × 1–5", "—", "normal 4n+1 = 9 · worst-case 5² = 25", "TC-QTE-BVA2-001..009, TC-QTE-WC-001..025"],
])

# ===================================================================== 8. Coverage
ws = wb.create_sheet("Coverage")
title(ws, "Code coverage (coverage.py, statement + branch)", "First full run vs. after coverage-guided tests")
header(ws, 4, ["Module", "Statements", "Missed (final)", "Branches", "Partial (final)", "First run %", "Final %",
               "Gain (pp)"], [30, 12, 13, 11, 13, 12, 10, 10])
i = 5
for f, d in cov["files"].items():
    s = d["summary"]
    if not s["num_statements"]:
        continue
    vals = [f, s["num_statements"], s["missing_lines"], s["num_branches"], s["num_partial_branches"],
            cov0["files"][f]["summary"]["percent_covered"] / 100, s["percent_covered"] / 100, f"=(G{i}-F{i})*100"]
    for j, v in enumerate(vals, 1):
        c = ws.cell(row=i, column=j, value=v)
        c.font, c.border = (INPUT if 2 <= j <= 7 else BODY), BORDER
    ws.cell(row=i, column=6).number_format = ws.cell(row=i, column=7).number_format = "0.0%"
    ws.cell(row=i, column=8).number_format = "0.0"
    i += 1
ws.cell(row=i, column=1, value="TOTAL").font = Font(name=F, bold=True)
ws.cell(row=i, column=2, value=f"=SUM(B5:B{i - 1})")
ws.cell(row=i, column=3, value=f"=SUM(C5:C{i - 1})")
ws.cell(row=i, column=4, value=f"=SUM(D5:D{i - 1})")
ws.cell(row=i, column=5, value=f"=SUM(E5:E{i - 1})")
ws.cell(row=i, column=6, value=cb["percent_covered"] / 100).font = INPUT
ws.cell(row=i, column=7, value=cs["percent_covered"] / 100).font = INPUT
ws.cell(row=i, column=6).number_format = ws.cell(row=i, column=7).number_format = "0.0%"

# ===================================================================== 9. Mutation
ws = wb.create_sheet("Mutation")
title(ws, "Mutation testing — 270 first-order mutants of app/domain/*.py",
      "Operators: ROR relational · AOR arithmetic · LCR logical · UOD unary-not deletion · CRP constant · BRV boolean")
header(ws, 4, ["Iteration", "Tests added", "Killed", "Survived", "Raw score"], [12, 12, 10, 10, 11])
for k, it in enumerate(mm["iterations"], 5):
    for j, v in enumerate([it["iteration"], it["tests_added"], it["killed"], it["survived"], f"=C{k}/(C{k}+D{k})"], 1):
        c = ws.cell(row=k, column=j, value=v)
        c.border, c.font = BORDER, (INPUT if j < 5 else BODY)
    ws.cell(row=k, column=5).number_format = "0.0%"
header(ws, 10, ["Mutant ID", "File", "Line", "Operator", "Change", "Status", "Killed by", "Equivalence reason"],
       [16, 26, 7, 10, 16, 14, 40, 70])
end = rows(ws, 11, [[m["id"], m["file"], m["line"], m["operator"], "mutate: " + m["change"], m["status"], m.get("killed_by", ""),
                     m.get("equivalence_reason", "")] for m in mut["mutants"]])
ws.conditional_formatting.add(f"F11:F{end}", CellIsRule(operator="equal", formula=['"KILLED"'], fill=PASS_FILL))
ws.conditional_formatting.add(f"F11:F{end}", CellIsRule(operator="equal", formula=['"EQUIVALENT"'], fill=SKIP_FILL))
ws.freeze_panes = "A11"

# ===================================================================== 10. Fault seeding
ws = wb.create_sheet("Fault Seeding")
title(ws, "Fault seeding (defect injection) — Mills' estimator",
      "N̂ = n × S / s   (n native defects found, S seeded, s seeded found)")
header(ws, 4, ["Fault", "File", "Injected bug", "Level expected to catch", "Detected", "Failing tests", "Detected by"],
       [9, 28, 46, 14, 10, 10, 60])
rows(ws, 5, [[f["id"], f["file"], f["description"], f["expected_level"], "YES" if f["detected"] else "NO",
              f["failing_tests"], ", ".join(f["detected_by"])] for f in seed["faults"]])

# ===================================================================== 11. Performance
ws = wb.create_sheet("Performance")
title(ws, "Performance test results (live uvicorn server, mixed workload)",
      "Workload: 50 % availability · 30 % quote · 15 % book+pay · 5 % list bookings. Single worker, SQLite file DB, 2 vCPU.")
header(ws, 4, ["Phase", "VUs", "Requests", "Throughput (req/s)", "p50 ms", "p95 ms", "p99 ms", "Max ms", "Errors %",
               "Run"], [22, 7, 10, 16, 9, 9, 9, 9, 9, 16])
prow = []
for label, P in (("before tuning", perf0), ("after WAL tuning", perf)):
    prow.append(["Baseline", P["baseline"]["vus"], P["baseline"]["requests"], P["baseline"]["throughput_rps"],
                 P["baseline"]["p50_ms"], P["baseline"]["p95_ms"], P["baseline"]["p99_ms"], P["baseline"]["max_ms"],
                 P["baseline"]["error_rate_pct"], label])
    L = P["load"]
    prow.append(["Load", L["vus"], L["requests"], L["throughput_rps"], L["p50_ms"], L["p95_ms"], L["p99_ms"],
                 L["max_ms"], L["error_rate_pct"], label])
    for s in P["stress"]:
        prow.append(["Stress step", s["vus"], s["requests"], s["throughput_rps"], s["p50_ms"], s["p95_ms"],
                     s["p99_ms"], s["max_ms"], s["error_rate_pct"], label])
    for k, s in P["spike"].items():
        prow.append([f"Spike — {k}", s["vus"], s["requests"], s["throughput_rps"], s["p50_ms"], s["p95_ms"],
                     s["p99_ms"], s["max_ms"], s["error_rate_pct"], label])
    for n, s in enumerate(P["soak"]["windows"], 1):
        prow.append([f"Soak window {n} (RSS {s['rss_mb']} MB)", s["vus"], s["requests"], s["throughput_rps"],
                     s["p50_ms"], s["p95_ms"], s["p99_ms"], s["max_ms"], s["error_rate_pct"], label])
    for k in ("before", "after"):
        s = P["volume"][k]
        prow.append([f"Volume — {k} +5000 rows", s["vus"], s["requests"], s["throughput_rps"], s["p50_ms"],
                     s["p95_ms"], s["p99_ms"], s["max_ms"], s["error_rate_pct"], label])
end = rows(ws, 5, prow, INPUT)
ws.conditional_formatting.add(f"F5:F{end}", CellIsRule(operator="greaterThan", formula=["300"], fill=FAIL_FILL))
ws.cell(row=end + 1, column=1, value="Red p95 cells exceed the 300 ms SLA (meaningful for the Load phase; stress/spike deliberately exceed it).").font = Font(name=F, italic=True, size=9)

# ===================================================================== 12. Static testing
ws = wb.create_sheet("Static Testing")
title(ws, "Static testing — requirements review and code inspection findings")
header(ws, 4, ["ID", "Item", "Type", "Severity / tool", "Finding", "Resolution / decision", "Status"],
       [8, 14, 15, 12, 60, 70, 18])
srows = [[x["id"], x["requirement"], x["type"], x["severity"], x["finding"], x["resolution"], "Closed"]
         for x in ms["requirement_review"]]
srows += [[x["id"], x["file"], "Code inspection", "Ruff/Bandit/Radon", x["finding"], x["decision"], x["status"]]
          for x in ms["code_inspection"]]
rows(ws, 5, srows)

wb["Summary"].column_dimensions["A"].width = 40
for s in wb.worksheets:
    s.page_setup.orientation = "landscape"
    s.page_setup.paperSize = s.PAPERSIZE_A4
    s.sheet_properties.pageSetUpPr.fitToPage = True
    s.page_setup.fitToWidth = 1
    s.page_setup.fitToHeight = 0
    s.print_options.horizontalCentered = True
    s.sheet_view.showGridLines = False
    s.sheet_properties.tabColor = {"Summary": NAVY, "Test Cases": TEAL, "RTM": "2A78D6", "Defect Log": "E34948"}.get(s.title, "B7B5AC")
wb.save(FILE)
print(FILE)
