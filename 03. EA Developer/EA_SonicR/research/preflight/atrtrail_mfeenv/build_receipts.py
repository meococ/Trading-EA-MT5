# -*- coding: utf-8 -*-
"""Contract receipts for ATR-trail Model 0 (ARM075-K15 primary + ARM100-K20 alt)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5"
OUT = ROOT / "03. EA Developer/EA_SonicR/research/preflight/atrtrail_mfeenv/contracts"
CTRL_MANIFEST = ROOT / "02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/run_manifest.json"
CTRL_REPORT = ROOT / "02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/report.html"

# Alphabetical key order matches alpha.ps1 Sort-Object on override map keys.
PRIMARY = {
    "hypothesis_id": "HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001",
    "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260715_H_RR2_EXIT_ATRTRAIL_MFEENV_ARM075_K15_001_PREREG.md",
    "overrides": (
        "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;"
        "InpPartialClose=0;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;"
        "InpTrailActivateR=0.75;InpTrailATR_Mul=1.5;InpTrailBE=0;"
        "InpUseTrail=1;InpUseWeekendFlat=1"
    ),
    "stub": "receipt_stubs_HYP_RR2_EXIT_ATRTRAIL_MFEENV_ARM075_K15_001",
    "receipt_name": "20260715_HYP_RR2_EXIT_ATRTRAIL_MFEENV_ARM075_K15_001_CONTRACT_RECEIPT.json",
    "note": (
        "ATR-trail native Model 0 primary ARM075/K15; parent RR2 194548; "
        "InpTrailBE=0; cost=UNVERIFIED_TESTER_DEFAULT or Real if available."
    ),
}
ALT = {
    "hypothesis_id": "HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001",
    "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260715_H_RR2_EXIT_ATRTRAIL_MFEENV_ARM100_K20_001_PREREG.md",
    "overrides": (
        "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;"
        "InpPartialClose=0;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;"
        "InpTrailActivateR=1.0;InpTrailATR_Mul=2.0;InpTrailBE=0;"
        "InpUseTrail=1;InpUseWeekendFlat=1"
    ),
    "stub": "receipt_stubs_HYP_RR2_EXIT_ATRTRAIL_MFEENV_ARM100_K20_001",
    "receipt_name": "20260715_HYP_RR2_EXIT_ATRTRAIL_MFEENV_ARM100_K20_001_CONTRACT_RECEIPT.json",
    "note": (
        "ATR-trail native Model 0 alternate ARM100/K20; a priori sibling; "
        "run after primary; do not densify from primary readout."
    ),
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def text_sha(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def build_one(spec: dict) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    stub = OUT / spec["stub"]
    stub.mkdir(parents=True, exist_ok=True)
    hyp = spec["hypothesis_id"]
    ov = spec["overrides"]

    task = {
        "hypothesis_id": hyp,
        "ea_name": "EA_SilverBullet",
        "symbol": "USDJPY",
        "period": "M15",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "deposit": 100000,
        "leverage": 100,
        "overrides": ov,
        "run_role": "challenger",
    }
    prereg = {
        "hypothesis_id": hyp,
        "prereg_path": spec["prereg_path"],
        "frozen": True,
        "probe_sha256": "1626718918088C2ED1EB1F24DD879BDB0ADA48338DADDACBB80E042923855B3B",
        "offline_authority": "mfe_envelope_proxy_not_deployable",
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker_target": "FivePercentOnline-Real",
        "observed_ok_if": "MetaQuotes-Demo_or_Real_busy",
        "spread_binding": "current",
        "note": (
            "Missing commission/slippage fields are not zero. "
            "Demo/tester cost label OK if Real busy; not research-grade QFSI freeze."
        ),
    }
    include_note = (
        "EA_SilverBullet_v2 tick trail ManageTrailingStop + closed M15 ATR14; "
        "Trade.mqh stdlib; InpTrailBE=0 native ATR trail monetization."
    )
    (stub / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (stub / "prereg.json").write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")
    (stub / "cost_source_manifest.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    (stub / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")

    evidence = [
        ("task_packet", stub / "task_packet.json"),
        ("source", EA),
        ("prereg", stub / "prereg.json"),
        ("cost_source_manifest", stub / "cost_source_manifest.json"),
        ("include_0001", stub / "include_note.txt"),
        ("matched_control_manifest", CTRL_MANIFEST),
        ("matched_control_report", CTRL_REPORT),
    ]
    evidence_objs = []
    include_records = []
    for label, path in evidence:
        h = sha256_file(path)
        evidence_objs.append(
            {"label": label, "kind": "file", "path": str(path.resolve()), "sha256": h}
        )
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{h}")

    include_closure = text_sha("\n".join(sorted(include_records)))

    agents = ROOT / "AGENTS.md"
    goal = ROOT / "01. GOAL" / "GOAL.md"
    records = []
    for p in (agents, goal, EA):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status_sha = text_sha(
        "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    )

    receipt_path = OUT / spec["receipt_name"]
    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": hyp,
        "task_packet_sha256": sha256_file(stub / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": hyp,
            "run_role": "challenger",
            "ea_name": "EA_SilverBullet",
            "symbol": "USDJPY",
            "period": "M15",
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": ov,
            "telemetry_tier": "off",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence_objs,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": spec["note"],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(receipt_path)
    sha_path = receipt_path.with_suffix(receipt_path.suffix + ".sha256.txt")
    # Prefer .sha256.txt sibling naming used elsewhere
    sha_txt = OUT / (receipt_path.stem + ".sha256.txt")
    sha_txt.write_text(rec_sha + "\n", encoding="utf-8")
    return {
        "hypothesis_id": hyp,
        "receipt": str(receipt_path),
        "sha256": rec_sha,
        "sha_txt": str(sha_txt),
        "overrides": ov,
        "commit": commit,
        "source_sha256": sha256_file(EA),
    }


def main() -> int:
    results = [build_one(PRIMARY), build_one(ALT)]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
