"""census_2g.py - 2G STEP 3b: HOLDOUT census before any signal or P/L.

Per symbol: M1 bars, weeks with data, weekday gaps > 60 min, duplicate
timestamps, E0' (second-stamped) bars, minute-aligned bars > 20% off
previous close, bars with range > 10x that day's median M1 range.
Count and list only - nothing is voided by the census.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import e0

SYMS = ["EURUSD", "XAUUSD"]


def run_census(sym, m1):
    t = m1["t"]
    rows = {"sym": sym, "m1_bars": len(t),
            "t_min": int(t.min()), "t_max": int(t.max())}
    lo, hi = dm.VALIDATION_END, dm.COMMON_END
    rows["weeks_span"] = int((hi - lo) // (7 * 86400))
    wk = np.unique((t - lo) // (7 * 86400))
    rows["weeks_with_data"] = len(wk)
    rows["coverage"] = len(wk) / rows["weeks_span"]
    # weekday gaps > 60 min inside Mon-Fri
    dt_ = np.diff(t)
    dow = ((t[:-1] // 86400) + 3) % 7   # epoch day0=Thu -> Mon=4..Fri=1?
    # simpler: convert to weekday via datetime
    wd = pd.to_datetime(pd.Series(t[:-1]), unit="s").dt.dayofweek
    weekday_gap = (dt_ > 3600) & (wd < 5)
    # exclude gaps crossing the daily break (23:55-00:00) - those are
    # normal session breaks; flag only >60min anyway, they qualify
    rows["weekday_gaps_gt60m"] = int(weekday_gap.sum())
    gap_list = [(int(t[:-1][weekday_gap][i]), int(dt_[weekday_gap][i]))
                for i in range(int(weekday_gap.sum()))]
    rows["dup_ts"] = int(len(t) - len(np.unique(t)))
    ss = e0.second_stamp(m1)
    rows["e0s_bars"] = int(ss.sum())
    # minute-aligned bars >20% off previous normal close
    prev_c = np.concatenate([[np.nan], m1["c"][:-1]])
    dev = np.maximum(np.abs(m1["h"] / prev_c - 1),
                     np.abs(m1["l"] / prev_c - 1))
    big = (~ss) & (dev > 0.20)
    rows["gt20pct_bars"] = int(big.sum())
    big_list = [(int(t[i]), float(m1["o"][i]), float(m1["h"][i]),
                 float(m1["l"][i]), float(m1["c"][i]), float(prev_c[i]),
                 float(dev[i])) for i in np.nonzero(big)[0]]
    # range > 10x that day's median M1 range
    day = t // 86400
    rng = m1["h"] - m1["l"]
    med = pd.Series(rng).groupby(day).transform("median")
    fat = (rng > 10 * med) & (med > 0)
    rows["range10x_bars"] = int(fat.sum())
    fat_list = [(int(t[i]), float(rng[i]), float(med[i]))
                for i in np.nonzero(fat)[0]]
    return rows, {"e0s": [int(t[i]) for i in np.nonzero(ss)[0]],
                  "gaps": gap_list, "gt20pct": big_list,
                  "range10x": fat_list}


def main():
    dm.open_holdout(SYMS)
    lo, hi = dm.HOLDOUT
    out = []
    details = {}
    for sym in SYMS:
        m1 = dm.load_m1(sym, lo, hi, allow_holdout=True)
        r, d = run_census(sym, m1)
        out.append(r)
        details[sym] = d
        print(f"[census] {sym}: bars={r['m1_bars']} "
              f"wk={r['weeks_with_data']}/{r['weeks_span']} "
              f"gaps>60m={r['weekday_gaps_gt60m']} dup={r['dup_ts']} "
              f"e0s={r['e0s_bars']} >20%={r['gt20pct_bars']} "
              f"r10x={r['range10x_bars']}", flush=True)
    pd.DataFrame(out).to_csv("out/census_2g.csv", index=False)
    import json
    with open("out/census_2g_detail.json", "w") as f:
        json.dump(details, f)


if __name__ == "__main__":
    main()
