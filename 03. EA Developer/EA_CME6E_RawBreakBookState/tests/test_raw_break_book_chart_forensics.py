from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "analyze_raw_break_book_chart_forensics.py"
CORRECTION_PATH = PACKAGE / "research" / "render_raw_break_book_clock_corrected_charts.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_raw_break_book_chart_forensics", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_correction_module():
    spec = importlib.util.spec_from_file_location("render_raw_break_book_clock_corrected_charts", CORRECTION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_population() -> pd.DataFrame:
    rows = []
    for direction_index, direction in enumerate(("BUY", "SELL")):
        for index in range(12):
            win = index % 3 == 0
            realized_r = 2.0 + index / 100 if win else -1.0 - index / 100
            rows.append(
                {
                    "position_id": str(direction_index * 100 + index + 1),
                    "direction": direction,
                    "book_alignment_score": -0.2 + index * 0.04,
                    "realized_r": realized_r,
                    "net": 20.0 if win else -10.0,
                    "stop_pips": 3.0 + index / 10,
                    "volume": 0.2,
                    "entry_minute_utc": 60 + index * 5,
                }
            )
    return pd.DataFrame(rows)


def test_frozen_sampling_selects_twelve_unique_declared_strata() -> None:
    module = load_module()
    selected = module.select_cases(synthetic_population())

    assert len(selected) == 12
    assert selected["position_id"].nunique() == 12
    assert selected["stratum"].value_counts().to_dict() == {
        "EXTREME_WIN": 2,
        "EXTREME_LOSS": 2,
        "MEDIAN_WIN": 2,
        "MEDIAN_LOSS": 2,
        "MATCHED_BUY_WIN": 1,
        "MATCHED_BUY_LOSS": 1,
        "MATCHED_SELL_WIN": 1,
        "MATCHED_SELL_LOSS": 1,
    }


def test_exit_classification_uses_planned_geometry() -> None:
    module = load_module()
    buy_tp = {"direction": "BUY", "exit": 1.10201, "planned_stop": 1.099, "planned_target": 1.102}
    sell_sl = {"direction": "SELL", "exit": 1.10101, "planned_stop": 1.101, "planned_target": 1.098}

    assert module.classify_exit(buy_tp) == "TP_LIKE"
    assert module.classify_exit(sell_sl) == "SL_LIKE"


def test_population_metrics_report_realized_payoff_and_breakeven_win_rate() -> None:
    module = load_module()
    rows = pd.DataFrame(
        [
            {"net": 20.0, "realized_r": 2.0},
            {"net": -10.0, "realized_r": -1.0},
            {"net": -10.0, "realized_r": -1.0},
        ]
    )

    metrics = module.basic_metrics(rows)

    assert metrics["profit_factor"] == pytest.approx(1.0)
    assert metrics["average_win"] == pytest.approx(20.0)
    assert metrics["average_loss_abs"] == pytest.approx(10.0)
    assert metrics["realized_payoff_ratio"] == pytest.approx(2.0)
    assert metrics["implied_breakeven_win_rate"] == pytest.approx(1.0 / 3.0)


def test_m1_path_geometry_is_direction_aligned() -> None:
    module = load_module()
    bars = pd.DataFrame(
        {
            "high": [1.1010, 1.1020],
            "low": [1.0995, 1.0990],
            "close": [1.1005, 1.1015],
        }
    )

    buy = module.path_geometry(bars, direction="BUY", entry=1.1000, risk_price=0.0010)
    sell = module.path_geometry(bars, direction="SELL", entry=1.1000, risk_price=0.0010)

    assert buy["mfe_r"] == pytest.approx(2.0)
    assert buy["mae_r"] == pytest.approx(1.0)
    assert sell["mfe_r"] == pytest.approx(1.0)
    assert sell["mae_r"] == pytest.approx(2.0)


def test_clock_correction_separates_feature_cutoff_from_actual_decision() -> None:
    module = load_correction_module()
    semantics = module.clock_semantics(
        {
            "decision_time_utc": "2019-01-03 00:15:00",
            "entry_time_utc": "2019-01-03 00:20:00",
        }
    )

    assert semantics["feature_cutoff_role"] == "BREAK_BAR_OPEN"
    assert semantics["actual_closed_bar_decision_role"] == "NEXT_BAR_OPEN_ENTRY"
    assert semantics["feature_cutoff_to_actual_decision_seconds"] == pytest.approx(300.0)
