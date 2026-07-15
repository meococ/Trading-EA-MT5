#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decision Framework — Programmatic ITERATE / PIVOT / ABANDON Engine
==================================================================

Evaluates strategy metrics and returns a structured decision with reasoning.
See DECISION_FRAMEWORK.md for the full specification.

Usage:
    python decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2
    python decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2 --prev-pf 1.20
    python decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2 --output decision.json
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional


class Decision(str, Enum):
    ITERATE = "ITERATE"
    PIVOT = "PIVOT"
    ABANDON = "ABANDON"
    PROMOTE = "PROMOTE"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Quality Gate Thresholds ──────────────────────────────────────────

GATE_PF = 1.4
GATE_DD = 15.0
GATE_WFA_PASS = 0.6
GATE_MC_P95_DD = 15.0
GATE_MIN_TRADES = 200
GATE_TRADES_PER_MONTH_SOFT = 20

# ── Abandon Thresholds ───────────────────────────────────────────────

ABANDON_PF_THRESHOLD = 1.05
ABANDON_PF_MIN_ITER = 3
ABANDON_WFA_THRESHOLD = 0.4
ABANDON_WFA_MIN_ITER = 2
ABANDON_MC_DD_THRESHOLD = 50.0
MAX_ITERATIONS = 5


@dataclass
class StrategyMetrics:
    """Input metrics for decision evaluation."""
    pf: float
    max_dd_pct: float
    total_trades: int
    wfa_pass_rate: float
    mc_p95_dd: float
    iteration: int
    prev_pf: Optional[float] = None
    trades_per_month: Optional[float] = None


