# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004 — partial result

Verdict: `ENGINEERING_PARTIAL_NO_RETRY`; no source-census or economic verdict.

The host/tool process ended after 344.4 seconds. At the last atomic manifest:

- 264 calls had been marked attempted;
- 256 completed with hash-bound raw and analysis artifacts;
- 8 were `IN_FLIGHT` and are permanently ambiguous/no-retry;
- 63 were still `UNATTEMPTED`;
- no Python-level `FAILED_NO_RETRY` entry was recorded.

The 256 complete artifacts contain 1,562,391 source records and 44,553,936 compressed
raw bytes. 255/256 passed semantics; `EVT0250` is source-invalid. The outcome-blind
effective distribution is 121 continuation / 134 reversal and 131 long / 124 short.
This is balanced but cannot pass the original 327/327-complete gate.

The eight ambiguous event IDs (`EVT0258`, `EVT0260`–`EVT0266`) must never be retried
or used from partial files. A child may acquire only the exact 63 unattempted identities
and combine them with the 256 completed receipts while freezing ambiguous/unavailable
identities as FLAT. No outcome or economic field has been opened.

