"""arrival_estimate — R02 stratified ATT estimator (PINNED, R02-C1-5).

Every degree of freedom below is a frozen choice, quoted sentence-for-
sentence by `rounds/R02/PREREG.md` section 6:

* Stratum key (primary): ``(side, approach-decile, atr-decile,
  hour_bucket, anchor-dist-decile)``; co-primary adds a ``since_near``
  tercile.  Edges are computed ONCE on the pooled treated+control events
  of each (generator, symbol) cell and are reused unchanged inside every
  bootstrap replicate.
* Common-support set: strata containing >= 1 treated AND >= 1 control
  event.  Events outside it are dropped and the dropped share per arm is
  reported.
* ``omega_s`` = n_T,s / n_T(CS)  (treated share; sums to 1 on the CS set).
* Outcome value per event: 1.0 / 0.0 conditional on resolution
  (BOUNCE=1, BREAK=0; CONT=1, RETURN=0; NONE/DROPPED excluded from the
  proportion — raw shares reported alongside, never hidden).
* ``D_sym = sum_s omega_s * (p_T,s - p_C,s)`` per (generator, symbol).
* Headline ``D_g = sum_sym w_sym * D_sym`` with
  ``w_sym = n_T,sym(CS) / sum_sym n_T,sym(CS)``.
* CI: percentile (2.5/97.5) bootstrap clustered by server day
  (``day_i``), B = 10,000, seed 20260920; days resampled independently
  per symbol for the pooled CI.
* ``D_top``: treated events whose ``zone_S`` (max strength among
  overlapping armed zones at t-1) falls in the TOP tercile of the pooled
  treated ``zone_S`` for that (generator, symbol) — tercile bounds are
  computed BEFORE any outcome join and recorded in FREEZE.json — versus
  ALL control events sharing their strata (common support recomputed on
  the restricted treated set).  D_mid / D_bot likewise.
* Monotone gate: ``D_bot <= D_mid <= D_top``.

This module NEVER touches bars — it consumes event rows and precomputed
outcome labels only.  It may be unit-tested on synthetic data; it must
not be run on real data before the R02 freeze.
"""

import numpy as np

import arrival_common as ac

__all__ = ["tercile_bounds", "assign_terciles", "att_cell",
           "bootstrap_ci", "pool_cells", "att_weighted",
           "bootstrap_weighted", "bootstrap_resid", "bootstrap_e3",
           "bootstrap_pooled", "resid_D", "e3_D"]

BOOT_B = 10000
BOOT_SEED = 20260920


def _pack_boots(boots):
    """R02-K B1a: every bootstrap_* RETAINS its replicate array and
    returns dict(lo, hi, p, n_boot, boots).  p = one-sided
    (1 + #{D_b <= 0}) / (n_boot + 1) — the pinned recipe, identical
    for every experiment."""
    b = np.asarray(boots, dtype=np.float64)
    if b.size == 0:
        return {"lo": float("nan"), "hi": float("nan"),
                "p": float("nan"), "n_boot": 0, "boots": b}
    return {"lo": float(np.percentile(b, 2.5)),
            "hi": float(np.percentile(b, 97.5)),
            "p": float((1.0 + np.sum(b <= 0.0)) / (b.size + 1.0)),
            "n_boot": int(b.size), "boots": b}


def tercile_bounds(events, treated_idx):
    """(q33, q67) of pooled treated zone_S — computed BEFORE outcomes."""
    s = [events[i]["zone_S"] for i in treated_idx
         if events[i].get("zone_S") is not None]
    if not s:
        return (float("nan"), float("nan"))
    q = np.quantile(np.asarray(s, dtype=np.float64), [1 / 3, 2 / 3])
    return float(q[0]), float(q[1])


def assign_terciles(events, treated_idx, bounds):
    """Tag treated events 'bot'/'mid'/'top' by frozen bounds."""
    q33, q67 = bounds
    for i in treated_idx:
        s = events[i].get("zone_S")
        events[i]["tercile"] = ("na" if s is None or s != s else
                                "bot" if s <= q33 else
                                "mid" if s <= q67 else "top")


def _strata(events, treated_idx, control_idx, fine):
    keys, *_ = ac.stratify(events, list(treated_idx) + list(control_idx),
                           fine=fine)
    return keys


