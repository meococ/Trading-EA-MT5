# Prereg — HYP-D1-TREND-H4-PB-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner thick-expectancy rebuild after HARD_EMPTY_CONTINUES; GPT waived

## Identity

- Hypothesis ID: `HYP-D1-TREND-H4-PB-001`
- EA: `EA_D1TrendH4PB`
- Path: `03. EA Developer/EA_D1TrendH4PB/EA_D1TrendH4PB.mq5`
- Parent: thick-edge wave (HTF trend + H4 value PB; RR=3 multi-day)

## Thesis

Closed D1 close vs EMA50 sets directional bias. On H4, a pullback that
touches EMA20 within the last 3 closed bars, then closes back on the trend
side of EMA20 with a same-direction body, enters with pre-registered RR=3.0.
Multi-day hold allowed inside the week; weekend flat. Independent of H1
ATR-regime momentum, EMA stretch fade, and M15 ITSM/H1-BOS pullbacks.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY H4 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| D1 bias | close[1] vs EMA50_D1 |
| H4 entry | EMA20 touch in bars[1..3] + reclaim close + body |
| Days | Mon–Thu; Fri off |
| Risk | 0.50%; max 1/day; TP 3.0R; SL 1.0×ATR_H4 beyond PB extreme |
| Flat | Fri / weekend; max hold 30 H4 bars |
| Magic | 880991 |
| Overrides | (none) |

## De-dup

`readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md`

## Kill / Park / HIT

Standard Model 0 research bar; on HIT run cost-stress x1.5/x2 vs RR2.

## Banned

- Flip to fade; mine EMA periods / RR / days from readout
- Rescue H1-ATR-mom or ITSM
