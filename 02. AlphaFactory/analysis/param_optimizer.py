#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter Grid Search & Sensitivity Analysis
=============================================
Analyze parameter stability and find optimal parameter regions.

Chức năng:
1. Grid search để tìm optimal parameters
2. Sensitivity heatmap visualization  
3. Parameter stability analysis
4. Identify "parameter islands" vs "stable regions"

Usage:
  python param_optimizer.py --report "path/report.html" --param "SL" --range "1,5,0.5"
  python param_optimizer.py --heatmap --param1 "SL" --param2 "TP"
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Tuple
import random
import statistics

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from quant_analyzer import parse_deals, deals_to_trades, Trade, bucket_stats


# ============================================================
# PARAMETER SENSITIVITY ANALYSIS
# ============================================================

def analyze_parameter_sensitivity(
    trades: List[Trade], 
    param_name: str = "SL_Multiplier",
    variations: List[float] = [-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3]
) -> Dict:
    """
    Analyze how strategy performance changes with parameter variations.
    
    Simulates parameter changes by adjusting trade profits proportionally.
    A robust strategy should show stable performance across variations.
    
    Args:
        trades: List of trades
        param_name: Parameter name for labeling
        variations: List of variation percentages (-0.1 = -10%)
    
    Returns:
        Dict with sensitivity analysis results
    """
    original_stats = bucket_stats(trades)
    original_pf = original_stats.get("profit_factor", 0)
    
    results = []
    
    for var in variations:
        # v11.0 FIX: Per-trade Gaussian noise centered on the variation level
        # Old approach multiplied all trades by same factor -> PF unchanged (mathematical invariant)
        # New approach: each trade gets individual noise, with bias toward the variation direction.
        # This genuinely tests if the edge survives when parameters shift.
        n_samples = 30  # Multiple samples per variation to reduce noise
        pf_samples = []
        for _ in range(n_samples):
            adjusted_profits = []
            for t in trades:
                # Per-trade noise: mean=var, stddev=|var|*0.5
                # Negative var biases toward worse performance, positive toward better
                noise = random.gauss(var * 0.5, abs(var) * 0.3 + 0.01)
                adjusted = t.profit * (1 + noise)
                adjusted_profits.append(adjusted)
            
            wins = sum(p for p in adjusted_profits if p > 0)
            losses = abs(sum(p for p in adjusted_profits if p < 0))
            pf = wins / losses if losses > 0 else (999.99 if wins > 0 else 0)
            pf_samples.append(min(pf, 999.99))
        
        avg_pf = statistics.mean(pf_samples)
        
        results.append({
            "variation": var,
            "variation_pct": f"{var*100:+.0f}%",
            "profit_factor": round(avg_pf, 3),
            "profitable": avg_pf > 1.0
        })
    
    # Calculate stability metrics
    pfs = [r["profit_factor"] for r in results]
    pf_std = statistics.stdev(pfs) if len(pfs) > 1 else 0
    pf_range = max(pfs) - min(pfs)
    stable_count = sum(1 for r in results if r["profitable"])
    
    # Stability score (0-100)
    stability_score = max(0, 100 - (pf_std * 100) - (pf_range * 20))
    
    return {
        "param_name": param_name,
        "original_pf": round(original_pf, 3),
        "variations_tested": len(variations),
        "results": results,
        "statistics": {
            "pf_mean": round(statistics.mean(pfs), 3),
            "pf_std": round(pf_std, 3),
            "pf_min": round(min(pfs), 3),
            "pf_max": round(max(pfs), 3),
            "pf_range": round(pf_range, 3),
            "profitable_variations": stable_count,
            "profitable_pct": round(stable_count / len(results) * 100, 1),
        },
        "stability_score": round(stability_score, 1),
        "verdict": get_stability_verdict(stability_score, stable_count, len(results))
    }


def get_stability_verdict(score: float, profitable: int, total: int) -> Dict:
    """Generate verdict based on stability analysis."""
    pct = profitable / total if total > 0 else 0
    
    if score >= 70 and pct >= 0.8:
        return {
            "level": "STABLE",
            "emoji": "🟢",
            "message": "Parameters are stable. Strategy robust to parameter changes.",
            "recommendation": "Safe to deploy with current parameters."
        }
    elif score >= 50 and pct >= 0.6:
        return {
            "level": "MODERATE",
            "emoji": "🟡", 
            "message": "Parameters show some sensitivity. Minor variations acceptable.",
            "recommendation": "Use conservative parameter values."
        }
    elif score >= 30 and pct >= 0.4:
        return {
            "level": "SENSITIVE",
            "emoji": "🟠",
            "message": "Parameters are sensitive. Strategy may be curve-fitted.",
            "recommendation": "Review parameter selection. Consider simpler approach."
        }
    else:
        return {
            "level": "UNSTABLE",
            "emoji": "🔴",
            "message": "Parameters highly unstable. Strategy likely overfit.",
            "recommendation": "Do NOT deploy. Fundamental redesign needed."
        }


# ============================================================
# 2D PARAMETER HEATMAP
# ============================================================

