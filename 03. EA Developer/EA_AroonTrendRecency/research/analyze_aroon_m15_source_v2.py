#!/usr/bin/env python3
"""Outcome-blind vectorized XAUUSD M15 Aroon-25 source analyzer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "analyze_aroon_m15_source.py"
BASE_SHA256 = "6E2383CE15074890905AFC6AAF2E6D0D9893FBDE8B414850F28F12A08F100CF0"
SPEC = importlib.util.spec_from_file_location("aroon001_formula_contract", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen Aroon formula dependency")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

HYPOTHESIS_ID = "HYP-AROON-XAUUSD-M15-002"
PARENT_HYPOTHESIS_ID = "HYP-AROON-XAUUSD-M15-001"
PARENT_TERMINAL_ROW_SHA256 = "1B13776D3436F2C192B85EF5B3968323632D0E08A3CC841736B3E9EF198665F3"
PARENT_FAILURE_SHA256 = "9F830B1363FFE1E3EF1A53C64AEE8245708436267B3008A97D67C57DBE4003A9"
PARENT_REVIEW_SHA256 = "041874A8DCA0059CB23BF400986D948027A22684A2B85B6F0B51B922004A6AC0"
PARENT_START_SHA256 = "E2F0D692D0A0602E8C04200205C1ACAEBCB2900FAFD738253D275A3CD38AFE7E"
SEMANTIC_DIFF_SHA256 = "4317E63CA2996E1B391A2B41C90E80D54ED18F440B46B401072514558F65D5B6"
ATTEMPT_ID = "AROON002-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "4EF5AA1BA1DC97358716D5C230AE88652C2615C11C1972126A13BE2CA4845326"
TEST_SHA256 = "F9E9A8E2578994B159166A72F1D85A6E2DD171AD7A54A82E6EB61B5141C28B99"
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/analyze_aroon_m15_source_v2.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/tests/test_analyze_aroon_m15_source_v2.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/HYP-AROON-XAUUSD-M15-002_FROZEN_PREREG.md"
PARENT_FAILURE_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/HYP-AROON-XAUUSD-M15-001_ENGINEERING_TIMEOUT.md"
PARENT_REVIEW_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/HYP-AROON-XAUUSD-M15-001_POST_FAILURE_REVIEW.md"
PARENT_START_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/evidence/HYP-AROON-XAUUSD-M15-001/AROON001-SOURCE-ATTEMPT-001/attempt_started.json"
SEMANTIC_DIFF_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/HYP-AROON-XAUUSD-M15-002_AGGREGATION_SEMANTIC_DIFF.md"


def sha256_file(path: Path) -> str:
    return BASE.sha256_file(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = BASE.json_bytes(payload)
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError(f"exclusive artifact already exists: {path.name}") from exc


def verify_frozen_inputs(paths: dict[str, Path], expected: dict[str, str]) -> dict[str, str]:
    if set(paths) != set(expected):
        raise ValueError("frozen input labels differ from expected labels")
    observed = {name: sha256_file(path) for name, path in paths.items()}
    mismatches = sorted(name for name, digest in observed.items() if digest != expected[name])
    if mismatches:
        raise ValueError(f"frozen input SHA mismatch: {mismatches}")
    return observed


def phase(output_dir: Path, number: int, name: str, started: str, **details: Any) -> Path:
    path = output_dir / f"phase_{number:02d}_{name}.json"
    exclusive_json(
        path,
        {
            "schema_version": "aroon002_source_phase.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "recorded_at_utc": utc_now(),
            "phase": name,
            "details": details,
        },
    )
    return path


def aggregate_m15_vectorized(data: pd.DataFrame) -> pd.DataFrame:
    work = data.copy().sort_values(["source_epoch", "time_utc"], kind="stable").reset_index(drop=True)
    work["bucket_epoch"] = (work["source_epoch"].astype(np.int64) // 900) * 900
    grouped = work.groupby("bucket_epoch", sort=True, observed=True)
    work["slot"] = grouped.cumcount().astype(np.int64)
    time_ns = work["time_utc"].astype("int64")
    first_time_ns = time_ns.groupby(work["bucket_epoch"], sort=True).transform("first")
    exact_epoch = work["source_epoch"].astype(np.int64).eq(work["bucket_epoch"] + work["slot"] * 300)
    exact_utc = time_ns.eq(first_time_ns + work["slot"] * 300 * 1_000_000_000)
    prices = work.loc[:, ["high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    price_valid = (
        np.isfinite(prices.to_numpy(dtype=float)).all(axis=1)
        & prices["high"].ge(prices["low"])
        & prices["close"].ge(prices["low"])
        & prices["close"].le(prices["high"])
        & prices["close"].gt(0.0)
    )
    work["row_contract"] = exact_epoch & exact_utc & price_valid
    summary = grouped.agg(
        row_count=("source_epoch", "size"),
        time_utc=("time_utc", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        row_contract=("row_contract", "all"),
    ).reset_index()
    summary["complete"] = summary["row_count"].eq(3) & summary["row_contract"].astype(bool)
    invalid = ~summary["complete"]
    summary.loc[invalid, ["high", "low", "close"]] = math.nan
    result = pd.DataFrame(
        {
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "source_epoch": summary["bucket_epoch"].astype(np.int64),
            "time_utc": summary["time_utc"],
            "complete": summary["complete"].astype(bool),
            "high": pd.to_numeric(summary["high"], errors="coerce"),
            "low": pd.to_numeric(summary["low"], errors="coerce"),
            "close": pd.to_numeric(summary["close"], errors="coerce"),
        }
    )
    if result.empty or result.at[0, "time_utc"] != BASE.SOURCE_START:
        raise ValueError("vectorized M15 frame does not preserve frozen inception")
    return result.reset_index(drop=True)


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    registry_bytes = registry_path.read_bytes()
    current: list[tuple[bytes, dict[str, Any]]] = []
    parents: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_bytes.splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            current.append((raw, row))
        elif row.get("hypothesis_id") == PARENT_HYPOTHESIS_ID:
            parents.append((raw, row))
    if not current or not parents:
        raise ValueError("missing current or parent registry authority")
    parent_raw, parent = parents[-1]
    if hashlib.sha256(parent_raw).hexdigest().upper() != PARENT_TERMINAL_ROW_SHA256 or parent.get("state") != "parked" or parent.get("verdict") != "PARK_ENGINEERING_TIMEOUT_BEFORE_SOURCE_REPORT_NO_ECONOMIC_VERDICT":
        raise ValueError("parent terminal row mismatch")
    raw, row = current[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "probe": row.get("state") == "probe",
        "parent": row.get("parent_candidate") == PARENT_HYPOTHESIS_ID,
        "verdict": row.get("verdict") == "FROZEN_VECTORIZED_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "run_ids": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "one_attempt": validation.get("source_feasibility_attempt_limit") == 1,
        "source_run": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "prehistory": validation.get("prehistory_source_access_authorized") is True,
        "prehistory_start": validation.get("prehistory_source_start") == BASE.SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest_path": validation.get("manifest_path") == BASE.MANIFEST_RELATIVE_PATH,
        "manifest_sha": validation.get("manifest_sha256") == BASE.MANIFEST_SHA256,
        "data_path": validation.get("data_path") == BASE.DATA_RELATIVE_PATH,
        "data_sha": validation.get("data_sha256") == BASE.DATA_SHA256,
        "data_predicate": validation.get("data_access_predicate") == BASE.DATA_ACCESS_PREDICATE,
        "analyzer_path": validation.get("reviewed_analyzer_path") == ANALYZER_RELATIVE_PATH,
        "analyzer_sha": validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "test_path": validation.get("reviewed_test_path") == TEST_RELATIVE_PATH,
        "test_sha": validation.get("reviewed_test_sha256") == TEST_SHA256,
        "formula_path": validation.get("formula_dependency_path") == BASE.ANALYZER_RELATIVE_PATH,
        "formula_sha": validation.get("formula_dependency_sha256") == BASE_SHA256,
        "parent_row": validation.get("parent_terminal_row_sha256") == PARENT_TERMINAL_ROW_SHA256,
        "parent_start": validation.get("parent_attempt_started_sha256") == PARENT_START_SHA256,
        "parent_failure": validation.get("parent_failure_sha256") == PARENT_FAILURE_SHA256,
        "parent_review": validation.get("parent_post_failure_review_sha256") == PARENT_REVIEW_SHA256,
        "semantic_diff": validation.get("aggregation_semantic_diff_sha256") == SEMANTIC_DIFF_SHA256,
        "zero_metrics": all(metrics.get(name) == 0 for name in BASE.ZERO_METRICS),
        "validation_closed": metrics.get("research_validation_opened") is False,
        "holdout_closed": metrics.get("research_holdout_opened") is False,
        "false_permissions": all(validation.get(name) is False for name in BASE.FALSE_PERMISSIONS),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest().upper(),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "parent_terminal_row_sha256": hashlib.sha256(parent_raw).hexdigest().upper(),
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
    }


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    marker_path = output_dir / "attempt_started.json"
    exclusive_json(
        marker_path,
        {
            "schema_version": "aroon002_source_attempt_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "process_id": os.getpid(),
            "registry_sha256": authority["registry_sha256"],
            "latest_hypothesis_row_sha256": authority["latest_row_sha256"],
            "parent_terminal_row_sha256": authority["parent_terminal_row_sha256"],
            "analyzer_sha256": sha256_file(Path(__file__).resolve()),
            "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED",
        },
    )
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg = root / PREREG_RELATIVE_PATH
    manifest = root / BASE.MANIFEST_RELATIVE_PATH
    data_path = root / BASE.DATA_RELATIVE_PATH
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_AroonTrendRecency/research/evidence/HYP-AROON-XAUUSD-M15-002/AROON002-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    try:
        bound = {
            "preregistration": prereg,
            "manifest": manifest,
            "data": data_path,
            "analyzer": Path(__file__).resolve(),
            "tests": root / TEST_RELATIVE_PATH,
            "formula_dependency": BASE_PATH,
            "parent_start": root / PARENT_START_RELATIVE_PATH,
            "parent_failure": root / PARENT_FAILURE_RELATIVE_PATH,
            "parent_review": root / PARENT_REVIEW_RELATIVE_PATH,
            "semantic_diff": root / SEMANTIC_DIFF_RELATIVE_PATH,
        }
        expected = {
            "preregistration": PREREG_SHA256,
            "manifest": BASE.MANIFEST_SHA256,
            "data": BASE.DATA_SHA256,
            "analyzer": authority["analyzer_sha256"],
            "tests": TEST_SHA256,
            "formula_dependency": BASE_SHA256,
            "parent_start": PARENT_START_SHA256,
            "parent_failure": PARENT_FAILURE_SHA256,
            "parent_review": PARENT_REVIEW_SHA256,
            "semantic_diff": SEMANTIC_DIFF_SHA256,
        }
        verify_frozen_inputs(bound, expected)
        BASE.validate_manifest(manifest, data_path)
        if sha256_file(data_path) != BASE.DATA_SHA256:
            raise ValueError("M5 data SHA mismatch")
        if not set(BASE.REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
            raise ValueError("Parquet schema missing required columns")
        phase(output_dir, 2, "hash_schema_verified", started, manifest_sha256=BASE.MANIFEST_SHA256, data_sha256=BASE.DATA_SHA256)
        raw = pd.read_parquet(data_path, columns=list(BASE.REQUIRED_COLUMNS), filters=[("time_utc", "<", BASE.DESIGN_END.to_pydatetime())], engine="pyarrow")
        selected = BASE.validate_m5_frame(raw)
        phase(output_dir, 3, "source_read", started, source_rows=int(len(selected)))
        aggregated = aggregate_m15_vectorized(selected)
        phase(output_dir, 4, "aggregation_complete", started, represented_m15_rows=int(len(aggregated)), complete_m15_rows=int(aggregated["complete"].sum()))
        BASE.HYPOTHESIS_ID = HYPOTHESIS_ID
        BASE.ATTEMPT_ID = ATTEMPT_ID
        events, report = BASE.analyze_frame(aggregated)
        BASE.assert_outcome_blind(events, report)
        replay_events, replay_report = BASE.analyze_frame(aggregated)
        if BASE.jsonl_bytes(events) != BASE.jsonl_bytes(replay_events) or BASE.json_bytes(report) != BASE.json_bytes(replay_report):
            raise ValueError("deterministic replay failed")
        phase(output_dir, 5, "analysis_complete", started, raw_events=int(report["funnel"]["raw_events"]), executable_events=int(report["funnel"]["executable_events"]))
        final_hashes = verify_frozen_inputs(bound, expected)
        report_bytes = BASE.json_bytes(report)
        ledger_bytes = BASE.jsonl_bytes(events)
        report_path = output_dir / "aroon_002_source_report.json"
        ledger_path = output_dir / "aroon_002_event_ledger.jsonl"
        BASE.atomic_write(report_path, report_bytes)
        BASE.atomic_write(ledger_path, ledger_bytes)
        phase_paths = sorted(output_dir.glob("phase_*.json"))
        receipt = {
            "schema_version": "aroon002_source_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "completed_at_utc": utc_now(),
            "bindings": {
                "preregistration": {"path": PREREG_RELATIVE_PATH, "sha256": final_hashes["preregistration"]},
                "manifest": {"path": BASE.MANIFEST_RELATIVE_PATH, "sha256": final_hashes["manifest"]},
                "data": {"path": BASE.DATA_RELATIVE_PATH, "sha256": final_hashes["data"]},
                "analyzer": {"path": ANALYZER_RELATIVE_PATH, "sha256": final_hashes["analyzer"]},
                "tests": {"path": TEST_RELATIVE_PATH, "sha256": final_hashes["tests"]},
                "formula_dependency": {"path": BASE.ANALYZER_RELATIVE_PATH, "sha256": final_hashes["formula_dependency"]},
                "parent_start": {"path": PARENT_START_RELATIVE_PATH, "sha256": final_hashes["parent_start"]},
                "parent_failure": {"path": PARENT_FAILURE_RELATIVE_PATH, "sha256": final_hashes["parent_failure"]},
                "parent_review": {"path": PARENT_REVIEW_RELATIVE_PATH, "sha256": final_hashes["parent_review"]},
                "semantic_diff": {"path": SEMANTIC_DIFF_RELATIVE_PATH, "sha256": final_hashes["semantic_diff"]},
                "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority},
                "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)},
                "phases": [{"path": item.relative_to(root).as_posix(), "sha256": sha256_file(item)} for item in phase_paths],
                "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
                "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
            },
            "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0},
            "verdict": report["verdict"],
        }
        receipt_bytes = BASE.json_bytes(receipt)
        receipt_path = output_dir / "source_feasibility_receipt.json"
        BASE.atomic_write(receipt_path, receipt_bytes)
        terminal = {
            "schema_version": "aroon002_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": receipt["completed_at_utc"],
            "status": "COMPLETE",
            "verdict": report["verdict"],
            "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
            "attempt_started_sha256": sha256_file(start_path),
            "same_id_retry_authorized": False,
        }
        exclusive_json(output_dir / "attempt_terminal.json", terminal)
        return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}
    except Exception as exc:
        terminal_path = output_dir / "attempt_terminal.json"
        if not terminal_path.exists():
            exclusive_json(
                terminal_path,
                {
                    "schema_version": "aroon002_source_attempt_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "completed_at_utc": utc_now(),
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempt_started_sha256": sha256_file(start_path),
                    "created_artifacts": [item.name for item in sorted(output_dir.iterdir())],
                    "same_id_retry_authorized": False,
                },
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = execute(Path(__file__).resolve().parents[3])
    print(BASE.json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
