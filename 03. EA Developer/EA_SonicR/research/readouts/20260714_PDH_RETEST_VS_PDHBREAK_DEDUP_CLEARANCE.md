# De-dup — PDH Retest vs PDH Break / LiqSweep / ORB

Date: 2026-07-14  
Verdict: `INTAKE_CLEARED / INDEPENDENT`

| Comparator | Mechanism | Why independent |
|---|---|---|
| `HYP-PDH-BREAK-M15-001` PARK | Immediate M15 close beyond PDH/PDL | Retest requires **later** bar touch+reject after break arm |
| LiqSweep / PDLevel fade KILL | Fade after sweep of PDH/PDL | Continuation after acceptance, not fade |
| LondonORB / FailedORB | Session opening range | D1 prior-day levels, not OR |
| H1-BOS / H4-struct | HTF swing BOS | Daily PDH/PDL object |

Not a parameter retune of PDH-BREAK. New ID required and used.
