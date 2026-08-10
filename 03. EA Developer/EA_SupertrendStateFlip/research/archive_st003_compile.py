#!/usr/bin/env python3
"""Archive the completed HYP003 compile before any later AlphaFactory rebuild."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
ATTEMPT_ID = "ST003-COMPILE-001"
SOURCE_SHA256 = "C4C2A0A700434A2C104551D9AD33ECB8893ACB887E25C6E2E045F4A94638A32E"
EX5_SHA256 = "F446A86B86294B8E244173F545E989C664C4BCEB5F79885247B7D0EF8593A06A"
LOG_SHA256 = "F640411BAD680146289741EF839FFDBFAF8E68383ACEA519BA8A7EBC8C81837E"


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


def validate_authority(registry: Path) -> dict[str, str]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((raw, row))
    if not matches:
        raise ValueError("HYP003 authority is absent")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    if not (
        row.get("state") == "probe"
        and row.get("verdict") == "FROZEN_MQL5_PARITY_ORACLE_BUILD_AUTHORIZED"
        and validation.get("compile_attempt_id") == ATTEMPT_ID
        and validation.get("compile_attempt_limit") == 1
        and validation.get("mql5_compile_authorized") is True
        and metrics.get("compile_attempts_consumed") == 0
        and validation.get("mt5_authorized") is False
        and validation.get("economics_authorized") is False
    ):
        raise ValueError("HYP003 compile archive authority mismatch")
    return {
        "registry_sha256": sha256_file(registry),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def execute() -> dict[str, Any]:
    package = ROOT / "03. EA Developer/EA_SupertrendStateFlip"
    registry = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output = package / "research/evidence/HYP-ST-XAUUSD-H1-003/ST003-COMPILE-001"
    if output.exists() and any(output.iterdir()):
        raise ValueError("ST003 compile archive already exists")
    authority = validate_authority(registry)
    sources = {
        "EA_SupertrendStateFlip.mq5": (package / "EA_SupertrendStateFlip.mq5", SOURCE_SHA256),
        "EA_SupertrendStateFlip.ex5": (package / "EA_SupertrendStateFlip.ex5", EX5_SHA256),
        "EA_SupertrendStateFlip.log": (package / "EA_SupertrendStateFlip.log", LOG_SHA256),
    }
    for label, (path, expected) in sources.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"canonical compile artifact changed before archive: {label}")
    log_text = sources["EA_SupertrendStateFlip.log"][0].read_text(encoding="utf-16", errors="ignore")
    if not re.search(r"Result:\s*0 errors,\s*0 warnings", log_text):
        raise ValueError("compile log lacks the frozen 0E/0W result")
    output.mkdir(parents=True, exist_ok=True)
    archived: dict[str, dict[str, Any]] = {}
    for label, (source, expected) in sources.items():
        target = output / label
        data = source.read_bytes()
        write_exclusive(target, data)
        archived[label] = {
            "canonical_path": source.as_posix(),
            "archived_path": target.as_posix(),
            "sha256": expected,
            "size_bytes": len(data),
            "canonical_modified_at_utc": datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema_version": "st003_compile_archive_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "collection_mode": "POST_COMPILE_IMMEDIATE_ARCHIVE_NO_PRESTART_CLAIM",
        "completed_at_utc": completed,
        "bindings": {
            "collector": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "registry": {"path": registry.as_posix(), **authority},
            "artifacts": archived,
        },
        "compile_result": {"errors": 0, "warnings": 0, "ex5_size_bytes": archived["EA_SupertrendStateFlip.ex5"]["size_bytes"]},
        "attempt_started_artifact_exists": False,
        "reason_attempt_started_absent": "Compile completed through AlphaFactory before this immutable archive was requested; no retroactive start claim is fabricated.",
        "verdict": "COMPILE_ARCHIVE_PASS_0E_0W",
    }
    receipt_bytes = json_bytes(receipt)
    receipt_path = output / "compile_archive_receipt.json"
    write_exclusive(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "st003_compile_archive_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": completed,
        "status": "COMPLETE",
        "verdict": receipt["verdict"],
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(output / "attempt_terminal.json", json_bytes(terminal))
    return receipt


if __name__ == "__main__":
    result = execute()
    print(json_bytes({"verdict": result["verdict"], "compile_result": result["compile_result"]}).decode("utf-8"), end="")
