from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "probe_raw_break_book_state_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location("probe_raw_break_book_state_design", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def feature(position_id: str, direction: str, end: str, score: float, eligible: bool = True):
    return {
        "position_id": position_id,
        "direction": direction,
        "end": end,
        "book_alignment_score": str(score),
        "quality_eligible": str(eligible),
        "quality_reason": "PASS" if eligible else "SOURCE_EMPTY",
    }


def outcome(position_id: str, direction: str, decision_time: str, net: float, realized_r: float):
    return {
        "position_id": position_id,
        "direction": direction,
        "decision_time": decision_time,
        "volume": "0.20",
        "net": str(net),
        "realized_r": str(realized_r),
        "initial_risk_account": "10.0",
    }


def test_join_requires_position_clock_and_direction_identity() -> None:
    module = load_module()

    def fixed_clock(value: datetime) -> datetime:
        return value.replace(hour=value.hour - 2)

    features = [feature("7", "BUY", "2019-01-03T00:15:00Z", 0.1)]
    outcomes = [outcome("7", "BUY", "2019.01.03 02:15:00", 10.0, 1.0)]

    joined = module.join_design_rows(features, outcomes, fixed_clock)
    assert joined[0]["decision_time_utc"] == "2019-01-03T00:15:00Z"
    assert joined[0]["net"] == pytest.approx(10.0)

    with pytest.raises(module.ProbeError, match="direction mismatch"):
        module.join_design_rows(features, [{**outcomes[0], "direction": "SELL"}], fixed_clock)


def test_profit_factor_and_fixed_round_trip_stress() -> None:
    module = load_module()
    rows = [
        {"net": 20.0, "realized_r": 2.0, "volume": 0.2, "direction": "BUY", "decision_year": 2019},
        {"net": -10.0, "realized_r": -1.0, "volume": 0.2, "direction": "SELL", "decision_year": 2020},
    ]

    metrics = module.arm_metrics(rows, elapsed_weeks=1.0)

    assert metrics["native"]["profit_factor"] == pytest.approx(2.0)
    assert metrics["native"]["mean_realized_r"] == pytest.approx(0.5)
    assert metrics["cost_stress"]["1.5"]["profit_factor"] == pytest.approx(17.0 / 13.0)
    assert metrics["cadence_per_elapsed_week"] == pytest.approx(2.0)


def test_frozen_median_population_uses_ties_on_challenger_side() -> None:
    module = load_module()
    rows = [
        {"quality_eligible": True, "book_alignment_score": -1.0},
        {"quality_eligible": True, "book_alignment_score": 0.0},
        {"quality_eligible": True, "book_alignment_score": 0.0},
        {"quality_eligible": False, "book_alignment_score": 9.0},
    ]

    populations = module.select_frozen_populations(rows, threshold=0.0)

    assert len(populations["CONTROL_QUALITY_ELIGIBLE"]) == 3
    assert len(populations["CHALLENGER_TOP50_SCORE"]) == 2
    assert len(populations["NEGATIVE_CONTROL_BOTTOM50_SCORE"]) == 1


def test_gate_verdict_kills_any_valid_economic_failure() -> None:
    module = load_module()
    control = {"native": {"profit_factor": 1.20, "mean_realized_r": 0.02}}
    bottom = {"native": {"profit_factor": 1.10, "mean_realized_r": 0.01}}
    challenger = {
        "count": 230,
        "cadence_per_elapsed_week": 2.2,
        "native": {"profit_factor": 1.29, "mean_realized_r": 0.10},
        "cost_stress": {"1.5": {"profit_factor": 1.30}, "2.25": {"profit_factor": 1.05}},
        "by_year": {
            "2019": {"profit_factor": 1.1, "mean_realized_r": 0.1},
            "2020": {"profit_factor": 1.1, "mean_realized_r": 0.1},
        },
        "by_direction": {
            "BUY": {"profit_factor": 1.1, "mean_realized_r": 0.1},
            "SELL": {"profit_factor": 1.1, "mean_realized_r": 0.1},
        },
    }

    result = module.evaluate_gates(control, challenger, bottom, dsr_value=0.99, integrity_pass=True)

    assert result["verdict"] == "KILL_DESIGN_BOOK_ALIGNMENT_NO_POSITIVE_EXPECTANCY"
    assert result["gates"]["native_pf_gte_1_30"] is False


def test_integrity_failure_parks_without_market_verdict() -> None:
    module = load_module()
    result = module.evaluate_gates({}, {}, {}, dsr_value=0.0, integrity_pass=False)
    assert result["verdict"] == "PARK_INVALID_BOOK_FEATURE_OR_JOIN"

