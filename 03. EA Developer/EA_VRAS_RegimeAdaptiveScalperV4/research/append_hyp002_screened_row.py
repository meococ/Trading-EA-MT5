#!/usr/bin/env python3
"""Append the frozen HYP-002 screened row after validating a staged registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path


HYPOTHESIS_ID = "HYP-VRAS-USDJPY-M5-002"
PREDECESSOR_ID = "HYP-VRAS-USDJPY-M5-001"
PREDECESSOR_COMMIT = "055bed5"
PREDECESSOR_SHA256 = "425352144DE7E9F3291D48FEC85C52E0B2F6FDE2FB87BA83CEAACB9EB978EAFE"
SOURCE_REPO_PATH = (
    "03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/"
    "EA_VRAS_RegimeAdaptiveScalperV4.mq5"
)
SNAPSHOT_REPO_PATH = (
    "03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/source_snapshots/"
    "EA_VRAS_RegimeAdaptiveScalperV4_HYP-VRAS-USDJPY-M5-001_42535214.mq5"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def prepare_snapshot(root: Path) -> Path:
    snapshot = root / SNAPSHOT_REPO_PATH
    payload = subprocess.run(
        ["git", "-C", str(root), "show", f"{PREDECESSOR_COMMIT}:{SOURCE_REPO_PATH}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    if sha256_bytes(payload) != PREDECESSOR_SHA256:
        raise ValueError("predecessor Git blob SHA256 mismatch")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists() and snapshot.read_bytes() != payload:
        raise ValueError("predecessor source snapshot already exists with different bytes")
    if not snapshot.exists():
        temporary = snapshot.with_name(f".{snapshot.name}.{os.getpid()}.tmp")
        temporary.write_bytes(payload)
        temporary.replace(snapshot)
    return snapshot


def corrected_predecessor_registry(before: bytes) -> tuple[bytes, int]:
    raw_lines = before.decode("utf-8-sig").splitlines()
    corrected = 0
    for index, raw in enumerate(raw_lines):
        item = json.loads(raw)
        if item.get("hypothesis_id") != PREDECESSOR_ID:
            continue
        if not item.get("source_hash"):
            continue
        if item.get("source_hash") != PREDECESSOR_SHA256:
            raise ValueError("predecessor registry source hash is unexpected")
        validation = item.get("validation")
        if not isinstance(validation, dict):
            raise ValueError("predecessor registry validation object is missing")
        if validation.get("source_snapshot_path") == SNAPSHOT_REPO_PATH and validation.get(
            "source_snapshot_sha256"
        ) == PREDECESSOR_SHA256:
            continue
        validation["source_snapshot_path"] = SNAPSHOT_REPO_PATH
        validation["source_snapshot_sha256"] = PREDECESSOR_SHA256
        raw_lines[index] = json.dumps(item, separators=(",", ":"), ensure_ascii=False)
        corrected += 1
    if corrected not in {0, 2}:
        raise ValueError(f"expected zero or two predecessor pointer corrections; got {corrected}")
    return ("\n".join(raw_lines) + "\n").encode("utf-8"), corrected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repair-latest", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    row_path = Path(__file__).with_name("HYP-VRAS-USDJPY-M5-002_SCREENED_ROW.json")
    validator = root / "04. Memory" / "research" / "validate_candidate_registry.py"
    row = json.loads(row_path.read_text(encoding="utf-8"))
    if row.get("hypothesis_id") != HYPOTHESIS_ID or row.get("state") != "screened":
        raise ValueError("frozen row identity/state mismatch")
    compact = json.dumps(row, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    prepare_snapshot(root)
    before = registry.read_bytes()
    if not before.endswith(b"\n"):
        raise ValueError("canonical registry lacks terminal LF")
    corrected_before, corrected_count = corrected_predecessor_registry(before)
    corrected_lines = corrected_before.decode("utf-8-sig").splitlines()
    matches = [
        index
        for index, line in enumerate(corrected_lines)
        if json.loads(line).get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if matches:
        if not args.repair_latest or len(matches) != 1 or matches[0] != len(corrected_lines) - 1:
            raise ValueError(f"canonical registry already contains {HYPOTHESIS_ID}")
        current = json.loads(corrected_lines[matches[0]])
        if current.get("state") != "screened" or current.get("source_hash") != row.get(
            "source_hash"
        ):
            raise ValueError("latest HYP-002 row is outside the narrow repair contract")
        corrected_lines[matches[0]] = compact.decode("utf-8")
        final_payload = ("\n".join(corrected_lines) + "\n").encode("utf-8")
        action = "REPAIRED_LATEST"
    else:
        if args.repair_latest:
            raise ValueError("repair requested but HYP-002 is absent")
        final_payload = corrected_before + compact + b"\n"
        action = "APPENDED"
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".jsonl", prefix="vras_hyp002_registry_", delete=False
    ) as handle:
        staged = Path(handle.name)
        handle.write(final_payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        subprocess.run(
            ["python", str(validator), "--registry", str(staged)],
            cwd=root,
            check=True,
        )
        if args.apply:
            temporary = registry.with_name(f".{registry.name}.{os.getpid()}.tmp")
            with temporary.open("wb") as handle:
                handle.write(final_payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(registry)
            subprocess.run(["python", str(validator)], cwd=root, check=True)
    finally:
        staged.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "status": "APPLIED" if args.apply else "STAGED_PASS",
                "action": action,
                "predecessor_pointer_corrections": corrected_count,
                "snapshot": SNAPSHOT_REPO_PATH,
                "snapshot_sha256": PREDECESSOR_SHA256,
                "row": row,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
