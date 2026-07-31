import argparse
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import threading
from pathlib import Path


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
PLAN_SHA256 = "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
SOURCE_RECEIPT_SCHEMA = "trendstack_002_source_validation.v2"
PACKET_RECEIPT_SCHEMA = "trendstack_002_decision_packet_receipt.v2"
PACKET_SCHEMA = "trendstack_002_decision_packet.v1"
LEDGER_SCHEMA = "trendstack_002_stage0_eligibility_ledger_row.v1"
TRACE_SCHEMA = "trendstack_002_stage0_access_trace_row.v1"
RECONCILIATION_SCHEMA = "trendstack_002_stage0_reconciliation.v1"
RECEIPT_SCHEMA = "trendstack_002_stage0_receipt.v1"
EXPECTED_WORKER_SHA256 = "70D4A33047039971C453B35AF6D5B75683E2AF3997EEAA35443C1899A447252A"
EXPECTED_PROVENANCE = {
    "source_manifest_sha256": "7F7E06B1477F05BB6682BB6F387407D1807A3AC00052BCD54F93FF74E13E60E1",
    "source_receipt_sha256": "DB4523AD07E064535094F133590D182378E43E5C3E2B04E72292C08F1F1F4D67",
    "decision_manifest_sha256": "D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA",
    "decision_receipt_sha256": "DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320",
    "packet_set_sha256": "22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E",
    "extractor_sha256": "0CB3AE2051A9ACE8CD1A92BE657A96123D7C3B95F179D607ECA5DA3507720CEC",
    "request_count": 96,
    "source_rows": 49723,
    "shard_file_count": 4567,
    "packet_count": 1817,
    "maximum_utc_timestamp": "2022-12-30T21:00:00",
    "maximum_source_time_utc": "2022-12-30T11:00:00",
}
MAX_WORKER_STDOUT_BYTES = 16384
MAX_WORKER_STDERR_BYTES = 4096
MAX_WORKER_SOURCE_CHARS = 24000
WORKER_TIMEOUT_SECONDS = 60
WORKER_TERMINATION_GRACE_SECONDS = 5
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
EMPTY_PREFIX_SHA256 = hashlib.sha256(b"TRENDSTACK_002_STAGE0_EMPTY_PREFIX").hexdigest().upper()
SHA256_RE = re.compile(r"[0-9A-F]{64}\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
PACKET_PATH_RE = re.compile(r"(DESIGN|VALIDATION_FEATURE_ONLY)/(\d{4}-\d{2}-\d{2})\.json\Z")
PACKET_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "opportunity_id",
    "split",
    "decision_cutoff_utc",
    "m252_direction",
    "m6_direction",
    "alignment",
    "atr20",
    "control_m252_eligible",
    "control_m6_eligible",
    "challenger_stack_eligible",
    "negative_disagree_eligible",
    "exclusion_reason",
    "valid_prior_close_count",
    "max_source_time_utc",
    "source_shard_chain_hashes",
    "source_chain_sha256",
    "extractor_sha256",
    "source_plan_sha256",
    "packet_payload_sha256",
}
MANIFEST_FIELDS = {
    "hypothesis_id",
    "opportunity_id",
    "split",
    "packet_path",
    "packet_payload_sha256",
    "source_chain_sha256",
    "max_source_time_utc",
    "extractor_sha256",
    "source_plan_sha256",
    "forbidden_field_scan",
    "packet_file_sha256",
    "packet_bytes",
}
WORKER_ROW_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "opportunity_id",
    "split",
    "packet_payload_sha256",
    "packet_file_sha256",
    "source_chain_sha256",
    "max_source_time_utc",
    "feature_complete",
    "control_m252_only_eligible",
    "control_m252_only_direction",
    "control_m6_only_eligible",
    "control_m6_only_direction",
    "challenger_stack_eligible",
    "challenger_stack_direction",
    "negative_disagree_eligible",
    "negative_disagree_direction",
    "exclusion_reason",
}
SOURCE_RECEIPT_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "source_plan_sha256",
    "source_manifest_sha256",
    "request_count",
    "shard_file_count",
    "source_rows",
    "maximum_utc_timestamp",
    "runtime_provenance",
    "all_shard_hashes_verified",
    "no_2023_canonical_request",
    "no_2023_row",
    "no_2023_file",
    "m1_opened",
    "outcomes_opened",
    "physical_partition_status",
}
PACKET_RECEIPT_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "source_plan_sha256",
    "source_manifest_sha256",
    "source_validation_receipt_sha256",
    "decision_packet_manifest_sha256",
    "packet_count",
    "unique_opportunity_ids",
    "packet_set_sha256",
    "deterministic_rebuild_status",
    "forbidden_field_scan",
    "maximum_source_time_utc",
    "no_2023_packet",
    "m1_opened",
    "outcomes_opened",
    "holdout_opened",
    "economic_metrics_computed",
    "strategy_process_raw_source_access",
    "verdict",
}
REQUEST_MANIFEST_FIELDS = {
    "record_type",
    "request_id",
    "canonical_from_utc",
    "canonical_to_inclusive_utc",
    "source_end_exclusive_utc",
    "api_server_wall_from_encoded_as_utc",
    "api_server_wall_to_encoded_as_utc",
    "canonical_roundtrip_status",
    "symbol",
    "timeframe",
    "response",
    "runtime_hashes",
}
REQUEST_RESPONSE_FIELDS = {
    "rows",
    "first_server_time",
    "last_server_time",
    "first_utc_time",
    "last_utc_time",
    "duplicate_utc_opens",
    "gap_count",
    "maximum_gap_hours",
    "gap_multiple_status",
    "geometry_status",
    "holdout_rows_received",
}
SHARD_MANIFEST_FIELDS = {
    "record_type",
    "shard_path",
    "split",
    "date_utc",
    "segment",
    "rows",
    "bytes",
    "sha256",
    "canonical_row_content_sha256",
    "first_utc_time",
    "last_utc_time",
    "request_ids",
    "row_groups",
    "duplicate_utc_opens",
    "gap_multiple_status",
    "geometry_status",
    "holdout_rows_received",
    "runtime_hashes",
}
RUNTIME_HASH_FIELDS = {
    "terminal_executable_sha256",
    "python_executable_sha256",
    "metatrader5_native_module_sha256",
    "clock_tool_sha256",
    "extractor_sha256",
    "source_plan_sha256",
}
RUNTIME_PROVENANCE_FIELDS = {
    "terminal_executable_label",
    "terminal_executable_sha256",
    "terminal_build",
    "python_executable_label",
    "python_executable_sha256",
    "metatrader5_version",
    "metatrader5_native_module_label",
    "metatrader5_native_module_sha256",
    "clock_tool_label",
    "clock_tool_sha256",
    "extractor_label",
    "extractor_sha256",
    "source_plan_label",
    "source_plan_sha256",
    "account_guard",
    "pandas_version",
    "pyarrow_version",
}
ACCOUNT_GUARD_FIELDS = {
    "terminal_build",
    "terminal_trade_allowed",
    "account_mode",
    "server",
    "company",
    "symbol",
    "symbol_digits",
    "symbol_point",
}


class InvalidEngineering(Exception):
    pass


def _canonical_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(data):
    return hashlib.sha256(data).hexdigest().upper()


def _require(condition, message):
    if not condition:
        raise InvalidEngineering(message)


