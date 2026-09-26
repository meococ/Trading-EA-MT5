# EVAL_AUDIT — independent ruler lane report

Lane: EVAL-AUDIT (mandate 2026-09-21 16:12Z + R9/R9a). Written 17:06Z.
Scope: TUNE v2 only (`golden/draft/BOOK2012_TUNE_v2.jsonl`, 198 panels),
bars via `golden/book_loader.py` only, no outcomes, no HOLD. All code in
`research/perception/evalcheck/`: `common.py`, `e12_selftest.py`,
`eval_v2.py`, `e4_bridge.py`, `test_ruler.py`, logs `e12_eval_py.log`,
`e12_eval_v2.log`, `test_ruler.log`, `_bridge_rows.jsonl`,
`bridge_report.md`.

Code state measured:

- engine v1 aggregate sha `504eb8ef53e5c492`
  (engine ccfaf8d4, swings 78850d5e, boxes a507540e, lines 18107ccc,
  levels b1ac1576, patterns c3ea8324, salience 79eb5811, gates 21449535,
  cet 4f5121f6, params_v1_1 ece4b071). The build lane changed
  salience.py + params_v1_1.json mid-audit; earlier rows in this
  session's notes used hash `1329055ca1916b2b` — superseded.
- engine v0 aggregate sha `63c771d64e18f619`
  (engine_v0 67176549, params_v1 9a8a2481).
- eval.py **post-R9.1** sha `8d016922aecae265` (t1 = `len(e.bars)-1`).
  The pre-fix state (t1 = `len(m)-1`, day end) is replicated verbatim in
  `eval_v2.eng_objects_pre_r91` for the before/after column — the file
  itself was never edited by this lane.

---

## E1 — self-test (golden v2 fed back as engine output)

Method: every usable golden object/mark is converted to the engine
record format (`common.gold_as_engine`) and matched against itself, per
panel, with the same greedy assignment as the production report.

| ruler | identical copy | realistic copy (bar-quantised, panel filter) |
|---|---|---|
| eval.py | recall **0.9946** (551/554) | recall **0.9729** (539/554) |
| eval_v2 | recall **1.0000** (545/545) | recall **1.0000** (545/545) |

eval_v2's denominator (545) excludes 9 golden objects/marks that lie
entirely outside the panel window — unscorable by construction
(`scorable()`). eval.py counts them and then loses the copies anyway.

eval.py self-test failures (all diagnosed to file:line in
`e12_eval_py.log`):

- 2 PATTERN_LINE `time_only` — `eval.py:208` requires the engine record
  to carry `p0`; a time-only golden line cannot supply one, so the
  object is unmatchable.
- 4 BAR_MARKER — `eval.py:240`: a point stamp judged by span
  IoU ≥ 0.3 can never pass (its span has zero width).
- 4 objects + 1 level + 3 marks dropped by the `eng_objects` window
  filter at `eval.py:114` — objects entirely before w0 / after w1 are
  still counted in the golden denominator.
- 2 LABEL_TF marks with `t=None` — `match_mark` computes
  `em["t_birth"] - gm["t"]` unguarded (eval.py:251ff).

## E2 — jitter test (recall at 0.5× / 1× / 2× label precision)

Every golden object perturbed inside its own precision flag
(eye ±5p/±10min, meas ±2p, repaired bar-anchored ±1.5p; line endpoints
jittered as (t,p) pairs, slope recomputed). 200 draws per object.

| type | n | eval.py @1× | eval_v2 @0.5× | eval_v2 @1× | eval_v2 @2× |
|---|---|---|---|---|---|
| BOX | 108 | 0.996 | 1.000 | 0.996 | 0.251 |
| BRACKET | 85 | 1.000 | 0.996 | 0.973 | 0.894 |
| CONTEXT_LINE | 9 | 1.000 | 0.972 | 0.963 | 0.616 |
| CONTEXT_RANGE | 6 | 1.000 | 1.000 | 1.000 | 0.266 |
| LABEL_TF | 60 | **0.786** | 1.000 | 1.000 | 0.685 |
| LEVEL_CARRIED | 48 | **0.749** | 1.000 | 1.000 | 0.505 |
| MINI_LEVEL | 31 | **0.889** | 1.000 | 0.992 | 0.494 |
| PATTERN_LINE | 184 | 0.970 | 0.996 | 0.990 | 0.569 |
| RANGE_OPEN | 8 | 1.000 | 1.000 | 0.986 | 0.227 |
| SQUEEZE | 2 | 1.000 | 1.000 | 1.000 | 1.000 |
| BAR_MARKER | 4 | — (unmatchable) | 1.000 | 1.000 | 0.752 |