def _att_from_keys(events, values, treated_idx, control_idx, keys):
    """Stratified ATT on a fixed key assignment.  Returns
    (D, n_T_used, n_C_used)."""
    tset, cset = {}, {}
    for i in treated_idx:
        tset.setdefault(keys[i], []).append(i)
    for i in control_idx:
        cset.setdefault(keys[i], []).append(i)
    cs = [s for s in tset if s in cset]
    n_t = sum(len(tset[s]) for s in cs)
    if n_t == 0:
        return float("nan"), 0, 0
    D = 0.0
    n_c = 0
    for s in cs:
        ti, ci = tset[s], cset[s]
        n_c += len(ci)
        yt = [values[i] for i in ti if values[i] is not None]
        yc = [values[i] for i in ci if values[i] is not None]
        if not yt or not yc:
            continue
        D += (len(ti) / n_t) * (float(np.mean(yt)) - float(np.mean(yc)))
    return D, n_t, n_c


def att_cell(events, values, treated_idx, control_idx, fine=False,
             tercile=None):
    """One cell estimate.  `values`: per-event 1.0/0.0/None outcome.
    `tercile`: None|'bot'|'mid'|'top' restricts the treated arm (D_top
    semantics); controls are then all controls sharing the restricted
    strata."""
    if tercile is not None:
        treated_idx = [i for i in treated_idx
                       if events[i].get("tercile") == tercile]
    keys = _strata(events, treated_idx, control_idx, fine)
    D, n_t, n_c = _att_from_keys(events, values, treated_idx,
                                 control_idx, keys)
    return {"D": D, "n_T": n_t, "n_C": n_c,
            "dropped_T": len(treated_idx) - n_t,
            "dropped_C": len(control_idx) - n_c}


def _day_pos(carr, uniq):
    """cluster-id -> position array; makes the per-replicate gather O(n)
    instead of O(n_clusters x n).  Identical output to the flatnonzero
    scan it replaces (positions within each day stay sorted, and the
    concatenation order follows `pick`)."""
    return {d: np.flatnonzero(carr == d) for d in uniq}


def bootstrap_ci(events, values, treated_idx, control_idx, fine=False,
                 tercile=None, cluster=None, B=BOOT_B, seed=BOOT_SEED):
    """Cluster percentile CI.  `cluster`: cluster id per event index —
    default e['day_i'] (server day); the pre-declared robustness rerun
    passes e['bar_t'] // 604800 (server week).  Strata fixed from the
    observed sample."""
    if tercile is not None:
        treated_idx = [i for i in treated_idx
                       if events[i].get("tercile") == tercile]
    treated_idx, control_idx = list(treated_idx), list(control_idx)
    keys = _strata(events, treated_idx, control_idx, fine)
    idx_all = treated_idx + control_idx
    if cluster is None:
        cluster = [events[i]["day_i"] for i in idx_all]
    day_arr = np.asarray(cluster)
    uniq = np.unique(day_arr)
    d2p = _day_pos(day_arr, uniq)
    rng = np.random.default_rng(seed)
    boots = []
    t_mask = np.zeros(len(idx_all), dtype=bool)
    t_mask[:len(treated_idx)] = True
    for _ in range(int(B)):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([d2p[d] for d in pick])
        bidx = [idx_all[j] for j in sel]
        bmask = t_mask[sel]
        bt = [i for i, m in zip(bidx, bmask) if m]
        bc = [i for i, m in zip(bidx, bmask) if not m]
        bkeys = {i: keys[i] for i in bidx}
        d, n_t, _ = _att_from_keys(events, values, bt, bc, bkeys)
        if np.isfinite(d) and n_t > 0:
            boots.append(d)
    return _pack_boots(boots)


def pool_cells(cells):
    """Headline D across symbols: treated-share-weighted mean of
    per-symbol D.  `cells`: {symbol: att_cell dict}."""
    ws = {s: c["n_T"] for s, c in cells.items()}
    tot = sum(ws.values())
    if tot == 0:
        return float("nan")
    return float(sum(c["D"] * ws[s] for s, c in cells.items()) / tot)


