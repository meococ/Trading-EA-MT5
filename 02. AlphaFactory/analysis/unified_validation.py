#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Validation Runner — AlphaFactory
=========================================
Inspired by Vibe-Trading's run_validation() pattern: run ALL validation
checks from a single entry point with parallel execution.

Runs:
  1. Enhanced Analysis (session/hour/weekday breakdown)
  2. Equity Curve Audit (R², flat periods, spike dependency)
  3. Monte Carlo (1000 trade-order permutations)
  4. Walk-Forward Analysis (5 windows, 70/30 IS/OOS)
  5. Robustness Suite (7 tests)
  6. Slippage summary artifact
  7. Monthly fitness artifact
  8. Overnight exposure artifact

Usage:
  python unified_validation.py --report "path/to/report.html" [--out "output_dir"] [--sequential]

Or via alpha.ps1:
  .\alpha.ps1 validate-full -Report "path/to/report.html"

Output:
  validation_summary.json — consolidated pass/fail for all gates
  slippage_summary.json — execution slippage/TCA surface if logs exist
  monthly_fitness.json — monthly return/frequency/consistency snapshot
  overnight_exposure.json — no-overnight policy audit
  Individual test outputs preserved in output directory
"""

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from quant_analyzer import (
    Trade,
    bucket_stats,
    deals_to_trades,
    infer_exit_tag,
    parse_deals,
    percentile,
)

ANALYSIS_DIR = Path(__file__).resolve().parent
DEFAULT_RANDOM_SEED = 1729

DEFAULT_GATE_THRESHOLDS: Dict[str, float] = {
    "min_profit_factor": 1.30,
    "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0,
    "max_drawdown_pct": 8.0,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.00,
    "min_robustness_pass_rate": 0.60,
    "max_monte_carlo_p95_dd_pct": 8.0,
    "min_confirmed_trades": 100.0,
    "min_wfa_oos_profitable_ratio": 0.60,
    "max_pbo": 0.20,
    "max_white_reality_check_p": 0.05,
    "min_spread_coverage_ratio": 0.99,
    "min_commission_samples": 30.0,
    "min_slippage_samples": 100.0,
    "min_confirmed_months": 84.0,
    "min_positive_month_ratio": 0.50,
    "max_month_positive_profit_share": 0.20,
    "min_confirmed_half_years": 14.0,
    "min_positive_half_years": 9.0,
    "min_positive_half_year_ratio": 9.0 / 14.0,
    "max_half_year_positive_profit_share": 0.35,
    "min_confirmed_years": 7.0,
    "min_positive_years": 4.0,
    "min_positive_year_ratio": 4.0 / 7.0,
    "max_year_positive_profit_share": 0.40,
}

# Minimal promotion-grade cost evidence contract. ``sonic_cost_stress.v1`` is a
# report-only fixed-dollar diagnostic and intentionally cannot satisfy this.
VERIFIED_COST_PROVENANCE_SCHEMA: Dict[str, Any] = {
    "schema_version": "verified_execution_cost.v1",
    "provenance_status": "VERIFIED",
    "report_binding": "artifact.report resolves to the validated report",
    "execution_provenance": {
        "broker": "nonempty string",
        "server": "nonempty string",
        "broker_fingerprint": "SHA256 matching run_manifest.broker_fingerprint",
        "server_fingerprint": "SHA256 matching run_manifest.server_fingerprint",
        "account_fingerprint": "SHA256 matching run_manifest.account_fingerprint",
        "data_fingerprint": "SHA256 matching run_manifest.data_fingerprint",
        "symbol/from/to": "exact run-manifest identity",
        "symbol_geometry": {
            "digits/point/pip_size": "exact run_manifest.fingerprint_basis geometry",
        },
        "historical_spread": {
            "source": "existing evidence file",
            "sha256": "actual evidence-file SHA256",
            "coverage": "per-symbol coverage_ratio >= 0.99 and consistent with sample counts",
        },
        "commission": {
            "source": "existing evidence file with matching SHA256",
            "value": "finite numeric value >= 0",
            "sample_count": "minimum sample count or verified broker contract",
            "broker_contract": {
                "round_turn_account_per_lot": "finite value > 0 exactly equal to commission.value",
            },
        },
        "slippage": {
            "source": "existing evidence file with matching SHA256",
            "sample_count": "minimum independent-reference total with >=30 buys and >=30 sells",
            "reference_sides": "buy ask and sell bid",
            "p90": "finite nonnegative p90_buy/p90_sell with p90_roundturn equal to their sum",
            "slippage_unit": "pips",
            "method": "nonempty adverse-fill methodology",
        },
        "cost_methodology": {
            "direction_aware": True,
            "description": "nonempty long/short bid-ask application description",
        },
    },
    "net_r_x1_5": "finite positive value equal to recomputed cost_x1_50 net R",
    "scenarios": "unique exact label+multiplier rows with recomputable finite profit factor",
}

# ─── Bars-per-year lookup (from Vibe-Trading pattern) ───

BARS_PER_YEAR = {
    "M1": 252 * 1440 // 1,
    "M5": 252 * 288,
    "M15": 252 * 96,
    "M30": 252 * 48,
    "H1": 252 * 24,
    "H4": 252 * 6,
    "D1": 252,
    "W1": 52,
    "MN1": 12,
}


def bars_per_year(timeframe: str = "D1") -> int:
    """Return annualization factor for a given MT5 timeframe."""
    return BARS_PER_YEAR.get(timeframe.upper(), 252)


# ─── Individual test runners ───


def _run_python(script: str, args: List[str], label: str) -> Dict[str, Any]:
    """Run a Python analysis script as subprocess, capture output."""
    script_path = ANALYSIS_DIR / script
    if not script_path.exists():
        return {"test": label, "status": "SKIP", "reason": f"{script} not found"}

    cmd = [sys.executable, str(script_path)] + args
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            cwd=str(ANALYSIS_DIR),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        elapsed = round(time.perf_counter() - t0, 1)
        return {
            "test": label,
            "status": "OK" if result.returncode == 0 else "FAIL",
            "returncode": result.returncode,
            "elapsed_s": elapsed,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"test": label, "status": "TIMEOUT", "elapsed_s": 300}
    except Exception as e:
        return {"test": label, "status": "ERROR", "reason": str(e)}



def run_enhanced_analysis(report: str, out_dir: str) -> Dict[str, Any]:
    """Gate 1-4: Enhanced analysis (session, hour, weekday, streaks, weaknesses)."""
    return _run_python(
        "enhanced_analyzer.py",
        ["--report", report, "--charts", "--out", out_dir],
        "enhanced_analysis",
    )



def run_equity_audit(report: str, out_dir: str) -> Dict[str, Any]:
    """Gate 2: Equity curve audit (R², flat periods, spike dependency)."""
    return _run_python(
        "equity_curve_audit.py",
        ["--report", report, "--out", out_dir],
        "equity_curve_audit",
    )



def run_monte_carlo(report: str, out_dir: str) -> Dict[str, Any]:
    """Gate 6: Monte Carlo simulation (1000 permutations)."""
    return _run_python(
        "monte_carlo.py",
        ["--report", report, "--sims", "1000", "--seed", str(DEFAULT_RANDOM_SEED), "--out", out_dir],
        "monte_carlo",
    )



def run_walk_forward(report: str, out_dir: str, variant_manifest: str = "") -> Dict[str, Any]:
    """Gate 5: Walk-Forward Analysis (5 windows, 70/30 split)."""
    args = ["--report", report, "--windows", "5", "--out", out_dir]
    if variant_manifest:
        args.extend(["--variant-manifest", variant_manifest])
    return _run_python(
        "walk_forward.py",
        args,
        "walk_forward",
    )



def run_robustness(report: str, out_dir: str, variant_manifest: str = "") -> Dict[str, Any]:
    """Gate 6: Robustness suite (7 tests)."""
    args = ["--report", report, "--test", "all", "--seed", str(DEFAULT_RANDOM_SEED), "--out", out_dir]
    if variant_manifest:
        args.extend(["--variant-manifest", variant_manifest])
    return _run_python(
        "robustness_suite.py",
        args,
        "robustness_suite",
    )


def run_cscv_pbo(variants_dir: str, out_dir: str, variant_manifest: str = "") -> Dict[str, Any]:
    """Generate a deterministic PBO artifact from the full supplied variant family."""
    args = ["--variants-dir", variants_dir, "--seed", str(DEFAULT_RANDOM_SEED), "--out", out_dir]
    if variant_manifest:
        args.extend(["--variant-manifest", variant_manifest])
    return _run_python(
        "cscv_pbo.py",
        args,
        "cscv_pbo",
    )


def run_white_reality_check(variants_dir: str, out_dir: str, variant_manifest: str = "") -> Dict[str, Any]:
    """Generate a deterministic White Reality Check artifact for supplied variants."""
    args = ["--variants-dir", variants_dir, "--seed", str(DEFAULT_RANDOM_SEED), "--out", out_dir]
    if variant_manifest:
        args.extend(["--variant-manifest", variant_manifest])
    return _run_python(
        "white_reality_check.py",
        args,
        "white_reality_check",
    )


# ─── Helpers for post-processing artifacts ───


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except (UnicodeError, json.JSONDecodeError):
            continue
    return {}



def _write_json(path: Path, payload: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)



def _parse_manifest_date(raw: Any) -> Optional[dt.date]:
    if not raw:
        return None
    if isinstance(raw, dt.datetime):
        return raw.date()
    if isinstance(raw, dt.date):
        return raw
    text = str(raw).strip()
    for date_format in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def _elapsed_window_days(
    start_date: Optional[dt.date],
    end_date: Optional[dt.date],
    *,
    inclusive: bool,
) -> Optional[int]:
    if start_date is None or end_date is None or start_date > end_date:
        return None
    return (end_date - start_date).days + (1 if inclusive else 0)



def _month_labels(start_date: dt.date, end_date: dt.date) -> List[str]:
    labels: List[str] = []
    year, month = start_date.year, start_date.month
    while (year, month) <= (end_date.year, end_date.month):
        labels.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return labels



def _load_run_manifest(report_path: Path) -> Dict[str, Any]:
    return _load_json(report_path.parent / "run_manifest.json")



def _resolve_logs_dir(report_path: Path, out_dir: Path) -> Optional[Path]:
    candidates = [
        out_dir / "logs",
        report_path.parent / "analysis" / "logs",
        report_path.parent / "logs",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None



def _classify_monthly_band(monthly_return_pct: float) -> str:
    if monthly_return_pct < 3.0:
        return "below_target"
    if monthly_return_pct < 5.0:
        return "viable"
    if monthly_return_pct <= 10.0:
        return "high_priority"
    return "extra_skepticism_required"



def _crosses_weekend(trade: Trade) -> bool:
    start = trade.entry_time.date()
    end = trade.exit_time.date()
    cur = start
    while cur <= end:
        if cur.weekday() >= 5:
            return True
        cur += dt.timedelta(days=1)
    return False



def _load_trade_set(report_path: Path) -> Tuple[List[Any], List[Trade], float]:
    deals = parse_deals(report_path)
    trades = deals_to_trades(deals)
    if not deals:
        raise ValueError("No deals parsed from report")
    start_equity = next(
        (
            d.balance
            for d in deals
            if (d.side or "").strip().lower() == "balance" and d.balance > 0
        ),
        deals[0].balance,
    )
    return deals, trades, start_equity



def generate_slippage_summary(report: str, out_dir: str) -> Dict[str, Any]:
    report_path = Path(report)
    out_path = Path(out_dir) / "slippage_summary.json"
    manifest = _load_run_manifest(report_path)
    logs_dir = _resolve_logs_dir(report_path, Path(out_dir))

    if not logs_dir:
        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "logs_dir": "",
            "available": False,
            "status": "WARN",
            "reason": "No logs directory found for TCA/slippage extraction.",
            "symbol": manifest.get("symbol", ""),
            "period": manifest.get("period", ""),
            "slippage_pts": None,
            "scenarios_pts": None,
            "execution_quality": None,
        }
        _write_json(out_path, payload)
        return {"status": "WARN", "artifact": str(out_path), "reason": payload["reason"]}

    try:
        from tca_summary import build_summary as build_tca_summary

        tca = build_tca_summary(logs_dir)
        slip = ((tca.get("exec") or {}).get("slippage_pts") or {})
        p50_abs = abs(float(slip.get("p50", 0.0) or 0.0))
        abs_mean = float(slip.get("abs_mean", 0.0) or 0.0)
        p90_abs = float(slip.get("p90_abs", 0.0) or 0.0)
        max_abs = float(slip.get("max_abs", 0.0) or 0.0)
        n = int(slip.get("n", 0) or 0)

        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "logs_dir": str(logs_dir),
            "available": n > 0,
            "status": "OK" if n > 0 else "WARN",
            "symbol": manifest.get("symbol", ""),
            "period": manifest.get("period", ""),
            "slippage_pts": slip if n > 0 else None,
            "scenarios_pts": (
                {
                    "baseline": round(max(p50_abs, abs_mean), 4),
                    "realistic_live": round(max(abs_mean, p90_abs), 4),
                    "stressed": round(max(p90_abs, max_abs), 4),
                }
                if n > 0
                else None
            ),
            "execution_quality": {
                "open_ack_minus_fill_gap": ((tca.get("reconciliation") or {}).get("open_ack_minus_fill_gap", 0)),
                "modify_unresolved": ((tca.get("reconciliation") or {}).get("modify_unresolved", 0)),
                "close_unresolved": ((tca.get("reconciliation") or {}).get("close_unresolved", 0)),
                "final_closes": ((tca.get("trades") or {}).get("final_closes", 0)),
                "passive_final_closes": ((tca.get("reconciliation") or {}).get("passive_final_closes", 0)),
            },
            "tca_summary": tca,
        }
        _write_json(out_path, payload)
        return {
            "status": "OK" if n > 0 else "WARN",
            "artifact": str(out_path),
            "reason": "Observed slippage extracted from TCA logs." if n > 0 else "Logs found but no slippage samples present.",
        }
    except Exception as e:
        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "logs_dir": str(logs_dir),
            "available": False,
            "status": "ERROR",
            "reason": str(e),
        }
        _write_json(out_path, payload)
        return {"status": "ERROR", "artifact": str(out_path), "reason": str(e)}



def generate_monthly_fitness(report: str, out_dir: str) -> Dict[str, Any]:
    report_path = Path(report)
    out_path = Path(out_dir) / "monthly_fitness.json"
    manifest = _load_run_manifest(report_path)
    slippage_payload = _load_json(Path(out_dir) / "slippage_summary.json")

    try:
        _, trades, start_equity = _load_trade_set(report_path)
        if not trades:
            raise ValueError("No trades reconstructed from report")

        manifest_from = _parse_manifest_date(str(manifest.get("from", "")))
        manifest_to = _parse_manifest_date(str(manifest.get("to", "")))
        exit_dates = [t.exit_time.date() for t in trades]
        start_date = manifest_from or min(exit_dates)
        end_date = manifest_to or max(exit_dates)
        month_labels = _month_labels(start_date, end_date)

        monthly_by_label = {label: {"month": label, "n": 0, "net_profit": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "max_dd_abs": 0.0} for label in month_labels}
        for label, bucket in _group_monthly(trades):
            stats = bucket_stats(bucket)
            stats["month"] = label
            monthly_by_label[label] = stats

        months = [monthly_by_label[label] for label in month_labels]
        pnl_series = [float(row.get("net_profit", 0.0) or 0.0) for row in months]
        active_months = sum(1 for row in months if int(row.get("n", 0) or 0) > 0)
        total_months = len(months)
        inactive_months = max(total_months - active_months, 0)
        trades_per_month_total = len(trades) / total_months if total_months else 0.0
        trades_per_active_month = len(trades) / active_months if active_months else 0.0
        mean_monthly_pnl = sum(pnl_series) / total_months if total_months else 0.0
        median_monthly_pnl = percentile(pnl_series, 50) if pnl_series else 0.0
        mean_monthly_return_pct = (mean_monthly_pnl / start_equity * 100.0) if start_equity else 0.0
        median_monthly_return_pct = (median_monthly_pnl / start_equity * 100.0) if start_equity else 0.0
        positive_month_ratio = (sum(1 for x in pnl_series if x > 0) / total_months) if total_months else 0.0
        negative_month_ratio = (sum(1 for x in pnl_series if x < 0) / total_months) if total_months else 0.0
        flat_month_ratio = (sum(1 for x in pnl_series if abs(x) < 1e-9) / total_months) if total_months else 0.0
        low_pf_months = sum(1 for row in months if int(row.get("n", 0) or 0) > 0 and float(row.get("profit_factor", 0.0) or 0.0) < 0.8)
        strong_pf_months = sum(1 for row in months if int(row.get("n", 0) or 0) > 0 and float(row.get("profit_factor", 0.0) or 0.0) >= 1.2)
        slippage_points = (((slippage_payload.get("scenarios_pts") or {}).get("realistic_live")) if isinstance(slippage_payload, dict) else None)

        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "symbol": manifest.get("symbol", ""),
            "period": manifest.get("period", ""),
            "execution_lane": manifest.get("execution_lane", ""),
            "start_equity": start_equity,
            "total_trades": len(trades),
            "monthly_window": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
                "total_months": total_months,
                "active_months": active_months,
                "inactive_months": inactive_months,
            },
            "trade_frequency": {
                "trades_per_month_total_window": round(trades_per_month_total, 4),
                "trades_per_active_month": round(trades_per_active_month, 4),
            },
            "gross_monthly": {
                "mean_pnl": round(mean_monthly_pnl, 4),
                "median_pnl": round(median_monthly_pnl, 4),
                "p25_pnl": round(percentile(pnl_series, 25), 4) if pnl_series else 0.0,
                "p75_pnl": round(percentile(pnl_series, 75), 4) if pnl_series else 0.0,
                "mean_return_pct": round(mean_monthly_return_pct, 4),
                "median_return_pct": round(median_monthly_return_pct, 4),
                "annualized_from_mean_pct": round(mean_monthly_return_pct * 12.0, 4),
            },
            "consistency": {
                "positive_month_ratio": round(positive_month_ratio, 4),
                "negative_month_ratio": round(negative_month_ratio, 4),
                "flat_month_ratio": round(flat_month_ratio, 4),
                "months_pf_below_0_8": low_pf_months,
                "months_pf_at_or_above_1_2": strong_pf_months,
            },
            "target_band": {
                "assessment_basis": "gross_backtest_monthly_mean_pct",
                "assessed_monthly_return_pct": round(mean_monthly_return_pct, 4),
                "classification": _classify_monthly_band(mean_monthly_return_pct),
                "user_target_band_pct": [3.0, 10.0],
            },
            "slippage_context": {
                "slippage_summary": str(Path(out_dir) / "slippage_summary.json"),
                "realistic_live_slippage_pts": slippage_points,
                "return_after_slippage_pct": None,
                "note": "Slippage points are recorded when logs exist, but return conversion requires symbol/lot-value context not guaranteed inside report-only validation.",
            },
            "months": months,
        }
        _write_json(out_path, payload)
        return {"status": "OK", "artifact": str(out_path), "reason": "Monthly fitness artifact written."}
    except Exception as e:
        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "status": "ERROR",
            "reason": str(e),
        }
        _write_json(out_path, payload)
        return {"status": "ERROR", "artifact": str(out_path), "reason": str(e)}



def _group_monthly(trades: List[Trade]) -> List[Tuple[str, List[Trade]]]:
    buckets: Dict[str, List[Trade]] = {}
    for trade in trades:
        label = f"{trade.exit_time.year:04d}-{trade.exit_time.month:02d}"
        buckets.setdefault(label, []).append(trade)
    return [(label, buckets[label]) for label in sorted(buckets)]



def _duration_hours(trades: List[Trade]) -> List[float]:
    return [max(t.duration_minutes / 60.0, 0.0) for t in trades]



def generate_overnight_exposure(report: str, out_dir: str) -> Dict[str, Any]:
    report_path = Path(report)
    out_path = Path(out_dir) / "overnight_exposure.json"
    manifest = _load_run_manifest(report_path)

    try:
        _, trades, _ = _load_trade_set(report_path)
        if not trades:
            raise ValueError("No trades reconstructed from report")

        overnight = [t for t in trades if t.exit_time.date() > t.entry_time.date()]
        weekend = [t for t in trades if _crosses_weekend(t)]
        friday_to_monday = [
            t for t in trades
            if t.entry_time.weekday() == 4 and t.exit_time.weekday() == 0 and t.exit_time.date() > t.entry_time.date()
        ]
        exit_tags = Counter(infer_exit_tag(t) for t in trades)
        overnight_exit_tags = Counter(infer_exit_tag(t) for t in overnight)
        duration_all = _duration_hours(trades)
        duration_overnight = _duration_hours(overnight)
        total_trades = len(trades)
        overnight_ratio = len(overnight) / total_trades if total_trades else 0.0
        weekend_ratio = len(weekend) / total_trades if total_trades else 0.0
        friday_to_monday_ratio = len(friday_to_monday) / total_trades if total_trades else 0.0

        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "symbol": manifest.get("symbol", ""),
            "period": manifest.get("period", ""),
            "default_policy": "intraday_no_overnight",
            "counts": {
                "total_trades": total_trades,
                "same_day_trades": total_trades - len(overnight),
                "overnight_trades": len(overnight),
                "weekend_crossing_trades": len(weekend),
                "friday_to_monday_trades": len(friday_to_monday),
                "close_22_exits": exit_tags.get("close_22", 0),
                "friday_close_exits": exit_tags.get("friday_close", 0),
            },
            "ratios": {
                "overnight_pct": round(overnight_ratio * 100.0, 4),
                "weekend_crossing_pct": round(weekend_ratio * 100.0, 4),
                "friday_to_monday_pct": round(friday_to_monday_ratio * 100.0, 4),
            },
            "duration_hours": {
                "all_trades": {
                    "mean": round(sum(duration_all) / len(duration_all), 4) if duration_all else 0.0,
                    "p50": round(percentile(duration_all, 50), 4) if duration_all else 0.0,
                    "p90": round(percentile(duration_all, 90), 4) if duration_all else 0.0,
                    "p95": round(percentile(duration_all, 95), 4) if duration_all else 0.0,
                    "max": round(max(duration_all), 4) if duration_all else 0.0,
                },
                "overnight_only": {
                    "mean": round(sum(duration_overnight) / len(duration_overnight), 4) if duration_overnight else 0.0,
                    "p50": round(percentile(duration_overnight, 50), 4) if duration_overnight else 0.0,
                    "p90": round(percentile(duration_overnight, 90), 4) if duration_overnight else 0.0,
                    "p95": round(percentile(duration_overnight, 95), 4) if duration_overnight else 0.0,
                    "max": round(max(duration_overnight), 4) if duration_overnight else 0.0,
                },
            },
            "overnight_exit_tags": [
                {"tag": tag, "n": count}
                for tag, count in overnight_exit_tags.most_common()
            ],
            "policy_verdicts": {
                "intraday_default": "PASS" if not overnight else "FAIL",
                "weekend_holding": "PASS" if not weekend else ("FAIL" if weekend_ratio > 0.10 else "WARNING"),
            },
            "note": "Default workspace doctrine is intraday/no-overnight unless explicitly justified.",
        }
        _write_json(out_path, payload)
        return {"status": "OK", "artifact": str(out_path), "reason": "Overnight exposure artifact written."}
    except Exception as e:
        payload = {
            "generated_at_utc": _now_utc(),
            "report": str(report_path),
            "run_manifest": str(report_path.parent / "run_manifest.json"),
            "status": "ERROR",
            "reason": str(e),
        }
        _write_json(out_path, payload)
        return {"status": "ERROR", "artifact": str(out_path), "reason": str(e)}


# ─── Parallel orchestration (DAG pattern from Vibe-Trading) ───


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_int(value: Any) -> Optional[int]:
    number = _as_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _gate(
    status: str,
    *,
    actual: Any,
    required: str,
    artifact: str = "",
    reason: str = "",
) -> Dict[str, Any]:
    return {
        "status": status,
        "actual": actual,
        "required": required,
        "artifact": artifact,
        "reason": reason,
    }


def _numeric_gate(
    value: Optional[float],
    predicate: Any,
    required: str,
    artifact: Path,
    missing_reason: str,
) -> Dict[str, Any]:
    if value is None:
        return _gate(
            "BLOCKED",
            actual=None,
            required=required,
            artifact=str(artifact),
            reason=missing_reason,
        )
    passed = bool(predicate(value))
    return _gate(
        "PASS" if passed else "FAIL",
        actual=value,
        required=required,
        artifact=str(artifact),
        reason="" if passed else f"Observed value {value} does not satisfy {required}.",
    )


def _first_value(payload: Dict[str, Any], keys: Tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _same_resolved_path(left: Any, right: Path) -> bool:
    if not left:
        return False
    try:
        return Path(str(left)).resolve() == right.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def _resolve_cost_artifact(
    out_path: Path,
    report_path: Path,
    explicit_path: str = "",
) -> Tuple[Dict[str, Any], Optional[Path], str]:
    if explicit_path:
        candidates = [Path(explicit_path)]
    else:
        candidates = sorted(
            {
                *out_path.glob("sonic_cost_stress*.json"),
                *out_path.glob("cost_stress*.json"),
            },
            key=lambda path: (path.stat().st_mtime_ns, path.name) if path.exists() else (0, path.name),
            reverse=True,
        )

    if not candidates:
        return {}, None, "No cost-stress artifact was found."

    invalid_reasons: List[str] = []
    for candidate in candidates:
        payload = _load_json(candidate)
        if not payload:
            invalid_reasons.append(f"unreadable:{candidate}")
            continue
        if not _same_resolved_path(payload.get("report"), report_path):
            invalid_reasons.append(f"report_identity_mismatch:{candidate}")
            continue
        if not isinstance(payload.get("scenarios"), list):
            invalid_reasons.append(f"missing_scenarios:{candidate}")
            continue
        return payload, candidate, ""

    return {}, candidates[0], "; ".join(invalid_reasons)


def _resolve_wfa_artifact(out_path: Path, explicit_path: str = "") -> Tuple[Dict[str, Any], Path]:
    candidates = (
        [Path(explicit_path)]
        if explicit_path
        else [out_path / "optimization_wfa_results.json", out_path / "wfa_results.json"]
    )
    for candidate in candidates:
        payload = _load_json(candidate)
        if payload:
            return payload, candidate
    return {}, candidates[0]


def _validated_cost_scenario(
    payload: Dict[str, Any], label: str, multiplier: float
) -> Tuple[Optional[Dict[str, float]], str]:
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        return None, "cost-stress scenarios must be a list"

    label_indices: List[int] = []
    multiplier_indices: List[int] = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            continue
        if str(scenario.get("scenario", "")) == label:
            label_indices.append(index)
        if _as_float(scenario.get("cost_multiplier")) == multiplier:
            multiplier_indices.append(index)

    if len(label_indices) != 1 or len(multiplier_indices) != 1:
        return (
            None,
            f"{label} must have exactly one scenario label and exactly one "
            f"cost_multiplier={multiplier} row",
        )
    if label_indices[0] != multiplier_indices[0]:
        return None, f"{label} label and cost_multiplier={multiplier} identify different rows"

    scenario = scenarios[label_indices[0]]
    loss_count = _as_int(scenario.get("loss_count"))
    positive_net_r = _as_float(scenario.get("sum_positive_net_r"))
    negative_net_r = _as_float(scenario.get("sum_negative_net_r"))
    declared_pf = _as_float(scenario.get("profit_factor"))
    if loss_count is None or loss_count <= 0:
        return None, f"{label}.loss_count must be a positive integer"
    if positive_net_r is None or positive_net_r < 0:
        return None, f"{label}.sum_positive_net_r must be finite and >= 0"
    if negative_net_r is None or negative_net_r >= 0:
        return None, f"{label}.sum_negative_net_r must be finite and < 0"

    recomputed_pf = positive_net_r / abs(negative_net_r)
    if declared_pf is None or not math.isclose(
        declared_pf, recomputed_pf, rel_tol=0.0, abs_tol=1e-6
    ):
        return None, f"{label}.profit_factor does not match recomputed R profit factor"
    return {
        "profit_factor": recomputed_pf,
        "net_r": positive_net_r + negative_net_r,
        "loss_count": float(loss_count),
        "sum_positive_net_r": positive_net_r,
        "sum_negative_net_r": negative_net_r,
    }, ""


def _cost_profit_factor(payload: Dict[str, Any], label: str, multiplier: float) -> Optional[float]:
    scenario, _ = _validated_cost_scenario(payload, label, multiplier)
    return scenario["profit_factor"] if scenario else None


def _baseline_falsification_gates(
    trades: List[Trade],
    cost_payload: Dict[str, Any],
    economic_from: str,
    economic_to: str,
    contract: Dict[str, Any],
    artifact: str,
) -> Dict[str, Dict[str, Any]]:
    """Evaluate the frozen, outcome-facing TRAIN baseline gates only.

    This deliberately stays separate from promotion gates.  A PASS here means
    the one preregistered baseline survived its economic falsification screen;
    it does not authorize optimization, OOS, holdout, paper, or live trading.
    """
    gates: Dict[str, Dict[str, Any]] = {}
    start = _parse_manifest_date(economic_from)
    end = _parse_manifest_date(economic_to)
    required_contract = {
        "min_completed_trades",
        "min_direction_share",
        "max_year_trade_share",
        "require_positive_cost_expectancy",
        "require_all_calendar_years_positive",
    }
    if set(contract) != required_contract:
        reason = "baseline_acceptance_contract must contain exactly the five frozen fields"
        gates["economic_window_coverage"] = _gate(
            "BLOCKED", actual=contract, required=reason, artifact=artifact, reason=reason
        )
        return gates
    min_trades = _as_int(contract.get("min_completed_trades"))
    min_direction_share = _as_float(contract.get("min_direction_share"))
    max_year_share = _as_float(contract.get("max_year_trade_share"))
    require_positive = contract.get("require_positive_cost_expectancy") is True
    require_all_years = contract.get("require_all_calendar_years_positive") is True
    if (
        start is None
        or end is None
        or start > end
        or min_trades is None
        or min_trades <= 0
        or min_direction_share is None
        or not 0.0 <= min_direction_share <= 0.5
        or max_year_share is None
        or not 0.0 < max_year_share <= 1.0
        or not require_positive
        or not require_all_years
    ):
        reason = "baseline economic window or acceptance values are invalid/fail-open"
        gates["economic_window_coverage"] = _gate(
            "BLOCKED",
            actual={"from": economic_from, "to": economic_to, "contract": contract},
            required="valid inclusive economic window and strict enabled baseline gates",
            artifact=artifact,
            reason=reason,
        )
        return gates

    outside = [
        index
        for index, trade in enumerate(trades, start=1)
        if trade.entry_time.date() < start
        or trade.entry_time.date() > end
        or trade.exit_time.date() < start
        or trade.exit_time.date() > end
    ]
    artifact_window = cost_payload.get("economic_window")
    artifact_window_matches = (
        isinstance(artifact_window, dict)
        and str(artifact_window.get("from") or "") == economic_from
        and str(artifact_window.get("to") or "") == economic_to
        and str(artifact_window.get("boundary") or "") == "inclusive_calendar_dates"
    )
    coverage_actual = {
        "from": economic_from,
        "to": economic_to,
        "boundary": "inclusive_calendar_dates",
        "cost_artifact_economic_window": artifact_window,
        "cost_artifact_window_matches": artifact_window_matches,
        "completed_positions": len(trades),
        "outside_trade_indices": outside[:20],
        "first_entry_time": min((trade.entry_time.isoformat() for trade in trades), default=None),
        "last_exit_time": max((trade.exit_time.isoformat() for trade in trades), default=None),
    }
    coverage_passed = bool(trades) and not outside and artifact_window_matches
    gates["economic_window_coverage"] = _gate(
        "PASS" if coverage_passed else "FAIL",
        actual=coverage_actual,
        required="every completed position entry and exit is inside the frozen inclusive economic window",
        artifact=artifact,
        reason="" if coverage_passed else "Completed positions are absent or outside the economic window.",
    )

    gates["minimum_trades_baseline"] = _gate(
        "PASS" if len(trades) >= min_trades else "FAIL",
        actual=len(trades),
        required=f"completed positions >= {min_trades}",
        artifact=artifact,
        reason="" if len(trades) >= min_trades else "Baseline sample is below the preregistered floor.",
    )

    direction_counts = Counter(str(trade.side or "").strip().upper() for trade in trades)
    direction_shares = {
        direction: (direction_counts.get(direction, 0) / len(trades) if trades else 0.0)
        for direction in ("BUY", "SELL")
    }
    direction_passed = bool(trades) and all(
        share >= min_direction_share for share in direction_shares.values()
    ) and sum(direction_counts.get(direction, 0) for direction in ("BUY", "SELL")) == len(trades)
    gates["direction_balance_baseline"] = _gate(
        "PASS" if direction_passed else "FAIL",
        actual={"counts": dict(direction_counts), "shares": direction_shares},
        required=f"BUY and SELL shares are each >= {min_direction_share}",
        artifact=artifact,
        reason="" if direction_passed else "Direction mix is invalid or too concentrated.",
    )

    year_counts = Counter(trade.exit_time.year for trade in trades)
    max_actual_year_share = max(year_counts.values(), default=0) / len(trades) if trades else 0.0
    concentration_passed = bool(trades) and max_actual_year_share <= max_year_share
    gates["year_trade_concentration_baseline"] = _gate(
        "PASS" if concentration_passed else "FAIL",
        actual={"counts": dict(sorted(year_counts.items())), "max_year_share": max_actual_year_share},
        required=f"maximum exit-year trade share <= {max_year_share}",
        artifact=artifact,
        reason="" if concentration_passed else "Baseline events are overly concentrated in one year.",
    )

    repricing = cost_payload.get("trade_repricing")
    repricing_errors: List[str] = []
    values_by_year: Dict[int, List[float]] = {}
    if not isinstance(repricing, list) or len(repricing) != len(trades):
        repricing_errors.append("trade_repricing must match the completed-position count")
        repricing = []
    for index, row in enumerate(repricing, start=1):
        if not isinstance(row, dict):
            repricing_errors.append(f"trade_repricing row {index} is not an object")
            continue
        exit_raw = str(row.get("exit_time") or "").strip()
        try:
            exit_time = dt.datetime.strptime(exit_raw, "%Y.%m.%d %H:%M:%S")
        except ValueError:
            repricing_errors.append(f"trade_repricing row {index} has invalid exit_time")
            continue
        if exit_time.date() < start or exit_time.date() > end:
            repricing_errors.append(f"trade_repricing row {index} exits outside economic window")
            continue
        components = [
            _as_float(row.get("gross_r")),
            _as_float(row.get("swap_r")),
            _as_float(row.get("commission_r")),
            _as_float(row.get("slippage_r")),
        ]
        if any(value is None for value in components):
            repricing_errors.append(f"trade_repricing row {index} has invalid x1 components")
            continue
        gross_r, swap_r, commission_r, slippage_r = components
        values_by_year.setdefault(exit_time.year, []).append(
            float(gross_r) + float(swap_r) - float(commission_r) - float(slippage_r)
        )

    all_values = [value for values in values_by_year.values() for value in values]
    net_r_x1 = sum(all_values)
    expectancy_x1 = net_r_x1 / len(all_values) if all_values else None
    expectancy_passed = not repricing_errors and expectancy_x1 is not None and expectancy_x1 > 0.0
    gates["positive_cost_expectancy_baseline"] = _gate(
        "PASS" if expectancy_passed else ("BLOCKED" if repricing_errors else "FAIL"),
        actual={
            "net_r_x1": net_r_x1 if all_values else None,
            "expectancy_r_x1": expectancy_x1,
            "trade_count": len(all_values),
            "errors": repricing_errors,
        },
        required="strictly positive mean net R at verified/proxy x1 costs",
        artifact=artifact,
        reason="" if expectancy_passed else "; ".join(repricing_errors) or "Net x1 expectancy is not positive.",
    )

    expected_years = list(range(start.year, end.year + 1))
    year_net_r = {year: sum(values_by_year.get(year, [])) for year in expected_years}
    all_years_passed = (
        not repricing_errors
        and all(values_by_year.get(year) for year in expected_years)
        and all(year_net_r[year] > 0.0 for year in expected_years)
    )
    gates["all_calendar_years_positive_baseline"] = _gate(
        "PASS" if all_years_passed else ("BLOCKED" if repricing_errors else "FAIL"),
        actual={
            "net_r_x1_by_exit_year": year_net_r,
            "trade_count_by_exit_year": {
                year: len(values_by_year.get(year, [])) for year in expected_years
            },
            "errors": repricing_errors,
        },
        required="each calendar year in the economic window has >=1 exit and strictly positive x1 net R",
        artifact=artifact,
        reason="" if all_years_passed else "; ".join(repricing_errors) or "At least one calendar year is absent or nonpositive.",
    )
    return gates


_VERIFIED_COST_BUILDER_MODULE: Any = None
_VERIFIED_COST_BUILDER_SHA256: Optional[str] = None


def _load_verified_cost_builder() -> Tuple[Any, Path]:
    """Load the canonical producer without trusting artifact-declared code."""
    global _VERIFIED_COST_BUILDER_MODULE, _VERIFIED_COST_BUILDER_SHA256
    builder_path = ANALYSIS_DIR.parent / "tools" / "build_verified_cost_artifact.py"
    current_sha256 = _file_sha256(builder_path)
    if not current_sha256:
        raise RuntimeError("canonical verified-cost builder is missing")
    if (
        _VERIFIED_COST_BUILDER_MODULE is None
        or _VERIFIED_COST_BUILDER_SHA256 != current_sha256
    ):
        spec = importlib.util.spec_from_file_location(
            "_alphafactory_verified_cost_builder", builder_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load canonical verified-cost builder")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _VERIFIED_COST_BUILDER_MODULE = module
        _VERIFIED_COST_BUILDER_SHA256 = current_sha256
    return _VERIFIED_COST_BUILDER_MODULE, builder_path.resolve()


def _recomputed_cost_evidence(
    payload: Dict[str, Any],
    report_path: Path,
    expected_trade_count: Optional[int],
) -> Dict[str, Any]:
    """Rehash raw inputs and rebuild every economic row before promotion."""
    reasons: List[str] = []
    rebuilt: Dict[str, Any] = {}
    builder_path: Optional[Path] = None
    producer = payload.get("producer") if isinstance(payload.get("producer"), dict) else {}
    cost_source_raw = payload.get("cost_source_manifest")
    cost_source_path: Optional[Path] = None
    try:
        builder, builder_path = _load_verified_cost_builder()
        if not _same_resolved_path(producer.get("script"), builder_path):
            reasons.append("producer.script is not the canonical verified-cost builder")
        actual_builder_sha = _file_sha256(builder_path)
        if (
            not actual_builder_sha
            or not _is_sha256(producer.get("script_sha256"))
            or str(producer.get("script_sha256")).lower() != actual_builder_sha.lower()
        ):
            reasons.append("producer.script_sha256 does not match the canonical builder")

        cost_source_path = Path(str(cost_source_raw or "")).resolve()
        actual_cost_source_sha = _file_sha256(cost_source_path)
        declared_cost_source_sha = str(payload.get("cost_source_manifest_sha256") or "")
        if not actual_cost_source_sha:
            reasons.append("cost_source_manifest does not exist")
        elif (
            not _is_sha256(declared_cost_source_sha)
            or declared_cost_source_sha.lower() != actual_cost_source_sha.lower()
        ):
            reasons.append("cost_source_manifest_sha256 does not match raw manifest")
        else:
            economic_window = payload.get("economic_window")
            if isinstance(economic_window, dict):
                rebuilt = builder.build(
                    report_path,
                    cost_source_path,
                    economic_from=str(economic_window.get("from") or ""),
                    economic_to=str(economic_window.get("to") or ""),
                )
            else:
                rebuilt = builder.build(report_path, cost_source_path)
    except Exception as exc:
        reasons.append(f"canonical cost rebuild failed: {exc}")

    compared_fields = [
        "schema_version",
        "provenance_status",
        "stress_mode",
        "promotion_eligible",
        "report",
        "report_sha256",
        "run_id",
        "hypothesis_id",
        "run_identity_sha256",
        "cost_source_manifest",
        "cost_source_manifest_sha256",
        "lifecycle_evidence",
        "run_meta_evidence",
        "execution_provenance",
        "trade_repricing",
        "scenarios",
        "net_r_x1_5",
        "producer",
    ]
    for optional_field in ("tester_preload_window", "economic_window"):
        if optional_field in payload:
            compared_fields.append(optional_field)
    mismatched_fields: List[str] = []
    if rebuilt:
        for field in compared_fields:
            if json.dumps(payload.get(field), sort_keys=True, separators=(",", ":")) != json.dumps(
                rebuilt.get(field), sort_keys=True, separators=(",", ":")
            ):
                mismatched_fields.append(field)
        if mismatched_fields:
            reasons.append(
                "artifact fields do not match canonical raw-evidence rebuild: "
                + ", ".join(mismatched_fields)
            )
        trade_rows = rebuilt.get("trade_repricing")
        rebuilt_count = len(trade_rows) if isinstance(trade_rows, list) else None
        if expected_trade_count is None or expected_trade_count <= 0:
            reasons.append("fresh report-derived completed-position count is unavailable")
        elif rebuilt_count != expected_trade_count:
            reasons.append(
                "trade_repricing count does not match fresh report-derived completed-position count"
            )
    else:
        rebuilt_count = None

    return {
        "verified": not reasons,
        "reasons": reasons,
        "builder_path": str(builder_path) if builder_path else None,
        "cost_source_manifest": str(cost_source_path) if cost_source_path else None,
        "recomputed_trade_count": rebuilt_count,
        "mismatched_fields": mismatched_fields,
    }


def _cost_evidence_scope(
    payload: Dict[str, Any], *, allow_research_cost_proxy: bool
) -> Dict[str, Any]:
    """Classify the cost tier without allowing a proxy to inherit promotion rights."""
    evidence = (
        payload.get("execution_provenance")
        if isinstance(payload.get("execution_provenance"), dict)
        else {}
    )
    is_proxy = any(
        (
            payload.get("schema_version") == "research_execution_cost_proxy.v1",
            payload.get("provenance_status") == "VERIFIED_RESEARCH_PROXY",
            evidence.get("evidence_tier") == "RESEARCH_PROXY",
        )
    )
    if not is_proxy:
        return {
            "evidence_tier": "PROMOTION_GRADE",
            "research_falsification_eligible": True,
            "promotion_eligible": True,
        }
    if not allow_research_cost_proxy:
        raise ValueError("RESEARCH_PROXY cost evidence requires explicit opt-in")
    required = {
        "schema_version": "research_execution_cost_proxy.v1",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "stress_mode": "run_bound_research_cost_proxy_repricing",
        "promotion_eligible": False,
    }
    for field, expected in required.items():
        if payload.get(field) != expected:
            raise ValueError(f"RESEARCH_PROXY field {field} must equal {expected!r}")
    if evidence.get("evidence_tier") != "RESEARCH_PROXY" or evidence.get(
        "promotion_eligible"
    ) is not False:
        raise ValueError("RESEARCH_PROXY execution provenance must remain non-promotable")
    return {
        "evidence_tier": "RESEARCH_PROXY",
        "research_falsification_eligible": True,
        "promotion_eligible": False,
    }


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    if not _nonempty_string(value):
        return False
    text = str(value).strip()
    return len(text) == 64 and all(char in "0123456789abcdefABCDEF" for char in text)


def _file_sha256(path: Path) -> Optional[str]:
    try:
        if not path.is_file():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _directory_tree_sha256(path: Path) -> Optional[str]:
    try:
        root = path.resolve()
        if not root.is_dir():
            return None
        records: List[str] = []
        for child in sorted(
            (candidate for candidate in root.rglob("*") if candidate.is_file()),
            key=lambda candidate: str(candidate.resolve()).lower(),
        ):
            relative = child.resolve().relative_to(root).as_posix()
            digest = _file_sha256(child)
            if digest is None:
                return None
            records.append(f"{relative}\t{digest.upper()}")
        return _text_sha256("\n".join(records))
    except (OSError, RuntimeError, ValueError):
        return None


def _include_snapshot_binding(manifest: Dict[str, Any], manifest_path: Path) -> Dict[str, Any]:
    root = _resolve_evidence_path(manifest.get("snapshot_root"), manifest_path)
    include_rows = manifest.get("include_snapshots")
    errors: List[str] = []
    records: List[str] = []
    audited: List[Dict[str, Any]] = []
    if root is None or not root.is_dir():
        errors.append("snapshot_root is missing")
    if not isinstance(include_rows, list):
        errors.append("include_snapshots must be a list")
        include_rows = []
    for row in sorted(
        (item for item in include_rows if isinstance(item, dict)),
        key=lambda item: str(item.get("snapshot_path") or "").lower(),
    ):
        raw_path = row.get("snapshot_path")
        path = _resolve_evidence_path(raw_path, manifest_path)
        declared_sha = str(row.get("sha256") or "").strip()
        actual_sha = _file_sha256(path) if path is not None else None
        relative: Optional[str] = None
        if root is not None and path is not None:
            try:
                relative = path.resolve().relative_to(root.resolve()).as_posix()
            except (OSError, RuntimeError, ValueError):
                errors.append(f"include snapshot escapes snapshot_root: {raw_path}")
        if path is None or not path.is_file():
            errors.append(f"include snapshot is missing: {raw_path}")
        elif not _is_sha256(declared_sha) or not actual_sha or declared_sha.lower() != actual_sha.lower():
            errors.append(f"include snapshot SHA256 mismatch: {raw_path}")
        if relative is not None and actual_sha is not None:
            records.append(f"{relative}\t{actual_sha.upper()}")
        audited.append(
            {
                "path": str(path) if path is not None else None,
                "relative_path": relative,
                "declared_sha256": declared_sha or None,
                "actual_sha256": actual_sha,
            }
        )
    actual_set_sha = _text_sha256("\n".join(records)) if not errors else None
    declared_set_sha = str(manifest.get("includes_sha256") or "").strip()
    return {
        "snapshot_root": str(root) if root is not None else None,
        "include_count": len(include_rows),
        "includes": audited,
        "declared_sha256": declared_set_sha or None,
        "actual_sha256": actual_set_sha,
        "sha256_match": bool(
            actual_set_sha
            and _is_sha256(declared_set_sha)
            and declared_set_sha.lower() == actual_set_sha.lower()
        ),
        "errors": errors,
    }


def _run_identity_payload(manifest: Dict[str, Any], report_sha256: Optional[str]) -> Dict[str, Any]:
    """Return the immutable run identity; mutable attestations are intentionally excluded."""
    return {
        "run_id": str(manifest.get("run_id") or "").strip(),
        "hypothesis_id": str(manifest.get("hypothesis_id") or "").strip(),
        "run_role": str(manifest.get("run_role") or "").strip(),
        "ea_name": str(manifest.get("ea_name") or "").strip(),
        "report_sha256": str(report_sha256 or "").lower(),
        "source_sha256": str(
            _first_value(
                manifest,
                ("source_sha256", "main_file_sha256", "canonical_source_sha256"),
            )
            or ""
        ).lower(),
        "symbol": str(manifest.get("symbol") or "").strip(),
        "period": str(manifest.get("period") or manifest.get("timeframe") or "").strip(),
        "from": str(_first_value(manifest, ("from", "from_date", "FromDate")) or "").strip(),
        "to": str(_first_value(manifest, ("to", "to_date", "ToDate")) or "").strip(),
        "model": manifest.get("model"),
        "execution_lane": str(manifest.get("execution_lane") or "").strip(),
        "execution_mode": manifest.get("execution_mode"),
        "fixed_delay_ms": manifest.get("fixed_delay_ms"),
        "overrides": manifest.get("overrides"),
        "config_sha256": str(manifest.get("config_sha256") or "").lower(),
        "ex5_sha256": str(manifest.get("ex5_sha256") or "").lower(),
        "tester_ex5_sha256": str(manifest.get("tester_ex5_sha256") or "").lower(),
        "includes_sha256": str(manifest.get("includes_sha256") or "").lower(),
        "git_commit": str(manifest.get("git_commit") or "").strip(),
        "git_status_sha256": str(manifest.get("git_status_sha256") or "").lower(),
        "deposit": manifest.get("deposit"),
        "leverage": manifest.get("leverage"),
        "spread": manifest.get("spread"),
        "telemetry_tier": str(manifest.get("telemetry_tier") or "").strip(),
        "broker_fingerprint": str(manifest.get("broker_fingerprint") or "").lower(),
        "server_fingerprint": str(manifest.get("server_fingerprint") or "").lower(),
        "account_fingerprint": str(manifest.get("account_fingerprint") or "").lower(),
        "data_fingerprint": str(manifest.get("data_fingerprint") or "").lower(),
    }


def _run_identity_sha256(manifest: Dict[str, Any], report_sha256: Optional[str]) -> str:
    encoded = json.dumps(
        _run_identity_payload(manifest, report_sha256),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _run_manifest_file_bindings(
    manifest: Dict[str, Any],
    report_path: Path,
) -> Dict[str, Any]:
    manifest_path = report_path.parent / "run_manifest.json"
    actual_report_sha = _file_sha256(report_path)
    manifest_report_sha = str(manifest.get("report_sha256") or "").strip()
    source_raw = _first_value(
        manifest,
        ("source_snapshot", "source_path", "main_file"),
    )
    source_path = _resolve_evidence_path(source_raw, manifest_path)
    actual_source_sha = _file_sha256(source_path) if source_path is not None else None
    manifest_source_sha = str(
        _first_value(
            manifest,
            ("source_sha256", "main_file_sha256", "canonical_source_sha256"),
        )
        or ""
    ).strip()
    artifact_bindings: Dict[str, Dict[str, Any]] = {}
    for label, path_field, hash_field in (
        ("config", "config_snapshot", "config_sha256"),
        ("ex5", "ex5_snapshot", "ex5_sha256"),
        ("tester_ex5", "tester_ex5_path", "tester_ex5_sha256"),
    ):
        path = _resolve_evidence_path(manifest.get(path_field), manifest_path)
        actual_sha = _file_sha256(path) if path is not None else None
        declared_sha = str(manifest.get(hash_field) or "").strip()
        artifact_bindings[label] = {
            "path": str(path) if path is not None else None,
            "exists": bool(path is not None and path.is_file()),
            "declared_sha256": declared_sha or None,
            "actual_sha256": actual_sha,
            "sha256_match": bool(
                actual_sha
                and _is_sha256(declared_sha)
                and declared_sha.lower() == actual_sha.lower()
            ),
        }
    include_binding = _include_snapshot_binding(manifest, manifest_path)
    tester_actual = artifact_bindings["tester_ex5"].get("actual_sha256")
    ex5_actual = artifact_bindings["ex5"].get("actual_sha256")
    return {
        "report_path_match": _same_resolved_path(manifest.get("report_path"), report_path),
        "manifest_report_sha256": manifest_report_sha or None,
        "actual_report_sha256": actual_report_sha,
        "report_sha256_match": bool(
            actual_report_sha
            and _is_sha256(manifest_report_sha)
            and manifest_report_sha.lower() == actual_report_sha.lower()
        ),
        "source_path": str(source_path) if source_path is not None else None,
        "source_exists": bool(source_path is not None and source_path.is_file()),
        "manifest_source_sha256": manifest_source_sha or None,
        "actual_source_sha256": actual_source_sha,
        "source_sha256_match": bool(
            actual_source_sha
            and _is_sha256(manifest_source_sha)
            and manifest_source_sha.lower() == actual_source_sha.lower()
        ),
        "config": artifact_bindings["config"],
        "config_sha256_match": artifact_bindings["config"]["sha256_match"],
        "ex5": artifact_bindings["ex5"],
        "ex5_sha256_match": artifact_bindings["ex5"]["sha256_match"],
        "tester_ex5": artifact_bindings["tester_ex5"],
        "tester_ex5_sha256_match": artifact_bindings["tester_ex5"]["sha256_match"],
        "tester_ex5_matches_ex5": bool(
            tester_actual and ex5_actual and tester_actual.lower() == ex5_actual.lower()
        ),
        "include_snapshots": include_binding,
        "includes_sha256_match": include_binding["sha256_match"],
    }


def _nonrepaint_audit_evidence(
    payload: Dict[str, Any],
    artifact_path: Path,
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """Rehash and bind a non-repaint audit to the exact run snapshot set."""
    reasons: List[str] = []
    if payload.get("schema_version") != "alphafactory_nonrepaint_audit.v1":
        reasons.append("schema_version must equal alphafactory_nonrepaint_audit.v1")
    if payload.get("status") != "PASS":
        reasons.append("status must equal PASS")
    if payload.get("findings") not in ([], None):
        reasons.append("findings must be empty")
    for field in ("run_id", "hypothesis_id"):
        if str(payload.get(field) or "").strip() != str(manifest.get(field) or "").strip():
            reasons.append(f"{field} does not match run_manifest")

    expected: Dict[str, str] = {}
    source_path = _resolve_evidence_path(manifest.get("source_snapshot"), artifact_path)
    source_sha = str(manifest.get("source_sha256") or "").lower()
    if source_path is None or not source_path.is_file() or not _is_sha256(source_sha):
        reasons.append("run_manifest source snapshot/hash is incomplete")
    else:
        expected[str(source_path.resolve()).lower()] = source_sha
    include_rows = manifest.get("include_snapshots")
    if not isinstance(include_rows, list):
        reasons.append("run_manifest include_snapshots must be a list")
        include_rows = []
    for index, row in enumerate(include_rows):
        if not isinstance(row, dict):
            reasons.append(f"run_manifest include_snapshots[{index}] is not an object")
            continue
        include_path = _resolve_evidence_path(row.get("snapshot_path"), artifact_path)
        include_sha = str(row.get("sha256") or "").lower()
        if include_path is None or not include_path.is_file() or not _is_sha256(include_sha):
            reasons.append(f"run_manifest include_snapshots[{index}] path/hash is incomplete")
            continue
        expected[str(include_path.resolve()).lower()] = include_sha

    observed: Dict[str, str] = {}
    audited_files = payload.get("audited_files")
    if not isinstance(audited_files, list):
        reasons.append("audited_files must be a list")
        audited_files = []
    for index, row in enumerate(audited_files):
        if not isinstance(row, dict):
            reasons.append(f"audited_files[{index}] is not an object")
            continue
        audited_path = _resolve_evidence_path(row.get("path"), artifact_path)
        declared_sha = str(row.get("sha256") or "").lower()
        if audited_path is None or not audited_path.is_file() or not _is_sha256(declared_sha):
            reasons.append(f"audited_files[{index}] path/hash is incomplete")
            continue
        key = str(audited_path.resolve()).lower()
        if key in observed:
            reasons.append(f"audited_files contains duplicate path: {audited_path}")
            continue
        observed[key] = declared_sha
        actual_sha = _file_sha256(audited_path)
        if actual_sha is None or actual_sha.lower() != declared_sha:
            reasons.append(f"audited file SHA256 mismatch: {audited_path}")

    if set(observed) != set(expected):
        reasons.append("audited_files does not exactly equal the run source/include snapshot set")
    for path_key in sorted(set(observed) & set(expected)):
        if observed[path_key] != expected[path_key]:
            reasons.append(f"audited hash does not match run_manifest snapshot hash: {path_key}")
    return {
        "verified": not reasons,
        "reasons": reasons,
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "expected_file_count": len(expected),
        "audited_file_count": len(observed),
    }


def _resolve_evidence_path(raw_path: Any, artifact_path: Path) -> Optional[Path]:
    if not _nonempty_string(raw_path):
        return None
    try:
        path = Path(str(raw_path).strip())
        if not path.is_absolute():
            path = artifact_path.parent / path
        return path.resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def _verify_file_reference(
    node: Dict[str, Any],
    artifact_path: Path,
    prefix: str,
) -> Tuple[Dict[str, Any], List[str]]:
    source = node.get("source")
    declared_sha = str(node.get("sha256") or node.get("source_sha256") or "").strip()
    resolved = _resolve_evidence_path(source, artifact_path)
    actual_sha = _file_sha256(resolved) if resolved is not None else None
    reasons: List[str] = []
    if not _nonempty_string(source):
        reasons.append(f"{prefix}.source must be nonempty")
    elif resolved is None or not resolved.is_file():
        reasons.append(f"{prefix}.source does not exist")
    if not _is_sha256(declared_sha):
        reasons.append(f"{prefix}.sha256 must be a SHA256 hash")
    elif actual_sha is not None and declared_sha.lower() != actual_sha.lower():
        reasons.append(f"{prefix}.sha256 mismatch")
    return {
        "source": str(source or ""),
        "resolved_source": str(resolved) if resolved is not None else None,
        "declared_sha256": declared_sha or None,
        "actual_sha256": actual_sha,
        "exists": bool(resolved is not None and resolved.is_file()),
        "hash_match": bool(actual_sha and _is_sha256(declared_sha) and actual_sha.lower() == declared_sha.lower()),
    }, reasons


def _cost_provenance(
    payload: Dict[str, Any],
    report_path: Path,
    artifact_path: Path,
    manifest: Dict[str, Any],
    thresholds: Dict[str, float],
    expected_trade_count: Optional[int],
    allow_research_cost_proxy: bool = False,
) -> Dict[str, Any]:
    try:
        scope = _cost_evidence_scope(
            payload,
            allow_research_cost_proxy=allow_research_cost_proxy,
        )
    except ValueError as exc:
        return {
            "verified": False,
            "reasons": [str(exc)],
            "evidence_tier": "RESEARCH_PROXY",
            "research_falsification_eligible": False,
            "promotion_eligible": False,
        }
    if scope["evidence_tier"] == "RESEARCH_PROXY":
        recomputed = _recomputed_cost_evidence(payload, report_path, expected_trade_count)
        reasons = list(recomputed.get("reasons") or [])
        if not _same_resolved_path(payload.get("report"), report_path):
            reasons.append("research proxy report does not bind to the current report")
        return {
            "verified": not reasons,
            "reasons": reasons,
            **scope,
            "schema_version": payload.get("schema_version"),
            "provenance_status": payload.get("provenance_status"),
            "stress_mode": payload.get("stress_mode"),
            "report_match": not any("report" in reason for reason in reasons),
            "canonical_rebuild": recomputed,
            "methodology_description": (
                payload.get("execution_provenance", {})
                .get("cost_methodology", {})
                .get("description")
            ),
        }
    expected_schema = str(VERIFIED_COST_PROVENANCE_SCHEMA["schema_version"])
    schema_version = str(payload.get("schema_version") or "").strip()
    provenance_status = str(payload.get("provenance_status") or "").strip()
    stress_mode = str(payload.get("stress_mode") or "").strip()
    report_match = _same_resolved_path(payload.get("report"), report_path)
    evidence = (
        payload.get("execution_provenance")
        if isinstance(payload.get("execution_provenance"), dict)
        else {}
    )
    spread = (
        evidence.get("historical_spread")
        if isinstance(evidence.get("historical_spread"), dict)
        else {}
    )
    commission = (
        evidence.get("commission")
        if isinstance(evidence.get("commission"), dict)
        else {}
    )
    slippage = (
        evidence.get("slippage")
        if isinstance(evidence.get("slippage"), dict)
        else {}
    )
    methodology = (
        evidence.get("cost_methodology")
        if isinstance(evidence.get("cost_methodology"), dict)
        else {}
    )
    symbol_geometry = (
        evidence.get("symbol_geometry")
        if isinstance(evidence.get("symbol_geometry"), dict)
        else {}
    )

    commission_value = _as_float(commission.get("value"))
    commission_sample_count = _as_int(commission.get("sample_count"))
    slippage_sample_count = _as_int(slippage.get("sample_count"))
    slippage_buy_count = _as_int(slippage.get("buy_count"))
    slippage_sell_count = _as_int(slippage.get("sell_count"))
    slippage_p90_buy = _as_float(slippage.get("p90_buy"))
    slippage_p90_sell = _as_float(slippage.get("p90_sell"))
    slippage_p90_roundturn = _as_float(slippage.get("p90_roundturn"))
    declared_net_r_x1_5 = _as_float(payload.get("net_r_x1_5"))
    x1_5_scenario, _ = _validated_cost_scenario(payload, "cost_x1_50", 1.5)
    spread_reference, spread_reference_reasons = _verify_file_reference(
        spread,
        artifact_path,
        "execution_provenance.historical_spread",
    )
    commission_reference: Dict[str, Any] = {}
    commission_reference_reasons: List[str] = []
    slippage_reference, slippage_reference_reasons = _verify_file_reference(
        slippage,
        artifact_path,
        "execution_provenance.slippage",
    )

    coverage = spread.get("coverage") if isinstance(spread.get("coverage"), dict) else {}
    coverage_samples = _as_int(
        _first_value(coverage, ("sample_count", "nonzero_sample_count", "valid_sample_count"))
    )
    coverage_total = _as_int(_first_value(coverage, ("total_count", "bar_count", "total_bars")))
    coverage_ratio = _normalized_ratio(
        _first_value(coverage, ("coverage_ratio", "coverage_pct", "nonzero_coverage_pct"))
    )
    if coverage_ratio is None and coverage_samples is not None and coverage_total:
        coverage_ratio = coverage_samples / coverage_total

    manifest_basis = (
        manifest.get("fingerprint_basis")
        if isinstance(manifest.get("fingerprint_basis"), dict)
        else {}
    )
    manifest_digits = _as_int(manifest_basis.get("digits"))
    manifest_point = _as_float(manifest_basis.get("point"))
    manifest_pip_size = _as_float(manifest_basis.get("pip_size"))
    evidence_digits = _as_int(symbol_geometry.get("digits"))
    evidence_point = _as_float(symbol_geometry.get("point"))
    evidence_pip_size = _as_float(symbol_geometry.get("pip_size"))
    identity_fields = (
        "broker_fingerprint",
        "server_fingerprint",
        "account_fingerprint",
        "data_fingerprint",
    )
    identity_matches: Dict[str, bool] = {}
    manifest_from = _parse_manifest_date(_first_value(manifest, ("from", "from_date", "FromDate")))
    manifest_to = _parse_manifest_date(_first_value(manifest, ("to", "to_date", "ToDate")))
    evidence_from = _parse_manifest_date(_first_value(evidence, ("from", "from_date", "FromDate")))
    evidence_to = _parse_manifest_date(_first_value(evidence, ("to", "to_date", "ToDate")))
    spread_from = _parse_manifest_date(_first_value(coverage, ("from", "from_date", "FromDate")))
    spread_to = _parse_manifest_date(_first_value(coverage, ("to", "to_date", "ToDate")))

    declared_report_sha = str(payload.get("report_sha256") or "").strip()
    actual_report_sha = _file_sha256(report_path)
    declared_run_identity = str(payload.get("run_identity_sha256") or "").strip()
    actual_run_identity = _run_identity_sha256(manifest, actual_report_sha)
    run_file_bindings = _run_manifest_file_bindings(manifest, report_path)
    reasons: List[str] = []

    if provenance_status != "VERIFIED":
        reasons.append("provenance_status must equal VERIFIED")
    if schema_version != expected_schema:
        reasons.append(f"schema_version must equal {expected_schema}")
    if "report_only" in stress_mode.lower() or "proxy" in stress_mode.lower():
        reasons.append("report-only/proxy stress mode is diagnostic-only")
    if not report_match:
        reasons.append("artifact report does not bind to the current report")
    if not _is_sha256(declared_report_sha) or not actual_report_sha or declared_report_sha.lower() != actual_report_sha.lower():
        reasons.append("report_sha256 does not match current report")
    if not _is_sha256(declared_run_identity) or declared_run_identity.lower() != actual_run_identity.lower():
        reasons.append("run_identity_sha256 does not match canonical run identity")
    if not run_file_bindings["report_path_match"]:
        reasons.append("run_manifest.report_path does not match current report")
    if not run_file_bindings["report_sha256_match"]:
        reasons.append("run_manifest.report_sha256 does not match current report")
    if not run_file_bindings["source_exists"]:
        reasons.append("run manifest source evidence does not exist")
    elif not run_file_bindings["source_sha256_match"]:
        reasons.append("run_manifest.source_sha256 does not match source evidence")
    for binding_name in ("config", "ex5", "tester_ex5"):
        binding = run_file_bindings[binding_name]
        if not binding["exists"]:
            reasons.append(f"run manifest {binding_name} evidence does not exist")
        elif not binding["sha256_match"]:
            reasons.append(f"run_manifest {binding_name} SHA256 does not match evidence")
    if not run_file_bindings["tester_ex5_matches_ex5"]:
        reasons.append("executed tester EX5 does not match snapshotted EX5")
    if not run_file_bindings["includes_sha256_match"]:
        reasons.append("run_manifest.includes_sha256 does not match include snapshot closure")
    for field in ("broker", "server"):
        if not _nonempty_string(evidence.get(field)):
            reasons.append(f"execution_provenance.{field} must be nonempty")
    for field in identity_fields:
        evidence_value = str(evidence.get(field) or "").strip()
        manifest_value = str(manifest.get(field) or "").strip()
        if not _is_sha256(evidence_value):
            reasons.append(f"execution_provenance.{field} must be a SHA256 hash")
        if not _is_sha256(manifest_value):
            reasons.append(f"run_manifest.{field} must be a SHA256 hash")
        identity_matches[field] = bool(
            _is_sha256(evidence_value)
            and _is_sha256(manifest_value)
            and evidence_value.lower() == manifest_value.lower()
        )
        if not identity_matches[field]:
            reasons.append(f"{field} does not match run manifest")
    for label_field in ("broker", "server"):
        manifest_label = manifest_basis.get(label_field)
        if _nonempty_string(manifest_label) and evidence.get(label_field) != manifest_label:
            reasons.append(f"{label_field} does not match run manifest fingerprint_basis")

    geometry_values = (
        ("digits", evidence_digits, manifest_digits, lambda value: 0 <= value <= 15),
        ("point", evidence_point, manifest_point, lambda value: value > 0),
        ("pip_size", evidence_pip_size, manifest_pip_size, lambda value: value > 0),
    )
    for field, evidence_value, manifest_value, valid in geometry_values:
        if manifest_value is None or not valid(manifest_value):
            reasons.append(
                f"run_manifest.fingerprint_basis.{field} must be finite and valid"
            )
        if evidence_value is None or not valid(evidence_value):
            reasons.append(
                f"execution_provenance.symbol_geometry.{field} must be finite and valid"
            )
        if (
            manifest_value is not None
            and evidence_value is not None
            and valid(manifest_value)
            and valid(evidence_value)
            and evidence_value != manifest_value
        ):
            reasons.append(
                f"execution_provenance.symbol_geometry.{field} does not match "
                f"run_manifest.fingerprint_basis.{field}"
            )

    evidence_symbol = str(evidence.get("symbol") or "").strip()
    manifest_symbol = str(manifest.get("symbol") or "").strip()
    if not evidence_symbol:
        reasons.append("execution_provenance.symbol must be nonempty")
    if not manifest_symbol or evidence_symbol != manifest_symbol:
        reasons.append("symbol does not match run manifest")
    if not manifest_from or not evidence_from or evidence_from != manifest_from:
        reasons.append("from does not match run manifest")
    if not manifest_to or not evidence_to or evidence_to != manifest_to:
        reasons.append("to does not match run manifest")

    reasons.extend(spread_reference_reasons)
    reasons.extend(slippage_reference_reasons)
    if str(spread.get("verification_status") or "") != "VERIFIED":
        reasons.append("execution_provenance.historical_spread.verification_status must equal VERIFIED")
    if str(spread.get("symbol") or "").strip() != manifest_symbol:
        reasons.append("execution_provenance.historical_spread.symbol does not match run manifest")
    if not manifest_from or not spread_from or spread_from != manifest_from:
        reasons.append("execution_provenance.historical_spread.coverage.from does not match run manifest")
    if not manifest_to or not spread_to or spread_to != manifest_to:
        reasons.append("execution_provenance.historical_spread.coverage.to does not match run manifest")
    if coverage_samples is None or coverage_samples <= 0:
        reasons.append("execution_provenance.historical_spread.coverage.sample_count must be positive")
    if coverage_total is None or coverage_total <= 0:
        reasons.append("execution_provenance.historical_spread.coverage.total_count must be positive")
    if coverage_samples is not None and coverage_total is not None and coverage_samples > coverage_total:
        reasons.append("execution_provenance.historical_spread.coverage.sample_count cannot exceed total_count")
    min_spread_coverage = thresholds["min_spread_coverage_ratio"]
    if coverage_ratio is None or not min_spread_coverage <= coverage_ratio <= 1.0:
        reasons.append(
            "execution_provenance.historical_spread.coverage.coverage_ratio "
            f"must be between {min_spread_coverage} and 1.0"
        )
    if coverage_samples is not None and coverage_total and coverage_ratio is not None:
        computed_coverage = coverage_samples / coverage_total
        if abs(coverage_ratio - computed_coverage) > 0.000001:
            reasons.append(
                "execution_provenance.historical_spread.coverage.coverage_ratio "
                "does not match sample_count divided by total_count"
            )

    if str(commission.get("verification_status") or "") != "VERIFIED":
        reasons.append("execution_provenance.commission.verification_status must equal VERIFIED")
    if commission_value is None or commission_value < 0:
        reasons.append("execution_provenance.commission.value must be finite and >= 0")
    min_commission_samples = int(thresholds["min_commission_samples"])
    commission_contract_supplied = "broker_contract" in commission
    commission_contract_raw = commission.get("broker_contract")
    commission_contract = (
        commission_contract_raw if isinstance(commission_contract_raw, dict) else {}
    )
    contract_reference: Dict[str, Any] = {}
    contract_reasons: List[str] = []
    contract_verified = False
    empirical_commission_valid = False
    empirical_declared = bool(
        _nonempty_string(commission.get("source"))
        or _nonempty_string(commission.get("sha256"))
        or commission_sample_count is not None
    )
    if empirical_declared:
        commission_reference, commission_reference_reasons = _verify_file_reference(
            commission,
            artifact_path,
            "execution_provenance.commission",
        )
        commission_symbol_match = str(commission.get("symbol") or "").strip() == manifest_symbol
        commission_same_symbol = commission.get("same_symbol_lifecycles") is True
        empirical_commission_valid = bool(
            not commission_reference_reasons
            and commission_sample_count is not None
            and commission_sample_count >= min_commission_samples
            and commission_symbol_match
            and commission_same_symbol
            and _nonempty_string(commission.get("method"))
        )
        if not empirical_commission_valid and not commission_contract:
            reasons.extend(commission_reference_reasons)
            if commission_sample_count is None or commission_sample_count < min_commission_samples:
                reasons.append(
                    "execution_provenance.commission.sample_count must be >= "
                    f"{min_commission_samples}"
                )
            if not commission_symbol_match:
                reasons.append("execution_provenance.commission.symbol does not match run manifest")
            if not commission_same_symbol:
                reasons.append("execution_provenance.commission.same_symbol_lifecycles must be true")
            if not _nonempty_string(commission.get("method")):
                reasons.append("execution_provenance.commission.method must be nonempty")
    if commission_contract_supplied and not commission_contract:
        reasons.append(
            "execution_provenance.commission.broker_contract must be a nonempty object"
        )
    if commission_contract:
        contract_reference, contract_reasons = _verify_file_reference(
            commission_contract,
            artifact_path,
            "execution_provenance.commission.broker_contract",
        )
        contract_broker_match = bool(
            _is_sha256(commission_contract.get("broker_fingerprint"))
            and str(commission_contract.get("broker_fingerprint")).lower()
            == str(manifest.get("broker_fingerprint") or "").lower()
        )
        contract_server_match = bool(
            _is_sha256(commission_contract.get("server_fingerprint"))
            and str(commission_contract.get("server_fingerprint")).lower()
            == str(manifest.get("server_fingerprint") or "").lower()
        )
        contract_account_match = bool(
            _is_sha256(commission_contract.get("account_fingerprint"))
            and str(commission_contract.get("account_fingerprint")).lower()
            == str(manifest.get("account_fingerprint") or "").lower()
        )
        contract_symbol_match = str(commission_contract.get("symbol") or "").strip() == manifest_symbol
        manifest_currency = str(manifest_basis.get("currency") or "").strip()
        contract_currency_match = bool(
            manifest_currency
            and str(commission_contract.get("account_currency") or "").strip()
            == manifest_currency
        )
        contract_per_lot_basis = commission_contract.get("per_lot_basis") is True
        contract_from = _parse_manifest_date(
            _first_value(commission_contract, ("from", "from_date", "FromDate"))
        )
        contract_to = _parse_manifest_date(
            _first_value(commission_contract, ("to", "to_date", "ToDate"))
        )
        contract_from_match = bool(manifest_from and contract_from == manifest_from)
        contract_to_match = bool(manifest_to and contract_to == manifest_to)
        contract_conversion_match = (
            str(commission_contract.get("conversion_method") or "")
            == "per_trade_contemporaneous"
        )
        contract_round_turn_per_lot = _as_float(
            commission_contract.get("round_turn_account_per_lot")
        )
        contract_round_turn_positive = bool(
            contract_round_turn_per_lot is not None and contract_round_turn_per_lot > 0
        )
        contract_round_turn_matches_value = bool(
            contract_round_turn_positive
            and commission_value is not None
            and contract_round_turn_per_lot == commission_value
        )
        contract_description_present = _nonempty_string(commission_contract.get("description"))
        contract_verified = bool(
            not contract_reasons
            and contract_broker_match
            and contract_server_match
            and contract_account_match
            and contract_symbol_match
            and contract_currency_match
            and contract_per_lot_basis
            and contract_from_match
            and contract_to_match
            and contract_conversion_match
            and contract_round_turn_positive
            and contract_round_turn_matches_value
            and contract_description_present
        )
        if not contract_verified:
            reasons.extend(contract_reasons)
            if not contract_broker_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.broker_fingerprint "
                    "does not match run manifest"
                )
            if not contract_symbol_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.symbol does not match run manifest"
                )
            if not contract_server_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.server_fingerprint "
                    "does not match run manifest"
                )
            if not contract_account_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.account_fingerprint "
                    "does not match run manifest"
                )
            if not contract_currency_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.account_currency "
                    "does not match run manifest fingerprint_basis"
                )
            if not contract_per_lot_basis:
                reasons.append(
                    "execution_provenance.commission.broker_contract.per_lot_basis must be true"
                )
            if not contract_from_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.from does not match run manifest"
                )
            if not contract_to_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.to does not match run manifest"
                )
            if not contract_conversion_match:
                reasons.append(
                    "execution_provenance.commission.broker_contract.conversion_method "
                    "must equal per_trade_contemporaneous"
                )
            if not contract_round_turn_positive:
                reasons.append(
                    "execution_provenance.commission.broker_contract."
                    "round_turn_account_per_lot must be finite and > 0"
                )
            elif not contract_round_turn_matches_value:
                reasons.append(
                    "execution_provenance.commission.broker_contract."
                    "round_turn_account_per_lot must equal commission.value"
                )
            if not contract_description_present:
                reasons.append(
                    "execution_provenance.commission.broker_contract.description must be nonempty"
                )
    if not empirical_commission_valid and not contract_verified:
        reasons.append(
            "execution_provenance.commission requires >= "
            f"{min_commission_samples} same-symbol lifecycles or a hash-verified broker contract"
        )

    if str(slippage.get("verification_status") or "") != "VERIFIED":
        reasons.append("execution_provenance.slippage.verification_status must equal VERIFIED")
    if str(slippage.get("symbol") or "").strip() != manifest_symbol:
        reasons.append("execution_provenance.slippage.symbol does not match run manifest")
    min_slippage_samples = int(thresholds["min_slippage_samples"])
    if slippage_sample_count is None or slippage_sample_count < min_slippage_samples:
        reasons.append(
            "execution_provenance.slippage.sample_count must be >= "
            f"{min_slippage_samples}"
        )
    if slippage_buy_count is None or slippage_buy_count < 30:
        reasons.append("execution_provenance.slippage.buy_count must be >= 30")
    if slippage_sell_count is None or slippage_sell_count < 30:
        reasons.append("execution_provenance.slippage.sell_count must be >= 30")
    if (
        slippage_sample_count is not None
        and slippage_buy_count is not None
        and slippage_sell_count is not None
        and slippage_sample_count != slippage_buy_count + slippage_sell_count
    ):
        reasons.append(
            "execution_provenance.slippage.sample_count must equal buy_count + sell_count"
        )
    if slippage_p90_buy is None or slippage_p90_buy < 0:
        reasons.append("execution_provenance.slippage.p90_buy must be finite and >= 0")
    if slippage_p90_sell is None or slippage_p90_sell < 0:
        reasons.append("execution_provenance.slippage.p90_sell must be finite and >= 0")
    if slippage_p90_roundturn is None or slippage_p90_roundturn < 0:
        reasons.append("execution_provenance.slippage.p90_roundturn must be finite and >= 0")
    elif (
        slippage_p90_buy is not None
        and slippage_p90_sell is not None
        and abs(slippage_p90_roundturn - (slippage_p90_buy + slippage_p90_sell)) > 1e-9
    ):
        reasons.append(
            "execution_provenance.slippage.p90_roundturn must equal p90_buy + p90_sell"
        )
    if str(slippage.get("buy_reference_side") or "") != "ask":
        reasons.append("execution_provenance.slippage.buy_reference_side must equal ask")
    if str(slippage.get("sell_reference_side") or "") != "bid":
        reasons.append("execution_provenance.slippage.sell_reference_side must equal bid")
    if str(slippage.get("slippage_unit") or "") != "pips":
        reasons.append("execution_provenance.slippage.slippage_unit must equal pips")
    if not _nonempty_string(slippage.get("method")):
        reasons.append("execution_provenance.slippage.method must be nonempty")
    if slippage.get("independent_reference") is not True:
        reasons.append("execution_provenance.slippage.independent_reference must be true")
    if str(methodology.get("verification_status") or "") != "VERIFIED":
        reasons.append("execution_provenance.cost_methodology.verification_status must equal VERIFIED")
    if methodology.get("direction_aware") is not True:
        reasons.append("execution_provenance.cost_methodology.direction_aware must be true")
    if not _nonempty_string(methodology.get("description")):
        reasons.append("execution_provenance.cost_methodology.description must be nonempty")
    if not _nonempty_string(methodology.get("long_cost_treatment")):
        reasons.append("execution_provenance.cost_methodology.long_cost_treatment must be nonempty")
    if not _nonempty_string(methodology.get("short_cost_treatment")):
        reasons.append("execution_provenance.cost_methodology.short_cost_treatment must be nonempty")
    if (
        _nonempty_string(methodology.get("long_cost_treatment"))
        and _nonempty_string(methodology.get("short_cost_treatment"))
        and methodology.get("long_cost_treatment") == methodology.get("short_cost_treatment")
    ):
        reasons.append("execution_provenance.cost_methodology long and short treatments must differ")
    if declared_net_r_x1_5 is None or declared_net_r_x1_5 <= 0:
        reasons.append("net_r_x1_5 must be finite and > 0")
    elif x1_5_scenario is not None and not math.isclose(
        declared_net_r_x1_5,
        x1_5_scenario["net_r"],
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        reasons.append("net_r_x1_5 does not match recomputed cost_x1_50 net R")

    recomputed_evidence = _recomputed_cost_evidence(
        payload,
        report_path,
        expected_trade_count,
    )
    reasons.extend(recomputed_evidence["reasons"])

    return {
        "verified": not reasons,
        "reasons": reasons,
        **scope,
        "schema_version": schema_version or None,
        "provenance_status": provenance_status or None,
        "stress_mode": stress_mode or None,
        "report_match": report_match,
        "report_sha256_match": bool(actual_report_sha and _is_sha256(declared_report_sha) and declared_report_sha.lower() == actual_report_sha.lower()),
        "declared_run_identity_sha256": declared_run_identity or None,
        "current_run_identity_sha256": actual_run_identity,
        "run_identity_fields": _run_identity_payload(manifest, actual_report_sha),
        "run_identity_sha256_match": bool(_is_sha256(declared_run_identity) and declared_run_identity.lower() == actual_run_identity.lower()),
        "run_manifest_file_bindings": run_file_bindings,
        "broker": evidence.get("broker"),
        "server": evidence.get("server"),
        "identity_matches": identity_matches,
        "symbol": evidence_symbol or None,
        "symbol_geometry": {
            "digits": evidence_digits,
            "point": evidence_point,
            "pip_size": evidence_pip_size,
            "manifest_digits": manifest_digits,
            "manifest_point": manifest_point,
            "manifest_pip_size": manifest_pip_size,
        },
        "from": evidence_from.isoformat() if evidence_from else None,
        "to": evidence_to.isoformat() if evidence_to else None,
        "historical_spread_reference": spread_reference,
        "historical_spread_coverage": {
            "sample_count": coverage_samples,
            "total_count": coverage_total,
            "coverage_ratio": coverage_ratio,
        },
        "commission_reference": commission_reference,
        "commission_value": commission_value,
        "commission_sample_count": commission_sample_count,
        "commission_contract_reference": contract_reference,
        "commission_contract_round_turn_account_per_lot": (
            _as_float(commission_contract.get("round_turn_account_per_lot"))
            if commission_contract
            else None
        ),
        "slippage_reference": slippage_reference,
        "slippage_sample_count": slippage_sample_count,
        "slippage_buy_count": slippage_buy_count,
        "slippage_sell_count": slippage_sell_count,
        "slippage_p90_buy": slippage_p90_buy,
        "slippage_p90_sell": slippage_p90_sell,
        "slippage_p90_roundturn": slippage_p90_roundturn,
        "slippage_unit": slippage.get("slippage_unit"),
        "net_r_x1_5": declared_net_r_x1_5,
        "direction_aware": methodology.get("direction_aware") is True,
        "methodology_description": methodology.get("description"),
        "canonical_rebuild": recomputed_evidence,
    }


def _verified_cost_gate(
    value: Optional[float],
    minimum: float,
    artifact: Path,
    provenance: Dict[str, Any],
    missing_reason: str,
    *,
    strict_minimum: bool = False,
) -> Dict[str, Any]:
    actual = {
        "profit_factor": value,
        "provenance": provenance,
    }
    comparison = ">" if strict_minimum else ">="
    required = f"verified execution provenance and profit_factor {comparison} {minimum}"
    if value is None:
        return _gate(
            "BLOCKED",
            actual=actual,
            required=required,
            artifact=str(artifact),
            reason=missing_reason,
        )
    if provenance.get("verified") is not True:
        reasons = provenance.get("reasons") or ["unverified cost evidence"]
        return _gate(
            "BLOCKED",
            actual=actual,
            required=required,
            artifact=str(artifact),
            reason="Cost provenance is not VERIFIED: " + "; ".join(str(item) for item in reasons),
        )
    passed = value > minimum if strict_minimum else value >= minimum
    return _gate(
        "PASS" if passed else "FAIL",
        actual=actual,
        required=required,
        artifact=str(artifact),
        reason=(
            ""
            if passed
            else f"Observed profit factor {value} does not satisfy {comparison} {minimum}."
        ),
    )


def _normalized_ratio(value: Any) -> Optional[float]:
    ratio = _as_float(value)
    if ratio is None:
        return None
    if ratio > 1.0:
        ratio /= 100.0
    return ratio if 0.0 <= ratio <= 1.0 else None


def _artifact_fingerprint(path: Path) -> Dict[str, Any]:
    fingerprint: Dict[str, Any] = {
        "path": str(path),
        "exists": False,
        "size": None,
        "mtime_ns": None,
        "sha256": None,
    }
    try:
        if not path.exists() or not path.is_file():
            return fingerprint
        stat = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        fingerprint.update(
            {
                "exists": True,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": digest.hexdigest(),
            }
        )
    except OSError as exc:
        fingerprint["error"] = str(exc)
    return fingerprint


def _invocation_owned_artifacts(
    out_path: Path,
    *,
    stage: str,
    variants_dir: str,
) -> Dict[str, Path]:
    artifacts = {
        "enhanced_summary": out_path / "enhanced_summary.json",
        "equity_audit": out_path / "equity_audit.json",
        "monte_carlo": out_path / "monte_carlo_results.json",
        "walk_forward": out_path / "wfa_results.json",
        "robustness": out_path / "robustness_results.json",
        "execution": out_path / "slippage_summary.json",
        "monthly_fitness": out_path / "monthly_fitness.json",
        "overnight_exposure": out_path / "overnight_exposure.json",
    }
    if str(stage).strip().lower() == "confirmed":
        artifacts.update(
            {
                "pbo": out_path / "cscv_pbo.json",
                "white_reality_check": out_path / "white_reality_check.json",
            }
        )
    return artifacts


def _snapshot_artifacts(paths: Dict[str, Path]) -> Dict[str, Dict[str, Any]]:
    return {name: _artifact_fingerprint(path) for name, path in paths.items()}


ARTIFACT_PRODUCERS: Dict[str, str] = {
    "enhanced_summary": "enhanced_analysis",
    "equity_audit": "equity_curve_audit",
    "monte_carlo": "monte_carlo",
    "walk_forward": "walk_forward",
    "robustness": "robustness_suite",
    "execution": "slippage_summary",
    "monthly_fitness": "monthly_fitness",
    "overnight_exposure": "overnight_exposure",
    "pbo": "cscv_pbo",
    "white_reality_check": "white_reality_check",
}


def _invocation_succeeded(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    status_ok = str(result.get("status") or "").upper() == "OK"
    returncode = result.get("returncode")
    return status_ok and (returncode is None or returncode == 0)


def _compare_artifact_snapshots(
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
    producer_results: Optional[Dict[str, Any]] = None,
    producer_by_artifact: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    created: List[str] = []
    rewritten: List[str] = []
    content_changed: List[str] = []
    identical_rewrite: List[str] = []
    unchanged: List[str] = []
    missing: List[str] = []
    failed_producer: List[str] = []
    fresh: List[str] = []
    not_fresh: List[str] = []
    audit: Dict[str, Any] = {}
    producers = producer_by_artifact or ARTIFACT_PRODUCERS
    outcomes = producer_results or {}

    for name in sorted(set(before) | set(after)):
        previous = before.get(name) or {}
        current = after.get(name) or {}
        previous_exists = previous.get("exists") is True
        current_exists = current.get("exists") is True
        previous_mtime_raw = previous.get("mtime_ns")
        current_mtime_raw = current.get("mtime_ns")
        previous_mtime = previous_mtime_raw if isinstance(previous_mtime_raw, int) else None
        current_mtime = current_mtime_raw if isinstance(current_mtime_raw, int) else None
        sha_changed = (
            previous_exists
            and current_exists
            and previous.get("sha256") != current.get("sha256")
        )
        mtime_changed = bool(
            previous_mtime is not None
            and current_mtime is not None
            and current_mtime != previous_mtime
        )
        producer = producers.get(name)
        producer_result = outcomes.get(producer) if producer else None
        producer_success = bool(producer and _invocation_succeeded(producer_result))

        if not current_exists:
            state = "missing"
            missing.append(name)
        elif not previous_exists:
            state = "created"
            created.append(name)
        elif sha_changed:
            state = "content_changed"
            rewritten.append(name)
            content_changed.append(name)
        elif mtime_changed:
            state = "identical_rewrite"
            rewritten.append(name)
            identical_rewrite.append(name)
        else:
            state = "unchanged"
            unchanged.append(name)

        fingerprint_delta = state in {"created", "content_changed"}
        is_fresh = bool(current_exists and fingerprint_delta and producer_success)
        if not producer_success:
            failed_producer.append(name)
        if is_fresh:
            fresh.append(name)
        else:
            not_fresh.append(name)

        audit[name] = {
            "state": state,
            "sha256_changed": sha_changed,
            "fingerprint_delta": fingerprint_delta,
            "producer": producer,
            "producer_success": producer_success,
            "producer_result": producer_result,
            "fresh": is_fresh,
            "before": previous,
            "after": current,
        }

    return {
        "created": created,
        "rewritten": rewritten,
        "content_changed": content_changed,
        "identical_rewrite": identical_rewrite,
        "unchanged": unchanged,
        "missing": missing,
        "failed_producer": sorted(set(failed_producer)),
        "fresh": fresh,
        "not_fresh": not_fresh,
        "artifacts": audit,
    }


def _wfa_binding(
    payload: Dict[str, Any],
    report_path: Path,
    manifest: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    artifact_report = payload.get("report")
    artifact_run_id = str(payload.get("run_id") or "").strip()
    artifact_hypothesis_id = str(payload.get("hypothesis_id") or "").strip()
    artifact_report_sha = str(payload.get("report_sha256") or "").strip()
    artifact_run_identity = str(payload.get("run_identity_sha256") or "").strip()
    artifact_source_sha = str(payload.get("source_sha256") or "").strip()
    manifest_run_id = str(manifest.get("run_id") or "").strip()
    manifest_hypothesis_id = str(manifest.get("hypothesis_id") or "").strip()
    manifest_source_sha = str(
        _first_value(
            manifest,
            ("source_sha256", "main_file_sha256", "canonical_source_sha256"),
        )
        or ""
    ).strip()
    actual_report_sha = _file_sha256(report_path)
    actual_run_identity = _run_identity_sha256(manifest, actual_report_sha)
    run_file_bindings = _run_manifest_file_bindings(manifest, report_path)

    report_match = _same_resolved_path(artifact_report, report_path)
    report_sha256_match = bool(
        actual_report_sha
        and _is_sha256(artifact_report_sha)
        and artifact_report_sha.lower() == actual_report_sha.lower()
    )
    run_id_match = bool(
        artifact_run_id and manifest_run_id and artifact_run_id == manifest_run_id
    )
    hypothesis_id_match = bool(
        artifact_hypothesis_id
        and manifest_hypothesis_id
        and artifact_hypothesis_id == manifest_hypothesis_id
    )
    run_identity_sha256_match = bool(
        _is_sha256(artifact_run_identity)
        and artifact_run_identity.lower() == actual_run_identity.lower()
    )
    source_sha256_match = bool(
        _is_sha256(artifact_source_sha)
        and _is_sha256(manifest_source_sha)
        and artifact_source_sha.lower() == manifest_source_sha.lower()
    )
    binding = {
        "artifact_report": str(artifact_report or ""),
        "current_report": str(report_path),
        "report_match": report_match,
        "artifact_report_sha256": artifact_report_sha,
        "current_report_sha256": actual_report_sha,
        "report_sha256_match": report_sha256_match,
        "artifact_run_id": artifact_run_id,
        "manifest_run_id": manifest_run_id,
        "run_id_match": run_id_match,
        "artifact_hypothesis_id": artifact_hypothesis_id,
        "manifest_hypothesis_id": manifest_hypothesis_id,
        "hypothesis_id_match": hypothesis_id_match,
        "artifact_run_identity_sha256": artifact_run_identity,
        "current_run_identity_sha256": actual_run_identity,
        "run_identity_fields": _run_identity_payload(manifest, actual_report_sha),
        "run_identity_sha256_match": run_identity_sha256_match,
        "artifact_source_sha256": artifact_source_sha,
        "manifest_source_sha256": manifest_source_sha,
        "source_sha256_match": source_sha256_match,
        "run_manifest_file_bindings": run_file_bindings,
    }
    return all(
        (
            report_match,
            report_sha256_match,
            run_id_match,
            hypothesis_id_match,
            run_identity_sha256_match,
            source_sha256_match,
            run_file_bindings["report_path_match"],
            run_file_bindings["report_sha256_match"],
            run_file_bindings["source_exists"],
            run_file_bindings["source_sha256_match"],
            run_file_bindings["config_sha256_match"],
            run_file_bindings["ex5_sha256_match"],
            run_file_bindings["tester_ex5_sha256_match"],
            run_file_bindings["tester_ex5_matches_ex5"],
            run_file_bindings["includes_sha256_match"],
        )
    ), binding


def _variant_artifact_binding(
    payload: Dict[str, Any],
    *,
    expected_schema: str,
    variants_dir: Path,
    report_path: Path,
    manifest: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    variant_manifest_path = variants_dir / "variant_manifest.json"
    current_variant_manifest_sha = _file_sha256(variant_manifest_path)
    declared_variant_manifest_sha = str(payload.get("variant_manifest_sha256") or "").strip()
    actual_variants_sha = _directory_tree_sha256(variants_dir)
    declared_variants_sha = str(payload.get("variants_sha256") or "").strip()
    actual_report_sha = _file_sha256(report_path)
    declared_report_sha = str(payload.get("report_sha256") or "").strip()
    actual_run_identity = _run_identity_sha256(manifest, actual_report_sha)
    declared_run_identity = str(payload.get("run_identity_sha256") or "").strip()
    artifact_run_id = str(payload.get("run_id") or "").strip()
    artifact_hypothesis_id = str(payload.get("hypothesis_id") or "").strip()
    manifest_run_id = str(manifest.get("run_id") or "").strip()
    manifest_hypothesis_id = str(manifest.get("hypothesis_id") or "").strip()
    artifact_source_sha = str(payload.get("source_sha256") or "").strip()
    manifest_source_sha = str(
        _first_value(manifest, ("source_sha256", "main_file_sha256", "canonical_source_sha256")) or ""
    ).strip()
    binding = {
        "schema_version": payload.get("schema_version"),
        "schema_match": payload.get("schema_version") == expected_schema,
        "artifact_variants_dir": str(payload.get("variants_dir") or ""),
        "current_variants_dir": str(variants_dir),
        "variants_dir_match": _same_resolved_path(payload.get("variants_dir"), variants_dir),
        "declared_variants_sha256": declared_variants_sha or None,
        "current_variants_sha256": actual_variants_sha,
        "variants_sha256_match": bool(
            actual_variants_sha
            and _is_sha256(declared_variants_sha)
            and declared_variants_sha.lower() == actual_variants_sha.lower()
        ),
        "variant_manifest_match": _same_resolved_path(
            payload.get("variant_manifest"), variant_manifest_path
        ),
        "variant_manifest_sha256_match": bool(
            current_variant_manifest_sha
            and _is_sha256(declared_variant_manifest_sha)
            and declared_variant_manifest_sha.lower() == current_variant_manifest_sha.lower()
        ),
        "report_match": _same_resolved_path(payload.get("report"), report_path),
        "report_sha256_match": bool(
            actual_report_sha
            and _is_sha256(declared_report_sha)
            and declared_report_sha.lower() == actual_report_sha.lower()
        ),
        "run_id_match": bool(
            artifact_run_id and manifest_run_id and artifact_run_id == manifest_run_id
        ),
        "hypothesis_id_match": bool(
            artifact_hypothesis_id
            and manifest_hypothesis_id
            and artifact_hypothesis_id == manifest_hypothesis_id
        ),
        "source_sha256_match": bool(
            _is_sha256(artifact_source_sha)
            and _is_sha256(manifest_source_sha)
            and artifact_source_sha.lower() == manifest_source_sha.lower()
        ),
        "run_identity_sha256_match": bool(
            _is_sha256(declared_run_identity)
            and declared_run_identity.lower() == actual_run_identity.lower()
        ),
    }
    return all(
        (
            binding["schema_match"],
            binding["variants_dir_match"],
            binding["variants_sha256_match"],
            binding["variant_manifest_match"],
            binding["variant_manifest_sha256_match"],
            binding["report_match"],
            binding["report_sha256_match"],
            binding["run_id_match"],
            binding["hypothesis_id_match"],
            binding["source_sha256_match"],
            binding["run_identity_sha256_match"],
        )
    ), binding


def _bind_variant_artifact(
    artifact_path: Path,
    *,
    schema_version: str,
    variants_dir: Path,
    report_path: Path,
    manifest: Dict[str, Any],
) -> None:
    payload = _load_json(artifact_path)
    if not payload:
        raise ValueError(f"Variant artifact is missing or unreadable: {artifact_path}")
    report_sha = _file_sha256(report_path)
    variants_sha = _directory_tree_sha256(variants_dir)
    if not report_sha or not variants_sha:
        raise ValueError("Report or variant-family evidence cannot be hashed")
    expected_promotion_kinds = {
        "alphafactory_optimization_wfa.v1": "optimization_aware_walk_forward",
        "alphafactory_robustness_promotion.v1": "matched_ea_rerun_parameter_sensitivity",
        "alphafactory_cscv_pbo.v1": "preregistered_aligned_variant_matrix_cscv",
        "alphafactory_white_reality_check.v1": "preregistered_aligned_white_reality_check",
    }
    variant_manifest_path = variants_dir / "variant_manifest.json"
    variant_manifest_sha = _file_sha256(variant_manifest_path)
    declared_manifest_sha = str(payload.get("variant_manifest_sha256") or "").strip()
    expected_kind = expected_promotion_kinds.get(schema_version)
    manifest_source_sha = str(
        _first_value(manifest, ("source_sha256", "main_file_sha256", "canonical_source_sha256")) or ""
    ).strip()
    producer_is_promotion_grade = all(
        (
            payload.get("promotion_eligible") is True,
            payload.get("analysis_kind") == expected_kind,
            variant_manifest_path.is_file(),
            bool(variant_manifest_sha),
            _same_resolved_path(payload.get("variant_manifest"), variant_manifest_path),
            _is_sha256(declared_manifest_sha),
            declared_manifest_sha.lower() == str(variant_manifest_sha).lower(),
            str(payload.get("hypothesis_id") or "").strip()
            == str(manifest.get("hypothesis_id") or "").strip(),
            _is_sha256(str(payload.get("source_sha256") or "").strip()),
            str(payload.get("source_sha256") or "").strip().lower()
            == manifest_source_sha.lower(),
        )
    )
    payload.update(
        {
            "schema_version": schema_version,
            "variants_dir": str(variants_dir),
            "variants_sha256": variants_sha,
            "report": str(report_path),
            "report_sha256": report_sha,
            "run_id": str(manifest.get("run_id") or "").strip(),
            "hypothesis_id": str(manifest.get("hypothesis_id") or "").strip(),
            "run_identity_sha256": _run_identity_sha256(manifest, report_sha),
            "analysis_kind": payload.get("analysis_kind") if producer_is_promotion_grade else (
                "posthoc_trade_csv_cscv_proxy"
                if schema_version == "alphafactory_cscv_pbo.v1"
                else "independent_variant_resampling_proxy"
            ),
            "promotion_eligible": producer_is_promotion_grade,
        }
    )
    if not producer_is_promotion_grade:
        payload["limitation"] = (
            "Diagnostic only: producer output did not prove a preregistered, hash-bound, "
            "aligned full variant family tied to the current run source."
        )
    _write_json(artifact_path, payload)


def _positive_profit_share(values: List[float]) -> Optional[float]:
    positive = [value for value in values if value > 0]
    total = sum(positive)
    if total <= 0:
        return None
    return max(positive) / total


def _monthly_stability_evidence(
    payload: Dict[str, Any],
    report_path: Path,
    manifest_path: Path,
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    rows = payload.get("months") if isinstance(payload.get("months"), list) else []
    if not payload:
        errors.append("monthly_fitness.json is missing or unreadable")
    if not _same_resolved_path(payload.get("report"), report_path):
        errors.append("monthly fitness report does not bind to current report")
    if not _same_resolved_path(payload.get("run_manifest"), manifest_path):
        errors.append("monthly fitness run_manifest does not bind to current run manifest")

    manifest_from = _parse_manifest_date(
        _first_value(manifest, ("from", "from_date", "FromDate", "From"))
    )
    manifest_to = _parse_manifest_date(
        _first_value(manifest, ("to", "to_date", "ToDate", "To"))
    )
    expected_months = _month_labels(manifest_from, manifest_to) if manifest_from and manifest_to else []
    monthly: Dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("monthly fitness contains a non-object month row")
            continue
        label = str(row.get("month") or "").strip()
        try:
            parsed = dt.datetime.strptime(label, "%Y-%m")
        except ValueError:
            errors.append(f"invalid month label: {label or '<missing>'}")
            continue
        value = _as_float(row.get("net_profit"))
        if value is None:
            errors.append(f"month {label} is missing finite net_profit")
            continue
        normalized = f"{parsed.year:04d}-{parsed.month:02d}"
        if normalized in monthly:
            errors.append(f"duplicate month row: {normalized}")
            continue
        monthly[normalized] = value

    actual_months = sorted(monthly)
    if not expected_months:
        errors.append("run manifest is missing a valid from/to window")
    elif actual_months != expected_months:
        errors.append("monthly fitness rows do not exactly cover the run-manifest window")
    window = payload.get("monthly_window") if isinstance(payload.get("monthly_window"), dict) else {}
    declared_total = _as_int(window.get("total_months"))
    if declared_total is None or declared_total != len(monthly):
        errors.append("monthly_window.total_months does not match month rows")

    half_year: Dict[str, float] = {}
    yearly: Dict[str, float] = {}
    for label, value in monthly.items():
        year = label[:4]
        month = int(label[5:7])
        half_label = f"{year}H{1 if month <= 6 else 2}"
        half_year[half_label] = half_year.get(half_label, 0.0) + value
        yearly[year] = yearly.get(year, 0.0) + value

    month_values = list(monthly.values())
    half_values = list(half_year.values())
    year_values = list(yearly.values())
    return {
        "errors": errors,
        "months": {
            "total": len(month_values),
            "positive": sum(value > 0 for value in month_values),
            "positive_ratio": (
                sum(value > 0 for value in month_values) / len(month_values)
                if month_values
                else None
            ),
            "max_positive_profit_share": _positive_profit_share(month_values),
        },
        "half_years": {
            "total": len(half_values),
            "positive": sum(value > 0 for value in half_values),
            "positive_ratio": (
                sum(value > 0 for value in half_values) / len(half_values)
                if half_values
                else None
            ),
            "max_positive_profit_share": _positive_profit_share(half_values),
        },
        "years": {
            "total": len(year_values),
            "positive": sum(value > 0 for value in year_values),
            "positive_ratio": (
                sum(value > 0 for value in year_values) / len(year_values)
                if year_values
                else None
            ),
            "max_positive_profit_share": _positive_profit_share(year_values),
        },
    }


def _stability_gate(
    actual: Dict[str, Any],
    *,
    minimum_periods: int,
    minimum_positive: Optional[int],
    minimum_positive_ratio: Optional[float],
    maximum_positive_profit_share: float,
    artifact: Path,
    evidence_errors: List[str],
    label: str,
) -> Dict[str, Any]:
    required_parts = [f"total {label} >= {minimum_periods}"]
    if minimum_positive is not None:
        required_parts.append(f"positive {label} >= {minimum_positive}")
    if minimum_positive_ratio is not None:
        required_parts.append(f"positive ratio >= {minimum_positive_ratio}")
    required_parts.append(f"max positive-profit share <= {maximum_positive_profit_share}")
    required = "; ".join(required_parts)
    if evidence_errors:
        return _gate(
            "BLOCKED",
            actual=actual,
            required=required,
            artifact=str(artifact),
            reason="; ".join(evidence_errors),
        )
    total = _as_int(actual.get("total"))
    if total is None or total < minimum_periods:
        return _gate(
            "BLOCKED",
            actual=actual,
            required=required,
            artifact=str(artifact),
            reason=f"Insufficient {label} coverage for confirmed-stage validation.",
        )
    positive = _as_int(actual.get("positive"))
    positive_ratio = _as_float(actual.get("positive_ratio"))
    concentration = _as_float(actual.get("max_positive_profit_share"))
    passed = concentration is not None and concentration <= maximum_positive_profit_share
    if minimum_positive is not None:
        passed = passed and positive is not None and positive >= minimum_positive
    if minimum_positive_ratio is not None:
        passed = passed and positive_ratio is not None and positive_ratio >= minimum_positive_ratio
    return _gate(
        "PASS" if passed else "FAIL",
        actual=actual,
        required=required,
        artifact=str(artifact),
        reason="" if passed else f"{label.capitalize()} stability or concentration is outside the confirmed-stage gate.",
    )


def evaluate_validation_gates(
    report: str,
    out_dir: str,
    *,
    stage: str = "challenger",
    thresholds: Optional[Dict[str, float]] = None,
    holding_contract: str = "scalp",
    cost_artifact: str = "",
    wfa_artifact: str = "",
    variants_dir: str = "",
    runner_results: Optional[Dict[str, Any]] = None,
    artifact_freshness: Optional[Dict[str, Any]] = None,
    invocation_id: str = "",
    invocation_start_utc: str = "",
    allow_research_cost_proxy: bool = False,
    economic_from: str = "",
    economic_to: str = "",
    baseline_acceptance_contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate promotion gates from bound artifacts and successful invocations."""
    normalized_stage = str(stage).strip().lower()
    if normalized_stage not in {"challenger", "confirmed"}:
        raise ValueError("stage must be 'challenger' or 'confirmed'")
    if holding_contract not in {"scalp", "non_scalp"}:
        raise ValueError("holding_contract must be 'scalp' or 'non_scalp'")

    gate_thresholds = dict(DEFAULT_GATE_THRESHOLDS)
    if thresholds:
        unknown = sorted(set(thresholds) - set(gate_thresholds))
        if unknown:
            raise ValueError(f"Unknown gate threshold(s): {', '.join(unknown)}")
        gate_thresholds.update({key: float(value) for key, value in thresholds.items()})

    report_path = Path(report).resolve()
    out_path = Path(out_dir).resolve()
    variants_path = Path(variants_dir).resolve() if str(variants_dir).strip() else None
    manifest_path = report_path.parent / "run_manifest.json"
    enhanced_path = out_path / "enhanced_summary.json"
    robustness_path = out_path / "robustness_results.json"
    monte_carlo_path = out_path / "monte_carlo_results.json"
    equity_path = out_path / "equity_audit.json"
    overnight_path = out_path / "overnight_exposure.json"
    execution_path = out_path / "slippage_summary.json"
    monthly_path = out_path / "monthly_fitness.json"
    nonrepaint_path = out_path / "nonrepaint_audit.json"
    pbo_path = out_path / "cscv_pbo.json"
    white_rc_path = out_path / "white_reality_check.json"

    manifest = _load_json(manifest_path)
    enhanced = _load_json(enhanced_path)
    robustness = _load_json(robustness_path)
    monte_carlo = _load_json(monte_carlo_path)
    equity = _load_json(equity_path)
    overnight = _load_json(overnight_path)
    execution = _load_json(execution_path)
    monthly = _load_json(monthly_path)
    nonrepaint = _load_json(nonrepaint_path)
    cost, cost_path, cost_resolution_reason = _resolve_cost_artifact(
        out_path, report_path, cost_artifact
    )

    gates: Dict[str, Dict[str, Any]] = {}
    manifest_model = _as_int(manifest.get("model"))
    gates["mt5_real_ticks_model"] = _gate(
        "PASS" if manifest_model == 0 else "BLOCKED",
        actual=manifest_model,
        required="run_manifest.model == 0 (every tick generated from M1 bars; not broker real ticks)",
        artifact=str(manifest_path),
        reason=(
            ""
            if manifest_model == 0
            else "Challenger and confirmed validation require Model 0 under the current contract; faster tester models cannot promote. Model 4 is a separate broker-real-tick fidelity contract."
        ),
    )
    nonrepaint_evidence = _nonrepaint_audit_evidence(
        nonrepaint,
        nonrepaint_path,
        manifest,
    )
    gates["nonrepaint_audit"] = _gate(
        "PASS" if nonrepaint_evidence["verified"] else "BLOCKED",
        actual=nonrepaint_evidence,
        required=(
            "PASS alphafactory_nonrepaint_audit.v1 bound to the exact rehashed "
            "run source/include snapshot set"
        ),
        artifact=str(nonrepaint_path),
        reason=(
            ""
            if nonrepaint_evidence["verified"]
            else "; ".join(nonrepaint_evidence["reasons"])
        ),
    )
    if runner_results is not None:
        failed_runners = {
            name: result
            for name, result in runner_results.items()
            if not _invocation_succeeded(result)
        }
        successful_runners = sorted(set(runner_results) - set(failed_runners))
        gates["runner_invocation_success"] = _gate(
            "PASS" if not failed_runners else "BLOCKED",
            actual={
                "successful": successful_runners,
                "failed": failed_runners,
            },
            required="every invoked runner/generator returns status OK and returncode 0 when present",
            reason=(
                ""
                if not failed_runners
                else "One or more validation invocations failed, timed out, skipped, warned, or returned nonzero."
            ),
        )
    n_trades = _as_int(enhanced.get("n_trades"))
    max_drawdown_pct = _as_float(enhanced.get("max_drawdown_pct"))

    from_date = _parse_manifest_date(economic_from) if economic_from else _parse_manifest_date(
        _first_value(manifest, ("from", "from_date", "FromDate", "From"))
    )
    to_date = _parse_manifest_date(economic_to) if economic_to else _parse_manifest_date(
        _first_value(manifest, ("to", "to_date", "ToDate", "To"))
    )
    inclusive_economic_window = bool(economic_from and economic_to)
    elapsed_days = _elapsed_window_days(
        from_date,
        to_date,
        inclusive=inclusive_economic_window,
    )
    elapsed_weeks = (elapsed_days / 7.0) if elapsed_days is not None and elapsed_days > 0 else None
    trades_per_week = (n_trades / elapsed_weeks) if n_trades is not None and elapsed_weeks else None
    cadence_actual = {
        "completed_positions": n_trades,
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
        "elapsed_days": elapsed_days,
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_week": trades_per_week,
        "formula": (
            "n_trades / (((economic_to - economic_from).days + 1) / 7.0)"
            if inclusive_economic_window
            else "n_trades / ((manifest_to - manifest_from).days / 7.0)"
        ),
    }
    min_cadence = gate_thresholds["min_trades_per_week"]
    max_cadence = gate_thresholds["max_trades_per_week"]
    if trades_per_week is None:
        gates["cadence"] = _gate(
            "BLOCKED",
            actual=cadence_actual,
            required=f"{min_cadence} <= trades/week <= {max_cadence}",
            artifact=str(manifest_path),
            reason="Missing completed-position count or a positive elapsed run-manifest date span.",
        )
    else:
        cadence_passed = min_cadence <= trades_per_week <= max_cadence
        gates["cadence"] = _gate(
            "PASS" if cadence_passed else "FAIL",
            actual=cadence_actual,
            required=f"{min_cadence} <= trades/week <= {max_cadence}",
            artifact=str(manifest_path),
            reason="" if cadence_passed else "Elapsed-calendar cadence is outside the allowed band.",
        )

    max_dd = gate_thresholds["max_drawdown_pct"]
    gates["max_drawdown_pct"] = _numeric_gate(
        max_drawdown_pct,
        lambda value: 0.0 <= value <= max_dd,
        f"0 <= value <= {max_dd}",
        enhanced_path,
        "Missing finite max_drawdown_pct in enhanced_summary.json.",
    )

    cost_path_for_gate = cost_path or Path(cost_artifact or (out_path / "sonic_cost_stress*.json"))
    cost_x1 = _cost_profit_factor(cost, "cost_x1_00", 1.0)
    cost_x1_5 = _cost_profit_factor(cost, "cost_x1_50", 1.5)
    cost_x2 = _cost_profit_factor(cost, "cost_x2_00", 2.0)
    _, cost_x1_reason = _validated_cost_scenario(cost, "cost_x1_00", 1.0)
    _, cost_x1_5_reason = _validated_cost_scenario(cost, "cost_x1_50", 1.5)
    _, cost_x2_reason = _validated_cost_scenario(cost, "cost_x2_00", 2.0)
    cost_provenance = _cost_provenance(
        cost,
        report_path,
        cost_path_for_gate,
        manifest,
        gate_thresholds,
        n_trades,
        allow_research_cost_proxy=allow_research_cost_proxy,
    )
    min_pf = gate_thresholds["min_profit_factor"]
    min_cost_x1_5 = gate_thresholds["min_cost_pf_x1_5"]
    min_cost_x2 = gate_thresholds["min_cost_pf_x2"]
    gates["profit_factor"] = _verified_cost_gate(
        cost_x1,
        min_pf,
        cost_path_for_gate,
        cost_provenance,
        cost_resolution_reason or cost_x1_reason or "Invalid cost_x1_00 scenario.",
        strict_minimum=True,
    )
    gates["cost_stress_x1_5"] = _verified_cost_gate(
        cost_x1_5,
        min_cost_x1_5,
        cost_path_for_gate,
        cost_provenance,
        cost_resolution_reason or cost_x1_5_reason or "Invalid cost_x1_50 scenario.",
    )
    gates["cost_stress_x2"] = _verified_cost_gate(
        cost_x2,
        min_cost_x2,
        cost_path_for_gate,
        cost_provenance,
        cost_resolution_reason or cost_x2_reason or "Invalid cost_x2_00 scenario.",
    )

    if baseline_acceptance_contract is not None:
        try:
            _, baseline_trades, _ = _load_trade_set(report_path)
            baseline_gates = _baseline_falsification_gates(
                baseline_trades,
                cost,
                economic_from,
                economic_to,
                baseline_acceptance_contract,
                str(cost_path_for_gate),
            )
        except Exception as exc:
            baseline_gates = {
                "economic_window_coverage": _gate(
                    "BLOCKED",
                    actual=None,
                    required="parseable report trades and a valid frozen baseline contract",
                    artifact=str(report_path),
                    reason=f"Baseline falsification evaluation failed: {exc}",
                )
            }
        gates.update(baseline_gates)

    robustness_summary = robustness.get("summary") if isinstance(robustness.get("summary"), dict) else {}
    robustness_rate = _normalized_ratio(robustness_summary.get("pass_rate"))
    min_robustness = gate_thresholds["min_robustness_pass_rate"]
    robustness_actual = {
        "pass_rate": robustness_rate,
        "analysis_kind": robustness.get("analysis_kind"),
        "promotion_eligible": robustness.get("promotion_eligible"),
    }
    robustness_bound, robustness_binding = (
        _variant_artifact_binding(
            robustness,
            expected_schema="alphafactory_robustness_promotion.v1",
            variants_dir=variants_path,
            report_path=report_path,
            manifest=manifest,
        )
        if normalized_stage == "confirmed" and variants_path is not None and robustness
        else (False, {})
    )
    robustness_actual["binding"] = robustness_binding
    if normalized_stage == "confirmed" and (
        robustness.get("analysis_kind") != "matched_ea_rerun_parameter_sensitivity"
        or robustness.get("promotion_eligible") is not True
    ):
        gates["robustness_pass_rate"] = _gate(
            "BLOCKED",
            actual=robustness_actual,
            required=(
                "promotion-eligible matched EA reruns over preregistered parameter/data perturbations "
                f"with pass_rate >= {min_robustness}"
            ),
            artifact=str(robustness_path),
            reason=(
                "The current robustness suite is a realized-P/L diagnostic proxy and cannot support "
                "confirmed promotion."
            ),
        )
    elif normalized_stage == "confirmed" and not robustness_bound:
        gates["robustness_pass_rate"] = _gate(
            "BLOCKED",
            actual=robustness_actual,
            required=(
                "fresh hash-bound matched EA reruns over the preregistered full variant family "
                f"with pass_rate >= {min_robustness}"
            ),
            artifact=str(robustness_path),
            reason="Robustness artifact is not bound to the current variant family and run identity.",
        )
    else:
        gates["robustness_pass_rate"] = _numeric_gate(
            robustness_rate,
            lambda value: value >= min_robustness,
            f">= {min_robustness}",
            robustness_path,
            "Missing numeric robustness summary.pass_rate.",
        )

    mc_dd = monte_carlo.get("max_drawdown_pct")
    mc_p95 = _as_float(mc_dd.get("p95")) if isinstance(mc_dd, dict) else None
    max_mc_dd = gate_thresholds["max_monte_carlo_p95_dd_pct"]
    gates["monte_carlo_p95_drawdown"] = _numeric_gate(
        mc_p95,
        lambda value: 0.0 <= value <= max_mc_dd,
        f"0 <= value <= {max_mc_dd}",
        monte_carlo_path,
        "Missing finite max_drawdown_pct.p95 in Monte Carlo artifact.",
    )

    equity_verdict = str(equity.get("verdict", "")).upper() if equity else ""
    if not equity_verdict:
        gates["equity_audit"] = _gate(
            "BLOCKED",
            actual=None,
            required="verdict == PASS",
            artifact=str(equity_path),
            reason="Missing equity_audit.json or verdict.",
        )
    else:
        equity_passed = equity_verdict == "PASS"
        gates["equity_audit"] = _gate(
            "PASS" if equity_passed else "FAIL",
            actual=equity_verdict,
            required="verdict == PASS",
            artifact=str(equity_path),
            reason="" if equity_passed else "Equity audit did not return PASS.",
        )

    if holding_contract == "scalp":
        counts = overnight.get("counts") if isinstance(overnight.get("counts"), dict) else {}
        overnight_count = _as_int(counts.get("overnight_trades"))
        weekend_count = _as_int(counts.get("weekend_crossing_trades"))
        exposure_actual = {
            "overnight_trades": overnight_count,
            "weekend_crossing_trades": weekend_count,
        }
        if overnight_count is None or weekend_count is None:
            gates["overnight_weekend_exposure"] = _gate(
                "BLOCKED",
                actual=exposure_actual,
                required="overnight_trades == 0 and weekend_crossing_trades == 0",
                artifact=str(overnight_path),
                reason="Missing overnight exposure artifact or required counts.",
            )
        else:
            exposure_passed = overnight_count == 0 and weekend_count == 0
            gates["overnight_weekend_exposure"] = _gate(
                "PASS" if exposure_passed else "FAIL",
                actual=exposure_actual,
                required="overnight_trades == 0 and weekend_crossing_trades == 0",
                artifact=str(overnight_path),
                reason="" if exposure_passed else "Scalp contract contains overnight or weekend exposure.",
            )
    else:
        gates["overnight_weekend_exposure"] = _gate(
            "PASS",
            actual={"holding_contract": holding_contract, "waived": True},
            required="not applicable to non-scalp contract",
            artifact=str(overnight_path),
            reason="",
        )

    quality = execution.get("execution_quality") if isinstance(execution.get("execution_quality"), dict) else {}
    gap_fields = ("open_ack_minus_fill_gap", "modify_unresolved", "close_unresolved")
    execution_gaps = {field: _as_int(quality.get(field)) for field in gap_fields}
    execution_available = execution.get("available") is True
    if not execution_available or any(value is None for value in execution_gaps.values()):
        gates["execution_reconciliation"] = _gate(
            "BLOCKED",
            actual={"available": execution_available, **execution_gaps},
            required="available == true and all reconciliation gaps == 0",
            artifact=str(execution_path),
            reason="Missing observed execution artifact or reconciliation counters.",
        )
    else:
        execution_passed = all(value == 0 for value in execution_gaps.values())
        gates["execution_reconciliation"] = _gate(
            "PASS" if execution_passed else "FAIL",
            actual={"available": True, **execution_gaps},
            required="available == true and all reconciliation gaps == 0",
            artifact=str(execution_path),
            reason="" if execution_passed else "Execution reconciliation contains unresolved gaps.",
        )

    artifact_paths: Dict[str, str] = {
        "run_manifest": str(manifest_path),
        "enhanced_summary": str(enhanced_path),
        "cost_stress": str(cost_path_for_gate),
        "robustness": str(robustness_path),
        "monte_carlo": str(monte_carlo_path),
        "equity_audit": str(equity_path),
        "overnight_exposure": str(overnight_path),
        "execution": str(execution_path),
        "monthly_fitness": str(monthly_path),
        "nonrepaint_audit": str(nonrepaint_path),
    }

    if normalized_stage == "confirmed":
        min_confirmed_trades = int(gate_thresholds["min_confirmed_trades"])
        gates["minimum_trades"] = _numeric_gate(
            float(n_trades) if n_trades is not None else None,
            lambda value: value >= min_confirmed_trades,
            f">= {min_confirmed_trades}",
            enhanced_path,
            "Missing completed-position count in enhanced_summary.json.",
        )

        stability = _monthly_stability_evidence(
            monthly,
            report_path,
            manifest_path,
            manifest,
        )
        stability_errors = list(stability.get("errors") or [])
        gates["monthly_stability"] = _stability_gate(
            stability["months"],
            minimum_periods=int(gate_thresholds["min_confirmed_months"]),
            minimum_positive=None,
            minimum_positive_ratio=gate_thresholds["min_positive_month_ratio"],
            maximum_positive_profit_share=gate_thresholds["max_month_positive_profit_share"],
            artifact=monthly_path,
            evidence_errors=stability_errors,
            label="months",
        )
        gates["half_year_stability"] = _stability_gate(
            stability["half_years"],
            minimum_periods=int(gate_thresholds["min_confirmed_half_years"]),
            minimum_positive=int(gate_thresholds["min_positive_half_years"]),
            minimum_positive_ratio=gate_thresholds["min_positive_half_year_ratio"],
            maximum_positive_profit_share=gate_thresholds["max_half_year_positive_profit_share"],
            artifact=monthly_path,
            evidence_errors=stability_errors,
            label="half-years",
        )
        gates["year_stability"] = _stability_gate(
            stability["years"],
            minimum_periods=int(gate_thresholds["min_confirmed_years"]),
            minimum_positive=int(gate_thresholds["min_positive_years"]),
            minimum_positive_ratio=gate_thresholds["min_positive_year_ratio"],
            maximum_positive_profit_share=gate_thresholds["max_year_positive_profit_share"],
            artifact=monthly_path,
            evidence_errors=stability_errors,
            label="years",
        )

        wfa, resolved_wfa_path = _resolve_wfa_artifact(out_path, wfa_artifact)
        artifact_paths["walk_forward"] = str(resolved_wfa_path)
        wfa_summary = wfa.get("summary") if isinstance(wfa.get("summary"), dict) else {}
        wfa_ratio = _normalized_ratio(
            _first_value(wfa_summary, ("oos_profitable_ratio", "profitable_oos_ratio"))
        )
        if wfa_ratio is None:
            wfa_ratio = _normalized_ratio(
                _first_value(wfa, ("oos_profitable_ratio", "profitable_oos_ratio"))
            )
        wfa_kind = str(wfa.get("analysis_kind", ""))
        promotion_wfa = (
            wfa.get("promotion_eligible") is True
            and wfa_kind == "optimization_aware_walk_forward"
        )
        wfa_run_bound, wfa_binding = _wfa_binding(wfa, report_path, manifest)
        wfa_family_bound, wfa_family_binding = (
            _variant_artifact_binding(
                wfa,
                expected_schema="alphafactory_optimization_wfa.v1",
                variants_dir=variants_path,
                report_path=report_path,
                manifest=manifest,
            )
            if variants_path is not None and wfa
            else (False, {})
        )
        wfa_bound = wfa_run_bound and wfa_family_bound
        wfa_actual = {
            "analysis_kind": wfa_kind or None,
            "promotion_eligible": wfa.get("promotion_eligible"),
            "oos_profitable_ratio": wfa_ratio,
            "binding": wfa_binding,
            "variant_family_binding": wfa_family_binding,
        }
        min_wfa_ratio = gate_thresholds["min_wfa_oos_profitable_ratio"]
        if not wfa:
            gates["walk_forward"] = _gate(
                "BLOCKED",
                actual=wfa_actual,
                required=f"optimization-aware promotion_eligible WFA with OOS ratio >= {min_wfa_ratio}",
                artifact=str(resolved_wfa_path),
                reason="Missing WFA artifact.",
            )
        elif not promotion_wfa:
            gates["walk_forward"] = _gate(
                "BLOCKED",
                actual=wfa_actual,
                required=f"optimization-aware promotion_eligible WFA with OOS ratio >= {min_wfa_ratio}",
                artifact=str(resolved_wfa_path),
                reason=(
                    "WFA analysis_kind must equal optimization_aware_walk_forward with "
                    "promotion_eligible=true; unknown/fixed-parameter artifacts cannot promote."
                ),
            )
        elif not wfa_bound:
            gates["walk_forward"] = _gate(
                "BLOCKED",
                actual=wfa_actual,
                required=f"optimization-aware promotion_eligible WFA with OOS ratio >= {min_wfa_ratio}",
                artifact=str(resolved_wfa_path),
                reason=(
                    "Optimization WFA artifact does not bind all required identities: "
                    "report path/hash, run_id, hypothesis_id, canonical run identity, and source hash."
                ),
            )
        elif wfa_ratio is None:
            gates["walk_forward"] = _gate(
                "BLOCKED",
                actual=wfa_actual,
                required=f"optimization-aware promotion_eligible WFA with OOS ratio >= {min_wfa_ratio}",
                artifact=str(resolved_wfa_path),
                reason="Promotion WFA artifact is missing a numeric OOS profitable ratio.",
            )
        else:
            wfa_passed = wfa_ratio >= min_wfa_ratio
            gates["walk_forward"] = _gate(
                "PASS" if wfa_passed else "FAIL",
                actual=wfa_actual,
                required=f"optimization-aware promotion_eligible WFA with OOS ratio >= {min_wfa_ratio}",
                artifact=str(resolved_wfa_path),
                reason="" if wfa_passed else "WFA OOS profitable ratio is below threshold.",
            )

        pbo = _load_json(pbo_path)
        artifact_paths["pbo"] = str(pbo_path)
        pbo_variants = _as_int(pbo.get("n_variants"))
        pbo_combos = _as_int(pbo.get("combos_used"))
        pbo_value = _as_float(pbo.get("pbo"))
        pbo_bound, pbo_binding = (
            _variant_artifact_binding(
                pbo,
                expected_schema="alphafactory_cscv_pbo.v1",
                variants_dir=variants_path,
                report_path=report_path,
                manifest=manifest,
            )
            if variants_path is not None and pbo
            else (False, {})
        )
        pbo_actual = {
            "n_variants": pbo_variants,
            "combos_used": pbo_combos,
            "pbo": pbo_value,
            "analysis_kind": pbo.get("analysis_kind"),
            "promotion_eligible": pbo.get("promotion_eligible"),
            "binding": pbo_binding,
        }
        max_pbo = gate_thresholds["max_pbo"]
        if variants_path is None:
            gates["pbo"] = _gate(
                "BLOCKED",
                actual=pbo_actual,
                required=f"fresh hash-bound variant family and PBO < {max_pbo}",
                artifact=str(pbo_path),
                reason="Confirmed validation requires a nonempty variants_dir; stale PBO evidence cannot be reused.",
            )
        elif (
            pbo.get("analysis_kind") != "preregistered_aligned_variant_matrix_cscv"
            or pbo.get("promotion_eligible") is not True
        ):
            gates["pbo"] = _gate(
                "BLOCKED",
                actual=pbo_actual,
                required=(
                    "promotion-eligible CSCV/PBO from a preregistered aligned variant matrix "
                    f"with PBO < {max_pbo}"
                ),
                artifact=str(pbo_path),
                reason=(
                    "The current PBO producer consumes post-hoc trade CSV variants and is "
                    "diagnostic-only; it cannot support confirmed promotion."
                ),
            )
        elif not pbo or pbo_variants is None or pbo_variants < 2 or pbo_combos is None or pbo_combos <= 0:
            gates["pbo"] = _gate(
                "BLOCKED",
                actual=pbo_actual,
                required=f"full variant family (>=2 variants), usable CSCV combinations, and PBO < {max_pbo}",
                artifact=str(pbo_path),
                reason="Missing PBO artifact, variant family, or usable CSCV combinations.",
            )
        elif not pbo_bound:
            gates["pbo"] = _gate(
                "BLOCKED",
                actual=pbo_actual,
                required=f"fresh hash-bound variant family and PBO < {max_pbo}",
                artifact=str(pbo_path),
                reason="PBO artifact does not bind to the supplied variant family and current run identity.",
            )
        elif pbo_value is None:
            gates["pbo"] = _gate(
                "BLOCKED",
                actual=pbo_actual,
                required=f"PBO < {max_pbo}",
                artifact=str(pbo_path),
                reason="PBO artifact is missing a finite pbo value.",
            )
        else:
            pbo_passed = pbo_value < max_pbo
            gates["pbo"] = _gate(
                "PASS" if pbo_passed else "FAIL",
                actual=pbo_actual,
                required=f"PBO < {max_pbo}",
                artifact=str(pbo_path),
                reason="" if pbo_passed else "PBO is not below the confirmed-stage threshold.",
            )

        white_rc = _load_json(white_rc_path)
        artifact_paths["white_reality_check"] = str(white_rc_path)
        white_variants = _as_int(white_rc.get("n_variants"))
        white_bootstrap = _as_int(white_rc.get("n_bootstrap"))
        white_p = _as_float(white_rc.get("p_value"))
        white_bound, white_binding = (
            _variant_artifact_binding(
                white_rc,
                expected_schema="alphafactory_white_reality_check.v1",
                variants_dir=variants_path,
                report_path=report_path,
                manifest=manifest,
            )
            if variants_path is not None and white_rc
            else (False, {})
        )
        white_actual = {
            "n_variants": white_variants,
            "n_bootstrap": white_bootstrap,
            "p_value": white_p,
            "analysis_kind": white_rc.get("analysis_kind"),
            "promotion_eligible": white_rc.get("promotion_eligible"),
            "binding": white_binding,
        }
        max_white_p = gate_thresholds["max_white_reality_check_p"]
        if variants_path is None:
            gates["white_reality_check"] = _gate(
                "BLOCKED",
                actual=white_actual,
                required=f"fresh hash-bound variant family and p < {max_white_p}",
                artifact=str(white_rc_path),
                reason="Confirmed validation requires a nonempty variants_dir; stale Reality Check evidence cannot be reused.",
            )
        elif (
            white_rc.get("analysis_kind") != "preregistered_aligned_white_reality_check"
            or white_rc.get("promotion_eligible") is not True
        ):
            gates["white_reality_check"] = _gate(
                "BLOCKED",
                actual=white_actual,
                required=(
                    "promotion-eligible White Reality Check preserving the preregistered aligned "
                    f"variant-selection process with p < {max_white_p}"
                ),
                artifact=str(white_rc_path),
                reason=(
                    "The current Reality Check independently resamples variant trade lists and is "
                    "diagnostic-only; it cannot support confirmed promotion."
                ),
            )
        elif (
            not white_rc
            or white_variants is None
            or white_variants < 2
            or white_bootstrap is None
            or white_bootstrap <= 0
        ):
            gates["white_reality_check"] = _gate(
                "BLOCKED",
                actual=white_actual,
                required=f"full variant family (>=2 variants), bootstrap samples, and p < {max_white_p}",
                artifact=str(white_rc_path),
                reason="Missing White Reality Check artifact, variant family, or bootstrap evidence.",
            )
        elif not white_bound:
            gates["white_reality_check"] = _gate(
                "BLOCKED",
                actual=white_actual,
                required=f"fresh hash-bound variant family and p < {max_white_p}",
                artifact=str(white_rc_path),
                reason="Reality Check artifact does not bind to the supplied variant family and current run identity.",
            )
        elif white_p is None:
            gates["white_reality_check"] = _gate(
                "BLOCKED",
                actual=white_actual,
                required=f"p < {max_white_p}",
                artifact=str(white_rc_path),
                reason="White Reality Check artifact is missing a finite p_value.",
            )
        else:
            white_passed = white_p < max_white_p
            gates["white_reality_check"] = _gate(
                "PASS" if white_passed else "FAIL",
                actual=white_actual,
                required=f"p < {max_white_p}",
                artifact=str(white_rc_path),
                reason="" if white_passed else "White Reality Check p-value is not below threshold.",
            )

    if artifact_freshness is not None:
        not_fresh = list(artifact_freshness.get("not_fresh") or [])
        if "not_fresh" not in artifact_freshness:
            not_fresh = sorted(
                {
                    *list(artifact_freshness.get("missing") or []),
                    *list(artifact_freshness.get("unchanged") or []),
                    *list(artifact_freshness.get("identical_rewrite") or []),
                    *list(artifact_freshness.get("failed_producer") or []),
                }
            )
        freshness_passed = not not_fresh
        gates["invocation_artifact_freshness"] = _gate(
            "PASS" if freshness_passed else "BLOCKED",
            actual=artifact_freshness,
            required=(
                "every invocation-owned artifact has a successful producer invocation and is newly "
                "created or has a content SHA256 delta"
            ),
            reason=(
                ""
                if freshness_passed
                else "Invocation-owned artifacts lack a successful attributable content-fingerprint delta."
            ),
        )

    baseline_gate_names = [
        "mt5_real_ticks_model",
        "nonrepaint_audit",
        "economic_window_coverage",
        "cadence",
        "max_drawdown_pct",
        "profit_factor",
        "cost_stress_x1_5",
        "cost_stress_x2",
        "minimum_trades_baseline",
        "direction_balance_baseline",
        "year_trade_concentration_baseline",
        "positive_cost_expectancy_baseline",
        "all_calendar_years_positive_baseline",
    ]
    baseline_gate_names = [name for name in baseline_gate_names if name in gates]
    baseline_non_passing = [
        name for name in baseline_gate_names if gates[name]["status"] != "PASS"
    ]
    baseline_blocked = any(gates[name]["status"] == "BLOCKED" for name in baseline_gate_names)
    baseline_verdict = (
        "NOT_EVALUATED"
        if baseline_acceptance_contract is None
        else "BLOCKED"
        if baseline_blocked
        else "FAIL"
        if baseline_non_passing
        else "PASS"
    )

    gates_passed = sum(1 for gate in gates.values() if gate["status"] == "PASS")
    non_passing = [name for name, gate in gates.items() if gate["status"] != "PASS"]
    verdict = "PASS" if not non_passing else "REVIEW"
    return {
        "schema_version": "alphafactory_validation_summary.v2",
        "invocation_id": invocation_id,
        "invocation_start_utc": invocation_start_utc,
        "report": str(report_path),
        "output_dir": str(out_path),
        "stage": normalized_stage,
        "holding_contract": holding_contract,
        "thresholds": gate_thresholds,
        "decision_basis": "successful_invocations_plus_bound_numeric_and_artifact_gates",
        "runner_exit_codes_affect_verdict": True,
        "runners": runner_results or {},
        "artifact_paths": artifact_paths,
        "gates": gates,
        "gates_passed": gates_passed,
        "gates_total": len(gates),
        "non_passing_gates": non_passing,
        "verdict": verdict,
        "economic_window": {
            "from": economic_from or None,
            "to": economic_to or None,
            "boundary": "inclusive_calendar_dates" if economic_from and economic_to else None,
        },
        "baseline_acceptance_contract": baseline_acceptance_contract,
        "baseline_falsification_gate_names": baseline_gate_names,
        "baseline_falsification_non_passing_gates": baseline_non_passing,
        "baseline_falsification_verdict": baseline_verdict,
        "research_cost_proxy": cost_provenance.get("evidence_tier") == "RESEARCH_PROXY",
        "research_falsification_eligible": bool(
            cost_provenance.get("verified")
            and cost_provenance.get("research_falsification_eligible")
        ),
        "promotion_eligible": bool(
            verdict == "PASS" and cost_provenance.get("promotion_eligible") is True
        ),
    }