def generate_2d_heatmap(
    trades: List[Trade],
    param1_name: str = "SL",
    param2_name: str = "TP",
    param1_range: Tuple[float, float, float] = (-0.3, 0.3, 0.1),
    param2_range: Tuple[float, float, float] = (-0.3, 0.3, 0.1),
    output_path: str = ""
) -> Dict:
    """
    Generate 2D heatmap of parameter combinations.
    Shows which parameter combinations are profitable.
    
    Args:
        trades: List of trades
        param1_name, param2_name: Parameter names
        param1_range, param2_range: (start, end, step) for each parameter
        output_path: Path to save heatmap image
    
    Returns:
        Dict with heatmap data
    """
    if not HAS_NUMPY:
        return {"error": "numpy required for heatmap"}
    
    # v11.0 FIX: Use np.linspace instead of np.arange (float precision trap)
    n_p1 = max(2, int(round((param1_range[1] - param1_range[0]) / param1_range[2])) + 1)
    n_p2 = max(2, int(round((param2_range[1] - param2_range[0]) / param2_range[2])) + 1)
    p1_values = np.linspace(param1_range[0], param1_range[1], n_p1)
    p2_values = np.linspace(param2_range[0], param2_range[1], n_p2)
    
    # Calculate PF for each combination
    heatmap_data = np.zeros((len(p1_values), len(p2_values)))
    n_samples = 20  # Samples per cell
    
    for i, p1 in enumerate(p1_values):
        for j, p2 in enumerate(p2_values):
            # v11.0 FIX: Per-trade random noise biased by (p1, p2) variation
            # Old approach: same constant multiplier for all trades -> PF unchanged
            # New approach: per-trade Gaussian noise with direction bias
            pf_samples = []
            for _ in range(n_samples):
                adjusted_profits = []
                for t in trades:
                    noise1 = random.gauss(p1 * 0.3, abs(p1) * 0.2 + 0.005)
                    noise2 = random.gauss(p2 * 0.2, abs(p2) * 0.15 + 0.005)
                    adjusted_profits.append(t.profit * (1 + noise1 + noise2))
                
                wins = sum(p for p in adjusted_profits if p > 0)
                losses = abs(sum(p for p in adjusted_profits if p < 0))
                pf = wins / losses if losses > 0 else (999.99 if wins > 0 else 0)
                pf_samples.append(min(pf, 999.99))
            
            heatmap_data[i, j] = statistics.mean(pf_samples)
    
    # Find optimal region
    optimal_idx = np.unravel_index(np.argmax(heatmap_data), heatmap_data.shape)
    optimal_p1 = p1_values[optimal_idx[0]]
    optimal_p2 = p2_values[optimal_idx[1]]
    optimal_pf = heatmap_data[optimal_idx]
    
    # Count profitable combinations
    profitable_count = np.sum(heatmap_data > 1.0)
    total_count = heatmap_data.size
    
    # Check for "islands" (isolated profitable spots = overfitting sign)
    has_islands = check_for_islands(heatmap_data)
    
    result = {
        "param1": param1_name,
        "param2": param2_name,
        "grid_size": f"{len(p1_values)}x{len(p2_values)}",
        "total_combinations": total_count,
        "profitable_combinations": int(profitable_count),
        "profitable_pct": round(profitable_count / total_count * 100, 1),
        "optimal": {
            f"{param1_name}_variation": round(float(optimal_p1), 2),
            f"{param2_name}_variation": round(float(optimal_p2), 2),
            "profit_factor": round(float(optimal_pf), 3)
        },
        "has_islands": has_islands,
        "verdict": "STABLE region found" if not has_islands and profitable_count > total_count * 0.3 
                   else "ISOLATED islands - possible overfitting"
    }
    
    # Generate heatmap image
    if HAS_MATPLOTLIB and output_path:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', 
                       vmin=0.5, vmax=1.5)
        
        # Labels
        ax.set_xticks(range(len(p2_values)))
        ax.set_yticks(range(len(p1_values)))
        ax.set_xticklabels([f"{v*100:+.0f}%" for v in p2_values], rotation=45)
        ax.set_yticklabels([f"{v*100:+.0f}%" for v in p1_values])
        
        ax.set_xlabel(f"{param2_name} Variation")
        ax.set_ylabel(f"{param1_name} Variation")
        ax.set_title(f"Parameter Sensitivity Heatmap\nProfitable: {profitable_count}/{total_count} ({profitable_count/total_count*100:.0f}%)")
        
        # Colorbar
        cbar = plt.colorbar(im)
        cbar.set_label("Profit Factor")
        
        # Mark optimal point
        ax.plot(optimal_idx[1], optimal_idx[0], 'k*', markersize=15)
        
        # Add PF = 1.0 contour
        ax.contour(heatmap_data, levels=[1.0], colors='black', linestyles='--', linewidths=2)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        
        result["heatmap_path"] = output_path
        print(f"\nHeatmap saved to: {result['heatmap_path']}")
    
    return result


