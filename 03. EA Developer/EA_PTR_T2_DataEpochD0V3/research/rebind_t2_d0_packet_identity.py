#!/usr/bin/env python3
"""Rebind a D0 collection packet from a data-valid, identity-discovery MT5 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SHARED_RESEARCH_DIR = WORKSPACE_ROOT / "04. Memory" / "research"
if str(SHARED_RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_RESEARCH_DIR))

from data_epoch_journal import model4_mode_errors  # noqa: E402


AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-003"
EA_NAME = "EA_PTR_T2_DataEpochD0V3"
MODEL = 0
SERVER = "FivePercentOnline-Real"
ALLOWED_COVERAGE = {"FULL_2018_PLUS", "BROKER_LIMITED_START"}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def upper_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-F0-9]{64}", value) is None:
        raise ValueError(f"{label} must be uppercase SHA256")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    packet = load(args.packet)
    manifest = load(args.manifest)
    if packet.get("authority") != AUTHORITY:
        raise ValueError("packet is not collection-only authority")
    expected = {
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "run_role": "control",
        "symbol": packet.get("symbol"),
        "period": "M5",
        "from": "1970.01.01",
        "to": "2026.07.30",
        "model": MODEL,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(f"manifest {field} does not match packet")
    gate = manifest.get("data_quality_gate")
    if not isinstance(gate, dict):
        raise ValueError("identity-discovery run has no completed data_quality_gate")
    if gate.get("coverage_class") not in ALLOWED_COVERAGE:
        raise ValueError("identity-discovery run coverage class is invalid")
    quality = gate.get("history_quality")
    if isinstance(quality, bool) or not isinstance(quality, (int, float)) or float(quality) <= 97.0:
        raise ValueError("identity-discovery run History Quality does not exceed 97")
    if gate.get("actual_to") != "2026.07.30":
        raise ValueError("identity-discovery run did not reach the frozen cutoff")
    proof = gate.get("series_proof")
    if not isinstance(proof, dict) or proof.get("symbol") != packet.get("symbol"):
        raise ValueError("identity-discovery run series proof is absent or wrong-symbol")
    if proof.get("copytime_from_epoch") != proof.get("m5_first_epoch"):
        raise ValueError("identity-discovery run CopyTime anchor is invalid")
    if proof.get("copytime_first_epoch") != proof.get("m5_first_epoch"):
        raise ValueError("identity-discovery run CopyTime result is invalid")
    if MODEL == 4:
        local_run_dir = Path(str(manifest.get("local_run_dir") or "")).resolve()
        journal = manifest.get("data_quality_journal_delta")
        if not isinstance(journal, dict) or journal.get("path") != "logs/tester_journal_delta.log":
            raise ValueError("identity-discovery Model 4 journal receipt is absent")
        journal_path = (local_run_dir / str(journal["path"])).resolve()
        if not journal_path.is_file() or not journal_path.is_relative_to(local_run_dir):
            raise ValueError("identity-discovery Model 4 journal path is invalid")
        journal_sha = hashlib.sha256(journal_path.read_bytes()).hexdigest().upper()
        if journal_sha != journal.get("sha256"):
            raise ValueError("identity-discovery Model 4 journal SHA mismatch")
        journal_text = journal_path.read_text(encoding="utf-8", errors="replace")
        mode_errors = model4_mode_errors(
            journal_text,
            symbol=str(packet.get("symbol")),
            period="M5",
            server=SERVER,
            label="identity-discovery Model 4 journal",
        )
        if mode_errors:
            raise ValueError("; ".join(mode_errors))

    for field in ("broker_fingerprint", "server_fingerprint", "account_fingerprint", "data_fingerprint"):
        packet[field] = upper_sha(manifest.get(field), f"manifest {field}")
    args.packet.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "TASK_PACKET_IDENTITY_REBOUND "
        f"symbol={packet['symbol']} hq={float(quality):g} coverage={gate['coverage_class']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
