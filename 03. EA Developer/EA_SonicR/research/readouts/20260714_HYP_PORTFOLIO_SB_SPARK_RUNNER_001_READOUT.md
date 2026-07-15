# Readout — HYP-PORTFOLIO-SB-SPARK-RUNNER-001

Date: 2026-07-14  
State: `KILLED_AT_MODEL_0`  
Family budget: `portfolio_sb_spark_runner` **1/1 spent**

## Verdict

**KILL.** Live dual-runner Model 0 clears cadence but **fails research PF**
(tester-`current` PF **1.22** < GOAL **1.30**). Offline compose proxy (PF 1.339)
did **not** survive shared-equity co-execution. Do **not** densify SB / Spark /
Donchian / NYPM / Friday scrape.

| Item | Value |
|---|---|
| EA | `EA_SBSparkBook` |
| `run_id` | **`20260714_224302`** |
| Binding | USDJPY M15 2021.01.01–2025.12.31 · deposit **100000** · overrides empty · Model 0 |
| Receipt SHA | `E4F4B9ACD90CB960423355E4482161B3D286D6BD211348EE6F7399DF6D713D64` (verified) |
| Report SHA | `9B74830551991B68D80DB9B161EFBA2C44E3715F258BDF4CCB7E6C633C1200D3` |
| Lane | `terminal64=0` at launch; closeout threw empty `required_sidecars=['']` after report ready — metrics via `alpha.ps1 analyze` |

## Metrics vs GOAL

| Gate | Result | Note |
|---|---|---|
| PF > 1.30 (verified cost) | **FAIL** | Tester PF **1.219**; cost unverified |
| 2–5 / elapsed calendar week | **PASS** | **842** trades / **260.714** wk → **~3.23**/wk |
| Cost stress x1.5≥1.25 / x2≥1.00 | **FAIL** | A priori +$12: x1 **1.011** / x1.5 **0.922** / x2 **0.840** |
| Exposure / MC DD / train+holdout | Not run | Fail-closed after research PF miss |

| Metric | Value |
|---|---|
| Trades | 842 |
| PF | 1.219 |
| Net | +$10,716.31 |
| Expectancy | +$12.73/trade |
| Max DD | 2.09% |
| Win rate | 49.8% |

Offline proxy (pre-Model0): pooled PF **1.339** / ~**3.24**/wk / N≈845 — research
only. Live book ≈same N, **PF −0.12** vs proxy (shared equity / sleeve
interaction / SB module fidelity gap).

## Cost stress (diagnostic, not confirmed)

Artifact: `02. AlphaFactory/runs/EA_SBSparkBook/20260714_224302/analysis/cost_stress_base12.json`

| Scenario | PF | Net |
|---|---:|---:|
| base_report | 1.219 | +10716 |
| cost_x1 (+$12) | 1.011 | +612 |
| cost_x1.5 | 0.922 | −4440 |
| cost_x2 | 0.840 | −9492 |

## Banned (honored)

No SB management densify · no Donchian retune · no NYPM · no Friday scrape ·
no PF cherry-pick sleeves.

## Next

1. Family **spent** — do not re-run same hyp with knobs.
2. Best shelf unchanged: RR2 `194548` PF 1.378 / ~2.01 (a priori +$12 x1.5 FAIL).
3. Independent next hyp only after de-dup → probe → prereg (not portfolio rescue).
