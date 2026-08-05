# AIRQMB EURUSD SCREEN-003 - Aborted iCustom Parameter Smoke

- Model/date cell: EURUSD M5, Model 4, `2023.01.02-2024.12.31`
- Stop: before report generation and before any performance outcome read
- Economic trials consumed: `0`

The tester log showed every custom indicator returning `INIT_PARAMETERS_INCORRECT` from the first simulated bar. The long explicit `iCustom` argument lists were therefore not accepted by the runtime EX5 input schemas. CopyBuffer retried the failed instances, producing repeated errors; no signal or trading result from this launch is admissible.

The outcome-blind successor removes the fragile variadic parameter lists and uses each indicator's canonical defaults. Tester-aware guards inside the three indicators suppress only chart objects and alerts while retaining every mathematical buffer. SCREEN-003 is superseded consistently across all nine cells with no report and no economic verdict.
