# HYP-MULTI-TSMOM-D1-004-CONTRACT-PROBE-002 — frozen no-order spec probe

Authority: source/formula only. Performance and economics are forbidden.

Legal delta from the failed V1 engineering probe: emit the exact
`DATA_EPOCH_D0_SERIES_PROOF` required by the AlphaFactory fixed-window data
quality gate. Broker fields, symbol list, time window and no-order behavior are
unchanged. This revision exists because V1 produced a report but failed the
post-run D0 journal-proof gate.

The EA attaches to broker-native `EURUSD H1`, sends zero orders, and emits the
current Strategy Tester contract for EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY,
USDCAD, USDCHF, XAUUSD and BTCUSD. The fields are Bid/Ask availability, digits,
point, tick size/value, contract size, lot min/max/step, calculation/trade mode,
base/profit/margin currencies, swap mode, long/short swap and triple-swap day.

Frozen run: EURUSD H1, MT5 Model 0, `[2026-08-03,2026-08-05)`, deposit USD
100,000, leverage 1:100, no overrides, no visual mode. This can support only a
current-contract adverse-financing bound; it cannot establish historical swap,
PIT economics, expectancy, PF, drawdown or promotion readiness.
