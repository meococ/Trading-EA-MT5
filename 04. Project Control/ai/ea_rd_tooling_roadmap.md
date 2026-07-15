# EA R&D Tooling Roadmap

Updated: 2026-05-01
Scope: `EA_SonicR`, AlphaFactory, MetaQuotes-Demo symbols (`XAUUSD`, `EURUSD`, `GBPUSD`)

## Why This Exists

Progress has been too slow because too much of the EA loop still depends on manual log reading, scattered run folders, and human memory. The current bottleneck is not a missing indicator. The bottleneck is missing evidence automation:

- no one-command Sonic attribution pipeline,
- no mandatory candidate-vs-baseline comparator,
- no cost-stress matrix bound to each candidate,
- no experiment registry that records failed trials as first-class data,
- no compact casebook/label loop before adding new rules,
- no MCP layer that exposes AlphaFactory results as structured JSON.

The correct target is not to replace AlphaFactory or MT5 Strategy Tester. The correct target is to make AlphaFactory the execution kernel and wrap it with structured scripts, run indexing, validation reports, and a small custom MCP surface.

## Current Ground Truth

- `EA_SonicR` is research-only.
- MT5 tester remains the final execution-fidelity source.
- `Model=1` can screen fast; `Model=0` remains the confirmation lane.
- Profit factor alone cannot promote a candidate.
- The active XAUUSD M5 research candidate reached cadence/PF that is worth studying, but `validate-full` is still `REVIEW 0/5`.
- Sonic R implementation is reconstructed parity research, not confirmed original-source parity.

## Team Verdict

All three research agents converged on the same operating conclusion:

1. Do not adopt a separate backtesting engine as the product source of truth.
2. Keep `02. AlphaFactory/alpha.ps1` as the canonical compile/backtest/analyze lane.
3. Add an AlphaFactory JSON wrapper before adding more strategy logic.
4. Add a runs database and query layer so agents stop re-reading huge folders.
5. Build Sonic-specific attribution, casebook, label, and cost-stress tools.
6. Add MCP only where it exposes stable, bounded tools. MCP must not become an unguarded shell.

## Recommended Architecture

```text
Agent session
  -> Project control docs
  -> AlphaFactory JSON wrapper
  -> MT5 compile/backtest/analyze/validate-full
  -> Runs SQLite/DuckDB index
  -> Sonic attribution and casebook tools
  -> Robustness lab: WFA, MC, PBO/CSCV, WRC/SPA, cost stress
  -> Compact report + cleanup/archive-first
```

The EA stays in MQL5. Python is used for research, analysis, labeling, reporting, and orchestration.

## Build Workflow

Every meaningful experiment should follow this sequence:

1. Pre-register hypothesis
   - Symbol, timeframe, model, date window, inputs, variant tag.
   - One strategy change only.
   - Pass/fail gates written before seeing the result.

2. Run controlled backtest
   - Compile first.
   - Use explicit `InpVariantTag` for telemetry-on Sonic R runs.
   - Store `run_id`, config, report, and run manifest.

3. Analyze as data, not as a story
   - Join Signals, Trades, Opportunities, Regime, PVSRA/SR sidecars.
   - Report trades, net, PF, DD, monthly mean, active months, session/hour concentration, overnight/weekend exposure.

4. Compare to frozen baseline
   - Same symbol/timeframe/model/window/cost assumptions.
   - Reject if improvement is PF-only or caused by mined hours.

5. Stress and falsify
   - Cost stress, slippage/spread sensitivity, WFA, Monte Carlo/bootstrap, PBO/CSCV, WRC/SPA where applicable.

6. Produce evidence casebook
   - Sample only useful cases: top wins, top losses, high-MFE misses, high-MAE false positives, weak months, blocked near-pass candidates.
   - Do not screenshot every trade.
   - Run MT5-native sampled snapshots only after numeric artifacts and casebook index exist.

7. Cleanup
   - Preserve cited artifacts.
   - Archive stale Common Files telemetry and old run folders with manifest.
   - Rebuild the run index.

## Script Backlog

### Existing P0 Tools

