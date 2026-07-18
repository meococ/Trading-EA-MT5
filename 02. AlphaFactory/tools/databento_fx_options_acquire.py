#!/usr/bin/env python3
"""Plan, submit, and download a bounded Databento EUR/USD option-chain order.

The default ``plan`` action uses only Databento metadata and symbology APIs,
which Databento documents as free. No time-series request is made until the
Owner supplies an explicit USD ceiling to ``submit``. API keys are never
written to an artifact or printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SCHEMA_VERSION = "databento_fx_options_acquisition.v1"
DATASET = "GLBX.MDP3"
START = "2020-01-02"
END = "2026-07-01"  # Exclusive; contract coverage ends 2026-06-30.
KEY_PATTERN = re.compile(r"^db-[A-Za-z0-9_-]{29}$")

# Current CME MDP 3.0 assets plus legacy premium-quoted roots that may occur
# inside the frozen historical window. Free symbology resolution decides which
# roots actually exist for the account/range before any paid request is made.
OPTION_PARENT_CANDIDATES = tuple(
    ["EUU.OPT"]
    + [f"MO{i}.OPT" for i in range(1, 6)]
    + [f"TU{i}.OPT" for i in range(1, 6)]
    + [f"WE{i}.OPT" for i in range(1, 6)]
    + [f"SU{i}.OPT" for i in range(1, 6)]
    + [f"{i}EU.OPT" for i in range(1, 6)]
    + ["6E.OPT"]
    + [f"6E{i}.OPT" for i in range(1, 6)]
    + ["XT.OPT"]
    + [f"XT{i}.OPT" for i in range(1, 6)]
)
FUTURES_PARENTS = ("6E.FUT",)
REQUIRED_SCHEMAS = ("definition", "statistics")


class AcquisitionError(RuntimeError):
    """Fail-closed acquisition contract error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def ensure_d_workspace(root: Path) -> Path:
    resolved = root.resolve()
    if resolved.drive.upper() != "D:":
        raise AcquisitionError(f"external-data root must be on D:, got {resolved}")
    expected = Path(__file__).resolve().parents[1] / "external"
    try:
        resolved.relative_to(expected.resolve())
    except ValueError as exc:
        raise AcquisitionError(
            f"external-data root must remain under {expected.resolve()}, got {resolved}"
        ) from exc
    return resolved


def read_user_environment(name: str) -> str | None:
    """Read a Windows user environment value without logging it."""

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
            "DATABENTO_API_KEY is absent. Run tools/configure_databento_key.ps1 "
            "locally; never paste the key into chat or a tracked file."
        )
    if not KEY_PATTERN.fullmatch(key.strip()):
        raise AcquisitionError(
            "DATABENTO_API_KEY has an unexpected format; expected a 32-character db- key"
        )
    return key.strip()


def make_client(key: str):
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError(
            "Databento SDK is missing. Use the D-side python-databento runtime."
        ) from exc
    return db.Historical(key)


def resolved_parent_symbols(response: dict[str, Any]) -> list[str]:
    result = response.get("result")
    if not isinstance(result, dict):
        return []
    return sorted(
        symbol
        for symbol in result
        if isinstance(symbol, str) and result.get(symbol)
    )


def request_specs(option_parents: Sequence[str]) -> list[dict[str, Any]]:
    symbols = sorted(set(option_parents) | set(FUTURES_PARENTS))
    return [
        {
            "name": schema,
            "dataset": DATASET,
            "schema": schema,
            "symbols": symbols,
            "stype_in": "parent",
            "start": START,
            "end": END,
        }
        for schema in REQUIRED_SCHEMAS
    ]


