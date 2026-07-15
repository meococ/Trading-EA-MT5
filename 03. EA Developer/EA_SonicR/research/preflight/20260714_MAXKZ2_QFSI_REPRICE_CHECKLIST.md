# MaxKZ2 QFSI Reprice Checklist — one page (frozen)

Status: `CLOSED_FAIL_PARTIAL_REAL_COST` / full QFSI still `STOP_DATA_FRONTIER`  
Date: 2026-07-14 ~22:10 ICT  
Authority: cost reprice only — **no new strategy logic**  
Post-login: probe V6 PASS (`FivePercentOnline-Real`); captures accumulate;
inventory V6 eligible **0**. Partial Real stress ran — MaxKZ2 **FAIL** under
both live-tick ~$2.31 and aggregated-capture ~$2.62 P50. **Not** verified /
**not** confirmed.

## Survivor lock (do not redesign)

| Field | Frozen value |
|---|---|
| `hypothesis_id` | `HYP-SB-MAXKZ2-DENSITY-002` |
| Research run (baseline) | `20260714_192304` |
| EA / source | `EA_SilverBullet` / `EA_SilverBullet_v2.mq5` |
| Symbol / TF / window | USDJPY / M15 / 2021.01.01–2025.12.31 |
| Deposit / leverage | 100000 / 100 |
| Overrides | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpUseWeekendFlat=1` |
| Sessions | LDN+NYAM; NYPM **off** (as run) |
| Matched control | A1 `20260714_002505` (weekend-flat only) |
| Current cost grade | `REAL_PARTIAL_SAMPLE_NOT_FULL_QFSI` — **PARK FAIL** — not confirmed |

## Preconditions (Owner-physical) — checked 2026-07-14

1. MT5 login server == `FivePercentOnline-Real` — **PASS** (probe V6).
2. Read-only probe verdict `TARGET_SERVER_READONLY_PROBE_COMPLETE` — **PASS**.
3. No-live QFSI capture on Real — **RUNNING/PARTIAL** (`004_EXTENSION` + priors).
4. Hash-bound eligible bundle — **FAIL** (inventory V6 eligible **0**).

## Capture symbols (contract)

- Contract core: EURUSD, GBPUSD, XAUUSD (execution-data contract V1).
- Survivor reprice symbol: **USDJPY** (present; commission lifecycles still **0**).

## Reprice outcome (closed)

1. Same source / overrides / window — cost provenance only.
2. Live-tick P50 x1 PF **1.275** FAIL; aggregated-capture P50 x1 **1.267** FAIL.
3. A1 under same live-tick model also x1 FAIL (**1.284**).
4. Kill/park from verified-or-honest-partial PF only — **PARK**. No densify.

## Pass / fail (research bar under verified cost)

- Joint: PF > 1.30 **and** 2–5 trades/week elapsed under honest Real cost.
- Result: **FAIL** → park; **no densify rescue**.
- Pass research bar ≠ GOAL; GOAL still needs full confirmed suite (blocked).

## Banned

Day/hour mining · densify spam · Demo ticks as Real cost · missing-cost-as-zero · GOAL claim from this checklist alone · elevating partial QFSI to confirmed.
