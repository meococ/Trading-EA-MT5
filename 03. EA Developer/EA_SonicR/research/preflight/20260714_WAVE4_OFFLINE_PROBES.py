#!/usr/bin/env python3
"""Offline probes for Wave4 survivors behind EQHL intake-kill.

1) HYP-H1-RV-COMPRESS-BREAK-001
2) HYP-GBPJPY-LEAD-USDJPY-H1-001

Not Model 0. Kill-fast only. Synthetic +$12 cost haircut.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
DEPOSIT = 100_000.0
RISK_PCT = 0.50
BASE_COST = 12.0
WEEKS = (TO - FROM).days / 7.0


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def load_h1(symbol_candidates: tuple[str, ...]) -> tuple[str, list[Bar]]:
    for s in symbol_candidates:
        if not mt5.symbol_select(s, True):
            continue
        rates = mt5.copy_rates_range(s, mt5.TIMEFRAME_H1, FROM, TO)
        if rates is not None and len(rates) > 500:
            bars = [
                Bar(
                    t=datetime.fromtimestamp(int(r["time"])),
                    o=float(r["open"]),
                    h=float(r["high"]),
                    l=float(r["low"]),
                    c=float(r["close"]),
                )
                for r in rates
            ]
            return s, bars
    raise RuntimeError(f"no H1 rates for {symbol_candidates}: {mt5.last_error()}")


def atr(bars: list[Bar], i: int, period: int = 14) -> float:
    if i < period:
        return 0.0
    trs = []
    for j in range(i - period + 1, i + 1):
        prev = bars[j - 1].c
        trs.append(max(bars[j].h - bars[j].l, abs(bars[j].h - prev), abs(bars[j].l - prev)))
    return sum(trs) / period


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
            "pf": pf_of(cut) if cut else None,
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def simulate_path(
    bars: list[Bar],
    i_entry: int,
    direction: int,
    entry: float,
    sl: float,
    tp: float,
    max_hold: int,
    flat_hour: int,
) -> tuple[float, str, int]:
    risk = abs(entry - sl)
    if risk <= 0:
        return 0.0, "bad_sl", 0
    exit_px = entry
    reason = "max_hold"
    hold = 0
    for k in range(i_entry + 1, min(len(bars), i_entry + 1 + max_hold)):
        hold += 1
        bk = bars[k]
        if bk.t.hour >= flat_hour or bk.t.weekday() >= 4:
            exit_px = bk.o
            reason = "flat"
            break
        if direction > 0:
            if bk.l <= sl:
                exit_px, reason = sl, "sl"
                break
            if bk.h >= tp:
                exit_px, reason = tp, "tp"
                break
        else:
            if bk.h >= sl:
                exit_px, reason = sl, "sl"
                break
            if bk.l <= tp:
                exit_px, reason = tp, "tp"
                break
        exit_px = bk.c
    r_mult = (exit_px - entry) / risk if direction > 0 else (entry - exit_px) / risk
    pnl = DEPOSIT * RISK_PCT / 100.0 * r_mult
    return pnl, reason, hold


def verdict_from(n: int, tpw: float, pf0: float | None, cost: dict) -> tuple[str, str, list[str]]:
    kills: list[str] = []
    if n < 80:
        kills.append(f"N={n}<80")
    if tpw < 1.0 or tpw > 6.0:
        kills.append(f"tpw={tpw:.3f} not in [1,6]")
    if pf0 is None or pf0 < 1.00:
        kills.append(f"PF={pf0}<1.00")
    if kills:
        return "KILLED_AT_OFFLINE_PROBE", "WITHHELD_KILL_FAST", kills
    if cost["x1"]["pf"] is not None and cost["x1"]["pf"] < 1.00:
        kills.append(f"cost_x1_pf={cost['x1']['pf']}")
        return "KILLED_AT_OFFLINE_PROBE_COST_X1", "WITHHELD_KILL_FAST", kills
    return "PROBE_SURVIVE", "AUTHORIZED_IF_SURVIVE", kills


def probe_rv(bars: list[Bar], symbol: str) -> dict:
    SHORT, LONG, COMPRESS, DON, MIN_BODY, SL_ATR, RR = 6, 48, 0.55, 20, 0.40, 1.25, 2.5
    MAX_HOLD, FLAT, MAX_DAY = 24, 22, 2
    trades = []
    i = LONG + DON + 5
    day_count = 0
    last_day = None
    while i < len(bars) - 2:
        b1 = bars[i]  # signal bar[1]
        if b1.t.weekday() > 3 or b1.t.hour < 1 or b1.t.hour >= 21:
            i += 1
            continue
        if last_day != b1.t.date():
            last_day = b1.t.date()
            day_count = 0
        if day_count >= MAX_DAY:
            i += 1
            continue
        # compress on bars ending shift2 => index i-1
        i2 = i - 1
        if i2 - LONG < 0:
            i += 1
            continue
        short_rv = sum(bars[j].h - bars[j].l for j in range(i2 - SHORT + 1, i2 + 1)) / SHORT
        long_rv = sum(bars[j].h - bars[j].l for j in range(i2 - LONG + 1, i2 + 1)) / LONG
        if short_rv <= 0 or long_rv <= 0 or (short_rv / long_rv) > COMPRESS:
            i += 1
            continue
        # Donchian of shifts 2..21 => indices i-1 .. i-20
        hi = max(bars[j].h for j in range(i2 - DON + 1, i2 + 1))
        lo = min(bars[j].l for j in range(i2 - DON + 1, i2 + 1))
        a = atr(bars, i)
        if a <= 0:
            i += 1
            continue
        body = abs(b1.c - b1.o)
        if body < a * MIN_BODY:
            i += 1
            continue
        direction = 0
        if b1.c > hi:
            direction = 1
        elif b1.c < lo:
            direction = -1
        else:
            i += 1
            continue
        entry = b1.c
        sl = entry - a * SL_ATR if direction > 0 else entry + a * SL_ATR
        risk = abs(entry - sl)
        tp = entry + risk * RR if direction > 0 else entry - risk * RR
        pnl, reason, hold = simulate_path(bars, i, direction, entry, sl, tp, MAX_HOLD, FLAT)
        trades.append({"t": b1.t.isoformat(), "pnl": pnl, "exit": reason, "hold": hold})
        day_count += 1
        i += 1

    pnls = [t["pnl"] for t in trades]
    n = len(pnls)
    tpw = n / WEEKS
    pf0 = pf_of(pnls)
    cost = haircuts(pnls)
    verdict, model0, kills = verdict_from(n, tpw, pf0, cost)
    return {
        "hypothesis_id": "HYP-H1-RV-COMPRESS-BREAK-001",
        "ea": "EA_H1RVCompressBreak",
        "symbol": symbol,
        "tf": "H1",
        "n_trades": n,
        "tpw_elapsed": round(tpw, 4),
        "pf_zero_spread": pf0,
        "net_zero_spread": round(sum(pnls), 2),
        "exp_zero_spread": round(sum(pnls) / n, 4) if n else 0.0,
        "cost_stress_synthetic": {"base_cost_usd": BASE_COST, **cost},
        "kill_reasons": kills,
        "verdict": verdict,
        "model0": model0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def probe_gbpjpy(follow: list[Bar], lead: list[Bar], follow_sym: str, lead_sym: str) -> dict:
    THRESH, SL_ATR, RR, MAX_HOLD, FLAT, MAX_DAY = 1.0, 1.25, 2.5, 24, 22, 2
    # Align by timestamp
    lead_by_t = {b.t: b for b in lead}
    trades = []
    i = 20
    day_count = 0
    last_day = None
    while i < len(follow) - 2:
        b1 = follow[i]
        if b1.t.weekday() > 3 or b1.t.hour < 7 or b1.t.hour >= 20:
            i += 1
            continue
        if last_day != b1.t.date():
            last_day = b1.t.date()
            day_count = 0
        if day_count >= MAX_DAY:
            i += 1
            continue
        # lead bar[2] older than follower bar[1]
        # find lead bar with time < b1.t, then its prior
        # Approximate: lead at same clock as follow[i-1] is bar[2] relative if synced
        t2 = follow[i - 1].t
        t3 = follow[i - 2].t
        if t2 not in lead_by_t or t3 not in lead_by_t:
            i += 1
            continue
        if t2 >= b1.t:
            i += 1
            continue
        lb2 = lead_by_t[t2]
        lb3 = lead_by_t[t3]
        # lead ATR at t2
        # find index in lead
        # cheaper: ATR from lead bars around t2
        # build local window from lead list via binary-ish scan
        # Use follow indices mapped: assume aligned H1
        lead_i2 = None
        for li, lb in enumerate(lead):
            if lb.t == t2:
                lead_i2 = li
                break
        if lead_i2 is None or lead_i2 < 14:
            i += 1
            continue
        latr = atr(lead, lead_i2)
        if latr <= 0:
            i += 1
            continue
        move = lb2.c - lb3.c
        if abs(move) < latr * THRESH:
            i += 1
            continue
        direction = 1 if move > 0 else -1
        a = atr(follow, i)
        if a <= 0:
            i += 1
            continue
        entry = b1.c
        sl = entry - a * SL_ATR if direction > 0 else entry + a * SL_ATR
        risk = abs(entry - sl)
        tp = entry + risk * RR if direction > 0 else entry - risk * RR
        pnl, reason, hold = simulate_path(follow, i, direction, entry, sl, tp, MAX_HOLD, FLAT)
        trades.append({"t": b1.t.isoformat(), "pnl": pnl, "exit": reason, "hold": hold, "dir": direction})
        day_count += 1
        i += 1

    pnls = [t["pnl"] for t in trades]
    n = len(pnls)
    tpw = n / WEEKS
    pf0 = pf_of(pnls)
    cost = haircuts(pnls)
    verdict, model0, kills = verdict_from(n, tpw, pf0, cost)
    return {
        "hypothesis_id": "HYP-GBPJPY-LEAD-USDJPY-H1-001",
        "ea": "EA_H1GBPJPYLead",
        "symbol": follow_sym,
        "lead_symbol": lead_sym,
        "tf": "H1",
        "n_trades": n,
        "tpw_elapsed": round(tpw, 4),
        "pf_zero_spread": pf0,
        "net_zero_spread": round(sum(pnls), 2),
        "exp_zero_spread": round(sum(pnls) / n, 4) if n else 0.0,
        "cost_stress_synthetic": {"base_cost_usd": BASE_COST, **cost},
        "kill_reasons": kills,
        "verdict": verdict,
        "model0": model0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(payload["hypothesis_id"], payload["verdict"],
          "N=", payload["n_trades"], "PF=", payload["pf_zero_spread"],
          "tpw=", payload["tpw_elapsed"])
    print("  sha", hashlib.sha256(path.read_bytes()).hexdigest().upper())


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    uj_sym, uj = load_h1(("USDJPY", "USDJPY+"))
    gj_sym, gj = load_h1(("GBPJPY", "GBPJPY+"))
    mt5.shutdown()

    rv = probe_rv(uj, uj_sym)
    write(PRE / "20260714_H1_RV_COMPRESS_BREAK_OFFLINE_PROBE.json", rv)

    gjp = probe_gbpjpy(uj, gj, uj_sym, gj_sym)
    write(PRE / "20260714_GBPJPY_LEAD_USDJPY_H1_OFFLINE_PROBE.json", gjp)


if __name__ == "__main__":
    main()
