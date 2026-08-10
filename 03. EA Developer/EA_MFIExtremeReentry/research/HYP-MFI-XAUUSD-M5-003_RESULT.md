# HYP-MFI-XAUUSD-M5-003 — Source-feasibility Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_MFI_JOINT_DIVERGENCE`

The sole outcome-blind attempt completed with deterministic replay and durable evidence. From 351,303 design rows, 327,726 confirmation rows were usable (`93.2935%`), below the frozen `99%` gate. The exact mapping produced 4,508 raw and 4,500 executable events (`2,205 LONG`, `2,295 SHORT`) at `17.2508/week`, above the frozen `5/week` maximum. Eight raw events lacked an exact next M5 timestamp. Each calendar year was `16.5507–17.7205/week`, also above its maximum.

Minimum rows/events, exact-next coverage, direction balance, year concentration and zero-conflict gates passed. No post-event OHLC, return, trade, cost or PF was computed. This result says only that exact strict N=2 joint price–MFI14 divergence is over-frequent and has insufficient continuous-window coverage on this XAUUSD M5 source; it makes no economic no-edge claim.

Same-ID retry, pivot-radius/threshold rescue, MQL5 build, economics, validation, holdout, paper and live use remain unauthorized.
