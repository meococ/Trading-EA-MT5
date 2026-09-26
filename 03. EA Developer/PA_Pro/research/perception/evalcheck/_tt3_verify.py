"""EVAL-AUDIT R83 s.83.2 verify (TT-3 box_broken):

  1. ON (trade_tags=1, box_yield=0) canonical == uip2_pbbirth@8361fe85
     arm cache on all cached windows (facts-only change);
  2. facts['trade_tags'] carries exit_bar + break_clause when
     box_broken sets;
  3. INDEPENDENT recompute of s_box_broken on sampled live boxes —
     my own entry/j0 + run3 + shock scan (no shared code) vs the
     emitted stats, incl. first-set (exit_bar is the FIRST bar of the
     confirming run / the shock bar) and the no-entry case;
  4. report numbers for the Lead: live-box tag rates split by
     clause; of the 16 C-3 box hits, how many tagged at their tau;
     golden compliance (author boxes tagged at own tau, per clause);
     the 4 S1-b fatal panels + 7 E5 panels: tagged? exit_bar?;
     creep diagnostic (closes beyond one edge, never a run);
  5. prefix invariance on 5 panels (emit at truncated taus).

usage: python evalcheck/_tt3_verify.py [--limit N]
"""
import collections
import copy
import glob
import os
import pickle
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
import funnel as F                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import trade_tags as TT                         # noqa: E402
import engine as ENG                            # noqa: E402
import DR_RULES_measure as DM                   # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"
PIP = EV.PIP
S1B_FATAL = {"9.10c", "9.33c", "9.36c", "9.40a"}
E5_PANELS = {"9.17b", "9.36c", "9.42b", "9.48b"}   # build's 29-TT3 E5
E3_PANELS = {"9.10c", "9.11b", "9.17b", "9.25a", "9.2b", "9.33c",
             "9.52a"}


def _tol_e(a):
    return max(1.0, 0.25 * a)


def my_box_broken(lo, hi, j_from, j1, c, abr, run_need=3, shock=3.0):
    """Independent recompute of TT.s_box_broken — entry-anchored.
    Returns (bbroken, exit_bar, clause, entry, creep)."""
    j0 = None
    for j in range(max(0, j_from), j1 + 1):
        t = _tol_e(abr[j])
        if lo - t <= c[j] <= hi + t:
            j0 = j
            break
    if j0 is None:
        return False, None, None, None, 0
    run = sgn = 0
    n_up = n_dn = 0
    for j in range(j0 + 1, j1 + 1):
        t = _tol_e(abr[j])
        if c[j] > hi + t:
            d, dist = 1, c[j] - hi
        elif c[j] < lo - t:
            d, dist = -1, lo - c[j]
        else:
            d = 0
        if not d:
            run = sgn = 0
            continue
        n_up += d > 0
        n_dn += d < 0
        if dist >= shock * abr[j]:
            return True, j, "shock", j0, max(n_up, n_dn)
        run = run + 1 if d == sgn else 1
        sgn = d
        if run >= run_need:
            return True, j - run_need + 1, "run3", j0, \
                max(n_up, n_dn)
    return False, None, None, j0, max(n_up, n_dn)


