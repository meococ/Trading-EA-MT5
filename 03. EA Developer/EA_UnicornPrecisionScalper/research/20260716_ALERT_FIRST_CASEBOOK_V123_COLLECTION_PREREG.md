# ALERT_FIRST_CASEBOOK_V1.3 collection preregistration

Status: `FROZEN_DATA_ACQUISITION_ONLY`  
Frozen: 2026-07-16 before the V1.3 collection run  
Collection id: `DATA-ACQ-UNICORN-CASEBOOK-V1-002`  
Authority: no trading hypothesis, no Model-0 performance claim, no outcome join

## Bound collection

- EA/source contract: `EA_UnicornPrecisionScalper` /
  `UPS_ALERT_FIRST_CASEBOOK_V1_3`.
- Exact source SHA256:
  `10E278435644E63FD6418047AC775537CECEE8BBA4A9E5D89842E0F15312CB18`.
- Symbol/period: `XAUUSD` / `M5`.
- Window: `2024.01.01` through `2025.12.25`.
- Tester model: `0`; role string `control` is a harness binding only and does
  not create an economic matched-control experiment.
- Mutation inputs remain false: `InpResearchAutoMode=false` and
  `InpAllowRetiredResearchExecution=false`.
- Instrumentation: `InpEnableAlertCasebook=true`, lifecycle telemetry false,
  maximum 200 rows, exact `InpExpectedSourceSha256` equal to the bound source.
- Terminal data and tester roots must be physically on `D:`. `FILE_COMMON` is
  disabled and no protected `C:` root may change.

## Engineering-only delta from V1.2

The detector, score, thresholds, session, entry geometry, stop and target are
unchanged. V1.3 adds source SHA256 to every casebook row and metadata file,
adds a blank `label_true_breaker_valid` review column, makes trade mutation
tester-only, fails closed on position/order/history enumeration errors,
reconciles money risk to the actual broker fill, and binds order deviation to
the declared slippage budget.

The completed V1.2 collection is preserved but is diagnostic-only for the
labeling gate because its row/meta schema did not bind the source hash and did
not expose the breaker-validity label required by the fidelity audit.

## Acceptance and stop rules

The collection is valid only if all conditions hold:

1. MetaEditor compiles the exact bound source with 0 errors and 0 warnings.
2. The Strategy Tester report and enhanced summary contain zero trades.
3. Exactly one casebook CSV and one metadata CSV are harvested by AlphaFactory.
4. The casebook contains 100 to 200 unique completed-bar alert rows.
5. All human-label and outcome-like fields, including breaker validity, are
   blank.
6. Contract IDs, collection ID, source SHA256, symbol, period and D-drive data
   path agree across casebook, metadata, preset, task and run manifest.
7. Protected C-drive MT5 inventories are byte/count/metadata identical before
   and after the run.

If fewer than 100 rows are collected, stop at `INSUFFICIENT_ALERT_DENSITY`; do
not change signal thresholds, session, RR or detector rules. Even a valid
collection remains unlabeled and cannot authorize PnL analysis or another
Unicorn economic run. Independent human labels and a separately frozen
analysis plan remain mandatory.