@dataclass
class DecisionResult:
    """Structured output of the decision framework."""
    decision: str
    confidence: str
    reasons: List[str] = field(default_factory=list)
    metrics_summary: dict = field(default_factory=dict)
    gates_passed: dict = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def evaluate(metrics: StrategyMetrics) -> DecisionResult:
    """
    Evaluate strategy metrics and return a decision.

    Decision tree priority (top to bottom):
    1. Too few trades       → ABANDON
    2. Max iterations hit   → PIVOT
    3. PF too low after 3+  → ABANDON
    4. MC catastrophic      → ABANDON
    5. WFA curve-fit        → ABANDON
    6. All quality gates    → PROMOTE
    7. Improving            → ITERATE
    8. Stalled              → ITERATE (with warning)
    """
    m = metrics
    reasons: List[str] = []
    warnings: List[str] = []
    next_steps: List[str] = []

    # ── Gate checks ──────────────────────────────────────────────
    gates = {
        "pf": m.pf >= GATE_PF,
        "dd": m.max_dd_pct <= GATE_DD,
        "wfa": m.wfa_pass_rate >= GATE_WFA_PASS,
        "mc": m.mc_p95_dd <= GATE_MC_P95_DD,
        "trades": m.total_trades >= GATE_MIN_TRADES,
    }

    metrics_summary = {
        "pf": m.pf,
        "max_dd_pct": m.max_dd_pct,
        "total_trades": m.total_trades,
        "wfa_pass_rate": m.wfa_pass_rate,
        "mc_p95_dd": m.mc_p95_dd,
        "iteration": m.iteration,
    }
    if m.prev_pf is not None:
        metrics_summary["prev_pf"] = m.prev_pf

    # ── Soft warnings ────────────────────────────────────────────
    if m.trades_per_month is not None and m.trades_per_month < GATE_TRADES_PER_MONTH_SOFT:
        warnings.append(
            f"Trades/month ({m.trades_per_month:.1f}) below soft threshold ({GATE_TRADES_PER_MONTH_SOFT})"
        )

    # ── 1. Too few trades ────────────────────────────────────────
    if m.total_trades < GATE_MIN_TRADES:
        reasons.append(f"Total trades ({m.total_trades}) < minimum ({GATE_MIN_TRADES})")
        next_steps.append("Extend backtest period or relax entry filters to get more trades")
        return DecisionResult(
            decision=Decision.ABANDON.value,
            confidence=Confidence.HIGH.value,
            reasons=reasons,
            metrics_summary=metrics_summary,
            gates_passed=gates,
            next_steps=next_steps,
            warnings=warnings,
        )

    # ── 2. Max iterations ────────────────────────────────────────
    if m.iteration >= MAX_ITERATIONS:
        reasons.append(f"Iteration {m.iteration} >= max ({MAX_ITERATIONS}) for this hypothesis")
        next_steps.append("PIVOT: Try a fundamentally different entry logic or timeframe")
        next_steps.append("Log all lessons learned before pivoting")
        return DecisionResult(
            decision=Decision.PIVOT.value,
            confidence=Confidence.HIGH.value,
            reasons=reasons,
            metrics_summary=metrics_summary,
            gates_passed=gates,
            next_steps=next_steps,
            warnings=warnings,
        )

    # ── 3. PF too low after N iterations ─────────────────────────
    if m.pf < ABANDON_PF_THRESHOLD and m.iteration >= ABANDON_PF_MIN_ITER:
        reasons.append(
            f"PF ({m.pf:.2f}) < {ABANDON_PF_THRESHOLD} after {m.iteration} iterations — no viable edge"
        )
        next_steps.append("ABANDON this hypothesis. The edge does not exist")
        return DecisionResult(
            decision=Decision.ABANDON.value,
            confidence=Confidence.HIGH.value,
            reasons=reasons,
            metrics_summary=metrics_summary,
            gates_passed=gates,
            next_steps=next_steps,
            warnings=warnings,
        )

    # ── 4. Monte Carlo catastrophic ──────────────────────────────
    if m.mc_p95_dd > ABANDON_MC_DD_THRESHOLD:
        reasons.append(
            f"MC P95 DD ({m.mc_p95_dd:.1f}%) > {ABANDON_MC_DD_THRESHOLD}% — catastrophic tail risk"
        )
        next_steps.append("Rethink position sizing and risk management from scratch")
        return DecisionResult(
            decision=Decision.ABANDON.value,
            confidence=Confidence.HIGH.value,
            reasons=reasons,
            metrics_summary=metrics_summary,
            gates_passed=gates,
            next_steps=next_steps,
            warnings=warnings,
        )

    # ── 5. WFA curve-fit ─────────────────────────────────────────
    if m.wfa_pass_rate < ABANDON_WFA_THRESHOLD and m.iteration >= ABANDON_WFA_MIN_ITER:
        reasons.append(
            f"WFA pass rate ({m.wfa_pass_rate:.0%}) < {ABANDON_WFA_THRESHOLD:.0%} after "
            f"{m.iteration} iterations — strategy is curve-fitted"
        )
        next_steps.append("Reduce parameters. Simplify entry logic. Consider different concept")
        return DecisionResult(
            decision=Decision.ABANDON.value,
            confidence=Confidence.HIGH.value,
            reasons=reasons,
            metrics_summary=metrics_summary,
            gates_passed=gates,
            next_steps=next_steps,
            warnings=warnings,
        )

    # ── 6. All quality gates pass → PROMOTE ──────────────────────
    if all(gates.values()):
        reasons.append("All quality gates passed")
        reasons.append(
            f"PF={m.pf:.2f}, DD={m.max_dd_pct:.1f}%, WFA={m.wfa_pass_rate:.0%}, "
            f"MC_P95={m.mc_p95_dd:.1f}%, trades={m.total_trades}"
        )
        next_steps.append("Run full 7-test robustness suite")
        next_steps.append("If robustness passes, strategy is deployment candidate")
        return DecisionResult(
            decision=Decision.PROMOTE.value,
            confidence=Confidence.HIGH.value,
            reasons=reasons,
            metrics_summary=metrics_summary,
            gates_passed=gates,
            next_steps=next_steps,
            warnings=warnings,
        )

    # ── 7/8. ITERATE — with improvement tracking ────────────────
    improving = True
    if m.prev_pf is not None:
        pf_delta = m.pf - m.prev_pf
        if pf_delta > 0.1:
            reasons.append(f"PF improved by {pf_delta:+.2f} (from {m.prev_pf:.2f} to {m.pf:.2f})")
        elif pf_delta > 0:
            reasons.append(f"PF marginally improved by {pf_delta:+.2f}")
            warnings.append("Improvement is small — consider whether further iteration is worthwhile")
        else:
            reasons.append(f"PF did not improve ({pf_delta:+.2f})")
            warnings.append("No improvement from previous iteration — risk of stalling")
            improving = False
    else:
        reasons.append(f"Iteration {m.iteration} — tracking started")

    # Build specific next-step recommendations based on failing gates
    if not gates["pf"]:
        next_steps.append(f"PF ({m.pf:.2f}) below {GATE_PF} — refine entry filter or session window")
    if not gates["dd"]:
        next_steps.append(
            f"DD ({m.max_dd_pct:.1f}%) above {GATE_DD}% — tighten SL, reduce lot size, "
            "or add drawdown circuit breaker"
        )
    if not gates["wfa"]:
        next_steps.append(
            f"WFA pass rate ({m.wfa_pass_rate:.0%}) below {GATE_WFA_PASS:.0%} — "
            "simplify strategy, reduce parameters"
        )
    if not gates["mc"]:
        next_steps.append(
            f"MC P95 DD ({m.mc_p95_dd:.1f}%) above {GATE_MC_P95_DD}% — "
            "add position sizing cap or diversify entries"
        )

    confidence = Confidence.MEDIUM.value if improving else Confidence.LOW.value

    return DecisionResult(
        decision=Decision.ITERATE.value,
        confidence=confidence,
        reasons=reasons,
        metrics_summary=metrics_summary,
        gates_passed=gates,
        next_steps=next_steps,
        warnings=warnings,
    )


