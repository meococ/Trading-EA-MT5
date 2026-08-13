# HYP-QPF-EURUSD-M1-002 - frozen quote-path fidelity evidence reissue

Status: `FROZEN_SOURCE_ONLY_NO_OUTCOME` on 2026-08-12.

## Identity and predecessor boundary

- EA: `EA_QuotePathFidelityProbe`; symbol/timeframe: FivePercent Real
  `EURUSD` M1; completed output buckets: M5.
- Tester: MT5 Strategy Tester Model 0 / every tick based on real ticks through
  `02. AlphaFactory/alpha.ps1`.
- Frozen window: `[2018-01-01T00:00:00, 2026-08-01T00:00:00)` in broker server
  time. `ToDate=2026.08.01` is exclusive.
- Authority: `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`; zero orders,
  positions, deals and economic metrics.
- Required sidecar: exactly one `*_QuotePathFidelity_*.csv`, hash-bound in the
  run manifest and copied into the run logs directory.

`HYP-QPF-EURUSD-M1-001 / 20260812_035458` is
`ENGINEERING_INVALID_EVIDENCE_CAPTURE`: it reached 99% History Quality,
188,146,311 ticks, 2,977,291 bars, 595,936 emitted M5 buckets, zero out-of-order
buckets and zero trades, but its RequiredSidecars list was empty, so the only
artifact containing the frozen detailed gates was not captured. It also ended
at the 2025 boundary while native metadata now proves files through 2026-07.
No detailed source verdict or economic information was obtained. HYP002 changes
no observable, threshold or market thesis; it repairs evidence capture and the
predeclared availability boundary only.

## Frozen observable set

For each causal `MqlTick`, aggregate into a bucket that is emitted only after a
later M5 bucket begins:

- total ticks; valid/invalid Bid-Ask quotes; invalid/repeated/reverse millisecond
  clocks; exact duplicate quotes;
- quote changes split into Bid-only, Ask-only and both-side updates;
- mid up/down/flat counts and spread-change counts;
- tick flags, positive-volume diagnostics and fixed inter-arrival buckets;
- longest duplicate-quote and constant-spread runs plus spread point summary.

The final open bucket is omitted. The CSV contains no future return, trade,
price outcome, label, PnL, PF, balance, equity, MFE or MAE.

## Simultaneous frozen gates

All gates pass or the exact source object is killed:

1. MT5 report History Quality is strictly greater than 97%, Model 0 real ticks are used, and
   every year 2018-2026 appears in emitted buckets.
2. Source, EX5, config, report and the single required CSV are hash-bound by the
   run manifest; compile is fresh with zero errors and zero warnings.
3. Report, journal and every CSV row show zero orders/trades; final balance
   remains the initial balance; `promotion_eligible=false` on every row.
4. Pooled and per-year invalid/crossed quote share is at most 0.10%; reverse
   millisecond clock count is zero; positive timestamp coverage is 100%.
5. Pooled and per-year at least 95% of active M5 buckets contain at least 20
   valid quote changes.
6. Pooled and per-year exact duplicate quote share is below 5% of valid quote
   transitions.
7. Pooled and per-year one-sided quote-update share
   `(bid_only+ask_only)/quote_changes` is at least 5%, and spread-change share
   `spread_changes/(quote_changes+exact_duplicate_quotes)` is at least 1%.
8. Bucket timestamps are strictly increasing and unique, all identity/schema
   fields are exact, `bar_complete=true`, final open bucket is absent, and no
   economic column exists.

The transition denominator is frozen as
`quote_changes + exact_duplicate_quotes`. No denominator or threshold may be
changed after the CSV is read.

Verdicts:

- `PASS_QUOTE_PATH_FIDELITY_MAY_RESEARCH_CLOSED_M5_M15_CHILD`
- `KILL_QUOTE_PATH_FIDELITY_EXACT_EURUSD_METATICKS`
- `ENGINEERING_INVALID_NO_SOURCE_VERDICT`

No same-ID rerun or threshold/year/symbol shortening is allowed after a valid
verdict. If PASS, only a separately preregistered closed-M5/M15 child may read
price outcomes. Highest-priority family for de-dup is intra-bar Bid-versus-Ask
quote-update event-timing structure (asynchronous side revision clocks), not
generic midquote momentum/CVD, signed absorption, VRAS/reclaim, spread shock/
recovery, volume-clock exhaustion, tick-volume effort/rejection, Sonic filters
or event flow. Direction and thresholds remain unfrozen because economics are
not authorized here.
