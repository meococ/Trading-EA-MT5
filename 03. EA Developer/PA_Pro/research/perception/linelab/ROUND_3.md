# L3 ROUND 3 — anti-churn + operating-point selection

R2 drew med 7 lines/panel vs golden ~1.3. Cause: every trigger event
births an argmax; pierce→replace cycles add one closed object each
(observed: born 45 → pierced 47 → replaced 51). Fixes:

- `revive`: a new same-side pair matching a CLOSED line's geometry
  (within 2·tol at current bar, closed ≤48 bars ago) reopens that
  object — no new ink.
- `pierce_dead_bars=2`: line is dead only after 2 consecutive closes
  through (a 1-bar poke is a tease; golden tolerates teases, L1).
- `reanchor_margin` 0.5→1.5.
- `min_score` 2.0→2.5.

## Variants measured (all 198 panels)

| variant | v2 recall | v2 prec | eval.py recall | ink med |
|---------|-----------|---------|----------------|---------|
| R3a nt4 + score4.0 + revive + pierce2 | 16/184 = 0.087 | 0.022 | 5/186 | 4.0 |
| R3b nt4 + score2.5 + revive + pierce2 | 18/184 = 0.098 | 0.022 | 5/186 | 4.0 |
| R3c nt3 + fresh_only + revive + pierce2 | 18/184 = 0.098 | 0.022 | 6/186 | 4.0 |
| **R3d nt3 + score2.5 + revive + pierce2** | **24/184 = 0.130** | **0.025** | **7/186 = 0.038** | **5.0** |

Trusted subset (v2): R3d 23/141 = 0.163 (R2: 26/141 = 0.184).
R3d strata (v2): constrained_fit 13/120, text_anchor_bars 9/62.

## Fold spread — mandated feature protocol (final, R2 pool)

Day-level 5-fold AUC, any-match labeling (n=124,979, pos=1,846):
- `age_min` 0.73/0.78/0.77/0.85/0.83 → **only feature ≥0.60 on every
  fold** (overall 0.818).
- `struct_first` 0.70/0.65/0.64/0.59/0.77 → drop (fold 4 < 0.60).
- All others <0.60 on ≥1 fold: nt, over_p, wick_over, span,
  slope_abr_hr, fresh, recent_touches, nt_per_span, ema_side,
  dist_to_last_p, anch_bar_ext, prox_abr, score, rel_nt, rel_score,
  rel_span, is_best.

Under the stricter first-match labeling (n_pos=168), *no* feature
passes — the draw moment itself is not separable by single causal
features. **Protocol outcome: only `age_min` qualifies; a multi-
feature equal-weight score cannot be honestly built.** The birth
score nt − over/tol − age/120 is retained as a gate-serving
heuristic and flagged for Lead review — consistent with
DISAGREEMENT_2 ("score can't separate golden-right from
golden-wrong") and R9a's missing barrier/position term.

## Final operating point (R3d + stale-retire, run `lab_final`)

R11 §2 market fact added: stale-line retirement — close any active
line untouched for `stale_retire_bars=60` (~5h; premium≈0 bound
48–96). Also tracks `last_touch` on every active line's bar-wick
touch. (3rd-touch fact §2a: lifecycle never closes on a touch —
lines live through 3rd+ touches by construction.)

| engine | v2 recall | v2 prec | v2 trusted | eval.py recall | ink med |
|--------|-----------|---------|------------|----------------|---------|
| v0 | 20/184 = 0.109 | 0.017 | 15/141 = 0.106 | 4/186 = 0.022 | 6.0 |
| v1 | 14/184 = 0.076 | 0.022 | 11/141 = 0.078 | 5/186 = 0.027 | 3.0 |
| **lab final** | **26/184 = 0.141** | **0.025** | **24/141 = 0.170** | **8/186 = 0.043** | **5.0** |
| lab R2 (max-recall) | 30/184 = 0.163 | 0.020 | 26/141 = 0.184 | 11/186 = 0.059 | 7.0 |

eval_v2 is the official ruler (R10); eval.py column is legacy.
Lead baseline to beat (R10 §3): v0 0.10 / v1 0.09 under v2 —
lab clears both at comparable precision; stale-retire moved
26 vs 24 hits vs R3d at same ink.

Residual gap to HOLD≥0.50: coverage ceiling (~57% candidate
coverage; ~23% of golden lines have no expressible anchor pair
<8p — consistent with the L1 'eye'-precision suspects) plus
context-blind selection (no fold-stable features).

Known-answer tests: `tests/test_known_answers.py` — T1 clean
3+touch rising line found (nt=6, slope 0.75 p/bar); T2 lone spike
draws nothing. PASS.
