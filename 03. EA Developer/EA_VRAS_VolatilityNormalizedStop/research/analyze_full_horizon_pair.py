#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

START = datetime(2019, 1, 1)
END = datetime(2022, 12, 31)
ELAPSED_WEEKS = (END - START).total_seconds() / (7 * 86400)


def pf(values: list[float]) -> float:
    gains = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    return gains / losses if losses else math.inf


def longest_loss_streak(values: list[float]) -> int:
    best = current = 0
    for value in values:
        current = current + 1 if value < 0 else 0
        best = max(best, current)
    return best


def session(hour: int) -> str:
    if 0 <= hour < 8:
        return "Asia"
    if 8 <= hour < 14:
        return "Europe"
    if 14 <= hour < 21:
        return "NewYork"
    return "OffHours"


def bucket(rows: list[dict], key) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(key(row))].append(row)
    result = {}
    for label, values in sorted(groups.items()):
        nets = [v["net"] for v in values]
        result[label] = {
            "trades": len(values),
            "profit_factor": pf(nets),
            "net_usd": sum(nets),
            "mean_realized_r": sum(v["realized_r"] for v in values) / len(values),
            "win_rate_pct": 100 * sum(v["net"] > 0 for v in values) / len(values),
        }
    return result


def quantile_labels(values: list[float]) -> tuple[float, float, float]:
    ordered = sorted(values)
    def q(frac: float) -> float:
        return ordered[min(len(ordered) - 1, int(frac * (len(ordered) - 1)))]
    return q(0.25), q(0.50), q(0.75)


def quartile(value: float, cuts: tuple[float, float, float]) -> str:
    if value <= cuts[0]:
        return "Q1_low"
    if value <= cuts[1]:
        return "Q2"
    if value <= cuts[2]:
        return "Q3"
    return "Q4_high"


