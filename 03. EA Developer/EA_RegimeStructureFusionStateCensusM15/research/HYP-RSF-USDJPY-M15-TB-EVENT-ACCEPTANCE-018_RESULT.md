# HYP-RSF-USDJPY-M15-TB-EVENT-ACCEPTANCE-018 — Result

## Verdict

`KILL_NO_STABLE_TB_EVENT_EDGE`

The preregistered TB Smart Money Concept structural event clock did not produce a stable, cost-positive acceptance model on USDJPY M15 discovery data. No 2023+ validation or holdout data was opened.

## Bound object

- Symbol/timeframe: USDJPY M15.
- Discovery window: 2018-01-01 through 2022-12-31; expanding-year tests in 2019, 2020, 2021 and 2022.
- Parent census run: `20260808_012351`.
- Parent census SHA-256: `1FFA026BF50C431C87EC9EC9CE5DD7D17ABB26DBDB179680B8E75C5421642D2A`.
- Event direction was fixed by TB SMC rising edges:
  - long: structure-up, displacement-up or sweep-low;
  - short: structure-down, displacement-down or sweep-high.
- Same-direction events on one bar were collapsed; 491 opposing-direction conflicts were rejected.
- The acceptance model retained features from all five indicators: QQE MOD, Modern Bollinger Bands, AI Regime Detection, Volatility Regime Classifier and TB SMC.
- No session filter, event-type removal, outcome-driven debounce or 2023+ data access was allowed.

## Outcome-blind Stage A

- Unique events: 32,678.
- Long/short balance: 50.44% / 49.56%.
- Pooled cadence: 125.410 events/week.
- Annual cadence range: 122.414 to 127.259 events/week.
- Maximum year share: 20.26%.
- Event flags: 5,202 structure rises, 24,834 displacement rises and 6,147 sweep rises. Multiple same-direction flags may occur on one event.

All preregistered cadence and balance gates passed. This only authorized Stage B; it was not economic evidence.

## Frozen Stage B

Six cells were tested: Logistic and shallow HistGradientBoosting at TP 0.75, 1.00 and 1.25 ATR, with SL 1.00 ATR and an eight-bar horizon. Thresholds targeted 2.5, 3.5 and 4.5 trades/week and were chosen only on each expanding training fold. Costs used observed spread with the preregistered 1.5x spread plus volatility-slippage formula.

Best cell: Logistic, TP 1.00 ATR.

- Trades at primary cadence: 799.
- Pooled profit factor: 0.857068.
- Pooled net result: -60.321847R.
- Median yearly profit factor: 0.916812.
- Adjacent-cadence pooled PF: 0.848034 at 2.5/week and 0.830641 at 4.5/week.
- Selected flags: 238 structure, 468 displacement and 223 sweep. A trade can carry more than one flag.

Year results for the best cell:

| Year | Trades | Trades/week | Net R | PF |
|---:|---:|---:|---:|---:|
| 2019 | 219 | 4.216 | -42.674 | 0.668 |
| 2020 | 184 | 3.534 | -14.434 | 0.854 |
| 2021 | 159 | 3.076 | -0.883 | 0.989 |
| 2022 | 237 | 4.587 | -2.331 | 0.980 |

Every tested model/target cell had pooled PF below 0.86. The result therefore fails profitability, cross-year consistency and adjacent-threshold stability gates.

## Interpretation and failure radius

TB SMC provides a stable and balanced structural event clock, but the event directions do not have sufficient post-cost expectancy. The other four indicators could not reliably distinguish accepted from rejected TB events under the frozen decision surface. This closes the native-price, five-indicator state/transition/barrier/event-acceptance family tested on USDJPY M5 and M15. It does not prove that the indicators are visually wrong; it proves that these closed-bar features did not form a tradable edge under the tested causal contracts and observed costs.

Reopening requires a materially different mechanism or information set, such as causal quote/order-flow information, not another conjunction, session subset, event-type deletion or parameter rescue on the same census.

## Evidence

- Stage-A JSON SHA-256: `161CBFA138C121933D712CE8DB2A9634CA128A3A165B2642F16644E97027E0DE`.
- Event clock SHA-256: `B18B87FA4F8003F752154B5EC365C67EDBDA4DAA7187F28DAC70BA8701039A32`.
- Stage-B result SHA-256: `CC6726B920BCC9071797C19101653A5CFF556B16886165CDF2F658A0CED6C26F`.
- Stage-B folds SHA-256: `C3B6A5E215D6D8313C40EC868CAD58C65147393A1553CD27AD076BEC042F17CF`.
- Stage-B script SHA-256: `2C7F7FEFB2518722DC806062D8DD559F2C885008E9DA283FAE7D1D3A5F8DAB8D`.

