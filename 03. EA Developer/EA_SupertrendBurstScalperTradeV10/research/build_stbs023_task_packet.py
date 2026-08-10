from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-023"
EA_NAME = "EA_SupertrendBurstScalperTradeV10"
PACKAGE = ROOT / "03. EA Developer" / EA_NAME
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = PACKAGE / "research" / f"{HYPOTHESIS_ID}_MODEL0_BASELINE_PREREG.md"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST_MANIFEST = PACKAGE / "research" / f"{HYPOTHESIS_ID}_RESEARCH_COST_SOURCE_MANIFEST.json"
OUTPUT = PACKAGE / "research" / "preflight" / HYPOTHESIS_ID / "V1" / "task_packet.control.json"
BUILDER = Path(__file__).resolve()
GITIGNORE = ROOT / ".gitignore"
PACKET_ATTEMPT_ROOT = (
    PACKAGE / "research" / "evidence" / HYPOTHESIS_ID / "STBS023-PACKET-BUILD-001"
)
PACKET_ATTEMPT_START = PACKET_ATTEMPT_ROOT / "attempt_started.json"
PACKET_ATTEMPT_TERMINAL = PACKET_ATTEMPT_ROOT / "attempt_terminal.json"

PACKET_ONLY_AUTHORITY = "PACKET_BUILD_ONLY_NO_EXECUTION_NO_ECONOMICS"
PACKET_ATTEMPT_ID = "STBS023-PACKET-BUILD-001"
MT5_ATTEMPT_ID = "STBS023-MODEL0-TRAIN-001"
PROBE_FALSE_FIELDS = (
    "mt5_train_run_authorized",
    "mt5_audit_run_authorized",
    "model0_audit_run_authorized",
    "mt5_authorized",
    "model0_authorized",
    "model0_data_acquisition_authorized",
    "model0_performance_authorized",
    "model4_authorized",
    "model4_data_acquisition_authorized",
    "model4_performance_authorized",
    "source_run_authorized",
    "compile_authorized",
    "run_compile_authorized",
    "mql5_compile_authorized",
    "standalone_compile_authorized",
    "trade_api_authorized",
    "performance_metrics_authorized",
    "outcome_prices_authorized",
    "post_event_ohlc_authorized",
    "artifact_collection_authorized",
    "comparator_execution_authorized",
    "visual_mode_authorized",
    "network_authorized",
    "paid_requests_authorized",
    "economics_authorized",
    "research_falsification_authorized",
    "optimization_authorized",
    "validation_authorized",
    "holdout_authorized",
    "research_validation_access_authorized",
    "research_holdout_access_authorized",
    "validation_access_authorized",
    "holdout_access_authorized",
    "economic_validity_authorized",
    "promotion_eligible",
    "paper_trading_authorized",
    "live_trading_authorized",
    "market_edge_claim_authorized",
    "same_id_retry_authorized",
    "registry_mutation_allowed",
)
PROBE_ZERO_METRICS = {
    "packet_build_attempt_limit": 1,
    "packet_build_attempts_consumed": 0,
    "mt5_attempt_limit": 1,
    "mt5_attempts_consumed": 0,
    "run_compile_attempt_limit": 1,
    "run_compile_attempts_consumed": 0,
    "model0_runs": 0,
    "mt5_launches": 0,
    "orders_executed": 0,
    "trades_simulated": 0,
    "returns_computed": 0,
    "performance_trials_executed": 0,
    "economics_executed": False,
    "research_validation_opened": False,
    "research_holdout_opened": False,
}

