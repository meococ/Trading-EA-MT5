# HYP-RSF-EURUSD-M5-VISUAL-005 — Native Screenshot Readback Smoke

Status: `PREREGISTERED_DIAGNOSTIC_ONLY`

## Purpose and one bounded engineering delta

VISUAL-004 proved that `ChartScreenShot=true` is only queue acceptance and is not
proof that an image exists. It also exposed a missing QQE histogram and excessive TB
zone retention. VISUAL-005 is a two-day engineering smoke, not a strategy test.

The frozen delta is limited to presentation and evidence integrity:

1. QQE explicitly declares three runtime color indexes without changing public
   buffer numbers or calculations.
2. The display-only TB handle keeps one cell and one void; the parent decision handle
   remains untouched.
3. Screenshot telemetry reports success only after `FileIsExist` plus positive
   `FileSize`; queue result, MQL error, verification ticks and timeout are separate.
4. One scheduled display-only screenshot probe is queued at server time
   `2019.06.04 09:55`. It cannot submit, alter or close a trade.

## Frozen execution

- EA: `EA_RegimeStructureFusionForensics`
- symbol/timeframe: `EURUSD M5`
- interval: `2019.06.03` through `2019.06.05`
- Model 0, no artificial delay, current spread
- deposit/leverage: `100000 USD`, `1:100`
- Visual Mode required
- parent Cell-16 masks and decision engines unchanged
- smoke timestamp: `1559642100` (`2019.06.04 09:55` server-chart value)
- screenshot settle: 250 ms; verification timeout: 20 tester ticks

## Acceptance and stop rule

Engineering pass requires all of the following:

- compile with zero errors;
- one VisualShots SMOKE row with `request_ok=1`, `file_verified=1`,
  `screenshot_ok=1`, and `file_size_bytes>0`;
- the referenced PNG exists in the collected run artifacts and is hashable;
- direct native MT5 inspection shows QQE histogram columns and at most one active
  TB cell plus one active void; chart price must remain legible;
- no indicator alert storm.

If the queue remains accepted but the file cannot be read back, this ID is killed and
AlphaFactory must use an external capture of the actual MT5 window with event-bound
metadata. No Python price rendering or synthetic chart may substitute for it.

This diagnostic cannot authorize economic claims, parameter selection, validation /
holdout access, or promotion.
