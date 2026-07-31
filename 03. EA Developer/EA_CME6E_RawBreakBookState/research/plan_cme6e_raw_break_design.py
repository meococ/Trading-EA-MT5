#!/usr/bin/env python3
"""Quote an outcome-blind CME 6E raw-BREAK DESIGN corpus without downloading it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SCHEMA_VERSION = "cme6e_raw_break_design_source_plan.v1"
CANDIDATE_IDENTITY = "CME_GLOBEX_6E_MBP10_RAW_BREAK_BOOK_STATE"
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
COST_MODE = "historical-streaming"
DATABENTO_SDK_VERSION = "0.54.0"
WINDOW_SECONDS = 120
DESIGN_YEARS = (2019, 2020)
SEALED_OOS_YEARS = (2021, 2022)
KEY_PATTERN = re.compile(r"^db-[A-Za-z0-9_-]{29}$")

WORKSPACE = Path(__file__).resolve().parents[3]
MODULE_PATH = Path(__file__).resolve()
PAIR_EVIDENCE = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SweepCascadeContinuation"
    / "research"
    / "evidence"
    / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
)
CONTROL_PATH = PAIR_EVIDENCE / "control_trades.csv"
CLOCK_PATH = (
    WORKSPACE
    / "02. AlphaFactory"
    / "tools"
    / "research"
    / "fivepercent_server_clock.py"
)
PARENT_PLAN_PATH = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_mbp10_scc"
    / "acquisition_plan.json"
)
PARENT_MANIFEST_PATH = PARENT_PLAN_PATH.with_name("download_manifest.json")
DEFAULT_OUTPUT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_raw_break_design"
    / "source_plan.json"
)
REUSABLE_QUOTE_PATH = DEFAULT_OUTPUT.with_name("source_plan.unbound_tool_superseded.json")

CONTROL_SHA256 = "07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
PARENT_PLAN_SHA256 = "CD7DA4F331D7A52B0FEE5B7F9E82755FA2D342E8DA2AA055FA8F691B671FD929"
PARENT_MANIFEST_SHA256 = "2F2018175DE9C3ED9EA18FC8701E2AE3A17E16DBFE66468EFB2F6455E9454B8C"
REUSABLE_QUOTE_SHA256 = "FF06D9BD348EF4146AFBF84FA1CBED63F8A26F33F53B7B58ECD903F07FA92454"


class PlanError(RuntimeError):
    """Fail-closed source-planning error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanError(f"expected a JSON object in {path}")
    return value


