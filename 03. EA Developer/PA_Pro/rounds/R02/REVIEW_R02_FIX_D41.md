# REVIEW_R02_FIX_D41 — adversarial fix review (gold-bean)

Reviewer: independent, outcome-blind. No real-data outcome computed, no
result file read. Revert-proofs ran on copies in `_scratch/fix_gate/`
with synthetic data only; no real file touched, nothing deleted.

## SUMMARY
- (a) CONFIRMED — D39(c) verbatim at PREREG.md:605-607 ("the sample-size-weighted mean of its per-symbol cell D's (`w_c` = the cell's observed contributing-event count)"); `cl` carries `"w": float(len(gb["treated"]))` (outcome_run.py:205-209 e3 / :245-249 e1resid) = the contributing-event count, and D39c's "recomputes the weighted mean in every replicate" under `bootstrap_pooled`'s fixed-weight mean (estimate.py:416-461, `p["c"]["w"]` at :457-458) requires an observed, replicate-invariant weight — `len(treated)` is exactly that.
- (b) CONFIRMED — `cl` is a list comprehension over `cells` itself (e3 :205, e1resid :245, e2 :311): same length, same order, element i derived from cells[i] — `zip(cells, cl)` pairing is correct by construction; truncation impossible. No explicit length assert exists, but none is needed: the invariant is structural, provable from the construction site.
- (c) CONFIRMED — `_json_default` (outcome_run.py:348-354) touches serialization only; `json.dump(res, f, default=_json_default)` (:363). No consumer reads unit JSONs back — grep finds no reader of `_scratch/r02_outcomes/`; `write_reports` (:387) consumes the in-process `results` dict. Replicates are used only in-process (p/CI computed in `_pack_boots` before serialization). float64→JSON→float64 is round-trip exact regardless.
- (d) CONFIRMED — the three tests (test_arrival.py:767/787/802) call the real `orun._run_unit` + `orun._write_unit` (only B/SYMS/OUT_DIR/ledger-path monkeypatched, :710-716); pytest: 3 passed. Bite-proven on `_scratch/fix_gate/` copies: defect-1 revert → `KeyError: 'w'` at e3 and e1resid, `ValueError: too many values to unpack` at e2; defect-2 revert (`default=float`) → `TypeError: only 0-dimensional arrays…` on all three units.
- (e) CONFIRMED — disk hashes match reported (runner 97e17afb…, tests 2e788fff…); FREEZE.json 1cd40018…, FREEZE_v2.json 5b2f4980…, PREREG.md 6d6c751c…, ledger 27 lines / 0 R02 rows all intact. One extra change beyond the three named files: `DEVIATION_D40` gained an addendum (mtime 00:02Z, before this fix's 00:31Z) — it is the authorized-edits account my v2 review (f) required; documentary only.
- (f) CONFIRMED — D41 states the defect was present in the v2-sealed runner (:20-23) and that no test exercised a claim unit end to end (:24-28, explicitly blaming the suite AND the v2 review); the `_write_unit` ndarray defect is recorded at :29-31 and in the changed-files list :78-81. It does not claim an unprovable introduction point — accurate.
FIX-GATE: OPEN

## Detail

### (a) D39c and the weight source

PREREG.md:605-607, verbatim: "(c) The generator-level statistic is the
sample-size-weighted mean of its per-symbol cell D's (`w_c` = the
cell's observed contributing-event count), and
`arrival_estimate.bootstrap_pooled` resamples DAY clusters
independently within each contributing cell … recomputes the weighted
mean in every replicate".

`cells` = bookkeeping tuples `(sym, gb)` (e3/e1resid) or
`(sym, ev, idx_all, mask, w)` (e2), appended inside `for sym in SYMS`
for contributing cells only. `cl` = the list of per-cell dicts
`{"events", "values", "treated"/"idx_all","is_a", "w"}` that
`bootstrap_pooled` consumes; `w` is set once per cell from
`len(gb["treated"])` (e3/e1resid) — the observed count of the armed
pool both arms are drawn from. The clause settles it: the weight must
be observed and fixed (the pooled replicate recomputes a *fixed-weight*
mean — a per-replicate post-trim weight is not implementable under that
spec), and `cl` is the only weight-bearing collection. Reading `w`
from `cells`' `gb` was both a crash and, had `gb` ever carried a "w"
key, a silently wrong source. CONFIRMED.

### (b) Zip alignment — the dangerous line

`zip(cells, cl)` cannot mispair: `cl` is produced by a list
comprehension iterating `cells` in order (e3 :205-209
`for sym, gb in cells`; e1resid :245-249 identical; e2 :311-315
`for sym, ev, ia_, m, w in cells`). A comprehension over a list yields
len == len and position-for-position correspondence — the i-th `cl`
element is a pure function of `cells[i]`, carrying that same `sym`'s
`gb`. Truncation is impossible (same length always); reordering is
impossible (single pass, same iterable). The `sym` used for the
`per_cell` lookup comes from the `cells` element; the `w` comes from
the `cl` element built from that same element. No `assert
len(cells)==len(cl)` exists — unnecessary given the construction, and
adding one would be belt-and-suspenders, not a correctness
requirement. CONFIRMED.

Flagged observation (pre-existing, sealed in v2, out of fix scope):
`run_e2` weights pair cells by `float(len(ia))` — arm-A count only,
not `len(idx_all)` = ia+ib. If D39c's "contributing-event count" is
read as both arms, this is asymmetric; if read as "the treated-arm
count" it is defensible. E2 is flagging-only and cannot carry a claim,
so nothing decision-bearing turns on it — but it wants a one-line Lead
ruling before any future freeze re-seals this code. Not a blocker for
this fix.

### (c) `_write_unit` change

`_json_default` (:348-354) maps ndarray→tolist, np scalar→.item(),
else float(). Used only as `json.dump`'s `default` (:363).
Serialization-only; no arithmetic, no estimand contact. Downstream:
no code anywhere reads `_scratch/r02_outcomes/*.json` back — the
report stage consumes `results` in-process (`write_reports(results,
…)` :387). p/lo/hi are computed by `_pack_boots` on the live ndarray
before serialization. Even if a file were read back, JSON float64
shortest-roundtrip reproduces the bits exactly. CONFIRMED.

### (d) Test quality + bite proof

Tests drive `orun._run_unit` → real `run_e3`/`run_e1resid`/`run_e2` →
real `bootstrap_*` → real `_write_unit` + `pa_ledger.append` (ledger
redirected to tmp_path). Only env constants are monkeypatched
(:710-716). Synthetic data, B=60 — outcome-blind preserved.

Bite proof on `_scratch/fix_gate/` copies (`bite_proof.py`), reusing
the test file's own synthetic builders:

| unit | fixed copy | defect-1 reverted | defect-2 reverted |
|---|---|---|---|
| e3:line1_cluster | OK | `KeyError: 'w'` | `TypeError: only 0-dim arrays…` |
| e1resid:sd_base | OK | `KeyError: 'w'` | `TypeError` |
| e2:line1\|fractal | OK | `ValueError: too many values to unpack` | `TypeError` |

The e2 revert was artificial (its site was never broken) and still
fails — every test bites on both defects. Real suite: `pytest -k
test_runner` → 3 passed, 24 deselected. CONFIRMED.

### (e) Scope

Disk sha256: runner `97e17afb…`, tests `2e788fff…` — both match the
report. FREEZE.json `1cd40018…`, FREEZE_v2.json `5b2f4980…`,
PREREG.md `6d6c751c…` unchanged; ledger 27 lines, 0 R02 rows; no
`r02_outcomes/` written. Mtime scan shows only: runner (00:31Z), tests
(00:30Z), DEVIATION_D41 (00:31Z, new), plus DEVIATION_D40 (00:02Z) —
the addendum my v2 review's item (f) required, documenting the
authorized post-23:18Z edits per file. Documentary only; disclosed.

### (f) Deviation honesty

D41 states: defect present in the v2-sealed runner (:20-23); the
v1-era run died inside the first unit and never reached the line
(:21-22, :68-70); no outcome was computed (:22-23); the 24-test suite
AND the independent v2 review both missed it because nothing executed
a claim unit end to end (:24-28, :70-74); the `_write_unit` ndarray
defect is recorded as incidental integrity-only (:29-31). It does not
overclaim provenance ("introduced by the rebuild" is unprovable since
the runner was not in v1's seal — the doc says "present in the runner
sealed by FREEZE_v2", which is the verifiable statement). CONFIRMED.
