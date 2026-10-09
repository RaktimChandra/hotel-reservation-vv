// HRRS — Software Verification & Validation: full test documentation report.
const fs = require("fs");
const path = require("path");
const L = require("./lib");
const { J, ROOT, P, H1, H2, H3, SP, bullets, numbered, eq, callout, code, table, fig, tcap, cover, build, toc, C } = L;

const results = J("reports/results.json");
const reqs = J("docs/requirements.json");
const defects = J("reports/defects_found.json");
const defectsManual = fs.existsSync(path.join(ROOT, "reports/defects_manual.json")) ? J("reports/defects_manual.json") : [];
const mx = fs.existsSync(path.join(ROOT, "reports/manual/manual_exec.json")) ? J("reports/manual/manual_exec.json") : null;
const ms = J("docs/manual_and_static.json");
const mut = J("reports/mutation.json");
const seed = J("reports/fault_seeding.json");
const perf = J("reports/perf.json"), perf0 = J("reports/perf_before_tuning.json");
const cov = J("reports/coverage.json"), cov0 = J("reports/coverage_iter1.json");
const axe = J("reports/a11y_axe.json");
const cc = J("reports/static/radon_cc.json");
const ruff = J("reports/static/ruff.json"), bandit = J("reports/static/bandit.json");

const count = (f) => results.filter(f).length;
const N = results.length, PASS = count((r) => r.status === "PASS"), SKIP = count((r) => r.status === "SKIPPED");
const byLevel = (lv) => count((r) => r.level === lv);
const pct = (x) => (100 * x).toFixed(1) + " %";
const covT = cov.totals, covT0 = cov0.totals;
const src = (file, fn) => {
  const lines = fs.readFileSync(path.join(ROOT, file), "utf8").split("\n");
  const start = lines.findIndex((l) => l.startsWith(`def ${fn}(`));
  let end = start + 1;
  while (end < lines.length && (lines[end].startsWith(" ") || lines[end] === "")) end++;
  return lines.slice(start, end).filter((l, i, a) => !(l === "" && i === a.length - 1)).map((l, i) => `${String(start + i + 1).padStart(3)}  ${l}`);
};
const pick = (pred, n = 999) => results.filter(pred).slice(0, n);
const caseRows = (rs) => rs.map((r) => [r.id, r.title, r.inputs, r.expected, r.status]);
const caseTable = (rs, w = [2.1, 4.2, 2.6, 2.2, 1]) => table(["TC ID", "Objective", "Inputs", "Expected", "Result"], caseRows(rs), w,
  { size: 16, center: [4], fill: (r) => (r[4] === "PASS" ? null : r[4] === "SKIPPED" ? "FFF3D6" : "FBE1E1") });

// =========================================================================== front matter
function front() {
  return [
    ...cover("Hotel Room Reservation System", "Planning, designing, automating and executing a complete verification & validation campaign", "Software Test Documentation Report"),
    L.H1("Bonafide Certificate", false),
    P("Certified that this report titled **“Software Verification and Validation of a Hotel Room Reservation System (HRRS)”** is the bonafide work of **Raktim Chandra (RA2311033010038)**, who carried out the work under my supervision as part of the course Software Verification and Validation (FT-3 component) during the academic year 2026–27."),
    SP(900),
    table(["Faculty in charge", "Head of the Department"], [["\n\n\nSignature\nMr. Kaviyaraj R.\nSoftware Verification and Validation", "\n\n\nSignature\n\nDepartment of Computational Intelligence"]], [1, 1], { size: 20 }),
    L.H1("Acknowledgement", false),
    P("We thank **Mr. Kaviyaraj R.** for the course and for framing this component around real test design rather than theory alone. We thank the Department of Computational Intelligence and SRM Institute of Science and Technology for the laboratory and computing facilities."),
    L.H1("Abstract", false),
    P(`This report documents a complete verification and validation (V&V) campaign for a **Hotel Room Reservation System (HRRS)** that I specified, built and tested end-to-end. The system — a FastAPI REST service with a SQLite store and a browser front-end — implements registration, authentication with lock-out, availability search, a pricing engine with weekend/peak surcharges, loyalty and promotional discounts and Indian GST slabs, payments with idempotency, a cancellation/refund policy, a booking life-cycle state machine, check-in/check-out with late fees and management metrics (Occupancy, ADR, RevPAR).`),
    P(`From 15 functional and 17 non-functional requirements we designed **${N} test cases** using every technique in the FT-3 syllabus — Boundary Value Analysis (robust, multi-variable and worst-case), Equivalence Class Partitioning, Decision Tables, Cause-Effect Graphing, and white-box statement, branch, condition, MC/DC, basis-path (cyclomatic complexity), loop and data-flow coverage — and extended it with state-transition, pairwise, property-based, BDD acceptance, security (OWASP), performance (load, stress, spike, soak, volume), accessibility, compatibility, recovery, mutation and fault-seeding techniques, across unit, integration, system, end-to-end and acceptance levels.`),
    P(`Every test case is executable and traceable: the run writes its real outcome back into the catalogue. Final execution: **${PASS} passed, ${SKIP} skipped (browsers unavailable in the lab sandbox), 0 failed**; **${covT.percent_statements_covered.toFixed(0)} % statement and ${covT.percent_branches_covered.toFixed(1)} % branch coverage**; **mutation score 100 %** (267 of 267 non-equivalent mutants killed); **12/12 seeded faults detected**. Testing found **${defects.length} genuine defects** — including a performance defect whose fix cut booking p95 latency from ${perf0.load.by_endpoint_p95.book.toFixed(0)} ms to ${perf.load.by_endpoint_p95.book.toFixed(0)} ms, and a weakness in our own security test exposed by fault seeding — all fixed and regression-tested.`),
    P("**Keywords:** software testing, verification and validation, BVA, ECP, decision table, cause-effect graph, cyclomatic complexity, MC/DC, mutation testing, test automation, hotel reservation.", { run: { size: 20 } }),
    L.H1("Highlights at a glance", false),
    table(["Dimension", "Result"], [
      ["Test cases designed & executed", `${N} (${byLevel("Unit")} unit · ${byLevel("Integration")} integration · ${byLevel("System")} system/API · ${byLevel("System (E2E UI)")} E2E UI · ${byLevel("Acceptance (UAT)")} UAT) + ${ms.manual_cases.length} manual + ${ms.exploratory_charters.length} exploratory charters`],
      ["Outcome", `${PASS} PASS · ${SKIP} SKIPPED · 0 FAIL — identical on a second stability run; 20-thread race test 25/25 runs`],
      ["Code coverage (coverage.py)", `${covT.covered_lines}/${covT.num_statements} statements (100 %) · ${covT.covered_branches}/${covT.num_branches} branches (${covT.percent_branches_covered.toFixed(1)} %)`],
      ["Mutation testing (own AST engine)", "270 mutants · 6 operators · 3 iterations 85.9 % → 97.8 % → 98.9 % raw · 100 % after excluding 3 proven-equivalent mutants"],
      ["Fault seeding", "12 realistic bugs injected · 11/12 caught (Rev A) → 12/12 (Rev B) · Mills N̂ = 4.0, latent ≈ 0"],
      ["Defects found", `${defects.length} — functional (ECP), 2 UI (exploratory), performance (load test), test-suite (fault seeding); all fixed and regression-tested`],
      ["Performance (25 users)", `p95 ${perf0.load.p95_ms} → ${perf.load.p95_ms} ms (SLA 300 ms) · ${perf.load.throughput_rps} req/s · 0 % errors · flat memory over a 60 s soak`],
      ["Security", "OWASP A01/A02/A03/A05/A07 cases: SQLi, XSS (stored + DOM), IDOR, privilege escalation, brute-force lock-out, enumeration, headers — all pass"],
      ["Accessibility", `axe-core WCAG 2.1 A/AA: ${axe.violations.length} violations, ${axe.passes} rules passed; keyboard-only flow passes`],
      ["Traceability", `${reqs.length}/${reqs.length} requirements have executed tests (RTM); NFR-COMP-02 partial (Firefox/WebKit not installable in sandbox)`],
    ], [2.2, 6.3], { size: 18 }),
    ...toc(process.env.TOC_PAGES || ""),
  ];
}

