#!/usr/bin/env python3
"""Report-only cost stress for EA_SonicR MT5 trade artifacts.

This tool intentionally labels the result as a proxy when slippage telemetry is
missing. It reprices parsed MT5 report trades by subtracting a simple round-turn
cost from every closed trade. It is useful for first-pass falsification, not for
broker execution proof.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
ANALYSIS_ROOT = ALPHA_ROOT / "analysis"
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"

sys.path.insert(0, str(ANALYSIS_ROOT))
from quant_analyzer import bucket_stats, deals_to_trades, parse_deals  # noqa: E402


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-16"))


def safe_num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def get_start_equity(deals: list[Any], default: float = 10000.0) -> float:
    for deal in deals:
        if (deal.side or "").strip().lower() == "balance" and deal.balance > 0:
            return float(deal.balance)
    return default


def max_drawdown_pct(profits: list[float], start_equity: float) -> float:
    equity = start_equity
    peak = start_equity
    max_dd = 0.0
    for profit in profits:
        equity += profit
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return max_dd


def monthly_counts(trades: list[Any], adjusted: list[float]) -> dict[str, Any]:
    months: dict[str, float] = {}
    for trade, profit in zip(trades, adjusted):
        key = trade.exit_time.strftime("%Y-%m")
        months[key] = months.get(key, 0.0) + profit
    total = len(months)
    positive = sum(1 for value in months.values() if value > 0)
    negative = sum(1 for value in months.values() if value < 0)
    return {
        "active_months": total,
        "positive_months": positive,
        "negative_months": negative,
        "positive_month_ratio": round(positive / total, 6) if total else 0.0,
        "months": [{"month": key, "net_profit": round(value, 2)} for key, value in sorted(months.items())],
    }


def scenario_stats(trades: list[Any], adjusted: list[float], start_equity: float) -> dict[str, Any]:
    proxy_trades = []
    for trade, profit in zip(trades, adjusted):
        proxy_trades.append(type("ProxyTrade", (), {"profit": profit})())
    stats = bucket_stats(proxy_trades)
    months = monthly_counts(trades, adjusted)
    return {
        "n_trades": len(adjusted),
        "net_profit": round(sum(adjusted), 2),
        "profit_factor": round(safe_num(stats.get("profit_factor")), 6),
        "win_rate_pct": round(safe_num(stats.get("win_rate_pct")), 6),
        "expectancy_per_trade": round(sum(adjusted) / len(adjusted), 6) if adjusted else 0.0,
        "max_drawdown_pct": round(max_drawdown_pct(adjusted, start_equity), 6),
        "positive_months": months["positive_months"],
        "negative_months": months["negative_months"],
        "active_months": months["active_months"],
        "positive_month_ratio": months["positive_month_ratio"],
    }


def build_cost_matrix(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = run_dir_for(args.run, args.ea)
    report = Path(args.report).resolve() if args.report else run_dir / "report.html"
    if not report.exists():
        return {
            "schema_version": "sonic_cost_stress.v1",
            "verdict": "INVALID",
            "findings": [f"missing_report:{report}"],
        }

    manifest = load_json(run_dir / "run_manifest.json")
    slippage = load_json(run_dir / "analysis" / "slippage_summary.json")
    deals = parse_deals(report)
    trades = deals_to_trades(deals)
    start_equity = get_start_equity(deals, args.start_equity)
    base_profits = [float(t.profit) for t in trades]

    base_round_turn_cost = args.base_cost_per_trade
    if base_round_turn_cost == 0.0:
        base_round_turn_cost = (
            args.spread_points * args.point_value_per_lot * args.lot_size
            + args.slippage_points * 2.0 * args.point_value_per_lot * args.lot_size
            + args.commission_round_turn
        )

    scenarios = []
    for label, multiplier in (
        ("base_report", 0.0),
        ("cost_x1_00", 1.0),
        ("cost_x1_25", 1.25),
        ("cost_x1_50", 1.50),
        ("cost_x2_00", 2.00),
    ):
        round_turn = base_round_turn_cost * multiplier
        adjusted = [profit - round_turn for profit in base_profits]
        row = scenario_stats(trades, adjusted, start_equity)
        row.update(
            {
                "scenario": label,
                "cost_multiplier": multiplier,
                "round_turn_cost_per_trade": round(round_turn, 6),
                "delta_net_vs_report": round(row["net_profit"] - sum(base_profits), 2),
            }
        )
        scenarios.append(row)

    findings: list[str] = []
    stress_mode = "telemetry_informed"
    if not slippage or not slippage.get("available"):
        stress_mode = "report_only_cost_stress"
        findings.append("slippage_samples_missing_report_only_proxy")
    if base_round_turn_cost <= 0:
        findings.append("zero_cost_assumption")

    x150 = next(row for row in scenarios if row["scenario"] == "cost_x1_50")
    x200 = next(row for row in scenarios if row["scenario"] == "cost_x2_00")
    if x150["profit_factor"] < 1.25:
        findings.append("pf_below_1_25_at_cost_x1_50")
    if x200["profit_factor"] < 1.0:
        findings.append("pf_below_1_00_at_cost_x2_00")

    verdict = "REVIEW"
    if findings == []:
        verdict = "RESEARCH_PASS"

    return {
        "schema_version": "sonic_cost_stress.v1",
        "run_id": (manifest or {}).get("run_id") or run_dir.name,
        "run_dir": str(run_dir),
        "report": str(report),
        "symbol": (manifest or {}).get("symbol") or "",
        "period": (manifest or {}).get("period") or "",
        "model": safe_int((manifest or {}).get("model")),
        "stress_mode": stress_mode,
        "cost_assumption": {
            "base_cost_per_trade": args.base_cost_per_trade,
            "spread_points": args.spread_points,
            "slippage_points": args.slippage_points,
            "commission_round_turn": args.commission_round_turn,
            "point_value_per_lot": args.point_value_per_lot,
            "lot_size": args.lot_size,
            "computed_base_round_turn_cost": round(base_round_turn_cost, 6),
            "note": "Report-only proxy: subtracts round-turn cost from each closed trade. Use telemetry/broker data before deploy claims.",
        },
        "report_trade_count": len(trades),
        "scenarios": scenarios,
        "findings": findings,
        "verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run report-only Sonic R cost-stress matrix.")
    ap.add_argument("run", help="Run id or run directory.")
    ap.add_argument("--ea", default=DEFAULT_EA, help=f"EA name under AlphaFactory runs (default: {DEFAULT_EA}).")
    ap.add_argument("--report", default="", help="Optional report.html path.")
    ap.add_argument("--out", default="", help="Optional JSON output path.")
    ap.add_argument("--start-equity", type=float, default=10000.0)
    ap.add_argument("--base-cost-per-trade", type=float, default=0.0)
    ap.add_argument("--spread-points", type=float, default=0.0)
    ap.add_argument("--slippage-points", type=float, default=0.0)
    ap.add_argument("--commission-round-turn", type=float, default=0.0)
    ap.add_argument("--point-value-per-lot", type=float, default=1.0)
    ap.add_argument("--lot-size", type=float, default=0.01)
    args = ap.parse_args()

    result = build_cost_matrix(args)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result["verdict"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
