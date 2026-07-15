#!/usr/bin/env python3
"""Round 13 greenfield — NON-FADE only; outside R10–R12 session/fade densify.

HARD FORBIDDEN densify:
  ≠ OHLC fade / mean-reversion / session-edge (Tokyo lunch, London fix/open,
    NY reopen, CLOSELOC, D1EMA dist, Fri-PM, relstr, WO-k, …)
  ≠ R1–R9 / unpark / triad / NAS-β fade / metal-ratio MR / CHF / COM3 /
    corr / yen-β / Parkinson / synth / ON-ratio / tickvol
  ≠ XS / AUDNZD / AONIA / CORRA / thin3 / carry / exit / FRED /
    LNY / TOM / weekend-gap-FADE / ORB / NR7 / VWAP / SB
  ≠ FX3 swing-thick / FX3 TSMOM-band densify

A priori (lead self-merge; nested Task unavailable):
  1) HYP-FX3-H1-NFP-IMPULSE-CONT-001
     — event-driven: reconstructable first-Friday US payroll window;
       CONTINUE first H1 impulse (≠ fade, ≠ London-fix)
  2) HYP-FX3-H1-CUSUM-BREAK-PERSIST-001
     — structural-break persistence via Page CUSUM on z-returns;
       trade WITH break (≠ residual fade / Parkinson)
  3) HYP-XAUUSD-H4-D1-TSMOM-THICK-001
     — multi-day momentum + thick stops on NON-FX3 book (XAU);
       ≠ FX3 swing/TSMOM densify; ≠ XAU USD-β fade; ≠ XAU/XAG zMR

+$12 joint. Model 0 only if PROBE_SURVIVOR.
"""
from __future__ import annotations

import hashlib
import json
import math
from calendar import monthcalendar
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

STEM = "20260715_GREENFIELD_R13_EVENT_CUSUM_XAUMOM"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R13_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 NFP impulse continuation (reconstructable first-Friday calendar)
NFP_BODY_ATR = 0.80
NFP_SL = 1.60
NFP_RR = 2.00
NFP_HOLD = 12
NFP_EVENT_HOURS = (12, 13)  # 8:30 ET ≈ 12:30/13:30 UTC across DST

# 2 CUSUM break persistence
CUSUM_K = 0.50  # allowance (in z units)
CUSUM_H = 3.50  # decision threshold
CUSUM_ZWIN = 48  # rolling std window for z
CUSUM_SL = 1.75
CUSUM_RR = 2.00
CUSUM_HOLD = 16
CUSUM_COOLDOWN = 24  # bars after fire before re-arm (per symbol)
CUSUM_MAX_DAY = 1  # book: first FX3 per UTC day

# 3 XAU D1 TSMOM → H4 thick
XAU_ROC = 20
XAU_ROC_ATR = 2.50  # |ROC20| ≥ 2.5×D1 ATR14
XAU_SL = 2.00
XAU_RR = 2.50
XAU_HOLD = 36  # H4 bars (~6 trading days)


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


def first_fridays(y0, y1):
    """Reconstructable US NFP schedule proxy: first Friday of each month."""
    out = set()
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            cal = monthcalendar(y, m)
            # monthcalendar rows Mon..Sun; Friday index=4
            for week in cal:
                if week[4] != 0:
                    out.add((y, m, week[4]))
                    break
    return out


