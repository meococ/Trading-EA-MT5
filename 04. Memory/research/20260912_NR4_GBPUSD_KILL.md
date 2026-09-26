# KILL — HYP-NR4-GB-M5-001 (EA_Nr4, GBPUSD M5)

**Date:** 2026-09-12 — era-2 falsification screen, cell 16.
**Run:** `02. AlphaFactory/runs/EA_Nr4/20260912_130654` (deciding),
calibration `124223` + `130240` (audit-gate stop before cost chain).

## Hypothesis

M5 NR4 volatility-compression breakout: closed bar 2 has the smallest
range of bars 2..5, then bar 1 closes beyond bar 2's high/low, H4 EMA50
agreeing. SL max(1.5xATR, 80pts), TP 1.5R, 12-bar time stop,
session 08-16, Friday forbidden.

This was the first GBPUSD sleeve cell and the first pure
*volatility-compression -> expansion* mechanism on the board — a class
not represented in any of the 15 prior kills.

## Result (governed Model 0, 1999.01.01-2026.09.11, quality 99)

| Metric | Value |
|---|---|
| Trades | 18,552 |
| Cadence | ~12.9/wk — PASS |
| Profit factor | **0.783** |
| Net | **-$7,805.27** |
| Max DD | 78.7% |
| Win rate | 39.9% |
| Cost PF x1.0 / x1.5 / x2.0 | **0.692 / 0.637 / 0.586** |
| Non-repaint audit | PASS |
| Overnight/weekend | 0 — PASS |

## Verdict

**KILL.** Gross-negative before full cost loading; every cost scenario
below break-even. Range compression does not resolve into directional
edge on GBPUSD either — same signature as all 15 prior cells: PF in the
0.68-1.00 band, uniform decay across years/sessions/weekdays.

## Engineering notes

- New auditor rule `allowed_for_loop_shift`: identifier shift proven >= 1
  as a for-loop induction variable with literal init >= 1, no
  decrement/reassign in body. EA_Nr4's `for(int k=3;...)` NR scan is the
  canonical case. Regression tests 15/15.
- GBPUSD evidence tier built fresh on Build 6192: 1.76M real spread
  ticks (p90 0.1 pip), 775k slippage quote pairs, commission bound
  $7.00/lot RT over 30 real lifecycles.
- GBPUSD verified-M1 coverage confirmed identical to EURUSD: real M1 from
  1999-01, 1971-1998 daily-stub; `verified_m1_asof` applied.

## Board state

16 kills / 0 passes. Symbols falsified: XAUUSD (5), EURUSD (9+1 board),
GBPUSD (1). Mechanism families falsified: trend-adaptive, oscillator MR,
session VWAP, calendar drift, squeeze-release, IBS continuation,
Camarilla, H1 displacement, liquidity sweep, range breakout, tick-volume,
cross-symbol RS, hour-open, HTF pullback, FVG, NR4 compression.
