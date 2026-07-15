# De-dup clearance — Keltner Squeeze vs VolExp / Chop

Date: 2026-07-14  
Verdict: `INTAKE_CLEARED / INDEPENDENT`  
Hypothesis: `HYP-KELTNER-SQUEEZE-M15-001`

## Question

Is BB-inside-KC squeeze breakout a twin of killed VolExp / ChopTrend?

## Comparison

| Family | Mechanism | Verdict |
|---|---|---|
| VolExp / VolCluster (KILL) | Realized vol ratio / GARCH expansion | **Different: BB/KC geometry, not RV** |
| ChopTrend (FAIL_CLOSED) | CI + EMA cross | **No CI; squeeze release ≠ EMA cross** |
| HourOpen / London ORB | Session/clock range break | **No opening-range construct** |
| Spark / InsideBar / TickVol / GoldJPY | Other price families | **Independent** |
| ITSM / SB / USBILL | Pullback / FVG / exogenous | **Independent** |

## Seed

S654 baseline PF 1.15 Mon+Wed+Thu Europe — not S655 Mon+Thu skip-Wed
robustness-killed densify. Freeze S654 day set a priori.

## Clearance

`INTAKE_CLEARED / INDEPENDENT`. Authorize Model 0 screen. Do not rescue via
S655 skip-Wed or CI twin.
