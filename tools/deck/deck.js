// HRRS V&V presentation (PowerPoint, structured deck: theme + layouts + sections + speaker notes).
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("./theme");

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = (f) => path.join(ROOT, "docs", "figures", f);
const SHOT = (f) => path.join(ROOT, "reports", "screenshots", f);
const J = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const OUT = path.join(ROOT, "deliverables", "HRRS_VV_Presentation_Raktim.pptx");

const results = J("reports/results.json"), defects = J("reports/defects_found.json"), reqs = J("docs/requirements.json");
const mut = J("reports/mutation.json"), seed = J("reports/fault_seeding.json"), perf = J("reports/perf.json"), perf0 = J("reports/perf_before_tuning.json");
const cov = J("reports/coverage.json"), cov0 = J("reports/coverage_iter1.json"), axe = J("reports/a11y_axe.json"), ms = J("docs/manual_and_static.json");
const N = results.length, PASS = results.filter((r) => r.status === "PASS").length, SKIP = N - PASS;
const lvl = (x) => results.filter((r) => r.level === x).length;

const THEME = { name: "HRRS Marina", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "14213D", lt1: "FFFFFF", dk2: "0F6E78", lt2: "EEF4F6", accent1: "0F6E78", accent2: "E3A53A", accent3: "2A78D6",
    accent4: "E34948", accent5: "1BAF7A", accent6: "4A3AA7", hlink: "2A78D6", folHlink: "4A3AA7" } };
const HEX = { navy: "14213D", teal: "0F6E78", gold: "E3A53A", blue: "2A78D6", red: "E34948", green: "1BAF7A", violet: "4A3AA7",
  ink: "1B1B1B", ink2: "52514E", grid: "E3E1DA", pale: "EEF4F6", paleGold: "FBF1DE", paleRed: "FBE6E6", paleGreen: "E2F5EC", white: "FFFFFF" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Raktim Chandra — SRMIST";
pres.company = "SRM Institute of Science and Technology";
pres.title = "HRRS — Software Verification and Validation";
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({ title: "TITLE", background: { color: HEX.navy }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 11.7, h: 1.6, fontFace: "Cambria", fontSize: 50, bold: true, color: C.background1, valign: "bottom", align: "left" }, text: "" } },
  { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.75, w: 11.7, h: 1.0, fontFace: "Calibri", fontSize: 22, color: "C9D6E8", valign: "top", align: "left" }, text: "" } }] });
pres.defineSlideMaster({ title: "SECTION", background: { color: HEX.teal }, objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.9, w: 11.7, h: 1.2, fontFace: "Cambria", fontSize: 44, bold: true, color: C.background1, valign: "middle", align: "left" }, text: "" } },
  { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.15, w: 11.7, h: 0.9, fontFace: "Calibri", fontSize: 20, color: "D7ECEE", valign: "top", align: "left" }, text: "" } }],
  slideNumber: { x: 12.3, y: 6.95, w: 0.6, h: 0.3, fontFace: "Calibri", fontSize: 10, color: "D7ECEE", align: "right" } });
pres.defineSlideMaster({ title: "CONTENT", background: { color: HEX.white }, margin: [0.5, 0.6, 0.6, 0.6], objects: [
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.32, w: 12.1, h: 0.85, fontFace: "Cambria", fontSize: 30, bold: true, color: C.text1, valign: "middle", margin: 0, align: "left" }, text: "" } },
  { text: { text: "HRRS · Software Verification & Validation · Raktim Chandra · SRMIST", options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontFace: "Calibri", fontSize: 10, color: "8A8984", margin: 0 } } }],
  slideNumber: { x: 12.1, y: 7.0, w: 0.6, h: 0.3, fontFace: "Calibri", fontSize: 10, color: "8A8984", align: "right" } });

// ------------------------------------------------------------------ helpers
async function icon(Comp, color = "FFFFFF", size = 256) {
  const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
let objN = 0;
const nm = (p) => `${p}-${++objN}`;
function card(s, x, y, w, h, fill = HEX.white, line = HEX.grid) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: line, width: 1 },
    shadow: { type: "outer", color: "000000", opacity: 0.08, blur: 6, offset: 2, angle: 90 }, objectName: nm("card") });
}
async function iconCircle(s, Comp, x, y, d = 0.62, bg = HEX.teal) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { color: bg }, objectName: nm("icon-bg") });
  s.addImage({ data: await icon(Comp), x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: nm("icon") });
}
function chip(s, text, x, y, w = 1.7, fill = HEX.pale, color = HEX.teal) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.32, rectRadius: 0.16, fill: { color: fill }, line: { color: fill }, objectName: nm("chip") });
  s.addText(text, { x, y, w, h: 0.32, fontFace: "Consolas", fontSize: 10.5, color, bold: true, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: nm("chip-t") });
}
function txt(s, text, o) { s.addText(text, { fontFace: "Calibri", fontSize: 15, color: HEX.ink, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 4, objectName: nm("t"), ...o }); }
function bulletsT(s, items, o) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1 } })),
    { fontFace: "Calibri", fontSize: 15, color: HEX.ink, valign: "top", margin: 0, paraSpaceAfter: 6, isTextBox: true, objectName: nm("b"), ...o });
}
function stat(s, big, label, x, y, w, color = HEX.teal) {
  txt(s, big, { x, y, w, h: 0.85, fontFace: "Calibri", fontSize: 40, bold: true, color, align: "left", valign: "bottom" });
  txt(s, label, { x, y: y + 0.88, w, h: 0.6, fontSize: 13, color: HEX.ink2 });
}
function eqBox(s, text, x, y, w, h = 0.55, size = 18) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: "F5F7FA" }, line: { color: "DCE3EC", width: 1 }, objectName: nm("eq") });
  txt(s, text, { x: x + 0.15, y, w: w - 0.3, h, fontFace: "Cambria Math", fontSize: size, color: HEX.navy, align: "center", valign: "middle" });
}
function img(s, file, x, y, w, h) {
  const b = fs.readFileSync(file);
  const iw = b.readUInt32BE(16), ih = b.readUInt32BE(20);
  let ww = w, hh = w * ih / iw;
  if (hh > h) { hh = h; ww = h * iw / ih; }
  s.addImage({ path: file, x: x + (w - ww) / 2, y: y + (h - hh) / 2, w: ww, h: hh, objectName: nm("img") });
}
const TH = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.navy }, fontFace: "Calibri" } });
function tbl(s, head, rows, o) {
  const data = [head.map(TH), ...rows.map((r) => r.map((v) => (typeof v === "object" && v !== null && v.text !== undefined ? v : { text: String(v) })))];
  s.addTable(data, { fontFace: "Calibri", fontSize: 14, color: HEX.ink, border: { type: "solid", pt: 0.75, color: "D5D2C8" }, fill: { color: "FFFFFF" },
    valign: "middle", margin: 0.05, rowH: 0.3, autoPage: false, objectName: nm("tbl"), ...o });
}
const PASSC = (t) => ({ text: t, options: { color: t === "PASS" ? "067647" : t === "SKIPPED" ? "B7791F" : "B42318", bold: true, align: "center" } });
const chartBase = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt",
  legendFontFace: "+mn-lt", catAxisLabelColor: HEX.ink2, valAxisLabelColor: HEX.ink2, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  dataLabelFontSize: 11, dataLabelColor: HEX.ink2, valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" },
  titleFontSize: 14, titleColor: HEX.ink, legendFontSize: 12, legendColor: HEX.ink2 };

let SEC = "";
function section(title, sub, num, notes) {
  SEC = title;
  pres.addSection({ title });
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: SEC });
  s.addText(title, { placeholder: "title" });
  s.addText(sub, { placeholder: "body" });
  txt(s, num, { x: 0.8, y: 1.0, w: 3, h: 1.8, fontFace: "Cambria", fontSize: 96, bold: true, color: "3F9AA3", valign: "bottom" });
  s.addNotes(notes);
}
function content(title, notes) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: SEC });
  s.addText(title, { placeholder: "title" });
  s.addNotes(notes);
  return s;
}

