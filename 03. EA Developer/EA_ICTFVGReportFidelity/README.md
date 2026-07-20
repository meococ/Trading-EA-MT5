# EA_ICTFVGReportFidelity

Owner-authorized EURUSD M5 implementation of the ordered ICT/FVG report state
machine. This package is a separate hypothesis and does not modify or reopen
the killed `EA_FVGConfluence` specimen.

Current engineering identity is the audit-retained v1.27 source for terminal
`HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026`. It has no rerun,
economic, paper, live or promotion authority. The single authorized zero-trade
Model-0 collection defined 6,398/6,401 pivot-relative dwell profiles, but only
181 were `ADVERSE_DOMINANT` (2.8290%, 0.40583 per elapsed week) versus 6,217
`FAVORABLE_DOMINANT`. The frozen density and materiality gates failed in both
temporal splits, so HYP-027 was not opened and the HYP-012 sweep-confirmation /
pivot-dwell branch is at `FRONTIER_STOP`. Canonical source SHA-256:
`227A52E93713731EF639D9484DABC89B85006660F436C0F232117C60F1528127`.

HYP-026 terminal readout:
`research/HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026_READOUT.md`.

The inherited EA state machine implements:

`M5 sweep/reclaim -> displacement + strict FVG -> fresh OB/FVG overlap ->
closed M15 MSS -> first 50-70% retest/rejection -> closed M15 ADX > 25`,

plus London/New York sessions, fixed-money risk sizing, prop controls,
restart-safe lifecycle accounting and a hash-bound historical-news guard. The
news source keeps all 1,282 event rows; the runtime lookup correctly contains
869 sorted unique release timestamps (413 same-time rows collapsed only in the
lookup).

Current engineering proof: 110/110 package tests PASS, AlphaFactory compile 0
errors / 0 warnings, exact-source/dependency non-repaint V23 PASS and post-run
source/binary receipt V31 verified. These are engineering facts only; they do
not rescue the negative HYP-012/HYP-017 economics or establish edge.

Corrected Model-0 verdict: HYP-008 is terminal
**KILL_AT_MODEL0_CORRECTED_EXECUTION_CONTROL_LOSS_CHALLENGER_ZERO_TRADE**.
Its 8%-DD control opened 122 trades, PF 0.5774, net -USD 7,944.29 and then
stopped in March 2019; the full report-fidelity challenger reached one valid
retest, failed ADX and opened zero trades.

The first Owner-requested no-DD full-chart observation is complete under
HYP-010. The
intermediate 0.25%-risk run `20260719_131410` was invalid because broker/tester
stop-out ended it on 25 April 2019. The identity-bound micro-risk control
`20260719_133139` then completed all 2019-2022 data: 2,070 trades, 9.925 trades
per elapsed week, PF 0.7625, win rate 46.62%, -0.1348R/trade and net -USD
2,752.44 at diagnostic 0.01% risk. All four calendar years were negative. This
is the generous sweep/reclaim control, not the zero-trade full-fidelity object.

The follow-up HYP-011 run `20260719_142214` explicitly opened 2018 through
2026-07-19 and disabled the news guard consistently because the immutable
calendar covers only 2019-2022 and otherwise fail-closes outer years. It
completed 636,544 bars / 206,517,809 ticks and reconciled 4,341 opens with
4,341 final closes. Result: PF 0.7588, win rate 46.90%, -0.13775R per position
with defined risk, 9.736 trades/week, net -USD 5,801.70 and 6.014% balance DD
at 0.01% risk; every entry year was negative after commission. MT5 history
quality was 99% versus the frozen 100% gate, so the honest verdict is
`INVALID_DIAGNOSTIC_HISTORY_QUALITY_99_PERCENT`, not a clean completion.

A later Grok Build CLI pass plus independent position/context reconstruction
explained the failure without changing the source or reopening the hypothesis:
pre-commission PF was already 0.9007, the observed payoff required 53.79% wins
versus 46.90% achieved, and the +0.5R lock compressed 1,237 winners while 2,285
positions realized near-full stops. The active object was `SignalMode=0`; the
full displacement/FVG/MSS/retest/ADX state machine remained dormant. Twenty-four
hash-bound case charts (12 as-of, 12 anatomy) support the readout.

Historical same-broker cost provenance remains failed. No optimization,
post-hoc threshold loosening, promotion, paper or live attachment is
authorized. HYP-011's explicit 2023+ diagnostic access does not reopen any
sealed window for another hypothesis.

