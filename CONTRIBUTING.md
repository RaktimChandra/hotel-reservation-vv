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

**Modules / groups:** REG registration · AUTH · SRCH search · BOOK · ROOM · PRC pricing · QTE quote · CAN cancellation ·
CHK check-out · PAY payment · STM state machine · BEN benefits · RPT reports · WB white-box · EG error guessing ·
PBT property-based · INT integration · SYS system · SEC security · PERF · E2E · UAT · COV coverage-guided ·
MUT mutation-guided · MAN manual.

**Techniques:** BVA / BVA2 boundary values · ECP partitions · DT decision table · CEG cause-effect graph ·
SEQ state sequences · STMT / BR / COND / MCDC / PATH / DF / LOOP white-box criteria · PW pairwise ·
NEG negative · API contract · REC recovery · SMK smoke · RGN regression · FN functional · WC worst case.

## Before opening a pull request

```bash
pytest -q                          # full suite, writes reports/results.json
ruff check app tests tools
python tools/check_package.py
```

Use the defect-report issue form for bugs; it mirrors the columns of the project's defect log.
