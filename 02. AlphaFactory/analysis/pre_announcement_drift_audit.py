#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-announcement drift audit (analysis-only).

Buckets trades by proximity to curated event times using the legacy
news-filter CSV schema: date,time_utc,event_type,currency,importance.
Designed to test standalone event-timing hypotheses, not to modify EA logic.
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
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d"):
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
                dt = parse_dt(f"{row['date']} {row['time_utc']}:00" if len(row['time_utc']) == 5 else f"{row['date']} {row['time_utc']}")
            except Exception:
                continue
            out.append({
                'time': dt,
                'event_type': row.get('event_type', ''),
                'currency': row.get('currency', ''),
                'importance': int(row.get('importance', '0') or 0),
            })
    return out


def read_trades(path: Path) -> List[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = row.get('entry_time') or row.get('timestamp') or row.get('time')
            if not ts:
                continue
            try:
                out.append({
                    'entry_time': parse_dt(ts),
                    'profit': float(row['profit']),
                })
            except Exception:
                continue
    return out


def stats(rows: List[dict]) -> dict:
    if not rows:
        return {'n': 0, 'net_profit': 0.0, 'profit_factor': 0.0, 'win_rate_pct': 0.0, 'expectancy': 0.0}
    profits = [r['profit'] for r in rows]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = gp / gl if gl > 0 else 999.99
    return {
        'n': len(rows),
        'net_profit': round(sum(profits), 2),
        'profit_factor': round(pf, 3),
        'win_rate_pct': round(100.0 * len(wins) / len(rows), 2),
        'expectancy': round(sum(profits) / len(rows), 2),
    }


def classify(trade_dt: datetime, events: List[dict], pre_windows: List[int], post_windows: List[int]) -> str:
    best = 'NONE'
    for e in events:
        delta_min = (trade_dt - e['time']).total_seconds() / 60.0
        for w in pre_windows:
            if -w <= delta_min < 0:
                return f'PRE_{w}M'
        for w in post_windows:
            if 0 <= delta_min <= w:
                return f'POST_{w}M'
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--trades', required=True)
    ap.add_argument('--events', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pre', default='30,60,90')
    ap.add_argument('--post', default='15,30')
    args = ap.parse_args()

    pre_windows = [int(x) for x in args.pre.split(',') if x.strip()]
    post_windows = [int(x) for x in args.post.split(',') if x.strip()]
    events = read_events(Path(args.events))
    trades = read_trades(Path(args.trades))

    buckets: Dict[str, List[dict]] = {'NONE': []}
    for w in pre_windows:
        buckets[f'PRE_{w}M'] = []
    for w in post_windows:
        buckets[f'POST_{w}M'] = []

    for t in trades:
        bucket = classify(t['entry_time'], events, pre_windows, post_windows)
        buckets[bucket].append(t)

    result = {
        'label': args.label,
        'pre_windows': pre_windows,
        'post_windows': post_windows,
        'buckets': {k: stats(v) for k, v in buckets.items()},
    }
    out = Path(args.out)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print(f'Wrote: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