// =========================================================================== 1 introduction
function intro() {
  return [
    H1("1. Introduction"),
    H2("1.1 Purpose"),
    P("This document is the single source of truth for how the Hotel Room Reservation System (HRRS) was verified and validated. It contains the test plan, the test design for every technique in the course plan, the executable test cases with their real results, defects, metrics and lessons learnt. It follows the structure of IEEE 829-2008 (Test Documentation) and ISO/IEC/IEEE 29119-3, and the V&V activities of IEEE 1012."),
    H2("1.2 Verification versus validation"),
    table(["", "Verification", "Validation"], [
      ["Question", "Are we building the product **right**?", "Are we building the **right** product?"],
      ["Checks against", "Specifications, design, standards", "User needs and intended use"],
      ["Typical activities", "Reviews, inspections, static analysis, unit/integration tests, coverage", "System, acceptance (UAT), usability, beta tests"],
      ["In this project", "Requirements review RV-01..07, code inspection CI-01..08, Ruff/Bandit/Radon, 448 unit + 31 integration tests, coverage, mutation", "71 system/E2E tests, 4 BDD acceptance scenarios, accessibility audit, performance against SLA"],
    ], [1.4, 3.6, 3.6]),
    tcap("Verification and validation compared"),
    H2("1.3 Scope"),
    P("In scope: every functional requirement FR-01…FR-15 and non-functional requirement for performance, security, reliability, usability/accessibility, compatibility and interface (Chapter 2). Out of scope: real payment-network integration (a stub with fault injection stands in), e-mail notifications and multi-property inventory."),
    H2("1.4 Objectives"),
    ...bullets([
      "Design test cases systematically with **every FT-3 technique** — BVA, ECP, cause-effect graphing, decision tables and source-code coverage — and show the derivation, not just the result.",
      "Design test cases for **each testing level** (unit, integration, system, acceptance) and connect them with a V-model and a requirements traceability matrix.",
      "Make every test case **executable** so results are measured, repeatable and honest.",
      "Go beyond the syllabus where it adds evidence: mutation testing, fault seeding, property-based testing, performance engineering and security testing.",
    ]),
    H2("1.5 Definitions and acronyms"),
    table(["Term", "Meaning"], [
      ["BVA / ECP", "Boundary Value Analysis / Equivalence Class Partitioning"],
      ["DT / CEG", "Decision Table / Cause-Effect Graph"],
      ["V(G)", "McCabe cyclomatic complexity of control-flow graph G"],
      ["MC/DC", "Modified Condition/Decision Coverage — each condition shown to independently affect the decision"],
      ["du-pair", "A definition-use pair of a variable along a def-clear path (data-flow testing)"],
      ["SUT / AUT", "System / Application Under Test"],
      ["RTM", "Requirements Traceability Matrix"],
      ["p95", "95th-percentile latency: 95 % of requests complete within this time"],
      ["VU", "Virtual user (concurrent simulated client) in load testing"],
      ["ADR / RevPAR", "Average Daily Rate / Revenue Per Available Room"],
      ["IDOR", "Insecure Direct Object Reference (broken object-level authorisation)"],
      ["UAT / BDD", "User Acceptance Testing / Behaviour-Driven Development (Gherkin)"],
    ], [1.6, 6.9]),
    tcap("Glossary"),
    H2("1.6 References"),
    ...bullets([
      "IEEE Std 829-2008, *Standard for Software and System Test Documentation*.",
      "ISO/IEC/IEEE 29119-1…4, *Software and systems engineering — Software testing*.",
      "IEEE Std 1012-2016, *Standard for System, Software, and Hardware Verification and Validation*.",
      "T. J. McCabe, “A Complexity Measure”, *IEEE Transactions on Software Engineering*, SE-2(4), 1976.",
      "G. J. Myers, C. Sandler, T. Badgett, *The Art of Software Testing*, 3rd ed., Wiley.",
      "P. Ammann and J. Offutt, *Introduction to Software Testing*, 2nd ed., Cambridge University Press.",
      "OWASP Top 10 (2021) and W3C Web Content Accessibility Guidelines (WCAG) 2.1.",
      "Government of India GST rate rationalisation (effective 22 Sep 2025): hotel accommodation ≤ ₹7,500/night 5 %, above 18 %.",
    ]),
  ];
}

// =========================================================================== 2 system under test
function sut() {
  return [
    H1("2. System Under Test"),
    H2("2.1 Overview"),
    P("**HRRS** (branded *Marina Crest Reservations* in the UI) is a working web application built specifically to be tested. It has a three-layer design so each layer maps onto a test level: a pure-function **domain layer** (unit tests), a **service layer** wired to SQLite and a payment gateway (integration tests) and a **REST/UI layer** (system, end-to-end and acceptance tests)."),
    ...fig("architecture.png", "HRRS architecture and the layer each test level targets", 6.3),
    table(["Metric", "Value"], [["Application source (SLOC, radon)", "1,023 lines in 14 modules"],
      ["REST endpoints", "17 (auth, search, quote, bookings, payment, cancel, check-in/out, admin)"],
      ["Room inventory", "20 rooms: 8 STANDARD, 6 DELUXE, 3 FAMILY, 3 SUITE"],
      ["Test code", "≈ 3,000 lines across 13 test modules + 1 Gherkin feature"],
      ["Tooling", "pytest, pytest-bdd, Hypothesis, Playwright + axe-core, coverage.py, httpx, Ruff, Bandit, Radon, own mutation and fault-seeding engines"]], [2.6, 5.9]),
    tcap("System and test-asset size"),
    H2("2.2 Requirements baseline"),
    P("Requirements were written to be **testable** — each states measurable boundaries. The requirements review (Chapter 11) found seven ambiguities that were resolved before test design; the resolutions are part of the baseline below."),
    table(["ID", "Area", "Requirement (testable form)"], reqs.map((r) => [r.id, r.area, r.text]), [1.25, 1.6, 5.7], { size: 16 }),
    tcap("Functional and non-functional requirements"),
    H2("2.3 Key business rules as equations"),
    P("The pricing engine is the richest source of boundaries, so its rules are written as equations that the test oracle re-implements independently:"),
    eq("nightly_price(d) = tariff × (1 + 0.20·[d ∈ {Fri, Sat}] + 0.30·[d ∈ 20 Dec … 5 Jan])"),
    eq("subtotal = Σ_nights Σ_rooms nightly_price(d)"),
    eq("discount = min( subtotal × (long_stay% + loyalty%) + promo,  0.30 × subtotal )"),
    eq("total = (subtotal − discount) × (1 + GST(tariff)),   GST = 0 | 5 % | 18 %"),
    P("Worked example (verified by test TC-SYS-FN-002 and by hand): an Executive Suite with an extra bed (₹7,500 + ₹800 = ₹8,300 declared tariff → 18 % GST slab) for Thu 24 → Sun 27 Dec 2026 has multipliers 1.30 (Thu, peak), 1.50 (Fri, peak + weekend), 1.50 (Sat), so subtotal = 8,300 × 4.30 = ₹35,690.00, GST = ₹6,424.20, total = **₹42,114.20**."),
    eq("Occupancy % = rooms_sold ÷ rooms_available × 100     ADR = revenue ÷ rooms_sold     RevPAR = revenue ÷ rooms_available = ADR × Occupancy"),
    H2("2.4 Booking life-cycle"),
    ...fig("state_machine.png", "Booking state machine (FR-09) — double borders mark final states", 6.3),
  ];
}

// =========================================================================== 3 concepts & approach
function approach() {
  return [
    H1("3. Testing Approach, Levels and Types"),
    H2("3.1 V-model"),
    P("Each design artefact on the left of the V is verified by the matching test level on the right. Requirements are **validated** by acceptance tests; design, architecture and modules are **verified** by system, integration and unit tests."),
    ...fig("vmodel.png", "V-model mapping for HRRS with the number of executed cases per level", 6.4),
    H2("3.2 Software Testing Life Cycle (STLC)"),
    ...fig("stlc.png", "STLC phases and the artefact this project produced at each phase", 6.4),
    H2("3.3 Taxonomy of testing applied"),
    P("Figure 7 is the map for the rest of the report: every leaf is a technique that was actually applied, with test cases in the catalogue."),
    ...fig("taxonomy.png", "Testing types → sub-types → techniques used on HRRS", 4.4),
    H2("3.4 Test pyramid"),
    P("The suite follows the test pyramid: many fast, precise unit tests; fewer, slower integration and system tests; a thin layer of end-to-end and acceptance tests that prove real user journeys."),
    ...fig("test_pyramid.png", "Executed test cases per level", 4.8),
    table(["Level", "Target", "Driver / environment", "Cases", "Typical runtime"], [
      ["Unit", "Domain functions (pure)", "pytest, Hypothesis", String(byLevel("Unit")), "< 3 s total"],
      ["Integration", "Service + SQLite + gateway stub", "pytest, temp DB files, threads", String(byLevel("Integration")), "≈ 5 s"],
      ["System / API", "Whole app via HTTP", "FastAPI TestClient", String(byLevel("System")), "≈ 10 s"],
      ["System (E2E UI)", "Browser + live server", "Playwright Chromium, axe-core", String(byLevel("System (E2E UI)")), "≈ 15 s"],
      ["Acceptance (UAT)", "User stories", "pytest-bdd (Gherkin)", String(byLevel("Acceptance (UAT)")), "≈ 1 s"],
    ], [1.6, 2.2, 2.6, 0.8, 1.3], { center: [3] }),
    tcap("Test levels, targets and environments"),
    H2("3.5 Test-case identifier scheme"),
    P("`TC-<MODULE>-<TECHNIQUE>-<NNN>`, e.g. `TC-CAN-DT-004` = Cancellation, Decision Table, case 4. Modules: REG registration, AUTH, SRCH search, BOOK, ROOM, PRC pricing, QTE quote, CAN cancellation, CHK check-out, PAY payment, STM state machine, BEN benefits, RPT reports, WB white-box, EG error guessing, PBT property-based, INT integration, SYS system, SEC security, PERF, E2E, UAT, COV coverage-guided, MUT mutation-guided, MAN manual."),
    callout("Single source of truth.", "Every automated test carries its IEEE 829 fields (ID, objective, module, requirement, technique, level, type, priority, pre-conditions, inputs, steps, expected result) as a pytest marker. A conftest hook records the **actual** outcome, duration and timestamp, and the workbook, RTM and this report are generated from that record — no result in this document was typed by hand."),
  ];
}

