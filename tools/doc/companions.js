// Companion documents: Test Summary Report (IEEE 829), Case Studies, Cycle-Test prep pack (problems + viva).
const fs = require("fs");
const path = require("path");
const L = require("./lib");
const { J, ROOT, P, H1, H1n, H2, H3, SP, bullets, eq, callout, code, table, fig, tcap, cover, build, C } = L;

const results = J("reports/results.json");
const defects = J("reports/defects_found.json");
const defectsManual = fs.existsSync(path.join(ROOT, "reports/defects_manual.json")) ? J("reports/defects_manual.json") : [];
const reqs = J("docs/requirements.json");
const ms = J("docs/manual_and_static.json");
const mut = J("reports/mutation.json");
const seed = J("reports/fault_seeding.json");
const perf = J("reports/perf.json"), perf0 = J("reports/perf_before_tuning.json");
const cov = J("reports/coverage.json").totals, cov0 = J("reports/coverage_iter1.json").totals;
const N = results.length, PASS = results.filter((r) => r.status === "PASS").length, SKIP = N - PASS;
const OUT = path.join(ROOT, "deliverables");
const which = process.argv[2] || "all";

// ============================================================================ Test Summary Report
async function tsr() {
  const lv = (x) => results.filter((r) => r.level === x);
  const body = [
    H1n("1. Test summary report identifier"),
    P("HRRS-TSR-1.0 · relates to test plan HRRS-TP-1.0 · system HRRS v1.0 (build tested on " + results[0].executed_at.slice(0, 10) + ")."),
    H2("2. Summary"),
    P(`All planned automated testing for HRRS v1.0 was completed. **${N} test cases** were executed across five levels: **${PASS} passed, ${SKIP} skipped, 0 failed** (pytest reports 558 passed / 2 skipped because one Gherkin outline runs three examples and four self-checks carry no case ID). Five defects were found by automated testing and all are fixed and regression-tested; manual testing found five more in packaging and documentation (DEF-006…010), all fixed and retested. All exit criteria in the test plan are met; **the team recommends release**, with the two open items listed under Variances.`),
    H2("3. Variances"),
    ...bullets([
      "**Cross-browser (NFR-COMP-02):** Firefox and WebKit cases (TC-E2E-011/012) were skipped — the lab sandbox could not download those browsers. Mitigated with Chromium device emulation; to be executed on team machines.",
      `**Manual cases:** of ${ms.manual_cases.length} manual cases, ${ms.manual_cases.filter((m) => (m.status || "").startsWith("PASS")).length} passed (localisation ×2, installation, documentation on retest), ${ms.manual_cases.filter((m) => m.status === "IN PROGRESS").length} are in progress (heuristic evaluation: evaluator 2 pending; screen reader: automated proxy passed, real NVDA/VoiceOver pass pending) and ${ms.manual_cases.filter((m) => m.status === "NOT RUN").length} are not yet run because they need real participants or devices (usability study, beta, Firefox on Windows, Safari on iPhone). Kits for these are in the Manual Test Execution Kit.`,
      "**Scope change:** coverage-guided (10) and mutation-guided (26) cases were added during execution in response to measured gaps — an intended feedback loop, not a plan deviation in effort.",
    ]),
    H2("4. Comprehensiveness assessment"),
    table(["Criterion (from test plan)", "Target", "Achieved", "Status"], [
      ["P1 cases passing", "100 %", "100 %", "Met"],
      ["Statement coverage", "≥ 95 %", `${cov.percent_statements_covered.toFixed(0)} % (${cov.covered_lines}/${cov.num_statements})`, "Met"],
      ["Branch coverage", "≥ 90 %", `${cov.percent_branches_covered.toFixed(1)} % (${cov.covered_branches}/${cov.num_branches})`, "Met"],
      ["Mutation score", "≥ 90 %", "100 % (267/267 non-equivalent)", "Met"],
      ["Requirements with executed tests", "100 %", `${reqs.length}/${reqs.length}`, "Met"],
      ["Load-test p95 at 25 users", "< 300 ms", `${perf.load.p95_ms} ms`, "Met"],
      ["Error rate under load", "< 1 %", `${perf.load.error_rate_pct} %`, "Met"],
      ["Open Critical/Major defects", "0", "0", "Met"],
      ["WCAG 2.1 AA serious/critical violations", "0", "0", "Met"],
    ], [3, 1.4, 2.6, 1.2], { center: [3] }),
    tcap("Exit criteria assessment"),
    H2("5. Summary of results"),
    table(["Level", "Executed", "Passed", "Skipped", "Failed"], ["Unit", "Integration", "System", "System (E2E UI)", "Acceptance (UAT)"].map((x) => {
      const rs = lv(x);
      return [x, String(rs.length), String(rs.filter((r) => r.status === "PASS").length), String(rs.filter((r) => r.status === "SKIPPED").length), "0"];
    }), [2.6, 1.2, 1.2, 1.2, 1.2], { center: [1, 2, 3, 4] }),
    tcap("Results by level"),
    table(["ID", "Title", "Severity", "Found by", "Status"], defects.concat(defectsManual).map((d) => [d.id, d.title, d.severity, d.technique, d.status]), [0.9, 4.2, 0.9, 2, 1.4], { size: 17 }),
    tcap("Defects"),
    H2("6. Evaluation"),
    P(`Risk-weighted, the product is in good condition. The highest-exposure risks (overbooking, wrong price/tax, double charge, unauthorised access) each have dedicated tests at two or more levels and all pass, including a 20-thread race repeated 25 times. Suite effectiveness is evidenced independently of coverage: every non-equivalent mutant is killed and all 12 seeded faults are detected (Mills' estimate of latent product defects ≈ ${seed.summary.estimated_latent}). The residual risk is concentrated in untested browser engines and in usability, which only real users can validate.`),
    H2("7. Summary of activities"),
    table(["Activity", "Output"], [
      ["Requirements review", "7 findings (RV-01…07), all resolved"], ["Static analysis & inspection", "Ruff, Bandit, Radon; 8 inspection items (CI-01…08)"],
      ["Test design", `${N} automated + ${ms.manual_cases.length} manual cases, ${ms.exploratory_charters.length} exploratory charters`],
      ["Execution", "2 full runs (identical), 25× concurrency repeat, E2E video + screenshots"],
      ["Performance campaign", "baseline, load, stress, spike, soak, volume — before and after tuning"],
      ["Mutation testing", "270 mutants, 3 iterations"], ["Fault seeding", "12 seeded faults, 2 revisions"],
      ["Manual testing", `${ms.manual_cases.filter((m) => m.status && m.status !== "NOT RUN").length} of ${ms.manual_cases.length} manual cases executed (fully or in part); results in the workbook`],
      ["Defect management", `${defects.length + defectsManual.length} defects logged (${defects.length} product/test-suite, ${defectsManual.length} packaging/docs), fixed, re-tested, regression-protected`]], [2.6, 5.9]),
    tcap("Activities"),
    H2("8. Approvals"),
    table(["Role", "Name", "Signature", "Date"], [["Test lead", "Raktim Chandra (RA2311033010038)", "", ""], ["Faculty", "Mr. Kaviyaraj R.", "", ""]], [1.6, 3.4, 2, 1.4], { size: 19 }),
  ];
  return build(path.join(OUT, "HRRS_Test_Summary_Report_IEEE829_Raktim.docx"),
    [[...cover("Test Summary Report", "IEEE 829-2008 test summary for HRRS v1.0", "Test Summary Report"), ], body], "HRRS — Test Summary Report (IEEE 829)");
}

