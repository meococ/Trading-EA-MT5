"""dr_analyze.py -- DR-BOX (R64) hypothesis battery, null-first.

Design (stated before measuring, playbook 3.6):
  * Unit of analysis: one box golden (119 TUNE).  Pool: the panel's
    event-route candidates born <= j_tau ("available").  Label: cand's
    edges within tol_px(golden) of the golden's edges ("match").
  * Feature stat: mean(feature | match) - mean(feature | non-match)
    over all cells that have >=1 match and >=1 non-match.
  * Null A (label shuffle): within each such cell, reassign the match
    labels uniformly among the cell's available cands, count fixed;
    200 draws; report null p95 (and p5).
  * Null B (density-aware) for price-position features: pseudo-matches
    drawn with probability proportional to band-overlap coefficient
    vs the golden band (accounts for geometric near-duplicates).
  * Post-tau features are used ONLY as hypothesis tests (H-hind), never
    as selection features.
  * Ranking test (D4): per cell, the cand ranked first by feature
    (random tie-break, expected value); hit if it matches.  Null =
    uniform-random pick in the same pool.
"""
import sys, os, pickle, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = np.random.RandomState(20260923)

ROWS = pickle.load(open(os.path.join(HERE, "dr_rows.pkl"), "rb"))

# ---------------- feature table ----------------
# (name, direction so larger=more author-like, density-aware?)
FEATS = [
    ("px_in_box",        +1, True),
    ("close_at_box",     +1, True),     # in-band or <=0.5 ABR of edge
    ("neg_dist_edge",    +1, True),     # -dist_close_edge_abr
    ("neg_bars_touch",   +1, False),    # -bars_since_touch
    ("neg_age",          +1, False),    # -(j_tau-born): fresh birth
    ("pos_age",          +1, False),    # +(j_tau-born): old birth
    ("neg_t0",           +1, False),    # -t0: span starts early
    ("pos_span",         +1, False),    # +span_bars: long episode
    ("height",           +1, False),
    ("neg_h_abr",        +1, False),    # -height/abr (thin)
    ("pos_h_abr",        +1, False),    # +height/abr (tall)
    ("overlap_ratio",    +1, False),
    ("touches_min",      +1, False),
    ("touches_sum",      +1, False),
    ("n_swings",         +1, False),
    ("neg_compression",  +1, False),    # second-half range smaller
    ("px_frac_edge",     +1, True),     # close sits AT an edge (0 or 1)
    ("leg",              +1, False),
    ("prom",             +1, False),
    ("pairsep",          +1, False),
    ("route_rd",         +1, False),
    ("neg_round50",      +1, True),     # edge ON a 00/50 level
    ("neg_asia",         +1, True),     # edge ON the asia-range edge
    ("neg_dayext",       +1, True),     # edge ON day-so-far extreme
    ("neg_dayopen",      +1, True),     # edge ON the day open
    ("win_cover",        +1, False),    # share of window bars in band
    ("win_span",         +1, False),    # cand span / window bars
]

# post-tau test fields (H-hind only)
POST = ["brk_bar", "post_exc_abr", "brk_up_bar", "brk_dn_bar"]


def enrich(r):
    """Add derived feature values to each avail cand dict (in place)."""
    span_w = max(r["j_tau"] - r["jw0"], 1)
    for cd in r["pool"]:
        if not cd["avail"]:
            continue
        h_, l_ = cd["hi"], cd["lo"]
        px = r["px_tau"]
        cd["close_at_box"] = float(
            cd["px_in_box"] or
            min(abs(px - h_), abs(px - l_)) <= 0.5 * r["abr_tau"])
        cd["neg_dist_edge"] = -cd["dist_close_edge_abr"]
        cd["neg_bars_touch"] = -cd["bars_since_touch"]
        cd["neg_age"] = -cd["age_bars"]
        cd["pos_age"] = cd["age_bars"]
        cd["neg_t0"] = -cd["t0"]
        cd["pos_span"] = cd["span_bars"]
        cd["neg_h_abr"] = -cd["height"] / r["abr_tau"]
        cd["pos_h_abr"] = cd["height"] / r["abr_tau"]
        cd["touches_min"] = min(cd["touches_hi"], cd["touches_lo"])
        cd["touches_sum"] = cd["touches_hi"] + cd["touches_lo"]
        cd["neg_compression"] = -cd["compression"]
        pf = cd["px_frac"]
        cd["px_frac_edge"] = float(pf <= 0.15 or pf >= 0.85) \
            if 0.0 <= pf <= 1.0 else 0.0
        cd["route_rd"] = float(cd["route"] == "rd")
        cd["neg_round50"] = -cd["min_round50"]
        cd["neg_asia"] = -cd.get("min_asia", 9999)
        cd["neg_dayext"] = -min(cd["hi_dayext"], cd["lo_dayext"])
        cd["neg_dayopen"] = -min(cd["hi_dayopen"], cd["lo_dayopen"])
        # share of window bars [jw0, j_tau] whose range overlaps the band
        # (recomputed lazily in caller if needed; approximated by overlap)
        cd["win_cover"] = cd["overlap_ratio"]
        cd["win_span"] = cd["span_bars"] / span_w


