# PORT_PLAN_V2 — Python perception v2 → MQL5 (rev2)

Lane: ARCH (R67 §67.3; rev2 under R72 §72.3). Keeps the two-track
structure of `mql5/PORT_PLAN.md` (pass track / read-view track) and its
P-FREEZE rule: **no engine logic ports before the architecture freeze
the Owner signs** — and per this review cycle, not before the
determinism contracts in §5 are written.

Parity contract (unchanged): Python JSONL → `tools/jsonl_to_csv.py` →
`perception_csv_v1` wire → MQL5 importer → `parity/compare_perception.py`
per-bar id-keyed compare. Target ≥99.5% identical bars; exact on
type/id/state/role/side/letter/t1/t2; 1e-9 on price floats.

## rev2 changes (absorbing ARCH_REVIEW §f + items 3, 8, 9)

- **All caps now carry measured maxima** (623-panel C-3 canonical cache,
  `arch/caps_measure.py`, run 05:25Z): objects ≤25, concurrent ACTIVE
  ≤9, pivot seq/alive ≤103, origins ≤52, births/bar ≤2, LABEL_TF ≤2/run,
  pool residual ≤53. Nominal guesses replaced.
- **Unbounded scans declared** (review f.1): `book.alive()`, `book.seq`,
  `origins`, `_near_structure`'s `e.bars[:bs]` grow with run length —
  bounded on eval panels (≤237 bars) but unbounded on a continuous MQL5
  engine → windowed views + eviction policies spec'd in §4/§5.
- **`_ev_uip_born` is per-run** (review A-C7/f.2): the latch never
  resets; MQL5 needs a reset boundary — proposed new-CET-day reset,
  an explicit measured arm (§3).
- **Determinism contracts written** (review f.3/f.4): banker's rounding
  vs `MathRound`, `repr(sorted(geom.items()))` → canonical key spec,
  dict-insertion-order contracts, `id()` → index map, sets → bounded
  arrays, dynamic `meta_*` → fixed struct. §5.
- **Parity compares canonical tuples, not pickles** (review f.6); the
  canonical tuple itself gains `score/priority/touches` before any
  score-writing step is checkable (R72 §72.5b).
- EventBox spec corrected to **C-3**: `ev_uip+persist+lvfree+pb_birth`;
  `pb_write`/`buildstart` OFF (§3).

---

## 1. Reuse / retire map for `mql5/*.mqh`

| module | v2 fate | why |
|---|---|---|
| `PA_Perception.mqh` | **REUSE, extend** | Obj schema + CSV importer; add trailing fields (e.g. `exposed` if the demoted arbiter ever lands) — wire stays v1-compatible |
| `PA_Draw.mqh` | **REUSE** | draw grammar/themes unchanged |
| `PA_Visual.mqh` | **REUSE** | viewer renders snapshots |
| `PA_Types.mqh` | **REUSE, extend** | add `ENUM_PA_FAMILY`, `CPaEvent`, `PaEdge` board entry |
| `PA_Zones.mqh` | **RETIRE from perception path** | zone-era CPaCtx; lessons (incremental state, rings) already absorbed; keep file, no import |
| `PA_Setups.mqh` | unchanged consumer | reads snapshots only |
| zone-era salience hooks (CPaGenCtx SF02, D11/D12) | **RETIRE** | replaced by family pipes (+ whatever arms survive) |

New files (at port time): `PA_Engine2.mqh`, `PA_Pipes.mqh`,
`PA_Store.mqh`, `PA_Swing.mqh`. ~~`PA_Arbiter.mqh`~~ **dropped** — the
arbiter is off the critical path (ARCH_V2 §3.4); if a measured display
metric ever lands it returns as a thin ordering function, not a class.

## 2. Class mapping

