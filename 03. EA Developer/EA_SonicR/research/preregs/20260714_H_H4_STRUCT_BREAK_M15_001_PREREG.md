# Prereg — HYP-H4-STRUCT-BREAK-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuild after HARD_EMPTY_SHELF; GPT waived

## Identity

- Hypothesis ID: `HYP-H4-STRUCT-BREAK-M15-001`
- EA: `EA_H4StructBreak_M15`
- Path: `03. EA Developer/EA_H4StructBreak_M15/EA_H4StructBreak_M15.mq5`
- Parent: independent of killed `HYP-H1-BOS-M15-PB-001` (H1 swing + EMA pullback)

## Thesis

H4 closed-bar swing break (pivot L=2) defines structure shift. M15 enters on
closed-bar[1] **acceptance** beyond the broken H4 swing with body confirmation —
not EMA densify of the killed H1-BOS book. Slower HTF → thicker invalidation
(swing reclaim) and structurally lower cadence than H1-BOS.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 (structure via PERIOD_H4) |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Swing L | 2; BOS max age 12 H4 bars |
| Entry | M15 body≥0.40 close beyond swing ± ATR×0.05 |
| Session | [7,18); flat 21; Mon–Thu |
| Risk | 0.50%; max 1/day; TP 1.5R; SL swing±ATR×0.20 |
| Magic | 880982 |
| Overrides | (none) |

## De-dup

See `readouts/20260714_H4_STRUCT_VS_H1BOS_DEDUP_CLEARANCE.md`.

## Kill / Park / HIT

Standard Model 0 research bar; on HIT run cost-stress x1.5/x2.

## Banned

- Mining SwingL / EMA transplant from H1-BOS
- Day/hour mine; flip to fade
