"""Graphviz diagrams for the report and deck (SVG + PNG)."""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

INK, INK2, GRID = "#0b0b0b", "#52514e", "#c9c7bf"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
                                                          "#008300", "#4a3aa7", "#e34948")
LBLUE, LORANGE, LAQUA, LVIOLET, LRED, LGREY = "#e3eefb", "#fde8df", "#dcf3ea", "#e7e4f6", "#fbe1e1", "#f1f0ec"

BASE = f'''graph [fontname="Inter", fontsize=12, bgcolor="#fcfcfb", pad=0.3, nodesep=0.45, ranksep=0.55];
node [fontname="Inter", fontsize=11, shape=box, style="rounded,filled", fillcolor="white", color="{GRID}", penwidth=1.2, fontcolor="{INK}"];
edge [fontname="Inter", fontsize=10, color="#8a8984", fontcolor="{INK2}", arrowsize=0.7, penwidth=1.2];'''


def render(name, body, engine="dot"):
    src = OUT / f"{name}.dot"
    src.write_text(body)
    for fmt in ("svg", "png"):
        extra = ["-Gdpi=200"] if fmt == "png" else []
        subprocess.run([engine, f"-T{fmt}", *extra, str(src), "-o", str(OUT / f"{name}.{fmt}")], check=True)
    src.unlink()


render("architecture", f'''digraph G {{ {BASE} rankdir=TB;
 subgraph cluster_c {{ label="Client"; style="rounded,dashed"; color="{GRID}"; fontcolor="{INK2}";
   ui [label="Web UI (HTML + JS)\\nsearch · book · pay · cancel", fillcolor="{LBLUE}", color="{BLUE}"];
   api_client [label="REST clients / tests\\nTestClient · Playwright · httpx", fillcolor="{LGREY}"]; }}
 subgraph cluster_s {{ label="HRRS server (FastAPI · uvicorn)"; style="rounded"; color="{GRID}"; fontcolor="{INK2}";
   routes [label="API layer  app/main.py\\n17 endpoints · auth · error mapping · security headers", fillcolor="{LVIOLET}", color="{VIOLET}"];
   svc [label="Service layer  app/services.py\\nbooking · payment · cancellation · check-in/out · reports", fillcolor="{LORANGE}", color="{ORANGE}"];
   subgraph cluster_d {{ label="Domain layer (pure functions — unit-test target)"; style="rounded,filled"; fillcolor="#f7fbf9"; color="{AQUA}"; fontcolor="{GREEN}";
     v [label="validation"]; p [label="pricing + GST"]; c [label="cancellation\\n+ late fee"]; pay [label="payment\\n(Luhn, UPI)"]; st [label="state machine"]; m [label="metrics\\nOcc · ADR · RevPAR"]; }}
 }}
 db [label="SQLite (WAL)\\nusers · bookings · rooms · payments · audit_log", shape=cylinder, fillcolor="{LGREY}"];
 gw [label="Payment gateway stub\\nfault injection: timeout / decline", fillcolor="{LRED}", color="{RED}"];
 ui -> routes [label=" JSON / HTTPS"]; api_client -> routes; routes -> svc; svc -> v; svc -> p; svc -> c; svc -> pay; svc -> st; svc -> m;
 svc -> db [label=" parameterised SQL"]; svc -> gw [label=" charge()"];
}}''')

render("state_machine", f'''digraph G {{ {BASE} rankdir=LR; nodesep=0.6;
 node [shape=box, style="rounded,filled", width=1.5];
 start [shape=circle, label="", width=0.22, style=filled, fillcolor="{INK}"];
 PENDING [fillcolor="{LBLUE}", color="{BLUE}"]; CONFIRMED [fillcolor="{LAQUA}", color="{AQUA}"];
 CHECKED_IN [fillcolor="{LVIOLET}", color="{VIOLET}"];
 CHECKED_OUT [fillcolor="{LGREY}", peripheries=2]; CANCELLED [fillcolor="{LRED}", color="{RED}", peripheries=2];
 EXPIRED [fillcolor="{LORANGE}", color="{ORANGE}", peripheries=2];
 start -> PENDING [label="create booking"];
 PENDING -> CONFIRMED [label="pay  [≤ 15 min, valid card/UPI]"];
 PENDING -> EXPIRED [label="expire  [> 15 min]"];
 PENDING -> CANCELLED [label="cancel  (no charge)"];
 CONFIRMED -> CANCELLED [label="cancel  / refund per DT-1"];
 CONFIRMED -> CHECKED_IN [label="check_in  [ID verified ∧ date reached]"];
 CHECKED_IN -> CHECKED_OUT [label="check_out  / late fee"];
}}''')

