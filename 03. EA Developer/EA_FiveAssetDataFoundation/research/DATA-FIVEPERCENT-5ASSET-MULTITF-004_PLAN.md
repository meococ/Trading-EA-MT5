# DATA-FIVEPERCENT-5ASSET-MULTITF-004 Plan

Status: FROZEN before the one production export.

Date: 2026-08-02

## Objective

Create a reusable, symbol-safe FivePercentOnline-Real raw broker-bar foundation
on `D:` for `EURUSD, USDJPY, GBPUSD, XAUUSD, BTCUSD`. Owner aliases are
normalized once: `JPYUSD -> USDJPY` and `GPBUSD -> GBPUSD`.

This is data setup only. It is not an EA hypothesis, economic trial, T2
Model-4 receipt, tester History Quality result, or true order-flow dataset.

## Carry-forward from datasets 001-003

- 001 failed before its first file because a 56-year M1 request exceeded MT5's
  single-request envelope.
- 002 fixed that with ten-year M1 chunks, wrote eight unpublished partial
  files, then failed on an exact GBPUSD source triplicate. Its partial corpus
  remains marked unusable and hash-inventoried.
- 003 safely collapsed exact same-epoch source duplicates, then the complete
  20-frame preflight found 236 BTC rows whose nominal UTC values collide at
  DST transitions. These are different price bars, not duplicates. The
  EURUSD-derived broker clock is empirically valid when the FX market is closed
  during the transition; continuous historical BTC bars make those UTC labels
  intrinsically ambiguous.

Dataset 004 does not delete, shift, or invent timestamps for those BTC bars.
It preserves the broker source time as authority and explicitly nulls only the
ambiguous UTC projections.

## Frozen source and bounds

- Terminal: `02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe`
- Portable root: `02. AlphaFactory/runtime/mt5-portable-fivepercent/`
- Server/company: `FivePercentOnline-Real` / contains
  `Five Percent Online Ltd`.
- Demo account is allowed; terminal-side trading must be disabled.
- Terminal `MaxBars >= 20,000,000`.
- Source start sentinel: `1970-01-01T00:00:00Z`.
- Frozen cutoff: `2026-08-01T23:59:59Z`.
- Native timeframes: `M1, M5, H1, H4`.
- M1 uses non-overlapping ten-calendar-year requests; the other timeframes use
  one full-range request.
- Only `MetaTrader5.copy_rates_range` may read bars. Order, position, deal and
  account-history APIs are forbidden.

## Timestamp and duplicate contract

The primary, complete, unique and strictly increasing time axis is
`source_epoch`, with `time_server` as its naive broker-wall-clock rendering.

The era-aware FivePercent UTC+2/+3 clock model provides `time_utc` and
`utc_offset_h`. If two distinct BTC source bars project onto one nominal UTC
at a continuous-market DST transition:

1. both source bars are retained;
2. `time_utc` is null for both rows;
3. `utc_ambiguous=true` for both rows;
4. `source_epoch`, `time_server`, prices and volumes remain unchanged;
5. every ambiguous group must contain exactly two rows, offsets `{2,3}`, and
   broker times exactly one hour apart.

The frozen expected ambiguity census is BTCUSD M1=170 rows, M5=56, H1=10,
H4=0; every other symbol/timeframe must have zero. Any census or pattern drift
fails closed. Research requiring exact UTC must exclude/resolve flagged rows;
server-time research can use the complete primary source axis.

Same-epoch source rows may be collapsed only when every source field is
identical. Any conflicting same-epoch value fails. Counts remain in manifest.

## Storage contract

Create new files only under:

`02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/`

Each symbol/timeframe gets one Parquet file with schema:

`symbol, timeframe, source_epoch, time_server, time_utc, utc_offset_h, utc_ambiguous, open, high, low, close, tick_volume, spread, real_volume`

The manifest binds all 20 files by path, bytes and SHA256, plus source/UTC
quality counts, coverage, gaps and zero-volume/spread counters. Large Parquet
files remain ignored by Git; durable receipts live in package evidence.

## Fail-closed gates

1. Plan, tool and tests are hash-bound by a one-use run authority.
2. Terminal binary, configuration, broker identity, D-drive paths, MaxBars and
   terminal-side trading state match the frozen contract.
3. All five symbol geometries and all twenty frames exist.
4. Exact source duplicates are value-equivalent before removal; conflicts fail.
5. Source epochs are unique and strictly increasing after reconciliation.
6. UTC nulls equal the ambiguity flag exactly and match the frozen census and
   two-row DST-transition pattern; non-null UTC is unique and increasing.
7. OHLC is positive/finite/consistent; volume and spread fields are nonnegative.
8. Only fully closed bars at/before cutoff are retained.
9. Output is create-new and every file is re-hashed before manifest/receipt.
10. Four protected C-drive roots have identical pre/post metadata digests.

Any failure is a data-setup blocker only, never a market no-edge verdict.

## Authority exclusions

- Orders submitted and trades simulated: 0.
- PnL, PF, WR, expectancy, MFE/MAE and optimization: forbidden.
- Promotion, paper/live authority and holdout selection: false.
- Tick volume/real volume/candle direction are not aggressor-side flow; no true
  CVD, VPIN or LOB OFI claim is authorized.
- T2 remains a separate nine-symbol no-skip Model-4/HQ>97 contract; this raw
  five-symbol corpus does not complete or partially unlock it.
