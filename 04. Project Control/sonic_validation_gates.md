# Sonic R Validation Gates

Updated: 2026-07-11

This file turns the Sonic R research doctrine into staged gates. It is not a
profit target shortcut. A candidate can move forward only when the required
artifacts exist and the result is broad enough to survive data-mining pressure.

## Stages

| Stage | Allowed evidence | Required artifacts | Decision power |
|---|---|---|---|
| `idea` | Trader thesis, source mapping, visual observation | Prereg draft, registry row | No backtest conclusion |
| `probe` | Offline closed-bar scanner, labels, snapshots | Probe output, label file, candidate registry update | Can refine thesis or kill |
| `screened` | Model 1 matched control/challenger | Report, run manifest, cost stress, split attribution | Can kill or park only |
| `challenger` | Model 0 matched control/challenger | `validate-full`, cost stress, non-repaint audit, sidecar audit | Can continue to full validation |
| `confirmed` | Full validation stack | Promotion-eligible optimization-aware WFA and robustness, preregistered aligned PBO/CSCV and White Reality Check/SPA, Monte Carlo, equity audit | Can enter portfolio review |
| `portfolio-sleeve` | Multi-lane portfolio test | Correlation/overlap, portfolio DD, combined cost stress | Research deployment review only |

## Stage Thresholds

### Probe

- Uses only closed-bar data.
- Has a `hypothesis_id`.
- Has locked chart-state labels if the hypothesis comes from visual chart reads.
- Has negative controls: sideway losses, impulse wins, high-MFE misses, high-MAE
  false positives, adjacent sessions.
- No EA rule patch is allowed from probe alone.

### Screened

- Model 1 only.
- Matched control required.
- Source path and input identity recorded.
- Cost stress x1/x1.5/x2 reported.
- Half-year/year/month split reported when the window allows.
- Outcome: kill or park. No promotion.

### Challenger

- Model 0 is mandatory for both strict control and challenger runs. Model 1 can
  kill or park only.
- Compile proof accepts MetaEditor exit `0` or `1` only. Exit `1` is valid only
  when a fresh compile log proves `0 errors` and a fresh non-empty EX5 is newer
  than the compile start.
- At least one trade, exact elapsed-day/week cadence, and report-bound cost PF
  x1/x1.5/x2 are required; a zero-trade screen must transition to kill/park,
  not remain `challenger`.
- Must beat matched control on net and risk-adjusted behavior, not only PF.
- No hidden overnight/weekend exposure.
- Execution/TCA issues must be explained.
- Sidecar/header changes must be versioned and analyzers updated.
- `validate-full` cannot be `REVIEW 0/5` for a deploy-readiness claim.

### Confirmed

Recommended minimums before portfolio review:

- Train and holdout must each independently pass cadence, cost PF, positive net
  R, stability/concentration, and every preregistered control margin. Aggregate
  metrics cannot hide a failing split.
- `CANDIDATE_REGISTRY.jsonl` must pass
  `validate_candidate_registry.py`, including elapsed arithmetic, physical
  readout/source/compiled-artifact hashes, split report/cost/outcome hashes, and
  the full validation-artifact set.
- Cost PF x1.5 remains above `1.25`.
- Cost PF x2 does not collapse below breakeven.
- A confirmed run requires an exact 84-month/14-half-year/7-year monthly
  fitness surface for a 2019-2025 style window; shorter evidence remains
  challenger-only.
- Positive months ratio at least `0.50`, with no one positive month contributing
  more than `20%` of total positive-month profit.
- Positive half-years at least `9/14`, with no one positive half-year
  contributing more than `35%` of total positive-half-year profit.
- Positive years at least `4/7`, with no one positive year contributing more
  than `40%` of total positive-year profit.
- WFA OOS profitable ratio at least `0.60`.
- PBO below `0.20` preferred; `0.20-0.40` is caution/park unless mechanism
  evidence is strong; above `0.40` is normally kill.
- White Reality Check/SPA must use the preregistered aligned full tried-variant
  family and reject the null of no superior strategy (`p < 0.05`).
- Monte Carlo P95 DD stays inside the risk budget.

Current producer boundary:

