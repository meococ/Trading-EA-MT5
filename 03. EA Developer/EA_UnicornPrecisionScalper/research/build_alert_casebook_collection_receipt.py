#!/usr/bin/env python3
"""Build a fail-closed AlphaFactory receipt for alert-only data acquisition."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
RESEARCH = SCRIPT.parent
PACKAGE = RESEARCH.parent
ROOT = SCRIPT.parents[3]
EVIDENCE = RESEARCH / "evidence"

EA = PACKAGE / "EA_UnicornPrecisionScalper.mq5"
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
CAPABILITY = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
PRESET = PACKAGE / "presets" / "ALERT_CASEBOOK_COLLECTION_V1.set"
CONTRACT = RESEARCH / "ALERT_FIRST_CASEBOOK_V1_CONTRACT.md"
PREREG = RESEARCH / "20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_PREREG.md"
STORAGE_BEFORE = EVIDENCE / "20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_STORAGE_BEFORE.json"

TASK = EVIDENCE / "20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_TASK.json"
COST = EVIDENCE / "20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_COST_NA.json"
RECEIPT = EVIDENCE / "20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_EXECUTION_RECEIPT.json"
RECEIPT_SHA = EVIDENCE / "20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_EXECUTION_RECEIPT.sha256.txt"

HYPOTHESIS_ID = "DATA-ACQ-UNICORN-CASEBOOK-V1-002"
REQUIRED_SIDECARS = [
    "XAUUSD_AlertCasebookMeta_*.csv",
    "XAUUSD_AlertCasebook_*.csv",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def git_snapshot() -> tuple[str, str]:
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    status_lines = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    return commit, sha256_text("\n".join(status_lines))


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for required in (EA, ALPHA, CAPABILITY, PRESET, CONTRACT, PREREG, STORAGE_BEFORE):
        if not required.is_file():
            raise SystemExit(f"required collection evidence missing: {required}")

    source_sha = sha256_file(EA)
    overrides = (
        "InpAlertCasebookMaxRows=200;"
        "InpAllowRetiredResearchExecution=false;"
        "InpEnableAlertCasebook=true;"
        "InpEnableTelemetry=false;"
        f"InpExpectedSourceSha256={source_sha};"
        "InpResearchAutoMode=false"
    )
    task = {
        "schema_version": "alphafactory_data_acquisition_task.v1",
        "authority": "DATA_ACQUISITION_ONLY_NO_TRADING_HYPOTHESIS",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": "EA_UnicornPrecisionScalper",
        "source_sha256": source_sha,
        "source_contract_id": "UPS_ALERT_FIRST_CASEBOOK_V1_3",
        "symbol": "XAUUSD",
        "period": "M5",
        "from": "2024.01.01",
        "to": "2025.12.25",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "run_role": "control",
        "telemetry_tier": "off",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "overrides": overrides,
        "required_sidecars": REQUIRED_SIDECARS,
        "performance_analysis_authorized": False,
        "trading_mutation_authorized": False,
        "max_casebook_rows": 200,
        "min_valid_rows": 100,
        "protected_storage_rule": "C_ROOTS_MUST_BE_IDENTICAL_BEFORE_AFTER",
    }
    write_json(TASK, task)
    write_json(
        COST,
        {
            "schema_version": "alphafactory_data_acquisition_cost_na.v1",
            "cost_provenance": "NOT_APPLICABLE_ZERO_TRADE_COLLECTION",
            "missing_cost_is_not_zero": True,
            "performance_claim_authorized": False,
            "note": "This sentinel cannot be reused for an economic backtest.",
        },
    )

    # Pre-create every output path before git status is frozen. The repository is
    # intentionally dirty; the receipt binds the exact porcelain path set.
    RECEIPT.write_text("{}\n", encoding="utf-8")
    RECEIPT_SHA.write_text("PENDING\n", encoding="utf-8")
    commit, status_sha = git_snapshot()

    evidence = [
        file_evidence("task_packet", TASK),
        file_evidence("source", EA),
        file_evidence("prereg", PREREG),
        file_evidence("cost_source_manifest", COST),
        file_evidence("include_0001", CAPABILITY),
        file_evidence("include_0002", CONTRACT),
        file_evidence("include_0003", PRESET),
        file_evidence("include_0004", STORAGE_BEFORE),
        file_evidence("include_0005", ALPHA),
    ]
    include_records = []
    for item in sorted(
        (entry for entry in evidence if entry["label"].startswith("include_")),
        key=lambda entry: str(Path(entry["path"]).resolve()).lower(),
    ):
        include_records.append(
            f"{str(Path(item['path']).resolve()).lower()}\t{item['sha256'].upper()}"
        )

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "hypothesis_id": HYPOTHESIS_ID,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": HYPOTHESIS_ID,
            "run_role": "control",
            "ea_name": "EA_UnicornPrecisionScalper",
            "symbol": "XAUUSD",
            "period": "M5",
            "from": "2024.01.01",
            "to": "2025.12.25",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "off",
            "deposit": 10000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": REQUIRED_SIDECARS,
            "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
            "include_closure_sha256": sha256_text("\n".join(include_records)),
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Supported legacy receipt schema is used only to exercise the real "
            "AlphaFactory tester path. Zero-trade collection is not promotion evidence."
        ),
    }
    write_json(RECEIPT, receipt)
    receipt_sha = sha256_file(RECEIPT)
    RECEIPT_SHA.write_text(receipt_sha + "\n", encoding="utf-8")
    print(f"TASK={TASK}")
    print(f"RECEIPT={RECEIPT}")
    print(f"RECEIPT_SHA256={receipt_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
