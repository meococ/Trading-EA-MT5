"""select_eval — X3 selection measure for BOX candidates (lab runs).

Labels each distinct BOX candidate in a cached lab run with the official
prefix-consistent rule (funnel.cand_right) and scores every causal
candidate feature by AUC on a day-level 5-fold split of TUNE, per the
mandate: keep a feature only if AUC >= 0.60 on EVERY fold; combine
survivors with equal weight on ranks (no fitted weights).

Usage:  python select_eval.py [--tag lab_r3]
Writes: cache/select_<tag>.jsonl  +  AUC table to stdout.
"""
import argparse
import collections
import json
import os
import pickle
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
for _p in (_HERE, _PERC, os.path.join(_PERC, "evalcheck"),
           os.path.join(_PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, os.path.abspath(_p))

import common as C           # noqa: E402
import eval as EV            # noqa: E402
import eval_v2 as V2         # noqa: E402
import funnel as FN          # noqa: E402
import run_eval as RE        # noqa: E402

sys.modules.setdefault("__main__")._Shim = RE._Shim

FEATS = ["age_min", "prom_sum", "prom_min", "contacts", "struct_any",
         "struct_both", "contain_frac", "n_piv", "hgt", "lean_top"]
# direction: features where SMALLER should mean righter get inverted
INV = {"hgt"}


def collect(recs, tag):
    rows = []
    runs = os.path.join(_HERE, "cache", "runs")
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        f = os.path.join(runs, "s2_%s_%s_%d.pkl" % (tag, rec["date"], w1))
        if not os.path.exists(f):
            continue
        e = pickle.load(open(f, "rb"))
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        gobjs, _un, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)
              and g["spec_type"] == "BOX"]
        for g in g2:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        seen = set()
        for cd in e.cand_log or []:
            if cd.get("kind") != "BOX":
                continue
            r = FN.cand_as_record(cd, m, w0, w1)
            if r is None:
                continue
            key = (r.get("t0"), round(r.get("lo", 0) * 2),
                   round(r.get("hi", 0) * 2), r["t_birth"])
            if key in seen:
                continue
            seen.add(key)
            row = {"panel": rec["id"], "date": rec["date"],
                   "y": any(FN.cand_right(g, r, m) for g in g2),
                   "outcome": cd.get("outcome"),
                   "lo": r.get("lo"), "hi": r.get("hi"),
                   "t0m": r.get("t0"), "tb": r.get("t_birth"),
                   "route": cd.get("route")}
            for fk in FEATS:
                row[fk] = cd.get(fk)
            row["prom_abr"] = (cd.get("prom_sum") / cd["abr"]
                               if cd.get("abr") else None)
            row["hgt_abr"] = (cd.get("hgt") / cd["abr"]
                              if cd.get("abr") else None)
            rows.append(row)
    return rows


def auc(rows, feat):
    pts = [(r[feat], r["y"]) for r in rows if r.get(feat) is not None]
    pos = [p for p, y in pts if y]
    neg = [p for p, y in pts if not y]
    if not pos or not neg:
        return None
    neg_s = sorted(neg)
    import bisect
    wins = sum(bisect.bisect_left(neg_s, p) + 0.5 *
               sum(1 for q in neg_s if q == p) for p in pos)
    return wins / (len(pos) * len(neg))


def combined(rows, feats):
    rk = {}
    for f in feats:
        vals = sorted({r[f] for r in rows if r.get(f) is not None})
        rk[f] = {v: k for k, v in enumerate(vals)}
    for r in rows:
        s, n = 0.0, 0
        for f in feats:
            if r.get(f) is None:
                continue
            v = rk[f][r[f]]
            v = -v if f in INV else v
            s += v
            n += 1
        r["_comb"] = s / n if n else None


def folds(rows, k=5):
    days = sorted({r["date"] for r in rows})
    return [set(d for j, d in enumerate(days) if j % k == f)
            for f in range(k)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="lab_r3")
    args = ap.parse_args()
    recs = C.load_tune()
    rows = collect(recs, args.tag)
    out = os.path.join(_HERE, "cache", "select_%s.jsonl" % args.tag)
    with open(out, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    n_pos = sum(r["y"] for r in rows)
    print("candidates: %d   right: %d (%.4f)"
          % (len(rows), n_pos, n_pos / max(len(rows), 1)))

    feats = FEATS + ["prom_abr", "hgt_abr"]
    fs = folds(rows)
    print("\nfeature      overall  " +
          "  ".join("f%d" % i for i in range(5)))
    ok = []
    for feat in feats:
        ov = auc(rows, feat)
        pf = [auc([r for r in rows if r["date"] in fs[i]], feat)
              for i in range(5)]
        fmt = lambda v: " ----- " if v is None else " %.3f " % v
        print("%-12s %s%s" % (feat, fmt(ov), "".join(fmt(v)
                                                    for v in pf)))
        if all(v is not None and v >= 0.60 for v in pf):
            ok.append(feat)
    print("\nfeatures >=0.60 all folds:", ok or "NONE")
    if ok:
        combined(rows, ok)
        ov = auc(rows, "_comb")
        pf = [auc([r for r in rows if r["date"] in fs[i]], "_comb")
              for i in range(5)]
        print("combined %s overall %.3f folds %s"
              % (ok, ov, ["%.3f" % v for v in pf]))


if __name__ == "__main__":
    main()
