# Offline Portfolio Composition Probe V1 — SparkAsian + ITSM

Date: 2026-07-14  
Status: `FAIL_POOLED_PF_BELOW_1_30_CADENCE_OK` / **GOAL unmet** / **not confirmed**  
Process: `GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY`  
No new EA coded this turn.

## Universe freeze (exact; no cherry-pick)

| Member | EA | Run ID | Symbol / TF | Hypothesis |
|---|---|---|---|---|
| A | `EA_M15SparkAsian` | `20260714_002614` | USDJPY M15 | `HYP-SPARK-ASIAN-M15-001` |
| B | `EA_ITSM` | `20260714_003920` | USDJPY M15 | `HYP-ITSM-PULLBACK-M15-001` |

Selection rule: Owner-named run IDs only. SB and all other shelf EAs are **excluded**. No PF-ranked substitution of twins or other books.

Paths:

- `02. AlphaFactory/runs/EA_M15SparkAsian/20260714_002614/` (report SHA256 `7CAE7A9332B551FE58360E2B89022835F23E7706345ED2E7DC02F5122D80001A`)
- `02. AlphaFactory/runs/EA_ITSM/20260714_003920/` (receipt SHA256 `0B5FBAB87648D9CA66EA168C1B891F1CCED852C7081D41A11D781DEF97FB9D31`)

Machine result: `preflight/20260714_OFFLINE_SPARK_ITSM_COMPOSE_PROBE_V1.json`  
Result SHA256: `0D095E4FC08C8449F720954178E5457C702F80F264D381E4203B7B4A261864F9`  
Tool: `preflight/20260714_OFFLINE_SPARK_ITSM_COMPOSE_PROBE_V1.py`

## Cost caveat (hard)

Both runs use Strategy Tester spread=`current` (Demo research-proxy). Commission/swap fields are not broker-verified. **Missing cost ≠ 0.** This probe is **not** `confirmed` and cannot claim after-cost GOAL pass.

## Window

Identical overlapping tester window: **2021.01.01 – 2025.12.31**.  
Elapsed calendar days = **1825**; elapsed calendar weeks = **1825/7 ≈ 260.714**.

## Sleeve metrics (tester report)

| Sleeve | N | Net $ | Gross profit | Gross loss | PF | Expectancy | Trades/week (elapsed) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Spark `20260714_002614` | 325 | +1099.38 | 4700.42 | −3601.04 | **1.31** | +3.38 | **~1.25** |
| ITSM `20260714_003920` | 852 | +3959.60 | 29221.60 | −25262.00 | **1.16** | +4.65 | **~3.27** |

Trade-series sources: Spark deals from `report.html` (650 deals → 325 round-trips); ITSM from PX6 trades CSV (852 final closes). Trade-level PF matches report PF within rounding (Spark 1.305 / ITSM 1.157).

## Pooled composition (naive equal-join of both books)

| Metric | Value |
|---|---|
| Pooled N | **1177** (= 325 + 852) |
| Pooled net $ | **+5058.98** |
| Pooled gross profit | 33922.02 |
| Pooled gross loss (abs) | 28863.04 |
| Pooled PF (report gross) | **1.175** |
| Pooled PF (trade PnLs) | **1.175** (identical) |
| Pooled trades/week (elapsed) | **4.51** (= 1177 / 260.714) |
| Naive pooled expectancy | +4.30 $/trade |

Interpretation: cadence clears the 2–5/week GOAL band by stacking a sparse high-PF sleeve onto a denser sub-1.30 sleeve. Pooled PF is **weighted toward ITSM** (852/1177 ≈ 72% of trades) and lands **below 1.30**.

## Entry overlap / correlation (joinable)

| Measure | Value |
|---|---|
| Exact same entry timestamp | **4** |
| Same M15 bar entry overlap | **5** |
| Same calendar-day entry overlap | **182** |
| Spark entries within ±60m of an ITSM entry | **32 / 325** (~9.8%) |
| ITSM entries within ±60m of a Spark entry | **32 / 852** (~3.8%) |
| Weekly PnL Pearson (elapsed week grid) | **0.183** (weak) |
| Weeks both active / Spark-only / ITSM-only | **175 / 0 / 86** |

Entry clocks are largely distinct (almost no same-bar collisions). Weekly PnL co-movement is weak-positive, not a clone. Spark-active weeks are a subset of ITSM-active weeks because ITSM is denser — that is cadence nesting, not identity duplication.

## Verdict vs GOAL (research screen only)

GOAL needs pooled ~**2–5/wk** AND **PF > 1.30** after verified cost. On this offline probe:

| Gate | Result |
|---|---|
| Pooled elapsed cadence ∈ [2, 5]/wk | **PASS** (~4.51) |
| Pooled PF > 1.30 | **FAIL** (1.175) |
| Verified broker cost | **FAIL** (tester `current` only) |
| Confirmed / promotion | **No** |

**Decision:** `FAIL_POOLED_PF_BELOW_1_30_CADENCE_OK`.

**Worth coding a portfolio EA sleeve next?** **No** — not from this probe alone. Cadence stacking works; edge does not. A combined sleeve would inherit ITSM’s sub-1.30 PF dominance and still lack Real/QFSI cost proof. Do not open a portfolio-compose prereg/compile from these two near-misses.

## What this does *not* authorize

- No registry promote, no Model 0 portfolio backtest, no new multi-sleeve EA.
- No PF-ranked swap to SB or other parked books inside this freeze.
- No post-hoc day/hour veto mined from the overlap table.
- No claim that low entry-timestamp overlap equals diversification after cost.

## Next (honest)

1. Keep Spark + ITSM parked as separate near-misses.
2. Highest leverage for GOAL remains Owner Real login + QFSI cost capture on near-GOAL PF books (SB/Spark), not composing a denser weak-PF sleeve.
3. New independent thesis still required for a legal PF>1.30 book at 2–5/wk; GPT Deep Research remains waived (local only).
