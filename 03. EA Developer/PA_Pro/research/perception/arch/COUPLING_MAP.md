# COUPLING_MAP — every cross-family state read / shared quota in v1

Lane: ARCH (R67 §67.3; rev2 under R72 §72.3).

## rev2 changes (answers ARCH_REVIEW "fixes required" items 1 & 8)

- **Re-anchored every cite to the post-A1–A5 tree** (`2d497427`):
  `engine.py` is now 882 L (`_ev_uip_step` 329–455, `update` 458,
  `_v0_sync` 551, `_retire` 596, `_squeeze_exit` 636, `_mk`/`_birth`
  223/226); `salience.py` is the post-A4 stage split (`round` 530 →
  `_grave_sweep` 542, `_yield_sweep` 570, `_score_pass` 622,
  `_grant_pass` 668, `_admit_one` 699, `_yield_birth` 1211,
  `_ctx_convert` 1248, `_displace` 1312, `_joint_pass` 1453,
  `_pool_sweep` 1483); `Candidate`/`_band_of`/`FAMILY` moved to
  `kernel.py` (A1); `Obj`/`ObjectStore` to `objects.py` (A2).
  All `boxes/levels/lines/patterns.py` cites unchanged (files untouched).
- **Added the two missing cross-family channels** (review A-C2):
  `boxes.py:1288 e.patterns.relabel` (box→annot *rewrite* of live
  LABEL_TF) and `lines.py:422 e.patterns.label` (line→annot *birth*).
- **Corrected the UIP birth description** (review A-C8): the event
  object is born by a **direct `self._birth` call at engine.py:445** —
  no pool admission, no rate-ledger spend, no `slot_free` check. The
  measured level −4 channel was *occupation* of `live`/`n_act` plus
  edge seeding (both now excluded by lvfree), not admission
  competition. Table rows below corrected.

"Family" = the kinds grouped by `kernel.FAMILY` (`kernel.py:15-21`:
box: BOX/RANGE_OPEN/CONTEXT_RANGE; line: PATTERN_LINE/CONTEXT_LINE;
level: LEVEL_CARRIED/MINI_LEVEL; bracket; squeeze; annot: LABEL_TF/
BAR_MARKER) and `budget_class` (signal/context/annot). Note
(review A-C6): CONTEXT_RANGE/CONTEXT_LINE still sit inside the box/line
families in the current tree — a separate context family exists only
under the failed `fam_context` flag; v2's ContextPipe is a **new**
split, not current behaviour.

Coupling types:
- **Q = shared quota/ledger** — one family's spend can deny another's
- **R = state read** — a family's decision reads another's objects
- **B = birth/rewrite channel** — one family creates or mutates
  another's objects
- **D = display/displacement** — visibility/rank decided across families

Measured-cost column cites VERIFY_LOG timestamps / REQUESTS / params
provenance.

## 1. `salience.py` — the shared tournament (densest coupling)