render("cfg_refund", f'''digraph G {{ {BASE} rankdir=TB; nodesep=0.35; ranksep=0.35;
 node [shape=circle, width=0.5, fixedsize=true, style=filled, fillcolor="white", fontsize=11];
 n1 [label="1"]; d1 [label="D1", fillcolor="{LBLUE}", color="{BLUE}"]; d2 [label="D2", fillcolor="{LBLUE}", color="{BLUE}"];
 d3 [label="D3", fillcolor="{LBLUE}", color="{BLUE}"]; d4 [label="D4", fillcolor="{LBLUE}", color="{BLUE}"];
 d5 [label="D5", fillcolor="{LBLUE}", color="{BLUE}"]; d6 [label="D6", fillcolor="{LBLUE}", color="{BLUE}"];
 d7 [label="D7", fillcolor="{LBLUE}", color="{BLUE}"];
 node [shape=box, width=1.25, height=0.42, fixedsize=false, style="rounded,filled", fillcolor="{LAQUA}", color="{AQUA}", fontsize=10];
 r1 [label="R1 100 %+voucher"]; e [label="raise CANCEL_AFTER", fillcolor="{LRED}", color="{RED}"]; r2 [label="R2 0 %"];
 r3 [label="R3 100 %"]; r5 [label="R5 75 %"]; r4 [label="R4 50 % − ₹200"]; r7 [label="R7 25 %"]; r6 [label="R6 0 %"];
 x [shape=doublecircle, label="exit", width=0.55, fixedsize=true, fillcolor="{LGREY}", color="{INK2}"];
 n1 -> d1; d1 -> r1 [label="hotel"]; d1 -> d2 [label="¬hotel"];
 d2 -> e [label="days<0"]; d2 -> d3; d3 -> r2 [label="¬refundable"]; d3 -> d4;
 d4 -> r3 [label="≥7"]; d4 -> d5; d5 -> d6 [label="≥2"]; d5 -> d7 [label="<2"];
 d6 -> r5 [label="PLAT"]; d6 -> r4; d7 -> r7 [label="PLAT"]; d7 -> r6;
 r1 -> x; e -> x; r2 -> x; r3 -> x; r5 -> x; r4 -> x; r7 -> x; r6 -> x;
 legend [shape=note, fillcolor="white", color="{GRID}", fontsize=10, label="refund_decision()\\l7 predicate nodes  →  V(G) = P + 1 = 8\\lN = 17 nodes, E = 23 edges  →  V(G) = E − N + 2 = 8\\l8 basis paths  →  TC-WB-PATH-001 … 008\\l"];
}}''')

render("cfg_latefee", f'''digraph G {{ {BASE} rankdir=TB; nodesep=0.4; ranksep=0.35;
 node [shape=box, style="rounded,filled", fillcolor="white", fontsize=10];
 s [label="1  rate = Decimal(nightly)   [def rate]"];
 a [label="2  rate < 0 ?   [p-use rate]", fillcolor="{LBLUE}", color="{BLUE}"];
 err [label="raise TARIFF_NEGATIVE", fillcolor="{LRED}", color="{RED}"];
 b [label="3  t ≤ 12:00 ?", fillcolor="{LBLUE}", color="{BLUE}"];
 c [label="5  t ≤ 15:00 ?", fillcolor="{LBLUE}", color="{BLUE}"];
 d [label="7  t ≤ 18:00 ?", fillcolor="{LBLUE}", color="{BLUE}"];
 p0 [label="4  pct = 0   [def#1]", fillcolor="{LAQUA}", color="{AQUA}"];
 p25 [label="6  pct = 25   [def#2]", fillcolor="{LAQUA}", color="{AQUA}"];
 p50 [label="8  pct = 50   [def#3]", fillcolor="{LAQUA}", color="{AQUA}"];
 p100 [label="9  pct = 100   [def#4]", fillcolor="{LAQUA}", color="{AQUA}"];
 r [label="10  return rate × pct / 100   [c-use rate, pct]", fillcolor="{LVIOLET}", color="{VIOLET}"];
 s -> a; a -> err [label="T"]; a -> b [label="F"]; b -> p0 [label="T"]; b -> c [label="F"];
 c -> p25 [label="T"]; c -> d [label="F"]; d -> p50 [label="T"]; d -> p100 [label="F"];
 p0 -> r; p25 -> r; p50 -> r; p100 -> r;
 note [shape=note, color="{GRID}", label="V(G) = 4 decisions + 1 = 5\\ldu-pairs for pct: (4,10) (6,10) (8,10) (9,10)\\lall-defs = all-uses = 4 tests + 1 error path\\l→ TC-WB-DF-001 … 005\\l"];
}}''')

