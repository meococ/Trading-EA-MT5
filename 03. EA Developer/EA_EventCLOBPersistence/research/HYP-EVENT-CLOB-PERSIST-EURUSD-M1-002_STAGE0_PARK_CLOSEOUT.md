# STAGE 0 PARK CLOSEOUT — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002

Status: terminal for this hypothesis at Stage 0B-D on 2026-07-28.

Verdict: `PARK_STAGE0B_DESIGN_SOURCE_OR_CADENCE`.

This is an engineering-valid, outcome-blind source-quality and feature-supply
failure. It is not a market no-edge verdict. Stage 1, EURUSD outcomes,
validation-source purchase, `.mq5`, MT5, promotion, paper and live are forbidden
for this hypothesis.

## Frozen authority and acquisition evidence

- Owner ceiling: USD 3.50 for plan
  `DEDDE7F292738C16A200C59903F7839C85B728818805AA09D46D3E7F188E0C16`.
- Live estimated source cost: USD 3.141317501659. This is vendor estimate
  evidence, not an invoice-verified actual charge.
- Download manifest SHA-256:
  `9438133803AF33E52C641DF149D04AA8E1CA8B1DD5A510795E0B55C3D2698229`.
- Acquisition authority receipt SHA-256:
  `15D2878DA8F461219E29DBBDD34B42F8B74116DB6B7A1EA9F5AF060748A4FA13`.
- All 658 request identities completed exactly once; 652 nonempty DBNs and six
  explicit source-empty DBNs were retained under the canonical D-side root.
- No validation-period source or EURUSD price/outcome was acquired or opened.

## Reviewed Stage 0 execution snapshot

- Base Stage 0 task packet SHA-256:
  `5B4B636AB925E6579F4B5084339EC6E5E613266F3384C4CDA34B0D4D73FDA588`.
- V2 integrity amendment SHA-256:
  `6658ED3EFF6323F29DC99E8B2A8BF2A38A776FBA3AC63D0692CDC1F077870CDD`.
- V3 stable-handle amendment SHA-256:
  `7F42B75E19A5AB2AA3FDE714F815671EBC063A54098C941F69A3533CC8C2ED37`.
- Reviewed analyzer SHA-256:
  `FAB30F1418C953B16D28F4849C87F5A4802A9878D37ECD1CCB9BFDF6972D63B3`.
- Reviewed tests SHA-256:
  `AF085832B419DD120B9FB7F02DE875E8B143526E36DEA7AA8939138BCB27BE20`.
- Parent-owned launch receipt SHA-256:
  `E12F68C64A4439BA3A8E883656220EBA46B850A77AA4B552F1EB95C498312462`.
- Dedicated-runtime focused suite: 50/50 PASS before live execution.
- Runtime: Python 3.12.10, Databento 0.54.0, local `DBNStore.from_bytes`
  decoding only; network, paid-call and remote-client surfaces were absent.
- Independent V3 review reproduced and closed all declared path, reparse,
  mutation and handle-identity races before authorizing the first live run.

## Frozen Stage 0 artifacts

- Event feature ledger:
  `02. AlphaFactory/data/databento/cme_6e_event_clob_design_segments/stage0_event_feature_ledger.csv`
  — SHA-256
  `0E8DC009DE57563E911375F5CD069DD96470DF0115B25110AAA32DA2052BB57D`.
- Source-quality manifest:
  `02. AlphaFactory/data/databento/cme_6e_event_clob_design_segments/stage0_source_quality_manifest.json`
  — SHA-256
  `B30971C99FB74BD0319BC8348BC59EF3B7C9A9AF585D3AD2B7971BA471D3A2BE`.
- Stage 0 readout:
  `03. EA Developer/EA_EventCLOBPersistence/research/HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_SOURCE_READOUT.md`
  — SHA-256
  `E23E4C0A324BEAB27493347A582AA6196F21F1E47C6470D84BB52F8E2DF3BA43`.
- Independent non-publishing replay reproduced all three artifacts byte for
  byte and found zero source-binding, reason, formula or aggregate mismatch.

## Gate results

| Gate | Frozen result | Verdict |
|---|---:|---|
| Request identities | 658/658 | PASS |
| Event pairs | 329/329 | PASS |
| PRE nonempty coverage | 326/329 = 0.990881 | PASS |
| LATE nonempty coverage | 326/329 = 0.990881 | PASS |
| Paired nonempty coverage | 326/329 = 0.990881 | PASS |
| Source-quality paired events | 1 | FAIL |
| Feature-eligible events | 1, minimum 209 | FAIL |
| Eligible cadence | 0.009576/week, required 2.0–5.0 | FAIL |
| Fatal event-clock bound cases | 11, required 0 | FAIL |
| Prohibited reads/calls | all zero | PASS |

