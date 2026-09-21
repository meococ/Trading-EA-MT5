"""arrival_contrast — R02-D identifiable contrasts (OUTCOME-BLIND).

R02's binary "marked vs unmarked" contrast failed positivity by
construction (FINDING_1). The round pivots to contrasts where BOTH
arms are zone arrivals, so overlap is structural rather than hoped
for:

E1  STRENGTH (primary): among arrivals at ARMED zones of generator g
    (zone state at t-1, per R02-C1), does the TOP strength tercile
    behave differently from the BOTTOM? Contrast variable = tercile of
    `zone_S` (max strength over armed zones overlapping G at tp);
    middle tercile excluded from the contrast, reported separately.

E2  CROSS-GENERATOR (secondary): for unordered pair {g,h}, arrivals at
    a band marked by g but not h versus marked by h but not g.
    "Marked by g" = an ARMED zone of g overlaps G at tp; "not marked
    by h" additionally requires NO LIVE zone of h (armed or not)
    overlapping G at tp. The pair runs on the FINER of the two grids
    (smaller u_atr — more bands, more events); declared, not chosen
    per-pair.

Propensity machinery (PINNED, R02-D §4): unpenalized IRLS logistic
regression of the arm indicator on
    [approach_atr, anchor_dist, log(A), sin(2*pi*utc_min/1440),
     cos(2*pi*utc_min/1440), since_near, pos_r5]
features standardized inside the fit (mu/sd carried with the model);
fitted per symbol per generator (per pair for E2). ATT weights:
w_A = 1, w_B = e/(1-e). Trimming: keep e in [0.05, 0.95] in BOTH arms
(trimmed share reported); control weights winsorized at their own 99th
percentile within the cell. Balance gate: |SMD| <= 0.10 on ALL seven
features after weighting, checked BEFORE the freeze.

Residual-strength confirmatory (PINNED, R02-E §3 + R02-E2): `zone_S`
is regressed (unpenalized OLS, standardized features) on the seven
propensity features plus `zone_touches` (the argmax armed zone's own
`touches` count at tp), per symbol per generator over the pooled
treated set; the identical top-vs-bottom tercile contrast is then run
on the RESIDUALS — the part of the score recency cannot explain.
Attenuation guard (R02-E2): the regression's R-squared is reported
next to every residual result; a cell with R2 >= 0.90 retains no
usable residual signal and its residual confirmatory is declared
UNDERPOWERED-BY-CONSTRUCTION in advance — a null there is
uninformative and may never be quoted as evidence that the score is
a recency proxy. The 0.90 threshold and the 0.05 `since_near` claim
gate are fixed blind and may not move after an outcome is seen.

This module computes ONLY event-level, <= t features. No outcome
column exists here.
"""

import numpy as np

import arrival_common as ac

__all__ = ["FEATURES", "E3_FEATURES", "build_X", "fit_logit",
           "predict_logit", "att_weights", "smd", "balance_report",
           "e1_arms", "e3_arms", "attach_touches", "resid_strength",
           "resid_arms", "tag_pair", "live_overlap_tables",
           "table_overlap"]

FEATURES = ("approach_atr", "anchor_dist", "log_atr",
            "sin_hour", "cos_hour", "since_near", "pos_r5", "side")

# R02-H SS3 + R02-J SS1: E3 propensity/balance set = FEATURES minus
# the treatment itself (zone_since_touch, zone_fresh) plus
# zone_touches.  since_near is back IN: it is band-level proximity
# (price loitering near the location), not the zone's own retest
# recency.  zone_touches is IN: validation COUNT, not recency.
# zone_S is deliberately OUT (R02-J SS2): s_rec is a component of the
# score, so zone_S is a CONSEQUENCE of the treatment — conditioning
# on it would strip the effect being measured and open a collider
# path.  Reported as a diagnostic, never a covariate.
E3_FEATURES = ("approach_atr", "anchor_dist", "log_atr",
               "sin_hour", "cos_hour", "since_near", "pos_r5",
               "side", "zone_touches")

RECENCY_FEATURES = ("since_near", "zone_since_touch", "zone_fresh")
RECENCY_GATE = 0.05               # claim sub-gate on recency features
SINCE_CAP = 1440                  # zone_since_touch cap (M5 bars, 5d)

