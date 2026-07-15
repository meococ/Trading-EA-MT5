#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone event-window drift audit.

Measures pre/post-event directional edge directly on price bars using a curated
calendar CSV with schema: date,time_utc,event_type,currency,importance.
This is analysis-only; it does not encode any trading system logic.
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
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized datetime: {s}")


def read_events(path: Path) -> List[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                t = parse_dt(f"{row['date']} {row['time_utc']}")
            except Exception:
                continue
            out.append({
                'time': t,
                'event_type': row.get('event_type', ''),
                'currency': row.get('currency', ''),
                'importance': int(row.get('importance', '0') or 0),
            })
    return out


def read_bars(path: Path) -> Dict[datetime, float]:
    out: Dict[datetime, float] = {}
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                dt = parse_dt(str(row['Date']))
                close = float(row['Close'])
            except Exception:
                continue
            out[dt] = close
    return out


def value_at_or_after(ts: datetime, bars: Dict[datetime, float]) -> tuple[datetime, float] | None:
    future = [t for t in bars.keys() if t >= ts]
    if not future:
        return None
    t0 = min(future)
    return t0, bars[t0]


def calc_return(a: float, b: float) -> float:
    return 0.0 if a == 0 else (b / a - 1.0)


def stats(values: List[float], cost_bps: float) -> dict:
    if not values:
        return {'n': 0, 'mean_gross_bps': 0.0, 'mean_net_bps': 0.0, 'hit_rate_pct': 0.0}
    gross_bps = [v * 10000.0 for v in values]
    net_bps = [g - cost_bps for g in gross_bps]
    wins = sum(1 for x in net_bps if x > 0)
    return {
        'n': len(values),
        'mean_gross_bps': round(sum(gross_bps) / len(gross_bps), 4),
        'mean_net_bps': round(sum(net_bps) / len(net_bps), 4),
        'hit_rate_pct': round(100.0 * wins / len(values), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--bars', required=True)
    ap.add_argument('--events', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pre', default='30,60,90')
    ap.add_argument('--post', default='15,30')
    ap.add_argument('--cost-bps', type=float, default=2.0)
    args = ap.parse_args()

    bars = read_bars(Path(args.bars))
    events = read_events(Path(args.events))
    pre_windows = [int(x) for x in args.pre.split(',') if x.strip()]
    post_windows = [int(x) for x in args.post.split(',') if x.strip()]

    result = {
        'label': args.label,
        'cost_bps': args.cost_bps,
        'pre_windows': pre_windows,
        'post_windows': post_windows,
        'pre': {},
        'post': {},
    }

    for w in pre_windows:
        vals = []
        for e in events:
            start = value_at_or_after(e['time'] - timedelta(minutes=w), bars)
            end = value_at_or_after(e['time'], bars)
            if not start or not end:
                continue
            vals.append(calc_return(start[1], end[1]))
        result['pre'][str(w)] = stats(vals, args.cost_bps)

    for w in post_windows:
        vals = []
        for e in events:
            start = value_at_or_after(e['time'], bars)
            end = value_at_or_after(e['time'] + timedelta(minutes=w), bars)
            if not start or not end:
                continue
            vals.append(calc_return(start[1], end[1]))
        result['post'][str(w)] = stats(vals, args.cost_bps)

    out = Path(args.out)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print(f'Wrote: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
