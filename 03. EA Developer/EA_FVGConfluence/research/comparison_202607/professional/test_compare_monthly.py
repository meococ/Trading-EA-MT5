from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PATH = Path(__file__).with_name("compare_monthly.py")
SPEC = importlib.util.spec_from_file_location("compare_monthly", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def series(offset: float = 0.0) -> dict[str, float]:
    result = {}
    year, month = 2020, 1
    for index in range(48):
        result[f"{year:04d}-{month:02d}"] = (0.01 if index % 2 == 0 else -0.005) + offset
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def test_normalization_is_lagged_and_capped() -> None:
    raw = series()
    normalized = MODULE.lagged_vol_normalize(raw)
    assert len(normalized) == 36
    assert list(normalized)[0] == "2021-01"
    assert normalized["2021-01"] <= raw["2021-01"] * 2.0 + 1e-12


def test_comparison_refuses_small_peer_cohort() -> None:
    payload = {
        "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
        "ea": {"monthly_returns": series()},
        "peers": [{"monthly_returns": series()}] * 4,
    }
    with pytest.raises(MODULE.ComparisonError, match="at least five"):
        MODULE.compare(payload)


def test_comparison_is_seed_reproducible() -> None:
    payload = {
        "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
        "seed": 7,
        "bootstrap_reps": 200,
        "ea_workspace_pf_cost_cadence_gates_passed": True,
        "ea": {"monthly_returns": series(0.002)},
        "peers": [{"monthly_returns": series(index * 0.0001)} for index in range(5)],
    }
    first = MODULE.compare(payload)
    second = MODULE.compare(payload)
    assert first == second
    assert first["peer_count"] == 5

