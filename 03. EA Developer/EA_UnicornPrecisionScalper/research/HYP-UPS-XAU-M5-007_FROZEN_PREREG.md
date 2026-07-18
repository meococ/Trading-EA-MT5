# Frozen preregistration — HYP-UPS-XAU-M5-007

## Status and purpose

- Frozen before the first HYP-007 fill-feasibility result.
- Parent mechanism: terminal `HYP-UPS-XAU-M5-006` event-anchored signal.
- New feature family: execution-only FVG consequent-encroachment limit entry.
- This is a fresh hypothesis, not a revival or parameter rescue of HYP-006.
- No live/paper attachment and no market-order fallback.

## Independent prior

The source report prescribes waiting for a conditional retrace and placing a
limit at the FVG midpoint/CE with short expiry when the zone has not yet been
touched. The completed EAs instead entered immediately at market. HYP-007
tests that omitted execution policy without using the observed weak
weekday/hour/year slices and without changing signal thresholds, direction,
session, stop, target or risk gates.

## Frozen contract

- Symbol/timeframe: `XAUUSD` / `M5`.
- Window: `2024.01.01` through `2025.12.25`, elapsed calendar weeks.
- Signal identity: exact event-anchored HYP-006 detector and thresholds.
- Limit price: arithmetic midpoint of the detected FVG.
- Expiry: exactly 3 subsequent closed M5 bars.
- Pending invalidation: after a bar closes through the bound sweep extreme.
- Intrabar ordering for the density probe: a touched resting limit counts as a
  fill before close-time invalidation; MT5 real-tick Model 0 must resolve the
  actual path if build authority is later earned.
- No chase, no market fallback, no hour/weekday/year/direction veto.
- Probe reads only candidate/fill feasibility. It must not calculate PnL,
  target/stop outcome, MFE, MAE or forward return.

## Frozen probe gates

All must pass before source modification or Strategy Tester:

1. Exact parent candidate count remains 251.
2. Filled-limit cadence is at least 2.0 and at most 5.0 per elapsed week.
3. Fill rate is at least 82.5% (the minimum implied by 251 candidates and the
   2.0/week cadence floor).
4. At least 20 active months contain a fill.
5. At least 30 long and 30 short fills.
6. The probe emits no strategy PnL/outcome fields and persists no raw bars.

Any failed gate is terminal `KILL_AT_FILL_FEASIBILITY_PROBE`. Do not extend
expiry, move the limit away from CE, enable a market fallback, remove shorts,
or select a session/hour/day after reading the result.

## Conditional Model-0 contract

Only if every probe gate passes:

- advance canonical source under HYP-007 with the one coherent execution
  change above;
- compile with 0 errors/0 warnings and pass exact-source non-repaint audit;
- use the same FivePercent D-portable identity, 2024–2025 window, risk rules
  and conservative research cost proxy as HYP-006;
- run exactly one valid research-control Model 0;
- require PF > 1.80, 2–5 trades/week, DD <= 5.5%, cost PF x1.5 >= 1.25,
  cost PF x2 >= 1.00 and Monte Carlo P95 DD <= 5.5%;
- failure is terminal and never authorizes live execution.

