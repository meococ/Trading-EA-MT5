from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RUNNER_PATH = (
    Path(__file__).resolve().parents[3]
    / "02. AlphaFactory"
    / "tools"
    / "research"
    / "empirical_probe_runner.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("empirical_probe_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_select_symbol_never_uses_another_symbols_tail():
    mod = load_runner()
    frame = pd.DataFrame(
        {
            "symbol": ["EURJPY"] * 4 + ["USDJPY"] * 4,
            "time_utc": pd.date_range("2020-01-01", periods=8, freq="min"),
            "close": [120.0, 120.1, 120.2, 120.3, 100.0, 100.1, 100.2, 100.3],
        }
    )

    selected = mod.select_symbol(frame, "EURJPY")

    assert len(selected) == 4
    assert selected["symbol"].eq("EURJPY").all()
    assert selected["close"].min() > 119.0


def test_select_symbol_rejects_missing_or_mixed_identity():
    mod = load_runner()
    missing_column = pd.DataFrame({"close": [1.0, 2.0]})
    with pytest.raises(RuntimeError, match="MISSING SYMBOL COLUMN"):
        mod.select_symbol(missing_column, "EURJPY")

    frame = pd.DataFrame(
        {"symbol": ["USDJPY"], "time_utc": ["2020-01-01T00:00:00Z"], "close": [100.0]}
    )
    with pytest.raises(RuntimeError, match="SYMBOL NOT FOUND"):
        mod.select_symbol(frame, "EURJPY")


def test_daily_sessions_do_not_stitch_across_dates_or_gaps():
    mod = load_runner()
    first = pd.date_range("2020-01-02 00:00", periods=6, freq="min", tz="UTC")
    second = pd.date_range("2020-01-03 00:00", periods=6, freq="min", tz="UTC")
    broken = list(pd.date_range("2020-01-04 00:00", periods=3, freq="min", tz="UTC"))
    broken += list(pd.date_range("2020-01-04 00:05", periods=3, freq="min", tz="UTC"))
    times = list(first) + list(second) + broken
    frame = pd.DataFrame(
        {
            "symbol": ["EURJPY"] * len(times),
            "time_utc": times,
            "close": np.linspace(120.0, 121.0, len(times)),
        }
    )

    sessions = mod.contiguous_daily_sessions(
        frame, start_hour=0, end_hour=6, min_rows=6
    )

    assert len(sessions) == 2
    assert all(len(session) == 6 for session in sessions)
    assert all(session["time_utc"].dt.date.nunique() == 1 for session in sessions)


def test_true_flow_contract_rejects_ohlc_and_tick_volume_proxy():
    mod = load_runner()

    blocked = mod.inspect_flow_contract(
        {"time_utc", "open", "high", "low", "close", "tick_volume", "real_volume"}
    )
    available = mod.inspect_flow_contract(
        {
            "time_utc",
            "trade_side",
            "trade_volume",
            "bid_size",
            "ask_size",
        }
    )

    assert blocked["all_required_available"] is False
    assert blocked["vpin_cvd_available"] is False
    assert blocked["lob_ofi_available"] is False
    assert available["all_required_available"] is True


def test_ou_calibration_uses_ar1_half_life_and_guards_invalid_b():
    mod = load_runner()
    rng = np.random.default_rng(7)
    values = [10.0]
    for _ in range(3000):
        values.append(1.0 + 0.8 * values[-1] + rng.normal(0.0, 0.05))

    valid = mod.calibrate_ou_process(np.asarray(values[-1500:]), dt=1.0)
    invalid = mod.calibrate_ou_process(np.arange(100.0), dt=1.0)

    assert valid["valid"] is True
    assert valid["b"] == pytest.approx(0.8, abs=0.04)
    assert valid["half_life"] == pytest.approx(-np.log(2.0) / np.log(valid["b"]))
    assert invalid["valid"] is False
    assert invalid["half_life"] is None


def test_any_p0_blocker_denies_ea_build_and_mt5():
    mod = load_runner()

    result = mod.evaluate_preflight(
        identity_ok=False,
        coverage_ok=False,
        target_evidence_ok=False,
        flow_contract_ok=False,
        estimator_contract_ok=False,
        async_kernel_ready=False,
    )

    assert result["verdict"] == (
        "PARK_PRE_EA_INVALID_PLAN_EVIDENCE_OR_CAPABILITY_NO_OUTCOME_READ"
    )
    assert result["authority"]["mql5_build_authorized"] is False
    assert result["authority"]["mt5_authorized"] is False
    assert result["authority"]["economics_authorized"] is False
    assert len(result["blockers"]) == 6
