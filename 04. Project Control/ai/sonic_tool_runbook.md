# Sonic R Tool Runbook

Updated: 2026-05-03

Scope: `EA_SonicR`, AlphaFactory, MetaQuotes-Demo symbols `XAUUSD`, `EURUSD`,
`GBPUSD`.

## Purpose

Use this file when a session needs to compile, backtest, analyze, compare,
audit, label, snapshot, or clean Sonic R evidence. AlphaFactory and MT5 tester
artifacts remain the execution truth. These tools speed up research; they do
not promote an EA by themselves.

## Standard Run Closure

After any meaningful Sonic R backtest, use this order:

1. Compile/backtest/analyze through AlphaFactory or `alpha_json.ps1`.
2. Run `validate-full`.
3. Compare to the frozen baseline on the same model/window.
4. Run cost stress.
5. Run market-phase attribution for XAU/S1/sideway questions.
6. Run GoldRegime audit when `InpEnableGoldRegimeTelemetry=1`.
7. Build or refresh casebook/index artifacts.
8. Run evidence audit.
9. Capture bounded MT5-native snapshots only for selected cases.
10. Archive/clean stale telemetry after preserving cited evidence.

## Core Commands

### AlphaFactory JSON Wrapper

Use when an agent or MCP needs structured output from `alpha.ps1`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/alpha_json.ps1" `
  -Action status
```

Compile:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/alpha_json.ps1" `
  -Action compile `
  -Name "EA_SonicR"
```

Validate a run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/alpha_json.ps1" `
  -Action validate-full `
  -Report "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/report.html" `
  -Out "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/alpha_json_validate_full.json"
```

Important: `success=true` means the wrapper completed. Strategy readiness is
the `headline.validation_verdict` and gate stack, not wrapper success.

### Candidate Compare

Use for every challenger before reading PF in isolation.

```powershell
python "02. AlphaFactory/tools/sonic_candidate_compare.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --baseline 20260501_000718 `
  --out "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_candidate_compare_vs_20260501_000718.json"
```

Reject candidates that only improve PF while net, monthly economics, validation,
or execution realism worsens.

### Repro Drift Map

Use before any cadence/gate/default patch when run counts drift across
otherwise similar configs.

```powershell
python "02. AlphaFactory/tools/sonic_repro_drift_map.py" `
  20260501_000718 20260501_150443 20260501_150910 20260501_151422 `
  --out-json "02. AlphaFactory/runs/EA_SonicR/20260501_151422/analysis/sonic_repro_drift_map.json" `
  --out-md "02. AlphaFactory/runs/EA_SonicR/20260501_151422/analysis/sonic_repro_drift_map.md"
```

Current use: explain the `282 / 95 / 237` XAUUSD M5 drift before treating any
cadence change as strategy improvement.

### Cost Stress

Use as first-pass falsification. It is report-only unless broker-informed cost
conversion is added later.

```powershell
python "02. AlphaFactory/tools/sonic_cost_stress.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --base-cost-per-trade 0.50 `
  --out "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_cost_stress_report_only_050.json"
```

Do not call a run robust if PF collapses under small per-trade costs.

### Evidence Audit

Use before a run is cited in docs or used as a baseline.

```powershell
python "02. AlphaFactory/tools/evidence_audit.py" <RUN_ID> `
  --baseline 20260501_000718 `
  --require-casebook `
  --require-native-snapshot `
  --require-compare `
  --require-cost `
  --out "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/evidence_audit.json"
```

Status meanings:

- `PASS`: required files exist and validation has no audit warnings.
- `REVIEW`: required files exist, but validation or another gate still blocks
  promotion.
- `FAIL`: required evidence is missing or empty.

### Casebook Index

Use after casebook, labels, cost stress, compare, or snapshots change.

```powershell
python "02. AlphaFactory/tools/sonic_casebook_index.py" `
  --run-dir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>"
```

Outputs:

- `analysis/casebook_analysis_index.json`
- `analysis/casebook_analysis_readout.md`

### Machine Label Audit

Use for pre-entry heuristic labels only. It must not use outcome/PnL/MFE fields
as inputs.

```powershell
python "02. AlphaFactory/tools/sonic_state_label_audit.py" `
  --cases "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_state/sonic_state_cases.csv" `
  --out-labels "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_state/sonic_state_machine_labels.csv" `
  --out-audit "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_state/sonic_state_label_audit.json" `
  --out-md "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_state/sonic_state_label_audit.md"
```

### Population Evaluation

Use to test pre-entry feature lift on the full opportunity population, not the
biased casebook sample.

