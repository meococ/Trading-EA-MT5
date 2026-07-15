#!/usr/bin/env python3
"""Offline probe — HYP-H1-EMA-STACK-PB-001 (closed-bar mirror).

H1 EMA8/21/50 stack + pullback touch EMA21 then close resume; RR=2.5.
Kill-fast only. Not Model 0.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(r"d:\Trading EA MT5")
OUT = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_H1_EMA_STACK_PB_OFFLINE_PROBE.json"
)
FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
DEPOSIT = 100_000.0
RISK_PCT = 0.50
BASE_COST = 12.0
RR = 2.5
SL_ATR = 1.10
MAX_HOLD = 24
FLAT = 22
MAX_DAY = 2
TOUCH_ATR = 0.25  # how close to EMA21 counts as touch


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def ema_series(closes: list[float], period: int) -> list[float]:
    out = [0.0] * len(closes)
    if len(closes) < period:
        return out
    k = 2.0 / (period + 1)
    s = sum(closes[:period]) / period
    for i in range(period - 1):
        out[i] = 0.0
    out[period - 1] = s
    for i in range(period, len(closes)):
        s = closes[i] * k + s * (1 - k)
        out[i] = s
    return out


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


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    symbol = None
    rates = None
    for s in ("USDJPY", "USDJPY+"):
        if mt5.symbol_select(s, True):
            rates = mt5.copy_rates_range(s, mt5.TIMEFRAME_H1, FROM, TO)
            if rates is not None and len(rates) > 500:
                symbol = s
                break
    mt5.shutdown()
    if not symbol or rates is None:
        raise SystemExit("no rates")

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
    closes = [b.c for b in bars]
    e8 = ema_series(closes, 8)
    e21 = ema_series(closes, 21)
    e50 = ema_series(closes, 50)

    trades = []
    i = 60
    day_count = 0
    last_day = None
    while i < len(bars) - 2:
        b = bars[i]
        if b.t.weekday() > 3 or b.t.hour < 1 or b.t.hour >= 21:
            i += 1
            continue
        if last_day != b.t.date():
            last_day = b.t.date()
            day_count = 0
        if day_count >= MAX_DAY:
            i += 1
            continue
        if e50[i] <= 0:
            i += 1
            continue
        a = atr(bars, i)
        if a <= 0:
            i += 1
            continue

        bull = e8[i] > e21[i] > e50[i]
        bear = e8[i] < e21[i] < e50[i]
        if not bull and not bear:
            i += 1
            continue

        # pullback touch EMA21 then close resume with stack
        touch = abs(b.l - e21[i]) <= a * TOUCH_ATR or abs(b.h - e21[i]) <= a * TOUCH_ATR
        # also allow wick through EMA21 then reclaim
        through_bull = b.l <= e21[i] <= b.h
        through_bear = b.l <= e21[i] <= b.h
        if bull:
            if not (through_bull or touch):
                i += 1
                continue
            if b.c <= e21[i]:  # must close back above EMA21
                i += 1
                continue
            direction = 1
        else:
            if not (through_bear or touch):
                i += 1
                continue
            if b.c >= e21[i]:
                i += 1
                continue
            direction = -1

        entry = b.c
        sl = entry - a * SL_ATR if direction > 0 else entry + a * SL_ATR
        risk = abs(entry - sl)
        tp = entry + risk * RR if direction > 0 else entry - risk * RR

        exit_px = entry
        reason = "max_hold"
        hold = 0
        for k in range(i + 1, min(len(bars), i + 1 + MAX_HOLD)):
            hold += 1
            bk = bars[k]
            if bk.t.hour >= FLAT or bk.t.weekday() >= 4:
                exit_px, reason = bk.o, "flat"
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
        trades.append(pnl)
        day_count += 1
        i += 1

    n = len(trades)
    tpw = n / WEEKS
    pf0 = pf_of(trades)

    def hair(m):
        cut = [p - BASE_COST * m for p in trades]
        return {"pf": pf_of(cut), "net": round(sum(cut), 2), "exp": round(sum(cut) / n, 4) if n else 0}

    cost = {"base_cost_usd": BASE_COST, "x1": hair(1), "x1_5": hair(1.5), "x2": hair(2)}
    kills = []
    if n < 80:
        kills.append(f"N={n}<80")
    if tpw < 1.0 or tpw > 6.0:
        kills.append(f"tpw={tpw:.3f} not in [1,6]")
    if pf0 is None or pf0 < 1.00:
        kills.append(f"PF={pf0}<1.00")
    if kills:
        verdict, model0 = "KILLED_AT_OFFLINE_PROBE", "WITHHELD_KILL_FAST"
    elif cost["x1"]["pf"] is not None and cost["x1"]["pf"] < 1.00:
        kills.append(f"cost_x1={cost['x1']['pf']}")
        verdict, model0 = "KILLED_AT_OFFLINE_PROBE_COST_X1", "WITHHELD_KILL_FAST"
    else:
        verdict, model0 = "PROBE_SURVIVE", "AUTHORIZED_IF_SURVIVE"

    payload = {
        "hypothesis_id": "HYP-H1-EMA-STACK-PB-001",
        "probe_type": "offline_closed_bar_mirror",
        "not_model0": True,
        "symbol": symbol,
        "tf": "H1",
        "n_trades": n,
        "tpw_elapsed": round(tpw, 4),
        "pf_zero_spread": pf0,
        "net_zero_spread": round(sum(trades), 2),
        "exp_zero_spread": round(sum(trades) / n, 4) if n else 0.0,
        "cost_stress_synthetic": cost,
        "kill_reasons": kills,
        "verdict": verdict,
        "model0": model0,
        "params": {"ema": [8, 21, 50], "rr": RR, "sl_atr": SL_ATR, "touch_atr": TOUCH_ATR},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "n_trades", "tpw_elapsed", "pf_zero_spread", "verdict", "model0", "kill_reasons"
    )}, indent=2))
    print("sha", hashlib.sha256(OUT.read_bytes()).hexdigest().upper())


if __name__ == "__main__":
    main()
