# Cost-stress readout — survivor haircut wave (no Real)

Date: 2026-07-14 ~19:40 ICT  
Hypothesis probe: `HYP-COST-HAIRCUT-SURVIVOR-001` (offline; no Model 0)  
Method frozen a priori: subtract `base_cost_per_trade × mult` from each closed-trade
PnL **on top of** tester-embedded spread (`sonic_cost_stress.py`).  
SB-class base = **$12**/trade; Spark base = **$8**/trade.  
Label: `UNVERIFIED_TESTER_DEFAULT` / `report_only_cost_stress`. **Not confirmed.**

## Results

| Sleeve | Run | Base PF | x1.0 PF | x1.5 PF | x2.0 PF | Verdict vs GOAL stress |
|---|---|---:|---:|---:|---:|---|
| MaxKZ2 | `20260714_192304` | 1.334 | 1.057 | **0.942** | **0.840** | FAIL x1.5≥1.25 ∧ x2≥1.00 |
| SB A1 | `20260714_002505` | 1.344 | 1.063 | **0.947** | **0.843** | FAIL |
| Spark | `20260714_002821` / `002614` | 1.305 | 0.695 | **0.511** | **0.376** | FAIL (fragile) |

Artifacts:
- `preflight/20260714_COSTSTRESS_MAXKZ2_192304.json`
- `preflight/20260714_COSTSTRESS_SB_A1_002505.json`
- `preflight/20260714_COSTSTRESS_SPARK_002821.json`
- `preflight/20260714_COSTSTRESS_SPARK_002614.json`

## Interpretation

Under this a priori incremental haircut, **all research near-misses are FRAGILE**.
Tester PF>1.30 does **not** survive x1.5/x2 incremental cost. Distance to GOAL under
stressed cost is large — rebuild/discovery must target **higher expectancy per trade**
or lower trade count with same net, not densify spam. Magnitude of `$12/$8` is a
research proxy, not Real QFSI; Real reprice remains parallel hygiene when available.

## Compose note

MaxKZ2+Spark pooled PF 1.330 / ~3.34/wk (prior probe) inherits the same fragility —
do not code portfolio EA from FRAGILE sleeves. Phase0 contamination still blocks promote.

## Next R&D (no Owner login)

1. Independent Model 0 screens (AsianSweepReclaim, LondonORBAccept, EngulfTrend, EURUSD MaxKZ2 transfer).
2. Prefer mechanisms with larger avg win / fewer round-turns.
3. Optional milder haircut band only as sensitivity disclosure — not promotion path.
