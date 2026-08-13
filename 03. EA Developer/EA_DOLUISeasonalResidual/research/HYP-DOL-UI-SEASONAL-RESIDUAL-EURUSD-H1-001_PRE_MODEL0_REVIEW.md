# HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001 - pre-Model0 implementation review

Status: `PASS`

No blocking findings. Model0 receipts may be opened for the frozen TRAIN-only
primary and reverse comparator, with `InpResearchAutoMode=true` override and no
validation/holdout access.

Evidence checked:

- Frozen prereg locks TRAIN to `2018-01-01` through `2023-01-01`, keeps
  validation/holdout sealed, and defines delayed H1 entry as release `:30` ->
  next H1 decision bar -> entry after that bar closes
  (`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_FROZEN_ECONOMIC_PREREG.md:22`,
  `:36`, `:41`, `:81`).
- Generated table is source-bound and TRAIN-only: 260 events, 101 BUY, 157 SELL,
  2 FLAT, source/table hashes fixed, and no price/economic metrics in manifest
  (`generate_dolui_train_table.py:74`, `:86`, `:110`, `:190`).
- EA validates table/hash/clock geometry in `OnInit`, enforces
  EURUSD/H1/tester/audit/research mode, uses closed decision bar
  `iTime(..., PERIOD_H1, 1)`, and enters only at/after `entry_target` with max
  5-minute delay (`EA_DOLUISeasonalResidual.mq5:102`, `:273`, `:427`, `:495`).
- Sizing and costs match prereg: fixed exposure percent over 40-pip denominator,
  pip value from tick size/value, no SL/TP, observed spread/fill cost floored at
  zero, commission and dynamic slippage recorded separately
  (`EA_DOLUISeasonalResidual.mq5:211`, `:291`, `:378`).
- Event accounting and sidecars are explicit: source FLAT, missed, mismatch,
  weekend, overlap, rejects and completed events are counted; deinit fails
  closed if all 260 are not accounted (`EA_DOLUISeasonalResidual.mq5:401`,
  `:545`).
- Reverse comparator changes direction only and writes isolated role sidecars
  (`EA_DOLUISeasonalResidual.mq5:293`, `:445`).
- Compile receipt is clean: `0 errors, 0 warnings`
  (`EA_DOLUISeasonalResidual.log:47`); EX5 is nonempty.
- Nonrepaint audit is PASS and binds the EA/include hashes
  (`HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001_NONREPAINT_AUDIT.json:2`, `:9`).

Verification run read-only: DOLUI test suite `23 passed in 0.57s` with bytecode
and pytest cache disabled. Compile was not rerun during this review because that
would write build artifacts.

Authorization scope: TRAIN Model0 receipts may be opened for PRIMARY and exact
sign-reversed comparator only. Internal validation, holdout, optimization,
promotion, paper trading, and live trading remain sealed.