(async () => {
  // =================================================================== OPENING
  SEC = "Opening";
  pres.addSection({ title: SEC });
  let s = pres.addSlide({ masterName: "TITLE", sectionTitle: SEC });
  s.addText("Testing a Hotel Room Reservation System", { placeholder: "title" });
  s.addText("Software Verification & Validation · FT-3: test-case design and testing levels — planned, built, automated and measured", { placeholder: "body" });
  txt(s, "Raktim Chandra  ·  RA2311033010038", { x: 0.8, y: 5.4, w: 11.7, h: 0.4, fontSize: 18, color: "FFFFFF", bold: true });
  txt(s, "Faculty: Mr. Kaviyaraj R.  ·  B.Tech CSE (Software Engineering) · Sem VII · AI2 · CINTEL · SRM Institute of Science and Technology", { x: 0.8, y: 5.85, w: 11.7, h: 0.4, fontSize: 14, color: "C9D6E8" });
  chip(s, `${N} TEST CASES · 0 FAILURES`, 0.8, 1.2, 3.6, "1E3358", "F2C46D");
  s.addNotes("The one-line story: I did not just write test cases on paper — I built the hotel system, wrote 554 executable test cases using every FT-3 technique, ran them, measured how good they are, and every number in this deck comes from that run.");

  s = content("One project, four workstreams", "The whole campaign was planned, built, automated and reported by one person, organised as four workstreams that map to the sections of this talk.");
  const team = [["Automation", "WORKSTREAM 1", "Test plan · @tc automation framework · results pipeline · performance engineering", fa.FaChessKing],
    ["Black-box design", "WORKSTREAM 2", "ECP, BVA, decision tables, cause-effect graphs, state transition · BDD acceptance", fa.FaTable],
    ["White-box", "WORKSTREAM 3", "CFG, V(G), MC/DC, data-flow · integration · mutation · fault seeding", fa.FaProjectDiagram],
    ["Non-functional", "WORKSTREAM 4", "Security (OWASP) · end-to-end UI · accessibility · compatibility", fa.FaShieldAlt]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.08;
    card(s, x, 1.55, 2.85, 4.1);
    await iconCircle(s, team[i][3], x + 0.3, 1.85, 0.8, [HEX.teal, HEX.blue, HEX.violet, HEX.red][i]);
    txt(s, team[i][0], { x: x + 0.3, y: 2.85, w: 2.3, h: 0.45, fontFace: "Cambria", fontSize: 19, bold: true, color: HEX.navy });
    txt(s, team[i][1], { x: x + 0.3, y: 3.3, w: 2.3, h: 0.35, fontFace: "Consolas", fontSize: 12, color: HEX.teal });
    txt(s, team[i][2], { x: x + 0.3, y: 3.8, w: 2.3, h: 1.7, fontSize: 16, color: HEX.ink2 });
  }
  txt(s, "Faculty: Mr. Kaviyaraj R.  ·  Course component FT-3 (Cycle Test 3): manual test case design and testing levels", { x: 0.6, y: 5.95, w: 12.1, h: 0.4, fontSize: 14, color: HEX.ink2 });

  s = content("The result in six numbers", "These six numbers are the whole talk. 554 designed and executed cases; 100% statement coverage; mutation score 100% after excluding three mathematically equivalent mutants; all 12 deliberately injected bugs caught; five real defects found and fixed; and peak-load p95 latency of about 150 ms against a 300 ms target.");
  const stats = [[String(N), "executed test cases across 5 levels", HEX.teal], ["100 %", `statement coverage (${cov.totals.covered_lines}/${cov.totals.num_statements}); ${cov.totals.percent_branches_covered.toFixed(1)} % branches`, HEX.blue],
    ["100 %", "mutation score — 267/267 non-equivalent mutants killed", HEX.violet], ["12 / 12", "seeded faults detected (fault seeding)", HEX.green],
    [String(defects.length), "real defects found → fixed → regression-tested", HEX.red], [`${Math.round(perf.load.p95_ms)} ms`, "p95 at 25 concurrent users (SLA 300 ms)", HEX.gold]];
  stats.forEach(([b, l, c], i) => { const x = 0.6 + (i % 3) * 4.1, y = 1.6 + Math.floor(i / 3) * 2.55; card(s, x, y, 3.8, 2.25); stat(s, b, l, x + 0.3, y + 0.2, 3.3, c); });

  s = content("Agenda", "Six parts; each section owner presents it.");
  const ag = [["01", "The system under test", "what we built and why it is test-worthy"], ["02", "Strategy & plan", "V-model, taxonomy, pyramid, IEEE 829 plan"],
    ["03", "Black-box design", "ECP · BVA · decision tables · cause-effect · state · pairwise"], ["04", "White-box coverage", "CFG · V(G) · MC/DC · data-flow · mutation · seeding"],
    ["05", "Levels & non-functional", "integration · system · E2E · UAT · performance · security"], ["06", "Results", "execution, RTM, defects, metrics, lessons"]];
  ag.forEach(([n, t, d], i) => { const x = 0.6 + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 1.75; card(s, x, y, 5.9, 1.5);
    txt(s, n, { x: x + 0.3, y: y + 0.25, w: 1.1, h: 1, fontFace: "Cambria", fontSize: 40, bold: true, color: HEX.gold });
    txt(s, t, { x: x + 1.45, y: y + 0.28, w: 4.2, h: 0.45, fontFace: "Cambria", fontSize: 20, bold: true, color: HEX.navy });
    txt(s, d, { x: x + 1.45, y: y + 0.78, w: 4.2, h: 0.5, fontSize: 14, color: HEX.ink2 }); });

  // =================================================================== 01 SYSTEM
  section("The system under test", "Marina Crest Reservations — a FastAPI + SQLite + web UI application built to be tested", "01", "We needed a system rich enough in rules to exercise every technique, so we specified and built one.");

  s = content("HRRS: small enough to build, rich enough to test", "Walk the eight capabilities; point out that each one is a source of boundaries, combinations or states.");
  const feats = [[fa.FaUserCheck, "Registration & sign-in", "name/e-mail/mobile/age rules · lock-out after 3 failures"], [fa.FaSearch, "Availability search", "1–30 nights, ≤ 365 days ahead, 4 room types"],
    [fa.FaRupeeSign, "Pricing engine", "weekend +20 %, peak +30 %, loyalty, long-stay, promos, GST slabs"], [fa.FaCreditCard, "Payments", "Luhn cards, UPI, 15-min window, idempotency keys"],
    [fa.FaUndo, "Cancellation policy", "8-rule refund decision table, processing fee, vouchers"], [fa.FaExchangeAlt, "Booking life-cycle", "6 states, 5 events, illegal moves rejected"],
    [fa.FaDoorOpen, "Check-in / check-out", "ID verification, late check-out fee bands"], [fa.FaChartLine, "Management metrics", "Occupancy, ADR, RevPAR"]];
  for (let i = 0; i < 8; i++) { const x = 0.6 + (i % 4) * 3.08, y = 1.55 + Math.floor(i / 4) * 2.6; card(s, x, y, 2.85, 2.35);
    await iconCircle(s, feats[i][0], x + 0.25, y + 0.25, 0.6, i % 2 ? HEX.blue : HEX.teal);
    txt(s, feats[i][1], { x: x + 0.25, y: y + 0.98, w: 2.4, h: 0.4, fontFace: "Cambria", fontSize: 16, bold: true, color: HEX.navy });
    txt(s, feats[i][2], { x: x + 0.25, y: y + 1.42, w: 2.4, h: 0.85, fontSize: 13, color: HEX.ink2 }); }

  s = content("Three layers, three test levels", "The architecture was designed for testability: pure domain functions for unit tests, a service layer with a real database for integration tests, and HTTP/UI for system and acceptance tests. The payment gateway is a stub with fault injection.");
  img(s, FIG("architecture.png"), 0.6, 1.25, 12.1, 3.95);
  [["Domain layer", "pure functions → unit tests (448)", HEX.green], ["Service + DB + stub", "→ integration tests (31)", HEX.gold], ["REST API + web UI", "→ system, E2E and UAT tests (75)", HEX.violet]].forEach(([t, d, c], i) => {
    const x = 0.6 + i * 4.1; card(s, x, 5.4, 3.85, 1.35); s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 5.82, w: 0.5, h: 0.5, fill: { color: c }, line: { color: c } });
    txt(s, t, { x: x + 0.9, y: 5.58, w: 2.8, h: 0.45, fontSize: 16, bold: true, color: HEX.navy }); txt(s, d, { x: x + 0.9, y: 6.03, w: 2.8, h: 0.5, fontSize: 14, color: HEX.ink2 }); });

  s = content("The pricing rules, written as equations", "Writing the rules as equations made boundaries obvious and let us build an independent test oracle. Walk the worked example: it is verified by a test and by hand.");
  eqBox(s, "nightly(d) = tariff × (1 + 0.20·[Fri/Sat] + 0.30·[20 Dec–5 Jan])", 0.6, 1.5, 7.4, 0.6, 15);
  eqBox(s, "discount = min( subtotal·(long-stay% + loyalty%) + promo, 0.30·subtotal )", 0.6, 2.3, 7.4, 0.6, 14);
  eqBox(s, "total = (subtotal − discount) × (1 + GST),  GST ∈ {0, 5 %, 18 %}", 0.6, 3.1, 7.4, 0.6, 15);
  eqBox(s, "RevPAR = revenue ÷ rooms available = ADR × Occupancy", 0.6, 3.9, 7.4, 0.6, 15);
  txt(s, "GST slab on the declared nightly tariff (rates effective 22 Sep 2025): below ₹1,000 nil · up to ₹7,500 → 5 % · above ₹7,500 → 18 %. The ₹7,500 edge is a classic boundary.", { x: 0.6, y: 4.75, w: 7.4, h: 1.0, fontSize: 14, color: HEX.ink2 });
  card(s, 8.35, 1.5, 4.35, 5.1, HEX.paleGold, "EED9B0");
  txt(s, "Worked example", { x: 8.65, y: 1.7, w: 3.8, h: 0.4, fontFace: "Cambria", fontSize: 18, bold: true, color: HEX.navy });
  txt(s, [{ text: "Suite + extra bed, Thu 24 → Sun 27 Dec 2026", options: { bold: true, breakLine: true } },
    { text: "declared tariff 7,500 + 800 = ₹8,300 → 18 % slab", options: { breakLine: true } },
    { text: "Thu ×1.30 (peak) · Fri ×1.50 · Sat ×1.50", options: { breakLine: true } },
    { text: "subtotal = 8,300 × 4.30 = ₹35,690.00", options: { breakLine: true } },
    { text: "GST 18 % = ₹6,424.20", options: { breakLine: true } },
    { text: "total = ₹42,114.20", options: { bold: true, color: HEX.teal } }], { x: 8.65, y: 2.2, w: 3.85, h: 3.2, fontSize: 15, paraSpaceAfter: 8 });
  chip(s, "TC-SYS-FN-002", 8.65, 5.85, 1.8);

  s = content("Booking life-cycle as a state machine", "Six states, five events. Only six transitions are legal; the other twenty-four cells of the state table must be rejected — we test all thirty.");
  img(s, FIG("state_machine.png"), 0.5, 1.4, 12.3, 3.9);
  [["6", "states"], ["5", "events"], ["6", "legal transitions"], ["24", "illegal — must be rejected"]].forEach(([b, l], i) => stat(s, b, l, 0.8 + i * 3.1, 5.25, 2.8, i === 3 ? HEX.red : HEX.teal));

  s = content("Requirements were made testable first", "Static testing came first: the requirements review found seven ambiguities — such as which tariff decides the GST slab — before any test was written. 15 functional, 17 non-functional requirements.");
  tbl(s, ["ID", "Requirement (testable form, abridged)"], reqs.filter((r) => r.id.startsWith("FR")).slice(0, 9).map((r) => [r.id, r.text.length > 92 ? r.text.slice(0, 90) + "…" : r.text]),
    { x: 0.6, y: 1.45, w: 8.2, colW: [0.8, 7.4], fontSize: 12, rowH: 0.5 });
  card(s, 9.1, 1.45, 3.6, 4.9, HEX.paleRed, "F2C9C9");
  txt(s, "Review found 7 issues", { x: 9.35, y: 1.65, w: 3.2, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: HEX.navy });
  bulletsT(s, ["RV-01 Which tariff decides GST?", "RV-02 Is arrival day still cancellable?", "RV-03 Which nights are “weekend”?", "RV-04 Promo vs. 30 % cap order", "RV-05 Lock-out counter reset", "RV-06 Guests across rooms", "RV-07 “Should be fast” → p95 < 300 ms"],
    { x: 9.35, y: 2.2, w: 3.2, h: 4, fontSize: 13 });

  // =================================================================== 02 STRATEGY
  section("Strategy & plan", "How we decided what to test, at which level, with which technique", "02", "");

  s = content("Verification vs. validation", "Keep the distinction crisp; then map our activities to each column.");
  for (let i = 0; i < 2; i++) {
    const [t, q, items, c, ic] = [["Verification", "Are we building the product right?", ["Requirements review (RV-01..07) & code inspection", "Static analysis: Ruff, Bandit, Radon", "448 unit + 31 integration tests", "Coverage, mutation testing, fault seeding"], HEX.blue, fa.FaCheckDouble],
      ["Validation", "Are we building the right product?", ["71 system & end-to-end tests", "4 BDD acceptance scenarios in users' language", "Accessibility audit & keyboard-only use", "Performance against the agreed SLA"], HEX.teal, fa.FaUserFriends]][i];
    const x = 0.6 + i * 6.15; card(s, x, 1.55, 5.9, 4.9); await iconCircle(s, ic, x + 0.35, 1.85, 0.75, c);
    txt(s, t, { x: x + 1.3, y: 1.85, w: 4.3, h: 0.45, fontFace: "Cambria", fontSize: 24, bold: true, color: HEX.navy });
    txt(s, q, { x: x + 1.3, y: 2.3, w: 4.3, h: 0.4, fontSize: 15, italic: true, color: c });
    bulletsT(s, items, { x: x + 0.4, y: 3.0, w: 5.2, h: 3.2, fontSize: 19, paraSpaceAfter: 12 });
  }

  s = content("V-model: every design level has a matching test level", "Read left-down then right-up; dashed arrows are the verification/validation pairs. Numbers are executed cases per level.");
  img(s, FIG("vmodel.png"), 0.6, 1.3, 12.1, 5.5);

  s = content("What “every type and sub-type” means here", "This map organises the rest of the talk. Every leaf is a technique we actually applied with test cases in the catalogue.");
  img(s, FIG("taxonomy.png"), 0.4, 1.25, 4.2, 5.65);
  const fam = [["Static", "reviews · inspection · lint · SAST · complexity", HEX.blue], ["Black-box", "BVA · ECP · DT · CEG · state · pairwise · BDD · error guessing · property-based", HEX.green],
    ["White-box", "statement · branch · condition · MC/DC · basis path · loop · data-flow · mutation · seeding", HEX.violet], ["Levels", "unit · integration (bottom-up + stubs) · system · E2E · acceptance", HEX.gold],
    ["Non-functional", "load · stress · spike · soak · volume · security · a11y · compatibility · recovery · concurrency", HEX.red], ["Change-related", "regression · confirmation · smoke", HEX.teal]];
  fam.forEach(([t, d, c], i) => { const y = 1.35 + i * 0.93; card(s, 4.9, y, 7.8, 0.8); s.addShape(pres.shapes.OVAL, { x: 5.1, y: y + 0.24, w: 0.32, h: 0.32, fill: { color: c }, line: { color: c } });
    txt(s, t, { x: 5.6, y: y + 0.12, w: 1.9, h: 0.55, fontSize: 16, bold: true, color: HEX.navy, valign: "middle" }); txt(s, d, { x: 7.5, y: y + 0.12, w: 5.05, h: 0.55, fontSize: 13, color: HEX.ink2, valign: "middle" }); });

  s = content("The test pyramid we actually built", "Many fast unit tests, fewer slower ones on top. Whole suite runs in about 40 seconds.");
  s.addChart(pres.charts.BAR, [{ name: "Test cases", labels: ["Unit", "Integration", "System / API", "E2E UI", "Acceptance"], values: [lvl("Unit"), lvl("Integration"), lvl("System"), lvl("System (E2E UI)"), lvl("Acceptance (UAT)")] }],
    { x: 0.6, y: 1.4, w: 7.2, h: 5.3, barDir: "bar", chartColors: [HEX.teal], showValue: true, dataLabelPosition: "outEnd", showLegend: false, showTitle: true, title: "Executed test cases per level", catAxisOrientation: "maxMin", valAxisHidden: true, barGapWidthPct: 45, ...chartBase });
  tbl(s, ["Level", "Driver", "Runtime"], [["Unit", "pytest + Hypothesis", "< 3 s"], ["Integration", "pytest, temp SQLite, threads", "≈ 5 s"], ["System / API", "FastAPI TestClient", "≈ 10 s"], ["E2E UI", "Playwright Chromium + axe", "≈ 15 s"], ["Acceptance", "pytest-bdd (Gherkin)", "≈ 1 s"]],
    { x: 8.1, y: 1.55, w: 4.6, colW: [1.3, 2.3, 1.0], fontSize: 14, rowH: 0.5 });
  txt(s, "Full suite: ≈ 40 s · identical results on a second run · no flaky tests", { x: 8.1, y: 4.9, w: 4.6, h: 0.8, fontSize: 15, bold: true, color: HEX.teal });

  s = content("IEEE 829 test plan — the decisions that mattered", "Highlight exit criteria — they are measurable, and we met them. Risk-based: the highest-exposure risks get tests at two or more levels.");
  tbl(s, ["Level", "Exit criteria", "Met"], [["Unit", "all pass · coverage ≥ 95 % · mutation ≥ 90 %", "✓"], ["Integration", "all pass incl. 25× concurrency repeat", "✓"], ["System", "P1/P2 pass · SLA met · no open Major", "✓"], ["Acceptance", "all UAT scenarios pass", "✓"]],
    { x: 0.6, y: 1.5, w: 6.0, colW: [1.4, 3.9, 0.7], fontSize: 15, rowH: 0.65 });
  tbl(s, ["Top risk", "Exposure", "Tested by"], [["Overbooking under load", "High", "20-thread race ×25"], ["Wrong price / tax", "High", "BVA + pairwise oracle"], ["Double charge", "High", "idempotency tests"], ["Unauthorised access", "Medium", "IDOR / escalation"], ["Slow booking at peak", "Medium", "load campaign"]],
    { x: 6.9, y: 1.5, w: 5.8, colW: [2.3, 1.1, 2.4], fontSize: 15, rowH: 0.6 });
  txt(s, "Suspension: smoke suite fails or > 10 % blocked · Resumption: smoke green on fixed build · Environment: frozen clock 8 Oct 2026 10:00 for reproducible dates", { x: 0.6, y: 5.6, w: 12.1, h: 0.9, fontSize: 14, color: HEX.ink2 });

  s = content("Every test case is executable — and reports itself", "This is our differentiator. IEEE 829 fields live on the test; the run writes the actual result back; workbook, RTM and report are generated from it. No result was typed by hand.");
  const ex = results.find((r) => r.id === "TC-CAN-DT-004");
  tbl(s, ["Field", "Value"], [["TC ID", ex.id], ["Objective", ex.title], ["Module / requirement", `${ex.module} / ${ex.requirement}`], ["Technique / level", `${ex.technique} / ${ex.level}`],
    ["Inputs", ex.inputs], ["Expected", ex.expected], ["Actual (written by the run)", "As expected"], ["Status · duration", `${ex.status} · ${ex.duration_ms} ms`], ["Automated test", ex.nodeid]],
    { x: 0.6, y: 1.45, w: 7.3, colW: [2.1, 5.2], fontSize: 11.5, rowH: 0.43 });
  const flow = [["@tc marker", "IEEE 829 fields on each test"], ["pytest run", "conftest hook records outcome"], ["results.json", "554 rows, real status"], ["Generators", "workbook · RTM · report · deck"]];
  flow.forEach(([t, d], i) => { const y = 1.45 + i * 1.2; card(s, 8.3, y, 4.4, 0.95, i === 2 ? HEX.paleGold : HEX.pale, "D5E3E6");
    txt(s, t, { x: 8.55, y: y + 0.12, w: 4, h: 0.38, fontFace: "Consolas", fontSize: 15, bold: true, color: HEX.teal }); txt(s, d, { x: 8.55, y: y + 0.5, w: 4, h: 0.38, fontSize: 13, color: HEX.ink2 }); });

  // =================================================================== 03 BLACK BOX
  section("Black-box test design", "Deriving cases from the specification: ECP · BVA · decision tables · cause-effect · state · pairwise", "03", "");

  s = content("ECP: one representative per class — and it found a real bug", "Valid classes together, invalid classes one at a time so a failure has one cause. Enumerating valid class V4 — an initial — found DEF-001.");
  tbl(s, ["Input", "Valid classes", "Invalid classes (one at a time)"], [["E-mail", "simple · plus-tag · upper-case", "no @ · no local · no domain · no TLD · 1-char TLD · space · two @ · empty · None"],
    ["Mobile", "9xxxxxxxxx · 6xxxxxxxxx · +91", "starts 5 · 9 digits · 11 digits · letters · inner space · empty"], ["Name", "letters · ' · - · initial “R. ”", "digits · @ · emoji · blank · <script>"],
    ["Password", "upper+lower+digit+special", "no upper · no lower · no digit · no special · space · non-string"], ["Card", "Visa · MasterCard · spaced · dashed", "Luhn fail · 15/17 digits · letters · empty"]],
    { x: 0.6, y: 1.45, w: 7.8, colW: [1.2, 2.6, 4.0], fontSize: 13, rowH: 0.75 });
  card(s, 8.7, 1.45, 4.0, 4.9, HEX.paleRed, "F2C9C9");
  await iconCircle(s, fa.FaBug, 8.95, 1.7, 0.7, HEX.red);
  txt(s, "DEF-001", { x: 9.8, y: 1.78, w: 2.7, h: 0.5, fontFace: "Cambria", fontSize: 24, bold: true, color: HEX.red });
  txt(s, [{ text: "Valid class V4 “R. Chandra” was rejected.", options: { bold: true, breakLine: true } }, { text: "The name pattern allowed only one separator between letter groups, so “. ” failed.", options: { breakLine: true } },
    { text: "Fixed; API regression test TC-REG-RGN-001 now registers “R. Chandra”.", options: {} }], { x: 8.95, y: 2.65, w: 3.5, h: 3.4, fontSize: 15, paraSpaceAfter: 10 });
  txt(s, `${results.filter((r) => r.technique === "ECP").length} ECP cases executed`, { x: 0.6, y: 6.5, w: 7, h: 0.4, fontSize: 15, bold: true, color: HEX.teal });

  s = content("BVA: test where off-by-one bugs live", "Four variants and their formulas. We used robust BVA on every single bounded input and normal + worst-case BVA for the two-variable nights × rooms quote.");
  tbl(s, ["Variant", "Values per variable", "Cases"], [["Normal", "min, min+1, nom, max−1, max", "4n + 1"], ["Robust", "+ min−1, max+1", "6n + 1"], ["Worst-case", "all 5 values crossed", "5ⁿ"], ["Robust worst-case", "all 7 values crossed", "7ⁿ"]],
    { x: 0.6, y: 1.45, w: 5.2, colW: [1.7, 2.5, 1.0], fontSize: 15, rowH: 0.5 });
  txt(s, "n = 3 (age, nights, rooms) → 13 · 19 · 125 · 343 cases", { x: 0.6, y: 4.55, w: 5.2, h: 0.5, fontSize: 15, bold: true, color: HEX.teal });
  txt(s, `${results.filter((r) => r.technique.startsWith("BVA")).length} BVA cases executed — 16 single-variable inputs + 34 multi-variable`, { x: 0.6, y: 5.15, w: 5.2, h: 0.8, fontSize: 14, color: HEX.ink2 });
  img(s, FIG("ecp_bva_lines.png"), 6.0, 1.35, 6.8, 5.5);

  s = content("BVA in action: the ₹7,500 GST edge and a 5 × 5 worst-case grid", "Left: eleven GST boundary cases. Right: the 25-cell worst-case grid for nights × rooms — every cell is an executed, passing test. The seeded bug SF-03 (< instead of <=) was caught by TC-PRC-BVA-008.");
  const g = results.filter((r) => r.id.startsWith("TC-PRC-BVA-0") && Number(r.id.slice(-3)) <= 11);
  tbl(s, ["TC ID", "Tariff", "Expected", "Result"], g.map((r) => [r.id, r.inputs.replace("tariff=", "₹"), r.expected, PASSC(r.status)]), { x: 0.6, y: 1.4, w: 5.9, colW: [1.9, 1.2, 1.8, 1.0], fontSize: 11.5, rowH: 0.36 });
  const nights = [1, 2, 15, 29, 30], rooms = [1, 2, 3, 4, 5];
  txt(s, "rooms →", { x: 7.9, y: 1.4, w: 4, h: 0.35, fontSize: 13, color: HEX.ink2 });
  rooms.forEach((r, j) => txt(s, String(r), { x: 7.9 + j * 0.9, y: 1.75, w: 0.85, h: 0.3, fontSize: 13, bold: true, align: "center", color: HEX.navy }));
  nights.forEach((n, i) => { txt(s, `${n} n`, { x: 6.95, y: 2.1 + i * 0.82, w: 0.85, h: 0.75, fontSize: 13, bold: true, color: HEX.navy, valign: "middle", align: "right" });
    rooms.forEach((r, j) => { s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.95 + j * 0.9, y: 2.1 + i * 0.82, w: 0.8, h: 0.72, rectRadius: 0.08, fill: { color: HEX.paleGreen }, line: { color: "BFE6D3" } });
      txt(s, "PASS", { x: 7.95 + j * 0.9, y: 2.1 + i * 0.82, w: 0.8, h: 0.72, fontSize: 10.5, bold: true, color: "067647", align: "center", valign: "middle" }); }); });
  txt(s, "TC-QTE-WC-001 … 025 · invariant: total = taxable + GST, discount ≤ 30 %", { x: 6.95, y: 6.25, w: 5.8, h: 0.45, fontSize: 13, color: HEX.ink2 });

  s = content("Decision table DT-1: cancellation refund in 8 rules", "Four conditions give 32 combinations; don't-cares collapse them to 8 rules. One test per rule gives rule coverage; 14 more cases expand the tier column and test precedence.");
  const H = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.teal }, align: "center" } });
  const dtRows = [["C1 Hotel-initiated?", "Y", "N", "N", "N", "N", "N", "N", "N"], ["C2 Refundable rate?", "–", "N", "Y", "Y", "Y", "Y", "Y", "Y"], ["C3 Days before check-in", "–", "≥0", "≥7", "2–6", "2–6", "0–1", "0–1", "<0"],
    ["C4 PLATINUM member?", "–", "–", "–", "N", "Y", "N", "Y", "–"], ["A1 Refund %", "100", "0", "100", "50", "75", "0", "25", "reject"], ["A2 Fee ₹", "0", "0", "0", "200", "0", "0", "0", "–"], ["A3 Voucher", "✓", "", "", "", "", "", "", ""],
    ["Test case", "001", "002", "003", "004", "005", "006", "007", "008"]];
  s.addTable([["Condition / action", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"].map((t) => H(t)),
    ...dtRows.map((r, i) => r.map((v, j) => ({ text: v, options: { align: j ? "center" : "left", bold: j === 0 || i >= 4, fill: { color: i >= 4 && i < 7 ? HEX.paleGold : i === 7 ? HEX.pale : "FFFFFF" }, fontFace: i === 7 && j ? "Consolas" : "Calibri" } })))],
    { x: 0.6, y: 1.45, w: 12.1, colW: [3.3, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1], fontSize: 14, rowH: 0.5, border: { type: "solid", pt: 0.75, color: "D5D2C8" }, fontFace: "Calibri", color: HEX.ink, valign: "middle", objectName: "dt1" });
  txt(s, "32 combinations → 8 rules · 22 executed cases · DT-2 (benefits) runs all 2⁴ = 16 rules · DT-3 covers sign-in lock-out", { x: 0.6, y: 6.2, w: 12.1, h: 0.45, fontSize: 15, bold: true, color: HEX.teal });

  s = content("Cause-effect graph: logic first, then a reduced test set", "Causes and effects joined by AND/OR/NOT; back-tracking each effect gives 10 cases instead of 16, each forcing one AND input false or one OR input solely true.");
  img(s, FIG("cause_effect.png"), 0.4, 1.3, 7.6, 5.0);
  eqBox(s, "E1 = C1 ∧ C2 ∧ C4", 8.3, 1.5, 4.4, 0.55, 18); eqBox(s, "E2 = C1 ∨ (C2 ∧ C3)", 8.3, 2.2, 4.4, 0.55, 18); eqBox(s, "E3 = ¬E1 ∧ ¬E2", 8.3, 2.9, 4.4, 0.55, 18);
  bulletsT(s, ["C1 tier GOLD/PLATINUM · C2 ≥ 3 nights", "C3 booked ≥ 30 days ahead · C4 room ≠ SUITE", "E1 free upgrade · E2 free breakfast · E3 none", "10 CEG cases + 16 exhaustive DT cases — all PASS"], { x: 8.3, y: 3.75, w: 4.4, h: 2.6, fontSize: 14 });

  s = content("State transition: all 30 cells of the state table", "0-switch coverage: 6 valid transitions must move correctly and 24 illegal ones must be rejected. Plus 8 multi-event sequences. A seeded bug that allowed cancelling after check-in was caught by TC-STM-SEQ-005.");
  const evs = ["pay", "expire", "cancel", "check_in", "check_out"], sts = ["PENDING", "CONFIRMED", "CHECKED_IN", "CHECKED_OUT", "CANCELLED", "EXPIRED"];
  const T = { pay: { PENDING: "CONFIRMED" }, expire: { PENDING: "EXPIRED" }, cancel: { PENDING: "CANCELLED", CONFIRMED: "CANCELLED" }, check_in: { CONFIRMED: "CHECKED_IN" }, check_out: { CHECKED_IN: "CHECKED_OUT" } };
  s.addTable([["State \\ event", ...evs].map((t) => H(t)), ...sts.map((st) => [{ text: st, options: { bold: true, fontFace: "Consolas" } },
    ...evs.map((e) => (T[e][st] ? { text: "→ " + T[e][st], options: { fill: { color: HEX.paleGreen }, color: "067647", bold: true, align: "center" } } : { text: "✗ rejected", options: { fill: { color: "FBF3F3" }, color: "B42318", align: "center" } }))])],
    { x: 0.6, y: 1.45, w: 12.1, colW: [2.35, 1.95, 1.95, 1.95, 1.95, 1.95], fontSize: 13, rowH: 0.55, border: { type: "solid", pt: 0.75, color: "D5D2C8" }, fontFace: "Calibri", color: HEX.ink, valign: "middle", objectName: "stt" });
  txt(s, "30 table cases (TC-STM-001…030) + 8 sequences (TC-STM-SEQ) + Hypothesis fuzzing of random event sequences (TC-PBT-007)", { x: 0.6, y: 5.6, w: 12.1, h: 0.6, fontSize: 15, bold: true, color: HEX.teal });

  s = content("Pairwise testing with an oracle, plus property-based tests", "288 combinations of five pricing parameters reduced to 20 all-pairs cases, each checked against a naive re-implementation of the formula. Property-based tests check invariants on hundreds of generated inputs.");
  stat(s, "288 → 20", "pricing combinations → all-pairs cases (−93 %)", 0.6, 1.4, 5.5, HEX.teal);
  bulletsT(s, ["Parameters: room 4 × tier 4 × promo 3 × extra bed 2 × stay pattern 3", "Every pair of values appears in ≥ 1 case (125 pairs)", "Oracle written from the SRS — not from the code — so a shared misunderstanding cannot hide", "Production engine and oracle agree on all 20"], { x: 0.6, y: 3.1, w: 5.6, h: 3.3, fontSize: 15 });
  tbl(s, ["Property (Hypothesis)", "Examples"], [["total = taxable + GST; all amounts ≥ 0", "200"], ["discount ≤ 30 % of subtotal", "200"], ["one more night never lowers the price", "200"], ["k rooms cost k × one room", "200"],
    ["0 ≤ refund ≤ amount paid", "300"], ["any digit change breaks a Luhn number", "200"], ["random events never escape the 6 states", "300"], ["accepted password ⇒ all rules hold", "400"]],
    { x: 6.6, y: 1.45, w: 6.1, colW: [5.0, 1.1], fontSize: 14, rowH: 0.55 });

  // =================================================================== 04 WHITE BOX
  section("White-box coverage", "From control-flow graphs to mutation testing — measuring what the tests really check", "04", "");

  s = content("Coverage criteria form a hierarchy", "Each stronger criterion subsumes the weaker. Then the formula for each.");
  const lad = [["Statement", "every statement runs", "executed ÷ statements"], ["Branch", "every decision TRUE and FALSE", "taken ÷ branches"], ["Condition", "every atomic condition TRUE and FALSE", "outcomes ÷ 2·conditions"],
    ["MC/DC", "each condition independently flips the decision", "≥ N + 1 tests"], ["Basis path", "V(G) independent paths", "paths ÷ V(G)"]];
  lad.forEach(([t, d, f], i) => { const y = 1.45 + i * 1.0, x = 0.6 + i * 0.35; card(s, x, y, 7.4 - i * 0.35, 0.85, i % 2 ? HEX.pale : HEX.white);
    txt(s, t, { x: x + 0.25, y: y + 0.12, w: 1.9, h: 0.6, fontFace: "Cambria", fontSize: 18, bold: true, color: HEX.navy, valign: "middle" });
    txt(s, d, { x: x + 2.2, y: y + 0.12, w: 4.9 - i * 0.35, h: 0.6, fontSize: 14, color: HEX.ink2, valign: "middle" }); });
  txt(s, "▲ stronger criteria subsume the weaker ones below", { x: 0.6, y: 6.45, w: 7, h: 0.35, fontSize: 13, color: HEX.ink2, italic: true });
  card(s, 8.4, 1.45, 4.3, 4.9, HEX.paleGold, "EED9B0");
  txt(s, "Also applied", { x: 8.65, y: 1.65, w: 3.8, h: 0.45, fontFace: "Cambria", fontSize: 18, bold: true, color: HEX.navy });
  bulletsT(s, ["Loop testing: 0, 1, 2, m, n−1, n iterations", "Data-flow: all-defs, all-uses, all-du-paths", "Coverage-guided gap closure", "Mutation testing — 270 mutants", "Fault seeding — 12 injected bugs"], { x: 8.65, y: 2.2, w: 3.8, h: 3.8, fontSize: 15 });

  s = content("refund_decision(): V(G) = 8, three ways", "17 nodes, 23 edges, 7 predicate nodes. All three formulas give 8 independent paths, so 8 basis-path tests. Radon reports 9 because it also counts the boolean operator in (tier or 'NONE').");
  img(s, FIG("cfg_refund.png"), 0.4, 1.25, 6.4, 5.65);
  eqBox(s, "V(G) = E − N + 2P = 23 − 17 + 2 = 8", 7.0, 1.5, 5.7, 0.6, 19);
  eqBox(s, "V(G) = predicate nodes + 1 = 7 + 1 = 8", 7.0, 2.3, 5.7, 0.6, 19);
  eqBox(s, "V(G) = bounded regions + 1 = 7 + 1 = 8", 7.0, 3.1, 5.7, 0.6, 19);
  card(s, 7.0, 4.0, 5.7, 2.35, HEX.pale, "D5E3E6");
  txt(s, [{ text: "Why does radon say 9?", options: { bold: true, breakLine: true, color: HEX.navy } }, { text: "Radon counts each Boolean operator as a decision (extended complexity). `(tier or \"NONE\")` adds one. McCabe on the CFG is 8 — basis-path design uses the CFG value." }],
    { x: 7.25, y: 4.2, w: 5.2, h: 2.0, fontSize: 15, paraSpaceAfter: 8 });

  s = content("Eight basis paths, eight tests — and 100 % branch coverage", "One test per independent path; together they also cover every statement and branch of the function.");
  tbl(s, ["TC ID", "Path (decision outcomes)", "Inputs", "Exit", "Result"], results.filter((r) => r.id.startsWith("TC-WB-PATH") && Number(r.id.slice(-3)) <= 8).map((r) => [r.id, r.title.split(": ")[1] || r.title, r.inputs.replace(/, /g, " · "), r.expected.replace("Exits through ", ""), PASSC(r.status)]),
    { x: 0.6, y: 1.45, w: 12.1, colW: [1.8, 3.9, 4.0, 1.4, 1.0], fontSize: 13, rowH: 0.6 });

  s = content("From statement to MC/DC on a single decision", "Each step adds a test the weaker criterion can skip. MC/DC needs N+1 = 3 tests for two conditions.");
  eqBox(s, "if  cap is not None  and  amount > cap :   amount = cap", 0.6, 1.45, 12.1, 0.6, 19);
  tbl(s, ["Criterion", "Tests", "Test added", "What the weaker criterion misses"], [["Statement", "1", "WELCOME10 on ₹50,000 → cap applied (STMT-001)", "—"], ["Branch", "2", "+ WELCOME10 on ₹4,000 → decision FALSE (BR-001)", "never takes the FALSE arm"],
    ["Condition", "3", "+ FLAT500 → `cap is not None` FALSE (COND-001)", "condition A never false"], ["MC/DC", "N+1 = 3", "(T,T)→T · (T,F)→F · (F,–)→F (MCDC-001…003)", "independent effect of each condition"]],
    { x: 0.6, y: 2.3, w: 12.1, colW: [1.6, 1.1, 5.4, 4.0], fontSize: 15, rowH: 0.6 });
  txt(s, "Coverage of gst_rate() for {500}: 4/8 statements (50 %), 2/6 branches (33 %) → add 12000: 75 % / 67 % → add 5000, −5: 100 % / 100 % (verified with coverage.py)", { x: 0.6, y: 5.3, w: 12.1, h: 0.8, fontSize: 15, color: HEX.teal, bold: true });

  s = content("MC/DC on four conditions: is it peak season?", "Each condition needs an independence pair — two tests differing only in that condition with different outcomes. Because a month cannot be both 12 and 1, A and C are coupled, so 6 tests instead of N+1 = 5.");
  eqBox(s, "peak = (A ∧ B) ∨ (C ∧ D)     A: month = 12   B: day ≥ 20   C: month = 1   D: day ≤ 5", 0.6, 1.45, 12.1, 0.6, 16);
  const mc = [["MCDC-004", "25 Dec", "T", "T", "F", "F", "T", "base"], ["MCDC-005", "10 Dec", "T", "F", "F", "F", "F", "B ↔ 004"], ["MCDC-006", "25 Nov", "F", "T", "F", "F", "F", "A ↔ 004"], ["MCDC-007", "3 Jan", "F", "F", "T", "T", "T", "base"], ["MCDC-008", "10 Jan", "F", "F", "T", "F", "F", "D ↔ 007"], ["MCDC-009", "3 Nov", "F", "F", "F", "T", "F", "C ↔ 007"]];
  s.addTable([["Test", "Date", "A", "B", "C", "D", "Outcome", "Independence pair"].map((t) => H(t)), ...mc.map((r) => r.map((v, j) => ({ text: v, options: { align: j > 1 && j < 7 ? "center" : "left", bold: j === 6, color: v === "T" ? "067647" : v === "F" && j > 1 && j < 7 ? "B42318" : HEX.ink, fontFace: j === 0 ? "Consolas" : "Calibri" } })))],
    { x: 0.6, y: 2.3, w: 12.1, colW: [1.7, 1.4, 1, 1, 1, 1, 1.5, 3.5], fontSize: 14, rowH: 0.5, border: { type: "solid", pt: 0.75, color: "D5D2C8" }, fontFace: "Calibri", valign: "middle", objectName: "mcdc" });

  s = content("Data-flow testing: every definition reaches its use", "In late_checkout_fee, pct has four definitions and one use; all-defs and all-uses need the same 4 tests, plus the error path. promo_amount's amount variable adds two more du-paths.");
  img(s, FIG("cfg_latefee.png"), 0.4, 1.25, 6.2, 5.65);
  tbl(s, ["Var", "def", "use", "Test"], [["rate", "1", "2 (p-use)", "WB-DF-001"], ["pct", "4 (=0)", "10 (c-use)", "WB-DF-002"], ["pct", "6 (=25)", "10 (c-use)", "WB-DF-003"], ["pct", "8 (=50)", "10 (c-use)", "WB-DF-004"], ["pct", "9 (=100)", "10 (c-use)", "WB-DF-005"], ["amount", "PCT", "> cap → return", "WB-DF-006"], ["amount", "AMT", "return", "WB-DF-007"]],
    { x: 6.9, y: 1.45, w: 5.8, colW: [1.1, 1.3, 1.7, 1.7], fontSize: 14, rowH: 0.48 });
  txt(s, "Loop testing on the per-night loop: 0 (rejected), 1, 2, 15, 29, 30 iterations — TC-WB-LOOP-001…006", { x: 6.9, y: 5.3, w: 5.8, h: 0.9, fontSize: 14, color: HEX.teal, bold: true });

  s = content(`Coverage: from ${cov0.totals.percent_covered.toFixed(1)} % to ${cov.totals.percent_covered.toFixed(1)} % by chasing the gaps`, "The first full run left a few branches uncovered. They were real untested behaviour — most importantly, no API test had ever triggered the 409 handler for an illegal state transition. Ten coverage-guided tests closed them.");
  const files = Object.keys(cov.files).filter((f) => cov.files[f].summary.num_statements > 0);
  s.addChart(pres.charts.BAR, [{ name: "First full run", labels: files.map((f) => f.replace("app/", "").replace("domain/", "").replace(".py", "")), values: files.map((f) => +cov0.files[f].summary.percent_covered.toFixed(1)) },
    { name: "After coverage-guided tests", labels: files.map((f) => f.replace("app/", "").replace("domain/", "").replace(".py", "")), values: files.map((f) => +cov.files[f].summary.percent_covered.toFixed(1)) }],
    { x: 0.6, y: 1.4, w: 8.2, h: 5.3, barDir: "col", chartColors: [HEX.gold, HEX.teal], valAxisMinVal: 90, valAxisMaxVal: 100, showLegend: true, legendPos: "b", showTitle: true, title: "Statement + branch coverage per module (%) — axis from 90", barGapWidthPct: 60, ...chartBase, catAxisLabelFontSize: 10 });
  stat(s, "867 / 867", "statements covered (100 %)", 9.1, 1.6, 3.6, HEX.teal);
  stat(s, "255 / 256", "branches covered (99.6 %)", 9.1, 3.2, 3.6, HEX.blue);
  txt(s, "Gap found: HTTP 409 handler never hit by any API test → TC-COV-001", { x: 9.1, y: 4.9, w: 3.6, h: 1.0, fontSize: 14, bold: true, color: HEX.red });

  s = content("Mutation testing: does a wrong result get noticed?", "We built our own AST mutation engine. Iteration 1: 85.9%; all 23 metrics mutants survived because metrics were only tested at integration level. Mutation-guided tests took it to 98.9% raw; the last 3 are proven equivalent, so the score is 100%.");
  const it = mut.summary.iterations;
  s.addChart(pres.charts.BAR, [{ name: "Killed", labels: it.map((x) => `Iteration ${x.iteration} (+${x.tests_added} tests)`), values: it.map((x) => x.killed) }, { name: "Survived", labels: it.map((x) => `Iteration ${x.iteration} (+${x.tests_added} tests)`), values: it.map((x) => x.survived) }],
    { x: 0.6, y: 1.4, w: 6.6, h: 5.3, barDir: "col", barGrouping: "stacked", chartColors: [HEX.teal, HEX.red], showValue: true, dataLabelPosition: "inEnd", dataLabelColor: "FFFFFF", showLegend: true, legendPos: "b", showTitle: true, title: "Mutants killed vs. survived (of 270)", barGapWidthPct: 55, valAxisMinVal: 0, valAxisMaxVal: 280, ...chartBase, dataLabelColor: "FFFFFF" });
  eqBox(s, "MS = killed ÷ (total − equivalent) = 100 %", 7.5, 1.5, 5.2, 0.6, 15);
  tbl(s, ["Operator", "Example", "Killed"], [["ROR", "≥ 7 → > 7", "120/122"], ["CRP", "14 → 15", "51/52"], ["AOR", "− → +", "32/32"], ["UOD", "not x → x", "29/29"], ["LCR", "and → or", "25/25"], ["BRV", "True → False", "10/10"]],
    { x: 7.5, y: 2.35, w: 5.2, colW: [1.2, 2.6, 1.4], fontSize: 14, rowH: 0.42 });
  txt(s, "3 equivalent mutants, e.g. `d > 9` → `d >= 9` in Luhn: a doubled digit is always even, so it is never 9", { x: 7.5, y: 5.5, w: 5.2, h: 0.9, fontSize: 13.5, color: HEX.ink2 });

  s = content("Fault seeding: we tested our tests — and one failed us", "Twelve realistic bugs injected one at a time; the full suite run against each. Rev A missed SF-11, a DOM-XSS hole, because our XSS test used a path that never echoes input. Strengthened test, Rev B catches 12/12.");
  img(s, FIG("fault_seeding.png"), 0.4, 1.3, 7.6, 4.5);
  eqBox(s, `N̂ = n × S ÷ s = ${seed.summary.native_found} × ${seed.summary.seeded} ÷ ${seed.summary.seeded_detected} = ${seed.summary.mills_estimated_native_total}`, 8.25, 1.5, 4.45, 0.6, 17);
  txt(s, "Mills' estimator: latent product defects ≈ 0 (Rev A estimate: 4.36)", { x: 8.25, y: 2.2, w: 4.45, h: 0.7, fontSize: 13.5, color: HEX.ink2 });
  card(s, 8.25, 3.05, 4.45, 3.3, HEX.paleGold, "EED9B0");
  txt(s, [{ text: "DEF-005 — a defect in our test suite", options: { bold: true, breakLine: true, color: HEX.navy } }, { text: "SF-11: textContent → innerHTML. 0 failures. The login error never reflects input; the promo-code error does. TC-E2E-003 Rev B attacks that path — now detected." }],
    { x: 8.5, y: 3.25, w: 4.0, h: 3.0, fontSize: 14.5, paraSpaceAfter: 8 });
  txt(s, "Caught at: Unit (6) · Integration (4) · System (1) · E2E (1) — no single level catches everything", { x: 0.6, y: 6.0, w: 7.4, h: 0.6, fontSize: 14, bold: true, color: HEX.teal });

  // =================================================================== 05 LEVELS & NFR
  section("Levels & non-functional testing", "Integration · system · end-to-end · acceptance · performance · security · accessibility", "05", "");

  s = content("Integration: bottom-up with a fault-injecting stub", "Domain first, then service with a real SQLite DB, then HTTP. The external payment gateway is a stub that can time out or decline, so recovery paths are deterministic. 20 threads race for 3 suites — exactly 3 win.");
  img(s, FIG("integration_strategy.png"), 0.4, 1.3, 5.6, 5.3);
  card(s, 6.3, 1.45, 6.4, 2.35, HEX.pale, "D5E3E6");
  txt(s, "Concurrency: no overbooking", { x: 6.55, y: 1.6, w: 5.9, h: 0.45, fontFace: "Cambria", fontSize: 19, bold: true, color: HEX.navy });
  [["20", "threads at a barrier"], ["3", "bookings succeed"], ["25 / 25", "repeated runs pass"]].forEach(([b, l], i) => stat(s, b, l, 6.55 + i * 2.05, 2.0, 1.9, HEX.teal));
  tbl(s, ["Integration focus", "Tests"], [["Overlap rules, inventory exhaustion", "INT-002…004"], ["Payment + masking, idempotency", "INT-006, 007"], ["Gateway timeout / decline recovery", "INT-008, 024"], ["Restart persistence, expiry job", "INT-009…011"], ["Login decision table (lock-out)", "AUTH-DT-001…006"]],
    { x: 6.3, y: 4.0, w: 6.4, colW: [4.3, 2.1], fontSize: 14, rowH: 0.45 });

  s = content("System level: the API keeps its contract, even when it says no", "Every error has a documented status and machine-readable code. The OpenAPI contract is tested too.");
  const neg = results.filter((r) => r.id.startsWith("TC-SYS-NEG")).slice(0, 12);
  tbl(s, ["TC ID", "Scenario", "Expected", "Result"], neg.map((r) => [r.id, r.title.split(" → ")[0], r.expected, PASSC(r.status)]), { x: 0.6, y: 1.4, w: 12.1, colW: [1.9, 6.0, 3.2, 1.0], fontSize: 13, rowH: 0.42 });

  s = content("End-to-end in a real browser — recorded on video", "Playwright drives Chromium against a live server: register, sign in, search, price, reserve, pay, cancel. Every run records video and screenshots; these are from the test run.");
  [["crop_search.png", "1 · Search: live availability and prices", 0.6, 1.4], ["crop_quote.png", "2 · Price breakdown with GST", 6.75, 1.4],
   ["crop_paid.png", "3 · Paid: booking CONFIRMED", 0.6, 3.95], ["crop_cancel.png", "4 · Cancelled: refund rule R3", 6.75, 3.95]].forEach(([f, l, x, y]) => {
    card(s, x, y, 5.95, 2.4); img(s, FIG(f), x + 0.1, y + 0.1, 5.75, 1.85); txt(s, l, { x: x + 0.2, y: y + 1.98, w: 5.5, h: 0.35, fontSize: 14, bold: true, color: HEX.navy }); });
  txt(s, `${lvl("System (E2E UI)")} E2E cases: journey · validation · DOM-XSS · axe-core · keyboard-only · 4 devices · 3 browsers (2 skipped here) · page load · 2 regression`, { x: 0.6, y: 6.45, w: 12.1, h: 0.4, fontSize: 14, color: HEX.teal, bold: true });

  s = content("Acceptance: requirements as executable Gherkin", "Written in the hotel's vocabulary and executed with pytest-bdd. The Scenario Outline runs three examples.");
  const featAll = fs.readFileSync(path.join(ROOT, "tests/acceptance/features/booking.feature"), "utf8").split("\n");
  const st0 = featAll.findIndex((l) => l.includes("@UAT-03"));
  const feat = featAll.slice(st0, st0 + 12).map((l) => l.replace(/^  /, "")).join("\n");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.4, w: 7.6, h: 5.2, rectRadius: 0.1, fill: { color: "1E2A44" }, line: { color: "1E2A44" } });
  txt(s, feat, { x: 0.85, y: 1.6, w: 7.2, h: 4.9, fontFace: "Consolas", fontSize: 13, color: "E8EEF7" });
  tbl(s, ["UAT", "Scenario", "Result"], results.filter((r) => r.id.startsWith("TC-UAT")).map((r) => [r.id.replace("TC-", ""), r.title.replace(/^UAT-0\d /, ""), PASSC(r.status)]), { x: 8.5, y: 1.45, w: 4.2, colW: [0.9, 2.5, 0.8], fontSize: 12, rowH: 0.6 });

  s = content("Load test found DEF-004: SLA met on average, missed on booking", "Overall p95 passed, but book+pay was 663 ms. Root cause: SQLite rollback journal. WAL journaling cut it to about 200 ms with the identical workload.");
  const eps = ["availability", "quote", "list", "book"];
  s.addChart(pres.charts.BAR, [{ name: "Before tuning", labels: ["availability", "quote", "list bookings", "book + pay"], values: eps.map((e) => perf0.load.by_endpoint_p95[e]) }, { name: "After WAL tuning", labels: ["availability", "quote", "list bookings", "book + pay"], values: eps.map((e) => perf.load.by_endpoint_p95[e]) }],
    { x: 0.6, y: 1.4, w: 7.6, h: 5.3, barDir: "col", chartColors: [HEX.gold, HEX.teal], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", showLegend: true, legendPos: "b", showTitle: true, title: "p95 latency at 25 concurrent users (ms) — SLA 300 ms", barGapWidthPct: 60, ...chartBase });
  [[`${perf0.load.by_endpoint_p95.book.toFixed(0)} → ${perf.load.by_endpoint_p95.book.toFixed(0)} ms`, "book + pay p95", HEX.red], [`${perf0.load.p95_ms} → ${perf.load.p95_ms} ms`, "overall p95 (SLA 300)", HEX.teal], [`${perf0.load.throughput_rps} → ${perf.load.throughput_rps}`, "requests / second", HEX.blue], ["0 %", "errors in every phase", HEX.green]].forEach(([b, l, c], i) => stat(s, b, l, 8.6, 1.4 + i * 1.32, 4.1, c));

  s = content("Stress, spike and soak: where it bends, and that it recovers", "Stress shows the knee moved from about 25 to 50 users after tuning; spike recovers immediately; soak shows no memory growth or latency drift. Single uvicorn worker on 2 vCPUs.");
  const vus = perf.stress.map((x) => String(x.vus));
  s.addChart(pres.charts.LINE, [{ name: "Before tuning", labels: vus, values: perf0.stress.map((x) => x.p95_ms) }, { name: "After WAL tuning", labels: vus, values: perf.stress.map((x) => x.p95_ms) }],
    { x: 0.6, y: 1.4, w: 7.4, h: 5.3, chartColors: [HEX.gold, HEX.teal], lineSize: 2, lineDataSymbolSize: 8, showLegend: true, legendPos: "b", showTitle: true, title: "Stress: p95 latency (ms) vs. concurrent users", catAxisTitle: "concurrent users", showCatAxisTitle: true, catAxisTitleFontSize: 12, catAxisTitleColor: HEX.ink2, ...chartBase });
  [[`${perf.spike.burst.p95_ms.toFixed(0)} ms`, `spike burst p95 (150 users) → back to ${perf.spike.after.p95_ms} ms`, HEX.gold], [`${perf.soak.windows.reduce((a, w) => a + w.requests, 0).toLocaleString("en-IN")}`, "requests in 60 s soak, RSS flat ≈ 86 MB", HEX.teal], [`${perf.volume.before.p95_ms} → ${perf.volume.after.p95_ms} ms`, "p95 after +5,000 bookings (volume)", HEX.blue]].forEach(([b, l, c], i) => stat(s, b, l, 8.4, 1.4 + i * 1.75, 4.3, c));

  s = content("Security: OWASP Top 10 categories, attacked on purpose", "Each row is an executed attack. Also SAST: Bandit's two findings were triaged — one hardened with an allow-list, one a false positive.");
  tbl(s, ["OWASP 2021", "Attack", "Result"], [["A01 Access control", "Guest B reads / pays / cancels guest A's booking (IDOR)", "403 blocked"], ["A01 Access control", "Guest sets own tier to PLATINUM; forces hotel refund", "403 blocked"],
    ["A02 Cryptography", "Plain password, hash or card number exposed", "PBKDF2 ×120k · masked PAN"], ["A03 Injection", "' OR '1'='1' -- in e-mail, password, path", "parameterised · 401/422"],
    ["A03 XSS", "<img onerror> in name; reflected via promo error", "rejected · rendered as text"], ["A05 Misconfiguration", "headers, stack traces", "CSP, XFO, nosniff · no traces"],
    ["A07 Auth failures", "brute force · user enumeration · logout", "lock after 3 · same message · revoked"], ["Integrity", "replayed payment", "Idempotency-Key"]],
    { x: 0.6, y: 1.4, w: 12.1, colW: [2.4, 6.2, 3.5], fontSize: 15, rowH: 0.6 });

  s = content("Accessibility and compatibility", "axe-core checked WCAG 2.0/2.1 A and AA rules on the rendered page: zero violations. Keyboard-only sign-in works. Four emulated devices with no horizontal scroll. Firefox/WebKit tests exist but were skipped because those browsers could not be installed in the sandbox.");
  stat(s, String(axe.violations.length), "axe-core WCAG A/AA violations", 0.6, 1.4, 3.2, HEX.green);
  stat(s, String(axe.passes), "accessibility rules passed", 0.6, 3.0, 3.2, HEX.teal);
  stat(s, "4 / 4", "device layouts pass, no horizontal scroll", 0.6, 4.6, 3.2, HEX.blue);
  [["08_device_iPhone_13.png", "iPhone 13"], ["08_device_Pixel_7.png", "Pixel 7"], ["08_device_iPad_gen_7.png", "iPad (gen 7)"]].forEach(([f, l], i) => { const x = 4.2 + i * 2.85; card(s, x, 1.4, 2.6, 5.2); img(s, SHOT(f), x + 0.1, 1.5, 2.4, 4.6); txt(s, l, { x: x + 0.1, y: 6.15, w: 2.4, h: 0.35, fontSize: 13, bold: true, align: "center", color: HEX.navy }); });

  // =================================================================== 06 RESULTS
  section("Results", "What ran, what it found, and what we learnt", "06", "");

  s = content(`${PASS} passed · ${SKIP} skipped · 0 failed`, "Final execution numbers by level; two skipped are the cross-browser cases. Same result on a second run.");
  const L5 = ["Unit", "Integration", "System", "System (E2E UI)", "Acceptance (UAT)"];
  s.addChart(pres.charts.BAR, [{ name: "Passed", labels: ["Unit", "Integration", "System/API", "E2E UI", "UAT"], values: L5.map((x) => results.filter((r) => r.level === x && r.status === "PASS").length) },
    { name: "Skipped", labels: ["Unit", "Integration", "System/API", "E2E UI", "UAT"], values: L5.map((x) => results.filter((r) => r.level === x && r.status === "SKIPPED").length) }],
    { x: 0.6, y: 1.4, w: 7.6, h: 5.3, barDir: "col", barGrouping: "stacked", chartColors: [HEX.teal, HEX.gold], showValue: false, showLegend: true, legendPos: "b", showTitle: true, title: "Executed test cases by level", barGapWidthPct: 50, ...chartBase });
  tbl(s, ["Level", "Pass", "Skip", "Fail"], L5.map((x) => [x.replace("System (E2E UI)", "E2E UI").replace("Acceptance (UAT)", "UAT"), String(results.filter((r) => r.level === x && r.status === "PASS").length), String(results.filter((r) => r.level === x && r.status === "SKIPPED").length), "0"]).concat([["Total", String(PASS), String(SKIP), "0"]]),
    { x: 8.6, y: 1.5, w: 4.1, colW: [1.9, 0.75, 0.7, 0.75], fontSize: 14, rowH: 0.48 });

  s = content("Traceability: every requirement reaches executed tests", "Heat-map of executed tests per requirement and level. 32 of 32 requirements covered; NFR-COMP-02 is partial because two browsers were skipped.");
  img(s, FIG("rtm_heatmap.png"), 0.4, 1.2, 5.6, 5.75);
  bulletsT(s, ["Forward: requirement → tests (coverage)", "Backward: every test names its requirement (no orphan tests)", "Pricing (FR-06) has the most cases — highest-risk rule set", "Workbook RTM recomputes with live formulas"], { x: 6.4, y: 1.6, w: 6.3, h: 3.5, fontSize: 16 });
  stat(s, "32 / 32", "requirements with executed tests", 6.4, 4.6, 6, HEX.teal);

  s = content("Five real defects — each found by a different technique", "No single technique would have found all five. That is the case for using many techniques.");
  const dcol = { "DEF-001": HEX.blue, "DEF-002": HEX.violet, "DEF-003": HEX.violet, "DEF-004": HEX.red, "DEF-005": HEX.gold };
  defects.forEach((d, i) => { const x = 0.6 + i * 2.46; card(s, x, 1.45, 2.3, 4.75);
    txt(s, d.id, { x: x + 0.2, y: 1.6, w: 1.9, h: 0.45, fontFace: "Cambria", fontSize: 20, bold: true, color: dcol[d.id] });
    txt(s, d.technique.replace("Exploratory testing / visual review", "Exploratory review").replace("Performance – load testing", "Load testing").replace("Fault seeding / defect injection", "Fault seeding"), { x: x + 0.2, y: 2.05, w: 1.9, h: 0.55, fontSize: 12, bold: true, color: HEX.teal });
    txt(s, d.title, { x: x + 0.2, y: 2.65, w: 1.9, h: 2.6, fontSize: 15, color: HEX.ink });
    chip(s, d.severity.toUpperCase(), x + 0.2, 5.35, 1.0, d.severity === "Major" ? HEX.paleRed : HEX.paleGold, d.severity === "Major" ? "B42318" : "B7791F");
    txt(s, "fixed ✓", { x: x + 1.25, y: 5.35, w: 0.9, h: 0.32, fontSize: 12, bold: true, color: "067647", valign: "middle" }); });
  txt(s, "Every fix has a regression test that was shown to fail on the unfixed code before it was accepted.", { x: 0.6, y: 6.5, w: 12.1, h: 0.4, fontSize: 14, color: HEX.ink2 });

  {
    const mc = ms.manual_cases, dm = fs.existsSync(path.join(ROOT, "reports/defects_manual.json")) ? J("reports/defects_manual.json") : [];
    const nP = mc.filter((m) => (m.status || "").startsWith("PASS")).length, nI = mc.filter((m) => m.status === "IN PROGRESS").length, nN = mc.filter((m) => m.status === "NOT RUN").length;
    s = content("Manual testing — run for real, or marked honestly", `${nP} manual cases passed with evidence, ${nI} are half done, ${nN} need real people or devices and were not simulated — each has a kit. Following our own README on a clean machine failed first time: ${dm.length} packaging defects, all fixed.`);
    const stCol = (st) => st.startsWith("PASS") ? "067647" : st === "IN PROGRESS" ? "B7791F" : "52514E";
    tbl(s, ["Manual case", "Type", "Status"], mc.map((m) => [m.id.replace("TC-MAN-", ""), m.type, { text: m.status, options: { bold: true, color: stCol(m.status) } }]),
      { x: 0.6, y: 1.4, w: 6.2, colW: [1.9, 2.3, 2.0], fontSize: 12.5, rowH: 0.43 });
    [[`${nP}`, "passed", HEX.green], [`${nI}`, "in progress", HEX.gold], [`${nN}`, "need people / devices", HEX.ink2]].forEach(([v, l, c], i) => {
      const x = 7.2 + i * 1.85; card(s, x, 1.4, 1.7, 1.25);
      txt(s, v, { x: x + 0.15, y: 1.48, w: 1.4, h: 0.6, fontFace: "Cambria", fontSize: 30, bold: true, color: c, align: "center" });
      txt(s, l, { x: x + 0.1, y: 2.1, w: 1.5, h: 0.5, fontSize: 11.5, color: HEX.ink2, align: "center" }); });
    txt(s, "L10N-001 · 30-night quote in Indian grouping", { x: 7.2, y: 2.9, w: 5.5, h: 0.3, fontSize: 12, bold: true, color: HEX.teal });
    const mx = J("reports/manual/manual_exec.json")["L10N-001"].amounts;
    tbl(s, ["Subtotal", "Discount", "GST 5 %", "Total"].map((h) => h), [mx.map((a, i) => ({ text: (i === 1 ? "− " : "") + a, options: { fontFace: "Consolas", bold: i === 3, color: i === 3 ? HEX.teal : HEX.ink, align: "center" } }))],
      { x: 7.2, y: 3.25, w: 5.5, colW: [1.45, 1.35, 1.25, 1.45], fontSize: 12.5, rowH: 0.38 });
    txt(s, "₹ sign · lakh grouping · two decimals — PASS", { x: 7.2, y: 4.08, w: 5.5, h: 0.3, fontSize: 11.5, color: HEX.ink2 });
    card(s, 7.2, 4.5, 5.5, 2.0, HEX.paleRed, "F3C6C6");
    txt(s, `DOC-001 found ${dm.length} more defects`, { x: 7.45, y: 4.62, w: 5.1, h: 0.4, fontFace: "Cambria", fontSize: 17, bold: true, color: "B42318" });
    txt(s, "We followed our own README on a clean machine. The suite failed (axe-core not shipped), a README line could not run, a marker run overwrote the evidence, and the generators needed lab-only paths. All fixed (DEF-006…010) and guarded by tools/check_package.py.",
      { x: 7.45, y: 5.05, w: 5.1, h: 1.4, fontSize: 12.5, color: HEX.ink });
  }

  s = content("Test metrics dashboard", "Formulas and values; the workbook computes these live.");
  const mets = [["Pass rate", "passed ÷ executed", `${(100 * PASS / PASS).toFixed(0)} %`], ["Requirement coverage", "covered ÷ requirements", "100 %"], ["Statement coverage", "867 ÷ 867", "100 %"], ["Branch coverage", "255 ÷ 256", "99.6 %"],
    ["Mutation score", "267 ÷ (270 − 3)", "100 %"], ["Seeded fault detection", "12 ÷ 12", "100 %"], ["Defect density", "4 ÷ 1.023 KLOC", "3.91 / KLOC"], ["DRE", "4 ÷ (4 + 0)", "100 %"], ["Test : code ratio", "≈ 3,000 ÷ 1,023 LOC", "≈ 2.9 : 1"]];
  mets.forEach(([t, f, v], i) => { const x = 0.6 + (i % 3) * 4.1, y = 1.45 + Math.floor(i / 3) * 1.75; card(s, x, y, 3.85, 1.5);
    txt(s, v, { x: x + 0.25, y: y + 0.15, w: 3.4, h: 0.65, fontFace: "Cambria", fontSize: 28, bold: true, color: HEX.teal });
    txt(s, t, { x: x + 0.25, y: y + 0.8, w: 3.4, h: 0.32, fontSize: 14, bold: true, color: HEX.navy }); txt(s, f, { x: x + 0.25, y: y + 1.1, w: 3.4, h: 0.3, fontSize: 12, color: HEX.ink2 }); });

  s = content("One booking, every lens", "Ananya (GOLD) books a Deluxe with extra bed, Fri 18–Sun 20 Dec, with WELCOME10, then cancels 4 days out. Every technique has something to say about this one booking; the price was checked against the oracle.");
  tbl(s, ["Lens", "Answer for this booking"], [["ECP / BVA", "4 guests = DELUXE capacity 3 + bed → exactly at the maximum; 19 Dec is the day before peak"],
    ["Pricing", "4,800 × (1.2 + 1.2) = 11,520 − (10 % GOLD 1,152 + promo 1,000 cap) = 9,368 + 5 % GST = ₹9,836.40"], ["Cause-effect", "C1 = T, C2 = F → no upgrade, free breakfast"], ["State machine", "PENDING → CONFIRMED → CANCELLED"],
    ["Decision table", "refundable, 4 days, not PLATINUM → R4: 50 % − ₹200 = ₹4,718.20"], ["White-box", "basis path P6 of refund_decision; MC/DC case 001 of the promo cap"], ["Security / perf", "403 for other guests · idempotent payment · book p95 ≈ 200 ms"]],
    { x: 0.6, y: 1.45, w: 12.1, colW: [2.2, 9.9], fontSize: 14, rowH: 0.62 });

  s = content("What I learnt", "One point per lesson; each came from a real finding in this project.");
  const lessons = [[fa.FaSearchPlus, "Enumerate every valid class", "ECP found a bug random data would almost never hit"], [fa.FaPercentage, "Coverage ≠ checking", "97.8 % coverage still hid 38 surviving mutants"],
    [fa.FaVial, "Test the tests", "fault seeding showed one security test could never fail"], [fa.FaTachometerAlt, "Never trust an average", "overall SLA passed while booking was 2× over"],
    [fa.FaEye, "Look at the screen", "two UI defects found by eye, then locked in by automation"], [fa.FaBalanceScale, "Report honestly", "skipped is skipped — never counted as passed"]];
  for (let i = 0; i < 6; i++) { const x = 0.6 + (i % 3) * 4.1, y = 1.45 + Math.floor(i / 3) * 2.55; card(s, x, y, 3.85, 2.3);
    await iconCircle(s, lessons[i][0], x + 0.25, y + 0.25, 0.65, [HEX.teal, HEX.blue, HEX.gold, HEX.red, HEX.violet, HEX.green][i]);
    txt(s, lessons[i][1], { x: x + 0.25, y: y + 1.0, w: 3.4, h: 0.45, fontFace: "Cambria", fontSize: 17, bold: true, color: HEX.navy });
    txt(s, lessons[i][2], { x: x + 0.25, y: y + 1.45, w: 3.4, h: 0.75, fontSize: 14, color: HEX.ink2 }); }

  s = content("Everything is in the submission — and reproducible", "Point to the package contents and the three commands to reproduce.");
  tbl(s, ["Deliverable", "What it is"], [["Test report (Word + PDF, 83 pp)", "plan, design, cases, results, metrics, case study, full catalogue"], ["Test-case workbook (Excel)", "554 cases with real results · RTM · defects · decision tables · metrics"],
    ["TSR · case studies · prep pack · manual kit", "IEEE 829 TSR · 5 investigations · 15 problems + viva · manual execution records + kits"], ["Source code + test suite", "HRRS app, 13 test modules, Gherkin, perf / mutation / seeding tools"],
    ["Evidence", "HTML & JUnit reports, coverage HTML, E2E videos & screenshots, perf JSON"], ["Demo video & dashboard", "captioned demo video · interactive results page"]], { x: 0.6, y: 1.45, w: 7.4, colW: [3.0, 4.4], fontSize: 13.5, rowH: 0.68 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.3, y: 1.45, w: 4.4, h: 4.6, rectRadius: 0.1, fill: { color: "1E2A44" }, line: { color: "1E2A44" } });
  txt(s, "pip install -r requirements.txt\npython -m playwright install chromium\n\nuvicorn app.main:app\n\npytest --cov=app --cov-branch\npytest -m smoke\npython tools/perf_test.py\npython tools/mutation.py\npython tools/fault_seeding.py", { x: 8.5, y: 1.65, w: 4.0, h: 4.2, fontFace: "Consolas", fontSize: 13, color: "E8EEF7" });

  s = pres.addSlide({ masterName: "TITLE", sectionTitle: SEC });
  s.addText("Thank you — questions?", { placeholder: "title" });
  s.addText(`${N} executable test cases · 10 defects found and fixed · 100 % statement coverage · 100 % mutation score`, { placeholder: "body" });
  txt(s, "Raktim Chandra · RA2311033010038", { x: 0.8, y: 5.4, w: 11.7, h: 0.4, fontSize: 18, color: "FFFFFF", bold: true });
  txt(s, "Software Verification and Validation · Mr. Kaviyaraj R. · SRMIST", { x: 0.8, y: 5.85, w: 11.7, h: 0.4, fontSize: 14, color: "C9D6E8" });
  s.addNotes("Offer a live demo: run python tools/live_demo.py and open the HTML report, or play the E2E video.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
