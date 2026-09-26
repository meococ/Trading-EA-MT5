# ARCH_V2 — Perception Architecture v2 (design only; rev2)

Lane: ARCH (Ruling 67 §67.3, rev2 under Ruling 72 §72.3). Status:
DESIGN. Everything here is a proposal; M1, M2, the ruler, the fixtures,
thresholds and the spec belong to the Owner.

## rev2 changes (absorbing ARCH_REVIEW.md, 23/09 04:37Z)

1. **Arbiter demoted off the critical path** (review item 7 + §d
   verdict BLOCK): no ruler-visible metric exists that a display
   arbiter could move — `clutter` counts every object whose drawn span
   intersects the panel regardless of state (`eval.py:107-145,357`),
   and recall@k uses `state != "DELETED"` (`snapshot.py:77-85`). An
   `exposed` flag reaches no consumer; writing `state` repeats the
   measured `ctx_yield` harm; rewriting `o.score` repeats the measured
   `joint_struct`/`box_prio` harm. §3.4 now states this decision
   plainly and names the gate that could bring it back.
2. **EventBox spec corrected to C-3** (review items 3, M-C2, A-C7/A-C8):
   the kept mechanism is `ev_uip + persist + lvfree + pb_birth` (all ON
   in `params_v1_1.json` since the `1a5502129b4c1554` fold);
   `pb_write`/`buildstart` are OFF (inert / byte-flat). Birth is a
   **direct `_birth` call** (`engine.py:445`) — no pool, no rate
   ledger, no `slot_free`. `_ev_uip_born` is a **per-run latch**
   (init `engine.py:133`, read `:417`, set `:451`, never reset) — the
   reset boundary is now an explicit open decision (§4).
3. **Bounded-cost claim restated** (review item 2, A-C3): "all
   lookbacks ≤600 bars" was false. Windowed lookbacks are capped;
   unbounded scans are listed explicitly in §7 (`_near_structure`'s
   `e.bars[:bs]` scan, `book.alive()` iterations in `_lab_line_score`/
   `_scan`/`_dome_update`, the never-expiring `origins` registry —
   measured max 52/panel on 623 C-3 runs, `caps_measure.py`).
4. **`_ttl` removed from quarantine** (review A-C4): kept-path box
   candidate TTL lives in BoxPipe (boxes.py:571-583 + call sites
   283/568/597/831/1024/1165).
5. **Essence findings folded into §1 and §4** (review task 3): DR-BOX —
   freshest structure wins, reach is the main loss; DR-LINE (interim) —
   the author's line is the boundary of the *newest* structure, the
   defended-veto is the binding constraint on line reach; for levels
   the question is which zone and when price approaches.
6. **Denominators fixed** (review M-C4): BOX-LAB ruler-exact reachable
   = 46/119; DR-BOX reachable = 51/119 (youngest pick 20/51);
   event-golden cells = 15 (T1 5/15). Never mixed again.
7. **Module map (§6) updated for landed reality** (review A-C12):
   `kernel.py` and `objects.py` exist (A1/A2); `pipes.py` shells exist
   (A3); `salience.round()` is already split into stages (A4);
   `Candidate.fam` exists (A5). What remains aspirational is marked.
8. **Bracket cap corrected**: `famcap_bracket=0` = uncapped, not 2
   (review A-C5). **Suite references**: the suite of record is 72 tests
   (`research/perception/tests/`); earlier "67/67" was a wrong-directory
   collection (review M-C1).

---

## 0. Why v2 exists (the measured diagnosis)

The v1 engine is incremental and causal, but its *selection* layer is a
single shared tournament. Every family's candidates enter one pool
(`salience.pool`), are scored by one composite, and compete for:

- one `budget_class` cap (`budget_signal/context/annot`, hard 9),
- one joint birth ledger (`rate_total` per 72 bars),
- joint live caps (`fam_total_live`, `joint_struct`),
- cross-family displacement, NMS, graves, cooldowns.

Result: families are zero-sum. Improving one family measurably hurts
another. The two cleanest measurements:

