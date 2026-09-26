"""_flips_c2.py — per-golden hit sets for C-2 A/B arms (EVAL-AUDIT).

For each (hash, variant) this walks the same tau-window loop as
m1_row.measure but keeps golden identity, so two arms can be diffed to
name exactly which goldens flip miss->hit / hit->miss at the family's
budget k.  Cache-only, read-only.

Usage: python evalcheck/_flips_c2.py
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
from snapshot import tau_of, live_records       # noqa: E402

M1 = (("box", 1), ("level", 1), ("line", 2))


def gkey(rec, g):
    return (rec["id"], g["spec_type"], g.get("t0"), g.get("t1"),
            round(g.get("price") or g.get("price_hi") or
                  g.get("price_lo") or 0.0, 5))


def golden_hits(eng_hash, variant, recs):
    """{gkey: {"fam":f,"hit@k":bool,...}} over all M1-fam goldens."""
    out = {}
    miss = 0
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
        for tau, gs in sorted(by_tau.items()):
            f = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                             % (variant + "_" if variant else "",
                                eng_hash, rec["date"], tau))
            if not os.path.exists(f):
                miss += 1
                continue
            with open(f, "rb") as fh:
                e_t = pickle.load(fh)
            live, _em = live_records(e_t, m, w0, tau)
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
                if fg not in dict(M1):
                    continue
                k = dict(M1)[fg]
                top = fam_ranked.get(fg, [])[:k]
                hit = any(V2.match(g, er, m) for er in top)
                kkey = gkey(rec, g)
                out.setdefault(kkey, {"fam": fg})["hit@%d" % k] = hit
    return out, miss


def diff(tag, a, b):
    gained, lost = [], []
    for kkey in a:
        fa, fb = a[kkey], b.get(kkey, {"hit@1": None})
        fam = fa["fam"]
        kk = "hit@%d" % dict(M1)[fam]
        ha, hb = fa.get(kk), fb.get(kk)
        if ha is True and hb is not True:
            gained.append((fam, kkey))
        elif ha is not True and hb is True:
            lost.append((fam, kkey))
    print("%s: +%d -%d" % (tag, len(gained), len(lost)))
    for fam, kkey in sorted(gained):
        print("   + %s %s" % (fam, kkey))
    for fam, kkey in sorted(lost):
        print("   - %s %s" % (fam, kkey))
    return gained, lost


def main():
    recs = C.load_tune()
    pairs = [
        ("K7 marker.off @66f596dc", "66f596dc8234b436",
         "ctxy_off", "bmoff_on"),
        ("K8 cong_pivedge @81f7503f", "81f7503f346dab9f",
         "pedg_off", "pedg_on"),
        ("K9 rate_label_tf=2 @759d9036", "759d9036b20969a8",
         "ltfcap_off", "ltfcap_on"),
    ]
    for tag, hh, va, vb in pairs:
        ha, ma = golden_hits(hh, va, recs)
        hb, mb = golden_hits(hh, vb, recs)
        print("%s  (misses off=%d on=%d)" % (tag, ma, mb))
        diff("  OFF->ON", ha, hb)


if __name__ == "__main__":
    main()
