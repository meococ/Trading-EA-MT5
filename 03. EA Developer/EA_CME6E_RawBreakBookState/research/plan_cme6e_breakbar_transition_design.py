#!/usr/bin/env python3
"""Quote a clock-correct CME 6E break-bar DESIGN corpus without downloading it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SCHEMA_VERSION = "cme6e_breakbar_transition_source_plan.v1"
CANDIDATE_IDENTITY = "CME_GLOBEX_6E_MBP10_RAW_BREAK_BREAKBAR_TRANSITION"
PROPOSED_HYPOTHESIS_ID = "HYP-CME6E-RAWBREAK-BOOKTRANSITION-002"
PRIOR_HYPOTHESIS_ID = "HYP-CME6E-RAWBREAK-BOOKSTATE-001"
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
COST_MODE = "historical-streaming"
DATABENTO_SDK_VERSION = "0.54.0"
DESIGN_YEARS = (2021, 2022)
EXPECTED_ROWS = 565
KEY_PATTERN = re.compile(r"^db-[A-Za-z0-9_-]{29}$")

WORKSPACE = Path(__file__).resolve().parents[3]
MODULE_PATH = Path(__file__).resolve()
CONTROL_PATH = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SweepCascadeContinuation"
    / "research"
    / "evidence"
    / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    / "control_trades.csv"
)
CLOCK_PATH = (
    WORKSPACE
    / "02. AlphaFactory"
    / "tools"
    / "research"
    / "fivepercent_server_clock.py"
)
PRIOR_READOUT_PATH = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_CME6E_RawBreakBookState"
    / "research"
    / "HYP-CME6E-RAWBREAK-BOOKSTATE-001_CHART_FORENSICS_READOUT.md"
)
DEFAULT_OUTPUT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_breakbar_transition_design"
    / "source_plan.json"
)

CONTROL_SHA256 = "07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
PRIOR_READOUT_SHA256 = "562A87F6FBD46E1F8C7EA5874E017A79193C8B9ECD16553F388CD9C2486EAFD8"


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


def compute_plan_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        stable_payload(payload), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def verify_inputs() -> None:
    checks = (
        (CONTROL_PATH, CONTROL_SHA256, "raw BREAK control ledger"),
        (CLOCK_PATH, CLOCK_SHA256, "server clock"),
        (PRIOR_READOUT_PATH, PRIOR_READOUT_SHA256, "clock-forensics readout"),
    )
    for path, expected, label in checks:
        if not path.is_file():
            raise PlanError(f"missing {label}: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise PlanError(
                f"{label} SHA mismatch: expected {expected}, got {actual}"
            )


def load_server_to_utc() -> Callable[[datetime], datetime]:
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", CLOCK_PATH)
    if spec is None or spec.loader is None:
        raise PlanError("cannot load canonical server clock")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.server_to_utc


def _format_utc(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def read_design_requests() -> list[dict[str, str | int]]:
    """Read only decision identity and execution-clock fields from the parent ledger."""
    verify_inputs()
    server_to_utc = load_server_to_utc()
    requests: list[dict[str, str | int]] = []
    seen: set[tuple[str, str]] = set()
    with CONTROL_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"position_id", "decision_time", "open_time", "direction"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise PlanError("control ledger is missing identity/clock fields")
        for raw in reader:
            # Do not access close_time, prices, stop/target, net or realized_r.
            position_id = str(raw["position_id"])
            direction = str(raw["direction"])
            if direction not in {"BUY", "SELL"}:
                raise PlanError(f"invalid direction for position {position_id}")
            break_server = datetime.strptime(
                str(raw["decision_time"]), "%Y.%m.%d %H:%M:%S"
            )
            if break_server.year not in DESIGN_YEARS:
                continue
            actual_server = datetime.strptime(
                str(raw["open_time"]), "%Y.%m.%d %H:%M:%S"
            )
            break_utc = server_to_utc(break_server).replace(tzinfo=timezone.utc)
            actual_utc = server_to_utc(actual_server).replace(tzinfo=timezone.utc)
            duration = int((actual_utc - break_utc).total_seconds())
            if duration not in {300, 330}:
                raise PlanError(
                    f"unexpected break-to-entry lag for position {position_id}: {duration}s"
                )
            identity = (position_id, _format_utc(actual_utc))
            if identity in seen:
                raise PlanError(f"duplicate DESIGN identity: {identity}")
            seen.add(identity)
            start = _format_utc(break_utc)
            end = _format_utc(actual_utc)
            requests.append(
                {
                    "position_id": position_id,
                    "direction": direction,
                    "break_bar_open": start,
                    "actual_decision": end,
                    "start": start,
                    "end": end,
                    "duration_seconds": duration,
                    "filename": (
                        f"CTRL_PID{int(position_id):09d}_"
                        f"{actual_utc.strftime('%Y%m%dT%H%M%SZ')}.dbn.zst"
                    ),
                }
            )
    requests.sort(key=lambda item: (str(item["end"]), int(item["position_id"])))
    if len(requests) != EXPECTED_ROWS:
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
    key = (
        os.environ.get("DATABENTO_API_KEY")
        or read_user_environment("DATABENTO_API_KEY")
        or ""
    ).strip()
    if not KEY_PATTERN.fullmatch(key):
        raise PlanError("valid local DATABENTO_API_KEY is required for metadata quotes")
    try:
        import databento as db
    except ImportError as exc:
        raise PlanError("use the D-side Python Databento runtime") from exc
    if str(getattr(db, "__version__", "")) != DATABENTO_SDK_VERSION:
        raise PlanError("Databento SDK version mismatch")
    return db.Historical(key)


def quote_requests(
    requests: list[dict[str, str | int]],
    *,
    client_factory: Callable[[], Any],
    workers: int,
) -> list[dict[str, Any]]:
    if workers < 1 or workers > 16:
        raise PlanError("metadata workers must be between 1 and 16")
    local = threading.local()

    def quote(item: dict[str, str | int]) -> dict[str, Any]:
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
            "position_id": str(item["position_id"]),
            "estimated_cost_usd": cost,
            "billable_bytes": size,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(quote, requests))


def build_plan(
    requests: list[dict[str, str | int]],
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
        item
        for item in requests
        if int(quoted[str(item["position_id"])]["billable_bytes"]) <= 0
    ]
    billable = [item for item in requests if item not in metadata_empty]
    total_cost = sum(
        float(quoted[str(item["position_id"])]["estimated_cost_usd"])
        for item in billable
    )
    total_bytes = sum(
        int(quoted[str(item["position_id"])]["billable_bytes"])
        for item in billable
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "METADATA_QUOTED_OWNER_APPROVAL_REQUIRED",
        "candidate_identity": CANDIDATE_IDENTITY,
        "proposed_hypothesis_id": PROPOSED_HYPOTHESIS_ID,
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "cost_mode": COST_MODE,
        "design_utc_years": list(DESIGN_YEARS),
        "input": {
            "path": str(CONTROL_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": CONTROL_SHA256,
            "fields_used": ["position_id", "decision_time", "open_time", "direction"],
            "outcome_fields_used": False,
        },
        "clock": {
            "path": str(CLOCK_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": CLOCK_SHA256,
        },
        "clock_semantics": {
            "feature_window_start_role": "BREAK_BAR_OPEN",
            "feature_window_end_role": "ACTUAL_NEXT_BAR_DECISION_ENTRY",
            "expected_duration_seconds": [300, 330],
            "feature_window_contains_full_closed_break_bar": True,
            "records_must_be_strictly_before_actual_decision": True,
        },
        "prior_hypothesis": {
            "hypothesis_id": PRIOR_HYPOTHESIS_ID,
            "readout_path": str(PRIOR_READOUT_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "readout_sha256": PRIOR_READOUT_SHA256,
            "oos_opened_under_prior_id": False,
            "same_id_rescue": False,
            "delta": "new clock-correct break-bar transition data contract on a source-unopened population",
        },
        "feature_contract_preview": {
            "levels": [0, 1, 2, 3, 4],
            "direction_aligned": True,
            "transition": "compare early and late displayed-depth imbalance within the closed M5 break bar",
            "threshold_frozen_after_source_validation_only": True,
            "outcomes_used": False,
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
        "recommended_owner_ceiling_usd": math.ceil(total_cost * 200.0 - 1e-9) / 100.0,
        "download_authorized": False,
        "paid_request_made": False,
        "outcomes_opened": False,
        "prohibitions": [
            "metadata planning only; this tool has no timeseries surface",
            "no paid request without explicit Owner plan ID and spending ceiling",
            "no outcome join before source validation plus fresh registry/prereg SHA bind",
            "no HYP-001 amendment, old DESIGN clock shift, threshold rescue or OOS claim",
            "no MQL5, Model 0, promotion, paper or live authority",
        ],
    }
    payload["plan_id"] = compute_plan_id(payload)
    validate_plan(payload)
    return payload


def validate_plan(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise PlanError("source plan schema mismatch")
    if payload.get("candidate_identity") != CANDIDATE_IDENTITY:
        raise PlanError("source plan candidate mismatch")
    if payload.get("input", {}).get("sha256") != CONTROL_SHA256:
        raise PlanError("source plan input hash mismatch")
    if payload.get("input", {}).get("outcome_fields_used") is not False:
        raise PlanError("source plan is not outcome-blind")
    if payload.get("paid_request_made") is not False:
        raise PlanError("source plan reports a paid request")
    if payload.get("download_authorized") is not False:
        raise PlanError("source plan incorrectly authorizes download")
    requests = payload.get("requests", [])
    empty = payload.get("metadata_empty_windows", [])
    if len(requests) + len(empty) != EXPECTED_ROWS:
        raise PlanError("source plan decision coverage mismatch")
    identities: set[tuple[str, str]] = set()
    for item in [*requests, *empty]:
        if item.get("start") != item.get("break_bar_open"):
            raise PlanError("feature start is not the break-bar open")
        if item.get("end") != item.get("actual_decision"):
            raise PlanError("feature end is not the actual decision")
        if int(item.get("duration_seconds", -1)) not in {300, 330}:
            raise PlanError("invalid feature-window duration")
        identity = (str(item.get("position_id")), str(item.get("actual_decision")))
        if identity in identities:
            raise PlanError("duplicate source-plan identity")
        identities.add(identity)
    if payload.get("plan_id") != compute_plan_id(payload):
        raise PlanError("source plan hash mismatch")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        requests = read_design_requests()
        quotes = quote_requests(
            requests,
            client_factory=load_client,
            workers=args.workers,
        )
        plan = build_plan(
            requests,
            quotes,
            quote_provenance={
                "mode": "live_metadata_quote",
                "network_calls": len(requests) * 2,
                "paid_request_made": False,
                "timeseries_calls": 0,
            },
        )
        output = args.output.resolve()
        try:
            output.relative_to((WORKSPACE / "02. AlphaFactory" / "data").resolve())
        except ValueError as exc:
            raise PlanError("source plan output must stay under AlphaFactory data") from exc
        write_json_atomic(output, plan)
        print(
            "CME6E_BREAKBAR_PLAN_OK "
            f"plan_id={plan['plan_id']} decisions={EXPECTED_ROWS} "
            f"billable={len(plan['requests'])} metadata_empty={len(plan['metadata_empty_windows'])} "
            f"estimated_cost_usd={plan['estimated_cost_usd']:.12f} "
            f"recommended_ceiling_usd={plan['recommended_owner_ceiling_usd']:.2f} "
            "paid_request_made=false outcomes_opened=false"
        )
        print(f"plan={output}")
        return 0
    except PlanError as exc:
        print(f"CME6E_BREAKBAR_PLAN_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
