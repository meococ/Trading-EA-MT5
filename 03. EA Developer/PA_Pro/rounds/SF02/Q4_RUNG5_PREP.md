# Q4 — Rung-5 prep: data availability + cost evidence (report only)

Scope: whether USDCAD, USDCHF, NZDUSD can join the screen universe in a
future rung-5 box. Read-only probes of the cache; no outcomes computed.

## Bar coverage (DESIGN split, via pa_data.frame, warmup_days=30)

| symbol | M5 bars | M1 bars | range (UTC) | pip |
|---|---|---|---|---|
| USDCAD | 444,998 | 2,236,517 | 2015-12-02 .. 2021-12-31 | 0.0001 |
| USDCHF | 443,644 | 2,234,857 | 2015-12-02 .. 2021-12-31 | 0.0001 |
| NZDUSD | 445,105 | 2,237,026 | 2015-12-02 .. 2021-12-31 | 0.0001 |

Same coverage as the current four-symbol universe — no gaps at frame
level. M1 fill data is present for `pa_fill.simulate` (realistic fills).

## Cost evidence (pa_costs.C_RT_P90, round-trip pips)

| symbol | c_rt P90 | note |
|---|---|---|
| USDCAD | 1.4 | = USDJPY/AUDUSD tier — the costliest current bucket |
| USDCHF | 1.1 | = GBPUSD tier |
| NZDUSD | 1.4 | = USDJPY/AUDUSD tier |

Implication for the `s_struct >= 10*c_rt` guard: USDCAD/NZDUSD need
structural stops >= 14 pips — wider than EURUSD (10) — so thin-S rungs
are less populated there; rung ladders may need symbol-specific floors.

## Missing pieces (would be built in a future box, all DESIGN-only)

1. Zone caches: `sf_ctx.build_cache` per symbol per generator
   (line1_cluster, sd_base) — causal, reads DESIGN bars only. Not yet
   built (only the 4 current symbols have caches in
   `rounds/SF01/zcache/`).
2. Session sanity: all three are USD-quoted majors; EU/US session
   definitions (pa_random session_of) apply unchanged.
3. Spread history: c_rt values are already in pa_costs — no additional
   work needed for cost tiers x1/x1.5/x2.
