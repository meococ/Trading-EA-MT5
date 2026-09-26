# MIGRATION_PLAN — v1 → v2, ordered identity-checkable steps (rev2)

Lane: ARCH (R67 §67.3; rev2 under R72 §72.3). Governing rule: **every
step either (a) is a pure move — byte-identical to parent — or (b) is a
measured arm behind a flag**. Identity oracle = `evalcheck/cache.py:
canonical()` (objects+cand_log+bars) + the suite of record
(`research/perception/tests/`, **72 tests** — the earlier "67" was a
wrong-directory collection, PL 03:56Z). Gate: `MIGRATION_GATE.md`
(Lead-owned; a step lands only when listed OPEN).

## rev2 changes (absorbing ARCH_REVIEW)

- **Phase A reality recorded**: A1–A5 landed on tree `2d497427`,
  byte-identical to C-3 on 623/623 cached TUNE windows + suite 72/72
  (REQUESTS §24/§25). **A6 was reverted** — review (c) BLOCK: changing
  `_retire`/`_squeeze_exit` iteration order is observable (wall reads
  mid-sweep). A6 is re-filed below as measured arm **C6**.
- **Oracle blind spot declared** (review (c) preamble, R72 §72.5b):
  `canonical()` covers `(type, why, t_birth, t_left, t_right, state,
  id, geometry, events)` + cand_log + bars — **NOT** `o.score`,
  `o.priority`, `o.role`, `o.touches`, `o.style`. Any step that writes
  scores (arbiter, grant changes) is invisible to the gate until
  EVAL-AUDIT extends the tuple. All score-writing steps below are
  gated on that extension.
- **Pickle-compat shims are load-bearing** (review (c)): salience
  re-exports kernel names and `engine.__setstate__` routes
  `objects`/`_act` for legacy pickles, `Obj.__setstate__` maps legacy
  `state`, `getattr(c,"fam",None)` convention for pre-A5 Candidates.
  These are part of the identity contract — never remove silently.
- **B-steps re-spec'd** per review verdicts (B1 FIX, B4 FIX;
  B2/B3/B5/B6/B7 were BLOCK on the old texts — new specs below).
- **Backup path added** (§Phase D): the smallest safe path if B-steps
  can't be made identity-safe.

---

## Phase A — DONE (landed, verified)

| step | hash | content | verify |
|---|---|---|---|
| A0 oracle | — | `canonical()` exists; convention: full canonical set (1728-run OFF-id) or 623/623 cached C-3 panels | DONE; **tuple extension (score/priority/touches) owed by EVAL-AUDIT before any arbiter step** (R72 §72.5b) |
| A1 kernel.py | 18ea3147 | SIGNAL/CONTEXT/ANNOT/FAMILY/budget_class/Candidate/footprint_overlap/band_of/sig/sig_obj extracted; salience re-exports (pickle `find_class` safe) | DONE — 623/623 byte-identical (`_idchk_full.py`, REQ §25) |
| A2 ObjectStore | 033aad2b | `Obj`+`ObjectStore` → objects.py; engine property shims `objects`/`_act`/`active`/`_mk`/`_birth`; `__setstate__` legacy-pickle bridge (623 pkls, 0 errors) | DONE — id-check + suite now logged; **invariant documented: mirrors (`_v0_sync`) must never receive an ACTIVE state write** (state setter auto-registers `_act`) |
| A3 pipe shells | ba1b9532 | `pipes.py` FamilyPipe delegation shells; 12 `update` call sites route `pipes.*`; pivot/tracker call order pinned textually | DONE — 198/198 + 72/72 |
| A4 round split | e1775edd | `round()` → `_grave_sweep/_yield_sweep/_score_pass/_grant_pass/_admit_one/_yield_birth/_ctx_convert/_displace/_joint_pass/_pool_sweep` | DONE — 198/198 + 72/72; `_logged`/cand_log interleave preserved |
| A5 `c.fam` | 63148cff | `Candidate.fam = FAMILY.get(kind)` shadow field (unread; `__slots__` updated; `getattr` convention for old pickles) | DONE — 198/198 + 72/72 |
| ~~A6~~ retire order | 350b5b69 | **REVERTED** @2d497427 | BLOCK (review): iteration-order change observable via `_squeeze_exit` wall reads. Re-filed as arm **C6** |

Remaining owed: EVAL-AUDIT's independent check of `2d497427`
(R72 §72.5a) — not this lane's.

---

## Phase B — re-spec'd (all CLOSED until reviewer OK + gate OPEN)

Master flag: `arch_v2` (default 0). **Universal OFF rule (review B1
fix): when OFF, the OFF path must not even *construct* v2 state** — no
shadow pools, no tags beyond A5's, no extra iteration. OFF ≡ parent
byte-for-byte is proven per landing.

### B1. Shadow reads only — FIX'd spec
- What: per-family *views* derived by filtering on `c.fam` at read time
  (no second pool object; no double `propose`; `_logged` and `_grave*`
  machinery stay single-source on the shared pool; **no second `order`
  sort**).
