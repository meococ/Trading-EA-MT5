from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "build_event_aggflow_007_source_quality.py"
SPEC = importlib.util.spec_from_file_location("event_aggflow_007_source", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def trade(*, side: str, size: int = 3, ts_recv: int = 101, action: str = "T"):
    return SimpleNamespace(action=action, side=side, size=size, ts_recv=ts_recv)


def row(request_id: str, dominance: str, direct: int) -> dict:
    signed = 1 if dominance == "BUY" else -1 if dominance == "SELL" else 0
    return {
        "request_id": request_id,
        "event_time_utc": "2019-01-01T00:00:00.000Z",
        "start_utc": "2019-01-01T00:00:00.000Z",
        "end_utc": "2019-01-01T00:00:15.000Z",
        "coverage_kind": "dbn",
        "record_count": max(1, direct),
        "direct_record_count": direct,
        "unclassified_record_count": 0 if direct else 1,
        "buy_volume": 1 if dominance == "BUY" else 0,
        "sell_volume": 1 if dominance == "SELL" else 0,
        "signed_flow": signed,
        "dominance": dominance,
        "source_bytes": 10,
        "source_sha256": "A" * 64,
    }


def passing_rows() -> list[dict]:
    rows = []
    for index in range(131):
        rows.append(row(f"B{index:03d}", "BUY", 1))
    for index in range(130):
        rows.append(row(f"S{index:03d}", "SELL", 1))
    for index in range(52):
        rows.append(row(f"T{index:03d}", "TIE", 2))
    for index in range(16):
        rows.append(row(f"N{index:03d}", "NO_DIRECT", 0))
    return rows


def test_aggregate_records_uses_direct_aggressor_volume_only() -> None:
    values = MODULE.aggregate_records(
        [trade(side="B", size=7), trade(side="A", size=2), trade(side="N", size=99)],
        start_ns=100,
        end_ns=200,
    )
    assert values == {
        "record_count": 3,
        "direct_record_count": 2,
        "unclassified_record_count": 1,
        "buy_volume": 7,
        "sell_volume": 2,
        "signed_flow": 5,
    }


def test_half_open_receive_time_accepts_start_and_rejects_end() -> None:
    assert MODULE.aggregate_records([trade(side="B", ts_recv=100)], start_ns=100, end_ns=200)[
        "record_count"
    ] == 1
    with pytest.raises(MODULE.SourceQualityError, match="outside"):
        MODULE.aggregate_records([trade(side="B", ts_recv=200)], start_ns=100, end_ns=200)


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (trade(side="B", action="A"), "non-trade"),
        (trade(side="X"), "unknown aggressor"),
        (trade(side="B", size=0), "nonpositive"),
        (trade(side="B", size=-1), "nonpositive"),
        (SimpleNamespace(action="T", side="B", size=1, ts_recv="101"), "malformed"),
    ],
)
def test_record_integrity_violations_fail(record, message: str) -> None:
    with pytest.raises(MODULE.SourceQualityError, match=message):
        MODULE.aggregate_records([record], start_ns=100, end_ns=200)


def test_classification_has_explicit_no_source_no_direct_tie() -> None:
    base = {
        "direct_record_count": 0,
        "signed_flow": 0,
    }
    assert MODULE.classify_row(base, "live_zero_byte") == "NO_SOURCE"
    assert MODULE.classify_row(base, "dbn") == "NO_DIRECT"
    base["direct_record_count"] = 2
    assert MODULE.classify_row(base, "dbn") == "TIE"
    base["signed_flow"] = 1
    assert MODULE.classify_row(base, "dbn") == "BUY"
    base["signed_flow"] = -1
    assert MODULE.classify_row(base, "dbn") == "SELL"


def test_exact_frozen_feasibility_boundary_passes() -> None:
    summary = MODULE.summarize(passing_rows())
    assert summary["event_count"] == 329
    assert summary["events_with_direct_side"] == 313
    assert summary["nonzero_signed_flow_events"] == 261
    assert summary["buyer_dominant_events"] == 131
    assert summary["seller_dominant_events"] == 130
    assert summary["source_feasibility_pass"] is True


def test_feasibility_fails_without_changing_transform() -> None:
    rows = passing_rows()
    rows[0]["dominance"] = "TIE"
    rows[0]["signed_flow"] = 0
    summary = MODULE.summarize(rows)
    assert summary["nonzero_signed_flow_events"] == 260
    assert summary["gates"]["nonzero_events_at_least_261"] is False
    assert summary["source_feasibility_pass"] is False


def test_parse_utc_ns_is_exact_for_millisecond_clock() -> None:
    start = MODULE.parse_utc_ns("2019-01-03T15:00:00.000Z")
    end = MODULE.parse_utc_ns("2019-01-03T15:00:15.000Z")
    assert end - start == 15_000_000_000


def test_csv_output_contains_only_source_fields() -> None:
    payload = MODULE.csv_bytes([passing_rows()[0]])
    header = payload.splitlines()[0].decode("ascii")
    assert "signed_flow" in header
    for forbidden in ("eurusd", "return", "pnl", "profit_factor", "target"):
        assert forbidden not in header.lower()


def test_tool_has_no_network_client_or_api_key_loader() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "db.Historical(",
        "timeseries.get_range",
        "metadata.get_cost",
        "DATABENTO_API_KEY",
        "import requests",
        "import aiohttp",
    ):
        assert forbidden not in source


def test_exclusive_writer_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    MODULE.write_exclusive(path, b"one")
    with pytest.raises(FileExistsError):
        MODULE.write_exclusive(path, b"two")
    assert path.read_bytes() == b"one"
