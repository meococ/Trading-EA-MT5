#!/usr/bin/env python3
"""Post-pivot arch lane — MFE stall-cut + Asia→London state-machine.

Authority: Owner STRATEGY PIVOT next; EXO_FRED_DISPLACE_SPAM_PAUSED.
NOT FRED spam. NOT MaxKZ/RR densify. NOT BE@1R clone. NOT invent cost freeze.

A priori frozen objects (offline first; Model 0 only on PROBE_SURVIVOR):
  1) HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001
     Path-dependent MFE stall hard-exit on frozen RR2 `194548`.
     Arms at 0.75R MFE; hard-closes after stall/giveback — NOT BE@1R.
  2) HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001
     Intake replacement after ATR-ratio continuation coil returned N=0
     (unit mismatch: Asia multi-bar range vs 1-bar ATR). Relative coil =
     AsiaRange ≤ p40 of prior 60 Asia ranges → London H/L break + EXPIRE.
     Not NZD/EUR/XAU densify twin; not RR2 hour densify.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

RR2_RUN = "20260714_194548"
RR2_DIR = RUNS / "EA_SilverBullet" / RR2_RUN
SYMBOL = "USDJPY"

OUT_JSON = PRE / "20260715_MFE_ASIA_STATE_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_MFE_ASIA_STATE_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_MFE_ASIA_STATE_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_MFE_ASIA_STATE_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_MFE_ASIA_STATE_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_MFE_ASIA_STATE_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- MFE stall-cut a priori (≠ BE@1R) ---
MFE_ARM_R = 0.75          # arm below 1.0R (BE used 1.0R)
STALL_BARS = 6            # M15 bars without new peak MFE
STALL_GIVEBACK_R = 0.30   # must give back ≥0.30R from peak to hard-exit
# BE@1R moved SL→entry and waited; this hard-closes at stall bar close.

# --- Asia→London state-machine a priori (intake variant) ---
# Primary ATR-coil continuation (COIL_ATR_MAX=0.60, Asia 0-6, cont mid-disp)
# failed intake N=0 — documented; replaced without readout mining.
ASIA_H0, ASIA_H1 = 0, 7
LONDON_H0, LONDON_H1 = 7, 12  # hard EXPIRE after 12
COIL_PCTL = 40.0
COIL_LOOKBACK_DAYS = 60
SL_BUF_ATR = 0.10
RR = 2.0
MAX_HOLD_H1 = 18
# Documented intake-fail contract (not re-probed as survivor candidate)
INTAKE_FAIL_ASIA_CONT = {
    "hypothesis_id": "HYP-USDJPY-H1-ASIA-COIL-LONDON-CONT-STATE-001",
    "verdict": "INTAKE_FAIL_EMPTY",
    "reason": "AsiaRange/ATR14_bar unit mismatch; n_coil_armed=0 at COIL_ATR_MAX=0.60",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / WEEKS if WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(
    m: dict,
    hc: dict,
    baseline_x15: float | None = None,
    require_lift: bool = False,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.5 <= tpw <= 6.0):
        notes.append("cadence_fail")
    if pf <= 1.20:
        notes.append("pf_fail")
    if x15 < 1.15:
        notes.append("stress_fail")
    if require_lift and baseline_x15 is not None and x15 <= baseline_x15 + 0.01:
        notes.append("no_stress_lift_vs_baseline")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
        and (
            (not require_lift)
            or baseline_x15 is None
            or x15 > baseline_x15 + 0.01
        )
    ):
        return "PROBE_SURVIVOR", notes
    if not notes:
        notes.append("joint_screen_miss")
    return "KILLED_AT_OFFLINE_PROBE", notes


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


def load_closed_trades(path: Path) -> list[dict]:
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in (
                "1",
                "true",
                "True",
            ):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                tp = float(op.get("tp") or op.get("initial_tp") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                side = str(op.get("order_type") or "").upper()
                direction = -1 if "SELL" in side else (1 if "BUY" in side else 0)
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (
                    (vol * 100_000.0 * risk_pts) / px
                    if px > 0 and vol > 0 and risk_pts > 0
                    else 0.0
                )
                ot = parse_dt(op.get("event_time") or "")
                ct = parse_dt(row.get("event_time") or "")
                closed.append(
                    {
                        "position_id": pid,
                        "open_time": ot,
                        "close_time": ct,
                        "pnl": pnl,
                        "entry": entry,
                        "sl": sl,
                        "tp": tp,
                        "volume": vol,
                        "direction": direction,
                        "risk_pts": risk_pts,
                        "risk_usd": risk_usd,
                    }
                )
    return closed


def atr14(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    n = len(c)
    prev_c = np.empty(n)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    out = np.full(n, np.nan)
    if n < 14:
        return out
    out[13] = tr[:14].mean()
    alpha = 1.0 / 14.0
    for i in range(14, n):
        out[i] = out[i - 1] * (1.0 - alpha) + tr[i] * alpha
    return out


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def mt5_dow(ts: int) -> int:
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def load_rates(symbol: str, tf: int) -> dict[str, np.ndarray]:
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INIT_FAIL:{mt5.last_error()}")
    if not mt5.symbol_select(symbol, True):
        mt5.shutdown()
        raise RuntimeError(f"symbol_select fail {symbol}: {mt5.last_error()}")
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    mt5.shutdown()
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol} {tf}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def load_m15_bars(symbol: str) -> list[dict]:
    d = load_rates(symbol, mt5.TIMEFRAME_M15)
    bars = []
    for i in range(len(d["time"])):
        bars.append(
            {
                "t": datetime.fromtimestamp(int(d["time"][i])),
                "o": float(d["open"][i]),
                "h": float(d["high"][i]),
                "l": float(d["low"][i]),
                "c": float(d["close"][i]),
            }
        )
    return bars


def resim_mfe_stallcut(trade: dict, bars: list[dict], bar_index: dict) -> tuple[float, str]:
    """Hard-exit on MFE stall/giveback. Returns (pnl, exit_reason)."""
    if trade["open_time"] is None or trade["direction"] == 0:
        return trade["pnl"], "orig_no_dir"
    if trade["risk_pts"] <= 0 or trade["risk_usd"] <= 0:
        return trade["pnl"], "orig_no_risk"
    entry = trade["entry"]
    sl0 = trade["sl"]
    tp0 = trade["tp"]
    d = trade["direction"]
    R = abs(entry - sl0)
    if R <= 0:
        return trade["pnl"], "orig_bad_R"
    if not tp0 or tp0 <= 0:
        tp0 = entry + d * 2.0 * R
    ot = trade["open_time"]
    end = trade["close_time"] or (ot + timedelta(hours=48))

    t15 = ot.replace(second=0, microsecond=0)
    minute = (t15.minute // 15) * 15
    t15 = t15.replace(minute=minute)
    i0 = bar_index.get(t15)
    if i0 is None:
        for k in range(0, 8):
            for cand in (t15 + timedelta(minutes=15 * k), t15 - timedelta(minutes=15 * k)):
                if cand in bar_index:
                    i0 = bar_index[cand]
                    break
            if i0 is not None:
                break
    if i0 is None:
        return trade["pnl"], "orig_no_bar"

    armed = False
    peak_mfe_r = 0.0
    stall_count = 0

    for i in range(i0, len(bars)):
        b = bars[i]
        if b["t"] < ot:
            continue
        if b["t"] > end + timedelta(hours=2):
            break
        h, l, c = b["h"], b["l"], b["c"]

        # Conservative: SL first
        if d > 0:
            if l <= sl0:
                return -1.0 * trade["risk_usd"], "sl"
            if h >= tp0:
                return ((tp0 - entry) / R) * trade["risk_usd"], "tp"
            mfe_r = max(0.0, (h - entry) / R)
            cur_r = (c - entry) / R
        else:
            if h >= sl0:
                return -1.0 * trade["risk_usd"], "sl"
            if l <= tp0:
                return ((entry - tp0) / R) * trade["risk_usd"], "tp"
            mfe_r = max(0.0, (entry - l) / R)
            cur_r = (entry - c) / R

        if (not armed) and mfe_r >= MFE_ARM_R:
            armed = True
            peak_mfe_r = mfe_r
            stall_count = 0
            continue

        if armed:
            if mfe_r > peak_mfe_r + 1e-12:
                peak_mfe_r = mfe_r
                stall_count = 0
            else:
                stall_count += 1
                giveback = peak_mfe_r - cur_r
                if stall_count >= STALL_BARS and giveback >= STALL_GIVEBACK_R:
                    # Hard exit at bar close — NOT move SL to BE
                    return cur_r * trade["risk_usd"], "stallcut"

    return trade["pnl"], "orig_timeout"


def probe_mfe_stallcut(trades: list[dict], baseline_x15: float) -> dict:
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    bars = load_m15_bars(SYMBOL)
    bar_index = {b["t"]: i for i, b in enumerate(bars)}
    new_pnls: list[float] = []
    reasons: dict[str, int] = defaultdict(int)
    n_changed = 0
    for t in trades:
        npnl, reason = resim_mfe_stallcut(t, bars, bar_index)
        reasons[reason] += 1
        if abs(npnl - t["pnl"]) > 1e-6:
            n_changed += 1
        new_pnls.append(npnl)
    m = metrics(new_pnls)
    hc = haircuts(new_pnls)
    verdict, notes = joint_verdict(m, hc, baseline_x15=baseline_x15, require_lift=True)
    return {
        "hypothesis_id": "HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001",
        "family": "architecture_mfe_stallcut_exit",
        "contract": {
            "arm_mfe_r": MFE_ARM_R,
            "stall_bars_m15": STALL_BARS,
            "giveback_r": STALL_GIVEBACK_R,
            "exit": "hard_close_at_stall_bar_close",
            "not": "BE@1R / SL→entry / trail-from-BE / MaxKZ / RR densify / FRED",
        },
        "mt5_bars_m15": len(bars),
        "n_pnl_changed": n_changed,
        "exit_reasons": dict(reasons),
        "baseline": {"metrics": base_m, "haircut_flat12": base_hc},
        "metrics": m,
        "haircut_flat12": hc,
        "baseline_x15": baseline_x15,
        "stress_lift_vs_baseline": round(
            ((hc.get("x1_5") or {}).get("pf") or 0.0) - baseline_x15, 4
        ),
        "verdict": verdict,
        "notes": notes,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def resolve_r(
    direction: int,
    entry: float,
    sl: float,
    tp: float,
    i0: int,
    h: np.ndarray,
    l: np.ndarray,
    c: np.ndarray,
    max_hold: int,
) -> float | None:
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        hi, lo = h[j], l[j]
        if (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl):
            return -1.0
        if (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp):
            return float(RR)
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def by_day_index(t: np.ndarray) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        out.setdefault(day_key(int(ts)), []).append(i)
    return out


def r_to_cash_pnls(rs: list[float]) -> list[float]:
    """Fixed fractional risk path (structural convention)."""
    bal = DEPOSIT
    pnls = []
    for r in rs:
        pnl = bal * RISK_FRAC * r
        pnls.append(pnl)
        bal += pnl
    return pnls


def probe_asia_london_state(h1: dict) -> dict:
    """Relative percentile-coil → London H/L break state-machine (intake variant)."""
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    by = by_day_index(t)
    days = sorted(by.keys())
    asia_rows: list[dict] = []
    for d in days:
        idxs = by[d]
        asia = [i for i in idxs if ASIA_H0 <= hour_u(int(t[i])) < ASIA_H1]
        if len(asia) < 4:
            continue
        ahi = max(h[i] for i in asia)
        alo = min(l[i] for i in asia)
        if ahi <= alo:
            continue
        asia_rows.append(
            {
                "day": d,
                "range": ahi - alo,
                "ahi": ahi,
                "alo": alo,
                "idxs": idxs,
            }
        )

    rs: list[float] = []
    funnel = {
        "n_asia_days": len(asia_rows),
        "n_coil_armed": 0,
        "n_fire": 0,
        "n_expire": 0,
        "n_trades": 0,
        "n_skip_dist": 0,
        "n_skip_untradeable": 0,
        "n_skip_atr": 0,
    }
    for k, row in enumerate(asia_rows):
        if k < COIL_LOOKBACK_DAYS:
            continue
        prior = [asia_rows[j]["range"] for j in range(k - COIL_LOOKBACK_DAYS, k)]
        thr = float(np.percentile(prior, COIL_PCTL))
        if row["range"] > thr:
            continue
        funnel["n_coil_armed"] += 1
        ahi, alo = row["ahi"], row["alo"]
        idxs = row["idxs"]
        london = [i for i in idxs if LONDON_H0 <= hour_u(int(t[i])) < LONDON_H1]
        fire_i = None
        up = False
        for i in london:
            if c[i] > ahi:
                fire_i, up = i, True
                break
            if c[i] < alo:
                fire_i, up = i, False
                break
        if fire_i is None:
            funnel["n_expire"] += 1
            continue
        funnel["n_fire"] += 1
        entry_i = fire_i + 1
        if entry_i >= len(c) - 1 or not tradeable(int(t[entry_i])):
            funnel["n_skip_untradeable"] += 1
            continue
        if math.isnan(atr[fire_i]) or atr[fire_i] <= 0:
            funnel["n_skip_atr"] += 1
            continue
        bias = 1 if up else -1
        entry = float(o[entry_i])
        extreme = alo if up else ahi
        sl = (
            extreme - SL_BUF_ATR * atr[fire_i]
            if up
            else extreme + SL_BUF_ATR * atr[fire_i]
        )
        dist = abs(entry - sl)
        if dist < 0.05 or dist > 2.0:
            funnel["n_skip_dist"] += 1
            continue
        tp = entry + bias * dist * RR
        r = resolve_r(bias, entry, sl, tp, entry_i, h, l, c, MAX_HOLD_H1)
        if r is None:
            continue
        rs.append(float(r))
        funnel["n_trades"] += 1

    pnls = r_to_cash_pnls(rs)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc, baseline_x15=None, require_lift=False)
    return {
        "hypothesis_id": "HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001",
        "family": "architecture_asia_london_state_machine",
        "symbol": SYMBOL,
        "tf": "H1",
        "replaces_intake_fail": INTAKE_FAIL_ASIA_CONT,
        "contract": {
            "asia_hours_utc": [ASIA_H0, ASIA_H1],
            "london_fire_hours_utc": [LONDON_H0, LONDON_H1],
            "coil": f"AsiaRange <= p{COIL_PCTL:.0f} of prior {COIL_LOOKBACK_DAYS} Asia ranges",
            "fire": "first London H1 close beyond Asia high/low",
            "rr": RR,
            "expire": "no fire by London_H1 → EXPIRED (no late entry)",
            "states": "IDLE → COIL_ARMED → FIRED | EXPIRED",
            "not": (
                "ATR-bar coil continuation (intake-fail) / NZD Asia-range break densify / "
                "EUR Asia-box / XAU Asia-compress / RR2 hour densify / BE@1R / FRED"
            ),
        },
        "funnel": funnel,
        "metrics": m,
        "haircut_flat12": hc,
        "verdict": verdict,
        "notes": notes,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def write_dedup() -> None:
    text = """# De-dup clearance — MFE stall-cut + Asia→London state-machine