- Forbidden (explicit): constructing `pool_f` lists that live alongside
  `self.pool`; any write path that diverges `_logged`; a second
  `sorted()` of the pool.
- Identity: OFF skips all of it; ON builds read-only views and asserts
  `view_f == [c for c in pool if c.fam==f]` in a debug test only.
- Verdict sought: OK.

### B4. Pinned dispatch order — FIX'd spec (lands with B1)
- What: textual contract + thin call hub, synchronous FIFO, no queue:
  - pivot fan-out order verbatim: `patterns → levels → boxes →
    reanchor → context_range → ev_uip → lines` (`engine.py` update);
  - tracker order verbatim: `asia_update → congestion_scan →
    session_update → maintain×4 → _retire → round`.
- The hub is a same-thread direct call sequence — it exists so later
  arms have one insertion point; it changes no order today.
- Identity: OFF = today's inline calls; ON = same calls in same order
  through the hub → byte-identical required.

### B5. EventBox relocation — re-spec'd (review BLOCK → pure move)
- **Not** a behaviour arm: C-3's EventBox already IS the parent. The
  step is a *relocation*: move `_ev_uip_step`'s body into
  `BoxPipe.event_step(i, piv)` called at the **identical point** in the
  pivot fan-out (between `context_range` and `lines`); `_ev_uip_born`/
  `_last_ev_birth` move with it; `lvfree` exclusions stay at their three
  sites (`levels.py:38-48`, `salience.py ~684-696`, `~1370`) reading the
  same `meta_uip_persist`/flags.
- Spec = C-3 exactly: `ev_uip`+`persist`+`lvfree`+`pb_birth` semantics;
  `pb_write`/`buildstart` remain OFF-reading `.get()`s; birth stays a
  direct `_birth` (no pool).
- Identity: byte-identical required (same calls, same order, same
  writes) — this is checkable and was the review's "mechanism is
  preservable" conclusion.
- **Open decision carried, not resolved here:** `_ev_uip_born` reset
  boundary for continuous runs (proposed: new CET day) — separate
  measured arm, blocks nothing in the relocation.

### B6. Typed events at existing call sites — re-spec'd (BLOCK → FIX-by-spec)
- Mechanism: `e.emit(ev)` = a synchronous dispatch that calls the
  consumer's `ingest` **at the exact current call site** — no queue, no
  deferral. Byte-neutrality holds iff mutation timing is unchanged, so
  the spec pins emission points:
  | emission site (current) | event | consumer |
  |---|---|---|
  | boxes.py:1212 | `BOX_BROKEN(edge,side,src_feats)` | LevelPipe.ingest → `spawn` body |
  | boxes.py:1220 | `BOX_OTHER_EDGE(edge,side)` | LevelPipe.ingest |
  | lines.py:449 | `LINE_BROKEN(price,side,src_feats)` | LevelPipe.ingest |
  | patterns.py:224 | `FORMATION_MID(price,side)` | LevelPipe.ingest |
  | boxes.py:1201,1279 + **lines.py:422** | `EDGE_POKE(side,letter,price,parent)` | AnnotPipe → `label` body |
  | **boxes.py:1288** | `EDGE_RELABEL(parent,top,bot,hgt)` | AnnotPipe → `relabel` body |
- **Payload rule (review fix 8):** `levels.spawn` inherits feats from
  the *source object* (`levels.py:42-76`) — so every spawn-type event
  carries `src_feats` = the parent's `feats`/`sali` dict **copied at
  emit time**, plus `src_id` for `meta["src"]`. `ingest` passes them
  verbatim into the same `spawn` body — no re-reading the source object
  later (its state may have moved).
- Fallback (if synchronous emit proves non-neutral): keep direct calls
  behind an interface — `level_pipe.ingest_spawn(...)` invoked inline —
  same call sites, zero machinery. The review offered exactly this
  escape; the interface is the deliverable either way.
- Identity: OFF = direct calls; ON = same calls via emit/interface.
  Byte-identical required.

