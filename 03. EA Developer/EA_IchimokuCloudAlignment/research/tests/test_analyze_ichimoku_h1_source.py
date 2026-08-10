from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_ichimoku_h1_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_ichimoku_h1_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_frame(prices: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time_utc": pd.date_range("2018-01-01T00:00:00Z", periods=len(prices), freq="1h"),
            "high": prices + 1.0,
            "low": prices - 1.0,
            "close": prices,
        }
    )


def directional_frame(direction: str) -> pd.DataFrame:
    if direction == "LONG":
        prices = np.r_[np.linspace(100.0, 150.0, 100), np.linspace(150.0, 140.0, 20), np.linspace(140.0, 170.0, 40)]
    else:
        prices = np.r_[np.linspace(150.0, 100.0, 100), np.linspace(100.0, 110.0, 20), np.linspace(110.0, 80.0, 40)]
    return source_frame(prices)


def test_h1_reuses_exact_hash_bound_indicator_formula() -> None:
    assert MODULE.base.sha256_file(MODULE.BASE_PATH) == MODULE.BASE_SHA256
    indicator = MODULE.base.calculate_ichimoku(source_frame(np.arange(100, dtype=float)))
    assert not bool(indicator["feature_valid"].iloc[76])
    assert bool(indicator["feature_valid"].iloc[77])


@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_exact_h1_full_alignment_event(direction: str) -> None:
    events, report = MODULE.analyze_frame(directional_frame(direction))

    assert [row["direction"] for row in events] == [direction]
    source = pd.Timestamp(events[0]["source_bar_time_utc"])
    decision = pd.Timestamp(events[0]["decision_time_utc"])
    assert decision - source == pd.Timedelta(hours=1)
    assert report["funnel"]["raw_events"] == 1


def test_h1_raw_event_at_gap_is_consumed() -> None:
    frame = directional_frame("LONG")
    event_index = 130
    frame.loc[event_index + 1 :, "time_utc"] = frame.loc[event_index + 1 :, "time_utc"] + pd.Timedelta(hours=1)

    events, report = MODULE.analyze_frame(frame)

    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_market_closure_inside_lookback_preserves_bar_count_formula() -> None:
    frame = directional_frame("LONG")
    frame.loc[50:, "time_utc"] = frame.loc[50:, "time_utc"] + pd.Timedelta(days=2)

    events, _ = MODULE.analyze_frame(frame)

    assert len(events) == 1


def test_event_ledger_is_exact_source_allowlist() -> None:
    events, report = MODULE.analyze_frame(directional_frame("LONG"))
    MODULE.assert_outcome_blind(events, report)
    assert set(events[0]) == MODULE.base.EVENT_KEYS


def test_selected_frame_requires_native_h1() -> None:
    prices = np.arange(MODULE.MIN_ROWS, dtype=float) + 100.0
    frame = source_frame(prices)
    frame.insert(0, "symbol", "XAUUSD")
    frame.insert(1, "timeframe", "M5")
    frame.insert(2, "source_epoch", np.arange(len(frame)))
    frame.insert(4, "utc_ambiguous", False)

    with pytest.raises(ValueError, match="H1"):
        MODULE.validate_selected_frame(frame)


def test_registry_requires_hash_bound_formula_dependency(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    row = {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "state": "probe",
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.PREREG_SHA256,
        "metrics": {"source_feasibility_attempts_consumed": 0},
        "validation": {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
            "source_feasibility_attempt_limit": 1,
            "source_run_authorized": True,
            "source_feasibility_only": True,
            "reviewed_analyzer_sha256": MODULE.base.sha256_file(MODULE_PATH),
            "ichimoku_formula_dependency_sha256": "0" * 64,
            "outcome_prices_authorized": False,
            "economics_authorized": False,
            "research_validation_access_authorized": False,
            "research_holdout_access_authorized": False,
            "mt5_authorized": False,
            "mql5_authorized": False,
            "live_trading_authorized": False,
        },
    }
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dependency"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