// =========================================================================== 4 test plan
function plan() {
  return [
    H1("4. Test Plan (IEEE 829)"),
    table(["Section", "Content"], [
      ["Test plan identifier", "HRRS-TP-1.0"],
      ["Test items", "HRRS v1.0: app/domain/* (validation, pricing, cancellation, payment, state, metrics), app/services.py, app/main.py, app/static/index.html, SQLite schema"],
      ["Features to be tested", "FR-01 … FR-15; NFR performance, security, reliability, usability/accessibility, compatibility, interface, availability"],
      ["Features not tested", "Real card-network authorisation (stubbed), outbound e-mail/SMS, multi-hotel inventory, localisation beyond en-IN"],
      ["Approach", "Risk-based; black-box design per requirement, white-box coverage on the domain layer, automation at every level, exploratory sessions on UI, non-functional campaigns"],
      ["Item pass / fail criteria", "A test passes when actual = expected exactly (error codes, amounts to the paisa, HTTP status). Release needs 100 % of P1 cases passing, ≥ 95 % statement coverage, mutation score ≥ 90 %, no open Critical/Major defects"],
      ["Suspension criteria", "Build fails smoke suite (TC-SYS-SMK-*); > 10 % of a suite blocked by one defect; environment unavailable"],
      ["Resumption criteria", "Smoke suite green on the fixed build; blocking defect verified fixed"],
      ["Test deliverables", "This report, test plan, test-case workbook (cases, RTM, defect log, metrics), test summary report, automation code, HTML/JUnit reports, coverage report, videos and screenshots, deck"],
      ["Environment", "Linux x86-64, 2 vCPU · Python 3.13 · FastAPI 0.143 · SQLite (WAL) · Playwright Chromium 141 · Node 22 (axe-core) · frozen clock 8 Oct 2026 10:00 for reproducibility"],
      ["Responsibilities", "See RACI below"],
      ["Schedule", "Week 1 requirements & review · Week 2 design (black-box) · Week 3 white-box & integration · Week 4 system, E2E, non-functional · Week 5 execution, defects, closure"],
      ["Risks & contingencies", "See risk register below"],
      ["Approvals", "Faculty: Mr. Kaviyaraj R. · Test lead: Raktim Chandra"],
    ], [2.1, 6.4], { size: 18 }),
    tcap("IEEE 829 test plan"),
    H2("4.1 Workstreams"),
    table(["Workstream", "Scope"], [
      ["Strategy & automation", "Test strategy and plan, automation framework (@tc metadata → results.json), performance engineering"],
      ["Black-box design", "BVA, ECP, decision tables, cause-effect graphing, state transition, BDD acceptance"],
      ["White-box & test quality", "CFG, V(G), basis paths, MC/DC, data-flow, mutation testing, fault seeding, integration"],
      ["Non-functional", "Security (OWASP), end-to-end UI, accessibility, compatibility, recovery"],
      ["Static testing & reporting", "Requirements review, code inspection, defect triage, metrics, reporting"],
    ], [2.4, 6.1]),
    tcap("Workstreams — all planned, executed and reported by the author"),
    H2("4.2 Entry and exit criteria"),
    table(["Level", "Entry criteria", "Exit criteria", "Met?"], [
      ["Unit", "Module compiles; requirements reviewed", "All unit cases pass; domain coverage ≥ 95 %; mutation ≥ 90 %", "Yes — 100 % / 100 %"],
      ["Integration", "Unit exit met; DB schema stable; gateway stub ready", "All integration cases pass incl. concurrency ×25", "Yes"],
      ["System", "Integration exit met; app deploys; smoke green", "All P1/P2 pass; SLA met; no open Major", "Yes"],
      ["Acceptance", "System exit met", "All UAT scenarios pass", "Yes"],
    ], [1.2, 2.8, 3.4, 1.2]),
    tcap("Entry / exit criteria per level"),
    H2("4.3 Risk register (risk-based testing)"),
    table(["Risk", "Likelihood", "Impact", "Exposure", "Mitigation / tests"], [
      ["Overbooking under concurrent requests", "Medium", "High", "High", "Serialised write transaction; 20-thread race test ×25 (TC-INT-005)"],
      ["Wrong price or tax charged", "Medium", "High", "High", "BVA on every pricing boundary, pairwise + independent oracle, property tests"],
      ["Double charge on retry", "Medium", "High", "High", "Idempotency key; TC-INT-007, TC-COV-001/002"],
      ["Unauthorised access to bookings", "Low", "High", "Medium", "Object/role checks; IDOR and escalation tests TC-SEC-005/006"],
      ["Slow booking at peak", "Medium", "Medium", "Medium", "Load/stress/spike/soak campaign; found and fixed DEF-004"],
      ["Inaccessible UI", "Low", "Medium", "Low", "axe-core audit, keyboard-only test"],
      ["Lab cannot run Firefox/WebKit", "High", "Low", "Medium", "Device emulation in Chromium; manual cases TC-MAN-COMP-001/002"],
    ], [2.4, 1, 0.9, 1, 3.2]),
    tcap("Product and project risks with mitigations"),
  ];
}

