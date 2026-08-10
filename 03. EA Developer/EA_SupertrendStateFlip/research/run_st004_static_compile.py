#!/usr/bin/env python3
"""Claim, run, and immutably seal the sole HYP004 AlphaFactory static compile."""

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
HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-004"
ATTEMPT_ID = "ST004-COMPILE-001"
SOURCE_SHA256 = "C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02"
ALPHA_PS1_SHA256 = "758D0185A862E023309F7D1A9DFF5970072D71F310975AFCE526CD6E5965F93F"
OUTPUT_DIR = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-004/ST004-COMPILE-001"


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


def validate_registry(registry_path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing HYP004 compile authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_ST004_STATIC_COMPILE_AUTHORIZED",
        "compile": validation.get("mql5_compile_authorized") is True,
        "attempt": validation.get("compile_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("compile_attempt_limit") == 1,
        "unconsumed": metrics.get("compile_attempts_consumed") == 0,
        "source": validation.get("reviewed_mql_source_sha256") == SOURCE_SHA256,
        "runner": validation.get("reviewed_compile_runner_sha256") == sha256_file(Path(__file__).resolve()),
        "alpha": validation.get("reviewed_alpha_ps1_sha256") == ALPHA_PS1_SHA256,
        "alpha_file": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1") == ALPHA_PS1_SHA256,
        "no_mt5": validation.get("mt5_parity_run_authorized") is False,
        "no_comparator": validation.get("comparator_execution_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP004 compile authority failed: {failed}")
    prereg = (ROOT / str(row.get("prereg_path", ""))).resolve()
    if not prereg.is_file() or sha256_file(prereg) != row.get("prereg_sha256"):
        raise ValueError("HYP004 prereg binding mismatch")
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def run_compile(registry_path: Path) -> dict[str, Any]:
    registry_path = registry_path.resolve()
    row, authority = validate_registry(registry_path)
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError("HYP004 compile attempt already exists")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = OUTPUT_DIR / "attempt_started.json"
    write_exclusive(
        marker,
        json_bytes(
            {
                "schema_version": "st004_compile_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "started_at_utc": started,
                "runner_sha256": sha256_file(Path(__file__).resolve()),
                "source_sha256": SOURCE_SHA256,
                "process_id": os.getpid(),
                **authority,
            }
        ),
    )
    source = ROOT / "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5"
    ex5 = source.with_suffix(".ex5")
    log = source.with_suffix(".log")
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "02. AlphaFactory/alpha.ps1"), "compile", "EA_SupertrendStateFlip",
    ]
    try:
        if sha256_file(source) != SOURCE_SHA256:
            raise ValueError("HYP004 source changed after compile claim")
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            timeout=300,
            check=False,
        )
        write_exclusive(OUTPUT_DIR / "alpha_stdout.log", completed.stdout)
        write_exclusive(OUTPUT_DIR / "alpha_stderr.log", completed.stderr)
        if completed.returncode != 0:
            raise ValueError(f"AlphaFactory compile returned {completed.returncode}")
        if not ex5.is_file() or not log.is_file() or ex5.stat().st_size <= 0:
            raise ValueError("AlphaFactory compile output is absent/empty")
        if sha256_file(source) != SOURCE_SHA256:
            raise ValueError("HYP004 source changed during compile")
        log_bytes = log.read_bytes()
        log_text = decode_text(log_bytes)
        if (
            re.search(r"\b0\s+errors?\b", log_text, re.IGNORECASE) is None
            or re.search(r"\b0\s+warnings?\b", log_text, re.IGNORECASE) is None
        ):
            raise ValueError("MetaEditor log does not prove 0 errors / 0 warnings")
        artifacts = {
            "source": (source, OUTPUT_DIR / source.name),
            "compiled_ex5": (ex5, OUTPUT_DIR / ex5.name),
            "compile_log": (log, OUTPUT_DIR / log.name),
        }
        source_hashes: dict[str, str] = {}
        for label, (origin, destination) in artifacts.items():
            raw = origin.read_bytes()
            source_hashes[label] = hashlib.sha256(raw).hexdigest().upper()
            write_exclusive(destination, raw)
            if sha256_file(origin) != source_hashes[label] or sha256_file(destination) != source_hashes[label]:
                raise ValueError(f"{label} changed during immutable archive")
        finished = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt = {
            "schema_version": "st004_static_compile_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "completed_at_utc": finished,
            "verdict": "STATIC_COMPILE_PASS_0E_0W",
            "bindings": {
                "runner": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
                "alpha_ps1": {"path": (ROOT / "02. AlphaFactory/alpha.ps1").as_posix(), "sha256": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1")},
                "registry": {"path": registry_path.as_posix(), **authority},
                "authority_prereg": {"path": row.get("prereg_path"), "sha256": row.get("prereg_sha256")},
                "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
                **{
                    label: {
                        "source_path": origin.as_posix(),
                        "archive_path": destination.as_posix(),
                        "sha256": source_hashes[label],
                    }
                    for label, (origin, destination) in artifacts.items()
                },
                "alpha_stdout": {"path": (OUTPUT_DIR / "alpha_stdout.log").as_posix(), "sha256": sha256_file(OUTPUT_DIR / "alpha_stdout.log")},
                "alpha_stderr": {"path": (OUTPUT_DIR / "alpha_stderr.log").as_posix(), "sha256": sha256_file(OUTPUT_DIR / "alpha_stderr.log")},
            },
            "compile_errors": 0,
            "compile_warnings": 0,
            "mt5_executed": False,
            "economics_evaluated": False,
        }
        receipt_bytes = json_bytes(receipt)
        receipt_path = OUTPUT_DIR / "compile_receipt.json"
        write_exclusive(receipt_path, receipt_bytes)
        terminal = {
            "schema_version": "st004_static_compile_terminal.v1",
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
                        "schema_version": "st004_static_compile_terminal.v1",
                        "hypothesis_id": HYPOTHESIS_ID,
                        "attempt_id": ATTEMPT_ID,
                        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "status": "FAILED",
                        "verdict": "STATIC_COMPILE_FAIL",
                        "error_type": type(exc).__name__,
                        "same_id_retry_authorized": False,
                    }
                ),
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    receipt = run_compile(args.registry)
    print(json_bytes({"verdict": receipt["verdict"]}).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