```powershell
python "02. AlphaFactory/tools/sonic_population_eval.py" `
  --run-dir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --symbol XAUUSD
```

No EA rule is authorized unless a feature is stable across time splits and cost
stress does not collapse.

### S1 Gate Audit

Use before coding any dedicated S1 gate or S1 risk route.

```powershell
python "02. AlphaFactory/tools/sonic_s1_gate_audit.py" <RUN_ID> `
  --cost 0.50 `
  --out "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_s1_gate_audit.json" `
  --out-md "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>/analysis/sonic_s1_gate_audit.md"
```

This is audit-only. A good bucket in this report is not a rule until it survives
pre-registration, matched backtest, validation, and cost stress.

For deeper S1 opportunity/trade joins, target-RR buckets, removal buckets, and
half-year cost stability:

```powershell
python "02. AlphaFactory/tools/sonic_s1_deep_anatomy.py" `
  --run-dir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --cost 0.50 `
  --min-n 15 `
  --min-kept 80 `
  --top 25
```

Outputs:

- `analysis/sonic_s1_deep_anatomy.json`
- `analysis/sonic_s1_deep_anatomy.md`
- `analysis/sonic_s1_deep_anatomy_candidates.csv`

Use this before changing S1 geometry. Current evidence says very high S1
`target_rr` can be a tight-stop trap, not quality.

### Sideway Range Probe

Use before coding any sideway/range-entry rule. It reads PVSRA/SR sidecars and
labels outer-quartile range rotations by forward TP/SL/MFE/MAE.

```powershell
python "02. AlphaFactory/tools/sonic_sideway_range_probe.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --horizon-bars 12 `
  --min-width-atr 0.8 `
  --max-width-atr 3.6 `
  --min-crosses 3 `
  --min-pvsra-strength 1.0 `
  --min-rr 0.8
```

Outputs:

- `analysis/sonic_sideway_range_probe.json`
- `analysis/sonic_sideway_range_probe.md`
- `analysis/sonic_sideway_range_probe.csv`

Current evidence from `20260502_223437`: generic range rotation is not stable
enough to code. Strict probe had only `2` candidates; loose probe had `59`
with total label R `-1.2284`; raw probe over `1256` candidates was near zero.
Do not loosen R1 without a new compression-to-impulse thesis.

### Market Phase Attribution

Use after telemetry-on Sonic R runs when the question is whether the EA profits
in impulse, transition, or sideway regimes. The tool streams the PVSRA/SR
sidecar and joins only actual trade entry bars, so it can handle large sidecars
without loading the full CSV into memory.

```powershell
python "02. AlphaFactory/tools/sonic_market_phase_attribution.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>"
```

Outputs:

- `analysis/market_phase_attribution.json`
- `analysis/market_phase_attribution.md`
- `analysis/market_phase_attribution_by_phase.csv`
- `analysis/market_phase_attribution_by_lane_phase.csv`
- `analysis/market_phase_trade_labels.csv`

Current evidence from long-window run `20260502_232935`: the current XAU stack
fails `2019-2025` with PF `0.952`; `SIDEWAY_WIDE` is the major drag (`103`
trades, net `-165.91`, PF `0.7441`), while impulse phases are only mildly
positive. Treat 2024-2025 as a favorable regime pocket, not proof of robust
edge.

### S1 Phase Feature Audit

Use after market-phase attribution before coding any S1 phase/context rule. It
tests simple keep/drop candidates against report-only cost and half-year
stability.

```powershell
python "02. AlphaFactory/tools/sonic_s1_phase_feature_audit.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --cost-per-trade 0.50
```

Outputs:

- `analysis/sonic_s1_phase_feature_audit.json`
- `analysis/sonic_s1_phase_feature_audit.md`
- `analysis/sonic_s1_phase_feature_audit.csv`

Current evidence from `20260502_232935`: `REJECT_NO_PASSER`. Dropping S1
sideway, keeping only impulse, blocking weak hours, or adding Dragon/HTF/body
context does not pass cost and half-year stability. No EA patch is authorized
from those simple rules.

### Phase Case Sampler

Use before MT5-native screenshots when the casebook must target market-phase
questions instead of generic top wins/losses.

```powershell
python "02. AlphaFactory/tools/sonic_phase_case_sampler.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --per-bucket 6
```

It writes `analysis/entry_asof_casebook/cases.csv`, which can then feed the
existing MT5 snapshot flow:

```powershell
& "02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1" `
  -RunDir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  -SampleReason "s1_sideway_wide_loss,s1_impulse_win" `
  -MaxCases 12 `
  -RunMt5Startup `
  -CleanupStaging
