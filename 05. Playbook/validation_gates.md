# Validation Gates

Updated: 2026-07-26

Gate authority for every EA lane. This file is not a profit target shortcut.
A candidate can move forward only when the required artifacts exist and the
result is broad enough to survive data-mining pressure.

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
- A probe used as KILL/falsification evidence requires a pre-outcome frozen
  PROBE_PLAN SHA-bound in the registry row (template:
  `02. AlphaFactory/templates/research/PROBE_PLAN.template.md`). A bound plan
  is immutable; pre-outcome amendments become a new `_V2.md` bound at the next
  transition.
- Indicator variant is part of the frozen surface: MT5 built-ins differ from
  Wilder formulas (iATR = SMA of TR; iADX = EMA of per-bar DI). A plan states
  `*_mt5` or `*_wilder` per indicator; Model-0-bound lanes use `*_mt5`
  (parity instrument: `tools/research/parity_harness.py`, PASS artifact
  required before trusting a SURVIVE that leans on an indicator gate).
- Expectancy floor is a WEEKLY bar: +0.08R/trade is calibrated to 2-5
  trades/week (~0.16-0.40R/week). For off-band cadence, preserve the weekly intent
  by scaling the per-trade threshold and declaring the chosen floor in the
  frozen plan pre-outcome. PF and stress gates do not move.
- A probe alone should not drive an EA rule patch — treat it as
  thesis-refine/kill evidence and confirm any rule change through screened+.

### Multi-simulation / grid falsification (exhaustive closure runs)

- Verdict statistic: DSR (Bailey & Lopez de Prado 2014), floor `0.95`.
- N = EVERY executed simulation across all stages, including controls and
  failed arms. Cost tiers x1/x1.5/x2 are NOT separate trials (same trade set).
- V[SR] is estimated across all evaluated arms' per-trade Sharpe; PSR uses
  skew and non-excess kurtosis; radicand <= 0 means FAIL, not skip.
- Primary series is the pooled train+validation set (a searched split is no
  longer OOS); two-split figures are diagnostics; the sealed holdout is the
  only true OOS and is spent at most once by a flagged survivor.
- Necessary-condition routing (net PF <= gross PF, same arm) may skip
  DOWNSTREAM cost work, but an arm with a DIFFERENT trade set (session shift,
  gate change) is not bounded by another arm's gross PF — never label such
  axes "exhaustively simulated" when they were only routed away.
- Default verdict is KILL; a DSR survivor is a FLAG requiring fresh prereg +
  verified cost + Model 0, never a promotion by itself.
- A parameter/variant sweep freezes source/config/count/selection fields before
  outcomes, then completes `alphafactory_optimization_receipt.v1` with full
  report and selected-series hashes after the run without changing frozen
  fields. `N` is every campaign simulation, not retained/top-k rows. The v1
  importer can diagnose the current family and a declared prior trial count,
  but cannot pass a gate until the campaign ledger independently proves
  cumulative exposure and preregistration time. MT5 tester Sharpe cannot be
  mixed with per-trade `net_R` moments.
- A stability surface is admissible only when every cell comes from a real
  optimization pass. Gaussian perturbation of one realized P/L series is not
  parameter evidence and cannot support `STABLE`, promotion or deployment.
- `analysis/purged_cpcv.py` requires event-level `start_time → label_end`
  intervals and the exact same event universe for every variant. It supplies a
  purged combinatorial split/PBO diagnostic, not reconstructed CPCV paths; the
  existing aligned daily CSCV/PBO producer remains a separate promotion surface
  until a stronger artifact is hash-bound into `validate-full`.

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
- Should outperform the matched control on the comparator declared in the
  frozen `acceptance_contract` (e.g. net and net/DD, not PF alone).