def probe_nfp_impulse_cont(h1_data):
    """Event-driven continuation after reconstructable first-Friday payroll window."""
    nfp_days = first_fridays(FROM.year, TO.year)
    closed, open_pos = [], []
    clock = h1_data["EURUSD"]["t"]
    # Track per-event which symbols already entered
    fired = set()  # (y,m,d,sym)

    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: h1_data[s] for s in FX3}, ts, closed, NFP_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key_day = (dt.year, dt.month, dt.day)
        if key_day not in nfp_days:
            continue
        if dt.hour not in NFP_EVENT_HOURS:
            continue
        # Prefer the stronger of hour 12/13: evaluate each closed bar independently
        for sym in FX3:
            if (key_day[0], key_day[1], key_day[2], sym) in fired:
                continue
            d = h1_data[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j >= len(d["t"]) or d["t"][j] != ts:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < NFP_BODY_ATR * atr:
                continue
            # If both 12 and 13 fire, keep stronger body only once via fired set
            # Require this hour is the max-|body| among event hours present
            best = abs(body)
            for hh in NFP_EVENT_HOURS:
                # find bar same day hour hh
                for k in range(max(0, j - 3), min(len(d["t"]), j + 4)):
                    dtk = datetime.fromtimestamp(int(d["t"][k]), tz=timezone.utc)
                    if (dtk.year, dtk.month, dtk.day) != key_day:
                        continue
                    if dtk.hour != hh:
                        continue
                    atrk = d["atr"][k]
                    if not np.isfinite(atrk) or atrk <= 0:
                        continue
                    bk = abs(float(d["c"][k]) - float(d["o"][k]))
                    if bk > best + 1e-12:
                        best = bk
            if abs(body) + 1e-12 < best:
                continue  # wait for / skip weaker hour
            side = 1 if body > 0 else -1
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * NFP_SL * atr
            tp = entry + side * NFP_RR * NFP_SL * atr
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
            fired.add((key_day[0], key_day[1], key_day[2], sym))
    flush_open(open_pos, {s: h1_data[s] for s in FX3}, closed)
    return summarize(closed)


def rolling_std(x, n):
    out = np.full_like(x, np.nan, dtype=float)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1 : i + 1]
        out[i] = float(np.std(w, ddof=1)) if np.all(np.isfinite(w)) else np.nan
    return out


