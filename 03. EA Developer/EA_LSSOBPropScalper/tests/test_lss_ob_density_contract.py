from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PACKAGE = Path(__file__).resolve().parents[1]
RESEARCH = PACKAGE / "research"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = load_module("lss_ob_probe_engine", RESEARCH / "lss_ob_probe_engine.py")
parity = load_module("lss_ob_native_m15_parity", RESEARCH / "lss_ob_native_m15_parity.py")


def bar_frame(values: list[tuple[float, float, float, float]], start: str = "2020-01-06 07:00") -> pd.DataFrame:
    times = pd.date_range(start, periods=len(values), freq="15min")
    frame = pd.DataFrame(values, columns=["open", "high", "low", "close"])
    frame.insert(0, "time_utc", times)
    frame["decision_time_utc"] = frame["time_utc"] + pd.Timedelta(minutes=15)
    frame["tick_volume"] = 1
    return frame


def test_resample_uses_left_closed_utc_ohlc_and_keeps_partial_bins() -> None:
    m1 = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(["2020-01-01 07:00", "2020-01-01 07:01", "2020-01-01 07:15"]),
            "open": [1.0, 1.1, 2.0],
            "high": [1.2, 1.3, 2.2],
            "low": [0.9, 1.0, 1.9],
            "close": [1.1, 1.2, 2.1],
            "tick_volume": [2, 3, 4],
        }
    )
    out = engine.resample_ohlc(m1, "15min")
    assert len(out) == 2
    assert out.iloc[0][["open", "high", "low", "close", "tick_volume", "m1_count"]].tolist() == [1.0, 1.3, 0.9, 1.2, 5, 2]
    assert out.iloc[1]["m1_count"] == 1


def test_pivot_is_unavailable_until_two_right_bars_close() -> None:
    bars = bar_frame(
        [
            (2, 3, 1.5, 2),
            (2, 2.5, 1.4, 2),
            (2, 2.4, 1.0, 2),
            (2, 2.5, 1.3, 2),
            (2, 2.6, 1.4, 2),
        ]
    )
    pivots = engine.confirmed_pivot_frame(bars, 2)
    assert pivots.iloc[3]["pivot_low_idx"] == -1
    assert pivots.iloc[4]["pivot_low_idx"] == 2
    assert pivots.iloc[4]["pivot_low"] == 1.0


def test_news_guard_accepts_duplicate_epochs_and_blocks_inclusive_boundaries() -> None:
    guard = engine.NewsGuard(
        [pd.Timestamp("2020-01-01 10:00"), pd.Timestamp("2020-01-01 10:00")], 30
    )
    assert guard.blocked(pd.Timestamp("2020-01-01 09:30"))
    assert guard.blocked(pd.Timestamp("2020-01-01 10:30"))
    assert not guard.blocked(pd.Timestamp("2020-01-01 09:29:59"))


def test_strict_fvg_and_confirmation_are_mirrored() -> None:
    spec = engine.FrozenSpec()
    bullish = bar_frame([(1.0, 1.1, 0.9, 1.0), (1.0, 1.05, 0.95, 0.98), (1.2, 1.5, 1.2, 1.45)])
    bearish = bar_frame([(2.0, 2.1, 1.9, 2.0), (2.0, 2.05, 1.95, 2.02), (1.8, 1.8, 1.5, 1.55)])
    assert engine.strict_fvg(bullish, 2, 1) == (1.1, 1.2)
    assert engine.strict_fvg(bearish, 2, -1) == (1.8, 1.9)
    assert engine.is_confirmation(bullish, 2, 1, spec)
    assert engine.is_confirmation(bearish, 2, -1, spec)


@pytest.mark.parametrize(
    ("count", "expected"),
    [(416, False), (417, True), (1042, True), (1043, False)],
)
def test_pooled_cadence_integer_boundaries(count: int, expected: bool) -> None:
    weeks = engine.elapsed_weeks("2019-01-03", "2022-12-31")
    rate = count / weeks
    assert (2.0 <= rate <= 5.0) is expected


def test_no_outcome_schema_rejects_forbidden_keys() -> None:
    engine.assert_no_outcome_schema(
        {
            "outcomes_included": False,
            "performance_metrics_authorized": False,
            "event_count": 0,
        }
    )
    with pytest.raises(ValueError):
        engine.assert_no_outcome_schema({"profit_factor": 0})


def test_frozen_plan_and_runner_bind_expected_hashes() -> None:
    plan = RESEARCH / "HYP-LSS-OB-REPL-EURUSD-M15-001_PROBE_PLAN.md"
    runner = (RESEARCH / "lss_ob_density_probe.py").read_text(encoding="utf-8")
    assert plan.is_file()
    assert "7F051DE01B89E6A41A01B0C7EC023ED7435AF74420EA2E6D89AB9348279C26BD" in runner
    assert "2959C555DB6690FD6EFD6CFB3B4C6323698E590C2F724235A" not in runner
    assert "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A" in runner
    assert "PASS_NATIVE_M1_UTC_REPLAY" in runner
    assert "NATIVE_MT5_PARITY.json" in runner


def test_density_verdict_is_terminal_below_frozen_floor() -> None:
    empty = {
        name: {
            "event_count": 0,
            "elapsed_calendar_days": 1,
            "elapsed_calendar_weeks": 1.0,
            "events_per_elapsed_week": 0.0,
        }
        for name in ("pooled", "train", "validation")
    }
    verdict, gates = engine.density_verdict(empty)
    assert verdict == "TERMINAL_STOP_FIDELITY_CADENCE_NO_BUILD_NO_MODEL0"
    assert any(gate["status"] == "FAIL" for gate in gates)


def test_native_ohlc_parity_fails_closed_on_bar_or_price_mismatch() -> None:
    offline = bar_frame([(1.0, 1.2, 0.9, 1.1), (1.1, 1.3, 1.0, 1.2)])
    native = offline.copy()
    assert parity.compare_ohlc(offline, native)["status"] == "PASS"
    native.at[1, "high"] += 0.00001
    comparison = parity.compare_ohlc(offline, native)
    assert comparison["status"] == "FAIL"
    assert comparison["fields"]["high"]["mismatch_count"] == 1
