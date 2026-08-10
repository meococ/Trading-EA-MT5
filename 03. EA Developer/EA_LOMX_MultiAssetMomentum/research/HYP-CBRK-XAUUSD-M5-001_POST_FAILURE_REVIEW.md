# HYP-CBRK-XAUUSD-M5-001 — independent post-failure review

Verdict: `PARK_ENGINEERING_PRE_EXECUTION_SIGNAL_SESSION_CLOCK_MISMATCH_NO_MT5_NO_OUTCOMES_NO_ECONOMICS`.

The reviewer independently confirmed that `OnTick()` gates weekdays and `[07:00,16:00)` using decision-time `utc_now` before `LoadClosedBars()` materializes the signal. Because the decision occurs at the next M5 open, the actual eligible closed signal bars are shifted one bar earlier: `[06:55,15:55)`.

The exact arithmetic in `EvaluateBreakout()` remains aligned with the outcome-blind Stage-0 cell. This review therefore does not reject the XAUUSD compression-breakout mechanism, source cadence, data feasibility, or economic edge. There was no MT5 attempt, report, order, deal, trade, return, PF, cost evaluation, validation, or holdout access.

A lawful fresh revision must use `ServerToUtc(rates[0].time)` after a successful `LoadClosedBars()`, gate the signal-bar UTC at 06:55/07:00/15:55/16:00 boundaries, use the same signal UTC when resolving the exact 72-bar Asian range, and preserve `utc_now` for execution-time position/risk/flatten management. Using `rates[1]` is forbidden because that is bar2 under `CopyRates(...,1,...)` with series ordering.

The DQ child remains unopened. Before it runs, its preregistration must require exactly `351303` report bars, HQ strictly greater than 97%, the exact fixed window, and a one-shot claim/receipt/terminal chain with every trading and economic authority disabled.