def _require_sha256(value, label):
    _require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None, f"invalid {label}")


def _reject_json_constant(value):
    raise InvalidEngineering(f"non-finite JSON constant: {value}")


def _parse_json(raw, label):
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidEngineering(f"invalid JSON: {label}") from exc
    _require(isinstance(value, dict), f"JSON object required: {label}")
    return value


def _parse_jsonl(raw, label):
    _require(raw.endswith(b"\n"), f"JSONL must end with newline: {label}")
    lines = raw.splitlines()
    _require(len(lines) > 0, f"empty JSONL: {label}")
    rows = []
    for index, line in enumerate(lines, start=1):
        _require(line != b"", f"blank JSONL row: {label}:{index}")
        rows.append(_parse_json(line, f"{label}:{index}"))
        _require(line == _canonical_bytes(rows[-1]), f"noncanonical JSONL row: {label}:{index}")
    return rows


def _absolute_path(path):
    return Path(os.path.abspath(os.fspath(path)))


def _lstat_no_reparse(path):
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise InvalidEngineering("filesystem component cannot be inspected") from exc
    attributes = getattr(metadata, "st_file_attributes", 0)
    _require(not stat.S_ISLNK(metadata.st_mode), "filesystem symlink is forbidden")
    _require(not attributes & FILE_ATTRIBUTE_REPARSE_POINT, "filesystem reparse point is forbidden")
    return metadata


def _validate_component_chain(path):
    absolute = _absolute_path(path)
    parts = absolute.parts
    _require(len(parts) > 0, "filesystem path is empty")
    current = Path(parts[0])
    _lstat_no_reparse(current)
    for part in parts[1:]:
        current = current / part
        _lstat_no_reparse(current)
    return absolute


def _identity(metadata):
    attributes = getattr(metadata, "st_file_attributes", 0)
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_nlink,
        metadata.st_mode,
        attributes,
        bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT),
    )


def _open_handle_identity(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_nlink,
        metadata.st_mode,
        getattr(metadata, "st_file_attributes", 0),
    )


def _validate_root(root, frozen_root):
    root = _validate_component_chain(root)
    frozen_root = _validate_component_chain(frozen_root)
    root_metadata = _lstat_no_reparse(root)
    frozen_metadata = _lstat_no_reparse(frozen_root)
    _require(stat.S_ISDIR(root_metadata.st_mode), "source package root is not a directory")
    _require(stat.S_ISDIR(frozen_metadata.st_mode), "frozen root is not a directory")
    try:
        resolved = root.resolve(strict=True)
        frozen_resolved = frozen_root.resolve(strict=True)
    except OSError as exc:
        raise InvalidEngineering("source package root cannot be resolved") from exc
    _require(resolved == frozen_resolved, "source package root does not match frozen root")
    return resolved


def _resolve_with_strict_existing_parent(path):
    absolute = _absolute_path(path)
    cursor = absolute
    missing_parts = []
    while True:
        try:
            os.lstat(cursor)
            break
        except FileNotFoundError:
            _require(cursor.parent != cursor, "output root has no existing parent")
            missing_parts.append(cursor.name)
            cursor = cursor.parent
        except OSError as exc:
            raise InvalidEngineering("output root parent cannot be inspected") from exc
    existing = _validate_component_chain(cursor)
    try:
        resolved_existing = existing.resolve(strict=True)
    except OSError as exc:
        raise InvalidEngineering("output root parent cannot be resolved") from exc
    return resolved_existing.joinpath(*reversed(missing_parts))


def _paths_overlap(first, second):
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def _validate_output_disjointness(output_root, package_root, frozen_root):
    package_resolved = _validate_component_chain(package_root).resolve(strict=True)
    frozen_resolved = _validate_component_chain(frozen_root).resolve(strict=True)
    output_resolved = _resolve_with_strict_existing_parent(output_root)
    _require(
        not _paths_overlap(output_resolved, package_resolved)
        and not _paths_overlap(output_resolved, frozen_resolved),
        "output root overlaps immutable input",
    )
    return output_resolved


def _validate_confined_path(path, root, *, require_file=True):
    path = _absolute_path(path)
    root = _absolute_path(root)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise InvalidEngineering("path escapes frozen root") from exc
    _validate_component_chain(path)
    metadata = _lstat_no_reparse(path)
    if require_file:
        _require(stat.S_ISREG(metadata.st_mode), "required source package file is not regular")
        _require(metadata.st_nlink == 1, "hardlinked source package file is forbidden")
    else:
        _require(stat.S_ISDIR(metadata.st_mode), "required source package directory is missing")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise InvalidEngineering("source package path cannot be resolved") from exc
    _require(resolved.is_relative_to(root), "resolved path escapes frozen root")
    return path


def _read_stable_regular_file_with_identity(path):
    path = _validate_component_chain(path)
    before = _lstat_no_reparse(path)
    _require(stat.S_ISREG(before.st_mode), "opened path is not a regular file")
    _require(before.st_nlink == 1, "hardlinked opened file is forbidden")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require(
                _open_handle_identity(opened) == _open_handle_identity(before),
                "opened file identity changed before read",
            )
            payload = stream.read()
            after_open = os.fstat(stream.fileno())
            _require(
                _open_handle_identity(after_open) == _open_handle_identity(before),
                "opened file identity changed during read",
            )
        after_path = _lstat_no_reparse(path)
    except OSError as exc:
        raise InvalidEngineering("failed to read stable regular file") from exc
    _require(_identity(after_path) == _identity(before), "opened file identity changed after read")
    _require(len(payload) == before.st_size, "opened file size changed during read")
    return payload, _identity(before)


def _read_stable_regular_file(path):
    payload, _ = _read_stable_regular_file_with_identity(path)
    return payload


def _read_bound_file(path, root):
    checked = _validate_confined_path(path, root)
    return _read_stable_regular_file(checked)


def _read_bound_file_with_identity(path, root):
    checked = _validate_confined_path(path, root)
    return _read_stable_regular_file_with_identity(checked)


def _enumerate_packet_tree(packet_root, root):
    packet_root = _validate_confined_path(packet_root, root, require_file=False)
    pending = [packet_root]
    files = []
    directory_identities = {}
    while pending:
        directory = pending.pop()
        _validate_confined_path(directory, root, require_file=False)
        before = _lstat_no_reparse(directory)
        relative_directory = directory.relative_to(root).as_posix()
        directory_identities[relative_directory] = _identity(before)
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise InvalidEngineering("decision packet directory enumeration failed") from exc
        _require(
            _identity(_lstat_no_reparse(directory)) == _identity(before),
            "decision packet directory changed during enumeration",
        )
        for entry in entries:
            path = Path(entry.path)
            metadata = _lstat_no_reparse(path)
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                _require(metadata.st_nlink == 1, "hardlinked decision packet is forbidden")
                files.append(path.relative_to(packet_root).as_posix())
            else:
                raise InvalidEngineering("unsupported decision packet filesystem entry")
    for relative_directory, expected_identity in directory_identities.items():
        _require(
            _identity(_lstat_no_reparse(root / Path(relative_directory))) == expected_identity,
            "decision packet directory changed during enumeration",
        )
    return sorted(files), dict(sorted(directory_identities.items()))


def _enumerate_packet_files(packet_root, root):
    files, _ = _enumerate_packet_tree(packet_root, root)
    return files


