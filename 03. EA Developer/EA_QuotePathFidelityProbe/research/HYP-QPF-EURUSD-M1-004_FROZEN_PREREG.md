# HYP-QPF-EURUSD-M1-004 - frozen D0-proof quote-path fidelity reissue

Status: `FROZEN_SOURCE_ONLY_NO_OUTCOME` on 2026-08-12.

HYP004 preserves HYP003's FivePercent Real EURUSD M1 source, completed-M5
observable set, `[2018-01-01,2026-08-01)` window, denominators and all pooled
and per-year thresholds. The only source delta is identity plus the standard
fail-closed AlphaFactory `DATA_EPOCH_D0_SERIES_PROOF`. The proof reads only
MT5 series availability timestamps/counts and cannot read future returns,
trade outcomes or economics.

Tester: Model 0 through `02. AlphaFactory/alpha.ps1`. Required sidecar: exactly
one `*_QuotePathFidelity_*.csv`. Required explicit overrides, with no omission
or addition:
`InpCollectionOnly=1;InpHypothesisId=HYP-QPF-EURUSD-M1-004;InpExpectedSymbol=EURUSD;InpExpectedPeriodMinutes=1;InpBucketMinutes=5`.

HYP003 is terminal engineering-invalid because it omitted the D0 proof, causing
AlphaFactory to stop before completing sidecar identity. Its diagnostic values
are not a source verdict and cannot be used to alter HYP004.

Frozen source gates, evaluated simultaneously pooled and separately for every
year 2018-2026:

1. Exact five tester inputs appear in config and journal; D0 series proof passes;
   History Quality is strictly greater than 97%; Model 0 is used.
2. Source, EX5, config, report and exactly one CSV are hash-bound in the completed
   manifest; compile is fresh with zero errors and zero warnings.
3. Zero orders/trades and unchanged final balance; every row has
   `bar_complete=true`, `orders_sent=0`, `promotion_eligible=false`.
4. Invalid/crossed quote share is at most 0.10%; reverse millisecond clock count
   is zero; positive timestamp coverage is 100%.
5. At least 95% of active M5 buckets contain at least 20 valid quote changes.
6. Exact duplicate share is below 5% of
   `quote_changes + exact_duplicate_quotes`.
7. `(bid_only+ask_only)/quote_changes` is at least 5%, and
   `spread_changes/(quote_changes+exact_duplicate_quotes)` is at least 1%.
8. Bucket timestamps are strictly increasing and unique, all years are present,
   the final open bucket is omitted, and no economic/outcome column exists.

Verdicts:

- `PASS_QUOTE_PATH_FIDELITY_MAY_RESEARCH_CLOSED_M5_M15_CHILD`
- `KILL_QUOTE_PATH_FIDELITY_EXACT_EURUSD_METATICKS`
- `ENGINEERING_INVALID_NO_SOURCE_VERDICT`

This is the final one-shot source confirmation. No same-ID rerun, threshold,
denominator, year or symbol change is permitted after launch. A valid KILL
closes this exact information object. Only a valid PASS may authorize a fresh,
separately preregistered closed-M5/M15 economic child.