Gate: eval_v2 recall at 1× ≥ 0.9 for every type — **pass**
(min = CONTEXT_LINE 0.963). The 2× column is diagnostic only: at twice
the promised label noise the ruler is allowed to degrade; it does so
gracefully (no cliff to zero except where the noise exceeds the object
itself, e.g. RANGE_OPEN spans ~20 min vs ±20 min time jitter).

eval.py's collapse at 1× on LABEL_TF (±5 min mark tol vs ±10 min label
noise) and LEVEL/MINI_LEVEL (2p flat tol vs 5p eye noise) proves its
tolerances are tighter than the yardstick can support — recall losses
there were ruler noise, not engine signal.

## E3 — eval_v2 rules (all tolerances tied to the precision flag)

- **Conversion (frozen, self-contained):** `eval_v2.eng_objects` —
  ACTIVE right edge = last **fed** bar `len(e.bars)-1`, then both sides
  clipped to `[w0, w1]` (engine AND golden; 33 golden objects have
  `t0 < w0`). Carries `meta_build_start/end` + `break_bar` through in
  minutes for the containment route.
- **BOX/RANGE_OPEN/CONTEXT_RANGE:** primary = **true IoU of
  containment windows** ≥ 0.5 — golden `build_start..build_end`
  (fallbacks `t0`,`t1`; degenerate point windows fall back to drawn
  span), engine `meta_build_*` (fallback `t0..break_bar`, then drawn
  span). Fallback route = engine drawn span covers ≥ 50% of the golden
  window. Both routes need both edges within the precision tol;
  `time_only` → span only.
- **PATTERN_LINE/CONTEXT_LINE:** shared span W = clipped spans'
  intersection, ≥ 25% of golden span (≥10 min, capped at half the span
  for very short lines). Both ends of W must agree within
  `σp + |slope_g|·10min` — endpoint-time noise projected through the
  line's own slope. Extension excluded. No endpoints → coverage + dir.
- **LEVEL_CARRIED/MINI_LEVEL:** |Δprice| ≤ σp AND ≥1 min overlap.
- **LABEL_TF:** |Δt| ≤ 10 min AND same side; `t=None` → side only.
- **BRACKET:** coverage ≥ 0.3 of the formation span AND same letter
  family (m/w/i stripped).
- **SQUEEZE:** coverage ≥ 0.3. **BAR_MARKER:** stamp within ±10 min of
  the golden mark window.
- Degenerate clipped engine spans (a point at the panel edge) score
  coverage 1.0 iff the point sits inside the golden span.

Known-answer tests (`test_ruler.py`, all pass — `test_ruler.log`):

- (a) ACTIVE box ending at w1: matches under post-fix eval.py and v2.
- (b) box closed at golden t1: matches under both.
- (c) same box stretched to 23:55: **fails** pre-R9.1 conversion,
  matches v2's clipped conversion.
- (d) engine claiming `t1_drawn = len(m)-1` is clipped to w1 by v2.
- (e) ACTIVE engine box vs golden drawn-closed-early: strict still
  fails it (drawn-span IoU 0.33); v2 matches via containment — the
  residual strict defect.

## E4 — bridge, 198 panels (recall; `bridge_report.md`)

Columns: Q2-loose = measure.py candidate-universe coverage; pre =
eval.py pre-16:28Z; now = eval.py `8d016922`; now+TI = same with true
IoU; v2 = eval_v2. Empty panels: **0/198** for both engines.
Clutter median: v0 8.00, v1 4.33.

engine v0:

