# HYP025 post-claim self-rejection failure

Verdict: `KILL_POSTCLAIM_ONE_SHOT_SELF_REJECTION_NO_ALPHA_NO_MT5_NO_ECONOMIC_VERDICT`

The sole `STBS025-MODEL0-TRAIN-001` execution created its durable early claim, then the later authority blocker rejected that exact newly created marker as an already-consumed attempt. This is a runner reconciliation defect, not a strategy, data, cost or economic result.

## Exact immutable evidence

- screened authority raw-row SHA256: `107B71A2A6585E7354687D6371D4AAFE68C529CAA94F6E5356F2E5D808D7E961`
- packet SHA256: `1C70DFB65F8CBEE3DAD2727B29A8985A64227617C0F7F25B536F9FBA306F0039`
- attempt start: `02. AlphaFactory/runtime/model0_economic_attempts/HYP-STBS-XAUUSD-M15-025/STBS025-MODEL0-TRAIN-001/attempt_started.json`
- attempt start SHA256: `9E797CF2E538D4001B896C2DF526F03A91FBA478B6A230AA4AB8331C96C3F988`
- failed terminal: `02. AlphaFactory/runtime/model0_economic_attempts/HYP-STBS-XAUUSD-M15-025/STBS025-MODEL0-TRAIN-001/attempt_terminal.json`
- failed terminal SHA256: `0427459036C393EDEA80FD9844D520A0C514571FD83AF281DC0AC6C86BD0428B`
- exact terminal error: `Execution blocked: Model0 economic one-shot attempt is already consumed` for the same start path
- the attempt root contains exactly those two files
- terminal status is `FAILED`, binds the exact start hash, and has `run_id=null`, `run_dir=null`, `same_id_retry_authorized=false`
- `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV12` is absent

## Scope and counters

- packet-build attempts consumed: 1
- Model0 attempts consumed: 1
- run-compile attempts consumed: 0
- Alpha runs, MT5 launches, Model0 runs: 0
- orders, trades, returns and performance trials: 0
- economics, validation and holdout: unopened

No report, market data, order, deal, PnL, PF, cost rebuild or outcome was opened. No economic inference is admissible.

## Root cause and lawful next lane

`New-EarlyModel0EconomicLaunchClaim` correctly fsynced the one-shot marker. Later, `Add-Model0EconomicLaunchAuthorityBlockers` performed the generic pre-existing-marker check after that claim and rejected the exact in-memory marker it should have reconciled.

HYP025 is terminal and cannot retry. A fresh HYP026 identity-only engineering child may preserve every strategy/data/cost/acceptance parameter while changing identity/magic and fixing only this runner invariant: a fresh execution may accept the exact in-memory early marker whose path/hash/registry/packet identity reconciles and whose terminal is absent; every pre-existing, missing, mismatched or terminalized marker remains rejected.
