#!/usr/bin/env python3
"""Disclosed immutable archive of the already-completed HYP001 static build."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-001"
ARCHIVE_ID = "STBS001-STATIC-COMPILE-001"
SOURCE_SHA256 = "B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D"
OUTPUT_DIR = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-001/STBS001-STATIC-COMPILE-001"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def decode_text(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="strict")
    return raw.decode("utf-8-sig", errors="strict")


def main() -> int:
    package = ROOT / "03. EA Developer/EA_SupertrendBurstScalper"
    files = {
        "source": package / "EA_SupertrendBurstScalper.mq5",
        "compiled_ex5": package / "EA_SupertrendBurstScalper.ex5",
        "compile_log": package / "EA_SupertrendBurstScalper.log",
        "prereg": package / "research/HYP-STBS-XAUUSD-M15-001_ENGINEERING_PREREG.md",
        "engineering_tests": package / "research/tests/test_stbs_001_engineering_contract.py",
        "nonrepaint_manifest": package / "HYP-STBS-XAUUSD-M15-001_NONREPAINT_MANIFEST.json",
        "nonrepaint_audit": package / "research/HYP-STBS-XAUUSD-M15-001_NONREPAINT_AUDIT.json",
        "ea_contract": package / "ALPHAFACTORY_EA_CONTRACT.json",
    }
    if OUTPUT_DIR.exists():
        raise ValueError("static compile archive already exists")
    if any(not path.is_file() for path in files.values()):
        raise ValueError("static compile archive input is absent")
    if sha256_file(files["source"]) != SOURCE_SHA256:
        raise ValueError("reviewed source hash changed before archive")
    log_text = decode_text(files["compile_log"].read_bytes())
    if not re.search(r"\b0\s+errors?\b", log_text, re.I) or not re.search(
        r"\b0\s+warnings?\b", log_text, re.I
    ):
        raise ValueError("compile log does not prove 0 errors / 0 warnings")
    audit = json.loads(files["nonrepaint_audit"].read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or audit.get("findings") != []:
        raise ValueError("non-repaint audit is not a zero-finding PASS")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    bindings: dict[str, Any] = {}
    for label, source in files.items():
        raw = source.read_bytes()
        destination = OUTPUT_DIR / source.name
        write_exclusive(destination, raw)
        digest = hashlib.sha256(raw).hexdigest().upper()
        if sha256_file(source) != digest or sha256_file(destination) != digest:
            raise ValueError(f"{label} changed during archive")
        bindings[label] = {
            "source_path": source.as_posix(),
            "archive_path": destination.as_posix(),
            "sha256": digest,
        }
    completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema_version": "stbs001_disclosed_static_compile_archive.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "archive_id": ARCHIVE_ID,
        "completed_at_utc": completed,
        "disclosure": "Archive created after the canonical compile; no retroactive pre-compile claim is asserted.",
        "collector": {
            "path": Path(__file__).resolve().as_posix(),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "bindings": bindings,
        "compile_errors": 0,
        "compile_warnings": 0,
        "nonrepaint_status": "PASS",
        "mt5_executed": False,
        "economics_evaluated": False,
    }
    receipt_raw = json_bytes(receipt)
    receipt_path = OUTPUT_DIR / "static_compile_archive_receipt.json"
    write_exclusive(receipt_path, receipt_raw)
    terminal = {
        "schema_version": "stbs001_disclosed_static_compile_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "archive_id": ARCHIVE_ID,
        "completed_at_utc": completed,
        "status": "COMPLETE",
        "verdict": "STATIC_BUILD_ARCHIVED_0E_0W_NONREPAINT_PASS",
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(OUTPUT_DIR / "attempt_terminal.json", json_bytes(terminal))
    print(json.dumps({"receipt": receipt_path.as_posix(), "sha256": sha256_file(receipt_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
