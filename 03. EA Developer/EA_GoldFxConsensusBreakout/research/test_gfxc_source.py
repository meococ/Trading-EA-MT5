from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "analyze_gfxc_source.py"
PREREG = HERE / "HYP-GFXC-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md"


def load_module():
    spec = importlib.util.spec_from_file_location("gfxc", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic_joined(rows: int = 420) -> pd.DataFrame:
    epoch = np.arange(rows, dtype=np.int64) * 300 + 1514764800
    x = np.arange(rows, dtype=float)
    base = 100.0 * np.exp(0.00005 * x + 0.0008 * np.sin(x / 5.0))
    return pd.DataFrame({
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s").strftime("%Y-%m-%d %H:%M:%S"),
        "xau_high": base * 1.0002,
        "xau_low": base * 0.9998,
        "XAUUSD_close": base,
        "EURUSD_close": 1.10 * np.exp(0.00003 * x + 0.0005 * np.cos(x / 7.0)),
        "GBPUSD_close": 1.30 * np.exp(0.00002 * x + 0.0006 * np.sin(x / 9.0)),
        "USDJPY_close": 110.0 * np.exp(-0.00002 * x + 0.0004 * np.cos(x / 11.0)),
    })


def test_prereg_freezes_sources_formula_and_no_outcomes():
    text = PREREG.read_text(encoding="utf-8")
    assert "GFXC-SOURCE-001" in text
    assert "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380" in text
    assert "0.50" in text and "288" in text and "24-bar" in text and "12 joined-bar" in text
    assert "must not inspect any price after the decision bar" in text


def test_formula_uses_shifted_scale_and_prior_breakout():
    text = SOURCE.read_text(encoding="utf-8")
    assert "one_bar.shift(1).rolling(SCALE_WINDOW" in text
    assert 'data["xau_high"].shift(1).rolling(BREAKOUT_WINDOW' in text
    assert 'data["xau_low"].shift(1).rolling(BREAKOUT_WINDOW' in text
    assert "WARMUP_ROWS = 290" in text


def test_future_mutation_does_not_change_earlier_features():
    module = load_module()
    frame = synthetic_joined()
    original = module.compute_features(frame)
    changed = frame.copy()
    changed.loc[400:, [f"{s}_close" for s in module.SYMBOLS]] *= 3.0
    changed.loc[400:, ["xau_high", "xau_low"]] *= 3.0
    replay = module.compute_features(changed)
    cols = [f"{s}_z12" for s in module.SYMBOLS] + ["prior_upper", "prior_lower"]
    pd.testing.assert_frame_equal(original.loc[:399, cols], replay.loc[:399, cols])


def test_state_requires_all_four_normalized_legs_and_breakout():
    module = load_module()
    data = module.compute_features(synthetic_joined())
    i = module.WARMUP_ROWS
    data.at[i, "feature_usable"] = True
    data.at[i, "XAUUSD_close"] = float(data.at[i, "prior_upper"]) + 1.0
    data.at[i, "XAUUSD_z12"] = 0.6
    data.at[i, "EURUSD_z12"] = 0.6
    data.at[i, "GBPUSD_z12"] = 0.6
    data.at[i, "USDJPY_z12"] = -0.6
    long_state = (
        data.at[i, "feature_usable"]
        and data.at[i, "XAUUSD_close"] > data.at[i, "prior_upper"]
        and data.at[i, "XAUUSD_z12"] >= module.Z_THRESHOLD
        and data.at[i, "EURUSD_z12"] >= module.Z_THRESHOLD
        and data.at[i, "GBPUSD_z12"] >= module.Z_THRESHOLD
        and data.at[i, "USDJPY_z12"] <= -module.Z_THRESHOLD
    )
    assert long_state
    data.at[i, "USDJPY_z12"] = -0.49
    assert not (data.at[i, "USDJPY_z12"] <= -module.Z_THRESHOLD)


def test_lockout_consumes_following_transitions():
    module = load_module()
    rows = module.WARMUP_ROWS + 30
    frame = synthetic_joined(rows)
    data = module.compute_features(frame)
    data["feature_usable"] = True
    data["long_state"] = False
    data["short_state"] = False
    data.loc[module.WARMUP_ROWS, "long_state"] = True
    data.loc[module.WARMUP_ROWS + 2, "long_state"] = True
    data.loc[module.WARMUP_ROWS + 13, "long_state"] = True
    events, conflicts = module.extract_events(data)
    assert conflicts == 0
    assert len(events) == 2


def test_friday_cutoff_is_availability_utc():
    module = load_module()
    text = SOURCE.read_text(encoding="utf-8")
    assert "server_to_utc(server_time + timedelta(seconds=300))" in text
    assert '"decision_year": availability_utc.year' in text


def test_attempt_is_claimed_before_any_parquet_read_and_outputs_exclusive():
    text = SOURCE.read_text(encoding="utf-8")
    assert text.index("ATTEMPT_ROOT.mkdir()") < text.index("pd.read_parquet")
    assert 'with path.open("xb")' in text
    assert "os.fsync" in text
    assert "deterministic replay mismatch" in text


def test_report_never_contains_outcome_fields():
    module = load_module()
    report, ledger = module.analyze(synthetic_joined())
    assert report["outcomes_opened"] is False
    assert report["economics_evaluated"] is False
    forbidden = {"profit", "return", "pnl", "pf", "mfe", "mae", "next_close", "next_high", "next_low"}
    for row in ledger:
        assert forbidden.isdisjoint(row)
