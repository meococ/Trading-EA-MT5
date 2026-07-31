#!/usr/bin/env python3
"""Outcome-blind source and pre-event geometry audit for EventVolOCO HYP-001.

Importing this module is inert.  The production attempt is reachable only through
``main`` and remains fail-closed behind the immutable V2 plan, an independently
reviewed pre-source registry row, exact input hashes, and create-new outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import stat
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


HYPOTHESIS_ID = "HYP-EVENT-VOL-OCO-EURUSD-M1-001"
ATTEMPT_ID = "HYP001-SOURCE-PREFLIGHT-001"
EVIDENCE_CLASS = "OUTCOME_BLIND_SOURCE_AND_GEOMETRY_FEASIBILITY_ONLY"

V1_PLAN_REL = "03. EA Developer/EA_EventVolOCO/research/HYP-EVENT-VOL-OCO-EURUSD-M1-001_PROBE_PLAN.md"
V2_PLAN_REL = "03. EA Developer/EA_EventVolOCO/research/HYP-EVENT-VOL-OCO-EURUSD-M1-001_PROBE_PLAN_V2.md"
V1_PLAN_SHA256 = "AA940E556D741625AEBF219565B9667965D7D6F9122C9E790350A78AA6E3510A"
V2_PLAN_SHA256 = "D400DB0CCB93763D8F814D67BA31230DD0519E6A8981667703DFA47B48304058"

RAW_REL = "02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json"
RAW_SHA256 = "78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F"
NORMALIZED_REL = "02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv"
NORMALIZED_SHA256 = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
FOREX_MANIFEST_REL = "02. AlphaFactory/data/forexfactory/EURUSD/news_events/manifest.json"
FOREX_MANIFEST_SHA256 = "79C40AE0C7DFF7CF44539D00FD108E6D038648694EABD7AA44E234ACC00EF5B1"
DESIGN_MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl"
DESIGN_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
DESIGN_RECEIPT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json"
DESIGN_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
PUBLIC_DESIGN_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/DESIGN"
PUBLIC_M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
BUILDER_REL = "03. EA Developer/EA_EventVolOCO/research/build_event_vol_oco_001_source.py"
TEST_REL = "03. EA Developer/EA_EventVolOCO/research/tests/test_build_event_vol_oco_001_source.py"
INDEPENDENT_REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_EventVolOCO/research/"
    "HYP-EVENT-VOL-OCO-EURUSD-M1-001_INDEPENDENT_SOURCE_REVIEW_RECEIPT.json"
)
INDEPENDENT_REVIEW_SCHEMA = "event_vol_oco_independent_source_review.v1"

CLEAN_CSV_REL = "03. EA Developer/EA_EventVolOCO/research/source/clean_point_release_clocks_2019_2020.csv"
CLEAN_MANIFEST_REL = "03. EA Developer/EA_EventVolOCO/research/source/clean_point_release_clock_manifest.json"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_EventVolOCO/research/evidence/"
    "HYP-EVENT-VOL-OCO-EURUSD-M1-001_SOURCE_FEASIBILITY/"
    "HYP001-SOURCE-PREFLIGHT-001"
)

NORMALIZED_FIELDS = (
    "event_time_utc",
    "event_id",
    "currency",
    "impact",
    "event_name",
    "event_date_local",
    "source_week",
    "source_url",
)
OHLC_COLUMNS = ("time_utc", "open", "high", "low", "close")
TIME_ONLY_COLUMNS = ("time_utc",)
SEMANTIC_EXCLUSION = re.compile(
    r"speaks?|speech(?:es)?|testif(?:y|ies|ied)|testimony|press conferences?|hearings?",
    re.IGNORECASE,
)
FORBIDDEN_OUTPUT_KEY_PARTS = (
    "actual",
    "forecast",
    "previous",
    "return",
    "pnl",
    "profit_factor",
    "win_rate",
    "mfe",
    "mae",
    "trade_outcome",
)
FORBIDDEN_PATH_PARTS = {"private", "sealed", "validation", "holdout"}

DESIGN_START = datetime(2019, 1, 1, tzinfo=timezone.utc)
DESIGN_END = datetime(2021, 1, 1, tzinfo=timezone.utc)
EXPECTED_CLEAN_CLUSTERS = 319
EXPECTED_CLEAN_MEMBER_ROWS = 505
ELAPSED_WEEKS = 104.42857142857143
PIP_SIZE = 0.0001

LATER_ECONOMICS_MT5_MODEL = 4
LATER_ECONOMICS_MODEL_LABEL = "Every tick based on real ticks"
MODEL_ZERO_ALLOWED_FOR_LATER_ECONOMICS = False

ZERO_COUNTERS = {
    "post_t_price_values_read": 0,
    "future_ohlc_rows_read": 0,
    "outcome_fields_emitted": 0,
    "returns_computed": 0,
    "trades_simulated": 0,
    "performance_trials_executed": 0,
    "economics_executed": False,
    "model0_runs": 0,
    "model4_runs": 0,
    "mt5_launches": 0,
    "mql5_files_created": 0,
    "research_validation_opened": False,
    "research_holdout_opened": False,
    "paid_requests_made": 0,
    "network_calls": 0,
}


class ContractError(RuntimeError):
    """A fail-closed violation of the frozen source-only contract."""


class EventSourceIncomplete(ContractError):
    """An event-local minute/price completeness failure counted by the frozen gate."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _has_reparse_attribute(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_no_alias_in_existing_chain(path: Path) -> None:
    """Reject symlink/junction/reparse components, including ancestors above the root."""

    absolute = _absolute_lexical(path)
    for candidate in list(reversed(absolute.parents)) + [absolute]:
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink() or _has_reparse_attribute(candidate):
                raise ContractError(f"ancestor is a symlink or reparse point: {candidate}")


def _assert_lexical_and_resolved_containment(path: Path, root: Path) -> tuple[Path, Path]:
    absolute_path = _absolute_lexical(path)
    absolute_root = _absolute_lexical(root)
    _assert_no_alias_in_existing_chain(absolute_root)
    if not absolute_root.exists() or not absolute_root.is_dir():
        raise ContractError(f"exact root is missing or not a directory: {absolute_root}")
    try:
        relative = absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise ContractError(f"path is outside exact root: {absolute_path}") from exc
    _assert_no_alias_in_existing_chain(absolute_path)
    resolved_root = absolute_root.resolve(strict=True)
    nearest = absolute_path
    missing_tail: list[str] = []
    while not nearest.exists() and not nearest.is_symlink():
        missing_tail.append(nearest.name)
        if nearest.parent == nearest:
            raise ContractError(f"cannot resolve path containment: {absolute_path}")
        nearest = nearest.parent
    _assert_no_alias_in_existing_chain(nearest)
    resolved_candidate = nearest.resolve(strict=True)
    for part in reversed(missing_tail):
        resolved_candidate /= part
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ContractError(f"resolved path is outside exact root: {absolute_path}") from exc
    return absolute_path, relative