| loc (current tree) | type | source → target | what is read / mutated | measured cost |
|---|---|---|---|---|
| `_revive_target` :338-357 | R | any family → e.objects | revive scans `reversed(e.objects)` of **same kind** — internal, keep; order-dependent (objects-append order) | none |
| `_joint_drop` :410-452 | D/R | joint → **all structural families** | drop order reads every live structure; the "keep breakout side" test reads the *box object's* broke state (`bside`, ~:439-447) to decide which LINES survive | joint_struct cap4: lvl−4 line−4; cap3: lvl−3 line−4 brk−7, clutter 5.33 (VL 08:23Z/09:04Z) |
| `_suppressed` :474-520 (flag-off branch) | D | cand → all same-**family** cands+live | NMS groups by FAMILY — CONTEXT_RANGE shadows BOX in the same family | fixture debt: context holds box slot → 7 named theory fixtures fail (VL 06:52Z); `fam_budget` same-kind branch is the kept path |
| `_score_pass` :622-666 (`o.score` writes :638-639; ev `+100` grant :653-664) | D | ev box → all families' exposure | one score map over all families; the event object's `o.score`/`geometry["sali"]["score"]` get +100 vs every family's ranking | part of uip2's pick dominance; note: `o.score` is **invisible to `canonical()`** — the identity oracle can't see it (review (c)) |
| `_grant_pass` :668-697 + order sort :673-676 | Q | all families | one `sorted(pool, key=(-score,kind,route,t0,repr(sorted(geom))))` over one pool → interleaved births couple ids across families; `box_young_first` rewrites `order[k]` positionally (:685-690) | ordering is the birth-order contract (A-C11: **no fixed family admit order exists today**) |
| `_admit_one` class budgets :740-753 | Q | cand → ALL live objects | `live` (class pool), `n_act` (all actives), `slot_free` = `len(live)<cap and n_act<9` (`budget_hard`) | uip2 level −4 channel (occupation, VL 02:47Z); famoff arms worse everywhere (VL 07:36–07:38Z); fam_ledger arm (b): BOX −2 "budgets NOT fully separate" (VL 22:41Z §27.2.2) |
| `famlive_*` branch ~:755-770 | Q | cand → same-family live only | **own-family** read — the v2-correct branch | none (this is what v2 keeps) |
| `fam_total_live` :775-781 | Q | cand → ALL actives | joint live cap | caps 4/3/2 all FAIL M1 (VL 07:01Z; 10c34e28/fbb3a173) |
| `fam_caps` ~:790-806 | Q | cand → same-kind born count | per-panel kind cap over e.objects — own-kind, keep | kept (per-kind); **note `famcap_bracket=0` = uncapped** (review A-C5) |
| `rate_label_tf` ~:806-818 | Q | LABEL_TF → e.objects count | own-kind day count over whole object array — internal | kept (moves into AnnotPipe) |
| rate ledger ~:880-940 | Q | every birth → **joint** ledger | `rate_<kind>` own-kind OK; `total`/`rate_total` (:935), `ctx_full`, `mini_full`, `joint_full` reads are JOINT | uip2 level −4 (VL 02:47Z); def-MINI births spent ~43% of shared pool (prov `def_mini_off`); **ledger note: `rate_total` "never observed to fire in kept state" — VERIFY ON CACHE before claiming removal is free** (review (d)) |
| `lc_score_pick` :975 | D | LC cand → LC incumbents | same-kind slot transfer; mutates shared `_births` (slot swap) | OFF; concept kept per-family |
| `box_score_pick` :1041 (`_prio` :1105) | D | box cand → box incumbents | same-family slot transfer | kept ON (K4 +4 box) |
| `ctx_yield` :572-585 (sweep), :708-728, :1182-1186 + `_hidden_ctx` :81/:597-619/:1244 | R+D | signal cand → CONTEXT objects | `blockers` scan live context objects to suppress signal births; hide = `state` toggle + `_hidden_ctx` restore list | flag failed (VL 07:52Z); hide-not-evict semantics = the only existing "hide" machinery (see arbiter decision, ARCH_V2 §3.4) |
| `_ctx_convert` :1248-1310 | R+**mutation** | box cand → CONTEXT_RANGE object | converts a live CONTEXT_RANGE into a BOX (mutates type/state/geometry) | loose-overlap variant: 186 converts, level −4 line −3 (in-code note) |
| `_displace` :1312-1451 | D | cand → incumbents of **class** or family | under `budget_class`: displacement pool = whole class (a level can evict a line); under `fam_budget`: same family; under `box_prio`: whole box family incl. context-class members | box_prio: level −3/−4 clutter 6.00–6.33 (VL 07:32Z/07:36Z) |
| `_joint_pass` :1453-1481 (`joint_struct` :1461-1467) | Q | cand → ALL structural objects | count + victim pick across families | FAIL caps (VL 08:23Z) |
| `_pool_sweep` :1483+ | — | all | expire/keep pool rows | fine (moves per-family) |

## 2. `engine.py` — orchestration couplings

