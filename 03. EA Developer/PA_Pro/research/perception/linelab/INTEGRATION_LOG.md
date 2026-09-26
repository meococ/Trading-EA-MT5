# INTEGRATION_LOG — LINE-LAB mandate 2 (L5 port / L6 measure / L7 / L8)

18:05Z — rulings read up to R12 at 18:05Z. Ruler pins: eval_v2
50e11fd5, common c6b3fa0d, eval.py 8d016922, book_loader b40c2cab.
Ownership: lines.py + pattern_line/context_line sections of
params_v1_1.json (str_replace only). Queue: L5 port L4 items 1-7 +
T1/T2 tests, keep suite green; L6 full-engine all-types under
eval_v2; L7 coverage; L8 selection.


18:26Z — L5 port complete.

Changed (lines.py, engine hash cf2a7c1abc3c21d6 -> 694313a38abc2da6):
1. open trigger: proposals fire on ANY new confirmed anchor
   (theta1/theta2 pivot OR loc-extreme), not only on DC pivots.
2. anchor pool += session/leg extremes via _is_loc_ext
   (loc_sess_bars=18 window, +-loc_ext_bars confirmation).
3. over-pivot veto relaxed: overshoot <= over_veto_tol_mult*tol (2.0).
4. slope drift tolerance: |slope-sign flips| within
   slope_drift_mult (2.0) x per-pair slope.
5. span_max_min 240 -> 360 (long golden lines ~350min).
6. min_touch_events=3 birth gate (Volman 3-point rule).
7. anti-churn: revive recently-closed same-geometry line
   (revive_max_age_bars=48, reanchor_margin=1.5); pierce needs
   pierce_dead_bars=2 consecutive closes; last_touch tracked;
   stale_retire_bars=60 closes untouched lines; decisive break
   spawns broken_line_edge LEVEL_CARRIED candidate.

Params (all with provenance entries, str_replace edits only):
pattern_line.{span_max_min:360, over_veto_tol_mult:2.0,
slope_drift_mult:2.0, reanchor_margin:1.5, pierce_dead_bars:2,
stale_retire_bars:60, revive_max_age_bars:48, loc_sess_bars:18,
min_touch_events:3}.

Pre-existing test changes (R12 section 2 log):
- t_lines_rising_hull: OLD fixture zigzag([1.3280,1.3310,1.3285,
  1.3320],6) = 2 lows -> under the >=3 touch-event rule no line
  can legitimately form. NEW zigzag([1.3280,1.3310,1.3285,1.3320,
  1.3290,1.3330],6) = 3 ascending defended lows. Assertion
  unchanged (bottom line, slope>0). Intent preserved: the test
  still proves rising lines anchor on the lower hull; the longer
  fixture only supplies the third touch the new rule requires.
- t_lines_falling_hull: same extension, mirrored
  ([1.3320,1.3290,1.3315,1.3280,1.3310,1.3275],6); assertion
  unchanged (top line, slope<0).
- t_levels_broken_line_edge: OLD zigzag 5-leg bpl=4 gave a
  2-touch line whose traverse died in ONE bar; NEW zigzag 7-leg
  bpl=3 + flat(20) tail gives a >=3-touch line, pierce requires
  2 consecutive closes (pierce_dead_bars=2), and the flat tail
  lets the broken_line_edge candidate through salience.
  Assertion unchanged (broken_line_edge LEVEL_CARRIED exists).
  Intent preserved: pierced-line carry still tested; fixture now
  satisfies the lifecycle the spec already described.
- NEW t_lines_three_touch_rising_known_answer (lab T1 port):
  asserts detection at proposal layer via cand_log plus geometry
  on any born object — salience rate_total can legitimately
  refuse births in a busy fixture; the line grammar itself is
  what this test owns.
- NEW t_lines_lone_spike_no_line (lab T2 port): unchanged from
  lab; no line may anchor on the spike extreme.

Test bug fix (R12 section 4): tests/test_engine.py:158 and
tests/test_engine_v0.py:159 computed
px=(g["p0"]+g["slope"]*(i-g["t0"]))/P = ~1.3e8 (p0 already in
pips). Fixed to *P in both files; intent (drive a close through
the line) unchanged. v0 code untouched.

Test counts: test_engine_v1.py 32 -> 34 tests, 34/34 PASS
(3 fixture regressions found and fixed as above).
tests/test_engine.py 23/23 PASS after scale fix.
tests/test_engine_v0.py 23/23 PASS after scale fix — v0 still
green, confirming the fix is a test repair not a behavior change.

18:32Z — L6 full-engine measure, eval_v2 50e11fd5, 198 TUNE panels.
Engine hash v1 after L5 = 694313a38abc2da6 (before = cf2a7c1abc3c21d6,
the R12 baseline).  funnel.py run for both engines; labels written:
labels_v1_694313a38abc2da6.jsonl + labels_v0_63c771d64e18f619.jsonl
(v0 hash unchanged — regenerated, same digest).

