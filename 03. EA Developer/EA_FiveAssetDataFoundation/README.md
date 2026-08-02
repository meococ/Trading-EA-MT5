# EA Five-Asset Data Foundation

Status: `ENGINEERING_VALID_RAW_DATA_COMPLETE` for dataset
`DATA-FIVEPERCENT-5ASSET-MULTITF-004`.

This package records the zero-trade FivePercent demo-data setup requested for:

`EURUSD, USDJPY, GBPUSD, XAUUSD, BTCUSD`

Owner spellings `JPYUSD` and `GPBUSD` are normalized to the broker symbols
`USDJPY` and `GBPUSD`. The native timeframes are `M1, M5, H1, H4`, with a
frozen cutoff of `2026-08-01T23:59:59Z`.

## Canonical artifacts

- Data root:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/`
- Hash-bound manifest: `manifest.json` inside that root.
- Completion receipt:
  `research/evidence/DATA-FIVEPERCENT-5ASSET-MULTITF-004/export_receipt.json`
- Owner-facing technical readout:
  `research/DATA-FIVEPERCENT-5ASSET-MULTITF-004_READOUT.md`

The 20 Parquet files contain 48,314,068 rows and 1,206,400,142 compressed
bytes. They are local D-drive data and intentionally ignored by Git; the
manifest and evidence receipts are tracked.

## Time-axis rule

Use `source_epoch` (or its broker-wall rendering `time_server`) as the complete,
unique primary ordering key. `time_utc` is available when the broker clock maps
unambiguously. For 236 continuous-market BTC rows at DST transitions,
`time_utc` is null and `utc_ambiguous=true`; no bar was deleted or assigned a
fabricated UTC. Research requiring exact UTC must exclude or independently
resolve those flagged rows.

Exact same-epoch rows are removed only when every source field is identical.
The manifest records nine such removed copies and zero conflicting source
duplicate groups.

## Authority boundary

This package proves only an offline raw broker-bar foundation. It does not
measure MT5 tester History Quality, profitability, expectancy, spread-cost
truth, true aggressor-side volume, CVD, VPIN, LOB OFI, or promotion readiness.
It does not satisfy or partially unlock the separate nine-symbol T2 contract.
