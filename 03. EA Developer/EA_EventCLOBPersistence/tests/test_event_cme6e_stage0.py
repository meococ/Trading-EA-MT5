from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import platform
import sys
import types
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


WORKSPACE = Path(__file__).resolve().parents[3]
SOURCE = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_EventCLOBPersistence"
    / "research"
    / "analyze_event_cme6e_stage0.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_event_cme6e_stage0", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records(
    module,
    *,
    count: int = 30,
    start_ns: int = 1_000_000_000_000,
    end_ns: int = 1_060_000_000_000,
    bid_size: int = 3,
    ask_size: int = 1,
    spread_ticks: float = 1.0,
    instrument_id: int = 1191,
    last_staleness_ns: int = 1_000_000_000,
):
    last = end_ns - last_staleness_ns
    first = last - (count - 1) * 500_000_000
    result = []
    for index in range(count):
        row = {
            "ts_event": first + index * 500_000_000,
            "instrument_id": instrument_id,
            "bid_px_00": 1_100_000_000,
            "ask_px_00": 1_100_000_000 + int(spread_ticks * module.TICK_RAW),
        }
        for level in range(5):
            row[f"bid_sz_{level:02d}"] = bid_size
            row[f"ask_sz_{level:02d}"] = ask_size
        result.append(row)
    return result


def passed_segment(i5: float, *, spread_ticks: float = 1.0):
    return {
        "record_count": 30,
        "quality_pass": True,
        "reason_codes": [],
        "i5_median": i5,
        "median_spread_ticks": spread_ticks,
        "first_ts_event_ns": 1,
        "last_ts_event_ns": 2,
        "max_gap_ns": 1,
    }


def test_segment_formula_and_exact_quality_boundaries_pass() -> None:
    module = load_module()
    start_ns = 1_000_000_000_000
    end_ns = start_ns + 60 * module.ONE_SECOND_NS
    result = module.analyze_segment(
        records(module, start_ns=start_ns, end_ns=end_ns, spread_ticks=2.0),
        start_ns=start_ns,
        end_ns=end_ns,
        expected_instrument_id=1191,
    )

    assert result["quality_pass"] is True
    assert result["record_count"] == 30
    assert result["reason_codes"] == []
    assert result["i5_median"] == pytest.approx(0.5)
    assert result["median_spread_ticks"] == pytest.approx(2.0)
    assert result["last_ts_event_ns"] == end_ns - module.ONE_SECOND_NS
    assert result["max_gap_ns"] == 500_000_000


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("count", "RECORD_COUNT_LT_30"),
        ("stale", "FINAL_STALENESS_GT_1S"),
        ("gap", "MAX_GAP_GT_1S"),
        ("denominator", "I5_DENOMINATOR_NONPOSITIVE_OR_NONFINITE"),
        ("nonmonotonic", "TS_EVENT_NONMONOTONIC"),
        ("outside", "TS_EVENT_OUTSIDE_HALF_OPEN_SEGMENT"),
        ("instrument", "INSTRUMENT_ID_MISMATCH"),
    ],
)
def test_segment_quality_failures_are_deterministic(mutation: str, reason: str) -> None:
    module = load_module()
    start_ns = 1_000_000_000_000
    end_ns = start_ns + 60 * module.ONE_SECOND_NS
    sample = records(module, start_ns=start_ns, end_ns=end_ns)
    if mutation == "count":
        sample = sample[:29]
    elif mutation == "stale":
        for row in sample:
            row["ts_event"] -= 1
    elif mutation == "gap":
        last = end_ns - module.ONE_SECOND_NS
        gaps = [module.ONE_SECOND_NS] * 29
        gaps[14] += 1
        first = last - sum(gaps)
        current = first
        sample[0]["ts_event"] = current
        for index, gap in enumerate(gaps, 1):
            current += gap
            sample[index]["ts_event"] = current
    elif mutation == "denominator":
        for row in sample:
            for level in range(5):
                row[f"bid_sz_{level:02d}"] = 0
                row[f"ask_sz_{level:02d}"] = 0
    elif mutation == "nonmonotonic":
        sample[10]["ts_event"], sample[11]["ts_event"] = (
            sample[11]["ts_event"],
            sample[10]["ts_event"],
        )
    elif mutation == "outside":
        sample[0]["ts_event"] = start_ns - 1
    else:
        sample[0]["instrument_id"] = 999

    result = module.analyze_segment(
        sample,
        start_ns=start_ns,
        end_ns=end_ns,
        expected_instrument_id=1191,
    )

    assert result["quality_pass"] is False
    assert reason in result["reason_codes"]