- **R66 / VERIFY_LOG 02:47Z** — `uip2_on` (one persistent event box,
  rewritten in place): box@1 **16/119 = v0 parity (+6)**, clutter 4.67,
  births exactly 1.0/panel — but level@1 fell 8/76 → **4/76 (−4)**.
  Mechanism verified on cache (REQUESTS.md §20 correction; review
  A-C8): (a) the event object's edges *seeded competing LEVEL_CARRIED*
  objects; (b) the persistent box *occupied* the shared `live`/`n_act`
  tallies that gate level births. **Not** admission competition — the
  UIP object bypasses the pool entirely (direct `_birth`,
  `engine.py:445`). Box parity was bought with level recall — a
  **coupling** failure, not a generation failure. `uip2_lvfree`
  excluded both channels and recovered level to −1 while holding box
  parity and clutter 4.33 (VL 03:33Z) — that pair of arms is now the
  C-3 parent (plus `pb_birth`, the fixture cure).
- **R25 / VERIFY_LOG 22:41Z** — `fam_ledger` still lost BOX −2 because
  "the budgets are NOT fully separate": shared live budget, shared
  displacement, shared NMS, continuation bypass.

Every subsequent joint cap failed the same way: `joint_struct` cap4/cap3
(level −4/−3, line −4, bracket −7 — VL 08:23Z/09:04Z), `box_prio`
(level −3/−4, clutter 6.00–6.33 — 07:32Z), `fam_context` (level −2,
clutter 5.67 — 07:52Z), `famoff*` (worse on every leg —
07:36–07:38Z). And the fixture debt: under fam flags a CONTEXT_RANGE
can hold the box family's single live slot, so no BOX is ever born —
the seven named theory fixtures fail (VL 06:35Z/06:52Z).

**Conclusion v2 takes:** the author's economy is *per-family* (about 1
box, 1–2 levels, ≤2 lines, ≤1 context, occasional brackets/marks), and
the *joint* economy is a display fact (≈3 objects on screen at τ,
≤5 structural, hard cap 8 — spec §5). v1 merged both into one selection
round. v2 separates them:

- Each family runs its own pipeline: **generate → lifecycle → its own
  budget**. A family's budget can never be spent by another family.
- Cross-family information moves only as **events** (facts, never
  shared mutable state): `BOX_BROKEN(edge)`, `LINE_BROKEN(price)`,
  `FORMATION_MID(price)`, `EDGE_POKE`/`EDGE_RELABEL` (annot channels),
  `EDGE_BOARD` (read-only band view).
- **The joint-economy question is deliberately NOT answered by a birth-
  path mechanism** (see §3.4 — the arbiter is off the critical path).

---

## 1. Design invariants (rev2: essence findings folded in)

1. **Causal, incremental, bounded.** At bar *i* every structure depends
   on bars ≤ *i* only; per-bar work is bounded by stated windowed
   lookbacks plus the unbounded scans listed in §7 (which the port must
   bound by measured maxima). Direct MQL5-portable.
2. **One object schema.** `Obj` (id, type, style, t_birth, t_left,
   t_right, geometry, state, touches, events, role, why, priority,
   score) is unchanged — the snapshot/eval contract does not move.
3. **A family owns its objects end-to-end.** Birth, geometry writes,
   lifecycle events, death: all inside the family pipeline. Another
   family can *request* a birth only by emitting an event the owning
   family may accept or decline — and the event carries everything the
   birth needs (source feats included; MIGRATION_PLAN B6).
4. **Determinism is the parity contract.** Object ids are assigned by
   append order (`TYPE%04d`), so birth order across families is part of
   the output. Today's order is the single score-sorted pool
   (`salience.py:673-676`); no fixed family admit order exists — any
   change is a measured arm, not a move.
5. **No flag carries unmeasured semantics.** Kept mechanisms fold into
   the core; failed ones are quarantined (FLAG_LEDGER).
6. **The freshest structure wins** (DR-BOX, measured): among causal
   pick rules the youngest-born object is the surviving choice —
   20/51 on DR-BOX's reachable set; BOX-LAB's ruler-exact bound showed
   "youngest" optimal at 14/46 reachable and no causal state rule does
   better (R70 §70.4). Design consequence: each family's representative
   is its newest qualifying object; re-anchor/rewrite mechanisms
   (keep-last) are preferred over spawning parallel alternatives.
