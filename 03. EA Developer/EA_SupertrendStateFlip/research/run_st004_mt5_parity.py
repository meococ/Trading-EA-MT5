#!/usr/bin/env python3
"""Claim and execute the sole HYP008 AlphaFactory MT5 parity collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
ATTEMPT_ID = "ST008-MT5-001"
AUDIT_RUN_ID = "ST003-MT5-PARITY-001"
SOURCE_SHA256 = "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
ALPHA_PS1_SHA256 = "68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8"
EXACT_OVERRIDES = "InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpParityFileName=ST003_MQL5_PARITY_001.csv"
OUTPUT_DIR = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def decode_text(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="ignore")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be", errors="ignore")
    return raw.decode("utf-8-sig", errors="ignore")


def validate_registry(registry: Path, contract_receipt: Path) -> tuple[dict[str, Any], dict[str, str]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing HYP008 MT5 authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "verdict": row.get("verdict") == "FROZEN_ST008_MT5_PARITY_RUN_AUTHORIZED",
        "run": validation.get("mt5_parity_run_authorized") is True,
        "attempt": validation.get("mt5_parity_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("mt5_parity_attempt_limit") == 1,
        "unconsumed": metrics.get("mt5_parity_attempts_consumed") == 0,
        "launcher": validation.get("reviewed_mt5_launcher_sha256") == sha256_file(Path(__file__).resolve()),
        "source": validation.get("reviewed_mql_source_sha256") == SOURCE_SHA256,
        "alpha": validation.get("reviewed_alpha_ps1_sha256") == ALPHA_PS1_SHA256,
        "alpha_file": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1") == ALPHA_PS1_SHA256,
        "receipt": validation.get("contract_receipt_sha256") == sha256_file(contract_receipt),
        "no_economics": validation.get("economics_authorized") is False,
        "no_outcomes": validation.get("performance_metrics_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP008 MT5 authority failed: {failed}")
    common = Path(str(validation.get("frozen_common_file_path", ""))).resolve()
    if not common.is_absolute() or common.name != "ST003_MQL5_PARITY_001.csv":
        raise ValueError("frozen FILE_COMMON path is invalid")
    if common.exists():
        raise ValueError("frozen FILE_COMMON path already exists; refusing overwrite/retry")
    return row, {
        "registry_sha256": sha256_file(registry),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "common_file_path": common.as_posix(),
    }


def build_alpha_command(contract_receipt: Path) -> list[str]:
    """Map semantic current spread to AlphaFactory's required empty CLI token."""
    return [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "02. AlphaFactory/alpha.ps1"), "backtest", "EA_SupertrendStateFlip",
        "-Symbol", "XAUUSD", "-Period", "H1", "-From", "2005.01.01", "-To", "2023.01.01",
        "-Model", "0", "-ExecutionMode", "0", "-FixedDelayMs", "0", "-TimeoutSec", "1800",
        "-Overrides", EXACT_OVERRIDES, "-HypothesisId", HYPOTHESIS_ID, "-RunRole", "control",
        "-TelemetryTier", "off", "-Deposit", "10000", "-Leverage", "100", "-Spread", "",
        "-ContractReceipt", str(contract_receipt), "-ContractReceiptSha256", sha256_file(contract_receipt),
    ]


