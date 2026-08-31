#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSCV & PBO (Probability of Backtest Overfitting)
================================================
Compute PBO across strategy variants using Combinatorially Symmetric Cross-Validation.

Input: variants directory containing subfolders with trades.csv (from quant_analyzer),
or direct CSV files inside the directory.
"""

import argparse
import csv
import json
import math
import random
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

from aligned_variant_evidence import load_aligned_variant_evidence


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))


def _read_trades_csv(path: Path) -> List[Tuple[datetime, float]]:
    trades = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            exit_time = row.get("exit_time") or row.get("ExitTime") or ""
            profit = row.get("profit") or row.get("Profit") or ""
            if not exit_time:
                continue
            try:
                t = _parse_dt(exit_time)
                p = float(profit)
            except Exception:
                continue
            trades.append((t, p))
    return trades


def _metric_from_profits(profits: List[float], metric: str) -> float:
    if not profits:
        return float("-inf")
    if metric == "pf":
        gp = sum(p for p in profits if p > 0)
        gl = abs(sum(p for p in profits if p < 0))
        return (gp / gl) if gl > 0 else 999.99  # v11.2: cap
    if metric == "sharpe":
        mean = sum(profits) / len(profits)
        var = sum((p - mean) ** 2 for p in profits) / max(1, len(profits) - 1)
        std = math.sqrt(var)
        return (mean / std) * math.sqrt(len(profits)) if std > 0 else float("-inf")
    if metric == "expectancy":
        return sum(profits) / len(profits)
    return sum(profits) / len(profits)


def _collect_variants(variants_dir: Path) -> Dict[str, List[Tuple[datetime, float]]]:
    variants: Dict[str, List[Tuple[datetime, float]]] = {}
    for p in variants_dir.iterdir():
        if p.is_file() and p.suffix.lower() == ".csv":
            trades = _read_trades_csv(p)
            if trades:
                variants[p.stem] = trades
        elif p.is_dir():
            csv_path = p / "trades.csv"
            if csv_path.exists():
                trades = _read_trades_csv(csv_path)
                if trades:
                    variants[p.name] = trades
    return variants


def _build_slices(global_start: datetime, global_end: datetime, n_slices: int) -> List[Tuple[datetime, datetime]]:
    total_sec = max(1.0, (global_end - global_start).total_seconds())
    slice_sec = total_sec / n_slices
    slices = []
    for i in range(n_slices):
        s = global_start + (i * slice_sec) * (global_end - global_start) / total_sec
        e = global_start + ((i + 1) * slice_sec) * (global_end - global_start) / total_sec
        slices.append((s, e))
    return slices


def _assign_slices(trades: List[Tuple[datetime, float]], slices: List[Tuple[datetime, datetime]]) -> List[List[float]]:
    buckets = [[] for _ in slices]
    for t, p in trades:
        for i, (s, e) in enumerate(slices):
            if (t >= s and t < e) or (i == len(slices) - 1 and t == e):
                buckets[i].append(p)
                break
    return buckets


def cscv_pbo(variants: Dict[str, List[Tuple[datetime, float]]], n_slices: int, is_ratio: float,
             min_trades_per_slice: int, metric: str, max_combos: int, seed: int) -> dict:
    if not variants:
        return {"error": "No variants found"}

    # Global time range
    all_times = [t for v in variants.values() for t, _ in v]
    global_start = min(all_times)
    global_end = max(all_times)
    slices = _build_slices(global_start, global_end, n_slices)

    # Precompute slice metrics per variant
    per_variant_metrics = {}
    coverage = {}
    for name, trades in variants.items():
        buckets = _assign_slices(trades, slices)
        metrics = []
        counts = []
        for b in buckets:
            counts.append(len(b))
            if len(b) < min_trades_per_slice:
                metrics.append(None)
            else:
                metrics.append(_metric_from_profits(b, metric))
        per_variant_metrics[name] = metrics
        coverage[name] = counts

    is_count = max(1, min(n_slices - 1, int(round(n_slices * is_ratio))))
    all_indices = list(range(n_slices))
    combos = list(combinations(all_indices, is_count))

    rng = random.Random(seed)
    if max_combos > 0 and len(combos) > max_combos:
        combos = rng.sample(combos, max_combos)

    bad = 0
    used = 0
    oos_rank_list = []

    for is_idx in combos:
        oos_idx = [i for i in all_indices if i not in is_idx]
        is_scores = {}
        oos_scores = {}
        for name, metrics in per_variant_metrics.items():
            is_vals = [metrics[i] for i in is_idx if metrics[i] is not None]
            oos_vals = [metrics[i] for i in oos_idx if metrics[i] is not None]
            if len(is_vals) != len(is_idx) or len(oos_vals) != len(oos_idx):
                continue
            is_scores[name] = sum(is_vals) / len(is_vals)
            oos_scores[name] = sum(oos_vals) / len(oos_vals)

        if len(is_scores) < 2:
            continue

        best_is = max(is_scores.items(), key=lambda x: x[1])[0]
        ranked_oos = sorted(oos_scores.items(), key=lambda x: x[1], reverse=True)
        ranks = {name: idx + 1 for idx, (name, _) in enumerate(ranked_oos)}
        rank = ranks.get(best_is, len(ranked_oos))
        oos_rank_list.append(rank)

        used += 1
        median_rank = (len(ranked_oos) + 1) / 2.0
        if rank > median_rank:
            bad += 1

    pbo = (bad / used) if used > 0 else None
    return {
        "n_variants": len(variants),
        "n_slices": n_slices,
        "is_slices": is_count,
        "oos_slices": n_slices - is_count,
        "metric": metric,
        "min_trades_per_slice": min_trades_per_slice,
        "combos_used": used,
        "pbo": pbo,
        "oos_rank_avg": round(sum(oos_rank_list) / len(oos_rank_list), 2) if oos_rank_list else None,
        "coverage_by_variant": coverage,
    }


def aligned_cscv_pbo(manifest_path: Path) -> dict:
    evidence = load_aligned_variant_evidence(manifest_path)
    variants = {
        variant_id: [(_parse_dt(day + "T00:00:00+00:00"), value) for day, value in zip(evidence.dates, values)]
        for variant_id, values in evidence.series.items()
    }
    result = cscv_pbo(
        variants=variants,
        n_slices=evidence.cscv_slices,
        is_ratio=0.5,
        min_trades_per_slice=1,
        metric="mean",
        max_combos=evidence.cscv_max_combinations,
        seed=evidence.random_seed,
    )
    result.update(
        {
            "analysis_kind": "preregistered_aligned_variant_matrix_cscv",
            "promotion_eligible": True,
            "selection_process_provenance": "full frozen variant family",
            **evidence.promotion_metadata(),
        }
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="CSCV & PBO for strategy variants")
    ap.add_argument("--variants-dir", required=True, help="Directory containing variant folders or trades.csv files")
    ap.add_argument("--metric", default="sharpe", choices=["sharpe", "pf", "expectancy", "mean"], help="Metric for ranking")
    ap.add_argument("--slices", type=int, default=8, help="Number of slices for CSCV")
    ap.add_argument("--is-ratio", type=float, default=0.5, help="IS ratio (0-1)")
    ap.add_argument("--min-trades-per-slice", type=int, default=5, help="Minimum trades per slice")
    ap.add_argument("--max-combos", type=int, default=200, help="Max combinations to sample (0 = all)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--out", default="", help="Output directory")
    ap.add_argument(
        "--variant-manifest",
        default="",
        help="Preregistered aligned variant manifest; enables promotion-grade CSCV/PBO",
    )
    args = ap.parse_args()

    variants_dir = Path(args.variants_dir)
    if not variants_dir.exists():
        raise SystemExit(f"variants-dir not found: {variants_dir}")

    try:
        if args.variant_manifest:
            result = aligned_cscv_pbo(Path(args.variant_manifest))
        else:
            variants = _collect_variants(variants_dir)
            result = cscv_pbo(
                variants=variants,
                n_slices=args.slices,
                is_ratio=args.is_ratio,
                min_trades_per_slice=args.min_trades_per_slice,
                metric=args.metric,
                max_combos=args.max_combos,
                seed=args.seed,
            )
            result.update(
                {
                    "analysis_kind": "posthoc_trade_csv_cscv_proxy",
                    "promotion_eligible": False,
                    "limitation": (
                        "Diagnostic only: no preregistered aligned variant manifest was supplied."
                    ),
                }
            )
    except ValueError as exc:
        result = {"error": str(exc), "promotion_eligible": False}

    out_dir = Path(args.out) if args.out else variants_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "cscv_pbo.json"
    out_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1
    print(f"[CSCV/PBO] saved: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
