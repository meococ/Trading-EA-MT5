# Source of Truth Registry

Updated: 2026-07-15

> **Path relocation (Owner 2026-07-15):** Active EA Developer shelf is empty.
> Former `03. EA Developer/EA_SonicR/` (incl. research ledger) and
> `EA_SilverBullet/` live under `00. Old File/EA_Archive/`. Root
> `README-SONIC-R.md`, `SYNC_REPORT.md`, and `tests/` are archived under
> `00. Old File/docs_archive/` and `tests_archive/`. Rows below that still
> cite `03. EA Developer/EA_SonicR/...` refer to the **archived** copies at
> `00. Old File/EA_Archive/EA_SonicR/...` — not active surface. Defer to
> `hot.md` / `INDEX.md` for live paths.

## Priority order
1. Fresh code and generated run artifacts
2. `04. Memory/hot.md` (fast-path session cache)
3. This registry (`04. Memory/source_of_truth.md`/`.json`)
4. `04. Memory/do_not_repeat_failures.md`
5. `05. Guidance/` (gates, runbook, ea_engineering_standard, research_doctrine)
6. `AGENTS.md`
7. `INDEX.md` (workspace map)
8. `02. AlphaFactory/STRATEGY_LOG.md`
9. Archived documents (`00. Old File/`)

## Root hygiene rule
- Keep the project root lean.
- Root should contain only: `AGENTS.md` (cross-agent launcher), `CLAUDE.md`
  (pointer-only Claude entry), `INDEX.md` (workspace map), and the
  `01. GOAL/` folder holding the Owner-frozen `GOAL.md`. The hidden
  `.codex/operator/` recovery ledger is also allowed for long-running
  operator-loop tasks, but it is operational only and always defers to
  `hot.md`.
- Do **not** keep root stubs for `README-SONIC-R.md` or `SYNC_REPORT.md`
  (archived under `00. Old File/docs_archive/`).
- Root must not keep MT5 sample experts such as `ExpertMACD.mq5` or their compiled `.ex5` outputs.
- Move retired markdown to `00. Old File/docs_archive/` (preferred) or
  `00. Old File/markdown_graveyard/`.
- Keep control docs split: state in `04. Memory/` (hot.md, do_not_repeat,
  registry), rules in `05. Guidance/` (4 core docs). Archived doctrine + AI/session
  archive under `00. Old File/project_control_archive_20260716/`.
- Keep raw AlphaFactory runs and local SQLite catalogs out of git; they are operational storage, not source-of-truth documents.
- `EA_SonicR` (research ledger) and `EA_SilverBullet` (binary-only) are archived
  under `00. Old File/EA_Archive/` — not active surface. Active lanes:
  `EA_FVGConfluence`, `EA_HybridICT_Sonic`.
- Retired or cached EA source outside an explicitly opened lane belongs under
  `00. Old File/EA_Archive/` and is archive-only.

## Availability contract

- A status of `authoritative`, `evidence`, `archive`, or `invalidated` means the path exists in this checkout.
- `backup-only` means the local path is absent but the same relative path exists under `G:\Drive của tôi\META TRADING\Advisors` and its SHA256 is pinned in the JSON registry.
- `unavailable-unresolved` means the path is absent both locally and at that declared backup root. It is a historical index record only, not usable evidence.
- Run `python "04. Memory/validate_source_of_truth.py"` before relying on this registry.