| type | gold | Q2 | pre | now | now+TI | v2 |
|---|---|---|---|---|---|---|
| BOX | 111 | 0.95 | 0.07 | 0.26 | 0.23 | 0.21 |
| BRACKET | 85 | 0.36 | 0.08 | 0.13 | 0.12 | **0.73** |
| PATTERN_LINE | 186 | 0.84 | 0.01 | 0.02 | 0.02 | 0.10 |
| LEVEL_CARRIED | 48 | 0.23 | 0.06 | 0.06 | 0.06 | 0.17 |
| RANGE_OPEN | 8 | 0.75 | 0.12 | 0.62 | 0.62 | 0.38 |
| CONTEXT_LINE | 9 | 0.89 | 0.56 | 0.56 | 0.56 | 0.22 |
| LABEL_TF(marks=60) | — | — | 0.13 | 0.13 | 0.13 | 0.13 |

engine v1:

| type | gold | Q2 | pre | now | now+TI | v2 |
|---|---|---|---|---|---|---|
| BOX | 111 | 0.93 | 0.08 | 0.16 | 0.15 | 0.07 |
| BRACKET | 85 | 0.14 | 0.01 | 0.01 | 0.01 | 0.07 |
| PATTERN_LINE | 186 | 0.88 | 0.03 | 0.03 | 0.03 | 0.09 |
| LEVEL_CARRIED | 48 | 0.50 | 0.08 | 0.08 | 0.08 | 0.10 |
| MINI_LEVEL | 32 | 0.47 | 0.09 | 0.09 | 0.09 | 0.06 |
| RANGE_OPEN | 8 | 1.00 | 0.12 | 0.25 | 0.25 | 0.25 |
| CONTEXT_RANGE | 6 | 1.00 | 0.00 | 0.00 | 0.00 | 0.17 |
| LABEL_TF(marks=60) | — | — | 0.06 | 0.06 | 0.06 | 0.08 |

BOX route provenance (BOX+RANGE_OPEN+CONTEXT_RANGE matches under v2):

- v0: containment_iou = 18, coverage = 10; **10/10 coverage matches
  would fail true containment IoU ≥ 0.5.**
- v1: containment_iou = 3, coverage = 8; **8/8 coverage matches would
  fail true containment IoU ≥ 0.5** (e.g. 9.40c: engine window
  760–790 vs golden 905–960, IoU 0.00 — same edges, different
  formation).

## Ruler bugs found (in `eval.py`)

1. **Day-end stretch (R9.1, fixed in-file at 16:28Z):** ACTIVE objects
   converted with `t1 = len(m)-1` — the last bar of the day, ~430–830
   min past the panel edge. Effect: v0 BOX strict recall 0.07 → 0.26,
   v1 0.08 → 0.16 after the fix alone.
2. **No left clip:** engine `t0 < w0` never clipped; golden `t0 < w0`
   exists on 33 objects. Spans compared off-window asymmetrically.
3. **Non-true IoU:** `iou()` = intersection / max(len), asymmetric and
   generous when one span swallows the other. True-IoU column shows a
   small further drop (v0 BOX 0.26 → 0.23).
4. **BOX judged on drawn span:** conflates drawn edge with containment
   (D9). Even post-fix, strict fails an ACTIVE box whose golden twin's
   drawn edge closed early (known-answer e) and cannot see that v1's
   containment windows diverge — v2's 8 coverage-route matches all sit
   below true IoU 0.5.
5. **Unscorable golden counted:** objects/marks entirely outside the
   panel stay in the denominator (E1 identical-copy ceiling 0.9946).
6. **BAR_MARKER unmatchable:** span-IoU on a zero-width event.
7. **`time_only` lines unmatchable:** `eval.py:208` hard-requires `p0`.
8. **Tolerances tighter than label noise:** flat 6p/3p, mark ±5 min —
   E2 collapse at 1× on LABEL_TF/LEVEL_CARRIED/MINI_LEVEL.
9. **`match_mark` unguarded `t=None`** subtraction.

## Proposed §6.1 text changes (proposals only — spec untouched)

- Replace "time IoU" with **"intersection-over-union of the two spans,
  both clipped to the panel window [w0, w1]"**.
