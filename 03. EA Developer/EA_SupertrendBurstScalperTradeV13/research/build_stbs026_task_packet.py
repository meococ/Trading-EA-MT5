from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-026"
EA_NAME = "EA_SupertrendBurstScalperTradeV13"
PACKAGE = ROOT / "03. EA Developer" / EA_NAME
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = PACKAGE / "research" / f"{HYPOTHESIS_ID}_MODEL0_BASELINE_PREREG.md"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST_MANIFEST = PACKAGE / "research" / f"{HYPOTHESIS_ID}_RESEARCH_COST_SOURCE_MANIFEST.json"
JOURNAL_BUDGET_ADDENDUM = (
    PACKAGE / "research" / f"{HYPOTHESIS_ID}_JOURNAL_BUDGET_ADDENDUM.md"
)
PRE_EXECUTION_HARNESS_ADDENDUM = (
    PACKAGE / "research" / f"{HYPOTHESIS_ID}_PRE_EXECUTION_HARNESS_ADDENDUM.md"
)
INDEPENDENT_PRE_PROBE_REVIEW = (
    PACKAGE / "research" / f"{HYPOTHESIS_ID}_INDEPENDENT_PRE_PROBE_REVIEW.md"
)
BOUNDED_DIFF_PROOF = (
    PACKAGE / "research" / f"{HYPOTHESIS_ID}_V12_V13_POSTCLAIM_RECONCILIATION_DIFF_PROOF.md"
)
COMPACT_TELEMETRY_TEST = (
    PACKAGE / "research" / "tests" / "test_stbs026_v13_identity_contract.py"
)
PARENT_PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV12"
PARENT_FAILURE_PACKET = (
    PARENT_PACKAGE / "research" / "HYP-STBS-XAUUSD-M15-025_POSTCLAIM_SELF_REJECTION_FAILURE.md"
)
PARENT_POST_FAILURE_REVIEW = (
    PARENT_PACKAGE / "research" / "HYP-STBS-XAUUSD-M15-025_INDEPENDENT_POST_FAILURE_REVIEW.md"
)
PROJECTION_PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV10"
PARENT_FAILURE_EVIDENCE = (
    PROJECTION_PACKAGE
    / "research"
    / "evidence"
    / "HYP-STBS-XAUUSD-M15-023"
    / "STBS023-FAILURE-CLOSE-001"
)
TESTER_NO_SPAM_PROJECTION = (
    PARENT_FAILURE_EVIDENCE / "tester_hyp023_no_spam_projection.utf16le.log"
)
AGENT_NO_SPAM_PROJECTION = (
    PARENT_FAILURE_EVIDENCE / "agent_hyp023_no_spam_projection.utf16le.log"
)
OUTPUT = PACKAGE / "research" / "preflight" / HYPOTHESIS_ID / "V1" / "task_packet.control.json"
BUILDER = Path(__file__).resolve()
GITIGNORE = ROOT / ".gitignore"
RESERVED_POST_PACKET_REVIEW = (
    PACKAGE / "research" / f"{HYPOTHESIS_ID}_POST_PACKET_REVIEW.md"
)
RESERVED_POST_PACKET_REVIEW_STATUS_LINE = (
    '?? "03. EA Developer/EA_SupertrendBurstScalperTradeV13/research/'
    'HYP-STBS-XAUUSD-M15-026_POST_PACKET_REVIEW.md"'
)
PACKET_ATTEMPT_ROOT = (
    PACKAGE / "research" / "evidence" / HYPOTHESIS_ID / "STBS026-PACKET-BUILD-001"
)
PACKET_ATTEMPT_START = PACKET_ATTEMPT_ROOT / "attempt_started.json"
PACKET_ATTEMPT_TERMINAL = PACKET_ATTEMPT_ROOT / "attempt_terminal.json"

PACKET_ONLY_AUTHORITY = "PACKET_BUILD_ONLY_NO_EXECUTION_NO_ECONOMICS"
PACKET_ATTEMPT_ID = "STBS026-PACKET-BUILD-001"
MT5_ATTEMPT_ID = "STBS026-MODEL0-TRAIN-001"
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

