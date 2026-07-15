#!/usr/bin/env python3
"""Build HYP-SB-WEEKEND-FLAT-001 ContractReceipt matching alpha.ps1 NOGIT provenance."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer" / "EA_SilverBullet" / "EA_SilverBullet_v2.mq5"
AGENTS = ROOT / "AGENTS.md"
GOAL = ROOT / "01. GOAL" / "GOAL.md"
PREREG_MD = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260713_H_SB_WEEKEND_FLAT_001_RESEARCH_FREEZE.md"
)
CONTRACTS = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "sb_weekend_flat"
)
STUBS = CONTRACTS / "receipt_stubs_HYP_SB_WEEKEND_FLAT_001"

HYP = "HYP-SB-WEEKEND-FLAT-001"
EA_NAME = "EA_SilverBullet"
FROM = "2021.01.01"
TO = "2025.12.31"
SYMBOL = "USDJPY"
PERIOD = "M15"
MODEL = 0
DEPOSIT = 100000
LEVERAGE = 100

CONTROL_OVERRIDES = "InpUseWeekendFlat=0"
# alpha.ps1 ConvertFrom-NormalizedOverrideMap sorts keys alphabetically
CHALLENGER_OVERRIDES = (
    "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseWeekendFlat=1"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def nogit_snapshot(active_source: Path) -> tuple[str, str]:
    """Match Get-NoGitProvenanceSnapshot -ActiveSource in current alpha.ps1."""
    paths = [AGENTS, GOAL, active_source]
    records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
    prov = sha256_text("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    return commit, sha256_text(status)


def build_receipt(
    *,
    run_role: str,
    overrides: str,
    receipt_name: str,
    matched_control_manifest: Path | None = None,
    matched_control_report: Path | None = None,
) -> tuple[Path, str]:
    if not EA.is_file():
        raise SystemExit(f"EA missing: {EA}")
    if not PREREG_MD.is_file():
        raise SystemExit(f"Prereg missing: {PREREG_MD}")

    CONTRACTS.mkdir(parents=True, exist_ok=True)
    STUBS.mkdir(parents=True, exist_ok=True)

    role_stub = STUBS / f"task_packet_{run_role}.json"
    role_stub.write_text(
        json.dumps(
            {
                "schema_version": "sonic_research_task_packet.v1",
                "hypothesis_id": HYP,
                "run_role": run_role,
                "ea_name": EA_NAME,
                "symbol": SYMBOL,
                "period": PERIOD,
                "from": FROM,
                "to": TO,
                "model": MODEL,
                "overrides": overrides,
                "mechanism": (
                    "Matched Model 0 for weekend-flat A1 on EA_SilverBullet_v2 "
                    f"({run_role})."
                ),
                "authority": (
                    "Owner MT-backtest autonomy 2026-07-14 + research freeze; "
                    "not promotion."
                ),
                "cost_note": (
                    "Research cost proxy only; Demo/tester not "
                    "FivePercentOnline-Real provenance"
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Keep shared stubs stable; rewrite prereg/cost/include if missing or stale role.
    prereg_stub = STUBS / "prereg.json"
    prereg_stub.write_text(
        json.dumps(
            {
                "schema_version": "sonic_prereg.v1",
                "hypothesis_id": HYP,
                "status": "RESEARCH_FROZEN_FOR_MODEL0",
                "prereg_md": str(PREREG_MD.resolve()),
                "prereg_md_sha256": sha256_file(PREREG_MD),
                "intervention": "A1 weekend-flat only via InpUseWeekendFlat",
                "control_overrides": CONTROL_OVERRIDES,
                "challenger_overrides": CHALLENGER_OVERRIDES,
                "symbol": SYMBOL,
                "period": PERIOD,
                "window": f"{FROM}-{TO}",
                "model": MODEL,
                "deposit": DEPOSIT,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cost_stub = STUBS / "cost_source_manifest.json"
    cost_stub.write_text(
        json.dumps(
            {
                "schema_version": "alphafactory_cost_source_manifest.v1",
                "hypothesis_id": HYP,
                "status": "UNVERIFIED_TESTER_DEFAULT",
                "spread_policy": "tester_current",
                "commission": "unknown_not_zero",
                "slippage": "unknown_not_zero",
                "note": (
                    "Missing/zero cost fields must NOT be treated as zero friction. "
                    "Screen PF is tester-reported only."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    include = STUBS / "include_note.txt"
    include.write_text(
        "EA_SilverBullet_v2.mq5 includes Trade.mqh (MT5 stdlib). "
        "Packet-bound include closure stub for receipt.\n",
        encoding="utf-8",
    )

    # Compatibility alias used by older control receipt evidence path.
    task_alias = STUBS / "task_packet.json"
    if run_role == "control":
        task_alias.write_text(role_stub.read_text(encoding="utf-8"), encoding="utf-8")
        task_path = task_alias
    else:
        task_path = role_stub

    h_task = sha256_file(task_path)
    h_prereg = sha256_file(prereg_stub)
    h_cost = sha256_file(cost_stub)
    h_include = sha256_file(include)
    h_source = sha256_file(EA)

    include_record = f"{str(include.resolve()).lower()}\t{h_include}"
    include_closure = sha256_text(include_record)
    git_commit, git_status_sha = nogit_snapshot(EA)

    evidence = [
        {
            "label": "task_packet",
            "kind": "file",
            "path": str(task_path.resolve()),
            "sha256": h_task,
        },
        {
            "label": "source",
            "kind": "file",
            "path": str(EA.resolve()),
            "sha256": h_source,
        },
        {
            "label": "prereg",
            "kind": "file",
            "path": str(prereg_stub.resolve()),
            "sha256": h_prereg,
        },
        {
            "label": "cost_source_manifest",
            "kind": "file",
            "path": str(cost_stub.resolve()),
            "sha256": h_cost,
        },
        {
            "label": "include_0001",
            "kind": "file",
            "path": str(include.resolve()),
            "sha256": h_include,
        },
    ]

    if run_role == "challenger":
        if matched_control_manifest is None or matched_control_report is None:
            raise SystemExit(
                "challenger requires --control-manifest and --control-report"
            )
        for label, path in (
            ("matched_control_manifest", matched_control_manifest),
            ("matched_control_report", matched_control_report),
        ):
            if not path.is_file():
                raise SystemExit(f"Missing {label}: {path}")
            evidence.append(
                {
                    "label": label,
                    "kind": "file",
                    "path": str(path.resolve()),
                    "sha256": sha256_file(path),
                }
            )

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": h_task,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": run_role,
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": MODEL,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "off",
            "deposit": DEPOSIT,
            "leverage": LEVERAGE,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {
                "digits": 3,
                "point": 0.001,
                "pip_size": 0.01,
            },
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            f"Model 0 {run_role} for HYP-SB-WEEKEND-FLAT-001. "
            "NOGIT = AGENTS.md + GOAL.md + EA_SilverBullet_v2.mq5 ActiveSource. "
            "Cost provenance unverified."
        ),
    }

    receipt_path = CONTRACTS / receipt_name
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    print(f"GIT_COMMIT={git_commit}")
    print(f"GIT_STATUS_SHA256={git_status_sha}")
    print(f"RECEIPT_PATH={receipt_path}")
    print(f"RECEIPT_SHA256={receipt_sha}")
    return receipt_path, receipt_sha


def main(argv: list[str]) -> int:
    role = "control"
    control_manifest = None
    control_report = None
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--role":
            role = args.pop(0)
        elif a == "--control-manifest":
            control_manifest = Path(args.pop(0))
        elif a == "--control-report":
            control_report = Path(args.pop(0))
        else:
            raise SystemExit(f"Unknown arg: {a}")

    if role == "control":
        build_receipt(
            run_role="control",
            overrides=CONTROL_OVERRIDES,
            receipt_name="20260714_HYP_SB_WEEKEND_FLAT_001_CONTROL_RECEIPT.json",
        )
    elif role == "challenger":
        build_receipt(
            run_role="challenger",
            overrides=CHALLENGER_OVERRIDES,
            receipt_name="20260714_HYP_SB_WEEKEND_FLAT_001_CHALLENGER_RECEIPT.json",
            matched_control_manifest=control_manifest,
            matched_control_report=control_report,
        )
    else:
        raise SystemExit("role must be control|challenger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
