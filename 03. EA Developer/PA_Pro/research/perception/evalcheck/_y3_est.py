"""EVAL-AUDIT s.84.5 — independent Y3 offline estimate (read-only).

(a) of the 16 C-3 box@1 hits at golden taus, how many carry
    stale_far at the decision bar;
(b) of the 59 BUDGET_CUT misses in boxlab/e3_diag.jsonl, how many
    incumbents (box1) carry stale_far at the golden tau, and whether
    an edge-matched pending candidate existed (diag fields recount).

Stale_far via TT.object_stats on the arm-cache engine at tau —
same code path as the engine facts (fresh-geometry caveat noted
in the TT-3 record applies equally here).

usage: python evalcheck/_y3_est.py
"""
import collections
import glob
import json
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))
sys.path.insert(0, os.path.join(PERC, "boxlab"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import trade_tags as TT                         # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"


def arm_file(date, w1):
    return os.path.join(CA.CACHE,
                        "run_%s_%s_%s_%s.pkl" % (ARM_V, ARM_H, date, w1))


def stale_at(ob, nfed, bars, ema, abr, pivots):
    ff, st = TT.object_stats(ob, nfed, bars, ema, abr, pivots)
    if ff is None:
        return None, None
    return bool(st.get("stale")), st


def main():
    recs = list(C.load_tune())
    # ---- same-date attribution (from _y_verify) ------------------- #
    by_date = collections.defaultdict(list)
    for r in recs:
        by_date[r["date"]].append(r)

    def base_rec(date, w1):
        cand = [x for x in by_date[date]
                if x["window"]["x0"] <= w1
                <= (x["window"]["x1"] or 1439)]
        for x in cand:
            w0 = x["window"]["x0"]
            w1f = x["window"]["x1"] or 1439
            g2 = [g for g in EV.gold_objects(x)[0]
                  if V2.scorable(g, w0, w1f)]
            if any(tau_of(g) is not None
                   and min(tau_of(g), w1f) == w1 for g in g2):
                return x
        return cand[0] if cand else None

    # ---- (a) the 16 box hits -------------------------------------- #
    print("== (a) 16 C-3 box hits: stale_far at their golden tau ==")
    n_hit = n_stale = 0
    hit_rows = []
    for f in sorted(glob.glob(os.path.join(
            CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H)))):
        stem = os.path.basename(f)[:-4]
        date, w1 = stem.rsplit("_", 2)[1:]
        w1 = int(w1)
        rec = base_rec(date, w1)
        if rec is None:
            continue
        w0 = rec["window"]["x0"]
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, w1)]
        g_box = [g for g in g2 if EV.FAMILY.get(g["spec_type"]) == "box"
                 and tau_of(g) is not None
                 and min(tau_of(g), rec["window"]["x1"] or 1439) == w1]
        if not g_box:
            continue
        e = pickle.load(open(f, "rb"))
        t, m, _o, _h, _l, _c = CA.bars(date)
        m = np.asarray(m)
        live, _em = live_records(e, m, w0, w1)
        osc = {ob.id: getattr(ob, "score", None) for ob in e.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        ranked = RK.rank_live(live, RK.score_map(e))
        top = [r for r in ranked if EV.FAMILY.get(r["type"]) == "box"][:1]
        if not top:
            continue
        pick = top[0]
        hit = any(V2.match(g, pick, m) for g in g_box)
        if not hit:
            continue
        n_hit += 1
        ob = next((x for x in e.objects if x.id == pick["id"]), None)
        nfed = len(e.bars) - 1
        st_flag, st = stale_at(ob, nfed, e.bars, e.ema, e.abr,
                               e.book.seq)
        n_stale += bool(st_flag)
        hit_rows.append((rec["id"], w1, pick["id"], st_flag,
                         st.get("stale_dist") if st else None))
        print("  %s@%s %s stale=%s" % (rec["id"], w1, pick["id"],
                                     st_flag))
    print("hits %d, stale %d" % (n_hit, n_stale))

    # ---- (b) 59 BUDGET_CUT incumbents ----------------------------- #
    print("\n== (b) 59 BUDGET_CUT incumbents: stale_far at golden tau ==")
    rec_by_id = {r["id"]: r for r in recs}
    n = n_stale2 = n_edge = n_stale_edge = 0
    seen = set()
    for l in open(os.path.join(PERC, "boxlab", "e3_diag.jsonl"),
                  encoding="utf8"):
        row = json.loads(l)
        if row.get("cls") != "BUDGET_CUT":
            continue
        k3 = (row["panel"], row["tau"])
        if k3 in seen:
            continue
        seen.add(k3)
        n += 1
        edge = bool(row.get("edge_matched"))
        n_edge += edge
        rec = rec_by_id.get(row["panel"])
        if rec is None:
            print("  NO REC", row["panel"], row["tau"])
            continue
        f = arm_file(rec["date"], row["tau"])
        if not os.path.exists(f):
            print("  NO FILE", rec["id"], row["tau"])
            continue
        e = pickle.load(open(f, "rb"))
        bid = (row.get("box1") or {}).get("id")
        ob = next((x for x in e.objects if x.id == bid), None)
        if ob is None:
            print("  NO OBJ", row["panel"], row["tau"], bid)
            continue
        nfed = len(e.bars) - 1
        st_flag, st = stale_at(ob, nfed, e.bars, e.ema, e.abr,
                               e.book.seq)
        n_stale2 += bool(st_flag)
        n_stale_edge += edge and bool(st_flag)
        if st_flag:
            print("  STALE %s@%s %s edge=%s dist=%s"
                  % (row["panel"], row["tau"], bid, edge,
                     st.get("stale_dist") if st else None))
    print("BUDGET_CUT %d | incumbents stale %d | edge-matched %d | "
          "stale AND edge-matched %d" % (n, n_stale2, n_edge,
                                        n_stale_edge))


if __name__ == "__main__":
    main()