def _parse_utc(value, label):
    _require(type(value) is str and value != "", f"invalid {label}")
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)
    except ValueError as exc:
        raise InvalidEngineering(f"invalid {label}") from exc


def _validate_runtime_hashes(runtime_hashes):
    _require(isinstance(runtime_hashes, dict) and set(runtime_hashes) == RUNTIME_HASH_FIELDS, "runtime hash schema mismatch")
    for field, value in runtime_hashes.items():
        _require_sha256(value, f"runtime hash {field}")
    _require(runtime_hashes["source_plan_sha256"] == PLAN_SHA256, "runtime plan hash mismatch")
    _require(
        runtime_hashes["extractor_sha256"] == EXPECTED_PROVENANCE["extractor_sha256"],
        "runtime extractor hash mismatch",
    )


def _validate_runtime_provenance(runtime, runtime_hashes):
    _require(isinstance(runtime, dict) and set(runtime) == RUNTIME_PROVENANCE_FIELDS, "runtime provenance schema mismatch")
    for field in RUNTIME_HASH_FIELDS:
        _require(runtime[field] == runtime_hashes[field], f"runtime provenance {field} mismatch")
    _require(type(runtime["terminal_build"]) is int and runtime["terminal_build"] > 0, "invalid terminal build")
    exact_labels = {
        "terminal_executable_label": "terminal64.exe",
        "clock_tool_label": "fivepercent_server_clock.py",
        "extractor_label": "prepare_trendstack_002_source.py",
        "source_plan_label": "HYP-TRENDSTACK-EURUSD-H1-002_SOURCE_PLAN.md",
    }
    for field, expected in exact_labels.items():
        _require(runtime[field] == expected, f"runtime provenance {field} mismatch")
    for field in (
        "python_executable_label",
        "metatrader5_version",
        "metatrader5_native_module_label",
        "pandas_version",
        "pyarrow_version",
    ):
        _require(type(runtime[field]) is str and runtime[field] != "", f"invalid runtime provenance {field}")
        _require("/" not in runtime[field] and "\\" not in runtime[field], f"runtime provenance {field} is a path")
    guard = runtime["account_guard"]
    _require(isinstance(guard, dict) and set(guard) == ACCOUNT_GUARD_FIELDS, "account guard schema mismatch")
    _require(
        type(guard["terminal_build"]) is int and guard["terminal_build"] == runtime["terminal_build"],
        "account guard terminal build mismatch",
    )
    _require(guard["terminal_trade_allowed"] is False, "account guard trading is enabled")
    _require(guard["account_mode"] == "DEMO", "account guard is not DEMO")
    _require(guard["server"] == "FivePercentOnline-Real", "account guard server mismatch")
    _require(guard["company"] == "Five Percent Online Ltd", "account guard company mismatch")
    _require(guard["symbol"] == "EURUSD" and guard["symbol_digits"] == 5, "account guard symbol mismatch")
    _require(
        type(guard["symbol_point"]) in (int, float)
        and not isinstance(guard["symbol_point"], bool)
        and abs(float(guard["symbol_point"]) - 0.00001) <= 1e-12,
        "account guard point mismatch",
    )


def _validate_source_manifest(rows):
    request_count = 0
    shard_count = 0
    source_rows = 0
    maximum_raw_time = None
    runtime_hashes = None
    request_ids = set()
    source_start = datetime.datetime(2015, 1, 2, tzinfo=datetime.timezone.utc)
    design_start = datetime.date(2016, 1, 4)
    validation_start = datetime.date(2021, 1, 1)
    holdout_start = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
    for row in rows:
        record_type = row.get("record_type")
        if record_type == "request":
            _require(set(row) == REQUEST_MANIFEST_FIELDS, "request manifest schema mismatch")
            request_count += 1
            request_id = row["request_id"]
            _require(type(request_id) is str and request_id != "" and request_id not in request_ids, "invalid request id")
            request_ids.add(request_id)
            _require(row["symbol"] == "EURUSD" and row["timeframe"] == "H1", "request symbol/timeframe mismatch")
            _require(row["canonical_roundtrip_status"] == "PASS", "request roundtrip status mismatch")
            canonical_from = _parse_utc(row["canonical_from_utc"], "request start")
            canonical_to = _parse_utc(row["canonical_to_inclusive_utc"], "request inclusive end")
            source_end = _parse_utc(row["source_end_exclusive_utc"], "request exclusive end")
            _require(source_start <= canonical_from <= canonical_to < source_end <= holdout_start, "request range outside frozen source range")
            _require(canonical_to + datetime.timedelta(seconds=1) == source_end, "request end geometry mismatch")
            _parse_utc(row["api_server_wall_from_encoded_as_utc"], "API request start")
            _parse_utc(row["api_server_wall_to_encoded_as_utc"], "API request end")
            response = row["response"]
            _require(isinstance(response, dict) and set(response) == REQUEST_RESPONSE_FIELDS, "request response schema mismatch")
            _require(type(response["rows"]) is int and response["rows"] >= 0, "invalid request row count")
            for field in ("duplicate_utc_opens", "gap_count", "holdout_rows_received"):
                _require(type(response[field]) is int and response[field] >= 0, f"invalid request response {field}")
            _require(response["holdout_rows_received"] == 0, "request contains holdout rows")
            _require(response["gap_multiple_status"] == "PASS" and response["geometry_status"] == "PASS", "request quality status failed")
            for field in ("first_utc_time", "last_utc_time"):
                if response[field] is not None:
                    _parse_utc(response[field], f"request response {field}")
        elif record_type == "shard":
            _require(set(row) == SHARD_MANIFEST_FIELDS, "shard manifest schema mismatch")
            shard_count += 1
            try:
                shard_date = datetime.date.fromisoformat(row["date_utc"])
            except (TypeError, ValueError) as exc:
                raise InvalidEngineering("invalid shard date") from exc
            _require(datetime.date(2015, 1, 2) <= shard_date < datetime.date(2023, 1, 1), "shard date outside frozen source range")
            expected_split = "WARMUP" if shard_date < design_start else "DESIGN" if shard_date < validation_start else "VALIDATION_FEATURE_ONLY"
            _require(row["split"] == expected_split, "shard split/date mismatch")
            _require(row["segment"] in ("pre12", "post12"), "invalid shard segment")
            expected_path = f"raw_h1/{expected_split}/{shard_date}/{row['segment']}.parquet"
            _require(row["shard_path"] == expected_path, "shard path mismatch")
            _require(type(row["rows"]) is int and row["rows"] > 0, "invalid shard row count")
            _require(type(row["bytes"]) is int and row["bytes"] > 0, "invalid shard byte count")
            _require(type(row["row_groups"]) is int and row["row_groups"] == 1, "invalid shard row-group count")
            _require(type(row["duplicate_utc_opens"]) is int and row["duplicate_utc_opens"] == 0, "duplicate shard UTC opens")
            _require(type(row["holdout_rows_received"]) is int and row["holdout_rows_received"] == 0, "shard contains holdout rows")
            _require(row["gap_multiple_status"] == "PASS" and row["geometry_status"] == "PASS", "shard quality status failed")
            _require_sha256(row["sha256"], "shard sha256")
            _require_sha256(row["canonical_row_content_sha256"], "shard content sha256")
            first_time = _parse_utc(row["first_utc_time"], "shard first time")
            last_time = _parse_utc(row["last_utc_time"], "shard last time")
            _require(first_time.date() == last_time.date() == shard_date and first_time <= last_time, "shard timestamp/date mismatch")
            if row["segment"] == "pre12":
                _require(last_time.hour < 12, "pre12 shard contains post12 time")
            else:
                _require(first_time.hour >= 12, "post12 shard contains pre12 time")
            _require(isinstance(row["request_ids"], list) and row["request_ids"], "shard request ids missing")
            _require(all(type(value) is str and value != "" for value in row["request_ids"]), "invalid shard request id")
            source_rows += row["rows"]
            maximum_raw_time = last_time if maximum_raw_time is None or last_time > maximum_raw_time else maximum_raw_time
        else:
            raise InvalidEngineering("unknown source manifest record type")
        _validate_runtime_hashes(row["runtime_hashes"])
        if runtime_hashes is None:
            runtime_hashes = row["runtime_hashes"]
        else:
            _require(row["runtime_hashes"] == runtime_hashes, "source manifest runtime hash drift")
    _require(request_count == EXPECTED_PROVENANCE["request_count"], "source request count mismatch")
    _require(shard_count == EXPECTED_PROVENANCE["shard_file_count"], "source shard count mismatch")
    _require(source_rows == EXPECTED_PROVENANCE["source_rows"], "source row count mismatch")
    _require(maximum_raw_time is not None, "source manifest has no shard time")
    _require(
        maximum_raw_time == _parse_utc(EXPECTED_PROVENANCE["maximum_utc_timestamp"], "expected maximum raw time"),
        "source maximum raw time mismatch",
    )
    return runtime_hashes