- BOX row: "time agreement on the **containment window**
  (`build_start..build_end`, fallbacks `t0`,`t1`; degenerate windows
  fall back to drawn span) via true IoU ≥ 0.5; coverage ≥ 0.5 of the
  golden window is acceptable only when one side records no window."
- Line rows: "evaluate price agreement at both ends of the **shared
  pre-break span** (≥25% of golden span, ≥10 min); tolerance =
  `precision σp + |slope|·10min`; drawn extension is not scored."
- Level rows: "price within `σp` of the flag AND ≥1 min time overlap."
- Mark row: "|Δt| ≤ 10 min AND same side; missing time → side only."
- BAR_MARKER: "engine stamp within ±10 min of the mark window."
- Add: "objects/marks lying entirely outside the panel window are
  excluded from the denominator and counted as unscorable."
- Add: "report the match-route counts (containment-IoU vs coverage
  fallback) alongside BOX recall."

## Recommendation

**Adopt `evalcheck/eval_v2.py` as the official ruler.** It is the only
instrument here that passes its own calibration (E1 = 1.0000 identical
AND realistic, E2@1× ≥ 0.96 on every type), implements the D9
containment semantics the golden audit established, satisfies R9/R9a
(clipped frozen conversion, true IoU, two-route BOX matching with route
provenance), and ships known-answer regression tests. Keep `eval.py`
read-only as the legacy column in the bridge for continuity; do not
tune the engine against it further.

Honest caveat for the build lane: v2 is a *stricter* ruler on BOX for
v1 (0.07 vs strict 0.16) because it measures containment, not ink —
the drawn-span matches it discards genuinely fail containment IoU.
That is the semantics the spec describes; the low number is engine
truth, not ruler noise.

## 5-line summary for the build lane

1. Official ruler = `evalcheck/eval_v2.py` (pending Lead sign-off);
   `eval.py` stays as a legacy column only.
2. Your BOX score is 0.07 v2 / 0.16 strict — containment windows
   (`meta_build_*`, propagated via `salience._birth`) diverge from
   golden `build_start..build_end`; only 3/11 matches survive true IoU.
3. PATTERN_LINE is judged on pre-break anchors + slope on the shared
   span — v1 draws them (Q2 0.88) but anchors/slope agree only 0.09.
4. BRACKET regressed hard vs v0 (0.73 → 0.07): v1 draws fewer/wrong
   formation spans; letters alone won't match without ≥30% coverage.
5. Bars-side work is fine — engine is never empty; the gap is
   geometry/timing semantics, not detection.

---

## Addendum — Ruling 11 revision (2026-09-21 ~17:56Z)

The Lead's Ruling 11 revised the official ruler; EVAL-AUDIT implemented
it.  Ruler hashes now: `eval_v2.py 50e11fd5a2ab7974`,
`common.py c6b3fa0d28713204`.

- **§11.1 BOX rule**: match = true IoU of containment windows >= 0.5 +
  both edges within tol; coverage fallback only when a side recorded no
  window at all (route still counted).  New diagnostic `box_located`
  (ovcoef >= 0.5 + edges) — reported beside recall, never a match.
- **§11.2 funnel**: prefix-consistent `cand_right` for candidates
  (BOX: edges + start within 20min of build_start + i <= build_end+10;
  line: two-point on shared span + i <= t1; level: price + i in span).
- **§11.3 line sigma**: repaired lines 1.5p -> 2.0p (trusted hug4
  p95 = 2.0p); Tier-A 44 suspect labels -> `line_tierA.json`, trusted
  subset (n=141) reported alongside in the bridge table.
- Gates after the change: E1 1.0000 both copies; E2@1x min 0.949
  (all types >= 0.9); test_ruler +3 R11 cases PASS.
- Re-baseline (bridge_report.md, v1 engine now `cf2a7c1abc3c21d6`):
  v0 BOX 0.21 / located 0.23; v1 BOX 0.05 / located 0.06;
  PATTERN_LINE trusted: v0 0.11, v1 0.08.
- Funnel under §11.2: v0 BOX oracle 0.31 / born 0.21; v1 BOX oracle
  0.31 / born 0.05, PATTERN_LINE oracle 0.40 / born 0.08 — the v1 gap
  is selection, not geometry or tolerance.
