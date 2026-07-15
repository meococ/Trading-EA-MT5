#!/usr/bin/env python3
"""Round 21 greenfield — two-bar accel + Donch8 bodyQ + USD-implied EURJPY.

HARD FORBIDDEN: R20 XAU→NZD / USDJPY→XAU-inv / XTI→AUD; R19 CRYPTO3/riskon/
EURCHF; ETH VR; R18 AUD-imp/pivot/co-mom; R17–R10 densify; Parkinson/compress;
lead-impulse clones R16–R20; fade/MR; unpark/exit/FRED.

A priori (nested critic GO — quality/structural, not lead clones):
  1) HYP-FX3-H1-TWOBAR-ACCEL-CLOSECONF-CONT-001
  2) HYP-GBPUSD-H1-DONCH8-BREAK-BODYQ-CONT-001
  3) HYP-EURJPY-H1-USD-IMPLIED-CROSS-CONT-001

+$12 joint thick∩cadence. Model 0 only if PROBE_SURVIVOR.
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

STEM = "20260715_GREENFIELD_R21_ACCEL_DONCH_USDIMP"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R21_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 two-bar accel + close conf
AC_BODY = 0.40
AC_RATIO = 1.25
AC_CLOSE = 0.25  # outer 25% of range
AC_SL = 1.45
AC_RR = 2.00
AC_HOLD = 10

# 2 Donch8 break + bodyQ
DN_N = 8
DN_BREAK = 0.20
DN_BODY = 0.50
DN_SL = 1.45
DN_RR = 2.00
DN_HOLD = 10

# 3 USD-implied EURJPY cross
UI_IMP = 0.55
UI_LEG = 0.35
UI_SL = 1.40
UI_RR = 2.00
UI_HOLD = 10


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


def probe_fx3_twobar_accel(data):
    """FX3 book: 2-bar accel + close in outer quartile → CONT."""
    closed, open_pos = [], []
    clock = data["EURUSD"]["t"]
    last_day_sym = set()
    open_syms = set()
    for i in range(3, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, data, ts, closed, AC_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        for sym in FX3:
            if sym in open_syms:
                continue
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            d = data[sym]
            j2 = asof_idx(d, sig_ts)
            if j2 is None or j2 < 1:
                continue
            j1 = j2 - 1
            atr = d["atr"][j2]
            if not np.isfinite(atr) or atr <= 0:
                continue
            b1 = float(d["c"][j1]) - float(d["o"][j1])
            b2 = float(d["c"][j2]) - float(d["o"][j2])
            if abs(b1) < AC_BODY * atr or abs(b2) < AC_BODY * atr:
                continue
            if (b1 > 0) != (b2 > 0):
                continue
            if abs(b2) < AC_RATIO * abs(b1):
                continue
            rng = float(d["h"][j2]) - float(d["l"][j2])
            if rng <= 0:
                continue
            if b2 > 0:
                loc = (float(d["c"][j2]) - float(d["l"][j2])) / rng
                if loc < (1.0 - AC_CLOSE):
                    continue
                side = 1
            else:
                loc = (float(d["h"][j2]) - float(d["c"][j2])) / rng
                if loc < (1.0 - AC_CLOSE):
                    continue
                side = -1
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * AC_SL * atr
            tp = entry + side * AC_RR * AC_SL * atr
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
    flush_open(open_pos, data, closed)
    return summarize(closed)


def probe_gbpusd_donch8(gb):
    closed, open_pos = [], []
    sym = "GBPUSD"
    last_day = None
    for i in range(DN_N + 2, len(gb["t"]) - 1):
        ts = int(gb["t"][i])
        open_pos = manage_exits(open_pos, {sym: gb}, ts, closed, DN_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1  # signal bar
        atr = gb["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        prior_h = float(np.max(gb["h"][j - DN_N : j]))
        prior_l = float(np.min(gb["l"][j - DN_N : j]))
        body = float(gb["c"][j]) - float(gb["o"][j])
        c = float(gb["c"][j])
        side = 0
        if c >= prior_h + DN_BREAK * atr and body >= DN_BODY * atr:
            side = 1
        elif c <= prior_l - DN_BREAK * atr and body <= -DN_BODY * atr:
            side = -1
        if side == 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(gb["o"][i])
        sl = entry - side * DN_SL * atr
        tp = entry + side * DN_RR * DN_SL * atr
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
    flush_open(open_pos, {sym: gb}, closed)
    return summarize(closed)


def probe_eurjpy_usd_implied(ej, eu, uj):
    closed, open_pos = [], []
    sym = "EURJPY"
    last_day = None
    for i in range(2, len(ej["t"]) - 1):
        ts = int(ej["t"][i])
        open_pos = manage_exits(open_pos, {sym: ej}, ts, closed, UI_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig_ts = int(ej["t"][i - 1])
        ei = asof_idx(eu, sig_ts)
        ji = asof_idx(uj, sig_ts)
        if ei is None or ji is None:
            continue
        atr_e = eu["atr"][ei]
        atr_j = uj["atr"][ji]
        atr = ej["atr"][i - 1]
        if (
            not np.isfinite(atr_e)
            or atr_e <= 0
            or not np.isfinite(atr_j)
            or atr_j <= 0
            or not np.isfinite(atr)
            or atr <= 0
        ):
            continue
        be = float(eu["c"][ei]) - float(eu["o"][ei])
        bj = float(uj["c"][ji]) - float(uj["o"][ji])
        if abs(be) < UI_LEG * atr_e or abs(bj) < UI_LEG * atr_j:
            continue
        # Implied EURJPY move ≈ EURUSD body in price units of EJ is not 1:1;
        # use signed ATR-normalized legs: r_imp = be/atr_e - bj/atr_j
        # (USDJPY up = JPY weak = EURJPY up contribution from -USDJPY? Wait:
        # EURJPY ≈ EURUSD * USDJPY. d(log EJ) ≈ d(log EU) + d(log UJ).
        # So r_imp = be/atr_e + bj/atr_j in signed ATR units.
        r_imp = (be / atr_e) + (bj / atr_j)
        if abs(r_imp) < UI_IMP:
            continue
        side = 1 if r_imp > 0 else -1
        day = dt.date()
        if day == last_day:
            continue
        entry = float(ej["o"][i])
        sl = entry - side * UI_SL * atr
        tp = entry + side * UI_RR * UI_SL * atr
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
    flush_open(open_pos, {sym: ej}, closed)
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
                "feature_family": "greenfield_r21_accel_donch_usdimp",
                "lane": "strategy_shift_r21_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R21 NON-FADE quality/structural outside R10–R20; "
                    "nested critic GO; not lead-impulse clones"
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


def write_docs(results, receipt, any_surv, qnote, clean_book_note, freeze_sha):
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
                "# 3-critic panel — Round 21 accel / Donch8 / USD-implied",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (quality/structural; avoid R16–R20 lead clones).",
                "",
                "## Named (NON-FADE)",
                "1. `FX3_H1_TWOBAR_ACCEL_CLOSECONF_CONT`",
                "2. `GBPUSD_H1_DONCH8_BREAK_BODYQ_CONT`",
                "3. `EURJPY_H1_USD_IMPLIED_CROSS_CONT`",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — own-bar accel / channel break / FX identity CONT |",
                "| Quant | PASS — independent objects; AND-gates vs VR starvation |",
                "| MQL5/MT5 | PASS — closed-bar as-of; EURUSD+USDJPY → EURJPY |",
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
                "# Design — Round 21 accel / Donch8 / USD-implied",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                f"## 1 `HYP-FX3-H1-TWOBAR-ACCEL-CLOSECONF-CONT-001`",
                f"2 same-sign bodies ≥{AC_BODY}×ATR; bar2≥{AC_RATIO}×bar1; close outer "
                f"{int(AC_CLOSE*100)}% → CONT FX3; SL={AC_SL} RR={AC_RR}. ≠ streak-3 densify.",
                "",
                f"## 2 `HYP-GBPUSD-H1-DONCH8-BREAK-BODYQ-CONT-001`",
                f"Close beyond prior-{DN_N} HL by ≥{DN_BREAK}×ATR AND |body|≥{DN_BODY}×ATR "
                f"→ CONT; SL={DN_SL} RR={DN_RR}. ≠ US30 D1 HL / pivot R1S1.",
                "",
                f"## 3 `HYP-EURJPY-H1-USD-IMPLIED-CROSS-CONT-001`",
                f"r_imp=be/atr_e+bj/atr_j; |r_imp|≥{UI_IMP} and legs ≥{UI_LEG}×ATR → "
                f"EURJPY CONT; SL={UI_SL} RR={UI_RR}. ≠ co-mom / US30-lead / β-fade.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 21 accel / Donch8 / USD-implied",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 two-bar accel+closeconf CONT | ≠ R15 streak-N; ≠ R11 closeloc-only; "
                "≠ R16–R20 lead-impulse |",
                "| GBPUSD Donch8 break+bodyQ CONT | ≠ R16 US30 D1 HL; ≠ R18 pivot; "
                "≠ Parkinson compress; ≠ unpark inside |",
                "| EURJPY USD-implied cross CONT | ≠ R18 GBPJPY×EURJPY co-mom; "
                "≠ R8 β-resid fade; ≠ R16 US30-lead; ≠ R19 risk-on |",
                "",
                "R10–R20 densify boards: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 21 accel / Donch8 / USD-implied",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Freeze SHA256: `{freeze_sha}`",
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
                "# Session closeout — Round 21 accel / Donch8 / USD-implied",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify accel-k / Donch8-k / USD-imp-k /",
                "R20 XAU-NZD/USDJPY-inv/XTI-AUD / R19–R10 / unpark / exit / FRED.",
                "Next: next true greenfield outside R21 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 21 accel / Donch8 / USD-implied",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R20. **NON-FADE.** Quality/structural (không lead-clone).",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify accel / Donch8 / USD-imp / R10–R20.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R21 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 21",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R21 NON-FADE (accel/Donch/USD-imp). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 21 — accel / Donch8 / USD-implied",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "",
                "## Near-miss shelf (do not densify)",
                "- R17 ETH VR: PF≈1.98 x1.5≈1.77 but tpw≈0.33 — cadence only.",
                "- R19 CRYPTO3 breadth: tpw≈19.9 but PF≈0.95 — thick cadence thin edge.",
                "- R20 lead board: tpw≈4.9 PF≈0.92–1.02 — cadence OK, edge insolvent.",
                "",
                "## Cấm",
                "Densify R1–R21 / VR rescue / lead-clone rescue / fade-session / "
                "unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R21 (NON-FADE); cost khi Owner drop deal-export.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, receipt, any_surv, qnote, clean_note, freeze_sha):
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
        f"- **GREENFIELD ROUND21 ACCEL/DONCH/USDIMP CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R20 densify + ETH VR near-miss ban.",
        "  Nested critic GO — quality/structural (not lead-impulse clones) "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R21_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify accel-k / Donch8-k / USD-imp-k /",
        "  R20 XAU-NZD/USDJPY-inv/XTI-AUD / R19 CRYPTO3/riskon/EURCHF /",
        "  ETH VR-k / R18–R10 / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R21 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R21 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND21 ACCEL/DONCH/USDIMP CLOSEOUT"):
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


def freeze_contract_sha() -> str:
    contract = {
        "accel": {
            "body": AC_BODY,
            "ratio": AC_RATIO,
            "close": AC_CLOSE,
            "sl": AC_SL,
            "rr": AC_RR,
            "hold": AC_HOLD,
            "universe": list(FX3),
        },
        "donch": {
            "n": DN_N,
            "break": DN_BREAK,
            "body": DN_BODY,
            "sl": DN_SL,
            "rr": DN_RR,
            "hold": DN_HOLD,
        },
        "usdimp": {
            "imp": UI_IMP,
            "leg": UI_LEG,
            "sl": UI_SL,
            "rr": UI_RR,
            "hold": UI_HOLD,
            "formula": "r_imp=be/atr_e+bj/atr_j",
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R10_R20_densify__ETH_VR__lead_impulse_clones",
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
                    "# Universe freeze — Round 21 accel / Donch8 / USD-implied",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-TWOBAR-ACCEL-CLOSECONF-CONT-001",
                    "2. HYP-GBPUSD-H1-DONCH8-BREAK-BODYQ-CONT-001",
                    "3. HYP-EURJPY-H1-USD-IMPLIED-CROSS-CONT-001",
                    "",
                    "Formula note: EURJPY implied uses r_imp = be/atr_e + bj/atr_j "
                    "(log-additivity of EURUSD×USDJPY).",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        fx3 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        gb = enrich(load("GBPUSD", mt5.TIMEFRAME_H1))
        ej = enrich(load("EURJPY", mt5.TIMEFRAME_H1))
        eu = fx3["EURUSD"]
        uj = fx3["USDJPY"]
        results = [
            pack_result(
                "HYP-FX3-H1-TWOBAR-ACCEL-CLOSECONF-CONT-001",
                "fx3_h1_twobar_accel_closeconf_cont",
                "FX3",
                "H1",
                *probe_fx3_twobar_accel(fx3),
            ),
            pack_result(
                "HYP-GBPUSD-H1-DONCH8-BREAK-BODYQ-CONT-001",
                "gbpusd_h1_donch8_break_bodyq_cont",
                "GBPUSD",
                "H1",
                *probe_gbpusd_donch8(gb),
            ),
            pack_result(
                "HYP-EURJPY-H1-USD-IMPLIED-CROSS-CONT-001",
                "eurjpy_h1_usd_implied_cross_cont",
                "EURJPY",
                "H1",
                *probe_eurjpy_usd_implied(ej, eu, uj),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r21_accel_donch_usdimp.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": "NON_FADE__NO_R10_R20_DENSIFY__NO_ETH_VR_RESCUE",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "accel": {
                    "body": AC_BODY,
                    "ratio": AC_RATIO,
                    "close": AC_CLOSE,
                    "sl": AC_SL,
                    "rr": AC_RR,
                    "hold": AC_HOLD,
                },
                "donch": {
                    "n": DN_N,
                    "break": DN_BREAK,
                    "body": DN_BODY,
                    "sl": DN_SL,
                    "rr": DN_RR,
                    "hold": DN_HOLD,
                },
                "usdimp": {
                    "imp": UI_IMP,
                    "leg": UI_LEG,
                    "sl": UI_SL,
                    "rr": UI_RR,
                    "hold": UI_HOLD,
                },
            },
            "qfsi_parallel": qnote,
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
        write_docs(results, receipt, any_surv, qnote, clean_note, freeze_sha)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, qnote, clean_note, freeze_sha)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "receipt": receipt,
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
