# Readout — HYP-SB-MAXKZ2-DENSITY-002 Model 0

Date: 2026-07-14  
Status: `PARK_FAIL_PARTIAL_REAL_COST` / **GOAL unmet** / **not confirmed**  
Parent: `HYP-SB-WEEKEND-FLAT-001` A1

## Run (tester current — research screen)

| Role | run_id | Overrides | N | tpw | PF | Net | Exp |
|---|---|---|---:|---:|---:|---:|---:|
| Baseline A1 | `20260714_002505` | weekend-flat; MaxKZ=1; Risk=1.0% | 520 | 1.9945 | **1.34** | 7875.93 | 15.15 |
| Challenger | `20260714_192304` | MaxKZ=2; weekend-flat; **Risk=0.5%** | 546 | **2.0942** | **1.33** | 8123.09 | 14.88 |

Elapsed weeks: 260.7143. Deposit 100000. Twin: `20260714_192515`.

## Gate vs GOAL

| Check | Tester current | Partial Real cost | Full QFSI / confirmed |
|---|---|---|---|
| PF > 1.30 | **PASS** (1.33) | **FAIL** | not eligible |
| Cadence 2–5 tpw elapsed | **PASS** (2.09) | PASS (unchanged) | — |
| Cost stress x1.5≥1.25 / x2≥1.00 | n/a (unverified) | **FAIL** @x1 already | — |
| Confirmed suite | not run | **fail-closed** | blocked |

### Partial Real cost stress (USDJPY)

| Model | Base $/trade @0.5 lot | x1 PF | x1.5 PF | x2 PF | Verdict |
|---|---:|---:|---:|---:|---|
| Live-tick P50 + EURUSD N=2 clue | ~2.309 | **1.275** | **1.246** | 1.218 | **FAIL** |
| Aggregated-capture P50 (fail-closed) | ~2.618 | **1.267** | **1.235** | 1.204 | **FAIL** |

Cost grade: `REAL_PARTIAL_SAMPLE_NOT_FULL_QFSI`. Slippage MISSING ≠ 0.  
Inventory V6: eligible bundles **0** / `STOP_DATA_FRONTIER`.

## Decision

**PARK** under honest Real partial cost. Research HIT under tester-`current` is **superseded for GOAL claims**. Do **not** densify MaxTradesPerKZ / Friday / hours from this readout. Do **not** claim confirmed.

## Explicit non-rescues

Do not retune MaxKZ from this readout. Do not combine NYPM into this ID.  
Do not elevate Demo or partial QFSI to confirmed.

## Evidence pointers

- Owner-login Grok deliverable: `readouts/20260714_OWNER_LOGIN_QFSI_REPRICE_GROK_DELIVERABLE.md`
- Fail-closed authority: `readouts/20260714_MAXKZ2_QFSI_REAL_FAILCLOSED_DELIVERABLE.md`
- Live-tick receipt: `preflight/20260714_QFSI_REAL_REPRICE_RR2_MAXKZ2_RECEIPT.json`
- A1/Spark lot-scale: `preflight/20260714_QFSI_REAL_REPRICE_A1_SPARK_LOTSCALE_RECEIPT.json`

## Next

1. Keep PARK; accumulate full QFSI only as hygiene (will not rescue MaxKZ2 PF under current partial models).
2. Prefer independent thick-edge discovery over MaxKZ densify.
3. RR2 remains the only SB-family partial-Real cost-stress PASS diagnostic — still not confirmed.
