#!/usr/bin/env python3
"""Reproducible, risk-normalized monthly cohort comparison."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any


class ComparisonError(ValueError):
    pass


def annualized_vol(values: list[float]) -> float:
    return statistics.stdev(values) * math.sqrt(12.0) if len(values) >= 2 else 0.0


def annualized_sharpe(values: list[float]) -> float:
    vol = annualized_vol(values)
    return statistics.mean(values) * 12.0 / vol if vol > 0 else 0.0


def max_drawdown(values: list[float]) -> float:
    equity = peak = 1.0
    worst = 0.0
    for value in values:
        equity *= 1.0 + value
        peak = max(peak, equity)
        worst = max(worst, 1.0 - equity / peak)
    return worst


def lagged_vol_normalize(
    series: dict[str, float], target: float = 0.10, leverage_cap: float = 2.0
) -> dict[str, float]:
    months = sorted(series)
    if len(months) < 36:
        raise ComparisonError("each raw series requires at least 36 months")
    normalized: dict[str, float] = {}
    for index in range(12, len(months)):
        prior = [float(series[month]) for month in months[index - 12 : index]]
        trailing_vol = annualized_vol(prior)
        multiplier = leverage_cap if trailing_vol <= 1e-12 else min(
            leverage_cap, target / trailing_vol
        )
        normalized[months[index]] = float(series[months[index]]) * multiplier
    return normalized


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def paired_block_delta_sharpe(
    ea: list[float], benchmark: list[float], seed: int, reps: int, block: int
) -> list[float]:
    if len(ea) != len(benchmark) or len(ea) < block:
        raise ComparisonError("paired series length/block mismatch")
    rng = random.Random(seed)
    count = len(ea)
    deltas: list[float] = []
    for _ in range(reps):
        indices: list[int] = []
        while len(indices) < count:
            start = rng.randrange(count)
            indices.extend((start + offset) % count for offset in range(block))
        indices = indices[:count]
        ea_draw = [ea[index] for index in indices]
        benchmark_draw = [benchmark[index] for index in indices]
        deltas.append(annualized_sharpe(ea_draw) - annualized_sharpe(benchmark_draw))
    return deltas


def compare(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("study_id") != "STUDY-FVG-COMPARE-EURUSD-M5-001":
        raise ComparisonError("study_id mismatch")
    peers = payload.get("peers", [])
    if len(peers) < 5:
        raise ComparisonError("at least five verified peer series are required")
    ea = lagged_vol_normalize(payload["ea"]["monthly_returns"])
    normalized_peers = [lagged_vol_normalize(peer["monthly_returns"]) for peer in peers]
    common = sorted(set(ea).intersection(*(set(peer) for peer in normalized_peers)))
    if len(common) < 24:
        raise ComparisonError("common normalized overlap requires at least 24 months")

    ea_values = [ea[month] for month in common]
    peer_values = [[peer[month] for month in common] for peer in normalized_peers]
    median_series = [statistics.median(values) for values in zip(*peer_values)]
    deltas = paired_block_delta_sharpe(
        ea_values,
        median_series,
        int(payload.get("seed", 26071801)),
        int(payload.get("bootstrap_reps", 5000)),
        int(payload.get("block_months", 3)),
    )
    lower_90 = quantile(deltas, 0.05)
    lower_95 = quantile(deltas, 0.025)
    upper_95 = quantile(deltas, 0.975)
    ea_dd = max_drawdown(ea_values)
    median_peer_dd = statistics.median(max_drawdown(values) for values in peer_values)
    internal_gates = bool(payload.get("ea_workspace_pf_cost_cadence_gates_passed"))
    tail_not_worse = ea_dd <= median_peer_dd + 0.03

    if lower_95 > 0 and tail_not_worse and internal_gates:
        verdict = "SUPERIOR"
    elif lower_90 >= -0.25 and tail_not_worse and internal_gates:
        verdict = "NON_INFERIOR"
    elif upper_95 < 0:
        verdict = "INFERIOR"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "schema_version": "professional_monthly_comparison.v1",
        "study_id": payload["study_id"],
        "months_in_common": common,
        "peer_count": len(peers),
        "normalization": {
            "annual_vol_target": 0.10,
            "trailing_window_months": 12,
            "lag_months": 1,
            "leverage_cap": 2.0,
        },
        "ea_sharpe": annualized_sharpe(ea_values),
        "cohort_median_series_sharpe": annualized_sharpe(median_series),
        "delta_sharpe_ci": {
            "lower_90": lower_90,
            "lower_95": lower_95,
            "upper_95": upper_95,
        },
        "ea_max_drawdown": ea_dd,
        "cohort_median_max_drawdown": median_peer_dd,
        "workspace_gates_passed": internal_gates,
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = compare(payload)
        code = 0
    except (ComparisonError, KeyError, OSError, TypeError, ValueError) as exc:
        result = {
            "schema_version": "professional_monthly_comparison.v1",
            "verdict": "INSUFFICIENT_VERIFIED_DATA",
            "error": str(exc),
        }
        code = 2
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

