# Source of Truth Registry

Updated: 2026-07-30

> **Role:** this registry records canonical paths and availability. It is not a
> live shelf inventory and never grants source/run/rerun/promotion/live
> authority. Resolve the current EA shelf from `03. EA Developer/README.md`,
> disk and `02. AlphaFactory/alpha.ps1 status`; resolve hypothesis state from
> the candidate registry and exact artifacts.

## Authority and use order

1. Apply `AGENTS.md` for governance and `01. GOAL/GOAL.md` for the Owner outcome.
2. For execution decisions: current Owner scope → hard safety/active lock →
   frozen prereg/registry/task packet → source/run/receipt/validator artifacts.
3. Use this registry only to prove which path is canonical/available.
4. `hot.md`, failure catalogs, old reports, operator ledgers and sub-agent memos
   are context for routing/de-dup; they do not override 1–3.
5. `00. Old File/` is historical/archive-only and cannot produce new execution
   evidence.

## Root hygiene rule
- Keep the project root lean.
- Root should contain only: `AGENTS.md` (cross-agent launcher), `CLAUDE.md`
  (pointer-only Claude entry), `INDEX.md` (workspace map), and the
  `01. GOAL/` folder holding the Owner-frozen `GOAL.md`. The hidden
  `.codex/operator/` recovery ledger is also allowed for long-running
  operator-loop tasks, but it is a non-authoritative recovery pointer.
- Do **not** keep root stubs for `README-SONIC-R.md` or `SYNC_REPORT.md`
  (archived under `00. Old File/docs_archive/`).
- Root must not keep MT5 sample experts such as `ExpertMACD.mq5` or their compiled `.ex5` outputs.
- Move retired markdown to `00. Old File/docs_archive/` (preferred) or
  `00. Old File/markdown_graveyard/`.
- Keep control docs split: state in `04. Memory/` (hot.md, do_not_repeat,
  generic research registry), rules in `05. Playbook/` (5 core docs). Archived doctrine + AI/session
  archive under `00. Old File/project_control_archive_20260716/`.
- Keep raw AlphaFactory runs and local SQLite catalogs out of git; they are operational storage, not source-of-truth documents.
- `EA_SonicR` and binary-only `EA_SilverBullet` are archived under
  `00. Old File/EA_Archive/` — not active surface. Do not hard-code the active
  shelf here; use `03. EA Developer/README.md`, disk and AlphaFactory status.
- Retired or cached EA source outside an explicitly opened lane belongs under
  `00. Old File/EA_Archive/` and is archive-only.

## Availability contract

- A status of `authoritative`, `evidence`, `archive`, or `invalidated` means the path exists in this checkout.
- `backup-only` means the local path is absent and its external backup hash is pinned. The backup is hash-checked whenever its declared root is mounted; an unavailable root declared `optional` emits a portability warning instead of failing unrelated local truth.
- `unavailable-unresolved` means the path is absent both locally and at that declared backup root. It is a historical index record only, not usable evidence.
- Run `python "04. Memory/validate_source_of_truth.py"` before relying on this registry.
- Use `--strict-backups` only for an explicit backup-audit job that requires every optional external root to be mounted.

