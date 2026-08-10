# HYP028 Independent Pre-Comparator Review

- Verdict: `PASS_PRE_AUTHORITY`
- Scope: static review only; no comparator, MT5, compile, source-data, optimization, validation or holdout execution occurred.

## Frozen package

- Preregistration SHA256: `07AAE59E919A5A1A200155561A54B433D47DE5853CCD8BF10D40F417456F43B5`
- Comparator SHA256: `A6DA37D85588A5808BB47234C6EF2D414FE327334FB7EECC88D6D85A2389EF66`
- Test SHA256: `0105CF0EAA22151AEDD75426B870F071F3D56CCD9463B408423F1CBCB9DD3315`
- Focused result: `104 passed`
- Attempt: `STBS028-COMPARATOR-001`, limit `1`, consumed `0` before authority.
- Parent HYP027 terminal raw-row SHA256: `020AA793BB63BA4003F3555F627ADA3C07BB61DCAECAA95BE5E839343885D68E`

## Independent findings

1. The only functional adapter change is exact use of `run_meta_evidence.semantic_validation`; legacy-only `semantic`, dual fields, missing fields, extra fields and any of the four frozen value mismatches fail closed.
2. The HYP027 start, terminal, authority row, non-repaint audit, verified cost artifact, derived run manifest and derived cost manifest are explicitly bound. Eleven parent authority SHA fields have missing/wrong mutation coverage, and six critical parent artifacts have byte-tamper coverage.
3. Durable claim ordering, one-buffer registry parsing, immutable capture/final rehash, unified overall/baseline/exit-code reconciliation, economic false-pass protections and deterministic replay remain unchanged from the reviewed HYP027 comparator.
4. HYP028 authorizes only one comparator-only recovery over the exact sealed HYP026 run. It does not authorize MT5, compile, source-data access, strategy changes, optimization, validation, holdout, promotion, paper or live operation.

Authority may be appended only if it binds the exact three package hashes and this review SHA, preserves the frozen acceptance contract, uses pristine counters, and keeps same-ID retry false.
