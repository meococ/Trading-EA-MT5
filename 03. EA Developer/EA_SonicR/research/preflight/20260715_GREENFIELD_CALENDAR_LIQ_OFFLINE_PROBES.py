#!/usr/bin/env python3
"""Independent greenfield offline probes — calendar/liquidity class.

Outside ALL recent kill shelves:
  ≠ carry densify (Mon→Thu / flush / anticarry×vol)
  ≠ D1 vol-regime / swing ADX-thrust / entry-state / RR2 exit
  ≠ FRED displace / LNY / XS residual-mom / 6J / USBILL

A priori (≥2), +$12 cost haircut (research screen; cost freeze still GAP):
  1) HYP-FX3-H4-TURNMONTH-LIQ-BOOK-001
  2) HYP-FX3-H1-WEEKEND-GAP-FADE-001

Model 0 only if PROBE_SURVIVOR.
"""
from __future__ import annotations

import calendar
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

OUT_JSON = PRE / "20260715_GREENFIELD_CALENDAR_LIQ_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_CALENDAR_LIQ_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_CALENDAR_LIQ_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_CALENDAR_LIQ_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_CALENDAR_LIQ_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_CALENDAR_LIQ_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY")

# Object 1 — turn-of-month liquidity continuation
TOM_SL_ATR = 1.5
TOM_MAX_HOLD_H4 = 6
TOM_RR = 2.0
TOM_MAX_OPEN = 2
TOM_MOM_LB = 5  # D1 closes

# Object 2 — weekend gap fade
GAP_MIN_ATR = 0.35
GAP_SL_BUF = 0.15  # ATR beyond gap extreme
GAP_RR = 1.5
GAP_MAX_HOLD_H1 = 12
GAP_MAX_OPEN = 2


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
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0:
        notes.append("cadence_fail")
    x15 = hc["x1_5"]["pf"]
    if x15 is None or x15 < 1.25:
        notes.append("stress_fail")
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "PROBE_SURVIVOR", []


def atr_arr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    out = np.full_like(tr, np.nan, dtype=float)
    if len(tr) < n:
        return out
    s = tr[:n].sum()
    out[n - 1] = s / n
    for i in range(n, len(tr)):
        s = s - tr[i - n] + tr[i]
        out[i] = s / n
    return out


def load_tf(symbol: str, tf: int) -> dict[str, np.ndarray]:
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"rates fail {symbol} tf={tf}: {mt5.last_error()}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def pip_size(symbol: str) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.0001 if "JPY" not in symbol else 0.01
    return info.point * (10 if info.digits in (3, 5) else 1)


def cash_pnl(symbol: str, side: int, entry: float, exit_px: float, lots: float) -> float:
    info = mt5.symbol_info(symbol)
    tick_val = float(info.trade_tick_value) if info else 1.0
    tick_size = float(info.trade_tick_size) if info else pip_size(symbol)
    if tick_size <= 0:
        tick_size = pip_size(symbol)
    move = (exit_px - entry) * side
    return move / tick_size * tick_val * lots


def risk_lots(symbol: str, entry: float, sl: float) -> float:
    info = mt5.symbol_info(symbol)
    risk = DEPOSIT * RISK_FRAC
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss_per_lot = dist / tick_size * tick_val
    if loss_per_lot <= 0:
        return 0.01
    lots = max(0.01, math.floor(risk / loss_per_lot * 100) / 100)
    return min(lots, 5.0)


def month_end_trading_days(year: int, month: int) -> list[date]:
    """Last 2 weekdays of month + first 2 weekdays of next month (TOM window)."""
    last = date(year, month, calendar.monthrange(year, month)[1])
    # walk back for weekdays in month
    end_days: list[date] = []
    d = last
    while len(end_days) < 2 and d.month == month:
        if d.weekday() < 5:
            end_days.append(d)
        d -= timedelta(days=1)
    end_days = list(reversed(end_days))
    # next month first 2
    if month == 12:
        ny, nm = year + 1, 1
    else:
        ny, nm = year, month + 1
    start_days: list[date] = []
    d = date(ny, nm, 1)
    while len(start_days) < 2:
        if d.weekday() < 5:
            start_days.append(d)
        d += timedelta(days=1)
    return end_days + start_days


def build_tom_set() -> set[date]:
    s: set[date] = set()
    for y in range(2020, 2027):
        for m in range(1, 13):
            for d in month_end_trading_days(y, m):
                if date(2021, 1, 1) <= d <= date(2025, 12, 31):
                    s.add(d)
    return s


