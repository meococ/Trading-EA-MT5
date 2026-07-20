#!/usr/bin/env python3
"""Build the fail-closed execution packet for the one HYP-024 collection."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
EA_NAME = "EA_ICTFVGReportFidelity"
HYPOTHESIS_ID = "HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024"
PARENT_HYPOTHESIS_ID = "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012"
AUTHORITY = "OWNER_AUTHORIZED_OUTCOME_BLIND_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION"
PACKAGE = ROOT / "03. EA Developer" / EA_NAME
RESEARCH = PACKAGE / "research"
EVIDENCE = RESEARCH / "evidence"
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = RESEARCH / f"{HYPOTHESIS_ID}_COLLECTION_PLAN.md"
MATRIX = RESEARCH / f"{HYPOTHESIS_ID}_LOGIC_TO_CODE_MATRIX.md"
PRESET = PACKAGE / "presets" / "EURUSD_M5_HYP024_TIME_RESILIENCE_COLLECT.set"
CAPABILITY = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
TICK_COVERAGE = EVIDENCE / "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018_TICK_COVERAGE.json"
TEST_RECEIPT = EVIDENCE / "20260719_HYP024_BUILD_TEST_RECEIPT.json"
SOURCE_RECEIPT = EVIDENCE / "20260719_SOURCE_BINARY_RECEIPT_V28.json"
TRIAL_LOG = EVIDENCE / "HYP024_TRIAL_LOG.jsonl"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
INCLUDES = [PACKAGE / "HumanContextEngine.mqh", PACKAGE / "NewsCalendar2019_2022.mqh"]
OUT = ROOT / "02. AlphaFactory" / "runtime" / "ict_fvg_hyp024_collection_receipt"

EXPECTED = {
    SOURCE: "3BC2130CE8F84AF44C6D3EFEC0639A7B461907A096A6AE90636479E6BB40E77B",
    PREREG: "6A80E4C97D19D901F6D96112114B0979F5065323E307D5907620FC77906E8269",
    MATRIX: "9BBE43380CFC24A35101A6CEBEE559572EAC6B97467E37853570EEEC667847E8",
    PRESET: "7192B0BC4963C8593B7F1C84D5D370EAC5EC45DEB28D7DBCAB4112649297A6BE",
    TICK_COVERAGE: "9A68530745B40F6B8E1AC4768F23FE6C052A2F99A5BC3654C4AF8A0E325191F6",
    TEST_RECEIPT: "B1BD8D120042EA288729118D5F97501C40F154C9B32D390B3603F505E6FB61FD",
    SOURCE_RECEIPT: "F969A70AACFBE30AC5A7FA2C461F6654603228B21E999DE1331CBA9E097A9E15",
}
ACCEPTANCE_CONTRACT = {
    "min_profit_factor": 1.3,
    "min_trades_per_week": 2,
    "max_trades_per_week": 5,
    "max_drawdown_pct": 8,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1,
    "max_monte_carlo_p95_dd_pct": 8,
}
REQUIRED_SIDECARS = sorted(
    [
        "*_HumanContext_*.csv",
        "*_LevelPath_*.csv",
        "*_LevelResilience_*.csv",
        "*_LifecycleTrades_*.csv",
        "*_RunMeta_*.json",
        "*_TickInitiation_*.csv",
    ]
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


def evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha_file(path),
    }


def frozen_overrides() -> str:
    values: dict[str, str] = {}
    for raw in PRESET.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        name, value = line.split("=", 1)
        if name in values:
            raise ValueError(f"duplicate preset input: {name}")
        values[name] = value
    required = {
        "InpResearchAutoMode": "false",
        "InpEnableTelemetry": "true",
        "InpSignalMode": "6",
        "InpRiskPercent": "0.01",
        "InpMagic": "5600733",
        "InpMaxAccountDrawdownPct": "100.00",
        "InpRequireNewsGuard": "false",
    }
    for name, expected in required.items():
        if values.get(name) != expected:
            raise ValueError(f"preset must bind {name}={expected}")
    return ";".join(f"{name}={values[name]}" for name in sorted(values))


def validate_frozen_inputs() -> tuple[dict, str]:
    for path in [*EXPECTED, CAPABILITY, TRIAL_LOG, REGISTRY, *INCLUDES]:
        if not path.is_file():
            raise ValueError(f"required evidence missing: {path}")
    for path, expected_hash in EXPECTED.items():
        if sha_file(path) != expected_hash:
            raise ValueError(f"frozen evidence drifted: {path}")
    latest = None
    latest_raw = ""
    for raw in REGISTRY.read_text(encoding="utf-8-sig").splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                latest = row
                latest_raw = raw
    if latest is None or latest.get("state") != "challenger":
        raise ValueError("latest HYP024 registry state must be challenger")
    validation = latest.get("validation") or {}
    if validation.get("model0_authorized") is not True:
        raise ValueError("HYP024 Model 0 is not authorized")
    if validation.get("performance_metrics_authorized") is not False:
        raise ValueError("HYP024 unexpectedly authorizes performance metrics")
    if validation.get("promotion_eligible") is not False:
        raise ValueError("HYP024 unexpectedly became promotion eligible")
    if latest.get("source_hash") != sha_file(SOURCE):
        raise ValueError("registry source hash does not match canonical source")
    if latest.get("prereg_sha256") != sha_file(PREREG):
        raise ValueError("registry prereg hash does not match frozen plan")
    if latest.get("acceptance_contract") != ACCEPTANCE_CONTRACT:
        raise ValueError("registry acceptance contract drifted")
    return latest, latest_raw


def build() -> dict[str, str]:
    latest, latest_raw = validate_frozen_inputs()
    overrides = frozen_overrides()
    task_path = OUT / "task_packet.control.json"
    cost_path = OUT / "cost_source_manifest.control.json"
    write_json(
        cost_path,
        {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "symbol": "EURUSD",
            "cost_status": "NOT_APPLICABLE_ZERO_TRADE_COLLECTION",
            "trading_authorized": False,
            "performance_metrics_authorized": False,
            "promotion_eligible": False,
            "note": "Mode 6 cannot call an order path and economics are forbidden.",
        },
    )
    include_closure = [
        {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha_file(path)}
        for path in INCLUDES
    ]
    include_rows = [
        f"{str(path.resolve()).lower()}\t{sha_file(path)}"
        for path in sorted(INCLUDES, key=lambda item: str(item.resolve()).lower())
    ]
    commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    write_json(
        task_path,
        {
            "schema_version": "alphafactory_research_task_packet.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
            "authority": AUTHORITY,
            "run_role": "control",
            "ea_name": EA_NAME,
            "source_path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": EXPECTED[SOURCE],
            "registry_path": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
            "registry_sha256": sha_file(REGISTRY),
            "registry_row_sha256": sha_text(latest_raw),
            "prereg_path": str(PREREG.relative_to(ROOT)).replace("\\", "/"),
            "prereg_sha256": EXPECTED[PREREG],
            "ea_contract_path": str(CAPABILITY.relative_to(ROOT)).replace("\\", "/"),
            "ea_contract_sha256": sha_file(CAPABILITY),
            "telemetry_profile": "lifecycle-v3",
            "comparison_adapter": "generic-control-improvement-v1",
            "symbol": "EURUSD",
            "period": "M5",
            "from": "2018.01.01",
            "to": "2026.07.19",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "trade-only",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "validation_stage": "challenger",
            "holding_contract": "scalp",
            "acceptance_contract": ACCEPTANCE_CONTRACT,
            "git_commit": commit,
            "git_status": status,
            "git_status_sha256": sha_text("\n".join(status)),
            "include_closure": include_closure,
            "include_closure_sha256": sha_text("\n".join(include_rows)),
            "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
            "server_fingerprint": "9A5FF2C4C87709651E1E576FC6F87603238710F1B7B2F011F5377CD106F6EC3F",
            "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
            "data_fingerprint": "2C6B361F68E76905DBBB951EB1F5E011EB4792286614B410CAC2A3C9688B3EA3",
            "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
            "required_sidecars": REQUIRED_SIDECARS,
            "required_manifest_hashes": [
                "source_sha256", "config_sha256", "report_sha256",
                "ex5_sha256", "includes_sha256",
            ],
            "cost_source_manifest_path": str(cost_path.resolve()),
            "cost_source_manifest_sha256": sha_file(cost_path),
            "matched_control_run_id": "",
            "matched_control_hypothesis_id": "",
            "matched_control_manifest_sha256": "",
            "matched_control_report_sha256": "",
            "matched_control_overrides": "",
            "matched_control_source_sha256": "",
            "matched_control_config_sha256": "",
            "matched_control_ex5_sha256": "",
            "matched_control_includes_sha256": "",
            "matched_control_git_commit": "",
            "matched_control_git_status_sha256": "",
            "wfa_artifact_path": "",
            "wfa_artifact_sha256": "",
            "variants_dir": "",
            "variants_sha256": "",
            "preset_path": str(PRESET.resolve()),
            "preset_sha256": EXPECTED[PRESET],
            "trading_authorized": False,
            "performance_metrics_authorized": False,
            "promotion_eligible": False,
            "allowed_reads": [
                "LevelResilience frozen identity, millisecond durations, natural label and interval fields",
                "HumanContext decision identity for one-to-one reconciliation",
                "RunMeta identity and frozen counters",
                "LifecycleTrades, TickInitiation and LevelPath row counts only",
                "run manifest identity, history quality, tick count and sidecar seal",
            ],
            "forbidden_reads": [
                "report profit, drawdown, balance, equity or trade result",
                "trade exits, PnL, commission, swap, MFE, MAE or future prices",
                "duration threshold, gap filter, tick floor, count predicate, label inversion, spread, session, direction or year mining",
            ],
            "note": "Exactly one frozen zero-trade outcome-blind time-weighted level-resilience collection.",
        },
    )
    bindings = [
        evidence("task_packet", task_path),
        evidence("candidate_registry", REGISTRY),
        evidence("source", SOURCE),
        evidence("ea_capability_contract", CAPABILITY),
        evidence("prereg", PREREG),
        evidence("logic_to_code_matrix", MATRIX),
        evidence("cost_source_manifest", cost_path),
        evidence("preset", PRESET),
        evidence("tick_coverage", TICK_COVERAGE),
        evidence("test_receipt", TEST_RECEIPT),
        evidence("source_binary_receipt", SOURCE_RECEIPT),
        evidence("trial_log", TRIAL_LOG),
    ]
    for index, include in enumerate(INCLUDES):
        bindings.append(evidence(f"include_{index:04d}", include))
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "authority": AUTHORITY,
        "registry_row_sha256": sha_text(latest_raw),
        "registry_file_sha256": sha_file(REGISTRY),
        "task_packet_sha256": sha_file(task_path),
        "git_commit": commit,
        "git_status_sha256": sha_text("\n".join(status)),
        "binding": {
            "hypothesis_id": HYPOTHESIS_ID,
            "run_role": "control",
            "ea_name": EA_NAME,
            "symbol": "EURUSD",
            "period": "M5",
            "from": "2018.01.01",
            "to": "2026.07.19",
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
            "include_closure_sha256": sha_text("\n".join(include_rows)),
        },
        "evidence": bindings,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "promotion_eligible": False,
    }
    receipt_path = OUT / "execution_receipt.control.json"
    write_json(receipt_path, receipt)
    receipt_sha = sha_file(receipt_path)
    (OUT / "execution_receipt.control.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    return {
        "task_packet": str(task_path),
        "cost_manifest": str(cost_path),
        "receipt": str(receipt_path),
        "receipt_sha256": receipt_sha,
        "overrides": overrides,
    }


if __name__ == "__main__":
    print(json.dumps(build()))
