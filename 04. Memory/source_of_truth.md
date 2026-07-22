# Source of Truth Registry

Updated: 2026-07-21

> **Active shelf:** after the 2026-07-15 relocation and 2026-07-18 concurrent
> research, compilable EA Developer source is `EA_FVGConfluence`,
> `EA_HybridICT_Sonic`, `EA_ICTFVGReportFidelity`, `EA_ICTVisualEdge`,
> `EA_KLR_Scalper`, `EA_LSSOBPropScalper`, `EA_MZMS_Scalper`, `EA_UnicornPrecisionScalper`,
> `EA_UnicornPrecisionScalperControl`, and `EA_UnicornPrecisionScalperRR15`.
> The LSS-OB, Control and RR15 packages are retained for diagnostic reproducibility;
> their current hypotheses are terminal KILL. PO3-AMD and DRAT are
> pre-code terminal research records with no `.mq5`. Former
> `03. EA Developer/EA_SonicR/` (incl. research ledger) and `EA_SilverBullet/`
> live under `00. Old File/EA_Archive/`. Root
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
5. `05. Playbook/` (validation_gates, tool_runbook, ea_golden_path, ea_engineering_standard, research_doctrine)
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
  generic research registry), rules in `05. Playbook/` (5 core docs). Archived doctrine + AI/session
  archive under `00. Old File/project_control_archive_20260716/`.
