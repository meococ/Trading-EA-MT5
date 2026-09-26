# GKIT_LOG — lane G-KIT (render tool for the chart reviewer, R80 s80.6)

Owner task received 23/09 ~10:10Z. Walls: writes only under
`research/perception/review/`; no engine / tests / ruler / evalcheck /
golden / owner_pack edits; no git, no MT5, no deletes; pa_slots <= 1
BelowNormal; engine runs only via `tools/heavy_run.py --lane gkit`;
TUNE only, HOLD sealed, no outcomes.

## Read log

- 2026-09-23: rulings read up to R80
  - R77 in full (s77.5 bracket placement: hug the formation extreme,
    ~0.5*ABR beyond tops for M / below lows for W; never a fixed band).
  - R78 in full (keep rule; arm definitions H0/S1/TT; override-style
    offline arms on C-3 cached objects at tau).
  - R79 in full (M2-TV rendering: R77 renderer, EMA25 visible, no bars
    after tau, objects clipped at tau, dashed "now" line).
  - R80 in full (s80.6 G-KIT spec: one CLI, flags or override jsonl,
    12 fixed review panels = 4 box-led + 4 level-led + 4 line-led TUNE
    decisions, none from p099-p102 panels; calibration p099-p102 blind).
  - Reused (import, not forked): `render.py` (book grammar + bracket
    rule), `ceiling_render.py` (base sheet: bars stop at tau, dashed
    divider, axis json), `evalcheck/snapshot.py` + `recall_at_k.py`
    (live objects at tau from canonical caches, R75 s75.6),
    `deepresearch/DR_RULES_measure.py` (golden-decision tau list via
    `DR_RULES_events.jsonl`), `evalcheck/plausibility.py` (pack item
    look: one blue object), `ceiling_sample.py` (the 10 ceiling
    panels), `owner_pack/dr_rules_item_geom.jsonl` (p099-p102
    geometry; `_owner_judge_key/` never opened).
  - STABLE C-3 = tree `1a5502129b4c1554`; canonical cache =
    `run_uip2_pbbirth_8361fe85e73f9437_<date>_<tau>.pkl`
    (evalcheck/_cache), verified via `_gate_pack_c3.py` /
    `GATE_PACK_C3_1a550212.md`.

## Build log

- 2026-09-23: `render_review_set.py` written (CLI: `--arm`,
  `--flags`, `--override`, `--panels`, `--out`, `--make-panels`,
  `--calib`, `--sheet`, `--selftest`, `--drop-tagged`).  Reuse =
  import: `ceiling_render.render_sheet` (base sheet: bars stop at
  tau, dashed now-line, axis json), `_render_v2.VMap/_dash_*` (owner-
  pack look, 1700x620), `cache.py` (canonical bars), pickled
  `run_uip2_pbbirth_8361fe85e73f9437_<date>_<tau>.pkl` (live objects
  at tau per snapshot.py semantics: state != DELETED), book grammar
  mirrored from `render.py` incl. R77 s77.5 bracket placement, item
  ink mirrored from `plausibility.draw_item` (blue, 3px).
  `clip_now()` whites out every plot column right of the now line so
  literally no candle ink exists there (the tau bar straddles the
  divider by ~half a bar width; it is clipped too).
- 2026-09-23: `review_panels.json` FIXED (seed 20260923): 12 TUNE
  golden-decision points from `DR_RULES_events.jsonl` (kind=obj,
  single-family decisions preferred), 4 box + 4 level + 4 line, 12
  distinct dates; excluded p099-p102 panels {9.1a, 9.34b, 9.30c,
  9.46a} (via owner_pack/dr_rules_item_geom.jsonl) and the 10 ceiling
  panels {9.11a, 9.19a, 9.23c, 9.24c, 9.25b, 9.36b, 9.38a, 9.50a,
  9.62a, 9.66c}.  Every chosen (date,tau) has its canonical c3 cache
  pickle.