HYP-012 then tested a genuinely new bounded post-event state instead of a
static HTF filter. Control run `20260719_161929` reproduced the immediate-entry
economics; challenger `20260719_162104` waited up to three closed M5 bars for
rejection plus a strong decisive close. It produced 3,385 positions at PF
0.8104, -0.09799R/position, 7.592 trades/week, 3.335% diagnostic DD and zero
positive entry years, versus control PF 0.7588 / -0.13775R. Every measured
confirmation, sweep and completed H1/H4 bucket remained PF below 1. Both runs
had only 99% tester history quality versus the frozen 100% gate, so HYP-012 is
terminal `INVALID_DIAGNOSTIC_HISTORY_QUALITY_99_PERCENT_AND_KILL_CONTEXT_NO_EDGE`.
Forensics also found 37 weekend crossings caused by a tick-driven Friday
flatten defect. HYP-013 repaired that defect with a Friday 20:55 UTC
owned-position close and matching entry veto while preserving signal geometry.
All 37 diagnosed rows are subject to the new cutoff, but no hypothetical close
price or parent PnL was recomputed; the repair does not rescue the negative
alpha result.

HYP-012 readout:
`research/HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012_READOUT.md`.

HYP-013 Friday-safety readout:
`research/HYP-ICT-FVG-FRIDAY-SAFE-EURUSD-M5-013_READOUT.md`.

The subsequent HYP-014 diagnostic tested exactly one rolling annual
probability/no-trade policy over the 3,385 HYP-012 entries. It accepted only 15
of 2,551 evaluation opportunities (`0.044/week`) and remained negative at the
primary fixed cost: PF 0.9577 and -0.01577R/accepted trade. Pooled rolling AUC
was 0.4879; ten of fourteen frozen gates failed. Exact replay reproduced all
output hashes. Verdict `KILL_AT_ROLLING_OOS_DIAGNOSTIC_NO_CODE`: no probability
mode was added and the current source has no economic, paper or live authority.

HYP-014 readout:
`research/HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014_READOUT.md`.

HYP-014 outcome-disclosed high-score casebook:
`research/HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014_CASEBOOK_READOUT.md`.

HYP-015 now supplies the context surface that the previous EA was missing:
closed H1/H4 dealing ranges and confirmed structure, prior day/week and Asia
liquidity, H1/H4 swing pools, nearest directional draw-on-liquidity and room in
R, internal/external sweep classification, point-in-time partial H1/H4 candles,
and initiation/exhaustion measurements. It writes a separate outcome-blind
decision ledger before trade send and cannot alter the inherited trade policy.
The offline reference reproduced 3,385 unique positions with 99.084% complete
context and zero error on all six frozen H1 chart anchors. This is engineering
evidence only; it does not claim edge or authorize Model 0, paper or live use.

HYP-015 readout:
`research/HYP-ICT-FVG-HUMAN-CONTEXT-ENGINE-EURUSD-M5-015_READOUT.md`.

HYP-016R1 then collected the wider sweep/reclaim universe without opening
trades or reading outcomes. Its fixed natural policy opened HYP-017. The single
authorized HYP-017 Model-0 run produced 3,703 reconciled trades at native PF
0.7553 and -USD 5,107.84. With the frozen additional 1.5-pip diagnostic, PF is
0.3513 and expectancy is -0.52139R/trade; the week-block 95% CI is entirely
negative. Both sessions, directions and context states plus every 2018-2026
year lose. Verdict `KILL_AT_HYP017_MODEL0_NO_STABLE_EDGE`; the v1.23 source is
retained for audit only and has no rerun, paper, live or promotion authority.

HYP-017 readout:
`research/HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017_READOUT.md`.

Post-run visual review now uses `chart_case_render.v2`: the M5 anatomy panel
marks the exact pivot, sweep/reclaim, confirmation, entry and exit sequence
with distinct shapes and hash-bound timestamps/prices, while one selectable
M15/H1/H4/D1 panel shows completed HTF bars plus a hatched current HTF candle
aggregated only from source bars already closed at entry. In the frozen H1
anatomy review, the entry candle is centered at 50% width with 24 H1 candles
before and 24 after it. The full center candle and right half are explicitly
marked `POST-ENTRY OUTCOME`; the blue hatch preserves what that center candle
looked like at the exact decision cutoff.
The frozen review rendered six of six HYP-012 cases with all rule-chain and
entry/exit markers, centered-entry anchors, outcome disclosures and
decision-state cutoffs verified. Receipt:
`research/evidence/HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012_CONTEXT_VISUAL_V2_RECEIPT.json`.

Frozen full-chart contract:
`research/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_DIAGNOSTIC_PLAN.md`.

Terminal readout:
`research/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_READOUT.md`.

Trade-forensics readout:
`research/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_TRADE_FORENSICS_READOUT.md`.

Higher-timeframe C09/C10 quantification:
`research/HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_HTF_PAIR_READOUT.md`.
The frozen winner/loser pair is also among the closest short entries on
closed-bar M15/H1/H4/D1 context (combined rank 11/2,012; D1 rank 1/2,012),
while all measured HTF bias/pivot groups remain PF below 1. This is a
post-outcome no-rescue diagnostic, not a new strategy filter.
