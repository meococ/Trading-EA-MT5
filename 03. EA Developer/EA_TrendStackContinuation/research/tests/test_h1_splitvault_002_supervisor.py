import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_splitvault_002_supervisor import (
    DESIGN_DATE_SET_PREFIX,
    InvalidSupervisor,
    NarrowDesignCapability,
    build_child_payload,
    canonical_json,
    canonical_selection_bytes,
    preflight_selection_manifest,
    prepare_narrow_design_capability,
    validate_selection_mapping,
    validate_full_packet_document,
    validate_run_packet,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _selection(dates):
    payload = b"".join(
        canonical_json({"date": day, "schema_version": "trendstack_006_design_date_selection.v1"}) + b"\n"
        for day in dates
    )
    return payload, _sha(DESIGN_DATE_SET_PREFIX + b"".join(day.encode("ascii") + b"\n" for day in dates))


def test_selection_preflight_is_metadata_only_exact_1297_dates():
    start = date(2016, 1, 4)
    dates = [(start + timedelta(days=index)).isoformat() for index in range(1297)]
    payload, digest = _selection(dates)

    result = preflight_selection_manifest(payload, expected_count=1297, expected_date_set_sha256=digest)

    assert result.dates == tuple(dates)
    assert result.date_set_sha256 == digest
    assert canonical_selection_bytes(result.dates).startswith(DESIGN_DATE_SET_PREFIX)


def test_selection_rejects_duplicate_missing_and_feature_fields():
    good_dates = ["2016-01-04", "2016-01-05"]
    payload, digest = _selection(good_dates)
    with pytest.raises(InvalidSupervisor):
        preflight_selection_manifest(payload, expected_count=3, expected_date_set_sha256=digest)

    dup_payload, dup_digest = _selection(["2016-01-04", "2016-01-04"])
    with pytest.raises(InvalidSupervisor):
        preflight_selection_manifest(dup_payload, expected_count=2, expected_date_set_sha256=dup_digest)

    leaky = canonical_json(
        {"date": "2016-01-04", "m252": 1, "schema_version": "trendstack_006_design_date_selection.v1"}
    ) + b"\n"
    with pytest.raises(InvalidSupervisor):
        preflight_selection_manifest(leaky, expected_count=1, expected_date_set_sha256=_sha(leaky))


def test_child_payload_narrows_extras_and_never_reads_unselected_dates():
    selected = ("2016-01-04", "2016-01-05")
    reads = {"2016-01-04": 0, "2016-01-05": 0, "2016-01-06": 0}

    def reader(day):
        reads[day] += 1
        if day == "2016-01-06":
            raise AssertionError("extra date payload must not be opened")
        return (day + "-payload").encode("ascii")

    capability = NarrowDesignCapability(
        available_dates=("2016-01-04", "2016-01-05", "2016-01-06"),
        selected_dates=selected,
        selected_hashes={day: _sha((day + "-payload").encode("ascii")) for day in selected},
        day_reader=reader,
        public_receipt=b'{"verdict":"COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"}\n',
        public_manifest=b"manifest\n",
    )

    payload = build_child_payload(
        capability,
        selection_manifest=b"selection\n",
        contract={
            "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
            "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-006",
            "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
            "stage_role": "DESIGN",
            "output_capability": "trendstack_006_design_h1",
        },
    )

    assert tuple(payload["design_dates"]) == selected
    assert payload["actual_extra_design_dates"] == 1
    assert set(payload) == {
        "actual_extra_design_dates",
        "collection_id",
        "contract",
        "custody_manifest",
        "custody_receipt",
        "design_dates",
        "hypothesis_id",
        "selected_shards",
        "selection_manifest",
    }
    assert reads == {"2016-01-04": 1, "2016-01-05": 1, "2016-01-06": 0}


def test_selection_mapping_binds_date_path_hash_and_bytes_before_reads():
    dates = ("2016-01-04", "2016-01-05")
    rows = [
        {
            "bytes": 10,
            "date": "2016-01-04",
            "relative_path": "public/DESIGN/2016-01-04/h1.parquet",
            "schema_version": "trendstack_006_selected_design_shard.v1",
            "sha256": "A" * 64,
        },
        {
            "bytes": 11,
            "date": "2016-01-05",
            "relative_path": "public/DESIGN/2016-01-05/h1.parquet",
            "schema_version": "trendstack_006_selected_design_shard.v1",
            "sha256": "B" * 64,
        },
    ]
    payload = b"".join(canonical_json(row) + b"\n" for row in rows)
    assert validate_selection_mapping(payload, dates).mapping["2016-01-04"]["bytes"] == 10

    bad = dict(rows[1])
    bad["date"] = "2016-01-04"
    with pytest.raises(InvalidSupervisor):
        validate_selection_mapping(canonical_json(rows[0]) + b"\n" + canonical_json(bad) + b"\n", dates)


def test_packet_validation_disarmed_by_default_and_forbids_runtime_capabilities():
    packet = {
        "schema_version": "trendstack_006_source_run_packet.v1",
        "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-006",
        "registry_row_index": 282,
        "registry_row_sha256": "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E",
        "review_base_supervisor_sha256": "A" * 64,
        "runtime_supervisor_sha256": "B" * 64,
        "reviewed_run_packet_sha256": "C" * 64,
        "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
        "network_allowed": False,
        "subprocess_allowed": False,
        "economics_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "performance_metrics_authorized": False,
    }
    with pytest.raises(InvalidSupervisor):
        validate_run_packet(packet)
    with pytest.raises(TypeError):
        validate_run_packet(packet, reviewed_run_packet_sha256="C" * 64)

    bad = dict(packet)
    bad["network_allowed"] = True
    with pytest.raises(InvalidSupervisor):
        validate_run_packet(bad)

    with pytest.raises(InvalidSupervisor):
        validate_run_packet(packet)


def test_packet_placeholders_and_missing_full_bindings_are_rejected():
    packet = {
        "schema_version": "trendstack_006_source_run_packet.v1",
        "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-006",
        "registry_row_index": 282,
        "registry_row_sha256": "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E",
        "review_base_supervisor_sha256": "A" * 64,
        "runtime_supervisor_sha256": "B" * 64,
        "reviewed_run_packet_sha256": "C" * 64,
        "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
        "network_allowed": False,
        "subprocess_allowed": False,
        "economics_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "performance_metrics_authorized": False,
    }
    with pytest.raises(InvalidSupervisor):
        validate_run_packet(packet)


def _seal_packet(packet):
    import h1_splitvault_002_supervisor as supervisor

    packet["authority"] = supervisor.source_run_authority_template(packet, "0" * 64)
    detached = supervisor.compute_detached_packet_sha256(packet)
    packet["reviewed_run_packet_sha256"] = detached
    packet["authority"]["detached_packet_sha256"] = detached
    return detached


def _full_packet(module_fields, frozen_values):

    packet = {}
    for key in module_fields:
        if key.endswith("_sha256"):
            packet[key] = "A" * 64
        elif key.endswith("_path") or key.endswith("_root"):
            packet[key] = "D:/synthetic/" + key
        else:
            packet[key] = False
    packet.update(
        {
            "schema_version": "trendstack_006_h1_splitvault_source_run_packet.v1",
            "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
            "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-006",
            "registry_row_index": 282,
            "registry_row_sha256": "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E",
            "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
            "source_bytes": 2781897,
            "source_rows": 71785,
            "source_row_groups": 1,
            "source_footer_length": 5392,
            "source_footer_start": 2776497,
            "expected_design_dates": 1297,
            "expected_rows_per_day": 7,
            "expected_total_rows": 9079,
            "expected_raw_opens": 1,
            "expected_selected_opens": 1297,
            "expected_unselected_opens": 0,
            "one_shot_custody_source_attempt_authorized": True,
        }
    )
    packet.update(frozen_values)
    _seal_packet(packet)
    return packet


def test_full_canonical_packet_document_passes_but_execution_stays_disarmed():
    import h1_splitvault_002_supervisor as supervisor

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    payload = canonical_json(packet) + b"\n"
    result = validate_full_packet_document(payload, packet["reviewed_run_packet_sha256"])
    assert result["expected_total_rows"] == 9079
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None
    with pytest.raises(InvalidSupervisor):
        validate_run_packet(packet)

    for field, value in (
        ("expected_total_rows", 9078),
        ("source_path", "D:/synthetic/drift.parquet"),
        ("network_allowed", True),
    ):
        bad = dict(packet)
        bad[field] = value
        bad_payload = canonical_json(bad) + b"\n"
        with pytest.raises(InvalidSupervisor):
            validate_full_packet_document(bad_payload, packet["reviewed_run_packet_sha256"])


def test_narrow_capability_consumes_hash_failure_and_rejects_nested_leak_before_read():
    calls = {"count": 0}

    def reader(_day):
        calls["count"] += 1
        return b"wrong"

    cap = NarrowDesignCapability(
        available_dates=("2016-01-04", "2016-01-05"),
        selected_dates=("2016-01-04",),
        selected_hashes={"2016-01-04": "A" * 64},
        day_reader=reader,
        public_receipt=b'{}\n',
        public_manifest=b"mapping\n",
    )
    with pytest.raises(InvalidSupervisor):
        cap.read_design_day("2016-01-04")
    with pytest.raises(InvalidSupervisor):
        cap.read_design_day("2016-01-04")
    assert calls["count"] == 1
    assert cap.attempted_open_count() == 1

    untouched = NarrowDesignCapability(
        available_dates=("2016-01-04",),
        selected_dates=("2016-01-04",),
        selected_hashes={"2016-01-04": _sha(b"ok")},
        day_reader=lambda _day: b"ok",
        public_receipt=b'{}\n',
        public_manifest=b"mapping\n",
    )
    with pytest.raises(InvalidSupervisor):
        build_child_payload(
            untouched,
            selection_manifest=b"bad\n",
            contract={
                "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
                "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-006",
                "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
                "stage_role": "DESIGN",
                "output_capability": {"source_path": "forbidden"},
            },
        )
    assert untouched.attempted_open_count() == 0


def test_selection_mapping_reconciles_exact_extra_date_count():
    dates = ("2016-01-04",)
    rows = []
    for index, day in enumerate(("2016-01-04", "2016-01-05")):
        rows.append(
            {
                "bytes": 10 + index,
                "date": day,
                "relative_path": f"public/DESIGN/{day}/h1.parquet",
                "schema_version": "trendstack_006_selected_design_shard.v1",
                "sha256": chr(65 + index) * 64,
            }
        )
    payload = b"".join(canonical_json(row) + b"\n" for row in rows)
    mapping = validate_selection_mapping(payload, dates)
    assert mapping.extra_date_count == 1


def test_one_shot_lifecycle_orders_marker_before_pipeline_writes_terminal_and_self_disarms():
    import h1_splitvault_002_supervisor as supervisor

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    payload = canonical_json(packet) + b"\n"
    verified = validate_full_packet_document(payload, packet["reviewed_run_packet_sha256"])
    events = []

    class Operations:
        def preflight(self, accepted):
            assert accepted["source_attempt_id"] == packet["source_attempt_id"]
            events.append("preflight")
            return {"raw_opened": False}

        def start(self, accepted, context):
            assert context["raw_opened"] is False
            events.append("marker")
            return {"verdict": "ATTEMPT_CONSUMED"}, "B" * 64

        def pipeline(self, accepted, marker, context):
            assert marker["verdict"] == "ATTEMPT_CONSUMED"
            events.append("pipeline")
            return {"verdict": "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"}

        def disarm(self, accepted, context):
            events.append("disarm")
            return {
                "disarmed_supervisor_sha256": "D" * 64,
                "supervisor_sentinel_status": "DISARMED_NONE_VERIFIED",
                "arm_manifest_sha256": "E" * 64,
            }

        def terminal(self, accepted, marker_sha256, verdict, evidence, context):
            assert marker_sha256 == "B" * 64
            assert set(evidence) <= {
                "design_date_set_sha256",
                "source_receipt_sha256",
                "validated_dates",
                "validated_h1_rows",
                "validator_test_sha256",
                "validator_tool_sha256",
                "disarmed_supervisor_sha256",
                "supervisor_sentinel_status",
                "arm_manifest_sha256",
            }
            events.append(("terminal", verdict))
            return "C" * 64

    supervisor.REVIEWED_RUN_PACKET_SHA256 = packet["reviewed_run_packet_sha256"]
    result = supervisor._run_one_shot_lifecycle(verified, Operations())
    assert result["attempt_terminal_sha256"] == "C" * 64
    assert events == [
        "preflight",
        "marker",
        "pipeline",
        "disarm",
        ("terminal", "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"),
    ]
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


def test_one_shot_failure_after_marker_still_writes_sanitized_terminal_and_self_disarms():
    import h1_splitvault_002_supervisor as supervisor

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    payload = canonical_json(packet) + b"\n"
    verified = validate_full_packet_document(payload, packet["reviewed_run_packet_sha256"])
    terminal = []

    class Operations:
        def preflight(self, _accepted):
            return {}

        def start(self, _accepted, _context):
            return {"verdict": "ATTEMPT_CONSUMED"}, "B" * 64

        def pipeline(self, _accepted, _marker, _context):
            raise RuntimeError("private detail must not escape")

        def disarm(self, _accepted, _context):
            return {
                "disarmed_supervisor_sha256": "D" * 64,
                "supervisor_sentinel_status": "DISARMED_NONE_VERIFIED",
                "arm_manifest_sha256": "E" * 64,
            }

        def terminal(self, _accepted, _marker_sha256, verdict, evidence, _context):
            terminal.append((verdict, evidence))
            return "C" * 64

    supervisor.REVIEWED_RUN_PACKET_SHA256 = packet["reviewed_run_packet_sha256"]
    with pytest.raises(InvalidSupervisor) as raised:
        supervisor._run_one_shot_lifecycle(verified, Operations())
    assert str(raised.value) == "INVALID_SUPERVISOR"
    assert terminal == [
        (
            "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT",
            {
                "arm_manifest_sha256": "E" * 64,
                "disarmed_supervisor_sha256": "D" * 64,
                "supervisor_sentinel_status": "DISARMED_NONE_VERIFIED",
            },
        )
    ]
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


def test_persistent_self_disarm_rewrites_only_temp_runtime_copy(tmp_path, monkeypatch):
    import h1_splitvault_002_supervisor as supervisor

    packet_sha = "A" * 64
    runtime = tmp_path / "supervisor-copy.py"
    runtime.write_bytes(
        b"before\nREVIEWED_RUN_PACKET_SHA256: str | None = \"" + packet_sha.encode("ascii") + b"\"\nafter\n"
    )
    monkeypatch.setattr(supervisor, "__file__", str(runtime))
    supervisor._self_disarm_runtime(packet_sha)
    assert runtime.read_bytes() == b"before\nREVIEWED_RUN_PACKET_SHA256: str | None = None\nafter\n"


def test_mandatory_mapping_pipeline_binds_receipt_hash_path_bytes_and_extras_before_reads():
    selected = ("2016-01-04",)
    selection_payload, date_set_sha = _selection(selected)
    preflight = preflight_selection_manifest(
        selection_payload,
        expected_count=1,
        expected_date_set_sha256=date_set_sha,
    )
    payloads = {"2016-01-04": b"selected", "2016-01-05": b"extra"}
    rows = [
        {
            "bytes": len(payloads[day]),
            "date": day,
            "relative_path": f"public/DESIGN/{day}/h1.parquet",
            "rows": 7,
            "schema_version": "h1_splitvault_002_public_design_shard.v1",
            "sha256": _sha(payloads[day]),
        }
        for day in sorted(payloads)
    ]
    public_manifest = b"".join(canonical_json(row) + b"\n" for row in rows)
    public_receipt = canonical_json(
        {
            "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
            "design_dates": 2,
            "design_manifest_sha256": _sha(public_manifest),
            "raw_source_opens": 1,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "schema_version": "h1_splitvault_002_public_receipt.v1",
            "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
            "source_rows": 71785,
            "unselected_shard_opens": 0,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
    ) + b"\n"

    class CustodyCapability:
        def __init__(self):
            self.reads = {day: 0 for day in payloads}

        def public_manifest_bytes(self):
            return public_manifest

        def public_receipt_bytes(self):
            return public_receipt

        def read_design_day(self, day):
            self.reads[day] += 1
            return payloads[day]

        def open_counts(self):
            return dict(self.reads)

    custody = CustodyCapability()
    narrowed = prepare_narrow_design_capability(
        custody,
        preflight,
        expected_source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
    )
    assert narrowed.actual_extra_design_dates() == 1
    assert custody.reads == {"2016-01-04": 0, "2016-01-05": 0}
    assert narrowed.read_design_day("2016-01-04") == b"selected"
    assert custody.reads == {"2016-01-04": 1, "2016-01-05": 0}

    leaky_receipt = json.loads(public_receipt)
    leaky_receipt["nested"] = {"pnl": 1}
    custody.public_receipt_bytes = lambda: canonical_json(leaky_receipt) + b"\n"
    with pytest.raises(InvalidSupervisor):
        prepare_narrow_design_capability(
            custody,
            preflight,
            expected_source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
        )
    assert custody.reads == {"2016-01-04": 1, "2016-01-05": 0}


def _v9_public_extra_case(extra_count):
    selected = ("2016-01-04", "2016-01-05")
    selection_payload, date_set_sha = _selection(selected)
    preflight = preflight_selection_manifest(
        selection_payload,
        expected_count=len(selected),
        expected_date_set_sha256=date_set_sha,
    )
    extra_dates = tuple(
        (date(2016, 1, 6) + timedelta(days=index)).isoformat()
        for index in range(extra_count)
    )
    payloads = {day: ("payload-" + day).encode("ascii") for day in selected + extra_dates}
    rows = [
        {
            "bytes": len(payloads[day]),
            "date": day,
            "relative_path": f"public/DESIGN/{day}/h1.parquet",
            "rows": 7,
            "schema_version": "h1_splitvault_002_public_design_shard.v1",
            "sha256": _sha(payloads[day]),
        }
        for day in sorted(payloads)
    ]

    class PublicCapability:
        def __init__(self):
            self.rows = rows
            self.payloads = payloads
            self.opens = {day: 0 for day in payloads}
            self.receipt_design_dates = len(rows)

        def public_manifest_bytes(self):
            return b"".join(canonical_json(row) + b"\n" for row in self.rows)

        def public_receipt_bytes(self):
            manifest = self.public_manifest_bytes()
            return canonical_json(
                {
                    "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
                    "design_dates": self.receipt_design_dates,
                    "design_manifest_sha256": _sha(manifest),
                    "raw_source_opens": 1,
                    "research_holdout_opened": False,
                    "research_validation_opened": False,
                    "schema_version": "h1_splitvault_002_public_receipt.v1",
                    "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
                    "source_rows": 71785,
                    "unselected_shard_opens": 0,
                    "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
                }
            ) + b"\n"

        def read_design_day(self, day):
            self.opens[day] += 1
            return self.payloads[day]

        def open_counts(self):
            return dict(self.opens)

    return selected, extra_dates, preflight, PublicCapability()


@pytest.mark.parametrize("extra_count", [0, 3, 12])
def test_v9_actual_extra_dates_are_derived_and_reconciled_exact_once(extra_count):
    import h1_splitvault_002_supervisor as supervisor

    selected, extra_dates, preflight, custody = _v9_public_extra_case(extra_count)
    narrowed = supervisor.prepare_narrow_design_capability(
        custody,
        preflight,
        expected_source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
    )
    assert narrowed.actual_extra_design_dates() == extra_count
    assert custody.opens == {day: 0 for day in selected + extra_dates}

    child = supervisor.materialize_child_capability(
        narrowed,
        source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
    )
    assert child.actual_extra_design_dates() == extra_count
    assert custody.opens == {
        **{day: 1 for day in selected},
        **{day: 0 for day in extra_dates},
    }
    for day in selected:
        child.read_design_day(day)
    assert child.open_count_summary() == {
        "raw_source_opens": 1,
        "selected_shard_opens": len(selected),
        "unselected_shard_opens": 0,
    }


@pytest.mark.parametrize(
    "failure",
    [
        "missing_selected", "duplicate_selected", "receipt_count_mismatch",
        "negative_count", "duplicate_extra", "selected_hash_drift", "unselected_read",
    ],
)
def test_v9_public_metadata_or_open_reconciliation_failures_cannot_materialize(failure):
    import h1_splitvault_002_supervisor as supervisor

    selected, extra_dates, preflight, custody = _v9_public_extra_case(1)
    if failure == "missing_selected":
        custody.rows = [row for row in custody.rows if row["date"] != selected[0]]
        custody.opens.pop(selected[0])
        custody.receipt_design_dates = len(custody.rows)
    elif failure == "duplicate_selected":
        custody.rows.append(dict(custody.rows[0]))
        custody.receipt_design_dates = len(custody.rows)
    elif failure == "receipt_count_mismatch":
        custody.receipt_design_dates += 1
    elif failure == "negative_count":
        custody.receipt_design_dates = len(selected) - 1
    elif failure == "duplicate_extra":
        extra_row = next(row for row in custody.rows if row["date"] == extra_dates[0])
        custody.rows.append(dict(extra_row))
        custody.receipt_design_dates = len(custody.rows)

    if failure in {
        "missing_selected", "duplicate_selected", "receipt_count_mismatch",
        "negative_count", "duplicate_extra",
    }:
        with pytest.raises(InvalidSupervisor):
            supervisor.prepare_narrow_design_capability(
                custody,
                preflight,
                expected_source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
            )
        assert all(count == 0 for count in custody.opens.values())
        return

    narrowed = supervisor.prepare_narrow_design_capability(
        custody,
        preflight,
        expected_source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
    )
    if failure == "selected_hash_drift":
        custody.payloads[selected[0]] = b"drift"
    else:
        custody.opens[extra_dates[0]] = 1
    with pytest.raises(InvalidSupervisor):
        supervisor.materialize_child_capability(
            narrowed,
            source_attempt_id="HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
        )


def test_v9_unselected_read_after_marker_can_only_write_failed_terminal():
    import h1_splitvault_002_supervisor as supervisor

    _selected, extra_dates, preflight, custody = _v9_public_extra_case(1)
    events = []

    class Operations:
        def preflight(self, _packet):
            return {"preflight": preflight, "custody": custody}

        def start(self, _packet, _context):
            events.append("MARKER")
            return {"verdict": "ATTEMPT_CONSUMED"}, "A" * 64

        def pipeline(self, packet, _marker, context):
            events.append("PIPELINE")
            narrowed = supervisor.prepare_narrow_design_capability(
                context["custody"],
                context["preflight"],
                expected_source_attempt_id=packet["source_attempt_id"],
            )
            context["custody"].opens[extra_dates[0]] = 1
            supervisor.materialize_child_capability(
                narrowed,
                source_attempt_id=packet["source_attempt_id"],
            )
            raise AssertionError("unselected read must fail before READY")

        def disarm(self, _packet, _context):
            events.append("DISARM")
            return {
                "arm_manifest_sha256": "B" * 64,
                "disarmed_supervisor_sha256": "C" * 64,
                "supervisor_sentinel_status": "DISARMED_NONE_VERIFIED",
            }

        def terminal(self, _packet, _marker_sha, verdict, _evidence, _context):
            events.append("TERMINAL:" + verdict)
            return "D" * 64

    detached = "E" * 64
    packet = supervisor.VerifiedRunPacket(
        {"source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"},
        detached,
        b"{}\n",
    )
    supervisor.REVIEWED_RUN_PACKET_SHA256 = detached
    with pytest.raises(InvalidSupervisor):
        supervisor._run_one_shot_lifecycle(packet, Operations())
    assert events == ["MARKER", "PIPELINE", "DISARM", "TERMINAL:" + supervisor._FAILED]
    assert supervisor._READY not in events
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


def test_exact_canonical_synthetic_packet_runs_complete_in_process_one_shot(tmp_path, monkeypatch):
    import h1_splitvault_002_supervisor as supervisor
    import build_trendstack_006_design_source as builder
    import validate_trendstack_006_design_source as validator
    from h1_splitvault_002_custodian import EXPECTED_SCHEMA

    rows = []
    for day, hours in (
        ("2016-01-03", [12]),
        ("2016-01-04", range(12, 19)),
        ("2016-01-05", range(12, 19)),
        ("2016-01-06", range(12, 19)),
        ("2021-01-01", [12]),
        ("2023-01-01", [12]),
    ):
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
    pq.write_table(pa.Table.from_pylist(rows, schema=EXPECTED_SCHEMA), sink, row_group_size=len(rows))
    source_payload = sink.getvalue().to_pybytes()
    footer_length = int.from_bytes(source_payload[-8:-4], "little")
    footer_start = len(source_payload) - 8 - footer_length
    selected = ("2016-01-04", "2016-01-05")
    selection_payload, date_set_sha = _selection(selected)

    def bound_file(name, payload):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path, _sha(payload)

    source_path, source_sha = bound_file("inputs/source.parquet", source_payload)
    source_manifest_path, source_manifest_sha = bound_file(
        "inputs/manifest.json", b'{"bar":"closed","price":"bid","symbol":"EURUSD","timeframe":"H1"}\n'
    )
    clock_path, clock_sha = bound_file("inputs/clock.py", b"# synthetic bound clock\n")
    selection_path, selection_sha = bound_file("inputs/selection.jsonl", selection_payload)
    generic = {}
    for name in (
        "collection_plan_v1", "collection_plan_v2", "probe_plan_v1", "probe_plan_v2",
        "packet_review_receipt", "parent_stage0_ledger", "parent_stage0_receipt",
    ):
        generic[name] = bound_file(f"inputs/{name}.txt", (name + "\n").encode("ascii"))
    registry_path = Path(__file__).resolve().parents[4] / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    generic["registry"] = (registry_path, _sha(registry_path.read_bytes()))
    goal_path = Path(__file__).resolve().parents[4] / "01. GOAL" / "GOAL.md"
    generic["owner_goal"] = (goal_path, _sha(goal_path.read_bytes()))

    research = Path(supervisor.__file__).resolve().parent
    test_root = Path(__file__).resolve().parent
    file_bindings = {
        "collection_plan_v1": generic["collection_plan_v1"],
        "collection_plan_v2": generic["collection_plan_v2"],
        "probe_plan_v1": generic["probe_plan_v1"],
        "probe_plan_v2": generic["probe_plan_v2"],
        "registry": generic["registry"],
        "owner_goal": generic["owner_goal"],
        "source_manifest": (source_manifest_path, source_manifest_sha),
        "clock": (clock_path, clock_sha),
        "custodian_tool": bound_file("tool-copies/custodian.py", (research / "h1_splitvault_002_custodian.py").read_bytes()),
        "supervisor_tool": bound_file("tool-copies/supervisor.py", Path(supervisor.__file__).read_bytes()),
        "design_builder_tool": bound_file("tool-copies/builder.py", Path(builder.__file__).read_bytes()),
        "validator_tool": bound_file("tool-copies/validator.py", Path(validator.__file__).read_bytes()),
        "custodian_test": bound_file("test-copies/custodian.py", (test_root / "test_h1_splitvault_002_custodian.py").read_bytes()),
        "supervisor_test": bound_file("test-copies/supervisor.py", Path(__file__).read_bytes()),
        "design_builder_test": bound_file("test-copies/builder.py", (test_root / "test_build_trendstack_006_design_source.py").read_bytes()),
        "validator_test": bound_file("test-copies/validator.py", (test_root / "test_validate_trendstack_006_design_source.py").read_bytes()),
        "packet_review_receipt": generic["packet_review_receipt"],
        "parent_stage0_ledger": generic["parent_stage0_ledger"],
        "parent_stage0_receipt": generic["parent_stage0_receipt"],
        "selection_manifest": (selection_path, selection_sha),
    }

    frozen_updates = {
        "owner_goal_path": str(file_bindings["owner_goal"][0]),
        "owner_goal_sha256": file_bindings["owner_goal"][1],
        "collection_plan_v1_path": str(file_bindings["collection_plan_v1"][0]),
        "collection_plan_v1_sha256": file_bindings["collection_plan_v1"][1],
        "collection_plan_v2_path": str(file_bindings["collection_plan_v2"][0]),
        "collection_plan_v2_sha256": file_bindings["collection_plan_v2"][1],
        "probe_plan_v1_path": str(file_bindings["probe_plan_v1"][0]),
        "probe_plan_v1_sha256": file_bindings["probe_plan_v1"][1],
        "probe_plan_v2_path": str(file_bindings["probe_plan_v2"][0]),
        "probe_plan_v2_sha256": file_bindings["probe_plan_v2"][1],
        "registry_path": str(file_bindings["registry"][0]),
        "source_path": str(source_path),
        "source_sha256": source_sha,
        "source_bytes": len(source_payload),
        "source_rows": len(rows),
        "source_row_groups": 1,
        "source_footer_length": footer_length,
        "source_footer_start": footer_start,
        "source_footer_sha256": _sha(source_payload[footer_start:]),
        "source_manifest_path": str(source_manifest_path),
        "source_manifest_sha256": source_manifest_sha,
        "clock_path": str(clock_path),
        "clock_sha256": clock_sha,
        "parent_stage0_ledger_sha256": file_bindings["parent_stage0_ledger"][1],
        "parent_stage0_receipt_sha256": file_bindings["parent_stage0_receipt"][1],
        "expected_design_dates": 2,
        "expected_rows_per_day": 7,
        "expected_total_rows": 14,
        "expected_raw_opens": 1,
        "expected_selected_opens": 2,
        "expected_unselected_opens": 0,
    }
    for key, value in frozen_updates.items():
        monkeypatch.setitem(supervisor.FROZEN_PACKET_VALUES, key, value)
    monkeypatch.setattr(supervisor, "FROZEN_DESIGN_DATE_SET_SHA256", date_set_sha)

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    for prefix, (path, digest) in file_bindings.items():
        packet[prefix + "_path"] = str(path)
        packet[prefix + "_sha256"] = digest
    packet.pop("supervisor_tool_sha256")
    packet.update(
        {
            "source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890",
            "source_path": str(source_path),
            "source_sha256": source_sha,
            "source_bytes": len(source_payload),
            "source_rows": len(rows),
            "source_row_groups": 1,
            "source_footer_length": footer_length,
            "source_footer_start": footer_start,
            "source_footer_sha256": _sha(source_payload[footer_start:]),
            "expected_design_dates": 2,
            "expected_rows_per_day": 7,
            "expected_total_rows": 14,
            "expected_raw_opens": 1,
            "expected_selected_opens": 2,
            "expected_unselected_opens": 0,
            "attempt_evidence_root": str(tmp_path / "evidence" / "attempt"),
            "custody_stage_path": str(tmp_path / ".h1_splitvault_002.attempt-HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"),
            "splitvault_output_root": str(tmp_path / "h1_splitvault_002"),
            "design_stage_path": str(tmp_path / ".trendstack_006_design_h1.attempt-HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"),
            "design_source_output_root": str(tmp_path / "trendstack_006_design_h1"),
            "selection_manifest_path": str(selection_path),
            "selection_manifest_sha256": selection_sha,
        }
    )
    (tmp_path / "evidence").mkdir()
    disarmed_runtime = file_bindings["supervisor_tool"][0].read_bytes()
    disarmed_runtime_sha = _sha(disarmed_runtime)
    packet["runtime_supervisor_sha256"] = "0" * 64
    packet["review_base_supervisor_sha256"] = disarmed_runtime_sha
    packet["supervisor_review_base_sha256"] = disarmed_runtime_sha
    packet_sha = _seal_packet(packet)
    armed_runtime = disarmed_runtime.replace(
        b"REVIEWED_RUN_PACKET_SHA256: str | None = None",
        b'REVIEWED_RUN_PACKET_SHA256: str | None = "' + packet_sha.encode("ascii") + b'"',
    )
    assert armed_runtime != disarmed_runtime
    file_bindings["supervisor_tool"][0].write_bytes(armed_runtime)
    packet["runtime_supervisor_sha256"] = _sha(armed_runtime)
    assert _seal_packet(packet) == packet_sha
    packet_payload = canonical_json(packet) + b"\n"
    packet_path = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_RUN_PACKET.json"
    packet_path.write_bytes(packet_payload)
    verified = validate_full_packet_document(packet_payload, packet_sha)
    arm_manifest_path = tmp_path / supervisor.ARM_MANIFEST_NAME
    arm_manifest_path.write_bytes(
        supervisor.build_arm_manifest_document(
            verified,
            armed_runtime,
            file_bindings["supervisor_tool"][0],
            packet_path,
        )
    )
    build_shape = builder.BuildShape(date_set_sha, 2, 7, 14, selected[0], selected[-1])
    validation_shape = validator.ValidationShape(date_set_sha, 2, 7, 14, selected[0], selected[-1])
    operations = supervisor._InProcessOperations(
        packet_path,
        workspace=tmp_path,
        arm_manifest_path=arm_manifest_path,
        testing_build_shape=build_shape,
        testing_validation_shape=validation_shape,
        testing_clock_converter=lambda server: server,
    )
    supervisor.REVIEWED_RUN_PACKET_SHA256 = packet_sha
    result = supervisor._run_one_shot_lifecycle(verified, operations)
    assert result["verdict"] == "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
    assert result["validated_dates"] == 2
    assert (tmp_path / "evidence" / "attempt" / "attempt_started.json").is_file()
    assert (tmp_path / "evidence" / "attempt" / "attempt_terminal.json").is_file()
    assert (tmp_path / "trendstack_006_design_h1" / "design_h1_source_receipt.json").is_file()
    terminal = json.loads((tmp_path / "evidence" / "attempt" / "attempt_terminal.json").read_bytes())
    marker = json.loads((tmp_path / "evidence" / "attempt" / "attempt_started.json").read_bytes())
    assert terminal["supervisor_sentinel_status"] == "DISARMED_NONE_VERIFIED"
    assert terminal["arm_manifest_sha256"] == marker["arm_manifest_sha256"]
    assert b"REVIEWED_RUN_PACKET_SHA256: str | None = None" in file_bindings["supervisor_tool"][0].read_bytes()
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


def test_v6_detached_digest_excludes_only_arm_dependent_fields():
    import h1_splitvault_002_supervisor as supervisor

    packet = {
        "authority": {"detached_packet_sha256": "A" * 64, "source_run_authorized": True},
        "runtime_supervisor_sha256": "B" * 64,
        "reviewed_run_packet_sha256": "C" * 64,
        "strategy_binding": "ORIGINAL",
    }
    first = supervisor.compute_detached_packet_sha256(packet)
    arm_only = json.loads(json.dumps(packet))
    arm_only["runtime_supervisor_sha256"] = "D" * 64
    arm_only["reviewed_run_packet_sha256"] = "E" * 64
    arm_only["authority"]["detached_packet_sha256"] = "F" * 64
    assert supervisor.compute_detached_packet_sha256(arm_only) == first

    drifted = json.loads(json.dumps(packet))
    drifted["strategy_binding"] = "DRIFTED"
    assert supervisor.compute_detached_packet_sha256(drifted) != first


def test_v6_exact_verified_private_module_ignores_malicious_named_cache(monkeypatch, tmp_path):
    import types
    import h1_splitvault_002_supervisor as supervisor

    malicious = types.ModuleType("h1_splitvault_002_custodian")
    malicious.PROVENANCE = "MALICIOUS_CACHE"
    monkeypatch.setitem(sys.modules, "h1_splitvault_002_custodian", malicious)
    payload = b"PROVENANCE = 'EXACT_VERIFIED_BYTES'\n"
    module = supervisor._execute_verified_module(
        payload,
        tmp_path / "h1_splitvault_002_custodian.py",
        _sha(payload),
        supervisor._freeze_dependency_map(),
    )
    assert module.PROVENANCE == "EXACT_VERIFIED_BYTES"
    assert module.__verified_sha256__ == _sha(payload)
    assert sys.modules["h1_splitvault_002_custodian"] is malicious


def test_v6_ready_is_impossible_until_disarm_and_terminal_failure_is_explicit():
    import h1_splitvault_002_supervisor as supervisor

    events = []

    class Operations:
        def preflight(self, _packet):
            return {}

        def start(self, _packet, _context):
            return {"verdict": "ATTEMPT_CONSUMED"}, "A" * 64

        def pipeline(self, _packet, _marker, _context):
            return {"verdict": supervisor._READY}

        def disarm(self, _packet, _context):
            events.append("disarm")
            raise OSError("replace failed")

        def terminal(self, _packet, _marker_sha, verdict, _evidence, _context):
            events.append(("terminal", verdict))
            raise OSError("terminal failed")

    packet = supervisor.VerifiedRunPacket(
        {"source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"},
        "B" * 64,
        b"{}\n",
    )
    supervisor.REVIEWED_RUN_PACKET_SHA256 = "B" * 64
    with pytest.raises(InvalidSupervisor, match="DISARM_FAILED.*TERMINAL_FAILED"):
        supervisor._run_one_shot_lifecycle(packet, Operations())
    assert events == ["disarm", ("terminal", supervisor._FAILED)]
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


def _v6_production_preflight_tuple(tmp_path, monkeypatch, *, tool_sources=None):
    import h1_splitvault_002_supervisor as supervisor
    import build_trendstack_006_design_source as builder
    import validate_trendstack_006_design_source as validator

    original_supervisor = Path(supervisor.__file__).resolve()
    original_research = original_supervisor.parent
    original_tests = Path(__file__).resolve().parent
    research = tmp_path / "research"
    tests = research / "tests"
    data = tmp_path / "data"
    parent_stage0 = research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0"
    attempt_parent = research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_ATTEMPTS"
    for directory in (tests, data, parent_stage0, attempt_parent, tmp_path / "inputs"):
        directory.mkdir(parents=True, exist_ok=True)

    def write(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path, _sha(payload)

    source = write(data / "source.parquet", b"SYNTHETIC_PREFLIGHT_ONLY")
    source_manifest = write(tmp_path / "inputs" / "manifest.json", b'{"bar":"closed","price":"bid","symbol":"EURUSD","timeframe":"H1"}\n')
    clock = write(tmp_path / "inputs" / "clock.py", b"def server_to_utc(value):\n    return value\n")
    selection_payload, date_set_sha = _selection(["2016-01-04"])
    selection = write(tmp_path / "inputs" / "selection.jsonl", selection_payload)
    registry_path = Path(__file__).resolve().parents[4] / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    registry = (registry_path, _sha(registry_path.read_bytes()))
    goal_path = Path(__file__).resolve().parents[4] / "01. GOAL" / "GOAL.md"
    goal = (goal_path, _sha(goal_path.read_bytes()))
    plan_v1 = write(tmp_path / "inputs" / "collection-v1.md", b"collection-v1\n")
    plan_v2 = write(tmp_path / "inputs" / "collection-v2.md", b"collection-v2\n")
    probe_v1 = write(tmp_path / "inputs" / "probe-v1.md", b"probe-v1\n")
    probe_v2 = write(tmp_path / "inputs" / "probe-v2.md", b"probe-v2\n")
    review = write(tmp_path / "inputs" / "review.json", b"{}\n")
    ledger = write(parent_stage0 / "stage0_eligibility_ledger.jsonl", b"{}\n")
    receipt = write(parent_stage0 / "stage0_receipt.json", b"{}\n")
    tools = {
        "custodian_tool": write(
            research / "h1_splitvault_002_custodian.py",
            tool_sources["custodian_tool"] if tool_sources is not None else (original_research / "h1_splitvault_002_custodian.py").read_bytes(),
        ),
        "supervisor_tool": write(research / "h1_splitvault_002_supervisor.py", original_supervisor.read_bytes()),
        "design_builder_tool": write(
            research / "build_trendstack_006_design_source.py",
            tool_sources["design_builder_tool"] if tool_sources is not None else Path(builder.__file__).read_bytes(),
        ),
        "validator_tool": write(
            research / "validate_trendstack_006_design_source.py",
            tool_sources["validator_tool"] if tool_sources is not None else Path(validator.__file__).read_bytes(),
        ),
        "custodian_test": write(tests / "test_h1_splitvault_002_custodian.py", (original_tests / "test_h1_splitvault_002_custodian.py").read_bytes()),
        "supervisor_test": write(tests / "test_h1_splitvault_002_supervisor.py", Path(__file__).read_bytes()),
        "design_builder_test": write(tests / "test_build_trendstack_006_design_source.py", (original_tests / "test_build_trendstack_006_design_source.py").read_bytes()),
        "validator_test": write(tests / "test_validate_trendstack_006_design_source.py", (original_tests / "test_validate_trendstack_006_design_source.py").read_bytes()),
    }
    bindings = {
        "owner_goal": goal,
        "collection_plan_v1": plan_v1,
        "collection_plan_v2": plan_v2,
        "probe_plan_v1": probe_v1,
        "probe_plan_v2": probe_v2,
        "registry": registry,
        "source_manifest": source_manifest,
        "clock": clock,
        **tools,
        "packet_review_receipt": review,
        "parent_stage0_ledger": ledger,
        "parent_stage0_receipt": receipt,
        "selection_manifest": selection,
    }
    frozen = {
        "owner_goal_path": str(goal[0]),
        "owner_goal_sha256": goal[1],
        "collection_plan_v1_path": str(plan_v1[0]),
        "collection_plan_v1_sha256": plan_v1[1],
        "collection_plan_v2_path": str(plan_v2[0]),
        "collection_plan_v2_sha256": plan_v2[1],
        "probe_plan_v1_path": str(probe_v1[0]),
        "probe_plan_v1_sha256": probe_v1[1],
        "probe_plan_v2_path": str(probe_v2[0]),
        "probe_plan_v2_sha256": probe_v2[1],
        "registry_path": str(registry[0]),
        "source_path": str(source[0]),
        "source_sha256": source[1],
        "source_bytes": len(source[0].read_bytes()),
        "source_rows": 1,
        "source_row_groups": 1,
        "source_footer_length": 1,
        "source_footer_start": len(source[0].read_bytes()) - 9,
        "source_footer_sha256": _sha(b"synthetic-footer"),
        "source_manifest_path": str(source_manifest[0]),
        "source_manifest_sha256": source_manifest[1],
        "clock_path": str(clock[0]),
        "clock_sha256": clock[1],
        "parent_stage0_ledger_sha256": ledger[1],
        "parent_stage0_receipt_sha256": receipt[1],
        "expected_design_dates": 1,
        "expected_rows_per_day": 7,
        "expected_total_rows": 7,
        "expected_raw_opens": 1,
        "expected_selected_opens": 1,
        "expected_unselected_opens": 0,
    }
    for key, value in frozen.items():
        monkeypatch.setitem(supervisor.FROZEN_PACKET_VALUES, key, value)
    monkeypatch.setattr(supervisor, "FROZEN_DESIGN_DATE_SET_SHA256", date_set_sha)
    monkeypatch.setattr(supervisor, "__file__", str(tools["supervisor_tool"][0]))

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    for prefix, (path, digest) in bindings.items():
        packet[prefix + "_path"] = str(path)
        packet[prefix + "_sha256"] = digest
    packet.pop("supervisor_tool_sha256")
    attempt = packet["source_attempt_id"]
    packet.update(
        {
            "source_path": str(source[0]),
            "source_sha256": source[1],
            "source_bytes": len(source[0].read_bytes()),
            "source_rows": 1,
            "source_row_groups": 1,
            "source_footer_length": 1,
            "source_footer_start": len(source[0].read_bytes()) - 9,
            "source_footer_sha256": _sha(b"synthetic-footer"),
            "expected_design_dates": 1,
            "expected_rows_per_day": 7,
            "expected_total_rows": 7,
            "expected_raw_opens": 1,
            "expected_selected_opens": 1,
            "expected_unselected_opens": 0,
            "attempt_evidence_root": str(attempt_parent / attempt),
            "custody_stage_path": str(data / f".h1_splitvault_002.attempt-{attempt}"),
            "splitvault_output_root": str(data / "h1_splitvault_002"),
            "design_stage_path": str(data / f".trendstack_006_design_h1.attempt-{attempt}"),
            "design_source_output_root": str(data / "trendstack_006_design_h1"),
            "selection_manifest_path": str(selection[0]),
            "selection_manifest_sha256": selection[1],
        }
    )
    disarmed = tools["supervisor_tool"][0].read_bytes()
    disarmed_sha = _sha(disarmed)
    packet["runtime_supervisor_sha256"] = "0" * 64
    packet["review_base_supervisor_sha256"] = disarmed_sha
    packet["supervisor_review_base_sha256"] = disarmed_sha
    detached = _seal_packet(packet)
    armed = disarmed.replace(
        b"REVIEWED_RUN_PACKET_SHA256: str | None = None",
        b'REVIEWED_RUN_PACKET_SHA256: str | None = "' + detached.encode("ascii") + b'"',
    )
    tools["supervisor_tool"][0].write_bytes(armed)
    packet["runtime_supervisor_sha256"] = _sha(armed)
    assert _seal_packet(packet) == detached
    packet_payload = canonical_json(packet) + b"\n"
    packet_path = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_RUN_PACKET.json"
    packet_path.write_bytes(packet_payload)
    verified = supervisor.validate_full_packet_document(packet_payload, detached)
    arm_path = tmp_path / supervisor.ARM_MANIFEST_NAME
    supervisor.create_arm_manifest(verified, tools["supervisor_tool"][0], packet_path, arm_path)
    arm_payload = arm_path.read_bytes()
    operations = supervisor._InProcessOperations(packet_path, workspace=tmp_path, arm_manifest_path=arm_path)
    return supervisor, packet, verified, operations, arm_payload, tools


def _v7_production_standin_tools():
    custodian = b'''import hashlib
import json

class CustodyAuthority:
    def __init__(self, **values):
        self.__dict__.update(values)

class Capability:
    def __init__(self, receipt, manifest, payload):
        self.receipt = receipt
        self.manifest = manifest
        self.payload = payload
        self.opens = {"2016-01-04": 0}
    def public_receipt_bytes(self):
        return self.receipt
    def public_manifest_bytes(self):
        return self.manifest
    def read_design_day(self, day):
        self.opens[day] += 1
        return self.payload
    def open_counts(self):
        return dict(self.opens)

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def run_custody(source_reader, *, source_manifest_payload, clock_payload, output_root, stage_root, authority, marker):
    source_reader()
    day = "2016-01-04"
    selected = b"selected"
    row = {
        "bytes": len(selected),
        "date": day,
        "relative_path": "public/DESIGN/2016-01-04/h1.parquet",
        "rows": 7,
        "schema_version": "h1_splitvault_002_public_design_shard.v1",
        "sha256": hashlib.sha256(selected).hexdigest().upper(),
    }
    manifest = _canonical(row) + b"\\n"
    receipt = {
        "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
        "design_dates": 1,
        "design_manifest_sha256": hashlib.sha256(manifest).hexdigest().upper(),
        "raw_source_opens": 1,
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "schema_version": "h1_splitvault_002_public_receipt.v1",
        "source_attempt_id": authority.source_attempt_id,
        "source_rows": authority.expected_source_rows,
        "unselected_shard_opens": 0,
        "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }
    receipt_payload = _canonical(receipt) + b"\\n"
    return receipt, Capability(receipt_payload, manifest, selected)
'''
    builder = b'''class DesignSourceContract:
    def __init__(self, **values):
        self.__dict__.update(values)

def build_design_source(capability, output_root, contract):
    output_root.mkdir()
    return {"pending_receipt_sha256": "A" * 64, "pending_tree_sha256": "B" * 64}
'''
    validator = b'''class ValidationAuthority:
    def __init__(self, **values):
        self.__dict__.update(values)

def validate_design_source(output_root, authority):
    return {
        "design_date_set_sha256": "C" * 64,
        "source_receipt_sha256": "D" * 64,
        "validated_dates": 1,
        "validated_h1_rows": 7,
        "validator_test_sha256": authority.validator_test_sha256,
        "validator_tool_sha256": authority.validator_tool_sha256,
        "verdict": "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET",
    }
'''
    return {
        "custodian_tool": custodian,
        "design_builder_tool": builder,
        "validator_tool": validator,
    }


def test_v7_production_mode_synthetic_one_shot_uses_clean_frozen_dependencies(tmp_path, monkeypatch):
    supervisor, packet, verified, operations, _arm_payload, tools = _v6_production_preflight_tuple(
        tmp_path,
        monkeypatch,
        tool_sources=_v7_production_standin_tools(),
    )
    assert operations.testing is False
    supervisor.REVIEWED_RUN_PACKET_SHA256 = verified.detached_sha256
    result = supervisor._run_one_shot_lifecycle(verified, operations)
    assert result["verdict"] == supervisor._READY
    marker = json.loads((Path(packet["attempt_evidence_root"]) / "attempt_started.json").read_bytes())
    terminal = json.loads((Path(packet["attempt_evidence_root"]) / "attempt_terminal.json").read_bytes())
    assert terminal["verdict"] == supervisor._READY
    assert terminal["supervisor_sentinel_status"] == "DISARMED_NONE_VERIFIED"
    assert "expected_extra_design_dates" not in marker
    assert "actual_extra_design_dates" not in marker
    assert terminal["actual_extra_design_dates"] == result["actual_extra_design_dates"] == 0
    assert marker["dependency_attestation_sha256"] == terminal["dependency_attestation_sha256"]
    assert terminal["dependency_attestation_sha256"] == result["dependency_attestation_sha256"]
    assert len(bytes.fromhex(result["dependency_attestation_sha256"])) == 32
    assert b"REVIEWED_RUN_PACKET_SHA256: str | None = None" in tools["supervisor_tool"][0].read_bytes()
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


def test_v6_production_mode_arm_tuple_preflights_and_swap_cannot_execute(tmp_path, monkeypatch):
    supervisor, packet, verified, operations, arm_payload, tools = _v6_production_preflight_tuple(tmp_path, monkeypatch)
    assert operations.testing is False
    context = operations.preflight(verified)
    assert context["source_reads"] == 0
    assert context["arm_manifest"]["detached_packet_sha256"] == verified.detached_sha256
    with pytest.raises(InvalidSupervisor):
        supervisor.create_arm_manifest(
            verified,
            tools["supervisor_tool"][0],
            operations.packet_path,
            operations.arm_manifest_path,
        )

    runtime_drift = json.loads(json.dumps(packet))
    runtime_drift["runtime_supervisor_sha256"] = "F" * 64
    assert supervisor.compute_detached_packet_sha256(runtime_drift) == verified.detached_sha256
    runtime_payload = canonical_json(runtime_drift) + b"\n"
    runtime_verified = supervisor.validate_full_packet_document(runtime_payload, verified.detached_sha256)
    with pytest.raises(InvalidSupervisor):
        supervisor.validate_arm_manifest_document(
            arm_payload,
            runtime_verified,
            tools["supervisor_tool"][0].read_bytes(),
            tools["supervisor_tool"][0],
            operations.packet_path,
        )

    tools["design_builder_tool"][0].write_bytes(b"MALICIOUS_POST_PREFLIGHT_SWAP\n")
    with pytest.raises(Exception):
        operations._verified_private_tools(verified, context)
    assert not Path(packet["attempt_evidence_root"]).exists()


def test_v6_registry_probe_is_legal_only_with_detached_packet_authority(tmp_path, monkeypatch):
    supervisor, _packet, verified, _operations, _arm_payload, _tools = _v6_production_preflight_tuple(tmp_path, monkeypatch)
    registry = Path(verified["registry_path"]).read_bytes()
    supervisor._verify_registry_rows(registry, verified)

    false_values = verified.as_dict()
    false_values["authority"] = dict(false_values["authority"])
    false_values["authority"]["source_run_authorized"] = False
    false_packet = supervisor.VerifiedRunPacket(false_values, verified.detached_sha256, verified.canonical_bytes)
    with pytest.raises(Exception):
        supervisor._verify_registry_rows(registry, false_packet)

    rows = registry.splitlines()
    current = json.loads(rows[281])
    current["state"] = "source_run"
    rows[281] = canonical_json(current)
    with pytest.raises(Exception):
        supervisor._verify_registry_rows(b"\n".join(rows) + b"\n", verified)

    extra = verified.as_dict()
    extra["authority"] = {**extra["authority"], "invented_registry_state": "source_run"}
    with pytest.raises(InvalidSupervisor):
        supervisor.validate_full_packet_document(canonical_json(extra) + b"\n", verified.detached_sha256)


def test_v6_disarm_failure_writes_only_engineering_failure_terminal(tmp_path):
    import h1_splitvault_002_supervisor as supervisor

    terminal_path = tmp_path / "attempt_terminal.json"

    class Operations:
        def preflight(self, _packet):
            return {}

        def start(self, _packet, _context):
            return {"verdict": "ATTEMPT_CONSUMED"}, "A" * 64

        def pipeline(self, _packet, _marker, _context):
            return {"verdict": supervisor._READY}

        def disarm(self, _packet, _context):
            raise OSError("injected replace/fsync/readback failure")

        def terminal(self, _packet, _marker_sha, verdict, evidence, _context):
            payload = canonical_json({"evidence": evidence, "verdict": verdict}) + b"\n"
            terminal_path.write_bytes(payload)
            return _sha(payload)

    packet = supervisor.VerifiedRunPacket(
        {"source_attempt_id": "HYP006-SOURCE-ATTEMPT-ABCDEF1234567890"},
        "B" * 64,
        b"{}\n",
    )
    supervisor.REVIEWED_RUN_PACKET_SHA256 = "B" * 64
    with pytest.raises(InvalidSupervisor, match="DISARM_FAILED"):
        supervisor._run_one_shot_lifecycle(packet, Operations())
    assert json.loads(terminal_path.read_bytes())["verdict"] == supervisor._FAILED
    assert supervisor._READY.encode("ascii") not in terminal_path.read_bytes()
    assert supervisor.REVIEWED_RUN_PACKET_SHA256 is None


@pytest.mark.parametrize("poisoned_name", ["pyarrow", "pyarrow.parquet", "dataclasses", "pathlib"])
def test_v7_preflight_rejects_preloaded_dependency_poison_before_marker(tmp_path, monkeypatch, poisoned_name):
    import types

    supervisor, packet, verified, operations, _arm_payload, _tools = _v6_production_preflight_tuple(tmp_path, monkeypatch)
    monkeypatch.setitem(sys.modules, poisoned_name, types.ModuleType(poisoned_name))
    with pytest.raises(InvalidSupervisor):
        operations.preflight(verified)
    assert not Path(packet["attempt_evidence_root"]).exists()


def test_v7_preflight_rejects_combined_dependency_poison(tmp_path, monkeypatch):
    import types

    _supervisor, packet, verified, operations, _arm_payload, _tools = _v6_production_preflight_tuple(tmp_path, monkeypatch)
    for name in ("pyarrow", "pyarrow.parquet", "dataclasses", "pathlib"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    with pytest.raises(InvalidSupervisor):
        operations.preflight(verified)
    assert not Path(packet["attempt_evidence_root"]).exists()


def test_v7_preflight_rejects_pyarrow_clone_with_forged_canonical_metadata(tmp_path, monkeypatch):
    import types

    _supervisor, packet, verified, operations, _arm_payload, _tools = _v6_production_preflight_tuple(tmp_path, monkeypatch)
    trusted = sys.modules["pyarrow"]
    forged = types.ModuleType("pyarrow")
    forged.__spec__ = trusted.__spec__
    forged.__file__ = trusted.__file__
    forged.__path__ = trusted.__path__
    forged.parquet = sys.modules["pyarrow.parquet"]
    monkeypatch.setitem(sys.modules, "pyarrow", forged)
    with pytest.raises(InvalidSupervisor):
        operations.preflight(verified)
    assert not Path(packet["attempt_evidence_root"]).exists()


def test_v7_frozen_dependency_drift_blocks_execution_and_ready_terminal(tmp_path, monkeypatch):
    import types

    supervisor, packet, verified, operations, _arm_payload, _tools = _v6_production_preflight_tuple(tmp_path, monkeypatch)
    context = operations.preflight(verified)
    marker, marker_sha = operations.start(verified, context)
    monkeypatch.setitem(sys.modules, "dataclasses", types.ModuleType("dataclasses"))
    with pytest.raises(Exception):
        operations._verified_private_tools(verified, context)
    with pytest.raises(InvalidSupervisor):
        operations.terminal(
            verified,
            marker_sha,
            supervisor._READY,
            {
                "arm_manifest_sha256": context["arm_manifest"]["arm_manifest_sha256"],
                "disarmed_supervisor_sha256": "A" * 64,
                "supervisor_sentinel_status": "DISARMED_NONE_VERIFIED",
            },
            context,
        )
    assert marker["verdict"] == "ATTEMPT_CONSUMED"
    terminal_path = Path(packet["attempt_evidence_root"]) / "attempt_terminal.json"
    assert not terminal_path.exists()


def test_v7_private_execution_has_minimal_builtins_and_no_import_fallback(tmp_path):
    import h1_splitvault_002_supervisor as supervisor

    dependencies = supervisor._freeze_dependency_map()
    payload = b"RESULT = len(bytes([1, 2]))\n"
    module = supervisor._execute_verified_module(payload, tmp_path / "verified.py", _sha(payload), dependencies)
    assert module.RESULT == 2
    injected = module.__dict__["__builtins__"]
    assert set(injected) == set(supervisor._MINIMAL_BUILTIN_NAMES) | {"__import__"}
    assert not {"open", "eval", "exec", "compile"} & set(injected)

    forbidden = b"import socket\n"
    with pytest.raises(InvalidSupervisor):
        supervisor._execute_verified_module(forbidden, tmp_path / "forbidden.py", _sha(forbidden), dependencies)


def test_v7_frozen_dependency_origin_identity_metadata_is_rechecked():
    import dataclasses

    import h1_splitvault_002_supervisor as supervisor

    dependencies = supervisor._freeze_dependency_map()
    frozen = dependencies["pathlib"]
    dependencies["pathlib"] = dataclasses.replace(frozen, file_identity=(0,) * 7)
    with pytest.raises(Exception):
        supervisor._recheck_dependency_map(dependencies)


def test_v8_preimport_canonical_looking_replacements_make_production_ineligible(tmp_path, monkeypatch):
    import dataclasses
    import pathlib
    import types

    import h1_splitvault_002_supervisor as supervisor

    real_modules = {
        "dataclasses": dataclasses,
        "pathlib": pathlib,
        "pyarrow": pa,
        "pyarrow.parquet": pq,
    }
    replacements = {}
    for name, real in real_modules.items():
        replacement = types.ModuleType(name)
        replacement.__dict__.update(real.__dict__)
        replacements[name] = replacement
    replacements["pyarrow"].parquet = replacements["pyarrow.parquet"]
    for name, replacement in replacements.items():
        monkeypatch.setitem(sys.modules, name, replacement)

    private_name = "_v8_preloaded_supervisor"
    fresh = types.ModuleType(private_name)
    fresh.__file__ = supervisor.__file__
    fresh.__package__ = None
    monkeypatch.setitem(sys.modules, private_name, fresh)
    source = Path(supervisor.__file__).read_bytes()
    exec(compile(source, supervisor.__file__, "exec"), fresh.__dict__)

    assert fresh._PROTECTED_PRELOAD_AT_BOOTSTRAP == (
        "dataclasses", "pathlib", "pyarrow", "pyarrow.parquet",
    )
    assert fresh._PRODUCTION_BOOTSTRAP_ELIGIBLE is False
    operations = fresh._InProcessOperations(
        tmp_path / "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_RUN_PACKET.json",
        _require_clean_bootstrap=True,
    )
    with pytest.raises(fresh.InvalidSupervisor):
        operations.preflight(None)
    with pytest.raises(fresh.InvalidSupervisor):
        fresh.supervise(tmp_path / "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_RUN_PACKET.json")
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize(("dependency_name", "symbol_name"), [("pyarrow", "BufferReader"), ("json", "dumps")])
def test_v8_same_module_symbol_replacement_fails_but_proxy_keeps_original(
    monkeypatch, dependency_name, symbol_name,
):
    import h1_splitvault_002_supervisor as supervisor

    dependencies = supervisor._freeze_dependency_map()
    frozen = dependencies[dependency_name]
    original = getattr(frozen.proxy, symbol_name)
    replacement = object()
    monkeypatch.setattr(frozen.module, symbol_name, replacement)

    assert getattr(frozen.proxy, symbol_name) is original
    assert getattr(frozen.module, symbol_name) is replacement
    with pytest.raises(Exception):
        supervisor._recheck_dependency_map(dependencies)


def test_v8_private_imports_return_immutable_exact_symbol_proxies(tmp_path):
    import types

    import h1_splitvault_002_supervisor as supervisor

    dependencies = supervisor._freeze_dependency_map()
    proxy = dependencies["json"].proxy
    assert not isinstance(proxy, types.ModuleType)
    assert proxy.dumps is json.dumps
    with pytest.raises(AttributeError):
        _ = proxy.not_allowlisted
    with pytest.raises(AttributeError):
        _ = proxy._proxy_symbols
    with pytest.raises(AttributeError):
        proxy.dumps = object()
    with pytest.raises(AttributeError):
        object.__setattr__(proxy, "_proxy_symbols", {})

    payload = b'import json\nPROXY = json\nRESULT = json.dumps({"ok": True}, sort_keys=True, separators=(",", ":"))\n'
    module = supervisor._execute_verified_module(payload, tmp_path / "verified.py", _sha(payload), dependencies)
    assert module.PROXY is proxy
    assert module.RESULT == '{"ok":true}'
    assert not isinstance(module.PROXY, types.ModuleType)


def test_v8_dependency_attestation_is_exact_and_deterministic():
    import h1_splitvault_002_supervisor as supervisor

    first = supervisor._freeze_dependency_map()
    second = supervisor._freeze_dependency_map()
    first_document, first_sha = supervisor._dependency_attestation(first)
    second_document, second_sha = supervisor._dependency_attestation(second)

    assert first_document == second_document
    assert first_sha == second_sha == _sha(canonical_json(first_document))
    assert set(first_document) == {"dependencies", "schema_version"}
    assert first_document["schema_version"] == "trendstack_006_dependency_attestation.v1"
    assert [item["module"] for item in first_document["dependencies"]] == sorted(first)
    for item in first_document["dependencies"]:
        assert set(item) == {
            "file_identity", "file_sha256", "loader_type", "module", "origin", "symbols",
        }
        for symbol in item["symbols"]:
            assert set(symbol) == {"name", "type_module", "type_qualname"}


@pytest.mark.parametrize("legacy_field", ["source_run_registry_row_index", "source_run_registry_row_sha256"])
def test_v7_packet_rejects_phantom_registry_fields_as_extra_contract(tmp_path, legacy_field):
    import h1_splitvault_002_supervisor as supervisor

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    packet[legacy_field] = 283 if legacy_field.endswith("index") else "A" * 64
    payload = canonical_json(packet) + b"\n"
    with pytest.raises(InvalidSupervisor):
        supervisor.validate_full_packet_document(payload, packet["reviewed_run_packet_sha256"])


def test_v9_packet_rejects_legacy_expected_extra_guess_and_canonical_packet_omits_it():
    import h1_splitvault_002_supervisor as supervisor

    packet = _full_packet(supervisor.FULL_PACKET_FIELDS, supervisor.FROZEN_PACKET_VALUES)
    assert "expected_extra_design_dates" not in packet
    payload = canonical_json(packet) + b"\n"
    supervisor.validate_full_packet_document(payload, packet["reviewed_run_packet_sha256"])

    legacy = dict(packet)
    legacy["expected_extra_design_dates"] = 3
    detached = _seal_packet(legacy)
    with pytest.raises(InvalidSupervisor):
        supervisor.validate_full_packet_document(canonical_json(legacy) + b"\n", detached)