- `walk_forward.py` is fixed-parameter temporal slicing and diagnostic-only.
- `robustness_suite.py` perturbs realized P/L proxies and is diagnostic-only.
- the current `cscv_pbo.py` and `white_reality_check.py` outputs are bound and
  reproducible diagnostics, but they do not preserve a preregistered aligned
  selection matrix and set `promotion_eligible=false`.
- therefore the current tool stack must return `REVIEW/BLOCKED` at
  `confirmed`; freshly regenerating these diagnostics cannot promote a run.

### Portfolio Sleeve

- At least two independently confirmed component IDs.
- Hash-bound correlation/exposure and trade-overlap audits.
- Portfolio Monte Carlo P95 DD no greater than the declared risk budget.
- Combined cost PF x1.5 at least `1.25` and cost PF x2 at least `1.00`.
- The `portfolio-sleeve` registry state is invalid without these portfolio-only
  artifacts even when every component passed individual validation.

## Hard Invalidations

- Source compiled from `00. Old File` or any archive path.
- Missing `hypothesis_id` for a meaningful backtest.
- Model 1 used as promotion evidence.
- Any strict control/challenger run with `model != 0`.
- Post-hoc hour/day/year veto treated as a rule without new preregistration.
- PVSRA/volume/S&R used as standalone trigger without separate validation.
- Bar-zero price/buffer logic in a decision path.
- Filling at the same historical close used to form a completed-bar signal.
- Bar-level spread used to synthesize promotion-grade ask barriers when
  chronological bid/ask quote ticks are unavailable.
- Missing or stale run evidence after a claimed result.
- Lifecycle cost evidence that is not `sonic_telemetry.v3`, lacks finite
  positive `initial_risk_account`, lacks entry/exit `deal_profit`,
  `deal_commission`, `deal_swap`, `deal_fee`, or `deal_net`, fails deal-level
  reconciliation with the corrected `pnl_gross`/`pnl_net` semantics, or is not
  bound into a `verified_execution_cost.v1` artifact.
- Cost evidence that trusts declared sample counts, value, or P90 instead of
  parsing raw spread (`timestamp/symbol/bid/ask`), commission lifecycle, and
  side/reference/fill/pip slippage rows, or a hash-bound JSON broker contract.
- Any missing report-deal-to-lifecycle join, or any mismatch when unified
  validation canonical-rebuilds `trade_repricing` and `scenarios` from the raw
  cost inputs.
- Any OPEN row that substitutes requested order or net-position aggregate
  values for the actual history-deal ID, fill volume, fill price, fill time,
  position ID, and effective stop. Unrepresented partial/multi-deal fills block
  promotion.
- A Source S/R matched-control claim that assumes
  `InpUseSourceSrInteractionV1=0` is behavior-neutral. Current code still uses
  `source_sr_runway_pips` in Classic decision gates, so this remains a research
  blocker until a code fix or matched ablation proves isolation.

## Required Run Manifest Fields

Every serious run should have a run-local manifest or readout containing:

- `hypothesis_id`
- control/challenger run role
- command line
- git status snapshot
- canonical source path
- source hash
- compiled artifact timestamp/hash
- MetaEditor exit code plus fresh compile-log path/hash proving `0 errors`
- copied tester path
- input hash
- symbol/timeframe/window/model
- execution mode, fixed delay, deposit, leverage, and spread
- broker/server-build, account-contract, and tester-data fingerprints
- overrides and variant tag
- telemetry tier
- telemetry schema (`sonic_telemetry.v3`), PX6/Trades
  `initial_risk_account`, entry/exit deal-component presence, and reconciliation
  of deal-level values to corrected `pnl_gross`/`pnl_net`
- report path
- sidecar file hashes and row counts
- validation outputs
- cost stress outputs
- report-bound `verified_execution_cost.v1` path/hash produced by
  `build_verified_cost_artifact.py`
- raw spread/commission/slippage paths and hashes, or the hash-bound broker
  contract, plus full report-deal/lifecycle join and canonical-rebuild status
- phase/regime attribution outputs
- casebook/snapshot outputs when applicable
- final verdict and registry state transition
