#!/usr/bin/env python3
"""Round 31 greenfield — Outside-bar CONT + First-DOM + Post-timestop cooldown.

Post R30: dayopen/IMM/samedircap ALL_KILL. Keep NON-indicator / NON-FADE.

HARD FORBIDDEN densify: R1–R30 incl. dayopen / IMM / samedircap /
equal-HL / opex-window / oneslot / week-HL / monthend / losscd /
H4-engulf / TA clones / lead / fade-session / ORB/IB / unpark / RR2 / FRED.

A priori (≥2; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-OUTSIDE-BAR-CONT-001           (structural outside CONT)
  2) HYP-GBPUSD-H1-FIRST-DOM-CONT-001          (event first day-of-month)
  3) HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001 (book pacing after time-exit)

+$12 joint. Model 0 only if PROBE_SURVIVOR. Closed-bar only.
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

STEM = "20260715_GREENFIELD_R31_OUTSIDE_FIRSTDOM_TSTOPCD"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R31_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"
OUT_DEAL_RETRY = PRE / "20260715_COST_DEAL_RETRY_R31.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 Outside-bar CONT (engulfs prior H+L; CONT in close direction)
OB_BODY = 0.35
OB_SL = 1.45
OB_RR = 2.00
OB_HOLD = 12

# 2 First trading day of month CONT on GBPUSD
FD_BODY = 0.40
FD_SL = 1.45
FD_RR = 2.00
FD_HOLD = 10

# 3 Post-timestop cooldown arch: after time-exit, wait CD bars before re-entry
TS_BODY = 0.40
TS_SL = 1.45
TS_RR = 2.00
TS_HOLD = 10
TS_CD = 6  # bars flat after time-stop before new entry on that symbol


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


def manage_exits(open_pos, data, ts, closed, hold_limit, on_time_exit=None):
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
            if reason == "time" and on_time_exit is not None:
                on_time_exit(sym, ts)
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


def is_first_dom(dt: datetime, prev_dt: datetime | None) -> bool:
    """True if this weekday bar is the first weekday of a new calendar month."""
    if dt.weekday() >= 5:
        return False
    if prev_dt is None:
        return False  # need a prior bar to detect month roll
    return (dt.year, dt.month) != (prev_dt.year, prev_dt.month)


def probe_fx3_outside(h1):
    """Outside bar (H>prevH and L<prevL) + body filter → CONT in close direction."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    for i in range(30, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, OB_HOLD)
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
            if j is None or j < 2:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # outside vs prior closed bar j-1
            if not (d["h"][j] > d["h"][j - 1] and d["l"][j] < d["l"][j - 1]):
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < OB_BODY * atr:
                continue
            side = 1 if body > 0 else -1
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * OB_SL * atr
            tp = entry + side * OB_RR * OB_SL * atr
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


