# R02 Deviation D43 — E2 pooled path looks up the wrong generator's values (KeyError 36182)

Status: RULED by the Lead, 2026-09-21 04:30Z. Option (ii) from ASK_LEAD.md (v3 section).
Scope: FREEZE_v3 (`f0462985…`), sealed runner `arrival_outcome_run.py` (`97e17afb…`), `arrival_estimate.py` (`103fdaa4…`).
Evidence: `research/arrival/_scratch/reexec_r02/d43_audit.py` + `d43_audit_output.txt`.
The audit reads only design-side inputs (the blind frozen bundles and the freeze hashes). It resolves no outcomes and prints no estimates.

## 1. What happened

Executor process B stopped at 03:38:14Z on unit #8 of the E2 family, `e2:fractal_h1|sd_base`, with `KeyError: 36182`.
The error was raised in `arrival_estimate._xprep` (line 213), called from `bootstrap_pooled` (line 439), called from `run_e2` (line 315). The full traceback is in ASK_LEAD.md.
- 25 unit files were written.
- 8 E2 units were not computed: #8 crashed and #9–#15 never started.
- `write_reports()` was never called.

## 2. Root cause

`run_e2` (arrival_outcome_run.py) loops over the symbols. In each iteration it sets `base = pt["grid"]` (line 292), and the per-cell point estimates correctly use `vals[sym][base]` (line 302).

After the loop, the pooled-bootstrap cell list is built like this (line 312):

```python
cl = [{"events": ev, "values": vals[sym][base][EP_KEY[ep]], ...}
      for sym, ev, ia_, m, w in cells]
```

`sym` and `ev` are unpacked from each cell. `base` is not; it still holds the value from the last loop iteration, which is **USDJPY's pair grid**. So for any cell whose own grid differs from USDJPY's:
- its events and arm indices come from its own grid generator;
- its `values` come from a different generator's event list.

`values` is a dict keyed `0..n_events-1` (`_resolve_symbol`). A misaligned index therefore either raises KeyError (index past the end) or silently picks up another event's outcome.

A pair's grid is the generator with more events in that symbol. The audit found this held in 60/60 pair×symbol cells, with no ties. The lookup is therefore wrong only when the denser generator flips between symbols.

## 3. Audit result (all inputs sha-verified equal to FREEZE_v3)

| Pair(s) | Grid per symbol | Effect of the stale `base` |
|---|---|---|
| 14 of the 15 pairs | same generator in all 4 symbols | none: the stale `base` equals every cell's own grid |
| #8 `fractal_h1\|sd_base` | EURUSD = fractal_h1 (36597 events vs sd_base 36171); GBPUSD/AUDUSD/USDJPY = sd_base | the EURUSD cell looks up sd_base values. 182 of its 15002 arm indices are ≥ 36171, and the first one reached is **36182**, the exact key in the executor's traceback |

- The failure is fully determined by the frozen inputs. A static prediction from the bundles reproduces the exact failing key.
- The executor's read-only description ("pair-arm index space does not line up with the resolved-event index space on this path") was right. D43 pins it to one line and shows that only one pair is affected.
- No silent misalignment occurred in any completed unit.

## 4. Impact

| Item | Status |
|---|---|
| E3 ×6, E1resid ×6, E1raw ×6 | **Unaffected.** Their cell lists index `vals[sym][gen]` with the function argument `gen`, not a leftover loop variable. |
| E2 #1–#7 (completed) | **Unaffected by D43.** The grid is identical in all 4 symbols. They keep the existing D42 label. |
| E2 #8 `fractal_h1\|sd_base` | NOT COMPUTED (crash). |
| E2 #9–#15 | NOT COMPUTED: the run aborted first. D43 would not have affected them. |
| CLAIM_VERDICT.md (E3 line1_cluster) | **Unaffected.** E2 is "flagging only" in FREEZE_v3 `claim_paths`. |

E2 coverage, using design-side eligibility (≥2 contributing cells, from gate_pass + pair_arms):
- 9 of the 15 pairs are eligible.
- R02 computed 3 of them: `line1_cluster|sd_base`, `fractal_h1|kde_swing`, `fractal_h1|profile_va`.
- The 6 eligible pairs lost are FR|SD, KD|SD, KD|RL, PV|SD, PV|RL and SD|RL.

A related latent issue was **not triggered**. `D_pooled` divides by the weight sum of *all* cells but sums only cells with a finite D, so a NaN cell would pull `D_pooled` toward 0. A value-blind check found 0 non-finite per-cell D among contributing cells in all 25 files.

## 5. Ruling: option (ii)

- R02 accepts the 25 completed unit files. The E2 family is recorded as **partial: 7/15 pairs computed, 3/9 eligible pairs**.
- There is no v4 re-freeze and no patched rerun inside R02.

Reasons:
- E2 is flagging-only.
- No claim rests on E2 or could be changed by it.
- The claim unit has already been reproduced bit-exact.
- A patched post-hoc run would be a non-preregistered analysis inside a closed round.

Re-executing `e2:fractal_h1|sd_base` alone (the planned "d3") is **dropped**. The audit predicts the exact failing key from the frozen inputs, which is stronger evidence than a rerun, and a rerun would take a python slot away from the SF lane.

## 6. Carried forward (R03 code base; sealed R02 code stays untouched)

1. **Fix.** Carry each cell's grid in its tuple, `cells.append((sym, ev, idx_all, mask, w, base))`, and use `vals[sym][b_]` in the comprehension. Alternatively, build `cl` inside the symbol loop.
2. **Fix.** In `D_pooled`, normalize only by the weights of cells with a finite D, or pre-register how NaN cells are handled.
3. **Regression fixture.** At least 2 synthetic symbols where the denser generator of a pair flips between symbols. Assert that every pooled cell reads `vals[sym][grid(sym)]`, and that the crash from this deviation cannot recur.
4. **Execution gate (Charter addendum 3) widened.** Before any freeze, run a synthetic end-to-end of **every** pre-registered unit path, not only the claim paths. The fixture must be heterogeneous across symbols: differing pair grids, a symbol with zero contributing cells, and a cell with one empty arm. D41, D42 and D43 all sat on non-claim paths that the gate never exercised.
