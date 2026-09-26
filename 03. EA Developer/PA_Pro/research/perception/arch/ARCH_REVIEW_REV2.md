# ARCH_REVIEW_REV2 — re-review of the rev2 drafts (Ruling 72 §72.4)

Lane: ARCH-REVIEW re-check. Reviewer did not write the drafts; first
review at `arch/ARCH_REVIEW.md` (04:37Z). Tree under review:
`2d497427` = STABLE C-3 + A1–A5 landed, A6 reverted. Evidence order:
current source tree > `results.jsonl` > `VERIFY_LOG.md` (VL) >
`REQUESTS.md` (REQ) > `PERCEPTION_LOG.md` (PL) > drafts.

Verification status carried into this review: EVAL-AUDIT independently
checked `2d497427` at VL 05:37Z — **623/623 cached C-3 panels
byte-identical incl. all τ-truncated runs**, suite 72/72. R72 §72.5a
is discharged. The canonical-tuple extension (§72.5b,
score/priority/touches) is correctly carried as a gate prerequisite,
not claimed done.

---

## 1. The nine required fixes — verdict per item

| # | fix required (ARCH_REVIEW) | verdict | evidence |
|---|---|---|---|
| 1 | Re-anchor stale cites; add `boxes.py:1288 relabel` + `lines.py:422 label` channels | **RESOLVED** | COUPLING_MAP rev2 re-anchored; every cite I re-checked is exact on `2d497427` (engine.py 882 L: `_ev_uip_step` 329-455, `update` 458, `_v0_sync` 551, `_retire` 596, `_squeeze_exit` 636, `_mk`/`_birth` 223/226; salience.py 1500 L: `round` 530 → `_grave_sweep` 542, `_yield_sweep` 570, `_score_pass` 622, `_grant_pass` 668, `_admit_one` 699, `_yield_birth` 1211, `_ctx_convert` 1248, `_displace` 1312, `_joint_pass` 1453, `_pool_sweep` 1483). Both missing channels now in ARCH_V2 §3.3 table and COUPLING_MAP. |
| 2 | `_ttl` out of quarantine; restate the bound; list unbounded scans | **RESOLVED** | §5.1 explicitly un-quarantines `_ttl` ("kept-path box TTL machinery → BoxPipe"; boxes.py:571-583 + call sites verified). §7 honest-bound table lists `_near_structure` `e.bars[:bs]`, `book.alive()` (`_lab_line_score`/`_scan`/`_dome_update`), never-expiring `origins`. |
| 3 | EventBox spec → C-3 (`pb_birth`, direct `_birth`, per-run latch + reset) | **RESOLVED** | §4 rewritten: `ev_uip+persist+lvfree+pb_birth`; `pb_write`/`buildstart` OFF; direct `self._birth` at `engine.py:445` verified (actual ~444-445); latch init `:133`/read `:417`/set `:451` verified; reset boundary explicitly an open decision (CET-day proposed). Minor line drift only: lvfree cites "~684-696, ~1370" now sit at `salience.py:736-748` and `:1464-1466` (post-A4) — cosmetic, sites named correctly. |
| 4 | FLAG_LEDGER recount + missing row + §B wording + `.get()` defaults | **RESOLVED** | Header now 49 bools / 21 ON — matches my independent count (`params_v1_1.json` walk: 49/21). Row 44 `ev_uip_pb_birth` added with correct mechanism cite. §B: `famcap_bracket=0`→uncapped, `min_score_birth_signal`→dead leaf, `def_*`→20 leaves, `rate_<kind>`→7+default, `retire_far` mixed-result wording (PL 19→22/LC 6→5), `tail_bars` non-zero-delta — all match VL/PL. New §C lists `.get()`-only defaults with sites; spot-checked `scan_lookback_bars` boxes.py:735/739, `wait_ttl` :581, `level_edges` :133/752 — exact. |
| 5 | A2 verification logged; A1 extended to canonical; canonical tuple extension declared | **RESOLVED** | A2 id-check + suite logged (REQ §25); A1 strengthened to 623/623 all-cached (`_idchk_full.py`, REQ §25) and independently re-verified (VL 05:37Z); oracle blind spot declared in MIGRATION_PLAN §rev2 + invariant 6; tuple extension correctly gated on EVAL-AUDIT (R72 §72.5b). |
| 6 | A6: index-order or measured arm | **RESOLVED** | A6 reverted @350b5b69→`2d497427` (REQ §25); `_retire` sweeps `active()` append order again (`engine.py:596`+); `RETIRE_FAM_ORDER` survives as declaration-only constant (`engine.py:43`, comment `:613`); re-filed as arm **C6** with the correct gate note (full canonical, not just TUNE-flat). |
| 7 | Arbiter: name a ruler-visible metric + gate, or drop | **RESOLVED** | §3.4 — removed from critical path with the correct reasoning (clutter counts drawn spans incl. DELETED; recall@k reads `state`; `exposed` reaches no consumer; both fallback mechanisms repeat measured failures `ctx_yield`/`joint_struct`). Return gate named: a measured live@τ display column + canonical-tuple extension → arm C3. This is exactly the honest outcome. |
| 8 | B6 emission-point/payload spec; B7 per-consumer board views | **RESOLVED** | B6: per-site emission table (all six channels incl. rev2-added `lines.py:422`, `boxes.py:1288`), synchronous-at-callsite, payload = `src_feats` copied at emit + `src_id`; interface fallback stated. B7: per-consumer view table incl. non-consumers (`_revive_target`, `_budget_ok`, `_suppressed`), objects-append ordering, raw floats, capacity 32 vs measured max-live 9, `_squeeze_exit` snapshot-vs-live divergence correctly flagged as measured arm. Residual nits in §5 below. |
| 9 | PORT_PLAN: measured maxima, rounding/id()/geom-key/dict-order contracts | **PARTIAL** | §5 determinism contracts are real and correct (banker's rounding vs `MathRound`, `repr(sorted(geom.items()))` → canonical key spec, insertion-order → arrays+counters, `id()`→index map, sets→bitmask, `meta_*`→fixed struct, accumulation order). Measured caps verified by my own `caps_measure.py` run: objects ≤25, live ≤9, seq/alive ≤103, origins ≤52, births/bar ≤2, labels ≤2 — all exact. **But the pool sizing is under-evidenced: `m_pool[32]`/family is sized off end-of-run residual (53), while the TTL-window proposal bound reaches `pool24_level=926`** — see §5 R-1. |

**Net: 8/9 resolved, 1 partial (port pool sizing).**

---

## 2. Phase B re-check (flag OFF ≡ parent byte-for-byte; ON = stated gate)

Universal OFF rule added ("OFF must not even construct v2 state") —
correct and necessary.

| step | verdict | basis / required fix |
|---|---|---|
| **B1** shadow views | **OK** | Read-time filters on `c.fam`; no second pool, no second `order` sort, `_logged`/`_grave*` single-source; OFF skips construction. Spec is implementable and byte-checkable. One invariant to write down: `c.fam` is fixed at construction via `FAMILY.get` — it must never be read under a flag that re-maps families (`fam_context` is quarantined, so today trivially true; state it). |
| **B4** pinned dispatch | **FIX** | Spec order is wrong vs `update()` on two points — build's own pre-landing audit (REQ §26, 06:02Z) already caught both and I verified them: (a) pivot pin omits the `[flag ev_route_box: _ev_box_birth]` call site and the `is_structural` guard on `reanchor_check`/`propose_context_range` (`engine.py:514-522`); (b) tracker pin says "maintain×4" — actual is `box.maintain → line.maintain → level.maintain` (×3, annot has no maintain) `→ annot.squeeze_scan → _retire → round → _pressure_update` (`engine.py:528-543`). Patch the two lists to §26's literal text — the corrected pin is then byte-identical by construction. |
| **B5** EventBox relocation | **OK** | Re-spec'd as pure move: `_ev_uip_step` body → `BoxPipe.event_step` at the identical call point; latch + `_last_ev_birth` move with it; lvfree's three sites untouched; birth stays direct `_birth`. Byte-identical is checkable (same calls/order/writes). Two implementation notes: (i) `_uip_build_start` (OFF-flag path) moves or stays via `e.` — pick one, state it; (ii) latch relocation changes where the state lives — pre-B5 pickled engines are not resumed in eval so this is safe, but say so. Reset-boundary decision correctly deferred to a separate arm. |
| **B6** typed events | **FIX** | Emission table + synchronous-same-site dispatch + src_feats-copied-at-emit payload rule — correct skeleton. Three payload clarifications needed: (1) `levels.spawn` re-resolves `src` to check `meta_uip_persist` (`levels.py:41-48`) — the lvfree veto is a *live object read*, so the payload's `src_id` must let `ingest` re-resolve the object (or carry a `src_uip_persist` bool frozen at emit); the spec's "no re-reading the source object" applies to feats only — say so. (2) Pin `parent` payload type: `label`/`relabel` take the Obj reference (`patterns.py:309/330`), `spawn` takes an id — one convention per event. (3) `relabel` itself re-scans `e.objects` for `role==parent.id` (`patterns.py:335+`) — annot-internal lookup; state that ingest replays the body verbatim including that scan. |
| **B7** EDGE_BOARD | **FIX** | Per-consumer views correctly spec'd; the `_squeeze_exit` snapshot-vs-live divergence is honestly re-classified as a measured arm (not a move) — that was the trap. Remaining tightenings: (a) pin ONE rebuild-boundary rule (the table mixes "rebuilt after all maintains" for squeeze_scan vs "snapshot at stage start" for `_retire` — pick the rule and say which stages get live vs snapshot views); (b) `stand_aside`/`facts` output reads (`engine.py` ~760s) aren't listed — mark them direct-read/non-consumer explicitly; (c) `_near_structure`'s `e.bars[:bs]` bound stays open — the row says "needs its own window bound" but no candidate bound is proposed (suggest stating the window, e.g. same 600, as the divergence-accepted item §7 requires). |
| **B2** split admission | **OK — correctly removed from Phase B** | Reclassified as arm **C1** (`arch_budgets`): a behaviour change by design, so it never belonged in the refactor track. Its pre-check is now DONE and stronger than asked: PL 05:49Z proves `rate_total` is *statically unreachable* under `fam_budget` (`salience.py:928-935` takes the fam-share branch) + 39,008 `rate_limited` vetoes across 620/623 panels, zero joint. C1's gate is a normal keep-rule A/B + OFF-flag identity. |
| **B3** arbiter | **OK — correctly demoted** | Removed to arm **C3**, gated on a metric that doesn't exist + the canonical-tuple extension. See §3. |
| **Phase D backup** (B1+B4+B5 only, rest arms) | **OK** | Coherent smallest safe path; "what it gives up" is stated honestly (no structural decoupling by default). Note B4 inside it needs the same §26 patch. |

Phase-C arms as listed (C1 budgets, C2 context split, C3 arbiter,
C6 retire-order) each carry a flag + keep-rule gate — correct vehicle.
C1's rate_total blocker is already discharged (above). C6 correctly
demands full canonical, not TUNE-only.

---

## 3. Arbiter — task question

Resolved correctly. ARCH_V2 §3.4 states the decision with the right
mechanism analysis, names the only gate that could revive it (a measured
live@τ display column in evalcheck + the extended canonical tuple), and
re-files it as arm C3 off the critical path. No ruler-visible metric
exists for it today — confirmed independently in §d of my first review
(`eval.py:107-145` counts drawn spans regardless of state;
`snapshot.py:77-85` live = `state != "DELETED"`; `o.exposed` has no
consumer). Off the critical path: confirmed.

## 4. Essence findings in ARCH_V2 — task question

Stated as evidence with sources, correctly: DR-BOX freshest-wins
(20/51 reachable; BOX-LAB ruler-exact bound 14/46, R70 §70.4), reach =
68/119 main loss pool, EC-Bv2 held at +3/68/1.48 births (over the ~1
bar) — all match REQ §19-23/R66-R72. DR-LINE interim is marked
*provisional* and I verified its numbers against
`deepresearch/DR_LINE_ESSENCE.md`: veto-off reach 0.22→0.56,
`young_a` 0.18-0.24 vs 0.04-0.12, origin-within-tol 0.85 vs shifted
nulls 0.74-0.83, `ndef_dist@2` 0.32/0.23 vs born 0.19/0.07 — all real.
Design consequence is kept provisional (LinePipe newest-structure
membership; LevelPipe zone/approach ranking) and does **not** bend any
B-step — correct restraint: essence informs future generation arms
(C-lane), not the refactor.

## 5. Residual findings in rev2 (new, minor)

- **R-1 (port, real): pool cap under-evidenced.** `m_pool[32]`/family is
  justified by end-of-run residual 53. Candidates leave the pool early
  (`c.expires=i` on birth/loss) but peak occupancy is bounded only by
  proposals-in-TTL-window — my caps_measure run shows
  `pool24_level=926`, `pool24_box=114`. True peak is unmeasured
  (needs in-run `max len(pool)` instrumentation, not post-hoc pickles —
  `pool_end` is residual, `pool24` overcounts by including propose-time
  rejects). "Expire-first" eviction on a 32 ring would silently diverge
  from Python (which never evicts early). Fix: add a peak-occupancy
  probe before fixing the cap.
- **R-2 (B4 spec):** the two literal-order patches per REQ §26
  (ev_box_birth call site + is_structural guard; maintain×3 +
  squeeze_scan + `_pressure_update`). One-line spec patch, already
  diagnosed by build.
- **R-3 (cosmetic):** ARCH_V2 §4's lvfree cites drifted post-A4
  (`~684-696`→736-748, `~1370`→1464-1466); `~` prefixes keep it honest
  but re-anchor anyway. FLAG_LEDGER row 39 (`ev_route_pullback`) still
  says "ON under OFF parent" — the parent is C-3 (ON) now, so the pb
  route is load-bearing for the V3 gate, not idle.
- **R-4 (note, not defect):** caps_measure's `max_live` counts an
  object's first `close` event as its end — objects DELETED via direct
  state writes (ctx_yield path) have no close event and would
  over-count; under C-3 those paths are OFF so max 9 stands.
- **R-5 (process):** "canonical set" should be defined once —
  623 cached windows (all incl. τ-truncated, per VL 05:37Z) vs the older
  576/1728-check convention differ in coverage, not in kind; write the
  definition in the plan so "byte-identical on canonical" is
  unambiguous next round.

---

## 6. Verdict table (one screen)

| item | verdict |
|---|---|
| 9 fixes | 8 RESOLVED, 1 PARTIAL (port pool sizing) |
| B1 shadow views | **OK** — recommend OPEN |
| B4 pinned dispatch | **FIX** — apply REQ §26's two literal-order patches, then OK |
| B5 EventBox relocation | **OK** — recommend OPEN (pure move, byte-checkable) |
| B6 typed events | **FIX** — payload clarifications (veto re-resolve, parent type, relabel scan replay) |
| B7 edge board | **FIX** — one rebuild-boundary rule; `stand_aside` non-consumer note; `_near_structure` window bound |
| B2 → arm C1 | **OK** (rightly off refactor track; rate_total pre-check done) |
| B3 → arm C3 | **OK** (rightly demoted; gated on new metric + tuple ext) |
| Phase D backup | **OK** (B1+B4+B5 minimal path; same B4 patch applies) |
| Arbiter decision | **RESOLVED** — off critical path, gate named |
| Essence fold | **OK** — sourced, provisional, doesn't distort B-steps |
| Port plan | **FIX** — pool peak-occupancy measurement (R-1); rest of §5 contracts sound |

## 7. Recommended MIGRATION_GATE openings (Lead decides)

- **OPEN: B1** (shadow views) — implementable, OFF-safe by construction.
- **OPEN: B5** (EventBox relocation) — pure move; latch/pickle note in §2.
- **OPEN after patch: B4** — apply REQ §26's corrected pin lists first;
  landing B4 before/with B1 is fine either way (it is order-documentation).
- **Keep CLOSED: B6, B7** — one more spec round each (payloads; rebuild
  boundary); both are close — the fixes are known and small.
- **Keep CLOSED: B2, B3** — correctly not steps; C1/C3 are measured arms
  under the normal keep rule, not gate items.
- **C6** may proceed as a measured arm whenever ordered (full canonical
  required — its TUNE-flat result does not cover the wall-read channel).
- EVAL-AUDIT's canonical-tuple extension (§72.5b) stays the prerequisite
  for anything that writes `o.score`/`priority`/`touches`.

HANDOVER 06:13Z next=Lead opens B1/B5 (and B4 after the §26 patch); ARCH author rounds B6/B7 specs
