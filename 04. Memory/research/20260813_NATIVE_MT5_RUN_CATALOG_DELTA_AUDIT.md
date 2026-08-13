# Native MT5 run-catalog delta audit

Date: 2026-08-13

Verdict: `NO_NATIVE_CANDIDATE_CURRENT_FRONTIER`

Overall goal: `ACTIVE / UNMET`

This is a database-first reuse and delta audit. It did not authorize or open a
hypothesis, price outcome, EA edit, compile, MT5 run, optimization, purchase,
paper trade or live trade.

## Current catalog receipt

The AlphaFactory run catalog was rebuilt from the current filesystem:

- run folders discovered: `627`;
- rows indexed: `504`;
- folders skipped by the indexer: `123`;
- index errors: `0`;
- rows with comparable metrics in the summary: `482` across `128` EA names.

The discovery query `PF > 1.3 AND DD < 8 AND trades > 200` returned `49` rows.
Those rows are not 49 independent candidates. They collapse mainly into the
legacy Cobra, ITSM, ChopRegime, SilverBullet, VolCluster, ShanghaiFix and
related campaign families.

## Why the historical leaders do not reopen

The authoritative artifact review in
`20260812_RUN_CATALOG_NEAR_SURVIVOR_AUDIT.md` already classifies the legacy
leaders as terminal or inadmissible. The current delta confirms the same
boundary:

- many old source files are absent from the canonical EA shelf, so the exact
  source/non-repaint identity cannot be reproduced;
- the June campaign contains many same-day EA/config trials without a bound
  pre-outcome hypothesis or multiple-trial correction;
- the legacy cost artifacts subtract an arbitrary USD `0.50` per trade while
  recording spread, slippage and commission as zero;
- the generic `validate-full PASS` means the analyzers executed, not that
  economic or promotion gates passed.

Representative artifact checks:

- `EA_Cobra/20260621_173025`: PF `1.5983`, 210 trades, but equity audit `FAIL`,
  top-5% trades contribute `61.0%`, longest flat period `725` days, monthly
  return assessment `0.1346%` and cost inputs are unbound zeros.
- `EA_ITSM/20260621_172759`: PF `1.5778`, 363 trades, but only three of five OOS
  WFA windows are profitable, top-5% trades contribute `70.1%`, longest flat
  period `495` days and the same zero-input cost proxy is used. The specific
  family authority is `KILL_NO_REVIVAL` in
  `20260812_ITSM_SONIC_USDJPY_REVIVAL_AUDIT.md`.
- `EA_LondonNY/20260621_173121`: PF `2.0950` but only 112 trades over eight
  years, one of five OOS windows is not profitable, robustness is 6/7, the
  source is absent from the canonical shelf and costs are the same unbound
  report-only proxy.

No historical high-PF row can be promoted, copied or rebuilt from these
reports. A new run of the same logic with changed hours, weekdays, thresholds,
SL/TP, sizing, symbol or timeframe would be post-outcome revival.

## Filesystem delta after the prior shelf snapshot

The only five run directories dated 2026-08-13 are:

- `EA_DOLUISeasonalResidual/20260813_094716`;
- `EA_DOLUISeasonalResidual/20260813_094909`;
- `EA_EventDepthTransfer/20260813_104115`;
- `EA_EventDepthTransfer/20260813_104643`;
- `EA_EventDepthTransfer/20260813_104719`.

Their current registry descendants are terminal:

- DOLUI primary base PF `1.0118`, x1.5 PF `0.9743`, x2 PF `0.9381`; the reverse
  was inferior. Verdict `KILL_FROZEN_MAPPING`.
- EventDepthTransfer primary PF `0.9147` with negative expectancy; reverse PF
  `0.3846`. Verdict `KILL_FROZEN_MAPPING_FINAL_AUTHORITY`.

Thus the current catalog delta contains no new near-survivor.

## Native information-object frontier

The current FivePercent MT5 surface provides price/OHLC, indicator transforms,
ticks, tick volume, spread, server/session clocks, MarketBook sentinel ladders
and the MT5 calendar. Each is already inside a closed family radius documented
by the broker/external shelf audit and failure catalog. Renaming or reclocking
one of those fields does not create a new information object.

Grok Build was given only the current counts, terminal lineages and native
field inventory. It returned `NO_NATIVE_CANDIDATE`, citing the same de-dup
boundary. Lead accepts the result because it matches the local artifacts; Grok
is advisory and did not supply market evidence.

## Verdict boundary and next gate

`NO_NATIVE_CANDIDATE_CURRENT_FRONTIER` closes only the present local/native
reuse search. It does not close the overall EA goal.

The highest-information surviving object is the non-native CLS institutional
fund-flow source gate. Its exact R2 inquiry is ready but vendor contact still
requires explicit Owner authority. A reply remains metadata and must pass the
frozen fifteen-gate intake contract before any hypothesis, code or MT5 run.

