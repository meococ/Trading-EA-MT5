# HYP-VRAS-EURUSD-M5-006 — Forensic Analysis

## Economics and cost

The challenger fails every frozen absolute economic gate: 158 trades, PF 0.7313, net -USD 6,059.53, expectancy -USD 38.35/trade, mean realized R -0.1570, max DD 7.66%, and cadence 0.7575 trades per full elapsed calendar week. Price P/L was already -USD 3,497.82 before -USD 2,561.71 recorded costs. Diagnostic PF proxies fall to 0.6867 at 1.5x recorded cost and 0.6455 at 2x. Cost provenance remains unverified, so these are diagnostic stress results only.

## Matched comparison and stop mechanics

Control was also negative: 240 trades, PF 0.7881, net -USD 6,033.32, mean R -0.1026, DD 8.28%. Challenger relative deltas are PF -0.0568, mean R -0.0545R, initial-stop exit share worse by 11.05 percentage points, and DD better by only 0.62 percentage points. Its average stop was 7.94 pips versus control 9.10 pips; the frozen ATR floor reached as low as 2.5 pips while control could not go below 4.0. Rejecting raw structures above 3 ATR removed 199 candidates. Thus this mechanism did not reliably widen weak stops; it combined quiet-regime narrow stops with rejection of wider structures.

## Time, session, direction and regime

Both arms hit the initial-equity DD entry latch in Q1 2019, so the remaining frozen window contains no later trades. Control last exit was 2019-03-14 11:30 broker time; challenger last exit was 2019-03-12 05:17:28. This is a complete and adverse time-stability conclusion, not evidence about 2020–2022 regime performance. Challenger session results were Asia 39 trades / PF 0.64 / -USD 2,050; Europe 59 / PF 0.91 / -USD 645; New York 51 / PF 0.69 / -USD 2,509; off-hours 9 / PF 0.34 / -USD 856. No session is a valid rescue. Long/short decomposition is retained in lifecycle data, but no preregistered directional veto is authorized. Regime breakdown is insufficient because the HYP006 decision surface does not emit an independent regime label.

## Execution, lifecycle and funnel

History quality is 100% for both Model-0 runs. Control reconciles 240 OPEN + 240 final CLOSE across 240 unique positions to report net exactly; challenger reconciles 158 + 158 across 158 positions exactly. Minimum recorded initial risk is positive (control USD 234.00; challenger USD 235.06). Tester log triage is clean. Challenger funnel: 10,863 closed-bar signals/attempts, 158 opens, 199 structure-too-wide rejects, 10,505 shared guard rejects, one risk reject, and the account DD latch active. The generic datalog analyzer reports zero because it does not ingest lifecycle-v3; the direct report/lifecycle reconciliation is authoritative.

## Winning and losing causes

Winners require a rapid directional continuation to reach 1.5R before the two-hour cap; target exit share was 26.58%. Losers are dominated by initial-stop exits at 50.63%. The rendered tail loser P222 demonstrates the key conflict: a 2.8-pip challenger SL was hit just before price moved strongly in the intended short direction. Wider risk is not sufficient by itself, however, because aggregate price P/L remains negative and the challenger performs worse than control.

## Logic conflicts and limitations

- max(structure, 1 ATR) is not a guaranteed wider stop than a four-pip floor when M5 ATR is below four pips.
- Rejecting structure above 3 ATR changes sample composition and lowers cadence; it is part of the frozen mechanism, not a post-hoc excuse.
- The rolling 48-bar VWAP is not a London/session VWAP or AVWAP.
- Cost/news/slippage provenance is diagnostic only; no promotion or live inference is allowed.
- Decision indicator charts are labeled non-parity diagnostic recomputations from hash-bound broker M1 bars.

Final verdict: KILL_VOLATILITY_NORMALIZED_STOP_WORSE_THAN_CONTROL. Monte Carlo, WFA and parameter sensitivity are not run because base economics and the matched relative gates already fail; they cannot rescue HYP006.
