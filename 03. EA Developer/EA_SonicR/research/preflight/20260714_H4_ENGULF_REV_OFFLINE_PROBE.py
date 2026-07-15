#!/usr/bin/env python3
"""Cheap offline probe for HYP-H4-ENGULF-REV-001 (closed-bar mirror)."""
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
    / "20260714_H4_ENGULF_REV_OFFLINE_PROBE.json"
)
EA_PATH = ROOT / "03. EA Developer" / "EA_H4EngulfRev" / "EA_H4EngulfRev.mq5"
SYMBOL_CANDIDATES = ("USDJPY", "USDJPY+")
FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
MIN_BODY_ATR = 0.25
SL_ATR_BUF = 0.10
ATR_PERIOD = 14
RR = 3.0
MAX_HOLD = 20
FLAT_HOUR = 22
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest().upper()


def atr_at(bars: list[Bar], i: int, period: int) -> float:
    if i < period:
        return 0.0
    trs = []
    for j in range(i - period + 1, i + 1):
        prev_c = bars[j - 1].c
        tr = max(bars[j].h - bars[j].l, abs(bars[j].h - prev_c), abs(bars[j].l - prev_c))
        trs.append(tr)
    return sum(trs) / period


def body(b: Bar) -> tuple[float, float, float]:
    lo = min(b.o, b.c)
    hi = max(b.o, b.c)
    return lo, hi, abs(b.c - b.o)


def detect_engulf(bars: list[Bar], i1: int) -> tuple[bool, bool, float, float] | None:
    """Mirror EA: opposite-color body engulf + bar[1] mid accept."""
    i2, i3 = i1 - 1, i1 - 2
    if i3 < 0:
        return None
    b1, b2, b3 = bars[i1], bars[i2], bars[i3]
    if b2.o == b2.c or b3.o == b3.c:
        return None
    # ATR on engulf bar (EA CopyBuffer shift 2)
    atr = atr_at(bars, i2, ATR_PERIOD)
    if atr <= 0:
        return None
    lo2, hi2, body2 = body(b2)
    lo3, hi3, _body3 = body(b3)
    if body2 < atr * MIN_BODY_ATR:
        return None
    if not (hi2 > hi3 and lo2 < lo3):
        return None
    mid = (hi2 + lo2) * 0.5
    bull_engulf = b2.c > b2.o and b3.c < b3.o
    bear_engulf = b2.c < b2.o and b3.c > b3.o
    if bull_engulf and b1.c >= mid:
        return (True, True, b2.h, b2.l)
    if bear_engulf and b1.c <= mid:
        return (True, False, b2.h, b2.l)
    return None


def simulate(bars: list[Bar]) -> dict:
    trades = []
    i = ATR_PERIOD + 3
    last_day = None
    trades_today = 0
    while i < len(bars) - 1:
        b1 = bars[i]
        day = (b1.t.year, b1.t.month, b1.t.day)
        if day != last_day:
            last_day = day
            trades_today = 0
        if b1.t.hour >= FLAT_HOUR or b1.t.weekday() >= 4 or trades_today >= 1:
            i += 1
            continue
        sig = detect_engulf(bars, i)
        if sig is None:
            i += 1
            continue
        _, is_buy, out_h, out_l = sig
        atr = atr_at(bars, i, ATR_PERIOD)
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
        risk_cash = DEPOSIT * (RISK_PCT / 100.0)
        r_mult = ((exit_px - entry) / sl_dist) if is_buy else ((entry - exit_px) / sl_dist)
        pnl = r_mult * risk_cash
        trades.append({"pnl": pnl, "reason": exit_reason, "r": r_mult})
        trades_today += 1
        i = exit_i + 1
    return summarize(trades)


def summarize(trades: list[dict]) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0, "pf": 0.0, "net": 0.0, "exp": 0.0, "tpw": 0.0}
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
    gw, gl = sum(wins), abs(sum(losses))
    pf = (gw / gl) if gl > 0 else 0.0
    net = sum(t["pnl"] for t in trades)
    elapsed_weeks = (datetime(2025, 12, 31) - datetime(2021, 1, 1)).days / 7.0
    tpw = n / elapsed_weeks

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
        "pf_cost_x1": round(pf_at(1.0), 4),
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
    cost_ok = m.get("pf_cost_x1_5", 0) >= 1.25 and m.get("pf_cost_x2", 0) >= 1.00
    thin = m["exp"] < 20.0 or m.get("exp_after_12", -999) < 5.0
    if kill or thin or m.get("pf_cost_x1", 0) < 1.0:
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
    # Read EA signal briefly to confirm mid-accept semantics exist
    src = EA_PATH.read_text(encoding="utf-8", errors="replace") if EA_PATH.exists() else ""
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
            rates = mt5.copy_rates_range(s, mt5.TIMEFRAME_H4, FROM, TO)
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
        payload = {
            "hypothesis_id": "HYP-H4-ENGULF-REV-001",
            "probe": "offline_closed_bar_mirror",
            "symbol": symbol,
            "bars": len(bars),
            "window": "2021.01.01-2025.12.31",
            "metrics": metrics,
            "gate": g,
            "ea_mentions_engulf": ("engulf" in src.lower()),
            "source_sha256": sha256_file(EA_PATH) if EA_PATH.exists() else None,
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