def run_all_validations(
    report: str,
    out_dir: str,
    parallel: bool = True,
    *,
    stage: str = "challenger",
    thresholds: Optional[Dict[str, float]] = None,
    holding_contract: str = "scalp",
    cost_artifact: str = "",
    wfa_artifact: str = "",
    variants_dir: str = "",
    allow_research_cost_proxy: bool = False,
    economic_from: str = "",
    economic_to: str = "",
    baseline_acceptance_contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run all validation tests, optionally in parallel.

    DAG structure:
      Layer 0 (parallel): [enhanced_analysis, equity_audit]
      Layer 1 (parallel): [monte_carlo, walk_forward, robustness]
      Layer 2 (serial):   [artifact consolidation]

    All Layer 0 and 1 tests are independent — run them all in parallel.
    """
    normalized_stage = str(stage).strip().lower()
    promotion_manifest_path = (
        (Path(variants_dir).resolve() / "variant_manifest.json")
        if normalized_stage == "confirmed" and variants_dir
        else None
    )
    promotion_manifest = (
        str(promotion_manifest_path)
        if promotion_manifest_path is not None and promotion_manifest_path.is_file()
        else ""
    )
    tests = [
        ("enhanced_analysis", run_enhanced_analysis),
        ("equity_curve_audit", run_equity_audit),
        ("monte_carlo", run_monte_carlo),
        (
            "walk_forward",
            lambda current_report, output: run_walk_forward(
                current_report, output, promotion_manifest
            ),
        ),
        (
            "robustness_suite",
            lambda current_report, output: run_robustness(
                current_report, output, promotion_manifest
            ),
        ),
    ]
    if normalized_stage == "confirmed" and variants_dir:
        tests.extend(
            [
                (
                    "cscv_pbo",
                    lambda _report, output: run_cscv_pbo(
                        variants_dir, output, promotion_manifest
                    ),
                ),
                (
                    "white_reality_check",
                    lambda _report, output: run_white_reality_check(
                        variants_dir, output, promotion_manifest
                    ),
                ),
            ]
        )

    results: Dict[str, Any] = {}
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    invocation_id = str(uuid.uuid4())
    invocation_start_utc = _now_utc()
    owned_artifact_paths = _invocation_owned_artifacts(
        out_path,
        stage=stage,
        variants_dir=variants_dir,
    )
    before_artifacts = _snapshot_artifacts(owned_artifact_paths)
    t_start = time.perf_counter()

    if parallel:
        with ThreadPoolExecutor(max_workers=len(tests)) as executor:
            futures = {
                executor.submit(fn, report, out_dir): name
                for name, fn in tests
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    results[name] = {"test": name, "status": "ERROR", "reason": str(e)}
    else:
        for name, fn in tests:
            print(f"  Running {name}...")
            results[name] = fn(report, out_dir)

    if normalized_stage == "confirmed" and variants_dir:
        report_path = Path(report).resolve()
        manifest = _load_json(report_path.parent / "run_manifest.json")
        variants_path = Path(variants_dir).resolve()
        binding_targets = [
            ("cscv_pbo", "cscv_pbo.json", "alphafactory_cscv_pbo.v1"),
            (
                "white_reality_check",
                "white_reality_check.json",
                "alphafactory_white_reality_check.v1",
            ),
        ]
        if promotion_manifest:
            binding_targets.extend(
                [
                    ("walk_forward", "wfa_results.json", "alphafactory_optimization_wfa.v1"),
                    (
                        "robustness_suite",
                        "robustness_results.json",
                        "alphafactory_robustness_promotion.v1",
                    ),
                ]
            )
        for runner_name, artifact_name, schema_version in binding_targets:
            if _invocation_succeeded(results.get(runner_name)):
                try:
                    _bind_variant_artifact(
                        out_path / artifact_name,
                        schema_version=schema_version,
                        variants_dir=variants_path,
                        report_path=report_path,
                        manifest=manifest,
                    )
                except Exception as exc:
                    results[runner_name] = {
                        **(results.get(runner_name) or {}),
                        "status": "ERROR",
                        "reason": f"Variant artifact binding failed: {exc}",
                    }

    artifact_results = {
        "slippage_summary": generate_slippage_summary(report, out_dir),
        "monthly_fitness": generate_monthly_fitness(report, out_dir),
        "overnight_exposure": generate_overnight_exposure(report, out_dir),
    }
    invocation_results = {**results, **artifact_results}
    after_artifacts = _snapshot_artifacts(owned_artifact_paths)
    artifact_freshness = _compare_artifact_snapshots(
        before_artifacts,
        after_artifacts,
        producer_results=invocation_results,
        producer_by_artifact=ARTIFACT_PRODUCERS,
    )

    total_elapsed = round(time.perf_counter() - t_start, 1)

    summary = evaluate_validation_gates(
        report,
        out_dir,
        stage=stage,
        thresholds=thresholds,
        holding_contract=holding_contract,
        cost_artifact=cost_artifact,
        wfa_artifact=wfa_artifact,
        variants_dir=variants_dir,
        runner_results=invocation_results,
        artifact_freshness=artifact_freshness,
        invocation_id=invocation_id,
        invocation_start_utc=invocation_start_utc,
        allow_research_cost_proxy=allow_research_cost_proxy,
        economic_from=economic_from,
        economic_to=economic_to,
        baseline_acceptance_contract=baseline_acceptance_contract,
    )
    summary["total_elapsed_s"] = total_elapsed
    summary["parallel"] = parallel
    summary["tests"] = {
        name: {
            "status": result.get("status", "UNKNOWN"),
            "returncode": result.get("returncode"),
            "elapsed_s": result.get("elapsed_s", 0),
            "verdict_input": True,
        }
        for name, result in invocation_results.items()
    }
    summary["artifacts"] = artifact_results

    return summary


# ─── Transcript checkpoint (save analysis context) ───


def save_transcript(summary: Dict[str, Any], results: Dict[str, Any], out_dir: str) -> str:
    """Save full validation transcript as JSONL for replay/debugging."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    transcript_path = out_path / f"validation_transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "summary", "data": summary}, ensure_ascii=False) + "\n")
        for name, result in results.items():
            f.write(json.dumps({"type": "test_result", "test": name, "data": result}, ensure_ascii=False) + "\n")

    return str(transcript_path)


