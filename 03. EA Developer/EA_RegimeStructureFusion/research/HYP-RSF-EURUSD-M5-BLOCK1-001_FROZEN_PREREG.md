# HYP-RSF-EURUSD-M5-BLOCK1-001 Frozen Preregistration

Frozen before any 2018-2022 discovery outcome is read. This is the first
symbol-specific mechanism/session block under the master
`HYP-RSF-MULTI9-M5-001` family. It is not a rescue of the terminal integration
smoke: it is the prospective ablation block declared before that smoke ran.

## Question

For EURUSD M5 with M15 context, which necessary layers of the five-indicator
decision stack survive across multiple calendar regimes without violating the
required 2-5 trades/week cadence?

The Q1-2023 smoke (`20260806_171007`) is engineering evidence only. Its mode,
session, weekday and hour results are forbidden inputs to this selection.

## Frozen identity and execution contract

- EA source SHA-256: `E40F29431E8ADA440302F7DEDB7ACD8EBCB48C1308EB6B43936849C128E959D0`
- Compile checkpoint: MetaEditor `0 errors / 0 warnings`; local EX5 96,124 bytes.
- Each AlphaFactory launch recompiles the same source. Its generated EX5 hash
  is recorded in that run manifest; selection binds source hash, compiler
  result and per-run EX5 hash instead of assuming EX5 byte reproducibility.
- AIRD source: `C432AEF3BF7EC93EC8A64BD2806C115E71F822B2DCB438DAC22590FB978EB475`
- VRC source: `EB81B1426CBDAF3143F553388A213E2BB5A3E33E05433991918CC5977273A087`
- MBB source: `AC5DB6E1DDA825F6A3535E9AB1E4C9956086C7AF590E2672C71CF03D8F4E54FE`
- TB SMC source: `4658F3CD2C439C2655EF1534A18D29BC52EB6D91B494F2C17CC337755F1F1F33`
- QQE source: `22456C83C73D2070F52D83BBCE7D5DC1982CD987F8BE807E10482703982CAF9A`
- Symbol/timeframe: EURUSD M5; context M15.
- Discovery window: 2018.01.01-2022.12.31.
- Tester model: Model 0 / every tick.
- Deposit/leverage: 100,000 USD / 1:100, matching the broker's money-mode
  margin-call 92,000 USD and stop-out 90,000 USD geometry.
- Risk: 0.20% per trade; all exits, stop geometry, cooldown and daily controls
  remain at the source defaults.
- Costs: tester current spread plus report commission/swap. This is a research
  proxy, not independent dynamic-slippage evidence, so Block 1 cannot establish
  economic validity or promotion readiness.
- Every completed or cadence-killed cell counts toward family trial count.

## Locked ablation semantics

All five indicators remain initialized in every cell to hold warm-up and data
availability constant. The switches affect the decision path only:

- `InpUseContextRouter=false`: removes the global AIRD confidence/state and VRC
  regime predicates. Breakout origin becomes MBB release only.
- `InpUseTbStructure=false`: removes TB entry filters and all TB-derived stop
  anchors. TB ATR remains a frozen shared risk-normalization utility for the
  minimum/maximum stop envelope; therefore “MBB-only” means entry-decision
  ablation, not indicator-unloaded isolation.
- `InpUseQqeTiming=false`: removes QQE side, direction, reacceleration and
  extreme predicates.
- MBB S1/S2/S3 events remain mandatory in every cell. Mode priority stays
  breakout, then trend, then range.
- `InpProfileMode=1` is mandatory. Session and mode axes are controlled only by
  `InpManualSessionMask` and `InpManualModeMask`; the three `InpAllow*Mode`
  inputs remain true.
- RunMeta must report effective masks, all three switches, stop-out geometry and
  separate setup/context/structure/timing/risk/execution counters.

This is a cumulative necessity hierarchy, not a full factorial estimate of
all interactions. It intentionally does not test TB without context or QQE
without TB.

## Exact 18-cell matrix and immutable order

