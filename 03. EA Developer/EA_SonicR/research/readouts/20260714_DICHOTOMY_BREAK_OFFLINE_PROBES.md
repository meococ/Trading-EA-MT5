# Dichotomy-break offline probes

Generated: 2026-07-14T16:27:01.782178+00:00
Mandate: break thick↔cadence; no sweep/ORB/IB/ATR%ile clones.
De-dup: `20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md`
Merge: `20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md`
Receipt SHA (json file): `7B0D607553DF8497B693DB562924B9C3B9018999132E013873D814F4EB798D90`

| ID | N | PF | tpw | cost×1.5 PF | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-RR2-EXIT-BE1R-M15PATH-001` | 524 | 0.1349 | 2.0099 | 0.0965 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-RR2-USJP-YIELD-ZGATE-001` | 371 | 1.3804 | 1.423 | 1.0041 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-BOOK-CORRCAP-RR2-SPARK-001` | 794 | 1.2995 | 3.0455 | 0.9985 | **KILLED_AT_OFFLINE_PROBE** |

Survivors: `[]`
Model 0 authorized: `False`

## Notes

- `HYP-RR2-EXIT-BE1R-M15PATH-001`: notes=['pf_fail', 'stress_fail', 'no_stress_lift_vs_baseline'] funnel=None
- `HYP-RR2-USJP-YIELD-ZGATE-001`: notes=['stress_fail', 'no_stress_lift_vs_baseline'] funnel={'n_base': 524, 'kept': 371, 'skipped': 153, 'missing_z': 0}
- `HYP-BOOK-CORRCAP-RR2-SPARK-001`: notes=['stress_fail', 'book_pf_below_best_sleeve'] funnel={'n_rr2': 524, 'n_spark': 325, 'accepted': 794, 'rejected_overlap': 55, 'mix': {'RR2': 524, 'SPARK': 270}}

Best shelf RR2 `194548` unchanged unless survivor. Phase-0 still BLOCKED. No densify.