## Registry
| Path | Status | Why it matters |
| --- | --- | --- |
| `AGENTS.md` | authoritative | Single cross-agent operating doctrine. Slimmed 2026-07-11 to lean hard rules plus pointers; detailed doctrine moved to 05. Guidance/research_doctrine.md; active scope is owned by hot.md. |
| `CLAUDE.md` | authoritative | Pointer-only session entry file for Claude agents; defers to hot.md, 01. GOAL/GOAL.md, root INDEX.md, and AGENTS.md. Added 2026-07-11. |
| `INDEX.md` | authoritative | Root workspace map: one-line what/when pointers to control docs, research, EA source, AlphaFactory, and tests. Pointer-only; content lives at the destinations. Added 2026-07-11. |
| `.codex/operator/STATUS.md` | evidence | Operational recovery ledger for the active long-running V2 hardening task. It is subordinate to hot.md and is not research or execution authority. |
| `.codex/operator/EXPERIMENTS.jsonl` | evidence | Append-only bounded-experiment ledger for the active V2 hardening task, including red-first checks, diagnoses, and stop states. |
| `01. GOAL/GOAL.md` | authoritative | Owner-frozen north-star target: joint PF/cadence/cost-stress/exposure/evidence-window table, DONE ladder, non-goals, and probe-first operating principle. Changes only on explicit Owner decision; numeric authority remains sonic_validation_gates.md. |
| `05. Guidance/research_doctrine.md` | authoritative | Full research/validation doctrine moved out of AGENTS.md on 2026-07-11: Sonic doctrine, research workflow, registry contract, chart-state label contract, overfit budget, team review roles, MT5 non-repaint rules, and backtest hygiene. |
| `04. Memory/validate_source_of_truth.py` | authoritative | Fail-closed local/backup availability, SHA256, duplicate-path, and JSON-to-Markdown registry consistency validator. |
| `05. Guidance/sonic_validation_gates.md` | authoritative | Stage-gate matrix for Sonic R research: probe, screen, challenger, confirmed, portfolio-sleeve, required artifacts, thresholds, and invalidations. |
| `00. Old File/agent_guidance_archive/20260503_1916_sonic_readme_cleanup/manifest.json` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: archive. Manifest for retired Claude/doc/root guidance layers archived during the Sonic R knowledge-map cleanup. |
| `04. Memory/hot.md` | authoritative | Fast-path session cache (<500 words). Replaces current_state header at session start. |
| `04. Memory/source_of_truth.md` | authoritative | Human-readable registry |
| `04. Memory/source_of_truth.json` | authoritative | Machine-readable registry |
| `05. Guidance/ea_engineering_standard.md` | authoritative | EA engineering standard |
| `05. Guidance/sonic_tool_runbook.md` | authoritative | Practical Sonic R command runbook for AlphaFactory JSON, compare, cost stress, evidence audit, casebook, population eval, MT5 snapshots, runs DB, and cleanup. |
| `00. Old File/EA_Archive/README.md` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Archive-only rule for retired/non-current EA source; confirms EA_SonicR remains the only active EA source. |
| `02. AlphaFactory/STRATEGY_LOG.md` | authoritative | Experiment memory |
| `02. AlphaFactory/tools/alpha_json.ps1` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. JSON wrapper around selected alpha.ps1 actions; separates command completion from strategy validation verdict for agent/MCP workflows. |
| `02. AlphaFactory/tools/sonic_candidate_compare.py` | authoritative | Sonic R per-run artifact comparator against frozen baseline 20260501_000718; rejects identity mismatches and PF-only conclusions. |
| `02. AlphaFactory/tools/sonic_cost_stress.py` | authoritative | Sonic R report-only cost-stress matrix; flags missing slippage telemetry and must not be treated as broker execution proof. |
| `02. AlphaFactory/tools/sonic_repro_drift_map.py` | authoritative | Sonic R reproducibility drift mapper for comparing run identity, input hashes, metric deltas, and score-gate/telemetry effects before cadence conclusions. |
| `02. AlphaFactory/tools/sonic_trade_forensics.py` | authoritative | Sonic R deep trade forensics tool for weak buckets, top wins/losses, and exploratory entry-rule clusters from joined trade/state telemetry. |
| `02. AlphaFactory/tools/sonic_risk_router_sim.py` | authoritative | Report-only Sonic R risk-router simulation from forensic rule candidates; useful for falsification only because MT5 min-lot and execution constraints can invalidate linear scaling. |
| `02. AlphaFactory/tools/sonic_trade_pair_compare.py` | authoritative | Sonic R paired trade comparator; explains exact control-vs-challenger outcome deltas by entry key when management rules change exits. |
| `02. AlphaFactory/tools/sonic_gold_regime_context_audit.py` | authoritative | Sonic R GoldRegime sidecar audit; joins compact closed-bar gold flow context to final trades and tests S1 flow screens against cost, half-year, and year-diversity gates. |
| `02. AlphaFactory/tools/sonic_compression_impulse_probe.py` | authoritative | Offline Sonic R compression-to-impulse, exploratory breakout, and micro-scalp probe from PVSRA/SR closed-bar sidecars before EA lane coding. |
| `02. AlphaFactory/tools/sonic_impulse_retest_probe.py` | authoritative | Offline Sonic R post-breakout retest/reclaim probe; tests whether waiting for retest improves breakout behavior before EA code changes. |
| `02. AlphaFactory/tools/sonic_profit_period_anatomy.py` | authoritative | Sonic R profit-period anatomy analyzer for months, years, phases, lanes, direction/session, regime buckets, and signal context. |
| `02. AlphaFactory/tools/sonic_casebook_index.py` | authoritative | Sonic R casebook index and readout builder that connects visual evidence, blind labels, verified trade stats, execution, cost stress, validation, and baseline comparison. |
| `02. AlphaFactory/tools/sonic_state_label_audit.py` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Sonic R machine-suggested pre-entry label audit; assigns heuristic labels without outcome/PnL/MFE inputs, then audits them against trade/outcome fields for research only. |
| `02. AlphaFactory/tools/sonic_population_eval.py` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Sonic R population evaluator; joins Opportunities, opportunity labels, PVSRA/SR context, and Trades to test pre-entry feature lift across half-year splits before EA code changes. |
| `02. AlphaFactory/tools/sonic_prepare_mt5_snapshot_cases.py` | authoritative | Prepares bounded Sonic R case requests for MT5-native screenshot capture and writes traceable run-local artifacts. |
| `02. AlphaFactory/tools/sonic_collect_mt5_snapshots.py` | authoritative | Collects MT5-native screenshot outputs from MQL5/Files, computes SHA256, and writes run-local native screenshot manifests. |
| `02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1` | authoritative | Post-casebook Sonic R snapshot wrapper: prepare, compile/install MT5 script, collect screenshots, refresh casebook index, and write bounded JSON status. |
| `02. AlphaFactory/tools/evidence_audit.py` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Per-run evidence closure checker; verifies required artifacts before a Sonic R run is cited or used as a baseline. |
| `02. AlphaFactory/tools/sonic_s1_gate_audit.py` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. S1 sweep-reclaim audit tool; measures S1 by split/session/hour/PVSRA context and report-only cost before any dedicated S1 gate patch. |
| `02. AlphaFactory/tools/sonic_s1_deep_anatomy.py` | authoritative | S1 opportunity/trade join and bucket analyzer; reports target-RR/risk/session/PVSRA split stability and cost-adjusted keep/remove candidates before S1 geometry changes. |
| `02. AlphaFactory/tools/sonic_sideway_range_probe.py` | authoritative | Offline sideway/range-rotation probe from PVSRA/SR sidecars; labels MFE/MAE/TP/SL before any range-entry EA patch. |
| `02. AlphaFactory/tools/sonic_market_phase_attribution.py` | authoritative | Streams PVSRA/SR sidecars and joins actual trades to impulse/transition/sideway phase buckets plus per-trade labels for Sonic R regime research. |
| `02. AlphaFactory/tools/sonic_s1_phase_feature_audit.py` | authoritative | Offline S1 phase/context feature screen from market-phase trade labels, including cost and half-year stability before any EA patch. |
| `02. AlphaFactory/tools/sonic_phase_case_sampler.py` | authoritative | Builds phase-specific casebook CSVs for MT5-native snapshots, especially S1 sideway-wide losses versus S1 impulse wins. |
| `02. AlphaFactory/tools/sonic_market_regime_profit_atlas.py` | authoritative | Multi-horizon Sonic R regime atlas joining PVSRA/SR price context to trades for macro-year, volatility, trend-efficiency, range-width, and trend-alignment attribution. |
| `02. AlphaFactory/tools/sonic_research_loop.ps1` | authoritative | Dry-run-by-default strict Model 0 control/challenger loop: immutable task packet and execution receipt, shared exact EA source contract, physical cost-source checks, control bootstrap, matched-control proof, exact run marker, report-bound verified cost builder, direct unified validation, and fail-closed transitions. Current execution remains blocked by incomplete same-broker cost data and no eligible frozen candidate. |
| `02. AlphaFactory/tools/ea_contract.ps1` | authoritative | Shared fail-closed resolver for exact active EA main-source paths and explicit telemetry profiles. It pins SilverBullet to EA_SilverBullet_v2.mq5, preserves the OpenHalfMom naming exception, and forbids archive or arbitrary-file fallback. |
| `02. AlphaFactory/tools/build_verified_cost_artifact.py` | authoritative | Report-bound verified cost producer for sonic_telemetry.v3 PX6/Trades lifecycles. It joins every report deal ID to lifecycle evidence; derives spread, commission P90, and side-aware slippage from raw CSV inputs or a hash-bound JSON broker contract rather than self-attested summaries; reconciles deal and gross/net semantics; emits verified_execution_cost.v1; and has 6/6 focused unit tests passing. |
| `02. AlphaFactory/schemas/execution_data_capture_manifest.v1.schema.json` | authoritative | JSON Schema for read-only V4 execution-data bundles, including broker identity, frozen QFSI thresholds, hash-bound artifact references, required symbols, and zero-order safety fields. |
| `02. AlphaFactory/tools/execution_data_foundation.py` | authoritative | Read-only MT5 probe plus hash/row/timestamp/lookahead/sample-gate bundle validator and inventory producer; separates tester proxies from broker evidence and never exposes a mutating trade-call surface. |
| `02. AlphaFactory/analysis/unified_validation.py` | authoritative | Numeric/artifact validator for strict Model 0 challenger/confirmed stages: exact cadence, physical rehash, verified broker cost, non-repaint, stability, and freshness gates. It canonical-rebuilds verified cost from raw inputs and compares trade_repricing/scenarios. Current fixed-parameter WFA, realized-P/L robustness, PBO, and White Reality Check producers are diagnostic-only and block confirmed promotion. |
| `02. AlphaFactory/tools/runs_db.py` | authoritative | Local SQLite index and query layer for large backtest history under 02. AlphaFactory/runs/. |
| `02. AlphaFactory/tools/workspace_hygiene.ps1` | authoritative | Operational cleanup helper for MT5 sample experts, stale agent worktrees, and optional run-database rebuild. |
| `02. AlphaFactory/tools/archive_backtest_artifacts.ps1` | authoritative | Archive-first cleanup helper for stale AlphaFactory runs and Terminal/Common/Files telemetry after backtests; default dry-run, -Execute moves files to Google Drive with a manifest. Keep list includes current Sonic R evidence runs. |
| `00. Old File/markdown_graveyard/00_READ_ME_FIRST.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Legacy BB mean-reversion recommendation contradicted by validated local runs |
| `00. Old File/markdown_graveyard/CHOPPY_BOT_QUICKSTART.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Legacy implementation guide for invalidated thesis |
| `00. Old File/markdown_graveyard/CHOPPY_GOLD_INDEX.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Legacy index for invalidated package |
| `00. Old File/markdown_graveyard/CHOPPY_GOLD_RESEARCH.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Broad research note superseded by local artifacts |
| `00. Old File/markdown_graveyard/CHOPPY_GOLD_SUMMARY.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Legacy summary for invalidated package |
| `00. Old File/markdown_graveyard/CHOPPY_GOLD_VISUAL_REFERENCE.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Legacy visual reference for invalidated package |
| `00. Old File/markdown_graveyard/XAUUSD_CHOPPY_CAUSATION.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: invalidated. Historical color only, not live strategy truth |
| `00. Old File/markdown_graveyard/GOLD_EA_MARKET_RESEARCH.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: archive. Background market research archived to reduce root clutter |
| `00. Old File/markdown_graveyard/QUICK_REFERENCE_CARD.md` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: archive. Legacy quick reference archived to keep the root lean |
| `02. EA/Liquidity_Sweep_SFP/Backtest/backtest.md` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: invalidated. Historical index only; not usable evidence. EA_Liquidity_Sweep_SFP backtest 2025 XAUUSD M15: PF 0.57, 61 trades, WR 36%, DD 20.7% — strategy failed. Removed from working tree 2026-03-20, preserved in git history. |
| `02. EA/EA_SMC_Confluence/Configure/AlphaFactory_overrides.md` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: archive. Historical index only; not usable evidence. SMC Confluence AlphaFactory override config — EA removed from working tree 2026-03-20, preserved in git history. |
