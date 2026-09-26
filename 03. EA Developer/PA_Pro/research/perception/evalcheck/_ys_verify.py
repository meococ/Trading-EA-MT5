"""EVAL-AUDIT s.85.3 — independent verify of boxlab/YS_EST.md.

Two decisive checks (own code, same stated semantics):
  A) YS-b item-1: for each of the 16 box@1 hits at golden tau, does
     the holder yield before tau?  Yield rule (their spec): the
     object has s_box_broken on its CURRENT band version (entry
     j0 anchored at min(t_left, j1) - engine semantics) AND a
     box-kind pool cand born strictly AFTER the break's exit_bar
     is pending/live (cand_log entries) at that bar.  Reported
     yield bars must precede tau.
  B) YS-a frees: sticky yield simulation over the 59 BUDGET_CUT
     rows - track the yielded set bar-by-bar; holder(j) = ev_-why
     object if active & not yielded else max-score active box;
     a row is FREED iff within its pending window there is a bar
     where every active box object is yielded (slot empty).
     Edge-matched frees decide the >=5 gate.

usage: python evalcheck/_ys_verify.py [--hits-only]
"""
import collections
import json
import os
import pickle
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import trade_tags as TT                         # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"
RE_W = re.compile(r"\[(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\]"
                  r".*?t0=(\d+)")
# cand_log 'kind' is the object type, not the route name
BOXK = ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")


def band_versions(o, e):
    g = o.geometry
    seq = []
    if (o.why or "").startswith("ev_") and o.type == "BOX":
        b = [cd for cd in e.cand_log
             if cd.get("outcome") == "uip_birth"
             and cd.get("idx") == o.t_birth]
        if b:
            seq.append((int(o.t_birth), float(b[-1]["bottom"]),
                        float(b[-1]["top"])))
        for ev in o.events:
            if ev[1] == "uip_rewrite":
                mm = RE_W.search(str(ev[2]))
                if mm:
                    seq.append((int(ev[0]), float(mm.group(1)),
                                float(mm.group(2))))
    if not seq and "bottom" in g:
        seq.append((int(o.t_birth or 0), float(g["bottom"]),
                    float(g["top"])))
    seq.sort(key=lambda v: v[0])
    return seq


def band_at(seq, j):
    cur = seq[0]
    for v in seq:
        if v[0] <= j:
            cur = v
        else:
            break
    return cur


def first_break(o, seq, j_to, c, abr):
    """First (bar, exit_bar, band) where s_box_broken fires on the
    band live at that bar, scanning versions in order.  Engine
    semantics: entry j0 = first close inside band+-tol after
    j_from = min(t_left, j1)."""
    for i, (vb, lo, hi) in enumerate(seq):
        j_end = seq[i + 1][0] - 1 if i + 1 < len(seq) else j_to
        j_end = min(j_end, j_to)
        if j_end < vb:
            continue
        jf = min(int(o.t_left), j_end)
        bb = TT.s_box_broken(lo, hi, jf, j_end,
                             np.asarray(c), np.asarray(abr))
        if bb["bbroken"]:
            return vb, lo, hi, int(bb["exit_bar"])
    return None


def pool_cand_born_after(e, j_from, j_to):
    """Any box-kind cand whose first log idx > j_from and which has
    a log entry at some bar <= j_to (alive/pending then)."""
    # group by cand identity (route+band)
    sig = {}
    for cd in e.cand_log:
        if cd.get("kind") not in BOXK:
            continue
        k = (cd.get("route"), round(cd.get("bottom") or 0, 1),
             round(cd.get("top") or 0, 1))
        sig.setdefault(k, []).append(int(cd["idx"]))
    res = []
    for k, idxs in sig.items():
        born = min(idxs)
        if born > j_from and any(i <= j_to for i in idxs):
            res.append((k, born, max(idxs)))
    return res


