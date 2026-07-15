# Prereg — HYP-SB-MAXKZ2-RR2-FRICTION-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner iterate continuation; cost-stress V3
`STRUCTURAL_FRICTION_DEAD_END_CANDIDATE` on MaxKZ2/books

## Identity

- Hypothesis ID: `HYP-SB-MAXKZ2-RR2-FRICTION-001`
- EA: `EA_SilverBullet` (`EA_SilverBullet_v2.mq5`)
- Parent: `HYP-SB-MAXKZ2-DENSITY-002` (`20260714_192304`)
- Probe: `OFFLINE_SB_FRICTION_RR2_PROBE_V1` SHA256
  `BEFF235F1FAFD86B69F02871766B39C3CCE1CA46F1E51BF104FFD6AF7996BC30`

## Thesis

MaxKZ2 clears research PF>1.30 ∧ 2–5/wk under tester-`current`, but V3
cost-stress shows break-even to PF=1.30 at ~$1.30/trade and GOAL-style
loss-side x1.5/x2 **KILL**. Edge is friction-thin, not cadence-thin.

Child freezes TP R:R stretch **1.50 → 2.00** on both London and NY KZ
(`InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0`) while keeping MaxKZ2 entry geometry
verbatim. Goal: thicken winner dollars so the book survives a realistic
$/trade haircut without densifying entries.

Offline probe used an **optimistic** winner-PnL scale (losers unchanged;
timeouts ignored). Verdict
`PROBE_WEAK_SURVIVOR_MODEL0_OPTIONAL_FRICTION_STILL_FAILS_X15`:
optimistic H0 PF 1.78 / H@$2 PF 1.72, but loss×1.5 still PF 1.19 < 1.25.
Model 0 is authorized as falsification, not as a rescue claim.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Overrides | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpUseWeekendFlat=1` |
| Control | MaxKZ2 `20260714_192304` (RR=1.5 defaults) |

## De-dup clearance

- Not MaxKZ densify (>2 banned)
- Not NYPM / MaxHold / ITSM session / London-only
- Not USBILL rescue
- Not EURUSD transfer (`HYP-SB-MAXKZ2-EURUSD-TRANSFER-001` separate)
- Not hour/day mine from cost-stress or Spark hour-11 weakness

## Kill / Park / HIT (research screen)

| Gate | Rule |
|---|---|
| KILL | PF < 1.00 or tpw outside [1.0, 6.0] or N < 80 |
| PARK | Survives kill but PF ≤ 1.30 or tpw outside [2, 5] |
| HIT research bar | PF > 1.30 ∧ tpw ∈ [2, 5] under tester `current` |
| Friction note | Offline recompute $2/trade + loss×1.5 after Model 0; x1.5 still expected fail under honesty |

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Missing cost ≠ 0. Not confirmed / not GOAL.
Optimistic offline probe is **not** execution proof.

## Banned

- Raising MaxTradesPerKZ further
- Mining RR from Model 0 losers
- Claiming GOAL from Demo
- Retuning RR to 2.5/3.0 from this readout (needs new ID)
