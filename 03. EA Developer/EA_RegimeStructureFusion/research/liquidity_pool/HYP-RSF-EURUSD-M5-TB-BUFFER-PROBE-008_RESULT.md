# HYP-RSF-EURUSD-M5-TB-BUFFER-PROBE-008 — diagnostic result

Run `20260807_101652` is engineering-only and has no economic authority.

Across 2,112 eligible January-2018 decision bars:

- `snapshot_fail_tb46_read = 2112`
- all other read/value fail counters = 0
- `indicator_ready = 0`

Root cause: TB v3 binds liquidity buffers 44–47 as `INDICATOR_DATA`, but `indicator_plots` remained 44. MetaTrader compiled and loaded the EX5 without an error, yet `CopyBuffer(handle,46,...)` failed on every bar because the added public buffers were outside the exported plot surface.

Required correction: set `indicator_plots=48`, add four `DRAW_NONE` plot definitions/labels for buffers 44–47, preserve calculation buffer 48, then rerun the same short diagnostic before any full-window economic run.

No strategy parameter or trade rule is implicated by this probe.
