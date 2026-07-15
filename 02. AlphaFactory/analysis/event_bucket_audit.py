#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor-only event bucket audit.

Buckets trades into PRE_EVENT / EVENT_WEEK / POST_EVENT windows using a
manually curated event-date CSV. Intended for seasonal/calendar research,
not production gating.
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
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
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
                event_dt = parse_dt(row["event_date"])
            except Exception:
                continue
            out.append({
                "event_date": event_dt,
                "event_name": row.get("event_name", ""),
                "event_type": row.get("event_type", ""),
                "importance": row.get("importance", ""),
                "notes": row.get("notes", ""),
            })
    return out


def read_trades(path: Path) -> List[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                exit_dt = parse_dt(row.get("exit_time") or row.get("timestamp") or row.get("time"))
                profit = float(row["profit"])
            except Exception:
                continue
            out.append({"exit_dt": exit_dt, "profit": profit})
    return out


def classify(trade_dt: datetime, events: List[dict], pre_days: int, post_days: int) -> str:
    for e in events:
        d0 = e["event_date"].date()
        td = trade_dt.date()
        if d0 - timedelta(days=pre_days) <= td < d0:
            return "PRE_EVENT"
        if td == d0 or (d0 < td <= d0 + timedelta(days=post_days)):
            return "POST_EVENT" if td > d0 else "EVENT_WEEK"
    return "NONE"


def stats(rows: List[dict]) -> dict:
    if not rows:
        return {"n": 0, "net_profit": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "expectancy": 0.0}
    profits = [r["profit"] for r in rows]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = gp / gl if gl > 0 else 999.99
    return {
        "n": len(rows),
        "net_profit": round(sum(profits), 2),
        "profit_factor": round(pf, 3),
        "win_rate_pct": round(100.0 * len(wins) / len(rows), 2),
        "expectancy": round(sum(profits) / len(rows), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pre-days", type=int, default=2)
    ap.add_argument("--post-days", type=int, default=2)
    args = ap.parse_args()

    events = read_events(Path(args.events))
    trades = read_trades(Path(args.trades))
    buckets: Dict[str, List[dict]] = {"PRE_EVENT": [], "EVENT_WEEK": [], "POST_EVENT": [], "NONE": []}
    for t in trades:
        bucket = classify(t["exit_dt"], events, args.pre_days, args.post_days)
        buckets[bucket].append(t)

    result = {
        "label": args.label,
        "pre_days": args.pre_days,
        "post_days": args.post_days,
        "buckets": {k: stats(v) for k, v in buckets.items()},
    }
    out = Path(args.out)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
