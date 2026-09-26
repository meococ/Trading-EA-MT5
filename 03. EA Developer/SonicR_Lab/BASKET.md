# BASKET.md - Round-2C replication basket (written BEFORE any basket P/L)

Lead brief 23/09 20:20Z. Question: do the frozen round-2B/A1 rules
replicate on symbols they were never fitted on? This file pins the
basket, costs, roll windows and data checks - all outcome-blind.

## 1. Basket (fixed by the Lead)

GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD, USDCHF, EURJPY, GBPJPY, EURGBP,
AUDJPY. Data: `02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet`
(same ETL, same suspect flags as EURUSD/XAUUSD). DESIGN window identical
to PREREG.md (COMMON_START .. DESIGN_END ~2020-01-15).

Pip = 0.01 for JPY pairs, 0.0001 otherwise. Point = pip/10.

## 2. Costs (Lead assumptions, ECN-like, incl. commission + p90 slippage)

Round-trip cost in pips: GBPUSD 1.4, USDJPY 1.2, AUDUSD 1.3, NZDUSD 1.8,
USDCAD 1.6, USDCHF 1.6, EURJPY 1.6, GBPJPY 2.6, EURGBP 1.5, AUDJPY 1.8.

Decomposition into the harness cost model (`src/data.py`): same baseline
as EURUSD - spread 0.1p + commission 0.7p fixed, remainder into two-sided
slippage so that spread + 2*slip + comm = the Lead's round-trip number.

E1b rollover spread stress: +2.0 pips ask side inside each symbol's roll
window (GBPJPY +3.0 pips) - Lead assumption, labelled as such.

## 3. Roll windows (discovered outcome-blind from suspect clustering)

Method (`runs/basket_check.py`): smallest contiguous arc of server
minute-of-day covering >= 99% of suspect-bar mass (95% fallback, max
60 min). GBPJPY/AUDJPY reached only 95% cover - suspect mass slightly
more spread; windows still tight.

| symbol | roll window (server) | cover |
|--------|---------------------|-------|
| GBPUSD | 23:59-00:28 | 0.99 |
| USDJPY | 23:59-00:30 | 0.99 |
| AUDUSD | 23:59-00:29 | 0.99 |
| NZDUSD | 23:59-00:30 | 0.99 |
| USDCAD | 23:59-00:29 | 0.99 |
| USDCHF | 23:59-00:27 | 0.99 |
| EURJPY | 23:59-00:33 | 0.99 |
| GBPJPY | 00:00-00:16 | 0.95 |
| EURGBP | 23:59-00:26 | 0.99 |
| AUDJPY | 00:00-00:17 | 0.95 |

Consistent with EURUSD's 23:55-00:15: the same feed defect across the
whole FX basket.

## 4. Per-symbol data checks (out/basket_checks.csv)

Coverage: all 10 symbols have bars in 100% of DESIGN weeks -> NONE
dropped. Suspect share uniformly ~1.1%.

Exit-free roll diagnostic (per server-day max M1 range / max
|open-prev close| inside the roll window vs the two adjacent equal-
length quiet windows):

| symbol | range med | range P90 | range P99 | jump med | jump P99 | med daily range (p) |
|--------|-----------|-----------|-----------|----------|----------|---------------------|
| GBPUSD | 27.7 | 53.4 | 92.0 | 58.0 | 472.4 | 106.6 |
| USDJPY | 22.2 | 42.1 | 77.0 | 52.2 | 430.6 | 71.7 |
| AUDUSD | 23.3 | 41.9 | 65.3 | 50.0 | 393.3 | 76.0 |
| NZDUSD | 19.1 | 35.6 | 56.7 | 33.0 | 286.0 | 72.3 |
| USDCAD | 23.6 | 45.4 | 78.8 | 39.0 | 343.8 | 79.6 |
| USDCHF | 24.2 | 52.4 | 103.9 | 40.3 | 364.8 | 71.1 |
| EURJPY | 22.2 | 41.1 | 68.5 | 65.3 | 535.2 | 104.7 |
| GBPJPY | 26.6 | 51.8 | 89.8 | 68.0 | 671.7 | 135.3 |
| EURGBP | 24.1 | 45.9 | 74.4 | 51.2 | 388.3 | 57.8 |
| AUDJPY | 24.9 | 47.2 | 78.1 | 63.5 | 580.4 | 87.1 |

Same signature as EURUSD (30.9x) / XAUUSD (37.9x): the rollover window
is systematically the most extreme window of the day despite being the
real market's quietest hour. E1 stays justified on the basket.

## 5. SL caps (data-derived, same formula as XAUUSD)

cap(symbol) = (120 / mdr_EURUSD) * mdr_symbol * PIP[symbol] in price
units; mdr = median daily server-day range over DESIGN. Values are
written into the census output (`runs/run_census_2c.py` logs, per-symbol
`mdr_pips` column above); the formula is unchanged - only the input
median is per-symbol.

## 6. Harness

H0 = E1b + E2 + E3, suspect bars tradable. H1 = H0 + E1 skip_suspect
with the A1 gap rules. Identical to round 2/2B; no parameter changes.
Secondary column: daily flat 23:50 server on both harnesses.
