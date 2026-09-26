"""M4 — BOXES AND BREAKOUTS (DESIGN only).

Detector per preregistration (STUDY_PLAN §5, ledger T000364) — revised
after the M8 review (the previous version used a longest-window/34-pip
detector that was NOT the declared one; see DEVIATIONS D7):

  At bar t look back W = 30 bars: hh = max h, ll = min l over the window.
  A box is CONFIRMED at t iff
    * height hh-ll in [1.5, 6.0] * abr[t];
    * top touches  #{i in window: h_i >= hh - tol_i} >= 2 and
      bottom     #{i in window: l_i <= ll + tol_i} >= 2;
    * interleave: the first and last edge-touching bar of the window are
      on opposite edges (a bar touching both edges is assigned to the
      edge its close is nearer to);
    * span between the first and last edge touch >= 9 bars;
    * no box currently active.
  The box [ll, hh] freezes at the confirm bar.  It dies at the first
  close >= tol beyond an edge (BOX_BREAK event, dir +1/-1) or 100 bars
  after birth (silent expiry).  At most one break per box per direction
  (the box dies at the first break).

  While active, a wick beyond an edge that closes back inside is a POKE;
  consecutive poking bars on the same edge merge into one event with the
  max penetration depth.

Placebo (declared §5 — replaces the non-declared random-bar placebo the
reviewer voided):  fake edges = the M3 P-RAND pool (24 uniform prices
per day inside day_open +- 3.5*ABR, same generator/seed as
mk_m3_levels.grid_columns).  A level becomes a candidate fake edge only
after >= 2 zone touches (level +- tol) inside the trailing 30 bars —
the same "tested edge" conditioning as the real detector's edge-touch
counts.
    POKE  dir+1: h[t] > edge and c[t] <= edge   (depth = h - edge)
    POKE  dir-1: l[t] < edge and c[t] >= edge
    BREAK dir+1: c[t] > edge + tol[t] with c[t-1] <= edge + tol[t-1]
    BREAK dir-1: mirror
Freshness: >= FRESH bars between same-direction events; an edge dies in
a direction after its break (one break per direction per edge, like a
real box).  The poke's traversal target = the nearest same-day PRAND
level on the opposite side (self-contained fake height, matched via the
height tercile in the stratum key).

Metrics:
  - box height/duration distributions by session (descriptive)
  - breakout follow-through: declared race — P(move >= 1*ABR beyond the
    edge in the break direction before >= 1*ABR back through it, H=24);
    plus fwd_H and MFE descriptively; buildup (a) vs (b) per plan.
  - false breaks: P(reach opposite edge <=24 bars) by disjoint poke-depth
    bins (0,1], (1,2], (2,3], (3,5] pips, vs placebo pokes.

Output: out/m4_events_<SYM>.npz, out/m4_results.json, BOXES.md.
"""

import hashlib
import os
import sys
import zlib

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402

OUT = K.OUT
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4}
YEARS = list(range(2016, 2022))

W = 30                        # trailing window, bars (plan §5)
H_MIN_A, H_MAX_A = 1.5, 6.0   # box height bounds in ABR (plan §5)
SPAN_MIN = 9                  # first->last edge-touch span (plan §5)
AGE_MAX = 100                 # box dies 100 bars after birth (plan §5)
PRESS_A, TIGHT_A = 1.0, 0.8   # buildup: high within 1 ABR of edge, tight .8
RACE_Y, RACE_H = 1.0, 24      # follow-through race: 1 ABR, 24 bars
OPP_HORIZON = 24              # bars to reach the opposite edge
CONV_HORIZON = 3              # bars for a poke to convert to a break


def session_of(cet_min):
    if cet_min < 480:
        return "ASIA"
    if cet_min < 870:
        return "EU"
    if cet_min < 1080:
        return "US"
    return "LATE"


# ------------------------------------------------------------- detection
def _edge_side_seq(hw, lw, cw, hh, ll, tolw):
    """Edge-touch sequence in a window: arrays of bar -> 0 none, +1 top,
    -1 bottom.  A bar touching both edges is assigned to the edge its
    close is nearer to."""
    tt = hw >= hh - tolw
    tb = lw <= ll + tolw
    side = np.zeros(len(hw), dtype=np.int64)
    both = tt & tb
    side[tt & ~tb] = 1
    side[tb & ~tt] = -1
    if both.any():
        nearer_top = (hh - cw) <= (cw - ll)
        side[both & nearer_top] = 1
        side[both & ~nearer_top] = -1
    return side


