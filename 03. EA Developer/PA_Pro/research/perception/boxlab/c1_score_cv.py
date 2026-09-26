"""c1_score_cv.py — leave-one-day-out check for box.rank_score.

Queue item 2 (§34.8.2.2): "run a leave-one-day-out check that the
engine's score reproduces the lab ranking."  Uses the same day-level
folds as LEVEL-LAB V8 / boxlab cv_eval (select_eval.folds, j%5).

For each fold we take the engine's BOX-family objects live at each box
golden's tau and rank them two ways:
  - engine ranking (object score -> born cand_log score -> recency),
    the production M1 rule;
  - box_rank ranking (o.geometry["meta_box_rank"], the ported lab
    ranker — output field only).
box@1 per fold under each, plus a per-fold point-biserial sanity:
P(right box has higher box_rank than the best wrong live box).

Usage: python c1_score_cv.py [variant]   (default c1_score)
"""
import collections
import glob
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
EVAL = os.path.join(PERC, "evalcheck")
sys.path.insert(0, EVAL)
sys.path.insert(0, PERC)

import numpy as np                          # noqa: E402

import common as C                          # noqa: E402
import eval as EV                           # noqa: E402
import eval_v2 as V2                        # noqa: E402
import cache as CA                          # noqa: E402
from snapshot import tau_of, live_records   # noqa: E402

from select_eval import folds               # noqa: E402


def _pkl(variant, h8, date, w1):
    pat = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                       % (variant + "_" if variant else "", h8,
                          date, w1))
    if os.path.exists(pat):
        return pat
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s%s*_%s_%s.pkl" % (
            variant + "_" if variant else "", h8, date, w1)))
    return g[0] if g else None


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "c1r_score"
    h8 = sys.argv[2] if len(sys.argv) > 2 else None
    if h8 is None:
        # find the newest variant cache set
        g = sorted(glob.glob(os.path.join(
            CA.CACHE, "run_%s_*.pkl" % variant)))
        if not g:
            sys.exit("no cache for %s" % variant)
        import re
        h8 = re.search(r"run_%s_([0-9a-f]{16})_" % variant,
                       os.path.basename(g[0])).group(1)
    print("variant=%s hash=%s" % (variant, h8))
    recs = C.load_tune()
    fl = folds(recs)          # same day-level split as LEVEL-LAB V8
    fold_of = {d: j for j, s in enumerate(fl) for d in s}
    per_fold = collections.defaultdict(
        lambda: {"eng": [0, 0], "rank": [0, 0], "dom": [0, 0]})
    pooled = {"eng": [0, 0], "rank": [0, 0], "dom": [0, 0]}
    for j, rec in enumerate(recs):
        fold = fold_of.get(rec["date"], j % 5)
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        by_tau = collections.defaultdict(list)
        for g in g2:
            if g["spec_type"] != "BOX":
                continue
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            f = _pkl(variant, h8, rec["date"], tau)
            if not f:
                continue
            try:
                e_t = pickle.load(open(f, "rb"))
            except Exception:
                continue
            live, _em = live_records(e_t, m, w0, tau)
            boxes = [r for r in live
                     if EV.FAMILY.get(r["type"]) == "box"]
            if not boxes:
                continue
            # attach scores
            smap = {}
            for cd in e_t.cand_log or []:
                if cd.get("outcome") == "born" and \
                        cd.get("kind") != "LABEL_TF":
                    key = (cd["kind"], cd.get("cet_min"))
                    smap[key] = max(smap.get(key, 0.0),
                                    cd.get("score") or 0.0)
            osc = {o.id: getattr(o, "score", None)
                   for o in e_t.objects}
            brk = {o.id: o.geometry.get("meta_box_rank")
                   for o in e_t.objects}
            for r in boxes:
                r["score"] = osc.get(r["id"])
                r["box_rank"] = brk.get(r["id"])

            def _key(r):
                s = r.get("score")
                if s is None:
                    s = smap.get((r["type"], r.get("t_birth")))
                if s is not None:
                    return (0, -s, -(r.get("t_birth") or 0))
                return (1, -(r.get("t_birth") or 0), 0)

            def _key_r(r):
                s = r.get("box_rank")
                if s is not None:
                    return (0, -s, -(r.get("t_birth") or 0))
                    # fall THROUGH to engine key when box_rank absent
                return _key(r)

            top_eng = sorted(boxes, key=_key)[0]
            top_rk = sorted(boxes, key=_key_r)[0]
            for g in gs:
                hit_e = V2.match(g, top_eng, m)
                hit_r = V2.match(g, top_rk, m)
                per_fold[fold]["eng"][0] += hit_e
                per_fold[fold]["eng"][1] += 1
                per_fold[fold]["rank"][0] += hit_r
                per_fold[fold]["rank"][1] += 1
                pooled["eng"][0] += hit_e
                pooled["eng"][1] += 1
                pooled["rank"][0] += hit_r
                pooled["rank"][1] += 1
                # dominance: does some MATCHING live box carry the max
                # box_rank among live boxes?  (the ranking question the
                # build lane cares about)
                ranked = sorted(boxes,
                                key=lambda r: -(r.get("box_rank")
                                                if r.get("box_rank")
                                                is not None else
                                                -10 ** 9))
                hit_top = V2.match(g, ranked[0], m)
                any_match = any(V2.match(g, r, m) for r in boxes)
                if any_match:
                    per_fold[fold]["dom"][1] += 1
                    pooled["dom"][1] += 1
                    per_fold[fold]["dom"][0] += hit_top
                    pooled["dom"][0] += hit_top
    print("%-5s %-14s %-14s %-14s" % ("fold", "box@1 eng",
                                      "box@1 box_rank",
                                      "top-box_rank match|coverable"))
    for f in sorted(per_fold):
        r = per_fold[f]
        print("%-5d %.3f (%d/%d)   %.3f (%d/%d)   %.3f (%d/%d)" % (
            f,
            r["eng"][0] / r["eng"][1] if r["eng"][1] else 0,
            r["eng"][0], r["eng"][1],
            r["rank"][0] / r["rank"][1] if r["rank"][1] else 0,
            r["rank"][0], r["rank"][1],
            r["dom"][0] / r["dom"][1] if r["dom"][1] else 0,
            r["dom"][0], r["dom"][1]))
    print("pooled %.3f (%d/%d)   %.3f (%d/%d)   %.3f (%d/%d)" % (
        pooled["eng"][0] / pooled["eng"][1] if pooled["eng"][1] else 0,
        pooled["eng"][0], pooled["eng"][1],
        pooled["rank"][0] / pooled["rank"][1]
        if pooled["rank"][1] else 0,
        pooled["rank"][0], pooled["rank"][1],
        pooled["dom"][0] / pooled["dom"][1] if pooled["dom"][1] else 0,
        pooled["dom"][0], pooled["dom"][1]))


if __name__ == "__main__":
    main()
