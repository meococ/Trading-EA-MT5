#!/usr/bin/env python3
"""Build hash-bound AlphaFactory receipts for HYP-007 diagnostic Model 0.

This follows the existing owner-authorized diagnostic receipt surface used by
AlphaFactory when historical execution-cost provenance is incomplete. It never
marks a run promotion-eligible and it binds each arm to its frozen preset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
HYPOTHESIS_ID = "HYP-ICT-FVG-FIDM0NEWS-EURUSD-M5-007"
PARENT_HYPOTHESIS_ID = "HYP-ICT-FVG-FIDM0-EURUSD-M5-006"
EA_NAME = "EA_ICTFVGReportFidelity"
PACKAGE = ROOT / "03. EA Developer" / EA_NAME
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = PACKAGE / "research" / f"{HYPOTHESIS_ID}_ENGINEERING_PLAN.md"
CAPABILITY = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
NEWS_INCLUDE = PACKAGE / "NewsCalendar2019_2022.mqh"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
OUT = ROOT / "02. AlphaFactory" / "runtime" / "ict_fvg_fidm0_receipts"
PRESETS = {
    "control": PACKAGE / "presets" / "EURUSD_M5_CONTROL.set",
    "challenger": PACKAGE / "presets" / "EURUSD_M5_CHALLENGER.set",
}
EXPECTED_PRESET_SHA256 = {
    "control": "E62D0386B915B4E9BD1FA4A8C761FD72844DBDE2223D175A48F798D6D2F84DB3",
    "challenger": "74FCE7C0C465D5BEA6BAEA9538071C290207621194BA7D74E41996C4CB0A0C68",
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha_file(path),
    }


def git_snapshot() -> tuple[str, str]:
    commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    process = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True,
        text=True,
        capture_output=True,
    )
    return commit, sha_text("\n".join(process.stdout.splitlines()))


def read_frozen_overrides(role: str) -> str:
    preset = PRESETS[role]
    actual_hash = sha_file(preset)
    expected_hash = EXPECTED_PRESET_SHA256[role]
    if actual_hash != expected_hash:
        raise ValueError(
            f"{role} preset drifted: expected {expected_hash}, got {actual_hash}"
        )
    lines = [
        line.strip()
        for line in preset.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";"))
    ]
    expected_mode = "InpSignalMode=0" if role == "control" else "InpSignalMode=1"
    if expected_mode not in lines:
        raise ValueError(f"{role} preset does not contain {expected_mode}")
    if sum(line.startswith("InpSignalMode=") for line in lines) != 1:
        raise ValueError(f"{role} preset must bind exactly one signal mode")
    override_map: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise ValueError(f"malformed preset line: {line}")
        name, value = line.split("=", 1)
        if name in override_map:
            raise ValueError(f"duplicate preset input: {name}")
        override_map[name] = value
    # alpha.ps1 normalizes every invocation into this exact sorted form before
    # validating the receipt binding.
    return ";".join(f"{name}={override_map[name]}" for name in sorted(override_map))


def latest_registry_row() -> dict[str, object]:
    matches = []
    for raw in REGISTRY.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append(row)
    if not matches:
        raise ValueError(f"registry has no row for {HYPOTHESIS_ID}")
    latest = matches[-1]
    validation = latest.get("validation") or {}
    if latest.get("state") != "challenger":
        raise ValueError("latest registry state is not challenger")
    if validation.get("model0_authorized") is not True:
        raise ValueError("latest registry row does not authorize Model 0")
    if validation.get("promotion_eligible") is not False:
        raise ValueError("diagnostic child unexpectedly became promotion-eligible")
    if latest.get("source_hash") != sha_file(SOURCE):
        raise ValueError("registry source hash does not match canonical source")
    if latest.get("prereg_sha256") != sha_file(PREREG):
        raise ValueError("registry prereg hash does not match frozen plan")
    return latest


def build(role: str, control_run: Path | None) -> tuple[Path, str, str]:
    for required in (SOURCE, PREREG, CAPABILITY, NEWS_INCLUDE, REGISTRY, PRESETS[role]):
        if not required.is_file():
            raise ValueError(f"required evidence is missing: {required}")
    latest_registry_row()
    overrides = read_frozen_overrides(role)
    if role == "control" and control_run is not None:
        raise ValueError("control receipt must not bind a prior run")
    if role == "challenger" and control_run is None:
        raise ValueError("challenger receipt requires --control-run")

    task_path = OUT / f"task_packet.{role}.json"
    cost_path = OUT / f"cost_source_manifest.{role}.json"
    task_packet: dict[str, object] = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "authority": "OWNER_ACTIVE_BUILD_DIAGNOSTIC_MODEL0",
        "ea_name": EA_NAME,
        "symbol": "EURUSD",
        "period": "M5",
        "from": "2019.01.01",
        "to": "2022.12.31",
        "model": 0,
        "run_role": role,
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "overrides": overrides,
        "preset_path": str(PRESETS[role].resolve()),
        "preset_sha256": EXPECTED_PRESET_SHA256[role],
        "cost_provenance": "FAIL_SPREAD_COST_PROVENANCE",
        "promotion_eligible": False,
        "note": (
            "Exactly one frozen diagnostic Model-0 arm; no optimization, "
            "parameter rescue, paper/live authority, or holdout access."
        ),
    }
    if control_run is not None:
        control_manifest = control_run / "run_manifest.json"
        control_report = control_run / "report.html"
        for required in (control_manifest, control_report):
            if not required.is_file():
                raise ValueError(f"matched control evidence is missing: {required}")
        manifest = json.loads(control_manifest.read_text(encoding="utf-8-sig"))
        if manifest.get("hypothesis_id") != HYPOTHESIS_ID:
            raise ValueError("matched control hypothesis does not match")
        if manifest.get("run_role") != "control":
            raise ValueError("matched run is not a control")
        task_packet.update(
            {
                "matched_control_run_id": control_run.name,
                "matched_control_manifest_sha256": sha_file(control_manifest),
                "matched_control_report_sha256": sha_file(control_report),
            }
        )
    write_json(task_path, task_packet)
    write_json(
        cost_path,
        {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "symbol": "EURUSD",
            "broker": "Five Percent Online Ltd",
            "spread_policy": "tester_current",
            "round_turn_repricing_pips": [1.5, 2.25, 3.0],
            "spread_cost_provenance": "FAIL_SPREAD_COST_PROVENANCE",
            "commission": "unknown_not_zero",
            "slippage": "unknown_not_zero",
            "audit_status": "FAIL_DIAGNOSTIC_ONLY",
            "promotion_eligible": False,
            "note": (
                "Diagnostic receipt only: historical spread has zero rows, "
                "commission lifecycle sample is insufficient, and slippage is unverified."
            ),
        },
    )

    evidence = [
        file_evidence("task_packet", task_path),
        file_evidence("candidate_registry", REGISTRY),
        file_evidence("source", SOURCE),
        file_evidence("ea_capability_contract", CAPABILITY),
        file_evidence("prereg", PREREG),
        file_evidence("cost_source_manifest", cost_path),
        file_evidence("preset", PRESETS[role]),
        file_evidence("include_0000", NEWS_INCLUDE),
    ]
    if control_run is not None:
        evidence.extend(
            [
                file_evidence("matched_control_manifest", control_run / "run_manifest.json"),
                file_evidence("matched_control_report", control_run / "report.html"),
            ]
        )

    include_records = [
        f"{str(Path(item['path']).resolve()).lower()}\t{item['sha256'].upper()}"
        for item in sorted(
            (entry for entry in evidence if entry["label"].startswith("include_")),
            key=lambda entry: str(Path(entry["path"]).resolve()),
        )
    ]
    commit, status_sha = git_snapshot()
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "authority": "OWNER_ACTIVE_BUILD_DIAGNOSTIC_MODEL0",
        "registry_row_sha256": sha_file(REGISTRY),
        "task_packet_sha256": sha_file(task_path),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": HYPOTHESIS_ID,
            "run_role": role,
            "ea_name": EA_NAME,
            "symbol": "EURUSD",
            "period": "M5",
            "from": "2019.01.01",
            "to": "2022.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "trade-only",
            "telemetry_profile": "lifecycle-v3",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
            "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
            "include_closure_sha256": sha_text("\n".join(include_records)),
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "promotion_eligible": False,
    }
    receipt_path = OUT / f"execution_receipt.{role}.json"
    write_json(receipt_path, receipt)
    receipt_sha = sha_file(receipt_path)
    (OUT / f"execution_receipt.{role}.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    return receipt_path, receipt_sha, overrides


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("control", "challenger"))
    parser.add_argument("--control-run", type=Path)
    args = parser.parse_args()
    receipt, receipt_sha, overrides = build(args.role, args.control_run)
    print(
        json.dumps(
            {"receipt": str(receipt), "sha256": receipt_sha, "overrides": overrides}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