- 2026-09-23: rendered `sets/c3/` = 12 PNG + 12 JSON + `_sheet.png`
  (4x3).  Live objects at tau drawn clipped at tau: box counts
  9-15/panel.
- 2026-09-23: rendered `sets/calib/` = calib_1..4 + JSON + `_map.json`
  (seed-shuffled: calib_1=p102, calib_2=p100, calib_3=p099,
  calib_4=p101).  One blue object each, no bars after tau.
- 2026-09-23: `--selftest` PASS x2 (bytes-identical render;
  no-ink-right-of-now = 0 dark px).  `--flags` correctly refuses
  outside `heavy_run --lane gkit` + `GKIT_UNDER_HEAVY=1`.
- 2026-09-23: `HOWTO.md` = exact command lines for s1a/s1b/h0a/h0b/
  h0c (expected override paths per R78 s78.4) and the TT trade view
  (`--flags trade_tags=1`, `--drop-tagged`) under heavy_run.

## ESCALATE

(none so far)
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.2b
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.10c
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.11b
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.17b
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.25a
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.33c
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.36c
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.40a
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.42b
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.48b
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.52a
- 2026-09-23 11:07Z ESCALATE s1b non-box mismatch 9.57b

## Round 2 — R81 s81.5(2) review sets (11:0xZ)

- rulings read up to R81 (in full: s81.5(1) TT-2 task + hide set minus lone_edge; s81.5(2) this lane; s81.5(3) _diff.md requirement).
- NOTE on the 12 ESCALATE lines above (11:07Z): assert artifact, not a real mismatch — the drawn json gained a "tags" field this round so strict dict-equality vs the older c3 json failed on every panel. Assert now compares non-box records with the tags field normalised; all 12 panels PASS. No engine/object change happened in between.
- S1 adapter: deepresearch/DR_RULES_S1_objects.jsonl is a STATISTICS file (909 rows, both arms per row), not a drawable override. render_review_set.py now detects that shape (is_s1_stats) and adapts it: every live box-family object gets t_left <- b_j0 computed with the measure's own formula (cap=jge(m,tau-375min)); file rows must agree (0 mismatches on all 12 panels). Live boxes with no stats row (not in the measure's ranked set, e.g. RAN0000/CON0006 born-and-ended before the window) get the same transform; they sit outside the view so ink is unchanged. Non-box objects untouched; write_diff asserts per panel == c3 (12/12 PASS).
- --hide <csv> added (R81 s81.5(1)): explicit tag set that hides. tt_view_v1 uses the TT-v1 hide set = {daylight, steep, shock_inside, impulse_inside, zombie, superseded} — lone_edge NOT hidden. The build lane's --drop-tagged uses TT.TRADE_VIEW_HIDE which already includes the TT-2 tags (line_broken/line_cuts_bodies/stale_far); since TT-2 is not yet verified, v1 uses --hide with the v1 subset only. drawn json records now carry the object's tags list.
- _diff.md per set written automatically for non-c3 arms (added/removed/changed from the per-panel jsons; removals annotated with the tags that hid them).

- tt_view_v1 rendered via tools/heavy_run.py --lane gkit (GKIT_UNDER_HEAVY=1, lock waited 0.0min, run 0.1min): --flags trade_tags=1 --hide daylight,steep,shock_inside,impulse_inside,zombie,superseded --sheet. 12/12 PNG+JSON+_sheet+_diff. Working tree already carries TT-2 code (TRADE_VIEW_HIDE incl v2 tags; PERCEPTION_LOG last entry 11:00Z = TT-2 task, no EVAL-AUDIT verification entry) so v1 used --hide with the v1 subset — objects carrying only v2 tags (line_broken/line_cuts_bodies/stale_far) or only lone_edge remain drawn (verified in diff: every hide= reason contains >=1 v1 tag; lone_edge-only objects present in json).
- HANDOVER next=tt_view_v2 — blocked on EVAL-AUDIT verification of TT-2 (R81 s81.5(2) LATER clause). Command when it lands: GKIT_UNDER_HEAVY=1 python tools/heavy_run.py --lane gkit -- python review/render_review_set.py --arm tt_view_v2 --flags trade_tags=1 --drop-tagged --sheet ; then copy PNGs to _scratch/gr2/tt_view_v2/.
- selftest re-run after round-2 changes: bytes-identical PASS, no-ink-right-of-now PASS.

