# HYP-VRAS-EURUSD-M5-010 — Preflight Failure Readout

Verdict: `PARK_PRECOUNT_CONTRACT_PATH_AND_IMPLEMENTATION_MISMATCH_NO_OUTCOME_READ`

An independent read-only reviewer found the frozen telemetry path omitted the
actual producer suffix (`_188132734`), while the implementation performed an
unfrozen wildcard lookup. The same preflight also found full-row materializing
wording/implementation drift, insufficient non-finite parity rejection,
unfrozen second-bearing timestamp semantics and stale HYP009 output schema
identifiers. The core FSM ordering and comparator no-lookahead were accepted.

No real Stage-0 probe was run. No event count, cadence, overlap, P/L, forward
return, excursion, MQL5 source or Model-0 result was opened. The still-untested
mechanism may proceed only under a new consolidated contract with the exact
telemetry filename and corrected fail-closed semantics.
