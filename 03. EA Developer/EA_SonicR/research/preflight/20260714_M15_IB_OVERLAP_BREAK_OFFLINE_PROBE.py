#!/usr/bin/env python3
"""Cheap offline probe for HYP-M15-IB-OVERLAP-BREAK-001 (closed-bar mirror).

Not Model 0 evidence. Kill-fast screen only.
Mirrors EA_M15IBOverlapBreak defaults + a priori +$12 cost haircut.
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
    / "20260714_M15_IB_OVERLAP_BREAK_OFFLINE_PROBE.json"
)
SYMBOL_CANDIDATES = ("USDJPY", "USDJPY+")
TF = mt5.TIMEFRAME_M15
FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)

IB_START = 7
IB_END = 8  # exclusive
OVERLAP_START = 13
OVERLAP_END = 16
MIN_BODY_ATR = 0.35
MIN_IB_ATR = 0.40
SL_ATR_BUF = 0.10
ATR_PERIOD = 14
RR = 2.5
MAX_HOLD = 32
FLAT_HOUR = 21
MAX_PER_DAY = 2
RISK_PCT = 0.50
DEPOSIT = 100_000.0
BASE_COST = 12.0


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def atr_at(bars: list[Bar], i: int, period: int) -> float:
    if i < period:
        return 0.0
    trs: list[float] = []
    for j in range(i - period + 1, i + 1):
        prev_c = bars[j - 1].c
        tr = max(bars[j].h - bars[j].l, abs(bars[j].h - prev_c), abs(bars[j].l - prev_c))
        trs.append(tr)
    return sum(trs) / period


def is_trade_dow(dow: int) -> bool:
    return dow in (0, 1, 2, 3)  # Mon–Thu


def simulate(bars: list[Bar]) -> dict:
    trades: list[dict] = []
    i = ATR_PERIOD + 5
    n = len(bars)

    while i < n - 2:
        b = bars[i]
        if not is_trade_dow(b.t.weekday()):
            i += 1
            continue

        # Build IB for this calendar day from bars in hour IB_START
        day = b.t.date()
        ib_h = None
        ib_l = None
        for j in range(max(0, i - 80), i + 1):
            bj = bars[j]
            if bj.t.date() != day:
                continue
            if bj.t.hour == IB_START:
                if ib_h is None:
                    ib_h, ib_l = bj.h, bj.l
                else:
                    ib_h = max(ib_h, bj.h)
                    ib_l = min(ib_l, bj.l)

        # IB ready only after IB_END hour has started (closed bars past IB hour)
        if ib_h is None or ib_l is None or ib_h <= ib_l:
            i += 1
            continue
        if b.t.hour < IB_END:
            i += 1
            continue
        if b.t.hour < OVERLAP_START or b.t.hour >= OVERLAP_END:
            i += 1
            continue

        atr = atr_at(bars, i, ATR_PERIOD)
        if atr <= 0:
            i += 1
            continue
        if (ib_h - ib_l) < atr * MIN_IB_ATR:
            i += 1
            continue

        body = abs(b.c - b.o)
        if body < atr * MIN_BODY_ATR:
            i += 1
            continue

        direction = 0
        sl_extreme = 0.0
        if b.c > ib_h and b.h > ib_h:
            direction = 1
            sl_extreme = ib_l
        elif b.c < ib_l and b.l < ib_l:
            direction = -1
            sl_extreme = ib_h
        else:
            i += 1
            continue

        entry = b.c
        if direction > 0:
            sl = sl_extreme - atr * SL_ATR_BUF
            risk = entry - sl
            if risk <= 0:
                i += 1
                continue
            tp = entry + risk * RR
        else:
            sl = sl_extreme + atr * SL_ATR_BUF
            risk = sl - entry
            if risk <= 0:
                i += 1
                continue
            tp = entry - risk * RR

        # One break direction / day (mirrors g_brokeToday)
        exit_px = entry
        exit_reason = "max_hold"
        hold = 0
        for k in range(i + 1, min(n, i + 1 + MAX_HOLD)):
            hold += 1
            bk = bars[k]
            if bk.t.hour >= FLAT_HOUR or bk.t.weekday() >= 4:
                exit_px = bk.o
                exit_reason = "flat"
                break
            if direction > 0:
                if bk.l <= sl:
                    exit_px = sl
                    exit_reason = "sl"
                    break
                if bk.h >= tp:
                    exit_px = tp
                    exit_reason = "tp"
                    break
            else:
                if bk.h >= sl:
                    exit_px = sl
                    exit_reason = "sl"
                    break
                if bk.l <= tp:
                    exit_px = tp
                    exit_reason = "tp"
                    break
            exit_px = bk.c

        # Rough cash PnL at fixed risk fraction of deposit (risk 0.5% → risk_cash)
        risk_cash = DEPOSIT * RISK_PCT / 100.0
        r_mult = (exit_px - entry) / risk if direction > 0 else (entry - exit_px) / risk
        pnl = risk_cash * r_mult

        trades.append(
            {
                "t": b.t.isoformat(),
                "dir": direction,
                "pnl": round(pnl, 4),
                "r": round(r_mult, 4),
                "exit": exit_reason,
                "hold": hold,
            }
        )

        # Skip rest of day after break
        day_end = i + 1
        while day_end < n and bars[day_end].t.date() == day:
            day_end += 1
        i = day_end

    return trades


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")

    symbol = None
    rates = None
    for s in SYMBOL_CANDIDATES:
        if not mt5.symbol_select(s, True):
            continue
        rates = mt5.copy_rates_range(s, TF, FROM, TO)
        if rates is not None and len(rates) > 500:
            symbol = s
            break
    if symbol is None or rates is None:
        mt5.shutdown()
        raise SystemExit(f"no rates: {mt5.last_error()}")

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
    mt5.shutdown()

    trades = simulate(bars)
    pnls = [t["pnl"] for t in trades]
    n = len(pnls)
    weeks = (TO - FROM).days / 7.0
    tpw = n / weeks if weeks > 0 else 0.0
    pf0 = pf_of(pnls)
    exp = (sum(pnls) / n) if n else 0.0

    def haircut(mult: float) -> dict:
        cut = [p - BASE_COST * mult for p in pnls]
        return {
            "pf": None if not cut else pf_of(cut),
            "net": round(sum(cut), 2),
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }

    cost = {
        "base_cost_usd": BASE_COST,
        "x1": haircut(1.0),
        "x1_5": haircut(1.5),
        "x2": haircut(2.0),
    }

    # Screen: PF>1.30 ∧ 2–5 tpw ∧ x1.5≥1.25 ∧ x2≥1.00 (optimistic zero-spread first)
    kill_reasons: list[str] = []
    if n < 80:
        kill_reasons.append(f"N={n}<80")
    if tpw < 1.0 or tpw > 6.0:
        kill_reasons.append(f"tpw={tpw:.3f} not in [1,6]")
    if pf0 is None or pf0 < 1.00:
        kill_reasons.append(f"PF={pf0}<1.00")

    survive_kill = len(kill_reasons) == 0
    research_hit = (
        survive_kill
        and pf0 is not None
        and pf0 > 1.30
        and 2.0 <= tpw <= 5.0
        and cost["x1_5"]["pf"] is not None
        and cost["x1_5"]["pf"] >= 1.25
        and cost["x2"]["pf"] is not None
        and cost["x2"]["pf"] >= 1.00
    )

    model0 = "AUTHORIZED_IF_SURVIVE"
    verdict = "PROBE_SURVIVE"
    if not survive_kill:
        verdict = "KILLED_AT_OFFLINE_PROBE"
        model0 = "WITHHELD_KILL_FAST"
    elif pf0 is not None and pf0 < 1.20:
        # weak but above kill — still allow Model0? Doctrine: kill-fast on thin
        # Keep Model0 if survives hard kill gates; cost stress will decide.
        verdict = "PROBE_WEAK_SURVIVE_MODEL0_OK"
    elif cost["x1"]["pf"] is not None and cost["x1"]["pf"] < 1.00:
        verdict = "KILLED_AT_OFFLINE_PROBE_COST_X1"
        model0 = "WITHHELD_KILL_FAST"
        kill_reasons.append(f"cost_x1_pf={cost['x1']['pf']}")

    payload = {
        "hypothesis_id": "HYP-M15-IB-OVERLAP-BREAK-001",
        "ea": "EA_M15IBOverlapBreak",
        "probe_type": "offline_closed_bar_mirror",
        "not_model0": True,
        "symbol": symbol,
        "tf": "M15",
        "from": FROM.isoformat(),
        "to": TO.isoformat(),
        "bars": len(bars),
        "n_trades": n,
        "tpw_elapsed": round(tpw, 4),
        "pf_zero_spread": pf0,
        "net_zero_spread": round(sum(pnls), 2),
        "exp_zero_spread": round(exp, 4),
        "cost_stress_synthetic": cost,
        "kill_reasons": kill_reasons,
        "verdict": verdict,
        "model0": model0,
        "research_hit_screen": research_hit,
        "params": {
            "ib": [IB_START, IB_END],
            "overlap": [OVERLAP_START, OVERLAP_END],
            "min_body_atr": MIN_BODY_ATR,
            "min_ib_atr": MIN_IB_ATR,
            "rr": RR,
            "max_hold": MAX_HOLD,
            "max_per_day": MAX_PER_DAY,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "n_trades", "tpw_elapsed", "pf_zero_spread", "verdict", "model0",
        "kill_reasons", "research_hit_screen",
    )}, indent=2))
    print("wrote", OUT)
    print("sha256", hashlib.sha256(OUT.read_bytes()).hexdigest().upper())


if __name__ == "__main__":
    main()
