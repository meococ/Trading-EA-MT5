# Frozen prereg - HYP-XRV-EURUSD-M15-001

Grok `/deep-research-trading-meta5` loop 8. Execution EURUSD, references USDJPY and GBPUSD, M15 Model 0 design `[2018-01-01,2022-01-01)`. The current and preceding closed bars must share identical open times on all three symbols and all six bars must have positive tick volume; otherwise the EUR chart bar is skipped with no warm-up or state update. Fifty synchronized observations are required before signals.

For each synchronized decision bar, compute one-bar simple returns. Basket = (-USDJPY return + GBPUSD return)/2 and residual = EURUSD return - basket. A dislocation requires absolute residual >=0.00028. Primary freezes residual sign and size, then within later bars 1-5 requires absolute residual to shrink by at least 40% while the EURUSD candle closes in the fade direction. Entry is at the next bar open. Matched control enters the fade directly on the dislocation.

Initial EURUSD stop distance is 1.8 ATR14 clamped to 12..32 pips. No TP/partial. At +0.9R move stop to entry plus 1 pip; at +1.5R arm an 8-pip tick trail. Hard time stop 10 M15 bars. Daily flat 21:40, Friday flat 18:40, no weekend entry, one EURUSD position maximum.

Spread <=16 points. Volume is the minimum of 0.25% equity risk, 3.5x equity notional, and 10% free-margin use. Daily/weekly locks 1.0%/2.5%.

Kill for incomplete window/account stop-out, trades <170 or >550, PF <1.15, expectancy <=0, DD >6.0%, top-three >28% total net, margin >10%, or synchronized-data skip rate >8%. No control, OOS, holdout, tuning, or subgroup filtering until primary passes.
