from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-027"
PARENT_ID = "HYP-STBS-XAUUSD-M15-026"
TARGET_ID = "HYP-STBS-XAUUSD-M15-026"
ATTEMPT_ID = "STBS027-COMPARATOR-001"
EA_NAME = "EA_SupertrendBurstScalperTradeV13"
RUN_ID = "20260810_073648"

REGISTRY = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUN_ROOT = ROOT / "02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV13/20260810_073648"
ATTEMPT_ROOT = ROOT / "02. AlphaFactory/runtime/comparator_attempts" / HYPOTHESIS_ID / ATTEMPT_ID
PARENT_ATTEMPT_ROOT = ROOT / "02. AlphaFactory/runtime/model0_economic_attempts/HYP-STBS-XAUUSD-M15-026/STBS026-MODEL0-TRAIN-001"

PREREG = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-027_SEALED_EXISTING_RUN_RECOVERY_PREREG.md")
TEST = Path(__file__).with_name("tests") / "test_stbs027_sealed_existing_run.py"
PRE_REVIEW = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-027_INDEPENDENT_PRE_COMPARATOR_REVIEW.md")
PARENT_FAILURE = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-026_RUNTIME_NONREPAINT_PATH_FAILURE.md")
PARENT_REVIEW = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-026_INDEPENDENT_POST_FAILURE_REVIEW.md")
PARENT_TASK = Path(__file__).with_name("preflight") / PARENT_ID / "V1" / "task_packet.control.json"
PARENT_COST = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-026_RESEARCH_COST_SOURCE_MANIFEST.json")
PARENT_EXECUTION_RECEIPT = ROOT / "02. AlphaFactory/runtime/ea_execution_receipt_20260810_073640_32636_777afac3.json"
HYP013_TASK = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV3/research/preflight/HYP-STBS-XAUUSD-M15-013/V1/task_packet.control.json"
COST_SOURCE_ROOT = ROOT / "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/evidence/HYP-LASR-XAUUSD-M5-001/COST_SOURCE"
STATIC_NR_MANIFEST = Path(__file__).parents[1] / "HYP-STBS-XAUUSD-M15-026_NONREPAINT_MANIFEST.json"
STATIC_NR_AUDIT = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-026_NONREPAINT_AUDIT.json")
COMPILE_LOG = Path(__file__).parents[1] / "EA_SupertrendBurstScalperTradeV13.log"

AUDITOR = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
COST_BUILDER = ROOT / "02. AlphaFactory/tools/build_verified_cost_artifact.py"
UNIFIED = ROOT / "02. AlphaFactory/analysis/unified_validation.py"
QUANT = ROOT / "02. AlphaFactory/analysis/quant_analyzer.py"

PARENT_TERMINAL_ROW_SHA = "4BDE6051399987ACC4ABE96768B507741276952DBA34290BE002FB413D69D91F"
PARENT_TERMINAL_VERDICT = "KILL_RUNTIME_NONREPAINT_DERIVED_MANIFEST_PARENT_MISMATCH_NO_ADMISSIBLE_ECONOMIC_VERDICT"
PARENT_START_SHA = "850FA109EF88DD32F6AA365429856C0D95FBD4C40633DDEE6711E68DAFA7F35F"
PARENT_TERMINAL_SHA = "26E45DC012C4B7E5115D5FF027A2930D5DBB366CB40B7F233675D594DBE8C05C"
PARENT_FAILURE_SHA = "05D78766789969098D14C74B561CD7C44A0F00CFD683F71C3F63045946CB7FDA"
PARENT_REVIEW_SHA = "0F1E97017F9A0200B67734D793A457998DFD82BB5CAF8697E38CF9DF8012EB50"
PARENT_TASK_SHA = "4A5A570EF427AB4BFDB674D975FB065B96597623B1D6059894592D280E133710"
PARENT_COST_SHA = "5C9E00C6405D82D3756DF2E913E69B1E2E34E2405B8E76DFB7EBCDECF602C513"
PARENT_EXECUTION_RECEIPT_SHA = "4BF162519C150FDF6D8D03EB09024FD2ED0C74AB5319793EBEC7EAD8AC329E87"
HYP013_TASK_SHA = "DE25AE28B29087901514B1ABA067A00B8DF05F7F4288CF93D79188A730255DE9"
SPREAD_SOURCE_SHA = "6FBDB039300E571E30939F0149B504D53173836D0B0DDEA5772B33EA48AD0579"
COMMISSION_SOURCE_SHA = "5076439080F46F759AF3734E19749CC71584A9CB7F05C11E84DE7A9EAE6498C4"
SLIPPAGE_SOURCE_SHA = "515619377D67EADAC3B4A55AFCEE49FC2C5A7EE3D39BBE07B54316D9B9A4836E"
LINEAGE_RECEIPT_SHA = "55508F8F246A5524A8EA43A6118A0C2C47BFE06039A7EDDBC2C257068508A607"
RAW_TICK_FAILURE_SHA = "E43B91092B587D420FFDB28FAFB29F53ECB4175CCE0054A2C9252B7C366C8570"
STATIC_NR_MANIFEST_SHA = "958B4678772D2FFEF8DAC9A22ADCACEFCD0D868862180D02974C0C7433138E63"
STATIC_NR_AUDIT_SHA = "D94C9745A0349D946C242B72B2F230B03E43F7E6334711D9ACDB2F89A00DA1E0"

RUN_MANIFEST_SHA = "11566CBDED4B7466F3CA809162980C9387E1B0B949FBE1B6E6D15990C371D5BD"
REPORT_SHA = "706AE950D20C84DD24364722E613BF5C7C7105C5A2DAB0598E2FE89847E976C5"
JOURNAL_SHA = "7718C4205A70FEF32157B3286987077D8D35FAC988C94F4EBCA0DEB0D7579A9D"
LIFECYCLE_SHA = "0F3B393D7BFB764DD69BC670ABA68E7B8D1E36CBB743BC6D6A1AD33D1A171FDA"
RUNMETA_SHA = "EFF1941719BBA3478680FFC639E87B60506AE237C416429B9EE27947AE46A25D"
SOURCE_SHA = "F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4"
EX5_SHA = "94FE593C64E55A276B6C7E912B53D72087644954E09371B13292F9C048FDD45D"
CONFIG_SHA = "578B769FCC90A8EE5317213EB324DB745125D670EE7F0B2E59B9E1AEC466C12B"
OVERRIDES_SHA = "5A8AB484FBA56984486F6C461875483EE5D03A46EC3477251BBBED24D90FE299"
COMPILE_LOG_SHA = "224B3AA926D5342A3A205DE7BBEC4F99CE6A3B660D4BD828F73102DE75725279"

