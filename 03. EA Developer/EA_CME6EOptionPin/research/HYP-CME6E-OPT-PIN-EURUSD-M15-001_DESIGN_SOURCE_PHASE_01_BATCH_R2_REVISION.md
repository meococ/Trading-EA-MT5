# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - phase-01 batch R2

Batch R1 was rejected locally before any HTTP batch submission because the
pinned Databento SDK 0.55.1 accepts `day`, `week`, `month`, or `none`, not the
newer documented `year` split duration.  The R1 receipt records zero batch,
timeseries, and paid payload calls.

R2 changes only `split_duration` from `year` to `month` and uses a new exclusive
artifact root.  The exact parent list, schema, period, symbology, encoding,
compression, quote/budget gates, one-submit limit, and every source/economic
boundary remain unchanged.

