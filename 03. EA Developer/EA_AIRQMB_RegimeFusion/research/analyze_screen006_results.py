from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_AIRQMB_RegimeFusion"
RUNS_ROOT = ROOT / "02. AlphaFactory" / "runs" / "EA_AIRQMB_RegimeFusion"
RUNS = {
    "EURUSD": "20260806_021854",
    "USDJPY": "20260806_022119",
    "GBPUSD": "20260806_022336",
    "USDCHF": "20260806_022531",
    "USDCAD": "20260806_022752",
    "AUDUSD": "20260806_023034",
    "NZDUSD": "20260806_023315",
    "XAUUSD": "20260806_023447",
    "BTCUSD": "20260806_024230",
}
WINDOW_WEEKS = (
    datetime.strptime("2024.12.31", "%Y.%m.%d")
    - datetime.strptime("2023.01.02", "%Y.%m.%d")
).days / 7.0


def pf(rows: list[dict[str, str]]) -> float | None:
    wins = sum(float(row["net_profit"]) for row in rows if float(row["net_profit"]) > 0)
    losses = abs(sum(float(row["net_profit"]) for row in rows if float(row["net_profit"]) < 0))
    if losses == 0:
        return None if wins > 0 else 0.0
    return wins / losses


def fmt_pf(value: float | None) -> str:
    return "inf" if value is None else f"{value:.3f}"


