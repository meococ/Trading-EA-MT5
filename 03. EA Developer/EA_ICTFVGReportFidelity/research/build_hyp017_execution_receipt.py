#!/usr/bin/env python3
"""Build the single-run AlphaFactory execution receipt for HYP-017."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
EA_NAME = "EA_ICTFVGReportFidelity"
HYPOTHESIS_ID = "HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017"
PARENT_HYPOTHESIS_ID = "HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1"
AUTHORITY = "OWNER_AUTHORIZED_FROZEN_HUMAN_CONTEXT_POLICY_DIAGNOSTIC_MODEL0"
FROM_DATE = "2018.01.01"
TO_DATE = "2026.07.19"

PACKAGE = ROOT / "03. EA Developer" / EA_NAME
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = PACKAGE / "research" / f"{HYPOTHESIS_ID}_MODEL0_PLAN.md"
PRESET = PACKAGE / "presets" / "EURUSD_M5_HYP017_HUMAN_CONTEXT_POLICY.set"
CAPABILITY = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
INCLUDES = [PACKAGE / "HumanContextEngine.mqh", PACKAGE / "NewsCalendar2019_2022.mqh"]
PARENT_COLLECTION = (
    PACKAGE
    / "research"
    / "evidence"
    / "HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1_COLLECTION_RESULT.json"
)
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
OUT = ROOT / "02. AlphaFactory" / "runtime" / "ict_fvg_hyp017_execution_receipt"

EXPECTED_SOURCE_SHA256 = "FF02340C65CBB0E36B1794CB8263023FDD9B7F9218492E749F1F8875C826A5C6"
EXPECTED_PREREG_SHA256 = "0FF4BABC96257BAC7B70F2A017320832F25CC53546868946F7F3E235B8392FF2"
EXPECTED_PRESET_SHA256 = "AA97D48D9999EF6303B8E9849BEF87FDAA399BCAF4A106E4574073BBEBF74EEC"
EXPECTED_COLLECTION_SHA256 = "BF1D930AEF0B01CAA6E939DD3B3762FFDF39F5585E678B14B626FA6BC35A5873"
REQUIRED_SIDECARS = sorted(
    ["*_HumanContext_*.csv", "*_LifecycleTrades_*.csv", "*_RunMeta_*.json"]
)


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


def read_frozen_overrides() -> str:
    if sha_file(PRESET) != EXPECTED_PRESET_SHA256:
        raise ValueError("HYP-017 preset drifted")
    values: dict[str, str] = {}
    for raw in PRESET.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if "=" not in line:
            raise ValueError(f"malformed preset line: {line}")
        name, value = line.split("=", 1)
        if name in values:
            raise ValueError(f"duplicate preset input: {name}")
        values[name] = value
    required = {
        "InpResearchAutoMode": "true",
        "InpEnableTelemetry": "true",
        "InpSignalMode": "3",
        "InpRiskPercent": "0.01",
        "InpMagic": "5600727",
        "InpMaxAccountDrawdownPct": "100.00",
        "InpRequireNewsGuard": "false",
    }
    for name, expected in required.items():
        if values.get(name) != expected:
            raise ValueError(f"preset must bind {name}={expected}")
    return ";".join(f"{name}={values[name]}" for name in sorted(values))


def validate_registry() -> None:
    matches = []
    for raw in REGISTRY.read_text(encoding="utf-8-sig").splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append(row)
    if not matches:
        raise ValueError("HYP-017 registry row is missing")
    latest = matches[-1]
    validation = latest.get("validation") or {}
    if latest.get("state") != "challenger":
        raise ValueError("latest HYP-017 registry state is not challenger")
    if validation.get("model0_authorized") is not True:
        raise ValueError("HYP-017 Model 0 is not authorized")
    if validation.get("performance_metrics_authorized") is not True:
        raise ValueError("HYP-017 performance diagnostics are not authorized")
    if validation.get("promotion_eligible") is not False:
        raise ValueError("HYP-017 unexpectedly became promotion eligible")
    if latest.get("source_hash") != sha_file(SOURCE):
        raise ValueError("registry source hash does not match canonical source")
    if latest.get("prereg_sha256") != sha_file(PREREG):
        raise ValueError("registry prereg hash does not match frozen plan")


def build() -> tuple[Path, str, str]:
    required = [SOURCE, PREREG, PRESET, CAPABILITY, PARENT_COLLECTION, REGISTRY, *INCLUDES]
    for path in required:
        if not path.is_file():
            raise ValueError(f"required evidence is missing: {path}")
    if sha_file(SOURCE) != EXPECTED_SOURCE_SHA256:
        raise ValueError("canonical HYP-017 source drifted")
    if sha_file(PREREG) != EXPECTED_PREREG_SHA256:
        raise ValueError("frozen HYP-017 preregistration drifted")
    if sha_file(PARENT_COLLECTION) != EXPECTED_COLLECTION_SHA256:
        raise ValueError("parent outcome-blind collection drifted")
    validate_registry()
    overrides = read_frozen_overrides()

    task_path = OUT / "task_packet.control.json"
    cost_path = OUT / "cost_source_manifest.control.json"
    write_json(
        task_path,
        {
            "schema_version": "alphafactory_research_task_packet.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
            "authority": AUTHORITY,
            "ea_name": EA_NAME,
            "symbol": "EURUSD",
            "period": "M5",
            "from": FROM_DATE,
            "to": TO_DATE,
            "model": 0,
            "run_role": "control",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "overrides": overrides,
            "preset_path": str(PRESET.resolve()),
            "preset_sha256": EXPECTED_PRESET_SHA256,
            "parent_collection_sha256": EXPECTED_COLLECTION_SHA256,
            "economic_runs_authorized": 1,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "note": "Exactly one frozen HYP-017 diagnostic economic run; no repeat or rescue.",
        },
    )
    write_json(
        cost_path,
        {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "symbol": "EURUSD",
            "broker": "Five Percent Online Ltd",
            "tester_spread": "current_embedded",
            "incremental_round_turn_pips": [1.5, 2.25, 3.0],
            "spread_cost_provenance": "FAIL_SPREAD_COST_PROVENANCE",
            "commission": "tester_lifecycle_observed_not_independently_verified",
            "slippage": "unknown_not_zero",
            "audit_status": "FAIL_DIAGNOSTIC_ONLY",
            "promotion_eligible": False,
            "note": "Conservative incremental pips are applied on top of tester lifecycle net.",
        },
    )

    evidence = [
        file_evidence("task_packet", task_path),
        file_evidence("candidate_registry", REGISTRY),
        file_evidence("source", SOURCE),
        file_evidence("ea_capability_contract", CAPABILITY),
        file_evidence("prereg", PREREG),
        file_evidence("cost_source_manifest", cost_path),
        file_evidence("preset", PRESET),
        file_evidence("parent_collection", PARENT_COLLECTION),
    ]
    for index, path in enumerate(INCLUDES):
        evidence.append(file_evidence(f"include_{index:04d}", path))
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
        "authority": AUTHORITY,
        "registry_row_sha256": sha_file(REGISTRY),
        "task_packet_sha256": sha_file(task_path),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": HYPOTHESIS_ID,
            "run_role": "control",
            "ea_name": EA_NAME,
            "symbol": "EURUSD",
            "period": "M5",
            "from": FROM_DATE,
            "to": TO_DATE,
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "trade-only",
            "telemetry_profile": "lifecycle-v3",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": REQUIRED_SIDECARS,
            "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
            "include_closure_sha256": sha_text("\n".join(include_records)),
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "promotion_eligible": False,
    }
    receipt_path = OUT / "execution_receipt.control.json"
    write_json(receipt_path, receipt)
    receipt_sha = sha_file(receipt_path)
    (OUT / "execution_receipt.control.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    return receipt_path, receipt_sha, overrides


def main() -> int:
    receipt, receipt_sha, overrides = build()
    print(json.dumps({"receipt": str(receipt), "sha256": receipt_sha, "overrides": overrides}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