def _validate_source_receipt(receipt, source_manifest_raw, runtime_hashes):
    _require(set(receipt) == SOURCE_RECEIPT_FIELDS, "source receipt schema fields mismatch")
    _require(receipt["schema_version"] == SOURCE_RECEIPT_SCHEMA, "source receipt schema mismatch")
    _require(receipt["hypothesis_id"] == HYPOTHESIS_ID, "source receipt hypothesis mismatch")
    _require(receipt["source_plan_sha256"] == PLAN_SHA256, "source receipt plan mismatch")
    _require(receipt["source_manifest_sha256"] == _sha256(source_manifest_raw), "source manifest hash mismatch")
    _require(receipt["physical_partition_status"] == "PASS", "source physical validation is not PASS")
    _require(receipt["all_shard_hashes_verified"] is True, "source shard hashes are not verified")
    for field in ("no_2023_canonical_request", "no_2023_row", "no_2023_file"):
        _require(receipt[field] is True, f"source receipt {field} is not true")
    for field in ("m1_opened", "outcomes_opened"):
        _require(receipt[field] is False, f"source receipt {field} is not false")
    for field in ("request_count", "shard_file_count", "source_rows"):
        _require(receipt[field] == EXPECTED_PROVENANCE[field], f"source receipt {field} mismatch")
    _require(
        _parse_utc(receipt["maximum_utc_timestamp"], "source receipt maximum time")
        == _parse_utc(EXPECTED_PROVENANCE["maximum_utc_timestamp"], "expected source maximum time"),
        "source receipt maximum time mismatch",
    )
    _validate_runtime_provenance(receipt["runtime_provenance"], runtime_hashes)


def _validate_packet_receipt(receipt, source_manifest_raw, source_receipt_raw, packet_manifest_raw):
    _require(set(receipt) == PACKET_RECEIPT_FIELDS, "packet receipt schema fields mismatch")
    _require(receipt["schema_version"] == PACKET_RECEIPT_SCHEMA, "packet receipt schema mismatch")
    _require(receipt["hypothesis_id"] == HYPOTHESIS_ID, "packet receipt hypothesis mismatch")
    _require(receipt["source_plan_sha256"] == PLAN_SHA256, "packet receipt plan mismatch")
    bindings = {
        "source_manifest_sha256": _sha256(source_manifest_raw),
        "source_validation_receipt_sha256": _sha256(source_receipt_raw),
        "decision_packet_manifest_sha256": _sha256(packet_manifest_raw),
    }
    for field, expected in bindings.items():
        _require(receipt[field] == expected, f"packet receipt {field} mismatch")
    _require(receipt["unique_opportunity_ids"] is True, "packet opportunity ids are not unique")
    _require(receipt["deterministic_rebuild_status"] == "PASS_DISK_REOPEN", "packet reopen validation failed")
    _require(receipt["forbidden_field_scan"] == "PASS", "packet forbidden-field scan failed")
    _require(receipt["no_2023_packet"] is True, "packet receipt permits 2023")
    for field in ("m1_opened", "outcomes_opened", "holdout_opened", "economic_metrics_computed"):
        _require(receipt[field] is False, f"packet receipt {field} is not false")
    _require(
        receipt["strategy_process_raw_source_access"] == "NOT_YET_VERIFIED_STAGE0_REQUIRED",
        "packet strategy-access status mismatch",
    )
    _require(receipt["verdict"] == "SOURCE_READY_FOR_INDEPENDENT_STAGE0_REVIEW", "packet receipt verdict mismatch")
    _require(receipt["packet_set_sha256"] == EXPECTED_PROVENANCE["packet_set_sha256"], "packet set pinned hash mismatch")
    _require(receipt["packet_count"] == EXPECTED_PROVENANCE["packet_count"], "packet receipt pinned count mismatch")
    _require(
        _parse_utc(receipt["maximum_source_time_utc"], "packet receipt maximum source time")
        == _parse_utc(EXPECTED_PROVENANCE["maximum_source_time_utc"], "expected packet source time"),
        "packet receipt maximum source time mismatch",
    )


def _validate_manifest_rows(rows):
    opportunity_ids = []
    packet_paths = []
    for row in rows:
        _require(set(row) == MANIFEST_FIELDS, "decision packet manifest schema mismatch")
        _require(row["hypothesis_id"] == HYPOTHESIS_ID, "manifest hypothesis mismatch")
        _require(row["source_plan_sha256"] == PLAN_SHA256, "manifest plan mismatch")
        _require(row["extractor_sha256"] == EXPECTED_PROVENANCE["extractor_sha256"], "manifest extractor mismatch")
        _require(row["forbidden_field_scan"] == "PASS", "manifest forbidden-field scan failed")
        for field in ("packet_payload_sha256", "source_chain_sha256", "extractor_sha256", "packet_file_sha256"):
            _require_sha256(row[field], f"manifest {field}")
        _require(type(row["packet_bytes"]) is int and row["packet_bytes"] > 0, "invalid manifest packet bytes")
        opportunity = row["opportunity_id"]
        _require(isinstance(opportunity, str) and DATE_RE.fullmatch(opportunity) is not None, "invalid manifest opportunity")
        try:
            opportunity_date = datetime.date.fromisoformat(opportunity)
        except ValueError as exc:
            raise InvalidEngineering("invalid manifest opportunity") from exc
        _require(
            datetime.date(2016, 1, 4) <= opportunity_date < datetime.date(2023, 1, 1),
            "manifest opportunity outside frozen range",
        )
        match = PACKET_PATH_RE.fullmatch(row["packet_path"]) if isinstance(row["packet_path"], str) else None
        _require(match is not None, "noncanonical packet path")
        _require(match.group(1) == row["split"] and match.group(2) == opportunity, "packet path identity mismatch")
        _require("2023" not in row["packet_path"], "forbidden 2023 packet path")
        expected_split = "DESIGN" if opportunity < "2021-01-01" else "VALIDATION_FEATURE_ONLY"
        _require(row["split"] == expected_split, "manifest split date mismatch")
        opportunity_ids.append(opportunity)
        packet_paths.append(row["packet_path"])
    _require(opportunity_ids == sorted(opportunity_ids), "manifest opportunity order mismatch")
    _require(len(opportunity_ids) == len(set(opportunity_ids)), "duplicate manifest opportunity id")
    _require(len(packet_paths) == len(set(packet_paths)), "duplicate manifest packet path")


