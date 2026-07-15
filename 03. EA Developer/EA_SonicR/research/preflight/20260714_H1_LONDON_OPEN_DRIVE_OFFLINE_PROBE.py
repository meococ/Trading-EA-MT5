#!/usr/bin/env python3
"""Offline probe — HYP-H1-LONDON-OPEN-DRIVE-001.

First London H1 (server hour==7) closed drive: body>=0.50 ATR and close in
directional third → continuation RR=2.5. Kill-fast only.
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
    / "20260714_H1_LONDON_OPEN_DRIVE_OFFLINE_PROBE.json"
)
FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
DEPOSIT = 100_000.0
RISK_PCT = 0.50
BASE_COST = 12.0
LONDON_HOUR = 7
MIN_BODY = 0.50
CLOSE_FRAC = 0.33  # close in top/bottom third
RR = 2.5
SL_ATR_BUF = 0.10
MAX_HOLD = 8
FLAT = 16  # flat before late NY; keep London→early NY
MAX_DAY = 1


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def atr(bars, i, period=14):
    if i < period:
        return 0.0
    trs = []
    for j in range(i - period + 1, i + 1):
        prev = bars[j - 1].c
        trs.append(max(bars[j].h - bars[j].l, abs(bars[j].h - prev), abs(bars[j].l - prev)))
    return sum(trs) / period


def pf_of(pnls):
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def main():
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
    bars = [
        Bar(datetime.fromtimestamp(int(r["time"])), float(r["open"]), float(r["high"]),
            float(r["low"]), float(r["close"]))
        for r in rates
    ]

    trades = []
    for i in range(20, len(bars) - 2):
        b = bars[i]
        if b.t.weekday() > 3 or b.t.hour != LONDON_HOUR:
            continue
        a = atr(bars, i)
        if a <= 0:
            continue
        rng = b.h - b.l
        if rng <= 0:
            continue
        body = abs(b.c - b.o)
        if body < a * MIN_BODY:
            continue
        direction = 0
        if b.c > b.o and (b.c - b.l) / rng >= (1.0 - CLOSE_FRAC):
            direction = 1
        elif b.c < b.o and (b.h - b.c) / rng >= (1.0 - CLOSE_FRAC):
            direction = -1
        else:
            continue

        entry = b.c
        sl = (b.l - a * SL_ATR_BUF) if direction > 0 else (b.h + a * SL_ATR_BUF)
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + risk * RR if direction > 0 else entry - risk * RR

        exit_px, reason, hold = entry, "max_hold", 0
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
        trades.append(DEPOSIT * RISK_PCT / 100.0 * r_mult)

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
        "hypothesis_id": "HYP-H1-LONDON-OPEN-DRIVE-001",
        "probe_type": "offline_closed_bar_mirror",
        "not_model0": True,
        "symbol": symbol,
        "tf": "H1",
        "n_trades": n,
        "tpw_elapsed": round(tpw, 4),
        "pf_zero_spread": pf0,
        "net_zero_spread": round(sum(trades), 2) if trades else 0.0,
        "exp_zero_spread": round(sum(trades) / n, 4) if n else 0.0,
        "cost_stress_synthetic": cost,
        "kill_reasons": kills,
        "verdict": verdict,
        "model0": model0,
        "params": {
            "london_hour": LONDON_HOUR,
            "min_body_atr": MIN_BODY,
            "close_frac": CLOSE_FRAC,
            "rr": RR,
            "flat_hour": FLAT,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "n_trades", "tpw_elapsed", "pf_zero_spread", "verdict", "model0", "kill_reasons",
        "cost_stress_synthetic",
    )}, indent=2))
    print("sha", hashlib.sha256(OUT.read_bytes()).hexdigest().upper())


if __name__ == "__main__":
    main()
