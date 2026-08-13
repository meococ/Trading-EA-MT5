# HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001 - source feasibility plan

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

## Identity

- Hypothesis: `HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001`
- Attempt: `DOLUI001-SOURCE-001`, limit exactly one full-corpus attempt.
- Family: `official-dol-ui-unadjusted-seasonal-residual`.
- Intended target: FivePercent `EURUSD`, H1, closed-bar execution only.
- Archive cutoff: `2026-08-06` inclusive.
- Source cost: USD `0.00`; no account, key, purchase, subscription or
  auto-renewal.

This plan freezes a source object, not an edge. It authorizes only official DOL
archive discovery, PDF download, field extraction, hashing, source-direction
counts and a static tester CSV. It does not authorize reading EURUSD prices,
returns, trades, PnL, PF, drawdown, validation target prices, holdout target
prices, MQL5, MT5, optimization, promotion, paper or live trading.

## Materially fresh information object

Every weekly DOL `UNEMPLOYMENT INSURANCE WEEKLY CLAIMS` release co-publishes:

1. the advance unadjusted initial-claims change from the preceding week; and
2. the change that the official seasonal factors had expected.

Freeze the information field as:

`seasonal_residual = actual_unadjusted_change - seasonal_expected_change`.

The sign is fixed before any target-price observation:

- positive residual: claims are worse than the official seasonal expectation,
  USD-negative, future candidate side `BUY_EURUSD`;
- negative residual: claims are better than the official seasonal expectation,
  USD-positive, future candidate side `SELL_EURUSD`;
- zero residual: `FLAT`, no future trade.

There is no magnitude threshold, percentile, event-name selection, day/session
filter, target-price sign, consensus forecast or retrospective ALFRED value in
the formula. The object is distinct from the killed ForexFactory retrospective
consensus payload and the unavailable MT5 Economic Calendar delta lane.

## Primary sources and delivery identity

- Archive tool: `https://oui.doleta.gov/unemploy/claims_arch.asp`
- Archive POST endpoint: `https://oui.doleta.gov/unemploy/archive.asp`
- Current official release: `https://www.dol.gov/ui/data.pdf`
- Historical PDF shape: `https://oui.doleta.gov/press/YYYY/MMDDYY.pdf`

The archive form is queried with `report=press`, an exact year, and
`submit=Submit`. Only links returned by that official form are admissible; URL
guessing is forbidden. The live object is the same weekly DOL PDF schema at the
stable current-release URL. A future EA may use a hash-bound static CSV in the
tester and a separately reviewed pure-MQL5 HTTPS/PDF extraction path live. This
plan does not authorize that live implementation.

## Frozen fields and clock

For each archived PDF, extract only:

- source URL, bytes, page count and SHA-256;
- release date and the explicit `8:30 A.M. (Eastern)` embargo clock;
- release UTC derived with `America/New_York`, preserving EST/EDT;
- claims week-ending date;
- first-public seasonally adjusted initial-claims level and signed weekly
  change;
- whether the prior level was described as revised or unrevised and the
  revision delta when explicitly stated;
- first-public unadjusted claims total and signed weekly change;
- official seasonal-factors expected signed change;
- the exact residual and frozen EURUSD side above.

The PDF release date must equal the archive path year plus the filename's
`MMDD` components. The two-digit filename year suffix is recorded but is not
authoritative because the official 2019 archive contains `010318.pdf` for the
2019-01-03 release. The claims
week-ending date must be no later than the release and no more than 14 days
earlier. Missing, duplicated, conflicting or ambiguous values fail closed.

## Frozen corpus and stage labels

The pre-plan archive census observed these official-link counts through the
cutoff. The full attempt must reproduce them exactly:

| Year | Expected PDFs | Stage label |
|---:|---:|---|
| 2018 | 52 | TRAIN_SOURCE |
| 2019 | 51 | TRAIN_SOURCE |
| 2020 | 53 | TRAIN_SOURCE |
| 2021 | 52 | TRAIN_SOURCE |
| 2022 | 52 | TRAIN_SOURCE |
| 2023 | 52 | INTERNAL_VALIDATION_SOURCE |
| 2024 | 52 | INTERNAL_VALIDATION_SOURCE |
| 2025 | 46 | SEALED_HOLDOUT_SOURCE_ONLY |
| 2026 through 2026-08-06 | 31 | SEALED_HOLDOUT_SOURCE_ONLY |

Thus the expected totals are 260 TRAIN source rows, 104 internal-validation
source rows, 77 sealed-holdout source-only rows and 441 rows overall. No target
price belonging to any stage may be opened by this attempt.

## Source-only gates

All gates were frozen without EURUSD outcomes:

1. exact official archive counts above and 441 unique URLs;
2. 100% successful in-attempt PDF download from the returned official URLs,
   zero pre-existing raw-cache reads, `%PDF-` signature and nonempty SHA-256;
3. 100% parse coverage for release clock, SA first print, unadjusted actual
   change and seasonal expected change;
4. 100% unique release UTC and claims week-ending identities;
5. exactly 260/104/77 rows in the three source stages;
6. at least 95% nonzero residuals;
7. among nonzero TRAIN residuals, at least 20% `BUY_EURUSD` and at least 20%
   `SELL_EURUSD`;
8. no TRAIN year may contribute more than 22% of TRAIN rows;
9. zero price, return, trade, economic, MQL5, MT5, validation-target and
   holdout-target reads.

The attempt verdict is `PASS_SOURCE_FEASIBILITY` only if every gate passes.
Any failure produces `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY`. A pass authorizes a
new, separately frozen economic preregistration; it is not economic-validity or
permission to code an EA.

## Prospective economic skeleton - not yet authorized

If the source passes, a new economic packet may freeze one untuned EURUSD H1
baseline, enter only after the required completed H1 decision bar, close before
the weekend, include spread/commission/dynamic slippage, and compare the frozen
polarity with exactly one reversed-sign comparator. TRAIN is 2018-2022,
internal validation is 2023-2024, and 2025-present target prices remain sealed.
No holding period, SL/TP or risk parameter is authorized by this source plan.
