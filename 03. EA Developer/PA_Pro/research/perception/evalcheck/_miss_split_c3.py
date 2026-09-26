"""_miss_split_c3.py — R60 §60.5.1: split the 109 box misses by the
ruler's own match components (eval_v2, read-only).

For each scorable BOX golden missed by box@1 at tau on STABLE C-2
(c1r_p_base@ee2cbf12 == merged 4c2df34d), take the engine's rank-1
live box-family object at tau and decompose the ruler's verdict:

  window_ok  = containment-window true-IoU >= .5, OR the coverage
               fallback when a side recorded no window (R11 s.11.1)
  edges_ok   = both edges within tol (or golden is time_only)

Classes:
  no_candidate   - no live box-family object at tau
  window_only    - edges ok, window fails   (price right, time wrong)
  edges_only     - window ok, edges fail    (time right, price wrong)
  both_fail      - neither passes
  (hit goldens are reported separately)

Also reported per class: the same decomposition against the BEST
live candidate (max coverage score) - does a matching object exist
beneath rank-1 at all.
"""
import collections
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

HASH = "ee2cbf1202db47b6"
VAR = "c1r_p_base"


def components(g, e, m):
    """(window_ok, edges_ok) for a BOX golden vs engine object."""
    wg0, wg1 = V2._gold_window(g)
    we0, we1 = V2._eng_window(e)
    if None in (wg0, wg1, we0, we1):
        return None, None
    window_ok = V2.iou_true(we0, we1, wg0, wg1) >= 0.5
    if not window_ok and not (V2._has_gold_window(g)
                              and V2._has_eng_window(e)):
        w0, w1 = e.get("w0", -10**9), e.get("w1", 10**9)
        e0, e1 = V2._clip(*V2._span(e), w0, w1)
        if e0 is not None:
            window_ok = V2._cov_or_point(e0, e1, wg0, wg1) >= 0.5
    t_only = C.is_time_only(g)
    edges_ok = V2._box_edges_ok(g, e, t_only, V2.tol_px(g))
    return window_ok, edges_ok


def main():
    recs = C.load_tune()
    cls_pick = collections.Counter()      # rank-1 pick decomposition
    cls_best = collections.Counter()      # best-coverage object
    hit = 0
    spec_hit = collections.Counter()
    pick_types = collections.Counter()
    details = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)
              and EV.FAMILY.get(g["spec_type"]) == "box"]
        for g in g2:
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            f = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                             % (VAR + "_", HASH, rec["date"], tau))
            if not os.path.exists(f):
                continue
            with open(f, "rb") as fh:
                e_t = pickle.load(fh)
            live, _em = live_records(e_t, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e_t))
            boxfam = [r for r in ranked
                      if EV.FAMILY.get(r["type"]) == "box"]
            # is this golden hit by rank-1?  (box@1 question)
            top1 = boxfam[:1]
            if top1 and V2.match(g, top1[0], m):
                hit += 1
                spec_hit[g["spec_type"]] += 1
                continue
            # best-matching live box object (any rank)
            best = None
            best_sc = -1.0
            for r in boxfam:
                sc = V2.score(g, r)
                if sc > best_sc:
                    best_sc, best = sc, r
            if not boxfam:
                cls_pick["no_candidate"] += 1
                cls_best["no_candidate"] += 1
                pick_types["none"] += 1
                details.append((rec["id"], "no_candidate", None))
                continue
            pick_types[top1[0]["type"]] += 1
            w, e_ok = components(g, top1[0], m)
            cls_pick[("edges_only" if w else
                      "window_only" if e_ok else "both_fail")] += 1
            if best is not None:
                wb, eb = components(g, best, m)
                cls_best[("edges_only" if wb else
                          "window_only" if eb else "both_fail")] += 1
            details.append((rec["id"],
                            "pick:%s w=%s e=%s" % (top1[0]["type"],
                                                   w, e_ok),
                            "best:%s w=%s e=%s" % (best["type"], wb, eb)))

    print("box-family goldens hit at rank-1: %d %s" % (hit,
          dict(spec_hit)))
    print("misses split by RANK-1 pick vs ruler components:")
    for k, v in cls_pick.most_common():
        print("  %-14s %d" % (k, v))
    print("pick types on misses: %s" % dict(pick_types))
    print("same decomposition vs BEST-coverage live object:")
    for k, v in cls_best.most_common():
        print("  %-14s %d" % (k, v))
    out = os.path.join(HERE, "_miss_split_detail.txt")
    with open(out, "w") as fh:
        for d in details:
            fh.write("%s | %s | %s\n" % d)
    print("details -> %s" % out)


if __name__ == "__main__":
    main()