def estimate_requests(metadata, specs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    estimates: list[dict[str, Any]] = []
    for spec in specs:
        call = {
            "dataset": spec["dataset"],
            "schema": spec["schema"],
            "symbols": spec["symbols"],
            "stype_in": spec["stype_in"],
            "start": spec["start"],
            "end": spec["end"],
        }
        cost = float(metadata.get_cost(mode="historical", **call))
        size = int(metadata.get_billable_size(**call))
        estimates.append({**spec, "estimated_cost_usd": cost, "billable_size": size})
    return estimates


def _plan_id(payload: dict[str, Any]) -> str:
    stable = {k: v for k, v in payload.items() if k not in {"generated_at_utc", "plan_id"}}
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def build_plan(client) -> dict[str, Any]:
    datasets = client.metadata.list_datasets(start_date=START, end_date=END)
    if DATASET not in datasets:
        raise AcquisitionError(f"account has no visible {DATASET} dataset")

    schemas = client.metadata.list_schemas(dataset=DATASET)
    missing_schemas = [schema for schema in REQUIRED_SCHEMAS if schema not in schemas]
    if missing_schemas:
        raise AcquisitionError(f"{DATASET} is missing schemas: {missing_schemas}")

    symbology = client.symbology.resolve(
        dataset=DATASET,
        symbols=list(OPTION_PARENT_CANDIDATES),
        stype_in="parent",
        stype_out="raw_symbol",
        start_date=START,
        end_date=END,
    )
    option_parents = resolved_parent_symbols(symbology)
    if not option_parents:
        raise AcquisitionError(
            "none of the official CME EUR/USD option parent roots resolved"
        )

    specs = request_specs(option_parents)
    estimates = estimate_requests(client.metadata, specs)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "ESTIMATED_NOT_SUBMITTED",
        "dataset": DATASET,
        "coverage": {"start_inclusive": START, "end_exclusive": END},
        "account_check": {
            "dataset_visible": True,
            "required_schemas_present": True,
            "available_range": client.metadata.get_dataset_range(dataset=DATASET),
        },
        "symbology": {
            "candidate_parents": list(OPTION_PARENT_CANDIDATES),
            "resolved_option_parents": option_parents,
            "not_found": symbology.get("not_found", []),
            "partial": symbology.get("partial", []),
        },
        "requests": estimates,
        "estimated_total_usd": sum(item["estimated_cost_usd"] for item in estimates),
        "estimated_total_billable_size": sum(item["billable_size"] for item in estimates),
        "charging_rule": (
            "No paid time-series call has been made. Submit requires an explicit "
            "Owner USD ceiling and re-estimates cost immediately before submission."
        ),
        "api_key_stored": False,
    }
    payload["plan_id"] = _plan_id(payload)
    return payload


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AcquisitionError(f"expected JSON object in {path}")
    return value


def extract_job_id(response: dict[str, Any]) -> str:
    for key in ("id", "job_id"):
        value = response.get(key)
        if isinstance(value, str) and value:
            return value
    raise AcquisitionError(f"Databento submit response has no job identifier: {response}")


def submit_plan(
    client,
    plan: dict[str, Any],
    approved_max_usd: float,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AcquisitionError("unsupported or missing acquisition plan schema")
    if plan.get("plan_id") != _plan_id(plan):
        raise AcquisitionError("acquisition plan hash mismatch")
    if approved_max_usd <= 0:
        raise AcquisitionError("approved USD ceiling must be positive")

    specs = [
        {key: item[key] for key in ("name", "dataset", "schema", "symbols", "stype_in", "start", "end")}
        for item in plan.get("requests", [])
    ]
    estimates = estimate_requests(client.metadata, specs)
    live_total = sum(item["estimated_cost_usd"] for item in estimates)
    if live_total > approved_max_usd:
        raise AcquisitionError(
            f"live estimate ${live_total:.6f} exceeds approved ceiling ${approved_max_usd:.6f}"
        )

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "SUBMITTING",
        "plan_id": plan["plan_id"],
        "approved_max_usd": approved_max_usd,
        "live_estimated_total_usd": live_total,
        "jobs": [],
        "api_key_stored": False,
    }
    for spec in estimates:
        response = client.batch.submit_job(
            dataset=spec["dataset"],
            symbols=spec["symbols"],
            schema=spec["schema"],
            start=spec["start"],
            end=spec["end"],
            encoding="csv",
            compression="zstd",
            pretty_px=True,
            pretty_ts=True,
            map_symbols=True,
            split_symbols=False,
            split_duration="month",
            delivery="download",
            stype_in=spec["stype_in"],
            stype_out="raw_symbol",
        )
        job = {
            "name": spec["name"],
            "job_id": extract_job_id(response),
            "estimated_cost_usd": spec["estimated_cost_usd"],
            "submit_response": response,
        }
        result["jobs"].append(job)
        if on_progress:
            on_progress(result)
    result["status"] = "SUBMITTED_NOT_DOWNLOADED"
    return result


