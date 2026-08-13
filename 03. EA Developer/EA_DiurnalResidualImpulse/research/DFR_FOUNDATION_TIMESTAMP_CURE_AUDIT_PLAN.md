# DFR Foundation timestamp-cure audit plan

Audit ID: `DFR-FOUNDATION-TIMESTAMP-CURE-001`

Status: `FROZEN_PRE_READ_CAPABILITY_ONLY`

## Question

Does the already-local, hash-bound FiveAssetFoundation EURUSD M5 timestamp plane independently cure the exact source-executable horizon failure of terminal `HYP-DFR-IC-EURUSD-M15-001` without changing its signal IDs, thresholds, session, lifecycle, or reading any price outcome?

This audit is not a hypothesis, source rerun, economics attempt, MQL5/MT5 authorization, or permission to revive HYP001. A pass only establishes independent data-cure evidence for a separately reviewed child decision.

## Frozen inputs

- HYP001 source classifications: `research/evidence/HYP-DFR-IC-EURUSD-M15-001_SOURCE_FEASIBILITY/DFRIC001-SOURCE-001/dfr_ic_001_source_classifications.jsonl`
- Classification SHA-256: `E5AF87FE704DBA1114C89D1422DD016DBFB25F41DA442B8786CF26216CAAE8AC`
- Expected classifications: 1,235; old `SOURCE_EXECUTABLE`: 1,220; old `HORIZON_INCOMPLETE`: 15.
- Foundation Parquet: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet`
- Foundation SHA-256: `6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8`

## Frozen method

1. Decode from classifications only `source_signal_id`, `decision_utc`, `entry_open_utc`, and old status.
2. Decode from Parquet only `symbol`, `timeframe`, `time_utc`, and `utc_ambiguous`. Price, spread, volume, return, and trade fields are forbidden.
3. Select normalized UTC timestamps from `2015-01-01T00:00:00Z` inclusive to `2021-01-01T00:00:00Z` exclusive.
4. A derived M15 timestamp exists only when the M5 timestamp group contains exactly offsets 0, 5, and 10 minutes with no duplicate.
5. For each frozen HYP001 signal, require six consecutive derived M15 starts beginning at its frozen `entry_open_utc`.
6. Report old incomplete signals recovered, old executable signals retained, new incomplete IDs, and total coverage. Never calculate a signal, return, trade, PnL, PF, drawdown, or price feature.

## Frozen capability gates

- Exactly 1,235 unique frozen signal IDs are evaluated.
- New six-M15 horizon coverage is at least 99.0%.
- At least 99.0% of the 1,220 old executable signals remain horizon-complete.
- At least one of the 15 old incomplete signals is recovered.
- Zero ambiguous UTC rows; deterministic replay produces identical canonical output.
- All forbidden counters remain zero.

Verdicts:

- All pass: `PASS_INDEPENDENT_TIMESTAMP_CURE_EVIDENCE_ONLY`.
- Otherwise: `NO_DFR_REOPENABLE_TIMESTAMP_CURE`.

Neither verdict opens outcomes. A later child remains prohibited unless Lead also proves information-family de-dup, a causal case, a clean source-to-MT5 parity contract, and fresh pre-outcome authority.