def hits():
    """[(rec, tau, holder_obj, e)] - the 16 box@1 hits."""
    recs = list(C.load_tune())
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

    out = []
    import glob
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
        g_box = [g for g in g2
                 if EV.FAMILY.get(g["spec_type"]) == "box"
                 and tau_of(g) is not None
                 and min(tau_of(g), rec["window"]["x1"] or 1439)
                 == w1]
        if not g_box:
            continue
        e = pickle.load(open(f, "rb"))
        _t, m, _o, _h, _l, _c = CA.bars(date)
        m = np.asarray(m)
        live, _em = live_records(e, m, w0, w1)
        osc = {ob.id: getattr(ob, "score", None) for ob in e.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        ranked = RK.rank_live(live, RK.score_map(e))
        top = [r for r in ranked
               if EV.FAMILY.get(r["type"]) == "box"][:1]
        if not top:
            continue
        if not any(V2.match(g, top[0], m) for g in g_box):
            continue
        ob = next((x for x in e.objects if x.id == top[0]["id"]),
                  None)
        if ob is not None:
            out.append((rec, w1, ob, e, date))
    return out


def check_ysb_hits():
    print("== YS-b: does each of the 16 hits yield before tau? ==")
    n_lost = 0
    for rec, w1, ob, e, date in hits():
        _t, m, _o, _h, _l, c = CA.bars(date)
        m = np.asarray(m)
        abr = np.asarray(CA.abr(date))
        j_tau = min(int(np.searchsorted(m, w1)), len(e.bars) - 1)
        seq = band_versions(ob, e)
        br = first_break(ob, seq, j_tau, c, abr)
        if br is None:
            print("  %s@%s %s: NO break pre-tau -> keeps slot"
                  % (rec["id"], w1, ob.id))
            continue
        vb, lo, hi, xb = br
        # yield fires at first bar > xb with a pending/live cand
        # born after exit_bar.  Window for the cand's existence:
        # its first idx > xb and any idx <= j_tau.
        cands = pool_cand_born_after(e, xb, j_tau)
        ybar = min((born for _k, born, _mx in cands), default=None)
        lost = ybar is not None and ybar <= j_tau
        n_lost += lost
        print("  %s@%s %s: break v@%d exit=%d postcands=%d "
              "yield~%s -> %s"
              % (rec["id"], w1, ob.id, vb, xb, len(cands),
                 ybar, "LOST" if lost else "keeps"))
    print("hits lost under YS-b: %d/16" % n_lost)


def check_ysa_frees():
    print("\n== YS-a sticky-yield frees over 59 BUDGET_CUT rows ==")
    recs = {r["id"]: r for r in C.load_tune()}
    e3 = [json.loads(x) for x in
          open(os.path.join(PERC, "boxlab", "e3_diag.jsonl"),
               encoding="utf8")]
    seen = set()
    n_free = n_free_edge = 0
    for r in e3:
        if r.get("cls") != "BUDGET_CUT":
            continue
        k3 = (r["panel"], r["tau"])
        if k3 in seen:
            continue
        seen.add(k3)
        rec = recs[r["panel"]]
        f = os.path.join(CA.CACHE,
                         "run_%s_%s_%s_%s.pkl"
                         % (ARM_V, ARM_H, rec["date"], r["tau"]))
        if not os.path.exists(f):
            continue
        e = pickle.load(open(f, "rb"))
        _t, m, _o, h, l, c = CA.bars(rec["date"])
        m = np.asarray(m)
        abr = np.asarray(CA.abr(rec["date"]))
        j_tau = min(int(np.searchsorted(m, r["tau"])),
                    len(e.bars) - 1)
        # sticky sim, faithful to their spec: at each bar the holder
        # is the ev_-why object if active & not yielded, else the
        # max-score active non-yielded box object.  ONLY the holder
        # can yield (first stale_far onset on its live band).  The
        # slot is empty only when no non-yielded active box exists;
        # a freed cand then promotes (upper bound).
        boxes = [ob for ob in e.objects
                 if EV.FAMILY.get(ob.type) == "box"
                 and "bottom" in ob.geometry]
        bseq = {ob.id: band_versions(ob, e) for ob in boxes}

        def stale_onset(ob):
            seq = bseq.get(ob.id)
            if not seq:
                return None
            j_from = int(ob.t_birth or 0)
            for j in range(j_from, j_tau + 1):
                _b, lo, hi = band_at(seq, j)
                s = TT.s_stale_far("box", {"bottom": lo, "top": hi},
                                   j_from, j, h, l, c, abr)
                if s["stale"]:
                    return j
            return None

        yielded = set()
        yield_at = {}
        onset_memo = {}

        def onset_of(ob):
            if ob.id not in onset_memo:
                onset_memo[ob.id] = stale_onset(ob)
            return onset_memo[ob.id]

        def pick(alive):
            return next(
                (ob for ob in alive
                 if (ob.why or "").startswith("ev_")),
                max(alive, key=lambda x: getattr(x, "score", 0)
                    or 0, default=None)) if alive else None

        # bar-by-bar holder chain over the whole run; the holder
        # yields at its stale onset; the successor takes the slot on
        # the SAME bar (yield-bar succession per their spec).
        chain = []
        for j in range(0, j_tau + 1):
            while True:
                alive = [ob for ob in boxes
                         if int(ob.t_birth or 0) <= j
                         and (ob.t_right is None
                              or int(ob.t_right) >= j)
                         and ob.id not in yielded]
                holder = pick(alive)
                if holder is None:
                    chain.append(None)
                    break
                on = onset_of(holder)
                if on is not None and on <= j:
                    yielded.add(holder.id)
                    yield_at.setdefault(holder.id, on)
                    continue
                chain.append(holder.id)
                break
        w0c = w1c = None
        sig = (r["cand"].get("route"),
               round(r["cand"].get("lo") or 0, 1),
               round(r["cand"].get("hi") or 0, 1))
        idxs = [cd["idx"] for cd in e.cand_log
                if cd.get("kind") in BOXK
                and cd.get("route") == sig[0]
                and round(cd.get("bottom") or 0, 1) == sig[1]
                and round(cd.get("top") or 0, 1) == sig[2]]
        w0c, w1c = (min(idxs), max(idxs)) if idxs else \
            (int(r["cand"]["idx"]), int(r["cand"]["idx"]))
        pend_end = j_tau if r["killer"] == "proposed" else w1c
        # freed (their def, ys_est.py:408-450): the row's INCUMBENT
        # yields while THIS cand is pending -> yield bar inside
        # [w0c, pend_end].  A yield before w0c does NOT free - the
        # successor promotes at the yield bar and keeps blocking.
        inc_y = yield_at.get(r["box1"]["id"])
        frees = inc_y is not None and w0c <= inc_y <= pend_end
        if frees:
            n_free += 1
            n_free_edge += bool(r.get("edge_matched"))
            print("  FREED %s@%s inc=%s yld@%s cwin=[%d,%d] edge=%s"
                  % (r["panel"], r["tau"], r["box1"]["id"],
                     yield_at.get(r["box1"]["id"]), w0c, pend_end,
                     r.get("edge_matched")))
    print("YS-a frees: %d rows | edge-matched: %d"
          % (n_free, n_free_edge))


def main():
    hits_only = "--hits-only" in sys.argv
    check_ysb_hits()
    if not hits_only:
        check_ysa_frees()


if __name__ == "__main__":
    main()
