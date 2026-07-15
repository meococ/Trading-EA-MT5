#!/usr/bin/env python3
"""Structural rebuild offline probes V1 — post Wave5 diminishing returns.

A priori theses (frozen before ranking; GPT waived; no densify):
  T1 HYP-COST-ARM-RMIN-RR2-001  — cost-aware arming filter on frozen RR2 series
  T2 HYP-AUDJPY-LEAD-USDJPY-H1-001 — cross-asset lead (NOT GBPJPY densify)
  T3 HYP-D1-TREND-H1-PB-001 — D1 regime lock + H1 pullback (NOT ATR%ile/EMA densify)
  T4 Phase-0 RR2+Spark equal-join diagnostic recompute (NOT ceremony)

Probe-only. Model 0 withheld unless verdict=PROBE_SURVIVOR.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

RR2_RUN = "20260714_194548"
SPARK_RUN = "20260714_193358"
RR2_DIR = RUNS / "EA_SilverBullet" / RR2_RUN
SPARK_DIR = RUNS / "EA_M15SparkAsian" / SPARK_RUN

OUT_JSON = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V1.json"
OUT_MD = READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V1.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_PCT = 0.50


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


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


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


def load_closed_trades(path: Path) -> list[dict]:
    """Pair OPEN/CLOSE by position_id; keep final closes with net_profit."""
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in ("1", "true", "True"):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                # USDJPY approx: 1 point = 0.001; PnL per point per 1.0 lot ≈ $6.67 at ~150, but
                # use observed loser magnitude when available: risk_usd ≈ |pnl| for pure SL hits.
                risk_usd = risk_pts * vol * 1000.0 / 100.0  # point-value proxy for JPY pairs @ lot
                # Better proxy from volume*risk_pts*contract: for USDJPY, tickvalue≈(vol*100000*0.001)/price
                px = entry if entry else 150.0
                if px > 0 and vol > 0 and risk_pts > 0:
                    risk_usd = (vol * 100_000.0 * risk_pts) / px
                closed.append(
                    {
                        "position_id": pid,
                        "tag": op.get("tag") or row.get("tag") or "",
                        "open_time": op.get("event_time") or "",
                        "close_time": row.get("event_time") or "",
                        "pnl": pnl,
                        "entry": entry,
                        "sl": sl,
                        "volume": vol,
                        "risk_pts": risk_pts,
                        "risk_usd": risk_usd,
                        "achievedr": float(row.get("achievedr") or 0),
                    }
                )
    return closed


# ---------------------------------------------------------------------------
# T1 — cost-aware arming on RR2 series (architecture: risk gate, not densify)
# ---------------------------------------------------------------------------
def probe_t1_cost_arm(trades: list[dict]) -> dict:
    """Arm only if structure stop risk_$ >= k * a priori friction ($12).

    A priori k frozen at 2.0 and 3.0 (not mined from stress readout).
    Optimistic: filter existing entries — if even optimism fails, kill thesis.
    """
    base = metrics([t["pnl"] for t in trades])
    base_hc = haircuts([t["pnl"] for t in trades])
    variants = {}
    survivors = []
    for k in (2.0, 3.0):
        thr = BASE_COST * k
        kept = [t for t in trades if t["risk_usd"] >= thr]
        pnls = [t["pnl"] for t in kept]
        m = metrics(pnls)
        hc = haircuts(pnls)
        # Probe survivor bar: stress x1.5 PF>=1.20 OR exp>=25 after +$12; tpw in [1.5,6]; N>=80
        pass_stress = (hc["x1_5"]["pf"] or 0) >= 1.20 or (hc["x1"]["exp"] or 0) >= 25.0
        pass_cadence = m["tpw"] is not None and 1.5 <= m["tpw"] <= 6.0
        pass_n = m["n"] >= 80
        verdict = "PROBE_SURVIVOR" if (pass_stress and pass_cadence and pass_n and (m["pf"] or 0) > 1.20) else "KILLED_AT_OFFLINE_PROBE"
        variants[f"k{k:g}"] = {
            "min_risk_usd": thr,
            "metrics": m,
            "cost_stress": hc,
            "pass_stress_proxy": pass_stress,
            "pass_cadence_proxy": pass_cadence,
            "pass_n": pass_n,
            "verdict": verdict,
        }
        if verdict == "PROBE_SURVIVOR":
            survivors.append(f"k{k:g}")

    # Also: asymmetric — keep trades only when projected TP R$ >= friction*2
    # Using achievedR>0 winners scaled: require risk_usd * 2.0 >= 2*BASE_COST (same as k=2 RR>=1)
    # Secondary: drop tiny-risk floor-min-lot geometry (risk_usd < $8)
    tiny = [t for t in trades if t["risk_usd"] >= 8.0]
    tiny_m = metrics([t["pnl"] for t in tiny])
    tiny_hc = haircuts([t["pnl"] for t in tiny])

    overall = "PROBE_SURVIVOR" if survivors else "KILLED_AT_OFFLINE_PROBE"
    return {
        "hypothesis_id": "HYP-COST-ARM-RMIN-RR2-001",
        "thesis": "cost_aware_arming_risk_model",
        "de_dup": "NOT MaxKZ/RR densify; filter = min structure risk vs friction; parent RR2 frozen",
        "baseline_rr2": {"metrics": base, "cost_stress": base_hc},
        "variants": variants,
        "drop_tiny_risk_lt8": {"metrics": tiny_m, "cost_stress": tiny_hc},
        "risk_usd_p50": round(sorted(t["risk_usd"] for t in trades)[len(trades) // 2], 2) if trades else None,
        "risk_usd_p10": round(sorted(t["risk_usd"] for t in trades)[max(0, len(trades) // 10)], 2) if trades else None,
        "verdict": overall,
        "model0": "AUTHORIZED_IF_SURVIVOR" if overall == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
        "survivors": survivors,
    }


# ---------------------------------------------------------------------------
# T4 — Phase-0 diagnostic equal-join (NOT ceremony)
# ---------------------------------------------------------------------------
def parse_report_orders(report_html: Path) -> list[dict]:
    """Best-effort extract closed trade PnL from report.html Deal rows."""
    text = report_html.read_text(encoding="utf-8", errors="ignore")
    # AlphaFactory enhanced_summary preferred when present
    return []


def load_pnls_from_run(run_dir: Path) -> tuple[list[float], dict]:
    """Prefer PX6 trades CSV; else parse report.html Deals (Spark path)."""
    enh = run_dir / "analysis" / "enhanced_summary.json"
    meta: dict = {}
    if enh.exists():
        meta = json.loads(enh.read_text(encoding="utf-8"))
    try:
        trades_path = find_trades_csv(run_dir)
        closed = load_closed_trades(trades_path)
        return [t["pnl"] for t in closed], {
            "enhanced_summary": meta,
            "source": str(trades_path),
            "n_closed": len(closed),
        }
    except FileNotFoundError:
        pass
    # Reuse proven HTML deals parser from capacity compose probe
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "rr2_spark_cap",
        str(PRE / "20260714_OFFLINE_SB_RR2_SPARK_CAPACITY_COMPOSE_PROBE_V1.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    report = run_dir / "report.html"
    deals = mod.parse_deals_html(report)
    trades = mod.deals_to_trades(deals)
    pnls = [float(t["pnl"]) for t in trades]
    return pnls, {
        "enhanced_summary": meta,
        "source": str(report),
        "n_closed": len(pnls),
    }


def probe_t4_compose_diagnostic(rr2_pnls: list[float], spark_pnls: list[float]) -> dict:
    pooled = rr2_pnls + spark_pnls
    m = metrics(pooled)
    # Cadence for union ≈ (n_rr2 + n_spark) / weeks on intersection approx same window
    hc = haircuts(pooled)
    weekly_note = "equal 1:1 trade-series union; correlation not re-estimated here"
    # Ceremony legality
    contamination = {
        "status": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
        "attestation": "preflight/20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json",
        "universe_freeze": "readouts/20260714_PHASE0_RR2_SPARK_UNIVERSE_FREEZE.md",
        "ceremony_legal": False,
    }
    return {
        "hypothesis_id": "HYP-PHASE0-RR2-SPARK-COMPOSE-DIAG-001",
        "thesis": "portfolio_sleeve_equal_join_diagnostic_only",
        "frozen_universe": {"rr2": RR2_RUN, "spark": SPARK_RUN},
        "rr2": metrics(rr2_pnls),
        "spark": metrics(spark_pnls),
        "pooled": m,
        "cost_stress_pooled": hc,
        "note": weekly_note,
        "contamination": contamination,
        "verdict": "DIAGNOSTIC_ONLY__CEREMONY_BLOCKED",
        "model0": "WITHHELD_CONTAMINATION",
        "goal_like_proxy": {
            "pf_gt_1_30": (m["pf"] or 0) > 1.30,
            "tpw_in_2_5": m["tpw"] is not None and 2.0 <= m["tpw"] <= 5.0,
            "x1_5_ge_1_25": (hc["x1_5"]["pf"] or 0) >= 1.25,
        },
    }


# ---------------------------------------------------------------------------
# T2 / T3 — MT5 bar probes (may fail if terminal unavailable)
# ---------------------------------------------------------------------------
@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def try_mt5_probes() -> dict:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {"status": "MT5_MODULE_MISSING", "t2": None, "t3": None}

    if not mt5.initialize():
        return {"status": f"MT5_INIT_FAIL:{mt5.last_error()}", "t2": None, "t3": None}

    def load(symbol_candidates: tuple[str, ...], tf) -> tuple[str, list[Bar]]:
        for s in symbol_candidates:
            if not mt5.symbol_select(s, True):
                continue
            rates = mt5.copy_rates_range(s, tf, FROM, TO)
            if rates is not None and len(rates) > 500:
                bars = [
                    Bar(
                        t=datetime.fromtimestamp(int(r["time"])),
                        o=float(r["open"]),
                        h=float(r["high"]),
                        l=float(r["low"]),
                        c=float(r["close"]),
                    )
                    for r in rates
                ]
                return s, bars
        raise RuntimeError(f"no rates for {symbol_candidates}")

    def atr(bars: list[Bar], i: int, period: int = 14) -> float:
        if i < period:
            return 0.0
        trs = []
        for j in range(i - period + 1, i + 1):
            prev = bars[j - 1].c
            trs.append(max(bars[j].h - bars[j].l, abs(bars[j].h - prev), abs(bars[j].l - prev)))
        return sum(trs) / period

    def simulate(bars, i_entry, direction, entry, sl, tp, max_hold=24, flat_hour=22):
        risk = abs(entry - sl)
        if risk <= 0:
            return 0.0
        exit_px = entry
        for k in range(i_entry + 1, min(len(bars), i_entry + 1 + max_hold)):
            bk = bars[k]
            if bk.t.hour >= flat_hour or bk.t.weekday() >= 4:
                exit_px = bk.o
                break
            if direction > 0:
                if bk.l <= sl:
                    exit_px = sl
                    break
                if bk.h >= tp:
                    exit_px = tp
                    break
            else:
                if bk.h >= sl:
                    exit_px = sl
                    break
                if bk.l <= tp:
                    exit_px = tp
                    break
            exit_px = bk.c
        # cash PnL at 0.5% risk of deposit
        risk_cash = DEPOSIT * (RISK_PCT / 100.0)
        signed = (exit_px - entry) / risk * direction
        return risk_cash * signed

    out: dict = {"status": "OK"}

    # T2 AUDJPY lead → USDJPY
    try:
        lead_sym, lead = load(("AUDJPY", "AUDJPYm", "AUDJPY."), mt5.TIMEFRAME_H1)
        foll_sym, foll = load(("USDJPY", "USDJPYm", "USDJPY."), mt5.TIMEFRAME_H1)
        lead_map = {b.t: i for i, b in enumerate(lead)}
        pnls: list[float] = []
        day_count: dict[str, int] = defaultdict(int)
        RR = 2.5
        # Impulse on lead bar[2]; follower decision on closed bar aligned at t (bar[1] semantics).
        for j in range(40, len(foll) - 2):
            fb = foll[j]
            if fb.t.weekday() >= 4:
                continue
            lj = lead_map.get(fb.t)
            if lj is None or lj < 40:
                continue
            li = lj - 2
            if li < 14:
                continue
            lb = lead[li]
            a = atr(lead, li)
            if a <= 0:
                continue
            if (lb.h - lb.l) < 1.2 * a:
                continue
            direction = 1 if lb.c > lb.o else -1
            if (fb.c - fb.o) * direction <= 0:
                continue
            day = fb.t.strftime("%Y-%m-%d")
            if day_count[day] >= 2:
                continue
            entry = fb.c
            sl = entry - direction * 1.0 * atr(foll, j)
            if abs(entry - sl) <= 0:
                continue
            tp = entry + direction * RR * abs(entry - sl)
            pnl = simulate(foll, j, direction, entry, sl, tp)
            pnls.append(pnl)
            day_count[day] += 1

        m = metrics(pnls)
        hc = haircuts(pnls)
        pass_stress = (hc["x1_5"]["pf"] or 0) >= 1.20 or (hc["x1"]["exp"] or 0) >= 25.0
        pass_cadence = m["tpw"] is not None and 1.5 <= m["tpw"] <= 6.0
        pass_n = m["n"] >= 80
        pass_pf = (m["pf"] or 0) > 1.20
        verdict = (
            "PROBE_SURVIVOR"
            if pass_stress and pass_cadence and pass_n and pass_pf
            else "KILLED_AT_OFFLINE_PROBE"
        )
        out["t2"] = {
            "hypothesis_id": "HYP-AUDJPY-LEAD-USDJPY-H1-001",
            "thesis": "cross_asset_quality_impulse_lag",
            "de_dup": "NOT GBPJPY-lead densify; NOT GOLDJPY inverse; new leader AUDJPY",
            "lead_symbol": lead_sym,
            "follow_symbol": foll_sym,
            "metrics": m,
            "cost_stress": hc,
            "verdict": verdict,
            "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
            "kill_notes": [
                x
                for x, ok in (
                    ("stress_fail", pass_stress),
                    ("cadence_fail", pass_cadence),
                    ("n_fail", pass_n),
                    ("pf_fail", pass_pf),
                )
                if not ok
            ],
        }
    except Exception as e:
        out["t2"] = {"hypothesis_id": "HYP-AUDJPY-LEAD-USDJPY-H1-001", "verdict": "PROBE_BLOCKED", "error": str(e)}

    # T3 D1 trend → H1 pullback (structure: D1 EMA50 slope + H1 PB to EMA21)
    try:
        sym, h1 = load(("USDJPY", "USDJPYm", "USDJPY."), mt5.TIMEFRAME_H1)
        _, d1 = load((sym,), mt5.TIMEFRAME_D1)

        def ema(vals: list[float], period: int) -> list[float]:
            out_e = [0.0] * len(vals)
            if len(vals) < period:
                return out_e
            k = 2 / (period + 1)
            out_e[period - 1] = sum(vals[:period]) / period
            for i in range(period, len(vals)):
                out_e[i] = vals[i] * k + out_e[i - 1] * (1 - k)
            return out_e

        d1_close = [b.c for b in d1]
        d1_ema50 = ema(d1_close, 50)
        d1_map = {b.t.date(): (b, d1_ema50[i], d1_ema50[i - 1] if i > 0 else d1_ema50[i]) for i, b in enumerate(d1)}

        h1_close = [b.c for b in h1]
        h1_ema21 = ema(h1_close, 21)
        pnls = []
        day_count = defaultdict(int)
        RR = 2.5
        for i in range(60, len(h1) - 2):
            b = h1[i]
            if b.t.weekday() >= 4:
                continue
            # HTF = prior completed D1 (yesterday)
            dkey = (b.t.date().toordinal() - 1)
            # find d1 by date
            prior_date = datetime.fromordinal(b.t.date().toordinal() - 1).date()
            if prior_date not in d1_map:
                continue
            db, e50, e50_prev = d1_map[prior_date]
            if e50 == 0 or e50_prev == 0:
                continue
            bull = e50 > e50_prev and db.c > e50
            bear = e50 < e50_prev and db.c < e50
            if not (bull or bear):
                continue
            direction = 1 if bull else -1
            e21 = h1_ema21[i]
            if e21 <= 0:
                continue
            # pullback touch: low/high within 0.25 ATR of EMA21 then close resume
            a = atr(h1, i)
            if a <= 0:
                continue
            touched = (b.l <= e21 + 0.25 * a and direction > 0) or (b.h >= e21 - 0.25 * a and direction < 0)
            resume = (b.c - b.o) * direction > 0 and (b.c - e21) * direction > 0
            if not (touched and resume):
                continue
            day = b.t.strftime("%Y-%m-%d")
            if day_count[day] >= 2:
                continue
            entry = b.c
            sl = entry - direction * 1.1 * a
            tp = entry + direction * RR * abs(entry - sl)
            pnl = simulate(h1, i, direction, entry, sl, tp)
            pnls.append(pnl)
            day_count[day] += 1

        m = metrics(pnls)
        hc = haircuts(pnls)
        pass_stress = (hc["x1_5"]["pf"] or 0) >= 1.20 or (hc["x1"]["exp"] or 0) >= 25.0
        pass_cadence = m["tpw"] is not None and 1.5 <= m["tpw"] <= 6.0
        pass_n = m["n"] >= 80
        pass_pf = (m["pf"] or 0) > 1.20
        # Extra de-dup kill: if this is essentially H1-EMA-STACK-PB (already killed offline),
        # we still allow as D1-gated child but must beat parent kill (tpw was 6.27).
        verdict = (
            "PROBE_SURVIVOR"
            if pass_stress and pass_cadence and pass_n and pass_pf
            else "KILLED_AT_OFFLINE_PROBE"
        )
        out["t3"] = {
            "hypothesis_id": "HYP-D1-TREND-H1-PB-001",
            "thesis": "multi_tf_d1_lock_h1_pullback",
            "de_dup": "NOT ATR%ile Donchian; NOT H1-EMA-STACK-PB ungated densify; D1 slope+close gate is the architecture change",
            "symbol": sym,
            "metrics": m,
            "cost_stress": hc,
            "verdict": verdict,
            "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD_KILL_FAST",
            "kill_notes": [
                x
                for x, ok in (
                    ("stress_fail", pass_stress),
                    ("cadence_fail", pass_cadence),
                    ("n_fail", pass_n),
                    ("pf_fail", pass_pf),
                )
                if not ok
            ],
            "vs_killed_ema_stack": "parent HYP-H1-EMA-STACK-PB-001 killed offline tpw=6.27/pf~1.02; this adds D1 lock to cut cadence+thin edge",
        }
    except Exception as e:
        out["t3"] = {"hypothesis_id": "HYP-D1-TREND-H1-PB-001", "verdict": "PROBE_BLOCKED", "error": str(e)}

    mt5.shutdown()
    return out


def write_md(result: dict) -> None:
    t1 = result["t1"]
    t4 = result["t4"]
    mt5p = result.get("mt5_probes") or {}
    t2 = mt5p.get("t2")
    t3 = mt5p.get("t3")
    lines = [
        "# Structural rebuild offline probes V1 (post-Wave5)",
        "",
        f"Generated: {result['generated_at']}",
        "Authority: Owner R&D continue; `DEMO_DISCOVERY_DIMINISHING_RETURNS=true`; GPT waived",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        "## Panel merge (architecture shortlist ≤4)",
        "",
        "| # | Thesis | Architecture | Offline verdict |",
        "|---|---|---|---|",
        f"| T1 | Cost-aware arming on RR2 | Risk model | **{t1['verdict']}** |",
        f"| T2 | AUDJPY→USDJPY H1 lead | Cross-asset lag | **{(t2 or {}).get('verdict', 'NOT_RUN')}** |",
        f"| T3 | D1 trend → H1 PB | Multi-TF confirmation | **{(t3 or {}).get('verdict', 'NOT_RUN')}** |",
        f"| T4 | RR2+Spark equal-join | Portfolio sleeve rules | **{t4['verdict']}** |",
        "",
        "## T1 — Cost-aware arming",
        "",
        f"- Baseline RR2 `{RR2_RUN}`: PF {t1['baseline_rr2']['metrics']['pf']} / "
        f"tpw {t1['baseline_rr2']['metrics']['tpw']} / "
        f"+$12 x1.5 PF {t1['baseline_rr2']['cost_stress']['x1_5']['pf']}",
        f"- risk_usd P10/P50: {t1.get('risk_usd_p10')} / {t1.get('risk_usd_p50')}",
    ]
    for k, v in t1["variants"].items():
        lines.append(
            f"- `{k}` min_risk=${v['min_risk_usd']}: N={v['metrics']['n']} PF={v['metrics']['pf']} "
            f"tpw={v['metrics']['tpw']} x1.5={v['cost_stress']['x1_5']['pf']} → **{v['verdict']}**"
        )
    lines += [
        "",
        "## T2 / T3 — MT5 bar probes",
        "",
        f"- MT5 status: `{mt5p.get('status')}`",
    ]
    if t2:
        lines.append(
            f"- T2: N={t2.get('metrics', {}).get('n')} PF={t2.get('metrics', {}).get('pf')} "
            f"tpw={t2.get('metrics', {}).get('tpw')} → **{t2.get('verdict')}** "
            f"kills={t2.get('kill_notes') or t2.get('error')}"
        )
    if t3:
        lines.append(
            f"- T3: N={t3.get('metrics', {}).get('n')} PF={t3.get('metrics', {}).get('pf')} "
            f"tpw={t3.get('metrics', {}).get('tpw')} → **{t3.get('verdict')}** "
            f"kills={t3.get('kill_notes') or t3.get('error')}"
        )
    lines += [
        "",
        "## T4 — Phase-0 compose",
        "",
        f"- Universe frozen: RR2 `{RR2_RUN}` + Spark `{SPARK_RUN}`",
        f"- Pooled diagnostic: PF {t4['pooled']['pf']} / tpw {t4['pooled']['tpw']} / "
        f"x1.5 {t4['cost_stress_pooled']['x1_5']['pf']}",
        f"- Ceremony: **BLOCKED** — `{t4['contamination']['status']}`",
        f"- Goal-like proxy (diagnostic only): {t4['goal_like_proxy']}",
        "",
        "## What NOT to test",
        "",
        "- MaxKZ/RR/SB/Spark densify; ATR%ile; Asia/London/NY IB hours",
        "- Wave1–5 killed/parked families; GBPJPY-lead retune; EMA-stack densify",
        "- Phase-0 outcome compose until Owner clean freeze review",
        "- Another random session-break Model 0 batch",
        "",
        "## Model 0 authorization",
        "",
    ]
    survivors = []
    if t1["verdict"] == "PROBE_SURVIVOR":
        survivors.append("T1")
    if (t2 or {}).get("verdict") == "PROBE_SURVIVOR":
        survivors.append("T2")
    if (t3 or {}).get("verdict") == "PROBE_SURVIVOR":
        survivors.append("T3")
    if survivors:
        lines.append(f"Survivors authorized for registry+prereg+Model0: **{', '.join(survivors)}**")
    else:
        lines.append("**No offline survivors.** Model 0 withheld. Prefer next structural object redesign, not densify.")
    lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    trades_csv = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_csv)
    rr2_pnls = [t["pnl"] for t in trades]
    spark_pnls, spark_meta = load_pnls_from_run(SPARK_DIR)

    t1 = probe_t1_cost_arm(trades)
    t4 = probe_t4_compose_diagnostic(rr2_pnls, spark_pnls)
    t4["spark_meta"] = {k: spark_meta[k] for k in ("source", "n_closed")}

    print("T1 done", t1["verdict"], flush=True)
    print("T4 done", t4["verdict"], flush=True)
    print("Starting MT5 probes...", flush=True)
    mt5_probes = try_mt5_probes()
    print("MT5 status", mt5_probes.get("status"), flush=True)

    result = {
        "schema": "structural_rebuild_offline_probes.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "Owner_post_Wave5_diminishing_returns",
        "gpt": "waived",
        "demo_discovery_diminishing_returns": True,
        "best_shelf": RR2_RUN,
        "t1": t1,
        "t4": t4,
        "mt5_probes": mt5_probes,
        "banned_densify": [
            "MaxKZ",
            "RR",
            "SB",
            "Spark",
            "ATR%ile",
            "Asia/London/NY IB hours",
            "Wave1-5 killed/parked",
        ],
    }
    # Collect survivors
    surv = []
    if t1["verdict"] == "PROBE_SURVIVOR":
        surv.append(t1["hypothesis_id"])
    for key in ("t2", "t3"):
        block = mt5_probes.get(key) or {}
        if block.get("verdict") == "PROBE_SURVIVOR":
            surv.append(block["hypothesis_id"])
    result["offline_survivors"] = surv
    result["any_model0_authorized"] = bool(surv)

    raw = json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8")
    result["result_sha256"] = sha256_bytes(raw)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_md(result)
    print("Wrote", OUT_JSON)
    print("Wrote", OUT_MD)
    print("survivors", surv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