def simulate_book(trades: list[dict]) -> list[float]:
    """trades: list with entry_t, exit_t, pnl — already sized; just return pnls chrono."""
    trades = sorted(trades, key=lambda t: t["entry_t"])
    return [t["pnl"] for t in trades]


def probe_turnmonth(sym_data: dict[str, dict]) -> tuple[list[float], dict]:
    tom = build_tom_set()
    open_pos: list[dict] = []
    closed: list[dict] = []
    # Align on each symbol independently; book cap across symbols
    # Iterate global H4 timeline from EURUSD as clock
    clock = sym_data["EURUSD"]["h4"]["time"]
    # Precompute per-symbol ATR and D1 mom
    meta: dict[str, Any] = {}
    for sym, d in sym_data.items():
        h4, d1 = d["h4"], d["d1"]
        atr = atr_arr(h4["high"], h4["low"], h4["close"], 14)
        # map D1 date -> close idx
        d1_dates = [datetime.utcfromtimestamp(int(t)).date() for t in d1["time"]]
        meta[sym] = {"atr": atr, "d1_dates": d1_dates, "d1_close": d1["close"]}

    for i, ts in enumerate(clock):
        dt = datetime.utcfromtimestamp(int(ts))
        d = dt.date()
        # manage exits first
        still = []
        for pos in open_pos:
            sym = pos["sym"]
            h4 = sym_data[sym]["h4"]
            # find bar index for this ts on symbol
            idx = int(np.searchsorted(h4["time"], ts, side="left"))
            if idx >= len(h4["time"]) or h4["time"][idx] != ts:
                still.append(pos)
                continue
            hi, lo, cl = h4["high"][idx], h4["low"][idx], h4["close"][idx]
            exit_px = None
            reason = None
            if pos["side"] > 0:
                if lo <= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif hi >= pos["tp"]:
                    exit_px, reason = pos["tp"], "tp"
            else:
                if hi >= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif lo <= pos["tp"]:
                    exit_px, reason = pos["tp"], "tp"
            bars_held = pos.get("bars", 0) + 1
            pos["bars"] = bars_held
            if exit_px is None and bars_held >= TOM_MAX_HOLD_H4:
                exit_px, reason = cl, "time"
            if exit_px is not None:
                pnl = cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"])
                closed.append({"entry_t": pos["entry_t"], "exit_t": int(ts), "pnl": pnl, "reason": reason, "sym": sym})
            else:
                still.append(pos)
        open_pos = still

        if d not in tom:
            continue
        if dt.weekday() >= 5:
            continue
        # only first H4 of day ≥ 08 UTC to avoid Asia thin (a priori)
        if dt.hour < 8:
            continue
        if len(open_pos) >= TOM_MAX_OPEN:
            continue
        open_syms = {p["sym"] for p in open_pos}
        for sym in UNIVERSE:
            if sym in open_syms or len(open_pos) >= TOM_MAX_OPEN:
                continue
            h4 = sym_data[sym]["h4"]
            idx = int(np.searchsorted(h4["time"], ts, side="left"))
            if idx < 20 or idx >= len(h4["time"]) or h4["time"][idx] != ts:
                continue
            # one entry per symbol per TOM day
            if any(p["sym"] == sym and datetime.utcfromtimestamp(p["entry_t"]).date() == d for p in open_pos):
                continue
            if any(
                c["sym"] == sym and datetime.utcfromtimestamp(c["entry_t"]).date() == d for c in closed
            ):
                continue
            atr = meta[sym]["atr"][idx]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # D1 momentum: last closed D1 before today
            d1_dates = meta[sym]["d1_dates"]
            d1_close = meta[sym]["d1_close"]
            j = len(d1_dates) - 1
            while j >= 0 and d1_dates[j] >= d:
                j -= 1
            if j < TOM_MOM_LB:
                continue
            mom = d1_close[j] - d1_close[j - TOM_MOM_LB]
            if abs(mom) < 0.15 * atr:  # need directional bias vs H4 ATR scale
                # use D1 ATR-ish: skip tiny
                continue
            side = 1 if mom > 0 else -1
            entry = float(h4["open"][idx])  # closed-bar: signal on prior; enter open of signal bar after D1 known
            # Actually: D1 known after prior day close → can enter any H4 on TOM day at open of bar i (no lookahead)
            sl = entry - side * TOM_SL_ATR * atr
            tp = entry + side * TOM_RR * TOM_SL_ATR * atr
            lots = risk_lots(sym, entry, sl)
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": lots,
                    "entry_t": int(ts),
                    "bars": 0,
                }
            )
            open_syms.add(sym)

    # force flat remaining at end
    for pos in open_pos:
        sym = pos["sym"]
        h4 = sym_data[sym]["h4"]
        cl = float(h4["close"][-1])
        pnl = cash_pnl(sym, pos["side"], pos["entry"], cl, pos["lots"])
        closed.append({"entry_t": pos["entry_t"], "exit_t": int(h4["time"][-1]), "pnl": pnl, "reason": "eod", "sym": sym})

    pnls = simulate_book(closed)
    detail = {
        "n_signals": len(closed),
        "by_reason": {},
        "by_sym": {},
    }
    for c in closed:
        detail["by_reason"][c["reason"]] = detail["by_reason"].get(c["reason"], 0) + 1
        detail["by_sym"][c["sym"]] = detail["by_sym"].get(c["sym"], 0) + 1
    return pnls, detail


