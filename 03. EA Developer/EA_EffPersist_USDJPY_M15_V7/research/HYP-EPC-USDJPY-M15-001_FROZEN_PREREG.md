# Frozen prereg - HYP-EPC-USDJPY-M15-001

Grok `/deep-research-trading-meta5` loop 7. USDJPY M15 Model 0 design `[2018-01-01,2022-01-01)`. Native closed bars only, one owned position maximum, broker server time accepted with DST, no weekend entry, daily flat 21:40 and Friday flat 18:40.

ER10 is absolute net close displacement from bar 1 to bar 11 divided by the sum of ten absolute one-bar close changes. Any zero-range bar in the ten-bar window forces ER to zero. ATR14 is the simple mean of 14 true ranges ending on the decision bar. A trigger requires ER >=0.68 and a nonzero net direction. Primary permits a signal only on bars 1-3 after the trigger when current ER >=0.55, the current ER direction remains the trigger direction, and the current close has not reversed more than 0.30 current ATR from the trigger close. Bar 4 expires the trigger. Matched control enters directly on ER >=0.68.

Initial stop is the current ER window low minus 0.20 ATR for long or window high plus 0.20 ATR for short, with entry distance clamped to 1.10..2.40 ATR. No TP/partial. At +0.9R move stop to +0.12R; at +1.5R arm a 0.75 ATR trail updated only on a new closed bar. Hard time stop 12 M15 bars.

Spread <=16 points. Volume is the minimum of 0.25% equity risk, 3.5x equity notional, and 10% free-margin use. Daily/weekly equity locks are 1.0%/2.5%.

Kill for incomplete full window/account stop-out, trades <170 or >580, PF <1.15, expectancy <=0, DD >6.5%, top-three >30% of total net profit, or margin >10%. No control, OOS, holdout, tuning, or subgroup filtering until primary passes all design gates.