Masks: RANGE=1, TREND=2, BREAKOUT=4; LONDON=2, OVERLAP=4.

| Cell | Session | Session mask | Mechanism/modes | Mode mask | Context | TB | QQE |
|---:|---|---:|---|---:|---:|---:|---:|
| 01 | London | 2 | MBB only, all modes | 7 | 0 | 0 | 0 |
| 02 | London | 2 | MBB + context, all modes | 7 | 1 | 0 | 0 |
| 03 | London | 2 | MBB + context + TB, all modes | 7 | 1 | 1 | 0 |
| 04 | London | 2 | Full stack, all modes | 7 | 1 | 1 | 1 |
| 05 | London | 2 | Full stack, trend only | 2 | 1 | 1 | 1 |
| 06 | London | 2 | Full stack, breakout only | 4 | 1 | 1 | 1 |
| 07 | Overlap | 4 | MBB only, all modes | 7 | 0 | 0 | 0 |
| 08 | Overlap | 4 | MBB + context, all modes | 7 | 1 | 0 | 0 |
| 09 | Overlap | 4 | MBB + context + TB, all modes | 7 | 1 | 1 | 0 |
| 10 | Overlap | 4 | Full stack, all modes | 7 | 1 | 1 | 1 |
| 11 | Overlap | 4 | Full stack, trend only | 2 | 1 | 1 | 1 |
| 12 | Overlap | 4 | Full stack, breakout only | 4 | 1 | 1 | 1 |
| 13 | Union | 6 | MBB only, all modes | 7 | 0 | 0 | 0 |
| 14 | Union | 6 | MBB + context, all modes | 7 | 1 | 0 | 0 |
| 15 | Union | 6 | MBB + context + TB, all modes | 7 | 1 | 1 | 0 |
| 16 | Union | 6 | Full stack, all modes | 7 | 1 | 1 | 1 |
| 17 | Union | 6 | Full stack, trend only | 2 | 1 | 1 | 1 |
| 18 | Union | 6 | Full stack, breakout only | 4 | 1 | 1 | 1 |

No other session, hour, weekday, direction, threshold or exit dimension is
authorized in Block 1.

## Analysis and selection

1. Reconcile every lifecycle OPEN to one final CLOSE. Engineering-invalid runs
   are repaired without reading/ranking economic output and rerun under the
   same cell ID.
2. Segment each fixed cell's lifecycle trades into calendar years 2018-2022.
   Each year is an independent temporal bucket. Also report the whole window.
3. Hard reject cells outside 2-5 trades per elapsed calendar week in any
   required annual bucket, or with non-positive net expectancy after tester
   costs.
4. Use expanding selection folds: rank using years available through `t`, then
   record the selected cell's result in year `t+1`. Rank by median next-year net
   R, not in-sample PF or total net profit.
5. Require an adjacent session or cumulative-mechanism neighbor to retain at
   least 90% of the selected median fold score. Isolated peaks fail.
6. Prefer fewer decision layers, then a single session over the union, then
   lower OOS dispersion, lower drawdown and finally the lower cell number.
7. DSR/PBO family count includes the integration outcome plus all executed
   Block-1 cells and all later campaign simulations. No discarded run vanishes.

## Stop conditions and authority

- Stop this EURUSD branch if no cell passes cadence and positive-expectancy
  gates across discovery years.
- Stop if the apparent winner lacks adjacent/cumulative-neighbor support.
- Stop and open a new hypothesis ID for any post-outcome change to switches,
  router logic, matrix, sessions, costs or selection rules.
- Structure, regime/timing and exit blocks remain locked until Block 1 produces
  a stable positive discovery survivor.
- Rolling 2023-2024 validation and the 2025+ family holdout remain closed.
- No Block-1 result can authorize demo/live use or promotion.

Independent prereg review: Grok Build read-only review returned
`ACCEPT_WITH_CHANGES`; the changes above implement its required switch
semantics, MANUAL masks, counter separation and strict Q1 isolation. Codex owns
the final decision and source verification.
