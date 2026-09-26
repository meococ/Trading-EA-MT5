"""_uip_report.py — post-A/B deliverables for the R62 T1/UIP arms.

Reads cached engine pickles (same hash, per variant) and reports:
- clutter median + margin (panels <= 5.0) on the clutter@tau series
- uip births per panel (cand_log outcome == 'uip_birth')
- live objects per panel at tau (live_records)
- flipped goldens box@1 (hit sets diffed OFF->ON)

Usage: python _uip_report.py <hash> uip_on uip2_on
"""
import collections
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import common as C          # noqa: E402
import cache as CA          # noqa: E402
import eval as EV           # noqa: E402
import eval_v2 as V2        # noqa: E402
import recall_at_k as RK    # noqa: E402
from snapshot import tau_of, live_records   # noqa: E402


def load(hh, variant, rec, tau=None):
    w1 = rec["window"]["x1"] or 1439
    if tau is not None:
        w1 = tau
    f = os.path.join(
        CA.CACHE, "run_%s%s_%s_%s.pkl"
        % (variant + "_" if variant else "", hh, rec["date"], w1))
    if not os.path.exists(f):
        return None
    with open(f, "rb") as fh:
        return pickle.load(fh)


def arm_stats(hh, variant):
    recs = C.load_tune()
    ratios = []
    births = []
    live_n = []
    hits = {}
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        e = load(hh, variant, rec)
        if e is None:
            continue
        nb = sum(1 for cd in (e.cand_log or [])
                 if cd.get("outcome") == "uip_birth")
        births.append(nb)
        eobjs = V2.eng_objects(e, m, w0, w1)
        if g2:
            ratios.append(len(eobjs) / len(g2))
        for tau, gs in sorted(by_tau.items()):
            e_t = load(hh, variant, rec, tau)
            if e_t is None:
                continue
            live, _em = live_records(e_t, m, w0, tau)
            live_n.append(len(live))
            osc = {ob.id: getattr(ob, "score", None)
                   for ob in e_t.objects}
            for r in live:
                r["score"] = osc.get(r["id"])
            ranked = RK.rank_live(live, RK.score_map(e_t))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                ff = EV.FAMILY.get(r["type"])
                if ff:
                    fam_ranked[ff].append(r)
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                kk = {"box": 1, "level": 1, "line": 2}.get(fg)
                if kk is None:
                    continue
                top = fam_ranked.get(fg, [])[:kk]
                key = (rec["id"], fg, g.get("t0"), g.get("t1"),
                       round(g.get("price_lo") or g.get("price") or 0,
                             5))
                hits[key] = any(V2.match(g, er, m) for er in top)
    return {"ratios": np.array(ratios), "births": np.array(births),
            "live": np.array(live_n), "hits": hits}


def main():
    hh = sys.argv[1]
    variants = sys.argv[2:]
    stats = {}
    for v in variants:
        s = arm_stats(hh, v)
        stats[v] = s
        cl = s["ratios"]
        print("\n=== %s @%s ===" % (v, hh[:8]))
        print("  uip births/panel: med %.1f mean %.2f max %d"
              % (np.median(s["births"]), s["births"].mean(),
                 s["births"].max()))
        print("  live@tau objs: med %.1f mean %.2f"
              % (np.median(s["live"]), s["live"].mean()))
        print("  clutter ratio med %.2f | margin <=5.0: %d/%d"
              % (np.median(cl), int((cl <= 5.0).sum()), len(cl)))
    if len(variants) >= 2:
        a, b = stats[variants[0]]["hits"], stats[variants[1]]["hits"]
        keys = set(a) | set(b)
        up = [k for k in keys if not a.get(k) and b.get(k)]
        dn = [k for k in keys if a.get(k) and not b.get(k)]
        print("\nflips %s->%s: +%d -%d"
              % (variants[0], variants[1], len(up), len(dn)))
        # R66 report format: per-family flips vs the parent arm
        for fam in ("box", "level", "line"):
            uf = [k for k in up if k[1] == fam]
            df = [k for k in dn if k[1] == fam]
            print("    %-6s +%d -%d" % (fam, len(uf), len(df)))
        # pairwise vs every other variant (e.g. delta vs uip2 base)
        for v2 in variants[2:]:
            c = stats[v2]["hits"]
            up2 = [k for k in set(b) | set(c)
                   if b.get(k) and not c.get(k)]
            dn2 = [k for k in set(b) | set(c)
                   if c.get(k) and not b.get(k)]
            print("  flips %s->%s: +%d -%d"
                  % (v2, variants[1], len(up2), len(dn2)))
        for k in sorted(dn):
            print("   - %s" % (k,))
        for k in sorted(up):
            print("   + %s" % (k,))


if __name__ == "__main__":
    main()
