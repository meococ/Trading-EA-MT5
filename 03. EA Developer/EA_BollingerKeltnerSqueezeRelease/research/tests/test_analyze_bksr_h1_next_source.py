from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_bksr_h1_next_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_bksr_h1_next_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def design_frame(count: int = 40) -> pd.DataFrame:
    times = pd.date_range(MODULE.DESIGN_START, periods=count, freq="1h")
    close = np.full(count, 100.0)
    close[24] = 102.0
    return pd.DataFrame({
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "source_epoch": [int(value.timestamp()) for value in times],
        "time_utc": times,
        "utc_ambiguous": False,
        "high": np.maximum(close, 103.0),
        "low": np.minimum(close, 97.0),
        "close": close,
    })


def synthetic_bands(count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    basis = np.full(count, 100.0)
    bb_upper = np.full(count, 112.0)
    bb_lower = np.full(count, 88.0)
    kc_upper = np.full(count, 110.0)
    kc_lower = np.full(count, 90.0)
    bb_upper[22:24] = 105.0
    bb_lower[22:24] = 95.0
    return basis, bb_upper, bb_lower, kc_upper, kc_lower


def test_frozen_dependencies_match() -> None:
    assert MODULE.sha256_file(MODULE.BASE_PATH) == MODULE.BASE_SHA256
    assert MODULE.sha256_file(MODULE.ROOT / MODULE.PREREG_RELATIVE_PATH) == MODULE.PREREG_SHA256


def test_exact_next_h1_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_frame()
    monkeypatch.setattr(MODULE.BASE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    events, report = MODULE.analyze_frame(frame)
    assert len(events) == 1
    assert events[0]["source_bar_index"] == 24
    assert events[0]["decision_source_epoch"] == events[0]["source_bar_source_epoch"] + 3600
    assert report["events"]["raw"] == 1
    assert report["events"]["executable"] == 1
    MODULE.assert_outcome_blind(events, report)


@pytest.mark.parametrize("mutation", ["utc_gap", "epoch_gap", "sealed_boundary"])
def test_gap_or_boundary_consumes_event(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    frame = design_frame()
    monkeypatch.setattr(MODULE.BASE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    if mutation == "utc_gap":
        frame.loc[25:, "time_utc"] = pd.to_datetime(frame.loc[25:, "time_utc"], utc=True) + pd.Timedelta(hours=1)
    elif mutation == "epoch_gap":
        frame.loc[25:, "source_epoch"] += 3600
    else:
        frame.loc[24, "time_utc"] = MODULE.DESIGN_END - pd.Timedelta(hours=1)
        frame.loc[25, "time_utc"] = MODULE.DESIGN_END
        frame.loc[24, "source_epoch"] = int(frame.loc[24, "time_utc"].timestamp())
        frame.loc[25, "source_epoch"] = int(frame.loc[25, "time_utc"].timestamp())
    events, report = MODULE.analyze_frame(frame)
    assert events == []
    assert report["events"]["raw"] == 1
    assert report["events"]["gap_rejects"] + report["events"]["boundary_rejects"] == 1


def test_outcome_allowlist_rejects_forward_price(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_frame()
    monkeypatch.setattr(MODULE.BASE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    events, report = MODULE.analyze_frame(frame)
    invalid = dict(events[0], next_close=101.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)


def test_year_bucket_uses_decision_year_across_new_year(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_frame()
    start = pd.Timestamp("2018-12-30T23:00:00Z")
    times = pd.date_range(start, periods=len(frame), freq="1h")
    frame["time_utc"] = times
    frame["source_epoch"] = [int(value.timestamp()) for value in times]
    # Synthetic release remains at index 24: 2018-12-31 23:00, available 2019-01-01 00:00.
    monkeypatch.setattr(MODULE.BASE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    events, report = MODULE.analyze_frame(frame)
    assert len(events) == 1
    assert events[0]["source_bar_time_utc"] == "2018-12-31T23:00:00Z"
    assert events[0]["decision_time_utc"] == "2019-01-01T00:00:00Z"
    assert report["by_year"]["2018"] == 0
    assert report["by_year"]["2019"] == 1


def test_attempt_claim_is_exclusive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "artifact.bin"
    MODULE.exclusive_bytes(path, b"one")
    with pytest.raises(FileExistsError):
        MODULE.exclusive_bytes(path, b"two")