| Python v2 | MQL5 | per-bar state |
|---|---|---|
| series (EMA/ABR/tol/todvol) | `CPaSeries` | EMA25, ABR ring (20), todvol table |
| `DCStream`+`SwingBook` | `CPaSwing` | DC state; pivot seq **ring 128** (measured ≤103) |
| `gates.py` | `CPaGates` | CET flags, hard_block, session_prior |
| `ObjectStore` | `CPaStore` | `Obj m_obj[64]` + active bitmap (measured ≤25, 2.5× headroom); **append-only, ids never recycled** |
| `BoxPipe`+EventBox | `CPaPipeBox` | asia tracker (fixed struct), congestion state, EvBox struct (§3), `_ttl` helper, watch reg ≤8 |
| `LinePipe` | `CPaPipeLine` | term/sess anchor trackers; revive list |
| `LevelPipe` | `CPaPipeLevel` | origins ring **64, expire-first** (measured ≤52; Python has no eviction → port diverges past 64 — flagged) |
| `BracketPipe`/`SqueezePipe`/`AnnotPipe`/`ContextPipe` | `CPaPipe*` | small fixed state; context family is a NEW split (C2 arm) |
| per-family pool | `Cand m_pool[32]` per pipe | measured residual total ≤53; per-family 32 + expire-first |
| events | `CPaEvent m_ev[8]` synchronous | measured births/bar ≤2; emissions are synchronous inline calls — the "queue" is a call frame, not a buffer |
| edge board | `PaEdge m_board[32]` | measured ≤9 live; rebuilt at stage boundary (see MIGRATION_PLAN B7 consumer table) |
| `Engine2` | `CPaPerception2` | `StepBar()` per closed bar |

## 3. EventBox port spec (C-3 exact)

```cpp
struct PaEvBox {
  bool born;         // per-run latch — Python: set once, never reset
  int  obj_idx;      // store index (-1 none)
  int  last_birth;   // pivot-seq idx of last birth (cooldown 10)
};
// triggers from CPaSwing.seq: range_double_* (sep>=8, |dP|<=2.0p,
// band=seg extremes +/-2, win 600) and pullback_end (span>=8);
// under pb_birth a pb cand may BIRTH at gate idx-t0a>=3.
// birth: height 6..34p, edge dedup max(1p,.25*ABR) vs live BOX,
//   then DIRECT store.Birth() — no pool, no rate ledger.
// rewrite: rd_* events rewrite (lo,hi,t0) in place; pb_write OFF.
// persist: close-veto on all kill paths.
// lvfree: no level-seeding emissions; excluded from other families'
//   tallies; counted only in box live.
// buildstart: OFF (byte-flat @c06365ce); field optional.
```

**Reset boundary — OPEN DECISION (blocks a correct continuous port):**
Python latches per engine lifetime = per eval panel. Proposed: reset at
each new CET day (aligns with `_asia_day`/`_asia` tracker boundary and
the per-day golden panels). Alternatives: session boundary, or never
reset + `uip_spent` forever. Whichever is chosen needs a measured arm
(a second birth/day changes box ink).

## 4. Per-bar state & bounded cost — honest version

Measured maxima (623 C-3 panels, TUNE windows ≤237 bars):

| array | measured max | proposed cap | headroom |
|---|---|---|---|
| objects/run | 25 | 64 | 2.6× |
| concurrent ACTIVE | 9 | 32 (edge board) | 3.5× |
| book.seq / alive() | 103 | 128 ring | 1.2× |
| defended origins | 52 | 64, expire-first | 1.2× — **policy needed: Python never evicts theta origins** |
| births per (bar,family) | 2 | 8 events/bar | 4× |
| LABEL_TF / run | 2 | day cap 2 (param) | — |
| pool residual | 53 all-fam | 32/family | per-family suffice |
| `_watch` / `_hidden_ctx` | 0 (flags OFF) | 8 | nominal |
| bars/panel | 237 | n/a — MQL5 is continuous | see below |

**Continuous-run consequence:** `seq`/`alive`/`origins`/`bars`-scans
grow with run length in Python and only look bounded because eval
panels are ≤237 bars. On MQL5 they must be **ring/capped structures
with stated eviction** (expire-first, windowed views) — each eviction
is a divergence risk vs Python and gets its own parity check.

