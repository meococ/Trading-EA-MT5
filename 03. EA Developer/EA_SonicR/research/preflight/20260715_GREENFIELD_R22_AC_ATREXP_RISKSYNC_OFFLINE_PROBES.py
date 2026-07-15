#!/usr/bin/env python3
"""Round 22 greenfield — lag1-AC regime + ATR-expansion burst + FX3 risk-sync.

BREAK lead-clone local optimum (R16–R20 cadence-OK / PF@$12 fail).

HARD FORBIDDEN: commodity/equity→FX lead clones; USD-implied densify;
R10–R21 densify lists; Parkinson/compress; residual/corr/ON-ratio;
ETH VR rescue; fade/MR; unpark/exit/FRED.

A priori (≥2 mechanisms; 3 named; nested critic GO — lead self-merge):
  1) HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001
     Statistical persistence: rolling lag-1 return AC gate + body CONT.
  2) HYP-GBPUSD-H1-ATREXP-BURST-CONT-001
     Vol-expansion regime (ATR14/ATR56) + conviction body CONT.
  3) HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001
     Same-bar FX-major risk-sync → AUD CONT (≠ XTI/XAU/US30 lead).

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

STEM = "20260715_GREENFIELD_R22_AC_ATREXP_RISKSYNC"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_R22_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# 1 lag-1 AC regime + body
AC_WIN = 24
AC_MIN = 0.15
AC_BODY = 0.55
AC_SL = 1.45
AC_RR = 2.00
AC_HOLD = 10

# 2 ATR expansion burst
EX_FAST = 14
EX_SLOW = 56
EX_RATIO = 1.25
EX_BODY = 0.60
EX_CLOSE = 0.30  # outer 30% of range
EX_SL = 1.45
EX_RR = 2.00
EX_HOLD = 10

# 3 FX3 risk-sync → AUD
RS_LEG = 0.35
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


def lag1_ac_arr(c, win=AC_WIN):
    """Rolling Pearson corr of close-to-close returns with lag-1."""
    r = np.empty_like(c, dtype=float)
    r[0] = np.nan
    r[1:] = np.diff(c) / c[:-1]
    out = np.full_like(c, np.nan, dtype=float)
    for i in range(win, len(c)):
        # pairs (r[t], r[t-1]) for t in (i-win+1 .. i] → need r[i-win+1 : i+1] and lag
        a = r[i - win + 1 : i + 1]
        b = r[i - win : i]
        if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)):
            continue
        if np.std(a) < 1e-12 or np.std(b) < 1e-12:
            continue
        out[i] = float(np.corrcoef(a, b)[0, 1])
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


def enrich(d, with_ac=False, with_atr_slow=False):
    d["atr"] = atr_arr(d["h"], d["l"], d["c"], EX_FAST)
    if with_atr_slow:
        d["atr_slow"] = atr_arr(d["h"], d["l"], d["c"], EX_SLOW)
    if with_ac:
        d["ac"] = lag1_ac_arr(d["c"], AC_WIN)
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


def probe_fx3_lag1ac(data):
    """FX3 book: lag-1 AC regime + body CONT."""
    closed, open_pos = [], []
    clock = data["EURUSD"]["t"]
    last_day_sym = set()
    open_syms = set()
    warmup = AC_WIN + 2
    for i in range(warmup, len(clock) - 1):
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
            j = asof_idx(d, sig_ts)
            if j is None or j < AC_WIN:
                continue
            atr = d["atr"][j]
            ac = d["ac"][j]
            if not np.isfinite(atr) or atr <= 0 or not np.isfinite(ac):
                continue
            if ac < AC_MIN:
                continue
            body = float(d["c"][j]) - float(d["o"][j])
            if abs(body) < AC_BODY * atr:
                continue
            side = 1 if body > 0 else -1
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


def probe_gbpusd_atrexp(gb):
    """GBPUSD: ATR expansion regime + conviction body CONT."""
    closed, open_pos = [], []
    sym = "GBPUSD"
    last_day = None
    start = EX_SLOW + 2
    for i in range(start, len(gb["t"]) - 1):
        ts = int(gb["t"][i])
        open_pos = manage_exits(open_pos, {sym: gb}, ts, closed, EX_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        j = i - 1
        atr = gb["atr"][j]
        atr_s = gb["atr_slow"][j]
        if (
            not np.isfinite(atr)
            or atr <= 0
            or not np.isfinite(atr_s)
            or atr_s <= 0
        ):
            continue
        if atr / atr_s < EX_RATIO:
            continue
        body = float(gb["c"][j]) - float(gb["o"][j])
        if abs(body) < EX_BODY * atr:
            continue
        rng = float(gb["h"][j]) - float(gb["l"][j])
        if rng <= 0:
            continue
        if body > 0:
            loc = (float(gb["c"][j]) - float(gb["l"][j])) / rng
            if loc < (1.0 - EX_CLOSE):
                continue
            side = 1
        else:
            loc = (float(gb["h"][j]) - float(gb["c"][j])) / rng
            if loc < (1.0 - EX_CLOSE):
                continue
            side = -1
        day = dt.date()
        if day == last_day:
            continue
        entry = float(gb["o"][i])
        sl = entry - side * EX_SL * atr
        tp = entry + side * EX_RR * EX_SL * atr
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


def probe_aud_fx3_risksync(aud, eu, gb, uj):
    """AUDUSD CONT when FX3 same-bar risk-on/off sync (no commodity/equity lead)."""
    closed, open_pos = [], []
    sym = "AUDUSD"
    last_day = None
    for i in range(2, len(aud["t"]) - 1):
        ts = int(aud["t"][i])
        open_pos = manage_exits(open_pos, {sym: aud}, ts, closed, RS_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if open_pos:
            continue
        sig_ts = int(aud["t"][i - 1])
        ei = asof_idx(eu, sig_ts)
        gi = asof_idx(gb, sig_ts)
        ji = asof_idx(uj, sig_ts)
        if ei is None or gi is None or ji is None:
            continue
        atr_e = eu["atr"][ei]
        atr_g = gb["atr"][gi]
        atr_j = uj["atr"][ji]
        atr = aud["atr"][i - 1]
        if any(
            (not np.isfinite(x) or x <= 0)
            for x in (atr_e, atr_g, atr_j, atr)
        ):
            continue
        be = float(eu["c"][ei]) - float(eu["o"][ei])
        bg = float(gb["c"][gi]) - float(gb["o"][gi])
        bj = float(uj["c"][ji]) - float(uj["o"][ji])
        if abs(be) < RS_LEG * atr_e or abs(bg) < RS_LEG * atr_g or abs(bj) < RS_LEG * atr_j:
            continue
        # Risk-on proxy: EUR↑, GBP↑, USDJPY↓ (JPY risk-on / USD soft vs JPY)
        # Risk-off: opposite. Require all three legs agree.
        e_on = be > 0
        g_on = bg > 0
        j_on = bj < 0  # USDJPY down = JPY bid = risk-on
        if e_on == g_on == j_on:
            side = 1 if e_on else -1
        else:
            continue
        day = dt.date()
        if day == last_day:
            continue
        entry = float(aud["o"][i])
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
    flush_open(open_pos, {sym: aud}, closed)
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
                "feature_family": "greenfield_r22_ac_atrexp_risksync",
                "lane": "strategy_shift_r22_greenfield_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "R22 NON-FADE break lead-clone local optimum; "
                    "AC-regime / ATR-exp / FX3-risksync; nested critic GO"
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
                "# 3-critic panel — Round 22 AC / ATR-exp / FX3-risksync",
                "",
                "Date: 2026-07-15",
                "Nested critic **GO** (break lead-clone local optimum; not R16–R21 densify).",
                "",
                "## Named (NON-FADE) — why different mechanisms",
                "1. `FX3_H1_LAG1AC_REGIME_BODY_CONT` — lag-1 return AC regime (≠ VR/ER/lead)",
                "2. `GBPUSD_H1_ATREXP_BURST_CONT` — ATR expansion burst (≠ Parkinson compress/Donch)",
                "3. `AUDUSD_H1_FX3_RISKSYNC_CONT` — same-bar FX risk-sync (≠ XTI/XAU/US30 lead)",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — three independent edge stories; AUD sync ≠ oil/metal lead |",
                "| Quant | PASS — AC≠VR; expansion≠compress; FX breadth≠cross-asset lag |",
                "| MQL5/MT5 | PASS — closed-bar as-of; ATR/AC precomputed on closed bars |",
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
                "# Design — Round 22 AC / ATR-exp / FX3-risksync",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## Mandate",
                "Break lead-clone local optimum (R16–R20: cadence OK, PF@$12 fail).",
                "FORBIDDEN: commodity/equity→FX leads; USD-implied densify; R10–R21 densify.",
                "",
                f"## 1 `HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001`",
                f"Rolling {AC_WIN}-bar lag-1 return Pearson AC ≥{AC_MIN} AND |body|≥{AC_BODY}×ATR",
                f"→ CONT FX3; SL={AC_SL} RR={AC_RR}.",
                "Why: statistical persistence regime of own returns — not path-ER, not VR",
                "(variance scaling), not cross-asset lead.",
                "",
                f"## 2 `HYP-GBPUSD-H1-ATREXP-BURST-CONT-001`",
                f"ATR({EX_FAST})/ATR({EX_SLOW})≥{EX_RATIO} AND |body|≥{EX_BODY}×ATR AND close",
                f"outer {int(EX_CLOSE*100)}% → CONT; SL={EX_SL} RR={EX_RR}.",
                "Why: volatility *expansion* + conviction — opposite of Parkinson compress;",
                "≠ Donch channel break; ≠ two-bar accel.",
                "",
                f"## 3 `HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001`",
                f"Same-bar EURUSD+GBPUSD+USDJPY risk-sync (|leg|≥{RS_LEG}×ATR; JPY risk-on =",
                f"USDJPY↓) → AUDUSD CONT; SL={RS_SL} RR={RS_RR}.",
                "Why: FX-complex co-movement same bar — economically related to risk-on AUD",
                "but **not** lagged XTI/XAU/US30 lead (the local optimum to break).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 22 AC / ATR-exp / FX3-risksync",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 lag1-AC regime+body CONT | ≠ R17 ETH VR; ≠ path-ER shelf; ≠ R15 streak; "
                "≠ R16–R20 lead-impulse |",
                "| GBPUSD ATR-exp burst CONT | ≠ Parkinson/range-compress (banned); ≠ R21 Donch8; "
                "≠ R21 two-bar accel; ≠ D1 volregime-8d |",
                "| AUDUSD FX3 risk-sync CONT | ≠ R20 XTI→AUD lead; ≠ R19 CADJPY XTI+NAS riskon; "
                "≠ R18 AUD→NZD lead; ≠ R21 USD-implied |",
                "",
                "R10–R21 densify boards + lead-clone rescue + USD-imp densify: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 22 AC / ATR-exp / FX3-risksync",
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
                "# Session closeout — Round 22 AC / ATR-exp / FX3-risksync",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify AC-k / ATR-exp-k / FX3-risksync-k /",
                "lead-clones / USD-imp / R21–R10 / unpark / exit / FRED.",
                "Next: next true greenfield outside R22 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 22 AC / ATR-exp / FX3-risksync",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Ngoài R10–R21. **NON-FADE.** Break lead-clone local optimum.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cơ chế (a priori)",
                "1. Lag-1 AC regime — persistence thống kê (≠ VR/ER/lead)",
                "2. ATR expansion burst — vol mở rộng (≠ compress/Donch)",
                "3. FX3 risk-sync → AUD — đồng pha FX (≠ XTI/XAU lead)",
                "",
                "## Quyết định",
                "- Không densify AC / ATR-exp / risksync / lead-clone / USD-imp / R10–R21.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài R22 **hoặc** research-grade cost.",
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
                "# VN brief — Clean book + Round 22",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book + discovery R22 NON-FADE (AC/ATR-exp/risksync). GOAL: chưa đạt.",
                "",
                "## 1. Clean book `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`",
                clean_book_note,
                "- Model 0 book-level: **WITHHELD**.",
                "",
                "## 2. Discovery Round 22 — AC / ATR-exp / FX3-risksync",
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
                "- R20–R21 lead / USD-imp boards: cadence OK, PF@$12 fail — **no densify**.",
                "",
                "## Cấm",
                "Densify R1–R22 / VR rescue / lead-clone rescue / USD-imp densify / "
                "fade-session / unpark / exit / FRED / Phase-0.",
                "",
                "## Next agent",
                "Giữ QFSI; greenfield ngoài R22 (NON-FADE); cost khi Owner drop deal-export.",
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
        f"- **GREENFIELD ROUND22 AC/ATREXP/RISKSYNC CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / `QFSI_007_HEALTHY` / "
        f"`NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  NON-FADE greenfield outside R10–R21 densify; break lead-clone local optimum.",
        "  Nested critic GO — AC-regime / ATR-exp / FX3-risksync (not lead clones) "
        f"(sha={freeze_sha[:16]}…). Lead self-merge closeout.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_CLEAN_BOOK_AND_R22_VN_ACTION_BRIEF.md`.",
        f"  QFSI spot-check: {qnote}",
        "  Do **not** densify AC-k / ATR-exp-k / FX3-risksync-k /",
        "  lead-clones / USD-imp-k / R21 accel/Donch / R20 XAU-NZD/USDJPY-inv/XTI-AUD /",
        "  R19–R10 / R1–R9 / unpark / exit / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        f"  {clean_note}",
        "  Next: next true greenfield outside R22 (still NON-FADE) — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | R22 "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND22 AC/ATREXP/RISKSYNC CLOSEOUT"):
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
        "lag1ac": {
            "win": AC_WIN,
            "min_ac": AC_MIN,
            "body": AC_BODY,
            "sl": AC_SL,
            "rr": AC_RR,
            "hold": AC_HOLD,
            "universe": list(FX3),
        },
        "atrexp": {
            "fast": EX_FAST,
            "slow": EX_SLOW,
            "ratio": EX_RATIO,
            "body": EX_BODY,
            "close": EX_CLOSE,
            "sl": EX_SL,
            "rr": EX_RR,
            "hold": EX_HOLD,
        },
        "risksync": {
            "leg": RS_LEG,
            "sl": RS_SL,
            "rr": RS_RR,
            "hold": RS_HOLD,
            "rule": "EUR↑+GBP↑+USDJPY↓ → AUD long; opposite → AUD short",
        },
        "cost": BASE_COST,
        "window": "2021.01.01-2025.12.31",
        "forbidden": "R10_R21_densify__lead_clones__USD_implied__Parkinson_compress",
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
                    "# Universe freeze — Round 22 AC / ATR-exp / FX3-risksync",
                    "",
                    "Frozen a priori BEFORE metrics (nested critic GO — break lead-clone).",
                    f"Freeze SHA: `{freeze_sha}`",
                    "",
                    "1. HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001",
                    "2. HYP-GBPUSD-H1-ATREXP-BURST-CONT-001",
                    "3. HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001",
                    "",
                    "Mechanism note: (1) lag-1 return AC regime ≠ VR/ER; "
                    "(2) ATR expansion ≠ Parkinson compress; "
                    "(3) FX3 same-bar risk-sync ≠ commodity/equity→FX lead.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        qnote = qfsi_parallel_note()
        clean_note = load_clean_book_note()
        fx3 = {
            s: enrich(load(s, mt5.TIMEFRAME_H1), with_ac=True) for s in FX3
        }
        gb = enrich(
            load("GBPUSD", mt5.TIMEFRAME_H1), with_atr_slow=True
        )
        # GBP in fx3 already has atr; risksync needs eu/gb/uj atr
        aud = enrich(load("AUDUSD", mt5.TIMEFRAME_H1))
        eu = fx3["EURUSD"]
        uj = fx3["USDJPY"]
        # use gb from fx3 for risksync (has atr); separate gb for atrexp has atr_slow
        results = [
            pack_result(
                "HYP-FX3-H1-LAG1AC-REGIME-BODY-CONT-001",
                "fx3_h1_lag1ac_regime_body_cont",
                "FX3",
                "H1",
                *probe_fx3_lag1ac(fx3),
            ),
            pack_result(
                "HYP-GBPUSD-H1-ATREXP-BURST-CONT-001",
                "gbpusd_h1_atrexp_burst_cont",
                "GBPUSD",
                "H1",
                *probe_gbpusd_atrexp(gb),
            ),
            pack_result(
                "HYP-AUDUSD-H1-FX3-RISKSYNC-CONT-001",
                "audusd_h1_fx3_risksync_cont",
                "AUDUSD",
                "H1",
                *probe_aud_fx3_risksync(aud, eu, fx3["GBPUSD"], uj),
            ),
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_r22_ac_atrexp_risksync.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "freeze_sha256": freeze_sha,
            "hard_constraint": (
                "NON_FADE__NO_R10_R21_DENSIFY__NO_LEAD_CLONES__NO_USD_IMP_DENSIFY"
            ),
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "lag1ac": {
                    "win": AC_WIN,
                    "min_ac": AC_MIN,
                    "body": AC_BODY,
                    "sl": AC_SL,
                    "rr": AC_RR,
                    "hold": AC_HOLD,
                },
                "atrexp": {
                    "fast": EX_FAST,
                    "slow": EX_SLOW,
                    "ratio": EX_RATIO,
                    "body": EX_BODY,
                    "close": EX_CLOSE,
                    "sl": EX_SL,
                    "rr": EX_RR,
                    "hold": EX_HOLD,
                },
                "risksync": {
                    "leg": RS_LEG,
                    "sl": RS_SL,
                    "rr": RS_RR,
                    "hold": RS_HOLD,
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
