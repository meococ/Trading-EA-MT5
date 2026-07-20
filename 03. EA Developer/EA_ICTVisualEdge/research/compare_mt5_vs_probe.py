#!/usr/bin/env python3
"""Compare the real-tick MT5 tester result against the offline probe.

MT5 side: parse common/ictvis_deals.csv (per-deal money P&L incl. commission+swap
at real spread). Offline side: the DESIGN candidates restricted to 2016-2018.
The EA is one-position-at-a-time so trade COUNT differs from the probe's
independent-candidate universe; the cross-check is on DIRECTION + economics
(is the real-tick object net-negative as the probe predicted, and what is the
real cost per trade vs the 1.5-pip proxy).
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd, numpy as np

CSV = Path(r"C:/Users/ADMIN/AppData/Roaming/MetaQuotes/Terminal/Common/Files/ictvis_deals.csv")
HERE = Path(__file__).resolve().parent
S1 = HERE / "evidence" / "stage1"


def mt5_side() -> dict:
    d = pd.read_csv(CSV)
    d.columns = [c.strip() for c in d.columns]
    out = d[d["entry_exit"] == 1].copy()          # DEAL_ENTRY_OUT = closed trades
    out["net"] = out["profit"] + out["commission"] + out["swap"]
    out["dt"] = pd.to_datetime(out["deal_time"], unit="s")
    pos = out.loc[out.net > 0, "net"].sum(); neg = -out.loc[out.net < 0, "net"].sum()
    pf = pos / neg if neg > 0 else float("inf")
    by_year = out.groupby(out["dt"].dt.year)["net"].agg(["count", "sum"]).round(2)
    # cost per trade: commission+swap plus spread already inside profit; report gross fees
    fees = (out["commission"].abs() + out["swap"].abs()).sum()
    return {"n_trades": int(len(out)), "net_money": round(float(out.net.sum()), 2),
            "pf": round(float(pf), 3), "win_rate": round(float((out.net > 0).mean()), 4),
            "total_fees_money": round(float(fees), 2),
            "by_year": by_year.to_dict("index")}


def probe_side() -> dict:
    d = pd.read_parquet(S1 / "candidates_M5_features.parquet")
    d["dt"] = pd.to_datetime(d["entry_time_utc"])
    sub = d[(d["dt"] >= "2016-01-01") & (d["dt"] < "2019-01-01")].copy()
    sub["cost_r"] = 1.5 / sub["risk_pip"]; sub["r_net"] = sub["r_gross"] - sub["cost_r"]
    posN = sub.loc[sub.r_net > 0, "r_net"].sum(); negN = -sub.loc[sub.r_net < 0, "r_net"].sum()
    posG = sub.loc[sub.r_gross > 0, "r_gross"].sum(); negG = -sub.loc[sub.r_gross < 0, "r_gross"].sum()
    return {"n_candidates": int(len(sub)),
            "pf_gross_zerocost": round(float(posG / negG), 3),
            "pf_net_1p5pip": round(float(posN / negN), 3),
            "mean_r_gross": round(float(sub.r_gross.mean()), 4),
            "mean_r_net": round(float(sub.r_net.mean()), 4),
            "win_gross": round(float(sub.win.mean()), 4)}


def main() -> int:
    res = {"window": "2016-2018 EURUSD M5",
           "mt5_real_tick": mt5_side(), "offline_probe": probe_side()}
    (S1 / "mt5_vs_probe_2016_2018.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
