# HYP-KVO-EURUSD-M15-004 — Source-to-spec review

Functional delta from the frozen HYP003 source is limited to fresh identity/magic, exact MARKET_CLOSED no-fill classification, and removal of routine journal prints. Signal, indicator, sizing, risk and exit expressions are unchanged.

Safety invariant: an entry response is nonfatal only when retcode is exact MARKET_CLOSED, result order/deal are zero, and immediate owned position/order enumerations both succeed with count zero. Unknown transport/result states fail closed.

Evidence invariant: INIT/D0/preload/fatal/summary remain; high-volume SIGNAL/ENTRY/nonfatal rejection rows are absent. The explicit 32 MiB cap is a receipt-level evidence bound, not an EA parameter. Its conservative calculation covers all 9,524 raw-signal attempts plus the calendar-day maximum accepted entry/exit lifecycle across both journal sources; it does not use HYP003's post-fatal broker-attempt count.