| Tool | Path | Purpose |
| --- | --- | --- |
| AlphaFactory JSON wrapper | `02. AlphaFactory/tools/alpha_json.ps1` | Stable JSON output for compile/backtest/analyze/validate-full. |
| Candidate comparator | `02. AlphaFactory/tools/sonic_candidate_compare.py` | Compare one candidate to frozen baseline across economics, safety, robustness artifacts. |
| Cost stress | `02. AlphaFactory/tools/sonic_cost_stress.py` | Reprice trades under spread/slippage/commission tiers and report PF/net/DD/month impact. |
| MT5 snapshot flow | `02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1` | Post-casebook wrapper for bounded MT5-native screenshots, stale-stage cleanup, SHA256 collection, and casebook index refresh. |
| Evidence audit | `02. AlphaFactory/tools/evidence_audit.py` | Verify required run artifacts exist before a run can be cited. |
| Casebook index | `02. AlphaFactory/tools/sonic_casebook_index.py` | Connect visual evidence, labels, validation, compare, cost stress, and snapshots into one readout. |
| Population eval | `02. AlphaFactory/tools/sonic_population_eval.py` | Test feature lift across the full opportunity population and time splits. |
| Runs DB | `02. AlphaFactory/tools/runs_db.py` | Rebuild/query local run catalog after backtests and cleanup. |
| Archive cleanup | `02. AlphaFactory/tools/archive_backtest_artifacts.ps1` | Archive-first cleanup for stale AlphaFactory runs and `Terminal/Common/Files`; pair with `runs_db.py build`. |

### Planned P0/P1 Tools

| Tool | Path | Purpose |
| --- | --- | --- |
| Sonic attribution batch | `02. AlphaFactory/tools/sonic_full_attribution.ps1` | Planned wrapper for compile, telemetry-on backtest, sidecar hygiene, datalog attribution, compare, cost, and evidence audit. |
| Broker-informed cost conversion | `02. AlphaFactory/tools/sonic_broker_cost_model.py` | Planned conversion from spread/slippage/tick metadata to realistic per-trade cost tiers. |
| Snapshot batch stabilizer | extend `02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1` | Preload/navigate historical bars reliably so multi-case native snapshot batches stop failing partially. |

### P1: Needed For Sonic R Edge Discovery

| Tool | Path | Purpose |
| --- | --- | --- |
| Casebook pipeline | `03. EA Developer/EA_SonicR/research/sonic_casebook_pipeline.ps1` | Sidecars -> sampled cases -> charts -> labels -> optional MT5-native snapshot flow. |
| MFE/MAE labeler | `03. EA Developer/EA_SonicR/research/sonic_label_mfe_mae.py` | Label candidates without logging every bar in MT5. |
| Filter provenance audit | `02. AlphaFactory/tools/sonic_filter_pbo.py` | Track where hour/session/filter rules came from and test split stability. |
| Regime report | `02. AlphaFactory/tools/sonic_regime_report.py` | TREND/RANGE/TRANSITION attribution by symbol/session/month. |

### P2: Useful After The Pipeline Is Stable

| Tool | Path | Purpose |
| --- | --- | --- |
| Plotly report pack | `02. AlphaFactory/analysis/report_pack.py` | Static PNG/PDF/HTML plots for run summaries. |
| Portfolio exposure lab | extend `02. AlphaFactory/analysis/portfolio_optimizer.py` | Correlation, overlap, and portfolio-level cadence. |
| Experiment registry | `02. AlphaFactory/tools/experiment_registry.py` | Hypothesis -> run_id -> result -> decision -> next action. |

## MCP Backlog

### P0: Custom AlphaFactory MCP

This is the highest-leverage MCP. It should expose bounded tools, not a generic terminal:

- `frontier_state`
- `compile_ea`
- `run_backtest`
- `analyze_run`
- `validate_full`
- `compare_baseline`
- `telemetry_summary`
- `archive_cleanup`
- `evidence_audit`

Required behavior:

- Inputs are schema-bound: EA, symbol, timeframe, model, date range, preset/setfile, variant tag.
- Output is compact JSON: status, run_id, artifact paths, PF, trades, DD, validation blockers.
- Refuse promotion language when `validate-full` or required artifacts are missing.
- Dry-run cleanup by default.

### P1: Runs Database MCP

Use SQLite first; DuckDB can be added later for larger Parquet/event datasets.

Minimum query surface:

- latest runs by EA/symbol/timeframe,
- candidate vs baseline,
- validation blocker frequency,
- sidecar hygiene failures,
- session/hour/month attribution,
- strategy lineage by `InpVariantTag`.

### P1: Playwright MCP

Use only for generated HTML reports, dashboards, and visual inspection. Do not use browser clicks as the backtest runner. MT5 execution should remain script/CLI-driven.

### P2: GitHub MCP