| loc (current tree) | type | source → target | read/mutate | measured cost |
|---|---|---|---|---|
| pivot fan-out inside `update` (:489-503) | dispatch | engine → all books | pinned order: `patterns→levels→boxes→reanchor→context_range→ev→lines` | none itself; order is the birth-order contract |
| tracker/maintain order (:505-519) | dispatch | engine → all books | pinned order: `asia_update→congestion_scan→session_update→maintain×4→_retire→round` | none itself; pin verbatim for B4 |
| `_retire` :596 + `_squeeze_exit` :636 | R | generic → all actives | `far/stale` own geometry; wall reads cross families via `_band_of`; `_squeeze_exit` reads `wo.state` mid-sweep → **close order is observable** (why A6 was BLOCKed/reverted) | wall_exit 60 closes 0 bad (VL 20:33Z) — keep semantics |
| `_ev_uip_step` :329-455 | R+B | event box → direct `_birth` | reads `book.seq` (shared), writes one Obj via **`self._birth` at :445 — bypasses pool, rate ledger, `slot_free`**; per-run latch `_ev_uip_born` (:133 init, :417 read, :451 set — never reset) | uip2_on level −4 was **occupation + edge seeding**, not admission competition (VL 02:47Z; mechanism REQ §20); lvfree → −1 (VL 03:33Z) |
| `stand_aside`/facts ~:790-860 | R | output → active set | output-layer reads, post-selection | none (v2 keeps as output read) |
| `_v0_sync` :551 | mirror | v0 engine → e.objects | verbatim mirror objects bypass budgets — option-B prep, never run; relies on "mirrors never receive ACTIVE state writes" invariant (objects.py setter auto-registers `_act`) | n/a |

## 3. `boxes.py` — box → others

| loc | type | read/mutate | v2 resolution |
|---|---|---|---|
| L251, 729, 802, 997, 1110, 1319 `e.active("BOX")` | internal | own-family dedup/cover — correct | keep |
| L374-395 `_near_structure` | R | box generation reads **all** `e.active()` for a near edge — **and scans `e.bars[:bs]`, an O(run-history) unbounded scan** (review A-C3) | EDGE_BOARD for the object part; the bars scan needs a stated window bound |
| L1050-1054 `propose_context_range` | R | context route reads `active("BOX")+active("CONTEXT_RANGE")` containment | ContextPipe reads EDGE_BOARD |
| L1179-1283 `maintain` | B+D | on break: `e.levels.spawn` (L1212 broken edge, L1220 congestion_edge); on poke: `e.patterns.label` (L1201, L1279); **`e.patterns.relabel` L1288 — box→annot rewrite channel (rev2 added)** | emit `BOX_BROKEN`/`BOX_OTHER_EDGE`/`EDGE_POKE`/`EDGE_RELABEL` events |
| L1219-1223 | B | box break seeds level candidates; **event-box edges seeded levels via the origin path** — the lvfree veto at levels.py:38-48 is the patch | invariant: EventBox emits no level-seeding events |
| `_ttl` L571-583, call sites L283/568/597/831/1024/1165 | internal | candidate TTL (kept-path function — `wait_ttl` arm is dormant) | **moves into BoxPipe, NOT quarantine** (review A-C4) |
| `asia_update` ~L1075-1168 | R | reads active("BOX") covering — own family; `_asia` dict + `meta live_tracker` back-link (objects.py:147) | keep; dict-order contract for port |

## 4. `levels.py` — level → others

| loc | type | read/mutate | v2 resolution |
|---|---|---|---|
| L38-48 `ev_uip_lvfree` veto | R | level generation inspects a **box object's** meta flag to veto its edges as seeds | invariant: EventBox publishes no level-seeding edges — veto disappears |
| L42, L72-76 src inherit | R | spawn reads the **source object** (box/line/bracket) feats to inherit salience | **event payload must carry parent feats verbatim** (review fix 8) |
| L50-58 dedupe | internal | own-family | keep |
| L192-193, 235-290, 341-401 maintain/origins | internal | own-family reads; `origins` registry — **theta origins never expire → unbounded** (measured max 52/panel, caps_measure.py) | keep; port needs eviction policy |
| ~L310 `_budget_ok` | R | defended birth counts pending cands **in the shared pool** | reads LevelPipe's own pool — internal in v2 |
| L370 note | Q | comment: LC-only arm skips shared `rate_total` spend | ledger is per-family in v2 |

