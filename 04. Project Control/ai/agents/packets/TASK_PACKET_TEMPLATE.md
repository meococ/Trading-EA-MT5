# Task Packet Template

Copy to `TASK_PACKET_<YYYYMMDD>_<topic>.md`. English. Immutable once workers start.

## Header

- `packet_id`:
- `hypothesis_id`:
- `role_assigned`: red-team | research | impl | qc
- `model`: `cursor-grok-4.5-high-fast`
- `mode`: readonly | write
- `created_by`: coordinator
- `created_at`:

## Scope

- Objective (one sentence):
- In-scope paths:
- Out-of-scope:
- Decision surface (impl only — exactly one):

## Bound inputs (hashes when available)

- prereg:
- registry row:
- prior evidence:
- compile/run receipts:

## Stop rules

- Stop if:
- Do not:

## Required out receipt fields

`verdict`, `evidence_paths[]`, `blockers[]`, `confidence`