def stat_diff(rows, feat):
    """mean(f|match) - mean(f|non-match) pooled over qualifying cells."""
    d = []
    for r in rows:
        pool = [c for c in r["pool"] if c["avail"]]
        ms = [c for c in pool if c["match"]]
        ot = [c for c in pool if not c["match"]]
        if not ms or not ot:
            continue
        fm = [c.get(feat) for c in ms if c.get(feat) is not None]
        fo = [c.get(feat) for c in ot if c.get(feat) is not None]
        if fm and fo:
            d.append((float(np.mean(fm)), float(np.mean(fo)),
                      len(ms), len(ot)))
    if not d:
        return None, 0
    return float(np.mean([a - b for a, b, _, _ in d])), len(d)


def shuffle_null(rows, feat, draws=200, weighted=False):
    """Null distribution of the diff stat."""
    stats = []
    for _ in range(draws):
        d = []
        for r in rows:
            pool = [c for c in r["pool"] if c["avail"]
                    and c.get(feat) is not None]
            n_m = sum(c["match"] for c in pool)
            if n_m == 0 or n_m == len(pool):
                continue
            if weighted:
                glo, ghi = r["g_lo"], r["g_hi"]
                w = []
                for c in pool:
                    inter = max(0.0, min(c["hi"], ghi)
                                - max(c["lo"], glo))
                    w.append(inter / max(c["hi"] - c["lo"], 1e-9))
                w = np.asarray(w, float)
                w = w / w.sum() if w.sum() else np.ones(len(pool)) / len(pool)
                idx = RNG.choice(len(pool), size=n_m, replace=False, p=w)
            else:
                idx = RNG.choice(len(pool), size=n_m, replace=False)
            pick = np.zeros(len(pool), bool)
            pick[idx] = True
            fm = [pool[i][feat] for i in range(len(pool)) if pick[i]]
            fo = [pool[i][feat] for i in range(len(pool)) if not pick[i]]
            d.append(np.mean(fm) - np.mean(fo))
        if d:
            stats.append(float(np.mean(d)))
    stats = np.asarray(stats)
    return (np.percentile(stats, 5), np.percentile(stats, 95),
            float(np.mean(stats)))


def rank1_recall(rows, feat, live_only=False):
    """Expected recall@1 (fractional ties) over reachable cells."""
    hits = 0.0
    n = 0
    for r in rows:
        pool = [c for c in r["pool"] if c["avail"]
                and c.get(feat) is not None]
        if live_only:
            pool = [c for c in pool
                    if c["px_in_box"] or c["dist_close_edge_abr"] <= 0.5]
        if not any(c["match"] for c in pool):
            continue
        n += 1
        v = np.array([c[feat] for c in pool], float)
        top = v == v.max()
        hits += float(np.mean([pool[i]["match"]
                               for i in np.where(top)[0]]))
    return hits, n


def random_pick_null(rows, live_only=False):
    return float(np.mean(
        [sum(c["match"] for c in r["pool"] if c["avail"]) /
         max(1, sum(c["avail"] for c in r["pool"]))
         for r in rows if any(c["match"] and c["avail"]
                              for c in r["pool"])]))


def main():
    rows = ROWS
    for r in rows:
        enrich(r)
    reach = [r for r in rows if r["n_match"]]
    print("cells with >=1 match:", len(reach), "of", len(rows))
    print("random-pick null recall@1: %.3f" % random_pick_null(rows))

    print("\n== feature diff stats (match - rest) vs nulls ==")
    print("%-16s %8s %6s | %-18s | %-18s | verdict"
          % ("feat", "obs", "ncell", "nullA p5/p95", "nullB p5/p95"))
    for name, sign, dens in FEATS:
        obs, nc = stat_diff(rows, name)
        if obs is None:
            continue
        lo, hi, mu = shuffle_null(rows, name)
        vb = ""
        if dens:
            lo2, hi2, mu2 = shuffle_null(rows, name, weighted=True)
            vb = "%.3f/%.3f" % (lo2, hi2)
            keep = obs > hi and obs > hi2
        else:
            vb = "-"
            keep = obs > hi or obs < lo
        print("%-16s %+8.3f %6d | %+.3f/%+.3f | %-18s | %s"
              % (name, obs, nc, lo, hi, vb, "KEEP" if keep else "drop"))

    print("\n== recall@1 by single feature (reachable cells) ==")
    for name, sign, dens in FEATS:
        h_all, n_all = rank1_recall(rows, name)
        h_lv, n_lv = rank1_recall(rows, name, live_only=True)
        print("%-16s all %5.1f/%d   live %5.1f/%d"
              % (name, h_all, n_all, h_lv, n_lv))


if __name__ == "__main__":
    main()
