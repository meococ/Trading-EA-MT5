#!/usr/bin/env python3
"""Boot independent rebuild lane: registry append + probe matrix + thick-edge stress."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / r"03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl"
PRE = ROOT / r"03. EA Developer\EA_SonicR\research\preflight"
TOOLS = ROOT / r"02. AlphaFactory\tools"
sys.path.insert(0, str(TOOLS))

ROWS = [
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-SESSION-VWAP-RECLAIM-M15-001",
        "state": "preregistered",
        "parent_candidate": None,
        "feature_family": "m15_session_vwap_reclaim",
        "lane": "independent_rebuild_friction_20260714",
        "setup_type": "Session VWAP stretch then reclaim fade; closed-bar[1]; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner rebuke deferred P2; friction dead-end rebuild; GPT waived",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SESSION_VWAP_RECLAIM_M15_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_SVR_001",
        "source_path": "03. EA Developer/EA_M15SessionVWAPReclaim/EA_M15SessionVWAPReclaim.mq5",
        "run_ids": [],
        "metrics": None,
        "validation": {"cost_stress": "tester current + x1.5/x2 haircut screen"},
    },
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H1-BOS-M15-PB-001",
        "state": "preregistered",
        "parent_candidate": None,
        "feature_family": "h1_bos_m15_pullback",
        "lane": "independent_rebuild_friction_20260714",
        "setup_type": "H1 swing BOS bias + M15 EMA20 pullback; closed-bar; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner rebuke deferred H1BOS; friction dead-end rebuild; GPT waived",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_BOS_M15_PB_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_HBOS_001",
        "source_path": "03. EA Developer/EA_H1BOS_M15Pullback/EA_H1BOS_M15Pullback.mq5",
        "run_ids": [],
        "metrics": None,
        "validation": {"cost_stress": "tester current + x1.5/x2 haircut screen"},
    },
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-ASIAN-TAIL-FADE-USDJPY-001",
        "state": "preregistered",
        "parent_candidate": "EA_AsianTailFade XAU scaffold ATR port",
        "feature_family": "m15_asian_tail_fade_usdjpy",
        "lane": "independent_rebuild_friction_20260714",
        "setup_type": "Early-Asia ATR move fade late Asia; USDJPY ATR port; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner rebuke systems #1 ATF port; friction dead-end rebuild; GPT waived",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ASIAN_TAIL_FADE_USDJPY_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_ATFJ_001",
        "source_path": "03. EA Developer/EA_M15AsianTailFade/EA_M15AsianTailFade.mq5",
        "run_ids": [],
        "metrics": None,
        "validation": {"cost_stress": "tester current + x1.5/x2 haircut screen"},
    },
]


def append_registry() -> list[str]:
    existing = REG.read_text(encoding="utf-8")
    appended: list[str] = []
    for row in ROWS:
        marker = f'"hypothesis_id":"{row["hypothesis_id"]}"'
        fam = f'"feature_family":"{row["feature_family"]}"'
        if marker in existing and fam in existing:
            print("skip existing", row["hypothesis_id"])
            continue
        with REG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        appended.append(row["hypothesis_id"])
    return appended


def write_matrix() -> str:
    matrix = {
        "schema": "independent_rebuild_probe_matrix_v1",
        "generated_ict": "2026-07-14T19:55:00+07:00",
        "authority": "Owner iterate/rebuild; friction dead-end; GPT waived; free MT",
        "anti_patterns_honored": [
            "no MaxKZ densify",
            "no RR retune",
            "no USBILL rescue",
            "no post-hoc filters from RR2/MaxKZ2/Spark",
            "no GPT Deep Research",
        ],
        "dedup_clearance": (
            "03. EA Developer/EA_SonicR/research/readouts/"
            "20260714_DISCOVERY_WAVE2_VWAP_BOS_ATF_DEDUP_CLEARANCE.md"
        ),
        "screen_contract": {
            "kill": "PF<1.00 OR tpw not in [1,6] OR N<80 OR x1.5_pf < 1.00",
            "park": "survives kill but PF<=1.30 or tpw not in [2,5] OR x1.5_pf < 1.25",
            "hit_research": "PF>1.30 AND tpw in [2,5] tester current",
            "goal_stress_prefer": (
                "x1.5_pf >= 1.25 AND x2_pf >= 1.00 "
                "(report-only haircut; not QFSI)"
            ),
        },
        "candidates": [
            {
                "hypothesis_id": "HYP-SESSION-VWAP-RECLAIM-M15-001",
                "ea": "EA_M15SessionVWAPReclaim",
                "status": "QUEUED_MODEL0",
                "offline_probe": "NONE_CHEAP_ARTIFACT_WAIVED_TO_MODEL0",
            },
            {
                "hypothesis_id": "HYP-H1-BOS-M15-PB-001",
                "ea": "EA_H1BOS_M15Pullback",
                "status": "QUEUED_MODEL0",
                "offline_probe": "NONE_CHEAP_ARTIFACT_WAIVED_TO_MODEL0",
            },
            {
                "hypothesis_id": "HYP-ASIAN-TAIL-FADE-USDJPY-001",
                "ea": "EA_M15AsianTailFade",
                "status": "QUEUED_MODEL0",
                "offline_probe": "ENGINEERING_PORT_NOT_GOLD_RESULT_TRANSFER",
            },
            {
                "hypothesis_id": "OFFLINE-LONDONNY-THICK-EDGE-SLEEVE",
                "ea": "EA_LondonNY",
                "run_id": "20260709_074209",
                "status": "OFFLINE_COSTSTRESS_NOTE",
                "note": "sparse GOAL-closed; thick expectancy sleeve reference only",
            },
        ],
        "forbidden_reopens": [
            "MaxKZ densify",
            "RR2.5/3.0",
            "USBILL z",
            "ITSM T10 day mine",
            "Gotobi/LondonNY sole GOAL book",
        ],
    }
    out = PRE / "20260714_INDEPENDENT_REBUILD_PROBE_MATRIX_V1.json"
    text = json.dumps(matrix, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
    Path(str(out) + ".sha256.txt").write_text(sha + "\n", encoding="utf-8")
    print("matrix", out.name, sha)
    return sha


def thick_edge_londonny() -> dict:
    """Report-only cost stress on thick-edge LondonNY sleeve (not GOAL reopen)."""
    from sonic_cost_stress import run_dir_for, load_report_trades, stress  # type: ignore

    # Prefer CLI-compatible path if helpers differ — fall back to subprocess.
    raise NotImplementedError


def main() -> int:
    appended = append_registry()
    print("appended", appended)
    write_matrix()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