// ============================================================================ Case studies
async function cases() {
  const story = (title, rows) => [H2(title), table(["", ""], rows, [1.6, 6.9], { size: 19, keyCol: true })];
  const body = [
    H1n("About these case studies"),
    P("Each case study follows one real finding from this campaign from the moment a technique raised it to the regression test that now guards it. Nothing here is hypothetical: IDs refer to the test catalogue, the defect log and the run artefacts in the submission."),
    ...story("Case Study 1 — A valid name the system refused (ECP → DEF-001)", [
      ["Context", "FR-01 allows letters plus the separators space, dot, apostrophe and hyphen in guest names."],
      ["Technique", "Equivalence Class Partitioning. The designer listed the valid classes explicitly — including **V4: an initial followed by a space** (“R. Chandra”) — instead of testing only “typical” names."],
      ["What happened", "TC-REG-ECP-025 failed: the validator returned NAME_CHARS. The regular expression allowed exactly one separator between letter groups, so the two-character sequence “. ” broke it."],
      ["Why other tests missed it", "Every other valid name in BVA and E2E data had single separators. Random data would rarely produce this exact shape."],
      ["Fix & protection", "Pattern extended to accept “. ”. API-level regression test TC-REG-RGN-001 registers “R. Chandra” end-to-end."],
      ["Lesson", "ECP is not just “one valid and one invalid value”: enumerating *every* valid class is where specification defects surface."]]),
    ...story("Case Study 2 — An SLA met on average, missed where it matters (load test → DEF-004)", [
      ["Context", "NFR-PERF-01: p95 < 300 ms at 25 concurrent users."],
      ["Technique", "Load testing with a realistic mixed workload, reporting p95 **per endpoint**, not just overall."],
      ["What happened", `Overall p95 was ${perf0.load.p95_ms} ms — a pass. But book + pay was **${perf0.load.by_endpoint_p95.book} ms**, more than twice the SLA. The stress curve put the overall SLA knee at only ~25 users.`],
      ["Diagnosis", "Bookings are the only write-heavy path. SQLite's default rollback journal fsyncs every commit and blocks readers during writes; the booking path commits twice (hold + payment)."],
      ["Fix", "WAL journaling with synchronous=NORMAL for file databases (one change in db.py)."],
      ["Evidence", `Re-run with the identical seeded workload: book p95 **${perf.load.by_endpoint_p95.book} ms (−${Math.round(100 * (1 - perf.load.by_endpoint_p95.book / perf0.load.by_endpoint_p95.book))} %)**, overall p95 ${perf.load.p95_ms} ms, throughput ${perf0.load.throughput_rps} → ${perf.load.throughput_rps} req/s, SLA knee moved from ~25 to ~50 users, still 0 % errors.`],
      ["Lesson", "Averages and aggregates hide the slowest, most valuable transaction. Always break performance results down by operation."]]),
    ...fig("load_endpoints.png", "Per-endpoint p95 before and after the fix", 5.4),
    ...story("Case Study 3 — Testing the tests (fault seeding → DEF-005)", [
      ["Context", "NFR-SEC-04 requires that server text is never interpreted as HTML in the browser. TC-E2E-003 was written to prove it."],
      ["Technique", "Fault seeding: 12 realistic bugs were injected one at a time and the **full** suite (unit → E2E) run against each."],
      ["What happened", "Seeded fault SF-11 changed `textContent` to `innerHTML` — a real DOM-XSS hole. **No test failed.** The XSS test typed a payload into the login form, but the login error is a constant string that never echoes input, so the vulnerable code path could not show a difference."],
      ["Fix", "TC-E2E-003 (Rev B) now attacks the promo-code field, whose error message reflects the input back. It asserts that no <img> element is created, no script runs and the payload is displayed literally."],
      ["Evidence", "Re-running SF-11: detected. Seeding detection 11/12 → 12/12; Mills' estimate of native defects 4.36 → 4.0."],
      ["Lesson", "A test that cannot fail proves nothing. Coverage would not have caught this (the line ran); only injecting the fault did."]]),
    ...story("Case Study 4 — 97.8 % coverage, 38 undetected faults (mutation testing)", [
      ["Context", "After the first full run, coverage was already 97.8 %."],
      ["Technique", "Mutation testing with our own AST engine: 270 mutants over 6 operators in the domain layer."],
      ["What happened", "Iteration 1 killed 232 (85.9 %). All 23 mutants of the metrics module survived — occupancy, ADR and RevPAR were only checked at integration level, so a unit-level change to them went unnoticed by the unit suite."],
      ["Other gaps exposed", "e-mail length 254/255; a nightly tariff of exactly ₹0; discounts that sum to *exactly* the 30 % cap (is it “capped”?); boolean values used as head-counts; immutability of refund decisions; a hotel with exactly one room."],
      ["Fix", "26 mutation-guided tests in two iterations: 85.9 % → 97.8 % → 98.9 % raw. The 3 survivors were proven equivalent (e.g., `d > 9` vs `d >= 9` in Luhn, where a doubled digit is always even)."],
      ["Lesson", "Coverage measures what ran; mutation score measures what was checked. Equivalent mutants must be argued, not assumed."]]),
    ...fig("mutation_iterations.png", "Mutation score by iteration", 5.2),
    ...story("Case Study 5 — Looking at a screenshot (exploratory → DEF-002, DEF-003)", [
      ["Context", "All E2E assertions passed on the first run."],
      ["Technique", "Exploratory session XS-02: a 30-minute visual review of the screenshots recorded by the passing E2E test."],
      ["What happened", "Two defects no assertion checked: the booking form's number inputs overflowed their grid cells (the Extra-beds box spilled outside the card) and a zero discount was shown as “₹-0.00”."],
      ["Fix", "CSS `width:100%; min-width:0` on inputs; discount displayed as “− ₹x” only when positive."],
      ["Protection", "TC-E2E-014 measures every field's bounding box against its card; TC-E2E-015 asserts “₹0.00”. Both were proven to **fail on the unfixed code** before being accepted as regression tests."],
      ["Lesson", "Automated checks verify what someone thought to check. Human exploration finds what nobody did — then automation keeps it fixed."]]),
    H1("Cross-case observations"),
    table(["Technique", "Found", "Would other techniques have found it?"], [
      ["ECP (valid-class enumeration)", "DEF-001", "Unlikely — BVA and random data used single-separator names"],
      ["Load testing per endpoint", "DEF-004", "No — functional tests pass regardless of latency"],
      ["Fault seeding", "DEF-005 (test defect)", "No — coverage and mutation (unit-level) do not exercise the browser"],
      ["Mutation testing", "26 missing tests", "Partly — coverage-guided tests found 10 different gaps"],
      ["Exploratory / visual", "DEF-002, DEF-003", "No — no assertion described layout or sign formatting"]], [2.4, 1.6, 4.5]),
    tcap("No single technique would have found all five defects"),
  ];
  return build(path.join(OUT, "HRRS_Case_Studies_Raktim.docx"),
    [cover("Case Studies", "Five findings from the HRRS V&V campaign, traced end to end", "Case Study Document"), body], "HRRS — Case Studies");
}

