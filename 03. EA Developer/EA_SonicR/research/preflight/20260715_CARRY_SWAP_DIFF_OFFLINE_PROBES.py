#!/usr/bin/env python3
"""Next class after D1 vol-regime ALL_KILL — carry/swap-aware multi-day differential.

NEW contracts (not V8 weekly/daily/rate-event/vol retune; not USBILL):
  1) HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001
  2) HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001

Broker SWAP_LONG/SHORT schedule: NOT reconstructable in workspace → G3 rate-diff
/365 funding proxy only (labeled research-proxy). Model 0 iff PROBE_SURVIVOR.
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
RATES_CSV = ROOT / "03. EA Developer" / "EA_CarryPublicRates" / "carry_rates_d1.csv"

OUT_JSON = PRE / "20260715_CARRY_SWAP_DIFF_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_CARRY_SWAP_DIFF_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_CARRY_SWAP_DIFF_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_CARRY_SWAP_DIFF_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_CARRY_SWAP_DIFF_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_CARRY_SWAP_DIFF_VN_ACTION_BRIEF.md"
OUT_CRITIC = READ / "20260715_CARRY_SWAP_DIFF_3CRITIC_MEMO.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY")

# Object 1 — Mon→Thu funding-proxy harvest
CARRY_MIN_PP = 0.50
FUND_MIN_PIPS = 1.5
HOLD_NIGHTS = 3
HARVEST_SL_ATR = 1.8
HARVEST_MAX_OPEN = 3

# Object 2 — flush→carry ride
FLUSH_CARRY_MIN = 0.35
FLUSH_LOOKBACK = 5
FLUSH_ATR_K = 1.0
FLUSH_SL_ATR = 1.6
FLUSH_RR = 2.5
FLUSH_MAX_HOLD = 32
FLUSH_MAX_OPEN = 2


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float]) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
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
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(n / WEEKS, 4) if WEEKS else None,
    }


def joint_verdict(m: dict, hc: dict) -> tuple[str, list[str]]:
    notes: list[str] = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
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
    return "KILLED_AT_OFFLINE_PROBE", notes or ["joint_screen_miss"]


def atr_wilder(h, l, c, length=14):
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


def load_tf(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol}: {mt5.last_error()}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def weekday(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).weekday()


def hour_utc(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def pair_carry(symbol: str, usd: float, eur: float, gbp: float, jpy: float) -> float:
    if symbol == "EURUSD":
        return eur - usd
    if symbol == "GBPUSD":
        return gbp - usd
    if symbol == "USDJPY":
        return usd - jpy
    raise KeyError(symbol)


def load_rates_lagged() -> dict[str, tuple[list[date], list[float]]]:
    """Observation-date panel → available_at with V8 lags (+1 USD/EUR/GBP, +2 JPY)."""
    raw: dict[str, dict[date, float]] = {k: {} for k in ("usd", "eur", "gbp", "jpy")}
    with RATES_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                d = date.fromisoformat(row["date"][:10])
                for k in raw:
                    v = float(row[k])
                    if math.isfinite(v):
                        raw[k][d] = v
            except (KeyError, ValueError, TypeError):
                continue
    lags = {"usd": 1, "eur": 1, "gbp": 1, "jpy": 2}
    out: dict[str, tuple[list[date], list[float]]] = {}
    for k, series in raw.items():
        lag = lags[k]
        items = sorted((d + timedelta(days=lag), v) for d, v in series.items())
        out[k] = ([d for d, _ in items], [v for _, v in items])
    return out


def asof(series: tuple[list[date], list[float]], d: date) -> float | None:
    dates, vals = series
    if not dates:
        return None
    i = bisect.bisect_right(dates, d) - 1
    if i < 0:
        return None
    return vals[i]


def rates_on(
    lagged: dict[str, tuple[list[date], list[float]]], d: date
) -> tuple[float, float, float, float] | None:
    vals = []
    for k in ("usd", "eur", "gbp", "jpy"):
        v = asof(lagged[k], d)
        if v is None:
            return None
        vals.append(v)
    return vals[0], vals[1], vals[2], vals[3]


def funding_pips(symbol: str, spot: float, carry_pp: float, nights: int) -> float:
    """Research proxy: |spot * carry%/100 / 365 * nights| / pip_size. Not broker swap."""
    daily = abs(spot * (carry_pp / 100.0) / 365.0) * nights
    return daily / pip_size(symbol)


def resolve_r(direction, entry, sl, tp, i0, h, l, c, max_hold, rr_hit):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        if direction > 0:
            if l[j] <= sl:
                return -1.0
            if tp is not None and h[j] >= tp:
                return float(rr_hit)
        else:
            if h[j] >= sl:
                return -1.0
            if tp is not None and l[j] <= tp:
                return float(rr_hit)
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def pnls_from_r(trades):
    bal = DEPOSIT
    out = []
    for t in trades:
        pnl = bal * RISK_FRAC * t["r"]
        out.append(pnl)
        bal += pnl
    return out


def pack(hid, funnel, trades, note="", family="carry_swap_diff_fx3"):
    pnls = pnls_from_r(trades)
    m, hc = metrics(pnls), haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "symbol": "BOOK:EUR+GBP+USDJPY",
        "tf": "D1→H4",
        "family": family,
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "note": note,
        "n_trades_raw": len(trades),
    }


def build(symbol):
    h4 = load_tf(symbol, mt5.TIMEFRAME_H4)
    d1 = load_tf(symbol, mt5.TIMEFRAME_D1)
    h4["atr"] = atr_wilder(h4["high"], h4["low"], h4["close"], 14)
    d1["atr14"] = atr_wilder(d1["high"], d1["low"], d1["close"], 14)
    return {"symbol": symbol, "h4": h4, "d1": d1}


def portfolio_select(cands, funnel, max_open: int):
    cands = sorted(cands, key=lambda x: (x["ts_entry"], -x["score"], x["symbol"]))
    trades = []
    open_until: dict[str, int] = {}
    for c in cands:
        ts = c["ts_entry"]
        open_until = {s: te for s, te in open_until.items() if te > ts}
        if c["symbol"] in open_until or len(open_until) >= max_open:
            funnel["n_blocked_overlap"] += 1
            continue
        open_until[c["symbol"]] = c["ts_exit"]
        trades.append(
            {
                "r": c["r"],
                "symbol": c["symbol"],
                "ts": ts,
                "direction": c["direction"],
            }
        )
        funnel["by_symbol"][c["symbol"]] = funnel["by_symbol"].get(c["symbol"], 0) + 1
        funnel["n_trades"] += 1
    return trades


def find_monday_h4(h4, d: date):
    """First closed H4 bar on date d with hour>=08 UTC (decision on closed bar)."""
    for i in range(len(h4["time"])):
        ts = int(h4["time"][i])
        dt = datetime.fromtimestamp(ts, timezone.utc)
        if dt.date() != d:
            continue
        if dt.weekday() != 0:
            continue
        if dt.hour >= 8:
            return i
    return None


def find_thu_exit_idx(h4, from_i: int) -> int:
    """Last H4 on Thursday with hour<=16 UTC after entry, else last eligible."""
    best = from_i
    for j in range(from_i, len(h4["time"])):
        dt = datetime.fromtimestamp(int(h4["time"][j]), timezone.utc)
        if dt.weekday() > 3:
            break
        if dt.weekday() == 3 and dt.hour <= 16:
            best = j
        elif dt.weekday() < 3:
            best = j
    return best


def d1_index_on_or_before(d1, d: date) -> int | None:
    best = None
    for i in range(len(d1["time"])):
        di = datetime.fromtimestamp(int(d1["time"][i]), timezone.utc).date()
        if di <= d:
            best = i
        else:
            break
    return best


def probe_monthu_harvest(books, lagged):
    """Mon→Thu with-carry harvest under funding-proxy floor."""
    funnel = {
        "n_armed": 0,
        "n_trades": 0,
        "n_blocked_overlap": 0,
        "n_funding_fail": 0,
        "n_carry_fail": 0,
        "by_symbol": {},
    }
    cands = []
    # Iterate Mondays via EURUSD H4 calendar
    ref = books["EURUSD"]["h4"]
    seen_weeks: set[str] = set()
    for i in range(len(ref["time"])):
        ts = int(ref["time"][i])
        dt = datetime.fromtimestamp(ts, timezone.utc)
        if dt.weekday() != 0 or dt.hour < 8:
            continue
        week_id = dt.strftime("%Y-%W")
        if week_id in seen_weeks:
            continue
        seen_weeks.add(week_id)
        d = dt.date()
        rates = rates_on(lagged, d)
        if rates is None:
            continue
        usd, eur, gbp, jpy = rates
        for sym, b in books.items():
            h4, d1 = b["h4"], b["d1"]
            hi = find_monday_h4(h4, d)
            if hi is None or hi >= len(h4["time"]) - 2:
                continue
            carry = pair_carry(sym, usd, eur, gbp, jpy)
            if abs(carry) < CARRY_MIN_PP:
                funnel["n_carry_fail"] += 1
                continue
            spot = float(h4["open"][hi])
            fund = funding_pips(sym, spot, carry, HOLD_NIGHTS)
            if fund < FUND_MIN_PIPS:
                funnel["n_funding_fail"] += 1
                continue
            direction = 1 if carry > 0 else -1
            a_h = h4["atr"][hi]
            if math.isnan(a_h) or a_h <= 0:
                continue
            funnel["n_armed"] += 1
            entry = spot
            sl = entry - direction * HARVEST_SL_ATR * a_h
            thu_i = find_thu_exit_idx(h4, hi)
            max_hold = max(1, thu_i - hi + 1)
            # Time-stop only (tp=None); SL can cut early
            r = resolve_r(
                direction,
                entry,
                sl,
                None,
                hi,
                h4["high"],
                h4["low"],
                h4["close"],
                max_hold,
                0.0,
            )
            if r is None:
                continue
            # Sign-flip check at Thursday: if carry flipped, close at last bar (already in r path via time)
            rates_thu = rates_on(
                lagged,
                datetime.fromtimestamp(int(h4["time"][thu_i]), timezone.utc).date(),
            )
            if rates_thu is not None:
                c2 = pair_carry(sym, *rates_thu)
                if c2 * carry <= 0:
                    # flatten at first bar where rates available that day — approx mid-hold close
                    mid = hi + max(1, (thu_i - hi) // 2)
                    risk = abs(entry - sl)
                    if risk > 0:
                        r = direction * (float(h4["close"][mid]) - entry) / risk
            cands.append(
                {
                    "ts_entry": int(h4["time"][hi]),
                    "ts_exit": int(h4["time"][thu_i]),
                    "symbol": sym,
                    "direction": direction,
                    "score": float(fund),
                    "r": float(r),
                    "day": day_key(int(h4["time"][hi])),
                }
            )
    trades = portfolio_select(cands, funnel, HARVEST_MAX_OPEN)
    return pack(
        "HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001",
        funnel,
        trades,
        "Mon→Thu with-carry; |carry|≥0.50pp; funding proxy ≥1.5 pip/3n; SL 1.8 ATR_H4",
        family="carry_fundproxy_monthu_harvest",
    )


def probe_flush_mr(books, lagged):
    """Adverse D1 flush against carry → ride WITH carry multi-day."""
    funnel = {
        "n_armed": 0,
        "n_trades": 0,
        "n_blocked_overlap": 0,
        "n_carry_fail": 0,
        "by_symbol": {},
    }
    cands = []
    for sym, b in books.items():
        d1, h4 = b["d1"], b["h4"]
        n = len(d1["time"])
        for i in range(max(20, FLUSH_LOOKBACK + 1), n - 1):
            if weekday(int(d1["time"][i])) >= 5:
                continue
            d = datetime.fromtimestamp(int(d1["time"][i]), timezone.utc).date()
            rates = rates_on(lagged, d)
            if rates is None:
                continue
            carry = pair_carry(sym, *rates)
            if abs(carry) < FLUSH_CARRY_MIN:
                funnel["n_carry_fail"] += 1
                continue
            direction = 1 if carry > 0 else -1  # WITH carry
            a14 = d1["atr14"][i]
            if math.isnan(a14) or a14 <= 0:
                continue
            # Adverse flush: price moved against carry over prior FLUSH_LOOKBACK bars
            window = slice(i - FLUSH_LOOKBACK, i + 1)
            if direction > 0:
                # long carry → adverse = sold off → close near period low extreme
                extreme = float(min(d1["low"][window]))
                move = float(d1["close"][i - FLUSH_LOOKBACK]) - float(d1["close"][i])
                if move < FLUSH_ATR_K * a14:
                    continue
                # require close within 0.25 ATR of extreme low (flush end)
                if float(d1["close"][i]) > extreme + 0.25 * a14:
                    continue
            else:
                extreme = float(max(d1["high"][window]))
                move = float(d1["close"][i]) - float(d1["close"][i - FLUSH_LOOKBACK])
                if move < FLUSH_ATR_K * a14:
                    continue
                if float(d1["close"][i]) < extreme - 0.25 * a14:
                    continue
            funnel["n_armed"] += 1
            entry_ts_min = int(d1["time"][i + 1])
            hi = None
            for k in range(len(h4["time"])):
                if int(h4["time"][k]) >= entry_ts_min:
                    hi = k
                    break
            if hi is None or hi >= len(h4["time"]) - 2:
                continue
            a_h = h4["atr"][hi]
            if math.isnan(a_h) or a_h <= 0:
                continue
            entry = float(h4["open"][hi])
            sl = extreme - direction * FLUSH_SL_ATR * a_h
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + direction * FLUSH_RR * risk
            r = resolve_r(
                direction,
                entry,
                sl,
                tp,
                hi,
                h4["high"],
                h4["low"],
                h4["close"],
                FLUSH_MAX_HOLD,
                FLUSH_RR,
            )
            if r is None:
                continue
            # exit ts approx
            te = int(h4["time"][min(hi + FLUSH_MAX_HOLD - 1, len(h4["time"]) - 1)])
            for j in range(hi, min(hi + FLUSH_MAX_HOLD, len(h4["time"]))):
                if direction > 0 and (
                    h4["low"][j] <= sl or h4["high"][j] >= tp
                ):
                    te = int(h4["time"][j])
                    break
                if direction < 0 and (
                    h4["high"][j] >= sl or h4["low"][j] <= tp
                ):
                    te = int(h4["time"][j])
                    break
            cands.append(
                {
                    "ts_entry": int(h4["time"][hi]),
                    "ts_exit": te,
                    "symbol": sym,
                    "direction": direction,
                    "score": float(abs(carry)),
                    "r": float(r),
                    "day": day_key(int(d1["time"][i])),
                }
            )
    trades = portfolio_select(cands, funnel, FLUSH_MAX_OPEN)
    return pack(
        "HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001",
        funnel,
        trades,
        "5d adverse flush ≥1.0 ATR_D1 vs carry → ride WITH carry; RR2.5; ≤2 book",
        family="carry_flush_mr_multiday",
    )


def append_registry(results: list[dict], receipt: str) -> None:
    ts = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "parent_candidate": "post_d1_volregime_carry_swap_diff_20260715",
                "feature_family": r["family"],
                "lane": "carry_swap_aware_multiday_20260715",
                "setup_type": r["note"],
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4/D1",
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "source_provenance": "G3 lagged rates carry_rates_d1 + Demo OHLC; no broker swap schedule",
                "prereg_path": None,
                "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "run_ids": [],
                "metrics": {
                    "trades": r["metrics"]["n"],
                    "pf": r["metrics"]["pf"],
                    "tpw": r["metrics"]["tpw"],
                    "pf_cost_x1_5": r["haircuts"]["x1_5"]["pf"],
                },
                "validation": {
                    "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                    "receipt_sha256": receipt,
                    "status": r["verdict"],
                },
                "verdict": r["verdict"],
                "reason": ",".join(r["kill_notes"]),
                "updated_at": ts,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results: list[dict], receipt: str, intake: dict) -> None:
    all_kill = all(r["verdict"] != "PROBE_SURVIVOR" for r in results)
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — Carry/swap-aware multi-day differential FX3",
                "",
                "Date: 2026-07-15",
                "Parent: D1 vol-regime break ALL_KILL → named next class",
                "",
                "## Data",
                "- G3 rates: `EA_CarryPublicRates/carry_rates_d1.csv` with V8 lags",
                "  (+1 USD/EUR/GBP, +2 JPY).",
                "- Broker SWAP_LONG/SHORT schedule: **GAP** (deal `swap` cols only).",
                "  Funding = research proxy `|spot×carry%/365×nights|/pip` — not QFSI swap.",
                "",
                "## Design 1 — Mon→Thu funding-proxy harvest",
                "`HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001`",
                f"Monday H4≥08 UTC; |carry|≥{CARRY_MIN_PP} pp; funding proxy ≥{FUND_MIN_PIPS}",
                f"pip over {HOLD_NIGHTS} nights; hold with-carry to Thursday ≤16 UTC;",
                f"SL {HARVEST_SL_ATR}×ATR14_H4; ≤1/symbol ≤{HARVEST_MAX_OPEN} book.",
                "",
                "## Design 2 — Flush then ride carry",
                "`HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001`",
                f"|carry|≥{FLUSH_CARRY_MIN}; 5d adverse move ≥{FLUSH_ATR_K}×ATR14_D1 ending",
                f"at flush extreme; enter WITH carry next H4; SL {FLUSH_SL_ATR}×ATR_H4;",
                f"RR={FLUSH_RR}; hold≤{FLUSH_MAX_HOLD} H4; ≤{FLUSH_MAX_OPEN} book.",
                "",
                "## ≠ killed",
                "≠ V8_CARRY_DIFF (Friday single winner); ≠ V8_CARRY_DAILY_RANK (deadband",
                "long-max/short-min); ≠ V8_CARRY_RATE_EVENT_5BP; ≠ V8_CARRY_VOL_REGIME",
                "(Menkhoff); ≠ USBILL slope→USD basket.",
                "",
                "## If both fail — next object class",
                "Microstructure only if research-grade cost exists; else greenfield",
                "outside kill shelf (e.g. CME 6J spot−fwd basis gate) — not V8 carry retune,",
                "not D1 breakout densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup — Carry/swap-aware multi-day differential",
                "",
                f"Status: **{intake['status']}**",
                "",
                "| ID | ≠ killed |",
                "|---|---|",
                "| `HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001` | ≠ weekly single-pair Friday rebalance; ≠ daily rank deadband; ≠ 5bp event; ≠ Menkhoff vol; ≠ USBILL |",
                "| `HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001` | ≠ rank/rebalance books; trigger = price flush vs carry; ≠ USBILL basket; ≠ vol-regime H4 strip |",
                "",
                "## Intake ruling",
                intake["ruling"],
                "",
                "## Broker swap",
                "No reconstructable SWAP_LONG/SHORT history → funding proxy from G3 only.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_CRITIC.write_text(
        "\n".join(
            [
                "# 3-critic merge — Carry/swap-aware differential",
                "",
                "Nested: `cursor-grok-4.5-high-fast` design critic.",
                "",
                "| Role | Call |",
                "|---|---|",
                "| Trader | Mon→Thu funding harvest + flush→carry ride are mechanism-new vs V8 rank |",
                "| Quant | Joint thick+cadence+$12; Model 0 only PROBE_SURVIVOR |",
                "| MQL5/MT5 | Closed-bar H4/D1; lagged rates; no broker-swap claim |",
                "",
                f"Intake: {intake['status']}. Probe offline executed.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = [
        "# Offline probes — Carry/swap-aware multi-day differential",
        "",
        f"Receipt: `{receipt}`",
        f"Intake: **{intake['status']}**",
        "",
        "| ID | N | PF | tpw | x1.5 | Verdict | Notes |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        lines.append(
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | **{r['verdict']}** | "
            f"{','.join(r['kill_notes'])} |"
        )
    lines += ["", f"Model 0: {'WITHHELD' if all_kill else 'survivors only'}.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    status = (
        "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `OFFLINE_ALL_KILL` / `NO_MODEL0`"
        if all_kill
        else "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `PROBE_SURVIVOR_PRESENT`"
    )
    next_class = (
        "Microstructure **only if** research-grade cost exists; else CME 6J "
        "spot−fwd basis multi-day sleeve (panel on disk) — not V8 carry densify, "
        "not D1 breakout densify."
        if all_kill
        else "Model 0 for survivors only; do not densify frozen constants."
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — Carry/swap-aware multi-day differential",
                "",
                "Date: 2026-07-15",
                f"Status: {status}",
                "",
            ]
            + [
                f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → **{r['verdict']}**"
                for r in results
            ]
            + [
                "",
                f"Receipt: `{receipt}`",
                "Do not densify carry pp / funding pip floor / flush K / RR from this board.",
                "Best shelf RR2 `194548`. Cost GAP. Login not headline. GOAL unmet.",
                "",
                "## Next",
                next_class,
                "",
            ]
        ),
        encoding="utf-8",
    )

    vn_lines = [
        "# VN action brief — Carry/swap-aware differential",
        "",
        f"- Intake de-dup: **{intake['status']}** (≠ V8 weekly/daily/5bp/vol; ≠ USBILL).",
        f"- Broker swap schedule: **GAP** → dùng G3 funding proxy.",
        f"- Offline 2 object → **{'OFFLINE_ALL_KILL / NO_MODEL0' if all_kill else 'có PROBE_SURVIVOR'}**:",
    ]
    for r in results:
        vn_lines.append(
            f"  - `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
            f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
        )
    vn_lines += [
        f"- Receipt `{receipt[:16]}…`",
        "- Không densify ngưỡng carry/funding/flush từ board này.",
        f"- Next: {next_class}",
        "- Best shelf RR2 `194548`. Cost GAP. Login không phải headline. GOAL unmet.",
        "",
    ]
    OUT_VN.write_text("\n".join(vn_lines), encoding="utf-8")

    # hot.md prepend (same pattern as vol-regime board)
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill2 = not survivors
    status = (
        "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `OFFLINE_ALL_KILL__NO_MODEL0`"
        if all_kill2
        else "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `PROBE_SURVIVOR_PRESENT`"
    )
    stamp = "2026-07-15 ~09:25 ICT"
    lines = [
        f"- **CARRY/SWAP-AWARE DIFF CLOSEOUT ({stamp}) — {status}.**",
        "  Named next class after D1 vol-regime ALL_KILL. Nested critic",
        "  `cursor-grok-4.5-high-fast`. G3 lagged rates; broker swap schedule GAP.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    lines += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_CARRY_SWAP_DIFF_OFFLINE_PROBES.json`;",
        "  design `readouts/20260715_CARRY_SWAP_DIFF_DESIGN_MEMO.md`;",
        "  dedup `readouts/20260715_CARRY_SWAP_DIFF_DEDUP_CLEARANCE.md`;",
        "  closeout `readouts/20260715_CARRY_SWAP_DIFF_SESSION_CLOSEOUT.md`;",
        "  VN `readouts/20260715_CARRY_SWAP_DIFF_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify carry pp / funding floor / flush K / RR.",
        "  Do **not** retune V8 weekly/daily/5bp/vol or USBILL.",
        f"  Next class: {next_class}",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    bullet = "\n".join(lines)
    header = (
        "# Hot Cache\n\n"
        f"Updated: {stamp} | Carry/swap-aware differential offline "
        + ("ALL_KILL; " if all_kill2 else "SURVIVOR; ")
        + "Real on; GOAL unmet\n\n"
        "## Active Truth\n\n"
    )
    text = HOT.read_text(encoding="utf-8")
    marker = "## Active Truth\n"
    idx = text.find(marker)
    if idx >= 0:
        rest = text[idx + len(marker) :]
        if rest.startswith("\n"):
            rest = rest[1:]
        HOT.write_text(header + bullet + rest, encoding="utf-8")
    else:
        HOT.write_text(header + bullet + text, encoding="utf-8")


def intake_ruling() -> dict:
    """A priori intake: CLEARED unless pure duplicate of killed V8/USBILL."""
    return {
        "status": "CLEARED",
        "ruling": (
            "Not pure duplicate: (1) Mon→Thu multi-symbol funding-floor harvest ≠ "
            "Friday single-winner weekly / daily deadband rank / 5bp event / Menkhoff; "
            "(2) flush→WITH-carry RR book ≠ rank rebalance and ≠ USBILL slope basket. "
            "Broker swap schedule absent → funding proxy labeled research-only."
        ),
    }


def main() -> int:
    intake = intake_ruling()
    if intake["status"] == "INTAKE_KILL":
        # pivot path — should not hit for this design
        payload = {
            "status": "INTAKE_KILL",
            "intake": intake,
            "generated_at_utc": utc_now(),
        }
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        OUT_JSON.write_bytes(raw)
        print("INTAKE_KILL", sha256_bytes(raw))
        return 2

    if not mt5.initialize():
        raise SystemExit(f"mt5 init fail: {mt5.last_error()}")
    try:
        lagged = load_rates_lagged()
        books = {s: build(s) for s in UNIVERSE}
        results = [
            probe_monthu_harvest(books, lagged),
            probe_flush_mr(books, lagged),
        ]
    finally:
        mt5.shutdown()

    payload: dict[str, Any] = {
        "schema": "carry_swap_diff_offline_probes.v1",
        "generated_at_utc": utc_now(),
        "window": {"from": FROM.isoformat(), "to": TO.isoformat(), "weeks": WEEKS},
        "cost": {"base_rt_usd": BASE_COST, "grade": "UNVERIFIED_OFFLINE_PROXY_PLUS12"},
        "rates_panel": str(RATES_CSV),
        "broker_swap_schedule": "GAP_USE_G3_FUNDING_PROXY",
        "intake": intake,
        "joint_screen": {
            "n_min": 80,
            "tpw": [1.5, 6.0],
            "pf_min": 1.20,
            "x1_5_pf_min": 1.15,
        },
        "results": results,
        "model0_policy": "PROBE_SURVIVOR_ONLY",
        "next_class_if_empty": (
            "microstructure if research-grade cost else CME 6J spot-fwd basis "
            "multiday — not V8 carry densify"
        ),
        "receipt_sha256": None,
    }
    # Stable receipt: hash payload without receipt field, then embed.
    stub = {k: v for k, v in payload.items() if k != "receipt_sha256"}
    receipt = sha256_bytes(json.dumps(stub, indent=2, sort_keys=True).encode("utf-8"))
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    write_docs(results, receipt, intake)
    append_registry(results, receipt)

    print("receipt", receipt)
    for r in results:
        print(
            r["hypothesis_id"],
            r["verdict"],
            r["metrics"],
            r["haircuts"]["x1_5"],
            r["kill_notes"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
