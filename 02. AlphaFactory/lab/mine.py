"""Mining orchestrator: run systematic cell sweeps into lab.duckdb.

Families encode mechanism CLASSES, not one-off probes. Each cell = a fully
specified mechanism instance (event + side + exit spec). Thousands of cells
per run; every cell (incl. negatives) is stored — the falsification ledger.
"""
import sys
import time

import numpy as np

import data_plane
import features
import labels
import sweep


def _cost(df):
    """Per-event recorded-spread RT cost (GATE B: flat 1.0p proxy
    understated boundary windows ~2x and fabricated the surviving
    cells). Returns the cost array; the caller feeds eval cost_arr=
    and records the realized mean for provenance."""
    return labels.spread_cost_arr(df)


def _mean_cost(cost, mask):
    m = mask[:-1]
    return float(np.mean(cost[1:][m])) if m.any() else np.nan


def grid_impulse_cont(sym, lab):
    """With-trend continuation: k-bar impulse >= theta -> enter same direction
    at next-bar open. Priority class (fills favorable for continuation)."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    ev = labels.Evaluator(df, pip)
    cost = _cost(df)
    cells = 0
    for k in (5, 15, 30, 60):
        r_k = features.ret_k(df, k) / pip
        for th in (3, 5, 8, 12):
            for dirn in (1, -1):
                mask = _cooldown(((r_k * dirn) >= th).fillna(False).to_numpy(),
                                 k)
                nev = int(mask.sum())
                if nev < 60:
                    continue
                for sl in (8, 12, 16, 24):
                    for tp in (0, 8, 16, 24):
                        for hold in (30, 60, 120):
                            cell = {"family": "impulse_cont", "symbol": sym,
                                    "side": dirn, "k": k, "theta": th,
                                    "sl": sl, "tp": tp, "hold": hold}
                            if lab.done(cell):
                                continue
                            lab.record(cell, ev.eval(
                                mask, dirn, sl, tp, hold, cost_arr=cost),
                                _mean_cost(cost, mask))
                            cells += 1
    return cells


def grid_breakout_cont(sym, lab):
    """Continuation via prior-k extreme breakout, with-trend only."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    ev = labels.Evaluator(df, pip)
    cost = _cost(df)
    cells = 0
    for k in (30, 60, 120):
        for dirn in (1, -1):
            mask = features.breakout_mask(df, k, dirn, pip, 0.5)
            # thin clusters: require 5-bar cooldown between events
            mask = _cooldown(mask, 5)
            if mask.sum() < 60:
                continue
            for sl in (10, 16, 24):
                for tp in (0, 12, 24):
                    for hold in (60, 120, 240):
                        cell = {"family": "breakout_cont", "symbol": sym,
                                "side": dirn, "k": k, "sl": sl, "tp": tp,
                                "hold": hold}
                        if lab.done(cell):
                            continue
                        lab.record(cell, ev.eval(
                            mask, dirn, sl, tp, hold, cost_arr=cost),
                            _mean_cost(cost, mask))
                        cells += 1
    return cells


