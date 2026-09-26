# M15 scaling notes (lab only — no engine edits, B.S(c))

M15 carries 1/3 the bars per wall-clock hour vs M5. Params denominated
in **bars that encode a duration** need ×1/3 when the engine is ported;
params that are **wall-clock** (CET/minutes/days) or **event counts**
(touches, pivots, defences, births-per-window caps) do not.

## Scale ×1/3 (duration-in-bars)

| param | M5 | M15 |
|---|---|---|
| abr_len | 20 | 7 |
| ema_len | 25 | 8 |
| window_bars | 84 | 28 |
| box.min_build_bars | 6 | 2 |
| box.reanchor_cooldown_bars | 12 | 4 |
| box.right_edge_min_bars / max_bars | 6 / 18 | 2 / 6 |
| box.tf_relabel_bars | 3 | 1 |
| box.cong_min_bars | 6 | 2 |
| line.pierce_dead_bars | 2 | 1 |
| line.stale_retire_bars | 60 | 20 |
| line.revive_max_age_bars | 48 | 16 |
| line.loc_sess_bars | 18 | 6 |
| line.term_lookback_bars | 18 | 6 |
| line.extend_min_bars / max_bars | 3 / 17 | 1 / 6 |
| line.context_min_bars / max_bars | 36 / 96 | 12 / 32 |
| line.span_max_bars | 96 | 32 |
| line.loc_ext_bars | 3 | 1 |
| level.mini_span_max_bars | 24 | 8 |
| level.def_traverse_bars | 2 | 1 |
| level.def_stale_bars | 60 | 20 |
| level.def_revive_bars | 96 | 32 |
| level.def_sess_grace_bars | 48 | 16 |
| level.def_ret24_bars | 24 | 8 |
| squeeze.min_bars | 3 | 1 |
| squeeze.apex_bars | 15 | 5 |
| squeeze.span_max_bars | 17 | 6 |
| bracket.sep_min_bars / max_bars | 4 / 40 | 1 / 13 |
| salience.recency_halflife_bars | 24 | 8 |
| salience.dwell_bars | 24 | 8 |
| salience.cand_ttl_bars | 24 | 8 |
| salience.rate_window_bars | 72 | 24 |
| salience.context_window_bars | 288 | 96 |
| salience.revive_max_bars | 144 | 48 |
| derived.ema_slope_hysteresis_bars | 3 | 1 |
| derived.chop_er_bars | 10 | 3 |
| lifecycle.far_bars | 24 | 8 |
| lifecycle.stale_bars | 72 | 24 |
| ev-route SEP (double_top_min_sep_bars) | 4 | 1 |
| ev-route COOL (birth_cooldown_bars) | 10 | 3 |

## Keep unchanged (wall-clock or event counts)

- CET/minutes/days: `box.asia_start_cet`, `box.asia_end_cet`,
  `line.span_max_min`, `level.def_asia_end_min`,
  `level.def_mini_max_age_min`, `derived.grid_window_days`,
  `derived.tod_window_days`.
- Event counts: `box.min_company`, `box.max_legs_back`,
  `line.min_touches`, `line.min_touch_events`, `level.depth_init`,
  `level.mini_min_pivots`, `level.def_min_defences`,
  `level.def_level_max_live`, `level.def_mini_max_live`.
- Caps per scaled window (density per wall-clock is unchanged):
  all `salience.budget_*`, `rate_*`, `fam_rate_*`, `famcap_*`,
  `famlive_*`, `fam_floor`, `fam_total_live`, `joint_struct`,
  `rate_label_tf`. The *window* shrinks ×1/3; the per-window caps stay.
- `box.tail_bars = 0` (already zero).
- ev-route pip constants unchanged: DTOL=2.0p, HMIN=6.0p, HMAX=34.0p
  (price-domain); pullback span>=3 bars would scale to 1.

## Caveats

- Rounded values: several params floor at 1 on M15 (min_build_bars 6→2,
  tf_relabel 3→1) — the M15 engine loses sub-bar resolution; anything
  already ≤3 bars is effectively a 1-bar gate.
- `line.slope_floor` is pips/bar: M15 bars are 3× longer, so the same
  pips/hour floor is 3× the pips/bar value (0.25→0.75 if ported).
  Slope thresholds are the only class that scales ×3, not ×1/3.
- These are unscaled translations, not tuned values — an M15 port needs
  its own TUNE pass.