AUDITOR_SHA = "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360"
COST_BUILDER_SHA = "617AF7E526E7D30DBB7C6BBEF7B6DB3740552ABA31BFBFB0F6C42A4C1F8BB3AD"
UNIFIED_SHA = "E9C26801D020298AE6BADD1737ECE5B77778EA34951B99EB3A0B81F47D5E9DE2"
QUANT_SHA = "A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B"
DATA_SHA = "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25"
BROKER_SHA = "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54"
SERVER_SHA = "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0"
ACCOUNT_SHA = "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"

COPYTIME_LINE = 678
ECONOMIC_FROM = "2018.01.02"
ECONOMIC_TO = "2022.12.30"
ACCEPTANCE = {
    "min_profit_factor": 1.3,
    "min_trades_per_week": 2,
    "max_trades_per_week": 5,
    "max_drawdown_pct": 8,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1,
    "max_monte_carlo_p95_dd_pct": 8,
}
BASELINE = {
    "min_completed_trades": 500,
    "min_direction_share": 0.3,
    "max_year_trade_share": 0.3,
    "require_positive_cost_expectancy": True,
    "require_all_calendar_years_positive": True,
}
ENGINEERING_GATES = {
    "mt5_real_ticks_model",
    "nonrepaint_audit",
    "economic_window_coverage",
    "runner_invocation_success",
    "invocation_artifact_freshness",
    "equity_audit",
    "execution_reconciliation",
}
ADDITIONAL_ECONOMIC_GATES = {
    "monte_carlo_p95_drawdown",
    "overnight_weekend_exposure",
}

REQUIRED_TRUE = {
    "artifact_collection_authorized",
    "comparator_execution_authorized",
    "performance_metrics_authorized",
    "outcome_prices_authorized",
    "post_event_ohlc_authorized",
    "economics_authorized",
    "research_falsification_authorized",
}
REQUIRED_FALSE = {
    "packet_build_authorized",
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
    "visual_mode_authorized",
    "network_authorized",
    "paid_requests_authorized",
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
}
ZERO_METRICS: dict[str, object] = {
    "comparator_attempts_consumed": 0,
    "mt5_attempts_consumed": 0,
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


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def strict_json(raw: bytes, label: str) -> object:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(f"{label} duplicate JSON key: {key}")
            result[key] = value
        return result

    def bad_constant(value: str) -> object:
        raise RuntimeError(f"{label} nonfinite JSON value: {value}")

    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs_hook, parse_constant=bad_constant)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"{label} invalid JSON") from exc


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def claim() -> tuple[Path, str]:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    path = ATTEMPT_ROOT / "attempt_started.json"
    raw = canonical(
        {
            "schema_version": "stbs027_comparator_attempt_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "parent_hypothesis_id": PARENT_ID,
            "target_run_id": RUN_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": now(),
            "same_id_retry_authorized": False,
        }
    )
    exclusive(path, raw)
    return path, sha256_bytes(raw)


def registry_rows(raw_registry: bytes) -> list[tuple[dict[str, Any], str, bytes]]:
    result: list[tuple[dict[str, Any], str, bytes]] = []
    for number, raw in enumerate(raw_registry.splitlines(), 1):
        row = strict_json(raw, f"registry line {number}")
        if not isinstance(row, dict):
            raise RuntimeError(f"registry line {number} is not an object")
        result.append((row, sha256_bytes(raw), raw))
    return result