def detect_boxes(bars, abr, tol):
    """Causal §5 box state machine.  Returns (boxes, pokes, breaks)."""
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    c = np.asarray(bars["c"])
    warm = np.asarray(bars["warmup"], dtype=bool)
    day = K.day_id(bars)
    year = K.server_year(bars)
    cetm = K.cet_minutes(bars)
    utc_min = np.asarray(bars["utc_min"])
    dow = np.asarray(bars["dow"])
    pip = float(bars["pip"])
    n = len(c)

    hh = pd.Series(h).rolling(W).max().values   # hh[t]: max h[t-W+1..t]
    ll = pd.Series(l).rolling(W).min().values
    rng = hh - ll

    boxes, pokes, breaks = [], [], []
    active = None          # dict(lo,hi,born)
    poke_streak = None     # dict(dir,start,end,depth,box)
    t = W
    while t < n:
        if active is None:
            if not warm[t] and np.isfinite(abr[t]) and abr[t] > 0 \
                    and np.isfinite(rng[t]) \
                    and H_MIN_A * abr[t] <= rng[t] <= H_MAX_A * abr[t]:
                s = t - W + 1
                side_seq = _edge_side_seq(h[s:t + 1], l[s:t + 1],
                                          c[s:t + 1], hh[t], ll[t],
                                          tol[s:t + 1])
                et = np.flatnonzero(side_seq)
                if (side_seq == 1).sum() >= 2 and (side_seq == -1).sum() >= 2 \
                        and len(et) >= 2 \
                        and side_seq[et[0]] != side_seq[et[-1]] \
                        and et[-1] - et[0] >= SPAN_MIN:
                    active = {"lo": float(ll[t]), "hi": float(hh[t]),
                              "born_at": t,
                              "session": session_of(int(cetm[t]))}
                    boxes.append(active)
            t += 1
            continue
        # ---- active box ------------------------------------------------
        if t - active["born_at"] >= AGE_MAX:
            active["died_at"] = t
            active = None
            continue                       # silent age death; bar retried
        lo, hi = active["lo"], active["hi"]
        if c[t] > hi + tol[t]:
            brd = +1
        elif c[t] < lo - tol[t]:
            brd = -1
        else:
            brd = 0
        if brd:
            if poke_streak is not None:
                pokes.append(poke_streak); poke_streak = None
            active["died_at"] = t
            breaks.append(_mk_ev(bars, t, brd, active, abr, day, year,
                                 utc_min, cetm, dow, kind="BREAK"))
            active = None
            t += 1
            continue
        if h[t] > hi and c[t] <= hi:
            if poke_streak and poke_streak["dir"] == 1:
                poke_streak["depth"] = max(poke_streak["depth"],
                                           float(h[t] - hi))
                poke_streak["end"] = t
            else:
                if poke_streak:
                    pokes.append(poke_streak)
                poke_streak = {"dir": 1, "start": t, "end": t,
                               "depth": float(h[t] - hi), "box": active}
        elif l[t] < lo and c[t] >= lo:
            if poke_streak and poke_streak["dir"] == -1:
                poke_streak["depth"] = max(poke_streak["depth"],
                                           float(lo - l[t]))
                poke_streak["end"] = t
            else:
                if poke_streak:
                    pokes.append(poke_streak)
                poke_streak = {"dir": -1, "start": t, "end": t,
                               "depth": float(lo - l[t]), "box": active}
        elif poke_streak is not None:
            pokes.append(poke_streak); poke_streak = None
        t += 1
    if poke_streak is not None:
        pokes.append(poke_streak)
    return boxes, pokes, breaks


def _mk_ev(bars, t, side, box, abr, day, year, utc_min, cetm, dow,
           kind="BREAK"):
    return {"bar": int(t), "day": int(day[t]), "year": int(year[t]),
            "utc_min": int(utc_min[t]), "cet_min": int(cetm[t]),
            "dow": int(dow[t]), "side": int(side), "kind": kind,
            "abr": float(abr[t]),
            "approach_atr": np.nan,
            "box_lo": box["lo"], "box_hi": box["hi"],
            "box_h_pips": (box["hi"] - box["lo"]) / float(bars["pip"]),
            "box_age": int(t - box["born_at"]),
            "session": box["session"]}


