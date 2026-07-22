# Frozen preregistration — MZMS XAU M5 four-mechanism campaign

Status: **FROZEN 2026-07-22 before source modification, compile, or any new outcome access.**

This file binds four fresh hypotheses authorized by the Owner. It does not reopen or rescue
terminal/invalid HYP-006. The exact decision surface is the Grok design candidate at
`research/HYP-MZMS-XAU-M5-007-010_GROK_DESIGN_CANDIDATE.md`, SHA256
`DF80B74C20F28528D3A4B30D996A704C8C1BB162EBBC4E3D360BF16456AF7298`.
That referenced artifact is immutable for this campaign.

## 1. Identity and trial universe

| Order | Hypothesis | `InpSignalMode` | Mechanism | Magic |
|---:|---|---:|---|---:|
| 1 | `HYP-MZMS-XAU-M5-007` | 2 | Donchian fresh-impulse initiation with expanding ATR and rising mid-band ADX | 5600727 |
| 2 | `HYP-MZMS-XAU-M5-008` | 3 | EMA20/EMA100 trend pullback and closed-bar pivot reclaim | 5600728 |
| 3 | `HYP-MZMS-XAU-M5-009` | 4 | Bollinger/ATR compression followed by closed-bar envelope breakout | 5600729 |
| 4 | `HYP-MZMS-XAU-M5-010` | 5 | RSI/wick/ADX-roll exhaustion rejection mean reversion | 5600730 |

- Canonical package: `EA_MZMS_Scalper`.
- Trial accounting: exactly four economic tester invocations, one per row above. `N_trials=4`.
- Run order is fixed as 007 → 008 → 009 → 010.
- One canonical multi-variant source may implement all modes before the first run.
- There is no optimization, parameter grid, rerun, alternative control, or outcome-driven arm removal.
- Owner explicitly requested build → compile → Model-0 backtest for all four; therefore the
  cheap offline density probe is skipped as an Owner-directed build-first exception. The
  adverse prior and all gates remain frozen.

## 2. Data and tester boundary

- Broker/runtime: portable FivePercent MT5 via AlphaFactory.
- Symbol/timeframe/model: `XAUUSD`, `M5`, Strategy Tester Model `0`.
- Requested window: `2018.01.01` through `2026.07.22`.
- Deposit/leverage/risk: USD 100,000 / 1:100 / 0.01% equity per accepted entry.
- Known prior: the immediately preceding XAU run produced 98% history quality.
- Hard validity gate: report history quality must be at least 99%. Below 99% means
  `PARK_INVALID_ENGINEERING_RUN_HISTORY_QUALITY_BELOW_99`; economics may be described only
  as diagnostic shape and cannot authorize promotion or a strategy no-edge kill.
- Cost provenance remains unverified/diagnostic. Missing cost is never interpreted as zero.
- Embedded EUR/USD 2019–2022 news data is not PIT-complete for XAU/full-window, so
  `InpRequireNewsGuard=false` uniformly. This blocks promotion.

## 3. Exact decision surface

The exact shift-indexed boolean rules, parameters, indicator formulas, MQL5 implementation
touchpoints, telemetry fields, per-mode adversarial priors, and per-mode kill gates are
sections 1 through 10 of the bound Grok design candidate SHA above. In particular:

- Signals use closed M5 bars only (`shift >= 1`) and execute at the first quote of the next bar.
- Intrabar signal evaluation, break-even, partial close, and trailing are OFF.
- Common session is 08:00–17:00 UTC using the existing FivePercent EU-DST server clock;
  hard flatten is 18:15 UTC.
- Spread ceiling is 35 XAU points; cooldown is five closed M5 bars; one owned position max;
  five entries max per UTC day.
- Stop is the farther of five-bar structure plus 40 points and 1.5×ATR14.
- Target is 1.6R; time exit is 15 M5 bars; risk guards remain 1.5% daily and 8% account DD.
- Each mode must emit decision-time telemetry for every active indicator/gate required by its
  chart panel. Post-run indicator reconstruction is not accepted as decision truth without
  parity evidence.

Any change to a rule or parameter above before the first outcome requires `_V2` and a new
registry transition. Any change after an outcome requires a new hypothesis ID.

## 4. Engineering gates before Model 0

All must pass before the first tester run:

1. Red-first package tests for modes 2–5, identity/magic mapping, boundary booleans, mode
   dispatch, telemetry surface, closed-bar indexing, cooldown, ownership, BE OFF, and legacy
   modes 0/1 unchanged.
2. AlphaFactory compile from the canonical package with 0 errors and 0 warnings.
3. Exact-source non-repaint audit with zero findings.
4. Source snapshot, EX5, compile receipt, capability contract, task packets, and cost manifest
   hash-bound before execution.
5. Registry transitions for all four hypotheses advance from `probe` to `screened` with the
   same source SHA and this prereg SHA.

## 5. Acceptance and kill gates per hypothesis

All gates are evaluated independently for each mode when history quality is valid:

- Profit factor ≥ 1.35.
- Cadence 2.0–5.0 trades per elapsed requested-window calendar week.
- Maximum drawdown ≤ 6.0%.
- Verified-cost stress PF: x1.5 ≥ 1.25 and x2 ≥ 1.00; if verified cost is unavailable,
  promotion remains blocked and results stay diagnostic.
- Monte Carlo P95 maximum drawdown ≤ 6.0% when sample size supports it.
- Lifecycle must reconcile exactly to report and RunMeta, with zero net-P/L gap.
- WFA, robustness, year/month/session/direction/holding/stop/volatility, execution and
  concentration diagnostics must be reported; weak subgroups may not be deleted post hoc.

History-valid terminal kill: cadence failure, or PF < 1 with at least 100 trades, or negative
expectancy with at least 100 trades, or DD > 6%, yields `KILL_DIAGNOSTIC_NO_EDGE` for that ID.
An invalid-history run is parked, not economically killed or promoted.

## 6. Frozen chart-forensics contract

After each run and before opening images, freeze its position population and select at least
100 unique closed positions following section 10 of the bound design:

- 30 winners, 30 losers, 10 matched winner/loser pairs (20 positions), and 20 anomalies;
- deterministic seed from hypothesis ID + run ID;
- if fewer than 100 defined-risk positions exist, render the entire population and mark
  `SAMPLE_DEGENERATE_N_LT_100`;
- render both `decision_asof` and `anatomy` indicator-rich PNGs per case;
- one Grok job reviews five cases, global Grok concurrency one;
- require exact case/position coverage and `image_opened=true` before acceptance.

Grok observations are mechanism diagnostics only. They cannot patch a completed mode or grant
a rerun. Parent owns lifecycle reconciliation, source fidelity QC, exact counts, and verdict.

## 7. Forbidden post-result edits

- No threshold, indicator period, session/hour/day/year/direction, symbol, RR, stop, hold,
  cooldown, spread, BE, or risk adjustment under IDs 007–010.
- No selecting a winner then tuning it on the same 2018–2026 window.
- No claim of production readiness, paper/live authority, or profitability from compile,
  invalid history, tester-only costs, reviewer text, or in-sample PF.
- No fifth run or rerun without a new Owner decision and fresh hypothesis identity.

Promotion eligibility is frozen `false` for all four hypotheses.
