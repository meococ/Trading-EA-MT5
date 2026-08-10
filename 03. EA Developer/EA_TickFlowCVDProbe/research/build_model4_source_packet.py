#!/usr/bin/env python3
"""Build the hash-bound zero-trade Model-4 packet for HYP-TFCVD-XAUUSD-M5-001."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-TFCVD-XAUUSD-M5-001"
EA_NAME = "EA_TickFlowCVDProbe"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
OVERRIDES = (
    "InpCollectionOnly=true;InpExpectedPeriodMinutes=5;InpExpectedSymbol=XAUUSD;"
    "InpHypothesisId=HYP-TFCVD-XAUUSD-M5-001"
)
FROM = "2018.01.01"
TO = "2022.12.31"
ASOF = "2026-08-08T18:18:00Z"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def repo_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def git_output(root: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8").splitlines()


def latest_registry_row(registry: Path) -> tuple[str, dict[str, Any]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for raw in registry.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no {HYPOTHESIS_ID} row")
    raw, row = matches[-1]
    if row.get("state") != "screened" or row.get("model") != 4:
        raise ValueError("latest registry row is not the screened Model-4 authority")
    validation = row.get("validation", {})
    if (
        validation.get("authority") != AUTHORITY
        or validation.get("economics_authorized") is not False
        or validation.get("model4_data_acquisition_authorized") is not True
    ):
        raise ValueError("registry does not carry the exact zero-trade Model-4 authority")
    return raw, row


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    package = root / "03. EA Developer" / EA_NAME
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / f"{HYPOTHESIS_ID}_FROZEN_PREREG.md"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    cost_manifest = package / "research" / "COLLECTION_ONLY_COST_SOURCE_MANIFEST.json"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    output_dir = package / "research" / "preflight" / HYPOTHESIS_ID
    packet_path = output_dir / "task_packet.control.json"
    receipt_path = output_dir / "contract_receipt.control.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    required = (source, prereg, ea_contract, cost_manifest, registry)
    for path in required:
        if not path.is_file():
            raise ValueError(f"required input is missing: {path}")
    raw_row, row = latest_registry_row(registry)
    if row["source_hash"] != sha256_file(source):
        raise ValueError("registry source binding changed")
    if row["prereg_sha256"] != sha256_file(prereg):
        raise ValueError("registry prereg binding changed")

    data_quality = {
        "history_quality": {"operator": "gt", "value": 97.0},
        "coverage_mode": "fixed_window",
        "availability_asof_utc": ASOF,
        "requested_from": FROM,
        "requested_to": TO,
        "require_tester_journal_bounds": True,
    }
    packet: dict[str, Any] = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "source_path": repo_path(source, root),
        "source_sha256": sha256_file(source),
        "registry_path": repo_path(registry, root),
        "registry_sha256": sha256_file(registry),
        "registry_row_sha256": sha256_bytes(raw_row.encode("utf-8")),
        "prereg_path": repo_path(prereg, root),
        "prereg_sha256": sha256_file(prereg),
        "ea_contract_path": repo_path(ea_contract, root),
        "ea_contract_sha256": sha256_file(ea_contract),
        "telemetry_profile": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": "XAUUSD",
        "period": "M5",
        "from": FROM,
        "to": TO,
        "data_quality_contract": data_quality,
        "model": 4,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "validation_stage": "source_feasibility",
        "holding_contract": "non_trading_collection",
        "data_acceptance_contract": row["data_acceptance_contract"],
        "include_closure": [],
        "include_closure_sha256": sha256_bytes(b""),
        "indicator_dependencies": [],
        "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
        "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
        "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
        "data_fingerprint": "0A21DA8833CBA7EAF08D0962E2203F5FD33ABF4E780C37F63DBC7850F35E76B5",
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "required_sidecars": [],
        "required_manifest_hashes": [
            "source_sha256",
            "config_sha256",
            "report_sha256",
            "ex5_sha256",
            "includes_sha256",
        ],
        "cost_source_manifest_path": repo_path(cost_manifest, root),
        "cost_source_manifest_sha256": sha256_file(cost_manifest),
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }

    # Pre-create both paths before binding git status. Rewriting an already
    # untracked path does not alter `git status --short --untracked-files=all`.
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    receipt_path.touch(exist_ok=True)
    commit = git_output(root, "rev-parse", "HEAD")[0].strip()
    status = git_output(root, "status", "--short", "--untracked-files=all")
    status_sha = sha256_bytes("\n".join(status).encode("utf-8"))
    packet["git_commit"] = commit
    packet["git_status"] = status
    packet["git_status_sha256"] = status_sha
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    evidence = [
        file_evidence("task_packet", packet_path),
        file_evidence("candidate_registry", registry),
        file_evidence("source", source),
        file_evidence("prereg", prereg),
        file_evidence("cost_source_manifest", cost_manifest),
    ]
    binding = {
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "M5",
        "from": FROM,
        "to": TO,
        "model": 4,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "symbol_geometry": packet["symbol_geometry"],
        "include_closure_sha256": packet["include_closure_sha256"],
        "indicator_dependencies": [],
        "data_quality_contract": data_quality,
    }
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": binding,
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    if git_output(root, "status", "--short", "--untracked-files=all") != status:
        raise ValueError("git status changed while packet/receipt were being bound")
    print(
        json.dumps(
            {
                "task_packet": str(packet_path),
                "task_packet_sha256": sha256_file(packet_path),
                "contract_receipt": str(receipt_path),
                "contract_receipt_sha256": sha256_file(receipt_path),
                "git_commit": commit,
                "git_status_sha256": status_sha,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
