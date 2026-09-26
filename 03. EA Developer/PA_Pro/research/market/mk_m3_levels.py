"""M3 — levels as zones (DESIGN 2016-2021).

Level sets (STUDY_PLAN §1): S1 (theta1=1.0 ABR DC pivots), S2 (2.5 ABR),
PDH/PDL, ASIA hi/lo (00:00-08:00 CET), RND 00/50 grid, placebos P-RND20,
P-RND10, P-RAND (24 uniform levels/day).

Per event: touch machinery (fresh 24, away 1.0 ABR), outcome resolved on the
M1 path for x in {1, 2} ABR barriers, horizon 48 M5 bars.  Plus overshoot,
retest-after-break and role-reversal, and round-number cross "cascades".

Outputs: out/m3_events_<SYM>.npz (event tables), out/m3_summary.json,
LEVELS.md.  One ledger row (kind=market_study) per result family with
spec_sha256 = STUDY_PLAN hash.
"""

import hashlib
import json
import os
import sys
import zlib

import numpy as np


def sym_seed(sym):
    """Stable per-symbol seed (str.__hash__ is process-randomized)."""
    return zlib.crc32(sym.encode("ascii")) & 0x7FFFFFFF

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402

PLAN_SHA = "abc8b5ba5a80d04928b78204e2d690a5cdb74b091f515a6ff8669cfb499f962c"
HOR = 48
MAX_AGE = 1440          # 5 days of M5 bars
FRESH_CROSS = 288       # cascade freshness: level untouched for 24h


# ------------------------------------------------------------ level sets
def pivot_columns(bars, pivots, max_age=MAX_AGE):
    """Interval-graph colouring: each pivot -> first free column."""
    n = len(bars["t"])
    cols = []          # each: dict(price,birth,lid arrays)
    free_at = []
    pid = 0
    for (ci, ei, kind, price) in pivots:
        pid += 1
        b = int(ci)
        e = int(min(n, ci + max_age))
        placed = False
        for k in range(len(cols)):
            if free_at[k] <= b:
                c = cols[k]
                c["price"][b:e] = price
                c["birth"][b:e] = b
                c["lid"][b:e] = pid
                c["kind"][b:e] = kind
                free_at[k] = e
                placed = True
                break
        if not placed:
            cols.append({"price": np.full(n, np.nan),
                         "birth": np.zeros(n, np.int64),
                         "lid": np.zeros(n, np.int64),
                         "kind": np.zeros(n, np.int64)})
            free_at.append(e)
            c = cols[-1]
            c["price"][b:e] = price
            c["birth"][b:e] = b
            c["lid"][b:e] = pid
            c["kind"][b:e] = kind
    return cols


def pdh_pdl_columns(bars):
    """Prev server-day high/low, active the whole current day."""
    n = len(bars["t"])
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    day = K.day_id(bars)
    days = np.unique(day)
    day_hi = {d: float(h[day == d].max()) for d in days}
    day_lo = {d: float(l[day == d].min()) for d in days}
    pdh = np.full(n, np.nan); pdl = np.full(n, np.nan)
    bh = np.zeros(n, np.int64); bl = np.zeros(n, np.int64)
    prev = None
    for d in days:
        m = day == d
        if prev is not None:
            pdh[m] = day_hi[prev]; pdl[m] = day_lo[prev]
            first = int(np.flatnonzero(m)[0])
            bh[m] = first; bl[m] = first
        prev = d
    cols = [
        {"price": pdh, "birth": bh, "lid": (day % 10**6) * 10 + 1,
         "kind": np.full(n, 1)},
        {"price": pdl, "birth": bl, "lid": (day % 10**6) * 10 + 2,
         "kind": np.full(n, -1)},
    ]
    return cols


