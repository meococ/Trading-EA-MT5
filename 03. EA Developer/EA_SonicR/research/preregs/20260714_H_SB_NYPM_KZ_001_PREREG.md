# Prereg — HYP-SB-NYPM-KZ-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Author: local self-research (Owner rebuild/iteration auth; no ChatGPT)

## Identity

- Hypothesis ID: `HYP-SB-NYPM-KZ-001`
- Parent: `HYP-SB-WEEKEND-FLAT-001` (A1 parked)
- EA: `EA_SilverBullet` / `EA_SilverBullet_v2.mq5`
- Feature family: `silverbullet_nypm_killzone_session_expand`

## Thesis

Adding the pre-existing NY PM kill zone `[20,22)` as an a priori session
structure (input already in source, default off) increases eligible SilverBullet
setup density while keeping A1 weekend-flat. This is a **session-window variant
frozen before run**, not a post-hoc hour veto mined from A1 readout.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Model | 0 |
| Deposit | 100000 |
| Control baseline | A1 `20260714_002505` (InpUseNYPM=0 + weekend flat) |
| Challenger | `InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseNYPM=1;InpNYPM_Start=20;InpNYPM_End=22` |
| Cost | tester `current`; missing≠0 |

Banned: retuning NYPM hours from readout; combining with MaxHold in this ID;
mining Fri cutoff; flipping KZ off after seeing PF.

## Kill / Park

- Kill: PF < 1.00 or N < 80 or tpw ∉ [1.0, 6.0]
- Park: survives kill, GOAL unmet
- HIT_RESEARCH_BAR: PF>1.30 and tpw∈[2.0,5.0] (not confirmed)
