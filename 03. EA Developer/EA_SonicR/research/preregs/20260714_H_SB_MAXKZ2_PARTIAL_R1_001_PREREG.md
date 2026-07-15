# Prereg — HYP-SB-MAXKZ2-PARTIAL-R1-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner post-cost rebuild; SB exit/risk (not densify)  
Parent: `HYP-SB-MAXKZ2-DENSITY-002` (`20260714_192304`) — FAIL under Real-P50

## Identity

- Hypothesis ID: `HYP-SB-MAXKZ2-PARTIAL-R1-001`
- EA: `EA_SilverBullet` (`EA_SilverBullet_v2.mq5`)
- Exit rebuild: bank **50% at 1R**, runner to default TP 1.5R; trail OFF
- Explicitly **not**: MaxTradesPerKZ>2 densify; NYPM; RR retune from readout;
  ATR-stop retune (`HYP-SB-COSTBUFFER-ATRSTOP-001` already PARK)

## Thesis

MaxKZ2 clears research PF under tester-`current` but fails GOAL cost-stress
under caveated Real P50 (~$2.31). Entry geometry stays MaxKZ2+A1 weekend-flat.
Structural **partial-close** realizes half risk earlier so net expectancy after
additive haircut can improve without adding trade density.

Backlog seed `HYP-SB-PARTIAL-R1-001` (A1) is **not** reused — this ID binds
explicitly to MaxKZ2 parent that failed Real stress.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Entry | MaxKZ2 + weekend flat A1 (same as parent) |
| Exit | `InpPartialClose=1;InpPCL_TriggerR=1.0;InpPCL_ClosePct=0.50` |
| Trail | OFF |
| TP RR | default 1.5 LDN/NY (not RR2 stack) |
| Overrides | `InpMaxTradesPerKZ=2;InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpRiskPct=0.5;InpPartialClose=1;InpPCL_TriggerR=1.0;InpPCL_ClosePct=0.5;InpUseTrail=0` |

## Kill / Park / HIT

| Gate | Rule |
|---|---|
| KILL | PF < 1.00 or tpw ∉ [1.0, 6.0] or N < 80 |
| PARK | Survives kill but PF ≤ 1.30 or joint cadence fail |
| HIT | PF > 1.30 ∧ tpw ∈ [2, 5] |

On HIT: diagnostic Real-P50 haircut stress — not verified QFSI.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Missing slip ≠ 0. Not GOAL.
