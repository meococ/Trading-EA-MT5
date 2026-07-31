# HYP-PTR-T2-DATA-EPOCH-D0-M5-001 Prereg Amendment V2

## Authority

- Amendment type: PRE_OUTCOME_SECOND_SOURCE_DATA_PROVENANCE
- Authority: DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE
- Economics authorized: false
- Performance metrics authorized: false
- Trading mutation authorized: false
- Task packets created by this amendment: false
- MT5 backtest/run authorized by this amendment: false

## Frozen Base

- Base prereg path: `03. EA Developer/EA_PTR_T2_DataEpochD0/research/HYP-PTR-T2-DATA-EPOCH-D0-M5-001_PREREG.md`
- Base prereg SHA256: `E2E8E2B1FB75F5E9FD98E3EF8F0AD9501E78825208077D8F08852E740F7BD1E0`
- Epoch manifest path: `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json`
- Epoch manifest SHA256: `F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648`
- EA contract path: `03. EA Developer/EA_PTR_T2_DataEpochD0/ALPHAFACTORY_EA_CONTRACT.json`
- EA contract SHA256: `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`

## Source Amendment

- Canonical source path: `03. EA Developer/EA_PTR_T2_DataEpochD0/EA_PTR_T2_DataEpochD0.mq5`
- Prior prereg-bound source SHA256: `E0D5662F207ACE9D92FDE50E864F2C9A4FA5D9BD5DF4DC840C6BC1DC7D0307E2`
- V2 source SHA256: `0CBE31DAF3CA1BE9BDA971E080D48FB80C654DC4E3D3B3B5748B10A65CD12E25`
- Change surface: one `DATA_EPOCH_D0_SERIES_PROOF` marker emitted during `OnInit` after required series calls are valid.
- Fail-closed additions: `OnInit` fails when required `SeriesInfoInteger` calls fail, M5 is not synchronized, terminal max bars is invalid, or `CopyTime(_Symbol, PERIOD_M5, 1970.01.01, 1, ...)` does not return exactly one bar without error.

## Exact Series Proof Fields

Future collection run manifests must preserve the machine-parsed proof under `run_manifest.data_quality_gate.series_proof` with exactly these fields:

`symbol`, `m5_synchronized`, `m5_first_epoch`, `m5_terminal_first_epoch`, `m1_server_first_epoch`, `m1_terminal_first_epoch`, `m5_bars`, `terminal_maxbars`, `copytime_from_epoch`, `copytime_count`, `copytime_result`, `copytime_first_epoch`, `copytime_last_error`.

Allowed `run_manifest.data_quality_gate.coverage_class` values:

- `FULL_2018_PLUS`
- `BROKER_LIMITED_START`

Rejected value:

- `INVALID_TRUNCATED_TERMINAL_CACHE`

## Appender Binding

- Ledger appender path: `03. EA Developer/EA_PTR_T2_DataEpochD0/research/append_t2_data_epoch_evidence.py`
- Ledger appender SHA256: `5D6097794E0D512CCCB6088A626232F21539CE3E6B52390B08851BD6D67D9E98`
- Ledger appender test path: `03. EA Developer/EA_PTR_T2_DataEpochD0/research/tests/test_append_t2_data_epoch_evidence.py`
- Ledger appender test SHA256: `49C0A473C3E0A7910E5F6184703377AE30D3BB7045B680E724CBA2CEAA35B9DC`

## Non-Changes

This V2 amendment does not change the nine-symbol universe, timeframe, model, date range, History Quality threshold, no-trade EA contract, cost-source authority, or any acceptance economics. It only adds a second-source provenance proof for terminal/server history availability before a future data-acquisition packet can be created.
