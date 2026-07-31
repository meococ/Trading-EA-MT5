# HYP-VRAS-EURUSD-M5-008 — Full-Horizon Diagnostic Readout

Verdict: **full-horizon coverage confirms no edge; both stop arms remain negative.**

| Metric | Control fixed clamp | Challenger ATR structural |
|---|---:|---:|
| Trades | 4841 | 3611 |
| Profit factor | 0.7736 | 0.7722 |
| Gross price PF before recorded costs | 0.8803 | 0.8870 |
| Net profit (USD 500k diagnostic) | -25579.82 | -20791.58 |
| Mean realized R | -0.1096 | -0.1184 |
| Max DD | 5.31% | 4.28% |
| Cadence / elapsed week | 23.21 | 17.31 |
| Initial-stop exit share | 40.71% | 44.78% |
| Mean stop | 9.45 pip | 9.34 pip |
| Cost PF 1.5x proxy | 0.7263 | 0.7220 |
| Cost PF 2x proxy | 0.6829 | 0.6762 |

Relative PF lift -0.0013; mean-R lift -0.0088; DD change -1.02pp; trade-count change -1230.

Coverage and reconciliation pass for both arms: 100% history quality, 298,483 bars, full 2019–2022 interval, no tester stop-out, account DD halt disabled, and exact report ↔ lifecycle net P/L.

Every calendar year and every telemetry ATR quartile is PF < 1 in both arms. The later market regimes do not reverse the early negative expectancy. The challenger reduces trade count and drawdown mainly through rejection/exposure reduction; it does not improve PF or mean R.

The nominal TP is 1.5R, but the challenger realizes only a 1.0586 payoff ratio (average win +0.9555R versus average loss -0.9026R). Break-even WR is therefore 48.58%, materially above the observed 42.20%. The largest winner (+5.63R) and largest loser (-6.04R) both cross a weekend: the 24-bar time stop pauses while the market is closed, so this intraday surface has uncontrolled gap tails.

The generic `validate-full` command automatically emitted WFA/Monte-Carlo/robustness diagnostics after the result. They were outside the frozen HYP008 plan and are excluded from the verdict; they do not create rescue or promotion authority.

This is diagnostic-only. Cost provenance remains unverified, and no parameter/R:R/session/year/direction rescue, promotion, or live use is authorized.
