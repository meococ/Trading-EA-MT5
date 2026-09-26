"""Tick momentum / mean-reversion probe, parametrized by symbol.

Law under test: sub-minute to 15-min tick moves are spread-cost
dominated (XAU -$6, BTC -$56 all scales). On tight-spread FX
(EURUSD/USDJPY ~0.2-0.5p RT) the same tests may net positive.

Events: mid move over trailing window W >= th pips -> enter at next
tick, hold H, exit. Direction: momentum (with move) or reversion
(against). Dedup via cooldown = H after each event. Cost embedded in
entry at hi/lo (real quoted spread) + exit at opposite side.
"""
import os
import sys
import glob
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_plane as tp

PIP = {"AUDUSD": 1e-4, "XAUUSD": 0.1, "EURUSD": 1e-4, "USDJPY": 1e-2,
       "GBPUSD": 1e-4, "BTCUSD": 1.0}


def probe(sym, w_ms, h_ms, th_pip, mode, cooldown_ms=None):
    files = sorted(glob.glob(os.path.join(
        tp.ROOT, sym, "decoded", "*", "*", "*.afdticks")))
    pip = PIP.get(sym, 1e-4)
    cd = h_ms if cooldown_ms is None else cooldown_ms
    pnls = []
    days = []
    for p in files:
        d = datetime.strptime(os.path.basename(p)[:10], "%Y-%m-%d").date()
        r = tp.load_day(sym, d)
        if r is None or len(r) < 200:
            continue
        lo = np.minimum(r["ask"], r["bid"]); hi = np.maximum(r["ask"], r["bid"])
        mid = (lo + hi) * 0.5
        ms = r["ms"]
        next_ok = ms[0]
        i = 0
        n = len(r)
        while i < n:
            if ms[i] < next_ok:
                i += 1
                continue
            # find tick at ms[i]-w_ms
            j = np.searchsorted(ms, ms[i] - w_ms)
            if j >= i:
                i += 1
                continue
            move = (mid[i] - mid[j]) / pip
            if abs(move) < th_pip:
                i += 1
                continue
            side = (1 if move > 0 else -1) * (1 if mode == "mom" else -1)
            ent = hi[i] if side > 0 else lo[i]
            xi = np.searchsorted(ms, ms[i] + h_ms)
            if xi >= n:
                break
            ext = lo[xi] if side > 0 else hi[xi]
            pnls.append((ext - ent) / pip * side)
            days.append(str(d))
            next_ok = ms[i] + cd
            i = xi
    v = np.array(pnls)
    if len(v) < 20:
        return None
    w = v[v > 0]; l = v[v <= 0]
    pf = w.sum() / abs(l.sum()) if l.sum() else np.inf
    span = len(set(days))
    per_wk = len(v) / max(span / 5.0, 1)
    return {"n": len(v), "mean": v.mean(), "pf": pf, "wr": (v > 0).mean(),
            "days": span, "per_wk": per_wk}


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    print(f"== {sym} tick momentum vs reversion (net of real spread) ==")
    for w_s in (30, 60, 300):
        for h_s in (60, 300, 900):
            for th in (0.5, 1.0, 2.0, 4.0):
                for mode in ("mom", "rev"):
                    r = probe(sym, w_s * 1000, h_s * 1000, th, mode)
                    if r:
                        print(f"  W={w_s:4d}s H={h_s:4d}s th={th:4.1f}p {mode} "
                              f"n={r['n']:5d} mean={r['mean']:+7.2f}p "
                              f"PF={r['pf']:5.2f} {r['per_wk']:5.1f}/wk")
