#!/usr/bin/env python3
"""Build the one-shot outcome-blind full-bar ST003 Supertrend parity oracle."""

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


HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
ATTEMPT_ID = "ST003-ORACLE-001"
PREREG_SHA256 = "D82037A5730F0766EE872C3A3D1DB5AAB9DA3BD69BADC08B1323446B1FDF924D"
DEPENDENCY_SHA256 = "9B44FDCFEA2BC944E4CC70B3C0C9D92E0899BC6F4A9EDE1ECE4AF933F20EAF3B"
FORMULA_SHA256 = "2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
SOURCE_START = pd.Timestamp("2004-06-11T04:00:00Z")
REQUIRED_COLUMNS = (
    "symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous",
    "high", "low", "close",
)
ORACLE_KEYS = {
    "schema_version", "hypothesis_id", "source_epoch", "time_utc", "atr10",
    "final_upper", "final_lower", "supertrend", "prior_state", "state",
    "raw_event", "next_source_epoch", "exact_next", "executable_event", "direction",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_hash_bound_module(name: str, path: Path, expected_sha256: str) -> Any:
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"{name} SHA mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACKAGE_ROOT = Path(__file__).resolve().parent
DEPENDENCY_PATH = PACKAGE_ROOT / "analyze_supertrend_flatbar_source.py"
CLOCK_PATH = Path(__file__).resolve().parents[3] / "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
DEPENDENCY = load_hash_bound_module("st002_dependency", DEPENDENCY_PATH, DEPENDENCY_SHA256)
CLOCK = load_hash_bound_module("fivepercent_server_clock", CLOCK_PATH, CLOCK_SHA256)


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def finite_float(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("oracle contains non-finite indicator output")
    return result


def validate_clock_mapping(source_epoch: int, time_utc: pd.Timestamp) -> None:
    server_naive = datetime.fromtimestamp(source_epoch, tz=timezone.utc).replace(tzinfo=None)
    mapped = CLOCK.server_to_utc(server_naive).replace(tzinfo=timezone.utc)
    if mapped != time_utc.to_pydatetime():
        raise ValueError(f"server clock mapping mismatch at source_epoch={source_epoch}")


def is_exact_next(source_epoch: int, next_source_epoch: int) -> bool:
    """Frozen execution adjacency uses the primary native server/source epoch."""
    return next_source_epoch == source_epoch + 3600


def build_oracle_rows(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    for column in ("source_epoch",):
        data[column] = pd.to_numeric(data[column], errors="raise").astype("int64")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    indicator = DEPENDENCY.calculate_supertrend(data)
    states = indicator["state"]
    prior = np.roll(states, 1)
    prior[0] = 0
    feature = indicator["feature_valid"]
    design = ((data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)).to_numpy()
    comparable = design & feature
    comparable[-1] = False
    rows: list[dict[str, Any]] = []
    raw_count = 0
    executable_count = 0
    long_count = 0
    short_count = 0
    gap_event_count = 0
    for index in np.flatnonzero(comparable):
        source_epoch = int(data.at[index, "source_epoch"])
        next_epoch = int(data.at[index + 1, "source_epoch"])
        validate_clock_mapping(source_epoch, data.at[index, "time_utc"])
        raw_event = bool(prior[index] != 0 and prior[index] != states[index])
        exact_next = is_exact_next(source_epoch, next_epoch)
        executable = raw_event and exact_next
        direction = ""
        if raw_event:
            raw_count += 1
            direction = "LONG" if states[index] == DEPENDENCY.UP else "SHORT"
            if not exact_next:
                gap_event_count += 1
        if executable:
            executable_count += 1
            if direction == "LONG":
                long_count += 1
            else:
                short_count += 1
        rows.append({
            "schema_version": "st003_source_parity_oracle.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "source_epoch": source_epoch,
            "time_utc": data.at[index, "time_utc"].isoformat().replace("+00:00", "Z"),
            "atr10": finite_float(indicator["atr"][index]),
            "final_upper": finite_float(indicator["upper"][index]),
            "final_lower": finite_float(indicator["lower"][index]),
            "supertrend": finite_float(indicator["supertrend"][index]),
            "prior_state": "UP" if prior[index] == DEPENDENCY.UP else "DOWN",
            "state": "UP" if states[index] == DEPENDENCY.UP else "DOWN",
            "raw_event": int(raw_event),
            "next_source_epoch": next_epoch,
            "exact_next": int(exact_next),
            "executable_event": int(executable),
            "direction": direction,
        })
    report = {
        "schema_version": "st003_source_parity_oracle_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "source_rows": int(len(data)),
        "design_rows": int(design.sum()),
        "oracle_comparable_rows": len(rows),
        "raw_events": raw_count,
        "executable_events": executable_count,
        "gap_rejected_events": gap_event_count,
        "long_events": long_count,
        "short_events": short_count,
        "outcome_fields_emitted": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
    }
    return rows, report


def validate_oracle(rows: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in rows:
        if set(row) != ORACLE_KEYS:
            raise ValueError("oracle schema differs from exact allowlist")
    epochs = [row["source_epoch"] for row in rows]
    if epochs != sorted(set(epochs)):
        raise ValueError("oracle source_epoch must be unique and increasing")
    expected = {
        "source_rows": 107679,
        "design_rows": 29461,
        "oracle_comparable_rows": 29460,
        "raw_events": 690,
        "executable_events": 683,
        "gap_rejected_events": 7,
        "long_events": 339,
        "short_events": 344,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError(f"frozen parent invariant mismatch: {key}")


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing ST003 registry authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "probe": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_MQL5_PARITY_ORACLE_BUILD_AUTHORIZED",
        "parent": row.get("parent_candidate") == "HYP-ST-XAUUSD-H1-002",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "attempt": validation.get("oracle_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("oracle_attempt_limit") == 1,
        "unconsumed": metrics.get("oracle_attempts_consumed") == 0,
        "oracle": validation.get("oracle_run_authorized") is True,
        "builder": validation.get("reviewed_oracle_builder_sha256") == sha256_file(Path(__file__).resolve()),
        "dependency": validation.get("formula_dependency_sha256") == FORMULA_SHA256,
        "no_outcomes": validation.get("outcome_prices_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_mt5": validation.get("mt5_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
    }
    failed = [key for key, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"ST003 oracle authority failed: {failed}")
    return {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("oracle attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / "attempt_started.json"
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = {
        "schema_version": "st003_oracle_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "started_at_utc": started, "process_id": os.getpid(),
        "registry_sha256": authority["registry_sha256"],
        "latest_hypothesis_row_sha256": authority["latest_row_sha256"],
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED",
    }
    try:
        with marker_path.open("xb") as handle:
            handle.write(json_bytes(marker))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("oracle attempt already claimed") from exc
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-003_MQL5_PARITY_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("ST003 preregistration SHA mismatch")
    if sha256_file(DEPENDENCY.FORMULA_DEPENDENCY_PATH) != FORMULA_SHA256:
        raise ValueError("ST001 formula dependency SHA mismatch")
    authority = validate_registry_authority(registry)
    started, marker_path = claim_attempt(output_dir, authority)
    DEPENDENCY.validate_manifest(manifest, data_path)
    if sha256_file(manifest) != MANIFEST_SHA256 or sha256_file(data_path) != DATA_SHA256:
        raise ValueError("manifest/data SHA mismatch")
    if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("source schema missing oracle columns")
    raw = pd.read_parquet(
        data_path, columns=list(REQUIRED_COLUMNS),
        filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow",
    )
    selected = DEPENDENCY.validate_selected_frame(raw)
    rows, report = build_oracle_rows(selected)
    validate_oracle(rows, report)
    replay_rows, replay_report = build_oracle_rows(selected)
    if jsonl_bytes(rows) != jsonl_bytes(replay_rows) or json_bytes(report) != json_bytes(replay_report):
        raise ValueError("oracle deterministic replay failed")
    oracle_bytes = jsonl_bytes(rows)
    report_bytes = json_bytes(report)
    oracle_path = output_dir / "st003_source_parity_oracle.jsonl"
    report_path = output_dir / "st003_source_parity_oracle_report.json"
    atomic_write(oracle_path, oracle_bytes)
    atomic_write(report_path, report_bytes)
    completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema_version": "st003_source_parity_oracle_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "started_at_utc": started, "completed_at_utc": completed,
        "bindings": {
            "preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": sha256_file(prereg)},
            "builder": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "st002_dependency": {"path": DEPENDENCY_PATH.relative_to(root).as_posix(), "sha256": sha256_file(DEPENDENCY_PATH)},
            "formula_dependency": {"path": DEPENDENCY.FORMULA_DEPENDENCY_PATH.relative_to(root).as_posix(), "sha256": sha256_file(DEPENDENCY.FORMULA_DEPENDENCY_PATH)},
            "clock_model": {"path": CLOCK_PATH.relative_to(root).as_posix(), "sha256": sha256_file(CLOCK_PATH)},
            "manifest": {"path": manifest.relative_to(root).as_posix(), "sha256": sha256_file(manifest)},
            "data": {"path": data_path.relative_to(root).as_posix(), "sha256": sha256_file(data_path)},
            "registry": {"path": registry.relative_to(root).as_posix(), **authority},
            "attempt_started": {"path": marker_path.relative_to(root).as_posix(), "sha256": sha256_file(marker_path)},
            "oracle": {"path": oracle_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(oracle_bytes).hexdigest().upper()},
            "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
        },
        "outcome_blind_counters": {
            "outcome_fields_emitted": 0, "returns_computed": 0, "trades_simulated": 0,
            "pnl_computed": 0, "performance_metrics_computed": 0,
            "validation_rows_read": 0, "holdout_rows_read": 0,
        },
        "verdict": "ORACLE_BUILD_PASS",
    }
    receipt_bytes = json_bytes(receipt)
    receipt_path = output_dir / "oracle_receipt.json"
    atomic_write(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "st003_source_parity_oracle_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "completed_at_utc": completed, "status": "COMPLETE", "verdict": "ORACLE_BUILD_PASS",
        "oracle_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    atomic_write(output_dir / "attempt_terminal.json", json_bytes(terminal))
    return {"report": report, "output_dir": str(output_dir)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = execute(Path(__file__).resolve().parents[3])
    print(json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