def test_pair_spread_and_sign_eligibility_boundaries() -> None:
    module = load_module()
    eligible = module.evaluate_pair(
        passed_segment(0.2), passed_segment(0.5, spread_ticks=2.0)
    )
    assert eligible == {
        "pair_quality_pass": True,
        "pair_reason_codes": [],
        "i5_pre": 0.2,
        "i5_late": 0.5,
        "delta_i5": 0.3,
        "late_median_spread_ticks": 2.0,
        "feature_eligible": True,
        "direction": "LONG",
    }

    too_wide = module.evaluate_pair(
        passed_segment(0.2), passed_segment(0.5, spread_ticks=2.0000001)
    )
    assert too_wide["pair_quality_pass"] is False
    assert too_wide["feature_eligible"] is False
    assert "LATE_MEDIAN_SPREAD_GT_2_TICKS" in too_wide["pair_reason_codes"]

    equal = module.evaluate_pair(passed_segment(0.5), passed_segment(0.5))
    zero_late = module.evaluate_pair(passed_segment(-0.5), passed_segment(0.0))
    opposite = module.evaluate_pair(passed_segment(0.6), passed_segment(0.2))
    assert equal["feature_eligible"] is False
    assert zero_late["feature_eligible"] is False
    assert opposite["feature_eligible"] is False
    assert equal["direction"] == zero_late["direction"] == opposite["direction"] == ""


def canonical_request(module, *, event_id: str = "EVT0001", segment: str = "PRE"):
    event_time = "2019-01-03T15:00:00.000Z"
    return module.expected_request_contract(event_id, event_time, segment)


def bind_request_file(module, path: Path, request: dict, payload: bytes) -> None:
    path.write_bytes(payload)
    request.update(
        {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest().upper(),
            "records": 0,
            "source_empty": True,
            "charged_empty_evidence": {
                "paid_request_completed": True,
                "response_validated": True,
                "retry_prohibited": True,
            },
        }
    )


def valid_run_authority(module) -> dict:
    return {
        "schema_version": "event_clob_stage0_run_authority.v1",
        "hypothesis_id": module.HYPOTHESIS_ID,
        "base_packet_path": module._workspace_path(module.TASK_PACKET_PATH),
        "base_packet_sha256": module.TASK_PACKET_SHA256,
        "amendment_path": module._workspace_path(module.V3_TASK_PACKET_PATH),
        "amendment_sha256": module.V3_TASK_PACKET_SHA256,
        "review_verdict": "PASS",
        "reviewed_analyzer_path": module._workspace_path(module.SOURCE_PATH),
        "reviewed_analyzer_sha256": module.sha256_file(module.SOURCE_PATH),
        "reviewed_tests_path": module._workspace_path(module.TEST_PATH),
        "reviewed_tests_sha256": module.sha256_file(module.TEST_PATH),
        "required_python_relative_path": module.REQUIRED_PYTHON_RELATIVE_PATH,
        "required_python_sha256": module.REQUIRED_PYTHON_SHA256,
        "required_python_version": platform.python_version(),
        "required_databento_version": "0.54.0",
        "live_stage0_authorized": True,
    }


def test_request_contract_rejects_wrong_bounds_year_and_duplicate_identity() -> None:
    module = load_module()
    request = canonical_request(module)
    module.validate_request_contract(request)

    wrong_bound = copy.deepcopy(request)
    wrong_bound["end"] = "2019-01-03T14:59:46.000Z"
    with pytest.raises(module.Stage0Error, match="bounds"):
        module.validate_request_contract(wrong_bound)

    wrong_year = module.expected_request_contract(
        "EVT0500", "2021-01-03T15:00:00.000Z", "PRE"
    )
    with pytest.raises(module.Stage0Error, match="design year"):
        module.validate_request_contract(wrong_year)

    with pytest.raises(module.Stage0Error, match="duplicate request identity"):
        module.validate_unique_requests([request, copy.deepcopy(request)])