// ============================================================================ Cycle-test prep: problems + viva
async function prep() {
  const prob = (n, title, q, steps, ans) => [H2(`Problem ${n} — ${title}`), P("**Question.** " + q), ...steps.map((s) => P(s)), callout("Answer.", ans, L.C.aqua, "1BAF7A")];
  const body = [
    H1n("How to use this pack"),
    P("FT-3 tests black-box design (BVA, ECP, cause-effect graphs, decision tables), white-box coverage problems and test-level design. Each problem below uses HRRS so the numbers can be checked against the real code and tests. Solutions were verified by running them (coverage figures with coverage.py)."),
    H1("Part A — Worked problems"),
    ...prob(1, "How many BVA test cases?", "A booking function takes age (18–120), nights (1–30) and rooms (1–5). How many test cases for normal, robust, worst-case and robust worst-case BVA?",
      ["n = 3 independent variables."], "Normal 4n + 1 = **13**; robust 6n + 1 = **19**; worst-case 5ⁿ = 5³ = **125**; robust worst-case 7ⁿ = 7³ = **343**."),
    ...prob(2, "BVA values", "Write the robust BVA values for stay length (1–30 nights).", ["min−1, min, min+1, nominal, max−1, max, max+1."],
      "**0, 1, 2, 15, 29, 30, 31** — 0 and 31 must be rejected (STAY_TOO_SHORT / STAY_TOO_LONG). See TC-SRCH-BVA-001…007."),
    ...prob(3, "Equivalence classes", "Identify equivalence classes for the rooms-per-booking field (valid 1–5, integer).",
      ["Partition on validity and on type."], "Valid **V1: 1 ≤ r ≤ 5**. Invalid **I1: r < 1**, **I2: r > 5**, **I3: non-integer** (2.0, “two”), **I4: boolean** (True). Minimum tests = 1 + 4 = **5**, e.g. 3, 0, 6, 2.0, True."),
    ...prob(4, "Decision table size", "The refund rule has conditions: hotel-initiated (Y/N), refundable (Y/N), days band (≥7, 2–6, 0–1, <0), PLATINUM (Y/N). How many rules in the full table, and why does DT-1 have only 8?",
      ["Full table = 2 × 2 × 4 × 2."], "**32** rules. Don't-care entries collapse them: when hotel-initiated = Y nothing else matters (16 → 1); non-refundable ignores band and tier; tier only matters in the 2–6 and 0–1 bands. Result: **8 rules**."),
    ...prob(5, "Cause-effect to decision table", "E1 = C1 ∧ C2 ∧ C4 and E2 = C1 ∨ (C2 ∧ C3). For C1 = F, C2 = T, C3 = T, C4 = T give E1 and E2.",
      ["Evaluate each node."], "E1 = F ∧ T ∧ T = **F**; E2 = F ∨ (T ∧ T) = **T** → free breakfast, no upgrade (rule 9 in DT-2, TC-BEN-DT-009)."),
    ...prob(6, "Cyclomatic complexity", "Compute V(G) for late_checkout_fee(): `if rate < 0 … raise; if t ≤ 12:00 pct = 0 elif t ≤ 15:00 pct = 25 elif t ≤ 18:00 pct = 50 else pct = 100; return`.",
      ["Count the predicate nodes: rate < 0, ≤ 12:00, ≤ 15:00, ≤ 18:00 = 4."], "V(G) = P + 1 = **5**. Five basis paths: error, 0 %, 25 %, 50 %, 100 % (TC-WB-DF-001…005)."),
    ...prob(7, "V(G) from a graph", "A CFG has 17 nodes, 23 edges and one connected component. Find V(G).", [], "V(G) = E − N + 2P = 23 − 17 + 2 = **8** (refund_decision, Figure 9 in the report)."),
    ...prob(8, "Statement and branch coverage %", "gst_rate has 8 executable statements and 3 decisions (6 branches): `tariff<0`, `tariff<1000`, `tariff≤7500`. Compute coverage for test sets {500}, {500, 12000}, {500, 12000, 5000, −5}.",
      ["{500}: executes assign, test 1 (F), test 2 (T), return 0 → 4 statements; branches D1-F, D2-T.", "{500, 12000}: adds test 3 (F) and return 18 %.", "Adding 5000 and −5 covers return 5 % and the raise."],
      "{500}: statements **4/8 = 50 %**, branches **2/6 = 33.3 %**. {500, 12000}: **6/8 = 75 %**, **4/6 = 66.7 %**. All four: **100 % / 100 %** (verified with coverage.py)."),
    ...prob(9, "MC/DC minimum set", "Give a minimum MC/DC test set for D = (A ∧ B) ∨ C.",
      ["N = 3 conditions → at least N + 1 = 4 tests. Each condition needs an independence pair (two tests differing only in that condition, with different outcomes)."],
      "{ (T,T,F)→T, (F,T,F)→F, (T,F,F)→F, (F,T,T)→T }. Pairs: A = tests 1–2, B = tests 1–3, C = tests 2–4. **4 tests**."),
    ...prob(10, "Mutation score", "270 mutants, 232 killed, 3 proven equivalent. Compute the mutation score.", [], "MS = 232 ÷ (270 − 3) = 232 ÷ 267 = **86.9 %** (our iteration-1 result before mutation-guided tests)."),
    ...prob(11, "Fault seeding (Mills)", "20 faults seeded; testing finds 16 seeded and 12 native faults. Estimate total native faults and latent faults.", [],
      "N̂ = n × S ÷ s = 12 × 20 ÷ 16 = **15**; latent ≈ 15 − 12 = **3**."),
    ...prob(12, "Pairwise reduction", "Three parameters each with 3 values. Exhaustive vs. pairwise test count?", [],
      "Exhaustive 3³ = **27**; pairwise needs only **9** (an L9 orthogonal array) because each pair of parameters has 3 × 3 = 9 value pairs and each test covers 3 pairs."),
    ...prob(13, "Defect metrics", "4 defects found before release, 0 after; app is 1,023 SLOC. Compute DRE and defect density.", [],
      "DRE = 4 ÷ (4 + 0) = **100 %**; density = 4 ÷ 1.023 KLOC = **3.91 defects/KLOC**."),
    ...prob(14, "Little's law", `A load test sustains ${perf.load.throughput_rps} req/s with mean response ${perf.load.mean_ms} ms. How many requests are in the server at once?`, [],
      `L = λW = ${perf.load.throughput_rps} × ${(perf.load.mean_ms / 1000).toFixed(4)} ≈ **${(perf.load.throughput_rps * perf.load.mean_ms / 1000).toFixed(1)}** requests.`),
    ...prob(15, "Designing tests per level", "For “guest cancels a paid booking 3 days before arrival”, give one test at each level.", [],
      "**Unit:** refund_decision(True, 3) → 50 %, fee 200 (TC-CAN-BVA-005). **Integration:** service + DB: refund = 0.5 × total − 200 and status CANCELLED (TC-INT-012). **System:** POST /api/bookings/{id}/cancel returns rule R4 (TC-SYS-*). **Acceptance:** Gherkin “cancels 4 days before → 50 % under R4” (TC-UAT-003)."),
    H1("Part B — Viva questions with model answers"),
    table(["#", "Question", "Model answer (with HRRS evidence)"], [
      ["1", "Verification vs. validation?", "Verification: built right (specs) — reviews, unit/integration, coverage. Validation: right product (needs) — system, UAT."],
      ["2", "Why test at boundaries?", "Off-by-one and wrong relational operators cluster there; e.g. GST at exactly ₹7,500 must be 5 %, not 18 % (SF-03 caught by TC-PRC-BVA-008)."],
      ["3", "Weak vs. strong ECP?", "Weak: each class covered at least once; strong: every combination of classes. Invalid classes one at a time."],
      ["4", "When is a decision table better than ECP?", "When outputs depend on combinations of conditions (refund depends on 4 conditions together)."],
      ["5", "What does a cause-effect graph add?", "It captures logical relations (∧, ∨, ¬) and constraints, and lets you derive a reduced set by back-tracking effects."],
      ["6", "Statement vs. branch coverage?", "Branch subsumes statement; an if without else can reach 100 % statements while never taking the false branch."],
      ["7", "What is MC/DC and where is it mandated?", "Every condition independently affects the decision; required for the most critical avionics software (DO-178C level A)."],
      ["8", "Three ways to compute V(G)?", "E − N + 2P; predicates + 1; regions + 1."],
      ["9", "Why did radon report 9 for refund_decision?", "It counts Boolean operators (`or`) as decisions — extended complexity."],
      ["10", "What is a du-path?", "A path from a variable's definition to its use with no redefinition in between."],
      ["11", "Equivalent mutant?", "A mutant that behaves identically for all inputs; it must be excluded from the score (3 in HRRS)."],
      ["12", "Stub vs. driver?", "Stub replaces a called component (payment gateway); driver calls the unit under test (pytest)."],
      ["13", "Top-down vs. bottom-up integration?", "Top-down needs stubs, finds design faults early; bottom-up needs drivers, tests foundations first. HRRS: bottom-up with a gateway stub."],
      ["14", "Smoke vs. sanity?", "Smoke: broad, shallow build check (3 SMK cases). Sanity: narrow check of a fix (regression tests per defect)."],
      ["15", "Load vs. stress vs. soak vs. spike?", "Expected load vs. beyond capacity vs. long duration vs. sudden burst — all four run on HRRS."],
      ["16", "What is a test oracle?", "The mechanism that decides the expected result; HRRS pairwise tests use an independent re-implementation of the pricing formula."],
      ["17", "Why property-based testing?", "It checks invariants on hundreds of generated inputs and shrinks failures to a minimal example."],
      ["18", "What is IDOR and how was it tested?", "Accessing another user's object by changing an ID; guest B gets 403 for guest A's booking (TC-SEC-005)."],
      ["19", "Why idempotency keys?", "So a retried payment request cannot charge twice (TC-INT-007)."],
      ["20", "What did fault seeding teach you?", "Our XSS test could not fail; we strengthened it (DEF-005)."],
      ["21", "What is an RTM and why bi-directional?", "Maps requirements ↔ tests; forward shows coverage, backward shows every test has a reason."],
      ["22", "Entry and exit criteria?", "Conditions to start and to finish a level — e.g. unit exit: all pass, coverage ≥ 95 %, mutation ≥ 90 %."],
      ["23", "Severity vs. priority?", "Severity = impact on the system; priority = urgency to fix. DEF-004 was Major/P2."],
      ["24", "How do you know a regression test is real?", "Revert the fix and watch it fail — done for TC-E2E-014/015."],
      ["25", "Pesticide paradox?", "Repeating the same tests finds fewer new bugs; we added exploratory, mutation and seeding to escape it."],
    ], [0.4, 2.6, 5.5], { size: 17 }),
    tcap("Viva preparation"),
  ];
  return build(path.join(OUT, "HRRS_CycleTest3_Prep_Problems_and_Viva_Raktim.docx"),
    [cover("Cycle Test 3 Prep Pack", "Worked FT-3 problems on BVA, ECP, decision tables, CEG and code coverage + viva answers", "Study Companion"), body], "HRRS — FT-3 Prep Pack");
}


