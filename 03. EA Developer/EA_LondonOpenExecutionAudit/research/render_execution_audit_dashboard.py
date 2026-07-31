from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCENARIOS = {
    "EURUSD_MIDDAY_CONT": {"entry_min": 8 * 60 + 31, "entry_max": 8 * 60 + 31, "exit_min": 12 * 60},
    "GBPUSD_MIDDAY_REV": {"entry_min": 8 * 60 + 31, "entry_max": 8 * 60 + 31, "exit_min": 12 * 60},
    "GBPUSD_LATE_FIX_REV": {"entry_min": 15 * 60 + 30, "entry_max": 15 * 60 + 59, "exit_min": 16 * 60},
    "GBPUSD_FULL_SESSION_REV": {"entry_min": 8 * 60 + 31, "entry_max": 8 * 60 + 31, "exit_min": 16 * 60 + 30},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def one(path: Path, pattern: str) -> Path:
    matches = list((path / "logs").glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {pattern} in {path}, found {len(matches)}")
    return matches[0]


def minute_of_day(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, format="%Y.%m.%d %H:%M:%S")
    return parsed.dt.hour * 60 + parsed.dt.minute


def quantiles(values: pd.Series) -> dict[str, float]:
    values = values.astype(float)
    return {
        "mean": float(values.mean()),
        "p50": float(values.quantile(0.50)),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
    }


def analyze(scenario: str, run_dir: Path) -> tuple[dict, pd.Series, pd.Series, pd.Series]:
    contract = SCENARIOS[scenario]
    decision_path = one(run_dir, "*_DecisionTelemetry_*.csv")
    lifecycle_path = one(run_dir, "*_LifecycleTrades_*.csv")
    meta_path = one(run_dir, "*_RunMeta_*.json")
    report_path = run_dir / "report.html"
    summary_path = run_dir / "analysis" / "enhanced_summary.json"

    decisions = pd.read_csv(decision_path)
    lifecycle = pd.read_csv(lifecycle_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    economics = json.loads(summary_path.read_text(encoding="utf-8"))

    signals = decisions[decisions.event == "SIGNAL_READY"].copy()
    entry_requests = decisions[decisions.event == "ENTRY_REQUEST"].copy()
    entry_deals = decisions[decisions.event == "ENTRY_DEAL"].copy()
    exit_requests = decisions[decisions.event == "EXIT_REQUEST"].copy()
    exit_deals = decisions[decisions.event == "EXIT_DEAL"].copy()
    opens = lifecycle[lifecycle.action == "OPEN"]
    closes = lifecycle[(lifecycle.action == "CLOSE") & (lifecycle.is_final_close == 1)]

    signal_minutes = minute_of_day(signals.london_time)
    entry_minutes = minute_of_day(entry_requests.london_time)
    exit_minutes = minute_of_day(exit_requests.london_time)

    entry_pairs = entry_requests.merge(
        entry_deals[["london_date", "actual_deal_price", "deal_id", "position_id"]],
        on="london_date",
        how="inner",
        suffixes=("_request", "_deal"),
    )
    exit_pairs = exit_requests.merge(
        exit_deals[["london_date", "actual_deal_price", "deal_id", "position_id"]],
        on="london_date",
        how="inner",
        suffixes=("_request", "_deal"),
    )
    entry_adverse = np.where(
        entry_pairs.direction > 0,
        entry_pairs.actual_deal_price_deal - entry_pairs.request_price,
        entry_pairs.request_price - entry_pairs.actual_deal_price_deal,
    ) / 0.0001
    exit_adverse = np.where(
        exit_pairs.direction > 0,
        exit_pairs.request_price - exit_pairs.actual_deal_price_deal,
        exit_pairs.actual_deal_price_deal - exit_pairs.request_price,
    ) / 0.0001
    entry_adverse = pd.Series(entry_adverse)
    exit_adverse = pd.Series(exit_adverse)
    spreads = entry_requests.spread_points.astype(float) * 0.1

    sample_index = len(entry_pairs) // 2
    sample_entry = entry_pairs.iloc[sample_index]
    sample_exit = exit_pairs[exit_pairs.london_date == sample_entry.london_date].iloc[0]
    sample_signal = signals[signals.london_date == sample_entry.london_date].iloc[0]

    result = {
        "scenario": scenario,
        "run_dir": str(run_dir.resolve()),
        "run_manifest_sha256": sha256(run_dir / "run_manifest.json"),
        "report_sha256": sha256(report_path),
        "decision_sha256": sha256(decision_path),
        "lifecycle_sha256": sha256(lifecycle_path),
        "runmeta_sha256": sha256(meta_path),
        "counts": {
            "signals": int(len(signals)),
            "entry_requests": int(len(entry_requests)),
            "entry_deals": int(len(entry_deals)),
            "lifecycle_opens": int(len(opens)),
            "exit_requests": int(len(exit_requests)),
            "exit_deals": int(len(exit_deals)),
            "lifecycle_final_closes": int(len(closes)),
        },
        "time_compliance": {
            "signal_0831_pct": float((signal_minutes == 8 * 60 + 31).mean() * 100),
            "entry_frozen_gate_pct": float(
                ((entry_minutes >= contract["entry_min"]) & (entry_minutes <= contract["entry_max"])).mean() * 100
            ),
            "exit_not_before_gate_pct": float((exit_minutes >= contract["exit_min"]).mean() * 100),
            "signal_minute_min_median_max": [int(signal_minutes.min()), float(signal_minutes.median()), int(signal_minutes.max())],
            "entry_minute_min_median_max": [int(entry_minutes.min()), float(entry_minutes.median()), int(entry_minutes.max())],
            "exit_minute_min_median_max": [int(exit_minutes.min()), float(exit_minutes.median()), int(exit_minutes.max())],
        },
        "entry_spread_pips": quantiles(spreads),
        "entry_adverse_fill_pips": quantiles(entry_adverse),
        "exit_adverse_fill_pips": quantiles(exit_adverse),
        "sample_trade": {
            "london_date": str(sample_entry.london_date),
            "signal_london": str(sample_signal.london_time),
            "source_0800_server": str(sample_signal.source_0800_server),
            "source_0830_server": str(sample_signal.source_0830_server),
            "source_0800_open_bid": float(sample_signal.source_0800_open_bid),
            "source_0830_open_bid": float(sample_signal.source_0830_open_bid),
            "formation_sign": int(sample_signal.formation_sign),
            "polarity": int(sample_signal.polarity),
            "direction": int(sample_signal.direction),
            "entry_london": str(sample_entry.london_time),
            "entry_request_price": float(sample_entry.request_price),
            "entry_deal_price": float(sample_entry.actual_deal_price_deal),
            "entry_deal_id": int(sample_entry.deal_id_deal),
            "position_id": int(sample_entry.position_id_deal),
            "exit_london": str(sample_exit.london_time),
            "exit_request_price": float(sample_exit.request_price),
            "exit_deal_price": float(sample_exit.actual_deal_price_deal),
            "exit_deal_id": int(sample_exit.deal_id_deal),
        },
        "runmeta_diagnostic": meta["diagnostic"],
        "economics_diagnostic_only": {
            "n_trades": economics["n_trades"],
            "profit_factor": economics["profit_factor"],
            "net_profit": economics["net_profit"],
            "win_rate_pct": economics["win_rate_pct"],
            "max_drawdown_pct": economics["max_drawdown_pct"],
            "expectancy_per_trade": economics["expectancy_per_trade"],
        },
    }
    return result, spreads, entry_adverse, exit_adverse


def label_minutes(value: float) -> str:
    value = int(round(value))
    return f"{value // 60:02d}:{value % 60:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    for scenario in SCENARIOS:
        parser.add_argument(f"--{scenario.lower().replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    parser.add_argument("--png-out", required=True, type=Path)
    args = parser.parse_args()

    results = []
    spreads_by_scenario = []
    entry_slippage = []
    exit_slippage = []
    for scenario in SCENARIOS:
        result, spreads, entry_adverse, exit_adverse = analyze(scenario, getattr(args, scenario.lower()))
        results.append(result)
        spreads_by_scenario.append(spreads)
        entry_slippage.append(entry_adverse)
        exit_slippage.append(exit_adverse)

    payload = {
        "schema_version": "lomx_execution_audit_dashboard.v1",
        "hypothesis_id": "HYP-LOMX-EXEC-AUDIT-M1-003",
        "audit_only": True,
        "performance_metrics_authorized": False,
        "parent_economic_verdict_unchanged": "KILLED",
        "total_completed_lifecycles": sum(item["counts"]["lifecycle_final_closes"] for item in results),
        "all_execution_contracts_passed": all(
            item["time_compliance"][key] == 100.0
            for item in results
            for key in ("signal_0831_pct", "entry_frozen_gate_pct", "exit_not_before_gate_pct")
        ),
        "scenarios": results,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    names = [item["scenario"].replace("GBPUSD_", "GBP ").replace("EURUSD_", "EUR ") for item in results]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    fig.suptitle("HYP-LOMX-EXEC-AUDIT-M1-003 | Model-0 execution fidelity (2016-2020)", fontsize=16, weight="bold")

    ax = axes[0, 0]
    x = np.arange(len(names))
    width = 0.18
    count_keys = ["signals", "entry_deals", "exit_deals", "lifecycle_final_closes"]
    for idx, key in enumerate(count_keys):
        ax.bar(x + (idx - 1.5) * width, [r["counts"][key] for r in results], width, label=key)
    ax.axhline(1000, color="#b22222", linestyle="--", linewidth=1.3, label="frozen floor=1000")
    ax.set_title("Population reconciliation")
    ax.set_xticks(x, names, rotation=12, ha="right")
    ax.set_ylabel("rows / completed lifecycles")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 1]
    colors = ["#2f5597", "#70ad47", "#c55a11"]
    for idx, result in enumerate(results):
        timings = result["time_compliance"]
        values = [timings["signal_minute_min_median_max"][1], timings["entry_minute_min_median_max"][1], timings["exit_minute_min_median_max"][1]]
        ax.plot(values, [idx] * 3, "o-", color=colors[idx % len(colors)], linewidth=2, markersize=7)
        if values[0] == values[1]:
            labels = [(values[0], "signal+entry", 0), (values[2], "exit", 0)]
        else:
            labels = [(values[0], "signal", 0), (values[1], "entry", -12), (values[2], "exit", 12)]
        for value, stage, x_offset in labels:
            ax.annotate(
                f"{stage} {label_minutes(value)}",
                (value, idx),
                xytext=(x_offset, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
    ax.set_yticks(range(len(names)), names)
    ticks = sorted({8 * 60 + 31, 12 * 60, 15 * 60 + 30, 16 * 60, 16 * 60 + 30})
    ax.set_xticks(ticks, [label_minutes(v) for v in ticks], rotation=25, ha="right")
    ax.set_xlim(8 * 60, 17 * 60)
    ax.set_title("Median London-time event sequence")
    ax.grid(axis="x", alpha=0.3)

    ax = axes[1, 0]
    ax.boxplot(spreads_by_scenario, tick_labels=names, showfliers=False)
    ax.set_title("Executable spread at entry request")
    ax.set_ylabel("pips")
    ax.tick_params(axis="x", rotation=12)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 1]
    x = np.arange(len(names))
    entry_p95 = [float(series.quantile(0.95)) for series in entry_slippage]
    exit_p95 = [float(series.quantile(0.95)) for series in exit_slippage]
    entry_max = [float(series.max()) for series in entry_slippage]
    exit_max = [float(series.max()) for series in exit_slippage]
    ax.bar(x - 0.2, entry_p95, 0.2, label="entry adverse p95")
    ax.bar(x, exit_p95, 0.2, label="exit adverse p95")
    ax.scatter(x - 0.2, entry_max, marker="x", color="black", label="entry max")
    ax.scatter(x, exit_max, marker="+", color="#b22222", label="exit max")
    ax.set_xticks(x, names, rotation=12, ha="right")
    ax.set_ylabel("pips")
    ax.set_title("Request-to-deal adverse fill delta")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    fig.text(0.5, 0.005, "AUDIT ONLY - economics, promotion, paper and live authority remain FALSE; parent HYP002 kill is unchanged.", ha="center", color="#b22222", weight="bold")
    args.png_out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.png_out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"all_execution_contracts_passed": payload["all_execution_contracts_passed"], "total_completed_lifecycles": payload["total_completed_lifecycles"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
