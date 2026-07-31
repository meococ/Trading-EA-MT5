from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "build_eurfxofi_011_source_quality.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi011", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@dataclass
class WindowSpec:
    request_id: str = "TEST"
    local_date: str = "2018-01-18"
    split: str = "TRAIN"
    start: str = "2018-01-18T13:14:45Z"
    end: str = "2018-01-18T13:15:00Z"
    filename: str | None = "TEST.dbn.zst"
    source_empty: bool = False
    expected_bytes: int = 1
    expected_sha256: str | None = "A" * 64
    expected_records: int = 2


def _frame(recv: list[str], event: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {"ts_event": pd.to_datetime(event, utc=True), "side": ["B"] * len(recv)},
        index=pd.DatetimeIndex(pd.to_datetime(recv, utc=True), name="ts_recv"),
    )


def test_disarmed_sentinel_normalization_is_stable() -> None:
    assert MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_builder_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert MODULE.normalized_builder_base_sha256(armed) == base


def test_receive_time_range_accepts_early_publisher_event() -> None:
    frame = _frame(
        ["2018-01-18T13:14:45.000118568Z", "2018-01-18T13:14:53.000000000Z"],
        ["2018-01-18T13:14:44.999026305Z", "2018-01-18T13:14:52.999700000Z"],
    )

    def original(proxy: pd.DataFrame, spec: WindowSpec) -> dict[str, object]:
        assert (pd.to_datetime(proxy["ts_event"], utc=True).array == proxy.index.array).all()
        return {"request_id": spec.request_id}

    row = MODULE.aggregate_window_frame_011(object(), original, frame, WindowSpec())
    assert row["timestamp_index"] == "ts_recv"
    assert row["ts_recv_outside_count"] == 0
    assert row["event_before_start_count"] == 1
    assert row["event_after_end_count"] == 0
    assert row["max_abs_event_to_recv_us"] == pytest.approx(1092.263)


def test_receive_time_outside_range_is_fatal_even_if_event_is_inside() -> None:
    frame = _frame(
        ["2018-01-18T13:14:44.999999999Z"],
        ["2018-01-18T13:14:45.000000000Z"],
    )
    with pytest.raises(MODULE.SourceQualityError, match="ts_recv outside"):
        MODULE.aggregate_window_frame_011(object(), lambda frame, spec: {}, frame, WindowSpec(expected_records=1))


def test_missing_receive_time_index_is_fatal() -> None:
    frame = _frame(
        ["2018-01-18T13:14:46Z"],
        ["2018-01-18T13:14:46Z"],
    ).rename_axis("wrong_clock")
    with pytest.raises(MODULE.SourceQualityError, match="missing Databento ts_recv"):
        MODULE.aggregate_window_frame_011(object(), lambda frame, spec: {}, frame, WindowSpec(expected_records=1))


def test_source_empty_row_preserves_receive_time_contract() -> None:
    spec = WindowSpec(filename=None, source_empty=True, expected_records=0)
    row = MODULE.aggregate_window_frame_011(
        object(), lambda frame, spec: {"request_id": spec.request_id}, pd.DataFrame(), spec
    )
    assert row["timestamp_index"] == "ts_recv"
    assert row["ts_recv_outside_count"] == 0
    assert row["median_event_to_recv_us"] is None


def test_authority_fails_while_disarmed(tmp_path: Path) -> None:
    with pytest.raises(MODULE.SourceQualityError, match="not armed"):
        MODULE.verify_authority(tmp_path)
