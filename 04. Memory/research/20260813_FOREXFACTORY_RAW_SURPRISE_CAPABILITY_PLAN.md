# ForexFactory raw surprise capability plan — 2026-08-13

Status: `FROZEN_SOURCE_ONLY_AFTER_SCHEMA_PREFLIGHT`.

## Why this audit exists

The normalized ForexFactory calendar CSV intentionally contains only event
clock fields. A source-only schema preflight of the already-local raw JSON found
additional `actual`, `forecast` and `previous` strings. Before treating those
fields as an information object, this one audit asks whether they can satisfy a
point-in-time macro-surprise source contract.

The preflight read the container metadata and one sample record only. It did
not aggregate the event population, read any market price, calculate a return,
choose a direction or inspect economics. This plan freezes the aggregate audit
before those source-only counts are computed.

## Frozen input

- Path:
  `02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json`
- Bytes: `944989`.
- File modified UTC: `2026-07-18T15:40:28.0378275Z`.
- SHA-256:
  `78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F`.
- Declared coverage: 2019-01-01 through 2022-12-31, EUR/USD high-impact events.
- Declared acquisition: 2026-07-18.

Only the raw JSON above may be read by the audit. The normalized CSV, market
bars, ticks, MT5 reports, registry outcomes, trade logs and validation/holdout
data are not inputs.

## Frozen source gates

All gates must pass to call the payload a candidate source:

1. `container_identity`: input SHA, schema version and event count reconcile
   with the embedded validation block.
2. `field_presence`: every event has time, ID, currency, name and the three
   surprise-field keys, even if a value is blank for nonnumeric events.
3. `numeric_coverage`: at least 70% of all events and at least 50% in every
   calendar year have parseable numeric `actual` and `forecast` values after a
   unit-consistent parser.
4. `first_public_pit`: each numeric event has evidence that the stored forecast
   was captured before release and the actual was captured at first publication,
   not scraped retrospectively.
5. `revision_trace`: revisions to actual/previous/forecast are versioned per
   event with capture timestamp and immutable snapshot identity.
6. `historical_live_identity`: the same field semantics and revision policy are
   documented for a current update contract usable at the intended venue.
7. `source_rank`: the payload is not marked diagnostic-only and is eligible to
   support promotion evidence.
8. `year_coverage`: every year 2019–2022 has at least 100 parseable numeric
   surprise events. This is only a source-density check, not a cadence or trade
   gate.

Gates 4–7 are provenance gates, not inferred from numeric completeness. A
retrospective third-party page with full values fails even when every string is
parseable.

## Frozen parser rules

- Accept signed decimal values with optional `%`, `K`, `M`, `B` or `T` suffix.
- Parentheses, inequality signs, ranges, text labels and mixed-unit strings fail
  numeric parsing.
- `actual` and `forecast` must have identical suffix/unit within an event.
- A surprise magnitude may be counted only as `actual - forecast`; it may not
  be mapped to EURUSD direction in this audit.
- Simultaneous events remain separate source rows. No aggregation, allowlist,
  tail threshold or event-name selection is authorized.

## Frozen output and terminal rules

The audit emits one JSON report and one receipt under:

`04. Memory/research/evidence/FOREXFACTORY-RAW-SURPRISE-CAPABILITY-001/`

Allowed verdicts:

- `PASS_SOURCE_CAPABILITY_ONLY_NO_HYPOTHESIS`; or
- `KILL_RETROSPECTIVE_OR_NON_PIT_SURPRISE_SOURCE`.

Any failure of gates 4, 5, 6 or 7 is terminal for this exact retrospective
artifact, regardless of numeric coverage. No repair, web re-scrape, source
purchase, hypothesis ID, MQL5, MT5 launch, price outcome, economic metric,
validation, holdout, paper or live action is authorized by this plan.

The report must keep these counters at zero:

- market price fields read;
- post-event returns computed;
- directions assigned;
- trades simulated;
- PnL/PF/DD metrics computed;
- MT5 launches;
- validation or holdout reads.
