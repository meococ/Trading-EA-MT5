# HYP-PTR-T2-DATA-EPOCH-D0-M5-001 Preregistration

Status: frozen pre-outcome D0 data-epoch ceremony.

## Identity

- Hypothesis ID: `HYP-PTR-T2-DATA-EPOCH-D0-M5-001`
- EA: `EA_PTR_T2_DataEpochD0`
- Source SHA256:
  `E0D5662F207ACE9D92FDE50E864F2C9A4FA5D9BD5DF4DC840C6BC1DC7D0307E2`
- EA contract SHA256:
  `974EE2B3D642805C552B6FCB27E6238CE6D4E1340B98FDC44562A02EE96DA969`
- Epoch contract SHA256:
  `F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648`

## Frozen Data-Epoch Contract

- Server: `FivePercentOnline-Real`
- Timeframe: `M5`
- Tester model: `0`
- From: `1970.01.01`
- To: `2026.07.30`
- Availability cutoff: `2026-07-30T23:59:59Z`
- History Quality gate: strictly greater than `97.0`
- Mandatory symbols, exact order:
  `XAUUSD`, `BTCUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`,
  `AUDUSD`, `NZDUSD`

## Authority

The only authorized run class is `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`.
The run role is `control` and the EA telemetry profile is `none`.

Authorized observations:
- Strategy Tester report identity and History Quality.
- Run manifest identity, data-quality contract, data-quality gate, journal
  bounds, and data-quality fingerprint.
- Zero-trade summary proving `n_trades=0` and
  `performance_metrics_authorized=false`.

Forbidden observations:
- Profit factor, win rate, expectancy, drawdown, equity, balance, trade result,
  stop/target result, or any other economic/performance metric.
- Optimization, parameter tuning, validation, holdout, promotion, paper trading,
  or live trading.

## Acceptance Before Ledger Append

`append_t2_data_epoch_evidence.py` may append one selected PASS row for a symbol
only when all checks pass:

- Symbol is one of the exact mandatory nine symbols.
- `run_manifest.json` is `alphafactory_run_manifest.v2`, `M5`, Model 0,
  `1970.01.01` to `2026.07.30`.
- `data_quality_contract` matches the epoch contract exactly.
- `data_quality_gate.history_quality` is strictly greater than `97.0`.
- `data_quality_gate.actual_to` equals `2026.07.30`.
- `contract_receipt_sha256` and `report_sha256` match the referenced files.
- Receipt authority is `DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE`.
- Zero-trade summary has exactly the authorized zero-trade schema and no
  performance metrics authorization.
- The evidence ledger has no prior selected PASS row for the same symbol.

Completion of 9/9 data evidence is a data-quality gate only. It does not
evaluate edge and does not authorize economic claims.
