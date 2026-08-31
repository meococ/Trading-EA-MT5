# Post-real-volume run-catalog reconciliation — 2026-08-13

## Verdict

`NO_LAWFUL_SURVIVOR / NO_MODEL0_AUTHORIZED / GOAL ACTIVE_UNMET`.

The refreshed AlphaFactory catalog contains no abandoned XAU/Forex M5/M15
candidate that can lawfully bypass fresh mechanism discovery. Headline profit
factor is a locator signal only; the original report, source contract, trial
history, OOS evidence and terminal family verdict remain authoritative.

No hypothesis, MQL5 source, compile, MT5 test, validation, holdout, paper trade
or live trade was opened by this reconciliation.

## Frozen scope and catalog identity

- Active symbols: `XAUUSD`, `EURUSD`, `USDJPY`, `GBPUSD`, `USDCHF`, `USDCAD`,
  `AUDUSD`, `NZDUSD`.
- Active decision periods: closed-bar `M5` or `M15` only.
- Catalog build result: 499 indexed run folders, 123 skipped, zero build errors.
- Catalog: `02. AlphaFactory/runs.db`.
- Catalog SHA-256:
  `D11D9B4E97545E81D4E89DEC7FEEF7BA13CC63C9E0B1C4FFADEB05B2A4A8CE49`.

The threshold is written explicitly because `> 200` and `>= 200` are not the
same query:

| Read-only locator query | Rows | Families | Interpretation |
|---|---:|---:|---|
| all symbols/periods, trades `> 200`, PF `> 1.30`, DD `< 8%` | 49 | 9 | Diagnostic query that excludes the 200-trade Gotobi row. |
| all symbols/periods, trades `>= 200`, PF `> 1.30`, DD `< 8%` | 50 | 10 | Broad catalog view; includes two off-contract false survivors. |
| active symbols plus M5/M15, trades `>= 200`, PF `> 1.30`, DD `< 8%` | 48 | 8 | Authoritative active-scope locator surface. |

The active-scope 48 rows belong only to `EA_Cobra`, `EA_ITSM`, `EA_Gotobi`,
`EA_ChopRegime`, `EA_VolCluster`, `EA_ShanghaiFixScalp`,
`EA_M15SparkAsian` and `EA_SilverBullet`. The exact family-level closeout is
already bound in
`04. Memory/research/20260812_RUN_CATALOG_NEAR_SURVIVOR_AUDIT.md` and
`04. Memory/research/20260813_XAU_FOREX_ONLY_SCOPE_AND_CATALOG_AUDIT.md`.

## Active-scope false-survivor decision

| Family | Why the headline catalog row cannot be revived |
|---|---|
| Cobra | Source/trial contaminated, equity concentrated, weekend heavy and overlaps terminal session/previous-day breakout families. |
| ITSM | Independent FivePercent baselines, WFA and concentration evidence ended in `KILL_NO_REVIVAL`; the attractive row is selected from a sweep. |
| Gotobi | The timezone-corrected treatment failed; the one boundary row has exactly 200 trades and is not a new independent result. |
| ChopRegime | A FivePercent headline PF does not erase selection debt from session/day sweeps; untouched 2018–2020 OOS was approximately PF 1.03, so the family is terminal. |
| VolCluster | No auditable source/cost identity and terminal latest-OOS evidence. |
| ShanghaiFixScalp | No auditable source/cost identity, zero-commission concern and WFA 1/5. |
| M15SparkAsian | Part of the terminal Spark family; independent runner evidence did not clear the PF gate. |
| SilverBullet | Archived/binary-only, trial contaminated and failed FivePercent broker transfer near PF 1.00. |

Relaxing cadence, selecting a sibling timestamp or pointing at a different
broker header would be post-hoc family revival, not new evidence.

## Why the broad catalog has two extra rows

### `EA_EventAggressorFlow/20260812_184117`

This row is `EURUSD M1`, outside the active closed-M5/M15 contract. Its frozen
exact mapping is also terminal on its own terms: top-5%-gross-profit
concentration was `32.4011%`, above the frozen `30%` cap. It cannot be promoted
or remapped after that readout.

Report SHA-256:
`A359ABEE5B185F59F7B36982EDA7A41E2EC10A8A24722DF371F4C07750377EE0`.

### `EA_MultiAssetTSMOMD1V6/20260812_110939`

This row is a custom-symbol `H1` test, outside the active contract. The apparent
PF `1.4033` is engineering-invalid because currency parsing produced zero FX
PnL/spread telemetry. The corrected native run `20260812_113422` returned PF
`0.4853467684`, net `-USD 7,708.23`, expectancy about `-USD 18.01/trade` and
zero positive years out of four. The bugged row cannot be used as economics.

Report SHA-256 values:

- invalid custom-symbol run:
  `61A9B52D9E9262E39101DEA34612DB2F0E430E0C1A0CA8F906692312A2E0FFB0`;
- corrected native run:
  `B14AF2C0AE084323FD547ED97646635E85B82F1388D1319C1497A6C54DCA45A9`.

## Alternate installed MT5 source decision

The separate MetaQuotes-Demo terminal exposes variable live DOM sizes, unlike
the FivePercent placeholder field, but it cannot supply the required historical
DOM replay and is not the intended deployment venue. Training on its future
collection would break source identity at serve time. No collector, hypothesis
or EA was opened from that terminal.

The alternate terminal is therefore `REJECT_ALTERNATE_MT5_SOURCE` for the
current goal. It can reopen only if Owner changes the intended venue/evidence
window, or the intended deploy venue supplies documented varying sizes plus a
replayable archive.

## Lead decision

There is no lawful survivor to compile or run. Building any catalog family now
would either repeat a terminal family, exploit an engineering-invalid headline,
change the decision timeframe after the result, or train on a source that cannot
serve at the intended venue.

Continue the active goal with one materially fresh, outcome-blind XAU/Forex
information object. Freeze its own source identity, cadence, cost, symbol,
timeframe and OOS boundaries before opening prices or economics. Paid data and
services remain unauthorized.

## Authority hashes

- `04. Memory/research/20260813_XAU_FOREX_ONLY_SCOPE_AND_CATALOG_AUDIT.md`:
  `A11B7BC856B81A75B7AD394D5A336503F803E4635A8D40C99E5A2C425E27F894`.
- `04. Memory/research/20260812_RUN_CATALOG_NEAR_SURVIVOR_AUDIT.md`:
  `F2F1D2930603391575B0476704D414288F4B845D632E20348CC2629395C1A238`.
- Representative FivePercent ChopRegime report
  `EA_ChopRegime/20260702_230323`:
  `AE81CAA5759D7C50A1FACEDADD076062D77EBEA9EE8C80C7F1A2DE4EC9F88BC3`.