# ─── Context compressor ───


def compress_validation_context(summary: Dict[str, Any]) -> str:
    """Compress full validation results into a concise summary for LLM context."""
    lines = [
        f"## Validation Summary ({summary.get('total_elapsed_s', '?')}s, {'parallel' if summary.get('parallel') else 'sequential'})",
        f"Stage: **{summary.get('stage', 'UNKNOWN')}**",
        f"Verdict: **{summary.get('verdict', 'UNKNOWN')}** ({summary.get('gates_passed', 0)}/{summary.get('gates_total', 0)} numeric/artifact gates)",
        "",
    ]

    for name, gate in summary.get("gates", {}).items():
        lines.append(f"  {gate.get('status', '?')} | {name} | required {gate.get('required', '')}")

    lines.extend(["", "Invocation outcomes (verdict inputs):"])
    for name, test_info in summary.get("tests", {}).items():
        status = test_info.get("status", "?")
        elapsed = test_info.get("elapsed_s", 0)
        lines.append(f"  {status} | {name} ({elapsed}s)")

    lines.append("")
    for name, artifact in summary.get("artifacts", {}).items():
        status = artifact.get("status", "?")
        lines.append(f"  {status} | {name} -> {artifact.get('artifact', '')}")

    return "\n".join(lines)


# ─── CLI ───