## 5. Determinism contracts (review f.3/f.4 — the hard part)

The 1e-9 parity gate fails silently on these unless spec'd:

1. **Rounding:** Python `round()` = banker's (half-to-even); MQL5
   `MathRound` = half-away. Every `round(x, k)` in the engine (dozens:
   geometry fields, scores, `kernel._sig` keys, boxes dedup keys at
   `boxes.py:491/527/959`) must call one helper `PaRound(x,k)`
   implementing round-half-even. `.5` cases are the divergence point.
2. **Geometry-key canonicalisation:** pool sort key ends in
   `repr(sorted(geom.items()))` (`salience.py:676`). MQL5 has no repr —
   spec: `key = join("|", sorted(key+"="+fmt(v)))` with `fmt` =
   Python-repr-shortest float formatting (or round-trip %.17g); the
   comparator is total: `(-score, kind, route, t0, key)` — plus Python
   `sorted` is stable ⇒ ties keep insertion order; encode insertion
   index explicitly in MQL5.
3. **Dict insertion order:** `_watch`, `_asia`, `_grave_band`,
   `_hidden_ctx`, `_pedg_memo` rely on Python dict order → fixed arrays
   + explicit sequence counters in MQL5.
4. **`id()` → index map:** `_v0m` mirrors are keyed by `id(v0o)`
   (object identity) — port as object index → store-slot map (module is
   quarantined anyway, but the contract stands for any future mirror).
5. **`reversed(e.objects)`:** `_revive_target` depends on objects-append
   order → reverse index iteration, not a sorted view.
6. **Sets:** `_logged`, `_graved` → bounded bitmask/arrays (cap 16
   tags/cand — `_logged` holds ~6 outcomes max).
7. **Dynamic attrs:** `o._oi`, `meta_*` geometry keys → fixed `Obj`
   struct with optional fields (`has_build_start` bool + field).
8. **Accumulation order:** `sum(neigh)`, ABR/EMA recurrences, float
   adds in `score` — iteration order pinned; `double` both sides;
   document that ABR/EMA are order-sensitive recurrences (port the
   identical update order).

## 6. Parity harness (updated)

1. **Python export** (exists): JSONL snapshots → `jsonl_to_csv.py` →
   `perception_csv_v1`.
2. **MQL5 export**: parity script replays the same CSV bars →
   `CPaPerception2` → same CSV columns (extend `PA_Perception.mqh`
   serializer).
3. **Compare** (exists): `parity/compare_perception.py` joins
   `(bar_t,id)`; exact on type/state/role/side/letter/t1/t2/events;
   1e-9 on floats **after** the rounding contract of §5.1; gate ≥99.5%.
   **Compares canonical tuples — pickles are eval-side plumbing only**
   (review f.6).
4. **Invariance checks:** prefix invariance ([0..T] vs [0..T+k]);
   future-mutation; incremental-vs-batch (`PushBar` vs `Init` replay);
   same-input-twice byte-identical.
5. **Prereq (R72 §72.5b):** the canonical tuple gains
   `score/priority/touches` on the Python side first — else score-path
   divergences are invisible to both oracle and comparator.

## 7. Not included

- cand_log (Python-side diagnostic), watch/leg/dense/kde variants
  (quarantined), `_v0e` mirror (superseded — and its `id()` keys are
  the example for contract §5.4), param re-derivation (params ship as
  a generated `PaParams` struct).

## 8. Porting order (after P-FREEZE + this review absorbed)

```
PA_Types extend → PA_Store → CPaSwing (+gates+series) →
CPaPipeLevel + events → CPaPipeBox (+EventBox w/ reset decision) →
CPaPipeLine → Bracket/Squeeze/Annot/Context → CPaPerception2 →
parity script → compare gate
```

Per-module acceptance: each ported pipe must show ≥99.5% bar-identity
on the golden panel set before the next pipe starts. **Do not start
before the architecture freeze absorbs the review's (a)/(c) fixes**
(review §f closing note) — and §5's contracts exist first, because
parity against an under-specified reference cannot be proven.
