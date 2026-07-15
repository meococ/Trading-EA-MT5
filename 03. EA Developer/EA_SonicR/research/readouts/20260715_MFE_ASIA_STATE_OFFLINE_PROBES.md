# Offline probes — MFE stall-cut + Asia→London state-machine

Date: 2026-07-15
Status: `OFFLINE_ALL_KILL` / `NO_MODEL0`
Authority: `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Baseline RR2 `194548`

```
{
  "metrics": {
    "n": 524,
    "pf": 1.3794,
    "net": 9851.14,
    "exp": 18.7999,
    "tpw": 2.0099
  },
  "haircut_flat12": {
    "x1": {
      "pf": 1.1205,
      "net": 3563.14,
      "exp": 6.7999
    },
    "x1_5": {
      "pf": 1.0134,
      "net": 419.14,
      "exp": 0.7999
    },
    "x2": {
      "pf": 0.9179,
      "net": -2724.86,
      "exp": -5.2001
    }
  }
}
```

## Results

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001` | 524 | 0.1561 | 2.0099 | **0.1069** | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001` | 276 | 1.2551 | 1.0586 | **1.1679** | **KILLED_AT_OFFLINE_PROBE** |

## Notes

- `HYP-RR2-EXIT-MFE-STALLCUT-M15PATH-001`: notes=['pf_fail', 'stress_fail', 'no_stress_lift_vs_baseline'] funnel=None reasons={'sl': 445, 'orig_timeout': 11, 'stallcut': 35, 'tp': 33}
- `HYP-USDJPY-H1-ASIA-PCTL-COIL-LONDON-BREAK-STATE-001`: notes=['cadence_fail'] funnel={'n_asia_days': 1299, 'n_coil_armed': 497, 'n_fire': 347, 'n_expire': 150, 'n_trades': 276, 'n_skip_dist': 1, 'n_skip_untradeable': 70, 'n_skip_atr': 0} reasons=None

Receipt SHA: `3BF1A9FA66F7CB883950842AFE8A779CDCF751C32A658EE3F4368F887BF51FBD`
Model 0: `WITHHELD`
Best shelf: `RR2_20260714_194548`

