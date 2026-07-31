# HYP-TRENDSTACK-EURUSD-H1-006 — PROBE PLAN V2

Status: `FROZEN_IDEA_AMENDMENT_PRE_OUTCOME`

This create-new V2 supersedes V1 SHA256
`2BFB0E0B3CF5F929ABE6320433A10C9DC84731A35E327E94F8D46D08CFD00FF4`.
Every V1 clause remains binding except where V2 explicitly replaces or narrows
it below. No source content, post-decision price row, return, PnL or performance
metric was opened before V2 freeze.

## 1. Source/economic capability separation

The HYP-006 source phase is governed by
`DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002_PLAN_V2.md`. Its source child
receives only a metadata-only 1,297-date allowlist and selected public DESIGN H1
bytes. It must not receive direction, M252, M6, alignment, eligibility, arm or
ATR. The accepted full Stage-0 feature projection is an input only to a future
separate evaluator after independent source PASS and a create-new economic
packet. No source artifact is an economic result.

## 2. Exact per-arm opportunity identity and counts

There is at most one opportunity per `arm × UTC date`; arms never overwrite or
collapse one another. Accepted DESIGN counts are frozen from HYP-002:

- `CONTROL_M252_ONLY`: `1,297` arm rows, direction M252;
- `CONTROL_M6_ONLY`: `1,292` arm rows, direction M6;
- `CHALLENGER_STACK`: `661` arm rows, direction M252 on agreement;
- `NEGATIVE_DISAGREE`: `631` arm rows, direction M6 on disagreement;
- total evaluated arm rows: exactly `3,881`.

Any count/join/identity mismatch is engineering invalid before an economic
verdict. Cadence gate 1 uses the 661 completed STACK trades divided by the frozen
260.571428571 elapsed weeks, subject to source completeness.

## 3. Direction-specific stop comparisons

- LONG entry bar (12:00): if `low <= stop`, exit at exact stop.
- LONG later bars (13:00 through 17:00): if `open <= stop`, exit at that adverse
  open; else if `low <= stop`, exit at exact stop.
- SHORT entry bar (12:00): if `high >= stop`, exit at exact stop.
- SHORT later bars (13:00 through 17:00): if `open >= stop`, exit at that adverse
  open; else if `high >= stop`, exit at exact stop.
- Equality is a stop touch. If no stop occurs, exit at the 18:00 BID open. Do
  not inspect 18:00 high/low; even an 18:00 open beyond stop is
  `TIME_EXIT_1800` at that open.

These clauses replace every ambiguous V1 phrase using generic `low/high` or
`adverse open` while retaining the same one-stop/no-TP chronology.

## 4. Exact cost tier for relative gates

All four relative gates use exact `1.50-pip net R` metrics:

9. STACK 1.50-pip PF minus the better standalone 1.50-pip PF `>= 0.15`;
10. STACK 1.50-pip mean net R minus the better standalone 1.50-pip mean net R
    `>= 0.05`;
11. STACK 1.50-pip PF minus DISAGREE 1.50-pip PF `>= 0.15`;
12. STACK 1.50-pip mean net R minus DISAGREE 1.50-pip mean net R `>= 0.05`.

The better standalone remains the separate maximum of M252 and M6 for the exact
metric being compared. V1 PF status/delta rules remain binding. Costs 2.25 and
3.00 pips are used only by absolute gates 3 and 4 and their arm diagnostics;
they cannot be substituted into gates 9–12.

## 5. Review and routing

All V1 ratio-minus-one, equality, directions, pip, PF, DSR, schema/BID, source
parentage, dormant DD/Monte-Carlo, no-rescue and sequential routing clauses
remain unchanged. This V2 grants no build/run authority until an independently
reviewed registry `idea -> probe` row binds both V2 SHAs.
