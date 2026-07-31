# HYP-CME6E-RAWBREAK-BOOKTRANSITION-002 — Grok one-image-at-a-time review

Status: **24/24 INDIVIDUAL VISION JOBS ACCEPTED**  
Reviewer: **Grok Build `grok-4.5`, reasoning `high`**  
Epistemic class: **post-outcome forensic review; no rule authority**  
Date: `2026-07-27`

## Executive verdict

Grok inspected every frozen chart as a separate stateless backend job with
exactly one inline PNG. Twelve future-hidden decision charts were reviewed
first; only after those jobs were accepted were the 12 outcome anatomy charts
reviewed independently.

The blind phase is the material result. Grok returned `AMBIGUOUS` on 10/12
decision charts and made only two directional continuation predictions. One
was correct and one was wrong. It did not identify any blind chart as a likely
failure. Therefore an independent visual reviewer could describe risk and
context, but could not reliably distinguish winner from loser on this frozen
sample before the outcome was visible.

Once outcomes were disclosed, the paths were easy to classify: six clean
continuations (the six winners), three immediate failed breaks, and three
favorable-then-giveback losses. Grok assigned four of the six losses primarily
to setup/entry and two to exit management. This corroborates the parent
forensics: entry selection is the dominant failure layer, while giveback is a
real but secondary mechanism.

The terminal verdict remains
`KILL_DESIGN_BREAKBAR_BOOK_TRANSITION_NO_POSITIVE_EXPECTANCY`. The Grok review
does not authorize a filter, parameter change, rerun, promotion, paper, or live
action.

## Runner and image integrity

- Campaign: `HYP002_GROK_EACH_IMAGE_20260727`.
- Backend calls: 24; accepted first attempt: 24; retries: zero.
- Aggregate backend elapsed time: `1,304.441` seconds. Runner-reported usage
  cost: `USD 1.3906932` total (`USD 0.05794555` mean/job); this is runner
  usage metadata, not an independently audited invoice.
- Image contract: 24 distinct PNGs, exactly one ACP inline image per call.
- Order: `D01..D12` outcome-blind, then `O01..O12` outcome-visible.
- Every accepted summary: `success=true`, `EndTurn`, non-empty/useful response,
  `grok-4.5`, reasoning `high`, permission `auto`, no plan, no subagents, web
  disabled, `prompt_transport=acp_blocks_file`, image count one, schema PASS.
- Every result: exact case/job/image SHA identity, `image_opened=true`, and
  `no_rule_or_rerun_authority=true`.
- Mechanical campaign validation: 24/24 images opened and all runner/schema
  gates passed.

The local paths in the request metadata were not visual evidence. The runner
base64-embedded the PNG bytes into a hash-bound ACP prompt and verified the
decoded byte count against the source image before accepting each response.

## Blind decision review

| Job | Case | Grok freshness | Blind prediction | Confidence | Actual |
|---|---|---|---|---|---|
| D01 | F001 / PID2058 | MATURE | AMBIGUOUS | MEDIUM | WIN |
| D02 | F002 / PID1762 | MIXED | AMBIGUOUS | MEDIUM | WIN |
| D03 | F003 / PID1324 | MATURE | AMBIGUOUS | MEDIUM | LOSS |
| D04 | F004 / PID2166 | MATURE | AMBIGUOUS | MEDIUM | LOSS |
| D05 | F005 / PID1678 | MIXED | AMBIGUOUS | MEDIUM | WIN |
| D06 | F006 / PID1476 | FRESH | CONTINUATION | MEDIUM | WIN — correct |
| D07 | F007 / PID1282 | MIXED | AMBIGUOUS | MEDIUM | LOSS |
| D08 | F008 / PID1916 | MIXED | AMBIGUOUS | MEDIUM | LOSS |
| D09 | F009 / PID1598 | MIXED | AMBIGUOUS | MEDIUM | WIN |
| D10 | F010 / PID1412 | FRESH | AMBIGUOUS | MEDIUM | LOSS |
| D11 | F011 / PID1182 | FRESH | AMBIGUOUS | MEDIUM | WIN |
| D12 | F012 / PID1676 | MIXED | CONTINUATION | MEDIUM | LOSS — wrong |

