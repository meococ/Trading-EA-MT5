"""Contract tests for the probe SDK (tools/research)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE / "02. AlphaFactory" / "tools" / "research"))

from controls import matched_random_entries, time_shift_entries  # noqa: E402
from indicators import (adx_mt5, atr_mt5, rolling_half_life, rsi_wilder,  # noqa: E402
                        true_range, wilder_rma)
from metrics import (loo_pf, max_dd_r, positive_year_stats, profit_factor,  # noqa: E402
                     top1_win_share)
from sealed_loader import elapsed_weeks, load_sealed_bars, tag_splits  # noqa: E402
from trial_log import append_trial, numpy_safe  # noqa: E402


def test_wilder_rma_seed_and_recursion() -> None:
    r = wilder_rma(pd.Series([1.0, 2, 3, 4, 5, 6]), 3)
    assert abs(r.iloc[2] - 2.0) < 1e-12
    assert abs(r.iloc[3] - (2.0 + (4 - 2.0) / 3)) < 1e-12


def test_rsi_wilder_bounds_and_direction() -> None:
    up = rsi_wilder(pd.Series(np.arange(100, dtype=float)), 14)
    assert up.iloc[-1] > 99.0
    mixed = rsi_wilder(pd.Series(100 + np.sin(np.arange(200) / 3.0)), 14)
    m = mixed.dropna()
    assert ((m >= 0) & (m <= 100)).all()


def test_mt5_variant_semantics() -> None:
    rng = np.random.default_rng(3)
    n = 300
    close = pd.Series(1.10 + np.cumsum(rng.normal(0, 0.001, n)))
    df = pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]),
        "high": close + 0.0005,
        "low": close - 0.0005,
        "close": close,
    })
    # iATR semantics = SIMPLE MA of TR (not Wilder)
    expected = true_range(df).rolling(14).mean()
    assert np.allclose(atr_mt5(df, 14).dropna(), expected.dropna(), atol=1e-15)
    adx = adx_mt5(df, 14).dropna()
    assert ((adx >= 0) & (adx <= 100)).all()
    # strong monotonic trend drives MT5 ADX high
    trend = pd.DataFrame({
        "open": 1.0 + np.arange(200) * 0.001,
        "high": 1.0008 + np.arange(200) * 0.001,
        "low": 0.9998 + np.arange(200) * 0.001,
        "close": 1.0005 + np.arange(200) * 0.001,
    })
    assert adx_mt5(trend, 14).iloc[-1] > 60


def test_half_life_recovers_known_ou() -> None:
    rng = np.random.default_rng(0)
    theta, n = 0.05, 3000
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = x[i - 1] + theta * (0.0 - x[i - 1]) + rng.normal(0, 1.0)
    _, hl = rolling_half_life(pd.Series(x), 300)
    med = np.nanmedian(hl.iloc[500:])
    assert 0.7 * 13.86 < med < 1.3 * 13.86


def test_sealed_loader_blocks_holdout(tmp_path: Path) -> None:
    t = pd.date_range("2022-01-01", periods=100, freq="D")
    df = pd.DataFrame({"time_utc": t, "close": np.arange(100.0)})
    p = tmp_path / "bars.parquet"
    df.to_parquet(p, index=False)
    bars, receipt = load_sealed_bars(p, pd.Timestamp("2022-03-01"))
    assert receipt["holdout_bars_loaded"] == 0
    assert pd.to_datetime(bars["time_utc"]).max() < pd.Timestamp("2022-03-01")
    assert receipt["bars_loaded"] == len(bars) == 59
    assert len(receipt["bars_sha256"]) == 64


def test_tag_splits_and_elapsed_weeks() -> None:
    df = pd.DataFrame({"time_utc": pd.date_range("2021-01-01", periods=10, freq="D")})
    tags = tag_splits(df, {"a": ("2021-01-01", "2021-01-05"), "b": ("2021-01-06", "2021-01-10")})
    assert (tags[:5] == "a").all() and (tags[5:] == "b").all()
    assert abs(elapsed_weeks("2021-01-01", "2021-01-14") - 2.0) < 1e-9


def test_trial_log_requirements_and_numpy(tmp_path: Path) -> None:
    log = tmp_path / "trials.jsonl"
    with pytest.raises(ValueError):
        append_trial(log, {"hypothesis_id": "HYP-X"})
    append_trial(log, {"hypothesis_id": "HYP-X", "prereg_sha256": "A" * 64,
                       "n": np.int64(5), "pf": np.float64(1.5), "ok": np.bool_(True)})
    row = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert row["n"] == 5 and row["pf"] == 1.5 and row["ok"] is True
    with pytest.raises(TypeError):
        numpy_safe(object())


def test_metrics_known_values() -> None:
    vals = [2.0, -1.0, 1.0, -1.0]
    assert abs(profit_factor(vals) - 1.5) < 1e-12
    assert abs(max_dd_r([1.0, -2.0, 0.5]) - 2.0) < 1e-12
    assert abs(top1_win_share(vals) - 2.0 / 3.0) < 1e-12
    assert abs(loo_pf(vals) - 0.5) < 1e-12
    n_pos, share = positive_year_stats({"2020": 5.0, "2021": -1.0, "2022": 5.0})
    assert n_pos == 2 and abs(share - 0.5) < 1e-12


def test_controls_deterministic_and_masked() -> None:
    times = pd.Series(pd.date_range("2021-01-01", periods=1000, freq="h"))
    mask = times.dt.hour.between(7, 15)
    a = matched_random_entries(times, 50, seed=7, mask=mask)
    b = matched_random_entries(times, 50, seed=7, mask=mask)
    assert a.equals(b) and len(a) == 50
    assert a.dt.hour.between(7, 15).all()
    shifted = time_shift_entries(a.head(5), times, shift_bars=24)
    assert len(shifted) == 5
    assert (pd.to_datetime(shifted.iloc[0]) - pd.to_datetime(a.iloc[0])).total_seconds() == 24 * 3600
