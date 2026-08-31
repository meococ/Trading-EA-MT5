#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal FX-fix reversal probe.

Measures pre-fix and post-fix return windows around a fixed daily timestamp.
Intended for fast falsification of Tokyo / ECB / London fix reversal hypotheses.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


def parse_dt(s: str) -> datetime:
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized datetime: {s}")


def read_bars(path: Path) -> Dict[datetime, float]:
    out: Dict[datetime, float] = {}
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                dt = parse_dt(str(row["Date"]))
                close = float(row["Close"])
            except Exception:
                continue
            out[dt] = close
    return out


def value_at_or_after(ts: datetime, bars: Dict[datetime, float]):
    future = [t for t in bars.keys() if t >= ts]
    if not future:
        return None
    t0 = min(future)
    return t0, bars[t0]


def calc_return(a: float, b: float) -> float:
    return 0.0 if a == 0 else (b / a - 1.0)


def stats(values: List[float], cost_bps: float) -> dict:
    if not values:
        return {"n": 0, "mean_gross_bps": 0.0, "mean_net_bps": 0.0, "hit_rate_pct": 0.0}
    gross = [v * 10000.0 for v in values]
    net = [g - cost_bps for g in gross]
    wins = sum(1 for x in net if x > 0)
    return {
        "n": len(values),
        "mean_gross_bps": round(sum(gross) / len(gross), 4),
        "mean_net_bps": round(sum(net) / len(net), 4),
        "hit_rate_pct": round(100.0 * wins / len(values), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--fix-time", required=True, help="HH:MM UTC, e.g. 00:55")
    ap.add_argument("--pre", default="5,10,15")
    ap.add_argument("--post", default="5,10,15")
    ap.add_argument("--cost-bps", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    bars = read_bars(Path(args.bars))
    pre_windows = [int(x) for x in args.pre.split(',') if x.strip()]
    post_windows = [int(x) for x in args.post.split(',') if x.strip()]
    hh, mm = map(int, args.fix_time.split(':'))

    all_dates = sorted({t.date() for t in bars.keys()})
    result = {"label": args.label, "fix_time": args.fix_time, "cost_bps": args.cost_bps, "pre": {}, "post": {}}

    for w in pre_windows:
        vals = []
        for d in all_dates:
            fix_dt = datetime(d.year, d.month, d.day, hh, mm)
            a = value_at_or_after(fix_dt - timedelta(minutes=w), bars)
            b = value_at_or_after(fix_dt, bars)
            if not a or not b:
                continue
            vals.append(calc_return(a[1], b[1]))
        result['pre'][str(w)] = stats(vals, args.cost_bps)

    for w in post_windows:
        vals = []
        for d in all_dates:
            fix_dt = datetime(d.year, d.month, d.day, hh, mm)
            a = value_at_or_after(fix_dt, bars)
            b = value_at_or_after(fix_dt + timedelta(minutes=w), bars)
            if not a or not b:
                continue
            vals.append(calc_return(a[1], b[1]))
        result['post'][str(w)] = stats(vals, args.cost_bps)

    out = Path(args.out)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print(f'Wrote: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
