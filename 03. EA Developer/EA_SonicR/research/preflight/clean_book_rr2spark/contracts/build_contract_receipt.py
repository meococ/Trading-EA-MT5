#!/usr/bin/env python3
"""Build ContractReceipt for HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001 Model 0 unlock."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
CONTRACTS = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "clean_book_rr2spark"
    / "contracts"
)
STUBS = CONTRACTS / "receipt_stubs_HYP_BOOK_CLEAN_APRIORI_RR2SPARK_001"
EA = ROOT / "03. EA Developer" / "EA_SBSparkBook" / "EA_SBSparkBook.mq5"
SB_MOD = ROOT / "03. EA Developer" / "EA_SBSparkBook" / "Modules" / "SB_A1_Module.mqh"
SPK_MOD = ROOT / "03. EA Developer" / "EA_SBSparkBook" / "Modules" / "SparkAsian_Module.mqh"
PREREG_MD = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260715_H_BOOK_CLEAN_APRIORI_RR2SPARK_001_MODEL0_PREREG.md"
)
RECEIPT = CONTRACTS / "20260715_HYP_BOOK_CLEAN_APRIORI_RR2SPARK_001_CONTRACT_RECEIPT.json"
SHA_TXT = CONTRACTS / "20260715_HYP_BOOK_CLEAN_APRIORI_RR2SPARK_001_CONTRACT_RECEIPT.sha256.txt"

HYP = "HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001"
EA_NAME = "EA_SBSparkBook"
FROM = "2021.01.01"
TO = "2025.12.31"
SYMBOL = "USDJPY"
PERIOD = "M15"
MODEL = 0
DEPOSIT = 100000
LEVERAGE = 100


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def git_snapshot() -> tuple[str, str]:
    """Match alpha.ps1 Get-GitSnapshot when root is a real work tree."""
    import subprocess

    def run(args: list[str]) -> str:
        p = subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode != 0:
            raise SystemExit(f"git failed ({args}): {p.stderr}")
        return p.stdout

    inside = run(["git", "rev-parse", "--is-inside-work-tree"]).strip()
    if inside != "true":
        # Fallback NO-GIT provenance (AGENTS.md doctrine path)
        paths = [
            ROOT / "AGENTS.md",
            ROOT / "01. GOAL" / "GOAL.md",
            EA,
        ]
        records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
        prov = sha256_text("\n".join(records))
        commit = f"NOGIT-{prov}"
        status = "\n".join(
            ["nogit=true", "dirty=true", f"provenance_sha256={prov}"]
        )
        return commit, sha256_text(status)

    commit = run(["git", "rev-parse", "HEAD"]).strip()
    status = run(["git", "status", "--short", "--untracked-files=all"])
    # PowerShell Join uses `n between lines; trailing empty from splitlines drop
    lines = status.splitlines()
    payload = "\n".join(lines)
    return commit, sha256_text(payload)


def main() -> int:
    for p in (EA, SB_MOD, SPK_MOD, PREREG_MD):
        if not p.is_file():
            raise SystemExit(f"Missing: {p}")

    CONTRACTS.mkdir(parents=True, exist_ok=True)
    STUBS.mkdir(parents=True, exist_ok=True)

    stubs = {
        "task_packet.json": {
            "schema_version": "sonic_research_task_packet.v1",
            "hypothesis_id": HYP,
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": MODEL,
            "run_role": "control",
            "deposit": DEPOSIT,
            "note": (
                "Clean-book PRIMARY RR2+Spark dual-magic Model 0 unlock. "
                "Offline GOAL_SCREEN_FAIL stands; not GOAL claim."
            ),
        },
        "prereg.json": {
            "schema_version": "sonic_prereg.v1",
            "hypothesis_id": HYP,
            "status": "FROZEN",
            "prereg_md": str(PREREG_MD.resolve()),
            "prereg_md_sha256": sha256_file(PREREG_MD),
        },
        "cost_source_manifest.json": {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "hypothesis_id": HYP,
            "status": "UNVERIFIED_TESTER_CURRENT_SPREAD",
            "note": (
                "Missing/zero cost fields must NOT be treated as zero friction. "
                "Screen PF is tester spread=current only; QFSI freeze still GAP."
            ),
        },
    }
    for name, obj in stubs.items():
        (STUBS / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    include_note = STUBS / "include_note.txt"
    include_note.write_text(
        "EA_SBSparkBook clean-book v1.10: SB RR2/MaxKZ2 module + SparkAsian module. "
        "Heat=1 priority A>B. Trade.mqh is MT5 stdlib.\n",
        encoding="utf-8",
    )

    task = STUBS / "task_packet.json"
    prereg = STUBS / "prereg.json"
    cost = STUBS / "cost_source_manifest.json"

    evidence_files = [
        ("task_packet", task),
        ("source", EA),
        ("prereg", prereg),
        ("cost_source_manifest", cost),
        ("include_0001", include_note),
        ("include_0002", SB_MOD),
        ("include_0003", SPK_MOD),
    ]

    evidence = []
    include_records = []
    for label, path in evidence_files:
        h = sha256_file(path)
        evidence.append(
            {
                "label": label,
                "kind": "file",
                "path": str(path.resolve()),
                "sha256": h,
            }
        )
        if label.startswith("include_"):
            include_records.append(
                f"{str(path.resolve()).lower()}\t{h}"
            )

    include_records.sort()
    include_closure = sha256_text("\n".join(include_records))
    git_commit, git_status_sha = git_snapshot()

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": sha256_file(task),
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": "control",
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": MODEL,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": "",
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
            "Clean-book PRIMARY Model 0 control. Sleeve authority 194548+193358 reused "
            "as offline baseline only; this run is the dual-magic book EA. Not GOAL."
        ),
    }

    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(RECEIPT)
    SHA_TXT.write_text(receipt_sha + "\n", encoding="utf-8")
    print(f"GIT_COMMIT={git_commit}")
    print(f"GIT_STATUS_SHA256={git_status_sha}")
    print(f"RECEIPT_PATH={RECEIPT}")
    print(f"RECEIPT_SHA256={receipt_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
