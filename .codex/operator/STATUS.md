# Generic EA Golden Path Status

- Authority: operational recovery ledger only; `04. Memory/hot.md` remains the
  canonical live-scope owner.
- Goal: make AlphaFactory's design-to-decision workflow generic across active
  EA packages, fail closed before MT5, and remove Sonic/archive/Git-mutation
  assumptions from the public path.
- Current state: implementation and focused offline verification complete.
- Delivered: workspace-wide append-only registry + validator; generic runner;
  per-package capability contract; generic lifecycle telemetry naming and
  matched-control comparator; active-shelf-only discovery; removed backup
  auto-commit/push action; structured registry acceptance gates; exact
  LifecycleTrades/RunMeta identity; templates and five-doc golden path.
- Evidence: PowerShell AST clean; Python compile clean; `alpha list/status`
  reports exactly `EA_FVGConfluence` and `EA_HybridICT_Sonic`; FVG dry-run exits
  0 and blocks before MT5 on probe/capability/task-packet gates; 22/22 focused
  tests pass; candidate registry passes.
- External blocker: source-of-truth validator remains RED only on the same 10
  absent `G:` backup-only files. JSON/Markdown parity has no new error.
- No trading/runtime actions: no MT5 backtest, live order, or run deletion.
  Owner authorized commit/push of this bounded golden-path slice on 2026-07-16.
- Next: accept Owner's EA brief through `05. Playbook/ea_golden_path.md`; freeze
  one legal hypothesis before code/run. Mount `G:` separately to close the
  external availability gate.
