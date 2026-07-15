#!/usr/bin/env python3
"""Round 19 greenfield — CRYPTO3 breadth book + CADJPY risk-on + EURCHF sentiment.

HARD FORBIDDEN: ETH VR densify (VR-k / hold / multi-sym rescue of that exact object);
R18 AUD-imp/pivot/co-mom; R17 VR/semivar/UTC0; R16–R10 densify; residual/corr/
Parkinson/ON-ratio; fade/MR; unpark/exit/FRED; BTC/XAG ROC-k thick clones.

A priori freeze (before metrics):
  readouts/20260715_GREENFIELD_R19_CRYPTO3_BREADTH_RISKON_UNIVERSE_FREEZE.md
  1) HYP-CRYPTO3-H1-BREADTH-IMPULSE-CONT-BOOK-001
  2) HYP-CADJPY-H1-XTI-NAS-RISKON-CONT-001
  3) HYP-EURCHF-H1-NAS-SENTIMENT-CONT-001

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

STEM = "20260715_GREENFIELD_R19_CRYPTO3_BREADTH_RISKON"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R19_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# Book A — CRYPTO3 breadth (frozen)
CRYPTO3 = ("BTCUSD", "ETHUSD", "LTCUSD")
CR_IMP = 0.50
CR_BREADTH = 2
CR_SL = 1.50
CR_RR = 2.00
CR_HOLD = 10

# B — CADJPY ← XTI×NAS risk-on (frozen)
RO_XTI = 0.55
RO_NAS = 0.45
RO_SL = 1.45
RO_RR = 2.00
RO_HOLD = 10

# C — EURCHF ← NAS sentiment (frozen)
EC_NAS = 0.70
EC_SL = 1.40
EC_RR = 2.00
EC_HOLD = 10


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
    # crypto often needs finer lot floor
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


def probe_crypto3_breadth_book(data):
    """Multi-asset crypto thick book — breadth≥2 same-sign impulse; per-symbol heat."""
    closed, open_pos = [], []
    clock = data["BTCUSD"]["t"]
    last_day_sym = set()
    open_syms = set()
    for i in range(2, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, data, ts, closed, CR_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        # crypto 24/7 — no weekday filter
        sig_ts = int(clock[i - 1])
        impulses = []
        for sym in CRYPTO3:
            d = data[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 1:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < CR_IMP * atr:
                continue
            impulses.append((sym, 1 if body > 0 else -1, abs(body) / atr, j))
        if len(impulses) < CR_BREADTH:
            continue
        for side in (1, -1):
            members = [x for x in impulses if x[1] == side]
            if len(members) < CR_BREADTH:
                continue
            for sym, s, _str, j in members:
                day_key = (dt.date(), sym)
                if day_key in last_day_sym or sym in open_syms:
                    continue
                d = data[sym]
                ent_i = asof_idx(d, ts)
                if ent_i is None:
                    continue
                atr = d["atr"][j]
                if not np.isfinite(atr) or atr <= 0:
                    continue
                entry = float(d["o"][ent_i])
                sl = entry - s * CR_SL * atr
                tp = entry + s * CR_RR * CR_SL * atr
                lots = risk_lots(sym, entry, sl)
                open_pos.append(
                    {
                        "sym": sym,
                        "side": s,
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


def probe_cadjpy_xti_nas_riskon(cj, xti, nas):
    closed, open_pos = [], []
    sym = "CADJPY"
    last_day = None
    for i in range(2, len(cj["t"]) - 1):
        ts = int(cj["t"][i])
        open_pos = manage_exits(open_pos, {sym: cj}, ts, closed, RO_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig_ts = int(cj["t"][i - 1])
        xi = asof_idx(xti, sig_ts)
        ni = asof_idx(nas, sig_ts)
        if xi is None or ni is None:
            continue
        atr_x = xti["atr"][xi]
        atr_n = nas["atr"][ni]
        if not np.isfinite(atr_x) or atr_x <= 0 or not np.isfinite(atr_n) or atr_n <= 0:
            continue
        body_x = float(xti["c"][xi]) - float(xti["o"][xi])
        body_n = float(nas["c"][ni]) - float(nas["o"][ni])
        if abs(body_x) < RO_XTI * atr_x:
            continue
        if abs(body_n) < RO_NAS * atr_n:
            continue
        if (body_x > 0) != (body_n > 0):
            continue
        side = 1 if body_x > 0 else -1
        atr = cj["atr"][i - 1]
        if not np.isfinite(atr) or atr <= 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(cj["o"][i])
        sl = entry - side * RO_SL * atr
        tp = entry + side * RO_RR * RO_SL * atr
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
    flush_open(open_pos, {sym: cj}, closed)
    return summarize(closed)


def probe_eurchf_nas_sentiment(ec, nas):
    closed, open_pos = [], []
    sym = "EURCHF"
    last_day = None
    for i in range(2, len(ec["t"]) - 1):
        ts = int(ec["t"][i])
        open_pos = manage_exits(open_pos, {sym: ec}, ts, closed, EC_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig_ts = int(ec["t"][i - 1])
        ni = asof_idx(nas, sig_ts)
        if ni is None:
            continue
        atr_n = nas["atr"][ni]
        if not np.isfinite(atr_n) or atr_n <= 0:
            continue
        body_n = float(nas["c"][ni]) - float(nas["o"][ni])
        if abs(body_n) < EC_NAS * atr_n:
            continue
        side = 1 if body_n > 0 else -1
        atr = ec["atr"][i - 1]
        if not np.isfinite(atr) or atr <= 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(ec["o"][i])
        sl = entry - side * EC_SL * atr
        tp = entry + side * EC_RR * EC_SL * atr
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
    flush_open(open_pos, {sym: ec}, closed)
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
                "feature_family": "greenfield_r19_crypto3_breadth_riskon",
                "lane": "strategy_shift_r19_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R19 CRYPTO3 breadth book a priori + NON-FADE outside R10–R18; "
                    "ETH VR densify FORBIDDEN; nested critic GO"
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
                "# 3-critic panel — Round 19 CRYPTO3 breadth / risk-on / EURCHF",
                "",
                "Date: 2026-07-15",
                "Nested critic GO (lead self-merge). ETH VR near-miss densify FORBIDDEN.",
                "",
                "## Named (NON-FADE)",
                "1. `CRYPTO3_H1_BREADTH_IMPULSE_CONT_BOOK`",
                "2. `CADJPY_XTI_NAS_RISKON_CONT`",
                "3. `EURCHF_NAS_SENTIMENT_CONT`",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — crypto beta breadth + oil/equity risk-on + CHF sentiment |",
                "| Quant | SOFT — multi-asset heat / lead sync risk; freeze-only; no VR rescue |",
                "| MQL5/MT5 | PASS — closed-bar as-of; crypto 24/7 clock OK |",
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
                "# Design — Round 19 CRYPTO3 breadth / CADJPY risk-on / EURCHF",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                f"## 1 `HYP-CRYPTO3-H1-BREADTH-IMPULSE-CONT-BOOK-001`",
                f"Universe {list(CRYPTO3)} frozen; breadth≥{CR_BREADTH} with "
                f"|body|≥{CR_IMP}×ATR same sign → CONT each member next open; "
                f"SL={CR_SL} RR={CR_RR} hold≤{CR_HOLD}. NOT ETH VR densify.",
                "",
                f"## 2 `HYP-CADJPY-H1-XTI-NAS-RISKON-CONT-001`",
                f"XTI |body|≥{RO_XTI}×ATR and NAS same-sign |body|≥{RO_NAS}×ATR → "
                f"CADJPY CONT; SL={RO_SL} RR={RO_RR}.",
                "",
                f"## 3 `HYP-EURCHF-H1-NAS-SENTIMENT-CONT-001`",
                f"NAS |body|≥{EC_NAS}×ATR → EURCHF CONT same sign; SL={EC_SL} RR={EC_RR}.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Dedup already written a priori; refresh identical contract
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 19 CRYPTO3 breadth / CADJPY risk-on / EURCHF sentiment",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| CRYPTO3 H1 breadth impulse CONT book | ≠ ETH H4 VR mom densify "
                "(VR-k/hold/multi-sym rescue FORBIDDEN); ≠ BTC D1 ROC TSMOM thick; "
                "≠ ETH UTC0 open-drive; ≠ body-streak FX3; ≠ single-name crypto ROC |",
                "| CADJPY ← XTI×NAS risk-on CONT | ≠ WTI→USDCAD ToT; ≠ EURJPY←US30 lead; "
                "≠ GBPJPY×EURJPY co-mom; ≠ AUD COM3 resid MR; ≠ yen-β / NAS-β resid fade |",
                "| EURCHF ← NAS sentiment CONT | ≠ USDCHF FX-risk basket resid fade; "
                "≠ US30→FX lead densify; ≠ London-fix / session boards |",
                "",
                "R10–R18 densify boards + ETH VR near-miss densify: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 19 CRYPTO3 breadth / risk-on / EURCHF",
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
                "# Session closeout — Round 19 CRYPTO3 breadth / risk-on / EURCHF",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify CRYPTO3 breadth-k / CADJPY riskon-k / EURCHF nas-k /",
                "ETH VR-k / R18–R10 / R1–R9 / unpark / exit / FRED.",
                "Next: next true greenfield outside R19 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 19 CRYPTO3 breadth / risk-on / EURCHF",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R18. **NON-FADE.** Crypto book a priori ≠ densify ETH VR.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify CRYPTO3 breadth / CADJPY riskon / EURCHF / VR / R10–R18.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R19 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 19",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R19 NON-FADE (crypto a priori book + FX). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 19 — CRYPTO3 breadth / CADJPY risk-on / EURCHF",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "",
                "## Near-miss shelf (do not densify)",
                "- R17 ETH VR: PF≈1.98 x1.5≈1.77 but tpw≈0.33 — cadence only; "
                "**no** VR-k/hold/multi-sym rescue.",
                "- R16 EURJPY←US30 lead: PF≈1.09 N=1289 — PF/stress fail.",
                "- R13 XAU TSMOM: PF≈1.43 — no ROC-k densify.",
                "",
                "## Cấm",
                "Densify R1–R19 / VR rescue / CRYPTO3 breadth-k / fade-session / "
                "unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R19 (NON-FADE); cost khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND19 CRYPTO3/BREADTH/RISKON CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R18 densify + ETH VR near-miss ban.",
        "  A priori CRYPTO3 universe freeze before metrics "
        f"(sha={freeze_sha[:16]}…). Nested critic GO → lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R19_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify CRYPTO3 breadth-k / CADJPY riskon-k / EURCHF nas-k /",
        "  ETH VR-k / R18 AUD-imp/pivot/co-mom / R17 semivar/UTC0 / R16–R10 /",
        "  R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R19 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R19 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND19 CRYPTO3/BREADTH/RISKON CLOSEOUT"):
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
        "universe_crypto3": list(CRYPTO3),
        "crypto": {
            "imp": CR_IMP,
            "breadth": CR_BREADTH,
            "sl": CR_SL,
            "rr": CR_RR,
            "hold": CR_HOLD,
        },
        "riskon": {
            "xti": RO_XTI,
            "nas": RO_NAS,
            "sl": RO_SL,
            "rr": RO_RR,
            "hold": RO_HOLD,
        },
        "eurchf": {"nas": EC_NAS, "sl": EC_SL, "rr": EC_RR, "hold": EC_HOLD},
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "ETH_VR_densify_VR-k_hold_multisym_rescue",
    }
    return sha256_bytes(
        json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        freeze_sha = freeze_contract_sha()
        # stamp freeze sha into freeze memo if present
        if OUT_FREEZE.exists():
            txt = OUT_FREEZE.read_text(encoding="utf-8")
            if "Freeze SHA placeholder" in txt or "Freeze SHA:" in txt:
                lines = txt.splitlines()
                out_lines = []
                for ln in lines:
                    if ln.startswith("Freeze SHA placeholder") or ln.startswith(
                        "Freeze SHA:"
                    ):
                        out_lines.append(f"Freeze SHA: `{freeze_sha}`")
                    else:
                        out_lines.append(ln)
                OUT_FREEZE.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        crypto = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in CRYPTO3}
        cj = enrich(load("CADJPY", mt5.TIMEFRAME_H1))
        xti = enrich(load("XTIUSD", mt5.TIMEFRAME_H1))
        nas = enrich(load("NAS100", mt5.TIMEFRAME_H1))
        ec = enrich(load("EURCHF", mt5.TIMEFRAME_H1))
        results = [
            pack_result(
                "HYP-CRYPTO3-H1-BREADTH-IMPULSE-CONT-BOOK-001",
                "crypto3_h1_breadth_impulse_cont_book",
                "CRYPTO3",
                "H1",
                *probe_crypto3_breadth_book(crypto),
            ),
            pack_result(
                "HYP-CADJPY-H1-XTI-NAS-RISKON-CONT-001",
                "cadjpy_h1_xti_nas_riskon_cont",
                "CADJPY",
                "H1",
                *probe_cadjpy_xti_nas_riskon(cj, xti, nas),
            ),
            pack_result(
                "HYP-EURCHF-H1-NAS-SENTIMENT-CONT-001",
                "eurchf_h1_nas_sentiment_cont",
                "EURCHF",
                "H1",
                *probe_eurchf_nas_sentiment(ec, nas),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r19_crypto3_breadth_riskon.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": "NON_FADE__NO_R10_R18_DENSIFY__NO_ETH_VR_RESCUE",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "crypto3_book": {
                    "universe": list(CRYPTO3),
                    "imp": CR_IMP,
                    "breadth": CR_BREADTH,
                    "sl": CR_SL,
                    "rr": CR_RR,
                    "hold": CR_HOLD,
                },
                "riskon": {
                    "xti": RO_XTI,
                    "nas": RO_NAS,
                    "sl": RO_SL,
                    "rr": RO_RR,
                    "hold": RO_HOLD,
                },
                "eurchf": {
                    "nas": EC_NAS,
                    "sl": EC_SL,
                    "rr": EC_RR,
                    "hold": EC_HOLD,
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
        write_docs(results, receipt, any_surv, qnote, clean_note, freeze_sha)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, qnote, clean_note, freeze_sha)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "freeze_sha": freeze_sha,
                    "any_survivor": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            "m": r["metrics"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["fail_notes"],
                            "by_sym": r["detail"].get("by_sym"),
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