def _validate_packet_against_manifest(packet, raw, row):
    _require(set(packet) == PACKET_FIELDS, "decision packet schema fields mismatch")
    _require(packet["schema_version"] == PACKET_SCHEMA, "decision packet schema mismatch")
    _require(packet["hypothesis_id"] == HYPOTHESIS_ID, "decision packet hypothesis mismatch")
    _require(packet["source_plan_sha256"] == PLAN_SHA256, "decision packet plan mismatch")
    _require(len(raw) == row["packet_bytes"], "decision packet byte count mismatch")
    _require(_sha256(raw) == row["packet_file_sha256"], "decision packet file hash mismatch")
    unsigned = {key: value for key, value in packet.items() if key != "packet_payload_sha256"}
    _require(_sha256(_canonical_bytes(unsigned)) == packet["packet_payload_sha256"], "decision packet payload hash mismatch")
    mappings = {
        "opportunity_id": "opportunity_id",
        "split": "split",
        "packet_payload_sha256": "packet_payload_sha256",
        "source_chain_sha256": "source_chain_sha256",
        "max_source_time_utc": "max_source_time_utc",
        "extractor_sha256": "extractor_sha256",
        "source_plan_sha256": "source_plan_sha256",
    }
    for packet_field, manifest_field in mappings.items():
        _require(packet[packet_field] == row[manifest_field], f"packet/manifest {packet_field} mismatch")


def validate_source_package(package_root, *, frozen_root):
    try:
        root = _validate_root(package_root, frozen_root)
        root_identity = _identity(_lstat_no_reparse(root))
        bound_file_bytes = {}
        bound_file_identities = {}
        for relative in (
            "source_manifest.jsonl",
            "source_validation_receipt.json",
            "decision_packet_manifest.jsonl",
            "decision_packet_receipt.json",
        ):
            payload, identity = _read_bound_file_with_identity(root / relative, root)
            bound_file_bytes[relative] = payload
            bound_file_identities[relative] = identity
        source_manifest_raw = bound_file_bytes["source_manifest.jsonl"]
        source_receipt_raw = bound_file_bytes["source_validation_receipt.json"]
        packet_manifest_raw = bound_file_bytes["decision_packet_manifest.jsonl"]
        packet_receipt_raw = bound_file_bytes["decision_packet_receipt.json"]
        pinned_files = {
            "source manifest": (source_manifest_raw, "source_manifest_sha256"),
            "source receipt": (source_receipt_raw, "source_receipt_sha256"),
            "decision manifest": (packet_manifest_raw, "decision_manifest_sha256"),
            "decision receipt": (packet_receipt_raw, "decision_receipt_sha256"),
        }
        for label, (payload, expected_field) in pinned_files.items():
            _require(_sha256(payload) == EXPECTED_PROVENANCE[expected_field], f"pinned {label} hash mismatch")
        source_manifest = _parse_jsonl(source_manifest_raw, "source_manifest.jsonl")
        _require(len(source_manifest) > 0, "empty source manifest")
        source_receipt = _parse_json(source_receipt_raw, "source_validation_receipt.json")
        packet_manifest = _parse_jsonl(packet_manifest_raw, "decision_packet_manifest.jsonl")
        packet_receipt = _parse_json(packet_receipt_raw, "decision_packet_receipt.json")
        runtime_hashes = _validate_source_manifest(source_manifest)
        _validate_source_receipt(source_receipt, source_manifest_raw, runtime_hashes)
        _validate_packet_receipt(
            packet_receipt,
            source_manifest_raw,
            source_receipt_raw,
            packet_manifest_raw,
        )
        _validate_manifest_rows(packet_manifest)
        _require(
            packet_receipt["packet_count"] == len(packet_manifest) == EXPECTED_PROVENANCE["packet_count"],
            "packet receipt count mismatch",
        )

        packet_root = _validate_confined_path(root / "decision_packets", root, require_file=False)
        physical_paths, packet_directory_identities = _enumerate_packet_tree(packet_root, root)
        expected_paths = sorted(row["packet_path"] for row in packet_manifest)
        _require(sorted(physical_paths) == expected_paths, "decision packet physical set mismatch")

        packet_bytes_by_path = {}
        packet_file_identities = {}
        packet_set_hasher = hashlib.sha256()
        for relative in expected_paths:
            raw, identity = _read_bound_file_with_identity(packet_root / Path(relative), root)
            row = next(item for item in packet_manifest if item["packet_path"] == relative)
            packet = _parse_json(raw, relative)
            _validate_packet_against_manifest(packet, raw, row)
            packet_bytes_by_path[relative] = raw
            packet_file_identities[relative] = identity
            packet_set_hasher.update(relative.encode("utf-8"))
            packet_set_hasher.update(b"\0")
            packet_set_hasher.update(raw)
        _require(
            packet_set_hasher.hexdigest().upper() == packet_receipt["packet_set_sha256"],
            "decision packet set hash mismatch",
        )
        _require(
            _parse_utc(packet_receipt["maximum_source_time_utc"], "packet receipt maximum source time")
            == max(_parse_utc(row["max_source_time_utc"], "manifest maximum source time") for row in packet_manifest),
            "packet maximum source time mismatch",
        )
        _require(_identity(_lstat_no_reparse(root)) == root_identity, "source package changed during validation")
        for relative, expected_identity in bound_file_identities.items():
            _require(
                _identity(_lstat_no_reparse(root / relative)) == expected_identity,
                "source package changed during validation",
            )
        final_physical_paths, final_packet_directory_identities = _enumerate_packet_tree(packet_root, root)
        _require(final_physical_paths == expected_paths, "source package changed during validation")
        _require(
            final_packet_directory_identities == packet_directory_identities,
            "source package changed during validation",
        )
        for relative, expected_identity in packet_file_identities.items():
            _require(
                _identity(_lstat_no_reparse(packet_root / Path(relative))) == expected_identity,
                "source package changed during validation",
            )
        package_component_identities = {".": root_identity, **packet_directory_identities}
        return {
            "root": root,
            "root_identity": root_identity,
            "package_component_identities": package_component_identities,
            "packet_manifest": packet_manifest,
            "packet_bytes_by_path": packet_bytes_by_path,
            "packet_file_identities": packet_file_identities,
            "bound_file_bytes": bound_file_bytes,
            "bound_file_identities": bound_file_identities,
            "source_manifest_sha256": _sha256(source_manifest_raw),
            "source_validation_receipt_sha256": _sha256(source_receipt_raw),
            "decision_packet_manifest_sha256": _sha256(packet_manifest_raw),
            "decision_packet_receipt_sha256": _sha256(packet_receipt_raw),
            "packet_set_sha256": packet_receipt["packet_set_sha256"],
        }
    except InvalidEngineering:
        raise
    except Exception as exc:
        raise InvalidEngineering(f"source package validation failed: {type(exc).__name__}") from exc


