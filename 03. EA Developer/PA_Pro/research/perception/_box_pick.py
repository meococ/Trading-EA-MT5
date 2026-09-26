"""_box_pick.py — R40 §40.3 detail report for box_score_pick.

For each box golden whose right proposal was RATE-LIMITED under the
parent arm (BOX-LAB's 30-case set): is a matching BOX object live at
tau under the arm, and is it the family's top-1 (box@1 hit)?

Also reports supersede events per panel and flicker.

Usage: python _box_pick.py <parent_variant> <arm_variant> <hash>
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
            boxes = [r for r in ranked
                     if EV.FAMILY.get(r["type"]) == "box"]
            gbox = [g for g in gs
                    if EV.FAMILY.get(g["spec_type"]) == "box"]
            out.append({"panel": rec["id"], "tau": tau, "m": m,
                        "g": gbox, "boxes": boxes, "live": live,
                        "eng": e_t})
    return out


def rate_limited_goldens(rows):
    """Golden boxes with a matching proposal in cand_log that was
    slot-blocked (rate_limited / outranked / fam_capped /
    nms_suppressed) and never born live under the parent."""
    BLOCKED = {"rate_limited", "outranked", "fam_capped",
               "nms_suppressed", "suppressed_budget"}
    res = []
    for r in rows:
        eng = r["eng"]
        for g in r["g"]:
            if any(V2.match(g, er, r["m"]) for er in r["boxes"]):
                continue        # golden already live at tau
            blocked = False
            for cd in eng.cand_log:
                if cd.get("kind") != "BOX":
                    continue
                # cand_log t0/t1 are BAR INDICES; golden spans are
                # minutes-of-day — convert through the bar clock.
                def _mm(j):
                    return r["m"][min(max(j, 0), len(r["m"]) - 1)]
                er = {"type": "BOX", "t0": _mm(cd.get("t0", 0)),
                      "t1": _mm(cd.get("t1", 0)),
                      "lo": cd.get("bottom"), "hi": cd.get("top"),
                      "bs": _mm(cd.get("t0", 0)),
                      "be": _mm(cd.get("t1", 0)), "id": "c"}
                if V2.match(g, er, r["m"]) and \
                        cd.get("outcome") in BLOCKED:
                    blocked = True
                    break
            if blocked:
                res.append((r, g))
    return res


def main():
    pv, av, h = sys.argv[1], sys.argv[2], sys.argv[3]
    recs = C.load_tune()
    prows = rows_for(h, AB.ARMS[pv], recs, pv)
    arows = rows_for(h, AB.ARMS[av], recs, av)
    akey = {(r["panel"], r["tau"]): r for r in arows}
    rl = rate_limited_goldens(prows)
    print("rate-killed box goldens under parent: %d" % len(rl))
    nl = nt = 0
    for r, g in rl:
        ar = akey.get((r["panel"], r["tau"]))
        if ar is None:
            continue
        live_hit = any(V2.match(g, er, ar["m"]) for er in ar["boxes"])
        top_hit = any(V2.match(g, er, ar["m"]) for er in ar["boxes"][:1])
        nl += live_hit
        nt += top_hit
        print("  %s tau=%s -> live@tau=%s top1=%s"
              % (r["panel"], r["tau"], live_hit, top_hit))
    print("arm: live@tau %d/%d, top-1 %d/%d" % (nl, len(rl), nt, len(rl)))
    sup = {}
    for rec in recs:
        e = CA.run(h, AB.ARMS[av], rec, variant=av)
        n = sum(1 for o in e.objects
                for _i, ev, _w in o.events if ev == "superseded")
        if n:
            sup[rec["id"]] = n
    print("superseded events per panel (arm):", sup)
    print("total supersessions:", sum(sup.values()))


if __name__ == "__main__":
    main()