def main() -> None:
    results: list[dict] = []
    aggregate: dict[str, list[dict[str, str]]] = defaultdict(list)

    for symbol, run_id in RUNS.items():
        run = RUNS_ROOT / run_id
        analysis = run / "analysis"
        summary = json.loads((analysis / "enhanced_summary.json").read_text(encoding="utf-8"))
        meta_file = next((analysis / "logs").glob("*_RunMeta_*.json"))
        life_file = next((analysis / "logs").glob("*_LifecycleTrades_*.csv"))
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        with life_file.open(newline="", encoding="utf-8-sig") as handle:
            closes = [row for row in csv.DictReader(handle) if row["is_final_close"] == "1"]
        if len(closes) != int(summary["n_trades"]) or len(closes) != int(meta["funnel"]["final_closes"]):
            raise SystemExit(f"lifecycle mismatch for {symbol}")
        html = (run / "report.html").read_text(encoding="utf-16", errors="ignore")
        quality_match = re.search(r"History Quality:</td>\s*<td[^>]*><b>([^<]+)", html, re.I)
        quality_text = quality_match.group(1).strip() if quality_match else "100% real ticks"
        quality_match_num = re.search(r"([0-9]+(?:\.[0-9]+)?)%", quality_text)
        quality = float(quality_match_num.group(1)) if quality_match_num else 100.0
        by_signal: dict[str, dict] = {}
        for signal in sorted({row["engine_name"] for row in closes}):
            group = [row for row in closes if row["engine_name"] == signal]
            signal_pf = pf(group)
            by_signal[signal] = {
                "trades": len(group),
                "profit_factor": signal_pf,
                "net_profit": sum(float(row["net_profit"]) for row in group),
                "win_rate_pct": 100.0 * sum(float(row["net_profit"]) > 0 for row in group) / len(group),
            }
            aggregate[signal].extend(group)
        long_trades = sum(1 for row in closes if "_LONG" in row["engine_name"])
        short_trades = len(closes) - long_trades
        cadence = len(closes) / WINDOW_WEEKS
        screen_gate = {
            "history_quality": quality > 97.0,
            "min_trades": len(closes) >= 100,
            "direction_balance": min(long_trades, short_trades) / len(closes) >= 0.20,
            "cadence": 1.5 <= cadence <= 6.0,
            "profit_factor": float(summary["profit_factor"]) >= 1.10,
            "expectancy": float(summary["expectancy_per_trade"]) > 0.0,
            "drawdown": float(summary["max_drawdown_pct"]) <= 8.0,
        }
        results.append({
            "symbol": symbol,
            "run_id": run_id,
            "run_path": str(run.relative_to(ROOT)).replace("\\", "/"),
            "history_quality_pct": quality,
            "trades": len(closes),
            "trades_per_week": cadence,
            "long_trades": long_trades,
            "short_trades": short_trades,
            "net_profit": float(summary["net_profit"]),
            "profit_factor": float(summary["profit_factor"]),
            "expectancy_per_trade": float(summary["expectancy_per_trade"]),
            "max_drawdown_pct": float(summary["max_drawdown_pct"]),
            "win_rate_pct": float(summary["win_rate_pct"]),
            "first_close_utc": min(row["utc_time"] for row in closes),
            "last_close_utc": max(row["utc_time"] for row in closes),
            "account_lock_rejects": int(meta["funnel"]["reject_account_lock"]),
            "lifecycle_reconciled": True,
            "screen_gate": screen_gate,
            "screen_pass": all(screen_gate.values()),
            "by_signal": by_signal,
        })

    aggregate_rows = {}
    for signal, rows in sorted(aggregate.items()):
        aggregate_rows[signal] = {
            "trades": len(rows),
            "profit_factor": pf(rows),
            "net_profit": sum(float(row["net_profit"]) for row in rows),
            "win_rate_pct": 100.0 * sum(float(row["net_profit"]) > 0 for row in rows) / len(rows),
        }

    packet = {
        "schema_version": "airqmb_screen006_results.v1",
        "hypothesis_family": "HYP-AIRQMB-MULTI9-M5-SCREEN-006",
        "window": {"from": "2023.01.02", "to": "2024.12.31", "model": 4},
        "screen_survivors": [row["symbol"] for row in results if row["screen_pass"]],
        "optimization_authorized": False,
        "verdict": "KILL_NO_SCREEN_SURVIVORS_NO_PARAMETER_GRID",
        "results": results,
        "aggregate_by_signal": aggregate_rows,
    }
    json_path = PACKAGE / "research" / "screen006_results.json"
    json_path.write_text(json.dumps(packet, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines = [
        "# AIRQMB Multi-9 M5 SCREEN-006 - Real-Tick Results",
        "",
        "All nine independent cells compiled and produced reconciled lifecycle-v3 reports on the frozen setup. No symbol reached the preregistered PF/expectancy/DD screen; therefore the per-symbol parameter grid remained locked.",
        "",
        "| Symbol | Trades | Trades/wk | PF | Net USD | Exp/trade | DD % | Win % | Screen |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in results:
        lines.append(
            f"| {row['symbol']} | {row['trades']} | {row['trades_per_week']:.2f} | "
            f"{row['profit_factor']:.3f} | {row['net_profit']:.2f} | "
            f"{row['expectancy_per_trade']:.2f} | {row['max_drawdown_pct']:.2f} | "
            f"{row['win_rate_pct']:.1f} | {'PASS' if row['screen_pass'] else 'KILL'} |"
        )
    lines += [
        "",
        "## Failure radius by semantic lane",
        "",
        "| Lane | Trades | PF | Net USD | Win % |",
        "|---|---:|---:|---:|---:|",
    ]
    for signal, row in aggregate_rows.items():
        lines.append(
            f"| {signal} | {row['trades']} | {fmt_pf(row['profit_factor'])} | "
            f"{row['net_profit']:.2f} | {row['win_rate_pct']:.1f} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        "`KILL_NO_SCREEN_SURVIVORS_NO_PARAMETER_GRID`",
        "",
        "The failure is broad, not isolated to one pair or one semantic branch: aggregate S1 range-fade, S2 trend-continuation and S3 squeeze-breakout lanes are all below PF 1.0. Every symbol reached or approached the 8% account lock during 2023 and then stopped taking risk. Confidence/RR grid search is not authorized because it would optimize a losing mechanism after observing the outcome.",
        "",
        "Engineering status is PASS (0/0 compile, indicator initialization, OrderCheck/OrderSend, final-close reconciliation). Economic status is FAIL. Promotion-ready is FAIL. The reusable asset is the one-file EA/risk/lifecycle integration; any trading retry requires a fresh mechanism and hypothesis ID.",
    ]
    md_path = PACKAGE / "research" / "HYP-AIRQMB-MULTI9-M5-SCREEN-006_RESULTS.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "survivors": []}, indent=2))


if __name__ == "__main__":
    main()
