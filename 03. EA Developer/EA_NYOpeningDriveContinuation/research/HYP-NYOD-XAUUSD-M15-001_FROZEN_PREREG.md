# HYP-NYOD-XAUUSD-M15-001 — Frozen preregistration

Status: FROZEN BEFORE COMPILE OR OUTCOME READ

## Market thesis

At the New York metals-liquidity handoff, a completed 08:15–08:30 New York
M15 bar that expands beyond recent volatility and closes through the preceding
two-hour range represents directional price discovery rather than a failed
auction. Continuation should persist long enough to support a short intraday
scalp after realistic FivePercent costs.

This is an event-anchored continuation mechanism. It is materially different
from terminal COMEX/fix reversion, VWAP fade, sweep/reclaim, generic indicator
crosses, and the closed ATR impulse-pullback family.

## Frozen mapping

- Symbol/timeframe: native FivePercent `XAUUSD`, `M15`.
- Design baseline window: `[2018-01-01, 2023-01-01)`; validation and later data
  remain unopened for strategy selection.
- Decision bar: completed New York-local 08:15 M15 bar; entry may occur only on
  the exact 08:30 next-bar open.
- Broker clock: FivePercent server winter UTC+2 / Europe-DST UTC+3; New York DST
  uses the US second-Sunday-March / first-Sunday-November rules.
- Reference volatility: native ATR14 at shift 2, ending before the drive bar.
- Prior range: strict max high/min low of the eight completed M15 bars before
  the drive bar.
- Common drive gate: true range >= 1.00 prior ATR and body/range >= 0.60.
- LONG: bullish drive, close-location >= 0.75, close strictly above prior range.
- SHORT: exact inverse below prior range.
- Maximum one consumed signal per New York calendar date; no direction/session
  filter beyond this atomic event definition.
- Entry: market on the first tick of the exact next M15 bar.
- Initial stop: opposite drive extreme plus 0.15 prior ATR buffer.
- Target: 1.50R from actual requested entry; no break-even or trailing.
- Time exit: first tick after six completed M15 bars (90 minutes).
- Risk: 0.25% equity by `OrderCalcProfit`; one symbol position, no pyramid.
- Daily/account locks: 3.5% / 8%; Friday no-new-entry and flatten from 20:00 UTC.
- Missing bars, invalid prices/ATR, non-exact clock, invalid stop/margin/volume or
  foreign exposure fail closed.

## Baseline contract

One untuned Model-0 run through `02. AlphaFactory/alpha.ps1` only. Report costs
must include broker spread and commission. No optimization, direction removal,
clock shift, threshold search, alternative exit, or post-read filter is allowed
under this ID.

Minimum economic gates before validation:

- PF > 1.30 after x1 cost;
- 2–5 completed trades per elapsed calendar week;
- x1.5 PF >= 1.25 and x2 PF >= 1.00;
- both directions >=30%, no calendar year >30% of trades;
- positive expectancy after cost and max relative DD <=8%.

Any implementation defect may be corrected without changing this market
mapping. Any logic or parameter change after outcomes requires a fresh ID.
