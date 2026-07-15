# Prereg — HYP-WEEKLY-HL-BREAK-H4-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner thick-expectancy rebuild after HARD_EMPTY_CONTINUES; GPT waived

## Identity

- Hypothesis ID: `HYP-WEEKLY-HL-BREAK-H4-001`
- EA: `EA_WeeklyHLBreak_H4`
- Path: `03. EA Developer/EA_WeeklyHLBreak_H4/EA_WeeklyHLBreak_H4.mq5`
- Parent: thick-edge wave (W1 structure break; RR=3; cadence via multi-symbol stub if sparse)

## Thesis

Prior completed calendar week (W1[1]) high/low is a structural level distinct
from PDH/PDL. First closed H4 beyond that level in the new week enters
continuation with pre-registered RR=3.0 and SL keyed to a fraction of the
prior week range. Multi-day hold inside the week; weekend flat.
Primary Model 0 = USDJPY. If HIT but cadence sparse, next legal path is
a priori multi-symbol EURUSD+GBPUSD+USDJPY pool — not day densify.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H4 (primary) |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Level | W1[1] high / low |
| Entry | first H4 close beyond level this week |
| Days | Mon–Thu; Fri off |
| Risk | 0.50%; max 1/day; TP 3.0R; SL = 0.35× week range (clamped) |
| Flat | Fri / weekend; max hold 40 H4 bars |
| Magic | 880992 |
| Overrides | (none) |

## De-dup

`readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md`

## Kill / Park / HIT

Standard Model 0 research bar; on HIT run cost-stress x1.5/x2 vs RR2.

## Banned

- Retune to PDH; mine week filters / RR / days from readout
- Rescue PDH-break / PDH-retest / LNY DualWin
