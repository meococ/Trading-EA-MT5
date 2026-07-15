#!/usr/bin/env python3
"""Round 5 greenfield joint screen — post R1–R4 dichotomy ALL_KILL.

Outside densify:
  ≠ majority/TS/spring/PB/AONIA/CORRA/thin3/exit/FRED/LNY/XS
  ≠ solo/accept/disp/ER/bodyATR/mother/CLOSELOC

A priori (≥2), +$12, Model 0 only if PROBE_SURVIVOR:
  1) HYP-FX3-H4-BOOKSPLIT-LEADER-CONT-001
  2) HYP-FX3-H4-IMPULSE-HALFBACK-HOLD-001

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

OUT_JSON = PRE / "20260715_GREENFIELD_SPLIT_HALFBACK_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_SPLIT_HALFBACK_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_SPLIT_HALFBACK_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_SPLIT_HALFBACK_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_SPLIT_HALFBACK_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_SPLIT_HALFBACK_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Book-split leader continuation ---
SPLIT_LEAD_MIN = 0.50
SPLIT_VS_MED = 0.25
SPLIT_CLIMAX = 0.85
SPLIT_SL = 1.20
SPLIT_RR = 2.5
SPLIT_HOLD = 6
SPLIT_MAX_OPEN = 1
SPLIT_MAX_PER_DAY = 1

# --- Impulse halfback hold ---
IMP_BODY = 0.55
IMP_OUTER = 0.25
IMP_RANGE = 0.80
HB_WINDOW = 2
HB_OUTER = 0.30
HB_SL_PAD = 0.10
HB_SL_CAP = 1.30
HB_RR = 2.5
HB_HOLD = 6
HB_MAX_PER_DAY = 1
HB_BOOK_MAX = 2


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


def usd_sign_from_r(sym, r):
    """+1 = USD strength from pair body r=(C-O)/ATR."""
    if abs(r) < 1e-12:
        return 0
    price_up = 1 if r > 0 else -1
    if sym in ("EURUSD", "GBPUSD"):
        return -price_up
    return price_up


def probe_booksplit_leader(data):
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    funnel = {"n_bars": 0, "n_split": 0, "n_climax_skip": 0, "n_trades": 0}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, SPLIT_HOLD)
        if dt.weekday() >= 4:  # Mon–Thu
            continue
        if len(open_pos) >= SPLIT_MAX_OPEN:
            continue
        j = i - 1
        if j < 20:
            continue
        funnel["n_bars"] += 1
        day = dt.date().isoformat()
        if day_count.get(day, 0) >= SPLIT_MAX_PER_DAY:
            continue

        rs = {}
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
            rs[sym] = (d["c"][idx] - d["o"][idx]) / atr
            atrs[sym] = atr
        if not ok:
            continue

        usd_signs = {sym: usd_sign_from_r(sym, rs[sym]) for sym in FX3}
        nonzero = [s for s in usd_signs.values() if s != 0]
        if len(nonzero) < 2:
            continue
        if len(set(nonzero)) < 2:
            continue  # all agree on USD
        funnel["n_split"] += 1

        lead = max(rs, key=lambda s: abs(rs[s]))
        r_lead = rs[lead]
        abs_vals = [abs(rs[s]) for s in FX3]
        if abs(r_lead) < SPLIT_LEAD_MIN:
            continue
        if abs(r_lead) - float(np.median(abs_vals)) < SPLIT_VS_MED:
            continue
        if abs(r_lead) >= SPLIT_CLIMAX:
            funnel["n_climax_skip"] += 1
            continue

        dL = data[lead]
        e_i = int(np.searchsorted(dL["t"], ts, side="left"))
        if e_i >= len(dL["t"]) or dL["t"][e_i] != ts:
            continue
        price_side = 1 if r_lead > 0 else -1
        entry = float(dL["o"][e_i])
        atr = atrs[lead]
        sl = entry - price_side * SPLIT_SL * atr
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + price_side * SPLIT_RR * risk
        open_pos.append(
            {
                "sym": lead,
                "side": price_side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": risk_lots(lead, entry, sl),
                "bars": 0,
            }
        )
        day_count[day] = day_count.get(day, 0) + 1
        funnel["n_trades"] += 1

    flush_open(open_pos, data, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def probe_impulse_halfback_hold(data):
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}
    arms = {s: None for s in FX3}
    funnel = {"n_impulse": 0, "n_hold": 0, "n_invalid": 0, "n_expire": 0, "n_trades": 0}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, HB_HOLD)
        j = i - 1
        if j < 20:
            continue

        # Update / create arms from newly closed impulse bars
        for sym in FX3:
            d = data[sym]
            idx = int(np.searchsorted(d["t"], clock[j], side="left"))
            if idx < 20 or d["t"][idx] != clock[j]:
                continue
            atr = d["atr"][idx]
            if not np.isfinite(atr) or atr <= 0:
                continue
            o, h, l, c = d["o"][idx], d["h"][idx], d["l"][idx], d["c"][idx]
            rng = h - l
            body = abs(c - o)
            loc = close_loc(o, h, l, c)
            a = arms[sym]

            # Age / invalidate existing arm using this closed bar
            if a is not None:
                age = idx - a["imp_i"]
                if age > HB_WINDOW:
                    funnel["n_expire"] += 1
                    arms[sym] = None
                    a = None
                elif a["side"] > 0 and c < a["mid"]:
                    funnel["n_invalid"] += 1
                    arms[sym] = None
                    a = None
                elif a["side"] < 0 and c > a["mid"]:
                    funnel["n_invalid"] += 1
                    arms[sym] = None
                    a = None
                elif a["side"] > 0 and c < a["imp_l"]:
                    funnel["n_invalid"] += 1
                    arms[sym] = None
                    a = None
                elif a["side"] < 0 and c > a["imp_h"]:
                    funnel["n_invalid"] += 1
                    arms[sym] = None
                    a = None

            # New impulse arm (only if none active)
            if arms[sym] is None and body >= IMP_BODY * atr and rng >= IMP_RANGE * atr:
                bull = c > o
                if (bull and loc >= (1.0 - IMP_OUTER)) or (
                    (not bull) and loc <= IMP_OUTER
                ):
                    arms[sym] = {
                        "side": 1 if bull else -1,
                        "imp_i": idx,
                        "imp_h": h,
                        "imp_l": l,
                        "mid": (h + l) / 2.0,
                        "atr": atr,
                        "outer_hi": l + (1.0 - HB_OUTER) * rng if bull else None,
                        "outer_lo": h - (1.0 - HB_OUTER) * rng if (not bull) else None,
                    }
                    # For bull: outer 30% means loc >= 0.70 → close >= l+0.7*rng
                    if bull:
                        arms[sym]["outer_floor"] = l + (1.0 - HB_OUTER) * rng
                    else:
                        arms[sym]["outer_ceil"] = h - (1.0 - HB_OUTER) * rng
                    funnel["n_impulse"] += 1

            # Halfback hold trigger on this closed bar (not the impulse bar itself)
            a = arms[sym]
            if a is None or idx == a["imp_i"]:
                continue
            age = idx - a["imp_i"]
            if age < 1 or age > HB_WINDOW:
                continue

            held = False
            if a["side"] > 0:
                # touched mid or below (halfback) but closed back in outer third
                if l <= a["mid"] and c >= a["outer_floor"] and c >= a["mid"]:
                    held = True
            else:
                if h >= a["mid"] and c <= a["outer_ceil"] and c <= a["mid"]:
                    held = True
            if not held:
                continue
            funnel["n_hold"] += 1

            if dt.weekday() >= 5:
                arms[sym] = None
                continue
            if len(open_pos) >= HB_BOOK_MAX:
                arms[sym] = None
                continue
            day = dt.date().isoformat()
            if day_count.get((day, sym), 0) >= HB_MAX_PER_DAY:
                arms[sym] = None
                continue
            if any(p["sym"] == sym for p in open_pos):
                arms[sym] = None
                continue

            e_i = int(np.searchsorted(d["t"], ts, side="left"))
            if e_i >= len(d["t"]) or d["t"][e_i] != ts:
                arms[sym] = None
                continue
            entry = float(d["o"][e_i])
            side = a["side"]
            if side > 0:
                sl_raw = a["imp_l"] - HB_SL_PAD * a["atr"]
            else:
                sl_raw = a["imp_h"] + HB_SL_PAD * a["atr"]
            # Cap SL distance
            cap = HB_SL_CAP * a["atr"]
            if abs(entry - sl_raw) > cap:
                sl_raw = entry - side * cap
            risk = abs(entry - sl_raw)
            if risk <= 0:
                arms[sym] = None
                continue
            tp = entry + side * HB_RR * risk
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl_raw,
                    "tp": tp,
                    "lots": risk_lots(sym, entry, sl_raw),
                    "bars": 0,
                }
            )
            day_count[(day, sym)] = day_count.get((day, sym), 0) + 1
            funnel["n_trades"] += 1
            arms[sym] = None

    flush_open(open_pos, data, closed)
    pnls, detail = summarize(closed)
    detail["funnel"] = funnel
    return pnls, detail


def write_all(results, receipt, any_surv):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Book-split leader + Impulse halfback-hold (Round 5)",
                "",
                "Date: 2026-07-15",
                "Parent: Round1–4 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.",
                "",
                "## Why (vs R1–R4)",
                "- R4 fade died because extremes persist → R5 **follows** split leader.",
                "- R4 ER ≈ soft TS → R5 halfback is structural mid-reject, not path band.",
                "- R2 spring/PB rare → halfback mid-test is denser common event.",
                "- R3 solo needs quiet peers → split requires active disagreement.",
                "",
                "## 1 `HYP-FX3-H4-BOOKSPLIT-LEADER-CONT-001`",
                "USD-signs disagree; leader |r|≥0.50 and |r|−med(|r|)≥0.25; skip |r|≥0.85;",
                "WITH leader next H4. SL1.20 RR2.5 hold≤6 MaxOpen1 MaxPerDay1 Mon–Thu.",
                "",
                "## 2 `HYP-FX3-H4-IMPULSE-HALFBACK-HOLD-001`",
                "Impulse body≥0.55 ATR outer25% range≥0.80 ATR; within 2 H4 touch mid then",
                "close back outer30% same side mid; SL beyond impulse±0.10 (cap1.30) RR2.5.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No densify R1–R4 knobs.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 5 book-split + halfback-hold",
                "",
                "| Object | Vs killboard |",
                "|---|---|",
                "| Book-split leader cont | ≠ majority-lag; ≠ solo quiet-peers; ≠ bookdisp fade; ≠ XS z; ≠ TS/ER/accept |",
                "| Impulse halfback-hold | ≠ spring fail-pierce; ≠ H1 PB-reclaim; ≠ H4disp H1 accept; ≠ Outside/Engulf fade; ≠ consec3 fade; ≠ mother/NR7/Asia-coil |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline — Round 5 book-split + halfback-hold",
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
                "# Closeout — Round 5 split+halfback greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do not densify split/halfback / disp/ER/solo/accept / majority/TS/spring/PB / AONIA/CORRA/thin3.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 5 book-split + halfback-hold",
                f"- `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify split/halfback / R1–R4 shelves / AONIA/CORRA/thin3/exit/FRED/LNY/XS.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Compact session brief R1–R5
    def row_from_json(path):
        if not path.exists():
            return [], ""
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for x in payload["results"]:
            rows.append(
                f"| `{x['hypothesis_id']}` | {x['metrics']['n']} | {x['metrics']['pf']} | "
                f"{x['metrics']['tpw']} | {x['haircuts']['x1_5']['pf']} | KILL |"
            )
        return rows, payload.get("receipt_sha256", "")

    r3_rows, r3_rcpt = row_from_json(
        PRE / "20260715_GREENFIELD_SOLO_ACCEPT_OFFLINE_PROBES.json"
    )
    r4_rows, r4_rcpt = row_from_json(PRE / "20260715_GREENFIELD_DISP_ER_OFFLINE_PROBES.json")
    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D (greenfield R1–R5)",
                "",
                f"Thời điểm: 2026-07-15 ~{datetime.now().strftime('%H:%M')} ICT",
                "Không densify killboard. Không idle cost (QFSI song song).",
                "",
                "## Round 1 thick — majority + TSMOM → ALL_KILL",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                "| majority-lag | 690 | 0.948 | 2.65 | 0.874 | KILL |",
                "| TSMOM-band | 2263 | 1.167 | 8.68 | 1.098 | KILL |",
                "",
                "## Round 2 quality — spring + PB-reclaim → ALL_KILL",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                "| spring | 122 | 1.319 | 0.47 | 1.235 | KILL |",
                "| PB-reclaim | 154 | 1.228 | 0.59 | 1.156 | KILL |",
                "",
                "## Round 3 — solo + H4disp accept → ALL_KILL",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *r3_rows,
                f"Receipt `{r3_rcpt}`",
                "",
                "## Round 4 — bookdisp fade + path-ER → ALL_KILL",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *r4_rows,
                f"Receipt `{r4_rcpt}`",
                "",
                f"## Round 5 — book-split leader + halfback-hold → `{status}`",
                "| Object | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *[
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
                    f"{'SURVIVOR' if r['verdict'] == 'PROBE_SURVIVOR' else 'KILL'} |"
                    for r in results
                ],
                f"Receipt `{receipt}`",
                "",
                "## Quyết định",
                f"- {'Có' if any_surv else 'Zero'} Model 0.",
                "- Dichotomy thick↔quality vẫn sống qua 5 rounds — **không densify**.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next: true greenfield ngoài killboard.",
                "",
                "Login không headline. GOAL unmet.",
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
                        "parent_candidate": "post_round4_disp_er_20260715",
                        "feature_family": "greenfield_split_halfback_r5",
                        "lane": "greenfield_split_halfback_20260715",
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
        f"- **GREENFIELD ROUND5 SPLIT+HALFBACK CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Post R1–R4 dichotomy; nested critic `cursor-grok-4.5-high-fast`.",
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
        "  `preflight/20260715_GREENFIELD_SPLIT_HALFBACK_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_SPLIT_HALFBACK_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`.",
        "  Do **not** densify split/halfback / disp/ER/solo/accept / majority/TS/spring/PB /",
        "  AONIA/CORRA/thin3/exit/FRED/LNY/XS.",
        "  Next: next true greenfield outside killboard — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round5 split+halfback greenfield "
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

        pnls1, det1 = probe_booksplit_leader(h4)
        m1, hc1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, hc1)

        pnls2, det2 = probe_impulse_halfback_hold(h4)
        m2, hc2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, hc2)

        results = [
            {
                "hypothesis_id": "HYP-FX3-H4-BOOKSPLIT-LEADER-CONT-001",
                "setup_type": (
                    "H4 USD-sign split → leader |r| cont; SL1.2 RR2.5 Mon-Thu"
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
                "hypothesis_id": "HYP-FX3-H4-IMPULSE-HALFBACK-HOLD-001",
                "setup_type": (
                    "H4 impulse→halfback mid-reject hold; SL pad0.1 RR2.5 hold≤6"
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
            "schema": "greenfield_split_halfback_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "window": "2021.01.01-2025.12.31",
            "parent_kill": "Round1-4 ALL_KILL",
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