def asia_columns(bars):
    """Asia hi/lo 00:00-08:00 CET, armed strictly after the window closes.

    Bars are grouped by server day; CET minute is close-based.  The Asia
    window of CET-day d is the server-day-d bars closing at cet in (0,480]
    (server 01:05-09:00).  Post-Asia bars of CET-day d are: server-day-d
    bars with cet in (480,1380)  *plus*  server-day-(d+1) bars with
    cet >= 1380 — those are CET 23:xx of day d sitting in the first server
    hour of day d+1 (previously they were armed with a level computed from
    bars up to ~9h in their own future: review finding F-ASIA).
    """
    n = len(bars["t"])
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    day = K.day_id(bars)
    cet = K.cet_minutes(bars)
    ahi = np.full(n, np.nan); alo = np.full(n, np.nan)
    bh = np.zeros(n, np.int64); bl = np.zeros(n, np.int64)
    win = {}
    for d in np.unique(day):
        m = day == d
        asia = m & (cet <= 480) & (cet > 0)
        if asia.sum() < 30:
            continue
        win[d] = (float(h[asia].max()), float(l[asia].min()))
    for d, (hi, lo) in win.items():
        post = ((day == d) & (cet > 480) & (cet < 1380)) | \
               ((day == d + 1) & (cet >= 1380))
        if not post.any():
            continue
        first = int(np.flatnonzero(post)[0])
        ahi[post] = hi; alo[post] = lo
        bh[post] = first; bl[post] = first
    return [
        {"price": ahi, "birth": bh, "lid": (day % 10**6) * 10 + 3,
         "kind": np.full(n, 1)},
        {"price": alo, "birth": bl, "lid": (day % 10**6) * 10 + 4,
         "kind": np.full(n, -1)},
    ]


def grid_columns(bars, abr, off_pips=0.0, span=3.5, uniform=None, seed=0):
    """Per-day level columns: 50-pip grid at `off_pips`, or `uniform` random
    draws per day inside day_open +- span*A.  A per (median ABR of the day)."""
    n = len(bars["t"])
    o = np.asarray(bars["o"]); pip = float(bars["pip"])
    day = K.day_id(bars)
    g = 50.0 * pip
    days_levels = {}
    maxk = 0
    for d in np.unique(day):
        m = day == d
        i0 = int(np.flatnonzero(m)[0])
        A = float(abr[i0])          # causal: ABR at the day's first bar
        if not np.isfinite(A) or A <= 0:
            continue
        lo = o[i0] - span * A
        hi = o[i0] + span * A
        if uniform is None:
            k0 = int(np.floor((lo - off_pips * pip) / g))
            k1 = int(np.ceil((hi - off_pips * pip) / g))
            lev = [(k * g + off_pips * pip) for k in range(k0, k1 + 1)]
        else:
            rng = np.random.default_rng(seed ^ (int(d) * 7919))
            lev = list(rng.uniform(lo, hi, size=uniform))
        days_levels[d] = (i0, lev)
        maxk = max(maxk, len(lev))
    cols = []
    for k in range(maxk):
        price = np.full(n, np.nan)
        birth = np.zeros(n, np.int64)
        lid = np.zeros(n, np.int64)
        for d, (i0, lev) in days_levels.items():
            if k < len(lev):
                m = day == d
                price[m] = lev[k]
                birth[m] = i0
                lid[m] = (int(d) % 10**6) * 100 + k
        cols.append({"price": price, "birth": birth, "lid": lid,
                     "kind": np.zeros(n, np.int64)})
    return cols


# --------------------------------------------------------- event detection
def detect_touches(bars, col, abr, tol, fresh=K.FRESH, away=K.AWAY):
    """Vectorized first-touch detection on one level column."""
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    c = np.asarray(bars["c"])
    warm = np.asarray(bars["warmup"], dtype=bool)
    n = len(h)
    price = col["price"]
    zlo = price - tol
    zhi = price + tol
    active = np.isfinite(price)
    touch = active & (l <= zhi) & (h >= zlo)
    birth = col["birth"]
    cand = touch & np.isfinite(abr) & (abr > 0) & ~warm
    cand[0] = False
    t_arr = np.asarray(bars["t"], dtype=np.int64)
    years = K.server_year(bars)
    cetm = K.cet_minutes(bars)
    dow = np.asarray(bars["dow"])
    utc_min = np.asarray(bars["utc_min"])
    day = K.day_id(bars)
    events = []
    for t in np.flatnonzero(cand):
        # freshness: no bar in [t-fresh, t) intersected the *event* zone,
        # evaluated only over bars where this level instance was live
        # (>= its birth bar).  Closes the review's per-column-zone hole.
        w0 = max(int(birth[t]), t - fresh)
        if w0 < t and ((l[w0:t] <= zhi[t]) & (h[w0:t] >= zlo[t])).any():
            continue
        w0 = max(0, t - fresh)
        dc = np.maximum(zlo[t] - c[w0:t], c[w0:t] - zhi[t])
        A = abr[t]
        if not (dc >= away * A).any():
            continue
        cp = c[t - 1]
        if cp <= zlo[t]:
            side = -1
        elif cp >= zhi[t]:
            side = +1
        else:
            continue
        events.append({
            "bar": int(t), "t": int(t_arr[t]), "day": int(day[t]),
            "year": int(years[t]), "utc_min": int(utc_min[t]),
            "cet_min": int(cetm[t]), "dow": int(dow[t]),
            "side": int(side), "level": float(price[t]),
            "zlo": float(zlo[t]), "zhi": float(zhi[t]),
            "tol": float(tol[t]), "abr": float(A),
            "approach_atr": float(dc.max() / A),
            "dist_cp": float(abs(price[t] - cp) / A),
            "age_bars": int(t - col["birth"][t]),
            "lid": int(col["lid"][t]), "kind": int(col["kind"][t]),
        })
    return events


