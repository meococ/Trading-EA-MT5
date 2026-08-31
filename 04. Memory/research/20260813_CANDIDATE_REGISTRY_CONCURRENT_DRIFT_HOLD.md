# Candidate registry concurrent-drift hold

Date: 2026-08-13 (Asia/Saigon)

## Verdict

`HOLD_LINEAGE_AUDIT_REGISTRY_IDENTITY_DRIFT`

This is a read-only integrity receipt. It does not mutate the registry, lineage
override or any hypothesis state.

## Trigger

The earlier lineage audit was bound to a 978-row registry identity and an
explicit receipt-bound T2 edge. During final validation of the separate Grok
SonicR recovery work, the real-binding test failed closed because the current
registry SHA no longer matched the override.

One validation read observed transient SHA256
`A97A345EE8BE8EC2748C6AC559AB51F6FD34A481663AF8D40B91DAA0BBEA6E85`.
A subsequent stable two-read snapshot was:

- rows: `469`;
- bytes: `2251259`;
- SHA256:
  `6B23F356FDAE8402DA62056206BAA9328FC53C13C4CAE1371A1A2396F2CBE039`;
- last write UTC: `2026-08-13T15:04:37.1343448Z`.

The last registry row is historical object `HYP-VRAS-USDJPY-M5-003`, with
`updated_at_utc=2026-08-02T16:15:00Z` and terminal verdict
`KILL_PRIMARY_MODEL0_ZERO_EDGE_AND_CADENCE_TELEMETRY_CONTRACT_FAIL`. The
combination of a fresh filesystem write time, smaller row set and older logical
tail is consistent with a concurrent replacement/restoration, not a lawful
append to the 978-row identity. This receipt does not attribute which process
performed it.

## Read-only diagnostic

Running the auditor against the stable 469-row file with a deliberately absent
override file produced:

- 166 hypothesis IDs;
- 53 EA names;
- 73 graph leaves;
- 72 terminal leaves;
- zero open economic objects;
- zero source-only objects;
- one stale screened T2 collection-only parent caused by omission of the
  receipt-bound override;
- verdict `NO_OPEN_ECONOMIC_CANDIDATE`.

That diagnostic is not an authoritative refreshed lineage audit. The missing
override was intentional; it proves only that the current raw file does not
contain an economic-open row under the coherent authority gates.

## Guard

- Do not auto-edit `CANDIDATE_LINEAGE_OVERRIDES.json` to the new hash merely to
  make tests pass.
- Do not append research to, compact, restore or otherwise repair the registry
  from this task while the owner/concurrent writer is unknown.
- Do not keep quoting the historical 978-row/137-leaf result as confirmed
  current.
- Before the next registry-authoritative decision, reconcile the intended
  canonical registry identity, review the replacement provenance and then
  deliberately refresh any hash-bound lineage receipt.

The overall EA goal remains `ACTIVE / UNMET`; this integrity hold blocks only
claims derived from the hash-bound lineage auditor, not the goal itself.

