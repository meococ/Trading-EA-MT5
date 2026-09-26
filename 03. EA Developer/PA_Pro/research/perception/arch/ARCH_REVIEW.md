# ARCH_REVIEW — neutral audit of the Perception-Architecture v2 drafts

Lane: ARCH-REVIEW (Lead 23/09 04:15Z, Ruling 70 §70.3). Reviewer did not
write the drafts. Read-only audit: no engine/test/fixture/param/draft files
touched. Evidence order: current source tree > `status/results.jsonl` >
`evalcheck/VERIFY_LOG.md` (VL) > `boxlab/REQUESTS.md` / `boxlab/BOX_LOG.md` >
`PERCEPTION_LOG.md` (PL) > rulings.

## 0. Tree state at review time (04:37Z)

The tree moved twice since the drafts were finished (ARCH lane 04:01Z):

1. **STABLE C-3 folded 04:17Z** — `1a5502129b4c1554` = @8361fe85 +
   `uip2_pbbirth` defaults: `ev_uip=T, ev_uip_persist=T, ev_uip_lvfree=T,
   ev_uip_pb_birth=T`; `pb_write`, `ev_uip_buildstart`, `box_v0_family`
   remain OFF (PL 04:17Z; REQUESTS §25). The current parameter tree IS C-3.
2. **MIGRATION A1 landed 04:24Z @18ea3147** — `kernel.py` (121 L) now holds
   SIGNAL/CONTEXT/ANNOT/FAMILY/budget_class/Candidate/footprint_overlap/
   band_of/sig/sig_obj; `salience.py` re-exports them. Logged check:
   id 198/198 TUNE + suite 72/72 (PL 04:24Z).
3. **A2 landed after the last log entry** — `objects.py` (152 L) holds
   `Obj` + `ObjectStore`; `engine.py` keeps `objects`/`_act`/`active()`/
   `_mk`/`_birth` as property shims plus `__setstate__` routing for legacy
   pickles. **No id-check or suite line is logged for A2 at review time.**
4. File sizes now: `engine.py` 853 L (was ~938–945 at draft time),
   `salience.py` 1412 L (was 1501), `kernel.py` 121, `objects.py` 152,
   `boxes.py` 1358 (untouched). Every absolute `engine.py`/`salience.py`
   line cite in the drafts is therefore stale by ~90 lines.
5. Suite of record = `research/perception/tests/` = **72 collected**
   (PL 03:56Z correction; REQUESTS §25). All draft references to "67/67"
   mean the wrong-directory EA suite and must be re-read as such.
6. Canonical identity convention in the logs is "OFF-id NNN/NNN vs base
   cache" on **576/1728** runs. A1's logged check covered 198 TUNE runs.

---

## (a) Code claims — drafts vs current tree

### Verified true (content exists; refs given at CURRENT lines)

| claim | current location | verdict |
|---|---|---|
| `Candidate` is a slots record; `geom/feats/meta` dict-copied; `_logged` set | `kernel.py:31-50` | TRUE — note: **no `fam` slot** (A5 needs `__slots__` update) |
| pool sort `(-score, kind, route, t0, repr(sorted(geom.items())))` | `salience.py:638-641` | TRUE — matches the draft's per-family comparator exactly |
| ev `+100` rank grant writes `o.score` and `o.geometry["sali"]["score"]` | `salience.py:622-633` | TRUE |
| shared class budget `live`/`n_act`/`slot_free`, `budget_hard=9` | `salience.py:686-697` | TRUE — draft cited `salience.py:651-667`, which is the ctx_yield comment block; wrong range even at draft time |
| `famlive_*` same-family branch (the kept branch) | `salience.py:698-722` | TRUE |
| `fam_total_live`, `joint_struct` gates exist, OFF | `salience.py:723-731, 1363-1373` | TRUE |
| `lc_score_pick`, `box_score_pick`, `ctx_yield`, `ctx_convert` | `salience.py:923, 989, 555-558/1130, 1165-1225` | TRUE |
| `_revive_target` scans `reversed(e.objects)` — order-dependent | `salience.py:323-357` | TRUE |
| UIP step, persist close-veto, lvfree exclusions | `engine.py:314-442`; `objects.py:55-64`; `levels.py:38-48`; `salience.py:684-696, ~1370` | TRUE |
| box→level spawn (`congestion_edge` etc.), box→annot `label` | `boxes.py:1212, 1220, 1201, 1279` | TRUE |
| `_band_of` point band for priced/line objects | `kernel.py:83-94` | TRUE — a wall's band resolves to one edge price |
| `asia_update`, `propose_context_range`, `maintain` sites | `boxes.py` as cited | TRUE (boxes.py unchanged) |