```

Current smoke on `20260502_232935` collected `12/12` MT5-native screenshots for
S1 sideway-wide losses versus S1 impulse wins.

### Market Regime Profit Atlas

Use when aggregate PF looks regime-dependent and the question is which broader
gold-market state carries profit. This tool enriches trades with 3h/8h/1d/5d/
10d/20d trend, range width, volatility, trend efficiency, trend alignment, and
macro-year attribution tags.

```powershell
python "02. AlphaFactory/tools/sonic_market_regime_profit_atlas.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --cost-per-trade 0.50 `
  --min-combo-n 20
```

Outputs:

- `analysis/market_regime_profit_atlas.json`
- `analysis/market_regime_profit_atlas.md`
- `analysis/market_regime_profit_atlas_by_macro.csv`
- `analysis/market_regime_profit_atlas_combos.csv`
- `analysis/market_regime_trade_labels.csv`

Current evidence from `20260502_232935`: profits after cost are concentrated in
2024-2025. Price-only trend proxies out to 20 days do not recreate the edge
robustly; removing S1 in 20d strong downtrends still leaves cost PF below 1.0
and weak half-year stability. Do not patch EA from this atlas alone.

### Gold Regime Context Telemetry

Use `InpEnableGoldRegimeTelemetry=1` only for XAUUSD M5 research runs. It writes
`<symbol>_GoldRegimeContext_<run_id>.csv` and logs compact closed-bar context
for trade/candidate rows only, not every M5 bar.

Enable in a controlled run:

```powershell
& "02. AlphaFactory/alpha.ps1" backtest "EA_SonicR" `
  -Symbol XAUUSD -Period M5 -From "2019.01.01" -To "2025.12.31" -Model 1 `
  -Overrides "<explicit 008B inputs>;InpEnableGoldRegimeTelemetry=1;InpVariantTag=H_XAU_GOLDCTX_EXAMPLE"
```

Audit after the run:

```powershell
python "02. AlphaFactory/tools/sonic_gold_regime_context_audit.py" `
  "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --cost-per-trade 0.50
```

Outputs:

- `analysis/sonic_gold_regime_context_audit.json`
- `analysis/sonic_gold_regime_context_audit.md`
- `analysis/sonic_gold_regime_context_audit_candidates.csv`
- `analysis/sonic_gold_regime_joined_trades.csv`

Current evidence from `20260503_145322`: telemetry parity passed and the sidecar
joined `492/492` final trades, but every GoldRegime S1 screen failed. S1 against
5d flow is a real loss pocket (`166` trades, cost PF `0.6974`, net `-390.06`),
yet deleting it only lifts the portfolio to roughly breakeven. Do not code an
S1 flow gate from this alone.

### Guarded Research Loop

Use `sonic_research_loop.ps1` to keep future sessions from skipping gates. It
is dry-run by default and creates a lock file while running. It can compile,
backtest, validate-full, cost stress, market-phase attribution, GoldRegime audit
when the sidecar exists, candidate compare, refresh `runs.db`, and optionally
archive Common Files telemetry.

Dry run:

```powershell
& "02. AlphaFactory/tools/sonic_research_loop.ps1" `
  -Symbol XAUUSD -Period M5 -From "2024.01.01" -To "2025.12.31" -Model 1 `
  -VariantTag "H_XAU_EXAMPLE" `
  -Overrides "InpEnableTelemetry=1;InpVariantTag=H_XAU_EXAMPLE"
```

Execute:

```powershell
& "02. AlphaFactory/tools/sonic_research_loop.ps1" `
  -Symbol XAUUSD -Period M5 -From "2019.01.01" -To "2025.12.31" -Model 1 `
  -VariantTag "H_XAU_LONG_EXAMPLE" `
  -Overrides "<explicit semicolon-separated inputs>" `
  -CleanupCommonFiles `
  -Execute
```

Do not wire this into Windows Task Scheduler without an explicit decision. For
now it is a manual guarded loop to avoid runaway MT5 memory and stale cache
mistakes.

### State Telemetry V2

Use `InpEnableStateTelemetry=1` only for research diagnostics. It writes
`<symbol>_StateTelemetry_<run_id>.csv` and does not change trading logic.
V2 fills the existing extension, break, S/R runway, Dragon retest,
sweep/reclaim side, wave smoothness, and Dragon-overlap columns. These fields
are pre-entry diagnostics, not rule authorization.

