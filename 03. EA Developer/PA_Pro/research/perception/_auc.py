"""_auc.py — §9a.2: AUC of the birth score (and candidate features)
for golden-right vs golden-wrong on the capped-candidate pool.

Pool = cand_log rows whose outcome is a cap decision
(born / rate_limited / outranked / nms_suppressed / expired /
below_min_score).  One row per candidate signature, the LAST one
(the decision moment's score).  Label = candidate geometry matches a
golden object of the same family within the object's own precision
sigma (same right_geom test as _regression.py).

5-fold split by panel DATE (panels on one day stay together).
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

PIP = EV.PIP
CAP_OUTCOMES = ("born", "rate_limited", "outranked", "nms_suppressed",
                "expired", "below_min_score")


def _fam_letter(s):
    return (s or "").replace("m", "").replace("w", "").replace("i", "")


def right_geom(g, row, m, tol):
    gt = g["spec_type"]
    if gt in ("BOX", "RANGE_OPEN", "CONTEXT_RANGE"):
        if g.get("price_lo") is None:
            return False
        lo, hi = row.get("bottom"), row.get("top")
        return lo is not None and hi is not None and \
            abs(lo - g["price_lo"] / PIP) <= tol and \
            abs(hi - g["price_hi"] / PIP) <= tol
    if gt in ("LEVEL_CARRIED", "MINI_LEVEL"):
        if g.get("price") is None:
            return False
        p = row.get("price", row.get("level"))
        return p is not None and abs(p - g["price"] / PIP) <= tol
    if gt == "BRACKET":
        if _fam_letter(g.get("letter")) != _fam_letter(row.get("letter")):
            return False
        t0, t1 = row.get("t0"), row.get("t1")
        if t0 is None:
            return False
        t0 = m[int(min(max(t0, 0), len(m) - 1))]
        t1 = m[int(min(max(t1 if t1 is not None else t0, 0),
                       len(m) - 1))]
        ov = eval_v2._overlap(t0, t1, g["t0"], g["t1"])
        return ov >= 0.3 * max(g["t1"] - g["t0"], 1)
    if gt in ("PATTERN_LINE", "CONTEXT_LINE"):
        p0, p1 = g.get("price0"), g.get("price1")
        if p0 is None or p1 is None or row.get("p0") is None:
            return False
        # engine line evaluated at golden span ends vs golden endpoints
        t0b = row.get("t0")
        sl = row.get("slope")
        if t0b is None or sl is None:
            return False
        for tmin, pexp in ((g["t0"], p0), (g["t1"], p1)):
            if tmin is None:
                return False
            j = min(int(np.searchsorted(m, tmin)), len(m) - 1)
            if abs(row["p0"] + sl * (j - t0b) - pexp / PIP) > tol:
                return False
        return True
    return False


def auc(scores, labels):
    """Mann-Whitney AUC."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, int)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if not n1 or not n0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    r = np.empty(len(s))
    r[order] = np.arange(1, len(s) + 1)
    # average ranks on ties
    uq, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    r = cnt[inv] * 0 + r
    for k in range(len(uq)):
        idx = np.where(inv == k)[0]
        if len(idx) > 1:
            r[idx] = r[idx].mean()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    recs = C.load_tune()
    rows_out = open("_auc_rows.jsonl", "w", encoding="utf8")
    with pa_slots.slot("auc", timeout=300):
        for k, rec in enumerate(recs):
            w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
            t, m, o, h, l, c = EV.day_bars(rec["date"])
            e = EV.run_engine(ENG1.PerceptionEngine, m, t, o, h, l, c, w1)
            gobjs, _un, _to = EV.gold_objects(rec)
            gold = [g for g in gobjs
                    if eval_v2.scorable(g, w0, w1)]
            for g in gold:
                if g.get("t0") is None:
                    g["t0"] = w0
                if g.get("t1") is None:
                    g["t1"] = w1
            seen = {}
            for row in e.cand_log:
                if row["outcome"] not in CAP_OUTCOMES:
                    continue
                key = (row["kind"], row["route"], row.get("t0"),
                       repr(sorted((kk, vv) for kk, vv in row.items()
                                   if kk in ("top", "bottom", "price",
                                             "p0", "slope", "letter",
                                             "level"))))
                seen[key] = row      # last outcome wins
            for key, row in seen.items():
                fam = EV.FAMILY.get(row["kind"])
                lab = 0
                for g in gold:
                    if EV.FAMILY.get(g["spec_type"]) != fam:
                        continue
                    tol = C.prec_sigmas(g)[0]
                    if right_geom(g, row, m, tol):
                        lab = 1
                        break
                rec_out = {"panel": rec["id"], "date": rec["date"],
                           "kind": row["kind"], "score": row["score"],
                           "outcome": row["outcome"], "label": lab}
                for f_ in ("barrier", "pressure", "compression",
                           "ema_guide"):
                    if f_ in row:
                        rec_out[f_] = row[f_]
                rows_out.write(json.dumps(rec_out) + "\n")
            if (k + 1) % 50 == 0:
                print("  %d/%d" % (k + 1, len(recs)), flush=True)
    rows_out.close()

    rows = [json.loads(x) for x in open("_auc_rows.jsonl")]
    dates = sorted({r["date"] for r in rows})
    folds = [set(dates[i::5]) for i in range(5)]

    def rep(name, val_fn):
        print("\n-- %s" % name)
        for fi, fold in enumerate(folds):
            sub = [r for r in rows if r["date"] in fold]
            sc = [val_fn(r) for r in sub]
            lb = [r["label"] for r in sub]
            ok = [j for j, v in enumerate(sc) if v is not None]
            a = auc([sc[j] for j in ok], [lb[j] for j in ok])
            print("  fold%d n=%d pos=%d AUC=%.3f"
                  % (fi, len(ok), sum(lb[j] for j in ok), a))
        sc = [val_fn(r) for r in rows]
        ok = [j for j, v in enumerate(sc) if v is not None]
        print("  ALL   n=%d pos=%d AUC=%.3f"
              % (len(ok), sum(r["label"] for r in rows),
                 auc([sc[j] for j in ok],
                     [rows[j]["label"] for j in ok])))

    rep("birth score", lambda r: r["score"])
    for f_ in ("barrier", "pressure", "compression", "ema_guide"):
        if any(f_ in r for r in rows):
            rep(f_, lambda r: r.get(f_))
    print("\nper-kind score AUC:")
    for kind in sorted({r["kind"] for r in rows}):
        sub = [r for r in rows if r["kind"] == kind]
        print("  %-14s n=%4d pos=%3d AUC=%.3f"
              % (kind, len(sub), sum(r["label"] for r in sub),
                 auc([r["score"] for r in sub],
                     [r["label"] for r in sub])))


if __name__ == "__main__":
    main()
