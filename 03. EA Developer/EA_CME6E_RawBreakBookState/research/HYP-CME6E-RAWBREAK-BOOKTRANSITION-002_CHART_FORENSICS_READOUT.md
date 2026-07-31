# HYP-CME6E-RAWBREAK-BOOKTRANSITION-002 — chart and setup forensics

Verdict: **TERMINAL KILL CONFIRMED; ENTRY/CONTEXT FAILURE DOMINATES**  
Epistemic layer: **engineering-valid / economic-invalid / post-outcome descriptive**  
Date: `2026-07-27`

## 1. Executive verdict

The frozen chart sample and the full 258-trade population support the same
decision as the preregistered probe. The exact top-half CME 6E transition
overlay does not distinguish continuation from failed raw first-close breaks.
The terminal verdict remains
`KILL_DESIGN_BREAKBAR_BOOK_TRANSITION_NO_POSITIVE_EXPECTANCY`.

The failure is primarily in the **setup/entry decision surface**, not merely in
cost or the 120-minute timeout:

1. **OBSERVED — immediate adverse selection:** 161/258 trades (`62.4%`) are
   SL-like. Seventy-four trades (`28.7%` of the population) stop within 15
   minutes and lose `USD 823.50`. Another 101/258 (`39.1%`) never achieve even
   `+0.5R` bar-extreme favorable excursion and lose `USD 1,072.50`. Confidence:
   high that the entry surface is weak; medium that the causal label is
   exhaustion rather than an unmeasured state.
2. **OBSERVED — the book-transition score does not rank outcomes
   monotonically:** Spearman correlation is only `0.0627` versus realized R
   (`0.0655` versus net). Score quartile 3 is positive, but the highest score
   quartile falls back to negative; the strongest selected score (`0.323`) is
   an extreme loss. Confidence: high that this exact score is not a stable
   discriminator.
3. **OBSERVED — explicit cost amplifies, but does not create, the loss:** direct
   lifecycle reconstruction gives pre-explicit-cost PF `0.9353` and net
   `-USD 101.79`. Explicit commission/swap/fee contributes another
   `-USD 281.04`, producing native net `-USD 382.83`. Confidence: high. Spread
   is embedded in execution and cannot be separated from this ledger.

**STRONG INFERENCE:** the raw rule enters at the first tick after a completed M5
close crosses a confirmed pivot, with no hold, retest, replenishment, or
available-room decision. It therefore mixes at least two visually different
objects: a fresh continuation and a late/mature impulse that has just exhausted
at the break. The current M5 OHLC and five-level book summary do not separate
them reliably before entry.

Exit geometry is a secondary issue, not the main one. Thirty-two losing trades
(`12.4%` of all trades) first reach at least `+1R` and later close negative, so
some giveback exists. However, the dominant loss is early failure: the
`<=15`-minute bucket has PF `0.2833`, while the `60–120`-minute bucket is
positive. A management overlay on these opened outcomes would be an illegal
post-hoc rescue, not evidence that HYP-002 can be repaired.

## 2. Evidence integrity and scope

- The sampling plan was frozen before any chart view: SHA
  `5E26798433E3837D9A6FAF59C5D310C919647BB495CCCA723CC0E32ADE7E09F8`.
- The immutable sample contains 12 cases in declared order: two extreme wins,
  two extreme losses, two median wins, two median losses, and matched BUY and
  SELL winner/loser pairs. Sample manifest SHA:
  `53261925AAD0B1D02920314A39ADD8F749F7A378D97567F3F8257FBBE0BFD006`.
- Each case has a decision-as-of chart with future price hidden and a separate
  outcome anatomy chart. Twenty-four images were rendered; chart manifest SHA:
  `3FD635CA5F9E462F4CD964C7597286B7F30B030A8A6D42F40FF2D99935A4FD7F`.
- The causal CME 6E trace enforces
  `break_bar_open <= ts_event_and_recv < actual_decision`; 36,332 records were
  decoded for the 12 cases. Trace receipt SHA:
  `470B21A296DE4A17FEAB43EF63271D19EC027DEBF3982199B22FCAA004DF9060`.
- The full forensic population is the exact preregistered top-258 challenger,
  not a chart-selected subset. All 258 positions reconcile to exactly 516
  lifecycle rows with no partial closes and zero net mismatch.
