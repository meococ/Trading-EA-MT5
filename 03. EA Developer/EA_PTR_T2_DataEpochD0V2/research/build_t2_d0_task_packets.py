#!/usr/bin/env python3
"""Build the frozen nine-symbol T2 D0 collection task packets."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
PREFLIGHT = PACKAGE / "research" / "preflight" / "HYP-PTR-T2-DATA-EPOCH-D0-M5-002"
REGISTRY = WORKSPACE / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / "EA_PTR_T2_DataEpochD0V2.mq5"
PREREG = PACKAGE / "research" / "HYP-PTR-T2-DATA-EPOCH-D0-M5-002_PREREG.md"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST = PACKAGE / "research" / "COLLECTION_ONLY_COST_SOURCE_MANIFEST.json"

HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-002"
EA_NAME = "EA_PTR_T2_DataEpochD0V2"
EPOCH_SHA = "F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
MODEL = 0
BROKER_FINGERPRINT = "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54"
SERVER_FINGERPRINT = "9A5FF2C4C87709651E1E576FC6F87603238710F1B7B2F011F5377CD106F6EC3F"
ACCOUNT_FINGERPRINT = "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
EMPTY_INCLUDE_SHA = hashlib.sha256(b"").hexdigest().upper()

GEOMETRY = {
    "XAUUSD": {"digits": 2, "point": 0.01, "pip_size": 0.01},
    "BTCUSD": {"digits": 2, "point": 0.01, "pip_size": 0.01},
    "EURUSD": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
    "USDJPY": {"digits": 3, "point": 0.001, "pip_size": 0.01},
    "GBPUSD": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
    "USDCHF": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
    "USDCAD": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
    "AUDUSD": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
    "NZDUSD": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
}


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(WORKSPACE.resolve()).as_posix()


def git_snapshot() -> tuple[str, list[str], str]:
    commit = subprocess.check_output(
        ["git", "-C", str(WORKSPACE), "rev-parse", "HEAD"], text=True
    ).strip()
    result = subprocess.run(
        ["git", "-C", str(WORKSPACE), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    status = result.stdout.splitlines()
    return commit, status, sha_text("\n".join(status))


def registry_binding() -> tuple[str, str]:
    lines = REGISTRY.read_bytes().splitlines()
    if not lines:
        raise RuntimeError("candidate registry is empty")
    row = json.loads(lines[-1].decode("utf-8-sig"))
    if row.get("hypothesis_id") != HYPOTHESIS_ID or row.get("state") != "screened":
        raise RuntimeError(
            f"latest registry row is not the frozen {HYPOTHESIS_ID} screened row"
        )
    validation = row.get("validation")
    if not isinstance(validation, dict):
        raise RuntimeError("latest registry row lacks validation authority")
    artifact_bindings = (
        ("source", row.get("source_path"), row.get("source_hash"), SOURCE),
        ("prereg", row.get("prereg_path"), row.get("prereg_sha256"), PREREG),
        (
            "EA contract",
            validation.get("ea_contract_path"),
            validation.get("ea_contract_sha256"),
            EA_CONTRACT,
        ),
        (
            "cost source manifest",
            validation.get("cost_source_manifest_path"),
            validation.get("cost_source_manifest_sha256"),
            COST,
        ),
        (
            "packet builder core",
            validation.get("packet_builder_core_path"),
            validation.get("packet_builder_core_sha256"),
            Path(__file__).resolve(),
        ),
    )
    for label, registered_path, registered_sha, actual_path in artifact_bindings:
        if registered_path != rel(actual_path) or registered_sha != sha_file(actual_path):
            raise RuntimeError(f"latest registry row does not hash-bind the current {label}")
    if AUTHORITY == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE":
        if (
            validation.get("campaign_prebinding_status") != "BOUND_DATA_REPAIR"
            or validation.get("task_packet_authorized_next") is not True
            or validation.get("mt5_authorized") is not False
            or validation.get("performance_metrics_authorized") is not False
            or validation.get("economics_authorized") is not False
        ):
            raise RuntimeError(
                "latest registry row does not authorize collection-only packet creation"
            )
    return sha_file(REGISTRY), hashlib.sha256(lines[-1]).hexdigest().upper()


def packet(symbol: str, commit: str, status: list[str], status_sha: str) -> dict[str, object]:
    registry_sha, registry_row_sha = registry_binding()
    data_identity = f"FivePercentOnline-Real|{symbol}|M5|1970.01.01|2026.07.30|all_available_asof"
    return {
        "schema_version": "alphafactory_research_task_packet.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "source_path": rel(SOURCE),
        "source_sha256": sha_file(SOURCE),
        "registry_path": rel(REGISTRY),
        "registry_sha256": registry_sha,
        "registry_row_sha256": registry_row_sha,
        "prereg_path": rel(PREREG),
        "prereg_sha256": sha_file(PREREG),
        "ea_contract_path": rel(EA_CONTRACT),
        "ea_contract_sha256": sha_file(EA_CONTRACT),
        "telemetry_profile": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": symbol,
        "period": "M5",
        "from": "1970.01.01",
        "to": "2026.07.30",
        "data_quality_contract": {
            "history_quality": {"operator": "gt", "value": 97.0},
            "coverage_mode": "all_available_asof",
            "availability_asof_utc": "2026-07-30T23:59:59Z",
            "requested_from": "1970.01.01",
            "requested_to": "2026.07.30",
            "require_tester_journal_bounds": True,
        },
        "model": MODEL,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": (
            f"InpCollectionOnly=true;InpEpochManifestSha256={EPOCH_SHA};"
            f"InpExpectedTimeframe=5;InpGenerationId=T2;InpHypothesisId={HYPOTHESIS_ID}"
        ),
        "telemetry_tier": "off",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "validation_stage": "challenger",
        "holding_contract": "non_scalp",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2.0,
            "max_trades_per_week": 5.0,
            "max_drawdown_pct": 8.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "max_monte_carlo_p95_dd_pct": 8.0,
        },
        "git_commit": commit,
        "git_status": status,
        "git_status_sha256": status_sha,
        "include_closure": [],
        "include_closure_sha256": EMPTY_INCLUDE_SHA,
        "broker_fingerprint": BROKER_FINGERPRINT,
        "server_fingerprint": SERVER_FINGERPRINT,
        "account_fingerprint": ACCOUNT_FINGERPRINT,
        "data_fingerprint": sha_text(data_identity),
        "symbol_geometry": GEOMETRY[symbol],
        "required_sidecars": [],
        "required_manifest_hashes": [
            "source_sha256",
            "config_sha256",
            "report_sha256",
            "ex5_sha256",
            "includes_sha256",
        ],
        "cost_source_manifest_path": rel(COST),
        "cost_source_manifest_sha256": sha_file(COST),
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
    }


def main() -> int:
    PREFLIGHT.mkdir(parents=True, exist_ok=True)
    # Materialize all names first so the second-pass Git snapshot is stable.
    for symbol in GEOMETRY:
        (PREFLIGHT / f"task_packet.{symbol}.control.json").write_text("{}\n", encoding="utf-8")
    commit, status, status_sha = git_snapshot()
    for symbol in GEOMETRY:
        path = PREFLIGHT / f"task_packet.{symbol}.control.json"
        path.write_text(
            json.dumps(packet(symbol, commit, status, status_sha), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    commit_after, status_after, status_sha_after = git_snapshot()
    if (commit_after, status_after, status_sha_after) != (commit, status, status_sha):
        raise RuntimeError("Git snapshot changed while building task packets")
    print(f"TASK_PACKETS_OK count={len(GEOMETRY)} git_status_sha256={status_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
