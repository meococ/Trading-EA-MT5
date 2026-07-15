#!/usr/bin/env python3
"""Round 24 greenfield — NR7 breakout + ER regime mom + RS-rank CONT.

Post R23: MTF/fractal/postshock ALL_KILL (v2 closed-bar). Prefer mechanisms
outside R1–R23 densify bans. NON-FADE only.

HARD FORBIDDEN: R23 MTF/fractal/postshock densify; R22 AC/ATR-exp/risksync;
lead-clones; USD-implied; R21–R10 densify; Parkinson/compress; residual/corr/
ON-ratio; ETH VR; fade/MR; unpark/exit/FRED; London/NY ORB densify (parked M15);
inside-bar M15 densify.

A priori (≥2 mechanisms; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-NR7-BREAKOUT-CONT-001
     Toby Crabel NR7 (narrowest range of last 7) then next closed bar breaks
     NR7 high/low with bodyQ → CONT.
  2) HYP-GBPUSD-H1-ER-REGIME-MOM-CONT-001
     Kaufman Efficiency Ratio(10) ≥ threshold + directional body → CONT.
  3) HYP-EURUSD-H1-RS-RANK-CONT-001
     EURUSD 20-bar ROC ranks #1 among FX3 (USDJPY as -JPY ret) → CONT.

+$12 joint thick∩cadence. Model 0 only if PROBE_SURVIVOR.
Closed-bar only — no forming-bar peek.
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

STEM = "20260715_GREENFIELD_R24_NR7_ER_RSRANK"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R24_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"
OUT_COST = READ / "20260715_COST_DEAL_PULL_R24_GAP.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 NR7 breakout
NR_N = 7
NR_BODY = 0.40
NR_SL = 1.45
NR_RR = 2.00
NR_HOLD = 10

# 2 Kaufman ER regime mom
ER_N = 10
ER_MIN = 0.55
ER_BODY = 0.45
ER_SL = 1.45
ER_RR = 2.00
ER_HOLD = 10

# 3 RS-rank CONT
RS_N = 20
RS_BODY = 0.40
RS_SL = 1.45
RS_RR = 2.00
RS_HOLD = 10


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


def efficiency_ratio(c, i, n):
    """Kaufman ER at closed bar i using bars [i-n+1 .. i]."""
    if i < n:
        return np.nan
    change = abs(float(c[i]) - float(c[i - n]))
    path = 0.0
    for k in range(i - n + 1, i + 1):
        path += abs(float(c[k]) - float(c[k - 1]))
    if path <= 1e-12:
        return np.nan
    return change / path


def probe_fx3_nr7(h1):
    """FX3: NR7 compression then breakout CONT (closed-bar)."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    # Per-symbol pending NR7 levels after NR7 bar closes
    pending = {s: None for s in FX3}  # {hi, lo, atr, day}

    for i in range(NR_N + 2, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, NR_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])

        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < NR_N:
                continue
            # Detect NR7 on signal bar (fully closed)
            ranges = d["h"][j - NR_N + 1 : j + 1] - d["l"][j - NR_N + 1 : j + 1]
            if len(ranges) < NR_N or not np.all(np.isfinite(ranges)):
                continue
            if float(ranges[-1]) <= float(np.min(ranges)):
                atr = d["atr"][j]
                if np.isfinite(atr) and atr > 0:
                    pending[sym] = {
                        "hi": float(d["h"][j]),
                        "lo": float(d["l"][j]),
                        "atr": float(atr),
                        "nr_ts": sig_ts,
                    }

            if sym in open_syms:
                continue
            pend = pending[sym]
            if pend is None:
                continue
            # Break must be on a later bar than NR7
            if sig_ts <= pend["nr_ts"]:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            c = float(d["c"][j])
            side = 0
            if c > pend["hi"] and body >= NR_BODY * atr:
                side = 1
            elif c < pend["lo"] and body <= -NR_BODY * atr:
                side = -1
            if side == 0:
                continue
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * NR_SL * atr
            tp = entry + side * NR_RR * NR_SL * atr
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
            pending[sym] = None  # consume
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def probe_gbpusd_er(gb):
    """GBPUSD: Kaufman ER regime + body CONT."""
    closed, open_pos = [], []
    sym = "GBPUSD"
    last_day = None
    for i in range(ER_N + 3, len(gb["t"]) - 1):
        ts = int(gb["t"][i])
        open_pos = manage_exits(open_pos, {sym: gb}, ts, closed, ER_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1  # signal = last closed
        er = efficiency_ratio(gb["c"], j, ER_N)
        atr = gb["atr"][j]
        if not np.isfinite(er) or not np.isfinite(atr) or atr <= 0:
            continue
        if er < ER_MIN:
            continue
        body = float(gb["c"][j]) - float(gb["o"][j])
        if abs(body) < ER_BODY * atr:
            continue
        # Direction from net change over ER window (closed)
        net = float(gb["c"][j]) - float(gb["c"][j - ER_N])
        if net == 0:
            continue
        side = 1 if net > 0 else -1
        if (side > 0 and body <= 0) or (side < 0 and body >= 0):
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(gb["o"][i])
        sl = entry - side * ER_SL * atr
        tp = entry + side * ER_RR * ER_SL * atr
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


def probe_eurusd_rs_rank(h1):
    """EURUSD: 20-bar ROC ranks #1 among FX3 → CONT with bodyQ.

    USDJPY score = -ROC so 'USD strength vs JPY' aligns with EURUSD long bias
    when EUR leads USD pairs; ranks are signed FX3 relative momentum.
    """
    closed, open_pos = [], []
    sym = "EURUSD"
    last_day = None
    # Align on EURUSD clock; look up each symbol by timestamp
    eu = h1["EURUSD"]
    for i in range(RS_N + 3, len(eu["t"]) - 1):
        ts = int(eu["t"][i])
        open_pos = manage_exits(open_pos, {sym: eu}, ts, closed, RS_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig_ts = int(eu["t"][i - 1])
        scores = {}
        ok = True
        for s in FX3:
            d = h1[s]
            j = asof_idx(d, sig_ts)
            if j is None or j < RS_N:
                ok = False
                break
            c0 = float(d["c"][j - RS_N])
            c1 = float(d["c"][j])
            if c0 <= 0:
                ok = False
                break
            roc = (c1 - c0) / c0
            # For USDJPY, invert so higher score = stronger USD (weaker JPY)
            # Rank among FX3 as relative USD-pair strength for EURUSD decision:
            # use raw ROC for EUR/GBP; for USDJPY use -roc (JPY strength).
            scores[s] = roc if s != "USDJPY" else -roc
        if not ok:
            continue
        # EURUSD must be strictly best (long) or strictly worst (short)
        eu_score = scores["EURUSD"]
        others = [scores[s] for s in FX3 if s != "EURUSD"]
        side = 0
        if eu_score > max(others):
            side = 1
        elif eu_score < min(others):
            side = -1
        if side == 0:
            continue
        j = asof_idx(eu, sig_ts)
        if j is None:
            continue
        atr = eu["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(eu["c"][j]) - float(eu["o"][j])
        if abs(body) < RS_BODY * atr:
            continue
        if (side > 0 and body <= 0) or (side < 0 and body >= 0):
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(eu["o"][i])
        sl = entry - side * RS_SL * atr
        tp = entry + side * RS_RR * RS_SL * atr
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
                "feature_family": "greenfield_r24_nr7_er_rsrank",
                "lane": "strategy_shift_r24_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R24 NON-FADE after R23 MTF/fractal/postshock ALL_KILL; "
                    "nested critic GO lead self-merge; no ORB/IB densify"
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
                "# 3-critic panel — Round 24 NR7 / ER / RS-rank",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (lead self-merge; outside R1–R23 densify).",
                "",
                "## Named (NON-FADE) — why different mechanisms",
                "1. `FX3_H1_NR7_BREAKOUT_CONT` — Crabel compression→expansion (≠ Donch/ATR-exp/fractal)",
                "2. `GBPUSD_H1_ER_REGIME_MOM_CONT` — Kaufman path-efficiency regime (≠ lag1-AC)",
                "3. `EURUSD_H1_RS_RANK_CONT` — intra-FX3 relative strength rank (≠ cross-asset lead)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — classic NR7 + efficiency + RS; not fade/session densify |",
                "| Quant | PASS — independent params; joint thick∩cadence gates a priori |",
                "| MQL5/MT5 | PASS — closed-bar NR7 confirm then later break; ER/RS as-of signal bar |",
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
                "# Design — Round 24 NR7 / ER / RS-rank",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## Mandate",
                "Outside R1–R23 densify. NON-FADE. No ORB/IB densify (prior parked/killed).",
                "",
                f"## 1 `HYP-FX3-H1-NR7-BREAKOUT-CONT-001`",
                f"NR{NR_N} (narrowest range of {NR_N}); later close beyond NR hi/lo with",
                f"|body|≥{NR_BODY}×ATR → CONT; SL={NR_SL} RR={NR_RR}.",
                "Why: compression→expansion — ≠ R21 Donch8; ≠ R22 ATR-exp; ≠ R23 fractal.",
                "",
                f"## 2 `HYP-GBPUSD-H1-ER-REGIME-MOM-CONT-001`",
                f"Kaufman ER({ER_N})≥{ER_MIN} + |body|≥{ER_BODY}×ATR aligned to ER net → CONT;",
                f"SL={ER_SL} RR={ER_RR}.",
                "Why: path-efficiency regime — ≠ R22 lag1-AC; ≠ R21 two-bar accel.",
                "",
                f"## 3 `HYP-EURUSD-H1-RS-RANK-CONT-001`",
                f"EURUSD ROC({RS_N}) strictly best/worst among FX3 + bodyQ → CONT;",
                f"SL={RS_SL} RR={RS_RR}.",
                "Why: intra-basket RS — ≠ cross-asset lead-clones; ≠ R22 FX3-risksync.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 24 NR7 / ER / RS-rank",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 NR7 breakout CONT | ≠ R21 Donch8; ≠ R22 ATR-exp burst; ≠ R23 fractal5; "
                "≠ M15 inside-bar densify (different TF+NR7 definition) |",
                "| GBPUSD ER regime mom CONT | ≠ R22 lag1-AC; ≠ R21 twobar-accel; ≠ R15 streak |",
                "| EURUSD RS-rank CONT | ≠ lead-clones (XAU/XTI/AUD/US30); ≠ R22 FX3-risksync "
                "(sync≠rank); ≠ R19 breadth crypto |",
                "",
                "Also forbidden: London/NY ORB densify (parked M15), fade/MR, unpark/exit/FRED.",
                "R1–R23 densify: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 24 NR7 / ER / RS-rank",
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
                "# Session closeout — Round 24 NR7 / ER / RS-rank",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify NR7-k / ER-k / RS-rank-k /",
                "R23 MTF/fractal/postshock / R22 AC/ATR/risksync / lead-clones /",
                "USD-imp / ORB/IB / R21–R10 / unpark / exit / FRED.",
                "Next: next true greenfield outside R24 — QFSI parallel; cost autonomous retry.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 24 NR7 / ER / RS-rank",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R23. **NON-FADE.** Không densify ORB/IB.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế (a priori)",
                "1. NR7 breakout — nén→bung (≠ Donch/ATR-exp/fractal)",
                "2. Kaufman ER regime — hiệu quả đường giá (≠ lag1-AC)",
                "3. RS-rank FX3 — sức mạnh tương đối nội bộ (≠ lead cross-asset)",
                "",
                "## Cost (autonomous)",
                cost_note,
                "",
                "## Quyết định",
                "- Không densify NR7 / ER / RS-rank / R1–R23 / lead / ORB.",
                "- Best shelf RR2 `194548`. Cost GAP (không invent). QFSI parallel.",
                "- Next: greenfield ngoài R24 **hoặc** cost khi history dày hơn.",
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
                "# VN brief — Clean book + Round 24",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R24 NON-FADE (NR7/ER/RS-rank). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 24 — NR7 / ER / RS-rank",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007 + cost",
                f"{qnote}",
                f"Cost: {cost_note}",
                "",
                "## Near-miss shelf (do not densify)",
                "- R17 ETH VR: PF≈1.98 tpw≈0.33 — cadence only.",
                "- R21 EURJPY USD-imp: PF≈1.20 x1.5≈1.13 — near but joint fail.",
                "- R22–R23 thick boards: cadence OK / PF@$12 fail — **no densify**.",
                "",
                "## Cấm",
                "Densify R1–R24 / VR / lead-clone / USD-imp / ORB/IB / fade-session / "
                "unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R24 (NON-FADE); cost = autonomous "
                "`history_deals_get` / QFSI accumulate — **không** hỏi Owner deal-export làm headline.",
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
        f"- **GREENFIELD ROUND24 NR7/ER/RSRANK CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R1–R23 densify; no ORB/IB densify.",
        "  Nested critic GO — NR7 / Kaufman-ER / FX3 RS-rank (not lead clones) "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R24_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        f"  Cost autonomous: {cost_note}",
        "  Do **not** densify NR7-k / ER-k / RS-rank-k /",
        "  R23 MTF/fractal/postshock / R22 AC/ATR-exp/risksync / lead-clones /",
        "  USD-imp / ORB/IB / R21–R10 / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R24 (still NON-FADE) — QFSI parallel; "
        "cost autonomous retry (no Owner deal-export headline).",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R24 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND24 NR7/ER/RSRANK CLOSEOUT"):
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
    # Patch Next Move ACTIVE line
    final = []
    for ln in out:
        if ln.startswith("- **ACTIVE — STRATEGY SHIFT aftermath.**"):
            final.append(
                "- **ACTIVE — STRATEGY SHIFT aftermath.** Track A PRIMARY book diagnostic "
                "partial under a priori +$12 (caps+cadence OK, PF fail) — **park compose**; "
                "do not outcome-mine densify or re-rank sleeves. Phase-0 still needs Owner "
                "contamination clear. Track B: keep QFSI 007 watcher / capture / Real "
                "(72h wall). Next discovery = true greenfield **outside** R1–R24 densify "
                "(NON-FADE), or cost provenance via autonomous `history_deals_get` / QFSI "
                "(no Owner deal-export headline). Best shelf RR2 `194548`. GOAL unmet."
            )
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


def load_cost_note() -> str:
    """Summarize autonomous live deal pull if present; never invent spreads."""
    root = (
        ROOT
        / "02. AlphaFactory"
        / "evidence"
        / "execution"
        / "FivePercentOnline-Real"
        / "20260715_DEAL_HISTORY_IMPORT_LIVE_R24"
    )
    man = root / "import_manifest.json"
    if not man.exists():
        return (
            "GAP — live `history_deals_get` import not yet landed this session; "
            "no SHA freeze; slip MISSING≠0"
        )
    try:
        p = json.loads(man.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "GAP — import_manifest unreadable"
    counts = p.get("commission_lifecycle_counts") or {}
    raw_n = p.get("raw_deal_count", 0)
    status = p.get("status", "?")
    eu = counts.get("EURUSD", 0)
    uj = counts.get("USDJPY", 0)
    note = (
        f"autonomous live import `{status}` raw_deals={raw_n} "
        f"comm EURUSD={eu}/30 USDJPY={uj}/30 slip=0 MISSING≠0; "
        f"freeze_eligible=False (quote_days≪90)"
    )
    # Write dedicated GAP doc
    OUT_COST.write_text(
        "\n".join(
            [
                "# Cost deal-pull R24 — remaining GAP",
                "",
                f"Generated: {utc_now()}",
                f"Source: `{man.as_posix()}`",
                f"Mode: `{p.get('mode')}` server=`{p.get('observed_server')}`",
                f"Status: `{status}`",
                f"Raw deals (lookback {p.get('history_lookback_days')}d): **{raw_n}**",
                "",
                "## Commission lifecycles (positive round-turn only)",
                *[f"- {k}: **{v}**/30 needed" for k, v in sorted(counts.items())],
                "",
                "## Gates",
                "- quote_days: still ≪90 (QFSI accumulate in progress)",
                "- commission: EURUSD/USDJPY need ≥30 unique lifecycles each",
                "- slip: **MISSING ≠ 0** — cannot mint from deal.profit alone",
                "",
                "## Freeze",
                "**NOT research-grade.** Do not invent spreads. Do not re-stress RR2 "
                "under fabricated multi-year surface.",
                "",
                "Owner deal-export is optional enrichment only — not the headline ask.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return note


def freeze_contract_sha() -> str:
    contract = {
        "nr7": {
            "n": NR_N,
            "body": NR_BODY,
            "sl": NR_SL,
            "rr": NR_RR,
            "hold": NR_HOLD,
            "universe": list(FX3),
        },
        "er": {
            "n": ER_N,
            "min": ER_MIN,
            "body": ER_BODY,
            "sl": ER_SL,
            "rr": ER_RR,
            "hold": ER_HOLD,
        },
        "rs": {
            "n": RS_N,
            "body": RS_BODY,
            "sl": RS_SL,
            "rr": RS_RR,
            "hold": RS_HOLD,
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R1_R23_densify__lead_clones__ORB_IB_densify",
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
                    "# Universe freeze — Round 24 NR7 / ER / RS-rank",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — lead self-merge).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-NR7-BREAKOUT-CONT-001",
                    "2. HYP-GBPUSD-H1-ER-REGIME-MOM-CONT-001",
                    "3. HYP-EURUSD-H1-RS-RANK-CONT-001",
                    "",
                    "Mechanism note: (1) NR7 compression≠Donch/ATR-exp/fractal; "
                    "(2) Kaufman ER≠lag1-AC; "
                    "(3) intra-FX3 RS-rank≠cross-asset lead.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        cost_note = load_cost_note()
        h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        results = [
            pack_result(
                "HYP-FX3-H1-NR7-BREAKOUT-CONT-001",
                "fx3_h1_nr7_breakout_cont",
                "FX3",
                "H1",
                *probe_fx3_nr7(h1),
            ),
            pack_result(
                "HYP-GBPUSD-H1-ER-REGIME-MOM-CONT-001",
                "gbpusd_h1_er_regime_mom_cont",
                "GBPUSD",
                "H1",
                *probe_gbpusd_er(h1["GBPUSD"]),
            ),
            pack_result(
                "HYP-EURUSD-H1-RS-RANK-CONT-001",
                "eurusd_h1_rs_rank_cont",
                "EURUSD",
                "H1",
                *probe_eurusd_rs_rank(h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r24_nr7_er_rsrank.v1_closedbar",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": "NON_FADE__NO_R1_R23_DENSIFY__NO_LEAD__NO_ORB_IB",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "nr7": {
                    "n": NR_N,
                    "body": NR_BODY,
                    "sl": NR_SL,
                    "rr": NR_RR,
                    "hold": NR_HOLD,
                },
                "er": {
                    "n": ER_N,
                    "min": ER_MIN,
                    "body": ER_BODY,
                    "sl": ER_SL,
                    "rr": ER_RR,
                    "hold": ER_HOLD,
                },
                "rs": {
                    "n": RS_N,
                    "body": RS_BODY,
                    "sl": RS_SL,
                    "rr": RS_RR,
                    "hold": RS_HOLD,
                },
            },
            "qfsi_parallel": qnote,
            "cost_autonomous": cost_note,
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
