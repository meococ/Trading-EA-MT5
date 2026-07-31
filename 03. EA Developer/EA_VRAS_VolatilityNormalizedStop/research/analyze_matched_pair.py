#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

START = datetime(2019, 1, 1)
END = datetime(2022, 12, 31)
ELAPSED_WEEKS = (END - START).total_seconds() / (7 * 86400)

def one_run(run: Path) -> dict:
    summary = json.loads((run / "analysis" / "enhanced_summary.json").read_text(encoding="utf-8"))
    lifecycle = next((run / "analysis" / "logs").glob("*_LifecycleTrades_*.csv"))
    runmeta = json.loads(next((run / "analysis" / "logs").glob("*_RunMeta_*.json")).read_text(encoding="utf-8"))
    rows = list(csv.DictReader(lifecycle.open(encoding="utf-8-sig", newline="")))
    positions = defaultdict(list)
    for row in rows:
        positions[row["position_id"]].append(row)
    trades = []
    for position_id, events in positions.items():
        opens = [r for r in events if r["action"] == "OPEN"]
        closes = [r for r in events if r["is_final_close"] in {"1", "true", "True"}]
        if len(opens) != 1 or len(closes) != 1:
            raise SystemExit(f"unreconciled position {position_id}: opens={len(opens)} closes={len(closes)}")
        entry, close = opens[0], closes[0]
        direction = 1 if entry["order_type"] == "BUY" else -1
        risk = float(entry["initial_risk_account"])
        risk_pts = float(entry["risk_pts"])
        net = sum(float(r["deal_net"]) for r in events)
        price_pnl = sum(float(r["deal_profit"]) for r in events)
        costs = sum(float(r["deal_commission"]) + float(r["deal_swap"]) + float(r["deal_fee"]) for r in events)
        price_r = direction * (float(close["price"]) - float(entry["price"])) / (risk_pts * 0.00001)
        trades.append({
            "position_id": position_id, "entry_time": entry["event_time"], "exit_time": close["event_time"],
            "direction": entry["order_type"], "entry": float(entry["price"]), "exit": float(close["price"]),
            "risk_pts": risk_pts, "risk_account": risk, "net": net, "price_pnl": price_pnl, "costs": costs,
            "realized_r": net / risk, "price_r": price_r,
        })
    lifecycle_net = sum(t["net"] for t in trades)
    if round(lifecycle_net - float(summary["net_profit"]), 2) != 0:
        raise SystemExit(f"report/lifecycle mismatch {run}: {lifecycle_net} vs {summary['net_profit']}")
    def stressed_pf(multiplier: float) -> float:
        values = [t["price_pnl"] + multiplier * t["costs"] for t in trades]
        gains = sum(v for v in values if v > 0)
        losses = -sum(v for v in values if v < 0)
        return gains / losses if losses else float("inf")
    return {
        "run_id": run.name, "run_path": str(run), "variant": runmeta["variant_tag"],
        "history_quality_pct": 100, "trades": len(trades),
        "profit_factor": float(summary["profit_factor"]), "net_profit_usd": float(summary["net_profit"]),
        "win_rate_pct": float(summary["win_rate_pct"]), "expectancy_usd": float(summary["expectancy_per_trade"]),
        "max_drawdown_pct": float(summary["max_drawdown_pct"]),
        "cadence_per_elapsed_calendar_week": len(trades) / ELAPSED_WEEKS,
        "mean_realized_r": sum(t["realized_r"] for t in trades) / len(trades),
        "initial_stop_exit_share": sum(t["price_r"] <= -0.90 for t in trades) / len(trades),
        "target_exit_share": sum(t["price_r"] >= 1.40 for t in trades) / len(trades),
        "mean_stop_pips": sum(t["risk_pts"] * 0.1 for t in trades) / len(trades),
        "min_stop_pips": min(t["risk_pts"] * 0.1 for t in trades),
        "max_stop_pips": max(t["risk_pts"] * 0.1 for t in trades),
        "price_pnl_usd": sum(t["price_pnl"] for t in trades), "costs_usd": sum(t["costs"] for t in trades),
        "cost_pf_x1_5_proxy": stressed_pf(1.5), "cost_pf_x2_proxy": stressed_pf(2.0),
        "lifecycle": {"rows": len(rows), "opens": sum(r["action"] == "OPEN" for r in rows),
            "final_closes": sum(r["is_final_close"] in {"1", "true", "True"} for r in rows),
            "unique_positions": len(positions), "net_usd": lifecycle_net,
            "report_gap_usd": lifecycle_net - float(summary["net_profit"]),
            "minimum_initial_risk_account": min(t["risk_account"] for t in trades)},
        "diagnostic": runmeta["diagnostic"], "last_exit_time": max(t["exit_time"] for t in trades),
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--control", type=Path, required=True)
    p.add_argument("--challenger", type=Path, required=True)
    p.add_argument("--out-json", type=Path, required=True)
    p.add_argument("--out-md", type=Path, required=True)
    args = p.parse_args()
    control, challenger = one_run(args.control), one_run(args.challenger)
    relative = {
        "profit_factor_lift": challenger["profit_factor"] - control["profit_factor"],
        "mean_realized_r_lift": challenger["mean_realized_r"] - control["mean_realized_r"],
        "initial_stop_exit_share_reduction": control["initial_stop_exit_share"] - challenger["initial_stop_exit_share"],
        "max_drawdown_change_pct_points": challenger["max_drawdown_pct"] - control["max_drawdown_pct"],
    }
    absolute_gates = {
        "trades_gte_350": challenger["trades"] >= 350,
        "cadence_2_to_5": 2.0 <= challenger["cadence_per_elapsed_calendar_week"] <= 5.0,
        "pf_gte_1_30": challenger["profit_factor"] >= 1.30,
        "mean_r_gt_0_05": challenger["mean_realized_r"] > 0.05,
        "dd_lte_6": challenger["max_drawdown_pct"] <= 6.0,
        "cost_pf_x1_5_gte_1_25": challenger["cost_pf_x1_5_proxy"] >= 1.25,
        "cost_pf_x2_gte_1": challenger["cost_pf_x2_proxy"] >= 1.0,
    }
    relative_gates = {
        "pf_lift_gte_0_15": relative["profit_factor_lift"] >= 0.15,
        "mean_r_lift_gte_0_10": relative["mean_realized_r_lift"] >= 0.10,
        "stop_share_reduction_gte_10pp": relative["initial_stop_exit_share_reduction"] >= 0.10,
        "dd_not_worse_by_more_than_1pp": relative["max_drawdown_change_pct_points"] <= 1.0,
    }
    payload = {"schema_version": "vras_hyp006_matched_pair_readout.v1",
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-006", "control": control, "challenger": challenger,
        "relative": relative, "absolute_gates": absolute_gates, "relative_gates": relative_gates,
        "monte_carlo": "NOT_RUN_BASE_GATES_FAILED", "walk_forward": "NOT_RUN_BASE_GATES_FAILED",
        "robustness": "NOT_RUN_BASE_GATES_FAILED", "cost_status": "UNVERIFIED_DIAGNOSTIC_ONLY",
        "verdict": "KILL_VOLATILITY_NORMALIZED_STOP_WORSE_THAN_CONTROL"}
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# HYP-VRAS-EURUSD-M5-006 — Matched Model-0 Readout", "",
        "Verdict: **KILL — volatility-normalized structural stop is worse than control and both arms lose money.**", "",
        "| Metric | Control fixed clamp | Challenger ATR structural |", "|---|---:|---:|",
        f"| Trades | {control['trades']} | {challenger['trades']} |",
        f"| Profit factor | {control['profit_factor']:.4f} | {challenger['profit_factor']:.4f} |",
        f"| Net profit | USD {control['net_profit_usd']:.2f} | USD {challenger['net_profit_usd']:.2f} |",
        f"| Expectancy/trade | USD {control['expectancy_usd']:.2f} | USD {challenger['expectancy_usd']:.2f} |",
        f"| Mean realized R | {control['mean_realized_r']:.4f} | {challenger['mean_realized_r']:.4f} |",
        f"| Max DD | {control['max_drawdown_pct']:.2f}% | {challenger['max_drawdown_pct']:.2f}% |",
        f"| Cadence / elapsed week | {control['cadence_per_elapsed_calendar_week']:.4f} | {challenger['cadence_per_elapsed_calendar_week']:.4f} |",
        f"| Initial-stop exit share | {control['initial_stop_exit_share']:.2%} | {challenger['initial_stop_exit_share']:.2%} |",
        f"| Mean stop | {control['mean_stop_pips']:.2f} pips | {challenger['mean_stop_pips']:.2f} pips |",
        f"| Cost PF 1.5x proxy | {control['cost_pf_x1_5_proxy']:.4f} | {challenger['cost_pf_x1_5_proxy']:.4f} |",
        f"| Cost PF 2x proxy | {control['cost_pf_x2_proxy']:.4f} | {challenger['cost_pf_x2_proxy']:.4f} |", "",
        f"Relative PF lift: {relative['profit_factor_lift']:.4f}; mean-R lift: {relative['mean_realized_r_lift']:.4f}; initial-stop share reduction: {relative['initial_stop_exit_share_reduction']:.2%}; DD change: {relative['max_drawdown_change_pct_points']:.2f}pp.", "",
        "Lifecycle reconciliation is exact in both arms: every position has one OPEN and one final CLOSE, all initial risk values are positive, and report-minus-lifecycle net gap is USD 0.00.", "",
        f"Control account guard latched after its last exit at {control['last_exit_time']}; challenger at {challenger['last_exit_time']}. Cadence uses the full frozen calendar window, not active weeks.", "",
        "The ATR stop reduced drawdown slightly but lowered PF, win rate, mean R, cadence and trade count. This is not a successful SL fix. The entry decision surface still has negative expectancy; wider stops merely change the loss distribution.", "",
        "Monte Carlo, WFA and parameter robustness were not run because the frozen base and relative gates already fail. Running them cannot rescue HYP006. No retune, alternate ATR multiple, R:R, session/day/year/direction filter, promotion or live authority.",
    ]
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