def download_jobs(client, jobs: dict[str, Any], root: Path) -> dict[str, Any]:
    if jobs.get("schema_version") != SCHEMA_VERSION:
        raise AcquisitionError("unsupported or missing jobs manifest schema")
    downloaded: list[dict[str, Any]] = []
    for item in jobs.get("jobs", []):
        job_id = item.get("job_id")
        name = item.get("name")
        if not isinstance(job_id, str) or not isinstance(name, str):
            raise AcquisitionError("jobs manifest contains an invalid entry")
        details = client.batch.get_job_details(job_id=job_id)
        state = str(details.get("state") or details.get("status") or "").lower()
        if state not in {"done", "completed", "success"} and details.get("progress") != 100:
            raise AcquisitionError(f"job {job_id} is not complete: {state or details}")
        output = root / "raw" / "databento" / name
        files = client.batch.download(job_id=job_id, output_dir=output)
        downloaded.append(
            {"name": name, "job_id": job_id, "files": [str(Path(p)) for p in files]}
        )
    return {
        **jobs,
        "updated_at_utc": utc_now(),
        "status": "DOWNLOADED_RAW_VALIDATION_REQUIRED",
        "downloads": downloaded,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    alpha_root = Path(__file__).resolve().parents[1]
    default_root = alpha_root / "external" / "cme_fx_options_euro"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "submit", "download"))
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--approve-max-usd", type=float)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = ensure_d_workspace(args.root)
        root.mkdir(parents=True, exist_ok=True)
        key = load_api_key()
        client = make_client(key)
        plan_path = root / "databento_cost_plan.json"
        jobs_path = root / "databento_jobs.json"
        if args.action == "plan":
            plan = build_plan(client)
            write_json_atomic(plan_path, plan)
            print(
                "DATABENTO_PLAN "
                f"status={plan['status']} cost_usd={plan['estimated_total_usd']:.6f} "
                f"billable_bytes={plan['estimated_total_billable_size']}"
            )
            print(f"plan={plan_path}")
            return 0
        if args.action == "submit":
            if args.approve_max_usd is None:
                raise AcquisitionError("submit requires --approve-max-usd")
            plan = load_json(plan_path)

            def checkpoint(payload: dict[str, Any]) -> None:
                write_json_atomic(jobs_path, payload)

            jobs = submit_plan(client, plan, args.approve_max_usd, checkpoint)
            write_json_atomic(jobs_path, jobs)
            print(
                f"DATABENTO_SUBMIT status={jobs['status']} jobs={len(jobs['jobs'])} "
                f"live_estimate_usd={jobs['live_estimated_total_usd']:.6f}"
            )
            print(f"jobs={jobs_path}")
            return 0
        jobs = load_json(jobs_path)
        result = download_jobs(client, jobs, root)
        write_json_atomic(jobs_path, result)
        print(
            f"DATABENTO_DOWNLOAD status={result['status']} "
            f"jobs={len(result.get('downloads', []))}"
        )
        print(f"jobs={jobs_path}")
        return 0
    except AcquisitionError as exc:
        print(f"DATABENTO_ACQUISITION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
