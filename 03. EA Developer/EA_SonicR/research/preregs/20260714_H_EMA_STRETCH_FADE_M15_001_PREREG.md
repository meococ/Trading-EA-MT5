# Prereg — HYP-EMA-STRETCH-FADE-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-EMA-STRETCH-FADE-M15-001`
- EA: `EA_M15EMAStretchFade`
- Path: `03. EA Developer/EA_M15EMAStretchFade/EA_M15EMAStretchFade.mq5`
- Parent: none — pure EMA stretch MR; not ADR/ChopMR/Pivot rescue

## Thesis

On closed M15 `bar[1]`, if `|Close−EMA20|/ATR14 ≥ 1.50` (and ≤4.0), fade
toward EMA during Europe `[9,17)`. Mon–Thu, weekend flat, risk 0.5%, max 2/day.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision | closed `bar[1]` |
| EMA / ATR | 20 / 14 |
| Stretch | ≥1.50 ATR; max 4.0 |
| Trade window | `[9,17)`; flat 21 |
| Days | Mon–Thu |
| Risk / SL/TP | 0.50%; bar extreme±ATR×0.25; toward EMA / 1.0R |
| Caps | 2/day; hold 24; spread≤50 |
| Magic | 880944 |
| Cost | tester `current`; missing≠0 |

Banned: stretch/EMA/hour/day mining; flip to momentum; ADR% twin rescue.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000
- Kill: tpw∉[1.0,6.0] or PF<1.00 or N<80
- Park: PF∈[1.00,1.30) cadence OK, or PF≥1.30 tpw<2.0
- HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (not confirmed)

## Independence

`readouts/20260714_EMA_STRETCH_FADE_VS_ADR_CHOPMR_DEDUP_CLEARANCE.md`  
Probe: `readouts/20260714_HYP_EMA_STRETCH_FADE_M15_001_PROBE.md`
