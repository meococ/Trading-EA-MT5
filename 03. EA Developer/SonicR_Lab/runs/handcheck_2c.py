"""handcheck_2c.py - ROUND 2C: 5 fresh-path replayed trades on 2 basket
symbols, both harnesses (reviewer item 6).

Same independent replay as runs/handcheck.py (no sim.py import for the
replay core). Sample: 5 trades each on GBPUSD (F0_J) and EURJPY
(F2_NH_b) drawn from the H0 CSVs; each replayed on H0 and H1 and
compared to both CSV sets.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src.components import sessions as sess_mod
from src import runner
from src import sim as sim_mod            # ROLL table only

N = 5


def _roll(sym, ctm):
    (a, b), s = sim_mod.ROLL[sym]
    mod = (ctm % 86400) // 60
    inside = (mod >= a or mod < b) if a > b else a <= mod < b
    return s if inside else 0.0


def recompute(order, m1, sym, e1):
    mt, mo, mh, ml = m1["t"], m1["o"], m1["h"], m1["l"]
    msus = m1.get("suspect", np.zeros(len(mt), bool))
    step = 900
    start = int(np.searchsorted(mt, order["sig_ctm"] + step))
    end = int(np.searchsorted(mt, order["expiry_ctm"]))
    dr = order["dir"]; stop = order["entry_px"]
    fill_i = -1
    for i in range(start, end):
        if e1 and msus[i]:
            continue
        if (dr == 1 and mh[i] >= stop) or (dr == -1 and ml[i] <= stop):
            fill_i = i
            break
    if fill_i < 0:
        return None
    fill = max(stop, mo[fill_i]) if dr == 1 else min(stop, mo[fill_i])
    fill += dr * _roll(sym, int(mt[fill_i]))
    sl, tp = order["sl"], order["tp"]
    flat = sess_mod.friday_flatten_ctm(np.asarray([mt[fill_i]]))[0]
    last_i = int(np.searchsorted(mt, flat))
    if last_i <= fill_i:
        last_i = fill_i + 1
    scan_end = min(last_i, len(mt))
    prev_sus = False
    for i in range(fill_i, scan_end):
        if e1 and msus[i]:
            prev_sus = True
            continue
        sgn = _roll(sym, int(mt[i]))
        if dr == 1:
            if ml[i] <= sl:
                px = min(sl, mo[i]) if mo[i] < sl else sl
                return fill, px - sgn, mt[i], "sl"
            if mh[i] >= tp:
                px = tp if (prev_sus and mo[i] >= tp) else \
                    (max(tp, mo[i]) if mo[i] > tp else tp)
                return fill, px - sgn, mt[i], "tp"
        else:
            if mh[i] >= sl:
                px = max(sl, mo[i]) if mo[i] > sl else sl
                return fill, px + sgn, mt[i], "sl"
            if ml[i] <= tp:
                px = tp if (prev_sus and mo[i] <= tp) else \
                    (min(tp, mo[i]) if mo[i] < tp else tp)
                return fill, px + sgn, mt[i], "tp"
        prev_sus = False
    i = min(last_i, len(mt) - 1)
    while e1 and i < len(mt) - 1 and msus[i]:
        i += 1
    return fill, mo[i], mt[i], "flat"


def _load(sym, cfgid, tag):
    tr = pd.read_csv(f"out/trades_2c_{sym}_{cfgid}{tag}.csv")
    ords = pd.read_parquet(
        f"out/sigs/{sym}_{cfgid}_{dm.DESIGN[0]}.parquet")
    ctx = runner.get_ctx(sym, 15)
    ords["sig_ctm"] = ctx.tf["t"][ords["t"].to_numpy()]
    j = tr.merge(ords, on=["sig_ctm", "dir"], suffixes=("", "_o"))
    return j, ctx.m1


def main():
    total_mism = 0
    for sym, cfgid in (("GBPUSD", "F0_J"), ("EURJPY", "F2_NH_b")):
        j0, m1 = _load(sym, cfgid, "")
        jj = j0.sort_values("exit_ctm")
        step = max(1, len(jj) // N)
        keys = list(zip(jj["sig_ctm"].iloc[::step].head(N),
                        jj["dir"].iloc[::step].head(N)))
        for e1, tag, lab in ((False, "", "H0"), (True, "_e1", "H1")):
            j, _m = _load(sym, cfgid, tag)
            mism = 0
            for s_ctm, d in keys:
                rows = j[(j["sig_ctm"] == s_ctm) & (j["dir"] == d)]
                if len(rows) == 0:
                    print(f"{lab} {sym} sig={s_ctm}: no trade - skip")
                    continue
                row = rows.iloc[0]
                od = {"sig_ctm": int(s_ctm), "dir": int(d),
                      "entry_px": float(row["entry_o"]),
                      "sl": float(row["sl_o"]), "tp": float(row["tp_o"]),
                      "expiry_ctm": int(row["expiry_ctm"])}
                rec = recompute(od, m1, sym, e1)
                if rec is None:
                    print(f"{lab} {sym} sig={s_ctm}: no fill vs CSV "
                          "trade -> MISMATCH"); mism += 1; continue
                fill, exit_px, exit_ctm, reason = rec
                ok = (abs(fill - row["entry"]) < 1e-9
                      and abs(exit_px - row["exit"]) < 1e-9
                      and int(exit_ctm) == int(row["exit_ctm"])
                      and abs(row["pending_px"] - row["entry_o"]) < 1e-9
                      and (reason == row["reason"]
                           or (reason == "sl"
                               and row["reason"] == "sl_same")))
                if not ok:
                    mism += 1
                print(f"{lab} {sym} sig={s_ctm} dir={d}: fill "
                      f"{fill:.5f}/{row['entry']:.5f} exit "
                      f"{exit_px:.5f}/{row['exit']:.5f} {reason}/"
                      f"{row['reason']} -> {'OK' if ok else 'MISMATCH'}")
            print(f"== {lab} {sym} {cfgid}: {mism} mismatches")
            total_mism += mism
    print(f"TOTAL: {total_mism} mismatches")


if __name__ == "__main__":
    main()
