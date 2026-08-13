# Frozen preregistration - HYP-ORLS-EURUSD-H1-001

Frozen before MT5 outcome access on 2026-08-12 after Grok `/deep-research-trading-meta5` research and Codex leakage/execution review.

EURUSD H1, FivePercent native broker bars, current decision spread, one owned position. Six raw features at each new H1 open use the just-closed bars only: one-bar return, four-bar return, ATR8/close, ATR8/ATR24, tick-volume versus its last-eight-bar mean, and the current decision spread return z-scored against the prior 24 decision spreads. Each raw feature is standardized using EW state through the previous observation only (`beta=0.9975`, variance floor `1e-8`).

The fixed model is 7-dimensional recursive least squares (six standardized features plus intercept), `lambda=0.9975`, `alpha=1.0`, zero weights and `P=I/alpha`. A sample stores the standardized decision vector and broker H1 open. Exactly four contiguous H1 opens later, before the current prediction, the raw executable open-to-open log-return label matures and updates the model. No future label enters a prediction. Minimum warm-up is 120 valid observations.

Primary trades the RLS score only when its absolute value exceeds `1.5 * (decision spread / mid + 0.00008 commission return + 0.00005 slippage return)`. Matched control, if later authorized, substitutes four-hour open-to-open momentum with the same hurdle and lifecycle. Spread above 15 points cancels entry.

Entry is at the current H1 open/tick. Exit is at the open four H1 bars later. New entry is forbidden if that scheduled exit would cross the same-day 21:50 server flat or Friday 18:50 flat. Risk override is a catastrophe-only SL at `3*ATR14`, clamped 25..80 pips; no TP, BE, trail, session/weekday selection or outcome-derived filter. Volume is the minimum of 0.25% equity risk to the catastrophe stop, 3x notional and 9% free-margin use. Daily/weekly equity locks are 1.0%/2.5%.

DESIGN `[2018-01-01, 2022-01-01)` is authorized first for compile/runtime, coverage at least 98%, warm-up/delayed-label reconciliation, complete interval and cost-bearing economic diagnosis. Validation `[2022-01-01, 2024-01-01)` stays unopened until DESIGN engineering gates pass. Validation gates are 120..480 trades, PF >=1.15, average R >=0.05, DD <=8%, top-five <=30% positive net, catastrophe-stop rate <=25%, cost x1.5 PF >=1.05, cost x2 PF >=0.95, at least one positive validation year, PF above the matched control, and DSR >0 with 15 trials. Holdout 2024-current remains sealed until every validation gate passes.

Forbidden rescue: feature addition/deletion, symbol/timeframe transfer, threshold/hurdle/forgetting/standardizer/stop/hold tuning, direction/session/day/year selection, alternative model family, validation threshold fitting or holdout access after a failed gate.

Research anchors: Ljung and Soederstroem, *Theory and Practice of Recursive Identification* (MIT Press, 1983); Hayes, *Statistical Digital Signal Processing and Modeling* (Wiley, 1996); Lopez de Prado, *Advances in Financial Machine Learning* (Wiley, 2018), DOI `10.1002/9781119482086`.