def probe_gbpusd_first_dom(gb):
    closed, open_pos = [], []
    sym = "GBPUSD"
    last_day = None
    prev_sig_dt = None
    for i in range(30, len(gb["t"]) - 1):
        ts = int(gb["t"][i])
        open_pos = manage_exits(open_pos, {sym: gb}, ts, closed, FD_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1
        sig_dt = datetime.fromtimestamp(int(gb["t"][j]), tz=timezone.utc)
        # first DOM: signal bar is on first weekday of new month
        if not is_first_dom(sig_dt, prev_sig_dt):
            prev_sig_dt = sig_dt
            continue
        prev_sig_dt = sig_dt
        # only trade once on that first DOM
        atr = gb["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(gb["c"][j]) - float(gb["o"][j])
        if abs(body) < FD_BODY * atr:
            continue
        side = 1 if body > 0 else -1
        day = dt.date()
        if day == last_day:
            continue
        entry = float(gb["o"][i])
        sl = entry - side * FD_SL * atr
        tp = entry + side * FD_RR * FD_SL * atr
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


def probe_fx3_timestop_cd(h1):
    """Body CONT; after a time-stop exit on a symbol, block re-entry for TS_CD bars."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    cd_until = {s: -1 for s in FX3}  # bar index on clock until which blocked

    def on_time_exit(sym, ts):
        # find clock index of ts
        k = int(np.searchsorted(clock, ts, side="left"))
        cd_until[sym] = k + TS_CD

    for i in range(30, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(
            open_pos, h1, ts, closed, TS_HOLD, on_time_exit=on_time_exit
        )
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        for sym in FX3:
            if sym in open_syms:
                continue
            if i <= cd_until[sym]:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < TS_BODY * atr:
                continue
            side = 1 if body > 0 else -1
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * TS_SL * atr
            tp = entry + side * TS_RR * TS_SL * atr
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
                "feature_family": "greenfield_r31_outside_firstdom_tstopcd",
                "lane": "strategy_shift_r31_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R31 NON-FADE non-indicator after R30 ALL_KILL; "
                    "OPEX near-miss NO densify; nested critic GO lead self-merge"
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
                "# 3-critic panel — Round 31 Outside / FirstDOM / TimeStop-CD",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (lead self-merge; NON-indicator; outside R1–R30 densify).",
                "",
                "## Named (NON-FADE; structural / event / book)",
                "1. Outside-bar CONT — H>prevH & L<prevL then CONT close-dir (≠ Wave3 Outside-REV)",
                "2. First-DOM CONT — first weekday of calendar month (≠ R28 month-end)",
                "3. Post-timestop CD arch — after time-exit wait N bars (≠ R28 losscd)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — expansion bar CONT + month-start flow + inventory pacing |",
                "| Quant | PASS — independent; joint gates a priori; OPEX densify banned |",
                "| MQL5/MT5 | PASS — closed-bar outside / calendar DOM / next-open |",
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
                "# Design — Round 31 Outside / FirstDOM / TimeStop-CD",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-OUTSIDE-BAR-CONT-001`",
                f"Outside prior bar + body≥{OB_BODY}×ATR → CONT close direction.",
                "Why: CONT ≠ Wave3 Outside-REV; ≠ H4-engulf; ≠ Marubozu densify.",
                "",
                "## 2 `HYP-GBPUSD-H1-FIRST-DOM-CONT-001`",
                f"First weekday of new month + body≥{FD_BODY}×ATR → CONT.",
                "Why: month-start flow ≠ R28 month-end rebal; ≠ IMM; ≠ OPEX.",
                "",
                "## 3 `HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001`",
                f"|body|≥{TS_BODY}×ATR CONT; after time-stop exit wait {TS_CD} bars on that symbol.",
                "Why: inventory pacing ≠ R28 loss-cooldown; ≠ oneslot; ≠ samedir-cap.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 31 Outside / FirstDOM / TimeStop-CD",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 outside-bar CONT | ≠ Wave3 Outside-REV; ≠ R25 H4-engulf; ≠ R27 Marubozu |",
                "| GBPUSD first-DOM CONT | ≠ R28 month-end; ≠ R30 IMM; ≠ R29 OPEX; ≠ FRED |",
                "| FX3 post-timestop CD arch | ≠ R28 losscd; ≠ R29 oneslot; ≠ R30 samedir-cap |",
                "",
                "R1–R30 densify + OPEX-window near-miss + TA clones + fade/session + FRED + RR2 exits: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 31 Outside / FirstDOM / TimeStop-CD",
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
                "# Session closeout — Round 31 Outside / FirstDOM / TimeStop-CD",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify outside-k / firstdom-k / tstopcd-k /",
                "R30 dayopen/IMM/samedircap / R29 equal-HL/opex/oneslot /",
                "H4-engulf / lead / fade-session / unpark / RR2-exit / FRED.",
                "Next: next true greenfield outside R31 (NON-FADE, non-indicator).",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 31 Outside / FirstDOM / TimeStop-CD",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R1–R30. **NON-FADE. NON-indicator.**",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế",
                "1. Outside-bar CONT — nến bao trùm H+L rồi tiếp tục theo close (structural)",
                "2. First-DOM — ngày giao dịch đầu tháng (event)",
                "3. Post-timestop CD — sau time-exit chờ N bar mới vào lại (architecture)",
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
    near = [
        "- R29 USDJPY OPEX Friday: PF≈1.35 x1.5≈1.26 nhưng N=76 / tpw≈0.29 — **cấm densify cửa sổ**.",
        "- R25 USDJPY H4-engulf CONT: PF≈1.24 x1.5≈1.16 — **cấm densify**.",
        "- R28 prior-week HL PF≈1.10 — không densify.",
    ]
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN brief — Clean book + Round 31",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R31 NON-FADE structural/event/book. GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 31 — Outside / FirstDOM / TimeStop-CD",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007 + cost",
                f"{qnote}",
                f"Cost: {cost_note}",
                "",
                "## Near-miss shelf (do not densify)",
                *near,
                "",
                "## Cấm",
                "Densify R1–R31 / TA clones / OPEX-window / dayopen / IMM / samedircap / "
                "outside / firstdom / tstopcd / fade-session / unpark / RR2-exit / FRED / "
                "Phase-0 / H4-engulf.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R31 (**NON-FADE, non-indicator**); cost autonomous.",
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
        f"- **GREENFIELD ROUND31 OUTSIDE/FIRSTDOM/TSTOPCD CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE **non-indicator** greenfield outside R1–R30 densify",
        "  (structural / event / book-architecture).",
        "  Nested critic GO — Outside-bar / First-DOM / Post-timestop-CD "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R31_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        f"  Cost autonomous: {cost_note}",
        "  Near-miss carry (NO densify): OPEX PF≈1.35 x1.5≈1.26 but N=76 tpw≈0.29.",
        "  Do **not** densify outside-k / firstdom-k / tstopcd-k /",
        "  R30 dayopen/IMM/samedircap / R29 equal-HL/opex/oneslot /",
        "  R28 week-HL/monthend/losscd / H4-engulf / lead / fade-session /",
        "  ORB/IB / unpark / RR2-exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R31 (still NON-FADE, non-indicator) —",
        "  QFSI parallel; cost autonomous retry (no Owner deal-export headline).",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R31 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND31 OUTSIDE/FIRSTDOM/TSTOPCD CLOSEOUT"):
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
                "Next = greenfield **outside** R1–R31 densify (NON-FADE, non-indicator), "
                "or cost via autonomous `history_deals_get` / QFSI (no Owner deal-export headline). "
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
            base += f"; R31 retry history_deals_get raw_deals={deal_retry.get('raw_deals')}"
            cu = deal_retry.get("commission_unique_by_symbol") or {}
            if cu:
                base += f" comm_unique={cu}"
        else:
            base += f"; R31 retry FAIL ({deal_retry.get('error')})"
    return base + "; freeze_eligible=False"


def freeze_contract_sha() -> str:
    contract = {
        "outside_bar": {
            "body": OB_BODY,
            "sl": OB_SL,
            "rr": OB_RR,
            "hold": OB_HOLD,
            "universe": list(FX3),
        },
        "first_dom": {
            "body": FD_BODY,
            "sl": FD_SL,
            "rr": FD_RR,
            "hold": FD_HOLD,
            "symbol": "GBPUSD",
        },
        "post_timestop_cd": {
            "body": TS_BODY,
            "sl": TS_SL,
            "rr": TS_RR,
            "hold": TS_HOLD,
            "cd_bars": TS_CD,
            "universe": list(FX3),
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": (
            "R1_R30_densify__OPEX_window__dayopen_IMM_samedircap__"
            "equalHL_oneslot__weekHL_monthend_losscd__TA_clones__FRED__RR2_exit"
        ),
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
                    "# Universe freeze — Round 31 Outside / FirstDOM / TimeStop-CD",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — lead self-merge).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-OUTSIDE-BAR-CONT-001",
                    "2. HYP-GBPUSD-H1-FIRST-DOM-CONT-001",
                    "3. HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001",
                    "",
                    "Mechanism note: (1) outside CONT ≠ Outside-REV/H4-engulf/Marubozu;",
                    "(2) first-DOM ≠ month-end/IMM/OPEX; (3) timestop-CD ≠ losscd/oneslot.",
                    "OPEX-window densify FORBIDDEN. TA-indicator densify FORBIDDEN.",
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
                "HYP-FX3-H1-OUTSIDE-BAR-CONT-001",
                "fx3_h1_outside_bar_cont",
                "FX3",
                "H1",
                *probe_fx3_outside(h1),
            ),
            pack_result(
                "HYP-GBPUSD-H1-FIRST-DOM-CONT-001",
                "gbpusd_h1_first_dom_cont",
                "GBPUSD",
                "H1",
                *probe_gbpusd_first_dom(h1["GBPUSD"]),
            ),
            pack_result(
                "HYP-FX3-H1-POST-TIMESTOP-CD-ARCH-CONT-001",
                "fx3_h1_post_timestop_cd_arch_cont",
                "FX3",
                "H1",
                *probe_fx3_timestop_cd(h1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r31_outside_firstdom_tstopcd.v1_closedbar",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": (
                "NON_FADE__NON_INDICATOR__NO_R1_R30_DENSIFY__NO_OPEX_WINDOW__"
                "NO_H4ENGULF__NO_LEAD__NO_FADE_SESSION__NO_FRED__NO_RR2_EXIT"
            ),
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "qfsi_parallel": qnote,
            "cost_autonomous": cost_note,
            "deal_retry_r31": deal_retry,
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
