# Frozen prereg - HYP-VRE-EURUSD-M15-001

Grok `/deep-research-trading-meta5` loop 9. EURUSD M15 Model 0 design `[2018-01-01,2022-01-01)`. Single-symbol completed OHLC, current spread, account equity, and margin only. No reference history, tick reconstruction, external data, or indicator sidecar. Warm-up 50 closed bars; invalid or zero slow ATR fails closed.

ATR fast/slow are simple means of 8 and 40 true ranges ending on the decision bar. Expansion requires ATR8/ATR40 >=1.55 and directional body/range >=0.55. Primary freezes expansion direction and close. The immediately following closed bar must close in the same direction and not close more than 0.30 current ATR8 against the expansion close; otherwise state expires immediately. Entry is at the next bar open. Matched control enters directly on expansion.

Initial stop is 1.6 current ATR8 clamped 11..28 pips. No TP/partial. At +0.9R move stop to entry plus 0.8 pip; at +1.4R arm a 7-pip tick trail. Hard time stop 10 M15 bars. Daily flat 21:40, Friday flat 18:40, no weekend entry, one position.

Spread <=15 points. Volume is min of 0.25% equity risk, 3.5x equity notional, and 10% free-margin use. Daily/weekly locks 1.0%/2.5%.

Kill for incomplete window/account stop-out, trades <180 or >560, PF <1.15, expectancy <=0, DD >6.0%, top-three >28% net, or margin >10%. No control/OOS/holdout/tuning/filtering until primary passes.
