import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_splitvault_002_custodian import (
    EXPECTED_SCHEMA,
    CustodyAuthority,
    InvalidCustody,
    RawSourceCapability,
    SelectedShardCapability,
    run_custody,
    verify_source_payload,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _parquet_payload(tmp_path: Path) -> bytes:
    table = pa.table(
        {
            "time_server": pa.array([0], type=pa.timestamp("ns")),
            "time_utc": pa.array([0], type=pa.timestamp("ns")),
            "utc_offset_h": pa.array([0], type=pa.int8()),
            "open": pa.array([1.1], type=pa.float64()),
            "high": pa.array([1.2], type=pa.float64()),
            "low": pa.array([1.0], type=pa.float64()),
            "close": pa.array([1.15], type=pa.float64()),
            "tick_volume": pa.array([10], type=pa.uint64()),
            "spread": pa.array([1], type=pa.int32()),
            "real_volume": pa.array([0], type=pa.uint64()),
        },
        schema=EXPECTED_SCHEMA,
    )
    path = tmp_path / "synthetic.parquet"
    pq.write_table(table, path)
    return path.read_bytes()


def _authority(payload: bytes) -> CustodyAuthority:
    footer_length = int.from_bytes(payload[-8:-4], "little")
    footer_start = len(payload) - 8 - footer_length
    return CustodyAuthority(
        source_sha256=_sha(payload),
        source_bytes=len(payload),
        source_footer_length=footer_length,
        source_footer_start=footer_start,
        source_footer_sha256=_sha(payload[footer_start:]),
        source_manifest_sha256="A" * 64,
        clock_sha256="B" * 64,
        collection_plan_v1_sha256="C" * 64,
        collection_plan_v2_sha256="D" * 64,
        registry_row_index=282,
        registry_row_sha256="5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E",
        source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
        expected_source_rows=1,
    )


def test_raw_source_can_open_only_after_valid_attempt_marker_and_only_once(tmp_path):
    payload = _parquet_payload(tmp_path)
    authority = _authority(payload)
    cap = RawSourceCapability(lambda: payload, authority)
    marker = {
        "verdict": "ATTEMPT_CONSUMED",
        "source_attempt_id": authority.source_attempt_id,
        "registry_row_index": 282,
        "registry_row_sha256": authority.registry_row_sha256,
        "source_sha256": authority.source_sha256,
    }

    with pytest.raises(InvalidCustody):
        cap.open_after_marker({**marker, "verdict": "NOT_STARTED"})

    assert cap.open_after_marker(marker) == payload
    with pytest.raises(InvalidCustody):
        cap.open_after_marker(marker)


def test_verify_source_payload_binds_whole_file_footer_schema_and_provenance(tmp_path):
    payload = _parquet_payload(tmp_path)
    result = verify_source_payload(payload, _authority(payload))

    assert result["source_sha256"] == _sha(payload)
    assert result["schema_status"] == "PASS_EXACT_ARROW_SCHEMA_BID_CLOSED_H1"
    assert result["registry_row_index"] == 282

    bad = bytearray(payload)
    bad[-9] ^= 1
    with pytest.raises(InvalidCustody):
        verify_source_payload(bytes(bad), _authority(payload))


def test_wrong_packet_review_or_marker_binding_fails_before_raw_open(tmp_path):
    payload = _parquet_payload(tmp_path)
    authority = _authority(payload)
    opened = {"count": 0}

    def reader():
        opened["count"] += 1
        return payload

    cap = RawSourceCapability(reader, authority)
    with pytest.raises(InvalidCustody):
        cap.open_after_marker(
            {
                "verdict": "ATTEMPT_CONSUMED",
                "source_attempt_id": "HYP006-SOURCE-ATTEMPT-0000000000000000",
                "registry_row_index": 282,
                "registry_row_sha256": authority.registry_row_sha256,
                "source_sha256": authority.source_sha256,
            }
        )
    assert opened["count"] == 0


def test_raw_open_failure_is_consumed_before_reader_returns(tmp_path):
    payload = _parquet_payload(tmp_path)
    authority = _authority(payload)
    calls = {"count": 0}

    def reader():
        calls["count"] += 1
        raise RuntimeError("boom")

    cap = RawSourceCapability(reader, authority)
    marker = {
        "verdict": "ATTEMPT_CONSUMED",
        "source_attempt_id": authority.source_attempt_id,
        "registry_row_index": 282,
        "registry_row_sha256": authority.registry_row_sha256,
        "source_sha256": authority.source_sha256,
    }
    with pytest.raises(InvalidCustody):
        cap.open_after_marker(marker)
    with pytest.raises(InvalidCustody):
        cap.open_after_marker(marker)
    assert calls["count"] == 1


def test_selected_shard_failure_is_consumed_before_reader_returns():
    calls = {"count": 0}

    def reader(day):
        calls["count"] += 1
        raise RuntimeError(day)

    cap = SelectedShardCapability(
        selected_dates=("2016-01-04",),
        selected_hashes={"2016-01-04": "A" * 64},
        day_reader=reader,
    )
    with pytest.raises(InvalidCustody):
        cap.read_design_day("2016-01-04")
    with pytest.raises(InvalidCustody):
        cap.read_design_day("2016-01-04")
    assert calls["count"] == 1


def test_hash_failure_consumes_raw_and_selected_capabilities(tmp_path):
    payload = _parquet_payload(tmp_path)
    authority = _authority(payload)
    marker = {
        "verdict": "ATTEMPT_CONSUMED",
        "source_attempt_id": authority.source_attempt_id,
        "registry_row_index": 282,
        "registry_row_sha256": authority.registry_row_sha256,
        "source_sha256": authority.source_sha256,
    }
    raw_calls = {"count": 0}

    def bad_raw():
        raw_calls["count"] += 1
        return payload + b"drift"

    raw = RawSourceCapability(bad_raw, authority)
    with pytest.raises(InvalidCustody):
        raw.open_after_marker(marker)
    with pytest.raises(InvalidCustody):
        raw.open_after_marker(marker)
    assert raw_calls["count"] == 1
    assert raw.attempted_open_count() == 1

    selected_calls = {"count": 0}

    def bad_selected(_day):
        selected_calls["count"] += 1
        return b"wrong"

    selected = SelectedShardCapability(
        selected_dates=("2016-01-04",),
        selected_hashes={"2016-01-04": "A" * 64},
        day_reader=bad_selected,
    )
    with pytest.raises(InvalidCustody):
        selected.read_design_day("2016-01-04")
    with pytest.raises(InvalidCustody):
        selected.read_design_day("2016-01-04")
    assert selected_calls["count"] == 1
    assert selected.attempted_open_counts() == {"2016-01-04": 1}


def test_custody_rejects_auxiliary_null_and_multiple_row_groups(tmp_path):
    base = {
        "time_server": pa.array([0, 1], type=pa.timestamp("ns")),
        "time_utc": pa.array([0, 1], type=pa.timestamp("ns")),
        "utc_offset_h": pa.array([0, 0], type=pa.int8()),
        "open": pa.array([1.1, 1.1], type=pa.float64()),
        "high": pa.array([1.2, 1.2], type=pa.float64()),
        "low": pa.array([1.0, 1.0], type=pa.float64()),
        "close": pa.array([1.15, 1.15], type=pa.float64()),
        "tick_volume": pa.array([10, 10], type=pa.uint64()),
        "spread": pa.array([1, 1], type=pa.int32()),
        "real_volume": pa.array([0, 0], type=pa.uint64()),
    }
    table = pa.table(base, schema=EXPECTED_SCHEMA)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, row_group_size=1)
    payload = sink.getvalue().to_pybytes()
    authority = _authority(payload)
    object.__setattr__(authority, "expected_source_rows", 2)
    with pytest.raises(InvalidCustody):
        verify_source_payload(payload, authority)

    base["tick_volume"] = pa.array([10, None], type=pa.uint64())
    sink = pa.BufferOutputStream()
    pq.write_table(pa.table(base, schema=EXPECTED_SCHEMA), sink)
    null_payload = sink.getvalue().to_pybytes()
    null_authority = _authority(null_payload)
    object.__setattr__(null_authority, "expected_source_rows", 2)
    with pytest.raises(InvalidCustody):
        verify_source_payload(null_payload, null_authority)


