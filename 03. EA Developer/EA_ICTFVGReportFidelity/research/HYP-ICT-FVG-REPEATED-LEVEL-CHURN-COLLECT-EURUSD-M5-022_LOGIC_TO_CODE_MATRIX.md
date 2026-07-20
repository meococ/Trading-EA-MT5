# Logic-to-code matrix — HYP-022

Frozen before source modification.

| ID | Intent | Frozen rule | Source surface | Verification | Status |
|---|---|---|---|---|---|
| L01 | Sweep/reclaim context | Existing closed-M5 pivot sweep/reclaim | `DetectSweep` unchanged | parent regression | `VERIFIED_PARENT` |
| L02 | Bounded visible reversal | Existing max-three-bar confirmation | `AdvanceContextState` unchanged | parent regression | `VERIFIED_PARENT` |
| L03 | Measure repeated probing | Slot-owned side around sweep extreme | setup path fields | synthetic transitions | `PLANNED` |
| L04 | Add non-OHLC information | ORDERLY count <=1 vs REPEATED_CHURN >=2 | mode-5 label | identical-OHLC counterexample | `PLANNED` |
| L05 | Avoid HYP-020 redundancy | 0-vs-any pierce is forbidden | tests/readout | formal regression | `PLANNED` |
| L06 | Prevent setup contamination | compact active slot list | add/clear/accumulate helpers | concurrent setup fixture | `PLANNED` |
| L07 | Exclude future tick | process closed bar before accumulating new-bar tick | `OnTick` ordering | boundary fixture/static audit | `PLANNED` |
| L08 | Zero account mutation | log HumanContext+LevelPath, clear, return | mode-5 branch | no order call + zero lifecycle | `PLANNED` |
| L09 | Prove separability before economics | both labels >=20% and >=2/week in both splits | outcome-blind parser | repeat hash | `PLANNED` |

State path:
`EMPTY -> SWEPT+PATH_ACTIVE -> (invalidate|timeout|CONFIRM) -> PATH_LOGGED -> EMPTY`.

Exact-level ties are sticky. Invalid quotes never change state. Restart clears
unsealed state without OHLC reconstruction. No order is allowed.