def test_file_binding_rejects_hash_size_record_and_extra_file_mismatch(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    payload = b"synthetic-local-dbn"
    path = tmp_path / request["filename"]
    path.write_bytes(payload)
    request.update(
        {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest().upper(),
            "records": 30,
            "source_empty": False,
            "charged_empty_evidence": None,
        }
    )
    module.verify_file_binding(path, request)

    for field, value, match in (
        ("bytes", len(payload) + 1, "size mismatch"),
        ("sha256", "0" * 64, "hash mismatch"),
    ):
        changed = copy.deepcopy(request)
        changed[field] = value
        with pytest.raises(module.Stage0Error, match=match):
            module.verify_file_binding(path, changed)

    decoded = {"records": [{}] * 29}
    with pytest.raises(module.Stage0Error, match="record-count mismatch"):
        module.verify_decoded_record_count(request, decoded)

    (tmp_path / "unmanifested.dbn.zst").write_bytes(b"extra")
    with pytest.raises(module.Stage0Error, match="unmanifested extra"):
        module.verify_raw_file_set(tmp_path, [request])


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("dataset", "OTHER", "DBN_DATASET_MISMATCH"),
        ("schema", "trades", "DBN_SCHEMA_MISMATCH"),
        ("stype_in", "raw_symbol", "DBN_STYPE_IN_MISMATCH"),
        ("stype_out", "raw_symbol", "DBN_STYPE_OUT_MISMATCH"),
        ("symbols", ["OTHER"], "DBN_SYMBOL_MISMATCH"),
        ("mapping_ok", False, "INSTRUMENT_MAPPING_INVALID"),
    ],
)
def test_decoded_metadata_mismatch_is_fail_closed(field, value, reason) -> None:
    module = load_module()
    decoded = {
        "dataset": module.DATASET,
        "schema": module.SCHEMA,
        "stype_in": module.STYPE_IN,
        "stype_out": module.STYPE_OUT,
        "symbols": [module.SYMBOL],
        "mapping_ok": True,
        "expected_instrument_id": 1191,
        "metadata_start_ns": module.parse_utc_ns("2019-01-03T14:59:00.000Z"),
        "metadata_end_ns": module.parse_utc_ns("2019-01-03T14:59:45.000Z"),
        "records": [],
    }
    decoded[field] = value
    reasons = module.decoded_metadata_reason_codes(decoded, canonical_request(module))
    assert reason in reasons


def test_explicit_source_empty_is_never_quality_or_feature_eligible() -> None:
    module = load_module()
    empty = module.explicit_source_empty_segment()
    nonempty = passed_segment(0.5)
    pair = module.evaluate_pair(empty, nonempty)
    assert empty["quality_pass"] is False
    assert empty["reason_codes"] == ["EXPLICIT_SOURCE_EMPTY"]
    assert pair["pair_quality_pass"] is False
    assert pair["feature_eligible"] is False


def synthetic_rows(count: int, *, eligible: int, source_quality: int):
    rows = []
    for index in range(count):
        rows.append(
            {
                "pre_source_empty": False,
                "late_source_empty": False,
                "pair_quality_pass": index < source_quality,
                "feature_eligible": index < eligible,
                "fatal_source_integrity_failure": False,
            }
        )
    return rows


def test_population_denominator_and_cadence_gates() -> None:
    module = load_module()
    summary_209 = module.summarize_population(
        synthetic_rows(329, eligible=209, source_quality=250)
    )
    summary_208 = module.summarize_population(
        synthetic_rows(329, eligible=208, source_quality=250)
    )
    assert summary_209["event_count"] == 329
    assert summary_209["pre_nonempty_coverage"] == pytest.approx(1.0)
    assert summary_209["source_quality_paired_count"] == 250
    assert summary_209["feature_eligible_count"] == 209
    assert summary_209["gates"]["feature_eligible_count"]["pass"] is True
    assert summary_209["gates"]["feature_eligible_cadence"]["pass"] is True
    assert summary_208["gates"]["feature_eligible_count"]["pass"] is False
    assert summary_208["gates"]["feature_eligible_cadence"]["pass"] is False
    assert module.cadence_is_legal(2.0) is True
    assert module.cadence_is_legal(5.0) is True
    assert module.cadence_is_legal(1.999999) is False
    assert module.cadence_is_legal(5.000001) is False


def test_nonempty_coverages_use_329_and_pair_requires_both_segments() -> None:
    module = load_module()
    rows = synthetic_rows(329, eligible=209, source_quality=250)
    rows[0]["pre_source_empty"] = True
    rows[1]["late_source_empty"] = True
    rows[2]["pre_source_empty"] = True
    rows[2]["late_source_empty"] = True
    summary = module.summarize_population(rows)
    assert summary["pre_nonempty_count"] == 327
    assert summary["late_nonempty_count"] == 327
    assert summary["paired_nonempty_event_count"] == 326
    assert summary["pre_nonempty_coverage"] == pytest.approx(327 / 329)
    assert summary["late_nonempty_coverage"] == pytest.approx(327 / 329)
    assert summary["paired_nonempty_event_coverage"] == pytest.approx(326 / 329)


