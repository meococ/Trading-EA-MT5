# AIRQMB EURUSD SCREEN-005 - Engineering-Invalid Trade Gate

- Run ID: `20260806_021144`
- Model/date: EURUSD M5, Model 4 real ticks, `2023.01.02-2024.12.31`
- History: 100% real ticks, 148,937 M5 bars, 51,367,449 ticks
- Report: generated; enhanced analysis stopped because there were no deals
- Economic trials consumed: `0` (execution path was invalid)

The indicator and signal funnel was healthy: 80,825 ready closed bars, 25,374 bull, 27,913 bear, 6,077 range and 21,461 high-vol bars; raw MBB signals included 54 S1, 3,961 S2 and 52 S3 events. The EA attempted 4,067 admissible entries after session and geometry filters, but every attempt was rejected by the EA's own `OrderCheck` condition.

Root cause: `OrderCheck()` returned `true` with `MqlTradeCheckResult.retcode == 0`, which is the documented successful preflight result. The EA incorrectly required `TRADE_RETCODE_DONE` or `TRADE_RETCODE_PLACED`, codes that belong to `MqlTradeResult` after `OrderSend()`. No market order was submitted.

The successor accepts a preflight when `OrderCheck()` returns true and continues to validate `OrderSend()` using the trade-server result codes. Strategy equations and parameter values are unchanged. SCREEN-005 is engineering-invalid and superseded across all nine cells.
