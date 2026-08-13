from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).parents[1] / "analyze_eibb_m5_source.py"
SPEC = importlib.util.spec_from_file_location("eibb_source", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def m5_bar(time: str, high: float, low: float, close: float, epoch: int) -> dict:
    return {
        "symbol": "XAUUSD", "timeframe": "M5", "source_epoch": epoch,
        "time_utc": pd.Timestamp(time), "utc_ambiguous": False,
        "open": (high + low) / 2.0, "high": high, "low": low,
        "close": close, "tick_volume": 10.0,
    }


def add_m15(rows: list[dict], start: str, high: float, low: float, close: float) -> None:
    t = pd.Timestamp(start)
    epoch = int(t.timestamp())
    rows.extend([
        m5_bar(t.isoformat(), high, low, (high + low) / 2.0, epoch),
        m5_bar((t + pd.Timedelta(minutes=5)).isoformat(), high, low, (high + low) / 2.0, epoch + 300),
        m5_bar((t + pd.Timedelta(minutes=10)).isoformat(), high, low, close, epoch + 600),
    ])


def day_frame(breaks: list[tuple[str, float]]) -> pd.DataFrame:
    rows: list[dict] = []
    for minute in ("07:00", "07:15", "07:30", "07:45"):
        add_m15(rows, f"2018-01-02T{minute}:00Z", 101.0, 99.0, 100.0)
    for minute, close in breaks:
        add_m15(rows, f"2018-01-02T{minute}:00Z", max(close, 100.5), min(close, 99.5), close)
    return pd.DataFrame(rows)


def test_aggregate_requires_exact_three_constituents() -> None:
    frame = day_frame([("08:00", 102.0)])
    assert len(MODULE.aggregate_m15(frame)) == 5
    missing = frame.drop(frame.index[1]).reset_index(drop=True)
    assert len(MODULE.aggregate_m15(missing)) == 4


def test_first_break_only_and_exact_next() -> None:
    frame = day_frame([("08:00", 100.0), ("08:15", 102.0), ("08:30", 103.0)])
    report, events = MODULE.analyze(frame)
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["executable_events"] == 1
    assert events[0]["direction"] == "LONG"
    assert events[0]["source_bar_time_utc"] == "2018-01-02T08:15:00Z"
    assert events[0]["decision_time_utc"] == "2018-01-02T08:30:00Z"


def test_equality_does_not_break() -> None:
    frame = day_frame([("08:00", 101.0), ("08:15", 99.0), ("08:30", 100.0)])
    report, events = MODULE.analyze(frame)
    assert report["funnel"]["raw_events"] == 0
    assert events == []


def test_short_break() -> None:
    frame = day_frame([("08:00", 98.0), ("08:15", 97.0)])
    report, events = MODULE.analyze(frame)
    assert report["funnel"]["raw_events"] == 1
    assert events[0]["direction"] == "SHORT"


def test_missing_next_bar_consumes_event() -> None:
    frame = day_frame([("08:00", 102.0)])
    report, events = MODULE.analyze(frame)
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["executable_events"] == 0
    assert report["funnel"]["gap_rejected_events"] == 1
    assert events == []


def test_event_allowlist_has_no_post_event_price() -> None:
    frame = day_frame([("08:00", 102.0), ("08:15", 102.5)])
    report, events = MODULE.analyze(frame)
    MODULE.assert_outcome_blind(report, events)
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert not ({"return", "pnl", "profit_factor", "next_close"} & set(events[0]))


def test_claim_precedes_source_read_contract_is_present() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.index("claim_attempt()") < text.index("pd.read_parquet(")
    assert 'ATTEMPT_ROOT.mkdir()' in text
    assert 'with path.open("xb")' in text

