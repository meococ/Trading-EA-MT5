from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "build_eurfxofi_007_source_quality.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi007", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def window(expected_records: int = 3, source_empty: bool = False):
    return MODULE.WindowSpec(
        request_id="ECBFX-2020-01-02",
        local_date="2020-01-02",
        split="TRAIN",
        start="2020-01-02T13:14:45.000Z",
        end="2020-01-02T13:15:00.000Z",
        filename=None if source_empty else "ECBFX-2020-01-02.dbn.zst",
        source_empty=source_empty,
        expected_bytes=0,
        expected_sha256=None,
        expected_records=expected_records,
    )


def frame(*, crossed: bool = False, outside: bool = False) -> pd.DataFrame:
    start = pd.Timestamp("2020-01-02T13:14:45Z")
    event_times = [start + pd.Timedelta(seconds=value) for value in (1, 6, 11)]
    if outside:
        event_times[-1] = start + pd.Timedelta(seconds=15)
    bid = [1.10000, 1.10005, 1.10010]
    ask = [1.10005, 1.10010, 1.10015]
    if crossed:
        bid[1], ask[1] = 1.10015, 1.10010
    result = pd.DataFrame(
        {
            "ts_event": event_times,
            "action": ["T", "T", "T"],
            "side": ["B", "A", "N"],
            "price": [1.10005, 1.10005, 1.10010],
            "size": [3, 2, 1],
            "bid_px_00": bid,
            "ask_px_00": ask,
            "bid_sz_00": [10, 8, 9],
            "ask_sz_00": [5, 8, 12],
        },
        index=pd.DatetimeIndex(event_times, name="ts_recv"),
    )
    return result


def test_frozen_side_and_three_bin_transform() -> None:
    row = MODULE.aggregate_window_frame(frame(), window())
    assert row["records"] == 3
    assert row["buy_volume"] == 3.0
    assert row["sell_volume"] == 2.0
    assert row["unclassified_volume"] == 1.0
    assert row["classified_volume_share"] == pytest.approx(5.0 / 6.0)
    assert row["flow_signed"] == 1.0
    assert row["flow_imbalance"] == pytest.approx(0.2)
    assert row["bin1_flow_imbalance"] == 1.0
    assert row["bin2_flow_imbalance"] == -1.0
    assert math.isnan(row["bin3_flow_imbalance"])
    assert row["bin1_trade_count"] == 1
    assert row["bin2_trade_count"] == 1
    assert row["bin3_trade_count"] == 1
    assert row["median_spread_ticks"] == pytest.approx(1.0)
    assert row["crossed_records"] == 0


def test_out_of_window_and_crossed_book_fail_closed() -> None:
    with pytest.raises(MODULE.SourceQualityError, match="outside frozen window"):
        MODULE.aggregate_window_frame(frame(outside=True), window())
    with pytest.raises(MODULE.SourceQualityError, match="crossed book"):
        MODULE.aggregate_window_frame(frame(crossed=True), window())


def test_source_empty_row_is_explicit_and_null_featured() -> None:
    empty = pd.DataFrame()
    row = MODULE.aggregate_window_frame(empty, window(expected_records=0, source_empty=True))
    assert row["source_empty"] is True
    assert row["records"] == 0
    assert row["flow_imbalance"] is None
    assert row["bin1_flow_imbalance"] is None
    assert row["total_volume"] == 0.0


def test_record_count_and_required_fields_fail_closed() -> None:
    with pytest.raises(MODULE.SourceQualityError, match="record count mismatch"):
        MODULE.aggregate_window_frame(frame().iloc[:2], window())
    with pytest.raises(MODULE.SourceQualityError, match="missing TBBO fields"):
        MODULE.aggregate_window_frame(frame().drop(columns=["side"]), window())
