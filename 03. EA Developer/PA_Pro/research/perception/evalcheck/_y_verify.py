"""EVAL-AUDIT R83 s.83.4 arm-Y verify (box_yield).

Independent checks vs build's 30-Y report:
  1. M1 row on my own scorer: fresh engines box_yield=1 / =2 over the
     canonical (date,w1) arm grid; golden hits at decision taus under
     fam budgets box1/level1/line2/bracket1 (recall_at_k semantics).
  2. Census clutter median (full-window files: n_eng/n_gold).
  3. Flip recount vs parent arm picks (per (panel,tau,fam)).
  4. Yield mechanics on my own Y1 engines: every 'yield_broken' close
     - s_box_broken recomputed True on the dead object's final
       geometry at t_right; UIP-type objects included.
  5. Y1==Y2 claim: identical hit sets.
  6. Prefix invariance: canonical() snapshot at golden-tau bars inside
     a full run == canonical() of the stop-at-tau engine (10 panels).

usage: python evalcheck/_y_verify.py [--limit N]
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
from snapshot import tau_of, live_records       # noqa: E402
from _tt3_verify import my_box_broken           # noqa: E402

ARM_V, ARM_H = "uip2_pbbirth", "8361fe85e73f9437"
TOPK = {"box": 1, "level": 1, "line": 2, "bracket": 1}


def run_variant(flag, recs_by_key, arm_files):
    """One pass: fresh engines box_yield=flag over the arm grid."""
    base = copy.deepcopy(ENG.load_params())
    base["box_yield"] = flag
    ENG.load_params = lambda: copy.deepcopy(base)

    hits = collections.Counter()
    tot = collections.Counter()
    picks = {}                    # (date,w1,fam) -> [(id,matched)]
    ratios = []
    kills = []                    # yield_broken objects (for leg 4)
    ran = 0
    for ref in arm_files:
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = recs_by_key.get((date, w1))
        if rec is None:
            continue
        w0 = rec["window"]["x0"]
        full_x1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(date)
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c,
                          w1, w0=w0)
        ran += 1
        # M1 hits at this w1 (goldens deciding exactly at w1)
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, w1)]
        g_tau = [g for g in g2
                 if tau_of(g) is not None
                 and min(tau_of(g), full_x1) == w1]
        m = np.asarray(m)
        live, _ = live_records(e, m, w0, w1)
        osc = {ob.id: getattr(ob, "score", None) for ob in e.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        ranked = RK.rank_live(live, RK.score_map(e))
        fr = collections.defaultdict(list)
        for r in ranked:
            ff = EV.FAMILY.get(r["type"])
            if ff:
                fr[ff].append(r)
        for fam, k in TOPK.items():
            top = fr.get(fam, [])[:k]
            gf = [g for g in g_tau if EV.FAMILY.get(g["spec_type"])
                  == fam]
            pk = []
            for r in top:
                hit = any(V2.match(g, r, m) for g in gf)
                pk.append((r["id"], hit))
            picks[(date, w1, fam)] = pk
            for g in gf:
                tot[fam] += 1
                hits[fam] += any(V2.match(g, r, m) for r in top)
        # census on full-window files
        if w1 == full_x1:
            n_gold = len(g2)
            if n_gold:
                ratios.append(len(V2.eng_objects(e, m, w0, w1))
                              / n_gold)
        # yield mechanics
        for ob in e.objects:
            if any(cd == "close" and d == "yield_broken"
                   for _b, cd, d in getattr(ob, "events", ())):
                kills.append((date, w1, ob))
    return {"hits": hits, "tot": tot, "picks": picks,
            "ratios": ratios, "kills": kills, "ran": ran}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    print("disk hash:", F.code_hash(F.V1_FILES))
    recs = list(C.load_tune())
    by_key = {(r["date"], r["window"]["x1"] or 1439): r for r in recs}
    arm_files = sorted(glob.glob(os.path.join(
        CA.CACHE, "run_%s_%s_*.pkl" % (ARM_V, ARM_H))))
    if args.limit:
        arm_files = arm_files[:args.limit]
    # extend by_key: tau w1 -> base panel rec.  Same-date panels
    # share the day (66 dates): attribute by which panel actually has
    # a scorable golden deciding at w1, else first containing.
    by_date = collections.defaultdict(list)
    for r in recs:
        by_date[r["date"]].append(r)

    def base_rec(date, w1):
        r = by_key.get((date, w1))
        if r:
            return r
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
    keys = {}
    for ref in arm_files:
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        keys[(date, int(w1s))] = base_rec(date, int(w1s))
    keys = {k: v for k, v in keys.items() if v is not None}

    # ---- parent picks for the flip leg --------------------------- #
    par_picks = {}
    for ref in arm_files:
        stem = os.path.basename(ref)[:-4]
        date, w1s = stem.rsplit("_", 2)[1:]
        w1 = int(w1s)
        rec = keys.get((date, w1))
        if rec is None:
            continue
        e = pickle.load(open(ref, "rb"))
        w0 = rec["window"]["x0"]
        t, m, o, h, l, c = CA.bars(date)
        m = np.asarray(m)
        live, _ = live_records(e, m, w0, w1)
        osc = {ob.id: getattr(ob, "score", None) for ob in e.objects}
        for r in live:
            r["score"] = osc.get(r["id"])
        ranked = RK.rank_live(live, RK.score_map(e))
        fr = collections.defaultdict(list)
        for r in ranked:
            ff = EV.FAMILY.get(r["type"])
            if ff:
                fr[ff].append(r)
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, rec["window"]["x1"] or 1439)]
        g_tau = [g for g in g2
                 if tau_of(g) is not None
                 and min(tau_of(g), rec["window"]["x1"] or 1439)
                 == w1]
        for fam, k in TOPK.items():
            top = fr.get(fam, [])[:k]
            gf = [g for g in g_tau
                  if EV.FAMILY.get(g["spec_type"]) == fam]
            par_picks[(date, w1, fam)] = [
                (r["id"], any(V2.match(g, r, m) for g in gf))
                for r in top]

    res = {}
    for flag in (1, 2):
        res[flag] = run_variant(flag, keys, arm_files)

    for flag in (1, 2):
        r = res[flag]
        print("\n==== box_yield=%d over %d runs ====" % (flag, r["ran"]))
        print("M1: " + " ".join(
            "%s %d/%d" % (f, r["hits"][f], r["tot"][f])
            for f in ("box", "level", "line", "bracket")))
        print("census clutter median %.2f (panels %d)"
              % (float(np.median(r["ratios"])), len(r["ratios"])))
        # flips
        gained = collections.Counter()
        lost = collections.Counter()
        for k_, pk in r["picks"].items():
            fam = k_[2]
            pp = par_picks.get(k_, [])
            y_hit = any(m for _i, m in pk)
            p_hit = any(m for _i, m in pp)
            if p_hit and not y_hit:
                lost[fam] += 1
            elif y_hit and not p_hit:
                gained[fam] += 1
        print("flips vs parent: " + "; ".join(
            "%s -%d/+%d" % (f, lost[f], gained[f])
            for f in ("box", "level", "line", "bracket")))

    # ---- leg 4: yield mechanics on Y1 kills ----------------------- #
    ks = res[1]["kills"]
    seen = set()
    uniq = []
    for k3 in ks:
        key = (k3[0], k3[2].id, k3[2].t_right)
        if key not in seen:
            seen.add(key)
            uniq.append(k3)
    print("\nyield_broken kills (Y1): %d runs, %d distinct"
          % (len(ks), len(uniq)))
    ok = bad = uip = 0
    for date, w1, ob in uniq[:60]:
        g = ob.geometry
        if "top" not in g:
            continue
        t, m, o, h, l, c = CA.bars(date)
        j = min(int(ob.t_right or len(m) - 1), len(m) - 1)
        abr = CA.abr(date)
        bb, xb, cl, ent, cr = my_box_broken(
            g["bottom"], g["top"], min(int(ob.t_left), j), j,
            np.asarray(c), np.asarray(abr))
        ok += bb
        bad += (not bb)
        if ob.geometry.get("meta_uip_persist"):
            uip += 1
    print("  kills where my s_box_broken agrees at t_right: %d/%d"
          % (ok, ok + bad), "| uip_persist kills:", uip)

    # ---- leg 5: Y1 == Y2 ------------------------------------------ #
    same = all(res[1]["picks"].get(k) == res[2]["picks"].get(k)
               for k in res[1]["picks"])
    print("\nY1==Y2 picks identical:", same,
          "| kills y1 %d y2 %d" % (len(res[1]["kills"]),
                                   len(res[2]["kills"])))

    # ---- leg 6: prefix invariance on Y1 (10 panels) ---------------- #
    print("\n=== prefix invariance Y1 (10 panels) ===")
    base = copy.deepcopy(ENG.load_params())
    base["box_yield"] = 1
    n_ok = n_tot = 0
    for rec in recs[:10]:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        g2 = [g for g in EV.gold_objects(rec)[0]
              if V2.scorable(g, w0, w1)]
        taus = sorted({min(tau_of(g), w1) for g in g2
                       if tau_of(g) is not None and tau_of(g) >= w0})
        if not taus:
            continue
        t, m, o, h, l, c = CA.bars(rec["date"])
        m = np.asarray(m)
        idx = np.where(m <= w1)[0]
        snap_at = {int(np.where(m <= tau)[0][-1]): tau
                   for tau in taus}
        e2 = ENG.PerceptionEngine(copy.deepcopy(base))
        e2.w0_min = w0
        e2.cand_log = []
        snap = {}
        for j in idx:
            e2.update(int(t[j]), float(o[j]) * 1e-4,
                      float(h[j]) * 1e-4, float(l[j]) * 1e-4,
                      float(c[j]) * 1e-4, cet_min=int(m[j]))
            if j in snap_at:
                snap[snap_at[j]] = CA.canonical(e2)
        for tau in taus:
            e_s = EV.run_engine(
                lambda b=base: ENG.PerceptionEngine(copy.deepcopy(b)),
                m, t, o, h, l, c, tau, w0=w0)
            n_tot += 1
            n_ok += CA.canonical(e_s) == snap[tau]
    print("prefix invariance Y1: %d/%d" % (n_ok, n_tot))


if __name__ == "__main__":
    main()
