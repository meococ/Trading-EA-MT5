# Prereg — HYP-H1-SWING-FAILURE-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-H1-SWING-FAILURE-001`
- EA: `EA_H1SwingFailure`
- Path: `03. EA Developer/EA_H1SwingFailure/EA_H1SwingFailure.mq5`
- Parent: null (structure-based swing failure ≠ ORB-fade)

## Thesis

A confirmed H1 pivot (L=2) that is pierced and then closed back inside is a
failed structural break; fading toward the interior with SL beyond pierce
extreme has positive expectancy after tester costs on USDJPY.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY H1 |
| Decision | closed `bar[1]` |
| Pivot | L=2 each side; confirmed at shift≥3 |
| Pierce buffer | ATR×0.05 |
| Body gate | body/range ≥ 0.30 |
| Days | Mon–Thu; Fri off; weekend flat |
| Trade hours | `[1,21)`; flat 22 |
| Risk / SL/TP | 0.50%; pierce±ATR×0.15; TP=1.5R |
| Caps | 1/day; one use per swing level; hold ≤24; spread≤50 |
| Magic | 880951 |
| Cost | tester `current`; missing≠0 |

Banned: PivotL mining, day/hour mining, ORB/PDH retarget, Viper M15 rescue.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000
- Kill: tpw∉[1.0,6.0] or PF<1.00 or N<80
- Park: PF∈[1.00,1.30) cadence OK, or PF≥1.30 tpw<2.0
- HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (not confirmed)

## Independence

`readouts/20260714_H1_SWING_FAILURE_VS_ORB_LIQSWEEP_DEDUP_CLEARANCE.md`  
Probe: `readouts/20260714_HYP_H1_SWING_FAILURE_001_PROBE.md`
