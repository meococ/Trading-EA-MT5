# HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012 — Model-0 readout

## Verdict

`INVALID_DIAGNOSTIC_HISTORY_QUALITY_99_PERCENT_AND_KILL_CONTEXT_NO_EDGE`

The bounded post-sweep context state is an engineering-valid, materially new
mechanism. It improves loss severity relative to immediate sweep entry, but it
does not create positive expectancy and fails every frozen economic/cadence
gate. The 2018-2026 tester history is also 99% versus the preregistered 100%
validity requirement. HYP-012 is terminal. No threshold tuning, rerun,
promotion, paper, or live use is authorized.

This verdict kills the exact HYP-012 state transition, not all contextual,
probability-ranked, or discretionary trading.

## Frozen question and implementation

The control enters immediately after a closed M5 liquidity sweep/reclaim. The
challenger stores one setup per direction/session for at most three subsequent
closed M5 bars. It rejects the setup if price closes beyond the swept extreme
and confirms only when a directional candle:

- has real body at least `1.00x` the prior-20 M5 mean body;
- closes beyond the opposite extreme of the original sweep bar; and
- closes in the outer directional 25% of its own range.

The first tick after that confirmation close enters with the original sweep
extreme plus 1.5 pip stop buffer, 2R target and the same +0.5R lock after +1R.
Control and challenger differ only by `InpSignalMode` and magic number. Risk,
sessions, costs, account controls, date window, tester model and management are
matched.

The frozen V2 plan is
`HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012_MODEL0_PLAN_V2.md`, SHA-256
`8A50C07039C5FE2725E7CAEB29637F509773646EDEE926185BD3B308C291FDF3`.

## Engineering proof

- Canonical source SHA-256:
  `8B1C9E283B97716C91F61FCDB2A74B6168CC0671DAE896A941F0F181674E6CE1`.
- Red-first context contract: 4/5 failed before implementation; full package
  after implementation: 31/31 PASS.
- AlphaFactory compile: 0 errors / 0 warnings.
- Source/binary/compile receipt V16 SHA-256:
  `C5AEE3CC4633488E26AD54ADF6341D59F71BEDAFC25E6CE69CAA2F9385F92757`.
- Exact-source non-repaint V14: PASS, zero findings; only `iTime(...,0)` is
  used as the new-bar clock. Audit SHA-256:
  `BE31CBCB3E1A8FC76C3E3F21C39F143C8FE839DB1C9979FEADCD58B29717644F`.
- Both run manifests bind the same source SHA. AlphaFactory recompiles for each
  run, so EX5 byte hashes differ; no claim of deterministic binary identity is
  made.

## Matched Model-0 result

Window: EURUSD M5, `2018.01.01-2026.07.19`, Model 0, 100,000 deposit, 1:100,
0.01% diagnostic risk, account-DD input 100%, news disabled consistently.
Both runs processed 636,544 bars and 206,517,809 ticks.

| Metric | Immediate control | Context-state challenger | Delta |
|---|---:|---:|---:|
| Run ID | `20260719_161929` | `20260719_162104` | — |
| History quality | 99% | 99% | 0 pp |
| Positions | 4,341 | 3,385 | -956 |
| Trades / elapsed week | 9.736 | 7.592 | -2.144 |
| Profit factor | 0.7588 | 0.8104 | +0.0516 |
| Win rate | 46.90% | 46.68% | -0.23 pp |
| Net at micro-risk | -USD 5,801.70 | -USD 3,264.50 | +USD 2,537.20 |
| Expectancy | -0.13775R | -0.09799R | +0.03975R |
| Report max balance DD | 6.014% | 3.335% | -2.680 pp |

The lower loss and DD are real for this diagnostic, but they are caused by
fewer trades and moderately lower loss severity, not a positive edge. The
challenger's observed average winner is +0.897R and average loser is -0.969R,
which requires a 51.93% break-even win rate; achieved win rate is only 46.68%.
Its median winner is about +0.440R and median loser about -0.998R. There are
1,726 near-full-stop positions, 1,046 +0.5R-lock outcomes, and 500 near-2R
targets.

All nine entry years lose after commission. Annual PF ranges from 0.668 to
0.957; there is no positive year available to support a regime-stability
claim.

## State funnel

The telemetry reconciles exactly:

`26,756 raw sweeps = 5,703 duplicate active-state rejects + 6,879 acceptance
invalidations + 7,758 three-bar timeouts + 6,416 closed-bar confirmations`.

Of 6,416 confirmations, 3,385 positions opened after normal risk/exposure/
cooldown/spread gates. The context layer therefore remains common rather than
selective: 7.592 trades/week is still above the frozen 2-5 range.

## Why the new logic still fails

### 1. The confirmation variables do not discriminate outcomes

Winner and loser medians are nearly identical:

| Pre-entry feature | Winners | Losers |
|---|---:|---:|
| Confirmation body / prior-20 mean | 1.823x | 1.837x |
| Directional close location | 0.919 | 0.917 |
| Confirmation range | 5.9 pip | 5.9 pip |
| Bars after sweep | 2 | 2 |
| Sweep depth | 1.5 pip | 1.4 pip |
| Sweep reclaim | 1.6 pip | 1.6 pip |
| Initial risk | 10.3 pip median overall | 10.3 pip median overall |

