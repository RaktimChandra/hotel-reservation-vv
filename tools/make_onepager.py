"""Render the one-page summary (tools/onepager.html) to an A4 PDF and a PNG preview."""
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "onepager.html"
OUT = ROOT / "deliverables" / "HRRS_One_Page_Summary_Raktim.pdf"


def main():
    OUT.parent.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(SRC.as_uri())
        page.wait_for_timeout(600)
        # shrink until the summary fits on exactly one page
        for scale in (1.0, 0.98, 0.96, 0.94, 0.92, 0.9):
            page.pdf(path=str(OUT), format="A4", print_background=True, prefer_css_page_size=True, scale=scale)
            info = subprocess.run(["pdfinfo", str(OUT)], capture_output=True, text=True).stdout
            if "Pages:           1" in info:
                break
        browser.close()
    subprocess.run(["pdftoppm", "-r", "110", "-png", "-singlefile", str(OUT), str(OUT.with_suffix(""))], check=True)
    print("wrote", OUT, "at scale", scale)


if __name__ == "__main__":
    main()
