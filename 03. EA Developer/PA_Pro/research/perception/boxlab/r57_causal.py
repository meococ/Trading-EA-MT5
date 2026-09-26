#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""r57_causal.py — R57 §57.1 causal re-test of the null survivors.

H5-drawn used the golden's post-facto t1 -> hindsight.  The causal form
compares the RIGHT candidate vs the ENGINE'S WRONG PICK at tau on
quantities computable from bars <= tau:

  * bars_since_in_band   bars since close last inside band (0 = now)
  * px_in_box            close[tau] inside [bottom,top]
  * close_at_box         px_in_box OR dist_close_edge_abr <= X
                         (X = 0.5 ABR, stated before measurement)
  * dist_close_edge_abr  min(|px-edge|)/ABR
  * recency_bars         bars since cand t1 (age)
  * bars_since_touch     bars since any bar overlapped the band

And the survivor audit on the same causal footing:
  * prior_leg_abr (H4c)  h_rel_day (H6c)  h_abr (H10c)
  * pressure (H1c)       probes_top+bot (H3c)
  * ema_slope_span (H2c sanity)  overlap_ratio (H7c sanity)

Two paired designs per feature, each against a 200-draw within-cell
label-shuffle null:

  PAIRED   : cells with a right cand AND a wrong engine pick (n=12)
             delta_i = f(right) - f(pick); null draws a pseudo-right
             among the cell's non-right cands.
  VS-REST  : all cells with >=1 right cand (n=67)
             delta_i = mean f(right-set) - mean f(non-right);
             null shuffles the right set (same cardinality).
"""
import csv, os, sys, collections
import numpy as np

SEED = 20261202
DRAWS = 200
X_ABR = 0.5          # stated before measurement
HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "r_dataset", "rows.csv")


def fnum(r, k):
    try:
        return float(r.get(k) or "nan")
    except ValueError:
        return float("nan")


FEATS = {
    "bars_since_in_band":  lambda r: fnum(r, "bars_since_in_band"),
    "px_in_box":           lambda r: fnum(r, "px_in_box"),
    "close_at_box":        lambda r: float(fnum(r, "px_in_box") == 1.0
                                   or fnum(r, "dist_close_edge_abr") <= X_ABR),
    "neg_dist_edge_abr":   lambda r: -fnum(r, "dist_close_edge_abr"),
    "neg_recency":         lambda r: -fnum(r, "recency_bars"),
    "neg_bars_since_touch":lambda r: -fnum(r, "bars_since_touch"),
    "prior_leg_abr":       lambda r: fnum(r, "prior_leg_abr"),
    "h_rel_day":           lambda r: fnum(r, "h_rel_day"),
    "h_abr":               lambda r: fnum(r, "h_abr"),
    "pressure":            lambda r: fnum(r, "pressure"),
    "probes":              lambda r: fnum(r, "probes_top") + fnum(r, "probes_bot"),
    "neg_ema_slope_span":  lambda r: -fnum(r, "ema_slope_span"),
    "overlap_ratio":       lambda r: fnum(r, "overlap_ratio"),
}


def main():
    rows = list(csv.DictReader(open(ROWS, encoding="utf-8-sig")))
    cells = collections.defaultdict(list)
    for r in rows:
        cells[(r["panel"], r["tau"])].append(r)

    paired, vsrest = [], []
    for key, c in cells.items():
        right = [r for r in c if int(r["label_edge"]) >= 0]
        pick = [r for r in c if r["is_engine_pick"] == "1"
                and int(r["label_edge"]) < 0]
        others = [r for r in c if int(r["label_edge"]) < 0]
        if right and others:
            vsrest.append((right, others))
        if right and pick:
            paired.append((right, pick[0], others))
    print("cells=%d  paired=%d  vs-rest=%d" % (len(cells), len(paired), len(vsrest)))

    rng = np.random.default_rng(SEED)
    print("\n%-22s | %-26s | %-26s" % ("feature", "PAIRED (right-pick)", "VS-REST (right-rest)"))
    print("%-22s | %8s %8s %8s | %8s %8s %8s" %
          ("", "obs", "p95", "verd", "obs", "p95", "verd"))
    for name, fn in FEATS.items():
        # ---- PAIRED ----
        if paired:
            obs = np.mean([np.mean([fn(r) for r in right]) - fn(pk)
                           for right, pk, _o in paired])
            null = np.zeros(DRAWS)
            for d in range(DRAWS):
                s = 0.0
                for right, pk, others in paired:
                    pseudo = others[rng.integers(len(others))]
                    s += fn(pseudo) - fn(pk)
                null[d] = s / len(paired)
            p95p = np.percentile(null, 95)
            obs_p, p95_p, verd_p = obs, p95p, "KEEP" if obs > p95p else "drop"
        else:
            obs_p = p95_p = float("nan"); verd_p = "-"
        # ---- VS-REST ----
        cell_sets = vsrest
        obs = np.mean([np.mean([fn(r) for r in R]) - np.mean([fn(r) for r in O])
                       for R, O in cell_sets])
        pools = [(R + O, len(R)) for R, O in cell_sets]
        null = np.zeros(DRAWS)
        for d in range(DRAWS):
            s = 0.0
            for pool, k in pools:
                fv = np.array([fn(r) for r in pool])
                idx = rng.permutation(len(pool))
                s += fv[idx[:k]].mean() - fv[idx[k:]].mean()
            null[d] = s / len(pools)
        p95v = np.percentile(null, 95)
        verd_v = "KEEP" if obs > p95v else "drop"
        print("%-22s | %8.3f %8.3f %8s | %8.3f %8.3f %8s"
              % (name, obs_p, p95_p, verd_p, obs, p95v, verd_v))

    # ---- density-aware null for the price-position features (§57.1) ----
    # pseudo-right drawn ~ overlap-density: right cands sit where the
    # panel's proposal mass is dense, so a fair null must draw from the
    # same density profile, not uniformly.
    print("\ndensity-aware null (pseudo-right ~ band-overlap count):")
    for name in ("px_in_box", "close_at_box", "neg_dist_edge_abr"):
        fn = FEATS[name]
        obs = np.mean([np.mean([fn(r) for r in R]) - np.mean([fn(r) for r in O])
                       for R, O in cell_sets])
        null = np.zeros(DRAWS)
        dens = []
        for pool, k in pools:
            lo = np.array([fnum(r, "bottom") for r in pool])
            hi = np.array([fnum(r, "top") for r in pool])
            w = np.array([np.sum((lo <= hi[i]) & (hi >= lo[i]))
                          for i in range(len(pool))], float)
            dens.append((pool, k, w / w.sum()))
        for d in range(DRAWS):
            s = 0.0
            for pool, k, w in dens:
                fv = np.array([fn(r) for r in pool])
                idx = rng.choice(len(pool), size=k, replace=False, p=w)
                mask = np.ones(len(pool), bool); mask[idx] = False
                s += fv[idx].mean() - fv[mask].mean()
            null[d] = s / len(dens)
        p95d = np.percentile(null, 95)
        print("  %-20s obs %8.3f  dens-null p95 %8.3f  %s"
              % (name, obs, p95d, "KEEP" if obs > p95d else "drop"))


if __name__ == "__main__":
    main()