def validate_authority_row(row: dict[str, Any]) -> None:
    validation = row.get("validation")
    metrics = row.get("metrics")
    if not isinstance(validation, dict) or not isinstance(metrics, dict):
        raise RuntimeError("authority validation/metrics missing")
    if (
        row.get("state") != "screened"
        or row.get("parent_candidate") != PARENT_ID
        or row.get("evidence_contract_kind") != "economic"
        or row.get("model") != 0
        or row.get("source_hash") != SOURCE_SHA
        or row.get("acceptance_contract") != ACCEPTANCE
    ):
        raise RuntimeError("HYP027 root authority mismatch")
    expected = {
        "authority": "EXISTING_RUN_ECONOMIC_RECOVERY_ONLY",
        "comparator_attempt_id": ATTEMPT_ID,
        "comparator_attempt_limit": 1,
        "target_hypothesis_id": TARGET_ID,
        "target_run_id": RUN_ID,
        "parent_terminal_row_sha256": PARENT_TERMINAL_ROW_SHA,
        "run_manifest_sha256": RUN_MANIFEST_SHA,
        "run_report_sha256": REPORT_SHA,
        "run_journal_sha256": JOURNAL_SHA,
        "run_lifecycle_sha256": LIFECYCLE_SHA,
        "runmeta_sha256": RUNMETA_SHA,
        "run_source_snapshot_sha256": SOURCE_SHA,
        "run_ex5_snapshot_sha256": EX5_SHA,
        "run_config_snapshot_sha256": CONFIG_SHA,
        "parent_attempt_started_sha256": PARENT_START_SHA,
        "parent_attempt_terminal_sha256": PARENT_TERMINAL_SHA,
        "parent_failure_sha256": PARENT_FAILURE_SHA,
        "parent_failure_review_sha256": PARENT_REVIEW_SHA,
        "parent_task_packet_sha256": PARENT_TASK_SHA,
        "cost_source_manifest_sha256": PARENT_COST_SHA,
        "parent_execution_receipt_sha256": PARENT_EXECUTION_RECEIPT_SHA,
        "hyp013_preoutcome_task_sha256": HYP013_TASK_SHA,
        "historical_spread_source_sha256": SPREAD_SOURCE_SHA,
        "commission_source_sha256": COMMISSION_SOURCE_SHA,
        "slippage_source_sha256": SLIPPAGE_SOURCE_SHA,
        "cost_lineage_receipt_sha256": LINEAGE_RECEIPT_SHA,
        "raw_tick_failure_receipt_sha256": RAW_TICK_FAILURE_SHA,
        "reviewed_auditor_sha256": AUDITOR_SHA,
        "reviewed_cost_builder_sha256": COST_BUILDER_SHA,
        "reviewed_unified_validator_sha256": UNIFIED_SHA,
        "reviewed_quant_analyzer_sha256": QUANT_SHA,
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise RuntimeError(f"authority {key} mismatch")
    for key in REQUIRED_TRUE:
        if validation.get(key) is not True:
            raise RuntimeError(f"authority required-true mismatch: {key}")
    for key in REQUIRED_FALSE:
        if validation.get(key) is not False:
            raise RuntimeError(f"authority required-false mismatch: {key}")
    if metrics.get("comparator_attempt_limit") != 1:
        raise RuntimeError("comparator attempt limit mismatch")
    for key, value in ZERO_METRICS.items():
        if metrics.get(key) != value:
            raise RuntimeError(f"authority zero metric mismatch: {key}")


def authority() -> tuple[dict[str, Any], str, str, bytes, bytes, bytes]:
    raw_registry = REGISTRY.read_bytes()
    rows = registry_rows(raw_registry)
    parent_rows = [item for item in rows if item[0].get("hypothesis_id") == PARENT_ID]
    own_rows = [item for item in rows if item[0].get("hypothesis_id") == HYPOTHESIS_ID]
    if not parent_rows:
        raise RuntimeError("terminal HYP026 row absent")
    parent, parent_sha, parent_raw = parent_rows[-1]
    if (
        parent_sha != PARENT_TERMINAL_ROW_SHA
        or parent.get("state") != "killed"
        or parent.get("verdict") != PARENT_TERMINAL_VERDICT
    ):
        raise RuntimeError("terminal HYP026 row mismatch")
    if not own_rows:
        raise RuntimeError("HYP027 authority absent")
    row, row_sha, row_raw = own_rows[-1]
    validate_authority_row(row)
    return row, row_sha, sha256_bytes(raw_registry), raw_registry, row_raw, parent_raw


def capture_to(label: str, source: Path, expected_sha: str, target: Path) -> tuple[bytes, dict[str, object]]:
    raw = source.read_bytes()
    digest = sha256_bytes(raw)
    if digest != expected_sha:
        raise RuntimeError(f"{label} source hash mismatch")
    exclusive(target, raw)
    if sha256_file(target) != digest:
        raise RuntimeError(f"{label} capture mismatch")
    return raw, {
        "source_path": str(source),
        "captured_path": str(target),
        "sha256": digest,
        "length": len(raw),
    }


def capture_raw(label: str, raw: bytes, source_label: str, expected_sha: str, target: Path) -> tuple[bytes, dict[str, object]]:
    digest = sha256_bytes(raw)
    if digest != expected_sha:
        raise RuntimeError(f"{label} raw hash mismatch")
    exclusive(target, raw)
    if sha256_file(target) != digest:
        raise RuntimeError(f"{label} raw capture mismatch")
    return raw, {
        "source_path": source_label,
        "captured_path": str(target),
        "sha256": digest,
        "length": len(raw),
    }


def validate_original_manifest(payload: dict[str, Any]) -> None:
    expected = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": TARGET_ID,
        "run_id": RUN_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "M15",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 900,
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "telemetry_tier": "trade-only",
        "telemetry_profile": "lifecycle-v3",
        "visual_mode": False,
        "source_sha256": SOURCE_SHA,
        "ex5_sha256": EX5_SHA,
        "tester_ex5_sha256": EX5_SHA,
        "config_sha256": CONFIG_SHA,
        "report_sha256": REPORT_SHA,
        "contract_receipt_sha256": PARENT_EXECUTION_RECEIPT_SHA,
        "data_fingerprint": DATA_SHA,
        "broker_fingerprint": BROKER_SHA,
        "server_fingerprint": SERVER_SHA,
        "account_fingerprint": ACCOUNT_SHA,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"original manifest {key} mismatch")
    if payload.get("nondecision_provenance_copytime_authorized") is not None:
        raise RuntimeError("original manifest already contains provenance permission")
    dq = payload.get("data_quality_journal_delta")
    if dq != {
        "path": "logs/tester_journal_delta.log",
        "sha256": JOURNAL_SHA,
        "bytes_read": 1753472,
        "files_read": 3,
        "truncated": False,
    }:
        raise RuntimeError("original manifest journal contract mismatch")
    sidecars = payload.get("sidecars")
    if not isinstance(sidecars, list) or len(sidecars) != 3:
        raise RuntimeError("original manifest sidecar count mismatch")
    expected_sidecars = {
        "logs/tester_journal_delta.log": JOURNAL_SHA,
        "logs/XAUUSD_LifecycleTrades_HYP-STBS-XAUUSD-M15-026_5604126.csv": LIFECYCLE_SHA,
        "logs/XAUUSD_RunMeta_HYP-STBS-XAUUSD-M15-026_5604126.json": RUNMETA_SHA,
    }
    observed = {str(item.get("path")): str(item.get("sha256")) for item in sidecars if isinstance(item, dict)}
    if observed != expected_sidecars:
        raise RuntimeError("original manifest sidecar binding mismatch")


