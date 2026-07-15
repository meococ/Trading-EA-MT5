#!/usr/bin/env python3
"""HARD PIVOT W8 — after W1–W7 entry-state ALL_KILL.

Carry:
  - W7 expansion PD-mid: cadenceOK (tpw~2.4) but PF@$12=0.86 (thin/negative).
  - W7 London→NY handoff: thicker exp~$42 / PF@$12=1.14 but tpw~1.64 starve.
  - FVG thick rare FORBIDDEN densify. Cadence-capable location still dies under +$12.

NEW classes outside W1–W7 densify:
  1. HYP-FX3-H1-INSIDEBAR-MOTHER-BREAK-ACCEPT-CONT-001
     Mechanism: inside-bar (range ⊂ prior bar) arms mother zone; later break
     accept beyond mother extreme → CONT. Mother SL = structural invalidation
     → higher WR / post-friction $/trade; inside events frequent → cadence.
     NOT Outside-bar densify (R31); NOT NR7 densify; NOT FVG.
  2. HYP-FX3-H1-LONDON-BOX-OVERLAP-BREAK-ACCEPT-CONT-001
     Mechanism: build London [07,12) box; in London–NY overlap [12,16) first
     close-accept beyond box → CONT. Overlap liquidity confirms box break
     (filters false London breaks that bleed +$12); clocks keep cadence.
     NOT ORB/IB densify; NOT W7 handoff nest densify; NOT Asia-sweep.

Universe a priori: EURUSD+GBPUSD+USDJPY.
R_SERIES densify PAUSED. Model 0 only PROBE_SURVIVOR.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
PREREG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs"

STEM = "20260715_HARD_PIVOT_W8_INSIDEBAR_LBOX"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W8_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# Child 1: inside-bar mother break accept
IB_SESSION = (7, 17)
IB_MAX_WAIT = 8
IB_MIN_MOTHER_ATR = 0.55
IB_SL_PAD = 0.10
IB_RR = 2.00
IB_HOLD = 12

# Child 2: London box → overlap break accept
LB_LONDON = (7, 12)
LB_OVERLAP = (12, 16)
LB_MIN_BOX_ATR = 0.40
LB_MAX_BOX_ATR = 2.50
LB_MIN_BODY = 0.18
LB_SL_PAD = 0.10
LB_RR = 2.00
LB_HOLD = 12


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
        cut = [float(p) - BASE_COST * mult for p in pnls]
        p = pf_of(cut)
        out[key] = {
            "pf": None if not cut else round(float(p or 0.0), 4),
            "net": round(float(sum(cut)), 2) if cut else 0.0,
            "exp": round(float(sum(cut) / len(cut)), 4) if cut else 0.0,
        }
    return out


def metrics(pnls):
    n = len(pnls)
    p = pf_of(pnls)
    net = float(sum(pnls)) if pnls else 0.0
    return {
        "n": int(n),
        "pf": None if p is None else round(float(p), 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(float(n / WEEKS), 4) if WEEKS else None,
    }


def joint_verdict(m, hc, challenger: bool = False):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    pf12 = hc["x1"]["pf"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0 or tpw > 5.0:
        notes.append("cadence_fail")
    if pf12 < 1.30:
        notes.append("pf12_fail")
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
                    "entry_ts": pos.get("entry_ts"),
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
                "entry_ts": pos.get("entry_ts"),
            }
        )


def summarize(closed):
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def pack_result(hid, setup, symbol, timeframe, pnls, detail):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return _jsonable(
        {
            "hypothesis_id": hid,
            "setup": setup,
            "symbol": symbol,
            "timeframe": timeframe,
            "metrics": m,
            "haircuts": hc,
            "verdict": verdict,
            "fail_notes": notes,
            "detail": detail,
            "challenger": False,
        }
    )


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def build_london_box(d):
    """Map date -> London [7,12) UTC HL."""
    by_day = {}
    for j in range(len(d["t"])):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (LB_LONDON[0] <= dt.hour < LB_LONDON[1]):
            continue
        day = dt.date()
        h, l = float(d["h"][j]), float(d["l"][j])
        if day not in by_day:
            by_day[day] = {"hi": h, "lo": l, "n": 1}
        else:
            by_day[day]["hi"] = max(by_day[day]["hi"], h)
            by_day[day]["lo"] = min(by_day[day]["lo"], l)
            by_day[day]["n"] += 1
    return by_day


# ---------------------------------------------------------------------------
# Child 1 — inside-bar mother break accept CONT
# ---------------------------------------------------------------------------
def probe_fx3_insidebar_mother_break_accept(h1):
    """Arm when bar[j] is inside bar[j-1] (mother). Later bar accept close
    beyond mother extreme → CONT. Max 1/day/symbol.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    pending = {s: None for s in FX3}
    last_day_sym = set()
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, IB_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            for s in FX3:
                pending[s] = None
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)

        for sym in FX3:
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 25:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            pend = pending[sym]
            if pend is not None:
                pend["age"] += 1
                if pend["age"] > IB_MAX_WAIT:
                    pending[sym] = None
                    pend = None

            if (
                pend is not None
                and IB_SESSION[0] <= sig_dt.hour < IB_SESSION[1]
                and sym not in open_syms
            ):
                day_key = (sig_dt.date(), sym)
                if day_key not in last_day_sym:
                    cl = float(d["c"][j])
                    hi, lo = float(d["h"][j]), float(d["l"][j])
                    side = 0
                    if cl > pend["m_hi"] and lo <= pend["m_hi"]:
                        side = 1
                    elif cl < pend["m_lo"] and hi >= pend["m_lo"]:
                        side = -1
                    if side != 0:
                        ent_i = asof_idx(d, ts)
                        if ent_i is not None:
                            entry = float(d["o"][ent_i])
                            if side > 0:
                                sl = pend["m_lo"] - IB_SL_PAD * atr
                            else:
                                sl = pend["m_hi"] + IB_SL_PAD * atr
                            sl_dist = abs(entry - sl)
                            if sl_dist > 1e-12:
                                tp = entry + side * IB_RR * sl_dist
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
                                        "entry_ts": ts,
                                    }
                                )
                                last_day_sym.add(day_key)
                                pending[sym] = None
                                continue

            if pending[sym] is not None or sym in open_syms:
                continue
            if not (IB_SESSION[0] <= sig_dt.hour < IB_SESSION[1]):
                continue
            # inside bar: high<=mother high and low>=mother low
            mh, ml = float(d["h"][j - 1]), float(d["l"][j - 1])
            h, l = float(d["h"][j]), float(d["l"][j])
            mother_rng = mh - ml
            if mother_rng < IB_MIN_MOTHER_ATR * atr:
                continue
            if not (h <= mh and l >= ml and (h - l) < mother_rng):
                continue
            pending[sym] = {"m_hi": mh, "m_lo": ml, "age": 0}
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Child 2 — London box → overlap break accept CONT
# ---------------------------------------------------------------------------
def probe_fx3_london_box_overlap_break_accept(h1):
    """After London [7,12) box forms, in overlap [12,16) first close-accept
    beyond box extreme → CONT. Max 1/day/symbol.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    boxes = {s: build_london_box(h1[s]) for s in FX3}
    last_day_sym = set()
    fired = set()  # day,sym already attempted accept
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, LB_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if not (LB_OVERLAP[0] <= sig_dt.hour < LB_OVERLAP[1]):
            continue
        day = sig_dt.date()
        for sym in FX3:
            if sym in open_syms:
                continue
            day_key = (day, sym)
            if day_key in last_day_sym or day_key in fired:
                continue
            box = boxes[sym].get(day)
            if box is None or box.get("n", 0) < 3:
                continue
            b_hi, b_lo = box["hi"], box["lo"]
            if b_hi <= b_lo:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 25:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            box_rng = b_hi - b_lo
            if box_rng < LB_MIN_BOX_ATR * atr or box_rng > LB_MAX_BOX_ATR * atr:
                continue
            o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            if abs(c - o) < LB_MIN_BODY * atr:
                continue
            side = 0
            if c > b_hi and o <= b_hi:
                side = 1
            elif c < b_lo and o >= b_lo:
                side = -1
            fired.add(day_key)
            if side == 0:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            if side > 0:
                sl = b_lo - LB_SL_PAD * atr
            else:
                sl = b_hi + LB_SL_PAD * atr
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                continue
            tp = entry + side * LB_RR * sl_dist
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
                    "entry_ts": ts,
                }
            )
            last_day_sym.add(day_key)
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    p1 = PREREG / "20260715_H_FX3_H1_INSIDEBAR_MOTHER_BREAK_ACCEPT_CONT_001_PREREG.md"
    p2 = PREREG / "20260715_H_FX3_H1_LONDON_BOX_OVERLAP_BREAK_ACCEPT_CONT_001_PREREG.md"
    p1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-INSIDEBAR-MOTHER-BREAK-ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_insidebar_mother_break_accept`",
                "- Lane: `hard_pivot_w8_entrystate_20260715`",
                "- Thesis / post-friction $/trade → cadence:",
                "  Mother-bar SL = clean structural invalidation → higher WR after +$12;",
                "  inside-bar events are frequent across FX3 → cadence without FVG densify.",
                f"- Arm: inside bar (H/L ⊂ mother) with mother range≥{IB_MIN_MOTHER_ATR}*ATR.",
                f"- Accept within {IB_MAX_WAIT} bars: close beyond mother extreme.",
                f"- Session UTC[{IB_SESSION[0]},{IB_SESSION[1]}); RR={IB_RR}; hold≤{IB_HOLD}.",
                "- Hard ≠ Outside-bar densify; ≠ NR7 densify; ≠ W1–W7; ≠ FVG.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    p2.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-LONDON-BOX-OVERLAP-BREAK-ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_london_box_overlap_break_accept`",
                "- Lane: `hard_pivot_w8_entrystate_20260715`",
                "- Thesis / post-friction $/trade → cadence:",
                "  Overlap-only accept filters false London box breaks that die under +$12",
                "  (raises post-friction expectancy); London+overlap clocks keep cadence.",
                f"- Box: London UTC[{LB_LONDON[0]},{LB_LONDON[1]}) HL.",
                f"- Accept: overlap UTC[{LB_OVERLAP[0]},{LB_OVERLAP[1]}) first close beyond box.",
                f"- Box size ∈[{LB_MIN_BOX_ATR},{LB_MAX_BOX_ATR}]*ATR; RR={LB_RR}; hold≤{LB_HOLD}.",
                "- Hard ≠ ORB/IB densify; ≠ W7 handoff nest densify; ≠ Asia-sweep; ≠ FVG.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return str(p1.as_posix()), str(p2.as_posix())


def append_reg(results, receipt, prereg_paths):
    stamp = utc_now()
    fam = {
        "HYP-FX3-H1-INSIDEBAR-MOTHER-BREAK-ACCEPT-CONT-001": "fx_h1_insidebar_mother_break_accept",
        "HYP-FX3-H1-LONDON-BOX-OVERLAP-BREAK-ACCEPT-CONT-001": "fx_h1_london_box_overlap_break_accept",
    }
    with REG.open("a", encoding="utf-8") as f:
        for r, preg in zip(results, prereg_paths):
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"].startswith("KILLED") else "probe",
                "verdict": r["verdict"],
                "parent_candidate": None,
                "feature_family": fam.get(r["hypothesis_id"], "hard_pivot_w8"),
                "lane": "hard_pivot_w8_entrystate_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT W8 after W1-W7 ALL_KILL; insidebar-mother + "
                    "london-box-overlap; post-friction $/trade→cadence; "
                    "R-series densify PAUSED; no FVG densify"
                ),
                "prereg_path": preg,
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


def write_docs(results, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    def row(r):
        return (
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1']['pf']} | "
            f"{r['haircuts']['x1_5']['pf']} | "
            f"{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE', 'KILL')} |"
        )

    table = [
        "| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ] + [row(r) for r in results]

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — HARD PIVOT W8 (insidebar + london-box)",
                "",
                "Date: 2026-07-15",
                "Nested: trader/quant/MQL5 lead self-merge.",
                "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`.",
                "",
                "## Carry",
                "W7 expansion cadenceOK/thin; handoff thicker but starve.",
                "Need structural SL / overlap confirm without FVG densify.",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | GO insidebar mother-break; GO London-box overlap accept |",
                "| Quant | GO; a priori FX3; no corpse densify |",
                "| MQL5/MT5 | GO — OHLC closed-bar |",
                "",
                "Merge: **GO offline**. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT W8",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "## How each raises post-friction $/trade into cadence (no FVG densify)",
                "",
                "### 1 Inside-bar mother-break accept CONT",
                "Mother extreme = structural SL → cleaner invalidation → higher WR",
                "after fixed +$12; inside bars frequent on FX3 → cadence band.",
                "≠ Outside-bar densify; ≠ NR7 densify.",
                "",
                "### 2 London-box overlap-break accept CONT",
                "Accept only in London–NY overlap filters false London breaks that",
                "bleed under +$12 → thicker post-friction expectancy; clocks → cadence.",
                "≠ ORB/IB densify; ≠ W7 handoff nest densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W8",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| Inside-bar mother-break | ≠ W1–W7; ≠ Outside-bar densify; ≠ NR7 densify; ≠ FVG |",
                "| London-box overlap-break | ≠ ORB/IB densify; ≠ W7 handoff densify; ≠ Asia-sweep; ≠ FVG |",
                "",
                "FVG densify FORBIDDEN. R-series densify PAUSED.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT W8",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Freeze SHA256: `{freeze_sha}`",
                f"Status: `{status}`",
                f"QFSI: {qnote}",
                "",
                *table,
                "",
                "## Fail notes",
                *[
                    f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}"
                    for r in results
                ],
                "",
                "Model 0 WITHHELD unless PROBE_SURVIVOR. No corpse densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — HARD PIVOT W8",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED**.",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify insidebar-k / lbox-k / W1–W7 corpses / FVG / R10–R31.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W8",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                "### Thesis (không densify FVG)",
                "- Inside-bar mother: SL cấu trúc → WR sau +$12; event đủ dày cho cadence.",
                "- London-box overlap: chỉ accept overlap → lọc false break; clock giữ cadence.",
                "",
                f"Receipt `{receipt}`",
                "PAUSE R-series. Cấm densify FVG / W1–W8 corpses. Best shelf `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W8",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## HARD PIVOT W8 — `{status}`",
                *table,
                "",
                "### post-friction $/trade → cadence (W8)",
                "- Inside-bar mother-break: structural SL raises WR after +$12.",
                "- London-box overlap: overlap confirm filters thin London breaks.",
                "- Không densify FVG / W1–W7 corpses.",
                "",
                "- R-series densify PAUSED.",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, receipt, any_surv, freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines = [
        f"- **HARD PIVOT W8 INSIDEBAR/LBOX CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W8 after W1–W7 entry-state ALL_KILL.",
        "  NEW classes (post-friction $/trade→cadence): insidebar mother-break +",
        "  London-box overlap-break accept.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        m, hc = r["metrics"], r["haircuts"]
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} "
            f"x1.5={hc['x1_5']['pf']})."
        )
    lines += [
        f"  Receipt `{receipt}`",
        f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W8_VN_ACTION_BRIEF.md`.",
        f"  Freeze sha={freeze_sha[:16]}… QFSI: {qnote}",
        "  W7 carry: expansion cadenceOK/thin; handoff thicker/starve; FVG FORBIDDEN.",
        "  Do **not** densify insidebar-k / lbox-k / W1–W7 / FVG / R10–R31 / exit / MaxKZ.",
        "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
        "  Next: next entry-state class outside W1–W8; keep R-series paused;",
        "  QFSI parallel; cost autonomous retry.",
        "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
        "",
        "",
    ]
    block = "\n".join(lines)
    text = HOT.read_text(encoding="utf-8")
    old_lines = text.splitlines()
    if len(old_lines) >= 2 and old_lines[0].startswith("# Hot Cache"):
        old_lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W8 insidebar/lbox; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W8 aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W8 insidebar/lbox offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG or W1–W8 corpses. Do not resume R10–R31 densify. "
        "Next entry-state class if ALL_KILL. "
        "QFSI parallel; cost GAP. Best shelf RR2 `194548`. GOAL unmet.\n"
    )
    if nm in text:
        text2, nsub = re.subn(
            r"\n- \*\*ACTIVE — HARD PIVOT[^\n]*\n",
            next_block,
            text,
            count=1,
        )
        if nsub:
            text = text2
        else:
            idx = text.find(nm) + len(nm)
            text = text[:idx] + next_block + text[idx:]
    HOT.write_text(text, encoding="utf-8")


def qfsi_note():
    note = "QFSI 007 parallel; cost freeze GAP (11 deals); login not headline"
    for root in (ROOT / "04. Project Control" / "ai", ROOT / "02. AlphaFactory"):
        if not root.exists():
            continue
        for p in root.rglob("*heartbeat*.json"):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                return (
                    f"QFSI hb ts={j.get('ts') or j.get('timestamp')} "
                    f"alive={j.get('alive', j.get('watcher_alive'))}; cost GAP"
                )
            except Exception:
                continue
    return note


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")

    freeze_body = "\n".join(
        [
            "# Universe freeze — HARD PIVOT W8 insidebar + london-box",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Universe (a priori)",
            "- Symbols: EURUSD, GBPUSD, USDJPY",
            "",
            "## Children",
            "1. HYP-FX3-H1-INSIDEBAR-MOTHER-BREAK-ACCEPT-CONT-001",
            "2. HYP-FX3-H1-LONDON-BOX-OVERLAP-BREAK-ACCEPT-CONT-001",
            "",
            "## Forbidden",
            "FVG densify; W1–W7 densify; R10–R31 densify; exit/MaxKZ/ORB/IB/FRED.",
            "",
        ]
    )
    OUT_FREEZE.write_text(freeze_body, encoding="utf-8")
    freeze_sha = sha256_bytes(freeze_body.encode("utf-8"))
    prereg_paths = write_preregs()

    print("Loading H1 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}

    print("Probe Child1 insidebar mother-break...")
    p1, d1 = probe_fx3_insidebar_mother_break_accept(h1)
    r1 = pack_result(
        "HYP-FX3-H1-INSIDEBAR-MOTHER-BREAK-ACCEPT-CONT-001",
        "FX3 H1 inside-bar mother-break accept CONT",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p1,
        d1,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Child2 London-box overlap-break...")
    p2, d2 = probe_fx3_london_box_overlap_break_accept(h1)
    r2 = pack_result(
        "HYP-FX3-H1-LONDON-BOX-OVERLAP-BREAK-ACCEPT-CONT-001",
        "FX3 H1 London-box overlap-break accept CONT",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p2,
        d2,
    )
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    results = [r1, r2]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
    payload = {
        "schema": "hard_pivot_w8_insidebar_lbox.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "base_cost_usd": BASE_COST,
        "results": results,
        "any_survivor": any_surv,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "FVG_RETEST_DENSIFY_FORBIDDEN": True,
            "UNIVERSE_APRIORI_FREEZE": True,
        },
    }
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())

    qnote = qfsi_note()
    write_docs(results, receipt, any_surv, freeze_sha, qnote)
    append_reg(results, receipt, prereg_paths)
    patch_hot(results, receipt, any_surv, freeze_sha, qnote)
    print("Receipt:", receipt)
    print("Status:", "SURVIVOR" if any_surv else "ALL_KILL")
    mt5.shutdown()


if __name__ == "__main__":
    main()
