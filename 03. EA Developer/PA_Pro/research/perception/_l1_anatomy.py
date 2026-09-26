"""_l1_anatomy.py — R75 s.75.3(1): L-1 cross-family anatomy, read-only.

For every level@1 hit the C-3 parent has and l1_close loses, name what
took its place: which object, which budget/cap veto, which
structure-competition path (file:line via the cand_log outcome tags),
and whether the extra L-1 line births shifted any level candidate's
birth time or state.

Parent arm = uip2_pbbirth@8361fe85e73f9437 (canonical C-3 cache).
Arm        = l1_close@8b33011772e43474 (measured L-1 V1 cache).

Usage: python _l1_anatomy.py
"""
import collections
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "evalcheck"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common as C                      # noqa: E402
import eval as EV                       # noqa: E402
import eval_v2 as V2                    # noqa: E402
import cache as CA                      # noqa: E402
import recall_at_k as RK                # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402

PAR = ("uip2_pbbirth", "8361fe85e73f9437")
ARM = ("l1_close", "8b33011772e43474")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "evalcheck", "_cache")
LV_KINDS = ("LEVEL_CARRIED", "MINI_LEVEL")
LN_TYPES = ("PATTERN_LINE", "CONTEXT_LINE")


def pickled(variant, h, date, w1):
    f = os.path.join(CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h, date, w1))
    if not os.path.exists(f):
        return None
    try:
        with open(f, "rb") as fh:
            return pickle.load(fh)
    except Exception:
        return None


def level_ranked(e, m, w0, tau):
    live, _em = live_records(e, m, w0, tau)
    osc = {ob.id: getattr(ob, "score", None) for ob in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    ranked = RK.rank_live(live, RK.score_map(e))
    return [r for r in ranked if EV.FAMILY.get(r["type"]) == "level"]


def births_le(e, m, tau, types):
    n = 0
    for ob in e.objects:
        if ob.type in types:
            tb = ob.t_birth
            if tb is not None and \
                    int(m[min(tb, len(m) - 1)]) <= tau:
                n += 1
    return n


def lv_cands_near(e, price_raw, tol=8.0):
    out = []
    for r in e.cand_log or []:
        if r["kind"] not in LV_KINDS:
            continue
        p = r.get("price")
        if p is not None and abs(p - price_raw) <= tol:
            out.append(r)
    return out


def main():
    recs = C.load_tune()
    lost = []
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
            e_p = pickled(PAR[0], PAR[1], rec["date"], tau)
            e_a = pickled(ARM[0], ARM[1], rec["date"], tau)
            if e_p is None or e_a is None:
                continue
            lp = level_ranked(e_p, m, w0, tau)
            la = level_ranked(e_a, m, w0, tau)
            for g in gs:
                if EV.FAMILY.get(g["spec_type"]) != "level":
                    continue
                if lp and V2.match(g, lp[0], m) and not (
                        la and V2.match(g, la[0], m)):
                    lost.append((rec, tau, g, e_p, e_a, lp, la, m,
                                 w0))
    print("level@1 hits lost under l1_close: %d\n" % len(lost))
    for rec, tau, g, e_p, e_a, lp, la, m, w0 in lost:
        g0, g1 = g.get("t0"), g.get("t1")
        gprice_pips = (g.get("price") or 0) / 1e-4 \
            if g.get("price") else None
        gp_raw = (g.get("price") or 0)  # golden stored x1e4 already?
        win_p = lp[0]
        eobjs_a = V2.eng_objects(e_a, m, w0, tau)
        # every arm level object vs this golden: closest + route
        det = []
        for er in eobjs_a:
            if EV.FAMILY.get(er["type"]) != "level":
                continue
            ok, route = V2.match_detail(g, er, m)
            det.append((er.get("id"), er.get("type"),
                        er.get("price"), route, ok))
        near = sorted(det, key=lambda x: abs(
            (x[2] or 1e9) - (gprice_pips or 0)))[:4]
        # parent's winning object: find in e_p.objects for birth bar
        par_obj = next((ob for ob in e_p.objects
                        if ob.id == win_p.get("id")), None)
        p_birth = par_obj.t_birth if par_obj else None
        p_price = (par_obj.geometry.get("price") if par_obj
                   and par_obj.geometry else None)
        # arm cand at same birth bar +/- 3 near the parent price
        cand_same_bar = []
        if p_birth is not None and p_price is not None:
            for r in e_a.cand_log or []:
                if r["kind"] not in LV_KINDS:
                    continue
                if abs(r["idx"] - p_birth) <= 3 and \
                        abs((r.get("price") or 0) - p_price) <= 4:
                    cand_same_bar.append(
                        {"idx": r["idx"], "price": r.get("price"),
                         "outcome": r["outcome"],
                         "score": r.get("score")})
        cands = lv_cands_near(e_a, p_price or -1)
        veto = collections.Counter(r["outcome"] for r in cands)
        print("== %s tau=%d gold=%s@%.1f span=%s-%s ==" % (
            rec["id"], tau, g["spec_type"],
            gprice_pips or -1, g0, g1))
        print("  parent top1: %s price=%s score=%s birth_bar=%s" % (
            win_p.get("id"), win_p.get("price"),
            win_p.get("score"), p_birth))
        print("  arm top1..4 near golden price:")
        for row in near:
            print("    id=%s %s price=%s -> %s %s" % (
                row[0], row[1], row[2], row[3],
                "MATCH" if row[4] else ""))
        print("  arm cand at parent birth-bar: %s" %
              json.dumps(cand_same_bar[:6], default=str))
        print("  arm cands near par price (tol8p): %s" %
              json.dumps(dict(veto)))
        print("  PL/CL births<=tau: par=%d arm=%d | level births<=tau:"
              " par=%d arm=%d" % (
                  births_le(e_p, m, tau, LN_TYPES),
                  births_le(e_a, m, tau, LN_TYPES),
                  births_le(e_p, m, tau, LV_KINDS),
                  births_le(e_a, m, tau, LV_KINDS)))
        print()


if __name__ == "__main__":
    main()
