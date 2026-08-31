# EA_LSSOBPropScalper

Canonical audit package for the Owner-required exact LSS-OB EURUSD M15
replication.

Terminal state: `KILL_AT_MT5_MODEL0_CADENCE_ZERO_TRADE`.

- Hypothesis: `HYP-LSS-OB-REPL-MT5-EURUSD-M15-002`.
- Control MT5 Model 0: `20260719_001202`.
- Matched challenger MT5 Model 0: `20260719_001306`.
- Window: 2019-01-03 through 2022-12-31; 2023+ remained sealed.
- Both arms: 100% history quality, 99,475 bars, 79,411,093 ticks,
  388 sweeps, zero qualifying displacement/FVG, zero entries, zero trades.
- Tests: 20/20 PASS; compile: 0 errors/0 warnings; non-repaint V2: PASS.

PF, win rate, expectancy, Sharpe and drawdown are undefined because the trade
set is empty. The source is retained for audit only. Do not rerun, optimize,
change asset/timeframe/session/threshold/RR, open holdout, promote, or attach
live.

Readout:
`research/HYP-LSS-OB-REPL-MT5-EURUSD-M15-002_READOUT.md`.