TRIM_LO, TRIM_HI = 0.05, 0.95     # propensity overlap window (frozen)
WINSOR_Q = 0.99                   # control-weight cap quantile (frozen)
SMD_GATE = 0.10                   # balance gate (frozen)


def _feat(name, e):
    if name == "sin_hour":
        return np.sin(2.0 * np.pi * (e["utc_min"] / 1440.0))
    if name == "cos_hour":
        return np.cos(2.0 * np.pi * (e["utc_min"] / 1440.0))
    if name == "log_atr":
        return np.log(e["atr"])
    return float(e[name])


def build_X(events, idx, feats=FEATURES):
    """Feature matrix for the propensity model, pinned order.
    R02-G item 1: `side` (+1/-1 arrival direction) is feature 8 of
    FEATURES — in the model AND in the balance gate.  `feats` selects
    the column set (E3 passes E3_FEATURES)."""
    cols = [np.fromiter((_feat(f, events[i]) for i in idx),
                       dtype=np.float64, count=len(idx))
            for f in feats]
    return np.column_stack(cols) if cols else np.empty((len(idx), 0))


def fit_logit(X, y, max_iter=100, tol=1e-9):
    """Unpenalized IRLS logistic regression on standardized features.

    Returns dict(beta, mu, sd) — predict via predict_logit. Linear
    predictor clipped to +-30 for stability (declared)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0.0] = 1.0
    Z = np.column_stack([np.ones(X.shape[0]), (X - mu) / sd])
    beta = np.zeros(Z.shape[1])
    for _ in range(int(max_iter)):
        eta = np.clip(Z @ beta, -30.0, 30.0)
        p = 1.0 / (1.0 + np.exp(-eta))
        w = np.maximum(p * (1.0 - p), 1e-9)
        g = Z.T @ (y - p)
        H = (Z.T * w) @ Z
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        beta = beta + step
        if float(np.max(np.abs(step))) < tol:
            break
    return {"beta": beta, "mu": mu, "sd": sd}


def predict_logit(model, X):
    X = np.asarray(X, dtype=np.float64)
    Z = np.column_stack([np.ones(X.shape[0]),
                         (X - model["mu"]) / model["sd"]])
    eta = np.clip(Z @ model["beta"], -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-eta))


def att_weights(ps, y, lo=TRIM_LO, hi=TRIM_HI, winsor_q=WINSOR_Q):
    """ATT weights with frozen trimming. y=1 is the arm whose effect is
    estimated (for E1: top tercile; for E2: generator g's arm).

    Returns (w, keep): w_A = 1, w_B = e/(1-e) winsorized at the kept
    controls' `winsor_q` quantile; keep = e in [lo, hi] (both arms).
    """
    ps = np.asarray(ps, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    keep = (ps >= lo) & (ps <= hi)
    w = np.where(y > 0.5, 1.0, ps / np.maximum(1.0 - ps, 1e-9))
    wc = w[(y < 0.5) & keep]
    if wc.size:
        cap = float(np.quantile(wc, winsor_q))
        w = np.where((y < 0.5), np.minimum(w, cap), w)
    return w, keep


def smd(X, y, w=None, names=FEATURES):
    """Per-feature |SMD| between arms y=1 vs y=0 (weighted if w given).
    SMD = |m1 - m0| / sqrt((v1 + v0) / 2), unweighted variances."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if w is None:
        w = np.ones(len(y))
    out = {}
    for j, name in enumerate(names):
        x, ww = X[:, j], w
        m1 = float(np.sum(ww[y > 0.5] * x[y > 0.5])
                   / max(np.sum(ww[y > 0.5]), 1e-12))
        m0 = float(np.sum(ww[y < 0.5] * x[y < 0.5])
                   / max(np.sum(ww[y < 0.5]), 1e-12))
        v1 = float(np.var(x[y > 0.5])) if (y > 0.5).any() else 0.0
        v0 = float(np.var(x[y < 0.5])) if (y < 0.5).any() else 0.0
        denom = np.sqrt(max(0.5 * (v1 + v0), 1e-12))
        out[name] = abs(m1 - m0) / denom
    return out


def balance_report(events, idx_a, idx_b, feats=FEATURES):
    """Fit propensity for arm A (y=1) vs arm B (y=0) on `feats`;
    report pre/post-weighting max |SMD|, trimmed shares, and
    propensity range overlap. idx_a = treated-equivalent arm."""
    idx = list(idx_a) + list(idx_b)
    y = np.asarray([1.0] * len(idx_a) + [0.0] * len(idx_b))
    X = build_X(events, idx, feats)
    if len(idx_a) < 50 or len(idx_b) < 50:
        return {"n_a": len(idx_a), "n_b": len(idx_b), "skipped": True}
    model = fit_logit(X, y)
    ps = predict_logit(model, X)
    smd_pre = smd(X, y, names=feats)
    w, keep = att_weights(ps, y)
    kept_a = int((keep & (y > 0.5)).sum())
    kept_b = int((keep & (y < 0.5)).sum())
    saturated = kept_a < 50 or kept_b < 50   # a pass on ~no data is not a pass
    smd_post = (smd(X[keep], y[keep], w[keep], names=feats)
                if not saturated else {f: float("nan")
                                       for f in feats})
    e_a, e_b = ps[y > 0.5], ps[y < 0.5]
    lo = max(float(e_a.min()), float(e_b.min()))
    hi = min(float(e_a.max()), float(e_b.max()))
    return {"n_a": len(idx_a), "n_b": len(idx_b),
            "smd_pre": float(max(smd_pre.values())),
            "smd_post": float(max(smd_post.values())),
            "smd_post_by_feature": smd_post,
            "smd_pre_by_feature": smd_pre,
            "trim_share_a": float(1.0 - keep[y > 0.5].mean()),
            "trim_share_b": float(1.0 - keep[y < 0.5].mean()),
            "e_range_a": [float(e_a.min()), float(e_a.max())],
            "e_range_b": [float(e_b.min()), float(e_b.max())],
            "overlap_share": float(np.mean((ps >= lo) & (ps <= hi))),
            "kept_a": kept_a, "kept_b": kept_b,
            "saturated": saturated,
            "gate_pass": bool(not saturated and
                              max(smd_post.values()) <= SMD_GATE),
            "_w": w, "_keep": keep, "_ps": ps}


def recency_report(events, idx_a, idx_b, rep):
    """R02-G item 2 claim sub-gate: weighted |SMD| on the zone-recency
    set {since_near, zone_since_touch, zone_fresh} under the SAME
    fitted propensity weights (rep["_w"], rep["_keep"] from
    balance_report on the same arms). gate_pass requires all three
    <= RECENCY_GATE (0.05). zone_fresh enters as its share (0/1)."""
    idx = list(idx_a) + list(idx_b)
    y = np.asarray([1.0] * len(idx_a) + [0.0] * len(idx_b))
    keep = rep["_keep"]
    w = rep["_w"]
    out = {}
    for name in RECENCY_FEATURES:
        x = np.asarray([float(events[i].get(name) if
                            events[i].get(name) is not None else np.nan)
                        for i in idx])
        xk, yk, wk = x[keep], y[keep], w[keep]
        ok = ~np.isnan(xk)
        xk, yk, wk = xk[ok], yk[ok], wk[ok]
        m1 = float(np.sum(wk[yk > 0.5] * xk[yk > 0.5])
                   / max(np.sum(wk[yk > 0.5]), 1e-12))
        m0 = float(np.sum(wk[yk < 0.5] * xk[yk < 0.5])
                   / max(np.sum(wk[yk < 0.5]), 1e-12))
        v1 = float(np.var(xk[yk > 0.5])) if (yk > 0.5).any() else 0.0
        v0 = float(np.var(xk[yk < 0.5])) if (yk < 0.5).any() else 0.0
        out[name] = abs(m1 - m0) / np.sqrt(max(0.5 * (v1 + v0), 1e-12))
    return {"smd_by_feature": {k: float(v) for k, v in out.items()},
            "max_smd": float(max(out.values())),
            "gate_pass": bool(max(out.values()) <= RECENCY_GATE)}


def e1_arms(events, treated_idx, bounds):
    """E1 contrast arms: top vs bottom `zone_S` tercile among treated
    events (bounds from estimate.tercile_bounds, pre-outcome). Middle
    tercile excluded, returned for reporting."""
    q33, q67 = bounds
    idx = np.asarray(list(treated_idx))
    s = np.asarray([events[i].get("zone_S") for i in idx],
                   dtype=object)
    sv = np.asarray([float(x) if x is not None else np.nan
                     for x in s], dtype=np.float64)
    ok = ~np.isnan(sv)
    return {"top": idx[ok & (sv > q67)].tolist(),
            "mid": idx[ok & (sv > q33) & (sv <= q67)].tolist(),
            "bot": idx[ok & (sv <= q33)].tolist()}


def e3_arms(events, treated_idx, bounds):
    """E3 contrast arms (R02-H SS3): among armed-overlap treated
    events, split on `zone_since_touch` terciles.  arm "recent"
    (y=1) = BOTTOM tercile (touched recently); "stale" = TOP tercile
    (touched long ago / never); middle descriptive.  bounds =
    (q33, q67) of pooled treated zone_since_touch, pre-outcome.
    Degenerate bounds (q33 >= q67, e.g. all zones capped at
    SINCE_CAP) yield empty arms — the cell is non-evaluable."""
    q33, q67 = bounds
    if not (q33 < q67):
        return {"recent": [], "mid": [], "stale": [],
                "degenerate": True}
    idx = np.asarray(list(treated_idx))
    sv = np.asarray([float(events[i]["zone_since_touch"])
                     if events[i].get("zone_since_touch") is not None
                     else np.nan for i in idx], dtype=np.float64)
    ok = ~np.isnan(sv)
    # stale uses >= so a probability mass AT SINCE_CAP (never/long-ago
    # touched) lands in the stale arm, where it semantically belongs,
    # instead of being silently dropped.
    return {"recent": idx[ok & (sv <= q33)].tolist(),
            "mid": idx[ok & (sv > q33) & (sv < q67)].tolist(),
            "stale": idx[ok & (sv >= q67)].tolist(),
            "degenerate": False}


def attach_touches(events, src):
    """Set zone-level attributes on every event with a `zone_zid`,
    from `state_at(z, tp)` — the argmax armed zone's own history at
    labelling time (R02-E §3, R02-G item 2):
    `zone_touches`    = its `touches` count;
    `zone_since_touch`= min(tp - last_touch, SINCE_CAP) bars since its
                        last touch (never-touched -> SINCE_CAP)."""
    zmap = {r[0]: r[6] for r in src.zones()}
    for e in events:
        zid = e.get("zone_zid")
        if zid is None:
            continue
        z = zmap.get(zid)
        if z is None:
            continue
        tp = int(e["bar_idx"]) - 1
        st = src.state_at(z, tp)
        e["zone_touches"] = int(st.get("touches", 0))
        lt = st.get("last_touch")
        e["zone_since_touch"] = (float(min(tp - int(lt), SINCE_CAP))
                                 if lt is not None else float(SINCE_CAP))


def resid_xprep(events, base):
    """Precompute the residual-OLS design (FEATURES + zone_touches +
    zone_since_touch + zone_fresh) and the zone_S target over `base`
    once; a replicate then gathers rows by position instead of
    rebuilding from event dicts.  Pure per-row transforms — identical
    values; the standardization still happens per-fit on the resampled
    subset.  Returns (X_all, pos_of_event_idx, s_all) over exactly the
    base rows that carry all required attributes (membership in `pos`
    IS the attribute filter)."""
    rows = [i for i in base
            if events[i].get("zone_S") is not None
            and events[i].get("zone_touches") is not None
            and events[i].get("zone_since_touch") is not None
            and events[i].get("zone_fresh") is not None]
    if not rows:
        return np.empty((0, len(FEATURES) + 3)), {}, \
            np.empty(0, dtype=np.float64)
    X = build_X(events, rows)
    extra = np.asarray([[float(events[i]["zone_touches"]),
                         float(events[i]["zone_since_touch"]),
                         1.0 if events[i]["zone_fresh"] else 0.0]
                        for i in rows], dtype=np.float64)
    X = np.column_stack([X, extra])
    y = np.asarray([float(events[i]["zone_S"]) for i in rows],
                   dtype=np.float64)
    pos = {i: p for p, i in enumerate(rows)}
    return X, pos, y


def resid_strength(events, idx, return_diag=False, xp=None):
    """Residual strength (R02-E §3 + R02-G item 2, PINNED):
    unpenalized OLS of `zone_S` on the eight propensity features plus
    `zone_touches`, `zone_since_touch` and `zone_fresh` — the argmax
    armed zone's own retest history at tp, so "the part recency
    cannot explain" is actually true. Features standardized inside
    the fit; returns {event_idx: residual} for idx rows that have
    zone_S and all zone attributes. OLS linear predictor not clipped.

    With ``return_diag=True`` returns (resid, diag) where diag carries
    the R02-E2 attenuation diagnostics: `r2` = R-squared of the
    strength ~ covariates regression (share of the score that recency
    and geometry already explain) and `resid_var_share` =
    var(residual)/var(zone_S) = 1 - r2.  A cell with r2 >= 0.90 has no
    usable residual signal to test (pre-declared threshold)."""
    if xp is None:
        rows = [i for i in idx
                if events[i].get("zone_S") is not None
                and events[i].get("zone_touches") is not None
                and events[i].get("zone_since_touch") is not None
                and events[i].get("zone_fresh") is not None]
        if not rows:
            return ({}, {"r2": float("nan"),
                         "resid_var_share": float("nan"),
                         "n": 0}) if return_diag else {}
        X = build_X(events, rows)
        extra = np.asarray([[float(events[i]["zone_touches"]),
                             float(events[i]["zone_since_touch"]),
                             1.0 if events[i]["zone_fresh"] else 0.0]
                            for i in rows], dtype=np.float64)
        X = np.column_stack([X, extra])
        y = np.asarray([float(events[i]["zone_S"]) for i in rows],
                       dtype=np.float64)
    else:
        X_all, pos, s_all = xp
        rows = [i for i in idx if i in pos]
        if not rows:
            return ({}, {"r2": float("nan"),
                         "resid_var_share": float("nan"),
                         "n": 0}) if return_diag else {}
        sel = [pos[i] for i in rows]
        X, y = X_all[sel], s_all[sel]
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0.0] = 1.0
    Z = np.column_stack([np.ones(X.shape[0]), (X - mu) / sd])
    beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
    r = y - Z @ beta
    resid = {i: float(ri) for i, ri in zip(rows, r)}
    if not return_diag:
        return resid
    vy = float(np.var(y))
    share = float(np.var(r) / vy) if vy > 0 else float("nan")
    return resid, {"r2": (1.0 - share) if share == share else float("nan"),
                   "resid_var_share": share, "n": len(rows)}


