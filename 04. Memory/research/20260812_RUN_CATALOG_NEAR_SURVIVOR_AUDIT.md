# Run Catalog Near-Survivor Audit - 2026-08-12

## Scope

This is a database-first reuse audit, not a new economic experiment. The local
AlphaFactory catalog was used only to locate prior M5/M15 runs. Every verdict
below was traced back to the immutable run folder and its report/analysis
artifacts. No new price outcome, optimization, MT5 run or hypothesis was opened.

The 2026-06-21 campaign contains 58 cataloged runs across 22 EA names between
`20260621_145416` and `20260621_214115`. Selection from this batch therefore
has a material multiple-trial prior unless a pre-run hypothesis, source identity
and trial correction can be proved.

Previously reviewed apparent leaders remain terminal or inadmissible:
`EA_Cobra`, `EA_LondonNY`, `EA_ITSM`, `EA_Gotobi`, `EA_ChopRegime`,
`EA_SilverBullet`, `EA_Spark` and `EA_InsideBar`. The only two uncataloged
near-survivor names requiring direct artifact review were `EA_VolCluster` and
`EA_ShanghaiFixScalp`.

## EA_VolCluster / 20260621_192253

- Target: USDJPY M15, Model 0, 2018-01-01 through 2025-12-31, History Quality
  99%, 274 trades, PF 1.397382, net USD 6,188.36.
- Frozen run inputs traded only Monday and Thursday inside hours 10-14. The run
  folder contains no preregistered hypothesis ID or hash-bound source contract.
- The source file `EA_VolCluster.mq5` is absent from both the workspace and the
  local MT5 terminal trees. The run preserves only the compiled executable and
  logs, so closed-bar/non-repaint behavior and exact source identity cannot be
  audited or reproduced lawfully.
- The native report records zero commission on deals. Cost stress is explicitly
  `report_only_cost_stress`: spread points 0, slippage points 0, commission 0,
  and an arbitrary USD 0.50 round-turn deduction. The artifact itself says
  telemetry/broker data are required before deploy claims.
- `slippage_summary.json` is `WARN`, `available=false`, with no slippage samples
  and no final-close telemetry.
- Trade-sequence WFA produced profitable OOS windows in four of five partitions,
  but the most recent OOS window (2025-05-26 through 2025-11-24) failed at PF
  0.78 and net USD -333.18. This is adverse recency evidence, not a live-ready
  result.
- The generic WFA label `EXCELLENT` and validation `PASS` only mean the analysis
  scripts executed under their old gates; they do not repair missing source,
  costs, slippage, preregistration or trial control.

Verdict: `NO_REVIVAL_SOURCE_COST_TRIAL_AND_LATEST_OOS_FAIL`.

## EA_ShanghaiFixScalp / 20260621_194633

- Target: XAUUSD M15, Model 0, 2018-01-01 through 2025-12-31, History Quality
  99%, 281 trades, PF 1.380067, net USD 12,638.00.
- Frozen inputs select only Monday, AM fix, one direction and RR 1.5. There is no
  pre-run hypothesis/trial correction proving these choices were selected
  independently of outcomes.
- The source file `EA_ShanghaiFixScalp.mq5` is absent from both the workspace and
  local MT5 terminal trees, preventing lawful source/non-repaint reproduction.
- The report records zero commission. Its cost artifact is the same report-only
  USD 0.50 proxy with zero spread/slippage/commission assumptions; the slippage
  artifact is `WARN` and contains no samples.
- WFA is terminally poor: OOS PF by window is 0.98, 0.78, 3.76, 0.53 and 0.81;
  only one of five OOS windows is profitable. The generated WFA verdict itself
  says `POOR` and `Do NOT trade live`.

Verdict: `NO_REVIVAL_WFA_SOURCE_COST_AND_TRIAL_FAIL`.

## Registry lineage check

The latest-state query showed apparent open M5 probes only because source-only
parent IDs remain labeled `probe`. Their economic/runtime descendants are
terminal:

- Round Cascade HYP010 led to HYP011, killed at PF 0.6762 with ten of eleven
  frozen gates failing.
- JCDR HYP002 led through router/source children to HYP006, killed at PF
  0.763972, net USD -7,888.77 and equity DD 8.02%.

Parent state is not an unfinished edge and must not be treated as authorization
to resume the family.

## Final verdict and failure radius

`NO_REVIVAL_CANDIDATE` for the inspected historical M5/M15 catalog.

This closes only the reuse claim that an old high-PF run can be promoted or
silently rebuilt. It does not prove that volatility-cluster or time-fix market
mechanisms can never work. Any future attempt must be a materially independent,
pre-outcome object with surviving source, native 2018-latest data, explicit
commission/spread/slippage contracts, trial accounting and fresh OOS/holdout.

The active goal therefore remains `ACTIVE / UNMET` and returns to discovery of
a materially new information object on a symbol whose native M5/M15 history can
already satisfy the evidence window.

## Artifact anchors

- `02. AlphaFactory/runs/EA_VolCluster/20260621_192253/`
- `02. AlphaFactory/runs/EA_ShanghaiFixScalp/20260621_194633/`
- `04. Memory/research/CANDIDATE_REGISTRY.jsonl`
- `04. Memory/research/20260811_GROK_DEEP_RESEARCH_LOOP_REVIEW.md`
- `04. Memory/do_not_repeat_failures.md`