- The parent control source hash is
  `9C03F4CB913E18B6CF660E48E7ADBD86034B1352A80167C32CC238BA7F7817B3`;
  active mode is `CONTROL_FIRST_CLOSE_BREAK`, with hold/retest disabled.
  Exact-source non-repaint audit is PASS with zero findings.
- The prior derived TCA summary is rejected because its filename discovery
  returned zero lifecycle rows. Cost figures here are rebuilt directly from
  the bound lifecycle CSV. Explicit commission is observed; independent
  spread/slippage provenance remains `UNVERIFIED_DIAGNOSTIC_ONLY`.
- This is 2021–2022 DESIGN evidence for a broker EURUSD outcome ledger overlaid
  with CME 6E book data. It does not establish same-venue CME execution
  economics, does not open holdout, and grants no Model-0, promotion, paper, or
  live authority.

## 3. Full-population decomposition

### Economics and payoff geometry

| Metric | Result |
|---|---:|
| Trades | 258 |
| Wins / losses | 91 / 167 |
| Win rate | 35.27% |
| Realized payoff ratio | 1.4357 |
| Implied break-even win rate | 41.06% |
| Mean / median realized R | -0.1559 / -1.0696 |
| Native PF / net | 0.7823 / -USD 382.83 |
| Before explicit cost PF / net | 0.9353 / -USD 101.79 |
| Explicit cost total / mean per trade | USD 281.04 / USD 1.0893 |

The setup misses its realized-payoff break-even win rate by `5.79` percentage
points. Cost is economically material, but removing the separable explicit
cost still leaves negative expectancy.

### Outcome path

| Outcome class | N | Share | Net | Mean R |
|---|---:|---:|---:|---:|
| SL-like | 161 | 62.4% | -1,746.04 | -1.1341 |
| TP-like | 66 | 25.6% | +1,197.86 | +1.8929 |
| Timeout/other | 31 | 12.0% | +165.35 | +0.5624 |
| Stop within 15 minutes | 74 | 28.7% | -823.50 | -1.1586 |
| Losing after reaching at least +1R | 32 | 12.4% | -324.83 | -1.0551 |

Winner median hold is `44.52` minutes; loser median hold is `17.98` minutes.
Within the first five minutes, median favorable/adverse excursions are
`0.321R / 0.219R` for winners versus `0.155R / 0.455R` for losers. These are
outcome-descriptive path facts, not tradable decision-time features.

### Decision-time context

The decision charts do not show a clean winner/loser partition. Break-body
fraction, break range/ATR, close location, distance beyond pivot, entry gap,
spread, and the one-hour pre-entry return have small winner/loser standardized
differences. The score itself is only weakly associated with outcome.

Two population-level exhaustion leads are visible, but they are post-outcome
and non-authoritative:

- **HYPOTHESIS — directional range extension:** the upper half of aligned
  24-hour entry location (`>~0.698` in this observed population) contains 129
  trades and loses `USD 348.49`; the lowest quartile is approximately flat to
  positive (`+USD 20.99`). Winner median is `0.642`, loser median `0.743`.
- **HYPOTHESIS — mature H1 impulse:** the strongest aligned prior-12-hour H1
  return quartile (`>21.6` pips in this observed population) has N64, win rate
  `21.88%`, mean R `-0.4976`, and net `-USD 302.24`. The other three quartiles
  are much less negative in aggregate.

Those cut points were observed after outcomes and are explicitly forbidden as
HYP-002 filters. They support a fresh mechanism question only; they do not
authorize deleting extended trades from this result.

The fixed book score is non-monotonic. Its four within-challenger quartiles
have mean R `-0.2800`, `-0.4546`, `+0.1339`, and `-0.0232`. Selecting the
positive-looking third quartile would be direct post-hoc overfit.

## 4. Winner and loser anatomy

### What winners look like

**OBSERVED:** the selected winners generally convert the first break into a
clean sequence of same-direction bars after entry, reach roughly `+2R`, and
show limited full-trade adverse excursion. In the matched BUY winner F009, the
score is `0.0682`, the 24-hour directional location is only `0.257`, and the
trade reaches `+2.095R` MFE with `0.095R` MAE. In the matched SELL winner F011,
the prior aligned H1 move is only `+2.8` pips and the path reaches `+2.293R`
with `0.155R` MAE.