def resid_arms(resid, idx, bounds):
    """Same tercile-arm structure as e1_arms but on residual values.
    bounds = (q33, q67) of pooled residuals, computed pre-outcome."""
    q33, q67 = bounds
    ida = np.asarray(list(idx))
    sv = np.asarray([resid.get(i, np.nan) for i in ida],
                    dtype=np.float64)
    ok = ~np.isnan(sv)
    return {"top": ida[ok & (sv > q67)].tolist(),
            "mid": ida[ok & (sv > q33) & (sv <= q67)].tolist(),
            "bot": ida[ok & (sv <= q33)].tolist()}


def _overlap_any(zones_bands, glo, ghi):
    """True iff any (zl, zh) band overlaps [glo, ghi]."""
    for zl, zh in zones_bands:
        if zl <= ghi and zh >= glo:
            return True
    return False


def live_overlap_tables(src, tps):
    """Per-tp live-zone band tables for fast overlap queries.

    `tps`: sorted unique array of bar indices to cover.  Returns
    {tp: (sorted_lo, sorted_hi)} over zones live at tp
    (`created_idx <= tp`, `born_idx <= tp`, `end_idx >= tp`), bands
    from `band_range` (the zone's band AT tp).  Computed with one
    vectorized `band_range` call per zone — shared across all pairs
    that query this generator.
    """
    tps = np.asarray(sorted(set(int(t) for t in tps)), dtype=np.int64)
    recs = src._index_arrays() or []
    T = len(tps)
    tables = {}
    if not recs or T == 0:
        return tables
    created = np.asarray([int(r[6].created_idx) for r in recs],
                         dtype=np.int64)
    born = np.asarray([int(r[6].born_idx) for r in recs],
                      dtype=np.int64)
    end = np.asarray([int(r[6].end_idx) for r in recs], dtype=np.int64)
    live = ((created[:, None] <= tps[None, :])
            & (born[:, None] <= tps[None, :])
            & (end[:, None] >= tps[None, :]))
    CH = 4096
    for c0 in range(0, T, CH):
        tt = tps[c0:c0 + CH]
        los = np.empty((len(recs), len(tt)))
        his = np.empty((len(recs), len(tt)))
        for zi, r in enumerate(recs):
            lo, hi = src.band_range(r[6], tt)
            los[zi], his[zi] = lo, hi
        for j in range(len(tt)):
            m = live[:, c0 + j]
            tables[int(tt[j])] = (np.sort(los[m, j]),
                                  np.sort(his[m, j]))
    return tables


