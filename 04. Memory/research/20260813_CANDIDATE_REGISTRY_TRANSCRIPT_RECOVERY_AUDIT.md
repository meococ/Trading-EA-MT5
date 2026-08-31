# Candidate registry transcript recovery audit

Date: 2026-08-13 (Asia/Saigon)

## Verdict

`EXACT_978_BYTES_NOT_RECOVERED_HISTORICAL_FRONTIER_RECEIPT_CONFIRMED`

The missing 978-row registry was not reconstructed and the live registry was
not overwritten. The historical audit result is nevertheless confirmed as an
actual execution receipt in the current Codex session transcript, not a prose
memory:

- session id: `019fe528-57e7-7f63-8b80-9d1aff3841f9`;
- transcript JSONL line: `42662`;
- event timestamp: `2026-08-13T14:25:12.375Z`;
- call id: `call_zEHK1nmgR2uIAncSsHlPp0fV`;
- exact transcript-line bytes: `3596`;
- transcript-line SHA256:
  `C33D0D2B208277DD92390E3C0B593033719FBB1221239563574C57AF79CAC425`.

That receipt records the actual auditor output:

- rows: `978`;
- hypotheses: `390`;
- EA names: `99`;
- registry SHA256:
  `2043351DDB09F826187D4A55690646DC946415062531063774A721C334F26391`;
- open economic: empty;
- source-only: empty;
- stale nonterminal: empty;
- verdict: `NO_OPEN_ECONOMIC_CANDIDATE`.

The later revised lineage implementation and hash-bound override were reviewed
by Grok and passed 9/9 local tests, producing the stricter 137-terminal-leaf
frontier already documented in
`20260813_CANDIDATE_FRONTIER_LINEAGE_AUDIT.md`.

## Recovery attempts

1. A streaming transcript scan found no complete 978-row output. Shell output
   containing registry rows was truncated near 40 KB.
2. Successful `apply_patch` transcript events preserve exact unified diffs, but
   they do not cover every row appended by external worker processes.
3. The latest immutable local registry artifact remains the exact 877-row
   snapshot at SHA256
   `22D11CDC3B5827590B50F7082E8F423EC6C0D0977B0ADC37F8FAF3E8C284D558`.
4. A bounded Grok Build workspace search returned
   `NOT_FOUND_IN_BUILD_WORKSPACE` for the exact 978-row hash and later copies.

## Safety consequence

The historical frontier receipt may be used to prove what the auditor actually
reported at that hash. It is not a replacement for the missing registry bytes
and does not authorize rebinding `CANDIDATE_LINEAGE_OVERRIDES.json`, appending a
new registry row, reopening a terminal candidate or running economics.

Source-contract work may continue without registry mutation. Any future
candidate authorization remains fail-closed until the canonical registry
identity is restored or the Owner approves a new authoritative ledger process.
