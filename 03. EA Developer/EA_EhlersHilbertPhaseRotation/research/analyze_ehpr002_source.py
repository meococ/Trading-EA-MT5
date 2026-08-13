#!/usr/bin/env python3
"""UTC-corrected, outcome-blind EHPR source-feasibility attempt."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-EHPR-EURUSD-M15-002"
ATTEMPT_ID = "EHPR002-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "3B6C27EFA44267C5B0F8DD170A172A3C00CACBC5F116DA7CDD96A4DF0D8B0AC9"
PARENT_ANALYZER_SHA256 = "2A941BFB3BD36FA7C90BC68FC89CC977C68384BC29E6D1BBCB5671F8D6CB6A32"
REVIEWED_TEST_SHA256 = "EDE42FE82F933A08B95B09EE114BCD8E6ACC844D9DF509D6AC1CB55A431555F4"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8"
SOURCE_START = pd.Timestamp("2015-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2021-01-01T00:00:00Z")


def _load_parent() -> Any:
    path = Path(__file__).with_name("analyze_ehpr_source.py")
    spec = importlib.util.spec_from_file_location("ehpr001_frozen", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen parent analyzer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_parent()
BASE.HYPOTHESIS_ID = HYPOTHESIS_ID
BASE.ATTEMPT_ID = ATTEMPT_ID


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parquet_filters() -> list[tuple[str, str, datetime]]:
    """Return the frozen UTC predicate; never use broker-server source_epoch."""
    return [
        ("time_utc", ">=", SOURCE_START.to_pydatetime()),
        ("time_utc", "<", DESIGN_END.to_pydatetime()),
    ]


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((raw, row))
    if not matches:
        raise ValueError("missing HYP002 registry authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_EHPR002_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "attempt_limit": validation.get("source_feasibility_attempt_limit") == 1,
        "unconsumed": metrics.get("source_feasibility_attempts_consumed") == 0,
        "source_run": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "wrapper": validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "parent": validation.get("frozen_parent_analyzer_sha256") == PARENT_ANALYZER_SHA256,
        "test": validation.get("reviewed_test_sha256") == REVIEWED_TEST_SHA256,
        "no_outcomes": validation.get("outcome_prices_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_mt5": validation.get("mt5_authorized") is False,
        "no_mql5": validation.get("mql5_authorized") is False,
        "no_validation": validation.get("research_validation_access_authorized") is False,
        "no_holdout": validation.get("research_holdout_access_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker_path = output_dir / "attempt_started.json"
    marker = {
        "schema_version": "ehpr_attempt_started.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "process_id": os.getpid(),
        "registry_sha256": authority["registry_sha256"],
        "latest_hypothesis_row_sha256": authority["latest_row_sha256"],
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "frozen_parent_analyzer_sha256": sha256_file(Path(__file__).with_name("analyze_ehpr_source.py")),
        "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED",
    }
    with marker_path.open("xb") as handle:
        handle.write(BASE.json_bytes(marker))
        handle.flush()
        os.fsync(handle.fileno())
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    base_dir = root / "03. EA Developer/EA_EhlersHilbertPhaseRotation/research"
    prereg = base_dir / "HYP-EHPR-EURUSD-M15-002_FROZEN_PREREG.md"
    parent_analyzer = base_dir / "analyze_ehpr_source.py"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet"
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = base_dir / f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"

    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration hash mismatch")
    if sha256_file(parent_analyzer) != PARENT_ANALYZER_SHA256:
        raise ValueError("frozen parent analyzer hash mismatch")
    if sha256_file(manifest) != MANIFEST_SHA256 or sha256_file(data_path) != DATA_SHA256:
        raise ValueError("frozen source hash mismatch")
    BASE.validate_manifest(manifest, data_path)
    authority = validate_registry_authority(registry)
    if not set(BASE.REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("Parquet schema missing required columns")
    started, marker_path = claim_attempt(output_dir, authority)

    raw = pd.read_parquet(
        data_path,
        columns=list(BASE.REQUIRED_COLUMNS),
        filters=parquet_filters(),
        engine="pyarrow",
    )
    m15, resample = BASE.derived_m15_from_m5(raw)
    derived_coverage = resample["complete_m15_bars"] / max(resample["alignable_m15_slots"], 1)
    events, report = BASE.analyze_m15(m15)
    report["resample"] = {**resample, "derived_slot_coverage": derived_coverage}
    report["gates"]["complete_derived_m15_coverage"] = derived_coverage >= BASE.MIN_DERIVED_COVERAGE
    report["all_gates_pass"] = all(report["gates"].values())
    report["verdict"] = "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_MQL5_BASELINE" if report["all_gates_pass"] else "PARK_SOURCE_FEASIBILITY_EXACT_HILBERT_PHASE"
    BASE.assert_outcome_blind(events, report)

    replay_events, replay_report = BASE.analyze_m15(m15)
    replay_report["resample"] = report["resample"]
    replay_report["gates"]["complete_derived_m15_coverage"] = report["gates"]["complete_derived_m15_coverage"]
    replay_report["all_gates_pass"] = all(replay_report["gates"].values())
    replay_report["verdict"] = "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_MQL5_BASELINE" if replay_report["all_gates_pass"] else "PARK_SOURCE_FEASIBILITY_EXACT_HILBERT_PHASE"
    if BASE.jsonl_bytes(events) != BASE.jsonl_bytes(replay_events) or BASE.json_bytes(report) != BASE.json_bytes(replay_report):
        raise ValueError("deterministic replay failed")

    report_bytes = BASE.json_bytes(report)
    ledger_bytes = BASE.jsonl_bytes(events)
    report_path = output_dir / "ehpr_002_source_report.json"
    ledger_path = output_dir / "ehpr_002_event_ledger.jsonl"
    BASE.atomic_write(report_path, report_bytes)
    BASE.atomic_write(ledger_path, ledger_bytes)
    receipt = {
        "schema_version": "ehpr_source_receipt.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": sha256_file(prereg)},
            "manifest": {"path": manifest.relative_to(root).as_posix(), "sha256": sha256_file(manifest)},
            "data": {"path": data_path.relative_to(root).as_posix(), "sha256": sha256_file(data_path)},
            "analyzer": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "frozen_parent_analyzer": {"path": parent_analyzer.relative_to(root).as_posix(), "sha256": sha256_file(parent_analyzer)},
            "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority},
            "attempt_started": {"path": marker_path.relative_to(root).as_posix(), "sha256": sha256_file(marker_path)},
            "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
            "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
        },
        "outcome_blind_counters": report["prohibitions"],
        "verdict": report["verdict"],
    }
    receipt_bytes = BASE.json_bytes(receipt)
    receipt_path = output_dir / "source_feasibility_receipt.json"
    BASE.atomic_write(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "ehpr_attempt_terminal.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": receipt["completed_at_utc"],
        "status": "COMPLETE",
        "verdict": report["verdict"],
        "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    BASE.atomic_write(output_dir / "attempt_terminal.json", BASE.json_bytes(terminal))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    root = Path(__file__).resolve().parents[3]
    print(BASE.json_bytes(execute(root)).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
