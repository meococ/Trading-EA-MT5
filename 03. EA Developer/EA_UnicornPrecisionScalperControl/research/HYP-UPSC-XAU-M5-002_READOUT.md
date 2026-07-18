# Model-0 readout — HYP-UPSC-XAU-M5-002

## Verdict

**KILL. Do not trade live and do not tune/rescue this hypothesis.**

The identity-bound FivePercent Model-0 run `20260716_140224` fails the frozen
profit-factor, cadence, cost, robustness, Monte Carlo and equity gates. The
validation summary remains `REVIEW`, not `PASS`, because observed execution
reconciliation is unavailable and the orchestration receipt was disrupted by
concurrent dirty-tree changes. Those operational blocks cannot improve the
already failed strategy gates and do not justify another trial.

## Bound identity and code gates

- Broker/server: `Five Percent Online Ltd` /
  `FivePercentOnline-Real (Build 6006)`.
- Data fingerprint:
  `AFFE0908BC398364AF86E1A84FD3E884AB1F96DBEC36E380B07219B1295B01F8`.
- Source SHA256:
  `EFE6062F20B1F90E3FE77D1484B00F4E3F694FBA9369897403F965EBCD5819EF`.
- Compile: 0 errors; static non-repaint audit: `PASS` over the exact source
  plus seven terminal includes.
- Lifecycle: 138 completed positions / 276 deals; all initial risks reconcile
  after the pending/current/previous telemetry repair.

## Frozen gates versus result

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Completed positions | evidence | 138 | usable |
| Elapsed cadence | 2.0–5.0/week | 1.3343/week | FAIL |
| Full-cost PF x1.0 | >1.80 | 0.6884 | FAIL |
| Full-cost PF x1.5 | >=1.25 | 0.5740 | FAIL |
| Full-cost PF x2.0 | >=1.00 | 0.4806 | FAIL |
| Report max DD | <=5.50% | 4.5240% | PASS |
| Monte Carlo P95 DD | <=5.50% | 5.6541% | FAIL |
| Robustness pass rate | >=60% | 0% | FAIL |
| Equity audit | PASS | REJECT | FAIL |
| Overnight/weekend exposure | 0 / 0 | 0 / 0 | PASS |

The underlying tester report is already weak before the additional research
latency proxy: PF `0.9863`, net `-233.83 USD`, win rate `39.9%`, expectancy
`-1.69 USD/trade`. Adding the frozen research-only commission/latency proxy
reduces PF to `0.6884` and net expectancy to `-23.0358R` across the sample.

## Strategy analysis

- The four-closed-bar sweep implementation produces too few trades over 724
  elapsed days and no positive aggregate expectancy.
- Cost stress is monotonic and severe; this is not a marginal spread problem.
- Drawdown alone looks acceptable only because the strategy trades sparsely
  and has little positive edge. Tail simulation crosses the frozen DD limit.
- Session, weekday, hour and year breakdowns are diagnostic only. Disabling a
  weak slice after reading this report is forbidden post-hoc rescue.
- The independent event-anchored challenger was frozen before this outcome and
  must live or die under its own preregistration; it may not inherit tuned
  thresholds from this readout.

## Evidence

- Run: `02. AlphaFactory/runs/EA_UnicornPrecisionScalperControl/20260716_140224/`
- Report: `report.html`
- Manifest: `run_manifest.json`
- Non-repaint: `analysis/nonrepaint_audit.json`
- Cost: `analysis/verified_cost_artifact.json`
- Unified validation: `analysis/validation_summary.json`
- Robustness: `analysis/robustness_results.json`
- Monte Carlo: `analysis/monte_carlo_results.json`
- Equity: `analysis/equity_audit.json`

The cost artifact is explicitly research-only (`promotion_eligible=false`,
`fill_observed=false`). It is sufficient to falsify this candidate, never to
promote it.

