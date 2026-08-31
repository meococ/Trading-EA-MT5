# Candidate registry local recovery inventory

Date: 2026-08-13 (Asia/Saigon)

Verdict: `CANONICAL_978_BYTES_NOT_RECOVERED_DO_NOT_OVERWRITE`

## Current live file

- Path: `04. Memory/research/CANDIDATE_REGISTRY.jsonl`
- Rows: `469`
- SHA256:
  `6B23F356FDAE8402DA62056206BAA9328FC53C13C4CAE1371A1A2396F2CBE039`
- Logical tail: terminal `HYP-VRAS-USDJPY-M5-003`, dated 2026-08-02.

The file is older than multiple immutable runtime snapshots and is not a
credible continuation of the hash-bound 978-row audit.

## Immutable local snapshots found

1. `02. AlphaFactory/runtime/comparator_attempts/HYP-STBS-XAUUSD-M15-028/STBS028-COMPARATOR-001/captured/registry_snapshot.jsonl`
   - rows `877`
   - bytes `4193476`
   - SHA256
     `22D11CDC3B5827590B50F7082E8F423EC6C0D0977B0ADC37F8FAF3E8C284D558`
   - captured 2026-08-10T01:47:25Z
2. `02. AlphaFactory/runtime/comparator_attempts/HYP-STBS-XAUUSD-M15-027/STBS027-COMPARATOR-001/captured/registry_snapshot.jsonl`
   - rows `875`
   - SHA256
     `B19A099CCFE8D2FBD85D6A0E7F01C67F67FADD31231BFC1E3A84CD806644EA70`
3. `02. AlphaFactory/runtime/comparator_attempts/HYP-STBS-XAUUSD-M15-018/STBS018-COMPARATOR-001/captured/registry_snapshot.jsonl`
   - rows `850`
   - SHA256
     `A7AB72E7B19F9DA2885C36A6ACF42665B3E55B4728D1804C4C2084ED3BEAEDAB`

The frozen lineage audit separately binds a later 978-row identity at SHA256
`2043351DDB09F826187D4A55690646DC946415062531063774A721C334F26391`,
but no exact copy of those bytes was found in the bounded local search.

## Safety boundary

- The 877-row snapshot is the newest exact local recovery artifact, not the
  canonical current registry.
- It must not replace the live file and must not receive new appends.
- Missing rows 878-978 must not be reconstructed from prose receipts and called
  original bytes.
- Git was not used. Volume-shadow inspection was unavailable without elevated
  permission. No destructive or restorative action was taken.

Source-only research may continue without registry mutation. Any future
economic authorization remains fail-closed until canonical identity is
reconciled.

## Additional transcript and Grok recovery audit

A later recovery pass confirmed the historical 978-row audit as a real
transcript execution receipt at session JSONL line 42662. That exact receipt
binds rows `978`, registry SHA256 `2043351D...F26391` and verdict
`NO_OPEN_ECONOMIC_CANDIDATE`, but it does not contain the complete registry
bytes. Grok Build also returned `NOT_FOUND_IN_BUILD_WORKSPACE` for an exact
copy or later registry artifact.

The verdict of this inventory therefore remains unchanged: do not reconstruct
or overwrite the live registry. See
`20260813_CANDIDATE_REGISTRY_TRANSCRIPT_RECOVERY_AUDIT.md`.
