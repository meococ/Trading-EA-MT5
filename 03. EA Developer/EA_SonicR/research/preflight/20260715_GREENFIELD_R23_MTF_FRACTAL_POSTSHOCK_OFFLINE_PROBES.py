#!/usr/bin/env python3
"""Round 23 greenfield — multi-TF align + fractal break + post-shock CONT.

Post R22: AC/risksync again cadence-OK / PF@$12 fail. Prefer rarer quality.

HARD FORBIDDEN: R22 AC/ATR-exp/risksync densify; lead-clones; USD-implied;
R10–R21 densify; Parkinson/compress; residual/corr/ON-ratio; ETH VR;
fade/MR; unpark/exit/FRED.

A priori (≥2 mechanisms; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-MULTITF-ALIGN-CONT-001
     D1+H4+H1 same-sign closed bodies → H1 CONT (TF confluence).
  2) HYP-USDJPY-H1-FRACTAL5-BREAK-CONT-001
     Williams 5-bar fractal extreme break + bodyQ CONT.
  3) HYP-EURUSD-H1-POSTSHOCK-LONDON-CONT-001
     Prior D1 |ret|≥2.5σ → next London H1 CONT in shock direction.

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

STEM = "20260715_GREENFIELD_R23_MTF_FRACTAL_POSTSHOCK"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R23_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 multi-TF align
MT_BODY_H1 = 0.40
MT_BODY_H4 = 0.35
MT_BODY_D1 = 0.30
MT_SL = 1.45
MT_RR = 2.00
MT_HOLD = 10

# 2 fractal5 break
FR_N = 5  # center looks 2 left + 2 right → classic Williams 5
FR_BREAK = 0.15
FR_BODY = 0.45
FR_SL = 1.45
FR_RR = 2.00
FR_HOLD = 10

# 3 post-shock London
PS_WIN = 20
PS_Z = 2.5
PS_BODY = 0.50
PS_HOUR0 = 7
PS_HOUR1 = 11
PS_SL = 1.45
PS_RR = 2.00
PS_HOLD = 10


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


H1_SEC = 3600
H4_SEC = 4 * 3600
D1_SEC = 24 * 3600


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def last_fully_closed(d, asof_ts, period_sec):
    """Last bar whose close time (open+period) is <= asof_ts. No forming-bar peek."""
    if len(d["t"]) == 0:
        return None
    closes = d["t"].astype(np.int64) + int(period_sec)
    j = int(np.searchsorted(closes, int(asof_ts), side="right")) - 1
    return j if j >= 0 else None


def probe_fx3_mtf_align(h1, h4, d1):
    """FX3: D1+H4+H1 same-sign bodies → H1 CONT next open (closed-bar only)."""
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    open_syms = set()
    for i in range(3, len(clock) - 1):
        ts = int(clock[i])  # entry open
        open_pos = manage_exits(open_pos, h1, ts, closed, MT_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        # As-of entry open: H1 signal closed at sig_ts+H1; HTF must be fully closed ≤ ts
        for sym in FX3:
            if sym in open_syms:
                continue
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            dh1 = h1[sym]
            dh4 = h4[sym]
            dd1 = d1[sym]
            j1 = asof_idx(dh1, sig_ts)
            if j1 is None:
                continue
            j4 = last_fully_closed(dh4, ts, H4_SEC)
            jd = last_fully_closed(dd1, ts, D1_SEC)
            if j4 is None or jd is None:
                continue
            atr = dh1["atr"][j1]
            atr4 = dh4["atr"][j4]
            atrd = dd1["atr"][jd]
            if any((not np.isfinite(x) or x <= 0) for x in (atr, atr4, atrd)):
                continue
            b1 = float(dh1["c"][j1]) - float(dh1["o"][j1])
            b4 = float(dh4["c"][j4]) - float(dh4["o"][j4])
            bd = float(dd1["c"][jd]) - float(dd1["o"][jd])
            if abs(b1) < MT_BODY_H1 * atr:
                continue
            if abs(b4) < MT_BODY_H4 * atr4:
                continue
            if abs(bd) < MT_BODY_D1 * atrd:
                continue
            if not ((b1 > 0 and b4 > 0 and bd > 0) or (b1 < 0 and b4 < 0 and bd < 0)):
                continue
            side = 1 if b1 > 0 else -1
            ent_i = asof_idx(dh1, ts)
            if ent_i is None:
                continue
            entry = float(dh1["o"][ent_i])
            sl = entry - side * MT_SL * atr
            tp = entry + side * MT_RR * MT_SL * atr
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


def probe_usdjpy_fractal(uj):
    """USDJPY: after fractal confirm, later bar breaks level + bodyQ CONT."""
    closed, open_pos = [], []
    sym = "USDJPY"
    last_day = None
    # Maintain last confirmed fractal hi/lo levels (as-of closed bars only).
    last_fh = None
    last_fl = None
    for i in range(FR_N + 2, len(uj["t"]) - 1):
        ts = int(uj["t"][i])
        open_pos = manage_exits(open_pos, {sym: uj}, ts, closed, FR_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig = i - 1
        # Update confirmed fractals using bars fully known at signal close:
        # center k confirmed when sig >= k+2
        k = sig - 2
        if k >= 2:
            fh = float(uj["h"][k])
            fl = float(uj["l"][k])
            if (
                fh > float(uj["h"][k - 1])
                and fh > float(uj["h"][k - 2])
                and fh > float(uj["h"][k + 1])
                and fh > float(uj["h"][k + 2])
            ):
                last_fh = fh
            if (
                fl < float(uj["l"][k - 1])
                and fl < float(uj["l"][k - 2])
                and fl < float(uj["l"][k + 1])
                and fl < float(uj["l"][k + 2])
            ):
                last_fl = fl
        if open_pos:
            continue
        atr = uj["atr"][sig]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(uj["c"][sig]) - float(uj["o"][sig])
        c = float(uj["c"][sig])
        side = 0
        # Break must be on a bar AFTER confirmation (sig > k+2 for that fractal).
        # Using stored last_fh/fl which were confirmed at least at this signal bar.
        if last_fh is not None and c >= last_fh + FR_BREAK * atr and body >= FR_BODY * atr:
            side = 1
        elif last_fl is not None and c <= last_fl - FR_BREAK * atr and body <= -FR_BODY * atr:
            side = -1
        if side == 0:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(uj["o"][i])
        sl = entry - side * FR_SL * atr
        tp = entry + side * FR_RR * FR_SL * atr
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
        # Consume level to avoid repeat breaks of same fractal
        if side > 0:
            last_fh = None
        else:
            last_fl = None
    flush_open(open_pos, {sym: uj}, closed)
    return summarize(closed)


def probe_eurusd_postshock(eu, eu_d1):
    """EURUSD: after fully-closed D1 shock (|z|≥2.5), London H1 CONT."""
    closed, open_pos = [], []
    sym = "EURUSD"
    last_day = None
    dc = eu_d1["c"]
    dret = np.empty_like(dc)
    dret[0] = np.nan
    dret[1:] = np.diff(dc) / dc[:-1]
    dz = np.full_like(dc, np.nan)
    for i in range(PS_WIN, len(dc)):
        w = dret[i - PS_WIN + 1 : i + 1]
        if np.any(~np.isfinite(w)):
            continue
        mu, sd = float(np.mean(w[:-1])), float(np.std(w[:-1], ddof=1))
        if sd < 1e-12:
            continue
        dz[i] = (dret[i] - mu) / sd

    for i in range(3, len(eu["t"]) - 1):
        ts = int(eu["t"][i])
        open_pos = manage_exits(open_pos, {sym: eu}, ts, closed, PS_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        if not (PS_HOUR0 <= dt.hour < PS_HOUR1):
            continue
        # Fully closed D1 only (no forming day bar)
        jd = last_fully_closed(eu_d1, ts, D1_SEC)
        if jd is None or not np.isfinite(dz[jd]):
            continue
        if abs(dz[jd]) < PS_Z:
            continue
        shock_day = datetime.fromtimestamp(int(eu_d1["t"][jd]), tz=timezone.utc).date()
        # Trade only on the next weekday after shock day
        if dt.date() <= shock_day:
            continue
        if (dt.date() - shock_day).days > 3:
            continue
        j = i - 1
        atr = eu["atr"][j]
        if not np.isfinite(atr) or atr <= 0:
            continue
        body = float(eu["c"][j]) - float(eu["o"][j])
        if abs(body) < PS_BODY * atr:
            continue
        side = 1 if dz[jd] > 0 else -1
        if (side > 0 and body <= 0) or (side < 0 and body >= 0):
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(eu["o"][i])
        sl = entry - side * PS_SL * atr
        tp = entry + side * PS_RR * PS_SL * atr
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
                "feature_family": "greenfield_r23_mtf_fractal_postshock",
                "lane": "strategy_shift_r23_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R23 NON-FADE quality-over-cadence after R22 AC/risksync "
                    "cadence-OK/PF-fail; nested critic GO"
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
                "# 3-critic panel — Round 23 MTF / fractal / post-shock",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (quality-over-cadence after R22 thick PF-fail).",
                "",
                "## Named (NON-FADE) — why different mechanisms",
                "1. `FX3_H1_MULTITF_ALIGN_CONT` — D1+H4+H1 confluence (≠ single-TF accel/AC)",
                "2. `USDJPY_H1_FRACTAL5_BREAK_CONT` — Williams swing break (≠ Donch8 channel)",
                "3. `EURUSD_H1_POSTSHOCK_LONDON_CONT` — D1 shock aftermath (≠ NFP same-day)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — rarer structural/event-aftermath vs thick impulse spam |",
                "| Quant | PASS — independent; expect thinner N vs R22 AC board |",
                "| MQL5/MT5 | PASS — closed-bar fractal confirm; D1 as-of before London H1 |",
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
                "# Design — Round 23 MTF / fractal / post-shock",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## Mandate",
                "Outside R10–R22. Prefer quality over cadence-thick PF-fail local optimum.",
                "",
                f"## 1 `HYP-FX3-H1-MULTITF-ALIGN-CONT-001`",
                f"Closed D1/H4/H1 bodies same sign (≥{MT_BODY_D1}/{MT_BODY_H4}/{MT_BODY_H1}×ATR)",
                f"→ H1 CONT; SL={MT_SL} RR={MT_RR}.",
                "Why: multi-horizon confluence — ≠ R21 two-bar accel; ≠ R22 lag1-AC.",
                "",
                f"## 2 `HYP-USDJPY-H1-FRACTAL5-BREAK-CONT-001`",
                f"Williams {FR_N}-bar fractal confirm then close beyond ±{FR_BREAK}×ATR with",
                f"|body|≥{FR_BODY}×ATR → CONT; SL={FR_SL} RR={FR_RR}.",
                "Why: swing-structure break — ≠ R21 Donch8 rolling channel; ≠ R16 D1 HL.",
                "",
                f"## 3 `HYP-EURUSD-H1-POSTSHOCK-LONDON-CONT-001`",
                f"Prior D1 |z-ret|≥{PS_Z} (win={PS_WIN}); next London [{PS_HOUR0},{PS_HOUR1})",
                f"H1 body agrees → CONT; SL={PS_SL} RR={PS_RR}.",
                "Why: shock *aftermath* continuation — ≠ R13 NFP same-day impulse; ≠ R16 CPI.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 23 MTF / fractal / post-shock",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 multi-TF align CONT | ≠ R21 two-bar accel; ≠ R22 lag1-AC; ≠ R15 streak; "
                "≠ lead-clones |",
                "| USDJPY fractal5 break CONT | ≠ R21 Donch8; ≠ R16 US30 D1 HL; ≠ R18 pivot; "
                "≠ Parkinson compress |",
                "| EURUSD post-shock London CONT | ≠ R13 NFP same-day; ≠ R16 CPI body; "
                "≠ R14 weekend gap; ≠ R10 London drive densify |",
                "",
                "R10–R22 densify + lead-clone + USD-imp: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 23 MTF / fractal / post-shock",
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
                "# Session closeout — Round 23 MTF / fractal / post-shock",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify MTF-k / fractal-k / postshock-k /",
                "R22 AC/ATR/risksync / lead-clones / USD-imp / R21–R10 / unpark / exit / FRED.",
                "Next: next true greenfield outside R23 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 23 MTF / fractal / post-shock",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R22. **NON-FADE.** Quality-over-cadence.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế (a priori)",
                "1. Multi-TF align — D1+H4+H1 đồng hướng",
                "2. Fractal5 break — swing structure (≠ Donch)",
                "3. Post-shock London — hậu quả D1 shock (≠ NFP same-day)",
                "",
                "## Quyết định",
                "- Không densify MTF / fractal / postshock / R10–R22 / lead / USD-imp.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R23 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 23",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R23 NON-FADE (MTF/fractal/postshock). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 23 — MTF / fractal / post-shock",
                *table,
                f"Receipt `{receipt}` → `{status}`",
                f"Freeze `{freeze_sha[:16]}…`",
                "",
                "## 3. QFSI 007",
                f"{qnote}",
                "",
                "## Near-miss shelf (do not densify)",
                "- R17 ETH VR: PF≈1.98 tpw≈0.33 — cadence only.",
                "- R21 EURJPY USD-imp: PF≈1.20 x1.5≈1.13 — near but joint fail.",
                "- R22 AC/risksync: tpw≈5–7 PF≈0.96–1.08 — thick cadence PF-fail.",
                "",
                "## Cấm",
                "Densify R1–R23 / VR / lead-clone / USD-imp / fade-session / "
                "unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R23 (NON-FADE); cost khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND23 MTF/FRACTAL/POSTSHOCK CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R22 densify; quality-over-cadence.",
        "  Nested critic GO — MTF-align / fractal5 / post-shock (not lead clones) "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R23_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify MTF-k / fractal-k / postshock-k /",
        "  R22 AC/ATR-exp/risksync / lead-clones / USD-imp / R21–R10 /",
        "  R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R23 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R23 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND23 MTF/FRACTAL/POSTSHOCK CLOSEOUT"):
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
        "mtf": {
            "body_h1": MT_BODY_H1,
            "body_h4": MT_BODY_H4,
            "body_d1": MT_BODY_D1,
            "sl": MT_SL,
            "rr": MT_RR,
            "hold": MT_HOLD,
            "universe": list(FX3),
        },
        "fractal": {
            "n": FR_N,
            "break": FR_BREAK,
            "body": FR_BODY,
            "sl": FR_SL,
            "rr": FR_RR,
            "hold": FR_HOLD,
        },
        "postshock": {
            "win": PS_WIN,
            "z": PS_Z,
            "body": PS_BODY,
            "hours": [PS_HOUR0, PS_HOUR1],
            "sl": PS_SL,
            "rr": PS_RR,
            "hold": PS_HOLD,
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R10_R22_densify__lead_clones__USD_implied",
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
                    "# Universe freeze — Round 23 MTF / fractal / post-shock",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — quality-over-cadence).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-MULTITF-ALIGN-CONT-001",
                    "2. HYP-USDJPY-H1-FRACTAL5-BREAK-CONT-001",
                    "3. HYP-EURUSD-H1-POSTSHOCK-LONDON-CONT-001",
                    "",
                    "Mechanism note: (1) multi-TF confluence ≠ single-TF AC/accel; "
                    "(2) Williams fractal ≠ Donch channel; "
                    "(3) D1 shock aftermath ≠ NFP/CPI same-day.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
        h4 = {s: enrich(load(s, mt5.TIMEFRAME_H4)) for s in FX3}
        d1 = {s: enrich(load(s, mt5.TIMEFRAME_D1)) for s in FX3}
        uj = h1["USDJPY"]
        eu = h1["EURUSD"]
        eu_d1 = d1["EURUSD"]
        results = [
            pack_result(
                "HYP-FX3-H1-MULTITF-ALIGN-CONT-001",
                "fx3_h1_multitf_align_cont",
                "FX3",
                "H1",
                *probe_fx3_mtf_align(h1, h4, d1),
            ),
            pack_result(
                "HYP-USDJPY-H1-FRACTAL5-BREAK-CONT-001",
                "usdjpy_h1_fractal5_break_cont",
                "USDJPY",
                "H1",
                *probe_usdjpy_fractal(uj),
            ),
            pack_result(
                "HYP-EURUSD-H1-POSTSHOCK-LONDON-CONT-001",
                "eurusd_h1_postshock_london_cont",
                "EURUSD",
                "H1",
                *probe_eurusd_postshock(eu, eu_d1),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r23_mtf_fractal_postshock.v2_closedbar_asof",
            "lookahead_note": (
                "v1 INVALIDATED: HTF used forming H4/D1 (open<ts). "
                "v2 uses last_fully_closed(open+period<=asof)."
            ),
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": "NON_FADE__NO_R10_R22_DENSIFY__NO_LEAD_CLONES",
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "mtf": {
                    "body_h1": MT_BODY_H1,
                    "body_h4": MT_BODY_H4,
                    "body_d1": MT_BODY_D1,
                    "sl": MT_SL,
                    "rr": MT_RR,
                    "hold": MT_HOLD,
                },
                "fractal": {
                    "n": FR_N,
                    "break": FR_BREAK,
                    "body": FR_BODY,
                    "sl": FR_SL,
                    "rr": FR_RR,
                    "hold": FR_HOLD,
                },
                "postshock": {
                    "win": PS_WIN,
                    "z": PS_Z,
                    "body": PS_BODY,
                    "hours": [PS_HOUR0, PS_HOUR1],
                    "sl": PS_SL,
                    "rr": PS_RR,
                    "hold": PS_HOLD,
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
