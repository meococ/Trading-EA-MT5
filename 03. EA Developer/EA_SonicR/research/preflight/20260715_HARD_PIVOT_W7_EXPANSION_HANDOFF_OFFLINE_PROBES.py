#!/usr/bin/env python3
"""HARD PIVOT W7 — after W1–W6 entry-state ALL_KILL.

Carry:
  - Cadence-capable location accepts die under +$12 (thin edge).
  - Thick rare (FVG ~$53/tpw1.15) starves cadence — FVG densify FORBIDDEN.
  - W6 London excess starved; nested double-accept cadenceOK-ish but PF@$12~1.01.

NEW classes outside W1–W6 densify (raise post-friction $/trade INTO cadence band):
  1. HYP-FX3-H1-ATR-EXPANSION-PDMID-ACCEPT-CONT-001
     Mechanism: PD-mid break accept ONLY when ATR is in expansion regime
     (ATR > rolling median). Expansion filter kills chop mid-crosses that
     bleed under fixed +$12; remaining accepts should carry higher WR →
     higher post-friction expectancy while session/day clock keeps cadence.
     NOT open-FVG-window; NOT London excess wick; NOT auction-persist densify.
  2. HYP-FX3-H1-LONDON-DISP-NY-PB-ACCEPT-CONT-001
     Mechanism: nested session-handoff book — London displacement beyond Asia
     range arms; NY first PB-touch then accept beyond displace extreme → CONT.
     Cross-session nest raises confirmation rarity (edge thickness) without
     FVG densify; London→NY clocks supply cadence. NOT W6 same-session nest;
     NOT W5 Asia-sweep mid-reclaim; NOT NY-open-impulse densify; NOT leadlag.

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

STEM = "20260715_HARD_PIVOT_W7_EXPANSION_HANDOFF"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W7_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# Child 1: ATR-expansion PD-mid accept CONT
EX_SIGNAL = (7, 17)
EX_ATR_MED_N = 48  # ~2 trading days of H1
EX_MIN_BODY = 0.20
EX_SL_PAD = 0.12
EX_RR = 2.00
EX_HOLD = 12
EX_MAX_PER_DAY = 1

# Child 2: London displace → NY PB accept (session handoff nested)
HO_ASIA = (0, 7)
HO_LONDON_ARM = (7, 12)
HO_NY_ACCEPT = (12, 17)
HO_DISP_BODY = 0.85
HO_DISP_RATIO = 0.55
HO_MAX_WAIT = 8  # NY bars after arm
HO_SL_PAD = 0.12
HO_RR = 2.00
HO_HOLD = 12


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


def build_prior_day(d):
    """Map date -> prior calendar day's HL + mid from H1 bars."""
    by_day = {}
    for j in range(len(d["t"])):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        day = dt.date()
        h, l = float(d["h"][j]), float(d["l"][j])
        if day not in by_day:
            by_day[day] = {"hi": h, "lo": l}
        else:
            by_day[day]["hi"] = max(by_day[day]["hi"], h)
            by_day[day]["lo"] = min(by_day[day]["lo"], l)
    days = sorted(by_day.keys())
    prior = {}
    for i, day in enumerate(days):
        for k in range(i - 1, -1, -1):
            pd = days[k]
            if (day - pd).days <= 4:
                box = by_day[pd]
                prior[day] = {
                    "hi": box["hi"],
                    "lo": box["lo"],
                    "mid": 0.5 * (box["hi"] + box["lo"]),
                }
                break
    return prior


def build_asia_range(d):
    """Map date -> Asia session [0,7) UTC HL for that calendar day."""
    by_day = {}
    for j in range(len(d["t"])):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (HO_ASIA[0] <= dt.hour < HO_ASIA[1]):
            continue
        day = dt.date()
        h, l = float(d["h"][j]), float(d["l"][j])
        if day not in by_day:
            by_day[day] = {"hi": h, "lo": l}
        else:
            by_day[day]["hi"] = max(by_day[day]["hi"], h)
            by_day[day]["lo"] = min(by_day[day]["lo"], l)
    return by_day


def atr_median_ok(atr_series, j, n=EX_ATR_MED_N):
    if j < n or not np.isfinite(atr_series[j]) or atr_series[j] <= 0:
        return False
    window = atr_series[j - n : j]
    window = window[np.isfinite(window)]
    if len(window) < n // 2:
        return False
    med = float(np.median(window))
    return atr_series[j] > med and med > 0