7. **Reach, not selection, is the main loss.** 68/119 box goldens have
   no legal candidate at all (BOX-LAB reach accounting); selection over
   a relaxed space can only recover what generation produces. New
   generation routes plug into a family's `on_bar`/`on_pivot` without
   touching selection (e.g. the EC-B spike_base spec, REQUESTS §23 —
   held at +3/68 reach for 1.48 births/panel, above the ~1 birth bar).
8. **[DR-LINE interim — provisional until its report lands]** The
   author's line is the **boundary of the NEWEST structure**, not the
   historically best line: `young_a` (freshest first anchor) scores
   0.18–0.24 vs 0.04–0.12 for every quality rule on the relaxed space.
   The **defended-veto is the binding constraint** on line reach:
   legal-stream reach 0.22 → 0.56 without it (vA). For levels, the
   registry is dense and presence non-selective — the question is
   *which zone and when price approaches*, not whether a defended
   price exists (origin-within-tol reach 0.85 but shifted nulls
   0.74–0.83; best rule `ndef_dist@2` = 0.32 LC / 0.23 MINI vs engine
   born 0.19/0.07). Design consequence (provisional): LinePipe ranks by
   newest-structure membership; LevelPipe ranks zones by
   approach/recency, not by defence count alone.

---

## 2. Data flow

```
                     ┌─────────────── SHARED OBSERVATION LAYER ───────────────┐
 closed M5 bar i ──► │ bars / EMA25 / ABR(20) / tol · DCStream + SwingBook    │
                     │ gates (CET windows, hard_block) · day range · todvol   │
                     └───────┬───────────────────────────────────┬───────────┘
                             │ read-only facts                   │ read-only
                             │ (bars, pivots, EMA, ABR)          │ EDGE BOARD
        ┌────────────────────┼───────────┐                       │ (§3.3, B7)
        ▼                    ▼           ▼                       ▼
   ┌─────────┐        ┌──────────┐  ┌──────────┐          (published bands:
   │ BOX     │        │ LINE     │  │ LEVEL    │           every family's
   │ pipe    │        │ pipe     │  │ pipe     │           live edges,
   │ gen→    │        │ gen→     │  │ gen→     │           objects-append
   │ life→   │        │ life→    │  │ life→    │           order)
   │ budget  │        │ budget   │  │ budget   │
   └────┬────┘        └────┬─────┘  └────▲─────┘
        │                  │             │ ingest(ev)  ◄── family events:
        │                  └── LINE_BROKEN(price,side,src_feats) ──┘
        ├────── BOX_BROKEN(edge,side,src_feats) ───────────────────┘
        │                  ┌──────────┐  ┌──────────┐  ┌───────────┐
        │                  │ BRACKET  │  │ SQUEEZE  │  │ ANNOT     │
        │                  │ pipe     │  │ pipe     │  │ pipe      │
        │                  └────┬─────┘  └────┬─────┘  └─────▲─────┘
        │                       │ FORMATION_MID ─────────►LEVEL
        │   ┌──────────┐        │    EDGE_POKE/EDGE_RELABEL ──▲
        │   │ CONTEXT  │◄───────┴─────────────────────────────┘
        │   │ pipe     │  (NEW family split — not current FAMILY map)
        │   └────┬─────┘
        │        │
        ▼        ▼  all families return {born, live, cand-counts}
   ┌─────────────────── EXPOSURE + SNAPSHOT (no arbiter — §3.4) ────────┐
   │  o.score exposure writes stay where they are (salience _score_pass │
   │  + _grant_pass, incl. the ev +100 grant) — unchanged by v2         │
   │  optional future: display ordering behind a NEW evalcheck metric   │
   └──────────────────────────────┬────────────────────────────────────┘
                                  ▼
                            snapshot(i) → eval / render / MQL5 wire
```

Per-bar order inside `step(i)` — **pinned to today's engine order**
(`engine.py:458-543`; review B4 requires it verbatim):

```
1. shared.update(bar):        append bar; EMA/ABR/todvol; dc.update;
                              book.add on confirms; book.update_running
2. pivot fan-out (today's order):
      patterns → levels → boxes → reanchor → context_range → ev_uip
      → lines
3. tracker/maintain order (today's):
      asia_update → congestion_scan → session_update → maintain×4
      → _retire → round()
4. family admission = today's single round() (v2 keeps it until the
   C-arms land — Phase B is closed, MIGRATION_GATE.md)
5. snapshot / facts / stand_aside
```