def table_overlap(entry, glo, ghi):
    """True iff any live zone band overlaps [glo, ghi].
    entry = (sorted_lo, sorted_hi): overlap exists iff
    #(lo <= ghi) + #(hi >= glo) > N (pigeonhole on the two sets)."""
    lo_s, hi_s = entry
    n = lo_s.shape[0]
    if n == 0:
        return False
    a = int(np.searchsorted(lo_s, ghi, side="right"))
    b = n - int(np.searchsorted(hi_s, glo, side="left"))
    return a + b > n


def tag_pair(events, src_g, src_h, bars=None,
             live_tab_g=None, live_tab_h=None):
    """E2 arms on the (finer) grid already used to make `events`.

    Per event, zone state at tp = t-1 for BOTH generators:
      arm 'g' = armed_g overlaps G AND no live_h zone overlaps G;
      arm 'h' = armed_h overlaps G AND no live_g zone overlaps G;
      'x'   = everything else (both mark it, neither does, or the
              other generator's live structure sits on the band).
    Records per event: `zone_S_g`/`zone_S_h` (max armed overlap
    strength), `zone_fresh_g`/`zone_fresh_h` (own-zone untouched in
    [t-24,t-1]) when bars given.
    """
    l_arr = h_arr = None
    if bars is not None:
        l_arr = np.asarray(bars["l"], dtype=np.float64)
        h_arr = np.asarray(bars["h"], dtype=np.float64)
    out = {"g": [], "h": [], "x": []}
    for i, e in enumerate(events):
        glo, ghi = e["glo"], e["ghi"]
        t = int(e["bar_idx"])
        tp = t - 1
        if tp < 0:
            out["x"].append(i)
            continue
        ov_g = [(zl, zh, S) for (_z, zl, zh, S)
                in src_g.armed_views_cached(tp)
                if zl <= ghi and zh >= glo]
        ov_h = [(zl, zh, S) for (_z, zl, zh, S)
                in src_h.armed_views_cached(tp)
                if zl <= ghi and zh >= glo]
        e["zone_S_g"] = (float(max(s for _l, _h, s in ov_g))
                         if ov_g else None)
        e["zone_S_h"] = (float(max(s for _l, _h, s in ov_h))
                         if ov_h else None)
        if bars is not None:
            w0 = max(0, t - ac.FRESH)
            for tag, ov in (("g", ov_g), ("h", ov_h)):
                e[f"zone_fresh_{tag}"] = (
                    None if not ov else not any(
                        bool(((l_arr[w0:t] <= zh)
                              & (h_arr[w0:t] >= zl)).any())
                        for zl, zh, _s in ov))
        # armed subset of live for the same gen, so ov_g & ov_h -> x
        # without any live lookup; live check runs only when needed.
        def _live(src, tab):
            if tab is not None:
                ent = tab.get(tp)
                return table_overlap(ent, glo, ghi) if ent else False
            tp_arr = np.asarray([tp], dtype=np.int64)
            return _overlap_any(
                [(float(zl[0]), float(zh[0]))
                 for z in src.active_at_fast(tp)
                 for zl, zh in [src.band_range(z, tp_arr)]], glo, ghi)
        if ov_g and ov_h:
            out["x"].append(i)
        elif ov_g and not _live(src_h, live_tab_h):
            out["g"].append(i)
        elif ov_h and not _live(src_g, live_tab_g):
            out["h"].append(i)
        else:
            out["x"].append(i)
    return out
