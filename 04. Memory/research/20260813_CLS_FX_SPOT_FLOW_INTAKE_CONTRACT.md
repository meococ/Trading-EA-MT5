# CLS FX Spot Flow pre-outcome intake contract

Date frozen: 2026-08-13

Source object: `CLS-FXSPOTFLOW-FUND-G10CS-DAILY`

State: `FROZEN_DRAFT_NO_VENDOR_CONTACT_NO_ACQUISITION`

This contract validates a written vendor reply and, only after separate Owner
authorization, an outcome-free sample or historical delivery. It does not
authorize a purchase, source download, hypothesis, EA, target price, backtest,
paper trade or live trade.

## Authority sequence

1. Current authority permits only public-document research and this frozen
   contract.
2. Explicit Owner authorization is required before sending the inquiry.
3. A vendor reply and quote remain metadata. Owner must separately set and
   approve a hard one-time/recurring cost ceiling before any agreement, trial,
   sample access or API credential.
4. A paid or free sample must still pass every source-intake gate below before a
   hypothesis ID may be drafted.

## Fifteen fail-closed gates

1. **Written rights.** Vendor terms explicitly permit internal quantitative
   research and a local adapter feeding one MT5 process, prohibit external
   redistribution, state whether historical files may be retained after
   cancellation, and provide methodology-change access. Missing or ambiguous
   rights fail the source.
2. **Firm price and term.** Written quote states currency, setup fee, recurring
   fee, minimum term, seats, API/CSV entitlements and any usage/overage charge.
   It must be within a future explicit Owner ceiling. No uncapped or verbal
   price passes.
3. **Pair coverage lock.** Vendor names every delivered USD-major FX Spot Flow
   pair. The admitted universe is frozen to pairs present in both the written
   list and the sample; later missing pairs fail that date, not silently shrink
   the universe.
4. **Segment identity.** Data dictionary proves an isolatable fund-side executed
   spot field: funds-only bought and sold volume, or a documented funds leg
   against banks from which the same net is computed. A generic buy-side,
   aggregated-all-client or non-isolatable field fails.
5. **Sign and quote fixtures.** Vendor supplies at least three dated pair-level
   fixtures containing bought volume, sold volume, signed net and quote
   convention. Fixtures must cover both foreign-base/USD-quote and USD-base/
   foreign-quote pairs. Independent recomputation must map every row to
   foreign-currency buying pressure versus USD exactly.
6. **Clock and DST.** Each row has timezone-tagged event/window time and
   received/available time. Vendor documents New York DST conversion. Date-only,
   mixed-zone or inferred timestamps fail.
7. **Completeness at the frozen cut.** For the 24-hour window ending 16:00 New
   York, a machine-readable status or written SLA proves which rows were fully
   available by 16:30. Missing or late status makes that date flat/unused.
8. **Historical/dynamic identity.** Historical daily/hourly and dynamic samples
   share the same units, sign, segment taxonomy, pair identity and explicit
   methodology-version ID. An unexplained version or schema break fails.
9. **Revision semantics.** Vendor documents late matches, cancels, restatements
   and deletions. Revisions retain as-of/received time and prior identity or
   hash; silent overwrite fails.
10. **Immutable manifest.** Every delivery file is bound by source request,
    acquisition time, bytes, rows and SHA256. Recomputed values must match; no
    partial or mutable file is admitted.
11. **Coverage.** Historical delivery spans 2018-01-02 through the latest
    complete New York business date. Missing rows remain explicit gaps; no
    imputation, forward-fill or synthetic reconstruction is allowed.
12. **Counts-only transform.** Allowed derived columns are date, pair, signed
    fund flow, past-only 60-day standard deviation, standardized flow, rank,
    source completeness and methodology version. No price, spread, OHLC,
    return, PnL, PF, trade or future label may enter the intake process.
13. **Population ceiling.** At least 150 non-Friday dates must have the complete
    frozen pair set, a valid past-only 60-day window and 16:30-complete data.
    This is a source/cadence gate only, not economic evidence.
14. **Fail-closed daily state.** Any missing pair, late row, hash mismatch,
    incomplete rolling window, sign ambiguity or methodology break makes the
    whole cross-section flat for that date. Partial-universe ranking is
    forbidden.
15. **Append-only intake receipt.** One receipt binds vendor replies, quote,
    licence, schemas, fixtures, manifests and every gate result. Any failure
    leaves `source_intake_pass=false` and `hypothesis_authorized=false`.

## First fatal stop

Gates 4 and 5 are evaluated before any counts-only transform. If the fund field
cannot be isolated or the foreign-currency-versus-USD sign cannot be reproduced
from vendor fixtures, stop without opening a source sample beyond the permitted
metadata and without attempting another segment, sign or rule.

## Allowed artifacts after separately granted authority

- vendor email/letter, terms, quote and data dictionary;
- outcome-free CSV/API sample and historical flow files;
- methodology/revision/SLA note and sign fixtures;
- immutable file manifest and counts-only source-rank table;
- append-only source-intake receipt.

## Forbidden actions

- sending the inquiry before Owner authorization;
- accepting terms, starting a trial, creating credentials or purchasing before
  a separate Owner cost decision;
- target OHLC/return/PF access, MQL5, MT5, optimization or charting;
- imputation, threshold search, pair substitution, segment substitution,
  session selection or sign inversion after any source readout;
- interpreting source-intake PASS as economic-valid or promotion-ready.

## PASS-only consequence

All fifteen gates passing would establish only `source_intake_pass=true`. It
would unlock a new, separately reviewed hypothesis-ID preregistration. It would
not authorize economics, validation, holdout, paper trading or live trading.

