"""EVAL-AUDIT verify of the R61 event-route port A/B (evb_on/evb_off
@be204b98).  Cache-only, own scorer (m1_row.measure + own counters).

Checks:
  1. OFF-identity: evb_off@be204b98 vs c1r_p_base@ee2cbf12 (== STABLE
     C-2 4c2df34d via F1 identity) on all shared runs, objects +
     cand_log + events.
  2. M1 row both arms + paired day-bootstrap CIs vs v0.
  3. Clutter median + margin (panels <= 5.0).
  4. Live box-family objects per panel at tau (the s.61.2 'live
     objects per panel' report).
  5. Flipped box-family goldens ON vs OFF.
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
import m1_row as M1                             # noqa: E402
import _verify_keeps_c1 as VK                   # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402
from salience import FAMILY                     # noqa: E402

H = "be204b980694216e"
ON_VAR = "evb_on"
OFF_VAR = "evb_off"


def live_box_counts(variant, recs):
    """Median live box-family objects per panel at each panel's max
    tau (end of scored content), plus mean/max."""
    per = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                         % (variant, H, rec["date"], w1))
        if not os.path.exists(f):
            continue
        e = pickle.load(open(f, "rb"))
        live, _x = live_records(e, m, w0, w1)
        n = sum(1 for r in live if FAMILY.get(r["type"]) == "box")
        per.append(n)
    return np.array(per)


def event_births(variant, recs):
    """Per-panel count of born objects carrying an ev_* route tag,
    from cand_log + object geometry (whichever is populated)."""
    per = []
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                         % (variant, H, rec["date"], w1))
        if not os.path.exists(f):
            continue
        e = pickle.load(open(f, "rb"))
        n = 0
        for cd in e.cand_log or []:
            if (cd.get("outcome") == "born"
                    and str(cd.get("route") or "").startswith("ev_")):
                n += 1
        if not n:  # fall back to live objects tagged by route
            for ob in e.objects:
                if ob.geometry.get("meta_ev_route"):
                    n += 1
        per.append(n)
    return np.array(per)


def box_hits_by_golden(variant, recs):
    """Set of (panel, spec_type, tau, lo, hi) goldens hit at rank-1."""
    hits = set()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)
              and EV.FAMILY.get(g["spec_type"]) == "box"]
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                             % (variant, H, rec["date"], tau))
            if not os.path.exists(f):
                continue
            e = pickle.load(open(f, "rb"))
            live, _x = live_records(e, m, w0, tau)
            osc = {o.id: getattr(o, "score", None) for o in e.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e))
            top = [r for r in ranked
                   if EV.FAMILY.get(r["type"]) == "box"][:1]
            for g in gs:
                if top and V2.match(g, top[0], m):
                    hits.add((rec["id"], g["spec_type"], tau,
                              round(g.get("price_lo") or 0, 1),
                              round(g.get("price_hi") or 0, 1)))
    return hits


def main():
    import sys as _s
    if len(_s.argv) > 1:
        globals()["H"] = _s.argv[1]
    if len(_s.argv) > 3:
        globals()["OFF_VAR"], globals()["ON_VAR"] = _s.argv[2], _s.argv[3]
    recs = C.load_tune()
    print("hash %s | off=%s on=%s" % (H, OFF_VAR, ON_VAR))
    print("== 1. OFF-identity %s@%s vs c1r_p_base@ee2cbf12"
          % (OFF_VAR, H[:8]))
    n, so, sl, se, miss, diffs = VK.identity(
        H, OFF_VAR, "ee2cbf1202db47b6", "c1r_p_base", recs)
    print("n=%d obj=%d log=%d ev=%d miss=%d" % (n, so, sl, se, miss))
    for d in diffs:
        print("   ", d)

    print("== 2/3. M1 + clutter both arms")
    rng = __import__("random").Random(M1.SEED)
    off = M1.measure(H, OFF_VAR, recs)
    on = M1.measure(H, ON_VAR, recs)
    h0 = __import__("funnel").code_hash(__import__("funnel").V0_FILES)
    v0 = M1.measure(h0, "m1_v0", recs)
    o1 = M1.report("%s (parent)" % OFF_VAR, off, v0=v0, rng=rng)
    o2 = M1.report("%s  (arm)" % ON_VAR, on, v0=v0, rng=rng)
    r_on = np.array(sorted(o2["ratios"]))
    r_off = np.array(sorted(o1["ratios"]))
    print("margin<=5.0: off %d/%d | on %d/%d"
          % ((r_off <= 5.0).sum(), len(r_off),
             (r_on <= 5.0).sum(), len(r_on)))

    print("== 4. live box-family objects per panel (window end)")
    for v in (OFF_VAR, ON_VAR):
        a = live_box_counts(v, recs)
        print("  %s: med %.1f mean %.2f p90 %.0f max %d (n=%d)"
              % (v, np.median(a), a.mean(),
                 np.percentile(a, 90), a.max(), len(a)))

    print("== 4b. event-route births per panel (s.62.4 report)")
    for v in (OFF_VAR, ON_VAR):
        a = event_births(v, recs)
        print("  %s: med %.1f mean %.2f p90 %.0f max %d"
              % (v, np.median(a), a.mean(),
                 np.percentile(a, 90), a.max()))

    print("== 5. flipped box-family goldens (rank-1 hit ON vs OFF)")
    ho = box_hits_by_golden(ON_VAR, recs)
    hf = box_hits_by_golden(OFF_VAR, recs)
    gained = sorted(ho - hf)
    lost = sorted(hf - ho)
    print("  gained %d: %s" % (len(gained), gained))
    print("  lost   %d: %s" % (len(lost), lost))


if __name__ == "__main__":
    main()
