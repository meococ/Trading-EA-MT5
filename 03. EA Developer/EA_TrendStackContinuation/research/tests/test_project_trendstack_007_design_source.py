import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from project_trendstack_007_design_source import (
    EXPECTED_ARROW_SCHEMA,
    DecodedShard,
    ProjectionAuthority,
    ProjectionShape,
    bounded_public_shard_reader,
    canonical_json,
    pyarrow_projection_codecs,
    project_stage_from_paths,
    project_stage_synthetic,
    stable_read_regular,
    verified_clock_functions,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _selection(dates):
    return b"".join(
        canonical_json({"date": day, "schema_version": "trendstack_006_design_date_selection.v1"}) + b"\n"
        for day in dates
    )


def _date_set_sha(dates):
    payload = b"trendstack_002_design_date_set.v1\n" + b"".join(day.encode("ascii") + b"\n" for day in dates)
    return _sha(payload)


def _row(day, hour=12, *, offset=2):
    utc = datetime.fromisoformat(f"{day}T{hour:02d}:00:00")
    return {
        "time_server": utc + timedelta(hours=offset),
        "time_utc": utc,
        "utc_offset_h": offset,
        "open": 1.10,
        "high": 1.12,
        "low": 1.09,
        "close": 1.11,
        "tick_volume": 100,
        "spread": 12,
        "real_volume": 0,
    }


def _synthetic_case(tmp_path, *, selected=("2016-01-04", "2016-01-05"), extras=("2016-01-06",)):
    all_dates = tuple(sorted(selected + extras))
    payloads = {day: ("parquet-" + day).encode("ascii") for day in all_dates}
    manifest_rows = [
        {
            "bytes": len(payloads[day]),
            "date": day,
            "relative_path": f"public/DESIGN/{day}/h1.parquet",
            "rows": 2,
            "schema_version": "h1_splitvault_002_public_design_shard.v1",
            "sha256": _sha(payloads[day]),
        }
        for day in all_dates
    ]
    public_manifest = b"".join(canonical_json(row) + b"\n" for row in manifest_rows)
    public_receipt = canonical_json(
        {
            "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
            "design_dates": len(all_dates),
            "design_manifest_sha256": _sha(public_manifest),
            "raw_source_opens": 1,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "schema_version": "h1_splitvault_002_public_receipt.v1",
            "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
            "source_rows": 123,
            "unselected_shard_opens": 0,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
    ) + b"\n"
    selection = _selection(selected)
    opens = {day: 0 for day in all_dates}

    def reader(day, relative_path):
        assert relative_path == f"public/DESIGN/{day}/h1.parquet"
        opens[day] += 1
        return payloads[day]

    def decoder(payload):
        day = payload.decode("ascii").removeprefix("parquet-")
        return DecodedShard(EXPECTED_ARROW_SCHEMA, 1, (_row(day, 11), _row(day, 12)))

    def encoder(row):
        return canonical_json({key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()})

    def output_decoder(payload):
        raw = json.loads(payload)
        raw["time_server"] = datetime.fromisoformat(raw["time_server"])
        raw["time_utc"] = datetime.fromisoformat(raw["time_utc"])
        return DecodedShard(EXPECTED_ARROW_SCHEMA, 1, (raw,))

    authority = ProjectionAuthority(
        projection_attempt_id="HYP007-SOURCE-PROJECTION-ABCDEF1234567890",
        active_contract_sha256="A" * 64,
        task_packet_sha256="B" * 64,
        public_receipt_sha256=_sha(public_receipt),
        public_manifest_sha256=_sha(public_manifest),
        selection_manifest_sha256=_sha(selection),
    )
    shape = ProjectionShape(
        expected_dates=len(selected),
        expected_unselected_dates=len(extras),
        expected_date_set_sha256=_date_set_sha(selected),
        first_date=selected[0],
        last_date=selected[-1],
    )
    return {
        "stage": tmp_path / "stage",
        "authority": authority,
        "shape": shape,
        "receipt": public_receipt,
        "manifest": public_manifest,
        "selection": selection,
        "reader": reader,
        "decoder": decoder,
        "encoder": encoder,
        "output_decoder": output_decoder,
        "opens": opens,
        "selected": selected,
        "extras": extras,
        "payloads": payloads,
    }


def _project(case, **overrides):
    values = {
        "stage_root": case["stage"],
        "authority": case["authority"],
        "shape": case["shape"],
        "public_receipt": case["receipt"],
        "public_manifest": case["manifest"],
        "selection_manifest": case["selection"],
        "shard_reader": case["reader"],
        "decode_input": case["decoder"],
        "encode_output": case["encoder"],
        "decode_output": case["output_decoder"],
        "server_offset_hours": lambda value: 2,
        "server_to_utc": lambda value: value - timedelta(hours=2),
    }
    values.update(overrides)
    return project_stage_synthetic(**values)


def test_projector_builds_complete_stage_and_never_opens_unselected(tmp_path):
    case = _synthetic_case(tmp_path)
    result = _project(case)

    assert result["output_shards"] == len(case["selected"])
    assert result["output_rows"] == len(case["selected"])
    assert case["opens"] == {
        **{day: 1 for day in case["selected"]},
        **{day: 0 for day in case["extras"]},
    }
    assert set(result["stage_metadata_hashes"]) == {
        "projection_requests.jsonl", "projection_request_receipt.json",
        "design_1200_manifest.jsonl", "design_1200_source_trace.jsonl",
        "design_1200_reconciliation.json", "design_1200_projector_receipt.json",
    }
    assert all((case["stage"] / name).is_file() for name in result["stage_metadata_hashes"])
    assert len(list((case["stage"] / "DESIGN").rglob("*.parquet"))) == len(case["selected"])


def test_path_surface_owns_metadata_reads_inside_workspace(tmp_path):
    case = _synthetic_case(tmp_path)
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    receipt_path = metadata / "receipt.json"
    manifest_path = metadata / "manifest.jsonl"
    selection_path = metadata / "selection.jsonl"
    receipt_path.write_bytes(case["receipt"])
    manifest_path.write_bytes(case["manifest"])
    selection_path.write_bytes(case["selection"])

    result = project_stage_from_paths(
        workspace_root=tmp_path,
        public_receipt_path=receipt_path,
        public_manifest_path=manifest_path,
        selection_manifest_path=selection_path,
        stage_root=case["stage"], authority=case["authority"], shape=case["shape"],
        shard_reader=case["reader"], decode_input=case["decoder"],
        encode_output=case["encoder"], decode_output=case["output_decoder"],
        server_offset_hours=lambda value: 2,
        server_to_utc=lambda value: value - timedelta(hours=2),
    )
    assert result["output_shards"] == len(case["selected"])


def test_lazy_production_capabilities_are_sha_bound_and_schema_exact(tmp_path):
    clock = tmp_path / "clock.py"
    clock.write_bytes(
        b"from datetime import timedelta\n"
        b"def server_offset_hours(value): return 2\n"
        b"def server_to_utc(value): return value - timedelta(hours=2)\n"
    )
    offset, to_utc = verified_clock_functions(clock, tmp_path, _sha(clock.read_bytes()))
    assert offset(datetime(2020, 1, 1, 14)) == 2
    assert to_utc(datetime(2020, 1, 1, 14)) == datetime(2020, 1, 1, 12)

    shard_root = tmp_path / "public" / "DESIGN"
    shard = shard_root / "2016-01-04" / "h1.parquet"
    shard.parent.mkdir(parents=True)
    shard.write_bytes(b"synthetic-shard")
    reader = bounded_public_shard_reader(tmp_path, shard_root)
    assert reader("2016-01-04", "public/DESIGN/2016-01-04/h1.parquet") == b"synthetic-shard"
    with pytest.raises(Exception):
        reader("2016-01-04", "public/DESIGN/2016-01-05/h1.parquet")

    decode, encode, decode_output = pyarrow_projection_codecs()
    payload = encode(_row("2016-01-04"))
    decoded = decode(payload)
    assert decoded.schema == EXPECTED_ARROW_SCHEMA
    assert decoded.row_groups == 1 and len(decoded.rows) == 1
    assert decode_output(payload).rows == decoded.rows


@pytest.mark.parametrize("mutation", ["rename", "order", "type", "nullable"])
def test_projector_rejects_exact_schema_mutations_before_stage_publish(tmp_path, mutation):
    case = _synthetic_case(tmp_path)
    schema = list(EXPECTED_ARROW_SCHEMA)
    if mutation == "rename":
        schema[0] = ("renamed", schema[0][1], schema[0][2])
    elif mutation == "order":
        schema[0], schema[1] = schema[1], schema[0]
    elif mutation == "type":
        schema[2] = (schema[2][0], "int16", schema[2][2])
    else:
        schema[3] = (schema[3][0], schema[3][1], False)
    case["decoder"] = lambda payload: DecodedShard(tuple(schema), 1, (_row(case["selected"][0], 12),))
    with pytest.raises(Exception):
        _project(case, decode_input=case["decoder"])


@pytest.mark.parametrize("rows", [(), (_row("2016-01-04", 11),), (_row("2016-01-04", 12), _row("2016-01-04", 12))])
def test_projector_rejects_missing_or_duplicate_1200(tmp_path, rows):
    case = _synthetic_case(tmp_path, selected=("2016-01-04",), extras=())
    with pytest.raises(Exception):
        _project(case, decode_input=lambda payload: DecodedShard(EXPECTED_ARROW_SCHEMA, 1, rows))


def test_projector_rejects_clock_bytes_sha_and_unselected_mapping(tmp_path):
    case = _synthetic_case(tmp_path, selected=("2016-01-04",), extras=("2016-01-05",))
    with pytest.raises(Exception):
        _project(case, server_to_utc=lambda value: value)

    case = _synthetic_case(tmp_path / "bytes", selected=("2016-01-04",), extras=())
    case["reader"] = lambda day, relative: b"drift"
    with pytest.raises(Exception):
        _project(case, shard_reader=case["reader"])

    case = _synthetic_case(tmp_path / "mapping", selected=("2016-01-04",), extras=("2016-01-05",))
    selection = _selection(("2016-01-05",))
    with pytest.raises(Exception):
        _project(case, selection_manifest=selection)


def test_projector_rejects_frozen_upstream_access_count_mismatch(tmp_path):
    case = _synthetic_case(tmp_path)
    receipt = json.loads(case["receipt"])
    receipt["unselected_shard_opens"] = 1
    with pytest.raises(Exception):
        _project(case, public_receipt=canonical_json(receipt) + b"\n")


def test_stable_reader_rejects_escape_symlink_and_hardlink(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    regular = root / "regular.bin"
    regular.write_bytes(b"ok")
    assert stable_read_regular(regular, root) == b"ok"
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"no")
    with pytest.raises(Exception):
        stable_read_regular(outside, root)

    link = root / "link.bin"
    try:
        link.symlink_to(regular)
    except OSError:
        pass
    else:
        with pytest.raises(Exception):
            stable_read_regular(link, root)

    hard = root / "hard.bin"
    os.link(regular, hard)
    with pytest.raises(Exception):
        stable_read_regular(regular, root)


def test_projector_rejects_existing_stage_and_atomic_writes_do_not_replace(tmp_path):
    case = _synthetic_case(tmp_path)
    case["stage"].mkdir()
    with pytest.raises(Exception):
        _project(case)
