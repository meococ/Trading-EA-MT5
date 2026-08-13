# HYP-MULTI-TSMOM-D1-004-SWAP-SCHEDULE-PROBE-001 — frozen source probe

Authority: current broker specification only. No orders, performance metrics or
strategy economics are authorized.

The preceding contract probe captured swap mode and long/short values, but not
the seven independent `SYMBOL_SWAP_*DAY` coefficients. Those fields are needed
to distinguish single, zero and triple-charge days and to annualize mode 1 and
mode 4 without guessing. This probe emits mode, long/short swap, rollover3 and
Sunday through Saturday coefficients for the same nine native FivePercent
symbols. It also emits the AlphaFactory D0 M1/M5 series proof for EURUSD.

Frozen run: EURUSD H1, MT5 Model 0, `[2026-08-03,2026-08-05)`, deposit USD
100,000, leverage 1:100, no overrides and no visual mode. The output can close a
current-contract financing formula only; it is not historical PIT swap proof.
