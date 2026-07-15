#!/usr/bin/env python3
"""Round 10 greenfield — outside R1–R9 + unpark + exit + FRED densify boards.

FORBIDDEN densify (do not probe / retune):
  ≠ R1–R9 FX3 H4 path / triad / NAS / metal / CHF / COM3 / ADR /
    corr / yen-β / Parkinson / synth-resid / ON-ratio / tickvol
  ≠ Unpark W1/M15 / spring / PB / majority / TSMOM / solo / accept /
    split / halfback / disp / ER
  ≠ XS residual books / AUDNZD ZMR / AONIA / CORRA / thin3 / carry /
    exit / FRED / LNY / TOM / weekend-gap / ORB / NR7 / VWAP / SB

A priori (lead self-merge; Task nested critic unavailable):
  1) HYP-USDJPY-H1-TOKYO-LUNCH-FADE-001
  2) HYP-FX3-H1-LONDON-OPEN-DRIVE-CONT-001
  3) HYP-GBPUSD-H1-NY-REOPEN-CONT-001

+$12 joint. Model 0 only if PROBE_SURVIVOR.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

OUT_JSON = PRE / "20260715_GREENFIELD_R10_SESSION_EDGE_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_R10_SESSION_EDGE_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_R10_SESSION_EDGE_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_R10_SESSION_EDGE_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_R10_SESSION_EDGE_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_R10_SESSION_EDGE_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_R10_SESSION_EDGE_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R10_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 Tokyo lunch fade — morning impulse 00-02 UTC, fade at 03 UTC
TK_IMPULSE_HOURS = (0, 1, 2)
TK_FIRE = 3
TK_MIN_ATR = 0.80
TK_SL = 1.20
TK_RR = 1.50
TK_HOLD = 6
TK_MAX = 1

# 2 London open drive — closed 07:00 UTC H1 (London open hour)
LDN_BAR_HOUR = 7
LDN_BODY_ATR = 0.70
LDN_CLOSE_FRAC = 0.30  # close in top/bottom 30% of range
LDN_SL = 1.20
LDN_RR = 2.00
LDN_HOLD = 8
LDN_MAX = 1

# 3 GBP NY reopen — London AM net 07-12 UTC, fire 13 UTC continue
NY_AM_HOURS = range(7, 13)
NY_FIRE = 13
NY_MIN_ATR = 1.00
NY_SL = 1.20
NY_RR = 1.80
NY_HOLD = 10
NY_MAX = 1


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls):
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls):
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls):
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


def joint_verdict(m, hc):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0:
        notes.append("cadence_fail")
    if hc["x1_5"]["pf"] is None or hc["x1_5"]["pf"] < 1.25:
        notes.append("stress_fail")
    return ("PROBE_SURVIVOR", []) if not notes else ("KILLED_AT_OFFLINE_PROBE", notes)


def atr_arr(h, l, c, n=14):
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    out = np.full_like(tr, np.nan, dtype=float)
    s = tr[:n].sum()
    out[n - 1] = s / n
    for i in range(n, len(tr)):
        s = s - tr[i - n] + tr[i]
        out[i] = s / n
    return out


def load(symbol, tf, fr=FROM, to=TO):
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, tf, fr, to)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"{symbol} tf={tf}: {mt5.last_error()}")
    return {
        "t": rates["time"].astype(np.int64),
        "o": rates["open"].astype(float),
        "h": rates["high"].astype(float),
        "l": rates["low"].astype(float),
        "c": rates["close"].astype(float),
    }


def enrich(d):
    d["atr"] = atr_arr(d["h"], d["l"], d["c"])
    return d


def pip_size(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.01 if "JPY" in symbol else 0.0001
    return info.point * (10 if info.digits in (3, 5) else 1)


def cash_pnl(symbol, side, entry, exit_px, lots):
    info = mt5.symbol_info(symbol)
    tick_val = float(info.trade_tick_value) if info else 1.0
    tick_size = float(info.trade_tick_size) if info else pip_size(symbol)
    if tick_size <= 0:
        tick_size = pip_size(symbol)
    return (exit_px - entry) * side / tick_size * tick_val * lots


def risk_lots(symbol, entry, sl):
    info = mt5.symbol_info(symbol)
    risk = DEPOSIT * RISK_FRAC
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss = dist / tick_size * tick_val
    if loss <= 0:
        return 0.01
    return min(5.0, max(0.01, math.floor(risk / loss * 100) / 100))


def manage_exits(open_pos, data, ts, closed, hold_limit):
    still = []
    for pos in open_pos:
        sym = pos["sym"]
        d = data[sym]
        idx = int(np.searchsorted(d["t"], ts, side="left"))
        if idx >= len(d["t"]) or d["t"][idx] != ts:
            still.append(pos)
            continue
        exit_px = None
        reason = None
        if pos["side"] > 0:
            if d["l"][idx] <= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["h"][idx] >= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        else:
            if d["h"][idx] >= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["l"][idx] <= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        pos["bars"] += 1
        if exit_px is None and pos["bars"] >= hold_limit:
            exit_px, reason = d["c"][idx], "time"
        if exit_px is not None:
            closed.append(
                {
                    "pnl": cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"]),
                    "reason": reason,
                    "sym": sym,
                }
            )
        else:
            still.append(pos)
    return still


def flush_open(open_pos, data, closed):
    for pos in open_pos:
        d = data[pos["sym"]]
        closed.append(
            {
                "pnl": cash_pnl(
                    pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]
                ),
                "reason": "eod",
                "sym": pos["sym"],
            }
        )


def summarize(closed):
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail


def pack_result(hid, setup, symbol, timeframe, pnls, detail):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "setup": setup,
        "symbol": symbol,
        "timeframe": timeframe,
        "metrics": m,
        "haircuts": hc,
        "verdict": verdict,
        "fail_notes": notes,
        "detail": detail,
    }


def probe_tokyo_lunch(data):
    """Fade Tokyo morning impulse into lunch (03 UTC) on USDJPY H1."""
    d = data["USDJPY"]
    closed, open_pos = [], []
    last_day, day_count = None, 0
    # Index bars by (date, hour) for impulse lookback
    by_dh = {}
    for i, ts in enumerate(d["t"]):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        by_dh[(dt.date(), dt.hour)] = i

    for i in range(len(d["t"]) - 2):
        ts = int(d["t"][i])
        open_pos = manage_exits(open_pos, {"USDJPY": d}, ts, closed, TK_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5 or dt.hour != TK_FIRE:
            continue
        if day_count >= TK_MAX or open_pos:
            continue
        atr = d["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        # Morning net move using CLOSED bars 00,01,02 — all must exist and be closed
        # Signal bar is 03 UTC closed bar; impulse uses prior same-day hours.
        idxs = []
        ok = True
        for h in TK_IMPULSE_HOURS:
            j = by_dh.get((day, h))
            if j is None or j >= i:
                ok = False
                break
            idxs.append(j)
        if not ok or not idxs:
            continue
        morning_open = float(d["o"][idxs[0]])
        morning_close = float(d["c"][idxs[-1]])
        move = morning_close - morning_open
        if abs(move) < TK_MIN_ATR * atr:
            continue
        # Fade: morning up → short
        side = -1 if move > 0 else 1
        entry = float(d["o"][i + 1])
        sl = entry - side * TK_SL * atr
        tp = entry + side * TK_RR * TK_SL * atr
        lots = risk_lots("USDJPY", entry, sl)
        open_pos.append(
            {
                "sym": "USDJPY",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        day_count += 1
    flush_open(open_pos, {"USDJPY": d}, closed)
    return summarize(closed)


def probe_london_open_drive(data):
    """Continue London open-hour drive on first eligible FX3."""
    closed, open_pos = [], []
    last_day, day_count = None, 0
    # Use EURUSD clock
    clock = data["EURUSD"]["t"]
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, LDN_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5 or dt.hour != LDN_BAR_HOUR:
            continue
        if day_count >= LDN_MAX or open_pos:
            continue
        # Pick first FX3 with qualifying closed 07:00 bar
        chosen = None
        for sym in FX3:
            d = data[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j >= len(d["t"]) or d["t"][j] != ts:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            o, h, l, c = d["o"][j], d["h"][j], d["l"][j], d["c"][j]
            rng = h - l
            if rng <= 0:
                continue
            body = abs(c - o)
            if body < LDN_BODY_ATR * atr:
                continue
            if c > o:
                # bullish: close in top fraction
                if (h - c) / rng > LDN_CLOSE_FRAC:
                    continue
                side = 1
            else:
                if (c - l) / rng > LDN_CLOSE_FRAC:
                    continue
                side = -1
            # Entry next open on this symbol
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * LDN_SL * atr
            tp = entry + side * LDN_RR * LDN_SL * atr
            lots = risk_lots(sym, entry, sl)
            chosen = {
                "sym": sym,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
            break
        if chosen:
            open_pos.append(chosen)
            day_count += 1
    flush_open(open_pos, {s: data[s] for s in FX3}, closed)
    return summarize(closed)


def probe_gbp_ny_reopen(data):
    """Continue London AM GBP move into NY reopen (13 UTC)."""
    d = data["GBPUSD"]
    closed, open_pos = [], []
    last_day, day_count = None, 0
    by_dh = {}
    for i, ts in enumerate(d["t"]):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        by_dh[(dt.date(), dt.hour)] = i

    for i in range(len(d["t"]) - 2):
        ts = int(d["t"][i])
        open_pos = manage_exits(open_pos, {"GBPUSD": d}, ts, closed, NY_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5 or dt.hour != NY_FIRE:
            continue
        if day_count >= NY_MAX or open_pos:
            continue
        atr = d["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        idxs = []
        ok = True
        for h in NY_AM_HOURS:
            j = by_dh.get((day, h))
            if j is None or j >= i:
                ok = False
                break
            idxs.append(j)
        if not ok or not idxs:
            continue
        am_open = float(d["o"][idxs[0]])
        am_close = float(d["c"][idxs[-1]])
        move = am_close - am_open
        if abs(move) < NY_MIN_ATR * atr:
            continue
        side = 1 if move > 0 else -1
        entry = float(d["o"][i + 1])
        sl = entry - side * NY_SL * atr
        tp = entry + side * NY_RR * NY_SL * atr
        lots = risk_lots("GBPUSD", entry, sl)
        open_pos.append(
            {
                "sym": "GBPUSD",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        day_count += 1
    flush_open(open_pos, {"GBPUSD": d}, closed)
    return summarize(closed)


def append_reg(results, receipt):
    stamp = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"].startswith("KILLED") else "probe",
                "verdict": r["verdict"],
                "parent_candidate": None,
                "feature_family": "greenfield_r10_session_edge",
                "lane": "strategy_shift_r10_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": "R10 session-edge outside R1-R9 densify; lead self-merge",
                "prereg_path": None,
                "readout_path": str(OUT_MD.as_posix()),
                "metrics": r["metrics"],
                "validation": {
                    "cost_stress_apriori_usd": BASE_COST,
                    "haircuts": r["haircuts"],
                    "verdict": r["verdict"],
                    "fail_notes": r["fail_notes"],
                    "receipt_sha256": receipt,
                },
                "updated_at": stamp,
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                "receipt_sha256": receipt,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results, receipt, any_surv, qnote, clean_book_note):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    def row(r):
        return (
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
            f"{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE', 'KILL')} |"
        )

    table = [
        "| Object | N | PF | tpw | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ] + [row(r) for r in results]

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — Round 10 session-edge greenfield",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast` — Task backend unavailable;",
                "lead self-merge (same as Round7 precedent).",
                "",
                "## Named classes",
                "1. `USDJPY_TOKYO_LUNCH_FADE` — rank 1",
                "2. `FX3_LONDON_OPEN_DRIVE_CONT` — rank 2",
                "3. `GBPUSD_NY_REOPEN_CONT` — rank 3",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — true session microstructure; ≠ Asia-range Spark / ON-ratio |",
                "| Quant | SOFT — session filters reduce N; cost-fragile fades |",
                "| MQL5/MT5 | PASS — closed-bar impulse lookback; next-open entry |",
                "",
                "INTAKE_KILL: none.",
                "Model 0: **WITHHELD** until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 10 Tokyo lunch / London drive / NY reopen",
                "",
                "Date: 2026-07-15",
                "",
                f"## 1 `HYP-USDJPY-H1-TOKYO-LUNCH-FADE-001`",
                f"Morning net 00–02 UTC ≥{TK_MIN_ATR} ATR; fire 03 UTC fade; "
                f"SL={TK_SL} RR={TK_RR} hold≤{TK_HOLD}.",
                "",
                f"## 2 `HYP-FX3-H1-LONDON-OPEN-DRIVE-CONT-001`",
                f"Closed 07 UTC H1 body≥{LDN_BODY_ATR} ATR + close in extreme "
                f"{LDN_CLOSE_FRAC}; continue; first FX3; SL={LDN_SL} RR={LDN_RR} hold≤{LDN_HOLD}.",
                "",
                f"## 3 `HYP-GBPUSD-H1-NY-REOPEN-CONT-001`",
                f"London AM 07–12 net ≥{NY_MIN_ATR} ATR; fire 13 UTC continue; "
                f"SL={NY_SL} RR={NY_RR} hold≤{NY_HOLD}.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 10 session-edge",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| Tokyo lunch fade | ≠ Spark Asian range break; ≠ ON-ratio; ≠ weekend-gap; ≠ LNY |",
                "| London open drive | ≠ FX3 H4 path R1–R5; ≠ majority/TS; ≠ ORB densify (object=H1 body@07) |",
                "| NY reopen cont | ≠ majority lag; ≠ accept window; ≠ exit packs |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 10 session-edge",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Status: `{status}`",
                f"Cost a priori: +${BASE_COST:.0f}/trade",
                f"QFSI parallel: {qnote}",
                "",
                *table,
                "",
                "## Fail notes",
                *[
                    f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}"
                    for r in results
                ],
                "",
                "## Model 0",
                "AUTHORIZED only if any PROBE_SURVIVOR; else WITHHELD.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — Round 10 session-edge",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify Tokyo lunch / London drive / NY reopen params.",
                "Next: next true greenfield outside R10 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 10 session-edge greenfield",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R9 + unpark + exit + FRED. Nested critic Task unavailable → lead self-merge.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify Tokyo-lunch / London-drive / NY-reopen.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R10 **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN brief — Clean book + Round 10 (post STRATEGY SHIFT)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book path quanh Phase-0 CONTAMINATED + discovery R10.",
                "GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Freeze a priori trước metrics; **không** clear Phase-0 contamination.",
                "- Model 0 book-level: **WITHHELD** (offline pool ≠ EA challenger).",
                "",
                "## 2. Discovery Round 10 — session-edge",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "Spot-check: watcher/capture/Real LIVE — không babysit.",
                "",
                "## Cấm",
                "Densify R1–R9 / unpark / exit / FRED / R10 session params / Phase-0 ceremony.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R10; cost provenance khi Owner drop deal-export.",
                "Best shelf RR2 `194548`. Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, receipt, any_surv, qnote, clean_note):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines_r = []
    for i, r in enumerate(results, 1):
        m, hc = r["metrics"], r["haircuts"]
        lines_r.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} x1.5={hc['x1_5']['pf']})."
        )
    block = [
        "",
        f"- **CLEAN BOOK + R10 SESSION-EDGE CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `CLEAN_BOOK_OFFLINE` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  Clean-lane book hyp (NOT Phase-0 ceremony):",
        "  `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001` — freeze",
        "  `readouts/20260715_CLEAN_BOOK_APRIORI_UNIVERSE_FREEZE.md` then stress",
        "  `preflight/20260715_CLEAN_BOOK_APRIORI_RR2SPARK_STRESS.json`.",
        f"  {clean_note}",
        "  Model 0 book-level WITHHELD (offline pool ≠ EA challenger).",
        "  Phase-0 attestation still CONTAMINATED — not cleared.",
        "  Round10 greenfield outside R1–R9/unpark/exit/FRED densify.",
        "  Nested critic Task unavailable → lead self-merge `cursor-grok-4.5-high-fast`.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_R10_SESSION_EDGE_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R10_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify Tokyo lunch / London drive / NY reopen /",
        "  R1–R9 / unpark / triad / exit / FRED / residual/corr/Parkinson/ON-ratio.",
        "  Next: next true greenfield outside R10 — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Clean book + R10 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    # Remove prior same closeout if re-run
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **CLEAN BOOK + R10 SESSION-EDGE CLOSEOUT"):
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("- **") or (
                    nxt.startswith("## ") and "Active Truth" not in nxt
                ):
                    break
                if nxt.strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith(
                    "- **"
                ):
                    i += 1
                    break
                i += 1
            continue
        cleaned.append(ln)
        i += 1
    out = []
    inserted = False
    for ln in cleaned:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def qfsi_parallel_note() -> str:
    hb = PRE / "20260715_QFSI_007_WATCHER_HEARTBEAT.json"
    prog = (
        ROOT
        / "02. AlphaFactory"
        / "evidence"
        / "execution"
        / "FivePercentOnline-Real"
        / "20260715_QFSI_REAL_007_LONG_ACCUMULATE"
        / "capture_progress.json"
    )
    parts = []
    if hb.exists():
        try:
            h = json.loads(hb.read_text(encoding="utf-8"))
            parts.append(
                f"watcher_hb ts={h.get('ts')} alive={h.get('watcher_alive')} "
                f"cap_pid={h.get('capture_pid')} wall_rem={h.get('wall_remaining_sec')}"
            )
        except json.JSONDecodeError:
            parts.append("watcher_hb unreadable")
    else:
        parts.append("watcher_hb missing")
    if prog.exists():
        try:
            p = json.loads(prog.read_text(encoding="utf-8"))
            parts.append(
                f"007 accumulate hb={p.get('heartbeat_rows')} quotes={p.get('quote_rows')} "
                f"deadline={p.get('deadline_utc')}"
            )
        except json.JSONDecodeError:
            parts.append("007 progress unreadable")
    parts.append("cost freeze still GAP; login not headline")
    return "; ".join(parts)


def load_clean_book_note() -> str:
    path = PRE / "20260715_CLEAN_BOOK_APRIORI_RR2SPARK_STRESS.json"
    if not path.exists():
        return "Clean-book stress JSON missing — run stress first."
    p = json.loads(path.read_text(encoding="utf-8"))
    prim = p["books"]["PRIMARY_BOOK"]
    ext = p["books"]["EXTENDED_BOOK"]
    return (
        f"PRIMARY PF@$12={prim['pooled_after_heat']['pf_haircut']:.3f} "
        f"tpw={prim['pooled_after_heat']['tpw']:.3f} "
        f"verdict=`{prim['goal_screen']['verdict']}`; "
        f"EXTENDED PF@$12={ext['pooled_after_heat']['pf_haircut']:.3f} "
        f"tpw={ext['pooled_after_heat']['tpw']:.3f} "
        f"verdict=`{ext['goal_screen']['verdict']}`; "
        f"freeze_sha={p.get('freeze_sha256','')[:16]}…"
    )


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        data = {
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_H1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_H1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_H1)),
        }
        results = [
            pack_result(
                "HYP-USDJPY-H1-TOKYO-LUNCH-FADE-001",
                "usdjpy_h1_tokyo_lunch_fade",
                "USDJPY",
                "H1",
                *probe_tokyo_lunch(data),
            ),
            pack_result(
                "HYP-FX3-H1-LONDON-OPEN-DRIVE-CONT-001",
                "fx3_h1_london_open_drive_cont",
                "FX3",
                "H1",
                *probe_london_open_drive(data),
            ),
            pack_result(
                "HYP-GBPUSD-H1-NY-REOPEN-CONT-001",
                "gbpusd_h1_ny_reopen_cont",
                "GBPUSD",
                "H1",
                *probe_gbp_ny_reopen(data),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r10_session_edge.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "tokyo_lunch": {
                    "impulse_hours": list(TK_IMPULSE_HOURS),
                    "fire": TK_FIRE,
                    "min_atr": TK_MIN_ATR,
                    "sl": TK_SL,
                    "rr": TK_RR,
                    "hold": TK_HOLD,
                },
                "london_drive": {
                    "bar_hour": LDN_BAR_HOUR,
                    "body_atr": LDN_BODY_ATR,
                    "close_frac": LDN_CLOSE_FRAC,
                    "sl": LDN_SL,
                    "rr": LDN_RR,
                    "hold": LDN_HOLD,
                },
                "ny_reopen": {
                    "am_hours": list(NY_AM_HOURS),
                    "fire": NY_FIRE,
                    "min_atr": NY_MIN_ATR,
                    "sl": NY_SL,
                    "rr": NY_RR,
                    "hold": NY_HOLD,
                },
            },
            "qfsi_parallel": qnote,
            "clean_book_parallel": clean_note,
            "results": results,
            "any_probe_survivor": any_surv,
            "model0": "AUTHORIZED_IF_SURVIVOR" if any_surv else "WITHHELD",
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        write_docs(results, receipt, any_surv, qnote, clean_note)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, qnote, clean_note)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_surv": any_surv,
                    "clean_book": clean_note,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            "n": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "x1_5": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["fail_notes"],
                        }
                        for r in results
                    ],
                    "qfsi": qnote,
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