## tt_view_v2 — R81 s81.5(2) LATER clause met (12:35Z Lead order)

- rulings read up to R81 (LEAD_RULINGS.md ends at s81.7 — R81 is the last ruling present).
- TT-2 verified by EVAL-AUDIT @fa2e52e5 11:40Z (evalcheck/EVAL_LOG.md per Lead).
- ASSERT: trade_tags.TRADE_VIEW_HIDE == {daylight, steep, shock_inside, impulse_inside, zombie, superseded, line_broken, line_cuts_bodies, stale_far} (9 tags); lone_edge NOT in it -> fact-only, never hides. --drop-tagged hides exactly this set.
- --diff-vs <set> added: _diff.md gains a second per-panel table (tt_view_v2 vs tt_view_v1 = what the 3 new tags removed), hide tags annotated from the render's hidden records.

- counts (drawn objects per panel; b/l/l/b/o = box/level/line/bracket/other):
- c3: 9.2b=12(2/3/3/2/2), 9.10c=12(1/3/4/2/2), 9.11b=13(2/3/4/2/2), 9.17b=14(2/4/4/2/2), 9.25a=9(3/2/2/1/1), 9.33c=10(1/2/3/2/2), 9.36c=15(3/3/5/1/3), 9.40a=14(3/4/4/1/2), 9.42b=14(5/2/4/1/2), 9.48b=15(2/3/6/2/2), 9.52a=9(3/1/2/1/2), 9.57b=10(2/2/4/2/0) | mean=12.25 (b/l/l/b/o=2.4/2.7/3.8/1.6/1.8)
- tt_view_v1: 9.2b=7(1/0/2/2/2), 9.10c=9(1/0/4/2/2), 9.11b=8(1/0/3/2/2), 9.17b=7(0/0/3/2/2), 9.25a=5(1/0/2/1/1), 9.33c=7(0/1/2/2/2), 9.36c=9(2/0/3/1/3), 9.40a=8(0/1/4/1/2), 9.42b=8(1/0/4/1/2), 9.48b=11(1/0/6/2/2), 9.52a=8(2/1/2/1/2), 9.57b=6(1/0/3/2/0) | mean=7.75 (b/l/l/b/o=0.9/0.2/3.2/1.6/1.8)
- tt_view_v2: 9.2b=7(1/0/2/2/2), 9.10c=8(1/0/3/2/2), 9.11b=7(1/0/2/2/2), 9.17b=7(0/0/3/2/2), 9.25a=5(1/0/2/1/1), 9.33c=6(0/1/1/2/2), 9.36c=8(2/0/2/1/3), 9.40a=7(0/1/3/1/2), 9.42b=8(1/0/4/1/2), 9.48b=10(1/0/5/2/2), 9.52a=8(2/1/2/1/2), 9.57b=5(1/0/2/2/0) | mean=7.17 (b/l/l/b/o=0.9/0.2/2.6/1.6/1.8)

