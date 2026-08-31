# AlphaFactory generic research templates

- Copy `ALPHAFACTORY_EA_CONTRACT.template.json` into the EA package and keep
  `telemetry_profile=none` until the lifecycle CSV contract is actually
  implemented.
- Copy prereg/readout templates into `<EA>/research/`; never edit a frozen
  prereg after its hash enters the registry.
- `TASK_PACKET.control.template.json` is a field checklist, not executable
  evidence. Replace every placeholder from current files and broker/data
  evidence. The runner re-hashes all fields immediately before MT5.
- Use `TASK_PACKET.data_acquisition.template.json` only for a canonical
  zero-trade history probe. Its exact authority forbids PF/WR/cost economics,
  requires telemetry off, and closes after data-quality plus non-repaint proof.
- Freeze `acceptance_contract` from this hypothesis prereg (cadence and DD
  budget). Do not copy 2–5/week or 8% DD from an old registry row or from this
  template's REPLACE placeholders. The runner re-hashes packet gates immediately
  before MT5 and rejects weaker-than-frozen values.
- A challenger packet adds the frozen matched-control run ID and hashes. The
  runner rejects stale registry, source, includes, Git, cost or control identity.
- After a short prereg, go to compile/Model-0. `LOGIC_TO_CODE_MATRIX` is
  optional implementation hygiene, not a Model-0 gate.
- `EA_DELIVERY_PACKET` and Grok chart forensics are promotion/postmortem,
  additional to `validate-full`, not required before the first baseline.
- For `zero_trade_terminal`, replace `economic_analysis` with
  `funnel_analysis`; economics and win/loss causes are explicitly
  `NOT_APPLICABLE_ZERO_TRADES`, while rejection causes and representative
  rejection charts remain mandatory.
- Use `GROK_CHART_FORENSICS_PACKET.template.json` for large visual postmortems.
  It freezes sampling, decision/anatomy separation, decision-time indicator
  provenance, two reviewer lenses, five-case serial jobs and fail-closed
  coverage. It is an advisory analysis packet, not run or promotion authority.

Generic `lifecycle-v3` requires `InpEnableTelemetry` and exactly one
`*_LifecycleTrades_*.csv` with the columns enforced by
`tools/build_verified_cost_artifact.py`, plus a bound `*_RunMeta_*.json`.
The RunMeta object must use `alphafactory_run_meta.v1` and bind `run_id`,
`ea_name`, `symbol`, and `telemetry_profile=lifecycle-v3`; its filename must
contain the same `run_id`.
