#!/usr/bin/env python3
"""Build the frozen HYP-004 matched-pair readout from AlphaFactory artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_ROOT = ROOT / "02. AlphaFactory" / "analysis"
sys.path.insert(0, str(ANALYSIS_ROOT))
from quant_analyzer import parse_deals  # noqa: E402


FULL_FROM = datetime(2023, 1, 3)
FULL_TO = datetime(2026, 6, 30)
START_EQUITY = 100_000.0
PIP_VALUE_USD_PER_LOT = 10.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def safe_float(value: Any) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def stats(trades: Iterable[dict[str, Any]], elapsed_weeks: float) -> dict[str, Any]:
    rows = list(trades)
    profits = [float(row["net_usd"]) for row in rows]
    gross_profit = sum(value for value in profits if value > 0)
    gross_loss = -sum(value for value in profits if value < 0)
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.99 if gross_profit > 0 else 0.0)
    equity = START_EQUITY
    peak = START_EQUITY
    max_dd = 0.0
    for value in profits:
        equity += value
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    stop_count = sum(row["exit_class"] == "STOP" for row in rows)
    return {
        "trades": len(rows),
        "wins": sum(value > 0 for value in profits),
        "win_rate_pct": round(100.0 * sum(value > 0 for value in profits) / len(rows), 6) if rows else 0.0,
        "net_usd": round(sum(profits), 6),
        "profit_factor": round(pf, 9),
        "expectancy_usd": round(sum(profits) / len(rows), 6) if rows else 0.0,
        "mean_realized_r": round(sum(float(row["realized_r"]) for row in rows) / len(rows), 9) if rows else 0.0,
        "max_drawdown_pct": round(max_dd, 9),
        "trades_per_elapsed_week": round(len(rows) / elapsed_weeks, 9) if elapsed_weeks > 0 else 0.0,
        "stop_exits": stop_count,
        "stop_exit_share": round(stop_count / len(rows), 9) if rows else 0.0,
    }


def cost_stress(trades: list[dict[str, Any]], multiplier: float) -> dict[str, Any]:
    # The tester report already contains its broker spread/commission. To model
    # total cost at 1.5x/2x, add only the incremental 0.5x/1.0x of the EA's
    # telemetry cost estimate. This remains an unverified diagnostic proxy.
    incremental_scale = multiplier - 1.0
    adjusted: list[float] = []
    total_incremental = 0.0
    for row in trades:
        full_estimated_cost = (
            float(row["estimated_cost_pips"])
            * PIP_VALUE_USD_PER_LOT
            * float(row["volume"])
        )
        incremental = incremental_scale * full_estimated_cost
        total_incremental += incremental
        adjusted.append(float(row["net_usd"]) - incremental)
    gross_profit = sum(value for value in adjusted if value > 0)
    gross_loss = -sum(value for value in adjusted if value < 0)
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.99 if gross_profit > 0 else 0.0)
    return {
        "multiplier": multiplier,
        "profit_factor": round(pf, 9),
        "net_usd": round(sum(adjusted), 6),
        "incremental_cost_usd": round(total_incremental, 6),
        "status": "UNVERIFIED_DIAGNOSTIC_PROXY",
    }


def load_run(run_dir: Path) -> dict[str, Any]:
    logs = run_dir / "logs"
    lifecycle_path = next(logs.glob("*_LifecycleTrades_*.csv"))
    decision_path = next(logs.glob("*_DecisionTelemetry_*.csv"))
    runmeta_path = next(logs.glob("*_RunMeta_*.json"))
    report_path = run_dir / "report.html"
    summary_path = run_dir / "analysis" / "enhanced_summary.json"
    manifest_path = run_dir / "run_manifest.json"

    report_deals = {int(deal.deal_id): deal for deal in parse_deals(report_path) if deal.deal_id is not None}
    accepted_by_key: dict[tuple[datetime, float], list[dict[str, str]]] = defaultdict(list)
    status_counts: Counter[str] = Counter()
    rejected_rows: list[dict[str, str]] = []
    with decision_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            status_counts[row["status"]] += 1
            when = parse_time(row["server_time"])
            if row["status"] == "ORDER_ACCEPTED":
                accepted_by_key[(when, round(safe_float(row["entry"]), 5))].append(row)
            elif row["status"] == "PATH_CONFIRM_REJECT":
                rejected_rows.append(row)

    positions: dict[str, dict[str, Any]] = {}
    with lifecycle_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            position_id = row["position_id"]
            item = positions.setdefault(
                position_id,
                {
                    "position_id": int(position_id),
                    "net_usd": 0.0,
                    "initial_risk_account": safe_float(row["initial_risk_account"]),
                    "volume": safe_float(row["volume"]),
                },
            )
            item["net_usd"] += safe_float(row["deal_net"])
            if row["action"] == "OPEN":
                item["open_time"] = parse_time(row["event_time"])
                item["entry_price"] = safe_float(row["price"])
                item["direction"] = 1 if row["order_type"] == "BUY" else -1
                item["volume"] = safe_float(row["volume"])
            elif row["action"] == "CLOSE" and row["is_final_close"] == "1":
                item["close_time"] = parse_time(row["event_time"])
                item["exit_price"] = safe_float(row["price"])
                deal = report_deals.get(int(row["deal"]))
                item["exit_comment"] = (deal.comment if deal else "").strip()

    trades: list[dict[str, Any]] = []
    unmatched = 0
    for item in positions.values():
        if "open_time" not in item or "close_time" not in item:
            continue
        key = (item["open_time"], round(item["entry_price"], 5))
        candidates = accepted_by_key.get(key, [])
        if len(candidates) != 1:
            unmatched += 1
            decision: dict[str, str] = {}
        else:
            decision = candidates[0]
        event = decision.get("event", "UNMATCHED")
        exit_comment = item.get("exit_comment", "")
        if exit_comment.startswith("sl "):
            exit_class = "STOP"
        elif exit_comment.startswith("tp "):
            exit_class = "TARGET"
        else:
            exit_class = "SAFETY_OR_TIME"
        risk = float(item["initial_risk_account"])
        item.update(
            {
                "event": event,
                "branch": "TREND" if event.startswith("TREND_") else "RANGE" if event.startswith("RANGE_") else "UNKNOWN",
                "estimated_cost_pips": safe_float(decision.get("estimated_cost_pips")),
                "stop_price": safe_float(decision.get("stop")),
                "target_price": safe_float(decision.get("target")),
                "realized_r": float(item["net_usd"]) / risk if risk > 0 else 0.0,
                "exit_class": exit_class,
            }
        )
        trades.append(item)
    trades.sort(key=lambda row: row["close_time"])

    runmeta = read_json(runmeta_path)
    enhanced = read_json(summary_path)
    manifest = read_json(manifest_path)
    lifecycle_net = round(sum(float(row["net_usd"]) for row in trades), 6)
    return {
        "run_id": run_dir.name,
        "run_dir": run_dir,
        "variant": runmeta["variant_tag"],
        "trades": trades,
        "rejected_rows": rejected_rows,
        "status_counts": dict(status_counts),
        "runmeta": runmeta,
        "enhanced": enhanced,
        "manifest": manifest,
        "paths": {
            "report": report_path,
            "manifest": manifest_path,
            "lifecycle": lifecycle_path,
            "decision": decision_path,
            "runmeta": runmeta_path,
        },
        "reconciliation": {
            "lifecycle_positions": len(trades),
            "report_trades": int(enhanced["n_trades"]),
            "lifecycle_net_usd": lifecycle_net,
            "report_net_usd": round(float(enhanced["net_profit"]), 6),
            "net_gap_usd": round(lifecycle_net - float(enhanced["net_profit"]), 6),
            "unmatched_accepted_entries": unmatched,
            "status": "PASS_EXACT" if len(trades) == int(enhanced["n_trades"]) and abs(lifecycle_net - float(enhanced["net_profit"])) < 0.01 and unmatched == 0 else "FAIL",
        },
    }


def relative_metrics(control_stats: dict[str, Any], challenger_stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "profit_factor_lift": round(challenger_stats["profit_factor"] - control_stats["profit_factor"], 9),
        "mean_realized_r_lift": round(challenger_stats["mean_realized_r"] - control_stats["mean_realized_r"], 9),
        "stop_exit_share_reduction": round(control_stats["stop_exit_share"] - challenger_stats["stop_exit_share"], 9),
    }


def choose_chart_cases(challenger: dict[str, Any], bars_path: Path) -> list[dict[str, Any]]:
    trend_winners = [row for row in challenger["trades"] if row["branch"] == "TREND" and row["net_usd"] > 0]
    trend_winners.sort(key=lambda row: row["realized_r"])
    accepted = trend_winners[len(trend_winners) // 2]

    rejected = next(
        row for row in challenger["rejected_rows"]
        if row["event"] in {"PATH_EXTREME_BREAK_REJECT", "PATH_MEAN_STACK_REJECT", "PATH_M15_REJECT"}
        and safe_float(row["planned_stop"] if "planned_stop" in row else row.get("stop")) != 0.0
        and safe_float(row["session_vwap"]) != 0.0
        and safe_float(row["anchored_vwap"]) != 0.0
    )
    rejected_time = parse_time(rejected["server_time"])
    minute = pd.read_parquet(
        bars_path,
        columns=["time_server", "open", "high", "low", "close"],
        filters=[("time_server", ">=", rejected_time - timedelta(minutes=15)),
                 ("time_server", "<=", rejected_time + timedelta(hours=3, minutes=10))],
    )
    minute["time_server"] = pd.to_datetime(minute["time_server"])
    m5 = (
        minute.set_index("time_server")
        .sort_index()
        .resample("5min", label="left", closed="left")
        .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
        .dropna()
    )
    decision_bar = rejected_time - timedelta(minutes=5)
    observation_end = rejected_time + timedelta(hours=3)
    entry_price = float(m5.loc[decision_bar, "close"])
    exit_price = float(m5.loc[observation_end - timedelta(minutes=5), "close"])
    direction = 1 if "LONG" in rejected["event"] else -1
    stop = safe_float(rejected["stop"])
    target = entry_price + direction * 1.8 * abs(entry_price - stop)

    return [
        {
            "case_id": f"VRAS-004-ACCEPT-P{accepted['position_id']}",
            "position_id": accepted["position_id"],
            "case_kind": "TRADE",
            "telemetry_status": "ORDER_ACCEPTED",
            "event": accepted["event"],
            "direction": accepted["direction"],
            "entry_time_server": accepted["open_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time_server": accepted["close_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": accepted["entry_price"],
            "exit_price": accepted["exit_price"],
            "stop_price": accepted["stop_price"],
            "target_price": accepted["target_price"],
            "net_R": accepted["realized_r"],
            "net_usd": accepted["net_usd"],
            "exit_class": accepted["exit_class"],
        },
        {
            "case_id": "VRAS-004-REJECT-EXTREME",
            "position_id": 0,
            "case_kind": "REJECTED_PATH",
            "telemetry_status": "PATH_CONFIRM_REJECT",
            "event": rejected["event"],
            "direction": direction,
            "entry_time_server": rejected_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time_server": observation_end.strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "stop_price": stop,
            "target_price": target,
            "net_R": 0.0,
            "net_usd": 0.0,
            "exit_class": "NOT_TRADED",
        },
    ]


def choose_delivery_cases(challenger: dict[str, Any]) -> list[dict[str, Any]]:
    winners = sorted(
        (row for row in challenger["trades"] if row["net_usd"] > 0),
        key=lambda row: row["realized_r"],
    )
    losers = sorted(
        (row for row in challenger["trades"] if row["net_usd"] < 0),
        key=lambda row: row["realized_r"],
    )
    selected = [
        (winners[len(winners) // 2], "winner_median", "WIN"),
        (winners[-1], "winner_tail", "WIN"),
        (losers[len(losers) // 2], "loser_median", "LOSS"),
        (losers[0], "loser_tail", "LOSS"),
    ]
    rows: list[dict[str, Any]] = []
    for index, (trade, label, reason) in enumerate(selected, 1):
        rows.append(
            {
                "case_id": f"VRAS-004-D{index:02d}-P{trade['position_id']}",
                # The renderer is explicitly configured with time_col=time_server;
                # its generic case schema retains the historical *_utc field names.
                "entry_time_utc": trade["open_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "direction": trade["direction"],
                "entry": trade["entry_price"],
                "sl": trade["stop_price"],
                "tp": trade["target_price"],
                "exit_time_utc": trade["close_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "exit": trade["exit_price"],
                "reason": reason,
                "label": label,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--out-cases", type=Path, required=True)
    parser.add_argument("--out-delivery-cases", type=Path, required=True)
    args = parser.parse_args()

    control = load_run(args.control.resolve())
    challenger = load_run(args.challenger.resolve())
    elapsed_weeks = (FULL_TO - FULL_FROM).total_seconds() / (7 * 86400)
    control_stats = stats(control["trades"], elapsed_weeks)
    challenger_stats = stats(challenger["trades"], elapsed_weeks)
    common_end = control["trades"][-1]["close_time"]
    common_weeks = (common_end - FULL_FROM).total_seconds() / (7 * 86400)
    common_control = stats([row for row in control["trades"] if row["close_time"] <= common_end], common_weeks)
    common_challenger = stats([row for row in challenger["trades"] if row["close_time"] <= common_end], common_weeks)

    for loaded, aggregate in ((control, control_stats), (challenger, challenger_stats)):
        aggregate["by_branch"] = {
            branch: stats([row for row in loaded["trades"] if row["branch"] == branch], elapsed_weeks)
            for branch in ("RANGE", "TREND")
        }
        aggregate["by_year"] = {
            str(year): stats([row for row in loaded["trades"] if row["close_time"].year == year], elapsed_weeks)
            for year in range(2023, 2027)
        }
        aggregate["by_direction"] = {
            direction: stats(
                [row for row in loaded["trades"] if row["direction"] == direction_value],
                elapsed_weeks,
            )
            for direction, direction_value in (("LONG", 1), ("SHORT", -1))
        }
        aggregate["by_exit_class"] = {
            exit_class: stats(
                [row for row in loaded["trades"] if row["exit_class"] == exit_class],
                elapsed_weeks,
            )
            for exit_class in ("STOP", "TARGET", "SAFETY_OR_TIME")
        }
        aggregate["cost_stress_x1_5"] = cost_stress(loaded["trades"], 1.5)
        aggregate["cost_stress_x2"] = cost_stress(loaded["trades"], 2.0)

    challenger_validation = read_json(challenger["run_dir"] / "analysis" / "validation_summary.json")
    challenger_mc = read_json(challenger["run_dir"] / "analysis" / "monte_carlo_results.json")
    challenger_robustness = read_json(challenger["run_dir"] / "analysis" / "robustness_results.json")
    challenger_wfa = read_json(challenger["run_dir"] / "analysis" / "wfa_results.json")
    rel = relative_metrics(control_stats, challenger_stats)
    absolute_gates = {
        "trades_gte_350": challenger_stats["trades"] >= 350,
        "cadence_2_to_5_per_week": 2.0 <= challenger_stats["trades_per_elapsed_week"] <= 5.0,
        "profit_factor_gte_1_30": challenger_stats["profit_factor"] >= 1.30,
        "positive_expectancy": challenger_stats["expectancy_usd"] > 0,
        "max_drawdown_lte_6_pct": challenger_stats["max_drawdown_pct"] <= 6.0,
        "cost_x1_5_pf_gte_1_25": challenger_stats["cost_stress_x1_5"]["profit_factor"] >= 1.25,
        "cost_x2_pf_gte_1_00": challenger_stats["cost_stress_x2"]["profit_factor"] >= 1.0,
        "monte_carlo_p95_dd_lte_6_pct": safe_float(challenger_mc["max_drawdown_pct"]["p95"]) <= 6.0,
    }
    relative_gates = {
        "profit_factor_lift_gte_0_15": rel["profit_factor_lift"] >= 0.15,
        "mean_r_lift_gte_0_10": rel["mean_realized_r_lift"] >= 0.10,
        "stop_share_reduction_gte_10pp": rel["stop_exit_share_reduction"] >= 0.10,
    }
    funnel = challenger["runmeta"]["diagnostic"]
    result = {
        "schema_version": "vras_hyp004_matched_pair_readout.v1",
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-004",
        "window": {"from": "2023.01.03", "to": "2026.06.30", "elapsed_weeks": elapsed_weeks},
        "control": {"run_id": control["run_id"], "metrics": control_stats, "reconciliation": control["reconciliation"], "status_counts": control["status_counts"]},
        "challenger": {"run_id": challenger["run_id"], "metrics": challenger_stats, "reconciliation": challenger["reconciliation"], "status_counts": challenger["status_counts"]},
        "path_funnel": {
            "candidates_armed": funnel["path_candidates_armed"],
            "confirmations_passed": funnel["path_confirmations_passed"],
            "confirmations_rejected": funnel["path_confirmations_rejected"],
            "confirmations_expired": funnel["path_confirmations_expired"],
            "pass_rate": round(funnel["path_confirmations_passed"] / funnel["path_candidates_armed"], 9),
            "opened_trend_positions": funnel["trend_long_entries"] + funnel["trend_short_entries"],
            "raw_to_open_rate": round((funnel["trend_long_entries"] + funnel["trend_short_entries"]) / funnel["path_candidates_armed"], 9),
        },
        "relative_full_window": rel,
        "causal_diagnostics": {
            "winning_exit_classes": dict(Counter(row["exit_class"] for row in challenger["trades"] if row["net_usd"] > 0)),
            "losing_exit_classes": dict(Counter(row["exit_class"] for row in challenger["trades"] if row["net_usd"] < 0)),
            "winning_branches": dict(Counter(row["branch"] for row in challenger["trades"] if row["net_usd"] > 0)),
            "losing_branches": dict(Counter(row["branch"] for row in challenger["trades"] if row["net_usd"] < 0)),
            "logic_conflicts": {
                "path_arm_while_exposed": challenger["status_counts"].get("PATH_ARM_EXPOSURE_REJECT", 0),
                "exposure_guard_rejections": challenger["status_counts"].get("EXPOSURE_REJECT", 0),
                "interpretation": "Expected serialized state/exposure behavior; no evidence of branch leakage or duplicate exposure.",
            },
        },
        "common_horizon": {
            "through": common_end.isoformat(),
            "control": common_control,
            "challenger": common_challenger,
            "relative": relative_metrics(common_control, common_challenger),
            "note": "Diagnostic only: control stopped opening after the account-DD guard latched; frozen gates use the full window.",
        },
        "validation": {
            "absolute_gates": absolute_gates,
            "relative_gates": relative_gates,
            "absolute_passed": sum(absolute_gates.values()),
            "absolute_total": len(absolute_gates),
            "relative_passed": sum(relative_gates.values()),
            "relative_total": len(relative_gates),
            "unified_verdict": challenger_validation.get("verdict"),
            "robustness_pass_rate_pct": challenger_robustness["summary"]["pass_rate"],
            "wfa_oos_profitable_ratio": challenger_wfa["summary"]["oos_profitable_ratio"],
            "monte_carlo_p95_dd_pct": challenger_mc["max_drawdown_pct"]["p95"],
        },
        "limitations": [
            "Static news guard disabled in both arms because its calendar ends in 2022.",
            "Cost provenance and independent slippage reconciliation are unverified.",
            "Cost stress is an incremental telemetry-based diagnostic proxy, not promotion evidence.",
            "AlphaFactory WFA/robustness outputs are diagnostic fixed-parameter/trade-PnL proxies.",
        ],
        "verdict": "KILL_PATH_CONFIRMATION_NO_INDEPENDENT_EDGE",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    md = f"""# HYP-004 matched-pair readout

