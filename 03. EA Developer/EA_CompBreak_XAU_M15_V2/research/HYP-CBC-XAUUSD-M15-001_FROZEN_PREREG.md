# Frozen prereg — HYP-CBC-XAUUSD-M15-001

Status: FROZEN before compile and outcome-bearing execution on 2026-08-12.

Origin: Grok `/deep-research-trading-meta5` loop 2 after `HYP-CBWR-XAUUSD-M15-003` was killed. This is a materially new stateful continuation object, not a revision of wick rejection.

## Market object

- Primary: XAUUSD M15, Model 0, design window `[2018-01-01, 2022-01-01)`.
- All decisions use completed M15 bars. Entry is the first available tick of the next bar.
- No indicator dependency beyond native ATR(14); no external data, future pivot, grid, martingale, averaging or fixed TP.

## Frozen signal and state

1. Idle: compute the candidate compression box from shifts `[2..8]`, exactly seven completed bars.
2. Compression exists only if `box range <= 1.15 * ATR14[1]` and every box bar has `abs(close-open)/(high-low) <= 0.55`.
3. Freeze `BoxHigh`, `BoxLow`, detect time and ATR. The detection bar is shift `[1]`, is outside the box, and is allowed to break it.
4. Bull break: `Close[1] > BoxHigh + 0.10*ATR14[1]`; bear break is symmetric. Break bar body ratio must be `>=0.50`.
5. A frozen box expires after the ninth evaluated closed bar including its detection bar. No rolling/recomputed box while active.
6. Primary variant is `COMP7_PRIMARY`. Locked matched control is `BODY50_CONTROL`: every body-ratio `>=0.50` bar enters in its body direction with the same downstream management and a fixed `1.80 ATR` initial stop.

## Frozen execution and exits

- One XAUUSD position maximum. No reversal while exposed.
- Live spread at entry must be `<=48` points; otherwise the break is cancelled.
- Initial primary stop is beyond the opposite box edge by `0.20 ATR`, clamped to `[1.30,2.60] ATR` from actual entry.
- No hard take profit. At `+1.10R`, stop moves to `entry +0.15R` in the trade direction. At `+1.80R`, the trail arms; on each subsequent closed M15 bar it can tighten to `Close[1] +/- 0.90 ATR14[1]`. Stops never loosen.
- Hard time stop: 16 M15 bars. Daily flat 21:45 server; Friday flat 19:30 server; no weekend entry.

## Frozen risk

- Risk candidate: `0.45%` equity divided by one-lot stop loss.
- Notional candidate: `(4.50 * equity)/(entry * contract size)`.
- Margin candidate: `(0.12 * free margin)/(required margin per lot)`.
- Final volume is normalized downward from the minimum of all three. The actual order must again satisfy notional `<=4.50*equity` and required margin `<=12%` of pre-entry free margin.
- Entry locks: daily loss `1.20%`, weekly loss `3.00%`; after four consecutive losing exits, no new entry for eight hours.

## Telemetry and economics gate

Log every compression, expiry, break, entry cap, stop change and exit, including box, ATR, age, margin usage, notional/equity, MAE/MFE and bars held.

Immediate design kill if runtime/data invalid, no valid trades, design PF `<1.00`, expectancy `<=0`, maximum DD `>9%`, margin stop-out, or final cadence cannot plausibly reach 180 trades over 2018-latest. Advance to the locked matched control and OOS only if design PF `>=1.15`, expectancy positive, DD `<=9%`, counts reconcile, no margin failure and cadence is sufficient. Goal-level promotion thresholds are stricter and are not decided by this baseline.

No optimization, session/direction filtering, OOS readout, matched control, cross-symbol transfer or live action is authorized until the primary design baseline passes its advance gate.
