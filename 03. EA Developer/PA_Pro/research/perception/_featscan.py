"""_featscan.py — offline feature scan for BOX candidates.

Recomputes candidate features from day bars + cand geometry (the
cand_log rows carry top/bottom/t0/t1 bars + idx + abr + close), so
feature variants can be screened without touching the engine.

Label = right-geometry vs golden BOX (both edges within prec sigma).
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
import common as C                    # noqa: E402
import eval as EV                     # noqa: E402
import eval_v2                        # noqa: E402
import pa_slots                       # noqa: E402
import engine as ENG1                 # noqa: E402
from _auc import auc                  # noqa: E402

PIP = EV.PIP


def feats_for(row, O, H, L, Cl, EMA, ABR):
    i = row["idx"]
    top, bot = row.get("top"), row.get("bottom")
    if top is None or bot is None:
        return None
    t0 = row.get("t0", i)
    t1 = row.get("t1", i)
    t0 = int(min(max(t0, 0), i))
    t1 = int(min(max(t1, t0), i))
    abr = max(ABR[i], 1e-9)
    seg = slice(t0, t1 + 1)
    n = t1 - t0 + 1
    closes = Cl[seg]
    hi_run = H[seg]
    lo_run = L[seg]
    h = top - bot
    inside = np.mean((closes >= bot) & (closes <= top))
    wick_hi = np.sum(np.abs(hi_run - top) <= 0.25 * abr)
    wick_lo = np.sum(np.abs(lo_run - bot) <= 0.25 * abr)
    # extremes BEFORE the window: distance of each edge to nearest
    # prior swing-ish extreme approximated by prior day hi/lo so far
    pre_hi = H[:t0].max() if t0 else np.nan
    pre_lo = L[:t0].min() if t0 else np.nan
    d_pre = np.inf
    for e_ in (top, bot):
        if t0:
            d_pre = min(d_pre, abs(e_ - pre_hi), abs(e_ - pre_lo))
    # session (CET) of birth
    cet = row.get("cet_min") or 0
    in_eu = 480 <= cet <= 720        # 08:00-12:00
    return {
        "h_abr": h / abr,
        "span": n,
        "contain": inside,
        "touch_dens": (wick_hi + wick_lo) / n,
        "wick_top": wick_hi / n,
        "wick_bot": wick_lo / n,
        "dist_close": abs(Cl[i] - 0.5 * (top + bot)) / abr,
        "close_in": float(bot <= Cl[i] <= top),
        "d_prior_ext": d_pre / abr if np.isfinite(d_pre) else 9.9,
        "med_rng": float(np.median(hi_run - lo_run)) / abr,
        "ema_dist": abs(Cl[i] - EMA[i]) / abr,
        "in_eu": float(in_eu),
        "score": row.get("score", 0.0),
    }


def main():
    recs = C.load_tune()
    rows = []
    with pa_slots.slot("featscan", timeout=300):
        for k, rec in enumerate(recs):
            w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
            t, m, o, h, l, c = EV.day_bars(rec["date"])
            e = EV.run_engine(ENG1.PerceptionEngine, m, t, o, h, l, c,
                              w1)
            gobjs, _u, _t = EV.gold_objects(rec)
            gold = [g for g in gobjs if g["spec_type"] == "BOX"
                    and eval_v2.scorable(g, w0, w1)]
            EMA, ABR = np.asarray(e.ema), np.asarray(e.abr)
            H = np.asarray([b["h"] for b in e.bars])
            L = np.asarray([b["l"] for b in e.bars])
            Cl = np.asarray([b["c"] for b in e.bars])
            O = np.asarray([b["o"] for b in e.bars])
            seen = {}
            for row in e.cand_log:
                if row["kind"] != "BOX":
                    continue
                key = (row["route"], row.get("t0"),
                       row.get("top"), row.get("bottom"))
                seen[key] = row
            for row in seen.values():
                lab = 0
                for g in gold:
                    tol = C.prec_sigmas(g)[0]
                    if g.get("price_lo") is not None and \
                            abs(row.get("top", -9e9)
                                - g["price_hi"] / PIP) <= tol and \
                            abs(row.get("bottom", 9e9)
                                - g["price_lo"] / PIP) <= tol:
                        lab = 1
                        break
                f = feats_for(row, O, H, L, Cl, EMA, ABR)
                if f is None:
                    continue
                f["label"] = lab
                f["date"] = rec["date"]
                f["outcome"] = row["outcome"]
                rows.append(f)
            if (k + 1) % 50 == 0:
                print("  %d/%d" % (k + 1, len(recs)), flush=True)
    json.dump(rows, open("_feat_rows.json", "w"))
    dates = sorted({r["date"] for r in rows})
    folds = [set(dates[i::5]) for i in range(5)]
    feats = [k for k in rows[0] if k not in ("label", "date", "outcome")]
    print("\nBOX candidate feature AUCs (n=%d, pos=%d):"
          % (len(rows), sum(r["label"] for r in rows)))
    for f in feats:
        per = []
        for fold in folds:
            sub = [r for r in rows if r["date"] in fold]
            per.append(auc([r[f] for r in sub],
                           [r["label"] for r in sub]))
        all_ = auc([r[f] for r in rows], [r["label"] for r in rows])
        print("  %-12s all=%.3f  folds=%s"
              % (f, all_, " ".join("%.2f" % x for x in per)))
        # also inverted
        ai = auc([-r[f] for r in rows], [r["label"] for r in rows])
        if ai > all_:
            print("     (inverted all=%.3f)" % ai)


if __name__ == "__main__":
    main()
