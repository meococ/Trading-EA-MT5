# Prereg — HYP-SB-SPARK-BOOK-001

Status: `FROZEN_RESEARCH_SCREEN`  
Date: 2026-07-14  
Owner mandate: `ITERATE_EXPERIMENT_TEARDOWN_REBUILD_20260714_1909`  
Parent / related: Phase 0 `HYP-PORTFOLIO-COMPOSE-001` remains
`BLOCKED_NOT_READY_FOR_PREREG_FREEZE` (contamination). This ID is a **clean
independent research-book child** for SB+Spark iteration — not a clearance of
Phase 0 contamination.

## Hypothesis

Equal-join (and a priori weighted/overlap variants) of parked
`EA_SilverBullet` weekend-flat A1 and `EA_M15SparkAsian` on USDJPY M15 clears
research PF>1.30 and 2–5 trades/week elapsed under tester cost, and remains
the near-GOAL champion while expansion sleeves dilute PF.

## Frozen sleeve identity (exact; not PF-ranked after this prereg)

| Role | EA | Authoritative run | Deposit contract |
|---|---|---|---|
| Sleeve A | `EA_SilverBullet` | `20260714_002505` | 100000 |
| Sleeve B | `EA_M15SparkAsian` | `20260714_002614` (twin `002821`) | **must be re-run at 100000** for capital-honest book |

Selection rule: Phase-0-bound pair only. Explicitly excluded: ITSM, LondonORB,
NY, PDH, USBILL, Cobra, InsideBar, any killed shelf.

## A priori option set (frozen before this campaign’s ranking)

From offline matrix V1/V2 tools (IDs stable):

1. `OPT-BASE-SB-SPARK-EQ` — equal-join
2. `OPT-W-SB70-SPARK30` — risk weight 70/30
3. `OPT-OV-DROP-SAME-M15-BAR` — drop later same-bar entry
4. Cost ladder: `$0/$1/$2/$3/$5/$8/$10` per trade haircut
5. Capital normalize proxy `CAPNORM_SPARK_X10` until Deposit=100000 twin lands

**Banned:** hour/day veto mined from by_hour/by_weekday; Spark Mon–Thu densify;
USBILL retune; post-hoc sleeve swaps after reading pooled PF.

## Kill / park / promote screens (research-proxy)

| Gate | Rule |
|---|---|
| Kill expansion | Pooled PF < 1.05 or tpw outside [1.0, 8.0] |
| Park | 1.05 ≤ PF ≤ 1.30 or cadence miss |
| Research survive | PF > 1.30 and tpw ∈ [2, 5] on tester `current` |
| Confirmed / GOAL | **Blocked** until Real QFSI + gates file |

## Cost grade

`UNVERIFIED_TESTER_DEFAULT` until `FivePercentOnline-Real` QFSI. Missing
commission ≠ 0.

## EA architecture decision

Legacy `03. EA Developer/EA_Portfolio/` (CBR/ITSM/LNY/IB) is **torn down for
this lane** — contaminated with killed/parked unrelated sleeves. Do not compile
it as the SB+Spark book. Dual-instance AlphaFactory compose (two EX5, one
symbol window) is the research scaffold until a clean `EA_SBSparkBook` is
justified by Owner after capital twin + Real cost.

## Model 0 authorized this campaign

1. `EA_M15SparkAsian` Deposit=100000, USDJPY M15 2021-2025, same defaults as
   `002614` / `002821` (no densify overrides) — capital twin only.
2. No USBILL. No ITSM re-run. No LondonORB retune.

## Non-repaint

Both sleeves already closed-bar[1] Model 0 parked; no signal logic change in
capital twin.