- No hidden overnight/weekend exposure.
- Execution/TCA anomalies should be documented and explained in the readout.
- Conditional market-impact stress may supplement cost evidence when order
  size is material, but `dynamic_cost_analysis.json` does not replace the
  canonical verified spread/commission/fill corpus. Schema v1 converts explicit
  quote costs to account currency and prevents PnL-basis double counting, but
  remains diagnostic even with a hash-bound depth manifest because it does not
  recompute calibration or reconcile the order lifecycle.
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

- Legacy single-report WFA, synthetic realized-P/L perturbation, and ad-hoc CSV
  PBO/Reality Check modes remain diagnostic-only with
  `promotion_eligible=false`.
- Promotion mode requires `variant_manifest.json` conforming to
  `alphafactory_aligned_variant_manifest.v1`: the full tried family, baseline,
  preregistration, source and each Model-0 run/CSV are SHA-bound; `exit_time` +
  `net_r` are aligned on a common daily grid; missing days are zero; analysis
  settings and family closure are frozen before outcomes.
- With that manifest, the producers can emit promotion-eligible expanding WFA,
  matched-EA-rerun sensitivity, CSCV/PBO and a joint moving-block White Reality
  Check. `unified_validation.py` independently binds those outputs to the
  current report, run identity, source and variant tree before a gate can PASS.
- A missing, stale, incomplete or post-hoc variant manifest still returns
  `REVIEW/BLOCKED`. Promotion eligibility is evidence-derived, never a manual
  flag flip.

### Portfolio Sleeve

- At least two independently confirmed component IDs.
- Hash-bound correlation/exposure and trade-overlap audits.
- Portfolio Monte Carlo P95 DD no greater than the declared risk budget.
- Combined cost PF x1.5 at least `1.25` and cost PF x2 at least `1.00`.
- The `portfolio-sleeve` registry state is invalid without these portfolio-only
  artifacts even when every component passed individual validation.

## Two-Speed Research Closeout

### Evidence-contract tiers

- A fresh data-acquisition hypothesis freezes
  `evidence_contract_kind=data_acquisition` and a `data_acceptance_contract`:
  history-quality operator/threshold, all-available coverage, mandatory symbols,
  no-skip, tester-journal bounds and series proof. It must not carry PF/cadence/
  drawdown gates or produce economic claims.
- A strategy hypothesis freezes `evidence_contract_kind=economic` and the
  economic `acceptance_contract`. Data quality remains a prerequisite, not a
  substitute for expectancy.
- Historical rows may retain the old economic-shaped object for append-only
  compatibility. A terminal transition may add the tier marker once, but may
  not reinterpret prior evidence or revive a stale authority.

Use the cheapest terminal packet that still proves the decision.

### Fast-Kill lane

Use `alphafactory_fast_kill_closeout.v1` only for an exact hypothesis cell that
is terminal at probe or early Model 0. It requires a frozen preregistration,
hash-bound result summary/readout, a triggered preregistered fatal gate and a
declared minimum observation count. Any sequential early-stop boundary must be
named and frozen before outcomes. Model 0 also requires source, compile,
non-repaint, run manifest, tester report, summary metrics and log triage.

Fast-Kill deliberately does not require chart rendering, Grok review or the
full delivery schema. It may close only the exact cell as `KILLED|PARKED|INVALID`;
it cannot claim EA completion, promotion or completion of a positive-expectancy
book goal. Data/engineering invalidation never becomes a market/no-edge verdict.
An arbitrary first-50-trade PF cutoff invented after viewing the run is invalid.

### Heavy-Delivery lane

Use the full EA delivery packet for a candidate that survives its frozen
necessary-condition gates, continues to challenger/confirmed work, is used to
design the next mechanism from run anatomy, or is described as
`DONE|complete|ready`. Chart anatomy and external visual review are escalation
tools for material setup/path ambiguity and survivor diagnosis, not a tax on
every terminal loser. When Grok or another reviewer is cited, its manifest and
parent QC remain mandatory.

## EA Development Delivery Gate

