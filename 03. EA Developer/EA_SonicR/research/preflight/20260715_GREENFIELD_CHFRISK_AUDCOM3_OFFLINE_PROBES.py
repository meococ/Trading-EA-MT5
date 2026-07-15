#!/usr/bin/env python3
"""Round 7 greenfield — outside Round6 densify + prior bans.

FORBIDDEN densify:
  ≠ EUR triad parity z / NAS β / XAU-XAG ratio (Round6)
  ≠ FX3 H4 majority/TS/spring/PB/solo/accept/disp/ER/split/halfback (R1–R5)
  ≠ XS residual/mom · AUDNZD ZMR · XAU USD-beta · AONIA/CORRA/thin3
  ≠ carry/anticarry · D1 vol-regime/ADX swing · LNY · FRED · WTI/Brent
  ≠ Weekly-HL · VWAP · NR7/ORB · SB/M15 densify · exit-RR2

A priori (≥3 named; probe top 3), +$12 joint, Model 0 only if PROBE_SURVIVOR:
  1) HYP-USDCHF-H1-FXRISK-BASKET-RESID-FADE-001
  2) HYP-AUD-COM3-H1-BASKET-RESID-MR-001
  3) HYP-FX3-H1-ADR-EXHAUST-FADE-001

W1 HL-break / M15 thick-stop: remain PARKED (de-dup / densify risk).

Nested critic: cursor-grok-4.5-high-fast (lead self-merge; Task backend unavailable).
Panel: Sonic trader / quant validation / MQL5 systems
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

OUT_JSON = PRE / "20260715_GREENFIELD_CHFRISK_AUDCOM3_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_CHFRISK_AUDCOM3_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_CHFRISK_AUDCOM3_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_CHFRISK_AUDCOM3_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_CHFRISK_AUDCOM3_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_CHFRISK_AUDCOM3_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_CHFRISK_AUDCOM3_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
BETA_FROM = datetime(2019, 1, 1)
BETA_TO = datetime(2020, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- 1 USDCHF × FX risk-basket frozen-β residual fade ---
CHF_Z_LB = 60
CHF_Z_ENTRY = 1.75
CHF_SL = 1.2
CHF_RR = 2.0
CHF_HOLD = 24
CHF_FIRE_UTC = 12
CHF_MAX_PER_DAY = 1

# --- 2 AUD commodity ternary residual MR ---
COM_Z_LB = 48
COM_Z_ENTRY = 2.0
COM_SL = 1.5
COM_RR = 1.5
COM_HOLD = 36
COM_FIRE_UTC = 0  # Asia commodity fix window
COM_MAX_PER_DAY = 1

# --- 3 FX3 H1 ADR exhaustion fade ---
ADR_K = 0.90
ADR_SL = 1.5
ADR_RR = 1.5
ADR_HOLD = 16
ADR_FIRE_UTC = 8  # London open vicinity
ADR_MAX_PER_DAY = 1
FX3 = ("EURUSD", "GBPUSD", "USDJPY")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls):
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls):
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls):
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(n / WEEKS, 4) if WEEKS else None,
    }


def joint_verdict(m, hc):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0:
        notes.append("cadence_fail")
    if hc["x1_5"]["pf"] is None or hc["x1_5"]["pf"] < 1.25:
        notes.append("stress_fail")
    return ("PROBE_SURVIVOR", []) if not notes else ("KILLED_AT_OFFLINE_PROBE", notes)


def atr_arr(h, l, c, n=14):
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    out = np.full_like(tr, np.nan, dtype=float)
    s = tr[:n].sum()
    out[n - 1] = s / n
    for i in range(n, len(tr)):
        s = s - tr[i - n] + tr[i]
        out[i] = s / n
    return out


def rolling_z(x: np.ndarray, lb: int) -> np.ndarray:
    """Rolling z using last `lb` finite observations ending at i (gap-aware)."""
    out = np.full_like(x, np.nan, dtype=float)
    finite_vals: list[float] = []
    for i, v in enumerate(x):
        if np.isfinite(v):
            finite_vals.append(float(v))
            if len(finite_vals) > lb:
                finite_vals = finite_vals[-lb:]
            if len(finite_vals) < lb:
                continue
            w = np.asarray(finite_vals, dtype=float)
            mu = float(np.mean(w))
            sd = float(np.std(w, ddof=1))
            if sd <= 1e-12:
                continue
            out[i] = (w[-1] - mu) / sd
    return out


def load(symbol, tf, fr=FROM, to=TO):
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, tf, fr, to)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"{symbol} tf={tf}: {mt5.last_error()}")
    return {
        "t": rates["time"].astype(np.int64),
        "o": rates["open"].astype(float),
        "h": rates["high"].astype(float),
        "l": rates["low"].astype(float),
        "c": rates["close"].astype(float),
    }


def enrich(d):
    d["atr"] = atr_arr(d["h"], d["l"], d["c"])
    return d


def pip_size(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.01 if "JPY" in symbol else 0.0001
    return info.point * (10 if info.digits in (3, 5) else 1)


def cash_pnl(symbol, side, entry, exit_px, lots):
    info = mt5.symbol_info(symbol)
    tick_val = float(info.trade_tick_value) if info else 1.0
    tick_size = float(info.trade_tick_size) if info else pip_size(symbol)
    if tick_size <= 0:
        tick_size = pip_size(symbol)
    return (exit_px - entry) * side / tick_size * tick_val * lots


def risk_lots(symbol, entry, sl):
    info = mt5.symbol_info(symbol)
    risk = DEPOSIT * RISK_FRAC
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss = dist / tick_size * tick_val
    if loss <= 0:
        return 0.01
    return min(5.0, max(0.01, math.floor(risk / loss * 100) / 100))


def manage_exits(open_pos, data, ts, closed, hold_limit):
    still = []
    for pos in open_pos:
        sym = pos["sym"]
        d = data[sym]
        idx = int(np.searchsorted(d["t"], ts, side="left"))
        if idx >= len(d["t"]) or d["t"][idx] != ts:
            still.append(pos)
            continue
        exit_px = None
        reason = None
        if pos["side"] > 0:
            if d["l"][idx] <= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["h"][idx] >= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        else:
            if d["h"][idx] >= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["l"][idx] <= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        pos["bars"] += 1
        if exit_px is None and pos["bars"] >= hold_limit:
            exit_px, reason = d["c"][idx], "time"
        if exit_px is not None:
            closed.append(
                {
                    "pnl": cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"]),
                    "reason": reason,
                    "sym": sym,
                }
            )
        else:
            still.append(pos)
    return still


def flush_open(open_pos, data, closed):
    for pos in open_pos:
        d = data[pos["sym"]]
        closed.append(
            {
                "pnl": cash_pnl(
                    pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]
                ),
                "reason": "eod",
                "sym": pos["sym"],
            }
        )


def summarize(closed):
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail


def align_on(clock_t, d):
    idx = np.searchsorted(d["t"], clock_t, side="left")
    out = np.full(len(clock_t), -1, dtype=np.int64)
    for i, (j, ts) in enumerate(zip(idx, clock_t)):
        if j < len(d["t"]) and d["t"][j] == ts:
            out[i] = j
    return out


def logret(c0, c1):
    if c0 <= 0 or c1 <= 0:
        return None
    return math.log(c1 / c0)


def fit_chf_fxrisk_beta(chf_pre, eu_pre, gu_pre, uj_pre):
    """OLS: r_USDCHF = α + β * risk_on; risk_on=mean(r_EU,r_GU,-r_UJ)."""
    clock = chf_pre["t"]
    ie = align_on(clock, eu_pre)
    ig = align_on(clock, gu_pre)
    ij = align_on(clock, uj_pre)
    y = []
    x = []
    for i in range(1, len(clock)):
        if min(ie[i], ig[i], ij[i], ie[i - 1], ig[i - 1], ij[i - 1]) < 0:
            continue
        if eu_pre["t"][ie[i]] != clock[i] or gu_pre["t"][ig[i]] != clock[i]:
            continue
        if uj_pre["t"][ij[i]] != clock[i]:
            continue
        if eu_pre["t"][ie[i - 1]] != clock[i - 1]:
            continue
        if gu_pre["t"][ig[i - 1]] != clock[i - 1]:
            continue
        if uj_pre["t"][ij[i - 1]] != clock[i - 1]:
            continue
        rc = logret(chf_pre["c"][i - 1], chf_pre["c"][i])
        re = logret(eu_pre["c"][ie[i - 1]], eu_pre["c"][ie[i]])
        rg = logret(gu_pre["c"][ig[i - 1]], gu_pre["c"][ig[i]])
        rj = logret(uj_pre["c"][ij[i - 1]], uj_pre["c"][ij[i]])
        if None in (rc, re, rg, rj):
            continue
        risk_on = (re + rg + (-rj)) / 3.0
        y.append(rc)
        x.append(risk_on)
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if len(y) < 200:
        raise RuntimeError(f"CHF beta freeze sample too small: {len(y)}")
    X = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    yhat = X @ coef
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {
        "alpha": alpha,
        "beta": beta,
        "n_fit": int(len(y)),
        "r2": round(r2, 6),
        "window": "2019-01-01..2020-12-31",
        "driver": "FX_RISK_BASKET_mean(EU,GU,-UJ)",
    }


def probe_chf_fxrisk_resid(data, beta_fit):
    closed = []
    chf = data["USDCHF"]
    eu = data["EURUSD"]
    gu = data["GBPUSD"]
    uj = data["USDJPY"]
    clock = chf["t"]
    ie = align_on(clock, eu)
    ig = align_on(clock, gu)
    ij = align_on(clock, uj)
    alpha, beta = beta_fit["alpha"], beta_fit["beta"]

    resid = np.full(len(clock), np.nan)
    for i in range(1, len(clock)):
        if min(ie[i], ig[i], ij[i], ie[i - 1], ig[i - 1], ij[i - 1]) < 0:
            continue
        if eu["t"][ie[i]] != clock[i] or gu["t"][ig[i]] != clock[i]:
            continue
        if uj["t"][ij[i]] != clock[i]:
            continue
        if eu["t"][ie[i - 1]] != clock[i - 1]:
            continue
        if gu["t"][ig[i - 1]] != clock[i - 1]:
            continue
        if uj["t"][ij[i - 1]] != clock[i - 1]:
            continue
        rc = logret(chf["c"][i - 1], chf["c"][i])
        re = logret(eu["c"][ie[i - 1]], eu["c"][ie[i]])
        rg = logret(gu["c"][ig[i - 1]], gu["c"][ig[i]])
        rj = logret(uj["c"][ij[i - 1]], uj["c"][ij[i]])
        if None in (rc, re, rg, rj):
            continue
        risk_on = (re + rg + (-rj)) / 3.0
        resid[i] = rc - (alpha + beta * risk_on)
    z = rolling_z(resid, CHF_Z_LB)

    open_pos = []
    day_count = {}
    funnel = {
        "n_bars": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_hour": 0,
        "n_skip_open": 0,
    }
    data_map = {"USDCHF": chf}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data_map, ts, closed, CHF_HOLD)
        j = i - 1
        if j < CHF_Z_LB + 5:
            continue
        if dt.weekday() >= 5:
            continue
        funnel["n_bars"] += 1
        if dt.hour != CHF_FIRE_UTC:
            funnel["n_skip_hour"] += 1
            continue
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= CHF_MAX_PER_DAY:
            continue
        zj = z[j]
        if not np.isfinite(zj) or abs(zj) < CHF_Z_ENTRY:
            continue
        atr = chf["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        funnel["n_signal"] += 1
        # Fade: z>0 => USDCHF rich vs FX-risk beta => short USDCHF
        side = -1 if zj > 0 else 1
        entry = float(chf["o"][i])
        sl = entry - side * CHF_SL * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * CHF_RR * risk
        open_pos.append(
            {
                "sym": "USDCHF",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots("USDCHF", entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    detail["beta_fit"] = beta_fit
    detail["resid_finite"] = int(np.isfinite(resid).sum())
    return pnls, detail


def probe_aud_com3(data):
    """Fade AUDUSD when ln(AUD)-0.5ln(NZD)-0.5ln(CAD) z extreme."""
    closed = []
    aud = data["AUDUSD"]
    nzd = data["NZDUSD"]
    cad = data["USDCAD"]
    clock = aud["t"]
    inz = align_on(clock, nzd)
    # CAD quoted as USDCAD → CADUSD = 1/USDCAD
    ic = align_on(clock, cad)

    spread = np.full(len(clock), np.nan)
    for i in range(len(clock)):
        if inz[i] < 0 or ic[i] < 0:
            continue
        a = aud["c"][i]
        n = nzd["c"][inz[i]]
        u = cad["c"][ic[i]]
        if a <= 0 or n <= 0 or u <= 0:
            continue
        cad_usd = 1.0 / u
        spread[i] = math.log(a) - 0.5 * math.log(n) - 0.5 * math.log(cad_usd)
    z = rolling_z(spread, COM_Z_LB)

    open_pos = []
    day_count = {}
    funnel = {
        "n_bars": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_hour": 0,
        "n_skip_open": 0,
    }
    data_map = {"AUDUSD": aud}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data_map, ts, closed, COM_HOLD)
        j = i - 1
        if j < COM_Z_LB + 5:
            continue
        if dt.weekday() >= 5:
            continue
        funnel["n_bars"] += 1
        if dt.hour != COM_FIRE_UTC:
            funnel["n_skip_hour"] += 1
            continue
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= COM_MAX_PER_DAY:
            continue
        zj = z[j]
        if not np.isfinite(zj) or abs(zj) < COM_Z_ENTRY:
            continue
        atr = aud["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        funnel["n_signal"] += 1
        # z>0 => AUD rich vs NZD/CAD basket => short AUDUSD
        side = -1 if zj > 0 else 1
        entry = float(aud["o"][i])
        sl = entry - side * COM_SL * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * COM_RR * risk
        open_pos.append(
            {
                "sym": "AUDUSD",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots("AUDUSD", entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    detail["spread_finite"] = int(np.isfinite(spread).sum())
    return pnls, detail


def probe_fx3_adr_exhaust(data):
    """Fade FX3 when intraday range already ≥ k*ATR_D1 by London fire hour."""
    closed = []
    # Build D1 ATR map per symbol from D1 bars
    d1_atr: dict[str, dict[int, float]] = {}
    d1_data = {}
    for sym in FX3:
        d1 = enrich(load(sym, mt5.TIMEFRAME_D1))
        d1_data[sym] = d1
        mp = {}
        for i, ts in enumerate(d1["t"]):
            # map calendar day (UTC date of D1 bar open) -> ATR of *prior* closed D1
            if i < 1:
                continue
            day_ts = int(ts)
            atr_prev = d1["atr"][i - 1]
            if np.isfinite(atr_prev) and atr_prev > 0:
                mp[day_ts] = float(atr_prev)
        d1_atr[sym] = mp

    open_pos = []
    day_count: dict[str, int] = {}
    funnel = {
        "n_bars": 0,
        "n_eligible": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_open": 0,
        "n_skip_day": 0,
    }
    data_map = {s: data[s] for s in FX3}

    # Union clock from EURUSD
    clock = data["EURUSD"]["t"]
    idx_map = {s: align_on(clock, data[s]) for s in FX3}

    # Running day H/L from day open (H1 open of hour 0 or first bar of day)
    day_hl: dict[str, dict[str, float]] = {s: {} for s in FX3}
    day_open: dict[str, dict[str, float]] = {s: {} for s in FX3}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data_map, ts, closed, ADR_HOLD)
        if dt.weekday() >= 5:
            continue
        funnel["n_bars"] += 1
        day = dt.date().isoformat()

        # Update running day stats on closed prior bar for each sym
        j = i - 1
        if j < 20:
            continue
        for sym in FX3:
            k = idx_map[sym][j]
            if k < 0:
                continue
            dj = datetime.fromtimestamp(int(data[sym]["t"][k]), tz=timezone.utc)
            dkey = dj.date().isoformat()
            h = float(data[sym]["h"][k])
            l = float(data[sym]["l"][k])
            o = float(data[sym]["o"][k])
            if dkey not in day_open[sym]:
                day_open[sym][dkey] = o
                day_hl[sym][dkey] = [h, l]
            else:
                day_hl[sym][dkey][0] = max(day_hl[sym][dkey][0], h)
                day_hl[sym][dkey][1] = min(day_hl[sym][dkey][1], l)

        if dt.hour != ADR_FIRE_UTC:
            continue
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        if day_count.get(day, 0) >= ADR_MAX_PER_DAY:
            funnel["n_skip_day"] += 1
            continue

        # Pick first eligible symbol (a priori order EURUSD→GBPUSD→USDJPY)
        picked = None
        for sym in FX3:
            k = idx_map[sym][j]
            if k < 0:
                continue
            if day not in day_hl[sym] or day not in day_open[sym]:
                continue
            # prior D1 ATR: use D1 bar whose open date == day (maps to prior ATR)
            # Find D1 timestamp for this calendar day
            d1 = d1_data[sym]
            # search D1 bar with same UTC date
            day_epoch = int(
                datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp()
            )
            # ATR of prior day: look up by matching D1 open date key loosely
            atr_d1 = None
            di = int(np.searchsorted(d1["t"], day_epoch, side="left"))
            if di < len(d1["t"]) and d1["t"][di] == day_epoch and di >= 1:
                atr_d1 = float(d1["atr"][di - 1]) if np.isfinite(d1["atr"][di - 1]) else None
            elif di >= 1:
                # nearest prior D1
                atr_d1 = float(d1["atr"][di - 1]) if np.isfinite(d1["atr"][di - 1]) else None
            if atr_d1 is None or atr_d1 <= 0:
                continue
            dh, dl = day_hl[sym][day]
            rng = dh - dl
            if rng < ADR_K * atr_d1:
                continue
            funnel["n_eligible"] += 1
            c = float(data[sym]["c"][k])
            mid = 0.5 * (dh + dl)
            # Exhaustion location: close in outer third → fade back to mid
            upper = dl + (2.0 / 3.0) * rng
            lower = dl + (1.0 / 3.0) * rng
            if c >= upper:
                side = -1
            elif c <= lower:
                side = 1
            else:
                continue
            atr_h1 = data[sym]["atr"][k]
            if not np.isfinite(atr_h1) or atr_h1 <= 0:
                continue
            funnel["n_signal"] += 1
            entry = float(data[sym]["o"][idx_map[sym][i]]) if idx_map[sym][i] >= 0 else float(
                data[sym]["o"][k]
            )
            # Prefer next open of this symbol at fire bar
            ii = idx_map[sym][i]
            if ii >= 0:
                entry = float(data[sym]["o"][ii])
            sl = entry - side * ADR_SL * atr_h1
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + side * ADR_RR * risk
            # Soft: tp toward mid is OK but keep RR contract frozen
            picked = {
                "sym": sym,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots(sym, entry, sl),
                "bars": 0,
            }
            break

        if picked is None:
            continue
        open_pos.append(picked)
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def pack_result(hid, setup, symbol, timeframe, pnls, detail):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "setup_type": setup,
        "symbol": symbol,
        "timeframe": timeframe,
        "metrics": m,
        "haircuts": hc,
        "verdict": verdict,
        "fail_notes": notes,
        "detail": detail,
    }


def write_docs(results, receipt, any_surv, beta_fit, qfsi_note: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — CHF-risk + AUD-com3 + ADR greenfield (Round 7)",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast`",
                "Note: Task spawn backend unavailable → lead self-merge same model family.",
                "Parent: Round6 cross-asset/RV ALL_KILL; EUR triad near-miss densify FORBIDDEN.",
                "",
                "## Named classes (≥3)",
                "1. `CHF_FXRISK_BASKET_RESID_FADE` — rank 4.5",
                "2. `AUD_COM3_BASKET_RESID_MR` — rank 4.5",
                "3. `FX3_H1_ADR_EXHAUST_FADE` — rank 3.5",
                "4. W1 HL-break sleeve — **PARKED** (Weekly-HL killboard + N/tpw risk)",
                "5. M15 thick-stop non-SB — **PARKED** (cost GAP + SB densify contamination)",
                "",
                "## Top 3 selected",
                "- USDCHF H1 × FX risk-basket frozen-β residual fade",
                "- AUD commodity ternary (AUD vs NZD+CAD) residual MR",
                "- FX3 H1 D1-ADR exhaustion fade",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — CHF risk + commodity ternary ≠ H4 path / triad identity |",
                "| Quant | SOFT — residual/exhaust edges often cost-killed; ADR cadence risk |",
                "| MQL5/MT5 | PASS — closed-bar; FX-only risk (no NAS densify); no Model 0 yet |",
                "",
                "Unpark W1/M15: **NO**.",
                "Model 0: **WITHHELD** until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — CHF-risk + AUD-com3 + ADR greenfield (Round 7)",
                "",
                "Date: 2026-07-15",
                "Parent: Round6 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.",
                "",
                "## Why",
                "- Outside Round6 parity / NAS equity-β / metal-ratio densify.",
                "- Outside FX3 H4 R1–R5 path saturation.",
                "- W1 / M15 remain parked (de-dup not clear).",
                "",
                "## 1 `HYP-USDCHF-H1-FXRISK-BASKET-RESID-FADE-001`",
                "risk_on=mean(r_EURUSD,r_GBPUSD,−r_USDJPY);",
                f"Frozen β {beta_fit['window']} (α={beta_fit['alpha']:.6g}, "
                f"β={beta_fit['beta']:.6g}, n={beta_fit['n_fit']}, R²={beta_fit['r2']}).",
                f"resid z_lb={CHF_Z_LB}; |z|≥{CHF_Z_ENTRY}; fire UTC{CHF_FIRE_UTC};",
                f"fade USDCHF; SL={CHF_SL} ATR RR={CHF_RR} hold≤{CHF_HOLD}; 1/day.",
                "FX-only risk basket — **not** NAS100 equity-β densify.",
                "",
                "## 2 `HYP-AUD-COM3-H1-BASKET-RESID-MR-001`",
                "spread=ln(AUDUSD)−0.5ln(NZDUSD)−0.5ln(1/USDCAD);",
                f"z_lb={COM_Z_LB}; |z|≥{COM_Z_ENTRY}; fire UTC{COM_FIRE_UTC};",
                f"fade AUDUSD; SL={COM_SL} ATR RR={COM_RR} hold≤{COM_HOLD}; 1/day.",
                "Ternary commodity FX — **not** AUDNZD 2-leg ZMR / AONIA/CORRA.",
                "",
                "## 3 `HYP-FX3-H1-ADR-EXHAUST-FADE-001`",
                f"By UTC{ADR_FIRE_UTC}: day range ≥ {ADR_K}×ATR_D1(prior) and close in outer third;",
                f"fade first eligible of EURUSD→GBPUSD→USDJPY; SL={ADR_SL} ATR_H1 "
                f"RR={ADR_RR} hold≤{ADR_HOLD}; 1/day book.",
                "≠ thin3 jump / consec3 / H4 path / weekend-gap.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No triad / NAS β / metal / H4 path densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — CHF-risk + AUD-com3 + ADR greenfield (Round 7)",
                "",
                "| Object | Vs killboard |",
                "|---|---|",
                "| USDCHF FX-risk-basket resid fade | ≠ EUR triad identity parity; ≠ NAS100 equity-β; "
                "≠ XS residual/mom; ≠ USDCHF London-range-break (Wave6); ≠ VIX siblings |",
                "| AUD COM3 basket resid MR | ≠ AUDNZD 2-leg ZMR; ≠ AONIA/CORRA rate-diff; "
                "≠ XAU-XAG ratio; ≠ WTI-USDCAD ToT |",
                "| FX3 H1 ADR exhaust fade | ≠ thin3 jump; ≠ consec3 impulse; ≠ weekend-gap; "
                "≠ FX3 H4 path R1–R5; ≠ D1 volregime break; ≠ Outside/Engulf |",
                "| W1 HL-break | PARKED — Weekly-HL already killboard |",
                "| M15 thick-stop | PARKED — SB densify + cost GAP contamination |",
                "",
                "CLEARED for offline probe (top 3). No densify of cleared killboard knobs.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = [
        "# Offline — CHF-risk + AUD-com3 + ADR greenfield (Round 7)",
        "",
        f"Receipt `{receipt}`",
        f"Generated `{utc_now()}`",
        "Cost a priori +$12; gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.",
        f"CHF beta freeze: α={beta_fit['alpha']:.6g} β={beta_fit['beta']:.6g} "
        f"n={beta_fit['n_fit']} R²={beta_fit['r2']} driver={beta_fit['driver']}.",
        f"QFSI parallel: {qfsi_note}",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['hypothesis_id']}",
            f"- **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
            f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']}",
            f"- detail={json.dumps(r['detail'], default=str)}",
            "",
        ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — CHF-risk + AUD-com3 + ADR greenfield (Round 7)",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do **not** densify CHF β / COM3 z / ADR k / Round6 triad/NAS/metal / "
                "FX3 H4 R1–R5 / W1 / M15-SB.",
                "Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "Login not headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 7 CHF-risk + AUD-com3 + ADR",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                f"- `{status}`",
                "- Greenfield ngoài Round6 densify (cấm tune triad 1.245).",
                "- W1 / M15 vẫn PARKED.",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify CHF β / COM3 z / ADR k / path R1–R5 / triad / NAS / metal.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "- Next: true greenfield ngoài Round7 board **hoặc** research-grade cost.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def rows_from(path):
        if not path.exists():
            return [], ""
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for x in payload["results"]:
            v = "SURVIVOR" if x.get("verdict") == "PROBE_SURVIVOR" else "KILL"
            rows.append(
                f"| `{x['hypothesis_id']}` | {x['metrics']['n']} | {x['metrics']['pf']} | "
                f"{x['metrics']['tpw']} | {x['haircuts']['x1_5']['pf']} | {v} |"
            )
        return rows, payload.get("receipt_sha256", "")

    r6_rows, r6_rcpt = rows_from(PRE / "20260715_GREENFIELD_CROSSASSET_RV_OFFLINE_PROBES.json")

    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D (greenfield R1–R7)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Hard pivot: FX3 H4 path saturated (R1–R5). Round6 RV ALL_KILL "
                "(EUR triad near-miss — **cấm densify**). Round7 = CHF-risk / AUD-com3 / ADR.",
                "Không densify killboard. QFSI song song. Login không headline.",
                "",
                "## Round 1–5 — FX3 H4 path → ALL_KILL (saturated)",
                "## Round 6 — triad + NAS-β + XAU/XAG → ALL_KILL (near-miss triad FORBIDDEN densify)",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *r6_rows,
                f"Receipt `{r6_rcpt}`",
                "",
                f"## Round 7 — CHF-risk + AUD-com3 + ADR → `{status}`",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *[
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
                    f"{'SURVIVOR' if r['verdict'] == 'PROBE_SURVIVOR' else 'KILL'} |"
                    for r in results
                ],
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                f"- {'Có' if any_surv else 'Zero'} Model 0.",
                "- R1–R5 FX3 H4 path = saturated — FORBIDDEN densify.",
                "- Round6 triad near-miss — FORBIDDEN densify z.",
                "- W1 / M15 vẫn PARKED.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next: greenfield ngoài Round7 board **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(results, receipt):
    if REG.exists():
        keep = []
        drop_ids = {r["hypothesis_id"] for r in results}
        for line in REG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                keep.append(line)
                continue
            if (
                obj.get("hypothesis_id") in drop_ids
                and obj.get("lane") == "greenfield_chfrisk_audcom3_20260715"
            ):
                continue
            keep.append(line)
        REG.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "killed"
                        if r["verdict"] != "PROBE_SURVIVOR"
                        else "probe_survivor",
                        "parent_candidate": "post_round6_crossasset_rv_20260715",
                        "feature_family": "greenfield_chfrisk_audcom3_r7",
                        "lane": "greenfield_chfrisk_audcom3_20260715",
                        "setup_type": r["setup_type"],
                        "symbol": r["symbol"],
                        "timeframe": r["timeframe"],
                        "window": "2021.01.01-2025.12.31",
                        "model": "offline_probe_only",
                        "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                        "metrics": {
                            "trades": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "pf_cost_x1_5": r["haircuts"]["x1_5"]["pf"],
                        },
                        "validation": {
                            "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace(
                                "\\", "/"
                            ),
                            "receipt_sha256": receipt,
                            "status": r["verdict"],
                            "fail_notes": r["fail_notes"],
                            "model0": "AUTHORIZED"
                            if r["verdict"] == "PROBE_SURVIVOR"
                            else "WITHHELD",
                        },
                        "verdict": r["verdict"],
                        "reason": ",".join(r["fail_notes"]) or "probe_survivor",
                        "updated_at": "2026-07-15",
                        "cost_grade": "a_priori_usd12",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def patch_hot(results, receipt, any_surv, beta_fit, qfsi_note: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD ROUND7 CHFRISK/AUDCOM3/ADR CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Outside Round6 densify (triad near-miss FORBIDDEN). Nested critic "
        "`cursor-grok-4.5-high-fast` (lead self-merge; Task backend unavailable).",
        f"  CHF β freeze FX-risk-basket: α={beta_fit['alpha']:.6g} "
        f"β={beta_fit['beta']:.6g} n={beta_fit['n_fit']} R²={beta_fit['r2']}.",
        "  W1 HL-break + M15 thick-stop remain **PARKED**. Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_CHFRISK_AUDCOM3_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_CHFRISK_AUDCOM3_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`;",
        "  panel `readouts/20260715_GREENFIELD_CHFRISK_AUDCOM3_3CRITIC_PANEL.md`.",
        f"  QFSI parallel: {qfsi_note}",
        "  Do **not** densify CHF β / COM3 z / ADR k / triad / NAS β / metal /",
        "  FX3 H4 R1–R5 / XS / AUDNZD / AONIA/CORRA/thin3/exit/FRED/LNY/W1/M15-SB.",
        "  Next: next true greenfield outside Round7 board — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round7 CHF-risk/AUD-com3/ADR "
            f"{status.split('__')[0]}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if "GREENFIELD ROUND7 CHFRISK/AUDCOM3/ADR CLOSEOUT" in ln:
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("- **") or (
                    nxt.startswith("## ") and "Active Truth" not in nxt
                ):
                    break
                if nxt.strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith(
                    "- **"
                ):
                    i += 1
                    break
                i += 1
            continue
        cleaned.append(ln)
        i += 1
    lines = cleaned
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def qfsi_parallel_note() -> str:
    prog = (
        ROOT
        / "02. AlphaFactory"
        / "evidence"
        / "execution"
        / "FivePercentOnline-Real"
        / "20260715_QFSI_REAL_007_LONG_ACCUMULATE"
        / "capture_progress.json"
    )
    if not prog.exists():
        return "007 dir missing — cost GAP unchanged; not headline."
    try:
        p = json.loads(prog.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "007 progress unreadable — cost GAP unchanged."
    hb = p.get("heartbeat_rows")
    qr = p.get("quote_rows")
    dl = p.get("deadline_utc")
    return (
        f"007 accumulate hb={hb} quotes={qr} deadline={dl}; "
        "cost freeze still GAP; login not headline."
    )


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        qnote = qfsi_parallel_note()
        # Freeze window loads
        chf_pre = enrich(load("USDCHF", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO))
        eu_pre = enrich(load("EURUSD", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO))
        gu_pre = enrich(load("GBPUSD", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO))
        uj_pre = enrich(load("USDJPY", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO))
        beta_fit = fit_chf_fxrisk_beta(chf_pre, eu_pre, gu_pre, uj_pre)

        data = {
            "USDCHF": enrich(load("USDCHF", mt5.TIMEFRAME_H1)),
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_H1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_H1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_H1)),
            "AUDUSD": enrich(load("AUDUSD", mt5.TIMEFRAME_H1)),
            "NZDUSD": enrich(load("NZDUSD", mt5.TIMEFRAME_H1)),
            "USDCAD": enrich(load("USDCAD", mt5.TIMEFRAME_H1)),
        }

        results = []
        p1, d1 = probe_chf_fxrisk_resid(data, beta_fit)
        results.append(
            pack_result(
                "HYP-USDCHF-H1-FXRISK-BASKET-RESID-FADE-001",
                "chf_fxrisk_basket_resid_fade",
                "USDCHF",
                "H1",
                p1,
                d1,
            )
        )
        p2, d2 = probe_aud_com3(data)
        results.append(
            pack_result(
                "HYP-AUD-COM3-H1-BASKET-RESID-MR-001",
                "aud_com3_basket_resid_mr",
                "AUDUSD",
                "H1",
                p2,
                d2,
            )
        )
        p3, d3 = probe_fx3_adr_exhaust(data)
        results.append(
            pack_result(
                "HYP-FX3-H1-ADR-EXHAUST-FADE-001",
                "fx3_h1_adr_exhaust_fade",
                "FX3",
                "H1",
                p3,
                d3,
            )
        )

        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_chfrisk_audcom3_r7.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "beta_fit": beta_fit,
            "params": {
                "chf": {
                    "z_lb": CHF_Z_LB,
                    "z_entry": CHF_Z_ENTRY,
                    "sl": CHF_SL,
                    "rr": CHF_RR,
                    "hold": CHF_HOLD,
                    "fire_utc": CHF_FIRE_UTC,
                },
                "com3": {
                    "z_lb": COM_Z_LB,
                    "z_entry": COM_Z_ENTRY,
                    "sl": COM_SL,
                    "rr": COM_RR,
                    "hold": COM_HOLD,
                    "fire_utc": COM_FIRE_UTC,
                },
                "adr": {
                    "k": ADR_K,
                    "sl": ADR_SL,
                    "rr": ADR_RR,
                    "hold": ADR_HOLD,
                    "fire_utc": ADR_FIRE_UTC,
                },
            },
            "parked": ["W1_HL_break", "M15_thick_stop_non_SB"],
            "qfsi_parallel": qnote,
            "results": results,
            "any_probe_survivor": any_surv,
            "model0": "AUTHORIZED_IF_SURVIVOR" if any_surv else "WITHHELD",
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        write_docs(results, receipt, any_surv, beta_fit, qnote)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, beta_fit, qnote)
        print(json.dumps({"receipt": receipt, "any_surv": any_surv, "results": [
            {
                "id": r["hypothesis_id"],
                "verdict": r["verdict"],
                "n": r["metrics"]["n"],
                "pf": r["metrics"]["pf"],
                "tpw": r["metrics"]["tpw"],
                "x1_5": r["haircuts"]["x1_5"]["pf"],
                "notes": r["fail_notes"],
            }
            for r in results
        ], "qfsi": qnote}, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
