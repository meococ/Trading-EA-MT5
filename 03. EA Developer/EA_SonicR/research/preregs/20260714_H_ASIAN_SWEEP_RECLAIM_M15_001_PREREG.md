# Prereg — HYP-ASIAN-SWEEP-RECLAIM-M15-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuke ~19:29 — R&D continues without QFSI-wait; free MT Model 0

## Identity

- Hypothesis ID: `HYP-ASIAN-SWEEP-RECLAIM-M15-001`
- EA: `EA_M15AsianSweepReclaim`
- Path: `03. EA Developer/EA_M15AsianSweepReclaim/EA_M15AsianSweepReclaim.mq5`
- Parent: independent (trader P1 panel) — **not** SB densify, FailedORB fade, LondonORB break, Spark Asian breakout

## Thesis

Asian session locks H/L `[0,7)`. During London `[8,14)`, a closed bar pierces beyond one extreme then closes back inside (liquidity grab). Next closed bar(s) reclaim through Asian mid with body ≥0.40·ATR and D1 EMA50 bias — trade reclaim continuity. One trade/day, Mon–Thu, weekend flat, risk 0.5%.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Decision | closed bar[1] only |
| Asia | `[0,7)` lock |
| Trade | `[8,14)`; flat hour 21 |
| Days | Mon–Thu |
| Risk | 0.50%; max 1/day; TP 1.5R |
| Magic | 880961 |
| Cost | tester `current` research-proxy |

Banned after readout: Asia/London hour mine, day veto, body/ATR retune from this run.

## Kill / Park / HIT

- Kill: N<80 ∨ tpw∉[1.0,6.0] ∨ PF<1.00
- Park: PF∈[1.00,1.30) with cadence OK
- HIT_RESEARCH_BAR: PF>1.30 ∧ tpw∈[2.0,5.0] (still not confirmed)

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Offline x1.5/x2 haircut allowed; Real QFSI parallel only.
