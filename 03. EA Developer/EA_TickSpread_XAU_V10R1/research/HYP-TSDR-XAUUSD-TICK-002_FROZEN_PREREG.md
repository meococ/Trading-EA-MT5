# Frozen preregistration - HYP-TSDR-XAUUSD-TICK-002 P0

Freeze: 2026-08-12. Authority: `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`.

Fresh runtime repair of `HYP-TSDR-XAUUSD-TICK-001`. The first identity was rejected because its D0 proof field names did not match the canonical AlphaFactory parser. This identity changes only the hypothesis/EA/log prefix, magic number, and D0 proof schema. Tick measurement, date boundary, histogram, counters, and all gates are unchanged.

Run XAUUSD M1 from `2018.01.01` to `2018.01.10`, current spread, Model 0. Collect the first five broker dates and freeze at the first valid tick of the next broker date. P0 cannot trade and cannot authorize economics.

PASS requires invalid quotes <= 0.30%, decreasing `time_msc` <= 0.10%, equal `time_msc` <= 15.00%, median raw spread in [0.05, 3.00], long constant-spread-run ticks <= 40.00%, five broker dates, and at least one distribution tick. Any failure is `DATA_FRONTIER_BLOCKED`. No gate may be changed after the run.

