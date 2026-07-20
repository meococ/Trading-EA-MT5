# HYP-016R1 - frozen replacement outcome-blind context collection

## Amendment boundary

- Hypothesis: `HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1`.
- Parent: rejected instrumentation run of HYP-016, run `20260719_211915`.
- V1 plan SHA-256:
  `F2832194278BBB2D9171C45612FD81F1DDE8ADE8DD1BE6C4A30AE8022C714654`.
- The parent tester completed, but AlphaFactory rejected it before acceptance
  because RunMeta declared `lifecycle-v3+human-context-v1` while the package
  capability contract and manifest declared `lifecycle-v3`.
- Before this amendment, only RunMeta identity/counters, HumanContext schema
  samples, lifecycle row count, and the run manifest were inspected. No report
  profit, drawdown, trade exit, PnL, commission, MFE, MAE, or other outcome was
  read. The rejected run opened zero entries according to RunMeta.
- The sole permitted source delta versus HYP-016 is embedded identity/version
  plus the telemetry metadata correction
  `TELEMETRY_PROFILE="lifecycle-v3"`. Human-context schema remains separately
  declared as `human-context-v1`; signal, context, risk, and execution logic
  must remain byte-equivalent after normalizing those three identity fields.
- Exactly one replacement MT5 collection run is authorized. The rejected
  parent is retained as invalid instrumentation evidence, not an economic run.

## Frozen run

- Harness: AlphaFactory only; configured portable FivePercent tester on D:.
- Symbol/timeframe/model: `EURUSD`, `M5`, Model `0`.
- Window: `2018.01.01` through `2026.07.19`.
- Deposit/leverage/spread: `100000`, `100`, tester `current`.
- Role/tier: `control`, `trade-only`.
- Required sidecars: `*_HumanContext_*.csv`,
  `*_LifecycleTrades_*.csv`, `*_RunMeta_*.json`.
- Exact preset:
  `presets/EURUSD_M5_HYP016_HIGHRECALL_CONTEXT_COLLECT.set`, SHA-256
  `353C06AC6B631E1FB6E131BD91C68FC4E94DCAF7794F2C976CFCFDBC2E55264C`.
- `InpResearchAutoMode=false`, `InpSignalMode=0`, telemetry enabled, news guard
  disabled, risk `0.01`, maximum account drawdown threshold `100`, magic
  `5600726`; every other input is the exact frozen preset value.
- Trading is disabled. Zero attempted/opened entries and zero lifecycle data
  rows are mandatory.

## Outcome-blind collection contract

The parser may read only HumanContext rows, RunMeta identity/diagnostic counters,
lifecycle header/row count, and manifest identity/history quality. It must not
open the MT5 report or any outcome-bearing field.

Required gates:

1. source, EX5, compile log, V2 plan, preset and dependency closure are
   hash-bound after a 0/0 compile;
2. exact-source/dependency non-repaint audit passes with zero findings;
3. AlphaFactory accepts all required sidecars and exact identity/profile;
4. history quality is at least 99 percent;
5. lifecycle data rows, `entries_attempted`, and `entries_opened` all equal 0;
6. HumanContext rows equal `human_context_snapshots + human_context_invalid`;
7. event IDs and `(decision_time, direction, reason, event_id)` are unique;
8. rows cover both directions, London and New York, and every available year;
9. complete-context fraction is at least 99 percent and no future/outcome
   column exists;
10. elapsed-calendar cadence of the collection is at least 2 per week;
11. exact parser rerun yields the same canonical result hash.

## Frozen pre-economic natural policy

Without reading outcomes, count only:

```text
valid == 1
AND context_state IN {
  EXTERNAL_SWEEP_WITH_ROOM,
  INTERNAL_SWEEP_WITH_ROOM
}
```

This policy requires a directional pool, at least frozen 2R room, entry within
the H1/H4 20-bar dealing-range envelope, and not both H1/H4 structures opposed.
It adds no tunable threshold.

- If cadence is below 2 candidates per elapsed calendar week, or either
  direction/session/available year is absent: stop with
  `FRONTIER_CONTEXT_POLICY_CADENCE_FAILED_NO_ECONOMIC_RUN`.
- If it passes: freeze a fresh HYP-017 policy plan and source hash before
  reading any outcome or launching an economic run.
- HYP-016R1 can never authorize promotion, paper, or live trading.