Verdict: **KILL_PATH_CONFIRMATION_NO_INDEPENDENT_EDGE**.

| Metric | Control | Challenger | Frozen gate |
|---|---:|---:|---:|
| Trades | {control_stats['trades']} | {challenger_stats['trades']} | >=350 |
| Trades / elapsed week | {control_stats['trades_per_elapsed_week']:.3f} | {challenger_stats['trades_per_elapsed_week']:.3f} | 2.0-5.0 |
| Profit factor | {control_stats['profit_factor']:.4f} | {challenger_stats['profit_factor']:.4f} | >=1.30 |
| Net USD | {control_stats['net_usd']:.2f} | {challenger_stats['net_usd']:.2f} | positive |
| Mean realized R | {control_stats['mean_realized_r']:.4f} | {challenger_stats['mean_realized_r']:.4f} | lift >=0.10R |
| Stop-exit share | {100*control_stats['stop_exit_share']:.2f}% | {100*challenger_stats['stop_exit_share']:.2f}% | reduction >=10pp |
| Max DD | {control_stats['max_drawdown_pct']:.2f}% | {challenger_stats['max_drawdown_pct']:.2f}% | <=6% |
| Cost x1.5 PF proxy | {control_stats['cost_stress_x1_5']['profit_factor']:.4f} | {challenger_stats['cost_stress_x1_5']['profit_factor']:.4f} | >=1.25 |
| Cost x2 PF proxy | {control_stats['cost_stress_x2']['profit_factor']:.4f} | {challenger_stats['cost_stress_x2']['profit_factor']:.4f} | >=1.00 |

