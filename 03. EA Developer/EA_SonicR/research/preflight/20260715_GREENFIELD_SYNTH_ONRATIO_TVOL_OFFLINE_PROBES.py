#!/usr/bin/env python3
"""Round 9 greenfield — outside unpark + R1–R8 densify boards.

FORBIDDEN densify:
  ≠ Unpark W1/M15 · FX3 H4 R1–R5 · triad parity-z · NAS β · metal
  ≠ CHF risk · AUD COM3 · ADR · corr-recouple · yen-cross β · Parkinson (R8)
  ≠ XS/AUDNZD/AONIA/CORRA/thin3/carry/D1-vol/LNY/FRED/WTI
  ≠ Weekly-HL/VWAP/NR7/ORB/SB/exit/TOM/weekend-gap/consec

A priori (≥3 named; probe top 3), +$12 joint, Model 0 only if PROBE_SURVIVOR:
  1) HYP-EURUSD-H1-YENCROSS-SYNTH-RESID-FADE-001
  2) HYP-FX3-H1-OVERNIGHT-RATIO-CONT-001
  3) HYP-FX3-H1-TICKVOL-CLIMAX-FADE-001

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

OUT_JSON = PRE / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_3CRITIC_PANEL.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- 1 EURUSD vs yen-cross synthetic residual fade ---
SYN_Z_LB = 60
SYN_Z_ENTRY = 1.75
SYN_SL = 1.2
SYN_RR = 2.0
SYN_HOLD = 24
SYN_FIRE_UTC = 12
SYN_MAX_PER_DAY = 1

# --- 2 Overnight / intraday ratio continuation ---
ON_ASIA_END = 7  # UTC hours [0,7) = overnight proxy vs prior NY
ON_RATIO = 0.65
ON_MIN_ATR = 0.35  # |ON| move in ATR units
ON_SL = 1.2
ON_RR = 2.0
ON_HOLD = 16
ON_FIRE_UTC = 8  # London
ON_MAX_PER_DAY = 1

# --- 3 Tick-volume climax fade ---
TV_Z_LB = 60
TV_Z_ENTRY = 2.5
TV_BODY_ATR = 1.0
TV_SL = 1.2
TV_RR = 1.5
TV_HOLD = 12
TV_FIRE_UTC = 14
TV_MAX_PER_DAY = 1


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


def rolling_z(x: np.ndarray, lb: int) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    finite_vals: list[float] = []
    for i, v in enumerate(x):
        if np.isfinite(v):
            finite_vals.append(float(v))
            if len(finite_vals) > lb:
                finite_vals = finite_vals[-lb:]
            if len(finite_vals) < lb:
                continue
            w = np.asarray(finite_vals, dtype=float)
            mu = float(np.mean(w))
            sd = float(np.std(w, ddof=1))
            if sd <= 1e-12:
                continue
            out[i] = (w[-1] - mu) / sd
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
        "tv": rates["tick_volume"].astype(float),
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


def align_on(clock_t, d):
    idx = np.searchsorted(d["t"], clock_t, side="left")
    out = np.full(len(clock_t), -1, dtype=np.int64)
    for i, (j, ts) in enumerate(zip(idx, clock_t)):
        if j < len(d["t"]) and d["t"][j] == ts:
            out[i] = j
    return out


def probe_yen_synth_resid(data):
    """Identity residual: ln(EURUSD) - (ln(EURJPY) - ln(USDJPY))."""
    closed = []
    open_pos = []
    eu = data["EURUSD"]
    ej = data["EURJPY"]
    uj = data["USDJPY"]
    clock = eu["t"]
    ie = align_on(clock, ej)
    iu = align_on(clock, uj)
    spread = np.full(len(clock), np.nan, dtype=float)
    for i in range(len(clock)):
        if ie[i] < 0 or iu[i] < 0:
            continue
        if ej["t"][ie[i]] != clock[i] or uj["t"][iu[i]] != clock[i]:
            continue
        ce, cj, cu = eu["c"][i], ej["c"][ie[i]], uj["c"][iu[i]]
        if min(ce, cj, cu) <= 0:
            continue
        spread[i] = math.log(ce) - (math.log(cj) - math.log(cu))
    z = rolling_z(spread, SYN_Z_LB)
    last_day = None
    day_count = 0
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {"EURUSD": eu}, ts, closed, SYN_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day = day
            day_count = 0
        if dt.weekday() >= 5:
            continue
        if dt.hour != SYN_FIRE_UTC:
            continue
        if day_count >= SYN_MAX_PER_DAY or open_pos:
            continue
        zi = z[i]
        atr = eu["atr"][i]
        if not np.isfinite(zi) or not np.isfinite(atr) or atr <= 0:
            continue
        if abs(zi) < SYN_Z_ENTRY:
            continue
        side = -1 if zi > 0 else 1  # fade: rich EURUSD → short
        entry = float(eu["o"][i + 1])
        sl = entry - side * SYN_SL * atr
        tp = entry + side * SYN_RR * SYN_SL * atr
        lots = risk_lots("EURUSD", entry, sl)
        open_pos.append(
            {
                "sym": "EURUSD",
                "side": side,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "lots": lots,
                "bars": 0,
            }
        )
        day_count += 1
    flush_open(open_pos, {"EURUSD": eu}, closed)
    return summarize(closed)


def probe_overnight_ratio(data):
    """Continue overnight direction when |ON| dominates |ON|+|ID| at London fire."""
    closed = []
    open_pos = []
    # Per-day ON = close[ON_ASIA_END-1] - open[0]; ID = close[ON_FIRE-1] - close[ON_ASIA_END-1]
    # Simpler closed-bar: at fire hour bar, ON = close of hour (ON_ASIA_END-1) vs prior day close;
    # ID = close of fire-1 vs Asia-end close. Use day maps.
    day_maps = {s: {} for s in FX3}
    for sym in FX3:
        d = data[sym]
        for i, ts in enumerate(d["t"]):
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            if dt.weekday() >= 5:
                continue
            day_maps[sym].setdefault(dt.date(), []).append(i)

    clock = data["EURUSD"]["t"]
    idx_map = {s: align_on(clock, data[s]) for s in FX3}
    last_day = None
    day_count = 0
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, ON_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day = day
            day_count = 0
        if dt.weekday() >= 5:
            continue
        if dt.hour != ON_FIRE_UTC:
            continue
        if day_count >= ON_MAX_PER_DAY or open_pos:
            continue

        for sym in FX3:
            j = int(idx_map[sym][i])
            if j < 0 or data[sym]["t"][j] != ts:
                continue
            bars = day_maps[sym].get(day, [])
            if len(bars) < ON_FIRE_UTC + 1:
                continue
            # Find asia-end bar (hour == ON_ASIA_END-1) and prior day last bar
            d = data[sym]
            asia_i = None
            for bi in bars:
                bdt = datetime.fromtimestamp(int(d["t"][bi]), tz=timezone.utc)
                if bdt.hour == ON_ASIA_END - 1:
                    asia_i = bi
                    break
            if asia_i is None or asia_i < 1:
                continue
            # Prior session close ≈ bar before today's first bar
            day_start = bars[0]
            if day_start < 1:
                continue
            prior_close = float(d["c"][day_start - 1])
            asia_close = float(d["c"][asia_i])
            # Intraday so far = fire bar open vs asia (closed-bar: use prior hour close)
            fire_ref = float(d["o"][j])  # at fire open, info available from prior close
            # Use asia_close vs prior for ON; fire_ref vs asia for ID proxy
            on_move = asia_close - prior_close
            id_move = fire_ref - asia_close
            denom = abs(on_move) + abs(id_move)
            if denom <= 1e-12:
                continue
            ratio = abs(on_move) / denom
            if ratio < ON_RATIO:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            if abs(on_move) < ON_MIN_ATR * atr:
                continue
            side = 1 if on_move > 0 else -1
            entry = float(d["o"][j + 1]) if j + 1 < len(d["t"]) else None
            if entry is None:
                continue
            sl = entry - side * ON_SL * atr
            tp = entry + side * ON_RR * ON_SL * atr
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
            day_count += 1
            break
    flush_open(open_pos, {s: data[s] for s in FX3}, closed)
    return summarize(closed)


def probe_tickvol_climax(data):
    closed = []
    open_pos = []
    tv_z = {s: rolling_z(data[s]["tv"], TV_Z_LB) for s in FX3}
    clock = data["EURUSD"]["t"]
    idx_map = {s: align_on(clock, data[s]) for s in FX3}
    last_day = None
    day_count = 0
    for i in range(len(clock) - 2):
        ts = int(clock[i])
        open_pos = manage_exits(open_pos, {s: data[s] for s in FX3}, ts, closed, TV_HOLD)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        day = dt.date()
        if day != last_day:
            last_day = day
            day_count = 0
        if dt.weekday() >= 5:
            continue
        if dt.hour != TV_FIRE_UTC:
            continue
        if day_count >= TV_MAX_PER_DAY or open_pos:
            continue
        for sym in FX3:
            j = int(idx_map[sym][i])
            if j < 0 or data[sym]["t"][j] != ts:
                continue
            d = data[sym]
            zi = tv_z[sym][j]
            atr = d["atr"][j]
            if not np.isfinite(zi) or not np.isfinite(atr) or atr <= 0:
                continue
            if zi < TV_Z_ENTRY:
                continue
            body = abs(d["c"][j] - d["o"][j])
            if body < TV_BODY_ATR * atr:
                continue
            # Fade climax bar direction
            side = -1 if d["c"][j] > d["o"][j] else 1
            if j + 1 >= len(d["t"]):
                continue
            entry = float(d["o"][j + 1])
            sl = entry - side * TV_SL * atr
            tp = entry + side * TV_RR * TV_SL * atr
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
            day_count += 1
            break
    flush_open(open_pos, {s: data[s] for s in FX3}, closed)
    return summarize(closed)


def pack_result(hid, setup, symbol, timeframe, pnls, detail):
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "setup_type": setup,
        "symbol": symbol,
        "timeframe": timeframe,
        "metrics": m,
        "haircuts": hc,
        "verdict": verdict,
        "fail_notes": notes,
        "detail": detail,
    }


def append_reg(results, receipt):
    stamp = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "parent_candidate": "Round9_synth_onratio_tvol_greenfield",
                "feature_family": r["setup_type"],
                "lane": "unlimited_goal_greenfield_r9",
                "setup_type": r["setup_type"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "source_provenance": (
                    "Round9 true greenfield outside unpark+R1-R8; "
                    f"receipt {receipt}; nested cursor-grok-4.5-high-fast"
                ),
                "prereg_path": None,
                "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "metrics": r["metrics"],
                "validation": {
                    "cost_stress_apriori_usd": BASE_COST,
                    "haircuts": r["haircuts"],
                    "verdict": r["verdict"],
                    "fail_notes": r["fail_notes"],
                    "receipt_sha256": receipt,
                },
                "verdict": r["verdict"],
                "updated_at": stamp,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results, receipt, any_surv, qfsi_note: str):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")

    def row(r):
        return (
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | "
            f"{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE', 'KILL')} |"
        )

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — Round 9 TRUE greenfield (yen-synth / ON-ratio / tickvol)",
                "",
                "Date: 2026-07-15",
                "Nested model: `cursor-grok-4.5-high-fast`",
                "Parent: Round8 CORR/YENX/PARK OFFLINE_ALL_KILL.",
                "",
                "## Named classes",
                "1. `EURUSD_YENCROSS_SYNTH_RESID_FADE` — rank 1",
                "2. `FX3_OVERNIGHT_RATIO_CONT` — rank 2",
                "3. `FX3_TICKVOL_CLIMAX_FADE` — rank 3",
                "",
                "## Critic merge",
                "| Critic | Stance |",
                "|---|---|",
                "| Sonic trader | PASS — identity triangle ≠ R6 parity / R8 OLS-β |",
                "| Quant | SOFT — residual fatigue; tickvol cost-fragile |",
                "| MQL5/MT5 | PASS — closed-bar; tick_volume z; next-open |",
                "",
                "INTAKE_KILL: none hard.",
                "Model 0: **WITHHELD** until PROBE_SURVIVOR.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Round 9 yen-synth / overnight-ratio / tickvol",
                "",
                "Date: 2026-07-15",
                "Parent: Round8 ALL_KILL. Nested critic `cursor-grok-4.5-high-fast`.",
                "",
                "## Why these could break thick∩cadence",
                "- **Yen-synth identity resid:** Microstructure no-arb gaps on EURUSD vs",
                "  EURJPY/USDJPY recur often enough for cadence; fade is structurally thick",
                "  when cross-rate dislocation snaps (≠ R6 EURGBP parity-z, ≠ R8 OLS-β).",
                "- **Overnight-ratio cont:** 1×/day×FX3 natural cadence; overnight-dominant",
                "  days often carry informational thickness into London (≠ Asia H/L break).",
                "- **Tickvol climax fade:** Cadence from volume spikes; thickness only if",
                "  climax mean-reverts after +$12 (cost-fragile; probe to kill fast).",
                "",
                f"## 1 `HYP-EURUSD-H1-YENCROSS-SYNTH-RESID-FADE-001`",
                f"spread=ln(EURUSD)−(ln(EURJPY)−ln(USDJPY)); z_lb={SYN_Z_LB}; |z|≥{SYN_Z_ENTRY};",
                f"fire UTC{SYN_FIRE_UTC}; fade EURUSD; SL={SYN_SL} ATR RR={SYN_RR} hold≤{SYN_HOLD}.",
                "",
                f"## 2 `HYP-FX3-H1-OVERNIGHT-RATIO-CONT-001`",
                f"|ON|/(|ON|+|ID|)≥{ON_RATIO}; |ON|≥{ON_MIN_ATR} ATR; fire UTC{ON_FIRE_UTC};",
                f"continue ON dir; FX3 first-eligible; SL={ON_SL} ATR RR={ON_RR} hold≤{ON_HOLD}.",
                "",
                f"## 3 `HYP-FX3-H1-TICKVOL-CLIMAX-FADE-001`",
                f"tick_volume z_lb={TV_Z_LB}; z≥{TV_Z_ENTRY}; |body|≥{TV_BODY_ATR} ATR;",
                f"fire UTC{TV_FIRE_UTC}; fade; SL={TV_SL} ATR RR={TV_RR} hold≤{TV_HOLD}.",
                "",
                "## Model 0",
                "Only PROBE_SURVIVOR. No R1–R8 densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — Round 9 yen-synth / ON-ratio / tickvol",
                "",
                "| Object | Cleared vs |",
                "|---|---|",
                "| EURUSD yen-cross synth resid | ≠ R6 EURGBP parity-z; ≠ R8 EURJPY~USDJPY OLS-β; "
                "≠ CHF risk basket; ≠ XS residual book |",
                "| FX3 overnight-ratio cont | ≠ Asia-coil H/L break / Spark / ORB / LNY densify "
                "(object=|ON| share only); ≠ H4 path; ≠ weekend-gap |",
                "| FX3 tickvol climax fade | ≠ Parkinson compress-expand (R8); ≠ NR7; ≠ ADR exhaust; "
                "≠ thin3 jump; ≠ consec impulse |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    table = [
        "| Object | N | PF | tpw | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ] + [row(r) for r in results]

    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probes — Round 9 yen-synth / ON-ratio / tickvol",
                "",
                f"Generated: 2026-07-15 ~{stamp} ICT",
                f"Receipt SHA256: `{receipt}`",
                f"Status: `{status}`",
                f"Cost a priori: +${BASE_COST:.0f}/trade",
                f"QFSI parallel: {qfsi_note}",
                "",
                *table,
                "",
                "## Fail notes",
                *[f"- `{r['hypothesis_id']}`: {', '.join(r['fail_notes']) or 'none'}" for r in results],
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
                "# Session closeout — Round 9 yen-synth / ON-ratio / tickvol",
                "",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                "Model 0: WITHHELD" if not any_surv else "Model 0: AUTHORIZED for survivors only",
                "Do **not** densify synth z / ON ratio / tickvol z / R1–R8 boards.",
                "Next: next true greenfield outside Round9 — QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — Round 9 greenfield (yen-synth / ON-ratio / tickvol)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "Bề mặt ngoài unpark + R1–R8. Nested `cursor-grok-4.5-high-fast`.",
                "",
                f"## Kết quả — `{status}`",
                *table,
                "",
                f"Receipt `{receipt}`",
                "",
                "## Vì sao có thể phá thick∩cadence",
                "- Yen-synth identity: no-arb snap = thick; gap tái diễn = cadence.",
                "- ON-ratio: 1×/ngày×FX3 cadence; overnight-dominant = thickness tiềm năng.",
                "- Tickvol climax: cadence từ spike; thickness chỉ nếu fade sống sau +$12.",
                "",
                "## Quyết định",
                "- Không densify synth-z / ON-ratio / tickvol-z / killboard trước.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI parallel only.",
                "- Next: greenfield ngoài Round9 **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D (greenfield R1–R9)",
                "",
                f"Thời điểm: 2026-07-15 ~{stamp} ICT",
                "R1–R5 FX3 H4 path saturated. R6–R8 + Unpark ALL_KILL.",
                "Round9 = yen-synth / ON-ratio / tickvol — ngoài killboard.",
                "Không densify. QFSI song song. Login không headline.",
                "",
                "## Round 9 — yen-synth + ON-ratio + tickvol → "
                + ("SURVIVOR" if any_surv else "ALL_KILL"),
                *table,
                f"Receipt `{receipt}`",
                "**Cấm densify** synth-z / ON-ratio / tickvol-z.",
                "",
                "## Round 8 — corr + yen-β + Parkinson → ALL_KILL",
                "Receipt `E6A2A2090F64C63E18F9CE2EA37599AD1C0F6C3EB466CF4902042365A9774ADF`",
                "",
                "## Round 1–7 + Unpark → ALL_KILL (boards FORBIDDEN densify)",
                "",
                "## Quyết định",
                "- Zero Model 0." if not any_surv else "- Model 0 only for PROBE_SURVIVOR.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next: greenfield ngoài Round9 **hoặc** research-grade cost.",
                "",
                "Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results, receipt, any_surv, qnote: str):
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
        f"- **GREENFIELD ROUND9 SYNTH/ONRATIO/TVOL CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Outside unpark + R1–R8 densify. Nested critic `cursor-grok-4.5-high-fast`.",
        "  Offline joint screen:",
        *lines_r,
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_VN_ACTION_BRIEF.md`;",
        "  session `readouts/20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md`;",
        "  panel `readouts/20260715_GREENFIELD_SYNTH_ONRATIO_TVOL_3CRITIC_PANEL.md`.",
        f"  QFSI parallel: {qnote}",
        "  Do **not** densify synth z / ON ratio / tickvol z /",
        "  unpark W1/M15 / R1–R8 / triad / NAS / metal / FX3 H4 path /",
        "  carry / exit / AONIA/CORRA/thin3/FRED/LNY/XS.",
        "  Next: next true greenfield outside Round9 board — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Round9 SYNTH/ONRATIO/TVOL "
            f"{'SURVIVOR' if any_surv else 'OFFLINE_ALL_KILL'}; GOAL unmet"
        )
    cleaned = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- **GREENFIELD ROUND9 SYNTH/ONRATIO/TVOL CLOSEOUT"):
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
    prog = (
        ROOT
        / "02. AlphaFactory"
        / "evidence"
        / "execution"
        / "FivePercentOnline-Real"
        / "20260715_QFSI_REAL_007_LONG_ACCUMULATE"
        / "capture_progress.json"
    )
    if not prog.exists():
        return "007 dir missing — cost GAP unchanged; not headline."
    try:
        p = json.loads(prog.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "007 progress unreadable — cost GAP unchanged."
    return (
        f"007 accumulate hb={p.get('heartbeat_rows')} quotes={p.get('quote_rows')} "
        f"deadline={p.get('deadline_utc')}; cost freeze still GAP; login not headline."
    )


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        qnote = qfsi_parallel_note()
        data = {
            "EURUSD": enrich(load("EURUSD", mt5.TIMEFRAME_H1)),
            "GBPUSD": enrich(load("GBPUSD", mt5.TIMEFRAME_H1)),
            "USDJPY": enrich(load("USDJPY", mt5.TIMEFRAME_H1)),
            "EURJPY": enrich(load("EURJPY", mt5.TIMEFRAME_H1)),
        }
        results = [
            pack_result(
                "HYP-EURUSD-H1-YENCROSS-SYNTH-RESID-FADE-001",
                "eurusd_yencross_synth_resid_fade",
                "EURUSD",
                "H1",
                *probe_yen_synth_resid(data),
            ),
            pack_result(
                "HYP-FX3-H1-OVERNIGHT-RATIO-CONT-001",
                "fx3_h1_overnight_ratio_cont",
                "FX3",
                "H1",
                *probe_overnight_ratio(data),
            ),
            pack_result(
                "HYP-FX3-H1-TICKVOL-CLIMAX-FADE-001",
                "fx3_h1_tickvol_climax_fade",
                "FX3",
                "H1",
                *probe_tickvol_climax(data),
            ),
        ]
        # unpack: pack_result expects pnls, detail separately — fix call style
        # Above used *probe which returns (pnls, detail) — pack_result signature is
        # (hid, setup, symbol, timeframe, pnls, detail) — correct.

        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema_version": "greenfield_synth_onratio_tvol_r9.v1",
            "generated_at_utc": utc_now(),
            "window": "2021.01.01-2025.12.31",
            "cost_apriori_usd": BASE_COST,
            "gates": {
                "n_min": 80,
                "pf_min": 1.30,
                "tpw_min": 2.0,
                "x1_5_pf_min": 1.25,
            },
            "params": {
                "synth": {
                    "z_lb": SYN_Z_LB,
                    "z_entry": SYN_Z_ENTRY,
                    "sl": SYN_SL,
                    "rr": SYN_RR,
                    "hold": SYN_HOLD,
                    "fire_utc": SYN_FIRE_UTC,
                },
                "overnight": {
                    "ratio": ON_RATIO,
                    "min_atr": ON_MIN_ATR,
                    "asia_end": ON_ASIA_END,
                    "sl": ON_SL,
                    "rr": ON_RR,
                    "hold": ON_HOLD,
                    "fire_utc": ON_FIRE_UTC,
                },
                "tickvol": {
                    "z_lb": TV_Z_LB,
                    "z_entry": TV_Z_ENTRY,
                    "body_atr": TV_BODY_ATR,
                    "sl": TV_SL,
                    "rr": TV_RR,
                    "hold": TV_HOLD,
                    "fire_utc": TV_FIRE_UTC,
                },
            },
            "qfsi_parallel": qnote,
            "results": results,
            "any_probe_survivor": any_surv,
            "model0": "AUTHORIZED_IF_SURVIVOR" if any_surv else "WITHHELD",
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        receipt = sha256_bytes(raw)
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        write_docs(results, receipt, any_surv, qnote)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv, qnote)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_surv": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            "n": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "x1_5": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["fail_notes"],
                        }
                        for r in results
                    ],
                    "qfsi": qnote,
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
