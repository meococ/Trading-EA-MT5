# HYP-STBS-XAUUSD-M15-013 pre-execution harness addendum

Status: `FROZEN_PRE_EXECUTION_HARDENING`

The market thesis, MQL5 source, parameters, tester preload, economic window and cost gates remain exactly those in prereg SHA256 `EF3DB79293438056A1634723E5F2DAE7183E093EF33A6F84CC6E061AC4AFE1CA`. No HYP013 MT5 run, report, lifecycle outcome, PF or return was opened before this addendum.

Independent review of the first dry-run found three execution-governance defects: normal Model-0 economics lacked a durable one-shot attempt claim; `timeout_sec=900` was not carried through packet/receipt/manifest; and the five-field baseline contract plus packet bytes were not bound by the final registry authority. Those defects could permit a retry or a post-authority change to time budget or thresholds.

The corrected contract therefore requires:

- a packet-bound successor `screened` row that explicitly binds the prior row, exact task packet, current runner and AlphaFactory hashes;
- exact packet fields `attempt_id=STBS013-MODEL0-TRAIN-001`, `attempt_limit=1`, and `timeout_sec=900`;
- an exclusive `CreateNew` durable attempt-start record under ignored AlphaFactory runtime storage before Alpha compile/backtest;
- a durable COMPLETE or FAILED terminal; a hard crash leaves the start record and permanently blocks same-ID reuse;
- receipt and post-run manifest equality for `timeout_sec`;
- exact registry-to-packet comparison of all five supplemental baseline fields and the research-proxy permission triple;
- an append-only `screened -> screened` authority-hardening transition that permits no source, parameter, economic-contract, metric, run-ID or permission drift and verifies the packet, runner, AlphaFactory, validator and test bytes;
- semantic alias mapping from the frozen registry fields `require_positive_mean_x1_net_r` / `require_each_calendar_year_positive_x1_net_r` to the packet fields `require_positive_cost_expectancy` / `require_all_calendar_years_positive`, without changing either threshold;
- optimization, OOS, holdout, promotion, paper and live permissions remain false.

The focused combined gate passes 20 tests: the cost/governance module covers duplicate-claim rejection and mutations for timeout, minimum trades, performance permission, retry permission, consumed-attempt state and bound-control drift; the Model-0 pre-execution registry suite covers exact-pass, strategy drift, consumed attempt, broadened optimization permission, packet-threshold drift, prior-registry mismatch and bound-runner tampering. The final full runs pass 71 candidate-registry tests and 273 AlphaFactory tests; the only warnings are two pre-existing openpyxl default-style notices. This addendum authorizes no execution by itself; only the final hash-bound successor registry row may do so.
