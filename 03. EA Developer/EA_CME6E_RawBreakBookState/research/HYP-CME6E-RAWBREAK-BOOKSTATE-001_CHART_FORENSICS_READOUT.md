# HYP-CME6E-RAWBREAK-BOOKSTATE-001 chart-forensics readout

Date: 2026-07-27  
Status: `POSTMORTEM COMPLETE / EXACT OBJECT KILLED / INTENDED CLOCK MECHANISM UNTESTED / OOS SEALED`

## 1. Executive verdict

The chart review found a material clock-semantics defect in the causal claim.
The CME feature window ends at the control ledger's `decision_time`, but that
field is the **open of the closed M5 break bar**, not the time at which the EA
knows the break. The EA detects the break after that bar closes and attempts
entry on the next-bar tick. In 229/230 challenger trades the frozen CME window
therefore ends exactly 300 seconds before the actual closed-bar decision/entry;
the remaining row is 330 seconds because of observed entry latency.

This changes the interpretation, not the terminal registry verdict:

- **OBSERVED — engineering-valid for the exact frozen object:** source hashes,
  join, outcomes, frozen sampling and chart corpus reconcile. The exact tested
  feature is stale pre-break-bar displayed depth.
- **OBSERVED — economic-valid terminal KILL for that exact object:** N=230,
  PF=0.527529, net=-USD822.70, mean R=-0.365156, win rate=30.00%; both years and
  both directions lose.
- **STRONG INFERENCE — intended causal mechanism not tested:** "book state
  immediately before the actual closed-bar decision" was not implemented. Its
  economic value is **UNKNOWN**.
- **OBSERVED — promotion/deploy-ready: false:** OOS 2021-2022 remains unopened;
  there is no MQL5 successor, Model 0, promotion, paper or live authority.

Ranked failure mechanisms:

| Rank | Mechanism | Confidence | Evidence |
|---|---|---:|---|
| 1 | Feature clock is one full M5 break bar stale relative to the actual decision | High | 229/230 rows have a 300-second cutoff-to-entry gap; source uses `CopyRates(..., shift=1, ...)` and enters only on the next-bar tick |
| 2 | The frozen static five-level displayed-depth score has no useful rank discrimination | High | score-vs-R Spearman 0.0471; score deciles are non-monotonic; matched winners and losers have nearly identical scores/book traces |
| 3 | Raw first-close BREAK plus tight stop produces broad early adverse selection and insufficient realized payoff | Medium-high | 153/230 `SL_LIKE`; 65/74 trades held <=15 minutes lose; realized payoff 1.2309 requires 44.82% wins versus observed 30.00% |

Costs amplify the loss but are not its root cause: the already frozen stress
tests reduce PF from 0.527529 native to 0.260191 at 1.5 pips and 0.182109 at
2.25 pips.

## 2. Evidence integrity

The chart sample was frozen before any image was opened. Exactly 12 unique
DESIGN challenger positions were selected from the bound 230-row population:
two extreme winners, two extreme losers, two median winners, two median losers,
and matched BUY and SELL win/loss pairs. OOS was not quoted, acquired, joined or
viewed.

Authoritative evidence:

