# DECISION FRAMEWORK — Programmatic Strategy Evaluation

> **Version:** 1.0 | **Date:** 2026-03-10
> **Purpose:** Formal decision tree for ITERATE / PIVOT / ABANDON decisions.
> **Implementation:** `analysis/decision_framework.py`

---

## 1. OVERVIEW

Every strategy run ends with one of three decisions:

| Decision | Meaning | Action |
|----------|---------|--------|
| **ITERATE** | Strategy shows promise, needs specific improvement | Change ONE parameter/filter, re-run |
| **PIVOT** | Hypothesis exhausted, try different approach | New entry logic, different timeframe, or different concept |
| **ABANDON** | No viable edge found | Stop. Log lessons. Move on |

---

## 2. INPUT METRICS

| Input | Source | Type |
|-------|--------|------|
| `pf` | MT5 backtest report | float (Profit Factor) |
| `max_dd_pct` | MT5 backtest report | float (Max DD as % of account) |
| `total_trades` | MT5 backtest report | int |
| `wfa_pass_rate` | walk_forward.py output | float (0.0 - 1.0) |
| `mc_p95_dd` | monte_carlo.py output | float (P95 DD as %) |
| `iteration` | Manual tracking | int (iteration # for this hypothesis) |
| `prev_pf` | Previous run | float (for improvement tracking) |

---

## 3. DECISION TREE

```
                            ┌─ START ─┐
                            │         │
                    ┌───────▼─────────┐
                    │ trades < 200?   │
                    └───┬─────────┬───┘
                      YES         NO
                       │           │
              ┌────────▼──┐  ┌────▼────────────┐
              │ ABANDON   │  │ iteration >= 5?  │
              │ (too few  │  └───┬──────────┬───┘
              │  trades)  │    YES          NO
              └───────────┘     │            │
                       ┌────────▼──┐   ┌────▼────────────────┐
                       │  PIVOT    │   │ PF < 1.05 AND       │
                       │ (max iter)│   │ iteration >= 3?     │
                       └───────────┘   └───┬──────────┬──────┘
                                         YES          NO
                                          │            │
                                 ┌────────▼──┐   ┌────▼────────────┐
                                 │ ABANDON   │   │ MC P95 DD > 50%?│
                                 │ (no edge) │   └───┬──────────┬──┘
                                 └───────────┘     YES          NO
                                                    │            │
                                           ┌────────▼──┐   ┌────▼────────────┐
                                           │ ABANDON   │   │ WFA pass < 40%  │
                                           │ (tail     │   │ AND iter >= 2?  │
                                           │  risk)    │   └───┬──────────┬──┘
                                           └───────────┘     YES          NO
                                                              │            │
                                                     ┌────────▼──┐   ┌────▼──────────┐
                                                     │ ABANDON   │   │ QUALITY GATES  │
                                                     │ (overfit) │   │ ALL PASS?      │
                                                     └───────────┘   └───┬─────────┬──┘
                                                                       YES         NO
                                                                        │           │
                                                               ┌────────▼──┐  ┌────▼──────────┐
                                                               │ PROMOTE   │  │ Improvement   │
                                                               │ (run full │  │ from prev?    │
                                                               │ robust)   │  └───┬────────┬──┘
                                                               └───────────┘    YES        NO
                                                                                 │          │
                                                                        ┌────────▼──┐ ┌────▼────┐
                                                                        │ ITERATE   │ │ ITERATE │
                                                                        │ (continue)│ │ (warn:  │
                                                                        └───────────┘ │ stalled)│
                                                                                      └─────────┘
```

---

## 4. QUALITY GATE THRESHOLDS

| Gate | Threshold | Hard/Soft |
|------|-----------|-----------|
| PF | >= 1.4 | Hard |
| Max DD | <= 15% | Hard |
| WFA OOS PF | >= 1.0 (pass rate >= 60%) | Hard |
| MC P95 DD | <= 15% | Hard |
| Trades/month | >= 20 | Soft (warn if < 20) |
| Total trades | >= 200 | Hard |

---

## 5. ABANDON TRIGGERS (Hard Stop)

| Condition | Min Iterations | Confidence |
|-----------|---------------|------------|
| PF < 1.05 | 3 | HIGH — no edge exists |
| WFA < 40% | 2 | HIGH — curve-fitted |
| MC P95 DD > 50% | 1 | HIGH — catastrophic tail risk |
| trades < 200 | 1 | HIGH — insufficient data |
| No improvement for 2 consecutive iterations | 2 | MEDIUM — diminishing returns |

---

## 6. ITERATE GUIDANCE

When decision is ITERATE, provide specific next-step recommendations:

| Current Problem | Suggested Fix |
|----------------|---------------|
| PF < 1.4 but > 1.1 | Add/refine entry filter (session, trend, volatility) |
| DD > 15% but < 30% | Reduce position size, tighten SL, add time-based exit |
| WFA 40-60% | Simplify strategy (reduce params), widen parameter ranges |
| MC P95 DD 15-30% | Add drawdown circuit breaker, diversify entry conditions |
| Low trade count | Relax entry filters, consider lower timeframe |

---

## 7. PIVOT GUIDANCE

When decision is PIVOT, recommend direction change:

| Exhausted Approach | Suggested Pivot |
|-------------------|-----------------|
| Breakout failed | Try mean-reversion |
| Single timeframe failed | Try multi-timeframe confirmation |
| Single session failed | Try cross-session or session rotation |
| Trend-following failed | Try range/volatility-based |
| 5+ iterations with < 0.1 PF gain | Different instrument or concept entirely |

---

## 8. OUTPUT FORMAT

```json
{
  "decision": "ITERATE|PIVOT|ABANDON|PROMOTE",
  "confidence": "HIGH|MEDIUM|LOW",
  "reasons": [
    "Primary reason for decision",
    "Supporting evidence"
  ],
  "metrics_summary": {
    "pf": 1.35,
    "max_dd_pct": 12.5,
    "total_trades": 450,
    "wfa_pass_rate": 0.6,
    "mc_p95_dd": 18.2,
    "iteration": 2
  },
  "gates_passed": {
    "pf": true,
    "dd": true,
    "wfa": true,
    "mc": false,
    "trades": true
  },
  "next_steps": [
    "Specific actionable recommendation"
  ]
}
```

---

## 9. CLI USAGE

```bash
# Basic usage
python analysis/decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2

# With previous PF for improvement tracking
python analysis/decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2 --prev-pf 1.20

# Output to JSON file
python analysis/decision_framework.py --pf 1.35 --dd 12.5 --trades 450 --wfa 0.6 --mc 18.2 --iter 2 --output decision.json
```
