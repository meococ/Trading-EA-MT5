# Prereg — HYP-ENGULF-TREND-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuke ~19:29; systems critic #2

## Identity

- Hypothesis ID: `HYP-ENGULF-TREND-M15-001`
- EA: `EA_M15EngulfTrend`
- Path: `03. EA Developer/EA_M15EngulfTrend/EA_M15EngulfTrend.mq5`
- Parent: modernize `EA_EngulfTrend` — **drop CI/Chop** (Chop shelf dead); D1 EMA50; Mon–Thu a priori

## Thesis

Closed-bar engulfing (bar[1] body engulfs bar[2] body) with D1 EMA50 alignment in London–NY window `[8,18)`. Pattern OHLC edge independent of SB KZ / ORB / ITSM pullback. No Choppiness filter.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Engulf | min body 0.45·ATR; no vol confirm |
| Trend | D1 EMA50 required |
| Session | `[8,18)`; flat 21; Mon–Thu |
| Risk | 0.50%; max 2/day; TP 1.5R |
| Magic | 880962 |
| CI/Chop | **OFF** (removed) |

Banned: re-enable CI; skip-Tue mine; hour retune from readout.

## Kill / Park / HIT

Standard Model 0 research bar.

## Cost honesty

Tester `current` research-proxy only.
