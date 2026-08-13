# HYP-GC-OFI-INNOV-XAU-M5-003 — source-condition preregistration

Status: `OFFICIAL_DATASET_CONDITION_ONLY`. No TBBO aggregate, A/B/N count,
volume, session count, event count, cadence, XAUUSD price or economic field may
be opened by this step.

## Why this fresh successor exists

HYP001/HYP002 acquired the exact Q1-2019 TBBO/definition/status bytes. The
download emitted official warnings that some dates have reduced quality. The
v2 post-trade BBO wording was also non-executable for TBBO; Grok independently
accepted the single pre-trade-boundary v3 correction. HYP003 changes only these
source-engineering rules before any aggregate readout.

## Exact free query

- API: `Historical.metadata.get_dataset_condition`.
- Dataset: `GLBX.MDP3`.
- Half-open date range: `[2019-01-01, 2019-04-01)`.
- Exactly one metadata call; no timeseries or batch call.
- Persist the complete provider response in canonical JSON with hashes of the
  three acquired payloads and the v3 red-team receipt.

## Frozen condition policy

- A date labeled exactly `available` is source-eligible.
- Any other provider condition is source-unavailable, never imputed and never
  selected by outcome.
- All TBBO rows on an unavailable UTC date are excluded before side, BBO,
  transition, U, X or R aggregation.
- Unavailable dates create hard state resets on both boundaries. No transition,
  session, bin, sigma history or roll state may bridge them.
- The unavailable dates remain in the calendar denominator of every later
  cadence/year gate; they cannot be removed from the declared DESIGN window.
- This step has no maximum degraded-day threshold and no source PASS verdict.
  It only creates the point-in-time allowlist for a separately frozen analyzer.
- Missing dates, duplicate date rows or an unknown/malformed provider condition
  kill HYP003 before aggregate source access.

The policy handles a vendor outage as missing information rather than a trading
filter. It does not change any signal threshold or inspect whether the skipped
dates would have won or lost.
