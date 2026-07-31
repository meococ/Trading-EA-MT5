# HYP-EURFXOFI-EURUSD-M1-012 — Outcome-blind TBBO aggressor classifier

## Why this is a fresh mechanism

- HYP011 established that the exact 1,359-date corpus and `ts_recv` clock are valid, but direct Databento `side` labels classify only 71.587052% of aggressive volume and 87.294469% of populated windows. Frozen gates were 95% and 99%; they are not lowered.
- HYP011 read no EURUSD target or PnL. HYP012 changes only the source-side classifier using the pre-trade BBO already carried by each TBBO record.
- HYP011 source summary SHA256: `309D0B87A1CBEC06274D39B808DCF9325232463C834A5AAD636DB29F`.
- HYP011 terminal SHA256: `64E93D4CF0A4500095969818F4B3775B15224E52300B9C5952FFE19CED6EF3CE`.
- Parent raw manifest SHA256: `C2FA31D39970200DD05AF35A3E23BAE3941F1083BE870D77A4A24E4A709DF820`.

## Exact corpus and clock

- `GLBX.MDP3` / `tbbo` / `6E.v.0`, 2016-01-01 through 2026-07-29.
- TRAIN 630, VALIDATION 526, HOLDOUT 203 source dates; outcomes remain sealed.
- Exact availability: 1,338 positive DBNs, 18 paid zero-record DBNs, three live-quote no-file dates.
- `ts_recv` is the inclusive-start/exclusive-end membership, stable ordering and three 5-second bin clock. `ts_event` remains diagnostic only.

## Frozen causal, no-lookahead classifier

Each positive window is sorted by `ts_recv`. State is reset at the start of every 15-second window.

1. Trust direct Databento `side=B|A` as buy/sell aggressor.
2. For `side=N` with a valid, non-crossed pre-trade BBO:
   - trade price `>= ask` → buy;
   - trade price `<= bid` → sell;
   - otherwise price `> midpoint` → buy, price `< midpoint` → sell.
3. If price equals midpoint or the BBO is unavailable, use the sequential tick rule:
   - price above the previous trade → buy;
   - price below the previous trade → sell;
   - unchanged price carries the last classified direction within the same window only.
4. A first unresolved trade, or an unchanged trade with no prior classified direction, remains unknown.
5. No next trade, later bar, later date, target return, validation or holdout outcome may influence classification.

Aggressive signed size is `buy=+size`, `sell=-size`, residual unknown `=0`. Direct, quote-at-touch, midpoint, tick and residual volume/counts are recorded separately.

## Unchanged source gates and outputs

- Exact 1,359/1,338/18/3 cardinalities, 34,838 records and zero `ts_recv` outside records.
- Classified populated-window ratio `>= 99%` and classified aggressive-volume ratio `>= 95%`; these are the same gates HYP011 failed.
- No crossed book records, no negative size, exact DBN bytes/SHA/counts and explicit empty provenance.
- `source_features.parquet`, `source_quality_summary.json`, readout, five PNGs and hash-bound artifact/evidence manifests.
- Charts: yearly coverage, quality distributions, signed flow by sealed split, three-bin anatomy, and classifier-method/residual diagnostics.

## One-shot authority and prohibitions

- Attempt ID: `EURFXOFI012-SOURCE-CLASSIFIER-001`; one local run after review/sentinel binding.
- No network and no new paid request; the Owner USD2.25 ceiling is not reopened.
- No EURUSD post-entry price, return, PF, drawdown, DSR, validation, holdout, MT5, MQL5, Model 0, optimization, paper or live trading.
- PASS permits only a fresh TRAIN-only economics hypothesis using exact HYP012 feature/summary/manifest hashes. FAIL closes this classifier without threshold rescue.
