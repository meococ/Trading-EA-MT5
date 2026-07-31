#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
White's Reality Check
=====================
Estimate p-value for best strategy performance under data snooping.
Requires multiple strategy variants (each with trades.csv).
"""

import argparse
import csv
import json
import math
import random
from pathlib import Path
from typing import Dict, List

from aligned_variant_evidence import load_aligned_variant_evidence


def _read_profits(path: Path) -> List[float]:
    profits = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            p = row.get("profit") or row.get("Profit") or ""
            try:
                profits.append(float(p))
            except Exception:
                continue
    return profits


def _metric_from_profits(profits: List[float], metric: str) -> float:
    if not profits:
        return float("-inf")
    if metric == "net_profit":
        return sum(profits)
    if metric == "pf":
        gp = sum(p for p in profits if p > 0)
        gl = abs(sum(p for p in profits if p < 0))
        return (gp / gl) if gl > 0 else 999.99  # v11.2: cap
    if metric == "sharpe":
        mean = sum(profits) / len(profits)
        var = sum((p - mean) ** 2 for p in profits) / max(1, len(profits) - 1)
        std = math.sqrt(var)
        return (mean / std) * math.sqrt(len(profits)) if std > 0 else float("-inf")
    return sum(profits) / len(profits)


def _collect_variants(variants_dir: Path) -> Dict[str, List[float]]:
    variants: Dict[str, List[float]] = {}
    for p in variants_dir.iterdir():
        if p.is_file() and p.suffix.lower() == ".csv":
            profits = _read_profits(p)
            if profits:
                variants[p.stem] = profits
        elif p.is_dir():
            csv_path = p / "trades.csv"
            if csv_path.exists():
                profits = _read_profits(csv_path)
                if profits:
                    variants[p.name] = profits
    return variants


def white_reality_check(variants: Dict[str, List[float]], n_boot: int, metric: str, seed: int) -> dict:
    if not variants:
        return {"error": "No variants found"}

    observed_metrics = {name: _metric_from_profits(p, metric) for name, p in variants.items()}
    best_observed = max(observed_metrics.values())

    rng = random.Random(seed)
    boot_best = []

    for _ in range(n_boot):
        best_m = float("-inf")
        for name, profits in variants.items():
            if not profits:
                continue
            mean = sum(profits) / len(profits)
            detrended = [p - mean for p in profits]
            sample = [rng.choice(detrended) for _ in detrended]
            m = _metric_from_profits(sample, metric)
            if m > best_m:
                best_m = m
        boot_best.append(best_m)

    if not boot_best:
        return {"error": "Bootstrap failed"}

    p_value = sum(1 for x in boot_best if x >= best_observed) / len(boot_best)
    return {
        "n_variants": len(variants),
        "metric": metric,
        "n_bootstrap": n_boot,
        "best_observed": best_observed,
        "p_value": p_value,
        "verdict": "PASS" if p_value < 0.05 else "FAIL",
    }


def aligned_white_reality_check(manifest_path: Path) -> dict:
    """Joint moving-block bootstrap over aligned variant returns versus the frozen baseline."""
    evidence = load_aligned_variant_evidence(manifest_path)
    baseline = evidence.series[evidence.baseline_variant_id]
    differentials = {
        variant_id: [value - base for value, base in zip(values, baseline)]
        for variant_id, values in evidence.series.items()
        if variant_id != evidence.baseline_variant_id
    }
    if not differentials:
        raise ValueError("Reality Check requires at least one non-baseline variant")
    observed = {name: sum(values) / len(values) for name, values in differentials.items()}
    best_observed = max(observed.values())
    centered = {
        name: [value - observed[name] for value in values]
        for name, values in differentials.items()
    }
    n_rows = len(evidence.dates)
    block = evidence.white_reality_block_length
    rng = random.Random(evidence.random_seed)
    boot_best: List[float] = []
    for _ in range(evidence.white_reality_bootstrap):
        indices: List[int] = []
        while len(indices) < n_rows:
            start = rng.randrange(n_rows)
            indices.extend((start + offset) % n_rows for offset in range(block))
        indices = indices[:n_rows]
        boot_best.append(
            max(sum(values[index] for index in indices) / n_rows for values in centered.values())
        )
    exceedances = sum(1 for value in boot_best if value >= best_observed)
    p_value = (exceedances + 1) / (len(boot_best) + 1)
    return {
        "analysis_kind": "preregistered_aligned_white_reality_check",
        "promotion_eligible": True,
        "n_variants": len(evidence.expected_variant_ids),
        "n_tested_against_baseline": len(differentials),
        "baseline_variant_id": evidence.baseline_variant_id,
        "metric": "mean_daily_net_r_difference_vs_baseline",
        "n_bootstrap": evidence.white_reality_bootstrap,
        "block_length": block,
        "best_observed": best_observed,
        "p_value": p_value,
        "p_value_correction": "plus_one_finite_bootstrap",
        "verdict": "PASS" if p_value < 0.05 else "FAIL",
        "bootstrap_dependence": "same moving-block indices across all variants",
        **evidence.promotion_metadata(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="White's Reality Check")
    ap.add_argument("--variants-dir", required=True, help="Directory containing variant folders or trades.csv files")
    ap.add_argument("--metric", default="net_profit", choices=["net_profit", "pf", "sharpe", "expectancy"])
    ap.add_argument("--n-boot", type=int, default=2000, help="Bootstrap iterations")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--out", default="", help="Output directory")
    ap.add_argument(
        "--variant-manifest",
        default="",
        help="Preregistered aligned variant manifest; enables promotion-grade Reality Check",
    )
    args = ap.parse_args()

    variants_dir = Path(args.variants_dir)
    if not variants_dir.exists():
        raise SystemExit(f"variants-dir not found: {variants_dir}")

    try:
        if args.variant_manifest:
            result = aligned_white_reality_check(Path(args.variant_manifest))
        else:
            variants = _collect_variants(variants_dir)
            result = white_reality_check(variants, args.n_boot, args.metric, args.seed)
            result.update(
                {
                    "analysis_kind": "independent_variant_resampling_proxy",
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
    out_file = out_dir / "white_reality_check.json"
    out_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1
    print(f"[WhiteRC] saved: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
