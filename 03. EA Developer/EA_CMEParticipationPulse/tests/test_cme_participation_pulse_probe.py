from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "03. EA Developer" / "EA_CMEParticipationPulse" / "research" / "cme_participation_pulse_offline_probe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cme_participation_pulse_offline_probe", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def source_fixture():
    previous = date(2020, 1, 2)
    current = date(2020, 1, 3)
    publication = date(2020, 1, 6)
    source = {
        previous: {
            "EURUSD": {"open_interest": 100, "total_volume": 10},
            "GBPUSD": {"open_interest": 100, "total_volume": 10},
            "USDJPY": {"open_interest": 100, "total_volume": 10},
        },
        current: {
            "EURUSD": {"open_interest": 105, "total_volume": 10},
            "GBPUSD": {"open_interest": 120, "total_volume": 10},
            "USDJPY": {"open_interest": 95, "total_volume": 10},
        },
    }
    return previous, current, publication, source


def test_selects_largest_positive_oi_change_and_independent_price_control() -> None:
    module = load_module()
    previous, current, publication, source = source_fixture()
    event = module.select_event(
        previous,
        current,
        publication,
        source,
        {"EURUSD": 0.001, "GBPUSD": -0.002, "USDJPY": 1.0},
    )
    assert event is not None
    assert event.candidate_symbol == "GBPUSD"
    assert event.candidate_direction == -1
    assert event.control_symbol == "USDJPY"
    assert event.control_direction == 1


def test_no_positive_oi_expansion_means_no_candidate() -> None:
    module = load_module()
    previous, current, publication, source = source_fixture()
    for symbol in module.SYMBOL_ORDER:
        source[current][symbol]["open_interest"] = 99
    assert module.select_event(
        previous,
        current,
        publication,
        source,
        {"EURUSD": 0.001, "GBPUSD": -0.002, "USDJPY": 1.0},
    ) is None


def test_metrics_use_elapsed_calendar_weeks_and_frozen_risk() -> None:
    module = load_module()
    rows = [
        module.Trade("candidate", "train", "2019-01-02", "2019-01-03", "2019-01-04", "EURUSD", 0.1, 1, "2019-01-04T17:00:00+00:00", "2019-01-04T20:00:00+00:00", 1, 1, 0, 10, "time_exit", 10, 1.0, 0.8, 0.6),
        module.Trade("candidate", "train", "2020-01-02", "2020-01-03", "2020-01-06", "GBPUSD", 0.1, -1, "2020-01-06T17:00:00+00:00", "2020-01-06T20:00:00+00:00", 1, 1, 0, 10, "time_exit", -10, -1.0, -1.2, -1.4),
    ]
    metrics = module.metrics(rows, "train")
    assert metrics["elapsed_calendar_weeks"] > 208
    assert metrics["trades"] == 2
    assert metrics["profit_factor_x1"] == 1.0
    assert metrics["max_drawdown_pct_x1"] > 0


def test_gate_rejects_cadence_or_pf_failure() -> None:
    module = load_module()
    candidate = {
        "trades": 300,
        "trades_per_elapsed_week": 1.9,
        "profit_factor_x1": 1.31,
        "profit_factor_x1_5": 1.25,
        "profit_factor_x2": 1.0,
        "net_r_x1": 5.0,
        "max_drawdown_pct_x1": 2.0,
        "max_positive_year_share": 0.4,
    }
    control = {"profit_factor_x1": 1.1, "net_r_x1": 1.0}
    gates = module.build_gates(candidate, control, "train", 0, 0)
    assert gates["cadence_min_2"] is False
    assert all(value for key, value in gates.items() if key != "cadence_min_2")


def test_source_loader_remains_pre_holdout_and_hash_bound() -> None:
    module = load_module()
    dates, source, profile = module.load_source()
    assert dates[0].year == 2017 and dates[-1].year == 2023
    assert all(year not in module.HOLDOUT_YEARS for year in {day.year for day in dates})
    assert len(dates) == 1763
    assert len(source) == 1763
    assert profile["failures"] == []
