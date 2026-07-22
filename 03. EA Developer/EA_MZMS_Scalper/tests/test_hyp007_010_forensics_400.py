"""Focused tests for HYP-007..010 400-case visual forensics builder."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
BUILDER = (
    ROOT
    / "03. EA Developer"
    / "EA_MZMS_Scalper"
    / "research"
    / "build_hyp007_010_grok_forensics_400.py"
)


def load_builder():
    spec = importlib.util.spec_from_file_location("hyp007_010_forensics400", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def B():
    return load_builder()


def test_expected_run_mapping_and_targets(B):
    assert list(B.RUNS) == [
        "HYP-MZMS-XAU-M5-007",
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]
    assert B.RUNS["HYP-MZMS-XAU-M5-007"]["run_id"] == "20260722_015121"
    assert B.RUNS["HYP-MZMS-XAU-M5-008"]["run_id"] == "20260722_021353"
    assert B.RUNS["HYP-MZMS-XAU-M5-009"]["run_id"] == "20260722_023841"
    assert B.RUNS["HYP-MZMS-XAU-M5-010"]["run_id"] == "20260722_024229"
    assert B.RUNS["HYP-MZMS-XAU-M5-007"]["executed_target"] == 100
    assert B.RUNS["HYP-MZMS-XAU-M5-007"]["near_miss_target"] == 0
    assert B.RUNS["HYP-MZMS-XAU-M5-008"]["executed_target"] == 80
    assert B.RUNS["HYP-MZMS-XAU-M5-008"]["near_miss_target"] == 20
    assert B.RUNS["HYP-MZMS-XAU-M5-009"]["executed_target"] == 100
    assert B.RUNS["HYP-MZMS-XAU-M5-009"]["near_miss_target"] == 0
    assert B.RUNS["HYP-MZMS-XAU-M5-010"]["executed_target"] == 2
    assert B.RUNS["HYP-MZMS-XAU-M5-010"]["near_miss_target"] == 98


def test_bars_source_sha_constant(B):
    assert B.EXPECTED_BARS_SHA == (
        "8D4FEEFDE69D130F80C8DA630E65178C8F48087FD392E3A6F339B57770D2A3CC"
    )
    assert B.BARS_SOURCE.exists()
    assert B.sha256_file(B.BARS_SOURCE) == B.EXPECTED_BARS_SHA


def test_seed_deterministic(B):
    a = B.seed_for("HYP-MZMS-XAU-M5-007", "20260722_015121")
    b = B.seed_for("HYP-MZMS-XAU-M5-007", "20260722_015121")
    c = B.seed_for("HYP-MZMS-XAU-M5-008", "20260722_021353")
    assert a == b
    assert a != c


def _synthetic_positions(n: int = 40):
    rows = []
    for i in range(n):
        net = 1.0 if i % 2 == 0 else -1.0
        if i % 11 == 0:
            net = -1.2
        entry = datetime(2019 + (i % 6), 1 + (i % 9), 2, 10, 0, 0)
        rows.append(
            {
                "position_id": i + 1,
                "direction": 1 if i % 3 else -1,
                "side": "BUY" if i % 3 else "SELL",
                "entry_time_server": entry.strftime("%Y.%m.%d %H:%M:%S"),
                "entry_time": entry,
                "entry": 1800.0 + i,
                "exit_time_server": entry.strftime("%Y.%m.%d %H:%M:%S"),
                "exit_time": entry,
                "exit": 1801.0 + i,
                "risk_pts": 100.0,
                "initial_risk_account": 10.0,
                "net_usd": net,
                "net_R": net / 10.0,
                "sl": 1790.0,
                "tp": 1816.0,
                "hold_minutes": 5.0 if i % 11 == 0 else 40.0,
                "year": entry.year,
                "outcome_label": "WINNER" if net > 0 else "LOSER",
            }
        )
    return rows


def test_stratified_sample_size_and_uniqueness(B):
    positions = _synthetic_positions(80)
    sample = B.stratified_executed_sample(positions, 30, seed=123, take_all_if_leq=False)
    assert len(sample) == 30
    ids = [p["position_id"] for p in sample]
    assert len(ids) == len(set(ids))
    assert all(p["case_kind"] == "EXECUTED" for p in sample)


def test_stratified_take_all_when_small(B):
    positions = _synthetic_positions(12)
    sample = B.stratified_executed_sample(positions, 100, seed=1, take_all_if_leq=True)
    assert len(sample) == 12


def test_profit_factor(B):
    assert abs(B.profit_factor([2.0, -1.0]) - 2.0) < 1e-12
    assert B.profit_factor([1.0, 2.0]) == float("inf")
    assert B.profit_factor([-1.0, -2.0]) == 0.0


def test_gate_eval_010_synthetic(B):
    n = 80
    idx = np.arange(n)
    close = 1800 + np.cumsum(np.sin(idx / 5.0))
    high = close + 2.0
    low = close - 2.0
    open_ = close - 0.2
    # force an exhaustion-like last bars
    close[-1] = close[-2] - 0.5
    high[-1] = close[-1] + 3.0
    low[-1] = close[-1] - 0.2
    open_[-1] = close[-1] + 0.1
    bars = pd.DataFrame(
        {
            "time_server": pd.date_range("2020-01-01", periods=n, freq="5min"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }
    )
    ohlc = bars.rename(columns={"time_server": "time"})
    atr = B.atr_mt5(ohlc, 14) if hasattr(B, "atr_mt5") else None
    # use module helpers via research kit already imported in builder path
    from research.indicators import atr_mt5, ema, rsi_wilder

    bars["atr14"] = atr_mt5(ohlc, 14)
    adx, pdi, mdi = B.adx_di_mt5(ohlc, 14)
    bars["adx14"] = adx
    bars["pdi14"] = pdi
    bars["mdi14"] = mdi
    bars["rsi14"] = rsi_wilder(bars["close"], 14)
    bars["ema50"] = ema(bars["close"], 50)
    bars["body"] = (bars["close"] - bars["open"]).abs()
    bars["range"] = bars["high"] - bars["low"]
    ev = B.eval_010_at(n - 1, bars)
    assert ev is not None
    assert ev.active >= 3
    assert 0 <= ev.failed <= ev.active


def test_case_row_near_miss_has_no_trade_fields(B):
    case = {
        "case_id": "010-N001-B10",
        "case_kind": "OFFLINE_NEAR_MISS_DIAGNOSTIC",
        "hypothesis_id": "HYP-MZMS-XAU-M5-010",
        "run_id": "20260722_024229",
        "side": "SELL",
        "direction": -1,
        "stratum": "",
        "anomaly_tag": "",
        "image": "x.png",
        "image_sha256": "ABC",
        "time_server": "2020.01.01 10:00:00",
        "time_utc": "2020.01.01 08:00:00",
        "failed_gates": 1,
        "active_gates": 6,
        "normalized_distance": 0.12,
        "near_miss_rank": 1,
        "offline_full_signal_unexecuted": False,
    }
    row = B.case_row_for_csv(case)
    assert row["trade_fields_forbidden"] is True
    for field in ("entry", "sl", "tp", "exit", "net_usd", "net_R", "position_id"):
        assert row[field] == ""


def test_lifecycle_reconciliation_live_runs(B):
    """Exact OPEN+CLOSE, telemetry==entries, report/enhanced trade counts."""
    for hid, expected_n in [
        ("HYP-MZMS-XAU-M5-007", 3409),
        ("HYP-MZMS-XAU-M5-008", 80),
        ("HYP-MZMS-XAU-M5-009", 1041),
        ("HYP-MZMS-XAU-M5-010", 2),
    ]:
        recon = B.reconcile_hypothesis(hid)
        assert recon["positions"] == expected_n
        assert recon["state_telemetry_accepted_rows"] == expected_n
        assert recon["report_total_trades"] == expected_n
        assert recon["enhanced_n_trades"] == expected_n
        assert recon["exact_open_close_pairs"] is True
        assert recon["telemetry_equals_entries"] is True
        assert recon["history_quality_pct"] == 98.0
        assert recon["exact_reconciliation"] is True
