# Structural rebuild offline probes V3

Generated: 2026-07-14T16:10:17.674435Z
Authority: Owner R&D continue; offline-first; GPT waived
Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`

De-dup: `20260714_STRUCTURAL_V3_DEDUP_CLEARANCE.md`

## Probe C — H1 displace + FVG continuation

- ID: `HYP-H1-DISPLACE-FVG-CONT-001`
- Funnel: {'n_displace': 923, 'n_fvg': 788, 'n_trades': 247}
- N=247 PF=1.0168 tpw=0.947 exp=4.07
- Cost x1.5 (+$12 base) PF=0.9447
- Kill notes: ['cadence_fail', 'stress_fail']
- **Verdict: `KILLED_AT_OFFLINE_PROBE`** · model0=WITHHELD_KILL_FAST

## Probe D — M15 NY-IB fail-fade

- ID: `HYP-M15-NYIB-FAIL-FADE-001`
- Funnel: {'n_ib_days': 1298, 'n_break': 1296, 'n_fail': 966, 'n_trades': 82}
- N=82 PF=1.1219 tpw=0.314 exp=44.35
- Cost x1.5 (+$12 base) PF=1.0700
- Kill notes: ['cadence_fail', 'stress_fail']
- **Verdict: `KILLED_AT_OFFLINE_PROBE`** · model0=WITHHELD_KILL_FAST

## Board

| Probe | Verdict | Model 0 |
|---|---|---|
| C FVG cont | `KILLED_AT_OFFLINE_PROBE` | `WITHHELD_KILL_FAST` |
| D NYIB fail-fade | `KILLED_AT_OFFLINE_PROBE` | `WITHHELD_KILL_FAST` |

Offline survivors: `[]`
Any Model 0 authorized: `False`

Receipt SHA: `7CF12094A2443284DD8BD65BF74854D48BC8B29E71866DD4B230ED738558F22A`

## Phase-0 / best shelf

Phase-0 compose still blocked. Best shelf RR2 `194548` unchanged.
No densify from these kills.
