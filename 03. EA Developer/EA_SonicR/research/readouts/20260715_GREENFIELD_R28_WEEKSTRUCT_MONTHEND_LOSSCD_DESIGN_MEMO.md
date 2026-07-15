# Design — Round 28 Week-struct / Month-end / Loss-CD

Date: 2026-07-15
Freeze: `20260715_GREENFIELD_R28_WEEKSTRUCT_MONTHEND_LOSSCD_UNIVERSE_FREEZE.md` sha=70BC7D16A56CB86B…

## 1 `HYP-FX3-H1-PRIOR-WEEK-HL-BREAK-CONT-001`
First H1 close beyond prior completed ISO-week high/low + body≥0.35×ATR → CONT. First break per week per side.
Why: calendar-week structure ≠ R16 D1 HL; ≠ R23 fractal5; ≠ Donch; ≠ weekly-open fade.

## 2 `HYP-EURUSD-H1-MONTHEND-REBAL-CONT-001`
DOM≥28 or DOM≤2 + body≥0.4×ATR → CONT.
Why: month-end rebalancing flow ≠ NFP same-day; ≠ CPI; ≠ FRED displace; ≠ session pack.

## 3 `HYP-FX3-H1-LOSS-COOLDOWN-ARCH-CONT-001`
Body≥0.4×ATR CONT + per-symbol cooldown 24 bars after losing exit.
Why: execution/inventory architecture ≠ RS-rank; ≠ risksync; ≠ session MaxKZ densify.
