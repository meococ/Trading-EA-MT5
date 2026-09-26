"""_h5causal_review.py — independent re-run of BOX-LAB's H5-causal
paired test on r_dataset/rows.csv (REQUESTS.md ~15:10Z, R57 §57.1).

Spec as logged: per (panel,tau) cell, strongest right cand
(label_edge>=0, max score_last) vs the engine's live wrong pick
(is_engine_pick=1 row, label_edge<0).  Null = label_edge shuffled
within (panel,tau), 200 draws, seed 7.  Reported features are the
causal ones (bars <= tau only, per DATA_DICT).

EVAL-AUDIT addition: seed-777 robustness, plus a second null that
shuffles the right-cand CHOICE among all cands (draw a random cand as
"right") - sanity for thin n.
"""
import csv
import collections
import os
import sys
import random

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
ROWS = os.path.join(PERC, "boxlab", "r_dataset", "rows.csv")

FEATS = ["recency_bars", "bars_since_in_band", "bars_since_touch",
         "dist_close_edge_abr", "px_in_box", "ema_slope_span",
         "probes_bot", "probes_top", "h_abr", "h_rel_day",
         "overlap_ratio", "prior_leg_abr", "age_bars"]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def load():
    cells = collections.defaultdict(list)
    with open(ROWS, newline="") as fh:
        for r in csv.DictReader(fh):
            cells[(r["panel"], r["tau"])].append(r)
    return cells


def pick_pair(cell):
    """(right_row, wrong_row) or None."""
    rights = [r for r in cell if int(r["label_edge"]) >= 0]
    wrongs = [r for r in cell
              if r["is_engine_pick"] == "1" and int(r["label_edge"]) < 0]
    if not rights or not wrongs:
        return None
    right = max(rights, key=lambda r: num(r["score_last"]))
    return right, wrongs[0]


def diffs(cells, rng=None, shuffle=False, random_pick=False):
    out = collections.defaultdict(list)
    for key, cell in cells.items():
        if shuffle or random_pick:
            cell = [dict(r) for r in cell]
            if shuffle:
                le = [r["label_edge"] for r in cell]
                rng.shuffle(le)
                for r, v in zip(cell, le):
                    r["label_edge"] = v
            if random_pick:
                for r in cell:
                    r["label_edge"] = "-1"
                if cell:
                    cell[rng.randrange(len(cell))]["label_edge"] = "0"
        pr = pick_pair(cell)
        if pr is None:
            continue
        right, wrong = pr
        for f in FEATS:
            a, b = num(right[f]), num(wrong[f])
            if a == a and b == b:          # not NaN
                out[f].append(a - b)
    return out


def main():
    cells = load()
    n_cells = sum(1 for c in cells.values() if pick_pair(c))
    print("cells total %d | paired %d" % (len(cells), n_cells))

    obs = diffs(cells)
    rng = random.Random(7)
    null = collections.defaultdict(list)
    for _ in range(200):
        d = diffs(cells, rng=rng, shuffle=True)
        for f in FEATS:
            if d[f]:
                null[f].append(sum(d[f]) / len(d[f]))
    rng2 = random.Random(7)
    null_rp = collections.defaultdict(list)
    for _ in range(200):
        d = diffs(cells, rng=rng2, random_pick=True)
        for f in FEATS:
            if d[f]:
                null_rp[f].append(sum(d[f]) / len(d[f]))

    print("%-22s %8s %8s | %8s %8s | %8s %8s | n" % (
        "feat", "obs", "", "shuf_p95", "shuf_p5", "rnd_p95", "rnd_p5"))
    for f in FEATS:
        o = sum(obs[f]) / len(obs[f]) if obs[f] else float("nan")
        s = sorted(null[f]); s2 = sorted(null_rp[f])
        p95 = s[int(0.95 * (len(s) - 1))] if s else float("nan")
        p5 = s[int(0.05 * (len(s) - 1))] if s else float("nan")
        q95 = s2[int(0.95 * (len(s2) - 1))] if s2 else float("nan")
        q5 = s2[int(0.05 * (len(s2) - 1))] if s2 else float("nan")
        tag = ""
        if o == o:
            if o > p95 or o < p5:
                tag = "BEAT-shuffle"
        print("%-22s %8.3f %8s | %8.3f %8.3f | %8.3f %8.3f | %d %s" % (
            f, o, "", p95, p5, q95, q5, len(obs[f]), tag))


if __name__ == "__main__":
    main()
