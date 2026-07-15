#!/usr/bin/env python3
"""Track B — tick-path ATR-trail monetization (best faithful proxy).

Authority: Owner R&D continue 2026-07-15; EXO_FRED_DISPLACE_SPAM_PAUSED;
monetization rebuild still authorized; free Model 0 only for PROBE_SURVIVOR.

Named open class: ATR trailing monetization on parked RR2 `194548`.
  ≠ BE@1R (never clamp SL to entry)
  ≠ MFE stall-cut (no stall-timer / giveback hard-close)
  ≠ scale-out / timebox / vol-regime-R (killed prior board)
  ≠ voided OHLC M15 path rebuild (false SL inflation)

Tick bid/ask path for 2021–2025 tester trades is NOT available on disk
(multi-month copy_ticks_range hangs; QFSI still shallow). Proxies a priori:

  1) HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001
     Outcome-faithful MFE-envelope: MFE from M1 extremes in hold window;
     trail_floor_R = MFE_R − 1.5×ATR14(M15_closed)/R; bind only if
     realized_R < trail_floor_R after arm@0.75R.

  2) HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001
     Same envelope method; frozen alternate formula arm@1.0R, k=2.0
     (still ≠ BE: trail = peak−k·ATR, never clamp to entry).

  3) HYP-RR2-EXIT-ATRTRAIL-M1PATH-ARM075-K15-001
     M1 OHLC walk proxy (finer than voided M15); outcome-constrained
     dual-touch rule; labeled ≠ tick — do not overclaim.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
RUNS = ROOT / "02. AlphaFactory" / "runs"

RR2_RUN = "20260714_194548"
RR2_DIR = RUNS / "EA_SilverBullet" / RR2_RUN
SYMBOL = "USDJPY"

OUT_JSON = PRE / "20260715_ATRTRAIL_TICKPROXY_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_ATRTRAIL_TICKPROXY_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_ATRTRAIL_TICKPROXY_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_ATRTRAIL_TICKPROXY_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_ATRTRAIL_TICKPROXY_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_ATRTRAIL_TICKPROXY_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0

ATR_LEN_M15 = 14
# Child 1 — primary envelope
ARM_A = 0.75
K_A = 1.5
# Child 2 — alternate a priori envelope
ARM_B = 1.0
K_B = 2.0
# Child 3 — M1 path (same formula as A)
ARM_C = 0.75
K_C = 1.5


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
                        "deal_reason": str(row.get("deal_reason") or ""),
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


def build_bar_index(times: np.ndarray) -> dict[datetime, int]:
    out: dict[datetime, int] = {}
    for i, t in enumerate(times):
        out[datetime.fromtimestamp(int(t))] = i
    return out


def find_bar_i(
    ot: datetime, bar_index: dict[datetime, int], step_min: int
) -> int | None:
    t0 = ot.replace(second=0, microsecond=0)
    minute = (t0.minute // step_min) * step_min
    t0 = t0.replace(minute=minute)
    if t0 in bar_index:
        return bar_index[t0]
    for k in range(0, 12):
        for cand in (
            t0 + timedelta(minutes=step_min * k),
            t0 - timedelta(minutes=step_min * k),
        ):
            if cand in bar_index:
                return bar_index[cand]
    return None


def atr_at_or_before(
    ot: datetime, m15_times: list[datetime], m15_atr: np.ndarray
) -> float | None:
    """Closed-bar ATR: last M15 bar with time <= ot (no lookahead)."""
    lo, hi = 0, len(m15_times) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if m15_times[mid] <= ot:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    if ans is None:
        return None
    # Prefer prior completed bar if ot falls inside current forming bar
    i = ans - 1 if ans > 0 else ans
    v = float(m15_atr[i])
    if math.isnan(v) or v <= 0:
        return None
    return v


def mfe_mae_from_m1(
    trade: dict, m1: dict[str, np.ndarray], m1_index: dict[datetime, int]
) -> tuple[float | None, float | None, str]:
    """MFE/MAE in R units from M1 extremes during hold (path extrema artifact)."""
    if trade["open_time"] is None or trade["close_time"] is None:
        return None, None, "no_time"
    if trade["direction"] == 0 or trade["risk_pts"] <= 0:
        return None, None, "no_risk"
    entry = trade["entry"]
    R = trade["risk_pts"]
    d = trade["direction"]
    i0 = find_bar_i(trade["open_time"], m1_index, 1)
    i1 = find_bar_i(trade["close_time"], m1_index, 1)
    if i0 is None or i1 is None:
        return None, None, "no_m1"
    if i1 < i0:
        i0, i1 = i1, i0
    # Include bars from open through close
    h = m1["high"][i0 : i1 + 1]
    l = m1["low"][i0 : i1 + 1]
    if len(h) == 0:
        return None, None, "empty"
    if d > 0:
        mfe = (float(np.max(h)) - entry) / R
        mae = (entry - float(np.min(l))) / R
    else:
        mfe = (entry - float(np.min(l))) / R
        mae = (float(np.max(h)) - entry) / R
    return max(0.0, mfe), max(0.0, mae), "ok"


def resim_mfe_envelope(
    trade: dict,
    m1: dict[str, np.ndarray],
    m1_index: dict[datetime, int],
    m15_times: list[datetime],
    m15_atr: np.ndarray,
    arm_r: float,
    atr_k: float,
) -> tuple[float, str, dict]:
    """Outcome-faithful ATR trail via MFE envelope (no bar-walk SL invention)."""
    meta: dict[str, Any] = {"method": "mfe_envelope_m1_extrema"}
    if trade["risk_usd"] <= 0 or trade["risk_pts"] <= 0:
        return trade["pnl"], "orig_no_risk", meta
    atr = atr_at_or_before(trade["open_time"], m15_times, m15_atr)
    if atr is None:
        return trade["pnl"], "orig_no_atr", meta
    mfe_r, mae_r, st = mfe_mae_from_m1(trade, m1, m1_index)
    if mfe_r is None:
        return trade["pnl"], f"orig_{st}", meta
    realized_r = trade["pnl"] / trade["risk_usd"]
    trail_width_r = atr_k * atr / trade["risk_pts"]
    meta.update(
        {
            "mfe_r": round(mfe_r, 4),
            "mae_r": round(mae_r or 0.0, 4),
            "realized_r": round(realized_r, 4),
            "atr_m15": round(atr, 6),
            "trail_width_r": round(trail_width_r, 4),
            "arm_r": arm_r,
            "atr_k": atr_k,
        }
    )
    if mfe_r < arm_r - 1e-12:
        return trade["pnl"], "unarmed_keep", meta

    trail_floor_r = mfe_r - trail_width_r
    # ≠ BE: do NOT raise floor to 0.0 / entry
    meta["trail_floor_r"] = round(trail_floor_r, 4)

    if realized_r + 1e-12 >= trail_floor_r:
        # Giveback from peak did not exceed trail width → trail never binds
        return trade["pnl"], "trail_not_bind", meta

    # Trail binds: exit at trail floor (outcome-faithful under peak-then-exit assumption)
    new_pnl = trail_floor_r * trade["risk_usd"]
    return new_pnl, "trail_bind", meta


def resim_m1_path_trail(
    trade: dict,
    m1: dict[str, np.ndarray],
    m1_index: dict[datetime, int],
    m15_times: list[datetime],
    m15_atr: np.ndarray,
    arm_r: float,
    atr_k: float,
) -> tuple[float, str, dict]:
    """M1 OHLC walk ATR trail; outcome-constrained on dual-touch bars.

    Limitations (explicit): still ≠ tick; intra-bar order unknown; M1 can
    overstate stops vs tester ticks. Dual-touch bars defer to original outcome.
    """
    meta: dict[str, Any] = {
        "method": "m1_ohlc_path_proxy",
        "limitations": [
            "not_tick_bidask",
            "intra_bar_order_unknown",
            "dual_touch_defers_to_original",
        ],
    }
    if trade["open_time"] is None or trade["direction"] == 0:
        return trade["pnl"], "orig_no_dir", meta
    if trade["risk_pts"] <= 0 or trade["risk_usd"] <= 0:
        return trade["pnl"], "orig_no_risk", meta
    atr = atr_at_or_before(trade["open_time"], m15_times, m15_atr)
    if atr is None:
        return trade["pnl"], "orig_no_atr", meta

    entry = trade["entry"]
    sl0 = trade["sl"]
    tp0 = trade["tp"]
    d = trade["direction"]
    R = abs(entry - sl0)
    if R <= 0:
        return trade["pnl"], "orig_bad_R", meta
    if not tp0 or tp0 <= 0:
        tp0 = entry + d * 2.0 * R

    i0 = find_bar_i(trade["open_time"], m1_index, 1)
    end = trade["close_time"] or (trade["open_time"] + timedelta(hours=48))
    i_end = find_bar_i(end, m1_index, 1)
    if i0 is None:
        return trade["pnl"], "orig_no_m1", meta
    if i_end is None:
        i_end = min(i0 + 60 * 48, len(m1["time"]) - 1)

    armed = False
    peak = entry
    trail_sl = sl0
    trail_dist = atr_k * atr
    orig_r = trade["pnl"] / trade["risk_usd"]

    for i in range(i0, i_end + 1):
        t = datetime.fromtimestamp(int(m1["time"][i]))
        if t < trade["open_time"]:
            continue
        if t > end + timedelta(minutes=2):
            break
        h = float(m1["high"][i])
        l = float(m1["low"][i])
        stop = trail_sl if armed else sl0

        hit_stop = (d > 0 and l <= stop) or (d < 0 and h >= stop)
        hit_tp = (d > 0 and h >= tp0) or (d < 0 and l <= tp0)

        if hit_stop and hit_tp:
            # Ambiguous intra-bar: defer to original outcome (anti false-SL)
            return trade["pnl"], "dual_touch_defer_orig", meta

        if hit_stop:
            if d > 0:
                r = (stop - entry) / R
            else:
                r = (entry - stop) / R
            # Outcome constraint: do not invent a stop worse than original
            # if original closed later as a winner (path/tester mismatch)
            if (not armed) and orig_r > 0:
                return trade["pnl"], "false_sl_guard_orig", meta
            return r * trade["risk_usd"], ("trail_hit" if armed else "sl"), meta

        if hit_tp:
            if d > 0:
                r = (tp0 - entry) / R
            else:
                r = (entry - tp0) / R
            return r * trade["risk_usd"], "tp", meta

        if d > 0:
            mfe_r = max(0.0, (h - entry) / R)
            fav = h
        else:
            mfe_r = max(0.0, (entry - l) / R)
            fav = l

        if (not armed) and mfe_r >= arm_r - 1e-12:
            armed = True
            peak = fav

        if armed:
            if d > 0:
                peak = max(peak, fav)
                new_trail = peak - trail_dist
                # Never BE clamp to entry
                if new_trail > trail_sl:
                    trail_sl = new_trail
            else:
                peak = min(peak, fav)
                new_trail = peak + trail_dist
                if new_trail < trail_sl:
                    trail_sl = new_trail

    return trade["pnl"], "orig_timeout", meta


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
        "exit_reasons": dict(sorted(reasons.items(), key=lambda x: -x[1])),
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


def append_registry(rows: list[dict]) -> None:
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_docs(payload: dict, receipt: str) -> None:
    results = payload["probes"]
    base = payload["baseline"]
    survivors = [p for p in results if p["verdict"] == "PROBE_SURVIVOR"]
    status = "PROBE_SURVIVOR_PRESENT" if survivors else "OFFLINE_ALL_KILL"
    model0 = "AUTHORIZED" if survivors else "WITHHELD"
    base_x15 = (base.get("haircut_flat12") or {}).get("x1_5", {}).get("pf")

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — tick-path ATR-trail monetization (proxy)",
                "",
                "Date: 2026-07-15",
                "Lane: single; no-Git; offline-first",
                "Authority: Owner R&D continue; monetization rebuild authorized",
                "",
                "## Problem",
                "",
                "Fixed-RR RR2 `194548` dies under +$12 x1.5. Scale-out / timebox /",
                "vol-regime-R killed. OHLC M15 ATR-trail path **voided** (false SL",
                "inflation). Named open class: **ATR trailing monetization**.",
                "",
                "## Tick availability",
                "",
                "Full tick bid/ask path for tester window **unavailable** (QFSI shallow;",
                "`copy_ticks_range` multi-month hang). Proxies used; do not claim tick fidelity.",
                "",
                "## Rejected a priori",
                "",
                "- BE@1R / trail-from-BE clamp",
                "- MFE stall-cut hard-close",
                "- Scale-out / timebox / vol-regime-R densify",
                "- Voided M15 OHLC path rebuild as authority",
                "- FRED / XS / LNY / Asia densify",
                "",
                "## Design 1 — MFE envelope arm0.75 k1.5 "
                "(`HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001`)",
                "",
                "Authority method. MFE from M1 extrema in hold; ATR14(M15) closed at/before",
                f"entry; arm MFE≥{ARM_A}R; trail_floor = MFE − {K_A}×ATR/R. Bind only if",
                "realized_R < trail_floor. Never clamp to entry. No stall timer.",
                "",
                "## Design 2 — MFE envelope arm1.0 k2.0 "
                "(`HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001`)",
                "",
                f"Same envelope; frozen alternate arm≥{ARM_B}R, k={K_B}. Still ≠ BE:",
                "trail is peak−k·ATR, not SL→entry.",
                "",
                "## Design 3 — M1 path arm0.75 k1.5 "
                "(`HYP-RR2-EXIT-ATRTRAIL-M1PATH-ARM075-K15-001`)",
                "",
                "M1 OHLC walk + dual-touch defer-to-original. **Labeled ≠ tick.**",
                "Joint-scored with explicit limitations; do not overclaim.",
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
                "# De-dup clearance — tick-path ATR-trail monetization (proxy)",
                "",
                "Date: 2026-07-15",
                "Authority: Owner rebuild authorized; EXO_FRED_DISPLACE_SPAM_PAUSED",
                "",
                "## Objects",
                "",
                "| ID | Class | Independence claim |",
                "|---|---|---|",
                "| `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001` | ATR trail MFE-envelope | ≠ BE@1R; ≠ MFE stall; ≠ scale/timebox/volR; ≠ voided M15 path |",
                "| `HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001` | ATR trail MFE-envelope alt formula | a priori arm/k; ≠ densify after kill; ≠ BE clamp |",
                "| `HYP-RR2-EXIT-ATRTRAIL-M1PATH-ARM075-K15-001` | ATR trail M1 path proxy | finer than voided M15; dual-touch guard; ≠ tick claim |",
                "",
                "## Banned collisions",
                "",
                "- `HYP-RR2-EXIT-BE1R-M15PATH-001` / `HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001`",
                "- `HYP-RR2-EXIT-SCALEOUT-1R50-RUN2R-001` / TIMEBOX / VOLREGIME-RMULT",
                "- Voided `HYP-RR2-EXIT-ATRTRAIL-ARM075-K15-001` M15 OHLC path authority",
                "- FRED / XS / LNY / Asia densify",
                "",
                "## Survivor bar",
                "",
                "N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 ∧ stress lift vs RR2 baseline.",
                "",
                "## Clearance",
                "",
                "**CLEARED** for offline probe (proxy methods labeled).",
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
        tag = (
            "SURVIVOR"
            if p["verdict"] == "PROBE_SURVIVOR"
            else "KILL"
        )
        rows.append(
            f"| `{p['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"**{(hc.get('x1_5') or {}).get('pf')}** | **{tag}** |"
        )

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — tick-path ATR-trail monetization (proxy)",
                "",
                "Date: 2026-07-15",
                f"Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / "
                f"`{'MODEL0_' + model0 if survivors else 'NO_MODEL0'}`",
                "Lane: single checkout; no-Git; offline-first",
                "",
                "## Method",
                "",
                "- Tick path: **unavailable** → MFE-envelope (authority) + M1 path proxy.",
                "- Do not claim tick fidelity. Cost freeze still GAP (parallel QFSI only).",
                "",
                "## Offline joint screen",
                "",
                "| ID | N | PF | tpw | stress x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
                *rows,
                "",
                f"Receipt: `{receipt}`",
                f"Baseline RR2 x1.5: **{base_x15}**",
                f"Design: `{OUT_DESIGN.name}`",
                f"De-dup: `{OUT_DEDUP.name}`",
                f"Probes: `{OUT_JSON.name}`",
                "",
                "## Model 0",
                "",
                (
                    "Run Model 0 on: "
                    + ", ".join(f"`{s['hypothesis_id']}`" for s in survivors)
                    if survivors
                    else "Withheld (zero PROBE_SURVIVOR)."
                ),
                "",
                "## Decisions",
                "",
                "1. Keep `EXO_FRED_DISPLACE_SPAM_PAUSED`.",
                "2. Do **not** densify arm/k from this readout.",
                "3. Do **not** revive BE@1R / MFE stall / scale / timebox / volR / FRED / XS.",
                "4. Do **not** re-open voided M15 OHLC path as authority.",
                "5. Cost freeze: still GAP — QFSI accumulate parallel only.",
                "6. Best shelf RR2 `194548` until Model 0 survivor beats it. GOAL unmet.",
                "",
                "## Next",
                "",
                "- If survivor: Model 0 native ATR-trail path on that ID only.",
                "- If all kill: next monetization class outside ATR-trail densify,",
                "  or wait research-grade tick/cost surface — do not idle on banned families.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    vn = [
        "# Brief hành động (VN) — ATR-trail tick-proxy monetization",
        "",
        "- Tick path đầy đủ **không có** → dùng proxy: MFE-envelope (authority) + M1 path (nhãn ≠ tick).",
        f"- Track B trên RR2 `194548`: "
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
        vn.append(
            f"  - `{p['hypothesis_id']}`: N={m['n']} PF={m['pf']} tpw={m['tpw']} "
            f"x1.5={x15} → **{tag}** ({','.join(p['notes']) or 'ok'})"
        )
    vn += [
        f"- Baseline RR2 +$12 x1.5 ≈ **{base_x15}**.",
        "- Cấm densify arm/k; cấm revive BE@1R / MFE stall / scale / timebox / volR / FRED / XS.",
        "- Cost freeze vẫn GAP (2/90) — QFSI accumulate song song, không block Track B.",
        f"- Shelf: RR2 `194548`. Receipt `{receipt[:16]}…`. GOAL unmet.",
        "",
    ]
    OUT_VN.write_text("\n".join(vn) + "\n", encoding="utf-8")

    md = [
        "# ATR-trail tick-proxy — offline probes",
        "",
        f"Receipt: `{receipt}`",
        f"Baseline: N={base['metrics']['n']} PF={base['metrics']['pf']} "
        f"tpw={base['metrics']['tpw']} x1.5={base_x15}",
        "",
        "Method: tick unavailable → MFE-envelope (authority) + M1 path proxy (labeled).",
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


def patch_hot(payload: dict, receipt: str) -> None:
    results = payload["probes"]
    survivors = [p for p in results if p["verdict"] == "PROBE_SURVIVOR"]
    status = "PROBE_SURVIVOR_PRESENT" if survivors else "OFFLINE_ALL_KILL"
    stamp = datetime.now().strftime("%Y-%m-%d ~%H:%M ICT")
    lines = [
        f"- **ATR-TRAIL TICK-PROXY MONETIZATION CLOSEOUT ({stamp}) —",
        f"  `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}` / "
        f"`{'MODEL0_AUTHORIZED' if survivors else 'NO_MODEL0'}`.",
        "  Tick path unavailable; proxies labeled. Offline joint screen on RR2 `194548`:",
    ]
    for p in results:
        x15 = (p["haircut_flat12"].get("x1_5") or {}).get("pf")
        tag = "SURVIVOR" if p["verdict"] == "PROBE_SURVIVOR" else "KILL"
        lines.append(
            f"  - `{p['hypothesis_id']}` PF **{p['metrics']['pf']}** x1.5 **{x15}** "
            f"→ **{tag}**."
        )
    lines += [
        f"  Receipt `{receipt}`; VN `readouts/20260715_ATRTRAIL_TICKPROXY_VN_ACTION_BRIEF.md`;",
        "  closeout `readouts/20260715_ATRTRAIL_TICKPROXY_SESSION_CLOSEOUT.md`.",
        "  Do not densify arm/k; do not revive BE@1R/MFE stall/scale/timebox/volR;",
        "  do not invent cost freeze. QFSI accumulate parallel only.",
        "  Best shelf RR2 `194548`. GOAL unmet.",
        "",
    ]
    block = "\n".join(lines)
    text = HOT.read_text(encoding="utf-8")
    # Insert after "# Hot Cache" header + Updated line
    parts = text.split("\n", 3)
    # Rewrite Updated line + prepend Active Truth bullet after "## Active Truth"
    marker = "## Active Truth\n"
    idx = text.find(marker)
    if idx < 0:
        HOT.write_text(block + "\n" + text, encoding="utf-8")
        return
    insert_at = idx + len(marker)
    new_text = text[:insert_at] + "\n" + block + text[insert_at:]
    # Refresh Updated line
    import re

    new_text = re.sub(
        r"^Updated:.*$",
        f"Updated: {stamp} | ATR-trail tick-proxy board; RR2 `194548`; GOAL unmet",
        new_text,
        count=1,
        flags=re.M,
    )
    HOT.write_text(new_text, encoding="utf-8")


def main() -> int:
    print("[atrtrail] load RR2 trades…", flush=True)
    trades_csv = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_csv)
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    baseline_x15 = float((base_hc.get("x1_5") or {}).get("pf") or 0.0)
    print(
        f"[atrtrail] N={len(trades)} PF={base_m['pf']} tpw={base_m['tpw']} "
        f"x1.5={baseline_x15}",
        flush=True,
    )

    print("[atrtrail] load M15 ATR…", flush=True)
    m15 = load_rates(SYMBOL, mt5.TIMEFRAME_M15)
    m15_times = [datetime.fromtimestamp(int(t)) for t in m15["time"]]
    m15_atr = atr_wilder(m15["high"], m15["low"], m15["close"], ATR_LEN_M15)
    print(f"[atrtrail] M15 bars={len(m15_times)}", flush=True)

    print("[atrtrail] load M1 (extrema + path proxy)…", flush=True)
    m1 = load_rates(SYMBOL, mt5.TIMEFRAME_M1)
    m1_index = build_bar_index(m1["time"])
    print(f"[atrtrail] M1 bars={len(m1['time'])}", flush=True)

    probes: list[dict] = []

    # --- Probe 1: MFE envelope A ---
    print("[atrtrail] probe MFEENV ARM075 K15…", flush=True)
    pnls: list[float] = []
    reasons: dict[str, int] = defaultdict(int)
    ch = 0
    bind_n = 0
    for t in trades:
        p, r, _meta = resim_mfe_envelope(
            t, m1, m1_index, m15_times, m15_atr, ARM_A, K_A
        )
        reasons[r] += 1
        if r == "trail_bind":
            bind_n += 1
        if abs(p - t["pnl"]) > 1e-6:
            ch += 1
        pnls.append(p)
    p1 = probe_family(
        "HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM075-K15-001",
        "architecture_atr_trail_mfe_envelope",
        {
            "method": "mfe_envelope_m1_extrema",
            "arm_mfe_r": ARM_A,
            "atr_k": K_A,
            "atr_len_m15": ATR_LEN_M15,
            "be_clamp": False,
            "stall_timer": False,
            "tick_path": False,
            "authority": True,
            "not": "BE@1R / MFE stall / scale / timebox / volR / voided M15 path",
        },
        pnls,
        reasons,
        ch,
        baseline_x15,
        {"n_trail_bind": bind_n, "m1_bars": int(len(m1["time"])), "m15_bars": len(m15_times)},
    )
    probes.append(p1)
    print(
        f"  -> {p1['verdict']} PF={p1['metrics']['pf']} "
        f"x1.5={p1['haircut_flat12']['x1_5']['pf']} bind={bind_n}",
        flush=True,
    )

    # --- Probe 2: MFE envelope B ---
    print("[atrtrail] probe MFEENV ARM100 K20…", flush=True)
    pnls = []
    reasons = defaultdict(int)
    ch = 0
    bind_n = 0
    for t in trades:
        p, r, _meta = resim_mfe_envelope(
            t, m1, m1_index, m15_times, m15_atr, ARM_B, K_B
        )
        reasons[r] += 1
        if r == "trail_bind":
            bind_n += 1
        if abs(p - t["pnl"]) > 1e-6:
            ch += 1
        pnls.append(p)
    p2 = probe_family(
        "HYP-RR2-EXIT-ATRTRAIL-MFEENV-ARM100-K20-001",
        "architecture_atr_trail_mfe_envelope",
        {
            "method": "mfe_envelope_m1_extrema",
            "arm_mfe_r": ARM_B,
            "atr_k": K_B,
            "atr_len_m15": ATR_LEN_M15,
            "be_clamp": False,
            "stall_timer": False,
            "tick_path": False,
            "authority": True,
            "not": "BE@1R / densify-after-kill / MFE stall / voided M15 path",
        },
        pnls,
        reasons,
        ch,
        baseline_x15,
        {"n_trail_bind": bind_n, "m1_bars": int(len(m1["time"])), "m15_bars": len(m15_times)},
    )
    probes.append(p2)
    print(
        f"  -> {p2['verdict']} PF={p2['metrics']['pf']} "
        f"x1.5={p2['haircut_flat12']['x1_5']['pf']} bind={bind_n}",
        flush=True,
    )

    # --- Probe 3: M1 path ---
    print("[atrtrail] probe M1PATH ARM075 K15…", flush=True)
    pnls = []
    reasons = defaultdict(int)
    ch = 0
    for t in trades:
        p, r, _meta = resim_m1_path_trail(
            t, m1, m1_index, m15_times, m15_atr, ARM_C, K_C
        )
        reasons[r] += 1
        if abs(p - t["pnl"]) > 1e-6:
            ch += 1
        pnls.append(p)
    # Diagnostic fidelity: count losers vs original
    orig_loss = sum(1 for t in trades if t["pnl"] < 0)
    new_loss = sum(1 for p in pnls if p < 0)
    p3 = probe_family(
        "HYP-RR2-EXIT-ATRTRAIL-M1PATH-ARM075-K15-001",
        "architecture_atr_trail_m1_path_proxy",
        {
            "method": "m1_ohlc_path_proxy",
            "arm_mfe_r": ARM_C,
            "atr_k": K_C,
            "atr_len_m15": ATR_LEN_M15,
            "be_clamp": False,
            "stall_timer": False,
            "tick_path": False,
            "authority": False,
            "limitations": [
                "not_tick_bidask",
                "intra_bar_order_unknown",
                "dual_touch_defers_to_original",
            ],
            "not": "tick claim / BE@1R / MFE stall / voided M15 path authority",
        },
        pnls,
        reasons,
        ch,
        baseline_x15,
        {
            "m1_bars": int(len(m1["time"])),
            "orig_losers": orig_loss,
            "proxy_losers": new_loss,
            "loser_inflation": new_loss - orig_loss,
        },
    )
    probes.append(p3)
    print(
        f"  -> {p3['verdict']} PF={p3['metrics']['pf']} "
        f"x1.5={p3['haircut_flat12']['x1_5']['pf']} "
        f"losers {orig_loss}->{new_loss}",
        flush=True,
    )

    payload = {
        "schema_version": "sonic_atrtrail_tickproxy_offline.v1",
        "created_at_utc": datetime.utcnow().isoformat() + "Z",
        "rr2_sleeve": RR2_RUN,
        "trades_csv": str(trades_csv.relative_to(ROOT)).replace("\\", "/"),
        "trades_csv_sha256": sha256_file(trades_csv),
        "symbol": SYMBOL,
        "tick_path_available": False,
        "proxy_policy": {
            "authority": "mfe_envelope_m1_extrema",
            "diagnostic": "m1_ohlc_path_proxy",
            "voided": "m15_ohlc_path_rebuild_false_sl",
            "do_not_claim": "tick_bidask_fidelity",
        },
        "baseline": {
            "metrics": base_m,
            "haircut_flat12": base_hc,
        },
        "survivor_bar": {
            "n_ge": 80,
            "pf_gt": 1.20,
            "tpw_in": [1.5, 6.0],
            "stress_x15_ge": 1.15,
            "require_stress_lift_vs_baseline": True,
        },
        "probes": probes,
        "model0_policy": "PROBE_SURVIVOR_ONLY",
        "bans": [
            "no_BE1R_revive",
            "no_MFE_stall_revive",
            "no_scale_timebox_volR_densify",
            "no_voided_M15_path_authority",
            "no_FRED_XS_LNY_Asia_densify",
            "no_invent_cost_freeze",
        ],
        "best_shelf": "RR2_20260714_194548",
        "goal_met": False,
    }

    # Content hash excludes receipt field (stable); then embed + write.
    raw = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True).encode(
        "utf-8"
    )
    receipt = sha256_bytes(raw)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    write_docs(payload, receipt)

    # Registry append
    reg_rows = []
    for p in probes:
        state = (
            "probe_survivor"
            if p["verdict"] == "PROBE_SURVIVOR"
            else "killed_at_offline_probe"
        )
        reg_rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": p["hypothesis_id"],
                "state": state,
                "parent_candidate": "RR2_20260714_194548",
                "feature_family": "rr2_atr_trail_tickproxy_monetization",
                "lane": "exo_fred_displace_spam_paused_atrtrail_tickproxy",
                "setup_type": p["hypothesis_id"],
                "symbol": SYMBOL,
                "timeframe": "M1_extrema+M15_ATR / M1_path_proxy",
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "source_provenance": (
                    "20260715 ATR-trail tick-proxy board after monetization "
                    "scale/timebox/volR KILL; OHLC M15 path voided"
                ),
                "prereg_path": None,
                "readout_path": (
                    "03. EA Developer/EA_SonicR/research/readouts/"
                    "20260715_ATRTRAIL_TICKPROXY_SESSION_CLOSEOUT.md"
                ),
                "metrics": p["metrics"],
                "validation": {
                    "offline_probe": (
                        "03. EA Developer/EA_SonicR/research/preflight/"
                        "20260715_ATRTRAIL_TICKPROXY_OFFLINE_PROBES.json"
                    ),
                    "haircuts": p["haircut_flat12"],
                    "kill_notes": p["notes"],
                    "model0": p["model0"],
                    "method": p["contract"].get("method"),
                    "dedup": "readouts/20260715_ATRTRAIL_TICKPROXY_DEDUP_CLEARANCE.md",
                },
                "verdict": p["verdict"],
                "receipt_sha256": receipt,
                "updated_at": "2026-07-15",
                "cost_grade": "A_PRIORI_FLAT_12_PROXY_NOT_RESEARCH_FREEZE",
            }
        )
    append_registry(reg_rows)
    patch_hot(payload, receipt)

    print(f"[atrtrail] receipt={receipt}", flush=True)
    print(f"[atrtrail] wrote {OUT_JSON}", flush=True)
    survivors = [p for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    print(
        f"[atrtrail] survivors={len(survivors)} model0="
        f"{'AUTHORIZED' if survivors else 'WITHHELD'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
