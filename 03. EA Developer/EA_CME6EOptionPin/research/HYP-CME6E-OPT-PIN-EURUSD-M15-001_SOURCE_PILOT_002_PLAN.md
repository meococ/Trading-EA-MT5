# HYP-CME6E-OPT-PIN-EURUSD-M15-001 - source pilot 002 plan

Status: frozen before any pilot-002 definition/statistics payload or EURUSD
target/outcome is opened.

## Why one more pilot is necessary

Pilot 001 passed its frozen source gates but only 66 of 90 eligible option
instruments had a published `stat_type=9` record.  Every published OI quantity
was positive.  CME documents that open interest is a previous-trading-day
statistic, is updated once per day, and that zero open interest is represented
as zero in the Security Definition feed.  Databento documents that its
`statistics` schema contains venue-published statistics, but neither source
establishes from one expiry alone that absence from the normalized Statistics
payload is a stable zero/no-published-OI state rather than an incomplete
historical surface.

This second source-only pilot tests a structurally different quarterly expiry.
It cannot calculate EURUSD direction, return, PnL, profit factor, expectancy,
drawdown, or any other economic result.

## Frozen contract

- Hypothesis: `HYP-CME6E-OPT-PIN-EURUSD-M15-001`.
- Pilot: `CME6EOPTPIN002-SOURCE-PILOT-002`.
- Dataset: `GLBX.MDP3`; DBN encoding; `stype_in=parent`;
  `stype_out=instrument_id`.
- Quarterly parent: `EUU.OPT`.
- Contract family: September 2019 quarterly Euro FX options, source-defined
  asset `EUU`, underlying `6EU9`.
- Official expiration: Friday 2019-09-06 at 09:00 America/Chicago =
  `2019-09-06T14:00:00Z`.  CME independently uses this exact date as its
  September-2019 EUR/USD option example, and SER-8206 applies the 09:00 CT
  regime after 2019-06-09.
- Decision: end of the preceding fully closed M15 interval,
  `2019-09-06T13:45:00Z`.
- Strict OI reference ceiling: prior completed CME trade date,
  `2019-09-05T00:00:00Z`.
- Request interval for both schemas:
  `[2019-09-04T00:00:00Z, 2019-09-06T13:45:00Z)`.
- Schemas: `definition` and `statistics` only.  No trades, BBO, book, OHLCV,
  fixing price, or EURUSD target source is permitted.

## Point-in-time analysis

1. Reconstruct the latest definition per instrument before the decision.  Keep
   only non-user-defined outright calls and puts with asset `EUU`, underlying
   `6EU9`, exact source expiration `2019-09-06T14:00:00Z`, and finite positive
   strike.
2. Keep `stat_type=9` only, with finite nonnegative quantity,
   `ts_event < decision`, `ts_recv < decision`, and
   `ts_ref <= 2019-09-05T00:00:00Z`.  Retain the latest admissible record per
   eligible instrument.
3. Produce two surfaces without target prices:
   - published-only: unsigned call plus put OI by exact strike;
   - zero-completed: the same surface after eligible definitions without a
     published OI record are assigned zero.
4. Missing records may be treated as zero later only if the two surfaces have
   the same unique positive maximum and the missing set contains no published
   positive OI record before decision under any duplicate symbol/instrument
   identity.
5. Any tie, empty side, post-decision record, unstable identity, or difference
   between the two maxima fails closed.  No later OI revision is admissible.

## Quote and acquisition authority

Before payload calls, obtain one live `metadata.get_cost` and one
`metadata.get_billable_size` quote per schema.  Do not acquire if the combined
quote is non-finite, negative, or greater than or equal to USD 10.  Owner's
standing authority covers this exact frozen in-scope campaign only while the
combined quote is strictly below USD 10.  Exactly two payload calls are allowed,
with no automatic retry, subscription, auto-renewal, split purchase, live
capital, or deployment authority.

## PASS/KILL gates

All gates must pass:

- definitions resolve to at least one call and one put with stable identity;
- admissible OI exists for at least one call and one put;
- all selected records meet the strict time/reference inequalities;
- no payload record at or after the decision is present;
- published-only and zero-completed surfaces have the same unique positive
  maximum-OI strike and total;
- the missing-definition rate and all missing instrument IDs/symbols are
  persisted rather than hidden by a coverage percentage;
- payloads, quote, request contract, analyzer, surfaces, counters, and artifact
  hashes are persisted under `D:`;
- target/outcome field-use lists remain empty.

Failure is `KILL_SOURCE_PILOT` for this mapping.  PASS only authorizes freezing
and quoting the full 2018-2022 source/cadence campaign.  It does not authorize
economics, MQL5, MT5, validation, holdout, optimization, paper, or live use.

## Primary-source anchors

- CME SER-8206: `https://www.cmegroup.com/notices/ser/2018/08/SER-8206.html`
- CME September-6 example:
  `https://www.cmegroup.com/education/brochures-and-handbooks/cme-listed-fx-options-a-capital-efficient-low-cost-solution.html`
- CME MDP 3.0 open interest:
  `https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457226886/MDP+3.0+-+Open+Interest`
- Databento statistics schema:
  `https://databento.com/docs/knowledge-base/new-users/fields-by-schema`

