#!/usr/bin/env python3
"""Multi-day H4–D1 swing thick book — offline joint screen.

Authority: Owner R&D continue after entry-state ALL_KILL; EXO_FRED_DISPLACE_SPAM_PAUSED.
Nested critic: cursor-grok-4.5-high-fast. Model 0 only if PROBE_SURVIVOR.
Login never headline. Cost freeze still GAP — +$12 flat proxy only.

FORBIDDEN densify / clone families:
  RR2 exit / entry impulse / thinrisk / magnet
  FRED displace/ToT · LNY fade/coil/catchup · XS residual/mom · AUDNZD z
  H4 Outside/Engulf/Pin · Donchian · RV-compress/NR7 · D1-EMA-H4-PB
  Weekly-HL · H4-struct-M15 · H4-balance-break · Asia coil densify · MaxKZ/RR

A priori frozen (≥2):
  1) HYP-FX3-D1ADX-H4-THRUST3-SWING-001
  2) HYP-FX3-D1-TRENDDAY-ROC-BOOK-001

If both fail: next class = multi-symbol D1 vol-regime breakout
(ATR14/ATR50 expansion + close beyond prior 8-day extreme) — not channel/NR7/EMA-PB.
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

OUT_JSON = PRE / "20260715_SWING_THICK_BOOK_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_SWING_THICK_BOOK_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_SWING_THICK_BOOK_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_SWING_THICK_BOOK_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_SWING_THICK_BOOK_3CRITIC_MEMO.md"
OUT_CLOSE = READ / "20260715_SWING_THICK_BOOK_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_SWING_THICK_BOOK_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY")

# --- Object A: D1 ADX + H4 thrust3 continuation ---
A_ADX_LEN = 14
A_ADX_MIN = 25.0
A_THRUST_BARS = 3
A_THRUST_STEP_ATR = 0.25
A_SL_ATR = 1.75
A_SL_MIN_ATR = 1.50
A_RR = 3.0
A_MAX_HOLD_H4 = 28
A_MAX_OPEN_BOOK = 2

# --- Object B: D1 trend-day + ROC persist multi-setup ---
B_TD_RANGE_ATR = 1.15
B_TD_BODY_RATIO = 0.70
B_ROC_SHORT = 3
B_ROC_LONG = 10
B_ROC_MOVE_ATR = 1.0
B_SL_ATR = 1.60
B_RR = 2.5
B_MAX_HOLD_H4 = 32
B_MAX_OPEN_BOOK = 2


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / WEEKS if WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict) -> tuple[str, list[str]]:
    notes: list[str] = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.5 <= tpw <= 6.0):
        notes.append("cadence_fail")
    if pf <= 1.20:
        notes.append("pf_fail")
    if x15 < 1.15:
        notes.append("stress_fail")
    if n >= 80 and pf > 1.20 and 1.5 <= tpw <= 6.0 and x15 >= 1.15:
        return "PROBE_SURVIVOR", notes
    if not notes:
        notes.append("joint_screen_miss")
    return "KILLED_AT_OFFLINE_PROBE", notes


def atr_wilder(h: np.ndarray, l: np.ndarray, c: np.ndarray, length: int = 14) -> np.ndarray:
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n < length:
        return out
    out[length - 1] = tr[:length].mean()
    for i in range(length, n):
        out[i] = (out[i - 1] * (length - 1) + tr[i]) / length
    return out


def adx_di(h: np.ndarray, l: np.ndarray, c: np.ndarray, length: int = 14):
    """Return ADX, +DI, -DI (Wilder)."""
    n = len(c)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        plus_dm[i] = up if (up > dn and up > 0) else 0.0
        minus_dm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))

    atr = np.full(n, np.nan)
    pdm = np.full(n, np.nan)
    mdm = np.full(n, np.nan)
    if n < length:
        return atr, atr, atr
    atr[length - 1] = tr[:length].mean()
    pdm[length - 1] = plus_dm[:length].mean()
    mdm[length - 1] = minus_dm[:length].mean()
    for i in range(length, n):
        atr[i] = (atr[i - 1] * (length - 1) + tr[i]) / length
        pdm[i] = (pdm[i - 1] * (length - 1) + plus_dm[i]) / length
        mdm[i] = (mdm[i - 1] * (length - 1) + minus_dm[i]) / length

    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    dx = np.full(n, np.nan)
    for i in range(length - 1, n):
        if atr[i] <= 0 or math.isnan(atr[i]):
            continue
        plus_di[i] = 100.0 * pdm[i] / atr[i]
        minus_di[i] = 100.0 * mdm[i] / atr[i]
        s = plus_di[i] + minus_di[i]
        if s <= 0:
            continue
        dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / s

    adx = np.full(n, np.nan)
    # first ADX at 2*length-2
    start = 2 * length - 2
    if n <= start:
        return adx, plus_di, minus_di
    window = [dx[i] for i in range(length - 1, start + 1) if not math.isnan(dx[i])]
    if len(window) < length:
        return adx, plus_di, minus_di
    adx[start] = sum(window[-length:]) / length
    for i in range(start + 1, n):
        if math.isnan(dx[i]) or math.isnan(adx[i - 1]):
            continue
        adx[i] = (adx[i - 1] * (length - 1) + dx[i]) / length
    return adx, plus_di, minus_di


def load_tf(symbol: str, tf) -> dict:
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol} {tf}: {mt5.last_error()}")
    return {
        "symbol": symbol,
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def day_key(ts: int) -> str:
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")


def weekday(ts: int) -> int:
    return datetime.utcfromtimestamp(ts).weekday()


def resolve_r(
    direction: int,
    entry: float,
    sl: float,
    tp: float,
    i0: int,
    h: np.ndarray,
    l: np.ndarray,
    c: np.ndarray,
    max_hold: int,
    rr_hit: float,
) -> float | None:
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    end = min(i0 + max_hold, len(c))
    for j in range(i0, end):
        hi, lo = h[j], l[j]
        if direction > 0:
            if lo <= sl:
                return -1.0
            if hi >= tp:
                return float(rr_hit)
        else:
            if hi >= sl:
                return -1.0
            if lo <= tp:
                return float(rr_hit)
    j = min(i0 + max_hold - 1, len(c) - 1)
    if j < i0:
        return None
    return direction * (c[j] - entry) / risk


def pnls_from_r(trades: list[dict]) -> list[float]:
    bal = DEPOSIT
    out = []
    for t in trades:
        pnl = bal * RISK_FRAC * t["r"]
        out.append(pnl)
        bal += pnl
    return out


def pack(hid: str, funnel: dict, trades: list[dict], note: str = "") -> dict:
    pnls = pnls_from_r(trades)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "symbol": "BOOK:EUR+GBP+USDJPY",
        "tf": "H4/D1",
        "family": "swing_thick_multisym_book",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "cost_proxy_usd": BASE_COST,
        "note": note or "cost proxy +$12/trade flat; NOT research-grade freeze",
        "n_trades_raw": len(trades),
    }


def build_symbol_bundle(symbol: str) -> dict:
    h4 = load_tf(symbol, mt5.TIMEFRAME_H4)
    d1 = load_tf(symbol, mt5.TIMEFRAME_D1)
    h4["atr"] = atr_wilder(h4["high"], h4["low"], h4["close"], 14)
    d1["atr"] = atr_wilder(d1["high"], d1["low"], d1["close"], 14)
    d1["adx"], d1["pdi"], d1["mdi"] = adx_di(d1["high"], d1["low"], d1["close"], A_ADX_LEN)
    # map each H4 bar to last closed D1 index (D1 day < H4 day or same day closed)
    d1_idx = []
    j = -1
    for i, ts in enumerate(h4["time"]):
        while j + 1 < len(d1["time"]) and int(d1["time"][j + 1]) <= int(ts):
            # D1 bar timestamp is day open; treat as closed only after next day starts.
            # Conservative: use D1 bars with time < current H4 time (prior completed days).
            if int(d1["time"][j + 1]) < int(ts):
                j += 1
            else:
                break
        d1_idx.append(j)
    h4["d1_idx"] = np.array(d1_idx, dtype=np.int64)
    return {"h4": h4, "d1": d1, "symbol": symbol}


def active_count(open_until: dict[str, int], ts: int) -> int:
    return sum(1 for t_end in open_until.values() if t_end > ts)


def probe_adx_thrust(books: dict[str, dict]) -> dict:
    """Object A — D1 ADX filter + H4 3-bar thrust continuation, FX3 portfolio."""
    funnel = {
        "n_signal_bars": 0,
        "n_armed": 0,
        "n_trades": 0,
        "n_blocked_overlap": 0,
        "by_symbol": {},
    }
    # Collect candidate signals then simulate chronologically with portfolio caps
    cands: list[dict] = []
    for sym, b in books.items():
        h4, d1 = b["h4"], b["d1"]
        t, o, h, l, c, atr = h4["time"], h4["open"], h4["high"], h4["low"], h4["close"], h4["atr"]
        n = len(t)
        for i in range(A_THRUST_BARS, n - 2):
            if weekday(int(t[i])) >= 5:
                continue
            di = int(h4["d1_idx"][i])
            if di < A_ADX_LEN * 2:
                continue
            adx = d1["adx"][di]
            pdi = d1["pdi"][di]
            mdi = d1["mdi"][di]
            a = atr[i]
            if any(math.isnan(x) for x in (adx, pdi, mdi, a)) or a <= 0:
                continue
            if adx < A_ADX_MIN:
                continue
            # thrust bars i-2, i-1, i closed
            dirs = []
            ok_step = True
            for k in range(i - A_THRUST_BARS + 1, i + 1):
                if c[k] > o[k]:
                    dirs.append(1)
                elif c[k] < o[k]:
                    dirs.append(-1)
                else:
                    dirs.append(0)
                if k > i - A_THRUST_BARS + 1:
                    step = abs(c[k] - c[k - 1])
                    if step < A_THRUST_STEP_ATR * atr[k]:
                        ok_step = False
            if not ok_step or 0 in dirs or len(set(dirs)) != 1:
                continue
            direction = dirs[0]
            # DI align
            if direction > 0 and not (pdi > mdi):
                continue
            if direction < 0 and not (mdi > pdi):
                continue
            # bar3 extreme of three
            window_c = c[i - 2 : i + 1]
            if direction > 0 and c[i] < max(window_c):
                continue
            if direction < 0 and c[i] > min(window_c):
                continue
            funnel["n_signal_bars"] += 1
            leg_lo = float(min(l[i - 2 : i + 1]))
            leg_hi = float(max(h[i - 2 : i + 1]))
            i0 = i + 1
            entry = float(o[i0])
            # SL = 1.75 ATR beyond thrust-leg extreme
            if direction > 0:
                sl = leg_lo - A_SL_ATR * a
            else:
                sl = leg_hi + A_SL_ATR * a
            risk = abs(entry - sl)
            if risk < A_SL_MIN_ATR * a:
                sl = entry - direction * A_SL_MIN_ATR * a
                risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + direction * A_RR * risk
            r = resolve_r(direction, entry, sl, tp, i0, h, l, c, A_MAX_HOLD_H4, A_RR)
            if r is None:
                continue
            exit_i = min(i0 + A_MAX_HOLD_H4 - 1, n - 1)
            # approximate exit time: scan path
            exit_ts = int(t[exit_i])
            risk0 = abs(entry - sl)
            for j in range(i0, min(i0 + A_MAX_HOLD_H4, n)):
                if direction > 0 and (l[j] <= sl or h[j] >= tp):
                    exit_ts = int(t[j])
                    break
                if direction < 0 and (h[j] >= sl or l[j] <= tp):
                    exit_ts = int(t[j])
                    break
            cands.append(
                {
                    "ts_signal": int(t[i]),
                    "ts_entry": int(t[i0]),
                    "ts_exit": exit_ts,
                    "symbol": sym,
                    "direction": direction,
                    "adx": float(adx),
                    "r": float(r),
                    "day": day_key(int(t[i])),
                }
            )
            funnel["n_armed"] += 1

    cands.sort(key=lambda x: (x["ts_entry"], -x["adx"], x["symbol"]))
    trades: list[dict] = []
    open_until: dict[str, int] = {}
    # same-day EUR+GBP same dir: keep higher ADX
    day_eg: dict[str, list] = {}

    # First pass: resolve EUR/GBP same-day conflict
    by_day_dir: dict[tuple[str, int], list] = {}
    for c in cands:
        if c["symbol"] in ("EURUSD", "GBPUSD"):
            key = (c["day"], c["direction"])
            by_day_dir.setdefault(key, []).append(c)
    blocked_ids = set()
    for key, group in by_day_dir.items():
        if len(group) < 2:
            continue
        # keep max ADX among EUR+GBP
        best = max(group, key=lambda x: x["adx"])
        for g in group:
            if g is not best:
                blocked_ids.add(id(g))

    for c in cands:
        if id(c) in blocked_ids:
            funnel["n_blocked_overlap"] += 1
            continue
        ts_e = c["ts_entry"]
        # prune closed
        open_until = {s: te for s, te in open_until.items() if te > ts_e}
        if c["symbol"] in open_until:
            funnel["n_blocked_overlap"] += 1
            continue
        if len(open_until) >= A_MAX_OPEN_BOOK:
            funnel["n_blocked_overlap"] += 1
            continue
        open_until[c["symbol"]] = c["ts_exit"]
        trades.append(
            {
                "r": c["r"],
                "symbol": c["symbol"],
                "ts": c["ts_entry"],
                "direction": c["direction"],
                "adx": round(c["adx"], 2),
            }
        )
        funnel["by_symbol"][c["symbol"]] = funnel["by_symbol"].get(c["symbol"], 0) + 1
        funnel["n_trades"] += 1

    return pack(
        "HYP-FX3-D1ADX-H4-THRUST3-SWING-001",
        funnel,
        trades,
        "D1 ADX>=25 + H4 3-bar thrust cont; RR3; FX3 caps ≤2 open; ≠ Outside/NR7/EMA-PB",
    )


def probe_trendday_roc(books: dict[str, dict]) -> dict:
    """Object B — multi-setup D1 trend-day + ROC persist book."""
    funnel = {
        "n_td": 0,
        "n_rp": 0,
        "n_trades": 0,
        "n_blocked_overlap": 0,
        "by_symbol": {},
        "by_setup": {"TD": 0, "RP": 0},
    }
    cands: list[dict] = []

    for sym, b in books.items():
        h4, d1 = b["h4"], b["d1"]
        # Build D1 signals → enter next H4 open after D1 close.
        # D1 close time ≈ next day open on broker; map to first H4 with time > d1_time + 20h
        dt, do, dh, dl, dc, datr = (
            d1["time"],
            d1["open"],
            d1["high"],
            d1["low"],
            d1["close"],
            d1["atr"],
        )
        ht, ho, hh, hl, hc, hatr = (
            h4["time"],
            h4["open"],
            h4["high"],
            h4["low"],
            h4["close"],
            h4["atr"],
        )
        n_d = len(dt)
        # H4 index pointer
        hi = 0
        for i in range(B_ROC_LONG + 2, n_d - 1):
            if weekday(int(dt[i])) >= 5:
                continue
            a_d = datr[i]
            if math.isnan(a_d) or a_d <= 0:
                continue
            rng = dh[i] - dl[i]
            if rng <= 0:
                continue
            body = abs(dc[i] - do[i])
            td_ok = rng >= B_TD_RANGE_ATR * a_d and (body / rng) >= B_TD_BODY_RATIO
            roc3 = dc[i] - dc[i - B_ROC_SHORT]
            roc10 = dc[i] - dc[i - B_ROC_LONG]
            rp_ok = (
                np.sign(roc3) == np.sign(roc10)
                and np.sign(roc3) != 0
                and abs(dc[i] - dc[i - B_ROC_SHORT]) >= B_ROC_MOVE_ATR * a_d
            )
            setups = []
            if td_ok:
                funnel["n_td"] += 1
                setups.append(
                    (
                        "TD",
                        1 if dc[i] > do[i] else -1,
                        float(rng / a_d),
                        float(dl[i]),
                        float(dh[i]),
                    )
                )
            if rp_ok:
                funnel["n_rp"] += 1
                look_hi = float(max(dh[i - B_ROC_LONG : i + 1]))
                look_lo = float(min(dl[i - B_ROC_LONG : i + 1]))
                setups.append(
                    (
                        "RP",
                        int(np.sign(roc3)),
                        float(abs(roc3) / a_d),
                        look_lo,
                        look_hi,
                    )
                )
            if not setups:
                continue
            # same symbol same day: TD beats RP
            setups.sort(key=lambda x: (0 if x[0] == "TD" else 1, -x[2]))
            setup, direction, score, extreme_lo, extreme_hi = setups[0]
            if direction == 0:
                continue
            # find next H4 open strictly after this D1 bar timestamp
            # D1 time is typically 00:00 of the bar; bar closes at next D1 open.
            # Use first H4 with time >= next D1 open (dt[i+1]) for closed-bar entry.
            entry_ts_min = int(dt[i + 1]) if i + 1 < n_d else int(dt[i]) + 86400
            while hi < len(ht) and int(ht[hi]) < entry_ts_min:
                hi += 1
            if hi >= len(ht) - 2:
                continue
            # also require H4 ATR
            a_h = hatr[hi]
            if math.isnan(a_h) or a_h <= 0:
                continue
            entry = float(ho[hi])
            if direction > 0:
                sl = extreme_lo - B_SL_ATR * a_h
            else:
                sl = extreme_hi + B_SL_ATR * a_h
            risk = abs(entry - sl)
            if risk < B_SL_ATR * a_h * 0.5:
                sl = entry - direction * B_SL_ATR * a_h
                risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + direction * B_RR * risk
            r = resolve_r(
                direction, entry, sl, tp, hi, hh, hl, hc, B_MAX_HOLD_H4, B_RR
            )
            if r is None:
                continue
            exit_ts = int(ht[min(hi + B_MAX_HOLD_H4 - 1, len(ht) - 1)])
            for j in range(hi, min(hi + B_MAX_HOLD_H4, len(ht))):
                if direction > 0 and (hl[j] <= sl or hh[j] >= tp):
                    exit_ts = int(ht[j])
                    break
                if direction < 0 and (hh[j] >= sl or hl[j] <= tp):
                    exit_ts = int(ht[j])
                    break
            cands.append(
                {
                    "ts_entry": int(ht[hi]),
                    "ts_exit": exit_ts,
                    "symbol": sym,
                    "direction": direction,
                    "setup": setup,
                    "score": score,
                    "r": float(r),
                    "day": day_key(int(dt[i])),
                    "range_atr": float(rng / a_d),
                }
            )

    cands.sort(key=lambda x: (x["ts_entry"], 0 if x["setup"] == "TD" else 1, -x["score"], x["symbol"]))

    # EUR+GBP same-day same-dir: keep larger D1 range/ATR
    by_day_dir: dict[tuple[str, int], list] = {}
    for c in cands:
        if c["symbol"] in ("EURUSD", "GBPUSD"):
            by_day_dir.setdefault((c["day"], c["direction"]), []).append(c)
    blocked = set()
    for group in by_day_dir.values():
        if len(group) < 2:
            continue
        best = max(group, key=lambda x: x["range_atr"])
        for g in group:
            if g is not best:
                blocked.add(id(g))

    trades: list[dict] = []
    open_until: dict[str, int] = {}
    for c in cands:
        if id(c) in blocked:
            funnel["n_blocked_overlap"] += 1
            continue
        ts_e = c["ts_entry"]
        open_until = {s: te for s, te in open_until.items() if te > ts_e}
        if c["symbol"] in open_until:
            funnel["n_blocked_overlap"] += 1
            continue
        if len(open_until) >= B_MAX_OPEN_BOOK:
            funnel["n_blocked_overlap"] += 1
            continue
        open_until[c["symbol"]] = c["ts_exit"]
        trades.append(
            {
                "r": c["r"],
                "symbol": c["symbol"],
                "ts": c["ts_entry"],
                "direction": c["direction"],
                "setup": c["setup"],
            }
        )
        funnel["by_symbol"][c["symbol"]] = funnel["by_symbol"].get(c["symbol"], 0) + 1
        funnel["by_setup"][c["setup"]] = funnel["by_setup"].get(c["setup"], 0) + 1
        funnel["n_trades"] += 1

    return pack(
        "HYP-FX3-D1-TRENDDAY-ROC-BOOK-001",
        funnel,
        trades,
        "D1 trend-day + ROC persist multi-setup; RR2.5; FX3 caps; ≠ Outside/Donchian/EMA-PB",
    )


def write_docs(payload: dict) -> None:
    results = payload["results"]
    receipt = payload["receipt_sha256"]
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill = len(survivors) == 0

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — Multi-day H4–D1 swing thick book",
                "",
                "Date: 2026-07-15",
                "Lane: single; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`",
                "Panel: nested `cursor-grok-4.5-high-fast`",
                "",
                "## Problem",
                "",
                "Entry-state / exit / FRED / LNY / XS boards exhausted. Need a **new class**:",
                "multi-day swing thick enough that +$12 RT is a small fraction of R, with",
                "2–5/wk from **multi-symbol OR multi-setup portfolio** and frozen overlap",
                "rules — not densify of SB/RR2/entry/exit packs.",
                "",
                "## Design 1 — D1 ADX + H4 thrust3 continuation",
                "",
                "`HYP-FX3-D1ADX-H4-THRUST3-SWING-001`",
                "",
                "**Thesis:** D1 trend strength (ADX≥25 + DI align) plus same-direction H4",
                "three-bar thrust marks multi-day continuation; thick SL (1.75 ATR beyond",
                "leg) + RR=3; FX3 pool with ≤2 open and EUR/GBP same-day ADX arbiter.",
                "",
                "**Frozen:** universe EURUSD/GBPUSD/USDJPY; ADX14≥25; thrust step≥0.25 ATR;",
                "SL 1.75 ATR beyond 3-bar extreme (min 1.5 ATR from entry); RR=3; hold≤28 H4;",
                "≤1/symbol; ≤2 book; EUR+GBP same-dir same UTC day → higher D1 ADX only.",
                "",
                "## Design 2 — D1 trend-day + ROC persist multi-setup book",
                "",
                "`HYP-FX3-D1-TRENDDAY-ROC-BOOK-001`",
                "",
                "**Thesis:** Two independent D1 persistence setups (trend-day body dominance",
                "and short/medium ROC agreement) supply cadence; TD beats RP same day;",
                "thick SL 1.60 ATR; RR=2.5; same FX3 portfolio caps.",
                "",
                "**Frozen:** TD: range≥1.15 ATR_D1 and body/range≥0.70; RP: sign(ROC3)=sign(ROC10)",
                "and |Δ3|≥1.0 ATR_D1; entry next H4 open after D1 close; hold≤32 H4;",
                "EUR+GBP same-dir → larger range/ATR; TD>RP priority.",
                "",
                "## Model 0 policy",
                "",
                "Only if offline `PROBE_SURVIVOR`. Else withhold.",
                "",
                "## If both fail — next object class",
                "",
                "Multi-symbol **D1 volatility-regime breakout** (ATR14/ATR50 expansion",
                "threshold + close beyond prior 8-day extreme) with same frozen portfolio",
                "caps — still not channel/NR7/EMA-PB densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup clearance — Swing thick book board",
                "",
                "Status: **CLEARED** for offline probe only (2 objects).",
                "",
                "| ID | Mechanism | Explicit ≠ killed |",
                "|---|---|---|",
                "| `HYP-FX3-D1ADX-H4-THRUST3-SWING-001` | D1 ADX+DI + H4 3-bar thrust cont RR3 | ≠ H4 Outside/Engulf/Pin rev; ≠ Donchian; ≠ RV-compress/NR7; ≠ D1-EMA-H4-PB; ≠ Weekly-HL; ≠ H4-struct-M15; ≠ H4-balance; ≠ XS residual/mom; ≠ LNY/Asia coil; ≠ RR2 entry/exit |",
                "| `HYP-FX3-D1-TRENDDAY-ROC-BOOK-001` | D1 trend-day + ROC persist multi-setup RR2.5 | ≠ candle-pattern rev packs; ≠ Donchian/NR7 channel; ≠ EMA-PB reclaim; ≠ Weekly-HL break; ≠ XS factor books; ≠ SB impulse/thinrisk/magnet |",
                "",
                "Not cleared: densify / rescue of any killed family above.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# Merge memo — Swing thick book (nested critic)",
                "",
                "Date: 2026-07-15",
                "Panel: nested `cursor-grok-4.5-high-fast` (design) + lead execute",
                f"Receipt: `{receipt}`",
                "",
                "## Critic theses",
                "",
                "| Object | Class | Why thick+cadence path |",
                "|---|---|---|",
                "| A | D1 ADX + H4 thrust3 FX3 book | Large R vs +$12; portfolio caps for 2–5/wk |",
                "| B | D1 trend-day + ROC multi-setup FX3 | Independent persistence setups; frozen overlap |",
                "",
                "## Offline joint screen",
                "",
                "| ID | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
            ]
            + [
                (
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | **{r['verdict']}** |"
                )
                for r in results
            ]
            + [
                "",
                "Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.",
                "",
                "## Coordinator decision",
                "",
                f"- Survivors: **{len(survivors)}** / {len(results)}",
                "- Model 0: "
                + (
                    "WITHHELD (zero PROBE_SURVIVOR)"
                    if all_kill
                    else "AUTHORIZED for survivors only"
                ),
                "- Next if empty: D1 vol-regime breakout FX3 (not NR7/EMA-PB densify).",
                "- Best shelf RR2 `194548`. Cost GAP. Login not headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = [
        "# Offline probes — Swing thick book (H4–D1 multi-symbol)",
        "",
        f"Receipt: `{receipt}`",
        "",
        "| ID | N | PF | tpw | x1.5 | Verdict | Notes |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        lines.append(
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | **{r['verdict']}** | "
            f"{','.join(r['kill_notes']) or '—'} |"
        )
    lines += [
        "",
        "Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.",
        "",
        f"Model 0: {'WITHHELD' if all_kill else 'survivors only'}.",
        "",
        "Design: `readouts/20260715_SWING_THICK_BOOK_DESIGN_MEMO.md`",
        "Dedup: `readouts/20260715_SWING_THICK_BOOK_DEDUP_CLEARANCE.md`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — Swing thick book (H4–D1)",
                "",
                "Date: 2026-07-15",
                "Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / "
                + (
                    "`OFFLINE_ALL_KILL` / `NO_MODEL0`"
                    if all_kill
                    else "`PROBE_SURVIVOR_PRESENT` / Model0 armed survivors only"
                ),
                "",
                "## Executed",
                "",
                "1. Nested critic design (multi-day swing thick FX3 book).",
                "2. De-dup vs Outside/Engulf/Pin/Donchian/RV-compress/EMA-PB/Weekly-HL/…",
                "3. Offline joint screen ×2 a priori objects.",
                "4. Model 0 withheld unless PROBE_SURVIVOR.",
                "",
                "## Results",
                "",
            ]
            + [
                (
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → "
                    f"**{r['verdict']}** ({','.join(r['kill_notes']) or 'ok'})"
                )
                for r in results
            ]
            + [
                "",
                f"Receipt: `{receipt}`",
                "VN: `readouts/20260715_SWING_THICK_BOOK_VN_ACTION_BRIEF.md`",
                "",
                "## Decisions",
                "",
                "1. Do not densify ADX/thrust/ROC/TD params from this board.",
                "2. Do not reopen RR2 exit / FRED / LNY / XS densify.",
                "3. Best shelf remains RR2 `194548`. GOAL unmet.",
                "4. Cost freeze still GAP; login not headline.",
                "",
                "## Next",
                "",
            ]
            + (
                [
                    "Zero survivors — next independent object class:",
                    "**multi-symbol D1 volatility-regime breakout** (ATR14/ATR50 expansion",
                    "+ close beyond prior 8-day extreme) with frozen FX3 overlap caps.",
                ]
                if all_kill
                else [
                    "Run Model 0 only for PROBE_SURVIVOR IDs; keep losers frozen-killed.",
                ]
            )
            + ["",]
        ),
        encoding="utf-8",
    )

    vn = [
        "# Brief hành động (VN) — Swing thick book H4–D1",
        "",
        "- Class mới: **multi-day swing thick FX3 book** (không densify SB/RR2/exit/FRED/LNY/XS).",
        "- De-dup rõ vs Outside/Engulf/Pin/Donchian/RV-compress/EMA-PB/Weekly-HL.",
        "",
    ]
    for r in results:
        vn.append(
            f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
            f"×1.5={r['haircuts']['x1_5']['pf']} → **{r['verdict']}**"
        )
    vn += [
        "",
        f"- Survivors: **{len(survivors)}** → Model 0 "
        + ("WITHHELD." if all_kill else "armed cho survivor."),
        "- Shelf tốt nhất vẫn RR2 `194548`. Cost freeze vẫn GAP. GOAL unmet.",
        "- Login không phải headline.",
        "",
    ]
    if all_kill:
        vn += [
            "- Next class: **D1 vol-regime breakout FX3** (ATR14/ATR50 + 8-day extreme),",
            "  không densify ADX/thrust/TD/ROC từ board này.",
            "",
        ]
    OUT_VN.write_text("\n".join(vn), encoding="utf-8")


def append_registry(payload: dict) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with REG.open("a", encoding="utf-8") as f:
        for r in payload["results"]:
            state = "probe_survivor" if r["verdict"] == "PROBE_SURVIVOR" else "killed"
            rec = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": state,
                "verdict": r["verdict"],
                "lane": "swing_thick_book_20260715",
                "feature_family": r.get("family"),
                "symbol": r.get("symbol"),
                "timeframe": r.get("tf"),
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "metrics": r.get("metrics"),
                "validation": {
                    "cost_stress": "a_priori_+12_flat_proxy",
                    "kill_notes": r.get("kill_notes"),
                    "model0": r.get("model0"),
                    "dedup": "readouts/20260715_SWING_THICK_BOOK_DEDUP_CLEARANCE.md",
                    "panel": "readouts/20260715_SWING_THICK_BOOK_3CRITIC_MEMO.md",
                },
                "receipt_sha256": payload["receipt_sha256"],
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_SWING_THICK_BOOK_OFFLINE_PROBES.md",
                "updated_at": ts,
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                "reason": ",".join(r.get("kill_notes") or []) or r["verdict"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def patch_hot(payload: dict) -> None:
    results = payload["results"]
    receipt = payload["receipt_sha256"]
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill = len(survivors) == 0
    status = (
        "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `OFFLINE_ALL_KILL__NO_MODEL0`"
        if all_kill
        else "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `PROBE_SURVIVOR_PRESENT`"
    )
    lines = [
        f"- **SWING THICK BOOK CLOSEOUT (2026-07-15 ~08:55 ICT) — {status}.**",
        "  Post entry-state ALL_KILL; new class multi-day H4–D1 swing FX3 book",
        "  (not SB/RR2/exit/FRED/LNY/XS densify). Nested critic",
        "  `cursor-grok-4.5-high-fast`. Offline joint screen:",
    ]
    for r in results:
        lines.append(
            f"  {len(lines)-3}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    # fix numbering - rewrite cleaner
    lines = [
        f"- **SWING THICK BOOK CLOSEOUT (2026-07-15 ~08:55 ICT) — {status}.**",
        "  Post entry-state ALL_KILL; new class multi-day H4–D1 swing FX3 book",
        "  (not SB/RR2/exit/FRED/LNY/XS densify). Nested critic",
        "  `cursor-grok-4.5-high-fast`. Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    lines += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_SWING_THICK_BOOK_OFFLINE_PROBES.json`;",
        "  design `readouts/20260715_SWING_THICK_BOOK_DESIGN_MEMO.md`;",
        "  dedup `readouts/20260715_SWING_THICK_BOOK_DEDUP_CLEARANCE.md`;",
        "  closeout `readouts/20260715_SWING_THICK_BOOK_SESSION_CLOSEOUT.md`;",
        "  VN `readouts/20260715_SWING_THICK_BOOK_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify ADX/thrust/TD/ROC. Do **not** reopen exit/FRED/LNY/XS.",
    ]
    if all_kill:
        lines.append(
            "  Next class: D1 vol-regime breakout FX3 (ATR14/ATR50 + 8-day extreme)."
        )
    else:
        lines.append("  Model 0 armed for survivors only.")
    lines += [
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    bullet = "\n".join(lines)
    text = HOT.read_text(encoding="utf-8")
    # Update header timestamp
    header = (
        "# Hot Cache\n\n"
        "Updated: 2026-07-15 ~08:55 ICT | Swing thick book offline "
        + ("ALL_KILL; " if all_kill else "SURVIVOR; ")
        + "Real on; GOAL unmet\n\n"
        "## Active Truth\n\n"
    )
    marker = "## Active Truth\n"
    idx = text.find(marker)
    if idx >= 0:
        rest_start = idx + len(marker)
        # skip blank lines after marker
        rest = text[rest_start:]
        if rest.startswith("\n"):
            rest = rest[1:]
        new_text = header + bullet + rest
        # Avoid duplicating "## Active Truth" if rest already has prior bullets
        HOT.write_text(new_text, encoding="utf-8")
    else:
        HOT.write_text(header + bullet + text, encoding="utf-8")


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        books = {s: build_symbol_bundle(s) for s in UNIVERSE}
        r1 = probe_adx_thrust(books)
        r2 = probe_trendday_roc(books)
        results = [r1, r2]
        n_surv = sum(1 for r in results if r["verdict"] == "PROBE_SURVIVOR")
        payload: dict[str, Any] = {
            "schema": "swing_thick_book_offline_probes.v1",
            "created_at_utc": utc_now(),
            "authority": (
                "Owner R&D continue post entry-state ALL_KILL; "
                "EXO_FRED_DISPLACE_SPAM_PAUSED; offline-first; Model0 survivors only"
            ),
            "universe": list(UNIVERSE),
            "window": "2021.01.01-2025.12.31",
            "results": results,
            "n_survivors": n_surv,
            "model0_policy": "ARMED_ON_SURVIVOR" if n_surv else "WITHHELD_ZERO_SURVIVOR",
            "best_shelf": "RR2_20260714_194548",
            "next_class_if_empty": (
                "multi-symbol D1 vol-regime breakout "
                "(ATR14/ATR50 expansion + close beyond prior 8-day extreme)"
            ),
            "banned": [
                "SB/RR2 densify",
                "exit densify",
                "FRED",
                "LNY",
                "XS",
                "Outside/Engulf/Pin",
                "Donchian",
                "RV-compress/NR7",
                "D1-EMA-H4-PB",
                "Weekly-HL",
                "invent cost freeze",
            ],
            "goal": "unmet",
            "receipt_sha256": "PENDING",
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        payload["receipt_sha256"] = sha256_bytes(raw)
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        write_docs(payload)
        append_registry(payload)
        patch_hot(payload)
        print(
            json.dumps(
                {
                    "receipt": payload["receipt_sha256"],
                    "n_survivors": n_surv,
                    "verdicts": {r["hypothesis_id"]: r["verdict"] for r in results},
                    "metrics": {
                        r["hypothesis_id"]: {
                            "n": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["kill_notes"],
                            "funnel": r["funnel"],
                        }
                        for r in results
                    },
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
