"""c1_livedump.py — per-tau live-box dataset for the R40 queue.

For every scorable BOX golden, at its tau:
  - every live box-family object: score, route, edges, birth bar,
    feats (touches/prom_abr/contain/barrier/box_rank when present),
    meta fields, and whether it matches the golden (V2.match);
  - the golden's right-cand outcomes from cand_log;
  - whether a matching box is live (coverable) and its rank.

Output: boxlab/c1_runs/livedump_<variant>_<h8>.json — the training
set for the eventual engine-live ranker (§40.4.5) and the supersede
killtrace (§40.4.2).  Extraction only; no fitting here.

Usage: python c1_livedump.py [variant hash]  (default c1r_wd e62f2dc9)
"""
import collections
import glob
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import funnel as F                     # noqa: E402
import recall_at_k as RK               # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402

OUT = os.path.join(HERE, "c1_runs")


def _pkl(variant, h8, date, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h8, date, w1))
    if os.path.exists(f):
        return f
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (variant, h8, date, w1)))
    return g[0] if g else None


def _geom_feats(o, r):
    """Pull a compact feature row from the live record + object."""
    g = o.geometry if o is not None else {}
    sali = g.get("sali", {}) or {}
    feats = sali.get("feats", {}) or {}
    return {
        "score": r.get("score"),
        "route": r.get("why"),
        "lo": r.get("lo"), "hi": r.get("hi"),
        "t0": r.get("t0"), "t_birth": r.get("t_birth"),
        "touches": feats.get("touches"),
        "prom_abr": feats.get("prom_abr"),
        "contain": feats.get("contain"),
        "barrier": feats.get("barrier"),
        "box_rank": feats.get("box_rank",
                              g.get("meta_box_rank")),
        "deeper_lv": feats.get("deeper_lv"),
        "height": (r.get("hi") or 0) - (r.get("lo") or 0)
        if r.get("hi") is not None else None,
        "age": None if r.get("t_birth") is None else
        r.get("_tau", 0) - r["t_birth"],
    }


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "c1r_wd"
    h8 = sys.argv[2] if len(sys.argv) > 2 else "e62f2dc9"
    recs = C.load_tune()
    rows = []
    summ = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        ffull = _pkl(variant, h8, rec["date"], w1)
        if not ffull:
            continue
        efull = pickle.load(open(ffull, "rb"))
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        pairs_ = []
        for cd in efull.cand_log or []:
            if cd["kind"] == "LABEL_TF":
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is not None:
                pairs_.append((r, cd))
        bcands = [pr for pr in pairs_
                  if EV.FAMILY.get(pr[0]["type"]) == "box"]
        for gi, g in enumerate(g2):
            if g["spec_type"] != "BOX":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            ft = _pkl(variant, h8, rec["date"], tau)
            if not ft:
                continue
            e_t = pickle.load(open(ft, "rb"))
            live, _em = live_records(e_t, m, w0, tau)
            id2o = {ob.id: ob for ob in e_t.objects}
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
                r["_tau"] = tau
            smap = RK.score_map(e_t)
            ranked = RK.rank_live(live, smap)
            boxes = [r for r in ranked
                     if EV.FAMILY.get(r["type"]) == "box"]
            right = [(r, cd) for r, cd in bcands
                     if F.cand_right(g, r, m)]
            routs = collections.Counter(cd["outcome"]
                                        for _r, cd in right)
            match_rank = None
            brows = []
            for k, r in enumerate(boxes):
                ob = id2o.get(r["id"])
                hit = bool(V2.match(g, r, m))
                if hit and match_rank is None:
                    match_rank = k + 1
                fr = _geom_feats(ob, r)
                fr["rank"] = k + 1
                fr["match"] = hit
                brows.append(fr)
            summ["coverable" if match_rank else "uncoverable"] += 1
            if match_rank == 1:
                summ["hit@1"] += 1
            rows.append({
                "panel": rec["id"], "golden_i": gi, "tau": tau,
                "g_lo": g.get("price_lo"), "g_hi": g.get("price_hi"),
                "g_bs": g.get("build_start") or g.get("t0"),
                "g_be": g.get("build_end") or g.get("t1"),
                "n_live_box": len(boxes),
                "match_rank": match_rank,
                "right_outs": dict(routs),
                "right_best_sco": max(
                    (cd.get("score") for _r, cd in right
                     if cd.get("score") is not None), default=None),
                "boxes": brows})
    os.makedirs(OUT, exist_ok=True)
    outp = os.path.join(OUT, "livedump_%s_%s.json" % (variant, h8[:8]))
    json.dump({"variant": variant, "hash": h8, "rows": rows},
              open(outp, "w"), default=str)
    print("wrote %s" % outp)
    print("summary:", dict(summ))


if __name__ == "__main__":
    main()