def verify_inputs() -> None:
    checks = (
        (CONTROL_PATH, CONTROL_SHA256, "raw BREAK control decisions"),
        (CLOCK_PATH, CLOCK_SHA256, "server clock"),
        (PARENT_PLAN_PATH, PARENT_PLAN_SHA256, "validated 261-window plan"),
        (PARENT_MANIFEST_PATH, PARENT_MANIFEST_SHA256, "validated 261-window manifest"),
    )
    for path, expected, label in checks:
        if not path.is_file():
            raise PlanError(f"missing {label}: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise PlanError(f"{label} SHA mismatch: expected {expected}, got {actual}")


def load_server_to_utc() -> Callable[[datetime], datetime]:
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", CLOCK_PATH)
    if spec is None or spec.loader is None:
        raise PlanError("cannot load canonical server clock")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.server_to_utc


def read_design_requests() -> list[dict[str, str]]:
    verify_inputs()
    server_to_utc = load_server_to_utc()
    requests: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    with CONTROL_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"position_id", "decision_time", "direction"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise PlanError("control decision file is missing identity fields")
        for raw in reader:
            # Deliberately access only decision identity. Outcome-bearing columns
            # remain present in the source CSV but are never read by this planner.
            position_id = str(raw["position_id"])
            direction = str(raw["direction"])
            if direction not in {"BUY", "SELL"}:
                raise PlanError(f"invalid direction for position {position_id}")
            server_time = datetime.strptime(
                str(raw["decision_time"]), "%Y.%m.%d %H:%M:%S"
            )
            decision_utc = server_to_utc(server_time).replace(tzinfo=timezone.utc)
            if decision_utc.year not in DESIGN_YEARS:
                continue
            identity = (position_id, decision_utc.isoformat())
            if identity in seen:
                raise PlanError(f"duplicate design identity: {identity}")
            seen.add(identity)
            start = decision_utc - timedelta(seconds=WINDOW_SECONDS)
            requests.append(
                {
                    "position_id": position_id,
                    "direction": direction,
                    "start": start.isoformat().replace("+00:00", "Z"),
                    "end": decision_utc.isoformat().replace("+00:00", "Z"),
                    "filename": (
                        f"CTRL_PID{int(position_id):09d}_"
                        f"{decision_utc.strftime('%Y%m%dT%H%M%SZ')}.dbn.zst"
                    ),
                }
            )
    requests.sort(key=lambda item: (item["end"], int(item["position_id"])))
    if len(requests) != 547:
        raise PlanError(f"unexpected DESIGN decision count: {len(requests)}")
    return requests


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


def load_client():
    key = (os.environ.get("DATABENTO_API_KEY") or read_user_environment("DATABENTO_API_KEY") or "").strip()
    if not KEY_PATTERN.fullmatch(key):
        raise PlanError("valid local DATABENTO_API_KEY is required for free metadata quotes")
    try:
        import databento as db
    except ImportError as exc:
        raise PlanError("use the D-side python-databento runtime") from exc
    if str(getattr(db, "__version__", "")) != DATABENTO_SDK_VERSION:
        raise PlanError("Databento SDK version mismatch")
    return db.Historical(key)


def quote_requests(
    requests: list[dict[str, str]],
    *,
    client_factory: Callable[[], Any],
    workers: int,
) -> list[dict[str, Any]]:
    if workers < 1 or workers > 16:
        raise PlanError("metadata workers must be between 1 and 16")
    local = threading.local()

    def quote(item: dict[str, str]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = client_factory()
        call = {
            "dataset": DATASET,
            "schema": SCHEMA,
            "symbols": [SYMBOL],
            "stype_in": STYPE_IN,
            "start": item["start"],
            "end": item["end"],
        }
        cost = float(local.client.metadata.get_cost(mode=COST_MODE, **call))
        size = int(local.client.metadata.get_billable_size(**call))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise PlanError(f"invalid metadata quote for position {item['position_id']}")
        return {
            "position_id": item["position_id"],
            "estimated_cost_usd": cost,
            "billable_bytes": size,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(quote, requests))


def load_reusable_quotes(
    path: Path, expected_sha256: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not path.is_file():
        raise PlanError(f"metadata quote receipt is absent: {path}")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise PlanError(
            f"metadata quote receipt SHA mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    receipt = load_json(path)
    if receipt.get("candidate_identity") != CANDIDATE_IDENTITY:
        raise PlanError("metadata quote receipt candidate mismatch")
    if receipt.get("input", {}).get("outcome_fields_used") is not False:
        raise PlanError("metadata quote receipt is not outcome-blind")
    if receipt.get("sealed_oos_quoted") is not False:
        raise PlanError("metadata quote receipt opened sealed OOS")
    if receipt.get("paid_request_made") is not False:
        raise PlanError("metadata quote receipt reports a paid request")
    quotes = receipt.get("live_quotes")
    if not isinstance(quotes, list) or len(quotes) != 547:
        raise PlanError("metadata quote receipt coverage mismatch")
    for item in quotes:
        if not isinstance(item, dict):
            raise PlanError("metadata quote receipt contains an invalid quote")
        cost = float(item.get("estimated_cost_usd", -1))
        size = int(item.get("billable_bytes", -1))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise PlanError("metadata quote receipt contains an invalid cost or size")
    provenance = {
        "mode": "hash_bound_metadata_quote_reuse",
        "path": str(path.resolve().relative_to(WORKSPACE)).replace("\\", "/"),
        "sha256": actual_sha256,
        "source_plan_id": receipt.get("plan_id"),
        "source_generated_at_utc": receipt.get("generated_at_utc"),
        "network_calls": 0,
        "paid_request_made": False,
        "outcome_fields_used": False,
        "sealed_oos_quoted": False,
    }
    return quotes, provenance


def build_plan(
    requests: list[dict[str, str]],
    quotes: list[dict[str, Any]],
    *,
    quote_provenance: dict[str, Any],
) -> dict[str, Any]:
    if len(requests) != len(quotes):
        raise PlanError("metadata quote coverage mismatch")
    quoted = {str(item["position_id"]): item for item in quotes}
    if len(quoted) != len(requests):
        raise PlanError("duplicate metadata quote identity")
    metadata_empty = [
        item for item in requests if int(quoted[item["position_id"]]["billable_bytes"]) <= 0
    ]
    billable = [item for item in requests if item not in metadata_empty]
    total_cost = sum(float(quoted[item["position_id"]]["estimated_cost_usd"]) for item in billable)
    total_bytes = sum(int(quoted[item["position_id"]]["billable_bytes"]) for item in billable)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "METADATA_QUOTED_OWNER_APPROVAL_REQUIRED",
        "candidate_identity": CANDIDATE_IDENTITY,
        "not_ebs": True,
        "not_hyp004_rescue": True,
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "cost_mode": COST_MODE,
        "window_seconds": WINDOW_SECONDS,
        "design_utc_years": list(DESIGN_YEARS),
        "sealed_oos_utc_years": list(SEALED_OOS_YEARS),
        "sealed_oos_quoted": False,
        "input": {
            "path": str(CONTROL_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": CONTROL_SHA256,
            "fields_used": ["position_id", "decision_time", "direction"],
            "outcome_fields_used": False,
        },
        "clock": {
            "path": str(CLOCK_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": CLOCK_SHA256,
        },
        "source_feasibility_parent": {
            "plan_path": str(PARENT_PLAN_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "plan_sha256": PARENT_PLAN_SHA256,
            "manifest_path": str(PARENT_MANIFEST_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "manifest_sha256": PARENT_MANIFEST_SHA256,
        },
        "tool": {
            "path": str(MODULE_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": sha256_file(MODULE_PATH),
        },
        "quote_provenance": quote_provenance,
        "requests": billable,
        "metadata_empty_windows": metadata_empty,
        "live_quotes": quotes,
        "estimated_cost_usd": total_cost,
        "estimated_billable_bytes": total_bytes,
        "internal_2x_cost_ceiling_usd": total_cost * 2.0,
        "recommended_owner_ceiling_usd": math.ceil(total_cost * 200.0) / 100.0,
        "download_authorized": False,
        "paid_request_made": False,
        "prohibitions": [
            "metadata planning only; this tool has no time-series download call",
            "no outcome join before fresh registry and SHA-bound prereg",
            "no HYP004 amendment, rerun or rescue claim",
            "no OOS quote, download or outcome access",
            "new explicit Owner USD ceiling required before DESIGN acquisition",
        ],
    }
    payload["plan_id"] = plan_id(payload)
    validate_plan(payload)
    return payload


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise PlanError("source plan schema mismatch")
    if plan.get("candidate_identity") != CANDIDATE_IDENTITY:
        raise PlanError("candidate identity mismatch")
    if plan.get("tool", {}).get("sha256") != sha256_file(MODULE_PATH):
        raise PlanError("planner tool SHA mismatch")
    quote_provenance = plan.get("quote_provenance")
    if not isinstance(quote_provenance, dict):
        raise PlanError("metadata quote provenance is absent")
    if quote_provenance.get("paid_request_made") is not False:
        raise PlanError("metadata quote provenance reports a paid request")
    if plan.get("input", {}).get("outcome_fields_used") is not False:
        raise PlanError("source plan must remain outcome-blind")
    if plan.get("sealed_oos_quoted") is not False:
        raise PlanError("OOS must remain unquoted")
    if plan.get("download_authorized") is not False or plan.get("paid_request_made") is not False:
        raise PlanError("metadata-only plan cannot authorize a paid request")
    if plan.get("plan_id") != plan_id(plan):
        raise PlanError("source plan hash mismatch")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--reuse-quotes-from", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        requests = read_design_requests()
        if args.reuse_quotes_from is not None:
            quotes, quote_provenance = load_reusable_quotes(
                args.reuse_quotes_from.resolve(), REUSABLE_QUOTE_SHA256
            )
        else:
            quotes = quote_requests(
                requests, client_factory=load_client, workers=args.workers
            )
            quote_provenance = {
                "mode": "live_metadata_quotes",
                "network_calls": len(requests) * 2,
                "paid_request_made": False,
                "outcome_fields_used": False,
                "sealed_oos_quoted": False,
            }
        plan = build_plan(
            requests,
            quotes,
            quote_provenance=quote_provenance,
        )
        output = args.output.resolve()
        if output.drive.upper() != "D:":
            raise PlanError("source plan output must remain on D:")
        write_json_atomic(output, plan)
        print(
            "CME6E_RAW_BREAK_DESIGN_PLAN "
            f"status={plan['status']} plan_id={plan['plan_id']} "
            f"billable={len(plan['requests'])}/547 "
            f"estimated_usd={plan['estimated_cost_usd']:.12f} "
            f"recommended_ceiling_usd={plan['recommended_owner_ceiling_usd']:.2f} "
            "paid_request_made=false outcome_fields_used=false oos_quoted=false"
        )
        print(f"plan={output}")
        return 0
    except PlanError as exc:
        print(f"CME6E_RAW_BREAK_DESIGN_PLAN_BLOCKED reason={exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
