"""EVAL-AUDIT R81 s.81.5(1) verify (TT-2 ON arm): run the on-disk
engine with trade_tags=1 on every cached C-3 window and check:

  1. canonical() identical to the uip2_pbbirth@8361fe85 arm cache
     (ON == parent; OFF == parent covered by the freeze check);
  2. every live object carries facts["trade_tags"] (ON payload);
  3. OFF-run objects carry no trade_tags facts (control);
  4. tag-equivalence on the SHARED v1 stat keys:
     TT.object_stats == DR_RULES_measure.eng_stats where both emit
     the key (eng_stats has no v2 fields);
  5. independent v2 recompute: line_broken / line_cuts_bodies /
     stale_far recomputed by an in-file implementation (no shared
     code) on sampled objects, compared with the emitted stats;
  6. tradeable fraction of picked objects per family under
     v1-hide (TRADE_VIEW_HIDE minus the three v2 tags) and v1+v2.

usage: python evalcheck/_tt2_on_verify.py [--limit N]
"""
import collections
import copy
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

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
import eval_v2 as V2                            # noqa: E402
import funnel as F                              # noqa: E402
import engine as ENG                            # noqa: E402
import trade_tags as TT                         # noqa: E402
import DR_RULES_measure as DM                   # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402

ARM_H = "8361fe85e73f9437"
ARM_V = "uip2_pbbirth"
FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
V1_HIDE = TT.TRADE_VIEW_HIDE - {"line_broken", "line_cuts_bodies",
                               "stale_far"}
PIP = 1e4


def _tol_e(a):
    """engine edge tol (pip scale), mirrored from trade_tags.tol_e."""
    return max(1.0, 0.25 * a)


def my_line_broken(g, jb, j1, c, abr, n_need=2):
    """Independent recompute of TT.s_line_broken (no shared code)."""
    side = g.get("side")
    p0, slope, tb = g["p0"], g["slope"], g["t0"]
    run = 0
    for j in range(jb, j1 + 1):
        lv = p0 + slope * (j - tb)
        t = _tol_e(abr[j])
        if side == "top":
            thru = c[j] > lv + t
        elif side == "bottom":
            thru = c[j] < lv - t
        else:
            thru = abs(c[j] - lv) > t
        run = run + 1 if thru else 0
        if run >= n_need:
            return True
    return False


def my_line_cuts(g, j0, j1, o, c, abr, n_need=2):
    """Independent recompute of TT.s_line_cuts."""
    p0, slope, tb = g["p0"], g["slope"], g["t0"]
    n = 0
    for j in range(j0, j1 + 1):
        lv = p0 + slope * (j - tb)
        blo, bhi = min(o[j], c[j]), max(o[j], c[j])
        t = _tol_e(abr[j])
        if blo + t < lv < bhi - t:
            n += 1
            if n >= n_need:
                return True, n
    return False, n


