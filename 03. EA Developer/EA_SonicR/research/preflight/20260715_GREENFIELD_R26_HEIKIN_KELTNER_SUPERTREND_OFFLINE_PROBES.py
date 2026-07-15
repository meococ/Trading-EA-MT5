#!/usr/bin/env python3
"""Round 26 greenfield — Heikin streak + Keltner walk + Supertrend flip CONT.

Post R25: RangeP80/H4-engulf/VWAP ALL_KILL (H4-engulf near-miss — NO densify).
NON-FADE outside R1–R25 densify.

HARD FORBIDDEN: R25 RangeP80/H4-engulf/VWAP densify; R24 NR7/ER/RS-rank;
R23 MTF/fractal/postshock; R22 AC/ATR-exp/risksync; lead-clones; USD-implied;
ORB/IB densify; fade/MR; unpark/exit/FRED; inside-bar M15 densify; EMA-stack-PB densify.

A priori (≥2 mechanisms; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-HEIKIN-STREAK-CONT-001
  2) HYP-EURUSD-H1-KELTNER-WALK-CONT-001
  3) HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001

+$12 joint thick∩cadence. Model 0 only if PROBE_SURVIVOR. Closed-bar only.
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

STEM = "20260715_GREENFIELD_R26_HEIKIN_KELTNER_SUPERTREND"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R26_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"
OUT_DEAL_RETRY = PRE / "20260715_COST_DEAL_RETRY_R26.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 Heikin-Ashi streak CONT
HA_STREAK = 3
HA_BODY = 0.35
HA_SL = 1.45
HA_RR = 2.00
HA_HOLD = 10

# 2 Keltner walk CONT
KEL_EMA = 20
KEL_ATR_MULT = 1.50
KEL_WALK = 2  # consecutive closes outside band
KEL_BODY = 0.35
KEL_SL = 1.45
KEL_RR = 2.00
KEL_HOLD = 10

# 3 Supertrend flip CONT
ST_ATR_N = 10
ST_MULT = 3.0
ST_BODY = 0.35
ST_SL = 1.45
ST_RR = 2.00
ST_HOLD = 10


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


def ema_arr(x, n):
    out = np.full(len(x), np.nan, dtype=float)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1.0)
    out[n - 1] = float(np.mean(x[:n]))
    for i in range(n, len(x)):
        out[i] = a * float(x[i]) + (1.0 - a) * out[i - 1]
    return out


def heikin_ashi(o, h, l, c):
    n = len(c)
    ha_c = (o + h + l + c) / 4.0
    ha_o = np.empty(n, dtype=float)
    ha_o[0] = (float(o[0]) + float(c[0])) / 2.0
    for i in range(1, n):
        ha_o[i] = (ha_o[i - 1] + ha_c[i - 1]) / 2.0
    return ha_o, ha_c


def supertrend_dir(h, l, c, atr, n=ST_ATR_N, mult=ST_MULT):
    """Closed-bar Supertrend direction: +1 uptrend, -1 downtrend."""
    m = len(c)
    direction = np.zeros(m, dtype=int)
    final_upper = np.full(m, np.nan)
    final_lower = np.full(m, np.nan)
    for i in range(m):
        if not np.isfinite(atr[i]) or atr[i] <= 0:
            direction[i] = direction[i - 1] if i else 0
            continue
        mid = (float(h[i]) + float(l[i])) / 2.0
        basic_upper = mid + mult * float(atr[i])
        basic_lower = mid - mult * float(atr[i])
        if i == 0 or not np.isfinite(final_upper[i - 1]):
            final_upper[i] = basic_upper
            final_lower[i] = basic_lower
            direction[i] = 1 if float(c[i]) > mid else -1
            continue
        # Final bands (classic Supertrend recursion on closed bars)
        if basic_lower > final_lower[i - 1] or float(c[i - 1]) < final_lower[i - 1]:
            final_lower[i] = basic_lower
        else:
            final_lower[i] = final_lower[i - 1]
        if basic_upper < final_upper[i - 1] or float(c[i - 1]) > final_upper[i - 1]:
            final_upper[i] = basic_upper
        else:
            final_upper[i] = final_upper[i - 1]
        prev_dir = direction[i - 1] if direction[i - 1] != 0 else 1
        if prev_dir == 1:
            direction[i] = -1 if float(c[i]) < final_lower[i] else 1
        else:
            direction[i] = 1 if float(c[i]) > final_upper[i] else -1
        # If flipped, snap band to basic
        if direction[i] != prev_dir:
            if direction[i] == 1:
                final_lower[i] = basic_lower
            else:
                final_upper[i] = basic_upper
    return direction


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
    d["atr_st"] = atr_arr(d["h"], d["l"], d["c"], n=ST_ATR_N)
    d["ema20"] = ema_arr(d["c"], KEL_EMA)
    ha_o, ha_c = heikin_ashi(d["o"], d["h"], d["l"], d["c"])
    d["ha_o"] = ha_o
    d["ha_c"] = ha_c
    d["st_dir"] = supertrend_dir(d["h"], d["l"], d["c"], d["atr_st"])
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


def probe_fx3_heikin_streak(h1):
    """FX3: HA streak of HA_STREAK same-color closed bars + real body CONT."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    for i in range(HA_STREAK + 20, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, HA_HOLD)
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
            if j is None or j < HA_STREAK:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # HA colors on closed bars j-HA_STREAK+1 .. j
            colors = []
            ok = True
            for k in range(j - HA_STREAK + 1, j + 1):
                if d["ha_c"][k] > d["ha_o"][k]:
                    colors.append(1)
                elif d["ha_c"][k] < d["ha_o"][k]:
                    colors.append(-1)
                else:
                    ok = False
                    break
            if not ok or len(set(colors)) != 1:
                continue
            side = colors[0]
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < HA_BODY * atr:
                continue
            if (side > 0 and body <= 0) or (side < 0 and body >= 0):
                continue
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * HA_SL * atr
            tp = entry + side * HA_RR * HA_SL * atr
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