## Registry
| Path | Status | Why it matters |
| --- | --- | --- |
| `AGENTS.md` | authoritative | Single cross-agent operating doctrine with the Owner-to-artifact authority order, hard rules and canonical pointers; active scope is resolved from current Owner intent plus frozen contracts and artifacts, never from hot.md. |
| `CLAUDE.md` | authoritative | Pointer-only session entry file; defers to AGENTS.md, GOAL.md, INDEX.md and current registry/artifact truth. |
| `INDEX.md` | authoritative | Pointer-only workspace map; dynamic package metrics and hypothesis state stay at their canonical destinations. |
| `.codex/operator/STATUS.md` | evidence | Non-authoritative recovery pointer for long operator sessions; it contains no live metrics or execution authority. |
| `.codex/operator/EXPERIMENTS.jsonl` | evidence | Append-only bounded-experiment ledger for the active V2 hardening task, including red-first checks, diagnoses, and stop states. |
| `01. GOAL/GOAL.md` | authoritative | Owner-frozen north-star target: joint PF/cadence/cost-stress/exposure/evidence-window table, DONE ladder, non-goals, and probe-first operating principle. Changes only on explicit Owner decision; numeric authority remains validation_gates.md. |
| `05. Playbook/research_doctrine.md` | authoritative | Full research/validation doctrine: research workflow, registry contract, probe-plan freeze and versioning, chart-state label contract, multiple-testing budget, team review roles, MT5 non-repaint rules, and backtest hygiene. |
| `04. Memory/validate_source_of_truth.py` | authoritative | Fail-closed local availability, mounted-backup SHA256, duplicate-path, and JSON-to-Markdown consistency validator; absent optional external backup roots warn by default and --strict-backups restores fail-closed audit mode. |
| `05. Playbook/validation_gates.md` | authoritative | Stage-gate matrix for every EA lane, including Two-Speed Fast-Kill versus Heavy-Delivery closeout and promotion-grade aligned-variant confirmed evidence. |
| `00. Old File/agent_guidance_archive/20260503_1916_sonic_readme_cleanup/manifest.json` | backup-only | Local availability: absent in the lean checkout; hash-verified backup only. Original status: archive. Manifest for retired Claude/doc/root guidance layers archived during the Sonic R knowledge-map cleanup. |
| `04. Memory/hot.md` | evidence | Compact recent-routing cache; every claim requires artifact verification and the file grants no execution authority. |
| `04. Memory/source_of_truth.md` | authoritative | Human-readable registry |
| `04. Memory/source_of_truth.json` | authoritative | Machine-readable registry |
| `05. Playbook/ea_engineering_standard.md` | authoritative | Generic MQL5 engineering standard: closed-bar signal contract, ownership/state recovery, broker geometry, risk, lifecycle telemetry, and promotion boundaries. |
| `05. Playbook/ea_golden_path.md` | authoritative | Generic design-to-decision workflow for every EA: intake, de-dup, probe, prereg, build, Model 0, then Fast-Kill or Heavy-Delivery routing without post-hoc rescue. |
| `05. Playbook/tool_runbook.md` | authoritative | Generic AlphaFactory command runbook: Two-Speed closeout, confirmed aligned-variant validation, guarded MT5 research, evidence operations and cleanup. |
| `00. Old File/EA_Archive/README.md` | unavailable-unresolved | Local availability: absent in the lean checkout and not found at the declared backup root on 2026-07-11. Original status: authoritative. Historical index only; not usable evidence. Archive-only index for retired/non-current EA source; it makes no claim about the current active shelf. |
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
| `02. AlphaFactory/tools/research/setup_fivepercent_market_data.py` | authoritative | Hash-bound one-use zero-trade producer source for DATA-FIVEPERCENT-5ASSET-MULTITF-004; preserves source epochs, reconciles only exact duplicate rows and null-flags continuous-BTC DST UTC ambiguity. Consumed; not a general rerun authority. |
| `02. AlphaFactory/tools/research/finalize_fivepercent_market_data_receipt.py` | authoritative | Dataset-004 receipt-only recovery producer: independently re-hashes all 20 manifest files and protected-C reconciliation without importing MT5 or rewriting data/manifest. Consumed one-use evidence path. |
| `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json` | authoritative | Canonical local manifest for the completed FivePercent EURUSD/USDJPY/GBPUSD/XAUUSD/BTCUSD M1/M5/H1/H4 raw corpus; 48,314,068 rows, zero orders/economics, with BTC UTC ambiguity explicit. |
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
| `02. AlphaFactory/alpha.ps1` | authoritative | Canonical AlphaFactory command entrypoint; includes lean fast-kill validation and Heavy-Delivery plus full validation surfaces. |
| `02. AlphaFactory/tools/validate_fast_kill_closeout.py` | authoritative | Fail-closed hash and sample-bound validator for terminal probe or Model-0 Fast-Kill cells without chart or Grok ceremony. |
| `02. AlphaFactory/schemas/fast_kill_closeout.v1.schema.json` | authoritative | Machine schema for lean terminal Fast-Kill closeout packets. |
| `02. AlphaFactory/templates/research/FAST_KILL_CLOSEOUT.template.json` | authoritative | Template for preregistered minimum-sample and sequential-boundary Fast-Kill closeout. |
| `02. AlphaFactory/analysis/aligned_variant_evidence.py` | authoritative | Fail-closed loader for the preregistered full Model-0 variant family, physical source-binary-report rehash, daily net-R alignment, family closure and frozen analysis settings. |
| `02. AlphaFactory/schemas/aligned_variant_manifest.v1.schema.json` | authoritative | Machine schema for promotion-grade aligned variant-family evidence. |
| `02. AlphaFactory/templates/research/ALIGNED_VARIANT_MANIFEST.template.json` | authoritative | Template for a preregistered hash-bound aligned variant family used by confirmed-stage producers. |
| `02. AlphaFactory/analysis/walk_forward.py` | authoritative | Dual-mode WFA producer: legacy fixed-parameter diagnostic or expanding-window locked-OOS selection from an aligned variant manifest. |
| `02. AlphaFactory/analysis/robustness_suite.py` | authoritative | Dual-mode robustness producer: legacy realized-P-L diagnostics or matched Model-0 rerun parameter sensitivity from a frozen variant family. |
| `02. AlphaFactory/analysis/cscv_pbo.py` | authoritative | Dual-mode CSCV-PBO producer; promotion mode consumes the complete preregistered aligned daily net-R matrix. |
| `02. AlphaFactory/analysis/white_reality_check.py` | authoritative | Dual-mode White Reality Check producer; promotion mode uses joint moving-block resampling across the aligned full variant family. |
| `02. AlphaFactory/analysis/unified_validation.py` | authoritative | Numeric and artifact validator for Model-0 challenger and confirmed stages; promotion producers must bind the exact report, run, source, preregistered aligned variant manifest and full variant tree. |
| `02. AlphaFactory/tools/runs_db.py` | authoritative | Local SQLite index and query layer for large backtest history under 02. AlphaFactory/runs/. |
| `02. AlphaFactory/tools/workspace_hygiene.ps1` | authoritative | Dry-run-by-default operational cleanup helper for root MT5 sample experts and stale agent worktrees; -Execute is required for deletion or optional run-database rebuild. |
| `02. AlphaFactory/tools/archive_backtest_artifacts.ps1` | authoritative | Archive-first cleanup helper for stale AlphaFactory runs and Terminal/Common/Files telemetry; default dry-run, explicit EA scope, current control-surface reference scanning, contained atomic plans, and copy/hash-verify/remove execution with a manifest. |
| `02. AlphaFactory/tests/test_fast_kill_closeout.py` | authoritative | Regression tests for lean probe and Model-0 Fast-Kill integrity, anti-posthoc and minimum-sample sequential boundaries. |
| `02. AlphaFactory/tests/test_promotion_producers.py` | authoritative | Regression tests for aligned promotion producers, hash tamper, family closure and unified run binding. |
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
