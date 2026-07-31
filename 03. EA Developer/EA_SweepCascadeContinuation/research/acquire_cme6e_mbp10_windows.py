#!/usr/bin/env python3
"""Acquire the bounded CME 6E MBP-10 pre-entry source corpus fail-closed.

``plan`` is offline and never loads a Databento key. ``download`` first
re-quotes every planned window through free metadata calls, verifies the
Owner's explicit USD ceiling and all SHA-bound inputs, then downloads the 259
metadata-billable windows serially. Each complete DBN response is hashed and
checkpointed, including an explicit source-empty response, so a failed run can
resume without paying for already verified files or retrying a charged empty
window.

This is a source-acquisition utility, not an EBS test, hypothesis, outcome
join, EA backtest, or HYP004 rescue.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SCHEMA_VERSION = "cme6e_mbp10_window_acquisition.v2"
MANIFEST_SCHEMA_VERSION = "cme6e_mbp10_download_manifest.v2"
CANDIDATE_IDENTITY = "CME_GLOBEX_6E_CONTINUOUS_MBP10_PREENTRY_BOOK_STATE"
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
COST_MODE = "historical-streaming"
WINDOW_SECONDS = 120
DATABENTO_SDK_VERSION = "0.54.0"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
KEY_PATTERN = re.compile(r"^db-[A-Za-z0-9_-]{29}$")
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
PLAN_NAME = "acquisition_plan.json"
MANIFEST_NAME = "download_manifest.json"

WORKSPACE = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
PAIR_EVIDENCE = (
    PACKAGE
    / "research"
    / "evidence"
    / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
)
INPUT_PATH = PAIR_EVIDENCE / "challenger_trades.csv"
FEASIBILITY_PATH = PAIR_EVIDENCE / "CME6E_MBP10_SOURCE_FEASIBILITY_PLAN.json"
CLOCK_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
DATA_ROOT = WORKSPACE / "02. AlphaFactory" / "data"
DEFAULT_ROOT = DATA_ROOT / "databento" / "cme_6e_mbp10_scc"

INPUT_SHA256 = "0BC47F501CD5D9420F4DBE0BC08148CC5F7EFC8AB6C725248582288634D627AD"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
FEASIBILITY_SHA256 = "2EBAC8602350EB69518CACBD8BAF309B49BCE60C98AD2AD5DAFF3AA22FAFAA8B"


class AcquisitionError(RuntimeError):
    """Fail-closed source acquisition error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AcquisitionError(f"expected a JSON object in {path}")
    return value


def stable_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at_utc", "plan_id"}
    }


