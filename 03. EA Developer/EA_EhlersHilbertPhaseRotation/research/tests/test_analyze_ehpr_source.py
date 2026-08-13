from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_ehpr_source.py"
SPEC = importlib.util.spec_from_file_location("ehpr_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def synthetic_m15(period: int = 20, count: int = 320, gap_at: int | None = None) -> pd.DataFrame:
    times = []
    stamp = pd.Timestamp("2016-01-04T00:00:00Z")
    for index in range(count):
        if gap_at is not None and index == gap_at:
            stamp += pd.Timedelta(minutes=30)
        times.append(stamp)
        stamp += pd.Timedelta(minutes=15)
    values = [1.10 + 0.001 * math.sin(2.0 * math.pi * index / period) for index in range(count)]
    return pd.DataFrame({"time_utc": times, "open": values, "high": [value + 0.0001 for value in values], "low": [value - 0.0001 for value in values], "close": values})


def test_unit_sine_phase_crosses_alternate_and_period_converges() -> None:
    events, report = MODULE.analyze_m15(synthetic_m15())
    assert len(events) >= 20
    assert all(left["direction"] != right["direction"] for left, right in zip(events, events[1:]))
    assert 18.0 <= events[-1]["dominant_period"] <= 22.0
    assert report["prohibitions"]["returns_computed"] == 0


def test_constant_series_has_no_phase_events() -> None:
    frame = synthetic_m15()
    for column in ("open", "high", "low", "close"):
        frame[column] = 1.10
    events, report = MODULE.analyze_m15(frame)
    assert events == []
    assert report["funnel"]["executable_events"] == 0


def test_unexpected_gap_resets_and_rewarms() -> None:
    events, report = MODULE.analyze_m15(synthetic_m15(count=420, gap_at=210))
    assert report["funnel"]["unexpected_gap_resets"] == 1
    post_gap = [event for event in events if pd.Timestamp(event["source_bar_time_utc"]) >= pd.Timestamp("2016-01-06T05:00:00Z")]
    assert post_gap
    assert min(event["segment_bars"] for event in post_gap) >= MODULE.WARMUP_BARS + 1


def test_exact_m5_triplets_only() -> None:
    rows = []
    start = pd.Timestamp("2016-01-04T00:00:00Z")
    for minute in (0, 5, 10, 15, 25):
        stamp = start + pd.Timedelta(minutes=minute)
        rows.append({"symbol": "EURUSD", "timeframe": "M5", "source_epoch": int(stamp.timestamp()), "time_utc": stamp, "utc_ambiguous": False, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0})
    derived, diagnostics = MODULE.derived_m15_from_m5(pd.DataFrame(rows))
    assert len(derived) == 1
    assert diagnostics["complete_m15_bars"] == 1
    assert diagnostics["alignable_m15_slots"] == 2


def test_event_schema_exposes_no_post_event_price() -> None:
    events, report = MODULE.analyze_m15(synthetic_m15())
    MODULE.assert_outcome_blind(events, report)
    assert events and set(events[0]) == MODULE.EVENT_KEYS
    assert not any("return" in key or "pnl" in key or "profit" in key or "exit_price" in key for key in events[0])
