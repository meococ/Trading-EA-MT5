# EA_TickVolumeEffortRejection

Research package for `HYP-TVER-XAUUSD-M5-001`.

The hypothesis combines a TradingView-style Relative Volume calculation with a completed-bar effort-versus-result rejection pattern on FivePercent XAUUSD M5. `tick_volume` is treated only as unsigned broker quote activity; it is not exchange volume, aggressor volume or CVD.

Terminal status: `PARK_SOURCE_FEASIBILITY_EXACT_TVER_MAPPING` after the sole frozen attempt. The exact mapping produced 141 candidates and 0.540526/week, so no MQL5 indicator/EA, economics, validation, holdout, paper trading or live deployment is authorized. This package remains audit-only.

Canonical sources:

- TradingView Relative Volume calculation: <https://www.tradingview.com/support/solutions/43000635874-how-do-we-calculate-relative-volume-and-relative-volume-at-time/>
- TradingView Relative Volume at Time indicator: <https://www.tradingview.com/script/n0f50JKv-Relative-Volume-at-Time/>
- MQL5 `MqlRates` tick-volume field: <https://www.mql5.com/en/docs/constants/structures/mqlrates>
