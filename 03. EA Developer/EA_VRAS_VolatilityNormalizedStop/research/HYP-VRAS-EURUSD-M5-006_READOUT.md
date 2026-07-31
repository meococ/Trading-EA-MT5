# HYP-VRAS-EURUSD-M5-006 — Matched Model-0 Readout

Verdict: **KILL — volatility-normalized structural stop is worse than control and both arms lose money.**

| Metric | Control fixed clamp | Challenger ATR structural |
|---|---:|---:|
| Trades | 240 | 158 |
| Profit factor | 0.7881 | 0.7313 |
| Net profit | USD -6033.32 | USD -6059.53 |
| Expectancy/trade | USD -25.14 | USD -38.35 |
| Mean realized R | -0.1026 | -0.1570 |
| Max DD | 8.28% | 7.66% |
| Cadence / elapsed week | 1.1507 | 0.7575 |
| Initial-stop exit share | 39.58% | 50.63% |
| Mean stop | 9.10 pips | 7.94 pips |
| Cost PF 1.5x proxy | 0.7375 | 0.6867 |
| Cost PF 2x proxy | 0.6908 | 0.6455 |

Relative PF lift: -0.0568; mean-R lift: -0.0545; initial-stop share reduction: -11.05%; DD change: -0.62pp.

Lifecycle reconciliation is exact in both arms: every position has one OPEN and one final CLOSE, all initial risk values are positive, and report-minus-lifecycle net gap is USD 0.00.

Control account guard latched after its last exit at 2019.03.14 11:30:00; challenger at 2019.03.12 05:17:28. Cadence uses the full frozen calendar window, not active weeks.

The ATR stop reduced drawdown slightly but lowered PF, win rate, mean R, cadence and trade count. This is not a successful SL fix. The entry decision surface still has negative expectancy; wider stops merely change the loss distribution.

Monte Carlo, WFA and parameter robustness were not run because the frozen base and relative gates already fail. Running them cannot rescue HYP006. No retune, alternate ATR multiple, R:R, session/day/year/direction filter, promotion or live authority.
