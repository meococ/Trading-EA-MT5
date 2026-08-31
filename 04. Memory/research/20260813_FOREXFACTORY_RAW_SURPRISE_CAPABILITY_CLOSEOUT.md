# ForexFactory raw surprise capability closeout — 2026-08-13

## Verdict

`KILL_RETROSPECTIVE_OR_NON_PIT_SURPRISE_SOURCE`.

The local raw ForexFactory artifact does contain `actual`, `forecast` and
`previous` strings that were omitted from the normalized timing CSV. That is a
payload discovery, not a point-in-time data cure. The exact artifact was
acquired on 2026-07-18 for events dated 2019–2022 and contains no per-event
first-seen clock, pre-release forecast capture clock, first-public actual clock,
revision lineage or documented historical/live update contract.

No hypothesis, price outcome, direction, trade, economics, MQL5, MT5,
validation, holdout, paper or live action is authorized.

## Frozen audit and evidence

- Input:
  `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json`
- Input SHA-256:
  `78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F`.
- Frozen plan:
  `04. Memory/research/20260813_FOREXFACTORY_RAW_SURPRISE_CAPABILITY_PLAN.md`
  (`0ACF728A9F3D4A25D01F11548EE1B25F9A7C7238D3B98CCC02D26626E3629285`).
- Auditor:
  `04. Memory/research/audit_forexfactory_raw_surprise.py`
  (`1D27833ECD876C9170AD3E307DD706F916FD781D4B914014FED83C88F68DE5EF`).
- Tests:
  `04. Memory/research/tests/test_audit_forexfactory_raw_surprise.py`
  (`8750A6036143DC0627489259AA86D4271578A65F9CDD0FD83A3328C86D9C7DE8`).
- Evidence root:
  `04. Memory/research/evidence/FOREXFACTORY-RAW-SURPRISE-CAPABILITY-001/`.
- Report SHA-256:
  `C5A4C974B3B205DD9E8DEEE36DE261A2889A67E00C46B2E61B2E48B9147DF90D`.
- Receipt SHA-256:
  `A40075B09AFC4F754C054FD9250FE80AE566C0B6FBB0E285DFAADEB25BBD2F19`.

Verification passed: Python byte-compilation and five focused tests.

## Source-only result

| Gate or count | Result |
|---|---:|
| total events | 1,282 |
| required source-field keys present | 1,282 / 1,282 |
| parseable actual + forecast pairs | 880 |
| same-unit numeric pairs | 880 / 1,282 = 68.6427% |
| numeric pairs by year 2019 / 2020 / 2021 / 2022 | 238 / 205 / 180 / 257 |
| first-public/PIT rows | 0 / 880 |
| revision-trace rows | 0 / 880 |
| historical/live update contract | absent |
| declared source rank | C |
| declared promotion eligibility | false |

The frozen 70% aggregate numeric-coverage gate also failed, although every
year exceeded the 50% per-year gate and the 100-row density floor. This small
coverage miss is not the controlling failure and must not be repaired to reopen
the artifact. PIT, revisions, live identity and source rank fail independently.

All forbidden counters remained zero: market-price fields, post-event returns,
directions, trades, PnL/PF/DD, MT5 launches and validation/holdout reads.

## Grok Build red-team

The existing Build-mode Grok session received only the frozen source facts and
was forbidden from browsing, coding, re-scraping, purchasing data or reading
outcomes. It returned:

`B) REJECT_FF_RAW_SURPRISE_SOURCE`.

Its first fatal gate agrees with the local audit: one retrospective string per
field cannot reconstruct the forecast knowable immediately before release, the
first-published actual or an ordered revision history. Assuming the 2026
container value equals the release-time value would be hindsight, regardless of
numeric completeness. Grok is advisory; the hash-bound local audit controls the
verdict.

Conversation:
`https://grok.com/c/04527241-cd90-4e7f-a3e2-ea182ddbe4c8`.

## Failure radius and lawful reopen

This closes only the exact retrospective ForexFactory surprise payload. It may
not be revived by lowering 70%, selecting event names, choosing a tail,
normalizing units, grouping simultaneous releases or adding a price-conditioned
sign.

A future zero-outcome source attempt requires a hash-frozen archive that proves,
per event:

1. forecast capture strictly before release;
2. first-public actual capture at or after release;
3. ordered immutable revisions with capture timestamps; and
4. the same documented schema/revision semantics in historical and live use.

The active EA goal remains `ACTIVE / UNMET`. Continue with a materially fresh
information object; do not turn retrospective macro values into an edge claim.
