#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-pair intraday lead-lag probe.

Minimal measurement harness for hypotheses like EURJPY -> USDJPY.
It aligns bar-close timestamps only, tests lagged leader returns over
multiple windows, and evaluates follower same-direction follow-through.

This is a research probe, not production strategy logic.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Bar:
    ts: str
    close: float


def read_bars(path: Path) -> Dict[str, Bar]:
    bars: Dict[str, Bar] = {}
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ts = str(row.get("Date") or row.get("timestamp") or row.get("time") or "").strip()
            if not ts:
                continue
            close_s = row.get("Close") or row.get("close")
            if close_s in (None, ""):
                continue
            try:
                close = float(close_s)
            except Exception:
                continue
            bars[ts] = Bar(ts=ts, close=close)
    return bars


def returns(series: List[float], lag: int) -> List[float]:
    out = [0.0] * len(series)
    for i in range(lag, len(series)):
        prev = series[i - lag]
        out[i] = 0.0 if prev == 0 else (series[i] / prev - 1.0)
    return out


def sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def evaluate_lead_lag(leader: Dict[str, Bar], follower: Dict[str, Bar], lags: List[int], cost_bps: float) -> dict:
    common_ts = sorted(set(leader.keys()) & set(follower.keys()))
    leader_close = [leader[t].close for t in common_ts]
    follower_close = [follower[t].close for t in common_ts]

    result = {
        "n_common_bars": len(common_ts),
        "cost_bps": cost_bps,
        "windows": {},
    }

    for lag in lags:
        lead_ret = returns(leader_close, lag)
        foll_ret = returns(follower_close, 1)  # next-bar follow-through on same clock
        same_dir = 0
        valid = 0
        pnl_like: List[float] = []

        for i in range(lag, len(common_ts) - 1):
            s = sign(lead_ret[i])
            if s == 0:
                continue
            valid += 1
            gross = s * foll_ret[i + 1]
            net = gross - cost_bps / 10000.0
            pnl_like.append(net)
            if sign(net) == 1:
                same_dir += 1

        hit_rate = (same_dir / valid * 100.0) if valid else 0.0
        expectancy_bps = (sum(pnl_like) / len(pnl_like) * 10000.0) if pnl_like else 0.0
        result["windows"][str(lag)] = {
            "n": valid,
            "hit_rate_pct": round(hit_rate, 2),
            "expectancy_bps": round(expectancy_bps, 4),
            "mean_gross_bps": round((sum([x + cost_bps / 10000.0 for x in pnl_like]) / len(pnl_like) * 10000.0), 4) if pnl_like else 0.0,
        }

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leader", required=True, help="CSV with Date/Close for leader pair")
    ap.add_argument("--follower", required=True, help="CSV with Date/Close for follower pair")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lags", default="1,3,5,10,15")
    ap.add_argument("--cost-bps", type=float, default=2.0)
    args = ap.parse_args()

    leader = read_bars(Path(args.leader))
    follower = read_bars(Path(args.follower))
    lags = [int(x.strip()) for x in args.lags.split(",") if x.strip()]

    result = evaluate_lead_lag(leader, follower, lags, args.cost_bps)
    result["label"] = args.label
    result["leader_file"] = str(Path(args.leader))
    result["follower_file"] = str(Path(args.follower))

    out = Path(args.out)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
