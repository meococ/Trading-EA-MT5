# Run Data Policy

## Purpose
AlphaFactory produces large backtest folders, copied logs, runtime caches, and local query indexes. These are necessary for operations but should not pollute source control or the active code layout.

## Canonical storage
- Raw runs: `02. AlphaFactory/runs/<EA_NAME>/<RUN_ID>/`
- Runtime state: `02. AlphaFactory/runtime/`
- Local SQLite catalog: `02. AlphaFactory/runtime/catalog/runs.db`

## Canonical per-run evidence
For any run cited in decisions, keep these artifacts available in the run folder:
- `report.html`
- `config.ini`
- `run_manifest.json`
- `analysis/enhanced_summary.json`
- `analysis/validation_summary.json` when `validate-full` was run
- Any supporting artifacts actually used in the verdict, such as:
  - `analysis/equity_audit.json`
  - `analysis/monthly_fitness.json`
  - `analysis/wfa_results.json`
  - `analysis/robustness_results.json`
  - `analysis/monte_carlo_results.json`
  - `analysis/datalog/*.json`

## Git policy
- Raw `runs/` folders are local operational storage and are ignored by git.
- SQLite catalogs under `runtime/catalog/` are ignored by git.
- Temporary MT5 tester portable folders and stale agent worktrees are ignored by git.

## Query and indexing
- Use `python "02. AlphaFactory/tools/runs_db.py" build` to rebuild the local SQLite index.
- Use `summary`, `top`, `query`, `compare`, and `info` subcommands for fast navigation of large backtest history.
- The SQLite catalog accelerates discovery; it does not replace per-run artifacts as evidence.

## Active storage budget
- Generate the canonical inventory with `python "02. AlphaFactory/tools/backtest_storage_inventory.py"`; it reports total bytes, per-EA usage, largest files, direct orphan/generated files, and size-matched mirror candidates without hashing/deleting them.
- Default active budget: soft warning at 6 GiB and stop/new-batch review at 8 GiB. Owner may change these limits explicitly.
- Measure `02. AlphaFactory/runs/` before and after any batch of at least five runs or any batch expected to add at least 1 GiB.
- A budget breach opens a cleanup dry-run; it never authorizes automatic deletion or a scheduled cleanup loop.
- Future AlphaFactory runs keep both compatibility paths, `logs/` and `analysis/logs/`, but the second path is an NTFS hardlink when supported, so it consumes no second physical copy. A copy fallback must emit a warning.

## Retention tiers
- **Protected/canonical:** any run cited by `hot.md`, `current_state.md`, control docs, research notes, registry/prereg/readout, or an Owner keep list. Never delete automatically. Archive only with full file SHA256 inventory and an off-volume destination.
- **Research history:** killed/parked/failed runs not referenced by current decisions. After the minimum age gate, move the whole run off-volume with copy -> full hash verification -> source removal. Keep the cleanup plan and archive manifest.
- **Scratch/duplicates:** tester scratch, caches, and byte-identical `logs/` versus `analysis/logs/` mirrors. Remove scratch under its scoped hygiene tool; convert duplicate mirrors to hardlinks after exact size/SHA256 equality.
- Rebuild `runs.db` after a meaningful archive or dedupe batch. The catalog is disposable; manifests and per-run evidence are not.

## Large-log access contract
- Never use `Get-Content -Raw`, a full editor open, or unbounded tool output on a large backtest log.
- First run `large_log_reader.py inspect`. It streams the file, hashes it, counts lines/patterns, and stores only bounded head/tail/samples in `02. AlphaFactory/runtime/log_indexes/`.
- Use `search` with at most 200 matches and bounded context, or `window` with at most 500 numbered lines. Refine the query instead of increasing the cap.
- For Signals/Trades CSV, read `analysis/datalog/*.json` and `tag_summary.csv` first; use raw windows only to audit a specific anomaly.
- Use `runs_db.py` for cross-run navigation. Neither the log index nor SQLite replaces the hash-bound source artifact for a verdict.

