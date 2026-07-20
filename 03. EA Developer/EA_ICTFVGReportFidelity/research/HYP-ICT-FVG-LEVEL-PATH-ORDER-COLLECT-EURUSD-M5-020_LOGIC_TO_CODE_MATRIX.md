# Logic-to-code matrix — HYP-020

Frozen before source modification.

| ID | Trader observation / intent | Quantified rule | Source surface | Decision-time proof | Verification | Status |
|---|---|---|---|---|---|---|
| L01 | Liquidity must first be swept/reclaimed | Existing latest closed-M5 pivot sweep/reclaim | `DetectSweep` unchanged | closed M5 only | parent regression | `VERIFIED_PARENT` |
| L02 | Reversal must become visible | Existing max-three-bar body/break/outer-close confirmation | `AdvanceContextState` unchanged | closed bars `1+` | parent regression | `VERIFIED_PARENT` |
| L03 | Human sees hold versus repeated probing | Per-setup directed mid side around sweep extreme | new `LevelPathState` fields | online valid quotes only | red-first path fixtures | `PLANNED` |
| L04 | Churn is event order, not net sign | Count only `FAVORABLE -> ADVERSE` transitions after first favorable | `AccumulateLevelPaths` | tick timestamp before decision | identical-OHLC/different-path fixtures | `PLANNED` |
| L05 | Setup states cannot contaminate each other | Active slot index list + slot-owned counters | add/clear/compact helpers | setup identity | concurrent-setup fixture | `PLANNED` |
| L06 | Collection cannot mutate account | Mode 5 logs HumanContext + LevelPath then clears, no order call | mode-5 confirmation branch | zero entries/lifecycle rows | source contract + run reconciliation | `PLANNED` |
| L07 | Measurement must be distinct and dense | CLEAN/CHURN each ≥20% and ≥2/week in both temporal splits | outcome-blind parser | no future/economic fields | repeat hash + split gates | `PLANNED` |

State path:

`EMPTY → SWEPT + LEVEL_PATH_ACTIVE → (invalidate | timeout | CONFIRM) → LEVEL_PATH_LOGGED → EMPTY`.

Exact-level ties are sticky and never count as crossings. Invalid quotes are
counted but do not change side. Restart with an unsealed interval clears the
setup and does not backfill from OHLC.

No order is allowed. Parent stop/2R/management inputs remain only for
HumanContext comparability and a possible separately frozen child.

