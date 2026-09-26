# BOX_CEILING — why is the BOX oracle capped at ~0.31?

**HEADLINE: generation, not rule-strictness.**  Even with every rule maximally relaxed (edge tol x2, no start window, no proposal-time limit) the oracle caps at 0.76 v0 / 0.67 v1.  Detail: v0: relaxed-cap 0.76, none_within_2tol 26/82, edges_ok_start_wrong 32, start-inf@1x 0.47; v1: relaxed-cap 0.67, none_within_2tol 36/77, edges_ok_start_wrong 19, start-inf@1x 0.41.

Mandate 3 Z1.  Rule under test: R11 §11.2 `cand_right` (edges within tol + start within 20 min of build_start + proposal <= build_end + 10 min).  `tol` = object precision (eye 5p / meas 2p / refined 1.5p).  Engine runs via cache.

## engine v0 (`63c771d64e18f619`)

Golden scorable BOXes: 108 — right proposal exists for 26; funnel-style oracle (right OR born-matched) = 34 (0.31); diagnosed misses: 82

### Miss classes

- `edges_ok_start_wrong` = 32
- `none_within_2tol` = 26
- `one_edge_wrong_hi` = 10
- `one_edge_wrong_lo` = 8
- `both_edges_wrong` = 3
- `edges_ok_too_late` = 3

Of these misses, 8 were nevertheless matched by a born object (born-but-never-proposed-right).

### Nearest-candidate error distribution (misses only)

| quantity | p10 | p50 | p90 |
|---|---|---|---|
| lo edge err (p) | -2.89 | 0.00 | 5.10 |
| hi edge err (p) | -4.87 | 0.00 | 4.88 |
| lo edge err (ABR) | -0.59 | 0.00 | 0.83 |
| hi edge err (ABR) | -1.17 | 0.00 | 0.68 |
| start err (min) | -149.50 | 25.00 | 153.50 |
| proposal lag (min) | -193.50 | -32.50 | 134.50 |

| quantity | p50 | p90 |
|---|---|---|
| |dlo| p | 1.30 | 7.81 |
| |dhi| p | 2.15 | 9.64 |
| |dlo| ABR | 0.27 | 1.27 |
| |dhi| ABR | 0.35 | 1.47 |
| |start err| min | 45.00 | 204.50 |
| |prop lag| min | 70.00 | 232.50 |

### Oracle sensitivity (fraction of golden BOXes with a right proposal)

ALL 108 boxes:

| edge tol x | start 20 | start 40 | start 60 | start inf | (each row: prop-limit on / off) |
|---|---|---|---|---|---|
| 1.0x / plim | 0.24 | 0.31 | 0.40 | 0.47 | |
| 1.0x / free | 0.27 | 0.38 | 0.47 | 0.56 | |
| 1.5x / plim | 0.31 | 0.39 | 0.47 | 0.56 | |
| 1.5x / free | 0.35 | 0.49 | 0.58 | 0.69 | |
| 2.0x / plim | 0.37 | 0.45 | 0.55 | 0.64 | |
| 2.0x / free | 0.44 | 0.57 | 0.67 | 0.76 | |

split `eye/bs` (n=29): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.28 / 0.34 / 0.41
split `eye/t0fb` (n=49): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.24 / 0.29 / 0.35
split `meas/bs` (n=14): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.43 / 0.43 / 0.43
split `meas/t0fb` (n=16): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.00 / 0.19 / 0.31

### Brief: PATTERN_LINE / LEVEL_CARRIED misses (no right proposal)

- PATTERN_LINE: 184 golden, 138 without right proposal; classes: geometry_off=59, dir_wrong=58, too_late=18, no_price_evidence=2, no_shared_span=1; geom/price residual p50/p90 = 9.2/31.1 p
- LEVEL_CARRIED: 48 golden, 42 without right proposal; classes: price_off=33, outside_span=9; geom/price residual p50/p90 = 8.6/16.6 p

## engine v1 (`694313a38abc2da6`)

Golden scorable BOXes: 108 — right proposal exists for 31; funnel-style oracle (right OR born-matched) = 32 (0.30); diagnosed misses: 77

### Miss classes

- `none_within_2tol` = 36
- `edges_ok_start_wrong` = 19
- `both_edges_wrong` = 10
- `one_edge_wrong_lo` = 8
- `one_edge_wrong_hi` = 3
- `edges_ok_too_late` = 1

Of these misses, 1 were nevertheless matched by a born object (born-but-never-proposed-right).

### Nearest-candidate error distribution (misses only)

| quantity | p10 | p50 | p90 |
|---|---|---|---|
| lo edge err (p) | -4.72 | 1.80 | 14.92 |
| hi edge err (p) | -14.66 | -0.40 | 4.78 |
| lo edge err (ABR) | -0.62 | 0.33 | 2.16 |
| hi edge err (ABR) | -2.11 | -0.13 | 0.74 |
| start err (min) | -109.00 | 20.00 | 107.00 |
| proposal lag (min) | -182.80 | -50.00 | 82.00 |

| quantity | p50 | p90 |
|---|---|---|
| |dlo| p | 2.80 | 14.92 |
| |dhi| p | 2.60 | 15.68 |
| |dlo| ABR | 0.55 | 2.56 |
| |dhi| ABR | 0.51 | 2.25 |
| |start err| min | 50.00 | 162.00 |
| |prop lag| min | 85.00 | 182.80 |

### Oracle sensitivity (fraction of golden BOXes with a right proposal)

ALL 108 boxes:

| edge tol x | start 20 | start 40 | start 60 | start inf | (each row: prop-limit on / off) |
|---|---|---|---|---|---|
| 1.0x / plim | 0.29 | 0.33 | 0.37 | 0.41 | |
| 1.0x / free | 0.30 | 0.37 | 0.41 | 0.47 | |
| 1.5x / plim | 0.34 | 0.38 | 0.41 | 0.47 | |
| 1.5x / free | 0.38 | 0.44 | 0.48 | 0.56 | |
| 2.0x / plim | 0.41 | 0.44 | 0.48 | 0.55 | |
| 2.0x / free | 0.49 | 0.55 | 0.58 | 0.67 | |

split `eye/bs` (n=29): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.34 / 0.45 / 0.52
split `eye/t0fb` (n=49): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.27 / 0.31 / 0.37
split `meas/bs` (n=14): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.29 / 0.36 / 0.43
split `meas/t0fb` (n=16): oracle at tol x1.0/1.5/2.0, start 20, plim on = 0.25 / 0.25 / 0.31

### Brief: PATTERN_LINE / LEVEL_CARRIED misses (no right proposal)

- PATTERN_LINE: 184 golden, 120 without right proposal; classes: dir_wrong=53, geometry_off=40, too_late=13, no_shared_span=12, no_price_evidence=2; geom/price residual p50/p90 = 8.9/17.1 p
- LEVEL_CARRIED: 48 golden, 19 without right proposal; classes: price_off=14, outside_span=5; geom/price residual p50/p90 = 4.8/10.4 p
