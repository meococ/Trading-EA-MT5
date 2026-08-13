# Frozen prereg - HYP-EPC-USDJPY-M15-002

Runtime-only revision of Grok `/deep-research-trading-meta5` loop 7. The complete economic object, constants, USDJPY M15 binding, Model 0 design `[2018-01-01,2022-01-01)`, entry/exit/risk logic, and gates are identical to `HYP-EPC-USDJPY-M15-001`.

The prior run `20260812_015341` created a report but AlphaFactory rejected its 8 MiB truncated journal before analysis. That report is not economic evidence and was not inspected for performance. This revision changes only evidence throughput: new EA/hypothesis/magic identity, disables CTrade verbose logging, and retains only INIT, ENTRY, EXIT, and SUMMARY telemetry while all state counters remain in SUMMARY.

ER10 is absolute 10-bar net close displacement divided by ten-bar absolute close path. Trigger >=0.68; primary persistence on later bars 1-3 requires ER >=0.55, same net direction, and reversal <=0.30 ATR; bar 4 expires. Stop is current ER-window extreme plus 0.20 ATR, clamped 1.10..2.40 ATR. BE +0.12R at +0.9R; 0.75 ATR closed-bar trail after +1.5R; 12-bar time stop; one position. Spread <=16 points; risk 0.25%, notional 3.5x, free-margin 10%, daily/weekly locks 1.0%/2.5%.

Kill for incomplete full window/account stop-out, trades <170 or >580, PF <1.15, expectancy <=0, DD >6.5%, top-three >30% of total net profit, or margin >10%. No control/OOS/holdout/tuning until pass.
