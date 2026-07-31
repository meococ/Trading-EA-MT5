# HYP-CME6E-RAWBREAK-BOOKSTATE-001 — frozen chart-forensics plan

Date: 2026-07-27  
Status: `FROZEN_POSTMORTEM_ONLY / TERMINAL HYPOTHESIS UNCHANGED / OOS SEALED`

## Purpose and boundary

Explain why the already terminal DESIGN challenger failed by combining its
hash-bound outcome ledger with EURUSD price paths and the causal CME 6E MBP-10
book trace available before each raw BREAK decision.

This is descriptive postmortem evidence. It cannot change the terminal verdict,
select a rescue threshold, authorize OOS, create a trading rule, build MQL5,
rerun Model 0, promote or deploy. Any mechanism suggested after viewing outcomes
requires a fresh ID, outcome-blind feature contract and preregistration.

## Bound population

- Hypothesis: `HYP-CME6E-RAWBREAK-BOOKSTATE-001`.
- DESIGN only: 2019-2020; OOS 2021-2022 remains unopened.
- Challenger population: exact 230 rows with frozen score
  `>= -0.005025602742083225`.
- Joined ledger SHA256:
  `A28B47392E295C6D6296E4C7CC851C226C2F3060673014B37959F12407AC99B2`.
- Full parent control ledger SHA256:
  `07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9`.
- EURUSD M1 bar source SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- CME source plan, manifest and raw validation hashes remain those bound in the
  terminal probe/readout. No new market-data request is allowed.

## Frozen sampling rule before chart viewing

Select exactly 12 unique challenger positions in this order:

1. `EXTREME_WIN`: two largest realized R values, tie by position ID.
2. `EXTREME_LOSS`: two smallest realized R values, tie by position ID.
3. `MEDIAN_WIN`: two remaining positive-net rows closest to the median R among
   all positive-net challenger rows, tie by position ID.
4. `MEDIAN_LOSS`: two remaining nonpositive-net rows closest to the median R
   among all nonpositive-net challenger rows, tie by position ID.
5. `MATCHED_BUY_WIN` and `MATCHED_SELL_WIN`: from remaining rows, choose the
   positive-net BUY and SELL nearest the challenger median frozen book score.
6. For each matched winner, choose one remaining same-direction nonpositive-net
   row minimizing Euclidean distance over population-standardized, entry-known
   fields: frozen book score, initial stop pips, volume and UTC minute-of-day.
   Tie by position ID. Label these `MATCHED_BUY_LOSS` and `MATCHED_SELL_LOSS`.

Outcomes are legal only for the declared strata and labels. No chart may be
viewed before `case_selection.csv` and its manifest are written and hashed.

## Chart layers

For every selected case render:

- `decision`: outcome-blind EURUSD M1 path ending at entry, H1 as-of context,
  entry/SL/TP lines, and the direction-aligned CME five-level imbalance trace
  ending at the raw BREAK decision. No exit, R or win/loss text.
- `outcome`: EURUSD M1 path from pre-entry through exit plus 30 minutes,
  entry/SL/TP/exit and realized R. CME trace remains strictly pre-decision.

Every image must bind case ID, position ID, source hashes, selection stratum,
clock conversion, first/last bar and whether future price is visible.

## Required population analysis

- N, PF, net, win rate, account expectancy and realized-R expectancy.
- Average win/loss, realized payoff ratio and implied breakeven win rate.
- Fixed cost diagnostics already frozen by the terminal probe.
- Year, month, weekday, UTC hour, direction, holding-time, stop-width and score
  buckets where counts are sufficient.
- Tail contribution, score-versus-R rank correlation and score-decile ordering.
- M1 OHLC approximate MFE/MAE and early directional excursion, clearly labeled
  path-ambiguous and outcome-bearing.
- Winner/loser comparisons and the two predeclared matched pairs.

## Evidence labels and final contract

Use `OBSERVED`, `STRONG INFERENCE`, `HYPOTHESIS` and `UNKNOWN`. The readout must
satisfy the local `grok-ea-trade-forensics` analysis contract, rank no more than
three failure mechanisms with confidence, include the 12-case manifest, state
what winners share after matching, identify fidelity limitations and propose at
most three fresh mechanism-level hypotheses without mined thresholds.