### Mismatches / missing claims

- **A-C1. All `engine.py`/`salience.py` line cites are stale post-A1/A2.**
  Examples: `_retire` cited ~L606 → now `engine.py:573`; `_squeeze_exit`
  ~L692-724 → now `engine.py:607-640`; `_ev_uip_step` L406-524 →
  `engine.py:314-442`; `_v0_sync` ~L622 → `engine.py:532`; salience block
  cites shifted ~90 lines up. Content exists; re-anchor to names, not lines.
- **A-C2. `COUPLING_MAP` misses two cross-family call sites:**
  `boxes.py:1288` `e.patterns.relabel(i, o, top, bot, hgt)` — a box→annot
  *rewrite* channel, and `lines.py:422` `e.patterns.label(...)` — a
  line→annot birth channel. §5 lists line→level spawn only. Any event-bus
  design that does not carry `relabel` will silently drop live LABEL_TF
  rewrites.
- **A-C3. "All kept-path lookbacks ≤ 600 bars" is false.**
  `boxes.py` `_near_structure` (~L385-390) computes
  `max(x["h"] for x in e.bars[:bs])` / `min(...l...)` — an O(run-history)
  scan bounded only by run length. Also `lines.py` `_lab_line_score`
  iterates `e.book.alive()` (append-only, never pruned), `levels.py`
  `_update_origins` iterates the full `origins` registry (theta origins
  never expire), and `engine._dome_update` scans `book.alive()`. Per-bar
  cost grows with run length; only windowed *lookbacks* are capped.
- **A-C4. `ARCH_V2 §6` quarantines `_ttl`, but kept paths call it:**
  `boxes.py` candidate construction (~L281-283, ~L568, ~L831, ~L1024,
  ~L1165 asia route). `_ttl` must live in BoxPipe, not quarantine.
- **A-C5. "Bracket panel cap 2" is wrong:** `famcap_bracket = 0`, and the
  `famcap_*` check treats 0 as no cap. The bracket family is uncapped on
  the panel today.
- **A-C6. `FAMILY` still groups CONTEXT_RANGE→box, CONTEXT_LINE→line**
  (`kernel.py:15-21`). A separate context family exists only under
  `fam_context` (OFF, measured FAIL). Drafts that describe a permanent
  ContextPipe must state this is a *new* split, not current behaviour.
- **A-C7. `_ev_uip_born` is a per-engine-lifetime latch**
  (`engine.py:121` set False, `:436` set True, never reset — the
  day-boundary block `:456-464` does not touch it). "One object per panel"
  holds only because each eval panel runs a fresh engine. The architecture
  and port plans must define the reset boundary (day? panel? session?) —
  today it is "one per run".
- **A-C8. The UIP object does NOT go through the shared birth path.**
  `_ev_uip_step` calls `self.salience.score(cand)` then `self._birth`
  directly (`engine.py:432-436`) — no pool admission, no rate-ledger
  spend, no `slot_free` check. COUPLING_MAP's "birth goes through shared
  birth path → competes in joint quotas" is wrong; the measured level −4
  channel was *occupation* of `live`/`n_act` (which lvfree now excludes),
  not admission competition. This distinction matters for B5.
- **A-C9. `.get()` defaults absent from params and ledger:**
  `scan_lookback_bars`, `level_edges`, `wick_birth`, `kde_edges`,
  `wait_ttl`, `cong_piv_*`, `ev_uip_pb_write`/`buildstart` handling.
  Each needs a stated default + classification (kept-path input or dead).
- **A-C10. `min_score_birth_signal` (5.0) is never read** — dead leaf;
  FLAG_LEDGER §B lists it as a kept birth floor.
