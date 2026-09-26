"""metrics.py - trade-table analytics (D1/D3/D5)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def pf(tr: pd.DataFrame, col: str = "pnl_px_x1") -> float:
    if len(tr) == 0:
        return float("nan")
    g = tr.loc[tr[col] > 0, col].sum()
    l = -tr.loc[tr[col] < 0, col].sum()
    if l == 0:
        return float("inf") if g > 0 else float("nan")
    return float(g / l)


def pf_r(tr: pd.DataFrame, col: str = "r_x1") -> float:
    """PF in R space (E3): account P/L follows R under fixed-% sizing."""
    return pf(tr, col)


def _year(ctm: pd.Series) -> pd.Series:
    return pd.to_datetime(ctm, unit="s", utc=True).dt.year


def max_dd_r(tr: pd.DataFrame, col: str = "r_x1") -> float:
    """Max drawdown in R over the time-ordered r series."""
    if len(tr) == 0:
        return 0.0
    r = tr.sort_values("exit_ctm")[col].fillna(0).to_numpy()
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def summarize(tr: pd.DataFrame, weeks: float) -> dict:
    out = {"n": int(len(tr)),
           "trades_wk": len(tr) / weeks if weeks > 0 else 0.0,
           "pf_x1": pf(tr, "pnl_px_x1"),
           "pf_x15": pf(tr, "pnl_px_x15"),
           "pf_x2": pf(tr, "pnl_px_x2"),
           "pf_r_x1": pf_r(tr, "r_x1"),
           "pf_r_x15": pf_r(tr, "r_x15"),
           "win": float((tr["r_x1"] > 0).mean()) if len(tr) else np.nan,
           "exp_r": float(tr["r_x1"].mean()) if len(tr) else np.nan,
           "maxdd_r": max_dd_r(tr),
           "mfe_med": float(tr["mfe_r"].median()) if len(tr) else np.nan,
           "mae_med": float(tr["mae_r"].median()) if len(tr) else np.nan,
           "suspect": int(tr["suspect_fill"].sum()
                          + tr["suspect_exit"].sum()) if len(tr) else 0}
    if len(tr):
        yrs = tr.groupby(_year(tr["exit_ctm"]))
        pfy = yrs.apply(lambda g: pf(g, "pnl_px_x1"))
        out["pf_by_year"] = {int(k): round(float(v), 2)
                             for k, v in pfy.items()}
        out["pos_years"] = int((yrs["pnl_px_x1"].sum() > 0).sum())
        out["n_years"] = int(yrs.ngroups)
        out["pf_long"] = pf(tr[tr["dir"] == 1], "pnl_px_x1")
        out["pf_short"] = pf(tr[tr["dir"] == -1], "pnl_px_x1")
        tr_clean = tr[~(tr["suspect_fill"] | tr["suspect_exit"])]
        out["pf_x1_clean"] = pf(tr_clean, "pnl_px_x1")
    return out


def sharpe(tr: pd.DataFrame, col: str = "r_x1") -> float:
    if len(tr) < 3:
        return float("nan")
    r = tr[col].dropna().to_numpy()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(len(r))) if sd > 0 else np.nan
