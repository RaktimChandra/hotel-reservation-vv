"""Build the submission zip: deliverables + runnable source (no node_modules, caches or partial results)."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "HRRS_SVV_Raktim_Chandra"
SKIP_DIRS = {"node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
SKIP_FILES = {"results_partial.json"}
SKIP_SUFFIXES = {".sqlite", ".sqlite-wal", ".sqlite-shm", ".db"}
START = """HRRS — Software Verification & Validation · SRMIST
==========================================================
Raktim Chandra (RA2311033010038) · B.Tech CSE (Software Engineering) · Sem VII · AI2
Faculty: Mr. Kaviyaraj R.

01_Deliverables/
  HRRS_VV_Test_Report_Raktim.docx / .pdf            main report (83 pages): plan, design, cases, results, manual execution, metrics
  HRRS_VV_Presentation_Raktim.pptx / .pdf           presentation (54 slides, with speaker notes)
  HRRS_Test_Case_Workbook_Raktim.xlsx               554 automated cases with real results + 10 manual cases with execution record,
                                                   RTM, defect log (DEF-001…010), decision tables, metrics
  HRRS_Test_Summary_Report_IEEE829_Raktim.docx/.pdf IEEE 829 test summary report
  HRRS_Manual_Test_Execution_Kit_Raktim.docx/.pdf   execution records for the manual cases + kits for the ones that need people/devices
  HRRS_Case_Studies_Raktim.docx / .pdf              five findings traced end to end
  HRRS_CycleTest3_Prep_Problems_and_Viva_Raktim...  15 worked FT-3 problems + 25 viva answers
  HRRS_Demo_Video_Raktim.mp4                        110 s captioned demo (real browser recording)
  HRRS_Test_Results_Dashboard.html                 interactive results (open in a browser)
  HRRS_One_Page_Summary_Raktim.pdf / .png           one-page infographic

02_Project_Source/   runnable app + full test suite + tools + all raw evidence (see README.md)
  reports/test_report.html      pytest HTML report        reports/coverage_html/index.html   coverage report
  reports/e2e_videos/           browser test recordings   reports/screenshots/                E2E screenshots
  reports/manual/               manual-case evidence (screenshots, ARIA snapshot, captured requests)
  python tools/check_package.py  checks the package itself (regression guard for DEF-006…010)
"""


def main():
    out = ROOT / f"{TOP}_Complete_Package.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{TOP}/00_START_HERE.txt", START)
        z.write(ROOT / "README.md", f"{TOP}/README.md")
        for f in sorted((ROOT / "deliverables").iterdir()):
            z.write(f, f"{TOP}/01_Deliverables/{f.name}")
        for f in sorted(ROOT.rglob("*")):
            rel = f.relative_to(ROOT)
            if f.is_dir() or rel.parts[0] in ("deliverables",) or f.suffix == ".zip" or f.name in ("package-lock.json",):
                continue
            if SKIP_DIRS & set(rel.parts) or f.name in SKIP_FILES or "".join(f.suffixes[-1:]) in SKIP_SUFFIXES or f.suffix in SKIP_SUFFIXES:
                continue
            z.write(f, f"{TOP}/02_Project_Source/{rel.as_posix()}")
    print(out, round(out.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