def _recheck_source_package(validated):
    try:
        root = _validate_root(validated["root"], validated["root"])
        _require(
            _identity(_lstat_no_reparse(root)) == validated["root_identity"],
            "source package changed during Stage-0",
        )
        for relative, expected_raw in validated["bound_file_bytes"].items():
            current_raw, current_identity = _read_bound_file_with_identity(root / relative, root)
            _require(current_raw == expected_raw, "source package changed during Stage-0")
            _require(
                current_identity == validated["bound_file_identities"][relative],
                "source package changed during Stage-0",
            )
        packet_root = _validate_confined_path(root / "decision_packets", root, require_file=False)
        expected_paths = sorted(validated["packet_bytes_by_path"])
        current_paths, current_packet_directory_identities = _enumerate_packet_tree(packet_root, root)
        _require(
            current_paths == expected_paths,
            "source package changed during Stage-0",
        )
        _require(
            {".": _identity(_lstat_no_reparse(root)), **current_packet_directory_identities}
            == validated["package_component_identities"],
            "source package changed during Stage-0",
        )
        for relative in expected_paths:
            current_raw, current_identity = _read_bound_file_with_identity(packet_root / Path(relative), root)
            _require(
                current_raw == validated["packet_bytes_by_path"][relative],
                "source package changed during Stage-0",
            )
            _require(
                current_identity == validated["packet_file_identities"][relative],
                "source package changed during Stage-0",
            )
        final_paths, final_packet_directory_identities = _enumerate_packet_tree(packet_root, root)
        _require(final_paths == expected_paths, "source package changed during Stage-0")
        _require(
            {".": _identity(_lstat_no_reparse(root)), **final_packet_directory_identities}
            == validated["package_component_identities"],
            "source package changed during Stage-0",
        )
        for relative, expected_identity in validated["packet_file_identities"].items():
            _require(
                _identity(_lstat_no_reparse(packet_root / Path(relative))) == expected_identity,
                "source package changed during Stage-0",
            )
        _require(
            _identity(_lstat_no_reparse(root)) == validated["root_identity"],
            "source package changed during Stage-0",
        )
    except InvalidEngineering as exc:
        if str(exc) == "source package changed during Stage-0":
            raise
        raise InvalidEngineering("source package changed during Stage-0") from exc
    except Exception as exc:
        raise InvalidEngineering("source package changed during Stage-0") from exc


def _write_fsync(stream, value):
    stream.write(_canonical_bytes(value) + b"\n")
    stream.flush()
    os.fsync(stream.fileno())


def _validate_new_stream(path, stream):
    metadata = _lstat_no_reparse(path)
    opened = os.fstat(stream.fileno())
    _require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, "new output file is not singular regular file")
    _require(metadata.st_dev == opened.st_dev and metadata.st_ino == opened.st_ino, "new output stream identity mismatch")


def _write_new_json(path, value):
    path = Path(path)
    payload = _canonical_bytes(value) + b"\n"
    try:
        _validate_component_chain(path.parent)
        with path.open("xb") as stream:
            _validate_new_stream(path, stream)
            _write_fsync(stream, value)
    except OSError as exc:
        raise InvalidEngineering("immutable output creation failed") from exc
    _require(_read_stable_regular_file(path) == payload, "immutable output readback mismatch")


def _next_prefix(previous, row_payload_sha256):
    return _sha256(
        _canonical_bytes(
            {
                "prior_prefix_sha256": previous,
                "row_payload_sha256": row_payload_sha256,
            }
        )
    )


def _finalize_ledger_row(worker_row, row_index, packet_path, prior_prefix):
    base = dict(worker_row)
    base.update(
        {
            "schema_version": LEDGER_SCHEMA,
            "row_index": row_index,
            "packet_path": packet_path,
            "prior_prefix_sha256": prior_prefix,
        }
    )
    row_payload_sha256 = _sha256(_canonical_bytes(base))
    next_prefix = _next_prefix(prior_prefix, row_payload_sha256)
    base["row_payload_sha256"] = row_payload_sha256
    base["next_prefix_sha256"] = next_prefix
    return base


def _load_trusted_worker(worker_path):
    worker_path = _absolute_path(worker_path)
    expected_path = _absolute_path(Path(__file__).with_name("stage0_trendstack_002_worker.py"))
    _require(worker_path == expected_path, "worker path does not match the frozen worker")
    worker_bytes = _read_stable_regular_file(worker_path)
    worker_sha256 = _sha256(worker_bytes)
    _require(worker_sha256 == EXPECTED_WORKER_SHA256, "worker pinned hash mismatch")
    try:
        worker_source = worker_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidEngineering("worker source is not UTF-8") from exc
    _require("\x00" not in worker_source and len(worker_source) <= MAX_WORKER_SOURCE_CHARS, "worker source cannot be launched immutably")
    return worker_source, worker_sha256


def _validate_worker_row(row):
    _require(set(row) == WORKER_ROW_FIELDS, "worker output schema mismatch")
    _require(row["schema_version"] == "trendstack_002_stage0_worker_row.v1", "worker row schema mismatch")
    _require(row["hypothesis_id"] == HYPOTHESIS_ID, "worker row hypothesis mismatch")
    _require(row["split"] in ("DESIGN", "VALIDATION_FEATURE_ONLY"), "worker row split mismatch")
    for field in (
        "feature_complete",
        "control_m252_only_eligible",
        "control_m6_only_eligible",
        "challenger_stack_eligible",
        "negative_disagree_eligible",
    ):
        _require(type(row[field]) is bool, f"worker row {field} must be bool")
    pairs = (
        ("control_m252_only_eligible", "control_m252_only_direction"),
        ("control_m6_only_eligible", "control_m6_only_direction"),
        ("challenger_stack_eligible", "challenger_stack_direction"),
        ("negative_disagree_eligible", "negative_disagree_direction"),
    )
    for eligible_field, direction_field in pairs:
        direction = row[direction_field]
        if row[eligible_field]:
            _require(type(direction) is int and direction in (-1, 1), f"worker row {direction_field} invalid")
        else:
            _require(direction is None, f"worker row {direction_field} must be null")
    _require(not (row["challenger_stack_eligible"] and row["negative_disagree_eligible"]), "worker row arm conflict")
    for field in ("packet_payload_sha256", "packet_file_sha256", "source_chain_sha256"):
        _require_sha256(row[field], f"worker row {field}")


def _request_worker_termination(process, termination_lock):
    with termination_lock:
        try:
            if process.poll() is None:
                process.terminate()
        except OSError:
            pass


def _terminate_and_wait(process):
    try:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=WORKER_TERMINATION_GRACE_SECONDS)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=WORKER_TERMINATION_GRACE_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvalidEngineering("isolated worker could not be terminated") from exc


def _bounded_pipe_reader(stream, byte_cap, label, process, termination_lock, capture, state):
    try:
        while True:
            remaining = byte_cap - len(capture)
            chunk = os.read(stream.fileno(), min(4096, remaining + 1))
            if chunk == b"":
                return
            if len(chunk) > remaining:
                capture.extend(chunk[:remaining])
                state["overflow"] = True
                _request_worker_termination(process, termination_lock)
                return
            capture.extend(chunk)
    except BaseException as exc:
        state["reader_error"] = f"{label}:{type(exc).__name__}"
        _request_worker_termination(process, termination_lock)


