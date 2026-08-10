# EA_MFIExtremeReentry

Research package for `HYP-MFI-XAUUSD-M5-001`.

The hypothesis tests the standard 14-period Money Flow Index extreme re-entry on completed FivePercent XAUUSD M5 bars. MT5 `tick_volume` is used only as the indicator's broker-activity weight; it is not true money flow, exchange volume or aggressor flow.

`HYP-MFI-XAUUSD-M5-001` is terminal `PARK_SOURCE_FEASIBILITY_EXACT_MFI_REENTRY`: 6,262 events and 24.0055/week made one-step re-entry too frequent. It authorizes no MQL5/economics. The active research successor is the separately preregistered four-step failure-swing FSM `HYP-MFI-XAUUSD-M5-002`.

Primary references:

- TradingView Money Flow (MFI): <https://www.tradingview.com/support/solutions/43000502348-money-flow-mfi/>
- MQL5 `iMFI`: <https://www.mql5.com/en/docs/indicators/imfi>
