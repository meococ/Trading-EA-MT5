#!/usr/bin/env python3
"""Round 8 greenfield — outside unpark + R1–R7 + triad/NAS/metal + carry/exit.

FORBIDDEN densify:
  ≠ Unpark W1/M15 (HL-break / range-exp / inside)
  ≠ FX3 H4 majority/TS/spring/PB/solo/accept/disp/ER/split/halfback (R1–R5)
  ≠ EUR triad parity z / NAS β / XAU-XAG ratio (Round6)
  ≠ CHF FX-risk basket / AUD COM3 / ADR exhaust (Round7)
  ≠ XS residual/mom · AUDNZD ZMR · XAU USD-beta · AONIA/CORRA/thin3
  ≠ carry/anticarry · D1 vol-regime · LNY · FRED · WTI/Brent
  ≠ Weekly-HL · VWAP · NR7/ORB · SB/M15 densify · exit-RR2 · TOM/weekend-gap

A priori (≥3 named; probe top 3), +$12 joint, Model 0 only if PROBE_SURVIVOR:
  1) HYP-EURJPY-H1-USDJPY-BETA-RESID-FADE-001
  2) HYP-EURGBP-H1-CORR-BREAK-RECOUPLE-001
  3) HYP-FX3-H1-PARKINSON-COMPRESS-EXPAND-CONT-001

Nested critic: cursor-grok-4.5-high-fast
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

OUT_JSON = PRE / "20260715_GREENFIELD_CORR_YENX_PARK_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_CORR_YENX_PARK_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_CORR_YENX_PARK_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_CORR_YENX_PARK_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_CORR_YENX_PARK_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_CORR_YENX_PARK_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_CORR_YENX_PARK_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
BETA_FROM = datetime(2019, 1, 1)
BETA_TO = datetime(2020, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- 1 EURJPY × USDJPY frozen-β residual fade ---
YEN_Z_LB = 60
YEN_Z_ENTRY = 1.75
YEN_SL = 1.2
YEN_RR = 2.0
YEN_HOLD = 24
YEN_FIRE_UTC = 12
YEN_MAX_PER_DAY = 1

# --- 2 EURUSD–GBPUSD corr-break recouple fade ---
CORR_LB = 48
CORR_ENTRY = 0.35
DIV_LB = 12
DIV_ATR = 1.5
CORR_SL = 1.2
CORR_RR = 2.0
CORR_HOLD = 24
CORR_FIRE_UTC = 13
CORR_MAX_PER_DAY = 1

# --- 3 FX3 Parkinson compress → expand continuation ---
PK_WIN = 12
PK_COMPRESS_PCT = 0.25
PK_COMPRESS_BARS = 6
PK_EXPAND_K = 1.20
PK_SL = 1.2
PK_RR = 2.0
PK_HOLD = 16
PK_FIRE_UTC = 8
PK_MAX_PER_DAY = 1
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
    # Parkinson per-bar RV proxy (closed-bar HL)
    hl = np.log(np.maximum(d["h"] / np.maximum(d["l"], 1e-12), 1.0 + 1e-12))
    d["pk"] = math.sqrt(1.0 / (4.0 * math.log(2.0))) * hl
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


def fit_yen_cross_beta(ej_pre, uj_pre):
    """OLS: r_EURJPY = α + β * r_USDJPY on freeze window."""
    clock = ej_pre["t"]
    iu = align_on(clock, uj_pre)
    y = []
    x = []
    for i in range(1, len(clock)):
        if min(iu[i], iu[i - 1]) < 0:
            continue
        if uj_pre["t"][iu[i]] != clock[i] or uj_pre["t"][iu[i - 1]] != clock[i - 1]:
            continue
        rj = logret(ej_pre["c"][i - 1], ej_pre["c"][i])
        ru = logret(uj_pre["c"][iu[i - 1]], uj_pre["c"][iu[i]])
        if None in (rj, ru):
            continue
        y.append(rj)
        x.append(ru)
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if len(y) < 200:
        raise RuntimeError(f"Yen beta freeze sample too small: {len(y)}")
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
        "driver": "USDJPY_H1_logret",
        "dependent": "EURJPY_H1_logret",
    }


def probe_yen_cross_resid(data, beta_fit):
    closed = []
    open_pos = []
    ej = data["EURJPY"]
    uj = data["USDJPY"]
    clock = ej["t"]
    iu = align_on(clock, uj)
    resid = np.full(len(clock), np.nan, dtype=float)
    for i in range(1, len(clock)):
        if min(iu[i], iu[i - 1]) < 0:
            continue
        if uj["t"][iu[i]] != clock[i] or uj["t"][iu[i - 1]] != clock[i - 1]:
            continue
        rj = logret(ej["c"][i - 1], ej["c"][i])
        ru = logret(uj["c"][iu[i - 1]], uj["c"][iu[i]])
        if None in (rj, ru):
            continue
        resid[i] = rj - (beta_fit["alpha"] + beta_fit["beta"] * ru)
    z = rolling_z(resid, YEN_Z_LB)
    last_day = None
    day_count = 0
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, data, ts, closed, YEN_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day = day
            day_count = 0
        if dt.weekday() >= 5:
            continue
        if dt.hour != YEN_FIRE_UTC:
            continue
        if day_count >= YEN_MAX_PER_DAY:
            continue
        if open_pos:
            continue
        zi = z[i]
        atr = ej["atr"][i]
        if not np.isfinite(zi) or not np.isfinite(atr) or atr <= 0:
            continue
        if abs(zi) < YEN_Z_ENTRY:
            continue
        # Fade residual: +z → short EURJPY; -z → long
        side = -1 if zi > 0 else 1
        entry_i = i + 1
        if entry_i >= len(clock):
            continue
        entry = float(ej["o"][entry_i])
        sl = entry - side * YEN_SL * atr
        tp = entry + side * YEN_RR * YEN_SL * atr
        lots = risk_lots("EURJPY", entry, sl)
        open_pos.append(
            {
                "sym": "EURJPY",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        day_count += 1
    flush_open(open_pos, data, closed)
    return summarize(closed)


def rolling_corr(a: np.ndarray, b: np.ndarray, lb: int) -> np.ndarray:
    out = np.full(len(a), np.nan, dtype=float)
    for i in range(lb, len(a)):
        wa = a[i - lb + 1 : i + 1]
        wb = b[i - lb + 1 : i + 1]
        if not (np.all(np.isfinite(wa)) and np.all(np.isfinite(wb))):
            continue
        if np.std(wa) < 1e-12 or np.std(wb) < 1e-12:
            continue
        out[i] = float(np.corrcoef(wa, wb)[0, 1])
    return out


def probe_corr_recouple(data):
    """Fade the stronger USD-leg when EURUSD–GBPUSD corr collapses + divergence large."""
    closed = []
    open_pos = []
    eu = data["EURUSD"]
    gu = data["GBPUSD"]
    clock = eu["t"]
    ig = align_on(clock, gu)
    reu = np.full(len(clock), np.nan, dtype=float)
    rgu = np.full(len(clock), np.nan, dtype=float)
    for i in range(1, len(clock)):
        if ig[i] < 0 or ig[i - 1] < 0:
            continue
        if gu["t"][ig[i]] != clock[i] or gu["t"][ig[i - 1]] != clock[i - 1]:
            continue
        re = logret(eu["c"][i - 1], eu["c"][i])
        rg = logret(gu["c"][ig[i - 1]], gu["c"][ig[i]])
        if None in (re, rg):
            continue
        reu[i] = re
        rgu[i] = rg
    corr = rolling_corr(reu, rgu, CORR_LB)
    last_day = None
    day_count = 0
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {"EURUSD": eu, "GBPUSD": gu}, ts, closed, CORR_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day = day
            day_count = 0
        if dt.weekday() >= 5:
            continue
        if dt.hour != CORR_FIRE_UTC:
            continue
        if day_count >= CORR_MAX_PER_DAY:
            continue
        if open_pos:
            continue
        if ig[i] < 0 or gu["t"][ig[i]] != clock[i]:
            continue
        ci = corr[i]
        if not np.isfinite(ci) or ci >= CORR_ENTRY:
            continue
        if i < DIV_LB:
            continue
        # Cum logret over DIV_LB on both legs
        if not (
            np.all(np.isfinite(reu[i - DIV_LB + 1 : i + 1]))
            and np.all(np.isfinite(rgu[i - DIV_LB + 1 : i + 1]))
        ):
            continue
        ce = float(np.sum(reu[i - DIV_LB + 1 : i + 1]))
        cg = float(np.sum(rgu[i - DIV_LB + 1 : i + 1]))
        atr_e = eu["atr"][i]
        atr_g = gu["atr"][ig[i]]
        if not np.isfinite(atr_e) or not np.isfinite(atr_g) or atr_e <= 0 or atr_g <= 0:
            continue
        # Divergence in ATR units of each leg
        de = abs(ce) / (atr_e / eu["c"][i]) if eu["c"][i] > 0 else 0.0
        dg = abs(cg) / (atr_g / gu["c"][ig[i]]) if gu["c"][ig[i]] > 0 else 0.0
        if max(de, dg) < DIV_ATR:
            continue
        # Fade stronger mover (expect recouple toward weaker)
        if abs(ce) >= abs(cg):
            sym, side, atr = "EURUSD", (-1 if ce > 0 else 1), atr_e
            d_trade = eu
            entry_i = i + 1
        else:
            sym, side, atr = "GBPUSD", (-1 if cg > 0 else 1), atr_g
            d_trade = gu
            entry_i = int(ig[i]) + 1
            if entry_i >= len(gu["t"]):
                continue
        if sym == "EURUSD":
            if entry_i >= len(eu["t"]):
                continue
            entry = float(eu["o"][entry_i])
        else:
            entry = float(gu["o"][entry_i])
        sl = entry - side * CORR_SL * atr
        tp = entry + side * CORR_RR * CORR_SL * atr
        lots = risk_lots(sym, entry, sl)
        open_pos.append(
            {
                "sym": sym,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        day_count += 1
        _ = d_trade  # silence lint
    flush_open(open_pos, {"EURUSD": eu, "GBPUSD": gu}, closed)
    return summarize(closed)


def probe_parkinson_expand(data):
    """After Parkinson compress streak, trade expansion-bar continuation on FX3."""
    closed = []
    open_pos = []
    # Precompute per-symbol pk mean and percentile rank
    pk_mean = {}
    pk_rank = {}
    for sym in FX3:
        d = data[sym]
        pk = d["pk"]
        m = np.full(len(pk), np.nan, dtype=float)
        for i in range(PK_WIN - 1, len(pk)):
            w = pk[i - PK_WIN + 1 : i + 1]
            if np.all(np.isfinite(w)):
                m[i] = float(np.mean(w))
        # Rolling percentile of pk_mean vs prior 100 bars
        rank = np.full(len(m), np.nan, dtype=float)
        lb = 100
        for i in range(lb, len(m)):
            hist = m[i - lb : i]
            hist = hist[np.isfinite(hist)]
            if len(hist) < 40 or not np.isfinite(m[i]):
                continue
            rank[i] = float(np.mean(hist <= m[i]))
        pk_mean[sym] = m
        pk_rank[sym] = rank

    # Shared clock = EURUSD
    clock = data["EURUSD"]["t"]
    idx_map = {s: align_on(clock, data[s]) for s in FX3}
    last_day = None
    day_count = 0
    compress_streak = {s: 0 for s in FX3}

    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, PK_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day = day
            day_count = 0
        if dt.weekday() >= 5:
            continue

        # Update compress streaks on all symbols at this clock
        for sym in FX3:
            j = int(idx_map[sym][i])
            if j < 0 or data[sym]["t"][j] != ts:
                continue
            r = pk_rank[sym][j]
            if np.isfinite(r) and r <= PK_COMPRESS_PCT:
                compress_streak[sym] += 1
            else:
                compress_streak[sym] = 0

        if dt.hour != PK_FIRE_UTC:
            continue
        if day_count >= PK_MAX_PER_DAY:
            continue
        if open_pos:
            continue

        # First eligible FX3 with compress streak + expansion bar
        for sym in FX3:
            j = int(idx_map[sym][i])
            if j < 0 or data[sym]["t"][j] != ts:
                continue
            if compress_streak[sym] < PK_COMPRESS_BARS:
                continue
            d = data[sym]
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            bar_range = d["h"][j] - d["l"][j]
            if bar_range < PK_EXPAND_K * atr:
                continue
            # Continuation in close direction vs open
            if d["c"][j] > d["o"][j]:
                side = 1
            elif d["c"][j] < d["o"][j]:
                side = -1
            else:
                continue
            entry_i = j + 1
            if entry_i >= len(d["t"]):
                continue
            entry = float(d["o"][entry_i])
            sl = entry - side * PK_SL * atr
            tp = entry + side * PK_RR * PK_SL * atr
            lots = risk_lots(sym, entry, sl)
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": lots,
                    "bars": 0,
                }
            )
            day_count += 1
            # Reset streak after fire to avoid re-entry spam
            compress_streak[sym] = 0
            break
    flush_open(open_pos, {s: data[s] for s in FX3}, closed)
    return summarize(closed)


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


def append_reg(results, receipt):
    stamp = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "parent_candidate": "Round8_corr_yenx_parkinson_greenfield",
                "feature_family": r["setup_type"],
                "lane": "unlimited_goal_greenfield_r8",
                "setup_type": r["setup_type"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "source_provenance": (
                    "Round8 true greenfield outside unpark+R1-R7; "
                    f"receipt {receipt}; nested cursor-grok-4.5-high-fast"
                ),
                "prereg_path": None,
                "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "metrics": r["metrics"],
                "validation": {
                    "cost_stress_apriori_usd": BASE_COST,
                    "haircuts": r["haircuts"],
                    "verdict": r["verdict"],
                    "fail_notes": r["fail_notes"],
                    "receipt_sha256": receipt,
                },
                "verdict": r["verdict"],
                "updated_at": stamp,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results, receipt, any_surv, beta_fit, qfsi_note: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    def row(r):
        return (
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
            f"{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE', 'KILL')} |"
        )

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — Round 8 TRUE greenfield (corr / yen-β / Parkinson)",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast`",
                "Parent: Unpark W1/M15 + R6–R7 OFFLINE_ALL_KILL; outside forbidden densify.",
                "",
                "## Named classes (≥3)",
                "1. `EURJPY_USDJPY_BETA_RESID_FADE` — rank 1 (cleanest orthogonal vs R6–R7)",
                "2. `EURGBP_CORR_BREAK_RECOUPLE` — rank 2 (mechanism ≠ triad parity-z)",
                "3. `FX3_PARKINSON_COMPRESS_EXPAND_CONT` — rank 3 (NR7 adjacency watch)",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — yen-cross RV + corr-recouple ≠ H4 path / triad identity / NAS β |",
                "| Quant | SOFT — residual template fatigue; Parkinson cadence-heavy cost risk |",
                "| MQL5/MT5 | PASS — closed-bar; frozen-β OLS; next-open; no Model 0 yet |",
                "",
                "INTAKE_KILL: none hard.",
                "Model 0: **WITHHELD** until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 8 corr / yen-cross / Parkinson greenfield",
                "",
                "Date: 2026-07-15",
                "Parent: Unpark + R1–R7 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.",
                "",
                "## Why these could break thick∩cadence",
                "- **Yen-cross β-resid:** H1 |z| can print 2–5 tpw while EURJPY decoupling",
                "  from USDJPY is a distinct yen-risk RV (not equity NAS-β, not CHF basket).",
                "  Thickness: RR=2 fade after structural residual extremes.",
                "- **Corr-break recouple:** Policy/risk de-link episodes are quality events",
                "  (thick PF potential) that still recur on H1 without needing H4 path spam.",
                "  Mechanism = rolling corr + divergence — **not** EURGBP parity residual z.",
                "- **Parkinson compress→expand:** Cadence-friendly expansion after true",
                "  HL-RV squeeze; edge only if squeeze filters continuation better than",
                "  raw TSMOM/ER (which died post-cost).",
                "",
                f"## 1 `HYP-EURJPY-H1-USDJPY-BETA-RESID-FADE-001`",
                f"Frozen β {beta_fit['window']} (α={beta_fit['alpha']:.6g}, "
                f"β={beta_fit['beta']:.6g}, n={beta_fit['n_fit']}, R²={beta_fit['r2']}).",
                f"resid z_lb={YEN_Z_LB}; |z|≥{YEN_Z_ENTRY}; fire UTC{YEN_FIRE_UTC};",
                f"fade EURJPY; SL={YEN_SL} ATR RR={YEN_RR} hold≤{YEN_HOLD}; 1/day.",
                "Yen-cross FX RV — **not** NAS100 equity-β densify / CHF risk-basket densify.",
                "",
                f"## 2 `HYP-EURGBP-H1-CORR-BREAK-RECOUPLE-001`",
                f"corr_lb={CORR_LB}; corr<{CORR_ENTRY}; |div|_{DIV_LB}≥{DIV_ATR} ATR;",
                f"fade stronger USD-leg (EURUSD or GBPUSD); fire UTC{CORR_FIRE_UTC};",
                f"SL={CORR_SL} ATR RR={CORR_RR} hold≤{CORR_HOLD}; 1/day.",
                "≠ Round6 triad parity-z on EURGBP; ≠ LNY EUR-lead catchup.",
                "",
                f"## 3 `HYP-FX3-H1-PARKINSON-COMPRESS-EXPAND-CONT-001`",
                f"Parkinson mean{PK_WIN} ≤ p{int(PK_COMPRESS_PCT*100)} for ≥{PK_COMPRESS_BARS} bars;",
                f"then bar range ≥{PK_EXPAND_K}×ATR → continue; fire UTC{PK_FIRE_UTC};",
                f"FX3 first-eligible; SL={PK_SL} ATR RR={PK_RR} hold≤{PK_HOLD}; 1/day.",
                "≠ NR7 single-bar densify; ≠ R7 ADR exhaust fade; ≠ D1 volregime.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No unpark/R1–R7 densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 8 corr / yen-cross / Parkinson",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| EURJPY×USDJPY β-resid fade | ≠ NAS100→USDJPY equity-β (R6); ≠ CHF FX-risk basket (R7); "
                "≠ XAU USD-β; ≠ XS residual book; ≠ FX3 H4 path R1–R5 |",
                "| EUR/GBP corr-break recouple | ≠ EUR triad parity residual z (R6 near-miss); "
                "≠ LNY EURUSD-lead GBP catchup; ≠ XS mom; ≠ H4 path |",
                "| FX3 Parkinson compress-expand | ≠ NR7/ORB/SB/M15 densify (object=Parkinson RV streak+expand); "
                "≠ ADR exhaust fade (R7); ≠ D1 ATR14/50 volregime; ≠ thin3; ≠ TSMOM/ER path |",
                "",
                "Unpark W1/M15 / Round6–7 boards: **FORBIDDEN densify** — not reopened.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    table = [
        "| Object | N | PF | tpw | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ] + [row(r) for r in results]

    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 8 corr / yen-cross / Parkinson",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Status: `{status}`",
                f"Cost a priori: +${BASE_COST:.0f}/trade",
                f"QFSI parallel: {qfsi_note}",
                "",
                *table,
                "",
                "## Fail notes",
                *[f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}" for r in results],
                "",
                f"## Beta freeze (EURJPY ~ USDJPY)",
                f"- α={beta_fit['alpha']:.6g} β={beta_fit['beta']:.6g} "
                f"n={beta_fit['n_fit']} R²={beta_fit['r2']}",
                "",
                "## Model 0",
                "AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — Round 8 corr / yen-cross / Parkinson",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify corr threshold / yen β z / Parkinson pct /",
                "unpark W1/M15 / R1–R7 / triad / NAS / metal / carry / exit.",
                "Next: next true greenfield outside Round8 board — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 8 greenfield (corr / yen-cross / Parkinson)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Bề mặt **ngoài** unpark W1/M15 + R1–R7 + triad/NAS/metal + carry/exit.",
                "Nested critic `cursor-grok-4.5-high-fast`. Model 0 chỉ nếu PROBE_SURVIVOR.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Vì sao có thể phá thick∩cadence",
                "- Yen-cross β-resid: cadence H1 |z| + thickness RR2 trên RV khác NAS/CHF.",
                "- Corr-break recouple: episode chất lượng (thick) nhưng vẫn tái diễn H1.",
                "- Parkinson expand: cadence cao; chỉ sống nếu squeeze lọc được continuation.",
                "",
                "## Quyết định",
                "- Không densify corr/yen-z/Parkinson-pct / killboard trước đó.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài Round8 **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Append Round8 block to session VN (rewrite head summary)
    session_body = "\n".join(
        [
            "# VN brief — continue R&D (greenfield R1–R8)",
            "",
            f"Thời điểm: 2026-07-15 ~{stamp} ICT",
            "Hard pivot: FX3 H4 path saturated (R1–R5). Round6–7 + Unpark ALL_KILL.",
            "Round8 = corr-recouple / yen-cross β / Parkinson — ngoài killboard.",
            "Không densify killboard. QFSI song song. Login không headline.",
            "",
            "## Round 8 — corr + yen-cross + Parkinson → "
            + ("SURVIVOR" if any_surv else "ALL_KILL"),
            *table,
            f"Receipt `{receipt}`",
            "**Cấm densify** corr threshold / yen β z / Parkinson pct.",
            "",
            "## Round 1–5 — FX3 H4 path → ALL_KILL (saturated)",
            "## Round 6 — triad + NAS-β + XAU/XAG → ALL_KILL (near-miss triad FORBIDDEN densify)",
            "## Round 7 — CHF-risk + AUD-com3 + ADR → ALL_KILL",
            "## Unpark W1/M15 → ALL_KILL (cấm densify range-k / W1 / inside)",
            "",
            "## Quyết định",
            "- Zero Model 0." if not any_surv else "- Model 0 only for PROBE_SURVIVOR.",
            "- R1–R8 boards FORBIDDEN densify.",
            "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
            "- Next: greenfield ngoài Round8 board **hoặc** research-grade cost.",
            "",
            "Login không headline. GOAL unmet.",
            "",
        ]
    )
    OUT_SESSION_VN.write_text(session_body, encoding="utf-8")


def patch_hot(results, receipt, any_surv, beta_fit, qnote: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines_r = []
    for i, r in enumerate(results, 1):
        m, hc = r["metrics"], r["haircuts"]
        lines_r.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} x1.5={hc['x1_5']['pf']})."
        )
    block = [
        "",
        f"- **GREENFIELD ROUND8 CORR/YENX/PARK CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Outside unpark + R1–R7 densify. Nested critic `cursor-grok-4.5-high-fast`.",
        f"  Yen-cross β freeze EURJPY~USDJPY: α={beta_fit['alpha']:.6g} "
        f"β={beta_fit['beta']:.6g} n={beta_fit['n_fit']} R²={beta_fit['r2']}.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_CORR_YENX_PARK_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_CORR_YENX_PARK_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`;",
        "  panel `readouts/20260715_GREENFIELD_CORR_YENX_PARK_3CRITIC_PANEL.md`.",
        f"  QFSI parallel: {qnote}",
        "  Do **not** densify corr threshold / yen β z / Parkinson pct /",
        "  unpark W1/M15 / R1–R7 / triad / NAS / metal / FX3 H4 path /",
        "  carry / exit / AONIA/CORRA/thin3/FRED/LNY/XS.",
        "  Next: next true greenfield outside Round8 board — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    # Update header
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round8 CORR/YENX/PARK "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    # Insert after ## Active Truth
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        # Drop prior Round8 block if re-run
        if ln.startswith("- **GREENFIELD ROUND8 CORR/YENX/PARK CLOSEOUT"):
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
        ej_pre = enrich(load("EURJPY", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO))
        uj_pre = enrich(load("USDJPY", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO))
        beta_fit = fit_yen_cross_beta(ej_pre, uj_pre)

        data = {
            "EURJPY": enrich(load("EURJPY", mt5.TIMEFRAME_H1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_H1)),
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_H1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_H1)),
        }

        results = []
        p1, d1 = probe_yen_cross_resid(data, beta_fit)
        results.append(
            pack_result(
                "HYP-EURJPY-H1-USDJPY-BETA-RESID-FADE-001",
                "eurjpy_usdjpy_beta_resid_fade",
                "EURJPY",
                "H1",
                p1,
                d1,
            )
        )
        p2, d2 = probe_corr_recouple(data)
        results.append(
            pack_result(
                "HYP-EURGBP-H1-CORR-BREAK-RECOUPLE-001",
                "eurgbp_corr_break_recouple_fade",
                "EURUSD+GBPUSD",
                "H1",
                p2,
                d2,
            )
        )
        p3, d3 = probe_parkinson_expand(data)
        results.append(
            pack_result(
                "HYP-FX3-H1-PARKINSON-COMPRESS-EXPAND-CONT-001",
                "fx3_h1_parkinson_compress_expand_cont",
                "FX3",
                "H1",
                p3,
                d3,
            )
        )

        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_corr_yenx_park_r8.v1",
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
                "yen": {
                    "z_lb": YEN_Z_LB,
                    "z_entry": YEN_Z_ENTRY,
                    "sl": YEN_SL,
                    "rr": YEN_RR,
                    "hold": YEN_HOLD,
                    "fire_utc": YEN_FIRE_UTC,
                },
                "corr": {
                    "corr_lb": CORR_LB,
                    "corr_entry": CORR_ENTRY,
                    "div_lb": DIV_LB,
                    "div_atr": DIV_ATR,
                    "sl": CORR_SL,
                    "rr": CORR_RR,
                    "hold": CORR_HOLD,
                    "fire_utc": CORR_FIRE_UTC,
                },
                "parkinson": {
                    "win": PK_WIN,
                    "compress_pct": PK_COMPRESS_PCT,
                    "compress_bars": PK_COMPRESS_BARS,
                    "expand_k": PK_EXPAND_K,
                    "sl": PK_SL,
                    "rr": PK_RR,
                    "hold": PK_HOLD,
                    "fire_utc": PK_FIRE_UTC,
                },
            },
            "forbidden_densify": [
                "unpark_W1_M15",
                "FX3_H4_path_R1_R5",
                "triad_parity_z",
                "NAS_beta",
                "metal_ratio",
                "CHF_fxrisk",
                "AUD_COM3",
                "ADR_exhaust",
                "carry_exit_packs",
            ],
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
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_surv": any_surv,
                    "beta_fit": beta_fit,
                    "results": [
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
                    ],
                    "qfsi": qnote,
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
