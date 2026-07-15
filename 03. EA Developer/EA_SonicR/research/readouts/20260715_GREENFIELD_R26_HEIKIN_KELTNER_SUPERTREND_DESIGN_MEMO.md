# Design — Round 26 Heikin / Keltner / Supertrend

Date: 2026-07-15
Freeze: `20260715_GREENFIELD_R26_HEIKIN_KELTNER_SUPERTREND_UNIVERSE_FREEZE.md` sha=7E3A4DE650EB83A2…

## 1 `HYP-FX3-H1-HEIKIN-STREAK-CONT-001`
3 closed HA same-color + real |body|≥0.35×ATR → CONT.
Why: HA filter ≠ R15 raw streak; ≠ three-bar reverse; ≠ H4-engulf.

## 2 `HYP-EURUSD-H1-KELTNER-WALK-CONT-001`
2 closes outside EMA20±1.5×ATR + body → CONT.
Why: channel walk ≠ Donch8; ≠ RangeP80 expand; ≠ ATR-exp%.

## 3 `HYP-USDJPY-H1-SUPERTREND-FLIP-CONT-001`
Supertrend(10,3.0) flip + body≥0.35×ATR → CONT.
Why: ATR-trail flip ≠ Kaufman ER; ≠ lag1-AC; ≠ MTF align.