render("cause_effect", f'''digraph G {{ {BASE} rankdir=LR; nodesep=0.5; ranksep=1.0;
 node [shape=circle, width=0.55, fixedsize=true, style=filled];
 c1 [label="C1", fillcolor="{LBLUE}", color="{BLUE}"]; c2 [label="C2", fillcolor="{LBLUE}", color="{BLUE}"];
 c3 [label="C3", fillcolor="{LBLUE}", color="{BLUE}"]; c4 [label="C4", fillcolor="{LBLUE}", color="{BLUE}"];
 and1 [label="∧", fillcolor="white", color="{INK2}", width=0.42]; and2 [label="∧", fillcolor="white", color="{INK2}", width=0.42];
 or1 [label="∨", fillcolor="white", color="{INK2}", width=0.42]; nor [label="¬∨", fillcolor="white", color="{INK2}", width=0.48];
 e1 [label="E1", fillcolor="{LAQUA}", color="{AQUA}"]; e2 [label="E2", fillcolor="{LAQUA}", color="{AQUA}"]; e3 [label="E3", fillcolor="{LORANGE}", color="{ORANGE}"];
 c1 -> and1; c2 -> and1; c4 -> and1; and1 -> e1;
 c2 -> and2; c3 -> and2; c1 -> or1; and2 -> or1; or1 -> e2;
 e1 -> nor; e2 -> nor; nor -> e3;
 node [shape=plaintext, fixedsize=false, style=""];
 k [label=<<table border="0" cellpadding="3" cellspacing="0">
   <tr><td align="left"><b>Causes</b></td></tr>
   <tr><td align="left">C1 tier ∈ {{GOLD, PLATINUM}}</td></tr><tr><td align="left">C2 stay ≥ 3 nights</td></tr>
   <tr><td align="left">C3 booked ≥ 30 days ahead</td></tr><tr><td align="left">C4 room ≠ SUITE</td></tr>
   <tr><td align="left"><b>Effects</b></td></tr>
   <tr><td align="left">E1 free upgrade = C1 ∧ C2 ∧ C4</td></tr><tr><td align="left">E2 free breakfast = C1 ∨ (C2 ∧ C3)</td></tr>
   <tr><td align="left">E3 no benefit = ¬E1 ∧ ¬E2</td></tr></table>>];
}}''')

TAX = {
    "Static testing": {"Reviews": ["Requirements review (RV-01..07)", "Walkthrough", "Inspection (CI-01..08)"],
                       "Static analysis": ["Lint (Ruff)", "Security SAST (Bandit)", "Complexity (Radon)"]},
    "Black-box": {"Specification-based": ["Boundary Value Analysis", "Equivalence Partitioning", "Decision Table",
                                          "Cause-Effect Graph", "State Transition", "Pairwise", "Use-case / BDD"],
                  "Experience-based": ["Error guessing", "Exploratory charters", "Property-based"]},
    "White-box": {"Control-flow": ["Statement", "Branch / decision", "Condition", "MC/DC", "Basis path", "Loop"],
                  "Data-flow": ["all-defs", "all-uses", "all-du-paths"], "Fault-based": ["Mutation", "Fault seeding"]},
    "Levels": {"Unit": ["domain functions"], "Integration": ["bottom-up", "top-down (stubs)"],
               "System": ["API", "E2E UI"], "Acceptance": ["UAT", "Alpha / Beta"]},
    "Non-functional": {"Performance": ["Load", "Stress", "Spike", "Soak", "Volume"],
                       "Security": ["Injection", "XSS", "Access control", "Auth / lockout", "Headers"],
                       "Usability": ["Accessibility (axe)", "Keyboard-only", "Heuristics"],
                       "Compatibility": ["Devices", "Browsers"], "Reliability": ["Recovery", "Concurrency"]},
    "Change-related": {"Regression": ["per-defect tests"], "Confirmation": ["re-test"], "Smoke / Sanity": ["build check"]},
}
lines = [f'digraph G {{ {BASE} rankdir=LR; nodesep=0.08; ranksep=0.35; node [fontsize=9.5, height=0.26];',
         f'root [label="Software Testing\\n(HRRS)", fillcolor="{INK}", fontcolor="white", color="{INK}", fontsize=12];']