EXPECTED_SOURCE_SHA256 = "4B481CE867DB8A9F9E02AB218FEA50C88FD37A48B8ECB92E2048418DB7F7769B"
EXPECTED_PREREG_SHA256 = "24D607EA281C80359C57988E1680DE83BCBAEDD9AC3AE82A5F4226083F04DD26"
EXPECTED_CONTRACT_SHA256 = "4A2BAB503A148C78A85348B70340DDB0CDBBF31CD5941472BE0836BDE00A9578"
EXPECTED_COST_SHA256 = "9EE403BA01896DBC94EA271B2E2FE6EF9BB96E3D8EA1D21E510C2D504F137A97"
EXPECTED_GITIGNORE_SHA256 = "AB52FF98D7479D29EFA5C324622C77E9929E42939B5C3738C8FFDBB6B6C0B85C"
OVERRIDES = (
    "InpAuditOnly=false;InpEnableTelemetry=true;"
    "InpHypothesisId=HYP-STBS-XAUUSD-M15-023;InpMagic=5604123;"
    "InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;"
    "InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;"
    "InpPercentStopoutHeadroomFactor=1.25;"
    "InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V10_SL_STRESSED_MARGIN"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.rstrip("\r\n")


def write_exclusive_json(path: Path, payload: dict) -> None:
    raw = (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def claim_packet_attempt() -> str:
    PACKET_ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    PACKET_ATTEMPT_ROOT.mkdir(exist_ok=False)
    write_exclusive_json(
        PACKET_ATTEMPT_START,
        {
            "schema_version": "alphafactory_packet_attempt_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": PACKET_ATTEMPT_ID,
            "builder_path": repo_relative(BUILDER),
            "claimed_at_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        },
    )
    return sha256_file(PACKET_ATTEMPT_START)


def finish_packet_attempt(
    *, status: str, start_sha256: str, packet_sha256: str | None, error: str | None
) -> None:
    payload = {
        "schema_version": "alphafactory_packet_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": PACKET_ATTEMPT_ID,
        "status": status,
        "attempt_started_path": repo_relative(PACKET_ATTEMPT_START),
        "attempt_started_sha256": start_sha256,
        "packet_path": repo_relative(OUTPUT),
        "packet_sha256": packet_sha256,
        "error": error,
        "same_id_retry_authorized": False,
        "completed_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    write_exclusive_json(PACKET_ATTEMPT_TERMINAL, payload)


def latest_registry_identity(registry_raw: bytes | None = None) -> tuple[str, str, dict]:
    payload = REGISTRY.read_bytes() if registry_raw is None else registry_raw
    rows = [line for line in payload.decode("utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("candidate registry is empty")
    raw = rows[-1]
    row = json.loads(raw)
    row_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    if row.get("hypothesis_id") != HYPOTHESIS_ID or row.get("state") != "probe":
        raise RuntimeError("latest registry row is not the frozen HYP023 packet-only probe authority")
    if row.get("source_hash") != EXPECTED_SOURCE_SHA256 or row.get("prereg_sha256") != EXPECTED_PREREG_SHA256:
        raise RuntimeError("HYP023 authority source/prereg binding is invalid")
    if row.get("verdict") != "FROZEN_HYP023_PACKET_BUILDER_SEMANTIC_AUTHORITY":
        raise RuntimeError("latest HYP023 authority has the wrong packet-builder verdict")
    metrics = row.get("metrics")
    validation = row.get("validation")
    if not isinstance(metrics, dict) or not isinstance(validation, dict):
        raise RuntimeError("HYP023 packet-builder authority metrics/validation are absent")
    if row.get("run_ids") != [] or any(
        metrics.get(name) != expected for name, expected in PROBE_ZERO_METRICS.items()
    ):
        raise RuntimeError("HYP023 packet-builder authority counters are not pristine")
    if (
        validation.get("authority") != PACKET_ONLY_AUTHORITY
        or validation.get("packet_build_authorized") is not True
        or validation.get("packet_build_attempt_id") != PACKET_ATTEMPT_ID
        or validation.get("packet_build_attempt_limit") != 1
        or validation.get("mt5_attempt_id") != MT5_ATTEMPT_ID
        or validation.get("mt5_attempt_limit") != 1
        or "one_shot_economic_harness_version" in validation
        or any(validation.get(name) is not False for name in PROBE_FALSE_FIELDS)
        or validation.get("reviewed_task_packet_builder_path") != repo_relative(BUILDER)
        or validation.get("reviewed_task_packet_builder_sha256") != sha256_file(BUILDER)
    ):
        raise RuntimeError(
            "HYP023 packet-builder authority is not exact packet-only authority"
        )
    registry_hash = hashlib.sha256(payload).hexdigest().upper()
    return registry_hash, row_hash, row


def main() -> None:
    start_sha256 = claim_packet_attempt()
    packet_sha256: str | None = None
    try:
        frozen = {
            SOURCE: EXPECTED_SOURCE_SHA256,
            PREREG: EXPECTED_PREREG_SHA256,
            EA_CONTRACT: EXPECTED_CONTRACT_SHA256,
            COST_MANIFEST: EXPECTED_COST_SHA256,
            GITIGNORE: EXPECTED_GITIGNORE_SHA256,
        }
        for path, expected in frozen.items():
            actual = sha256_file(path)
            if actual != expected:
                raise RuntimeError(f"frozen input drift: {repo_relative(path)} {actual}")

        registry_raw = REGISTRY.read_bytes()
        registry_sha256, registry_row_sha256, _ = latest_registry_identity(registry_raw)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        output_handle = OUTPUT.open("xb")
        try:
            git_status = git("status", "--short", "--untracked-files=all").splitlines()
            git_status_payload = "\n".join(git_status).encode("utf-8")
            packet = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "inner_implementation_hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "M15",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "economic_window": {"from": "2018.01.02", "to": "2022.12.30"},
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 900,
        "attempt_id": MT5_ATTEMPT_ID,
        "attempt_limit": 1,
        "packet_build_attempt_id": PACKET_ATTEMPT_ID,
        "packet_build_attempt_start_path": repo_relative(PACKET_ATTEMPT_START),
        "packet_build_attempt_start_sha256": start_sha256,
        "overrides": OVERRIDES,
        "telemetry_tier": "trade-only",
        "telemetry_profile": "lifecycle-v3",
        "comparison_adapter": "generic-control-improvement-v1",
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
        "visual_mode": False,
        "indicator_dependencies": [],
        "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
        "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
        "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
        "data_fingerprint": "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25",
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "include_closure_sha256": "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
        "data_quality_contract": {
            "history_quality": {"operator": "gt", "value": 97.0},
            "coverage_mode": "fixed_window",
            "availability_asof_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "requested_from": "2005.01.01",
            "requested_to": "2023.01.01",
            "require_tester_journal_bounds": True,
        },
        "source_path": repo_relative(SOURCE),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "registry_path": repo_relative(REGISTRY),
        "registry_sha256": registry_sha256,
        "registry_row_sha256": registry_row_sha256,
        "prereg_path": repo_relative(PREREG),
        "prereg_sha256": EXPECTED_PREREG_SHA256,
        "ea_contract_path": repo_relative(EA_CONTRACT),
        "ea_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "validation_stage": "challenger",
        "holding_contract": "scalp",
        "include_closure": [],
        "required_manifest_hashes": [
            "source_sha256", "config_sha256", "report_sha256", "ex5_sha256", "includes_sha256"
        ],
        "cost_source_manifest_path": repo_relative(COST_MANIFEST),
        "cost_source_manifest_sha256": EXPECTED_COST_SHA256,
        "gitignore_path": repo_relative(GITIGNORE),
        "gitignore_sha256": EXPECTED_GITIGNORE_SHA256,
        "cost_evidence_tier": "research_proxy",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2,
            "max_trades_per_week": 5,
            "max_drawdown_pct": 8,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1,
            "max_monte_carlo_p95_dd_pct": 8,
        },
        "baseline_acceptance_contract": {
            "min_completed_trades": 500,
            "min_direction_share": 0.30,
            "max_year_trade_share": 0.30,
            "require_positive_cost_expectancy": True,
            "require_all_calendar_years_positive": True,
        },
        "performance_metrics_authorized": True,
        "economics_authorized": True,
        "promotion_eligible": False,
        "git_commit": git("rev-parse", "HEAD"),
        "git_status": git_status,
        "git_status_sha256": hashlib.sha256(git_status_payload).hexdigest().upper(),
            }

            payload = (json.dumps(packet, ensure_ascii=True, indent=2) + "\n").encode(
                "utf-8"
            )
            output_handle.write(payload)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        finally:
            output_handle.close()
        packet_sha256 = sha256_file(OUTPUT)
        finish_packet_attempt(
            status="COMPLETE",
            start_sha256=start_sha256,
            packet_sha256=packet_sha256,
            error=None,
        )
        print(
            json.dumps(
                {
                    "status": "BUILT",
                    "path": repo_relative(OUTPUT),
                    "sha256": packet_sha256,
                    "git_status_sha256": packet["git_status_sha256"],
                    "attempt_started_sha256": start_sha256,
                    "attempt_terminal_sha256": sha256_file(PACKET_ATTEMPT_TERMINAL),
                }
            )
        )
    except Exception as exc:
        if not PACKET_ATTEMPT_TERMINAL.exists():
            finish_packet_attempt(
                status="FAILED",
                start_sha256=start_sha256,
                packet_sha256=packet_sha256,
                error=f"{type(exc).__name__}: {exc}",
            )
        raise


if __name__ == "__main__":
    main()