# --- R02-D: propensity-weighted ATT (primary estimator for E1/E2) ---
#
# Frozen spec (PREREG §6): unpenalized IRLS logistic of the arm
# indicator on arrival_contrast.FEATURES (7 covariates, standardized
# inside the fit), fitted per symbol per generator (per pair for E2).
# Arm A (y=1) is the arm whose effect is estimated — E1: top strength
# tercile; E2: generator g's arm. Weights w_A=1, w_B=e/(1-e); trim
# e outside [0.05, 0.95] in both arms (trimmed share reported);
# control weights winsorized at their own 99th percentile within the
# cell. The outcome mean is over RESOLVED events only, using the
# fitted weights (same conditional-on-resolution semantics as the
# stratified estimator). Bootstrap refits the model inside EVERY
# replicate, clustered by `cluster` (server day; week as declared
# robustness).


def _xprep(events, values, base, feats):
    """Precompute X/val over `base` once; replicates then index rows by
    position instead of rebuilding the design matrix from event dicts.
    Returns (X_all, pos_of_event_idx, val_all).  build_X is a pure
    per-row transform, so X_all[pos] equals build_X over the subset —
    identical values, and fit_logit re-standardizes the resampled rows
    exactly as before."""
    import arrival_contrast as cc
    feats = cc.FEATURES if feats is None else feats
    X = cc.build_X(events, list(base), feats)
    pos = {i: p for p, i in enumerate(base)}
    val = np.asarray([np.nan if values[i] is None else float(values[i])
                      for i in base])
    return X, pos, val


def _att_core(X, y, val, feats):
    """IRLS propensity -> trim/winsorize -> weighted arm means on the
    resolved set.  Shared by _weighted_att_at and the cached replicate
    path; identical math."""
    import arrival_contrast as cc
    model = cc.fit_logit(X, y)
    ps = cc.predict_logit(model, X)
    w, keep = cc.att_weights(ps, y)
    out = {"D": float("nan"), "n_A": 0, "n_B": 0,
           "trim_a": float(1.0 - keep[y > 0.5].mean())
           if (y > 0.5).any() else float("nan"),
           "trim_b": float(1.0 - keep[y < 0.5].mean())
           if (y < 0.5).any() else float("nan"),
           "smd_post": float(max(cc.smd(X[keep], y[keep],
                                        w[keep], names=feats).values()))
                     if keep.any() else float("nan")}
    ok = np.isfinite(val)
    means = {}
    for arm, mv in ((1.0, y > 0.5), (0.0, y < 0.5)):
        m = mv & keep & ok
        den = float(np.sum(w[m]))
        means[arm] = (float(np.sum(w[m] * val[m])) / den
                      if den > 0 else float("nan"))
        out["n_A" if arm else "n_B"] = int(m.sum())
    out["D"] = means[1.0] - means[0.0]
    return out


def _weighted_att_at(events, values, idx_a, idx_b, feats=None,
                     xp=None):
    import arrival_contrast as cc
    feats = cc.FEATURES if feats is None else feats
    idx = list(idx_a) + list(idx_b)
    y = np.asarray([1.0] * len(idx_a) + [0.0] * len(idx_b))
    if xp is None:
        X = cc.build_X(events, idx, feats)
        val = np.asarray([np.nan if values[i] is None
                          else float(values[i]) for i in idx])
    else:
        X_all, pos, val_all = xp
        sel = [pos[i] for i in idx]
        X, val = X_all[sel], val_all[sel]
    return _att_core(X, y, val, feats)


def att_weighted(events, values, idx_a, idx_b, feats=None):
    """Propensity-weighted ATT for one cell (E1: top-vs-bot tercile;
    E2: g-arm vs h-arm; E3: recent-vs-stale on E3_FEATURES).
    See module spec above."""
    return _weighted_att_at(events, values, idx_a, idx_b, feats=feats)


