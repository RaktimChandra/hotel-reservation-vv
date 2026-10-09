// Writes the deck's own colour scheme and theme name into ppt/theme/theme1.xml.
// pptxgenjs sets the theme fonts but leaves Office's default palette; this replaces it.
const fs = require("fs");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));
const SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];

async function applyTheme(deckPath, theme) {
  const c = theme.colors || theme;
  for (const k of SLOTS) if (!/^[0-9A-Fa-f]{6}$/.test(String(c[k]))) throw new Error(`theme colour ${k} must be 6 hex digits`);
  const name = String(theme.name).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
  const zip = await JSZip.loadAsync(fs.readFileSync(deckPath));
  const part = "ppt/theme/theme1.xml";
  const scheme = `<a:clrScheme name="${name}">` + SLOTS.map((k) => `<a:${k}><a:srgbClr val="${String(c[k]).toUpperCase()}"/></a:${k}>`).join("") + "</a:clrScheme>";
  const xml = (await zip.file(part).async("string"))
    .replace(/<a:clrScheme\b[\s\S]*?<\/a:clrScheme>/, () => scheme)
    .replace(/(<a:(?:theme|fontScheme)\b[^>]*?\bname=")[^"]*"/g, (_, h) => `${h}${name}"`);
  zip.file(part, xml);
  fs.writeFileSync(deckPath, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}
module.exports = { applyTheme };
