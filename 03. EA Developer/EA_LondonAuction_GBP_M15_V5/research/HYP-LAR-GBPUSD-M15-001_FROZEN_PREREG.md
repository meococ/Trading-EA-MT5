# Frozen prereg — HYP-LAR-GBPUSD-M15-001

Grok `/deep-research-trading-meta5` loop 5. GBPUSD M15 Model 0 design `[2018-01-01,2022-01-01)`. Server-time balance bars open 00:00..<07:45; range valid 18..55 pips. Auction decisions close 08:00..11:30. First close beyond edge by 3 pips freezes direction/level; within six later bars, a separate closed bar must touch the 4-pip retest zone, then a still-later body/range >=0.40 directional bar triggers next-bar entry. One-entry/day hard latch. Primary requires retest; locked control enters direct break.

Stop opposite balance edge plus 4 pips, clamped 12..38 pips. No TP/partial; +1R to +1.5 pip BE, +1.7R arms 9-pip tick trail; time stop 16 bars; flat 21:40 and Friday 18:40. Spread <=22 points. Volume min of 0.25% risk, 3x equity notional, 10% free-margin. Locks 1% daily/2.5% weekly.

Kill for incomplete full window/account stop-out, trades <160 or >620, PF <1.15, expectancy <=0, DD >6%, top-three >30% net, margin >10% or any day >1 entry. No OOS/control/tuning/subgroup filtering until design pass.
