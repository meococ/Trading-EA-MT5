"""Offline probe engine for HYP-MR-REGIME-EURUSD-H1-001 (frozen surface).

Honors PROBE_PLAN_V2 sections 4/5/9: closed-bar features at t, fill at t+1
open, SL-first worst-case intrabar, frozen-at-entry mu/sigma/R/HL, trailing
+0.8R -> close -/+ 1.2xATR(t) (both arms), re-entry cooldown (both arms),
time-stop min(ceil(2xHL_e), 5-night cap by charged rollover events, Fri->Mon=1,
Wed weight x3), cost = 1.5 pips RT + 0.8 pip per weighted rollover, stress
x1.5/x2. Research screen only: promotion_eligible=false, cost UNVERIFIED_PROXY.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from mr_indicators import adx_wilder, atr_percentile, atr_wilder, detrend, rolling_half_life

ENGINE_VERSION = "mr_probe_engine.v1"

PIP = 0.0001
W = 100
Z_ENTRY = 2.0
K_SL = 2.0
TP_BUFFER_SIGMA = 0.2
TP_CAP_R = 1.5
TP_MEAN_MIN_DIST = 2.0 * PIP  # 2 x spread_p50 proxy (0.1 pip) = 0.2 pip
K_TS = 2.0
NIGHT_CAP_EVENTS = 5
TRIPLE_WEEKDAY = 2  # Wednesday (rollover charged x3)
GAP_GUARD_ATR = 4.0
SESSION_UTC = (7, 16)  # entry-bar open hour, half-open [7,16)
ADX_H1_MAX = 23.0
ADX_H4_MAX = 28.0
ATR_PCTILE_BAND = (25.0, 75.0)
HL_BAND = (4.0, 48.0)
TRAIL_ACTIVATE_R = 0.8
TRAIL_ATR_MULT = 1.2
COST_PIPS_RT_X1 = 1.5
SWAP_PIP_PER_UNIT = 0.8
RISK_PCT = 0.25


def compute_features(h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    out = h1.reset_index(drop=True).copy()
    out["atr14"] = atr_wilder(out, 14)
    out["adx14"] = adx_wilder(out, 14)
    D, sigma, z = detrend(out["close"], W)
    out["D"], out["sigma"], out["z"] = D, sigma, z
    out["mu"] = out["close"] - D
    lam, hl = rolling_half_life(D, W)
    out["lam"], out["hl"] = lam, hl
    out["atr_pctile"] = atr_percentile(out["atr14"], 250)

    # Last CLOSED H4 ADX available at the H1 decision time (t_open + 1h).
    h4f = h4.reset_index(drop=True).copy()
    h4f["adx4"] = adx_wilder(h4f, 14)
    h4f["avail_server"] = h4f["time_server"] + pd.Timedelta(hours=4)
    merged = pd.merge_asof(
        out[["time_server"]].assign(decision_server=out["time_server"] + pd.Timedelta(hours=1)),
        h4f[["avail_server", "adx4"]],
        left_on="decision_server",
        right_on="avail_server",
        direction="backward",
        allow_exact_matches=True,
    )
    out["adx4"] = merged["adx4"].to_numpy()
    return out


@dataclass
class Trade:
    arm: str
    direction: int  # +1 long, -1 short
    sig_idx: int
    entry_idx: int
    entry: float
    sl: float
    tp: float
    tp_binding: str
    r_price: float
    hl_e: float
    ts_bars: float
    exit_idx: int = -1
    exit_price: float = math.nan
    exit_reason: str = ""
    swap_events: int = 0
    swap_weighted: int = 0
    gross_r: float = math.nan
    times: dict = field(default_factory=dict)

    def r_pips(self) -> float:
        return self.r_price / PIP

    def cost_pips(self, mult: float) -> float:
        return (COST_PIPS_RT_X1 + SWAP_PIP_PER_UNIT * self.swap_weighted) * mult

    def net_r(self, mult: float) -> float:
        return self.gross_r - self.cost_pips(mult) / self.r_pips()


def _base_valid(f: pd.DataFrame, i: int) -> bool:
    return (
        np.isfinite(f.at[i, "z"])
        and np.isfinite(f.at[i, "atr14"])
        and f.at[i, "atr14"] > 0
        and np.isfinite(f.at[i, "mu"])
        and np.isfinite(f.at[i, "sigma"])
        and f.at[i, "sigma"] > 0
    )


def _challenger_gates(f: pd.DataFrame, i: int) -> bool:
    adx4 = f.at[i, "adx4"]
    pct = f.at[i, "atr_pctile"]
    hl = f.at[i, "hl"]
    return (
        np.isfinite(f.at[i, "adx14"]) and f.at[i, "adx14"] < ADX_H1_MAX
        and np.isfinite(adx4) and adx4 < ADX_H4_MAX
        and np.isfinite(pct) and ATR_PCTILE_BAND[0] <= pct <= ATR_PCTILE_BAND[1]
        and np.isfinite(hl) and HL_BAND[0] <= hl <= HL_BAND[1]
    )


def run_arm(f: pd.DataFrame, arm: str) -> list[Trade]:
    """Sequential single-position simulation over the full frame."""
    n = len(f)
    t_server = f["time_server"]
    t_utc = f["time_utc"]
    o = f["open"].to_numpy(float)
    h = f["high"].to_numpy(float)
    lo = f["low"].to_numpy(float)
    c = f["close"].to_numpy(float)
    atr = f["atr14"].to_numpy(float)
    z = f["z"].to_numpy(float)

    trades: list[Trade] = []
    i = 0
    cooldown = False
    while i < n - 1:
        if cooldown:
            if np.isfinite(z[i]) and abs(z[i]) < Z_ENTRY:
                cooldown = False
            i += 1
            continue

        direction = 0
        if _base_valid(f, i):
            if z[i] <= -Z_ENTRY:
                direction = 1
            elif z[i] >= Z_ENTRY:
                direction = -1
        if direction != 0 and arm == "challenger" and not _challenger_gates(f, i):
            direction = 0
        if direction == 0:
            i += 1
            continue

        e = i + 1
        hour = t_utc.iloc[e].hour
        if not (SESSION_UTC[0] <= hour < SESSION_UTC[1]):
            i += 1
            continue
        if abs(o[e] - c[i]) >= GAP_GUARD_ATR * atr[i]:
            i += 1
            continue

        entry = o[e]
        sgn = float(direction)
        sl = entry - sgn * K_SL * atr[i]
        r_price = abs(entry - sl)
        if r_price <= 0:
            i += 1
            continue
        mu_e, sig_e = float(f.at[i, "mu"]), float(f.at[i, "sigma"])
        tp_mean = mu_e - sgn * TP_BUFFER_SIGMA * sig_e
        tp_cap = entry + sgn * TP_CAP_R * r_price
        tp_mean_ok = (tp_mean - entry) * sgn >= TP_MEAN_MIN_DIST
        if tp_mean_ok and abs(tp_mean - entry) < abs(tp_cap - entry):
            tp, binding = tp_mean, "TP_mean"
        else:
            tp, binding = tp_cap, "TP_cap"

        hl_e = float(f.at[i, "hl"])
        hl_term = math.ceil(K_TS * hl_e) if np.isfinite(hl_e) else math.inf

        tr = Trade(
            arm=arm, direction=direction, sig_idx=i, entry_idx=e, entry=entry,
            sl=sl, tp=tp, tp_binding=binding, r_price=r_price,
            hl_e=hl_e if np.isfinite(hl_e) else math.nan,
            ts_bars=hl_term if hl_term is not math.inf else math.nan,
        )
        tr.times = {
            "feature_time_utc": str(t_utc.iloc[i] + pd.Timedelta(hours=1)),
            "decision_time_utc": str(t_utc.iloc[i] + pd.Timedelta(hours=1)),
            "execution_time_utc": str(t_utc.iloc[e]),
            "entry_time_server": str(t_server.iloc[e]),
        }

        # ---- manage ----
        sl_cur = sl
        exited = False
        for j in range(e, n):
            if j > e:
                prev, cur = t_server.iloc[j - 1], t_server.iloc[j]
                if cur.date() > prev.date():
                    weight = 3 if prev.dayofweek == TRIPLE_WEEKDAY else 1
                    if tr.swap_events + 1 > NIGHT_CAP_EVENTS:
                        tr.exit_idx, tr.exit_price, tr.exit_reason = j - 1, c[j - 1], "NIGHT_CAP"
                        exited = True
                        break
                    tr.swap_events += 1
                    tr.swap_weighted += weight
                if (j - e) >= hl_term:
                    tr.exit_idx, tr.exit_price, tr.exit_reason = j, o[j], "TIME_STOP"
                    exited = True
                    break
            # intrabar: SL first (worst case), then TP
            if direction == 1:
                if lo[j] <= sl_cur:
                    tr.exit_idx, tr.exit_price, tr.exit_reason = j, sl_cur, "SL"
                    exited = True
                    break
                if h[j] >= tp:
                    tr.exit_idx, tr.exit_price, tr.exit_reason = j, tp, "TP"
                    exited = True
                    break
            else:
                if h[j] >= sl_cur:
                    tr.exit_idx, tr.exit_price, tr.exit_reason = j, sl_cur, "SL"
                    exited = True
                    break
                if lo[j] <= tp:
                    tr.exit_idx, tr.exit_price, tr.exit_reason = j, tp, "TP"
                    exited = True
                    break
            # trailing at bar close (affects later bars), monotonic, 1x/bar
            if (c[j] - entry) * sgn >= TRAIL_ACTIVATE_R * r_price and np.isfinite(atr[j]):
                cand = c[j] - sgn * TRAIL_ATR_MULT * atr[j]
                if (cand - sl_cur) * sgn > 0:
                    sl_cur = cand
        if not exited:
            tr.exit_idx, tr.exit_price, tr.exit_reason = n - 1, c[n - 1], "DATA_END"

        tr.gross_r = (tr.exit_price - entry) * sgn / r_price
        tr.times["exit_time_server"] = str(t_server.iloc[tr.exit_idx])
        trades.append(tr)
        cooldown = True
        i = max(tr.exit_idx, i + 1)
    return trades


def split_of(entry_time_utc: pd.Timestamp) -> str:
    return "train" if entry_time_utc < pd.Timestamp("2021-01-01") else "validation"


SPLIT_BOUNDS = {
    "train": (date(2015, 1, 1), date(2020, 12, 31)),
    "validation": (date(2021, 1, 1), date(2022, 12, 31)),
}


def _pf(values: list[float]) -> float | None:
    wins = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses == 0:
        return None if wins == 0 else float("inf")
    return wins / losses


def metrics_for(trades: list[Trade], f: pd.DataFrame, split: str) -> dict:
    rows = [t for t in trades if split_of(f["time_utc"].iloc[t.entry_idx]) == split]
    lo_d, hi_d = SPLIT_BOUNDS[split]
    weeks = ((hi_d - lo_d).days + 1) / 7.0
    out: dict = {"trades": len(rows), "elapsed_weeks": round(weeks, 2),
                 "trades_per_week": round(len(rows) / weeks, 4)}
    if not rows:
        return out
    gross = [t.gross_r for t in rows]
    out["gross_pf"] = _round(_pf(gross))
    for label, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        net = [t.net_r(mult) for t in rows]
        out[f"pf_{label}"] = _round(_pf(net))
        out[f"net_r_{label}"] = round(sum(net), 4)
        if label == "x1":
            out["expectancy_r_x1"] = round(float(np.mean(net)), 5)
            out["win_rate_x1"] = round(float(np.mean([v > 0 for v in net])), 4)
            eq, peak, dd_r, cum = 1.0, 1.0, 0.0, 0.0
            cum_peak = 0.0
            dd_pct = 0.0
            for v in net:
                cum += v
                cum_peak = max(cum_peak, cum)
                dd_r = max(dd_r, cum_peak - cum)
                eq *= 1.0 + (RISK_PCT / 100.0) * v
                peak = max(peak, eq)
                dd_pct = max(dd_pct, (peak - eq) / peak)
            out["max_dd_r_x1"] = round(dd_r, 3)
            out["max_dd_pct_x1_at_risk0_25"] = round(100.0 * dd_pct, 3)
            by_year: dict[int, float] = {}
            for t in rows:
                y = int(f["time_utc"].iloc[t.entry_idx].year)
                by_year[y] = by_year.get(y, 0.0) + t.net_r(1.0)
            out["by_year_net_r_x1"] = {str(k): round(v, 3) for k, v in sorted(by_year.items())}
    out["exit_reasons"] = {
        r: sum(1 for t in rows if t.exit_reason == r)
        for r in sorted({t.exit_reason for t in rows})
    }
    return out


def _round(v: float | None) -> float | None:
    if v is None:
        return None
    if math.isinf(v):
        return 999.0
    return round(v, 4)
