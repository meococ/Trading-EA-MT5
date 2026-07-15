# Common-USD Factor Data Preflight

Date: 2026-07-10

Verdict: `BID-BAR_COVERAGE_OK / TICK-ASK-AND-COST BLOCKED`

Follow-up audit on 2026-07-11 confirms the blocker rather than clearing it:
historical quote ticks/ask barriers are unavailable, M15 spread coverage is
incomplete, commission history is insufficient, and independent pre-fill
slippage samples are zero. See
`20260711_BROKER_COST_PROVENANCE_AUDIT.md`.

## Method

A read-only MetaTrader5 Python connection queried synchronized M15 bars with
`copy_rates_range` from `2021-01-01T00:00:00Z` to
`2026-01-01T00:00:00Z`. No CSV was exported, no history was backfilled, no
tester was started, and no order or position action was performed.

Terminal fingerprint:

- terminal build: `5961`
- terminal path: `C:\Program Files\MetaTrader 5`
- data path: `C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075`
- account server: `FivePercentOnline-Real`
- account trade mode raw value: `0`
- currency: `USD`
- leverage: `100`

The raw trade-mode value and server label are recorded without inferring the
account's economic or deployment status.

## Coverage

| Symbol | M15 bars | First UTC bar | Last UTC bar | Digits | Point | Spread snapshot (points) | Trade mode |
|---|---:|---|---|---:|---:|---:|---:|
| EURUSD | 124,602 | 2021-01-04 00:00 | 2025-12-31 23:45 | 5 | 0.00001 | 2 | 4 |
| GBPUSD | 124,593 | 2021-01-04 00:00 | 2025-12-31 23:45 | 5 | 0.00001 | 3 | 4 |
| USDJPY | 124,611 | 2021-01-04 00:00 | 2025-12-31 23:45 | 3 | 0.001 | 2 | 4 |

All three required symbols exist, are visible, and cover the proposed train
and holdout windows. Counts differ slightly, so the offline probe must inner
join exact closed-bar UTC timestamps and publish missing-bar diagnostics before
forming the common factor.

## What This Does Not Prove

- A current spread snapshot is not a historical cost model.
- A bar-level spread field cannot reconstruct the ask high/low tick that decides
  a short stop or target.
- Tester-reported zero slippage is not execution evidence.
- Data availability does not prove the cross-sectional factor is predictive.
- The proposed 2024-2025 holdout is untouched only for this new hypothesis;
  those years were used by other families and cannot be described as globally
  unseen data.

## Next Gate

Before an offline outcome probe:

1. Freeze the formula and parameter budget in the preregistration.
2. Obtain same-broker historical bid/ask quote ticks, aggregate deterministic
   M15 bid/ask OHLC, inner join exact timestamps, and hash raw/joined datasets.
   The bid-only bars above are signal-data preflight, not outcome data.
3. Bind at least 30 same-symbol commission lifecycles or a hash-pinned contract,
   plus at least 100 independently referenced fills per symbol (minimum 30 buy
   and 30 sell). Measure buys from pre-fill ask and sells from pre-fill bid so
   spread is not double-counted. Convert commission per trade with the
   contemporaneous quote-to-account rate; do not reuse today's USDJPY tick
   value across 2021-2025.
4. Verify that train-only design does not read the 2024-2025 outcome columns.

The preregistration is now frozen at
`research/preregs/20260711_H_FX_CROSS_SECTIONAL_USD_FACTOR_001_PREREG.md`, but
steps 2-3 remain blocked. No analyzer outcome read, EA patch, compile, or MT5
backtest is authorized by this preflight.