# --------------------------------------------------------- placebo edges
def prand_edge_events(bars, abr, tol, sym="", w=W):
    """Declared §5 fake-edge placebo (P-RAND pool, >=2 trailing touches).

    Reuses mk_m3_levels.grid_columns so the level pool is identical to
    the M3 PRAND arm.  Opposite traversal target = nearest same-day pool
    level on the opposite side of the edge.
    """
    from mk_m3_levels import grid_columns, sym_seed
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    c = np.asarray(bars["c"])
    warm = np.asarray(bars["warmup"], dtype=bool)
    day = K.day_id(bars)
    year = K.server_year(bars)
    cetm = K.cet_minutes(bars)
    utc_min = np.asarray(bars["utc_min"])
    dow = np.asarray(bars["dow"])
    n = len(c)

    cols = grid_columns(bars, abr, off_pips=0.0, uniform=24,
                        seed=K.SEED + 40000 + sym_seed(sym))
    pmat = np.stack([col["price"] for col in cols])     # (nlev, n)
    pokes, brks = [], []
    for ci, col in enumerate(cols):
        price = col["price"]
        act = np.isfinite(price)
        if not act.any():
            continue
        # trailing-30 touch count of this level's zone, INCLUDING the
        # current bar ("touched >=2x in the trailing 30 bars" — the event
        # bar's own touch counts, so the effective prior-touch floor is 1)
        zl = price - tol; zh = price + tol
        tch = act & (l <= zh) & (h >= zl)
        cs = np.concatenate(([0], np.cumsum(tch.astype(np.int64))))
        idx = np.arange(n)
        cnt30 = cs[idx + 1] - cs[np.clip(idx - w + 1, 0, None)]
        last = {1: -10 ** 9, -1: -10 ** 9}
        dead = {1: False, -1: False}
        prev_c_ok_up = np.concatenate(([False],
                                       c[:-1] <= (price[:-1] + tol[:-1])))
        prev_c_ok_dn = np.concatenate(([False],
                                       c[:-1] >= (price[:-1] - tol[:-1])))
        for t in np.flatnonzero(act & (cnt30 >= 2) & ~warm
                              & np.isfinite(abr) & (abr > 0)):
            L = price[t]
            for d in (1, -1):
                if dead[d] or t - last[d] < K.FRESH:
                    continue
                if d > 0:
                    is_brk = c[t] > L + tol[t] and prev_c_ok_up[t]
                    is_poke = (not is_brk) and h[t] > L and c[t] <= L
                else:
                    is_brk = c[t] < L - tol[t] and prev_c_ok_dn[t]
                    is_poke = (not is_brk) and l[t] < L and c[t] >= L
                if not (is_brk or is_poke):
                    continue
                # nearest same-day pool level on the opposite side
                oth = pmat[:, t]
                opp = np.where(oth < L, oth, np.nan) if d > 0 else \
                    np.where(oth > L, oth, np.nan)
                opp = opp[np.isfinite(opp)]
                if not len(opp):
                    continue
                opp_e = float(opp.max() if d > 0 else opp.min())
                ev = {"bar": int(t), "end": int(t), "day": int(day[t]),
                      "year": int(year[t]), "utc_min": int(utc_min[t]),
                      "cet_min": int(cetm[t]), "dow": int(dow[t]),
                      "side": d, "abr": float(abr[t]),
                      "approach_atr": np.nan, "edge": float(L),
                      "opp": opp_e,
                      "hgt_abr": float(abs(opp_e - L) / abr[t])}
                if is_brk:
                    last[d] = t
                    dead[d] = True
                    brks.append(ev)
                else:
                    # streak-merge consecutive poke bars on this edge
                    # (mirror real pokes): one event, depth = max wick
                    dep = float(h[t] - L) if d > 0 else float(L - l[t])
                    end = t
                    while end + 1 < n and np.isfinite(price[end + 1]):
                        e1 = end + 1
                        if d > 0 and h[e1] > price[e1] \
                                and c[e1] <= price[e1]:
                            dep = max(dep, float(h[e1] - price[e1]))
                            end = e1
                        elif d < 0 and l[e1] < price[e1] \
                                and c[e1] >= price[e1]:
                            dep = max(dep, float(price[e1] - l[e1]))
                            end = e1
                        else:
                            break
                    ev["end"] = int(end)
                    ev["depth"] = dep
                    pokes.append(ev)
                    last[d] = end      # freshness from streak end
    return pokes, brks


