#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review hypothetical regime-gating candidates from external market-state trade labels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Callable, Dict, List


def read_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def stats(rows: List[dict]) -> dict:
    profits = [float(r["profit"]) for r in rows]
    if not profits:
        return {"n": 0, "net_profit": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "expectancy": 0.0}
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


def review(label: str, rows: List[dict]) -> dict:
    def eq(key: str, value: str) -> Callable[[dict], bool]:
        return lambda r: r[key] == value

    def neq_pair(vol: str, trend: str) -> Callable[[dict], bool]:
        return lambda r: not (r["vol_bucket"] == vol and r["trend_bucket"] == trend)

    rules: Dict[str, Callable[[dict], bool]] = {
        "ALL_TRADES": lambda r: True,
        "HIGH_VOL_ONLY": eq("vol_bucket", "HIGH_VOL"),
        "EXCLUDE_LOW_VOL": lambda r: r["vol_bucket"] != "LOW_VOL",
        "UPTREND_ONLY": eq("trend_bucket", "UPTREND"),
        "DOWNTREND_ONLY": eq("trend_bucket", "DOWNTREND"),
        "HIGH_VOL_UPTREND_ONLY": lambda r: r["vol_bucket"] == "HIGH_VOL" and r["trend_bucket"] == "UPTREND",
        "HIGH_VOL_DOWNTREND_ONLY": lambda r: r["vol_bucket"] == "HIGH_VOL" and r["trend_bucket"] == "DOWNTREND",
        "EXCLUDE_MIDVOL_DOWNTREND": neq_pair("MID_VOL", "DOWNTREND"),
        "EXCLUDE_MIDVOL_UPTREND": neq_pair("MID_VOL", "UPTREND"),
    }
    return {
        "label": label,
        "rules": {name: stats([r for r in rows if pred(r)]) for name, pred in rules.items()}
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = read_rows(Path(args.trades))
    result = review(args.label, rows)
    out = Path(args.out)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