EXPECTED_SOURCE_SHA256 = "F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4"
EXPECTED_PREREG_SHA256 = "99D583ED3A4578D1CF0B3105CE10C3AD4CA74A9D1FBBE8C311573B2106DACE8A"
EXPECTED_CONTRACT_SHA256 = "4A2BAB503A148C78A85348B70340DDB0CDBBF31CD5941472BE0836BDE00A9578"
EXPECTED_COST_SHA256 = "5C9E00C6405D82D3756DF2E913E69B1E2E34E2405B8E76DFB7EBCDECF602C513"
EXPECTED_GITIGNORE_SHA256 = "A4C5E0639B9540FB3AC253AD3AE3434D3ADCAF1C17F6318F9C63625474C5CC8A"
EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256 = (
    "57D1D71A41020FCDE27D54A18D1C43FAD87BB4BFBA10F77BB5255B4F65E8F3B7"
)
EXPECTED_PARENT_TERMINAL_ROW_SHA256 = (
    "702308403DE58F752A8ECF6F249D7167546F9BD837D42F04386D4B3F3D86B6AA"
)
EXPECTED_PARENT_TERMINAL_VERDICT = (
    "KILL_POSTCLAIM_ONE_SHOT_SELF_REJECTION_NO_ALPHA_NO_MT5_NO_ECONOMIC_VERDICT"
)
EXPECTED_PARENT_FAILURE_PACKET_SHA256 = (
    "F1B8F99D3D49974D20B8A77A6C554A49A4FBE20AE4FA1067122C509623270292"
)
EXPECTED_PARENT_POST_FAILURE_REVIEW_SHA256 = (
    "3ED0948EB0C7D3E59C6E86539BAA38DA2E20E0AAB4C03884120AB41BBDBEBB9F"
)
EXPECTED_TESTER_PROJECTION_SHA256 = (
    "DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B"
)
EXPECTED_TESTER_PROJECTION_BYTES = 871692
EXPECTED_AGENT_PROJECTION_SHA256 = (
    "2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF"
)
EXPECTED_AGENT_PROJECTION_BYTES = 858852
EXPECTED_JOURNAL_BUDGET_ADDENDUM_SHA256 = (
    "17D03D4936C9146441BA01D6F4F16DB13CBC2B622E01C56E78EF291981854176"
)
EXPECTED_PRE_EXECUTION_HARNESS_ADDENDUM_SHA256 = (
    "68DAF00C76CDFEAC2F8558A6BC275A72E10D9CC3B7A68AD193C236A9CDF8D882"
)
EXPECTED_INDEPENDENT_PRE_PROBE_REVIEW_SHA256 = (
    "1F58551217D6AF2895D2E1A133A9F148D1037BC763FE0A8963817123C549FAF6"
)
EXPECTED_BOUNDED_DIFF_PROOF_SHA256 = (
    "7E1BD63D851B6E77C94106DBCE5B737EA7C1A04539B683C34B33D87745FF3095"
)
EXPECTED_COMPACT_TELEMETRY_TEST_SHA256 = (
    "66DD9F7B31A85DF16AEFBFC7941EB1B36D67707D890CF5B5F222DB7F96E19FDE"
)
OVERRIDES = (
    "InpAuditOnly=false;InpEnableTelemetry=true;"
    "InpHypothesisId=HYP-STBS-XAUUSD-M15-026;InpMagic=5604126;"
    "InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;"
    "InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;"
    "InpPercentStopoutHeadroomFactor=1.25;"
    "InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V13_POSTCLAIM_RECONCILE"
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


def write_exclusive_json(path: Path, payload: dict) -> bytes:
    raw = (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return raw


def strict_json_loads(raw: str) -> dict:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=reject_duplicates)
    if not isinstance(value, dict):
        raise RuntimeError("registry row must be a JSON object")
    return value


def claim_packet_attempt() -> str:
    PACKET_ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    PACKET_ATTEMPT_ROOT.mkdir(exist_ok=False)
    raw = write_exclusive_json(
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
    return hashlib.sha256(raw).hexdigest().upper()


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
    row = strict_json_loads(raw)
    row_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    if row.get("hypothesis_id") != HYPOTHESIS_ID or row.get("state") != "probe":
        raise RuntimeError("latest registry row is not the frozen HYP026 packet-only probe authority")
    if (
        row.get("source_hash") != EXPECTED_SOURCE_SHA256
        or row.get("prereg_sha256") != EXPECTED_PREREG_SHA256
        or row.get("parent_candidate") != "HYP-STBS-XAUUSD-M15-025"
    ):
        raise RuntimeError("HYP026 authority source/prereg binding is invalid")
    if row.get("verdict") != "FROZEN_HYP026_PACKET_BUILDER_SEMANTIC_AUTHORITY":
        raise RuntimeError("latest HYP026 authority has the wrong packet-builder verdict")
    metrics = row.get("metrics")
    validation = row.get("validation")
    if not isinstance(metrics, dict) or not isinstance(validation, dict):
        raise RuntimeError("HYP026 packet-builder authority metrics/validation are absent")
    if row.get("run_ids") != [] or any(
        metrics.get(name) != expected for name, expected in PROBE_ZERO_METRICS.items()
    ):
        raise RuntimeError("HYP026 packet-builder authority counters are not pristine")
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
        or validation.get("exact_outer_hypothesis_id") != HYPOTHESIS_ID
        or validation.get("exact_inner_mql_identity") != "HYP-STBS-XAUUSD-M15-026"
        or validation.get("exact_ea_name") != EA_NAME
        or validation.get("parent_hyp025_terminal_row_sha256") != EXPECTED_PARENT_TERMINAL_ROW_SHA256
        or validation.get("parent_hyp025_terminal_verdict") != EXPECTED_PARENT_TERMINAL_VERDICT
        or validation.get("parent_hyp025_failure_path") != repo_relative(PARENT_FAILURE_PACKET)
        or validation.get("parent_hyp025_failure_sha256") != EXPECTED_PARENT_FAILURE_PACKET_SHA256
        or validation.get("parent_hyp025_post_failure_review_path") != repo_relative(PARENT_POST_FAILURE_REVIEW)
        or validation.get("parent_hyp025_post_failure_review_sha256") != EXPECTED_PARENT_POST_FAILURE_REVIEW_SHA256
        or validation.get("journal_budget_tester_projection_path") != repo_relative(TESTER_NO_SPAM_PROJECTION)
        or validation.get("journal_budget_tester_projection_sha256") != EXPECTED_TESTER_PROJECTION_SHA256
        or validation.get("journal_budget_tester_projection_bytes") != EXPECTED_TESTER_PROJECTION_BYTES
        or validation.get("journal_budget_agent_projection_path") != repo_relative(AGENT_NO_SPAM_PROJECTION)
        or validation.get("journal_budget_agent_projection_sha256") != EXPECTED_AGENT_PROJECTION_SHA256
        or validation.get("journal_budget_agent_projection_bytes") != EXPECTED_AGENT_PROJECTION_BYTES
        or validation.get("journal_budget_addendum_path") != repo_relative(JOURNAL_BUDGET_ADDENDUM)
        or validation.get("journal_budget_addendum_sha256") != EXPECTED_JOURNAL_BUDGET_ADDENDUM_SHA256
        or validation.get("pre_execution_harness_addendum_path") != repo_relative(PRE_EXECUTION_HARNESS_ADDENDUM)
        or validation.get("pre_execution_harness_addendum_sha256") != EXPECTED_PRE_EXECUTION_HARNESS_ADDENDUM_SHA256
        or validation.get("independent_pre_run_review_path") != repo_relative(INDEPENDENT_PRE_PROBE_REVIEW)
        or validation.get("independent_pre_run_review_sha256") != EXPECTED_INDEPENDENT_PRE_PROBE_REVIEW_SHA256
        or validation.get("bounded_diff_proof_path") != repo_relative(BOUNDED_DIFF_PROOF)
        or validation.get("bounded_diff_proof_sha256") != EXPECTED_BOUNDED_DIFF_PROOF_SHA256
        or validation.get("source_contract_test_path") != repo_relative(COMPACT_TELEMETRY_TEST)
        or validation.get("source_contract_test_sha256") != EXPECTED_COMPACT_TELEMETRY_TEST_SHA256
        or validation.get("reserved_post_packet_review_path") != repo_relative(RESERVED_POST_PACKET_REVIEW)
        or validation.get("reserved_post_packet_review_placeholder_sha256") != EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256
    ):
        raise RuntimeError(
            "HYP026 packet-builder authority is not exact packet-only authority"
        )
    parent_raw = None
    parent_row = None
    for candidate_raw in reversed(rows[:-1]):
        candidate = strict_json_loads(candidate_raw)
        if candidate.get("hypothesis_id") == "HYP-STBS-XAUUSD-M15-025":
            parent_raw = candidate_raw
            parent_row = candidate
            break
    if parent_raw is None or parent_row is None:
        raise RuntimeError("terminal HYP025 parent row is absent from the same registry snapshot")
    parent_hash = hashlib.sha256(parent_raw.encode("utf-8")).hexdigest().upper()
    if (
        parent_hash != EXPECTED_PARENT_TERMINAL_ROW_SHA256
        or parent_row.get("state") != "killed"
        or parent_row.get("verdict") != EXPECTED_PARENT_TERMINAL_VERDICT
    ):
        raise RuntimeError("terminal HYP025 parent row is not the exact frozen post-claim kill")
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
            JOURNAL_BUDGET_ADDENDUM: EXPECTED_JOURNAL_BUDGET_ADDENDUM_SHA256,
            PRE_EXECUTION_HARNESS_ADDENDUM: EXPECTED_PRE_EXECUTION_HARNESS_ADDENDUM_SHA256,
            INDEPENDENT_PRE_PROBE_REVIEW: EXPECTED_INDEPENDENT_PRE_PROBE_REVIEW_SHA256,
            BOUNDED_DIFF_PROOF: EXPECTED_BOUNDED_DIFF_PROOF_SHA256,
            COMPACT_TELEMETRY_TEST: EXPECTED_COMPACT_TELEMETRY_TEST_SHA256,
            PARENT_FAILURE_PACKET: EXPECTED_PARENT_FAILURE_PACKET_SHA256,
            PARENT_POST_FAILURE_REVIEW: EXPECTED_PARENT_POST_FAILURE_REVIEW_SHA256,
            TESTER_NO_SPAM_PROJECTION: EXPECTED_TESTER_PROJECTION_SHA256,
            AGENT_NO_SPAM_PROJECTION: EXPECTED_AGENT_PROJECTION_SHA256,
            GITIGNORE: EXPECTED_GITIGNORE_SHA256,
            RESERVED_POST_PACKET_REVIEW: EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256,
        }
        for path, expected in frozen.items():
            actual = sha256_file(path)
            if actual != expected:
                raise RuntimeError(f"frozen input drift: {repo_relative(path)} {actual}")
        if (
            TESTER_NO_SPAM_PROJECTION.stat().st_size != EXPECTED_TESTER_PROJECTION_BYTES
            or AGENT_NO_SPAM_PROJECTION.stat().st_size != EXPECTED_AGENT_PROJECTION_BYTES
        ):
            raise RuntimeError("frozen no-spam journal projection byte budget drifted")

        registry_raw = REGISTRY.read_bytes()
        registry_sha256, registry_row_sha256, _ = latest_registry_identity(registry_raw)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        output_handle = OUTPUT.open("xb")
        try:
            git_status = git("status", "--short", "--untracked-files=all").splitlines()
            if git_status.count(RESERVED_POST_PACKET_REVIEW_STATUS_LINE) != 1:
                raise RuntimeError(
                    "reserved post-packet review path must occur exactly once in git status"
                )
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
            "max_journal_delta_bytes": 4194304,
        },
        "source_path": repo_relative(SOURCE),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "registry_path": repo_relative(REGISTRY),
        "registry_sha256": registry_sha256,
        "registry_row_sha256": registry_row_sha256,
        "parent_hypothesis_id": "HYP-STBS-XAUUSD-M15-025",
        "parent_terminal_row_sha256": EXPECTED_PARENT_TERMINAL_ROW_SHA256,
        "parent_terminal_verdict": EXPECTED_PARENT_TERMINAL_VERDICT,
        "parent_failure_packet_path": repo_relative(PARENT_FAILURE_PACKET),
        "parent_failure_packet_sha256": EXPECTED_PARENT_FAILURE_PACKET_SHA256,
        "parent_post_failure_review_path": repo_relative(PARENT_POST_FAILURE_REVIEW),
        "parent_post_failure_review_sha256": EXPECTED_PARENT_POST_FAILURE_REVIEW_SHA256,
        "journal_budget_tester_projection_path": repo_relative(TESTER_NO_SPAM_PROJECTION),
        "journal_budget_tester_projection_sha256": EXPECTED_TESTER_PROJECTION_SHA256,
        "journal_budget_tester_projection_bytes": EXPECTED_TESTER_PROJECTION_BYTES,
        "journal_budget_agent_projection_path": repo_relative(AGENT_NO_SPAM_PROJECTION),
        "journal_budget_agent_projection_sha256": EXPECTED_AGENT_PROJECTION_SHA256,
        "journal_budget_agent_projection_bytes": EXPECTED_AGENT_PROJECTION_BYTES,
        "journal_budget_projected_combined_bytes": EXPECTED_TESTER_PROJECTION_BYTES + EXPECTED_AGENT_PROJECTION_BYTES,
        "journal_budget_addendum_path": repo_relative(JOURNAL_BUDGET_ADDENDUM),
        "journal_budget_addendum_sha256": EXPECTED_JOURNAL_BUDGET_ADDENDUM_SHA256,
        "pre_execution_harness_addendum_path": repo_relative(PRE_EXECUTION_HARNESS_ADDENDUM),
        "pre_execution_harness_addendum_sha256": EXPECTED_PRE_EXECUTION_HARNESS_ADDENDUM_SHA256,
        "independent_pre_run_review_path": repo_relative(INDEPENDENT_PRE_PROBE_REVIEW),
        "independent_pre_run_review_sha256": EXPECTED_INDEPENDENT_PRE_PROBE_REVIEW_SHA256,
        "bounded_diff_proof_path": repo_relative(BOUNDED_DIFF_PROOF),
        "bounded_diff_proof_sha256": EXPECTED_BOUNDED_DIFF_PROOF_SHA256,
        "source_contract_test_path": repo_relative(COMPACT_TELEMETRY_TEST),
        "source_contract_test_sha256": EXPECTED_COMPACT_TELEMETRY_TEST_SHA256,
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
        "reserved_post_packet_review_path": repo_relative(RESERVED_POST_PACKET_REVIEW),
        "reserved_post_packet_review_placeholder_sha256": EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256,
        "reserved_post_packet_review_status_line": RESERVED_POST_PACKET_REVIEW_STATUS_LINE,
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
        if sha256_file(RESERVED_POST_PACKET_REVIEW) != EXPECTED_RESERVED_POST_PACKET_REVIEW_SHA256:
            raise RuntimeError(
                "reserved post-packet review placeholder changed before packet completion"
            )
        terminal_git_status = git(
            "status", "--short", "--untracked-files=all"
        ).splitlines()
        if (
            terminal_git_status != git_status
            or terminal_git_status.count(RESERVED_POST_PACKET_REVIEW_STATUS_LINE) != 1
        ):
            raise RuntimeError("git path set changed before packet completion")
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
