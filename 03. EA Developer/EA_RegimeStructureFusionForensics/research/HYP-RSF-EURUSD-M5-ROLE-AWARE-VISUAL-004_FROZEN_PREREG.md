# HYP-RSF-EURUSD-M5-ROLE-AWARE-VISUAL-004 — frozen visual preregistration

Status: `DIAGNOSTIC_ONLY_NO_ECONOMIC_AUTHORITY`

## Purpose

Capture genuine portable MT5 Visual Mode charts for the exact executed trades of
the terminal `HYP-RSF-EURUSD-M5-ROLE-AWARE-003` run. The replay exists only to
compare the indicator and price anatomy of failures with successful controls;
its Model-1 report cannot change or rescue the killed economic result.

## Frozen selection

The lifecycle CSV of run `20260807_064845` was grouped by the four routes that
actually executed. Before visual replay, the worst net result and best net
result of each route were selected, yielding exactly eight cases:

1. RA003-C01: worst Breakout Long, position 12.
2. RA003-C02: best Breakout Long, position 108.
3. RA003-C03: worst Breakout Short, position 84.
4. RA003-C04: best Breakout Short, position 78.
5. RA003-C05: worst Trend Long, position 36.
6. RA003-C06: best Trend Long, position 20.
7. RA003-C07: worst Trend Short, position 54.
8. RA003-C08: best Trend Short, position 2.

The exact timestamps, prices, SL, TP, exit and R values are hash-bound in
`HYP-RSF-EURUSD-M5-ROLE-AWARE-003_VISUAL_CASES.csv`.

## Frozen replay contract

- EA: `EA_RegimeStructureFusionForensics`.
- Symbol/timeframe: EURUSD M5.
- Window: 2018-02-01 through 2020-12-20.
- Model: 1, visual diagnostic only.
- Schedule: `FROZEN_ROLE_AWARE_003_OUTCOMES_V1`.
- Case index: 0, so all eight frozen cases are visited chronologically.
- No Skip-To interaction is allowed.
- At one completed M5 bar after each exit, the chart must show actual M5 price,
  all attached indicator panes/overlays, and immutable entry/SL/TP/exit objects.
- External capture holds the real portable MT5 window for 30 seconds per case.
- Acceptance requires eight distinct full-window PNGs with valid PNG signature,
  non-zero dimensions, exact case identity and SHA256 manifest.
- Generated trades, balance, PF and report metrics have no economic authority.

## Interpretation boundary

The paired charts may identify event-order and price-path differences. They may
not authorize selecting a winning case, date, direction, route, hour, weekday or
year. Any successor trading mechanism requires a fresh economic hypothesis ID
and preregistration.
