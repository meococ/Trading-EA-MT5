from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "probe_usdjpy_m5_001.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("probe_usdjpy_m5_001", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_wrapping_session_is_kept_together_without_gap_stitching():
    mod = load_module()
    good = pd.date_range("2020-01-02 22:15", periods=87, freq="5min", tz="UTC")
    broken = list(pd.date_range("2020-01-03 22:15", periods=40, freq="5min", tz="UTC"))
    broken += list(pd.date_range("2020-01-04 02:00", periods=47, freq="5min", tz="UTC"))
    times = list(good) + broken
    frame = pd.DataFrame({"time_utc": times, "close": np.linspace(108.0, 109.0, len(times))})

    sessions = mod.extract_sessions(frame, min_rows=80)

    assert len(sessions) == 1
    assert sessions[0]["time_utc"].iloc[0] == good[0]
    assert sessions[0]["time_utc"].iloc[-1] == good[-1]


def test_ou_half_life_recovers_stationary_ar1_and_rejects_unit_root():
    mod = load_module()
    rng = np.random.default_rng(17)
    values = [100.0]
    for _ in range(5000):
        values.append(20.0 + 0.8 * values[-1] + rng.normal(0.0, 0.2))

    valid = mod.calibrate_ou(np.asarray(values[-1000:]))
    invalid = mod.calibrate_ou(np.arange(100.0))

    assert valid["valid"] is True
    assert valid["b"] == pytest.approx(0.8, abs=0.04)
    assert valid["half_life_m5_bars"] == pytest.approx(-np.log(2.0) / np.log(valid["b"]))
    assert invalid["valid"] is False


def test_frozen_gates_fail_closed():
    mod = load_module()
    passing_ci = {"median": 0.45, "lower_95": 0.43, "upper_95": 0.47}
    vr_ci = {"median": 0.90, "lower_95": 0.88, "upper_95": 0.92}
    hl_ci = {"median": 18.0, "lower_95": 14.0, "upper_95": 22.0}
    yearly = {str(year): 220 for year in range(2016, 2021)}

    passed = mod.evaluate_gates(
        session_count=1100,
        yearly_counts=yearly,
        hurst_ci=passing_ci,
        vr_ci=vr_ci,
        ou_valid_lower=0.70,
        half_life_ci=hl_ci,
    )
    failed = mod.evaluate_gates(
        session_count=999,
        yearly_counts=yearly,
        hurst_ci=passing_ci,
        vr_ci=vr_ci,
        ou_valid_lower=0.70,
        half_life_ci=hl_ci,
    )

    assert all(passed.values())
    assert failed["session_count_ge_1000"] is False


def test_bootstrap_is_deterministic_for_frozen_seed():
    mod = load_module()
    values = np.linspace(0.4, 0.6, 50)

    first = mod.bootstrap_median_interval(values, np.random.default_rng(20260802), reps=500)
    second = mod.bootstrap_median_interval(values, np.random.default_rng(20260802), reps=500)

    assert first == second
