# HYP-LSS-OB-REPL-MT5-EURUSD-M15-002 — MT5 Model 0 readout

## Terminal verdict

`KILL_AT_MT5_MODEL0_CADENCE_ZERO_TRADE`

The Owner-required MT5 replication is complete. Both fixed arms ran in the
FivePercent portable MT5 Strategy Tester on EURUSD M15 for 2019-01-03 through
2022-12-31. Each report has 100% history quality, 99,475 bars, and 79,411,093
ticks. Neither arm opened a trade.

This is not a zero-PnL result. With zero trades, PF, win rate, expectancy,
Sharpe, drawdown, cost stress, WFA, Monte Carlo, and FTMO pass rate are
undefined. The lane fails the frozen cadence/minimum-trade gate and terminates
before those analyses.

## Valid MT5 runs

| Arm | Run | Funnel | Trades | Cadence |
|---|---|---:|---:|---:|
| Control (`InpSignalMode=0`) | `20260719_001202` | 388 sweeps -> 0 displacement -> 0 FVG | 0 | 0.0/week |
| Challenger (`InpSignalMode=1`) | `20260719_001306` | 388 sweeps -> 0 displacement -> 0 FVG -> 0 confirmed retest | 0 | 0.0/week |

Both manifests reconcile exactly one lifecycle CSV and one identity-bound
RunMeta JSON. Broker and data fingerprints match between arms. The challenger
execution receipt is bound to the control manifest and report.

The AlphaFactory enhanced analyzer returned `No trades found in report` after
each valid run. That non-zero analyzer exit is expected for an empty trade set;
the run manifests, reports, fingerprints, and lifecycle sidecars had already
been completed and hash-bound.

## Engineering evidence

- Package tests: 20/20 PASS.
- AlphaFactory compile: 0 errors, 0 warnings.
- Executed source SHA256:
  `445DE0C03AD785A31C4EE06FFA17FD36D89B7513F34160CBF78C42CDD5AFB68C`.
- Exact-source non-repaint audit V2: PASS, zero findings.
- The initial MT5 attempt exposed a calendar-validator bug: distinct releases
  may share one epoch. The validator was corrected from strictly increasing to
  nondecreasing, regression-tested, recompiled, and re-audited before the valid
  runs. This changed no signal threshold or strategy geometry.

Two earlier attempts are invalid evidence: `20260719_000621` stopped at OnInit
with zero ticks; `20260719_001031` completed Tester execution but its receipt
lacked the required top-level authority field.

## Parity and provenance limitations

The earlier offline replay counted 383 context-aligned sweeps; native MT5
counted 388. Therefore absolute upstream event-identity parity is not achieved.
Both surfaces still agree at the decisive downstream gates: zero qualifying
displacements, zero strict FVGs, and zero entries. The engineering parity gate
is therefore FAIL, and it cannot rescue the already-terminal cadence result.

Same-broker cost provenance remains `FAIL_SPREAD_COST_PROVENANCE`; news remains
source-C diagnostic only. The reports are diagnostic and
`promotion_eligible=false`. The 2023+ holdout remained sealed.

## Decision

Do not change displacement multiple, sessions, direction, confirmation, stop,
RR, timeframe, or asset to rescue this hypothesis. Do not rerun, optimize,
promote, or attach live. A future attempt requires a new hypothesis and a
materially different information set or causal mechanism, not a looser
ICT/FVG/OB funnel.

Machine-readable result:
`research/evidence/HYP-LSS-OB-REPL-MT5-EURUSD-M15-002_MT5_RESULT.json`.
