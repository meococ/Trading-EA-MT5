# HYP-011 trade forensics — Grok Build CLI coordinated postmortem

Date: 2026-07-19

Scope: read-only failure/winner/context analysis of AlphaFactory run `20260719_142214`

Authority: diagnostic only; no tuning, rerun, promotion, paper or live authority

## Verdict

The run failed for a structural reason, not just because of commission. The
active object was the high-recall `SignalMode=0` sweep/reclaim control, not the
full ICT/FVG report-fidelity state machine. Its deal P&L was already negative
before explicit commission (`PF=0.9007`, `-$2,195.70`); commission added
`-$3,606.00` (`-0.0854R` per defined-risk position) and reduced final PF to
`0.7588` with `-$5,801.70` net.

The central geometry is unfavorable: achieved win rate was `46.90%`, while the
observed average payoff required `53.79%` to break even. Median winners were
only `+0.422R`; median losers were `-1.065R`. The source moves the stop to
`+0.5R` after touching `+1R`, producing the large `+0.4R net` winner cluster,
while most losing trades still realize the full initial stop.

This diagnosis does not revive or replace the terminal run verdict. MT5 history
quality was `99%` against the frozen `100%` gate, and historical execution-cost
provenance remains unverified.

## Evidence identity and reconciliation

- Source SHA-256:
  `EFEA68F7763873B5F880BBCB2919A3A2DF629289E06F69A525FA91396C9674A6`.
- Lifecycle SHA-256:
  `D475B6FC5145BBD79C26645A04900F3366B75961A665C36A112C6BF693A5C6A6`.
- `8,682` lifecycle rows reconcile to `4,341` opens and `4,341` final closes.
- `4,340` positions have defined initial-risk R; position `224` has a zero
  initial-risk telemetry anomaly and remains in money P&L but not R aggregates.
- Hash-bound FivePercent M1 bars were mechanically aggregated to M5. Context is
  available for `4,340/4,341` positions; the data pull ends before the last
  position (`8682`), so that one trade has no M5 context annotation.
- Grok completed on `grok-4.5`, session
  `019f795d-0138-7b11-afb1-d982795ec984`, `stopReason=EndTurn`. Its first
  cancelled response was rejected rather than accepted as evidence.
- Independent local reproduction matched the headline economics. Grok reported
  `1,448` matched pairs; the independently specified greedy matcher produced
  `1,465`. This small algorithmic difference does not affect the verdict.

Receipt:
`research/evidence/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_GROK_FORENSICS_RECEIPT.json`.

## Failure decomposition

| Mechanism | Evidence | Interpretation |
|---|---:|---|
| Negative before explicit commission | PF `0.9007`; `-$2,195.70`; `-0.0524R/trade` | The signal object itself has no positive expectancy in this sample. Removing commission alone does not rescue it. |
| Explicit commission load | `-$3,606.00`; `-$0.831/trade`; `-0.0854R/trade` | Small stop distances make fixed transaction costs material. Spread/slippage remain embedded in deal profit, so this is not a zero-cost counterfactual. |
| Payoff mismatch | avg win `+$8.965` / `+0.921R`; avg loss `-$10.436` / `-1.072R` | Required WR `53.79%` is well above achieved `46.90%`. |
| Full-stop concentration | `2,285` trades (`52.64%` of all trades) near full stop; `98.88%` of losing dollars | Losses are broad and repetitive, not caused by a few outliers. |
| Temporal instability | all 9 entry years PF `<1`; 79/103 months negative | No favorable year or stable subperiod exists in the completed chart. |
| Direction/session instability | BUY PF `0.729`; SELL PF `0.792`; measured London PF `0.769`; New York PF `0.703` | Neither side nor material session carries the book. |
| Context overlap | every quartile of risk width, sweep depth, reclaim, range/ATR, close location, 20-bar return and EMA context has PF `<1` | Simple one-factor thresholding is not an evidence-based rescue. |

The smallest measured UTC-hour bucket at hour 12 contains only eight trades and
has PF `1.14`. Therefore Grok's phrase “every hour loses” is too broad. The
defensible statement is that every year, both directions, both material
sessions and every sufficiently populated context bucket are negative.

## Where winning trades come from

The winners are two economically different groups:

1. `726` near-2R target wins (`16.72%` of all trades) contributed
   `$13,261.84`, or `72.66%` of all winning dollars. These are the rare paths
   where price continues or reverses decisively after the sweep and reaches the
   original target before the stop-management logic truncates it.
2. `1,237` locked-profit wins (`28.50%` of all trades) contributed only
   `$4,810.24`, or `26.35%` of winning dollars. Their median result is about
   `+0.4R net`, consistent with the source moving SL to `+0.5R` after `+1R` is
   touched.

