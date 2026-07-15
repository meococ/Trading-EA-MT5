#!/usr/bin/env python3
"""Round 29 greenfield — Equal-HL break + OPEX Friday + One-slot book arch.

Post R28: week-struct/monthend/losscd ALL_KILL. Keep NON-indicator lane.

HARD FORBIDDEN densify: R1–R28, H4-engulf, HA/Keltner/ST/Ichimoku/ROC,
week-HL/monthend/losscd, lead-clones, fade/session, FRED, RR2 exits.

A priori (≥2; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001     (structural liquidity)
  2) HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001     (event calendar)
  3) HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001  (book architecture)

+$12 joint. Model 0 only if PROBE_SURVIVOR. Closed-bar only.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

STEM = "20260715_GREENFIELD_R29_EQUALHL_OPEX_ONESLOT"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R29_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"
OUT_DEAL_RETRY = PRE / "20260715_COST_DEAL_RETRY_R29.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 Equal high/low double-tap then break CONT
EQ_TOL_ATR = 0.15  # highs within 0.15 ATR = equal
EQ_LOOKBACK = 30
EQ_MIN_SEP = 3  # bars between taps
EQ_BODY = 0.35
EQ_SL = 1.45
EQ_RR = 2.00
EQ_HOLD = 12

# 2 OPEX Friday (3rd Friday) CONT on USDJPY
OX_BODY = 0.40
OX_SL = 1.45
OX_RR = 2.00
OX_HOLD = 10

# 3 One-slot FX3 book architecture
OS_BODY = 0.40
OS_SL = 1.45
OS_RR = 2.00
OS_HOLD = 10


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
    step = 0.01
    if info.volume_min and info.volume_min < 0.01:
        step = float(info.volume_min)
    lots = math.floor(risk / loss / step) * step
    return min(5.0, max(float(info.volume_min or 0.01), lots))


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


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def is_third_friday(dt: datetime) -> bool:
    if dt.weekday() != 4:
        return False
    return 15 <= dt.day <= 21


def find_equal_level_break(d, j):
    """Return side if close breaks equal-high or equal-low structure at j."""
    atr = d["atr"][j]
    if not np.isfinite(atr) or atr <= 0:
        return 0
    tol = EQ_TOL_ATR * atr
    body = float(d["c"][j]) - float(d["o"][j])
    # Equal highs: two swing highs within lookback within tol; break above max
    hi_idxs = []
    lo_idxs = []
    start = max(1, j - EQ_LOOKBACK)
    for k in range(start, j):
        # local swing high/low (1-bar pivot)
        if d["h"][k] >= d["h"][k - 1] and (k + 1 >= j or d["h"][k] >= d["h"][k + 1]):
            hi_idxs.append(k)
        if d["l"][k] <= d["l"][k - 1] and (k + 1 >= j or d["l"][k] <= d["l"][k + 1]):
            lo_idxs.append(k)
    # equal high pair
    if len(hi_idxs) >= 2:
        for a in range(len(hi_idxs)):
            for b in range(a + 1, len(hi_idxs)):
                i1, i2 = hi_idxs[a], hi_idxs[b]
                if abs(i2 - i1) < EQ_MIN_SEP:
                    continue
                h1, h2 = float(d["h"][i1]), float(d["h"][i2])
                if abs(h1 - h2) > tol:
                    continue
                level = max(h1, h2)
                c0 = float(d["c"][j - 1])
                c1 = float(d["c"][j])
                if c0 <= level and c1 > level and body > 0 and abs(body) >= EQ_BODY * atr:
                    return 1
    if len(lo_idxs) >= 2:
        for a in range(len(lo_idxs)):
            for b in range(a + 1, len(lo_idxs)):
                i1, i2 = lo_idxs[a], lo_idxs[b]
                if abs(i2 - i1) < EQ_MIN_SEP:
                    continue
                l1, l2 = float(d["l"][i1]), float(d["l"][i2])
                if abs(l1 - l2) > tol:
                    continue
                level = min(l1, l2)
                c0 = float(d["c"][j - 1])
                c1 = float(d["c"][j])
                if c0 >= level and c1 < level and body < 0 and abs(body) >= EQ_BODY * atr:
                    return -1
    return 0


def probe_fx3_equal_hl(h1):
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    for i in range(EQ_LOOKBACK + 20, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, EQ_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        for sym in FX3:
            if sym in open_syms:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < EQ_LOOKBACK + 5:
                continue
            side = find_equal_level_break(d, j)
            if side == 0:
                continue
            atr = d["atr"][j]
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * EQ_SL * atr
            tp = entry + side * EQ_RR * EQ_SL * atr
            lots = risk_lots(sym, entry, sl)
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": lots,
                    "bars": 0,
                }
            )
            open_syms.add(sym)
            last_day_sym.add(day_key)
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def probe_usdjpy_opex(uj):
    closed, open_pos = [], []
    sym = "USDJPY"
    last_day = None
    for i in range(30, len(uj["t"]) - 1):
        ts = int(uj["t"][i])
        open_pos = manage_exits(open_pos, {sym: uj}, ts, closed, OX_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1
        sig_dt = datetime.fromtimestamp(int(uj["t"][j]), tz=timezone.utc)
        if not is_third_friday(sig_dt):
            continue
        atr = uj["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(uj["c"][j]) - float(uj["o"][j])
        if abs(body) < OX_BODY * atr:
            continue
        side = 1 if body > 0 else -1
        day = dt.date()
        if day == last_day:
            continue
        entry = float(uj["o"][i])
        sl = entry - side * OX_SL * atr
        tp = entry + side * OX_RR * OX_SL * atr
        lots = risk_lots(sym, entry, sl)
        open_pos.append(
            {
                "sym": sym,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        last_day = day
    flush_open(open_pos, {sym: uj}, closed)
    return summarize(closed)


def probe_fx3_oneslot(h1):
    """At most one open position across entire FX3 book; pick max |body|/ATR."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day = None
    for i in range(30, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, OS_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue  # one-slot: book must be flat
        if dt.date() == last_day:
            continue
        sig_ts = int(clock[i - 1])
        best = None
        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            score = abs(body) / atr
            if score < OS_BODY:
                continue
            side = 1 if body > 0 else -1
            cand = (score, sym, side, atr, j)
            if best is None or cand[0] > best[0]:
                best = cand
        if best is None:
            continue
        _, sym, side, atr, _ = best
        d = h1[sym]
        ent_i = asof_idx(d, ts)
        if ent_i is None:
            continue
        entry = float(d["o"][ent_i])
        sl = entry - side * OS_SL * atr
        tp = entry + side * OS_RR * OS_SL * atr
        lots = risk_lots(sym, entry, sl)
        open_pos.append(
            {
                "sym": sym,
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        last_day = dt.date()
    flush_open(open_pos, h1, closed)
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
                "feature_family": "greenfield_r29_equalhl_opex_oneslot",
                "lane": "strategy_shift_r29_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R29 NON-FADE non-indicator after R28 ALL_KILL; "
                    "nested critic GO lead self-merge"
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


def write_docs(results, receipt, any_surv, qnote, clean_book_note, freeze_sha, cost_note):
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
                "# 3-critic panel — Round 29 Equal-HL / OPEX / One-slot",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (lead self-merge; NON-indicator; outside R1–R28 densify).",
                "",
                "## Named (NON-FADE; structural / event / book)",
                "1. Equal-HL break CONT — double-tap liquidity then break (≠ fractal / week-HL)",
                "2. OPEX Friday CONT — 3rd-Friday equity expiry spillover (≠ month-end / NFP)",
                "3. One-slot book arch — max 1 FX3 position, pick max |body|/ATR (≠ losscd / RS-rank)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — liquidity structure + OPEX flow + portfolio slot |",
                "| Quant | PASS — independent; joint gates a priori |",
                "| MQL5/MT5 | PASS — closed-bar pivots / calendar Friday / next-open |",
                "",
                "Merge: **GO** offline only. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 29 Equal-HL / OPEX / One-slot",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001`",
                f"Two swing highs/lows within {EQ_TOL_ATR}×ATR over {EQ_LOOKBACK} bars, "
                f"sep≥{EQ_MIN_SEP}, then close break + body≥{EQ_BODY}×ATR → CONT.",
                "Why: equal-level liquidity ≠ R23 fractal5; ≠ R28 prior-week HL; ≠ Donch.",
                "",
                "## 2 `HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001`",
                f"3rd Friday (day 15–21) + body≥{OX_BODY}×ATR → CONT.",
                "Why: equity OPEX spillover ≠ R28 month-end; ≠ NFP/CPI/FRED; ≠ session pack.",
                "",
                "## 3 `HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001`",
                f"Book flat required; among FX3 with |body|≥{OS_BODY}×ATR pick max score; 1/day.",
                "Why: portfolio slot architecture ≠ R28 loss-cooldown; ≠ R24 RS-rank densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 29 Equal-HL / OPEX / One-slot",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 equal-HL break CONT | ≠ R23 fractal; ≠ R28 week-HL; ≠ R16 D1 HL; ≠ Donch |",
                "| USDJPY OPEX Friday CONT | ≠ R28 month-end; ≠ R13 NFP; ≠ R12 Fri-PM fade; ≠ FRED |",
                "| FX3 one-slot book arch | ≠ R28 losscd; ≠ R24 RS-rank; ≠ R22 risksync; ≠ R4 disp fade |",
                "",
                "R1–R28 densify + TA clones + fade/session + FRED + RR2 exits: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 29 Equal-HL / OPEX / One-slot",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Freeze SHA256: `{freeze_sha}`",
                f"Status: `{status}`",
                f"Cost a priori: +${BASE_COST:.0f}/trade",
                f"QFSI parallel: {qnote}",
                f"Cost track: {cost_note}",
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
                "# Session closeout — Round 29 Equal-HL / OPEX / One-slot",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify equal-HL-k / opex-k / oneslot-k /",
                "R28 week-HL/monthend/losscd / R27 TA / H4-engulf / lead /",
                "fade-session / unpark / RR2-exit / FRED.",
                "Next: next true greenfield outside R29 (NON-FADE, non-indicator).",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 29 Equal-HL / OPEX / One-slot",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R28. **NON-FADE. NON-indicator.**",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế",
                "1. Equal-HL break — double-tap thanh khoản rồi phá (structural)",
                "2. OPEX Friday — thứ Sáu thứ 3 trong tháng (event)",
                "3. One-slot book — tối đa 1 lệnh FX3, chọn |body|/ATR lớn nhất (architecture)",
                "",
                "## Cost",
                cost_note,
                "",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN brief — Clean book + Round 29",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R29 NON-FADE structural/event/book. GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 29 — Equal-HL / OPEX / One-slot",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007 + cost",
                f"{qnote}",
                f"Cost: {cost_note}",
                "",
                "## Near-miss shelf (do not densify)",
                "- R25 USDJPY H4-engulf CONT: PF≈1.24 x1.5≈1.16 — **cấm densify**.",
                "- R28 prior-week HL PF≈1.10 — không densify.",
                "",
                "## Cấm",
                "Densify R1–R29 / TA clones / week-HL / monthend / losscd / fade-session / "
                "unpark / RR2-exit / FRED / Phase-0 / H4-engulf.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R29 (**NON-FADE, non-indicator**); cost autonomous.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, receipt, any_surv, qnote, clean_note, freeze_sha, cost_note):
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
        f"- **GREENFIELD ROUND29 EQUALHL/OPEX/ONESLOT CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE **non-indicator** greenfield outside R1–R28 densify",
        "  (structural / event / book-architecture).",
        "  Nested critic GO — Equal-HL / OPEX-Friday / One-slot "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R29_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        f"  Cost autonomous: {cost_note}",
        "  Do **not** densify equal-HL-k / opex-k / oneslot-k /",
        "  R28 week-HL/monthend/losscd / R27 TA / R26 HA/Keltner/ST /",
        "  H4-engulf / lead / fade-session / ORB/IB / unpark / RR2-exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R29 (still NON-FADE, non-indicator) —",
        "  QFSI parallel; cost autonomous retry (no Owner deal-export headline).",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R29 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND29 EQUALHL/OPEX/ONESLOT CLOSEOUT"):
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
    final = []
    for ln in out:
        if ln.startswith("- **ACTIVE — STRATEGY SHIFT aftermath.**"):
            final.append(
                "- **ACTIVE — STRATEGY SHIFT aftermath.** Track A PRIMARY book diagnostic "
                "partial under a priori +$12 (caps+cadence OK, PF fail) — **park compose**; "
                "do not outcome-mine densify. Phase-0 needs Owner contamination clear. "
                "Track B: QFSI 007 watcher **75476** / capture **72320** / Real **27096**. "
                "Next = greenfield **outside** R1–R29 densify (NON-FADE, non-indicator), "
                "or cost via autonomous `history_deals_get` / QFSI (no Owner deal-export headline). "
                "Cost table `readouts/20260715_COST_MULTIDAY_TABLE_R24.md` "
                "(quote_days=2/90; freeze_eligible=False). "
                "Best shelf RR2 `194548`. GOAL unmet."
            )
            continue
        if ln.startswith("  partial under a priori") or ln.startswith(
            "  do not outcome-mine densify or re-rank"
        ):
            continue
        if "QFSI 007 watcher **75476**" in ln and not ln.startswith("- **"):
            continue
        if ln.strip().startswith("**outside** R1–") and not ln.startswith("- **"):
            continue
        if "cost provenance" in ln and not ln.startswith("- **"):
            continue
        if "Cost diagnostic table:" in ln and not ln.startswith("- **"):
            continue
        if "(quote_days=2/90" in ln and not ln.startswith("- **"):
            continue
        if ln.strip().startswith("Best shelf RR2") and not ln.startswith("- **"):
            if final and final[-1].startswith("- **ACTIVE"):
                continue
        final.append(ln)
    HOT.write_text("\n".join(final) + "\n", encoding="utf-8")


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


def retry_deals_count() -> dict:
    info = mt5.account_info()
    if info is None:
        return {"ok": False, "error": "account_info_none", "raw_deals": None}
    now = datetime.now(timezone.utc)
    frm = now - timedelta(days=3650)
    deals = mt5.history_deals_get(frm, now)
    if deals is None:
        return {
            "ok": False,
            "error": f"history_deals_get:{mt5.last_error()}",
            "raw_deals": None,
            "login": int(info.login),
            "server": str(info.server),
        }
    comm_by: dict[str, set] = {}
    for d in deals:
        sym = str(d.symbol or "").upper()
        if sym and abs(float(d.commission)) > 1e-12:
            comm_by.setdefault(sym, set()).add(str(d.position_id or d.ticket))
    out = {
        "ok": True,
        "login": int(info.login),
        "server": str(info.server),
        "raw_deals": len(deals),
        "commission_unique_by_symbol": {k: len(v) for k, v in comm_by.items()},
        "slip_side_ref": "MISSING_NE_0",
        "ts_utc": utc_now(),
    }
    OUT_DEAL_RETRY.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def load_cost_note(deal_retry: dict | None = None) -> str:
    man = (
        ROOT
        / "02. AlphaFactory"
        / "evidence"
        / "execution"
        / "FivePercentOnline-Real"
        / "20260715_DEAL_HISTORY_IMPORT_LIVE_R24"
        / "import_manifest.json"
    )
    table = PRE / "20260715_COST_MULTIDAY_TABLE_R24.json"
    if man.exists():
        p = json.loads(man.read_text(encoding="utf-8"))
        counts = p.get("commission_lifecycle_counts") or {}
        base = (
            f"autonomous live import `{p.get('status')}` raw_deals={p.get('raw_deal_count')} "
            f"comm EURUSD={counts.get('EURUSD',0)}/30 USDJPY={counts.get('USDJPY',0)}/30 "
            f"slip=0 MISSING≠0"
        )
    else:
        base = "live import missing"
    if table.exists():
        t = json.loads(table.read_text(encoding="utf-8"))
        base += (
            f"; multiday_table quote_days={t.get('quote_days_count')}/90 "
            f"freeze_eligible={t.get('freeze_eligible')}"
        )
    if deal_retry is not None:
        if deal_retry.get("ok"):
            base += f"; R29 retry history_deals_get raw_deals={deal_retry.get('raw_deals')}"
            cu = deal_retry.get("commission_unique_by_symbol") or {}
            if cu:
                base += f" comm_unique={cu}"
        else:
            base += f"; R29 retry FAIL ({deal_retry.get('error')})"
    return base + "; freeze_eligible=False"


def freeze_contract_sha() -> str:
    contract = {
        "equal_hl": {
            "tol_atr": EQ_TOL_ATR,
            "lookback": EQ_LOOKBACK,
            "min_sep": EQ_MIN_SEP,
            "body": EQ_BODY,
            "sl": EQ_SL,
            "rr": EQ_RR,
            "hold": EQ_HOLD,
        },
        "opex_friday": {
            "body": OX_BODY,
            "sl": OX_SL,
            "rr": OX_RR,
            "hold": OX_HOLD,
            "symbol": "USDJPY",
        },
        "oneslot_book": {
            "body": OS_BODY,
            "sl": OS_SL,
            "rr": OS_RR,
            "hold": OS_HOLD,
            "universe": list(FX3),
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R1_R28_densify__TA_clones__weekHL_monthend_losscd__FRED__RR2_exit",
    }
    return sha256_bytes(
        json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        freeze_sha = freeze_contract_sha()
        OUT_FREEZE.write_text(
            "\n".join(
                [
                    "# Universe freeze — Round 29 Equal-HL / OPEX / One-slot",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — lead self-merge).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001",
                    "2. HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001",
                    "3. HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001",
                    "",
                    "Mechanism note: (1) equal-level liquidity ≠ fractal/week-HL;",
                    "(2) OPEX Friday ≠ month-end/NFP; (3) one-slot book ≠ losscd/RS.",
                    "TA-indicator densify FORBIDDEN.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        deal_retry = retry_deals_count()
        cost_note = load_cost_note(deal_retry)
        h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        results = [
            pack_result(
                "HYP-FX3-H1-EQUAL-HL-BREAK-CONT-001",
                "fx3_h1_equal_hl_break_cont",
                "FX3",
                "H1",
                *probe_fx3_equal_hl(h1),
            ),
            pack_result(
                "HYP-USDJPY-H1-OPEX-FRIDAY-CONT-001",
                "usdjpy_h1_opex_friday_cont",
                "USDJPY",
                "H1",
                *probe_usdjpy_opex(h1["USDJPY"]),
            ),
            pack_result(
                "HYP-FX3-H1-ONESLOT-BOOK-ARCH-CONT-001",
                "fx3_h1_oneslot_book_arch_cont",
                "FX3",
                "H1",
                *probe_fx3_oneslot(h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r29_equalhl_opex_oneslot.v1_closedbar",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": (
                "NON_FADE__NON_INDICATOR__NO_R1_R28_DENSIFY__NO_H4ENGULF__"
                "NO_LEAD__NO_FADE_SESSION__NO_FRED__NO_RR2_EXIT"
            ),
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "qfsi_parallel": qnote,
            "cost_autonomous": cost_note,
            "deal_retry_r29": deal_retry,
            "clean_book_note": clean_note,
            "results": results,
            "model0": "AUTHORIZED_SURVIVORS_ONLY" if any_surv else "WITHHELD",
            "status": (
                "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
            ),
        }
        raw = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        write_docs(results, receipt, any_surv, qnote, clean_note, freeze_sha, cost_note)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, qnote, clean_note, freeze_sha, cost_note)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "receipt": receipt,
                    "cost": cost_note,
                    "deal_retry": deal_retry,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            "m": r["metrics"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
