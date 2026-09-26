"""run_report.py - selection (D5), ladder anatomy (D4), portfolio (D6).

Reads out/design_summary.csv + out/controls_summary.csv + trade files.
Freezes runs/selection.json BEFORE validation is ever run.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import metrics as mt

WEEKS_D = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)


def main():
    d = pd.read_csv("out/design_summary.csv")
    c = pd.read_csv("out/controls_summary.csv")
    m = d.merge(c[["sym", "cfg", "pct", "pf_flip", "pf_shift20",
                   "null_p95"]], on=["sym", "cfg"], how="left")
    # ---- D5 selection ----------------------------------------------------
    def ok(r):
        return (r["pf_x1"] >= 1.20 and r["pf_x15"] >= 1.05
                and r["trades_wk"] >= 1.0
                and r.get("pos_years", 0) >= 0.6 * r.get("n_years", 1)
                and r.get("pct", 0) >= 95)
    m["sel_ok"] = m.apply(ok, axis=1)
    cand = m[m["sel_ok"] & (m["cfg"] != "F0_J")].copy()
    cand["score"] = cand["exp_r"] * np.sqrt(cand["n"].clip(lower=1))
    cand = cand.sort_values("score", ascending=False).head(3)
    sel = {"selected": [{"sym": r["sym"], "cfg": r["cfg"]}
                        for _, r in cand.iterrows()],
           "rule": "D5 prereg", "frozen_utc": "TBD"}
    import datetime as dt
    sel["frozen_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    with open("runs/selection.json", "w") as f:
        json.dump(sel, f, indent=2)
    m.to_csv("out/selection_table.csv", index=False)
    print("selection:", sel["selected"])
    # ---- ladder anatomy --------------------------------------------------
    j = m[(m["cfg"] == "F0_J")]
    lad = []
    for _, r in m.iterrows():
        if r["family"] != "F1" or r["cfg"] == "F0_J":
            continue
        jrow = j[j["sym"] == r["sym"]]
        if jrow.empty:
            continue
        jrow = jrow.iloc[0]
        lad.append({"sym": r["sym"], "cfg": r["cfg"],
                    "dpf": r["pf_x1"] - jrow["pf_x1"],
                    "dexp": r["exp_r"] - jrow["exp_r"],
                    "dcad": r["trades_wk"] - jrow["trades_wk"],
                    "pf_x1": r["pf_x1"], "exp_r": r["exp_r"],
                    "trades_wk": r["trades_wk"]})
    pd.DataFrame(lad).to_csv("out/ladder.csv", index=False)
    print(pd.DataFrame(lad).to_string())


if __name__ == "__main__":
    main()
