from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "probe_cme6e_breakbar_transition_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "probe_cme6e_breakbar_transition_design", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def feature(
    position_id: str,
    direction: str,
    break_bar_open: str,
    actual_decision: str,
    score: float,
    eligible: bool = True,
):
    return {
        "position_id": position_id,
        "direction": direction,
        "break_bar_open": break_bar_open,
        "actual_decision": actual_decision,
        "book_transition_score": score,
        "quality_eligible": eligible,
        "quality_reason": "PASS" if eligible else "METADATA_EMPTY",
    }


def outcome(
    position_id: str,
    direction: str,
    decision_time: str,
    open_time: str,
    net: float,
    realized_r: float,
):
    return {
        "position_id": position_id,
        "direction": direction,
        "decision_time": decision_time,
        "open_time": open_time,
        "volume": "0.20",
        "net": str(net),
        "realized_r": str(realized_r),
        "initial_risk_account": "10.0",
    }


def test_join_binds_break_bar_and_actual_entry_clocks() -> None:
    module = load_module()

    def fixed_clock(value: datetime) -> datetime:
        return value - timedelta(hours=2)

    features = [
        feature(
            "1096",
            "BUY",
            "2021-01-03T23:30:00Z",
            "2021-01-03T23:35:00Z",
            0.10,
        )
    ]
    outcomes = [
        outcome(
            "1096",
            "BUY",
            "2021.01.04 01:30:00",
            "2021.01.04 01:35:00",
            10.0,
            1.0,
        )
    ]

    joined = module.join_design_rows(features, outcomes, fixed_clock)
    assert joined[0]["break_bar_open_utc"] == "2021-01-03T23:30:00Z"
    assert joined[0]["actual_decision_utc"] == "2021-01-03T23:35:00Z"
    assert joined[0]["net"] == pytest.approx(10.0)

    with pytest.raises(module.ProbeError, match="entry clock mismatch"):
        module.join_design_rows(
            features,
            [{**outcomes[0], "open_time": "2021.01.04 01:40:00"}],
            fixed_clock,
        )


def test_frozen_median_population_uses_ties_on_challenger_side() -> None:
    module = load_module()
    rows = [
        {"quality_eligible": True, "book_transition_score": -1.0},
        {"quality_eligible": True, "book_transition_score": 0.0},
        {"quality_eligible": True, "book_transition_score": 0.0},
        {"quality_eligible": False, "book_transition_score": 9.0},
    ]

    populations = module.select_frozen_populations(rows, threshold=0.0)

    assert len(populations["CONTROL_QUALITY_ELIGIBLE"]) == 3
    assert len(populations["CHALLENGER_TOP50_TRANSITION_SCORE"]) == 2
    assert len(populations["NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE"]) == 1


def test_fixed_round_trip_stress_and_design_buckets() -> None:
    module = load_module()
    rows = [
        {
            "net": 20.0,
            "realized_r": 2.0,
            "volume": 0.2,
            "direction": "BUY",
            "decision_year": 2021,
        },
        {
            "net": -10.0,
            "realized_r": -1.0,
            "volume": 0.2,
            "direction": "SELL",
            "decision_year": 2022,
        },
    ]

    metrics = module.arm_metrics(rows, elapsed_weeks=1.0)

    assert metrics["native"]["profit_factor"] == pytest.approx(2.0)
    assert metrics["native"]["mean_realized_r"] == pytest.approx(0.5)
    assert metrics["cost_stress"]["1.5"]["profit_factor"] == pytest.approx(17.0 / 13.0)
    assert metrics["by_year"]["2021"]["count"] == 1
    assert metrics["by_year"]["2022"]["count"] == 1


def test_any_valid_economic_failure_kills_only_hyp002() -> None:
    module = load_module()
    control = {"native": {"profit_factor": 1.20, "mean_realized_r": 0.02}}
    bottom = {"native": {"profit_factor": 1.10, "mean_realized_r": 0.01}}
    challenger = {
        "count": 258,
        "cadence_per_elapsed_week": 2.477,
        "native": {"profit_factor": 1.29, "mean_realized_r": 0.10},
        "cost_stress": {
            "1.5": {"profit_factor": 1.30},
            "2.25": {"profit_factor": 1.05},
        },
        "by_year": {
            "2021": {"profit_factor": 1.1, "mean_realized_r": 0.1},
            "2022": {"profit_factor": 1.1, "mean_realized_r": 0.1},
        },
        "by_direction": {
            "BUY": {"profit_factor": 1.1, "mean_realized_r": 0.1},
            "SELL": {"profit_factor": 1.1, "mean_realized_r": 0.1},
        },
    }

    result = module.evaluate_gates(
        control, challenger, bottom, dsr_value=0.99, integrity_pass=True
    )

    assert result["verdict"] == (
        "KILL_DESIGN_BREAKBAR_BOOK_TRANSITION_NO_POSITIVE_EXPECTANCY"
    )
    assert result["gates"]["native_pf_gte_1_30"] is False


def test_integrity_failure_parks_without_market_verdict() -> None:
    module = load_module()
    result = module.evaluate_gates({}, {}, {}, dsr_value=0.0, integrity_pass=False)
    assert result["verdict"] == "PARK_INVALID_BREAKBAR_BOOK_FEATURE_OR_JOIN"
