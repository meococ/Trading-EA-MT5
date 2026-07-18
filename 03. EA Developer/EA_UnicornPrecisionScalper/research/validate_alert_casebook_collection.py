#!/usr/bin/env python3
"""Validate one run-bound, zero-outcome Unicorn alert casebook collection."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


LABEL_COLUMNS = (
    "label_true_sweep_liquidity",
    "label_true_displacement",
    "label_true_mss_bos_close",
    "label_true_breaker_valid",
    "label_fvg_fresh_unfilled",
    "label_micro_confirm_present",
    "label_trade_quality_accept",
    "reject_reason",
    "reviewer_id",
    "label_time_utc",
)

SOURCE_CONTRACTS = {
    "UPS_ALERT_FIRST_CASEBOOK_V1_3": {
        "collection_id": "DATA-ACQ-UNICORN-CASEBOOK-V1-002",
        "required_columns": set(),
        "required_meta": set(),
    },
    "UPS_ALERT_FIRST_CASEBOOK_V1_4": {
        "collection_id": "DATA-ACQ-UNICORN-CASEBOOK-V1-003",
        "required_columns": {"m15_structure"},
        "required_meta": {"structure_pivot_strength"},
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def exactly_one(paths: list[Path], label: str) -> Path:
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {label}; found {len(paths)}")
    return paths[0]


def validate(run_dir: Path, min_rows: int = 100, max_rows: int = 200) -> dict[str, object]:
    run_dir = run_dir.resolve()
    logs = run_dir / "logs"
    main_csv = exactly_one(sorted(logs.glob("XAUUSD_AlertCasebook_*.csv")), "casebook CSV")
    meta_csv = exactly_one(sorted(logs.glob("XAUUSD_AlertCasebookMeta_*.csv")), "metadata CSV")
    rows = read_rows(main_csv)
    meta_rows = read_rows(meta_csv)
    if not min_rows <= len(rows) <= max_rows:
        raise ValueError(f"casebook rows {len(rows)} outside [{min_rows}, {max_rows}]")
    if len(meta_rows) != 1:
        raise ValueError(f"metadata must contain one row; found {len(meta_rows)}")
    meta = meta_rows[0]
    source_contract = meta.get("source_contract_id", "")
    contract = SOURCE_CONTRACTS.get(source_contract)
    if contract is None:
        raise ValueError("metadata source contract mismatch")

    required = {
        "schema_version",
        "contract_id",
        "source_contract_id",
        "source_sha256",
        "run_id",
        "event_id",
        "decision_time_utc",
        "symbol",
        *LABEL_COLUMNS,
        *contract["required_columns"],
    }
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"casebook columns missing: {sorted(missing)}")

    event_ids: set[str] = set()
    run_ids: set[str] = set()
    source_hashes: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if row["schema_version"] != "alert_first_casebook.v1":
            raise ValueError(f"row {index} schema mismatch")
        if row["contract_id"] != "ALERT_FIRST_CASEBOOK_V1":
            raise ValueError(f"row {index} contract mismatch")
        if row["source_contract_id"] != source_contract:
            raise ValueError(f"row {index} source contract mismatch")
        source_hash = row["source_sha256"].strip().upper()
        if len(source_hash) != 64 or any(char not in "0123456789ABCDEF" for char in source_hash):
            raise ValueError(f"row {index} source SHA256 is invalid")
        if row["symbol"] != "XAUUSD":
            raise ValueError(f"row {index} symbol mismatch")
        if source_contract.endswith("V1_4") and row.get("m15_structure") not in {"-1", "0", "1"}:
            raise ValueError(f"row {index} M15 structure state is invalid")
        if any((row.get(column) or "").strip() for column in LABEL_COLUMNS):
            raise ValueError(f"row {index} contains a prefilled human label or outcome field")
        event_id = row["event_id"].strip()
        if not event_id or event_id in event_ids:
            raise ValueError(f"row {index} has missing or duplicate event_id")
        event_ids.add(event_id)
        run_ids.add(row["run_id"].strip())
        source_hashes.add(source_hash)

    if len(run_ids) != 1 or meta.get("run_id", "").strip() not in run_ids:
        raise ValueError("casebook and metadata run_id mismatch")
    if meta.get("contract_id") != "ALERT_FIRST_CASEBOOK_V1":
        raise ValueError("metadata contract mismatch")
    missing_meta = contract["required_meta"].difference(meta)
    if missing_meta:
        raise ValueError(f"metadata columns missing: {sorted(missing_meta)}")
    meta_source_hash = meta.get("source_sha256", "").strip().upper()
    if len(source_hashes) != 1 or meta_source_hash not in source_hashes:
        raise ValueError("casebook and metadata source SHA256 mismatch")
    if meta.get("period") not in {"M5", "PERIOD_M5"}:
        raise ValueError("metadata period is not M5")
    if not meta.get("terminal_data_path", "").lower().startswith("d:\\"):
        raise ValueError("metadata terminal_data_path is not on D drive")
    if meta.get("casebook_max_rows") != str(max_rows):
        raise ValueError("metadata max-row contract mismatch")
    if source_contract.endswith("V1_4") and meta.get("structure_pivot_strength") != "2":
        raise ValueError("metadata M15 pivot-strength contract mismatch")

    summary_path = run_dir / "analysis" / "enhanced_summary.json"
    manifest_path = run_dir / "run_manifest.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if int(summary.get("n_trades", -1)) != 0:
        raise ValueError("Strategy Tester run was not zero-trade")
    if manifest.get("hypothesis_id") != contract["collection_id"]:
        raise ValueError("run manifest collection id mismatch")
    manifest_source_hash = str(manifest.get("source_sha256") or "").strip().upper()
    if manifest_source_hash != meta_source_hash:
        raise ValueError("casebook, metadata and run-manifest source SHA256 mismatch")
    if manifest.get("telemetry_tier") != "off":
        raise ValueError("lifecycle telemetry was not off")
    storage = manifest.get("mt5_storage_contract") or {}
    if storage.get("required_drive") != "D:" or not storage.get("portable_mode"):
        raise ValueError("run manifest does not prove portable D-drive storage")
    if storage.get("common_files_allowed") is not False:
        raise ValueError("run manifest allowed FILE_COMMON")

    return {
        "schema_version": "alert_first_casebook_collection_validation.v1",
        "status": "PASS",
        "run_id": next(iter(run_ids)),
        "alpha_run_dir": str(run_dir),
        "detector_rows": len(rows),
        "unique_event_ids": len(event_ids),
        "human_label_cells_nonblank": 0,
        "strategy_tester_trades": 0,
        "terminal_data_path": meta["terminal_data_path"],
        "source_sha256": meta_source_hash,
        "source_contract_id": source_contract,
        "casebook": {
            "path": str(main_csv),
            "sha256": sha256_file(main_csv),
        },
        "metadata": {
            "path": str(meta_csv),
            "sha256": sha256_file(meta_csv),
        },
        "run_manifest_sha256": sha256_file(manifest_path),
        "enhanced_summary_sha256": sha256_file(summary_path),
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE_OR_OUTCOME_CLAIM",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--min-rows", type=int, default=100)
    args = parser.parse_args()
    result = validate(args.run_dir, min_rows=args.min_rows)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
