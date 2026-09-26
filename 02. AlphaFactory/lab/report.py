"""Lab reporting: summarize the falsification ledger from results_log.csv
(readable while the duckdb writer lock is held)."""
import csv
import json
import sys

import numpy as np
import pandas as pd

LOG = "results_log.csv"


def load(latest_only=True):
    """Mixed-schema CSV (v2 rows lack sim_version). Parse per-line so a
    short row is padded sim_version=2; default to current version only."""
    import labels
    rdr = csv.reader(open(LOG, newline=""))
    hdr = next(rdr)
    rows = [r for r in rdr if r]
    n_col = len(hdr)
    if "sim_version" not in hdr:
        # v2 row: ...run_at,verdict (n_col fields)
        # v3 row: ...run_at,sim_version,verdict (n_col+1 fields)
        hdr = hdr[:-1] + ["sim_version", "verdict"]
        rows = [r if len(r) == n_col + 1
                else r[:-1] + ["2", r[-1]] for r in rows]
    df = pd.DataFrame([r for r in rows if len(r) == len(hdr)],
                      columns=hdr)
    for c in ("n_events", "n_kept", "dropped", "mean_p", "t_stat", "pf",
              "win_rate", "cost_rt", "pos_year_frac", "mae_med",
              "mfe_med", "sim_version"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["sim_version"] = df["sim_version"].fillna(2)
    if latest_only:
        df = df[df["sim_version"] == labels.SIM_VERSION]
    df["raw"] = df["mean_p"] + df["cost_rt"]
    p = df["params_json"].apply(json.loads)
    for k in ("hold", "sl", "tp", "hour", "theta", "k"):
        df[k] = p.apply(lambda d: d.get(k, np.nan))
    return df


def main():
    df = load()
    print(f"cells (sim v{int(df['sim_version'].max()) if len(df) else '?'}):"
          f" {len(df)}")
    print("\n=== coverage ===")
    print(df.groupby(["family", "symbol"]).size().unstack(
        fill_value=0).to_string())
    print("\n=== |raw| ceiling per family ===")
    print(df.groupby("family")["raw"].apply(
        lambda x: x.abs().describe()[["mean", "max"]]).unstack().round(3)
        .to_string())
    print("\n=== cells that could beat cost net (|raw|>1.3) ===")
    hot = df[df["raw"].abs() > 1.3]
    print(f"n={len(hot)}")
    if len(hot):
        print(hot[["family", "symbol", "n_kept", "raw", "t_stat", "pf",
                   "params_json"]].round(2).to_string(index=False))
    print("\n=== top 15 by |raw| ===")
    top = df.reindex(df["raw"].abs().sort_values(ascending=False).index)[:15]
    cols = ["family", "symbol", "n_kept", "raw", "t_stat", "pf", "win_rate",
            "hour", "theta", "hold", "sl", "tp"]
    print(top[cols].round(2).to_string(index=False))
    print("\n=== top 15 by t_stat (positive = profitable direction) ===")
    pos = df.nlargest(15, "t_stat")
    print(pos[cols].round(2).to_string(index=False))
    print("\n=== drift_hour leaders by hour ===")
    d = df[df.family == "drift_hour"]
    if len(d):
        best = d.loc[d.groupby(["symbol", "hour"])["t_stat"].idxmax()]
        piv = best.pivot_table(index="hour", columns="symbol",
                               values="raw", aggfunc="first").round(2)
        print(piv.to_string())


if __name__ == "__main__":
    main()
