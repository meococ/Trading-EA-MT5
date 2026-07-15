#!/usr/bin/env python3
"""Cheap offline probe for HYP-H4-OUTSIDE-REV-001 (closed-bar mirror of EA).

Not Model 0 evidence. Kill-fast screen only. Cost honesty: report-only
+$12/trade haircut on top of zero-spread synthetic fills.
"""
from __future__ import annotations

import hashlib
import json
import math
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
    / "20260714_H4_OUTSIDE_REV_OFFLINE_PROBE.json"
)
SYMBOL_CANDIDATES = ("USDJPY", "USDJPY+")
TF = mt5.TIMEFRAME_H4
FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WR = 7
SL_ATR_BUF = 0.10
ATR_PERIOD = 14
RR = 3.0
MAX_HOLD = 20
FLAT_HOUR = 22
RISK_PCT = 0.50
DEPOSIT = 100_000.0
BASE_COST = 12.0  # a priori friction screen


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest().upper()


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
    return dow in (0, 1, 2, 3)  # Mon–Thu (Python weekday)


def detect_fade(bars: list[Bar], i1: int) -> tuple[bool, bool, float, float] | None:
    """i1 = index of closed signal bar[1]; outside is bar[2]=i1-1 vs bar[3]=i1-2."""
    i2 = i1 - 1
    i3 = i1 - 2
    if i3 < 0 or i1 >= len(bars):
        return None
    if i2 < WR:  # need lookback window ending at i2
        return None
    b2, b3, b1 = bars[i2], bars[i3], bars[i1]
    if not (b2.h > b3.h and b2.l < b3.l):
        return None
    r2 = b2.h - b2.l
    if r2 <= 0:
        return None
    # WR7: widest among i2 and prior WR-1 bars (same as EA loop i=3..1+WR)
    for k in range(i2 - (WR - 1), i2):
        if k < 0:
            return None
        if (bars[k].h - bars[k].l) > r2:
            return None
    if b1.c >= b2.h or b1.c <= b2.l:
        return None
    mid = (b2.h + b2.l) * 0.5
    if b2.c >= mid and b1.c < mid:
        return (True, False, b2.h, b2.l)  # short
    if b2.c <= mid and b1.c > mid:
        return (True, True, b2.h, b2.l)  # long
    return None


def simulate(bars: list[Bar]) -> dict:
    trades: list[dict] = []
    i = WR + 3
    last_day: tuple[int, int, int] | None = None
    trades_today = 0
    while i < len(bars) - 1:
        b1 = bars[i]
        day = (b1.t.year, b1.t.month, b1.t.day)
        if day != last_day:
            last_day = day
            trades_today = 0
        if b1.t.hour >= FLAT_HOUR or not is_trade_dow(b1.t.weekday()) or trades_today >= 1:
            i += 1
            continue
        sig = detect_fade(bars, i)
        if sig is None:
            i += 1
            continue
        _, is_buy, out_h, out_l = sig
        atr = atr_at(bars, i - 1, ATR_PERIOD)  # ATR on closed bar[1] context ≈ EA CopyBuffer shift 1 at new bar
        if atr <= 0:
            i += 1
            continue
        # Entry at open of next bar after signal close (conservative vs EA tick-on-new-bar)
        entry_i = i + 1
        if entry_i >= len(bars):
            break
        entry = bars[entry_i].o
        sl_raw = (out_l - atr * SL_ATR_BUF) if is_buy else (out_h + atr * SL_ATR_BUF)
        sl_dist = abs(entry - sl_raw)
        if sl_dist <= 0:
            i += 1
            continue
        sl = entry - sl_dist if is_buy else entry + sl_dist
        tp = entry + sl_dist * RR if is_buy else entry - sl_dist * RR
        # Path: hold up to MAX_HOLD bars or flat hour / weekend
        exit_px = None
        exit_reason = "timeout"
        exit_i = entry_i
        for j in range(entry_i, min(entry_i + MAX_HOLD, len(bars))):
            bj = bars[j]
            exit_i = j
            if is_buy:
                if bj.l <= sl:
                    exit_px, exit_reason = sl, "sl"
                    break
                if bj.h >= tp:
                    exit_px, exit_reason = tp, "tp"
                    break
            else:
                if bj.h >= sl:
                    exit_px, exit_reason = sl, "sl"
                    break
                if bj.l <= tp:
                    exit_px, exit_reason = tp, "tp"
                    break
            if bj.t.hour >= FLAT_HOUR or bj.t.weekday() >= 4:
                exit_px, exit_reason = bj.c, "flat"
                break
        if exit_px is None:
            exit_px = bars[exit_i].c
        # Cash PnL with fixed fractional risk (R = risk cash)
        risk_cash = DEPOSIT * (RISK_PCT / 100.0)
        r_mult = ((exit_px - entry) / sl_dist) if is_buy else ((entry - exit_px) / sl_dist)
        pnl = r_mult * risk_cash
        trades.append(
            {
                "t": b1.t.isoformat(),
                "side": "buy" if is_buy else "sell",
                "r": round(r_mult, 4),
                "pnl": round(pnl, 2),
                "reason": exit_reason,
            }
        )
        trades_today += 1
        i = exit_i + 1  # no overlap
    return summarize(trades)


