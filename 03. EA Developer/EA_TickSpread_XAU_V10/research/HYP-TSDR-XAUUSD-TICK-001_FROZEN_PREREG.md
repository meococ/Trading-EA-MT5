# Frozen preregistration - HYP-TSDR-XAUUSD-TICK-001 P0

Freeze: 2026-08-12. Authority: `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`.

This phase asks one question only: does the configured FivePercent MT5 Model-0 XAUUSD tick stream support the quote-flow fields required by the proposed spread-dislocation/refill scalper? P0 cannot trade and cannot authorize performance metrics.

Run XAUUSD M1 from `2018.01.01` to `2018.01.10`, current spread, Model 0. Collect exactly the first five observed broker dates; freeze the verdict at the first valid tick of the following broker date. Distribution statistics exclude equal-`time_msc` ticks.

PASS requires all of:

- invalid bid/ask rate <= 0.30%;
- decreasing `time_msc` rate <= 0.10%;
- equal-`time_msc` rate <= 15.00%;
- median raw XAUUSD spread between 0.05 and 3.00 inclusive;
- no more than 40.00% of all ticks belonging to constant-spread runs of at least 40 ticks;
- at least five broker dates and at least one distribution tick.

Any failure is `DATA_FRONTIER_BLOCKED`. Do not change the gates, switch symbol, reinterpret generated ticks, or inspect economics. A PASS permits a fresh full-strategy source identity; it does not establish edge.

