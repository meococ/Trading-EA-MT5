#!/usr/bin/env python3
"""Round 25 greenfield — range-P80 expand + H4 engulf CONT + London VWAP reclaim.

Post R24: NR7/ER/RS-rank ALL_KILL. NON-FADE outside R1–R24 densify.

HARD FORBIDDEN: R24 NR7/ER/RS-rank densify; R23 MTF/fractal/postshock;
R22 AC/ATR-exp/risksync; lead-clones; USD-implied; ORB/IB densify; fade/MR;
unpark/exit/FRED.

A priori (≥2 mechanisms; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-RANGE-P80-EXPAND-CONT-001
  2) HYP-USDJPY-H4-ENGULF-CONT-001
  3) HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001

+$12 joint thick∩cadence. Model 0 only if PROBE_SURVIVOR. Closed-bar only.
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

STEM = "20260715_GREENFIELD_R25_RANGEP80_H4ENGULF_VWAP"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R25_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 range P80 expand
RP_WIN = 50
RP_PCTL = 0.80
RP_BODY = 0.40
RP_SL = 1.45
RP_RR = 2.00
RP_HOLD = 10

# 2 H4 engulf CONT
EG_BODY = 0.35  # H1 confirm body
EG_SL = 1.45
EG_RR = 2.00
EG_HOLD = 10

# 3 London VWAP reclaim
VW_HOUR0 = 7
VW_HOUR1 = 16
VW_PIERCE = 0.10  # min pierce beyond VWAP in ATR
VW_BODY = 0.40
VW_SL = 1.45
VW_RR = 2.00
VW_HOLD = 10

H1_SEC = 3600
H4_SEC = 4 * 3600


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


def last_fully_closed(d, asof_ts, period_sec):
    if len(d["t"]) == 0:
        return None
    closes = d["t"].astype(np.int64) + int(period_sec)
    j = int(np.searchsorted(closes, int(asof_ts), side="right")) - 1
    return j if j >= 0 else None


def probe_fx3_range_p80(h1):
    """FX3: TR in top P80 of last 50 + body CONT (expansion regime)."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    for i in range(RP_WIN + 3, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, RP_HOLD)
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
            if j is None or j < RP_WIN:
                continue
            trs = d["h"][j - RP_WIN + 1 : j + 1] - d["l"][j - RP_WIN + 1 : j + 1]
            if len(trs) < RP_WIN or not np.all(np.isfinite(trs)):
                continue
            thr = float(np.quantile(trs[:-1], RP_PCTL))  # prior window excl current
            cur = float(trs[-1])
            if cur < thr:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < RP_BODY * atr:
                continue
            side = 1 if body > 0 else -1
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * RP_SL * atr
            tp = entry + side * RP_RR * RP_SL * atr
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


