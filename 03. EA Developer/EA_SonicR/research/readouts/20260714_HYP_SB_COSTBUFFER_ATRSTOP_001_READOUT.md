# Readout — HYP-SB-COSTBUFFER-ATRSTOP-001 Model 0

Date: 2026-07-14 ~19:52 ICT  
Status: `PARKED` / research bar miss / friction **worse** than MaxKZ2  
Parent: `HYP-SB-MAXKZ2-DENSITY-002` (`20260714_192304`)

## Run

| Role | run_id | Overrides | N | tpw | PF | Net | DD |
|---|---|---|---:|---:|---:|---:|---:|
| Control MaxKZ2 | `20260714_192304` | SL_ATR=1.50 default | 546 | 2.09 | **1.33** | +8123 | ~0.85% |
| Challenger ATR1.0 | `20260714_195028` | **InpSL_ATR=1.0** | 554 | **2.12** | **1.24** | +5647 | ~1.53% |

Elapsed weeks: 260.7143. Deposit 100000. USDJPY M15 2021-2025. Model 0.  
`UNVERIFIED_TESTER_DEFAULT`. Alpha `includes_sha256` flake; artifacts kept.

## Gate

| Check | Result |
|---|---|
| KILL | **PASS** (survive) |
| Research HIT | **FAIL** — PF 1.24 ≤ 1.30 → **PARK** |
| vs MaxKZ2 | PF↓ net↓ DD↑ — loses control |
| Cost x1.5 / x2 (base+$12) | PF **0.851** / **0.752** — worse than MaxKZ2 |

## Explicit non-rescues

Do not retune InpSL_ATR from this readout. Do not stack RR2. Do not densify.

## Next

ATR-stop friction path **closed**. Prefer independent rebuilds (not MaxKZ /
RR / SL spam).
