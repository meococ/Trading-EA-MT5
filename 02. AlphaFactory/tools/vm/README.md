# tools/vm — VM operations toolkit

Session-start readiness, self-diagnosis, cleanup, and data inventory for the
AlphaFactory portable MT5 isolate on this Devin VM (plane `devin-vm-mqdemo`).

All scripts are PowerShell, support `-Json`, and exit 0 = PASS, 1 = WARN, 2 = FAIL.
They never print secret values.

## Scripts

| Script | Purpose |
|---|---|
| `vm_start.ps1` | Session boot: git fetch + ff-only, refresh PATH, authorize MetaQuotes-Demo (profile / env creds / WARN), then runs doctor and prints <=10 lines. Idempotent. |
| `vm_doctor.ps1` | Read-only checks: isolate + storage contract, demo auth state, `alpha.ps1 validate`, disk free (WARN < 10 GB), running MT5 processes (isolate vs foreign), git HEAD vs origin + dirty files, hooksPath, terminal build. |
| `vm_cleanup.ps1` | Dry-run by default (`-WhatIf`-style; pass `-Execute` to act). Delegates scoped file cleanup to `post_run_cleanup.ps1`, kills only MT5 processes whose exe path is inside the isolate, deletes temp cred files. |
| `vm_data_inventory.ps1` | Wraps `vm_data_inventory.py`: attaches MetaTrader5 to the isolate, probes 12 symbols (first/last M1 **of the locally-downloaded cache** — see method note, one sample tick day per year, spec, on-disk bytes), writes CSV + JSON to `02. AlphaFactory/runtime/vm_inventory/` plus a gap note vs `02. AlphaFactory/lab`. |
| `vm_history_probe.ps1` | Server-side depth probe: runs the Strategy Tester on a 1-week June window per (`-Symbols`, `-Years`) via `terminal64 /portable /config` and parses the agent/manager logs + `report.htm` (UTF-16). Fields: `history_sync_from/to` (terminal-synced M1 span), `history_quality` (report `% real ticks`; >0 = window tick-covered), `ticks_begin_from` (tick-store floor as extended by successive probes), `bars_in_test`, `no_real_ticks_flag`. Merges results into `runtime/vm_inventory/history_probe.{json,csv}` keyed on symbol+year. |

## Data-depth method note (MetaQuotes-Demo, 2026-09-26)

`copy_rates_from` only sees the history the terminal already downloaded — early
measurements of "~3 months M1" were that cache boundary, not server depth.
The Strategy Tester syncs history from the server, so floors below come from
`vm_history_probe.ps1` runs, not attach calls.

Measured floors (1-week June windows, Model=4, `ExpertMACD.ex5`):

| Symbol | M1 history floor | Real-tick coverage |
|---|---|---|
| EURUSD | ≥ 1989-01-03 | hq=100 at 2012/2015/2022/2024 windows; 0% at 2010 → floor in (2010-06, 2012-06] |
| XAUUSD | 2004-06-11 | hq=100 at 2019/2020/2024/2025; 0% at 2017 → floor in (2017-06, 2019-06] |
| AUDUSD | ≤ 1998-01-02 (1999 window synced from there) | 0% at 1999 |

Other 8 basket symbols were still mid first-sync when the sweep was aborted
(deadline order, not data verdict). `no_data_in_window` = report produced zero
bars for the probe week.

## Task packet template

```
ID:            VMOPS-XXXX
Goal:          <one sentence>
Lane/EA:       <lane or EA name>
Input:         <path> @ <SHA>
Work:          <what to do>
DoD:           <command(s) that must pass + key output>
Forbidden:     <explicit no-gos>
STOP points:   <conditions that halt and report>
Backup:        <fallback plan if primary fails>
```

## Report template

```
Result:    <one line>
Done:      <what was done>
Evidence:  <command + key output, run_id, SHA>
Verdict:   engineering: <pass/fail + tier> | economic: <separate, + tier>
Risks:     <risks / gaps>
Next:      <proposed next step>
```
