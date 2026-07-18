"""Parameterized sweep engine for HYP-MR-GRID-EURUSD-H1-002.

Same mechanics as the frozen mr_probe_engine.v1 (next-open fill, SL-first,
frozen-at-entry exits, 5-night cap with Wed x3, cooldown, cost 1.5 pips RT +
0.8 pip per weighted rollover) but every studied axis is a config field.
mr_probe_engine.py itself stays untouched as the 001 record.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from mr_indicators import adx_wilder, atr_percentile, atr_wilder, detrend, rolling_half_life

ENGINE_VERSION = "mr_grid_engine.v1"

PIP = 0.0001
TP_BUFFER_SIGMA = 0.2
TP_MEAN_MIN_DIST = 2.0 * PIP
NIGHT_CAP_EVENTS = 5
TRIPLE_WEEKDAY = 2
GAP_GUARD_ATR = 4.0
TRAIL_ACTIVATE_R = 0.8
TRAIL_ATR_MULT = 1.2
COST_PIPS_RT_X1 = 1.5
SWAP_PIP_PER_UNIT = 0.8
RISK_PCT = 0.25

SPLIT_BOUNDS = {
    "train": (date(2015, 1, 1), date(2020, 12, 31)),
    "validation": (date(2021, 1, 1), date(2022, 12, 31)),
}


@dataclass(frozen=True)
class GateSpec:
    adx_h1: float | None = None          # threshold or None=off
    adx_h4: float | None = None
    atr_band: tuple[float, float] | None = None
    hl_band: tuple[float, float] | None = None


@dataclass(frozen=True)
class CellConfig:
    cell_id: str
    W: int
    z_entry: float
    k_sl: float
    tp_cap_r: float
    k_ts: float
    session: tuple[int, int]
    trailing: bool
    gates: GateSpec                       # gates of the GATED arm


def precompute_base(h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    out = h1.reset_index(drop=True).copy()
    out["atr14"] = atr_wilder(out, 14)
    out["adx14"] = adx_wilder(out, 14)
    out["atr_pctile"] = atr_percentile(out["atr14"], 250)
    h4f = h4.reset_index(drop=True).copy()
    h4f["adx4"] = adx_wilder(h4f, 14)
    h4f["avail_server"] = h4f["time_server"] + pd.Timedelta(hours=4)
    merged = pd.merge_asof(
        out[["time_server"]].assign(decision_server=out["time_server"] + pd.Timedelta(hours=1)),
        h4f[["avail_server", "adx4"]],
        left_on="decision_server", right_on="avail_server",
        direction="backward", allow_exact_matches=True,
    )
    out["adx4"] = merged["adx4"].to_numpy()
    return out


def add_w_features(base: pd.DataFrame, W: int) -> pd.DataFrame:
    out = base.copy()
    D, sigma, z = detrend(out["close"], W)
    out["D"], out["sigma"], out["z"] = D, sigma, z
    out["mu"] = out["close"] - D
    lam, hl = rolling_half_life(D, W)
    out["lam"], out["hl"] = lam, hl
    return out


def run_cell_arm(f: dict[str, np.ndarray], cfg: CellConfig, gated: bool) -> list[dict]:
    """Simulate one arm. `f` is a dict of numpy arrays (fast worker payload)."""
    n = len(f["open"])
    o, h, lo, c = f["open"], f["high"], f["low"], f["close"]
    atr, adx1, adx4, pct = f["atr14"], f["adx14"], f["adx4"], f["atr_pctile"]
    z, mu, sig, hl = f["z"], f["mu"], f["sigma"], f["hl"]
    utc_hour, utc_year = f["utc_hour"], f["utc_year"]
    sdate, sweekday = f["server_dateord"], f["server_weekday"]
    is_val = f["is_validation"]

    g = cfg.gates if gated else GateSpec()
    trades: list[dict] = []
    i = 0
    cooldown = False
    while i < n - 1:
        if cooldown:
            if np.isfinite(z[i]) and abs(z[i]) < cfg.z_entry:
                cooldown = False
            i += 1
            continue

        direction = 0
        if (np.isfinite(z[i]) and np.isfinite(atr[i]) and atr[i] > 0
                and np.isfinite(mu[i]) and np.isfinite(sig[i]) and sig[i] > 0):
            if z[i] <= -cfg.z_entry:
                direction = 1
            elif z[i] >= cfg.z_entry:
                direction = -1
        if direction != 0 and gated:
            if g.adx_h1 is not None and not (np.isfinite(adx1[i]) and adx1[i] < g.adx_h1):
                direction = 0
            elif g.adx_h4 is not None and not (np.isfinite(adx4[i]) and adx4[i] < g.adx_h4):
                direction = 0
            elif g.atr_band is not None and not (np.isfinite(pct[i]) and g.atr_band[0] <= pct[i] <= g.atr_band[1]):
                direction = 0
            elif g.hl_band is not None and not (np.isfinite(hl[i]) and g.hl_band[0] <= hl[i] <= g.hl_band[1]):
                direction = 0
        if direction == 0:
            i += 1
            continue

        e = i + 1
        if not (cfg.session[0] <= utc_hour[e] < cfg.session[1]):
            i += 1
            continue
        if abs(o[e] - c[i]) >= GAP_GUARD_ATR * atr[i]:
            i += 1
            continue

        entry = o[e]
        sgn = float(direction)
        sl = entry - sgn * cfg.k_sl * atr[i]
        r_price = abs(entry - sl)
        if r_price <= 0:
            i += 1
            continue
        tp_mean = mu[i] - sgn * TP_BUFFER_SIGMA * sig[i]
        tp_cap = entry + sgn * cfg.tp_cap_r * r_price
        tp_mean_ok = (tp_mean - entry) * sgn >= TP_MEAN_MIN_DIST
        tp = tp_mean if (tp_mean_ok and abs(tp_mean - entry) < abs(tp_cap - entry)) else tp_cap

        hl_term = math.ceil(cfg.k_ts * hl[i]) if np.isfinite(hl[i]) else math.inf

        sl_cur = sl
        swap_events = 0
        swap_weighted = 0
        exit_idx, exit_price, reason = -1, math.nan, ""
        for j in range(e, n):
            if j > e:
                if sdate[j] > sdate[j - 1]:
                    if swap_events + 1 > NIGHT_CAP_EVENTS:
                        exit_idx, exit_price, reason = j - 1, c[j - 1], "NIGHT_CAP"
                        break
                    swap_events += 1
                    swap_weighted += 3 if sweekday[j - 1] == TRIPLE_WEEKDAY else 1
                if (j - e) >= hl_term:
                    exit_idx, exit_price, reason = j, o[j], "TIME_STOP"
                    break
            if direction == 1:
                if lo[j] <= sl_cur:
                    exit_idx, exit_price, reason = j, sl_cur, "SL"
                    break
                if h[j] >= tp:
                    exit_idx, exit_price, reason = j, tp, "TP"
                    break
            else:
                if h[j] >= sl_cur:
                    exit_idx, exit_price, reason = j, sl_cur, "SL"
                    break
                if lo[j] <= tp:
                    exit_idx, exit_price, reason = j, tp, "TP"
                    break
            if cfg.trailing and (c[j] - entry) * sgn >= TRAIL_ACTIVATE_R * r_price and np.isfinite(atr[j]):
                cand = c[j] - sgn * TRAIL_ATR_MULT * atr[j]
                if (cand - sl_cur) * sgn > 0:
                    sl_cur = cand
        if exit_idx < 0:
            exit_idx, exit_price, reason = n - 1, c[n - 1], "DATA_END"

        gross_r = (exit_price - entry) * sgn / r_price
        r_pips = r_price / PIP
        cost_r_x1 = (COST_PIPS_RT_X1 + SWAP_PIP_PER_UNIT * swap_weighted) / r_pips
        trades.append({
            "split": "validation" if is_val[e] else "train",
            "year": int(utc_year[e]),
            "gross_r": gross_r,
            "net_r_x1": gross_r - cost_r_x1,
            "net_r_x1_5": gross_r - 1.5 * cost_r_x1,
            "net_r_x2": gross_r - 2.0 * cost_r_x1,
            "reason": reason,
        })
        cooldown = True
        i = max(exit_idx, i + 1)
    return trades


def _pf(vals: np.ndarray) -> float | None:
    wins = float(vals[vals > 0].sum())
    losses = float(-vals[vals < 0].sum())
    if losses == 0.0:
        return None if wins == 0.0 else 999.0
    return round(wins / losses, 4)


def summarize_arm(trades: list[dict]) -> dict:
    out: dict = {}
    for split in ("train", "validation", "combined"):
        rows = [t for t in trades if split == "combined" or t["split"] == split]
        lo_d = SPLIT_BOUNDS["train"][0]
        hi_d = SPLIT_BOUNDS["validation"][1] if split == "combined" else SPLIT_BOUNDS[split][1]
        if split == "validation":
            lo_d = SPLIT_BOUNDS["validation"][0]
        weeks = ((hi_d - lo_d).days + 1) / 7.0
        s: dict = {"n": len(rows), "tpw": round(len(rows) / weeks, 4)}
        if rows:
            gross = np.array([t["gross_r"] for t in rows])
            x1 = np.array([t["net_r_x1"] for t in rows])
            s["gross_pf"] = _pf(gross)
            s["pf_x1"] = _pf(x1)
            s["pf_x1_5"] = _pf(np.array([t["net_r_x1_5"] for t in rows]))
            s["pf_x2"] = _pf(np.array([t["net_r_x2"] for t in rows]))
            s["exp_x1"] = round(float(x1.mean()), 5)
            s["net_r_x1"] = round(float(x1.sum()), 3)
            # moments of per-trade net R for later PSR/DSR without reruns
            s["sr_trade"] = round(float(x1.mean() / x1.std(ddof=1)), 5) if len(rows) > 2 and x1.std(ddof=1) > 0 else None
            s["skew"] = round(float(pd.Series(x1).skew()), 4) if len(rows) > 2 else None
            s["kurt"] = round(float(pd.Series(x1).kurt() + 3.0), 4) if len(rows) > 3 else None
            if split == "combined":
                by_year: dict[str, float] = {}
                for t in rows:
                    by_year[str(t["year"])] = round(by_year.get(str(t["year"]), 0.0) + t["net_r_x1"], 3)
                s["by_year_net_r_x1"] = by_year
                # outlier guards (statistics critic BLOCKER 2)
                if len(rows) >= 2:
                    loo = np.delete(x1, int(np.argmax(x1)))
                    s["loo_pf_x1"] = _pf(loo)
                    s["loo_exp_x1"] = round(float(loo.mean()), 5)
                pos = x1[x1 > 0]
                s["top1_win_share"] = round(float(pos.max() / pos.sum()), 4) if len(pos) else None
        out[split] = s
    return out


def frame_to_arrays(feats: pd.DataFrame) -> dict[str, np.ndarray]:
    ts = feats["time_server"]
    tu = feats["time_utc"]
    return {
        "open": feats["open"].to_numpy(float),
        "high": feats["high"].to_numpy(float),
        "low": feats["low"].to_numpy(float),
        "close": feats["close"].to_numpy(float),
        "atr14": feats["atr14"].to_numpy(float),
        "adx14": feats["adx14"].to_numpy(float),
        "adx4": feats["adx4"].to_numpy(float),
        "atr_pctile": feats["atr_pctile"].to_numpy(float),
        "z": feats["z"].to_numpy(float),
        "mu": feats["mu"].to_numpy(float),
        "sigma": feats["sigma"].to_numpy(float),
        "hl": feats["hl"].to_numpy(float),
        "utc_hour": tu.dt.hour.to_numpy(np.int64),
        "utc_year": tu.dt.year.to_numpy(np.int64),
        "server_dateord": ts.map(lambda x: x.toordinal()).to_numpy(np.int64),
        "server_weekday": ts.dt.dayofweek.to_numpy(np.int64),
        "is_validation": (tu >= pd.Timestamp("2021-01-01")).to_numpy(bool),
    }
