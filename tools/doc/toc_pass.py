"""Two-pass static TOC: build docx → PDF, locate each heading's page, rebuild until stable."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOFFICE_HELPER = Path("/mnt/skills/public/docx/scripts/office/soffice.py")   # sandbox helper, used if present


def to_pdf(docx):
    """Convert with LibreOffice. Uses the sandbox helper when available, otherwise a plain soffice on PATH."""
    import shutil
    import tempfile
    if SOFFICE_HELPER.exists():
        cmd = [sys.executable, str(SOFFICE_HELPER)]
    else:
        exe = shutil.which("soffice") or shutil.which("libreoffice")
        if not exe:
            sys.exit("LibreOffice (soffice) is required for the TOC pass: install it and re-run.")
        profile = Path(tempfile.mkdtemp()).as_uri()
        cmd = [exe, f"-env:UserInstallation={profile}"]
    subprocess.run(cmd + ["--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)],
                   check=True, capture_output=True, timeout=600)


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def render(script, docx, pages_file):
    env = {"TOC_PAGES": str(pages_file)} if pages_file and Path(pages_file).exists() else {}
    import os
    subprocess.run(["node", str(script), str(docx)], check=True, env={**os.environ, **env}, capture_output=True)
    to_pdf(docx)
    pdf = docx.with_suffix(".pdf")
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))
    texts = [norm(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"], capture_output=True,
                                 text=True).stdout) for i in range(1, n + 1)]
    heads = json.loads(docx.with_suffix(".heads.json").read_text())
    keys = [norm(t)[:40] for _, t in heads]
    toc_pages = {i for i, t in enumerate(texts) if sum(k in t for k in keys) >= 8}
    out, start = [], (max(toc_pages) + 1 if toc_pages else 0)
    for lvl, text in heads:
        key = norm(text)[:40]
        page = next((i for i in range(start, n) if key in texts[i]), None)
        if page is None:
            page = start
        out.append([lvl, text, page + 1])
        start = page
    return out, n


def main(script, docx):
    script, docx = Path(script), Path(docx)
    pages_file = docx.with_suffix(".toc.json")
    if pages_file.exists():
        pages_file.unlink()
    prev = None
    for it in range(4):
        pages, n = render(script, docx, pages_file if prev else None)
        pages_file.write_text(json.dumps(pages, ensure_ascii=False))
        print(f"pass {it + 1}: {n} pages")
        if prev == pages:
            break
        prev = pages
    pages_file.unlink(); docx.with_suffix(".heads.json").unlink()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