def build_derived_manifest(original_raw: bytes, sealed_run: Path) -> tuple[Path, str]:
    parsed = strict_json(original_raw, "original run manifest")
    if not isinstance(parsed, dict):
        raise RuntimeError("original run manifest root mismatch")
    validate_original_manifest(parsed)
    derived = dict(parsed)
    snapshot = sealed_run / "snapshot"
    derived.update(
        {
            "tester_ex5_path": str((snapshot / "build" / f"{EA_NAME}.ex5").resolve()),
            "config_file": str((sealed_run / "config" / "config.ini").resolve()),
            "report_path": str((sealed_run / "report.html").resolve()),
            "snapshot_root": str(snapshot.resolve()),
            "source_snapshot": str((snapshot / "source" / f"{EA_NAME}.mq5").resolve()),
            "ex5_snapshot": str((snapshot / "build" / f"{EA_NAME}.ex5").resolve()),
            "config_snapshot": str((snapshot / "config" / "config.ini").resolve()),
            "nondecision_provenance_copytime_authorized": True,
            "nondecision_provenance_authority_source": {
                "path": str(STATIC_NR_MANIFEST.resolve()),
                "sha256": STATIC_NR_MANIFEST_SHA,
                "original_run_manifest_sha256": RUN_MANIFEST_SHA,
                "scope": "single exact DATA_EPOCH_D0 CopyTime first-date proof; no decision or outcome access",
            },
        }
    )
    target = sealed_run / "run_manifest.json"
    exclusive(target, canonical(derived))
    return target, sha256_file(target)


def build_derived_cost_manifest(original_raw: bytes, controls: Path) -> tuple[Path, str]:
    parsed = strict_json(original_raw, "parent cost manifest")
    if not isinstance(parsed, dict):
        raise RuntimeError("parent cost manifest root mismatch")
    if (
        parsed.get("schema_version") != "alphafactory_cost_source_manifest.v1"
        or parsed.get("evidence_tier") != "RESEARCH_PROXY"
        or parsed.get("hypothesis_id") != TARGET_ID
        or parsed.get("ea_name") != EA_NAME
        or parsed.get("data_fingerprint") != DATA_SHA
        or parsed.get("broker_fingerprint") != BROKER_SHA
        or parsed.get("server_fingerprint") != SERVER_SHA
        or parsed.get("account_fingerprint") != ACCOUNT_SHA
        or parsed.get("from") != ECONOMIC_FROM
        or parsed.get("to") != ECONOMIC_TO
        or parsed.get("promotion_eligible") is not False
    ):
        raise RuntimeError("parent cost manifest semantic mismatch")
    derived = json.loads(json.dumps(parsed))
    derived["data_fingerprint_basis"]["preoutcome_hyp013_task"] = str((controls / "cost_sources/hyp013_task.json").resolve())
    derived["historical_spread_provenance"]["source"] = str((controls / "cost_sources/historical_spread.csv").resolve())
    derived["commission_provenance"]["source"] = str((controls / "cost_sources/commission.csv").resolve())
    derived["slippage_provenance"]["source"] = str((controls / "cost_sources/slippage.csv").resolve())
    derived["lineage_receipt"] = str((controls / "cost_sources/lineage_receipt.json").resolve())
    derived["failed_raw_tick_acquisition_receipt"] = str((controls / "cost_sources/raw_tick_failure.json").resolve())
    target = controls / "derived_cost_manifest.json"
    exclusive(target, canonical(derived))
    return target, sha256_file(target)


def run_tool(label: str, command: list[str], stdout_path: Path, stderr_path: Path, allowed: set[int]) -> int:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
    exclusive(stdout_path, completed.stdout)
    exclusive(stderr_path, completed.stderr)
    if completed.returncode not in allowed:
        raise RuntimeError(f"{label} failed with exit {completed.returncode}")
    return completed.returncode


def validate_nonrepaint(audit_path: Path, manifest_path: Path, manifest_sha: str, source_path: Path) -> dict[str, Any]:
    payload = strict_json(audit_path.read_bytes(), "runtime non-repaint audit")
    if not isinstance(payload, dict):
        raise RuntimeError("runtime non-repaint audit root mismatch")
    expected_keys = {
        "schema_version", "status", "hypothesis_id", "run_id", "manifest",
        "manifest_sha256", "collection_authority_verified", "audited_files",
        "findings", "allowed_new_bar_gates", "generated_at_utc",
    }
    if set(payload) != expected_keys:
        raise RuntimeError("runtime non-repaint audit key set mismatch")
    if (
        payload.get("schema_version") != "alphafactory_nonrepaint_audit.v1"
        or payload.get("status") != "PASS"
        or payload.get("hypothesis_id") != TARGET_ID
        or payload.get("run_id") != RUN_ID
        or Path(str(payload.get("manifest"))).resolve() != manifest_path.resolve()
        or payload.get("manifest_sha256") != manifest_sha
        or payload.get("collection_authority_verified") is not False
        or payload.get("findings") != []
    ):
        raise RuntimeError("runtime non-repaint identity/status mismatch")
    audited = payload.get("audited_files")
    allowed = payload.get("allowed_new_bar_gates")
    if audited != [{"path": str(source_path.resolve()), "sha256": SOURCE_SHA}]:
        raise RuntimeError("runtime non-repaint audited source mismatch")
    expected_gate = {
        "path": str(source_path.resolve()),
        "line": COPYTIME_LINE,
        "rule": "collection_first_date_copytime",
        "function": "CopyTime",
        "disposition": "allowed_collection_provenance_read",
    }
    if allowed != [expected_gate]:
        raise RuntimeError("runtime non-repaint allowance mismatch")
    return payload