pal = [BLUE, AQUA, VIOLET, ORANGE, RED, GREEN]
lpal = [LBLUE, LAQUA, LVIOLET, LORANGE, LRED, "#e1f1e1"]
k = 0
for i, (top, subs) in enumerate(TAX.items()):
    t = f"t{i}"
    lines.append(f'{t} [label="{top}", fillcolor="{pal[i]}", fontcolor="white", color="{pal[i]}", fontsize=11];')
    lines.append(f"root -> {t};")
    for j, (sub, leaves) in enumerate(subs.items()):
        s = f"s{i}_{j}"
        lines.append(f'{s} [label="{sub}", fillcolor="{lpal[i]}", color="{pal[i]}"];')
        lines.append(f"{t} -> {s};")
        for leaf in leaves:
            k += 1
            lines.append(f'l{k} [label="{leaf}", fillcolor="white", color="{GRID}", fontsize=9];')
            lines.append(f"{s} -> l{k};")
lines.append("}")
render("taxonomy", "\n".join(lines))

render("stlc", f'''digraph G {{ {BASE} rankdir=TB; nodesep=0.25; ranksep=0.3; newrank=true;
 node [width=1.55, fillcolor="{LBLUE}", color="{BLUE}"];
 a [label="1 Requirement\\nanalysis"]; b [label="2 Test\\nplanning"]; c [label="3 Test case\\ndesign"];
 d [label="4 Environment\\nsetup"]; e [label="5 Test\\nexecution"]; f [label="6 Defect\\nreporting"]; g [label="7 Test\\nclosure"];
 {{rank=same; a; b; c; d; e; f; g;}}
 a -> b -> c -> d -> e -> f -> g; f -> e [label="re-test", style=dashed, color="{ORANGE}", fontcolor="{ORANGE}", constraint=false];
 node [shape=note, fillcolor="white", color="{GRID}", fontsize=9, width=1.55];
 a1 [label="RTM · review\\nRV-01..07"]; b1 [label="Test plan\\nIEEE 829"]; c1 [label="554 cases\\n20+ techniques"];
 d1 [label="pytest · Playwright\\nhttpx · axe"]; e1 [label="558 pass · 2 skip\\n99.9 % coverage"]; f1 [label="DEF-001..005"]; g1 [label="Summary report\\n+ metrics"];
 {{rank=same; a1; b1; c1; d1; e1; f1; g1;}}
 edge [arrowhead=none, style=dotted];
 a -> a1; b -> b1; c -> c1; d -> d1; e -> e1; f -> f1; g -> g1;
}}''')

render("defect_lifecycle", f'''digraph G {{ {BASE} rankdir=LR; nodesep=0.35;
 node [width=1.25];
 new [label="New", fillcolor="{LBLUE}", color="{BLUE}"]; assigned [label="Assigned"]; open [label="Open"];
 fixed [label="Fixed"]; retest [label="Re-test", fillcolor="{LVIOLET}", color="{VIOLET}"];
 closed [label="Closed", fillcolor="{LAQUA}", color="{AQUA}", peripheries=2]; reopen [label="Re-opened", fillcolor="{LRED}", color="{RED}"];
 rej [label="Rejected /\\nDuplicate", fillcolor="{LGREY}"]; def [label="Deferred", fillcolor="{LORANGE}", color="{ORANGE}"];
 new -> assigned -> open -> fixed -> retest -> closed; retest -> reopen [label="fails"]; reopen -> assigned;
 new -> rej [label="not a defect"]; open -> def [label="low priority"];
}}''')

render("integration_strategy", f'''digraph G {{ {BASE} rankdir=TB; nodesep=0.35; ranksep=0.45;
 drv [label="Test driver\\npytest + TestClient", shape=box, style="rounded,filled,dashed", fillcolor="white", color="{ORANGE}"];
 api [label="API layer", fillcolor="{LVIOLET}", color="{VIOLET}"];
 svc [label="HotelService", fillcolor="{LORANGE}", color="{ORANGE}"];
 dom [label="Domain rules", fillcolor="{LAQUA}", color="{AQUA}"]; db [label="SQLite", shape=cylinder, fillcolor="{LGREY}"];
 stub [label="Gateway STUB\\nFAULT = None | timeout | decline", style="rounded,filled,dashed", fillcolor="{LRED}", color="{RED}"];
 drv -> api [label=" system tests"]; drv -> svc [label=" integration tests", style=dashed];
 api -> svc; svc -> dom; svc -> db; svc -> stub;
 note [shape=note, color="{GRID}", fontsize=10, label="Bottom-up: domain (unit) → service + DB → API → UI\\lTop-down element: real payment gateway replaced by a stub\\lwith fault injection, so recovery paths are deterministic\\l"];
}}''')

print(sorted(p.name for p in OUT.glob("*.png")))
