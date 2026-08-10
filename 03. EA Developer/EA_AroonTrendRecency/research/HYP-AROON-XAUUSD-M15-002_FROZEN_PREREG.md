# HYP-AROON-XAUUSD-M15-002 — Frozen Vectorized Source Revision

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Parent: terminal `HYP-AROON-XAUUSD-M15-001`, raw terminal-row SHA256 `1B13776D3436F2C192B85EF5B3968323632D0E08A3CC841736B3E9EF198665F3`.

Informing evidence: AROON001 was externally terminated after approximately 124 seconds before any report. It produced no source-gate or economic result. This revision changes only aggregation throughput and adds phase checkpoints; it is not a signal, parameter, filter, timeframe, source or acceptance rescue.

## Frozen mechanism

All semantic rules are inherited unchanged from the reviewed HYP001 formula contract at analyzer SHA256 `6E2383CE15074890905AFC6AAF2E6D0D9893FBDE8B414850F28F12A08F100CF0` and preregistration SHA256 `D2D3C8F358D4D77FCC6D6838D7F7315423E6A1473202E2AF0623AE5763BA85F8`:

- FivePercent XAUUSD M5 source SHA256 `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`;
- read exact inception through `<2023`, score `[2018,2023)`;
- M15 buckets are only observed `floor(source_epoch/900)*900` keys;
- complete iff exactly three unique rows at offsets 0/300/600, exact UTC +5m/+10m from offset zero, all prices finite and geometrically valid;
- incomplete observed buckets remain invalid; absent market-closure buckets are never synthesized;
- Aroon-25 uses 26 buckets, most-recent equal high/low, denominator 25;
- current/prior crossover requires `t-26..t`; first event index 26;
- LONG prior Up<=Down/current Up>Down; SHORT inverse;
- exact immediate next M15 timestamp and source epoch only; raw gap events are consumed;
- no thresholds, filters, cooldown, outcomes or optimization;
- gates remain rows>=100000, feature>=99%, exact-next>=97%, N>=500, pooled 2–5/week, each direction>=30%, max year<=30%, each year 1.25–6.50/week, zero conflicts.

## Sole implementation change

Replace the Python row-by-row group iteration with vectorized group transforms/aggregation. The vectorized result must be byte-semantically equal to the frozen legacy aggregator on bounded fixtures. It may not resample, reindex, synthesize, delete, fill, interpolate or reorder bucket keys.

Durable phase checkpoints may record only phase name, timestamp, row counts and frozen hashes. They may not contain price, event or outcome data. Required phases are claim, hash/schema verified, source read, aggregation complete, analysis complete and terminal.

Sole attempt: `AROON002-SOURCE-ATTEMPT-001`. Same-ID retry is forbidden.

All source/cadence gates must pass for a direct-MQL5 correctness child to open. Any failure parks the exact Aroon mapping. Timeout/error before report is engineering evidence only. No MQL5, MT5, economics, validation, holdout, promotion, paper or live authority exists here.

Primary formula reference: https://www.tradingview.com/blog/en/what-s-new-in-pine-23841/
