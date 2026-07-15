#!/usr/bin/env python3
"""Round 3 greenfield joint screen — break thick∩cadence dichotomy.

Outside densify:
  ≠ majority/TS/spring/PB/AONIA/CORRA/thin3/exit/FRED/LNY/XS
  ≠ bodyATR portfolio / mother / Asia-coil / carry / calendar / consec / CLOSELOC backup

A priori (≥2), +$12, Model 0 only if PROBE_SURVIVOR:
  1) HYP-FX3-H4-SOLO-LEADER-CONT-001
  2) HYP-FX3-H4DISP-H1-ACCEPT-CONT-001

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

OUT_JSON = PRE / "20260715_GREENFIELD_SOLO_ACCEPT_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_SOLO_ACCEPT_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_SOLO_ACCEPT_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_SOLO_ACCEPT_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_SOLO_ACCEPT_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_SOLO_ACCEPT_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Solo leader H4 ---
SOLO_LEAD_MIN = 0.55
SOLO_PEER_MAX = 0.22
SOLO_OUTER = 0.30
SOLO_SL_ATR = 1.20
SOLO_RR = 2.5
SOLO_HOLD = 6
SOLO_MAX_OPEN = 1
SOLO_MAX_PER_DAY = 1

# --- H4 displace → H1 accept ---
DISP_BODY = 0.50
DISP_OUTER = 0.25
ACCEPT_WINDOW = 3  # H1 bars after H4 close
ACCEPT_BODY = 0.30
ACCEPT_OUTER = 0.30
ACCEPT_SL_ATR = 1.15
ACCEPT_RR = 2.5
ACCEPT_HOLD = 12
ACCEPT_MAX_PER_DAY = 1
ACCEPT_BOOK_MAX = 2


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


def usd_signed_body(sym, o, c, atr):
    """Positive = USD strength (EURUSD/GBPUSD down, USDJPY up)."""
    body = (c - o) / atr
    if sym in ("EURUSD", "GBPUSD"):
        return -body
    return body


def probe_solo_leader(data):
    """Solo H4 leader with quiet peers → continue on leader."""
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    funnel = {"n_bars": 0, "n_solo": 0, "n_trades": 0}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, SOLO_HOLD)
        if dt.weekday() >= 5 or len(open_pos) >= SOLO_MAX_OPEN:
            continue
        j = i - 1  # signal = last closed H4
        if j < 20:
            continue
        funnel["n_bars"] += 1
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= SOLO_MAX_PER_DAY:
            continue

        scores = {}
        locs = {}
        atrs = {}
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
            o, h, l, c = d["o"][idx], d["h"][idx], d["l"][idx], d["c"][idx]
            scores[sym] = usd_signed_body(sym, o, c, atr)
            locs[sym] = close_loc(o, h, l, c)
            atrs[sym] = atr
        if not ok:
            continue

        leader = max(scores, key=lambda s: abs(scores[s]))
        lead_s = scores[leader]
        if abs(lead_s) < SOLO_LEAD_MIN:
            continue
        peers = [s for s in FX3 if s != leader]
        if any(abs(scores[p]) >= SOLO_PEER_MAX for p in peers):
            continue

        # Directional outer close on leader in price terms
        dL = data[leader]
        idxL = int(np.searchsorted(dL["t"], clock[j], side="left"))
        o, h, l, c = dL["o"][idxL], dL["h"][idxL], dL["l"][idxL], dL["c"][idxL]
        loc = locs[leader]
        # Price side continues WITH leader body sign (not USD-normalized)
        price_side = 1 if c > o else -1
        if price_side > 0 and loc < (1.0 - SOLO_OUTER):
            continue
        if price_side < 0 and loc > SOLO_OUTER:
            continue

        funnel["n_solo"] += 1
        e_i = int(np.searchsorted(dL["t"], ts, side="left"))
        if e_i >= len(dL["t"]) or dL["t"][e_i] != ts:
            continue
        if any(p["sym"] == leader for p in open_pos):
            continue

        entry = float(dL["o"][e_i])
        atr = atrs[leader]
        sl = entry - price_side * SOLO_SL_ATR * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + price_side * SOLO_RR * risk
        open_pos.append(
            {
                "sym": leader,
                "side": price_side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots(leader, entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def align_h4_idx(h4_t, ts):
    idx = int(np.searchsorted(h4_t, ts, side="right")) - 1
    return idx


def probe_h4disp_h1_accept(h4, h1):
    """H4 displacement → H1 accept beyond H4 close (no PB path)."""
    closed = []
    clock = h1["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    arms = {s: None for s in FX3}
    last_arm_h4 = {s: -1 for s in FX3}
    funnel = {"n_arms": 0, "n_accept": 0, "n_invalid": 0, "n_expire": 0, "n_trades": 0}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, h1, ts, closed, ACCEPT_HOLD)

        for sym in FX3:
            d4 = h4[sym]
            closed_before = ts - 4 * 3600
            k = align_h4_idx(d4["t"], closed_before)
            if k < 20 or k <= last_arm_h4[sym]:
                continue
            atr4 = d4["atr"][k]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            o, h, l, c = d4["o"][k], d4["h"][k], d4["l"][k], d4["c"][k]
            body = abs(c - o)
            loc = close_loc(o, h, l, c)
            if body < DISP_BODY * atr4:
                continue
            bull = c > o
            if not (
                (bull and loc >= (1.0 - DISP_OUTER))
                or ((not bull) and loc <= DISP_OUTER)
            ):
                continue
            # Arm once per qualifying closed H4
            last_arm_h4[sym] = k
            arms[sym] = {
                "side": 1 if bull else -1,
                "h4_close": float(c),
                "mid": (h + l) / 2.0,
                "atr4": atr4,
                "h4_i": k,
                "h4_t": int(d4["t"][k]),
                "h1_seen": 0,
            }
            funnel["n_arms"] += 1

        if dt.weekday() >= 5:
            continue
        open_syms = {p["sym"] for p in open_pos}
        day = dt.date().isoformat()

        for sym in FX3:
            a = arms[sym]
            if a is None:
                continue
            d1 = h1[sym]
            idx = int(np.searchsorted(d1["t"], ts, side="left"))
            if idx < 30 or d1["t"][idx] != ts:
                continue
            j = idx - 1  # closed H1 signal on this symbol
            if j < 1 or d1["t"][j] < a["h4_t"] + 4 * 3600:
                continue
            # Count only this symbol's post-H4 closed H1 bars
            a["h1_seen"] += 1
            if a["h1_seen"] > ACCEPT_WINDOW:
                funnel["n_expire"] += 1
                arms[sym] = None
                continue

            atr1 = d1["atr"][j]
            if not np.isfinite(atr1) or atr1 <= 0:
                continue
            o1, h1b, l1b, c1 = d1["o"][j], d1["h"][j], d1["l"][j], d1["c"][j]
            if a["side"] > 0 and c1 < a["mid"]:
                funnel["n_invalid"] += 1
                arms[sym] = None
                continue
            if a["side"] < 0 and c1 > a["mid"]:
                funnel["n_invalid"] += 1
                arms[sym] = None
                continue

            body = abs(c1 - o1)
            loc = close_loc(o1, h1b, l1b, c1)
            if body < ACCEPT_BODY * atr1:
                continue
            if a["side"] > 0:
                if c1 <= a["h4_close"] or loc < (1.0 - ACCEPT_OUTER):
                    continue
            else:
                if c1 >= a["h4_close"] or loc > ACCEPT_OUTER:
                    continue

            funnel["n_accept"] += 1
            if (
                sym in open_syms
                or len(open_pos) >= ACCEPT_BOOK_MAX
                or day_count.get((day, sym), 0) >= ACCEPT_MAX_PER_DAY
            ):
                arms[sym] = None
                continue

            entry = float(d1["o"][idx])
            side = a["side"]
            sl = entry - side * ACCEPT_SL_ATR * atr1
            risk = abs(entry - sl)
            if risk <= 0:
                arms[sym] = None
                continue
            tp = entry + side * ACCEPT_RR * risk
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": risk_lots(sym, entry, sl),
                    "bars": 0,
                }
            )
            open_syms.add(sym)
            day_count[(day, sym)] = day_count.get((day, sym), 0) + 1
            funnel["n_trades"] += 1
            arms[sym] = None

    flush_open(open_pos, h1, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def write_all(results, receipt, any_surv):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Solo-leader + H4-displace H1-accept (Round 3)",
                "",
                "Date: 2026-07-15",
                "Parent: Round1 thick ALL_KILL + Round2 quality ALL_KILL.",
                "Nested critic `cursor-grok-4.5-high-fast`.",
                "Goal: break thick∩cadence dichotomy without densify banned shelves.",
                "",
                "## Why these (vs Round1–2 failure modes)",
                "- Round1 (majority/TS): co-moving / soft-band thick → PF/stress die.",
                "- Round2 (spring/PB): rare auction geometries → cadence starve (~0.5 tpw).",
                "- Round3 targets mid-frequency + dual quality gates.",
                "",
                "## 1 `HYP-FX3-H4-SOLO-LEADER-CONT-001`",
                "Leader |signed_body/ATR|≥0.55; both peers |s|<0.22; leader close outer 30%;",
                "enter WITH leader next H4. SL=1.20 ATR; RR2.5; hold≤6; MaxOpen=1; MaxPerDay=1.",
                "Mechanism: opposite of majority — idiosyncratic solo repricing, not USD thrash.",
                "",
                "## 2 `HYP-FX3-H4DISP-H1-ACCEPT-CONT-001`",
                "Arm H4 body≥0.50 ATR outer 25%; accept ≤3 H1: close beyond H4 close same dir,",
                "H1 body≥0.30 ATR outer 30%; invalidate on mid repair (no PB path).",
                "SL=1.15 ATR; RR2.5; hold≤12 H1; MaxPerDay=1/sym; book≤2.",
                "Mechanism: continuation handshake denser than spring/PB rarity.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. Hold CLOSELOC backup unused. No densify knobs.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 3 solo-leader + H4disp H1-accept",
                "",
                "| Object | Vs recent killboard |",
                "|---|---|",
                "| Solo-leader cont | ≠ USD-majority-lag (agreement→laggard); here quiet peers→leader. ≠ TSMOM/bodyATR. ≠ XS residual/mom z. ≠ AONIA/CORRA/thin3. ≠ spring/PB. ≠ CLOSELOC backup. |",
                "| H4disp→H1 accept | ≠ PB-reclaim (forbids mid repair; no depth band). ≠ spring fade. ≠ CLOSELOC H1-only pressure. ≠ mother/Asia-coil/LNY. ≠ majority/TS/thin3/consec/calendar/carry/D1/swing/XS/bodyATR. |",
                "",
                "CLOSELOC-PRESSURE backup remains held unused.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline — Round 3 solo-leader + H4disp H1-accept",
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
                "# Closeout — Round 3 solo + accept greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do not densify solo peer/lead ATR / accept window / RR / majority / TS / spring / PB / AONIA / CORRA / thin3.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 3 solo-leader + H4disp H1-accept",
                f"- `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify solo/accept / majority/TS/spring/PB / AONIA/CORRA/thin3/exit/FRED/LNY/XS.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Rewrite session brief with full Round1–3
    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D post AONIA kill (greenfield rounds)",
                "",
                "Thời điểm: 2026-07-15 ~12:30 ICT",
                "Không densify AONIA/CORRA/thin3/majority/TS/spring/PB/exit/FRED/LNY/XS.",
                "Không idle chờ cost (QFSI song song).",
                "",
                "## Round 1 — USD lag + TS-mom (thick path)",
                "De-dup: ≠ XS residual fade; ≠ swing ADX/D1 volregime; ≠ AONIA/CORRA/thin3.",
                "",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                "| `HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001` | 690 | 0.948 | 2.65 | 0.874 | KILL (pf+stress) |",
                "| `HYP-FX3-H4-TSMOM-BAND-CONT-001` | 2263 | 1.167 | 8.68 | 1.098 | KILL (pf+stress; thick near-miss) |",
                "",
                "Receipt `D71CC8F52A4C4B45FE231FBDDF6650CCFF1DF37D1CF306AB9BA947FBA21F3561`",
                "",
                "## Round 2 — spring fail-break + H4-bias PB-reclaim (quality path)",
                "De-dup: ≠ consec3 fade; ≠ TS densify; ≠ majority lag; ≠ LNY densify.",
                "",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                "| `HYP-FX3-H4-TRENDDAY-FAILBREAK-SPRING-001` | 122 | 1.319 | 0.47 | 1.235 | KILL (cadence+stress; PF ok) |",
                "| `HYP-FX3-H4BIAS-H1-PB-RECLAIM-CONT-001` | 154 | 1.228 | 0.59 | 1.156 | KILL (pf+cadence+stress) |",
                "",
                "Receipt `C336051FFFEB1A1506C4E34E0E8D3F8F61F5929A6E8AE7CC6E9C3F09498E7E5C`",
                "",
                "## Round 3 — solo-leader + H4disp→H1 accept (break dichotomy)",
                "Thiết kế: mid-freq + dual gate. Solo = ngược majority; Accept = continuation handshake ≠ PB/spring.",
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
                "- Không densify solo peer/lead / accept window / majority/TS/spring/PB/AONIA/CORRA/thin3.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next EV: true greenfield ngoài killboard nếu ALL_KILL — không densify shelves.",
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
                        "parent_candidate": "post_round2_spring_pbreclaim_20260715",
                        "feature_family": "greenfield_solo_accept_r3",
                        "lane": "greenfield_solo_accept_20260715",
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
        f"- **GREENFIELD ROUND3 SOLO+ACCEPT CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Break thick∩cadence dichotomy after Round1–2 ALL_KILL.",
        "  Nested critic `cursor-grok-4.5-high-fast`. Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_SOLO_ACCEPT_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_SOLO_ACCEPT_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`.",
        "  Do **not** densify solo peer/lead / accept window / majority / TS / spring / PB /",
        "  AONIA / CORRA / thin3 / exit / FRED / LNY / XS.",
        "  Next: next true greenfield outside killboard — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round3 solo+accept greenfield "
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
        h1 = {}
        for s in FX3:
            d4 = load(s, mt5.TIMEFRAME_H4)
            d4["atr"] = atr_arr(d4["h"], d4["l"], d4["c"], 14)
            h4[s] = d4
            d1 = load(s, mt5.TIMEFRAME_H1)
            d1["atr"] = atr_arr(d1["h"], d1["l"], d1["c"], 14)
            h1[s] = d1

        pnls1, det1 = probe_solo_leader(h4)
        m1, hc1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, hc1)

        pnls2, det2 = probe_h4disp_h1_accept(h4, h1)
        m2, hc2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, hc2)

        results = [
            {
                "hypothesis_id": "HYP-FX3-H4-SOLO-LEADER-CONT-001",
                "setup_type": (
                    "H4 solo leader |s|≥0.55 peers<0.22 outer30% cont; "
                    "SL1.2 RR2.5 hold≤6"
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
                "hypothesis_id": "HYP-FX3-H4DISP-H1-ACCEPT-CONT-001",
                "setup_type": (
                    "H4 displace→H1 accept beyond H4 close ≤3bars; no mid-repair; "
                    "SL1.15 RR2.5 hold≤12"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4→H1",
                "metrics": m2,
                "haircuts": hc2,
                "verdict": v2,
                "fail_notes": n2,
                "detail": det2,
            },
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema": "greenfield_solo_accept_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "window": "2021.01.01-2025.12.31",
            "parent_kill": "Round1 thick + Round2 quality ALL_KILL",
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