def detect_crosses(bars, col, abr, tol, fresh=FRESH_CROSS):
    """Cascade events: first CLOSE >= tol beyond a level that has not been
    touched (wick or close inside zone) for `fresh` bars.

    Direction +1 = up cross (close above zhi+tol), -1 = down cross.
    """
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    c = np.asarray(bars["c"])
    warm = np.asarray(bars["warmup"], dtype=bool)
    n = len(h)
    price = col["price"]
    zlo = price - tol
    zhi = price + tol
    active = np.isfinite(price)
    touch = active & (l <= zhi) & (h >= zlo)
    cs = np.concatenate(([0], np.cumsum(touch.astype(np.int64))))
    idx = np.arange(n)
    cnt_prev = cs[idx] - cs[np.clip(idx - fresh, 0, None)]
    # plan: "first cross = close >= tol beyond the level" -> c beyond
    # price +- tol (i.e. beyond the outer zone edge).
    beyond_up = active & (c >= zhi)
    beyond_dn = active & (c <= zlo)
    prev_c = np.concatenate(([np.nan], c[:-1]))
    prev_zhi = np.concatenate(([np.nan], zhi[:-1]))
    prev_zlo = np.concatenate(([np.nan], zlo[:-1]))
    cross_up = beyond_up & ~(prev_c >= prev_zhi) & (cnt_prev == 0)
    cross_dn = beyond_dn & ~(prev_c <= prev_zlo) & (cnt_prev == 0)
    cand = (cross_up | cross_dn) & np.isfinite(abr) & (abr > 0) & ~warm
    cand[0] = False
    birth = col["birth"]
    # same event-zone refinement as detect_touches: a candidate is dropped
    # if any bar in [max(birth, t-fresh), t) intersected the *event* zone.
    for t in np.flatnonzero(cand):
        w0 = max(int(birth[t]), t - fresh)
        if w0 < t and ((l[w0:t] <= zhi[t]) & (h[w0:t] >= zlo[t])).any():
            cand[t] = False
    t_arr = np.asarray(bars["t"], dtype=np.int64)
    years = K.server_year(bars)
    cetm = K.cet_minutes(bars)
    dow = np.asarray(bars["dow"])
    utc_min = np.asarray(bars["utc_min"])
    day = K.day_id(bars)
    events = []
    for t in np.flatnonzero(cand):
        events.append({
            "bar": int(t), "t": int(t_arr[t]), "day": int(day[t]),
            "year": int(years[t]), "utc_min": int(utc_min[t]),
            "cet_min": int(cetm[t]), "dow": int(dow[t]),
            "side": int(1 if cross_up[t] else -1), "level": float(price[t]),
            "zlo": float(zlo[t]), "zhi": float(zhi[t]),
            "tol": float(tol[t]), "abr": float(abr[t]),
            "approach_atr": float("nan"),
            "dist_cp": float(abs(price[t] - c[t - 1]) / abr[t]),
            "age_bars": int(t - col["birth"][t]),
            "lid": int(col["lid"][t]), "kind": int(col["kind"][t]),
            "close": float(c[t]),
        })
    return events


