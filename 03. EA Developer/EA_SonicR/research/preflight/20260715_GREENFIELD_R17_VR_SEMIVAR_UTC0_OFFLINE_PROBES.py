#!/usr/bin/env python3
"""Round 17 greenfield — NON-FADE only; outside R10–R16 densify.

HARD FORBIDDEN: R16 US30 break-k / CPI body-k / US30 lead-lag near-miss;
R15 streak/BTC/XAG ROC; R14 gap/TV/NAS; R13 NFP/CUSUM/XAU; R12–R10;
R1–R9 residual/corr/Parkinson/ON-ratio; fade/MR; unpark/exit/FRED;
ROC-k thick clones.

A priori (nested critic GO):
  1) HYP-ETHUSD-H4-VARIANCE-RATIO-MOM-CONT-001
  2) HYP-NZDUSD-H1-SIGNED-SEMIVAR-CONT-001
  3) HYP-ETHUSD-H1-UTC0-OPEN-DRIVE-CONT-001

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

STEM = "20260715_GREENFIELD_R17_VR_SEMIVAR_UTC0"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R17_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# 1 ETH H4 VR mom CONT
VR_LB = 48
VR_Q = 2
VR_MIN = 1.20
VR_DIR_LB = 8
VR_SL = 1.50
VR_RR = 2.00
VR_HOLD = 10

# 2 NZD H1 signed semivar CONT
SV_LB = 24
SV_SHARE = 0.62
SV_SL = 1.40
SV_RR = 2.00
SV_HOLD = 12

# 3 ETH H1 UTC0 open drive CONT
U0_BODY_ATR = 0.80
U0_SL = 1.50
U0_RR = 2.00
U0_HOLD = 8


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


def variance_ratio(logret_window, q=2):
    """Lo-MacKinlay VR(q) on a 1d array of log returns (length = lb)."""
    x = np.asarray(logret_window, dtype=float)
    n = len(x)
    if n < q + 2:
        return np.nan
    mu = x.mean()
    var1 = np.sum((x - mu) ** 2) / (n - 1)
    if var1 <= 0:
        return np.nan
    # q-period overlapping returns
    nq = n - q + 1
    rq = np.array([x[i : i + q].sum() for i in range(nq)])
    varq = np.sum((rq - q * mu) ** 2) / (nq - 1) if nq > 1 else np.nan
    if not np.isfinite(varq) or varq <= 0:
        return np.nan
    return (varq / q) / var1


def probe_eth_vr_mom_cont(h4):
    closed, open_pos = [], []
    sym = "ETHUSD"
    c = h4["c"]
    logret = np.zeros(len(c))
    logret[1:] = np.log(c[1:] / c[:-1])
    last_day = None
    for i in range(VR_LB + VR_DIR_LB + 2, len(h4["t"]) - 1):
        ts = int(h4["t"][i])
        open_pos = manage_exits(open_pos, {sym: h4}, ts, closed, VR_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if open_pos:
            continue
        # Signal on closed bar i-1
        sig = i - 1
        win = logret[sig - VR_LB + 1 : sig + 1]
        vr = variance_ratio(win, VR_Q)
        if not np.isfinite(vr) or vr <= VR_MIN:
            continue
        direction = float(np.sum(logret[sig - VR_DIR_LB + 1 : sig + 1]))
        if direction == 0:
            continue
        side = 1 if direction > 0 else -1
        atr = h4["atr"][sig]
        if not np.isfinite(atr) or atr <= 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(h4["o"][i])
        sl = entry - side * VR_SL * atr
        tp = entry + side * VR_RR * VR_SL * atr
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
    flush_open(open_pos, {sym: h4}, closed)
    return summarize(closed)


def probe_nzd_signed_semivar_cont(h1):
    closed, open_pos = [], []
    sym = "NZDUSD"
    last_day = None
    for i in range(SV_LB + 2, len(h1["t"]) - 1):
        ts = int(h1["t"][i])
        open_pos = manage_exits(open_pos, {sym: h1}, ts, closed, SV_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig = i - 1
        ups = 0.0
        downs = 0.0
        for k in range(sig - SV_LB + 1, sig + 1):
            r = float(h1["c"][k]) - float(h1["o"][k])
            if r >= 0:
                ups += r * r
            else:
                downs += r * r
        tot = ups + downs
        if tot <= 0:
            continue
        up_share = ups / tot
        dn_share = downs / tot
        side = 0
        if up_share >= SV_SHARE:
            side = 1
        elif dn_share >= SV_SHARE:
            side = -1
        if side == 0:
            continue
        atr = h1["atr"][sig]
        if not np.isfinite(atr) or atr <= 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(h1["o"][i])
        sl = entry - side * SV_SL * atr
        tp = entry + side * SV_RR * SV_SL * atr
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
    flush_open(open_pos, {sym: h1}, closed)
    return summarize(closed)


def probe_eth_utc0_drive_cont(h1):
    closed, open_pos = [], []
    sym = "ETHUSD"
    fired_days = set()
    for i in range(1, len(h1["t"]) - 1):
        ts = int(h1["t"][i])
        open_pos = manage_exits(open_pos, {sym: h1}, ts, closed, U0_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.hour != 0:
            continue
        day = dt.date()
        if day in fired_days:
            continue
        if open_pos:
            continue
        atr = h1["atr"][i]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(h1["c"][i]) - float(h1["o"][i])
        if abs(body) < U0_BODY_ATR * atr:
            continue
        side = 1 if body > 0 else -1
        entry = float(h1["o"][i + 1])
        sl = entry - side * U0_SL * atr
        tp = entry + side * U0_RR * U0_SL * atr
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
        fired_days.add(day)
    flush_open(open_pos, {sym: h1}, closed)
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
                "feature_family": "greenfield_r17_vr_semivar_utc0",
                "lane": "strategy_shift_r17_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": "R17 NON-FADE outside R10–R16 densify; nested critic GO",
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
                "# 3-critic panel — Round 17 VR / semivar / UTC0",
                "",
                "Date: 2026-07-15",
                "Nested critic GO `cursor-grok-4.5-high-fast`; lead closeout.",
                "",
                "## Named (NON-FADE)",
                "1. `ETH_H4_VARIANCE_RATIO_MOM_CONT`",
                "2. `NZD_H1_SIGNED_SEMIVAR_CONT`",
                "3. `ETH_H1_UTC0_OPEN_DRIVE_CONT`",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — VR regime + signed pressure + crypto day-auction |",
                "| Quant | SOFT — estimator/session DOF; freeze-only OK |",
                "| MQL5/MT5 | PASS — closed-bar VR/semivar/UTC0 |",
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
                "# Design — Round 17 VR / semivar / UTC0",
                "",
                "Date: 2026-07-15",
                f"## 1 `HYP-ETHUSD-H4-VARIANCE-RATIO-MOM-CONT-001`",
                f"VR(q={VR_Q}, lb={VR_LB})>{VR_MIN} → CONT sign(sum last {VR_DIR_LB} logret);",
                f"SL={VR_SL} RR={VR_RR} hold≤{VR_HOLD}.",
                "",
                f"## 2 `HYP-NZDUSD-H1-SIGNED-SEMIVAR-CONT-001`",
                f"24-bar signed semi-var share≥{SV_SHARE} → CONT; SL={SV_SL} RR={SV_RR} hold≤{SV_HOLD}.",
                "",
                f"## 3 `HYP-ETHUSD-H1-UTC0-OPEN-DRIVE-CONT-001`",
                f"UTC hour=0 |body|≥{U0_BODY_ATR}×ATR → CONT; SL={U0_SL} RR={U0_RR} hold≤{U0_HOLD}.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 17 VR / semivar / UTC0",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| ETH VR mom CONT | ≠ BTC/XAU/XAG/NAS ROC-k thick; ≠ CUSUM; ≠ Parkinson; ≠ US30 HL-break |",
                "| NZD signed semivar CONT | ≠ Parkinson RV; ≠ tickvol-imb; ≠ ON-ratio; ≠ closeloc/streak; ≠ AUDNZD resid |",
                "| ETH UTC0 drive CONT | ≠ London/NY/Tokyo session densify; ≠ weekend-gap; ≠ CPI/NFP body-k; ≠ US30 lead |",
                "",
                "R10–R16 densify: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 17 VR / semivar / UTC0",
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
                "# Session closeout — Round 17 VR / semivar / UTC0",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify VR-k / semivar share-k / UTC0 body-k / R10–R16.",
                "Next: next true greenfield outside R17 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 17 VR / semivar / UTC0",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R16. **NON-FADE only.** ETH/NZD + architecture mới.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Không densify VR-k / semivar share-k / UTC0 body-k / R10–R16.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R17 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 17 (post R16)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R17 NON-FADE. GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 17 — VR / semivar / UTC0",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "",
                "## Cấm",
                "Densify R1–R17 / fade-session / unpark / exit / FRED / Phase-0 ceremony.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R17 (NON-FADE); cost khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND17 VR/SEMIVAR/UTC0 CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R16 densify + R1–R9/unpark/exit/FRED.",
        "  Nested critic GO → lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R17_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify VR-k / semivar share-k / UTC0 body-k /",
        "  R16 US30-break/CPI/lead / R15 streak/BTC/XAG / R14–R10 / R1–R9 /",
        "  unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R17 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R17 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND17 VR/SEMIVAR/UTC0 CLOSEOUT"):
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
        eth_h4 = enrich(load("ETHUSD", mt5.TIMEFRAME_H4))
        eth_h1 = enrich(load("ETHUSD", mt5.TIMEFRAME_H1))
        nzd_h1 = enrich(load("NZDUSD", mt5.TIMEFRAME_H1))
        results = [
            pack_result(
                "HYP-ETHUSD-H4-VARIANCE-RATIO-MOM-CONT-001",
                "ethusd_h4_variance_ratio_mom_cont",
                "ETHUSD",
                "H4",
                *probe_eth_vr_mom_cont(eth_h4),
            ),
            pack_result(
                "HYP-NZDUSD-H1-SIGNED-SEMIVAR-CONT-001",
                "nzdusd_h1_signed_semivar_cont",
                "NZDUSD",
                "H1",
                *probe_nzd_signed_semivar_cont(nzd_h1),
            ),
            pack_result(
                "HYP-ETHUSD-H1-UTC0-OPEN-DRIVE-CONT-001",
                "ethusd_h1_utc0_open_drive_cont",
                "ETHUSD",
                "H1",
                *probe_eth_utc0_drive_cont(eth_h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r17_vr_semivar_utc0.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "hard_constraint": "NON_FADE__NO_R10_R16_DENSIFY",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "vr": {
                    "lb": VR_LB,
                    "q": VR_Q,
                    "min": VR_MIN,
                    "dir_lb": VR_DIR_LB,
                    "sl": VR_SL,
                    "rr": VR_RR,
                    "hold": VR_HOLD,
                },
                "semivar": {
                    "lb": SV_LB,
                    "share": SV_SHARE,
                    "sl": SV_SL,
                    "rr": SV_RR,
                    "hold": SV_HOLD,
                },
                "utc0": {
                    "body_atr": U0_BODY_ATR,
                    "sl": U0_SL,
                    "rr": U0_RR,
                    "hold": U0_HOLD,
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
