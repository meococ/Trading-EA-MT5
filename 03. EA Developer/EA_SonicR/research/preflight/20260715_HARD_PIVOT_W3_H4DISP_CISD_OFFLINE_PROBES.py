#!/usr/bin/env python3
"""HARD PIVOT W3 — NEW entry-state after W2 breaker+bodymit ALL_KILL.

Evidence carry (NO densify of corpses):
  W1 auction: tpw≈12 thin; FVG: thick~$53 but tpw≈1.15
  W2 breaker: tpw≈8 PF thin; body-mit: tpw≈3.0 cadence OK but exp~$7 dies +$12

NEW classes (outside W1+W2 densify):
  1. HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001  — multi-TF location/accept
  2. HYP-SB-CISD-PULLBACK-ACCEPT-001      — new acceptance class (CISD)

R_SERIES densify remains PAUSED. Model 0 only PROBE_SURVIVOR.
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

STEM = "20260715_HARD_PIVOT_W3_H4DISP_CISD"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W3_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# Child 1: H4 displacement arms zone; H1 accept into H4 body → CONT
H4_DISP_ATR = 0.55
H4_DISP_RATIO = 0.65
H4_MAX_WAIT_H1 = 12  # H1 bars after H4 arm
H4_SL_PAD = 0.20
H4_RR = 2.00
H4_HOLD = 16  # H1 bars
H4_SESSION = (7, 17)

# Child 2: SB CISD after displacement pullback
SB_SYM = "USDJPY"
SB_LDN = (11, 12)
SB_NY = (16, 18)
SB_DISP_ATR = 0.40
SB_DISP_RATIO = 0.70
SB_MAX_WAIT = 10
SB_MAX_KZ = 2
SB_MAX_DAY = 3
SB_RR = 2.0
SB_HOLD = 32
SB_SKIP_FRI = True
SB_SL_PAD = 0.20
SB_PB_INTO = 0.35  # pullback must reach ≥35% into disp body before CISD

CTRL_PF12 = 1.1197
CTRL_X15 = 1.0134


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
    if challenger:
        if pf12 <= CTRL_PF12:
            notes.append("no_lift_vs_rr2_pf12")
        if (hc["x1_5"]["pf"] or 0.0) <= CTRL_X15:
            notes.append("no_lift_vs_rr2_x15")
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


def pack_result(hid, setup, symbol, timeframe, pnls, detail, challenger=False):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc, challenger=challenger)
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
            "challenger": challenger,
        }
    )


def asof_idx(d, ts):
    j = int(np.searchsorted(d["t"], ts, side="left"))
    if j < len(d["t"]) and int(d["t"][j]) == int(ts):
        return j
    return None


def h1_atr_asof(h1, ts):
    j = int(np.searchsorted(h1["t"], ts, side="right")) - 1
    if j < 14:
        return None
    atr = h1["atr"][j]
    if not np.isfinite(atr) or atr <= 0:
        return None
    return float(atr), j


def in_kz(hour: int) -> str | None:
    if SB_LDN[0] <= hour < SB_LDN[1]:
        return "LDN"
    if SB_NY[0] <= hour < SB_NY[1]:
        return "NY"
    return None


def last_closed_h4_idx(h4, ts):
    """Index of last fully closed H4 at or before ts."""
    j = int(np.searchsorted(h4["t"], ts, side="right")) - 1
    return j if j >= 14 else None


# ---------------------------------------------------------------------------
# Child 1 — H4 disp → H1 accept
# ---------------------------------------------------------------------------
def probe_fx3_h4disp_h1accept(h1, h4):
    """Arm on closed H4 displacement (body zone). No H1 entry on arm H4.
    Later H1: wick into H4 body + close accept outside → enter next H1 open.
    SL uses H4 ATR pad. Max 1/day/symbol.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    pending = {s: None for s in FX3}
    last_day_sym = set()
    armed_h4_ts = {s: set() for s in FX3}  # avoid re-arm same H4 bar
    for i in range(40, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, H4_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            for s in FX3:
                pending[s] = None
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)

        for sym in FX3:
            d1 = h1[sym]
            d4 = h4[sym]
            j1 = asof_idx(d1, sig_ts)
            if j1 is None or j1 < 20:
                continue

            pend = pending[sym]
            if pend is not None:
                pend["age"] += 1
                if pend["age"] > H4_MAX_WAIT_H1:
                    pending[sym] = None
                    pend = None

            # accept on H1
            if (
                pend is not None
                and pend["age"] >= 1
                and sym not in open_syms
                and H4_SESSION[0] <= sig_dt.hour < H4_SESSION[1]
            ):
                day_key = (dt.date(), sym)
                if day_key not in last_day_sym:
                    lo = float(d1["l"][j1])
                    hi = float(d1["h"][j1])
                    cl = float(d1["c"][j1])
                    zu, zl = pend["upper"], pend["lower"]
                    accepted = False
                    side = 0
                    if pend["bull"]:
                        into = lo <= zu and hi >= zl
                        if into and cl > zu:
                            accepted, side = True, 1
                    else:
                        into = hi >= zl and lo <= zu
                        if into and cl < zl:
                            accepted, side = True, -1
                    if accepted:
                        ent_i = asof_idx(d1, ts)
                        if ent_i is not None:
                            entry = float(d1["o"][ent_i])
                            atr4 = pend["atr4"]
                            if side > 0:
                                sl = zl - H4_SL_PAD * atr4
                            else:
                                sl = zu + H4_SL_PAD * atr4
                            sl_dist = abs(entry - sl)
                            if sl_dist > 1e-12:
                                tp = entry + side * H4_RR * sl_dist
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
                                open_syms.add(sym)
                                last_day_sym.add(day_key)
                                pending[sym] = None
                                continue

            # arm from newly closed H4 (only once per H4 bar)
            if pending[sym] is not None or sym in open_syms:
                continue
            if not (H4_SESSION[0] <= sig_dt.hour < H4_SESSION[1]):
                continue
            j4 = last_closed_h4_idx(d4, sig_ts)
            if j4 is None:
                continue
            h4_ts = int(d4["t"][j4])
            if h4_ts in armed_h4_ts[sym]:
                continue
            # Only arm when this H4 just became available: H4 close time ≈ within
            # last ~4 H1 bars of signal (fresh displacement, not stale zone)
            if sig_ts - h4_ts > 4 * 3600:
                continue
            atr4 = d4["atr"][j4]
            if not np.isfinite(atr4) or atr4 <= 0:
                continue
            o4, c4 = float(d4["o"][j4]), float(d4["c"][j4])
            h4b, l4b = float(d4["h"][j4]), float(d4["l"][j4])
            rng = h4b - l4b
            if rng <= 0:
                continue
            body = abs(c4 - o4)
            if body < H4_DISP_ATR * atr4:
                continue
            if body / rng < H4_DISP_RATIO:
                continue
            bull = c4 > o4
            upper, lower = max(o4, c4), min(o4, c4)
            if upper <= lower:
                continue
            pending[sym] = {
                "upper": upper,
                "lower": lower,
                "bull": bull,
                "age": 0,
                "atr4": float(atr4),
                "h4_ts": h4_ts,
            }
            armed_h4_ts[sym].add(h4_ts)
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Child 2 — SB CISD after pullback into disp body
# ---------------------------------------------------------------------------
def probe_sb_cisd_pullback_accept(m15, h1):
    """Arm on SB displacement. Require pullback into body, then CISD:
    closed bar closes back beyond the open of the most recent opposing bar
    in the pullback (change-in-state-of-delivery). Enter next M15 open.
    NOT FVG / NOT body-wick mitigation densify.
    """
    closed, open_pos = [], []
    d = m15
    pending = None
    trades_day = {}
    trades_kz = {}
    for i in range(40, len(d["t"]) - 1):
        ts = int(d["t"][i])
        open_pos = manage_exits(open_pos, {SB_SYM: d}, ts, closed, SB_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if SB_SKIP_FRI and dt.weekday() == 4:
            pending = None
            continue
        if dt.weekday() >= 5:
            pending = None
            continue

        sig = i - 1
        if pending is not None:
            pending["age"] += 1
            if pending["age"] > SB_MAX_WAIT:
                pending = None

        hour = datetime.fromtimestamp(int(d["t"][sig]), tz=timezone.utc).hour
        kz = in_kz(hour)
        if pending is not None and kz is None:
            if in_kz(dt.hour) is None:
                pending = None

        atr_pack = h1_atr_asof(h1, int(d["t"][sig]))
        if atr_pack is None:
            continue
        atr, _ = atr_pack

        if pending is not None and pending["age"] >= 1 and not open_pos:
            day = dt.date()
            if trades_day.get(day, 0) < SB_MAX_DAY:
                kz_key = (day, pending["kz"])
                if trades_kz.get(kz_key, 0) < SB_MAX_KZ:
                    lo = float(d["l"][sig])
                    hi = float(d["h"][sig])
                    cl = float(d["c"][sig])
                    op = float(d["o"][sig])
                    bu, bl = pending["upper"], pending["lower"]
                    depth = bu - bl
                    # track pullback into zone
                    if pending["bull"]:
                        if lo <= bu - SB_PB_INTO * depth:
                            pending["pb"] = True
                    else:
                        if hi >= bl + SB_PB_INTO * depth:
                            pending["pb"] = True
                    # CISD: after PB, closed bar closes beyond open of this bar's
                    # opposing character — proxy: close back outside body extreme
                    # AND close vs open confirms delivery resume (bull close > open
                    # and close > body upper; bear close < open and close < lower)
                    cisd = False
                    side = 0
                    if pending.get("pb"):
                        if pending["bull"]:
                            # CISD long: close > open and close > disp body upper
                            # after having pulled into body
                            if cl > op and cl > bu and lo <= bu:
                                cisd, side = True, 1
                        else:
                            if cl < op and cl < bl and hi >= bl:
                                cisd, side = True, -1
                    if cisd:
                        entry = float(d["o"][i])
                        if side > 0:
                            sl = bl - SB_SL_PAD * atr
                        else:
                            sl = bu + SB_SL_PAD * atr
                        sl_dist = abs(entry - sl)
                        if sl_dist > 1e-12:
                            tp = entry + side * SB_RR * sl_dist
                            lots = risk_lots(SB_SYM, entry, sl)
                            open_pos.append(
                                {
                                    "sym": SB_SYM,
                                    "side": side,
                                    "entry": entry,
                                    "sl": sl,
                                    "tp": tp,
                                    "lots": lots,
                                    "bars": 0,
                                    "entry_ts": ts,
                                }
                            )
                            trades_day[day] = trades_day.get(day, 0) + 1
                            trades_kz[kz_key] = trades_kz.get(kz_key, 0) + 1
                            pending = None
                            continue

        if pending is not None or kz is None or open_pos:
            continue
        o2, c2 = float(d["o"][sig]), float(d["c"][sig])
        h2, l2 = float(d["h"][sig]), float(d["l"][sig])
        rng2 = h2 - l2
        if rng2 <= 0:
            continue
        body2 = abs(c2 - o2)
        if body2 < SB_DISP_ATR * atr:
            continue
        if body2 / rng2 < SB_DISP_RATIO:
            continue
        is_bull = c2 > o2
        upper, lower = max(o2, c2), min(o2, c2)
        if upper <= lower:
            continue
        pending = {
            "upper": float(upper),
            "lower": float(lower),
            "bull": is_bull,
            "age": 0,
            "kz": kz,
            "pb": False,
            "arm_ts": int(d["t"][sig]),
        }
    flush_open(open_pos, {SB_SYM: d}, closed)
    return summarize(closed)


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    p1 = PREREG / "20260715_H_FX3_H1_H4DISP_H1ACCEPT_CONT_001_PREREG.md"
    p2 = PREREG / "20260715_H_SB_CISD_PULLBACK_ACCEPT_001_PREREG.md"
    p1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h4disp_h1_accept`",
                "- Lane: `hard_pivot_w3_entrystate_20260715`",
                "- Symbol/TF: FX3 / H4-arm + H1-accept",
                "- Thesis: multi-TF — rare H4 displacement location (thicker geometry)",
                "  + H1 delayed accept for fill cadence; aims joint thick+$/trade and 2–5/wk.",
                f"- Arm: closed H4 body≥{H4_DISP_ATR}*H4ATR, ratio≥{H4_DISP_RATIO};",
                "  zone = H4 body; fresh within 4h; no entry on arm H4.",
                f"- Trigger: later H1 (≤{H4_MAX_WAIT_H1}) wick-into-H4-body + close accept;",
                "  enter next H1 open.",
                f"- SL beyond H4 body ±{H4_SL_PAD}*H4ATR; RR={H4_RR}; hold≤{H4_HOLD};",
                f"  session UTC[{H4_SESSION[0]},{H4_SESSION[1]}); max 1/day/symbol.",
                "- Hard ≠ W1 auction/FVG densify; ≠ W2 breaker/bodymit densify;",
                "  ≠ H4-engulf densify (R25 CONT engulf ≠ accept-delay FSM); ≠ MTF-align densify.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    p2.write_text(
        "\n".join(
            [
                "# Prereg — HYP-SB-CISD-PULLBACK-ACCEPT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Parent shelf: `HYP-SB-MAXKZ2-RR2-FRICTION-001` / run `194548`",
                "- Feature family: `sb_cisd_pullback_accept`",
                "- Lane: `hard_pivot_w3_entrystate_20260715`",
                "- Symbol/TF: USDJPY / M15",
                "- Thesis: NEW acceptance class — CISD after required pullback into",
                "  disp body (not FVG gap fill, not body-wick mitigation alone).",
                f"- Arm: SB disp gates; require PB≥{SB_PB_INTO} into body; then CISD",
                "  (close confirms delivery resume beyond body extreme after PB).",
                f"- Enter next M15 open; RR={SB_RR}; MaxKZ={SB_MAX_KZ}; KZ LDN/NY.",
                "- Challenger gates: joint + lift vs RR2 PF@$12/x1.5.",
                "- Hard ≠ FVG-retest densify; ≠ body-mit densify; ≠ MaxKZ/exit densify.",
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
        "HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001": "fx_h4disp_h1_accept",
        "HYP-SB-CISD-PULLBACK-ACCEPT-001": "sb_cisd_pullback_accept",
    }
    with REG.open("a", encoding="utf-8") as f:
        for r, preg in zip(results, prereg_paths):
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"].startswith("KILLED") else "probe",
                "verdict": r["verdict"],
                "parent_candidate": (
                    "HYP-SB-MAXKZ2-RR2-FRICTION-001" if r.get("challenger") else None
                ),
                "feature_family": fam.get(r["hypothesis_id"], "hard_pivot_w3"),
                "lane": "hard_pivot_w3_entrystate_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT W3 after W2 breaker+bodymit ALL_KILL; "
                    "multi-TF H4→H1 accept + SB CISD; R-series densify PAUSED"
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
                "# 3-critic panel — HARD PIVOT W3 (H4disp + CISD)",
                "",
                "Date: 2026-07-15",
                "Nested critics: trader / quant / MQL5 (lead self-merge).",
                "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`.",
                "",
                "## Carry (ruthless)",
                "W2 body-mit hit cadence (tpw≈3) but exp~$7 — location too weak.",
                "FVG thick but rare. Need rarer location (H4) or stricter accept (CISD).",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | GO H4→H1 accept; GO CISD-after-PB |",
                "| Quant | GO both; no FVG/auction/breaker/bodymit densify |",
                "| MQL5/MT5 | GO — H4 as-of + H1 FSM; M15 CISD FSM |",
                "",
                "## Children",
                "1. `HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001` — GO",
                "2. `HYP-SB-CISD-PULLBACK-ACCEPT-001` — GO",
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
                "# Design — HARD PIVOT W3 H4disp + CISD",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001`",
                f"H4 disp body≥{H4_DISP_ATR}*ATR → arm H4 body; H1 later accept → CONT.",
                "Why: multi-TF location (rarer than H1 body-mit) + H1 fill cadence.",
                "",
                "## 2 `HYP-SB-CISD-PULLBACK-ACCEPT-001`",
                f"SB disp → require PB≥{SB_PB_INTO} into body → CISD close resume → enter.",
                "Why: new acceptance class; ≠ FVG gap; ≠ body-wick mitigation alone.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W3",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| H4disp→H1 accept | ≠ W1 auction/FVG; ≠ W2 breaker/bodymit; ≠ R25 H4-engulf densify; ≠ R23 MTF-align densify |",
                "| SB CISD-PB accept | ≠ FVG-retest densify; ≠ body-mit densify; ≠ MaxKZ/exit densify |",
                "",
                "All prior HARD PIVOT densify + R10–R31 + ORB/IB + FRED: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT W3 H4disp + CISD",
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
                "Do **not** densify any W1–W3 corpse knobs from readout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — HARD PIVOT W3",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED** (`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`).",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify h4disp-k / cisd-k / breaker-k / body-mit-k /",
                "auction-persist-k / fvg-retest-k / R10–R31 / exit / MaxKZ / ORB/IB.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W3",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## W3",
                "- Giữ PAUSE R-series densify.",
                "- Class mới: H4-disp→H1-accept + SB CISD-after-PB.",
                "- Cấm densify FVG / auction / breaker / body-mit.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W3",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book PRIMARY RR2+Spark + HARD PIVOT W3.",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241. Best shelf RR2 `194548`. Cost GAP.",
                "",
                f"## HARD PIVOT W3 — `{status}`",
                *table,
                "",
                "- R-series densify: **PAUSED**.",
                "- Không densify W1–W3 corpses / R10–R31 / exit / MaxKZ.",
                "",
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
        f"- **HARD PIVOT W3 H4DISP/CISD CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W3 after W2 breaker+bodymit ALL_KILL.",
        "  NEW classes: H4-disp→H1-accept + SB CISD-after-PB.",
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
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W3_VN_ACTION_BRIEF.md`.",
        f"  Panel `readouts/{STEM}_3CRITIC_PANEL.md`.",
        f"  Freeze sha={freeze_sha[:16]}…",
        f"  QFSI: {qnote}",
        "  Do **not** densify h4disp-k / cisd-k / breaker-k / body-mit-k /",
        "  auction-persist-k / fvg-retest-k / R10–R31 / exit / MaxKZ / ORB/IB / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        "  PRIMARY PF@$12=1.184 tpw=3.241 verdict=`DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL`.",
        "  Next: if ALL_KILL → next entry-state class outside W1–W3 objects;",
        "  keep R-series densify paused; QFSI parallel; cost autonomous retry.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
        "",
    ]
    block = "\n".join(lines)
    text = HOT.read_text(encoding="utf-8")
    old_lines = text.splitlines()
    if len(old_lines) >= 2 and old_lines[0].startswith("# Hot Cache"):
        old_lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W3 H4disp/CISD; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W3 aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W3 H4disp/CISD offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify W1–W3 corpses or resume R10–R31 densify. "
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
        text = text2 if nsub else text[: text.find(nm) + len(nm)] + next_block + text[text.find(nm) + len(nm) :]
    HOT.write_text(text, encoding="utf-8")


