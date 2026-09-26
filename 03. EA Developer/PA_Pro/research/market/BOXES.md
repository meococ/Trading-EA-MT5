> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**

# M4 — Boxes and breakouts (DESIGN 2016–2021)

Prereg `abc8b5ba…` — post-review revision: detector is the declared §5 one (W=30, height 1.5–6 ABR, interleaved touches, span>=9, 100-bar death); placebo = declared P-RAND fake edges (24 same-day uniform prices from the M3 PRAND pool, touched >=2x in trailing-30 — sparse; see D22).  D = matched-strata contrast; day-block bootstrap B=2000; BH q=0.10; stability 4/6y + 3/4s.

## F-BX — descriptive (pooled symbols)

| sym | boxes | h p25/50/75 (pips) | life p50/p75 (bars) | breaks | P(buildup) | pokes | depth p50 | P(conv<=3b) | P(opp<=24b) | plac pk/bk |
|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | 9763 | 12.0/17.1/24.1 | 12/27 | 9172 | 0.053 | 11383 | 0.8 | 0.336 | 0.226 | 103/48 |
| GBPUSD | 9419 | 16.3/24.4/35.3 | 11/26 | 8869 | 0.061 | 10376 | 1.0 | 0.355 | 0.214 | 113/48 |
| USDJPY | 9565 | 12.7/17.3/23.9 | 13/30 | 9207 | 0.054 | 10919 | 0.8 | 0.350 | 0.196 | 95/48 |
| AUDUSD | 10391 | 12.2/15.8/20.4 | 12/28 | 10080 | 0.055 | 12234 | 0.8 | 0.349 | 0.207 | 89/48 |

### box height by session (median pips, n)

| sym | ASIA | EU | US | LATE |
|---|---|---|---|---|---|
| EURUSD | 11.4 (3163) | 18.8 (2911) | 24.5 (1402) | 20.4 (2287) |
| GBPUSD | 15.1 (3222) | 29.7 (2486) | 36.9 (1472) | 27.6 (2239) |
| USDJPY | 15.3 (3132) | 16.6 (2824) | 21.0 (1268) | 18.9 (2341) |
| AUDUSD | 14.0 (3357) | 16.7 (3170) | 19.2 (1471) | 15.8 (2393) |

## F-BO — breakout follow-through (declared: race24, y=1 ABR, H=24)

| test | D | CI | p | q | stable |
|---|---|---|---|---|---|
| race24 | -0.0257 | -0.1210–0.0149 | 0.1968 | 0.3937 | no |
| buildup_minus_none | -0.0135 | -0.0380–0.0126 | 0.3020 | 0.4530 | YES |

descriptive (no q):

| metric | D |
|---|---|
| fwd6_desc | -1.8158 |
| fwd12_desc | -1.8672 |
| fwd24_desc | -2.9552 |
| fwd48_desc | -2.2936 |
| mfe24_desc | -2.7737 |

## F-FB — poke -> reach opposite edge <=24 bars: D vs fake-edge placebo (height-tercile stratified)

WARNING: the declared P-RAND fake edges produce traversal heights ~0.2 ABR vs real boxes ~5 ABR — the height-tercile strata barely overlap, so the matched subpopulation is thin and the D is dominated by the mechanical distance gap.  Treat as *not identified*; see DEVIATIONS D22.

| depth (pips) | D | CI | p | q | n_real | n_plac | stable |
|---|---|---|---|---|---|---|---|
| (0,1] | -0.7660 | -0.9297–-0.1667 | 0.0006 | 0.0024 | 611 | 112 | no |
| (1,2] | -0.7500 | -1.0000–-0.2500 | 0.0008 | 0.0024 | 267 | 90 | no |
| (2,3] | nan | nan–nan | nan | 1.0000 | 74 | 46 | no |
| (3,5] | nan | nan–nan | nan | 1.0000 | 60 | 38 | no |

same warning applies to race24 (placebo breaks ~48/symbol):
