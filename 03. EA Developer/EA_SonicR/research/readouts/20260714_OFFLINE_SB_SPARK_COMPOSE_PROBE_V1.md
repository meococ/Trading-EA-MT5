# Offline Portfolio Composition Probe V1 — SilverBullet A1 + SparkAsian

Date: 2026-07-14  
Status: `PROBE_NEAR_GOAL_CADENCE_AND_PF_BUT_COST_UNCONFIRMED` / **GOAL unmet** / **not confirmed**  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`  
No new EA coded this turn. No USBILL rescue.

## Universe freeze (exact; a priori Phase 0 identity)

| Member | EA | Run ID | Symbol / TF | Hypothesis |
|---|---|---|---|---|
| A | `EA_SilverBullet` | `20260714_002505` | USDJPY M15 | `HYP-SB-WEEKEND-FLAT-001` (A1 challenger) |
| B | `EA_M15SparkAsian` | `20260714_002614` | USDJPY M15 | `HYP-SPARK-ASIAN-M15-001` (Phase 0 twin of `002821`) |

Selection rule: Phase 0 `HYP-PORTFOLIO-COMPOSE-001` subset already bound in
`subset_universe_sha256=B1A04F9C1CD7E2A7B0C8B6463AE4438A52A45DD5645046B5AA682A2F69D4D138`.
**Not** a post-hoc PF swap after Spark+ITSM fail. ITSM / LondonORB / USBILL
explicitly excluded.

Paths:

- `02. AlphaFactory/runs/EA_SilverBullet/20260714_002505/` (report SHA256
  `A4208F42C6B56B069CE538590EBF2D302A58FDF89EB715BD9D29E89613711BF9`)
- `02. AlphaFactory/runs/EA_M15SparkAsian/20260714_002614/` (report SHA256
  `7CAE7A9332B551FE58360E2B89022835F23E7706345ED2E7DC02F5122D80001A`)

Machine result: `preflight/20260714_OFFLINE_SB_SPARK_COMPOSE_PROBE_V1.json`  
Result SHA256: `E4672DF1AC0BCFEAAB311B3D2791D123206938A9DBC9081A1E2B32380FA604FC`  
Tool: `preflight/20260714_OFFLINE_SB_SPARK_COMPOSE_PROBE_V1.py`

## Cost caveat (hard)

Both runs use Strategy Tester spread=`current` (MetaQuotes-Demo research-proxy).
Commission/swap fields are not broker-verified. **Missing cost ≠ 0.** This probe
is **not** `confirmed` and **cannot** claim after-cost GOAL pass.

Live terminal login check (2026-07-14): `common.ini` shows
`Login=108623344` / `Server=MetaQuotes-Demo`. No `FivePercentOnline-Real`
string in Terminal config / `accounts.dat`. Prior QFSI probe V2 verdict
`BROKER_SERVER_MISMATCH` (expected Real, observed Demo) remains true.

Blocker code: `BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN`.

## Window

Identical overlapping tester window: **2021.01.01 – 2025.12.31**.  
Elapsed calendar days = **1825**; elapsed calendar weeks = **1825/7 ≈ 260.714**.

## Sleeve metrics (tester report)

| Sleeve | N | Net $ | Gross profit | Gross loss | PF | Expectancy | Trades/week (elapsed) |
|---|---:|---:|---:|---:|---:|---:|---:|
| SB A1 `20260714_002505` | 520 | +7875.93 | 30753.30 | −22877.37 | **1.34** | +15.15 | **~1.99** |
| Spark `20260714_002614` | 325 | +1099.38 | 4700.42 | −3601.04 | **1.31** | +3.38 | **~1.25** |

Trade-level PF matches report PF (SB 1.344 / Spark 1.305).

## Pooled composition (naive equal-join of both books)

| Metric | Value |
|---|---|
| Pooled N | **845** (= 520 + 325) |
| Pooled net $ | **+8975.31** |
| Pooled gross profit | 35453.72 |
| Pooled gross loss (abs) | 26478.41 |
| Pooled PF (report gross) | **1.339** |
| Pooled PF (trade PnLs) | **1.339** (identical) |
| Pooled trades/week (elapsed) | **3.24** (= 845 / 260.714) |
| Naive pooled expectancy | +10.62 $/trade |

Interpretation: stacking two independently parked PF>1.30 sleeves clears both
research bars under tester-`current` cost. Unlike Spark+ITSM (pooled PF 1.175),
neither sleeve dilutes the other below 1.30.

## Entry overlap / correlation (joinable)

| Measure | Value |
|---|---|
| Exact same entry timestamp | **0** |
| Same M15 bar entry overlap | **3** |
| Same calendar-day entry overlap | **108** |
| SB entries within ±60m of a Spark entry | **22 / 520** (~4.2%) |
| Spark entries within ±60m of an SB entry | **22 / 325** (~6.8%) |
| Weekly PnL Pearson (elapsed week grid) | **0.078** (near-zero) |
| Weeks both active / SB-only / Spark-only | **161 / 76 / 14** |

Entry clocks are largely distinct. Weekly PnL co-movement is weak — not a clone
pair on this window.

## Verdict vs GOAL (research screen only)

GOAL needs pooled ~**2–5/wk** AND **PF > 1.30** after verified cost. On this
offline probe:

| Gate | Result |
|---|---|
| Pooled elapsed cadence ∈ [2, 5]/wk | **PASS** (~3.24) |
| Pooled PF > 1.30 | **PASS** (1.339) |
| Verified broker cost / cost-stress x1.5/x2 | **FAIL** (tester `current` only) |
| Phase 0 prereg freeze / clean contamination review | **FAIL** (`BLOCKED_NOT_READY_FOR_PREREG_FREEZE`) |
| Confirmed / promotion | **No** |

**Decision:** `PROBE_NEAR_GOAL_CADENCE_AND_PF_BUT_COST_UNCONFIRMED`.

**Worth coding a portfolio EA sleeve next?** **Yes as research scaffold only** —
after Owner clears Phase 0 contamination review and freezes risk-weighting /
common-window contracts. **Not** promotion. Do **not** claim GOAL.

## What this does *not* authorize

- No `confirmed` / GOAL claim.
- No registry promote to challenger/confirmed.
- No compile/Model 0 portfolio backtest until Phase 0 freeze is READY.
- No post-hoc day/hour veto mined from the overlap table.
- No USBILL / ITSM / LondonORB substitution into this universe.
- No Spark Mon–Thu densify; no SB Friday cutoff mine.

## Path A blockers remaining (exact)

1. `BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN` — Owner must login Real; agents
   cannot invent credentials. QFSI capture required before any after-cost claim.
2. `BLOCKED_NOT_READY_FOR_PREREG_FREEZE` — Phase 0 contamination attestation.
3. `MATCHED_CONTROL_PREREG_GAP_DISABLED_SIGNAL_OR_RANDOM_HOUR` — still blocks
   inventing a disabled-signal control on single sleeves.

## Contrast vs Spark+ITSM

| Probe | Pooled PF | Pooled tpw | Verdict |
|---|---:|---:|---|
| Spark+ITSM | 1.175 | 4.51 | `FAIL_POOLED_PF_BELOW_1_30_CADENCE_OK` |
| SB+Spark (this) | **1.339** | **3.24** | `PROBE_NEAR_GOAL_…_COST_UNCONFIRMED` |

## Next (honest)

1. Owner: login `FivePercentOnline-Real` → read-only QFSI for SB then Spark.
2. Owner/independent review: clear Phase 0 contamination → freeze portfolio
   contracts → only then consider research scaffold portfolio EA.
3. Path B new independent thesis: shelf remains EMPTY under current local data;
   do not mint cosmetic IDs.
