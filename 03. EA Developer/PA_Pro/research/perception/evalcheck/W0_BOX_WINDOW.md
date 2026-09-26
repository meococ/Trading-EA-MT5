# W0 — BOX window semantics diagnostic (LEAD_NOTE_R13)

Measured: 2026-09-21 ~20:0xZ.  Engine: cached v1 `694313a38abc2da6`
(the render `rv/694313a3_9.54a.png` the Lead viewed) and v0
`63c771d64e18f619`; also re-counted on `1f4bed5be55908d9`.  Ruler:
`eval_v2 50e11fd5` (frozen, unchanged — this is a report only).

## 1. Panel 9.54a — the tagged MISS

Golden BOX: drawn 120→550, edges 1.28154/1.28371, `build_start`
absent, `build_end=470`, status `repaired`, prec `eye` — but
`repair_method` ∈ REFINED_METHODS → **tol = 1.5 p** (bar-anchored
repair carries the 1.5 p model, not the eyeball 5 p).

Engine BOX-family objects overlapping it (windows in CET minutes):

| object | drawn t0..t1 | eng window (bs..be) | break_bar | IoU vs gold 120..470 | overlap coef | edge Δ (p) | route | verdict |
|---|---|---|---|---|---|---|---|---|
| RANGE_OPEN | 120..465 | 20..465 | — | **0.767** | 0.99 | lo −1.9, hi 0.0 | containment_iou | **FAIL on edges** (1.9 > 1.5 tol) |
| CONTEXT_RANGE | 120..540 | 30..540 | — | 0.686 | 1.00 | lo −6.1, hi +0.1 | containment_iou | FAIL on edges |
| BOX (why=…) | 120..215 | 35..120 | 185 | 0.00 | 0.00 | lo +12.4 | box_span | correct miss (different place) |
| BOX (why=…) | 245..520 | 245..395 | 490 | 0.429 | 1.00 | lo +7.5, hi +0.1 | coverage | FAIL on edges (7.5 p) |

The Lead's "same edges, same episode" box is the RANGE_OPEN (and the
CONTEXT_RANGE).  The ruler is **not** misreading the containment
window here — IoU 0.77 is a comfortable pass.  What fails the match
is the **edge check at the repaired 1.5 p tolerance**: the engine's
low edge is 1.9 p off the repaired golden edge.  Had the object been
`prec=eye` un-repaired (tol 5 p), it would match.

So the ruler did its job; the near-miss is a sub-tolerance edge
error against a *repaired* (bar-exact) label.  This is consistent
with the Z1 taxonomy: `none_within_2tol` / near-miss edges dominate
— generation is within ~2 p, not ~0.5 p, of the bar-exact labels.

## 2. Semantics of `meta_build_end` per route

Golden `build_end` (GOLDEN_AUDIT D9) = last bar before the first
decisive close outside the band.

Engine records, per route (boxes.py):

| route | meta_build_start | meta_build_end |
|---|---|---|
| asia_session | range start `a["start"]` | conversion bar `i` = proposal time (boxes.py:498) |
| congestion_scan / pullback_end | `bs` = start of the contiguous inside-close run | `be2` = run end extended through the confirm bar `i` = proposal time (boxes.py:202,391) |
| RANGE_OPEN | — (none recorded) | — |
| CONTEXT_RANGE | — (none recorded) | — |

`break_bar` is recorded separately at break confirmation
(boxes.py:558) and can be much later.

**Finding: the semantics differ.**  Golden `build_end` is
break-adjacent; engine `meta_build_end` is *proposal-time* (the
buildup run's end through the confirm bar).  A correct engine that
proposes early — which is exactly what the §13.4 blueprint wants —
records a window that ends well before containment actually ends.
`_eng_window` prefers `be` over `break_bar`, so the ruler currently
measures "evidence window", not "containment window".

## 3. Panel-wide count (198 TUNE panels)

Engine BOX-family objects whose recorded `be` precedes their own
`break_bar` by > 30 min (proposal-time signature):

| engine | objects with be < break−30m | current matches (of their golden pairs) | extra matches if window were `bs..break_bar` |
|---|---|---|---|
| v0 | 0 (v0 records no meta windows) | — | — |
| v1@694313a3 | 219 | 4 | **+2** |
| v1@1f4bed5b | 218 | 3 | **+2** |

Of the pairs that still fail with the `bs..break_bar` window:
~118-120 fail IoU (the box is simply elsewhere — wrong place), and
~11-14 fail edges (window fixed but prices off).

## 4. Conclusion and proposed conversion rule

- **The ruler is not misreading the engine's windows.**  The 9.54a
  MISS is a genuine 1.9-pip edge error against a 1.5-pip repaired
  label — and, more broadly, `meta_build_end` really does mean
  something different from `build_end` (proposal time vs break
  adjacency).
- **Proposed conversion rule (for the Lead to rule on):** the
  engine containment window should be `meta_build_start ..
  break_bar` when a `break_bar` is recorded, and
  `meta_build_start .. drawn t1` (clipped) when the box never
  broke — i.e. prefer `break_bar` over `meta_build_end`, since
  containment ends at the break, not at the proposal.
  - Empirical weight of the change: **~+2 golden boxes matched
    (≈ +0.02 recall) on current v1**.  Most wrong-window objects
    are wrong-*place* objects; fixing the window convention does
    not buy recall.  The honest read: the proposal-time convention
    is semantically wrong but quantitatively near-free either way.
  - Risk of the change: extending windows to `break_bar` can only
    raise IoU vs golden windows that run to `build_end`; it cannot
    shrink a match that exists today, so adoption is monotone-safe
    for recall (verify: no current match relies on the short
    window — none do by construction, IoU only grows).
- Recommendation to the Lead: adopt the conversion (it is the
  semantically correct containment window), but do not expect it to
  move the scoreboard — BOX's ceiling stays a generation/edges
  problem (Z1).

> CORRECTION (R19 §19.1, appended — original text above unchanged):
> the "monotone-safe, IoU only grows" claim is FALSE.  Extending an
> engine window past golden `build_end` enlarges the union without
> adding intersection, so IoU can fall and an existing match can be
> lost.  The +0.02 figure was gross gains only; net (with losses)
> was not measured.  Any future proposal must report net gains AND
> losses.

> NET MEASUREMENT (appended 20:3xZ, R19 §19.1 follow-up): on cached
> runs, conversion be -> break_bar_min gives BOX matched-set
> +2 gains / -1 loss = NET +1 of 108 (~+0.01 recall) on v1@1f4bed5b
> and v1@4aaa6a7a; 0 on v0.  One existing match IS lost by the
> extension, as R19 predicted.  Ruler unchanged.