def bootstrap_weighted(events, values, idx_a, idx_b, cluster=None,
                       B=BOOT_B, seed=BOOT_SEED, progress=None):
    """Cluster percentile CI for the propensity-weighted ATT; the
    propensity model is REFIT inside every replicate."""
    idx_all = list(idx_a) + list(idx_b)
    if cluster is None:
        cluster = [events[i]["day_i"] for i in idx_all]
    carr = np.asarray(cluster)
    uniq = np.unique(carr)
    d2p = _day_pos(carr, uniq)
    xp = _xprep(events, values, idx_all, None)
    rng = np.random.default_rng(seed)
    is_a = np.zeros(len(idx_all), dtype=bool)
    is_a[:len(idx_a)] = True
    boots = []
    for i in range(int(B)):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        if progress is not None and (i & 255) == 0:
            progress(i)
        sel = np.concatenate([d2p[c] for c in pick])
        rows = [idx_all[j] for j in sel]
        ba = [i for i, m in zip(rows, is_a[sel]) if m]
        bb = [i for i, m in zip(rows, is_a[sel]) if not m]
        if not ba or not bb:
            continue
        d = _weighted_att_at(events, values, ba, bb, xp=xp)["D"]
        if np.isfinite(d):
            boots.append(d)
    return _pack_boots(boots)


def bootstrap_resid(events, values, treated_idx, cluster=None,
                    B=BOOT_B, seed=BOOT_SEED, progress=None):
    """Cluster percentile CI for the RESIDUAL-strength confirmatory
    (R02-G item 6, pinned): EVERY replicate refits the residual OLS on
    the resampled treated set, recomputes residual tercile bounds,
    rebuilds top/bottom arms, refits the propensity model, then takes
    the weighted ATT.  Nothing fitted survives across replicates."""
    import arrival_contrast as cc
    idx_all = list(treated_idx)
    if cluster is None:
        cluster = [events[i]["day_i"] for i in idx_all]
    carr = np.asarray(cluster)
    uniq = np.unique(carr)
    d2p = _day_pos(carr, uniq)
    xp = _xprep(events, values, idx_all, None)
    xpr = cc.resid_xprep(events, idx_all)
    rng = np.random.default_rng(seed)
    boots = []
    for i in range(int(B)):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        if progress is not None and (i & 255) == 0:
            progress(i)
        sel = np.concatenate([d2p[c] for c in pick])
        rows = [idx_all[j] for j in sel]
        d = resid_D(events, values, rows, xp=xp, xpr=xpr)
        if np.isfinite(d):
            boots.append(d)
    return _pack_boots(boots)


def bootstrap_e3(events, values, treated_idx, cluster=None,
                 B=BOOT_B, seed=BOOT_SEED, progress=None):
    """Cluster percentile CI for E3 (R02-H SS3, pinned): EVERY
    replicate recomputes the zone_since_touch tercile bounds on the
    resampled treated set, rebuilds recent/stale arms, and refits the
    propensity on E3_FEATURES (zone-level recency excluded — it is the
    treatment; since_near + zone_touches are in per R02-J).  Nothing
    fitted survives across replicates."""
    import arrival_contrast as cc
    idx_all = list(treated_idx)
    if cluster is None:
        cluster = [events[i]["day_i"] for i in idx_all]
    carr = np.asarray(cluster)
    uniq = np.unique(carr)
    d2p = _day_pos(carr, uniq)
    xp = _xprep(events, values, idx_all, cc.E3_FEATURES)
    rng = np.random.default_rng(seed)
    boots = []
    for i in range(int(B)):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        if progress is not None and (i & 255) == 0:
            progress(i)
        sel = np.concatenate([d2p[c] for c in pick])
        rows = [idx_all[j] for j in sel]
        d = e3_D(events, values, rows, xp=xp)
        if np.isfinite(d):
            boots.append(d)
    return _pack_boots(boots)


def resid_D(events, values, rows, xp=None, xpr=None):
    """One replicate of the residual-strength D on `rows`: refit the
    residual OLS, recompute tercile bounds, rebuild top/bot arms,
    refit propensity on FEATURES, weighted ATT.  NaN if not fittable."""
    import arrival_contrast as cc
    resid = cc.resid_strength(events, rows, xp=xpr)
    vals = list(resid.values())
    if len(vals) < 150:
        return float("nan")
    q = np.quantile(np.asarray(vals), [1.0 / 3.0, 2.0 / 3.0])
    arms = cc.resid_arms(resid, rows, (float(q[0]), float(q[1])))
    if not arms["top"] or not arms["bot"]:
        return float("nan")
    return _weighted_att_at(events, values, arms["top"],
                            arms["bot"], xp=xp)["D"]


