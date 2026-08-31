#!/usr/bin/env python3
"""Offline sequential gate counts for EA_HybridICT_Sonic (Owner choice A).

NOT Model 0. NOT promotion. Mirrors HIS closed-bar gates on EURUSD M15+H4.
Identifies which AND gate first zeros cadence — no densify/rescue.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

# Factory isolate only (was r"C:\Program Files\MetaTrader 5\terminal64.exe",
# a path that does not exist here). See tools/factory_paths.py.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from tools.factory_paths import factory_mt5_terminal as _factory_mt5_terminal

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "03. EA Developer/EA_HybridICT_Sonic/research/preflight"
READOUT = (
    ROOT
    / "03. EA Developer/EA_HybridICT_Sonic/research"
    / "20260715_HIS_OFFLINE_GATECOUNT_EURUSD_M15_READOUT.md"
)
SYMBOL = "EURUSD"
FROM = datetime(2020, 1, 1)
TO = datetime(2026, 7, 15, 23, 59, 59)

# Frozen to remint / EA defaults used in diagnosis
DRAGON = 34
ATR_N = 14
ATR_MA = 50
SWING = 2
H4_LB = 80
M15_LB = 80
FVG_MAX_AGE = 60
LEVEL_ATR = 0.50
WAVE_LB = 40
VOL_AVG = 20
VOL_MULT = 1.5
SESSION_H0, SESSION_H1 = 7, 20
PIP = 0.0001
PENDING_OFF_PIPS = 4.0
DRAGON_SL_PIPS = 40.0
SL_ATR_BUF = 0.10
MAX_SL_ATR = 2.5
MIN_ATR_R, MAX_ATR_R = 0.70, 3.00


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ema(x: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    if len(x) < period:
        return out
    alpha = 2.0 / (period + 1.0)
    out[period - 1] = float(np.mean(x[:period]))
    for i in range(period, len(x)):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def atr_wilder(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n < period:
        return out
    out[period - 1] = float(np.mean(tr[:period]))
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def load_rates_chunked(tf: int, years: range) -> dict[str, np.ndarray]:
    """Year-chunked copy_rates_range (API rejects multi-year spans / huge counts)."""
    parts: list[np.ndarray] = []
    for y in years:
        fr = datetime(y, 1, 1)
        to = datetime(y + 1, 1, 1) if y < 2026 else datetime(2026, 7, 16)
        rates = mt5.copy_rates_range(SYMBOL, tf, fr, to)
        if rates is None:
            continue
        # drop single-bar stubs
        if len(rates) <= 1:
            continue
        parts.append(rates)
    if not parts:
        raise RuntimeError(f"rates fail tf={tf}: {mt5.last_error()}")
    rates = np.concatenate(parts)
    # de-dup by time ascending
    _, uniq = np.unique(rates["time"], return_index=True)
    rates = rates[np.sort(uniq)]
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
        "tick_volume": rates["tick_volume"].astype(float),
    }


def to_series_window(arr: np.ndarray, i: int, n: int) -> np.ndarray:
    """Series-order window ending at chrono i inclusive: [i, i-1, ..., i-n+1]."""
    start = i - n + 1
    if start < 0:
        return np.array([])
    return arr[start : i + 1][::-1].copy()


def is_swing_high_series(high: np.ndarray, i: int, strength: int) -> bool:
    # high is series-ordered (0=newest in window)
    if i < strength or i + strength >= len(high):
        return False
    for k in range(1, strength + 1):
        if high[i] <= high[i - k] or high[i] <= high[i + k]:
            return False
    return True


def is_swing_low_series(low: np.ndarray, i: int, strength: int) -> bool:
    if i < strength or i + strength >= len(low):
        return False
    for k in range(1, strength + 1):
        if low[i] >= low[i - k] or low[i] >= low[i + k]:
            return False
    return True


def compute_h4_bias(h4_o, h4_h, h4_l, h4_c) -> tuple[int, float, float, float, float]:
    """Inputs series-ordered H4 window (0=newest closed)."""
    n = len(h4_c)
    ob_h = ob_l = liq_h = liq_l = 0.0
    sh: list[int] = []
    sl: list[int] = []
    lim = min(n - SWING - 1, H4_LB - 1)
    for i in range(SWING, lim + 1):
        if len(sh) < 8 and is_swing_high_series(h4_h, i, SWING):
            sh.append(i)
        if len(sl) < 8 and is_swing_low_series(h4_l, i, SWING):
            sl.append(i)
        if len(sh) >= 8 and len(sl) >= 8:
            break
    if sh:
        liq_h = float(h4_h[sh[0]])
    if sl:
        liq_l = float(h4_l[sl[0]])

    bias = 0
    for i in range(lim, -1, -1):
        for s in sh:
            if s <= i:
                continue
            if h4_c[i] > h4_h[s]:
                bias = 1
                break
        for s in sl:
            if s <= i:
                continue
            if h4_c[i] < h4_l[s]:
                bias = -1
                break

    if bias == 0 and len(sh) >= 2 and len(sl) >= 2:
        hh = h4_h[sh[0]] > h4_h[sh[1]]
        hl = h4_l[sl[0]] > h4_l[sl[1]]
        lh = h4_h[sh[0]] < h4_h[sh[1]]
        ll = h4_l[sl[0]] < h4_l[sl[1]]
        if hh and hl:
            bias = 1
        elif lh and ll:
            bias = -1

    if bias != 0:
        for i in range(1, min(n, 30)):
            if bias > 0 and h4_c[i] < h4_o[i]:
                ob_h, ob_l = float(h4_h[i]), float(h4_l[i])
                break
            if bias < 0 and h4_c[i] > h4_o[i]:
                ob_h, ob_l = float(h4_h[i]), float(h4_l[i])
                break
    return bias, ob_h, ob_l, liq_h, liq_l


def find_fvg(h4_h, h4_l, h4_c, bias: int) -> tuple[bool, float, float]:
    n = len(h4_c)
    max_age = min(n - 3, FVG_MAX_AGE)
    for i in range(1, max_age + 1):
        if i + 2 >= n:
            break
        if bias > 0 and h4_l[i] > h4_h[i + 2]:
            top, bot = float(h4_l[i]), float(h4_h[i + 2])
            mitigated = any(h4_c[j] <= bot for j in range(0, i))
            if not mitigated:
                return True, top, bot
        if bias < 0 and h4_h[i] < h4_l[i + 2]:
            top, bot = float(h4_l[i + 2]), float(h4_h[i])
            mitigated = any(h4_c[j] >= top for j in range(0, i))
            if not mitigated:
                return True, top, bot
    return False, 0.0, 0.0


def near_level(
    low: float,
    high: float,
    atr: float,
    has_fvg: bool,
    ztop: float,
    zbot: float,
    ob_h: float,
    ob_l: float,
    liq_h: float,
    liq_l: float,
    bias: int,
) -> bool:
    tol = LEVEL_ATR * atr
    if has_fvg and ztop > zbot and low <= ztop + tol and high >= zbot - tol:
        return True
    if ob_h > ob_l and low <= ob_h + tol and high >= ob_l - tol:
        return True
    if bias > 0 and liq_l > 0.0 and abs(low - liq_l) <= tol:
        return True
    if bias < 0 and liq_h > 0.0 and abs(high - liq_h) <= tol:
        return True
    return False


def wave_long(h: np.ndarray, l: np.ndarray) -> bool:
    n = len(h)
    sh1 = sh2 = sl1 = sl2 = -1
    lim = min(n - SWING, WAVE_LB)
    for i in range(SWING, lim):
        if sh1 < 0 and is_swing_high_series(h, i, SWING):
            sh1 = i
        elif sh1 >= 0 and sh2 < 0 and is_swing_high_series(h, i, SWING) and i > sh1 + SWING:
            sh2 = i
        if sl1 < 0 and is_swing_low_series(l, i, SWING):
            sl1 = i
        elif sl1 >= 0 and sl2 < 0 and is_swing_low_series(l, i, SWING) and i > sl1 + SWING:
            sl2 = i
        if sh1 >= 0 and sl1 >= 0 and sl2 >= 0 and (sh2 >= 0 or True):
            if sl1 >= 0 and sl2 >= 0:
                break
    if sh1 < 0 or sl1 < 0 or sl2 < 0:
        return False
    hl = l[sl1] > l[sl2]
    rising = True if sh2 < 0 else h[sh1] > h[sh2]
    return bool(hl and rising)


def wave_short(h: np.ndarray, l: np.ndarray) -> bool:
    n = len(h)
    sh1 = sh2 = sl1 = sl2 = -1
    lim = min(n - SWING, WAVE_LB)
    for i in range(SWING, lim):
        if sh1 < 0 and is_swing_high_series(h, i, SWING):
            sh1 = i
        elif sh1 >= 0 and sh2 < 0 and is_swing_high_series(h, i, SWING) and i > sh1 + SWING:
            sh2 = i
        if sl1 < 0 and is_swing_low_series(l, i, SWING):
            sl1 = i
        elif sl1 >= 0 and sl2 < 0 and is_swing_low_series(l, i, SWING) and i > sl1 + SWING:
            sl2 = i
        if sh1 >= 0 and sh2 >= 0 and sl1 >= 0:
            break
    if sl1 < 0 or sh1 < 0 or sh2 < 0:
        return False
    lh = h[sh1] < h[sh2]
    falling = True if sl2 < 0 else l[sl1] < l[sl2]
    return bool(lh and falling)


def pvsra(vol: np.ndarray) -> bool:
    if len(vol) < VOL_AVG + 2:
        return False
    avg = float(np.mean(vol[1 : VOL_AVG + 1]))
    if avg <= 0:
        return False
    return float(vol[0]) >= avg * VOL_MULT


def in_session_gmt(ts: int) -> bool:
    dt = datetime.utcfromtimestamp(int(ts))
    if dt.weekday() >= 5:
        return False
    if dt.weekday() == 4 and dt.hour >= 20:
        return False
    return SESSION_H0 <= dt.hour < SESSION_H1


def map_h4_index(m15_t: int, h4_t: np.ndarray) -> int:
    # last H4 bar with time <= m15 bar time
    j = int(np.searchsorted(h4_t, m15_t, side="right") - 1)
    return j


def main() -> None:
    terminal = str(_factory_mt5_terminal())
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    try:
        mt5.symbol_select(SYMBOL, True)
        # M15 via Python API: usable year-chunks from ~2022 (2019-2021 stubs only).
        # H4 available deeper. Document coverage honestly vs Model 0 tester window.
        m15 = load_rates_chunked(mt5.TIMEFRAME_M15, range(2022, 2027))
        h4 = load_rates_chunked(mt5.TIMEFRAME_H4, range(2019, 2027))
    finally:
        mt5.shutdown()

    coverage = {
        "m15_bars": int(len(m15["close"])),
        "h4_bars": int(len(h4["close"])),
        "m15_first_utc": datetime.utcfromtimestamp(int(m15["time"][0])).isoformat() + "Z",
        "m15_last_utc": datetime.utcfromtimestamp(int(m15["time"][-1])).isoformat() + "Z",
        "note": (
            "Python copy_rates year-chunks: M15 usable ~2022+ on this terminal API; "
            "Model 0 tester had full 2020-2026 ticks. Gate ranking still valid on covered M15."
        ),
    }

    dh = ema(m15["high"], DRAGON)
    dm = ema(m15["close"], DRAGON)
    dl = ema(m15["low"], DRAGON)
    atr = atr_wilder(m15["high"], m15["low"], m15["close"], ATR_N)

    n = len(m15["close"])
    counts = {
        "N_bars_total": 0,
        "N0_session": 0,
        "N1_atr_regime": 0,
        "N2_bias": 0,
        "N3_level_object": 0,
        "N4_near_level": 0,
        "N5_wave": 0,
        "N6_dragon": 0,
        "N6a_mid_reclaim": 0,
        "N6b_outer_break": 0,
        "N7_pvsra": 0,
        "N8_sl_ok": 0,
        "N8_sl_fail_dragon40": 0,
    }

    # warmup
    start_i = max(M15_LB + 5, DRAGON + ATR_MA + 5)
    for i in range(start_i, n):
        counts["N_bars_total"] += 1
        ts = int(m15["time"][i])
        if not in_session_gmt(ts):
            continue
        counts["N0_session"] += 1

        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        # ATR regime: mean of last ATR_MA atr values ending at i
        if i < ATR_MA:
            continue
        atr_ma = float(np.mean(atr[i - ATR_MA + 1 : i + 1]))
        if atr_ma <= 0:
            continue
        ratio = a / atr_ma
        if ratio < MIN_ATR_R or ratio > MAX_ATR_R:
            continue
        counts["N1_atr_regime"] += 1

        j = map_h4_index(ts, h4["time"])
        if j < H4_LB:
            continue
        # series windows
        h4_o = to_series_window(h4["open"], j, H4_LB)
        h4_h = to_series_window(h4["high"], j, H4_LB)
        h4_l = to_series_window(h4["low"], j, H4_LB)
        h4_c = to_series_window(h4["close"], j, H4_LB)
        if len(h4_c) < H4_LB:
            continue

        bias, ob_h, ob_l, liq_h, liq_l = compute_h4_bias(h4_o, h4_h, h4_l, h4_c)
        if bias == 0:
            continue
        counts["N2_bias"] += 1

        has_fvg, ztop, zbot = find_fvg(h4_h, h4_l, h4_c, bias)
        if (not has_fvg) and (ob_h <= ob_l) and (liq_h <= 0.0) and (liq_l <= 0.0):
            continue
        counts["N3_level_object"] += 1

        if not near_level(
            float(m15["low"][i]),
            float(m15["high"][i]),
            a,
            has_fvg,
            ztop,
            zbot,
            ob_h,
            ob_l,
            liq_h,
            liq_l,
            bias,
        ):
            continue
        counts["N4_near_level"] += 1

        m_h = to_series_window(m15["high"], i, M15_LB)
        m_l = to_series_window(m15["low"], i, M15_LB)
        m_c = to_series_window(m15["close"], i, M15_LB)
        m_v = to_series_window(m15["tick_volume"], i, M15_LB)
        if len(m_c) < 40:
            continue

        if bias > 0 and not wave_long(m_h, m_l):
            continue
        if bias < 0 and not wave_short(m_h, m_l):
            continue
        counts["N5_wave"] += 1

        d_hi, d_md, d_lo = float(dh[i]), float(dm[i]), float(dl[i])
        c0, c1 = float(m15["close"][i]), float(m15["close"][i - 1])
        if bias > 0:
            outer = c0 > d_hi
            mid = c0 > d_md and c1 <= float(dm[i - 1])
        else:
            outer = c0 < d_lo
            mid = c0 < d_md and c1 >= float(dm[i - 1])
        if mid:
            counts["N6a_mid_reclaim"] += 1
        if outer:
            counts["N6b_outer_break"] += 1
        if not (outer or mid):
            continue
        counts["N6_dragon"] += 1

        if not pvsra(m_v):
            continue
        counts["N7_pvsra"] += 1

        # SL width gate (mirror EA)
        if bias > 0:
            sl = float(m15["low"][i])
            if has_fvg:
                sl = min(sl, zbot)
            if ob_l > 0:
                sl = min(sl, ob_l)
            if liq_l > 0:
                sl = min(sl, liq_l)
            sl -= SL_ATR_BUF * a
            dragon_sl = d_lo - DRAGON_SL_PIPS * PIP
            sl = min(sl, dragon_sl)
            entry = float(m15["high"][i]) + PENDING_OFF_PIPS * PIP
        else:
            sl = float(m15["high"][i])
            if has_fvg:
                sl = max(sl, ztop)
            if ob_h > 0:
                sl = max(sl, ob_h)
            if liq_h > 0:
                sl = max(sl, liq_h)
            sl += SL_ATR_BUF * a
            dragon_sl = d_hi + DRAGON_SL_PIPS * PIP
            sl = max(sl, dragon_sl)
            entry = float(m15["low"][i]) - PENDING_OFF_PIPS * PIP

        risk = abs(entry - sl)
        if risk <= 0:
            continue
        if risk > MAX_SL_ATR * a:
            counts["N8_sl_fail_dragon40"] += 1
            continue
        counts["N8_sl_ok"] += 1

    # drop ratios
    keys = [
        "N0_session",
        "N1_atr_regime",
        "N2_bias",
        "N3_level_object",
        "N4_near_level",
        "N5_wave",
        "N6_dragon",
        "N7_pvsra",
        "N8_sl_ok",
    ]
    drops: list[dict[str, Any]] = []
    prev = counts["N_bars_total"]
    first_near_zero = None
    for k in keys:
        cur = counts[k]
        ratio = (cur / prev) if prev > 0 else 0.0
        drops.append({"gate": k, "count": cur, "prev": prev, "pass_ratio": round(ratio, 6)})
        if first_near_zero is None and (cur == 0 or ratio < 0.01):
            first_near_zero = k
        prev = cur

    payload = {
        "schema_version": "his_offline_gatecount.v1",
        "owner_choice": "A",
        "symbol": SYMBOL,
        "requested_from": FROM.strftime("%Y-%m-%d"),
        "requested_to": TO.strftime("%Y-%m-%d"),
        "coverage": coverage,
        "note": "Offline only. Not Model 0. Not promotion. Mirror HIS mechanical gates.",
        "counts": counts,
        "drops": drops,
        "first_near_zero_gate": first_near_zero,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    out = OUT_DIR / "20260715_HIS_OFFLINE_GATECOUNT_EURUSD_M15.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    out.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
    (OUT_DIR / "20260715_HIS_OFFLINE_GATECOUNT_EURUSD_M15.sha256.txt").write_text(
        sha + "\n", encoding="utf-8"
    )

    # readout md
    lines = [
        "# HIS Offline Gate-Count — EURUSD M15 (Owner A)",
        "",
        f"Generated: {payload['generated_at_utc']}",
        f"Requested: {payload['requested_from']} → {payload['requested_to']}",
        f"Covered M15: {coverage['m15_first_utc']} → {coverage['m15_last_utc']} ({coverage['m15_bars']} bars)",
        f"Covered H4: {coverage['h4_bars']} bars",
        f"Coverage note: {coverage['note']}",
        f"Artifact SHA256: `{sha}`",
        "",
        "## Counts (sequential AND)",
        "",
        "| Gate | Count | Pass ratio vs prior |",
        "|---|---:|---:|",
        f"| N_bars_total | {counts['N_bars_total']} | — |",
    ]
    for d in drops:
        lines.append(f"| {d['gate']} | {d['count']} | {d['pass_ratio']:.4f} |")
    lines += [
        "",
        f"| N6a mid reclaim (non-exclusive) | {counts['N6a_mid_reclaim']} | — |",
        f"| N6b outer break (non-exclusive) | {counts['N6b_outer_break']} | — |",
        f"| N8 SL fail after full stack (Dragon±40 vs MaxSl) | {counts['N8_sl_fail_dragon40']} | — |",
        "",
        f"**First near-zero gate:** `{first_near_zero}`",
        "",
        "## Interpretation",
        "",
        "- Offline probe only — not Model 0 / not PF claim.",
        "- Do not densify Dragon 30–38 or post-hoc hour veto from this.",
        "- Parent hyp remains `KILL_AT_MODEL0_EMPTY`.",
        "",
    ]
    READOUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print("OUT", out)
    print("SHA", sha)
    print("FIRST_NEAR_ZERO", first_near_zero)


if __name__ == "__main__":
    main()
