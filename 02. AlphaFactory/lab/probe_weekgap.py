"""HYP-WGAP-JPY-M1-001 — committed probe reproducing the prereg cell.

Mechanism: USDJPY Monday 01:00-server LONG conditioned on weekend gap
< -2p, SL 20p, time-exit at close of the 02:01 bar (hold=60 bars).

Level semantics (no lookahead):
- Signal bar t = bar stamped Monday 01:00 server (lab dow: pandas 0=Mon).
- gap[t] uses the week's FIRST bar (the first bar whose lab `day` index
  changes = week reopen, stamped 00:00-00:05 Mon): gap = open[first] -
  close[first-1]. Both legs are known by ~00:06, ~55 min before the
  decision. The first bar is typically suspect-flagged (daily-summary
  record): only its OPEN is used — verified cross-broker exact on
  8/8 recent Mondays; its h/l are fabricated and never read.
- Entry at open of t+1 (01:01 bar). Exits: SL 20p intrabar, else close
  of bar stamped 02:01 (entry+60).

Run: python probe_weekgap.py
Writes: lab ledger row via sweep.Lab + event artifact CSV.
"""
import numpy as np
import pandas as pd

import data_plane
import labels
import sweep


def run(symbol="USDJPY", gap_thresh=-2.0, hold=60, sl=20.0):
    dp = data_plane.load(symbol)
    pip = data_plane.pip_size(symbol)
    ev = labels.Evaluator(dp, pip)
    cost = labels.spread_cost_arr(dp)

    dow = dp["dow"].to_numpy()
    mod = dp["mod"].to_numpy()
    day = dp["day"].to_numpy()
    c = dp["c"].to_numpy()
    o = dp["o"].to_numpy()
    firstbar = np.r_[True, day[1:] != day[:-1]]
    gap = np.zeros(len(dp))
    idx = np.flatnonzero(firstbar)
    prev = idx - 1
    ok = prev >= 0
    gap[idx[ok]] = (o[idx[ok]] - c[prev[ok]]) / pip

    evpos = np.flatnonzero((dow == 0) & (mod == 60))
    fb_of = np.array([np.flatnonzero(firstbar[:i + 1])[-1] for i in evpos])
    g = gap[fb_of]

    mask = np.zeros(len(dp), dtype=bool)
    mask[evpos[g < gap_thresh]] = True

    res = ev.eval(mask, 1, sl, 0.0, hold, cost_arr=cost)
    ret = res["ret"]
    yrs = pd.to_datetime(res["ctm"], unit="s").year.to_numpy()

    lab = sweep.Lab()
    cell = {
        "family": "weekgap_fade",
        "symbol": symbol,
        "side": 1,
        "dow": 0, "hour": 1, "gap_thresh": gap_thresh,
        "hold": hold, "sl": sl, "tp": 0,
    }
    row = lab.record(cell, res, cost_rt=float(np.mean(cost[evpos[g < gap_thresh]])))
    print("ledger row:", {k: row[k] for k in
          ("family", "symbol", "n_kept", "mean_p", "t_stat", "pf",
           "pos_year_frac", "verdict")})

    # Align gap to KEPT events by signal-bar ctm (positional slicing
    # misaligns after mid-stream drops — auditor catch, GATE B r2).
    sig_ctm = dp.index.to_numpy()[evpos]
    gap_by_ctm = dict(zip(sig_ctm.tolist(), g.tolist()))
    art = pd.DataFrame({
        "ctm": res["ctm"], "ret_pips": ret, "exit": res["exit"],
        "mae": res["mae"], "mfe": res["mfe"],
        "gap_pips": [gap_by_ctm[int(t)] for t in res["ctm"]],
    })
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "03. EA Developer", "EA_WeekGap",
                       "research", "evidence", "wgap_jpy_events.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    art.to_csv(out, index=False)
    print("artifact:", out, len(art), "events")
    print(f"headline: n={len(ret)} net={ret.mean():+.2f} PF={labels.pf(ret):.3f}")
    return res


if __name__ == "__main__":
    run()
