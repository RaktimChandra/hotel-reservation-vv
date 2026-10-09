# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-10-09

### Added
- Hotel Room Reservation System: domain rules, SQLite service layer, FastAPI REST API and accessible single-page UI.
- 554 executable test cases with IEEE 829 metadata across unit, integration, system, end-to-end and acceptance levels.
- Black-box suites: BVA, ECP, decision tables, cause-effect graphing, state transition, pairwise, property-based, error guessing.
- White-box suite: basis paths, statement/branch/condition/MC/DC, data flow, loops; coverage-guided tests.
- AST mutation-testing engine, fault-seeding tool with Mills estimator, load/stress/spike/soak/volume harness.
- Playwright E2E with axe-core accessibility audit, device layouts and cross-browser cases; Gherkin acceptance tests.
- Tool-assisted manual-case execution (localisation, heuristic review, screen-reader proxy) with evidence.
- Generators for the Excel workbook, Word/PDF report, IEEE 829 summary report, slide deck, dashboard, one-pager and video.
- Live test-case output (`pytest --tc`), guided demo runner, visible-browser mode (`HRRS_HEADED=1`).
- CI on Python 3.11 and 3.13, weekly mutation/fault-seeding workflow, release pipeline that builds every document.

### Fixed
- DEF-001 valid names with an initial rejected · DEF-002 booking-form overflow · DEF-003 "₹-0.00" discount ·
  DEF-004 booking p95 663 ms under load (WAL tuning → 201 ms) · DEF-005 a DOM-XSS test that could never fail.
- DEF-006…010 packaging and documentation defects found by following the README on a clean machine.

[1.0.0]: https://github.com/RaktimChandra/hotel-reservation-vv/releases/tag/v1.0.0
