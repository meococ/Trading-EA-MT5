# HYP-KVO-EURUSD-M15-003 — Source-to-spec review

## Frozen change from HYP-KVO-EURUSD-M15-002

The source preserves Klinger VF/CM/EMA calculations, the long/short FSM, exact-next scheduling, ATR/swing stop, 1.50R target, 16-bar exit, one accepted trade/day, 0.25% risk and the 2010–2017 TRAIN window.

Only these functional changes are authorized:

1. Fresh identity: HYP003, magic 5604003, variant `REJECTSAFE`.
2. `OrderSend=false`, timeout/unknown retcodes or nonzero result order/deal tickets are fatal.
3. Only exact `TRADE_RETCODE_MARKET_CLOSED` with zero result tickets proceeds to an immediate owned-position/order scan.
4. Treat that event as a nonfatal consumed rejection only when both enumeration calls succeed and both counts equal zero; otherwise emit fatal `ENTRY_REJECT_AMBIGUOUS`.
5. AlphaFactory report-ready cleanup may release a stale/reused PID ownership claim without stopping the replacement. Timeout and pre-report cleanup remain strict.

No outcome from HYP002 was accepted or used to select a parameter, filter, direction, session, stop, target or holding rule.

Focused regression result before compile: `12 passed`.
