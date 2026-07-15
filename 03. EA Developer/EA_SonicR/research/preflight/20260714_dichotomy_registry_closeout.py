#!/usr/bin/env python3
"""Append dichotomy-break offline KILL rows."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
PROBE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "20260714_DICHOTOMY_BREAK_OFFLINE_PROBES.json"


def main() -> None:
    payload = json.loads(PROBE.read_text(encoding="utf-8"))
    receipt = payload.get("receipt_sha256") or "7B0D607553DF8497B693DB562924B9C3B9018999132E013873D814F4EB798D90"
    rows = []
    for p in payload["probes"]:
        m = p.get("metrics") or {}
        rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": p["hypothesis_id"],
                "state": "killed",
                "verdict": p["verdict"],
                "reason": f"dichotomy offline; notes={p.get('kill_notes')}; n={m.get('n')} pf={m.get('pf')} tpw={m.get('tpw')} x15={(p.get('cost_stress') or {}).get('x1_5', {}).get('pf')}",
                "updated_at": "2026-07-14",
                "lane": "dichotomy_break_20260714",
                "parent_candidate": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "model": "offline_closed_bar_probe",
                "prereg_path": {
                    "HYP-RR2-EXIT-BE1R-M15PATH-001": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_RR2_EXIT_BE1R_M15PATH_001_PREREG.md",
                    "HYP-RR2-USJP-YIELD-ZGATE-001": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_RR2_USJP_YIELD_ZGATE_001_PREREG.md",
                    "HYP-BOOK-CORRCAP-RR2-SPARK-001": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_BOOK_CORRCAP_RR2_SPARK_001_PREREG.md",
                }[p["hypothesis_id"]],
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DICHOTOMY_BREAK_OFFLINE_PROBES.md",
                "metrics": m,
                "validation": {
                    "model0": "WITHHELD_KILL_FAST",
                    "probe_receipt": receipt,
                },
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
            }
        )
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"killed": [r["hypothesis_id"] for r in rows]}, indent=2))


if __name__ == "__main__":
    main()