## 5. `lines.py` — line → others

| loc | type | read/mutate | v2 resolution |
|---|---|---|---|
| L288-311 `_eval` re-anchor, L317-336 revive | internal | own-family | keep |
| L57, L260 `book.alive()` | shared | observation layer — **append-only, never pruned → unbounded per-bar scan** (review A-C3) | windowed alive view for port |
| L369-380 | shared | reads `e.dc` | fine |
| **L422 `e.patterns.label` (rev2 added)** | B | line→annot birth channel on poke/traverse | `EDGE_POKE` event → AnnotPipe |
| L449-452 `maintain` | B | `e.levels.spawn("broken_line_edge")` on pierce | `LINE_BROKEN` event |

## 6. `patterns.py` — annot/bracket/squeeze → others

| loc | type | read/mutate | v2 resolution |
|---|---|---|---|
| L67-82 marker `live_anchor` | R | scans **all** actives for anchor | EDGE_BOARD (route suppressed by marker.off) |
| L134-160 `_brackets` | shared | reads book streams | fine |
| L191-197 bracket relevance | R | reads all active bands to skip redundant brackets | EDGE_BOARD |
| L205-209 | internal | own-kind dedupe | keep |
| L224-225 `_emit_bracket` | B | `e.levels.spawn("formation_mid")` | `FORMATION_MID` event |
| L250-268 `squeeze_scan` | R | scans all actives as walls + EMA | EDGE_BOARD |
| L309-348 `label`/`relabel` | B | creates/rewrites LABEL_TF bound to a parent box/line edge | `EDGE_POKE`/`EDGE_RELABEL` events → AnnotPipe |

## 7. The measured cases (coupling → damage)

| case | coupling path | measured damage |
|---|---|---|
| uip2_on level −4 | ev edges → level seeds (spawn/origins) + persistent box occupying `live`/`n_act`/`fam_total_live`/`joint_struct` | level 8→4/76 while box hit parity (VL 02:47Z; mechanism REQ §20; fixed to −1 by lvfree VL 03:33Z) |
| fam_ledger (b) BOX −2 | per-kind shares + shared live/displacement | VL 22:41Z §27.2.2 "budgets NOT fully separate" |
| joint caps | `fam_total_live`, `joint_struct` | every cap arm FAIL (VL 07:01Z, 08:23Z, 09:04Z; gate pack C1 summary) |
| box_prio family-wide displacement | `displaceable` spans whole box family incl. context | level −3/−4, clutter 6.00–6.33 (VL 07:32Z/07:36Z) |
| fam_context split at birth | context objects competed with box for box slot | level −2, clutter 5.67 (VL 07:52Z/08:08Z) — correct idea, wrong layer |
| K3 fixture debt | CONTEXT_RANGE in box family + famlive_box=1 → no BOX birth | 7 named theory fixtures fail (VL 06:35Z/06:52Z) |
| shared rate_total spenders | def-MINI births, marker flood, LABEL_TF flood | prov notes; B3(i) cap kept (VL 14:43Z); **`rate_total` never observed to fire in kept state** (ledger note — verify on cache before claiming removal is free) |
| ctx_convert | direct type-mutation of a live context object | loose variant level −4 line −3 (in-code note) |

## 8. v2 resolution rule

Every row above resolves to one of three forms:

1. **internalized** — the read was already same-family (`famlive_*`,
   `fam_caps`, same-kind NMS, revive, slot transfers): it moves inside
   the family pipeline unchanged.
2. **evented** — birth/rewrite channels (`e.levels.spawn`,
   `e.patterns.label`, `e.patterns.relabel`) become typed events
   consumed by the owning family's `ingest()`; emission is **synchronous
   at the exact call site** and payloads carry the source object's
   inherited feats (MIGRATION_PLAN B6 spec).
3. **arbitrated or boarded** — joint quotas and cross-family active-band
   reads become either arbiter display rules (demoted — see ARCH_V2
   §3.4 decision) or flat EDGE_BOARD facts (bands at bar i, objects-
   append order, never mutable state).

No fourth kind remains.
