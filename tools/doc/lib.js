// Shared docx-js helpers for every HRRS document (report, test plan, summary, case studies, viva).
const fs = require("fs");
const path = require("path");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, BorderStyle, PageBreak, Header, Footer, PageNumber, TableOfContents,
  LevelFormat, PositionalTab, PositionalTabAlignment, PositionalTabLeader, VerticalAlign, TabStopType,
} = d;

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "docs", "figures");
const SHOT = path.join(ROOT, "reports", "screenshots");
const J = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));

const C = { navy: "14213D", teal: "0F6E78", ink: "1B1B1B", ink2: "52514E", line: "D5D2C8", pale: "EEF4FB",
  sand: "F6F1E7", aqua: "DCF3EA", red: "FBE1E1", gold: "B7791F", blue: "2A78D6" };
const BODY_FONT = "Times New Roman", HEAD_FONT = "Arial", MONO = "Consolas";
const PAGE_W = 11906, MARGIN = 1300, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, DXA

// ---------------------------------------------------------------- inline markup: **bold**, *italic*, `code`
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: (base.size || 22) - 2, color: "8A2B0F", ...base, bold: false }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const P = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { after: 120, line: 300 },
  alignment: opts.align || AlignmentType.JUSTIFIED, ...opts.para });
const HEADS = [];
const H1 = (t, inToc = true) => { if (inToc) HEADS.push([1, t]); return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true }); };
const H1n = (t) => { HEADS.push([1, t]); return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] }); };
const H2 = (t) => { HEADS.push([2, t]); return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] }); };
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const BR = () => new Paragraph({ children: [new PageBreak()] });
const SP = (n = 120) => new Paragraph({ children: [], spacing: { after: n } });

const bullets = (items, ref = "bullets") => items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 },
  children: runs(t), spacing: { after: 60, line: 280 } }));
const numbered = (items, ref) => items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 },
  children: runs(t), spacing: { after: 60, line: 280 } }));

function eq(text, note) {
  const ch = [new TextRun({ text, font: "Cambria Math", size: 24, italics: false, color: C.navy })];
  if (note) ch.push(new TextRun({ text: "     " + note, font: BODY_FONT, size: 18, color: C.ink2, italics: true }));
  return new Paragraph({ children: ch, alignment: AlignmentType.CENTER, spacing: { before: 100, after: 140 },
    shading: { type: ShadingType.CLEAR, fill: "F7F9FC", color: "auto" } });
}

function callout(title, text, fill = C.pale, edge = C.blue) {
  return new Paragraph({
    children: [new TextRun({ text: title + "  ", bold: true, color: C.navy }), ...runs(text)],
    shading: { type: ShadingType.CLEAR, fill, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 24, color: edge, space: 8 } },
    spacing: { before: 120, after: 160, line: 290 }, indent: { left: 200, right: 120 },
  });
}

function code(lines) {
  return lines.map((l, i) => new Paragraph({ children: [new TextRun({ text: l || " ", font: MONO, size: 17 })],
    shading: { type: ShadingType.CLEAR, fill: "F4F2EC", color: "auto" }, spacing: { after: 0, line: 240 },
    indent: { left: 200 }, keepNext: i < lines.length - 1 }));
}

// ---------------------------------------------------------------- tables
const border = { style: BorderStyle.SINGLE, size: 4, color: C.line };
const borders = { top: border, bottom: border, left: border, right: border };

function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = (opts.width || CONTENT_W) / total;
  const w = widths.map((x) => Math.floor(x * scale));
  const fs_ = opts.size || 18;
  const cell = (v, j, head, fill) => new TableCell({
    width: { size: w[j], type: WidthType.DXA }, borders,
    shading: { type: ShadingType.CLEAR, fill: head ? C.navy : (j === 0 && opts.keyCol ? "EEF4FB" : (fill || "FFFFFF")), color: "auto" },
    margins: { top: 50, bottom: 50, left: 90, right: 90 }, verticalAlign: VerticalAlign.CENTER,
    children: String(v ?? "").split("\n").map((line) => new Paragraph({
      children: runs(line, head ? { bold: true, color: "FFFFFF", size: fs_, font: HEAD_FONT } : { size: fs_ }),
      alignment: (opts.center || []).includes(j) ? AlignmentType.CENTER : AlignmentType.LEFT, spacing: { after: 0, line: 250 } })),
  });
  const tr = headers.every((h) => !h) ? [] : [new TableRow({ tableHeader: true, children: headers.map((h, j) => cell(h, j, true)) })];
  rows.forEach((r, i) => {
    const fill = opts.fill ? opts.fill(r, i) : (i % 2 ? "FAFAF7" : "FFFFFF");
    tr.push(new TableRow({ cantSplit: true, children: r.map((v, j) => cell(v, j, false, fill)) }));
  });
  return new Table({ width: { size: w.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: w, rows: tr });
}

let figNo = 0, tabNo = 0;
const figures = [], tables = [];
function caption(kind, text) {
  const n = kind === "Figure" ? ++figNo : ++tabNo;
  (kind === "Figure" ? figures : tables).push(`${kind} ${n}: ${text}`);
  return new Paragraph({ children: [new TextRun({ text: `${kind} ${n}. `, bold: true, size: 19, color: C.navy }),
    new TextRun({ text, italics: true, size: 19, color: C.ink2 })], alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 220 } });
}
const tcap = (text) => { const n = ++tabNo; tables.push(`Table ${n}: ${text}`);
  return new Paragraph({ children: [new TextRun({ text: `Table ${n}. `, bold: true, size: 19, color: C.navy }),
    new TextRun({ text, italics: true, size: 19, color: C.ink2 })], spacing: { before: 80, after: 200 } }); };

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function fig(file, text, widthIn = 6.2, dir = FIG) {
  const f = path.isAbsolute(file) ? file : path.join(dir, file);
  const { w, h } = pngSize(f);
  let wp = widthIn * 96, hp = wp * h / w;
  if (hp > 8.6 * 96) { hp = 8.6 * 96; wp = hp * w / h; }
  return [new Paragraph({ children: [new ImageRun({ type: "png", data: fs.readFileSync(f),
    transformation: { width: Math.round(wp), height: Math.round(hp) } })], alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 40 }, keepNext: true }), caption("Figure", text)];
}

