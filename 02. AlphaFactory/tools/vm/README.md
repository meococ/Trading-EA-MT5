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
| `vm_data_inventory.ps1` | Wraps `vm_data_inventory.py`: attaches MetaTrader5 to the isolate, probes 12 symbols (first/last M1, one sample tick day per year, spec, on-disk bytes), writes CSV + JSON to `02. AlphaFactory/runtime/vm_inventory/` plus a gap note vs `02. AlphaFactory/lab`. |

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
