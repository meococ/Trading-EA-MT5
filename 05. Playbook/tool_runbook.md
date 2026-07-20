# AlphaFactory Tool Runbook

Updated: 2026-07-19

Scope: AlphaFactory command and evidence operations for every EA lane. Active
EA scope and open lanes come from `04. Memory/hot.md`; this runbook does not
enumerate them. Nothing here authorizes compiling or backtesting from
`00. Old File/`.

## Purpose

Use this file when a session needs to compile, backtest, analyze, compare,
snapshot, or clean AlphaFactory evidence. AlphaFactory and MT5 tester artifacts
remain the execution truth. These tools speed up research; they do not promote
an EA by themselves. A command path marked unavailable in
`04. Memory/source_of_truth.json` is historical only and must not be invoked.

## Standard Run Closure

After any meaningful backtest, use this order:

1. Confirm `hypothesis_id`, registry row, frozen prereg/plan, task packet,
   active source contract, and cost-source boundary.
2. Compile/backtest through `alpha.ps1` or the guarded research loop.
3. Run `validate-full` against the exact report.
4. Compare to the matched control on the same model/window when applicable.
5. Run cost stress and the relevant regime/phase analysis.
6. Run standard log triage, reconcile report/lifecycle/RunMeta, then explain
   the funnel, execution anomalies, winning causes, losing causes and logic
   conflicts.
7. Render the mandatory multi-timeframe anatomy casebook: at least two winners
   plus two losers when available, or representative rejections for zero-trade.
8. Build the hash-bound EA delivery packet and require `alpha.ps1 delivery` PASS.
9. Archive/clean stale telemetry only after preserving cited evidence and
   reviewing the cleanup plan SHA.

### Outcome-blind collection closure

A Strategy Tester invocation is a data-acquisition run, not a performance
backtest, only when a frozen `DATA_ACQUISITION_ONLY` contract binds the
collection id, source/input/schema identity, exact window and D-side storage;
all mutation switches are false; label/outcome fields are blank; and both the
report and summary prove zero trades with
`performance_metrics_authorized=false`. Reject the collection if any trade or
outcome-like field appears. Do not cite PF, win rate or cadence from it.

Preserve the immutable source corpus and write any derived annotations as
separate overlays by `event_id`. Snapshot protected C roots before/after;
`FILE_COMMON` remains forbidden for portable collectors. A schema missing a
required source hash is diagnostic-only and must not be silently upgraded in
place.

## Core Commands

### AlphaFactory CLI

Status:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/alpha.ps1" status
```

Compile:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/alpha.ps1" compile "<EA_NAME>"
```

Validate a run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/alpha.ps1" validate-full `
  -Report "02. AlphaFactory/runs/<EA_NAME>/<RUN_ID>/report.html"
```

Validate an EA development closeout after the analysis and casebook exist:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/alpha.ps1" delivery `
  -Packet "03. EA Developer/<EA_NAME>/research/<EA_DELIVERY_PACKET.json>"
```

Start from `EA_DELIVERY_PACKET.template.json` and
`LOGIC_TO_CODE_MATRIX.template.md`. The completion validator rehashes every
binding, checks source→binary→run/log identity, verifies the full analysis
surface and inspects the casebook manifest plus each PNG hash. It is not a
profit or promotion gate; it makes incomplete EA diagnosis fail closed.

`alpha.ps1 backtest` requires the frozen hypothesis/task/receipt contract; use
the guarded research-loop section below rather than inventing an ad-hoc
command. Command completion is not strategy readiness; read the validation
verdict and full gate stack.

`TesterInputs` serialization is type-aware: numeric and boolean overrides use
the MT5 optimization tuple, while declared MQL5 `input string` overrides must
be written as plain `key=value`. If a new string input appears literally as
`value||value||0||value||N` in the tester log, reject the run as a harness
failure; do not weaken EA input validation.

For zero-trade data acquisition, `report ready` is not completion. Require the
exact receipt-bound sidecars, validate source hash and contract id across
manifest/meta/rows, prove every label/outcome column blank, and confirm the
zero-trade summary forbids performance metrics. A missing sidecar means the run
is invalid even when HTML exists; inspect config + Tester `OnInit` first. When
schema changes, version and preflight the extractor/rubric before labeling.

Validate the canonical hypothesis ledger before any ceremony:

```powershell
python "04. Memory/research/validate_candidate_registry.py"
```

Package capability template, prereg/probe-plan/readout templates and
task-packet checklists live at `02. AlphaFactory/templates/research/`.
`telemetry_profile=none` is compile/dry-run only; meaningful Model 0 requires
implemented `lifecycle-v3` evidence.

### Guarded Research Loop

Entry point for every EA is `ea_research_loop.ps1`
(`research_loop_engine.ps1` is its internal engine; do not call the engine
directly). The loop is dry-run by default, validates the registry first, binds
source/prereg/capability/include/Git/cost/control hashes, and holds the global
MT5 lock. Full design-to-decision order: `ea_golden_path.md`.

A valid dry run that reports BLOCKED is a preflight result, not an error:

```powershell
& "02. AlphaFactory/tools/ea_research_loop.ps1" `
  -EaName "<EA_NAME>" -HypothesisId "<HYP_ID>" -RunRole control `
  -Symbol EURUSD -Period M15 -From "2020.01.01" -To "2025.12.31" `
  -Model 0 -TelemetryTier trade-only -TaskPacket "<TASK_PACKET.json>" `
  -CostSourceManifest "<same path as task packet cost_source_manifest_path>"