def e3_D(events, values, rows, xp=None):
    """One replicate of the E3 recency D on `rows`: recompute
    zone_since_touch tercile bounds, rebuild recent/stale arms, refit
    propensity on E3_FEATURES, weighted ATT.  NaN if degenerate."""
    import arrival_contrast as cc
    vals = np.asarray([events[i]["zone_since_touch"] for i in rows
                       if events[i].get("zone_since_touch")
                       is not None], dtype=np.float64)
    if vals.size < 150:
        return float("nan")
    q = np.quantile(vals, [1.0 / 3.0, 2.0 / 3.0])
    arms = cc.e3_arms(events, rows, (float(q[0]), float(q[1])))
    if arms["degenerate"] or not arms["recent"] or not arms["stale"]:
        return float("nan")
    return _weighted_att_at(events, values, arms["recent"],
                            arms["stale"], feats=cc.E3_FEATURES,
                            xp=xp)["D"]


def _cell_rep_D(cell, kind, sel_pos, xp=None, xpr=None):
    """Dispatch one replicate D for a pooled-bootstrap cell.
    sel_pos = positions (into the cell's index list) drawn this
    replicate."""
    if kind == "pair":
        rows = [cell["idx_all"][j] for j in sel_pos]
        ba = [i for i, m in zip(rows, cell["is_a"][sel_pos]) if m]
        bb = [i for i, m in zip(rows, cell["is_a"][sel_pos]) if not m]
        if not ba or not bb:
            return float("nan")
        return _weighted_att_at(cell["events"], cell["values"],
                                ba, bb, xp=xp)["D"]
    rows = [cell["treated"][j] for j in sel_pos]
    if kind == "resid":
        return resid_D(cell["events"], cell["values"], rows,
                       xp=xp, xpr=xpr)
    return e3_D(cell["events"], cell["values"], rows, xp=xp)


def bootstrap_pooled(cells, kind, B=BOOT_B, seed=BOOT_SEED,
                     progress=None):
    """R02-K B1c — the pooled generator-level bootstrap the family unit
    requires.  `cells`: list of dicts, one per CONTRIBUTING
    symbol-cell, each carrying its own {"events", "values"} plus
    "treated" (resid/e3) or {"idx_all","is_a"} (pair) and "w" = its
    observed sample-size weight.  Every replicate resamples DAY
    clusters independently within each cell, recomputes that cell's D
    through the full refit chain (OLS+terciles+propensity for resid,
    terciles+propensity for e3, propensity for pair), then takes the
    fixed-weight mean of the per-cell D's.  Returns _pack_boots
    (replicates retained; p by the pinned one-sided recipe)."""
    import arrival_contrast as cc
    feats = cc.E3_FEATURES if kind == "e3" else None
    rng = np.random.default_rng(seed)
    prepped = []
    for c in cells:
        base = c["treated"] if kind != "pair" else c["idx_all"]
        carr = np.asarray(c.get("cluster") or
                          [c["events"][i]["day_i"] for i in base])
        uniq = np.unique(carr)
        prepped.append({"c": c, "base": list(base), "uniq": uniq,
                        "d2p": _day_pos(carr, uniq),
                        "xp": _xprep(c["events"], c["values"], base,
                                     feats),
                        "xpr": (cc.resid_xprep(c["events"], base)
                                if kind == "resid" else None)})
    boots = []
    for i in range(int(B)):
        if progress is not None and (i & 255) == 0:
            progress(i)
        num = den = 0.0
        for p in prepped:
            if p["uniq"].size == 0:
                continue
            pick = rng.choice(p["uniq"], size=len(p["uniq"]),
                              replace=True)
            sel = np.concatenate([p["d2p"][cl] for cl in pick])
            d = _cell_rep_D(p["c"], kind, sel, xp=p["xp"],
                            xpr=p["xpr"])
            if np.isfinite(d):
                num += p["c"]["w"] * d
                den += p["c"]["w"]
        if den > 0:
            boots.append(num / den)
    return _pack_boots(boots)
