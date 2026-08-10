from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_td9_h1_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_td9_h1_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_frame(count: int = 40) -> pd.DataFrame:
    times = pd.date_range(MODULE.SOURCE_START, periods=count, freq="1h")
    epochs = 1_086_937_200 + np.arange(count, dtype=np.int64) * 3600
    close = 120.0 - np.arange(count, dtype=float)
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False, "high": close + 1.0, "low": close - 1.0, "close": close})


def design_frame(count: int = 20, descending: bool = True, gap_after: int | None = None) -> pd.DataFrame:
    times = pd.date_range(MODULE.DESIGN_START, periods=count, freq="1h")
    epochs = 1_514_764_800 + np.arange(count, dtype=np.int64) * 3600
    if gap_after is not None:
        times = pd.DatetimeIndex([value + (pd.Timedelta(hours=1) if index > gap_after else pd.Timedelta(0)) for index, value in enumerate(times)])
        epochs[gap_after + 1 :] += 3600
    close = (120.0 - np.arange(count, dtype=float)) if descending else (80.0 + np.arange(count, dtype=float))
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False, "high": close + 1.0, "low": close - 1.0, "close": close})


def test_harness_dependency_and_h1_manifest_are_exact() -> None:
    assert MODULE.sha256_file(MODULE.HARNESS_PATH) == MODULE.HARNESS_SHA256
    manifest = json.loads((MODULE.ROOT / MODULE.MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")]
    assert len(matches) == 1 and matches[0]["sha256"] == MODULE.DATA_SHA256


def test_buy_setup_first_completes_at_index_12_and_latches() -> None:
    frame = design_frame(22, descending=True)
    long_event, short_event, late, reference = MODULE.setup_events(frame.high.to_numpy(), frame.low.to_numpy(), frame.close.to_numpy())
    assert np.flatnonzero(long_event).tolist() == [12]
    assert not short_event.any()
    assert late[12] < reference[12]


def test_sell_setup_is_strict_symmetric() -> None:
    frame = design_frame(22, descending=False)
    long_event, short_event, late, reference = MODULE.setup_events(frame.high.to_numpy(), frame.low.to_numpy(), frame.close.to_numpy())
    assert not long_event.any()
    assert np.flatnonzero(short_event).tolist() == [12]
    assert late[12] > reference[12]


def test_setup_equality_breaks_the_run() -> None:
    frame = design_frame(24, descending=True)
    frame.loc[8, "close"] = frame.loc[4, "close"]
    frame.loc[8, "high"] = frame.loc[8, "close"] + 1.0
    frame.loc[8, "low"] = frame.loc[8, "close"] - 1.0
    long_event, _, _, _ = MODULE.setup_events(frame.high.to_numpy(), frame.low.to_numpy(), frame.close.to_numpy())
    assert not long_event[:17].any()


def test_perfection_is_strict_and_equality_fails() -> None:
    frame = design_frame(16, descending=True)
    reference = min(frame.loc[9, "low"], frame.loc[10, "low"])
    frame.loc[11, "low"] = reference
    frame.loc[12, "low"] = reference
    long_event, _, _, _ = MODULE.setup_events(frame.high.to_numpy(), frame.low.to_numpy(), frame.close.to_numpy())
    assert not long_event[12]


def test_failed_bar9_perfection_is_consumed_not_delayed() -> None:
    frame = design_frame(18, descending=True)
    frame.loc[9, "low"] = 0.0
    frame.loc[10, "low"] = 0.0
    frame.loc[13, "low"] = -1.0
    long_event, _, _, _ = MODULE.setup_events(frame.high.to_numpy(), frame.low.to_numpy(), frame.close.to_numpy())
    assert not long_event.any()


def test_analyze_emits_exact_fields_and_direction() -> None:
    frame = design_frame(22, descending=True)
    events, report = MODULE.analyze_frame(frame)
    assert len(events) == 1 and events[0]["direction"] == "LONG"
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert events[0]["setup_count"] == 9
    assert report["funnel"]["raw_events"] == 1


def test_raw_gap_event_is_consumed() -> None:
    frame = design_frame(22, descending=True, gap_after=12)
    events, report = MODULE.analyze_frame(frame)
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_flat_bar_is_valid_but_equal_compare_breaks() -> None:
    frame = source_frame()
    frame.loc[8, ["high", "low", "close"]] = frame.loc[4, "close"]
    validated = MODULE.validate_frame(frame)
    assert validated.loc[8, "high"] == validated.loc[8, "low"] == validated.loc[8, "close"]
    long_event, _, _, _ = MODULE.setup_events(validated.high.to_numpy(), validated.low.to_numpy(), validated.close.to_numpy())
    assert not long_event[:17].any()


@pytest.mark.parametrize("column", ["symbol", "timeframe"])
def test_null_identity_fails_closed(column: str) -> None:
    frame = source_frame()
    frame.loc[1, column] = None
    with pytest.raises(ValueError, match="XAUUSD/H1"):
        MODULE.validate_frame(frame)


def test_outcome_blind_allowlist_rejects_next_price() -> None:
    frame = design_frame(22, descending=True)
    events, report = MODULE.analyze_frame(frame)
    MODULE.assert_outcome_blind(events, report)
    invalid = dict(events[0], next_close=100.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)


def authority_row() -> dict[str, object]:
    validation = {name: False for name in MODULE.FALSE_PERMISSIONS}
    validation.update({
        "source_feasibility_attempt_id": MODULE.ATTEMPT_ID, "source_feasibility_attempt_limit": 1,
        "source_run_authorized": True, "source_feasibility_only": True, "prehistory_source_access_authorized": True,
        "prehistory_source_start": MODULE.SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest_path": MODULE.MANIFEST_RELATIVE_PATH, "manifest_sha256": MODULE.MANIFEST_SHA256,
        "data_path": MODULE.DATA_RELATIVE_PATH, "data_sha256": MODULE.DATA_SHA256, "data_access_predicate": MODULE.DATA_ACCESS_PREDICATE,
        "reviewed_analyzer_path": MODULE.ANALYZER_RELATIVE_PATH, "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
        "reviewed_test_path": MODULE.TEST_RELATIVE_PATH, "reviewed_test_sha256": MODULE.TEST_SHA256,
        "harness_dependency_path": MODULE.HARNESS_RELATIVE_PATH, "harness_dependency_sha256": MODULE.HARNESS_SHA256,
    })
    metrics = {name: 0 for name in MODULE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    return {"hypothesis_id": MODULE.HYPOTHESIS_ID, "state": "probe", "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN", "prereg_sha256": MODULE.PREREG_SHA256, "run_ids": [], "metrics": metrics, "validation": validation}


@pytest.mark.parametrize("mutation", ["missing_direct", "direct_true", "attempt", "harness", "source_metric", "holdout"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    row = authority_row(); validation = row["validation"]; metrics = row["metrics"]
    assert isinstance(validation, dict) and isinstance(metrics, dict)
    if mutation == "missing_direct": validation.pop("direct_mql5_parity_authorized")
    elif mutation == "direct_true": validation["direct_mql5_parity_authorized"] = True
    elif mutation == "attempt": validation["source_feasibility_attempt_id"] = "WRONG"
    elif mutation == "harness": validation["harness_dependency_sha256"] = "0" * 64
    elif mutation == "source_metric": metrics["source_runs_executed"] = 1
    else: metrics["research_holdout_opened"] = True
    registry = tmp_path / "registry.jsonl"; registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="authority"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_and_frozen_rehash_are_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64, "analyzer_sha256": "C" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
    frozen = tmp_path / "frozen.bin"; frozen.write_bytes(b"frozen"); expected = {"frozen": MODULE.sha256_file(frozen)}
    assert MODULE.verify_frozen_inputs({"frozen": frozen}, expected) == expected
    frozen.write_bytes(b"drift")
    with pytest.raises(ValueError, match="frozen"):
        MODULE.verify_frozen_inputs({"frozen": frozen}, expected)