The treatment armed {funnel['path_candidates_armed']} raw Trend candidates,
passed {funnel['path_confirmations_passed']} ({100*result['path_funnel']['pass_rate']:.2f}%),
and opened {result['path_funnel']['opened_trend_positions']} Trend positions
({100*result['path_funnel']['raw_to_open_rate']:.2f}% raw-to-open). It reduced
drawdown and dollar loss, but PF lift was only {rel['profit_factor_lift']:.4f},
mean-R lift {rel['mean_realized_r_lift']:+.4f}R, and stop-share reduction
{100*rel['stop_exit_share_reduction']:+.2f}pp. All three relative gates failed.

The challenger also failed the necessary absolute trade-count, cadence, PF,
expectancy, cost-stress and Monte-Carlo P95 DD gates. Robustness passed
{challenger_robustness['summary']['passed']}/{challenger_robustness['summary']['total']};
diagnostic fixed-parameter OOS slices were profitable in
{challenger_wfa['summary']['oos_profitable_windows']}/{challenger_wfa['n_windows']} windows.

Control report/lifecycle reconciliation: {control['reconciliation']['status']}.
Challenger report/lifecycle reconciliation: {challenger['reconciliation']['status']}.
Both arms remain diagnostic-only because news, cost and independent execution
provenance are not promotion-grade.
"""
    args.out_md.write_text(md, encoding="utf-8")

    cases = choose_chart_cases(challenger, args.bars.resolve())
    with args.out_cases.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cases[0].keys()))
        writer.writeheader()
        writer.writerows(cases)

    delivery_cases = choose_delivery_cases(challenger)
    with args.out_delivery_cases.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(delivery_cases[0].keys()))
        writer.writeheader()
        writer.writerows(delivery_cases)

    print(json.dumps({"status": "HYP004_READOUT_OK", "out_json": str(args.out_json), "out_md": str(args.out_md), "cases": str(args.out_cases), "delivery_cases": str(args.out_delivery_cases), "verdict": result["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
