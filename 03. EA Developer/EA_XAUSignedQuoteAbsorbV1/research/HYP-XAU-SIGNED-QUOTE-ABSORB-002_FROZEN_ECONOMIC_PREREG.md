# HYP-XAU-SIGNED-QUOTE-ABSORB-002 — Frozen economic baseline

Frozen before reading any trading-performance output from this EA identity.

## Market thesis

Thirty-second signed quote pressure that is large but fails to move the XAU mid-price proportionally is treated as short-horizon absorption. Negative signed pressure with a resilient mid predicts a long reversal; positive signed pressure with a capped mid predicts a short reversal.

## Identity and data

- EA: `EA_XAUSignedQuoteAbsorbV1`
- Symbol: `AFD_XAUUSD_DUKA_V3`, M1, MT5 Model 4 real ticks
- Design window: `2018.01.01 <= t < 2022.01.01`
- Validation sealed: `2022.01.01 <= t < 2024.01.01`
- Holdout sealed: `2024.01.01 <= t <= 2026.07.31`
- Data source: imported Dukascopy true Bid/Ask; native spread is paid by tester.
- Baseline is research-only because the custom-symbol tester does not prove a live FivePercent commission/slippage contract.

## Frozen signal

- Strict `MqlTick.time_msc` arrival order; invalid nonpositive or crossed quotes ignored.
- Thirty-second interval before a closed M1 decision.
- `NetSignedPressure = sign(deltaBid) + sign(deltaAsk)` accumulated in the window.
- Long: pressure <= -8 and mid move >= -0.12 ATR(14).
- Short: pressure >= +8 and mid move <= +0.12 ATR(14).
- Entry at first tick of the next M1 only when native spread <= USD 0.30.
- Entry hours 01:00–21:00 custom-symbol time; Friday no new entry from 18:00.

## Frozen execution and risk

- One position at a time; no pyramiding or pending orders.
- SL distance: clamp(1.70 ATR(14), USD 0.35, USD 1.60).
- TP: 1.25R; time exit at seven minutes; Friday/weekend flatten safety.
- Position risk: 0.20% of current account balance using `OrderCalcProfit`; volume rounded down.
- Baseline has zero added synthetic slippage. If it survives, immutable stress variants subtract USD 0.05 and USD 0.10 price units round-trip per trade before any validation window is opened.

## Predeclared design verdict

Continue only if all are true after native Bid/Ask spread:

- PF >= 1.15;
- maximum equity drawdown <= 7.5%;
- average trade >= 0.08R;
- SL exit rate <= 55%;
- top 5% of trade profits contribute <= 38% of total positive profit;
- order/runtime reject rates do not make the implementation invalid.

A fail is terminal for this exact hypothesis identity. No post-hoc session, direction, threshold, SL, TP, or holding-time rescue is allowed. A materially new market mechanism must receive a new hypothesis ID.

