from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[3]
EA_NAME = "EA_SweepCascadeContinuation"
HYPOTHESIS_ID = "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004"
SOURCE_SHA256 = "9C03F4CB913E18B6CF660E48E7ADBD86034B1352A80167C32CC238BA7F7817B3"
WINDOW_START = datetime(2019, 1, 1)
WINDOW_END = datetime(2022, 12, 31)
ELAPSED_WEEKS = (WINDOW_END - WINDOW_START).days / 7.0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def find_one(root: Path, pattern: str) -> Path:
    matches = list((root / "logs").glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {pattern} in {root / 'logs'}, got {len(matches)}")
    return matches[0]


def safe_pf(values: list[float]) -> float:
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def summarize_values(values: list[float]) -> dict[str, float | int]:
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    return {
        "n": len(values),
        "net": round(sum(values), 8),
        "profit_factor": round(safe_pf(values), 8),
        "win_rate_pct": round(100.0 * len(wins) / len(values), 8) if values else 0.0,
        "mean": round(mean(values), 8) if values else 0.0,
        "median": round(median(values), 8) if values else 0.0,
        "average_win": round(mean(wins), 8) if wins else 0.0,
        "average_loss": round(mean(losses), 8) if losses else 0.0,
    }


def parse_run(run_dir: Path) -> tuple[dict, list[dict]]:
    manifest_path = run_dir / "run_manifest.json"
    report_summary_path = run_dir / "analysis" / "enhanced_summary.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    report_summary = json.loads(report_summary_path.read_text(encoding="utf-8-sig"))
    lifecycle_path = find_one(run_dir, "*_LifecycleTrades_*.csv")
    runmeta_path = find_one(run_dir, "*_RunMeta_*.json")
    decision_path = find_one(run_dir, "*_DecisionTelemetry_*.csv")
    runmeta = json.loads(runmeta_path.read_text(encoding="utf-8-sig"))
    with decision_path.open("r", encoding="utf-8-sig", newline="") as handle:
        decisions = list(csv.DictReader(handle))

    positions: dict[str, dict] = {}
    with lifecycle_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        position_id = row["position_id"]
        net = float(row["deal_net"])
        if row["action"] == "OPEN":
            if position_id in positions:
                raise RuntimeError(f"Duplicate OPEN for position {position_id}")
            positions[position_id] = {
                "position_id": position_id,
                "open_time": row["event_time"],
                "close_time": None,
                "direction": row["order_type"],
                "volume": float(row["volume"]),
                "entry": float(row["price"]),
                "exit": None,
                "risk_points": float(row["risk_pts"]),
                "initial_risk_account": float(row["initial_risk_account"]),
                "net": net,
                "closed": False,
            }
        elif row["action"] == "CLOSE":
            position = positions.get(position_id)
            if position is None:
                raise RuntimeError(f"CLOSE without OPEN for position {position_id}")
            position["close_time"] = row["event_time"]
            position["exit"] = float(row["price"])
            position["net"] += net
            position["closed"] = row["is_final_close"] == "1"
        else:
            raise RuntimeError(f"Unknown lifecycle action {row['action']}")

    trades = list(positions.values())
    recovered_risk_rows = 0
    for trade in trades:
        open_time = datetime.strptime(trade["open_time"], "%Y.%m.%d %H:%M:%S")
        direction = 1 if trade["direction"] == "BUY" else -1
        candidates = []
        for row in decisions:
            if row["status"] != "ORDER_ACCEPTED" or int(row["direction"]) != direction:
                continue
            if abs(float(row["entry"]) - trade["entry"]) > 0.000001:
                continue
            decision_time = datetime.strptime(row["server_time"], "%Y.%m.%d %H:%M:%S")
            lag_seconds = (open_time - decision_time).total_seconds()
            if 0 <= lag_seconds <= 900 and float(row["stop"]) > 0:
                candidates.append((decision_time, row))
        if len(candidates) != 1:
            raise RuntimeError(
                f"Could not uniquely bind decision geometry for position "
                f"{trade['position_id']}: {len(candidates)} candidates"
            )
        decision_time, row = candidates[0]
        trade["decision_time"] = decision_time.strftime("%Y.%m.%d %H:%M:%S")
        trade["planned_stop"] = float(row["stop"])
        trade["planned_target"] = float(row["target"])
        if trade["initial_risk_account"] <= 0:
            trade["risk_points"] = abs(trade["entry"] - float(row["stop"])) / 0.00001
            trade["initial_risk_account"] = (
                trade["risk_points"] * trade["volume"]
            )
            recovered_risk_rows += 1
        risk = trade["initial_risk_account"]
        trade["realized_r"] = trade["net"] / risk
        trade["close_year"] = int(trade["close_time"][:4]) if trade["close_time"] else None

    open_count = sum(row["action"] == "OPEN" for row in rows)
    close_count = sum(row["action"] == "CLOSE" for row in rows)
    native_values = [trade["net"] for trade in trades if trade["closed"]]
    r_values = [trade["realized_r"] for trade in trades if trade["closed"]]

    by_year: dict[str, dict] = {}
    for year in range(2019, 2023):
        values = [trade["net"] for trade in trades if trade["close_year"] == year]
        by_year[str(year)] = summarize_values(values)
    by_direction: dict[str, dict] = {}
    for direction in ("BUY", "SELL"):
        values = [trade["net"] for trade in trades if trade["direction"] == direction]
        by_direction[direction] = summarize_values(values)

    stress: dict[str, dict] = {}
    for pips in (0.5, 1.5, 2.25, 3.0):
        stressed = [
            trade["net"] - pips * trade["volume"] * 10.0
            for trade in trades
            if trade["closed"]
        ]
        stress[f"{pips:g}_pips"] = summarize_values(stressed)

    decision_status_counts: dict[str, int] = {}
    for row in decisions:
        key = f"{row['event']}::{row['status']}"
        decision_status_counts[key] = decision_status_counts.get(key, 0) + 1

    lifecycle_net = round(sum(native_values), 8)
    report_net = round(float(report_summary["net_profit"]), 8)
    report_n = int(report_summary["n_trades"])
    report_pf = float(report_summary["profit_factor"])
    valid = (
        manifest["hypothesis_id"] == HYPOTHESIS_ID
        and manifest["source_sha256"] == SOURCE_SHA256
        and int(runmeta["diagnostic"]["bars_seen"]) >= 298_000
        and open_count == close_count
        and all(trade["closed"] for trade in trades)
        and report_n == len(trades)
        and abs(report_net - lifecycle_net) <= 0.01
        and abs(report_pf - safe_pf(native_values)) <= 1e-6
        and trades[-1]["close_time"][:7] == "2022.12"
    )

    result = {
        "run_id": manifest["run_id"],
        "run_role": manifest["run_role"],
        "manifest_path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "manifest_sha256": sha256(manifest_path),
        "report_path": str((run_dir / "report.html").relative_to(ROOT)).replace("\\", "/"),
        "report_sha256": sha256(run_dir / "report.html"),
        "source_sha256": manifest["source_sha256"],
        "validity": {
            "valid": valid,
            "runmeta_bars": int(runmeta["diagnostic"]["bars_seen"]),
            "lifecycle_open": open_count,
            "lifecycle_close": close_count,
            "last_close_time": trades[-1]["close_time"],
            "report_trade_count_reconciled": report_n == len(trades),
            "report_net_reconciled": abs(report_net - lifecycle_net) <= 0.01,
            "report_pf_reconciled": abs(report_pf - safe_pf(native_values)) <= 1e-6,
        },
        "native": summarize_values(native_values),
        "realized_r": summarize_values(r_values),
        "max_drawdown_pct": round(float(report_summary["max_drawdown_pct"]), 8),
        "cadence_per_elapsed_week": round(len(trades) / ELAPSED_WEEKS, 8),
        "by_year": by_year,
        "by_direction": by_direction,
        "fixed_round_trip_stress": stress,
        "runmeta_diagnostic": runmeta["diagnostic"],
        "risk_geometry_rows_recovered_from_decision_telemetry": recovered_risk_rows,
        "decision_status_counts": decision_status_counts,
    }
    return result, trades


def write_trades(path: Path, trades: list[dict]) -> None:
    fieldnames = [
        "position_id",
        "open_time",
        "close_time",
        "decision_time",
        "direction",
        "volume",
        "entry",
        "exit",
        "planned_stop",
        "planned_target",
        "risk_points",
        "initial_risk_account",
        "net",
        "realized_r",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow({key: trade[key] for key in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-run", required=True)
    parser.add_argument("--challenger-run", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    run_root = ROOT / "02. AlphaFactory" / "runs" / EA_NAME
    control, control_trades = parse_run(run_root / args.control_run)
    challenger, challenger_trades = parse_run(run_root / args.challenger_run)
    if control["run_role"] != "control" or challenger["run_role"] != "challenger":
        raise RuntimeError("Matched run roles are incorrect")

    c_native = control["native"]
    h_native = challenger["native"]
    c_r = control["realized_r"]
    h_r = challenger["realized_r"]
    years_pf_positive = sum(
        challenger["by_year"][str(year)]["profit_factor"] > 1.0
        for year in range(2019, 2023)
    )
    gates = {
        "valid_matched_pair": control["validity"]["valid"] and challenger["validity"]["valid"],
        "challenger_n_gte_418": h_native["n"] >= 418,
        "challenger_cadence_2_to_5": 2.0 <= challenger["cadence_per_elapsed_week"] <= 5.0,
        "challenger_pf_gte_1_30": h_native["profit_factor"] >= 1.30,
        "challenger_dd_lte_6pct": challenger["max_drawdown_pct"] <= 6.0,
        "challenger_mean_r_gt_0": h_r["mean"] > 0.0,
        "three_of_four_years_pf_gt_1": years_pf_positive >= 3,
        "stress_1_5_pips_pf_gte_1_25": (
            challenger["fixed_round_trip_stress"]["1.5_pips"]["profit_factor"] >= 1.25
        ),
        "stress_2_25_pips_pf_gte_1_00": (
            challenger["fixed_round_trip_stress"]["2.25_pips"]["profit_factor"] >= 1.00
        ),
        "pf_lift_gte_0_10": h_native["profit_factor"] - c_native["profit_factor"] >= 0.10,
        "mean_r_lift_gte_0_05": h_r["mean"] - c_r["mean"] >= 0.05,
        "dd_change_lte_plus_1pp": (
            challenger["max_drawdown_pct"] - control["max_drawdown_pct"] <= 1.0
        ),
    }
    verdict = (
        "KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY"
        if gates["valid_matched_pair"] and not all(gates.values())
        else "PARK_INVALID_MICRO_RISK_DIAGNOSTIC"
        if not gates["valid_matched_pair"]
        else "PASS_DIAGNOSTIC_ONLY_NO_PROMOTION"
    )
    payload = {
        "schema_version": "scc_hyp004_pair_analysis.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_sha256": SOURCE_SHA256,
        "window": {"from": "2019.01.01", "to": "2022.12.31", "elapsed_weeks": ELAPSED_WEEKS},
        "risk_scale_pct": 0.01,
        "scale_note": "Dollar P/L is scale-diagnostic only; signal, PF and R decide.",
        "control": control,
        "challenger": challenger,
        "comparison": {
            "profit_factor_delta": round(
                h_native["profit_factor"] - c_native["profit_factor"], 8
            ),
            "mean_realized_r_delta": round(h_r["mean"] - c_r["mean"], 8),
            "max_drawdown_pct_point_delta": round(
                challenger["max_drawdown_pct"] - control["max_drawdown_pct"], 8
            ),
            "trade_count_delta": h_native["n"] - c_native["n"],
        },
        "gates": gates,
        "gates_passed": sum(gates.values()),
        "gates_total": len(gates),
        "verdict": verdict,
        "promotion_eligible": False,
        "post_hoc_rescue_authorized": False,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_trades(out_dir / "control_trades.csv", control_trades)
    write_trades(out_dir / "challenger_trades.csv", challenger_trades)
    result_path = out_dir / "pair_analysis.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": "scc_hyp004_analysis_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "analysis_script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "analysis_script_sha256": sha256(Path(__file__)),
        "pair_analysis_sha256": sha256(result_path),
        "control_trades_sha256": sha256(out_dir / "control_trades.csv"),
        "challenger_trades_sha256": sha256(out_dir / "challenger_trades.csv"),
        "verdict": verdict,
    }
    (out_dir / "analysis_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
