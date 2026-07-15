#!/usr/bin/env python3
"""Round 16 greenfield — NON-FADE only; outside R10–R15 densify.

HARD FORBIDDEN: streak/BTC-ROC/XAG-ROC; gap/TV-imb/NAS-ROC; NFP/CUSUM/XAU-ROC;
EMA/Fri/RS; London-fix/WO/closeloc; Tokyo/London/NY session; fade/MR;
R1–R9 residual/corr/Parkinson/ON-ratio; unpark/exit/FRED; WTI/ECB densify;
near-miss ROC-k thick clones.

Broker adapt: panel DE40 missing → US30 D1 HL-break CONT (≠ ROC thick).

A priori (nested critic GO + lead self-merge):
  1) HYP-US30-H4-D1-HL-BREAK-CONT-001
  2) HYP-USDJPY-H1-CPI-IMPULSE-CONT-001
  3) HYP-EURJPY-H1-US30-LEAD-CONT-001

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

STEM = "20260715_GREENFIELD_R16_HLBREAK_CPI_US30LEAD"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R16_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# 1 US30 D1 HL-break → H4 CONT
HL_BUF_ATR = 0.15
HL_SL = 2.00
HL_RR = 2.50
HL_HOLD = 20

# 2 USDJPY CPI impulse CONT — frozen BLS-style release calendar (a priori)
CPI_BODY_ATR = 1.00
CPI_SL = 1.50
CPI_RR = 2.00
CPI_HOLD = 8
CPI_EVENT_HOURS = (12, 13)  # 8:30 ET ≈ 12:30/13:30 UTC across DST
# Frozen public CPI release days (YYYY, M, D) — not mined from readout
CPI_DATES = {
    # 2021
    (2021, 1, 13), (2021, 2, 10), (2021, 3, 10), (2021, 4, 13),
    (2021, 5, 12), (2021, 6, 10), (2021, 7, 13), (2021, 8, 11),
    (2021, 9, 14), (2021, 10, 13), (2021, 11, 10), (2021, 12, 10),
    # 2022
    (2022, 1, 12), (2022, 2, 10), (2022, 3, 10), (2022, 4, 12),
    (2022, 5, 11), (2022, 6, 10), (2022, 7, 13), (2022, 8, 10),
    (2022, 9, 13), (2022, 10, 13), (2022, 11, 10), (2022, 12, 13),
    # 2023
    (2023, 1, 12), (2023, 2, 14), (2023, 3, 14), (2023, 4, 12),
    (2023, 5, 10), (2023, 6, 13), (2023, 7, 12), (2023, 8, 10),
    (2023, 9, 13), (2023, 10, 12), (2023, 11, 14), (2023, 12, 12),
    # 2024
    (2024, 1, 11), (2024, 2, 13), (2024, 3, 12), (2024, 4, 10),
    (2024, 5, 15), (2024, 6, 12), (2024, 7, 11), (2024, 8, 14),
    (2024, 9, 11), (2024, 10, 10), (2024, 11, 13), (2024, 12, 11),
    # 2025
    (2025, 1, 15), (2025, 2, 12), (2025, 3, 12), (2025, 4, 10),
    (2025, 5, 13), (2025, 6, 11), (2025, 7, 15), (2025, 8, 12),
    (2025, 9, 11), (2025, 10, 24), (2025, 11, 13), (2025, 12, 18),
}

# 3 EURJPY ← US30 lead CONT
LEAD_US30_ATR = 0.60
LEAD_EJ_ATR = 0.25
LEAD_LAGS = (0, 1)  # frozen; no search
LEAD_SL = 1.40
LEAD_RR = 2.00
LEAD_HOLD = 10


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


def asof_d1_index(d1_t, ts):
    """Last fully closed D1 bar strictly before H4 bar open ts."""
    j = int(np.searchsorted(d1_t, ts, side="left")) - 1
    return j


def probe_us30_d1_hl_break_cont(d1, h4):
    """Prior D1 HL break on closed H4 → continue thick."""
    closed, open_pos = [], []
    sym = "US30"
    last_sig_day = None
    for i in range(2, len(h4["t"]) - 1):
        ts = int(h4["t"][i])
        open_pos = manage_exits(open_pos, {sym: h4}, ts, closed, HL_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        # Signal on prior closed H4 bar i-1; entry at open of i
        sig_i = i - 1
        sig_ts = int(h4["t"][sig_i])
        j = asof_d1_index(d1["t"], sig_ts)
        if j < 1:
            continue
        # Prior completed D1 = j-1 relative to the D1 containing/as-of sig
        # Use last D1 with end <= sig_ts as completed day j
        d1_atr = d1["atr"][j]
        if not np.isfinite(d1_atr) or d1_atr <= 0:
            continue
        prior_h = float(d1["h"][j])
        prior_l = float(d1["l"][j])
        # Need previous day levels: break of day j high/low using H4 close at sig_i
        # Standard: break prior day's H/L → prior day is j (last closed D1 before sig)
        # Actually prior day HL = day j's H/L; H4 close must exceed that after day j closed.
        # Day j closed at d1["t"][j]+86400 roughly; require sig_ts > d1 day close.
        if sig_ts < int(d1["t"][j]) + 20 * 3600:
            # not yet past typical day settle; require next D1 started
            if j + 1 >= len(d1["t"]) or sig_ts < int(d1["t"][j + 1]):
                # still allow if we're on a later H4 after D1 bar time advanced
                pass
        # Use day j as the reference completed day only if a newer D1 bar exists
        if j + 1 >= len(d1["t"]):
            continue
        if sig_ts < int(d1["t"][j + 1]):
            continue  # D1 day j not fully closed yet at signal bar
        ref_h = float(d1["h"][j])
        ref_l = float(d1["l"][j])
        buf = HL_BUF_ATR * float(d1["atr"][j])
        close = float(h4["c"][sig_i])
        side = 0
        if close >= ref_h + buf:
            side = 1
        elif close <= ref_l - buf:
            side = -1
        if side == 0:
            continue
        day = dt.date()
        if day == last_sig_day:
            continue
        atr = h4["atr"][sig_i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        entry = float(h4["o"][i])
        sl = entry - side * HL_SL * atr
        tp = entry + side * HL_RR * HL_SL * atr
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
        last_sig_day = day
    flush_open(open_pos, {sym: h4}, closed)
    return summarize(closed)


def probe_usdjpy_cpi_impulse_cont(h1):
    closed, open_pos = [], []
    sym = "USDJPY"
    d = h1
    fired = set()
    for i in range(len(d["t"]) - 2):
        ts = int(d["t"][i])
        open_pos = manage_exits(open_pos, {sym: d}, ts, closed, CPI_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        key_day = (dt.year, dt.month, dt.day)
        if key_day not in CPI_DATES:
            continue
        if dt.hour not in CPI_EVENT_HOURS:
            continue
        if key_day in fired:
            continue
        atr = d["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(d["c"][i]) - float(d["o"][i])
        if abs(body) < CPI_BODY_ATR * atr:
            continue
        # Prefer stronger of the two event hours
        best = abs(body)
        for hh in CPI_EVENT_HOURS:
            for k in range(max(0, i - 3), min(len(d["t"]), i + 4)):
                dtk = datetime.fromtimestamp(int(d["t"][k]), tz=timezone.utc)
                if (dtk.year, dtk.month, dtk.day) != key_day or dtk.hour != hh:
                    continue
                atrk = d["atr"][k]
                if not np.isfinite(atrk) or atrk <= 0:
                    continue
                bk = abs(float(d["c"][k]) - float(d["o"][k]))
                if bk > best + 1e-12:
                    best = bk
        if abs(body) + 1e-12 < best:
            continue
        side = 1 if body > 0 else -1
        entry = float(d["o"][i + 1])
        sl = entry - side * CPI_SL * atr
        tp = entry + side * CPI_RR * CPI_SL * atr
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
        fired.add(key_day)
    flush_open(open_pos, {sym: d}, closed)
    return summarize(closed)


def probe_eurjpy_us30_lead_cont(ej, us30):
    """Closed US30 H1 thrust → EURJPY same-sign CONT within frozen lag."""
    closed, open_pos = [], []
    sym = "EURJPY"
    last_day = None
    # Precompute US30 signed thrust flags on closed bars
    us_side = np.zeros(len(us30["t"]), dtype=int)
    for i in range(1, len(us30["t"])):
        atr = us30["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        ret = float(us30["c"][i]) - float(us30["o"][i])
        if abs(ret) >= LEAD_US30_ATR * atr:
            us_side[i] = 1 if ret > 0 else -1

    for i in range(2, len(ej["t"]) - 1):
        ts = int(ej["t"][i])
        open_pos = manage_exits(open_pos, {sym: ej}, ts, closed, LEAD_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        # Signal on closed EJ bar i-1; need US30 lead at i-1-lag
        sig = i - 1
        atr = ej["atr"][sig]
        if not np.isfinite(atr) or atr <= 0:
            continue
        ej_ret = float(ej["c"][sig]) - float(ej["o"][sig])
        if abs(ej_ret) < LEAD_EJ_ATR * atr:
            continue
        ej_side = 1 if ej_ret > 0 else -1
        # Find US30 bar at same timestamp as EJ sig (or earlier)
        u = int(np.searchsorted(us30["t"], int(ej["t"][sig]), side="left"))
        if u >= len(us30["t"]) or int(us30["t"][u]) != int(ej["t"][sig]):
            u = int(np.searchsorted(us30["t"], int(ej["t"][sig]), side="right")) - 1
        if u < 0:
            continue
        matched = False
        for lag in LEAD_LAGS:
            ui = u - lag
            if ui < 0:
                continue
            if int(us_side[ui]) == ej_side and int(us_side[ui]) != 0:
                matched = True
                break
        if not matched:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(ej["o"][i])
        sl = entry - ej_side * LEAD_SL * atr
        tp = entry + ej_side * LEAD_RR * LEAD_SL * atr
        lots = risk_lots(sym, entry, sl)
        open_pos.append(
            {
                "sym": sym,
                "side": ej_side,
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
                "feature_family": "greenfield_r16_hlbreak_cpi_us30lead",
                "lane": "strategy_shift_r16_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": "R16 NON-FADE outside R10–R15 densify; nested critic GO",
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
                "# 3-critic panel — Round 16 HL-break / CPI / US30-lead",
                "",
                "Date: 2026-07-15",
                "Nested: critic Task `cursor-grok-4.5-high-fast` → GO; lead broker-adapt DE40→US30.",
                "",
                "## Named (NON-FADE)",
                "1. `US30_D1_HL_BREAK_H4_CONT` (panel DE40 → broker US30)",
                "2. `USDJPY_CPI_IMPULSE_CONT`",
                "3. `EURJPY_US30_LEAD_CONT`",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — equity structure + rates event + risk-on yen CONT |",
                "| Quant | SOFT — cadence/cost on index; CPI N sparse; lead sync risk |",
                "| MQL5/MT5 | PASS — closed-bar D1 as-of; CPI next open; US30 lead as-of |",
                "",
                "Merge: **GO** offline joint only. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 16 HL-break / CPI / US30-lead",
                "",
                "Date: 2026-07-15",
                "Hard constraint: NON-FADE; outside R10–R15 densify; no ROC-k thick densify.",
                "Broker adapt: DE40 missing → US30.",
                "",
                f"## 1 `HYP-US30-H4-D1-HL-BREAK-CONT-001`",
                f"H4 close beyond prior D1 H/L by ≥{HL_BUF_ATR}×D1 ATR → CONT;",
                f"SL={HL_SL} RR={HL_RR} hold≤{HL_HOLD}; 1/day.",
                "",
                f"## 2 `HYP-USDJPY-H1-CPI-IMPULSE-CONT-001`",
                f"Frozen CPI calendar; hour∈{CPI_EVENT_HOURS} UTC; |body|≥{CPI_BODY_ATR}×ATR;",
                f"CONTINUE; SL={CPI_SL} RR={CPI_RR} hold≤{CPI_HOLD}; 1/event.",
                "",
                f"## 3 `HYP-EURJPY-H1-US30-LEAD-CONT-001`",
                f"US30 |body|≥{LEAD_US30_ATR}×ATR leads EURJPY same-sign |body|≥{LEAD_EJ_ATR}×ATR;",
                f"lag∈{LEAD_LAGS}; SL={LEAD_SL} RR={LEAD_RR} hold≤{LEAD_HOLD}; 1/day.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 16 HL-break / CPI / US30-lead",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| US30 D1 HL-break CONT | ≠ NAS/XAU/BTC/XAG ROC-k thick; ≠ W1 HL unpark; ≠ ORB/NR7/VWAP/SB |",
                "| USDJPY CPI impulse CONT | ≠ NFP first-Friday densify; ≠ FRED/ECB/Brent/AONIA densify; ≠ London-fix |",
                "| EURJPY←US30 lead CONT | ≠ NAS→USDJPY β fade; ≠ EURJPY~USDJPY resid fade; ≠ GBP-EUR RS; ≠ ROC thick |",
                "",
                "R10–R15 densify boards: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 16 HL-break / CPI / US30-lead",
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
                "# Session closeout — Round 16 HL-break / CPI / US30-lead",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify US30 break-k / CPI body-k / US30 lead-lag / R10–R15.",
                "Next: next true greenfield outside R16 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 16 HL-break / CPI / US30-lead",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R15. **NON-FADE only.** Broker: DE40→US30.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify US30 break-k / CPI body-k / US30 lead-lag / R10–R15.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R16 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 16 (post R15)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R16 NON-FADE. GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 16 — HL-break / CPI / US30-lead",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "",
                "## Cấm",
                "Densify R1–R16 / fade-session / unpark / exit / FRED / Phase-0 ceremony.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R16 (NON-FADE); cost khi Owner drop deal-export.",
                "Best shelf RR2 `194548`. GOAL unmet.",
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
        f"- **GREENFIELD ROUND16 HLBREAK/CPI/US30LEAD CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R15 densify + R1–R9/unpark/exit/FRED.",
        "  Nested critic GO → lead broker-adapt DE40→US30; self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R16_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify US30 break-k / CPI body-k / US30 lead-lag /",
        "  R15 streak/BTC/XAG / R14 gap/TV/NAS / R13 NFP/CUSUM/XAU / R12–R10 / R1–R9 /",
        "  unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R16 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R16 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND16 HLBREAK/CPI/US30LEAD CLOSEOUT"):
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
        us30_d1 = enrich(load("US30", mt5.TIMEFRAME_D1))
        us30_h4 = enrich(load("US30", mt5.TIMEFRAME_H4))
        us30_h1 = enrich(load("US30", mt5.TIMEFRAME_H1))
        usdjpy_h1 = enrich(load("USDJPY", mt5.TIMEFRAME_H1))
        eurjpy_h1 = enrich(load("EURJPY", mt5.TIMEFRAME_H1))
        results = [
            pack_result(
                "HYP-US30-H4-D1-HL-BREAK-CONT-001",
                "us30_h4_d1_hl_break_cont",
                "US30",
                "H4",
                *probe_us30_d1_hl_break_cont(us30_d1, us30_h4),
            ),
            pack_result(
                "HYP-USDJPY-H1-CPI-IMPULSE-CONT-001",
                "usdjpy_h1_cpi_impulse_cont",
                "USDJPY",
                "H1",
                *probe_usdjpy_cpi_impulse_cont(usdjpy_h1),
            ),
            pack_result(
                "HYP-EURJPY-H1-US30-LEAD-CONT-001",
                "eurjpy_h1_us30_lead_cont",
                "EURJPY",
                "H1",
                *probe_eurjpy_us30_lead_cont(eurjpy_h1, us30_h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r16_hlbreak_cpi_us30lead.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "hard_constraint": "NON_FADE__NO_R10_R15_DENSIFY",
            "broker_adapt": "panel_DE40_missing__US30_HL_BREAK",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "hl_break": {
                    "buf_atr": HL_BUF_ATR,
                    "sl": HL_SL,
                    "rr": HL_RR,
                    "hold": HL_HOLD,
                },
                "cpi": {
                    "body_atr": CPI_BODY_ATR,
                    "sl": CPI_SL,
                    "rr": CPI_RR,
                    "hold": CPI_HOLD,
                    "event_hours_utc": list(CPI_EVENT_HOURS),
                    "n_frozen_dates": len(CPI_DATES),
                },
                "lead": {
                    "us30_atr": LEAD_US30_ATR,
                    "ej_atr": LEAD_EJ_ATR,
                    "lags": list(LEAD_LAGS),
                    "sl": LEAD_SL,
                    "rr": LEAD_RR,
                    "hold": LEAD_HOLD,
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
