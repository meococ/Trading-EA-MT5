# T2 VolmanCausalGrammar P3 engineering closeout

Date: 2026-08-13

Verdict: `TERMINAL_T2_P3_DUPLICATE_IDENTITY_POPULATION`

## Scope and authority

This work resumed the frozen EURUSD M5 T2/P3 outcome-blind identity/de-dup
gate. It did not read trades, excursions, returns or economics and never
authorized MQL5, MT5, an EA build or deployment. Grok Build acted as an
adversarial reviewer; local locks, source hashes, tests and receipts are the
authority.

## Engineering repair chain

1. The unchanged grammar completed a deterministic 50,000-bar benchmark in
   8.8582 seconds, while the prior full v1 replay had timed out after 3,600
   seconds without a packet.
2. A timing-only real prefix passed at 5,644.47 bars/second, but Grok correctly
   rejected using grammar timing as full-identity authority.
3. One same-path 50,000 prefix then hit its frozen 300-second wall before
   committing a packet. A separately locked stage-only probe localized the
   work to `ecrs_prefix`: at 297.74 seconds it had traversed 50,000/50,000 bars,
   CPU was still advancing and RSS was 571,576,320 bytes.
4. Static review found the matching O(n^2) defect. The frozen ECRS trace
   recomputed ATR-SMA20 and tick-volume-SMA20 across the full series at every
   signal index. The frozen mirror remained unchanged. A successor cached only
   those two arrays once per state.
5. The cache successor passed 78 deterministic tests, including per-index old
   versus new trace equality and exact emitted-event/event-key equality across
   empty/short inputs, indicator boundaries, missing/NaN values, news, session,
   spread and missing-bar gaps. Cache lock:
   `FB22FC27D1800589D7F0F291003FF7633BF2D83AE8DF98D1A025F2D4EDDE4363`.
6. One repaired 50,000 prefix completed the cached ECRS stage but failed at a
   non-v1 generic prefix comparator. No packet was retained. Review established
   that the frozen D7 comparator is structurally full-ledger-only: it requires
   exactly 596,141 rows and complete 2015-01-02 through 2022-12-30 coverage.
7. The sole authorized repaired full replay used the exact frozen
   `run_identity_comparisons`, full-source manifests,
   `compare_d7_primary_full_ledgers` and `write_result_packet`. The only
   computation substitution was the parity-locked cached ECRS emitter. It
   passed 89 tests and verify-only before execution.

## Terminal result

The full replay ran for 165.68 seconds and exited nonzero at
`pbp_identity_projection_full`. The exact frozen `_ensure_unique` guard found
11 duplicate normalized T2 PBP identities:

- 10 `PBP_BREAK_WINDOW` keys; and
- 1 `PBP_TOMBSTONE_CONTACT` key.

The collision key is `namespace + NORMALIZED_OVERLAP_FIELDS`. Multiple causal
audit events therefore collapse onto the same frozen SCC-comparison identity.
Selecting first/last, adding barrier provenance to the key or silently
deduplicating would change the frozen population/comparison semantics. Those
are new contracts, not an engineering repair.

The parent deleted the partial packet. `packet_verified=false`; no durable
identity counts, Jaccard, D7/D8 verdict, edge, economic result or build/live
authority exists.

Canonical evidence:

- full lock SHA:
  `5133F1221854E7CB626EB9B520B09DC70CF04154F060DA381DB359D6B00A1B5E`;
- heartbeat SHA:
  `296AFBD68A04DEB397D9A8E77BE0F43AF52062899D5043EACB394520F60E47A8`;
- stage receipt SHA:
  `66849ABEF8BB5C193FC6E19E3DC50AC4A225F37B604BD02FD46B8AF527272D08`;
- frozen mirror SHA:
  `11124E256986814C70B7BA97A0585F7447081F853D7847A78D205EAA2329EBC9`;
- cache successor SHA:
  `B077AD37B657A19406F19DC126007A657650DF963774F2432FB032E20412F7FD`.

## Failure radius and next boundary

The closed radius is the frozen T2/P3 result packet on the bound EURUSD M5
full ledger, specifically its PBP normalized identity population. No second
prefix/full replay, key/count rescue or threshold/source/schedule/grammar/
comparison change is authorized.

The following remain engineering-valid only: frozen input/hash verification,
the ECRS cache parity proof, successful full T2 and cached-ECRS stage execution,
and the fail-closed duplicate-key receipt. None establishes D7 pass, economic
validity or promotion readiness.

A different PBP identity key or population requires a new Owner/Lead contract
and is not a continuation of T2. The overall XAU/Forex EA goal remains
`ACTIVE / UNMET`. Its lawful frontier is still a materially new source object
or independently cured existing sleeve; the already-closed local and external
zero-cost frontier must not be repackaged into a candidate.
