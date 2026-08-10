# HYP-MFI-XAUUSD-M5-002 — Source Feasibility Result

Date: 2026-08-09  
Attempt: `MFI002-SOURCE-ATTEMPT-001`  
Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_MFI_FAILURE_SWING`

The sole four-step outcome-blind scan completed with byte-identical replay.

| Gate | Result | Pass |
|---|---:|:---:|
| Design rows | 351,303 | yes |
| Feature coverage | 99.9007% | yes |
| Raw-event exact-next coverage | 99.8733% | yes |
| Raw / executable / gap-rejected | 4,736 / 4,730 / 6 | yes |
| Pooled cadence | 18.13253/week (required 2–5) | no |
| LONG / SHORT | 2,198 / 2,532; 46.47% / 53.53% | yes |
| Maximum year share | 20.613% | yes |
| Every-year cadence | 17.260–18.699/week (required 1.25–6.5) | no |

The documented four-step oscillator path remains far too frequent on XAUUSD M5. Do not add a timeout, magnitude, cooldown, session or price filter, and do not rerun/build/open outcomes under this ID.

Failure radius is only the exact MFI14 20/80 EXTREME→ADVANCE→PULLBACK→trigger-break FSM on 2018–2022. No economic edge was evaluated.

