# L3 ROUND 2 — anchor expansion + gate repair

Config delta vs R1:
- + `loc_sess_bars=18`: anchor also on trailing-18-bar (~90min)
  leg/session extremes (provenance: L2 sess-extreme share ~9%;
  kill-audit showed named-bar anchors missing).
- loc-extreme bars now *trigger* proposals (previously pool-only):
  bar j = i−k freshly confirms → `_propose` for each side.
- `span_max_min` 240→360 (meas: L1 trusted span max ~350).
- `over_veto_tol_mult=2`: pivot overshoot veto at 2·tol (kill-audit:
  22/86 misses were vetoed at 1·tol while golden tolerates ~2·tol).
- `slope_drift_mult=2`: rising-top/falling-bottom drift cap 20p
  (kill-audit: 6/86 just beyond 1·drift).
- `min_touches` 2→3 (Volman 3-point rule; L2 golden med ~5).

## Results — all 198 TUNE panels, both rulers

| ruler | recall | precision | lines/panel |
|-------|--------|-----------|-------------|
| eval.py  | 11/186 = 0.059 | 0.007 | med 7.0, p90 11.0 |
| eval_v2  | 30/184 = 0.163 | 0.020 | med 7.0, p90 11.0 |

Trusted subset (v2): 26/141 = 0.184.
Strata (v2): constrained_fit 17/120, text_anchor_bars 11/62,
time_only 2/2.

Coverage ceiling (candidate dump, 124,979 cands, 1,846 positives):
105/185 = 57% (+6 lines vs R1).

Feature AUC re-run on the R2 pool (any-match): `age_min` still the
only ≥0.60-every-fold feature (0.73/0.78/0.77/0.85/0.83, overall
0.818). `struct_first` 0.70/0.65/0.64/0.59/0.77 — one fold at 0.59,
dropped. `over_p`, `prox_abr` hover 0.5–0.6 per fold, unstable.

Birth-forensics: 289 drawn lines on 40 panels, 7 matched; matched
births have nt p25 = 5.5 vs drawn median 4 → volume of nt≥4 junk
is the precision problem; 1,432/1,467 drawn lines match nothing.

## Delta

- Recall ~3× v1 at same ruler (0.163 vs 0.076) but ink 7/panel vs
  golden ~1.3 → precision 2%.
- Every additional gate tried trades recall ~linearly for ink:
  nt≥4 → cover 59; fresh → 55; prox≤2ABR → 58 (nt4).

→ ROUND_3: anti-churn (revive instead of re-ink, pierce hysteresis,
replace margin), then pick operating point.
