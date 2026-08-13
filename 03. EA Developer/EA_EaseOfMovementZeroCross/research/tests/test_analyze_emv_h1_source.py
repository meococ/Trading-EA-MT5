from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_emv_h1_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_emv_h1_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_binds_unique_native_h1_source_without_opening_parquet() -> None:
    manifest = json.loads(MODULE.MANIFEST_PATH.read_text(encoding="utf-8"))
    matches = [item for item in manifest["files"] if str(item["path"]).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")]
    assert len(matches) == 1
    assert matches[0]["sha256"] == MODULE.DATA_SHA256


def test_eom14_formula_warmup_flat_range_and_scale() -> None:
    high = np.arange(100.0, 120.0)
    low = high - 2.0
    volume = np.full(20, 10.0)
    result = MODULE.calculate_eom14(high, low, volume)
    assert np.isnan(result[:14]).all()
    assert result[14] == pytest.approx(0.2)
    flat = MODULE.calculate_eom14(np.full(20, 100.0), np.full(20, 100.0), volume)
    assert flat[14] == pytest.approx(0.0)


def frame_with_eom(values: list[float], gap_after: int | None = None) -> pd.DataFrame:
    count = len(values)
    times = pd.date_range(MODULE.DESIGN_START, periods=count, freq="1h")
    epochs = 1_514_764_800 + np.arange(count, dtype=np.int64) * 3600
    if gap_after is not None:
        times = pd.DatetimeIndex([time + (pd.Timedelta(hours=1) if index > gap_after else pd.Timedelta(0)) for index, time in enumerate(times)])
        epochs[gap_after + 1:] += 3600
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False, "high": 101.0, "low": 99.0, "close": 100.0, "tick_volume": 10.0, "_eom": values})


def test_zero_cross_equality_arms_and_current_equality_does_not_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [0.0, 1.0, 0.0, -1.0, 0.0]
    frame = frame_with_eom(values)
    monkeypatch.setattr(MODULE, "calculate_eom14", lambda high, low, volume: np.asarray(values, dtype=float))
    report, events = MODULE.analyze(frame.drop(columns="_eom"))
    assert [event["direction"] for event in events] == ["LONG", "SHORT"]
    assert report["funnel"]["raw_events"] == 2


def test_gap_cross_is_consumed(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [-1.0, 1.0, 1.0]
    frame = frame_with_eom(values, gap_after=1)
    monkeypatch.setattr(MODULE, "calculate_eom14", lambda high, low, volume: np.asarray(values, dtype=float))
    report, events = MODULE.analyze(frame.drop(columns="_eom"))
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def valid_source_frame() -> pd.DataFrame:
    times = pd.date_range(MODULE.SOURCE_START, periods=20, freq="1h")
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "H1", "source_epoch": 1_086_937_200 + np.arange(20) * 3600, "time_utc": times, "utc_ambiguous": False, "high": 101.0, "low": 99.0, "close": 100.0, "tick_volume": 10.0})


@pytest.mark.parametrize("mutation", ["zero_volume", "nonfinite", "inverted", "outside", "null_symbol"])
def test_invalid_source_rows_fail_closed(mutation: str) -> None:
    frame = valid_source_frame()
    if mutation == "zero_volume":
        frame.loc[3, "tick_volume"] = 0
    elif mutation == "nonfinite":
        frame.loc[3, "high"] = np.nan
    elif mutation == "inverted":
        frame.loc[3, "high"] = 98.0
    elif mutation == "outside":
        frame.loc[3, "close"] = 102.0
    else:
        frame.loc[3, "symbol"] = None
    with pytest.raises(ValueError):
        MODULE.validate_frame(frame)


def test_outcome_blind_allowlist_rejects_post_event_price() -> None:
    report = {"outcome_blind_counters": {"returns_computed": 0}}
    event = {"hypothesis_id": MODULE.HYPOTHESIS_ID, "source_bar_time_utc": "2018-01-01T00:00:00Z", "decision_time_utc": "2018-01-01T01:00:00Z", "direction": "LONG", "prior_eom14": -1.0, "eom14": 1.0}
    MODULE.assert_outcome_blind(report, [event])
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind(report, [dict(event, next_close=100.0)])
