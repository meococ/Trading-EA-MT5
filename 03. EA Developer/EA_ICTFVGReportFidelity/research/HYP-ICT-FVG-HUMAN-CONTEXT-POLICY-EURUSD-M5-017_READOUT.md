# HYP-017 Model-0 readout

## Verdict

`KILL_AT_HYP017_MODEL0_NO_STABLE_EDGE`. The frozen policy was tested once and
failed before any subgroup or threshold selection. Promotion remains `false`.

This is not evidence that all ICT/FVG ideas are false. It is direct evidence
that this exact high-recall sweep/reclaim plus two-state Human Context policy
does not have an economic edge under the tested EURUSD M5 contract.

## Frozen object and run identity

- Hypothesis: `HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017`.
- Source v1.23 SHA-256: `FF02340C65CBB0E36B1794CB8263023FDD9B7F9218492E749F1F8875C826A5C6`.
- Run: `20260719_215636`; EURUSD M5 Model 0; 2018-01-01 to 2026-07-19.
- Policy: accept only `EXTERNAL_SWEEP_WITH_ROOM` or
  `INTERNAL_SWEEP_WITH_ROOM`; existing market entry, sweep-extreme stop and 2R
  target; 0.01% risk; maximum two entries per day; news disabled.
- History: 99%; 636,544 bars / 206,517,809 ticks.
- Lifecycle reconciliation: 3,703 OPEN plus 3,703 final CLOSE rows, exactly
  matching the 3,703 tester trades. One fill was matched to the only
  same-direction decision within the previous five minutes because the next
  theoretical M5 boundary had no tick; ambiguity was zero.

## Economic result

| Layer | Trades | PF | Net | Expectancy |
|---|---:|---:|---:|---:|
| Native tester/lifecycle | 3,703 | 0.7553 | -$5,107.84 | -$1.379/trade |
| Additional 1.50-pip RT | 3,703 | 0.3513 | -$18,831.34 | -0.52139R/trade |
| Additional 2.25-pip RT | 3,703 | 0.2470 | -$25,693.09 | -0.71133R/trade |
| Additional 3.00-pip RT | 3,703 | 0.1768 | -$32,554.84 | -0.90127R/trade |

- Native win rate: 47.151%; native maximum account DD: 5.110%.
- Cadence: 8.3126 trades per elapsed week, above the frozen 2-5 target.
- Week-block bootstrap at 1.50 pip: mean -0.52139R/trade; 95% CI
  `[-0.55998, -0.48317]`; 10,000 repetitions; fixed seed 20260719.
- Positive years after the primary cost: zero of nine. Monday through Friday
  are negative even before the additional cost.
- Gates passed: 4/11. Identity/history, lifecycle reconciliation, minimum sample
  and DD passed. Cadence, all economic/cost gates, positive-year breadth and
  profit concentration failed.

## What fails structurally

1. **Context describes destination/room, not initiation.** The two accepted
   states say that liquidity was swept and room exists toward a directional
   objective. They do not prove that order flow has changed now. The policy
   enters immediately after reclaim without a separately validated trigger,
   so it repeatedly buys or sells inside unfinished noise.
2. **Entry and stop geometry are incompatible with M5 noise and costs.** The
   native median result is already approximately -0.994R. After the primary
   cost, the median becomes -1.169R and 1,666 trades are at or below -1.25R.
   Tight sweep-extreme stops make spread/slippage a material fraction of risk;
   many directionally plausible ideas are stopped before continuation.
3. **The internal state dominates and is weak.** `INTERNAL_SWEEP_WITH_ROOM`
   supplies 2,809 trades and PF 0.322 after primary cost. The apparently cleaner
   external state is better but still loses: 894 trades, PF 0.456. Removing the
   internal group now would be post-outcome rescue, and external-only would not
   pass anyway.
4. **The failure is not localized.** London PF is 0.323 and New York PF 0.412;
   long PF is 0.324 and short PF 0.376 after primary cost. Every 2018-2026 year
   is negative. No session, direction, weekday or year can explain away the
   result.
5. **Risk gates reduce fills but do not select alpha.** The run records 26,729
   sweeps, 10,694 policy accepts and 3,703 opened entries after prop, exposure,
   spread, risk, session and OrderCheck gates. These controls protect execution;
   they do not turn a weak signal into positive expectancy.

## Four-chart post-outcome anatomy

The casebook is diagnostic only. It cannot authorize a filter or rerun.

- `H17_L01`: internal-sweep long enters after a rising impulse/local high and
  immediately reverses. Available room did not establish initiation; the tight
  stop also converted the reversal into more than the intended 1R loss.
- `H17_L02`: internal-sweep short is directionally plausible later, but the
  1.5-pip stop is clipped by ordinary bounce before the subsequent decline.
  This isolates timing/geometry failure from directional-context failure.
- `H17_W01`: internal-sweep short receives immediate displacement, reaches the
  target, then reverses. It shows the sequence that the losing cases lack, but
  selecting it now would be an outcome-derived rule.
- `H17_W02`: external-sweep short is aligned with H1 decline/retest and
  continues immediately. This is the cleanest visual case, yet the entire
  external subgroup still has PF 0.456 after primary cost.

The H1 pane is centered on the entry H1 candle and contains four completed H1
bars after entry. Entry, initial SL, TP and actual exit are all rendered in the
M5 pane.

## Overfit boundary and next legal move

Policy selection was outcome-blind on HYP-016R1, so this run is not a classic
multi-parameter optimization over its own PnL. However, it was designed after
earlier family history and has no untouched independent holdout; it is therefore
diagnostic, not promotion evidence. Adding a confirmation threshold, deleting
the internal state, widening the stop, changing RR, or filtering sessions after
reading this result would be post-hoc overfit.

Any successor must introduce a materially new, pre-outcome information contract
rather than rescue HYP-017. Examples that require a fresh hypothesis and
outcome-blind feasibility check are: a discrete initiation sequence, normalized
stop/noise geometry, or a different execution mechanism. None is authorized by
this readout alone.

## Reproducibility and limitations

- Economic result SHA-256: `D011DBCE0A85F8341AFC323EF5F16DFB04E7FB0B4D5564C5B6317DDA9D5627BD`.
- Canonical result SHA-256: `DAF6D51EA1AE51925E3E55A8F0B34CFB2BA17E08241C8F5CC02A876E4EC52C5E`.
- Run manifest SHA-256: `DF246FDC501AEFD5B734723438AC96F23696B9E01BE900C4CA798BCA9193A20C`.
- Casebook manifest SHA-256: `92FF8F7FF37570E7BE897A44F1EAB99DB8D93F8F0BDA3F16A479BE1B4E4B3E97`.
- Exact analyzer replay reproduced both result hashes.
- Historical broker spread/slippage provenance remains unverified. Incremental
  pip costs are conservative because tester spread is already embedded.
- No failed subgroup may be removed and no second HYP-017 economic run is
  authorized.
