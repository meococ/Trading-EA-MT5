#!/usr/bin/env python3
"""Build the fail-closed receipt for HYP-018 real-tick collection."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
EA_NAME = "EA_ICTFVGReportFidelity"
HYPOTHESIS_ID = "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018"
PARENT_HYPOTHESIS_ID = "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012"
AUTHORITY = "OWNER_AUTHORIZED_OUTCOME_BLIND_REAL_TICK_INITIATION_COLLECTION"
FROM_DATE = "2018.01.01"
TO_DATE = "2026.07.19"

PACKAGE = ROOT / "03. EA Developer" / EA_NAME
RESEARCH = PACKAGE / "research"
EVIDENCE = RESEARCH / "evidence"
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = RESEARCH / f"{HYPOTHESIS_ID}_COLLECTION_PLAN.md"
MATRIX = RESEARCH / f"{HYPOTHESIS_ID}_LOGIC_TO_CODE_MATRIX.md"
PRESET = PACKAGE / "presets" / "EURUSD_M5_HYP018_TICK_INIT_COLLECT.set"
CAPABILITY = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
TICK_COVERAGE = EVIDENCE / f"{HYPOTHESIS_ID}_TICK_COVERAGE.json"
TEST_RECEIPT = EVIDENCE / "20260719_HYP018_BUILD_TEST_RECEIPT.json"
SOURCE_RECEIPT = EVIDENCE / "20260719_SOURCE_BINARY_RECEIPT_V24.json"
TRIAL_LOG = EVIDENCE / "HYP018_TRIAL_LOG.jsonl"
INCLUDES = [PACKAGE / "HumanContextEngine.mqh", PACKAGE / "NewsCalendar2019_2022.mqh"]
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
OUT = ROOT / "02. AlphaFactory" / "runtime" / "ict_fvg_hyp018_collection_receipt"

EXPECTED_SOURCE_SHA256 = "41536FFC43BE85B1250A627197BD63FED5C7D5C7CF87D8965163F5449EACDA40"
EXPECTED_PREREG_SHA256 = "E7B4000A45090EC01253AB430867756B3B1623A0A74DFF593E05C4B3B5B471B5"
EXPECTED_MATRIX_SHA256 = "85BA86E1F8918A8023204D4525AF147326645B7CF8C615A1E1979AEF54CFF00A"
EXPECTED_PRESET_SHA256 = "EE1E6ECFE911A25FA3A919BDF901E50729BE4F3D43F41D32C8578FC0FA79258A"
EXPECTED_TICK_COVERAGE_SHA256 = "9A68530745B40F6B8E1AC4768F23FE6C052A2F99A5BC3654C4AF8A0E325191F6"
EXPECTED_TEST_RECEIPT_SHA256 = "6B96F60C8163C5AEBD8F2511A3C16396B8BF4A7F1A2610F90EA8AB5A166F6DFD"
EXPECTED_SOURCE_RECEIPT_SHA256 = "E863E4AFF3810527AC8E12C7FB9AA565CDFFA5B5E93B8793262F101794717CEA"
REQUIRED_SIDECARS = sorted([
    "*_HumanContext_*.csv",
    "*_LifecycleTrades_*.csv",
    "*_RunMeta_*.json",
    "*_TickInitiation_*.csv",
])


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
    return {"label": label, "kind": "file", "path": str(path.resolve()), "sha256": sha_file(path)}


def git_snapshot() -> tuple[str, str]:
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    process = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True,
        text=True,
        capture_output=True,
    )
    return commit, sha_text("\n".join(process.stdout.splitlines()))


def read_frozen_overrides() -> str:
    if sha_file(PRESET) != EXPECTED_PRESET_SHA256:
        raise ValueError("HYP-018 preset drifted")
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
        "InpResearchAutoMode": "false",
        "InpEnableTelemetry": "true",
        "InpSignalMode": "4",
        "InpRiskPercent": "0.01",
        "InpMagic": "5600728",
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
        raise ValueError("HYP-018 registry row is missing")
    latest = matches[-1]
    validation = latest.get("validation") or {}
    if latest.get("state") != "challenger":
        raise ValueError("latest HYP-018 registry state is not challenger")
    if validation.get("model0_authorized") is not True:
        raise ValueError("HYP-018 Model 0 is not authorized")
    if validation.get("performance_metrics_authorized") is not False:
        raise ValueError("HYP-018 unexpectedly authorizes performance metrics")
    if validation.get("promotion_eligible") is not False:
        raise ValueError("HYP-018 unexpectedly became promotion eligible")
    if latest.get("source_hash") != sha_file(SOURCE):
        raise ValueError("registry source hash does not match canonical source")
    if latest.get("prereg_sha256") != sha_file(PREREG):
        raise ValueError("registry prereg hash does not match frozen plan")


def build() -> tuple[Path, str, str]:
    required = [
        SOURCE, PREREG, MATRIX, PRESET, CAPABILITY, TICK_COVERAGE,
        TEST_RECEIPT, SOURCE_RECEIPT, TRIAL_LOG, REGISTRY, *INCLUDES,
    ]
    for path in required:
        if not path.is_file():
            raise ValueError(f"required evidence is missing: {path}")
    expected_hashes = {
        SOURCE: EXPECTED_SOURCE_SHA256,
        PREREG: EXPECTED_PREREG_SHA256,
        MATRIX: EXPECTED_MATRIX_SHA256,
        PRESET: EXPECTED_PRESET_SHA256,
        TICK_COVERAGE: EXPECTED_TICK_COVERAGE_SHA256,
        TEST_RECEIPT: EXPECTED_TEST_RECEIPT_SHA256,
        SOURCE_RECEIPT: EXPECTED_SOURCE_RECEIPT_SHA256,
    }
    for path, expected in expected_hashes.items():
        if sha_file(path) != expected:
            raise ValueError(f"frozen evidence drifted: {path}")
    validate_registry()
    overrides = read_frozen_overrides()

    task_path = OUT / "task_packet.control.json"
    cost_path = OUT / "cost_source_manifest.control.json"
    write_json(task_path, {
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
        "trading_authorized": False,
        "performance_metrics_authorized": False,
        "promotion_eligible": False,
        "allowed_reads": [
            "TickInitiation identity and quote-mid path fields",
            "HumanContext funnel/context fields",
            "RunMeta identity and counters",
            "LifecycleTrades row count only",
            "run manifest identity, history quality, tick count, and required-sidecar seal",
        ],
        "forbidden_reads": [
            "report profit, drawdown, balance, equity, or trade result",
            "trade exits, PnL, commission, swap, MFE, MAE, or any outcome field",
            "imbalance magnitude threshold mining",
        ],
        "note": "Exactly one frozen zero-trade, outcome-blind, real-tick initiation collection run.",
    })
    write_json(cost_path, {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "symbol": "EURUSD",
        "cost_status": "NOT_APPLICABLE_ZERO_TRADE_COLLECTION",
        "trading_authorized": False,
        "performance_metrics_authorized": False,
        "promotion_eligible": False,
        "note": "No order may be opened and no economics may be scored.",
    })

    evidence = [
        file_evidence("task_packet", task_path),
        file_evidence("candidate_registry", REGISTRY),
        file_evidence("source", SOURCE),
        file_evidence("ea_capability_contract", CAPABILITY),
        file_evidence("prereg", PREREG),
        file_evidence("logic_to_code_matrix", MATRIX),
        file_evidence("cost_source_manifest", cost_path),
        file_evidence("preset", PRESET),
        file_evidence("tick_coverage", TICK_COVERAGE),
        file_evidence("test_receipt", TEST_RECEIPT),
        file_evidence("source_binary_receipt", SOURCE_RECEIPT),
        file_evidence("trial_log", TRIAL_LOG),
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
    (OUT / "execution_receipt.control.sha256.txt").write_text(receipt_sha + "\n", encoding="utf-8")
    return receipt_path, receipt_sha, overrides


def main() -> int:
    receipt, receipt_sha, overrides = build()
    print(json.dumps({"receipt": str(receipt), "sha256": receipt_sha, "overrides": overrides}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
