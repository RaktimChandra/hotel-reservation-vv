"""Test-case catalogue helpers.

Every executable test carries IEEE-829 style metadata via ``@pytest.mark.tc``.
``conftest.py`` collects that metadata together with the real outcome so the
test-case workbook, RTM and reports are generated from actual execution.
"""
import pytest

FIELDS = ("id", "title", "module", "requirement", "level", "type", "technique", "priority",
          "preconditions", "inputs", "steps", "expected")


def tc(id, title, *, module, requirement, level="Unit", type="Functional", technique,
       priority="P2", preconditions="—", inputs="—", steps="—", expected="—"):
    """Decorator for hand-written tests."""
    meta = dict(id=id, title=title, module=module, requirement=requirement, level=level, type=type,
                technique=technique, priority=priority, preconditions=preconditions,
                inputs=_fmt(inputs), steps=steps, expected=_fmt(expected))
    return pytest.mark.tc(**meta)


def _fmt(v):
    if isinstance(v, dict):
        return ", ".join(f"{k}={v!r}" for k, v in v.items())
    return str(v)


def cases(rows, **defaults):
    """Turn catalogue rows into pytest params. Each row is a dict with at least
    id, title, inputs (dict) and expected. Extra keys are kept for the test body."""
    out = []
    for r in rows:
        meta = {**defaults, **{k: r[k] for k in r if k in FIELDS}}
        meta.setdefault("priority", "P2")
        meta.setdefault("level", "Unit")
        meta.setdefault("type", "Functional")
        meta.setdefault("preconditions", "—")
        meta.setdefault("steps", "Call the unit under test with the inputs")
        meta["inputs"] = _fmt(r.get("inputs", "—"))
        meta["expected"] = _fmt(r.get("expected", "—"))
        out.append(pytest.param(r, id=r["id"], marks=pytest.mark.tc(**meta)))
    return out
