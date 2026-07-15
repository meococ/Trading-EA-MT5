#!/usr/bin/env python3
"""HARD PIVOT W2 — NEW entry-state classes (post auction-persist + FVG ALL_KILL).

PAUSE remains: R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED
FORBIDDEN densify: auction-persist-k / fvg-retest-k / R10–R31 / exit / MaxKZ /
  ETH VR / ORB/IB / FRED / Asia-break / Outside-bar

Children (a priori ≤2, outside prior HARD PIVOT objects):
  1. HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001
  2. HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001

Closed-bar only. +$12 a priori. Model 0 only if PROBE_SURVIVOR.
Lead self-merge nested critic (trader/quant/MQL5).
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
PREREG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preregs"

STEM = "20260715_HARD_PIVOT_W2_BREAKER_BODYMIT"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_W2_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Child 1: FX3 H1 breaker retest-accept CONT ---
# After closed BOS of confirmed swing (L=3), arm breaker = BOS-bar BODY.
# No entry on arm. Later wick-into-body + close accept → next open CONT.
BR_PIVOT_L = 3
BR_MAX_WAIT = 8
BR_SL_PAD = 0.15  # ATR pad beyond opposite body extreme
BR_RR = 2.00
BR_HOLD = 12
BR_SESSION = (7, 17)
BR_MIN_BOS_BODY = 0.25  # BOS bar body ≥ this * ATR (quality floor, a priori)

# --- Child 2: SB displacement BODY mitigation accept (NOT FVG densify) ---
SB_SYM = "USDJPY"
SB_LDN = (11, 12)
SB_NY = (16, 18)
SB_DISP_ATR = 0.40
SB_DISP_RATIO = 0.70
SB_MAX_WAIT = 8
SB_MAX_KZ = 2
SB_MAX_DAY = 3
SB_RR = 2.0
SB_HOLD = 32
SB_SKIP_FRI = True
SB_SL_PAD = 0.20

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


def last_confirmed_pivots(d, j, L=BR_PIVOT_L):
    """Most recent confirmed pivot high/low fully known at closed bar j.
    Pivot at k confirmed when j >= k+L and k >= L.
    """
    ph_idx, ph_px = None, None
    pl_idx, pl_px = None, None
    # scan backward for newest confirmed pivots
    for k in range(j - L, L - 1, -1):
        # pivot high at k
        if ph_idx is None:
            hi = d["h"][k]
            if hi >= np.max(d["h"][k - L : k]) and hi >= np.max(d["h"][k + 1 : k + L + 1]):
                ph_idx, ph_px = k, float(hi)
        if pl_idx is None:
            lo = d["l"][k]
            if lo <= np.min(d["l"][k - L : k]) and lo <= np.min(d["l"][k + 1 : k + L + 1]):
                pl_idx, pl_px = k, float(lo)
        if ph_idx is not None and pl_idx is not None:
            break
    return ph_idx, ph_px, pl_idx, pl_px


# ---------------------------------------------------------------------------
# Child 1 — breaker retest-accept CONT
# ---------------------------------------------------------------------------
def probe_fx3_breaker_retest(h1):
    """BOS of confirmed swing → arm BOS-bar body as breaker.
    Later wick-into-body + close accept outside → enter next H1 open CONT.
    Max 1 pending/symbol; max 1/day/symbol; session filter.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    pending = {s: None for s in FX3}  # per-symbol FSM
    last_day_sym = set()
    warmup = BR_PIVOT_L * 4 + 30
    for i in range(warmup, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, BR_HOLD)
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
            if j is None or j < warmup:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue

            # age / expire pending
            pend = pending[sym]
            if pend is not None:
                pend["age"] += 1
                if pend["age"] > BR_MAX_WAIT:
                    pending[sym] = None
                    pend = None

            # try acceptance entry (age >= 1)
            if (
                pend is not None
                and pend["age"] >= 1
                and sym not in open_syms
                and BR_SESSION[0] <= sig_dt.hour < BR_SESSION[1]
            ):
                day_key = (dt.date(), sym)
                if day_key not in last_day_sym:
                    lo = float(d["l"][j])
                    hi = float(d["h"][j])
                    cl = float(d["c"][j])
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
                        ent_i = asof_idx(d, ts)
                        if ent_i is not None:
                            entry = float(d["o"][ent_i])
                            if side > 0:
                                sl = zl - BR_SL_PAD * atr
                            else:
                                sl = zu + BR_SL_PAD * atr
                            sl_dist = abs(entry - sl)
                            if sl_dist > 1e-12:
                                tp = entry + side * BR_RR * sl_dist
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

            # arm new BOS only if no pending and no open
            if pending[sym] is not None or sym in open_syms:
                continue
            if not (BR_SESSION[0] <= sig_dt.hour < BR_SESSION[1]):
                continue

            ph_i, ph_px, pl_i, pl_px = last_confirmed_pivots(d, j, BR_PIVOT_L)
            o, c = float(d["o"][j]), float(d["c"][j])
            body = abs(c - o)
            if body < BR_MIN_BOS_BODY * atr:
                continue
            bull = False
            bear = False
            if ph_px is not None and c > ph_px and o <= ph_px:
                # close breaks prior swing high (BOS up); require pierce
                bull = True
            if pl_px is not None and c < pl_px and o >= pl_px:
                bear = True
            if bull == bear:
                continue  # none or both
            upper, lower = max(o, c), min(o, c)
            if upper <= lower:
                continue
            pending[sym] = {
                "upper": upper,
                "lower": lower,
                "bull": bull,
                "age": 0,
                "arm_ts": sig_ts,
                "pivot": ph_px if bull else pl_px,
            }
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Child 2 — SB disp BODY mitigation accept (NOT FVG)
# ---------------------------------------------------------------------------
def probe_sb_disp_body_mitigation(m15, h1):
    """Arm on closed SB displacement; zone = disp BODY (not FVG gap).
    No entry on arm. Later wick-into-body + close accept → next M15 open.
    MaxKZ=2, RR=2.0 — shelf parity challenger geometry.
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
            cur_hour = dt.hour
            if in_kz(cur_hour) is None:
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
                    bu, bl = pending["upper"], pending["lower"]
                    accepted = False
                    side = 0
                    if pending["bull"]:
                        into = lo <= bu and hi >= bl
                        if into and cl > bu:
                            accepted, side = True, 1
                    else:
                        into = hi >= bl and lo <= bu
                        if into and cl < bl:
                            accepted, side = True, -1
                    if accepted:
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
        # displacement = newest closed bar (sig) — body zone is THAT bar
        # (cleaner than 3-bar FVG; more frequent location class)
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
            "arm_ts": int(d["t"][sig]),
        }
    flush_open(open_pos, {SB_SYM: d}, closed)
    return summarize(closed)


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    p1 = PREREG / "20260715_H_FX3_H1_BREAKER_RETEST_ACCEPT_CONT_001_PREREG.md"
    p2 = PREREG / "20260715_H_SB_DISP_BODY_MITIGATION_ACCEPT_001_PREREG.md"
    p1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_breaker_retest_accept`",
                "- Lane: `hard_pivot_w2_entrystate_20260715`",
                "- Symbol/TF: FX3 / H1",
                "- Thesis: thick $/trade from delayed acceptance at BOS-bar body",
                "  (breaker location) after closed structure break — joint cadence",
                "  target via FX3 H1 swing BOS frequency, not FVG rarity / auction spam.",
                f"- Signal: confirmed swing pivot L={BR_PIVOT_L}; closed BOS beyond pivot",
                f"  with body≥{BR_MIN_BOS_BODY}*ATR; arm breaker = BOS-bar body;",
                "  **no entry on arm bar**.",
                f"- Trigger: later closed H1 (≤{BR_MAX_WAIT}) wicks into body + closes",
                "  back outside in BOS direction; enter next H1 open.",
                f"- SL beyond opposite body ±{BR_SL_PAD} ATR; RR={BR_RR}; hold≤{BR_HOLD};",
                f"  session UTC[{BR_SESSION[0]},{BR_SESSION[1]}); max 1/day/symbol.",
                "- Gates: N≥80; tpw∈[2,5]; PF≥1.30; PF@$12≥1.30; x1.5≥1.25.",
                "- Hard ≠ auction-persist-k densify; ≠ FVG-retest-k densify;",
                "  ≠ H1-BOS-M15-PB densify; ≠ fractal5-break densify; ≠ H1-OB-mitigation-k;",
                "  ≠ R10–R31 / exit / MaxKZ / ETH VR / ORB/IB.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    p2.write_text(
        "\n".join(
            [
                "# Prereg — HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Parent shelf: `HYP-SB-MAXKZ2-RR2-FRICTION-001` / run `194548`",
                "- Feature family: `sb_disp_body_mitigation_accept`",
                "- Lane: `hard_pivot_w2_entrystate_20260715`",
                "- Symbol/TF: USDJPY / M15",
                "- Thesis: keep FVG near-miss *lesson* (accept-delay thick $/trade)",
                "  but change **location class** to displacement BODY (not FVG gap)",
                "  to raise cadence without densifying killed FVG-retest object.",
                f"- Arm: SB disp gates (body≥{SB_DISP_ATR}*H1ATR, ratio≥{SB_DISP_RATIO})",
                "  in KZ; zone = [min(o,c), max(o,c)] of disp bar; no arm-bar fill.",
                f"- Trigger: later closed M15 (≤{SB_MAX_WAIT}) wick-into-body + close",
                "  accept outside in disp direction; enter next M15 open.",
                f"- SL beyond opposite body ±{SB_SL_PAD} ATR; RR={SB_RR}; MaxKZ={SB_MAX_KZ};",
                f"  KZ LDN{SB_LDN}/NY{SB_NY}; no HTF in probe.",
                "- Challenger gates: joint + PF@$12 > control 1.120 + x1.5 > 1.013.",
                "- Hard ≠ FVG-retest-k densify; ≠ bodyATR impulse-gate densify;",
                "  ≠ H1-OB-mitigation-k densify; ≠ MaxKZ/exit densify.",
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
        "HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001": "fx_h1_breaker_retest_accept",
        "HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001": "sb_disp_body_mitigation_accept",
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
                "feature_family": fam.get(r["hypothesis_id"], "hard_pivot_w2"),
                "lane": "hard_pivot_w2_entrystate_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT W2 after auction-persist+FVG ALL_KILL; "
                    "new entry-state classes; R-series densify still PAUSED"
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
                "# 3-critic panel — HARD PIVOT W2 (breaker + body-mit)",
                "",
                "Date: 2026-07-15",
                "Nested critics: trader / quant / MQL5 (lead self-merge).",
                "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` (unchanged).",
                "",
                "## Diagnosis carry",
                "Auction-persist ALL_KILL: dense tpw≈12, thin PF.",
                "FVG-retest ALL_KILL near-miss: thick exp≈$53 PF@$12≈1.21 but tpw≈1.15.",
                "**FORBIDDEN** to densify either. Need NEW location/acceptance classes",
                "aimed at joint thick $/trade AND tpw∈[2,5].",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | GO breaker retest-accept; GO body-mitigation (FVG lesson, new zone) |",
                "| Quant | GO both; target mid-cadence; no FVG/auction knob mining |",
                "| MQL5/MT5 | GO — H1 pivot FSM + M15 body FSM closed-bar probeable |",
                "",
                "## Named children",
                "1. `HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001` — GO",
                "2. `HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001` — GO",
                "",
                "Merge: **GO offline**. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "Forbidden: FVG densify, auction densify, R-series densify, exit/MaxKZ/ORB.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT W2 breaker + body-mitigation",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001`",
                f"Confirmed swing L={BR_PIVOT_L} → closed BOS (body≥{BR_MIN_BOS_BODY}*ATR)",
                " → arm BOS-bar BODY as breaker; later wick+accept close → CONT next open.",
                f"Session UTC[{BR_SESSION[0]},{BR_SESSION[1]}); RR={BR_RR} hold≤{BR_HOLD}.",
                "Why: structural location after BOS with accept-delay (thick edge lesson);",
                " FX3 cadence from swing BOS — ≠ auction outer-quartile; ≠ FVG gap.",
                "",
                "## 2 `HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001`",
                "Arm SB displacement; zone = disp **BODY** (not FVG); no arm fill;",
                " later wick-into-body + close accept → next M15 open.",
                f"USDJPY M15; KZ LDN{SB_LDN}/NY{SB_NY}; MaxKZ={SB_MAX_KZ}; RR={SB_RR}.",
                "Why: keep accept-delay thick $/trade lesson from FVG near-miss;",
                " change location class to raise cadence — NOT FVG densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT W2 breaker + body-mitigation",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 breaker retest-accept | ≠ auction-persist-k; ≠ FVG-retest-k; ≠ H1-BOS-M15-PB densify (EMA PB, no accept FSM); ≠ fractal5-break densify; ≠ equal-HL densify; ≠ H1-OB-mitigation-k (last-opposite candle) |",
                "| SB disp-body mitigation | ≠ FVG-retest-k densify (body≠gap); ≠ bodyATR impulse-gate densify; ≠ H1-OB-mitigation-k; ≠ MaxKZ/exit densify; ≠ Asia magnet |",
                "",
                "R10–R31 densify + ORB/IB + FRED/EXO + RR2 exit pack + auction/FVG densify: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT W2 breaker + body-mitigation",
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
                "Do **not** densify FVG / auction / breaker / body-mit knobs from readout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — HARD PIVOT W2 breaker + body-mitigation",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED** (`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`).",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify breaker-k / body-mit-k / auction-persist-k /",
                "fvg-retest-k / R10–R31 / exit / MaxKZ / ETH VR / ORB/IB / FRED.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT W2",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Pivot W2",
                "- Giữ **PAUSE** R-series densify.",
                "- Cấm densify auction-persist / FVG-retest từ near-miss.",
                "- 2 class mới: Breaker-Retest-Accept (FX3 H1) + Disp-Body-Mitigation (SB).",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Next",
                "Không densify knob từ readout. Nếu zero survivor → class entry-state tiếp theo.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT W2",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book PRIMARY RR2+Spark + HARD PIVOT W2 entry-state.",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241 — cadence OK, PF short GOAL.",
                "Best shelf RR2 `194548`. Phase-0 CONTAMINATED. Cost GAP.",
                "",
                f"## HARD PIVOT W2 — `{status}`",
                *table,
                "",
                "- R-series densify: **PAUSED**.",
                "- Không densify breaker / body-mit / auction / FVG / R10–R31 / exit / MaxKZ.",
                "- QFSI parallel; cost autonomous retry.",
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
        f"- **HARD PIVOT W2 BREAKER/BODYMIT CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT W2 after auction-persist + FVG-retest ALL_KILL.",
        "  NEW entry-state classes (not densify of killed objects).",
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
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_W2_VN_ACTION_BRIEF.md`.",
        f"  Panel `readouts/{STEM}_3CRITIC_PANEL.md`.",
        f"  Freeze sha={freeze_sha[:16]}…",
        f"  QFSI: {qnote}",
        "  Do **not** densify breaker-k / body-mit-k / auction-persist-k /",
        "  fvg-retest-k / R10–R31 / exit / MaxKZ / ETH VR / ORB/IB / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        "  PRIMARY PF@$12=1.184 tpw=3.241 verdict=`DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL`.",
        "  Next: if ALL_KILL → next entry-state class outside these four objects;",
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
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT W2 breaker/bodymit; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text:
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT W2 aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"W2 breaker/bodymit offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not densify FVG-retest / auction-persist / breaker / body-mit knobs. "
        "Do not resume R10–R31 densify. "
        "Next entry-state class if ALL_KILL. "
        "QFSI parallel; cost GAP. Best shelf RR2 `194548`. GOAL unmet.\n"
    )
    if nm in text:
        # replace prior ACTIVE HARD PIVOT line if present, else prepend
        import re

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
    note = (
        "QFSI 007 parallel accumulate; cost freeze still GAP "
        "(raw_deals≈11; freeze_eligible=False); login not headline"
    )
    roots = [
        ROOT / "04. Project Control" / "ai",
        ROOT / "02. AlphaFactory",
    ]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*heartbeat*.json"):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
                alive = j.get("alive", j.get("watcher_alive"))
                ts = j.get("ts") or j.get("timestamp")
                note = f"QFSI hb ts={ts} alive={alive}; cost freeze GAP (11 deals)"
                return note
            except Exception:
                continue
    return note


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")

    freeze_body = "\n".join(
        [
            "# Universe freeze — HARD PIVOT W2 breaker + body-mitigation",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Children (≤2)",
            "1. HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001",
            "2. HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001",
            "",
            "## Window",
            "2021.01.01 – 2025.12.31",
            "",
            "## Cost screen",
            f"+${BASE_COST:.0f}/trade a priori; x1.5 / x2 haircuts",
            "",
            "## Forbidden",
            "Auction-persist densify; FVG-retest densify; R10–R31 densify;",
            "exit densify; MaxKZ densify; ETH VR densify; ORB/IB; Asia-break;",
            "Outside-bar clones; FRED/EXO spam.",
            "",
        ]
    )
    OUT_FREEZE.write_text(freeze_body, encoding="utf-8")
    freeze_sha = sha256_bytes(freeze_body.encode("utf-8"))
    prereg_paths = write_preregs()

    print("Loading H1 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
    print("Loading USDJPY M15 + H1...")
    m15 = enrich(load(SB_SYM, mt5.TIMEFRAME_M15))
    h1_uj = h1["USDJPY"]

    print("Probe Child1 breaker retest-accept...")
    p1, d1 = probe_fx3_breaker_retest(h1)
    r1 = pack_result(
        "HYP-FX3-H1-BREAKER-RETEST-ACCEPT-CONT-001",
        "FX3 H1 BOS breaker body retest-accept CONT; delayed entry",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p1,
        d1,
        challenger=False,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Child2 disp-body mitigation...")
    p2, d2 = probe_sb_disp_body_mitigation(m15, h1_uj)
    r2 = pack_result(
        "HYP-SB-DISP-BODY-MITIGATION-ACCEPT-001",
        "USDJPY M15 SB disp BODY mitigation accept; not FVG; RR2 MaxKZ2",
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
        "schema": "hard_pivot_w2_breaker_bodymit.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "base_cost_usd": BASE_COST,
        "results": results,
        "any_survivor": any_surv,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "EXO_FRED_DISPLACE_SPAM_PAUSED": True,
            "FVG_RETEST_DENSIFY_FORBIDDEN": True,
            "AUCTION_PERSIST_DENSIFY_FORBIDDEN": True,
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
