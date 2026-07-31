#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lifecycle = next((args.run / "analysis" / "logs").glob("*_LifecycleTrades_*.csv"))
    rows = list(csv.DictReader(lifecycle.open(encoding="utf-8-sig", newline="")))
    positions = defaultdict(list)
    for row in rows:
        positions[row["position_id"]].append(row)
    trades = []
    for position_id, events in positions.items():
        entry = next(row for row in events if row["action"] == "OPEN")
        close = next(row for row in events if row["is_final_close"] == "1")
        direction = 1 if entry["order_type"] == "BUY" else -1
        entry_price = float(entry["price"])
        distance = float(entry["risk_pts"]) * 0.00001
        net = sum(float(row["deal_net"]) for row in events)
        trades.append({
            "position_id": position_id,
            "entry_time": entry["event_time"],
            "exit_time": close["event_time"],
            "direction": direction,
            "entry": entry_price,
            "sl": entry_price - direction * distance,
            "tp": entry_price + direction * distance * 1.5,
            "exit": float(close["price"]),
            "net": net,
        })
    winners = sorted((trade for trade in trades if trade["net"] > 0), key=lambda row: row["net"])
    losers = sorted((trade for trade in trades if trade["net"] <= 0), key=lambda row: row["net"])
    selected = [
        (winners[len(winners) // 2], "WIN", "winner_median"),
        (winners[-1], "WIN", "winner_tail"),
        (losers[len(losers) // 2], "LOSS", "loser_median"),
        (losers[0], "LOSS", "loser_tail_weekend_gap"),
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["case_id", "entry_time_utc", "direction", "entry", "sl", "tp",
              "exit_time_utc", "exit", "reason", "label"]
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, (trade, reason, label) in enumerate(selected, 1):
            writer.writerow({
                "case_id": f"VRAS-008-D{index:02d}-P{trade['position_id']}",
                "entry_time_utc": trade["entry_time"],
                "direction": trade["direction"],
                "entry": trade["entry"],
                "sl": trade["sl"],
                "tp": trade["tp"],
                "exit_time_utc": trade["exit_time"],
                "exit": trade["exit"],
                "reason": reason,
                "label": label,
            })
    print(f"HYP008_CASEBOOK_SELECTED cases={len(selected)} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
