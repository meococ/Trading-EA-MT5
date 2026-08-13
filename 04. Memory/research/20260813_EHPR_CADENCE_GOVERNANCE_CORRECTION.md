# EHPR cadence-governance correction — 2026-08-13

Verdict: `EHPR002_TERMINAL_ID__SOURCE_PASS__ECONOMICS_UNTESTED__STALE_CADENCE_SCHEMA_CORRECTED_PROSPECTIVELY`

## What happened

`HYP-EHPR-EURUSD-M15-002` completed one clean outcome-blind source attempt. It produced 21,618 executable EURUSD M15 Hilbert phase-cross events at 82.9638 events/week, with all frozen source gates passing and every outcome/economic counter remaining zero.

The hypothesis had nevertheless frozen a 2–5 completed-trades/week economic contract because `CANDIDATE_REGISTRY.schema.json` still forced every economic row into that legacy interval. That restriction contradicted the higher-authority 2026-08-11 `GOAL.md` rule: new mechanisms must preregister cadence from their own sample-size, cost, turnover, and capacity needs; there is no default 2–5/week cap.

The exact HYP002 ID remains terminal. Its frozen contract cannot be rewritten after the source counts were observed, and the same phase-cross definition cannot be reopened under a new ID merely to choose a friendlier cadence range. The post-source contract-mismatch decision is therefore an administrative verdict on HYP002, not an economic finding about Hilbert phase and not proof of no edge.

## Prospective correction

The registry schema now accepts any strictly positive `min_trades_per_week` and `max_trades_per_week`; the validator continues to require `min <= max`. Three focused schema tests prove that low-cadence and high-cadence mechanism contracts are accepted while zero/nonpositive cadence is rejected.

This correction applies only to future materially fresh candidates before their counts are observed. It does not revive HYP002, authorize MQL5/MT5, expose outcomes, or weaken PF, cost-stress, DD, validation, holdout, promotion, paper, or live gates.