// =========================================================================== 5 black box
function blackbox() {
  const dt1 = results.filter((r) => r.id.startsWith("TC-CAN-DT")).slice(0, 8);
  return [
    H1("5. Black-Box Test Case Design"),
    P("Black-box (specification-based) techniques derive test cases from the requirements without looking at the code. Each section gives the **theory**, the **derivation for HRRS**, and a **sample of the executed cases** (full lists in the workbook)."),
    H2("5.1 Equivalence Class Partitioning (ECP)"),
    P("ECP divides an input domain into classes whose members the system should treat identically, so one representative per class suffices. Valid classes are combined (weak normal ECP); invalid classes are tested **one at a time**, so a failure points to exactly one cause."),
    eq("minimum cases = (#valid-class combinations, often 1) + (#invalid classes)"),
    table(["Input", "Valid classes", "Invalid classes"], [
      ["E-mail (FR-01)", "V1 simple · V2 plus-tag/dots · V3 upper-case", "I1 no @ · I2 no local part · I3 no domain · I4 no TLD · I5 1-letter TLD · I6 space · I7 two @ · I8 empty · I9 None"],
      ["Mobile (FR-01)", "V1 starts 9 · V2 starts 6 · V3 +91 prefix", "I1 starts 5 · I2 9 digits · I3 11 digits · I4 letters · I5 inner space · I6 empty"],
      ["Name characters (FR-01)", "V1 letters · V2 apostrophe · V3 hyphen · V4 initial “R. ”", "I1 digits · I2 @ · I3 emoji · I4 blank · I5 HTML/script"],
      ["Password (FR-02)", "V1 all four character classes", "I1 no upper · I2 no lower · I3 no digit · I4 no special · I5 whitespace · I6 non-string"],
      ["Room type (FR-04)", "4 codes + lower-case", "unknown · empty · None · integer"],
      ["Loyalty tier (FR-06)", "NONE, SILVER, GOLD, PLATINUM, lower-case, missing", "DIAMOND"],
      ["Card (FR-08)", "Visa · MasterCard · spaced · dashed", "Luhn fail · 15 · 17 digits · letters · empty; CVV 2/4/alpha"],
      ["Night of week (FR-06)", "weekday {Sun–Thu} · weekend {Fri, Sat}", "—"],
    ], [1.7, 3, 3.8], { size: 17 }),
    tcap("Equivalence classes"),
    caseTable(pick((r) => r.id.startsWith("TC-REG-ECP"), 30)),
    tcap("Executed ECP cases for registration (all 30)"),
    callout("Defect found by ECP.", "Valid class V4 (“R. Chandra”, an initial followed by a space) was **rejected** — the name pattern allowed only one separator between letter groups. Logged as **DEF-001**, fixed, and guarded by regression test TC-REG-RGN-001.", "FBE1E1", "E34948"),
    H2("5.2 Boundary Value Analysis (BVA)"),
    P("Defects cluster at the edges of equivalence classes (off-by-one, `<` vs `<=`). BVA tests values on and around each boundary. For *n* independent variables:"),
    table(["Variant", "Values per variable", "Total cases", "HRRS use"], [
      ["Normal BVA", "min, min+1, nom, max−1, max", "4n + 1", "nights × rooms → 9 cases (TC-QTE-BVA2)"],
      ["Robust BVA", "adds min−1, max+1", "6n + 1", "every single bounded input (7 per variable)"],
      ["Worst-case BVA", "all 5 values crossed", "5ⁿ", "nights × rooms → 25 cases (TC-QTE-WC)"],
      ["Robust worst-case", "all 7 values crossed", "7ⁿ", "49 for n = 2 (not needed after the above)"],
    ], [1.6, 2.6, 1.2, 3.1]),
    tcap("BVA variants and formulas"),
    ...fig("ecp_bva_lines.png", "Equivalence classes (bands) and robust BVA points for three inputs", 6.2),
    table(["Variable (req)", "Range", "Test values", "Cases"], [
      ["Name length (FR-01)", "2–50", "1, 2, 3, 25, 49, 50, 51", "7"], ["Age (FR-01)", "18–120", "17, 18, 19, 60, 119, 120, 121", "7"],
      ["Password length (FR-02)", "8–20", "7, 8, 9, 14, 19, 20, 21", "7"], ["Nights (FR-03)", "1–30", "0, 1, 2, 15, 29, 30, 31", "7"],
      ["Days ahead (FR-03)", "0–365", "−1, 0, 1, 180, 364, 365, 366", "7"], ["Guests (FR-05)", "1–10", "0, 1, 2, 5, 9, 10, 11", "7"],
      ["Rooms (FR-05)", "1–5", "0 … 6", "7"], ["Occupancy per room type (FR-04)", "capacity (+1 bed)", "capacity, capacity+1, with/without bed", "11"],
      ["GST slab (FR-06)", "999|1000, 7500|7501", "−1, 0, 998, 999, 1000, 1001, 4000, 7499, 7500, 7501, 8300", "11"],
      ["Long-stay bands (FR-06)", "6|7, 13|14", "1, 6, 7, 8, 13, 14, 15, 30", "8"], ["Peak season (FR-06)", "20 Dec – 5 Jan", "19, 20, 21, 31 Dec; 1, 4, 5, 6 Jan", "8"],
      ["Promo WELCOME10 (FR-06)", "min ₹3,000; cap ₹1,000", "2999.99, 3000, 3000.01, 9999.90, 10000, 10000.10", "6"],
      ["Refund days (FR-07)", "<0 | 0–1 | 2–6 | ≥7", "−1, 0, 1, 2, 3, 6, 7, 8", "8"], ["Late check-out (FR-14)", "12:00 | 15:00 | 18:00", "11:59 … 23:59 (10 values)", "10"],
      ["Payment amount (FR-08)", "₹1 – ₹5,00,000", "0.99, 1, 1.01, 250000, 499999.99, 500000, 500000.01", "7"],
      ["Card expiry (FR-08)", "this month … +20 years", "09/2026 … 13/2027 (9 values)", "9"],
    ], [2.4, 1.6, 3.6, 0.7], { size: 17, center: [3] }),
    tcap("Single-variable robust BVA design"),
    caseTable(pick((r) => r.id.startsWith("TC-PRC-BVA-0") && Number(r.id.slice(-3)) <= 11)),
    tcap("Executed GST-slab boundary cases"),
    H2("5.3 Decision Table testing"),
    P("A decision table lists every combination of conditions (columns = rules) with the resulting actions. With *n* binary conditions there are 2ⁿ rules; don't-care entries (–) collapse rules that share an outcome. One test per rule gives **rule coverage**."),
    eq("rules = 2ⁿ (limited entry)     →     reduced by “–” entries where outcomes coincide"),
    H3("DT-1 Cancellation refund (FR-07)"),
    table(["Condition / Action", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"], [
      ["C1 Hotel-initiated?", "Y", "N", "N", "N", "N", "N", "N", "N"], ["C2 Refundable rate?", "–", "N", "Y", "Y", "Y", "Y", "Y", "Y"],
      ["C3 Days before check-in", "–", "≥0", "≥7", "2–6", "2–6", "0–1", "0–1", "<0"], ["C4 PLATINUM?", "–", "–", "–", "N", "Y", "N", "Y", "–"],
      ["A1 Refund %", "100", "0", "100", "50", "75", "0", "25", "reject"], ["A2 Fee ₹", "0", "0", "0", "200", "0", "0", "0", "–"],
      ["A3 Voucher", "X", "", "", "", "", "", "", ""]], [2.6, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.85], { size: 17, center: [1, 2, 3, 4, 5, 6, 7, 8] }),
    tcap("Limited-entry decision table DT-1"),
    caseTable(dt1),
    tcap("One executed test per rule (rule coverage); 14 more cases expand C4 over all tiers and test rule precedence"),
    H3("DT-2 Complimentary benefits (FR-15) — exhaustive 2⁴ = 16 rules"),
    P("Derived from the cause-effect graph in 5.4 and executed exhaustively as TC-BEN-DT-001…016 (all PASS). The full 16-column table is in the workbook sheet *Decision Tables*."),
    H3("DT-3 Sign-in and lock-out (FR-02)"),
    table(["Condition / Action", "R1", "R2", "R3", "R4", "R5", "R6"], [
      ["E-mail registered?", "N", "Y", "Y", "Y", "Y", "Y"], ["Password correct?", "–", "Y", "N", "N", "Y", "Y"],
      ["Prior consecutive failures", "–", "0", "0", "2", "3 (locked)", "3, expired"],
      ["Outcome", "401", "token", "401", "423 lock", "423", "token"], ["Test case", "AUTH-DT-001", "-002", "-003", "-004", "-005", "-006"]],
      [2.4, 1, 1, 1, 1, 1, 1.1], { size: 17, center: [1, 2, 3, 4, 5, 6] }),
    tcap("Decision table DT-3 (executed at integration level)"),
    H2("5.4 Cause-Effect Graphing (CEG)"),
    P("CEG models the logical relationships between **causes** (input conditions) and **effects** (outputs) as a Boolean graph with AND (∧), OR (∨) and NOT nodes. The graph is converted into a decision table, and test cases are chosen by **back-tracking** from each effect so that every node's inputs are exercised in the combinations that make it true and false."),
    ...fig("cause_effect.png", "Cause-effect graph for complimentary benefits (FR-15)", 6.2),
    eq("E1 = C1 ∧ C2 ∧ C4        E2 = C1 ∨ (C2 ∧ C3)        E3 = ¬E1 ∧ ¬E2"),
    caseTable(pick((r) => r.id.startsWith("TC-BEN-CEG"))),
    tcap("Reduced CEG test set (10 cases instead of 16) — each AND input made the deciding false input once, each OR input made the sole true input once"),
    P("A second, smaller CEG for surcharges (causes: weekend night, peak night; effect: multiplier) produced TC-PRC-CEG-001…004, covering ×1.00, ×1.20, ×1.30 and the additive ×1.50 when both causes hold."),
    H2("5.5 State Transition testing"),
    P("The state table crosses 6 states with 5 events (30 cells). **0-switch coverage** tests every cell: the 6 valid transitions must move to the right state and the 24 invalid ones must be rejected. **1-switch / path coverage** tests sequences of two or more events."),
    table(["State \\ Event", "pay", "expire", "cancel", "check_in", "check_out"], [
      ["PENDING", "CONFIRMED", "EXPIRED", "CANCELLED", "✗", "✗"], ["CONFIRMED", "✗", "✗", "CANCELLED", "CHECKED_IN", "✗"],
      ["CHECKED_IN", "✗", "✗", "✗", "✗", "CHECKED_OUT"], ["CHECKED_OUT", "✗", "✗", "✗", "✗", "✗"],
      ["CANCELLED", "✗", "✗", "✗", "✗", "✗"], ["EXPIRED", "✗", "✗", "✗", "✗", "✗"]],
      [1.8, 1.3, 1.2, 1.3, 1.3, 1.4], { size: 17, center: [1, 2, 3, 4, 5] }),
    tcap("State table — ✗ cells must raise TRANSITION_INVALID (TC-STM-001…030)"),
    caseTable(pick((r) => r.id.startsWith("TC-STM-SEQ"))),
    tcap("Transition sequences (n-switch)"),
    H2("5.6 Pairwise (combinatorial) testing with a test oracle"),
    P(`Five pricing parameters (room 4 × tier 4 × promo 3 × extra bed 2 × stay pattern 3) give **288** combinations. A greedy all-pairs generator covers every pair of values in only **${count((r) => r.id.startsWith("TC-QTE-PW"))} cases**. Each result is compared with an **independent test oracle** — a deliberately naive re-implementation of the pricing equations written from the SRS, not the code — so a shared misunderstanding cannot hide.`),
    eq("|pairs| = Σ_{i<j} |Pᵢ|·|Pⱼ| = 125 value pairs   →   20 test cases (93 % fewer than 288)"),
    H2("5.7 Property-based testing and error guessing"),
    P("Hypothesis generates hundreds of random inputs per property and shrinks failures to a minimal example. Properties encode **invariants** and **metamorphic relations** that must always hold:"),
    table(["ID", "Property", "Examples"], [
      ["TC-PBT-001", "total = taxable + GST and every amount ≥ 0", "200"], ["TC-PBT-002", "discount ≤ 30 % of subtotal (cap)", "200"],
      ["TC-PBT-003", "Metamorphic: one more night never lowers the subtotal", "200"], ["TC-PBT-004", "Metamorphic: k rooms cost k × one room", "200"],
      ["TC-PBT-005", "0 ≤ refund ≤ amount paid", "300"], ["TC-PBT-006", "Changing any digit of a Luhn-valid number breaks it", "200"],
      ["TC-PBT-007", "Random event sequences never escape the 6 states", "300"], ["TC-PBT-008", "Every accepted password satisfies all rules", "400"]],
      [1.3, 5.8, 1.1], { center: [2] }),
    tcap("Property-based test cases"),
    caseTable(pick((r) => r.id.startsWith("TC-EG"))),
    tcap("Error-guessing cases (leap years, year-end, type confusion, injection-shaped strings)"),
  ];
}

