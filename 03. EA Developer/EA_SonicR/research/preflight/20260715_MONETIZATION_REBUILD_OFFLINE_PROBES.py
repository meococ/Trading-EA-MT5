#!/usr/bin/env python3
"""Track B — monetization rebuild (offline-first) on parked RR2 `194548`.

Authority: Owner post-greenfield 2026-07-15 authorized “đập đi xây lại”;
EXO_FRED_DISPLACE_SPAM_PAUSED; free Model 0 for PROBE_SURVIVOR only.

Changes HOW edge is monetized — NOT entry densify. De-dup vs killed:
  BE@1R, MFE stall-cut, vol-target ATR risk, H4 regime-align gate.

A priori frozen (≥2; board runs 3):
  1) HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001
     Scale 50% @ +1.0R; remainder holds to original 2R TP / SL / timeout.
  2) HYP-RR2-EXIT-ATRTRAIL-ARM075-K15-001
     After MFE≥0.75R, trail SL = peak_favorable − 1.5×ATR14(M15).
     Never clamp to entry (≠ BE@1R). No stall-timer hard-close (≠ MFE stall).
  3) HYP-RR2-VOLREGIME-RMULT-H1ATR-001
     Same entries; TP multiple from closed H1 ATR14 %ile (60-bar):
       <30 → 1.5R; 30–70 → 2.0R; >70 → 3.0R. SL unchanged.
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

OUT_JSON = PRE / "20260715_MONETIZATION_REBUILD_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_MONETIZATION_REBUILD_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_MONETIZATION_REBUILD_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_MONETIZATION_REBUILD_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_MONETIZATION_REBUILD_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_MONETIZATION_REBUILD_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0

# --- Scale-out a priori ---
SCALE_FRAC = 0.50
SCALE_AT_R = 1.0
RUNNER_R = 2.0
TP_HIT_R_LO = 1.85  # treat ~2R outcomes as TP hits (tester fidelity)

# --- ATR trail a priori (≠ BE, ≠ MFE stall) — OHLC path used only as diagnostic ---
TRAIL_ARM_R = 0.75
TRAIL_ATR_K = 1.5
TRAIL_ATR_LEN = 14

# --- Time-box scalp→swing hybrid a priori (outcome-duration; no OHLC SL rebuild) ---
TIMEBOX_HOURS = 2.0
TIMEBOX_SCALP_R = 1.0
TIMEBOX_SWING_R = 3.0

# --- Vol-regime R multiple a priori ---
H1_ATR_LEN = 14
H1_PCT_LOOKBACK = 60
RMULT_LO = 1.5
RMULT_MID = 2.0
RMULT_HI = 3.0
PCT_LO = 30.0
PCT_HI = 70.0


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
    m: dict, hc: dict, baseline_x15: float | None = None, require_lift: bool = True
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
            not require_lift
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


def atr_wilder(h: np.ndarray, l: np.ndarray, c: np.ndarray, length: int) -> np.ndarray:
    n = len(c)
    prev_c = np.empty(n)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    out = np.full(n, np.nan)
    if n < length:
        return out
    out[length - 1] = tr[:length].mean()
    for i in range(length, n):
        out[i] = (out[i - 1] * (length - 1) + tr[i]) / length
    return out


def load_rates(symbol: str, tf: int) -> dict[str, np.ndarray]:
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INIT_FAIL:{mt5.last_error()}")
    try:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"symbol_select fail {symbol}: {mt5.last_error()}")
        rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
        if rates is None or len(rates) < 200:
            raise RuntimeError(f"rates fail {symbol} {tf}: {mt5.last_error()}")
        return {
            "time": rates["time"].astype(np.int64),
            "open": rates["open"].astype(float),
            "high": rates["high"].astype(float),
            "low": rates["low"].astype(float),
            "close": rates["close"].astype(float),
        }
    finally:
        mt5.shutdown()


def load_m15(symbol: str) -> tuple[list[dict], dict[datetime, int], np.ndarray]:
    d = load_rates(symbol, mt5.TIMEFRAME_M15)
    atr = atr_wilder(d["high"], d["low"], d["close"], TRAIL_ATR_LEN)
    bars = []
    bar_index: dict[datetime, int] = {}
    for i in range(len(d["time"])):
        t = datetime.fromtimestamp(int(d["time"][i]))
        bars.append(
            {
                "t": t,
                "o": float(d["open"][i]),
                "h": float(d["high"][i]),
                "l": float(d["low"][i]),
                "c": float(d["close"][i]),
                "atr": float(atr[i]) if not math.isnan(atr[i]) else None,
            }
        )
        bar_index[t] = i
    return bars, bar_index, atr


def find_bar_i(ot: datetime, bar_index: dict[datetime, int]) -> int | None:
    t15 = ot.replace(second=0, microsecond=0)
    minute = (t15.minute // 15) * 15
    t15 = t15.replace(minute=minute)
    i0 = bar_index.get(t15)
    if i0 is not None:
        return i0
    for k in range(0, 8):
        for cand in (t15 + timedelta(minutes=15 * k), t15 - timedelta(minutes=15 * k)):
            if cand in bar_index:
                return bar_index[cand]
    return None


def r_to_usd(r: float, risk_usd: float) -> float:
    return r * risk_usd


def resim_scaleout(trade: dict, bars: list[dict], bar_index: dict) -> tuple[float, str]:
    """50% @1R + 50% runner to 2R. Cost later applied flat per trade (same N)."""
    if trade["open_time"] is None or trade["direction"] == 0:
        return trade["pnl"], "orig_no_dir"
    if trade["risk_pts"] <= 0 or trade["risk_usd"] <= 0:
        return trade["pnl"], "orig_no_risk"
    entry = trade["entry"]
    sl0 = trade["sl"]
    d = trade["direction"]
    R = abs(entry - sl0)
    if R <= 0:
        return trade["pnl"], "orig_bad_R"
    tp_scale = entry + d * SCALE_AT_R * R
    tp_run = entry + d * RUNNER_R * R
    ot = trade["open_time"]
    end = trade["close_time"] or (ot + timedelta(hours=48))
    i0 = find_bar_i(ot, bar_index)
    if i0 is None:
        return trade["pnl"], "orig_no_bar"

    scaled = False
    pnl_r = 0.0
    rem = 1.0 - SCALE_FRAC

    for i in range(i0, len(bars)):
        b = bars[i]
        if b["t"] < ot:
            continue
        if b["t"] > end + timedelta(hours=2):
            # timeout remainder at close
            if d > 0:
                cur_r = (b["c"] - entry) / R
            else:
                cur_r = (entry - b["c"]) / R
            pnl_r += rem * cur_r
            return r_to_usd(pnl_r, trade["risk_usd"]), "timeout_runner"

        h, l = b["h"], b["l"]

        # SL first (conservative) on remaining size; if not yet scaled, full size
        hit_sl = (d > 0 and l <= sl0) or (d < 0 and h >= sl0)
        if hit_sl:
            if not scaled:
                return r_to_usd(-1.0, trade["risk_usd"]), "sl_full"
            pnl_r += rem * (-1.0)
            return r_to_usd(pnl_r, trade["risk_usd"]), "sl_runner"

        # Scale-out touch
        hit_scale = (d > 0 and h >= tp_scale) or (d < 0 and l <= tp_scale)
        if (not scaled) and hit_scale:
            pnl_r += SCALE_FRAC * SCALE_AT_R
            scaled = True
            # same bar may also hit runner / continue

        if scaled:
            hit_run = (d > 0 and h >= tp_run) or (d < 0 and l <= tp_run)
            if hit_run:
                pnl_r += rem * RUNNER_R
                return r_to_usd(pnl_r, trade["risk_usd"]), "tp_runner"
        else:
            # if somehow TP2 before scale (gap), take full at runner
            hit_run = (d > 0 and h >= tp_run) or (d < 0 and l <= tp_run)
            if hit_run:
                return r_to_usd(RUNNER_R, trade["risk_usd"]), "tp_full_gap"

    return trade["pnl"], "orig_timeout"


def resim_atr_trail(trade: dict, bars: list[dict], bar_index: dict) -> tuple[float, str]:
    """ATR trail after arm — never BE clamp; continuous trail ≠ stall hard-close."""
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
    i0 = find_bar_i(ot, bar_index)
    if i0 is None:
        return trade["pnl"], "orig_no_bar"

    armed = False
    peak = entry  # favorable extreme (high for long, low for short)
    trail_sl = sl0

    for i in range(i0, len(bars)):
        b = bars[i]
        if b["t"] < ot:
            continue
        if b["t"] > end + timedelta(hours=2):
            break
        h, l = b["h"], b["l"]
        atr = b["atr"]

        # Conservative: stop first (trail or initial)
        stop = trail_sl if armed else sl0
        if d > 0:
            if l <= stop:
                r = (stop - entry) / R
                return r_to_usd(r, trade["risk_usd"]), ("trail_hit" if armed else "sl")
            if h >= tp0:
                return r_to_usd((tp0 - entry) / R, trade["risk_usd"]), "tp"
            mfe_r = max(0.0, (h - entry) / R)
            fav = h
        else:
            if h >= stop:
                r = (entry - stop) / R
                return r_to_usd(r, trade["risk_usd"]), ("trail_hit" if armed else "sl")
            if l <= tp0:
                return r_to_usd((entry - tp0) / R, trade["risk_usd"]), "tp"
            mfe_r = max(0.0, (entry - l) / R)
            fav = l

        if (not armed) and mfe_r >= TRAIL_ARM_R:
            armed = True
            peak = fav

        if armed and atr and atr > 0:
            if d > 0:
                peak = max(peak, fav)
                new_trail = peak - TRAIL_ATR_K * atr
                # Never clamp to entry (≠ BE); ratchet stop up only
                if new_trail > trail_sl:
                    trail_sl = new_trail
            else:
                peak = min(peak, fav)
                new_trail = peak + TRAIL_ATR_K * atr
                # Short: ratchet stop down only (more favorable)
                if new_trail < trail_sl:
                    trail_sl = new_trail

    # fallback original
    return trade["pnl"], "orig_timeout"


def percentile_rank(window: list[float], value: float) -> float:
    if not window:
        return 50.0
    below = sum(1 for x in window if x < value)
    equal = sum(1 for x in window if x == value)
    return 100.0 * (below + 0.5 * equal) / len(window)


def h1_index_at_or_before(times: list[datetime], t: datetime) -> int | None:
    lo, hi = 0, len(times) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return ans


def resim_volregime_rmult(
    trade: dict,
    h1_times: list[datetime],
    h1_atr: list[float | None],
    bars: list[dict],
    bar_index: dict,
) -> tuple[float, str, float]:
    """Recompute exit with TP = rmult(H1 ATR%ile) * R; path on M15."""
    if trade["open_time"] is None or trade["direction"] == 0:
        return trade["pnl"], "orig_no_dir", 2.0
    if trade["risk_pts"] <= 0 or trade["risk_usd"] <= 0:
        return trade["pnl"], "orig_no_risk", 2.0
    entry = trade["entry"]
    sl0 = trade["sl"]
    d = trade["direction"]
    R = abs(entry - sl0)
    if R <= 0:
        return trade["pnl"], "orig_bad_R", 2.0
    ot = trade["open_time"]
    ih = h1_index_at_or_before(h1_times, ot)
    if ih is None or ih < H1_PCT_LOOKBACK:
        return trade["pnl"], "orig_no_h1", 2.0
    cur_atr = h1_atr[ih]
    if cur_atr is None:
        return trade["pnl"], "orig_no_atr", 2.0
    window = [h1_atr[j] for j in range(ih - H1_PCT_LOOKBACK, ih) if h1_atr[j] is not None]
    if len(window) < H1_PCT_LOOKBACK // 2:
        return trade["pnl"], "orig_short_window", 2.0
    pr = percentile_rank([float(x) for x in window], float(cur_atr))
    if pr < PCT_LO:
        rmult = RMULT_LO
    elif pr > PCT_HI:
        rmult = RMULT_HI
    else:
        rmult = RMULT_MID
    tp0 = entry + d * rmult * R
    end = trade["close_time"] or (ot + timedelta(hours=48))
    # Extend hold slightly for 3R paths
    if rmult >= 2.5:
        end = max(end, ot + timedelta(hours=72))
    i0 = find_bar_i(ot, bar_index)
    if i0 is None:
        return trade["pnl"], "orig_no_bar", rmult

    for i in range(i0, len(bars)):
        b = bars[i]
        if b["t"] < ot:
            continue
        if b["t"] > end + timedelta(hours=2):
            if d > 0:
                cur_r = (b["c"] - entry) / R
            else:
                cur_r = (entry - b["c"]) / R
            return r_to_usd(cur_r, trade["risk_usd"]), "timeout", rmult
        h, l = b["h"], b["l"]
        if d > 0:
            if l <= sl0:
                return r_to_usd(-1.0, trade["risk_usd"]), "sl", rmult
            if h >= tp0:
                return r_to_usd(rmult, trade["risk_usd"]), "tp", rmult
        else:
            if h >= sl0:
                return r_to_usd(-1.0, trade["risk_usd"]), "sl", rmult
            if l <= tp0:
                return r_to_usd(rmult, trade["risk_usd"]), "tp", rmult
    return trade["pnl"], "orig_timeout", rmult


def probe_family(
    hyp_id: str,
    family: str,
    contract: dict,
    new_pnls: list[float],
    reasons: dict[str, int],
    n_changed: int,
    baseline_x15: float,
    extra: dict | None = None,
) -> dict:
    m = metrics(new_pnls)
    hc = haircuts(new_pnls)
    verdict, notes = joint_verdict(m, hc, baseline_x15=baseline_x15, require_lift=True)
    out = {
        "hypothesis_id": hyp_id,
        "family": family,
        "contract": contract,
        "n_pnl_changed": n_changed,
        "exit_reasons": dict(reasons),
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
    if extra:
        out.update(extra)
    return out


def write_docs(payload: dict, receipt: str) -> None:
    results = payload["probes"]
    base = payload["baseline"]

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — monetization rebuild (post-greenfield)",
                "",
                "Date: 2026-07-15",
                "Lane: single; no-Git; offline-first",
                "Authority: Owner authorized rebuild (“đập đi xây lại”); free Model 0 for survivors",
                "",
                "## Problem",
                "",
                "Public price+exo greenfield exhausted. Fixed-RR scalp RR2 `194548`",
                "dies under +$12 x1.5. Need monetization architectures that change",
                "**how** winners/losers are cashed — not denser entries.",
                "",
                "## Rejected a priori (killed / banned)",
                "",
                "- BE@1R / trail-from-BE",
                "- MFE stall-cut hard-close",
                "- Vol-target ATR risk sizing",
                "- H4 regime-align gate",
                "- FRED/XS/LNY/Asia densify",
                "",
                "## Design 1 — Scale-out (`HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001`)",
                "",
                f"Take {SCALE_FRAC:.0%} at +{SCALE_AT_R}R; remainder to +{RUNNER_R}R.",
                "Cadence unchanged (same entries).",
                "",
                "## Design 2 — ATR trail (`HYP-RR2-EXIT-ATRTRAIL-ARM075-K15-001`)",
                "",
                f"Arm at MFE≥{TRAIL_ARM_R}R; trail = peak − {TRAIL_ATR_K}×ATR{TRAIL_ATR_LEN}(M15).",
                "**≠ BE:** never clamp SL to entry. **≠ MFE stall:** no stall-bar",
                "timer / giveback hard-close — continuous ATR ratchet only.",
                "",
                "## Design 3 — Vol-regime R multiple (`HYP-RR2-VOLREGIME-RMULT-H1ATR-001`)",
                "",
                f"Closed H1 ATR%ile over {H1_PCT_LOOKBACK}: <{PCT_LO}→{RMULT_LO}R;",
                f"{PCT_LO}–{PCT_HI}→{RMULT_MID}R; >{PCT_HI}→{RMULT_HI}R. SL fixed.",
                "",
                "## Model 0 policy",
                "",
                "Only `PROBE_SURVIVOR`. Else withhold.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup clearance — monetization rebuild",
                "",
                "Date: 2026-07-15",
                "Authority: Owner rebuild authorized; EXO_FRED_DISPLACE_SPAM_PAUSED",
                "",
                "## Objects",
                "",
                "| ID | Class | Independence claim |",
                "|---|---|---|",
                "| `HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001` | Partial scale-out monetization | ≠ BE@1R; ≠ MFE stall; ≠ vol-target size; ≠ H4 gate |",
                "| `HYP-RR2-EXIT-ATRTRAIL-ARM075-K15-001` | ATR trail exit | ≠ BE clamp; ≠ stall-timer hard-close; ≠ MaxKZ/RR densify |",
                "| `HYP-RR2-VOLREGIME-RMULT-H1ATR-001` | Vol-regime TP multiple | ≠ H4 EMA align gate; ≠ entry filter densify; ≠ sizing vol-target |",
                "",
                "## Banned collisions",
                "",
                "- `HYP-RR2-EXIT-BE1R-M15PATH-001` (killed)",
                "- `HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001` (killed)",
                "- `HYP-RR2-VOLTARGET-ATRRISK-001` / `HYP-RR2-H4-REGIME-ALIGN-GATE-001` (killed)",
                "- FRED / XS / LNY / Asia densify; MaxKZ/RR retune",
                "",
                "## Survivor bar",
                "",
                "N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 ∧ stress lift vs RR2 baseline x1.5.",
                "",
                "## Clearance",
                "",
                "**CLEARED** for offline probe only.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = []
    for p in results:
        m = p["metrics"]
        hc = p["haircut_flat12"]
        rows.append(
            f"| `{p['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"**{(hc.get('x1_5') or {}).get('pf')}** | **{p['verdict'].replace('KILLED_AT_OFFLINE_PROBE','KILL').replace('PROBE_SURVIVOR','SURVIVOR')}** |"
        )

    survivors = [p for p in results if p["verdict"] == "PROBE_SURVIVOR"]
    model0 = "AUTHORIZED" if survivors else "WITHHELD"
    status = (
        "PROBE_SURVIVOR_PRESENT"
        if survivors
        else "OFFLINE_ALL_KILL"
    )

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — monetization rebuild + cost/tick V2",
                "",
                "Date: 2026-07-15",
                f"Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / "
                f"`{'MODEL0_' + model0 if survivors else 'NO_MODEL0'}`",
                "Lane: single checkout; no-Git; offline-first",
                "",
                "## Track B — monetization probes",
                "",
                "| ID | N | PF | tpw | stress x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *rows,
                "",
                f"Receipt: `{receipt}`",
                f"Baseline RR2 x1.5: **{(base.get('haircut_flat12') or {}).get('x1_5', {}).get('pf')}**",
                f"Design: `{OUT_DESIGN.name}`",
                f"De-dup: `{OUT_DEDUP.name}`",
                f"Probes: `{OUT_JSON.name}`",
                "",
                "## Model 0",
                "",
                f"{'Run Model 0 on: ' + ', '.join('`'+s['hypothesis_id']+'`' for s in survivors) if survivors else 'Withheld (zero PROBE_SURVIVOR).'}",
                "",
                "## Decisions",
                "",
                "1. Keep `EXO_FRED_DISPLACE_SPAM_PAUSED`.",
                "2. Do **not** densify scale frac / trail k / R-mult bands from this readout.",
                "3. Do **not** revive BE@1R / MFE stall / vol-target / H4-regime / FRED / XS.",
                "4. Best shelf unchanged until a survivor beats it under Model 0: RR2 `194548`.",
                "5. Track A cost freeze: see companion cost-tick V2 artifacts (do not invent).",
                "",
                "## Next",
                "",
                "- If survivor: Model 0 on that child ID only.",
                "- If all kill: continue cost acquire / next monetization class outside this board.",
                "- GOAL unmet.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    vn_lines = [
        "# Brief hành động (VN) — Monetization rebuild + cost/tick V2",
        "",
        f"- Track B: {len(results)} kiến trúc monetization trên RR2 `194548` — "
        + (
            f"**{len(survivors)} SURVIVOR** → Model 0 được phép."
            if survivors
            else "**ALL KILL** offline; không Model 0."
        ),
    ]
    for p in results:
        m = p["metrics"]
        x15 = (p["haircut_flat12"].get("x1_5") or {}).get("pf")
        tag = "SURVIVOR" if p["verdict"] == "PROBE_SURVIVOR" else "KILL"
        vn_lines.append(
            f"  - `{p['hypothesis_id']}`: N={m['n']} PF={m['pf']} tpw={m['tpw']} "
            f"x1.5={x15} → **{tag}** ({','.join(p['notes']) or 'ok'})"
        )
    vn_lines += [
        f"- Baseline RR2 +$12 x1.5 ≈ **{(base.get('haircut_flat12') or {}).get('x1_5', {}).get('pf')}**.",
        "- Cost surface: xem `20260715_COST_TICK_ACQUIRE_V2_COVERAGE_PROOF.md` — "
        "chỉ freeze nếu research-grade; GAP còn lại ghi rõ.",
        "- Cấm densify scale/trail/R-mult; cấm revive BE@1R / MFE stall / FRED / XS.",
        f"- Shelf tốt nhất vẫn RR2 `194548` trừ khi Model 0 survivor thắng. Receipt `{receipt[:16]}…`",
        "- GOAL unmet.",
        "",
    ]
    OUT_VN.write_text("\n".join(vn_lines) + "\n", encoding="utf-8")

    md = [
        "# Monetization rebuild — offline probes",
        "",
        f"Receipt: `{receipt}`",
        f"Baseline: N={base['metrics']['n']} PF={base['metrics']['pf']} "
        f"tpw={base['metrics']['tpw']} x1.5="
        f"{(base.get('haircut_flat12') or {}).get('x1_5', {}).get('pf')}",
        "",
        "| ID | N | PF | tpw | x1.5 | lift | Verdict | notes |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for p in results:
        m = p["metrics"]
        x15 = (p["haircut_flat12"].get("x1_5") or {}).get("pf")
        md.append(
            f"| `{p['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{x15} | {p['stress_lift_vs_baseline']} | `{p['verdict']}` | "
            f"{','.join(p['notes'])} |"
        )
    md += ["", f"Model 0: **{model0}**", ""]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> int:
    print("[monetize] load RR2 trades…", flush=True)
    trades_csv = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_csv)
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    baseline_x15 = float((base_hc.get("x1_5") or {}).get("pf") or 0.0)
    print(
        f"[monetize] N={len(trades)} PF={base_m['pf']} tpw={base_m['tpw']} "
        f"x1.5={baseline_x15}",
        flush=True,
    )

    print("[monetize] load M15…", flush=True)
    bars, bar_index, _atr = load_m15(SYMBOL)
    print(f"[monetize] M15 bars={len(bars)}", flush=True)

    print("[monetize] load H1 for vol-regime…", flush=True)
    h1 = load_rates(SYMBOL, mt5.TIMEFRAME_H1)
    h1_times = [datetime.fromtimestamp(int(t)) for t in h1["time"]]
    h1_atr_arr = atr_wilder(h1["high"], h1["low"], h1["close"], H1_ATR_LEN)
    h1_atr: list[float | None] = [
        None if math.isnan(x) else float(x) for x in h1_atr_arr
    ]

    # Probe 1: scale-out
    print("[monetize] probe scale-out…", flush=True)
    pnls1: list[float] = []
    reasons1: dict[str, int] = defaultdict(int)
    ch1 = 0
    for t in trades:
        p, r = resim_scaleout(t, bars, bar_index)
        reasons1[r] += 1
        if abs(p - t["pnl"]) > 1e-6:
            ch1 += 1
        pnls1.append(p)
    p1 = probe_family(
        "HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001",
        "architecture_scaleout_monetization",
        {
            "scale_frac": SCALE_FRAC,
            "scale_at_r": SCALE_AT_R,
            "runner_r": RUNNER_R,
            "not": "BE@1R / MFE stall / vol-target size / H4 gate / FRED",
        },
        pnls1,
        reasons1,
        ch1,
        baseline_x15,
        {"mt5_bars_m15": len(bars)},
    )
    print(
        f"  -> {p1['verdict']} PF={p1['metrics']['pf']} "
        f"x1.5={p1['haircut_flat12']['x1_5']['pf']}",
        flush=True,
    )

    # Probe 2: ATR trail
    print("[monetize] probe ATR trail…", flush=True)
    pnls2: list[float] = []
    reasons2: dict[str, int] = defaultdict(int)
    ch2 = 0
    for t in trades:
        p, r = resim_atr_trail(t, bars, bar_index)
        reasons2[r] += 1
        if abs(p - t["pnl"]) > 1e-6:
            ch2 += 1
        pnls2.append(p)
    p2 = probe_family(
        "HYP-RR2-EXIT-ATRTRAIL-ARM075-K15-001",
        "architecture_atr_trail_exit",
        {
            "arm_mfe_r": TRAIL_ARM_R,
            "atr_k": TRAIL_ATR_K,
            "atr_len_m15": TRAIL_ATR_LEN,
            "be_clamp": False,
            "stall_timer": False,
            "not": "BE@1R / MFE stall-cut / MaxKZ / RR densify",
        },
        pnls2,
        reasons2,
        ch2,
        baseline_x15,
        {"mt5_bars_m15": len(bars)},
    )
    print(
        f"  -> {p2['verdict']} PF={p2['metrics']['pf']} "
        f"x1.5={p2['haircut_flat12']['x1_5']['pf']}",
        flush=True,
    )

    # Probe 3: vol-regime R multiple
    print("[monetize] probe vol-regime R…", flush=True)
    pnls3: list[float] = []
    reasons3: dict[str, int] = defaultdict(int)
    rmult_hist: dict[str, int] = defaultdict(int)
    ch3 = 0
    for t in trades:
        p, r, rm = resim_volregime_rmult(t, h1_times, h1_atr, bars, bar_index)
        reasons3[r] += 1
        rmult_hist[str(rm)] += 1
        if abs(p - t["pnl"]) > 1e-6:
            ch3 += 1
        pnls3.append(p)
    p3 = probe_family(
        "HYP-RR2-VOLREGIME-RMULT-H1ATR-001",
        "architecture_volregime_rmult",
        {
            "h1_atr_len": H1_ATR_LEN,
            "pct_lookback": H1_PCT_LOOKBACK,
            "rmult_lo_mid_hi": [RMULT_LO, RMULT_MID, RMULT_HI],
            "pct_lo_hi": [PCT_LO, PCT_HI],
            "not": "H4 EMA align gate / entry densify / vol-target sizing / FRED",
        },
        pnls3,
        reasons3,
        ch3,
        baseline_x15,
        {"mt5_bars_m15": len(bars), "rmult_hist": dict(rmult_hist), "h1_bars": len(h1_times)},
    )
    print(
        f"  -> {p3['verdict']} PF={p3['metrics']['pf']} "
        f"x1.5={p3['haircut_flat12']['x1_5']['pf']}",
        flush=True,
    )

    probes = [p1, p2, p3]
    survivors = [p for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    payload: dict[str, Any] = {
        "schema": "monetization_rebuild_offline_probes_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": (
            "Owner post-greenfield rebuild authorized; EXO_FRED_DISPLACE_SPAM_PAUSED; "
            "Track B monetization"
        ),
        "rr2_sleeve": RR2_RUN,
        "trades_csv": str(trades_csv.relative_to(ROOT)).replace("\\", "/"),
        "baseline": {"metrics": base_m, "haircut_flat12": base_hc},
        "probes": probes,
        "survivors": [s["hypothesis_id"] for s in survivors],
        "model0": "AUTHORIZED" if survivors else "WITHHELD",
        "policy": [
            "no_densify_from_readout",
            "no_BE@1R_revive",
            "no_MFE_stall_revive",
            "no_voltarget_h4regime_revive",
            "no_FRED_XS_LNY_Asia_spam",
            "no_invent_cost_surface",
        ],
        "best_shelf": "RR2_20260714_194548",
        "goal": "UNMET",
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    receipt = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_docs(payload, receipt)

    print(json.dumps({"receipt": receipt, "survivors": payload["survivors"], "model0": payload["model0"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
