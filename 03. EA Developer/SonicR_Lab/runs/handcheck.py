"""handcheck.py - LEAD_NOTE_2 item (c) + reviewer item (f) + A1 redo.

Independently recompute sampled trades from raw M1 bars on BOTH harness
versions: H0 (E1b+E2+E3, suspect bars tradable) and H1 (H0 + E1 skip
rules). Fresh code path - not a re-import of sim.py.
Sample: 10 F0_J + 5 F2_NH_b signals drawn from the H0 trade CSV; each
signal is replayed under both rule-sets and compared to both CSVs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src.components import sessions as sess_mod
from src import runner

N_F0J = 10
N_F2 = 5

# E1b roll-spread windows (server minute-of-day) - mirrors sim.ROLL.
ROLL = {"EURUSD": ((1435, 15), 2.0 * 1e-4),
        "XAUUSD": ((55, 80), 20.0 * 0.1)}


def _roll(sym, ctm):
    (a, b), s = ROLL[sym]
    mod = (ctm % 86400) // 60
    inside = (mod >= a or mod < b) if a > b else a <= mod < b
    return s if inside else 0.0


def recompute(order, m1, sym, e1):
    """Fresh-path replay of one pending order on M1 bars.
    e1=True applies the Lead's E1 suspect-bar skip rules."""
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
    fill += dr * _roll(sym, int(mt[fill_i]))          # E1b: buy +S / sell -S
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
                px = min(sl, mo[i]) if mo[i] < sl else sl   # gap -> open
                return fill, px - sgn, mt[i], "sl"
            if mh[i] >= tp:
                px = tp if (prev_sus and mo[i] >= tp) else \
                    (max(tp, mo[i]) if mo[i] > tp else tp)  # no gap bonus
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
        i += 1                                    # flatten -> clean open
    return fill, mo[i], mt[i], "flat"


def _load(sym, cfgid, tag):
    tr = pd.read_csv(f"out/trades_{sym}_{cfgid}{tag}.csv")
    ords = pd.read_parquet(
        f"out/sigs/{sym}_{cfgid}_{dm.DESIGN[0]}.parquet")
    ctx = runner.get_ctx(sym, 15)
    ords["sig_ctm"] = ctx.tf["t"][ords["t"].to_numpy()]
    j = tr.merge(ords, on=["sig_ctm", "dir"], suffixes=("", "_o"))
    return j, ctx.m1


def sample_keys(j, n):
    jj = j.sort_values("exit_ctm")
    step = max(1, len(jj) // n)
    keys = list(zip(jj["sig_ctm"].iloc[::step].head(n),
                    jj["dir"].iloc[::step].head(n)))
    return keys


def check(j, m1, sym, keys, e1, label):
    mism = 0; checked = 0
    for s_ctm, d in keys:
        rows = j[(j["sig_ctm"] == s_ctm) & (j["dir"] == d)]
        if len(rows) == 0:
            print(f"{label} sig={s_ctm}: no {label} trade for signal - skip")
            continue
        row = rows.iloc[0]
        od = {"sig_ctm": int(s_ctm), "dir": int(d),
              "entry_px": float(row["entry_o"]), "sl": float(row["sl_o"]),
              "tp": float(row["tp_o"]), "expiry_ctm": int(row["expiry_ctm"])}
        rec = recompute(od, m1, sym, e1)
        checked += 1
        if rec is None:
            print(f"{label} sig={s_ctm}: order never filled but CSV has "
                  f"a trade -> MISMATCH"); mism += 1; continue
        fill, exit_px, exit_ctm, reason = rec
        ok = (abs(fill - row["entry"]) < 1e-9
              and abs(exit_px - row["exit"]) < 1e-9
              and int(exit_ctm) == int(row["exit_ctm"])
              and abs(row["pending_px"] - row["entry_o"]) < 1e-9
              and (reason == row["reason"]
                   or (reason == "sl" and row["reason"] == "sl_same")))
        flag = "OK" if ok else "MISMATCH"
        if not ok:
            mism += 1
        print(f"{label} sig={s_ctm} dir={d}: fill {fill:.5f} vs "
              f"{row['entry']:.5f} | exit {exit_px:.5f} vs {row['exit']:.5f}"
              f" | {reason} vs {row['reason']} -> {flag}")
    print(f"== {label}: {mism} mismatches over {checked} checked")
    return mism


def main():
    for sym, cfgid, n in (("EURUSD", "F0_J", N_F0J),
                          ("EURUSD", "F2_NH_b", N_F2)):
        j0, m1 = _load(sym, cfgid, "")
        keys = sample_keys(j0, n)
        check(j0, m1, sym, keys, e1=False, label=f"H0 {sym} {cfgid}")
        j1, _ = _load(sym, cfgid, "_e1")
        check(j1, m1, sym, keys, e1=True, label=f"H1 {sym} {cfgid}")


if __name__ == "__main__":
    main()
