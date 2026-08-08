# FIV2 Trust Reset & Freeze Record

Date: 2026-08-08  
Campaign ID: `FIV2-20260808-ATOMIC`  
Lead Quant: Main Agent (this session)

## 1. Trusted base

| Item | Value |
|---|---|
| Base commit | `00f8a2f5661a2c089fe16b5084fc02e7694b8008` |
| Source branch (audit) | `codex/lomx-multi-asset-momentum` @ clean tree |
| Campaign branch | `codex/five-indicator-rebuild-v2` |
| Campaign worktree | `D:\Trading EA MT5-five-indicator-rebuild-v2` |
| Audit worktree retained | `D:\Trading EA MT5` (not modified by campaign writes) |
| Dirty at start | **No** — nothing to commit on source branch |

## 2. MT5 / AlphaFactory (measured)

| Item | Value |
|---|---|
| AlphaFactory | v4.3 |
| MT5 | **STOPPED** |
| Portable | True — `runtime\mt5-portable-fivepercent` |
| Config | `alpha.local.ps1` |
| FILE_COMMON allowed | False |
| EAs recognized | 31 OK (includes prior RSF/AIRQMB/census; FIV2 package not yet registered) |

## 3. Indicator inventory (base commit)

| Indicator | Path | Fork SHA256 (FIV2) | Verdict |
|---|---|---|---|
| QQE MOD | `06.Indicator Alpha/QQE_MOD.mq5` | `0CD4381B...BE2F78` | Engineering ports exist; **reuse after re-audit** |
| Modern Bollinger Bands | `.../Modern_Bollinger_Bands_GBB.mq5` | `D105F12C...515F09` | same |
| AI Regime Detection | `.../AI_Regime_Detection.mq5` | `26132998...0B17A` | same |
| Volatility Regime Classifier | `.../Volatility_Regime_Classifier_QuantRegime.mq5` | `400AA62B...3AD8BC` | same |
| TB Smart Money Concept | `.../TB_Smart_Money_Concept_2026.mq5` | `D3A80027...BFA217` | v3 ABI; same |

## 4. Rebuild vs reuse

| Object | Decision |
|---|---|
| Indicator formula ports | **REUSE_AFTER_REAUDIT** — compile/non-repaint already engineering-valid; fork into package; independent reviewer must re-check contracts. Full rewrite only if audit fails. |
| Semantic contracts | **BUILD NEW** (this campaign) |
| Atomic engines R/T/B | **BUILD NEW** — separate IDs, no pooling |
| Trading EA | **BUILD NEW** only after atomic freeze |
| RSF / AIRQMB / census EA logic & economics | **DO NOT REUSE** as confirmation |
| Prior PF/N/charts | **Failure radius only** |

## 5. Universe / TF / split (frozen pre-outcome)

- **FX majors (primary stats):** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD  
- **Separate families (not pooled into FX):** XAUUSD, BTCUSD  
- **TF initial:** M5, M15  
- **DESIGN:** 2016-01-01 → 2021-06-30  
- **VALIDATION:** 2021-07-08 → 2023-03-31  
- **HOLDOUT:** 2023-04-08 → 2024-12-31  
- **Forward seal:** 2025-01-01+  
- **Embargo:** 7 calendar days between regions  

## 6. Trial budget / DSR N

\[
N = \sum \text{every completed distinct-trade-set arm}
\]

across symbols × TF × engines × parameter cells × controls.  
Cost x1/x1.5/x2 on the **same** trade set ≠ extra N.

Planned **cap** (not automatic run count):  
7 × 2 × 3 × 48 inner cells → theoretical discovery surface 2,016 cells before outer-fold multiplies; outer folds amortize search; **N is counted from actual runs only**. Latin Hypercube seed `20260808`. Hierarchical shrinkage required for pair profiles.

## 7. Acceptance gates (campaign floor; stricter of GOAL/gates wins)

- PF ≥ 1.30 (x1); ≥ 1.25 @ x1.5; ≥ 1.00 @ x2  
- Expectancy after cost > 0  
- Executable cadence **2–5 / elapsed week** (GOAL sleeve)  
- Stage-0 **raw** candidates ≥ **25 / week** before filters  
- Max DD ≤ 8%; MC P95 DD ≤ 8%  
- ≥ 70% outer folds positive expectancy  
- No year > 40% of positive gross  
- DSR ≥ 0.95; CPCV PBO ≤ 0.20  
- Parameter-neighbor stability PASS  
- Long/short and session/regime reported separately  

## 8. First Stage-0 ID

`HYP-FIV2-R-EURUSD-M5-STAGE0-001`  
ENGINE_R · EURUSD · M5 · DESIGN · zero-trade · outcome-blind  

## 9. Honest risk statement

Prior free/broker-native five-indicator surfaces (vote, state score, MBB-only, TB-only, AIRQMB, RSF) were **economically killed**. This campaign is Owner-authorized to test a **different decision architecture** (atomic role engines + ablation + nested CV). Edge is **not assumed**. If all preregistered engines/cells fail, result is scoped blocker — not a smart-looking EA.
