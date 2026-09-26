"""_lc_pick.py — queue-4 detail report for lc_score_pick.

Measures, per (panel, tau):
- covered-but-unhit level goldens under the parent arm: a golden of
  family 'level' matched by SOME live level-family object at tau, but
  not by the family's top-1 (the M1 level@1 miss).
- how many of those hit at level@1 under the arm;
- supersession count = 'superseded' close events on the arm's objects.

Usage: python _lc_pick.py <parent_variant> <arm_variant> <arm_hash> <parent_hash>
"""
import collections
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
from snapshot import tau_of, live_records
import recall_at_k as RK
import _ab_onehash as AB


def rows_for(eng_hash, cls, recs, variant):
    """per (panel,tau): golden level objs + live ranked + live level objs."""
    out = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t, variant=variant)
            live, _em = live_records(e_t, m, w0, tau)
            osc = {o.id: getattr(o, "score", None) for o in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            smap = RK.score_map(e_t)
            ranked = RK.rank_live(live, smap)
            lev = [r for r in ranked if EV.FAMILY.get(r["type"])
                   == "level"]
            glev = [g for g in gs if EV.FAMILY.get(g["spec_type"])
                    == "level"]
            out.append({"panel": rec["id"], "tau": tau, "m": m,
                        "g": glev, "lev": lev, "live": live})
    return out


def main():
    pv, av, ah, ph = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    recs = C.load_tune()
    prows = rows_for(ph, AB.ARMS[pv], recs, pv)
    arows = rows_for(ah, AB.ARMS[av], recs, av)
    akey = {(r["panel"], r["tau"]): r for r in arows}
    covered_unhit = []
    for r in prows:
        for g in r["g"]:
            covered = any(V2.match(g, er, r["m"]) for er in r["lev"])
            hit1 = any(V2.match(g, er, r["m"]) for er in r["lev"][:1])
            if covered and not hit1:
                ar = akey.get((r["panel"], r["tau"]))
                nowhit = ar is not None and any(
                    V2.match(g, er, ar["m"]) for er in ar["lev"][:1])
                covered_unhit.append(
                    (r["panel"], r["tau"], g.get("spec_type"), nowhit))
    n = len(covered_unhit)
    nh = sum(1 for *_x, h in covered_unhit if h)
    print("parent covered-but-unhit level goldens: %d" % n)
    print("of those now hit at level@1 under arm: %d" % nh)
    for row in covered_unhit:
        print("  %s tau=%s %s -> %s" % row)
    # flicker: superseded close events on the arm
    sup = 0
    for rec in recs:
        e = CA.run(ah, AB.ARMS[av], rec, variant=av)
        for o in e.objects:
            sup += sum(1 for _i, ev, _w in o.events
                       if ev == "close" and "superseded" in str(_w))
        # also count the event marker
        sup += sum(1 for o in e.objects
                   for _i, ev, _w in o.events if ev == "superseded")
    print("superseded events under arm: %d" % sup)


if __name__ == "__main__":
    main()