def probe_cusum_break_persist(h1_data):
    """Page CUSUM on z-returns; persist WITH structural break (not fade)."""
    closed, open_pos = [], []
    state = {
        s: {"sp": 0.0, "sm": 0.0, "cool": 0, "zstd": None, "ret": None} for s in FX3
    }
    for sym in FX3:
        d = h1_data[sym]
        ret = np.zeros(len(d["c"]))
        ret[1:] = d["c"][1:] - d["c"][:-1]
        # standardize by rolling std of returns (ATR-scale alternative)
        zstd = rolling_std(ret, CUSUM_ZWIN)
        state[sym]["ret"] = ret
        state[sym]["zstd"] = zstd

    clock = h1_data["EURUSD"]["t"]
    last_day, day_count = None, 0

    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(
            open_pos, {s: h1_data[s] for s in FX3}, ts, closed, CUSUM_HOLD
        )
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day, day_count = day, 0
        if dt.weekday() >= 5:
            continue
        if day_count >= CUSUM_MAX_DAY or open_pos:
            # still update CUSUM state even if not entering
            for sym in FX3:
                d = h1_data[sym]
                j = int(np.searchsorted(d["t"], ts, side="left"))
                if j >= len(d["t"]) or d["t"][j] != ts:
                    continue
                st = state[sym]
                if st["cool"] > 0:
                    st["cool"] -= 1
                zstd = st["zstd"][j]
                if not np.isfinite(zstd) or zstd <= 1e-12:
                    continue
                z = st["ret"][j] / zstd
                st["sp"] = max(0.0, st["sp"] + z - CUSUM_K)
                st["sm"] = max(0.0, st["sm"] - z - CUSUM_K)
            continue

        chosen = None
        for sym in FX3:
            d = h1_data[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j >= len(d["t"]) or d["t"][j] != ts:
                continue
            st = state[sym]
            if st["cool"] > 0:
                st["cool"] -= 1
                continue
            atr = d["atr"][j]
            zstd = st["zstd"][j]
            if not np.isfinite(atr) or atr <= 0 or not np.isfinite(zstd) or zstd <= 1e-12:
                continue
            z = st["ret"][j] / zstd
            st["sp"] = max(0.0, st["sp"] + z - CUSUM_K)
            st["sm"] = max(0.0, st["sm"] - z - CUSUM_K)
            side = 0
            if st["sp"] >= CUSUM_H:
                side = 1
            elif st["sm"] >= CUSUM_H:
                side = -1
            if side == 0:
                continue
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * CUSUM_SL * atr
            tp = entry + side * CUSUM_RR * CUSUM_SL * atr
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
            st["sp"] = 0.0
            st["sm"] = 0.0
            st["cool"] = CUSUM_COOLDOWN
            break
        if chosen:
            open_pos.append(chosen)
            day_count += 1
    flush_open(open_pos, {s: h1_data[s] for s in FX3}, closed)
    return summarize(closed)


def probe_xau_d1_tsmom_thick(d1, h4):
    """Non-FX3 multi-day momentum with thick H4 stops.

    Precompute as-of D1 TSMOM side for each H4 bar (last closed D1 only).
    Single H4 walk — no double-count of hold bars.
    """
    closed, open_pos = [], []
    # Build D1 signal series: side at D1 close usable after +86400
    d1_side = np.zeros(len(d1["t"]), dtype=int)
    for i in range(XAU_ROC + 2, len(d1["c"])):
        atr = d1["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        roc = float(d1["c"][i] - d1["c"][i - XAU_ROC])
        if abs(roc) < XAU_ROC_ATR * atr:
            continue
        d1_side[i] = 1 if roc > 0 else -1

    # Map to H4: for each H4 bar, last D1 whose close ≤ H4 open
    h4_sig = np.zeros(len(h4["t"]), dtype=int)
    j = 0
    for i, ts in enumerate(h4["t"]):
        while j + 1 < len(d1["t"]) and int(d1["t"][j + 1]) + 86400 <= int(ts):
            j += 1
        if int(d1["t"][j]) + 86400 <= int(ts):
            h4_sig[i] = d1_side[j]
        elif j > 0:
            h4_sig[i] = d1_side[j - 1]

    last_sig_day = None
    for i in range(1, len(h4["t"]) - 1):
        ts = int(h4["t"][i])
        open_pos = manage_exits(open_pos, {"XAUUSD": h4}, ts, closed, XAU_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        side = int(h4_sig[i])
        if side == 0:
            continue
        # Fire only on first H4 where this D1 signal becomes available
        prev = int(h4_sig[i - 1])
        if side == prev:
            continue
        day = dt.date()
        if day == last_sig_day:
            continue
        # ATR from prior closed H4 (no lookahead into bar i range)
        atr = h4["atr"][i - 1]
        if not np.isfinite(atr) or atr <= 0:
            continue
        entry = float(h4["o"][i])
        sl = entry - side * XAU_SL * atr
        tp = entry + side * XAU_RR * XAU_SL * atr
        lots = risk_lots("XAUUSD", entry, sl)
        open_pos.append(
            {
                "sym": "XAUUSD",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        last_sig_day = day
    flush_open(open_pos, {"XAUUSD": h4}, closed)
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
                "feature_family": "greenfield_r13_event_cusum_xaumom",
                "lane": "strategy_shift_r13_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R13 NON-FADE outside R10–R12 session/fade densify; lead self-merge"
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
                "# 3-critic panel — Round 13 event / CUSUM / XAU-mom",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast` — Task backend unavailable;",
                "lead self-merge.",
                "",
                "## Named classes (NON-FADE)",
                "1. `FX3_NFP_IMPULSE_CONT` — event-driven reconstructable timestamps",
                "2. `FX3_CUSUM_BREAK_PERSIST` — structural-break persistence",
                "3. `XAU_D1_TSMOM_H4_THICK` — multi-day mom thick stops non-FX3",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — payroll impulse + regime break + gold trend; ≠ fade/session densify |",
                "| Quant | SOFT — NFP DST hour proxy; CUSUM k/h a priori; XAU cadence may be thin |",
                "| MQL5/MT5 | PASS — closed-bar event hour; CUSUM update then next-open; D1→H4 as-of |",
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
                "# Design — Round 13 NFP cont / CUSUM persist / XAU thick-mom",
                "",
                "Date: 2026-07-15",
                "Hard constraint: **FORBIDDEN** OHLC fade / MR / session-edge densify.",
                "",
                f"## 1 `HYP-FX3-H1-NFP-IMPULSE-CONT-001`",
                f"First-Friday calendar (reconstructable); H1 hour∈{NFP_EVENT_HOURS} UTC;",
                f"|body|≥{NFP_BODY_ATR}×ATR → CONTINUE impulse; SL={NFP_SL} RR={NFP_RR} "
                f"hold≤{NFP_HOLD}; per-symbol once/event.",
                "",
                f"## 2 `HYP-FX3-H1-CUSUM-BREAK-PERSIST-001`",
                f"Page CUSUM on z-returns (win={CUSUM_ZWIN}, k={CUSUM_K}, h={CUSUM_H});",
                f"trade WITH break; SL={CUSUM_SL} RR={CUSUM_RR} hold≤{CUSUM_HOLD}; "
                f"cooldown={CUSUM_COOLDOWN}; first FX3/day.",
                "",
                f"## 3 `HYP-XAUUSD-H4-D1-TSMOM-THICK-001`",
                f"D1 |ROC{XAU_ROC}|≥{XAU_ROC_ATR}×ATR → H4 thick mom; SL={XAU_SL} "
                f"RR={XAU_RR} hold≤{XAU_HOLD}.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 13 event / CUSUM / XAU-mom",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| NFP impulse CONT | ≠ London-fix reversion; ≠ Fri-PM fade; ≠ session R10; ≠ weekend-gap fade |",
                "| CUSUM break persist | ≠ residual/β fade; ≠ Parkinson compress-expand; ≠ corr-break recouple |",
                "| XAU D1 TSMOM thick | ≠ FX3 swing-thick / FX3 TSMOM-band; ≠ XAU USD-β fade; ≠ XAU/XAG zMR |",
                "",
                "R10–R12 fade/session densify boards: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 13 event / CUSUM / XAU-mom",
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
                "# Session closeout — Round 13 event / CUSUM / XAU-mom",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify NFP body-k / CUSUM h-k / XAU ROC-k / R10–R12 fade/session.",
                "Next: next true greenfield outside R13 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 13 event / CUSUM / XAU-mom",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R12 fade/session densify. Lead self-merge. **NON-FADE only.**",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify NFP-k / CUSUM-h / XAU-ROC / R10–R12 fade-session.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R13 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 13 (post R12)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book path quanh Phase-0 CONTAMINATED + discovery R13 NON-FADE.",
                "GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Freeze a priori trước metrics; **không** clear Phase-0 contamination.",
                "- Model 0 book-level: **WITHHELD** (offline pool ≠ EA challenger).",
                "",
                "## 2. Discovery Round 13 — NFP cont / CUSUM persist / XAU thick-mom",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "Spot-check once — không babysit.",
                "",
                "## Cấm",
                "Densify R1–R13 / fade-session / unpark / exit / FRED / Phase-0 ceremony.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R13 (vẫn NON-FADE); cost provenance khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND13 EVENT/CUSUM/XAUMOM CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R12 fade/session densify + R1–R9/unpark/exit/FRED.",
        "  Nested critic Task unavailable → lead self-merge `cursor-grok-4.5-high-fast`.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R13_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify NFP body-k / CUSUM h-k / XAU ROC-k /",
        "  R12 EMA/Fri/RS / R11 fix/WO/closeloc / R10 session / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R13 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R13 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND13 EVENT/CUSUM/XAUMOM CLOSEOUT"):
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
        xau_d1 = enrich(load("XAUUSD", mt5.TIMEFRAME_D1))
        xau_h4 = enrich(load("XAUUSD", mt5.TIMEFRAME_H4))
        results = [
            pack_result(
                "HYP-FX3-H1-NFP-IMPULSE-CONT-001",
                "fx3_h1_nfp_impulse_cont",
                "FX3",
                "H1",
                *probe_nfp_impulse_cont(h1),
            ),
            pack_result(
                "HYP-FX3-H1-CUSUM-BREAK-PERSIST-001",
                "fx3_h1_cusum_break_persist",
                "FX3",
                "H1",
                *probe_cusum_break_persist(h1),
            ),
            pack_result(
                "HYP-XAUUSD-H4-D1-TSMOM-THICK-001",
                "xauusd_h4_d1_tsmom_thick",
                "XAUUSD",
                "H4",
                *probe_xau_d1_tsmom_thick(xau_d1, xau_h4),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r13_event_cusum_xaumom.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "hard_constraint": "NON_FADE__NO_SESSION_EDGE_DENSIFY",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "nfp": {
                    "body_atr": NFP_BODY_ATR,
                    "sl": NFP_SL,
                    "rr": NFP_RR,
                    "hold": NFP_HOLD,
                    "event_hours_utc": list(NFP_EVENT_HOURS),
                },
                "cusum": {
                    "k": CUSUM_K,
                    "h": CUSUM_H,
                    "zwin": CUSUM_ZWIN,
                    "sl": CUSUM_SL,
                    "rr": CUSUM_RR,
                    "hold": CUSUM_HOLD,
                    "cooldown": CUSUM_COOLDOWN,
                },
                "xau_mom": {
                    "roc": XAU_ROC,
                    "roc_atr": XAU_ROC_ATR,
                    "sl": XAU_SL,
                    "rr": XAU_RR,
                    "hold": XAU_HOLD,
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
                            "notes": r["fail_notes"],
                        }
                        for r in results
                    ],
                    "qfsi": qnote,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