Add after the repo has a real PR/CI workflow. Useful for issues, PR review, and Actions status. Not required for local AlphaFactory speed.

### P2: Memory MCP

Useful after the experiment registry exists. Memory should retrieve decisions and failed hypotheses; it must not replace source-of-truth docs or run artifacts.

## External Tools To Adopt Or Cherry-Pick

| Tool | Use | Decision |
| --- | --- | --- |
| MetaTrader5 Python API | Pull rates/ticks/deals/account/symbol metadata from terminal. | Adopt for runtime/data audits, not as final backtester. |
| DuckDB | Local analytics over CSV/Parquet and large run artifacts. | Adopt after SQLite runs DB is stable. |
| Polars | Fast dataframe transforms and out-of-core style processing. | Adopt for heavy sidecar/candidate joins if pandas is too slow. |
| QuantStats | Tear sheets, drawdown, monthly stats, Monte Carlo-style summaries. | Adopt for report pack. |
| Plotly + Kaleido | Static charts for evidence packs. | Adopt after Chrome/Chromium availability is verified. |
| Optuna | Parameter search with explicit trial registry. | Use only inside pre-registered search spaces; never blind tune. |
| skfolio | Portfolio/risk model selection, WalkForward, CPCV concepts. | Cherry-pick validation ideas for portfolio-level routing. |
| vectorbt | Fast signal research and splitters. | Optional sandbox only; do not replace MT5. |
| backtesting.py | Lightweight OHLC prototype sandbox. | Optional for hypothesis sketching only. |
| QuantConnect LEAN | Production architecture reference. | Study architecture; do not migrate Sonic R. |
| NautilusTrader | Event-driven/tick architecture reference. | Study architecture; too heavy to adopt now. |
| mlfinlab/finmlkit concepts | Triple-barrier labels, meta-labeling, purged CV. | Use concepts/lightweight implementation; avoid premium lock-in. |

## What Not To Do

- Do not add another full backtesting engine as the official result engine.
- Do not tune hour/session filters after seeing one lucky run.
- Do not promote any run from PF alone.
- Do not log every bar or screenshot every trade.
- Do not let MCP servers run with unrestricted filesystem access or secrets.
- Do not reopen archived EAs unless explicitly requested.

## Source References

- MetaTrader5 Python Integration: https://www.mql5.com/en/docs/integration/python_metatrader5
- MT5 Strategy Tester tick modes: https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
- MT5 Strategy Testing: https://www.metatrader5.com/en/terminal/help/algotrading/testing
- MQL5 Economic Calendar: https://www.mql5.com/en/docs/calendar
- Model Context Protocol architecture: https://modelcontextprotocol.io/docs/learn/architecture
- MCP reference servers: https://github.com/modelcontextprotocol/servers
- GitHub MCP server: https://github.com/github/github-mcp-server
- Microsoft Playwright MCP: https://github.com/microsoft/playwright-mcp
- DuckDB docs: https://duckdb.org/docs/current/
- Polars docs: https://docs.pola.rs/
- QuantStats: https://github.com/ranaroussi/quantstats
- Plotly static image export: https://plotly.com/python/static-image-export/
- Optuna docs: https://optuna.readthedocs.io/
- skfolio: https://github.com/skfolio/skfolio
- vectorbt: https://github.com/polakowo/vectorbt
- backtesting.py: https://kernc.github.io/backtesting.py/
- QuantConnect LEAN: https://github.com/QuantConnect/Lean
- Deflated Sharpe Ratio: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2460551_code87814.pdf?abstractid=2460551&mirid=1
- Probability of Backtest Overfitting: https://www.semanticscholar.org/paper/The-Probability-of-Backtest-Overfitting-Bailey-Borwein/b1233b4f5384f003e85c2e0eec1a2dfc08f624c5
- Hansen SPA test: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=264569

## Next Implementation Slice

The next practical coding step is not a new Sonic R entry rule. It is:

1. Improve MT5-native snapshot batch reliability beyond the current 1-case smoke.
2. Add broker-informed cost conversion using slippage/spread telemetry.
3. Add missing pre-entry telemetry fields: extension from Dragon/break, true S/R runway, retest quality, sweep/reclaim side, wave smoothness.
4. Re-run population evaluation and only then pre-register one default-off state feature.
5. Wire a small AlphaFactory MCP only after wrappers and evidence audit remain stable across several runs.

This makes every future strategy experiment faster, easier to review, and harder to overfit silently.
