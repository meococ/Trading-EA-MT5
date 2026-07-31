# HYP-VRAS-EURUSD-M5-009 — Preflight Failure Readout

Verdict: `PARK_PRECOUNT_CONTRACT_INTERNAL_CONTRADICTION_NO_OUTCOME_READ`

The exact SHA-bound decision telemetry contains fixed decision-time
`entry/stop/target` columns, while the V2 amendment also required rejecting any
schema containing stop/target. The parity gate was therefore impossible.
Registry validation correctly rejected a proposed V3 amendment because HYP009
had already transitioned to `probe`.

No real Stage-0 probe was run. No event count, cadence, overlap, P/L, forward
return, excursion, MQL5 source or Model-0 result was opened. The untested
mechanism is transferred to HYP010 under one consolidated frozen contract.
