"""DR_RULES_baselines.py — R77 s77.3 Part F: C-rules on PA-ATLAS baselines.

Read-only.  Runs bl_tdlines_k2 (lines) and bl_donchian_alt (levels) on
the same TUNE panels/golden-tau events as Parts B/C, computes the same
rule features (engine EMA25 / ABR20 units, engine swing-book pivots),
applies each preregistered variant as a selection filter, and re-counts
hits at budget + clutter.  Question per the contract: do the rules cut
their clutter while keeping their hits?

Baseline emit() receives its own causal ABR(50) (bl_common convention);
rule features use the pickled engine arrays (ema25/abr20/pivots) for
like-for-like comparison with Parts B/C.

Output: deepresearch/DR_RULES_baselines.json  (+ printed table)
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
for _p in (os.path.join(PERC, "evalcheck"), PERC,
           os.path.join(PERC, "practice", "baselines")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import common as C                      # noqa: E402
import eval as EV                       # noqa: E402
import eval_v2 as V2                    # noqa: E402
import cache as CA                      # noqa: E402
from snapshot import tau_of             # noqa: E402
from bl_common import _rec              # noqa: E402
from b_tdlines import emit as td_emit   # noqa: E402
from b_donchian import emit as dc_emit  # noqa: E402

import DR_RULES_measure as M            # noqa: E402

FAM_BUDGET = {"line": 2, "level": 1}
BASES = {"bl_tdlines_k2": (td_emit, "line"),
         "bl_donchian_alt": (dc_emit, "level")}


def feats(o, fam, j1, m, c, ema, abr, pivots, nfed):
    """Rule features for a live baseline object at bar j1."""
    jb = M.jle(m, o["birth"])
    f = {"c2_s": M.s_c2(j1, ema, abr)["c2_s"]}
    if fam == "level":
        p = o["price"]
        f["c1_abr"] = M.s_c1(p, p, j1, ema, abr)["c1_abr"]
        f["c1_pip"] = M.s_c1(p, p, j1, ema, abr)["c1_pip"]
        f["c7_sw"] = M.s_c7(jb, j1, c, abr, lambda j: p)["c7_sw"]
        a = M.s_c8(jb, j1, p, o["side"], pivots, abr)
        f["c8_beyond_abr"] = a["c8_beyond_abr"]
        ja = M.jle(m, o["birth_drawn"])
        a2 = M.s_c8(ja, j1, p, o["side"], pivots, abr)
        f["c8_beyond_abr_anch"] = a2["c8_beyond_abr"]
    elif fam == "line":
        p0, slope, tb = o["p0"], o["slope"], o["t0_bar"]
        lp = lambda j: p0 + slope * (j - tb)
        f["c7_sw"] = M.s_c7(jb, j1, c, abr, lp)["c7_sw"]
    return f


def passes(ft, fam, rv, thr):
    """same predicates as DR_RULES_report"""
    base, _, arg = rv.partition("@")
    if base == "C1":
        return ft["c1_abr"] is not None and ft["c1_abr"] <= float(arg)
    if base == "C1p":
        return ft["c1_pip"] is not None and ft["c1_pip"] <= float(arg)
    if base == "C2":
        s = ft["c2_s"]
        return s is not None and s <= thr["C2@%s" % fam][arg]
    if base == "C7":
        return ft["c7_sw"] is not None and ft["c7_sw"] <= int(arg)
    if base == "C8":
        b = ft["c8_beyond_abr"]
        return b is None or b < float(arg)
    if base == "C8a":
        b = ft["c8_beyond_abr_anch"]
        return b is None or b < float(arg)
    return True


def main():
    summ = json.load(open(os.path.join(HERE, "DR_RULES_summary.json")))
    thr = summ["thresholds"]
    recs = C.load_tune()
    out = {}
    for name, (emit, fam) in BASES.items():
        k = FAM_BUDGET[fam]
        variants = (["C1@0.5", "C1@1.0", "C1p@2", "C2@q95", "C2@q90",
                     "C7@2", "C7@3", "C8@1", "C8@2", "C8a@1", "C8a@2"]
                    if fam == "level" else
                    ["C2@q95", "C2@q90", "C7@2", "C7@3"])
        n_gold = n_hit0 = n_live = n_obj = 0
        hits = {rv: 0 for rv in variants}
        n_filt = {rv: 0 for rv in variants}
        clu0, cluF = [], {rv: [] for rv in variants}
        for rec in recs:
            w0 = rec["window"]["x0"]
            w1 = rec["window"]["x1"] or 1439
            t, m, o, h, l, c = CA.bars(rec["date"])
            abr50 = CA.abr(rec["date"])
            m = np.asarray(m); c = np.asarray(c)
            objs = emit(t, m, o, h, l, c, abr50) or []
            gobjs, _u, _to = EV.gold_objects(rec)
            g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
            # cumulative window-census clutter (published def)
            vis0 = [x for x in objs if x["birth"] <= w1 and
                    (x["die"] is None or x["die"] > w0)]
            # filter needs bar arrays: load engine pickle for features
            e = M.pickled(rec["date"], w1)
            clu0.append(len(vis0) / len(g2) if g2 else np.nan)
            # features per object at w1 for the census filter view
            if e is not None:
                ema = np.asarray(e.ema)
                abr20 = np.asarray(e.abr)
                pivots = e.book.seq
                mp = np.array([b["cet_min"] for b in e.bars])
                cp = np.array([b["c"] for b in e.bars])
                nfed = len(e.bars) - 1
                for rv in variants:
                    nfv = 0
                    for x in vis0:
                        if x["birth"] > w1:
                            continue
                        j1 = min(M.jle(mp, w1), nfed)
                        ft = feats(x, fam, j1, mp, cp, ema, abr20,
                                   pivots, nfed)
                        if passes(ft, fam, rv, thr):
                            nfv += 1
                    cluF[rv].append(nfv / len(g2) if g2 else np.nan)
            else:
                for rv in variants:
                    cluF[rv].append(np.nan)
            # per-tau events (golden scorable only, like bl_common)
            by_tau = collections.defaultdict(list)
            for g in g2:
                tau = tau_of(g)
                if tau is not None and tau >= w0:
                    by_tau[min(tau, w1)].append(g)
            e_cache = {}
            for tau, gs in sorted(by_tau.items()):
                if tau not in e_cache:
                    e_cache[tau] = M.pickled(rec["date"], tau)
                e = e_cache[tau]
                if e is None:
                    continue
                ema = np.asarray(e.ema)
                abr20 = np.asarray(e.abr)
                pivots = e.book.seq
                mp = np.array([b["cet_min"] for b in e.bars])
                cp = np.array([b["c"] for b in e.bars])
                nfed = len(e.bars) - 1
                live = [x for x in objs
                        if x["birth"] <= tau and
                        (x["die"] is None or x["die"] > tau)]
                jlast = min(M.jle(mp, tau), nfed)
                last_min = int(mp[jlast])
                recs_live = [_rec(x, w0, tau, last_min) for x in live]
                recs_live.sort(key=lambda r: (-r["_score"],
                                              -r["t_birth"]))
                recs_live = recs_live[:6]
                live_sorted = sorted(
                    live, key=lambda x: (-x["score"], -x["birth"]))[:6]
                fts = []
                j1 = min(M.jle(mp, tau), nfed)
                for x in live_sorted:
                    fts.append(feats(x, fam, j1, mp, cp, ema, abr20,
                                     pivots, nfed))
                top = recs_live  # single-family emit; budget k
                n_live += len(recs_live)
                n_obj += len(live)
                g_f = [g for g in gs
                       if EV.FAMILY.get(g["spec_type"]) == fam]
                n_gold += len(g_f)
                hit0 = sum(1 for g in g_f
                           if any(V2.match(g, er, mp)
                                  for er in top[:k]))
                n_hit0 += hit0
                for rv in variants:
                    keep = [r for r, ft in zip(recs_live, fts)
                            if ft is None or passes(ft, fam, rv, thr)]
                    n_filt[rv] += len(recs_live) - len(keep)
                    hits[rv] += sum(
                        1 for g in g_f
                        if any(V2.match(g, er, mp) for er in keep[:k]))
        def med(v):
            vv = [x for x in v if not np.isnan(x)]
            return float(np.median(vv)) if vv else None
        out[name] = {"fam": fam, "k": k, "n_gold": n_gold,
                     "hits0": n_hit0, "n_live": n_live,
                     "clutter0": med(clu0),
                     "variants": {rv: {"hits": hits[rv],
                                       "removed_live": n_filt[rv],
                                       "clutter": med(cluF[rv])}
                                  for rv in variants}}
        print("%s fam=%s gold=%d hits0=%d clutter0=%.2f live=%d"
              % (name, fam, n_gold, n_hit0, med(clu0), n_live))
        for rv in variants:
            v = out[name]["variants"][rv]
            print("  %-7s hits=%d (%+d) removed=%d/%d clutter=%.2f"
                  % (rv, v["hits"], v["hits"] - n_hit0,
                     v["removed_live"], n_live,
                     v["clutter"] if v["clutter"] else -1))
    with open(os.path.join(HERE, "DR_RULES_baselines.json"), "w",
              encoding="utf8") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