| Artifact | SHA256 / state |
|---|---|
| Frozen plan | `66BB8F6DA9D88F5D7068ED4FC653A7C8A28DCFA33A5DFAE823C24C198C97BEA2` |
| Sample manifest | `A6AA87B494931A851D0E2D60259BD7C76F27E8BED3FEB4E501AAF8C85C42346A` |
| Case selection | `6A13A3739A02AC57995BCD57E9231D2B4ADC570A227E81400339621DCC4B98F6` |
| Forensic population | `65E4FB7DAE61D20DA6034B356C9251FE87054E3997BFC5C3086F16D8C92A15E4` |
| Population analysis | `F1B65D8D19FE5ACB71EA3D529A1D64FBDDDBD8658EDEAE24CBC18B9C61E8EFF7` |
| CME book traces, 6,739 rows | `6A63683ECD071054DC861DACA317379DF2204D0F379CDBF5AD0F86F6C5AFB537` |
| Book extraction receipt | `4DCC79D8D3194995B6C378884C8B9D53529E05392AE9BB471EE13D2E506B4986` |
| EURUSD M1 bars | `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A` |
| Authoritative Clock V2 chart manifest | `D64554DDF3AB0CC33C6F75AB0BA652E279190F027B921E3CF128C0F12FC3810A` |
| Clock V2 decision contact sheet | `404E0E74C25BE4BAB26A7A4E4BB542F0E99ECDA812323A3C6FC095A42A7F8300` |
| Clock V2 outcome contact sheet | `AFBA4990474BB9E4BCA63F88958D67DCC5A0DD2CFD29DF44CC0B1FA66499CEC2` |
| Clock erratum | `E4687EBD8BF93B02CB20EE0C7A457D43325257AC1FB010B0A7ED47A09BB39C1B` |

The first `chart_manifest.json` and its images are retained for audit but are
not authoritative. They mislabeled the break-bar open timestamp as the actual
BREAK decision. The Clock V2 manifest explicitly distinguishes the purple
feature cutoff/break-bar open from the blue next-bar actual decision/entry.

Limitations:

- **OBSERVED:** decision charts hide post-entry price; outcome charts expose it
  only for declared postmortem anatomy.
- **OBSERVED:** CME book traces are MBP-10 displayed depth, not queue position,
  cancellations, hidden liquidity or broker-spot executable liquidity.
- **OBSERVED:** MFE/MAE is reconstructed from M1 OHLC, so intrabar sequencing is
  path-ambiguous.
- **UNKNOWN:** whether a correctly aligned actual-decision feature, dynamic
  order-flow transition or cross-venue basis state has predictive value.

## 3. Population decomposition

### Exact challenger economics

| Metric | Result |
|---|---:|
| Trades / wins / losses | 230 / 69 / 161 |
| Profit factor | 0.527529 |
| Net / expectancy per trade | -USD822.70 / -USD3.57696 |
| Mean / median realized R | -0.365156 / -1.092593 |
| Average win / average loss | USD13.3126 / USD10.8153 |
| Realized payoff ratio | 1.230900 |
| Observed / implied breakeven win rate | 30.00% / 44.8249% |

**OBSERVED:** loss is broad rather than one catastrophic tail. The worst ten
trades contribute only 7.23% of gross loss, while the best ten contribute
20.91% of gross profit.

### Stability and score ordering

| Slice | N | PF | Mean R / net |
|---|---:|---:|---:|
| 2019 | 114 | 0.469920 | -0.420647 / -USD471.04 |
| 2020 | 116 | 0.587568 | -0.310623 / -USD351.66 |
| BUY | 118 | 0.604009 | -0.286093 / -USD335.27 |
| SELL | 112 | 0.455148 | -0.448456 / -USD487.43 |

**OBSERVED:** score-vs-realized-R Spearman is 0.047104 and score-vs-net
Spearman is 0.050885. The eligible-population score-decile PF sequence is
0.491, 0.404, 0.804, 1.114, 0.754, 0.594, 0.361, 0.595, 0.485, 0.662. The only
positive decile is decile 3, inside the lower half; the upper deciles do not
improve monotonically. This forbids a same-ID cutoff rescue.

All weekdays are negative. Sparse month and hour pockets are mixed and cannot
support a calendar veto. Stop-width quartiles improve descriptively from PF
0.404 in Q1 to 0.793 in Q4, but every quartile remains below one. Widening the
stop after reading these outcomes would be post-hoc management rescue, not a
finding authorized by HYP-001.

### Exit and holding anatomy

