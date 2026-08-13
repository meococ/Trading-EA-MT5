# HYP-MULTI-TSMOM-D1-004-CONTRACT-PROBE — frozen no-order spec probe

Authority: source/formula only. Performance and economics are forbidden.

The EA attaches to broker-native `EURUSD H1`, sends zero orders, and emits the
current Strategy Tester contract for EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY,
USDCAD, USDCHF, XAUUSD and BTCUSD. Fields are Bid/Ask availability, digits,
point, tick size/value, contract size, lot min/max/step, trade calculation and
trade mode, base/profit/margin currencies, swap mode, long/short swap and the
triple-swap weekday.

The probe answers only whether the current broker contract can support a
defensible adverse financing overlay. It cannot establish historical swap,
PIT economics, expectancy, PF, drawdown or promotion readiness. Any financing
bound is frozen only after this receipt is read; it is not inferred from V4
performance.

Frozen run: EURUSD H1, MT5 Model 0, `[2026-08-03, 2026-08-05)`, deposit USD
100,000, leverage 1:100, no overrides, no visual mode.