def test_deterministic_ledger_and_manifest_bytes_have_no_wall_clock() -> None:
    module = load_module()
    row = {field: "" for field in module.LEDGER_FIELDS}
    row.update(
        {
            "event_clock_id": "EVT0001",
            "event_time_utc": "2019-01-03T15:00:00.000Z",
            "pre_segment_quality": True,
            "late_segment_quality": True,
            "pair_quality_pass": True,
            "feature_eligible": True,
            "direction": "LONG",
            "i5_pre": 0.2,
            "i5_late": 0.5,
            "delta_i5": 0.3,
            "late_median_spread_ticks": 2.0,
            "pre_quality_reason_codes": [],
            "late_quality_reason_codes": [],
            "pair_quality_reason_codes": [],
        }
    )
    ledger_a = module.render_ledger([row])
    ledger_b = module.render_ledger([copy.deepcopy(row)])
    assert ledger_a == ledger_b
    assert b"generated_at" not in ledger_a

    summary = module.summarize_population(
        synthetic_rows(329, eligible=209, source_quality=250)
    )
    manifest_a = module.render_json(
        module.build_output_manifest(
            bindings={"task_packet_sha256": "A" * 64},
            raw_bindings=[],
            summary=summary,
            analyzer_sha256="B" * 64,
            tests_sha256="C" * 64,
            ledger_sha256=hashlib.sha256(ledger_a).hexdigest().upper(),
        )
    )
    manifest_b = module.render_json(
        module.build_output_manifest(
            bindings={"task_packet_sha256": "A" * 64},
            raw_bindings=[],
            summary=copy.deepcopy(summary),
            analyzer_sha256="B" * 64,
            tests_sha256="C" * 64,
            ledger_sha256=hashlib.sha256(ledger_b).hexdigest().upper(),
        )
    )
    assert manifest_a == manifest_b
    assert b"generated_at" not in manifest_a
    decoded = json.loads(manifest_a)
    assert decoded["prohibited_read_counters"] == {
        "databento_client_constructions": 0,
        "eurusd_price_reads": 0,
        "middle_window_reads": 0,
        "network_calls": 0,
        "outcome_field_reads": 0,
        "paid_calls": 0,
        "validation_source_reads": 0,
    }


def test_cli_paths_are_exact_and_source_has_no_network_client_surface(
    tmp_path: Path,
) -> None:
    module = load_module()
    module.validate_exact_cli_paths(
        data_root=module.CANONICAL_DATA_ROOT,
        task_packet=module.TASK_PACKET_PATH,
        prereg=module.PREREG_PATH,
        clock_csv=module.CLOCK_PATH,
        ledger_out=module.LEDGER_PATH,
        manifest_out=module.OUTPUT_MANIFEST_PATH,
        readout_out=module.READOUT_PATH,
    )
    with pytest.raises(module.Stage0Error, match="exact canonical path"):
        module.validate_exact_cli_paths(
            data_root=tmp_path,
            task_packet=module.TASK_PACKET_PATH,
            prereg=module.PREREG_PATH,
            clock_csv=module.CLOCK_PATH,
            ledger_out=module.LEDGER_PATH,
            manifest_out=module.OUTPUT_MANIFEST_PATH,
            readout_out=module.READOUT_PATH,
        )

    source = SOURCE.read_text(encoding="utf-8")
    assert "DBNStore.from_bytes" in source
    assert "DBNStore.from_file" not in source
    assert "Historical(" not in source
    assert "Live(" not in source
    assert "timeseries.get_range" not in source
    assert "requests.get" not in source
    assert "urllib" not in source
    assert "socket" not in source


