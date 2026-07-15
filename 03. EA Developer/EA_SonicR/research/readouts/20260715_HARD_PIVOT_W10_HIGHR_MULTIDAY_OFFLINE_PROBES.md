# Offline probes — HARD PIVOT W10 high-R / multi-day

Generated: 2026-07-15 ~17:12 ICT
Receipt SHA256: `4AB5CB4EB996B0930001CFFC0B359ECAC3CD5E4222D12F5F273B186DAA367704`
Freeze SHA256: `D676485150B7F91E3377BC3BDE7EC3944C23E96658023C1246366B3C8E1F52DE`
Status: `OFFLINE_ALL_KILL__NO_MODEL0`
QFSI: QFSI 007 parallel; cost freeze GAP (11 deals); login not headline

## High-R dual-setup + book
| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001` | 257 | 0.824 | 0.9858 | 0.7948 | 0.7808 | KILL |
| `HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001` | 335 | 0.9171 | 1.2849 | 0.8626 | 0.8367 | KILL |
| `HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001` | 586 | 0.8569 | 2.2477 | 0.8174 | 0.7984 | KILL |

High-R book caps: corr=0.0652 overlap=0.0565 caps_ok=False

## Optional thick-rare month-struct book ≠ W9
| Object | N | PF | tpw | PF@$12 | x1.5 | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001` | 77 | 0.9978 | 0.2953 | 0.9627 | 0.9458 | KILL |
| `HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001` | 116 | 0.8782 | 0.4449 | 0.8343 | 0.8134 | KILL |
| `HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001` | 193 | 0.9349 | 0.7403 | 0.895 | 0.8759 | KILL |

Month book caps: corr=0.1206 overlap=0.0405 caps_ok=True

## Fail notes
- `HYP-FX3-H4-WEEKLY-OPEN-BIAS-RETEST-MULTIDAY-001`: pf_fail, cadence_fail, pf12_fail, stress_fail
- `HYP-FX3-H4-D1-DISPLACE-MID-RECLAIM-MULTIDAY-001`: pf_fail, cadence_fail, pf12_fail, stress_fail
- `HYP-FX3-H4-MONTHLY-OPEN-FIRST-ACCEPT-CONT-001`: n_fail, pf_fail, cadence_fail, pf12_fail, stress_fail
- `HYP-FX3-H4-PRIOR-MONTH-HL-FAILBREAK-REV-001`: pf_fail, cadence_fail, pf12_fail, stress_fail
- `HYP-BOOK-HIGHR-MULTIDAY-DUAL-SETUP-APRIORI-001`: pf_fail, pf12_fail, stress_fail, caps_fail
- `HYP-BOOK-THICKRARE-MONTHSTRUCT-APRIORI-001`: pf_fail, cadence_fail, pf12_fail, stress_fail

Model 0 WITHHELD unless PROBE_SURVIVOR. No corpse densify.