def test_custody_rejects_bound_clock_drift(tmp_path):
    payload = _parquet_payload(tmp_path)
    authority = _authority(payload)
    object.__setattr__(authority, "clock_converter", lambda server: server + timedelta(hours=1))
    with pytest.raises(InvalidCustody):
        verify_source_payload(payload, authority)


def test_custody_split_reconciliation_drift_fails_after_exactly_one_raw_open(tmp_path):
    timestamps = [
        datetime(2016, 1, 3, 12),
        datetime(2016, 1, 4, 12),
        datetime(2021, 1, 1, 12),
        datetime(2023, 1, 1, 12),
    ]
    rows = [
        {
            "time_server": value,
            "time_utc": value,
            "utc_offset_h": 0,
            "open": 1.1,
            "high": 1.2,
            "low": 1.0,
            "close": 1.15,
            "tick_volume": 10,
            "spread": 1,
            "real_volume": 0,
        }
        for value in timestamps
    ]
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(rows, schema=EXPECTED_SCHEMA), sink, row_group_size=4)
    payload = sink.getvalue().to_pybytes()
    manifest = b"EURUSD H1 closed bid\n"
    clock = b"synthetic clock\n"
    authority = _authority(payload)
    object.__setattr__(authority, "expected_source_rows", 4)
    object.__setattr__(authority, "source_manifest_sha256", _sha(manifest))
    object.__setattr__(authority, "clock_sha256", _sha(clock))
    object.__setattr__(authority, "expected_split_rows", (
        ("PRE_DESIGN", 0), ("DESIGN", 0), ("VALIDATION", 0), ("HOLDOUT", 0),
    ))
    marker = {
        "verdict": "ATTEMPT_CONSUMED",
        "source_attempt_id": authority.source_attempt_id,
        "registry_row_index": 282,
        "registry_row_sha256": authority.registry_row_sha256,
        "source_sha256": authority.source_sha256,
    }
    calls = {"count": 0}

    def reader():
        calls["count"] += 1
        return payload

    output = tmp_path / "h1_splitvault_002"
    stage = tmp_path / f".h1_splitvault_002.attempt-{authority.source_attempt_id}"
    with pytest.raises(InvalidCustody):
        run_custody(
            reader,
            source_manifest_payload=manifest,
            clock_payload=clock,
            output_root=output,
            stage_root=stage,
            authority=authority,
            marker=marker,
        )
    assert calls["count"] == 1
    assert not output.exists()
