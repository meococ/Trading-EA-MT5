# Prereg — HYP-H4-NR7-BREAK-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner thick-expectancy rebuild after HARD_EMPTY_CONTINUES; GPT waived

## Identity

- Hypothesis ID: `HYP-H4-NR7-BREAK-001`
- EA: `EA_H4NR7Break`
- Path: `03. EA Developer/EA_H4NR7Break/EA_H4NR7Break.mq5`
- Parent: thick-edge wave (compression→expansion; fewer-but-fatter RR=3)

## Thesis

Closed H4 bar that is the narrowest range of the prior 7 H4 bars (NR7)
is followed by the next closed H4 closing beyond that NR7 high/low →
continuation. Pre-registered RR=3.0 so expectancy/trade can clear friction
without densifying MaxKZ/RR2. Not VolExp M15 / Keltner / H4-struct BOS.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H4 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| NR lookback | 7 (classic Crabel NR7) |
| Entry | closed bar[1] beyond NR7 bar[2] high/low |
| Days | Mon–Thu; Fri off |
| Risk | 0.50%; max 1/day; TP 3.0R; SL at NR7 opposite ±0.1 ATR_H4 |
| Flat | Fri / weekend; max hold 20 H4 bars |
| Magic | 880990 |
| Overrides | (none) |

## De-dup

`readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md`

## Kill / Park / HIT

Standard Model 0 research bar; on HIT run cost-stress x1.5/x2 vs RR2.

## Banned

- Retune NR length / RR / day from readout
- Rescue as M15 densify or H4-struct twin