def format_text(result: DecisionResult) -> str:
    """Format decision result as human-readable text."""
    icon = {
        "ITERATE": "🔄",
        "PIVOT": "↪️",
        "ABANDON": "🛑",
        "PROMOTE": "✅",
    }.get(result.decision, "❓")

    lines = [
        f"\n{'='*60}",
        f"  DECISION: {icon} {result.decision}  (Confidence: {result.confidence})",
        f"{'='*60}",
        "",
        "REASONS:",
    ]
    for r in result.reasons:
        lines.append(f"  • {r}")

    if result.warnings:
        lines.append("\nWARNINGS:")
        for w in result.warnings:
            lines.append(f"  ⚠ {w}")

    lines.append("\nGATES:")
    for gate, passed in result.gates_passed.items():
        status = "✅" if passed else "❌"
        lines.append(f"  {status} {gate}")

    lines.append("\nNEXT STEPS:")
    for i, step in enumerate(result.next_steps, 1):
        lines.append(f"  {i}. {step}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Alpha Pipeline Decision Framework — ITERATE / PIVOT / ABANDON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2
  python decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2 --prev-pf 1.20
  python decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2 --output decision.json
        """,
    )

    parser.add_argument("--pf", type=float, required=True, help="Profit Factor from MT5 backtest")
    parser.add_argument("--dd", type=float, required=True, help="Max Drawdown %% from MT5 backtest")
    parser.add_argument("--trades", type=int, required=True, help="Total trade count")
    parser.add_argument("--wfa", type=float, required=True, help="WFA OOS pass rate (0.0 - 1.0)")
    parser.add_argument("--mc", type=float, required=True, help="Monte Carlo P95 DD %%")
    parser.add_argument("--iter", type=int, required=True, help="Current iteration number")
    parser.add_argument("--prev-pf", type=float, default=None, help="PF from previous iteration")
    parser.add_argument("--tpm", type=float, default=None, help="Trades per month (optional)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON to stdout")

    args = parser.parse_args()

    metrics = StrategyMetrics(
        pf=args.pf,
        max_dd_pct=args.dd,
        total_trades=args.trades,
        wfa_pass_rate=args.wfa,
        mc_p95_dd=args.mc,
        iteration=args.iter,
        prev_pf=args.prev_pf,
        trades_per_month=args.tpm,
    )

    result = evaluate(metrics)
    result_dict = asdict(result)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        print(f"Decision written to: {args.output}")

    if args.json:
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))
    elif not args.output:
        print(format_text(result))

    # Exit code: 0 = PROMOTE, 1 = ITERATE, 2 = PIVOT, 3 = ABANDON
    exit_codes = {"PROMOTE": 0, "ITERATE": 1, "PIVOT": 2, "ABANDON": 3}
    sys.exit(exit_codes.get(result.decision, 1))


if __name__ == "__main__":
    main()