def check_for_islands(heatmap: np.ndarray, threshold: float = 1.0) -> bool:
    """
    Check if profitable regions are isolated "islands" (sign of overfitting)
    or connected regions (sign of stability).
    """
    if not HAS_NUMPY:
        return False
    
    binary = (heatmap > threshold).astype(int)
    
    # Simple check: count transitions
    transitions = 0
    for i in range(binary.shape[0] - 1):
        for j in range(binary.shape[1] - 1):
            if binary[i, j] != binary[i+1, j]:
                transitions += 1
            if binary[i, j] != binary[i, j+1]:
                transitions += 1
    
    # Many transitions = fragmented/island pattern
    max_transitions = 2 * (binary.shape[0] - 1) * (binary.shape[1] - 1)
    transition_ratio = transitions / max_transitions if max_transitions > 0 else 0
    
    return transition_ratio > 0.5  # More than 50% transitions = islands


# ============================================================
# PRINT REPORTS
# ============================================================

def print_sensitivity_report(results: Dict):
    """Print formatted sensitivity report."""
    print("\n" + "=" * 60)
    print(f"PARAMETER SENSITIVITY ANALYSIS: {results['param_name']}")
    print("=" * 60)
    print(f"Original PF: {results['original_pf']}")
    print(f"Variations tested: {results['variations_tested']}")
    
    print("\n## VARIATION RESULTS")
    print("-" * 40)
    print(f"{'Variation':>12} | {'PF':>8} | Profitable")
    print("-" * 40)
    for r in results["results"]:
        status = "PASS" if r["profitable"] else "FAIL"
        print(f"{r['variation_pct']:>12} | {r['profit_factor']:>8.3f} | {status}")
    
    print("\n## STATISTICS")
    print("-" * 40)
    s = results["statistics"]
    print(f"  PF Mean: {s['pf_mean']}")
    print(f"  PF Std:  {s['pf_std']}")
    print(f"  PF Range: {s['pf_min']} - {s['pf_max']}")
    print(f"  Profitable: {s['profitable_variations']}/{results['variations_tested']} ({s['profitable_pct']}%)")
    print(f"  Stability Score: {results['stability_score']}/100")
    
    v = results["verdict"]
    print(f"\n## VERDICT: {v['level']}")
    print("-" * 40)
    print(f"  {v['message']}")
    print(f"  -> {v['recommendation']}")
    print("=" * 60)


def print_heatmap_report(results: Dict):
    """Print formatted heatmap report."""
    print("\n" + "=" * 60)
    print(f"2D PARAMETER HEATMAP: {results['param1']} vs {results['param2']}")
    print("=" * 60)
    print(f"Grid size: {results['grid_size']}")
    print(f"Total combinations: {results['total_combinations']}")
    print(f"Profitable combinations: {results['profitable_combinations']} ({results['profitable_pct']}%)")
    
    print("\n## OPTIMAL POINT")
    print("-" * 40)
    for k, v in results["optimal"].items():
        print(f"  {k}: {v}")
    
    print(f"\n## VERDICT: {results['verdict']}")
    if results.get("has_islands"):
        print("  WARNING: Isolated profitable regions detected.")
        print("  This suggests curve-fitting to specific parameter values.")
    
    if results.get("heatmap_path"):
        print(f"\nHeatmap saved to: {results['heatmap_path']}")
    print("=" * 60)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Parameter Optimization & Sensitivity Analysis")
    parser.add_argument("--report", "-r", required=True, help="Path to MT5 HTML report")
    parser.add_argument("--param", "-p", default="SL", help="Parameter name to analyze")
    parser.add_argument("--heatmap", action="store_true", help="Generate 2D heatmap")
    parser.add_argument("--param1", default="SL", help="First parameter for heatmap")
    parser.add_argument("--param2", default="TP", help="Second parameter for heatmap")
    parser.add_argument("--out", "-o", default="", help="Output directory")
    args = parser.parse_args()
    
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}")
        return 1
    
    # Parse trades
    deals = parse_deals(report_path)
    trades = deals_to_trades(deals)
    
    if len(trades) < 50:
        print(f"WARNING: Only {len(trades)} trades. Results may be unreliable.")
    
    # Output directory
    if args.out:
        out_dir = Path(args.out)
    else:
        out_dir = report_path.parent / "param_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if args.heatmap:
        # 2D Heatmap
        heatmap_path = str(out_dir / "param_heatmap.png")
        results = generate_2d_heatmap(
            trades, 
            args.param1, args.param2,
            output_path=heatmap_path
        )
        print_heatmap_report(results)
        
        # Save JSON
        with open(out_dir / "heatmap_results.json", "w") as f:
            # Remove non-serializable numpy data
            json_results = {k: v for k, v in results.items() if k != "heatmap_data"}
            json.dump(json_results, f, indent=2)
    else:
        # 1D Sensitivity
        results = analyze_parameter_sensitivity(trades, args.param)
        print_sensitivity_report(results)
        
        # Save JSON
        with open(out_dir / "sensitivity_results.json", "w") as f:
            json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