def validate_cost(cost: dict[str, Any], report_path: Path) -> None:
    if (
        cost.get("schema_version") != "research_execution_cost_proxy.v1"
        or cost.get("provenance_status") != "VERIFIED_RESEARCH_PROXY"
        or cost.get("promotion_eligible") is not False
        or cost.get("hypothesis_id") != TARGET_ID
        or cost.get("run_id") != RUN_ID
        or Path(str(cost.get("report"))).resolve() != report_path.resolve()
        or cost.get("report_sha256") != REPORT_SHA
    ):
        raise RuntimeError("verified cost artifact identity/status mismatch")
    economic_window = cost.get("economic_window")
    if (
        not isinstance(economic_window, dict)
        or economic_window.get("from") != ECONOMIC_FROM
        or economic_window.get("to") != ECONOMIC_TO
        or economic_window.get("boundary") != "inclusive_calendar_dates"
        or economic_window.get("trade_deal_count") != 928
        or set(economic_window) != {
            "from", "to", "boundary", "trade_deal_count",
            "first_trade_deal_time", "last_trade_deal_time",
        }
    ):
        raise RuntimeError("verified cost economic window mismatch")
    lifecycle = cost.get("lifecycle_evidence")
    runmeta = cost.get("run_meta_evidence")
    if not isinstance(lifecycle, dict) or lifecycle.get("completed_positions") != 464:
        raise RuntimeError("verified cost lifecycle count mismatch")
    if not isinstance(runmeta, dict) or runmeta.get("hypothesis_id") != TARGET_ID:
        raise RuntimeError("verified cost RunMeta mismatch")
    semantic = runmeta.get("semantic")
    if not isinstance(semantic, dict) or semantic.get("runtime_failed") is not False or semantic.get("row_count_reconciled") is not True:
        raise RuntimeError("verified cost RunMeta semantic mismatch")
    rows = cost.get("trade_repricing")
    scenarios = cost.get("scenarios")
    if not isinstance(rows, list) or len(rows) != 464 or not isinstance(scenarios, list):
        raise RuntimeError("verified cost repricing shape mismatch")
    if [row.get("scenario") for row in scenarios if isinstance(row, dict)] != ["cost_x1_00", "cost_x1_50", "cost_x2_00"]:
        raise RuntimeError("verified cost scenarios mismatch")


def validation_projection(summary: dict[str, Any]) -> dict[str, Any]:
    output_dir = str(summary.get("output_dir") or "")
    volatile_keys = {
        "invocation_id", "invocation_start_utc", "generated_at_utc",
        "started_at_utc", "finished_at_utc", "completed_at_utc",
        "duration_seconds", "elapsed_seconds",
    }

    def stable(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: stable(item)
                for key, item in value.items()
                if key not in volatile_keys
                and key != "artifact"
                and not key.endswith("_path")
                and not key.endswith("_sha256")
            }
        if isinstance(value, list):
            return [stable(item) for item in value]
        if isinstance(value, str) and output_dir:
            return value.replace(output_dir, "<VALIDATION_OUTPUT>")
        return value

    gates = summary.get("gates") if isinstance(summary.get("gates"), dict) else {}
    keys = [
        "schema_version", "stage", "holding_contract", "thresholds",
        "verdict", "non_passing_gates",
        "economic_window", "baseline_acceptance_contract",
        "baseline_falsification_gate_names", "baseline_falsification_non_passing_gates",
        "baseline_falsification_verdict", "research_cost_proxy",
        "research_falsification_eligible", "promotion_eligible",
    ]
    projection = {key: summary.get(key) for key in keys}
    projection["all_gates"] = gates
    return stable(projection)  # type: ignore[return-value]


def gate_statuses(summary: dict[str, Any]) -> dict[str, str]:
    gates = summary.get("gates")
    if not isinstance(gates, dict):
        raise RuntimeError("unified gates missing")
    result: dict[str, str] = {}
    for name, gate in gates.items():
        if not isinstance(name, str) or not isinstance(gate, dict) or gate.get("status") not in {"PASS", "FAIL", "BLOCKED"}:
            raise RuntimeError("unified gate shape/status mismatch")
        result[name] = str(gate["status"])
    return result


def validate_summary(summary: dict[str, Any], return_code: int) -> None:
    if (
        summary.get("schema_version") != "alphafactory_validation_summary.v2"
        or summary.get("stage") != "challenger"
        or summary.get("holding_contract") != "scalp"
        or summary.get("research_cost_proxy") is not True
        or summary.get("research_falsification_eligible") is not True
        or summary.get("promotion_eligible") is not False
        or summary.get("economic_window") != {
            "from": ECONOMIC_FROM,
            "to": ECONOMIC_TO,
            "boundary": "inclusive_calendar_dates",
        }
    ):
        raise RuntimeError("unified validation identity/status mismatch")
    statuses = gate_statuses(summary)
    expected_non_passing = [name for name in summary.get("gates", {}) if statuses[name] != "PASS"]
    if summary.get("non_passing_gates") != expected_non_passing:
        raise RuntimeError("unified overall non-passing gate reconciliation mismatch")
    expected_overall = "PASS" if not expected_non_passing else "REVIEW"
    if summary.get("verdict") != expected_overall:
        raise RuntimeError("unified overall verdict reconciliation mismatch")
    if (return_code == 0) != (expected_overall == "PASS") or return_code not in {0, 1}:
        raise RuntimeError("unified exit-code/verdict mismatch")

    baseline_names = summary.get("baseline_falsification_gate_names")
    if not isinstance(baseline_names, list) or not all(isinstance(name, str) and name in statuses for name in baseline_names):
        raise RuntimeError("unified baseline gate names mismatch")
    expected_baseline_non_passing = [name for name in baseline_names if statuses[name] != "PASS"]
    if summary.get("baseline_falsification_non_passing_gates") != expected_baseline_non_passing:
        raise RuntimeError("unified baseline non-passing gate reconciliation mismatch")
    expected_baseline = (
        "BLOCKED" if any(statuses[name] == "BLOCKED" for name in baseline_names)
        else "FAIL" if expected_baseline_non_passing
        else "PASS"
    )
    if summary.get("baseline_falsification_verdict") != expected_baseline:
        raise RuntimeError("unified baseline verdict reconciliation mismatch")
    missing_engineering = sorted(ENGINEERING_GATES - set(statuses))
    missing_economic = sorted(ADDITIONAL_ECONOMIC_GATES - set(statuses))
    if missing_engineering or missing_economic:
        raise RuntimeError(f"unified mandatory gates missing: engineering={missing_engineering}; economic={missing_economic}")


