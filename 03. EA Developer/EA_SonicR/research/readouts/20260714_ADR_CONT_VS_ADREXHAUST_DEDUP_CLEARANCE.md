# De-dup clearance — HYP-ADR-CONT-M15-001

Date: 2026-07-14  
Verdict: **PASS_INDEPENDENT**

## Mechanism

When today's range already reaches `ADR(14)` (closed D1 lookback), a closed M15 bar near the day's extreme **continues** expansion (long at day-high band / short at day-low band) with body + D1 EMA50. Opposite of ADRExhaust mean-reversion (S680/S681).

## Not a twin of

| ID / shelf | Why independent |
|---|---|
| ADRExhaust S680/S681 | Same ADR trigger family, **opposite trade side** (fade killed; S681 notes continuation favored) |
| PDH-Break | Prior-day levels, not ADR% of today |
| LondonORB / NYOpenDrive / FailedORB | Session ORB constructions |
| EMAStretchFade | EMA distance MR, no ADR |
| ITSM / SB / Spark / USBILL / Keltner | Different families |

## Cadence path

Max 1/day Mon–Thu → ≤4/elapsed wk structural.

## Banned after readout

No ADR thresh / extreme% / day / hour mining; no flip back to fade.
