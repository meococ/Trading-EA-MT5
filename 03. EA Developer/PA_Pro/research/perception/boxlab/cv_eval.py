"""cv_eval.py — R23 §23.3 / R25 §25.6: leave-one-day-out CV of a lab
round's frozen score, day-bootstrap CIs, and the barrier sign per
fold.

Weights are FROZEN (hand-set on all 108 goldens — nothing is fitted
per fold).  The CV therefore bounds fold-level variance of the fixed
scorer; it does NOT remove the global hand-tuning bias.  Stated
per the ruling: "freeze them across folds ... and say which" — frozen.

Folds: select_eval.folds (day-level 5-fold, day j -> fold j%5), the
same split LEVEL-LAB uses.

Usage: python cv_eval.py lab_r33 lab_r37 [more tags]
"""
import collections
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
for _p in (_HERE, _PERC, os.path.join(_PERC, "evalcheck"),
           os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, os.path.abspath(_p))

import common as C          # noqa: E402
import eval as EV           # noqa: E402
import funnel as FN         # noqa: E402
from select_eval import folds  # noqa: E402  same day folds as LEVEL-LAB

CACHE = os.path.join(_HERE, "cache")


def _panel_rows(tag):
    ev = json.load(open(os.path.join(CACHE, "eval_%s.json" % tag)))
    recs = {r["id"]: r for r in C.load_tune()}
    rows = []
    for pan in ev["panels"]:
        rows.append({"date": recs[pan["id"]]["date"], **pan})
    return rows, ev


def _metrics(rows):
    ng = sum(r["n_gold_box"] for r in rows)
    if not ng:
        return {}
    return {"born": sum(r["born_hit"] for r in rows) / ng,
            "r_at1": sum(r["rec_at1"] for r in rows) / ng,
            "r_at2": sum(r["rec_at2"] for r in rows) / ng,
            "ink": sum(r["n_born_box"] for r in rows) / max(len(rows), 1),
            "oracle": sum(r["oracle_hit"] for r in rows) / ng,
            "n_gold": ng}


def _boot_ci(rows, key_num, key_den, days=None, B=2000, seed=7):
    """Day-cluster bootstrap: resample days with replacement, pool
    panels of the resampled days, recompute ratio."""
    by_day = collections.defaultdict(list)
    for r in rows:
        by_day[r["date"]].append(r)
    dl = sorted(by_day)
    rng = np.random.RandomState(seed)
    vals = []
    for _ in range(B):
        pick = rng.choice(dl, size=len(dl), replace=True)
        num = den = 0
        for d in pick:
            for r in by_day[d]:
                num += r[key_num]
                den += r[key_den]
        vals.append(num / den if den else np.nan)
    vals = np.asarray(vals)
    vals = vals[~np.isnan(vals)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def cv_report(tag):
    rows, ev = _panel_rows(tag)
    days = sorted({r["date"] for r in rows})
    fs = folds([{"date": d} for d in days])  # sets of held-out days
    print("=== %s ===" % tag)
    print("days: %s" % ", ".join(days))
    overall = _metrics(rows)
    print("pooled: born %.3f  r@1 %.3f  r@2 %.3f  ink %.2f  oracle %.3f"
          % (overall["born"], overall["r_at1"], overall["r_at2"],
             overall["ink"], overall["oracle"]))
    for f, held in enumerate(fs):
        sub = [r for r in rows if r["date"] in held]
        mm = _metrics(sub)
        if mm:
            print("fold%d (held-out %s): born %.3f  r@1 %.3f  r@2 %.3f"
                  "  ink %.2f  (n=%d gold)"
                  % (f, ",".join(sorted(held)[0:1]) + "..%dd" % len(held),
                     mm["born"], mm["r_at1"], mm["r_at2"], mm["ink"],
                     mm["n_gold"]))
    for name, num in (("born", "born_hit"), ("r@1", "rec_at1"),
                      ("r@2", "rec_at2")):
        lo, hi = _boot_ci(rows, num, "n_gold_box")
        print("day-boot CI %s: %.3f [%.3f, %.3f]"
              % (name, overall[name.replace("@", "_at")], lo, hi))
    return rows


def barrier_sign(tag):
    """Barrier sign per fold: P(cand_right | barrier==0) vs
    P(cand_right | barrier>=1), from the cached run pickles
    (cand_feats is stripped from the eval json at save)."""
    import pickle
    import run_eval as RE
    sys.modules.setdefault("__main__", RE)
    sys.modules["__main__"] = RE  # _Shim lives there for the pickles
    rows, ev = _panel_rows(tag)
    recs = {r["id"]: r for r in C.load_tune()}
    days = sorted({r["date"] for r in rows})
    fs = folds([{"date": d} for d in days])
    print("=== %s barrier sign per fold ===" % tag)
    for f, held in enumerate(fs):
        n0 = r0 = n1 = r1 = 0
        for pan in ev["panels"]:
            rec = recs[pan["id"]]
            if rec["date"] not in held:
                continue
            w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
            fp = os.path.join(RE.RUNS, "s2_%s_%s_%d.pkl"
                              % (tag, rec["date"], w1))
            if not os.path.exists(fp):
                continue
            with open(fp, "rb") as fh:
                e = pickle.load(fh)
            t, m, o, h, l, c = EV.day_bars(rec["date"])
            gobjs, _u, _to = EV.gold_objects(rec)
            gbox = [g for g in gobjs if g.get("spec_type") == "BOX"]
            for cd in e.cand_log or []:
                if cd.get("kind") != "BOX":
                    continue
                rr = FN.cand_as_record(cd, m, w0, w1)
                if rr is None:
                    continue
                right = any(FN.cand_right(g, rr, m) for g in gbox)
                if (cd.get("barrier") or 0) >= 1:
                    n1 += 1; r1 += int(right)
                else:
                    n0 += 1; r0 += int(right)
        print("fold%d: P(right|bar=0)=%.4f (n=%d)  "
              "P(right|bar>=1)=%.4f (n=%d)"
              % (f, r0 / max(n0, 1), n0, r1 / max(n1, 1), n1))


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        cv_report(tag)
        print()
    for tag in sys.argv[1:]:
        barrier_sign(tag)
