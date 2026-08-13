# Frozen source prereg — HYP-DPMO-XAUUSD-M5-001

Frozen before opening DESIGN rows or computing the participation event count.

## Thesis

- EA: `EA_DailyParticipationMomentum`; FivePercent `XAUUSD`, native M5.
- DESIGN: 2018-01-01 inclusive through 2023-01-01 exclusive. Outcomes and
  2023+ remain sealed.
- At the fixed 15:55 UTC daily close, continue the completed 00:00–15:55 UTC
  session return only when that session's total broker tick activity is above
  the median of the prior 20 exact complete sessions. This is a joint
  participation-regime plus price-direction object; neither volume nor return
  can emit alone.
- Broker `tick_volume` is an activity proxy, not true traded volume, order flow,
  CVD, VPIN or depth.
- Repository de-dup found no exact daily current-session-activity-above-prior20-
  median continuation object. It differs from external CME OI participation,
  ARUC same-slot signed activity, VWAP weighting, cross-asset consensus and the
  closed single early-to-late momentum screen.

## Data

- Manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.
- XAUUSD M5 SHA256:
  `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`.
- Exact file is the local FiveAssetFoundation XAUUSD M5 Parquet. No paid data
  or TradingView data is required.
- Shared frame/session validator dependency is frozen at SHA256
  `AE06830575C27776926B3129F97FDD85EC586F830CC86977D4C63A16E888E583`.

## Exact source rule

For each UTC Monday–Friday date:

1. Require exactly the 192 native rows `00:00,00:05,...,15:55`, contiguous by
   UTC and `source_epoch`. Incomplete sessions emit nothing and do not enter the
   rolling history.
2. `Activity(d)=sum(tick_volume)` over those 192 completed bars.
3. `Return(d)=log(close_15:55/close_00:00)`.
4. After 20 prior complete sessions exist, compute their ordinary median
   activity. Current activity is excluded.
5. If `Activity(d)>Median20(d)` and `Return(d)>0`, emit LONG. If activity is
   above the median and return is `<0`, emit SHORT. Equality or zero return
   emits nothing.
6. Append current complete-session activity to history only after the decision.

There is no volume multiplier, return threshold, alternate lookback/checkpoint,
session filter, cooldown, daily quota beyond the one fixed daily observation,
direction deletion or parameter grid. `20` is one prior trading month and the
median is frozen before source.

Decision is the completed 15:55 bar; availability must be the exact 16:00 UTC
next source row (`+300`). Ledger fields are limited to IDs, clocks, direction,
activity, prior median, session return/start/end close, completeness and
exact-next. No post-16:00 price or economic field is allowed.

## Frozen gates and evidence

- DESIGN rows >=300,000; exact-session coverage >=95%; exact-next >=97%;
- executable N>=500; cadence 2–5/week; each direction >=30%;
- max decision-year share <=30%; each 2018–2022 year 1.25–6.5/week;
- zero conflicts; deterministic replay.

Sole attempt `DPMO-SOURCE-001` must claim/fsync before bound reads and always
persist structured per-gate evidence. A normal failure writes COMPLETE/PARK
report, ledger, receipt and terminal. Any exception writes failure context.

Any failure parks the exact mapping; no lookback/median/checkpoint/threshold/
direction/session/symbol/timeframe rescue under this ID. PASS authorizes only
unchanged MQL5 build/parity/compile/non-repaint and a separately preregistered
untuned Model-0 baseline. Optimization, validation, holdout, paper, promotion
and live remain closed.
