# SF01 / F2 — BREAK-AND-RETEST — ROUND REPORT

**Verdict: DEAD** (screen v2, 20/20 configs, DESIGN 2016-2021)

Spec: `SPEC.md` v2 — ledger `spec_prereg` T000089
(sha `509529e81e3cbc3dad13691d52133f912e2430ea0fee322f4394cf66c13a5837`;
v1 T000071 superseded pre-outcome per D8).
Screen data: `SCREEN.json` (every config ledger-logged via pa_eval).

## What was tested

First pullback into a broken (or role-flipped) zone rejected in the break
direction; episode anchored at the break bar; stop order 1 pip beyond the
rejection bar; inv = pullback extreme snapped to the S ladder; TP = 2R.
Grid: 5 rungs x {line1_cluster, sd_base} x rej_body{0,1} = 20.
Session gate eu|us a priori (D3).

## Census (pre-outcome)

1,950 basket signals / 314 wk = 6.2/wk — below the 10/wk target; the
event (break -> retest -> reject, first pullback only) is structurally
sparse.  Snapshots: 12 PNGs rendered; geometry visually verified.

## Screen result (x1 costs)

| metric | best cell | range |
|---|---|---|
| PF x1 | 1.103 (S24/line1) | 0.71 - 1.10 |
| N fills | 258 max | 46 - 258 |
| t | +0.50 | -2.05 .. +0.50 |
| years PF>1 | 3 | 0 - 3 of 6 |
| symbols exp_r>0 | 3 | 0 - 3 of 4 |

Only ONE cell tops PF 1.0 meaningfully (S24/line1, PF 1.103, N=139 —
under the 300-fill gate and far under the 1.15 PF gate). Everything else
is PF 0.71-0.96 or noise on ~50 trades. rej_body produced zero
discrimination (identical N in every cell — a cross-out close almost
always has a directional body).

Note: the first screen run produced lift_pp=None because of the tag
convention bug (D9); re-run with tag=index for correct lift rows —
verdict stands regardless (PF/N gates fail outright).

## Diagnosis

The event is real but rare (M5 zone flips are sparse) and carries no
measurable edge at 2R with structural stops. Revisions considered:
per-touch episodes and wider retest windows would raise cadence but
dilute the "first pullback" hypothesis that is the family's entire
premise — not a rescue, a different bet. DEAD.

## Evidence files

- `SPEC.md`, `SCREEN.json`, `snapshots/` (12 PNGs)
- Detector: `families/f2_break_retest.py`; tests:
  `families/test_f2_break_retest.py` (all pass)
