# Prereg — HYP-REPLACE-ME

Status: draft until de-dup and the cheap offline probe are recorded. Freeze this
file and bind its SHA256 in the registry before any meaningful Model 0 run.

Versioning & immutability: once this file's SHA enters the registry it is
immutable — the validator re-hashes ALL historical rows. Pre-outcome
amendments become a new `_V2.md` bound at the next transition; never edit in
place. For a probe-state row, a frozen PROBE_PLAN
(`PROBE_PLAN.template.md`) IS the prereg: bind its SHA in the `idea|probe`
row before the probe runs.

Trial accounting & deflation: N = every executed simulation (controls and
failed arms counted; cost tiers x1/x1.5/x2 are NOT separate trials); verdicts
over a searched family use DSR >= 0.95 (`tools/research/dsr.py`).

## Identity

- Hypothesis ID: `HYP-REPLACE-ME`
- EA package: `EA_REPLACE_ME`
- Parent / independent mechanism:
- Source provenance:
- Feature family and overlap with killed families:
- Symbol / timeframe / frozen window:
- Role / MT5 model: `control|challenger` / `0`

## Trader thesis and quantified mapping

- Market behavior expected:
- Entry, exit, invalidation and session rules:
- Closed-bar decision point (`shift >= 1`) and earliest executable quote:
- Position ownership, restart recovery and hedging/netting behavior:

## Frozen decision surface

List every input override, including risk, magic number, cost assumptions and
telemetry tier. A missing cost field is `UNVERIFIED`, never zero cost.

## Acceptance and kill gates

- Minimum sample and elapsed-calendar-week cadence:
- PF / expectancy after verified x1, x1.5 and x2 cost:
- Maximum DD / tail / concentration:
- OOS / walk-forward / sensitivity requirements:
- Matched-control relative requirements:

## Probe and de-dup evidence

- `do_not_repeat_failures.md` families checked:
- Cheap offline probe result:
- Decision: `screened|parked|killed`

## Forbidden post-result edits

Any threshold, hour/day/year veto or mechanism change suggested by this
hypothesis's readout requires a new hypothesis ID. No post-hoc rescue.
