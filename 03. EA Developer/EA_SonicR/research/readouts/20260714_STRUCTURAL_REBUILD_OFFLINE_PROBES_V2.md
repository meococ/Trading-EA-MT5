# Structural rebuild offline probes V2

Generated: 2026-07-14T16:08:53.066030+00:00
Authority: Owner R&D continue; offline-first; GPT waived
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

De-dup: `20260714_STOPRUN_ACCEPT_LNY_EVENT_DEDUP_CLEARANCE.md`

## Probe A — stop-run → multi-bar acceptance

- ID: `HYP-H1-PDLIQ-STOPRUN-ACCEPT-001`
- Symbol/TF: `USDJPY` / H1
- Funnel: {'n_stoprun': 1773, 'n_accept_geom': 390, 'n_trades': 164}
- N=164 PF=1.1115 tpw=0.629 exp=33.5436
- Cost x1.5 PF=1.0498 exp=15.5436
- Kill notes: ['cadence_fail', 'pf_fail', 'stress_fail']
- **Verdict: `KILLED_AT_OFFLINE_PROBE`** · model0=WITHHELD_KILL_FAST

## Probe B — LondonNY thick event redefinition

- ID: `HYP-LNY-RANGE-ACCEPT-M15-001`
- Symbol/TF: `USDJPY` / M15
- Funnel: {'n_expansion_days': 13, 'n_armed_bias': 11, 'n_trades': 4}
- N=4 PF=0.0 tpw=0.0153 exp=-151.705
- Cost x1.5 PF=0.0 exp=-169.705
- Kill notes: ['n_fail', 'cadence_fail', 'pf_fail', 'stress_fail']
- **Verdict: `KILLED_AT_OFFLINE_PROBE`** · model0=WITHHELD_KILL_FAST

## Board

| Probe | Verdict | Model 0 |
|---|---|---|
| A stop-run accept | `KILLED_AT_OFFLINE_PROBE` | `WITHHELD_KILL_FAST` |
| B LNY range-accept | `KILLED_AT_OFFLINE_PROBE` | `WITHHELD_KILL_FAST` |

Offline survivors: `[]`
Any Model 0 authorized: `False`

## Phase-0 compose

Not reopened. Still `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`.

## Best shelf

RR2 `20260714_194548` unchanged.
