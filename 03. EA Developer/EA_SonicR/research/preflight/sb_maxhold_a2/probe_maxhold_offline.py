# -*- coding: utf-8 -*-
"""Offline probe: simulate max-hold 30h on SB A1 PX6 trade log (pair OPEN/CLOSE)."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
TRADES = (
    ROOT
    / "02. AlphaFactory/runs/EA_SilverBullet/20260714_002505/analysis/logs"
    / "USDJPY_20260325_PX6_Trades_20210101_000000_20431953.csv"
)
OUT = (
    ROOT
    / "03. EA Developer/EA_SonicR/research/preflight/sb_maxhold_a2"
    / "20260714_SB_MAXHOLD_A2_OFFLINE_PROBE.json"
)
MAX_HOLD_H = 30.0


def parse_dt(s: str) -> datetime:
    s = s.strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(s)


def main() -> int:
    opens: dict[str, dict] = {}
    closes: dict[str, dict] = {}
    with TRADES.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            pid = str(r.get("position_id", "")).strip()
            if not pid:
                continue
            if r.get("action") == "OPEN":
                opens[pid] = r
            elif r.get("action") == "CLOSE" and str(r.get("is_final_close", "0")) in (
                "1",
                "true",
                "True",
            ):
                closes[pid] = r

    n = 0
    clipped = 0
    baseline = 0.0
    sim = 0.0
    holds = []
    for pid, o in opens.items():
        c = closes.get(pid)
        if not c:
            continue
        try:
            t0 = parse_dt(o["event_time"])
            t1 = parse_dt(c["event_time"])
            pnl = float(c["net_profit"])
        except Exception:
            continue
        if t1 <= t0:
            continue
        held = (t1 - t0).total_seconds() / 3600.0
        n += 1
        baseline += pnl
        holds.append(held)
        if held > MAX_HOLD_H:
            clipped += 1
            # Linear-path proxy (disclose): scale realized pnl to max-hold fraction.
            sim += pnl * (MAX_HOLD_H / held)
        else:
            sim += pnl

    holds_sorted = sorted(holds)
    elapsed_wk = 260.7142857142857
    result = {
        "schema_version": "sb_maxhold_a2_offline_probe.v1",
        "parent_run_id": "20260714_002505",
        "hypothesis_candidate": "HYP-SB-MAXHOLD-A2-001",
        "max_hold_hours": MAX_HOLD_H,
        "n_round_trips": n,
        "baseline_net": round(baseline, 2),
        "sim_net_linear_path_proxy": round(sim, 2),
        "delta_net": round(sim - baseline, 2),
        "n_clipped": clipped,
        "pct_clipped": round(clipped / n * 100.0, 2) if n else 0.0,
        "median_hold_h": holds_sorted[len(holds_sorted) // 2] if holds_sorted else None,
        "p90_hold_h": holds_sorted[int(0.9 * (len(holds_sorted) - 1))] if holds_sorted else None,
        "max_hold_h": max(holds_sorted) if holds_sorted else None,
        "baseline_tpw": round(n / elapsed_wk, 4),
        "caveat": "Clipped trades use linear-path PnL scale — not tick-true MTM at flat.",
    }
    if n < 50:
        result["verdict"] = "PROBE_FAIL_SAMPLE"
    elif clipped == 0:
        result["verdict"] = "PROBE_NULL_EFFECT_SKIP_MODEL0"
    elif result["delta_net"] < -0.05 * abs(baseline) and baseline > 0:
        result["verdict"] = "PROBE_DESTRUCTIVE_PROXY"
    else:
        result["verdict"] = "PROBE_PASS_TO_MODEL0_NONDESTRUCTIVE_PROXY"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(result, indent=2) + "\n"
    OUT.write_text(body, encoding="utf-8")
    sha = hashlib.sha256(body.encode()).hexdigest().upper()
    OUT.with_suffix(".sha256.txt").write_text(sha + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "sha256": sha, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
