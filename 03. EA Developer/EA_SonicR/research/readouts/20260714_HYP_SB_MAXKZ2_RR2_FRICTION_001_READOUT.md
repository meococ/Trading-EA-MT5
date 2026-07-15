# Readout — HYP-SB-MAXKZ2-RR2-FRICTION-001 Model 0

Date: 2026-07-14 ~19:47 ICT  
Status: `PARK_HIT_RESEARCH_BAR_FAILS_GOAL_X15_STRESS` / **GOAL unmet**  
Parent: `HYP-SB-MAXKZ2-DENSITY-002` (`20260714_192304`)

## Run

| Role | run_id | Overrides | N | tpw | PF | Net | DD |
|---|---|---|---:|---:|---:|---:|---:|
| Control MaxKZ2 RR1.5 | `20260714_192304` | MaxKZ=2; RR defaults 1.5 | 546 | 2.09 | **1.33** | +8123 | ~0.85% |
| Challenger RR2.0 | `20260714_194221` | MaxKZ=2; **TP RR=2.0** | 524 | **2.01** | **1.38** | +9828 | ~0.96% |

Elapsed weeks: 260.7143. Deposit 100000. USDJPY M15 2021-2025. Model 0.  
Tester `current` — `UNVERIFIED_TESTER_DEFAULT`. Report SHA256
`49D142CF2B9531AD2F9C338277FD30B00EC74F420B23A7E288687443723397E3`.  
Alpha `includes_sha256` flake; artifacts kept. Machine JSON
`preflight/20260714_HYP_SB_MAXKZ2_RR2_FRICTION_001_MODEL0.json`
(SHA `211F6107D048F52ABEC8718B04C5B5F555E7FFD472EA3705E387A43FFCE007CE`).

## Gate vs prereg

| Check | Result |
|---|---|
| KILL | **PASS** |
| Research HIT (PF&gt;1.30 ∧ tpw∈[2,5]) | **HIT** (1.38 / 2.01) |
| vs MaxKZ2 | PF↑ net↑ N↓ |

## Cost-stress (two honest proxies — both FAIL GOAL)

### A) Dollar haircut + loss-side (iterate V3 / MODEL0 JSON)

| Scenario | RR2 | MaxKZ2 |
|---|---:|---:|
| PF @$2/trade | **1.330** | 1.282 |
| loss×1.5 | **0.919** | 0.889 |
| loss×2 | **0.689** | 0.667 |

GOAL needs x1.5≥1.25 / x2≥1.00 → **FAIL** (improved vs MaxKZ2, still dead).

### B) sonic_cost_stress base +$12/trade

Artifact SHA `6D4E2B8770B59039589D7820A3FD78179B099E03F476B8028923DADE2B0C8E75`

| Scenario | RR2 | MaxKZ2 |
|---|---:|---:|
| x1.5 (+$18) | **1.013** | 0.942 |
| x2 (+$24) | **0.917** | 0.840 |

Same conclusion: friction↑, GOAL stress still FAIL.

## Compose

RR2 + Spark capacity `193732`: PF **1.374** / **~3.26**/wk / +$19013  
(SHA `A27EB72A35AD095EA1E90D5FFAAD9FBDE38E6752BC93E8B61888FB674B2507EE`).

## Non-rescues / follow-on

- Do not retune RR to 2.5/3.0 from this readout.
- Secondary ATR-stop **executed** → `HYP-SB-COSTBUFFER-ATRSTOP-001`
  `20260714_195028` **PARK** PF 1.24 (see sibling readout).
- Prefer independent rebuilds next.

## Wave2 ceremony confirm (2026-07-14)

Authoritative Model 0 run for this closeout: `20260714_194548` (same metrics as `194221`: PF **1.378** / 524t / tpw~**2.01** / net **9828.35**).

`sonic_cost_stress.py` report-only `--base-cost-per-trade 12` on `194548`:
- x1.5 (+$18): PF **1.0126** FAIL gate >=1.25
- x2 (+$24): PF **0.9172** FAIL gate >=1.00
Artifact: `02. AlphaFactory/runs/EA_SilverBullet/20260714_194548/analysis/cost_stress_base12.json`

Verdict unchanged: **HIT research bar / FAIL GOAL stress / PARK / do not densify**.

## Wave2 cost-stress refresh (run `20260714_194548`)
- base12 report-only: x1.5 PF **1.013** FAIL gate >=1.25; x2 PF **0.917** FAIL gate >=1.00
- Findings: `pf_below_1_25_at_cost_x1_50`, `pf_below_1_00_at_cost_x2_00`
- Verdict unchanged: HIT research bar under tester; FAIL GOAL stress; parked; not densify