| Class | N | Wins / losses | PF | Net / mean R |
|---|---:|---:|---:|---:|
| `SL_LIKE` | 153 | 0 / 153 | 0.000 | -USD1,702.01 / -1.14243 |
| `TP_LIKE` | 42 | 42 / 0 | n/a | +USD769.68 / +1.89494 |
| `TIMEOUT_OR_OTHER` | 35 | 27 / 8 | 3.792 | +USD109.63 / +0.32053 |
| Held <=15 minutes | 74 | 9 / 65 | 0.2215 | -USD575.62 / -0.79541 |
| Held 15-60 minutes | 96 | 26 / 70 | 0.6151 | -USD295.65 / -0.31236 |
| Held 60-120 minutes | 57 | 31 / 26 | 1.1339 | +USD31.28 / +0.05449 |

**STRONG INFERENCE:** the dominant economic failure is not rare tail risk; it
is repeated failure to achieve immediate follow-through after a first-close
break. The 60-120 minute bucket is outcome-bearing and cannot authorize a
longer-hold rescue.

## 4. Winner/loser anatomy

M1-OHLC approximate path geometry separates winners only after entry:

| Path metric | Winner median | Loser median |
|---|---:|---:|
| Full-trade MFE | 2.0476R | 0.2639R |
| Full-trade MAE | 0.3404R | 1.0345R |
| First-5-minute MFE | 0.4118R | 0.1385R |
| First-5-minute MAE | 0.2258R | 0.4167R |

These figures describe outcomes; they are not legal entry features.

The matched pairs are more informative:

- **OBSERVED — SELL pair:** F011 winner and F012 loser have almost identical
  frozen scores (0.186381 versus 0.185799), identical 2.5-pip stops, equal
  volume and the same UTC entry minute. Their displayed-depth traces do not
  contain a stable pre-entry signature that explains the opposite outcomes.
- **OBSERVED — BUY pair:** F009 winner and F010 loser also have similar scores
  (0.174437 versus 0.166324), identical 3.1-pip stops and near-equal volume.
  Both book traces are ambiguous/reversing, yet outcomes diverge.
- **STRONG INFERENCE:** after matching on the available entry-known fields,
  winners share no stable frozen book-state pattern. The visible separation is
  subsequent price follow-through, which is outcome-bearing.
- **HYPOTHESIS:** consolidation quality, break-bar order-flow transition or
  futures/spot basis may distinguish follow-through. The 12 charts are too
  small and post-outcome to establish any of them as a rule.

## 5. Logic/fidelity choke points

The parent control source explains the five-minute gap:

- `EA_SweepCascadeContinuation.mq5:55-56` freezes
  `CONTROL_FIRST_CLOSE_BREAK` and `InpUseHoldRetest=false`.
- `EA_SweepCascadeContinuation.mq5:960-995` gates on a new M5 bar, calls
  `CopyRates(_Symbol, PERIOD_M5, 1, 6, bars)`, detects the break on `bars[0]`
  and passes that closed bar to `ArmBreak`.
- `EA_SweepCascadeContinuation.mq5:530-552` stores `bar.time` as
  `g_candidate.break_time`; because hold/retest is disabled it immediately
  calls `ResolveControlBreak`.
- `EA_SweepCascadeContinuation.mq5:514-526` builds the stop from the break bar
  and attempts the trade on the current next-bar tick.
- The alternative hold/retest state machine at lines 555-677 is dormant for
  this control population. It cannot be cited as tested behavior.
- Target is nominally 2R and timeout is 24 M5 bars (lines 63-64 and 805-815),
  but the realized payoff ratio is only 1.2309 after stops, timeouts and costs.

**Observed fidelity choke point:** the research join used a correctly stored but
semantically misnamed timestamp. It queried `[break_bar_open-120s,
break_bar_open)`, not `[actual_decision-120s, actual_decision)`. The exact
stale-feature KILL is valid; the intended actual-decision claim is not.

## 6. Case chart manifest

All paths below are relative to the evidence root
`research/evidence/HYP-CME6E-RAWBREAK-BOOKSTATE-001_CHART_FORENSICS/`. The JSON
manifest binds every image hash, source hash, position, clock role and OOS flag.