### B7. EDGE_BOARD — re-spec'd (BLOCK → per-consumer views)
- The board is **not** a drop-in `e.active()` replacement. Per-consumer
  spec (review fix 8):
  | consumer | needs | board view |
  |---|---|---|
  | `boxes._near_structure` (~374-395) | any live object's band near a price + `e.bars[:bs]` stats (the bars scan is *not* board-servable — needs its own window bound, §7 ARCH_V2) | flat `(lo,hi,side)` in **objects-append order** |
  | `propose_context_range` (1050-1054) | containment vs live BOX+CONTEXT_RANGE | same view, kind-filtered |
  | `patterns.squeeze_scan` (250-268) | wall bands by id, **incl. moving point-band lines** — board must refresh per bar, per stage boundary | `(id,lo,hi)` rebuilt after all maintains |
  | bracket relevance (191-197), marker anchor (67-82) | bands of live objects | same flat view |
  | `_retire`/`_squeeze_exit` (engine 596/636) | wall bands **by object id**, read mid-sweep while closes mutate `active()` | board is a *snapshot taken at stage start* — divergence vs live reads must be measured (this is the subtle one: today's code reads live state mid-sweep; a snapshot changes semantics → measured arm, not a move) |
  | **NOT consumers** | `_revive_target` (needs CLOSED objects, reverse order); `levels._budget_ok` (reads the pool); `_suppressed` (pool+live same-family) | keep direct reads |
- Rules: capacity 32 (measured max concurrent ACTIVE = 9 on 623 C-3
  panels — `caps_measure.py`); stale entries impossible by construction
  (rebuilt each bar); iteration = objects-append order (never
  (kind,price) sort — first/last-match consumers depend on it); floats
  carried raw — consumers apply their own tolerance (no board-side
  rounding).
- Identity: OFF = no board built; ON = substitution per consumer, each
  with its own byte-check. `_squeeze_exit` substitution is the only one
  expected to need an arm (snapshot-vs-live semantics).

### B2/B3 — removed from Phase B (review BLOCKs stand)
- **B2 (split admission)** can never be byte-identical ON — different
  tie order, joint ledger reads, float accumulation order. That IS the
  behaviour change → it is arm **C1**, not a refactor step.
- **B3 (arbiter)** is demoted off the critical path (ARCH_V2 §3.4): no
  ruler-visible metric exists for it. It returns only if evalcheck adds
  a measured display metric — then it is arm **C3**, gated on the
  canonical-tuple extension (R72 §72.5b).

---

## Phase C — measured arms (each its own flag + keep-rule A/B)

| arm | flag | what changes ON | gate note |
|---|---|---|---|
| C1 | `arch_budgets` | per-family admit (own pool views, own rate rings, own live caps + same-family displacement); joint `rate_total`/`budget_*`/`fam_total_live`/`joint_struct` unread on birth path | expected: identical-or-better under event-box load; **pre-check: verify `rate_total` never fired on the canonical cache** |
| C2 | `arch_context` | CONTEXT_RANGE/CONTEXT_LINE → ContextPipe (new family split) | fixture-debt fix; `fam_context` failed M1 at birth-path — this is the structural version, still must pass keep-rule |
| C3 | `arch_arbiter` | display ordering/hide behind a NEW evalcheck metric (e.g. strict-C live@τ column) | **blocked until the metric exists + canonical tuple extended**; probably never — demoted |
| C4 | — | ~~EventBox promotion~~ | moot: C-3 already folds it (B5 is only relocation) |
| C5 | docs | quarantine annotations for dead flags (Owner's params — proposal only) | Owner decision |
| C6 | `arch_retire_famorder` | family-major `_retire` sweep (the reverted A6) | measured arm: TUNE-flat already known (198/198) but `wall_gone` close-order channel is real — needs full canonical + suite |

## Phase D — backup: the smallest safe path (review item 4 of the lane)

If the re-spec'd B-steps still cannot be made identity-safe, the
**minimum safe path is B1 + B4 + B5-relocation only**:

- B1 gives per-family views (read-only, zero risk).
- B4 gives the pinned dispatch contract (documentation + hub, zero
  behavioural delta).
- B5-relocation puts the event box inside BoxPipe (pure move; the C-3
  mechanism untouched).

Everything else becomes measured arms (C1/C2/C6) run through the
normal keep-rule — same as any experiment, no special identity claim.

**What it gives up (state plainly):** the monolith keeps its shared
selection round; families do not get isolated budgets by structure —
only by measured arms one at a time; the codebase keeps its coupling
but gains a documented map, a pinned order contract, and the event box
in its family home. No structural decoupling lands by default. That is
acceptable: every decoupling so far that skipped measurement failed
M1 — the evidence says arms are the only safe vehicle.

## Invariants every step keeps (unchanged + rev2 additions)

1. Object ids = append order; birth-order changes only via measured
   arms (never silently — A6 is the lesson).
2. `cand_log`/`snapshot` schemas unchanged.
3. Closed-bar causality.
4. No touching fixtures, thresholds, ruler, params, M1/M2, HOLD, spec.
5. OFF ≡ parent byte-for-byte; rollback = flag OFF; quarantine, never
   delete.
6. **(new)** Steps that write `o.score`/`priority`/`touches` are
   invisible to today's oracle — gated on the canonical-tuple
   extension (R72 §72.5b).
7. **(new)** Load-bearing shims: salience's kernel re-exports, engine
   `__setstate__`, `Obj.__setstate__` state mapping,
   `getattr(c,"fam",None)` — removing any of them is itself a step.

## Order recap (rev2)

```
Phase A: DONE @2d497427 (A1-A5; A6 reverted → C6)
Gate now: Phase B ALL CLOSED (MIGRATION_GATE.md) — reviewer re-checks
B1+B4 → B5-relocate → B6 events → B7 board   (each: review OK → gate
OPEN → land → canonical check)
C-arms run under the normal keep-rule whenever ordered.
Backup: B1+B4+B5 only; rest as arms.
```
