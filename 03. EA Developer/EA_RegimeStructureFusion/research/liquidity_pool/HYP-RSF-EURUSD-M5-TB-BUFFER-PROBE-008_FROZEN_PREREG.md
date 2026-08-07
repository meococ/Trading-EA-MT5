# HYP-RSF-EURUSD-M5-TB-BUFFER-PROBE-008 — engineering probe

Diagnostic only; frozen before telemetry instrumentation.

- EURUSD M5, `2018.01.01`–`2018.02.01`, Model 1.
- No economic, comparison, optimization, validation, holdout or promotion authority.
- Strategy parameters remain identical to the liquidity-pool lane.
- The only code change is fail-code counters for BarsCalculated, TB buffers 26/43/46/47, other required reads, TB ready value and TB contract value.
- Success means exactly one dominant failing counter identifies the snapshot contract defect. No profitability metric may be reported or used.
- A final full-window Model-0 hypothesis requires a new source hash and ID after the defect is corrected and compile/tests pass.
