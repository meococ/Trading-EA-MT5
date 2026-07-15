# Prereg — HYP-D1-TREND-H1-PB-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner post-Wave5 rebuild path **B**  
GPT: waived

## Identity

- Hypothesis ID: `HYP-D1-TREND-H1-PB-001`
- EA: `EA_D1TrendH1PB`
- Path: `03. EA Developer/EA_D1TrendH1PB/EA_D1TrendH1PB.mq5`
- Explicitly **not**: H4-PB densify; ATR-regime-mom densify; ATR%ile Donchian;
  AUDJPY/GBPJPY lead; Wave5 densify

## Thesis

Closed **D1** EMA50 bias sets direction. On **H1**, price pulls back to EMA21
within lookback then **reclaims** with closed-bar[1] body in trend direction.
RR=2.5 + MaxPerDay=2 targets joint thick expectancy and 2–5/wk cadence
(H4 sibling was cadence-thin).

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| D1 bias | close[1] vs EMA50 D1 shift≥1 |
| H1 PB | touch EMA21 within lookback 4 bars; reclaim close beyond EMA21 with directional body |
| Body | \|close−open\| ≥ 0.30×ATR(14) H1 |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| SL | 1.25×ATR beyond PB extreme |
| Max/day | 2 |
| Flat | hour≥22 / weekend; max hold 24 H1 |
| Magic | 880998 |
| Overrides | (none) |

## Kill / Park / HIT

| Gate | Rule |
|---|---|
| KILL | PF &lt; 1.00 or tpw ∉ [1.0, 6.0] or N &lt; 80 |
| PARK | Survives kill but PF ≤ 1.30 or tpw ∉ [2, 5] |
| HIT | PF &gt; 1.30 ∧ tpw ∈ [2, 5] under tester `current` |

On PF≥1.20: a priori `sonic_cost_stress` base+$12 x1.5/x2 diagnostic.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.

## Independence

`readouts/20260714_D1_TREND_H1_PB_DEDUP_CLEARANCE.md`
