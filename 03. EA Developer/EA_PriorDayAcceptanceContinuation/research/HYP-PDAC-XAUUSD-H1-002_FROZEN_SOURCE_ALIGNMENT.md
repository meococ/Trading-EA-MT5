# HYP-PDAC-XAUUSD-H1-002 — frozen pre-outcome source alignment

Status: `FROZEN_BEFORE_PD002_SOURCE_DERIVATION_OR_MT5`

Parent `HYP-PDAC-XAUUSD-H1-001` is parked pre-MT5 for a source/execution
population mismatch; no economic outcome exists.

HYP002 inherits every parent source event byte-for-byte from ledger SHA256
`D17738ED6BAA478A8B2F7BF1788EAAB36B726C93D1AA7BB1DE48FF74BD67045F`.
It changes no price condition. One event is executable only when its exact next
H1 availability time is not Friday at or after 20:00 UTC. Server time converts
to UTC with FivePercent winter UTC+2 and Europe-DST UTC+3 (last Sunday March at
03:00 server through last Sunday October at 04:00 server).

The frozen source gates remain: at least 500 events, cadence 2–5/week, each
direction at least 30%, no year above 30%, each year 1.25–6.5/week, and inherited
exact-next coverage at least 97%. No outcome fields may be opened.
