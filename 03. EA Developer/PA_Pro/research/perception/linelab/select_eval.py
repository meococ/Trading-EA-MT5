"""L8 — selection measure (MANDATE_LINE_LAB_2).

Labels PATTERN_LINE candidates with EVAL-AUDIT's R11 prefix-consistent
rule (funnel.cand_right via best_cand_match) and scores each causal
candidate feature by AUC on a day-level 5-fold split of TUNE.  The
combined score = equal weight on ranks, per the L3 protocol.

Run:  python -X utf8 select_eval.py [--limit N]
"""
import argparse
import collections
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "golden"))

import common as C          # noqa: E402
import eval as EV           # noqa: E402
import eval_v2 as V2        # noqa: E402
import funnel as F          # noqa: E402
import engine as ENG        # noqa: E402

# numeric candidate feats carried in cand_log rows (lines.py _eval)
FEATS = ["touches", "piv_touches", "prom_abr", "age_min", "score"]
# AUC direction: lower-is-better features get inverted
INV = {"age_min"}


def collect(recs):
    """Run the engine per panel; label each distinct line candidate."""
    rows = []
    for rec in recs:
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        e = EV.run_engine(ENG.PerceptionEngine, m, t, o, h, l, c, w1)
        gobjs, gmarks, gkeys, gmkeys = F.gold_with_keys(rec)
        g2 = [g for g in gobjs
              if V2.scorable(g, w0, w1)
              and g["spec_type"] in V2.LINE_TYPES]
        seen = set()
        for cd in e.cand_log or []:
            if cd["kind"] != "PATTERN_LINE":
                continue
            r = F.cand_as_record(cd, m, w0, w1)
            if r is None:
                continue
            key = (r.get("t0"), r.get("p0"), r.get("slope"))
            if key in seen:
                continue
            seen.add(key)
            row = {"panel": rec["id"], "date": rec["date"],
                   "y": F.best_cand_match(r, g2, m) is not None,
                   "outcome": cd.get("outcome")}
            for fk in FEATS:
                row[fk] = cd.get(fk)
            rows.append(row)
    return rows


def auc(rows, feat):
    """Rank AUC of `feat` against y; None if a class is missing."""
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
    """Equal-weight rank combination; returns per-row combined rank."""
    rk = {}
    for f in feats:
        vals = sorted({r[f] for r in rows if r.get(f) is not None})
        idx = {v: k for k, v in enumerate(vals)}
        rk[f] = idx
    for r in rows:
        s = 0.0
        n = 0
        for f in feats:
            if r.get(f) is None:
                continue
            v = rk[f][r[f]]
            v = -v if f in INV else v
            s += v
            n += 1
        r["_comb"] = s / n if n else None


def folds(rows, k=5):
    """Day-level split: fold by date."""
    days = sorted({r["date"] for r in rows})
    return [set(d for j, d in enumerate(days) if j % k == f)
            for f in range(k)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]
    rows = collect(recs)
    out = os.path.join(_HERE, "select_cands.jsonl")
    with open(out, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    n_pos = sum(r["y"] for r in rows)
    print("candidates: %d   right: %d (%.3f)"
          % (len(rows), n_pos, n_pos / max(len(rows), 1)))

    fs = folds(rows)
    print("\nfeature   overall   " +
          "  ".join("f%d" % i for i in range(5)))
    for feat in FEATS:
        ov = auc(rows, feat)
        pf = [auc([r for r in rows if r["date"] in fs[i]], feat)
              for i in range(5)]
        fmt = lambda v: "  ---- " if v is None else "  %.3f" % v
        print("%-11s %s%s" % (feat, fmt(ov), "".join(fmt(v)
                                                     for v in pf)))
    # combined score over features that pass >=0.60 on every fold
    ok = []
    for feat in FEATS:
        pf = [auc([r for r in rows if r["date"] in fs[i]], feat)
              for i in range(5)]
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