v2 target order (post-arms, aspirational): stage 3's family calls become
`pipe.on_bar/on_pivot/maintain` in the same pinned order; stage 4 becomes
per-family `admit()` — **only after the measured C-arms pass**.

---

## 3. Components

### 3.1 Shared observation layer (`core/`, partly landed)

| piece | from | status |
|---|---|---|
| `DCStream`, `SwingBook`, `Pivot` | swings.py | unchanged |
| `gates.py` | verbatim | unchanged |
| series (EMA/ABR/tol/todvol) | engine.py | unchanged |
| bar facts (`_bar_facts`, `_dome_update`, `_pressure_update`, `_grid_step`, `_chop`) | engine.py | unchanged (output layer) |
| `Candidate`, `band`, `footprint_overlap`, `_band_of`, `FAMILY`, `budget_class`, `_sig*` | **`kernel.py` — LANDED (A1 @18ea3147)** | done |
| `Obj`, `ObjectStore` (`_mk`/`_birth`/`active`/state setter incl. `_act` auto-register) | **`objects.py` — LANDED (A2 @033aad2b)** | done; mirrors-must-not-receive-ACTIVE invariant documented |
| `EDGE_BOARD` | new | B7 — per-consumer views spec'd in MIGRATION_PLAN |

### 3.2 Family pipeline contract

`pipes.py` shells exist (A3 @ba1b9532 — delegation only). Target
interface:

```python
class FamilyPipe:                      # no shared base state
    def on_bar(self, i): ...           # bar-driven generation + trackers
    def on_pivot(self, i, piv): ...    # pivot-event generation
    def ingest(self, ev): ...          # accept/decline cross-family events
    def maintain(self, i): ...         # lifecycle on OWN objects only
    def admit(self, i): ...            # pool → same-kind NMS → own rate
                                       # ledger → own live cap → birth
```