The pre-entry medians of target winners and full-stop losers overlap heavily:
both have about a 5.1–5.2 pip signal range, 1.3–1.4 pip sweep depth, 1.5 pip
reclaim and roughly 50 points initial risk. The current local sweep/reclaim
features do not cleanly identify which path will become a full target winner.

A post-exit M5 diagnostic of the `1,237` locked-profit trades found that, after
the lock exit and before 22:00 UTC, the original TP appeared before the original
SL in `640` cases (`51.74%`), while SL appeared first in `585` (`47.29%`), with
12 undecided. This supports testing management as a separate future hypothesis,
but it is not a valid same-sample claim: the scan is post-outcome, uses bid M5
OHLC, starts at the next full bar, applies SL-first ambiguity and lacks
short-side ask spread.

## Chart-grounded cases

The case list was frozen by the Grok pass before chart rendering. Twelve as-of
charts contain only bars available at entry; twelve anatomy charts show the
outcome path. All 24 rendered successfully and are bound by SHA-256 manifests.

- `C01`, position `1374`, `-4.298R`: a shallow 0.2-pip sweep/reclaim enters
  short with only 19 points risk. A sharp upward gap/jump crosses the intended
  stop and produces the worst slippage tail. This is an execution-tail example,
  not the dominant loss mechanism; only 18 trades were worse than `-1.3R`.
- `C03`, position `6836`, `+2.177R`: the short follows an already developing
  bearish displacement and reaches the target almost immediately. The win came
  from continuation strength not represented by the bare sweep gate.
- `C05`, position `5726`, `+0.422R`: trend-aligned long reaches the BE trigger,
  retraces into the `+0.5R` locked stop, then later reaches the original 2R
  level. It is a concrete example of management truncating a potential target.
- `C07`, position `4052`, `-1.065R`: long is stopped in nine minutes, followed
  later by a large rally. It illustrates sensitivity of a roughly 4.1-pip stop
  to local sequence/noise; it does not prove that widening stops is profitable.
- `C09` versus `C10`: two London shorts in strong pre-entry uptrends and with
  similar sweep/reclaim signatures. `C09` catches the reversal and wins
  `+1.871R`; `C10` is stopped almost immediately for `-1.387R` as the uptrend
  continues. The current signal has no MSS/displacement/FVG/HTF context gate to
  distinguish them.

Chart roots:

- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/charts_asof/`
- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/charts_anatomy/`

## Logic bottlenecks in source

1. **The tested object is not the report-fidelity strategy.** The override is
   `InpSignalMode=0`. `ProcessClosedM5Bar()` calls `DetectSweep()`, whose control
   branch opens immediately with comment `ICTFVG_CONTROL_SWEEP`. RunMeta proves
   `displacements=0`, `fvgs=0`, `mss=0`, `retests=0`, `adx_passes=0`.
2. **Entry context is too weak.** A close back through the latest local M5 pivot
   is sufficient. The full displacement → strict FVG → M15 MSS → fresh OB/FVG
   overlap → retest → ADX path is dormant. The matched charts show why the same
   local shape can be either exhaustion or continuation.
3. **Exit geometry compresses upside.** `ManageOwnedPosition()` locks `+0.5R`
   after `+1R`, while the original target is `2R`; `1,237` trades cluster near
   `+0.4R net`, but `2,285` trades still realize approximately `-1R`.
4. **Signal-bar stops are small relative to noise and cost.** Stop is the sweep
   bar extreme plus/minus 1.5 pips; median initial risk is 50 points (5 pips).
   The tightest risk-width quartile has PF `0.632` and expectancy `-0.238R`.
5. **Clock model drift exists from 2024.** Source applies European DST for every
   year, while the measured broker clock uses European DST through 2023 and US
   DST from 2024. This affects 106 entries and changes session classification
   for 47. Those 47 are negative, but this defect cannot explain 2018–2023 and
   must not be used as a rescue narrative.
6. **Analyzer output is not authoritative.** The existing TCA summary reports
   zero activity despite 4,341 reconciled lifecycles. Its zero values are
   rejected as a path/schema mismatch; lifecycle telemetry is the evidence.

## Decision

- Keep HYP-011 terminal. Do not tune session, hour, stop width, sweep depth or
  reclaim thresholds from this readout.
- Treat the DST clock and TCA zero-output issues as engineering defects, not
  alpha discoveries.
- If the Owner opens future work, the most defensible new research objects are
  separate preregistered hypotheses: an exit-management arm using unchanged
  entries, and a genuinely new point-in-time context model. They require new
  IDs and future/OOS evidence; neither may reuse HYP-011 to rescue the killed
  family.

Reproducible local outputs:

- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/trade_forensics.json`
- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/positions_with_context.csv`
- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/matched_pairs.csv`
- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/cases.csv`
- `02. AlphaFactory/runtime/ictfvg_hyp011_forensics/forensics_manifest.json`