```

Execute only after the JSON plan returns `execution_allowed=true`:

```powershell
& "02. AlphaFactory/tools/ea_research_loop.ps1" `
  -EaName "<EA_NAME>" -HypothesisId "<HYP_ID>" -RunRole control `
  -Symbol EURUSD -Period M15 -From "2020.01.01" -To "2025.12.31" `
  -Model 0 -TelemetryTier trade-only -TaskPacket "<TASK_PACKET.json>" `
  -CostSourceManifest "<same path as task packet cost_source_manifest_path>" `
  -Execute
```

`acceptance_contract` in the packet must match the frozen registry row exactly
and is passed through as unified-validation thresholds. `VariantTag` is valid
only when the package capability contract declares the input. An EA without
includes is valid. Scheduling/cron needs explicit approval (AGENTS §3).

### Candidate Compare

Generic challenger comparison is selected by the EA capability contract and is
normally invoked by `ea_research_loop.ps1`. Manual diagnostic form:

```powershell
python "02. AlphaFactory/tools/alpha_candidate_compare.py" `
  "02. AlphaFactory/runs/<EA_NAME>/<CHALLENGER_RUN_ID>" `
  --baseline "02. AlphaFactory/runs/<EA_NAME>/<CONTROL_RUN_ID>" `
  --ea "<EA_NAME>" `
  --out "02. AlphaFactory/runs/<EA_NAME>/<CHALLENGER_RUN_ID>/analysis/candidate_compare.json"
```

`candidate_compare_engine.py` exists only to re-read archived strict-format
evidence; new lanes use `alpha_candidate_compare.py`. Do not accept a candidate
on PF alone; weigh net and monthly economics, validation and execution realism
together, and declare the acceptance metric in the frozen plan before comparing.

### Cost Stress

First-pass falsification; report-only unless broker-informed cost conversion
is bound:

```powershell
python "02. AlphaFactory/tools/research_cost_stress.py" `
  "02. AlphaFactory/runs/<EA_NAME>/<RUN_ID>" `
  --base-cost-per-trade <COST> `
  --out "02. AlphaFactory/runs/<EA_NAME>/<RUN_ID>/analysis/cost_stress_report_only.json"
```

Do not call a run robust if PF collapses under small per-trade costs.

### Repro Drift Map

Use before any cadence/gate/default patch when run counts drift across
otherwise similar configs:

```powershell
python "02. AlphaFactory/tools/repro_drift_map.py" `
  <RUN_ID_1> <RUN_ID_2> <RUN_ID_3> `
  --out-json "02. AlphaFactory/runs/<EA_NAME>/<RUN_ID>/analysis/repro_drift_map.json" `
  --out-md "02. AlphaFactory/runs/<EA_NAME>/<RUN_ID>/analysis/repro_drift_map.md"
```

### Research Utilities (offline probes)

- `02. AlphaFactory/tools/research/dsr.py` — Deflated Sharpe Ratio with the
  workspace trial-accounting conventions; self-test via `python dsr.py`.
- `02. AlphaFactory/tools/research/fivepercent_server_clock.py` — canonical
  FivePercent server-time→UTC model (era-hybrid DST); self-test included.
- `02. AlphaFactory/tools/research/snapshot_c_roots.ps1 -OutputPath <json>` —
  before/after receipts of the 4 protected C roots (single digest
  implementation; never reimplement the hash).
