#!/usr/bin/env python3
"""Build NOGIT contract receipts for Owner-rebuke R&D wave Model 0 screens."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def build(cfg: dict) -> tuple[str, str]:
    ea = ROOT / cfg["ea_rel"]
    prereg = ROOT / cfg["prereg_rel"]
    agents = ROOT / "AGENTS.md"
    goal = ROOT / "01. GOAL/GOAL.md"
    stub_dir = ROOT / cfg["stub_rel"]
    stub_dir.mkdir(parents=True, exist_ok=True)
    contracts = stub_dir.parent

    prov_paths = [agents, goal, ea]
    records = []
    root_full = str(ROOT.resolve())
    for p in prov_paths:
        full = str(p.resolve())
        rel = full[len(root_full) :].lstrip("\\/").replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(p)}")
    prov_sha = sha256_text("\n".join(records))
    git_commit = f"NOGIT-{prov_sha}"
    git_status_sha256 = sha256_text(
        "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov_sha}"])
    )

    overrides = cfg.get("overrides", "")
    task_packet = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": cfg["hypothesis_id"],
        "ea_name": cfg["ea_name"],
        "symbol": cfg["symbol"],
        "period": cfg["period"],
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": "control",
        "overrides": overrides,
        "note": cfg.get("note", "Owner rebuke R&D wave; cost unverified."),
    }
    (stub_dir / "task_packet.json").write_text(
        json.dumps(task_packet, indent=2) + "\n", encoding="utf-8"
    )
    (stub_dir / "prereg.json").write_text(
        json.dumps(
            {
                "hypothesis_id": cfg["hypothesis_id"],
                "prereg_path": str(prereg),
                "prereg_sha256": sha256_file(prereg),
                "frozen": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (stub_dir / "cost_source_manifest.json").write_text(
        json.dumps(
            {
                "cost_provenance": "UNVERIFIED",
                "spread_policy": "tester_current",
                "commission": "unknown_not_zero",
                "slippage": "unknown_not_zero",
                "note": "Model 0 screen only; missing cost != 0.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (stub_dir / "include_note.txt").write_text(
        f"{cfg['ea_name']} Trade.mqh standard library stub for include closure.\n",
        encoding="utf-8",
    )

    def file_ev(label: str, path: Path) -> dict:
        return {
            "label": label,
            "kind": "file",
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
        }

    evidence = [
        file_ev("task_packet", stub_dir / "task_packet.json"),
        file_ev("source", ea),
        file_ev("prereg", stub_dir / "prereg.json"),
        file_ev("cost_source_manifest", stub_dir / "cost_source_manifest.json"),
        file_ev("include_0001", stub_dir / "include_note.txt"),
    ]
    include_items = [e for e in evidence if e["label"].startswith("include_")]
    include_records = []
    for item in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
        path = str(Path(item["path"]).resolve()).lower()
        include_records.append(f"{path}\t{item['sha256'].upper()}")
    include_closure_sha256 = sha256_text("\n".join(include_records))

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": cfg["hypothesis_id"],
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha256,
        "binding": {
            "hypothesis_id": cfg["hypothesis_id"],
            "run_role": "control",
            "ea_name": cfg["ea_name"],
            "symbol": cfg["symbol"],
            "period": cfg["period"],
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "off",
            "deposit": cfg["deposit"],
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": cfg["geometry"],
            "include_closure_sha256": include_closure_sha256,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": cfg.get("note", ""),
    }
    receipt_path = contracts / cfg["receipt_name"]
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (contracts / (cfg["receipt_name"] + ".sha256.txt")).write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(cfg["hypothesis_id"], "RECEIPT_SHA256", receipt_sha)
    return str(receipt_path), receipt_sha


CFGS = [
    {
        "hypothesis_id": "HYP-ASIAN-SWEEP-RECLAIM-M15-001",
        "ea_name": "EA_M15AsianSweepReclaim",
        "ea_rel": "03. EA Developer/EA_M15AsianSweepReclaim/EA_M15AsianSweepReclaim.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ASIAN_SWEEP_RECLAIM_M15_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/asian_sweep_reclaim_m15/contracts/receipt_stubs_HYP_ASR_001",
        "receipt_name": "20260714_HYP_ASIAN_SWEEP_RECLAIM_M15_001_CONTRACT_RECEIPT.json",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "note": "Owner rebuke wave; Asia sweep->London reclaim; not FailedORB/SB densify.",
    },
    {
        "hypothesis_id": "HYP-LONDON-ORB-ACCEPT-001",
        "ea_name": "EA_M15LondonORBAccept",
        "ea_rel": "03. EA Developer/EA_M15LondonORBAccept/EA_M15LondonORBAccept.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_LONDON_ORB_ACCEPT_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/london_orb_accept/contracts/receipt_stubs_HYP_LORBA_001",
        "receipt_name": "20260714_HYP_LONDON_ORB_ACCEPT_001_CONTRACT_RECEIPT.json",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "note": "London ORB dual-close acceptance rebuild of parked LondonORB.",
    },
    {
        "hypothesis_id": "HYP-ENGULF-TREND-M15-001",
        "ea_name": "EA_M15EngulfTrend",
        "ea_rel": "03. EA Developer/EA_M15EngulfTrend/EA_M15EngulfTrend.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ENGULF_TREND_M15_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/engulf_trend_m15/contracts/receipt_stubs_HYP_ENGT_001",
        "receipt_name": "20260714_HYP_ENGULF_TREND_M15_001_CONTRACT_RECEIPT.json",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "note": "Engulf + D1 EMA50; CI/Chop removed; Mon-Thu.",
    },
    {
        "hypothesis_id": "HYP-SB-MAXKZ2-EURUSD-TRANSFER-001",
        "ea_name": "EA_SilverBullet",
        "ea_rel": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXKZ2_EURUSD_TRANSFER_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/sb_maxkz2_eurusd/contracts/receipt_stubs_HYP_SB_MAXKZ2_EUR_001",
        "receipt_name": "20260714_HYP_SB_MAXKZ2_EURUSD_TRANSFER_001_CONTRACT_RECEIPT.json",
        "symbol": "EURUSD",
        "period": "M15",
        "deposit": 100000,
        "overrides": "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpUseWeekendFlat=1",
        "geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
        "note": "MaxKZ2 geometry verbatim transfer to EURUSD; not USDJPY densify.",
    },
]


if __name__ == "__main__":
    out = {}
    for cfg in CFGS:
        path, sha = build(cfg)
        out[cfg["hypothesis_id"]] = {"path": path, "sha256": sha}
    print(json.dumps(out, indent=2))
