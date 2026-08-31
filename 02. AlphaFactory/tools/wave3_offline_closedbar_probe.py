#!/usr/bin/env python3
"""Offline closed-bar probe for Discovery Wave3 (Outside / Engulf / PinPD).

Honesty:
- NOT AlphaFactory Model 0. NOT confirmed. NOT GOAL.
- Uses MT5 copy_rates (read-only) while Owner Real may be open.
- R-based path with fixed risk cash; time/flat exits approx fill at close.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
REG = ROOT / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Memory/hot.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK_PCT = 0.50
TP_RR = 3.0
POINT = 0.001
MIN_SL_POINTS = 100
MAX_SL_POINTS = 5000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def atr_wilder(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.full(n, np.nan)
    if n < period:
        return atr
    atr[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


@dataclass
class Trade:
    entry_i: int
    direction: int  # +1 buy / -1 sell
    entry: float
    sl: float
    tp: float
    risk_cash: float
    exit_i: int = -1
    exit: float = 0.0
    pnl: float = 0.0
    reason: str = ""


def load_rates(symbol: str, timeframe: int) -> dict[str, np.ndarray]:
    rates = mt5.copy_rates_range(symbol, timeframe, FROM, TO)
    if rates is None or len(rates) < 50:
        raise RuntimeError(f"rates unavailable {symbol} tf={timeframe}: {mt5.last_error()}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def day_of_week_utc(ts: int) -> int:
    # MT5 broker time usually server; use UTC from epoch as proxy for Mon-Thu filter
    return datetime.utcfromtimestamp(ts).weekday()  # Mon=0 .. Sun=6


def hour_utc(ts: int) -> int:
    return datetime.utcfromtimestamp(ts).hour


def simulate(
    bars: dict[str, np.ndarray],
    signal_fn: Callable[[int, dict[str, np.ndarray], np.ndarray], tuple[bool, int, float] | None],
    max_per_day: int,
    max_hold: int,
    flat_hour: int = 22,
    trade_fri: bool = False,
) -> list[Trade]:
    o, h, l, c, t = bars["open"], bars["high"], bars["low"], bars["close"], bars["time"]
    atr = atr_wilder(h, l, c, 14)
    trades: list[Trade] = []
    open_tr: Trade | None = None
    hold = 0
    last_day = None
    trades_today = 0
    balance = DEPOSIT

    # Iterate on closed bar i as "bar[1]" when new bar forms at i+1 ... 
    # Signal uses bars up through i (closed). Entry at open of i+1 approx (next bar open).
    for i in range(20, len(c) - 2):
        # Management on bar i close / bar i+1 open transition: use bar i as closed signal bar
        ts = int(t[i])
        dow = day_of_week_utc(ts)  # Mon=0
        # Map to MT5 day_of_week: Sun=0 ... Sat=6 — EA uses MqlDateTime.day_of_week
        # Python weekday Mon=0; convert: Sun=6 -> 0, Mon=0 -> 1, ... Sat=5 -> 6
        mt5_dow = (dow + 1) % 7
        day_key = datetime.utcfromtimestamp(ts).strftime("%Y%j")
        if day_key != last_day:
            last_day = day_key
            trades_today = 0

        hr = hour_utc(ts)

        if open_tr is not None:
            hold += 1
            # Check SL/TP against bar i+1 range (bar after entry decision) — for open trade use current bar i
            # Position was entered at open of entry_i; check bar i OHLC
            hi, lo, cl = h[i], l[i], c[i]
            hit_sl = (open_tr.direction > 0 and lo <= open_tr.sl) or (
                open_tr.direction < 0 and hi >= open_tr.sl
            )
            hit_tp = (open_tr.direction > 0 and hi >= open_tr.tp) or (
                open_tr.direction < 0 and lo <= open_tr.tp
            )
            flat = hold >= max_hold or hr >= flat_hour or mt5_dow in (0, 5, 6)
            if hit_sl and hit_tp:
                # conservative: SL first
                open_tr.exit_i = i
                open_tr.exit = open_tr.sl
                open_tr.pnl = -open_tr.risk_cash
                open_tr.reason = "sl_tp_tie_sl"
                balance += open_tr.pnl
                trades.append(open_tr)
                open_tr = None
                hold = 0
            elif hit_sl:
                open_tr.exit_i = i
                open_tr.exit = open_tr.sl
                open_tr.pnl = -open_tr.risk_cash
                open_tr.reason = "sl"
                balance += open_tr.pnl
                trades.append(open_tr)
                open_tr = None
                hold = 0
            elif hit_tp:
                open_tr.exit_i = i
                open_tr.exit = open_tr.tp
                open_tr.pnl = open_tr.risk_cash * TP_RR
                open_tr.reason = "tp"
                balance += open_tr.pnl
                trades.append(open_tr)
                open_tr = None
                hold = 0
            elif flat:
                open_tr.exit_i = i
                open_tr.exit = cl
                r_mult = open_tr.direction * (cl - open_tr.entry) / abs(open_tr.entry - open_tr.sl)
                open_tr.pnl = open_tr.risk_cash * r_mult
                open_tr.reason = "flat"
                balance += open_tr.pnl
                trades.append(open_tr)
                open_tr = None
                hold = 0
            continue

        # No position — signal on closed bar i, enter at open of i+1
        if hr >= flat_hour or mt5_dow in (0, 5, 6):
            continue
        if mt5_dow == 5 and not trade_fri:
            continue
        if mt5_dow not in (1, 2, 3, 4):  # Mon-Thu
            continue
        if trades_today >= max_per_day:
            continue
        if math.isnan(atr[i]) or atr[i] <= 0:
            continue

        sig = signal_fn(i, bars, atr)
        if not sig:
            continue
        ok, direction, sl_extreme = sig
        if not ok:
            continue

        entry = float(o[i + 1])  # next bar open proxy for ask/bid
        sl_raw = sl_extreme - atr[i] * 0.10 if direction > 0 else sl_extreme + atr[i] * 0.10
        sl_dist = abs(entry - sl_raw)
        min_sl = MIN_SL_POINTS * POINT
        max_sl = MAX_SL_POINTS * POINT
        if sl_dist < min_sl:
            sl_dist = min_sl
        if sl_dist > max_sl:
            continue
        sl = entry - sl_dist if direction > 0 else entry + sl_dist
        tp = entry + sl_dist * TP_RR if direction > 0 else entry - sl_dist * TP_RR
        risk_cash = balance * (RISK_PCT / 100.0)
        open_tr = Trade(
            entry_i=i + 1,
            direction=direction,
            entry=entry,
            sl=sl,
            tp=tp,
            risk_cash=risk_cash,
        )
        hold = 0
        trades_today += 1

    if open_tr is not None:
        open_tr.exit_i = len(c) - 1
        open_tr.exit = float(c[-1])
        r_mult = open_tr.direction * (open_tr.exit - open_tr.entry) / abs(open_tr.entry - open_tr.sl)
        open_tr.pnl = open_tr.risk_cash * r_mult
        open_tr.reason = "eod"
        trades.append(open_tr)

    return trades


def metrics(trades: list[Trade]) -> dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "n": 0,
            "pf": 0.0,
            "net": 0.0,
            "tpw": 0.0,
            "win_rate": 0.0,
            "exp": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
        }
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = sum(losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    net = sum(pnls)
    return {
        "n": n,
        "pf": pf,
        "net": net,
        "tpw": n / ELAPSED_WEEKS,
        "win_rate": len(wins) / n,
        "exp": net / n,
        "avg_win": (sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": (sum(losses) / len(losses)) if losses else 0.0,
        "exit_reasons": {
            k: sum(1 for t in trades if t.reason == k)
            for k in sorted({t.reason for t in trades})
        },
    }


def gate(m: dict[str, Any]) -> str:
    n, pf, tpw = m["n"], m["pf"], m["tpw"]
    if pf < 1.00 or not (1.0 <= tpw <= 6.0) or n < 80:
        return "KILL"
    if pf > 1.30 and 2.0 <= tpw <= 5.0:
        return "HIT_RESEARCH_BAR_OFFLINE_ONLY"
    return "PARK"


def signal_outside(i: int, bars: dict[str, np.ndarray], atr: np.ndarray):
    # closed bar i == bar[1]; outside at i-1 == bar[2]; prior i-2 == bar[3]
    h, l, c = bars["high"], bars["low"], bars["close"]
    wr = 7
    if i < 1 + wr:
        return None
    hi2, lo2 = h[i - 1], l[i - 1]
    hi3, lo3 = h[i - 2], l[i - 2]
    if not (hi2 > hi3 and lo2 < lo3):
        return None
    r2 = hi2 - lo2
    # EA: for shift = 3 .. 1+WR compare ranges; bar[shift] index = i-(shift-1)
    for shift in range(3, 1 + wr + 1):
        bi = i - (shift - 1)
        if bi < 0 or (h[bi] - l[bi]) > r2:
            return None
    c2, c1 = c[i - 1], c[i]
    if c1 >= hi2 or c1 <= lo2:
        return None
    mid = (hi2 + lo2) * 0.5
    if c2 >= mid and c1 < mid:
        return True, -1, hi2  # short
    if c2 <= mid and c1 > mid:
        return True, +1, lo2
    return None


def signal_engulf(i: int, bars: dict[str, np.ndarray], atr: np.ndarray):
    o, h, l, c = bars["open"], bars["high"], bars["low"], bars["close"]
    if i < 3 or math.isnan(atr[i - 1]):
        return None
    o2, c2, h2, l2 = o[i - 1], c[i - 1], h[i - 1], l[i - 1]
    o3, c3 = o[i - 2], c[i - 2]
    c1 = c[i]
    if o2 == c2 or o3 == c3:
        return None
    body2_hi, body2_lo = max(o2, c2), min(o2, c2)
    body3_hi, body3_lo = max(o3, c3), min(o3, c3)
    if not (body2_hi > body3_hi and body2_lo < body3_lo):
        return None
    if (body2_hi - body2_lo) < atr[i - 1] * 0.25:
        return None
    mid = (body2_hi + body2_lo) * 0.5
    bull = c2 > o2 and c3 < o3
    bear = c2 < o2 and c3 > o3
    if bull and c1 >= mid:
        return True, +1, l2
    if bear and c1 <= mid:
        return True, -1, h2
    return None


def signal_pin(i: int, bars: dict[str, np.ndarray], atr: np.ndarray, d1: dict[str, np.ndarray]):
    o, h, l, c, t = bars["open"], bars["high"], bars["low"], bars["close"], bars["time"]
    if math.isnan(atr[i]) or atr[i] <= 0:
        return None
    o1, h1, l1, c1 = o[i], h[i], l[i], c[i]
    rng = h1 - l1
    if rng <= 0:
        return None
    upper = h1 - max(o1, c1)
    lower = min(o1, c1) - l1
    # prior completed D1 relative to this H1 bar time
    ts = int(t[i])
    # find last D1 bar with time < start of current day
    day_start = datetime.utcfromtimestamp(ts).replace(hour=0, minute=0, second=0)
    day_start_ts = int(day_start.timestamp())
    d1_idx = np.searchsorted(d1["time"], day_start_ts, side="left") - 1
    if d1_idx < 0:
        return None
    pdh, pdl = float(d1["high"][d1_idx]), float(d1["low"][d1_idx])
    touch = atr[i] * 0.05
    if upper / rng >= 0.60 and lower / rng <= 0.25 and (pdh - touch) <= h1 <= (pdh + touch):
        return True, -1, h1
    if lower / rng >= 0.60 and upper / rng <= 0.25 and (pdl - touch) <= l1 <= (pdl + touch):
        return True, +1, l1
    return None


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(mt5.last_error())
    try:
        acc = mt5.account_info()
        server = getattr(acc, "server", None)
        login = getattr(acc, "login", None)
        mt5.symbol_select("USDJPY", True)
        h4 = load_rates("USDJPY", mt5.TIMEFRAME_H4)
        h1 = load_rates("USDJPY", mt5.TIMEFRAME_H1)
        d1 = load_rates("USDJPY", mt5.TIMEFRAME_D1)
    finally:
        mt5.shutdown()

    results = {}

    # Outside
    tr_out = simulate(h4, signal_outside, max_per_day=1, max_hold=20)
    m_out = metrics(tr_out)
    results["HYP-H4-OUTSIDE-REV-001"] = {
        "ea": "EA_H4OutsideRev",
        "tf": "H4",
        "metrics": m_out,
        "verdict": gate(m_out),
    }

    # Engulf
    tr_en = simulate(h4, signal_engulf, max_per_day=1, max_hold=20)
    m_en = metrics(tr_en)
    results["HYP-H4-ENGULF-REV-001"] = {
        "ea": "EA_H4EngulfRev",
        "tf": "H4",
        "metrics": m_en,
        "verdict": gate(m_en),
    }

    # Pin
    def pin_fn(i, bars, atr):
        return signal_pin(i, bars, atr, d1)

    tr_pin = simulate(h1, pin_fn, max_per_day=2, max_hold=12)
    m_pin = metrics(tr_pin)
    results["HYP-H1-PIN-PDLEVEL-001"] = {
        "ea": "EA_H1PinPDLevel",
        "tf": "H1",
        "metrics": m_pin,
        "verdict": gate(m_pin),
    }

    receipt = {
        "schema_version": "sonic_wave3_offline_probe.v1",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_CLOSED_BAR_PROBE_COMPLETE",
        "model0_status": "BLOCKED_UNRELATED_TERMINAL64_OWNER_REAL",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "server_observed": server,
        "login": login,
        "window": "2021.01.01-2025.12.31",
        "elapsed_weeks": ELAPSED_WEEKS,
        "risk_pct": RISK_PCT,
        "tp_rr": TP_RR,
        "results": results,
        "source_hashes": {
            "EA_H4OutsideRev": sha256_file(
                ROOT / "03. EA Developer/EA_H4OutsideRev/EA_H4OutsideRev.mq5"
            ),
            "EA_H4EngulfRev": sha256_file(
                ROOT / "03. EA Developer/EA_H4EngulfRev/EA_H4EngulfRev.mq5"
            ),
            "EA_H1PinPDLevel": sha256_file(
                ROOT / "03. EA Developer/EA_H1PinPDLevel/EA_H1PinPDLevel.mq5"
            ),
        },
        "banned": ["densify_maxkz", "hour_day_mine", "qfsi_stall", "claim_model0"],
    }
    out = PRE / "20260714_DISCOVERY_WAVE3_OFFLINE_PROBE.json"
    write_json(out, receipt)
    receipt_sha = sha256_file(out)

    # Deliverable VN
    lines = [
        "# Deliverable — Discovery Wave3 offline probe (Model 0 blocked)",
        "",
        "Date: 2026-07-14",
        "Authority: Owner continue independent discovery; no MaxKZ densify; no QFSI stall",
        "GPT: waived",
        "",
        "## Blocker Model 0",
        "",
        "`alpha.ps1 backtest` fail-closed: `Unrelated terminal64` (Owner Real login).",
        "Agent did **not** kill Real. Contracts rebuilt + compile OK; Model 0 not run.",
        "",
        "## Offline closed-bar probe (NOT Model 0)",
        "",
        f"Server observed: `{server}` login `{login}`. Window 2021–2025. RR=3 / risk 0.5%.",
        f"Receipt SHA: `{receipt_sha}`",
        "",
        "| ID | N | PF | tpw | Exp$/t | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for hid, row in results.items():
        m = row["metrics"]
        lines.append(
            f"| `{hid}` | {m['n']} | {m['pf']:.3f} | {m['tpw']:.2f} | {m['exp']:.2f} | **{row['verdict']}** |"
        )
    lines += [
        "",
        "## vs GOAL",
        "",
        "GOAL needs Model 0 + verified cost. Offline HIT only ranks for exclusive Model 0.",
        "KILL/PARK below follow prereg gates on offline metrics (honest proxy).",
        "",
        "## Next",
        "",
        "1. Owner đóng Real `terminal64` (hoặc exclusive tester) → chạy Model 0 Wave3 trio.",
        "2. Không densify MaxKZ/RR; không mine giờ/ngày; không QFSI-wait.",
        "3. Offline KILL → không Model 0 spam; PARK/HIT → Model 0 khi tester free.",
        "",
        f"JSON: `preflight/20260714_DISCOVERY_WAVE3_OFFLINE_PROBE.json`",
    ]
    deliv = READ / "20260714_DISCOVERY_WAVE3_OFFLINE_PROBE_DELIVERABLE.md"
    deliv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Registry append
    for hid, row in results.items():
        m = row["metrics"]
        reg = {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": hid,
            "state": "parked" if row["verdict"] == "PARK" else (
                "killed" if row["verdict"] == "KILL" else "preregistered"
            ),
            "verdict": f"OFFLINE_{row['verdict']}",
            "reason": (
                f"offline closed-bar N={m['n']} PF={m['pf']:.3f} tpw={m['tpw']:.2f}; "
                f"Model0 blocked unrelated Real terminal64"
            ),
            "updated_at": "2026-07-14",
            "lane": "discovery_wave3_20260714",
            "feature_family": hid,
            "symbol": "USDJPY",
            "timeframe": row["tf"],
            "window": "2021.01.01-2025.12.31",
            "model": "offline_closed_bar_probe",
            "source_path": f"03. EA Developer/{row['ea']}/{row['ea']}.mq5",
            "run_ids": [],
            "metrics": m,
            "validation": {
                "model0": "BLOCKED_UNRELATED_TERMINAL64",
                "offline_probe": row["verdict"],
                "cost_stress": "not_run",
            },
            "receipt_sha256": receipt_sha,
        }
        with REG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

        # Per-ID readout
        rd = READ / f"20260714_{hid.replace('-', '_')}_OFFLINE_PROBE_READOUT.md"
        rd.write_text(
            f"# Readout offline — {hid}\n\n"
            f"Status: `{row['verdict']}` / Model0 **BLOCKED**\n\n"
            f"| Metric | Value |\n|---|---:|\n"
            f"| N | {m['n']} |\n| PF | {m['pf']:.3f} |\n| tpw | {m['tpw']:.2f} |\n"
            f"| Net$ | {m['net']:.2f} |\n| Exp$/t | {m['exp']:.2f} |\n"
            f"| WinRate | {m['win_rate']:.3f} |\n\n"
            f"NOT Model 0. NOT GOAL. No densify.\n"
            f"Receipt `{receipt_sha}`.\n",
            encoding="utf-8",
        )

    print(json.dumps({"receipt_sha": receipt_sha, "results": {
        k: {"verdict": v["verdict"], **{kk: v["metrics"][kk] for kk in ("n", "pf", "tpw", "exp")}}
        for k, v in results.items()
    }}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