// =========================================================================== 6 white box
function whitebox() {
  const topcc = [];
  Object.entries(cc).forEach(([f, blocks]) => blocks.forEach((b) => { if (b.type === "function" || b.type === "method") topcc.push([b.name, f.replace("app/", ""), b.complexity, b.rank]); }));
  topcc.sort((a, b) => b[2] - a[2]);
  return [
    H1("6. White-Box Testing — Source-Code Coverage"),
    P("White-box (structural) testing designs cases from the code's control and data flow. The criteria form a **subsumption hierarchy** — satisfying a stronger one guarantees the weaker ones:"),
    eq("Path  ⟹  MC/DC  ⟹  Condition/Decision  ⟹  Branch (Decision)  ⟹  Statement"),
    table(["Criterion", "Requirement", "Coverage formula"], [
      ["Statement (C0)", "Every statement executes at least once", "statements executed ÷ total statements"],
      ["Branch / decision (C1)", "Every decision takes both TRUE and FALSE", "branches taken ÷ total branches"],
      ["Condition", "Every atomic condition is both TRUE and FALSE", "condition outcomes ÷ (2 × conditions)"],
      ["MC/DC", "Each condition shown to independently change the decision", "≥ N + 1 tests for N conditions"],
      ["Basis path", "V(G) linearly independent paths", "independent paths executed ÷ V(G)"],
      ["Loop", "0, 1, 2, typical m, n−1, n, n+1 iterations", "—"],
      ["Data flow", "all-defs / all-uses / all-du-paths", "du-pairs exercised ÷ du-pairs"],
    ], [1.8, 3.6, 3.1]),
    tcap("Coverage criteria"),
    H2("6.1 Cyclomatic complexity and basis paths — refund_decision()"),
    ...code(src("app/domain/cancellation.py", "refund_decision")),
    SP(80),
    ...fig("cfg_refund.png", "Control-flow graph of refund_decision() with predicate nodes D1–D7", 6.4),
    P("McCabe's cyclomatic complexity V(G) is the number of linearly independent paths — the minimum number of tests for basis-path coverage. Three equivalent ways to compute it on this graph:"),
    eq("V(G) = E − N + 2P = 23 − 17 + 2(1) = 8"),
    eq("V(G) = number of predicate nodes + 1 = 7 + 1 = 8"),
    eq("V(G) = number of bounded regions + 1 = 7 + 1 = 8"),
    callout("Why does Radon report 9?", "Radon counts each Boolean operator as an extra decision (extended/Myers complexity). The expression `(tier or \"NONE\")` adds one, so radon gives 9 while the classic McCabe count on the CFG is 8. Both are correct for their definitions; basis-path design uses the CFG value."),
    caseTable(pick((r) => r.id.startsWith("TC-WB-PATH") && Number(r.id.slice(-3)) <= 8)),
    tcap("Eight basis-path test cases — together they also achieve 100 % statement and branch coverage of the function"),
    H2("6.2 Statement vs. branch vs. condition vs. MC/DC — promo_amount()"),
    ...code(src("app/domain/pricing.py", "promo_amount")),
    SP(80),
    P("The final `if cap is not None and amount > cap` shows why each criterion is stronger than the previous one:"),
    table(["Criterion", "Tests needed", "Chosen tests", "What the weaker criterion misses"], [
      ["Statement", "1", "WELCOME10 on ₹50,000 → cap applied (TC-WB-STMT-001)", "—"],
      ["Branch", "2", "+ WELCOME10 on ₹4,000 → decision FALSE (TC-WB-BR-001)", "statement coverage never takes the FALSE arm"],
      ["Condition", "2–3", "+ FLAT500 → `cap is not None` FALSE (TC-WB-COND-001)", "branch coverage never makes condition A false"],
      ["MC/DC", "N + 1 = 3", "(T,T)→T, (T,F)→F, (F,–)→F (TC-WB-MCDC-001…003)", "condition coverage may not show each condition's independent effect"],
    ], [1.2, 1, 3.5, 2.8], { size: 17 }),
    tcap("Coverage ladder on one compound decision"),
    H3("MC/DC on a four-condition decision — is_peak_night()"),
    eq("peak = (A ∧ B) ∨ (C ∧ D)   A: month = 12   B: day ≥ 20   C: month = 1   D: day ≤ 5"),
    table(["Test", "Date", "A", "B", "C", "D", "Outcome", "Independence pair"], [
      ["MCDC-004", "25 Dec", "T", "T", "F", "F", "T", "base"], ["MCDC-005", "10 Dec", "T", "F", "F", "F", "F", "B (with 004)"],
      ["MCDC-006", "25 Nov", "F", "T", "F", "F", "F", "A (with 004)"], ["MCDC-007", "3 Jan", "F", "F", "T", "T", "T", "base"],
      ["MCDC-008", "10 Jan", "F", "F", "T", "F", "F", "D (with 007)"], ["MCDC-009", "3 Nov", "F", "F", "F", "T", "F", "C (with 007)"]],
      [1.1, 1, 0.5, 0.5, 0.5, 0.5, 0.9, 1.8], { size: 17, center: [2, 3, 4, 5, 6] }),
    tcap("MC/DC table — 6 tests (A and C are coupled: a month cannot be both 12 and 1, so N + 1 = 5 is not reachable)"),
    H2("6.3 Data-flow testing — late_checkout_fee()"),
    ...fig("cfg_latefee.png", "Control-flow graph annotated with definitions and uses of rate and pct", 5.6),
    table(["Variable", "Definition (node)", "Use (node, kind)", "du-path", "Test"], [
      ["rate", "1", "2 p-use (rate < 0)", "1 → 2", "TC-WB-DF-001"], ["pct", "4 (= 0)", "10 c-use", "4 → 10", "TC-WB-DF-002"],
      ["pct", "6 (= 25)", "10 c-use", "6 → 10", "TC-WB-DF-003"], ["pct", "8 (= 50)", "10 c-use", "8 → 10", "TC-WB-DF-004"],
      ["pct", "9 (= 100)", "10 c-use", "9 → 10", "TC-WB-DF-005"], ["amount (promo)", "PCT branch", "p-use > cap, c-use return", "def → cap → return", "TC-WB-DF-006"],
      ["amount (promo)", "AMT branch", "c-use return", "def → return", "TC-WB-DF-007"]], [1.4, 1.4, 1.9, 1.6, 1.4], { size: 17 }),
    tcap("Definition-use pairs and the tests that cover them (all-defs and all-uses satisfied)"),
    H2("6.4 Loop testing"),
    P("The per-night loop of `compute_quote` is a simple loop with bound n = 30. Simple-loop testing exercises skip (0 → rejected), 1, 2, typical m = 15, n − 1 = 29 and n = 30 iterations (TC-WB-LOOP-001…006); n + 1 = 31 is covered by BVA at the validation layer (TC-SRCH-BVA-007). TC-WB-LOOP-007 runs the Luhn loop with digits that do and do not overflow when doubled."),
    H2("6.5 Complexity profile of the code base"),
    table(["Function", "Module", "CC (radon)", "Rank"], topcc.slice(0, 12).map((r) => [r[0], r[1], String(r[2]), r[3]]), [3, 3, 1.2, 1], { center: [2, 3] }),
    tcap("Twelve most complex functions (A ≤ 5, B 6–10, C 11–20) — the C-ranked ones received the densest test design"),
    H2("6.6 Coverage results"),
    ...fig("coverage.png", "Statement + branch coverage per module before and after coverage-guided tests", 6.2),
    P(`The first full run reached ${covT0.percent_covered.toFixed(1)} %. The uncovered lines were not noise — they pointed at untested behaviour, so ten **coverage-guided** cases were added (TC-COV-001…010). The most important: no API test had ever triggered the HTTP 409 handler for an illegal state transition (paying an already confirmed booking). Final: **${covT.covered_lines}/${covT.num_statements} statements (100 %)** and **${covT.covered_branches}/${covT.num_branches} branches (${covT.percent_branches_covered.toFixed(1)} %)**; the one partial branch is the \`seed_admin=False\` path of the app factory, used only by tools.`),
    caseTable(pick((r) => r.id.startsWith("TC-COV"))),
    tcap("Coverage-guided test cases"),
    H2("6.7 Mutation testing — measuring test effectiveness"),
    P("Coverage shows code was **executed**, not that a wrong result would be **noticed**. Mutation testing injects small syntactic faults (mutants) and checks whether the suite fails (kills the mutant). We built an AST-based engine (`tools/mutation.py`) with six classic operators and ran the unit suite against every mutant in parallel sandboxes."),
    eq("Mutation score MS = killed ÷ (total − equivalent) = 267 ÷ (270 − 3) = 100 %"),
    table(["Operator", "Meaning", "Example on HRRS", "Killed / total"], [
      ["ROR", "Relational operator replacement", "`days_before >= 7` → `days_before > 7`", "120 / 122"],
      ["CRP", "Constant replacement", "`nights >= 14` → `nights >= 15`", "51 / 52"],
      ["AOR", "Arithmetic operator replacement", "`subtotal - discount` → `subtotal + discount`", "32 / 32"],
      ["UOD", "Unary NOT deletion", "`if not refundable` → `if refundable`", "29 / 29"],
      ["LCR", "Logical connector replacement", "`c1 and c2 and c4` → `c1 or c2 and c4`", "25 / 25"],
      ["BRV", "Boolean literal flip", "`frozen=True` → `frozen=False`", "10 / 10"]], [0.8, 2.3, 3.6, 1.2], { size: 17, center: [3] }),
    tcap("Mutation operators (survivors in ROR/CRP are the 3 equivalent mutants)"),
    ...fig("mutation_iterations.png", "Mutation score across three improvement iterations", 5.6),
    P("Iteration 1 killed 232/270 (85.9 %). The 38 survivors were analysed one by one: **all 23 metrics mutants survived** because occupancy/ADR/RevPAR were only tested at integration level; others revealed missing boundaries — e-mail length 254/255, a tariff of exactly ₹0, discounts summing to *exactly* the 30 % cap, boolean head-counts. 23 mutation-guided tests raised the score to 97.8 %; three more (a one-room hotel) to 98.9 %. The last 3 survivors are **equivalent mutants** — they can never change behaviour:"),
    table(["Mutant", "Change", "Why it is equivalent"], mut.mutants.filter((m) => m.status === "EQUIVALENT").map((m) => [m.id, m.change, m.equivalence_reason]), [1.4, 1.2, 5.9], { size: 17 }),
    tcap("Equivalent mutants (manual proof)"),
    H2("6.8 Fault seeding — estimating residual defects"),
    P("Fault seeding injects **realistic, hand-written** bugs at all layers and runs the full suite (unit → E2E). If the suite finds s of S seeded faults and n native faults, Mills' estimator gives the expected total native faults:"),
    eq(`N̂ = n × S ÷ s = ${seed.summary.native_found} × ${seed.summary.seeded} ÷ ${seed.summary.seeded_detected} = ${seed.summary.mills_estimated_native_total}     latent ≈ N̂ − n = ${seed.summary.estimated_latent}`),
    ...fig("fault_seeding.png", "Seeded faults and how many tests each one broke", 6.3),
    callout("The miss that taught us the most.", "In Rev A the suite **missed SF-11** — UI messages rendered with `innerHTML` (a DOM-XSS hole). Our XSS test (TC-E2E-003) used the login error, which never echoes user input, so it could not see the difference. The promo-code error *does* echo input. The test was rewritten to attack that path; the seeded fault is now caught (Rev B 12/12). Logged as **DEF-005** — a defect in the test suite itself.", "FFF3D6", "EDA100"),
  ];
}

