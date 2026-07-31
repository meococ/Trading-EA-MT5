# HYP-004 corrected Random-100 GFI readout

Status: `DESCRIPTIVE_POSTMORTEM_ONLY`  
Parent verdict authority: Codex lead quant/integrator  
Grok role: read-only chart-forensics reviewer  
Hypothesis: `HYP-SCC-MT5-REPLICATION-EURUSD-M5-004`  
Run: `20260725_210811`

## Clock correction and casebook acceptance

The original Random-100 chart campaign is invalid because its chart clock did
not align MT5 server-time trades with the UTC-indexed research bars. It cannot
support chart observations or mechanism claims. The replacement V2 corpus:

- converts every entry and exit to the bar clock before rendering;
- renders one decision-time H1 chart and one outcome-anatomy H1 chart for each
  of 100 deterministic random cases;
- matches all 200 entry/exit marker events against UTC M1 bars;
- has zero missing markers, median marker error 0 points, p90 error 2 points
  and maximum error 15 points.

Fail-closed casebook receipt:
`random100_forensics_clock_v2/random100_casebook_qc.json`,
SHA256
`4CD04614A5A388AD56538CEF1E2CFA07CE0B37B8BCA0250D92CECD795854DAA3`.

The timebase correction changes only the visual corpus and chart-derived
interpretation. It does not change the MT5 report, trade population, native
economics or terminal `KILL` verdict.

## Chart-output quality audit

| Dimension | Verdict | Evidence and limitation |
|---|---|---|
| Temporal fidelity | `PASS` | Canonical server-to-UTC conversion, 200/200 entry/exit marker checks, zero missing and 0/2/15 point median/p90/max error. |
| Trade-lifecycle fidelity | `PASS` | Direction, entry, SL, TP, exit, hold duration and exit class are drawn from the reconciled lifecycle ledger. |
| Outcome-leakage control | `PASS` | `decision_asof` ends at the entry cutoff and masks the future; `anatomy` explicitly discloses the post-entry path. The two image roles are not interchangeable. |
| Population sampling | `PASS` | The sample was seed-fixed before review, covers 100 unique positions and is directionally consistent with the 261-trade population. |
| Reviewer/image coverage | `PASS` | Grok opened 100/100 decision images and 100/100 anatomy images; semantic QC reconciled every case. |
| Multi-timeframe context | `PARTIAL` | H1 cutoff, last closed bar and current partial bar are explicit, but the casebook carries no M15/H4 context or measured strategy-specific HTF state. |
| Signal-state traceability | `PARTIAL` | Charts do not draw the consumed pivot, BREAK arm, HOLD state, retest acceptance, spread gate or the exact closed-bar decision chain. They explain realized paths better than why the EA accepted each trade. |
| Execution-cost visibility | `PARTIAL` | SL/TP/exit prices are visible, but commission, realized spread, slippage and cost-in-R are not overlaid per case. Population cost stress remains a separate artifact. |
| Predictive feature discovery | `FAIL_CLOSED` | Anatomy labels are outcome-disclosing. The chart set may generate hypotheses but cannot establish a decision-time discriminator or authorize threshold selection. |

Overall quality:
`PASS_FOR_POSTMORTEM_PATH_FORENSICS_PARTIAL_FOR_SIGNAL_FIDELITY_NOT_VALID_FOR_OPTIMIZATION`.

Before a future EA can use charts for decision-rule refinement, its casebook
must add hash-bound decision-time telemetry for every active state/gate and
execution-cost component. That upgrade belongs to the new hypothesis package;
it is not a repair or rerun of HYP-004.

## Grok transport and coverage acceptance

The corrected campaign used 20 bounded ACP jobs of five cases each. Every job
transported ten inline PNG content blocks: five decision-time images and five
outcome-anatomy images. Global concurrency remained one. Invalid or truncated
responses were rejected; retries preserved the same case contract and were
accepted only after schema and semantic validation.

Accepted coverage:

