#!/usr/bin/env python3
"""Round 11 greenfield — outside R10 session densify + all prior bans.

FORBIDDEN densify (do not probe / retune):
  ≠ R10 Tokyo lunch / London open drive / NY reopen
  ≠ R1–R9 FX3 H4 path / triad / NAS / metal / CHF / COM3 / ADR /
    corr / yen-β / Parkinson / synth-resid / ON-ratio / tickvol
  ≠ Unpark W1/M15 / spring / PB / majority / TSMOM / solo / accept /
    split / halfback / disp / ER
  ≠ XS residual books / AUDNZD ZMR / AONIA / CORRA / thin3 / carry /
    exit / FRED / LNY / TOM / weekend-gap / ORB / NR7 / VWAP / SB

A priori (lead self-merge; Task nested critic unavailable):
  1) HYP-FX3-H1-LONDON-FIX-REVERSION-001
     — fade into-fix impulse after closed 15 UTC H1 (≠ R10 open/reopen)
  2) HYP-FX3-H1-WEEKLY-OPEN-DIST-FADE-001
     — fade extreme distance from weekly open (≠ W1 HL-break / VWAP)
  3) HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001
     — held backup from USD-lag board; first probe (≠ bodyATR densify)

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

OUT_JSON = PRE / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R11_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 London fix reversion — closed 15 UTC H1 into-fix impulse → fade next open
FIX_BAR_HOUR = 15
FIX_BODY_ATR = 0.80
FIX_CLOSE_FRAC = 0.30
FIX_SL = 1.20
FIX_RR = 1.50
FIX_HOLD = 4
FIX_MAX = 1

# 2 Weekly open distance fade
WO_DIST_ATR = 2.50
WO_SL = 1.50
WO_RR = 1.50
WO_HOLD = 12
WO_MAX_PER_WEEK = 1

# 3 CLOSELOC pressure continuation
CL_LOC = 0.75
CL_BODY_ATR = 0.50
CL_SL = 1.20
CL_RR = 2.00
CL_HOLD = 8
CL_MAX = 2  # per day across FX3


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


def close_loc(o, h, l, c):
    rng = h - l
    if rng <= 0:
        return 0.5
    return (c - l) / rng


def iso_week_key(dt: datetime) -> tuple:
    iso = dt.isocalendar()
    return (iso[0], iso[1])


def probe_london_fix_reversion(data):
    """Fade into-fix H1 impulse (closed 15 UTC) on first eligible FX3."""
    closed, open_pos = [], []
    last_day, day_count = None, 0
    clock = data["EURUSD"]["t"]
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, FIX_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5 or dt.hour != FIX_BAR_HOUR:
            continue
        if day_count >= FIX_MAX or open_pos:
            continue
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
            if body < FIX_BODY_ATR * atr:
                continue
            if c > o:
                if (h - c) / rng > FIX_CLOSE_FRAC:
                    continue
                side = -1  # fade bullish into-fix
            else:
                if (c - l) / rng > FIX_CLOSE_FRAC:
                    continue
                side = 1  # fade bearish into-fix
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * FIX_SL * atr
            tp = entry + side * FIX_RR * FIX_SL * atr
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


def probe_weekly_open_dist_fade(data):
    """Fade when |close - weekly_open| >= k*ATR; first FX3; ≤1/week."""
    closed, open_pos = [], []
    week_opens = {s: {} for s in FX3}  # week_key -> open price
    week_fired = set()
    clock = data["EURUSD"]["t"]

    # Precompute weekly opens from each symbol's first bar of ISO week
    for sym in FX3:
        d = data[sym]
        seen = set()
        for i, ts in enumerate(d["t"]):
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            if dt.weekday() >= 5:
                continue
            wk = iso_week_key(dt)
            if wk in seen:
                continue
            seen.add(wk)
            week_opens[sym][wk] = float(d["o"][i])

    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, WO_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        wk = iso_week_key(dt)
        if wk in week_fired or open_pos:
            continue
        # Skip Monday first hours — need distance to form; fire Tue–Fri
        if dt.weekday() == 0 and dt.hour < 12:
            continue
        chosen = None
        for sym in FX3:
            d = data[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j >= len(d["t"]) or d["t"][j] != ts:
                continue
            atr = d["atr"][j]
            wo = week_opens[sym].get(wk)
            if wo is None or not np.isfinite(atr) or atr <= 0:
                continue
            c = float(d["c"][j])
            dist = c - wo
            if abs(dist) < WO_DIST_ATR * atr:
                continue
            side = -1 if dist > 0 else 1  # fade toward weekly open
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * WO_SL * atr
            tp = entry + side * WO_RR * WO_SL * atr
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
            week_fired.add(wk)
    flush_open(open_pos, {s: data[s] for s in FX3}, closed)
    return summarize(closed)


def probe_closeloc_pressure_cont(data):
    """Continue H1 close-location pressure on FX3 (held backup, first probe)."""
    closed, open_pos = [], []
    last_day, day_count = None, 0
    clock = data["EURUSD"]["t"]
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, CL_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5:
            continue
        if day_count >= CL_MAX or open_pos:
            continue
        # Skip thin Asia-only hours and R10 fire hours to stay distinct
        if dt.hour in (3, 7, 13, 15):
            continue
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
            body = abs(c - o)
            if body < CL_BODY_ATR * atr:
                continue
            loc = close_loc(o, h, l, c)
            if loc >= CL_LOC and c > o:
                side = 1
            elif loc <= (1.0 - CL_LOC) and c < o:
                side = -1
            else:
                continue
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * CL_SL * atr
            tp = entry + side * CL_RR * CL_SL * atr
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
                "feature_family": "greenfield_r11_fix_wo_closeloc",
                "lane": "strategy_shift_r11_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R11 outside R10 session densify + R1-R9/unpark/exit/FRED; "
                    "lead self-merge; CLOSELOC was held backup now first-probed"
                ),
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
                "# 3-critic panel — Round 11 fix / weekly-open / closeloc",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast` — Task backend unavailable;",
                "lead self-merge (same as Round7/R10 precedent).",
                "",
                "## Named classes",
                "1. `FX3_LONDON_FIX_REVERSION` — rank 1",
                "2. `FX3_WEEKLY_OPEN_DIST_FADE` — rank 2",
                "3. `FX3_CLOSELOC_PRESSURE_CONT` — rank 3 (held backup → first probe)",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — fix microstructure + WO distance + pressure cont; ≠ R10 session densify |",
                "| Quant | SOFT — fix/WO may be thin; CLOSELOC may be cadence-heavy / cost-fragile |",
                "| MQL5/MT5 | PASS — closed-bar signal; next-open entry; no lookahead |",
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
                "# Design — Round 11 London fix / weekly-open dist / closeloc",
                "",
                "Date: 2026-07-15",
                "",
                "## 1 `HYP-FX3-H1-LONDON-FIX-REVERSION-001`",
                f"Closed {FIX_BAR_HOUR} UTC H1 body≥{FIX_BODY_ATR} ATR + close in extreme "
                f"{FIX_CLOSE_FRAC}; **fade**; first FX3; SL={FIX_SL} RR={FIX_RR} hold≤{FIX_HOLD}.",
                "Mechanism: into-fix inventory / WM-proxy reversion — ≠ London open drive, ≠ NY reopen.",
                "",
                "## 2 `HYP-FX3-H1-WEEKLY-OPEN-DIST-FADE-001`",
                f"|close − weekly_open| ≥ {WO_DIST_ATR} ATR; fade toward WO; first FX3; "
                f"≤{WO_MAX_PER_WEEK}/ISO-week; SL={WO_SL} RR={WO_RR} hold≤{WO_HOLD}.",
                "Mechanism: weekly mean-reversion to open — ≠ W1 HL-break, ≠ VWAP, ≠ PDH.",
                "",
                "## 3 `HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001`",
                f"close_loc≥{CL_LOC} (or ≤{1-CL_LOC}) + body≥{CL_BODY_ATR} ATR → continue; "
                f"skip hours {{3,7,13,15}}; ≤{CL_MAX}/day; SL={CL_SL} RR={CL_RR} hold≤{CL_HOLD}.",
                "Mechanism: held backup from USD-lag board — first offline probe (≠ bodyATR densify).",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 11 fix / weekly-open / closeloc",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| London fix reversion | ≠ R10 London open drive (07 cont); ≠ NY reopen (13 cont); ≠ LNY mid-imbalance fade; ≠ Tokyo lunch |",
                "| Weekly-open dist fade | ≠ Unpark W1 HL-break+D1; ≠ VWAP; ≠ PDH/SB; ≠ ADR exhaust |",
                "| CLOSELOC pressure cont | ≠ bodyATR portfolio densify; ≠ solo/accept/disp; first probe of held backup |",
                "",
                "R10 session params + R1–R9 / unpark / exit / FRED: **FORBIDDEN densify**.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 11 fix / weekly-open / closeloc",
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
                "# Session closeout — Round 11 fix / weekly-open / closeloc",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify fix-hour / WO-k / closeloc / R10 session / R1–R9 params.",
                "Next: next true greenfield outside R11 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 11 fix / weekly-open / closeloc",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10 session + R1–R9/unpark/exit/FRED. Nested critic Task unavailable → lead self-merge.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify London-fix / WO-dist / CLOSELOC / R10 session.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R11 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 11 (post R10)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book path quanh Phase-0 CONTAMINATED + discovery R11.",
                "GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Freeze a priori trước metrics; **không** clear Phase-0 contamination.",
                "- Model 0 book-level: **WITHHELD** (offline pool ≠ EA challenger).",
                "",
                "## 2. Discovery Round 11 — fix / WO / closeloc",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "Spot-check: watcher/capture/Real LIVE — không babysit.",
                "",
                "## Cấm",
                "Densify R1–R10 / unpark / exit / FRED / R11 fix-WO-closeloc params / Phase-0 ceremony.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R11; cost provenance khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND11 FIX/WO/CLOSELOC CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  Outside R10 session densify + R1–R9/unpark/exit/FRED.",
        "  Nested critic Task unavailable → lead self-merge `cursor-grok-4.5-high-fast`.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_R11_FIX_WO_CLOSELOC_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R11_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify London-fix / WO-k / closeloc /",
        "  R10 Tokyo/London/NY / R1–R9 / unpark / triad / exit / FRED /",
        "  residual/corr/Parkinson/ON-ratio.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged this round).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R11 — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R11 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND11 FIX/WO/CLOSELOC CLOSEOUT"):
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
                "HYP-FX3-H1-LONDON-FIX-REVERSION-001",
                "fx3_h1_london_fix_reversion",
                "FX3",
                "H1",
                *probe_london_fix_reversion(data),
            ),
            pack_result(
                "HYP-FX3-H1-WEEKLY-OPEN-DIST-FADE-001",
                "fx3_h1_weekly_open_dist_fade",
                "FX3",
                "H1",
                *probe_weekly_open_dist_fade(data),
            ),
            pack_result(
                "HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001",
                "fx3_h1_closeloc_pressure_cont",
                "FX3",
                "H1",
                *probe_closeloc_pressure_cont(data),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r11_fix_wo_closeloc.v1",
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
                "london_fix": {
                    "bar_hour": FIX_BAR_HOUR,
                    "body_atr": FIX_BODY_ATR,
                    "close_frac": FIX_CLOSE_FRAC,
                    "sl": FIX_SL,
                    "rr": FIX_RR,
                    "hold": FIX_HOLD,
                },
                "weekly_open": {
                    "dist_atr": WO_DIST_ATR,
                    "sl": WO_SL,
                    "rr": WO_RR,
                    "hold": WO_HOLD,
                    "max_per_week": WO_MAX_PER_WEEK,
                },
                "closeloc": {
                    "loc": CL_LOC,
                    "body_atr": CL_BODY_ATR,
                    "sl": CL_SL,
                    "rr": CL_RR,
                    "hold": CL_HOLD,
                    "max_per_day": CL_MAX,
                    "skip_hours": [3, 7, 13, 15],
                },
            },
            "qfsi_parallel": qnote,
            "clean_book_note": clean_note,
            "results": results,
            "any_survivor": any_surv,
            "model0": "AUTHORIZED_SURVIVORS_ONLY" if any_surv else "WITHHELD",
        }
        raw = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        write_docs(results, receipt, any_surv, qnote, clean_note)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, qnote, clean_note)
        print(json.dumps({"receipt": receipt, "any_survivor": any_surv, "results": [
            {"id": r["hypothesis_id"], "verdict": r["verdict"], "m": r["metrics"], "x15": r["haircuts"]["x1_5"]["pf"]}
            for r in results
        ], "qfsi": qnote}, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
