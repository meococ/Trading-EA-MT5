# HYP-VRAS-EURUSD-M5-008 - Full-Horizon Forensic Analysis

## Scope and validity

HYP008 is a diagnostic-only engineering successor to the invalid HYP007 run. It disables only the EA account-drawdown entry halt in Strategy Tester, continues to measure drawdown, and changes the tester capital/risk scale from USD 100,000 at 0.05% to USD 500,000 at 0.01%. Both configurations start near USD 50 cash risk per position. Signal, stop, TP, break-even, time-exit, guards and execution logic are unchanged.

Both serial Model-0 arms completed the full 2019-2022 window at 100% history quality: 298,483 bars and 79,486,116 ticks. Exact bounded tester-log windows show `Test passed`, no broker stop-out and clean thread completion. Report and lifecycle logs reconcile exactly: control 4,841 OPEN plus 4,841 final CLOSE; challenger 3,611 plus 3,611; net gap USD 0 in both arms. The account-DD halt was disabled, no actual account halt occurred, and the complete sample is therefore observable.

## Economics

| Metric | Control fixed clamp | Challenger ATR structural |
|---|---:|---:|
| Trades | 4,841 | 3,611 |
| PF after recorded costs | 0.7736 | 0.7722 |
| Gross price PF before recorded costs | 0.8803 | 0.8870 |
| Net P/L | -USD 25,579.82 | -USD 20,791.58 |
| Mean realized R | -0.1096 | -0.1184 |
| Max DD | 5.31% | 4.28% |
| Trades / elapsed week | 23.21 | 17.31 |
| Initial-stop share | 40.71% | 44.78% |

The challenger reduces drawdown by 1.02 percentage points and trades by 1,230, but PF changes by -0.0013 and mean R by -0.0088R. The lower drawdown comes from less exposure, especially 3,835 structural rejections, not higher trade quality. Both price-only PF values are below 1 before recorded costs, so execution costs are not the sole cause of failure. Recorded costs add about USD 12,912 of control loss and USD 11,193 of challenger loss. Cost-stress proxies worsen to PF 0.7220 at 1.5x and 0.6762 at 2x for the challenger. Cost provenance remains unverified; these values are diagnostic, not live estimates.

## Stop geometry and realized R:R

The nominal target is 1.5R, but the realized distribution is materially different. Challenger average win is +0.9555R and average loss is -0.9026R, a realized payoff ratio of only 1.0586. That payoff requires a 48.58% win rate to break even before any further safety margin; observed win rate is 42.20%. Control is similar: payoff 1.0631, required WR 48.47%, observed WR 42.12%.

The compression from nominal 1.5R to realized approximately 1.06 comes from break-even/managed exits, the 24-bar time exit, costs and gap behavior. Challenger target exits are only 23.71%; initial-stop exits are 44.78%, and another 16.28% finish in the break-even zone. Stop distance itself is not the missing edge: challenger mean stop is 9.34 pips, but the range is 2.1 to 83.4 pips and aggregate gross price PF remains 0.8870. The ATR-structural mechanism filters trades and lowers exposure without restoring expectancy.

## Time, session, direction and regime stability

All four calendar years lose in both arms. Challenger yearly PF is 0.6637, 0.9033, 0.7264 and 0.7854 for 2019 through 2022. Every session, BUY/SELL direction, telemetry ATR quartile and H1 EMA-distance quartile also has PF below 1. The best challenger ATR quartile is still only PF 0.8644. This rules out a hidden later-window recovery and gives no preregistered basis for a session, direction, volatility or year veto.

Equity quality also fails: challenger has 85.4% losing months, a negative median trade and 1,450 days without a new equity high; control has 87.5% losing months and 1,451 flat days. High trade count is therefore repeated negative expectancy, not useful cadence.

## Weekend-gap and time-stop conflict

The strategy is described as an intraday/scalping surface, but the 24-bar hold limit counts completed M5 bars. Market closure therefore pauses the clock. Challenger holds 125 positions overnight and 27 across weekends, with maximum elapsed duration 51.42 hours; control holds 91 overnight and 23 across weekends.

This creates uncontrolled tail geometry. Challenger's largest winner, P6634, is a Friday long held to Monday and realizes +5.63R after a favorable weekend gap. Its largest loser, P5814, is a Friday short held to Monday and realizes -6.04R after price gaps far beyond the initial stop. The tail is therefore partly a weekend-gap lottery rather than the declared 1.5R/1R geometry. A future hypothesis must define Friday flattening or wall-clock expiry before outcome, but adding that rule to HYP008 would be an unauthorized post-hoc rescue.

## Execution, charts and tool-boundary notes

The anatomy casebook binds two winners and two losers with entry, initial SL, TP and exit. A separate decision-as-of casebook shows the active closed M5 rolling VWAP48, closed H1 EMA200 and ATR14 diagnostics while hiding outcome and net R. These indicator panels are labeled non-parity diagnostic recomputations from the hash-bound broker bar corpus.

`alpha.ps1 validate-full` was invoked after the economic result and automatically generated generic fixed-parameter WFA, Monte Carlo and robustness artifacts. Those outputs were not part of the frozen HYP008 plan, are not used to rescue or promote the strategy, and are excluded from the HYP008 decision. The authoritative decision rests on the frozen matched Model-0 pair, exact lifecycle reconciliation and prespecified full-horizon decomposition.

## Verdict

`FULL_HORIZON_CONFIRMS_NO_EDGE_BOTH_ARMS_NEGATIVE`.

Removing the DD entry halt fixed sample censorship but did not reveal a profitable later regime. HYP008 is terminal KILLED as a diagnostic research child. No R:R retune, ATR multiple, stop minimum, session/year/direction filter, weekend rule, rerun, promotion or live use is authorized under this hypothesis.
