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
PREREG = PACKAGE / "research" / "HYP-AIRQMB-MULTI9-M5-001_FROZEN_PREREG.md"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
MANIFEST = PACKAGE / "research" / "baseline_receipts_manifest.json"
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
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True
    )
    return result.stdout.decode("utf-8").splitlines()


def latest_registry_rows() -> tuple[dict[str, tuple[str, dict]], str]:
    rows: dict[str, tuple[str, dict]] = {}
    raw_lines = REGISTRY.read_text(encoding="utf-8-sig").splitlines()
    for raw in raw_lines:
        if not raw.strip():
            continue
        row = json.loads(raw)
        rows[row["hypothesis_id"]] = (raw, row)
    return rows, sha256_file(REGISTRY)


def effective_overrides(symbol: str, magic: int) -> str:
    values = {
        "InpEnableTelemetry": "true",
        "InpExpectedSymbol": symbol,
        "InpHypothesisId": f"HYP-AIRQMB-{symbol}-M5-BASE-001",
        "InpMagic": str(magic),
        "InpResearchAutoMode": "true",
        "InpVariantTag": "BASELINE_FROZEN",
    }
    return ";".join(f"{key}={values[key]}" for key in sorted(values))


def evidence(label: str, path: Path) -> dict:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def main() -> None:
    for required in (SOURCE, PREREG, EA_CONTRACT, REGISTRY):
        if not required.is_file():
            raise SystemExit(f"missing receipt input: {required}")
    if sha256_file(SOURCE) != "A0622C7BCB22F1DBAABD707B1159679283D6B2C1AD0CFE642C5301E4573B1A81":
        raise SystemExit("source changed after preregistration")
    rows, registry_hash = latest_registry_rows()

    prepared: list[dict] = []
    for symbol, magic, geometry in CELLS:
        hypothesis_id = f"HYP-AIRQMB-{symbol}-M5-BASE-001"
        if hypothesis_id not in rows:
            raise SystemExit(f"registry row missing: {hypothesis_id}")
        raw_row, row = rows[hypothesis_id]
        if row.get("verdict") != "PREREGISTERED_BASELINE_NOT_RUN":
            raise SystemExit(f"baseline is not launchable: {hypothesis_id}")
        preflight = PACKAGE / "research" / "preflight" / hypothesis_id
        preflight.mkdir(parents=True, exist_ok=True)
        cost_manifest = preflight / "cost_source_manifest.json"
        task_packet = preflight / "task_packet.control.json"
        cost_payload = {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "evidence_tier": "RESEARCH_PROXY",
            "provenance_status": "BASELINE_CURRENT_SPREAD_ONLY",
            "audit_status": "COST_STRESS_BLOCKED_PENDING_BASELINE_SURVIVAL",
            "verdict": "RESEARCH_BASELINE_ONLY",
            "promotion_eligible": False,
            "broker": "Five Percent Online Ltd",
            "server": "FivePercentOnline-Real",
            "account_currency": "USD",
            "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
            "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
            "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
            "data_fingerprint": sha256_bytes(f"{symbol}|M5|2023.01.02|2024.12.31|MODEL0|PRE-RUN".encode()),
            "symbol": symbol,
            "from": "2023.01.02",
            "to": "2024.12.31",
            "symbol_geometry": geometry,
            "blocker": (
                "Current-spread Model-0 baseline only. Verified independent historical "
                "spread, commission and slippage evidence must be acquired for a survivor "
                "before economic-valid or promotion claims."
            ),
        }
        cost_manifest.write_text(json.dumps(cost_payload, indent=2) + "\n", encoding="utf-8")
        packet_payload = {
            "schema_version": "alphafactory_research_task_packet.v1",
            "hypothesis_id": hypothesis_id,
            "run_role": "control",
            "ea_name": "EA_AIRQMB_RegimeFusion",
            "symbol": symbol,
            "period": "M5",
            "from": "2023.01.02",
            "to": "2024.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": effective_overrides(symbol, magic),
            "telemetry_tier": "trade-only",
            "telemetry_profile": "lifecycle-v3",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "source_sha256": sha256_file(SOURCE),
            "prereg_sha256": sha256_file(PREREG),
            "registry_sha256": registry_hash,
            "registry_row_sha256": sha256_bytes(raw_row.encode("utf-8")),
            "ea_contract_sha256": sha256_file(EA_CONTRACT),
            "cost_source_manifest_sha256": sha256_file(cost_manifest),
            "symbol_geometry": geometry,
            "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
            "acceptance_contract": row["acceptance_contract"],
            "promotion_eligible": False,
        }
        task_packet.write_text(json.dumps(packet_payload, indent=2) + "\n", encoding="utf-8")
        prepared.append(
            {
                "symbol": symbol,
                "magic": magic,
                "geometry": geometry,
                "hypothesis_id": hypothesis_id,
                "raw_row": raw_row,
                "task_packet": task_packet,
                "cost_manifest": cost_manifest,
                "overrides": effective_overrides(symbol, magic),
            }
        )

    MANIFEST.write_text("{}\n", encoding="utf-8")
    commit = git_lines("rev-parse", "HEAD")[0].strip()
    status = git_lines("status", "--short", "--untracked-files=all")
    status_hash = sha256_bytes("\n".join(status).encode("utf-8"))
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt_records: list[dict] = []

    for item in prepared:
        packet = json.loads(item["task_packet"].read_text(encoding="utf-8"))
        packet["git_commit"] = commit
        packet["git_status"] = status
        packet["git_status_sha256"] = status_hash
        item["task_packet"].write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        task_hash = sha256_file(item["task_packet"])
        symbol = item["symbol"]
        hypothesis_id = item["hypothesis_id"]
        receipt_path = RUNTIME / f"ea_execution_receipt_airqmb_{symbol.lower()}_baseline.json"
        receipt = {
            "schema_version": "alphafactory_execution_receipt.v1",
            "hypothesis_id": hypothesis_id,
            "registry_row_sha256": sha256_bytes(item["raw_row"].encode("utf-8")),
            "task_packet_sha256": task_hash,
            "git_commit": commit,
            "git_status_sha256": status_hash,
            "binding": {
                "hypothesis_id": hypothesis_id,
                "run_role": "control",
                "ea_name": "EA_AIRQMB_RegimeFusion",
                "symbol": symbol,
                "period": "M5",
                "from": "2023.01.02",
                "to": "2024.12.31",
                "model": 0,
                "execution_mode": 0,
                "fixed_delay_ms": 0,
                "overrides": item["overrides"],
                "telemetry_tier": "trade-only",
                "telemetry_profile": "lifecycle-v3",
                "deposit": 100000,
                "leverage": 100,
                "spread": "current",
                "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
                "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
                "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
                "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
                "data_fingerprint": json.loads(item["cost_manifest"].read_text())["data_fingerprint"],
                "symbol_geometry": item["geometry"],
                "include_closure_sha256": EMPTY_SHA256,
            },
            "evidence": [
                evidence("task_packet", item["task_packet"]),
                evidence("candidate_registry", REGISTRY),
                evidence("source", SOURCE),
                evidence("ea_capability_contract", EA_CONTRACT),
                evidence("prereg", PREREG),
                evidence("cost_source_manifest", item["cost_manifest"]),
            ],
            "generated_at_utc": generated_at,
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipt_records.append(
            {
                "symbol": symbol,
                "hypothesis_id": hypothesis_id,
                "overrides": item["overrides"],
                "receipt_path": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
                "receipt_sha256": sha256_file(receipt_path),
                "task_packet_path": str(item["task_packet"].relative_to(ROOT)).replace("\\", "/"),
                "task_packet_sha256": task_hash,
            }
        )

    MANIFEST.write_text(
        json.dumps(
            {
                "schema_version": "airqmb_baseline_receipts.v1",
                "git_commit": commit,
                "git_status_sha256": status_hash,
                "generated_at_utc": generated_at,
                "cells": receipt_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"prepared": len(receipt_records), "manifest": str(MANIFEST)}, indent=2))


if __name__ == "__main__":
    main()