def execute(registry: Path, contract_receipt: Path) -> dict[str, Any]:
    registry = registry.resolve()
    contract_receipt = contract_receipt.resolve()
    row, authority = validate_registry(registry, contract_receipt)
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError("HYP008 MT5 attempt already exists")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = OUTPUT_DIR / "attempt_started.json"
    write_exclusive(
        marker,
        json_bytes(
            {
                "schema_version": "st005_mt5_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "audit_run_id": AUDIT_RUN_ID,
                "started_at_utc": started,
                "launcher_sha256": sha256_file(Path(__file__).resolve()),
                "alpha_ps1_sha256": ALPHA_PS1_SHA256,
                "contract_receipt_sha256": sha256_file(contract_receipt),
                "process_id": os.getpid(),
                **authority,
            }
        ),
    )
    command = build_alpha_command(contract_receipt)
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=2100, check=False)
        stdout_path = OUTPUT_DIR / "alpha_stdout.log"
        stderr_path = OUTPUT_DIR / "alpha_stderr.log"
        write_exclusive(stdout_path, completed.stdout)
        write_exclusive(stderr_path, completed.stderr)
        if completed.returncode != 0:
            raise ValueError(f"AlphaFactory MT5 returned {completed.returncode}")
        text = decode_text(completed.stdout) + "\n" + decode_text(completed.stderr)
        matches = re.findall(r"(?m)^ALPHA_RUN_DIR=(.+?)\s*$", text)
        if len(matches) != 1:
            raise ValueError(f"expected one ALPHA_RUN_DIR receipt, found {len(matches)}")
        run_dir = Path(matches[0].strip()).resolve()
        manifest = run_dir / "run_manifest.json"
        if not run_dir.is_dir() or not manifest.is_file():
            raise ValueError("AlphaFactory reported an invalid run directory")
        payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if payload.get("hypothesis_id") != HYPOTHESIS_ID or payload.get("source_sha256") != SOURCE_SHA256:
            raise ValueError("AlphaFactory run manifest identity/source mismatch")
        finished = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt = {
            "schema_version": "st005_mt5_run_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "audit_run_id": AUDIT_RUN_ID,
            "started_at_utc": started,
            "completed_at_utc": finished,
            "verdict": "MT5_ZERO_TRADE_COLLECTION_COMPLETE_PENDING_PARITY",
            "bindings": {
                "launcher": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
                "alpha_ps1": {"path": (ROOT / "02. AlphaFactory/alpha.ps1").as_posix(), "sha256": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1")},
                "registry": {"path": registry.as_posix(), **authority},
                "authority_prereg": {"path": row.get("prereg_path"), "sha256": row.get("prereg_sha256")},
                "contract_receipt": {"path": contract_receipt.as_posix(), "sha256": sha256_file(contract_receipt)},
                "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
                "alpha_stdout": {"path": stdout_path.as_posix(), "sha256": sha256_file(stdout_path)},
                "alpha_stderr": {"path": stderr_path.as_posix(), "sha256": sha256_file(stderr_path)},
                "run_manifest": {"path": manifest.as_posix(), "sha256": sha256_file(manifest)},
            },
            "alpha_run_dir": run_dir.as_posix(),
            "orders_executed": 0,
            "trades_executed": 0,
            "economics_evaluated": False,
        }
        receipt_bytes = json_bytes(receipt)
        receipt_path = OUTPUT_DIR / "mt5_run_receipt.json"
        write_exclusive(receipt_path, receipt_bytes)
        terminal = {
            "schema_version": "st005_mt5_run_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": finished,
            "status": "COMPLETE",
            "verdict": receipt["verdict"],
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
            "same_id_retry_authorized": False,
        }
        write_exclusive(OUTPUT_DIR / "attempt_terminal.json", json_bytes(terminal))
        return receipt
    except Exception as exc:
        terminal = OUTPUT_DIR / "attempt_terminal.json"
        if not terminal.exists():
            write_exclusive(
                terminal,
                json_bytes(
                    {
                        "schema_version": "st005_mt5_run_terminal.v1",
                        "hypothesis_id": HYPOTHESIS_ID,
                        "attempt_id": ATTEMPT_ID,
                        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "status": "FAILED",
                        "verdict": "MT5_ZERO_TRADE_COLLECTION_FAIL",
                        "error_type": type(exc).__name__,
                        "same_id_retry_authorized": False,
                    }
                ),
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--contract-receipt", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    receipt = execute(args.registry, args.contract_receipt)
    print(json_bytes({"verdict": receipt["verdict"], "alpha_run_dir": receipt["alpha_run_dir"]}).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
