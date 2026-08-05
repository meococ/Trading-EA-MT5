from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_AIRQMB_RegimeFusion"
RUNTIME = ROOT / "02. AlphaFactory" / "runtime"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / "EA_AIRQMB_RegimeFusion.mq5"
PREREG = PACKAGE / "research" / "HYP-AIRQMB-MULTI9-M5-SCREEN-006_FROZEN_PREREG.md"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
MANIFEST = PACKAGE / "research" / "screen006_receipts_manifest.json"
SOURCE_SHA256 = "16A6284D85B354E9F774AFD36F2C194609AC1E339A3891EB1E72B0807E3DBB8C"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()

CELLS = [
    ("EURUSD", 5686101, {"digits": 5, "point": 0.00001, "pip_size": 0.0001}),
    ("USDJPY", 5686102, {"digits": 3, "point": 0.001, "pip_size": 0.01}),
    ("GBPUSD", 5686103, {"digits": 5, "point": 0.00001, "pip_size": 0.0001}),
    ("USDCHF", 5686104, {"digits": 5, "point": 0.00001, "pip_size": 0.0001}),
    ("USDCAD", 5686105, {"digits": 5, "point": 0.00001, "pip_size": 0.0001}),
    ("AUDUSD", 5686106, {"digits": 5, "point": 0.00001, "pip_size": 0.0001}),
    ("NZDUSD", 5686107, {"digits": 5, "point": 0.00001, "pip_size": 0.0001}),
    ("XAUUSD", 5686108, {"digits": 2, "point": 0.01, "pip_size": 0.01}),
    ("BTCUSD", 5686109, {"digits": 2, "point": 0.01, "pip_size": 0.01}),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_lines(*args: str) -> list[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True
    ).stdout.decode("utf-8").splitlines()


def effective_overrides(symbol: str, magic: int) -> str:
    values = {
        "InpEnableTelemetry": "true",
        "InpExpectedSymbol": symbol,
        "InpHypothesisId": f"HYP-AIRQMB-{symbol}-M5-SCREEN-006",
        "InpMagic": str(magic),
        "InpResearchAutoMode": "true",
        "InpVariantTag": "SCREEN006_ORDERCHECK_MODEL4",
    }
    return ";".join(f"{key}={values[key]}" for key in sorted(values))


def item(label: str, path: Path) -> dict:
    return {"label": label, "kind": "file", "path": str(path.resolve()), "sha256": sha256_file(path)}


def main() -> None:
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise SystemExit("SCREEN-006 source changed")
    raw_lines = [line for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    latest: dict[str, tuple[str, dict]] = {}
    for line in raw_lines:
        row = json.loads(line)
        latest[row["hypothesis_id"]] = (line, row)
    registry_hash = sha256_file(REGISTRY)
    prepared: list[dict] = []

    for symbol, magic, geometry in CELLS:
        hypothesis_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-006"
        raw_row, row = latest[hypothesis_id]
        if row.get("verdict") != "PREREGISTERED_ORDERCHECK_MODEL4_SCREEN_NOT_RUN":
            raise SystemExit(f"screen not launchable: {hypothesis_id}")
        folder = PACKAGE / "research" / "preflight" / hypothesis_id
        folder.mkdir(parents=True, exist_ok=True)
        cost_path = folder / "cost_source_manifest.json"
        task_path = folder / "task_packet.control.json"
        cost = {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "evidence_tier": "RESEARCH_PROXY",
            "provenance_status": "ORDERCHECK_MODEL4_SCREEN_CURRENT_SPREAD_ONLY",
            "audit_status": "COST_STRESS_NOT_AUTHORIZED",
            "promotion_eligible": False,
            "symbol": symbol,
            "symbol_geometry": geometry,
            "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
            "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
            "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
            "data_fingerprint": sha256_bytes(f"{symbol}|M5|2023.01.02|2024.12.31|MODEL4|PRE-RUN".encode()),
            "blocker": "Model-4 screen cannot authorize cost or economic validity.",
        }
        cost_path.write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
        task = {
            "schema_version": "alphafactory_research_task_packet.v1",
            "hypothesis_id": hypothesis_id,
            "run_role": "control",
            "ea_name": "EA_AIRQMB_RegimeFusion",
            "symbol": symbol,
            "period": "M5",
            "from": "2023.01.02",
            "to": "2024.12.31",
            "model": 4,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": effective_overrides(symbol, magic),
            "telemetry_tier": "trade-only",
            "telemetry_profile": "lifecycle-v3",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "source_sha256": SOURCE_SHA256,
            "prereg_sha256": sha256_file(PREREG),
            "registry_sha256": registry_hash,
            "registry_row_sha256": sha256_bytes(raw_row.encode()),
            "ea_contract_sha256": sha256_file(EA_CONTRACT),
            "cost_source_manifest_sha256": sha256_file(cost_path),
            "symbol_geometry": geometry,
            "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
            "screen_contract": {
                "min_profit_factor": 1.10,
                "min_trades": 100,
                "min_trades_per_week": 1.5,
                "max_trades_per_week": 6.0,
                "max_drawdown_pct": 8.0,
            },
            "economic_claims_authorized": False,
            "promotion_eligible": False,
        }
        task_path.write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        prepared.append({
            "symbol": symbol, "magic": magic, "geometry": geometry,
            "hypothesis_id": hypothesis_id, "raw_row": raw_row,
            "task": task_path, "cost": cost_path,
            "overrides": effective_overrides(symbol, magic),
        })

    MANIFEST.write_text("{}\n", encoding="utf-8")
    commit = git_lines("rev-parse", "HEAD")[0].strip()
    status = git_lines("status", "--short", "--untracked-files=all")
    status_sha = sha256_bytes("\n".join(status).encode())
    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    cells: list[dict] = []

    for prepared_cell in prepared:
        task = json.loads(prepared_cell["task"].read_text())
        task.update({"git_commit": commit, "git_status": status, "git_status_sha256": status_sha})
        prepared_cell["task"].write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        symbol = prepared_cell["symbol"]
        hypothesis_id = prepared_cell["hypothesis_id"]
        cost = json.loads(prepared_cell["cost"].read_text())
        receipt_path = RUNTIME / f"ea_execution_receipt_airqmb_{symbol.lower()}_screen006.json"
        receipt = {
            "schema_version": "alphafactory_execution_receipt.v1",
            "hypothesis_id": hypothesis_id,
            "registry_row_sha256": sha256_bytes(prepared_cell["raw_row"].encode()),
            "task_packet_sha256": sha256_file(prepared_cell["task"]),
            "git_commit": commit,
            "git_status_sha256": status_sha,
            "binding": {
                "hypothesis_id": hypothesis_id, "run_role": "control",
                "ea_name": "EA_AIRQMB_RegimeFusion", "symbol": symbol, "period": "M5",
                "from": "2023.01.02", "to": "2024.12.31", "model": 4,
                "execution_mode": 0, "fixed_delay_ms": 0,
                "overrides": prepared_cell["overrides"], "telemetry_tier": "trade-only",
                "telemetry_profile": "lifecycle-v3", "deposit": 100000, "leverage": 100,
                "spread": "current", "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
                "broker_fingerprint": cost["broker_fingerprint"],
                "server_fingerprint": cost["server_fingerprint"],
                "account_fingerprint": cost["account_fingerprint"],
                "data_fingerprint": cost["data_fingerprint"],
                "symbol_geometry": prepared_cell["geometry"],
                "include_closure_sha256": EMPTY_SHA256,
            },
            "evidence": [
                item("task_packet", prepared_cell["task"]), item("candidate_registry", REGISTRY),
                item("source", SOURCE), item("ea_capability_contract", EA_CONTRACT),
                item("prereg", PREREG), item("cost_source_manifest", prepared_cell["cost"]),
            ],
            "generated_at_utc": generated,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        cells.append({
            "symbol": symbol, "hypothesis_id": hypothesis_id,
            "overrides": prepared_cell["overrides"],
            "receipt_path": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
            "receipt_sha256": sha256_file(receipt_path),
        })
    MANIFEST.write_text(json.dumps({
        "schema_version": "airqmb_screen006_receipts.v1", "git_commit": commit,
        "git_status_sha256": status_sha, "generated_at_utc": generated, "cells": cells,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"prepared": len(cells), "manifest": str(MANIFEST)}, indent=2))


if __name__ == "__main__":
    main()
