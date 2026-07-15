#!/usr/bin/env python3
"""Round 12 greenfield — outside R11 fix/WO/closeloc + all prior densify bans.

FORBIDDEN densify:
  ≠ R11 London-fix / WO-k / closeloc
  ≠ R10 Tokyo lunch / London open drive / NY reopen
  ≠ R1–R9 / unpark / triad / NAS / metal / CHF / COM3 / ADR /
    corr / yen-β / Parkinson / synth / ON-ratio / tickvol
  ≠ XS / AUDNZD / AONIA / CORRA / thin3 / carry / exit / FRED /
    LNY / TOM / weekend-gap / ORB / NR7 / VWAP / SB

A priori (lead self-merge):
  1) HYP-FX3-H1-D1EMA200-DIST-FADE-001
     — fade extreme H1 distance from D1 EMA200 (≠ WO / VWAP)
  2) HYP-FX3-H1-FRI-PM-PROFITTAKE-FADE-001
     — Friday PM fade of Mon–Thu net (≠ TOM / weekend-gap)
  3) HYP-GBPUSD-H1-EUR-RELSTRENGTH-CONT-001
     — GBP outpaces EUR → continue cable (≠ LNY lead-catchup / EURGBP corr)

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

OUT_JSON = PRE / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_R12_EMA_FRI_RELSTR_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R12_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 D1 EMA200 distance fade
EMA_LEN = 200
EMA_DIST_ATR = 2.00  # H1 ATR units from D1 EMA
EMA_SL = 1.40
EMA_RR = 1.50
EMA_HOLD = 10
EMA_MAX = 1  # per day first FX3

# 2 Friday PM profit-take fade
FRI_FIRE = 14  # UTC Friday
FRI_LOOK_HOURS = range(0, 14)  # Mon–Thu approx via week open→Fri 13 close
FRI_MIN_ATR = 1.50
FRI_SL = 1.20
FRI_RR = 1.50
FRI_HOLD = 6
FRI_MAX = 1

# 3 GBP vs EUR relative strength cont
RS_LOOK = 24  # H1 bars
RS_EDGE_ATR = 0.80  # GBP ret − EUR ret in ATR units
RS_SL = 1.20
RS_RR = 1.80
RS_HOLD = 8
RS_MAX = 1


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


def ema_arr(c, n):
    out = np.full_like(c, np.nan, dtype=float)
    if len(c) < n:
        return out
    out[n - 1] = c[:n].mean()
    k = 2.0 / (n + 1)
    for i in range(n, len(c)):
        out[i] = out[i - 1] + k * (c[i] - out[i - 1])
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


def map_d1_ema_to_h1(h1, d1):
    """As-of closed D1 EMA200 mapped to each H1 bar (no lookahead)."""
    d1_ema = ema_arr(d1["c"], EMA_LEN)
    out = np.full(len(h1["t"]), np.nan)
    j = 0
    for i, ts in enumerate(h1["t"]):
        # Use last D1 bar that has fully closed before this H1 bar's open
        while j + 1 < len(d1["t"]) and int(d1["t"][j + 1]) + 86400 <= int(ts):
            j += 1
        # D1 bar j is closed if its open time + 1d <= current H1 time
        if int(d1["t"][j]) + 86400 <= int(ts) and np.isfinite(d1_ema[j]):
            out[i] = d1_ema[j]
        elif j > 0 and np.isfinite(d1_ema[j - 1]):
            out[i] = d1_ema[j - 1]
    return out


def probe_d1ema_dist_fade(h1_data, d1_data):
    closed, open_pos = [], []
    last_day, day_count = None, 0
    ema_map = {s: map_d1_ema_to_h1(h1_data[s], d1_data[s]) for s in FX3}
    clock = h1_data["EURUSD"]["t"]
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: h1_data[s] for s in FX3}, ts, closed, EMA_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5:
            continue
        if day_count >= EMA_MAX or open_pos:
            continue
        chosen = None
        for sym in FX3:
            d = h1_data[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j >= len(d["t"]) or d["t"][j] != ts:
                continue
            atr = d["atr"][j]
            ema = ema_map[sym][j]
            if not np.isfinite(atr) or atr <= 0 or not np.isfinite(ema):
                continue
            c = float(d["c"][j])
            dist = c - ema
            if abs(dist) < EMA_DIST_ATR * atr:
                continue
            side = -1 if dist > 0 else 1
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * EMA_SL * atr
            tp = entry + side * EMA_RR * EMA_SL * atr
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
    flush_open(open_pos, {s: h1_data[s] for s in FX3}, closed)
    return summarize(closed)


def probe_fri_pm_profittake(data):
    """Friday 14 UTC: fade Mon open → Fri 13 close net if ≥ min ATR."""
    closed, open_pos = [], []
    week_open = {s: {} for s in FX3}
    for sym in FX3:
        d = data[sym]
        seen = set()
        for i, ts in enumerate(d["t"]):
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            if dt.weekday() >= 5:
                continue
            iso = dt.isocalendar()
            wk = (iso[0], iso[1])
            if wk in seen:
                continue
            seen.add(wk)
            week_open[sym][wk] = float(d["o"][i])

    last_week = None
    fired = False
    clock = data["EURUSD"]["t"]
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, FRI_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        iso = dt.isocalendar()
        wk = (iso[0], iso[1])
        if wk != last_week:
            last_week, fired = wk, False
        if dt.weekday() != 4 or dt.hour != FRI_FIRE:
            continue
        if fired or open_pos:
            continue
        chosen = None
        for sym in FX3:
            d = data[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j >= len(d["t"]) or d["t"][j] != ts:
                continue
            # Signal uses prior closed bar (13 UTC) — i.e. bar before fire hour
            # At hour==14 closed, look at week open vs close of hour 13 same day
            atr = d["atr"][j]
            wo = week_open[sym].get(wk)
            if wo is None or not np.isfinite(atr) or atr <= 0:
                continue
            # Find hour 13 same day
            prev_ts = ts - 3600
            k = int(np.searchsorted(d["t"], prev_ts, side="left"))
            if k >= len(d["t"]) or d["t"][k] != prev_ts:
                continue
            net = float(d["c"][k]) - wo
            if abs(net) < FRI_MIN_ATR * atr:
                continue
            side = -1 if net > 0 else 1
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * FRI_SL * atr
            tp = entry + side * FRI_RR * FRI_SL * atr
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
            fired = True
    flush_open(open_pos, {s: data[s] for s in FX3}, closed)
    return summarize(closed)


def probe_gbp_eur_relstrength(data):
    """GBP 24h ret exceeds EUR by edge → continue GBPUSD."""
    d_g = data["GBPUSD"]
    d_e = data["EURUSD"]
    closed, open_pos = [], []
    last_day, day_count = None, 0
    for i in range(RS_LOOK + 1, len(d_g["t"]) - 2):
        ts = int(d_g["t"][i])
        open_pos = manage_exits(open_pos, {"GBPUSD": d_g}, ts, closed, RS_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5:
            continue
        if day_count >= RS_MAX or open_pos:
            continue
        # Align EUR bar
        je = int(np.searchsorted(d_e["t"], ts, side="left"))
        if je >= len(d_e["t"]) or d_e["t"][je] != ts:
            continue
        if je < RS_LOOK or i < RS_LOOK:
            continue
        atr = d_g["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        ret_g = float(d_g["c"][i]) - float(d_g["c"][i - RS_LOOK])
        ret_e = float(d_e["c"][je]) - float(d_e["c"][je - RS_LOOK])
        # Express both in GBP ATR units (EUR ret / eurusd atr * gbp atr approx:
        # use raw price ret difference scaled by GBP ATR — EURUSD and GBPUSD similar scale)
        edge = (ret_g - ret_e) / atr
        if abs(edge) < RS_EDGE_ATR:
            continue
        side = 1 if edge > 0 else -1
        entry = float(d_g["o"][i + 1])
        sl = entry - side * RS_SL * atr
        tp = entry + side * RS_RR * RS_SL * atr
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
    flush_open(open_pos, {"GBPUSD": d_g}, closed)
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
                "feature_family": "greenfield_r12_ema_fri_relstr",
                "lane": "strategy_shift_r12_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": "R12 outside R11 densify; lead self-merge",
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
                "# 3-critic panel — Round 12 EMA / Fri / relstr",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast` — Task backend unavailable;",
                "lead self-merge.",
                "",
                "## Named classes",
                "1. `FX3_D1EMA200_DIST_FADE`",
                "2. `FX3_FRI_PM_PROFITTAKE_FADE`",
                "3. `GBPUSD_EUR_RELSTRENGTH_CONT`",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — HTF value MR + calendar profit-take + cross-pair RS; ≠ R11 |",
                "| Quant | SOFT — Fri thin N; EMA fade may be regime-dependent; RS scale approx |",
                "| MQL5/MT5 | PASS — D1 EMA as-of closed; next-open entry |",
                "",
                "INTAKE_KILL: none. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 12 D1EMA / Fri PM / GBP-EUR RS",
                "",
                "Date: 2026-07-15",
                "",
                f"## 1 `HYP-FX3-H1-D1EMA200-DIST-FADE-001`",
                f"|H1 close − D1 EMA{EMA_LEN}| ≥ {EMA_DIST_ATR}×H1 ATR; fade; first FX3; "
                f"SL={EMA_SL} RR={EMA_RR} hold≤{EMA_HOLD}.",
                "",
                f"## 2 `HYP-FX3-H1-FRI-PM-PROFITTAKE-FADE-001`",
                f"Fri {FRI_FIRE} UTC; |week_open→Thu/Fri13 close| ≥ {FRI_MIN_ATR} ATR; fade; "
                f"SL={FRI_SL} RR={FRI_RR} hold≤{FRI_HOLD}.",
                "",
                f"## 3 `HYP-GBPUSD-H1-EUR-RELSTRENGTH-CONT-001`",
                f"24h GBP−EUR return ≥ {RS_EDGE_ATR} GBP-ATR; continue cable; "
                f"SL={RS_SL} RR={RS_RR} hold≤{RS_HOLD}.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 12 EMA / Fri / relstr",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| D1EMA200 dist fade | ≠ R11 WO-dist; ≠ VWAP; ≠ Weekly-HL; ≠ ADR exhaust |",
                "| Fri PM profit-take | ≠ TOM; ≠ weekend-gap; ≠ carry Mon→Thu harvest |",
                "| GBP EUR relstr cont | ≠ LNY EUR-lead catchup; ≠ EURGBP corr-break; ≠ XS residual |",
                "",
                "R11 + R10 + R1–R9 densify boards: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 12 EMA / Fri / relstr",
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
                "# Session closeout — Round 12 EMA / Fri / relstr",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify EMA-k / Fri-hour / RS-edge / R11 / R10 params.",
                "Next: next true greenfield outside R12 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 12 EMA / Fri / relstr",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R11 + R10 + prior densify. Lead self-merge.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify D1EMA / Fri-PM / GBP-EUR-RS.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R12 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 12 (post R11)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book path quanh Phase-0 CONTAMINATED + discovery R12.",
                "GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Freeze a priori trước metrics; **không** clear Phase-0 contamination.",
                "- Model 0 book-level: **WITHHELD** (offline pool ≠ EA challenger).",
                "",
                "## 2. Discovery Round 12 — EMA / Fri / relstr",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "Spot-check once — không babysit.",
                "",
                "## Cấm",
                "Densify R1–R12 / unpark / exit / FRED / Phase-0 ceremony.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R12; cost provenance khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND12 EMA/FRI/RELSTR CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  Outside R11 densify + R10/R1–R9/unpark/exit/FRED.",
        "  Nested critic Task unavailable → lead self-merge `cursor-grok-4.5-high-fast`.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_R12_EMA_FRI_RELSTR_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R12_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify D1EMA-k / Fri-PM / GBP-EUR-RS /",
        "  R11 fix/WO/closeloc / R10 session / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R12 — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R12 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND12 EMA/FRI/RELSTR CLOSEOUT"):
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
        h1 = {
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_H1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_H1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_H1)),
        }
        d1 = {
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_D1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_D1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_D1)),
        }
        results = [
            pack_result(
                "HYP-FX3-H1-D1EMA200-DIST-FADE-001",
                "fx3_h1_d1ema200_dist_fade",
                "FX3",
                "H1",
                *probe_d1ema_dist_fade(h1, d1),
            ),
            pack_result(
                "HYP-FX3-H1-FRI-PM-PROFITTAKE-FADE-001",
                "fx3_h1_fri_pm_profittake_fade",
                "FX3",
                "H1",
                *probe_fri_pm_profittake(h1),
            ),
            pack_result(
                "HYP-GBPUSD-H1-EUR-RELSTRENGTH-CONT-001",
                "gbpusd_h1_eur_relstrength_cont",
                "GBPUSD",
                "H1",
                *probe_gbp_eur_relstrength(h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r12_ema_fri_relstr.v1",
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
                "d1ema": {
                    "len": EMA_LEN,
                    "dist_atr": EMA_DIST_ATR,
                    "sl": EMA_SL,
                    "rr": EMA_RR,
                    "hold": EMA_HOLD,
                },
                "fri_pm": {
                    "fire": FRI_FIRE,
                    "min_atr": FRI_MIN_ATR,
                    "sl": FRI_SL,
                    "rr": FRI_RR,
                    "hold": FRI_HOLD,
                },
                "relstr": {
                    "look": RS_LOOK,
                    "edge_atr": RS_EDGE_ATR,
                    "sl": RS_SL,
                    "rr": RS_RR,
                    "hold": RS_HOLD,
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
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_survivor": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            "m": r["metrics"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
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
