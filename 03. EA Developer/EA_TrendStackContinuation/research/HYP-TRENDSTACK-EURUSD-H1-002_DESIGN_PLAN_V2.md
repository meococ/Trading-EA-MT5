# DESIGN OUTCOME PLAN V2 — HYP-TRENDSTACK-EURUSD-H1-002

Status: FROZEN 2026-07-28 before production request-plan generation, DESIGN M1
access, outcome, PnL, or economic metric.

This is a pre-outcome authorization amendment to
`HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN.md` SHA256
`06AB038A59A9CEEF3E47734E892CCC04A98F43D6E82B9373A2C8680EBB6DA0A9`.
All mechanism, indicator, clock, split, execution, cost, arm, trial, economic
gate, artifact, and verdict terms in that plan remain unchanged. V2 adds one
fail-closed authority binding only: the exact accepted Stage-0 DESIGN date set.

## Exact DESIGN date-set authority

The accepted Stage-0 eligibility ledger SHA256 remains:

`3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`.

Its strict `split == "DESIGN"` opportunity IDs form exactly 1,297 unique,
strictly increasing ISO dates from `2016-01-04` through `2020-12-31`.

Canonical date-set bytes are defined exactly as UTF-8:

```text
trendstack_002_design_date_set.v1\n
<opportunity_id_0001>\n
...
<opportunity_id_1297>\n
```

There is one LF after the version label, one LF after every ISO date including
the last, no BOM, no CR, and no extra field. Canonical byte length is 14,301.
The frozen SHA256 is:

`4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`.

The reviewed request-plan builder must derive this set from the accepted ledger
and emit the same date-set hash in its receipt. The canonical DESIGN run packet
must bind both the ledger SHA and this date-set SHA. Acquisition and evaluator
must independently recompute the date-set SHA from the entire request plan and
require the frozen value before `mt5.initialize` or any economic calculation.
Counts, first/last dates, and schema validity are necessary but not sufficient.

A self-authored run packet, request receipt, or 1,297-row interior date set with
a different canonical date-set hash is `INVALID_ENGINEERING`, even if every
other file/hash is internally consistent. It must not reach MT5 initialization,
M1 access, shard loading, or economics.

## Capability boundary

- Acquisition remains source-only and does not read feature, direction, ATR, or
  arm fields. The frozen date-set hash is its complete opportunity allowlist.
- Evaluator still joins only the accepted Stage-0/decision-packet chain and the
  exact date-authorized M1 shards.
- VALIDATION dates, all timestamps on/after 2021-01-01, HOLDOUT, Model 0,
  promotion, paper, live, and deploy remain unauthorized.
- The canonical create-new DESIGN run packet must bind this V2 file SHA256 and
  the exact final hashes of the reviewed request builder, acquisition tool,
  evaluator, request plan, request receipt, clock tool, and DSR tool.
