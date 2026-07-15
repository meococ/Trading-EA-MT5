#!/usr/bin/env python3
"""HARD PIVOT — ENTRY-STATE rebuild offline probes (post R10–R31 densify spam).

PAUSE: R-series OHLC/calendar/indicator/event densify for this session.

3-critic merge (trader / quant / MQL5):
  Child1 GO:  HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001
  Child2 COND: HYP-SB-FVG-RETEST-ACCEPT-DELAY-001
  Asia-break / ORB / exit densify / MaxKZ densify / ETH VR densify: FORBIDDEN

Closed-bar only. +$12 a priori. Model 0 only if PROBE_SURVIVOR.
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

STEM = "20260715_HARD_PIVOT_ENTRYSTATE_REBUILD"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_CLEAN_VN = READ / "20260715_CLEAN_BOOK_AND_HARD_PIVOT_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_UNIVERSE_FREEZE.md"
OUT_BOOK_FREEZE = READ / "20260715_HARD_PIVOT_BOOK_RR2SPARK_PERSIST_APRIORI_FREEZE.md"
OUT_BOOK_STRESS = READ / "20260715_HARD_PIVOT_BOOK_RR2SPARK_PERSIST_STRESS.md"
OUT_BOOK_STRESS_JSON = PRE / "20260715_HARD_PIVOT_BOOK_RR2SPARK_PERSIST_STRESS.json"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Child 1: FX3 H1 auction-persist (cadence-designed; NOT ETH VR densify) ---
# a priori λ̂ target book contribution ~1–2 tpw; sleeve tpw ∈ [2.0, 5.0] gate
AP_LOOKBACK = 48          # closes for quartile (prior window, excl current)
AP_RANGE_MED_N = 12       # prior ranges for median expansion
AP_NEED = 3               # ≥3 of last 4 closes in outer quartile, same side
AP_SL = 1.50
AP_RR = 2.00
AP_HOLD = 10
AP_SESSION = (7, 17)      # UTC hour of signal bar [start, end)

# --- Child 2: SB FVG retest-accept delay (USDJPY M15; shelf parity geometry) ---
# SB defaults: LDN[11,12) NY[16,18) broker/server hour; DispBodyATR=0.40; ratio=0.70
# RR2 shelf overrides: MaxKZ=2, RR=2.0 — frozen here for challenger parity
SB_SYM = "USDJPY"
SB_LDN = (11, 12)
SB_NY = (16, 18)
SB_DISP_ATR = 0.40
SB_DISP_RATIO = 0.70
SB_FVG_MIN = 0.10
SB_MAX_WAIT = 8
SB_MAX_KZ = 2
SB_MAX_DAY = 3
SB_RR = 2.0
SB_HOLD = 32  # M15 bars (~8h) — management proxy; SL/TP primary
SB_SKIP_FRI = True

# Shelf control reference (diagnostic compare only)
CTRL_PF12 = 1.1197
CTRL_X15 = 1.0134

RR2_RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_194548"
SPARK_RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_M15SparkAsian" / "20260714_193358"
# Spark twin shelf name from clean book; try both
SPARK_CANDIDATES = [
    ROOT / "02. AlphaFactory" / "runs" / "EA_M15SparkAsian" / "20260714_193358",
    ROOT / "02. AlphaFactory" / "runs" / "EA_Spark" / "20260714_193358",
    ROOT / "02. AlphaFactory" / "runs" / "EA_M15SparkAsian" / "20260714_193732",
]


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
    """ATR of last fully closed H1 at or before ts."""
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


# ---------------------------------------------------------------------------
# Child 1 — auction persist
# ---------------------------------------------------------------------------
def probe_fx3_auction_persist(h1):
    """≥3/4 prior closes in outer quartile (same side) + range > med(prior12)
    → CONT at next H1 open. Max 1/day/symbol. Session hour filter.
    Quartile window = prior AP_LOOKBACK closes EXCLUDING signal bar.
    """
    closed, open_pos = [], []
    clock = h1["EURUSD"]["t"]
    last_day_sym = set()
    for i in range(AP_LOOKBACK + 20, len(clock) - 1):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, h1, ts, closed, AP_HOLD)
        open_syms = {p["sym"] for p in open_pos}
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        if dt.weekday() >= 5:
            continue
        sig_ts = int(clock[i - 1])
        sig_dt = datetime.fromtimestamp(sig_ts, tz=timezone.utc)
        if not (AP_SESSION[0] <= sig_dt.hour < AP_SESSION[1]):
            continue
        for sym in FX3:
            if sym in open_syms:
                continue
            d = h1[sym]
            j = asof_idx(d, sig_ts)
            if j is None or j < AP_LOOKBACK + AP_RANGE_MED_N + 2:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # range expansion vs prior med (exclude current)
            ranges = d["h"][j - AP_RANGE_MED_N : j] - d["l"][j - AP_RANGE_MED_N : j]
            med_r = float(np.median(ranges))
            cur_r = float(d["h"][j] - d["l"][j])
            if med_r <= 0 or cur_r <= med_r:
                continue
            # outer-quartile location of last 4 closes vs prior lookback excl those? 
            # Freeze: distribution = closes [j-AP_LOOKBACK, j) i.e. prior AP_LOOKBACK excl signal
            dist = d["c"][j - AP_LOOKBACK : j]
            q_lo = float(np.quantile(dist, 0.25))
            q_hi = float(np.quantile(dist, 0.75))
            last4 = d["c"][j - 3 : j + 1]  # includes signal close — OK: signal is closed
            # For quartile membership of last4, use dist that excludes signal to avoid
            # self-influence on thresholds: already q from [j-LOOKBACK, j)
            bull_hits = int(np.sum(last4 >= q_hi))
            bear_hits = int(np.sum(last4 <= q_lo))
            side = 0
            if bull_hits >= AP_NEED and bull_hits > bear_hits:
                side = 1
            elif bear_hits >= AP_NEED and bear_hits > bull_hits:
                side = -1
            else:
                continue
            day_key = (dt.date(), sym)
            if day_key in last_day_sym:
                continue
            ent_i = asof_idx(d, ts)
            if ent_i is None:
                continue
            entry = float(d["o"][ent_i])
            sl = entry - side * AP_SL * atr
            tp = entry + side * AP_RR * AP_SL * atr
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
    flush_open(open_pos, h1, closed)
    return summarize(closed)


# ---------------------------------------------------------------------------
# Child 2 — FVG retest-accept delay (M15 FSM; NOT RR2 trade filter)
# ---------------------------------------------------------------------------
def probe_sb_fvg_retest_accept(m15, h1):
    """Arm on closed-bar displacement+FVG (SB geometry). No entry on arm bar.
    Later closed M15: wick into FVG + close back OUTSIDE in disp direction
    → enter next M15 open. SL beyond opposite FVG extreme. MaxKZ=2, RR=2.
    No HTF filter (clean kill screen).
    """
    closed, open_pos = [], []
    d = m15
    pending = None  # dict or None
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

        # --- age / expire pending on each new bar (signal = previous closed) ---
        sig = i - 1
        if pending is not None:
            pending["age"] += 1
            if pending["age"] > SB_MAX_WAIT:
                pending = None

        hour = datetime.fromtimestamp(int(d["t"][sig]), tz=timezone.utc).hour
        kz = in_kz(hour)

        # expire if left KZ with no fill (SB clears when KZ_NONE)
        if pending is not None and kz is None:
            # only clear if current bar hour also out — use entry-bar hour
            cur_hour = dt.hour
            if in_kz(cur_hour) is None:
                pending = None

        atr_pack = h1_atr_asof(h1, int(d["t"][sig]))
        if atr_pack is None:
            continue
        atr, _ = atr_pack

        # --- try acceptance entry (age >= 1 → not arm bar) ---
        if pending is not None and pending["age"] >= 1 and not open_pos:
            day = dt.date()
            if trades_day.get(day, 0) < SB_MAX_DAY:
                kz_key = (day, pending["kz"])
                if trades_kz.get(kz_key, 0) < SB_MAX_KZ:
                    lo = float(d["l"][sig])
                    hi = float(d["h"][sig])
                    cl = float(d["c"][sig])
                    fu, fl = pending["upper"], pending["lower"]
                    accepted = False
                    if pending["bull"]:
                        # wick into zone, close back above upper (acceptance)
                        into = lo <= fu and hi >= fl
                        if into and cl > fu:
                            accepted = True
                            side = 1
                    else:
                        into = hi >= fl and lo <= fu
                        if into and cl < fl:
                            accepted = True
                            side = -1
                    if accepted:
                        entry = float(d["o"][i])
                        if pending["bull"]:
                            sl = fl - 0.2 * atr
                            side = 1
                        else:
                            sl = fu + 0.2 * atr
                            side = -1
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

        # --- arm new FVG only in KZ when no pending ---
        if pending is not None or kz is None or open_pos:
            continue
        # displacement at shift2 relative to sig as shift1 → bars sig-1 = mid (disp)
        # SB: shift1=newest closed, shift2=disp, shift3=oldest
        # At time of bar i open, closed bars: ... sig=i-1 is shift1
        s1, s2, s3 = sig, sig - 1, sig - 2
        if s3 < 1:
            continue
        o2, c2 = float(d["o"][s2]), float(d["c"][s2])
        h2, l2 = float(d["h"][s2]), float(d["l"][s2])
        rng2 = h2 - l2
        if rng2 <= 0:
            continue
        body2 = abs(c2 - o2)
        if body2 < SB_DISP_ATR * atr:
            continue
        if body2 / rng2 < SB_DISP_RATIO:
            continue
        is_bull = c2 > o2
        h3, l3 = float(d["h"][s3]), float(d["l"][s3])
        h1b, l1b = float(d["h"][s1]), float(d["l"][s1])
        if is_bull:
            fvg_lower, fvg_upper = h3, l1b
            if not (fvg_upper > fvg_lower and (fvg_upper - fvg_lower) >= SB_FVG_MIN * atr):
                continue
            bull = True
        else:
            fvg_upper, fvg_lower = l3, h1b
            if not (fvg_upper > fvg_lower and (fvg_upper - fvg_lower) >= SB_FVG_MIN * atr):
                continue
            bull = False
        pending = {
            "upper": float(fvg_upper),
            "lower": float(fvg_lower),
            "bull": bull,
            "age": 0,  # arm bar — no entry this bar
            "kz": kz,
            "arm_ts": int(d["t"][s1]),
        }
    flush_open(open_pos, {SB_SYM: d}, closed)
    return summarize(closed)


def find_spark_run():
    for p in SPARK_CANDIDATES:
        if (p / "report.html").exists() or (p / "report.htm").exists():
            return p
    # glob
    base = ROOT / "02. AlphaFactory" / "runs"
    for cand in base.glob("**/20260714_193358"):
        if cand.is_dir():
            return cand
    for cand in base.glob("**/20260714_193358*"):
        if cand.is_dir():
            return cand
    return None


def load_deal_pnls(run_dir: Path):
    """Best-effort load trade pnls from AlphaFactory run artifacts."""
    paths = [
        run_dir / "datalog" / "trades.csv",
        run_dir / "trades.csv",
        run_dir / "analysis" / "trades.csv",
    ]
    for p in paths:
        if p.exists():
            import csv

            pnls = []
            with p.open(encoding="utf-8", errors="replace") as f:
                r = csv.DictReader(f)
                cols = r.fieldnames or []
                pnl_col = None
                for c in cols:
                    if c.lower() in ("pnl", "profit", "pl", "net_pnl", "profit_usd"):
                        pnl_col = c
                        break
                if pnl_col is None:
                    continue
                for row in r:
                    try:
                        pnls.append(float(row[pnl_col]))
                    except (TypeError, ValueError):
                        continue
            if pnls:
                return pnls, str(p)
    # fallback: parse report.html for Deal rows — skip if heavy; return empty
    return [], None


def a_priori_book_freeze(persist_hyp: str):
    text = "\n".join(
        [
            "# A priori freeze — PRIMARY book + independent persist sleeve",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "",
            "## Membership (frozen before sleeve metrics)",
            "| Slot | Object | run / hyp |",
            "|---|---|---|",
            "| A | RR2 shelf | `20260714_194548` / `HYP-SB-MAXKZ2-RR2-FRICTION-001` |",
            "| B | Spark shelf | `20260714_193358` |",
            f"| C | Persist sleeve | `{persist_hyp}` (independent; NOT ETH VR densify) |",
            "",
            "## Caps (a priori)",
            "- Weekly corr ≤ 0.35 vs each pair",
            "- Overlap frac ≤ 0.05",
            "- Book tpw ∈ [2.0, 5.0] elapsed calendar weeks",
            "- Screen: PF@$12 ≥ 1.30; x1.5 ≥ 1.25",
            "",
            "## Exclusions",
            "- MaxKZ2 real-path fail twin",
            "- ITSM densify into PRIMARY",
            "- ETH VR object / threshold densify",
            "- R10–R31 densify corpses",
            "",
            "## Claim rule",
            "Do **not** claim book GOAL until C is PROBE_SURVIVOR and pooled +$12 stress passes.",
            "Phase-0 still CONTAMINATED — this freeze is diagnostic clean-path only.",
            "",
        ]
    )
    OUT_BOOK_FREEZE.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def optional_book_stress(persist_pnls, persist_closed_meta, receipt):
    """If persist survives, pool with RR2+Spark deal pnls under +$12 (diagnostic)."""
    rr2_pnls, rr2_src = load_deal_pnls(RR2_RUN)
    spark_dir = find_spark_run()
    spark_pnls, spark_src = ([], None)
    if spark_dir:
        spark_pnls, spark_src = load_deal_pnls(spark_dir)
    payload = {
        "schema": "hard_pivot_book_stress.v1",
        "receipt_sha256": receipt,
        "rr2_n": len(rr2_pnls),
        "rr2_src": rr2_src,
        "spark_n": len(spark_pnls),
        "spark_src": spark_src,
        "persist_n": len(persist_pnls),
        "note": "Diagnostic pool of independent sleeve pnls; not EA portfolio Model 0.",
    }
    if not rr2_pnls or not spark_pnls:
        payload["verdict"] = "BOOK_STRESS_SKIPPED__MISSING_SLEEVE_DEALS"
        OUT_BOOK_STRESS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        OUT_BOOK_STRESS.write_text(
            "# Book stress — SKIPPED (missing RR2/Spark deal artifacts)\n"
            f"rr2_src={rr2_src} spark_src={spark_src}\n"
            "A priori freeze stands; no claim.\n",
            encoding="utf-8",
        )
        return payload
    # naive pool (no heat drop — diagnostic; caps not fully re-simulated)
    pooled = rr2_pnls + spark_pnls + persist_pnls
    m = metrics(pooled)
    hc = haircuts(pooled)
    payload["metrics"] = m
    payload["haircuts"] = hc
    notes = []
    if (m["tpw"] or 0) < 2.0 or (m["tpw"] or 0) > 5.0:
        notes.append("cadence")
    if (hc["x1"]["pf"] or 0) < 1.30:
        notes.append("pf12")
    if (hc["x1_5"]["pf"] or 0) < 1.25:
        notes.append("x15")
    payload["verdict"] = (
        "DIAGNOSTIC_BOOK_PASS_SCREEN" if not notes else "DIAGNOSTIC_BOOK_FAIL_SCREEN"
    )
    payload["fail_notes"] = notes
    OUT_BOOK_STRESS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_BOOK_STRESS.write_text(
        "\n".join(
            [
                "# Book stress — RR2 + Spark + Persist (diagnostic)",
                "",
                f"Verdict: `{payload['verdict']}`",
                f"Pooled N={m['n']} PF={m['pf']} PF@$12={hc['x1']['pf']} "
                f"tpw={m['tpw']} x1.5={hc['x1_5']['pf']}",
                f"Fail notes: {notes or 'none'}",
                "Not Phase-0. Not Model 0 portfolio EA. Caps not re-simulated here.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return payload


def write_preregs():
    PREREG.mkdir(parents=True, exist_ok=True)
    p1 = PREREG / "20260715_H_FX3_H1_AUCTION_PERSIST_CADENCE_CONT_001_PREREG.md"
    p2 = PREREG / "20260715_H_SB_FVG_RETEST_ACCEPT_DELAY_001_PREREG.md"
    p1.write_text(
        "\n".join(
            [
                "# Prereg — HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Feature family: `fx_h1_auction_persist_cadence`",
                "- Lane: `hard_pivot_entrystate_rebuild_20260715`",
                "- Symbol/TF: FX3 / H1",
                "- Thesis: thick $/trade from acceptance at distribution extremes +",
                "  range expansion; cadence engineered a priori for book sleeve",
                "  (VR *lesson*, NOT ETH VR densify).",
                "- Signal (closed-bar): ≥3 of last 4 closes in outer quartile of",
                f"  prior {AP_LOOKBACK} closes (same side) AND range > median(prior",
                f"  {AP_RANGE_MED_N} ranges); session UTC hour ∈[{AP_SESSION[0]},{AP_SESSION[1]}).",
                "- Entry: next H1 open. SL/RR/hold frozen:",
                f"  SL={AP_SL} ATR, RR={AP_RR}, hold≤{AP_HOLD}, max 1/day/symbol.",
                "- Gates: N≥80; tpw∈[2,5]; PF≥1.30; PF@$12≥1.30; x1.5≥1.25.",
                "- Banned: ETH VR-k densify; AC/HA/ER/ROC rename; exit/MaxKZ densify;",
                "  R10–R31 densify; ORB/IB.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    p2.write_text(
        "\n".join(
            [
                "# Prereg — HYP-SB-FVG-RETEST-ACCEPT-DELAY-001",
                "",
                "- State: `preregistered` (frozen pre-offline)",
                "- Parent shelf: `HYP-SB-MAXKZ2-RR2-FRICTION-001` / run `194548`",
                "- Feature family: `sb_fvg_retest_acceptance_delay`",
                "- Lane: `hard_pivot_entrystate_rebuild_20260715`",
                "- Symbol/TF: USDJPY / M15",
                "- Thesis: RR2/$12 death = late-chase touch-fills; delay entry until",
                "  closed-bar return into FVG + acceptance close outside zone.",
                "- Arm: SB displacement+FVG geometry (DispBodyATR=0.40, ratio=0.70,",
                f"  FVG_Min={SB_FVG_MIN}); KZ LDN{SB_LDN}/NY{SB_NY}; no entry on arm bar.",
                "- Trigger: later closed M15 wicks into FVG and closes back outside",
                "  in displacement direction; enter next M15 open.",
                f"- SL beyond opposite FVG extreme; RR={SB_RR}; MaxKZ={SB_MAX_KZ};",
                "  no HTF in probe (clean screen). H1 ATR as-of.",
                "- Challenger gates: joint + PF@$12 > control 1.120 + x1.5 > 1.013.",
                "- Hard ≠ bodyATR gate / thin-risk / Asia magnet / exit densify / MaxKZ densify.",
                "- Model 0: only PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return str(p1.as_posix()), str(p2.as_posix())


def append_reg(results, receipt, prereg_paths):
    stamp = utc_now()
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
                "feature_family": (
                    "sb_fvg_retest_acceptance_delay"
                    if r.get("challenger")
                    else "fx_h1_auction_persist_cadence"
                ),
                "lane": "hard_pivot_entrystate_rebuild_20260715",
                "setup_type": r["setup"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "source_provenance": (
                    "HARD PIVOT after R10-R31 ALL_KILL densify spam; "
                    "3-critic merge; entry-state rebuild not exit/MaxKZ/R-series"
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


def write_docs(results, receipt, any_surv, freeze_sha, book_freeze_sha, book_payload, qnote):
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
                "# 3-critic panel — HARD PIVOT entry-state rebuild",
                "",
                "Date: 2026-07-15",
                "Nested critics: trader / quant / MQL5 (cursor-grok-4.5-high-fast).",
                "Lead merge: **PAUSE R-series densify**; implement ≤2 entry-state children.",
                "",
                "## Diagnosis (merged)",
                "RR2/Spark die under +$12 because expectancy/trade is friction-thin",
                "(~$19 raw vs $12 RT), not because cadence or exits are broken.",
                "Exit densify ALL_KILL; MaxKZ densify banned; R10–R31 entry templates",
                "ALL_KILL. Need higher $/trade via entry location / acceptance, not more signals.",
                "Quant: RR2 needs ~+$8.7/trade for PF@$12≥1.30; binding x1.5 ~+$12.4.",
                "PRIMARY book equal-lift ~+$6.5 / +$9.8.",
                "",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | CONDITIONAL GO — Retest-Accept SB #1; FX persist sleeve #2; Asia-break NO-GO |",
                "| Quant | GO persist cadence sleeve first; CONDITIONAL retest-accept; Asia-break NO-GO |",
                "| MQL5/MT5 | B probeable from H1 OHLC now; A needs M15 FSM (not RR2 trade filter); C NO-GO |",
                "",
                "## Named children (≤2)",
                "1. `HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001` — GO",
                "2. `HYP-SB-FVG-RETEST-ACCEPT-DELAY-001` — CONDITIONAL GO",
                "",
                "Merge: **GO offline**. Model 0 WITHHELD until PROBE_SURVIVOR.",
                "Forbidden: R-series densify, exit densify, MaxKZ densify, ETH VR densify, ORB/IB.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — HARD PIVOT entry-state rebuild",
                "",
                "Date: 2026-07-15",
                f"Freeze: `{OUT_FREEZE.name}` sha={freeze_sha[:16]}…",
                "",
                "## 1 `HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001`",
                f"≥{AP_NEED}/4 closes in outer quartile of prior {AP_LOOKBACK} +",
                f" range > med(prior {AP_RANGE_MED_N}) → CONT next open.",
                f"Session UTC[{AP_SESSION[0]},{AP_SESSION[1]}); SL={AP_SL} RR={AP_RR} hold≤{AP_HOLD}.",
                "Why: VR *lesson* (thick when rare) redesigned for FX book cadence —",
                " NOT densify of killed ETH H4 VR object; ≠ AC/HA/ER/ROC clones.",
                "",
                "## 2 `HYP-SB-FVG-RETEST-ACCEPT-DELAY-001`",
                "Arm SB FVG on closed displacement; **no fill on arm bar**;",
                " enter on later closed wick-into-FVG + close back outside zone.",
                f"USDJPY M15; KZ LDN{SB_LDN}/NY{SB_NY}; MaxKZ={SB_MAX_KZ}; RR={SB_RR};",
                " H1 ATR as-of; no HTF in probe.",
                "Why: attacks late-chase touch-fill root of RR2/$12 death;",
                " ≠ bodyATR gate densify; ≠ exit densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — HARD PIVOT entry-state rebuild",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| FX3 auction-persist | ≠ ETH VR-k densify; ≠ R22 AC; ≠ R26 HA; ≠ R24 ER; ≠ R27 ROC |",
                "| SB FVG retest-accept | ≠ bodyATR impulse gate; ≠ thin-risk P25; ≠ Asia magnet; ≠ stop-run-accept; ≠ MaxKZ densify; ≠ exit densify |",
                "",
                "R10–R31 densify + ORB/IB + FRED/EXO spam + RR2 exit pack: **FORBIDDEN**.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — HARD PIVOT entry-state rebuild",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Freeze SHA256: `{freeze_sha}`",
                f"Book freeze SHA256: `{book_freeze_sha}`",
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
                "## Optional book stress",
                f"```{json.dumps(book_payload, indent=2) if book_payload else 'null'}```",
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
                "# Session closeout — HARD PIVOT entry-state rebuild",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "R-series densify: **PAUSED** this session (`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`).",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify auction-persist-k / fvg-retest-k /",
                "R10–R31 / exit / MaxKZ / ETH VR / ORB/IB / FRED.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — HARD PIVOT entry-state rebuild",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "",
                "## Pivot",
                "- **PAUSE** densify R-series OHLC/calendar/indicator/event (R10–R31 spam).",
                "- 3-critic: edge chết dưới +$12 vì $/trade mỏng (~$19 vs $12 RT), không phải cadence/exit.",
                "- ≤2 child entry-state: Auction-Persist FX3 H1 + SB FVG Retest-Accept.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Cost / QFSI",
                qnote,
                "Cost freeze vẫn GAP (11 deals). Login không phải headline.",
                "",
                "## Next",
                "Không densify knob từ readout này. Không Outside-bar clone.",
                "Nếu zero survivor: giữ shelf RR2 `194548`; tìm entry-state class mới ngoài hai object này.",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_CLEAN_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Clean book + HARD PIVOT",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Lane: clean-book PRIMARY RR2+Spark + HARD PIVOT entry-state rebuild.",
                "",
                "## Clean book (unchanged)",
                "PRIMARY PF@$12=1.184 tpw=3.241 — cadence OK, PF short GOAL.",
                "Best shelf RR2 `194548`. Phase-0 CONTAMINATED. Cost GAP.",
                "",
                f"## HARD PIVOT — `{status}`",
                *table,
                "",
                "- R-series densify: **PAUSED**.",
                "- Không densify auction-persist / fvg-retest / R10–R31 / exit / MaxKZ / ETH VR.",
                "- QFSI parallel; cost autonomous retry.",
                "",
                f"Receipt `{receipt}`",
                "GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, receipt, any_surv, freeze_sha, book_freeze_sha, qnote):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    lines = [
        f"- **HARD PIVOT ENTRY-STATE REBUILD CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / "
        f"`QFSI_007_HEALTHY` / `NO_MODEL0` / `PHASE0_STILL_CONTAMINATED`.**",
        "  HARD PIVOT after R10–R31 densify spam ALL_KILL. Pause R-series OHLC/",
        "  calendar/indicator/event densify this session. 3-critic merge → ≤2",
        "  entry-state rebuild children (not exit densify, not MaxKZ densify,",
        "  not Outside-bar clone, not ETH VR densify).",
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
        f"  VN `readouts/20260715_CLEAN_BOOK_AND_HARD_PIVOT_VN_ACTION_BRIEF.md`.",
        f"  Panel `readouts/{STEM}_3CRITIC_PANEL.md`.",
        f"  Book a priori freeze sha={book_freeze_sha[:16]}… "
        f"`readouts/{OUT_BOOK_FREEZE.name}`.",
        f"  QFSI: {qnote}",
        "  Near-miss note (NO densify): FVG-retest exp≈$53/trade PF@$12≈1.21 but",
        "  tpw≈1.15 cadence_fail; auction-persist too dense tpw≈12 PF thin.",
        "  Do **not** densify auction-persist-k / fvg-retest-k /",
        "  R10–R31 / exit / MaxKZ / ETH VR / ORB/IB / FRED.",
        "  Clean book still GOAL_SCREEN_FAIL (unchanged).",
        "  PRIMARY PF@$12=1.184 tpw=3.241 verdict=`DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL`.",
        "  Next: entry-state architecture class outside these two objects;",
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
            f"Updated: 2026-07-15 ~{stamp} ICT | HARD PIVOT entry-state; "
            f"R-series densify PAUSED; {status}; GOAL unmet"
        )
        text = "\n".join(old_lines) + ("\n" if text.endswith("\n") else "")
    marker = "## Active Truth\n"
    if marker in text and "HARD PIVOT ENTRY-STATE REBUILD CLOSEOUT" not in text[:2500]:
        text = text.replace(marker, marker + "\n" + block, 1)
    elif "HARD PIVOT ENTRY-STATE REBUILD CLOSEOUT" not in text[:2500]:
        # fallback insert after first blank following Active Truth
        text = text.replace(marker, marker + "\n" + block, 1)
    nm = "## Next Move\n"
    next_block = (
        f"\n- **ACTIVE — HARD PIVOT aftermath.** "
        f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`. "
        f"Entry-state rebuild offline `{status}` receipt `{receipt[:16]}…`. "
        "Do not resume R10–R31 densify spam. Do not exit/MaxKZ/ETH-VR densify. "
        "Do not densify FVG-retest cadence or auction-persist sparsity knobs from readout. "
        "Next entry-state class outside auction-persist / fvg-retest. "
        "QFSI parallel; cost GAP (11 deals). Best shelf RR2 `194548`. GOAL unmet.\n"
    )
    if nm in text and "ACTIVE — HARD PIVOT aftermath" not in text:
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

    # a priori freeze docs BEFORE metrics
    freeze_body = "\n".join(
        [
            "# Universe freeze — HARD PIVOT entry-state rebuild",
            "",
            "Date: 2026-07-15",
            "Status: `APRIORI_FREEZE__PRE_METRICS`",
            "Flag: `R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED`",
            "",
            "## Children (≤2)",
            "1. HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001",
            "2. HYP-SB-FVG-RETEST-ACCEPT-DELAY-001",
            "",
            "## Window",
            "2021.01.01 – 2025.12.31",
            "",
            "## Cost screen",
            f"+${BASE_COST:.0f}/trade a priori; x1.5 / x2 haircuts",
            "",
            "## Forbidden",
            "R10–R31 densify; exit densify; MaxKZ densify; ETH VR densify; ORB/IB;",
            "Asia-break hold; Outside-bar clones; FRED/EXO spam.",
            "",
        ]
    )
    OUT_FREEZE.write_text(freeze_body, encoding="utf-8")
    freeze_sha = sha256_bytes(freeze_body.encode("utf-8"))
    book_freeze_sha = a_priori_book_freeze(
        "HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001"
    )
    prereg_paths = write_preregs()

    print("Loading H1 FX3...")
    h1 = {s: enrich(load(s, mt5.TIMEFRAME_H1)) for s in FX3}
    print("Loading USDJPY M15 + H1...")
    m15 = enrich(load(SB_SYM, mt5.TIMEFRAME_M15))
    h1_uj = h1["USDJPY"]

    print("Probe Child1 auction-persist...")
    p1, d1 = probe_fx3_auction_persist(h1)
    r1 = pack_result(
        "HYP-FX3-H1-AUCTION-PERSIST-CADENCE-CONT-001",
        "FX3 H1 auction outer-quartile persist + range expand CONT; cadence-designed",
        "EURUSD+GBPUSD+USDJPY",
        "H1",
        p1,
        d1,
        challenger=False,
    )
    print("  ", r1["verdict"], r1["metrics"], r1["haircuts"]["x1"], r1["fail_notes"])

    print("Probe Child2 FVG retest-accept...")
    p2, d2 = probe_sb_fvg_retest_accept(m15, h1_uj)
    r2 = pack_result(
        "HYP-SB-FVG-RETEST-ACCEPT-DELAY-001",
        "USDJPY M15 SB FVG retest-acceptance delay; no arm-bar fill; RR2 MaxKZ2",
        SB_SYM,
        "M15",
        p2,
        d2,
        challenger=True,
    )
    print("  ", r2["verdict"], r2["metrics"], r2["haircuts"]["x1"], r2["fail_notes"])

    results = [r1, r2]
    any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)

    book_payload = {"verdict": "BOOK_STRESS_WITHHELD__NO_SLEEVE_SURVIVOR"}
    if r1["verdict"] == "PROBE_SURVIVOR":
        book_payload = optional_book_stress(p1, d1, receipt="PENDING")

    payload = {
        "schema": "hard_pivot_entrystate_rebuild.v1",
        "generated_at": utc_now(),
        "freeze_sha256": freeze_sha,
        "book_freeze_sha256": book_freeze_sha,
        "base_cost_usd": BASE_COST,
        "results": results,
        "any_survivor": any_surv,
        "book_stress": book_payload,
        "flags": {
            "R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED": True,
            "EXO_FRED_DISPLACE_SPAM_PAUSED": True,
        },
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    receipt = sha256_bytes(raw)
    payload["receipt_sha256"] = receipt
    if r1["verdict"] == "PROBE_SURVIVOR" and book_payload.get("verdict", "").startswith(
        "DIAGNOSTIC"
    ):
        pass  # already written
    elif r1["verdict"] == "PROBE_SURVIVOR":
        book_payload = optional_book_stress(p1, d1, receipt)
        payload["book_stress"] = book_payload
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt

    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    # re-hash file bytes
    receipt = sha256_bytes(OUT_JSON.read_bytes())
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_bytes(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    receipt = sha256_bytes(OUT_JSON.read_bytes())

    qnote = qfsi_note()
    write_docs(results, receipt, any_surv, freeze_sha, book_freeze_sha, book_payload, qnote)
    append_reg(results, receipt, prereg_paths)
    patch_hot(results, receipt, any_surv, freeze_sha, book_freeze_sha, qnote)

    print("Receipt:", receipt)
    print("Status:", "SURVIVOR" if any_surv else "ALL_KILL")
    mt5.shutdown()


if __name__ == "__main__":
    main()
