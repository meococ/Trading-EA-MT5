# DATA-FIVEPERCENT-5ASSET-MULTITF-003 Plan

Status: FROZEN before the one production export.

Date: 2026-08-02

## Objective

Create a reusable, symbol-safe FivePercentOnline-Real broker-bar foundation on
`D:` for the Owner-requested instruments. User aliases are normalized once:

- `JPYUSD` -> `USDJPY`
- `GPBUSD` -> `GBPUSD`

The canonical ordered universe is:

`EURUSD, USDJPY, GBPUSD, XAUUSD, BTCUSD`

This is raw data setup only. It is not an EA hypothesis, economic trial, T2
Model-4 receipt, tester History Quality result, or true order-flow dataset.

## Carry-forward from failed datasets

- Dataset 001 failed before its first output because the full 56-year M1 range
  exceeded MT5's single-request envelope. Its authority is consumed.
- Dataset 002 used bounded M1 chunks and successfully wrote eight unpublished
  EURUSD/USDJPY files, then failed closed on three duplicate GBPUSD M1 rows.
  Forensics proved all three source rows have the same epoch, OHLC, volumes and
  spread. Its authority is consumed and its partial corpus is marked unusable.

Dataset 003 preserves chunking and adds one narrowly authorized repair: a
same-epoch group may be collapsed to one row only when every source field is
identical. Any conflicting value remains a hard failure. Counts are published
per file in the manifest.

## Frozen source and bounds

- Terminal:
  `02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe`
- Portable data root:
  `02. AlphaFactory/runtime/mt5-portable-fivepercent/`
- Expected server: `FivePercentOnline-Real`
- Expected company: contains `Five Percent Online Ltd`
- Demo trade mode is allowed; source identity is the exact broker server above.
- Terminal trading must be disabled before every read.
- Terminal `MaxBars` must be at least 20,000,000.
- Requested start sentinel: `1970-01-01T00:00:00Z` (all broker history).
- Frozen cutoff: `2026-08-01T23:59:59Z`.
- Native timeframes: `M1, M5, H1, H4`.
- API: `MetaTrader5.copy_rates_range`; no order, position, deal-history or
  account-history API is allowed.
- M1 is requested in non-overlapping ten-calendar-year chunks. M5/H1/H4 use
  one full-range request each.

## Storage contract

Create new files only under:

`02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-003/`

Existing corpora and failed datasets 001/002 must not be overwritten. Each
symbol/timeframe gets one Parquet file with this explicit schema:

`symbol, timeframe, time_server, time_utc, utc_offset_h, open, high, low, close, tick_volume, spread, real_volume`

`time_server` preserves the broker wall clock encoded by MT5. `time_utc` uses
the canonical FivePercent era-aware UTC+2/+3 model. Only fully closed bars at
or before the frozen cutoff may be published.

For each frame the manifest records raw source rows, exact-duplicate groups,
removed exact-duplicate rows and conflicting groups. Exact duplicate removal
is deterministic `keep first`; since all source fields must match, the retained
row is value-equivalent. After reconciliation UTC times must be unique and
strictly increasing.

The root `manifest.json` binds every file by path, byte count and SHA256, plus
symbol geometry, rows, first/last timestamps, gaps and outcome-blind counters.
The large Parquet corpus remains ignored by Git; durable receipts live under
the package evidence directory.

## Fail-closed gates

1. Tool, tests and this plan are hash-bound by a one-use run-authority file.
2. Terminal executable and live data path resolve to `D:`.
3. Live server/company match exactly and terminal-side trading is disabled.
4. All five canonical symbols exist with frozen digits/point geometry.
5. All four requested native timeframes return at least one closed bar.
6. Same-time source rows with any conflicting field fail; only exact duplicates
   may be collapsed and their counts must be retained.
7. Every reconciled frame has exact identity, positive finite OHLC, unique
   strictly increasing timestamps and no bar closing after the cutoff.
8. Every bounded request stays below the 20-million-bar cap.
9. Dataset root is absent or empty before the run; no overwrite/resume under
   this ID is allowed.
10. Published file hashes are re-read and reconciled into manifest and receipt.
11. The canonical four protected `C:` roots are snapshotted immediately before
    and after export; metadata digests must be identical.

Any failure yields a data-setup blocker only. It cannot be reinterpreted as a
market no-edge verdict.

## Authority exclusions

- Orders submitted: 0.
- Trades simulated: 0.
- PnL, PF, WR, expectancy, cadence, MFE/MAE: forbidden.
- Validation/holdout selection: not performed.
- Optimization, promotion, paper and live authority: false.
- `tick_volume`, candle direction and `real_volume` are not aggressor-side
  volume; this dataset cannot authorize true CVD, VPIN or LOB OFI claims.
- T2 remains a nine-symbol no-skip Model-4/HQ>97 contract. This five-symbol raw
  corpus does not satisfy or partially unlock that campaign gate.
