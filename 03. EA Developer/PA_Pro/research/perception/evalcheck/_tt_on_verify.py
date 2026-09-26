"""EVAL-AUDIT R78/79.3 step-1 verify (ON arm): run the on-disk engine
with trade_tags=1 on every cached C-3 window and check:

  1. canonical() identical to the uip2_pbbirth@8361fe85 arm cache
     (ON == parent, transitively ON == OFF since OFF == parent);
  2. every live object carries facts["trade_tags"] (ON payload);
  3. OFF-run objects carry no trade_tags facts (control);
  4. tag-equivalence: TT.object_stats == DR_RULES_measure.eng_stats
     on a sample of live objects (same inputs -> same stats);
  5. tradeable fraction of picked objects per family (recount of
     build's s.27-TT numbers).

usage: python evalcheck/_tt_on_verify.py [--limit N]
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

    # ---- patch load_params ONCE: trade_tags=1 --------------------- #
    base_params = ENG.load_params()
    on_params = copy.deepcopy(base_params)
    on_params["trade_tags"] = 1
    _orig = ENG.load_params
    ENG.load_params = lambda: copy.deepcopy(on_params)

    n = same = facts_on = miss = 0
    eq_rows = eq_match = 0
    frac = collections.defaultdict(lambda: [0, 0])
    diffs = []
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
        # facts payload
        live, _em = live_records(e, m_day, rec["window"]["x0"], w1)
        for r in live:
            ob = next((o for o in e.objects if o.id == r["id"]), None)
            if ob is not None and \
                    "trade_tags" in getattr(ob, "facts", {}):
                facts_on += 1
        # equivalence spot-check: first 3 live objects per run
        m = np.array([b["cet_min"] for b in e.bars])
        o = np.array([b["o"] for b in e.bars])
        h = np.array([b["h"] for b in e.bars])
        l = np.array([b["l"] for b in e.bars])
        c = np.array([b["c"] for b in e.bars])
        ema = np.asarray(e.ema)
        abr = np.asarray(e.abr)
        nfed = len(e.bars) - 1
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
                continue          # no-rule families: {} by design
            eq_rows += 1
            keys = set(st_new) | set(st_old)
            ok = all(st_new.get(k) == st_old.get(k)
                     or (isinstance(st_new.get(k), float)
                         and isinstance(st_old.get(k), float)
                         and abs(st_new[k] - st_old[k]) < 1e-9)
                     for k in keys)
            eq_match += ok
        # tradeable fraction on picked objects at golden taus
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
                    frac[fam][1] += 1
                    if tg and tg["tradeable"]:
                        frac[fam][0] += 1
    ENG.load_params = _orig
    # ---- OFF control: one window, default params ------------------ #
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
    print("object_stats==eng_stats: %d/%d" % (eq_match, eq_rows))
    print("tradeable fraction of picks by family:")
    for f in ("box", "level", "line", "bracket"):
        a, b = frac[f]
        print("  %-7s %d/%d = %.3f" % (f, a, b, a / b if b else 0))
    for d in diffs[:10]:
        print("  DIFF", d)


if __name__ == "__main__":
    main()
