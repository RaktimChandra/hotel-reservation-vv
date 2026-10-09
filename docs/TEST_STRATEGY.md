# Test strategy

The full IEEE 829 test plan is chapter 4 of the test report (attached to each release). This page is the short version.

## Approach

Risk-based. Every requirement gets black-box test design; the domain layer additionally gets white-box coverage criteria; every level is automated; exploratory sessions cover the UI; non-functional campaigns cover performance, security, reliability and accessibility. Test quality is measured independently of coverage with mutation testing and fault seeding.

## Levels

| Level | What is under test | Entry criteria | Exit criteria | Result |
|---|---|---|---|---|
| Unit (448) | `app/domain/*` pure business rules | Module importable, requirements reviewed | All pass · coverage ≥ 95 % · mutation ≥ 90 % | 100 % · 100 % |
| Integration (31) | services + SQLite + gateway stub | Unit exit met, schema stable | All pass incl. 20-thread race ×25 | Met |
| System (56) | REST API: functional, negative, contract, security, recovery, performance | App deploys, smoke green | All P1/P2 pass · SLA met · no open Major | Met |
| End-to-end (15) | Browser UI with Playwright | System exit met | Journeys, accessibility, layouts pass | 13 pass, 2 skipped (browsers) |
| Acceptance (4 + outline) | Gherkin scenarios in business language | System exit met | All scenarios pass | Met |

**Suspension:** smoke suite fails, or more than 10 % of a suite is blocked by one defect.
**Resumption:** smoke suite green on the fixed build and the blocking defect verified fixed.

## Risk register

| Risk | Exposure | Mitigation (tests) |
|---|---|---|
| Overbooking under concurrent requests | High | Serialised write transaction · 20-thread race repeated 25× (TC-INT-005) |
| Wrong price or tax | High | BVA on every pricing boundary · pairwise with an independent oracle · property-based invariants |
| Double charge on retry | High | Idempotency key · TC-INT-007, TC-SEC-013, TC-COV-001/002 |
| Unauthorised access to bookings | Medium | Object- and role-level checks · IDOR and escalation tests (TC-SEC-005/006) |
| Slow booking at peak | Medium | Load / stress / spike / soak campaign — found DEF-004 |
| Inaccessible UI | Low | axe-core WCAG 2.1 audit · keyboard-only journey · screen-reader proxy |
| Lab cannot run Firefox/WebKit | Medium | Chromium device emulation · CI cross-browser job · manual cases COMP-001/002 |

## Techniques → where to find them

| Technique | Tests |
|---|---|
| Boundary value analysis, robust and worst-case | `tests/unit/test_bva.py` |
| Equivalence class partitioning | `tests/unit/test_ecp.py` |
| Decision tables, cause-effect graph | `tests/unit/test_decision_tables.py` |
| State transition (0-switch and sequences) | `tests/unit/test_state_transition.py` |
| Statement, branch, condition, MC/DC, basis path, data flow, loop | `tests/unit/test_whitebox.py` |
| Pairwise, property-based, error guessing | `tests/unit/test_combinatorial_property.py` |
| Mutation-guided | `tests/unit/test_mutation_guided.py`, engine in `tools/mutation.py` |
| Integration, concurrency | `tests/integration/` |
| API functional, negative, contract, security, recovery | `tests/system/test_api_system.py` |
| Coverage-guided | `tests/system/test_coverage_guided.py` |
| Performance (load, stress, spike, soak, volume) | `tools/perf_test.py`, `tests/system/test_performance.py` |
| End-to-end, accessibility, compatibility | `tests/e2e/test_ui_e2e.py` |
| Acceptance (BDD) | `tests/acceptance/` |
| Fault seeding | `tools/fault_seeding.py` |
| Static testing, manual and exploratory | `docs/manual_and_static.json`, `tools/manual_exec.py` |

## Pass / fail rule

A test passes only when actual equals expected exactly — error codes, amounts to the paisa, HTTP status codes. Skipped is reported as skipped, never as passed.

## Reproducibility

All date-dependent tests run on a frozen clock (8 Oct 2026, 10:00). The CI workflow runs the full suite on Python 3.11 and 3.13 on every push.