def probe_weekend_gap(sym_data: dict[str, dict]) -> tuple[list[float], dict]:
    closed: list[dict] = []
    open_pos: list[dict] = []

    # Build Friday close / Monday first H1 pairs per symbol
    for sym in UNIVERSE:
        h1 = sym_data[sym]["h1"]
        d1 = sym_data[sym]["d1"]
        atr_d1 = atr_arr(d1["high"], d1["low"], d1["close"], 14)
        d1_date = [datetime.utcfromtimestamp(int(t)).date() for t in d1["time"]]
        # index Monday bars
        for i in range(1, len(h1["time"])):
            dt = datetime.utcfromtimestamp(int(h1["time"][i]))
            if dt.weekday() != 0:  # Monday
                continue
            # first Monday H1 only (00-01 or broker's first)
            prev = datetime.utcfromtimestamp(int(h1["time"][i - 1]))
            if prev.weekday() == 0:
                continue  # not first Monday bar
            # Friday close = last bar before weekend
            j = i - 1
            while j >= 0 and datetime.utcfromtimestamp(int(h1["time"][j])).weekday() > 4:
                j -= 1
            if j < 0:
                continue
            fri = datetime.utcfromtimestamp(int(h1["time"][j]))
            if fri.weekday() != 4:
                # find last Friday
                while j >= 0 and datetime.utcfromtimestamp(int(h1["time"][j])).weekday() != 4:
                    j -= 1
                if j < 0:
                    continue
                fri = datetime.utcfromtimestamp(int(h1["time"][j]))
            fri_close = float(h1["close"][j])
            mon_open = float(h1["open"][i])
            gap = mon_open - fri_close
            # D1 ATR as of Friday date
            fd = fri.date()
            di = len(d1_date) - 1
            while di >= 0 and d1_date[di] > fd:
                di -= 1
            if di < 14 or not np.isfinite(atr_d1[di]) or atr_d1[di] <= 0:
                continue
            if abs(gap) < GAP_MIN_ATR * atr_d1[di]:
                continue
            # fade the gap
            side = -1 if gap > 0 else 1
            entry = mon_open
            atr = atr_d1[di]
            if gap > 0:
                sl = mon_open + GAP_SL_BUF * atr
            else:
                sl = mon_open - GAP_SL_BUF * atr
            # ensure SL beyond gap extreme
            if side < 0:
                sl = max(sl, mon_open + GAP_SL_BUF * atr)
            else:
                sl = min(sl, mon_open - GAP_SL_BUF * atr)
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + side * GAP_RR * risk
            lots = risk_lots(sym, entry, sl)
            # simulate forward on H1
            exit_px = None
            reason = None
            exit_t = int(h1["time"][i])
            for k in range(i, min(i + GAP_MAX_HOLD_H1, len(h1["time"]))):
                hi, lo, cl = h1["high"][k], h1["low"][k], h1["close"][k]
                if side > 0:
                    if lo <= sl:
                        exit_px, reason, exit_t = sl, "sl", int(h1["time"][k])
                        break
                    if hi >= tp:
                        exit_px, reason, exit_t = tp, "tp", int(h1["time"][k])
                        break
                else:
                    if hi >= sl:
                        exit_px, reason, exit_t = sl, "sl", int(h1["time"][k])
                        break
                    if lo <= tp:
                        exit_px, reason, exit_t = tp, "tp", int(h1["time"][k])
                        break
                exit_px, reason, exit_t = cl, "time", int(h1["time"][k])
            if exit_px is None:
                continue
            pnl = cash_pnl(sym, side, entry, exit_px, lots)
            closed.append(
                {
                    "entry_t": int(h1["time"][i]),
                    "exit_t": exit_t,
                    "pnl": pnl,
                    "reason": reason,
                    "sym": sym,
                    "gap_atr": abs(gap) / atr,
                }
            )

    # enforce book max open roughly by dropping overlapping extras (keep earliest)
    closed.sort(key=lambda t: t["entry_t"])
    active: list[dict] = []
    kept: list[dict] = []
    for t in closed:
        active = [a for a in active if a["exit_t"] > t["entry_t"]]
        if len(active) >= GAP_MAX_OPEN:
            continue
        if any(a["sym"] == t["sym"] for a in active):
            continue
        kept.append(t)
        active.append(t)

    pnls = [t["pnl"] for t in kept]
    detail = {
        "n_raw": len(closed),
        "n_kept": len(kept),
        "by_reason": {},
        "by_sym": {},
        "median_gap_atr": None
        if not kept
        else round(float(np.median([t["gap_atr"] for t in kept])), 4),
    }
    for c in kept:
        detail["by_reason"][c["reason"]] = detail["by_reason"].get(c["reason"], 0) + 1
        detail["by_sym"][c["sym"]] = detail["by_sym"].get(c["sym"], 0) + 1
    return pnls, detail


