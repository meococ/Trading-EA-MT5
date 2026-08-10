# HYP-CRSI-XAUUSD-H1-001 — Independent Pre-run Review

Verdict: `PASS`

Scope: static source-feasibility package review only. No Parquet row was opened and the analyzer was not executed during review.

## Frozen identities

- Preregistration SHA256: `70951DE02291AA490F0F0D06B27A43AEE495A7D5AD43AA8C7A770A4E9CBB84F6`
- Analyzer SHA256: `318AA0C142112A455DE00F33DA33A4D9E8EFB8B9F97BCE58295E72D2D00B381A`
- Test SHA256: `6189C091B5A54D838A81201B8E4A7F247BCDC54C3E0BC7E3CFBBF367DD7EBF4B`
- Test result: `80 passed`
- Frozen attempt: `CRSI001-SOURCE-ATTEMPT-001`

## Review findings

- CRSI `(3,2,100)` calculation is exact under the preregistered contract: Wilder RSI seeds and zero branches, up/down streak equality reset, strict tie-excluded current ROC rank against the prior 100 ROCs, and the three-component average.
- Current/prior CRSI signal dependency is exactly `t-102..t`; the first usable event index is `102`.
- LONG and SHORT re-entry predicates, equality boundaries, design-only scoring, exact-next timestamp-only execution mapping, calendar-year accounting and source-only ledger allowlist are causal and outcome-blind.
- The complete native H1 close chain from `2004-06-11T04:00:00Z` through design end must be finite and strictly positive, so the calculation cannot silently reseed after an invalid prehistory close.
- Registry authority explicitly binds prehistory access, manifest/data path and SHA, predicate, analyzer/test path and SHA, pristine counters and run IDs, and an omission-fail-closed false permission matrix.
- The attempt claim is exclusive and durable before source data access. Deterministic in-memory replay and receipt/terminal bindings are present.
- No prior Connors RSI/CRSI hypothesis exists in the candidate registry or failure catalog; this is materially distinct from the terminal Supertrend, Vortex, MFI, Ichimoku, VWAP, sweep/retest and compression mechanisms.

## Authorized scope

Authorize exactly one outcome-blind source/cadence scan over the frozen native FivePercent XAUUSD H1 dataset, with full prehistory state and scoring only in 2018–2022. No post-event price, return, trade simulation, PF, MQL5, MT5, optimization, validation, holdout, deployment or live authority is granted.
