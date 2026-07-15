# Prereg — HYP-SB-COSTBUFFER-ATRSTOP-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner secondary after RR2 PARK on GOAL x1.5 stress

## Identity

- Hypothesis ID: `HYP-SB-COSTBUFFER-ATRSTOP-001`
- EA: `EA_SilverBullet` (`EA_SilverBullet_v2.mq5`)
- Parent: `HYP-SB-MAXKZ2-DENSITY-002` (`20260714_192304`)
- Sibling friction: `HYP-SB-MAXKZ2-RR2-FRICTION-001` (`20260714_194221`) PARK on
  GOAL loss×1.5 — **not stacked**
- De-dup: `readouts/20260714_COSTBUFFER_ATRSTOP_VS_RR2_DEDUP_CLEARANCE.md`

## Thesis

RR2 thickened winners (TP RR 2.0) but loss-side ×1.5 still kills GOAL stress.
Child freezes a priori tighter SL buffer `InpSL_ATR=1.0` (from 1.50) on MaxKZ2
entry geometry with **default TP RR 1.5**. Goal: shrink average loss dollars so
loss-side stress may clear ≥1.25 / ≥1.00 without densifying or retuning RR.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Overrides | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpSL_ATR=1.0;InpUseWeekendFlat=1` |
| Control | MaxKZ2 `20260714_192304` (InpSL_ATR=1.50 default) |

## Kill / Park / HIT

| Gate | Rule |
|---|---|
| KILL | PF < 1.00 or tpw outside [1.0, 6.0] or N < 80 |
| PARK | Survives kill but PF ≤ 1.30 or tpw outside [2, 5] |
| HIT research bar | PF > 1.30 ∧ tpw ∈ [2, 5] under tester `current` |
| Friction note | After Model 0: sonic_cost_stress base+$12 and/or loss×1.5; fail ≠ retune SL |

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Missing ≠ 0. Not confirmed / not GOAL.

## Banned

- Stacking RR2 overrides onto this ID
- Raising MaxTradesPerKZ / MaxPerDay / Mon–Thu
- Mining SL from Model 0 losers (new ID required)
- Claiming GOAL from Demo