def classify_summary(summary: dict[str, Any]) -> dict[str, object]:
    statuses = gate_statuses(summary)
    engineering_non_passing = sorted(name for name in ENGINEERING_GATES if statuses.get(name) != "PASS")
    baseline_names = list(summary["baseline_falsification_gate_names"])
    economic_names = sorted((set(baseline_names) - ENGINEERING_GATES) | ADDITIONAL_ECONOMIC_GATES)
    economic_blocked = sorted(name for name in economic_names if statuses.get(name) == "BLOCKED")
    economic_failed = sorted(name for name in economic_names if statuses.get(name) == "FAIL")
    if engineering_non_passing or economic_blocked:
        verdict = "KILL_ENGINEERING_UNIFIED_PREREQUISITE_BLOCKED_NO_ECONOMIC_VERDICT"
        economic_valid = False
        economic_verdict_created = False
    elif economic_failed:
        verdict = "FAIL_ECONOMIC_BASELINE_RESEARCH_PROXY_EXACT_MAPPING"
        economic_valid = False
        economic_verdict_created = True
    else:
        verdict = "PASS_ECONOMIC_BASELINE_RESEARCH_PROXY_NONPROMOTABLE"
        economic_valid = True
        economic_verdict_created = True
    return {
        "verdict": verdict,
        "engineering_non_passing_gates": engineering_non_passing,
        "economic_blocked_gates": economic_blocked,
        "economic_failed_gates": economic_failed,
        "economic_valid": economic_valid,
        "economic_verdict_created": economic_verdict_created,
    }


