# Prereg — HYP-H1-ATR-REGIME-MOM-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-H1-ATR-REGIME-MOM-001`
- EA: `EA_H1ATRRegimeMom`
- Path: `03. EA Developer/EA_H1ATRRegimeMom/EA_H1ATRRegimeMom.mq5`
- Parent: null (new H1 vol-regime directional family)

## Thesis

When H1 realized volatility is elevated relative to its slow baseline
(`ATR14 / SMA50(ATR) ≥ 1.20`), directional continuation of closed-bar side vs
EMA50 has positive expectancy after tester costs. Not mean-reversion stretch.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY H1 |
| Decision | closed `bar[1]` |
| Regime gate | ATR14 / SMA50(ATR) ≥ **1.20** |
| Direction | close vs EMA50 |
| Body gate | body/range ≥ 0.35 |
| Days | Mon–Thu; Fri off; weekend flat |
| Trade hours | `[1,21)`; flat 22 |
| Risk / SL/TP | 0.50%; SL=1.5×ATR; TP=1.5R |
| Caps | 1/day; hold ≤24 H1; spread≤50 |
| Magic | 880950 |
| Cost | tester `current`; missing≠0 |

Banned: ATR-ratio mining, EMA/day/hour mining, flip to fade, VolExp rescue.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000
- Kill: tpw∉[1.0,6.0] or PF<1.00 or N<80
- Park: PF∈[1.00,1.30) cadence OK, or PF≥1.30 tpw<2.0
- HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (not confirmed)

## Independence

`readouts/20260714_H1_ATR_REGIME_MOM_VS_VOLEXP_CHOP_DEDUP_CLEARANCE.md`  
Probe: `readouts/20260714_HYP_H1_ATR_REGIME_MOM_001_PROBE.md`