def box_stats_mine(ob, nfed, c, abr):
    """My own box_broken for one engine Obj."""
    g = ob.geometry
    j1 = min(int(g.get("t1_drawn") or
                 (ob.t_right if ob.t_right is not None else nfed)),
             nfed)
    j0 = min(int(ob.t_left), j1)
    return my_box_broken(g["bottom"], g["top"], j0, j1, c, abr)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    print("disk hash:", F.code_hash(F.V1_FILES))
    recs = C.load_tune()
    by_key = {(r["date"], r["window"]["x1"] or 1439): r for r in recs}
    arm_files = sorted(glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H))))
    if args.limit:
        arm_files = arm_files[:args.limit]

    on_params = copy.deepcopy(ENG.load_params())
    on_params["trade_tags"] = 1
    on_params["box_yield"] = 0
    ENG.load_params = lambda: copy.deepcopy(on_params)

    n = same = miss = 0
    recs_used = {}
    box_rows = []            # (date, w1, obj, st) for later legs
    v3_rows = v3_match = 0
    v3_disagree = []
    clause_ct = collections.Counter()
    n_boxes = 0
    hit_boxes = []           # (panel, gi, tau, id, tags)
    for ref in arm_files:
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = by_key.get((date, w1))
        full_x1 = rec["window"]["x1"] or 1439 if rec else w1
        if rec is None:
            base = next((r for r in recs
                         if r["date"] == date
                         and r["window"]["x0"] <= w1
                         <= (r["window"]["x1"] or 1439)), None)
            if base is None:
                miss += 1
                continue
            full_x1 = base["window"]["x1"] or 1439
            rec = dict(base, window=dict(base["window"], x1=w1))
        recs_used[(date, w1)] = rec
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m_day, t, _o, _h, _l,
                          _c, w1, w0=rec["window"]["x0"])
        e_ref = pickle.load(open(ref, "rb"))
        n += 1
        same += (CA.canonical(e) == CA.canonical(e_ref))
        m = np.array([b["cet_min"] for b in e.bars])
        c = np.array([b["c"] for b in e.bars])
        abr = np.asarray(e.abr)
        nfed = len(e.bars) - 1
        live, _em = live_records(e, m_day, rec["window"]["x0"], w1)
        objs = {ob.id: ob for ob in e.objects}
        # ---- v3 independent recompute + clause rates ------------- #
        for r in live:
            ob = objs.get(r["id"])
            if ob is None or EV.FAMILY.get(ob.type) != "box" \
                    or "top" not in ob.geometry:
                continue
            n_boxes += 1
            fam, st = TT.object_stats(
                ob, nfed, e.bars, e.ema, e.abr, e.book.seq)
            clause_ct[st.get("break_clause") or
                      ("broken" if st.get("bbroken") else "clean")] += 1
            mine = box_stats_mine(ob, nfed, c, abr)
            v3_rows += 1
            ok = (bool(st.get("bbroken")) == mine[0]
                  and st.get("exit_bar") == mine[1]
                  and st.get("break_clause") == mine[2]
                  and st.get("entry") == mine[3])
            v3_match += ok
            if not ok and len(v3_disagree) < 8:
                v3_disagree.append((date, r["id"],
                                    (st.get("bbroken"),
                                     st.get("exit_bar"),
                                     st.get("break_clause"),
                                     st.get("entry")), mine))
        # ---- 16-hit leg (box@1 hits at golden taus) ---------------
        # full-window files only: each (panel, gi) hit is evaluated
        # exactly once at its own tau, never via a tau-run file.
        gobjs, _u, _to = EV.gold_objects(rec)
        w0 = rec["window"]["x0"]
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)] if \
            w1 == full_x1 else []
        osc = {ob.id: getattr(ob, "score", None)
               for ob in e.objects}
        for tau in sorted({min(tau_of(g), w1) for g in g2
                           if tau_of(g) is not None
                           and tau_of(g) >= w0}):
            if tau > w1:
                continue
            e_t = DM.pickled(rec["date"], tau)
            if e_t is None:
                continue
            live_t, _ = live_records(e_t, m_day, w0, tau)
            osc_t = {ob.id: getattr(ob, "score", None)
                     for ob in e_t.objects}
            for r in live_t:
                r["score"] = osc_t.get(r["id"])
            ranked = RK.rank_live(live_t, RK.score_map(e_t))
            fr = collections.defaultdict(list)
            for r in ranked:
                ff = EV.FAMILY.get(r["type"])
                if ff:
                    fr[ff].append(r)
            pick = fr.get("box", [])[:1]
            if not pick:
                continue
            r0 = pick[0]
            ob_t = next((o for o in e_t.objects if o.id == r0["id"]),
                        None)
            st = {}
            if ob_t is not None:
                _f, st = TT.object_stats(
                    ob_t, len(e_t.bars) - 1, e_t.bars, e_t.ema,
                    e_t.abr, e_t.book.seq)
            for gi, g in enumerate(
                    [g for g in g2
                     if EV.FAMILY.get(g["spec_type"]) == "box"
                     and min(tau_of(g), w1) == tau]):
                if not V2.match(g, r0, m_day):
                    continue
                tags = TT.tags_from_stats(_f, st) if st else set()
                hit_boxes.append((rec["id"], gi, tau, r0["id"],
                                  sorted(tags),
                                  st.get("break_clause"),
                                  st.get("exit_bar")))
    print("canonical ON==C-3-arm: %d/%d (miss %d)" % (same, n, miss))
    print("v3 recompute: %d/%d match" % (v3_match, v3_rows),
          v3_disagree[:4])
    print("live box clause rates (n=%d): %s" % (n_boxes, dict(clause_ct)))
    print("box@1 hits evaluated: %d" % len(hit_boxes))
    tagged_hits = [x for x in hit_boxes
                   if "box_broken" in x[4]]
    print("hits tagged box_broken: %d/16-ish -> %s"
          % (len(tagged_hits),
             [(x[0], x[2], x[5], x[6]) for x in tagged_hits][:20]))

    # ---- golden compliance: author boxes tagged at own tau -------- #
    print("\n=== golden compliance (author boxes at own tau) ===")
    g_tot = g_tag = 0
    g_clause = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        t, m, o, h, l, c = CA.bars(rec["date"])
        m = np.asarray(m)
        abr = CA.abr(rec["date"])
        for g in g2:
            if EV.FAMILY.get(g["spec_type"]) != "box":
                continue
            g_tot += 1
            lo = g.get("price_lo") or g.get("price0")
            hi = g.get("price_hi") or g.get("price1")
            tau = tau_of(g)
            if not lo or not hi or g.get("t0") is None or \
                    tau is None or not (w0 <= tau <= w1):
                g_clause["unevaluated"] += 1
                continue
            lo, hi = lo / PIP, hi / PIP
            j_from = int(np.searchsorted(m, g["t0"]))
            j1 = min(int(np.searchsorted(m, min(tau, w1), "right"))
                     - 1, len(m) - 1)
            bb, xb, cl, ent, cr = my_box_broken(
                lo, hi, j_from, j1, np.asarray(c), np.asarray(abr))
            g_tag += bb
            g_clause[cl or "clean"] += 1
    print("author boxes tagged at own tau: %d/%d = %.3f | %s"
          % (g_tag, g_tot, g_tag / max(g_tot, 1), dict(g_clause)))

    # ---- S1b fatal + E5 panels: tagged? exit_bar? ------------------ #
    print("\n=== S1b-fatal / E5 panels: live boxes at review tau ===")
    for pid in sorted(S1B_FATAL | E5_PANELS | E3_PANELS):
        rec = next((r for r in recs if r["id"] == pid), None)
        if rec is None:
            continue
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        taus = sorted({min(tau_of(g), w1) for g in g2
                       if tau_of(g) is not None and tau_of(g) >= w0})
        tau = taus[-1] if taus else w1
        e = DM.pickled(rec["date"], tau)
        if e is None:
            continue
        m = np.array([b["cet_min"] for b in e.bars])
        live, _ = live_records(e, m, w0, tau)
        out = []
        for r in live:
            ob = next((o for o in e.objects if o.id == r["id"]), None)
            if ob is None or EV.FAMILY.get(ob.type) != "box":
                continue
            _f, st = TT.object_stats(
                ob, len(e.bars) - 1, e.bars, e.ema, e.abr,
                e.book.seq)
            out.append("%s:%s%s" % (r["id"],
                                    "BROKEN" if st.get("bbroken")
                                    else "clean",
                                    "@%d/%s" % (st.get("exit_bar") or
                                                -1,
                                                st.get("break_clause"))
                                    if st.get("bbroken") else ""))
        print("  %-6s tau=%-4d %s" % (pid, tau, " | ".join(out)))

    # ---- prefix invariance: ON-run facts snapshot at tau vs -------
    # post-hoc tags on the truncated arm run (geometry frozen at tau).
    # A box's drawn band rewrites as bars arrive, so final-geometry
    # post-hoc stats on the full run cannot reproduce the at-tau tag;
    # snapshot facts per bar instead (engine-side, observability only).
    print("\n=== prefix invariance (ON-run facts@tau vs cut-run) ===")
    import random
    rng = random.Random(83)
    snap = {}
    orig_step = ENG.PerceptionEngine._trade_tag_step

    def _snap_step(self, i):
        orig_step(self, i)
        if self.p.get("trade_tags"):
            snap[i] = {ob.id: dict(ob.facts.get("trade_tags", {}))
                       for ob in self.active()}

    ENG.PerceptionEngine._trade_tag_step = _snap_step
    try:
        for rec in rng.sample(recs, 5):
            w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
            gobjs, _u, _to = EV.gold_objects(rec)
            g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
            taus = sorted({min(tau_of(g), w1) for g in g2
                           if tau_of(g) is not None and tau_of(g) >= w0})
            if not taus:
                continue
            tau = taus[0]
            e_cut = DM.pickled(rec["date"], tau)
            if e_cut is None:
                continue
            snap.clear()
            t, m, o, h, l, c = CA.bars(rec["date"])
            e_full_on = EV.run_engine(ENG.PerceptionEngine, m, t, o,
                                      h, l, c, w1, w0=w0)
            m_f = np.array([b["cet_min"] for b in e_full_on.bars])
            jt = int(np.searchsorted(m_f, tau, "right")) - 1
            live_tau = snap.get(jt) or {}
            ok = bad = 0
            diffs = []
            full_objs = {ob.id: ob for ob in e_full_on.objects}
            for ob in e_cut.objects:
                if EV.FAMILY.get(ob.type) != "box" or \
                        "top" not in ob.geometry or \
                        ob.state != "ACTIVE":
                    continue
                _f, st = TT.object_stats(
                    ob, len(e_cut.bars) - 1, e_cut.bars, e_cut.ema,
                    e_cut.abr, e_cut.book.seq)
                cut_tag = ("box_broken" in TT.tags_from_stats(_f, st),
                           st.get("exit_bar"), st.get("break_clause"))
                s = live_tau.get(ob.id)
                fo = full_objs.get(ob.id)
                anchor_same = fo is not None and fo.t_left == ob.t_left
                full_tag = None if s is None else (
                    "box_broken" in s.get("tags", []),
                    s.get("exit_bar"), s.get("break_clause"))
                if s is None or not anchor_same or full_tag != cut_tag:
                    bad += 1
                    diffs.append((ob.id, cut_tag, full_tag,
                                  anchor_same))
                else:
                    ok += 1
            print("  %s tau=%d boxes=%d ok=%d bad=%d %s"
                  % (rec["id"], tau, ok + bad, ok, bad,
                     diffs[:3] if diffs else ""))
    finally:
        ENG.PerceptionEngine._trade_tag_step = orig_step


if __name__ == "__main__":
    main()
