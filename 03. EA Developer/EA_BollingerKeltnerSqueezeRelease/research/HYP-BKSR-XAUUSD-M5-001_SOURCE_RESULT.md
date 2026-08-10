# HYP-BKSR-XAUUSD-M5-001 - Source Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_BBKC_SQUEEZE_RELEASE`

The sole deterministic outcome-blind source attempt completed. The exact H1 Bollinger-Keltner squeeze-release mechanism achieves the target opportunity clock, balanced directions and stable yearly cadence, but its frozen dual-axis H1-to-native-M5 decision mapping misses the exact coverage gate.

- H1 source / design / usable rows: `107,679 / 29,461 / 29,461` (`100%`, PASS)
- M5 clock rows: `1,233,571`; no M5 price columns read
- raw / executable / clock-rejected events: `757 / 731 / 26`
- exact M5 decision coverage: `96.565390%` (FAIL; gate `>=97%`)
- LONG / SHORT: `363 / 368` (PASS)
- pooled cadence: `2.802300/week` (PASS)
- annual cadence: `2.4932-3.2322/week` (all PASS)
- max-year share: `23.1190%` (PASS)
- conflicts: `0` (PASS)

Only exact M5 decision coverage failed. No M5 price, post-event H1 OHLC, return, trade simulation, PnL, PF, validation or holdout value was read. This is not an economic no-edge conclusion.

The exact ID is terminal. The `97%` gate will not be lowered and UTC/source-epoch mapping will not be relaxed. No timeframe, period/multiplier, duration/intensity, filter, retest, cooldown or delayed-entry rescue is authorized.
