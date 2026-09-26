# DEVIATION D41 — RUNNER CELLS DEFECT (R02-M)

## SUMMARY

- The executor found `KeyError: 'w'` at
  `research/arrival/arrival_outcome_run.py:211` (run_e3 pooled
  numerator) — the identical defect sits at :251 (run_e1resid).
  `run_e2` at :317 was already correct.
- Both lines summed over `cells` — a list of `(sym, gb)` bookkeeping
  tuples, where `gb` has no `"w"` — instead of `cl`, the per-cell
  dicts carrying the pinned weight.
- Prereg clause that settles it, verbatim (D39(c), §0): "The
  generator-level statistic is the sample-size-weighted mean of its
  per-symbol cell D's (`w_c` = the cell's observed contributing-event
  count)". See also D29(d): "every symbol-cell contributing to the
  claim" = exactly the cells whose D_sym enters the pooled D.
- `cl` is built exclusively from `cells` (contributing cells only)
  and carries `w = len(treated)` = the pinned `w_c`; the fix pairs
  `zip(cells, cl)`, matching `run_e2`.
- The defect was present in the runner sealed by FREEZE_v2 (the v1-era
  run expired after 57 min inside the first unit and never reached the
  line). No outcome was ever computed: TRIALS.jsonl = 27 lines, no
  `r02_outcomes/` files, no RESULTS.md.
- Neither the 24-test suite nor the independent v2 review caught it —
  nothing executed a claim unit end to end. That gap is closed by
  `test_runner_e3_unit_end_to_end`,
  `test_runner_e1resid_unit_end_to_end` and
  `test_runner_e2_unit_end_to_end` (synthetic data only, B=60).
- Incidental, integrity-only: `_write_unit` needed a JSON default for
  the retained `boots` ndarray (the mandated per-unit write could not
  otherwise complete). No estimand touched.
- No freeze file written or modified; no ledger row appended in the
  real ledger; no real-data outcome computed.

## DETAIL

### The defect and the fix

`run_e3` (was :211) and `run_e1resid` (was :251) both read:

    num = sum(c["w"] * per_cell[sym][ep]["D"] for sym, c in cells
              if np.isfinite(per_cell[sym][ep]["D"]))

`cells` is a list of `(sym, gb)` tuples — `c` bound to the bundle dict
`gb`, which has no `"w"` key -> `KeyError: 'w'` the moment any cell
contributes. `cl` is the list built immediately above from `cells`:

    cl = [{"events": gb["events"], "values": ..., "treated": ...,
           "w": float(len(gb["treated"]))} for sym, gb in cells]

— the per-cell record `bootstrap_pooled` consumes, carrying `w_c`.
The corrected lines (identical shape to `run_e2`'s :316-318):

    num = sum(c["w"] * per_cell[sym][ep]["D"]
              for (sym, *_), c in zip(cells, cl)
              if np.isfinite(per_cell[sym][ep]["D"]))

`zip(cells, cl)` iterates exactly the contributing cells (cl is built
only from cells), takes `w_c` from `cl`, and the symbol name for the
`per_cell` lookup from `cells`. Which collection is iterated
determines which cells contribute — under D39(c)+D29(d) the pooled
statistic sums `w_c * D_sym` over contributing cells only, so `cl`
(the weight-bearing, contributing-only collection) is the required
source of `w`, and `cells` supplies `sym`.

### Why it was missed

The v1-era run spent its entire box life inside
`bootstrap_e3(EURUSD)` — the crash site sits after all per-cell
bootstraps and the pooled bootstrap, so it was never reached. The
unit suite exercised `bootstrap_pooled`/`e3_D`/`resid_D` directly but
never `run_e3`/`run_e1resid`/`_run_unit`; the review verified hashes
and semantics, not execution. Fix now proven by synthetic end-to-end
tests for all three unit kinds.

### Files changed under this ruling

- `arrival_outcome_run.py`: the two numerator lines; `_write_unit`
  default serializer (`_json_default` — ndarray/np-scalar -> JSON).
  Nothing else.
- `tests/test_arrival.py`: three new end-to-end unit tests appended.
