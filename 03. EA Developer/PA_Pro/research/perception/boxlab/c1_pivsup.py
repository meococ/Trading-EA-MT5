"""c1_pivsup.py -- R51 s.51.5.1: pivot-support separation diagnosis.

On the 32 "score-starved" covered-but-missed goldens from c1_missed
(below_min_score 14 + outranked 10 + rate_limited 8): does the feature
"each band edge lies within tol of a pivot confirmed by the eval bar"
separate the RIGHT candidate from the objects that beat or blocked it?

Right side : pooled cands whose edges match the golden.
Wrong side : the box objects live at the cand's resolution bar that
             held the slot (outranked/rate_limited) or were born in
             the panel window while the right cand died on score.

Output: per-golden row + a 2x2 separation table
(right-supported vs wrong-supported counts).
"""
import sys, os, pickle, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalcheck"))
sys.path.insert(0, os.path.join(HERE, ".."))

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
import recall_at_k as RK                   # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402
import c1_missed as CM                     # noqa: E402

HASH = CM.HASH
VAR = CM.VAR
PIP = C.PIP


def piv_prices(e, bar_i):
    """Confirmed pivot prices by bar index."""
    book = getattr(e, "book", None)
    if book is None or not hasattr(book, "seq"):
        return []
    return [p.price for p in book.seq
            if getattr(p, "t_conf", 10 ** 9) <= bar_i]


def edge_sup(lo, hi, pivs, tol):
    """0/1/2 = how many band edges sit within tol of a confirmed pivot."""
    n = 0
    for edge in (lo, hi):
        if any(abs(edge - p) <= tol for p in pivs):
            n += 1
    return n


def main():
    rows = []
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        if CM._pk(rec, w1) is None:
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        by_tau = collections.defaultdict(list)
        for gi, g in enumerate(g2):
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append((gi, g))
        for tau, gs in sorted(by_tau.items()):
            e_t = CM._pk(rec, tau)
            if e_t is None:
                continue
            live, _em = live_records(e_t, m, w0, tau)
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e_t))
            fam = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == "box"]
            for gi, g in gs:
                if EV.FAMILY.get(g["spec_type"]) != "box":
                    continue
                hit = any(V2.match(g, er, m) for er in fam[:1])
                if hit:
                    continue
                tol = V2.tol_px(g)
                mc = [cd for cd in (e_t.cand_log or [])
                      if cd.get("kind") == "BOX"
                      and (cd.get("cet_min") or 0) <= tau
                      and CM.edge_match(cd, g, tol)
                      and CM.span_overlap(cd, g, m, w0, tau)]
                cands = collections.defaultdict(list)
                for cd in mc:
                    cands[CM.ckey(cd)].append(cd)
                # pooled cands = those with any resolution row
                pooled = []
                for k, rr in cands.items():
                    res = [cd for cd in rr
                           if cd.get("outcome") not in ("proposed",)]
                    if res:
                        res.sort(key=lambda cd: cd.get("cet_min") or 0)
                        pooled.append(res[-1])
                pooled = [cd for cd in pooled
                          if cd.get("outcome") not in CM.BORN]
                if not pooled:
                    continue
                # ---- right side: pivot support of the right cand ----
                # eval bar = resolution cet_min -> bar index
                right = []
                for cd in pooled:
                    cm = cd.get("cet_min") or 0
                    bi = int(min(len(m) - 1,
                                 max(0, list(m).index(cm)
                                     if cm in m else 0)))
                    # searchsorted equivalent without numpy import loop
                    import numpy as np
                    bi = int(np.searchsorted(m, cm))
                    pivs = piv_prices(e_t, bi)
                    right.append((edge_sup(cd["bottom"], cd["top"],
                                           pivs, tol),
                                  cd.get("outcome"),
                                  cd.get("route")))
                # ---- wrong side: box objects live at tau that are
                # NOT matches (they held the slots) ----
                wrong = []
                import numpy as np
                for r in live:
                    if r["type"] != "BOX":
                        continue
                    if V2.match(g, r, m):
                        continue   # the right box, had it lived
                    bi = int(np.searchsorted(m, tau))
                    pivs = piv_prices(e_t, bi)
                    wrong.append((edge_sup(r.get("lo", -1),
                                           r.get("hi", -1),
                                           pivs, tol),
                                  r.get("why"),
                                  r.get("score")))
                rows.append({"panel": rec["id"], "gi": gi, "tau": tau,
                             "right": right, "wrong": wrong})
    sep_r = collections.Counter()
    sep_w = collections.Counter()
    for r in rows:
        for s, oc, rt in r["right"]:
            sep_r[s] += 1
        for s, why, sc in r["wrong"]:
            sep_w[s] += 1
    print("goldens:", len(rows))
    print("right-cand edge support dist:", dict(sep_r))
    print("wrong-obj  edge support dist:", dict(sep_w))
    both_r = sum(1 for r in rows
                 if any(s == 2 for s, _, _ in r["right"]))
    both_w = sum(1 for r in rows
                 if any(s == 2 for s, _, _ in r["wrong"]))
    print("goldens with a 2-edge-supported right cand:", both_r)
    print("goldens with a 2-edge-supported live wrong box:", both_w)
    print("\n-- rows --")
    for r in rows:
        print("%-6s g%d t%-4d right=%s wrong=%s"
              % (r["panel"], r["gi"], r["tau"], r["right"], r["wrong"]))


if __name__ == "__main__":
    main()