- Keep raw AlphaFactory runs and local SQLite catalogs out of git; they are operational storage, not source-of-truth documents.
- `EA_SonicR` (research ledger) and `EA_SilverBullet` (binary-only) are archived
  under `00. Old File/EA_Archive/` — not active surface. Active compilable lanes:
  `EA_FVGConfluence`, `EA_HybridICT_Sonic`, `EA_ICTFVGReportFidelity`,
  `EA_ICTVisualEdge`, `EA_KLR_Scalper` (diagnostic-only),
  `EA_LSSOBPropScalper` (terminal MT5 zero-trade replication),
  `EA_MZMS_Scalper` (terminal full-history Model-0 diagnostic KILL;
  audit-only source),
  `EA_UnicornPrecisionScalper`,
  `EA_UnicornPrecisionScalperControl` (terminal KILL; retained for evidence),
  and `EA_UnicornPrecisionScalperRR15` (bounded diagnostic sensitivity only).
  `EA_PO3_AMD_Scalper` and `EA_DRAT_ONNX_ICT_Hybrid` remain evidence-only kills.
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
| `AGENTS.md` | authoritative | Single cross-agent operating doctrine. Slimmed 2026-07-11 to lean hard rules plus pointers; detailed doctrine moved to 05. Playbook/research_doctrine.md; active scope is owned by hot.md. |
| `CLAUDE.md` | authoritative | Pointer-only session entry file for Claude agents; defers to hot.md, 01. GOAL/GOAL.md, root INDEX.md, and AGENTS.md. Added 2026-07-11. |
| `INDEX.md` | authoritative | Root workspace map: one-line what/when pointers to control docs, research, EA source, AlphaFactory, and tests. Pointer-only; content lives at the destinations. Added 2026-07-11. |
| `.codex/operator/STATUS.md` | evidence | Operational recovery ledger for the active long-running operator task. It is subordinate to hot.md and is not research or execution authority. |
| `.codex/operator/EXPERIMENTS.jsonl` | evidence | Append-only bounded-experiment ledger for the active V2 hardening task, including red-first checks, diagnoses, and stop states. |
| `01. GOAL/GOAL.md` | authoritative | Owner-frozen north-star target: joint PF/cadence/cost-stress/exposure/evidence-window table, DONE ladder, non-goals, and probe-first operating principle. Changes only on explicit Owner decision; numeric authority remains validation_gates.md. |
| `05. Playbook/research_doctrine.md` | authoritative | Full research/validation doctrine: research workflow, registry contract, probe-plan freeze and versioning, chart-state label contract, multiple-testing budget, team review roles, MT5 non-repaint rules, and backtest hygiene. |
| `04. Memory/validate_source_of_truth.py` | authoritative | Fail-closed local/backup availability, SHA256, duplicate-path, and JSON-to-Markdown registry consistency validator. |
| `05. Playbook/validation_gates.md` | authoritative | Stage-gate matrix for every EA lane: probe, screened, challenger, confirmed, portfolio-sleeve; required artifacts, thresholds, multi-simulation deflation conventions, and hard invalidations. |
| `00. Old File/agent_guidance_archive/20260503_1916_sonic_readme_cleanup/manifest.json` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: archive. Manifest for retired Claude/doc/root guidance layers archived during the Sonic R knowledge-map cleanup. |
| `04. Memory/hot.md` | authoritative | Fast-path session cache (<500 words). Replaces current_state header at session start. |
| `04. Memory/source_of_truth.md` | authoritative | Human-readable registry |
| `04. Memory/source_of_truth.json` | authoritative | Machine-readable registry |
| `05. Playbook/ea_engineering_standard.md` | authoritative | Generic MQL5 engineering standard: closed-bar signal contract, ownership/state recovery, broker geometry, risk, lifecycle telemetry, and promotion boundaries. |
| `05. Playbook/ea_golden_path.md` | authoritative | Generic design-to-decision workflow for every EA: intake, de-dup, cheap probe, frozen prereg, canonical build, capability/cost preflight, sequential Model 0 control/challenger, validation, and closeout. |
| `05. Playbook/tool_runbook.md` | authoritative | Generic AlphaFactory command runbook: CLI, guarded research loop, candidate compare, cost stress, research utilities, market-data acquisition, runs DB, and cleanup. |
| `00. Old File/EA_Archive/README.md` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Archive-only rule for retired/non-current EA source; confirms EA_SonicR remains the only active EA source. |
| `02. AlphaFactory/STRATEGY_LOG.md` | authoritative | Experiment memory |
| `02. AlphaFactory/tools/alpha_json.ps1` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. JSON wrapper around selected alpha.ps1 actions; separates command completion from strategy validation verdict for agent/MCP workflows. |
| `02. AlphaFactory/tools/candidate_compare_engine.py` | authoritative | Per-run artifact comparator against a frozen baseline for archived strict-format evidence; rejects identity mismatches and PF-only conclusions. |
| `02. AlphaFactory/tools/research_cost_stress.py` | authoritative | Report-only per-trade cost-stress matrix for first-pass falsification; not broker-informed unless a cost conversion is bound. |
| `02. AlphaFactory/tools/repro_drift_map.py` | authoritative | Reproducibility drift mapper comparing run identity, input hashes, metric deltas and gate/telemetry effects before cadence conclusions. |
| `02. AlphaFactory/tools/evidence_audit.py` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Per-run evidence closure checker; verifies required artifacts before a Sonic R run is cited or used as a baseline. |
| `02. AlphaFactory/tools/research_loop_engine.ps1` | authoritative | Compatibility engine behind the generic EA research entrypoint: dry-run-by-default strict Model 0 control/challenger loop, immutable task packet and receipt, registry/source/capability/cost binding, matched-control proof, validation, and fail-closed transitions. |
| `02. AlphaFactory/tools/ea_research_loop.ps1` | authoritative | Generic public entrypoint for the strict AlphaFactory control/challenger loop; delegates to the compatibility engine without weakening its contract. |
| `02. AlphaFactory/tools/alpha_candidate_compare.py` | authoritative | Generic identity-bound challenger comparator using control-relative net, PF, and net-to-drawdown improvement; absolute acceptance is frozen in the canonical registry/task packet and passed to unified validation. |
| `02. AlphaFactory/tools/ea_contract.ps1` | authoritative | Shared fail-closed resolver for exact active EA source and optional hash-bound per-package capability contract (telemetry, phase, comparator, variant input). It pins EA_FVGConfluence and EA_HybridICT_Sonic and forbids archive or arbitrary-file fallback. |
| `02. AlphaFactory/tools/build_verified_cost_artifact.py` | authoritative | Report-bound verified cost producer for generic AlphaFactory LifecycleTrades and legacy PX6 lifecycles. It joins report deals, derives cost from raw or hash-bound broker evidence, reconciles P&L/risk, and emits verified_execution_cost.v1. |
| `02. AlphaFactory/tools/validate_ea_delivery_packet.py` | authoritative | Fail-closed EA development completion validator. It rehashes logic/source/build/run/log/analysis/casebook bindings and rejects missing win-loss or zero-trade forensics before a DONE claim. |
| `02. AlphaFactory/tools/research/dsr.py` | authoritative | Canonical Deflated Sharpe Ratio implementation with the workspace trial-accounting conventions (N = every executed simulation; cost tiers not separate trials); self-tested against the paper's E[max SR] example. |
| `02. AlphaFactory/tools/research/fivepercent_server_clock.py` | authoritative | Canonical FivePercent server-to-UTC clock model: UTC+2/+3 with EU DST calendar through 2023 and US DST calendar from 2024, verified weekly via Friday-17:00-NY close anchors. |
| `02. AlphaFactory/tools/research/snapshot_c_roots.ps1` | authoritative | Zero-arg wrapper snapshotting the 4 protected C roots by delegating to tools/snapshot_mt5_storage.ps1; the digest implementation stays single-sourced. |
| `02. AlphaFactory/tools/research/chart_case_render.py` | authoritative | Per-case candlestick renderer from hash-bound bar data plus a cases CSV; asof mode draws only bars closed before entry (decision-time information set), anatomy mode is outcome-only; emits a manifest with per-image SHA256. Required basis for any chart claim in readouts/preregs. |
| `02. AlphaFactory/tools/research/log_triage.py` | authoritative | Streaming standard error-pattern battery for heavy tester/EA logs; one compact JSON summary so raw logs never enter agent context except targeted windows. |
| `02. AlphaFactory/tools/research/indicators.py` | authoritative | Single-source indicator math with two variant families: *_wilder (literature) and *_mt5 (iATR = SMA of TR, iADX = EMA of per-bar DI; parity-proven ~5e-11 against build 6006). A frozen plan must state which family it uses; Model-0-bound lanes use *_mt5. |
| `02. AlphaFactory/tools/research/sealed_loader.py` | authoritative | Holdout-sealed parquet loading with read-time filter, post-load assert and a seal receipt; split tagging and elapsed-calendar-week helpers. |
| `02. AlphaFactory/tools/research/trial_log.py` | authoritative | Canonical trial-log appender: hypothesis_id + prereg_sha256 required on every row, numpy-safe single serialization. |
| `02. AlphaFactory/tools/research/metrics.py` | authoritative | Mechanism-neutral per-trade-R metrics: profit factor, expectancy, drawdown in R and percent, by-year stats, DSR inputs, top-1 win share, leave-one-out PF. |
| `02. AlphaFactory/tools/research/controls.py` | authoritative | Negative-control entry generators (matched-random and time-shift) producing timestamps only; the lane's frozen exit engine simulates them so control and challenger share identical mechanics. |
| `02. AlphaFactory/tools/research/parity_harness.py` | authoritative | MT5 indicator parity instrument: compiles and runs mql5/ParityDump.mq5 in the portable FivePercent terminal via a StartUp config, proves bar identity against the lane parquet, diffs iATR/iADX/iRSI vs the python *_mt5 variants and emits a PASS/FAIL parity artifact. |
| `02. AlphaFactory/tools/research/mql5/ParityDump.mq5` | authoritative | Harness-only chart script (no trading): dumps closed-bar iATR/iADX/iRSI values to CSV on the portable data root and closes the terminal. |
| `02. AlphaFactory/tools/snapshot_mt5_storage.ps1` | authoritative | Canonical bounded metadata-inventory hasher for MT5 storage roots used by before/after C-root receipts. The only valid digest implementation for alphafactory_mt5_storage_snapshot.v1. |
| `02. AlphaFactory/templates/research/PROBE_PLAN.template.md` | authoritative | Pre-outcome frozen probe-plan template: identity, de-dup, hash-bound data, frozen decision surface, trial accounting plus DSR, kill gates, exclusions, exhaustive-grid variant clauses. |
| `04. Memory/research/CANDIDATE_REGISTRY.jsonl` | authoritative | Canonical append-only hypothesis state ledger shared by all active EA packages; current seed records the FVG probe and terminal Hybrid SIGATR kill. |
| `04. Memory/research/CANDIDATE_REGISTRY.schema.json` | authoritative | Generic schema for AlphaFactory hypothesis state rows. |
| `04. Memory/research/validate_candidate_registry.py` | authoritative | Fail-closed registry validator for strict JSON, schema, canonical source/prereg hash binding, non-weakenable structured acceptance gates, Model 0 execution states, immutable identity, terminal states, and legal append transitions. |
| `02. AlphaFactory/templates/research/README.md` | authoritative | Canonical generic templates and lifecycle-v3 capability guidance for new EA research packages. |
| `02. AlphaFactory/templates/research/EA_DELIVERY_PACKET.template.json` | authoritative | Template for the hash-bound logic-to-backtest-to-forensics completion packet required after meaningful EA runs. |
| `02. AlphaFactory/templates/research/LOGIC_TO_CODE_MATRIX.template.md` | authoritative | Pre-outcome mapping template from trader observation through quantified role, decision-time data, source, telemetry and verification. |
| `02. AlphaFactory/schemas/ea_delivery_packet.v1.schema.json` | authoritative | Machine schema for AlphaFactory EA development delivery packets; the Python validator enforces the deeper conditional evidence rules. |
| `02. AlphaFactory/schemas/execution_data_capture_manifest.v1.schema.json` | authoritative | JSON Schema for read-only V4 execution-data bundles, including broker identity, frozen QFSI thresholds, hash-bound artifact references, required symbols, and zero-order safety fields. |
| `02. AlphaFactory/tools/execution_data_foundation.py` | authoritative | Read-only MT5 probe plus hash/row/timestamp/lookahead/sample-gate bundle validator and inventory producer; separates tester proxies from broker evidence and never exposes a mutating trade-call surface. |
| `02. AlphaFactory/analysis/unified_validation.py` | authoritative | Numeric/artifact validator for strict Model 0 challenger/confirmed stages: exact cadence, physical rehash, verified broker cost, non-repaint, stability, and freshness gates. It canonical-rebuilds verified cost from raw inputs and compares trade_repricing/scenarios. Current fixed-parameter WFA, realized-P/L robustness, PBO, and White Reality Check producers are diagnostic-only and block confirmed promotion. |
| `02. AlphaFactory/tools/runs_db.py` | authoritative | Local SQLite index and query layer for large backtest history under 02. AlphaFactory/runs/. |
| `02. AlphaFactory/tools/workspace_hygiene.ps1` | authoritative | Dry-run-by-default operational cleanup helper for root MT5 sample experts and stale agent worktrees; -Execute is required for deletion or optional run-database rebuild. |
| `02. AlphaFactory/tools/archive_backtest_artifacts.ps1` | authoritative | Archive-first cleanup helper for stale AlphaFactory runs and Terminal/Common/Files telemetry; default dry-run, explicit EA scope, current control-surface reference scanning, contained atomic plans, and copy/hash-verify/remove execution with a manifest. |
| `02. AlphaFactory/tests/test_operational_hygiene.py` | authoritative | Offline regression tests for cleanup dry-run semantics, archive reference protection and path containment, Windows validator encoding, live registry pins, and runbook command-surface truth. |
| `02. AlphaFactory/tests/test_ea_golden_path.py` | authoritative | Offline regression suite for generic EA discovery, removed backup mutation surface, registry and acceptance validation, package capability contracts, research dry-run, lifecycle RunMeta identity, and generic matched-control comparison. |
| `02. AlphaFactory/tests/test_ea_delivery_packet.py` | authoritative | Regression suite for valid economic and zero-trade delivery packets plus missing evidence, tampered hashes, incomplete analysis and chart-marker failures. |
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
