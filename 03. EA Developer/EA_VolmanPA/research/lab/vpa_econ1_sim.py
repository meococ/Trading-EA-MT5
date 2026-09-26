"""VPA-ECON-1 fill/exit engine — frozen semantics (prereg VPA-DR3_ECON1_PREREG §3).

Shared by the DR3 signals and the matched-random entries so the lift compares
like with like. Semantics mirror the frozen random baseline
(`vpa_random_baseline.py:125-266`) plus the ECON-1 order model:

  - stop order = signal-bar extreme +/- 1.0 pip; valid V=3 M5 bars;
  - fill on the M1 path, gap-aware: fill = max(open, stop) / min(open, stop);
  - order cancelled if the invalidation is touched BEFORE the fill (adverse-first
    inside an M1 bar: the cancel wins over a same-bar fill);
  - all-in cost c_rt applied once as an adverse fill shift (x1/x1.5/x2);
  - SL = fill - S, TP = fill + 2S; resolved on M1, SL checked first (same-bar
    TP+SL -> SL);
  - safety flats: Friday 20:00 server (no new order at/after it; open position
    closed at the first M1 close at/after it), daily 22:00 server, plus a
    server-midnight fallback;
  - no break-even, no trailing, no partials, no manual exits.

Causal: a trade only reads M1 bars after its own signal bar; no future data.
"""

import numpy as np

BUF_PIPS = 1.0
V_BARS = 3
S_PIPS = 8.0
TP_MULT = 2.0