The sole eligible event was `EVT0103`, direction LONG. It does not authorize an
economic probe because the frozen population and cadence gates failed.

## Failure anatomy

- `MAX_GAP_GT_1S`: 488/652 nonempty segments. PRE failed this gate in 325/326
  segments and LATE in 163/326. Median maximum gap was 1.813076258 seconds;
  P95 was 4.326456024 seconds. These were real event-driven MBP silence gaps on
  both `ts_event` and `ts_recv`, not decoder or scale errors.
- `FINAL_STALENESS_GT_1S`: 61 segments.
- `TS_EVENT_OUTSIDE_HALF_OPEN_SEGMENT`: 149 records in 11 segments. All 149 had
  `ts_recv` inside the requested half-open interval, while `ts_event` was up to
  12.971223 ms before start or 1.515991 ms after end. Vendor range selection was
  receive-clock consistent; the frozen feature contract required event-clock
  containment and therefore correctly failed these events.
- Other recorded reasons were explicit source-empty, two record-count failures
  and two LATE spread failures. None changes the terminal population result.

## Lead/process retrospective

What worked and should be retained:

- The spend ceiling, exact request identities, hashes, source custody and
  outcome seal were enforced. The terminal verdict is reproducible and did not
  consume EURUSD outcomes to rescue a weak source population.
- Coverage, source quality, feature eligibility and economics remained separate
  gates. The source failure was not mislabeled as market no-edge.

Objective weaknesses in the research lead's execution:

1. The one-second maximum inter-record-gap rule was frozen without first proving
   that this threshold represented missing data rather than legitimate silence
   in an event-driven MBP feed. It became the dominant exclusion mechanism, so
   the source contract—not the imbalance mechanism—decided almost the entire
   population.
2. The work sequence was too expensive. A tiny outcome-blind, representative
   acquisition could have measured inter-arrival, final-staleness and
   `ts_event` versus `ts_recv` boundary behavior before the full 658-request
   design purchase was authorized.
3. The shorthand "1/329 signals" was imprecise. The correct state was one
   `feature-eligible event`; it was not a trade, a winner or an economic signal.
   This wording obscured why no EA was built and overstated progress toward the
   Owner's outcome.
4. Engineering-valid acquisition was allowed to dominate the session narrative
   even though the Owner's actual goal—an economically tested EA—remained
   unmet. Future status reports must lead with the product/economic state, then
   explain the engineering evidence.

Corrective controls for future hypotheses:

- Before a paid/full event-driven acquisition, run a minimum-cost outcome-blind
  source-semantics pilot on a preregistered representative sample. Measure the
  inter-arrival distribution, tail staleness, clock used by the vendor's range
  selector and expected pass rate of every proposed source-quality threshold.
- Every source-quality threshold must state its physical meaning, the failure it
  detects and how it distinguishes missing/corrupt data from legitimate market
  inactivity. If that distinction is unknown, the threshold is exploratory and
  cannot govern a full purchase yet.
- Use explicit funnel vocabulary in reports:
  `request -> nonempty segment -> source-quality event -> feature-eligible event
  -> executable trade -> economic survivor`. Never collapse these states into
  the word "signal".
- Stage spending as free metadata/quote -> minimal paid semantics pilot ->
  frozen full-design contract -> economic probe. A pilot PASS may authorize the
  next stage; it never authorizes PnL, EA build, promotion or live trading by
  itself.

These controls apply prospectively. They do not reopen HYP-002 or authorize
relaxing its frozen gates.

## Failure radius and prohibited rescue

The closed object is the exact 2019–2020 scheduled point-release population,
`GLBX.MDP3` `mbp-10` `6E.v.0`, PRE `[T-60,T-15)`, LATE `[T+45,T+60)`, top-five
median `I5`/delta/sign rule, and the frozen one-second gap/staleness plus exact
event-clock containment gates.

Do not reopen this ID by relaxing gap, staleness, bounds, spread, record count,
source-quality coverage, segment bounds, event subsets or sign persistence. Do
not open EURUSD outcomes, purchase 2021–2022 validation source, or build MQL5
"just to see." A successor requires a materially new mechanism/data contract
or decision surface, fresh de-dup, a new hypothesis ID and preregistration.

The Owner's broader goal remains unmet. The next safe lane must be a distinct
candidate rather than a repair of this terminal Stage 0 object.
