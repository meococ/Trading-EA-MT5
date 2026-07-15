#!/usr/bin/env python3
"""Round 6 greenfield — TRUE different surfaces after FX3 H4 R1–R5 saturation.

FORBIDDEN densify:
  ≠ FX3 H4 majority/TS/spring/PB/solo/accept/disp/ER/split/halfback
  ≠ XS residual/mom · AUDNZD ZMR · XAU USD-beta · AONIA/CORRA/thin3
  ≠ carry/anticarry · D1 vol-regime/ADX swing · LNY · FRED displace · VIX siblings

A priori (≥3 named; probe top 3), +$12 joint, Model 0 only if PROBE_SURVIVOR:
  1) HYP-EUR-TRIAD-H1-PARITY-RESID-MR-001
  2) HYP-USDJPY-H1-NAS100-BETA-RESID-FADE-001
  3) HYP-XAU-XAG-H1-RATIO-ZMR-001

Nested critic: cursor-grok-4.5-high-fast
Panel: Sonic trader / quant validation / MQL5 systems

Engineering note: rolling_z uses last lb *finite* observations (equity H1
gaps break contiguous lb=60 on FX clock). Not a threshold densify.
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

OUT_JSON = PRE / "20260715_GREENFIELD_CROSSASSET_RV_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_CROSSASSET_RV_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_CROSSASSET_RV_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_CROSSASSET_RV_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_CROSSASSET_RV_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_CROSSASSET_RV_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_CROSSASSET_RV_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
BETA_FROM = datetime(2019, 1, 1)
BETA_TO = datetime(2020, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- 1 EUR triangular parity residual MR ---
PAR_Z_LB = 48
PAR_Z_ENTRY = 2.0
PAR_SL = 1.5
PAR_RR = 1.5
PAR_HOLD = 24
PAR_FIRE_UTC = None  # any H1; 1/day cap
PAR_MAX_PER_DAY = 1

# --- 2 USDJPY × NAS100 frozen-β residual fade ---
BETA_Z_LB = 60
BETA_Z_ENTRY = 1.75
BETA_SL = 1.2
BETA_RR = 2.0
BETA_HOLD = 24
BETA_FIRE_UTC = 16
BETA_MAX_PER_DAY = 1

# --- 3 XAU–XAG ratio residual MR ---
RATIO_Z_LB = 48
RATIO_Z_ENTRY = 2.0
RATIO_SL = 1.5
RATIO_RR = 1.5
RATIO_HOLD = 36
RATIO_FIRE_UTC = 12
RATIO_MAX_PER_DAY = 1


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
        # if NaN: do not append; z stays NaN at gap bars
    return out


def load(symbol, tf, fr=FROM, to=TO):
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
    """Map clock timestamps -> indices in d; -1 if missing."""
    idx = np.searchsorted(d["t"], clock_t, side="left")
    out = np.full(len(clock_t), -1, dtype=np.int64)
    for i, (j, ts) in enumerate(zip(idx, clock_t)):
        if j < len(d["t"]) and d["t"][j] == ts:
            out[i] = j
    return out


def probe_eur_triad_parity(data):
    """Fade EURGBP vs EURUSD/GBPUSD log-parity residual."""
    closed = []
    eurgbp = data["EURGBP"]
    eurusd = data["EURUSD"]
    gbpusd = data["GBPUSD"]
    clock = eurgbp["t"]
    ie = align_on(clock, eurusd)
    ig = align_on(clock, gbpusd)

    resid = np.full(len(clock), np.nan)
    for i in range(len(clock)):
        if ie[i] < 0 or ig[i] < 0:
            continue
        eg = eurgbp["c"][i]
        eu = eurusd["c"][ie[i]]
        gu = gbpusd["c"][ig[i]]
        if eg <= 0 or eu <= 0 or gu <= 0:
            continue
        synth = eu / gu
        resid[i] = math.log(eg) - math.log(synth)
    z = rolling_z(resid, PAR_Z_LB)

    open_pos = []
    day_count = {}
    funnel = {
        "n_bars": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_open": 0,
        "n_skip_day": 0,
    }
    data_map = {"EURGBP": eurgbp}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data_map, ts, closed, PAR_HOLD)
        j = i - 1
        if j < PAR_Z_LB + 5:
            continue
        if dt.weekday() >= 5:
            continue
        funnel["n_bars"] += 1
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= PAR_MAX_PER_DAY:
            funnel["n_skip_day"] += 1
            continue
        zj = z[j]
        if not np.isfinite(zj) or abs(zj) < PAR_Z_ENTRY:
            continue
        atr = eurgbp["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        funnel["n_signal"] += 1
        # Fade residual: z>0 => EURGBP rich vs synth => short EURGBP
        side = -1 if zj > 0 else 1
        entry = float(eurgbp["o"][i])
        sl = entry - side * PAR_SL * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * PAR_RR * risk
        open_pos.append(
            {
                "sym": "EURGBP",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots("EURGBP", entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data_map, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    detail["resid_finite"] = int(np.isfinite(resid).sum())
    detail["z_finite"] = int(np.isfinite(z).sum())
    return pnls, detail


def fit_frozen_beta(usdjpy_pre, nas_pre):
    """OLS β: r_USDJPY = α + β * r_NAS100 on overlapping H1; freeze α,β."""
    clock = usdjpy_pre["t"]
    inas = align_on(clock, nas_pre)
    rj = []
    rn = []
    for i in range(1, len(clock)):
        if inas[i] < 1 or inas[i - 1] < 0:
            continue
        # require consecutive NAS bars for return
        if nas_pre["t"][inas[i]] != clock[i]:
            continue
        if nas_pre["t"][inas[i] - 1] != clock[i - 1] and inas[i - 1] >= 0:
            # allow if prior NAS index maps to prior clock
            if nas_pre["t"][inas[i - 1]] != clock[i - 1]:
                continue
        c0, c1 = usdjpy_pre["c"][i - 1], usdjpy_pre["c"][i]
        n0, n1 = nas_pre["c"][inas[i - 1]], nas_pre["c"][inas[i]]
        if c0 <= 0 or n0 <= 0:
            continue
        rj.append(math.log(c1 / c0))
        rn.append(math.log(n1 / n0))
    rj = np.asarray(rj, dtype=float)
    rn = np.asarray(rn, dtype=float)
    if len(rj) < 200:
        raise RuntimeError(f"beta freeze sample too small: {len(rj)}")
    # OLS with intercept
    X = np.column_stack([np.ones(len(rn)), rn])
    coef, *_ = np.linalg.lstsq(X, rj, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    yhat = X @ coef
    ss_res = float(np.sum((rj - yhat) ** 2))
    ss_tot = float(np.sum((rj - rj.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {
        "alpha": alpha,
        "beta": beta,
        "n_fit": int(len(rj)),
        "r2": round(r2, 6),
        "window": "2019-01-01..2020-12-31",
        "driver": "NAS100",
    }


def probe_nas100_beta_resid(data, beta_fit):
    """Fade USDJPY residual vs frozen NAS100 beta; lag = closed prior H1 only."""
    closed = []
    jpy = data["USDJPY"]
    nas = data["NAS100"]
    clock = jpy["t"]
    inas = align_on(clock, nas)
    alpha, beta = beta_fit["alpha"], beta_fit["beta"]

    resid = np.full(len(clock), np.nan)
    for i in range(1, len(clock)):
        if inas[i] < 1 or inas[i - 1] < 0:
            continue
        if nas["t"][inas[i]] != clock[i]:
            continue
        if nas["t"][inas[i - 1]] != clock[i - 1]:
            continue
        c0, c1 = jpy["c"][i - 1], jpy["c"][i]
        n0, n1 = nas["c"][inas[i - 1]], nas["c"][inas[i]]
        if c0 <= 0 or n0 <= 0:
            continue
        rj = math.log(c1 / c0)
        rn = math.log(n1 / n0)
        # residual uses same closed bar — decision at next open (i+1) so no lookahead
        resid[i] = rj - (alpha + beta * rn)
    z = rolling_z(resid, BETA_Z_LB)

    open_pos = []
    day_count = {}
    funnel = {
        "n_bars": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_hour": 0,
        "n_skip_open": 0,
    }
    data_map = {"USDJPY": jpy}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data_map, ts, closed, BETA_HOLD)
        j = i - 1
        if j < BETA_Z_LB + 5:
            continue
        if dt.weekday() >= 5:
            continue
        funnel["n_bars"] += 1
        if dt.hour != BETA_FIRE_UTC:
            funnel["n_skip_hour"] += 1
            continue
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= BETA_MAX_PER_DAY:
            continue
        zj = z[j]
        if not np.isfinite(zj) or abs(zj) < BETA_Z_ENTRY:
            continue
        atr = jpy["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        funnel["n_signal"] += 1
        # Fade: z>0 => JPY pair rich vs equity beta => short USDJPY
        side = -1 if zj > 0 else 1
        entry = float(jpy["o"][i])
        sl = entry - side * BETA_SL * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * BETA_RR * risk
        open_pos.append(
            {
                "sym": "USDJPY",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots("USDJPY", entry, sl),
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


def probe_xau_xag_ratio(data):
    """Fade XAGUSD when ln(XAU)-ln(XAG) z extreme."""
    closed = []
    xau = data["XAUUSD"]
    xag = data["XAGUSD"]
    clock = xag["t"]
    ix = align_on(clock, xau)

    spread = np.full(len(clock), np.nan)
    for i in range(len(clock)):
        if ix[i] < 0:
            continue
        a = xau["c"][ix[i]]
        g = xag["c"][i]
        if a <= 0 or g <= 0:
            continue
        spread[i] = math.log(a) - math.log(g)
    z = rolling_z(spread, RATIO_Z_LB)

    open_pos = []
    day_count = {}
    funnel = {
        "n_bars": 0,
        "n_signal": 0,
        "n_trades": 0,
        "n_skip_hour": 0,
        "n_skip_open": 0,
    }
    data_map = {"XAGUSD": xag}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data_map, ts, closed, RATIO_HOLD)
        j = i - 1
        if j < RATIO_Z_LB + 5:
            continue
        if dt.weekday() >= 5:
            continue
        funnel["n_bars"] += 1
        if dt.hour != RATIO_FIRE_UTC:
            funnel["n_skip_hour"] += 1
            continue
        if open_pos:
            funnel["n_skip_open"] += 1
            continue
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= RATIO_MAX_PER_DAY:
            continue
        zj = z[j]
        if not np.isfinite(zj) or abs(zj) < RATIO_Z_ENTRY:
            continue
        atr = xag["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        funnel["n_signal"] += 1
        # z>0 => gold rich vs silver / silver cheap => long XAG to fade ratio
        # Fade ratio: high ln(XAU/XAG) => buy XAG (expect ratio mean-revert down)
        side = 1 if zj > 0 else -1
        entry = float(xag["o"][i])
        sl = entry - side * RATIO_SL * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + side * RATIO_RR * risk
        open_pos.append(
            {
                "sym": "XAGUSD",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots("XAGUSD", entry, sl),
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


def write_docs(results, receipt, any_surv, beta_fit):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — Cross-asset / RV greenfield (Round 6)",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast`",
                "Parent: FX3 H4 R1–R5 OHLC path/cont/fade family **SATURATED** under +$12.",
                "",
                "## Named classes (≥3)",
                "1. `EUR_TRIANGULAR_PARITY_RESIDUAL_MR` — rank 4.5",
                "2. `EQUITY_FX_BETA_RESID_FADE` (NAS100 proxy; US500 missing) — rank 4",
                "3. `XAU_XAG_RATIO_RESIDUAL_MR` — rank 4",
                "4. W1 HL-break sleeve — parked (N/tpw joint-screen risk)",
                "5. M15 thick-stop non-SB — parked (cost + densify contamination)",
                "",
                "## Top 3 selected",
                "- EUR triad H1 parity residual MR",
                "- USDJPY H1 × NAS100 frozen-β residual fade",
                "- XAU–XAG H1 ratio ZMR",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — objects outside H4 path states |",
                "| Quant | SOFT — residual edges often cost-killed; still lawful probe |",
                "| MQL5/MT5 | PASS — closed-bar sync; no tick-cost claim; no Model 0 yet |",
                "",
                "Model 0: **WITHHELD** until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Cross-asset / RV greenfield (Round 6)",
                "",
                "Date: 2026-07-15",
                "Parent: R1–R5 FX3 H4 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.",
                "",
                "## Why (vs saturated FX3 H4 path)",
                "- Change **object + surface**, not retune majority/TS/spring/PB/solo/disp/ER/split/halfback.",
                "- Parity / equity-beta / metal-ratio are identity or cross-asset residuals.",
                "",
                "## 1 `HYP-EUR-TRIAD-H1-PARITY-RESID-MR-001`",
                f"resid=ln(EURGBP)−ln(EURUSD/GBPUSD); z_lb={PAR_Z_LB}; |z|≥{PAR_Z_ENTRY};",
                f"fade EURGBP; SL={PAR_SL} ATR RR={PAR_RR} hold≤{PAR_HOLD}; 1/day; next open.",
                "",
                "## 2 `HYP-USDJPY-H1-NAS100-BETA-RESID-FADE-001`",
                f"Frozen β from {beta_fit['window']} NAS100→USDJPY OLS "
                f"(α={beta_fit['alpha']:.6g}, β={beta_fit['beta']:.6g}, "
                f"n={beta_fit['n_fit']}, R²={beta_fit['r2']}).",
                f"resid z_lb={BETA_Z_LB}; |z|≥{BETA_Z_ENTRY}; fire UTC{BETA_FIRE_UTC};",
                f"fade USDJPY; SL={BETA_SL} ATR RR={BETA_RR} hold≤{BETA_HOLD}.",
                "US500 missing on broker → NAS100 Demo H1 proxy (explicit, not VIX).",
                "",
                "## 3 `HYP-XAU-XAG-H1-RATIO-ZMR-001`",
                f"spread=ln(XAU)−ln(XAG); z_lb={RATIO_Z_LB}; |z|≥{RATIO_Z_ENTRY};",
                f"fade via XAGUSD; SL={RATIO_SL} ATR RR={RATIO_RR} hold≤{RATIO_HOLD}; "
                f"UTC{RATIO_FIRE_UTC}.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No FX3 H4 path densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Cross-asset / RV greenfield (Round 6)",
                "",
                "| Object | Vs killboard |",
                "|---|---|",
                "| EUR triad parity resid MR | ≠ FX3 H4 path R1–R5; ≠ EURGBP→EURUSD lead (V8); "
                "≠ XS residual/mom; ≠ AUDNZD ZMR; ≠ LNY EUR/GBP |",
                "| USDJPY NAS100 frozen-β fade | ≠ XAU USD-beta resid; ≠ XS USD residual; "
                "≠ VIX/HY/MOVE/DTWEX siblings; ≠ FRED displace; ≠ WTI→USDCAD |",
                "| XAU–XAG ratio ZMR | ≠ XAU USD-beta resid fade; ≠ AUDNZD ZMR; "
                "≠ impulse consec; ≠ FX3 H4 path |",
                "",
                "CLEARED for offline probe. No densify of cleared killboard knobs.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = [
        "# Offline — Cross-asset / RV greenfield (Round 6)",
        "",
        f"Receipt `{receipt}`",
        f"Generated `{utc_now()}`",
        "Cost a priori +$12; gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.",
        f"Beta freeze: α={beta_fit['alpha']:.6g} β={beta_fit['beta']:.6g} "
        f"n={beta_fit['n_fit']} R²={beta_fit['r2']} driver=NAS100.",
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
                "# Closeout — Cross-asset / RV greenfield (Round 6)",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do **not** densify FX3 H4 path R1–R5 / XS / AUDNZD / XAU-beta / "
                "parity z / NAS β / metal-ratio knobs from this board.",
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
                "# VN brief — Round 6 cross-asset / RV greenfield",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                f"- `{status}`",
                "- Surface **khác** FX3 H4 path (R1–R5 saturated).",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify path R1–R5 / XS / AUDNZD / XAU-beta / parity z / NAS β / ratio.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "- Next: true greenfield ngoài board này **hoặc** research-grade cost — "
                "không quay lại FX3 H4 OHLC path family.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Update compact session brief R1–R6
    def rows_from(path):
        if not path.exists():
            return [], ""
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for x in payload["results"]:
            v = (
                "SURVIVOR"
                if x.get("verdict") == "PROBE_SURVIVOR"
                else "KILL"
            )
            rows.append(
                f"| `{x['hypothesis_id']}` | {x['metrics']['n']} | {x['metrics']['pf']} | "
                f"{x['metrics']['tpw']} | {x['haircuts']['x1_5']['pf']} | {v} |"
            )
        return rows, payload.get("receipt_sha256", "")

    r3_rows, r3_rcpt = rows_from(PRE / "20260715_GREENFIELD_SOLO_ACCEPT_OFFLINE_PROBES.json")
    r4_rows, r4_rcpt = rows_from(PRE / "20260715_GREENFIELD_DISP_ER_OFFLINE_PROBES.json")
    r5_rows, r5_rcpt = rows_from(
        PRE / "20260715_GREENFIELD_SPLIT_HALFBACK_OFFLINE_PROBES.json"
    )

    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D (greenfield R1–R6)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Hard pivot: FX3 H4 OHLC path family **saturated** sau R5. "
                "Round 6 = cross-asset / RV surfaces.",
                "Không densify killboard. QFSI song song. Login không headline.",
                "",
                "## Round 1–5 — FX3 H4 path/cont/fade → ALL_KILL (saturated)",
                "| Round | Objects | Verdict |",
                "|---|---|---|",
                "| R1 | majority-lag + TSMOM-band | ALL_KILL |",
                "| R2 | spring + PB-reclaim | ALL_KILL |",
                "| R3 | solo-leader + H4disp accept | ALL_KILL |",
                "| R4 | bookdisp fade + path-ER | ALL_KILL |",
                "| R5 | book-split + halfback-hold | ALL_KILL |",
                "",
                "### R3 detail",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *r3_rows,
                f"Receipt `{r3_rcpt}`",
                "",
                "### R4 detail",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *r4_rows,
                f"Receipt `{r4_rcpt}`",
                "",
                "### R5 detail",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *r5_rows,
                f"Receipt `{r5_rcpt}`",
                "",
                f"## Round 6 — EUR triad + NAS100-β + XAU/XAG → `{status}`",
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
                "- R1–R5 FX3 H4 path = **saturated** — FORBIDDEN densify.",
                "- Round 6 đổi surface (parity / equity-β / metal ratio).",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next: greenfield ngoài Round 6 board **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(results, receipt):
    # Idempotent: drop prior rows for these hypothesis_ids from this lane.
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
                and obj.get("lane") == "greenfield_crossasset_rv_20260715"
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
                        "parent_candidate": "post_round5_fx3_h4_saturated_20260715",
                        "feature_family": "greenfield_crossasset_rv_r6",
                        "lane": "greenfield_crossasset_rv_20260715",
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


def patch_hot(results, receipt, any_surv, beta_fit):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD ROUND6 CROSSASSET/RV CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Hard pivot after FX3 H4 R1–R5 path family **SATURATED**. Nested critic "
        "`cursor-grok-4.5-high-fast`.",
        f"  Beta freeze NAS100→USDJPY: α={beta_fit['alpha']:.6g} "
        f"β={beta_fit['beta']:.6g} n={beta_fit['n_fit']} R²={beta_fit['r2']}.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_CROSSASSET_RV_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_CROSSASSET_RV_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`;",
        "  panel `readouts/20260715_GREENFIELD_CROSSASSET_RV_3CRITIC_PANEL.md`.",
        "  Do **not** densify FX3 H4 path R1–R5 / parity z / NAS β / metal-ratio /",
        "  XS / AUDNZD / XAU-beta / AONIA/CORRA/thin3/exit/FRED/LNY.",
        "  Next: next true greenfield outside Round6 board — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round6 cross-asset/RV greenfield "
            f"{status.split('__')[0]}; GOAL unmet"
        )
    # Remove any prior Round6 block (idempotent re-run after engineering fix).
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if "GREENFIELD ROUND6 CROSSASSET/RV CLOSEOUT" in ln:
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


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        for s in (
            "EURUSD",
            "GBPUSD",
            "EURGBP",
            "USDJPY",
            "NAS100",
            "XAUUSD",
            "XAGUSD",
        ):
            if not mt5.symbol_select(s, True):
                raise RuntimeError(f"symbol_select failed: {s}")

        data = {
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_H1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_H1)),
            "EURGBP": enrich(load("EURGBP", mt5.TIMEFRAME_H1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_H1)),
            "NAS100": enrich(load("NAS100", mt5.TIMEFRAME_H1)),
            "XAUUSD": enrich(load("XAUUSD", mt5.TIMEFRAME_H1)),
            "XAGUSD": enrich(load("XAGUSD", mt5.TIMEFRAME_H1)),
        }
        jpy_pre = load("USDJPY", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO)
        nas_pre = load("NAS100", mt5.TIMEFRAME_H1, BETA_FROM, BETA_TO)
        beta_fit = fit_frozen_beta(jpy_pre, nas_pre)

        results = []
        pnls, detail = probe_eur_triad_parity(data)
        results.append(
            pack_result(
                "HYP-EUR-TRIAD-H1-PARITY-RESID-MR-001",
                "EURGBP fade vs EURUSD/GBPUSD log-parity residual z",
                "EURGBP",
                "H1",
                pnls,
                detail,
            )
        )
        pnls, detail = probe_nas100_beta_resid(data, beta_fit)
        results.append(
            pack_result(
                "HYP-USDJPY-H1-NAS100-BETA-RESID-FADE-001",
                "USDJPY fade vs frozen NAS100 beta residual z",
                "USDJPY(+NAS100)",
                "H1",
                pnls,
                detail,
            )
        )
        pnls, detail = probe_xau_xag_ratio(data)
        results.append(
            pack_result(
                "HYP-XAU-XAG-H1-RATIO-ZMR-001",
                "XAGUSD fade of ln(XAU/XAG) ratio residual z",
                "XAGUSD(+XAUUSD)",
                "H1",
                pnls,
                detail,
            )
        )

        payload = {
            "generated_at": utc_now(),
            "lane": "greenfield_crossasset_rv_20260715",
            "parent": "post_round5_fx3_h4_saturated",
            "nested_critic": "cursor-grok-4.5-high-fast",
            "cost_usd": BASE_COST,
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "beta_fit": beta_fit,
            "forbidden": [
                "FX3_H4_path_R1_R5_densify",
                "XS_AUDNZD_XAU_USD_beta_densify",
                "AONIA_CORRA_thin3_carry_LNY_FRED_VIX_siblings",
            ],
            "results": results,
            "receipt_sha256": None,
        }
        # Canonical receipt over payload excluding receipt field, then embed.
        body = {k: v for k, v in payload.items() if k != "receipt_sha256"}
        receipt = sha256_bytes(
            (json.dumps(body, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n").encode(
                "utf-8"
            )
        )
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )

        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        write_docs(results, receipt, any_surv, beta_fit)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, beta_fit)

        print("RECEIPT", receipt)
        print("STATUS", "SURVIVOR" if any_surv else "ALL_KILL")
        for r in results:
            print(
                r["hypothesis_id"],
                r["verdict"],
                r["metrics"],
                r["haircuts"]["x1_5"],
                r["fail_notes"],
            )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