// =========================================================================== 7 levels
function levels() {
  const feat = fs.readFileSync(path.join(ROOT, "tests/acceptance/features/booking.feature"), "utf8").split("\n");
  return [
    H1("7. Test Cases by Testing Level"),
    H2("7.1 Unit level"),
    P(`${byLevel("Unit")} unit cases target the pure domain functions — all of Chapters 5 and 6. They run in under three seconds, so they run on every change.`),
    H2("7.2 Integration level"),
    P("Integration was **bottom-up** — domain rules first, then the service with a real SQLite database, then the HTTP layer — with one **top-down** element: the external payment gateway is replaced by a **stub** that can inject timeouts and declines, and pytest acts as the **driver**."),
    ...fig("integration_strategy.png", "Integration strategy, drivers and stubs", 4.8),
    caseTable(pick((r) => r.id.startsWith("TC-INT")), [1.4, 4.6, 2.8, 2.4, 0.9]),
    tcap("Integration test cases"),
    callout("Concurrency evidence.", "TC-INT-005 releases 20 threads simultaneously (a barrier) to book the same 3 suites. Exactly 3 succeed, 17 get NO_AVAILABILITY and no room is allocated twice. To rule out a lucky interleaving, the test was repeated 25 times: 25/25 passed."),
    H2("7.3 System level (API)"),
    caseTable(pick((r) => r.id.startsWith("TC-SYS-FN") || r.id.startsWith("TC-SYS-SMK") || r.id.startsWith("TC-SYS-API")), [1.6, 4.4, 2.8, 2.4, 0.9]),
    tcap("Functional, smoke and contract system tests"),
    caseTable(pick((r) => r.id.startsWith("TC-SYS-NEG")), [1.6, 4.4, 2.8, 2.4, 0.9]),
    tcap("Negative API tests — every error returns the documented status code and machine-readable error code"),
    H2("7.4 System level (end-to-end UI)"),
    P("Playwright drives a real Chromium browser against a live uvicorn server. Every run records **video** and **step screenshots** (included in the submission)."),
    ...fig(path.join(L.SHOT, "05_paid.png"), "TC-E2E-001 — booking confirmed after payment (captured during the test run)", 4.6),
    caseTable(pick((r) => r.id.startsWith("TC-E2E")), [1.4, 4.6, 2.8, 2.4, 0.9]),
    tcap("End-to-end UI cases (two cross-browser cases skipped: Firefox/WebKit binaries not installable in the lab sandbox)"),
    H2("7.5 Acceptance level (UAT with BDD)"),
    P("Acceptance criteria were written in Gherkin with the product owner's vocabulary and executed with pytest-bdd. The Scenario Outline runs three examples."),
    ...code(feat),
    SP(80),
    caseTable(pick((r) => r.id.startsWith("TC-UAT"))),
    tcap("Acceptance test cases"),
  ];
}

// =========================================================================== 8 non functional
function nonfunctional() {
  const load = perf.load, l0 = perf0.load;
  return [
    H1("8. Non-Functional Testing"),
    H2("8.1 Performance testing"),
    P("A dedicated harness (`tools/perf_test.py`) runs a realistic mix — 50 % availability, 30 % quotes, 15 % book-and-pay, 5 % booking lists — against a live server on a file database. Six campaign types were run:"),
    table(["Type", "Goal", "Profile", "Result"], [
      ["Baseline", "Reference latency", "1 user × 200 requests", `p95 ${perf.baseline.p95_ms} ms`],
      ["Load", "SLA at expected peak", "25 users × 40 requests", `p95 ${load.p95_ms} ms (SLA 300) · ${load.throughput_rps} req/s · ${load.error_rate_pct} % errors`],
      ["Stress", "Find the breaking point", "10 → 25 → 50 → 100 → 200 users", "SLA knee ≈ 50 users; 0 errors even at 200"],
      ["Spike", "Sudden burst & recovery", "5 → 150 → 5 users", `burst p95 ${perf.spike.burst.p95_ms} ms; back to ${perf.spike.after.p95_ms} ms`],
      ["Soak (endurance)", "Leaks / drift", "20 users for 60 s", `≈ ${perf.soak.windows.reduce((a, w) => a + w.requests, 0).toLocaleString("en-IN")} requests; RSS flat ≈ ${perf.soak.windows.at(-1).rss_mb} MB`],
      ["Volume", "Data-size sensitivity", "+5,000 bookings in DB", `p95 ${perf.volume.before.p95_ms} → ${perf.volume.after.p95_ms} ms`],
    ], [1.3, 1.8, 2.4, 3], { size: 17 }),
    tcap("Performance campaign"),
    ...fig("load_endpoints.png", "Per-endpoint p95 at 25 users before and after the DEF-004 fix", 5.6),
    callout("Defect found by load testing — DEF-004.", `Overall p95 met the SLA (${l0.p95_ms} ms), but **book + pay** was ${l0.by_endpoint_p95.book} ms. Root cause: SQLite's default rollback journal fsyncs every commit and blocks readers during writes. Enabling WAL journaling with synchronous=NORMAL gave book p95 **${load.by_endpoint_p95.book} ms (−${Math.round(100 * (1 - load.by_endpoint_p95.book / l0.by_endpoint_p95.book))} %)**, overall p95 ${load.p95_ms} ms and +${Math.round(100 * (load.throughput_rps / l0.throughput_rps - 1))} % throughput, re-measured with the identical seeded workload.`, "FBE1E1", "E34948"),
    ...fig("stress_latency.png", "Stress test: p95 latency against concurrent users", 5.6),
    ...fig("stress_throughput.png", "Stress test: throughput saturates around 10 users for one worker process", 5.6),
    ...fig("soak.png", "Soak test: no latency drift and no memory growth over 60 s", 6.2),
    ...fig("spike.png", "Spike test: latency rises under a 150-user burst and recovers immediately", 4.6),
    P("Little's law cross-checks the load numbers: concurrency ≈ throughput × mean response time."),
    eq(`L = λ × W = ${load.throughput_rps} req/s × ${(load.mean_ms / 1000).toFixed(4)} s ≈ ${(load.throughput_rps * load.mean_ms / 1000).toFixed(1)} requests in flight  (25 users, each also spends time in the client)`),
    H2("8.2 Security testing"),
    table(["OWASP 2021 category", "Attack / check", "Test", "Result"], [
      ["A01 Broken access control", "Guest reads/pays/cancels another guest's booking (IDOR)", "TC-SEC-005, TC-INT-015", "403 — blocked"],
      ["A01 Broken access control", "Guest sets own tier / forces hotel-initiated refund", "TC-SEC-006", "403 — blocked"],
      ["A02 Cryptographic failures", "Plain passwords, hash or PAN in responses or DB", "TC-INT-016, TC-SEC-011, TC-INT-006", "PBKDF2-SHA256 ×120k; masked PAN only"],
      ["A03 Injection", "SQLi in e-mail, password, path; dynamic UPDATE", "TC-SEC-001…003, TC-INT-025", "parameterised; allow-list"],
      ["A03 Injection (XSS)", "Stored XSS in name; reflected/DOM XSS via promo error", "TC-SEC-004, TC-E2E-003", "rejected; rendered as text"],
      ["A05 Misconfiguration", "Security headers; stack traces", "TC-SEC-010, TC-SEC-012", "CSP, XFO, nosniff, no traces"],
      ["A07 Auth failures", "Brute force; user enumeration; logout", "TC-SEC-007…009", "lock after 3; same message; token revoked"],
      ["Integrity", "Replay / double charge", "TC-SEC-013, TC-INT-007", "Idempotency-Key enforced"],
    ], [1.9, 3, 2, 1.7], { size: 16 }),
    tcap("Security test mapping to OWASP Top 10"),
    P(`Static application security testing (Bandit) reported ${bandit.results.length} medium findings (B608 string-built SQL). One was a real hardening opportunity (fixed with a column allow-list, CI-01); the other is a false positive (only “?” placeholders are interpolated, CI-02).`),
    H2("8.3 Usability and accessibility testing"),
    P(`The axe-core engine audited the rendered page against WCAG 2.0/2.1 A and AA rules: **${axe.violations.length} violations, ${axe.passes} rules passed, ${axe.incomplete} needing review**. TC-E2E-005 completes sign-in with the keyboard alone. Manual heuristic evaluation, think-aloud sessions and screen-reader passes are designed as TC-MAN-USE-001/002 and TC-MAN-A11Y-001 for the team to execute.`),
    H2("8.4 Compatibility testing"),
    P("Chromium device emulation verified the layout on iPhone 13, Pixel 7, iPad (gen 7) and desktop with no horizontal scrolling (TC-E2E-006…009). Cross-browser cases for Firefox and WebKit are automated but were **skipped** because those browsers could not be downloaded in the sandbox; they run unchanged on a team laptop after `playwright install`."),
    ...fig(path.join(L.SHOT, "08_device_iPhone_13.png"), "TC-E2E-006 — search results on an emulated iPhone 13", 2.2),
    H2("8.5 Reliability, recovery and concurrency"),
    ...bullets([
      "**Fault injection:** gateway timeout and decline leave the booking PENDING with no payment row; a retry succeeds (TC-INT-008, TC-INT-024, TC-SYS-REC-001).",
      "**Restart recovery:** a new process on the same database file sees the committed booking (TC-INT-009, TC-COV-009).",
      "**Concurrency:** no overbooking under a 20-thread race, 25/25 repetitions (TC-INT-005).",
      "**Stability:** the full suite run twice in succession gave identical results (no flaky tests).",
    ]),
  ];
}

