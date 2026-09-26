"""c1_v0table.py — R39 §39.4 bullet 3 / R40 §40.4.3: the 16 box
goldens v0 hits at @1, and what v1 has live at each of those tau.

For every scorable BOX golden:
  * v0 live set at tau (m1_v0 pickles): top-1 box by rank_live;
    v0 "hits" when top-1 matches the golden (the 16-hit set).
  * v1 live set at the same tau (lvltr_off @ 22888182 = the kept
    parent's flag-OFF run): its top-1 box, and where (if anywhere) a
    matching box sits in the ranking.

One row per v0-hit golden + the v1-side story.

Usage: python c1_v0table.py [v1variant v1hash]
        default lvltr_off 2288818268e1cd7c
"""
import glob
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
import funnel as F                     # noqa: E402
import recall_at_k as RK               # noqa: E402
from snapshot import tau_of, live_records  # noqa: E402

V0H = F.code_hash(F.V0_FILES)


def _pkl(variant, h8, date, w1):
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (variant, h8, date, w1))
    if os.path.exists(f):
        return f
    g = glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s*_%s_%s.pkl" % (variant, h8, date, w1)))
    return g[0] if g else None


def _boxes_at(variant, h8, date, tau, m, w0):
    f = _pkl(variant, h8, date, tau)
    if not f:
        return None, None
    e = pickle.load(open(f, "rb"))
    live, _em = live_records(e, m, w0, tau)
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    smap = RK.score_map(e)
    ranked = RK.rank_live(live, smap)
    boxes = [r for r in ranked if EV.FAMILY.get(r["type"]) == "box"]
    return boxes, e


def _edge(r):
    return "%.0f-%.0f" % (r.get("lo") or 0, r.get("hi") or 0)


def main():
    v1v = sys.argv[1] if len(sys.argv) > 1 else "lvltr_off"
    v1h = sys.argv[2] if len(sys.argv) > 2 else "2288818268e1cd7c"
    recs = C.load_tune()
    rows = []
    n_v0hit = n_v1live_match = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for g in g2:
            if g["spec_type"] != "BOX":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            b0, _e0 = _boxes_at("m1_v0", V0H, rec["date"], tau, m, w0)
            if not b0:
                continue
            v0top = b0[0]
            if not V2.match(g, v0top, m):
                continue                     # only the 16 v0 hits
            n_v0hit += 1
            b1, e1 = _boxes_at(v1v, v1h, rec["date"], tau, m, w0)
            v1top = b1[0] if b1 else None
            match_rank = None
            if b1:
                for k, r in enumerate(b1):
                    if V2.match(g, r, m):
                        match_rank = k + 1
                        break
            if match_rank:
                n_v1live_match += 1
            rows.append({
                "id": rec["id"], "tau": tau,
                "g": "%.0f-%.0f" % (g["price_lo"] * 1e4,
                                    g["price_hi"] * 1e4),
                "v0": "%s %.1f" % (v0top.get("why"),
                                   v0top.get("score") or -1),
                "v0e": _edge(v0top),
                "v1": "-",
                "v1e": "-",
                "v1sco": "-",
                "v1match": match_rank or "-"})
            if v1top is not None:
                rows[-1]["v1"] = str(v1top.get("why"))[:10]
                rows[-1]["v1e"] = _edge(v1top)
                rows[-1]["v1sco"] = "%.1f" % (v1top.get("score") or -1)
    print("v0 box@1 hits found: %d | v1 has a matching box live at "
          "those tau: %d" % (n_v0hit, n_v1live_match))
    print("%-7s %-5s %-13s | %-16s %-13s | %-10s %-13s %-6s %s" % (
        "panel", "tau", "golden", "v0 top (hit)", "v0 edges",
        "v1 top", "v1 edges", "v1 sco", "v1 match rank"))
    for r in rows:
        print("%-7s %-5d %-13s | %-16s %-13s | %-10s %-13s %-6s %s" % (
            r["id"], r["tau"], r["g"], r["v0"], r["v0e"],
            r["v1"], r["v1e"], r["v1sco"], r["v1match"]))


if __name__ == "__main__":
    main()
