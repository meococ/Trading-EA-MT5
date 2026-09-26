# SCALE REPORT C1 — frozen engine 9acaa206 (R48 §48.4), DESIGN 2016–2021

Snapshot under test: `scale/engine_9acaa206/` — the build lane's freeze
candidate, sha256s verified, `code_hash` recomputes to
`9acaa206c8d386dc`.  Arm **C1** = its `params_v1_1.json` defaults (the
round's keeps K1–K6 ON); arm **V1** = `scale/engine_e62f2dc9/` +
`params_stable.json` (the `9283b389` STABLE line verified in C-round 1).

Identity: `verify_c1.py` — 3 TUNE panels vs cached
`m1_v1@9acaa206` runs: canonical EQUAL ×3 (`_verify_c1.log`).

Data wall unchanged: `design_loader.py` (DESIGN 2016–2021, ctm
pushdown, symbol allowlist, outcome-module refusal).  Outcome-blind —
drawing counts only.  Same 240 stratified days as C-round 1
(`_days_240.txt`, extracted from the V1 run's own output so the day-set
is identical by construction).

What the round changed (params diff, e62f2dc9-KEPT → 9acaa206 defaults):
`box.cong_trigger` ON (pivot-free congestion births, h≤5.5 ABR,
≥6 bars), `box.dedup_iou` + `box.wick_edges` ON, `box.rank_score` ON,
`salience.fam_budget`+`fam_caps` ON (author-derived per-kind caps),
`salience.box_lab_score_use`+`box_score_pick` ON (score supersede),
`famlive_context=1`, `line.slope_floor=0.25` pips/bar,
`level.def_mini_off`+`defended_origin` ON.  `joint_struct`,
`fam_total_live`, `famcap_bracket` ship at 0/OFF.

## Q2 — EURUSD M5, same 240 days, C1 vs V1 vs author

_(full year×session tables and all flags with examples: TABLES_C1.md)_

Pooled rows (author: live med 1.0 / p90 2.0; box 3.45 ABR / 28 bars;
slope 9.2 p/hr):

| arm | sess | struct med/p90 | >5 | sa% | emL/100 | emU/100 | BOX/d | PL/d | LC/d | BR/d | boxH abr | boxDur | slope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | asia | 4.0 / 4.7 | .002 | .57 | 6.0 | 11.3 | 1.61 | 2.04 | 1.18 | 1.23 | 5.2 | 61 | 1.8 |
| **C1** | asia | **3.0 / 4.2** | .007 | .53 | 5.9 | 10.0 | **1.04** | 2.41 | 1.28 | **1.01** | **8.6** | **100** | **3.6** |
| V1 | eu | 3.0 / 4.2 | .001 | .58 | 5.6 | 0.14 | 0.97 | 1.68 | 0.93 | 0.88 | 2.6 | 44 | 2.9 |
| **C1** | eu | 3.0 / **3.9** | .006 | .58 | 5.8 | 0.17 | 0.99 | 1.77 | 0.97 | **0.60** | 3.4 | 42 | **4.7** |
| V1 | us | 3.0 / 3.9 | .004 | .70 | 4.8 | 0.00 | 0.84 | 1.43 | 0.73 | 0.68 | 2.4 | 44 | 3.9 |
| **C1** | us | 3.0 / **3.5** | .001 | .68 | 4.8 | 0.00 | **0.66** | 1.44 | 0.80 | **0.55** | 2.8 | **37** | **5.6** |

**How much ink did the round remove?**  Net −7.8% drawn objects
(4168→3843) on identical days, and it is the RIGHT ink: live-object p90
down in every session (asia 4.7→4.2, eu 4.2→3.9, us 3.9→3.5), asia
median 4→3.  Births/day fell exactly where the keeps aimed: BRACKET
−18…−32% (asia 1.23→1.01, eu 0.88→0.60), BOX −35% asia (1.61→1.04) and
−21% us; RANGE_OPEN births collapsed (0.35→0.01/day — the congestion
trigger now births final boxes directly).  Line slope moved toward the
author on every session (asia 1.8→3.6, eu 2.9→4.7, us 3.9→5.6 p/hr vs
author 9.2 — `line.slope_floor` visibly working, still <½× author).

**But the keeps traded density for size:** congestion-triggered boxes
are taller and longer — asia box height 5.2→**8.6 ABR** (author 3.45,
new >2x flag in 6 cells) and asia duration 61→**100 bars** (flag in 8
cells).  PATTERN_LINE births went UP slightly (2.04→2.41 asia).  Flag
count overall: **178 cells C1 vs 205 V1** (−13%).

**Families still >2x the author row (pooled, all sessions):**
struct_med 3× (everywhere), em_logged ~5–6/100 bars (author ~0),
asia em_unlogged ~10/100 (F4 forming ranges), births:
LEVEL_CARRIED ~2–10×, CONTEXT_LINE ~6–32×, PATTERN_LINE ~2–5×,
BRACKET ~3–12×, BOX ~3× (asia+us).  MINI_LEVEL births are now ~0 —
the under-draw flag disappeared with the count itself.

## Census — arm C1, every DESIGN trading day 2016–2021, EURUSD M5

Counts of drawings only: boxes born, box breakouts (engine
`break`/`break_confirm`/`pierced` events), levels born, lines born.
Per (day, session) rows in `_census_C1_EURUSD_M5.jsonl` (6451 rows,
all 1868 trading days); `census_report.py` zero-fills days with no
drawings before taking medians.  `cv` = std/mean of the six yearly
totals — the year-spread the Owner asked for.

**Per session, all six years pooled** (tot / median-day / cv):

| sess | days | boxes | breaks | levels | lines |
|---|---|---|---|---|---|
| asia | 1557 | 1552 / 1.0 / .07 | 9193 / 6.0 / .14 | 1946 / 1.0 / .03 | 4787 / 3.0 / .03 |
| eu   | 1557 | 1504 / 1.0 / .13 | 10606 / 6.0 / .07 | 1509 / 1.0 / .01 | 3325 / 2.0 / .02 |
| us   | 1557 | 1221 / 0.0 / .06 | 7019 / 4.0 / .04 | 1269 / 1.0 / .03 | 2711 / 2.0 / .03 |
| other| 1868 | 1131 / 0.0 / .08 | 6231 / 3.0 / .06 | 1150 / 1.0 / .05 | 2606 / 1.0 / .03 |

**Per-year totals** (the full grid is in `_census_table.txt`):

| year | asia boxes/br/lv/ln | eu boxes/br/lv/ln | us boxes/br/lv/ln |
|---|---|---|---|
| 2016 | 266 / 1654 / 316 / 804 | 262 / 1799 / 254 / 564 | 211 / 1215 / 223 / 430 |
| 2017 | 265 / 1660 / 324 / 808 | 237 / 1752 / 251 / 566 | 193 / 1168 / 216 / 446 |
| 2018 | 279 / 1713 / 333 / 822 | 304 / 1957 / 252 / 533 | 218 / 1233 / 208 / 453 |
| 2019 | 224 / 1109 / 323 / 749 | 202 / 1540 / 247 / 563 | 197 / 1096 / 203 / 463 |
| 2020 | 264 / 1632 / 312 / 787 | 273 / 1800 / 254 / 553 | 218 / 1188 / 211 / 456 |
| 2021 | 254 / 1425 / 338 / 817 | 226 / 1758 / 251 / 546 | 184 / 1119 / 208 / 463 |

**Answer to the 04:17Z question:** on the frozen round engine the
drawing census is strikingly uniform — levels and lines vary by
**CV 1–5%** year over year, boxes 6–13%, breakouts 4–14%.  The only
visible regime response is 2019 (the low-vol year): breakouts dip
~20–30% (asia 1109 vs ~1650 elsewhere) while births barely move — the
engine draws on schedule regardless of tape.  Mechanically consistent,
yes; but the per-day rates themselves sit ~3× the author's.

**Cross-symbol check (arm C1, GBPUSD M5, same 240 days; pip = 1e-4 so
no F3 distortion):** identical direction — asia struct 4.0→3.0, BOX
births 1.50→0.96/d, slope 2.1→4.2 p/hr, and the same congestion-box
signature (asia boxH 4.5→7.1 ABR, boxDur 70→104).  GBPUSD table in
TABLES_C1.md (`C1_GBPUSD_M5`).

## Gallery

`gallery/index.md` — 10 random sessions (Mon–Fri, excl 01-01/12-25,
≥60 session bars), rendered twice: arm C1 and arm V1 side by side.
The pair `2020-04-28_asia` is representative: V1 stacks two wide boxes
plus long lines; C1 shows one bracket row and noticeably less ink.

## What changed since the 05:53Z report

- Engine is now the round-frozen `9acaa206` (K1–K6 ON), verified
  byte-equal to the freeze candidate and canonically equal to the
  cached `m1_v1@9acaa206` TUNE runs (3 panels).
- Ink −7.8% vs V1 on identical days; live-object p90 down in every
  session; asia median 4→3.  Births down where aimed (BRACKET, BOX,
  RANGE_OPEN→0.01/d).  Slope 1.8–3.9 → 3.6–5.6 p/hr toward author 9.2.
- New pressure: congestion boxes are taller (asia 5.2→8.6 ABR) and
  longer (61→100 bars); PATTERN_LINE births up slightly.
- Flag cells 205 → 178 (−13%); the density-vs-author gap narrows but
  does not close: still ~3× live ink.

## For the next round

1. `box.cong_*` produces the tallest, longest boxes in the book —
   consider height/duration bounds inside the trigger, or a post-birth
   shrink (asia boxH 8.6 ABR vs author 3.45 is the single worst ratio
   left).
2. PATTERN_LINE is now the top birth kind everywhere (~1.4–2.4/day)
   — with slope_floor on, quantity, not flatness, is the remaining
   line gap.
3. asia `em_unlogged` ~10/100 bars is still the silent RANGE_OPEN
   tracker (F4); F4's `track` event would make this auditable.
4. Census takeaway for build: births are schedule-driven, not
   tape-driven (2019 dip is breaks-only) — any "draw less" lever must
   cut births directly, the tape won't.
5. Unchanged from C-round 1: struct 3×, re-anchors ~5/100 bars,
   LEVEL_CARRIED/CONTEXT_LINE over-birth, M15 needs bar→time rescaling,
   USDJPY needs F3's per-symbol pip.

## Limitations

Same as C-round 1: day-mode + 5-trading-day warmup undercounts objects
born earlier; `struct med` = median of per-(day,session) medians; asia
`box_dur` includes the RANGE_OPEN forming span; Sunday-open stubs are
noise.  New: the census counts objects by FINAL type, so a RANGE_OPEN
that converts is a BOX birth at the range's birth bar.