This is the mandatory completeness gate for the Heavy-Delivery lane. It
does not grant promotion; it prevents an agent from closing development after a
compile, report or attractive aggregate metric while logic/log/chart diagnosis
is still missing.

An `economic_run` delivery packet must hash-bind:

- frozen prereg and logic-to-code matrix with every material requirement mapped
  and tested;
- canonical source, EX5, compile log, test receipt and exact-source non-repaint
  audit;
- Model-0 run manifest, report, LifecycleTrades, RunMeta and standard log triage;
- reconciled analysis covering economics, cost stress, elapsed-week cadence,
  time/year stability, session, direction, regime/context, funnel, execution,
  win causes, loss causes, logic conflicts and limitations;
- an anatomy casebook with at least two winners and two losers when available.
  Every case shows entry/initial SL/TP/actual exit plus a centered HTF entry
  candle and explicitly labeled post-entry outcome bars;
- a separate outcome-blind `decision_asof` image for every cited setup-quality
  judgment. It must hide outcome/net_R and show every active indicator/gate
  from decision-time telemetry or a parity-proven MT5 export. Combined charts
  are human anatomy views, not unbiased entry evidence;
- when Grok or another external visual reviewer is cited, a machine-validated
  reviewer manifest must prove request/response identity, exact case and
  position coverage, `image_opened=true`, unique sampling and parent QC against
  lifecycle/source. Reviewer output is advisory and cannot itself authorize a
  rule change;
- a readout that separates pre-outcome rule from post-outcome observation and
  forbids direct rescue of a failed rule.

A `zero_trade_terminal` packet keeps source/compile/run/log identity and
report/lifecycle reconciliation, but economics and win/loss causes are explicitly
`NOT_APPLICABLE_ZERO_TRADES`. Funnel attribution and representative rejected-
candidate charts remain mandatory. Zero trades never become PF/WR/expectancy 0.

Run `alpha.ps1 delivery -Packet <packet>`. A missing role, stale hash, unresolved
logic ambiguity, report/lifecycle mismatch, unresolved material log error,
missing analysis dimension, or incomplete chart markers makes the completion
claim invalid. `INSUFFICIENT_EXPLAINED` is permitted only where the packet gives
a material reason; for an economic run all dimensions except regime evidence
must be `COMPLETE`.

## Hard Invalidations

- Source compiled from `00. Old File` or any archive path.
- Missing `hypothesis_id` for a meaningful backtest.
- Model 1 used as promotion evidence.
- Any strict control/challenger run with `model != 0`.
- Post-hoc hour/day/year veto treated as a rule without new preregistration.
- (Guidance) Declare each indicator's role (context/qualification vs trigger)
  in the frozen plan; a context/qualification indicator relied on as the sole
  entry trigger should carry its own validation before it counts.
- Bar-zero price/buffer logic in a decision path.
- Filling at the same historical close used to form a completed-bar signal.
- Bar-level spread used to synthesize promotion-grade ask barriers when
  chronological bid/ask quote ticks are unavailable.
- Missing or stale run evidence after a claimed result.
- Any EA development `DONE|complete|ready`, promotion, or survivor-based rule
  design claim without a passing `alphafactory_ea_delivery_packet.v1`. A valid
  Fast-Kill packet is the terminal exception for the exact killed/parked cell.
- Lifecycle cost evidence that is not `lifecycle-v3` telemetry (RunMeta schema
  `alphafactory_run_meta.v1`), lacks finite
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
- A matched-control claim that assumes a disabled input is behavior-neutral
  while the code still reads its state in a decision path. Prove isolation
  with a code fix or a matched ablation before using such a control.

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
- telemetry schema (`lifecycle-v3` / RunMeta `alphafactory_run_meta.v1`;
  cost artifact `verified_execution_cost.v1`), PX6/Trades
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
- delivery packet path/hash and `EA_DELIVERY_PACKET_OK` receipt
- final verdict and registry state transition
