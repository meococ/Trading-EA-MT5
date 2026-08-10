# HYP-MFI-XAUUSD-M5-001 — Independent Post-failure Review

Date: 2026-08-09  
Reviewer: read-only sub-agent `t2_campaign_audit`  
Verdict: `PASS_PARK`

No post-event OHLC, performance, validation or holdout data was accessed.

## Integrity and arithmetic

- Start `BB64FC55…CF74F`
- Report `B3460792…D42FA`
- Ledger `DBAAAD3D…64A85`
- Receipt `CA415F81…8F475`
- Terminal `7B4C5312…0B88F`

The terminal binds the source receipt; the receipt binds preregistration `F89BE9…D57295`, analyzer `FEEB94…DC2E`, source declarations, exact pre-run registry snapshot, report and ledger.

Independent ledger audit found 6,262 unique ordered crossings with zero crossing, timestamp or schema violations: 2,877 LONG and 3,385 SHORT. Pooled cadence is 24.0055/week, above the maximum 5. Each year produces 22.745–25.008/week, above the maximum 6.5. Direction balance and maximum-year share 20.824% pass.

`PARK_SOURCE_FEASIBILITY_EXACT_MFI_REENTRY` is mandatory. It is an over-frequency verdict for the exact one-step MFI14 re-entry mapping, not economic no-edge.

## Legal successor

`HYP-MFI-XAUUSD-M5-002` may implement TradingView's documented four-step MFI failure swing because MFI001 explicitly excluded it before results. It is a new oscillator path/state object, not a cooldown or threshold rescue.

Bullish FSM:

1. arm on completed `MFI <= 20`;
2. first `MFI > 20` enters ADVANCE and tracks its maximum;
3. first strict decline that remains above 20 freezes that maximum as trigger and enters PULLBACK;
4. first later completed `MFI > trigger` emits LONG.

Bearish FSM is exact inverse using `MFI >= 80`, re-entry below 80, tracked minimum, first strict rise below 80 and subsequent strict break below the frozen minimum for SHORT.

Invalid MFI resets. Returning to the extreme restarts that side. After an event both sides reset and require a fresh extreme. Simultaneous events reject. No timeout, cooldown, debounce, price/session filter or outcome is permitted.