### What losers look like

Two losing anatomies appear:

1. **Immediate failed break / adverse selection.** Extreme loss F003 has the
   strongest selected transition score (`0.323`) and enters a SELL near the
   `0.987` aligned edge of its prior-24-hour range, yet stops in `1.6` minutes.
   F004 stops in about `0.5` minute. High apparent break-bar book alignment is
   therefore not sufficient for continuation.
2. **Initial continuation followed by full giveback.** Matched BUY loss F010
   is deliberately close to F009 in direction, score, stop width, volume, and
   UTC minute. It reaches `+1.636R` MFE, fails to complete the 2R target, and
   later stops after 106 minutes. This is a real minority path-management
   problem, but it does not explain the much larger immediate-stop population.

Matched SELL loss F012 is the clearest exhaustion example: its score (`0.0577`)
is close to winner F011 (`0.0689`), but its aligned prior-12-hour H1 move is
`+66.1` pips versus `+2.8` pips for F011. It reaches only `+0.677R` before
reversing to a stop. The pair is visual support for the maturity hypothesis,
not population proof by itself.

### What the decision charts do not show

**OBSERVED:** several winners and losers look similarly valid at the actual
decision boundary. There is no stable visual signature in the frozen 12 cases
that the implemented score captures and that cleanly predicts follow-through.
Outcome charts make continuation and reversal obvious only after the fact.

**UNKNOWN:** whether deeper CME state, replenishment at the broken level,
queue dynamics, or a same-venue CME execution target would separate these
paths. The five displayed levels summarized over the completed bar cannot
answer that question.

## 5. Logic and fidelity choke points

The active source implements the tested object faithfully:

- `OnTick` gates on a new M5 bar and loads only closed bars with
  `CopyRates(..., shift=1, ...)` (`snapshot/source/...mq5:960–975`).
- `DetectBreak` requires the latest closed bar to cross a confirmed pivot by
  close and allows only one attempt per UTC day (`:470–494`).
- With hold/retest disabled, `ArmBreak` immediately calls
  `ResolveControlBreak`; no post-break observation is made (`:514–552`).
- Stop is the break-bar extreme plus `0.25 ATR`; target is fixed at `2R`
  (`:516–526`, `:373–377`).
- Exposure, spread, broker-distance, and risk-size guards execute before order
  submission (`:348–443`). Median accepted-entry spread and entry gap do not
  differ between winners and losers, so accepted-fill execution is not the
  observed primary separator.
- Remaining positions close after 24 M5 bars / 120 minutes (`:805–815`). The
  timeout/other group is positive, so the timeout is not the dominant loss
  source.

The main choke point is therefore intentional logic, not an implementation
bug: the decision is made immediately after the full break bar without a
second observation capable of distinguishing acceptance from rejection.

## 6. Frozen case manifest