## Cleanup
- Use `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/tools/workspace_hygiene.ps1"` to remove MT5 sample experts from repo root and prune stale agent worktrees.
- Add `-BuildRunsDb` when a cleanup pass should refresh the local catalog.
- After meaningful backtest batches, run archive-first cleanup with `02. AlphaFactory/tools/archive_backtest_artifacts.ps1`.
- Default to dry-run first. Dry-run now writes a durable plan with candidate sizes, age gate, explicit keep IDs, and run IDs discovered from canonical references.
- `-Execute` requires an exact EA name and an off-volume archive root by default. It copies, creates a full per-file SHA256 inventory, verifies the destination, and only then removes the source. Same-volume execution requires explicit `-AllowSameVolumeArchive` and does not free disk space.
- Use `dedupe_backtest_log_mirrors.ps1` separately for byte-identical compatibility mirrors. Dry-run writes a reclaimable-bytes plan; `-Execute` converts only exact matches to hardlinks.
- Clean stale `Terminal/Common/Files` telemetry and sidecars after preserving required calendar/news CSVs and any artifacts cited in decisions.
- Cleanup must not delete evidence for runs referenced by `current_state.md`, `hot.md`, `decisions.md`, or Sonic R research notes.
- Legacy/non-current EA source belongs under `00. Old File/EA_Archive/`; do not treat that folder as active source.

## Post-backtest evidence flow
- After any meaningful Sonic R backtest, run validation/comparison/cost artifacts first, then casebook/index artifacts, then MT5-native sampled snapshots only for selected cases.
- Sonic R candidate closure quickref:
  1. `alpha_json.ps1 -Action validate-full -Report ".../<RUN_ID>/report.html" -Out ".../<RUN_ID>/analysis/alpha_json_validate_full.json"`
  2. `sonic_candidate_compare.py <RUN_ID> --baseline 20260501_000718 --out ".../<RUN_ID>/analysis/sonic_candidate_compare_vs_20260501_000718.json"`
  3. `sonic_cost_stress.py <RUN_ID> --base-cost-per-trade 0.50 --out ".../<RUN_ID>/analysis/sonic_cost_stress_report_only_050.json"`
  4. `sonic_casebook_index.py --run-dir ".../<RUN_ID>"`
  5. `evidence_audit.py <RUN_ID> --baseline 20260501_000718 --require-casebook --require-compare --require-cost --out ".../<RUN_ID>/analysis/evidence_audit.json"`
  6. Optional selected screenshots via `sonic_mt5_snapshot_flow.ps1`, then rerun `sonic_casebook_index.py` and `evidence_audit.py`.
  7. Inspect large logs through `large_log_reader.py`; never ingest them whole.
  8. Dry-run `dedupe_backtest_log_mirrors.ps1` and `archive_backtest_artifacts.ps1`; use `-Execute` only after the Owner accepts the exact plan, off-volume target, and protected keep list.
- Use `02. AlphaFactory/tools/sonic_mt5_snapshot_flow.ps1` after casebook generation. The first pass prepares request CSVs, compiles/installs the MT5 script, and should report `pending_mt5_script_run` until MT5 runs `SonicR_CaseSnapshot`.
- After the MT5 script writes `SonicR_CaseSnapshot/shots.csv`, rerun the wrapper with `-SkipPrepare -SkipCompile -CleanupStaging` to collect PNGs, write `sha256.csv`, and refresh `casebook_analysis_index.json/readout.md`.
- Native screenshots are visual audit artifacts only. They can improve trader-eye review, but they do not replace `report.html`, trade CSVs, `validate-full`, cost stress, WFA, robustness, or Monte Carlo gates.
- The collector must reject stale `shots.csv`, case mismatches, partial capture, missing images, and suspiciously small or oversized screenshot payloads.

## Operational rule
- One change, one run, one interpretation.
- If a run matters enough to cite, keep its manifest and analysis artifacts intact even if the raw folder is ignored by git.
- Telemetry-on Sonic R runs should use a non-empty `InpVariantTag` so AlphaFactory sidecar hygiene can identify the intended run token.