def my_stale_far(fam, g, jb, j1, h, l, c, abr,
                 abr_mult=3.0, gap_need=24):
    """Independent recompute of TT.s_stale_far."""
    a = abr[j1]
    cc = c[j1]
    if fam == "box":
        lo, hi = g["bottom"], g["top"]
        dist = 0.0 if lo <= cc <= hi else min(abs(cc - lo),
                                              abs(cc - hi))
    elif fam == "level":
        dist = abs(cc - g["price"])
    else:
        dist = abs(cc - (g["p0"] + g["slope"] * (j1 - g["t0"])))
    if dist <= abr_mult * a:
        return False
    last = None
    for j in range(j1, -1, -1):
        t = _tol_e(abr[j])
        if fam == "box":
            touched = l[j] <= hi + t and h[j] >= lo - t
        elif fam == "level":
            touched = l[j] <= g["price"] + t and h[j] >= g["price"] - t
        else:
            v = g["p0"] + g["slope"] * (j - g["t0"])
            touched = l[j] <= v + t and h[j] >= v - t
        if touched:
            last = j
            break
    gap = (j1 - last) if last is not None else \
        (j1 - jb if jb is not None else j1)
    return gap > gap_need


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    h_now = F.code_hash(F.V1_FILES)
    print("disk hash:", h_now)
    recs = C.load_tune()
    by_key = {(r["date"], r["window"]["x1"] or 1439): r for r in recs}
    arm_files = sorted(glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H))))
    if args.limit:
        arm_files = arm_files[:args.limit]

    base_params = ENG.load_params()
    on_params = copy.deepcopy(base_params)
    on_params["trade_tags"] = 1
    _orig = ENG.load_params
    ENG.load_params = lambda: copy.deepcopy(on_params)

    n = same = facts_on = miss = 0
    eq_rows = eq_match = 0
    v2_rows = v2_match = 0
    v2_disagree = []
    frac = collections.defaultdict(lambda: [0, 0, 0])
    for ref in arm_files:
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = by_key.get((date, w1))
        if rec is None:
            base = next((r for r in recs
                         if r["date"] == date
                         and r["window"]["x0"] <= w1
                         <= (r["window"]["x1"] or 1439)), None)
            if base is None:
                miss += 1
                continue
            rec = dict(base, window=dict(base["window"], x1=w1))
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m_day, t, _o, _h, _l,
                          _c, w1, w0=rec["window"]["x0"])
        e_ref = pickle.load(open(ref, "rb"))
        n += 1
        same += (CA.canonical(e) == CA.canonical(e_ref))
        live, _em = live_records(e, m_day, rec["window"]["x0"], w1)
        for r in live:
            ob = next((o for o in e.objects if o.id == r["id"]), None)
            if ob is not None and \
                    "trade_tags" in getattr(ob, "facts", {}):
                facts_on += 1
        m = np.array([b["cet_min"] for b in e.bars])
        o = np.array([b["o"] for b in e.bars])
        h = np.array([b["h"] for b in e.bars])
        l = np.array([b["l"] for b in e.bars])
        c = np.array([b["c"] for b in e.bars])
        ema = np.asarray(e.ema)
        abr = np.asarray(e.abr)
        nfed = len(e.bars) - 1
        # v1-key equivalence + v2 independent recompute, 3 objs/run
        for r in live[:3]:
            ob = next((o2 for o2 in e.objects if o2.id == r["id"]),
                      None)
            if ob is None:
                continue
            fam, st_new = TT.object_stats(
                ob, nfed, {"m": m, "o": o, "h": h, "l": l, "c": c},
                ema, abr, e.book.seq)
            st_old = DM.eng_stats(ob, m, o, h, l, c, ema, abr,
                                  e.book.seq, nfed)
            if fam is None:
                continue
            eq_rows += 1
            shared = set(st_new) & set(st_old)
            ok = all(st_new.get(k) == st_old.get(k)
                     or (isinstance(st_new.get(k), float)
                         and isinstance(st_old.get(k), float)
                         and abs(st_new[k] - st_old[k]) < 1e-9)
                     for k in shared)
            eq_match += ok
            # ---- independent v2 recompute on this object -------- #
            g = ob.geometry
            j1 = st_new["j1"]
            if fam == "line" and "p0" in g:
                ja = min(g.get("meta_anchors") or [int(g["t0"])])
                ja = max(0, min(ja, j1))
                lc_mine, lc_n = my_line_cuts(g, ja, j1, o, c, abr)
                if ob.t_birth is not None:
                    lb_mine = my_line_broken(g, int(ob.t_birth), j1,
                                             c, abr)
                    lb_ref = bool(st_new.get("lbroken"))
                else:
                    lb_mine = lb_ref = "n/a (no t_birth)"
                v2_rows += 1
                ok2 = (lb_mine == lb_ref
                       and lc_mine == bool(st_new.get("lcuts")))
                v2_match += ok2
                if not ok2 and len(v2_disagree) < 10:
                    v2_disagree.append(
                        (date, r["id"], "line",
                         st_new.get("lbroken"), lb_mine,
                         bool(st_new.get("lcuts")), lc_mine))
            have_geom = (fam == "box" and "top" in g) or \
                (fam == "level" and "price" in g) or \
                (fam == "line" and "p0" in g)
            if have_geom:
                sf_mine = my_stale_far(fam, g,
                                       int(ob.t_birth)
                                       if ob.t_birth is not None
                                       else None, j1, h, l, c, abr)
                v2_rows += 1
                ok3 = sf_mine == bool(st_new.get("stale"))
                v2_match += ok3
                if not ok3 and len(v2_disagree) < 10:
                    v2_disagree.append(
                        (date, r["id"], fam,
                         bool(st_new.get("stale")), sf_mine))
        # tradeable fractions on picks at golden taus: v1 vs v1+v2
        gobjs, _u, _to = EV.gold_objects(rec)
        w0 = rec["window"]["x0"]
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for tau in sorted({min(tau_of(g), w1) for g in g2
                           if tau_of(g) is not None
                           and tau_of(g) >= w0}):
            if tau > w1:
                continue
            live2, _e2 = live_records(e, m_day, w0, tau)
            ranked = RK.rank_live(live2, RK.score_map(e))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                ff = EV.FAMILY.get(r["type"])
                if ff:
                    fam_ranked[ff].append(r)
            for fam, k in FAM_BUDGET.items():
                for r in fam_ranked.get(fam, [])[:k]:
                    ob = next((o3 for o3 in e.objects
                               if o3.id == r["id"]), None)
                    if ob is None:
                        continue
                    tg = getattr(ob, "facts", {}).get("trade_tags")
                    frac[fam][2] += 1
                    if tg:
                        ts = set(tg["tags"])
                        if not (ts & V1_HIDE):
                            frac[fam][0] += 1
                        if tg["tradeable"]:
                            frac[fam][1] += 1
    ENG.load_params = _orig
    off_facts = -1
    for ref in arm_files:
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        rec = by_key.get((date, int(w1s)))
        if rec is None:
            continue
        t, m_day, _o, _h, _l, _c = CA.bars(rec["date"])
        e0 = EV.run_engine(ENG.PerceptionEngine, m_day, t, _o, _h,
                           _l, _c, rec["window"]["x1"] or 1439,
                           w0=rec["window"]["x0"])
        off_facts = sum(1 for ob in e0.objects
                        if "trade_tags" in getattr(ob, "facts", {}))
        break
    print("canonical ON==parent: %d/%d (miss %d)" % (same, n, miss))
    print("objects carrying facts['trade_tags'] (OFF control):",
          off_facts)
    print("objects carrying facts['trade_tags'] (ON):", facts_on)
    print("shared-key stats equivalence: %d/%d" % (eq_match, eq_rows))
    print("v2 stats independent recompute: %d/%d"
          % (v2_match, v2_rows))
    print("tradeable fraction of picks by family (v1 | v1+v2):")
    for f in ("box", "level", "line", "bracket"):
        a, b, tot = frac[f]
        print("  %-7s %d/%d = %.3f | %d/%d = %.3f"
              % (f, a, tot, a / tot if tot else 0,
                 b, tot, b / tot if tot else 0))
    for d in v2_disagree[:10]:
        print("  V2-DISAGREE", d)


if __name__ == "__main__":
    main()
