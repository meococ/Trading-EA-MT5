# BOX-LAB research dataset — data dictionary (R56 §56.4 item 3)

Built by `boxlab/build_r_dataset.py` from K9/STABLE C-2 caches
(`run_c1r_p_base_ee2cbf1202db47b6_*` — byte-identical objects to the
post-F1 merge `4c2df34d7a2a8ee3`, proven by 1728/1728 identity).
TUNE only.  No HOLD.  No engine code changes.

## Grain

One row per **BOX candidate per box-golden τ**.  τ = the golden box's
evaluation minute (`tau_of`, clipped to panel window).  A candidate is
included at τ if it logged at least one `cand_log` row with
`cet_min ≤ τ`.  8975 rows / 92 panels / 115 (panel,τ) cells.

## Identity columns

| col | meaning |
|---|---|
| `panel` | TUNE panel id (e.g. `9.1c`) |
| `date` | trading date (day id for LODO CV) |
| `tau` | golden evaluation minute (cet_min) |
| `cand_key` | `(route, top, bottom, t0)` — join key to cand_log rows |

## cand_log passthrough

`route top bottom t0 t1 t_left touches prom_abr contain barrier
pressure compression ema_guide box_rank deeper_lv n_active`

`t0`,`t1` are day-bar **indices** (not cet_min).  `score_last` = the
score on the candidate's most recent cand_log row ≤ τ.
`last_outcome` = last non-"proposed" outcome ≤ τ
(`pending` if never resolved): pending 4830 / expired 3114 /
below_min_score 613 / outranked 291 / rate_limited 127.
`born_by_tau` = 1 if the cand ever logged `born` by τ.

## Labels

| col | definition |
|---|---|
| `label_golden` | gi of the box golden (scorable, `tau_of ≤ τ`) that the cand's **drawn span** matches under `eval_v2.match` (IoU ≥ .5 vs golden containment window + both edges in tol); −1 if none.  Strict ruler label: covers 12 distinct goldens — conservative because candidates have no recorded bs/be containment window. |
| `label_edge` | gi under the lab "covered" convention: `edge_match` (both edges within `tol_px`) + `span_overlap` vs golden span at τ; −1 if none.  This is the funnel's covered/right-geometry label. |
| `is_engine_pick` | 1 if the cand's (top,bottom) equals the top-ranked live box-family object's (hi,lo) at τ. |
| `pick_type`/`pick_hi`/`pick_lo`/`pick_t0`/`pick_t1`/`pick_score`/`pick_id` | cell-level: the engine's top-ranked live box-family object at τ (BOX 34 cells / CONTEXT_RANGE 80 / RANGE_OPEN 1 of 115). |

**Primary label for hypothesis tests: `label_edge`** (consistent with
the R1 author-vs-engine funnel).

## Raw causal features (bars ≤ τ only)

All computed inside `feats_at` from `e.bars`/`e.abr`/`e.ema`/`e.book.seq`
truncated at `j_tau` (last bar with cet_min ≤ τ).  Nothing post-τ.

| col | definition |
|---|---|
| `px_in_box` | close at τ inside [bottom,top] |
| `dist_close_edge_abr` | min(|px−top|,|px−bot|)/ABR |
| `bars_since_in_band` | bars since close last inside band (0 = inside now) |
| `ema_slope_span` | |EMA25(end)−EMA25(start)| / span bars (flatness over box's own span) |
| `ema_in_band` | EMA25 inside band at τ |
| `probes_top`/`probes_bot` | wick beyond edge + close back inside (rejected probes) |
| `prior_leg_abr` | last pivot leg size in ABR confirmed before t0 (box after a leg) |
| `age_bars` | bars from t0 to τ (candidate age — R57.1 H5-causal quantity) |
| `recency_bars` | bars since box's t1 (structure freshness) |
| `bars_since_touch` | bars since any bar overlapped the band |
| `h_rel_day` | box height / day range so far |
| `h_abr` | box height / ABR |
| `overlap_ratio` | share of span bars whose range overlapped the band |
| `abr_at_tau` | ABR at τ (normaliser) |

## Determinism

Re-running `build_r_dataset.py` on the same caches reproduces the file
byte-for-byte (dict order fixed, no randomness).
