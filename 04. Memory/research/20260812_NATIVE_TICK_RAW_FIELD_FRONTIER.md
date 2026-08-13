# FivePercent native tick raw-field frontier

Date: 2026-08-12  
Verdict: `NO_CANDIDATE_LOCAL_FRONTIER`

## Method and boundary

- Read-only `MetaTrader5.copy_ticks_range` calls against the configured
  `FivePercentOnline-Real` terminal.
- The diagnostic retained only row counts and presence counts for `last`,
  `volume`, `volume_real` and `TICK_FLAG_LAST/VOLUME/BUY/SELL`.
- No price value, return, target, PnL, direction or trade rule was inspected or
  persisted. No EA, hypothesis, order or economic run was opened.
- Git was not invoked and is outside this research lane.

## Cross-symbol current-day result

Window: `[2026-08-11T00:00:00Z, 2026-08-12T00:00:00Z)`.

| Symbol | Ticks | Nonzero last | Nonzero volume | Nonzero real volume | LAST flag | VOLUME flag | BUY flag | SELL flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 102,615 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| GBPUSD | 213,219 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| USDJPY | 189,154 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| XAUUSD | 1,392,859 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| BTCUSD | 787,448 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

EURUSD one-day samples in 2018, 2020, 2022 and 2024 likewise contained zero
nonzero `last`, `volume`, `volume_real` and zero BUY/SELL flags across 53,305 to
107,121 ticks per sampled day.

## De-dup closeout

- The native historical tick stream is quote-only for the fields needed to
  distinguish executed trade flow or aggressor side.
- The Bid/Ask quote-path object has already been killed by the valid HYP-QPF
  source gate, so renaming quote churn or broker tick counts does not create a
  new information family.
- The apparent HYP016 pressure-continuation control is not a survivor:
  `HYP-EURFXMOM-EURUSD-M1-005` later failed confirmatory validation with x1 PF
  `0.885041` and `0/9` economic gates.
- The live DOM capability is prospective-only and has no 2018-latest replay.

The same Grok Build session independently returned
`NO_CANDIDATE_LOCAL_FRONTIER`. Under the current local information set there is
no lawful new source-capability ID to mint. The active goal must move to a
materially new raw-data source with train/serve identity and 2018-latest replay,
not to another transformation of OHLC, tick volume or quote fields.

