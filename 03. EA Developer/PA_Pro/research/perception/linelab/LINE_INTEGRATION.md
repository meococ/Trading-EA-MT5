# L4 — LINE_INTEGRATION: what the build lane should change in `lines.py`

Measured baselines (all 198 TUNE panels; eval_v2 = official ruler
per R10, eval.py = legacy; lab = final config incl. stale-retire):

| engine | v2 recall | v2 prec | v2 trusted (n=141) | eval.py recall | ink med |
|--------|-----------|---------|--------------------|----------------|---------|
| v0 | 0.109 | 0.017 | 0.106 | 0.022 | 6.0 |
| v1 | 0.076 | 0.022 | 0.078 | 0.027 | 3.0 |
| lab  | 0.141 | 0.025 | 0.170 | 0.043 | 5.0 |

(Lead's baseline to beat per R10 §3: v0 0.10 / v1 0.09 — cleared.
Line sigma now 2.0p, Ruling 11 §11.3 / `REFINED_LINE_SIGMA`.)

v1 is NOT a regression in recall quality per se — it under-proposes
(3.0 lines/panel vs v0's 6.0) and selects poorly. The lab gains come
from a wider anchor universe + more trigger moments + lifecycle
anti-churn, all causal and all inside `lines.py`'s existing shape.

## Exact changes (proposer side)

**1. Let local-extreme anchors trigger `_eval`.**
v1: `_eval` returns early at `lines.py:81` (`if piv not in pool`),
so only DC-pivot confirmations ever propose — the named-bar anchors
it already builds (lines 49–70) are passive members. Lab fix
(`lines_lab.py update`): when bar `j = i - loc_ext_bars` completes
its ±k window and qualifies on side `sd`, run the same pair
evaluation with `piv = (t_ext=j, price=extreme, dir=sd)`.
Cost: ~1 extra `_eval` per few bars. This is the single biggest
coverage fix — golden's second anchors are often micro/local
extremes that never confirm as DC pivots (L2: mid/last touches are
θ1/loc-class ~60%).

**2. Add leg/session-extreme anchors** (`loc_sess_bars = 18`).
In `_pool`, alongside the ±k local-extreme test, also qualify bar j
if its defended-side extreme is the extremum over the trailing 18
bars ending at j (≈90min leg extreme — "the ~14:45 low").
Provenance: lab param; L2 sess-extreme share ~9%; R1 kill-audit
(9.19a#0-type misses). Causal (window ends at j, usable at j+k).

**3. `over` veto: `tol` → `2·tol`** (`over_veto_tol_mult=2`).
v1 vetoes any in-span pivot beyond 1·tol (`lines.py:133,143`).
Kill-audit: 22/86 missed golden lines were expressible pairs vetoed
at 1·tol; L1 hug4 p90 ≈ 6p shows golden tolerates defended-side
pokes. Overshoot stays in the score as a penalty, not a veto.

**4. `flat_drift` cap ×2 for slope-sign gate** (`slope_drift_mult=2`
→ effective 20p/span). 6/86 misses were mildly rising ceilings /
falling floors beyond ±10p — Volman draws gently drifting necklines.

**5. `span_max_min` 240→360.** L1 trusted-subset span max ~350min
(9.22c#0 is a ~6h rising line). `span_max_bars=96` already allows it.

**6. Birth floor on deduped touch *events* ≥3** (endpoints + ≥1 mid
touch). v1's `n_pt + n_anch ≥ min_touches` admits 2-anchor pairs.
R3 variants show nt_event≥3 keeps recall, ≥4 loses it (coverage
77→59). Golden touch median is ~5 — but most of that accrues after
the draw moment; ≥3 at birth is the right floor.

**7. Lifecycle anti-churn in `maintain`.**
- `pierce_dead_bars=2`: dead only after 2 consecutive closes through
  (1-bar poke = tease; L1: golden lines carry early pokes).
- `revive`: a new same-side pair matching a CLOSED line's geometry
  (≤2·tol at current bar, closed ≤48 bars ago) reopens that object
  instead of inking a new one — halves replace-churn ink.
- `reanchor_margin` 0.5→1.5.
- `stale_retire_bars=60`: retire an active line with no wick touch
  for 60 bars (~5h). Provenance: DR-MARKET FINAL v2 via R11 §2 —
  level premium ≈0 after ~5h untouched; Lead bound 48–96 bars.
  Companion fact: never close on a touch — 3rd+ touches on real
  pivot lines bounce +7–8pt over placebo (line lives through them).

## Selection score — honest flag for the Lead

Mandated protocol (day-level 5-fold AUC, ≥0.60 on every fold, ≤4
features, equal-weight ranks): **only `age_min` passes**
(0.73–0.85/fold, any-match). `struct_first` fails one fold (0.59);
everything else <0.60 somewhere. Under first-match (draw-moment)
labeling, nothing passes. So no honest multi-feature score exists —
consistent with DISAGREEMENT_2 and R9a's missing barrier term.
Recommendation: keep `score = nt − over/tol − age` as the proposer's
argmax key (unchanged family), and let **salience** own the volume
budget — the lab shows precision is dominated by lines/panel, and
per-panel budget is a salience job, not a line-route job.

## Tests to port

`linelab/tests/test_known_answers.py`:
- T1: synthetic clean rising 3+touch leg → a rising bottom
  PATTERN_LINE must be born (found: nt=6, slope 0.75 p/bar).
- T2: lone 25-pip down-spike in a flat market → no line may anchor
  on it (drawn=0).

## Expected deltas (measured on the same 198 panels)

- v2 recall 0.076 → 0.141 final config (0.163 if the Lead accepts
  R2's looser nt≥3/1·tol-over variant at 7.0 ink).
- eval.py recall 0.027 → 0.043.
- Precision ~flat (0.025 vs 0.022) at ~5 lines/panel until salience
  budgets; trusted-subset recall 0.078 → 0.170.
- Coverage ceiling: ~57% of scorable goldens expressible at <4p;
  ~23% have no anchor pair <8p (partly L1 'eye'-precision suspects).

## Summary (5 lines)

1. Open the trigger: every new anchor (pivot OR confirmed local
   extreme) proposes — v1's `piv in pool` early-return hides half
   the anchor universe.
2. Widen anchors: ±3-bar local + 18-bar leg/session extremes;
   spans to 360min.
3. Soften two vetoes: pivot-overshoot 2·tol, slope-drift 20p —
   golden tolerates both; keep them as score penalties.
4. Anti-churn lifecycle: pierce needs 2 closes, revive matching
   closed lines, margin 1.5 — kills replace-churn ink.
5. Selection stays heuristic: no causal feature survives the fold
   bar; give the volume budget to salience.