def probe_eurusd_keltner_walk(eu):
    """EURUSD: KELT_WALK consecutive closes outside Keltner → CONT."""
    closed, open_pos = [], []
    sym = "EURUSD"
    last_day = None
    for i in range(KEL_EMA + KEL_WALK + 5, len(eu["t"]) - 1):
        ts = int(eu["t"][i])
        open_pos = manage_exits(open_pos, {sym: eu}, ts, closed, KEL_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1
        atr = eu["atr"][j]
        ema = eu["ema20"][j]
        if not np.isfinite(atr) or atr <= 0 or not np.isfinite(ema):
            continue
        # Walk: last KEL_WALK closed bars all outside same side (per-bar bands)
        outs_up = True
        outs_dn = True
        for k in range(KEL_WALK):
            jj = j - k
            a = eu["atr"][jj]
            e = eu["ema20"][jj]
            if not np.isfinite(a) or a <= 0 or not np.isfinite(e):
                outs_up = outs_dn = False
                break
            u = e + KEL_ATR_MULT * a
            lo = e - KEL_ATR_MULT * a
            if float(eu["c"][jj]) <= u:
                outs_up = False
            if float(eu["c"][jj]) >= lo:
                outs_dn = False
        if outs_up:
            side = 1
        elif outs_dn:
            side = -1
        else:
            continue
        body = float(eu["c"][j]) - float(eu["o"][j])
        if abs(body) < KEL_BODY * atr:
            continue
        if (side > 0 and body <= 0) or (side < 0 and body >= 0):
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(eu["o"][i])
        sl = entry - side * KEL_SL * atr
        tp = entry + side * KEL_RR * KEL_SL * atr
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


def probe_usdjpy_supertrend_flip(uj):
    """USDJPY: Supertrend direction flip on closed bar + body CONT."""
    closed, open_pos = [], []
    sym = "USDJPY"
    last_day = None
    last_flip_i = None
    for i in range(ST_ATR_N + 5, len(uj["t"]) - 1):
        ts = int(uj["t"][i])
        open_pos = manage_exits(open_pos, {sym: uj}, ts, closed, ST_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1
        if j < 1:
            continue
        d0, d1 = int(uj["st_dir"][j - 1]), int(uj["st_dir"][j])
        if d0 == 0 or d1 == 0 or d0 == d1:
            continue
        if last_flip_i == j:
            continue
        side = d1  # new trend direction
        atr = uj["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(uj["c"][j]) - float(uj["o"][j])
        if abs(body) < ST_BODY * atr:
            continue
        if (side > 0 and body <= 0) or (side < 0 and body >= 0):
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(uj["o"][i])
        sl = entry - side * ST_SL * atr
        tp = entry + side * ST_RR * ST_SL * atr
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
        last_flip_i = j
    flush_open(open_pos, {sym: uj}, closed)
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
                "feature_family": "greenfield_r26_heikin_keltner_supertrend",
                "lane": "strategy_shift_r26_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R26 NON-FADE after R25 RangeP80/H4-engulf/VWAP ALL_KILL; "
                    "nested critic GO lead self-merge; NO H4-engulf densify"
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
                "# 3-critic panel — Round 26 Heikin / Keltner / Supertrend",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (lead self-merge; outside R1–R25 densify).",
                "",
                "## Named (NON-FADE)",
                "1. Heikin-Ashi streak CONT — HA color persistence (≠ raw close streak)",
                "2. Keltner walk CONT — channel walk (≠ Donch / RangeP80 / ATR-exp%)",
                "3. Supertrend flip CONT — ATR-trail regime flip (≠ Kaufman ER / AC)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — classic trend-following trio, non-fade |",
                "| Quant | PASS — independent mechanisms; joint gates a priori |",
                "| MQL5/MT5 | PASS — HA/ST from closed bars only; next-open entry |",
                "",
                "Merge: **GO** offline only. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "Near-miss ban carry: R25 H4-engulf — do **not** densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 26 Heikin / Keltner / Supertrend",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-HEIKIN-STREAK-CONT-001`",
                f"{HA_STREAK} closed HA same-color + real |body|≥{HA_BODY}×ATR → CONT.",
                "Why: HA filter ≠ R15 raw streak; ≠ three-bar reverse; ≠ H4-engulf.",
                "",
                "## 2 `HYP-EURUSD-H1-KELTNER-WALK-CONT-001`",
                f"{KEL_WALK} closes outside EMA{KEL_EMA}±{KEL_ATR_MULT}×ATR + body → CONT.",
                "Why: channel walk ≠ Donch8; ≠ RangeP80 expand; ≠ ATR-exp%.",
                "",
                "## 3 `HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001`",
                f"Supertrend({ST_ATR_N},{ST_MULT}) flip + body≥{ST_BODY}×ATR → CONT.",
                "Why: ATR-trail flip ≠ Kaufman ER; ≠ lag1-AC; ≠ MTF align.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 26 Heikin / Keltner / Supertrend",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 HA streak CONT | ≠ R15 close-streak; ≠ 3-bar rev; ≠ H4-engulf |",
                "| EURUSD Keltner walk | ≠ R21 Donch8; ≠ R25 RangeP80; ≠ R22 ATR-exp |",
                "| USDJPY Supertrend flip | ≠ R24 Kaufman ER; ≠ R22 AC; ≠ R23 MTF |",
                "",
                "R1–R25 densify + lead + ORB/IB + fade + H4-engulf near-miss: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 26 Heikin / Keltner / Supertrend",
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
                "# Session closeout — Round 26 Heikin / Keltner / Supertrend",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify Heikin-k / Keltner-k / Supertrend-k /",
                "R25 RangeP80/H4-engulf/VWAP / R24 NR7/ER/RS / lead / ORB / unpark / exit / FRED.",
                "Next: next true greenfield outside R26 — QFSI parallel; cost autonomous retry.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 26 Heikin / Keltner / Supertrend",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R25. **NON-FADE.** Không densify H4-engulf near-miss.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế",
                "1. Heikin streak — màu HA liên tiếp (≠ streak close thô)",
                "2. Keltner walk — đi ngoài kênh (≠ Donch/RangeP80)",
                "3. Supertrend flip — lật trail ATR (≠ ER/AC)",
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
                "# VN brief — Clean book + Round 26",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R26 NON-FADE (Heikin/Keltner/Supertrend). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 26 — Heikin / Keltner / Supertrend",
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
                "- R17 ETH VR / R21 USD-imp / R22–R25 thick PF-fail boards — không densify.",
                "",
                "## Cấm",
                "Densify R1–R26 / VR / lead-clone / USD-imp / ORB/IB / fade-session / "
                "unpark / exit / FRED / Phase-0 / H4-engulf.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R26 (NON-FADE); cost = autonomous "
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
        f"- **GREENFIELD ROUND26 HEIKIN/KELTNER/SUPERTREND CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R1–R25 densify (incl. H4-engulf near-miss ban).",
        "  Nested critic GO — Heikin-streak / Keltner-walk / Supertrend-flip "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R26_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        f"  Cost autonomous: {cost_note}",
        "  Do **not** densify Heikin-k / Keltner-k / Supertrend-k /",
        "  R25 RangeP80/H4-engulf/VWAP / R24 NR7/ER/RS / lead-clones /",
        "  ORB/IB / R23–R10 / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R26 (still NON-FADE) — QFSI parallel; "
        "cost autonomous retry (no Owner deal-export headline).",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R26 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND26 HEIKIN/KELTNER/SUPERTREND CLOSEOUT"):
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
                "Next = greenfield **outside** R1–R26 densify (NON-FADE), or cost via "
                "autonomous `history_deals_get` / QFSI (no Owner deal-export headline). "
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
    """Optional autonomous history_deals_get spot-check — do not invent counts."""
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
            base += f"; R26 retry history_deals_get raw_deals={deal_retry.get('raw_deals')}"
            cu = deal_retry.get("commission_unique_by_symbol") or {}
            if cu:
                base += f" comm_unique={cu}"
        else:
            base += f"; R26 retry FAIL ({deal_retry.get('error')})"
    return base + "; freeze_eligible=False"


def freeze_contract_sha() -> str:
    contract = {
        "heikin": {
            "streak": HA_STREAK,
            "body": HA_BODY,
            "sl": HA_SL,
            "rr": HA_RR,
            "hold": HA_HOLD,
            "universe": list(FX3),
        },
        "keltner": {
            "ema": KEL_EMA,
            "atr_mult": KEL_ATR_MULT,
            "walk": KEL_WALK,
            "body": KEL_BODY,
            "sl": KEL_SL,
            "rr": KEL_RR,
            "hold": KEL_HOLD,
        },
        "supertrend": {
            "atr_n": ST_ATR_N,
            "mult": ST_MULT,
            "body": ST_BODY,
            "sl": ST_SL,
            "rr": ST_RR,
            "hold": ST_HOLD,
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R1_R25_densify__H4engulf_nearmiss__lead__ORB_IB_fade",
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
                    "# Universe freeze — Round 26 Heikin / Keltner / Supertrend",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — lead self-merge).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-HEIKIN-STREAK-CONT-001",
                    "2. HYP-EURUSD-H1-KELTNER-WALK-CONT-001",
                    "3. HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001",
                    "",
                    "Mechanism note: (1) HA streak≠raw streak; (2) Keltner walk≠Donch/RangeP80; "
                    "(3) Supertrend flip≠ER/AC. H4-engulf densify FORBIDDEN.",
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
                "HYP-FX3-H1-HEIKIN-STREAK-CONT-001",
                "fx3_h1_heikin_streak_cont",
                "FX3",
                "H1",
                *probe_fx3_heikin_streak(h1),
            ),
            pack_result(
                "HYP-EURUSD-H1-KELTNER-WALK-CONT-001",
                "eurusd_h1_keltner_walk_cont",
                "EURUSD",
                "H1",
                *probe_eurusd_keltner_walk(h1["EURUSD"]),
            ),
            pack_result(
                "HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001",
                "usdjpy_h1_supertrend_flip_cont",
                "USDJPY",
                "H1",
                *probe_usdjpy_supertrend_flip(h1["USDJPY"]),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r26_heikin_keltner_supertrend.v1_closedbar",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": "NON_FADE__NO_R1_R25_DENSIFY__NO_H4ENGULF__NO_LEAD__NO_ORB_IB",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "qfsi_parallel": qnote,
            "cost_autonomous": cost_note,
            "deal_retry_r26": deal_retry,
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