- batches: 20/20;
- unique cases: 100/100;
- decision images opened: 100/100;
- anatomy images opened: 100/100;
- total images opened: 200/200;
- accepted Grok cost: USD 1.7992532.

Semantic QC independently reconciled case ID, direction, entry, exit, exit
class and H1 range position against the frozen casebook. Receipt:
`random100_forensics_clock_v2/grok_review/random100_grok_batch_qc.json`,
SHA256
`9AE1B83FDB8A50BAC5858DDE68959F7995535E333798F4557AF96C0330E2B86B`.

## Population and random-sample economics

The 261-trade challenger remains economically negative:

- win rate 31.4176%;
- profit factor 0.6912782;
- net account P/L -587.30;
- mean realized R -0.23178969;
- cadence 1.25137 trades per elapsed calendar week.

The deterministic Random-100 sample is directionally consistent and slightly
worse:

- 28 wins / 72 losses;
- win rate 28.0%;
- profit factor 0.6035237;
- net account P/L -305.60;
- mean realized R -0.3111671.

## Grok descriptive path taxonomy

Across the corrected 100-case corpus Grok assigned:

- `TIGHT_STOP_MICROSTRUCTURE_FAILURE`: 58 cases, all losses;
- `IMMEDIATE_CONTINUATION_EXPANSION`: 23 cases, 21 wins and 2 losses;
- `NO_FOLLOWTHROUGH_TIMEOUT`: 15 cases, 5 wins and 10 losses;
- `MIXED_OR_OTHER`: 4 cases, 2 wins and 2 losses.

Evidence class coverage is 95 `OBSERVED` and 5 `STRONG_INFERENCE`.

These labels are **outcome-disclosing descriptions** because the anatomy image
contains the realized exit path. Their separation is not predictive evidence
and cannot be converted into an entry filter, stop change, target change,
timeout rule or optimization objective under HYP-004.

## Independent population path geometry

M1 OHLC diagnostics on all 261 trades support the same research direction
without granting a rule:

- 86 of 179 losers never reached +0.25R MFE;
- 65 of 179 losers reached at least +0.50R MFE;
- 30 of 179 losers reached at least +1.00R MFE;
- median loser MFE was +0.2632R;
- median winner MFE was +2.1137R.

Primary next research priority:
`ENTRY_SETUP_DISCRIMINATION`.

Secondary priority, under a separate child identity:
`EXIT_MANAGEMENT`.

The M1 diagnostic is not tick-exact path sequencing. It cannot decide which
side of a same-minute stop/target event occurred first and is not a backtest.

## Representative cases

- `R100_002_PID000000140`: short loss after favorable movement near the target
  before reversal to stop; useful anatomy for the exit-management research
  question, not authorization to move the stop.
- `R100_023_PID000000138`: clean short expansion reaching target in 2.6
  minutes; illustrates the small immediate-expansion subset.
- `R100_039_PID000000508`: short timeout after 120 minutes with approximately
  -0.084R; illustrates the no-followthrough class.
- `R100_001_PID000000268`: decision-time long case with low H1 range position;
  this single context is not evidence for an H1 range filter.

## Parent reconciliation and boundary

HYP-004 remains terminal:
`KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY`.

No same-ID tuning, optimization, rerun, patch, promotion or live authority is
created by this review. Specifically forbidden as HYP-004 rescue are retest,
pivot, ATR, stop, target, timeout, session, weekday, year, direction and H1
filter changes.

Any continuation requires:

1. a materially new causal mechanism, information/data contract or decision
   surface;
2. de-duplication against the existing registry and failure ledger;
3. a fresh hypothesis ID and frozen outcome-blind probe;
4. preregistration before any meaningful result;
5. direct matched MT5 Model-0 evidence, followed by independent OOS and
   robustness gates.

Deep Research and Grok outputs are idea inputs only. They do not grant build,
rerun, promotion or live authority.

Integrated corrected verdict:
`GFI_RANDOM100_CLOCK_V2_ACCEPTS_HYP004_KILL_AND_OPENS_ONLY_NEW_ID_DISCOVERY`.