def plan_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        stable_payload(payload), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _iso_utc(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _filename(position_id: str, end: datetime) -> str:
    return f"PID{int(position_id):09d}_{end.strftime('%Y%m%dT%H%M%SZ')}.dbn.zst"


def _load_server_clock() -> Callable[[datetime], datetime]:
    clock_tools = CLOCK_PATH.parent
    if str(clock_tools) not in sys.path:
        sys.path.insert(0, str(clock_tools))
    from fivepercent_server_clock import server_to_utc

    return server_to_utc


def _verify_local_contract() -> dict[str, Any]:
    checks = (
        (INPUT_PATH, INPUT_SHA256, "entry clock input"),
        (CLOCK_PATH, CLOCK_SHA256, "server clock model"),
        (FEASIBILITY_PATH, FEASIBILITY_SHA256, "source feasibility plan"),
    )
    for path, expected, label in checks:
        if not path.is_file():
            raise AcquisitionError(f"missing {label}: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise AcquisitionError(
                f"{label} SHA mismatch: expected {expected}, got {actual}"
            )
    return load_json(FEASIBILITY_PATH)


def _read_decision_clock(
    server_to_utc: Callable[[datetime], datetime],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with INPUT_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"position_id", "decision_time", "direction"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise AcquisitionError(
                f"entry clock input is missing required fields: {sorted(required)}"
            )
        for raw in reader:
            # Deliberately access only decision-time identity fields. The source CSV
            # contains outcomes, but this acquisition plane never reads them.
            position_id = str(raw["position_id"])
            direction = str(raw["direction"])
            if direction not in {"BUY", "SELL"}:
                raise AcquisitionError(
                    f"position {position_id} has invalid frozen direction {direction!r}"
                )
            server_time = datetime.strptime(str(raw["decision_time"]), TIME_FORMAT)
            end = server_to_utc(server_time)
            start = end - timedelta(seconds=WINDOW_SECONDS)
            rows.append(
                {
                    "position_id": position_id,
                    "direction": direction,
                    "start": _iso_utc(start),
                    "end": _iso_utc(end),
                    "filename": _filename(position_id, end),
                }
            )
    rows.sort(key=lambda item: (item["end"], int(item["position_id"])))
    ids = [item["position_id"] for item in rows]
    ends = [item["end"] for item in rows]
    if len(ids) != len(set(ids)) or len(ends) != len(set(ends)):
        raise AcquisitionError("entry clock contains duplicate position IDs or windows")
    return rows


def build_acquisition_plan() -> dict[str, Any]:
    feasibility = _verify_local_contract()
    metadata = feasibility.get("metadata_only_estimate")
    population = feasibility.get("population_contract")
    if not isinstance(metadata, dict) or not isinstance(population, dict):
        raise AcquisitionError("source feasibility plan is missing frozen contracts")
    if metadata.get("paid_request_made") is not False:
        raise AcquisitionError("feasibility artifact does not prove zero paid requests")
    if metadata.get("quote_mode") != COST_MODE:
        raise AcquisitionError("feasibility quote mode does not match streaming download")
    if population.get("outcome_fields_used") is not False:
        raise AcquisitionError("feasibility population is not outcome-blind")

    rows = _read_decision_clock(_load_server_clock())
    zero_rows = metadata.get("zero_windows")
    if not isinstance(zero_rows, list):
        raise AcquisitionError("feasibility artifact is missing zero-window evidence")
    zero_ids = {str(item.get("position_id")) for item in zero_rows if isinstance(item, dict)}
    all_ids = {item["position_id"] for item in rows}
    if not zero_ids.issubset(all_ids):
        raise AcquisitionError("source-empty positions are absent from the entry clock")
    source_empty = [item for item in rows if item["position_id"] in zero_ids]
    requests = [item for item in rows if item["position_id"] not in zero_ids]

    expected_all = int(population.get("requested_windows", -1))
    expected_nonzero = int(metadata.get("nonzero_windows", -1))
    if len(rows) != expected_all or len(requests) != expected_nonzero:
        raise AcquisitionError(
            "window counts disagree with the frozen feasibility artifact: "
            f"all={len(rows)}/{expected_all}, nonzero={len(requests)}/{expected_nonzero}"
        )
    if rows[0]["end"] != population.get("first_window_end_utc"):
        raise AcquisitionError("first UTC window does not match the frozen feasibility plan")
    if rows[-1]["end"] != population.get("last_window_end_utc"):
        raise AcquisitionError("last UTC window does not match the frozen feasibility plan")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "PLANNED_NOT_QUOTED_NOT_DOWNLOADED",
        "candidate_identity": CANDIDATE_IDENTITY,
        "databento_sdk_version": DATABENTO_SDK_VERSION,
        "not_ebs": True,
        "not_hyp004_rescue": True,
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "stype_out": STYPE_OUT,
        "cost_mode": COST_MODE,
        "window_seconds": WINDOW_SECONDS,
        "input": {
            "path": str(INPUT_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": INPUT_SHA256,
        },
        "clock": {
            "path": str(CLOCK_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": CLOCK_SHA256,
        },
        "feasibility": {
            "path": str(FEASIBILITY_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": FEASIBILITY_SHA256,
        },
        "tool": {
            "path": str(Path(__file__).resolve().relative_to(WORKSPACE)).replace(
                "\\", "/"
            ),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "fields_used": ["position_id", "decision_time", "direction"],
        "outcome_fields_used": False,
        "all_windows": rows,
        "requests": requests,
        "source_empty_windows": source_empty,
        "estimated_cost_usd": float(metadata["estimated_cost_usd"]),
        "estimated_billable_bytes": int(metadata["billable_bytes_total"]),
        "internal_2x_cost_ceiling_usd": float(
            metadata["internal_2x_cost_ceiling_usd"]
        ),
        "recommended_owner_ceiling_usd": float(
            metadata["recommended_owner_ceiling_usd"]
        ),
        "download_authorized": False,
        "paid_request_made": False,
        "prohibitions": [
            "no EBS or spot-CLOB claim",
            "no outcome join before fresh registry and SHA-bound prereg",
            "no HYP004 rerun or rescue",
            "no full-period continuous dump",
            "no paid request without explicit Owner USD ceiling",
        ],
    }
    payload["plan_id"] = plan_id(payload)
    validate_plan(payload)
    return payload


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AcquisitionError("unsupported or missing acquisition plan schema")
    if plan.get("candidate_identity") != CANDIDATE_IDENTITY:
        raise AcquisitionError("acquisition plan candidate identity mismatch")
    if plan.get("databento_sdk_version") != DATABENTO_SDK_VERSION:
        raise AcquisitionError("acquisition plan Databento SDK version mismatch")
    if plan.get("cost_mode") != COST_MODE:
        raise AcquisitionError("acquisition plan cost mode mismatch")
    tool = plan.get("tool")
    if not isinstance(tool, dict) or tool.get("sha256") != sha256_file(
        Path(__file__).resolve()
    ):
        raise AcquisitionError("acquisition plan tool SHA mismatch")
    if plan.get("outcome_fields_used") is not False:
        raise AcquisitionError("acquisition plan must remain outcome-blind")
    if plan.get("plan_id") != plan_id(plan):
        raise AcquisitionError("acquisition plan hash mismatch")
    requests = plan.get("requests")
    if not isinstance(requests, list) or not requests:
        raise AcquisitionError("acquisition plan has no download requests")
    filenames: set[str] = set()
    identities: set[tuple[str, str]] = set()
    for item in requests:
        if not isinstance(item, dict):
            raise AcquisitionError("acquisition plan contains an invalid request")
        required = {"position_id", "direction", "start", "end", "filename"}
        if not required.issubset(item):
            raise AcquisitionError("acquisition request is missing required fields")
        if item["direction"] not in {"BUY", "SELL"}:
            raise AcquisitionError("acquisition request has invalid direction")
        start = datetime.fromisoformat(str(item["start"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(item["end"]).replace("Z", "+00:00"))
        if end - start != timedelta(seconds=WINDOW_SECONDS):
            raise AcquisitionError("acquisition request window is not exactly 120 seconds")
        filename = str(item["filename"])
        identity = (str(item["position_id"]), str(item["end"]))
        if filename in filenames or identity in identities:
            raise AcquisitionError("acquisition plan contains duplicate output identities")
        filenames.add(filename)
        identities.add(identity)


def ensure_output_root(root: Path) -> Path:
    resolved = root.resolve()
    if resolved.drive.upper() != "D:":
        raise AcquisitionError(f"output root must be on D:, got {resolved}")
    try:
        resolved.relative_to(DATA_ROOT.resolve())
    except ValueError as exc:
        raise AcquisitionError(
            f"output root must remain under {DATA_ROOT.resolve()}, got {resolved}"
        ) from exc
    return resolved


def read_user_environment(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except (FileNotFoundError, OSError):
        return None


def load_api_key() -> str:
    key = os.environ.get("DATABENTO_API_KEY") or read_user_environment(
        "DATABENTO_API_KEY"
    )
    if not key:
        raise AcquisitionError(
            "DATABENTO_API_KEY is absent; configure it locally and never paste it into chat"
        )
    key = key.strip()
    if not KEY_PATTERN.fullmatch(key):
        raise AcquisitionError("DATABENTO_API_KEY has an unexpected format")
    return key


def make_client(key: str):
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError(
            "Databento SDK is missing; use the D-side python-databento runtime"
        ) from exc
    installed = str(getattr(db, "__version__", ""))
    if installed != DATABENTO_SDK_VERSION:
        raise AcquisitionError(
            f"Databento SDK version mismatch: required {DATABENTO_SDK_VERSION}, "
            f"installed {installed or 'unknown'}"
        )
    return db.Historical(key)


def validate_dbn_zstd(path: Path) -> None:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise AcquisitionError(f"DBN Zstandard file is missing or empty: {path}")
    with path.open("rb") as handle:
        signature = handle.read(len(ZSTD_MAGIC))
    if signature != ZSTD_MAGIC:
        raise AcquisitionError(f"DBN file has invalid Zstandard signature: {path}")


def validate_dbn_file(path: Path, allow_zero: bool = False) -> int:
    """Fully decode a DBN Zstandard file so truncated streams cannot be adopted."""

    validate_dbn_zstd(path)
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError(
            "Databento SDK is required to validate downloaded DBN files"
        ) from exc
    installed = str(getattr(db, "__version__", ""))
    if installed != DATABENTO_SDK_VERSION:
        raise AcquisitionError(
            f"Databento SDK version mismatch during DBN validation: "
            f"required {DATABENTO_SDK_VERSION}, installed {installed or 'unknown'}"
        )
    try:
        record_count = sum(1 for _ in db.DBNStore.from_file(path))
    except Exception as exc:
        raise AcquisitionError(f"DBN full-stream validation failed for {path}: {exc}") from exc
    if record_count <= 0 and not allow_zero:
        raise AcquisitionError(f"DBN file contains zero market-data records: {path}")
    return record_count


def _api_call(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": item["start"],
        "end": item["end"],
    }


def quote_windows(
    client,
    requests: list[dict[str, Any]],
    *,
    client_factory: Callable[[], Any] | None = None,
    workers: int = 1,
) -> list[dict[str, Any]]:
    if workers < 1 or workers > 16:
        raise AcquisitionError("metadata quote workers must be between 1 and 16")
    local = threading.local()

    def quote(item: dict[str, Any]) -> dict[str, Any]:
        if client_factory is None:
            metadata = client.metadata
        else:
            if not hasattr(local, "client"):
                local.client = client_factory()
            metadata = local.client.metadata
        call = _api_call(item)
        cost = float(metadata.get_cost(mode=COST_MODE, **call))
        size = int(metadata.get_billable_size(**call))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError(
                f"invalid live quote for position {item['position_id']}: cost={cost}, size={size}"
            )
        return {
            "position_id": item["position_id"],
            "start": item["start"],
            "end": item["end"],
            "estimated_cost_usd": cost,
            "billable_bytes": size,
        }

    if workers == 1:
        return [quote(item) for item in requests]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(quote, requests))


def _verified_downloads(
    root: Path, manifest: dict[str, Any], plan: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise AcquisitionError("existing download manifest schema mismatch")
    if manifest.get("plan_id") != plan["plan_id"]:
        raise AcquisitionError("existing download manifest belongs to another plan")
    planned = {str(item["filename"]): item for item in plan["requests"]}
    verified: dict[str, dict[str, Any]] = {}
    for item in manifest.get("downloads", []):
        if not isinstance(item, dict):
            raise AcquisitionError("download manifest contains an invalid file entry")
        filename = str(item.get("filename", ""))
        expected_hash = str(item.get("sha256", ""))
        if filename not in planned:
            raise AcquisitionError(
                f"download manifest contains an output outside the frozen plan: {filename}"
            )
        if filename in verified:
            raise AcquisitionError(
                f"download manifest contains a duplicate output: {filename}"
            )
        request = planned[filename]
        for field in ("position_id", "direction", "start", "end"):
            if str(item.get(field, "")) != str(request[field]):
                raise AcquisitionError(
                    f"download manifest identity mismatch for {filename}: {field}"
                )
        path = root / "raw" / filename
        source_empty = item.get("source_empty") is True
        records = validate_dbn_file(path, allow_zero=source_empty)
        if source_empty != (records == 0):
            raise AcquisitionError(
                f"checkpointed DBN source-empty classification mismatch for {filename}"
            )
        if int(item.get("records", -1)) != records:
            raise AcquisitionError(
                f"checkpointed DBN record count mismatch for {filename}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise AcquisitionError(
                f"checkpointed DBN hash mismatch for {filename}: {actual_hash}"
            )
        if int(item.get("bytes", -1)) != path.stat().st_size:
            raise AcquisitionError(
                f"checkpointed DBN byte count mismatch for {filename}"
            )
        verified[filename] = item
    return verified


def _recover_in_flight(
    *,
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    quotes_by_position: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    in_flight = manifest.get("in_flight")
    if in_flight in (None, {}):
        return None
    if not isinstance(in_flight, dict):
        raise AcquisitionError("download manifest has an invalid in-flight journal")
    filename = str(in_flight.get("filename", ""))
    planned = {str(item["filename"]): item for item in plan["requests"]}
    if filename not in planned:
        raise AcquisitionError("in-flight journal is outside the frozen plan")
    request = planned[filename]
    for field in ("position_id", "direction", "start", "end"):
        if str(in_flight.get(field, "")) != str(request[field]):
            raise AcquisitionError(
                f"in-flight journal identity mismatch for {filename}: {field}"
            )
    raw_root = root / "raw"
    output = raw_root / filename
    partial = output.with_suffix(output.suffix + ".partial")
    if output.exists() and partial.exists():
        raise AcquisitionError(
            f"both final and partial files exist for in-flight request: {filename}"
        )
    candidate = output if output.exists() else partial
    if not candidate.exists():
        raise AcquisitionError(
            "in-flight paid request has no recoverable file; refusing automatic retry "
            f"for position {request['position_id']}"
        )
    records = validate_dbn_file(candidate, allow_zero=True)
    if candidate == partial:
        os.replace(partial, output)
    quote = quotes_by_position[request["position_id"]]
    return {
        "position_id": request["position_id"],
        "direction": request["direction"],
        "start": request["start"],
        "end": request["end"],
        "filename": filename,
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "records": records,
        "source_empty": records == 0,
        "estimated_cost_usd": quote["estimated_cost_usd"],
        "billable_bytes": quote["billable_bytes"],
        "recovered_from_in_flight": True,
    }


def download_windows(
    *,
    client,
    plan: dict[str, Any],
    approved_max_usd: float,
    root: Path,
    metadata_client_factory: Callable[[], Any] | None = None,
    quote_workers: int = 1,
) -> dict[str, Any]:
    validate_plan(plan)
    _verify_local_contract()
    root = ensure_output_root(root)
    if not math.isfinite(approved_max_usd) or approved_max_usd <= 0:
        raise AcquisitionError("approved USD ceiling must be a positive finite number")
    contract_ceiling = float(plan.get("recommended_owner_ceiling_usd", 0))
    if approved_max_usd > contract_ceiling:
        raise AcquisitionError(
            f"approved ceiling ${approved_max_usd:.6f} exceeds frozen contract ceiling "
            f"${contract_ceiling:.6f}"
        )

    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / MANIFEST_NAME
    existing = load_json(manifest_path) if manifest_path.is_file() else {}
    verified = _verified_downloads(root, existing, plan)

    requests = list(plan["requests"])
    quotes = quote_windows(
        client,
        requests,
        client_factory=metadata_client_factory,
        workers=quote_workers,
    )
    if len(quotes) != len(requests):
        raise AcquisitionError("live quote coverage does not match the acquisition plan")
    empty = [item["position_id"] for item in quotes if item["billable_bytes"] <= 0]
    if empty:
        raise AcquisitionError(
            "planned non-empty windows are now empty; no paid request made: "
            + ",".join(empty)
        )
    live_total = sum(float(item["estimated_cost_usd"]) for item in quotes)
    if live_total > approved_max_usd:
        raise AcquisitionError(
            f"live estimate ${live_total:.6f} exceeds approved ceiling "
            f"${approved_max_usd:.6f}"
        )
    drift_ceiling = float(
        plan.get("internal_2x_cost_ceiling_usd", contract_ceiling)
    )
    if live_total > drift_ceiling:
        raise AcquisitionError(
            f"live estimate ${live_total:.6f} exceeds frozen two-times drift ceiling "
            f"${drift_ceiling:.6f}"
        )

    by_position = {item["position_id"]: item for item in quotes}
    downloads = list(verified.values())
    completed_names = set(verified)
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "updated_at_utc": utc_now(),
        "status": "QUOTED_NOT_DOWNLOADED",
        "candidate_identity": CANDIDATE_IDENTITY,
        "plan_id": plan["plan_id"],
        "approved_max_usd": approved_max_usd,
        "live_estimated_total_usd": live_total,
        "live_estimated_billable_bytes": sum(
            int(item["billable_bytes"]) for item in quotes
        ),
        "live_quotes": quotes,
        "downloads": downloads,
        "resume_verified_files": len(verified),
        "recovered_in_flight_files": int(
            existing.get("recovered_in_flight_files", 0)
        ),
        "in_flight": existing.get("in_flight"),
        "paid_requests_completed": len(downloads),
        "nonempty_files": sum(
            1 for item in downloads if item.get("source_empty") is not True
        ),
        "source_empty_files": sum(
            1 for item in downloads if item.get("source_empty") is True
        ),
        "estimated_cost_completed_usd": sum(
            float(by_position[item["position_id"]]["estimated_cost_usd"])
            for item in downloads
        ),
        "outcome_fields_used": False,
        "api_key_stored": False,
    }
    write_json_atomic(manifest_path, manifest)

    raw_root = root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    recovered = _recover_in_flight(
        root=root,
        manifest=manifest,
        plan=plan,
        quotes_by_position=by_position,
    )
    if recovered is not None:
        if recovered["filename"] in completed_names:
            raise AcquisitionError(
                "in-flight journal duplicates an already checkpointed download"
            )
        downloads.append(recovered)
        completed_names.add(recovered["filename"])
        manifest["downloads"] = downloads
        manifest["in_flight"] = None
        manifest["recovered_in_flight_files"] += 1
        manifest["paid_requests_completed"] = len(downloads)
        manifest["nonempty_files"] = sum(
            1 for item in downloads if item.get("source_empty") is not True
        )
        manifest["source_empty_files"] = sum(
            1 for item in downloads if item.get("source_empty") is True
        )
        manifest["estimated_cost_completed_usd"] = sum(
            float(entry["estimated_cost_usd"]) for entry in downloads
        )
        manifest["updated_at_utc"] = utc_now()
        write_json_atomic(manifest_path, manifest)

    for request in requests:
        filename = str(request["filename"])
        if filename in completed_names:
            continue
        output = raw_root / filename
        partial = output.with_suffix(output.suffix + ".partial")
        if output.exists():
            raise AcquisitionError(
                f"unmanifested output already exists; refusing overwrite: {output}"
            )
        if partial.exists():
            raise AcquisitionError(
                f"unmanifested partial output exists; refusing paid retry: {partial}"
            )
        quote = by_position[request["position_id"]]
        manifest["status"] = "DOWNLOADING"
        manifest["in_flight"] = {
            "position_id": request["position_id"],
            "direction": request["direction"],
            "start": request["start"],
            "end": request["end"],
            "filename": filename,
            "started_at_utc": utc_now(),
            "estimated_cost_usd": quote["estimated_cost_usd"],
            "billable_bytes": quote["billable_bytes"],
        }
        manifest["updated_at_utc"] = utc_now()
        write_json_atomic(manifest_path, manifest)
        call = _api_call(request)
        try:
            client.timeseries.get_range(
                **call,
                stype_out=STYPE_OUT,
                path=partial,
            )
        except Exception as exc:  # SDK/network error becomes an auditable stop.
            raise AcquisitionError(
                f"paid request failed for position {request['position_id']}: {exc}"
            ) from exc
        records = validate_dbn_file(partial, allow_zero=True)
        os.replace(partial, output)
        item = {
            "position_id": request["position_id"],
            "direction": request["direction"],
            "start": request["start"],
            "end": request["end"],
            "filename": filename,
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
            "records": records,
            "source_empty": records == 0,
            "estimated_cost_usd": quote["estimated_cost_usd"],
            "billable_bytes": quote["billable_bytes"],
        }
        downloads.append(item)
        completed_names.add(filename)
        manifest["downloads"] = downloads
        manifest["in_flight"] = None
        manifest["paid_requests_completed"] = len(downloads)
        manifest["nonempty_files"] = sum(
            1 for entry in downloads if entry.get("source_empty") is not True
        )
        manifest["source_empty_files"] = sum(
            1 for entry in downloads if entry.get("source_empty") is True
        )
        manifest["estimated_cost_completed_usd"] = sum(
            float(entry["estimated_cost_usd"]) for entry in downloads
        )
        manifest["updated_at_utc"] = utc_now()
        write_json_atomic(manifest_path, manifest)

    if len(downloads) != len(requests):
        raise AcquisitionError(
            f"download coverage incomplete: {len(downloads)}/{len(requests)}"
        )
    _verified_downloads(root, manifest, plan)
    manifest["status"] = "DOWNLOADED_RAW_VALIDATION_REQUIRED"
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    return manifest


def validate_download(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    validate_plan(plan)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise AcquisitionError(f"download manifest is absent: {manifest_path}")
    manifest = load_json(manifest_path)
    verified = _verified_downloads(root, manifest, plan)
    if len(verified) != len(plan["requests"]):
        raise AcquisitionError(
            f"validated DBN coverage is incomplete: {len(verified)}/{len(plan['requests'])}"
        )
    return {
        "status": "RAW_SOURCE_HASH_VALIDATION_PASS",
        "plan_id": plan["plan_id"],
        "files": len(verified),
        "nonempty_files": sum(
            1 for item in verified.values() if item.get("source_empty") is not True
        ),
        "source_empty_files": sum(
            1 for item in verified.values() if item.get("source_empty") is True
        ),
        "bytes": sum(int(item["bytes"]) for item in verified.values()),
        "outcome_fields_used": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "download", "validate"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--approve-max-usd", type=float)
    parser.add_argument("--expected-plan-id")
    parser.add_argument("--quote-workers", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = ensure_output_root(args.root)
        plan_path = root / PLAN_NAME
        if args.action == "plan":
            plan = build_acquisition_plan()
            root.mkdir(parents=True, exist_ok=True)
            write_json_atomic(plan_path, plan)
            print(
                "CME6E_MBP10_PLAN "
                f"status={plan['status']} plan_id={plan['plan_id']} "
                f"windows={len(plan['requests'])}/{len(plan['all_windows'])} "
                f"estimated_cost_usd={plan['estimated_cost_usd']:.12f} "
                f"paid_request_made=false"
            )
            print(f"plan={plan_path}")
            return 0

        plan = load_json(plan_path)
        validate_plan(plan)
        if not args.expected_plan_id:
            raise AcquisitionError(
                f"{args.action} requires --expected-plan-id {plan['plan_id']}"
            )
        if args.expected_plan_id != plan["plan_id"]:
            raise AcquisitionError("operator expected plan ID does not match disk plan")

        if args.action == "validate":
            result = validate_download(root, plan)
            print(
                "CME6E_MBP10_VALIDATE "
                f"status={result['status']} files={result['files']} "
                f"nonempty={result['nonempty_files']} "
                f"source_empty={result['source_empty_files']} bytes={result['bytes']}"
            )
            return 0

        if args.approve_max_usd is None:
            raise AcquisitionError("download requires --approve-max-usd")
        key = load_api_key()
        client = make_client(key)
        result = download_windows(
            client=client,
            plan=plan,
            approved_max_usd=args.approve_max_usd,
            root=root,
            metadata_client_factory=lambda: make_client(key),
            quote_workers=args.quote_workers,
        )
        print(
            "CME6E_MBP10_DOWNLOAD "
            f"status={result['status']} files={len(result['downloads'])} "
            f"nonempty={result['nonempty_files']} "
            f"source_empty={result['source_empty_files']} "
            f"live_estimate_usd={result['live_estimated_total_usd']:.12f}"
        )
        print(f"manifest={root / MANIFEST_NAME}")
        return 0
    except AcquisitionError as exc:
        print(f"CME6E_MBP10_ACQUISITION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
