# FLAG_LEDGER — every boolean flag + key parameters (ARCH lane; rev2)

## rev2 changes (answers ARCH_REVIEW item 4 + spot-check (e))

- **Recount: 49 boolean leaves / 21 ON at C-3 defaults** (script count
  05:26Z; was written "48/17" — `ev_uip_pb_birth` existed OFF at draft
  time and four `ev_uip*` flags turned ON at the C-3 fold 04:17Z).
- **Added the missing `ev_uip_pb_birth` row** — the actual kept fixture
  cure (V3 arm @8361fe85, folded into C-3 = `1a5502129b4c1554`).
- **`ev_uip`, `ev_uip_persist`, `ev_uip_lvfree`, `ev_uip_pb_birth`
  re-marked KEPT-ON** (C-3 defaults; verified VL 04:15Z/04:29Z).
- **`ev_uip_pb_write` reclassified**: V2 (`lvfree_pb`) was byte-flat and
  retired by R68 — it is OFF in C-3, *not* the kept promotion.
- **`ev_uip_buildstart` reclassified**: official A/B byte-flat +0
  (`uip2_bs @c06365ce`, REQUESTS §24) — OFF, records a diagnostic field.
- **§B row fixes**: `famcap_bracket=0` means *uncapped* (0 = no cap in
  the famcap check); `min_score_birth_signal` is a **dead leaf** (never
  read); `level.def_*` = 20 leaves (21 incl. the flag); `rate_<kind>` =
  7 kind rates + `rate_default`; `retire_far OFF` wording corrected
  (VL 20:31Z: PL 19→22 *up*, LC 6→5 *down*); `box.tail_bars` was *not*
  zero-delta (VL 21:47Z: bracket .29→.31, clutter 10→11 — small but
  real).
- **`box.leg_edges` reclassified measured-inert** (PL 04:58Z: fires,
  zero-delta); `box.watch_birth` informational arm only (PL 05:49Z).
- **New §C**: `.get()`-only code defaults absent from the params file
  (review A-C9) — each with its in-code default and classification.

Status legend: **KEPT-ON** / **FAILED-OFF** / **DEAD** /
**PENDING** / **INERT-OFF** (measured flat, default OFF).
Fate legend: **fold** / **tunable** / **quarantine**.

Citations: VL = `evalcheck/VERIFY_LOG.md`, RL = `LEAD_RULINGS.md`,
ARCH = `LEAD_RULINGS_ARCHIVE_R00-R50.md`, REQ = `boxlab/REQUESTS.md`,
prov = `params_v1_1.json` provenance, PL = `PERCEPTION_LOG.md`.

## A. Boolean flags (49)

