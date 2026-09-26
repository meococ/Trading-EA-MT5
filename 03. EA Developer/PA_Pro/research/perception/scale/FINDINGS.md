# SCALE lane — findings for the build lane (C-round 1)

All findings are on snapshot `engine_e62f2dc9` (live hash at lane start),
DESIGN 2016–2021, outcome-blind. Repro commands are at the bottom.

## F1 — Engine throughput collapses quadratically with run length

`PerceptionEngine.update` cost grows ~linearly in the number of objects
*and swings* accumulated, so a long continuous run degrades badly:

| run length | objects at end | sustained rate |
|---|---|---|
| 288 bars (1 day, fresh)  | ~20–60  | ~720 bars/s (Q1) |
| ~6 000 bars (~21 d)      | ~200    | ~113 bars/s |
| 12 160 bars (~52 d)      | 888     | **57 bars/s**  |

Profile of a 6 484-bar run (KEPT, EURUSD 2017-03, `cProfile`):

```
195 s total; ~170 s inside swings.py:
  519 310 437 calls
  swings.alive      78 067 calls   122.1 s cum
  swings._floors   111 796 629 calls  78.0 s cum
  swings.floor_min  98 095 623 calls  93.6 s cum
  engine._abr      111 796 629 calls  40.4 s cum
  salience.round    6 484 calls      96.8 s cum
  salience._lab_line_score  45 594 calls 77.9 s cum
```

`swings._floors`/`floor_min` is called ~17 000× per bar (once per
live-swing scan inside `alive`), and `engine._abr` recomputes a linear
scan for every one of those calls. The swing book is a flat list with
no indexing — each `alive` query is O(all swings), and each `floor_min`
re-walks the swing list.

Suggestions for the build lane (no SCALE edit made):
1. Cache/index `swings._floors` by (dir, price band) or by a rolling
   structure; `floor_min` looks like a candidate for a deque/heap.
2. `engine._abr` is re-evaluated per swing check — hoist it to a
   per-bar value (it already is `self.abr[i]`; the hot path is
   `PerceptionEngine._abr` at engine.py:184, called from inside the
   floor loop — pass `abr` down instead).
3. If continuous multi-week runs are a goal, an object/lifecycle sweep
   (dead objects leave the salience ledger sooner) also bounds the
   per-bar scan.

Impact on this lane: Q2–Q4 use fresh engine per measured day +
5-trading-day warmup, which keeps each run in the ~150–300 bars/s
regime. Statistics that depend on objects born >5 trading days earlier
(long CONTEXT_LINEs, ancient LEVEL_CARRIED) are slightly undercounted;
noted in SCALE_REPORT.md.

## F2 — prefix-invariance comparator artifacts (not engine bugs)

Two engine behaviours make a naive "final object state" comparator
report false causality breaks. Both are *correct* engine behaviour:

- `boxes.py` `asia_convert` mutates a live RANGE_OPEN into BOX in place
  (`o.type = "BOX"`). Comparing final type to a prefix run's type at t
  misfires; reconstruct type-at-t from the event log.
- `lines.py` `revive` re-opens a *closed* object (same id) on a later
  re-trigger. Final `t_right`/`state` are not the state at t; compare
  liveness at t and event history truncated at t.

After the comparator projects full-run state to t (`_type_at`,
liveness-at-t, events ≤ t), Q1 is clean: 1000/1000 sampled timestamps
invariant on KEPT and STABLE, byte-identical reruns, zero genuine
causality failures.

## F4 — the asia unlogged edge moves are the forming RANGE_OPEN

Q2 shows ~11–15 unlogged edge moves per 100 asia bars on both arms.
A 5-day probe (EURUSD 2017-03-06..10, KEPT) attributes them:

```
52x RANGE_OPEN  UNLOGGED  (no event at the bar)
24x PATTERN_LINE logged   re_anchor
13x PATTERN_LINE logged   re_anchor + tease_pierce
 6x CONTEXT_LINE  logged   re_anchor
 5x CONTEXT_LINE  logged   re_anchor + tease_pierce
 3x BOX          logged   re_anchor
 2x BOX          logged   asia_convert
```

Cause: `boxes.py:713-716` — while the Asian range is forming
(00:00–08:00 CET), the live RANGE_OPEN's `top`/`bottom`/`t1` are
re-written every bar with no event.  Under spec §6.1 ("edges stable
once drawn, except logged re-anchors") this is silent ink movement —
but the object is still *forming*; its edges are meant to extend until
`asia_convert` finalises them.

Design question for the build lane: either log a `track`/`extend`
event on each forming update (auditability), or declare forming
RANGE_OPENs exempt in the spec and stop drawing them before they
finalise.  Outside asia, unlogged moves are ~0–0.4/100 bars — clean.

## F5 — render.py object layer is off by 1e8 (latent, found by Q5)

`render.py` mixes two pip conventions in one file:

- candles / grid / padding treat `bars` as PRICE and `PIP=1e-4` as
  price-per-pip: `p_lo - 8*PIP`, `p += 50*PIP` — correct.
- the object layer does `vm.y(g["top"] / PIP)` — for engine geometry in
  pips that is pips×10 000, landing ~1e8 off-canvas; PIL then either
  draws nothing or crashes on the astronomic coordinate
  (`draw_bitmap`/`x1>=x0` errors).

It needs `g["top"] * PIP` (pips→price), or PIP=1e4 with the padding/
grid sites flipped.  The gallery works around it by feeding a scaled
objects-view (`gallery.py` `_ScaledObj`, ×1e-8).  Any QA overlay that
drew engine objects through this file was silently blank — worth
checking whether any existing artefact relied on it.

Also: `render_engine` uses minute-of-day as the x-axis, so bars arrays
must be single-day — multi-day arrays wrap onto the same axis
(gallery.py slices to the target day and shifts object indices).

## F3 — USDJPY pip-scale mismatch (Q3 detail)

`engine.PIP = 1e4` is hardcoded. For USDJPY (true pip 1e-2) every
pip-denominated threshold sits at 1/100 of its intended scale and the
20/50 round grid
never matches real JPY rounds (110.00/110.50 are 5 000 engine units
apart, not 50). See the Q3 table: USDJPY rows diverge from EURUSD/
GBPUSD/AUDUSD on every pip-scaled statistic. A per-symbol `pip_size`
param (default 1e-4) feeding `update()` is the minimal fix.

## F6 — K6 congestion boxes are the tallest, longest objects at scale

Measured on the frozen 9acaa206 (arm C1) vs the previous STABLE on the
same 240 EURUSD days: asia box height median rose 5.2 -> 8.6 ABR
(author 3.45; new >2x flag in 6 cells) and asia box duration 61 -> 100
bars (8 flagged cells).  RANGE_OPEN births collapsed 0.35 -> 0.01/day,
so the trigger works as intended — it births finished boxes — but the
bands it selects sit wider and live longer than anything the author
draws.  If the next round keeps tuning cong_*, bound the band by
height (in ABR) at trigger time, or let a tall candidate split.
