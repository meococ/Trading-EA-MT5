"""Build frozen AlphaFactory Model-0 PRIMARY/REVERSE packets and receipts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
EA_ROOT = ROOT / "03. EA Developer/EA_DOLUISeasonalResidual"
RESEARCH = EA_ROOT / "research"
PREFLIGHT = RESEARCH / "preflight/HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001"
HYPOTHESIS_ID = "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001"
OVERRIDE_COMMON = (
    "InpDeviationPoints=100;InpEnableAudit=true;InpExposurePercent=0.25;"
    "InpHypothesisId=HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001;"
    "InpMagic=8132601;InpMaxEntryDelaySec=300;InpMaxLots=1.0;"
    "InpResearchAutoMode=true;InpReverseComparator={reverse};"
    "InpSizingPips=40.0;InpVariantTag=DOLUI_RESIDUAL_H1_DELAY4H_V1"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def git_snapshot() -> tuple[str, list[str], str]:
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    result = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = result.stdout.splitlines()
    return commit, lines, sha256_text("\n".join(lines))


def task_packet(role: str) -> dict[str, object]:
    reverse = role == "REVERSE"
    required = [
        f"DOLUI001_RunMeta_{role}.json",
        f"EURUSD_DOLUI001_Trades_{role}.csv",
    ]
    return {
        "schema_version": "dolui_001_model0_task.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": f"DOLUI001-MODEL0-{role}-001",
        "one_attempt_only": True,
        "same_id_retry_authorized": False,
        "visual_mode": False,
        "indicator_dependencies": [],
        "command_contract": {
            "action": "backtest",
            "ea_name": "EA_DOLUISeasonalResidual",
            "symbol": "EURUSD",
            "period": "H1",
            "from": "2018.01.01",
            "to": "2023.01.01",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "timeout_sec": 3600,
            "run_role": "control",
            "telemetry_tier": "off",
            "telemetry_profile": "none",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "holding_contract": "fixed_4h_event_trade",
            "required_sidecars": required,
            "overrides": OVERRIDE_COMMON.format(reverse=str(reverse).lower()),
        },
        "acceptance": {
            "all_events_accounted": 260,
            "source_flat_exact": 2,
            "min_completed_trades": 250,
            "min_completed_per_year": 48,
            "min_positive_years_of_five": 3,
            "min_base_profit_factor": 1.30,
            "min_base_expectancy_strict": 0.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "min_cost_expectancy_x2": 0.0,
            "max_native_equity_drawdown_pct": 8.0,
            "reverse_pf_and_expectancy_both_inferior": True,
            "max_top_5pct_profit_contribution": 0.30,
            "validation_opened": False,
            "optimization_authorized": False,
            "paper_live_authorized": False,
        },
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    PREFLIGHT.mkdir(parents=True, exist_ok=True)
    roles = ("PRIMARY", "REVERSE")
    task_paths: dict[str, Path] = {}
    receipt_paths: dict[str, Path] = {}
    for role in roles:
        task_paths[role] = RESEARCH / f"{HYPOTHESIS_ID}_{role}_TASK.json"
        receipt_paths[role] = PREFLIGHT / f"contract_receipt.{role.lower()}.json"
        write_json(task_paths[role], task_packet(role))
        if not receipt_paths[role].exists():
            receipt_paths[role].write_text("{}\n", encoding="utf-8")

    shared = [
        ("source", EA_ROOT / "EA_DOLUISeasonalResidual.mq5"),
        ("static_ex5", EA_ROOT / "EA_DOLUISeasonalResidual.ex5"),
        ("static_compile_log", EA_ROOT / "EA_DOLUISeasonalResidual.log"),
        ("prereg", RESEARCH / f"{HYPOTHESIS_ID}_FROZEN_ECONOMIC_PREREG.md"),
        ("cost_source_manifest", RESEARCH / f"{HYPOTHESIS_ID}_COST_SOURCE_MANIFEST.json"),
        ("candidate_registry", ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"),
        ("ea_contract", EA_ROOT / "ALPHAFACTORY_EA_CONTRACT.json"),
        ("nonrepaint_manifest", EA_ROOT / f"{HYPOTHESIS_ID}_NONREPAINT_MANIFEST.json"),
        ("nonrepaint_audit", RESEARCH / f"{HYPOTHESIS_ID}_NONREPAINT_AUDIT.json"),
        ("source_manifest", ROOT / f"02. AlphaFactory/data/dol_ui/{HYPOTHESIS_ID}/manifest.json"),
        ("source_csv", ROOT / f"02. AlphaFactory/data/dol_ui/{HYPOTHESIS_ID}/dol_ui_seasonal_residual_2018_20260806.csv"),
        ("source_receipt", RESEARCH / f"evidence/{HYPOTHESIS_ID}/DOLUI001-SOURCE-002/source_feasibility_receipt.json"),
        ("train_table_manifest", RESEARCH / f"{HYPOTHESIS_ID}_TRAIN_TABLE_MANIFEST.json"),
        ("pre_model0_review", RESEARCH / f"{HYPOTHESIS_ID}_PRE_MODEL0_REVIEW.md"),
        ("frozen_analyzer", RESEARCH / "analyze_dolui_001.py"),
        ("alpha_ps1", ROOT / "02. AlphaFactory/alpha.ps1"),
    ]
    includes = [
        ("include_dolui_table", EA_ROOT / "resources/dolui_001_train_table.mqh"),
        ("include_trade", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/Trade.mqh"),
        ("include_object", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Object.mqh"),
        ("include_stdliberr", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/StdLibErr.mqh"),
        ("include_order_info", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/OrderInfo.mqh"),
        ("include_history_order_info", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/HistoryOrderInfo.mqh"),
        ("include_position_info", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/PositionInfo.mqh"),
        ("include_deal_info", ROOT / "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/DealInfo.mqh"),
    ]
    commit, status_lines, status_hash = git_snapshot()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output: dict[str, object] = {}
    for role in roles:
        reverse = role == "REVERSE"
        task_ev = evidence("task_packet", task_paths[role])
        items = [task_ev] + [evidence(label, path) for label, path in shared]
        items += [evidence(label, path) for label, path in includes]
        include_records = [
            f"{str(Path(item['path']).resolve()).lower()}\t{item['sha256'].upper()}"
            for item in sorted(
                (value for value in items if value["label"].startswith("include_")),
                key=lambda value: str(Path(value["path"]).resolve()).lower(),
            )
        ]
        required = [
            f"DOLUI001_RunMeta_{role}.json",
            f"EURUSD_DOLUI001_Trades_{role}.csv",
        ]
        receipt = {
            "schema_version": "alphafactory_execution_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "task_packet_sha256": task_ev["sha256"],
            "git_commit": commit,
            "git_status_sha256": status_hash,
            "binding": {
                "hypothesis_id": HYPOTHESIS_ID,
                "run_role": "control",
                "ea_name": "EA_DOLUISeasonalResidual",
                "symbol": "EURUSD",
                "period": "H1",
                "from": "2018.01.01",
                "to": "2023.01.01",
                "model": 0,
                "execution_mode": 0,
                "fixed_delay_ms": 0,
                "timeout_sec": 3600,
                "overrides": OVERRIDE_COMMON.format(reverse=str(reverse).lower()),
                "telemetry_tier": "off",
                "telemetry_profile": "none",
                "deposit": 100000,
                "leverage": 100,
                "spread": "current",
                "required_sidecars": required,
                "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
                "visual_mode": False,
                "indicator_dependencies": [],
                "include_closure_sha256": sha256_text("\n".join(include_records)),
                "data_quality_contract": {
                    "availability_asof_utc": generated,
                    "coverage_mode": "fixed_window",
                    "history_quality": {"operator": "gt", "value": 97},
                    "requested_from": "2018.01.01",
                    "requested_to": "2023.01.01",
                    "require_tester_journal_bounds": True,
                    "max_journal_delta_bytes": 4194304,
                },
            },
            "evidence": items,
            "generated_at_utc": generated,
            "note": f"Frozen TRAIN Model-0 {role}; validation and holdout remain sealed.",
        }
        write_json(receipt_paths[role], receipt)
        output[role.lower()] = {
            "task": str(task_paths[role]),
            "task_sha256": task_ev["sha256"],
            "receipt": str(receipt_paths[role]),
            "receipt_sha256": sha256_file(receipt_paths[role]),
        }
    print(json.dumps({"git_commit": commit, "git_status_sha256": status_hash, "status_count": len(status_lines), **output}, indent=2))


if __name__ == "__main__":
    main()