Smoke template:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/alpha.ps1" backtest "EA_SonicR" `
  -Symbol XAUUSD -Period M5 -From "2025.01.01" -To "2025.02.28" -Model 1 `
  -Overrides "InpEnableTelemetry=1;InpEnableStateTelemetry=1;InpUseOpportunityScoreGate=1;InpVariantTag=XAU_STATE_TEL_ON_SMOKE_20260501"
```

Compare against the same window with `InpEnableStateTelemetry=0`. Trade count,
net, and PF must match. The sidecar is for score-gate diagnostics only.
Reference V2 smoke: `20260501_215613` off versus `20260501_215736` on.

### State Telemetry Audit

Use after any run with `InpEnableStateTelemetry=1` to attribute score-gate
behavior by setup, direction, session bucket, and executed trade variant.

```powershell
python "02. AlphaFactory/tools/sonic_state_telemetry_audit.py" `
  --run-dir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>"
```

Outputs:

- `analysis/sonic_state_telemetry_audit.json`
- `analysis/sonic_state_telemetry_audit.md`

Important limitation: `Trades` currently has no `candidate_id`, so the audit
uses a heuristic exact join on `run_id + entry_server_ts + direction + variant`.
Do not use this report as promotion evidence by itself.

### Trade-State Anatomy

Use when a run needs real win/loss anatomy rather than aggregate PF.

```powershell
python "02. AlphaFactory/tools/sonic_trade_state_anatomy.py" `
  --run-dir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --min-bucket-n 5
```

Outputs:

- `analysis/sonic_trade_state_anatomy.json`
- `analysis/sonic_trade_state_anatomy.md`
- `analysis/sonic_trade_state_joined.csv`

Read this before changing score thresholds. Current evidence says the raw
opportunity score can be higher on losers than winners, so raising the score
threshold is not automatically a quality improvement.

### Deep Forensics And Pair Compare

Use these after `sonic_trade_state_anatomy.py` has created
`analysis/sonic_trade_state_joined.csv`.

For weak buckets, top wins/losses, and candidate rule clusters:

```powershell
python "02. AlphaFactory/tools/sonic_trade_forensics.py" `
  --run-dir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  --control-run-dir "02. AlphaFactory/runs/EA_SonicR/<CONTROL_RUN_ID>" `
  --min-removed 4 `
  --min-kept 40 `
  --top 12
```

For exact trade-by-trade deltas between a challenger and matched control:

```powershell
python "02. AlphaFactory/tools/sonic_trade_pair_compare.py" `
  --current-run-dir "02. AlphaFactory/runs/EA_SonicR/<CANDIDATE_RUN_ID>" `
  --control-run-dir "02. AlphaFactory/runs/EA_SonicR/<CONTROL_RUN_ID>" `
  --top 12
```

Outputs:

- `analysis/sonic_trade_forensics.json/.md`
- `analysis/sonic_trade_forensics_rules.csv`
- `analysis/sonic_trade_pair_compare.json/.md/.csv`

Use pair compare when a management rule changes exits. Aggregate PF can hide
whether the rule saved real stops or merely cut future winners.

### MT5-Native Snapshot Flow

Use sampled snapshots only. Do not screenshot every trade.

Automated 1-case smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1" `
  -RunDir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  -SampleReason "top_loss" `
  -MaxCases 1 `
  -CompileTimeoutSec 45 `
  -RunMt5Startup `
  -Mt5TimeoutSec 180 `
  -CleanupStaging
```

Manual fallback:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1" `
  -RunDir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  -SampleReason "top_loss,top_win" `
  -MaxCases 6
```

Then run `SonicR_CaseSnapshot` inside MT5 and collect:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1" `
  -RunDir "02. AlphaFactory/runs/EA_SonicR/<RUN_ID>" `
  -SkipPrepare -SkipCompile -CleanupStaging
```

Known limitation: as of `20260501_151422`, 1-case automated capture works, but
larger historical batches can fail partially when MT5 does not load/navigate the
event bar reliably.

### Runs Database

Rebuild after meaningful batches or cleanup:

```powershell
python "02. AlphaFactory/tools/runs_db.py" build
```

Useful queries:

```powershell
python "02. AlphaFactory/tools/runs_db.py" summary
python "02. AlphaFactory/tools/runs_db.py" info <RUN_ID>
python "02. AlphaFactory/tools/runs_db.py" compare <BASELINE_RUN_ID> <CANDIDATE_RUN_ID>
```

The database is an index, not evidence. For decisions, trace back to per-run
artifacts.

### Offline Sonic State Probes

Use these before coding a new XAU lane. They read run-local sidecars/reports and
write analysis artifacts under the same run folder.

Compression-to-impulse / breakout screens:

