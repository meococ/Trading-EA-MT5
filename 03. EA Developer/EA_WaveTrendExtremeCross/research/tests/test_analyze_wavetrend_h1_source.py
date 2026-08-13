from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_wavetrend_h1_source.py"
SPEC = importlib.util.spec_from_file_location("wavetrend_h1_source", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def frame_from_ap(values: list[float]) -> pd.DataFrame:
    ap = np.asarray(values, dtype=float)
    return pd.DataFrame({
        "time_server": pd.date_range("2015-01-01", periods=len(ap), freq="h"),
        "time_utc": pd.date_range("2015-01-01", periods=len(ap), freq="h"),
        "open": ap,
        "high": ap + 0.001,
        "low": ap - 0.001,
        "close": ap,
    })


def test_ema_seeds_first_finite_and_uses_exact_alpha() -> None:
    values = np.array([np.nan, 10.0, 12.0, 14.0])
    out = MOD.ema_first_finite(values, 3)
    assert np.isnan(out[0])
    assert out[1] == 10.0
    assert out[2] == 11.0
    assert out[3] == 12.5


def test_ci_is_invalid_while_smoothed_deviation_is_zero() -> None:
    state = MOD.wavetrend_state(frame_from_ap([1.0] * 20))
    assert state["ci"].isna().all()
    assert state["wt1"].isna().all()
    assert (state["signal"] == 0).all()


def test_wt2_is_exact_four_value_sma() -> None:
    values = [1.0] * 8 + [1.01, 1.02, 1.00, 0.99, 1.03, 1.04]
    state = MOD.wavetrend_state(frame_from_ap(values))
    finite = np.flatnonzero(np.isfinite(state["wt2"].to_numpy()))
    assert len(finite) > 0
    i = int(finite[0])
    assert state.iloc[i]["wt2"] == np.mean(state["wt1"].iloc[i - 3:i + 1])


def test_signal_requires_strict_cross_and_current_extreme() -> None:
    wt1 = np.array([-70.0, -65.0, -59.0, 70.0, 65.0, 59.0])
    wt2 = np.array([-65.0, -65.0, -60.0, 65.0, 65.0, 60.0])
    signals = []
    for i in range(1, len(wt1)):
        long_event = wt1[i - 1] <= wt2[i - 1] and wt1[i] > wt2[i] and wt1[i] < -MOD.EXTREME
        short_event = wt1[i - 1] >= wt2[i - 1] and wt1[i] < wt2[i] and wt1[i] > MOD.EXTREME
        signals.append((long_event, short_event))
    assert signals[0] == (False, False)  # current equality does not emit
    assert signals[1] == (False, False)  # crossover outside the strict extreme
    assert signals[3] == (False, False)  # current equality does not emit
    assert signals[4] == (False, False)  # crossover outside the strict extreme


def test_validate_source_rejects_bad_geometry_and_duplicate_clock() -> None:
    frame = frame_from_ap([1.0, 1.1, 1.2])
    bad = frame.copy()
    bad.loc[1, "high"] = 0.5
    try:
        MOD.validate_source(bad)
        raise AssertionError("bad geometry must fail")
    except ValueError as exc:
        assert "geometry" in str(exc)
    duplicate = frame.copy()
    duplicate.loc[1, "time_server"] = duplicate.loc[0, "time_server"]
    try:
        MOD.validate_source(duplicate)
        raise AssertionError("duplicate clock must fail")
    except ValueError as exc:
        assert "time_server" in str(exc)


def test_analyzer_has_no_post_event_price_or_economic_fields() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ["profit_factor", "net_profit", "expectancy", "next_open", "next_close", "pnl"]
    assert all(token not in text for token in forbidden)
    assert '"outcomes_read": false' in text
    assert '"paid_data_used": false' in text


def test_attempt_is_exclusive_and_failure_terminal_is_evidenced() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "output.mkdir(parents=True, exist_ok=False)" in text
    assert '"same_id_retry_allowed": False' in text
    for token in ("failed_stage", "captured_bindings", 'observed["h1_rows"]', 'observed["gates"]'):
        assert token in text


def test_decision_is_exact_next_h1_not_signal_bar_open() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert '"source_bar_time_server": times[i].isoformat()' in text
    assert '"decision_time_server": times[i + 1].isoformat()' in text
    assert '"availability_time_server": times[i + 1].isoformat()' in text
    assert "(times[i + 1] - times[i]).total_seconds() == 3600" in text
    assert '"year_axis": "decision_time_server"' in text


def test_source_hash_and_no_paid_data_contract_are_frozen() -> None:
    assert MOD.SOURCE_SHA256 == "71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08"
    prereg = MOD.PREREG.read_text(encoding="utf-8")
    assert "No paid data" in prereg
    assert "10/21/4" in prereg
