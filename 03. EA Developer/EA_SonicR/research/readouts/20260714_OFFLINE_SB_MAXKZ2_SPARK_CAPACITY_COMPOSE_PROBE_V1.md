# Offline compose — SB MaxKZ2 + Spark capacity (matched Deposit=100000)

Date: 2026-07-14  
Status: `PROBE_NEAR_GOAL_CADENCE_AND_PF_BUT_COST_UNCONFIRMED`  
Result JSON:
`preflight/20260714_OFFLINE_SB_MAXKZ2_SPARK_CAPACITY_COMPOSE_PROBE_V1.json`  
SHA256: `3CE907B565D19763A5946A800226D492D51CF4633B1F9CE696BF18ADEC32A21B`

## Universe (a priori capacity update)

| Sleeve | Run | Deposit | PF | N | tpw | Net |
|---|---|---:|---:|---:|---:|---:|
| SB MaxKZ2 | `20260714_192304` | 100000 | 1.33 | 546 | 2.09 | +8123 |
| Spark capacity | `20260714_193732` | 100000 | 1.37 | 327 | 1.25 | +9184 |

Prior mixed-deposit compose used Spark `002614` (Deposit=10000) → understated
Spark dollar contribution. This probe replaces Spark with capacity Model 0 at
matched capital; capacity itself is PARK/null densify (+2 trades).

## Pooled

| Metric | Value |
|---|---|
| N | 873 |
| PF | **1.352** |
| tpw elapsed | **3.35** |
| Net $ | +17307 |
| Weekly PnL corr | 0.089 |
| Same-bar overlap | 3 |

Clears research PF>1.30 + 2–5/wk under tester `current` only — **not confirmed**.
Slightly stronger PF than mixed-deposit MaxKZ2+Spark002614 (1.330 / 3.34/wk)
because Spark dollars are now on Deposit=100000. Phase 0 contamination freeze
unchanged — no portfolio EA coded as promotion candidate.