def grid_pullback_cont(sym, lab):
    """Pullback continuation: strong leg, shallow counter-move, re-enter with
    trend."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    ev = labels.Evaluator(df, pip)
    cost = _cost(df)
    cells = 0
    for kt in (15, 30, 60):
        for kp in (5, 10):
            d = features.pullback_mask(df, kt, kp, pip, min_trend=3.0)
            for dirn in (1, -1):
                mask = _cooldown((d == dirn).to_numpy(), 10)
                if mask.sum() < 60:
                    continue
                for sl in (10, 16, 24):
                    for tp in (0, 12, 24):
                        for hold in (60, 120):
                            cell = {"family": "pullback_cont", "symbol": sym,
                                    "side": dirn, "kt": kt, "kp": kp,
                                    "sl": sl, "tp": tp, "hold": hold}
                            if lab.done(cell):
                                continue
                            lab.record(cell, ev.eval(
                                mask, dirn, sl, tp, hold, cost_arr=cost),
                                _mean_cost(cost, mask))
                            cells += 1
    return cells


def grid_drift_hour(sym, lab):
    """Unconditional drift: enter every day at hour h, exit per spec.
    The only class whose measured magnitudes (+2-3.6p/hr) clear the cost
    floor. Suspect-window events drop automatically via path checks."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    ev = labels.Evaluator(df, pip)
    cost = _cost(df)
    cells = 0
    mod = df["mod"].to_numpy()
    for hr in range(24):
        evmask = mod == (hr * 60)   # first M1 bar of hour h each day
        if evmask.sum() < 60:
            continue
        for dirn in (1, -1):
            for sl in (12, 20, 30):
                for tp in (0, 12, 20, 30):
                    for hold in (30, 60, 120, 240):
                        cell = {"family": "drift_hour", "symbol": sym,
                                "side": dirn, "hour": hr, "sl": sl,
                                "tp": tp, "hold": hold}
                        if lab.done(cell):
                            continue
                        lab.record(cell, ev.eval(
                            evmask, dirn, sl, tp, hold, cost_arr=cost),
                            _mean_cost(cost, evmask))
                        cells += 1
    return cells


def grid_drift_mow(sym, lab):
    """Finer drift cells: hour x weekday entries on session hours only.
    Minimal exit grid — screening granularity, winners get refined later."""
    df = data_plane.load(sym)
    pip = data_plane.pip_size(sym)
    ev = labels.Evaluator(df, pip)
    cost = _cost(df)
    cells = 0
    mod = df["mod"].to_numpy()
    dow = df["dow"].to_numpy()
    for hr in list(range(0, 3)) + list(range(7, 16)):
        for d in range(5):
            evmask = (mod == hr * 60) & (dow == d)
            if evmask.sum() < 60:
                continue
            for dirn in (1, -1):
                for hold in (60, 240):
                    cell = {"family": "drift_mow", "symbol": sym,
                            "side": dirn, "hour": hr, "dow": d, "sl": 20,
                            "tp": 0, "hold": hold}
                    if lab.done(cell):
                        continue
                    lab.record(cell, ev.eval(
                        evmask, dirn, 20, 0, hold, cost_arr=cost),
                        _mean_cost(cost, evmask))
                    cells += 1
    return cells


def _cooldown(mask, gap):
    """Keep only events >= gap bars after the previous kept event."""
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return mask
    keep = np.zeros(len(idx), dtype=bool)
    last = -(gap + 1)
    for i, t in enumerate(idx):
        if t - last > gap:
            keep[i] = True
            last = t
    out = np.zeros_like(mask)
    out[idx[keep]] = True
    return out


FAMILIES = {
    "impulse_cont": grid_impulse_cont,
    "breakout_cont": grid_breakout_cont,
    "pullback_cont": grid_pullback_cont,
    "drift_hour": grid_drift_hour,
    "drift_mow": grid_drift_mow,
}


def main():
    args = sys.argv[1:]
    fams = [a for a in args if a in FAMILIES] or list(FAMILIES)
    syms = [a for a in args if a not in FAMILIES] or data_plane.SYMBOLS
    lab = sweep.Lab()
    t0 = time.time()
    for sym in syms:
        for fam in fams:
            n = FAMILIES[fam](sym, lab)
            print(f"{sym}/{fam}: {n} cells | {time.time()-t0:.0f}s",
                  flush=True)
            top = lab.db.execute(f"""
              SELECT symbol, side, params_json, n_kept,
                     round(mean_p,2) m, round(t_stat,1) t, round(pf,2) pf
              FROM results WHERE family='{fam}' AND symbol='{sym}'
              ORDER BY t_stat DESC LIMIT 4""").df()
            if len(top):
                print(top.to_string(index=False), flush=True)
    lab.apply_fdr()
    print("=== survivors ===", flush=True)
    print(lab.survivors().to_string())
    lab.close()


if __name__ == "__main__":
    main()
