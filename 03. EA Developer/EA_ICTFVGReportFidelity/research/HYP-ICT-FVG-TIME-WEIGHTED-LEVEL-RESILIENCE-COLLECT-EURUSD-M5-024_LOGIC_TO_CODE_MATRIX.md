# Logic-to-code matrix — HYP-024

Frozen before source modification.

| ID | Intent | Frozen rule | Source surface | Verification | Status |
|---|---|---|---|---|---|
| L01 | Preserve context | Existing closed-M5 sweep/reclaim | `DetectSweep` unchanged | parent snapshot regression | `VERIFIED_PARENT` |
| L02 | Preserve confirmation | Existing bounded three-bar reversal | `AdvanceContextState` unchanged | parent regression | `VERIFIED_PARENT` |
| L03 | Measure level holding | Last-valid-side millisecond carry | setup resilience fields | synthetic duration fixtures | `PLANNED` |
| L04 | Add non-OHLC information | favorable_ms vs adverse_ms sign | mode-6 label | same prices/OHLC/count, different times | `PLANNED` |
| L05 | Keep causal clock | `MqlTick.time_msc`, tail to decision only | accumulator + logger | decision-boundary fixture | `PLANNED` |
| L06 | Treat equality correctly | credit elapsed then retain side | accumulator | equality fixture | `PLANNED` |
| L07 | Treat invalid quote correctly | no side or clock mutation | accumulator | invalid-gap fixture | `PLANNED` |
| L08 | Prevent contamination | separate compact active-slot list | add/clear/accumulate helpers | concurrent setup fixture | `PLANNED` |
| L09 | Zero account mutation | log HC+LevelResilience, clear, return | mode-6 branch | no order call + zero lifecycle | `PLANNED` |
| L10 | Prove separability | each label >=20% and >=2/week in both splits | outcome-blind parser | deterministic replay | `PLANNED` |

State path:
`EMPTY -> SWEPT+RESILIENCE_ACTIVE -> FIRST_FAVORABLE -> (invalidate|timeout|CONFIRM) -> RESILIENCE_LOGGED -> EMPTY`.

No pre-first-favorable duration, OHLC reconstruction, post-decision tick,
economic outcome or post-hoc threshold is allowed.

