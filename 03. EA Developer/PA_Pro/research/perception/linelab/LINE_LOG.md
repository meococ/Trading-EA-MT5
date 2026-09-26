# LINE_LOG — lane LINE-LAB progress log

Lane opened 2026-09-21 ~16:59Z (Lead mandate). Writer: B4 lane agent.
Scope: `research/perception/linelab/` only; TUNE v2 only; bars via
`golden/book_loader.py`; causal proposer; HOLD never read.

## 17:07Z — lane start, context survey done

Read before writing a line:
- Mandate facts: 198 golden PATTERN_LINE, ALL `prec=eye`; repair
  methods: 122 `constrained_fit`, 62 `text_anchor_bars`, 12 unusable,
  2 time_only. v1 line recall 4/186 under eval.py; v1 0/8 vs v0 3/8
  on the 6-panel eval_v2 smoke -> v1 lines are a regression.
- `golden/validate.py`: TOUCH_TOL=1.5p, MIN_TOUCHES=2, `line_at()`,
  `load_days()`.
- `eval.py` PATTERN_LINE match: |dt0|,|dt1| <= 15 min AND engine line
  within tol (eye=6p) of golden endpoints evaluated at golden t0,t1.
- `evalcheck/eval_v2.py` LINE branch: clipped overlap >=
  min(0.5*gspan, max(10, 0.25*gspan)); then endpoint check at overlap
  edges with tol_l = sigma + |slope_g|*10min; repaired labels get
  sigma=1.5p, eye labels 5p. tol_px -> prec_sigmas in common.py.
- `swings.py`: DCStream(theta_fn, spike_fn).update(i,h,l)->Pivot list;
  Pivot(t_ext,t_conf,price,dir,theta,prom,prom_birth,leg,lone_spike);
  SwingBook(pmin_abr,pstruct_abr).alive()/structural()/superseded().
- `lines.py` v1: two routes (hull_max_touch on structural pivots;
  named_bar via _named_bars + _local_extreme), score - overshoot -
  age penalties, freeze/replace, pierce->extend 3..17 bars then
  extension_done; CONTEXT_LINE span gate [36,96] bars.
- `engine_v0.py`: pair-scan over confirmed pivots within window_bars;
  slope cap +-0.30 pips/bar; freshness veto (`same[-1][0]==idx`);
  >=3 touches or within 3*ABR of price; one line per side;
  pierce->extend 3..17.
- DN_LINE: hull anchors + max-touch select + freeze; steep legs may
  anchor on theta1 pivots; distance demotes not vetoes; known FNs
  9.11b/9.21b/9.21c/9.19a/9.17a/9.5c/9.23b; FPs 9.8c/9.40c/9.55c/9.46a.
- DISAGREEMENT_1/2: only 2/57 endpointed golden lines have an engine
  line within 6p of BOTH endpoints; golden lines die at break bar,
  v1 lines run to day-end; hull_max_touch picks wrong anchors.
- evalcheck/common.py prec_sigmas: repaired lines -> 1.5p price sigma
  (the ruler ASSUMES repair fits bars to ~1.5p; L1 must verify).
- GOLDEN_AUDIT: pre-v2 scan fits had 37/77 wrong-way slopes; v2
  repairs are text-constrained -> bar-faithful partly by construction;
  audit measures residual noise, not agreement by fiat.

Plan order: L1 audit script -> render 20 -> LINE_YARDSTICK_AUDIT.md
-> L2 anatomy -> L3 prototype + eval harness -> L4 integration note.

## 17:35Z — L1 done: LINE_YARDSTICK_AUDIT.md

