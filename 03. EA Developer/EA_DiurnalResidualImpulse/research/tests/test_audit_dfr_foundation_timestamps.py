from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_dfr_foundation_timestamps.py"
SPEC = importlib.util.spec_from_file_location("audit_dfr_foundation_timestamps", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUT
SPEC.loader.exec_module(SUT)


def test_complete_m15_requires_exact_three_m5_offsets() -> None:
    times = pd.Series(pd.to_datetime([
        "2020-01-01T00:00:00Z",
        "2020-01-01T00:05:00Z",
        "2020-01-01T00:10:00Z",
        "2020-01-01T00:15:00Z",
        "2020-01-01T00:25:00Z",
    ]))
    starts = SUT.complete_m15_starts(times)
    assert starts == {int(pd.Timestamp("2020-01-01T00:00:00Z").timestamp())}


def test_evaluate_reports_recovery_and_regression() -> None:
    base = pd.Timestamp("2020-01-01T00:00:00Z")
    signals = [
        {"source_signal_id": "A", "decision_utc": base - pd.Timedelta(minutes=15), "entry_open_utc": base, "status": "SOURCE_EXECUTABLE"},
        {"source_signal_id": "B", "decision_utc": base + pd.Timedelta(hours=2), "entry_open_utc": base + pd.Timedelta(hours=2, minutes=15), "status": "HORIZON_INCOMPLETE"},
    ]
    starts = {int((base + pd.Timedelta(minutes=15 * i)).timestamp()) for i in range(6)}
    starts |= {int((base + pd.Timedelta(hours=2, minutes=15 + 15 * i)).timestamp()) for i in range(6)}
    result = SUT.evaluate(signals, starts)
    assert result["population"]["old_executable_retained"] == 1
    assert result["population"]["old_incomplete_recovered"] == 1


def test_evaluate_never_emits_price_or_performance_fields() -> None:
    base = pd.Timestamp("2020-01-01T00:00:00Z")
    signals = [{"source_signal_id": "A", "decision_utc": base, "entry_open_utc": base + pd.Timedelta(minutes=15), "status": "SOURCE_EXECUTABLE"}]
    result = SUT.evaluate(signals, set())
    serialized = SUT.canonical_json(result).decode("utf-8")
    for forbidden in ('"open"', '"high"', '"low"', '"close"', '"return"', '"pnl"', '"profit_factor"'):
        assert forbidden not in serialized


def test_parquet_selection_is_normalized_utc_only() -> None:
    assert SUT.SOURCE_START == pd.Timestamp("2015-01-01T00:00:00Z")
    assert SUT.SOURCE_END == pd.Timestamp("2021-01-01T00:00:00Z")
