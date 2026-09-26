"""handcheck_2d.py - ROUND 2D: fresh-path replay of managed exits.

Independent verifier (does NOT call src.exits): for sampled managed
trades it scans the raw M1 path and recomputes what the rule dictates,
then compares exit_i / exit_px / reason / part fields to the CSV row.
Sample: >=1 'be', >=1 leg-A partial, >=1 'dragon', >=1 daily flat, on
both harnesses (H0 + H1), D symbols only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import managed as mg
from src import sim as sm
from src.components import indicators as ind
from src import data as dm

D_SET = ["AUDUSD", "USDCHF", "GBPJPY", "USDJPY", "GBPUSD",
         "EURUSD", "XAUUSD"]
EPS = 1e-9


def _v_exit(m1, sym, dr, fill_i, fill, sl, tp, rule, skip, flat23):
    """Independent re-derivation of the managed exit (audit code)."""
    mt, mo, mh, ml = m1["t"], m1["o"], m1["h"], m1["l"]
    sus = m1["suspect"]
    R0 = abs(fill - sl); trig = fill + dr * R0
    be = fill + dr * sm.round_trip_cost(sym)
    n = len(mt)
    mod = (mt % 86400) // 60
    # flatten boundary
    fctm = sm.sess_mod.friday_flatten_ctm(np.asarray([mt[fill_i]]))[0] \
        if hasattr(sm, "sess_mod") else None
    from src.components import sessions as sess
    fctm = sess.friday_flatten_ctm(np.asarray([mt[fill_i]]))[0]
    if flat23:
        day0 = mt[fill_i] - mod[fill_i] * 60
        d = day0 + 1430 * 60
        if mt[fill_i] >= d:
            d += 86400
        fctm = min(fctm, d)
    end = int(np.searchsorted(mt, fctm))
    end = min(end, n)
    # dragon precompute (fresh resample + EMA, not the engine's arrays)
    tf = dm.resample(m1, 15)
    e34h, _c, e34l = ind.dragon(tf)
    trig_i = -1; part_i = -1; part_px = np.nan; sl_eff = sl
    i = fill_i
    while i < end:
        if skip and sus[i]:
            i += 1
            continue
        sgn = sm._roll_px(sym) if sm._in_roll(sym, int(mt[i])) else 0.0
        # dragon: did a CLOSED M15 bar after trig cross the band?
        if rule in ("X3", "X4") and trig_i >= 0:
            t_trig = mt[trig_i]
            j = 0
            while j < len(tf["t"]) and tf["t"][j] + 900 <= t_trig:
                j += 1
            dragon_at = -1
            while j < len(tf["t"]):
                lastm = int(tf["m1_hi"][j]) - 1
                if skip and sus[lastm]:
                    j += 1
                    continue
                band = e34l[j] if dr == 1 else e34h[j]
                if (dr == 1 and tf["c"][j] < band) or \
                   (dr == -1 and tf["c"][j] > band):
                    k = int(np.searchsorted(mt, tf["t"][j] + 900))
                    if skip:
                        while k < n and sus[k]:
                            k += 1
                    dragon_at = k
                    break
                j += 1
            if 0 <= dragon_at == i:
                return {"exit_i": i, "exit_px": mo[i], "reason": "dragon",
                        "part_i": part_i, "part_px": part_px}
        tp_hit = rule != "X4" and \
            ((mh[i] >= tp) if dr == 1 else (ml[i] <= tp))
        sl_hit = (ml[i] <= sl_eff) if dr == 1 else (mh[i] >= sl_eff)
        if sl_hit:
            px = (min(sl_eff, mo[i]) if dr == 1 else max(sl_eff, mo[i]))
            px += -sgn if dr == 1 else sgn
            rs = "be" if sl_eff != sl else \
                ("sl_same" if i == fill_i and tp_hit else "sl")
            return {"exit_i": i, "exit_px": px, "reason": rs,
                    "part_i": part_i, "part_px": part_px}
        if rule == "X2" and part_i < 0 and \
                ((mh[i] >= trig) if dr == 1 else (ml[i] <= trig)):
            part_i = i
            part_px = trig + (-sgn if dr == 1 else sgn)
        if tp_hit:
            px = tp + (-sgn if dr == 1 else sgn)
            return {"exit_i": i, "exit_px": px, "reason": "tp",
                    "part_i": part_i, "part_px": part_px}
        if trig_i < 0 and \
                ((mh[i] >= trig) if dr == 1 else (ml[i] <= trig)):
            trig_i = i
            if rule in ("X1", "X3", "X4"):
                sl_eff = be
        if rule == "X2" and part_i == i and sl_eff == sl:
            sl_eff = be
        i += 1
    j = min(end, n - 1)
    while j < n - 1 and skip and sus[j]:
        j += 1
    return {"exit_i": j, "exit_px": mo[j],
            "reason": "flat" if end < n else "window_end",
            "part_i": part_i, "part_px": part_px}


def check_one(sym, cfg, rowidx, e1):
    tag = "_e1" if e1 else ""
    tr = pd.read_csv(f"out/trades_2d_{sym}_{cfg}{tag}.csv")
    row = tr.iloc[rowidx]
    lc = mg.light_ctx(sym)
    m1 = lc["m1"]; mt = m1["t"]
    fill_i = int(np.searchsorted(mt, int(row["fill_ctm"])))
    rule, hold = cfg.split("-")
    got = _v_exit(m1, sym, int(row["dir"]), fill_i, float(row["entry"]),
                  float(row["sl"]), float(row["tp"]), rule, skip=e1,
                  flat23=(hold == "DF"))
    ok = bool(got["exit_i"] == int(np.searchsorted(mt, int(row["exit_ctm"])))
              and abs(got["exit_px"] - row["exit"]) < EPS
              and got["reason"] == row["reason"])
    if rule == "X2" and row["part_ctm"]:
        ok = ok and bool(int(got["part_i"]) == int(
            np.searchsorted(mt, int(row["part_ctm"]))) and
            abs(got["part_px"] - row["part_px"]) < EPS)
    return ok, row["reason"], got["reason"]


def main():
    cases = []
    # pick samples: one be, one legA partial, one dragon, one DF flat,
    # one sl - across D symbols, on the harness where they exist
    wants = [("X1-HOLD", "be"), ("X2-HOLD", "tp"), ("X3-HOLD", "dragon"),
             ("X0-DF", "flat"), ("X1-DF", "be"), ("X3-DF", "flat"),
             ("X4-HOLD", "dragon"), ("X1-HOLD", "sl")]
    for e1 in (False, True):
        tag = "_e1" if e1 else ""
        for cfg, reason in wants:
            found = False
            for sym in D_SET:
                f = f"out/trades_2d_{sym}_{cfg}{tag}.csv"
                if not os.path.exists(f):
                    continue
                tr = pd.read_csv(f)
                idx = tr.index[tr["reason"] == reason]
                if len(idx) == 0:
                    continue
                ok, want, got = check_one(sym, cfg, int(idx[0]), e1)
                cases.append((cfg, sym, reason, "H1" if e1 else "H0",
                              want, got, ok))
                found = True
                break
            if not found:
                cases.append((cfg, "-", reason, "H1" if e1 else "H0",
                              "-", "-", "NO SAMPLE"))
    bad = [c for c in cases if c[-1] is not True]
    for c in cases:
        print(c, flush=True)
    print(f"handcheck_2d: {len(cases) - len(bad)}/{len(cases)} OK",
          flush=True)


if __name__ == "__main__":
    main()
