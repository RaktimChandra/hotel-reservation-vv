# Contributing

## Ground rules

1. Every behaviour change comes with a test case that names a requirement.
2. Results are never typed by hand — they come from `reports/results.json`, written by the run.
3. A defect fix lands together with a regression test that fails on the unfixed code.

## Adding a test case

Tests carry IEEE 829 metadata through the `@tc` decorator in `tests/tclib.py`:

```python
from tests.tclib import tc

@tc("TC-PRC-BVA-031", "Stay of 30 nights (maximum) is priced",
    module="Pricing", requirement="FR-06", technique="BVA", level="Unit",
    priority="P2", inputs="nights=30", expected="quote returned")
def test_max_nights(...):
    ...
```

### Test-case ID scheme

`TC-<MODULE>-<TECHNIQUE>-<NNN>` — e.g. `TC-CAN-DT-004` is Cancellation, Decision Table, case 4.

| Module | | Technique | |
|---|---|---|---|
| REG | registration | BVA | boundary value analysis |
| AUTH | authentication | ECP | equivalence partitioning |
| SRCH | search | DT | decision table |
| BOOK | booking | CEG | cause-effect graph |
| PRC | pricing | ST | state transition |
| CAN | cancellation | WB | white-box (PATH, MCDC, DF, LOOP) |
| PAY | payment | SEC | security |
| SYS / E2E / UAT | levels | PERF / REC | performance / recovery |

## Before opening a pull request

```bash
pytest -q                          # full suite, writes reports/results.json
ruff check app tests tools
python tools/check_package.py
```

Use the defect-report issue form for bugs; it mirrors the columns of the project's defect log.
