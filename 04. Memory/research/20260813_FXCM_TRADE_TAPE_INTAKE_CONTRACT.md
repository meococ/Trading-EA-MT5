# FXCM Pro Trade Tape pre-outcome intake contract - 2026-08-13

State: `FROZEN_DRAFT_NO_VENDOR_CONTACT_NO_ACQUISITION`

Object: `FXCM-PRO-TRADETAPE-RETAIL-TXN`

This contract applies only if the Owner later authorizes the vendor inquiry and
then separately authorizes receipt or acquisition. It is outcome-blind and does
not authorize a hypothesis, signal, EA, backtest or live use.

## Fail-closed gates

1. **Written contract pack.** A countersigned document must state that the
   Owner is eligible, resolve professional-feed versus personal-sample terms,
   give price and term, permit retention of paid history after cancellation,
   and allow internal research plus local MT5 ingestion. Missing clause fails.
2. **Price and term.** A firm written quote in a named currency must fit a
   future Owner ceiling and have a capped term/usage schedule. Verbal or
   unbounded usage pricing fails.
3. **Canonical history start.** The 2018 sheet establishes a 2017 lower bound.
   The vendor must state the current start and explain whether the published
   2012 claim names another product. The written start must match delivered
   files; undocumented dual starts fail.
4. **Symbol lock.** EURUSD and XAUUSD must exist on both historical CSV and live
   FIX 4.4. Either symbol missing on either path fails the object.
5. **Current quantity-sign identity.** The 2018 prior is bought-positive,
   sold-negative, with FIX Side 1/2. At least five current dated fixtures
   containing both sides must reproduce it. A mismatch fails and cannot be
   repaired by inventing another sign.
6. **Current clock and DST.** The 2018 prior is UTC execution time, while the
   current Pro page says EST. The vendor must name the authoritative current
   event clock, received/publication clock and DST rule, and delivered records
   must reproduce it. Mixed or unexplained time fails.
7. **Population and methodology version.** The vendor must define the covered
   FXCM retail executed-transaction population and tag every delivery/session
   with a methodology version. Silent regional, account or method changes fail
   from the change point.
8. **Historical/live identity.** Current CSV and FIX must share symbol mapping,
   quantity sign, rate units, clock, population, version and lifecycle rules.
   They must match the 2018 tag list/defaults or a dated successor changelog.
   An unexplained break fails.
9. **Lifecycle semantics.** The current meaning of tags 487 and 570 plus cancel,
   correction, partial fill, duplicate and late-record handling must be
   documented and flagged in data. Silent overwrite or unidentifiable
   duplicates fail.
10. **Immutable manifest.** Each file/symbol/day requires SHA256, byte count and
    row count. Independently recomputed values must match.
11. **Coverage without fabrication.** Delivery must span the canonical start to
    the latest complete date with an explicit gap/completeness map. Missing
    symbol-dates are excluded. Imputation and forward-fill are forbidden;
    silent gaps fail the pack.
12. **Source rate versus target ban.** Raw tape `Rate` is an allowed source
    field. Target MT5 OHLC, future return, PnL, PF or strategy outcome may not
    enter the delivery or intake QA.
13. **Counts-only QA.** Allowed QA reads timestamp, symbol, signed quantity,
    optional source rate, lifecycle flag, received time and completeness. It
    may report rows per symbol/day, long/short counts, duplicates and late-row
    rates. It may not create a signal, threshold, direction or horizon.
14. **Independent-date capacity.** After gates 4-11, count only complete
    EURUSD/XAUUSD dates. There must be enough dates for a later preregistered,
    non-overlapping cadence to yield at least 150 independent decisions.
    Cadence cannot be selected from outcomes at intake.
15. **Append-only intake receipt.** Hash the vendor reply, contracts, specs,
    fixtures, manifests and the gate table. Any failed gate leaves
    `hypothesis_authorized=false`.

## First fatal fail

Current-version identity at gates 5, 6 and 8. The 2018 schema is a valid prior,
not permission to assume that the present product is identical. Any unexplained
sign, clock or schema mismatch stops intake before aggregation.

## Allowed artifacts

- vendor letter, written quote and signed terms;
- product sheet, schema/FIX specification and methodology changelog;
- Owner-authorized sample or historical CSV/FIX fixtures;
- completeness/gap statement and immutable manifest;
- counts-only QA table constrained by gate 13; and
- append-only intake receipt.

## Forbidden actions

- agent-sent vendor contact, signup, trial or purchase without Owner authority;
- target MT5 OHLC, future returns, PnL, PF or strategy readout;
- EA/code/backtest before source intake and hypothesis preregistration;
- choosing follow/fade direction, threshold, session or horizon from outcomes;
- merging this transaction tape with retail-positioning or CLS flow identities;
- imputation, forward-fill, silent correction or a live-readiness claim.

## Pass only unlocks

All fifteen gates passing establishes source-intake capability only. It unlocks
a separate Owner cost acceptance and a new hypothesis-ID preregistration. It
does not establish engineering-valid, economic-valid or promotion-ready status.