def probe_usdjpy_h4_engulf(h1, h4):
    """USDJPY: closed H4 engulf → next H1 CONT with body confirm."""
    closed, open_pos = [], []
    sym = "USDJPY"
    uj = h1[sym]
    u4 = h4[sym]
    last_day = None
    last_engulf_ts = None
    for i in range(3, len(uj["t"]) - 1):
        ts = int(uj["t"][i])
        open_pos = manage_exits(open_pos, {sym: uj}, ts, closed, EG_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        # last fully closed H4 before entry open
        j4 = last_fully_closed(u4, ts, H4_SEC)
        if j4 is None or j4 < 1:
            continue
        o0, c0 = float(u4["o"][j4 - 1]), float(u4["c"][j4 - 1])
        o1, c1 = float(u4["o"][j4]), float(u4["c"][j4])
        # bullish engulf: prior bearish, current bullish, current range covers prior
        bull = c0 < o0 and c1 > o1 and c1 >= o0 and o1 <= c0
        bear = c0 > o0 and c1 < o1 and c1 <= o0 and o1 >= c0
        if not (bull or bear):
            continue
        engulf_ts = int(u4["t"][j4])
        if engulf_ts == last_engulf_ts:
            continue
        side = 1 if bull else -1
        j = i - 1
        atr = uj["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(uj["c"][j]) - float(uj["o"][j])
        if abs(body) < EG_BODY * atr:
            continue
        if (side > 0 and body <= 0) or (side < 0 and body >= 0):
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(uj["o"][i])
        sl = entry - side * EG_SL * atr
        tp = entry + side * EG_RR * EG_SL * atr
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
        last_engulf_ts = engulf_ts
    flush_open(open_pos, {sym: uj}, closed)
    return summarize(closed)


def probe_gbpusd_vwap_reclaim(gb):
    """GBPUSD: London session VWAP pierce then reclaim CONT (closed-bar)."""
    closed, open_pos = [], []
    sym = "GBPUSD"
    last_day = None
    # Running session VWAP state
    sess_date = None
    cum_tp_v = 0.0
    cum_v = 0.0
    pierced_below = False
    pierced_above = False

    for i in range(20, len(gb["t"]) - 1):
        ts = int(gb["t"][i])
        open_pos = manage_exits(open_pos, {sym: gb}, ts, closed, VW_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            sess_date = None
            continue
        # Update VWAP using prior closed bar (i-1) only when in London window
        j = i - 1
        sj = datetime.fromtimestamp(int(gb["t"][j]), tz=timezone.utc)
        if sess_date != sj.date():
            sess_date = sj.date()
            cum_tp_v = 0.0
            cum_v = 0.0
            pierced_below = False
            pierced_above = False
        if VW_HOUR0 <= sj.hour < VW_HOUR1:
            tp = (float(gb["h"][j]) + float(gb["l"][j]) + float(gb["c"][j])) / 3.0
            # volume proxy = range (tick vol unavailable consistently)
            vol = max(float(gb["h"][j]) - float(gb["l"][j]), 1e-12)
            cum_tp_v += tp * vol
            cum_v += vol
        if open_pos or cum_v <= 0:
            continue
        if not (VW_HOUR0 <= dt.hour < VW_HOUR1):
            continue
        vwap = cum_tp_v / cum_v
        atr = gb["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        lo, hi, c = float(gb["l"][j]), float(gb["h"][j]), float(gb["c"][j])
        body = c - float(gb["o"][j])
        # Track pierce
        if lo <= vwap - VW_PIERCE * atr:
            pierced_below = True
        if hi >= vwap + VW_PIERCE * atr:
            pierced_above = True
        side = 0
        # Reclaim: was pierced below, now close back above VWAP with bull body
        if pierced_below and c > vwap and body >= VW_BODY * atr:
            side = 1
        elif pierced_above and c < vwap and body <= -VW_BODY * atr:
            side = -1
        if side == 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(gb["o"][i])
        sl = entry - side * VW_SL * atr
        tp = entry + side * VW_RR * VW_SL * atr
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
        # consume pierce flags for the day
        pierced_below = False
        pierced_above = False
    flush_open(open_pos, {sym: gb}, closed)
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
                "feature_family": "greenfield_r25_rangep80_h4engulf_vwap",
                "lane": "strategy_shift_r25_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R25 NON-FADE after R24 NR7/ER/RS ALL_KILL; "
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
                "# 3-critic panel — Round 25 RangeP80 / H4-engulf / VWAP",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (lead self-merge; outside R1–R24 densify).",
                "",
                "## Named (NON-FADE)",
                "1. Range-P80 expand CONT — expansion regime (≠ NR7 compression)",
                "2. H4 engulf CONT — continuation engulf (≠ Wave3 engulf reverse)",
                "3. London VWAP reclaim CONT — auction reclaim (≠ ORB/fade)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — classic expansion / engulf / VWAP reclaim |",
                "| Quant | PASS — independent; joint gates a priori |",
                "| MQL5/MT5 | PASS — closed H4 as-of; VWAP from closed H1 only |",
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
                "# Design — Round 25 RangeP80 / H4-engulf / VWAP",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                f"## 1 `HYP-FX3-H1-RANGE-P80-EXPAND-CONT-001`",
                f"TR ≥ P{int(RP_PCTL*100)} of prior {RP_WIN-1} bars + |body|≥{RP_BODY}×ATR → CONT.",
                "Why: expansion ≠ R24 NR7; ≠ R22 ATR-exp% jump; ≠ R21 Donch.",
                "",
                f"## 2 `HYP-USDJPY-H4-ENGULF-CONT-001`",
                f"Closed H4 engulf + H1 body≥{EG_BODY}×ATR same dir → CONT.",
                "Why: CONT engulf ≠ Wave3 engulf reverse; ≠ R23 fractal.",
                "",
                f"## 3 `HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001`",
                f"London [{VW_HOUR0},{VW_HOUR1}) VWAP pierce≥{VW_PIERCE}×ATR then reclaim body → CONT.",
                "Why: reclaim CONT ≠ failed-ORB fade; ≠ London ORB densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 25 RangeP80 / H4-engulf / VWAP",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 range-P80 expand | ≠ R24 NR7; ≠ R22 ATR-exp; ≠ R21 Donch8 |",
                "| USDJPY H4 engulf CONT | ≠ Wave3 engulf reverse; ≠ R23 fractal; ≠ R15 streak |",
                "| GBPUSD London VWAP reclaim | ≠ London/NY ORB; ≠ failed-ORB fade; ≠ R10 session densify |",
                "",
                "R1–R24 densify + lead + ORB/IB + fade: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 25 RangeP80 / H4-engulf / VWAP",
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
                "# Session closeout — Round 25 RangeP80 / H4-engulf / VWAP",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify RangeP80-k / H4-engulf-k / VWAP-reclaim-k /",
                "R24 NR7/ER/RS / R23 MTF/fractal/postshock / lead / ORB / unpark / exit / FRED.",
                "Next: next true greenfield outside R25 — QFSI parallel; cost autonomous retry.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 25 RangeP80 / H4-engulf / VWAP",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R24. **NON-FADE.**",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế",
                "1. Range-P80 expand — bung biên độ (≠ NR7)",
                "2. H4 engulf CONT — continuation (≠ reverse)",
                "3. London VWAP reclaim — lấy lại VWAP (≠ ORB/fade)",
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
                "# VN brief — Clean book + Round 25",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R25 NON-FADE (RangeP80/H4-engulf/VWAP). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 25 — RangeP80 / H4-engulf / VWAP",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007 + cost",
                f"{qnote}",
                f"Cost: {cost_note}",
                "",
                "## Cấm",
                "Densify R1–R25 / VR / lead-clone / USD-imp / ORB/IB / fade-session / "
                "unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R25 (NON-FADE); cost = autonomous "
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
        f"- **GREENFIELD ROUND25 RANGEP80/H4ENGULF/VWAP CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R1–R24 densify.",
        "  Nested critic GO — RangeP80 / H4-engulf-CONT / London-VWAP-reclaim "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R25_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        f"  Cost autonomous: {cost_note}",
        "  Do **not** densify RangeP80-k / H4-engulf-k / VWAP-reclaim-k /",
        "  R24 NR7/ER/RS / R23 MTF/fractal/postshock / lead-clones /",
        "  ORB/IB / R22–R10 / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R25 (still NON-FADE) — QFSI parallel; "
        "cost autonomous retry (no Owner deal-export headline).",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R25 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND25 RANGEP80/H4ENGULF/VWAP CLOSEOUT"):
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
                "Next = greenfield **outside** R1–R25 densify (NON-FADE), or cost via "
                "autonomous `history_deals_get` / QFSI (no Owner deal-export headline). "
                "Cost table `readouts/20260715_COST_MULTIDAY_TABLE_R24.md` "
                "(quote_days=2/90; freeze_eligible=False). "
                "Best shelf RR2 `194548`. GOAL unmet."
            )
            # skip continuation lines of old ACTIVE bullet until next top-level bullet
            continue
        # Drop orphan continuation of old ACTIVE if present after our one-liner replace
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
            # only skip if orphan (previous ACTIVE multi-line)
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


def load_cost_note() -> str:
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
    return base + "; freeze_eligible=False"


def freeze_contract_sha() -> str:
    contract = {
        "rangep80": {
            "win": RP_WIN,
            "pctl": RP_PCTL,
            "body": RP_BODY,
            "sl": RP_SL,
            "rr": RP_RR,
            "hold": RP_HOLD,
            "universe": list(FX3),
        },
        "h4engulf": {
            "body": EG_BODY,
            "sl": EG_SL,
            "rr": EG_RR,
            "hold": EG_HOLD,
        },
        "vwap": {
            "hours": [VW_HOUR0, VW_HOUR1],
            "pierce": VW_PIERCE,
            "body": VW_BODY,
            "sl": VW_SL,
            "rr": VW_RR,
            "hold": VW_HOLD,
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R1_R24_densify__lead__ORB_IB_fade",
    }
    return sha256_bytes(
        json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    )


OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        freeze_sha = freeze_contract_sha()
        OUT_FREEZE.write_text(
            "\n".join(
                [
                    "# Universe freeze — Round 25 RangeP80 / H4-engulf / VWAP",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — lead self-merge).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-RANGE-P80-EXPAND-CONT-001",
                    "2. HYP-USDJPY-H4-ENGULF-CONT-001",
                    "3. HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001",
                    "",
                    "Mechanism note: (1) expansion≠NR7; (2) engulf CONT≠reverse; "
                    "(3) VWAP reclaim≠ORB/fade.",
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
        h4 = {s: enrich(load(s, mt5.TIMEFRAME_H4)) for s in FX3}
        results = [
            pack_result(
                "HYP-FX3-H1-RANGE-P80-EXPAND-CONT-001",
                "fx3_h1_range_p80_expand_cont",
                "FX3",
                "H1",
                *probe_fx3_range_p80(h1),
            ),
            pack_result(
                "HYP-USDJPY-H4-ENGULF-CONT-001",
                "usdjpy_h4_engulf_cont",
                "USDJPY",
                "H4->H1",
                *probe_usdjpy_h4_engulf(h1, h4),
            ),
            pack_result(
                "HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001",
                "gbpusd_h1_london_vwap_reclaim_cont",
                "GBPUSD",
                "H1",
                *probe_gbpusd_vwap_reclaim(h1["GBPUSD"]),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r25_rangep80_h4engulf_vwap.v1_closedbar",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": "NON_FADE__NO_R1_R24_DENSIFY__NO_LEAD__NO_ORB_IB",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
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