PATTERN_LINE, born objects (eval_v2 ruler):
                     recall   trusted  prec    ink/panel
  v0 63c771d6        0.109    0.106    0.020   5.96
  v1 cf2a7c1a (pre)  0.076    0.078    0.023   3.29
  v1 694313a3 (post) 0.109    0.121    0.029   3.45
(evalpy ruler post-L5: recall 0.027, prec 0.007, med 3.0/panel —
eval.py's endpoint check stays mis-shaped per L1; v2 is official.)

v1 post-L5 ties v0 born recall, beats it on trusted (0.121 vs 0.106)
and precision (0.029 vs 0.020) at 42% less line ink.  vs pre-L5 v1:
recall +43% (0.076->0.109), trusted +55% (0.078->0.121).

Funnel oracle (right proposal exists, selection perfect):
  PATTERN_LINE 0.40 -> 0.36 (proposals stricter: min_touch_events=3
  removes weak-right cands; born recall still rose — the surviving
  proposals are better aimed).
Other types, oracle/born, pre -> post (no regressions > 0.02):
  BOX        0.31/0.05 -> 0.30/0.05
  BRACKET    0.62/0.21 -> 0.60/0.20
  LEVEL_CARRIED 0.52/0.15 -> 0.54/0.12  (born -3: broken_line_edge
             candidates now compete inside rate_level_carried=1 —
             flagged, acceptable per-mandate but noted for REQ-1)
  CONTEXT_LINE 0.22 born unchanged; CONTEXT_RANGE 0.00 unchanged;
  LABEL_TF 0.05 born (was ~same); others flat.

Clutter: 13.15 objects/panel born (v0 23.58, v1-pre 12.90) vs golden
~2.7/panel — clutter is a whole-engine problem, not line-specific.

Salience cut on lines (the mandate's 'if caps cut hard, quantify'):
3,492 line proposals -> 302 born.  Of 125 RIGHT proposals: 70
rate_limited, 34 expired, 8 outranked, 2 nms, only 11 born.
Filed as linelab/REQUESTS.md REQ-1 (raise rate_pattern_line or exempt
revive-class re-proposals) + REQ-2 (TTL note).

scoreboard.py: does not exist yet in evalcheck/ — row skipped per
mandate ('once it exists').

18:51Z — L7/L8 done.  Rulings read up to R13 (LEAD_NOTE_R13 is for
EVAL-AUDIT; no line-lane action).  scoreboard.py landed mid-box — row
appended for the post-L7 engine (v1 ef06f265, ruler 50e11fd5:
PL r/p 0.10/0.03, orcPL 0.40 by scoreboard's own oracle defn,
clutter 10.0 live-at-decision, snapR 0.08).

L7 (coverage) — ROUND_4.md has the full table:
  post-L5      oracle 0.36 (67)  born 0.109  trusted 0.128  3492 cands
  R1 argmax    oracle 0.34 (63)  born 0.098  trusted 0.113  4752 cands
  R2 two-pass  oracle 0.34 (62)  born 0.098  trusted 0.121  4573 cands
  R3 theta1    oracle 0.38 (69)  born 0.103  trusted 0.135  3776 cands
  Kept R3: term anchor = unconfirmed theta1 DC leg extreme
  (e.dc.ext_idx), second-class via two-pass _scan so it can only add
  coverage.  Session extremes are pool members (never triggers).
  New param: line.term_lookback_bars=18 (provenance logged).

L8 (selection) — select_eval.py, funnel R11 prefix labels
(cand_right), 1,959 distinct line candidates, 80 right:
  feature       overall  folds
  touches        0.519    0.461/0.639/0.495/0.538/0.520
  piv_touches    0.564    0.437/0.666/0.588/0.654/0.564
  prom_abr       0.412    0.414/0.549/0.523/0.364/0.190
  age_min        0.511    0.503/0.452/0.475/0.518/0.708
  score(salience) 0.517   0.449/0.638/0.498/0.545/0.492
  -> NO feature reaches 0.60 on all 5 day-folds; per the L3 protocol
  no combined score is built.  The honest flag stands: age_min (0.81
  on the raw lab pair-dump) does NOT replicate on the production
  proposal stream (0.51) — the stream is already pre-filtered by the
  per-trigger best-pair rule, so what remains is the hard residue.
  Salience's current birth score AUC 0.52 here matches EVAL-AUDIT's
  0.53 finding — consistent, and equally unimprovable from cand feats.

REQUESTS.md: REQ-1 (rate cap: 76/126 right proposals rate_limited)
stands as the binding selection constraint; REQ-2 (TTL) noted.

18:52Z — final state check.  Engine v1 ef06f265ab84889f.
run_eval v1 (final code): evalpy recall 0.032 prec 0.009 trusted
0.042; eval_v2 recall 0.103 prec 0.028 trusted 0.128, med 3.0
lines/panel.  test_engine_v1 34/34 PASS on final code.
Queue complete: L5 ported+green, L6 measured+scoreboard row, L7
theta1-terminal kept (oracle 0.38), L8 measured (no feature passes;
honest flag), REQUESTS.md REQ-1/REQ-2 filed.