def test_local_decoder_uses_only_exact_dbnstore_from_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    request = canonical_request(module)
    calls = []

    class Store:
        dataset = module.DATASET
        schema = module.SCHEMA
        stype_in = module.STYPE_IN
        stype_out = module.STYPE_OUT
        symbols = [module.SYMBOL]
        mappings = {
            module.SYMBOL: [
                {
                    "start_date": date(2019, 1, 3),
                    "end_date": date(2019, 1, 4),
                    "symbol": "1191",
                }
            ]
        }
        start = datetime(2019, 1, 3, 14, 59, tzinfo=timezone.utc)
        end = datetime(2019, 1, 3, 14, 59, 45, tzinfo=timezone.utc)

        @staticmethod
        def to_ndarray():
            return []

    class DBNStore:
        @staticmethod
        def from_bytes(payload):
            calls.append(payload)
            return Store()

        @staticmethod
        def from_file(_path):
            raise AssertionError("path-based decoder is forbidden")

    monkeypatch.setitem(sys.modules, "databento", types.SimpleNamespace(DBNStore=DBNStore))
    payload = b"exact-compressed-manifest-bound-bytes"
    decoded = module._decode_local_dbn(payload, request)
    assert calls == [payload]
    assert decoded["mapping_ok"] is True
    assert decoded["expected_instrument_id"] == 1191
    assert decoded["records"] == []


def test_full_329_event_synthetic_snapshot_is_deterministic(tmp_path: Path) -> None:
    module = load_module()
    clocks = []
    downloads = []
    decoded_by_request = {}
    origin = datetime(2019, 1, 1, 12, 0, tzinfo=timezone.utc)
    for index in range(module.EXPECTED_EVENTS):
        event_id = f"EVT{index + 1:04d}"
        event_time = origin + timedelta(hours=12 * index)
        event_time_utc = module.format_utc(event_time)
        clocks.append(
            {"event_clock_id": event_id, "event_time_utc": event_time_utc}
        )
        for segment in ("PRE", "LATE"):
            request = module.expected_request_contract(event_id, event_time_utc, segment)
            payload = request["request_id"].encode("ascii")
            (tmp_path / request["filename"]).write_bytes(payload)
            request.update(
                {
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest().upper(),
                    "records": 30,
                    "source_empty": False,
                    "charged_empty_evidence": None,
                }
            )
            start_ns = module.parse_utc_ns(request["start"])
            end_ns = module.parse_utc_ns(request["end"])
            decoded_by_request[request["request_id"]] = {
                "dataset": module.DATASET,
                "schema": module.SCHEMA,
                "stype_in": module.STYPE_IN,
                "stype_out": module.STYPE_OUT,
                "symbols": [module.SYMBOL],
                "mapping_ok": True,
                "expected_instrument_id": 1191,
                "metadata_start_ns": start_ns,
                "metadata_end_ns": end_ns,
                "records": records(
                    module,
                    start_ns=start_ns,
                    end_ns=end_ns,
                    bid_size=3,
                    ask_size=2 if segment == "PRE" else 1,
                    last_staleness_ns=(
                        module.ONE_SECOND_NS if segment == "PRE" else 500_000_000
                    ),
                ),
            }
            downloads.append(request)

    manifest = {
        "schema_version": "event_clob_cme6e_mbp10_download_manifest.v1",
        "status": "DOWNLOADED_FULL_DBN_VALIDATION_PASS",
        "hypothesis_id": module.HYPOTHESIS_ID,
        "profile": "design-segments",
        "downloads": downloads,
        "in_flight": None,
        "paid_requests_completed": module.EXPECTED_REQUESTS,
        "timeseries_calls": module.EXPECTED_REQUESTS,
        "validation_source_sealed": True,
        "outcome_fields_used": False,
        "price_data_read": False,
    }

    def loader(_payload, request):
        return copy.deepcopy(decoded_by_request[request["request_id"]])

    rows_a, summary_a, raw_a = module.analyze_snapshot(
        manifest=manifest,
        clocks=clocks,
        raw_root=tmp_path,
        record_loader=loader,
    )
    rows_b, summary_b, raw_b = module.analyze_snapshot(
        manifest=copy.deepcopy(manifest),
        clocks=copy.deepcopy(clocks),
        raw_root=tmp_path,
        record_loader=loader,
    )
    assert len(rows_a) == module.EXPECTED_EVENTS
    assert len(raw_a) == module.EXPECTED_REQUESTS
    assert summary_a["feature_eligible_count"] == module.EXPECTED_EVENTS, json.dumps(
        rows_a[0], sort_keys=True
    )
    assert summary_a["stage0_pass"] is True
    assert module.render_ledger(rows_a) == module.render_ledger(rows_b)
    assert summary_a == summary_b
    assert raw_a == raw_b