def assign_touch_no(events):
    """touch_no = ordinal of the event within its level id (events sorted)."""
    events.sort(key=lambda e: (e["lid"], e["bar"]))
    cnt = {}
    for e in events:
        cnt[e["lid"]] = cnt.get(e["lid"], 0) + 1
        e["touch_no"] = cnt[e["lid"]]
    events.sort(key=lambda e: e["bar"])
    return events


# ------------------------------------------------------------- resolution
def resolve_event(m1, m5, ev, xs=(1.0, 2.0), horizon=HOR):
    """One M1 scan: bounce/break for each x, overshoot, retest, role rev."""
    t = ev["bar"]
    A = ev["abr"]
    m1t = np.asarray(m1["t"]); m5t = np.asarray(m5["t"])
    t1 = min(len(m5t), t + horizon)
    a, b = K.m1_window_for_bars(m1t, m5t, t, t1)
    h = m1["h"]; l = m1["l"]
    # locate the touch minute: first M1 bar of M5-bar t intersecting the
    # zone; the outcome path starts AFTER it (no pre-touch contamination)
    a_end = int(np.searchsorted(m1t, m5t[t] + 300, side="left"))
    start = a_end
    for j in range(a, a_end):
        if l[j] <= ev["zhi"] and h[j] >= ev["zlo"]:
            start = j + 1
            break
    side = ev["side"]
    if side == -1:
        # resistance touch: break = up through zhi+xA, bounce = down zlo-xA
        brk = {x: ev["zhi"] + x * A for x in xs}
        bnc = {x: ev["zlo"] - x * A for x in xs}
    else:
        # support touch: break = down through zlo-xA, bounce = up zhi+xA
        brk = {x: ev["zlo"] - x * A for x in xs}
        bnc = {x: ev["zhi"] + x * A for x in xs}
    first = {k: None for k in ("b1", "n1", "b2", "n2")}
    keys = list(xs)
    mx = -np.inf; mn = np.inf
    mx_b1 = -np.inf; mn_b1 = np.inf   # extremes until x1 resolves
    res = {"overshoot_full": 0.0, "retreat_full": 0.0}
    hit_bar = {}
    i = start
    while i < b:
        hi = h[i]; lo = l[i]
        if hi > mx: mx = hi
        if lo < mn: mn = lo
        if first["b1"] is None and first["n1"] is None:
            if hi > mx_b1: mx_b1 = hi
            if lo < mn_b1: mn_b1 = lo
        if side == -1:
            if first["b1"] is None and hi >= brk[keys[0]]: first["b1"] = i
            if first["n1"] is None and lo <= bnc[keys[0]]: first["n1"] = i
            if len(keys) > 1:
                if first["b2"] is None and hi >= brk[keys[1]]: first["b2"] = i
                if first["n2"] is None and lo <= bnc[keys[1]]: first["n2"] = i
        else:
            if first["b1"] is None and lo <= brk[keys[0]]: first["b1"] = i
            if first["n1"] is None and hi >= bnc[keys[0]]: first["n1"] = i
            if len(keys) > 1:
                if first["b2"] is None and lo <= brk[keys[1]]: first["b2"] = i
                if first["n2"] is None and hi >= bnc[keys[1]]: first["n2"] = i
        i += 1
    # per-x outcome
    for xi, x in enumerate(xs):
        fb = first[f"b{xi+1}"]; fn = first[f"n{xi+1}"]
        if fb is None and fn is None:
            oc = "NONE"; rb = None
        elif fb is None:
            oc = "BOUNCE"; rb = fn
        elif fn is None:
            oc = "BREAK"; rb = fb
        else:
            oc = "BREAK" if fb < fn else "BOUNCE"
            rb = min(fb, fn)
        res[f"out_x{x:g}"] = oc
        if rb is not None:
            res[f"resbar_x{x:g}"] = int(np.searchsorted(m5t, int(m1t[rb]),
                                                      side="right") - 1)
        else:
            res[f"resbar_x{x:g}"] = None
    # overshoot: max penetration beyond far edge
    if side == -1:
        res["overshoot_full"] = max(0.0, mx - ev["zhi"])
        res["overshoot_x1"] = max(0.0, mx_b1 - ev["zhi"])
        res["retreat_full"] = max(0.0, ev["zlo"] - mn)
        res["retreat_x1"] = max(0.0, ev["zlo"] - mn_b1)
        far = ev["zhi"]; near = ev["zlo"]
    else:
        res["overshoot_full"] = max(0.0, ev["zlo"] - mn)
        res["overshoot_x1"] = max(0.0, ev["zlo"] - mn_b1)
        res["retreat_full"] = max(0.0, mx - ev["zhi"])
        res["retreat_x1"] = max(0.0, mx_b1 - ev["zhi"])
        far = ev["zlo"]; near = ev["zhi"]
    # retest after x1 BREAK: first re-entry into zone after the break bar
    res["retest_12"] = None; res["retest_48"] = None
    res["role_rev"] = None
    if res["out_x1"] == "BREAK":
        res["retest_12"] = False; res["retest_48"] = False
        fb = first["b1"]
        j = fb + 1
        zend_m1 = b
        re_idx = None
        while j < zend_m1:
            if side == -1:
                if l[j] <= ev["zhi"]:
                    re_idx = j; break
            else:
                if h[j] >= ev["zlo"]:
                    re_idx = j; break
            j += 1
        if re_idx is not None:
            re_bar = int(np.searchsorted(m5t, int(m1t[re_idx]),
                                         side="right") - 1)
            brk_bar = int(np.searchsorted(m5t, int(m1t[fb]),
                                          side="right") - 1)
            dbar = re_bar - brk_bar     # retest lag measured from the break
            res["retest_12"] = bool(dbar <= 12)
            res["retest_48"] = bool(dbar <= 48)
            # role reversal: from re-entry, move >=1A in the break direction
            # (rebound past the FAR edge) before re-crossing the zone by 1A
            # (past the NEAR edge against the break direction).
            if side == -1:
                rb_up = far + 1.0 * A
                rc_dn = near - 1.0 * A
                hit, _, _ = K.first_hit(m1, re_idx, zend_m1, rb_up, rc_dn)
                res["role_rev"] = (hit == "up")
            else:
                rb_dn = far - 1.0 * A
                rc_up = near + 1.0 * A
                hit, _, _ = K.first_hit(m1, re_idx, zend_m1, rc_up, rb_dn)
                res["role_rev"] = (hit == "dn")
    return res


