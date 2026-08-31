# Repo cleanup + path-migration plan

Date: 2026-08-31
Workspace: `D:\Meta 5\Trading-EA-MT5`
Status: PLAN ONLY. This file is the only artifact this job is allowed to create.
Authority: Owner request → `01. GOAL/GOAL.md` → running contract → verified disk → registry. `04. Memory/hot.md` is cache.

Machine facts re-checked today: not a git repo; Python is the Microsoft Store stub; factory portable is pinned in gitignored `02. AlphaFactory/alpha.local.ps1` to `...\runtime\mt5-portable-mqdemo`; Owner GUI `D:\Meta 5\terminal64.exe` is running and is not a factory target; AppData clone `B68D05E1E7631B51201DCA32FCF5F4A6` exists and must not become the factory target; stale GUID `D0E8209F77C8CF37AD8BF550E51FF075` does not exist; old root `D:\Trading EA MT5` does not exist; `C:\Users\ADMIN` does not exist; `G:\` is offline.

Impact-per-effort order is the execution order in §7. Prefer archive/delete of dead weight over writing more markdown. Living files to touch later: `AGENTS.md`, `05. Playbook/WORKFLOW.md`, `03. EA Developer/README.md`, `04. Memory/source_of_truth.json`, `04. Memory/hot.md`, `02. AlphaFactory/analysis/decision_framework.py`, `02. AlphaFactory/DECISION_FRAMEWORK.md`, `.gitignore`, `.gitattributes`, `CONTRIBUTING.md`, `alpha.ps1`, `alpha.local.ps1.example`, probe defaults, `requirements.txt`. Do not restore the five missing playbook files. Do not recreate `INDEX.md`.

---

## 1. Verification table

Each of the 24 Owner findings, re-opened on disk today. `CONFIRMED` = Owner is right. `CORRECTED` = direction is right but a count, line, or causal claim is wrong. `REFUTED` = Owner is wrong. No finding is REFUTED.

| # | Verdict | What is true, with file:line |
|---|---|---|
| 1 | CONFIRMED | Live `& ".\02. AlphaFactory\alpha.ps1" status` emits exactly 9 `WARNING: Ignoring invalid active EA package` for `EA_ASRS_AdaptiveSweepReclaim`, `EA_CME6E_RawBreakBookState`, `EA_DRAT_ONNX_ICT_Hybrid`, `EA_EventCLOBPersistence`, `EA_FiveAssetDataFoundation`, `EA_GoldMacroPulse`, `EA_KalshiMacroPrint`, `EA_PO3_AMD_Scalper`, `EA_SGEFixingPulse`. Each of those 9 dirs contains only `README.md`. Rule: `alpha.ps1:1081-1106` + `tools/ea_contract.ps1:28-56` — warn when canonical `<EA>/<EA>.mq5` is missing **and** there is no `research/` dir. Census: 96 `EA_*` dirs, 87 with canonical `.mq5`, 9 invalid, 0 research-only. |
| 2 | CONFIRMED | `source_of_truth.json:42,52,80,85,90` still mark the five playbook files `authoritative`. On disk `05. Playbook/` contains only `WORKFLOW.md` and empty `Strategy/`. Glob of those five filenames across the repo = 0. |
| 3 | CONFIRMED | `source_of_truth.json` has zero `docs/` paths. `docs/EA_AUDIT_REPORT.md:2` self-labels `Status: authoritative`; `:6` `VERDICT: PASS — deployable on E8 Markets (USDJPY+)` for `EA_ITSM`. `GOAL.md:53` `ITSM / Hybrid / v10 / archive không revive`. `docs/PAPER_DEPLOY_GUIDE.md:7-11` lists Cobra / SilverBullet / Spark / InsideBar. Owner’s extra three names (ITSM, D1InsideDay, H4Ribbon) appear in the audit/handoff layer, not in the 4-EA table. All seven names have **no folder and no `.mq5`** under this workspace. Content dates are 2026-03-29 to 2026-04-14. Filesystem mtime is 2026-08-31 (copy), not authorship. |
| 4 | CONFIRMED | `AGENTS.md:89-91` names seven sub-agents under `.cursor/agents/`. `.cursor/` and `.codex/` do not exist. `source_of_truth.json:27-34` still lists `.codex/operator/STATUS.md` and `EXPERIMENTS.jsonl` as `evidence`. `.gitignore:73-77` ignores `.cursor/*` with `!.cursor/agents/` exceptions; `.gitignore:83` ignores `.codex/operator/`. |
| 5 | CONFIRMED | `SECURITY.md` cited by `CONTRIBUTING.md:37` — missing. `INDEX.md` declared authoritative at `source_of_truth.json:6,22-24` — missing. `00. Old File/` cited by `CLAUDE.md:16`, `GOAL.md:30`, `03. EA Developer/README.md:4,10` — missing. `05. Playbook/tool_runbook.md` cited by `WORKFLOW.md:190` — missing. None of these four names exist anywhere in the tree. |
| 6 | CONFIRMED | `WORKFLOW.md:184-187` are four unquoted `./02. AlphaFactory/alpha.ps1 ...` lines. PowerShell splits on the space after `./02.`. Extra hit: `03. EA Developer/README.md:3` uses the same unquoted form for `list`. Extra: `EA_SonicR_PVSRA/README.md:45` `powershell -NoProfile -File .\02. AlphaFactory\alpha.ps1 compile EA_SonicR_PVSRA` also breaks on the space unless `-File` is quoted. |
| 7 | CONFIRMED | `analysis/cobra_tail_harvester.py:22` and `analysis/factor_dsr_analysis.py:51` hardcode `c:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\Advisors`. Additional live/test hits of the same GUID: `tests/test_mt5_portable_storage.py:166-178`; frozen `analysis/eurjpy_usdjpy_leadlag_m5.json:37-38`; `docs/E8_SYMBOL_AUDIT.md:69`; `docs/handoff/handoff-20260414-2314.md:57,60`; `STRATEGY_LOG.md:838,3984`. GUID does not exist on this machine. |
| 8 | CONFIRMED | `tools/research/empirical_probe_runner.py:40-42` `C:\Users\ADMIN\.gemini\antigravity\brain\911cac32-...\final_ea_build_plan.md`. Only `.gemini` / `antigravity` hit. |
| 9 | CONFIRMED | `skills/perplexity-search/SKILL.md:23` `C:\Users\ADMIN\.openclaw\workspace\skills\perplexity-search\scripts\search.py`. Skill already `DEPRECATED-SOFT` at `:4` (YAML `status:`). |
| 10 | CONFIRMED | `tests/test_setup_fivepercent_market_data.py:67` `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent`. Additional **executable** old-root strings: `tests/test_mt5_portable_storage.py:169,179,185-189,201,210-214,224-228,239-242`. Old root does not exist. Several of those test strings are **negative fixtures** (must stay forbidden-shaped, not retargeted at this machine’s real portable). |
| 11 | CONFIRMED | Defaults to `C:\Program Files\MetaTrader 5\terminal64.exe`: `tools/impact_pressure_probe.py:623`, `tools/drat_onnx_ict_probe.py:500`, `tools/his_offline_gatecount_eurusd_m15.py:309`, `tools/mt5_uia_backtest_probe.ps1:95`. That Program Files path **does not exist here**. Owner GUI that **does** exist is `D:\Meta 5\terminal64.exe` (seen live in `alpha.ps1 status`). Extra: `alpha.ps1:109-119` still auto-detects Program Files if `alpha.local.ps1` is missing. `mt5_storage_contract.ps1:183-187` lists Program Files as a **denylist**, which is correct — do not turn that list into a candidate. |
| 12 | CONFIRMED | `docs/PAPER_DEPLOY_GUIDE.md:27-28` uses `02. EA Developer/`. `source_of_truth.json:383,390` uses `02. EA/` as historical `unavailable-unresolved` index (do **not** rewrite those two into `03. EA Developer/` — the EAs were removed 2026-03-20). Live bug: `tools/vector_memory.py:91,96-99,125-126` still globs `02. EA Developer`. Real shelf is `03. EA Developer/`. |
| 13 | CORRECTED | `.gitattributes` has a comment at `:1` then **5** rules. Owner’s “2 of 5” counted prefixes. Four rules target missing trees: `:2-3` `**/EA_SonicR/research/*` (`EA_SonicR` exists as mq5+Include+README, **no** `research/`); `:4-5` `**/EA_VolmanCausalGrammar/research/*` (package absent). `:6` still matches `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_EXECUTION_FREEZE_V1.json`. |
| 14 | CONFIRMED | `AGENTS.md:58` `(Owner đã mở BTCUSD)`. `GOAL.md:21-22` lists exactly `XAUUSD, EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD`. BTCUSD is absent from GOAL and hot.md. GOAL outranks AGENTS (`AGENTS.md:13`). |
| 15 | CONFIRMED | `GOAL.md:12,36` and `WORKFLOW.md:139` `PF > 1.30`. `decision_framework.py:39` `GATE_PF = 1.4`; `DECISION_FRAMEWORK.md:92` `PF \| >= 1.4 \| Hard`. Scope: `alpha.ps1` never calls `decision_framework.py`. Live validator `unified_validation.py:62` already uses `"min_profit_factor": 1.30`. |
| 16 | CORRECTED | `GOAL.md:13,37` DONE cadence is 2–5 trades/week. `AGENTS.md:59-60` already says that is a DONE threshold, not a default kill-gate. `DECISION_FRAMEWORK.md:96` `Trades/month >= 20` is **Soft**. Hard auto-fail is `Total trades >= 200` (`DECISION_FRAMEWORK.md:97,108` and `decision_framework.py:43,127-138`). A GOAL-compliant 2–3/week EA is **not** auto-failed by the 20/month floor (warn only). It **is** auto-failed if a short Fast-Kill window yields N<200 (≈1 year at 2/week). Live harness `unified_validation.py:63-65,71` uses cadence fallbacks `0.01–10000`/week and `min_confirmed_trades: 100`. |
| 17 | CORRECTED | Dates hold: registry newest `updated_at_utc=2026-08-02T16:15:00Z` (row 469, `HYP-VRAS-USDJPY-M5-003`); `STRATEGY_LOG.md` last dated section `2026-08-13`; `hot.md:3` `Updated: 2026-08-27`. IBRK / I1PB / `HYP-SONICR-XAU-H1-H4AT-001` have **zero** registry rows. Host match holds: `EA_SonicR_PVSRA.mq5:3,8,38,42,97` = H4AT-001, v4.86, magic 16082776 (`:96` is `EA_NAME`; hypothesis const is `:97`). “Zero EA” is too strong: IBRK_* and I1PB_* are reject-reason tokens **inside the host** at `Include/SNR_Signal.mqh:53990-54195`, same file family as variant `XAU_H1_H4AT`. They are not standalone packages. Mapping them to `EA_EuropeInitialBalanceBreakout` (`HYP-EIBB-...`) or `EA_H1PrevDayBreak` (`HYP-PDBREAK-...`) is a nickname guess; those hypothesis IDs do not match hot.md. `02. AlphaFactory/runs/` does not exist, so Fast-Kill ids `20260827_085615` / `20260827_141109` have no local run artifact. Live registry is 469 rows, not the 978-row copy `STRATEGY_LOG.md` still describes. |
| 18 | CONFIRMED | Recomputed from `CANDIDATE_REGISTRY.jsonl` (469 rows): 156 non-empty `source_path` occurrences / 25 unique / **25/25 resolve**. 166 unique `prereg_path` / **0/166 resolve**. 53 unique `ea_name`, **23 with no folder**. Ghosts: `EA_ActivityResponseContinuation`, `EA_CFTCOptionsPulse`, `EA_CMEParticipationPulse`, `EA_DiurnalResidualImpulse`, `EA_ECRS_CompressionReleaseScalper`, `EA_EuropeOpenUSDDemand`, `EA_EURSessionDrift`, `EA_EventVolOCO`, `EA_G10WeeklyXSMomentum`, `EA_GLDFlowPulse`, `EA_HVGQAWAP_StateEngine`, `EA_HybridRegimeMR`, `EA_JumpClusterDecayReversal`, `EA_LiquidityVacuumOvershootReversal`, `EA_LondonFixHalfHourMomentum`, `EA_LondonOpenJPYMomentum`, `EA_LondonOpenMultiAssetMomentum`, `EA_RoundNumberCascade`, `EA_SpreadRecoveryImpactReversal`, `EA_TrendStackContinuation`, `EA_TriangularConsensusLag`, `EA_VolumeClockExhaustion`, `EA_VRAS_FirstPassageAcceptance`. Sample missing prereg: `03. EA Developer/EA_FVGConfluence/research/HYP-FVG-SCALP-CONFL-M5-EUR-001_PREREG.md`. |
| 19 | CONFIRMED | 34 EA READMEs cite `research/`; 9 of those packages still have a `research/` dir; **25 cite a missing dir**. Host: `EA_SonicR_PVSRA/README.md:38` `research/SNR_INVARIANTS.md` — file absent. The 25: ASRS, CME6E, CompBreak, DOLUI, DRAT, EffPersist_V7R1, EventAggressorFlow, EventCLOB, EventDepthTransfer, FiveAsset, FixReversal, FVGConfluence, GoldMacroPulse, LondonAuction, NativeSessionStatsProbe, PO3, Residual, SGEFixingPulse, SonicR, SonicR_PVSRA, VolRegime, VolThrust, VRAS_PathConfirmedTrend, VRAS_V3, WickReject. 8 of the 9 empty packages are in this 25; Kalshi README writes `esearch/` (typo) so it did not match. |
| 20 | CORRECTED | `Get-EAs` starts at `alpha.ps1:1081`; the `EA_*` filter is `:1090`. All six exist and are **indicators**, not Experts: `AI_Regime_Detection.mq5:31` `indicator_separate_window`; `Modern_Bollinger_Bands_GBB.mq5:27` `indicator_chart_window`; `QQE_MOD.mq5:25` `indicator_separate_window`; `SMC_Order_Block_Detector.mq5:7` `indicator_chart_window`; `TB_Smart_Money_Concept_2026.mq5:58` `indicator_chart_window`; `Volatility_Regime_Classifier_QuantRegime.mq5:36` `indicator_chart_window`. Invisible-to-harness is intended. Other non-`EA_*`: `_Shared/*.mqh` plus host `EA_SonicR_PVSRA/Indicators/SNR_*.mq5`. |
| 21 | CONFIRMED | `.gitignore:86` `04. Memory/hot*.md`. `CLAUDE.md:10` preflight step 3 is `04. Memory/hot.md`. File exists (16 lines). No other `hot*.md`. |
| 22 | CORRECTED | `03. EA Developer/README.md:7-8` lists exactly one **living host** `EA_SonicR_PVSRA` — that is policy, and it matches `GOAL.md:29`. Harness count is not 85: status lists **87** compile-capable `EA_*` after the 9 warnings (96−9). 2026-08-13 audits that said 107 are stale. |
| 23 | CONFIRMED | `source_of_truth.json:486-490` backup root `G:\Drive của tôi\META TRADING\Advisors`, mode `optional`. `validate_source_of_truth.py:153-161` warns and `continue`s when that root is missing unless `--strict-backups`. Counts: 10 `backup-only` + 5 `unavailable-unresolved` = 15 unchecked. `G:\` does not exist. |
| 24 | CORRECTED | `requirements.txt` is 275 pinned lines including `altair==6.0.0`, `bottle==0.13.4`, `chromadb==1.1.1`, `pyinstaller==6.19.0`. `alpha.ps1` calls bare `python` at 25 sites (`:2440` through `:2996`). `alpha.ps1 validate` (`:2986-3000`) requires `numpy`, `pandas`, `matplotlib`; `vectorbt` optional. Owner’s “MetaTrader5 absent” is wrong: freeze line `requirements.txt:120` is `metatrader5==5.0.5509`. It is still drowned in unrelated pins. `mt5_connector.py:29` and `trade_chart_capture.py:44` import it. Default analyze/monte/wfa/robust/cpcv/param/impact/delivery/fast-kill scripts are stdlib + local modules (`quant_analyzer.py:13` “Minimal dependencies (standard library only)”). |

---

## 2. Pre-flight safety step

There is no `.git`, no reflog, no recycle-bin contract. `00. Old File/` (the historical graveyard) is also absent. Every archive/delete is a real filesystem move.

**Do this first, in this order, before any archive or edit. This is a recommendation, not a menu.**

1. **Full-tree zip on D:**  
   `Compress-Archive` is too weak for the portable MT5 tree (path length + 559 files under `runtime/`). Use:
   ```powershell
   New-Item -ItemType Directory -Force -Path "D:\Meta 5\backups" | Out-Null
   tar.exe -a -c -f "D:\Meta 5\backups\Trading-EA-MT5-20260831-pre-cleanup.zip" -C "D:\Meta 5" "Trading-EA-MT5"
   ```
   Confirm the zip is non-empty and contains `01. GOAL\GOAL.md`, `03. EA Developer\EA_SonicR_PVSRA\EA_SonicR_PVSRA.mq5`, and `02. AlphaFactory\alpha.ps1`. Keep the zip until the last phase’s verification command has passed.

2. **`git init` + one initial commit, immediately after the zip, before any move.**  
   Reason: the zip is disaster recovery; git is the reviewable diff and the one-command rollback for every later phase. Owner has not asked to push. There is no remote. Do not `git push`. Do not set a GitHub origin.

   Before `git add`, un-ignore the preflight cache so the initial commit actually contains `hot.md`:
   ```gitignore
   04. Memory/hot*.md
   !04. Memory/hot.md
   ```
   Then:
   ```powershell
   git init
   git add -A
   git add -f -- "04. Memory/hot.md"
   git status
   git commit -m "baseline: workspace as of 2026-08-31 before cleanup"
   git rev-parse HEAD
   git status --porcelain   # must be empty except alpha.local.ps1 / runtime (already ignored)
   ```
   Respect existing `.gitignore` for `02. AlphaFactory/runtime/`, `runs/`, `*.ex5`, parquet. Do **not** force-add the portable terminal; the zip covers that.

3. Recreate the historical graveyard name, nothing else:
   `00. Old File/EA_Archive/` and `00. Old File/docs_archive/`.  
   Do not invent `00. Graveyard/`. `.gitignore:58` already ignores `00. Old File/`. After git init, a move into that folder is a tracked **deletion** from `03. EA Developer/` (recoverable via `git checkout`) plus a local copy in the gitignored graveyard (recoverable via the zip).

Do not start Phase 1 until both the zip path and the baseline commit SHA exist.

---

## 3. Path migration

### 3.1 Machine-independence rule (code/config, not a new markdown)

This must not rot on the next folder move.

1. **Repo root** is the directory that contains `AGENTS.md`, `02. AlphaFactory/`, and `03. EA Developer/`. PowerShell already has `$AdvisorsRoot = Split-Path -Parent $PSScriptRoot` in `alpha.ps1:91`. Python tools must walk parents from `__file__` looking for those three markers. Optional env `ALPHAFACTORY_REPO_ROOT` is allowed only if it contains the same three markers.
2. **Factory MT5 target** comes only from gitignored `alpha.local.ps1`, generated by `tools/init_machine_paths.ps1`. InstallRoot = DataRoot = `Join-Path $PSScriptRoot "runtime\mt5-portable-mqdemo"` (or `mt5-portable-fivepercent` when Owner retargets). Always `/portable`. Never Program Files, never `%APPDATA%\MetaQuotes\Terminal\<32-hex>`, never `D:\Meta 5` (Owner GUI root), never leftover `runtime\mt5-portable`.
3. **Python `mt5.initialize()`** must pass `path=` to that factory `terminal64.exe`. Bare `mt5.initialize()` attaches to the running Owner GUI — that is a bug, not a fallback. Add one helper `02. AlphaFactory/tools/factory_paths.py` (`find_repo_root`, `load_alpha_local` parse-don’t-execute, `factory_mt5_terminal`, `mt5_initialize_kwargs`). No `MT5_TERMINAL` env that can point anywhere.
4. **Tests** use synthetic fixtures (`D:\af-runtime\mt5-portable-mqdemo`, `C:\Users\fixture\...`, Program Files as a **negative** sentinel). Do not paste `toila` or `B68D05E1...` into tests.
5. **Historical logs / JSONL / STRATEGY_LOG / redteam reports** are frozen evidence. Do not rewrite their paths into this machine’s locators.
6. **`source_of_truth.json` `02. EA/...` rows** stay as `unavailable-unresolved` historical index. They are not a folder-prefix typo for the live shelf.

Tighten `Assert-Mt5FactoryTargetIsolate` so `D:\Meta 5` cannot be pinned as InstallRoot even though it is not Program Files.

Kill `Resolve-Mt5InstallRoot` / `Resolve-Mt5DataRoot` auto-detect in `alpha.ps1:109-155`. Missing `alpha.local.ps1` must throw and point at `init_machine_paths.ps1`.

### 3.2 Exact edits — live tools (config-driven)

Do **not** replace Program Files / dead GUID with `B68D05E1...` or `D:\Meta 5\terminal64.exe`.

| File | Line | Old | New | Mode |
|---|---|---|---|---|
| `02. AlphaFactory/alpha.local.ps1.example` | 20 | `$MT5InstallRoot = "D:\Meta 5\Trading-EA-MT5\02. AlphaFactory\runtime\mt5-portable-mqdemo"` | `$MT5InstallRoot = Join-Path $PSScriptRoot "runtime\mt5-portable-mqdemo"` | config |
| `02. AlphaFactory/alpha.local.ps1.example` | 29 (comment) | `$MT5InstallRoot = "D:\Meta 5\Trading-EA-MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent"` | `$MT5InstallRoot = Join-Path $PSScriptRoot "runtime\mt5-portable-fivepercent"` | config |
| `02. AlphaFactory/alpha.local.ps1.example` | 10-12, 31-36 | deny-list is only Program Files + AppData hex | also deny `D:\Meta 5` (Owner GUI) and GUID `D0E8209F...` | comment |
| `02. AlphaFactory/alpha.ps1` | 109-119 | `Resolve-Mt5InstallRoot` candidates Program Files | delete function; missing local config throws | config |
| `02. AlphaFactory/alpha.ps1` | 122-144 | `Resolve-Mt5DataRoot` scans AppData Terminal GUIDs | delete; DataRoot only from alpha.local | config |
| `02. AlphaFactory/tools/init_machine_paths.ps1` | 51 | writes absolute `$portable` | write `Join-Path $PSScriptRoot "runtime\mt5-portable-mqdemo"` form; regen `alpha.local.ps1 -Force` | config |
| `02. AlphaFactory/tools/impact_pressure_probe.py` | 623 | `default=r"C:\Program Files\MetaTrader 5\terminal64.exe"` | `default=str(factory_mt5_terminal())` (required factory path) | config |
| `02. AlphaFactory/tools/drat_onnx_ict_probe.py` | 500 | same default | same | config |
| `02. AlphaFactory/tools/his_offline_gatecount_eurusd_m15.py` | 309 | `terminal = r"C:\Program Files\MetaTrader 5\terminal64.exe"` | `terminal = str(factory_mt5_terminal())` | config |
| `02. AlphaFactory/tools/mt5_uia_backtest_probe.ps1` | 95 | `$terminalExe = "C:\Program Files\MetaTrader 5\terminal64.exe"` | dot-source alpha.local; `Join-Path $MT5InstallRoot "terminal64.exe"`; add `/portable`; **stop** force-killing every `terminal64` (`:96-99`) | config |
| `02. AlphaFactory/analysis/mt5_connector.py` | 72 area | `mt5.initialize()` with no path | `mt5.initialize(**mt5_initialize_kwargs())` | config |
| `02. AlphaFactory/tools/vector_memory.py` | 91,96-99,125-126 | `'02. EA Developer/...'` | `'03. EA Developer/...'` | hardcode-fix (folder rename, not machine path) |
| `02. AlphaFactory/tools/vector_memory.py` | 23 | `ROOT / 'docs' / 'ai' / 'source_of_truth.json'` | `ROOT / '04. Memory' / 'source_of_truth.json'` | hardcode-fix |
| `02. AlphaFactory/tools/research/empirical_probe_runner.py` | 40-42 | `C:\Users\ADMIN\.gemini\antigravity\brain\...` | if the supplied plan is absent, skip/fail-closed on that hash; do not keep `.gemini` | config |
| `02. AlphaFactory/skills/perplexity-search/SKILL.md` | 23 | ADMIN `.openclaw\...search.py` | delete the absolute command; keep “use native web_search” (skill already DEPRECATED-SOFT) | hardcode-fix |
| `05. Playbook/WORKFLOW.md` | 184 | `./02. AlphaFactory/alpha.ps1 status` | `& ".\02. AlphaFactory\alpha.ps1" status` | hardcode-fix |
| `05. Playbook/WORKFLOW.md` | 185 | `./02. AlphaFactory/alpha.ps1 compile "<EA>"` | `& ".\02. AlphaFactory\alpha.ps1" compile "<EA>"` | hardcode-fix |
| `05. Playbook/WORKFLOW.md` | 186 | `./02. AlphaFactory/alpha.ps1 backtest ...` | `& ".\02. AlphaFactory\alpha.ps1" backtest "<EA>" -Symbol <SYMBOL> -Period <TF> -HypothesisId <ID>` | hardcode-fix |
| `05. Playbook/WORKFLOW.md` | 187 | `./02. AlphaFactory/alpha.ps1 analyze ...` | `& ".\02. AlphaFactory\alpha.ps1" analyze -Report "<REPORT_PATH>"` | hardcode-fix |
| `03. EA Developer/README.md` | 3 | `` `./02. AlphaFactory/alpha.ps1 list` `` | `` `& ".\02. AlphaFactory\alpha.ps1" list` `` | hardcode-fix |
| `03. EA Developer/EA_SonicR_PVSRA/README.md` | 45 | `-File .\02. AlphaFactory\alpha.ps1 compile EA_SonicR_PVSRA` | `-File ".\02. AlphaFactory\alpha.ps1" compile EA_SonicR_PVSRA` | hardcode-fix |

Any other `mt5.initialize()` under `02. AlphaFactory/tools/` and `analysis/` that omits `path=` is the same class as row `mt5_connector.py`: switch to `mt5_initialize_kwargs()`. Do this in the Python phase, not by pasting `D:\Meta 5\...` into fifty files.

### 3.3 Exact edits — tests (synthetic; do not use this machine’s real GUI/clone)

| File | Line | Old | New | Mode |
|---|---|---|---|---|
| `02. AlphaFactory/tests/test_setup_fivepercent_market_data.py` | 67 | `r"D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent"` | repo-relative via `Path(__file__).resolve().parents[1] / "runtime" / "mt5-portable-fivepercent"` (this is a reject-broker test; path only needs to be D:-shaped portable, not a live attach) | config |
| `02. AlphaFactory/tests/test_mt5_portable_storage.py` | 165-169 | Program Files + `D0E8209F...` + `D:\Trading EA MT5\...runtime` as **reject** fixture | keep Program Files as the forbidden sentinel; replace ADMIN/GUID/old-root with `C:\Users\fixture\AppData\Roaming\MetaQuotes\Terminal\0123456789ABCDEF0123456789ABCDEF` and `D:\af-runtime` | synthetic |
| `02. AlphaFactory/tests/test_mt5_portable_storage.py` | 185-189 | `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-mqdemo` as **accept** fixture | `D:\af-runtime\mt5-portable-mqdemo` (shape check, not Test-Path on this machine’s tree) | synthetic |
| `02. AlphaFactory/tests/test_mt5_portable_storage.py` | 198-242 | same old-root + liveupdate GUID `36E211F7...` | `D:\af-runtime\...` + fixture GUID `0123456789ABCDEF0123456789ABCDEF` | synthetic |
| `02. AlphaFactory/tests/test_session_trader_collector.py` | 44,131 | `C:\Program Files\MetaTrader 5` as dummy terminal_info path | `D:\af-runtime\mt5-portable-mqdemo` **or** keep Program Files if the test is fingerprinting a GUI-shaped path — if the assert is only “a path string exists”, prefer the portable fixture and update the fingerprint | synthetic |

Add one negative test: `Assert-Mt5FactoryTargetIsolate` rejects `D:\Meta 5` and rejects DataRoot `...\B68D05E1E7631B51201DCA32FCF5F4A6`.

### 3.4 Do not “migrate” — archive or freeze

| File | Why not a new hardcode |
|---|---|
| `02. AlphaFactory/analysis/cobra_tail_harvester.py` | One-off for `EA_Cobra` runs that are gone. ARCHIVE with docs, do not point at B68D or factory portable. |
| `02. AlphaFactory/analysis/factor_dsr_analysis.py` | Same. ARCHIVE. |
| `02. AlphaFactory/analysis/eurjpy_usdjpy_leadlag_m5.json` | Frozen output. Leave bytes. |
| `STRATEGY_LOG.md` ADMIN/GUID/`02. EA Developer` lines | Diary. Leave bytes. |
| `docs/**` ADMIN/GUID/`02. EA Developer` | Whole tree is archived in §4. |
| `source_of_truth.json:383,390` `02. EA/...` | Historical unavailable index. Leave. |
| `04. Memory/research/20260726_REDTEAM_FULL_REPO_REVIEW.md` | Forensic report. Leave. |
| `mt5_storage_contract.ps1:183-187` Program Files list | Denylist. Leave as denylist. |

### 3.5 `.gitattributes`

Delete lines 2-5 (dead `EA_SonicR/research` and `EA_VolmanCausalGrammar` rules; line 1 is a comment). Keep the freeze glob at line 6, tightened to the file that exists:

```
04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_EXECUTION_FREEZE_*.json text eol=lf
```

---

## 4. Deletion / archive plan

Graveyard name: **recreate `00. Old File/`** (already gitignored, already named by GOAL / CLAUDE / EA README / SoT). Do not invent a new folder name.

**No DELETE of unique evidence before the §2 zip + git baseline.** After that, DELETE is allowed only for empty dirs and generated noise.

### DELETE (after backup)

| Item | Justification |
|---|---|
| `05. Playbook/Strategy/` (empty dir) | Zero files. |
| `EA_H1PrevDayBreak.ex5` / `.log` next to source | Gitignored binary noise; not shelf proof. |

### ARCHIVE to `00. Old File/`

| Item | Dest | Justification |
|---|---|---|
| The 9 README-only EA packages listed in finding 1 | `00. Old File/EA_Archive/<name>/` | They are the **only** `Get-EAs` warning sources. Phase 1 cannot pass while they sit on the shelf. Do not dummy-`.mq5`. Do not add empty `research/` to silence the warn. |
| Entire `docs/` tree (5 files) | `00. Old File/docs_archive/` | March–April 2026 layer, outside SoT, contradicts GOAL (ITSM deployable, 4-EA portfolio that is 0/7 on disk). Archiving beats writing a disclaimer. |
| `02. AlphaFactory/analysis/cobra_tail_harvester.py` | `00. Old File/alpha_archive/` | Dead GUID + missing `EA_Cobra`. |
| `02. AlphaFactory/analysis/factor_dsr_analysis.py` | `00. Old File/alpha_archive/` | Same. |
| `02. AlphaFactory/XAUUSD_RESEARCH_REPORT.md` | `00. Old File/alpha_archive/` | 2026-03 Phoenix report, not living truth. |
| `03. EA Developer/EA_SonicR/` (classic) | `00. Old File/EA_Archive/EA_SonicR/` | `GOAL.md:29-30` forbids compiling classic SonicR. SoT already calls it archive-only. It currently sits on the live shelf with a valid `.mq5`, so Get-EAs lists it. |

### KEEP-AND-FIX

| Item | Justification |
|---|---|
| `03. EA Developer/EA_SonicR_PVSRA/` | GOAL host. Fix README `:38` (drop missing `SNR_INVARIANTS.md`) and `:45` (quote the `-File` path). |
| 6 non-`EA_*` indicators | Indicators with iCustom contracts, including GBB used by `EA_GBB_TrendPullback`. Do not rename to `EA_*`. Leave on shelf (Get-EAs already ignores them). Optional later: `03. EA Developer/_Indicators/` — not Phase 1. |
| `_Shared/` | Shared kernel, not an EA package. |
| `CANDIDATE_REGISTRY.jsonl` | Append-only evidence. Do not delete the 23 ghost rows. Do not rewrite 166 missing preregs. |
| `STRATEGY_LOG.md` | SoT-authoritative experiment diary. Stale vs GOAL; do not rewrite paths; do not archive the whole log. |
| `04. Memory/research/` (91 md + PTR campaign + this plan) | Historical evidence. |
| `02. AlphaFactory/runtime/mt5-portable-mqdemo` | Factory isolate. Already gitignored. |
| `alpha.local.ps1` | Machine pin. Regen after example becomes relative. |
| `AGENTS.md`, `GOAL.md`, `WORKFLOW.md`, EA README, SoT, hot.md, decision_framework | Doctrine reconciliation in §5. |
| `.gitignore` hot.md exception | Finding 21. |
| `.gitattributes` | Finding 13. |
| `CONTRIBUTING.md:37` | Drop `SECURITY.md` pointer; one inline sentence on credential exposure. Do not create `SECURITY.md`. |
| `requirements.txt` | Replace freeze; see §6. |
| `vector_memory.py` prefix | Finding 12 live indexer. |

### RESOLVE-AMBIGUITY-WITH-OWNER (do not block Phase 1)

| Item | Why Owner, not agent |
|---|---|
| Mass-park of the other **86** compile-capable `EA_*` packages (everything except host after classic SonicR is archived) | README and GOAL say one living host. Status currently lists 87 names and drowns that. Moving ~86 trees is the real slim-down, but it is a large reversible-only-via-git operation and some packages are the raw material for “family mới” (`hot.md:15`). Default in this plan: **do it in Phase 5 after git**, as one commit, unless Owner stops it. |
| Restore five playbook files from `G:\Drive của tôi\META TRADING\Advisors` | G: is offline. Slim-down says do not restore. WORKFLOW already absorbed the operating contract. |
| Recreate `.cursor/agents/` seven markdown agents | AGENTS.md names them; folder is absent. Slim = stop claiming the folder, do not write seven new agent docs. |
| Recreate `.codex/operator/STATUS.md` | Gitignored evidence, gone. Demote SoT rows. |
| Recreate `INDEX.md` | SoT calls it authoritative. Slim = demote SoT, do not write a new map. |
| Append registry rows for H4AT / IBRK / I1PB | Host source exists; run artifacts do not. Filling the ledger without a hash-bound run is a research-integrity decision, not cleanup. |

**23 ghost registry EAs:** KEEP the rows. They document killed/parked names. Do not recreate empty folders to make the count pretty.

**25 READMEs citing missing `research/`:** for the 9 empty packages, the README is archived with the package. For living/parked packages that still have `.mq5`, strip the dead `research/` sentence in the same commit that archives docs — do not recreate empty `research/` dirs (that would also change Get-EAs behaviour for any future README-only leftover).

---

## 5. Doctrine reconciliation

Authority used: Owner request (this job) → `GOAL.md` → verified disk. Cache (`hot.md`) never wins a number.

| Contradiction | Winner | Why | Concrete edit |
|---|---|---|---|
| BTCUSD in AGENTS vs 8 XAU+FX in GOAL | **GOAL.md:21-22** | `AGENTS.md:13` puts GOAL above AGENTS body text. The parenthetical is a stale Owner-memory. | `AGENTS.md:58` change `(Owner đã mở \`BTCUSD\`)` → delete the parenthesis. Line becomes `Active universe: theo \`01. GOAL/GOAL.md\`.` Do not add BTCUSD to GOAL. |
| PF 1.4 vs 1.30 | **GOAL.md:12,36 + WORKFLOW.md:139 + unified_validation.py:62** | Numeric DONE is GOAL. `decision_framework.py` is a 2026-03-10 CLI orphan (`DECISION_FRAMEWORK.md:3`); `alpha.ps1` never calls it. | `decision_framework.py:39` `GATE_PF = 1.4` → `GATE_PF = 1.30`. `DECISION_FRAMEWORK.md:92` `>= 1.4` → `> 1.30 (GOAL)`. Banner at top of DECISION_FRAMEWORK.md: “Diagnostic CLI only; economic law is GOAL.md / unified_validation.py.” Do not resurrect `validation_gates.md`. Fix `source_of_truth.json:39` “numeric authority remains validation_gates.md” → “numeric authority is GOAL.md”. |
| Cadence 2–5/week vs N<200 ABANDON / 20 trades/month | **GOAL.md + AGENTS.md:59-60** | 2–5/week is Owner DONE, not a kill-gate. 20/month is already Soft. Hard N<200 auto-kills a short GOAL-compliant Fast-Kill. | `decision_framework.py:127-138`: N<200 becomes a **warning**, not `return ABANDON`. `DECISION_FRAMEWORK.md:40-48` and `:108` same. Keep 200 as a sample-size **warn**. Do not invent a 20/month hard floor. Live `unified_validation.py` cadence fallbacks stay mechanism-specific. |
| Five missing playbook files still `authoritative` in SoT | **WORKFLOW.md + GOAL.md + AGENTS.md** (files that exist) | Cannot delete what is gone. Restoring five doctrine files is anti-slim. `20260813_HOT_CACHE_ARCHIVE.md` already said the old playbooks were replaced. | In `source_of_truth.json`, set those five paths (and `INDEX.md`, `.codex/operator/STATUS.md`, `.codex/operator/EXPERIMENTS.jsonl`) to `unavailable-unresolved` with reason “absent in this checkout; living process is WORKFLOW.md / GOAL.md / AGENTS.md”. `WORKFLOW.md:190` `Survivor: ... tool_runbook.md` → `Survivor: validate-full / delivery — see \`alpha.ps1 help\`.` Empty `05. Playbook/Strategy/` deleted. |
| `hot.md` IBRK/I1PB/H4AT vs empty registry | **hot.md is cache** (`hot.md:5`, `AGENTS.md:14`) | PF figures in hot.md are routing hints, not ledger truth. Host source for H4AT/IBRK/I1PB exists; run artifacts do not. | `hot.md`: keep the three campaign lines but prefix `CACHE ONLY — not in CANDIDATE_REGISTRY, no runs/ artifact.` Do not append registry rows as part of cleanup. Next-action line stays “family mới”. |
| README “1 live EA” vs 87 Get-EAs | **GOAL host = 1; harness list = inventory** | Both can be true if README says so. | After Phase 1 (9 gone) rewrite `03. EA Developer/README.md` to: living host `EA_SonicR_PVSRA`; classic SonicR is archive-only; indicators are not Get-EAs; parked `EA_*` count = whatever remains on the shelf after Phase 5. |
| AGENTS `.cursor/agents/` | **AGENTS roles can stay; folder is not required** | Slim. | `AGENTS.md:89` “Sub-agent (\`.cursor/agents/\`):” → “Sub-agent roles (logical; on-disk catalog optional):”. |

Do not write replacement doctrine files.

---

## 6. Python decision

**Install Python. Do not mark the layer dormant.**

Compile/backtest can run from PowerShell + factory portable without Python. Everything Owner listed as currently dead — `analyze`, `validate`, `validate-full`, `monte`, `wfa`, `robust`, `param`, `cpcv`, `impact`, `mt5data`, `delivery`, `fast-kill`, plus 58 tests — calls bare `python`. `alpha.ps1 validate` (`:2986-3000`) is an explicit env gate. Dormant-Python would freeze the research loop at “EX5 exists”. That contradicts GOAL’s KPI (time to an economic baseline, then validation).

**Version:** CPython **3.12 x64** from python.org (not the Store stub at `C:\Users\toila\AppData\Local\Microsoft\WindowsApps\python.exe`). Disable the App execution aliases for `python.exe` / `python3.exe`. Confirm:

```powershell
where.exe python
python --version          # must print Python 3.12.x, not the Store banner
python -c "import sys; print(sys.executable)"
```

3.12 is the conservative wheel target for `MetaTrader5`. Do not install 3.13+ until that package is verified.

**Replace `requirements.txt` (275-pin freeze) with this actual import set:**

```
# AlphaFactory — packages actually imported by alpha.ps1 verbs and tests.
# Not a pip freeze. Do not add chromadb/altair/bottle/pyinstaller.

numpy>=1.26,<3
pandas>=2.2,<3
matplotlib>=3.8,<4
pytest>=8,<10
pytest-timeout>=2.3,<3
MetaTrader5>=5.0.45
```

Optional extra, not in the default file (only `scan`):

```
python -m pip install vectorbt
```

**Why this list, not 275 and not empty:**

| Package | Who imports it |
|---|---|
| *(stdlib only)* | `quant_analyzer.py`, `enhanced_analyzer.py` (charts optional), `monte_carlo.py`, `walk_forward.py`, `robustness_suite.py`, `param_optimizer.py`, `purged_cpcv.py`, `dynamic_cost_model.py`, `unified_validation.py`, `datalog_analyzer.py`, `tca_summary.py`, `strategy_logger.py`, `audit_mql5_nonrepaint.py`, delivery/fast-kill validators |
| `numpy`, `pandas`, `matplotlib` | `alpha.ps1 validate` (`:2986`); `tests/test_setup_fivepercent_market_data.py:8-10`; charts in enhanced_analyzer / trade_chart_capture |
| `MetaTrader5` | `mt5_connector.py:29` (`mt5data`), `trade_chart_capture.py:44` (fail-open), probes. Already in the freeze as `metatrader5==5.0.5509` (`requirements.txt:120`); keep it, drop the other 274 pins. |
| `pytest`, `pytest-timeout` | 58 tests; freeze already had `pytest==9.0.2` |
| `vectorbt` | `quick_scan.py:24` only; `alpha.ps1 validate` already treats it as optional |

Do not install chromadb, altair, bottle, pyinstaller, customtkinter, yfinance, plotly (dashboard.py is not an `alpha.ps1` verb).

Verification after install:

```powershell
python -m pip install -r ".\02. AlphaFactory\requirements.txt"
& ".\02. AlphaFactory\alpha.ps1" validate
python -m pytest -q ".\02. AlphaFactory\tests\test_mt5_portable_storage.py" ".\02. AlphaFactory\tests\test_setup_fivepercent_market_data.py"
```

---

## 7. Execution order

Ranked by impact per effort. Each phase ends with a command that must pass before the next phase starts. **Phase 1 must end with `alpha.ps1 status` emitting zero warnings.**

### Phase 0 — irreversibility off  (do first)

Zip + gitignore hot.md exception + `git init` + baseline commit, as specified in §2.

Verify:

```powershell
Test-Path "D:\Meta 5\backups\Trading-EA-MT5-20260831-pre-cleanup.zip"
git -C "D:\Meta 5\Trading-EA-MT5" rev-parse HEAD
git -C "D:\Meta 5\Trading-EA-MT5" cat-file -e HEAD:"04. Memory/hot.md"
```

### Phase 1 — zero `Get-EAs` warnings

Move the 9 README-only packages to `00. Old File/EA_Archive/<name>/`. Do not add dummy mq5 or empty `research/`.

Verify:

```powershell
& ".\02. AlphaFactory\alpha.ps1" status 2>&1 |
  Select-String -Pattern "WARNING: Ignoring invalid active EA package"
# must print nothing
```

Also confirm the 9 dirs are gone from `03. EA Developer\` and present under `00. Old File\EA_Archive\`.

### Phase 2 — factory pin cannot silently become Owner GUI

Relative `alpha.local.ps1.example` + `init_machine_paths.ps1`; delete Program Files/AppData auto-detect in `alpha.ps1`; tighten `Assert-Mt5FactoryTargetIsolate` to require under `runtime\mt5-portable-mqdemo|fivepercent` and to reject `D:\Meta 5`. Regen `alpha.local.ps1 -Force`.

Verify:

```powershell
& ".\02. AlphaFactory\alpha.ps1" status
# Config source: alpha.local.ps1
# Portable: True
# Install/Data: ...\runtime\mt5-portable-mqdemo
# still zero WARNING: Ignoring invalid
```

### Phase 3 — Python lives, requirements are real

Install 3.12, replace `requirements.txt`, run `alpha.ps1 validate`.

Verify: `alpha.ps1 validate` prints numpy/pandas/matplotlib OK; `python -c "import MetaTrader5"` works; Store stub is gone from `where.exe python`.

### Phase 4 — live path fixes (no new hardcodes)

Probes + `mt5_connector` + `vector_memory` + WORKFLOW/README quoted invocations + empirical_probe_runner fail-closed + perplexity SKILL absolute path removed + factory_paths.py + synthetic test fixtures. Archive cobra_tail / factor_dsr (do not retarget).

Verify:

```powershell
rg -n "D:\\Trading EA MT5|C:\\Users\\ADMIN|D0E8209F77C8CF37AD8BF550E51FF075|C:\\Program Files\\MetaTrader 5\\terminal64.exe" --glob "!04. Memory/research/**" --glob "!**/STRATEGY_LOG.md" --glob "!00. Old File/**"
# remaining hits must be: denylist comments, negative test sentinels, or this plan
```

Quoted workflow:

```powershell
# paste the four WORKFLOW examples; they must not throw "The term './02.' is not recognized"
```

### Phase 5 — shelf honesty (optional-but-recommended; one git commit)

Archive classic `EA_SonicR/` and, unless Owner stops the phase, every remaining non-host `EA_*` package to `00. Old File/EA_Archive/`. Keep host, `_Shared/`, six indicators. Rewrite EA README to match disk. Strip dead `research/` sentences from the host README.

Verify:

```powershell
& ".\02. AlphaFactory\alpha.ps1" list
# only EA_SonicR_PVSRA
& ".\02. AlphaFactory\alpha.ps1" status
# zero invalid-package warnings
```

If Owner rejects mass-park, skip the 86-package move; still archive classic `EA_SonicR/` (GOAL).

### Phase 6 — doctrine + SoT + hot.md + gitattributes + CONTRIBUTING

Edits in §5. Demote missing SoT entries. Do not restore playbooks, INDEX, or `.cursor/agents`.

Verify: `AGENTS.md` has no `BTCUSD`; `decision_framework.py` `GATE_PF == 1.30`; N<200 does not `return ABANDON`; `WORKFLOW.md:190` does not cite `tool_runbook.md`; SoT five playbook paths are not `authoritative`.

### Phase 7 — compile the actual host

```powershell
& ".\02. AlphaFactory\alpha.ps1" compile EA_SonicR_PVSRA
```

Verify: fresh MetaEditor log `0 errors, 0 warnings` and a new EX5 under the factory portable, not under `D:\Meta 5\`.

Do not open optimization, WFA, or a new family inside this cleanup job.

---

## 8. Risk register

| Risk | What breaks | Rollback |
|---|---|---|
| Move without §2 zip/git | 9 packages or `docs/` gone forever | Prevented by ordering. If someone skips it: only the zip can restore. |
| Mass-park Phase 5 of 86 EAs | Next-family source not on the shelf; Get-EAs looks empty except host | `git checkout <baseline> -- "03. EA Developer/<name>"` and/or copy back from `00. Old File/EA_Archive/` / zip |
| Retarget a probe at `B68D05E1...` or `D:\Meta 5\terminal64.exe` | Factory compiles against Owner GUI; mixed profiles; `alpha.local.ps1.example:10-16` violated | Reject the edit. Contract test in Phase 2 must fail that pin. |
| Bare `mt5.initialize()` left in tools | Python attaches to the running Owner GUI (PID 7712 today) | `factory_paths.mt5_initialize_kwargs`; grep `mt5.initialize(` |
| `test_mt5_portable_storage.py` rewritten to this machine’s real paths | Tests pass only here; next move fails; negative fixtures become positive | Keep Program Files / fixture GUID as sentinels |
| Rewrite STRATEGY_LOG / registry / frozen JSON | Hash-bound evidence mutated | Never in this plan. `git checkout` if it happens |
| `git add -A` force-adds `runtime/` | Multi-GB commit, possible secrets in portable logs | `.gitignore:48` already ignores `02. AlphaFactory/runtime/`. Check `git status` before commit |
| Store Python still on PATH after 3.12 install | `alpha.ps1` keeps calling the stub | Disable App execution aliases; `where.exe python` must not be `WindowsApps` |
| `requirements.txt` trimmed too far | A research tool (`dashboard.py` plotly, chromadb) fails | Install that package ad hoc; do not restore the 275 freeze |
| Fail-open SoT backup remains | 15 entries stay unaudited | Accepted. G: is offline. Do not block cleanup on Drive |
| `00. Old File/` gitignored | Graveyard copies are local-only | Initial git commit still has the pre-move bytes; zip has the full tree |
| Phase 1 dummy `research/` dirs | Warnings disappear, packages stay invalid, `list` still omits them | Forbidden. Archive instead |
| Owner GUI running during compile | Accidental attach / file locks | Phase 7 uses factory `/portable` only; do not kill Owner `terminal64` (`alpha.ps1` already refuses a blind kill) |

---

## Ranking (impact / effort)

1. Phase 0 zip+git — unlocks every later delete.
2. Phase 1 archive 9 empty EAs — status becomes truthful.
3. Phase 3 Python 3.12 + tiny requirements — analyze/validate/monte/wfa live.
4. Phase 2+4 factory pin + quoted CLI — toolchain runs **here**, not on ADMIN’s GUID.
5. Phase 6 GOAL-wins doctrine — stop auto-failing / promoting on the wrong numbers.
6. Phase 5 shelf honesty — status shows the actual host.
7. Archive `docs/` and Cobra one-offs — removes false “deployable” language.
8. Do not: restore playbooks, write INDEX.md, recreate 7 Cursor agents, rewrite registry history, retarget factory at AppData.
