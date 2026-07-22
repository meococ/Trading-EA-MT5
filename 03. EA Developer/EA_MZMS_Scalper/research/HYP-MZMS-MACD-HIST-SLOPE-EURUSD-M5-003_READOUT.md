# HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-003 — Terminal Readout

Verdict: `KILL_AT_FROZEN_OFFLINE_PROBE`

## Scope and validity

This is the first valid economic probe for the fresh Owner-requested MZMS V1.
It preserves the report parameters plus the Owner's mandatory corrections:
closed-bar local histogram extremum, ATR-normalized histogram delta, five-bar
cooldown, BE off, explicit FivePercent server-to-UTC Europe-DST conversion and
a fail-closed 0.8-pip entry-spread ceiling.

V1/ID 001 was parked before outcome access for a news-SHA transcription error.
V2/ID 002 was invalidated before economic acceptance for causal simulator
ordering. V3 added red-first checks and ended with zero same-timestamp re-entry,
zero position overlap, strict horizon exclusion and 2019-2022-only access.

Engineering evidence: 17/17 tests, AlphaFactory compile 0 errors/0 warnings,
57,306-byte EX5, and snapshot-bound nonrepaint PASS with zero findings.

## Frozen result

| View | N | Trades/week | PF at 1.5-pip diagnostic | Expectancy | Net R |
|---|---:|---:|---:|---:|---:|
| Pooled 2019-2022 | 1,808 | 8.674 | 0.6949 | -0.1937R | -350.16R |
| Design 2019-2021 | 1,327 | 8.483 | 0.6715 | -0.2123R | -281.67R |
| Validation 2022 | 481 | 9.250 | 0.7640 | -0.1424R | -68.49R |

Before diagnostic cost, the challenger was only PF 1.0419, +0.0213R/trade and
+38.54R. The matched control was gross PF 0.9982 and -0.00085R/trade. The
MZMS filter therefore improves the control slightly, but not remotely enough
to establish the frozen absolute edge or survive realistic M5 friction.

The challenger produced 902 longs and 906 shorts. All four years were negative
at x1 cost: -169.58R, -78.39R, -33.71R and -68.49R. Exit counts were 853 stop,
503 target and 452 time exit. No positive year exists.

Funnel: 298,483 closed M5 bars -> 9,624 raw challenger signals -> 3,391 session
passes -> 3,258 news passes -> 2,275 valid spread passes -> 1,808 executed.
The local-extremum and cooldown corrections prevent the original duplicate
cluster bug, but cadence remains 8.67-9.25/week, above the frozen 2-5 band.

Only 7/26 frozen gates passed. PF, expectancy, cost stress, drawdown, cadence
and positive-year concentration failed across pooled/design/validation. The
failure exists before cost on absolute expectancy and persists after cost in
every year and both temporal splits.

## Decision

Stop this exact MZMS V1. Do not rescue it with intrabar signals, removal of the
local-extremum rule, a lower delta threshold, BE, trailing, session/day/year
filters, another symbol, 2023+ access or a parameter sweep. Because the cheap
probe failed, Model-0, delivery promotion, paper and live execution remain
blocked. The compiled source is retained as an audit artifact, not a tradable EA.

Cost/news evidence remains diagnostic-only; this limitation cannot rescue a
candidate whose gross PF is 1.0419 and gross expectancy is 0.0213R.
