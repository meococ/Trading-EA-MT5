from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "analyze_bwvr_source_v2.py"
PREREG = HERE / "HYP-BWVR-BTCUSD-M5-002_FROZEN_SOURCE_PREREG.md"


def load_module():
    spec = importlib.util.spec_from_file_location("bwvr2", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic_frame(rows: int = 500) -> pd.DataFrame:
    epoch = np.arange(rows, dtype=np.int64) * 300 + 1514764800
    x = np.arange(rows, dtype=float)
    close = 10000.0 + 2.0 * x + 20.0 * np.sin(x / 5.0)
    utc = pd.to_datetime(epoch - 7200, unit="s", utc=True)
    return pd.DataFrame({
        "symbol": "BTCUSD",
        "timeframe": "M5",
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s"),
        "time_utc": utc,
        "utc_ambiguous": False,
        "open": close - 1.0,
        "high": close + 5.0,
        "low": close - 5.0,
        "close": close,
        "tick_volume": 100.0 + (x % 17),
    })


def test_prereg_freezes_only_capability_revision_and_no_outcomes():
    text = PREREG.read_text(encoding="utf-8")
    assert "BWVR002-SOURCE-001" in text
    assert "220,000" in text
    assert "1.50" in text and "24-bar lockout" in text
    assert "may not read next-bar OHLC" in text
    assert "market formula, signal inequalities" in text


def test_parent_formula_dependency_is_exact_and_hypothesis_is_fresh():
    module = load_module()
    assert module.HYPOTHESIS_ID == "HYP-BWVR-BTCUSD-M5-002"
    assert module.ATTEMPT_ID == "BWVR002-SOURCE-001"
    assert module.MIN_DESIGN_ROWS == 220_000
    assert module.sha256_file(module.BASE_ANALYZER_PATH) == module.BASE_ANALYZER_SHA


def test_row_floor_and_order_fail_as_separate_diagnostics():
    module = load_module()
    module.MIN_DESIGN_ROWS = 50
    short = synthetic_frame(49)
    with pytest.raises(ValueError, match="design row floor failed"):
        module.validate_v2(short)

    duplicate = synthetic_frame(60)
    duplicate.loc[20, "source_epoch"] = duplicate.loc[19, "source_epoch"]
    duplicate.loc[20, "time_server"] = duplicate.loc[19, "time_server"]
    with pytest.raises(ValueError, match="source epoch order gate failed"):
        module.validate_v2(duplicate)


def test_observed_contract_preserves_count_epochs_and_order():
    module = load_module()
    frame = synthetic_frame(75)
    observed = module.observed_contract(frame)
    assert observed["design_rows"] == 75
    assert observed["first_source_epoch"] == int(frame.iloc[0]["source_epoch"])
    assert observed["last_source_epoch"] == int(frame.iloc[-1]["source_epoch"])
    assert observed["strict_source_epoch_order"] is True


def test_v2_uses_parent_weekly_avwap_and_prior_atr_formula():
    module = load_module()
    base = module.load_base()
    frame = synthetic_frame(2500)
    data = base.compute_features(frame)
    change = data.index[data["week_key"].ne(data["week_key"].shift(1))][1]
    tp = (frame.at[change, "high"] + frame.at[change, "low"] + frame.at[change, "close"]) / 3.0
    assert data.at[change, "avwap"] == tp
    assert not bool(data.at[change, "feature_usable"])


def test_future_mutation_cannot_change_earlier_features():
    module = load_module()
    base = module.load_base()
    frame = synthetic_frame()
    first = base.compute_features(frame)
    changed = frame.copy()
    changed.loc[450:, ["open", "high", "low", "close"]] *= 2.0
    changed.loc[450:, "tick_volume"] *= 10.0
    second = base.compute_features(changed)
    cols = ["avwap", "atr14_prev", "lower", "upper", "long_event", "short_event"]
    pd.testing.assert_frame_equal(first.loc[:449, cols], second.loc[:449, cols])


def test_v2_report_replaces_obsolete_parent_row_gate():
    module = load_module()
    module.MIN_DESIGN_ROWS = 50
    base = module.load_base()
    report, ledger = module.analyze_v2(synthetic_frame(2500), base)
    assert "design_rows_gte_400000" not in report["gates"]
    assert report["gates"]["design_rows_gte_220000"] is True
    assert report["hypothesis_id"] == module.HYPOTHESIS_ID
    assert all(row["hypothesis_id"] == module.HYPOTHESIS_ID for row in ledger)


def test_claim_precedes_source_and_bound_input_reads_and_failure_is_structured():
    text = SOURCE.read_text(encoding="utf-8")
    assert text.index("write_exclusive(START_PATH") < text.index("initial = captured_hashes()")
    assert text.index("write_exclusive(START_PATH") < text.index("pd.read_parquet")
    assert 'with path.open("xb")' in text
    assert "os.fsync" in text
    assert '"observed_source_contract": observed' in text
    assert '"input_hashes": initial' in text


def test_ledger_contract_has_no_post_decision_price_or_outcome():
    module = load_module()
    module.MIN_DESIGN_ROWS = 50
    base = module.load_base()
    report, ledger = module.analyze_v2(synthetic_frame(2500), base)
    assert report["outcomes_opened"] is False
    assert report["economics_evaluated"] is False
    forbidden = {"profit", "pnl", "return", "pf", "mfe", "mae", "next_close", "next_high", "next_low"}
    for row in ledger:
        assert forbidden.isdisjoint(row)
