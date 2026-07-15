#!/usr/bin/env python3
"""Round 4 greenfield joint screen — post R1–R3 dichotomy ALL_KILL.

Outside densify:
  ≠ majority/TS/spring/PB/AONIA/CORRA/thin3/exit/FRED/LNY/XS
  ≠ solo peer|lead / accept window / bodyATR / mother / CLOSELOC

A priori (≥2), +$12, Model 0 only if PROBE_SURVIVOR:
  1) HYP-FX3-H4-BOOKDISP-EXTREME-FADE-001
  2) HYP-FX3-H4-PATH-ER-CONT-001

Nested critic: cursor-grok-4.5-high-fast
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

OUT_JSON = PRE / "20260715_GREENFIELD_DISP_ER_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_DISP_ER_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_DISP_ER_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_DISP_ER_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_DISP_ER_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_DISP_ER_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Book dispersion extreme fade ---
DISP_EXT_MIN = 0.55
DISP_VS_MED = 0.40
DISP_SPREAD = 0.50
DISP_SL_ATR = 1.10
DISP_RR = 2.0
DISP_HOLD = 4
DISP_MAX_OPEN = 1
DISP_MAX_PER_DAY = 1
DISP_IMPULSE_KILL = 0.70  # next bar same-dir body/ATR → skip entry

# --- Path ER continuation ---
ER_LEN = 8
ER_MIN = 0.62
ER_BODY = 0.40
ER_OUTER = 0.30
ER_SL_ATR = 1.20
ER_RR = 2.5
ER_HOLD = 6
ER_MAX_OPEN_SYM = 1
ER_MAX_PER_DAY = 1
ER_BOOK_MAX = 2


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


def load(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"{symbol} tf={tf}: {mt5.last_error()}")
    return {
        "t": rates["time"].astype(np.int64),
        "o": rates["open"].astype(float),
        "h": rates["high"].astype(float),
        "l": rates["low"].astype(float),
        "c": rates["close"].astype(float),
    }


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


def close_loc(o, h, l, c):
    rng = h - l
    if rng <= 0:
        return 0.5
    return (c - l) / rng


def usd_side_of_price(sym, price_side):
    """Map price side to USD strength side: +1 = USD up."""
    if sym in ("EURUSD", "GBPUSD"):
        return -price_side
    return price_side


def probe_bookdisp_extreme_fade(data):
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    funnel = {"n_bars": 0, "n_arm": 0, "n_impulse_skip": 0, "n_trades": 0}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, DISP_HOLD)
        if dt.weekday() >= 4:  # Mon–Thu only (0–3); skip Fri/weekend
            continue
        if len(open_pos) >= DISP_MAX_OPEN:
            continue
        j = i - 1  # signal bar
        if j < 20:
            continue
        funnel["n_bars"] += 1
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= DISP_MAX_PER_DAY:
            continue

        rs = {}
        ok = True
        for sym in FX3:
            d = data[sym]
            idx = int(np.searchsorted(d["t"], clock[j], side="left"))
            if idx < 20 or d["t"][idx] != clock[j]:
                ok = False
                break
            atr = d["atr"][idx]
            if not np.isfinite(atr) or atr <= 0:
                ok = False
                break
            rs[sym] = (d["c"][idx] - d["o"][idx]) / atr
        if not ok:
            continue

        vals = list(rs.values())
        med = float(np.median(vals))
        ext = max(rs, key=lambda s: abs(rs[s]))
        r_ext = rs[ext]
        if abs(r_ext) < DISP_EXT_MIN:
            continue
        if abs(r_ext - med) < DISP_VS_MED:
            continue
        if (max(abs(v) for v in vals) - min(abs(v) for v in vals)) < DISP_SPREAD:
            continue
        funnel["n_arm"] += 1

        # Invalidate if entry bar (current open bar's prior = j is signal;
        # check the bar that just closed at j is extreme; entry at i.
        # Impulse persistence check uses the signal bar itself? Critic:
        # "Invalidate if next bar |body|/ATR ≥ 0.70 same dir" — next after extreme.
        # At entry time i, "next bar" after extreme j is the bar closing at... 
        # We enter at open of i, so we only know bars ≤ j. The invalidate is
        # on the bar AFTER extreme before entry — that's only available if we
        # wait one more bar. Interpret: skip if extreme bar itself already
        # climax? Better: require one confirmation bar k=j for arm, enter at
        # i = j+1 open, and the "next bar" check happens if we delay.
        # Frozen: enter next H4 open after extreme. Impulse kill = if the
        # entry bar's *previous* (extreme) is followed by... we can't see
        # future. Check at decision using only closed extreme: skip if
        # |r_ext| ≥ DISP_IMPULSE_KILL (already runaway).
        if abs(r_ext) >= DISP_IMPULSE_KILL:
            funnel["n_impulse_skip"] += 1
            continue

        dE = data[ext]
        e_i = int(np.searchsorted(dE["t"], ts, side="left"))
        if e_i >= len(dE["t"]) or dE["t"][e_i] != ts:
            continue
        atr = dE["atr"][int(np.searchsorted(dE["t"], clock[j], side="left"))]
        price_side = -1 if r_ext > 0 else 1  # fade against extreme
        entry = float(dE["o"][e_i])
        sl = entry - price_side * DISP_SL_ATR * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + price_side * DISP_RR * risk
        open_pos.append(
            {
                "sym": ext,
                "side": price_side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots(ext, entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def path_er(c, i, n=ER_LEN):
    if i < n:
        return None
    net = abs(c[i] - c[i - n])
    path = 0.0
    for k in range(i - n + 1, i + 1):
        path += abs(c[k] - c[k - 1])
    if path <= 0:
        return None
    return net / path


def probe_path_er_cont(data):
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    funnel = {"n_bars": 0, "n_arm": 0, "n_usd_cap": 0, "n_trades": 0}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, ER_HOLD)
        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= ER_BOOK_MAX:
            continue
        j = i - 1
        if j < ER_LEN + 5:
            continue
        funnel["n_bars"] += 1
        day = dt.date().isoformat()
        open_syms = {p["sym"] for p in open_pos}

        candidates = []
        for sym in FX3:
            if sym in open_syms:
                continue
            if day_count.get((day, sym), 0) >= ER_MAX_PER_DAY:
                continue
            d = data[sym]
            idx = int(np.searchsorted(d["t"], clock[j], side="left"))
            if idx < ER_LEN + 5 or d["t"][idx] != clock[j]:
                continue
            atr = d["atr"][idx]
            if not np.isfinite(atr) or atr <= 0:
                continue
            er = path_er(d["c"], idx, ER_LEN)
            if er is None or er < ER_MIN:
                continue
            o, h, l, c = d["o"][idx], d["h"][idx], d["l"][idx], d["c"][idx]
            body = abs(c - o)
            if body < ER_BODY * atr:
                continue
            loc = close_loc(o, h, l, c)
            price_side = 1 if c > o else -1
            if price_side > 0 and loc < (1.0 - ER_OUTER):
                continue
            if price_side < 0 and loc > ER_OUTER:
                continue
            candidates.append(
                {
                    "sym": sym,
                    "er": er,
                    "side": price_side,
                    "atr": atr,
                    "usd": usd_side_of_price(sym, price_side),
                }
            )

        if not candidates:
            continue
        funnel["n_arm"] += len(candidates)

        # USD exposure cap: if EUR+GBP both fire same USD dir, keep higher ER only
        eu = [c for c in candidates if c["sym"] in ("EURUSD", "GBPUSD")]
        if len(eu) == 2 and eu[0]["usd"] == eu[1]["usd"]:
            drop = min(eu, key=lambda x: x["er"])
            candidates = [c for c in candidates if c["sym"] != drop["sym"]]
            funnel["n_usd_cap"] += 1

        # Fill book by ER desc
        candidates.sort(key=lambda x: -x["er"])
        for cand in candidates:
            if len(open_pos) >= ER_BOOK_MAX:
                break
            if cand["sym"] in open_syms:
                continue
            d = data[cand["sym"]]
            e_i = int(np.searchsorted(d["t"], ts, side="left"))
            if e_i >= len(d["t"]) or d["t"][e_i] != ts:
                continue
            entry = float(d["o"][e_i])
            side = cand["side"]
            sl = entry - side * ER_SL_ATR * cand["atr"]
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + side * ER_RR * risk
            open_pos.append(
                {
                    "sym": cand["sym"],
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": risk_lots(cand["sym"], entry, sl),
                    "bars": 0,
                }
            )
            open_syms.add(cand["sym"])
            day_count[(day, cand["sym"])] = day_count.get((day, cand["sym"]), 0) + 1
            funnel["n_trades"] += 1

    flush_open(open_pos, data, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def write_all(results, receipt, any_surv):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Book-dispersion fade + Path-ER cont (Round 4)",
                "",
                "Date: 2026-07-15",
                "Parent: Round1–3 ALL_KILL (thick / quality / middle-death+thick).",
                "Nested critic `cursor-grok-4.5-high-fast`.",
                "",
                "## Why these break dichotomy (a priori)",
                "- R1 follow co-move / R3 solo-cont both die; Disp **fades** extreme vs book median.",
                "- R2 rare auction starves; Path-ER uses frequent path-shape state, not spring/PB.",
                "- R3 accept was soft handshake spam; ER skips low path-efficiency thrash.",
                "",
                "## 1 `HYP-FX3-H4-BOOKDISP-EXTREME-FADE-001`",
                "r=(C-O)/ATR; ext=argmax|r|; |r_ext|≥0.55; |r_ext−med|≥0.40; max|r|−min|r|≥0.50;",
                "skip if |r_ext|≥0.70 climax; fade against ext next H4. SL1.10 RR2 hold≤4;",
                "MaxOpen1 MaxPerDay1 Mon–Thu.",
                "",
                "## 2 `HYP-FX3-H4-PATH-ER-CONT-001`",
                "ER8≥0.62; body≥0.40 ATR; close outer 30%; WITH next H4. SL1.20 RR2.5 hold≤6;",
                "MaxPerDay1/sym book≤2; EUR+GBP same-USD → keep higher ER only.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No densify R1–R3 knobs.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 4 book-disp fade + path-ER",
                "",
                "| Object | Vs killboard |",
                "|---|---|",
                "| BookDisp extreme-fade | ≠ majority follow; ≠ solo-leader cont; ≠ XS z; ≠ spring/PB; ≠ consec3 fade; ≠ anticarry |",
                "| Path-ER cont | ≠ TSMOM band; ≠ bodyATR; ≠ H4disp→H1 accept; ≠ D1ADX/thrust; ≠ Outside/Engulf; ≠ NR7/mother/Asia-coil |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline — Round 4 book-disp + path-ER",
        "",
        f"Receipt `{receipt}`",
        f"Generated `{utc_now()}`",
        "Cost a priori +$12; gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['hypothesis_id']}",
            f"- **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
            f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']}",
            f"- detail={json.dumps(r['detail'])}",
            "",
        ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — Round 4 disp+ER greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do not densify disp thresholds / ER / solo / accept / majority / TS / spring / PB / AONIA / CORRA / thin3.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 4 book-disp fade + path-ER",
                f"- `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify disp/ER / solo/accept / majority/TS/spring/PB / AONIA/CORRA/thin3/exit/FRED/LNY/XS.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Full session brief R1–R4
    r3_json = PRE / "20260715_GREENFIELD_SOLO_ACCEPT_OFFLINE_PROBES.json"
    r3 = json.loads(r3_json.read_text(encoding="utf-8")) if r3_json.exists() else None
    r3_rows = ""
    if r3:
        for x in r3["results"]:
            r3_rows += (
                f"| `{x['hypothesis_id']}` | {x['metrics']['n']} | {x['metrics']['pf']} | "
                f"{x['metrics']['tpw']} | {x['haircuts']['x1_5']['pf']} | KILL |\n"
            )
    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D post AONIA kill (greenfield rounds)",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "Không densify AONIA/CORRA/thin3/majority/TS/spring/PB/solo/accept/disp/ER/exit/FRED/LNY/XS.",
                "Không idle chờ cost (QFSI song song).",
                "",
                "## Round 1 — USD lag + TS-mom (thick)",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                "| `HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001` | 690 | 0.948 | 2.65 | 0.874 | KILL |",
                "| `HYP-FX3-H4-TSMOM-BAND-CONT-001` | 2263 | 1.167 | 8.68 | 1.098 | KILL |",
                "",
                "## Round 2 — spring + PB-reclaim (quality)",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                "| `HYP-FX3-H4-TRENDDAY-FAILBREAK-SPRING-001` | 122 | 1.319 | 0.47 | 1.235 | KILL |",
                "| `HYP-FX3-H4BIAS-H1-PB-RECLAIM-CONT-001` | 154 | 1.228 | 0.59 | 1.156 | KILL |",
                "",
                "## Round 3 — solo-leader + H4disp→H1 accept",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                r3_rows.rstrip(),
                "",
                f"Receipt R3 `{r3['receipt_sha256'] if r3 else 'n/a'}`",
                "",
                "## Round 4 — book-disp fade + path-ER (break dichotomy)",
                f"Status: `{status}`",
                "",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *[
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
                    f"{'SURVIVOR' if r['verdict'] == 'PROBE_SURVIVOR' else 'KILL'} |"
                    for r in results
                ],
                "",
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                f"- {'Có' if any_surv else 'Zero'} Model 0.",
                "- Dichotomy vẫn là giả thuyết sống nếu ALL_KILL — **không densify** để ép joint.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next EV: true greenfield ngoài killboard.",
                "",
                "Login không phải headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(results, receipt):
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "killed"
                        if r["verdict"] != "PROBE_SURVIVOR"
                        else "probe_survivor",
                        "parent_candidate": "post_round3_solo_accept_20260715",
                        "feature_family": "greenfield_disp_er_r4",
                        "lane": "greenfield_disp_er_20260715",
                        "setup_type": r["setup_type"],
                        "symbol": r["symbol"],
                        "timeframe": r["timeframe"],
                        "window": "2021.01.01-2025.12.31",
                        "model": "offline_probe_only",
                        "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                        "metrics": {
                            "trades": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "pf_cost_x1_5": r["haircuts"]["x1_5"]["pf"],
                        },
                        "validation": {
                            "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace(
                                "\\", "/"
                            ),
                            "receipt_sha256": receipt,
                            "status": r["verdict"],
                            "dedup": str(OUT_DEDUP.relative_to(ROOT)).replace("\\", "/"),
                        },
                        "verdict": r["verdict"],
                        "reason": ",".join(r["fail_notes"]) or "offline_pass",
                        "updated_at": "2026-07-15",
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )


def patch_hot(results, receipt, any_surv):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD ROUND4 DISP+ER CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Post R1–R3 dichotomy; nested critic `cursor-grok-4.5-high-fast`.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_DISP_ER_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_DISP_ER_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`.",
        "  Do **not** densify disp/ER / solo/accept / majority/TS/spring/PB /",
        "  AONIA/CORRA/thin3/exit/FRED/LNY/XS.",
        "  Next: next true greenfield outside killboard — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round4 disp+ER greenfield "
            f"{status.split('__')[0]}; GOAL unmet"
        )
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        for s in FX3:
            mt5.symbol_select(s, True)
        h4 = {}
        for s in FX3:
            d4 = load(s, mt5.TIMEFRAME_H4)
            d4["atr"] = atr_arr(d4["h"], d4["l"], d4["c"], 14)
            h4[s] = d4

        pnls1, det1 = probe_bookdisp_extreme_fade(h4)
        m1, hc1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, hc1)

        pnls2, det2 = probe_path_er_cont(h4)
        m2, hc2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, hc2)

        results = [
            {
                "hypothesis_id": "HYP-FX3-H4-BOOKDISP-EXTREME-FADE-001",
                "setup_type": (
                    "H4 book dispersion extreme fade vs median; "
                    "SL1.1 RR2 hold≤4 Mon-Thu"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "metrics": m1,
                "haircuts": hc1,
                "verdict": v1,
                "fail_notes": n1,
                "detail": det1,
            },
            {
                "hypothesis_id": "HYP-FX3-H4-PATH-ER-CONT-001",
                "setup_type": (
                    "H4 Kaufman ER8≥0.62 + body/outer cont; "
                    "SL1.2 RR2.5 hold≤6 USD-cap"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "metrics": m2,
                "haircuts": hc2,
                "verdict": v2,
                "fail_notes": n2,
                "detail": det2,
            },
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema": "greenfield_disp_er_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "window": "2021.01.01-2025.12.31",
            "parent_kill": "Round1-3 ALL_KILL",
            "nested_critic": "cursor-grok-4.5-high-fast",
            "results": results,
            "any_survivor": any_surv,
            "model0_authorized": any_surv,
            "receipt_sha256": None,
        }
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        write_all(results, receipt, any_surv)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_survivor": any_surv,
                    "model0_authorized": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            **r["metrics"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["fail_notes"],
                            "detail": r["detail"],
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
