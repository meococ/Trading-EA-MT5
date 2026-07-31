# TRAIN ECONOMIC PROBE PLAN V2 — HYP-EUVIX-EURUSD-M1-002

Frozen at `2026-07-29T17:49:20.000Z` as the pre-conditional-outcome engineering
successor to `HYP-EUVIX-EURUSD-M1-001`. V1 stopped before the VIX-to-PnL join,
selected zero conditional trades and computed no performance metric. This V2
changes only identity and the raw/missing/valid VIX population contract.

## Identity and unchanged decision surface

- Hypothesis: `HYP-EUVIX-EURUSD-M1-002`
- Parent market mechanism: `HYP-EUVIX-EURUSD-M1-001` (engineering-invalid,
  zero conditional outcomes)
- Research-only package: `EA_EuropeOpenUSDDemand`
- Attempt: `EUVIX002-TRAIN-ECON-001`, exactly once
- DESIGN/TRAIN: 2016-2020; validation 2021-2024 and 2025+ holdout sealed

Unchanged market object:

- source-ranked SHORT EURUSD from Europe/Berlin completed `07:59` close to
  completed `14:14` close;
- one trade only when a strictly lagged VIX close is at or above the median of
  the immediately prior 252 valid VIX closes, excluding itself;
- minimum 60 prior valid closes;
- fixed costs 1.50 / 2.25 / 3.00 pips;
- matched reverse plus frozen unfiltered-parent benchmark;
- ten DSR arms, 10,000 random-sign permutations with seed 20260729;
- identical structural/economic gates below.

No target PnL was joined to VIX before this V2 freeze. HYP001 is not an extra
DSR economic arm because it produced no conditional population or metric.

## Source mechanism

Krohn, Mueller and Whelan link larger FX-fix reversal returns to higher lagged
VIX and constrained intermediary risk-bearing. Their Table I also ranks the EUR
pre-ECB effect above JPY. Source: *Foreign Exchange Fixings and Returns Around
the Clock*, DOI `10.1111/jofi.13306`, open working paper:
`https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf`.

VIX source: CBOE daily close via FRED `VIXCLS`:
`https://fred.stlouisfed.org/series/VIXCLS`.

This remains a binary prospective translation, not an exact regression
replication. It does not use observed weekday/month PnL, shift the clock, or
reduce costs.

## Corrected V2 data contract

Bound parent target ledger:

- `03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001/trades.jsonl`
- SHA256:
  `204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8`
- exact rows: `1,296`.

Bound VIX CSV:

- `02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.csv`
- SHA256:
  `2280FF566149A58E2FD3B137686D94D9C0E6E2C884C2A77BC02BA7FFB7F6B248`
- exact raw rows: `1,328`;
- exact valid numeric closes: `1,281`;
- exact missing closes: `47`;
- missing/non-numeric closes are dropped before sorting/rolling;
- duplicate valid dates fail closed.

Corrected V2 manifest:

- `02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.manifest.v2.json`
- SHA256:
  `4E9FBF69D30143A03297CD9C4B0FB1455A83F221AF207A3966E670B2822AB74A`

V1 abort evidence is bound to prove the zero-outcome boundary:

- attempt-start SHA256:
  `8F4CB0C02F0F38ADFBF1A45EFDD1A1CB2D25378DCFABBF568539C61D3EAEFD6F`
- engineering-abort SHA256:
  `7C988710F998D6FE2ADCFDECF303EF4A13E4EF531629B93EF0D5CFAE570D9CD0`

Prior economic ledgers remain LOJM001, LOFIX002, EUUSD-USDJPY-001 and
EUUSD-EURUSD-001; their exact hashes plus the common evaluator and canonical
DSR module must be registry-bound. All data/evidence stays on `D:`.

## Exact no-lookahead feature algorithm

For parent trade date `t`:

1. After dropping exactly 47 missing VIX rows, select the latest valid VIX row
   with observation date strictly less than `t`.
2. Let that row be `j`. Its threshold is the median of valid rows
   `max(0,j-252)` through `j-1`; `j` is excluded.
3. At least 60 prior valid observations are required.
4. Trade iff `VIX[j] >= threshold[j]`.
5. Copy the exact parent gross PnL; recompute both directions at all three costs.

Feature-only pre-outcome result remains: 595 eligible generic business dates,
cadence `2.280118` per elapsed week. It is not an economic result.

## Frozen gates

Structural, all required:

1. selected parent trades `>=500`;
2. VIX mapping coverage of 1,296 parent rows `>=95%`;
3. selected cadence `2.0` to `5.0` per elapsed calendar week;
4. at least 30 selected trades in every local year;
5. largest selected year share `<=40%`.

Economic, all required:

1. x1 PF `>1.30`;
2. x1.5 PF `>=1.25`;
3. x2 PF `>=1.00`;
4. x1 expectancy `>0`;
5. at least four of five years positive at x1;
6. random-sign p-value `<=0.05`;
7. ten-arm DSR `>=0.95`;
8. x1 PF and expectancy exceed matched reverse and unfiltered parent
   (`PF=0.9687234884904704`, expectancy=`-0.29868827160493405`).

Structural failure makes no economic claim. Structural pass with any economic
failure kills this exact V2 object. Only 8/8 authorizes a new MQL5/Model-0
packet; validation, holdout, optimization, promotion, paper and live stay shut.

## One-shot evidence and prohibitions

Registry authority must bind plan, normalized evaluator, tests, four prior
economic ledgers, VIX CSV/V2 manifest, V1 zero-outcome abort evidence, parent
evaluator and DSR. Evidence root must be absent:

`03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-002/EUVIX002-TRAIN-ECON-001/`

Forbidden: any feature/gate/clock/direction/cost change, same-date VIX,
weekday/month/year selection, stop/target, 2021+ access, optimization, MQL5/MT5,
Model 0/4, promotion, paper, or live.