// ============================================================================ Manual test execution kit
async function kit() {
  const mc = ms.manual_cases, byId = Object.fromEntries(mc.map((m) => [m.id, m]));
  const blank = (cols, n) => Array.from({ length: n }, () => cols.map(() => ""));
  const rec = (id) => { const m = byId[id];
    return [H2(`${m.id} — ${m.title}`), table(["Field", "Record"], [["Requirement / type", `${m.requirement} · ${m.type}`], ["Steps", m.steps], ["Expected", m.expected],
      ["Tester", m.tester], ["Environment", m.environment], ["Actual result", m.actual], ["Status", m.status], ["Date", m.date || "—"], ["Evidence", m.evidence || "—"]], [1.7, 6.8], { size: 17 })]; };
  const SUS = ["I think that I would like to use this system frequently.", "I found the system unnecessarily complex.", "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to be able to use this system.", "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.", "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.", "I felt very confident using the system.", "I needed to learn a lot of things before I could get going with this system."];
  const journey = [["1", "Open the app; choose Register", "Registration form shown"], ["2", "Register: your name, a new e-mail, 10-digit mobile, age 21, password Hotel@2026", "“Account created”"],
    ["3", "Sign in with the same e-mail and password", "Header: “Signed in as <name>”"], ["4", "Check-in 2 Nov 2026, check-out 5 Nov 2026 → Search availability", "Four room cards; Deluxe shows a price for 3 nights"],
    ["5", "Deluxe → Select; Adults 2 → Get price", "Total ₹12,600.00 (subtotal ₹12,000.00 + GST ₹600.00)"], ["6", "Reserve", "“Rooms held”; payment panel shows the amount"],
    ["7", "Card 4111 1111 1111 1111, month 12, year 2028, CVV 123 → Pay now", "Status CONFIRMED in My bookings"], ["8", "Cancel the booking", "Status CANCELLED; full refund (rule R3, ≥ 7 days before check-in)"]];
  const body = [
    H1n("How to use this kit"),
    P("This kit records the execution of HRRS's ten manual test cases. Cases that could be executed with tools have their record filled in below, with the evidence. Cases that need real people or devices have **not** been simulated: for each there is a ready-to-run kit. When a case is executed, write the result in the yellow cells of the workbook's *Manual & Exploratory* sheet (or in docs/manual_and_static.json) and attach the evidence."),
    table(["ID", "Type", "Status", "What is left"], mc.map((m) => [m.id, m.type, m.status, m.status.startsWith("PASS") ? "—" : m.status === "IN PROGRESS" ? (m.id.includes("USE") ? "Evaluator 2 scores the heuristics" : "Real NVDA / VoiceOver pass") : "Execute with the kit below"]),
      [1.6, 1.5, 1.3, 4.1], { size: 17 }),
    tcap("Manual case status"),
    callout("Start the app for testers.", "pip install -r requirements.txt, then uvicorn app.main:app --host 0.0.0.0 --port 8000. On the same Wi-Fi, phones and other laptops open http://<your-laptop-IP>:8000. Admin: admin@hrrs.test / Admin@123."),
    H1("Part A — Execution records"),
    ...["TC-MAN-L10N-001", "TC-MAN-L10N-002", "TC-MAN-INST-001", "TC-MAN-DOC-001", "TC-MAN-USE-001", "TC-MAN-A11Y-001"].flatMap(rec),
    H3("TC-MAN-INST-001 — console record"),
    ...code(["$ python -m venv venv && . venv/bin/activate", "$ pip install -r requirements.txt          # finished at 0:21", "$ uvicorn app.main:app --port 8000 &",
      "$ curl -s http://127.0.0.1:8000/api/health   # {\"status\":\"ok\", …} at 0:26  (limit 5:00)", "$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/docs   # 200"]),
    H3("TC-MAN-DOC-001 — defects raised"),
    table(["ID", "Defect", "Severity", "Status"], defectsManual.map((d) => [d.id, d.title, d.severity, d.status]), [0.9, 5.4, 1, 1.2], { size: 17 }),
    tcap("Defects found by following the README on a clean machine"),
    H1("Part B — Kits for the cases still to run"),
    H2("USE-001 — evaluator 2 scoring sheet"),
    P("Score independently **before** reading evaluator 1's notes. Severity: 0 not a problem · 1 cosmetic · 2 minor · 3 major (fix before release) · 4 catastrophe. The case fails if either evaluator gives any heuristic 3 or more."),
    table(["Heuristic", "Severity (0–4)", "Where / why"], byId["TC-MAN-USE-001"].heuristic_scores.map(([h]) => [h, "", ""]), [3, 1.3, 4.2], { size: 17 }),
    tcap("Evaluator 2 — Nielsen heuristic scores"),
    H2("USE-002 — first-time-user study (5 participants)"),
    P("**Recruit** five people who have never seen HRRS (not team members). **Say:** “We are testing the website, not you. Please think aloud as you go. I can't help during the tasks.” Record screen and voice with consent. Start a stopwatch when the participant starts task 1."),
    table(["Task", "Instruction to read out", "Success means"], [["T1", "Create an account and sign in.", "Signed in, no help"], ["T2", "Book a Deluxe room for two adults from 2 to 5 November and pay with the test card 4111 1111 1111 1111.", "Booking CONFIRMED"],
      ["T3", "You've changed your plans. Cancel that booking.", "Booking CANCELLED"]], [0.6, 5.4, 2.5], { size: 17 }),
    tcap("Task script"),
    table(["P#", "T1 ✓/✗", "T2 ✓/✗", "T3 ✓/✗", "Time (min)", "Errors", "SUS", "Notes"], blank([1, 2, 3, 4, 5, 6, 7, 8], 5).map((r, i) => [`P${i + 1}`, ...r.slice(1)]), [0.5, 0.8, 0.8, 0.8, 1, 0.9, 0.7, 3], { size: 17 }),
    tcap("Recording sheet — pass if ≥ 4/5 complete all tasks, median time < 3 min and mean SUS ≥ 68"),
    H3("System Usability Scale (give after the tasks)"),
    table(["#", "Statement", "1 Strongly disagree … 5 Strongly agree"], SUS.map((q, i) => [String(i + 1), q, "1   2   3   4   5"]), [0.4, 5.6, 2.5], { size: 17 }),
    tcap("SUS questionnaire (Brooke, 1986)"),
    eq("SUS = 2.5 × [ Σ (odd item − 1) + Σ (5 − even item) ]   → 0 … 100; 68 is the average"),
    H2("COMP-001 / COMP-002 — Firefox on Windows 11 and Safari on iPhone"),
    P("Repeat the automated TC-E2E-001 journey by hand on each device. If 2 Nov 2026 has passed, use any three nights at least a week ahead and compare the price with Chromium for the same dates."),
    table(["Step", "Action", "Expected", "Firefox", "Safari"], journey.map((r) => [...r, "", ""]), [0.5, 3.3, 2.7, 1, 1], { size: 16 }),
    tcap("Cross-browser checklist (✓ / ✗ + note)"),
    ...bullets(["**Safari only:** tapping the card-number and CVV fields opens the numeric keypad; the page has no sideways scrolling at phone width; the date fields open the iOS date wheel.",
      "**Firefox only:** date fields show Firefox's own picker; focus rings are visible when tabbing.", "Take a screenshot at steps 5 and 8 on each device as evidence."]),
    H2("A11Y-001 — screen-reader pass"),
    table(["Check", "NVDA (Windows, Firefox/Chrome)", "VoiceOver (Mac: ⌘F5 · iPhone: Settings → Accessibility)", "Pass?"], [
      ["Headings list makes sense", "NVDA+F7 → Headings", "VO+U → Headings", ""], ["Every field announces its label", "Tab through the forms", "VO+→ through the forms", ""],
      ["Sign-in tabs announced as tabs, with selected state", "Tab to “Sign in”", "VO on the tab", ""], ["Wrong password message is read out without moving focus", "Submit a wrong password", "Same", ""],
      ["Price quote is read out after Get price", "Activate Get price", "Same", ""], ["Booking status and Cancel button are understandable in My bookings", "Table navigation Ctrl+Alt+arrows", "VO+arrows in table", ""]],
      [2.6, 2.1, 2.6, 0.7], { size: 16 }),
    tcap("Screen-reader script — expected result: every control announced with its label and every status message announced"),
    H2("BETA-001 — beta test (10 classmates, 3 days)"),
    callout("Invitation (copy and send).", "Hi! We built a hotel booking website for our Software V&V project and need 10 beta testers for 3 days. Please make, change and cancel a few bookings (use test card 4111 1111 1111 1111 — no real money) and fill in the 2-minute form at the end. Report anything odd using the bug template. Link: http://<host>:8000. Thank you!"),
    table(["#", "Feedback question", "Answer"], [["1", "Overall, how satisfied are you with the booking website? (1–5)", ""], ["2", "How easy was it to find and book a room? (1–5)", ""],
      ["3", "Did anything not work as you expected? Describe it.", ""], ["4", "Was anything confusing?", ""], ["5", "Which device and browser did you use?", ""], ["6", "Would you use this to book a real stay? Why / why not?", ""]], [0.4, 5.2, 2.9], { size: 17 }),
    tcap("Beta feedback form — pass if no P1 defect is reported and mean satisfaction ≥ 4/5"),
    table(["Field", "Fill in"], [["Reporter / date", ""], ["Device and browser", ""], ["What you did (steps)", ""], ["What you expected", ""], ["What happened", ""], ["Screenshot attached?", ""], ["How bad? (blocks booking / annoying / cosmetic)", ""]], [3, 5.5], { size: 17 }),
    tcap("Bug report template for beta testers"),
  ];
  return build(path.join(OUT, "HRRS_Manual_Test_Execution_Kit_Raktim.docx"),
    [cover("Manual Test Execution Kit", "Execution records for the ten manual test cases, and ready-to-run kits for the ones that need people or devices", "Test Execution Record"), body], "HRRS — Manual Test Execution Kit");
}

(async () => {
  if (which === "all" || which === "tsr") await tsr();
  if (which === "all" || which === "cases") await cases();
  if (which === "all" || which === "prep") await prep();
  if (which === "all" || which === "kit") await kit();
})();
