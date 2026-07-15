# Independent Rebuild Probe Matrix V1

Date: 2026-07-14  
Status: `CLOSED_EMPTY_SHELF_WAVE`  
Matrix SHA256: `E7D5B89F76C14C4FB96E136141E5133BA74EA17F96271E5A2A16BCBEEC153578`  
Closeout: `readouts/20260714_INDEPENDENT_REBUILD_EMPTY_SHELF_CLOSEOUT.md`

## Screen contract

- KILL: PF&lt;1.00 OR tpw∉[1,6] OR N&lt;80 OR x1.5_pf&lt;1.00
- PARK: survives kill but PF≤1.30 or tpw∉[2,5] OR x1.5_pf&lt;1.25
- Prefer HIT only with thick post-cost expectancy

## Results

| ID | Run | N | PF | tpw | x1.5 | Verdict |
|---|---|---:|---:|---:|---:|---|
| VWAP | `20260714_195418` | 1357 | 0.900 | 5.20 | 0.690 | KILL |
| AsianTail | `20260714_195640` | 1079 | 0.908 | 4.14 | 0.646 | KILL |
| H1-BOS PB | `20260714_195824` | 1626 | 1.073 | 6.24 | 0.816 | KILL |
| LondonNY ref | `20260709_074209` | 76 | 1.796 | 0.29 | 1.552 | friction PASS / cadence FAIL |

## Next lawful

PDH retest · H4 struct break · LNY-class thick cadence expand (new IDs only).
