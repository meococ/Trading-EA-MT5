from datetime import datetime
from dataclasses import replace
import json
import os
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_trendstack_006_design_source import (
    EXPECTED_SCHEMA,
    BuildShape,
    DesignSourceContract,
    InvalidDesignSource,
    build_design_source,
    build_design_source_for_testing,
    canonical_design_date_set_bytes,
    canonical_json,
    sha256_bytes,
)


ATTEMPT_ID = "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"


def _day_payload(day: str, hours=range(12, 19)) -> bytes:
    rows = []
    for hour in hours:
        utc = datetime.fromisoformat(f"{day}T{hour:02d}:00:00")
        rows.append(
            {
                "time_server": utc,
                "time_utc": utc,
                "utc_offset_h": 0,
                "open": 1.1,
                "high": 1.2,
                "low": 1.0,
                "close": 1.15,
                "tick_volume": 10,
                "spread": 1,
                "real_volume": 0,
            }
        )
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(rows, schema=EXPECTED_SCHEMA), sink)
    return sink.getvalue().to_pybytes()


def _day_payload_with_null(day: str) -> bytes:
    table = pq.read_table(pa.BufferReader(_day_payload(day)))
    columns = []
    for name in EXPECTED_SCHEMA.names:
        if name == "spread":
            columns.append(pa.array([1, 1, 1, None, 1, 1, 1], type=pa.int32()))
        else:
            columns.append(table[name])
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_arrays(columns, schema=EXPECTED_SCHEMA), sink)
    return sink.getvalue().to_pybytes()


class Capability:
    def __init__(self, payloads):
        self.payloads = dict(payloads)
        self.reads = {key: 0 for key in payloads}
        dates = tuple(sorted(payloads))
        self.selection = b"".join(
            canonical_json({"date": day, "schema_version": "trendstack_006_design_date_selection.v1"}) + b"\n"
            for day in dates
        )
        mapping_rows = []
        public_rows = []
        for day in dates:
            row = {
                "bytes": len(payloads[day]),
                "date": day,
                "relative_path": f"public/DESIGN/{day}/h1.parquet",
                "schema_version": "trendstack_006_selected_design_shard.v1",
                "sha256": sha256_bytes(payloads[day]),
            }
            mapping_rows.append(row)
            public_rows.append({**row, "rows": 7, "schema_version": "h1_splitvault_002_public_design_shard.v1"})
        self.mapping = b"".join(canonical_json(row) + b"\n" for row in mapping_rows)
        self.public_manifest = b"".join(canonical_json(row) + b"\n" for row in public_rows)
        self.public_receipt = canonical_json(
            {
                "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
                "design_dates": len(dates),
                "design_manifest_sha256": sha256_bytes(self.public_manifest),
                "raw_source_opens": 1,
                "research_holdout_opened": False,
                "research_validation_opened": False,
                "schema_version": "h1_splitvault_002_public_receipt.v1",
                "source_attempt_id": ATTEMPT_ID,
                "source_rows": sum(len(pq.read_table(pa.BufferReader(payload))) for payload in payloads.values()),
                "unselected_shard_opens": 0,
                "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
            }
        ) + b"\n"

    def design_dates(self):
        return tuple(sorted(self.payloads))

    def read_design_day(self, day):
        self.reads[day] += 1
        return self.payloads[day]

    def selection_manifest_bytes(self):
        return self.selection

    def selection_mapping_bytes(self):
        return self.mapping

    def public_receipt_bytes(self):
        return self.public_receipt

    def public_manifest_bytes(self):
        return self.public_manifest

    def open_count_summary(self):
        return {
            "raw_source_opens": 1,
            "selected_shard_opens": sum(self.reads.values()),
            "unselected_shard_opens": 0,
        }


def _shape(dates):
    return BuildShape(
        sha256_bytes(canonical_design_date_set_bytes(tuple(dates))),
        len(dates),
        7,
        7 * len(dates),
        dates[0],
        dates[-1],
    )


def _contract(tmp_path, cap):
    values = {key: "A" * 64 for key in (
        "builder_tool_sha256", "custodian_tool_sha256", "validator_tool_sha256",
        "custodian_test_sha256", "supervisor_test_sha256", "builder_test_sha256",
        "validator_test_sha256", "collection_plan_v1_sha256", "collection_plan_v2_sha256",
        "probe_plan_v1_sha256", "probe_plan_v2_sha256", "registry_sha256", "packet_sha256",
        "supervisor_review_base_sha256",
    )}
    return DesignSourceContract(
        **values,
        registry_row_index=282,
        registry_row_sha256="5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E",
        source_attempt_id=ATTEMPT_ID,
        design_stage_path=str(tmp_path / f".trendstack_006_design_h1.attempt-{ATTEMPT_ID}"),
        stage_role="DESIGN",
        custodian_public_receipt_sha256=sha256_bytes(cap.public_receipt),
        custodian_public_manifest_sha256=sha256_bytes(cap.public_manifest),
        selection_manifest_sha256=sha256_bytes(cap.selection),
        selection_mapping_sha256=sha256_bytes(cap.mapping),
    )


def _build(cap, output, contract, dates):
    return build_design_source_for_testing(cap, output, contract, shape=_shape(dates))


