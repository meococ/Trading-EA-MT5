# HYP-CRSI-XAUUSD-H1-001 — Source Result

Verdict: `PARK_SOURCE_FEASIBILITY_EXACT_CRSI_3_2_100_EXTREME_REENTRY`

The sole outcome-blind source attempt completed durably and deterministic replay matched. The exact CRSI `(3,2,100)` H1 extreme-reentry mapping is parked because executable exact-next coverage was `96.0422%`, below the frozen `97.0%` gate.

## Reconciled source metrics

- Native H1 source rows through 2022: `107,679`
- Prehistory rows: `78,218`
- Design rows / feature usable: `29,461 / 29,461` (`100%`)
- Raw events: `1,137`
- Executable events: `1,092`
- Gap-consumed raw events: `45`
- Exact-next coverage: `1,092 / 1,137 = 96.042216%` — **FAIL**
- Cadence: `4.186199/week` — PASS
- LONG / SHORT: `526 / 566` (`48.1685% / 51.8315%`) — PASS
- Year events 2018–2022: `229 / 206 / 209 / 222 / 226`
- Each-year cadence: `3.9507–4.3918/week` — PASS
- Maximum year share: `20.9707%` — PASS
- Direction conflicts: `0`

All gates except exact-next coverage passed. The event ledger contains 1,092 unique, strictly ordered rows and every row satisfies the exact timestamp, threshold, finite-value and allowlist contract.

## Epistemic boundary

No post-event OHLC, entry/exit price, return, PnL, trade simulation, cost, PF, validation or holdout data was opened. This result does not say CRSI lacks market edge. It says only that this exact native-H1 re-entry mapping fails the frozen executable-source coverage requirement.

The gate will not be lowered, a later-gap execution will not be substituted, and thresholds/session/debounce will not be changed under this ID. No MQL5 build is authorized from this result.
