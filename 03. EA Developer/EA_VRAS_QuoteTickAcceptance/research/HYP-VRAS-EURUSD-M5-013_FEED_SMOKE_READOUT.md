# HYP-VRAS-EURUSD-M5-013 feed-smoke readout

## Verdict

`PARK_DUPLICATE_NORMALIZED_TICK_COORDINATE_NO_EA_OUTCOME`

HYP-013 passed its engineering tests, compile 0 errors / 0 warnings,
exact-source non-repaint and zero-order static audit. Its sole authorized
120-second read-only feed smoke matched `FivePercentOnline-Real`, inferred the
broker clock offset as +10,800 seconds and wrote UTC-normalized timestamps.

The capture is invalid for research. It contains 240 quote rows but only 66
unique `time_msc` values; 174 rows repeat a prior timestamp. The collector
compared raw broker milliseconds with the normalized UTC cursor before writing
the current quote. Because raw time was three hours ahead, the predicate stayed
true even when the quote had not changed. The strict validator therefore stops
at CSV row 3 with `quote_ticks row 3 is not strictly monotonic`.

Safety remained intact: 240 heartbeats, zero orders, zero positions, account
history skipped and `live_trading_authorized=false`. No EA was attached, so no
arm, acceptance, trade, PnL, return or economic result exists.

## Evidence

- Capture: `20260723_VRAS013_UTC_FEED_SMOKE_001`.
- Manifest SHA256: `5C711B8815C9BC90E3508FBEBB0EAFEB8FD4E4CA6AC86E8D98388D983E156C1F`.
- Quote CSV SHA256: `1F2C6440CB1282F354AD61A3F5837F0064C375AB8E6ED4CB33E57209042FCA46`.
- Session-end SHA256: `FB1048F2958C974FE7BC43DDFFB40F3BF460E6DCAEBEF01A35AADC23ED77EA84`.
- Failure receipt: `research/evidence/HYP-VRAS-EURUSD-M5-013_ENGINEERING/feed_smoke_validation_error.json`.

## Boundary

HYP-013 is terminal and may not be rerun. A fresh administrative successor may
change only the timestamp-coordinate comparison: normalize first, then compare
against the normalized last-seen cursor; all signal and acceptance thresholds
remain frozen.
