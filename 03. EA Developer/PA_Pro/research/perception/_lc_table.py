"""_lc_table.py — R36 §36.4 19-case table for lc_score_pick.

For every level-family golden unhit at level@1 under the parent arm:
- is a RIGHT LC proposal in the cand_log (cand_right prefix rule)?
- that candidate's outcome + score vs the in-window slot holder;
- is the golden live-hit (any rank) / hit@1 under the arm?

Usage: python _lc_table.py <parent_var> <arm_var> <hash_p> <hash_a>
"""
import collections
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
import funnel as F
from snapshot import tau_of, live_records
import recall_at_k as RK
import _ab_onehash as AB


def panel_data(eng_hash, cls, rec, variant):
    """(g2 with taus, full cand_log, per-tau ranked live records)."""
    w0 = rec["window"]["x0"]
    w1 = rec["window"]["x1"] or 1439
    t, m, o, h, l, c = CA.bars(rec["date"])
    e = CA.run(eng_hash, cls, rec, variant=variant)
    gobjs, _u, _to = EV.gold_objects(rec)
    g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
    taus = {}
    for g in g2:
        tau = tau_of(g)
        if tau is not None and tau >= w0:
            taus.setdefault(min(tau, w1), []).append(g)
    live_at = {}
    for tau in taus:
        rec_t = dict(rec)
        rec_t["window"] = dict(rec["window"], x1=tau)
        e_t = CA.run(eng_hash, cls, rec_t, variant=variant)
        live, _em = live_records(e_t, m, w0, tau)
        osc = {ob.id: getattr(ob, "score", None) for ob in e_t.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        ranked = RK.rank_live(live, RK.score_map(e_t))
        live_at[tau] = ([r for r in ranked
                         if EV.FAMILY.get(r["type"]) == "level"],
                        e_t)
    return g2, taus, live_at, e.cand_log or [], m, w0, w1


def main():
    pv, av, ph, ah = sys.argv[1:5]
    recs = C.load_tune()
    rows = []
    for rec in recs:
        g2, taus, plive, pcl, m, w0, w1 = panel_data(
            ph, AB.ARMS[pv], rec, pv)
        _g2, _t, alive, _acl, _m, _w0, _w1 = panel_data(
            ah, AB.ARMS[av], rec, av)
        for tau, gs in sorted(taus.items()):
            lev = plive[tau][0]
            for g in gs:
                if EV.FAMILY.get(g["spec_type"]) != "level":
                    continue
                hit1 = any(V2.match(g, er, m) for er in lev[:1])
                if hit1:
                    continue
                # matching LC proposals in this panel's cand_log
                props = []
                for cd in pcl:
                    if cd.get("kind") != "LEVEL_CARRIED":
                        continue
                    r = F.cand_as_record(cd, m, w0, w1)
                    if r is None:
                        continue
                    if F.cand_right(g, r, m):
                        props.append((cd.get("outcome"),
                                      cd.get("score"),
                                      cd.get("cet_min")))
                a_lev = alive.get(tau, ([], None))[0]
                a_hit1 = any(V2.match(g, er, m) for er in a_lev[:1])
                a_hitany = any(V2.match(g, er, m) for er in a_lev)
                rows.append({"panel": rec["id"], "tau": tau,
                             "golden": g.get("spec_type"),
                             "props": props, "a_hit1": a_hit1,
                             "a_any": a_hitany})
    blocked = [r for r in rows
               if any(p[0] == "rate_limited" for p in r["props"])]
    print("level goldens unhit@1 under parent: %d" % len(rows))
    print("with a right LC proposal rate_limited: %d" % len(blocked))
    print("of those, hit@1 under arm: %d"
          % sum(1 for r in blocked if r["a_hit1"]))
    print("of those, live at any rank under arm: %d"
          % sum(1 for r in blocked if r["a_any"]))
    for r in rows:
        print("  %s tau=%s %-13s props=%s | arm hit@1=%s any=%s"
              % (r["panel"], r["tau"], r["golden"],
                 [(o_, s_) for o_, s_, _t in r["props"]],
                 r["a_hit1"], r["a_any"]))


if __name__ == "__main__":
    main()
