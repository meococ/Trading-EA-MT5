# Readout — HYP-H1-THREEBAR-REV-001

Date: 2026-07-14  
Probe: `preflight/20260714_H1_THREEBAR_REV_OFFLINE_PROBE.json`  
EA: `EA_H1ThreeBarRev` (prereg frozen; contract built)  
Verdict: **`KILLED_AT_OFFLINE_PROBE`** — Model 0 **not run** (fail-closed)

## Offline metrics (closed-bar mirror, next-bar open, zero spread)

| Metric | Value |
|---|---|
| Trades | **1741** |
| PF | **1.037** |
| Net | +$16272 |
| Expectancy | +$9.35/trade |
| tpw elapsed | **~6.68**/wk (above kill band ≤6.0) |
| Win rate | 39.8% |

## Cost-stress (a priori +$12 report-only on synthetic)

| Stress | PF |
|---|---:|
| x1 | **0.990** |
| x1.5 | **0.967** |
| x2 | **0.945** |

All fail GOAL cost-stress. Optimistic zero-spread PF already ~1.04 → Model 0
with tester spread would be worse; ceremony withheld.

## Gates

KILL_PROBE: tpw ∉ [1.0, 6.0] **and** pf_cost_x1 < 1.0.  
Do **not** retune MinBodyFrac / MaxPerDay / RR from this probe. Not PIN densify.

## Cost honesty

`UNVERIFIED_SYNTHETIC_PLUS_REPORT_ONLY_12`. Not Real QFSI. Not GOAL.
