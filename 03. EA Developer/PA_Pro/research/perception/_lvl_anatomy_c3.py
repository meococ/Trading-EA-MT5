"""_lvl_anatomy_c3.py — B.S(b) refresh on STABLE C-3: for every
scorable level-family golden (LEVEL_CARRIED + MINI_LEVEL), classify
under the C-3 cache (uip2_pbbirth@8361fe85 == defaults):

  hit          - rank-1 level object matches at tau (level@1)
  hit_deeper   - a match exists at rank>=2 (rescuable by selection)
  no_live      - no live level-family object at tau
  pick_close   - rank-1 pick within 5p of golden price
  pick_mid     - 5-10p off
  pick_far     - >10p off (wrong level entirely)

Cache-only, read-only.  Usage: python _lvl_anatomy_c3.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, HERE)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

HASH = "8361fe85e73f9437"
VAR = "uip2_pbbirth"


def gprice(g):
    """Golden price in pips (goldens are raw EURUSD ~1.33)."""
    if g.get("price") is not None:
        return g["price"] * 1e4
    lo, hi = g.get("price_lo"), g.get("price_hi")
    if lo is not None and hi is not None:
        return (lo + hi) / 2.0 * 1e4
    return None


def eprice(r):
    """Engine live-record price (already pips)."""
    return r.get("price")


def main():
    recs = C.load_tune()
    cls = collections.Counter()
    hits = []
    misses = collections.Counter()
    resc = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)
              and EV.FAMILY.get(g["spec_type"]) == "level"]
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            f = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                             % (VAR + "_", HASH, rec["date"], tau))
            if not os.path.exists(f):
                continue
            import pickle
            with open(f, "rb") as fh:
                e_t = pickle.load(fh)
            live, _em = live_records(e_t, m, w0, tau)
            ranked = RK.rank_live(live, RK.score_map(e_t))
            lvl = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == "level"]
            for g in gs:
                gp = gprice(g)
                if lvl and V2.match(g, lvl[0], m):
                    cls["hit"] += 1
                    hits.append((rec["id"], g["spec_type"],
                                 lvl[0]["type"], gp,
                                 eprice(lvl[0])))
                    continue
                # deeper ranks?
                dep = [k for k, r in enumerate(lvl[1:], start=2)
                       if V2.match(g, r, m)]
                if dep:
                    cls["hit_deeper"] += 1
                    resc.append((rec["id"], g["spec_type"],
                                 dep[0], gp))
                    continue
                if not lvl:
                    cls["no_live"] += 1
                    continue
                ep = eprice(lvl[0])
                err = abs(ep - gp) if (ep is not None
                                       and gp is not None) else 1e9
                cls["pick_close" if err <= 5 else
                    "pick_mid" if err <= 10 else "pick_far"] += 1
    print("level@1 anatomy on C-3 (uip2_pbbirth@8361fe85):")
    for k in ("hit", "hit_deeper", "no_live", "pick_close",
              "pick_mid", "pick_far"):
        print("  %-11s %d" % (k, cls[k]))
    print("  total        %d" % sum(cls.values()))
    print("\nhits:")
    for h_ in hits:
        print("  %s %s <- %s gold=%s eng=%s"
              % (h_[0], h_[1], h_[2],
                 "%.1f" % h_[3] if h_[3] is not None else "?",
                 "%.1f" % h_[4] if h_[4] is not None else "?"))
    print("\nrescuable (match at rank>=2):", len(resc))
    for r in resc:
        print("  %s %s rank%d gold=%s"
              % (r[0], r[1], r[2],
                 "%.1f" % r[3] if r[3] is not None else "?"))


if __name__ == "__main__":
    main()