def test_frozen_binding_verifier_does_not_decode_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    monkeypatch.setattr(
        module,
        "_decode_local_dbn",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("binding verifier decoded raw DBN")
        ),
    )
    bindings = module.verify_frozen_bindings()
    assert bindings["task_packet_sha256"] == module.TASK_PACKET_SHA256
    assert bindings["prereg_sha256"] == module.PREREG_SHA256
    assert bindings["download_manifest_sha256"] == module.DOWNLOAD_MANIFEST_SHA256
    assert bindings["registry"]["prefix_sha256"] == module.V14_PREFIX_SHA256


def test_cli_rejects_noncanonical_root_before_analysis(tmp_path: Path) -> None:
    module = load_module()
    with pytest.raises(SystemExit):
        module.main(["--data-root", str(tmp_path)])
    assert not (tmp_path / "stage0_event_feature_ledger.csv").exists()


def test_verified_snapshot_binds_exact_bytes_and_rejects_mutation_before_decode(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    original = b"manifest-bound-compressed-dbn"
    bind_request_file(module, path, request, original)
    seen: list[bytes] = []

    def decoder(payload: bytes, _request: dict):
        seen.append(payload)
        path.write_bytes(b"mutated-before-decoder-return")
        return {"records": []}

    with pytest.raises(module.Stage0Error, match="changed after byte binding"):
        module.decode_verified_snapshot(
            path,
            request,
            containment_root=tmp_path,
            decoder=decoder,
        )
    assert seen == [original]


def test_verified_snapshot_rejects_replacement_after_decode(tmp_path: Path) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    original = b"manifest-bound-compressed-dbn"
    bind_request_file(module, path, request, original)

    def decoder(_payload: bytes, _request: dict):
        replacement = tmp_path / "replacement.dbn.zst"
        replacement.write_bytes(original)
        os.replace(replacement, path)
        return {"records": []}

    with pytest.raises(module.Stage0Error, match="identity changed after decode"):
        module.decode_verified_snapshot(
            path,
            request,
            containment_root=tmp_path,
            decoder=decoder,
        )


def test_secure_path_rejects_alias_and_reparse_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    directory = tmp_path / "canonical"
    directory.mkdir()
    target = directory / "file.bin"
    target.write_bytes(b"x")
    alias = directory / ".." / "canonical" / "file.bin"
    with pytest.raises(module.Stage0Error, match="lexical exact path"):
        module.validate_secure_path(
            alias,
            expected=target,
            containment_root=tmp_path,
            must_exist=True,
        )

    original = module._is_reparse_component
    monkeypatch.setattr(
        module,
        "_is_reparse_component",
        lambda item: item == directory or original(item),
    )
    with pytest.raises(module.Stage0Error, match="reparse component"):
        module.validate_secure_path(
            target,
            expected=target,
            containment_root=tmp_path,
            must_exist=True,
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ({"review_verdict": "FAIL"}, "review verdict"),
        ({"live_stage0_authorized": False}, "not authorized"),
        ({"reviewed_analyzer_sha256": "0" * 64}, "analyzer hash"),
        ({"reviewed_tests_sha256": "0" * 64}, "tests hash"),
        ({"base_packet_sha256": "0" * 64}, "base packet"),
        ({"amendment_sha256": "0" * 64}, "amendment"),
    ],
)
def test_run_authority_is_exact_and_fail_closed(
    tmp_path: Path, mutation: dict, match: str
) -> None:
    module = load_module()
    authority = valid_run_authority(module)
    authority.update(mutation)
    path = tmp_path / "run_authority.json"
    payload = module.render_json(authority)
    path.write_bytes(payload)
    with pytest.raises(module.Stage0Error, match=match):
        module.validate_run_authority(
            path,
            module.sha256_bytes(payload),
            expected_path=path,
            containment_root=tmp_path,
        )


def test_run_authority_rejects_wrong_or_altered_receipt_hash(tmp_path: Path) -> None:
    module = load_module()
    authority = valid_run_authority(module)
    path = tmp_path / "run_authority.json"
    payload = module.render_json(authority)
    path.write_bytes(payload)
    with pytest.raises(module.Stage0Error, match="run-authority hash"):
        module.validate_run_authority(
            path,
            "0" * 64,
            expected_path=path,
            containment_root=tmp_path,
        )
    path.write_bytes(payload + b" ")
    with pytest.raises(module.Stage0Error, match="run-authority hash"):
        module.validate_run_authority(
            path,
            module.sha256_bytes(payload),
            expected_path=path,
            containment_root=tmp_path,
        )


