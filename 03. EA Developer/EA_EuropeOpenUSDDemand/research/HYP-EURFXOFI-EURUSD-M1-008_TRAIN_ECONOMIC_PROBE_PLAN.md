# TRAIN ECONOMIC PROBE PLAN - HYP-EURFXOFI-EURUSD-M1-008

Frozen on `2026-07-30` before HYP006 acquisition completion, before HYP007
source-feature materialization and before any HYP008 target return is opened.

## Mechanism and falsifiable claim

The killed pressure-only parent reversed the broad 07:59-to-14:14 EURUSD move
and achieved gross PF 1.110752 but only PF 0.845237 after 1.50 pips. HYP008 does
not retune that failed direction, lookback, threshold, clock or exit. It adds a
fresh contemporaneous information set: signed aggressive CME 6E trade flow in
the final 15 seconds before the 14:15 Europe/Berlin decision boundary.

Claim: if the fix-related inventory mechanism is real, the initiating side of
the final 6E trades should identify the pressure being unwound more directly
than the long pre-fix cash-price move. The primary therefore trades opposite
the sign of final signed aggressive 6E volume:

- positive `flow_signed` (buy aggressors dominate) -> SELL EURUSD;
- negative `flow_signed` (sell aggressors dominate) -> BUY EURUSD;
- exactly zero classified signed flow -> no trade.

No flow-magnitude threshold, quantile cutoff, calendar filter, volatility gate
or parameter search is allowed. This preserves cadence and prevents a
post-source-distribution rescue.

## Sealed population and timing

- Source feature: exact hash-bound HYP007 `source_features.parquet`, only if
  HYP007 verdict is `PASS_SOURCE_QUALITY` and its terminal artifact manifest is
  registry-bound.
- TRAIN outcomes only: 2016-01-01 through 2020-12-31. Validation 2021-2024 and
  HOLDOUT 2025-01-01 through 2026-07-29 remain return-sealed.
- Eligibility stays the HYP002 outcome-blind strict-lag rule: absolute
  07:59-to-14:14 pressure at least the median of the prior 60 complete
  weekdays, minimum 40 observations.
- Signal window: `[14:14:45,14:15:00) Europe/Berlin`, end-exclusive.
- Decision/entry proxy: completed 14:14 EURUSD bid close, observable at 14:15,
  with the frozen all-in cost charged below. No source timestamp at or after
  14:15 and no post-decision field may enter the signal.
- Exit: completed 15:59 EURUSD bid close, observable at 16:00.
- Maximum one trade per selected weekday; no stop, target or trailing logic in
  this probe.

## Predeclared arms and controls

Exactly four x1 economic arms form this cell; no additional variant may be
created after outcomes open:

1. `FLOW_REVERSAL_PRIMARY`: direction `-sign(flow_signed)`.
2. `FLOW_CONTINUATION_DIRECTION_CONTROL`: direction `+sign(flow_signed)`.
3. `PRESSURE_REVERSAL_PARENT_CONTROL`: direction opposite pre-fix pressure on
   the corrected HYP002 TRAIN dates.
4. `PRESSURE_CONTINUATION_CONTROL`: direction with pre-fix pressure.

The DSR trial universe is frozen at 16 x1 arms: the 12 already declared in the
parent family plus these four corrected-clock/TBBO arms. The flow/pressure
agreement flag and continuous flow imbalance may be reported for mechanism
diagnostics but cannot gate trades or define a fifth arm.

## Costs, metrics and pass gates

All four arms use the same raw post-fix return. Primary net PnL is evaluated at
fixed round-turn costs x1/x1.5/x2 = 1.50/2.25/3.00 pips. Cost fields are never
interpreted as actual zero.

The primary must pass every economic gate:

- PF x1 >= 1.30;
- PF x1.5 >= 1.25;
- PF x2 >= 1.00;
- expectancy x1 > 0 pips;
- cadence between 2 and 5 trades per elapsed calendar week;
- at least 4 of 5 TRAIN calendar years positive after x1 cost;
- leave-one-year-out PF x1 > 1.00 for every omitted year;
- one-sided sign-flip/permutation p <= 0.05 using 10,000 draws and seed
  `20260730`;
- deflated Sharpe probability >= 0.95 using the frozen 16-arm universe;
- no single TRAIN year contributes more than 35% of total positive x1 PnL.

Structural failure, missing source/target timestamps or a source-quality miss
is engineering/data invalid and cannot be called no-edge. A valid economic
gate failure kills exactly HYP008; it cannot be rescued by a flow threshold,
bin selection, date filter, alternative exit or cost change.

## Mandatory evidence and charts

The one-shot TRAIN attempt must produce a trade ledger, terminal JSON, log
triage, artifact manifest and these charts with exact population/gate labels:

1. gross/x1/x1.5/x2 cumulative PnL and x1 drawdown;
2. yearly x1 PnL, PF and expectancy;
3. four-arm PF/expectancy comparison at x1;
4. continuous flow-imbalance deciles versus raw post-fix return with confidence
   intervals, explicitly marked diagnostic-only/no threshold authorization;
5. direction, holding-return and flow distributions plus the signal funnel.

If and only if every TRAIN gate passes, five deterministic trade-anatomy cases
(largest absolute flow, median flow, earliest, latest and worst x1 PnL) may be
rendered for forensic review. Case selection is frozen here and is not a
performance filter.

## Authority boundary

This plan alone authorizes nothing. The evaluator, tests, exact HYP007
feature/artifact hashes, target dataset/clock hashes and one-shot attempt root
must be appended to the registry after HYP007 passes and before TRAIN outcomes
open. MQL5, Model 0, validation, holdout, optimization, promotion, paper and
live trading remain closed. A TRAIN survivor may open only a fresh sequential
validation successor; it does not become an EA automatically.