def main():
    parser = argparse.ArgumentParser(description="AlphaFactory Unified Validation Runner")
    parser.add_argument("--report", required=True, help="Path to MT5 backtest report.html")
    parser.add_argument("--out", default="", help="Output directory (default: alongside report, ./analysis)")
    parser.add_argument("--stage", choices=["challenger", "confirmed"], default="challenger")
    parser.add_argument("--holding-contract", choices=["scalp", "non_scalp"], default="scalp")
    parser.add_argument("--cost-artifact", default="", help="Explicit cost-stress JSON path")
    parser.add_argument("--wfa-artifact", default="", help="Explicit optimization-aware WFA JSON path")
    parser.add_argument("--variants-dir", default="", help="Full tried-variant family for confirmed PBO/White RC")
    parser.add_argument(
        "--allow-research-cost-proxy",
        action="store_true",
        help="Accept explicitly non-promotable RESEARCH_PROXY cost evidence for falsification",
    )
    parser.add_argument("--economic-from", default="", help="Inclusive economic scoring-window start (YYYY.MM.DD)")
    parser.add_argument("--economic-to", default="", help="Inclusive economic scoring-window end (YYYY.MM.DD)")
    parser.add_argument("--min-completed-trades", type=int, default=0)
    parser.add_argument("--min-direction-share", type=float, default=0.0)
    parser.add_argument("--max-year-trade-share", type=float, default=1.0)
    parser.add_argument("--require-positive-cost-expectancy", action="store_true")
    parser.add_argument("--require-all-calendar-years-positive", action="store_true")
    parser.add_argument("--min-pf", type=float, default=DEFAULT_GATE_THRESHOLDS["min_profit_factor"])
    parser.add_argument("--min-trades-per-week", type=float, default=DEFAULT_GATE_THRESHOLDS["min_trades_per_week"])
    parser.add_argument("--max-trades-per-week", type=float, default=DEFAULT_GATE_THRESHOLDS["max_trades_per_week"])
    parser.add_argument("--max-dd-pct", type=float, default=DEFAULT_GATE_THRESHOLDS["max_drawdown_pct"])
    parser.add_argument("--min-cost-pf-x1-5", type=float, default=DEFAULT_GATE_THRESHOLDS["min_cost_pf_x1_5"])
    parser.add_argument("--min-cost-pf-x2", type=float, default=DEFAULT_GATE_THRESHOLDS["min_cost_pf_x2"])
    parser.add_argument("--min-robustness-pass-rate", type=float, default=DEFAULT_GATE_THRESHOLDS["min_robustness_pass_rate"])
    parser.add_argument("--max-mc-p95-dd-pct", type=float, default=DEFAULT_GATE_THRESHOLDS["max_monte_carlo_p95_dd_pct"])
    parser.add_argument("--min-confirmed-trades", type=int, default=int(DEFAULT_GATE_THRESHOLDS["min_confirmed_trades"]))
    parser.add_argument("--min-wfa-oos-ratio", type=float, default=DEFAULT_GATE_THRESHOLDS["min_wfa_oos_profitable_ratio"])
    parser.add_argument("--max-pbo", type=float, default=DEFAULT_GATE_THRESHOLDS["max_pbo"])
    parser.add_argument("--max-white-rc-p", type=float, default=DEFAULT_GATE_THRESHOLDS["max_white_reality_check_p"])
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially (default: parallel)")
    parser.add_argument("--json", action="store_true", help="Output JSON only (no human-readable)")
    args = parser.parse_args()

    report = args.report
    report_path = Path(report)
    if not report_path.exists():
        print(f"ERROR: Report not found: {report}", file=sys.stderr)
        sys.exit(1)

    out_dir = args.out or str(report_path.parent / "analysis")
    parallel = not args.sequential

    if not args.json:
        worker_count = 7 if args.stage == "confirmed" and args.variants_dir else 5
        print(f"\n  ALPHAFACTORY UNIFIED VALIDATION")
        print(f"  {'=' * 50}")
        print(f"  Report:   {report}")
        print(f"  Output:   {out_dir}")
        print(f"  Stage:    {args.stage}")
        print(f"  Mode:     {f'Parallel ({worker_count} workers)' if parallel else 'Sequential'}")
        print(f"  {'=' * 50}\n")

    thresholds = {
        "min_profit_factor": args.min_pf,
        "min_trades_per_week": args.min_trades_per_week,
        "max_trades_per_week": args.max_trades_per_week,
        "max_drawdown_pct": args.max_dd_pct,
        "min_cost_pf_x1_5": args.min_cost_pf_x1_5,
        "min_cost_pf_x2": args.min_cost_pf_x2,
        "min_robustness_pass_rate": args.min_robustness_pass_rate,
        "max_monte_carlo_p95_dd_pct": args.max_mc_p95_dd_pct,
        "min_confirmed_trades": float(args.min_confirmed_trades),
        "min_wfa_oos_profitable_ratio": args.min_wfa_oos_ratio,
        "max_pbo": args.max_pbo,
        "max_white_reality_check_p": args.max_white_rc_p,
    }
    baseline_acceptance_contract = None
    if args.min_completed_trades > 0:
        baseline_acceptance_contract = {
            "min_completed_trades": args.min_completed_trades,
            "min_direction_share": args.min_direction_share,
            "max_year_trade_share": args.max_year_trade_share,
            "require_positive_cost_expectancy": args.require_positive_cost_expectancy,
            "require_all_calendar_years_positive": args.require_all_calendar_years_positive,
        }
    summary = run_all_validations(
        report,
        out_dir,
        parallel=parallel,
        stage=args.stage,
        thresholds=thresholds,
        holding_contract=args.holding_contract,
        cost_artifact=args.cost_artifact,
        wfa_artifact=args.wfa_artifact,
        variants_dir=args.variants_dir,
        allow_research_cost_proxy=args.allow_research_cost_proxy,
        economic_from=args.economic_from,
        economic_to=args.economic_to,
        baseline_acceptance_contract=baseline_acceptance_contract,
    )

    summary_path = Path(out_dir) / "validation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(compress_validation_context(summary))
        print(f"\n  Saved: {summary_path}")

    sys.exit(0 if summary["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