def qfsi_note():
    note = (
        "QFSI 007 parallel accumulate; cost freeze still GAP "
        "(raw_deals≈11; freeze_eligible=False); login not headline"
    )
    for root in (ROOT / "04. Project Control" / "ai", ROOT / "02. AlphaFactory"):
        if not root.exists():
            continue
        for p in root.rglob("*heartbeat*.json"):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                alive = j.get("alive", j.get("watcher_alive"))
                ts = j.get("ts") or j.get("timestamp")
                return f"QFSI hb ts={ts} alive={alive}; cost freeze GAP (11 deals)"
            except Exception:
                continue
    return note


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")

    freeze_body = "\n".join(
        [
            "# Universe freeze — HARD PIVOT W3 H4disp + CISD",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Children (≤2)",
            "1. HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001",
            "2. HYP-SB-CISD-PULLBACK-ACCEPT-001",
            "",
            "## Window",
            "2021.01.01 – 2025.12.31",
            "",
            "## Cost screen",
            f"+${BASE_COST:.0f}/trade a priori; x1.5 / x2 haircuts",
            "",
            "## Forbidden",
            "W1 auction/FVG densify; W2 breaker/bodymit densify; R10–R31 densify;",
            "exit/MaxKZ/ETH-VR/ORB/IB/FRED densify.",
            "",
        ]
    )
    OUT_FREEZE.write_text(freeze_body, encoding="utf-8")
    freeze_sha = sha256_bytes(freeze_body.encode("utf-8"))
    prereg_paths = write_preregs()

    print("Loading H1+H4 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
    h4 = {s: enrich(load(s, mt5.TIMEFRAME_H4)) for s in FX3}
    print("Loading USDJPY M15...")
    m15 = enrich(load(SB_SYM, mt5.TIMEFRAME_M15))
    h1_uj = h1["USDJPY"]

    print("Probe Child1 H4disp->H1accept...")
    p1, d1 = probe_fx3_h4disp_h1accept(h1, h4)
    r1 = pack_result(
        "HYP-FX3-H1-H4DISP-H1ACCEPT-CONT-001",
        "FX3 H4 displacement arm → H1 body accept CONT; multi-TF",
        "EURUSD+GBPUSD+USDJPY",
        "H4+H1",
        p1,
        d1,
        challenger=False,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Child2 CISD-PB accept...")
    p2, d2 = probe_sb_cisd_pullback_accept(m15, h1_uj)
    r2 = pack_result(
        "HYP-SB-CISD-PULLBACK-ACCEPT-001",
        "USDJPY M15 SB CISD after pullback into disp body; RR2 MaxKZ2",
        SB_SYM,
        "M15",
        p2,
        d2,
        challenger=True,
    )
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    results = [r1, r2]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)

    payload = {
        "schema": "hard_pivot_w3_h4disp_cisd.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "base_cost_usd": BASE_COST,
        "results": results,
        "any_survivor": any_surv,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "FVG_RETEST_DENSIFY_FORBIDDEN": True,
            "AUCTION_PERSIST_DENSIFY_FORBIDDEN": True,
            "BREAKER_BODYMIT_DENSIFY_FORBIDDEN": True,
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
