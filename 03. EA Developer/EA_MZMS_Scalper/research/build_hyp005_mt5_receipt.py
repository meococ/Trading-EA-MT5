#!/usr/bin/env python3
"""Build hash-bound manual AlphaFactory receipts for MZMS HYP-005."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-005"
EA_NAME = "EA_MZMS_Scalper"
FROM_DATE = "2018.01.01"
TO_DATE = "2026.07.21"
COMMON_INPUTS = {
    "InpAdxPeriod": "14",
    "InpAtrPeriod": "14",
    "InpBreakEvenR": "1.00",
    "InpCooldownBars": "5",
    "InpDailyLossPct": "1.50",
    "InpEmaPeriod": "200",
    "InpEnableTelemetry": "true",
    "InpFlattenUtcHour": "18",
    "InpFlattenUtcMinute": "15",
    "InpMacdFast": "12",
    "InpMacdSignal": "9",
    "InpMacdSlow": "26",
    "InpMagic": "5600721",
    "InpMaxAccountDrawdownPct": "8.00",
    "InpMaxHoldBars": "15",
    "InpMaxSpreadPips": "0.80",
    "InpMaxTradesPerDay": "5",
    "InpMinAdx": "18.0",
    "InpMinHistDeltaAtr": "0.01",
    "InpNewsBlackoutMinutes": "15",
    "InpRequireNewsGuard": "false",
    "InpResearchAutoMode": "true",
    "InpRiskPercent": "0.01",
    "InpRsiLower": "42.0",
    "InpRsiPeriod": "14",
    "InpRsiUpper": "58.0",
    "InpServerUsesEuropeDst": "true",
    "InpServerUtcOffsetWinterHours": "2",
    "InpSessionEndUtcHour": "17",
    "InpSessionStartUtcHour": "8",
    "InpStopAtrMultiple": "1.50",
    "InpStopBufferPips": "0.50",
    "InpStopLookbackBars": "5",
    "InpTargetRR": "1.60",
    "InpUseBreakEven": "false",
}
REQUIRED_SIDECARS = ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"]
ACCEPTANCE = {
    "min_profit_factor": 1.35,
    "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0,
    "max_drawdown_pct": 6.0,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.0,
    "max_monte_carlo_p95_dd_pct": 6.0,
}
INCLUDES = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/Trade.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Object.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/OrderInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/HistoryOrderInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/PositionInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/DealInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/StdLibErr.mqh",
    "03. EA Developer/EA_MZMS_Scalper/NewsCalendar2019_2022.mqh",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def git_snapshot(root: Path) -> tuple[str, list[str], str]:
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    return commit, status, sha256_bytes("\n".join(status).encode("utf-8"))


def overrides_for(role: str) -> str:
    values = dict(COMMON_INPUTS)
    values["InpSignalMode"] = "0" if role == "control" else "1"
    return ";".join(f"{key}={values[key]}" for key in sorted(values))


def latest_registry_row(registry: Path) -> tuple[str, dict[str, Any]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for raw in registry.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no row for {HYPOTHESIS_ID}")
    raw, row = matches[-1]
    if row.get("state") != "screened" or row.get("model") != 0:
        raise ValueError("latest HYP-005 registry row is not screened Model 0")
    return raw, row


def build(role: str, control_run: Path | None) -> tuple[Path, str]:
    root = Path(__file__).resolve().parents[3]
    package = root / "03. EA Developer" / EA_NAME
    preflight = package / "research" / "preflight" / HYPOTHESIS_ID
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / f"{HYPOTHESIS_ID}_FROZEN_PREREG.md"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    cost_manifest = preflight / "cost_source_manifest.unverified.json"
    task_path = preflight / f"task_packet.{role}.json"
    receipt_path = preflight / f"contract_receipt.{role}.json"

    for name in (
        "task_packet.control.json",
        "task_packet.challenger.json",
        "contract_receipt.control.json",
        "contract_receipt.challenger.json",
    ):
        path = preflight / name
        if not path.exists():
            write_json(path, {})

    required = [source, prereg, registry, ea_contract]
    required.extend(root / Path(*item.split("/")) for item in INCLUDES)
    for path in required:
        if not path.is_file():
            raise ValueError(f"required evidence is missing: {path}")

    raw_registry_row, registry_row = latest_registry_row(registry)
    source_hash = sha256_file(source)
    prereg_hash = sha256_file(prereg)
    if registry_row.get("source_hash") != source_hash:
        raise ValueError("screened registry source hash does not match disk")
    if registry_row.get("prereg_sha256") != prereg_hash:
        raise ValueError("screened registry prereg hash does not match disk")

    cost = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "evidence_tier": "UNVERIFIED_DIAGNOSTIC",
        "provenance_status": "UNVERIFIED",
        "promotion_eligible": False,
        "broker": "Five Percent Online Ltd",
        "server": "FivePercentOnline-Real",
        "symbol": "EURUSD",
        "from": FROM_DATE,
        "to": TO_DATE,
        "spread_policy": "MT5 Model 0 current/historical tick spread",
        "commission": "tester-reported only; not accepted as live fill provenance",
        "slippage": "not independently verified",
        "verdict": "DIAGNOSTIC_ONLY_NOT_PROMOTION_ELIGIBLE",
    }
    write_json(cost_manifest, cost)

    overrides = overrides_for(role)
    task = {
        "schema_version": "alphafactory_diagnostic_task_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": role,
        "ea_name": EA_NAME,
        "source_path": source.resolve().relative_to(root.resolve()).as_posix(),
        "source_sha256": source_hash,
        "registry_path": registry.resolve().relative_to(root.resolve()).as_posix(),
        "registry_sha256": sha256_file(registry),
        "registry_row_sha256": sha256_bytes(raw_registry_row.encode("utf-8")),
        "prereg_path": prereg.resolve().relative_to(root.resolve()).as_posix(),
        "prereg_sha256": prereg_hash,
        "ea_contract_path": ea_contract.resolve().relative_to(root.resolve()).as_posix(),
        "ea_contract_sha256": sha256_file(ea_contract),
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
        "required_sidecars": REQUIRED_SIDECARS,
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "acceptance_contract": ACCEPTANCE,
        "cost_status": "UNVERIFIED_DIAGNOSTIC_ONLY",
        "news_guard": "DISABLED_UNIFORMLY_CALENDAR_COVERAGE_INCOMPLETE",
        "promotion_eligible": False,
    }
    write_json(task_path, task)

    commit, status, status_hash = git_snapshot(root)
    task["git_commit"] = commit
    task["git_status"] = status
    task["git_status_sha256"] = status_hash
    write_json(task_path, task)

    evidence = [
        file_evidence("task_packet", task_path),
        file_evidence("source", source),
        file_evidence("prereg", prereg),
        file_evidence("cost_source_manifest", cost_manifest),
    ]
    for index, relative in enumerate(INCLUDES, start=1):
        evidence.append(
            file_evidence(f"include_{index:04d}", root / Path(*relative.split("/")))
        )

    if role == "challenger":
        if control_run is None:
            raise ValueError("--control-run is required for challenger receipt")
        manifest = control_run / "run_manifest.json"
        report = control_run / "report.html"
        if not manifest.is_file() or not report.is_file():
            raise ValueError("matched control manifest/report is missing")
        evidence.extend(
            [
                file_evidence("matched_control_manifest", manifest),
                file_evidence("matched_control_report", report),
            ]
        )

    include_records = []
    for item in sorted(
        (item for item in evidence if item["label"].startswith("include_")),
        key=lambda item: str(Path(item["path"]).resolve()).lower(),
    ):
        include_records.append(
            f"{str(Path(item['path']).resolve()).lower()}\t{item['sha256'].upper()}"
        )
    include_closure_sha256 = sha256_bytes("\n".join(include_records).encode("utf-8"))

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "authority": "OWNER_DIRECTED_DIAGNOSTIC_NO_PROMOTION",
        "hypothesis_id": HYPOTHESIS_ID,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": commit,
        "git_status_sha256": status_hash,
        "binding": {
            "hypothesis_id": HYPOTHESIS_ID,
            "run_role": role,
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
            "include_closure_sha256": include_closure_sha256,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Owner-directed 2018-YTD MZMS diagnostic instrumentation replacement. News guard is disabled "
            "uniformly because the embedded calendar is incomplete. No promotion authority."
        ),
    }
    write_json(receipt_path, receipt)
    return receipt_path, sha256_file(receipt_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("control", "challenger"), required=True)
    parser.add_argument("--control-run", type=Path)
    args = parser.parse_args()
    receipt, digest = build(
        args.role,
        args.control_run.resolve() if args.control_run is not None else None,
    )
    print(json.dumps({"receipt": str(receipt), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
