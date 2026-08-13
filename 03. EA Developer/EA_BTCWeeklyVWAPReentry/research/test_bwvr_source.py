from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "analyze_bwvr_source.py"
PREREG = HERE / "HYP-BWVR-BTCUSD-M5-001_FROZEN_SOURCE_PREREG.md"


def load_module():
    spec = importlib.util.spec_from_file_location("bwvr", SOURCE)
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


def test_prereg_freezes_btc_source_formula_and_no_outcomes():
    text = PREREG.read_text(encoding="utf-8")
    assert "BWVR-SOURCE-001" in text
    assert "5B4DA734215BA56DE0DEA7C33E06ECC74C44EDE1CED9986AEB5B98F4B2053AE0" in text
    assert "AVWAP" in text and "1.50" in text and "24-bar" in text
    assert "may not read next-bar OHLC" in text


def test_formula_uses_current_week_cumulative_vwap_and_prior_atr():
    text = SOURCE.read_text(encoding="utf-8")
    assert 'groupby(data["week_key"], sort=False).cumsum()' in text
    assert "tr.shift(1).rolling(ATR_WINDOW" in text
    assert "BAND_ATR = 1.50" in text


def test_weekly_vwap_resets_on_iso_week_change():
    module = load_module()
    frame = synthetic_frame(2500)
    data = module.compute_features(frame)
    change = data.index[data["week_key"].ne(data["week_key"].shift(1))][1]
    tp = (frame.at[change, "high"] + frame.at[change, "low"] + frame.at[change, "close"]) / 3.0
    assert data.at[change, "avwap"] == tp
    assert not bool(data.at[change, "feature_usable"])


def test_future_mutation_does_not_change_earlier_features():
    module = load_module()
    frame = synthetic_frame()
    first = module.compute_features(frame)
    changed = frame.copy()
    changed.loc[450:, ["open", "high", "low", "close"]] *= 2.0
    changed.loc[450:, "tick_volume"] *= 10.0
    second = module.compute_features(changed)
    cols = ["avwap", "atr14_prev", "lower", "upper", "long_event", "short_event"]
    pd.testing.assert_frame_equal(first.loc[:449, cols], second.loc[:449, cols])


def test_lockout_consumes_24_following_bars():
    module = load_module()
    data = module.compute_features(synthetic_frame(100))
    data["long_event"] = False
    data["short_event"] = False
    data.loc[20, "long_event"] = True
    data.loc[22, "long_event"] = True
    data.loc[45, "long_event"] = True
    events, conflicts = module.extract_events(data)
    assert conflicts == 0
    assert len(events) == 2


def test_ambiguous_utc_event_is_consumed_not_executable():
    module = load_module()
    data = module.compute_features(synthetic_frame(100))
    data["long_event"] = False
    data["short_event"] = False
    data.loc[20, "long_event"] = True
    data.loc[20, "utc_ambiguous"] = True
    data.loc[20, "time_utc"] = pd.NaT
    events, _ = module.extract_events(data)
    assert len(events) == 1
    assert events[0]["utc_available"] is False


def test_attempt_claim_precedes_parquet_read_and_outputs_are_exclusive():
    text = SOURCE.read_text(encoding="utf-8")
    assert text.index("ATTEMPT_ROOT.mkdir()") < text.index("pd.read_parquet")
    assert 'with path.open("xb")' in text
    assert "os.fsync" in text
    assert "deterministic replay mismatch" in text


def test_ledger_has_no_post_decision_price_or_outcome():
    module = load_module()
    report, ledger = module.analyze(synthetic_frame(1000))
    assert report["outcomes_opened"] is False
    assert report["economics_evaluated"] is False
    forbidden = {"profit", "pnl", "return", "pf", "mfe", "mae", "next_close", "next_high", "next_low"}
    for row in ledger:
        assert forbidden.isdisjoint(row)