# ------------------------------------------------------------- outcomes
def race24(m5, t, edge, side, A, y=RACE_Y, horizon=RACE_H):
    """Declared follow-through: +1 = price moves >= y*ABR beyond the edge
    in the break direction before >= y*ABR back through it, within
    `horizon` M5 bars after t.  0 if the reversal hits first, NaN if
    neither."""
    h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
    n = len(h)
    up = edge + y * A
    dn = edge - y * A
    for u in range(t + 1, min(n, t + 1 + horizon)):
        if side > 0:
            if h[u] >= up:
                return 1.0
            if l[u] <= dn:
                return 0.0
        else:
            if l[u] <= dn:
                return 1.0
            if h[u] >= up:
                return 0.0
    return np.nan


def mfe(m5, t, edge, side, A, horizon=RACE_H):
    """Max favourable excursion beyond the edge in ABR over `horizon`."""
    h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
    n = len(h)
    t1 = min(n, t + 1 + horizon)
    if t + 1 >= t1:
        return np.nan
    if side > 0:
        return float((h[t + 1:t1].max() - edge) / A)
    return float((edge - l[t + 1:t1].min()) / A)


def resolve_break(m1, m5, ev, horizon=48):
    """fwd returns + race24 + buildup features for a real break."""
    t = ev["bar"]; A = ev["abr"]; side = ev["side"]
    c = np.asarray(m5["c"]); h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
    res = {}
    for H in K.HORIZONS:
        j = t + H
        res[f"fwd_{H}"] = float((c[j] - c[t]) * side) if j < len(c) \
            else np.nan
    edge = ev["box_hi"] if side > 0 else ev["box_lo"]
    res["race24"] = race24(m5, t, edge, side, A)
    res["mfe24"] = mfe(m5, t, edge, side, A)
    # buildup per plan: >=3 consecutive bars immediately before t, each
    # range <= .8*ABR, each high within 1*ABR of the edge, non-decreasing
    # lows (up) / non-increasing highs (down).
    run = 0
    u = t - 1
    while u >= 0 and u > t - 8:
        tight = (h[u] - l[u]) <= TIGHT_A * A
        near = (edge - h[u]) <= PRESS_A * A if side > 0 else \
            (l[u] - edge) <= PRESS_A * A
        mono = True
        if run > 0:
            mono = l[u] <= l[u + 1] if side > 0 else h[u] >= h[u + 1]
        if tight and near and mono:
            run += 1
            u -= 1
        else:
            break
    res["buildup"] = bool(run >= 3)
    res["press_n"] = int(run)
    return res


def resolve_poke(m5, ev, opp_h=OPP_HORIZON, conv_h=CONV_HORIZON):
    """After a poke ends: conversion within conv_h bars; reach opposite
    edge within opp_h bars."""
    t_end = ev["end"]; side = ev["dir"]; A = ev["abr_at"]
    c = np.asarray(m5["c"]); h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
    tol_t = ev["tol_at"]
    lo, hi = ev["box"]["lo"], ev["box"]["hi"]
    n = len(c)
    conv = False
    for u in range(t_end + 1, min(n, t_end + 1 + conv_h)):
        if (side > 0 and c[u] > hi + tol_t) or \
                (side < 0 and c[u] < lo - tol_t):
            conv = True
            break
    opp_edge = lo if side > 0 else hi
    reach = False; reach_bar = None
    for u in range(t_end + 1, min(n, t_end + 1 + opp_h)):
        if (side > 0 and l[u] <= opp_edge) or \
                (side < 0 and h[u] >= opp_edge):
            reach = True; reach_bar = u
            break
    return {"converted": bool(conv), "reach_opp": bool(reach),
            "bars_to_opp": (reach_bar - t_end) if reach_bar else -1}


def resolve_poke_plac(m5, ev, opp_h=OPP_HORIZON):
    """Placebo poke: reach the fake box's opposite edge within opp_h."""
    t_end = ev["end"]; side = ev["side"]
    h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
    opp = ev["opp"]
    n = len(h)
    reach = False
    for u in range(t_end + 1, min(n, t_end + 1 + opp_h)):
        if (side > 0 and l[u] <= opp) or (side < 0 and h[u] >= opp):
            reach = True
            break
    return {"reach_opp": bool(reach)}


