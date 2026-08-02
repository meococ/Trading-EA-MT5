# DATA-FIVEPERCENT-5ASSET-MULTITF-004 Readout

Verdict: `ENGINEERING_VALID_RAW_DATA_COMPLETE`.

The FivePercent demo terminal produced a complete five-symbol, four-timeframe
offline corpus on `D:`. All 20 Parquet hashes reconcile to the manifest and the
four protected C-drive metadata roots are unchanged.

## Delivered coverage

| Symbol | M1 | M5 | H1 | H4 | Total rows |
|---|---:|---:|---:|---:|---:|
| EURUSD | 9,998,253 | 2,051,478 | 178,454 | 50,121 | 12,278,306 |
| USDJPY | 9,955,862 | 2,050,231 | 178,364 | 50,113 | 12,234,570 |
| GBPUSD | 9,846,543 | 2,038,395 | 172,681 | 44,423 | 12,102,042 |
| XAUUSD | 7,004,938 | 1,486,346 | 128,878 | 33,916 | 8,654,078 |
| BTCUSD | 2,368,383 | 594,886 | 64,360 | 17,443 | 3,045,072 |
| **Total** | **39,173,979** | **8,221,336** | **722,737** | **196,016** | **48,314,068** |

- Parquet payload: 1,206,400,142 bytes.
- Cutoff: `2026-08-01T23:59:59Z`.
- Source: `FivePercentOnline-Real`, company `Five Percent Online Ltd`, demo
  account, portable terminal build 6090, `MaxBars=20,000,000`.
- Terminal-side trading during export: false.
- Orders/trades/outcomes/economics: 0 / 0 / none / not executed.

## Data-quality decisions

- Nine exact source copies were removed only after all source fields matched:
  GBPUSD M1=2, XAUUSD M1=3, BTCUSD M1=4.
- No conflicting same-epoch source bars were accepted.
- BTCUSD contains 236 retained rows at continuous-market DST transitions where
  the EURUSD-verified broker clock creates 118 duplicate nominal UTC groups:
  M1=170 rows, M5=56, H1=10, H4=0.
- Those BTC rows remain complete on `source_epoch/time_server`; `time_utc` is
  null and `utc_ambiguous=true`. No arbitrary shift, deletion or fake UTC was
  used.
- All other non-null UTC values are unique and increasing.

## Execution history

- Dataset 001 stopped before its first file on an oversized single M1 request.
- Dataset 002 used bounded chunks but stopped on an exact GBPUSD triplicate;
  its eight partial files are inventoried and explicitly unpublished.
- Dataset 003 stopped in preflight before authority after detecting that BTC
  DST collisions were different bars, not duplicates.
- Dataset 004 passed the complete 20-frame preflight. Export and manifest
  completed; receipt rendering alone failed on an unresolved relative path.
  A hash-bound finalize-only tool re-hashed all files and created the missing
  receipt without starting MT5 or rewriting data/manifest.

## Canonical evidence

- Manifest:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`
  (`SHA256 D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`).
- Export receipt:
  `research/evidence/DATA-FIVEPERCENT-5ASSET-MULTITF-004/export_receipt.json`
  (`SHA256 6AA144D4EDA78C213C904BB6797FFE6E65283F74ABD2A06B782E01E30F8872FF`).
- Protected-C reconciliation:
  `research/evidence/DATA-FIVEPERCENT-5ASSET-MULTITF-004/storage_reconciliation.json`
  (`protected_c_roots_unchanged=true`).

Economic-valid and promotion-ready remain false/unassessed. This is a reusable
raw-data shelf, not evidence of a profitable strategy or completion of T2.