def _run_worker(worker_source, worker_sha256, stage_dir, expected_sha256):
    _require(_sha256(worker_source.encode("utf-8")) == worker_sha256, "in-memory worker source hash mismatch")
    command = [
        sys.executable,
        "-I",
        "-S",
        "-c",
        worker_source,
        "--packet",
        "packet.json",
        "--expected-sha256",
        expected_sha256,
    ]
    try:
        process = subprocess.Popen(
            command,
            cwd=stage_dir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
    except OSError as exc:
        raise InvalidEngineering("isolated worker process could not start") from exc
    _require(process.stdout is not None and process.stderr is not None, "isolated worker pipes are unavailable")
    stdout = bytearray()
    stderr = bytearray()
    stdout_state = {"overflow": False, "reader_error": None}
    stderr_state = {"overflow": False, "reader_error": None}
    termination_lock = threading.Lock()
    readers = [
        threading.Thread(
            target=_bounded_pipe_reader,
            args=(
                process.stdout,
                MAX_WORKER_STDOUT_BYTES,
                "stdout",
                process,
                termination_lock,
                stdout,
                stdout_state,
            ),
            daemon=True,
        ),
        threading.Thread(
            target=_bounded_pipe_reader,
            args=(
                process.stderr,
                MAX_WORKER_STDERR_BYTES,
                "stderr",
                process,
                termination_lock,
                stderr,
                stderr_state,
            ),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        process.wait(timeout=WORKER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_and_wait(process)
    finally:
        for reader in readers:
            reader.join(timeout=WORKER_TERMINATION_GRACE_SECONDS)
        process.stdout.close()
        process.stderr.close()
    _require(not any(reader.is_alive() for reader in readers), "worker output reader did not terminate")
    if timed_out:
        raise InvalidEngineering("isolated worker timed out")
    _require(stdout_state["reader_error"] is None, "worker stdout reader failed")
    _require(stderr_state["reader_error"] is None, "worker stderr reader failed")
    _require(not stdout_state["overflow"], "worker stdout exceeds byte bound")
    _require(not stderr_state["overflow"], "worker stderr exceeds byte bound")
    stdout_bytes = bytes(stdout)
    stderr_bytes = bytes(stderr)
    _require(process.returncode == 0, "isolated worker process failed")
    _require(stderr_bytes == b"", "isolated worker emitted stderr")
    _require(stdout_bytes.endswith(b"\n") and stdout_bytes.count(b"\n") == 1, "worker stdout is not one JSON row")
    row = _parse_json(stdout_bytes[:-1], "worker stdout")
    _require(stdout_bytes == _canonical_bytes(row) + b"\n", "worker stdout is not canonical")
    _validate_worker_row(row)
    return row, stdout_bytes


def _cleanup_stage(stage_dir):
    stage_dir = Path(stage_dir)
    _validate_component_chain(stage_dir)
    entries = list(stage_dir.iterdir())
    _require(len(entries) == 1 and entries[0].name == "packet.json", "staging directory was mutated")
    metadata = _lstat_no_reparse(entries[0])
    _require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, "staged packet is invalid")
    entries[0].unlink()
    stage_dir.rmdir()


def evaluate_count_gates(rows):
    for row in rows:
        _require(row.get("split") in ("DESIGN", "VALIDATION_FEATURE_ONLY"), "count-gate split is invalid")
        eligible = row.get("challenger_stack_eligible")
        direction = row.get("challenger_stack_direction")
        _require(type(eligible) is bool, "count-gate eligibility must be bool")
        if eligible:
            _require(type(direction) is int and direction in (-1, 1), "count-gate direction must be exact int")
        else:
            _require(direction is None, "ineligible count-gate direction must be null")

    def one(split, minimum, maximum):
        eligible = [
            row
            for row in rows
            if row.get("split") == split and row.get("challenger_stack_eligible") is True
        ]
        long_count = sum(type(row.get("challenger_stack_direction")) is int and row.get("challenger_stack_direction") == 1 for row in eligible)
        short_count = sum(type(row.get("challenger_stack_direction")) is int and row.get("challenger_stack_direction") == -1 for row in eligible)
        status = (
            "PASS"
            if minimum <= len(eligible) <= maximum and long_count >= 50 and short_count >= 50
            else "PARK"
        )
        return {"total": len(eligible), "long": long_count, "short": short_count, "status": status}

    design = one("DESIGN", 522, 1302)
    validation = one("VALIDATION_FEATURE_ONLY", 209, 521)
    return {
        "design": design,
        "validation_feature_only": validation,
        "stage0_verdict": "PASS" if design["status"] == validation["status"] == "PASS" else "PARK",
    }


def _read_output_jsonl(path):
    try:
        return _parse_jsonl(_read_stable_regular_file(path), Path(path).name)
    except OSError as exc:
        raise InvalidEngineering("failed to read Stage-0 output") from exc


def reconcile_outputs(output_root, manifest_rows):
    output_root = Path(output_root)
    ledger_rows = _read_output_jsonl(output_root / "stage0_eligibility_ledger.jsonl")
    trace_rows = _read_output_jsonl(output_root / "stage0_access_trace.jsonl")
    _require(len(ledger_rows) == len(trace_rows) == len(manifest_rows), "exact-once row count mismatch")
    prior_prefix = EMPTY_PREFIX_SHA256
    seen_opportunities = set()
    for index, (ledger, trace, manifest) in enumerate(zip(ledger_rows, trace_rows, manifest_rows)):
        _require(ledger.get("schema_version") == LEDGER_SCHEMA, "ledger schema mismatch")
        _require(trace.get("schema_version") == TRACE_SCHEMA, "access trace schema mismatch")
        _require(ledger.get("row_index") == trace.get("row_index") == index, "row index mismatch")
        _require(ledger.get("opportunity_id") == manifest["opportunity_id"], "ledger opportunity order mismatch")
        _require(trace.get("opportunity_id") == manifest["opportunity_id"], "trace opportunity order mismatch")
        _require(ledger.get("packet_path") == trace.get("packet_path") == manifest["packet_path"], "packet path reconciliation mismatch")
        _require(ledger["opportunity_id"] not in seen_opportunities, "duplicate reconciled opportunity")
        seen_opportunities.add(ledger["opportunity_id"])
        _require(ledger.get("prior_prefix_sha256") == prior_prefix, "ledger prefix-chain prior mismatch")
        base = {
            key: value
            for key, value in ledger.items()
            if key not in ("row_payload_sha256", "next_prefix_sha256")
        }
        expected_row_sha = _sha256(_canonical_bytes(base))
        _require(ledger.get("row_payload_sha256") == expected_row_sha, "ledger row payload hash mismatch")
        expected_next = _next_prefix(prior_prefix, expected_row_sha)
        _require(ledger.get("next_prefix_sha256") == expected_next, "ledger prefix-chain next mismatch")
        _require(trace.get("prior_prefix_sha256") == prior_prefix, "trace prior prefix mismatch")
        _require(trace.get("next_prefix_sha256") == expected_next, "trace next prefix mismatch")
        _require(trace.get("worker_row_payload_sha256") == expected_row_sha, "trace/ledger row hash mismatch")
        _require(trace.get("worker_sha256") == EXPECTED_WORKER_SHA256, "trace worker hash mismatch")
        _require_sha256(trace.get("worker_stdout_sha256"), "trace worker stdout sha256")
        _require(trace.get("packet_file_sha256") == manifest["packet_file_sha256"], "trace packet hash mismatch")
        _require(trace.get("staged_packet_count") == 1, "staged packet count mismatch")
        _require(trace.get("fresh_isolated_process") is True, "fresh worker process proof missing")
        _require(trace.get("process_sequence_index") == index, "worker process sequence mismatch")
        _require(trace.get("cleanup_status") == "PASS", "temporary cleanup failed")
        prior_prefix = expected_next
    return {
        "schema_version": RECONCILIATION_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": PLAN_SHA256,
        "packet_count": len(manifest_rows),
        "ledger_row_count": len(ledger_rows),
        "access_trace_row_count": len(trace_rows),
        "final_prefix_sha256": prior_prefix,
        "exact_once_reconciliation": "PASS",
        "temporary_cleanup": "PASS",
    }


def _run_stage0(package_root, output_root, worker_path, frozen_root):
    validated = validate_source_package(package_root, frozen_root=frozen_root)
    output_root = _validate_output_disjointness(
        output_root,
        validated["root"],
        frozen_root,
    )
    worker_source, worker_sha256 = _load_trusted_worker(worker_path)
    try:
        _validate_component_chain(output_root.parent)
        output_root.mkdir(parents=False, exist_ok=False)
        _validate_component_chain(output_root)
        work_root = output_root / ".stage0_work"
        work_root.mkdir(exist_ok=False)
        _validate_component_chain(work_root)
        ledger_path = output_root / "stage0_eligibility_ledger.jsonl"
        trace_path = output_root / "stage0_access_trace.jsonl"
        with ledger_path.open("xb") as ledger_stream, trace_path.open("xb") as trace_stream:
            _validate_new_stream(ledger_path, ledger_stream)
            _validate_new_stream(trace_path, trace_stream)
            prior_prefix = EMPTY_PREFIX_SHA256
            for index, manifest in enumerate(validated["packet_manifest"]):
                relative = manifest["packet_path"]
                raw = validated["packet_bytes_by_path"][relative]
                stage_dir = work_root / f"{index:08d}"
                stage_dir.mkdir(exist_ok=False)
                _validate_component_chain(stage_dir)
                staged_packet = stage_dir / "packet.json"
                with staged_packet.open("xb") as staged_stream:
                    _validate_new_stream(staged_packet, staged_stream)
                    staged_stream.write(raw)
                    staged_stream.flush()
                    os.fsync(staged_stream.fileno())
                _require(_read_stable_regular_file(staged_packet) == raw, "staged packet readback mismatch")
                _require(
                    [entry.name for entry in stage_dir.iterdir()] == ["packet.json"],
                    "staging directory must contain exactly packet.json",
                )
                worker_row, worker_stdout = _run_worker(
                    worker_source,
                    worker_sha256,
                    stage_dir,
                    manifest["packet_file_sha256"],
                )
                for field in ("opportunity_id", "split", "packet_payload_sha256", "packet_file_sha256", "source_chain_sha256", "max_source_time_utc"):
                    expected = manifest[field] if field in manifest else None
                    _require(worker_row[field] == expected, f"worker/manifest {field} mismatch")
                ledger_row = _finalize_ledger_row(worker_row, index, relative, prior_prefix)
                _write_fsync(ledger_stream, ledger_row)
                _cleanup_stage(stage_dir)
                trace_row = {
                    "schema_version": TRACE_SCHEMA,
                    "hypothesis_id": HYPOTHESIS_ID,
                    "source_plan_sha256": PLAN_SHA256,
                    "row_index": index,
                    "process_sequence_index": index,
                    "opportunity_id": manifest["opportunity_id"],
                    "packet_path": relative,
                    "packet_file_sha256": manifest["packet_file_sha256"],
                    "worker_sha256": worker_sha256,
                    "worker_stdout_sha256": _sha256(worker_stdout),
                    "worker_row_payload_sha256": ledger_row["row_payload_sha256"],
                    "prior_prefix_sha256": prior_prefix,
                    "next_prefix_sha256": ledger_row["next_prefix_sha256"],
                    "staged_packet_count": 1,
                    "fresh_isolated_process": True,
                    "cleanup_status": "PASS",
                }
                _write_fsync(trace_stream, trace_row)
                prior_prefix = ledger_row["next_prefix_sha256"]
        _require(not any(work_root.iterdir()), "temporary work root is not empty")
        work_root.rmdir()

        reconciliation = reconcile_outputs(output_root, validated["packet_manifest"])
        _write_new_json(output_root / "stage0_reconciliation.json", reconciliation)
        ledger_rows = _read_output_jsonl(output_root / "stage0_eligibility_ledger.jsonl")
        gates = evaluate_count_gates(ledger_rows)
        _recheck_source_package(validated)
        receipt = {
            "schema_version": RECEIPT_SCHEMA,
            "hypothesis_id": HYPOTHESIS_ID,
            "source_plan_sha256": PLAN_SHA256,
            "engineering_status": "PASS",
            "stage0_verdict": gates["stage0_verdict"],
            "packet_count": len(validated["packet_manifest"]),
            "worker_process_count": len(validated["packet_manifest"]),
            "exact_once_reconciliation": "PASS",
            "temporary_cleanup": "PASS",
            "count_gates": gates,
            "source_manifest_sha256": validated["source_manifest_sha256"],
            "source_validation_receipt_sha256": validated["source_validation_receipt_sha256"],
            "decision_packet_manifest_sha256": validated["decision_packet_manifest_sha256"],
            "decision_packet_receipt_sha256": validated["decision_packet_receipt_sha256"],
            "packet_set_sha256": validated["packet_set_sha256"],
            "worker_sha256": worker_sha256,
            "eligibility_ledger_sha256": _sha256(_read_stable_regular_file(output_root / "stage0_eligibility_ledger.jsonl")),
            "access_trace_sha256": _sha256(_read_stable_regular_file(output_root / "stage0_access_trace.jsonl")),
            "reconciliation_sha256": _sha256(_read_stable_regular_file(output_root / "stage0_reconciliation.json")),
        }
        _write_new_json(output_root / "stage0_receipt.json", receipt)
        return receipt
    except InvalidEngineering:
        raise
    except Exception as exc:
        raise InvalidEngineering(f"Stage-0 lifecycle failed: {type(exc).__name__}") from exc


def run_stage0(package_root, output_root, *, worker_path, frozen_root):
    return _run_stage0(package_root, output_root, worker_path, frozen_root)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline supervisor for HYP-TRENDSTACK-EURUSD-H1-002 Stage 0")
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--frozen-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--worker",
        default=str(Path(__file__).with_name("stage0_trendstack_002_worker.py")),
    )
    args = parser.parse_args(argv)
    receipt = run_stage0(
        args.package_root,
        args.output_root,
        worker_path=args.worker,
        frozen_root=args.frozen_root,
    )
    sys.stdout.buffer.write(_canonical_bytes(receipt) + b"\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InvalidEngineering as exc:
        print(f"INVALID_ENGINEERING: {exc}", file=sys.stderr)
        raise SystemExit(2)
