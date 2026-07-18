# READOUT — HYP-BR-SESSDRIFT-EURUSD-H1-001

Date: 2026-07-18 · Verdict: **KILL_AT_OFFLINE_PROBE** · No `.mq5`, no compile,
no Model 0, holdout 2023+ never loaded. Cost UNVERIFIED_PROXY;
`promotion_eligible=false`.

## Object

Breedon & Ranaldo (2013) intraday FX seasonality as a standalone unconditional
object (Owner-approved by name 2026-07-18; the one untested legal branch of
the MR v3 spec): daily SHORT EURUSD 07:00→11:00 UTC + LONG 13:00→17:00 UTC,
entry/exit at bar opens, R = 2×ATR14 of last closed bar, no signal, no
overnight, no swap. Frozen pre-outcome in `_PROBE_PLAN.md`
(SHA `8703E6A10139009AC9FD6372BAAC70B6375C95C36EECAFF23FF6B6D639EC04D8`);
contract tests 10/10; two simulated arms only (book_nostop primary, book_sl
secondary); trial N=2.

## Results (run `20260718_013918`, artifact SHA `90DF3AA5AB89E30CB4D4EC9C592BFE4399437C95E322F5EFB101CEFD0F86D3BE`)

| Arm | N | tpw | gross PF | PF@x1 | PF@x1.5 | PF@x2 | exp@x1 | pos years | conc | DSR |
|---|---|---|---|---|---|---|---|---|---|---|
| book_nostop | 4146 | 9.93 | 1.036 | 0.889 | 0.823 | 0.763 | −0.044R | 2/8 | 0.71 | 0.001 |
| book_sl | 4146 | 9.93 | 1.031 | 0.881 | 0.814 | 0.753 | −0.047R | 2/8 | 0.72 | 0.000 |

Partitions: short-window PF@x1 0.911/0.884, long-window 0.868/0.877 — neither
direction carries an edge. Gates: 6/8 economics checks failed in both arms
(only sample size and top-1 share passed).

## Interpretation

1. The residual drift is real but microscopic: gross PF 1.036 over 4146
   trades — an order of magnitude below what the 1.5-pip RT cost requires.
2. Decay is unambiguous: net@x1 by year = +21.8R (2015), −17.2, +8.7 (2017),
   then **five consecutive negative years 2018–2022** (−28.2, −51.1, −48.8,
   −37.8, −31.7). The B-R anomaly (sample 1997–2007) is gone in the modern
   sample, exactly as the spec's own decay warning predicted.
3. This closes the last untested branch of the Owner MR v3 spec. Every spec
   component is now evidence-terminal: Variant A killed (001), the full
   variant grid killed exhaustively (002), the B-R overlay killed standalone
   (this probe). Variant B (OB confluence) is moot — it is a filter on a dead
   base object and partially de-dups to killed FVG/OB lanes.

## Do-not-revive scope

Do not tune windows (any shift/local-time variant = the killed object),
directions, R normalization, or add conditioning (that becomes the killed
conditional London→NY family). Unconditional time-of-day drift on EURUSD is
terminal on 2015–2022 evidence. Reopen only with a materially different
information set + fresh Owner-scoped prereg.

## Artifacts

- Probe JSON: `evidence/20260718_013918_HYP_BR_SESSDRIFT_001_PROBE.json` (SHA above)
- Ledger: `evidence/20260718_013918_HYP_BR_SESSDRIFT_001_TRADES.csv`
  (SHA `551FABC3688E5A7A5B9BCA9951DB7E91F9FD40B1C2F5BB9EFDB5A13DF1937571`)
- Trial log: `trials/trial_log.jsonl` (2 rows) · Data: SHA-bound MR-lane
  EURUSD H1 parquet; holdout_bars_loaded=0 · No MT5 launch (pure parquet
  read); C roots untouched.