Findings: labels are *fitted geometry*, not pixels. Anchor end is
tight (anchor_res p90=1.8p; hug4 p95=2.0p on trusted subset); t1 is
ink-end, not an anchor (end1_res p90~20p). Suspect tiers: A=44
(thin_touch/loose_fit/anchor_drift/side+slope mismatch; includes both
R3 misses 9.41a#0, 9.66c#5 + visually-confirmed 9.66c#2),
B=9 early_fade. Trusted subset n=141 for geometry tuning.
eval_v2 sigma=1.5p OK at anchors, ~0.5-1p tight at unanchored t0;
eval.py endpoint check at t1 is mis-shaped (tests ink end).
Metric bug found+fixed mid-run: violation sign was inverted for
under-lines (was measuring safe-side distance); rerun from scratch.
Next: L2 anatomy on trusted subset.

## 17:53Z — L3 rounds + baselines

Prototyping loop (lines_lab.py + run_eval.py, both rulers, 198 panels):
- R1 pivot+loc3 anchors, pivot-trigger only: coverage 95/185.
- Kill-audit on 86 misses: 60 no-pair<4p / 22 over_pivot veto /
  6 slope_sign / 1 touches / 1 no-trigger.
- R2 (+sess-extreme anchors, loc-ext triggers, span 360, over 2*tol,
  drift x2, nt3): coverage 105/185; v2 recall 30/184=0.163 prec 0.020
  ink 7.0/panel; evalpy 11/186=0.059.
- R3 anti-churn (revive closed same-geometry, pierce needs 2 closes,
  margin 1.5): R3d = nt3+score2.5 -> v2 24/184=0.130 prec 0.025 ink
  5.0/panel, evalpy 7/186. nt4 or fresh_only variants cost recall
  without precision gain (4/panel, recall 0.09).
- Feature protocol (day-level 5-fold AUC, 125k candidates):
  only age_min passes >=0.60 every fold (0.73-0.85, any-match);
  struct_first 0.59-0.77 (one fold under). Under first-match
  labeling NOTHING passes — draw-moment is not separable by single
  causal features. Score = nt - over/tol - age stands as a
  gate-serving heuristic; flag to Lead.
- Baselines: v0 v2 20/184=0.109 prec 0.017 ink 6.0 | evalpy 0.022;
  v1 v2 14/184=0.076 prec 0.022 ink 3.0 | evalpy 0.027.
- Known-answer tests PASS (T1 rising 3-touch found nt=6 slope .75;
  T2 lone spike -> nothing drawn).
Next: ROUND_1/2/3 docs, LINE_INTEGRATION.md, final summary.

## 18:05Z — R10/R11 absorbed, final numbers

- R10: eval_v2 official ruler; "Recommended sigma" section added to
  LINE_YARDSTICK_AUDIT.md (trusted hug4 p50/80/90 = 0.29/0.83/1.57p;
  sigma 2.0p ~= 0.4 ABR, landed as REFINED_LINE_SIGMA).
- R11: stale_retire_bars=60 (5h no-touch) added to _maintain;
  veto histogram table added to ROUND_1; freshness *trigger* kept
  (fresh_only *gate* measured and rejected: recall 0.098 vs 0.141).
- Final lab config re-run: v2 26/184=0.141 prec 0.025 trusted
  24/141=0.170 ink 5.0 | evalpy 8/186=0.043. Beats v0 0.109 / v1
  0.076 baselines under v2.
- LINE_INTEGRATION.md + ROUND_1/2/3.md written. Tests PASS.
L1-L4 complete.

18:51Z — RESUME-2 status (mandate MANDATE_LINE_LAB_2).
L5 port landed: lines.py owns trigger-on-any-anchor, loc-ext +
sess-ext + theta1-terminal anchors (two-pass), over 2*tol, drift x2,
span 360, >=3 touch events, revive/pierce2/stale-retire60 anti-churn.
Suite green: test_engine_v1 34/34 (32+2 ported T1/T2), test_engine
23/23, test_engine_v0 23/23 (scale bug /P->*P fixed per LEAD_NOTE_R12
sec.4 — v0 still passes, v0 code untouched).
L6 (eval_v2 50e11fd5): PATTERN_LINE born recall 0.076->0.109, trusted
0.078->0.121, precision 0.023->0.029, ink 3.29->3.45/panel.  Other
types flat (LEVEL_CARRIED born 0.15->0.12, noted).  Scoreboard row
appended for ef06f265.
L7: oracle 0.36->0.38 via theta1 terminal anchor (second-class);
see ROUND_4.md.  L8: no cand feature passes 0.60 all folds on the
production stream; honest flag stands (select_eval.py).
REQUESTS.md REQ-1 filed: 76/126 right line proposals die rate_limited.
