# Bond-Yield Panel Continuation Closeout — 2026-07-13 (Grok self-research)

Status: `BOND_DIFF_FAMILY_KILLED / USBILL_REMAINS_ACTIVE_COST_BLOCKED`

## Scope note

This closeout covers **sovereign bond-diff / EU curve** probes only. It does
**not** kill `V8_USBILL_SLOPE_USD_BASKET_V1` — that result file is
`PROBE_SURVIVOR` (see
`readouts/20260713_USBILL_SLOPE_STATUS_CORRECTION_V1.md`). Stale notes that
called USBILL a kill are superseded.

## What changed this continuation

Acquired/used hash-bound non-US bond surfaces, built lagged panels, ran
independent offline probes. Bond-diff/curve family killed. No threshold rescue.

| Probe | Train trades / tpw | PF-A (cand vs ctrl) | Verdict |
|---|---|---|---|
| `V8_USEU_10Y_DIFF_EURUSD_V1` | 224 / 1.07 | 0.579 vs 0.834 | KILL |
| `V8_USUK_10Y_DIFF_GBPUSD_V1` | 197 / 0.94 | 0.834 vs 1.076 | KILL |
| `V8_EU_CURVE_SLOPE_EURUSD_V1` | 217 / 1.04 | 0.773 vs 0.868 | KILL |

Acquisition receipt:
`preflight/v8_exogenous/manifests/20260713_V8_BOND_YIELD_PANEL_ACQUISITION_V1.json`

## Active lane (separate)

`HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001` = offline `PROBE_SURVIVOR`, registry
`probe`, prereg frozen — **COST_PROVENANCE_GAP** blocks EA/Model 0/GOAL until
QFSI on `FivePercentOnline-Real`. Cadence ~1/wk &lt; North-Star 2–5.

## Phase 0

Identity draft (225) still `DRAFT_NOT_FROZEN` /
`BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`. Cannot self-clear.

## Owner-only blockers

1. QFSI Real login / capture (unblocks USBILL Model 0 + USD-factor idea).
2. Free MT5 terminal if SB weekend-flat Model 0 still queued.
3. Clean Phase 0 freeze review.

## Authority

No registry/prereg/EA from the three killed bond probes. Do not retune. GPT
waived.
