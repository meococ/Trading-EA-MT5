"""ci_bootstrap.py — paired day-bootstrap CI for the V8 proposer
comparison (R20 §20.3 item 4).

From select_budget --save output: per-day LC recall@2 for each
proposer under ITS fold-chosen ranker (choose on 4 folds, score on
the held-out fold — same protocol as the CV table).  Then bootstrap
the paired day-level differences lab-prod and lab-naive over the
~32 LC-carrying dates; a CI including 0 is reported as weak evidence.

Usage: python ci_bootstrap.py [sb_r2.json]
"""

import collections
import json
import sys

import numpy as np

RANKERS = ("birth_score", "dist", "ndef", "age", "cls", "ret24",
           "barrier", "combo")


def day_scores(res, stream, gkey="LEVEL_CARRIED", kk=2):
    """date -> recall@k under the proposer's fold-chosen ranker."""
    meta = res["_meta"]
    fr = res[stream]["fold_rows"][gkey]
    # per-fold chosen ranker on the OTHER folds
    chosen = []
    for f in range(5):
        train = [i for i in range(5) if i != f]

        def fs(rn):
            h = sum(x[0] for i in train for x in fr[rn][str(kk)][i])
            n = sum(x[1] for i in train for x in fr[rn][str(kk)][i])
            return h / n if n else 0.0
        chosen.append(max(RANKERS, key=fs))
    # map fold entries back to dates: fold fi list follows collection
    # order over panels with fold==fi and >=1 golden of gkey
    ng = meta["n_lc"] if gkey == "LEVEL_CARRIED" else meta["n_mini"]
    per_day = collections.defaultdict(lambda: [0, 0])
    for f in range(5):
        idxs = [j for j in range(len(meta["dates"]))
                if meta["folds"][j] == f and ng[j] > 0]
        entries = fr[chosen[f]][str(kk)][f]
        assert len(entries) == len(idxs), \
            "fold %d: %d entries vs %d panels" % (f, len(entries),
                                                 len(idxs))
        for j, ent in zip(idxs, entries):
            d = meta["dates"][j]
            per_day[d][0] += ent[0]
            per_day[d][1] += ent[1]
    return {d: h / n for d, (h, n) in per_day.items() if n}, chosen


def boot(diffs, seed=7, n=10000):
    d = np.asarray(diffs, dtype=float)
    rng = np.random.default_rng(seed)
    bs = np.array([rng.choice(d, len(d)).mean() for _ in range(n)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return float(d.mean()), float(lo), float(hi), len(d)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "sb_r2.json"
    res = json.load(open(path, encoding="utf8"))
    days_lab, ch_lab = day_scores(res, "lab")
    days_prod, ch_prod = day_scores(res, "prod")
    days_naive, ch_naive = day_scores(res, "naive")
    print("fold-chosen rankers  lab: %s" % ",".join(ch_lab))
    print("                     prod: %s" % ",".join(ch_prod))
    print("                    naive: %s" % ",".join(ch_naive))
    for name, other in (("prod", days_prod), ("naive", days_naive)):
        common = sorted(set(days_lab) & set(other))
        diffs = [days_lab[d] - other[d] for d in common]
        m, lo, hi, n = boot(diffs)
        weak = "  weak evidence" if lo <= 0 <= hi else ""
        print("lab - %-5s LC@2: %+.3f [%.3f, %.3f] over %d days%s"
              % (name, m, lo, hi, n, weak))


if __name__ == "__main__":
    main()
