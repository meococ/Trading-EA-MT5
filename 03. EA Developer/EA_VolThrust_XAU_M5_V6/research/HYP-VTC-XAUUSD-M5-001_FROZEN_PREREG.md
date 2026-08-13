# Frozen prereg - HYP-VTC-XAUUSD-M5-001

Grok `/deep-research-trading-meta5` loop 6. XAUUSD M5 Model 0 design `[2018-01-01,2022-01-01)`. Inputs use completed OHLC bars, broker tick volume, and live tester spread. Broker server time is accepted as recorded, including DST. No new weekend entry; force flat at 21:45 server and Friday 18:45.

On a completed bar, ATR14 is the simple mean of 14 true ranges ending on that bar. VolSMA20 is the mean tick volume of the 20 completed bars ending on that bar. Missing or zero volume anywhere in the required window fails closed. A thrust requires directional body/range >=0.62, range/ATR >=1.25, and tick volume/VolSMA >=1.70. Primary freezes thrust direction/high/low/ATR and, within four later bars, requires a pause that makes no new extreme in the thrust direction, closes within the thrust range expanded 0.25 ATR on both sides, and has body/range <=0.45. Entry is at the next bar open. Locked matched control enters the thrust directly without the pause.

Initial stop is thrust low minus 0.35 ATR for long or thrust high plus 0.35 ATR for short, with entry distance clamped to 1.15..2.50 thrust ATR. No TP/partial. At +0.9R move stop to +0.15R; at +1.6R arm a 0.80 ATR trail updated only when a new bar makes the previous bar available. Hard time stop 24 M5 bars. One owned position maximum.

Spread <=45 points. Volume is the minimum of 0.25% equity risk, 3.5x equity notional, and 10% free-margin use. Daily and weekly equity locks are 1.0% and 2.5%.

Kill for incomplete full window/account stop-out, trades <170 or >580, PF <1.15, expectancy <=0, DD >6.5%, top-three >32% of total net profit, or margin use >10%. No control, OOS, holdout, tuning, or subgroup filtering until the primary design passes every gate.
