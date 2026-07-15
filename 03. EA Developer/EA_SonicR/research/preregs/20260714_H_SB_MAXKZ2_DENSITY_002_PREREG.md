# Prereg — HYP-SB-MAXKZ2-DENSITY-002

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Campaign: Owner rebuild (2026-07-14 ~19:09 ICT)  
Parent: `HYP-SB-WEEKEND-FLAT-001` A1 parked (PF ~1.34 / ~1.99/wk)  
Author: local structural densify — a-priori option set with NYPM sibling

## Identity

- Hypothesis ID: `HYP-SB-MAXKZ2-DENSITY-002`
- EA name: `EA_SilverBullet` (`EA_SilverBullet_v2.mq5`)
- Path: `03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5`
- Sibling density arm vs `HYP-SB-NYPM-KZ-001` (not post-hoc after NYPM)
- Explicitly **not**: Friday mine; hour retune; MaxHold combined in this ID

## Thesis

Alternate density contract: keep LDN+NYAM only (NYPM off) but raise
**max trades per kill-zone** from 1 → 2 (`InpMaxTradesPerKZ=2`). Structural
entry-density within frozen sessions — aims to clear ≥2.0 tw/w without adding
a third session. Weekend-flat A1 + risk 0.5% retained.

## Locked Design

| Item | Frozen value |
|---|---|
| Symbol / TF | USDJPY M15 |
| Sessions | LDN + NYAM on; NYPM **off** (default) |
| Density | `InpMaxTradesPerKZ=2` |
| Weekend flat | A1 on: Fri 21:45 |
| Risk | 0.50% |
| Cost | research-proxy tester `current`; missing ≠ 0 |
| Deposit | 100000 |

Banned: raise MaxTradesPerDay from readout; enable NYPM after this fail
without new ID; Friday cutoff mine.

## Test Plan

- Model 0; 2021.01.01–2025.12.31; Deposit 100000; Leverage 100
- Overrides:
  `InpMaxTradesPerKZ=2;InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpRiskPct=0.5`
- Kill if PF < 1.00 or trades/week outside `[1.5, 6.0]` or N < 80
- Near-miss if PF≥1.00 cadence OK but fails joint GOAL research bar
- HIT_RESEARCH_BAR if PF > 1.30 and cadence in `[2.0, 5.0]` (still not confirmed)

## Cost honesty

Tester spread ≠ Real QFSI. No GOAL claim from this screen alone.
