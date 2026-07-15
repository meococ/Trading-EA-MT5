#!/usr/bin/env python3
"""Build ContractReceipts for rebuild-campaign Model 0 children."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "rebuild_campaign"

AF_RUNS = ROOT / "02. AlphaFactory" / "runs"

CHILDREN = [
    {
        "hyp": "HYP-SB-MAXKZ2-DENSITY-002",
        "folder": "sb_maxkz2",
        "ea_name": "EA_SilverBullet",
        "ea": ROOT / "03. EA Developer" / "EA_SilverBullet" / "EA_SilverBullet_v2.mq5",
        "prereg": ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs" / "20260714_H_SB_MAXKZ2_DENSITY_002_PREREG.md",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        # alpha.ps1 sorts override keys
        "overrides": "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpUseWeekendFlat=1",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "control_run": AF_RUNS / "EA_SilverBullet" / "20260714_002505",
        "note": "SB MaxKZ2 density child vs A1 control; Deposit 100000.",
    },
    {
        "hyp": "HYP-SB-NYPM-KZ-001",
        "folder": "sb_nypm",
        "ea_name": "EA_SilverBullet",
        "ea": ROOT / "03. EA Developer" / "EA_SilverBullet" / "EA_SilverBullet_v2.mq5",
        "prereg": ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs" / "20260714_H_SB_NYPM_KZ_001_PREREG.md",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpNYPM_End=22;InpNYPM_Start=20;InpUseNYPM=1;InpUseWeekendFlat=1",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "control_run": AF_RUNS / "EA_SilverBullet" / "20260714_002505",
        "note": "SB NYPM session expand + A1 weekend-flat; Deposit 100000.",
    },
    {
        "hyp": "HYP-ITSM-NYONLY-STRICTALIGN-002",
        "folder": "itsm_nyonly",
        "ea_name": "EA_ITSM",
        "ea": ROOT / "03. EA Developer" / "EA_ITSM" / "EA_ITSM.mq5",
        "prereg": ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs" / "20260714_H_ITSM_NYONLY_STRICTALIGN_002_PREREG.md",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 10000,
        # InpMaxTradesDay declared but dead in source (effective 1/day); keep for receipt parity with prereg text.
        "overrides": "InpKZ1_EndH=18;InpKZ1_StartH=15;InpMaxTradesDay=2;InpRR_Ratio=2.0;InpRiskPct=0.5;InpStrictAlign=1;InpTradeFri=0;InpUseKZ2=0",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "control_run": AF_RUNS / "EA_ITSM" / "20260714_003920",
        "note": "ITSM NY-only + StrictAlign; MaxTradesDay input is no-op (1/day hard).",
    },
    {
        "hyp": "HYP-ITSM-LONDON-ONLY-STRICTALIGN-002",
        "folder": "itsm_london",
        "ea_name": "EA_ITSM",
        "ea": ROOT / "03. EA Developer" / "EA_ITSM" / "EA_ITSM.mq5",
        "prereg": ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs" / "20260714_H_ITSM_LONDON_ONLY_STRICTALIGN_002_PREREG.md",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 10000,
        "overrides": "InpMaxTradesDay=2;InpRR_Ratio=2.0;InpRiskPct=0.5;InpStrictAlign=1;InpTradeFri=0;InpUseKZ2=0",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "control_run": AF_RUNS / "EA_ITSM" / "20260714_003920",
        "note": "ITSM London-only + StrictAlign sibling; KZ1 defaults [09,12).",
    },
    {
        "hyp": "HYP-SPARK-ASIAN-GBPUSD-001",
        "folder": "spark_gbpusd",
        "ea_name": "EA_M15SparkAsian",
        "ea": ROOT / "03. EA Developer" / "EA_M15SparkAsian" / "EA_M15SparkAsian.mq5",
        "prereg": ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs" / "20260714_H_SPARK_ASIAN_GBPUSD_001_PREREG.md",
        "symbol": "GBPUSD",
        "period": "M15",
        "deposit": 100000,
        "overrides": "InpMagic=880931;InpMaxPerDay=2;InpRiskPct=0.5;InpTPRatio=1.5;InpTradeFri=0;InpTradeMon=0;InpTradeThu=1;InpTradeTue=0;InpTradeWed=1",
        "geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
        "control_run": AF_RUNS / "EA_M15SparkAsian" / "20260714_002821",
        "note": "Spark Asian GBPUSD Wed-Thu S107 transfer; not USDJPY densify.",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def nogit_snapshot(ea: Path) -> tuple[str, str]:
    paths = [ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", ea]
    records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
    prov = sha256_text("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    return commit, sha256_text(status)


def normalize_overrides(ov: str) -> str:
    """Match alpha.ps1 ConvertFrom-NormalizedOverrideMap (case-insensitive key sort)."""
    pairs = []
    for part in ov.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        pairs.append((k, v))
    pairs.sort(key=lambda kv: kv[0].lower())
    return ";".join(f"{k}={v}" for k, v in pairs)


def build_one(cfg: dict) -> str:
    contracts = PRE / cfg["folder"] / "contracts"
    stubs = contracts / f"receipt_stubs_{cfg['hyp'].replace('-', '_')}"
    contracts.mkdir(parents=True, exist_ok=True)
    stubs.mkdir(parents=True, exist_ok=True)

    hyp = cfg["hyp"]
    overrides = normalize_overrides(cfg["overrides"])
    task = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": hyp,
        "ea_name": cfg["ea_name"],
        "symbol": cfg["symbol"],
        "period": cfg["period"],
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": "challenger",
        "overrides": overrides,
        "note": cfg["note"],
    }
    prereg = {
        "schema_version": "sonic_prereg.v1",
        "hypothesis_id": hyp,
        "status": "FROZEN",
        "prereg_md": str(cfg["prereg"].resolve()),
        "prereg_md_sha256": sha256_file(cfg["prereg"]),
        "overrides": overrides,
    }
    cost = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "hypothesis_id": hyp,
        "status": "UNVERIFIED_TESTER_DEFAULT",
        "policy": "DOCUMENTED_RESEARCH_PROXY",
        "spread": "current",
        "promotion_eligible": False,
    }
    for name, obj in {
        "task_packet.json": task,
        "prereg.json": prereg,
        "cost_source_manifest.json": cost,
    }.items():
        (stubs / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    include = stubs / "include_note.txt"
    include.write_text(
        f"{cfg['ea_name']} Model 0 rebuild-campaign child; closed-bar[1] assumed; "
        "include closure stub for AlphaFactory receipt binding.\n",
        encoding="utf-8",
    )

    tpath, ppath, cpath = stubs / "task_packet.json", stubs / "prereg.json", stubs / "cost_source_manifest.json"
    h_task, h_prereg, h_cost = sha256_file(tpath), sha256_file(ppath), sha256_file(cpath)
    h_include, h_source = sha256_file(include), sha256_file(cfg["ea"])
    include_closure = sha256_text(f"{str(include.resolve()).lower()}\t{h_include}")
    git_commit, git_status_sha = nogit_snapshot(cfg["ea"])
    ctrl_manifest = cfg["control_run"] / "run_manifest.json"
    ctrl_report = cfg["control_run"] / "report.html"
    if not ctrl_manifest.is_file() or not ctrl_report.is_file():
        raise FileNotFoundError(f"missing control artifacts under {cfg['control_run']}")

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": hyp,
        "task_packet_sha256": h_task,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": hyp,
            "run_role": "challenger",
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
            "include_closure_sha256": include_closure,
        },
        "evidence": [
            {"label": "task_packet", "kind": "file", "path": str(tpath.resolve()), "sha256": h_task},
            {"label": "source", "kind": "file", "path": str(cfg["ea"].resolve()), "sha256": h_source},
            {"label": "prereg", "kind": "file", "path": str(ppath.resolve()), "sha256": h_prereg},
            {"label": "cost_source_manifest", "kind": "file", "path": str(cpath.resolve()), "sha256": h_cost},
            {"label": "include_0001", "kind": "file", "path": str(include.resolve()), "sha256": h_include},
            {
                "label": "matched_control_manifest",
                "kind": "file",
                "path": str(ctrl_manifest.resolve()),
                "sha256": sha256_file(ctrl_manifest),
            },
            {
                "label": "matched_control_report",
                "kind": "file",
                "path": str(ctrl_report.resolve()),
                "sha256": sha256_file(ctrl_report),
            },
        ],
        "generated_at_utc": "2026-07-14T12:20:00Z",
        "note": cfg["note"],
    }
    receipt_path = contracts / f"20260714_{hyp.replace('-', '_')}_CONTRACT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (contracts / f"20260714_{hyp.replace('-', '_')}_CONTRACT_RECEIPT.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(f"{hyp}\t{receipt_sha}\t{receipt_path}")
    return receipt_sha


def main() -> int:
    for cfg in CHILDREN:
        build_one(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
