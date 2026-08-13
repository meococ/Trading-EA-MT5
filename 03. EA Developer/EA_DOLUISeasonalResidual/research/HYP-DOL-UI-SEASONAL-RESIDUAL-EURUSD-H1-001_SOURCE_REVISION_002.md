# HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001 - source revision 002

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Attempt `DOLUI001-SOURCE-001` terminated fail-closed after all 441 official
PDFs had been downloaded but before any ledger, source verdict, market-price
read or economic calculation. Its immutable terminal receipt is under
`research/evidence/HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001/DOLUI001-SOURCE-001`.

This document opens exactly one replacement source attempt,
`DOLUI001-SOURCE-002`. It inherits the source identity, formula, polarity,
archive cutoff, corpus, stage labels, cost limit and all prohibitions in the
original source-feasibility plan. It changes only the parser/source-availability
contract below. No target price or trading outcome was inspected when this
revision was written.

## Frozen correction catalog

An outcome-blind diagnostic pass over the failed attempt's raw official PDFs
found 434 parser-v1 successes and exactly seven failures:

- five PDF text layers split a word or a comma-grouped integer with an internal
  space; revision 002 may normalize only those lexical/text-layer artifacts;
- `2020/090320.pdf` and `2020/091020.pdf` publish the unadjusted actual change
  but do not publish the seasonal-factors expected change.

Only those two exact official URLs may have a missing expected-change field.
They must be retained with `source_availability=EXPECTED_NOT_PUBLISHED`, null
expected change and residual, and `direction=FLAT`. Any missing expected field
at another URL fails closed. An expected field appearing at either frozen
exception URL also fails closed because it would signal source drift.

The seasonally-adjusted prior-level qualifier may be `revised`, `unrevised`, or
not stated. `revised` still requires an explicit nearby old/new revision
lineage before the first initial-claims `4-week moving average` sentence;
revision wording from later insured-unemployment fields must not leak into this
field. `not_stated` is recorded literally and is not interpreted as
unrevised. This audit field does not enter the seasonal-residual formula.

## Replacement source gates

All original gates remain, except the former implicit 100% expected-field
availability is replaced by both of these exact gates:

1. 439 rows have `source_availability=SIGNAL_USABLE` and a non-null residual;
2. the exact two frozen 2020 URLs above are the only
   `EXPECTED_NOT_PUBLISHED` rows and both are `FLAT`.

The replacement attempt must again download 441/441 PDFs from the official
URLs into a new attempt-scoped empty raw root. Reusing the failed attempt raw
files as attempt evidence is forbidden. A PASS remains source feasibility only
and cannot establish an edge.