| # | flag | origin | measured A/B (cite) | status | proposed fate |
|---|---|---|---|---|---|
| 1 | `box.rank_score` (ON) | R34/BOX-LAB C1 | inside K3 bxcombo @dd96c5fe: box 2→3, line 17→19, clutter 5.00, OFF-id clean (VL 06:15Z; VL 05:22Z) | KEPT-ON | **fold** — `box_rank` computed on every box cand |
| 2 | `box.leg_edges` (off) | BOX-LAB C1 | fires but **zero-delta — measured inert** (PL 04:58Z) | INERT-OFF | quarantine |
| 3 | `box.wick_edges` (ON) | BOX-LAB C1 | KEPT via bxcombo (VL 06:15Z); solo zero-delta (VL 05:12Z) | KEPT-ON | **fold** |
| 4 | `box.dense_anchors` (off) | BOX-LAB C1 | no keep A/B on record | PENDING | quarantine |
| 5 | `box.dedup_iou` (ON) | BOX-LAB C1 X4#3 | KEPT via bxcombo (VL 06:15Z) | KEPT-ON | **fold** — same-episode IoU dedup |
| 6 | `box.watch_birth` (off) | BOX-LAB C1 X4#1 | informational arm only (PL 05:49Z); no keep A/B | PENDING | quarantine |
| 7 | `box.cong_trigger` (ON) | R44 §44.3 | K6 @df79ade3: box@1 7→9 (+2), clutter 5.00, OFF-id clean (VL 09:04Z/09:14Z) | KEPT-ON | **fold** |
| 8 | `box.cong_pivedge` (ON) | R50 §50.2.4 | K8 @81f7503f: box 9→10, level 7→8, clutter 4.67 (VL 14:43Z) | KEPT-ON | **fold** — uses `.get()` cong_piv_* defaults (§C) |
| 9 | `line.lab_score` (ON) | R34 §34.8.1 | K1 @afba83c5: line 16→18, box +1, level +3 (VL 06:15Z) | KEPT-ON | **fold** |
| 10 | `line.steep_pick` (off) | R41 §41.4 | lnsteep: line −2, rejected (VL 07:01Z) | FAILED-OFF | quarantine |
| 11 | `level.defended_origin` (ON) | R19/R20 | K2 @e62f2dc9: level 4→6 above v0 .066 (VL 06:15Z) | KEPT-ON | **fold** — LevelPipe core |
| 12 | `level.def_mini_off` (ON) | R24 §24.2 | inside K2; defended MINIs were ~43% of births, 0/31 hits (prov) | KEPT-ON | **fold** |
| 13 | `level.def_all_lc` (off) | v2b post-L10 | no keep A/B on record | PENDING | quarantine |
| 14 | `marker.day_extreme_only` (off) | R22 | paired A/B 05ad54cf: TF marks +182 but PL −2 LC −1 → fails keep-rule (prov + VL) | FAILED-OFF | quarantine |
| 15 | `marker.day_extreme_live_anchor_ok` (off) | R22 §22.2 | variant arm only | PENDING | quarantine |
| 16 | `marker.off` (ON) | R50 §50.2 | K7 @66f596dc: level 6→7, clutter 4.67, margin +13 (VL 14:43Z) | KEPT-ON | **fold** — BAR_MARKER suppressed |
| 17 | `salience.rate_blocked_extend` (off) | REQ-2, R13/R14 | never A/B'd to a ruling | PENDING | quarantine |
| 18 | `salience.revive_exempt` (off) | REQ-1(b), R13 §13.3 | unblocked-extension variant c188ae66 lost a LC (prov) | PENDING | quarantine |
| 19 | `salience.fam_ledger` (off) | R25 §25.5 | arm (b) BOX −2, FAIL CONFIRMED (VL 22:41Z §27.2.2) | FAILED-OFF | superseded by per-family budgets → quarantine |
| 20 | `salience.fam_budget` (ON) | R34 §34.8.1 | kept chain since K3; famoff arms all worse (VL 07:36–07:38Z) | KEPT-ON | **fold as architecture** |
| 21 | `salience.lc_score_pick` (off) | R34 §34.8.1 step 4 | no keep A/B | PENDING | quarantine → per-family `fam_score_pick` absorbs |
| 22 | `salience.box_prom_rank` (off) | R34 C1 q5 | superseded by box_lab_score_use | DEAD | quarantine |
| 23 | `salience.fam_caps` (ON) | R36 §36.3 | inside bxcombo (R38 §38.4: box+1 line+2) | KEPT-ON | **fold** — per-kind panel caps |
| 24 | `salience.box_lab_score_use` (ON) | R34 §34.8.2.4 | inside bxcombo (VL 06:15Z) | KEPT-ON | **fold** |
| 25 | `salience.level_touch_rec` (off) | R38 §38.5 | no keep A/B | PENDING | quarantine |
| 26 | `salience.line_dedup_merge` (off) | R38 §38.5 | no keep A/B | PENDING | quarantine |
| 27 | `salience.box_score_pick` (ON) | R40 §40.3 arm A | K4 @cfb862d4: box 3→7 (+4) (VL 06:25Z) | KEPT-ON | **fold** → per-family `fam_score_pick` |
| 28 | `salience.box_score_pick_prio` (off) | R40 §40.3 arm B | box 7→5 (−2), REJECTED (VL 06:25Z) | FAILED-OFF | quarantine |
| 29 | `salience.box_prio` (off) | R42 §42.4 | FAIL both revs: level −3/−4, clutter 6.00/6.33 (VL 07:32Z/07:36Z) | FAILED-OFF | quarantine; priority concept → eval-side ranking only (arbiter demoted, ARCH_V2 §3.4) |
| 30 | `salience.box_tau_prio` (off) | R42 §42.4 v4 | @c14060cb: box −3 FAIL (VL 07:36Z) | FAILED-OFF | quarantine |
| 31 | `salience.fam_context` (off) | R44 §44.2 | @88438120 + @4dcc44d7: level −2, clutter 5.67 FAIL; suite cures 7 fixtures (VL 07:52Z/08:08Z) | FAILED-OFF | quarantine flag; family-map fix → v2 ContextPipe (new split, C2 arm) |
| 32 | `salience.ctx_yield` (off) | R49 §49.4.2 | trial arm, no keep verdict; hide-not-evict machinery exists (`_hidden_ctx`) | FAILED-OFF | quarantine birth-path; the hide machinery is the only existing "hide" (arbiter decision) |
| 33 | `salience.ctx_convert` (off) | R51 §51.4.2 | loose variant: 186 converts, level −4 line −3 (in-code note) | FAILED-OFF | quarantine |
| 34 | `salience.box_young_first` (off) | R56 A1v2 | @97061ac5 INERT confirmed (VL 16:22Z) | DEAD | quarantine |
| 35 | `salience.box_live_at_birth` (off) | R56 A3 | lvb_on @29de0689 flat/inert (VL 16:22Z) | DEAD | quarantine |
| 36 | `salience.box_live_birth` (off) | R58 §58.3 | a4_on @b1d94617 INERT (VL 16:41Z) | DEAD | quarantine |
| 37 | `salience.box_edge_birth` (off) | R58 §58.3 | a4b_on @54bd315b: box −2 FAIL (VL 16:41Z) | FAILED-OFF | quarantine |
| 38 | `salience.ev_route_box` (off) | R61 §61.4 | evb_on −3 box cl 6.00 FAIL; evb2 −3 FAIL; arm3 inert (VL 00:59Z/01:02Z/01:15Z) | FAILED-OFF | quarantine — superseded by C-3 EventBox |
| 39 | `salience.ev_route_pullback` (ON) | R61 §61.4 v2 | only meaningful under #38 (OFF); pb route itself measured net −3 box@1 (prov) | PENDING (ON under OFF parent) | tunable; `pb_birth` (row 44) is the kept sibling |
| 40 | `salience.ev_uip` (ON — C-3) | R62 §62.4 | uip2_pbbirth @8361fe85: box 16/119 =v0 parity, level 7/76, line 20/193, clutter 4.33, births 1.0/pan, suite 72/72 — folded into STABLE C-3 `1a550212` (VL 04:15Z/04:29Z; REQ §25) | **KEPT-ON (C-3 default)** | **fold** — EventBox is the parent mechanism |
| 41 | `salience.ev_uip_persist` (ON — C-3) | R62 §62.4 T1 | same row; close-veto at objects.py:55-64 | **KEPT-ON (C-3)** | **fold** — persistence is EventBox policy |
| 42 | `salience.ev_uip_lvfree` (ON — C-3) | R66 §66.3 V1 | level −4→−1 fix; three exclusion sites: levels.py:38-48, salience.py ~684-696, ~1370 (VL 03:33Z, REQ §23) | **KEPT-ON (C-3)** | **fold** — v2 invariant |
| 43 | `salience.box_v0_family` (off) | R63 §63.4 | PREPARED, never run (VL 03:10Z); R71 §71.1: A/B/C no longer needed for M1 | PENDING | quarantine — superseded |
| 44 | `salience.ev_uip_pb_birth` (ON — C-3) **(rev2-added row)** | R68 §68.3 V3 | the kept fixture cure: pb cand may *birth* the UIP object at v0's route gate `idx-t0a>=3` (engine.py:~365-380); V3 flips vs V1 +0/−0 on TUNE picks, suite 72/72 (VL 04:15Z, REQ §25) | **KEPT-ON (C-3)** | **fold** — EventBox birth route |
| 45 | `salience.ev_uip_pb_write` (off) | R66 §66.3 V2 | byte-flat +0/−0 on TUNE picks; V2 arm retired by R68; OFF in C-3 (VL 03:33Z, REQ §23/§25) | **INERT-OFF (retired)** | quarantine — **not** the kept mechanism (rev2 fix: earlier draft mislabeled it) |
| 46 | `salience.ev_uip_buildstart` (off) | R66 §66.4 | official A/B `uip2_bs @c06365ce`: **byte-flat +0** on every deliverable; offline span-IoU 9→14/20 didn't propagate to picks (REQ §24) | INERT-OFF (measured flat) | tunable — diagnostic field, zero M1 cost |
| 47 | `lifecycle.far_enabled` (ON) | R11/R14 | retire_far ~430 closes, ~0.2% bad (VL 20:33Z); noFar arm: **PL 19→22 up but LC 6→5 down** — mixed, kept OFF for the LC loss (VL 20:31Z; rev2 wording fix) | KEPT-ON | **fold** |
| 48 | `lifecycle.stale_enabled` (ON) | R11/R14 | same verification row; stale p95 50→72 bound (prov) | KEPT-ON | **fold** |
| 49 | `lifecycle.wall_exit_enabled` (ON) | R14 §14.3 | wall_exit 60 closes, 0 bad (VL 20:33Z) | KEPT-ON | **fold** |