def test_missing_run_authority_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    missing = tmp_path / "missing_run_authority.json"
    with pytest.raises(module.Stage0Error, match="missing run-authority"):
        module.validate_run_authority(
            missing,
            "0" * 64,
            expected_path=missing,
            containment_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("required_python_relative_path", "C:/Python/python.exe", "runtime path"),
        ("required_python_sha256", "0" * 64, "runtime hash"),
        ("required_python_version", "0.0.0", "Python version"),
        ("required_databento_version", "0.0.0", "Databento version"),
    ],
)
def test_run_authority_enforces_exact_runtime(
    tmp_path: Path, field: str, value: str, match: str
) -> None:
    module = load_module()
    authority = valid_run_authority(module)
    authority[field] = value
    path = tmp_path / "run_authority.json"
    payload = module.render_json(authority)
    path.write_bytes(payload)
    with pytest.raises(module.Stage0Error, match=match):
        module.validate_run_authority(
            path,
            module.sha256_bytes(payload),
            expected_path=path,
            containment_root=tmp_path,
        )


def test_run_authority_revalidation_detects_bound_source_change(
    tmp_path: Path,
) -> None:
    module = load_module()
    source_copy = tmp_path / "analyzer.py"
    tests_copy = tmp_path / "tests.py"
    source_copy.write_bytes(b"source-v1")
    tests_copy.write_bytes(b"tests-v1")
    authority = valid_run_authority(module)
    authority["reviewed_analyzer_path"] = source_copy.name
    authority["reviewed_analyzer_sha256"] = module.sha256_file(source_copy)
    authority["reviewed_tests_path"] = tests_copy.name
    authority["reviewed_tests_sha256"] = module.sha256_file(tests_copy)
    path = tmp_path / "run_authority.json"
    payload = module.render_json(authority)
    path.write_bytes(payload)
    snapshot = module.validate_run_authority(
        path,
        module.sha256_bytes(payload),
        expected_path=path,
        containment_root=tmp_path,
        reviewed_analyzer_path=source_copy,
        reviewed_tests_path=tests_copy,
    )
    source_copy.write_bytes(b"source-v2")
    with pytest.raises(module.Stage0Error, match="analyzer hash"):
        module.revalidate_run_authority(snapshot)


def test_output_path_rechecks_ancestor_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    output = output_dir / "ledger.csv"
    original = module._is_reparse_component
    monkeypatch.setattr(
        module,
        "_is_reparse_component",
        lambda item: item == output_dir or original(item),
    )
    with pytest.raises(module.Stage0Error, match="reparse component"):
        module.validate_secure_path(
            output,
            expected=output,
            containment_root=tmp_path,
            must_exist=False,
        )
    assert not output.exists()


def test_prepublication_authority_failure_precedes_all_output_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    writes: list[Path] = []
    authority_snapshot = {
        "expected_sha256": "A" * 64,
        "payload": {
            "reviewed_analyzer_sha256": "B" * 64,
            "reviewed_tests_sha256": "C" * 64,
        },
    }
    monkeypatch.setattr(module, "validate_exact_cli_paths", lambda **_kwargs: None)
    monkeypatch.setattr(
        module, "validate_run_authority", lambda *_args, **_kwargs: authority_snapshot
    )
    monkeypatch.setattr(module, "verify_frozen_bindings", lambda: {})
    monkeypatch.setattr(module, "load_design_clocks", lambda _path: [])
    monkeypatch.setattr(module, "_load_json", lambda _path: {})
    monkeypatch.setattr(
        module,
        "analyze_snapshot",
        lambda **_kwargs: ([], {"stage0_pass": False}, []),
    )
    monkeypatch.setattr(module, "render_ledger", lambda _rows: b"ledger")
    monkeypatch.setattr(module, "build_output_manifest", lambda **_kwargs: {})
    monkeypatch.setattr(module, "render_json", lambda _value: b"manifest")
    monkeypatch.setattr(module, "render_readout", lambda _summary: b"readout")
    monkeypatch.setattr(
        module,
        "revalidate_run_authority",
        lambda _snapshot: (_ for _ in ()).throw(
            module.Stage0Error("reviewed analyzer hash changed before publication")
        ),
    )
    monkeypatch.setattr(
        module,
        "_write_immutable",
        lambda path, _payload, **_kwargs: writes.append(path),
    )

    with pytest.raises(module.Stage0Error, match="analyzer hash changed"):
        module.run_stage0(
            run_authority=module.RUN_AUTHORITY_PATH,
            expected_run_authority_sha256="A" * 64,
        )
    assert writes == []


