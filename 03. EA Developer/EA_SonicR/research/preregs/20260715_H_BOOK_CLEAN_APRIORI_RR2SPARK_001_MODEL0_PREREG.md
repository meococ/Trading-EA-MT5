# Prereg — HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001 (book Model 0 unlock)

Date: 2026-07-15  
State on freeze: `preregistered`  
Authority: Owner continue-R&D mandate — unlock book Model 0 (portfolio EA)  
Nested: lead self-merge; ChatGPT login-walled (do not stall)

## Identity

- Hypothesis ID: `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`
- EA: `EA_SBSparkBook` (`EA_SBSparkBook.mq5` v1.10)
- Parent / sleeve authority:
  - A_RR2 `HYP-SB-MAXKZ2-RR2-FRICTION-001` run `20260714_194548`
  - B_SPARK shelf `20260714_193358` (MaxPerDay=2 defaults)
- Freeze memo: `readouts/20260715_CLEAN_BOOK_APRIORI_UNIVERSE_FREEZE.md`
  SHA256 `F18FAB12ECCBD3FF09A4FA03317AB13A59DFCAE00BA9491B640D69D2B728931C`
- Offline stress: `preflight/20260715_CLEAN_BOOK_APRIORI_RR2SPARK_STRESS.json`
  SHA256 `5F41A94BCFC9185C6771E60616FE5A7855C770D795B28AFCC2C2AB36C4DBB28B`
- Prior killed dual-runner (different binding): `HYP-PORTFOLIO-SB-SPARK-RUNNER-001`
  A1+Spark `20260714_224302` — **not** this contract

## Thesis

Code the frozen clean-book PRIMARY topology (RR2 ∪ Spark, equal 1:1 risk,
heat=1, priority A>B) as one closed-bar dual-magic EA and run **Model 0**
under honest tester/`spread=current` labels. Offline PRIMARY already
`DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL` (PF@$12=1.184, tpw=3.241).
Book Model 0 was WITHHELD only for missing portfolio EA — Owner now unlocks
the EA + Model 0 path for **honest book-level tester evidence**, not GOAL.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol / TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | **0** |
| Spread | `current` (Demo/tester) |
| Cost label | `UNVERIFIED_TESTER_CURRENT_SPREAD` — missing fields ≠ 0; **not** QFSI |
| Sleeve A module | SB RR2/MaxKZ2/weekend-flat (mirrors 194548 overrides) |
| Sleeve A magic | `20260715` |
| Sleeve A risk | `0.5` |
| Sleeve B | SparkAsian defaults (193358 / MaxPerDay=2) |
| Sleeve B magic | `880930` |
| Sleeve B risk | `0.5` |
| Heat | `InpHeatCap1=1` — max concurrent open sleeves = 1 |
| Priority | A (SB) processed first; B enters only if A flat |
| Master overrides | empty (bindings baked into module `#define`s + input defaults) |
| EXTENDED ITSM | **out of scope** this Model 0 (PRIMARY only) |

### Sleeve A constants (baked; match 194548)

`MaxTradesPerKZ=2; TP_RR_LDN=2.0; TP_RR_NY=2.0; UseWeekendFlat=1; FridayFlat=21:45; RiskPct=0.5`

### Caps (a priori; fail-closed research screen)

| Cap | Rule |
|---|---|
| Haircut diagnostic | +$12 RT on closed trades (post-run stress; not tester native) |
| Weekly corr | ≤ 0.35 (offline already PASS) |
| Same-M15 overlap | ≤ 0.05 |
| Heat | concurrent open sleeves ≤ 1 |
| Cadence screen | pooled tpw ∈ [2, 5] elapsed calendar weeks |
| PF research screen | tester PF > 1.30 (diagnostic vs GOAL) |
| PF GOAL screen | PF@$12 > 1.30 — offline already FAIL; Model 0 must not claim GOAL |

## Chart-state / non-repaint

- Decisions on closed M15 bar only (modules use new-bar gate + shift≥1 HTF).
- No densify of RR / MaxKZ / Spark MaxPerDay / FVG / exit / exo / W1–W27 / R-series.
- Non-repaint audit required after this signal/data-access change (dual-sleeve heat).

## Test Plan

```text
.\alpha.ps1 compile "EA_SBSparkBook"
.\alpha.ps1 backtest "EA_SBSparkBook" -Symbol USDJPY -Period M15 `
  -From "2021.01.01" -To "2025.12.31" -Model 0 -Deposit 100000 `
  -TimeoutSec 7200 -HypothesisId "HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001" `
  -RunRole "challenger" -Spread "current"
```

## Kill / Park / HIT (honest; no GOAL claim)

| Gate | Rule |
|---|---|
| KILL | tester PF < 1.00 OR tpw ∉ [1.0, 6.5] OR N < 80 OR compile/runtime fail |
| PARK | survives kill but tester PF ≤ 1.30 OR tpw ∉ [2, 5] |
| HIT research bar | tester PF > 1.30 ∧ tpw ∈ [2, 5] under `spread=current` |
| GOAL | **FORBIDDEN claim** this turn — cost freeze GAP; offline @$12 already FAIL |
| Densify | **FORBIDDEN** after readout |

## Explicit non-claims

- Not Phase-0 clearance (`CONTAMINATED` stands).
- Not QFSI / Real confirmed cost.
- Not portfolio-sleeve promotion.
- Not re-burn of sleeve authority `194548` / `193358`.
- Not rescue of killed A1 book `224302`.

## Banned

- Post-hoc knob retune from this Model 0 readout
- Adding ITSM / MaxKZ densify / Spark 3PD twin `193732`
- Inventing cost from missing commission/slip fields
- Promoting RealP50 diagnostic (~1.36) over a priori +$12 screen