| Case | Stratum / reason | Dir | R | Decision / outcome chart |
|---|---|---:|---:|---|
| F001 PID152 | Extreme win #1 | SELL | +2.1515 | `charts_decision_clock_v2/F001_PID000000152_decision_clock_v2.png` / `charts_outcome_clock_v2/F001_PID000000152_outcome_clock_v2.png` |
| F002 PID342 | Extreme win #2 | SELL | +2.0135 | `charts_decision_clock_v2/F002_PID000000342_decision_clock_v2.png` / `charts_outcome_clock_v2/F002_PID000000342_outcome_clock_v2.png` |
| F003 PID710 | Extreme loss #1 | SELL | -1.3500 | `charts_decision_clock_v2/F003_PID000000710_decision_clock_v2.png` / `charts_outcome_clock_v2/F003_PID000000710_outcome_clock_v2.png` |
| F004 PID992 | Extreme loss #2 | BUY | -1.3043 | `charts_decision_clock_v2/F004_PID000000992_decision_clock_v2.png` / `charts_outcome_clock_v2/F004_PID000000992_outcome_clock_v2.png` |
| F005 PID436 | Median winner #1 | SELL | +1.8421 | `charts_decision_clock_v2/F005_PID000000436_decision_clock_v2.png` / `charts_outcome_clock_v2/F005_PID000000436_outcome_clock_v2.png` |
| F006 PID38 | Median winner #2 | BUY | +1.8500 | `charts_decision_clock_v2/F006_PID000000038_decision_clock_v2.png` / `charts_outcome_clock_v2/F006_PID000000038_outcome_clock_v2.png` |
| F007 PID814 | Median loser #1 | SELL | -1.1250 | `charts_decision_clock_v2/F007_PID000000814_decision_clock_v2.png` / `charts_outcome_clock_v2/F007_PID000000814_outcome_clock_v2.png` |
| F008 PID370 | Median loser #2 | SELL | -1.1250 | `charts_decision_clock_v2/F008_PID000000370_decision_clock_v2.png` / `charts_outcome_clock_v2/F008_PID000000370_outcome_clock_v2.png` |
| F009 PID484 | Matched BUY winner | BUY | +0.0968 | `charts_decision_clock_v2/F009_PID000000484_decision_clock_v2.png` / `charts_outcome_clock_v2/F009_PID000000484_outcome_clock_v2.png` |
| F010 PID18 | Matched BUY loser | BUY | -1.1613 | `charts_decision_clock_v2/F010_PID000000018_decision_clock_v2.png` / `charts_outcome_clock_v2/F010_PID000000018_outcome_clock_v2.png` |
| F011 PID174 | Matched SELL winner | SELL | +1.8800 | `charts_decision_clock_v2/F011_PID000000174_decision_clock_v2.png` / `charts_outcome_clock_v2/F011_PID000000174_outcome_clock_v2.png` |
| F012 PID354 | Matched SELL loser | SELL | -1.2000 | `charts_decision_clock_v2/F012_PID000000354_decision_clock_v2.png` / `charts_outcome_clock_v2/F012_PID000000354_outcome_clock_v2.png` |

## 7. Conclusions and legal next work

The exact HYP-001 stale pre-break-bar feature remains killed. It must not be
rescued by shifting old windows five minutes after outcomes are known, changing
the score cutoff, selecting the apparent 60-120 minute bucket, widening stops,
or vetoing dates/directions. The original hash-bound terminal readout and
registry row remain unchanged.

At most three materially fresh mechanisms are defensible for future
preregistration, each on a fresh untouched population:

1. **Actual-decision-aligned book state:** acquire/query the CME window ending
   at the next-bar decision tick, with the clock role named and validator-bound
   before any outcome join.
2. **Break-bar book transition:** measure depletion, replenishment, persistence
   and absorption across the full M5 break bar through the actual decision,
   instead of another static five-level snapshot or mined threshold.
3. **Cross-venue lead/lag state:** combine point-in-time 6E price/depth change
   with broker EURUSD movement or basis at the same decision timestamp, with a
   fresh mechanism, ID, source plan and outcome-blind contract.

No further paid data request, OOS opening, source build, Model 0 or deployment
is authorized by this postmortem.
