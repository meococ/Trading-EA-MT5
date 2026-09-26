"""fit_ranker.py -- A3 small learned ranker (R56 s.56.4).

Deterministic NumPy logistic ranker over boxlab/r_dataset/rows.csv.
Run OFF the Owner's PC (cloud lane); this file is the fitting script
that lane executes.

Controls per ruling:
  - <= 4 features, chosen only from hypotheses that beat their null
    (pass --features after R1 settles the list).
  - Leave-one-day-out CV: train on all days except d, score day d.
  - Shuffle control: 200 draws shuffling labels within (panel,tau);
    report null p95 for the pick-accuracy metric.
  - Reported number = CV result, never the in-sample fit.

Metric: pick-accuracy at tau -- among rows of a (panel,tau) cell, does
the model's argmax equal a label_edge>=0 row?  Compared against the
engine baseline (argmax of score_last / is_engine_pick row).

Usage: python fit_ranker.py --features px_in_box probes_top h_abr
"""
import sys, os, csv, argparse, itertools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "r_dataset", "rows.csv")
RNG_SEED = 20260924
N_SHUFFLE = 200
LR, EPOCHS, L2 = 0.3, 400, 1e-3


def load():
    with open(ROWS) as f:
        return list(csv.DictReader(f))


def fit_logreg(X, y, w0=None):
    """Plain batch GD logistic regression, deterministic."""
    n, d = X.shape
    w = np.zeros(d) if w0 is None else w0.copy()
    Xb = np.hstack([X, np.ones((n, 1))])
    wb = np.zeros(d + 1) if w0 is None else np.r_[w0, 0.0]
    for _ in range(EPOCHS):
        z = np.clip(Xb @ wb, -30, 30)
        p = 1.0 / (1.0 + np.exp(-z))
        g = Xb.T @ (p - y) / n + L2 * wb
        wb -= LR * g
    return wb


def score(X, wb):
    return 1.0 / (1.0 + np.exp(-np.clip(
        np.hstack([X, np.ones((len(X), 1))]) @ wb, -30, 30)))


def pick_acc(rows, preds, label="label_edge"):
    """Per (panel,tau): 1 if argmax row has label>=0, else 0."""
    cells = {}
    for r, p in zip(rows, preds):
        cells.setdefault((r["panel"], r["tau"]), []).append(
            (p, int(r[label]) >= 0))
    hits = 0
    for v in cells.values():
        i = int(np.argmax([x[0] for x in v]))
        hits += int(v[i][1])
    return hits, len(cells)


def engine_baseline(rows):
    cells = {}
    for r in rows:
        cells.setdefault((r["panel"], r["tau"]), []).append(r)
    hits = 0
    for v in cells.values():
        pick = next((r for r in v if r["is_engine_pick"] == "1"), None)
        if pick is None:
            s = [float(r["score_last"] or -99) for r in v]
            pick = v[int(np.argmax(s))]
        hits += int(int(pick["label_edge"]) >= 0)
    return hits, len(cells)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", nargs="+", required=True)
    a = ap.parse_args()
    assert len(a.features) <= 4, "A3 cap: <=4 features"
    rows = load()
    for r in rows:
        for f in a.features:
            r["_x_" + f] = float(r[f]) if r[f] not in (None, "") else 0.0
    days = sorted({r["date"] for r in rows})
    rng = np.random.RandomState(RNG_SEED)

    # ---- LODO CV ----
    preds = np.zeros(len(rows))
    for d in days:
        tr = [i for i, r in enumerate(rows) if r["date"] != d]
        te = [i for i, r in enumerate(rows) if r["date"] == d]
        X = np.array([[r["_x_" + f] for f in a.features]
                      for r in rows])
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        X = (X - mu) / sd
        y = np.array([int(r["label_edge"]) >= 0 for r in rows],
                     dtype=float)
        wb = fit_logreg(X[tr], y[tr])
        preds[te] = score(X[te], wb)
    hit_m, n_m = pick_acc(rows, preds)
    hit_b, _ = engine_baseline(rows)

    # ---- shuffle control: labels shuffled within (panel,tau) ----
    null = []
    cells = {}
    for i, r in enumerate(rows):
        cells.setdefault((r["panel"], r["tau"]), []).append(i)
    for _ in range(N_SHUFFLE):
        srows = [dict(r) for r in rows]
        for idx in cells.values():
            lab = [srows[i]["label_edge"] for i in idx]
            rng.shuffle(lab)
            for i, l in zip(idx, lab):
                srows[i]["label_edge"] = l
        sp = np.zeros(len(rows))
        for d in days:
            tr = [i for i, r in enumerate(srows) if r["date"] != d]
            te = [i for i, r in enumerate(srows) if r["date"] == d]
            X = np.array([[r["_x_" + f] for f in a.features]
                          for r in srows])
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            X = (X - mu) / sd
            y = np.array([int(r["label_edge"]) >= 0 for r in srows],
                         dtype=float)
            wb = fit_logreg(X[tr], y[tr])
            sp[te] = score(X[te], wb)
        h_, _ = pick_acc(srows, sp)
        null.append(h_)
    p95 = float(np.percentile(null, 95))
    print("features:", a.features)
    print("cells (panel,tau):", n_m)
    print("engine baseline pick-acc: %d/%d = %.3f"
          % (hit_b, n_m, hit_b / n_m))
    print("model LODO pick-acc:      %d/%d = %.3f"
          % (hit_m, n_m, hit_m / n_m))
    print("shuffle null p95: %.1f  -> model beats null: %s"
          % (p95, hit_m > p95))


if __name__ == "__main__":
    main()