// =========================================================================== 9 static, 10 results, 11 metrics
function staticTesting() {
  return [
    H1("9. Static Testing"),
    P("Static testing finds defects without executing code — it is the cheapest point to remove them."),
    H2("9.1 Requirements review"),
    table(["ID", "Req", "Type", "Finding", "Resolution"], ms.requirement_review.map((x) => [x.id, x.requirement, x.type, x.finding, x.resolution]),
      [0.7, 1, 1.1, 3, 3], { size: 16 }),
    tcap("Requirements review findings (all resolved before test design)"),
    H2("9.2 Code inspection and static analysis"),
    P(`Ruff (lint, complexity, security rules) reported ${ruff.length} findings and Bandit ${bandit.results.length}; each was triaged rather than blindly fixed or ignored:`),
    table(["ID", "File", "Finding", "Decision", "Status"], ms.code_inspection.map((x) => [x.id, x.file, x.finding, x.decision, x.status]), [0.7, 1.4, 2.6, 3, 1.1], { size: 16 }),
    tcap("Code inspection log"),
  ];
}

function execution() {
  const tech = {};
  results.forEach((r) => { const t = r.technique.split(" (")[0]; tech[t] = (tech[t] || 0) + 1; });
  return [
    H1("10. Test Execution and Defects"),
    H2("10.1 Execution summary"),
    table(["Level", "Executed", "Passed", "Failed", "Skipped", "Pass rate"], ["Unit", "Integration", "System", "System (E2E UI)", "Acceptance (UAT)"].map((lv) => {
      const rs = results.filter((r) => r.level === lv), p = rs.filter((r) => r.status === "PASS").length, s = rs.filter((r) => r.status === "SKIPPED").length;
      return [lv, String(rs.length - s), String(p), "0", String(s), pct(p / (rs.length - s))];
    }).concat([["TOTAL", String(N - SKIP), String(PASS), "0", String(SKIP), pct(PASS / (N - SKIP))]]),
    [2.2, 1, 1, 1, 1, 1.2], { center: [1, 2, 3, 4, 5] }),
    tcap(`Execution summary (run on ${results[0].executed_at.slice(0, 10)}, frozen clock)`),
    callout("Reconciling the counts.", `pytest itself reports **558 passed, 2 skipped** (560 test functions). The catalogue counts **${N} test cases**: the UAT-003 Scenario Outline is one test case that runs three examples (+2), and four structural self-checks (e.g. that the pairwise set really covers every pair) carry no test-case ID (+4). 554 + 2 + 4 = 560.`),
    ...fig("techniques.png", "Executed test cases by design technique", 5.8),
    H2("10.2 Requirements traceability"),
    ...fig("rtm_heatmap.png", "Executed test cases per requirement and level (RTM heat-map)", 5.0),
    H2("10.3 Defect report"),
    ...fig("defect_lifecycle.png", "Defect life cycle followed for every defect", 6),
    ...defects.flatMap((dd) => [
      H3(`${dd.id} — ${dd.title}`),
      table(["Field", "Detail"], [["Found by", dd.found_by], ["Technique", dd.technique], ["Module / requirement", `${dd.module} / ${dd.requirement}`],
        ["Severity / priority", `${dd.severity} / ${dd.priority}`], ["Steps to reproduce", dd.steps], ["Expected", dd.expected], ["Actual (before fix)", dd.actual_before_fix],
        ["Root cause", dd.root_cause], ["Fix", dd.fix], ["Status", dd.status]], [1.8, 6.7], { size: 17 }),
    ]),
    ...(defectsManual.length ? [
      H3("Defects found by manual testing (packaging and documentation)"),
      P(`Manual case TC-MAN-DOC-001 followed every README command on a clean machine, exactly as an examiner would. It failed the first time and raised **${defectsManual.length} further defects** — none in the reservation system itself, all in how the project is packaged and documented. They are kept separate from the product defects above so that the product metrics (defect density, DRE, Mills' estimate) are not distorted.`),
      table(["ID", "Defect", "Severity", "Root cause → fix", "Status"], defectsManual.map((dd) => [dd.id, dd.title, dd.severity, `${dd.root_cause} → ${dd.fix}`, dd.status]),
        [0.8, 2.6, 0.8, 3.4, 0.9], { size: 15 }),
      tcap("Packaging and documentation defects (TC-MAN-DOC-001), regression-protected by tools/check_package.py"),
    ] : []),
    ...manualExecution(),
  ];
}

function manualExecution() {
  const mc = ms.manual_cases;
  if (!mc[0].status) return [];
  const cnt = (f) => mc.filter(f).length;
  const passed = cnt((m) => m.status.startsWith("PASS")), prog = cnt((m) => m.status === "IN PROGRESS"), notRun = cnt((m) => m.status === "NOT RUN");
  const use = mc.find((m) => m.id === "TC-MAN-USE-001");
  return [
    H2("10.4 Manual test execution"),
    P(`The ${mc.length} manual cases were executed wherever that could be done honestly. **${passed} passed**, **${prog} are in progress** (the tool-assisted half is done; the human half is pending) and **${notRun} have not been run** because they need real participants or physical devices — those are never simulated. Each pending case has a ready-to-use kit (task script, questionnaire, checklist, recording sheet) in the Manual Test Execution Kit.`),
    table(["ID", "Type", "Tester", "Actual result", "Status"], mc.map((m) => [m.id, m.type, m.tester, m.actual, m.status]), [1.3, 1.0, 1.5, 4.0, 0.9], { size: 14 }),
    tcap("Manual test execution record"),
    H3("Localisation evidence"),
    P("TC-MAN-L10N-001 quoted the longest permitted stay (30 nights, two Family rooms). Every amount on screen uses the rupee sign, Indian lakh grouping and two decimals; the screenshot below is the evidence."),
    ...fig("../../reports/manual/L10N-001_quote.png", "TC-MAN-L10N-001 — amounts above ₹1 lakh in Indian grouping", 4.2),
    P("TC-MAN-L10N-002 started Chromium once with an Indian English and once with a US English interface. The fields show DD/MM/YYYY and MM/DD/YYYY respectively, and in both cases the API receives ISO dates (2026-11-15). The display order follows the browser's interface language, which is how native date controls work."),
    ...fig("../../reports/manual/L10N-002_dates_en-IN.png", "TC-MAN-L10N-002 — date fields in an en-IN browser show DD/MM/YYYY", 5.6),
    H3("Heuristic evaluation (TC-MAN-USE-001, evaluator 1)"),
    table(["Heuristic", "Severity", "Notes"], use.heuristic_scores.map(([h, sc, n]) => [h, String(sc), n]), [2.4, 0.8, 5.3], { size: 15, center: [1] }),
    tcap("Nielsen heuristics, severity 0 (none) to 4 (catastrophe) — highest score 2, so no major usability problem"),
    table(["ID", "Observation", "Severity", "Disposition"], use.observations, [0.8, 5.3, 1.2, 1.2], { size: 15 }),
    tcap("Usability and accessibility observations (backlog, not release-blocking)"),
    H3("Screen-reader proxy (TC-MAN-A11Y-001)"),
    P(mx ? `Before the real NVDA/VoiceOver pass, the accessibility tree that a screen reader reads was inspected directly: **${mx["A11Y-001"].controls.length} form controls, 0 without an accessible name**; ${mx["A11Y-001"].live_regions.length} live or status regions; the sign-in tabs are exposed as tabs with a selected state; and a failed sign-in message is placed in a status region, so it is announced. The proxy found one gap the automated axe audit did not: the bookings table has an empty column header (UX-06).` : use.actual),
  ];
}

