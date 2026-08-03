from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


PROBE = Path(__file__).resolve().parents[1] / "lomx_design_stage0_probe.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("lomx_design_stage0_probe", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_day(symbol: str = "EURUSD") -> pd.DataFrame:
    times = pd.date_range("2020-01-06T00:00:00Z", periods=200, freq="5min")
    phase = np.arange(len(times), dtype=float)
    close = 100.0 + 0.02 * np.sin(phase / 5.0)
    frame = pd.DataFrame(
        {
            "symbol": symbol,
            "timeframe": "M5",
            "time_utc": times,
            "utc_ambiguous": False,
            "open": close,
            "high": close + 0.05,
            "low": close - 0.05,
            "close": close,
            "tick_volume": 10,
        }
    )
    return frame


def test_wilder_atr_is_finite_and_positive_after_seed() -> None:
    probe = load_probe()
    values = probe.wilder_atr(base_day())
    assert np.isnan(values[:13]).all()
    assert np.isfinite(values[13:]).all()
    assert (values[13:] > 0).all()


def test_sweep_reclaim_uses_complete_same_day_asian_range() -> None:
    probe = load_probe()
    frame = base_day()
    signal = frame.index[frame["time_utc"] == pd.Timestamp("2020-01-06T07:00:00Z")][0]
    frame.loc[signal, ["open", "high", "low", "close", "tick_volume"]] = [
        99.93,
        99.97,
        99.88,
        99.935,
        100,
    ]
    candidates, coverage = probe.scan_symbol(frame, "EURUSD")
    sweep = candidates.loc[candidates["engine"] == "ASIAN_RANGE_SWEEP_RECLAIM"]
    assert coverage["complete_asian_dates"] == 1
    assert len(sweep) >= 1
    assert set(sweep["direction"]) <= {-1, 1}
    assert (sweep["initial_risk_price"] > 0).all()

    incomplete = frame.drop(index=0).reset_index(drop=True)
    rejected, coverage = probe.scan_symbol(incomplete, "EURUSD")
    assert coverage["complete_asian_dates"] == 0
    assert rejected.empty


def test_bar_range_compression_breakout_uses_bar2_and_prior_box() -> None:
    probe = load_probe()
    frame = base_day()
    bar2 = frame.index[frame["time_utc"] == pd.Timestamp("2020-01-06T07:05:00Z")][0]
    signal = bar2 + 1
    frame.loc[bar2, ["open", "high", "low", "close"]] = [100.0, 100.005, 99.995, 100.0]
    prior_high = frame.loc[signal - 15 : signal - 1, "high"].max()
    frame.loc[signal, ["open", "high", "low", "close", "tick_volume"]] = [
        prior_high + 0.01,
        prior_high + 0.20,
        prior_high,
        prior_high + 0.18,
        50,
    ]
    candidates, _ = probe.scan_symbol(frame, "EURUSD")
    breakout = candidates.loc[
        candidates["engine"] == "BAR_RANGE_COMPRESSION_BREAKOUT"
    ]
    assert len(breakout) >= 1
    assert 1 in set(breakout["direction"])


def test_combined_metrics_sweep_priority_and_opposing_collision_rejection() -> None:
    probe = load_probe()
    timestamp = pd.Timestamp("2020-01-06T07:05:00Z")
    rows = pd.DataFrame(
        [
            {
                "symbol": "EURUSD",
                "engine": "ASIAN_RANGE_SWEEP_RECLAIM",
                "decision_time_utc": timestamp,
                "direction": 1,
                "decision_close": 1.0,
                "atr14": 0.1,
                "initial_risk_price": 0.2,
                "asian_high": 1.2,
                "asian_low": 0.8,
                "volume_ratio": 2.0,
            },
            {
                "symbol": "EURUSD",
                "engine": "BAR_RANGE_COMPRESSION_BREAKOUT",
                "decision_time_utc": timestamp,
                "direction": 1,
                "decision_close": 1.0,
                "atr14": 0.1,
                "initial_risk_price": 0.2,
                "asian_high": 1.2,
                "asian_low": 0.8,
                "volume_ratio": 2.0,
            },
        ]
    )
    coverage = {
        "active_trading_dates": 1,
        "complete_asian_dates": 1,
        "asian_coverage_ratio": 1.0,
    }
    metrics = probe.combined_metrics(rows, coverage)
    assert metrics["deconflicted_candidate_count"] == 1
    assert metrics["same_bar_overlap_rows_removed"] == 1
    assert metrics["opposing_same_bar_collisions"] == 0

    rows.loc[1, "direction"] = -1
    metrics = probe.combined_metrics(rows, coverage)
    assert metrics["deconflicted_candidate_count"] == 0
    assert metrics["opposing_same_bar_collisions"] == 1


def test_candidate_schema_contains_no_outcome_fields() -> None:
    probe = load_probe()
    forbidden = ("pnl", "profit", "return", "mfe", "mae", "win", "loss", "exit")
    assert not any(any(token in column.lower() for token in forbidden) for column in probe.CANDIDATE_COLUMNS)