- tt_view_v2 rendered via heavy_run --lane gkit (waited 0.0min, run 0.4min): --flags trade_tags=1 --drop-tagged --diff-vs tt_view_v1 --sheet. 12/12 PNG+JSON+_sheet+_diff; PNGs copied to _scratch/gr2/tt_view_v2/.
- v2-vs-v1 delta (what the 3 TT-2 tags removed): 7 objects across 7 panels, all line-family — line_broken x2 (PAT0015, PAT0014), line_cuts_bodies x1 (PAT0016), stale_far x3 (PAT0011, PAT0010, PAT0001), line_cuts_bodies+stale_far x1 (CON0008). added=0, changed=0 on all panels.
- selftest re-run: bytes-identical PASS, no-ink-right-of-now PASS.
- HANDOVER next=idle-awaiting-Lead (round 2 on s1b + tt_view sets complete: c3, calib, s1b, tt_view_v1, tt_view_v2 all rendered, diffed and shallow-copied).

## tt_view_v3 — R83 s83.6 fade-broken (14:0xZ Lead order)

- rulings read up to R83 (R82 structure-layer revert + box_broken origin; R83 in full: s83.2 TT-3, s83.6 this lane, s83.7 M2-TV conditional name).
- precondition met: PERCEPTION_LOG 13:52Z TT-3 landed @e7d13384 on parent fa2e52e5, OFF==parent 623/623, ON==OFF 623/623, prefix 5/5, EVAL-AUDIT verified.
- --fade-broken added: box-family objects carrying tag box_broken are drawn instead of hidden, right edge = facts.trade_tags.exit_bar clipped at tau; style constants FADE_INK=200 (light grey), dashed via R._dash_rect dash=4 gap=4, width 1 (thin). box_broken is removed from that object's own hide set only; every other TRADE_VIEW_HIDE tag still hides. The constant is imported (TT.TRADE_VIEW_HIDE), never copied.
- per-panel no-ink-right-of-tau is enforced by the existing clip_now whiteout + now-line redraw (all objects are clipped at tau before that).

- counts (drawn objects per panel, solid+faded):
- c3: 9.2b=12+0, 9.10c=12+0, 9.11b=13+0, 9.17b=14+0, 9.25a=9+0, 9.33c=10+0, 9.36c=15+0, 9.40a=14+0, 9.42b=14+0, 9.48b=15+0, 9.52a=9+0, 9.57b=10+0 | mean solid=12.25 faded=0.00 total=12.25
- tt_view_v2: 9.2b=7+0, 9.10c=8+0, 9.11b=7+0, 9.17b=7+0, 9.25a=5+0, 9.33c=6+0, 9.36c=8+0, 9.40a=7+0, 9.42b=8+0, 9.48b=10+0, 9.52a=8+0, 9.57b=5+0 | mean solid=7.17 faded=0.00 total=7.17
- tt_view_v3: 9.2b=6+1, 9.10c=7+1, 9.11b=7+0, 9.17b=7+0, 9.25a=5+0, 9.33c=6+0, 9.36c=6+2, 9.40a=7+0, 9.42b=7+1, 9.48b=9+1, 9.52a=7+1, 9.57b=4+1 | mean solid=6.50 faded=0.67 total=7.17

- tt_view_v3 rendered via heavy_run --lane gkit (waited 2.0min behind EVAL-AUDIT, run 0.5min): --flags trade_tags=1 --drop-tagged --fade-broken --diff-vs tt_view_v2 --sheet. 12/12 PNG+JSON+_sheet+_diff; PNGs copied to _scratch/gr2/tt_view_v3/.
- faded boxes: 8 total across 7 panels (9.2b BOX0002@665min, 9.10c BOX0001@120, 9.36c BOX0001@195+BOX0018@900, 9.42b BOX0001@540, 9.48b BOX0002@130, 9.52a BOX0005@410, 9.57b BOX0001@120) - all clause=run3, all drawn dashed FADE_INK=200 truncated at exit_bar. removed-vs-v2 = 0 on all panels (no object hidden solely/additionally by box_broken; the 8 broken boxes show as changed t1_min vs v2).
- selftest re-run: bytes-identical PASS, no-ink-right-of-now PASS.
- HANDOVER next=idle-awaiting-Lead (round-3 inputs ready: tt_view_v3 + c3 control; tt_view_v2 fallback set also on disk).
