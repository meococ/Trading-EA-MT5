# HYP-PTR-T2-DATA-EPOCH-D0-M5-003 Preregistration

## Identity

- Hypothesis ID: `HYP-PTR-T2-DATA-EPOCH-D0-M5-003`
- EA name: `EA_PTR_T2_DataEpochD0V3`
- Mechanism scope: T2 D0 data-epoch acquisition with corrected first-available-bar CopyTime provenance
- Authority: `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`
- Parent context: `CAMPAIGN-PTR-E01/T2 data epoch`
- Status before any HYP003 packet/run: screened, not run

## Frozen Data Contract

- Server: `FivePercentOnline-Real`
- Symbols: `XAUUSD`, `BTCUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`, `AUDUSD`, `NZDUSD`
- Timeframe: `M5`
- Tester model: `0`
- From: `1970.01.01`
- To: `2026.07.30`
- Availability cutoff UTC: `2026-07-30T23:59:59Z`
- Required History Quality: `>97.0`
- Epoch manifest path: `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json`
- Epoch manifest SHA256: `F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648`

## Source Binding

- Canonical source path: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/EA_PTR_T2_DataEpochD0V3.mq5`
- Source SHA256: `EB9273BC7F1E0A5C7DB420916EC43CA3EE2A9BAE932D9C2101E4B85058FED70F`
- EA contract path: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/ALPHAFACTORY_EA_CONTRACT.json`
- EA contract SHA256: `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`
- Collection-only cost manifest path: `03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/COLLECTION_ONLY_COST_SOURCE_MANIFEST.json`

## Corrected Series Proof Gate

`OnInit` must emit exactly one machine-parseable `DATA_EPOCH_D0_SERIES_PROOF` marker after all required core calls succeed and before `DATA_EPOCH_D0_READY`.

Required fields:

`symbol`, `m5_synchronized`, `m5_first_epoch`, `m5_terminal_first_epoch`, `m1_server_first_epoch`, `m1_terminal_first_epoch`, `m5_bars`, `terminal_maxbars`, `copytime_from_epoch`, `copytime_count`, `copytime_result`, `copytime_first_epoch`, `copytime_last_error`.

Frozen correction versus HYP002:

- `copytime_from_epoch == m5_first_epoch`
- `copytime_result == 1`
- `copytime_last_error == 0`
- `copytime_first_epoch == m5_first_epoch`

The datetime-zero CopyTime request from HYP002 is engineering-invalid and is not reused here.

Future `run_manifest.data_quality_gate.coverage_class` must be either:

- `FULL_2018_PLUS`
- `BROKER_LIMITED_START`

`INVALID_TRUNCATED_TERMINAL_CACHE` is rejected.

The V3 appender includes both `coverage_class` and `series_proof` in the data-quality fingerprint basis.

## Explicit Non-Authority

No trades, PF, WR, expectancy, optimization, validation, holdout, promotion, paper trading, or live trading is authorized by this prereg. The only eligible future action is creation of reviewed task packets and receipts for data acquisition under the frozen nine-symbol D0 contract.