def summarize(trades: list[dict]) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0, "pf": 0.0, "net": 0.0, "exp": 0.0, "tpw": 0.0}
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
    gw = sum(wins)
    gl = abs(sum(losses))
    pf = (gw / gl) if gl > 0 else (999.0 if gw > 0 else 0.0)
    net = sum(t["pnl"] for t in trades)
    # elapsed calendar weeks 2021-01-01 .. 2025-12-31 ≈ 260.857
    elapsed_weeks = (datetime(2025, 12, 31) - datetime(2021, 1, 1)).days / 7.0
    tpw = n / elapsed_weeks
    # cost stress report-only
    stressed = [t["pnl"] - BASE_COST for t in trades]
    sw = sum(x for x in stressed if x > 0)
    sl_ = abs(sum(x for x in stressed if x <= 0))
    pf_c = (sw / sl_) if sl_ > 0 else 0.0
    # x1.5 / x2 as extra haircut multiples of base cost
    def pf_at(mult: float) -> float:
        xs = [t["pnl"] - BASE_COST * mult for t in trades]
        w = sum(x for x in xs if x > 0)
        l = abs(sum(x for x in xs if x <= 0))
        return (w / l) if l > 0 else 0.0

    return {
        "n": n,
        "pf": round(pf, 4),
        "net": round(net, 2),
        "exp": round(net / n, 2),
        "tpw": round(tpw, 4),
        "win_rate": round(len(wins) / n, 4),
        "cost_base": BASE_COST,
        "pf_cost_x1": round(pf_c, 4),
        "pf_cost_x1_5": round(pf_at(1.5), 4),
        "pf_cost_x2": round(pf_at(2.0), 4),
        "exp_after_12": round((net - n * BASE_COST) / n, 2),
        "reasons": {
            "tp": sum(1 for t in trades if t["reason"] == "tp"),
            "sl": sum(1 for t in trades if t["reason"] == "sl"),
            "flat": sum(1 for t in trades if t["reason"] == "flat"),
            "timeout": sum(1 for t in trades if t["reason"] == "timeout"),
        },
    }


def gate(m: dict) -> dict:
    n, pf, tpw = m["n"], m["pf"], m["tpw"]
    kill = n < 80 or pf < 1.0 or not (1.0 <= tpw <= 6.0)
    hit = (not kill) and pf > 1.30 and 2.0 <= tpw <= 5.0
    # baked cost screen
    cost_ok = m["pf_cost_x1_5"] >= 1.25 and m["pf_cost_x2"] >= 1.00
    thin = m["exp"] < 20.0 or m["exp_after_12"] < 5.0
    if kill or thin or m["pf_cost_x1"] < 1.0:
        verdict = "KILL_PROBE"
    elif hit and cost_ok:
        verdict = "SURVIVE_PROBE_TO_MODEL0"
    else:
        verdict = "PARK_OR_WEAK_PROBE"
    return {
        "kill_raw": kill,
        "hit_raw": hit,
        "cost_ok": cost_ok,
        "thin_expectancy": thin,
        "verdict": verdict,
    }


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(f"mt5.initialize failed: {mt5.last_error()}")
    try:
        symbol = None
        rates = None
        for s in SYMBOL_CANDIDATES:
            info = mt5.symbol_info(s)
            if info is None:
                continue
            if not info.visible:
                mt5.symbol_select(s, True)
            rates = mt5.copy_rates_range(s, TF, FROM, TO)
            if rates is not None and len(rates) > 100:
                symbol = s
                break
        if rates is None or symbol is None:
            raise SystemExit(f"no rates: {mt5.last_error()}")
        bars = [
            Bar(
                t=datetime.fromtimestamp(int(r["time"]), tz=timezone.utc).replace(tzinfo=None),
                o=float(r["open"]),
                h=float(r["high"]),
                l=float(r["low"]),
                c=float(r["close"]),
            )
            for r in rates
        ]
        metrics = simulate(bars)
        g = gate(metrics)
        ea = ROOT / "03. EA Developer" / "EA_H4OutsideRev" / "EA_H4OutsideRev.mq5"
        payload = {
            "hypothesis_id": "HYP-H4-OUTSIDE-REV-001",
            "probe": "offline_closed_bar_mirror",
            "symbol": symbol,
            "bars": len(bars),
            "window": "2021.01.01-2025.12.31",
            "metrics": metrics,
            "gate": g,
            "source_sha256": sha256_file(ea) if ea.exists() else None,
            "cost_honesty": "UNVERIFIED_SYNTHETIC_PLUS_REPORT_ONLY_12",
            "note": "Not Model 0; fill at next-bar open; zero spread in path sim",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