def execute() -> dict[str, Any]:
    start_path, start_sha = claim()
    context: dict[str, object] = {}
    try:
        row, row_sha, registry_sha, registry_raw, authority_raw, parent_raw = authority()
        context.update({"authority_row_sha256": row_sha, "registry_sha256_at_claim": registry_sha})
        captured_root = ATTEMPT_ROOT / "captured"
        sealed_run = ATTEMPT_ROOT / "sealed_run"
        evidence: dict[str, dict[str, object]] = {}
        captured: dict[str, bytes] = {}

        def bind(label: str, source: Path, digest: str, target: Path | None = None) -> bytes:
            raw, meta = capture_to(label, source, digest, target or (captured_root / label))
            captured[label] = raw
            evidence[label] = meta
            return raw

        bind("original_run_manifest.json", RUN_ROOT / "run_manifest.json", RUN_MANIFEST_SHA)
        bind("report.html", RUN_ROOT / "report.html", REPORT_SHA, sealed_run / "report.html")
        bind("journal.log", RUN_ROOT / "logs/tester_journal_delta.log", JOURNAL_SHA, sealed_run / "logs/tester_journal_delta.log")
        bind("lifecycle.csv", RUN_ROOT / "logs/XAUUSD_LifecycleTrades_HYP-STBS-XAUUSD-M15-026_5604126.csv", LIFECYCLE_SHA, sealed_run / "logs/XAUUSD_LifecycleTrades_HYP-STBS-XAUUSD-M15-026_5604126.csv")
        bind("runmeta.json", RUN_ROOT / "logs/XAUUSD_RunMeta_HYP-STBS-XAUUSD-M15-026_5604126.json", RUNMETA_SHA, sealed_run / "logs/XAUUSD_RunMeta_HYP-STBS-XAUUSD-M15-026_5604126.json")
        bind("source.mq5", RUN_ROOT / f"snapshot/source/{EA_NAME}.mq5", SOURCE_SHA, sealed_run / f"snapshot/source/{EA_NAME}.mq5")
        bind("ea.ex5", RUN_ROOT / f"snapshot/build/{EA_NAME}.ex5", EX5_SHA, sealed_run / f"snapshot/build/{EA_NAME}.ex5")
        bind("config.ini", RUN_ROOT / "snapshot/config/config.ini", CONFIG_SHA, sealed_run / "snapshot/config/config.ini")
        bind("overrides.txt", RUN_ROOT / "overrides.txt", OVERRIDES_SHA, sealed_run / "overrides.txt")
        bind("parent_attempt_started.json", PARENT_ATTEMPT_ROOT / "attempt_started.json", PARENT_START_SHA)
        bind("parent_attempt_terminal.json", PARENT_ATTEMPT_ROOT / "attempt_terminal.json", PARENT_TERMINAL_SHA)
        bind("parent_task_packet.json", PARENT_TASK, PARENT_TASK_SHA)
        bind("parent_execution_receipt.json", PARENT_EXECUTION_RECEIPT, PARENT_EXECUTION_RECEIPT_SHA)
        bind("parent_cost_manifest.json", PARENT_COST, PARENT_COST_SHA)
        bind("hyp013_task.json", HYP013_TASK, HYP013_TASK_SHA, ATTEMPT_ROOT / "controls/cost_sources/hyp013_task.json")
        bind("historical_spread.csv", COST_SOURCE_ROOT / "XAUUSD_HISTORICAL_SPREAD_M1.csv", SPREAD_SOURCE_SHA, ATTEMPT_ROOT / "controls/cost_sources/historical_spread.csv")
        bind("commission.csv", COST_SOURCE_ROOT / "XAUUSD_TESTER_COMMISSION_MAX.csv", COMMISSION_SOURCE_SHA, ATTEMPT_ROOT / "controls/cost_sources/commission.csv")
        bind("slippage.csv", COST_SOURCE_ROOT / "XAUUSD_QUOTE_LATENCY_1000MS.csv", SLIPPAGE_SOURCE_SHA, ATTEMPT_ROOT / "controls/cost_sources/slippage.csv")
        bind("lineage_receipt.json", COST_SOURCE_ROOT / "RESEARCH_COST_PROXY_RECEIPT.json", LINEAGE_RECEIPT_SHA, ATTEMPT_ROOT / "controls/cost_sources/lineage_receipt.json")
        bind("raw_tick_failure.json", COST_SOURCE_ROOT / "RAW_TICK_ACQUISITION_FAILURE.json", RAW_TICK_FAILURE_SHA, ATTEMPT_ROOT / "controls/cost_sources/raw_tick_failure.json")
        bind("static_nonrepaint_manifest.json", STATIC_NR_MANIFEST, STATIC_NR_MANIFEST_SHA)
        bind("static_nonrepaint_audit.json", STATIC_NR_AUDIT, STATIC_NR_AUDIT_SHA)
        bind("parent_failure.md", PARENT_FAILURE, PARENT_FAILURE_SHA)
        bind("parent_failure_review.md", PARENT_REVIEW, PARENT_REVIEW_SHA)
        bind("run_compile.log", COMPILE_LOG, COMPILE_LOG_SHA)
        bind("auditor.py", AUDITOR, AUDITOR_SHA)
        bind("cost_builder.py", COST_BUILDER, COST_BUILDER_SHA)
        bind("unified_validation.py", UNIFIED, UNIFIED_SHA)
        bind("quant_analyzer.py", QUANT, QUANT_SHA)
        bind("comparator.py", Path(__file__), str(row["validation"].get("reviewed_comparator_sha256", "")))
        bind("prereg.md", PREREG, str(row["validation"].get("reviewed_prereg_sha256", "")))
        bind("test.py", TEST, str(row["validation"].get("reviewed_test_sha256", "")))
        bind("independent_pre_review.md", PRE_REVIEW, str(row["validation"].get("independent_pre_comparator_review_sha256", "")))

        _, evidence["registry_snapshot.jsonl"] = capture_raw(
            "registry_snapshot.jsonl", registry_raw, str(REGISTRY), registry_sha, captured_root / "registry_snapshot.jsonl"
        )
        _, evidence["authority_row.json"] = capture_raw(
            "authority_row.json", authority_raw, f"{REGISTRY}#latest-{HYPOTHESIS_ID}", row_sha, captured_root / "authority_row.json"
        )
        _, evidence["parent_terminal_row.json"] = capture_raw(
            "parent_terminal_row.json", parent_raw, f"{REGISTRY}#latest-{PARENT_ID}", PARENT_TERMINAL_ROW_SHA, captured_root / "parent_terminal_row.json"
        )

        compile_text = captured["run_compile.log"].decode(
            "utf-16" if captured["run_compile.log"].startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig",
            errors="strict",
        )
        if len(re.findall(r"(?m)^Result:\s*0 errors,\s*0 warnings(?:,.*)?\s*$", compile_text)) != 1:
            raise RuntimeError("run compile log is not exact 0E/0W")

        derived_manifest, derived_sha = build_derived_manifest(captured["original_run_manifest.json"], sealed_run)
        derived_cost_manifest, derived_cost_sha = build_derived_cost_manifest(
            captured["parent_cost_manifest.json"], ATTEMPT_ROOT / "controls"
        )
        audit_path = ATTEMPT_ROOT / "analysis/nonrepaint_audit.json"
        run_tool(
            "non-repaint audit",
            [sys.executable, str(AUDITOR), "--manifest", str(derived_manifest), "--out", str(audit_path)],
            ATTEMPT_ROOT / "tool_logs/nonrepaint.stdout",
            ATTEMPT_ROOT / "tool_logs/nonrepaint.stderr",
            {0},
        )
        audit = validate_nonrepaint(
            audit_path,
            derived_manifest,
            derived_sha,
            sealed_run / f"snapshot/source/{EA_NAME}.mq5",
        )

        cost_path = ATTEMPT_ROOT / "analysis/verified_cost_artifact.json"
        run_tool(
            "verified cost builder",
            [
                sys.executable, str(COST_BUILDER),
                "--report", str(sealed_run / "report.html"),
                "--cost-source-manifest", str(derived_cost_manifest),
                "--economic-from", ECONOMIC_FROM,
                "--economic-to", ECONOMIC_TO,
                "--out", str(cost_path),
            ],
            ATTEMPT_ROOT / "tool_logs/cost.stdout",
            ATTEMPT_ROOT / "tool_logs/cost.stderr",
            {0},
        )
        cost_raw = cost_path.read_bytes()
        cost = strict_json(cost_raw, "verified cost artifact")
        if not isinstance(cost, dict):
            raise RuntimeError("verified cost artifact root mismatch")
        validate_cost(cost, sealed_run / "report.html")

        summaries: list[dict[str, Any]] = []
        return_codes: list[int] = []
        for suffix in ("a", "b"):
            out_dir = ATTEMPT_ROOT / f"analysis/validation_{suffix}"
            out_dir.mkdir(parents=True, exist_ok=False)
            exclusive(out_dir / "nonrepaint_audit.json", audit_path.read_bytes())
            args = [
                sys.executable, str(UNIFIED),
                "--report", str(sealed_run / "report.html"),
                "--out", str(out_dir),
                "--stage", "challenger",
                "--holding-contract", "scalp",
                "--cost-artifact", str(cost_path),
                "--economic-from", ECONOMIC_FROM,
                "--economic-to", ECONOMIC_TO,
                "--min-completed-trades", str(BASELINE["min_completed_trades"]),
                "--min-direction-share", str(BASELINE["min_direction_share"]),
                "--max-year-trade-share", str(BASELINE["max_year_trade_share"]),
                "--require-positive-cost-expectancy",
                "--require-all-calendar-years-positive",
                "--min-pf", str(ACCEPTANCE["min_profit_factor"]),
                "--min-trades-per-week", str(ACCEPTANCE["min_trades_per_week"]),
                "--max-trades-per-week", str(ACCEPTANCE["max_trades_per_week"]),
                "--max-dd-pct", str(ACCEPTANCE["max_drawdown_pct"]),
                "--min-cost-pf-x1-5", str(ACCEPTANCE["min_cost_pf_x1_5"]),
                "--min-cost-pf-x2", str(ACCEPTANCE["min_cost_pf_x2"]),
                "--max-mc-p95-dd-pct", str(ACCEPTANCE["max_monte_carlo_p95_dd_pct"]),
                "--allow-research-cost-proxy",
            ]
            rc = run_tool(
                f"unified validation {suffix}", args,
                ATTEMPT_ROOT / f"tool_logs/unified_{suffix}.stdout",
                ATTEMPT_ROOT / f"tool_logs/unified_{suffix}.stderr",
                {0, 1},
            )
            return_codes.append(rc)
            summary_raw = (out_dir / "validation_summary.json").read_bytes()
            summary = strict_json(summary_raw, f"validation summary {suffix}")
            if not isinstance(summary, dict):
                raise RuntimeError(f"validation summary {suffix} root mismatch")
            validate_summary(summary, rc)
            summaries.append(summary)

        if return_codes[0] != return_codes[1] or canonical(validation_projection(summaries[0])) != canonical(validation_projection(summaries[1])):
            raise RuntimeError("unified deterministic replay mismatch")

        for tool, digest in ((AUDITOR, AUDITOR_SHA), (COST_BUILDER, COST_BUILDER_SHA), (UNIFIED, UNIFIED_SHA), (QUANT, QUANT_SHA)):
            if sha256_file(tool) != digest:
                raise RuntimeError(f"reviewed tool drifted during comparator: {tool.name}")
        if sha256_file(derived_manifest) != derived_sha or sha256_file(audit_path) != sha256_bytes(audit_path.read_bytes()):
            raise RuntimeError("derived manifest or audit drifted")
        for label, meta in evidence.items():
            if sha256_file(Path(str(meta["captured_path"]))) != meta["sha256"]:
                raise RuntimeError(f"captured evidence drifted: {label}")

        projection = validation_projection(summaries[0])
        classification = classify_summary(summaries[0])
        verdict = str(classification["verdict"])
        result = {
            "schema_version": "stbs027_sealed_existing_run_result.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "target_hypothesis_id": TARGET_ID,
            "target_run_id": RUN_ID,
            "verdict": verdict,
            "baseline_falsification_verdict": summaries[0]["baseline_falsification_verdict"],
            "baseline_non_passing_gates": summaries[0]["baseline_falsification_non_passing_gates"],
            "research_cost_proxy": True,
            "promotion_eligible": False,
            "economic_valid": classification["economic_valid"],
            "economic_verdict_created": classification["economic_verdict_created"],
            "engineering_non_passing_gates": classification["engineering_non_passing_gates"],
            "economic_blocked_gates": classification["economic_blocked_gates"],
            "economic_failed_gates": classification["economic_failed_gates"],
            "cost_scenarios": cost["scenarios"],
            "validation_projection": projection,
            "nonrepaint_status": audit["status"],
            "deterministic_replay": True,
            "mt5_launched": False,
            "compile_executed": False,
            "source_market_data_opened": False,
            "new_orders_or_fills_created": 0,
            "inherited_completed_trades_read": 464,
            "optimization_executed": False,
            "research_validation_opened": False,
            "holdout_opened": False,
            "paper_authorized": False,
            "live_authorized": False,
        }
        result_path = ATTEMPT_ROOT / "comparison_result.json"
        exclusive(result_path, canonical(result))
        result_sha = sha256_file(result_path)
        receipt = {
            "schema_version": "stbs027_comparator_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "created_at_utc": now(),
            "authority_row_sha256": row_sha,
            "registry_sha256_at_claim": registry_sha,
            "attempt_started_path": str(start_path),
            "attempt_started_sha256": start_sha,
            "result_path": str(result_path),
            "result_sha256": result_sha,
            "derived_manifest_path": str(derived_manifest),
            "derived_manifest_sha256": derived_sha,
            "nonrepaint_audit_path": str(audit_path),
            "nonrepaint_audit_sha256": sha256_file(audit_path),
            "verified_cost_artifact_path": str(cost_path),
            "verified_cost_artifact_sha256": sha256_file(cost_path),
            "derived_cost_manifest_path": str(derived_cost_manifest),
            "derived_cost_manifest_sha256": derived_cost_sha,
            "validation_a_sha256": sha256_file(ATTEMPT_ROOT / "analysis/validation_a/validation_summary.json"),
            "validation_b_sha256": sha256_file(ATTEMPT_ROOT / "analysis/validation_b/validation_summary.json"),
            "evidence": evidence,
            "result": result,
            "mt5_launched": False,
            "compile_executed": False,
            "source_market_data_opened": False,
            "new_orders_or_fills_created": 0,
            "optimization_executed": False,
            "research_validation_opened": False,
            "holdout_opened": False,
            "promotion_authorized": False,
            "paper_authorized": False,
            "live_authorized": False,
            "same_id_retry_authorized": False,
        }
        receipt_path = ATTEMPT_ROOT / "comparison_receipt.json"
        exclusive(receipt_path, canonical(receipt))
        receipt_sha = sha256_file(receipt_path)
        terminal = {
            "schema_version": "stbs027_comparator_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "completed_at_utc": now(),
            "attempt_started_path": str(start_path),
            "attempt_started_sha256": start_sha,
            "receipt_path": str(receipt_path),
            "receipt_sha256": receipt_sha,
            "result_path": str(result_path),
            "result_sha256": result_sha,
            "verdict": verdict,
            "same_id_retry_authorized": False,
        }
        exclusive(ATTEMPT_ROOT / "attempt_terminal.json", canonical(terminal))
        return terminal
    except Exception as exc:
        artifacts = []
        for path in sorted(p for p in ATTEMPT_ROOT.rglob("*") if p.is_file() and p.name != "attempt_terminal.json"):
            artifacts.append({"path": str(path), "sha256": sha256_file(path), "length": path.stat().st_size})
        terminal = {
            "schema_version": "stbs027_comparator_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "FAILED",
            "completed_at_utc": now(),
            "attempt_started_path": str(start_path),
            "attempt_started_sha256": start_sha,
            **context,
            "error": str(exc),
            "attempt_artifacts": artifacts,
            "mt5_launched": False,
            "compile_executed": False,
            "source_market_data_opened": False,
            "new_orders_or_fills_created": 0,
            "economic_verdict_created": False,
            "same_id_retry_authorized": False,
        }
        exclusive(ATTEMPT_ROOT / "attempt_terminal.json", canonical(terminal))
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print("STBS027 comparator package loaded; --execute requires the sole frozen authority")
        return 0
    print(json.dumps(execute(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
