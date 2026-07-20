# AlphaFactory generic research templates

- Copy `ALPHAFACTORY_EA_CONTRACT.template.json` into the EA package and keep
  `telemetry_profile=none` until the lifecycle CSV contract is actually
  implemented.
- Copy prereg/readout templates into `<EA>/research/`; never edit a frozen
  prereg after its hash enters the registry.
- `TASK_PACKET.control.template.json` is a field checklist, not executable
  evidence. Replace every placeholder from current files and broker/data
  evidence. The runner re-hashes all fields immediately before MT5.
- Copy `acceptance_contract` exactly from the latest canonical registry row.
  The runner rejects weaker or different packet gates and passes the frozen
  values to unified validation.
- A challenger packet adds the frozen matched-control run ID and hashes. The
  runner rejects stale registry, source, includes, Git, cost or control identity.
- Start every implementation with `LOGIC_TO_CODE_MATRIX.template.md`. It keeps
  trader intent, quantified rule, role, source location, decision-time data,
  telemetry and test proof in one pre-outcome matrix.
- A strategy-development closeout must copy
  `EA_DELIVERY_PACKET.template.json`, replace every placeholder and pass
  `alpha.ps1 delivery -Packet <packet>`. This gate is additional to
  `validate-full`: it requires logic fidelity, compile/tests/non-repaint,
  report/lifecycle/log reconciliation, full performance attribution and a
  hash-bound multi-timeframe casebook.
- For `zero_trade_terminal`, replace `economic_analysis` with
  `funnel_analysis`; economics and win/loss causes are explicitly
  `NOT_APPLICABLE_ZERO_TRADES`, while rejection causes and representative
  rejection charts remain mandatory.

Generic `lifecycle-v3` requires `InpEnableTelemetry` and exactly one
`*_LifecycleTrades_*.csv` with the columns enforced by
`tools/build_verified_cost_artifact.py`, plus a bound `*_RunMeta_*.json`.
The RunMeta object must use `alphafactory_run_meta.v1` and bind `run_id`,
`ea_name`, `symbol`, and `telemetry_profile=lifecycle-v3`; its filename must
contain the same `run_id`.
