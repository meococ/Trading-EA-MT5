#!/usr/bin/env python3
"""Second greenfield joint screen after USD-lag + TSMOM ALL_KILL.

Outside densify:
  ≠ majority ATR / TS band (just killed), ≠ AONIA/CORRA/thin3,
  ≠ consec3 fade, ≠ bodyATR cont, ≠ swing ADX, ≠ D1 volregime,
  ≠ XS residual, ≠ LNY/TOM/gap, ≠ carry/anticarry, ≠ FRED/RR2-exit.

A priori (≥2), +$12, Model 0 only if PROBE_SURVIVOR:
  1) HYP-FX3-H4-TRENDDAY-FAILBREAK-SPRING-001
  2) HYP-FX3-H4BIAS-H1-PB-RECLAIM-CONT-001
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

OUT_JSON = PRE / "20260715_GREENFIELD_SPRING_PBRECLAIM_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_SPRING_PBRECLAIM_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_SPRING_PBRECLAIM_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_SPRING_PBRECLAIM_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_SPRING_PBRECLAIM_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_SPRING_PBRECLAIM_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Spring fail-break ---
SPR_BODY = 0.70
SPR_OUTER = 0.15  # close in outer 15% of range
SPR_PIERCE = 0.15
SPR_SL_PAD = 0.15
SPR_RR = 2.5
SPR_HOLD = 6
SPR_MAX_OPEN = 1
SPR_MAX_PER_DAY = 1

# --- H4 bias → H1 PB reclaim ---
BIAS_BODY = 0.55
BIAS_OUTER = 0.25
BIAS_LIFE = 8  # H4 bars
PB_LO = 0.40
PB_HI = 0.85
PB_MID_TOL = 0.10  # ATR_H4
RECLAIM_BODY = 0.30
PB_SL_PAD = 0.10
PB_RR = 3.0
PB_HOLD = 12  # H1
PB_MAX_OPEN_SYM = 1
PB_MAX_PER_DAY = 1
PB_BOOK_MAX = 2


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


def load(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"{symbol} tf={tf}: {mt5.last_error()}")
    return {
        "t": rates["time"].astype(np.int64),
        "o": rates["open"].astype(float),
        "h": rates["high"].astype(float),
        "l": rates["low"].astype(float),
        "c": rates["close"].astype(float),
    }


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


def close_loc(o, h, l, c):
    rng = h - l
    if rng <= 0:
        return 0.5
    return (c - l) / rng


def probe_trendday_failbreak_spring(data):
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, SPR_HOLD)
        if dt.weekday() >= 5 or len(open_pos) >= SPR_MAX_OPEN:
            continue
        # Arm = j-1 (T-1), trigger = j (T), enter at i (next open after T)
        j = i - 1
        arm = j - 1
        if arm < 20:
            continue
        day = dt.date().isoformat()

        for sym in FX3:
            if len(open_pos) >= SPR_MAX_OPEN:
                break
            if any(p["sym"] == sym for p in open_pos):
                continue
            if day_count.get((day, sym), 0) >= SPR_MAX_PER_DAY:
                continue
            d = data[sym]
            a_i = int(np.searchsorted(d["t"], clock[arm], side="left"))
            t_i = int(np.searchsorted(d["t"], clock[j], side="left"))
            e_i = int(np.searchsorted(d["t"], ts, side="left"))
            if (
                a_i < 20
                or t_i >= len(d["t"])
                or e_i >= len(d["t"])
                or d["t"][a_i] != clock[arm]
                or d["t"][t_i] != clock[j]
                or d["t"][e_i] != ts
            ):
                continue
            atr_a = d["atr"][a_i]
            atr_t = d["atr"][t_i]
            if not np.isfinite(atr_a) or atr_a <= 0 or not np.isfinite(atr_t) or atr_t <= 0:
                continue
            ao, ah, al, ac = d["o"][a_i], d["h"][a_i], d["l"][a_i], d["c"][a_i]
            to_, th, tl, tc = d["o"][t_i], d["h"][t_i], d["l"][t_i], d["c"][t_i]
            arng = ah - al
            if arng <= 0:
                continue
            body = abs(ac - ao)
            if body < SPR_BODY * atr_a:
                continue
            loc = close_loc(ao, ah, al, ac)
            bull_arm = ac > ao
            if bull_arm and loc < (1.0 - SPR_OUTER):
                continue
            if (not bull_arm) and loc > SPR_OUTER:
                continue
            mid = (ah + al) / 2.0

            if bull_arm:
                # upside fail: pierce high then close back inside + below mid
                if th < ah + SPR_PIERCE * atr_t:
                    continue
                if not (al <= tc <= ah):
                    continue
                if tc >= mid:
                    continue
                side = -1
                fail_ext = th
            else:
                if tl > al - SPR_PIERCE * atr_t:
                    continue
                if not (al <= tc <= ah):
                    continue
                if tc <= mid:
                    continue
                side = 1
                fail_ext = tl

            entry = float(d["o"][e_i])
            if side < 0:
                sl = fail_ext + SPR_SL_PAD * atr_t
            else:
                sl = fail_ext - SPR_SL_PAD * atr_t
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + side * SPR_RR * risk
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": risk_lots(sym, entry, sl),
                    "bars": 0,
                }
            )
            day_count[(day, sym)] = day_count.get((day, sym), 0) + 1

    flush_open(open_pos, data, closed)
    return summarize(closed)


def align_h4_idx(h4_t, ts):
    """Index of last H4 bar whose open time <= ts."""
    idx = int(np.searchsorted(h4_t, ts, side="right")) - 1
    return idx


def probe_h4bias_h1_pb_reclaim(h4, h1):
    """H4 displacement bias → bounded H1 pullback + reclaim continuation."""
    closed = []
    clock = h1["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    # Active bias per symbol: dict with fields
    bias = {s: None for s in FX3}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, h1, ts, closed, PB_HOLD)

        # Update / create H4 bias from last fully closed H4 (open time + 4h <= now)
        for sym in FX3:
            d4 = h4[sym]
            # last closed H4: bar open + 4h <= current H1 open
            # H4 duration seconds = 4*3600
            closed_before = ts - 4 * 3600
            k = align_h4_idx(d4["t"], closed_before)
            if k < 20:
                continue
            atr4 = d4["atr"][k]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            o, h, l, c = d4["o"][k], d4["h"][k], d4["l"][k], d4["c"][k]
            body = abs(c - o)
            loc = close_loc(o, h, l, c)
            new_bias = None
            if body >= BIAS_BODY * atr4:
                if c > o and loc >= (1.0 - BIAS_OUTER):
                    new_bias = {
                        "side": 1,
                        "mid": (h + l) / 2.0,
                        "ext": h,
                        "atr4": atr4,
                        "h4_i": k,
                        "born_h4": k,
                    }
                elif c < o and loc <= BIAS_OUTER:
                    new_bias = {
                        "side": -1,
                        "mid": (h + l) / 2.0,
                        "ext": l,
                        "atr4": atr4,
                        "h4_i": k,
                        "born_h4": k,
                    }
            b = bias[sym]
            if new_bias is not None:
                # refresh bias only if newer than current
                if b is None or new_bias["h4_i"] > b["h4_i"]:
                    bias[sym] = new_bias
                    b = bias[sym]
            if b is None:
                continue
            # age out
            if k - b["born_h4"] > BIAS_LIFE:
                bias[sym] = None
                continue
            # invalidate if H4 closes beyond opposite mid
            if b["side"] > 0 and c < b["mid"]:
                bias[sym] = None
                continue
            if b["side"] < 0 and c > b["mid"]:
                bias[sym] = None
                continue
            # update running extreme after bias
            if b["side"] > 0:
                b["ext"] = max(b["ext"], h)
            else:
                b["ext"] = min(b["ext"], l)

        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= PB_BOOK_MAX:
            continue
        open_syms = {p["sym"] for p in open_pos}
        day = dt.date().isoformat()

        for sym in FX3:
            if sym in open_syms or len(open_pos) >= PB_BOOK_MAX:
                continue
            if day_count.get((day, sym), 0) >= PB_MAX_PER_DAY:
                continue
            b = bias[sym]
            if b is None:
                continue
            d1 = h1[sym]
            idx = int(np.searchsorted(d1["t"], ts, side="left"))
            if idx < 30 or d1["t"][idx] != ts:
                continue
            # signal on closed H1 idx-1; enter at open idx
            j = idx - 1
            atr1 = d1["atr"][j]
            if not np.isfinite(atr1) or atr1 <= 0:
                continue
            # Pullback window starts AFTER bias H4 completes (post-bias extreme).
            bias_t = int(h4[sym]["t"][b["h4_i"]])
            start = int(np.searchsorted(d1["t"], bias_t + 4 * 3600, side="left"))
            if start < 0 or j - start < 3:
                continue
            # Running post-bias extreme then adverse PB into [start, j)
            # Reclaim evaluated on closed bar j.
            pre_h = d1["h"][start:j]
            pre_l = d1["l"][start:j]
            if len(pre_h) < 2:
                continue
            if b["side"] > 0:
                post_ext = float(np.max(pre_h))
                pb_ext = float(np.min(pre_l))
                depth = post_ext - pb_ext
                if depth < PB_LO * atr1 or depth > PB_HI * atr1:
                    continue
                if pb_ext < b["mid"] - PB_MID_TOL * b["atr4"]:
                    continue
                # Reclaim: bullish body closing back above PB extreme
                body = d1["c"][j] - d1["o"][j]
                if d1["c"][j] <= pb_ext or body < RECLAIM_BODY * atr1:
                    continue
                side = 1
                sl = pb_ext - PB_SL_PAD * atr1
            else:
                post_ext = float(np.min(pre_l))
                pb_ext = float(np.max(pre_h))
                depth = pb_ext - post_ext
                if depth < PB_LO * atr1 or depth > PB_HI * atr1:
                    continue
                if pb_ext > b["mid"] + PB_MID_TOL * b["atr4"]:
                    continue
                body = d1["o"][j] - d1["c"][j]
                if d1["c"][j] >= pb_ext or body < RECLAIM_BODY * atr1:
                    continue
                side = -1
                sl = pb_ext + PB_SL_PAD * atr1

            entry = float(d1["o"][idx])
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + side * PB_RR * risk
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": risk_lots(sym, entry, sl),
                    "bars": 0,
                }
            )
            open_syms.add(sym)
            day_count[(day, sym)] = day_count.get((day, sym), 0) + 1
            # consume bias after fire
            bias[sym] = None

    flush_open(open_pos, h1, closed)
    return summarize(closed)


def write_all(results, receipt, any_surv):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Trend-day fail-break spring + H4-bias H1 PB-reclaim",
                "",
                "Date: 2026-07-15",
                "Parent: USD-lag + TSMOM ALL_KILL (thick near-miss on TS).",
                "Nested critic `cursor-grok-4.5-high-fast`. Prefer quality over densify TS.",
                "",
                "## 1 `HYP-FX3-H4-TRENDDAY-FAILBREAK-SPRING-001`",
                "Arm: H4 body≥0.70 ATR + close outer 15%. Trigger: pierce≥0.15 ATR then",
                "close back inside past mid → spring fade. SL pad 0.15 ATR; RR2.5; hold≤6.",
                "",
                "## 2 `HYP-FX3-H4BIAS-H1-PB-RECLAIM-CONT-001`",
                "H4 bias body≥0.55 ATR outer 25%; H1 PB depth [0.40,0.85] ATR not through mid;",
                "reclaim body≥0.30 ATR → continue. SL pad 0.10; RR3; hold≤12 H1.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. Do not densify majority/TS/AONIA/CORRA/thin3.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — spring fail-break + H4-bias PB-reclaim",
                "",
                "| Object | Clearance |",
                "|---|---|",
                "| trendday fail-break spring | ≠ consec3 fade; ≠ TS/bodyATR cont; ≠ outside/engulf packs; ≠ D1 breakout |",
                "| H4-bias H1 PB-reclaim | ≠ TSMOM densify; ≠ swing ADX/thrust; ≠ majority lag; ≠ LNY session densify |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline — spring + PB-reclaim",
        "",
        f"Receipt `{receipt}`",
        f"Generated `{utc_now()}`",
        "Cost a priori +$12; gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['hypothesis_id']}",
            f"- **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
            f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']}",
            f"- detail={json.dumps(r['detail'])}",
            "",
        ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — spring + PB-reclaim greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do not densify spring pierce / PB depth / RR / majority / TS / AONIA / CORRA / thin3.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — spring + PB-reclaim greenfield",
                f"- `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify spring/PB / majority/TS / AONIA/CORRA/thin3.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Append to session brief
    prev = ""
    if OUT_SESSION_VN.exists():
        prev = OUT_SESSION_VN.read_text(encoding="utf-8").rstrip() + "\n\n"
    OUT_SESSION_VN.write_text(
        prev
        + "\n".join(
            [
                "## Round 2 — spring + PB-reclaim (post USD-lag/TSMOM kill)",
                f"- Status: `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → **{r['verdict']}**"
                    for r in results
                ],
                f"- Receipt `{receipt}`",
                "- Zero Model 0 unless survivor. Next: true greenfield ngoài killboard.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(results, receipt):
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "killed"
                        if r["verdict"] != "PROBE_SURVIVOR"
                        else "probe_survivor",
                        "parent_candidate": "post_usd_lag_tsmom_greenfield_20260715",
                        "feature_family": "greenfield_spring_pbreclaim",
                        "lane": "greenfield_spring_pbreclaim_20260715",
                        "setup_type": r["setup_type"],
                        "symbol": r["symbol"],
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
                            "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace(
                                "\\", "/"
                            ),
                            "receipt_sha256": receipt,
                            "status": r["verdict"],
                            "dedup": str(OUT_DEDUP.relative_to(ROOT)).replace("\\", "/"),
                        },
                        "verdict": r["verdict"],
                        "reason": ",".join(r["fail_notes"]) or "offline_pass",
                        "updated_at": "2026-07-15",
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )


def patch_hot(results, receipt, any_surv):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD SPRING + PB-RECLAIM CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Post USD-lag/TSMOM thick near-miss; quality-over-densify greenfield.",
        "  Nested critic `cursor-grok-4.5-high-fast`. Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_SPRING_PBRECLAIM_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_SPRING_PBRECLAIM_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify spring pierce / PB depth / RR / majority / TS / AONIA / CORRA / thin3.",
        "  Next: next true greenfield outside killboard — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Spring+PB-reclaim greenfield "
            f"{status.split('__')[0]}; GOAL unmet"
        )
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        for s in FX3:
            mt5.symbol_select(s, True)
        h4 = {}
        h1 = {}
        for s in FX3:
            d4 = load(s, mt5.TIMEFRAME_H4)
            d4["atr"] = atr_arr(d4["h"], d4["l"], d4["c"], 14)
            h4[s] = d4
            d1 = load(s, mt5.TIMEFRAME_H1)
            d1["atr"] = atr_arr(d1["h"], d1["l"], d1["c"], 14)
            h1[s] = d1

        pnls1, det1 = probe_trendday_failbreak_spring(h4)
        m1, hc1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, hc1)

        pnls2, det2 = probe_h4bias_h1_pb_reclaim(h4, h1)
        m2, hc2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, hc2)

        results = [
            {
                "hypothesis_id": "HYP-FX3-H4-TRENDDAY-FAILBREAK-SPRING-001",
                "setup_type": (
                    "H4 trend-day arm + fail-pierce→close-inside spring fade; "
                    "RR2.5 hold≤6"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "metrics": m1,
                "haircuts": hc1,
                "verdict": v1,
                "fail_notes": n1,
                "detail": det1,
            },
            {
                "hypothesis_id": "HYP-FX3-H4BIAS-H1-PB-RECLAIM-CONT-001",
                "setup_type": (
                    "H4 bias→H1 PB[0.4,0.85]ATR reclaim cont; SL0.1 RR3 hold≤12"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4→H1",
                "metrics": m2,
                "haircuts": hc2,
                "verdict": v2,
                "fail_notes": n2,
                "detail": det2,
            },
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema": "greenfield_spring_pbreclaim_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "window": "2021.01.01-2025.12.31",
            "parent_kill": "USD-lag+TSMOM ALL_KILL receipt 7FF7448A…",
            "results": results,
            "any_survivor": any_surv,
            "model0_authorized": any_surv,
            "receipt_sha256": None,
        }
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        write_all(results, receipt, any_surv)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_survivor": any_surv,
                    "model0_authorized": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            **r["metrics"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["fail_notes"],
                            "detail": r["detail"],
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
