# Prereg — HYP-PDH-RETEST-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuild after HARD_EMPTY_SHELF (VWAP/ATF/HBOS KILL); GPT waived

## Identity

- Hypothesis ID: `HYP-PDH-RETEST-M15-001`
- EA: `EA_M15PDHRetest`
- Path: `03. EA Developer/EA_M15PDHRetest/EA_M15PDHRetest.mq5`
- Parent: independent of parked `HYP-PDH-BREAK-M15-001` (immediate break continuation)

## Thesis

Prior-day high/low (D1 shift≥1) break arms a continuation state. Entry is **not**
on the break bar; entry requires a later closed M15 retest+reject of the broken
level (touch near level, close holds beyond). Mechanism = acceptance after
break via retest — different from immediate break continuation and opposite of
LiqSweep fade.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Levels | D1 high/low shift 1 |
| Break arm | body≥0.40; ATR×0.10 beyond PDH/PDL; D1 EMA50 |
| Retest | ≥1 bar after arm; touch ATR×0.25; reject ATR×0.10; max 24 bars |
| Session | [9,17); flat 21; Mon–Thu |
| Risk | 0.50%; max 1/day; TP 1.5R; SL level±ATR×0.20 |
| Magic | 880981 |
| Overrides | (none) |

## De-dup

See `readouts/20260714_PDH_RETEST_VS_PDHBREAK_DEDUP_CLEARANCE.md`.

## Kill / Park / HIT

- Kill: PF < 1.00 **or** tpw outside [1.0, 6.0] **or** N < 80
- Park: PF ∈ [1.00, 1.30) with cadence OK
- HIT research bar: PF > 1.30 ∧ tpw ∈ [2.0, 5.0] → cost-stress x1.5/x2 immediately

## Banned

- Retuning buffer/body/retest ATR from readout
- Day/hour mine; flip to fade; rescue PDH-BREAK densify
