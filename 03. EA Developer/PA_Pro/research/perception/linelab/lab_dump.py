"""lab_dump — dump every gate-passing line candidate with features and
label it against the panel's golden PATTERN_LINEs.

Label rule (eval_v2-shaped, slightly looser price gate for label noise):
  overlap of [cand t0, birth bar] with golden [t0,t1] >=
      min(0.5*gspan, max(10, 0.25*gspan))
  AND |cand(a) - gold(a)|, |cand(b) - gold(b)| <= 4 p at overlap edges
  AND slope sign agrees with golden dir when dir is known.

Output: linelab/cand_dump.jsonl  (one row per evaluated candidate)
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, _PERC)
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import lines_lab  # noqa: E402

OUT = os.path.join(_HERE, "cand_dump.jsonl")
PRICE_TOL = 4.0


def gold_lines(rec):
    out = []
    for k, o in enumerate(rec.get("objects", [])):
        if o.get("spec_type") != "PATTERN_LINE":
            continue
        if o.get("status") == "unusable" or o.get("prec") == "time_only":
            continue
        t0, t1 = o.get("t0"), o.get("t1")
        p0, p1 = o.get("price0"), o.get("price1")
        if None in (t0, t1, p0, p1) or t1 <= t0:
            continue
        out.append({"t0": int(t0), "t1": int(t1),
                    "p0": p0 * 1e4, "p1": p1 * 1e4,
                    "dir": o.get("dir"), "key": "%s#%d" % (rec["id"], k)})
    return out


def label_cand(c, gmins, daym):
    """c in bar-index space; gmins golden in minutes.  daym maps bar->min."""
    ct0 = int(daym[c["t0"]])
    ct1 = int(daym[c["i"]])
    if ct1 <= ct0:
        return None
    cp0, cp1 = c["p0"], c["p0"] + c["slope"] * (c["i"] - c["t0"])
    for g in gmins:
        ov = min(ct1, g["t1"]) - max(ct0, g["t0"])
        need = min(0.5 * (g["t1"] - g["t0"]),
                   max(10.0, 0.25 * (g["t1"] - g["t0"])))
        if ov < need:
            continue
        gd = {"up": 1, "down": -1}.get(g["dir"])
        if gd is not None and (c["slope"] > 0) != (gd > 0):
            continue
        a, b = max(ct0, g["t0"]), min(ct1, g["t1"])
        gv = lambda t: g["p0"] + (g["p1"] - g["p0"]) * (t - g["t0"]) / \
            (g["t1"] - g["t0"])
        cv = lambda t: cp0 + (cp1 - cp0) * (t - ct0) / (ct1 - ct0)
        if abs(cv(a) - gv(a)) <= PRICE_TOL and \
                abs(cv(b) - gv(b)) <= PRICE_TOL:
            return g["key"]
    return None


def main():
    recs = bars_cache.tune_records()
    days = bars_cache.days()
    n_c = n_pos = 0
    with open(OUT, "w", encoding="utf8") as f:
        for rec in recs:
            day = days[rec["date"]]
            w1 = rec["window"]["x1"]
            gl = gold_lines(rec)
            if not gl:
                continue
            e = lines_lab.LineLabEngine(
                params={"min_score": -1e9, "fresh_only": False})
            rows = []

            def hook(i, feats):
                feats["panel"] = rec["id"]
                feats["date"] = rec["date"]
                lbl = label_cand(feats, gl, day["m"])
                feats["label"] = lbl
                rows.append(feats)

            e.cand_hook = hook
            for j in np.where(day["m"] <= w1)[0]:
                e.update(int(day["t"][j]), float(day["o"][j]) * 1e-4,
                         float(day["h"][j]) * 1e-4,
                         float(day["l"][j]) * 1e-4,
                         float(day["c"][j]) * 1e-4,
                         cet_min=int(day["m"][j]))
            for r in rows:
                f.write(json.dumps(r) + "\n")
            n_c += len(rows)
            n_pos += sum(1 for r in rows if r["label"])
            print(rec["id"], len(rows), "cands",
                  sum(1 for r in rows if r["label"]), "pos",
                  flush=True)
    print("total cands %d, positives %d -> %s" % (n_c, n_pos, OUT))


if __name__ == "__main__":
    main()