# ------------------------------------------------------------- matching
def add_strata_keys(real, plac):
    """Compute shared tercile/decile edges on pooled events and assign keys."""
    pool_abr = np.array([e["abr"] for e in real] +
                        [e["abr"] for e in plac])
    pool_app = np.array([e["approach_atr"] for e in real] +
                        [e["approach_atr"] for e in plac])
    qa = np.quantile(pool_abr, [0, 1/3, 2/3, 1.0])
    qp = np.quantile(pool_app, np.linspace(0, 1, 11))
    for e in real + plac:
        e["atr_ter"] = int(np.searchsorted(qa, e["abr"], side="right") - 1)
        e["app_dec"] = int(np.searchsorted(qp, e["approach_atr"],
                                           side="right") - 1)


def day_of(e):
    return e["day"]


# ---------------------------------------------------------------- driver
def build_symbol_events(sym):
    """All level-set events for one symbol, with resolved outcomes."""
    d = K.load_symbol(sym)
    m1, m5 = d["m1"], d["m5"]
    abr = K.abr_series(m5)
    tol = K.tol_array(abr, float(m5["pip"]))
    h = np.asarray(m5["h"]); l = np.asarray(m5["l"]); c = np.asarray(m5["c"])

    sets = {}
    # S1 / S2 pivots
    for name, th_k in (("S1", 1.0), ("S2", 2.5)):
        theta = th_k * abr
        piv = K.dc_pivots(h, l, c, theta)
        cols = pivot_columns(m5, piv)
        ev = []
        for col in cols:
            ev += detect_touches(m5, col, abr, tol)
        ev = assign_touch_no(ev)
        sets[name] = ev
        print(f"  {sym} {name}: {len(cols)} cols, {len(piv)} pivots, "
              f"{len(ev)} events", flush=True)
    # PDH/PDL
    ev = []
    for col in pdh_pdl_columns(m5):
        ev += detect_touches(m5, col, abr, tol)
    sets["PDHPDL"] = assign_touch_no(ev)
    print(f"  {sym} PDHPDL: {len(ev)} events", flush=True)
    # ASIA
    ev = []
    for col in asia_columns(m5):
        ev += detect_touches(m5, col, abr, tol)
    sets["ASIA"] = assign_touch_no(ev)
    print(f"  {sym} ASIA: {len(ev)} events", flush=True)
    # RND + placebo grids + random levels
    for name, off, unif, sd in (("RND", 0.0, None, 0),
                                ("PRND20", 20.0, None, 0),
                                ("PRND10", 10.0, None, 0),
                                ("PRAND", 0.0, 24, K.SEED)):
        cols = grid_columns(m5, abr, off_pips=off, uniform=unif,
                            seed=sd + sym_seed(sym))
        ev = []
        for col in cols:
            ev += detect_touches(m5, col, abr, tol)
        sets[name] = assign_touch_no(ev)
        print(f"  {sym} {name}: {len(cols)} cols, {len(ev)} events",
              flush=True)
    # cascade cross events on RND + placebo grids (separate freshness)
    cross_sets = {}
    for name, off, unif, sd in (("RND", 0.0, None, 0),
                                ("PRND20", 20.0, None, 0),
                                ("PRAND", 0.0, 24, K.SEED)):
        cols = grid_columns(m5, abr, off_pips=off, uniform=unif,
                            seed=sd + sym_seed(sym))
        ev = []
        for col in cols:
            ev += detect_crosses(m5, col, abr, tol)
        cross_sets[name] = ev
        print(f"  {sym} X-{name}: {len(ev)} crosses", flush=True)
    sets["XRND"] = cross_sets["RND"]
    sets["XPRND20"] = cross_sets["PRND20"]
    sets["XPRAND"] = cross_sets["PRAND"]
    # resolve outcomes (touch sets on M1 path; cross sets via forward close)
    for name, ev in sets.items():
        if name.startswith("X"):
            c_arr = np.asarray(m5["c"])
            for e in ev:
                t = e["bar"]
                res = {}
                for H in (3, 12, 48):
                    j = t + H
                    res[f"fwd_{H}"] = float(
                        (c_arr[j] - c_arr[t]) * e["side"]) \
                        if j < len(c_arr) else float("nan")
                e["res"] = res
            print(f"  {sym} {name}: resolved {len(ev)}", flush=True)
            continue
        for e in ev:
            e["res"] = resolve_event(m1, m5, e)
        print(f"  {sym} {name}: resolved {len(ev)}", flush=True)
    # level density diagnostic: median armed S1+S2 levels within +-2 ABR
    dens = {}
    return sets, d