# ---------------------------------------------------------------------------
# Child 1 — ATR-expansion PD-mid accept CONT
# ---------------------------------------------------------------------------
def probe_fx3_atr_expansion_pdmid_accept(h1):
    """Close accept beyond prior-day mid ONLY when ATR > rolling median.
    Max 1/day/symbol. Expansion filter aims to raise WR (post-friction $/trade)
    while day clock + FX3 keep cadence — NOT FVG densify / NOT PD excess wick.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    pd = {s: build_prior_day(h1[s]) for s in FX3}
    last_day_sym = set()
    for i in range(60, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, EX_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if not (EX_SIGNAL[0] <= sig_dt.hour < EX_SIGNAL[1]):
            continue
        day = sig_dt.date()
        for sym in FX3:
            if sym in open_syms:
                continue
            day_key = (day, sym)
            if day_key in last_day_sym:
                continue
            box = pd[sym].get(day)
            if box is None:
                continue
            mid = box["mid"]
            p_hi, p_lo = box["hi"], box["lo"]
            if p_hi <= p_lo:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < EX_ATR_MED_N + 5:
                continue
            atr = d["atr"][j]
            if not atr_median_ok(d["atr"], j):
                continue
            o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            if abs(c - o) < EX_MIN_BODY * atr:
                continue
            # accept beyond PD mid (CONT break) — no excess wick required
            side = 0
            if c > mid and o <= mid and c > o:
                side = 1
            elif c < mid and o >= mid and c < o:
                side = -1
            if side == 0:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            if side > 0:
                sl = min(l, mid) - EX_SL_PAD * atr
            else:
                sl = max(h, mid) + EX_SL_PAD * atr
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                continue
            tp = entry + side * EX_RR * sl_dist
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


# ---------------------------------------------------------------------------
# Child 2 — London displace → NY PB accept CONT (session handoff nested)
# ---------------------------------------------------------------------------
def probe_fx3_london_disp_ny_pb_accept(h1):
    """Arm: London H1 displacement closing beyond Asia range extreme.
    Stage1 (NY): wick into displace body without accept.
    Stage2 (NY): accept close beyond displace extreme → CONT next open.
    Nested across sessions raises edge rarity vs same-session W6 nest;
    clocks supply cadence — NOT Asia-sweep mid-reclaim / NOT NY-open impulse.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    asia = {s: build_asia_range(h1[s]) for s in FX3}
    pending = {s: None for s in FX3}
    last_day_sym = set()
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, HO_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            for s in FX3:
                pending[s] = None
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        day = sig_dt.date()

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
                if pend["age"] > HO_MAX_WAIT or pend["day"] != day:
                    pending[sym] = None
                    pend = None

            # NY accept window on armed setup
            if (
                pend is not None
                and HO_NY_ACCEPT[0] <= sig_dt.hour < HO_NY_ACCEPT[1]
                and sym not in open_syms
            ):
                lo, hi, cl = float(d["l"][j]), float(d["h"][j]), float(d["c"][j])
                zu, zl = pend["upper"], pend["lower"]
                if pend["stage"] == 1:
                    touched = (lo <= zu and hi >= zl) if pend["bull"] else (hi >= zl and lo <= zu)
                    # reject early accept (collapse to single mit)
                    if pend["bull"] and cl > zu:
                        pending[sym] = None
                        continue
                    if (not pend["bull"]) and cl < zl:
                        pending[sym] = None
                        continue
                    if touched:
                        pend["stage"] = 2
                        pend["age"] = 0
                    continue

                if pend["stage"] == 2:
                    day_key = (day, sym)
                    if day_key in last_day_sym:
                        continue
                    accepted = False
                    side = 0
                    if pend["bull"] and lo <= zu and cl > zu:
                        accepted, side = True, 1
                    elif (not pend["bull"]) and hi >= zl and cl < zl:
                        accepted, side = True, -1
                    if accepted:
                        ent_i = asof_idx(d, ts)
                        if ent_i is not None:
                            entry = float(d["o"][ent_i])
                            if side > 0:
                                sl = zl - HO_SL_PAD * atr
                            else:
                                sl = zu + HO_SL_PAD * atr
                            sl_dist = abs(entry - sl)
                            if sl_dist > 1e-12:
                                tp = entry + side * HO_RR * sl_dist
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

            # Arm during London on Asia break displacement
            if pending[sym] is not None or sym in open_syms:
                continue
            if not (HO_LONDON_ARM[0] <= sig_dt.hour < HO_LONDON_ARM[1]):
                continue
            box = asia[sym].get(day)
            if box is None or box["hi"] <= box["lo"]:
                continue
            o, c = float(d["o"][j]), float(d["c"][j])
            h, l = float(d["h"][j]), float(d["l"][j])
            rng = h - l
            body = abs(c - o)
            if rng <= 0 or body < HO_DISP_BODY * atr or body / rng < HO_DISP_RATIO:
                continue
            bull = c > o
            # must close beyond Asia extreme in displace direction
            if bull and c <= box["hi"]:
                continue
            if (not bull) and c >= box["lo"]:
                continue
            upper, lower = max(o, c), min(o, c)
            if upper <= lower:
                continue
            pending[sym] = {
                "upper": upper,
                "lower": lower,
                "bull": bull,
                "stage": 1,
                "age": 0,
                "day": day,
            }
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    p1 = PREREG / "20260715_H_FX3_H1_ATR_EXPANSION_PDMID_ACCEPT_CONT_001_PREREG.md"
    p2 = PREREG / "20260715_H_FX3_H1_LONDON_DISP_NY_PB_ACCEPT_CONT_001_PREREG.md"
    p1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-ATR-EXPANSION-PDMID-ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_atr_expansion_pdmid_accept`",
                "- Lane: `hard_pivot_w7_entrystate_20260715`",
                "- Thesis / post-friction $/trade → cadence:",
                "  PD-mid accept is cadence-capable; ATR>median expansion filter",
                "  removes chop mid-crosses that die under +$12, raising WR and",
                "  post-friction expectancy into the GOAL band — WITHOUT densifying FVG.",
                f"- Signal UTC[{EX_SIGNAL[0]},{EX_SIGNAL[1]}): close accept beyond prior-day mid",
                f"  with body≥{EX_MIN_BODY}*ATR AND ATR[j] > median(ATR[{EX_ATR_MED_N}]).",
                f"- Entry next open; SL beyond signal extreme/mid+{EX_SL_PAD}*ATR; RR={EX_RR}; hold≤{EX_HOLD}.",
                "- Max 1/day/symbol. Universe a priori: EURUSD+GBPUSD+USDJPY.",
                "- Hard ≠ W1–W6 densify; ≠ London excess wick; ≠ FVG; ≠ auction-persist;",
                "  ≠ prior-day-open break densify; ≠ H4-balance densify.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    p2.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-LONDON-DISP-NY-PB-ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_london_disp_ny_pb_accept`",
                "- Lane: `hard_pivot_w7_entrystate_20260715`",
                "- Thesis / post-friction $/trade → cadence:",
                "  Nested London→NY handoff raises confirmation rarity (edge thickness",
                "  after +$12) vs single-session accepts; session clocks keep cadence",
                "  without FVG densify.",
                f"- Arm UTC[{HO_LONDON_ARM[0]},{HO_LONDON_ARM[1]}): displace body≥{HO_DISP_BODY}*ATR",
                f"  ratio≥{HO_DISP_RATIO} closing beyond Asia[{HO_ASIA[0]},{HO_ASIA[1]}) extreme.",
                f"- NY UTC[{HO_NY_ACCEPT[0]},{HO_NY_ACCEPT[1]}): stage1 PB-touch (no accept);",
                f"  stage2 accept beyond zone (≤{HO_MAX_WAIT} bars) → next open CONT.",
                f"- RR={HO_RR}; hold≤{HO_HOLD}. Max 1/day/symbol.",
                "- Hard ≠ W6 same-session nested densify; ≠ W5 Asia-sweep mid-reclaim;",
                "  ≠ NY-open-impulse densify; ≠ leadlag peer; ≠ FVG densify.",
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
        "HYP-FX3-H1-ATR-EXPANSION-PDMID-ACCEPT-CONT-001": "fx_h1_atr_expansion_pdmid_accept",
        "HYP-FX3-H1-LONDON-DISP-NY-PB-ACCEPT-CONT-001": "fx_h1_london_disp_ny_pb_accept",
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
                "feature_family": fam.get(r["hypothesis_id"], "hard_pivot_w7"),
                "lane": "hard_pivot_w7_entrystate_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT W7 after W1-W6 ALL_KILL; atr-expansion-pdmid + "
                    "london-disp-ny-pb handoff; post-friction $/trade→cadence; "
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
                "# 3-critic panel — HARD PIVOT W7 (expansion + handoff)",
                "",
                "Date: 2026-07-15",
                "Nested: trader/quant/MQL5 lead self-merge.",
                "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`.",
                "",
                "## Carry",
                "W1–W6 ALL_KILL. Cadence-capable location dies under +$12;",
                "FVG thick rare starves. Need post-friction $/trade↑ into cadence",
                "WITHOUT FVG densify.",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | GO ATR-expansion PD-mid; GO London→NY nested handoff |",
                "| Quant | GO; a priori FX3; no corpse densify; document $/trade thesis |",
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
                "# Design — HARD PIVOT W7",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "## How each raises post-friction $/trade into cadence (no FVG densify)",
                "",
                "### 1 ATR-expansion PD-mid accept CONT",
                "PD-mid accept alone is cadence-capable but thin under +$12 (W1–W6 lesson).",
                "Gate with ATR > rolling median: drop chop mid-crosses → higher WR →",
                "higher expectancy after fixed $12 friction, while 1/day×FX3 keeps tpw band.",
                "NOT FVG window; NOT London excess wick beyond PDH/PDL.",
                "",
                "### 2 London-disp → NY PB accept CONT (session handoff nested)",
                "Cross-session nest (London arm beyond Asia → NY PB-touch → accept)",
                "raises confirmation rarity vs single-bar / same-session nest (W6).",
                "Higher confirmation → thicker edge after +$12; London/NY clocks → cadence.",
                "NOT Asia-sweep mid-reclaim; NOT NY-open impulse densify; NOT leadlag.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W7",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| ATR-expansion PD-mid accept | ≠ W1–W6; ≠ London excess densify; ≠ auction-persist; ≠ prior-day-open densify; ≠ H4-balance densify; ≠ FVG |",
                "| London-disp NY PB accept | ≠ W6 same-session nest densify; ≠ W5 Asia-sweep mid-reclaim; ≠ NY-open-impulse densify; ≠ leadlag; ≠ FVG |",
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
                "# Offline probes — HARD PIVOT W7",
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
                "# Session closeout — HARD PIVOT W7",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED**.",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify expansion-k / handoff-k / W1–W6 corpses / FVG / R10–R31.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W7",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                "### Thesis (không densify FVG)",
                "- ATR-expansion PD-mid: lọc chop → tăng WR/expectancy sau +$12, giữ cadence.",
                "- London→NY nested handoff: nest liên phiên tăng rarity/edge; clock giữ cadence.",
                "",
                f"Receipt `{receipt}`",
                "PAUSE R-series. Cấm densify FVG / W1–W7 corpses. Best shelf `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W7",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## HARD PIVOT W7 — `{status}`",
                *table,
                "",
                "### post-friction $/trade → cadence (W7)",
                "- ATR-expansion PD-mid: expansion gate raises WR after +$12; day clock = cadence.",
                "- London-disp→NY PB: cross-session nest thickens edge; session clocks = cadence.",
                "- Không densify FVG (thick rare starve).",
                "",
                "- R-series densify PAUSED. Không densify FVG / W1–W7 corpses.",
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
        f"- **HARD PIVOT W7 EXPANSION/HANDOFF CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W7 after W1–W6 entry-state ALL_KILL.",
        "  NEW classes (post-friction $/trade→cadence): ATR-expansion PD-mid +",
        "  London-disp→NY PB handoff nested.",
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
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W7_VN_ACTION_BRIEF.md`.",
        f"  Freeze sha={freeze_sha[:16]}… QFSI: {qnote}",
        "  W6 carry: excess starve / nested PF@$12~1; FVG thick FORBIDDEN densify.",
        "  Do **not** densify expansion-k / handoff-k / W1–W6 / FVG / R10–R31 / exit / MaxKZ.",
        "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
        "  Next: next entry-state class outside W1–W7; keep R-series paused;",
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
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W7 expansion/handoff; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W7 aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W7 expansion/handoff offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG or W1–W7 corpses. Do not resume R10–R31 densify. "
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
            "# Universe freeze — HARD PIVOT W7 expansion + handoff",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Universe (a priori)",
            "- Symbols: EURUSD, GBPUSD, USDJPY",
            "",
            "## Children",
            "1. HYP-FX3-H1-ATR-EXPANSION-PDMID-ACCEPT-CONT-001",
            "2. HYP-FX3-H1-LONDON-DISP-NY-PB-ACCEPT-CONT-001",
            "",
            "## Forbidden",
            "FVG densify; W1–W6 densify; R10–R31 densify; exit/MaxKZ/ORB/IB/FRED.",
            "",
        ]
    )
    OUT_FREEZE.write_text(freeze_body, encoding="utf-8")
    freeze_sha = sha256_bytes(freeze_body.encode("utf-8"))
    prereg_paths = write_preregs()

    print("Loading H1 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}

    print("Probe Child1 ATR-expansion PD-mid accept...")
    p1, d1 = probe_fx3_atr_expansion_pdmid_accept(h1)
    r1 = pack_result(
        "HYP-FX3-H1-ATR-EXPANSION-PDMID-ACCEPT-CONT-001",
        "FX3 H1 ATR-expansion PD-mid accept CONT",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p1,
        d1,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Child2 London-disp NY PB accept...")
    p2, d2 = probe_fx3_london_disp_ny_pb_accept(h1)
    r2 = pack_result(
        "HYP-FX3-H1-LONDON-DISP-NY-PB-ACCEPT-CONT-001",
        "FX3 H1 London-disp → NY PB-accept CONT",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p2,
        d2,
    )
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    results = [r1, r2]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
    payload = {
        "schema": "hard_pivot_w7_expansion_handoff.v1",
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