| Case | Stratum | Dir | Score | R | Hold | Decision chart | Outcome chart |
|---|---|---:|---:|---:|---:|---|---|
| F001 / PID2058 | extreme win | BUY | 0.0350 | +2.043 | 17.0m | `charts_decision/F001_PID000002058_decision.png` | `charts_outcome/F001_PID000002058_outcome.png` |
| F002 / PID1762 | extreme win | BUY | 0.0045 | +1.974 | 33.3m | `charts_decision/F002_PID000001762_decision.png` | `charts_outcome/F002_PID000001762_outcome.png` |
| F003 / PID1324 | extreme loss | SELL | 0.3230 | -1.545 | 1.6m | `charts_decision/F003_PID000001324_decision.png` | `charts_outcome/F003_PID000001324_outcome.png` |
| F004 / PID2166 | extreme loss | SELL | 0.0280 | -1.448 | 0.5m | `charts_decision/F004_PID000002166_decision.png` | `charts_outcome/F004_PID000002166_outcome.png` |
| F005 / PID1678 | median win | BUY | 0.0667 | +1.871 | 52.2m | `charts_decision/F005_PID000001678_decision.png` | `charts_outcome/F005_PID000001678_outcome.png` |
| F006 / PID1476 | median win | BUY | 0.0896 | +1.875 | 35.6m | `charts_decision/F006_PID000001476_decision.png` | `charts_outcome/F006_PID000001476_outcome.png` |
| F007 / PID1282 | median loss | SELL | 0.0657 | -1.102 | 12.5m | `charts_decision/F007_PID000001282_decision.png` | `charts_outcome/F007_PID000001282_outcome.png` |
| F008 / PID1916 | median loss | BUY | 0.0187 | -1.102 | 14.3m | `charts_decision/F008_PID000001916_decision.png` | `charts_outcome/F008_PID000001916_outcome.png` |
| F009 / PID1598 | matched BUY win | BUY | 0.0682 | +1.810 | 12.6m | `charts_decision/F009_PID000001598_decision.png` | `charts_outcome/F009_PID000001598_outcome.png` |
| F010 / PID1412 | matched BUY loss | BUY | 0.0549 | -1.273 | 106.0m | `charts_decision/F010_PID000001412_decision.png` | `charts_outcome/F010_PID000001412_outcome.png` |
| F011 / PID1182 | matched SELL win | SELL | 0.0689 | +1.931 | 55.4m | `charts_decision/F011_PID000001182_decision.png` | `charts_outcome/F011_PID000001182_outcome.png` |
| F012 / PID1676 | matched SELL loss | SELL | 0.0577 | -1.081 | 55.1m | `charts_decision/F012_PID000001676_decision.png` | `charts_outcome/F012_PID000001676_outcome.png` |

The contact sheets are `decision_contact_sheet.png` and
`outcome_contact_sheet.png` under the evidence directory. Case charts are
anatomy evidence; the full-population CSV and lifecycle reconstruction own the
economic conclusion.

## 7. Conclusions and legal next hypotheses

### Final diagnosis

- **Primary:** raw first-close break entry admits too many immediate failed
  breaks and likely mature/exhausted impulses.
- **Secondary:** the frozen five-level transition score is noisy and
  non-monotonic; it cannot repair the entry surface.
- **Amplifier:** explicit cost consumes `USD 281.04`, but the price-profit
  component is already negative.
- **Minority issue:** some trades produce `+1R` or more then give it back, but a
  management rescue is neither dominant nor legal on this opened hypothesis.

No parameter, percentile, year/direction/session deletion, score reweight,
stop/target change, or management overlay is authorized for HYP-002.

At most two materially fresh hypotheses are suggested; neither is approved or
preregistered by this readout:

1. **HYPOTHESIS — post-break acceptance/replenishment entry:** use a fresh
   population and move the decision boundary beyond the raw close. Require an
   ex-ante defined revisit/hold plus same-venue book replenishment or renewed
   aggression before entry. This changes the entry mechanism and source
   contract rather than filtering HYP-002 outcomes.
2. **HYPOTHESIS — same-venue continuation freshness:** test CME 6E outcomes and
   execution against CME 6E book state, with a preregistered measure of
   available room and impulse maturity defined before outcomes. This changes
   the traded instrument/data contract and directly tests whether the
   EURUSD-CME proxy boundary hid useful microstructure information.

Both require de-duplication, a cheap source-feasibility probe, a new hypothesis
ID and frozen preregistration. Paid acquisition or live risk needs fresh Owner
approval.

### Independent Grok one-image audit

After this parent readout, Grok Build `grok-4.5/high` reviewed all 24 frozen
PNGs as 24 stateless one-image ACP jobs. The 12 decision charts were reviewed
outcome-blind before the 12 anatomy charts. Blind result: 10/12 `AMBIGUOUS`,
two `CONTINUATION`, with one correct and one wrong directional call. Outcome
result: six clean continuations, three immediate failed breaks and three
favorable-then-giveback paths; four of six losses were assigned primarily to
setup/entry and two to exit management. Every response passed `EndTurn`, exact
image SHA, `image_opened=true` and JSON-schema gates. This independently
confirms that outcome anatomy is visible after the fact while the implemented
decision surface lacks a stable visual separator. Full audit:
`research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_GROK_EACH_IMAGE_READOUT.md`.

## Evidence pointers

- `research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS_PLAN.md`
- `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/sample_manifest.json`
- `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/population_analysis.json`
- `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/forensic_population.csv`
- `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/chart_manifest.json`
- `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/book_trace_receipt.json`
- `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/grok_each_image_results.json`
