# EA_RegimeStructureFusion

Research-only, single-source MQL5 EA that assigns distinct responsibilities to
five workspace indicators:

- AIRD and VRC route the market into probabilistic/deterministic context.
- MBB supplies range, pullback and squeeze-release setups.
- TB SMC supplies structure, sweep, displacement and stop anchors.
- QQE supplies closed-bar momentum timing.

The EA exposes three independent decision modes: `RANGE`, `TREND_PULLBACK` and
`COMPRESSION_BREAKOUT`. A mode-specific route is used instead of requiring all
five indicators to vote on every entry.

## Safety contract

- Strategy Tester only; `OnInit` rejects non-tester attachment.
- M5 entry decisions run once at the first tick of a new M5 bar.
- All indicator reads use completed bars (`shift >= 1`).
- TB SMC public contract buffer 43 must be at least `3.0`.
- Research authority, telemetry, exact hypothesis ID and exact symbol are
  mandatory before any order can be submitted.
- AUTO symbol/session values are priors for research, not optimal settings.
- No paper/live or promotion authority is granted by this package.

## Build

```powershell
.\02. AlphaFactory\alpha.ps1 compile "EA_RegimeStructureFusion"
```

The EA is one `.mq5` source file but requires the five compiled indicator EX5
files under `MQL5/Indicators/AlphaFactory/` in the workflow-owned MT5 runtime.

## Current evidence status

- Engineering: **PASS** — compile 0 errors, 21 structural/temporal tests and 14
  PATH lifecycle contracts pass, all five indicators initialize, non-repaint
  audit passes, and an independent code review found no P0-P2 issue in the
  transaction/shadow lifecycle.
- Economic: **FAIL** — `HYP-RSF-EURUSD-M5-PATH-011` ran one frozen EURUSD M5
  Model-0 trial over 2018–2022. Its 738 trades produced PF 0.799290, net
  -USD 5,252.63 and -0.08563R mean expectancy. The exact 519-entry matched
  parent cohort also remained negative at -0.07209R.
- Promotion: **BLOCKED** — optimization, validation, holdout, paper and live
  authority were never opened.

See `research/block1/HYP-RSF-EURUSD-M5-BLOCK1-001_RESULTS.json` for the complete
machine-readable cell ledger and
`research/block1/HYP-RSF-EURUSD-M5-BLOCK1-001_FAILURE_PACKET.md` for the
failure radius and fresh-hypothesis boundary. The reusable engine is retained;
the failed signal must not be traded or tuned under the killed ID.

The latest causal-structure result is
`research/liquidity_pool/HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010_RESULT.md`.
Its native MT5 Visual Mode review uses the actual MBB, QQE and TB indicators
with real trade markers. The chart evidence explains that many losses entered
into nearby opposing zones or degraded structure, but those observations are
outcome-derived and cannot be converted into HYP-010 filters. The exact
decision surface is terminal and is not worth parameter, timezone, direction,
RR or engine rescue.

Independent Grok review confirms the verdict and records one non-promotable P2
debt: 12/162 entries retained the objective frozen at arm time although a
nearer still-live liquidity level existed at entry. Correct-side and 1.25R
runway invariants still held. Rebinding is a new decision surface, not a legal
HYP-010 patch/rerun. See
`research/liquidity_pool/HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010_GROK_REVIEW.md`.

The closed-bar forensic replay is documented in
`research/evidence/HYP-RSF-EURUSD-M5-FORENSICS-001/FORENSIC_REPORT.md`. It adds
14 outcome-locked as-of/anatomy case pairs containing all five indicator
states, full-population path analysis and an independent Grok review. It
confirms the parent kill and does not authorize a parameter rescue.

The latest closed-bar path-management result is
`research/path/HYP-RSF-EURUSD-M5-PATH-011_RESULT.md`. Four native MT5 Visual
Tester replays verify the actual MBB/TB/QQE behavior and trade markers. The
mechanism cuts some losses, but MBB+QQE exits dominate the book, TB-flip exits
worsen the matched cohort, and every route retains negative mean R. The
corresponding `HYP-RSF-EURUSD-M5-PATH-011_FAILURE_PACKET.json` seals OOS and
forbids parameter, timezone, route, direction, stop, RR, or indicator rescue.