- `02. AlphaFactory/tools/research/chart_case_render.py` — per-case candlestick
  PNGs from hash-bound bars + a cases CSV (`case_id, entry_time_utc, direction,
  entry[, sl, tp, exit_time_utc, exit, reason, label]`). Default `--mode asof`
  draws only bars closed before entry (decision-time information set);
  `--mode anatomy` is outcome view only. Emits `cases_manifest.json` with
  per-image SHA256 and the enforced cutoff.
- Future delivery casebooks must use anatomy mode with `label`, `direction`,
  `entry_marker_rendered`, `sl_line_rendered`, `tp_line_rendered`,
  `exit_marker_rendered`, centered HTF context and visible/labeled post-entry
  bars. As-of charts may accompany them but cannot replace outcome anatomy.
- `02. AlphaFactory/tools/research/log_triage.py <log>` — streaming standard
  error-pattern battery over heavy tester/EA logs; one compact JSON summary.
  Run this FIRST; open raw windows only where triage points
  (`large_log_reader.py window`).
- Probe SDK modules (`indicators.py`, `sealed_loader.py`, `trial_log.py`,
  `metrics.py`, `controls.py`) — mechanism-neutral primitives; charter and
  usage in `tools/research/README.md`. Indicator variants: `*_mt5` for
  Model-0-bound lanes, `*_wilder` for literature replication.
- `02. AlphaFactory/tools/research/parity_harness.py run --bars <parquet>` —
  captures iATR/iADX/iRSI in the portable FivePercent terminal via a
  [StartUp] script (`mql5/ParityDump.mq5`) and diffs against the python
  variants on identity-proven bars; emits a PASS/FAIL parity artifact.
- Probe plans start from
  `02. AlphaFactory/templates/research/PROBE_PLAN.template.md`.

### Market Data Acquisition (python bridge)

Pull closed bars read-only through the MetaTrader5 python package; persist
working datasets as Parquet under `02. AlphaFactory/data/` (never on `C:`
alongside the MT5 installation; never in `FILE_COMMON`). Requirements:

- Fail-closed identity checks before any pull (server/company/demo/trading
  disabled; symbol geometry).
- Snapshot protected C roots before/after the terminal session
  (`snapshot_c_roots.ps1`).
- `mt5.shutdown()` does not terminate the `terminal64.exe` it launched:
  verify no orphan process remains and record process count in the receipt.
- Convert server time with `fivepercent_server_clock.py`; store both
  `time_server` and `time_utc`. The broker's historical spread column is not
  cost evidence.

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
  -EaName "<EA_NAME>" -RunId "<RUN_ID>"
```

Review the JSON plan and reclaimable bytes. `-Execute` converts only exact
size/SHA256 matches to NTFS hardlinks; it does not remove either compatibility
path.

Workspace hygiene:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/workspace_hygiene.ps1"
```

The default is dry-run. Add `-Execute` only after reviewing the exact sample
and stale-worktree candidates. Rebuilding `runs.db` is also mutating and uses
`-BuildRunsDb -Execute`.

Archive-first backtest cleanup, dry run first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/tools/archive_backtest_artifacts.ps1" `
  -ArchiveRoot "X:\MT5_Archive" `
  -EaName "<EA_NAME>" `
  -MinAgeDays 14 `
  -IncludeCommonFiles `
  -IncludeRuns
```

Dry-run writes a plan under `02. AlphaFactory/runtime/cleanup_plans/`. Use
`-Execute` only after confirming the plan SHA, protected/reference keep list,
age gate and off-volume destination. Execute performs copy -> full per-file
SHA256 verification -> source removal. `-EaName '*'` is inventory-only and is
rejected for execution.

## Archived Analysis Tooling

Lane-specific analysis tools for the archived SonicR ledger (casebook,
anatomy, phase attribution, snapshot flow, state probes) live under
`00. Old File/EA_Archive/EA_SonicR/tools_analysis_archive_20260718/` with a
manifest. Archive-only: not valid execution surface; restoring one is an
Owner-scoped change.

## Guardrails

- Keep new strategy behavior default-off.
- Do not change telemetry/sidecar headers without a migration plan and updated
  analyzers.
- Do not tune hour/session filters after seeing a favorable run.
- Use entry-as-of visuals for setup labels; outcome charts are anatomy only.
- One change, one run, one interpretation.
- No EA closeout after a meaningful backtest without
  `EA_DELIVERY_PACKET_OK`; report/analyze/validate-full completion alone is
  insufficient.
