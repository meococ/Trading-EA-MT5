from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_follow_line_source.py"
SPEC = importlib.util.spec_from_file_location("follow_line_source", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def bars_from_close(close: list[float]) -> pd.DataFrame:
    c = np.asarray(close, dtype=float)
    return pd.DataFrame({
        "time_server": pd.date_range("2015-01-01", periods=len(c), freq="15min"),
        "open": c,
        "high": c + 0.0005,
        "low": c - 0.0005,
        "close": c,
    })


def test_wilder_atr_sma_seed_then_rma() -> None:
    high = np.array([2, 3, 4, 5, 6, 7], dtype=float)
    low = np.array([1, 2, 3, 4, 5, 6], dtype=float)
    close = np.array([1.5, 2.5, 3.5, 4.5, 5.5, 6.5], dtype=float)
    out = MOD.wilder_atr(high, low, close, 5)
    assert np.isnan(out[:4]).all()
    assert out[4] == 1.4
    assert out[5] == 1.42


def test_population_standard_deviation_is_frozen() -> None:
    bars = bars_from_close([1.0] * 20 + [2.0])
    state = MOD.follow_line_state(bars)
    expected = np.std(np.array([1.0] * 20 + [2.0]), ddof=0)
    assert state.iloc[-1]["sigma"] == expected


def test_inside_band_retains_line_and_trend() -> None:
    bars = bars_from_close([1.0] * 30)
    state = MOD.follow_line_state(bars)
    assert state["follow_line"].isna().all()
    assert (state["trend"] == 0).all()
    assert (state["signal"] == 0).all()


def test_first_long_state_is_symmetric_initialization_not_event() -> None:
    close = [1.0] * 24 + [1.02] + [1.02] * 5
    state = MOD.follow_line_state(bars_from_close(close))
    first_trend = np.flatnonzero(state["trend"].to_numpy() != 0)
    assert len(first_trend) > 0
    assert state.iloc[first_trend[0]]["trend"] == 1
    assert state.iloc[first_trend[0]]["signal"] == 0


def test_first_short_state_is_symmetric_initialization_not_event() -> None:
    close = [1.0] * 24 + [0.98] + [0.98] * 5
    state = MOD.follow_line_state(bars_from_close(close))
    first_trend = np.flatnonzero(state["trend"].to_numpy() != 0)
    assert len(first_trend) > 0
    assert state.iloc[first_trend[0]]["trend"] == -1
    assert state.iloc[first_trend[0]]["signal"] == 0


def test_signal_requires_exact_trend_flip() -> None:
    close = [1.0] * 24 + [1.02] + [1.02] * 4 + [0.98] + [0.98] * 4 + [1.03]
    state = MOD.follow_line_state(bars_from_close(close))
    for i, sig in enumerate(state["signal"].to_numpy()):
        if sig == 1:
            assert state.iloc[i - 1]["trend"] == -1
            assert state.iloc[i]["trend"] == 1
        elif sig == -1:
            assert state.iloc[i - 1]["trend"] == 1
            assert state.iloc[i]["trend"] == -1


def test_analyzer_contains_no_economic_or_next_price_fields() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = ["profit_factor", "net_profit", "expectancy", "next_close", "next_open", "pnl"]
    assert all(token not in text.lower() for token in forbidden)
    assert '"economic_fields_read": False' in text


def test_attempt_is_exclusive_and_no_same_id_retry() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "output.mkdir(parents=True, exist_ok=False)" in text
    assert '"same_id_retry_allowed": False' in text
    assert "bound input changed during attempt" in text


def test_failure_terminal_preserves_stage_bindings_counts_and_gates() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    for token in ("failed_stage", "captured_bindings", 'observed["m1_rows"]',
                  'observed["m15_rows"]', 'observed["gates"]'):
        assert token in text


def test_ledger_separates_decision_and_exact_next_availability() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert '"decision_time_server": times[i].isoformat()' in text
    assert '"availability_time_server": times[i + 1].isoformat()' in text
    assert '"year_axis": "decision_time_server"' in text
    assert "(times[i + 1] - times[i]).total_seconds() == 900" in text
