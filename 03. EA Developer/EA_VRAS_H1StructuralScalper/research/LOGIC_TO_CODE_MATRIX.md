# LOGIC_TO_CODE_MATRIX — HYP-VRAS-EURUSD-M5-005

| Logic Rule | Economic Specification | MQL5 Implementation Function / Block |
|---|---|---|
| Closed-Bar non-repaint | Every signal evaluates at completed bar [1] | `OnTick()` -> check `iTime(_Symbol, PERIOD_M5, 1) != last_bar_time` |
| H1 Trend Alignment | H1 Bar [1] Close > H1 EMA200 (Long) / < (Short) | `iMA(_Symbol, PERIOD_H1, 200, 0, MODE_EMA, PRICE_CLOSE)` at bar [1] |
| M5 Session VWAP | Cumulative volume-weighted price from London Open (08:00 UTC) | Custom Welford `UpdateSessionVWAP()` |
| Path Confirmation | M5 Bar [1] Close > M5 Bar [2] High (Long) / < Low (Short) | Closed bar check `iClose(1) > iHigh(2)` |
| Position Sizing | Risk 0.25% account balance based on SL distance | `CalculateLotSize(sl_distance_price)` |
| Structural SL | Swing High/Low over 10 M5 bars + 1.5 pips buffer | `iHighest()` / `iLowest()` over 10 bars |
| Structural TP | Fixed 1.5 × SL distance | `sl_distance * 1.5` |
| Break-Even Trigger | Move SL to `Entry + 0.5 pip` when floating profit >= 1.0R | `ManageBreakEven()` in `OnTick()` |