Families and their kinds (budgets = today's kept values):

| pipeline | kinds | own budget |
|---|---|---|
| `BoxPipe` | BOX, RANGE_OPEN, **EventBox** (§4) | famlive_box=1, rate_box=1/72b, famcap_box |
| `LinePipe` | PATTERN_LINE | famlive_line=2, rate 2/72b |
| `LevelPipe` | LEVEL_CARRIED, MINI_LEVEL | live ≤2 LC (def_level_max_live) / ≤1 MINI, rate 1+1/72b |
| `BracketPipe` | BRACKET | rate 1/72b; **panel-UNCAPPED today** (`famcap_bracket=0`) |
| `SqueezePipe` | SQUEEZE | famcap 1 |
| `AnnotPipe` | LABEL_TF (BAR_MARKER suppressed) | ≤2/day (measured max 2/run on 623 C-3 panels) |
| `ContextPipe` | CONTEXT_RANGE, CONTEXT_LINE | **new split** — context still sits inside box/line in `kernel.FAMILY`; separating it is arm C2, not a move |

Per-family internals (existing mechanisms, relocated — nothing new
invented):

- **pool** — family-scoped candidate list with own grave sets; `c.fam`
  tag exists (A5 @63148cff).
- **scorer** — shared composite default + kept family override
  (box → `box_rank`; line → `_lab_line_score`; level → defended score).
- **NMS** — same-kind only (today's `fam_budget` branch,
  `salience.py` `_suppressed`).
- **rate ledger** — per-kind `births[win=72]` ring. `rate_total`,
  `ctx_full`, `mini_full`, `joint_full` reads die on the birth path
  (C1 arm). **Ledger note to verify on cache: `rate_total` was "never
  observed to fire in kept state" — confirm before claiming the removal
  is free** (review §d).
- **live cap + displacement** — `famlive_<fam>`/`famcap_<kind>`; the
  `n_act < budget_hard` leg of `slot_free` must be explicitly
  replicated or dropped by decision (review §d), not by omission.
- **revive** — `_revive_target` per family (needs `reversed(objects)`
  incl. CLOSED — the edge board cannot serve it, review B7).

### 3.3 Cross-family channels (the only allowed couplings)

1. **Events** — synchronous emission at the exact current call site
   (B6 spec in MIGRATION_PLAN):

   | event | emitter → consumer | replaces (current tree) |
   |---|---|---|
   | `BOX_BROKEN(edge,side,src_feats)` | BoxPipe.maintain → LevelPipe | `e.levels.spawn` boxes.py:1212 |
   | `BOX_OTHER_EDGE(edge,side)` | BoxPipe.maintain → LevelPipe | boxes.py:1220 |
   | `LINE_BROKEN(price,side,src_feats)` | LinePipe.maintain → LevelPipe | lines.py:449 |
   | `FORMATION_MID(price,side)` | BracketPipe → LevelPipe | patterns.py:224 |
   | `EDGE_POKE(side,letter,price,parent)` | Box/Line maintain → AnnotPipe | `e.patterns.label` boxes.py:1201/1279, **lines.py:422** (rev2-added) |
   | `EDGE_RELABEL(parent,top,bot,hgt)` | BoxPipe.maintain → AnnotPipe | **`e.patterns.relabel` boxes.py:1288** (rev2-added — drops live LABEL_TF rewrites if missed) |

   Payloads must carry the **source object's inherited feats**
   (`levels.py:42-76` reads the src object's feats at spawn) or
   generation diverges (review fix 8).

2. **EDGE BOARD** (read-only): per-consumer views — see MIGRATION_PLAN
   B7 for the per-consumer spec (capacity 32 vs measured max-live 9;
   objects-append order for first/last-match consumers; rebuilt per bar
   at a stated boundary; raw floats, consumers apply own tolerance).
   **Not** a consumer: `_revive_target` (needs CLOSED objects),
   `levels._budget_ok` (reads the pool, not objects).

3. **Candidate audit channel** — `cand_log` unchanged.

### 3.4 The arbiter decision (rev2 — review item 7)

**Decision: the display arbiter is removed from the critical path.**

Why, measured:

- M1 `clutter` = `n_eng/n_gold` where `n_eng` counts every object whose
  drawn span intersects the panel — `eval.py:107-145,357` iterates
  `e.objects` **regardless of state**. Post-hoc hiding cannot move it;
  only fewer births or shorter spans can.
- M1 recall@k reads `live_records` = `state != "DELETED"`
  (`evalcheck/snapshot.py:77-85`). An `exposed` flag reaches no
  consumer — it is a new field nothing reads.
- To move any measured number the arbiter must either write `state`
  (the `ctx_yield`/`_hidden_ctx` precedent — measured, *hurt*: level
  −2, clutter 5.67) or rewrite `o.score` (the `joint_struct`/`box_prio`
  precedents — measured, level −3/−4). Both directions failed their
  A/Bs. And `state="DELETED"` hiding removes the object from
  `active()`/`maintain`/wall reads — freezing lifecycle, contradicting
  "keeps running and reappears"; every τ-miss during a hidden window is
  unrecoverable.
- Additionally `o.score`/`priority`/`touches` are **not in the
  canonical identity tuple** (`evalcheck/cache.py:111-120`) — an
  arbiter regression would be invisible to the identity oracle until
  EVAL-AUDIT extends it (R72 §72.5b).

So: no ruler-visible metric exists today that an arbiter could improve
without repeating two measured failures. What stays instead:

- **The joint economy is carried by budget sizing alone**: per-family
  live caps sum to 6 (< today's `budget_hard` 9), per-kind rate caps
  sum to 9/72b vs `rate_total` 5/72b (+80% headroom — the stated cost
  of decoupling; mitigating evidence `rate_total` never fired in kept
  state, *to be verified on cache*).
- **Exposure/ranking writes stay exactly where they are**
  (`_score_pass`/`_grant_pass` incl. the ev +100 grant). v2 changes
  nothing the ruler sees on the kept path.
- **The gate that could bring an arbiter back**: a measured display
  metric — e.g. a strict-C "live@τ object count" column (today only
  evalcheck's option-C diagnostic reports live@τ ≈2.0–2.33). If
  evalcheck adds it as a scored column AND the canonical tuple gains
  score/priority/touches, a display arbiter becomes a measurable arm
  (C3). Until then it is display cosmetics, and the plan does not
  pretend otherwise.

---

## 4. The event-driven box, first-class (`BoxPipe.EventBox`) — C-3 spec

The mechanism is **already the parent** (STABLE C-3
`1a5502129b4c1554` = `ev_uip`+`persist`+`lvfree`+`pb_birth` folded into
defaults; VL 04:15Z/04:29Z). v2's job is to give it a clean home, not
to re-invent it. Spec (`engine.py:329-455` as built):

- **State:** `ev = {born: bool, obj_idx, last_birth_idx}`.
  `_ev_uip_born` is a **per-run latch** — set once, never reset
  ("one object per panel" holds only because each eval panel runs a
  fresh engine). **Reset boundary — open decision for continuous
  runs (MQL5):** proposed reset at each new CET day (same boundary the
  `_asia` tracker uses); the alternative (session/panel boundary) is
  Owner-visible semantics. Either way it needs a measured arm before
  it is folded — marked here so nobody assumes "per panel" is portable.
- **Triggers** (on each confirmed pivot, from `book.seq`):
  `range_double_*` (same-side prior pivot, sep ≥ 8, |Δprice| ≤ 2.0p,
  band = segment extremes ±2, window 600) and `pullback_end` —
  under C-3's `pb_birth`, a pullback candidate may **birth** the object
  at v0's route gate `idx - t0a >= 3` (the fixture cure; `pb_write`
  in-place rewriting by pb candidates is OFF — inert, retired R68).
- **Birth:** first non-shadowed qualified candidate, height 6–34p,
  edge dedup vs live boxes at `max(1p, .25·ABR)`, cooldown 10 bars —
  then a **direct `self._birth`** (`engine.py:445`): the object does
  NOT enter the pool, does NOT spend the rate ledger, does NOT check
  `slot_free`. The family score is still computed for the record.
- **Rewrite:** every later non-shadowed `range_double_*` rewrites
  `(lo,hi,t0)` in place — keep-last. No new object, no new id, no extra
  ink. `meta_build_start` walk-back exists behind `buildstart`
  (OFF — official A/B byte-flat +0, REQ §24; the diagnostic field is
  retained as tunable).
- **Persistence:** `meta_uip_persist` → `objects.py:55-64` close-veto
  on all kill paths (vetoes logged). Within its family it is the
  governing object — v0's "one box governs" semantics.
- **Decoupling (`lvfree`, folded — three sites):**
  (a) `levels.py:38-48` — its edges never seed defended origins/levels;
  (b) `salience.py ~684-696` — excluded from `live`/`n_act`/
      displacement tallies;
  (c) `salience.py ~1370` — excluded from `joint_struct` counts.
  Measured: level −4 → −1 holding box parity + clutter 4.33.
- **Why "keep-last" is right (essence, DR-BOX):** the freshest
  structure wins — youngest-born is the surviving causal pick (20/51
  reachable; optimal 14/46 ruler-exact, R70 §70.4). The event object's
  rewrite-in-place IS the freshest-structure rule: the object is always
  the newest qualified congestion, never a stale incumbent defended by
  hysteresis.
- The family's *proposal* routes (cluster_range, congestion_scan,
  asia convert, `_ttl`-TTL'd pool cands) still feed the family's pool —
  they birth the one slot only when no event object governs.

---

## 5. What changes, what does not

### 5.1 Removed from the birth path (quarantined, not deleted)

`budget_signal/context/annot`, `budget_hard`, `rate_total`,
`fam_total_live`, `joint_struct`, `fam_ledger`, `ctx_yield`,
`ctx_convert`, `box_prio`, `box_live_*`, `box_young_first`,
`box_edge_birth`, `box_live_at_birth`, `rate_blocked_extend`,
`revive_exempt`, `fam_context`, cross-family NMS mode, class-wide
displacement, `_hidden_ctx`, `ev_route_box`, `box_v0_family`,
`ev_uip_pb_write`, `min_score_birth_signal` (dead leaf).

**`_ttl` is NOT quarantined** (rev2 fix): it is kept-path box TTL
machinery and moves into BoxPipe.

### 5.2 Unchanged

- swings.py, gates.py: verbatim.
- Obj schema, snapshot shape, cand_log rows, eval contract.
- Kept generation routes and their parameters.
- M1, ruler, fixtures, thresholds — Owner's.
- **Exposure writes** (`o.score`, ev +100 grant) — unchanged.

### 5.3 Family map correction (deferred to arm C2)

`CONTEXT_RANGE`/`CONTEXT_LINE` leave the box/line families — but this
is **new behaviour**, not current state (`kernel.FAMILY` still groups
them under box/line; review A-C6). It resolves the fixture-debt
mechanism structurally, yet it can only land as a measured arm because
`fam_context` (the birth-path version) already failed M1 once.

### 5.4 Deterministic interleaving

Birth order = today's single sorted pool
(`(-score, kind, route, t0, repr(sorted(geom.items())))`). Any
family-major order is **new behaviour** (review A-C11) — introduced
only by a measured arm, never as a refactor. The A6 retire-order
variant was reverted for exactly this reason (iteration order is
observable through `_squeeze_exit` wall reads).

---

## 6. Module → v2 map (updated for landed tree @2d497427)

| current file:function | v2 home | change |
|---|---|---|
| `kernel.py` (Candidate, band, footprint_overlap, _band_of, FAMILY, budget_class, _sig*) | `core/cand` | **LANDED (A1)** |
| `objects.py` (Obj, ObjectStore, close-veto, `_act` index) | `core/store` | **LANDED (A2)** |
| `pipes.py` (FamilyPipe shells) | per-family pipes | **LANDED as delegation (A3)**; real internals arrive via Phase-B/C steps |
| `engine.py` `update`/`__init__` | `Engine2.step` | orchestrator; stage order pinned §2 |
| `_theta/_spike/_tol/_abr`, `_bar_facts`, `_dome_update`, `_pressure_update`, `_grid_step`, `_chop`, `stand_aside`, `facts`, `snapshot` | `core/series`+`core/facts` | verbatim moves (unlanded) |
| `_ev_uip_step`, `_uip_build_start`, `_ev_uip_born`, `_last_ev_birth` | `BoxPipe.EventBox` | relocation = pure move (B5-respec); reset-boundary decision pending |
| `_v0_sync` (`box_v0_family`) | quarantine | prepared-never-run; superseded (R71 §71.1) |
| `_retire`, `_squeeze_exit` | per-family `maintain` tail | same rules, own objects, index order; wall reads via edge board (B7) |
| swings.py / gates.py | `core/` | verbatim |
| boxes.py `bucket_merge`, `cluster_edge`, `longest_contained_run`, `on_pivot`, `_propose_window`, `_buildup_run`, `_barrier_feats`, `_rank_score`, `congestion_scan`, `_cong_run`, `_pivedge_emit`, `asia_update`, `maintain`, `_break_class`, `reanchor_check` | BoxPipe | `_near_structure` via edge board + windowed bars scan; spawns/label/relabel → events |
| boxes.py `_variants`+`_kde_peak` | BoxPipe (wick variant only) | leg/dense/kde arms quarantined |
| boxes.py **`_ttl`** + `_watch_*`, `_log_proposed` | `_ttl` → BoxPipe (kept path); watch registry → quarantine (watch_birth OFF) | rev2 fix |
| boxes.py `propose_context_range` | ContextPipe | family move (C2 arm) |
| lines.py `on_pivot`, `_pool`, `_is_loc_ext`, `_scan`, `_eval`, `_term/_sess`, `maintain` | LinePipe | `e.levels.spawn`→event; `e.patterns.label`→event; `book.alive()` needs a windowed view |
| levels.py `spawn`, `session_update`, `on_pivot`, defended block (`_add_origin`…`_maintain_defended`), `maintain` | LevelPipe | spawn → ingest entry; `_budget_ok` reads own pool; `origins` registry needs eviction policy for port (max 52 measured) |
| patterns.py `_brackets`, `_emit_bracket` | BracketPipe | `formation_mid` spawn → event |
| patterns.py `_marker_check` | AnnotPipe (suppressed) | marker.off folded |
| patterns.py `squeeze_scan` | SqueezePipe | walls via edge board |
| patterns.py `label`, `relabel` | AnnotPipe T/F attach | triggered by EDGE_POKE / EDGE_RELABEL |
| salience.py `score`, `_lab_line_score` | per-family scorer | composite + overrides |
| salience.py `propose`, `_grave*`, `_expire`, `pool` | per-family pool | B1 (FIX'd spec) |
| salience.py `round` stages (`_grave_sweep`…`_pool_sweep`) | split → `FamilyPipe.admit` + legacy dispatch | **LANDED as extraction (A4)**; per-family admit = C1 arm |
| `_suppressed`, `_revive_target` | per-family | same-kind only; revive needs `reversed(objects)` |
| `_box_prio`, `_joint_drop` | **display reference only** (arbiter demoted) | survives as documentation of §5 order, not live code |
| `_births` ledger | per-family rate ledgers | C1 arm |
| `lc_score_pick`/`box_score_pick` | per-family `fam_score_pick` | box kept; level OFF |
| `_hidden_ctx`, ctx_yield/convert | quarantine | failed mechanisms |

---

## 7. Bounded cost per bar (rev2: honest bound)

**Windowed lookbacks are capped; several scans are NOT bounded by a
window** (review A-C3). The truthful statement:

| work | bound |
|---|---|
| pivot fan-out | few confirms/bar; lookbacks capped (span_max 96, windows 45–600) |
| box generation | seeds ≤ scan_lookback 45 (`.get` default — §C ledger); buildup ≤ span |
| event box | O(pivots in 600-bar window); rewrite O(1); measured seq ≤103 |
| line eval | pair scan over alive same-side pivots — **`book.alive()` is append-only, never pruned** → grows with run (measured ≤103/panel on TUNE windows; unbounded on continuous runs — port needs a windowed view) |
| level origins | registry linear scan — **theta origins never expire** (measured max 52/panel; unbounded continuous — eviction policy needed) |
| `_near_structure` | **scans `e.bars[:bs]` — O(run history)** (boxes.py:~385-390) — needs a stated window bound |
| `_dome_update` | scans `book.alive()` — same unbounded issue |
| pools | measured residual 53 total; per-family caps with expire-first |
| object array | append-only; measured max **25 objects/panel** (623-run C-3 canonical, `caps_measure.py`) → port cap 64 |
| max concurrent ACTIVE | measured **9** → edge board 32 |

Migration note: bounding the unbounded scans changes behaviour in
corner cases → each bounding is a small measured arm or a stated
divergence-accepted item in the port, not a silent refactor.

## 8. Evidence → design mapping (rev2: denominators fixed)

| measured fact | design consequence |
|---|---|
| uip2_on: box parity, level −4 via slot occupation + edge seeding (VL 02:47Z; NOT admission — birth bypasses pool) | family-owned budgets; lvfree invariants folded |
| uip2_lvfree: same parity, level −1, clutter 4.33 (VL 03:33Z) | decoupling = architecture default |
| uip2_pbbirth: fixture cure via pb birth gate `idx-t0a>=3`, flips +0/−0 (VL 04:15Z) | EventBox has two birth routes (rd + pb), one object |
| fam_ledger BOX −2 (VL 22:41Z) | splitting birth rates alone is insufficient |
| every joint cap / joint-priority arm failed M1 | joint rules removed from birth path; **no replacement mechanism on the critical path** (arbiter demoted) |
| context held the box slot → 7 fixture fails (VL 06:52Z) | context family split — as arm C2, not a move |
| event box births 1.0/panel, live at τ 15/15 event-golden cells (REQ §19) | first-class mechanism; persistence = family policy |
| freshest structure wins: youngest pick 20/51 (DR-BOX reachable=51/119); BOX-LAB ruler-exact bound 14/46 reachable (R70 §70.4) | keep-last rewrites; newest-object representatives per family |
| reach = largest loss pool (68/119 no candidate) | generation stays multi-route; new routes plug into `on_bar` |
| DR-LINE interim: defended-veto binds line reach (0.22→0.56); author's line = newest structure's boundary | LinePipe scoring prefers newest-structure membership (provisional) |
| `rate_total` "never fired in kept state" (ledger note) | removal plausibly free — **verify on cache before C1** |

## 9. Explicit non-goals / risks (rev2)

- The plan **does not** promise a joint-economy mechanism. Per-family
  budgets sized to author counts are the entire answer today; anything
  beyond that is a measured arm behind a metric that doesn't exist yet.
- `pb_write` is OFF/inert — do not resurrect it inside EventBox specs.
- `_ev_uip_born` reset boundary (day? session?) is an open decision
  that blocks a correct continuous-run port until resolved by a
  measured arm.
- Unbounded scans (§7) are divergence risks for the MQL5 port; each
  bounding needs its own check.
- `rate_total`-removal-is-free is asserted by a ledger note, not yet
  verified on the canonical cache.
- Author budget constants remain Owner-tunable parameters.
