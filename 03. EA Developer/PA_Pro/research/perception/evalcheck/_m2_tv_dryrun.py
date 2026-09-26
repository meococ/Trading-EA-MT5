"""EVAL-AUDIT R82 s.82.5(4) dry run — M2-TV pool counts only.

Placeholder engine: C-3 @fa2e52e5 + trade_tags=1.  Outputs POOL
COUNTS per family and class.  No PNG, no key, nothing the Owner
sees (per the dry-run clause).

Pools (M2_TV_PLAN.md as amended by s.82.5):
- ENGINE: for every golden-decision tau on each TUNE panel (minus
  the p099-p102 panels), live objects ranked per recall_at_k under
  the per-family budget; kept iff no TRADE_VIEW_HIDE tag at tau.
  Deduped by (panel, object id).
- GOLDEN: scorable golden objects at their own tau with no hide
  tag (golden conventions from _tt2_report_verify), deduped by
  (panel, gi), minus the four panels.
- NEGATIVE feasibility: engine-pool objects available for the
  audited mutations (count only).
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))

import numpy as np                              # noqa: E402
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import recall_at_k as RK                        # noqa: E402
import trade_tags as TT                         # noqa: E402
import DR_RULES_measure as DM                   # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402
from _tt2_report_verify import (gold_v2_stats,  # noqa: E402
                               tags_golden_v1)

FAM_BUDGET = {"box": 1, "line": 2, "level": 1, "bracket": 1}
EXCLUDE_PANELS = {"9.46a", "9.34b", "9.1a", "9.30c"}   # p099-p102
PIP = 1e4


def main():
    recs = [r for r in C.load_tune()
            if r["id"] not in EXCLUDE_PANELS]
    print("panels in scope: %d (excluded 4 calib panels)" % len(recs))

    # ---------------- ENGINE pool ------------------------------ #
    eng_pool = {}          # (panel,id) -> {fam, taus:set}
    n_tau = n_live_eval = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        taus = sorted({min(tau_of(g), w1) for g in g2
                       if tau_of(g) is not None
                       and tau_of(g) >= w0})
        for tau in taus:
            if tau > w1:
                continue
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            n_tau += 1
            m = np.array([b["cet_min"] for b in e.bars])
            live, _em = live_records(e, m, w0, tau)
            ranked = RK.rank_live(live, RK.score_map(e))
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                ff = EV.FAMILY.get(r["type"])
                if ff:
                    fam_ranked[ff].append(r)
            objs = {ob.id: ob for ob in e.objects}
            nfed = len(e.bars) - 1
            for fam, k in FAM_BUDGET.items():
                for r in fam_ranked.get(fam, [])[:k]:
                    ob = objs.get(r["id"])
                    if ob is None:
                        continue
                    n_live_eval += 1
                    ff, st = TT.object_stats(
                        ob, nfed, e.bars, e.ema, e.abr,
                        e.book.seq)
                    if ff is None:
                        # no-rule family: tradeable by design
                        trade = True
                    else:
                        tags = TT.tags_from_stats(ff, st)
                        trade = not (tags & TT.TRADE_VIEW_HIDE)
                    if not trade:
                        continue
                    key = (rec["id"], r["id"])
                    d = eng_pool.setdefault(
                        key, {"fam": fam, "taus": set()})
                    d["taus"].add(tau)
    eng_fam = collections.Counter(v["fam"] for v in eng_pool.values())
    print("engine taus evaluated: %d | pick evaluations: %d"
          % (n_tau, n_live_eval))
    print("ENGINE pool (unique panel,id tradeable picks):")
    for f in ("box", "level", "line", "bracket"):
        print("  %-7s %d" % (f, eng_fam.get(f, 0)))

    # ---------------- GOLDEN pool ------------------------------ #
    gold_rows = [json.loads(x) for x in open(
        os.path.join(PERC, "deepresearch", "DR_RULES_golden.jsonl"),
        encoding="utf8")]
    gold_by = collections.defaultdict(list)
    for r in gold_rows:
        gold_by[(r["panel"], r["tau"])].append(r)
    gold_pool = {}         # (panel,gi) -> fam
    for rec in recs:
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, rec["window"]["x0"],
                                            w1)]
        rows_here = [r for (p, tau), rs in gold_by.items()
                     if p == rec["id"] for r in rs]
        by_tau = collections.defaultdict(list)
        for r in rows_here:
            by_tau[r["tau"]].append(r)
        for tau, trs in sorted(by_tau.items()):
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            m = np.array([b["cet_min"] for b in e.bars])
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            for r in trs:
                g = g2[r["gi"]] if r["gi"] < len(g2) else None
                if g is None:
                    continue
                fam = r["fam"]
                t_v1 = tags_golden_v1(r)
                if t_v1 & TT.TRADE_VIEW_HIDE:
                    continue
                st2 = gold_v2_stats(g, fam, m, o, h, l, c, abr, tau)
                if st2.get("lbroken") or st2.get("lcuts") \
                        or st2.get("stale"):
                    continue
                gold_pool[(rec["id"], r["gi"])] = fam
    gold_fam = collections.Counter(gold_pool.values())
    print("GOLDEN pool (unique panel,gi, no hide tag):")
    for f in ("box", "level", "line", "bracket"):
        print("  %-7s %d" % (f, gold_fam.get(f, 0)))

    # ---------------- feasibility vs 50-item design ------------- #
    print("NEGATIVE source pool = engine pool objects "
          "(mutation re-tags): %d candidates"
          % sum(eng_fam.values()))
    print("design needs: engine 30 (>=6/fam), golden 10, "
          "negative 10")


if __name__ == "__main__":
    main()
