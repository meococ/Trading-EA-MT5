# Chart/ledger forensics — PULL-001 `20260817_013130`

Sampling locked before cases: all 92 pendings; 3 largest TP; 3 fast SL;
2 Friday-flatten wins. No hour/weekday cut.

## Population

| Item | Value |
|---|---|
| HQ / bars | 99% / 164806 |
| Pendings / fill / TTL | 92 / 60 / **32 (35%)** |
| Closed / PF / net | 60 / 1.86 / +1090 |
| Typical SL / TP | two-bar ~$1–3 price, ~$25 $risk / whole $20–30 |
| WR | 16.7% — fat TP vs tiny SL |

## Frozen cases (report deals)

| case | stratum | dir | entry | exit | note |
|---|---|---|---|---|---|
| W1 | largest TP | buy | 2020.02.18 1586.31 | 1610 TP +474 | London morning, full $24 run |
| W2 | large TP | buy | 2022.03.01 1906.63 | 1930 TP +280 | session impulse |
| W3 | large TP | buy | 2023.12.22 2049.50 | 2070 TP +267 | late-year, held hours |
| L1 | fast SL | buy | 2022.02.09 1828.09 | SL 4 min | 2-bar SL inside Dragon |
| L2 | fast SL | buy | 2021.02.09 1843.68 | SL 3 min | same |
| L3 | fast SL | sell | 2020.10.15 1893.02 | SL 1 min | same |
| F1 | Friday flat | buy | 2021.08.13 1757.34 | 19:00 +270 | run without TP print |
| F2 | Friday flat | buy | 2022.09.30 1663.05 | 19:00 +108 | same |

H4 location at entry: not reconstructed (no H4 bar dump). Inference only:
winners held through a later impulse; losers never left the Dragon noise.

## Material causes

1. **Cadence:** mid-tag is rare (92/7y) **and** 35% never fill (TTL 4 bars).
2. **WR:** SL is last-two-bar extreme inside the Dragon, not structural.
3. **Payoff:** when the $20 whole hits, R is large — that is the PF 1.86.

## Legal next (ENV-001)

Tag envelope (Dragon low/high), SL outside that band, pending lives the
session. Not “skip hour 13–14”, not Tuesday-only.

## Cannot conclude

H4/H1 Dragon alignment, whether TTL-fill would have been +EV, live spread.