def test_revalidation_rejects_identical_inode_swap_after_path_lstat(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    payload = b"byte-identical-manifest-payload"
    bind_request_file(module, path, request, payload)
    snapshot = module.capture_verified_snapshot(
        path, request, containment_root=tmp_path
    )
    replacement = tmp_path / "replacement.dbn.zst"
    replacement.write_bytes(payload)

    def hook(phase: str, point: str, _path: Path, _handle) -> None:
        if phase == "adversarial" and point == "after_path_before":
            os.replace(replacement, path)

    with pytest.raises(module.Stage0Error, match="identity changed"):
        module.revalidate_verified_snapshot(
            snapshot,
            phase="adversarial",
            _test_hook=hook,
        )


def test_full_decode_rejects_identical_swap_before_revalidation_read(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    payload = b"byte-identical-manifest-payload"
    bind_request_file(module, path, request, payload)
    replacement = tmp_path / "replacement.dbn.zst"
    replacement.write_bytes(payload)
    decoder_calls: list[bytes] = []

    def hook(phase: str, point: str, _path: Path, _handle) -> None:
        if phase == "before decode" and point == "after_path_before":
            os.replace(replacement, path)

    with pytest.raises(module.Stage0Error, match="identity changed"):
        module.decode_verified_snapshot(
            path,
            request,
            containment_root=tmp_path,
            decoder=lambda exact, _request: decoder_calls.append(exact) or {"records": []},
            _test_hook=hook,
        )
    assert decoder_calls == []


def test_identity_read_rejects_mutation_after_handle_fstat(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    payload = b"manifest-bound-compressed-payload"
    bind_request_file(module, path, request, payload)
    snapshot = module.capture_verified_snapshot(
        path, request, containment_root=tmp_path
    )

    def hook(phase: str, point: str, _path: Path, _handle) -> None:
        if phase == "mutate-open-handle" and point == "after_handle_before":
            path.write_bytes(b"mutated-open-file")

    with pytest.raises(module.Stage0Error, match="changed|identity"):
        module.revalidate_verified_snapshot(
            snapshot,
            phase="mutate-open-handle",
            _test_hook=hook,
        )


def test_identity_read_rejects_swap_after_handle_read_before_path_lstat(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    payload = b"manifest-bound-compressed-payload"
    bind_request_file(module, path, request, payload)
    snapshot = module.capture_verified_snapshot(
        path, request, containment_root=tmp_path
    )
    replacement = tmp_path / "replacement.dbn.zst"
    replacement.write_bytes(payload)

    def hook(phase: str, point: str, _path: Path, _handle) -> None:
        if phase == "swap-after-read" and point == "before_path_after":
            os.replace(replacement, path)

    with pytest.raises(module.Stage0Error, match="identity changed"):
        module.revalidate_verified_snapshot(
            snapshot,
            phase="swap-after-read",
            _test_hook=hook,
        )


def test_unchanged_identity_read_passes_without_path_read_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    payload = b"unchanged-manifest-bound-payload"
    bind_request_file(module, path, request, payload)
    snapshot = module.capture_verified_snapshot(
        path, request, containment_root=tmp_path
    )
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda _self: (_ for _ in ()).throw(
            AssertionError("identity-critical code reopened via Path.read_bytes")
        ),
    )
    module.revalidate_verified_snapshot(snapshot, phase="unchanged")


def test_final_raw_revalidation_binds_original_identity_and_one_handle(
    tmp_path: Path,
) -> None:
    module = load_module()
    request = canonical_request(module)
    path = tmp_path / request["filename"]
    payload = b"final-raw-manifest-bound-payload"
    bind_request_file(module, path, request, payload)
    snapshot = module.capture_verified_snapshot(
        path, request, containment_root=tmp_path
    )
    binding = {
        "filename": request["filename"],
        "bytes": snapshot["bytes"],
        "sha256": snapshot["sha256"],
        "_verified_identity": snapshot["identity"],
    }
    replacement = tmp_path / "replacement.dbn.zst"
    replacement.write_bytes(payload)

    def hook(phase: str, point: str, _path: Path, _handle) -> None:
        if phase == "final raw revalidation" and point == "after_path_before":
            os.replace(replacement, path)

    with pytest.raises(module.Stage0Error, match="identity changed"):
        module.revalidate_raw_bindings(tmp_path, [binding], _test_hook=hook)
