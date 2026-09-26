"""e0_scan.py - A3F STEP 1b: compute E0 flags for all 12 symbols,
COMMON_START..VALIDATION_END only (holdout sealed). Writes:
  out/e0_flags_<sym>.npz  (flag + info)
  E0_BARS.md              (every flagged bar, counts, named events,
                           near-misses where (b) failed across a gap)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from src import data as dm
from src import e0
from src import sim as sm

NAMED = [("SNB", "USDCHF", "2015-01-15"),
         ("GBP flash", "GBPUSD", "2016-10-07"),
         ("JPY flash", "USDJPY", "2019-01-03"),
         ("gold crash", "XAUUSD", "2013-04-15"),
         ("gold Mar2020", "XAUUSD", "2020-03-16"),
         ("gold flash", "XAUUSD", "2021-08-09")]


def _fmt(t):
    import datetime as dt
    return dt.datetime.utcfromtimestamp(int(t)).strftime("%Y-%m-%d %H:%M:%S")


def _day(ts_str):
    import datetime as dt
    return int(dt.datetime.strptime(ts_str, "%Y-%m-%d")
               .replace(tzinfo=dt.timezone.utc).timestamp())


def main():
    t00 = time.time()
    lo, hi = dm.COMMON_START, dm.VALIDATION_END
    lines = ["# E0_BARS - impossible prints flagged by E0",
             "",
             "Rule (LEAD_NOTE_5, frozen): |h or l vs last good close| > 3%",
             "AND close 15min later within 0.5% of ref. Both harnesses.",
             ""]
    all_info = []
    counts = []
    for sym in dm.ALL_SYMBOLS:
        m1 = dm.load_m1(sym, lo, hi)
        flag, info = e0.e0_flags(m1)
        np.savez_compressed(f"out/e0_flags_{sym}.npz",
                            flag=flag, t=m1["t"])
        t = m1["t"]
        des = int(flag[t <= dm.DESIGN_END].sum())
        val = int(flag[(t > dm.DESIGN_END) & (t <= dm.VALIDATION_END)]
                  .sum())
        counts.append({"sym": sym, "n_flag": int(flag.sum()),
                       "design": des, "validation": val})
        print(f"[e0] {sym}: {flag.sum()} flagged (D={des} V={val})",
              flush=True)
        if flag.sum() > 20:
            print(f"[e0] {sym} >20 flags - STOP per backup plan",
                  flush=True)
        # inside vs outside rollover windows
        mod = (t % 86400) // 60
        roll_start = sm.ROLL[sym][0][0]; roll_end = sm.ROLL[sym][0][1]
        in_roll = (mod >= roll_start) | (mod < roll_end) \
            if roll_end < roll_start else (mod >= roll_start) & \
            (mod < roll_end)
        for it in info:
            it["sym"] = sym
            it["in_roll"] = bool(in_roll[it["i"]])
            it["window"] = ("DESIGN" if it["t"] <= dm.DESIGN_END
                            else "VALIDATION")
            it["suspect"] = bool(m1["suspect"][it["i"]])
            i = it["i"]
            it["o"] = float(m1["o"][i]); it["h"] = float(m1["h"][i])
            it["l"] = float(m1["l"][i]); it["c"] = float(m1["c"][i])
            all_info.append(it)
        # named events: any flag in that symbol's day?
        for name, esym, day in NAMED:
            if esym != sym:
                continue
            d0 = _day(day); d1 = d0 + 86400
            nf = int(flag[(t >= d0) & (t < d1)].sum())
            # widest dev that day for context
            sel = (t >= d0) & (t < d1)
            print(f"[e0 event] {name} {sym} {day}: flagged={nf}",
                  flush=True)
        # near-misses where (b) failed across a gap (lag >> 900)
        nm = [it for it in info if not it["flagged"]
              and it["revert_lag_s"] > 3600]
        for it in nm:
            print(f"[e0 gap-miss] {sym} {_fmt(it['t'])} dev={it['dev']:.1%} "
                  f"revert_lag={it['revert_lag_s']/3600:.1f}h", flush=True)
    inf = pd.DataFrame(all_info)
    inf.to_csv("out/e0_bars.csv", index=False)
    pd.DataFrame(counts).to_csv("out/e0_counts.csv", index=False)
    print(inf[inf.flagged].to_string(index=False), flush=True)
    print(f"[e0] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
