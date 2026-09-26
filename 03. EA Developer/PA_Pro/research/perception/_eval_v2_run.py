"""_eval_v2_run.py — v0/v1 under the official ruler (eval_v2) only.

Usage: python _eval_v2_run.py [v0|v1|both]
"""
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
import common as C                    # noqa: E402
import eval as EV                     # noqa: E402
import eval_v2                        # noqa: E402
import pa_slots                       # noqa: E402
import engine as ENG1                 # noqa: E402
import engine_v0 as ENG0              # noqa: E402


def panel(rec, cls):
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1)
    gobjs, _un, _to = EV.gold_objects(rec)
    for g in gobjs:
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    g2 = [g for g in gobjs if eval_v2.scorable(g, w0, w1)]
    gmarks = EV.gold_marks(rec)
    gm2 = [gm for gm in gmarks if eval_v2.scorable_mark(gm, w0, w1)]
    eo = eval_v2.eng_objects(e, m, w0, w1)
    em = [r for r in eo if r["type"] == "LABEL_TF"]
    pairs, mp = C.match_panel(g2, eo, gm2, em, m,
                              eval_v2.match, eval_v2.match_mark,
                              eval_v2.score)
    routes = collections.Counter(
        eval_v2.match_detail(g2[gi], eo[ei], m)[1]
        for gi, ei in pairs
        if g2[gi]["spec_type"] in eval_v2.BOX_TYPES)
    return C.tally(g2, eo, gm2, pairs, mp), len(eo), routes


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    recs = C.load_tune()
    with pa_slots.slot("eval_v2_run", timeout=300):
        for tag, cls in (("v0", ENG0.PerceptionEngine),
                         ("v1", ENG1.PerceptionEngine)):
            if which not in ("both", tag):
                continue
            T = collections.defaultdict(
                lambda: {"g": 0, "e": 0, "m": 0})
            clutter, empty, routes = [], 0, collections.Counter()
            for k, rec in enumerate(recs):
                t_, n_e, rt = panel(rec, cls)
                for ty, d in t_.items():
                    for kk in d:
                        T[ty][kk] += d[kk]
                routes.update(rt)
                empty += n_e == 0
                gtot = sum(d["g"] for d in t_.values())
                if gtot:
                    clutter.append(n_e / gtot)
                if (k + 1) % 50 == 0:
                    print("  %s %d/%d" % (tag, k + 1, len(recs)),
                          flush=True)
            print("## %s (eval_v2)" % tag)
            for ty in sorted(T):
                g, e_, mh = T[ty]["g"], T[ty]["e"], T[ty]["m"]
                print("  %-14s g=%3d e=%4d m=%3d rec=%.2f prec=%s"
                      % (ty, g, e_, mh, mh / g if g else float("nan"),
                         "%.2f" % (mh / e_) if e_ else "nan"))
            print("  clutter median %.2f | empty %d | BOX routes %s"
                  % (float(np.median(clutter)), empty, dict(routes)))


if __name__ == "__main__":
    main()
