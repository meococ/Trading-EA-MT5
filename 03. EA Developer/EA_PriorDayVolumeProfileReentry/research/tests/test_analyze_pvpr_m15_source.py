from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_pvpr_m15_source.py"
SPEC = importlib.util.spec_from_file_location("pvpr_m15_source", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def day_frame(prices: list[float], volumes: list[int], start: str = "2020-01-06 00:00:00") -> pd.DataFrame:
    repeats = max(1, 1000 // len(prices) + 1)
    p = np.tile(np.asarray(prices, dtype=float), repeats)[:1000]
    v = np.tile(np.asarray(volumes, dtype=np.uint64), repeats)[:1000]
    times = pd.Series(pd.date_range(
        pd.Timestamp(start),
        pd.Timestamp(start).normalize() + pd.Timedelta(hours=23, minutes=50),
        periods=1000,
    ))
    return pd.DataFrame({
        "time_server": times,
        "time_utc": times,
        "open": p,
        "high": p + 0.00001,
        "low": p - 0.00001,
        "close": p,
        "tick_volume": v,
    })


def test_profile_poc_tie_uses_closest_mean_then_lower() -> None:
    frame = day_frame([1.1000, 1.1002], [10, 10])
    profile = MOD.build_profile(frame)
    assert profile is not None
    assert profile["poc"] == 1.1000


def test_value_area_expansion_prefers_larger_adjacent_then_lower_tie() -> None:
    frame = day_frame([1.1000, 1.1001, 1.1002], [6, 10, 6])
    profile = MOD.build_profile(frame)
    assert profile is not None
    assert profile["poc"] == 1.1001
    assert profile["val"] == 1.1000
    assert profile["vah"] == 1.1001
    assert profile["included_fraction"] >= 0.70


def test_incomplete_or_zero_volume_profile_fails_closed() -> None:
    small = day_frame([1.1], [1]).iloc[:999]
    assert MOD.build_profile(small) is None
    zero = day_frame([1.1], [0])
    assert MOD.build_profile(zero) is None


def test_validate_source_rejects_nonpositive_price_and_duplicate_utc() -> None:
    frame = day_frame([1.1], [1])
    bad = frame.copy()
    bad.loc[2, "close"] = 0.0
    try:
        MOD.validate_source(bad)
        raise AssertionError("nonpositive price must fail")
    except ValueError as exc:
        assert "positive" in str(exc)
    duplicate = frame.copy()
    duplicate.loc[2, "time_utc"] = duplicate.loc[1, "time_utc"]
    try:
        MOD.validate_source(duplicate)
        raise AssertionError("duplicate UTC must fail")
    except ValueError as exc:
        assert "time_utc" in str(exc)


def test_m15_aggregation_uses_utc_bucket_and_no_interpolation() -> None:
    times = pd.date_range("2020-01-07 07:00:00", periods=16, freq="min")
    frame = pd.DataFrame({
        "time_utc": times,
        "open": np.arange(16, dtype=float) + 1.0,
        "high": np.arange(16, dtype=float) + 1.1,
        "low": np.arange(16, dtype=float) + 0.9,
        "close": np.arange(16, dtype=float) + 1.05,
    })
    bars = MOD.aggregate_m15(frame)
    assert len(bars) == 2
    assert bars.iloc[0]["m1_rows"] == 15
    assert bars.iloc[1]["m1_rows"] == 1
    assert bars.iloc[0]["open"] == 1.0
    assert bars.iloc[0]["close"] == 15.05


def test_analyzer_is_source_only_and_uses_exact_utc_next_bar() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8").lower()
    for forbidden in ("profit_factor", "net_profit", "expectancy", "next_open", "next_close", "pnl"):
        assert forbidden not in text
    assert '"outcomes_read": false' in text
    assert '"paid_data_used": false' in text
    assert '(bars.iloc[index + 1]["time_utc"] - bars.iloc[index]["time_utc"]).total_seconds() == 900' in text
    assert '"year_axis": "decision_time_utc"' in text


def test_one_shot_claim_wraps_start_and_failure_terminal() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "output.mkdir(parents=True, exist_ok=False)" in text
    assert 'stage = "ROOT_CLAIMED"' in text
    assert "try:\n        write_json(output / \"attempt_started.json\"" in text
    assert 'if not terminal.exists()' in text
    assert '"same_id_retry_allowed": False' in text


def test_formula_and_native_data_contract_are_frozen() -> None:
    assert MOD.SOURCE_SHA256 == "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
    assert MOD.PIP == 0.0001
    assert MOD.VALUE_AREA_FRACTION == 0.70
    prereg = MOD.PREREG.read_text(encoding="utf-8")
    assert "No paid data" in prereg
    assert "one-auction-failure-per-day" in prereg
