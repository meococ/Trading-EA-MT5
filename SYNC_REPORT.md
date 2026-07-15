# SYNC_REPORT

Ticket: SYNC-002 - Lean local sync EA project from Google Drive backup
Generated: 2026-06-21 12:32:04 +07:00

## Step 1 - Clean old local clone
- Confirmed old workspace remote before deletion: origin https://github.com/meococ/EA-Development.git.
- Cleared D:\Trading EA MT5 only after resolved path matched exactly.
- Drive backup was not deleted, modified, committed, or pushed.

## Step 2 - Drive discovery
- Drive backup source: G:\Drive của tôi\META TRADING\Advisors
- Current checkout branch: shen/test-all-options-v1.
- Branches observed: main; shen/72h-nonstop-v1; shen/r1-ldn-window-v2; shen/r2-circuit-breaker-v5; shen/r3-addon-v1; shen/r6-late-ldn-regime-gate; shen/test-all-options-v1; worktree-agent branches; origin/main.
- Recommended base branch: shen/test-all-options-v1 because it is the checked-out working tree and contains the latest S42 validation/doc state in valid-ref history.
- EA source dir selected: 03. EA Developer.
- Best-looking EA from commit messages only: EA_ITSM (S42 validated: WFA 4/5, Robust 7/7, MC P95 16.1%). Keep EA_Cobra, EA_Gotobi, EA_LondonNY, and Phoenix context, but do not promote from commit text alone.
- git log --all --oneline --decorate -200 on Drive fails because DriveFS created broken desktop.ini refs under .git/refs. Raw failure and valid-ref fallback are preserved in .governance/MEMORY_git_history.md.

## Step 3 - Memory rescued
- Created .governance/MEMORY_git_history.md with branch listing, branch -vv, raw log --all failure, valid-ref log fallback, and shen branch one-line summaries.
- Copied AlphaFactory memory/docs: STRATEGY_LOG.md, strategy_index.json, runs.db, DECISION_FRAMEWORK.md, PHASE0_HARDENING_PLAN.md, XAUUSD_RESEARCH_REPORT.md.
- Requested docs not present in selected branch/root: SYSTEM_GUIDE, QUICK_START, GAPS_AND_LESSONS, root README under 02. AlphaFactory.

## Step 4 - Lean copy result
Copied:
- AGENTS.md
- README-SONIC R.md
- 03. EA Developer source only: .mq5/.mqh, preserving structure.
- 02. AlphaFactory: root keep files, memory docs, tools, templates, skills, analysis scripts/config only.
- docs excluding archive.
- 04. Project Control excluding generated/system junk.

EA source file counts:
- .mq5: 81 files
- .mqh: 30 files

Skipped with reason:
- 01. Indicator: no direct references to custom indicator filenames/basenames from active EA .mq5/.mqh source.
- 00. Old File, scratch, .playwright-mcp, worktrees, .git: explicit skip / old or tool state.
- ExpertMACD*, ExpertMAMA*, ExpertMAPSAR*: MetaQuotes sample EAs.
- AlphaTester: duplicate/heavy historical tester config output overlapping AlphaFactory runs/backtest history.
- 02. AlphaFactory/runs, archive, runtime, external: heavy history/runtime/output.
- 02. AlphaFactory/core, 02. AlphaFactory/data: missing in selected branch.
- 02. AlphaFactory/sensitivity_test.ps1, verify_report.py, check_volume.py: not present in selected branch; monte_carlo.py was found/copied from analysis/monte_carlo.py.

## Size summary
| Path | Files | MB |
|---|---:|---:|
| AGENTS.md | 1 | 0.013 |
| README-SONIC R.md | 1 | 0.031 |
| .governance | 1 | 0.01 |
| 02. AlphaFactory | 150 | 2.845 |
| 03. EA Developer | 111 | 1.835 |
| 04. Project Control | 27 | 2.741 |
| docs | 5 | 0.017 |
| .gitignore | 1 | 0.001 |
| TOTAL_EXCLUDING_GIT | 298 | 7.498 |

## Step 5 - MT5 local target configuration
- MT5 data target: C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075.
- Data root exists: True; MQL5\Experts exists: True.
- Executable resolved from origin.txt: C:\Program Files\MetaTrader 5\terminal64.exe.
- terminal64.exe exists: True; metaeditor64.exe exists: True.
- Updated 02. AlphaFactory/alpha.ps1 config lines:
- L51: $MT5InstallRoot = "C:\Program Files\MetaTrader 5"
- L52: $MT5DataRoot = "C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"
- L53: $MT5Mql5Root = Join-Path $MT5DataRoot "MQL5"
- L54: $MT5 = Join-Path $MT5InstallRoot "terminal64.exe"
- L55: $MetaEditor = Join-Path $MT5InstallRoot "metaeditor64.exe"
- L180: Start-Process -FilePath $MetaEditor -ArgumentList $compileArgs -Wait
- L205: $mql5Root = $MT5Mql5Root
- L225: $expertsRoot = Join-Path $mql5Root "Experts"
- L638: $mt5 = Join-Path $AlphaRoot "analysis\mt5_connector.py"
- No compile/backtest/live trading was run.
- Syntax/config smoke: alpha.ps1 status ran successfully and listed EAs; MT5 was STOPPED.

## Step 6 - Local git
- git init run in D:\Trading EA MT5.
- Remote after init: (none)
- No GitHub remote configured; no push performed.
- .gitignore added for secrets, AlphaFactory runs/output, MT5 binaries, and local agent/editor state.

## Acceptance checklist
- [x] Drive treated read-only; no delete/copy-back/commit/push on Drive.
- [!] Drive git status/diff verification did not complete on DriveFS: status -uno, diff, and ls-files -m timed out. Follow-up lock check found no .git/*.lock files; .git/index timestamp is 2026-06-05 20:24:19, not a new sync-time write.
- [x] KEEP-LIST core paths exist in D:.
- [x] SKIP-LIST heavy/sample paths not copied into D:.
- [x] .governance/MEMORY_git_history.md exists.
- [x] alpha.ps1 points at target MT5 data hash and valid local MT5 executable install.
- [x] D: has no GitHub remote.