The qualitative freshness labels also overlap outcomes. `MATURE` contains one
winner and two losses; `FRESH` contains two winners and one loss; `MIXED`
contains three winners and three losses. This balanced 12-case sample is too
small for a performance estimate, but it directly refutes a claim that Grok
could see a crisp pre-entry separation in these images.

Across the blind reviews Grok repeatedly noted plausible risk flags—late
decision timing, mature H1 recovery/decline, nearby M1 wick risk, mixed
structure, and weak/noisy book support—but correctly treated them as
non-decisive. It did not convert them into a post-hoc rule.

## Outcome anatomy review

| Job | Case | Actual path class | Primary layer | Confidence |
|---|---|---|---|---|
| O01 | F001 / PID2058 | CLEAN_CONTINUATION | WINNER_NO_FAILURE | HIGH |
| O02 | F002 / PID1762 | CLEAN_CONTINUATION | WINNER_NO_FAILURE | HIGH |
| O03 | F003 / PID1324 | IMMEDIATE_FAILED_BREAK | SETUP_ENTRY | HIGH |
| O04 | F004 / PID2166 | IMMEDIATE_FAILED_BREAK | SETUP_ENTRY | HIGH |
| O05 | F005 / PID1678 | CLEAN_CONTINUATION | WINNER_NO_FAILURE | HIGH |
| O06 | F006 / PID1476 | CLEAN_CONTINUATION | WINNER_NO_FAILURE | HIGH |
| O07 | F007 / PID1282 | IMMEDIATE_FAILED_BREAK | SETUP_ENTRY | HIGH |
| O08 | F008 / PID1916 | FAVORABLE_THEN_GIVEBACK | SETUP_ENTRY | HIGH |
| O09 | F009 / PID1598 | CLEAN_CONTINUATION | WINNER_NO_FAILURE | HIGH |
| O10 | F010 / PID1412 | FAVORABLE_THEN_GIVEBACK | EXIT_MANAGEMENT | HIGH |
| O11 | F011 / PID1182 | CLEAN_CONTINUATION | WINNER_NO_FAILURE | HIGH |
| O12 | F012 / PID1676 | FAVORABLE_THEN_GIVEBACK | EXIT_MANAGEMENT | HIGH |

Outcome charts make the path class obvious only after the future is visible.
They show two distinct loss mechanisms:

1. **Setup/entry failure:** F003, F004 and F007 fail to accept the break and
   reverse rapidly toward the stop. F008 obtains only a small favorable move
   before the late BUY impulse loses acceptance; Grok still places its primary
   defect at setup/entry.
2. **Giveback/exit management:** F010 and F012 first work in the intended
   direction, then surrender the favorable excursion and eventually hit the
   stop. This is visible path anatomy, not permission to add a breakeven or
   trailing rule to HYP-002.

## Book-trace finding

Grok independently found the displayed five-level book trace weak or
non-discriminating in all 12 outcome reviews:

- winners can have near-flat, negative-early, or only mildly positive book
  scores;
- losses can also have neutral or positive scores;
- F003 is the strongest counterexample: score `+0.323` remains directionally
  positive into a SELL that immediately fails;
- F012 retains mildly positive book values while the favorable path fully
  gives back into the stop.

This agrees with the population score-to-realized-R Spearman value `0.0627`.
The review does not support a different percentile or score-weight rescue.

## What this review establishes

**OBSERVED:** all 24 images were individually opened through the actual Grok
vision transport and every result passed a frozen schema.

**OBSERVED:** Grok could classify realized path anatomy with high confidence
after outcome disclosure, but treated 10/12 decision charts as ambiguous and
was only 1/2 on the two directional blind calls.

**STRONG INFERENCE:** the existing decision chart and frozen full-break-bar
book summary do not expose a visually stable continuation/failure separator.
The raw immediate first-close entry remains the primary mechanism weakness.

**UNKNOWN:** whether a materially later decision surface—post-break acceptance,
retest, replenishment, or same-venue CME execution—would add predictive state.
That requires a fresh hypothesis and population; it cannot be inferred from
these outcome charts.

## Evidence

- Campaign manifest: `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/grok_each_image_campaign.json`
- Validated campaign result: `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/grok_each_image_results.json`
- Per-job accepted packets: `research/evidence/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS/grok_each_image_validated/jobs/`
- Auditable runner artifacts: `.context/hyp002-grok-each-image-20260727/jobs/`
- Parent chart readout: `research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS_READOUT.md`