def build_ctx(m1, m5, m5_t, starts, pip, next_end=None):
    """Pre-extract the per-M1 lists used by the hot loop (one pass).
    next_end[i] = M1 index where the session containing M5 bar i ends
    (order cancelled at the session end, G1)."""
    n_m1 = len(m1["t"])
    mt = m1["t"]
    day = (mt // 86400)
    dow = ((mt // 86400) + 4) % 7          # Monday=0 (repo convention)
    srv_hour = (mt % 86400) // 3600
    return {
        "n_m1": n_m1,
        "mt": mt.tolist(), "mo": m1["o"].tolist(), "mh": m1["h"].tolist(),
        "ml": m1["l"].tolist(), "mc": m1["c"].tolist(),
        "mday": day.tolist(), "mdow": dow.tolist(), "msrv": srv_hour.tolist(),
        "starts": starts.tolist(),
        "m5h": np.asarray(m5["h"]).tolist(), "m5l": np.asarray(m5["l"]).tolist(),
        "m5_t": np.asarray(m5_t).tolist(),
        "n_m5": len(m5_t),
        "next_end": (np.asarray(next_end).tolist() if next_end is not None else None),
        "pip": pip,
    }


def simulate_entries(entries, ctx, S=S_PIPS, V=V_BARS, mult=1.0, cost_rt_pips=1.0,
                     buf_pips=BUF_PIPS, invalidation=True, flats=True):
    """entries: iterable of dicts {sig, side, inv (opt), atr (opt), tag (opt)}.
    Returns a list of trade dicts (fills and non-fills both logged)."""
    pip = ctx["pip"]
    c = cost_rt_pips * mult * pip
    sl_d = S * pip
    tp_d = TP_MULT * S * pip
    starts = ctx["starts"]
    n_m5 = ctx["n_m5"]
    n_m1 = ctx["n_m1"]
    mt, mo, mh, ml, mc = ctx["mt"], ctx["mo"], ctx["mh"], ctx["ml"], ctx["mc"]
    mday, mdow, msrv = ctx["mday"], ctx["mdow"], ctx["msrv"]
    m5h, m5l, m5_t = ctx["m5h"], ctx["m5l"], ctx["m5_t"]
    out = []
    for e in entries:
        sig = int(e["sig"])
        d = int(e["side"])
        tag = e.get("tag")
        if sig + 1 >= n_m5:
            continue
        # Friday 20:00 server veto: no new order at/after it
        srv_h = (m5_t[sig] % 86400) // 3600
        dow5 = ((m5_t[sig] // 86400) + 4) % 7
        if flats and dow5 == 4 and srv_h >= 20:
            out.append({"sig": sig, "side": d, "tag": tag, "status": "VETO_FRIDAY"})
            continue
        stop = (m5h[sig] + buf_pips * pip) if d > 0 else (m5l[sig] - buf_pips * pip)
        inv = e.get("inv") if invalidation else None
        i0 = starts[sig + 1]
        j = sig + 1 + V
        i1 = starts[j] if j < n_m5 else n_m1
        ne = ctx.get("next_end")
        if ne is not None and ne[sig] < i1:      # order cancelled at session end (G1)
            i1 = ne[sig]
        fi = -1
        fill_raw = 0.0
        cancelled = False
        for i in range(i0, i1):
            if inv is not None:
                if (d > 0 and ml[i] <= inv) or (d < 0 and mh[i] >= inv):
                    cancelled = True
                    break
            if d > 0 and mh[i] >= stop:
                fill_raw = mo[i] if mo[i] > stop else stop
                fi = i
                break
            if d < 0 and ml[i] <= stop:
                fill_raw = mo[i] if mo[i] < stop else stop
                fi = i
                break
        if cancelled:
            out.append({"sig": sig, "side": d, "tag": tag, "status": "CANCELLED"})
            continue
        if fi < 0:
            out.append({"sig": sig, "side": d, "tag": tag, "status": "EXPIRED"})
            continue
        gap = d * (fill_raw - stop)
        fill = fill_raw + d * c
        SL = fill - d * sl_d
        TP = fill + d * tp_d
        fday = mday[fi]
        exit_i = -1
        exit_px = fill
        reason = ""
        for i in range(fi, n_m1):
            if d > 0:
                if ml[i] <= SL:
                    exit_i, exit_px, reason = i, SL, "SL"
                    break
                if mh[i] >= TP:
                    exit_i, exit_px, reason = i, TP, "TP"
                    break
            else:
                if mh[i] >= SL:
                    exit_i, exit_px, reason = i, SL, "SL"
                    break
                if ml[i] <= TP:
                    exit_i, exit_px, reason = i, TP, "TP"
                    break
            if flats and msrv[i] >= 22:
                exit_i, exit_px, reason = i, mc[i], "DAILY"
                break
            if flats and mdow[i] == 4 and msrv[i] >= 20:
                exit_i, exit_px, reason = i, mc[i], "FRIDAY"
                break
            if mday[i] != fday:
                exit_i, exit_px, reason = i - 1, mc[i - 1], "MIDNIGHT"
                break
        if exit_i < 0:
            exit_i, exit_px, reason = n_m1 - 1, mc[n_m1 - 1], "DATA_END"
        if reason == "SL":
            r = -1.0
        elif reason == "TP":
            r = 2.0
        else:
            r = d * (exit_px - fill) / sl_d
        atr = e.get("atr")
        out.append({
            "sig": sig, "side": d, "tag": tag, "status": "FILLED",
            "fill_idx": fi, "fill": fill, "stop": stop, "sl": SL, "tp": TP,
            "exit_idx": exit_i, "exit_px": exit_px, "reason": reason, "r": r,
            "bars_m1": exit_i - fi + 1,
            "gap_atr": (gap / atr) if (atr and atr > 0) else None,
            "cost_pips": cost_rt_pips * mult,
            "exit_t": mt[exit_i], "fill_t": mt[fi],
        })
    return out


def metrics(trades, S=S_PIPS):
    """Aggregate the filled trades: N, WR, PF, b, exp R, R total, DD at 0.5%/trade."""
    filled = [t for t in trades if t.get("status") == "FILLED"]
    if not filled:
        return {"N": 0}
    rr = np.array([t["r"] for t in filled], dtype=np.float64)
    wins = rr[rr > 0]
    losses = rr[rr < 0]
    pf = float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
    b = float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) else float("nan")
    # equity: fixed 0.5% risk on the initial equity, chronological by exit time
    order = np.argsort([t["exit_t"] for t in filled], kind="stable")
    eq = 1.0
    peak = 1.0
    dd = 0.0
    curve = []
    for k in order:
        eq *= (1.0 + 0.005 * rr[k])
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
        curve.append(eq)
    return {
        "N": len(filled), "WR": float((rr > 0).mean()), "PF": pf, "b": b,
        "exp_r": float(rr.mean()), "R_total": float(rr.sum()),
        "max_dd_pct": float(dd * 100.0), "final_eq": float(eq),
        "n_tp": sum(1 for t in filled if t["reason"] == "TP"),
        "n_sl": sum(1 for t in filled if t["reason"] == "SL"),
        "n_daily": sum(1 for t in filled if t["reason"] == "DAILY"),
        "n_friday": sum(1 for t in filled if t["reason"] == "FRIDAY"),
        "n_midnight": sum(1 for t in filled if t["reason"] == "MIDNIGHT"),
        "n_data_end": sum(1 for t in filled if t["reason"] == "DATA_END"),
    }


def newcombe_diff(k1, n1, k2, n2, z=1.96):
    """95% CI for p1 - p2 (Newcombe method 10, same as the fidelity work)."""
    import math

    def wilson(k, n):
        p = k / n
        den = 1 + z * z / n
        ctr = (p + z * z / (2 * n)) / den
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return max(0.0, ctr - h), min(1.0, ctr + h)

    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
