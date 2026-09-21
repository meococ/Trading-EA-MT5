"""arrival_common — R02 arrival-matched design harness (OUTCOME-BLIND).

Question R02 asks: *when price arrives at a place, does it matter whether one
of our zones is there?*  Both arms come from ONE event-generating process:
arrival events on a zone-independent price grid laid at each server-day open.

This module computes ONLY event-level, <= t features.  No outcome column of
any kind exists here (no bounce/break/continuation, nothing past the event
bar).

Design decisions (pre-declared for R02; each marked Dn):

D1  GRID.  At the first bar of each server day (``t // 86400`` rollover on the
    M5 bar-open time), lay a grid of bands of width ``w_p`` at spacing
    ``w_p`` whose edges sit at ``anchor + k * w_p``, covering
    ``anchor +- SPAN_ATR * A(day-open bar)``.  ``w_p = u_g * w_scale * A``
    where ``u_g`` is generator g's median armed-zone width in ATR units and
    ``A`` is ATR14(H1) at the day-open bar.  Anchor = day open (primary) or
    previous day close (sensitivity).  The grid is fixed for the day and
    causal (depends only on the day-open bar and ATR known at that bar).
D2  ARRIVAL EVENT on band G at bar t (t inside the grid's day): bar t's range
    intersects G; no bar in ``[t-24, t-1]`` intersects G; at least one bar in
    that window has close distance ``max(glo - c_j, c_j - ghi) >= 1.0 * A(t)``;
    side from ``c_{t-1}`` (``-1`` if ``<= glo``, ``+1`` if ``>= ghi``, else
    reject); ``A(t)`` valid; bar t not warm-up.  The 24-bar lookback may cross
    the day boundary: G is a fixed price interval, and intersections of the
    interval before the grid was laid still count as touches (identical to the
    R01 semantics where a zone's band exists before the event).
D3  ARMS (LEAD RULING R02-C1-1/2 — labels from the CLOSE OF BAR t-1).
    Let ``gap(Z, G) = max(glo - z_hi, z_lo - ghi, 0)`` for zone Z of
    generator g, evaluated at ``tp = t - 1`` so the event being measured
    can never decide which arm it lands in.
    TREATED  iff an ARMED zone overlaps G at tp
             (``armed_views_cached(tp)``, the R01 parity path).
    CONTROL  iff NO LIVE zone of g (``active_at_fast(tp)`` — armed or
             not, broken or intact) lies within ``margin * w_p`` of G.
    EXCLUDED-MIDDLE otherwise (a live zone nearby but no armed overlap) —
    counted, reported, and used in the secondary T/X/C contrast
    ("armed / something there but not armed / genuinely nothing").
    Days with zero live zones produce CONTROL events (min gap = inf).
D4  FEATURES (all <= t): ``approach_atr`` = max close distance from G in
    ``[t-24, t-1]`` / ``A(t)`` (>= 1 by construction); ``since_touch`` =
    bars since the last bar intersecting G, capped at 1440 (>= 24 by
    freshness) — DIAGNOSTIC ONLY (R02-C1-4); ``since_near`` = bars since
    the last bar whose range intersected ``[mid - w_p/2, mid + w_p/2]``,
    capped at 1440 — the symmetric recency covariate computable
    identically in both arms; ``anchor_dist`` = ``|mid - anchor| / A``
    (A of the grid's day-open bar) — band distance from the day anchor
    (R02-C1-3); ``atr`` = A(t); ``hour_bucket`` = ``utc_min // 240``
    (6 x 4h); ``pos_r5`` = ``(mid_G - r5_lo) / (r5_hi - r5_lo)`` over
    ``[t-1440, t-1]``.
D5  STRATA / COMMON SUPPORT: ``side x approach-decile x atr-decile x
    hour_bucket x anchor-dist-decile``; co-primary adds a
    ``since_near`` tercile.  Deciles/terciles over pooled
    treated+control events per (generator, symbol, w_scale, anchor).
    ``support_T`` = share of treated events whose stratum contains >= 1
    control; ``support_C`` = share of control events whose stratum
    contains >= 1 treated.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PA_PRO = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_PA_PRO, "lib"),
           os.path.join(_PA_PRO, "struct", "zones"),
           os.path.join(_PA_PRO, "research", "physics")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

__all__ = ["DAY", "FRESH", "AWAY_ATR", "SPAN_ATR", "R5_BARS", "SINCE_CAP",
           "HOUR_MIN", "MARGINS", "day_segments", "armed_width_atr",
           "build_day_grid", "arrival_events", "tag_arms", "stratify",
           "common_support", "dist_summary"]

DAY = 86400
FRESH = 24                  # identical to phys_common.FRESH_BARS
AWAY_ATR = 1.0              # identical to phys_common.AWAY_ATR
SPAN_ATR = 5.0              # grid covers +-5 x A(day-open)
R5_BARS = 1440              # 5-day range window
SINCE_CAP = 1440            # since_touch cap
HOUR_MIN = 240              # 4-hour buckets for strata
MARGINS = (0.5, 1.0, 2.0)   # margin multipliers x w_p


def day_segments(bars):
    """[(d0, d1)] inclusive bar indices of each server day (t // 86400)."""
    t = np.asarray(bars["t"], dtype=np.int64)
    day = t // DAY
    edges = np.flatnonzero(np.concatenate(([True], day[1:] != day[:-1])))
    seg = []
    for i, s in enumerate(edges):
        e = int(edges[i + 1] - 1) if i + 1 < len(edges) else len(t) - 1
        seg.append((int(s), int(e)))
    return seg


def armed_width_atr(src, step=288):
    """Median armed-zone width in ATR units, sampled every `step` bars."""
    vals = []
    for t in range(0, src.n, int(step)):
        A = src.atr_of(t)
        if not np.isfinite(A) or A <= 0:
            continue
        for (_zid, lo, hi, _S) in src.armed_views_cached(t):
            if hi > lo:
                vals.append((hi - lo) / A)
    return float(np.median(vals)) if vals else float("nan"), len(vals)


def build_day_grid(anchor, A, u_atr, w_scale=1.0, span_atr=SPAN_ATR):
    """Band edges at anchor + k*w_p covering anchor +- span_atr*A.

    Returns (bands=[(glo,ghi)...], w_p).  Anchor is a band EDGE."""
    if not np.isfinite(A) or A <= 0 or not np.isfinite(u_atr) or u_atr <= 0:
        return [], float("nan")
    w_p = float(u_atr) * float(w_scale) * float(A)
    k = int(np.ceil(span_atr * A / w_p))
    k = min(k, 400)                       # safety cap
    edges = float(anchor) + np.arange(-k, k + 1, dtype=np.float64) * w_p
    return [(float(edges[i]), float(edges[i + 1]))
            for i in range(len(edges) - 1)], w_p


def _close_dist(glo, ghi, cwin):
    return np.maximum(glo - cwin, cwin - ghi)


def arrival_events(bars, ctx, grids):
    """Arrival events on per-day grids.  `grids`: list aligned with
    day_segments -> (bands, w_p, day_idx) or None for a skipped day.

    Returns (events, counters).  Events carry only <= t features."""
    import pa_clock

    l = np.asarray(bars["l"], dtype=np.float64)
    h = np.asarray(bars["h"], dtype=np.float64)
    c = np.asarray(bars["c"], dtype=np.float64)
    warm = np.asarray(bars.get("warmup", np.zeros(len(l), dtype=bool)),
                      dtype=bool)
    utc_min = np.asarray(bars["utc_min"], dtype=np.int64)
    t_arr = np.asarray(bars["t"], dtype=np.int64)
    years = pa_clock.server_year(t_arr + 300)
    events = []
    counters = {"days": 0, "days_no_atr": 0, "bands": 0, "cand": 0,
                "skip_fresh": 0, "skip_no_away": 0, "skip_side": 0,
                "skip_atr": 0, "skip_warm": 0}
    for di, ((d0, d1), gr) in enumerate(zip(day_segments(bars), grids)):
        if gr is None:
            counters["days_no_atr"] += 1
            continue
        bands, w_p, _di, anchor, A_day = gr
        counters["days"] += 1
        counters["bands"] += len(bands)
        lo_b = max(0, d0 - SINCE_CAP)
        seg0 = d0 - lo_b
        for (glo, ghi) in bands:
            mid = 0.5 * (glo + ghi)
            ins = (l[lo_b:d1 + 1] <= ghi) & (h[lo_b:d1 + 1] >= glo)
            nlo, nhi = mid - 0.5 * w_p, mid + 0.5 * w_p
            ins_n = (l[lo_b:d1 + 1] <= nhi) & (h[lo_b:d1 + 1] >= nlo)
            nz_near = np.flatnonzero(ins_n)
            seg = ins[seg0:]
            prev = np.concatenate(([ins[seg0 - 1] if seg0 > 0 else False],
                                   seg[:-1]))
            nz_all = np.flatnonzero(ins)
            for k_rel in np.flatnonzero(seg & ~prev):
                t = d0 + int(k_rel)
                k = t - lo_b
                counters["cand"] += 1
                w0 = max(0, k - FRESH)
                if ins[w0:k].any():
                    counters["skip_fresh"] += 1
                    continue
                A = float(ctx.a(t))
                if not np.isfinite(A) or A <= 0:
                    counters["skip_atr"] += 1
                    continue
                if warm[t]:
                    counters["skip_warm"] += 1
                    continue
                win = slice(max(lo_b, t - FRESH), t)
                d = _close_dist(glo, ghi, c[win])
                dmax = float(d.max()) if d.size else 0.0
                if not (dmax >= AWAY_ATR * A):
                    counters["skip_no_away"] += 1
                    continue
                cp = c[t - 1]
                if cp <= glo:
                    side = -1
                elif cp >= ghi:
                    side = +1
                else:
                    counters["skip_side"] += 1
                    continue
                p = int(np.searchsorted(nz_all, k) - 1)
                since = (t - int(lo_b + nz_all[p])) if p >= 0 else SINCE_CAP
                since = min(since, SINCE_CAP)
                pn = int(np.searchsorted(nz_near, k) - 1)
                since_n = (t - int(lo_b + nz_near[pn])) if pn >= 0 \
                    else SINCE_CAP
                since_n = min(since_n, SINCE_CAP)
                r0 = max(0, t - R5_BARS)
                if r0 < t:
                    r5lo = float(l[r0:t].min())
                    r5hi = float(h[r0:t].max())
                    pos = ((mid - r5lo) / (r5hi - r5lo)
                           if r5hi > r5lo else float("nan"))
                else:
                    pos = float("nan")
                events.append({
                    "day_i": di, "bar_idx": int(t), "bar_t": int(t_arr[t]),
                    "year": int(years[t]),
                    "utc_min": int(utc_min[t]),
                    "hour_bucket": int(utc_min[t] // HOUR_MIN),
                    "side": int(side), "glo": float(glo), "ghi": float(ghi),
                    "mid": mid, "w_p": float(w_p),
                    "atr": float(A), "approach_atr": dmax / A,
                    "since_touch": int(since), "since_near": int(since_n),
                    "anchor_dist": (abs(mid - anchor) / A_day
                                    if np.isfinite(A_day) and A_day > 0
                                    else float("nan")),
                    "pos_r5": float(pos),
                    "dist_cp": abs(mid - cp) / A,
                })
    return events, counters


def tag_arms(events, src, margins=MARGINS, bars=None):
    """Tag each event treated/control/excluded per margin multiplier.

    R02-C1: labels are computed from the zone state at bar ``t-1``
    (``tp = bar_idx - 1``) so the measured bar can never decide its own
    arm.  TREATED = an ARMED zone overlaps G at tp; CONTROL = NO LIVE
    zone of the generator (armed or not) within ``margin * w_p``;
    EXCLUDED = anything between.  Each treated event also records
    ``zone_S`` = max strength among the armed zones overlapping G
    (pre-declared multi-overlap rule; controls carry ``zone_S=None``).

    When ``bars`` is given, each treated event also records
    ``zone_fresh`` (R02-C1 FRESH-TO-ZONE): True iff NO armed zone
    overlapping G was intersected by any bar's range in ``[t-24, t-1]``
    (zone band taken at tp).  ``zone_fresh`` is None for controls.

    Returns {margin_mult: {"treated": idx, "control": idx,
    "excluded": idx}} plus diagnostic counters.
    """
    l_arr = h_arr = None
    if bars is not None:
        l_arr = np.asarray(bars["l"], dtype=np.float64)
        h_arr = np.asarray(bars["h"], dtype=np.float64)
    live_gap = []     # min gap over LIVE zones at tp (inf = no live zone)
    arm_ov = []       # any ARMED zone overlaps G at tp
    arm_S = []        # max S among overlapping armed zones (None else)
    for e in events:
        glo, ghi = e["glo"], e["ghi"]
        t = int(e["bar_idx"])
        tp = t - 1
        live = src.active_at_fast(tp) if tp >= 0 else []
        if live:
            tp_arr = np.asarray([tp], dtype=np.int64)
            lg = min(float(max(glo - float(zh[0]), float(zl[0]) - ghi,
                               0.0))
                     for z in live
                     for zl, zh in [src.band_range(z, tp_arr)])
        else:
            lg = float("inf")
        live_gap.append(lg)
        ov = [(z_lo, z_hi, S, zid) for (zid, z_lo, z_hi, S)
              in src.armed_views_cached(tp)
              if max(glo - z_hi, z_lo - ghi, 0.0) == 0.0]
        arm_ov.append(bool(ov))
        arm_S.append(float(max(s for _l, _h, s, _z in ov)) if ov else None)
        e["zone_zid"] = (max(ov, key=lambda r: (r[2], -r[3]))[3]
                         if ov else None)
        e["cover"] = (float(max(min(ghi, zh) - max(glo, zl)
                                for zl, zh, _s, _z in ov)) / e["w_p"]
                      if ov else None)
        if bars is not None and ov:
            w0 = max(0, t - FRESH)
            e["zone_fresh"] = not any(
                bool(((l_arr[w0:t] <= zh) & (h_arr[w0:t] >= zl)).any())
                for zl, zh, _s, _z in ov)
        elif bars is not None:
            e["zone_fresh"] = None
    for i, e in enumerate(events):
        e["zone_S"] = arm_S[i]
    out = {}
    for m in margins:
        tr, ct, ex = [], [], []
        for i, e in enumerate(events):
            if arm_ov[i]:
                tr.append(i)
            elif live_gap[i] > m * e["w_p"]:
                ct.append(i)
            else:
                ex.append(i)
        out[float(m)] = {"treated": tr, "control": ct, "excluded": ex}
    diag = {"no_live_events": int(sum(1 for g in live_gap
                                    if g == float("inf"))),
            "overlap_events": int(sum(arm_ov)),
            "live_near_not_armed": int(sum(
                1 for i, e in enumerate(events)
                if not arm_ov[i] and live_gap[i] <= 0.5 * e["w_p"])),
            "treated_zone_stale": (int(sum(
                1 for e in events
                if e.get("zone_fresh") is False)) if bars is not None
                else None)}
    return out, diag


def _deciles(x, n=10):
    q = np.quantile(np.asarray(x, dtype=np.float64), np.linspace(0, 1, n + 1))
    q[0], q[-1] = -np.inf, np.inf
    return q


def stratify(events, keep_idx, fine=False, since_bins=3, anch_bins=10):
    """Stratum key per event: (side, approach-decile, atr-decile,
    hour, anchor-dist-bin)  — R02-C1-3 adds anchor_dist to BOTH keys.

    fine=True adds a `since_near` bin (tercile by default) — the
    symmetric recency covariate (R02-C1-4), NOT band-level since_touch.
    anch_bins/since_bins control the anchor-distance and recency
    granularity (frozen spec: 10 and 3).
    """
    idx = list(keep_idx)
    da = _deciles([events[i]["approach_atr"] for i in idx])
    dr = _deciles([events[i]["atr"] for i in idx])
    dd = _deciles([events[i]["anchor_dist"] for i in idx], n=anch_bins)
    ds = (_deciles([events[i]["since_near"] for i in idx], n=since_bins)
          if fine else None)
    keys = {}
    for i in idx:
        e = events[i]
        a = int(np.searchsorted(da, e["approach_atr"], side="right") - 1)
        r = int(np.searchsorted(dr, e["atr"], side="right") - 1)
        d = int(np.searchsorted(dd, e["anchor_dist"], side="right") - 1)
        k = (e["side"], a, r, e["hour_bucket"], d)
        if fine:
            s = int(np.searchsorted(ds, e["since_near"], side="right") - 1)
            k = k + (s,)
        keys[i] = k
    return keys, da, dr, ds, dd


def common_support(events, treated_idx, control_idx, fine=False,
                   since_bins=3, anch_bins=10):
    """Share of treated events whose stratum has >=1 control, and vice versa."""
    keys, da, dr, ds, dd = stratify(
        events, list(treated_idx) + list(control_idx), fine=fine,
        since_bins=since_bins, anch_bins=anch_bins)
    tset = {keys[i] for i in treated_idx}
    cset = {keys[i] for i in control_idx}
    sup_t = (float(np.mean([keys[i] in cset for i in treated_idx]))
             if len(treated_idx) else float("nan"))
    sup_c = (float(np.mean([keys[i] in tset for i in control_idx]))
             if len(control_idx) else float("nan"))
    out = {"support_T": sup_t, "support_C": sup_c,
           "n_strata_T": len(tset), "n_strata_C": len(cset),
           "dist_edges": da.tolist(), "atr_edges": dr.tolist(),
           "anch_edges": dd.tolist()}
    if fine:
        out["since_edges"] = ds.tolist()
    return out


def dist_summary(events, idx):
    """Median/p10/p90 of the D4 features over the given event indices."""
    idx = list(idx)
    if not idx:
        return {}
    def q(key):
        v = np.asarray([events[i][key] for i in idx], dtype=np.float64)
        v = v[np.isfinite(v)]
        if not v.size:
            return None
        return [float(np.percentile(v, 10)), float(np.median(v)),
                float(np.percentile(v, 90))]
    out = {"n": len(idx)}
    for key in ("approach_atr", "since_touch", "since_near", "atr",
                "pos_r5", "dist_cp", "anchor_dist", "cover", "zone_S"):
        out[key] = q(key)
    hb = np.asarray([events[i]["hour_bucket"] for i in idx])
    out["hour_share"] = [float((hb == b).mean()) for b in range(6)]
    return out