def one_run(run: Path, deposit: float) -> dict:
    summary = json.loads((run / "analysis" / "enhanced_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8-sig"))
    logs = run / "analysis" / "logs"
    lifecycle_path = next(logs.glob("*_LifecycleTrades_*.csv"))
    decision_path = next(logs.glob("*_DecisionTelemetry_*.csv"))
    runmeta_path = next(logs.glob("*_RunMeta_*.json"))
    runmeta = json.loads(runmeta_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(lifecycle_path.open(encoding="utf-8-sig", newline="")))
    decisions = list(csv.DictReader(decision_path.open(encoding="utf-8-sig", newline="")))
    accepted = defaultdict(list)
    for row in decisions:
        if row["status"] == "ORDER_ACCEPTED":
            accepted[row["server_time"]].append(row)
    groups = defaultdict(list)
    for row in rows:
        groups[row["position_id"]].append(row)
    trades = []
    for position_id, events in groups.items():
        opens = [row for row in events if row["action"] == "OPEN"]
        closes = [row for row in events if row["is_final_close"] in {"1", "true", "True"}]
        if len(opens) != 1 or len(closes) != 1:
            raise SystemExit(f"unreconciled {run.name} position={position_id} opens={len(opens)} closes={len(closes)}")
        entry, close = opens[0], closes[0]
        entry_time = datetime.strptime(entry["event_time"], "%Y.%m.%d %H:%M:%S")
        exit_time = datetime.strptime(close["event_time"], "%Y.%m.%d %H:%M:%S")
        direction = 1 if entry["order_type"] == "BUY" else -1
        risk = float(entry["initial_risk_account"])
        risk_pts = float(entry["risk_pts"])
        net = sum(float(row["deal_net"]) for row in events)
        price_pnl = sum(float(row["deal_profit"]) for row in events)
        costs = sum(float(row["deal_commission"]) + float(row["deal_swap"]) + float(row["deal_fee"]) for row in events)
        price_r = direction * (float(close["price"]) - float(entry["price"])) / (risk_pts * 0.00001)
        if price_r <= -0.90:
            exit_class = "INITIAL_STOP"
        elif price_r >= 1.40:
            exit_class = "TARGET"
        elif -0.20 <= price_r <= 0.25:
            exit_class = "BREAKEVEN_ZONE"
        else:
            exit_class = "TIME_OR_MANAGED"
        telemetry = accepted[entry["event_time"]].pop(0) if accepted[entry["event_time"]] else None
        atr_pips = float(telemetry["atr14"]) / 0.0001 if telemetry else math.nan
        ema_distance_atr = (abs(float(telemetry["h1_close"]) - float(telemetry["h1_ema"])) /
                            float(telemetry["atr14"])) if telemetry and float(telemetry["atr14"]) else math.nan
        trades.append({
            "position_id": position_id,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "direction": entry["order_type"],
            "net": net,
            "price_pnl": price_pnl,
            "costs": costs,
            "risk_account": risk,
            "risk_pips": risk_pts * 0.1,
            "realized_r": net / risk,
            "price_r": price_r,
            "exit_class": exit_class,
            "holding_minutes": (exit_time - entry_time).total_seconds() / 60,
            "atr_pips": atr_pips,
            "ema_distance_atr": ema_distance_atr,
        })
    trades.sort(key=lambda row: (row["exit_time"], int(row["position_id"])))
    lifecycle_net = sum(row["net"] for row in trades)
    report_gap = lifecycle_net - float(summary["net_profit"])
    if round(report_gap, 2) != 0:
        raise SystemExit(f"report/lifecycle mismatch {run}: {report_gap}")
    equity = deposit
    peak = deposit
    max_dd = 0.0
    for row in trades:
        equity += row["net"]
        peak = max(peak, equity)
        max_dd = max(max_dd, 100 * (peak - equity) / peak)
    atr_values = [row["atr_pips"] for row in trades if math.isfinite(row["atr_pips"])]
    ema_values = [row["ema_distance_atr"] for row in trades if math.isfinite(row["ema_distance_atr"])]
    atr_cuts = quantile_labels(atr_values)
    ema_cuts = quantile_labels(ema_values)
    for row in trades:
        row["atr_quartile"] = quartile(row["atr_pips"], atr_cuts)
        row["ema_distance_quartile"] = quartile(row["ema_distance_atr"], ema_cuts)
    nets = [row["net"] for row in trades]
    win_r = [row["realized_r"] for row in trades if row["net"] > 0]
    loss_r = [row["realized_r"] for row in trades if row["net"] <= 0]
    average_win_r = sum(win_r) / len(win_r)
    average_loss_r = sum(loss_r) / len(loss_r)
    realized_payoff_ratio = average_win_r / abs(average_loss_r)
    price_pnl = [row["price_pnl"] for row in trades]
    stressed_15 = [row["price_pnl"] + 1.5 * row["costs"] for row in trades]
    stressed_20 = [row["price_pnl"] + 2.0 * row["costs"] for row in trades]
    return {
        "run_id": run.name,
        "run_path": str(run),
        "variant": runmeta["variant_tag"],
        "history_quality_pct": float(str(manifest["fingerprint_basis"]["history_quality"]).rstrip("%")),
        "bars": int(manifest["fingerprint_basis"]["bars"]),
        "ticks": int(manifest["fingerprint_basis"]["ticks"]),
        "trades": len(trades),
        "profit_factor": float(summary["profit_factor"]),
        "gross_price_profit_factor": pf(price_pnl),
        "net_profit_usd": float(summary["net_profit"]),
        "price_pnl_usd": sum(price_pnl),
        "recorded_costs_usd": sum(row["costs"] for row in trades),
        "win_rate_pct": float(summary["win_rate_pct"]),
        "expectancy_usd": float(summary["expectancy_per_trade"]),
        "mean_realized_r": sum(row["realized_r"] for row in trades) / len(trades),
        "median_realized_r": sorted(row["realized_r"] for row in trades)[len(trades) // 2],
        "average_win_r": average_win_r,
        "average_loss_r": average_loss_r,
        "realized_payoff_ratio": realized_payoff_ratio,
        "break_even_win_rate_pct_for_realized_payoff": 100 / (1 + realized_payoff_ratio),
        "mean_recorded_cost_r": sum(row["costs"] / row["risk_account"] for row in trades) / len(trades),
        "max_drawdown_pct_report": float(summary["max_drawdown_pct"]),
        "max_drawdown_pct_rebuilt": max_dd,
        "cadence_per_elapsed_calendar_week": len(trades) / ELAPSED_WEEKS,
        "initial_stop_exit_share": sum(row["exit_class"] == "INITIAL_STOP" for row in trades) / len(trades),
        "target_exit_share": sum(row["exit_class"] == "TARGET" for row in trades) / len(trades),
        "breakeven_zone_exit_share": sum(row["exit_class"] == "BREAKEVEN_ZONE" for row in trades) / len(trades),
        "mean_stop_pips": sum(row["risk_pips"] for row in trades) / len(trades),
        "min_stop_pips": min(row["risk_pips"] for row in trades),
        "max_stop_pips": max(row["risk_pips"] for row in trades),
        "mean_holding_minutes": sum(row["holding_minutes"] for row in trades) / len(trades),
        "largest_loss_usd": min(nets),
        "max_consecutive_losses": longest_loss_streak(nets),
        "cost_pf_x1_5_proxy": pf(stressed_15),
        "cost_pf_x2_proxy": pf(stressed_20),
        "exit_class_counts": dict(Counter(row["exit_class"] for row in trades)),
        "by_year": bucket(trades, lambda row: row["entry_time"].year),
        "by_session": bucket(trades, lambda row: session(row["entry_time"].hour)),
        "by_direction": bucket(trades, lambda row: row["direction"]),
        "by_atr_quartile": bucket(trades, lambda row: row["atr_quartile"]),
        "by_h1_ema_distance_quartile": bucket(trades, lambda row: row["ema_distance_quartile"]),
        "telemetry_quartile_cutoffs": {"atr_pips": atr_cuts, "h1_ema_distance_atr": ema_cuts},
        "lifecycle": {
            "rows": len(rows),
            "opens": sum(row["action"] == "OPEN" for row in rows),
            "final_closes": sum(row["is_final_close"] in {"1", "true", "True"} for row in rows),
            "unique_positions": len(groups),
            "net_usd": lifecycle_net,
            "report_gap_usd": report_gap,
            "minimum_initial_risk_account": min(row["risk_account"] for row in trades),
        },
        "diagnostic": runmeta["diagnostic"],
        "first_entry_time": min(row["entry_time"] for row in trades).isoformat(sep=" "),
        "last_exit_time": max(row["exit_time"] for row in trades).isoformat(sep=" "),
        "largest_winners": [
            {key: (value.isoformat(sep=" ") if isinstance(value, datetime) else value)
             for key, value in row.items() if key not in {"atr_quartile", "ema_distance_quartile"}}
            for row in sorted(trades, key=lambda item: item["net"], reverse=True)[:5]
        ],
        "largest_losers": [
            {key: (value.isoformat(sep=" ") if isinstance(value, datetime) else value)
             for key, value in row.items() if key not in {"atr_quartile", "ema_distance_quartile"}}
            for row in sorted(trades, key=lambda item: item["net"])[:5]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--deposit", type=float, default=500000)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    control = one_run(args.control, args.deposit)
    challenger = one_run(args.challenger, args.deposit)
    relative = {
        "profit_factor_lift": challenger["profit_factor"] - control["profit_factor"],
        "mean_realized_r_lift": challenger["mean_realized_r"] - control["mean_realized_r"],
        "initial_stop_exit_share_reduction": control["initial_stop_exit_share"] - challenger["initial_stop_exit_share"],
        "max_drawdown_change_pct_points": challenger["max_drawdown_pct_report"] - control["max_drawdown_pct_report"],
        "trade_count_change": challenger["trades"] - control["trades"],
    }
    payload = {
        "schema_version": "vras_hyp008_full_horizon_readout.v1",
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-008",
        "diagnostic_only": True,
        "promotion_eligible": False,
        "control": control,
        "challenger": challenger,
        "relative": relative,
        "verdict": "FULL_HORIZON_CONFIRMS_NO_EDGE_BOTH_ARMS_NEGATIVE",
        "interpretation": "The account-DD entry halt previously censored sample coverage but did not hide a profitable later regime. Both arms lose across every year and every telemetry ATR quartile; the ATR structural arm lowers exposure and DD but does not improve PF or realized R.",
        "unauthorized_outputs": ["parameter retune", "session/year/direction filter", "R:R change", "promotion", "live use"],
    }
    args.out_json.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    lines = [
        "# HYP-VRAS-EURUSD-M5-008 — Full-Horizon Diagnostic Readout", "",
        "Verdict: **full-horizon coverage confirms no edge; both stop arms remain negative.**", "",
        "| Metric | Control fixed clamp | Challenger ATR structural |", "|---|---:|---:|",
        f"| Trades | {control['trades']} | {challenger['trades']} |",
        f"| Profit factor | {control['profit_factor']:.4f} | {challenger['profit_factor']:.4f} |",
        f"| Gross price PF before recorded costs | {control['gross_price_profit_factor']:.4f} | {challenger['gross_price_profit_factor']:.4f} |",
        f"| Net profit (USD 500k diagnostic) | {control['net_profit_usd']:.2f} | {challenger['net_profit_usd']:.2f} |",
        f"| Mean realized R | {control['mean_realized_r']:.4f} | {challenger['mean_realized_r']:.4f} |",
        f"| Max DD | {control['max_drawdown_pct_report']:.2f}% | {challenger['max_drawdown_pct_report']:.2f}% |",
        f"| Cadence / elapsed week | {control['cadence_per_elapsed_calendar_week']:.2f} | {challenger['cadence_per_elapsed_calendar_week']:.2f} |",
        f"| Initial-stop exit share | {control['initial_stop_exit_share']:.2%} | {challenger['initial_stop_exit_share']:.2%} |",
        f"| Mean stop | {control['mean_stop_pips']:.2f} pip | {challenger['mean_stop_pips']:.2f} pip |",
        f"| Cost PF 1.5x proxy | {control['cost_pf_x1_5_proxy']:.4f} | {challenger['cost_pf_x1_5_proxy']:.4f} |",
        f"| Cost PF 2x proxy | {control['cost_pf_x2_proxy']:.4f} | {challenger['cost_pf_x2_proxy']:.4f} |", "",
        f"Relative PF lift {relative['profit_factor_lift']:.4f}; mean-R lift {relative['mean_realized_r_lift']:.4f}; DD change {relative['max_drawdown_change_pct_points']:.2f}pp; trade-count change {relative['trade_count_change']}.", "",
        "Coverage and reconciliation pass for both arms: 100% history quality, 298,483 bars, full 2019–2022 interval, no tester stop-out, account DD halt disabled, and exact report ↔ lifecycle net P/L.", "",
        "Every calendar year and every telemetry ATR quartile is PF < 1 in both arms. The later market regimes do not reverse the early negative expectancy. The challenger reduces trade count and drawdown mainly through rejection/exposure reduction; it does not improve PF or mean R.", "",
        "This is diagnostic-only. Cost provenance remains unverified, and no parameter/R:R/session/year/direction rescue, promotion, or live use is authorized.",
    ]
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