def main():
    os.makedirs(os.path.join(K.OUT), exist_ok=True)
    all_ev = {}
    for sym in K.CORE:
        print(f"[M3] {sym} ...", flush=True)
        with K.pa_slots.slot(f"dr-market M3 {sym}", timeout=120):
            sets, d = build_symbol_events(sym)
        # save event tables (npz, compact)
        npz = {}
        for name, ev in sets.items():
            keys = ["bar", "day", "year", "utc_min", "cet_min", "dow",
                    "side", "level", "zlo", "zhi", "tol", "abr",
                    "approach_atr", "dist_cp", "age_bars", "lid", "kind",
                    "touch_no"]
            for kk in keys:
                npz[f"{name}__{kk}"] = np.array(
                    [e.get(kk, float("nan")) for e in ev],
                    dtype=np.float64)
            for kk in ("out_x1", "out_x2", "resbar_x1", "resbar_x2",
                       "overshoot_full", "overshoot_x1", "retreat_full",
                       "retreat_x1", "retest_12", "retest_48", "role_rev",
                       "fwd_3", "fwd_12", "fwd_48"):
                vals = []
                for e in ev:
                    v = e["res"].get(kk)
                    if isinstance(v, str):
                        vals.append({"BOUNCE": 0, "BREAK": 1, "NONE": 2}[v])
                    elif v is None:
                        vals.append(-1.0)
                    elif isinstance(v, bool):
                        vals.append(float(v))
                    else:
                        vals.append(float(v))
                npz[f"{name}__{kk}"] = np.array(vals, dtype=np.float64)
        path = os.path.join(K.OUT, f"m3_events_{sym}.npz")
        np.savez_compressed(path, **npz)
        sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print(f"  {sym} saved {path} sha={sha[:12]}", flush=True)
        all_ev[sym] = sets
    # analysis happens in mk_m3_analyze.py (separate step for clarity)
    print("[M3] extraction done.")


if __name__ == "__main__":
    main()
