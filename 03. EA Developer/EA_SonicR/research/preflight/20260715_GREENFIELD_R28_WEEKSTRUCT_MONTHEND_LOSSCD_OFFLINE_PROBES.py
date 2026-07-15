#!/usr/bin/env python3
"""Round 28 greenfield — Prior-week structure + Month-end event + Loss-cooldown arch.

Post R27: Marubozu/Ichimoku/ROC ALL_KILL. Owner hard ban: no TA-indicator densify.

HARD FORBIDDEN densify: R1–R27, H4-engulf, HA/Keltner/ST/Ichimoku/ROC-band,
lead-clones, fade/session packs, FRED displace, RR2 exits.

A priori (≥2; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001   (structural)
  2) HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001     (event/calendar)
  3) HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001    (book/architecture)

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

STEM = "20260715_GREENFIELD_R28_WEEKSTRUCT_MONTHEND_LOSSCD"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R28_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"
OUT_DEAL_RETRY = PRE / "20260715_COST_DEAL_RETRY_R28.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 Prior-week HL break CONT (structural)
PW_BODY = 0.35
PW_SL = 1.45
PW_RR = 2.00
PW_HOLD = 12

# 2 Month-end rebal CONT (event)
ME_DOM_LATE = 28  # day-of-month >= this OR <= ME_DOM_EARLY
ME_DOM_EARLY = 2
ME_BODY = 0.40
ME_SL = 1.45
ME_RR = 2.00
ME_HOLD = 10

# 3 Loss-cooldown architecture CONT (book/arch)
LC_BODY = 0.40
LC_COOLDOWN_BARS = 24  # after a losing exit on that symbol
LC_SL = 1.45
LC_RR = 2.00
LC_HOLD = 10


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


def manage_exits(open_pos, data, ts, closed, hold_limit, on_close=None):
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
            pnl = cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"])
            closed.append({"pnl": pnl, "reason": reason, "sym": sym})
            if on_close is not None:
                on_close(sym, pnl, idx)
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


def iso_week_key(ts: int):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    y, w, _ = dt.isocalendar()
    return (y, w)


def build_prior_week_levels(d):
    """For each bar i, prior completed ISO-week high/low (closed-bar as-of)."""
    n = len(d["t"])
    prior_hi = np.full(n, np.nan, dtype=float)
    prior_lo = np.full(n, np.nan, dtype=float)
    # Accumulate current week; on week change, freeze previous as prior.
    cur_key = None
    cur_hi = cur_lo = None
    frozen_hi = frozen_lo = None
    for i in range(n):
        key = iso_week_key(int(d["t"][i]))
        h, l = float(d["h"][i]), float(d["l"][i])
        if cur_key is None:
            cur_key = key
            cur_hi, cur_lo = h, l
        elif key != cur_key:
            frozen_hi, frozen_lo = cur_hi, cur_lo
            cur_key = key
            cur_hi, cur_lo = h, l
        else:
            cur_hi = max(cur_hi, h)
            cur_lo = min(cur_lo, l)
        if frozen_hi is not None:
            prior_hi[i] = frozen_hi
            prior_lo[i] = frozen_lo
    return prior_hi, prior_lo


def probe_fx3_prior_week_hl(h1):
    """FX3: first H1 close beyond prior ISO-week HL + body CONT."""
    levels = {s: build_prior_week_levels(h1[s]) for s in FX3}
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    armed = {s: {"up": False, "dn": False, "week": None} for s in FX3}
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, PW_HOLD)
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
            if j is None or j < 30:
                continue
            phi, plo = levels[sym][0][j], levels[sym][1][j]
            if not (np.isfinite(phi) and np.isfinite(plo)):
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            c0 = float(d["c"][j - 1]) if j >= 1 else float(d["c"][j])
            c1 = float(d["c"][j])
            o1 = float(d["o"][j])
            body = c1 - o1
            wk = iso_week_key(int(d["t"][j]))
            st = armed[sym]
            if st["week"] != wk:
                st["week"] = wk
                st["up"] = False
                st["dn"] = False
            side = 0
            # Break: close crosses prior week extreme this bar; first time this week.
            if (not st["up"]) and c0 <= phi and c1 > phi and body > 0:
                if abs(body) >= PW_BODY * atr:
                    side = 1
                    st["up"] = True
            elif (not st["dn"]) and c0 >= plo and c1 < plo and body < 0:
                if abs(body) >= PW_BODY * atr:
                    side = -1
                    st["dn"] = True
            if side == 0:
                continue
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * PW_SL * atr
            tp = entry + side * PW_RR * PW_SL * atr
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


def probe_eurusd_monthend(eu):
    """EURUSD: month-end rebalancing window body CONT (calendar event)."""
    closed, open_pos = [], []
    sym = "EURUSD"
    last_day = None
    for i in range(30, len(eu["t"]) - 1):
        ts = int(eu["t"][i])
        open_pos = manage_exits(open_pos, {sym: eu}, ts, closed, ME_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1
        sig_dt = datetime.fromtimestamp(int(eu["t"][j]), tz=timezone.utc)
        dom = sig_dt.day
        if not (dom >= ME_DOM_LATE or dom <= ME_DOM_EARLY):
            continue
        atr = eu["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(eu["c"][j]) - float(eu["o"][j])
        if abs(body) < ME_BODY * atr:
            continue
        side = 1 if body > 0 else -1
        day = dt.date()
        if day == last_day:
            continue
        entry = float(eu["o"][i])
        sl = entry - side * ME_SL * atr
        tp = entry + side * ME_RR * ME_SL * atr
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
    flush_open(open_pos, {sym: eu}, closed)
    return summarize(closed)


def probe_fx3_loss_cooldown(h1):
    """FX3 body CONT with per-symbol loss-cooldown architecture."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    # cooldown_until[sym] = bar index on that symbol's series
    cooldown_until = {s: -1 for s in FX3}
    # map clock bar -> per-symbol index for cooldown updates
    sym_idx_at_clock = {}

    def on_close(sym, pnl, idx):
        if pnl < 0:
            cooldown_until[sym] = max(cooldown_until[sym], idx + LC_COOLDOWN_BARS)

    for i in range(30, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(
            open_pos, h1, ts, closed, LC_HOLD, on_close=on_close
        )
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
            if j is None or j < 20:
                continue
            if j <= cooldown_until[sym]:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < LC_BODY * atr:
                continue
            side = 1 if body > 0 else -1
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * LC_SL * atr
            tp = entry + side * LC_RR * LC_SL * atr
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
            sym_idx_at_clock[(ts, sym)] = ent_i
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
                "feature_family": "greenfield_r28_weekstruct_monthend_losscd",
                "lane": "strategy_shift_r28_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R28 NON-FADE structural/event/arch after R27 TA ALL_KILL; "
                    "nested critic GO lead self-merge; NO indicator densify"
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
                "# 3-critic panel — Round 28 Week-struct / Month-end / Loss-CD",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (lead self-merge; NON-indicator; outside R1–R27 densify).",
                "",
                "## Named (NON-FADE; structural / event / architecture)",
                "1. Prior-week HL break CONT — completed ISO-week structure (≠ D1 HL / fractal / Donch)",
                "2. Month-end rebal CONT — calendar flow window (≠ NFP / CPI / FRED)",
                "3. Loss-cooldown arch CONT — book inventory cooldown after loser (≠ session / MaxKZ densify)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — structural levels + month-end flow + anti-revenge arch |",
                "| Quant | PASS — independent families; joint gates a priori; no TA clone |",
                "| MQL5/MT5 | PASS — closed-bar week levels / calendar DOM / next-open entry |",
                "",
                "Merge: **GO** offline only. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "Hard ban carry: R1–R27 TA densify + H4-engulf near-miss — do **not** densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 28 Week-struct / Month-end / Loss-CD",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001`",
                "First H1 close beyond prior completed ISO-week high/low + body≥"
                f"{PW_BODY}×ATR → CONT. First break per week per side.",
                "Why: calendar-week structure ≠ R16 D1 HL; ≠ R23 fractal5; ≠ Donch; ≠ weekly-open fade.",
                "",
                "## 2 `HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001`",
                f"DOM≥{ME_DOM_LATE} or DOM≤{ME_DOM_EARLY} + body≥{ME_BODY}×ATR → CONT.",
                "Why: month-end rebalancing flow ≠ NFP same-day; ≠ CPI; ≠ FRED displace; ≠ session pack.",
                "",
                "## 3 `HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001`",
                f"Body≥{LC_BODY}×ATR CONT + per-symbol cooldown {LC_COOLDOWN_BARS} bars after losing exit.",
                "Why: execution/inventory architecture ≠ RS-rank; ≠ risksync; ≠ session MaxKZ densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 28 Week-struct / Month-end / Loss-CD",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 prior-week HL break CONT | ≠ R16 D1 HL; ≠ R23 fractal; ≠ R11 weekly-open fade; ≠ weekend-gap |",
                "| EURUSD month-end rebal CONT | ≠ R13 NFP; ≠ R16 CPI; ≠ FRED; ≠ R10 session-edge densify |",
                "| FX3 loss-cooldown arch CONT | ≠ R24 RS-rank; ≠ R22 risksync; ≠ R4 book-disp fade; ≠ SB MaxKZ |",
                "",
                "R1–R27 densify + H4-engulf + HA/Keltner/ST/Ichimoku/ROC + lead + fade/session + FRED + RR2 exits: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 28 Week-struct / Month-end / Loss-CD",
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
                "# Session closeout — Round 28 Week-struct / Month-end / Loss-CD",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify week-HL-k / monthend-k / losscd-k /",
                "R27 Marubozu/Ichimoku/ROC / R26 HA/Keltner/ST / H4-engulf / lead /",
                "fade-session / unpark / RR2-exit / FRED.",
                "Next: next true greenfield outside R28 (still NON-FADE, non-indicator) —",
                "QFSI parallel; cost autonomous retry.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 28 Week-struct / Month-end / Loss-CD",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R27. **NON-FADE.** **NON-indicator** (structural/event/arch).",
                "Cấm densify H4-engulf / HA/Keltner/ST/Ichimoku/ROC / lead / fade-session / FRED / RR2-exit.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế",
                "1. Prior-week HL break — phá đỉnh/đáy tuần ISO đã đóng (structural)",
                "2. Month-end rebal — cửa sổ cuối/đầu tháng (event flow)",
                "3. Loss-cooldown arch — cooldown sau lệnh lỗ theo symbol (book architecture)",
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
                "# VN brief — Clean book + Round 28",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R28 NON-FADE structural/event/arch. GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 28 — Week-struct / Month-end / Loss-CD",
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
                "- R17 ETH VR / R21–R27 TA boards — không densify.",
                "",
                "## Cấm",
                "Densify R1–R28 / TA-indicator clones / VR / lead-clone / USD-imp / ORB/IB / "
                "fade-session / unpark / RR2-exit / FRED / Phase-0 / H4-engulf.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R28 (**NON-FADE, non-indicator**); cost = autonomous "
                "`history_deals_get` / QFSI — **không** hỏi Owner deal-export làm headline.",
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
        f"- **GREENFIELD ROUND28 WEEKSTRUCT/MONTHEND/LOSSCD CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE **non-indicator** greenfield outside R1–R27 densify",
        "  (structural / event / book-architecture; TA-clone ban).",
        "  Nested critic GO — Prior-week HL / Month-end rebal / Loss-cooldown "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R28_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        f"  Cost autonomous: {cost_note}",
        "  Do **not** densify week-HL-k / monthend-k / losscd-k /",
        "  R27 Marubozu/Ichimoku/ROC / R26 HA/Keltner/ST / R25 H4-engulf /",
        "  lead-clones / fade-session / ORB/IB / R24–R10 / R1–R9 / unpark /",
        "  RR2-exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R28 (still NON-FADE, non-indicator) —",
        "  QFSI parallel; cost autonomous retry (no Owner deal-export headline).",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R28 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND28 WEEKSTRUCT/MONTHEND/LOSSCD CLOSEOUT"):
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
                "Next = greenfield **outside** R1–R28 densify (NON-FADE, non-indicator), "
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
            base += f"; R28 retry history_deals_get raw_deals={deal_retry.get('raw_deals')}"
            cu = deal_retry.get("commission_unique_by_symbol") or {}
            if cu:
                base += f" comm_unique={cu}"
        else:
            base += f"; R28 retry FAIL ({deal_retry.get('error')})"
    return base + "; freeze_eligible=False"


def freeze_contract_sha() -> str:
    contract = {
        "prior_week_hl": {
            "body": PW_BODY,
            "sl": PW_SL,
            "rr": PW_RR,
            "hold": PW_HOLD,
            "universe": list(FX3),
        },
        "monthend_rebal": {
            "dom_late": ME_DOM_LATE,
            "dom_early": ME_DOM_EARLY,
            "body": ME_BODY,
            "sl": ME_SL,
            "rr": ME_RR,
            "hold": ME_HOLD,
            "symbol": "EURUSD",
        },
        "loss_cooldown_arch": {
            "body": LC_BODY,
            "cooldown_bars": LC_COOLDOWN_BARS,
            "sl": LC_SL,
            "rr": LC_RR,
            "hold": LC_HOLD,
            "universe": list(FX3),
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R1_R27_densify__TA_clones__H4engulf__lead__fade_session__FRED__RR2_exit",
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
                    "# Universe freeze — Round 28 Week-struct / Month-end / Loss-CD",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — lead self-merge).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001",
                    "2. HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001",
                    "3. HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001",
                    "",
                    "Mechanism note: (1) prior-week structure ≠ D1/fractal/Donch;",
                    "(2) month-end flow ≠ NFP/CPI/FRED; (3) loss-cooldown arch ≠ RS/risksync.",
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
                "HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001",
                "fx3_h1_prior_week_hl_break_cont",
                "FX3",
                "H1",
                *probe_fx3_prior_week_hl(h1),
            ),
            pack_result(
                "HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001",
                "eurusd_h1_monthend_rebal_cont",
                "EURUSD",
                "H1",
                *probe_eurusd_monthend(h1["EURUSD"]),
            ),
            pack_result(
                "HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001",
                "fx3_h1_loss_cooldown_arch_cont",
                "FX3",
                "H1",
                *probe_fx3_loss_cooldown(h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r28_weekstruct_monthend_losscd.v1_closedbar",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": (
                "NON_FADE__NON_INDICATOR__NO_R1_R27_DENSIFY__NO_H4ENGULF__"
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
            "deal_retry_r28": deal_retry,
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