def assert_safe_directory(path: Path, *, exact_root: Path | None = None) -> Path:
    path = _absolute_lexical(path)
    root = path if exact_root is None else Path(exact_root)
    _assert_lexical_and_resolved_containment(path, root)
    if not path.exists() or not path.is_dir():
        raise ContractError(f"directory is missing or invalid: {path}")
    return path.resolve(strict=True)


def assert_safe_regular_file(path: Path, *, exact_root: Path | None = None) -> None:
    """Reject aliases, path escape, non-regular files, reparse points and hardlinks."""

    path = _absolute_lexical(path)
    if exact_root is not None:
        _, relative = _assert_lexical_and_resolved_containment(path, exact_root)
    else:
        _assert_no_alias_in_existing_chain(path)
        relative = None
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise ContractError(f"input file is missing: {path}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(f"input is not a regular file: {path}")
    if info.st_nlink != 1:
        raise ContractError(f"input must be a single-link file: {path}")
    if relative is not None:
        if any(part.lower() in FORBIDDEN_PATH_PARTS for part in relative.parts):
            raise ContractError(f"forbidden custody token in public path: {relative}")


def verify_file_sha256(path: Path, expected_sha256: str, *, exact_root: Path | None = None) -> str:
    assert_safe_regular_file(path, exact_root=exact_root)
    actual = sha256_file(path)
    if actual != expected_sha256.upper():
        raise ContractError(f"SHA256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    return actual


def read_safe_bytes_once(path: Path, *, exact_root: Path) -> bytes:
    assert_safe_regular_file(path, exact_root=exact_root)
    with Path(path).open("rb") as handle:
        return handle.read()


def read_bytes_verified_sha256(path: Path, expected_sha256: str, *, exact_root: Path | None = None) -> bytes:
    if exact_root is None:
        raise ContractError("exact_root is required for authority reads")
    payload = read_safe_bytes_once(path, exact_root=exact_root)
    actual = sha256_bytes(payload)
    if actual != expected_sha256.upper():
        raise ContractError(f"SHA256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    return payload


def read_authority_blobs(
    workspace_root: Path,
    specs: Mapping[str, tuple[str, str]],
    *,
    reader: Callable[..., bytes] = read_safe_bytes_once,
) -> dict[str, bytes]:
    """Read each named authority exactly once, then hash the exact returned bytes."""

    root = assert_safe_directory(workspace_root)
    payloads: dict[str, bytes] = {}
    for name, (relative, expected_sha256) in specs.items():
        path = root / relative
        payload = reader(path, exact_root=root)
        actual = sha256_bytes(payload)
        if actual != expected_sha256.upper():
            raise ContractError(f"SHA256 mismatch for {path}: expected {expected_sha256}, got {actual}")
        payloads[name] = payload
    return payloads


def load_json_bytes(payload: bytes, path: Path) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid JSON authority payload: {path}") from exc


def load_jsonl_bytes(payload: bytes, path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = payload.decode("utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ContractError(f"blank JSONL line at {path}:{number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContractError(f"invalid JSONL at {path}:{number}") from exc
        if not isinstance(row, dict):
            raise ContractError(f"non-object JSONL row at {path}:{number}")
        rows.append(row)
    if text and not text.endswith("\n"):
        raise ContractError(f"JSONL authority payload must end with newline: {path}")
    return rows


def load_normalized_csv_bytes(payload: bytes, path: Path) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig")
    stream = io.StringIO(text, newline="")
    reader = csv.DictReader(stream)
    if tuple(reader.fieldnames or ()) != NORMALIZED_FIELDS:
        raise ContractError(f"normalized CSV header mismatch: {path}: {reader.fieldnames}")
    return [dict(row) for row in reader]


def assert_safe_output_path(
    path: Path,
    *,
    workspace_root: Path | None = None,
    exact_root: Path | None = None,
) -> None:
    if exact_root is not None and workspace_root is not None:
        if _absolute_lexical(exact_root) != _absolute_lexical(workspace_root):
            raise ContractError("conflicting output containment roots")
    root = exact_root if exact_root is not None else workspace_root
    if root is None:
        raise ContractError("exact output root is required")
    _assert_lexical_and_resolved_containment(path, root)


def create_directory_create_new(path: Path, *, workspace_root: Path) -> None:
    assert_safe_output_path(path, workspace_root=workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert_safe_output_path(path, workspace_root=workspace_root)
    try:
        path.mkdir()
    except FileExistsError as exc:
        raise ContractError(f"output conflict; refusing existing directory: {path}") from exc
    if path.is_symlink() or _has_reparse_attribute(path):
        raise ContractError(f"created output directory is a symlink or reparse point: {path}")


def write_bytes_create_new(path: Path, payload: bytes, *, workspace_root: Path | None = None) -> None:
    if workspace_root is not None:
        assert_safe_output_path(path, workspace_root=workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if workspace_root is not None:
        assert_safe_output_path(path, workspace_root=workspace_root)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ContractError(f"output conflict; refusing overwrite: {path}") from exc


def write_json_create_new(path: Path, value: Any, *, workspace_root: Path | None = None) -> None:
    write_bytes_create_new(path, canonical_json_bytes(value), workspace_root=workspace_root)


def write_jsonl_create_new(path: Path, rows: Iterable[Mapping[str, Any]], *, workspace_root: Path | None = None) -> None:
    payload = b"".join(canonical_json_bytes(row) for row in rows)
    write_bytes_create_new(path, payload, workspace_root=workspace_root)


def _parse_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif hasattr(value, "to_pydatetime"):
        parsed = value.to_pydatetime()
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ContractError(f"invalid UTC timestamp: {value}") from exc
    else:
        raise ContractError(f"unsupported timestamp type: {type(value).__name__}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    if parsed.second != 0 or parsed.microsecond != 0:
        raise ContractError(f"timestamp is not minute aligned: {parsed.isoformat()}")
    return parsed


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_local_gmt7(local_date: str, local_time: str, declared_timezone: str) -> datetime:
    if declared_timezone != "GMT+7":
        raise ContractError(f"unexpected calendar timezone: {declared_timezone!r}")
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*", local_time)
    if not match:
        raise ContractError(f"untimed or invalid local event clock: {local_time!r}")
    hour = int(match.group(1))
    minute = int(match.group(2))
    if not 1 <= hour <= 12 or not 0 <= minute <= 59:
        raise ContractError(f"invalid local event clock: {local_time!r}")
    if match.group(3).lower() == "am":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12
    try:
        local_day = date.fromisoformat(local_date)
    except ValueError as exc:
        raise ContractError(f"invalid local event date: {local_date!r}") from exc
    local_dt = datetime.combine(local_day, time(hour, minute), timezone(timedelta(hours=7)))
    return local_dt.astimezone(timezone.utc)


def _require_exact_keys(row: Mapping[str, Any], expected: Sequence[str], label: str) -> None:
    actual = set(row)
    wanted = set(expected)
    if actual != wanted:
        raise ContractError(f"{label} schema mismatch: missing={sorted(wanted-actual)} extra={sorted(actual-wanted)}")


def assert_no_forbidden_output_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in FORBIDDEN_OUTPUT_KEY_PARTS):
                if key in ZERO_COUNTERS:
                    expected = ZERO_COUNTERS[key]
                    if child != expected or type(child) is not type(expected):
                        raise ContractError(f"forbidden outcome counter is nonzero or mistyped: {key}")
                    continue
                raise ContractError(f"forbidden output field: {key}")
            assert_no_forbidden_output_fields(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            assert_no_forbidden_output_fields(child)


def build_clean_clocks(
    raw_document: Mapping[str, Any],
    normalized_rows: Sequence[Mapping[str, str]],
    *,
    start: datetime = DESIGN_START,
    end: datetime = DESIGN_END,
    expected_clusters: int | None = EXPECTED_CLEAN_CLUSTERS,
    expected_member_rows: int | None = EXPECTED_CLEAN_MEMBER_ROWS,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    raw_rows = raw_document.get("events")
    if not isinstance(raw_rows, list):
        raise ContractError("raw JSON must contain an events list")

    raw_by_id: dict[str, Mapping[str, Any]] = {}
    for raw in raw_rows:
        if not isinstance(raw, Mapping):
            raise ContractError("raw event is not an object")
        event_id = str(raw.get("event_id", ""))
        if not event_id:
            raise ContractError("raw event_id is empty")
        if event_id in raw_by_id:
            raise ContractError(f"duplicate raw event_id: {event_id}")
        raw_by_id[event_id] = raw

    normalized_by_id: dict[str, Mapping[str, str]] = {}
    reconciled: list[dict[str, Any]] = []
    for row in normalized_rows:
        _require_exact_keys(row, NORMALIZED_FIELDS, "normalized CSV")
        event_id = row["event_id"]
        if event_id in normalized_by_id:
            raise ContractError(f"duplicate normalized event_id: {event_id}")
        normalized_by_id[event_id] = row
        raw = raw_by_id.get(event_id)
        if raw is None:
            raise ContractError(f"normalized event_id missing from raw source: {event_id}")
        mismatches = [field for field in NORMALIZED_FIELDS if str(raw.get(field, "")) != str(row[field])]
        if mismatches:
            raise ContractError(f"normalized/raw mismatch for {event_id}: {','.join(mismatches)}")
        recomputed = _parse_local_gmt7(
            str(raw.get("event_date_local", "")),
            str(raw.get("time_local_text", "")),
            str(raw.get("timezone", "")),
        )
        raw_utc = _parse_utc(raw["event_time_utc"])
        normalized_utc = _parse_utc(row["event_time_utc"])
        if recomputed != raw_utc or raw_utc != normalized_utc:
            raise ContractError(f"GMT+7 UTC reconciliation failed for {event_id}")
        reconciled.append(
            {
                "event_time": raw_utc,
                "event_id": event_id,
                "currency": row["currency"],
                "impact": row["impact"],
                "event_name": row["event_name"],
                "source_week": row["source_week"],
                "source_url": row["source_url"],
            }
        )

    if set(raw_by_id) != set(normalized_by_id):
        missing = sorted(set(raw_by_id) - set(normalized_by_id))
        raise ContractError(f"raw event_ids missing from normalized CSV: {missing[:5]}")

    grouped: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for row in reconciled:
        grouped[row["event_time"]].append(row)

    window_groups: list[tuple[datetime, list[dict[str, Any]]]] = []
    for event_time, members in grouped.items():
        if not start <= event_time < end:
            continue
        if any(member["currency"] not in {"EUR", "USD"} for member in members):
            continue
        if any(member["impact"] != "High Impact Expected" for member in members):
            continue
        window_groups.append((event_time, members))

    clean_groups: list[tuple[datetime, list[dict[str, Any]]]] = []
    excluded = 0
    for event_time, members in window_groups:
        if any(SEMANTIC_EXCLUSION.search(member["event_name"]) for member in members):
            excluded += 1
            continue
        clean_groups.append((event_time, sorted(members, key=lambda item: item["event_id"])))
    clean_groups.sort(key=lambda item: item[0])

    clocks: list[dict[str, Any]] = []
    for index, (event_time, members) in enumerate(clean_groups, start=1):
        clocks.append(
            {
                "event_clock_id": f"EVOCO{index:04d}",
                "event_time_utc": _iso_utc(event_time),
                "currencies": "|".join(sorted({member["currency"] for member in members})),
                "event_ids": "|".join(member["event_id"] for member in members),
                "event_names": "|".join(member["event_name"] for member in members),
                "source_weeks": "|".join(sorted({member["source_week"] for member in members})),
                "source_urls": "|".join(sorted({member["source_url"] for member in members})),
                "all_member_clean": True,
            }
        )

    stats = {
        "raw_event_count": len(raw_rows),
        "normalized_event_count": len(normalized_rows),
        "all_cluster_count": len(grouped),
        "window_cluster_count": len(window_groups),
        "semantic_excluded_cluster_count": excluded,
        "clean_cluster_count": len(clocks),
        "clean_member_row_count": sum(len(members) for _, members in clean_groups),
    }
    if expected_clusters is not None and stats["clean_cluster_count"] != expected_clusters:
        raise ContractError(
            f"clean cluster cardinality mismatch: expected {expected_clusters}, got {stats['clean_cluster_count']}"
        )
    if expected_member_rows is not None and stats["clean_member_row_count"] != expected_member_rows:
        raise ContractError(
            "clean member row cardinality mismatch: "
            f"expected {expected_member_rows}, got {stats['clean_member_row_count']}"
        )
    assert_no_forbidden_output_fields(clocks)
    return clocks, stats


def clean_clock_csv_bytes(clocks: Sequence[Mapping[str, Any]]) -> bytes:
    fields = (
        "event_clock_id",
        "event_time_utc",
        "currencies",
        "event_ids",
        "event_names",
        "source_weeks",
        "source_urls",
        "all_member_clean",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in clocks:
        writer.writerow({field: row[field] for field in fields})
    return stream.getvalue().encode("utf-8")


def _index_exact_minutes(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
    expected_start: datetime,
    expected_end: datetime,
    label: str,
) -> dict[datetime, Mapping[str, Any]]:
    indexed: dict[datetime, Mapping[str, Any]] = {}
    expected_keys = set(columns)
    for row in rows:
        if set(row) != expected_keys:
            extra = sorted(set(row) - expected_keys)
            missing = sorted(expected_keys - set(row))
            if label == "post-T":
                raise ContractError(f"post-T projection returned forbidden or missing fields: extra={extra} missing={missing}")
            raise ContractError(f"{label} projection schema mismatch: extra={extra} missing={missing}")
        stamp = _parse_utc(row["time_utc"])
        if stamp in indexed:
            raise EventSourceIncomplete(f"duplicate {label} timestamp: {_iso_utc(stamp)}")
        indexed[stamp] = row
    expected_count = int((expected_end - expected_start).total_seconds() // 60) + 1
    expected = {expected_start + timedelta(minutes=offset) for offset in range(expected_count)}
    if set(indexed) != expected:
        raise EventSourceIncomplete(
            f"{label} timestamp coverage mismatch: expected={len(expected)} observed={len(indexed)}"
        )
    return indexed


def _finite_price(row: Mapping[str, Any], key: str, label: str) -> float:
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventSourceIncomplete(f"non-numeric {label}.{key}")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise EventSourceIncomplete(f"invalid {label}.{key}")
    return value


def _validate_ohlc_order(row: Mapping[str, Any], label: str) -> tuple[float, float, float, float]:
    open_ = _finite_price(row, "open", label)
    high = _finite_price(row, "high", label)
    low = _finite_price(row, "low", label)
    close = _finite_price(row, "close", label)
    if high < max(open_, close) or low > min(open_, close) or high < low:
        raise EventSourceIncomplete(f"invalid {label} OHLC ordering")
    return open_, high, low, close


def compute_pre_event_geometry(
    event_time: datetime,
    read_range: Callable[[datetime, datetime, tuple[str, ...]], Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    event_time = _parse_utc(event_time)
    hour_floor = event_time.replace(minute=0)
    h1_start = hour_floor - timedelta(hours=21)
    h1_end = hour_floor - timedelta(minutes=1)
    box_start = event_time - timedelta(minutes=16)
    box_end = event_time - timedelta(minutes=2)

    h1_rows = read_range(h1_start, h1_end, OHLC_COLUMNS)
    h1_index = _index_exact_minutes(h1_rows, OHLC_COLUMNS, h1_start, h1_end, "H1")
    box_rows = read_range(box_start, box_end, OHLC_COLUMNS)
    box_index = _index_exact_minutes(box_rows, OHLC_COLUMNS, box_start, box_end, "box")
    arm_rows = read_range(event_time - timedelta(minutes=1), event_time - timedelta(minutes=1), TIME_ONLY_COLUMNS)
    _index_exact_minutes(
        arm_rows,
        TIME_ONLY_COLUMNS,
        event_time - timedelta(minutes=1),
        event_time - timedelta(minutes=1),
        "arming",
    )
    post_rows = read_range(event_time, event_time + timedelta(minutes=30), TIME_ONLY_COLUMNS)
    _index_exact_minutes(post_rows, TIME_ONLY_COLUMNS, event_time, event_time + timedelta(minutes=30), "post-T")

    h1_bars: list[dict[str, float]] = []
    for bucket_index in range(21):
        bucket_start = h1_start + timedelta(hours=bucket_index)
        minute_rows = [h1_index[bucket_start + timedelta(minutes=offset)] for offset in range(60)]
        ordered = [_validate_ohlc_order(row, "H1") for row in minute_rows]
        opens = [item[0] for item in ordered]
        highs = [item[1] for item in ordered]
        lows = [item[2] for item in ordered]
        closes = [item[3] for item in ordered]
        h1_bars.append({"open": opens[0], "high": max(highs), "low": min(lows), "close": closes[-1]})

    true_ranges: list[float] = []
    for index in range(1, 21):
        bar = h1_bars[index]
        previous_close = h1_bars[index - 1]["close"]
        true_ranges.append(
            max(
                bar["high"] - bar["low"],
                abs(bar["high"] - previous_close),
                abs(bar["low"] - previous_close),
            )
        )
    atr20_pips = sum(true_ranges) / len(true_ranges) / PIP_SIZE

    box_ordered = [_validate_ohlc_order(row, "box") for row in box_index.values()]
    box_high = max(item[1] for item in box_ordered)
    box_low = min(item[2] for item in box_ordered)
    if box_high <= box_low:
        raise EventSourceIncomplete("non-positive pre-event box width")
    box_width_pips = (box_high - box_low) / PIP_SIZE
    buffer_pips = max(2.0, 0.05 * atr20_pips)
    planned_risk_pips = box_width_pips + 2.0 * buffer_pips
    return {
        "event_time_utc": _iso_utc(event_time),
        "box_width_pips": round(box_width_pips, 10),
        "atr20_pips": round(atr20_pips, 10),
        "buffer_pips": round(buffer_pips, 10),
        "planned_risk_pips": round(planned_risk_pips, 10),
        "timestamp_coverage_complete": True,
        "h1_complete_bucket_count": 21,
        "box_complete_minute_count": 15,
        "arming_timestamp_count": 1,
        "post_t_time_only_timestamp_count": 31,
    }


def greedy_primary_schedule(event_times: Sequence[datetime]) -> tuple[list[datetime], list[datetime]]:
    selected: list[datetime] = []
    skipped: list[datetime] = []
    reserved_until: datetime | None = None
    for event_time in sorted({_parse_utc(value) for value in event_times}):
        arm = event_time - timedelta(minutes=1)
        if reserved_until is not None and arm <= reserved_until:
            skipped.append(event_time)
            continue
        selected.append(event_time)
        reserved_until = event_time + timedelta(minutes=30)
    return selected, skipped


def match_controls(
    primary_times: Sequence[datetime],
    all_clean_times: Sequence[datetime],
    feasible_control_times: set[datetime],
) -> tuple[list[tuple[datetime, datetime]], list[dict[str, str]]]:
    clean = sorted({_parse_utc(value) for value in all_clean_times})
    feasible = {_parse_utc(value) for value in feasible_control_times}
    pairs: list[tuple[datetime, datetime]] = []
    rejected: list[dict[str, str]] = []
    for primary in sorted({_parse_utc(value) for value in primary_times}):
        control = primary - timedelta(days=7)
        contamination = any(abs(candidate - control) <= timedelta(hours=2) for candidate in clean)
        if contamination:
            rejected.append({"event_time_utc": _iso_utc(primary), "reason": "control_contaminated_by_clean_event"})
        elif control not in feasible:
            rejected.append({"event_time_utc": _iso_utc(primary), "reason": "control_source_incomplete"})
        else:
            pairs.append((primary, control))
    return pairs, rejected


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ContractError("planned-risk population is empty")
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) or value <= 0 for value in ordered):
        raise ContractError("planned-risk population contains invalid values")
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def evaluate_source_gates(
    *,
    observed_clean_clusters: int,
    complete_clean_clusters: int,
    matched_pair_count: int,
    primary_risks_pips: Sequence[float],
    elapsed_weeks: float = ELAPSED_WEEKS,
) -> dict[str, Any]:
    if observed_clean_clusters <= 0 or elapsed_weeks <= 0:
        raise ContractError("invalid source gate denominator")
    clean_cadence = observed_clean_clusters / elapsed_weeks
    pair_cadence = matched_pair_count / elapsed_weeks
    median = _percentile(primary_risks_pips, 0.5)
    p25 = _percentile(primary_risks_pips, 0.25)
    cost_ratio = 6.0 / median
    required_complete = math.ceil(0.99 * observed_clean_clusters)
    gates = {
        "clean_cadence_2_to_5": 2.0 <= clean_cadence <= 5.0,
        "history_complete_99pct": complete_clean_clusters >= required_complete,
        "matched_pairs_gte_209": matched_pair_count >= 209,
        "pair_cadence_2_to_5": 2.0 <= pair_cadence <= 5.0,
        "median_planned_risk_gte_8": median >= 8.0,
        "p25_planned_risk_gte_5": p25 >= 5.0,
        "six_pip_to_median_lte_0_75": cost_ratio <= 0.75,
    }
    return {
        "elapsed_calendar_weeks": elapsed_weeks,
        "clean_cadence_per_week": clean_cadence,
        "required_complete_clean_clusters": required_complete,
        "pair_cadence_per_week": pair_cadence,
        "median_planned_risk_pips": median,
        "p25_planned_risk_pips": p25,
        "six_pip_to_median_planned_risk_ratio": cost_ratio,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
    }


def validate_design_receipt(receipt: Mapping[str, Any]) -> None:
    source_sha = receipt.get("source_sha256", receipt.get("m1_source_sha256"))
    if source_sha != PUBLIC_M1_SOURCE_SHA256:
        raise ContractError("public DESIGN receipt source SHA mismatch")
    if receipt.get("research_validation_opened") is not False:
        raise ContractError("research validation is not sealed")
    if receipt.get("research_holdout_opened") is not False:
        raise ContractError("research holdout is not sealed")
    if "design_manifest_sha256" in receipt and receipt["design_manifest_sha256"] != DESIGN_MANIFEST_SHA256:
        raise ContractError("public DESIGN receipt manifest SHA mismatch")


def validate_forex_manifest(manifest: Mapping[str, Any]) -> None:
    limitations = manifest.get("limitations")
    expected_limitations = [
        "Third-party impact ranking and timestamps are not an official release ledger.",
        "24 untimed EUR/USD rows and 63 global rows remain audit-only.",
        "This dataset cannot satisfy execution-cost provenance or promotion gates.",
    ]
    checks = [
        manifest.get("source_rank") == "C",
        manifest.get("promotion_eligible") is False,
        manifest.get("local_event_date_coverage") == {"from": "2019-01-01", "to": "2022-12-31"},
        manifest.get("raw", {}).get("path") == RAW_REL,
        manifest.get("raw", {}).get("sha256") == RAW_SHA256,
        manifest.get("normalized_csv", {}).get("path") == NORMALIZED_REL,
        manifest.get("normalized_csv", {}).get("sha256") == NORMALIZED_SHA256,
        limitations == expected_limitations,
    ]
    if not all(checks):
        raise ContractError("Forex Factory manifest contract mismatch")


def _load_single_registry_row(registry_payload: bytes, registry_path: Path) -> dict[str, Any]:
    matches = [
        row
        for row in load_jsonl_bytes(registry_payload, registry_path)
        if row.get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if len(matches) != 1:
        raise ContractError(f"registry must contain exactly one pre-source row; found {len(matches)}")
    return matches[0]


def _validate_pre_source_registry_row(row: Mapping[str, Any]) -> None:
    validation = row.get("validation", {})
    if row.get("prereg_path") != V2_PLAN_REL or row.get("prereg_sha256") != V2_PLAN_SHA256:
        raise ContractError("registry does not bind immutable V2 plan")
    provenance_text = canonical_json_bytes(row).decode("utf-8")
    if V1_PLAN_SHA256 not in provenance_text:
        raise ContractError("registry does not bind superseded immutable V1 plan SHA")
    if row.get("source_path") is not None or row.get("source_hash") is not None or row.get("model") is not None:
        raise ContractError("pre-source registry row must keep source_path/source_hash/model null")
    if validation.get("independent_pre_run_review_status") != "PASS":
        raise ContractError("independent pre-run review is not PASS in registry")
    if validation.get("source_run_authorized") is not True:
        raise ContractError("registry does not authorize the one source run")
    if validation.get("performance_metrics_authorized") is not False:
        raise ContractError("registry improperly authorizes performance metrics")
    if row.get("verdict") != "FROZEN_SOURCE_FEASIBILITY_RUN_AUTHORIZED_AFTER_INDEPENDENT_REVIEW":
        raise ContractError("registry pre-source verdict mismatch")


def validate_code_review_authority(
    workspace_root: Path,
    *,
    builder_rel: str = BUILDER_REL,
    test_rel: str = TEST_REL,
    registry_rel: str = REGISTRY_REL,
    receipt_rel: str = INDEPENDENT_REVIEW_RECEIPT_REL,
    reader: Callable[..., bytes] = read_safe_bytes_once,
    executing_builder_path: Path | None = None,
) -> dict[str, Any]:
    workspace_root = assert_safe_directory(workspace_root)
    builder_path = workspace_root / builder_rel
    test_path = workspace_root / test_rel
    registry_path = workspace_root / registry_rel
    receipt_path = workspace_root / receipt_rel
    if executing_builder_path is not None:
        assert_safe_regular_file(executing_builder_path, exact_root=workspace_root)
        if _absolute_lexical(executing_builder_path) != _absolute_lexical(builder_path):
            raise ContractError("executing builder path does not match reviewed builder path")
    builder_payload = reader(builder_path, exact_root=workspace_root)
    builder_sha256 = sha256_bytes(builder_payload)
    test_payload = reader(test_path, exact_root=workspace_root)
    test_sha256 = sha256_bytes(test_payload)
    registry_payload = reader(registry_path, exact_root=workspace_root)
    registry_row = _load_single_registry_row(registry_payload, registry_path)
    _validate_pre_source_registry_row(registry_row)
    validation = registry_row.get("validation", {})
    if validation.get("reviewed_builder_path") != builder_rel:
        raise ContractError("registry reviewed builder path mismatch")
    if validation.get("reviewed_builder_sha256") != builder_sha256:
        raise ContractError("registry reviewed builder SHA mismatch")
    if validation.get("reviewed_test_path") != test_rel:
        raise ContractError("registry reviewed test path mismatch")
    if validation.get("reviewed_test_sha256") != test_sha256:
        raise ContractError("registry reviewed test SHA mismatch")
    if validation.get("independent_review_receipt_path") != receipt_rel:
        raise ContractError("registry independent review receipt path mismatch")
    receipt_payload = reader(receipt_path, exact_root=workspace_root)
    receipt_sha256 = sha256_bytes(receipt_payload)
    if validation.get("independent_review_receipt_sha256") != receipt_sha256:
        raise ContractError("registry independent review receipt SHA mismatch")
    receipt = load_json_bytes(receipt_payload, receipt_path)
    if receipt.get("schema_version") != INDEPENDENT_REVIEW_SCHEMA:
        raise ContractError("independent review receipt schema mismatch")
    if receipt.get("hypothesis_id") != HYPOTHESIS_ID or receipt.get("review_status") != "PASS":
        raise ContractError("independent review receipt is not PASS for this hypothesis")
    if receipt.get("reviewed_builder") != {"path": builder_rel, "sha256": builder_sha256}:
        raise ContractError("independent review receipt reviewed builder SHA mismatch")
    if receipt.get("reviewed_tests") != {"path": test_rel, "sha256": test_sha256}:
        raise ContractError("independent review receipt reviewed test SHA mismatch")
    if receipt.get("v1_plan") != {"path": V1_PLAN_REL, "sha256": V1_PLAN_SHA256}:
        raise ContractError("independent review receipt V1 plan mismatch")
    if receipt.get("v2_plan") != {"path": V2_PLAN_REL, "sha256": V2_PLAN_SHA256}:
        raise ContractError("independent review receipt V2 plan mismatch")
    permissions = receipt.get("permissions", {})
    if permissions.get("source_feasibility_run") is not True:
        raise ContractError("independent review receipt does not authorize source feasibility")
    if permissions.get("performance_or_economics") is not False:
        raise ContractError("independent review receipt improperly authorizes economics")
    if permissions.get("mt5_or_mql5") is not False:
        raise ContractError("independent review receipt improperly authorizes MT5/MQL5")
    return {
        "builder_path": builder_rel,
        "builder_sha256": builder_sha256,
        "test_path": test_rel,
        "test_sha256": test_sha256,
        "independent_review_receipt_path": receipt_rel,
        "independent_review_receipt_sha256": receipt_sha256,
        "registry_row": registry_row,
    }


def review_binding_fields(binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "builder_path": binding["builder_path"],
        "builder_sha256": binding["builder_sha256"],
        "test_path": binding["test_path"],
        "test_sha256": binding["test_sha256"],
        "independent_review_receipt_path": binding["independent_review_receipt_path"],
        "independent_review_receipt_sha256": binding["independent_review_receipt_sha256"],
    }


def make_attempt_started_payload(registry_row: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "state": "STARTED",
        "evidence_class": EVIDENCE_CLASS,
        "v1_plan_sha256": V1_PLAN_SHA256,
        "v2_plan_sha256": V2_PLAN_SHA256,
        "registry_verdict": registry_row["verdict"],
        "later_economics_mt5_model": LATER_ECONOMICS_MT5_MODEL,
        "later_economics_model_label": LATER_ECONOMICS_MODEL_LABEL,
        "model_zero_allowed_for_later_economics": MODEL_ZERO_ALLOWED_FOR_LATER_ECONOMICS,
        **review_binding_fields(binding),
        "metrics": dict(ZERO_COUNTERS),
    }


def validate_pre_source_registry(workspace_root: Path) -> dict[str, Any]:
    return validate_code_review_authority(workspace_root)["registry_row"]


class PublicDesignReader:
    """Hash-verifying, projection-limited reader for exact public DESIGN shards."""

    def __init__(self, design_root: Path, manifest_rows: Sequence[Mapping[str, Any]]) -> None:
        self.design_root = assert_safe_directory(design_root)
        self.by_date: dict[date, Mapping[str, Any]] = {}
        self._byte_cache: dict[Path, bytes] = {}
        self._projection_cache: dict[tuple[date, tuple[str, ...]], list[dict[str, Any]]] = {}
        for row in manifest_rows:
            required = {"bytes", "date", "relative_path", "rows", "sha256"}
            if set(row) != required:
                raise ContractError("public DESIGN manifest row schema mismatch")
            shard_date = date.fromisoformat(str(row["date"]))
            if shard_date in self.by_date:
                raise ContractError(f"duplicate public DESIGN manifest date: {shard_date}")
            expected_rel = f"public/DESIGN/{shard_date.isoformat()}/m1.parquet"
            if row["relative_path"] != expected_rel:
                raise ContractError(f"public DESIGN manifest path mismatch for {shard_date}")
            self.by_date[shard_date] = row

    def _load_projection(self, shard_date: date, columns: tuple[str, ...]) -> list[dict[str, Any]]:
        key = (shard_date, columns)
        if key in self._projection_cache:
            return self._projection_cache[key]
        row = self.by_date.get(shard_date)
        if row is None:
            return []
        path = self.design_root / shard_date.isoformat() / "m1.parquet"
        assert_safe_regular_file(path, exact_root=self.design_root)
        payload = self._byte_cache.get(path)
        if payload is None:
            payload = read_safe_bytes_once(path, exact_root=self.design_root)
            if len(payload) != int(row["bytes"]):
                raise ContractError(f"public DESIGN shard byte-count mismatch: {path}")
            if sha256_bytes(payload) != str(row["sha256"]).upper():
                raise ContractError(f"public DESIGN shard SHA mismatch: {path}")
            self._byte_cache[path] = payload
        try:
            import pyarrow.parquet as parquet
        except ImportError as exc:
            raise ContractError("pyarrow is required for the public DESIGN projection") from exc
        table = parquet.read_table(io.BytesIO(payload), columns=list(columns))
        if table.num_rows != int(row["rows"]):
            raise ContractError(f"public DESIGN shard row-count mismatch: {path}")
        projected = [dict(item) for item in table.to_pylist()]
        self._projection_cache[key] = projected
        return projected

    def read_range(self, start: datetime, end: datetime, columns: tuple[str, ...]) -> list[dict[str, Any]]:
        start = _parse_utc(start)
        end = _parse_utc(end)
        if start > end:
            raise ContractError("invalid public DESIGN read range")
        if columns not in {OHLC_COLUMNS, TIME_ONLY_COLUMNS}:
            raise ContractError(f"forbidden public DESIGN projection: {columns}")
        if columns == OHLC_COLUMNS and end >= DESIGN_END + timedelta(days=1):
            raise ContractError("price projection exceeds frozen source scope")
        rows: list[dict[str, Any]] = []
        candidate = start.date() - timedelta(days=2)
        last = end.date() + timedelta(days=2)
        while candidate <= last:
            for row in self._load_projection(candidate, columns):
                stamp = _parse_utc(row["time_utc"])
                if start <= stamp <= end:
                    row["time_utc"] = stamp
                    rows.append(row)
            candidate += timedelta(days=1)
        rows.sort(key=lambda row: row["time_utc"])
        return rows


def execute_with_terminal_guard(
    output_root: Path,
    work: Callable[[], Any],
    *,
    started_payload: Mapping[str, Any] | None = None,
    workspace_root: Path | None = None,
) -> Any:
    output_root = Path(output_root)
    if workspace_root is None:
        output_root.mkdir(parents=True, exist_ok=True)
    elif not output_root.exists():
        create_directory_create_new(output_root, workspace_root=workspace_root)
    else:
        assert_safe_output_path(output_root, workspace_root=workspace_root)
    started_path = output_root / "attempt_started.json"
    terminal_path = output_root / "attempt_terminal.json"
    if started_path.exists() or terminal_path.exists():
        raise ContractError("output conflict in attempt lifecycle")
    started = dict(
        started_payload
        or {
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "evidence_class": EVIDENCE_CLASS,
            "state": "STARTED",
            "metrics": dict(ZERO_COUNTERS),
        }
    )
    write_json_create_new(started_path, started, workspace_root=workspace_root)
    try:
        return work()
    except Exception as exc:
        if not terminal_path.exists():
            write_json_create_new(
                terminal_path,
                {
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "engineering_status": "ERROR",
                    "market_verdict": None,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "metrics": dict(ZERO_COUNTERS),
                },
                workspace_root=workspace_root,
            )
        raise


def _workspace_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def _validate_authority_files(workspace_root: Path) -> dict[str, Any]:
    specs = {
        V1_PLAN_REL: (V1_PLAN_REL, V1_PLAN_SHA256),
        V2_PLAN_REL: (V2_PLAN_REL, V2_PLAN_SHA256),
        RAW_REL: (RAW_REL, RAW_SHA256),
        NORMALIZED_REL: (NORMALIZED_REL, NORMALIZED_SHA256),
        FOREX_MANIFEST_REL: (FOREX_MANIFEST_REL, FOREX_MANIFEST_SHA256),
        DESIGN_MANIFEST_REL: (DESIGN_MANIFEST_REL, DESIGN_MANIFEST_SHA256),
        DESIGN_RECEIPT_REL: (DESIGN_RECEIPT_REL, DESIGN_RECEIPT_SHA256),
    }
    payloads = read_authority_blobs(workspace_root, specs)
    forex_manifest = load_json_bytes(payloads[FOREX_MANIFEST_REL], workspace_root / FOREX_MANIFEST_REL)
    validate_forex_manifest(forex_manifest)
    design_receipt = load_json_bytes(payloads[DESIGN_RECEIPT_REL], workspace_root / DESIGN_RECEIPT_REL)
    validate_design_receipt(design_receipt)
    return {
        "forex_manifest": forex_manifest,
        "design_receipt": design_receipt,
        "raw_document": load_json_bytes(payloads[RAW_REL], workspace_root / RAW_REL),
        "normalized_rows": load_normalized_csv_bytes(payloads[NORMALIZED_REL], workspace_root / NORMALIZED_REL),
        "design_manifest_rows": load_jsonl_bytes(payloads[DESIGN_MANIFEST_REL], workspace_root / DESIGN_MANIFEST_REL),
    }


def _audit_geometries(
    clocks: Sequence[Mapping[str, Any]], reader: PublicDesignReader
) -> tuple[list[dict[str, Any]], dict[datetime, dict[str, Any]], list[datetime], list[datetime]]:
    all_times = [_parse_utc(clock["event_time_utc"]) for clock in clocks]
    selected, skipped = greedy_primary_schedule(all_times)
    selected_set = set(selected)
    skipped_set = set(skipped)
    geometry_by_time: dict[datetime, dict[str, Any]] = {}
    ledger: list[dict[str, Any]] = []
    for clock in clocks:
        event_time = _parse_utc(clock["event_time_utc"])
        record: dict[str, Any] = {
            "event_clock_id": clock["event_clock_id"],
            "event_time_utc": clock["event_time_utc"],
            "primary_schedule_status": "SELECTED" if event_time in selected_set else "SKIPPED_OVERLAP",
            "source_complete": False,
        }
        try:
            geometry = compute_pre_event_geometry(event_time, reader.read_range)
            geometry_by_time[event_time] = geometry
            record["source_complete"] = True
            record["geometry"] = geometry
        except EventSourceIncomplete as exc:
            record["source_incomplete_reason"] = str(exc)
        ledger.append(record)
    if set(all_times) != selected_set | skipped_set:
        raise ContractError("primary schedule accounting mismatch")
    return ledger, geometry_by_time, selected, skipped


def _add_control_audit(
    ledger: list[dict[str, Any]],
    all_clean_times: Sequence[datetime],
    selected: Sequence[datetime],
    geometry_by_time: dict[datetime, dict[str, Any]],
    reader: PublicDesignReader,
) -> list[tuple[datetime, datetime]]:
    clean = sorted(set(all_clean_times))
    feasible_controls: set[datetime] = set()
    control_geometry: dict[datetime, dict[str, Any]] = {}
    contamination_by_primary: dict[datetime, bool] = {}
    for primary in selected:
        control = primary - timedelta(days=7)
        contaminated = any(abs(event_time - control) <= timedelta(hours=2) for event_time in clean)
        contamination_by_primary[primary] = contaminated
        if contaminated:
            continue
        try:
            geometry = compute_pre_event_geometry(control, reader.read_range)
            feasible_controls.add(control)
            control_geometry[control] = geometry
        except EventSourceIncomplete:
            pass
    pairs, rejected = match_controls(selected, clean, feasible_controls)
    pair_by_primary = {primary: control for primary, control in pairs}
    rejected_by_primary = {_parse_utc(item["event_time_utc"]): item["reason"] for item in rejected}
    ledger_by_time = {_parse_utc(row["event_time_utc"]): row for row in ledger}
    for primary in selected:
        record = ledger_by_time[primary]
        control = primary - timedelta(days=7)
        record["control_time_utc"] = _iso_utc(control)
        if primary not in geometry_by_time:
            record["control_status"] = "NOT_EVALUATED_PRIMARY_INCOMPLETE"
        elif primary in pair_by_primary:
            record["control_status"] = "SOURCE_FEASIBLE_MATCHED"
            record["control_geometry"] = control_geometry[pair_by_primary[primary]]
        else:
            record["control_status"] = rejected_by_primary.get(primary, "CONTROL_SOURCE_INCOMPLETE")
        if contamination_by_primary.get(primary):
            record["control_status"] = "CONTROL_CONTAMINATED_BY_CLEAN_EVENT"
    return [(primary, control) for primary, control in pairs if primary in geometry_by_time]


def run_production(workspace_root: Path) -> dict[str, Any]:
    workspace_root = assert_safe_directory(workspace_root)
    binding = validate_code_review_authority(
        workspace_root,
        executing_builder_path=Path(__file__),
    )
    registry_row = binding["registry_row"]
    authority = _validate_authority_files(workspace_root)

    raw_document = authority["raw_document"]
    normalized_rows = authority["normalized_rows"]
    clocks, transform_stats = build_clean_clocks(raw_document, normalized_rows)
    clean_csv = clean_clock_csv_bytes(clocks)

    design_manifest_rows = authority["design_manifest_rows"]
    reader = PublicDesignReader(workspace_root / PUBLIC_DESIGN_ROOT_REL, design_manifest_rows)

    clean_csv_path = workspace_root / CLEAN_CSV_REL
    clean_manifest_path = workspace_root / CLEAN_MANIFEST_REL
    evidence_root = workspace_root / EVIDENCE_ROOT_REL
    if clean_csv_path.exists() or clean_manifest_path.exists() or evidence_root.exists():
        raise ContractError("output conflict before production attempt; refusing any overwrite")
    create_directory_create_new(evidence_root, workspace_root=workspace_root)

    started_payload = make_attempt_started_payload(registry_row, binding)

    def work() -> dict[str, Any]:
        write_bytes_create_new(clean_csv_path, clean_csv, workspace_root=workspace_root)
        clean_manifest = {
            "schema_version": "event_vol_oco_clean_clock.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "source_rank": "C",
            "promotion_eligible": False,
            "group_before_semantic_filter": True,
            "fixed_calendar_timezone": "GMT+7",
            "v1_plan": {"path": V1_PLAN_REL, "sha256": V1_PLAN_SHA256},
            "v2_plan": {"path": V2_PLAN_REL, "sha256": V2_PLAN_SHA256},
            "inputs": {
                "raw": {"path": RAW_REL, "sha256": RAW_SHA256},
                "normalized_csv": {"path": NORMALIZED_REL, "sha256": NORMALIZED_SHA256},
                "forex_manifest": {"path": FOREX_MANIFEST_REL, "sha256": FOREX_MANIFEST_SHA256},
            },
            "output": {"path": CLEAN_CSV_REL, "bytes": len(clean_csv), "sha256": sha256_bytes(clean_csv)},
            "transform_counts": transform_stats,
            "limitations": [
                "Third-party impact ranking and timestamps are not an official release ledger.",
                "24 untimed EUR/USD rows and 63 global rows remain audit-only.",
                "This dataset cannot satisfy execution-cost provenance or promotion gates.",
            ],
            "metrics": dict(ZERO_COUNTERS),
        }
        assert_no_forbidden_output_fields(clean_manifest)
        write_json_create_new(clean_manifest_path, clean_manifest, workspace_root=workspace_root)

        ledger, geometry_by_time, selected, skipped = _audit_geometries(clocks, reader)
        all_times = [_parse_utc(clock["event_time_utc"]) for clock in clocks]
        pairs = _add_control_audit(ledger, all_times, selected, geometry_by_time, reader)
        selected_complete = [geometry_by_time[event_time] for event_time in selected if event_time in geometry_by_time]
        risks = [float(item["planned_risk_pips"]) for item in selected_complete]
        gate_result = evaluate_source_gates(
            observed_clean_clusters=len(clocks),
            complete_clean_clusters=len(geometry_by_time),
            matched_pair_count=len(pairs),
            primary_risks_pips=risks,
        )
        verdict = (
            "PASS_SOURCE_FEASIBILITY_DIAGNOSTIC_ONLY"
            if gate_result["all_gates_pass"]
            else "PARK_SOURCE_FEASIBILITY_FAILED"
        )
        report = {
            "schema_version": "event_vol_oco_source_feasibility.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "evidence_class": EVIDENCE_CLASS,
            "engineering_status": "PASS",
            "market_verdict": verdict,
            "source_rank": "C",
            "promotion_eligible": False,
            "transform_counts": transform_stats,
            "complete_clean_clusters": len(geometry_by_time),
            "scheduled_primary_count": len(selected),
            "overlap_skipped_count": len(skipped),
            "scheduled_primary_complete_count": len(selected_complete),
            "matched_source_feasible_pair_count": len(pairs),
            "source_gates": gate_result,
            "later_economics_contract": {
                "authorized_now": False,
                "mt5_model": LATER_ECONOMICS_MT5_MODEL,
                "model_label": LATER_ECONOMICS_MODEL_LABEL,
                "model_zero_allowed": MODEL_ZERO_ALLOWED_FOR_LATER_ECONOMICS,
            },
            "metrics": dict(ZERO_COUNTERS),
        }
        assert_no_forbidden_output_fields(ledger)
        assert_no_forbidden_output_fields(report)
        ledger_path = evidence_root / "event_vol_oco_source_ledger.jsonl"
        report_path = evidence_root / "event_vol_oco_source_report.json"
        receipt_path = evidence_root / "source_feasibility_receipt.json"
        terminal_path = evidence_root / "attempt_terminal.json"
        write_jsonl_create_new(ledger_path, ledger, workspace_root=workspace_root)
        write_json_create_new(report_path, report, workspace_root=workspace_root)
        receipt = {
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "engineering_status": "PASS",
            "market_verdict": verdict,
            "v1_plan_sha256": V1_PLAN_SHA256,
            "v2_plan_sha256": V2_PLAN_SHA256,
            "script_sha256": binding["builder_sha256"],
            **review_binding_fields(binding),
            "artifacts": {
                "clean_clock_csv": {"path": CLEAN_CSV_REL, "sha256": sha256_file(clean_csv_path)},
                "clean_clock_manifest": {"path": CLEAN_MANIFEST_REL, "sha256": sha256_file(clean_manifest_path)},
                "attempt_started": {"sha256": sha256_file(evidence_root / "attempt_started.json")},
                "source_ledger": {"sha256": sha256_file(ledger_path)},
                "source_report": {"sha256": sha256_file(report_path)},
            },
            "public_design": {
                "manifest_sha256": DESIGN_MANIFEST_SHA256,
                "receipt_sha256": DESIGN_RECEIPT_SHA256,
                "m1_source_sha256": PUBLIC_M1_SOURCE_SHA256,
                "research_validation_opened": False,
                "research_holdout_opened": False,
            },
            "promotion_eligible": False,
            "metrics": dict(ZERO_COUNTERS),
        }
        assert_no_forbidden_output_fields(receipt)
        write_json_create_new(receipt_path, receipt, workspace_root=workspace_root)
        terminal = {
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "engineering_status": "PASS",
            "market_verdict": verdict,
            "report_sha256": sha256_file(report_path),
            "receipt_sha256": sha256_file(receipt_path),
            "metrics": dict(ZERO_COUNTERS),
        }
        write_json_create_new(terminal_path, terminal, workspace_root=workspace_root)
        return report

    return execute_with_terminal_guard(evidence_root, work, started_payload=started_payload, workspace_root=workspace_root)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=_workspace_root_from_script())
    parser.add_argument(
        "--execute-source-feasibility",
        action="store_true",
        help="Required explicit switch; still fails closed without reviewed registry authority.",
    )
    args = parser.parse_args(argv)
    if not args.execute_source_feasibility:
        raise ContractError("explicit --execute-source-feasibility is required")
    report = run_production(args.workspace_root)
    print(canonical_json_bytes(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
