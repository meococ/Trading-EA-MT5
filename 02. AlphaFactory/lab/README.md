# lab/ — research factory (replaces artisanal probe scripts)

Why this exists: the campaign was running one hand-written probe per
hypothesis — serial, unreproducible, no multiple-testing control, and (the
RGR lesson) able to produce confident "edges" from a measurement plane that
was never validated against tradable prices. The lab is the systematic
replacement: a canonical data plane, a vectorized feature/label library, a
sweep engine that stores EVERY cell including negatives, and statistical
gates before anything reaches preregistration.

## Layering (data flows down only)

```
etl.py        .hcc -> cache/<SYM>_M1_2010_2026.parquet (+suspect flags)
data_plane.py canonical load(); pip_size(); SYMBOLS
features.py   vectorized event detectors -> bool masks / float series
labels.py     next-bar-open path sim -> per-trade ret/exit/MAE/MFE
stats.py      welch-t, BH-FDR, split-half, per-year stability
sweep.py      cell defs -> lab.duckdb `results` (dedup by cell hash)
mine.py       family grids -> thousands of cells per run
model.py      HGB classifier, purged+embargoed walk-forward CV
```

## Rules (binding, same authority as /loop)

- Signal bar t decides; entry at open of t+1. Intrabar SL beats TP on
  ambiguity (conservative = tester-pessimistic).
- `suspect=True` regions are void: events whose entry bar OR hold window
  touches them are dropped and counted (`dropped_*` columns).
- Event-level discipline: every event mask passes a cooldown so one market
  move is never counted as N overlapping events (the tranche bug).
- Multiple testing: no cell is "an anomaly" unless q_val survives BH-FDR
  AND split-half same-sign AND pos_year_frac >= 0.6 AND t >= 2.8.
- cost_rt=1.0 pip baked into every label already; governed-discount rule
  still applies before prereg (fade-side needs another -1..3p discount).
- lab.duckdb results table is the falsification ledger. Never delete rows.

## Usage

```
python etl.py [SYMS...]          # rebuild cache (once, ~10 min)
python mine.py [families] [SYMS] # e.g. python mine.py impulse_cont EURUSD
python model.py [SYMS]           # direction model w/ purged CV
```

Query survivors:

```sql
SELECT symbol, params_json, n_kept, mean_p, t_stat, q_val, pf
FROM results WHERE q_val < 0.05 AND pos_year_frac > 0.6
ORDER BY t_stat DESC;
```
