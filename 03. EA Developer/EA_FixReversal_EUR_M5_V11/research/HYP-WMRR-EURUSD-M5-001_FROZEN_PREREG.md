# Frozen preregistration - HYP-WMRR-EURUSD-M5-001

Freeze: 2026-08-12. Primary untuned Model-0 baseline only.

Mechanism: benchmark-related order concentration in the LSEG WMR London 16:00 fixing window can create temporary EURUSD price pressure that partially reverses after the five-minute calculation window. This is scheduled institutional flow, distinct from London-open range/retest logic.

Clock authority: accepted no-trade run `EA_FixClock_EUR_M5_V11P/20260812_024540` classified FivePercentOnline-Real as `US_DST_NY_CLOSE`. London 16:00 is therefore 18:00 server normally and 19:00 from the US DST start to UK DST start and from UK DST end to US DST end. Calendar boundaries are calculated in-source.

At 18:05/19:05 availability, require 13 exact contiguous M5 bars. Store the close of the bar opened at 18:00/19:00 as `FixClose`. Displacement is that close minus the close of the bar opened exactly 60 minutes earlier. Require absolute displacement >=1.2 pips. Primary observes exactly the following three bars, opened +5/+10/+15 minutes; enter at their close availability when price first reverses at least 35% of the stored displacement. Direction is opposite displacement. One trade/day.

SL is 1.9 ATR(14), clamped 12-28 pips; TP 1.4R; time stop 18 bars; no trailing/BE. Risk 0.20%, notional 3x, margin 9%, spread 14 points, daily/weekly loss 0.9/2.2%. Daily flat 21:50; Friday flat 18:50. Unreachable stops cancel, never widen.

Baseline: EURUSD M5, 2018-01-01 through 2022-01-01, Model 0, current broker costs. Expected 180-320 trades. Kill if trades <150 or >380, PF <1.15, DD >6%, top three >30% of positive net, or average absolute displacement of entries <1.5 pips. No matched control or OOS unless every design gate passes.

Forbidden rescue: month-end selection, weekday/session/hour selection, changing the 18/19 mapping, displacement/retracement/ATR/exit tuning, alternate windows, control/OOS/holdout after failure.

