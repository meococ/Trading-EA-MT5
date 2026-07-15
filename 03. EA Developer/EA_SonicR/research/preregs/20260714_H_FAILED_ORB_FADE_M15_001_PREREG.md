# Prereg — HYP-FAILED-ORB-FADE-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (no ChatGPT)

## Identity

- Hypothesis ID: `HYP-FAILED-ORB-FADE-M15-001`
- EA: `EA_M15FailedORBFade`
- Path: `03. EA Developer/EA_M15FailedORBFade/EA_M15FailedORBFade.mq5`
- Parent: opposite of parked LondonORB break-continuation (not a rescue retune)

## Thesis

London first-hour OR `[9,10)` locks. A closed M15 `bar[1]` that pierces OR
high/low then closes back inside is a failed auction; fade toward OR mid with
SL beyond pierce extreme. Mon–Thu, weekend flat, risk 0.5%, max 1/day.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY M15 |
| Decision | closed `bar[1]` |
| ORB window | `[9,10)` build; lock ≥10 (a priori = LondonORB) |
| Range gate | ATR×`[0.25, 2.50]` |
| Pierce buffer | ATR×0.05 |
| Trade window | `[10,16)`; flat 21 |
| Days | Mon–Thu |
| Risk / SL/TP | 0.50%; pierce±ATR×0.15; mid or 1.5R |
| Caps | 1/day; hold 32; spread≤50 |
| Magic | 880943 |
| Cost | tester `current`; missing≠0 |

Banned: OR hour retune, day mining, flip to breakout, LondonORB rescue.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 10000
- Kill: tpw∉[1.0,6.0] or PF<1.00 or N<80
- Park: PF∈[1.00,1.30) cadence OK, or PF≥1.30 tpw<2.0
- HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (not confirmed)

## Independence

`readouts/20260714_FAILED_ORB_FADE_VS_LONDONORB_DEDUP_CLEARANCE.md`  
Probe: `readouts/20260714_HYP_FAILED_ORB_FADE_M15_001_PROBE.md`