def write_docs(results: list[dict], receipt: str, any_survivor: bool) -> None:
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — Greenfield calendar/liquidity FX3",
                "",
                "Date: 2026-07-15",
                "Parent: anti-carry vol-spike ALL_KILL; G10 alt-source parallel.",
                "",
                "## Design 1 — Turn-of-month liquidity continuation",
                "`HYP-FX3-H4-TURNMONTH-LIQ-BOOK-001`",
                "Window = last 2 weekdays of month + first 2 of next.",
                "Direction = sign of prior 5 D1 closes; enter H4≥08 UTC;",
                f"SL {TOM_SL_ATR}×ATR14_H4; RR={TOM_RR}; hold≤{TOM_MAX_HOLD_H4}; book≤{TOM_MAX_OPEN}.",
                "",
                "## Design 2 — Weekend gap fade",
                "`HYP-FX3-H1-WEEKEND-GAP-FADE-001`",
                f"Monday first H1; |gap|≥{GAP_MIN_ATR}×ATR14_D1 vs Friday close;",
                f"fade gap; SL buffer {GAP_SL_BUF}×ATR; RR={GAP_RR}; hold≤{GAP_MAX_HOLD_H1} H1.",
                "",
                "## ≠ kill shelf",
                "≠ carry Mon→Thu/flush/anticarry; ≠ D1 volregime/swing; ≠ RR2 exit/entry;",
                "≠ FRED displace; ≠ LNY/XS; ≠ NR7/ORB/IB densify; ≠ 6J/USBILL.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    dedup_rows = [
        "| Object | Vs killed / banned shelf |",
        "|---|---|",
        "| TOM liq book | Calendar window liquidity ≠ session LNY/ORB; ≠ carry harvest Mon→Thu |",
        "| Weekend gap fade | Weekend microstructure ≠ Asia densify; ≠ D1 breakout; ≠ XS residual |",
    ]
    OUT_DEDUP.write_text(
        "# Dedup clearance — Greenfield calendar/liquidity\n\n" + "\n".join(dedup_rows) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Offline probes — Greenfield calendar/liquidity",
        "",
        f"Receipt SHA256: `{receipt}`",
        f"Generated: {utc_now()}",
        f"A priori cost: +${BASE_COST:.0f} (x1/x1.5/x2); cost freeze GAP.",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['hypothesis_id']}",
            "",
            f"- verdict: **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
            f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']}",
            f"- x1.5 PF={r['haircuts']['x1_5']['pf']} x2 PF={r['haircuts']['x2']['pf']}",
            f"- detail: `{json.dumps(r['detail'], sort_keys=True)}`",
            "",
        ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    status = "PROBE_SURVIVOR_PRESENT" if any_survivor else "OFFLINE_ALL_KILL__NO_MODEL0"
    next_line = (
        "Model 0 prereg for survivors only."
        if any_survivor
        else (
            "G10 alt-source child if PANEL_READY; else another true greenfield "
            "outside calendar densify — not carry/D1/exit/FRED/LNY/XS."
        )
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — Greenfield calendar/liquidity",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "",
                f"Next: {next_line}",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Greenfield calendar/liquidity",
                "",
                f"- Trạng thái: `{status}` — không Model 0 trừ khi có survivor.",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                f"- Next: {next_line}",
                "- Best shelf RR2 `194548`. Cost freeze vẫn GAP. Login không phải headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_registry(results: list[dict], receipt: str) -> None:
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "parent_candidate": "post_anticarry_greenfield_calendar_20260715",
                "feature_family": "greenfield_calendar_liq_fx3",
                "lane": "greenfield_calendar_liq_20260715",
                "setup_type": r["setup_type"],
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
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
                "reason": ",".join(r["fail_notes"]) or "offline_pass",
                "updated_at": "2026-07-15",
            }
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def patch_hot(results: list[dict], receipt: str, any_survivor: bool) -> None:
    status = "PROBE_SURVIVOR_PRESENT" if any_survivor else "OFFLINE_ALL_KILL__NO_MODEL0"
    block = [
        f"- **GREENFIELD CALENDAR/LIQ CLOSEOUT (2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Independent greenfield after anti-carry ALL_KILL; parallel G10 alt-source.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        f"  `preflight/20260715_GREENFIELD_CALENDAR_LIQ_OFFLINE_PROBES.json`;",
        f"  closeout `readouts/20260715_GREENFIELD_CALENDAR_LIQ_SESSION_CLOSEOUT.md`;",
        f"  VN `readouts/20260715_GREENFIELD_CALENDAR_LIQ_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify TOM days / gap ATR / RR.",
        "  Next: G10 alt-source panel child if ready; else next true greenfield — "
        "not calendar densify, not carry/D1/exit/FRED/LNY/XS.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    # Update header stamp
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT | "
            f"Greenfield calendar/liq offline {status.split('__')[0]}; Real on; GOAL unmet"
        )
    # Insert after "## Active Truth"
    out: list[str] = []
    inserted = False
    for i, ln in enumerate(lines):
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    if not inserted:
        out = block + [""] + lines
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(f"mt5 init fail: {mt5.last_error()}")
    try:
        sym_data: dict[str, dict] = {}
        for sym in UNIVERSE:
            if not mt5.symbol_select(sym, True):
                raise SystemExit(f"symbol_select fail {sym}")
            sym_data[sym] = {
                "h4": load_tf(sym, mt5.TIMEFRAME_H4),
                "h1": load_tf(sym, mt5.TIMEFRAME_H1),
                "d1": load_tf(sym, mt5.TIMEFRAME_D1),
            }

        results: list[dict] = []
        pnls1, det1 = probe_turnmonth(sym_data)
        m1, h1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, h1)
        results.append(
            {
                "hypothesis_id": "HYP-FX3-H4-TURNMONTH-LIQ-BOOK-001",
                "setup_type": "TOM window H4 with 5D1 mom; SL1.5 ATR RR2 hold≤6",
                "timeframe": "H4",
                "family": "greenfield_calendar_liq_fx3",
                "metrics": m1,
                "haircuts": h1,
                "verdict": v1,
                "fail_notes": n1,
                "detail": det1,
            }
        )

        pnls2, det2 = probe_weekend_gap(sym_data)
        m2, h2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, h2)
        results.append(
            {
                "hypothesis_id": "HYP-FX3-H1-WEEKEND-GAP-FADE-001",
                "setup_type": "Mon H1 fade weekend gap≥0.35 ATR_D1; RR1.5 hold≤12",
                "timeframe": "H1",
                "family": "greenfield_calendar_liq_fx3",
                "metrics": m2,
                "haircuts": h2,
                "verdict": v2,
                "fail_notes": n2,
                "detail": det2,
            }
        )

        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema": "greenfield_calendar_liq_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "parent": "anticarry_volspike_ALL_KILL__g10_altsource_parallel",
            "base_cost_usd": BASE_COST,
            "window": {"from": "2021-01-01", "to": "2025-12-31"},
            "universe": list(UNIVERSE),
            "results": results,
            "any_survivor": any_surv,
            "model0_authorized": bool(any_surv),
            "receipt_sha256": None,
        }
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        any_surv = payload["any_survivor"]
        write_docs(results, receipt, any_surv)
        append_registry(results, receipt)
        patch_hot(results, receipt, any_surv)
        print(json.dumps({"receipt": receipt, "results": [
            {"id": r["hypothesis_id"], "verdict": r["verdict"], **r["metrics"], "x15": r["haircuts"]["x1_5"]["pf"]}
            for r in results
        ]}, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