// ---------------------------------------------------------------- cover
function cover(title, subtitle, docType) {
  const L = (t, o = {}) => new Paragraph({ children: [new TextRun({ text: t, ...o })], alignment: AlignmentType.CENTER,
    spacing: { after: o.after || 100 } });
  return [
    L("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", { bold: true, size: 30, color: C.navy, font: HEAD_FONT, after: 40 }),
    L("Kattankulathur, Chennai – 603 203", { size: 21, color: C.ink2, after: 40 }),
    L("Faculty of Engineering and Technology · School of Computing", { size: 21, color: C.ink2, after: 40 }),
    L("Department of Computational Intelligence (CINTEL)", { size: 21, color: C.ink2, after: 500 }),
    L(docType.toUpperCase(), { bold: true, size: 22, color: C.teal, font: HEAD_FONT, after: 160 }),
    L(title, { bold: true, size: 50, color: C.navy, font: HEAD_FONT, after: 120 }),
    L(subtitle, { size: 26, color: C.ink2, italics: true, after: 500 }),
    L("Course: Software Verification and Validation", { size: 23, after: 40 }),
    L("Component: FT-3 — Manual Test Case Design & Testing Levels", { size: 23, after: 40 }),
    L("B.Tech CSE (Software Engineering) · IV Year · Semester VII · Section AI2 · 2026–27", { size: 23, after: 400 }),
    L("Submitted by", { bold: true, size: 24, color: C.navy, after: 120 }),
    table(["Name", "Register number"], [["Raktim Chandra", "RA2311033010038"]], [3, 2],
      { width: 5600, size: 21, center: [1] }),
    SP(380),
    L("Submitted to: Mr. Kaviyaraj R.", { bold: true, size: 24, after: 40 }),
    L("Faculty, Software Verification and Validation", { size: 21, color: C.ink2, after: 40 }),
    L(new Date(J("reports/results.json")[0].executed_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }), { size: 21, color: C.ink2 }),
  ];
}

function build(file, sections, headerText) {
  const doc = new Document({
    creator: "Raktim Chandra — SRMIST", title: headerText, description: "HRRS Software V&V",
    styles: {
      default: { document: { run: { font: BODY_FONT, size: 22, color: C.ink } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 34, bold: true, font: HEAD_FONT, color: C.navy },
          paragraph: { spacing: { before: 120, after: 220 }, outlineLevel: 0,
            border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.teal, space: 6 } } } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 27, bold: true, font: HEAD_FONT, color: C.teal }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1, keepNext: true } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 23, bold: true, font: HEAD_FONT, color: C.navy }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2, keepNext: true } },
      ],
    },
    numbering: { config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
      ...Array.from({ length: 30 }, (_, i) => ({ reference: `num${i}`, levels: [{ level: 0, format: LevelFormat.DECIMAL,
        text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] })),
    ] },
    sections: sections.map((s, i) => ({
      properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 1300, bottom: 1200, left: MARGIN, right: MARGIN } },
        titlePage: i === 0 },
      headers: { default: new Header({ children: [new Paragraph({ children: [
        new TextRun({ text: headerText, size: 17, color: C.ink2, font: HEAD_FONT }),
        new TextRun({ children: [new PositionalTab({ alignment: PositionalTabAlignment.RIGHT, relativeTo: "margin", leader: "none" }),
          "Raktim Chandra · SRMIST · Software V&V"], size: 17, color: C.ink2, font: HEAD_FONT })],
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.line, space: 4 } } })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 17, color: C.ink2, font: HEAD_FONT })] })] }) },
      children: s,
    })),
  });
  return Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(file, buf); console.log("wrote", file); });
}

// Static TOC: page numbers come from a previous render (tools/doc/toc_pass.py) so the PDF and DOCX both show it.
function toc(pagesFile) {
  const out = [new Paragraph({ children: [new TextRun({ text: "Table of Contents", bold: true, size: 34, font: HEAD_FONT, color: C.navy })],
    spacing: { after: 200 }, pageBreakBefore: true })];
  let pages = [];
  try { pages = JSON.parse(fs.readFileSync(pagesFile, "utf8")); } catch (e) { pages = []; }
  const list = pages.length ? pages : Array.from({ length: 60 }, () => [2, "…", 0]);
  list.forEach(([lvl, text, pg]) => out.push(new Paragraph({
    children: [new TextRun({ text, bold: lvl === 1, size: lvl === 1 ? 21 : 19, font: lvl === 1 ? HEAD_FONT : BODY_FONT, color: lvl === 1 ? C.navy : C.ink }),
      new TextRun({ children: [new PositionalTab({ alignment: PositionalTabAlignment.RIGHT, relativeTo: "margin", leader: PositionalTabLeader.DOT }), String(pg || "")],
        size: lvl === 1 ? 21 : 19 })],
    indent: { left: lvl === 1 ? 0 : 360 }, spacing: { before: lvl === 1 ? 110 : 0, after: 30 } })));
  return out;
}

module.exports = { d, J, ROOT, FIG, SHOT, C, P, H1, H1n, H2, H3, BR, SP, bullets, numbered, eq, callout, code, table,
  fig, caption, tcap, cover, build, toc, runs, figures, tables, CONTENT_W, HEADS };