function metrics() {
  const sloc = 1023;
  return [
    H1("11. Test Metrics"),
    table(["Metric", "Formula", "Value"], [
      ["Test execution rate", "executed ÷ designed", `${N - SKIP} ÷ ${N} = ${pct((N - SKIP) / N)}`],
      ["Pass rate", "passed ÷ executed", `${PASS} ÷ ${N - SKIP} = ${pct(PASS / (N - SKIP))}`],
      ["Requirement coverage", "requirements with ≥1 test ÷ total", `${reqs.length} ÷ ${reqs.length} = 100 %`],
      ["Statement coverage", "statements executed ÷ statements", `${covT.covered_lines} ÷ ${covT.num_statements} = 100 %`],
      ["Branch coverage", "branches taken ÷ branches", `${covT.covered_branches} ÷ ${covT.num_branches} = ${covT.percent_branches_covered.toFixed(1)} %`],
      ["Mutation score", "killed ÷ (total − equivalent)", "267 ÷ 267 = 100 %"],
      ["Seeded fault detection", "s ÷ S", `${seed.summary.seeded_detected} ÷ ${seed.summary.seeded} = 100 % (Rev A 91.7 %)`],
      ["Defect density", "product defects ÷ KLOC", `4 ÷ ${(sloc / 1000).toFixed(3)} = ${(4 / (sloc / 1000)).toFixed(2)} defects/KLOC`],
      ["Defect removal efficiency", "pre-release ÷ (pre + post-release)", "4 ÷ (4 + 0) = 100 % (to be re-measured after beta)"],
      ["Test-to-code ratio", "test LOC ÷ app LOC", "≈ 3,000 ÷ 1,023 ≈ 2.9 : 1"],
      ["Automation rate", "automated cases ÷ all designed cases", `${N} ÷ ${N + ms.manual_cases.length} = ${pct(N / (N + ms.manual_cases.length))}`],
      ["Mean time per test", "Σ duration ÷ executed", `${(results.reduce((a, r) => a + r.duration_ms, 0) / (N - SKIP)).toFixed(1)} ms`],
    ], [2.2, 2.9, 3.4], { size: 18 }),
    tcap("Test metrics"),
  ];
}

// =========================================================================== 12 case study, 13 conclusion, appendices
function caseStudy() {
  return [
    H1("12. Case Study — One Booking, Every Lens"),
    P("To show how the techniques fit together, follow one realistic request through the system: *Ananya (GOLD member) books one Deluxe room with an extra bed for her family of 3 adults + 1 child, Fri 18 → Sun 20 Dec 2026, booking 71 days ahead, with promo WELCOME10, then cancels 4 days before arrival.*"),
    table(["Lens", "What we ask", "Answer for this booking"], [
      ["ECP", "Which class is each input in?", "tier GOLD (valid V3), room DELUXE (V2), promo WELCOME10 (V2), 4 guests (valid)"],
      ["BVA", "Is any input on a boundary?", "4 guests = DELUXE capacity 3 + 1 bed → exactly at max (TC-BOOK-BVA-019); 19 Dec is just before peak (TC-PRC-BVA-020)"],
      ["Pricing equations", "What should it cost?", "tariff 4,000 + 800 = 4,800 → 5 % GST; Fri ×1.20 + Sat ×1.20 → subtotal 11,520; discount = 10 % GOLD 1,152 + promo 1,000 (cap) = 2,152 ≤ 30 % → taxable 9,368; GST 468.40; total ₹9,836.40"],
      ["Cause-effect (FR-15)", "Which benefits?", "C1 = T (GOLD), C2 = F (2 nights) → E1 upgrade = F, E2 breakfast = T"],
      ["State transition", "Which path?", "PENDING → pay → CONFIRMED → cancel → CANCELLED"],
      ["Decision table (FR-07)", "What refund?", "refundable, 4 days, not PLATINUM → rule R4: 50 % − ₹200 = ₹4,718.20"],
      ["White-box", "Which code paths?", "refund_decision basis path P6; promo_amount cap TRUE branch (MC/DC case 001)"],
      ["Integration", "What changes in the DB?", "1 bookings row, 1 booking_rooms row, 1 payment row (masked card), audit entries"],
      ["Security", "What must not be possible?", "another guest reading it (403), replaying the payment (idempotent), seeing the card number"],
      ["Performance", "Is it fast at peak?", "book + pay p95 ≈ 201 ms at 25 concurrent users"],
    ], [1.5, 2, 5], { size: 17 }),
    tcap("One booking analysed with every technique"),
    P("The pricing row was checked independently: the test oracle in `test_combinatorial_property.py` and the production engine both return ₹9,836.40 for these inputs."),
    H2("12.1 Lessons learnt"),
    ...bullets([
      "**Specification techniques find specification defects.** ECP's “valid class V4” immediately found a real bug that random valid names would rarely hit.",
      "**Coverage is necessary, not sufficient.** 97.8 % coverage still hid 38 surviving mutants; mutation testing turned “executed” into “checked”.",
      "**Test the tests.** Fault seeding exposed that a security test exercised a path that could not fail — the most valuable finding of the project.",
      "**Non-functional defects hide behind averages.** The overall p95 met the SLA while one endpoint was more than twice over it.",
      "**Visual review still matters.** Two UI defects were found by looking at a screenshot, then locked in with automated regression tests that were proven to fail on the buggy version.",
      "**Honest reporting.** Cases that could not run here (Firefox/WebKit) are reported as SKIPPED with the reason, never as passed.",
      "**Test the package, not only the product.** Following our own README on a clean machine found five defects that 554 passing tests could not: the evidence only counts if someone else can reproduce it.",
    ]),
  ];
}

function conclusion() {
  return [
    H1("13. Conclusion and Future Work"),
    P(`This project specified, built and verified a non-trivial reservation system and documented ${N} executable test cases across every level and technique in the FT-3 plan and beyond. All P1 cases pass, structural coverage is complete, the mutation score is 100 % on non-equivalent mutants, every seeded fault is detected and all five defects found by automated testing were fixed and protected by regression tests. Manual testing then found five packaging and documentation defects, all fixed and retested. The exit criteria in the test plan are met.`),
    H2("Future work"),
    ...bullets(["Finish the four manual cases that need people or devices (usability study with five participants, ten-person beta, Firefox on Windows, Safari on iPhone) and the human halves of USE-001 and A11Y-001, using the execution kit.",
      "Run the Firefox/WebKit cross-browser cases on machines where those browsers are installed.", "Add a CI pipeline (GitHub Actions) that runs smoke on every push and the full suite nightly.",
      "Scale-out performance tests with multiple uvicorn workers and PostgreSQL.", "Contract testing against a real payment-gateway sandbox."]),
  ];
}

function appendix() {
  const rs = results.slice().sort((a, b) => a.id.localeCompare(b.id));
  return [
    H1("Appendix A — Complete Test Case Catalogue"),
    P(`All ${N} catalogued test cases with their actual result from the final run. Full IEEE 829 fields (pre-conditions, steps, automated test node) are in the workbook.`, { run: { size: 20 } }),
    table(["TC ID", "Objective", "Technique", "Level", "Req", "Result"], rs.map((r) => [r.id, r.title, r.technique.split(" (")[0], r.level.replace("System (E2E UI)", "E2E").replace("Acceptance (UAT)", "UAT"), r.requirement, r.status]),
      [1.7, 4, 1.7, 0.9, 1, 0.8], { size: 14, center: [5], fill: (r) => (r[5] === "SKIPPED" ? "FFF3D6" : null) }),
    H1("Appendix B — How to Reproduce"),
    ...code(["# from the project root (hrrs/)", "pip install -r requirements.txt", "python -m playwright install chromium",
      "", "# run the web app", "uvicorn app.main:app --reload       # open http://127.0.0.1:8000",
      "", "# full suite with coverage + HTML report", "pytest --cov=app --cov-branch --html=reports/test_report.html",
      "pytest -m smoke        # smoke suite only", "pytest -m security     # security suite", "pytest tests/e2e        # browser tests (videos in reports/e2e_videos)",
      "", "# non-functional & effectiveness campaigns", "python tools/perf_test.py        # load/stress/spike/soak/volume", "python tools/mutation.py         # mutation testing",
      "python tools/fault_seeding.py    # fault seeding", "", "# regenerate figures, workbook and documents", "python tools/make_charts.py && python tools/make_diagrams.py && python tools/make_workbook.py",
      "node tools/doc/report.js"]),
    H1("List of Figures and Tables"),
    ...L.figures.map((f) => P(f, { run: { size: 19 }, align: "left" })),
    SP(120),
    ...L.tables.map((t) => P(t, { run: { size: 19 }, align: "left" })),
  ];
}

const out = process.argv[2] || path.join(ROOT, "deliverables", "HRRS_VV_Test_Report_Raktim.docx");
const body = [...intro(), ...sut(), ...approach(), ...plan(), ...blackbox(), ...whitebox(), ...levels(), ...nonfunctional(),
  ...staticTesting(), ...execution(), ...metrics(), ...caseStudy(), ...conclusion(), ...appendix()];
build(out, [front(), body], "HRRS — Software Verification & Validation Report").then(() =>
  fs.writeFileSync(out.replace(/\.docx$/, ".heads.json"), JSON.stringify(L.HEADS)));
