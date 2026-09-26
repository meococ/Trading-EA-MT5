"""EVAL-AUDIT s.77.4(b) bridge - Part E executed evalcheck-side.

DR-RULES escalated Part E at 08:29Z and its lane closed at 08:56Z,
two minutes before the geometry-only unblock
(owner_pack/dr_rules_item_geom.jsonl) was posted.  To keep the join
moving, this script computes C1-C8 on the 102 blind pack items USING
DR-RULES' OWN measure code (deepresearch/DR_RULES_measure.py:
gold_stats + s_c1..s_c8 + edge_defs), so the rule definitions stay
theirs verbatim; only the inputs are the blind export.

Uniform treatment: every item is measured through gold_stats()
(golden-dict adapter), so birth anchor = drawn left edge t0 for ALL
classes - no class can see different semantics.  Per-item units from
the panel's tau-run cache pickle (engine ema/abr/pivots/fed bars).

Output: evalcheck/DR_RULES_pack_features.csv  (seq + rule stats)
Run:    python evalcheck/_dr_rules_packfeat.py
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "deepresearch"))

import common as C                              # noqa: E402
import DR_RULES_measure as DM                   # noqa: E402

GEOM = os.path.join(PERC, "owner_pack", "dr_rules_item_geom.jsonl")
OUT = os.path.join(HERE, "DR_RULES_pack_features.csv")


def golden_adapter(row):
    """Blind item -> golden-dict schema that gold_stats() consumes."""
    g = {"spec_type": row["kind"],
         "t0": row.get("t0"), "t1": row.get("t1"),
         "price_lo": row.get("lo"), "price_hi": row.get("hi"),
         "price": row.get("price"), "price0": row.get("p0"),
         "price1": row.get("p1"), "prec": None, "dir": None,
         "build_start": None, "build_end": None}
    if g["price1"] is None and g["price0"] is not None \
            and row.get("slope") is not None and row.get("t0") is not None \
            and row.get("t1") is not None and row["t1"] > row["t0"]:
        # engine-normed lines carry p0+slope(raw/bar); p1 = p0 +
        # slope * n_bars over [t0,t1] (5-min bars)
        g["price1"] = g["price0"] \
            + row["slope"] * (row["t1"] - row["t0"]) / 5.0
    return g


def main():
    recs = {r["id"]: r for r in C.load_tune()}
    rows = [json.loads(l) for l in open(GEOM, encoding="utf8")]
    out_rows, miss = [], []
    for row in rows:
        rec = recs[row["panel"]]
        tau = row["tau"]
        w1 = rec["window"]["x1"] or 1439
        e = DM.pickled(rec["date"], tau)
        full = False
        if e is None:
            # item tau is not a cached tau-run; the full-window run
            # carries identical causal ema/abr/pivots at j <= j_tau
            e = DM.pickled(rec["date"], w1)
            full = True
        if e is None:
            miss.append(row["seq"])
            out_rows.append({"seq": row["seq"], "degenerate": "nocache"})
            continue
        m = np.array([b["cet_min"] for b in e.bars])
        o = np.array([b["o"] for b in e.bars])
        h = np.array([b["h"] for b in e.bars])
        l = np.array([b["l"] for b in e.bars])
        c = np.array([b["c"] for b in e.bars])
        if full:
            # truncate every per-bar array at the last bar <= tau
            j1 = DM.jle(m, tau)
            if j1 is None:
                miss.append(row["seq"])
                out_rows.append({"seq": row["seq"],
                                 "degenerate": "pretau"})
                continue
            sl = slice(0, j1 + 1)
            m, o, h, l, c = m[sl], o[sl], h[sl], l[sl], c[sl]
        st = DM.gold_stats(golden_adapter(row), m, o, h, l, c,
                           np.asarray(e.ema), np.asarray(e.abr),
                           e.book.seq, tau, tau)
        st = {"seq": row["seq"], "panel": row["panel"], "tau": tau,
              **{k: v for k, v in st.items()
                 if isinstance(v, (int, float, str, bool))
                 or v is None}}
        out_rows.append(st)
    cols = ["seq", "panel", "tau"]
    seen = set(cols)
    for r in out_rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    with open(OUT, "w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print("wrote %d rows -> %s" % (len(out_rows), OUT))
    print("cache misses (degenerate=nocache):", miss)


if __name__ == "__main__":
    main()
