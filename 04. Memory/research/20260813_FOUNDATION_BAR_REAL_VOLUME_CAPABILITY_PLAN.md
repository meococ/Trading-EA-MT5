# Foundation M5 bar `real_volume` capability audit — frozen plan

Audit ID: `BAR-REAL-VOLUME-CAPABILITY-001`  
Frozen: 2026-08-13 before any row-level `real_volume` or `tick_volume` read.

## Trigger and epistemic boundary

A schema/Parquet-footer-only preflight found that the FiveAssetFoundation M5
files contain a `real_volume uint64` column whose footer maximum is nonzero for
EURUSD, GBPUSD, USDJPY and XAUUSD. This contradicts the current frontier summary
that treated the local bar surface as only OHLC/spread/tick-volume/time.

The preflight opened only file paths, schemas, row counts and footer min/max/null
statistics. It did not read a parquet data row, price, direction, return,
post-decision field, target, trade or economic metric.

This audit asks only whether `real_volume` is a durable, recent, nontrivial
broker-bar payload with 2018-latest coverage, and whether it is trivially
identical to `tick_volume`. It cannot prove centralized executed volume,
aggressor side, causal direction or edge. It authorizes no hypothesis ID, signal
mapping, outcome access, MQL5, MT5 run, optimization, validation, paper or live
use.

## Immutable inputs

Read exactly `time_utc`, `tick_volume` and `real_volume` from these M5 files:

| Symbol | Relative path | SHA256 |
|---|---|---|
| EURUSD | `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet` | `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8` |
| GBPUSD | `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/GBPUSD/GBPUSD_M5_ALL_AVAILABLE_20260801.parquet` | `8EE2720261FC05A13A2E919C3EAA4FF50EEF75F9CB068519C61C48BB3D6B4F4B` |
| USDJPY | `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/USDJPY/USDJPY_M5_ALL_AVAILABLE_20260801.parquet` | `FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD` |
| XAUUSD | `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet` | `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380` |

Frozen measurement window is `[2018-01-01T00:00:00Z,
2026-08-01T00:00:00Z)`. Recent-serve proxy is the fixed final 31 calendar days
`[2026-07-01T00:00:00Z, 2026-08-01T00:00:00Z)`.

The prior native-tick receipt
`04. Memory/research/20260812_NATIVE_TICK_RAW_FIELD_FRONTIER.md` is a fixed
adverse provenance fact: sampled ticks have zero `volume_real` and zero
LAST/VOLUME/BUY/SELL flags. This audit must not overwrite that fact.

## Exact measurements

For each symbol and for every UTC calendar year in the window, persist only:

- row count, nonzero/zero `real_volume` counts and nonzero share;
- positive `real_volume` minimum, maximum, integer GCD and distinct count;
- exact `real_volume == tick_volume` count/share;
- Pearson correlation between positive `real_volume` and `tick_volume`;
- first and last UTC timestamps with positive `real_volume`;
- the same counts for the frozen recent-serve window.

No OHLC or spread column may be requested. No sign, return, event, target or
trade may be calculated. Output may contain no per-row payload.

## Frozen gates

Payload capability passes only if all four symbols satisfy all of the following:

1. Every UTC year 2018..2026 has at least one row and `real_volume > 0` on at
   least `95%` of rows.
2. The recent-serve window has at least 1,000 rows and nonzero share at least
   `95%`.
3. Recent positive `real_volume` has at least 100 distinct values.
4. Across the full window, exact equality with `tick_volume` is below `99%`.
5. All hashes match, timestamps are finite and every counter is internally
   reconciled.

Even a payload PASS remains `BROKER_BAR_PAYLOAD_ONLY_NO_TRADE_PROVENANCE`. The
field can become a hypothesis source only after a separate primary provenance
or train/serve identity audit explains how bar `real_volume` exists while the
same broker's tick tape has no trade-volume fields. Without that evidence the
causal-source verdict is `KILL_REAL_VOLUME_PROVENANCE_UNRECONCILED`.

## Output and one-shot rule

Implementation:
`04. Memory/research/audit_foundation_bar_real_volume.py`  
Tests:
`04. Memory/research/tests/test_audit_foundation_bar_real_volume.py`  
Create-new evidence root:
`04. Memory/research/evidence/BAR-REAL-VOLUME-CAPABILITY-001/`

The evidence root may be created exactly once by `--execute`. A failure after
row access is terminal for this audit ID. A pre-read binding or implementation
failure may be corrected only before the evidence root exists and must be
reported separately.
