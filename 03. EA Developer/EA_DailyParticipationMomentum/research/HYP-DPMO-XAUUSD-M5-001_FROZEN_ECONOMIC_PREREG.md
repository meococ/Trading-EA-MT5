# HYP-DPMO-XAUUSD-M5-001 — frozen untuned economic baseline

Status: FROZEN BEFORE MQL5 COMPILE OR OUTCOME READ

## Market thesis and signal

The signal is exactly the source-passed daily participation-momentum mapping:
on a complete native M5 UTC session `00:00..15:55`, continue the sign of the
session close-to-close return only when the session's total broker tick
activity is strictly above the ordinary median of the prior 20 complete
sessions. The current session is excluded from the median. Tick volume is an
activity proxy, not true traded volume or order flow.

Source evidence is `DPMO-SOURCE-001`; report SHA256
`24863FC3447C215B537C225EFAA1278BBE9035855F8BDF7CCC6EEF904AEF5934` and
receipt SHA256
`17529FBE5383AAD1D377579BF88B45AD4269375D1D4DD99DD7C4E767C8F050BC`.

## Frozen execution mapping

- FivePercent `XAUUSD`, native `M5`, DESIGN `[2018-01-01, 2023-01-01)`.
- Decision: completed `15:55 UTC` bar; entry may occur only on the first tick
  of the exact `16:00 UTC` next M5 bar.
- Session completeness: exactly 192 positive-volume, geometrically valid,
  contiguous native bars `00:00,00:05,...,15:55 UTC`.
- Structural stop: LONG uses the minimum low of the 12 completed M5 bars ending
  at 15:55 minus `0.20 * ATR14`; SHORT uses the corresponding maximum high plus
  the buffer. ATR14 is the native closed-bar value at shift 1 when 16:00 opens.
- Stop is normalized outward to symbol tick size. Invalid/wrong-side/broker
  stop-level geometry emits no order and is not retried.
- Target: fixed `1.50R` from the requested market entry after stop
  normalization. No trailing stop, break-even, partial exit or scale-in.
- Time/session exit: close on the first tick at or after `20:00 UTC` the same
  day, equivalent to 48 completed M5 bars if neither SL nor TP has fired.
- Risk: `0.10%` current equity per requested trade, sized down to broker volume
  step with `OrderCalcProfit`; one owned symbol position, no pyramid.
- Daily/account entry locks: `3.5% / 8.0%`; Friday entries remain eligible at
  the same fixed 16:00 decision clock, and all owned exposure is flattened from
  `20:00 UTC` every day, so no weekend hold is permitted. Missing data, price, ATR, margin,
  position ambiguity or trade rejection fails closed.
- Broker clock: FivePercent server UTC+2 in winter and Europe-DST UTC+3.

## Sole baseline contract

Exactly one untuned Model-0 AlphaFactory run:

- EA `EA_DailyParticipationMomentum`; `XAUUSD/M5`;
- tester window `2018.01.01..2023.01.01`, deposit `100000`, leverage `100`,
  current broker spread and report commission;
- no optimization, clock/session shift, direction deletion, alternate
  activity threshold/lookback, stop/target/hold/risk search or post-read filter.

Minimum gates before opening validation:

- report history quality `>97%`;
- PF `>1.30` and expectancy `>0` after the captured x1 spread/commission cost;
- `2–5` completed trades per `1826/7` elapsed calendar weeks;
- both directions at least `30%`, no calendar year above `30%` of trades;
- maximum relative equity drawdown `<=8%`;
- later cost replay x1.5 PF `>=1.25`, x2 PF `>=1.00`.

Compile/runtime/signal mismatch is an engineering failure, not an economic
verdict. If the verified baseline fails PF, expectancy or cadence, this exact
object is terminal; any economic logic change requires a fresh hypothesis ID.
Validation, holdout, optimization, paper and live remain closed until all
baseline gates pass.