## B. Key non-boolean parameters

| param | value | origin / measured | status | proposed fate |
|---|---|---|---|---|
| `salience.budget_signal/context/annot` | 3/2/4 | RT1 §4.4 | coupled layer | removed from birth path → joint economy question is open (arbiter demoted, ARCH_V2 §3.4) |
| `salience.budget_hard` | 9 | RT1 §4.4 | coupled layer | removed; replacement live ceiling = Σfamlive=6 (+note `n_act<9` leg must be explicitly replicated or dropped by decision — review (d)) |
| `salience.rate_total` | 5 | golden joint births p95 | coupled; **"never observed to fire in kept state" per ledger note — verify on cache before claiming removal is free** | removed from birth path (C1 arm) |
| `salience.rate_<kind>` (7 kinds) + `rate_default` | {1,2,1,1,2,1,1}+1 | golden per-kind p90 | kept mechanism | per-family ledgers (rev2: corrected "×8" phrasing) |
| `salience.rate_context` + `context_window_bars` | 2 / 288 | ctx flood ~10/day vs golden ~2/day (VL 20:31Z arm B kept) | kept | ContextPipe own day-window ledger |
| `salience.rate_mini_day` | 0 | sparse-kind day cap | off (0) | tunable inside LevelPipe |
| `salience.rate_label_tf` | 2 | B3(i): labels flooded 189→616 after marker.off (VL 14:43Z K9) | kept | AnnotPipe day cap; **measured: ≤2/run on 623 C-3 panels (caps_measure.py)** |
| `salience.fam_rate_<kind>` + `fam_floor` | 2/1/1/1/1/1/1/1 | R25 §25.5 + R34 C1 | superseded mechanism | become per-family rate caps (same values) |
| `salience.famlive_box/line/level/bracket` | 1/2/1/1 | R34 C1 author live@τ p90 | kept | per-family live caps (level gets LC 2 via `def_level_max_live`) |
| `salience.famlive_context` | 1 | R44 §44.2 | flag failed; value valid | ContextPipe live cap (C2 arm) |
| `salience.famcap_context_range/context_line/mini_level/squeeze` | 1/1/2/1 | R36 §36.3 golden per-panel max | kept | per-kind panel caps inside families |
| `salience.famcap_bracket` | **0** | R36 §36.3; arm −1 → set 0 | kept | **0 = UNCAPPED, not "cap 2"** (rev2 fix) — bracket family is uncapped on the panel today |
| `salience.fam_total_live` | 0 | R39 §39.6; caps FAIL (VL 07:01Z) | FAILED-OFF | removed from birth path |
| `salience.joint_struct` | 0 | R43 §43.4.2; caps FAIL (VL 08:23Z/09:04Z) | FAILED-OFF | removed; `_joint_drop` ordering survives only as a display-priority reference |
| `salience.min_score_birth` | 0.5 | DN_SALIENCE stage 5 | kept | per-family birth floor |
| `salience.min_score_birth_signal` | 5.0 | MEASURE-TUNE separator (prov) | **DEAD LEAF — never read in code** (rev2 fix: was listed "kept") | quarantine (propose removal to Owner) |
| `salience.nms_iou` / `nested_frac` | 0.5 / 0.5 | DN_SALIENCE §5 | kept | per-family same-kind NMS |
| `salience.hyst_margin` / `dwell_bars` | 3.0 / 24 | RT4 §10 + MEASURE-TUNE | kept | per-family displacement guards |
| `salience.cand_ttl_bars` | 24 | TTL=72 tried & reverted (prov) | kept | per-family pool TTL |
| `salience.post_break_demote` | 0.3 | carry grammar | kept | family scorer term |
| `salience.revive_max_bars` | 144 | REQ-1(b) | kept | per-family revive window |
| `salience.box_live_scope` | 0 | R56 A1 | DEAD | quarantine |
| `salience.box_prom_w` | 10.0 | R34 C1 | DEAD w/ flag | quarantine |
| `salience.line_dedup_abr` | 1.0 | R38 §38.5 | PENDING w/ flag | quarantine |
| `box.tail_bars` | 0 | R21 §21.3: A/B 1c24be53 — **not zero-delta: bracket .29→.31, clutter 10→11, "small but real"** (VL 21:47Z; rev2 fix) | OFF, measured small-negative | tunable (0) |
| `box.cong_min_bars` / `cong_h_abr` | 6 / 5.5 | BOX-LAB sweep; K6 kept (VL 09:04Z) | kept | BoxPipe params |
| `line.slope_floor` | 0.25 | R41 §41.4 K5 @75a9650c: line 19→20 (VL 06:58Z) | kept | LinePipe param |
| `level.def_*` (**20 leaves**, 21 incl. flag) | see file | LEVEL-LAB measured config R19–R24 | kept | LevelPipe params verbatim (rev2: corrected count) |
| `derived.*` / `lifecycle.far_abr`/`far_bars`/`stale_bars` | as file | R11 §11.4a + DN_TF | kept | lifecycle params verbatim |

