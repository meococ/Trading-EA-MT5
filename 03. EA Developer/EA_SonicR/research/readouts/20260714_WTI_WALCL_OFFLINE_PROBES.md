# Offline probes — WTI ToT + WALCL QT gate

Date: 2026-07-14T16:47:26.170295Z  
Status: `OFFLINE_BOTH_KILL / NO_MODEL0`  
Receipt SHA: `AE7E16C246A69ADA7AEBE545A5413123ED9D942CEF0DFCA502BB1736EAC96FA3`

## Results

| ID | N | PF | tpw | x1.5 | Verdict | Notes |
|---|---:|---:|---:|---:|---|---|
| `HYP-USDCAD-H1-WTI-TOT-CONT-001` | 635 | 0.9494 | 2.4343 | 0.8906 | KILLED_AT_OFFLINE_PROBE | pf_fail,stress_fail |
| `HYP-RR2-WALCL-QT-ALLOW-GATE-001` | 318 | 1.2758 | 1.2191 | 0.9539 | KILLED_AT_OFFLINE_PROBE | stress_fail,no_stress_lift_vs_baseline |

Baseline RR2 (O2 ungated): N=524 PF=1.3794
x1.5=1.0134

## Funnel

### O1
```json
{
  "n_bias": 6948,
  "n_displace": 635,
  "n_trades": 635,
  "days_used": 635
}
```

### O2
```json
{
  "n_baseline": 524,
  "n_kept": 318,
  "n_skipped": 206,
  "n_no_walcl": 0,
  "keep_frac": 0.6069
}
```

## Model 0

WITHHELD — zero PROBE_SURVIVOR.

## Non-rescues

No WTI z densify · no WALCL threshold mine · no T10YIE twin · no MaxKZ/RR densify.
