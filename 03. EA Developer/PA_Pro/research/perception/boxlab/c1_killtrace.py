"""c1_killtrace.py — for each oracle-hit BOX golden under an arm,
what killed the right proposal?  cand_log rows carry geometry on
every outcome (_geom_log), so each right candidate can be matched and
its outcomes tabulated.

Answers the round's real question: the right box reaches the proposal
stream (oracle .407 under wd) but born recall stays .046 — where in
the funnel does it die?

Usage: python c1_killtrace.py [variant hash]   (default c1r_wd e62f2dc9)
"""
import collections
import glob
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
from scoreboard import panel_cands     # noqa: E402


def _pkl(variant, h8, date, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h8, date, w1))
    if os.path.exists(f):
        return f
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (variant, h8, date, w1)))
    return g[0] if g else None


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "c1r_wd"
    h8 = sys.argv[2] if len(sys.argv) > 2 else "e62f2dc9"
    recs = C.load_tune()
    kill = collections.Counter()          # outcome of right cands
    g_stats = collections.Counter()       # per-golden fate
    per_g = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        f = _pkl(variant, h8, rec["date"], w1)
        if not f:
            continue
        e = pickle.load(open(f, "rb"))
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        cands = [r for r in panel_cands(e, m, w0, w1)
                 if EV.FAMILY.get(r["type"]) == "box"]
        for g in g2:
            if g["spec_type"] != "BOX":
                continue
            right = [r for r in cands if F.cand_right(g, r, m)]
            if not right:
                g_stats["no_right_prop"] += 1
                continue
            outs = collections.Counter(r["outcome"] for r in right)
            kill.update(outs)
            if outs.get("born"):
                g_stats["born"] += 1
                per_g.append((rec["id"], "born", dict(outs)))
            elif outs.get("nms_suppressed"):
                g_stats["killed_nms"] += 1
                per_g.append((rec["id"], "nms", dict(outs)))
            elif outs.get("rate_limited"):
                g_stats["killed_rate"] += 1
                per_g.append((rec["id"], "rate", dict(outs)))
            elif outs.get("below_min_score"):
                g_stats["killed_score"] += 1
                per_g.append((rec["id"], "score", dict(outs)))
            elif outs.get("fam_capped"):
                g_stats["killed_famcap"] += 1
                per_g.append((rec["id"], "famcap", dict(outs)))
            elif outs.get("outranked"):
                g_stats["killed_outrank"] += 1
                per_g.append((rec["id"], "outrank", dict(outs)))
            elif outs.get("expired"):
                g_stats["killed_expire"] += 1
                per_g.append((rec["id"], "expire", dict(outs)))
            else:
                g_stats["only_proposed"] += 1
                per_g.append((rec["id"], "proposed", dict(outs)))
    print("variant=%s hash=%s" % (variant, h8))
    print("per-golden fate:", dict(g_stats))
    print("right-cand outcome counts:", dict(kill))
    print("\nfirst 25 rows:")
    for r in per_g[:25]:
        print("  %s %-8s %s" % r)


if __name__ == "__main__":
    main()
