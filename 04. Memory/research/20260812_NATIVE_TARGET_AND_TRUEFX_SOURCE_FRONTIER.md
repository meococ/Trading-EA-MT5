# Native Target and TrueFX Source Frontier - 2026-08-12

## Scope and authority

This checkpoint is pre-hypothesis and outcome-blind. It verifies native target
timestamps and public source contracts only. It does not authorize account
creation, acceptance of third-party terms, data download, price decoding,
return/event calculation, MQL5, MT5 economics, validation or deployment.

## Native M5/M15 target capability

Source:
`02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`

Only the `source_epoch` column was read for 2018-01-01 through 2026-07-31.
No OHLC, tick-volume, spread, return or outcome value was opened.

| Symbol | M5 rows | Duplicate timestamps | Strictly increasing | Exact 5-minute step | Complete aligned M15 triplets |
|---|---:|---:|---|---:|---:|
| EURUSD | 639,404 | 0 | yes | 99.8336% | 99.72327% |
| USDJPY | 639,434 | 0 | yes | 99.8330% | 99.72701% |
| GBPUSD | 639,318 | 0 | yes | 99.8253% | 99.71007% |
| XAUUSD | 604,078 | 0 | yes | 99.6284% | 99.26846% |

Each full 2018-2025 FX year contains about 74,000-75,000 M5 rows. XAUUSD
contains about 69,900-70,900 rows per year and shows its expected recurring
daily maintenance gaps. This proves that the current target-history blocker is
specific to BTCUSD; it is not a blocker for these four native symbols. A future
hypothesis still needs its own immutable session/coverage/clock receipt and
Strategy Tester History Quality above 97%.

## Same-symbol cross-provider frontier

### MetaQuotes-Demo -> FivePercent

Both local server trees contain annual EURUSD/USDJPY/GBPUSD/XAUUSD HCC files for
every year 2018-2026. That is only file availability. MetaQuotes-Demo is not a
documented firm or primary price-discovery venue, file-size differences do not
prove feed independence, and current HCC snapshots are not first-public
archives. Verdict:

`NO_CANDIDATE_METAQUOTES_DEMO_PROVENANCE_AND_PIT_FAIL`.

No HCC payload was decoded and no price comparison was run.

### Dukascopy SWFX -> FivePercent

Official Dukascopy documentation establishes a materially stronger source:

- SWFX is described as an ECN with a common client feed and prices combined
  from major banks, brokers and other marketplaces.
- JForex API exposes historical and live ticks/bars, including tick time, bid,
  ask and best-level volume.
- Historical tester data are built from marketplace tick-by-tick data.

However, the same official documentation says DEMO real-time ticks are created
in the DEMO environment while DEMO historical data come from LIVE history.
Without an authorized LIVE-equivalent access path, historical research and
runtime would use different source distributions. No public historical revision
log was found. Verdict:

`NO_CANDIDATE_DUKASCOPY_FREE_DEMO_TRAIN_SERVE_MISMATCH`.

Official references:

- https://www.dukascopy.com/swiss/english/forex/trading/
- https://www.dukascopy.com/wiki/en/development/strategy-api/historical-data/overview-historical-data/
- https://www.dukascopy.com/wiki/en/development/strategy-api/historical-data/history-ticks/
- https://www.dukascopy.com/swiss/english/forex/api/jforex-api/

### TrueFX / Integral OCX -> FivePercent

TrueFX was initially retained for an Owner access decision because its public
historical-download page advertises millisecond top-of-book ticks at zero cost.
That provisional conclusion is retracted after checking the current product
and eligibility pages:

- Official FAQ: indicative, event-driven institutional prices aggregated from
  real participants; FX and metals are sourced from Integral OCX.
- Official download page: millisecond top-of-book historical ticks at zero
  charge after registration/login.
- The current contact page states that TrueFX Market Data is available only to
  financial institutions, not individuals.
- The current live product page prices the Professional stream at USD 4,950 per
  month and the Institutional stream at USD 7,450 per month.
- A free registration form does not prove individual eligibility and does not
  expose an identical zero-cost live feed. Historical-only data cannot prove
  train/live-source identity for a deployable MT5 sleeve.

The Owner is an individual, no TrueFX account/data/API exists locally, and no
paid-data authorization exists. The Lead will not register, accept terms or
request paid access. Grok re-reviewed these corrected facts and retracted its
earlier access-request recommendation.

Verdict:

`NO_CANDIDATE_TRUEFX_INSTITUTION_ONLY_PAID_LIVE_AND_TRAIN_SERVE_IDENTITY_FAIL`.

Official references:

- https://www.truefx.com/truefx-market-data-faq/
- https://www.truefx.com/truefx-historical-downloads-2/
- https://www.truefx.com/contact-truefx/
- https://www.truefx.com/
- https://www.truefx.com/truefx-registration-2/

## Retired pre-price inventory gate

The previously proposed EURUSD metadata-only inventory is not authorized and
must not be executed. It would have checked monthly coverage, schema, hashes,
row counts and timestamps before opening prices, followed by a separately
predeclared live-vs-history identity test. The current eligibility and live
access facts fail before that inventory can establish a deployable source.

No account creation, terms acceptance, download, price-derived calculation,
hypothesis ID, MQL5 build or MT5 run is permitted for this TrueFX attempt.

## Current decision

The active goal remains `ACTIVE / UNMET`. No hypothesis ID is minted and no EA
is ready. MetaQuotes-Demo, Dukascopy DEMO and TrueFX are all terminal for this
same-symbol external quote-source pass under the current zero-cost individual
access contract. The next research pass must use a materially different,
lawfully accessible information mechanism; it must not reopen TrueFX by using
free history without a matching accessible live feed.