def resolve_break_plac(m5, ev):
    t = ev["bar"]; A = ev["abr"]; side = ev["side"]
    c = np.asarray(m5["c"])
    res = {}
    for H in K.HORIZONS:
        j = t + H
        res[f"fwd_{H}"] = float((c[j] - c[t]) * side) if j < len(c) \
            else np.nan
    res["race24"] = race24(m5, t, ev["edge"], side, A)
    res["mfe24"] = mfe(m5, t, ev["edge"], side, A)
    return res


# ---------------------------------------------------------------- main
def serialize(npz, name, ev, extra_keys):
    base = ["bar", "day", "year", "utc_min", "cet_min", "dow", "side",
            "abr", "approach_atr"]
    for kk in base + list(extra_keys):
        npz[f"{name}__{kk}"] = np.array(
            [e.get(kk, float("nan")) if not isinstance(e.get(kk), str)
             else float("nan") for e in ev], dtype=np.float64)


def main():
    os.makedirs(OUT, exist_ok=True)
    for sym in K.CORE:
        print(f"[M4] {sym} ...", flush=True)
        with K.pa_slots.slot(f"dr-market M4 {sym}", timeout=120):
            dd = K.load_symbol(sym)
            m1, m5 = dd["m1"], dd["m5"]
            abr = K.abr_series(m5)
            tol = K.tol_array(abr, float(m5["pip"]))
            boxes, pokes, breaks = detect_boxes(m5, abr, tol)
            ppk, pbr = prand_edge_events(m5, abr, tol, sym=sym)
            print(f"  {sym}: {len(boxes)} boxes, {len(pokes)} pokes, "
                  f"{len(breaks)} breaks | plac {len(ppk)} pokes, "
                  f"{len(pbr)} breaks", flush=True)
            for e in breaks:
                e["res"] = resolve_break(m1, m5, e)
            for e in pbr:
                e["res"] = resolve_break_plac(m5, e)
            for p in pokes:
                p["abr_at"] = float(abr[p["start"]])
                p["tol_at"] = float(tol[p["start"]])
                p.update(_mk_ev(m5, p["start"], p["dir"], p["box"], abr,
                                K.day_id(m5), K.server_year(m5),
                                np.asarray(m5["utc_min"]),
                                K.cet_minutes(m5), np.asarray(m5["dow"]),
                                kind="POKE"))
                p["res"] = resolve_poke(m5, p)
            for p in ppk:
                p["res"] = resolve_poke_plac(m5, p)
            npz = {}
            serialize(npz, "BREAK", breaks, ["box_h_pips", "box_age"])
            serialize(npz, "POKE", pokes, ["depth", "box_h_pips",
                                           "box_age"])
            serialize(npz, "PPK", ppk, ["depth", "edge", "opp", "hgt_abr"])
            serialize(npz, "PBRK", pbr, ["edge", "hgt_abr"])
            for name, ev in (("BREAK", breaks), ("PBRK", pbr)):
                for kk in [f"fwd_{H}" for H in K.HORIZONS] + \
                        ["buildup", "press_n", "race24", "mfe24"]:
                    npz[f"{name}__{kk}"] = np.array(
                        [float(e["res"].get(kk, np.nan))
                         if e["res"].get(kk) is not None else np.nan
                         for e in ev], dtype=np.float64)
            for kk in ("converted", "reach_opp", "bars_to_opp"):
                npz[f"POKE__{kk}"] = np.array(
                    [float(p["res"].get(kk, np.nan)) for p in pokes],
                    dtype=np.float64)
            npz["PPK__reach_opp"] = np.array(
                [float(p["res"].get("reach_opp", np.nan)) for p in ppk],
                dtype=np.float64)
            npz["BOX__session"] = np.array(
                [{"ASIA": 0, "EU": 1, "US": 2, "LATE": 3}[b["session"]]
                 for b in boxes], dtype=np.float64)
            npz["BOX__h_pips"] = np.array(
                [(b["hi"] - b["lo"]) / float(m5["pip"]) for b in boxes])
            npz["BOX__born"] = np.array([b["born_at"] for b in boxes])
            npz["BOX__age"] = np.array(
                [b.get("age", np.nan) for b in boxes])
            path = os.path.join(OUT, f"m4_events_{sym}.npz")
            np.savez_compressed(path, **npz)
            sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
            print(f"  {sym} saved sha={sha[:12]}", flush=True)
    print("[M4] extraction done.")


if __name__ == "__main__":
    main()
