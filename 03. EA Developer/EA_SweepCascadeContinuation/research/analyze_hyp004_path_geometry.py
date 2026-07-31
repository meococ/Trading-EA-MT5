#!/usr/bin/env python3
"""Describe HYP-004 post-entry path geometry without authorizing same-ID tuning."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


HYPOTHESIS_ID = "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004"
RUN_ID = "20260725_210811"
POINT_SIZE = 0.00001
MFE_LEVELS = (0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 1.80)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def quantiles(series: pd.Series) -> dict[str, float]:
    return {
        str(q): round(float(value), 8)
        for q, value in series.quantile([0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]).items()
    }


def summarize_group(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "n": int(len(frame)),
        "mean_net_r": round(float(frame["net_r"].mean()), 8),
        "median_net_r": round(float(frame["net_r"].median()), 8),
        "median_mfe_r": round(float(frame["mfe_r"].median()), 8),
        "median_mae_r": round(float(frame["mae_r"].median()), 8),
        "mfe_reach": {
            str(level): {
                "n": int((frame["mfe_r"] >= level).sum()),
                "share": round(float((frame["mfe_r"] >= level).mean()), 8),
            }
            for level in MFE_LEVELS
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parents[3]
    pair_root = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "evidence"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    )
    trades_path = pair_root / "challenger_trades.csv"
    bars_path = (
        workspace
        / "02. AlphaFactory"
        / "data"
        / "fivepercent"
        / "EURUSD"
        / "EURUSD_M1_2015_now.parquet"
    )
    output_path = args.output.resolve() if args.output else pair_root / "path_geometry_analysis_v2.json"

    trades = pd.read_csv(trades_path)
    bars = pd.read_parquet(
        bars_path, columns=["time_server", "high", "low", "spread"]
    )
    bars["time_server"] = pd.to_datetime(bars["time_server"])
    bars = bars.set_index("time_server").sort_index()

    rows: list[dict[str, object]] = []
    errors: list[str] = []
    for trade in trades.itertuples(index=False):
        entry_time = pd.Timestamp(trade.open_time)
        exit_time = pd.Timestamp(trade.close_time)
        window = bars.loc[entry_time.floor("min") : exit_time.floor("min")]
        risk = abs(float(trade.entry) - float(trade.planned_stop))
        if window.empty or risk <= 0:
            errors.append(f"position {trade.position_id}: missing bars or nonpositive risk")
            continue
        spread_price = window["spread"].astype(float) * POINT_SIZE
        if trade.direction == "BUY":
            favorable = (window["high"] - float(trade.entry)) / risk
            adverse = (float(trade.entry) - window["low"]) / risk
        else:
            ask_high = window["high"] + spread_price
            ask_low = window["low"] + spread_price
            favorable = (float(trade.entry) - ask_low) / risk
            adverse = (ask_high - float(trade.entry)) / risk
        rows.append(
            {
                "position_id": int(trade.position_id),
                "direction": trade.direction,
                "entry_time_server": str(entry_time),
                "exit_time_server": str(exit_time),
                "net_account": float(trade.net),
                "net_r": float(trade.realized_r),
                "outcome": "WIN" if float(trade.net) > 0 else "LOSS",
                "mfe_r": float(favorable.max()),
                "mae_r": float(adverse.max()),
                "hold_minutes": (exit_time - entry_time).total_seconds() / 60.0,
            }
        )

    frame = pd.DataFrame(rows)
    if errors or len(frame) != 261:
        raise SystemExit(
            f"PATH_GEOMETRY_INVALID rows={len(frame)} errors={errors[:5]}"
        )

    losers = frame[frame["outcome"] == "LOSS"]
    winners = frame[frame["outcome"] == "WIN"]
    bins = [-float("inf"), 0.25, 0.50, 1.00, 1.50, 1.80, float("inf")]
    labels = ["<0.25", "0.25-0.50", "0.50-1.00", "1.00-1.50", "1.50-1.80", ">=1.80"]
    frame["mfe_bin"] = pd.cut(frame["mfe_r"], bins=bins, labels=labels, right=False)
    by_mfe_bin = []
    for label, group in frame.groupby("mfe_bin", observed=False):
        by_mfe_bin.append(
            {
                "mfe_bin": str(label),
                "n": int(len(group)),
                "wins": int((group["outcome"] == "WIN").sum()),
                "losses": int((group["outcome"] == "LOSS").sum()),
                "mean_net_r": round(float(group["net_r"].mean()), 8),
                "median_net_r": round(float(group["net_r"].median()), 8),
            }
        )

    result = {
        "schema_version": "scc_path_geometry.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "status": "DESCRIPTIVE_POSTMORTEM_ONLY",
        "inputs": {
            "trades": {
                "path": trades_path.relative_to(workspace).as_posix(),
                "sha256": sha256(trades_path),
            },
            "bars": {
                "path": bars_path.relative_to(workspace).as_posix(),
                "sha256": sha256(bars_path),
                "time_col": "time_server",
                "bar_granularity": "M1",
            },
        },
        "coverage": {
            "trades_expected": 261,
            "trades_analyzed": int(len(frame)),
            "wins": int(len(winners)),
            "losses": int(len(losers)),
        },
        "population": summarize_group(frame),
        "winners": summarize_group(winners),
        "losers": summarize_group(losers),
        "mfe_quantiles_r": quantiles(frame["mfe_r"]),
        "mae_quantiles_r": quantiles(frame["mae_r"]),
        "by_mfe_bin": by_mfe_bin,
        "decision_implications": {
            "losers_mfe_below_0_25r": int((losers["mfe_r"] < 0.25).sum()),
            "losers_reached_0_50r": int((losers["mfe_r"] >= 0.50).sum()),
            "losers_reached_1_00r": int((losers["mfe_r"] >= 1.00).sum()),
            "losers_reached_1_50r": int((losers["mfe_r"] >= 1.50).sum()),
            "primary_research_priority": "ENTRY_SETUP_DISCRIMINATION",
            "secondary_research_priority": "EXIT_MANAGEMENT_AS_SEPARATE_CHILD",
        },
        "interpretation_boundary": [
            "Post-outcome MFE/MAE describes realized paths and is not a decision-time predictor.",
            "M1 OHLC plus minute spread is diagnostic, not tick-exact path sequencing.",
            "No break-even, partial, stop, target, timeout or filter change is authorized under HYP-004.",
            "Any management or entry redesign requires a fresh ID, frozen contract and independent test.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        "SCC_PATH_GEOMETRY_OK "
        f"trades={len(frame)} losers_lt_0.25R={result['decision_implications']['losers_mfe_below_0_25r']} "
        f"output_sha256={sha256(output_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
