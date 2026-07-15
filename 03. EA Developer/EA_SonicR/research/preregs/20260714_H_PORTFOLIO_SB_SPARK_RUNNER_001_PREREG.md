# Prereg — HYP-PORTFOLIO-SB-SPARK-RUNNER-001

Date: 2026-07-14  
State: `killed_at_model_0` (authoritative `20260714_224302`; PF 1.22 < 1.30)  
Family: `portfolio_sb_spark_runner` · budget **1/1 spent**  

## Thesis

Execute the exact Phase-0 dual-sleeve universe (SilverBullet A1 weekend-flat +
Spark Asian) as one research book with distinct magics, frozen sleeve params —
not a PF-ranked cherry-pick after Spark+ITSM fail.

## Offline probe (cheap / already on disk)

`readouts/20260714_OFFLINE_SB_SPARK_COMPOSE_PROBE_V1.md`  
Result SHA256 `E4672DF1AC0BCFEAAB311B3D2791D123206938A9DBC9081A1E2B32380FA604FC`  
Pooled PF **1.339**, **~3.24**/elapsed wk, overlap low — research bars clear under
tester-`current` only. **Not confirmed.**

## Frozen sleeve bindings

| Sleeve | EA / run | Overrides |
|---|---|---|
| A | `EA_SilverBullet` / `20260714_002505` | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseWeekendFlat=1` |
| B | `EA_M15SparkAsian` / `20260714_002614` | defaults (empty) |

Universe sha (Phase0): `B1A04F9C1CD7E2A7B0C8B6463AE4438A52A45DD5645046B5AA682A2F69D4D138`

## Build gate (honest)

**CLEARED (scaffold):** `EA_SBSparkBook` dual-runner shipped with SparkAsian_Module +
SB_A1_Module (A1 vol + weekend-flat). Legacy `EA_Portfolio` multi-sleeve stack
intentionally not reused. Phase-0 contamination attestation still
`BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW` for compose ceremony; this hyp is a
**separate runner** ID but still Demo-cost until Real QFSI.

Contract receipt + EX5 hashes live in readout / blocker JSON (rebuild after
prereg edits). Scaffold compile OK.

## This turn decision

Model 0 **complete**: `20260714_224302` → **KILL** (tester PF 1.219 < 1.30;
cadence ~3.23/wk PASS; +$12 cost stress FAIL). Offline NEAR_GOAL proxy did not
transfer. Do not densify.

## Banned

NYPM / Friday scrape / ITSM add / MaxHold stack as “portfolio”; outcome-mine
additional sleeves from tonight PF table.