def test_v7_contract_uses_only_canonical_registry_row_authority(tmp_path):
    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    contract = _contract(tmp_path, cap)
    assert "source_run_registry_row_index" not in contract.__dataclass_fields__
    assert "source_run_registry_row_sha256" not in contract.__dataclass_fields__
    assert contract.registry_row_index == 282
    assert contract.registry_row_sha256 == "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E"

    output = tmp_path / "trendstack_006_design_h1"
    result = _build(cap, output, contract, dates)
    receipt = json.loads((output / "design_h1_source_receipt.json").read_bytes())
    assert result["registry_row_index"] == receipt["registry_row_index"] == 282
    assert result["registry_row_sha256"] == receipt["registry_row_sha256"] == contract.registry_row_sha256
    assert not {"source_run_registry_row_index", "source_run_registry_row_sha256"} & set(receipt)


@pytest.mark.parametrize(
    "changes",
    [
        {"registry_row_index": 283},
        {"registry_row_index": 999999},
        {"registry_row_sha256": "F" * 64},
    ],
)
def test_v7_builder_rejects_noncanonical_registry_authority(tmp_path, changes):
    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    with pytest.raises(InvalidDesignSource):
        _build(
            cap,
            tmp_path / "trendstack_006_design_h1",
            replace(_contract(tmp_path, cap), **changes),
            dates,
        )


def test_build_source_emits_exact_7_h1_rows_per_selected_date_and_no_extras(tmp_path):
    dates = ["2016-01-04", "2016-01-05"]
    cap = Capability({day: _day_payload(day) for day in dates})
    output = tmp_path / "trendstack_006_design_h1"
    result = _build(cap, output, _contract(tmp_path, cap), dates)
    assert result["verdict"] == "PENDING_INDEPENDENT_VALIDATION"
    assert result["h1_rows"] == 14
    assert cap.reads == {"2016-01-04": 1, "2016-01-05": 1}
    assert len((output / "design_h1_manifest.jsonl").read_text().splitlines()) == 2


def test_production_entrypoint_cannot_accept_fixture_shape(tmp_path):
    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    with pytest.raises(InvalidDesignSource):
        build_design_source(cap, tmp_path / "trendstack_006_design_h1", _contract(tmp_path, cap))


def test_build_rejects_missing_duplicate_or_out_of_window_rows(tmp_path):
    dates = ["2016-01-04"]
    for name, payload in (
        ("trendstack_006_design_h1", _day_payload(dates[0], hours=[12, 13, 14, 15, 16, 17])),
        ("other", _day_payload(dates[0], hours=[12, 13, 14, 15, 16, 17, 19])),
        ("third", _day_payload("2016-01-05")),
    ):
        cap = Capability({dates[0]: payload})
        contract = _contract(tmp_path, cap)
        object.__setattr__(contract, "design_stage_path", str(tmp_path / f".{name}.attempt-{ATTEMPT_ID}"))
        with pytest.raises(InvalidDesignSource):
            _build(cap, tmp_path / name, contract, dates)


def test_build_refuses_preexisting_output_or_stage_contamination(tmp_path):
    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    contract = _contract(tmp_path, cap)
    output = tmp_path / "trendstack_006_design_h1"
    output.mkdir()
    with pytest.raises(InvalidDesignSource):
        _build(cap, output, contract, dates)
    output.rmdir()
    stage = Path(contract.design_stage_path)
    stage.mkdir()
    (stage / "contamination").write_text("x")
    with pytest.raises(InvalidDesignSource):
        _build(cap, output, contract, dates)


def test_build_rejects_empty_existing_stage_and_auxiliary_null(tmp_path):
    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    contract = _contract(tmp_path, cap)
    output = tmp_path / "trendstack_006_design_h1"
    stage = Path(contract.design_stage_path)
    stage.mkdir()
    with pytest.raises(InvalidDesignSource):
        _build(cap, output, contract, dates)
    stage.rmdir()
    cap = Capability({dates[0]: _day_payload_with_null(dates[0])})
    with pytest.raises(InvalidDesignSource):
        _build(cap, output, _contract(tmp_path, cap), dates)


def test_build_rejects_ads_or_reparse_parent_before_any_selected_read(tmp_path):
    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    if os.name == "nt":
        stream = Path(str(tmp_path) + ":economic_leak")
        try:
            stream.write_bytes(b"leak")
        except OSError:
            pytest.skip("alternate data streams unavailable")
        with pytest.raises(InvalidDesignSource):
            _build(cap, tmp_path / "trendstack_006_design_h1", _contract(tmp_path, cap), dates)
        assert cap.reads == {dates[0]: 0}
        return

    target = tmp_path / "actual"
    target.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    contract = _contract(link, cap)
    with pytest.raises(InvalidDesignSource):
        _build(cap, link / "trendstack_006_design_h1", contract, dates)
    assert cap.reads == {dates[0]: 0}


def test_build_detects_atomic_publication_identity_swap(tmp_path, monkeypatch):
    import build_trendstack_006_design_source as builder

    dates = ["2016-01-04"]
    cap = Capability({dates[0]: _day_payload(dates[0])})
    output = tmp_path / "trendstack_006_design_h1"
    real_rename = builder.os.rename

    def swapped_rename(source, destination):
        real_rename(source, destination)
        displaced = Path(destination).with_name(Path(destination).name + ".displaced")
        real_rename(destination, displaced)
        Path(destination).mkdir()

    monkeypatch.setattr(builder.os, "rename", swapped_rename)
    with pytest.raises(InvalidDesignSource):
        _build(cap, output, _contract(tmp_path, cap), dates)
