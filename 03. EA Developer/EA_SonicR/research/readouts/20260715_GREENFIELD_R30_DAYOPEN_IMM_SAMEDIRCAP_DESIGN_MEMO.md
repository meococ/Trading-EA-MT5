# Design — Round 30 Day-Open / IMM / SameDir-Cap2

Date: 2026-07-15
Freeze: `20260715_GREENFIELD_R30_DAYOPEN_IMM_SAMEDIRCAP_UNIVERSE_FREEZE.md` sha=562C452F380A3303…

## 1 `HYP-FX3-H1-PRIOR-DAY-OPEN-BREAK-CONT-001`
Close crosses prior UTC calendar-day OPEN + body≥0.35×ATR → CONT.
Why: day-open level ≠ R16/R28 HL breaks; ≠ equal-HL; ≠ Donch.

## 2 `HYP-EURUSD-H1-IMM-WEDNESDAY-CONT-001`
IMM Wed (3rd Wed Mar/Jun/Sep/Dec) + body≥0.4×ATR → CONT.
Why: FX futures roll ≠ R29 OPEX Friday; ≠ R28 month-end; ≠ FRED/CPI.

## 3 `HYP-FX3-H1-SAMEDIR-CAP2-ARCH-CONT-001`
|body|≥0.4×ATR CONT; hard cap ≤2 concurrent same-direction.
Why: correlation exposure architecture ≠ R29 oneslot; ≠ R28 losscd; ≠ RS-rank.
