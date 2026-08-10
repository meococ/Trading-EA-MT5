from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_supertrend_flatbar_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_supertrend_flatbar_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def price_frame(prices: np.ndarray, start: str = "2018-01-01T00:00:00Z") -> pd.DataFrame:
    return pd.DataFrame({
        "time_utc": pd.date_range(start, periods=len(prices), freq="1h"),
        "high": prices + 1.0,
        "low": prices - 1.0,
        "close": prices,
    })


def selected_frame(prices: np.ndarray) -> pd.DataFrame:
    data = price_frame(prices, MODULE.SOURCE_START.isoformat())
    data.insert(0, "symbol", "XAUUSD")
    data.insert(1, "timeframe", "H1")
    data.insert(2, "source_epoch", np.arange(len(data), dtype=np.int64))
    data.insert(4, "utc_ambiguous", False)
    return data


def make_flat(data: pd.DataFrame, index: int) -> None:
    data.loc[index, ["high", "low"]] = data.at[index, "close"]


def flip_prices() -> np.ndarray:
    return np.r_[np.full(20, 100.0), np.linspace(100.0, 150.0, 20), np.linspace(150.0, 80.0, 30)]


def test_formula_dependency_is_exactly_hash_bound() -> None:
    assert MODULE.sha256_file(MODULE.FORMULA_DEPENDENCY_PATH) == MODULE.FORMULA_DEPENDENCY_SHA256
    assert MODULE.calculate_supertrend is MODULE.FORMULA.calculate_supertrend


def test_flat_rows_are_valid_at_inception_seed_and_post_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE, "MIN_ROWS", 0)
    data = selected_frame(np.full(30, 100.0))
    for index in (0, 5, 9, 10, 29):
        make_flat(data, index)
    validated = MODULE.validate_selected_frame(data)
    assert len(validated) == 30
    assert int((validated["high"] == validated["low"]).sum()) == 5


@pytest.mark.parametrize(
    ("column", "value"),
    (("high", 98.0), ("close", 102.0), ("low", float("nan"))),
)
def test_nonfinite_inverted_or_outside_geometry_still_fails(
    monkeypatch: pytest.MonkeyPatch, column: str, value: float,
) -> None:
    monkeypatch.setattr(MODULE, "MIN_ROWS", 0)
    data = selected_frame(np.full(30, 100.0))
    data.loc[5, column] = value
    with pytest.raises(ValueError, match="high>=low"):
        MODULE.validate_selected_frame(data)


def test_flat_bars_do_not_reset_recursive_state_and_replay_is_deterministic() -> None:
    data = price_frame(flip_prices())
    for index in (0, 8, 9, 10, 22, 46):
        make_flat(data, index)
    first = MODULE.calculate_supertrend(data)
    second = MODULE.calculate_supertrend(data)
    np.testing.assert_allclose(first["atr"], second["atr"], equal_nan=True)
    np.testing.assert_allclose(first["supertrend"], second["supertrend"], equal_nan=True)
    np.testing.assert_array_equal(first["state"], second["state"])
    assert np.all(first["state"][9:] != 0)


def test_zero_atr_coincident_bands_use_deterministic_upper_first_identity() -> None:
    data = price_frame(np.full(20, 100.0))
    data[["high", "low"]] = 100.0
    indicator = MODULE.calculate_supertrend(data)
    assert indicator["atr"][9] == pytest.approx(0.0)
    assert indicator["upper"][9] == indicator["lower"][9] == 100.0
    assert np.all(indicator["state"][9:] == MODULE.DOWN)
    assert np.all(indicator["supertrend"][9:] == 100.0)


def test_source_events_preserve_exact_formula_and_allowlist() -> None:
    events, report = MODULE.analyze_frame(price_frame(flip_prices()))
    assert [row["direction"] for row in events] == ["LONG", "SHORT"]
    assert all(row["hypothesis_id"] == MODULE.HYPOTHESIS_ID for row in events)
    MODULE.assert_outcome_blind(events, report)
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert report["geometry_contract"] == "finite_high_gte_low_close_inside_range_flat_bars_valid_no_resets"


def test_raw_gap_flip_is_consumed_without_next_price() -> None:
    data = price_frame(flip_prices())
    data.loc[24:, "time_utc"] = data.loc[24:, "time_utc"] + pd.Timedelta(hours=1)
    events, report = MODULE.analyze_frame(data)
    assert [row["direction"] for row in events] == ["SHORT"]
    assert report["funnel"]["raw_events"] == 2
    assert report["funnel"]["gap_rejected_events"] == 1


def test_registry_requires_explicit_flat_bar_authority(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    row = {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "state": "probe",
        "parent_candidate": "HYP-ST-XAUUSD-H1-001",
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.PREREG_SHA256,
        "metrics": {"source_feasibility_attempts_consumed": 0},
        "validation": {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
            "source_feasibility_attempt_limit": 1,
            "source_run_authorized": True,
            "source_feasibility_only": True,
            "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
            "formula_dependency_sha256": MODULE.FORMULA_DEPENDENCY_SHA256,
            "prehistory_source_access_authorized": True,
            "flat_bar_source_validity_authorized": False,
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
    with pytest.raises(ValueError, match="flat_bars"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
