#!/usr/bin/env python3
"""Finalize the completed dataset-004 export from its immutable manifest.

This recovery path never starts MT5 and never rewrites market data or the
manifest. It independently re-hashes all 20 Parquet files, verifies storage
reconciliation and zero-outcome counters, then creates only the missing export
receipt under a hash-bound one-use authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


WORKSPACE = Path(__file__).resolve().parents[3]
DATASET_ID = "DATA-FIVEPERCENT-5ASSET-MULTITF-004"
SYMBOLS = ("EURUSD", "USDJPY", "GBPUSD", "XAUUSD", "BTCUSD")
TIMEFRAMES = ("M1", "M5", "H1", "H4")
DATA_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
    f"{DATASET_ID}"
)
MANIFEST_REL = f"{DATA_ROOT_REL}/manifest.json"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_FiveAssetDataFoundation/research/evidence/"
    f"{DATASET_ID}"
)
RECEIPT_REL = f"{EVIDENCE_ROOT_REL}/export_receipt.json"
AUTHORITY_REL = (
    "03. EA Developer/EA_FiveAssetDataFoundation/research/"
    f"{DATASET_ID}_FINALIZE_AUTHORITY.json"
)

EXPECTED_TOTAL_ROWS = 48_314_068
EXPECTED_TOTAL_BYTES = 1_206_400_142
EXPECTED_UTC_AMBIGUOUS_ROWS = 236
EXPECTED_EXACT_DUPLICATE_ROWS_REMOVED = 9


class FinalizeError(RuntimeError):
    """Fail-closed receipt-finalization violation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def atomic_json_create(path: Path, value: object) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FinalizeError(f"create-new receipt already exists: {target}")
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            stream.write(canonical_json(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def resolve_bound_path(raw: str, *, workspace: Path = WORKSPACE) -> Path:
    candidate = Path(raw)
    return candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()


def expected_parquet_paths() -> set[str]:
    return {
        f"{DATA_ROOT_REL}/{symbol}/{symbol}_{timeframe}_ALL_AVAILABLE_20260801.parquet"
        for symbol in SYMBOLS
        for timeframe in TIMEFRAMES
    }


def validate_zero_outcomes(manifest: Mapping[str, object]) -> None:
    counters = manifest.get("outcome_blind_counters")
    if not isinstance(counters, dict):
        raise FinalizeError("manifest outcome counters missing")
    expected = {
        "orders_submitted": 0,
        "trades_simulated": 0,
        "positions_queried": 0,
        "deals_queried": 0,
        "pnl_computed": 0,
        "profit_factor_computed": 0,
        "mfe_mae_computed": 0,
        "economics_executed": False,
        "validation_selected": False,
        "holdout_selected": False,
    }
    if any(counters.get(key) != value for key, value in expected.items()):
        raise FinalizeError("manifest outcome-blind counter drift")


def validate_manifest(
    manifest_path: Path,
    *,
    workspace: Path = WORKSPACE,
    expected_total_rows: int = EXPECTED_TOTAL_ROWS,
    expected_total_bytes: int = EXPECTED_TOTAL_BYTES,
    expected_utc_ambiguous_rows: int = EXPECTED_UTC_AMBIGUOUS_ROWS,
    expected_exact_duplicates_removed: int = EXPECTED_EXACT_DUPLICATE_ROWS_REMOVED,
) -> dict[str, object]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != "five_asset_market_data_manifest.v1"
        or manifest.get("dataset_id") != DATASET_ID
        or tuple(manifest.get("symbols", [])) != SYMBOLS
        or tuple(manifest.get("timeframes", [])) != TIMEFRAMES
    ):
        raise FinalizeError("manifest identity/scope mismatch")
    validate_zero_outcomes(manifest)
    terminal = manifest.get("terminal")
    if not isinstance(terminal, dict):
        raise FinalizeError("terminal metadata missing")
    data_path = Path(str(terminal.get("data_path", ""))).resolve()
    if (
        str(terminal.get("server")) != "FivePercentOnline-Real"
        or "Five Percent Online Ltd" not in str(terminal.get("company", ""))
        or bool(terminal.get("terminal_trade_allowed"))
        or data_path.drive.upper() != "D:"
    ):
        raise FinalizeError("terminal/broker/storage contract mismatch")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != 20:
        raise FinalizeError("manifest must bind exactly 20 files")
    if {str(item.get("path")) for item in files if isinstance(item, dict)} != expected_parquet_paths():
        raise FinalizeError("manifest file identity set mismatch")
    total_rows = 0
    total_bytes = 0
    ambiguous_rows = 0
    duplicates_removed = 0
    for item in files:
        if not isinstance(item, dict):
            raise FinalizeError("manifest file entry is not an object")
        path = resolve_bound_path(str(item.get("path", "")), workspace=workspace)
        if not path.is_file():
            raise FinalizeError(f"manifest file missing: {path}")
        size = int(path.stat().st_size)
        if size != int(item.get("bytes", -1)):
            raise FinalizeError(f"manifest byte mismatch: {path}")
        if sha256_file(path) != item.get("sha256"):
            raise FinalizeError(f"manifest SHA256 mismatch: {path}")
        total_rows += int(item.get("rows", -1))
        total_bytes += size
        ambiguous_rows += int(item.get("utc_ambiguous_rows", -1))
        duplicates_removed += int(item.get("source_exact_duplicate_rows_removed", -1))
    observed = (
        total_rows,
        total_bytes,
        ambiguous_rows,
        duplicates_removed,
    )
    expected = (
        expected_total_rows,
        expected_total_bytes,
        expected_utc_ambiguous_rows,
        expected_exact_duplicates_removed,
    )
    if observed != expected:
        raise FinalizeError(f"manifest aggregate mismatch expected={expected} actual={observed}")
    return {
        "manifest": manifest,
        "file_count": len(files),
        "total_rows": total_rows,
        "total_bytes": total_bytes,
        "utc_ambiguous_rows_total": ambiguous_rows,
        "source_exact_duplicate_rows_removed_total": duplicates_removed,
    }


def validate_authority(authority: Mapping[str, object]) -> None:
    if (
        authority.get("schema_version") != "five_asset_data_finalize_authority.v1"
        or authority.get("dataset_id") != DATASET_ID
        or authority.get("authorized") is not True
        or authority.get("one_use") is not True
    ):
        raise FinalizeError("finalization authority identity/state mismatch")
    for label in (
        "manifest",
        "export_tool",
        "finalizer",
        "test",
        "plan",
        "storage_reconciliation",
        "consumed_export_authority",
        "blocker",
    ):
        path = resolve_bound_path(str(authority.get(f"{label}_path", "")))
        expected = str(authority.get(f"{label}_sha256", ""))
        if not path.is_file() or sha256_file(path) != expected:
            raise FinalizeError(f"{label} hash binding mismatch")


def validate_storage_reconciliation(path: Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        payload.get("schema_version")
        != "five_asset_data_storage_reconciliation.v1"
        or payload.get("dataset_id") != DATASET_ID
        or payload.get("protected_c_roots_unchanged") is not True
    ):
        raise FinalizeError("protected-C storage reconciliation failed")
    return payload


def finalize(authority_path: Path) -> dict[str, object]:
    authority_path = Path(authority_path).resolve()
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    validate_authority(authority)
    manifest_path = resolve_bound_path(str(authority["manifest_path"]))
    summary = validate_manifest(manifest_path)
    storage_path = resolve_bound_path(str(authority["storage_reconciliation_path"]))
    storage = validate_storage_reconciliation(storage_path)
    blocker = json.loads(
        resolve_bound_path(str(authority["blocker_path"])).read_text(encoding="utf-8")
    )
    if blocker.get("attempted_authority_sha256") != authority.get(
        "attempted_export_authority_sha256"
    ):
        raise FinalizeError("attempted export authority hash mismatch")
    receipt_path = WORKSPACE / RECEIPT_REL
    receipt = {
        "schema_version": "five_asset_data_export_receipt.v1",
        "dataset_id": DATASET_ID,
        "status": "EXPORT_COMPLETE_RAW_DATA_ONLY_RECOVERED_FINALIZATION",
        "finalized_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recovery_scope": "RECEIPT_ONLY_NO_MT5_NO_DATA_OR_MANIFEST_REWRITE",
        "recovery_reason": "Relative authority path rendering failed after manifest publication.",
        "attempted_export_authority_sha256": authority[
            "attempted_export_authority_sha256"
        ],
        "consumed_export_authority_path": authority[
            "consumed_export_authority_path"
        ],
        "consumed_export_authority_sha256": authority[
            "consumed_export_authority_sha256"
        ],
        "finalize_authority_path": str(authority_path.relative_to(WORKSPACE)).replace(
            "\\", "/"
        ),
        "finalize_authority_sha256": sha256_file(authority_path),
        "finalizer_path": authority["finalizer_path"],
        "finalizer_sha256": authority["finalizer_sha256"],
        "manifest_path": str(manifest_path.relative_to(WORKSPACE)).replace("\\", "/"),
        "manifest_sha256": sha256_file(manifest_path),
        "published_file_count": summary["file_count"],
        "total_rows": summary["total_rows"],
        "total_bytes": summary["total_bytes"],
        "utc_ambiguous_rows_total": summary["utc_ambiguous_rows_total"],
        "source_exact_duplicate_rows_removed_total": summary[
            "source_exact_duplicate_rows_removed_total"
        ],
        "storage_reconciliation_path": str(storage_path.relative_to(WORKSPACE)).replace(
            "\\", "/"
        ),
        "storage_reconciliation_sha256": sha256_file(storage_path),
        "protected_c_roots_unchanged": storage["protected_c_roots_unchanged"],
        "orders_submitted": 0,
        "economics_executed": False,
        "t2_completion_claim": False,
        "promotion_eligible": False,
    }
    atomic_json_create(receipt_path, receipt)
    return receipt


def dry_run(authority_path: Path) -> dict[str, object]:
    try:
        authority = json.loads(Path(authority_path).resolve().read_text(encoding="utf-8"))
        validate_authority(authority)
        validate_manifest(resolve_bound_path(str(authority["manifest_path"])))
        validate_storage_reconciliation(
            resolve_bound_path(str(authority["storage_reconciliation_path"]))
        )
        allowed = not (WORKSPACE / RECEIPT_REL).exists()
        blocker = None if allowed else "export receipt already exists"
    except Exception as exc:
        allowed = False
        blocker = str(exc)
    return {
        "dataset_id": DATASET_ID,
        "execution_allowed": allowed,
        "mutated": False,
        "scope": "RECEIPT_ONLY",
        "blocker": blocker,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, default=WORKSPACE / AUTHORITY_REL)
    parser.add_argument("--production", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.production:
        print(json.dumps(dry_run(args.authority), sort_keys=True))
        return 0
    receipt = finalize(args.authority)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
