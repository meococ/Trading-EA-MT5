#!/usr/bin/env python3
"""Stage 2 (quantify) - EA_ICTVisualEdge / HYP-ICTVIS-EURUSD-M5-001.

Turn the eye's DESIGN-window hypotheses into declared, decision-time-safe feature
functions; measure their separation on the DESIGN split ONLY. TRAIN/VAL stay
untouched here; holdout is unloaded. Every feature reads only bars <= decision
bar i (asof). Output: per-feature separation table (mean-R and win-rate across
quantiles) written to a DESIGN report. Nothing is frozen or tuned to TRAIN here.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
S1 = HERE / "evidence" / "stage1"
PIP = 0.0001
ATR_N = 14
K_MOM = 6           # bars into entry for approach momentum/velocity
LEVEL_LB = 60       # lookback for level-touch / range position
LEVEL_TOL_PIP = 3.0
COMP_SHORT, COMP_LONG = 6, 30


def true_range(bars: pd.DataFrame) -> np.ndarray:
    h = bars["high"].to_numpy(); l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
    pc = np.concatenate([[c[0]], c[:-1]])
    return np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])


def compute_features(bars: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
    l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
    tr = true_range(bars)
    atr = pd.Series(tr).rolling(ATR_N).mean().to_numpy()

    feats = []
    for _, r in cand.iterrows():
        i = int(r["bar_i"]); d = int(r["direction"])
        a = atr[i]
        if not np.isfinite(a) or a <= 0 or i - LEVEL_LB < 0 or i - K_MOM < 0:
            feats.append({})
            continue
        # F1 approach_momentum: trade-direction return over last K bars / ATR.
        # negative => entering AGAINST momentum (short into a rally / long into a drop)
        f1 = d * (c[i] - c[i - K_MOM]) / a
        # F2 approach_velocity_abs
        f2 = abs(c[i] - c[i - K_MOM]) / a
        # F3 level_touch_count around swept extreme (recovered from stored stop:
        # stop = swept_extreme - d*STOP_BUFFER_PIP*PIP, buffer=2.0)
        ext = float(r["stop"]) + d * 2.0 * PIP
        win_h = h[i - LEVEL_LB:i]; win_l = l[i - LEVEL_LB:i]
        touched = np.sum((win_l <= ext + LEVEL_TOL_PIP * PIP) &
                         (win_h >= ext - LEVEL_TOL_PIP * PIP))
        f3 = float(touched)
        # F4 sweep_wick_ratio: rejection wick beyond close on bar i / bar range
        rng = max(h[i] - l[i], 1e-12)
        if d > 0:  # long: swept low, want lower wick
            wick = c[i] - l[i]
        else:      # short: swept high, want upper wick
            wick = h[i] - c[i]
        f4 = wick / rng
        # F5 range_position of entry in recent range (0=low,1=high); shorts want high
        rlo = win_l.min(); rhi = win_h.max()
        pos = (c[i] - rlo) / max(rhi - rlo, 1e-12)
        f5 = pos if d < 0 else (1.0 - pos)   # oriented: higher = better per hypothesis
        # F6 compression: short ATR / long ATR before entry
        trs = pd.Series(tr)
        f6 = (trs.iloc[i - COMP_SHORT:i].mean()) / max(trs.iloc[i - COMP_LONG:i].mean(), 1e-12)
        feats.append({"F1_approach_mom": f1, "F2_velocity": f2, "F3_touch": f3,
                      "F4_wick": f4, "F5_rangepos": f5, "F6_compression": f6})
    fdf = pd.DataFrame(feats, index=cand.index)
    return pd.concat([cand.reset_index(drop=True), fdf.reset_index(drop=True)], axis=1)


def separation(df: pd.DataFrame, feat: str, q: int = 5) -> dict:
    sub = df[np.isfinite(df[feat])].copy()
    if len(sub) < q * 50:
        return {"feature": feat, "n": int(len(sub)), "note": "insufficient"}
    sub["bin"] = pd.qcut(sub[feat], q, labels=False, duplicates="drop")
    g = sub.groupby("bin").agg(n=("r_gross", "size"),
                               mean_r=("r_gross", "mean"),
                               win=("win", "mean"))
    lo, hi = g["mean_r"].iloc[0], g["mean_r"].iloc[-1]
    # spearman monotonicity of mean_r vs bin
    rho = np.corrcoef(g.index.values, g["mean_r"].values)[0, 1]
    return {"feature": feat, "n": int(len(sub)),
            "meanR_lowbin": round(float(lo), 4), "meanR_highbin": round(float(hi), 4),
            "meanR_spread": round(float(hi - lo), 4),
            "win_lowbin": round(float(g["win"].iloc[0]), 4),
            "win_highbin": round(float(g["win"].iloc[-1]), 4),
            "monotonic_rho": round(float(rho), 3),
            "by_bin_meanR": [round(float(x), 4) for x in g["mean_r"].values]}


def main() -> int:
    bars = pd.read_parquet(S1 / "bars_M5.parquet")
    cand = pd.read_parquet(S1 / "candidates_M5.parquet")
    feat_df = compute_features(bars, cand)
    feat_df.to_parquet(S1 / "candidates_M5_features.parquet", index=False)

    design = feat_df[feat_df["split"] == "DESIGN"]
    features = ["F1_approach_mom", "F2_velocity", "F3_touch", "F4_wick",
                "F5_rangepos", "F6_compression"]
    report = {"split": "DESIGN", "n_design": int(len(design)),
              "base_win": round(float(design["win"].mean()), 4),
              "base_mean_r": round(float(design["r_gross"].mean()), 4),
              "features": [separation(design, f) for f in features]}
    (S1 / "stage2_design_separation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
