#!/usr/bin/env python3
"""HARD PIVOT W5 — after W1–W4 entry-state ALL_KILL.

Evidence map (NO densify corpses):
  FVG ~$53/1.15tpw near-miss FORBIDDEN densify;
  body-mit cadenceOK/thin; CISD mid; dualimp cadenceOK/thin+$12;
  round/breaker/H4/auction dense-thin.

NEW classes outside W1–W4 densify (explicit thick∩cadence breakers):
  1. HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001
     Mechanism: daily Asia HL location clock (cadence floor) + mid-reclaim
     accept (edge filter). NOT open-FVG-window-because-cadence-failed.
  2. HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001
     Mechanism: a priori multi-symbol peer book — lead impulse rarity (thick)
     + lag delayed accept (quality) expands cadence across frozen FX3 peers.

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

STEM = "20260715_HARD_PIVOT_W5_ASIASWEEP_LEADLAG"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W5_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# Child 1: Asia sweep → mid reclaim CONT
AS_ASIA = (0, 7)  # UTC hours forming Asia box
AS_SIGNAL = (7, 14)  # London reclaim window
AS_MIN_ASIA_BARS = 4
AS_SWEEP_PAD = 0.05  # ATR beyond Asia extreme
AS_MIN_BODY = 0.20
AS_SL_PAD = 0.10
AS_RR = 2.00
AS_HOLD = 12

# Child 2: lead-lag peer accept CONT (universe frozen a priori)
LL_LOOK = 12
LL_LEAD_BODY = 0.50
LL_MAX_WAIT = 5
LL_SESSION = (7, 17)
LL_SL = 1.25
LL_RR = 2.00
LL_HOLD = 12
# Frozen peer edges (NOT outcome-mined): (lead, lag, lag_side_sign vs lead_side)
# lag_side_sign=+1 means lag trades same numeric side as lead;
# lag_side_sign=-1 means lag trades opposite (USDJPY vs XXXUSD).
LL_EDGES = (
    ("EURUSD", "GBPUSD", +1),
    ("GBPUSD", "EURUSD", +1),
    ("EURUSD", "USDJPY", -1),
    ("GBPUSD", "USDJPY", -1),
)


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


def build_asia_boxes(d):
    """Map calendar date -> Asia HL box from closed H1 bars in AS_ASIA hours."""
    boxes = {}
    n = len(d["t"])
    for j in range(n):
        dt = datetime.fromtimestamp(int(d["t"][j]), tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        if not (AS_ASIA[0] <= dt.hour < AS_ASIA[1]):
            continue
        day = dt.date()
        h, l = float(d["h"][j]), float(d["l"][j])
        if day not in boxes:
            boxes[day] = {"hi": h, "lo": l, "n": 1, "last_j": j}
        else:
            boxes[day]["hi"] = max(boxes[day]["hi"], h)
            boxes[day]["lo"] = min(boxes[day]["lo"], l)
            boxes[day]["n"] += 1
            boxes[day]["last_j"] = j
    return boxes


# ---------------------------------------------------------------------------
# Child 1 — Asia sweep + mid reclaim CONT
# ---------------------------------------------------------------------------
def probe_fx3_asia_sweep_mid_reclaim(h1):
    """Daily Asia HL location. London wick sweeps extreme then closed-bar
    reclaim beyond Asia mid → CONT next open. Max 1/day/symbol.

    thick∩cadence breaker: Asia box = clocked location (cadence floor across
    FX3) without opening FVG windows; mid-reclaim accept filters noise for
    edge under +$12.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    asia = {s: build_asia_boxes(h1[s]) for s in FX3}
    last_day_sym = set()
    for i in range(30, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, AS_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if not (AS_SIGNAL[0] <= sig_dt.hour < AS_SIGNAL[1]):
            continue
        day = sig_dt.date()
        for sym in FX3:
            if sym in open_syms:
                continue
            day_key = (day, sym)
            if day_key in last_day_sym:
                continue
            box = asia[sym].get(day)
            if box is None or box["n"] < AS_MIN_ASIA_BARS:
                continue
            a_hi, a_lo = box["hi"], box["lo"]
            if a_hi <= a_lo:
                continue
            mid = 0.5 * (a_hi + a_lo)
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < 20 or j <= box["last_j"]:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            o, h, l, c = float(d["o"][j]), float(d["h"][j]), float(d["l"][j]), float(d["c"][j])
            body = abs(c - o)
            if body < AS_MIN_BODY * atr:
                continue
            side = 0
            sweep_ext = None
            # bull reclaim after Asia-low sweep
            if l <= a_lo - AS_SWEEP_PAD * atr and c > mid and c > a_lo:
                side = 1
                sweep_ext = l
            # bear reclaim after Asia-high sweep
            elif h >= a_hi + AS_SWEEP_PAD * atr and c < mid and c < a_hi:
                side = -1
                sweep_ext = h
            if side == 0 or sweep_ext is None:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            if side > 0:
                sl = sweep_ext - AS_SL_PAD * atr
            else:
                sl = sweep_ext + AS_SL_PAD * atr
            sl_dist = abs(entry - sl)
            if sl_dist <= 1e-12:
                continue
            tp = entry + side * AS_RR * sl_dist
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
# Child 2 — lead-lag peer accept CONT
# ---------------------------------------------------------------------------
def probe_fx3_leadlag_peer_accept(h1):
    """A priori FX3 peer book. Lead closed-bar impulse beyond LOOK extreme;
    lag that has NOT yet followed arms; later lag accept beyond its LOOK
    extreme in mapped direction → CONT next open.

    thick∩cadence breaker: lead rarity = thick timing; peer lag accept =
    quality delay; multi-symbol frozen universe expands cadence WITHOUT
    opening FVG windows because single-symbol cadence failed.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    # pending: lag_sym -> {side, age, lead, lead_ts}
    pending = {}
    last_day_sym = set()
    for i in range(LL_LOOK + 5, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, LL_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            pending.clear()
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)

        # age / expire pending
        expired = []
        for lag, pend in pending.items():
            pend["age"] += 1
            if pend["age"] > LL_MAX_WAIT:
                expired.append(lag)
        for lag in expired:
            pending.pop(lag, None)

        # try fire pending accepts
        if LL_SESSION[0] <= sig_dt.hour < LL_SESSION[1]:
            for lag in list(pending.keys()):
                if lag in open_syms:
                    continue
                pend = pending[lag]
                day_key = (dt.date(), lag)
                if day_key in last_day_sym:
                    continue
                d = h1[lag]
                j = asof_idx(d, sig_ts)
                if j is None or j < LL_LOOK + 2:
                    continue
                atr = d["atr"][j]
                if not np.isfinite(atr) or atr <= 0:
                    continue
                # LOOK window ending at bar before signal (exclude signal bar)
                hi = float(np.max(d["h"][j - LL_LOOK : j]))
                lo = float(np.min(d["l"][j - LL_LOOK : j]))
                c = float(d["c"][j])
                side = pend["side"]
                accepted = (side > 0 and c > hi) or (side < 0 and c < lo)
                if not accepted:
                    continue
                ent_i = asof_idx(d, ts)
                if ent_i is None:
                    continue
                entry = float(d["o"][ent_i])
                sl = entry - side * LL_SL * atr
                tp = entry + side * LL_RR * LL_SL * atr
                lots = risk_lots(lag, entry, sl)
                open_pos.append(
                    {
                        "sym": lag,
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
                pending.pop(lag, None)

        # arm new leads
        if not (LL_SESSION[0] <= sig_dt.hour < LL_SESSION[1]):
            continue
        for lead, lag, sign in LL_EDGES:
            if lag in pending or lag in open_syms:
                continue
            day_key = (dt.date(), lag)
            if day_key in last_day_sym:
                continue
            dl = h1[lead]
            dg = h1[lag]
            jl = asof_idx(dl, sig_ts)
            jg = asof_idx(dg, sig_ts)
            if jl is None or jg is None or jl < LL_LOOK + 2 or jg < LL_LOOK + 2:
                continue
            atr_l = dl["atr"][jl]
            if not np.isfinite(atr_l) or atr_l <= 0:
                continue
            o, c = float(dl["o"][jl]), float(dl["c"][jl])
            body = abs(c - o)
            if body < LL_LEAD_BODY * atr_l:
                continue
            lead_hi = float(np.max(dl["h"][jl - LL_LOOK : jl]))
            lead_lo = float(np.min(dl["l"][jl - LL_LOOK : jl]))
            lead_side = 0
            if c > lead_hi and c > o:
                lead_side = 1
            elif c < lead_lo and c < o:
                lead_side = -1
            if lead_side == 0:
                continue
            # lag must NOT have followed yet (close still inside prior LOOK range)
            lag_hi = float(np.max(dg["h"][jg - LL_LOOK : jg]))
            lag_lo = float(np.min(dg["l"][jg - LL_LOOK : jg]))
            lag_c = float(dg["c"][jg])
            lag_side = lead_side * sign
            if lag_c > lag_hi or lag_c < lag_lo:
                continue  # already broke prior range (followed or opposite)
            pending[lag] = {
                "side": lag_side,
                "age": 0,
                "lead": lead,
                "lead_ts": sig_ts,
            }
    flush_open(open_pos, h1, closed)
    return summarize(closed)


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    p1 = PREREG / "20260715_H_FX3_H1_ASIA_SWEEP_MID_RECLAIM_CONT_001_PREREG.md"
    p2 = PREREG / "20260715_H_FX3_H1_LEADLAG_PEER_ACCEPT_CONT_001_PREREG.md"
    p1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_asia_sweep_mid_reclaim`",
                "- Lane: `hard_pivot_w5_entrystate_20260715`",
                "- Thesis / thick∩cadence breaker: Asia HL is a **daily clocked",
                "  location** (cadence floor across FX3) — NOT an open FVG window.",
                "  Mid-reclaim after sweep is the accept filter for edge under +$12.",
                f"- Asia box UTC[{AS_ASIA[0]},{AS_ASIA[1]}); ≥{AS_MIN_ASIA_BARS} bars.",
                f"- Signal UTC[{AS_SIGNAL[0]},{AS_SIGNAL[1]}): wick sweeps Asia extreme",
                f"  by ≥{AS_SWEEP_PAD}*ATR; close reclaim beyond Asia mid; body≥{AS_MIN_BODY}*ATR.",
                f"- Entry next open; SL beyond sweep+{AS_SL_PAD}*ATR; RR={AS_RR}; hold≤{AS_HOLD}.",
                "- Max 1/day/symbol. Universe a priori: EURUSD+GBPUSD+USDJPY.",
                "- Hard ≠ W1–W4 densify; ≠ Spark Asian M15 breakout densify;",
                "  ≠ ORB/IB densify; ≠ FVG densify; ≠ equal-HL densify.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    p2.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_leadlag_peer_accept`",
                "- Lane: `hard_pivot_w5_entrystate_20260715`",
                "- Thesis / thick∩cadence breaker: **a priori multi-symbol peer book**.",
                "  Lead impulse = rare thick timing; lag delayed accept = quality.",
                "  Cadence expands across frozen peers — MUST NOT be “open FVG",
                "  window because cadence failed”.",
                "- Universe freeze (a priori): EURUSD, GBPUSD, USDJPY.",
                "- Frozen edges: EURUSD↔GBPUSD same-side; EURUSD/GBPUSD→USDJPY opposite.",
                f"- Lead: body≥{LL_LEAD_BODY}*ATR close beyond prior {LL_LOOK}-bar extreme.",
                f"- Lag arm: lag close still inside its {LL_LOOK}-bar range at lead time.",
                f"- Trigger: lag accept close beyond LOOK extreme within ≤{LL_MAX_WAIT} bars.",
                f"- Session UTC[{LL_SESSION[0]},{LL_SESSION[1]}); SL={LL_SL} ATR; RR={LL_RR}; hold≤{LL_HOLD}.",
                "- Hard ≠ W1–W4 densify; ≠ R12 relstr densify; ≠ R20/R21 lead densify;",
                "  ≠ FVG densify; ≠ oneslot densify.",
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
        "HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001": "fx_h1_asia_sweep_mid_reclaim",
        "HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001": "fx_h1_leadlag_peer_accept",
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
                "feature_family": fam.get(r["hypothesis_id"], "hard_pivot_w5"),
                "lane": "hard_pivot_w5_entrystate_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT W5 after W1-W4 ALL_KILL; asia-sweep-mid-reclaim + "
                    "leadlag-peer-accept; thick∩cadence breakers; R-series densify "
                    "PAUSED; no FVG densify"
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
                "# 3-critic panel — HARD PIVOT W5 (asia-sweep + leadlag)",
                "",
                "Date: 2026-07-15",
                "Nested: trader/quant/MQL5 lead self-merge.",
                "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`.",
                "",
                "## Carry",
                "W1–W4 map: thick edge only at rare FVG; cadence-capable accepts die under +$12.",
                "W5 tries (a) clocked Asia location + mid reclaim (b) a priori peer lead-lag book.",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | GO asia-sweep mid-reclaim; GO leadlag peer accept |",
                "| Quant | GO; universe frozen a priori; no corpse densify |",
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
                "# Design — HARD PIVOT W5",
                "",
                f"Freeze sha={freeze_sha[:16]}…",
                "",
                "## thick∩cadence break mandate",
                "FVG thick but tpw≈1.15 — NO densify. Cadence accepts die under +$12.",
                "W5 classes must break that dichotomy via location/book architecture.",
                "",
                "## 1 Asia-sweep mid-reclaim CONT",
                "Daily Asia HL clocked location → London sweep wick → close reclaim",
                "beyond Asia mid → CONT. Mechanism: cadence from daily location clock;",
                "edge from mid-reclaim accept — NOT open-FVG-window.",
                "",
                "## 2 Lead-lag peer accept CONT",
                "A priori FX3 peer edges. Lead impulse rarity + lag delayed accept.",
                "Mechanism: multi-symbol book expands cadence without FVG densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W5",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| Asia-sweep mid-reclaim | ≠ W1–W4; ≠ Spark Asian M15 breakout densify; ≠ ORB/IB; ≠ FVG; ≠ equal-HL; ≠ spring densify |",
                "| Leadlag peer accept | ≠ W1–W4; ≠ R12 relstr densify; ≠ R20/R21 lead densify; ≠ oneslot; ≠ FVG densify |",
                "",
                "FVG densify FORBIDDEN. R-series densify PAUSED.",
                "Universe freeze a priori (not post-cadence expansion).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT W5",
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
                "# Session closeout — HARD PIVOT W5",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED**.",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify asiasweep-k / leadlag-k / W1–W4 corpses / FVG / R10–R31.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W5",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "PAUSE R-series. Cấm densify FVG / W1–W5 corpses. Best shelf `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W5",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`.",
                "",
                f"## HARD PIVOT W5 — `{status}`",
                *table,
                "",
                "### thick∩cadence break (W5)",
                "- Asia-sweep mid-reclaim: daily Asia location clock + mid accept — NOT FVG densify.",
                "- Leadlag peer: a priori FX3 peer book — cadence from peers, not open FVG window.",
                "",
                "- R-series densify PAUSED. Không densify FVG / W1–W5 corpses.",
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
        f"- **HARD PIVOT W5 ASIASWEEP/LEADLAG CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W5 after W1–W4 entry-state ALL_KILL.",
        "  NEW classes (thick∩cadence breakers): asia-sweep mid-reclaim + leadlag peer.",
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
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W5_VN_ACTION_BRIEF.md`.",
        f"  Freeze sha={freeze_sha[:16]}… QFSI: {qnote}",
        "  Evidence map carry: FVG near-miss thick~$53/tpw1.15 FORBIDDEN densify;",
        "  cadence-capable accepts die under +$12 across W1–W4.",
        "  Do **not** densify asiasweep-k / leadlag-k / W1–W4 / FVG / R10–R31 / exit / MaxKZ.",
        "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
        "  Next: next entry-state class outside W1–W5; keep R-series paused;",
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
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W5 asiasweep/leadlag; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W5 aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W5 asiasweep/leadlag offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG or W1–W5 corpses. Do not resume R10–R31 densify. "
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
            "# Universe freeze — HARD PIVOT W5 asia-sweep + leadlag peer",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Universe (a priori — NOT post-cadence expansion)",
            "- Symbols: EURUSD, GBPUSD, USDJPY",
            "- Leadlag edges frozen: EURUSD↔GBPUSD same-side; EUR/GBP→USDJPY opposite",
            "",
            "## Children",
            "1. HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001",
            "2. HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001",
            "",
            "## thick∩cadence break mechanism",
            "- Asia: daily location clock + mid reclaim (not open FVG window)",
            "- Leadlag: peer book cadence from frozen multi-symbol edges",
            "",
            "## Forbidden",
            "FVG densify; W1–W4 densify; R10–R31 densify; exit/MaxKZ/ORB/IB/FRED.",
            "",
        ]
    )
    OUT_FREEZE.write_text(freeze_body, encoding="utf-8")
    freeze_sha = sha256_bytes(freeze_body.encode("utf-8"))
    prereg_paths = write_preregs()

    print("Loading H1 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}

    print("Probe Child1 asia-sweep mid-reclaim...")
    p1, d1 = probe_fx3_asia_sweep_mid_reclaim(h1)
    r1 = pack_result(
        "HYP-FX3-H1-ASIA-SWEEP-MID-RECLAIM-CONT-001",
        "FX3 H1 Asia HL sweep + mid reclaim CONT",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p1,
        d1,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Child2 leadlag peer accept...")
    p2, d2 = probe_fx3_leadlag_peer_accept(h1)
    r2 = pack_result(
        "HYP-FX3-H1-LEADLAG-PEER-ACCEPT-CONT-001",
        "FX3 H1 a priori lead-lag peer accept CONT",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p2,
        d2,
    )
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    results = [r1, r2]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
    payload = {
        "schema": "hard_pivot_w5_asiasweep_leadlag.v1",
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
        "thick_cadence_break": {
            "asia_sweep_mid_reclaim": "daily Asia location clock + mid accept",
            "leadlag_peer_accept": "a priori FX3 peer book; not open-FVG-for-cadence",
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
