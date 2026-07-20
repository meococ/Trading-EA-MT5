# Logic-to-code matrix — HYP-026

Frozen before source modification.

| ID | Intent | Frozen rule | Source surface | Verification | Status |
|---|---|---|---|---|---|
| L01 | Preserve sweep | Existing closed-M5 pivot breach/reclaim | `DetectSweep` predicate unchanged | parent snapshot regression | `VERIFIED_PARENT` |
| L02 | Preserve confirmation | Existing three-bar extreme confirmation/invalidation | `AdvanceContextState` unchanged | parent regression | `VERIFIED_PARENT` |
| L03 | Preserve exact breached level | Store same pivot used by sweep predicate | `AddSweepSetup` + `swept_pivot_level` | long/short source fixture | `PLANNED` |
| L04 | Change geometry only | mode 7 uses pivot, mode 6 retains sweep extreme | setup initialization | inside-wick non-tautology fixture | `PLANNED` |
| L05 | Keep causal clock | HYP-024 `time_msc` accumulator unchanged | resilience accumulator | duration/equality/invalid fixtures | `PLANNED` |
| L06 | Prevent slot contamination | existing compact setup-owned registry supports mode 7 | register/clear/accumulate | concurrent-slot fixture | `PLANNED` |
| L07 | Zero account mutation | HC + LevelResilience then clear/return | mode-7 branch | no order call + empty trade sidecars | `PLANNED` |
| L08 | Bind audit identity | v1.27, HYP-026, mode 7, exact preset | identity/RunMeta | source/EX5/log receipt | `PLANNED` |
| L09 | Prove separability | each label >=20% and >=2/week in both splits | outcome-blind parser | deterministic replay | `PLANNED` |

State path:
`EMPTY -> SWEPT+PIVOT_DWELL_ACTIVE -> FIRST_FAVORABLE -> (invalidate|timeout|CONFIRM) -> LEVEL_RESILIENCE_LOGGED -> EMPTY`.

No new threshold, HTF veto, subgroup, OHLC reconstruction, economic outcome or
post-decision quote is allowed.