Every quartile of confirmation-body strength, decisive-close location, sweep
depth/reclaim, initial risk and completed H1/H4 state remains PF below 1. More
body strength is therefore not a monotonic probability edge in this sample.

### 2. A simple higher-timeframe alignment veto is not the missing answer

Closed H1/H4 EMA context was attached point-in-time using completed bars only.
Both aligned groups return PF 0.757; mixed alignment PF 0.788; both opposed PF
0.883. All three lose. This is consistent with the earlier HYP-011 HTF audit:
static trend alignment does not separate reversal winners from continuation
losses and must not be promoted into a post-hoc filter.

### 3. Similar contexts still have opposite outcomes

The frozen closest short win/loss pair uses the same London session, confirms
two bars after the sweep, has the same 2.4-pip confirmation range and 0.792
directional close location, similar stop size and similar aligned H1/H4 EMA
state. Position 5,226 returns +0.409R; position 5,108 returns -1.049R. This is
the expected signature of a probabilistic setup: context can raise or lower
odds, but no individual visual pattern determines the outcome.

### 4. Management still compresses the payoff distribution

The +0.5R lock turns many valid excursions into approximately +0.4R net wins,
while most losses remain close to -1R. With this payoff distribution, a
confirmation gate must produce materially more than 52% winners or a better
exit distribution. HYP-012 does neither. Changing management after reading
these outcomes would be a new hypothesis, not a rescue.

### 5. Friday flatten is mechanically unsafe

Thirty-seven positions crossed the weekend close and contributed -13.62R.
Five positions finished below -1.30R; the worst was position 1,790 at -3.153R,
opened Friday 2020-02-21 16:05 UTC and closed on the first Sunday quote. The
cause is deterministic: a tick-driven `>=22:00 UTC` flatten cannot send the
close if the Friday market stops producing ticks before the threshold.

This is a separate execution defect and must be fixed before any future
economic test with a pre-close Friday flatten plus new-entry veto. Removing
the 13.62R weekend contribution would not rescue roughly -332R total
challenger expectancy, so it does not change the alpha verdict.

## Frozen gates

| Gate | Result |
|---|---|
| 100% tester history | FAIL (99%) |
| 2-5 trades / elapsed week | FAIL (7.592) |
| At least 800 positions | PASS (3,385) |
| PF >= 1.30 | FAIL (0.810) |
| PF improvement >= 0.20 | FAIL (+0.052) |
| Expectancy >= +0.05R | FAIL (-0.098R) |
| Expectancy improvement >= +0.15R | FAIL (+0.040R) |
| At least six positive years | FAIL (0/9) |

Cost provenance is still not verified on the same historical broker feed.
Consequently `promotion_eligible=false` independently of the negative result.

## What “human-like context” should mean next

The useful human behavior is not a market story. It is a consistent sequence:

1. retain event memory rather than react to one candle;
2. represent context as measured pre-entry features;
3. estimate a conditional probability/payoff, including uncertainty;
4. rank simultaneous opportunities and allow `NO_TRADE`;
5. execute with hard operational safeguards; and
6. update only on a scheduled, out-of-sample research cycle.

HYP-012 implemented step 1 and part of step 2. It did not implement calibrated
probability, interaction effects, opportunity ranking, or a selective no-trade
policy.

## Recommended next research plan — not authorized by this readout

Do not rerun HYP-012 with tuned body, lag, HTF, hour, year or stop thresholds.
A legal child must be materially new and frozen under a new ID:

1. **Execution hardening first:** pre-close Friday flatten while the market is
   tradable, Friday new-entry veto after the frozen cutoff, broker-clock/session
   parity and valid TCA telemetry. Prove with unit tests and targeted tester
   cases before reading economics.
2. **Feature contract:** retain only closed-bar, point-in-time variables known
   at decision time: sweep/reclaim geometry, time-to-confirm, confirmation
   shape, stop/range, session, volatility, and completed H1/H4 state. No
   discretionary labels or future path.
3. **Probability layer:** use a small preregistered regularized model or fixed
   score to estimate net-R expectancy, including cost. Interactions—not
   univariate thresholds—are the research question.
4. **Walk-forward policy:** train only on prior years, predict the next year,
   purge overlapping events, calibrate inside each training fold, and never
   refit on the evaluation year. Because HYP-012 outcomes through 2026 are now
   known, call this rolling OOS diagnostic, not a sealed holdout.
5. **Opportunity policy:** rank candidates online, cap exposure, accept only
   positive lower-confidence-bound expectancy, and assign rejected events 0R
   per opportunity. Do not force cadence by selecting bad trades.
6. **Frozen acceptance:** positive net R/opportunity after verified cost,
   PF >=1.30, 2-5 trades/week, stable fold contribution, no single-year rescue,
   and execution gates passing. If the model cannot outperform the exact
   HYP-012 control out of sample, kill the probability layer.

This is the closest systematic analogue to a disciplined trader: not “knowing
the market,” but applying the same conditional-probability and no-trade process
to every opportunity.

## Evidence map

- Control run: `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_161929/`
- Challenger run: `02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_162104/`
- Reconciled result:
  `02. AlphaFactory/runtime/ictfvg_hyp012_context_result/hyp012_context_result.json`
- Context/HTF forensics:
  `02. AlphaFactory/runtime/ictfvg_hyp012_context_forensics/forensics.json`
- Six frozen cases and twelve charts:
  `02. AlphaFactory/runtime/ictfvg_hyp012_context_forensics/`