## C. `.get()`-only code defaults absent from params (rev2 — review A-C9)

These leaves are read via `p.get(...)` and have no params_v1_1.json
entry — invisible to any ledger that only walks the file.

| leaf | in-code default | site | classification |
|---|---|---|---|
| `box.scan_lookback_bars` | 45 | boxes.py:735,739 | **live kept-path input** (congestion scan lookback) — add to params |
| `box.level_edges` | falsy (dormant) | boxes.py:133,752,871 | dormant probe (R42) — quarantine |
| `box.wick_birth` | falsy | boxes.py:641,679 | dormant — quarantine |
| `box.kde_edges` | falsy | boxes.py:664 | dormant — quarantine |
| `box.wait_ttl` | falsy | boxes.py:581 | dormant; ON would set box TTL = rate_window+cand_ttl — quarantine |
| `box.cong_piv_minrun` | 1 | boxes.py:920 | **live input** for ON route `cong_pivedge` — add to params |
| `box.cong_piv_minmem` | 1 | boxes.py:945 | live input — add to params |
| `box.cong_piv_topk` | 4 | boxes.py:948 | live input — add to params |
| `box.cong_piv_npairs` | 6 | boxes.py:968 | live input — add to params |
| `box.cong_piv_mininside` | 0.5 | boxes.py:984 | live input — add to params |
| `box.cong_piv_minsup` | 1 | boxes.py:986 | live input — add to params |
| `salience.ev_uip_pb_write`/`buildstart` | falsy | engine.py:400-411,447-449 | params leaves exist (OFF) — listed in §A; handling sites noted |

## D. Reading for the build lane (rev2)

- **Fold set** = the 21 ON flags + kept params = STABLE C-3 as-is.
  Nothing in the fold set changes a measured value.
- **Quarantine set** = FAILED-OFF/DEAD/PENDING flags stay in params
  (Owner's file); v2 code never reads them.
- **Promotion note (corrected)**: the EventBox mechanism is no longer a
  promotion — it IS the C-3 parent (`ev_uip`+`persist`+`lvfree`+
  `pb_birth` ON). What remains pending: `pb_write` (inert, retired),
  `buildstart` (byte-flat, diagnostic), and the `_ev_uip_born`
  reset-boundary decision for continuous runs (ARCH_V2 §4).
- **Margin note** (review M-C3): kept row margin is 110/179 (V3), not
  111 — the 111 figure was V1 `uip2_lvfree`.
