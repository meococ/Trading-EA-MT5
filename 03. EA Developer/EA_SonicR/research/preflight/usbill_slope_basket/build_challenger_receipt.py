#!/usr/bin/env python3
"""Build challenger receipt for EA_UsBillSlopeBasket Model 0 (matched to control)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(r"d:\Trading EA MT5")
EA = WORKSPACE / "03. EA Developer" / "EA_UsBillSlopeBasket" / "EA_UsBillSlopeBasket.mq5"
PREREG_MD = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260713_H_FX_USBILL_SLOPE_USD_BASKET_001_PREREG.md"
)
OUT_DIR = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "usbill_slope_basket"
    / "contracts"
)
STUBS = OUT_DIR / "receipt_stubs_HYP_SR_FX_USBILL_SLOPE_USD_BASKET_001_CHALLENGER"
RECEIPT = OUT_DIR / "20260714_HYP_SR_FX_USBILL_SLOPE_USD_BASKET_001_CHALLENGER_RECEIPT.json"

CONTROL_RUN = WORKSPACE / "02. AlphaFactory" / "runs" / "EA_UsBillSlopeBasket" / "20260714_013628"
CONTROL_MANIFEST = CONTROL_RUN / "run_manifest.json"
CONTROL_REPORT = CONTROL_RUN / "report.html"

HYP = "HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001"
EA_NAME = "EA_UsBillSlopeBasket"
SYMBOL = "EURUSD"
PERIOD = "D1"
FROM = "2019.01.01"
TO = "2025.12.31"
OVERRIDES = "InpMode=1"  # candidate


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def write_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    path.write_text(raw, encoding="utf-8", newline="\n")
    return sha256_file(path)


def get_nogit_snapshot() -> tuple[str, str]:
    agents = WORKSPACE / "AGENTS.md"
    goal = WORKSPACE / "01. GOAL" / "GOAL.md"
    paths = [agents, goal, EA]
    records = []
    root = str(WORKSPACE).rstrip("\\/")
    for p in paths:
        full = str(p.resolve())
        if full.lower().startswith(root.lower()):
            rel = full[len(root) :].lstrip("\\/").replace("\\", "/")
        else:
            rel = full.replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(p)}")
    payload = "\n".join(records)
    prov = sha256_text(payload)
    commit = f"NOGIT-{prov}"
    status_lines = ["nogit=true", "dirty=true", f"provenance_sha256={prov}"]
    status_sha = sha256_text("\n".join(status_lines))
    return commit, status_sha


def main() -> int:
    STUBS.mkdir(parents=True, exist_ok=True)
    if not CONTROL_MANIFEST.is_file() or not CONTROL_REPORT.is_file():
        raise SystemExit("control artifacts missing")

    task = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": HYP,
        "ea_name": EA_NAME,
        "symbol": SYMBOL,
        "period": PERIOD,
        "from": FROM,
        "to": TO,
        "model": 0,
        "run_role": "challenger",
        "overrides": OVERRIDES,
        "matched_control_run_id": "20260714_013628",
        "note": (
            "Model 0 CHALLENGER for US bill-slope USD basket. InpMode=1 = bill z sign. "
            "Matched control 20260714_013628 (InpMode=0). Cost UNVERIFIED_TESTER_DEFAULT."
        ),
    }
    task_path = STUBS / "task_packet.json"
    task_sha = write_json(task_path, task)

    prereg_stub = {
        "schema_version": "sonic_prereg.v1",
        "hypothesis_id": HYP,
        "status": "FROZEN",
        "prereg_md": str(PREREG_MD),
        "prereg_md_sha256": sha256_file(PREREG_MD),
    }
    prereg_path = STUBS / "prereg.json"
    prereg_sha = write_json(prereg_path, prereg_stub)

    cost = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "hypothesis_id": HYP,
        "status": "UNVERIFIED_TESTER_DEFAULT",
        "broker_target": "FivePercentOnline-Real",
        "observed_login_server": "MetaQuotes-Demo",
        "grade": "RESEARCH_PROXY_TESTER_SPREAD_ONLY",
        "note": "Not QFSI/Real. Missing cost != zero. Not confirmed/GOAL.",
    }
    cost_path = STUBS / "cost_source_manifest.json"
    cost_sha = write_json(cost_path, cost)

    include_path = STUBS / "include_note.txt"
    include_path.write_text(
        "EA_UsBillSlopeBasket is single-file; Trade.mqh is MT5 standard library. "
        "Challenger include_* closure stub.\n",
        encoding="utf-8",
        newline="\n",
    )
    include_sha = sha256_file(include_path)
    include_closure = sha256_text(
        f"{str(include_path.resolve()).lower()}\t{include_sha}"
    )

    control_manifest_sha = sha256_file(CONTROL_MANIFEST)
    control_report_sha = sha256_file(CONTROL_REPORT)
    source_sha = sha256_file(EA)
    git_commit, git_status_sha = get_nogit_snapshot()

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": task_sha,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": "challenger",
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": OVERRIDES,
            "telemetry_tier": "off",
            "deposit": 10000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {
                "digits": 5,
                "point": 0.00001,
                "pip_size": 0.0001,
            },
            "include_closure_sha256": include_closure,
        },
        "evidence": [
            {
                "label": "task_packet",
                "kind": "file",
                "path": str(task_path.resolve()),
                "sha256": task_sha,
            },
            {
                "label": "source",
                "kind": "file",
                "path": str(EA.resolve()),
                "sha256": source_sha,
            },
            {
                "label": "prereg",
                "kind": "file",
                "path": str(prereg_path.resolve()),
                "sha256": prereg_sha,
            },
            {
                "label": "cost_source_manifest",
                "kind": "file",
                "path": str(cost_path.resolve()),
                "sha256": cost_sha,
            },
            {
                "label": "matched_control_manifest",
                "kind": "file",
                "path": str(CONTROL_MANIFEST.resolve()),
                "sha256": control_manifest_sha,
            },
            {
                "label": "matched_control_report",
                "kind": "file",
                "path": str(CONTROL_REPORT.resolve()),
                "sha256": control_report_sha,
            },
            {
                "label": "include_0001",
                "kind": "file",
                "path": str(include_path.resolve()),
                "sha256": include_sha,
            },
        ],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Model 0 challenger matched to control 20260714_013628.",
    }
    receipt_sha = write_json(RECEIPT, receipt)
    (OUT_DIR / "20260714_HYP_SR_FX_USBILL_SLOPE_USD_BASKET_001_CHALLENGER_RECEIPT.sha256.txt").write_text(
        receipt_sha + "\n", encoding="ascii"
    )
    print(json.dumps({"receipt": str(RECEIPT), "sha256": receipt_sha, "git_commit": git_commit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
