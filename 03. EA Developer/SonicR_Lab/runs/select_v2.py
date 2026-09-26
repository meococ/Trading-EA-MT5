"""select_v2.py - D5 selection on BOTH harnesses (PREREG_V2 amendment A1).

Advance iff on BOTH H0 and H1, on DESIGN:
  pf_r_x1 >= 1.20 AND pf_x1 >= 1.20 AND pf_r_x15 >= 1.05 AND
  pf_x15 >= 1.05 AND trades_wk >= 1 AND pos_years/n_years >= 0.6 AND
  real PF_R beats the random-entry null at the 95th percentile
  (controls_h pct >= 95).
Rank by exp_r * sqrt(n); at most 3 advance -> runs/selection.json.
Also: best-of-N null over 100 cells (and the >=1/wk subset), deflated
Sharpe for the top configs, MC DD P95 for advancing configs.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd


def load_design():
    dfs = []
    for f, h in (("out/design_summary.csv", "H0"),
                 ("out/design_summary_e1.csv", "H1"),
                 ("out/design_summary_2b.csv", "H0"),
                 ("out/design_summary_2b_e1.csv", "H1")):
        if os.path.exists(f):
            d = pd.read_csv(f)
            d["harness"] = h
            dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)
    return df


def main():
    d = load_design()
    ctrl = pd.read_csv("out/controls_summary_h.csv")
    pct = {(r["sym"], r["cfg"], r["harness"]): r["pct"]
           for _, r in ctrl.iterrows()}
    null = np.load("out/controls_null_h.npz")

    rows = []
    for (sym, cid), g in d.groupby(["sym", "cfg"]):
        g = g.set_index("harness")
        if not {"H0", "H1"} <= set(g.index):
            continue
        r = {"sym": sym, "cfg": cid}
        ok = True
        for h in ("H0", "H1"):
            s = g.loc[h]
            ny = s["n_years"] if np.isfinite(s["n_years"]) else 0
            py = s["pos_years"] if np.isfinite(s["pos_years"]) else 0
            gate = (s["pf_r_x1"] >= 1.20 and s["pf_x1"] >= 1.20
                    and s["pf_r_x15"] >= 1.05 and s["pf_x15"] >= 1.05
                    and s["trades_wk"] >= 1.0
                    and ny > 0 and py / ny >= 0.6
                    and pct.get((sym, cid, h), -1) >= 95)
            for c in ("pf_r_x1", "pf_x1", "pf_r_x15", "pf_x15",
                      "trades_wk", "n", "exp_r", "maxdd_r"):
                r[f"{c}_{h}"] = s[c]
            r[f"posyr_{h}"] = f"{int(py)}/{int(ny)}"
            r[f"pct_{h}"] = pct.get((sym, cid, h))
            ok = ok and bool(gate)
        r["pass_d5"] = ok
        r["score"] = float(np.nanmin([r["exp_r_H0"], r["exp_r_H1"]])
                           * np.sqrt(min(r["n_H0"], r["n_H1"])))
        rows.append(r)
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    df.to_csv("out/selection_table.csv", index=False)
    adv = df[df["pass_d5"]].head(3)
    sel = {"selected": [{"sym": r["sym"], "cfg": r["cfg"]}
                        for _, r in adv.iterrows()],
           "rule": "D5 on H0 AND H1, both PF_R and pip PF, "
                   "pct>=95 on both", "n_candidates": int(len(df)),
           "n_pass": int(df["pass_d5"].sum())}
    json.dump(sel, open("runs/selection.json", "w"), indent=2)
    print(df.to_string(index=False))
    print("ADVANCING:", sel["selected"])

    # best-of-N null: max PF_R across cells, all 100 cells + >=1/wk subset
    keys = list(null.keys())
    wk = {(r["sym"], r["cfg"]): r["trades_wk"]
          for _, r in d[d["harness"] == "H0"].iterrows()}
    keys_all = keys
    keys_1w = [k for k in keys
               if wk.get(tuple(k.rsplit("_", 1)[0].split("_", 1)), 0)
               >= 1.0]

    def maxpf_null(ks, ndraw=10000):
        rng = np.random.default_rng(7)
        arrs = [null[k] for k in ks if len(null[k])]
        if not arrs:
            return np.array([np.nan])
        out = np.empty(ndraw)
        for b in range(ndraw):
            out[b] = max(a[rng.integers(0, len(a))]
                         for a in arrs)
        return out

    for lab, ks in (("all_100_cells", keys_all), ("ge1trwk", keys_1w)):
        b = maxpf_null(ks)
        print(f"max-PF_R null [{lab}]: cells={len(ks)} "
              f"p50={np.nanpercentile(b, 50):.3f} "
              f"p95={np.nanpercentile(b, 95):.3f} "
              f"max={np.nanmax(b):.3f}")
        np.save(f"out/maxpf_null_{lab}.npy", b)

    # deflated sharpe + MC DD for advancing configs
    for _, r in adv.iterrows():
        sym, cid = r["sym"], r["cfg"]
        for h, tag in (("H0", ""), ("H1", "_e1")):
            f = f"out/trades_{sym}_{cid}{tag}.csv"
            if not os.path.exists(f):
                f = f"out/trades_2b_{sym}_{cid}{tag}.csv"
            tr = pd.read_csv(f)
            rv = tr["r_x1"].dropna().to_numpy()
            nk = f"{sym}_{cid}_{h.lower()}"
            nmean = float(np.nanmean(null[nk])) if nk in null else np.nan
            sharpe = (rv.mean() - nmean) / rv.std() * np.sqrt(len(rv)) \
                if rv.std() > 0 else np.nan
            rng = np.random.default_rng(3)
            dds = []
            for _ in range(200):
                o = rng.permutation(rv)
                eq = np.cumsum(o)
                dds.append((np.maximum.accumulate(eq) - eq).max())
            print(f"{sym} {cid} {h}: deflated_sharpe={sharpe:.3f} "
                  f"mc_dd_p95={np.percentile(dds, 95):.1f}R "
                  f"(budget 30R)")


if __name__ == "__main__":
    main()