- **A-C11. No fixed family admit order exists today** — `round()` sorts
  one pool by score; B6's `[box, line, level, bracket, squeeze, annot,
  context]` is new behaviour, not an existing invariant.
- **A-C12. v2 modules:** `kernel.py`/`objects.py` now exist (A1/A2
  landed); `pipes.py`, `Engine2`, `Arbiter` still absent — the §6 module
  map remains aspirational beyond A2.

---

## (b) Measured claims — drafts vs logs

### Verified correct

- `uip2_on` 16/119 box (+6, v0 parity), level −4, line +3, clutter 4.67,
  births 1.0, live@τ 9.0 — VL 02:47Z, REQUESTS §20. Drafts correctly
  distinguish `uip_on` 7/119 (strict lifecycle) from `uip2_on` 16/119.
- `uip2_lvfree` / `uip2_pbbirth` rows: box 16/119, level 7/76, line
  20/193, bracket 29/85, clutter 4.33, births 1.0 — VL 03:33Z / 04:15Z,
  results.jsonl @8361fe85 KEEP.
- Level −4 mechanism (edge seeding `9.40c` + slot suppression `9.61c`) —
  REQUESTS §20 correction, VL 02:47Z.
- K1 lab_score (line 16→18, box 2→3, level 1→4, clutter 5.00), K2
  defended pair (level 4→6), K3 bxcombo (box +1, line +2) — VL.
- box_prio (level −3/−4, clutter 6.00–6.33), famoff (level −2, line −7,
  clutter 5.67), fam_context (level −2, line −1, clutter 5.67),
  joint caps (4/3/2 FAIL), fam_ledger (BOX −2, "budgets NOT fully
  separate" VL 22:41Z) — all verified.
- Event-box live at τ in 15/15 event-golden cells — REQUESTS §19 assist.
- STRICT live@τ ≈ 2.00 parent / 2.33 lvfree — VL 02:24Z, 03:33Z §66.5.
- `build_start` offline IoU 9→14/20, official A/B byte-flat (+0) —
  REQUESTS §20/§24, VL 03:52Z.
- DR-BOX youngest-either 20/51 vs rd 18/38 — REQUESTS §21 item 2.

### Mismatches

- **M-C1. "67/67" suite references are stale.** Suite of record is 72
  tests; C-3 is 72/72; earlier "67" was a wrong-directory collection
  (PL 03:56Z). MIGRATION_PLAN's baseline oracle must be re-anchored.
- **M-C2. `pb_write` is not the kept mechanism.** V2 (lvfree_pb) was
  byte-flat on picks and retired by R68; `ev_uip_pb_write` is OFF in C-3.
  The kept fixture cure is `ev_uip_pb_birth` (pb cand may *birth* the UIP
  object at the v0 route gate `idx-t0a>=3`, `engine.py:~365`). ARCH_V2
  §4/B5's "ON = uip2_lvfree_pb + build_start" describes an arm that was
  never kept: it adds `pb_write` (inert), adds `buildstart` (byte-flat
  but OFF in C-3), and omits `pb_birth` (the actual fixture cure).
  EventBox must be spec'd on the C-3 semantics, not the retired V2.
- **M-C3. margin discrepancy is real but benign:** `uip2_pbbirth`
  margin 110/179 vs `uip2_lvfree` 111/179 (results.jsonl). Clutter median
  identical 4.33; one panel sits at the ≤5.0 boundary differently. Not an
  M1 failure — but the drafts quoting 111 for the kept row are stale.
- **M-C4. Reachable-set denominators differ by source and must not be
  mixed:** BOX-LAB ruler-exact reachable = 46/119 (R66 throttle matrix);
  DR-BOX reachable = 51/119 (youngest pick 20/51); event-golden cells =
  15 (T1 5/15). Drafts citing "46" or "51" need the right attribution.
- **M-C5. `retire_far OFF` did not lose both PL and LC** — VL 20:31Z:
  pattern-line recall rose 19→22 while level recall fell 6→5. Ledger
  wording "noFar arm loses PL/LC" is inaccurate.
- **M-C6. `box.tail_bars` "ZERO delta" claim is contradicted by VL
  21:47Z** — tailON moved bracket .29→.31 and clutter 10→11: "small but
  real". The flag stays OFF, but the record is not zero-delta.
- **M-C7. Ledger leaf counts:** `level.def_*` has 20 leaves (21 incl.
  `defended_origin`), not 19; `rate_<kind>` is 7 kind rates +
  `rate_default`, the "×8" phrasing is loose (values {1,2,1,1,2,1,1,1}
  match params).

---

## (c) Identity safety — MIGRATION_PLAN steps

The OFF-identity oracle is `evalcheck/cache.py:canonical()` — pickled
`(type, why, t_birth, t_left, t_right, state, id, geometry, events)` per
object + `cand_log` + `bars`. **Blind spots the plan must know about:**
`o.score`, `o.priority`, `o.role`, `o.touches`, `o.style` are *not* in the
canonical tuple — an OFF-path regression that only perturbs scores passes
the gate yet changes ranking inputs (m1_row ranks by object-carried score
first). Any arbiter/score step must extend the oracle or add an M1-level
check. Pickle-compat for moved classes is handled (salience re-exports,
engine `__setstate__` routes `objects`/`_act`, `Obj.__setstate__` maps
legacy `state`), but only because the A1/A2 author added those shims —
they are load-bearing, call them out in the plan.

| step | verdict | why / required fix |
|---|---|---|
| **A0** (oracle: flag-OFF byte-equal on canonical) | **OK** | Oracle exists (`canonical()`); convention 576/1728 established. Fix-forward: extend the tuple with `score/priority/touches` before B3. |
| **A1** (kernel.py move) | **FIX** | Landed @18ea3147, bodies verbatim, re-exports keep `salience.X` and pickle `find_class` working, 198/198 TUNE + 72/72 logged. **But the plan's gate is the 1728-run canonical set — only TUNE 198 is logged.** Run the full canonical check before building on it. |
| **A2** (Obj/ObjectStore) | **FIX** | Landed on disk; `birth()`/`mk()` verbatim-modulo-`eng`; `objects`/`_act` property shims consistent; no `self.objects=`/`self._act=` writers exist; `_oi` predates C-3 so loaded pickles keep working. **No id-check or suite line is logged at all.** Also a latent contract change: `Obj.state` setter auto-registers in `_act` — `_v0_sync` mirrors rely on never receiving an `ACTIVE` write (true today only because engine_v0 never revives). Log the check + note the invariant. |
| **A3** (wrapper methods) | **FIX** | Shims as written (`active()`→`store.active()` etc.) are pure delegation — but the plan must enumerate *every* call site that mutates `e.objects`/`e._act` directly (`_v0_sync` appends to `e.objects`; `salience` iterates `e.objects`) and state that the shims return live references, not copies. Order of `maintain→_retire→round` (`engine.py:505-519`) is the birth-order contract — pin it textually. |
| **A4** (`round()` decomposition) | **FIX** | `round()` is one 900-line method (L515-1400+). Extraction must preserve: local-variable lifetime (`live`, `n_act`, `slot_free`, `order`, `prio_live`), `cand_log` write ordering interleaved with `_logged` mutation, the `box_young_first` positional rewrite (`order[k]=c`), and exception paths. Feasible but not mechanical — require per-extraction canonical diff. |
| **A5** (`c.fam` tag) | **FIX** | `Candidate.__slots__` lacks `fam` (`kernel.py:33-34`) — `c.fam =` raises AttributeError without a slots update; that changes pickle shape for cached engines (harmless: hash-keyed, and `fam` absent in old pickles → must be read via `getattr(c,"fam",None)` or set in `__init__`). Pool/cand_log untouched → doable, but the step as written ("add attribute") understates the slots/pickle work. |
| **A6** (pin family admit order) | **BLOCK** | `active()` returns objects-append order (sorted `_act` keys — `objects.py:102-109`); `_retire` iterates it while `_squeeze_exit` reads `wo.state` mid-sweep (`engine.py:607-640`) → close order is observable. Replacing index-order iteration with `[box,line,level,...]` is a behaviour change, not a move — an object closed earlier/later changes wall reads and id assignment. Re-frame as a measured arm or preserve index order inside the retire sweep. |
| **B1** (shadow pools) | **FIX** | Spec must forbid: double-`propose` (the pool is also the `_grave*`/ttl machinery), `_logged` divergence between pools, and any second `order` sort. Pool lifetime is shared mutable state (`_suppressed` scans same-family pool+live) — shadowing it per family changes NMS inputs. OFF must bypass construction of the shadow pools entirely, not just their decisions. |
| **B2** (split admission) | **BLOCK** | Per-family admission changes: tie order across families (today one `order` sort interleaves births → ids differ), `rate_total` joint ledger reads, `budget_hard`/`n_act` joint counts, float accumulation order in `score`. "OFF == parent" requires the OFF path to run today's monolithic loop verbatim — then ON is a new behaviour arm needing its own A/B, which the plan under-states. |
| **B3** (arbiter shadow) | **BLOCK** | (i) `o.exposed` reaches no consumer — see (d): the ruler reads `state`/drawn span only. (ii) Any score/priority writes are invisible to `canonical()` — the identity oracle cannot see this step's regressions. (iii) "hide = DELETED + restore" needs the `_hidden_ctx`-style restore machinery spec'd (a DELETED object leaves `active()`, `maintain`, wall reads — lifecycle freezes, contradicting "keeps running"). Specify the mechanism first; then it's an ON-arm A/B, not a shadow. |
| **B4** (event dispatch) | **FIX** | Pivot fan-out order (`patterns→levels→boxes→reanchor→context_range→ev→lines`, `engine.py:489-503`) and tracker order (`asia_update→congestion_scan→session_update→maintain×4→_retire→round`, `:505-519`) must be pinned verbatim; dispatching the same calls through a hub preserves order only if the hub is synchronous and FIFO. Synchronous queued events still reorder vs today's inline mutations unless emission order is pinned. Doable — write the order contract explicitly. |
| **B5** (EventBox port) | **BLOCK** | Three problems: (1) spec is stale — port the C-3 semantics (`pb_birth` gate, `pb_write`/`buildstart` OFF), not "lvfree_pb + buildstart"; (2) the birth bypasses salience entirely (`_birth` direct) — "inside BoxPipe with own budget" is a new placement needing an ON-arm measurement, and ON cannot be id-identical by design (new objects → new ids → canonical diffs; that's expected — say so); (3) `_ev_uip_born` is per-run not per-panel — define the reset boundary. Also port the lvfree exclusions at *three* sites (`levels.py:38-48`, `salience.py:684-696`, `~1370`). |
| **B6** (typed events replace direct calls) | **BLOCK** | Synchronous `emit` is not byte-neutral: today's calls are inline mutations (`e.levels.spawn` inside `boxes.maintain`, `e.patterns.label/relabel`). An event bus inserts a dispatch frame and — unless emission is synchronous at the exact call site — shifts mutation timing across the `maintain→retire→round` boundary. `levels.spawn` inherits feats from the *source object* (`levels.py:42-76`) — the event payload must carry those, or generation diverges. Fix: pin emission points + payloads, or keep direct calls behind an interface. |
| **B7** (EDGE_BOARD replaces `e.active()` scans) | **BLOCK** | Not a drop-in: `_near_structure` iterates `e.active()` for *any* near edge; `_revive_target` needs `reversed(objects)` incl. CLOSED (board of *active* edges can't serve it); `_squeeze_exit` reads wall bands by id incl. point-band lines (moving edges — board must refresh per bar); `levels._budget_ok` reads the shared *pool*, not objects. Unspecified: board capacity 32 vs worst case, stale-entry eviction, price rounding (float equality vs `repr`), duplicate edges, and ordering (consumers needing first/last-match order must get objects-order, not (kind,price)-order). Spec each consumer's required view before building the board. |

---

## (d) Design soundness — does the architecture preserve the economy?

**The display arbiter as spec'd is invisible to the ruler.** Two separate
measured quantities are conflated in the drafts:

- M1 `clutter` = `n_eng/n_gold` where `n_eng` = every object whose drawn
  span intersects the panel (`eval.py:107-145, 357` — `eng_objects`
  iterates `e.objects` regardless of `state`). Nothing the arbiter does
  post-hoc reduces it — the ink was already drawn. Only fewer births or
  shorter spans move clutter. "clutter at τ → ~1 live" (ARCH_V2 §5.3)
  mixes the live@τ diagnostic with the clutter metric.
- M1 recall@k uses `live_records` = `state != "DELETED"`
  (`evalcheck/snapshot.py:77-85`). `o.exposed=False` reaches neither —
  it is a new field nothing reads. To move any measured number the
  arbiter must write `state` (the `ctx_yield`/`_hidden_ctx` precedent —
  measured, and it *hurt*) or rewrite `o.score` (the `joint_struct`/
  `box_prio` precedent — measured, level −3/−4). Both precedents failed
  their A/Bs.
- If hiding does write `state="DELETED"`: the object leaves `active()`,
  `maintain`, `_retire`'s wall reads — lifecycle freezes, contradicting
  "keeps running and reappears"; and every object hidden at a golden's τ
  that was matching is a guaranteed recall loss. Reappearing later cannot
  recover a τ-miss. The arbiter can only *reduce* measured recall; its
  plausible benefit (visible@τ ≈ 3, author's economy) is invisible to the
  current metrics. **The arbiter needs a stated reason to exist** — either
  it feeds a NEW measured gate (e.g. a strict-C live@τ clutter column,
  which exists only as evalcheck's option-C diagnostic), or it is
  display cosmetics that the ruler cannot see. FIX: decide which, and if
  it's a metric, the metric must be added to the eval first.

**Per-family budgets:** removing shared caps is not free. Today's
`rate_total=5/72b` joint ledger is replaced by per-kind shares summing to
9/72b (1+2+1+1+2+1+1) — up to +80% birth headroom → more drawn ink →
clutter up (the metric the arbiter can't move). Mitigating evidence:
ledger note that `rate_total` "never observed to fire in kept state" —
if true on the canonical set the loss is nil, but that claim should be
*verified on the cache*, not asserted. `budget_hard=9` joint live cap is
replaced by Σfamlive = 6 — tighter, fine. `n_act` joint count disappears;
`slot_free`'s `n_act < 9` leg must be explicitly replicated or dropped by
decision, not by omission.

**EventBox:** the mechanism that reached box 16/119 + level 7/76 is
precisely: direct `_birth` outside the pool (no admission competition),
`meta_uip_persist` close-veto (all kill paths vetoed, vetoes logged),
in-place `(lo,hi,t0)` rewrites, `lvfree` exclusion from `live`/`n_act`/
displacement and from level edge-seeding, `pb_birth` route gate ≥3. The
draft captures most of this but (i) describes the wrong arm config
(M-C2), (ii) describes birth through the shared path (A-C8 — wrong), and
(iii) omits the reset-boundary question (A-C7). With those fixed, the
mechanism is preservable — it is already the parent.

**Level/line recall under removed caps:** the level −4 incident was
caused by slot occupation + edge seeding, both now excluded — fine. New
risk: per-family budgets let every family hold its own full live set
simultaneously (1 box + 1 level + 2 lines + 1 bracket + 1 ctx = 6 live +
labels), pushing live@τ above today's 8.0→? and drawn ink up. The
author's "~3 at τ" then rests entirely on the arbiter, which — per above —
cannot currently express it measurably.

---

## (e) FLAG_LEDGER spot-check (16 flags)

| flag | ledger says | evidence | verdict |
|---|---|---|---|
| `box.rank_score` ON | kept via bxcombo K3 | VL 05:22Z bxcombo +1 box +2 line | OK |
| `box.leg_edges` PENDING | no A/B | PL 04:58Z: fires, zero-delta, inert — not really "pending", measured-inert | OK w/ wording fix |
| `box.wick_edges` ON | kept via bxcombo | VL 05:12Z zero-delta solo; K3 bundle | OK |
| `box.dense_anchors` PENDING | — | no arm recorded | OK |
| `box.dedup_iou` ON | kept via bxcombo | same bundle | OK |
| `box.watch_birth` OFF | pending | PL 05:49Z informational arm only | OK |
| `box.cong_trigger` ON | K6 +2 box | VL 09:04Z/09:14Z | OK |
| `box.cong_pivedge` ON | K8 box 9→10 | VL; clutter 4.67 flat | OK |
| `line.lab_score` ON | K1 | VL: line +2 box +1 lvl +3 | OK |
| `line.steep_pick` OFF | lnsteep −2 | VL 07:01Z | OK |
| `level.defended_origin`+`def_mini_off` ON | K2 | VL: level +2 | OK |
| `marker.off` ON | K7 | VL | OK |
| `salience.fam_total_live` OFF | caps fail | VL 07:01Z | OK |
| `salience.joint_struct` OFF | fails | VL 08:23Z | OK |
| `salience.fam_context` OFF | fails | VL 07:52Z lvl−2 line−1 | OK |
| `ev_uip*` row | all OFF/PENDING | **stale**: C-3 has ev_uip/persist/lvfree/pb_birth ON | **STALE** |

Ledger-wide defects: (1) **49 boolean leaves / 21 ON now** — "48/17" was
already wrong at draft time (the `ev_uip_pb_birth` leaf existed, OFF, at
03:59Z); the flag is **absent from the ledger** though it is the kept
fixture cure. (2) All four `ev_uip*` rows read off/PENDING but are the
C-3 defaults. (3) `ev_uip_pb_write` described as the kept promotion —
inert/retired (M-C2). (4) `ev_uip_buildstart` listed pending — correct
today (OFF, byte-flat) but must not read as kept. (5) `famcap_bracket=0`
means *uncapped* — §B wording implies a cap of 2. (6)
`min_score_birth_signal` listed kept — never read (dead leaf).
(7) `.get()`-only defaults absent (A-C9). (8) `retire_far` wording
(M-C5), `tail_bars` zero-delta (M-C6), `level.def_*` count (M-C7).

---

## (f) PORT_PLAN_V2 — MQL5 portability hazards

1. **Unbounded per-bar cost (disproves "all lookbacks ≤600"):**
   `_near_structure` scans `e.bars[:bs]`; `_lab_line_score`, `_dome_update`,
   `_update_origins`, `_scan` iterate `book.alive()`/`seq`/`origins` — all
   append-only, unbounded. `origins`: theta origins never expire →
   `defended origins 64` cap needs an eviction policy Python doesn't have
   (divergence risk, must be measured: count origins/panel on canonical).
2. **`_ev_uip_born` is per-run** (A-C7): MQL5 is a continuous engine —
   without a reset rule the event box births *once ever*. Port needs the
   boundary decision first.
3. **Python-only idioms needing explicit contracts:** `dict` insertion
   order (`_watch`, `_asia`, `_grave_band`, `_hidden_ctx`, `_pedg_memo`,
   `_v0m` — the last keyed by **`id(v0o)`**, object identity, no MQL5
   analogue → needs an index map); `reversed(e.objects)`; `set`
   (`_logged`, `_graved` — bitmask/bounded array); dynamic attrs
   (`o._oi`, `meta_*` geometry keys → fixed struct with optional fields).
4. **Float/round/order semantics:** Python `round()` is banker's
   rounding; MQL5 `MathRound` is half-away — **the 1e-9 parity gate fails
   on .5 cases** unless every `round()` is spec'd. Pool comparator's
   geom-key is `repr(sorted(geom.items()))` — needs a canonical key
   encoding, not repr. `sorted` stability + tuple ordering must be
   restated as a comparator. Accumulation order (`sum(neigh)`,
   ABR/EMA recurrences) is fine only if iteration order is pinned.
5. **Sizing claims unproven:** `m_obj=256` tombstone store — ids are
   append-order strings (`BOX0123`) and `canonical()` compares them, so
   slot reuse must not recycle ids; prove max objects/run on canonical.
   `m_ev=16` event queue — overflow policy unspecified (silent drop =
   silent divergence). EDGE_BOARD 32 vs "≤10 in practice" — same: measure,
   then size with headroom. `book.seq` ring 64 / line pool 32 / births
   ring 32 — all need measured maxima, not nominal guesses.
6. **Pickles:** engine/candidate pickling is eval-side plumbing only —
   the plan rightly drops it; state that MQL5 parity compares canonical
   tuples, not pickles.
7. **The 99.5%-identical gate** is achievable only after items 1-5 are
   spec'd; today the Python side itself has unspecified order/order-
   sensitivity (A6, B7), so parity can't be proven against an
   under-specified reference.

**Do not start the port before the architecture freeze absorbs this
review's (a)/(c) fixes.**

---

## Verdict table (one screen)

| item | verdict |
|---|---|
| (a) code claims | **FIX** — stale lines post-A1/A2; `_near_structure` unbounded; `_ttl` mis-quarantined; `famcap_bracket` misread; relabel/line-label channels missing; UIP birth path misdescribed; `_ev_uip_born` scope unflagged |
| (b) measured claims | **FIX** — 67/72 suite refs; `pb_write`≠kept (`pb_birth` is); margin 110 vs 111; 46/51/15 denominators; retire_far/tail_bars wording |
| A0 oracle | **OK** (+extend canonical tuple with score/priority/touches) |
| A1 kernel move | **FIX** — landed clean; canonical-1728 check not logged (only 198 TUNE) |
| A2 ObjectStore | **FIX** — landed; **zero logged verification**; note state-setter/mirror invariant |
| A3 wrappers | **FIX** — enumerate direct-mutation call sites; pin update order |
| A4 round() split | **FIX** — per-extraction canonical diff; preserve `_logged`/cand_log interleave |
| A5 `c.fam` | **FIX** — `__slots__` update + pickle-shape note |
| A6 family order | **BLOCK** — iteration-order change is observable (`_retire`/`_squeeze_exit`); not a pure move |
| B1 shadow pools | **FIX** — OFF must skip construction; `_logged`/`_grave*` sharing spec'd |
| B2 split admission | **BLOCK** — tie order/ledger/float changes; OFF must run today's loop verbatim |
| B3 arbiter | **BLOCK** — `exposed` invisible to ruler; identity oracle can't see score writes; hide mechanism unspecified |
| B4 dispatch | **FIX** — pin synchronous order contract |
| B5 EventBox | **BLOCK** — wrong arm config (C-3 = pb_birth); birth bypasses pool; per-run latch; lvfree 3-site spec |
| B6 typed events | **BLOCK** — emission points/payloads (spawn inherits source feats); timing vs maintain boundary |
| B7 EDGE_BOARD | **BLOCK** — revive needs closed objects; moving wall edges; capacity/stale/order/rounding unspecified |
| (d) arbiter economy | **BLOCK as spec'd** — cannot move clutter or recall@k; needs a measured gate or removal |
| (e) ledger | **FIX** — 49/21 not 48/17; `ev_uip_pb_birth` row missing; dead leaf listed |
| (f) port plan | **FIX** — unbounded scans, per-run latch, dict/id()/repr/banker's-rounding, unproven caps |

## Fixes required before build continues

1. Re-anchor every stale line cite; add the two missing channels
   (`boxes.py:1288 relabel`, `lines.py:422 label`) to COUPLING_MAP.
2. Move `_ttl` out of quarantine; restate the 600-bar bound as
   "windowed lookbacks" and list the unbounded scans explicitly.
3. Correct EventBox spec to C-3 (`ev_uip`+`persist`+`lvfree`+`pb_birth`;
   `pb_write`/`buildstart` OFF); describe the direct-`_birth` path and
   the `_ev_uip_born` per-run latch; define the reset boundary.
4. FLAG_LEDGER: add `ev_uip_pb_birth`, recount 49/21, fix the §B rows
   (famcap_bracket, min_score_birth_signal, def_* count), fix wording
   (retire_far, tail_bars, pb_write).
5. Log A2's id-check + suite; extend A1's check to the full 1728
   canonical; extend `canonical()` with `score/priority/touches` before
   any arbiter step.
6. A6: either keep index-order iteration in retire or file it as a
   measured arm — it is not a pure move.
7. B3/B-arbiter: specify the hide mechanism (`state` toggle vs `exposed`)
   and what metric it is meant to move; if none, drop the arbiter from
   the plan's critical path.
8. B6/B7: write emission-point + payload spec (incl. `levels.spawn`
   source-feat inheritance) and per-consumer board views with
   capacity/stale/order/rounding rules.
9. PORT_PLAN: measured maxima for every proposed fixed cap; banker's-
   rounding and geom-key canonicalisation spec; `id()` → index map.

HANDOVER 04:37Z next=ARCH author absorbs fixes; build lane holds A3+
until A2 verification is logged and items 5-8 are resolved
