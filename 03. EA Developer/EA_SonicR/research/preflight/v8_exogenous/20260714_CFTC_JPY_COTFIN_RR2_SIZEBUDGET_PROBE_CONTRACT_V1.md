# Frozen Contract — CFTC JPY COT FinFut LevMoney SIZE BUDGET on RR2 (V1)

**Hypothesis ID:** `HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001`  
**Frozen date:** 2026-07-14  
**Status:** a priori offline probe contract (no threshold mining from readout)

## Object
SIZE BUDGET overlay on SilverBullet RR2 shelf. Scale position risk/PnL by crowding; do **not** skip trades.

## Panel
- Path: `03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/panels/cftc_jpy_finfut_net_lev_spec_d1_v1.csv`
- Expected SHA256: `93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54`
- Market filter: exact `JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE` (contains `JAPANESE YEN - CHICAGO`, excludes `EURO FX`)
- Availability: use panel `available_at_utc` (obs+4d); fail closed on SHA mismatch

## Crowding score
- Feature: `|net_lev_money|`
- Score: percentile rank among prior 52 weekly observations with `observation_date` strictly before current
- Require >=40 priors; else crowd_pct = missing

## Size mult (a priori)
| crowd_pct | size_mult |
|---|---:|
| missing | 1.00 |
| < 0.50 | 1.00 |
| [0.50, 0.80) | 0.67 |
| >= 0.80 | 0.50 |

## Trade join
- RR2 trades: `02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/logs/*_Trades_*.csv`
- Parse OPEN/CLOSE final closes (dichotomy `load_closed_trades` pattern)
- Window: 2021-01-01 .. 2025-12-31; WEEKS = days/7
- For each open_time date: latest COT row with `available_at <= open_date`
- `scaled_pnl = raw_pnl * size_mult`

## Cost stress
- `BASE_COST = 12.0`
- Haircut = `BASE_COST * stress_mult * size_mult` (cost scales with size)
- Report x1 / x1.5 / x2; also baseline unscaled

## Joint kill / survivor (a priori)
- **KILL** if N<80 OR tpw not in [1.0, 6.5] OR PF<1.05 OR +$12-scaled x1.5 PF<1.10 OR sized x1.5 does not beat baseline x1.5 by >0.01
- **PROBE_SURVIVOR** only if PF>1.20 AND tpw in [1.5, 6] AND x1.5 PF>=1.15 AND stress lift vs baseline
- Model 0 withheld unless PROBE_SURVIVOR

## Artifacts
- Probe script: `preflight/20260714_COT_SIZEBUDGET_RR2_PROBE.py`
- JSON: `preflight/20260714_COT_SIZEBUDGET_RR2_PROBE.json`
- Readout: `readouts/20260714_COT_SIZEBUDGET_RR2_PROBE.md`
