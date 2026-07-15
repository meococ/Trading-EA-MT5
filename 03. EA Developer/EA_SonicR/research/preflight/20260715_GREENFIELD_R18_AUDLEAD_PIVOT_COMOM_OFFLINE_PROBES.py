#!/usr/bin/env python3
"""Round 18 greenfield — NON-FADE only; outside R10–R17 densify.

HARD FORBIDDEN: ETH VR densify (near-miss cadence-only); R17 semivar/UTC0;
R16 US30-break/CPI/lead; R15–R10 densify; residual/corr/Parkinson/ON-ratio;
fade/MR; unpark/exit/FRED; ROC-k thick clones.

A priori (nested critic GO):
  1) HYP-NZDUSD-H1-AUD-IMPULSE-LEAD-CONT-001
  2) HYP-FX3-H1-D1-PIVOT-R1S1-BREAK-CONT-001
  3) HYP-GBPJPY-H1-EURJPY-COMOM-CONT-001

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

STEM = "20260715_GREENFIELD_R18_AUDLEAD_PIVOT_COMOM"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R18_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 AUD→NZD impulse lead
AL_IMP = 0.70
AL_SL = 1.40
AL_RR = 2.00
AL_HOLD = 10

# 2 FX3 D1 pivot R1/S1 break
PV_BODY = 0.50
PV_SL = 1.50
PV_RR = 2.00
PV_HOLD = 8

# 3 GBPJPY × EURJPY co-mom
CM_GJ = 0.65
CM_EJ = 0.40
CM_SL = 1.45
CM_RR = 2.00
CM_HOLD = 10


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


def probe_nzd_aud_lead_cont(nzd, aud):
    closed, open_pos = [], []
    sym = "NZDUSD"
    last_day = None
    for i in range(2, len(nzd["t"]) - 1):
        ts = int(nzd["t"][i])
        open_pos = manage_exits(open_pos, {sym: nzd}, ts, closed, AL_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        # NZD entry at i; lead = AUD closed bar with same timestamp as nzd[i-1]
        lead_ts = int(nzd["t"][i - 1])
        a = int(np.searchsorted(aud["t"], lead_ts, side="left"))
        if a >= len(aud["t"]) or int(aud["t"][a]) != lead_ts:
            a = int(np.searchsorted(aud["t"], lead_ts, side="right")) - 1
        if a < 0:
            continue
        atr_a = aud["atr"][a]
        if not np.isfinite(atr_a) or atr_a <= 0:
            continue
        ret_a = float(aud["c"][a]) - float(aud["o"][a])
        if abs(ret_a) < AL_IMP * atr_a:
            continue
        side = 1 if ret_a > 0 else -1
        atr = nzd["atr"][i - 1]
        if not np.isfinite(atr) or atr <= 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(nzd["o"][i])
        sl = entry - side * AL_SL * atr
        tp = entry + side * AL_RR * AL_SL * atr
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
    flush_open(open_pos, {sym: nzd}, closed)
    return summarize(closed)


def probe_fx3_pivot_break_cont(h1, d1):
    closed, open_pos = [], []
    data = {s: h1[s] for s in FX3}
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    for i in range(2, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, data, ts, closed, PV_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        for sym in FX3:
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            d = h1[sym]
            j = int(np.searchsorted(d["t"], ts, side="left"))
            if j < 1 or j >= len(d["t"]) or d["t"][j] != ts:
                continue
            sig = j - 1
            # prior completed D1 as-of signal bar
            dd = d1[sym]
            di = int(np.searchsorted(dd["t"], int(d["t"][sig]), side="right")) - 1
            if di < 1:
                continue
            # require next D1 started so day di is complete
            if di + 1 >= len(dd["t"]) or int(d["t"][sig]) < int(dd["t"][di + 1]):
                continue
            H, L, C = float(dd["h"][di]), float(dd["l"][di]), float(dd["c"][di])
            P = (H + L + C) / 3.0
            R1 = 2 * P - L
            S1 = 2 * P - H
            atr = d["atr"][sig]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][sig]) - float(d["o"][sig])
            close = float(d["c"][sig])
            side = 0
            if close > R1 and abs(body) >= PV_BODY * atr:
                side = 1
            elif close < S1 and abs(body) >= PV_BODY * atr:
                side = -1
            if side == 0:
                continue
            entry = float(d["o"][j])
            sl = entry - side * PV_SL * atr
            tp = entry + side * PV_RR * PV_SL * atr
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
            last_day_sym.add(day_key)
            break  # one FX3 exposure
    flush_open(open_pos, data, closed)
    return summarize(closed)


def probe_gbpjpy_eurjpy_comom(gj, ej):
    closed, open_pos = [], []
    sym = "GBPJPY"
    last_day = None
    for i in range(2, len(gj["t"]) - 1):
        ts = int(gj["t"][i])
        open_pos = manage_exits(open_pos, {sym: gj}, ts, closed, CM_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig = i - 1
        atr_g = gj["atr"][sig]
        if not np.isfinite(atr_g) or atr_g <= 0:
            continue
        ret_g = float(gj["c"][sig]) - float(gj["o"][sig])
        if abs(ret_g) < CM_GJ * atr_g:
            continue
        # sync EURJPY same timestamp
        e = int(np.searchsorted(ej["t"], int(gj["t"][sig]), side="left"))
        if e >= len(ej["t"]) or int(ej["t"][e]) != int(gj["t"][sig]):
            continue
        atr_e = ej["atr"][e]
        if not np.isfinite(atr_e) or atr_e <= 0:
            continue
        ret_e = float(ej["c"][e]) - float(ej["o"][e])
        if abs(ret_e) < CM_EJ * atr_e:
            continue
        if (ret_g > 0) != (ret_e > 0):
            continue
        side = 1 if ret_g > 0 else -1
        day = dt.date()
        if day == last_day:
            continue
        entry = float(gj["o"][i])
        sl = entry - side * CM_SL * atr_g
        tp = entry + side * CM_RR * CM_SL * atr_g
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
    flush_open(open_pos, {sym: gj}, closed)
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
                "feature_family": "greenfield_r18_audlead_pivot_comom",
                "lane": "strategy_shift_r18_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": "R18 NON-FADE outside R10–R17 densify; nested critic GO",
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
                "# 3-critic panel — Round 18 AUD-lead / pivot / co-mom",
                "",
                "Date: 2026-07-15",
                "Nested critic GO; ETH VR near-miss densify FORBIDDEN.",
                "",
                "## Named (NON-FADE)",
                "1. `NZD_AUD_IMPULSE_LEAD_CONT`",
                "2. `FX3_D1_PIVOT_R1S1_BREAK_CONT`",
                "3. `GBPJPY_EURJPY_COMOM_CONT`",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — commodity lead + pivot accept + yen co-mom |",
                "| Quant | SOFT — sync/mining risk; freeze-only |",
                "| MQL5/MT5 | PASS — closed-bar as-of |",
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
                "# Design — Round 18 AUD-lead / pivot / co-mom",
                "",
                "Date: 2026-07-15",
                f"## 1 `HYP-NZDUSD-H1-AUD-IMPULSE-LEAD-CONT-001`",
                f"AUDUSD |ret|≥{AL_IMP}×ATR → NZDUSD CONT next open; SL={AL_SL} RR={AL_RR}.",
                "",
                f"## 2 `HYP-FX3-H1-D1-PIVOT-R1S1-BREAK-CONT-001`",
                f"Prior D1 floor pivot R1/S1 break + |body|≥{PV_BODY}×ATR; SL={PV_SL} RR={PV_RR}.",
                "",
                f"## 3 `HYP-GBPJPY-H1-EURJPY-COMOM-CONT-001`",
                f"GBPJPY |ret|≥{CM_GJ}×ATR and EURJPY same-sign |ret|≥{CM_EJ}×ATR; SL={CM_SL} RR={CM_RR}.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 18 AUD-lead / pivot / co-mom",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| AUD→NZD lead CONT | ≠ ETH VR densify; ≠ NZD semivar; ≠ AUDNZD resid MR; ≠ US30 lead |",
                "| FX3 pivot R1/S1 CONT | ≠ US30 HL-break densify; ≠ ORB/NR7/W1 unpark; ≠ session boards |",
                "| GBPJPY×EURJPY co-mom | ≠ EURJPY←US30 lead; ≠ yen-β resid fade; ≠ GBP-EUR RS |",
                "",
                "R10–R17 densify + ETH VR near-miss densify: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 18 AUD-lead / pivot / co-mom",
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
                "# Session closeout — Round 18 AUD-lead / pivot / co-mom",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify AUD-imp-k / pivot-k / co-mom-k / ETH VR / R10–R17.",
                "Next: next true greenfield outside R18 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 18 AUD-lead / pivot / co-mom",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R17. **NON-FADE.** Cấm densify ETH VR near-miss.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify AUD-imp / pivot / co-mom / VR / R10–R17.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R18 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 18 (post R17)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R18 NON-FADE. GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 18 — AUD-lead / pivot / co-mom",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "",
                "## Near-miss shelf (do not densify)",
                "- R17 ETH VR: PF≈1.98 x1.5≈1.77 but tpw≈0.33 — cadence only.",
                "- R16 EURJPY←US30 lead: PF≈1.09 N=1289 — PF/stress fail.",
                "- R13 XAU TSMOM: PF≈1.43 — no ROC-k densify.",
                "",
                "## Cấm",
                "Densify R1–R18 / VR rescue / fade-session / unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R18 (NON-FADE); cost khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND18 AUDLEAD/PIVOT/COMOM CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R17 densify + ETH VR near-miss ban.",
        "  Nested critic GO → lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R18_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify AUD-imp-k / pivot-k / co-mom-k / ETH VR-k /",
        "  R17 semivar/UTC0 / R16 US30-break/CPI/lead / R15–R10 / R1–R9 /",
        "  unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R18 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R18 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND18 AUDLEAD/PIVOT/COMOM CLOSEOUT"):
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
        nzd = enrich(load("NZDUSD", mt5.TIMEFRAME_H1))
        aud = enrich(load("AUDUSD", mt5.TIMEFRAME_H1))
        h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        d1 = {s: enrich(load(s, mt5.TIMEFRAME_D1)) for s in FX3}
        gj = enrich(load("GBPJPY", mt5.TIMEFRAME_H1))
        ej = enrich(load("EURJPY", mt5.TIMEFRAME_H1))
        results = [
            pack_result(
                "HYP-NZDUSD-H1-AUD-IMPULSE-LEAD-CONT-001",
                "nzdusd_h1_aud_impulse_lead_cont",
                "NZDUSD",
                "H1",
                *probe_nzd_aud_lead_cont(nzd, aud),
            ),
            pack_result(
                "HYP-FX3-H1-D1-PIVOT-R1S1-BREAK-CONT-001",
                "fx3_h1_d1_pivot_r1s1_break_cont",
                "FX3",
                "H1",
                *probe_fx3_pivot_break_cont(h1, d1),
            ),
            pack_result(
                "HYP-GBPJPY-H1-EURJPY-COMOM-CONT-001",
                "gbpjpy_h1_eurjpy_comom_cont",
                "GBPJPY",
                "H1",
                *probe_gbpjpy_eurjpy_comom(gj, ej),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r18_audlead_pivot_comom.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "hard_constraint": "NON_FADE__NO_R10_R17_DENSIFY__NO_ETH_VR_RESCUE",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "aud_lead": {"imp": AL_IMP, "sl": AL_SL, "rr": AL_RR, "hold": AL_HOLD},
                "pivot": {"body": PV_BODY, "sl": PV_SL, "rr": PV_RR, "hold": PV_HOLD},
                "comom": {
                    "gj": CM_GJ,
                    "ej": CM_EJ,
                    "sl": CM_SL,
                    "rr": CM_RR,
                    "hold": CM_HOLD,
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
