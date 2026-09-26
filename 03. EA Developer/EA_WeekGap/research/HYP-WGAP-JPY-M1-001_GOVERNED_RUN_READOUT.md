# HYP-WGAP-JPY-M1-001 — Governed Model-0 Run Readout

**Run:** `02. AlphaFactory/runs/EA_WeekGap/20260919_183811` (control, Model 0, USDJPY M1,
verified_m1_asof 2010.01.04–2026.09.18, history quality 99%, coverage class VERIFIED_M1_START).
**Prereg:** `HYP-WGAP-JPY-M1-001_FROZEN_PREREG.md` sha256 `8A954096…0E1`.
**Registry:** row appended — state `killed`, verdict `KILLED_AT_MODEL_0`.

## Headline

- Tester: **427 trades, PF 1.58, net +$1,082.05, DD 2.58%, WR 56.0%** — all Monday, all Asia.
- Validation verdict: **REVIEW (6/14 gates)**.
- Cadence: **0.49 trades/week** — structural, declared in prereg; DONE impossible.

## Gate outcomes

| Gate | Result | Detail |
|---|---|---|
| mt5_real_ticks_model | PASS | Model 0 enforced |
| nonrepaint_audit | PASS | closed-bar + D0 proof clean |
| max_drawdown_pct | PASS | 2.58% ≤ 20 |
| monte_carlo_p95_drawdown | PASS | 2.17% ≤ 20 |
| robustness_pass_rate | PASS | |
| overnight_weekend_exposure | PASS | 0 overnight, 0 weekend crossings |
| cadence | **FAIL** | 0.49/wk vs 10–40 required — structural |
| profit_factor (recorded plane) | **FAIL** | repriced PF **1.13** > 1.30 fails |
| cost_stress_x1_5 | **FAIL** | 0.96 ≥ 1.25 fails |
| cost_stress_x2 | **FAIL** | 0.82 ≥ 1.0 fails |
| equity_audit | **FAIL** | REJECT: spike-dependent (top5% = 96% of profit), LONG_FLAT 4032d, R²=0.61 |
| runner_invocation_success | BLOCKED | slippage_summary WARN (no samples) |
| execution_reconciliation | BLOCKED | artifact unavailable |
| invocation_artifact_freshness | BLOCKED | failed_producer=execution |

## GATE C — probe↔governed divergence

- Signals: EA 429 vs probe 450 retained. Common Mondays 415; EA-only 14; probe-only 35.
- `gap_pips` on common dates: mean |dev| 1.48p, max 16.9p — inside the prereg-declared
  prev-close feed fragility (~1/8 weeks can classify differently cross-feed).
- Entry timing exact: all opens at :01; time-exit dominant at :02 (bars_held≥61),
  shorter holds = SL(20p) hits. Exit mix: TIME 90.2% / SL 9.8% (probe artifact).
- Per-trade |EA pips − probe ret|: median 2.4p, mean 4.3p, p90 9p — fill/spread noise.
- Portfolio convergence: **PF 1.58 (tester) vs 1.54 (probe)** — premise survives.

## MAE/MFE autopsy (probe artifact, 450 events)

- MAE p25/50/75: −9.3 / −3.7 / −0.9 p; MFE p25/50/75: 4.7 / 9.1 / 16.8 p.
- Winners n=263, MFE med 13.7p; losers n=187, MAE med −9.9p.
- **Median MFE-capture 0.19** — the fixed 61-bar time-stop leaves ~5.8p med
  unrealized on winners (value leakage is in the exit, not the premise).
- Classification: premise OK, execution OK, exit = frozen conservative time-stop;
  no post-observation tweak allowed under loop discipline.

## Verdict

Calibration purpose achieved: probe↔governed convergence verified on a real anomaly,
pipeline end-to-end exercised (registry→packet→receipt→run→gates→audit). As a GOAL
candidate the cell is killed — cadence is structurally incompatible (max ~1/wk),
recorded-plane repricing drops PF to 1.13, and both cost-stress tiers fail.
The anomaly remains a documented research cell, not a promotion candidate.