Date: 2026-07-15  
Authority: Owner post-pivot arch lane; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001` | Path-dependent exit on frozen RR2 `194548` | Hard-exit after MFE arm@0.75R + stall/giveback; **≠** BE@1R (no SL→entry); **≠** MaxKZ/RR densify; **≠** vol-target / H4 regime |
| `HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001` | New entry state-machine USDJPY H1 | Relative Asia-range p40 coil → London H/L break + EXPIRE; **≠** ATR-bar continuation (intake-fail); **≠** NZD Wave7 densify twin (adds relative coil + EXPIRE + RR=2 USDJPY); **≠** EUR Asia-box / XAU Asia-compress; **≠** RR2 hour densify |

## Intake fail (documented, not densified)

| ID | Result |
|---|---|
| `HYP-USDJPY-H1-ASIA-COIL-LONDON-CONT-STATE-001` | `INTAKE_FAIL_EMPTY` — AsiaRange vs 1-bar ATR@0.60 → n_coil=0 |

## Banned collisions

- Dichotomy BE@1R (`HYP-RR2-EXIT-BE1R-M15PATH-001`) — killed; this board does **not** revive BE.
- Vol-target / H4 regime (prior KILL board) — different mechanism.
- Wave5 EUR Asia-box / Wave7 NZD Asia-London / MULTISYM XAU Asia-compress densify.
- FRED displace/ToT / exo densify (spam paused).
- MaxKZ2 / RR / session / coil-percentile mining from this readout.

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.  
RR2 child additionally requires stress lift vs RR2 baseline x1.5.  
Model 0 withheld unless `PROBE_SURVIVOR`.

## Clearance

**CLEARED** for offline probe only (MFE + Asia pctl-coil variant).
"""
    OUT_DEDUP.write_text(text, encoding="utf-8")


def write_design() -> None:
    text = """# Design memo — MFE stall-cut + Asia→London state-machine

Date: 2026-07-15  
Lane: single; no-Git; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Problem

Post-pivot Track B killed vol-target and H4 regime. Best shelf remains RR2
`194548` (research PF~1.38 / ~2/wk; +$12 x1.5 ~1.01). Need architecture that
is **not** FRED exo, **not** BE@1R, **not** MaxKZ/RR densify.

## Rejected a priori

- BE@1R / trail-from-BE (falsified; PF collapse).
- New FRED series / exo densify.
- Densify Asia/London hours from Wave5–7 / MULTISYM readouts.
- Invent multi-month cost freeze / RR2 full rebind on diagnostic tick table.

## Design 1 — MFE stall-cut (`HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001`)

**Thesis:** RR2 give-back after partial favorable excursion destroys friction
expectancy. Cutting when MFE **stalls** (not when price merely tags 1R) should
harvest mid-path edge without BE scratch dynamics.

**Frozen ≠ BE@1R:**
| Item | Stall-cut | BE@1R (killed) |
|---|---|---|
| Arm | MFE ≥ **0.75R** | path reaches **1.0R** |
| Action | **hard close** at stall bar close | move SL → **entry**, wait |
| Stall | 6 M15 bars no new peak MFE **and** giveback ≥ 0.30R from peak | n/a |
| TP/SL | original TP/SL still active until stall | original TP; SL becomes BE |

## Design 2a — Asia continuation ATR-coil (INTAKE FAIL)

`HYP-USDJPY-H1-ASIA-COIL-LONDON-CONT-STATE-001`: Asia coil ≤0.60·ATR14(bar)
+ London continuation past Asia mid. **Empty** — multi-hour Asia range is
~2.5× 1-bar ATR at median; threshold unit-invalid. Documented; not densified.

## Design 2b — Asia pctl-coil London break state (intake replacement)

`HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001`

**Thesis:** Relative Asia compression (range ≤ p40 of prior 60 Asia days)
**ARMS** the day; London may **FIRE** on first close beyond Asia H/L; else
**EXPIRE**. State-machine monetizes coil→break without FRED/BE/RR densify.

**Frozen:** Asia 00–07 UTC; coil p40/60; London fire 07–12; RR=2; USDJPY H1;
SL = opposite Asia extreme ±0.10·ATR; one trade/day; hard EXPIRE.

**De-dup:** NZD Wave7 had no relative coil + used RR3; EUR/XAU were other
symbols / ATR-bar compress. This board freezes relative coil + EXPIRE a priori.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold. No Real stall required.
"""
    OUT_DESIGN.write_text(text, encoding="utf-8")


def write_artifacts(payload: dict) -> None:
    lines = [
        "# Offline probes — MFE stall-cut + Asia→London state-machine",
        "",
        f"Date: 2026-07-15",
        f"Status: `{'PROBE_SURVIVOR' if payload.get('any_survivor') else 'OFFLINE_ALL_KILL'}` / "
        f"`{'MODEL0_ARMED' if payload.get('any_survivor') else 'NO_MODEL0'}`",
        f"Authority: `EXO_FRED_DISPLACE_SPAM_PAUSED`",
        "",
        "## Baseline RR2 `194548`",
        "",
        "```",
        json.dumps(payload.get("baseline"), indent=2),
        "```",
        "",
        "## Results",
        "",
        "| ID | N | PF | tpw | x1.5 | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in payload["results"]:
        m = r.get("metrics") or {}
        hc = r.get("haircut_flat12") or {}
        x15 = (hc.get("x1_5") or {}).get("pf")
        lines.append(
            f"| `{r['hypothesis_id']}` | {m.get('n')} | {m.get('pf')} | "
            f"{m.get('tpw')} | **{x15}** | **{r.get('verdict')}** |"
        )
    lines += [
        "",
        "## Notes",
        "",
    ]
    for r in payload["results"]:
        lines.append(
            f"- `{r['hypothesis_id']}`: notes={r.get('notes')} "
            f"funnel={r.get('funnel')} reasons={r.get('exit_reasons')}"
        )
    lines += [
        "",
        f"Receipt SHA: `{payload.get('receipt_sha256')}`",
        f"Model 0: `{payload.get('model0')}`",
        f"Best shelf: `{payload.get('best_shelf')}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    survivors = payload.get("survivors") or []
    close = f"""# Session closeout — MFE stall-cut + Asia→London state-machine

Date: 2026-07-15  
Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{'OFFLINE_SURVIVOR' if survivors else 'OFFLINE_ALL_KILL'}` / `{'MODEL0_ARMED' if survivors else 'NO_MODEL0'}`  
Lane: single checkout; no-Git; no Real stall

## Board

| ID | N | PF | tpw | stress x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
"""
    for r in payload["results"]:
        m = r.get("metrics") or {}
        hc = r.get("haircut_flat12") or {}
        x15 = (hc.get("x1_5") or {}).get("pf")
        close += (
            f"| `{r['hypothesis_id']}` | {m.get('n')} | {m.get('pf')} | "
            f"{m.get('tpw')} | **{x15}** | **{r.get('verdict')}** |\n"
        )
    close += f"""
Baseline RR2 `194548` x1.5 flat+$12 = **{(payload.get('baseline') or {}).get('haircut_flat12', {}).get('x1_5', {}).get('pf')}**.

Receipt: `{payload.get('receipt_sha256')}`  
Design: `readouts/20260715_MFE_ASIA_STATE_DESIGN_MEMO.md`  
De-dup: `readouts/20260715_MFE_ASIA_STATE_DEDUP_CLEARANCE.md`

## Model 0

{"Armed for: " + ", ".join(survivors) if survivors else "Withheld (zero PROBE_SURVIVOR)."}

## Decisions

1. Keep **`EXO_FRED_DISPLACE_SPAM_PAUSED`** — no new FRED series.
2. Do **not** densify MFE arm/stall bars/giveback or Asia coil/disp/hours from this board.
3. Do **not** revive BE@1R; do **not** invent cost freeze; do **not** densify MaxKZ/RR.
4. Best shelf unchanged: RR2 `194548`. Phase-0 still BLOCKED. GOAL unmet.

## Next autonomous EV (non-login-only)

1. If both KILL: next independent arch class outside MFE/Asia densify — e.g. execution microstructure sleeve (once cost surface research-grade) or true non-Asia session structure on non-exhausted symbols.
2. Keep QFSI 006 accumulating; rebind harness `--execute` only on gate GO.
3. Owner PIT/vendor tape still required for multi-month session×hour cost freeze.
"""
    OUT_CLOSE.write_text(close, encoding="utf-8")

    rows_vn = []
    for r in payload["results"]:
        m = r.get("metrics") or {}
        hc = r.get("haircut_flat12") or {}
        x15 = (hc.get("x1_5") or {}).get("pf")
        rows_vn.append(
            f"- `{r['hypothesis_id']}`: N={m.get('n')} PF {m.get('pf')} "
            f"tpw {m.get('tpw')} x1.5 **{x15}** → **{r.get('verdict')}**"
        )
    vn = f"""# VN action brief — MFE stall-cut + Asia→London state

## Kết quả
- Tiếp `EXO_FRED_DISPLACE_SPAM_PAUSED` — không FRED spam; không stall vì login.
- Offline 2 object (de-dup cleared):
{chr(10).join(rows_vn)}
- Shelf tốt nhất vẫn RR2 `194548`. Model 0: **{payload.get('model0')}**.

## Receipt
- `{payload.get('receipt_sha256')}`
- Design/dedup/closeout: `20260715_MFE_ASIA_STATE_*`

## Không làm
- Densify MFE arm / stall bars / giveback; densify Asia coil/disp/giờ.
- Revive BE@1R / FRED exo / MaxKZ / RR.
- Invent multi-year cost; full-cost rebind khi gate còn STOP.

## Next (không phải “đi login”)
1. Nếu cả 2 KILL: object arch độc lập ngoài densify MFE/Asia (microstructure khi cost research-grade, hoặc structure session khác symbol chưa exhausted).
2. Giữ QFSI accumulate; harness `--execute` chỉ khi GO.
3. Multi-month cost freeze: Owner PIT/vendor hoặc tích lũy ≥90 ngày.
"""
    OUT_VN.write_text(vn, encoding="utf-8")


def main() -> int:
    write_dedup()
    write_design()

    trades_path = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_path)
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    baseline_x15 = float((base_hc.get("x1_5") or {}).get("pf") or 0.0)

    r1 = probe_mfe_stallcut(trades, baseline_x15)

    if not mt5.initialize():
        raise RuntimeError(f"MT5_INIT_FAIL:{mt5.last_error()}")
    h1 = load_rates(SYMBOL, mt5.TIMEFRAME_H1)
    # load_rates already shutdown; re-init not needed
    r2 = probe_asia_london_state(h1)

    results = [r1, r2]
    survivors = [r["hypothesis_id"] for r in results if r.get("verdict") == "PROBE_SURVIVOR"]

    payload: dict[str, Any] = {
        "schema": "mfe_asia_state_offline_probes.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "Owner post-pivot arch lane 2026-07-15; EXO_FRED_DISPLACE_SPAM_PAUSED",
        "rr2_sleeve": RR2_RUN,
        "trades_csv": str(trades_path.relative_to(ROOT)).replace("\\", "/"),
        "n_trades": len(trades),
        "baseline": {"metrics": base_m, "haircut_flat12": base_hc},
        "results": results,
        "any_survivor": bool(survivors),
        "survivors": survivors,
        "model0": "ARMED" if survivors else "WITHHELD",
        "intake_fail": INTAKE_FAIL_ASIA_CONT,
        "bans": [
            "no_BE@1R_revive",
            "no_FRED_spam",
            "no_RR_MaxKZ_densify",
            "no_invent_cost_surface",
            "no_Asia_hour_coil_pctl_densify_from_readout",
        ],
        "best_shelf": "RR2_20260714_194548",
        "dedup": str(OUT_DEDUP.relative_to(ROOT)).replace("\\", "/"),
        "design_memo": str(OUT_DESIGN.relative_to(ROOT)).replace("\\", "/"),
    }

    raw = json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    # provisional write without sha, then stamp
    payload["receipt_sha256"] = sha256_bytes(raw)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    # re-hash final file bytes
    payload["receipt_sha256"] = sha256_file(OUT_JSON)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    payload["receipt_sha256"] = sha256_file(OUT_JSON)

    write_artifacts(payload)
    print(json.dumps({
        "receipt": payload["receipt_sha256"],
        "any_survivor": payload["any_survivor"],
        "survivors": survivors,
        "results": [
            {
                "id": r["hypothesis_id"],
                "verdict": r["verdict"],
                "n": (r.get("metrics") or {}).get("n"),
                "pf": (r.get("metrics") or {}).get("pf"),
                "tpw": (r.get("metrics") or {}).get("tpw"),
                "x15": ((r.get("haircut_flat12") or {}).get("x1_5") or {}).get("pf"),
                "notes": r.get("notes"),
            }
            for r in results
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