```powershell
python "02. AlphaFactory/tools/sonic_compression_impulse_probe.py" `
  <RUN_ID> `
  --profile strict `
  --cost-r 0.05 `
  --min-count 240

python "02. AlphaFactory/tools/sonic_compression_impulse_probe.py" `
  <RUN_ID> `
  --profile exploratory `
  --cost-r 0.05 `
  --min-count 240

python "02. AlphaFactory/tools/sonic_compression_impulse_probe.py" `
  <RUN_ID> `
  --profile micro `
  --cost-r 0.05 `
  --min-count 240
```

Post-breakout retest screen:

```powershell
python "02. AlphaFactory/tools/sonic_impulse_retest_probe.py" `
  <RUN_ID> `
  --cost-r 0.05 `
  --min-count 240
```

Profit-period anatomy:

```powershell
python "02. AlphaFactory/tools/sonic_profit_period_anatomy.py" `
  <RUN_ID> `
  --cost-per-trade 0.50 `
  --min-bucket-trades 20
```

Guardrail from `20260503_145322`: compression strict/exploratory/micro and
post-impulse retest all failed long-window cost screens. Do not code a
compression/retest lane unless a new pre-registered thesis beats those failures
on count, PF after cost, half-year stability, and year diversity.

### Cleanup

Create the fast, non-destructive storage inventory first:

```powershell
python "02. AlphaFactory/tools/backtest_storage_inventory.py" --top 50
```

The compact inventory is written to
`02. AlphaFactory/runtime/storage/backtest_inventory.json`. Potential mirror
bytes are size-only estimates; exact SHA256 validation happens in the dedupe
tool.

Inspect a very large log without loading it into the agent context:

```powershell
python "02. AlphaFactory/tools/large_log_reader.py" inspect `
  "02. AlphaFactory/runs/<EA>/<RUN_ID>/logs/<FILE>.csv" `
  --head 20 --tail 20 `
  --pattern "ledger_fatal=M2_LEDGER_FATAL|fatal" `
  --pattern "execution_error=reject|timeout|invalid"

python "02. AlphaFactory/tools/large_log_reader.py" search `
  "02. AlphaFactory/runs/<EA>/<RUN_ID>/logs/<FILE>.csv" `
  "M2_LEDGER_FATAL|reject|timeout" --context 3 --max-matches 50

python "02. AlphaFactory/tools/large_log_reader.py" window `
  "02. AlphaFactory/runs/<EA>/<RUN_ID>/logs/<FILE>.csv" `
  --start 250000 --count 100
```

The commands write compact JSON under `02. AlphaFactory/runtime/log_indexes/`
and print only a one-line receipt. `search` is capped at 200 matches; `window`
is capped at 500 lines.

Dry-run duplicate physical log cleanup for one run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/dedupe_backtest_log_mirrors.ps1" `
  -EaName "EA_SonicR" -RunId "<RUN_ID>"
```

Review the JSON plan and reclaimable bytes. `-Execute` converts only exact
size/SHA256 matches to NTFS hardlinks; it does not remove either compatibility
path.

Workspace hygiene:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/workspace_hygiene.ps1" `
  -BuildRunsDb
```

Archive-first backtest cleanup, dry run first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/archive_backtest_artifacts.ps1" `
  -ArchiveRoot "X:\MT5_Archive" `
  -EaName "EA_SonicR" `
  -MinAgeDays 14 `
  -IncludeCommonFiles `
  -IncludeRuns
```

Dry-run writes a plan under `02. AlphaFactory/runtime/cleanup_plans/`. Use
`-Execute` only after confirming the plan SHA, protected/reference keep list,
age gate and off-volume destination. Execute performs copy -> full per-file
SHA256 verification -> source removal. `-EaName '*'` is inventory-only and is
rejected for execution.

## Current Baselines

- Frozen research baseline: `20260501_000718`.
- Attribution dataset: `20260501_151422`.
- S1 short-time telemetry seed: `20260502_214514`.
- Current XAU M5 economics research seed: `20260502_220922`.
- Telemetry/risk smoke: `20260501_012639`.

None is deploy/demo/prop-ready. `validate-full REVIEW 0/5` remains the blocker.

## Sonic R Research Guardrails

- Keep new strategy behavior default-off.
- Do not change `Signals` or `Trades` headers without migration plan.
- PVSRA/SR is context, not standalone trigger.
- Do not tune hour/session filters after seeing a lucky run.
- Use entry-as-of visuals for setup labels; outcome charts are anatomy only.
- Use population evaluation before coding any feature.
- One change, one run, one interpretation.
