# STUDY_PLAN ADDENDUM — M4b: shifted-box placebo for F-BO and F-FB

Status: preregistered BEFORE computation.  Amend `STUDY_PLAN.md` §5 only
for the placebo arm of the box families; everything else in §5 is
unchanged.  Ruling-2 item 4 (optional M4b).

## Motivation

The declared §5 P-RAND fake-edge placebo is underpowered (~48 breaks,
~60–110 pokes per symbol) and produces fake traversal heights ~0.2 ABR
vs real box heights ~5 ABR, so the height-tercile strata barely overlap
and F-BO/F-FB are not identified (DEVIATIONS D22).  This addendum
declares a redesigned placebo that is exchangeable AND dense, in the
spirit of the accepted M5 shifted-line placebo.

## Design — SHIFTED-EDGE copies (P-SHIFT), two arms

For every real confirmed box `B = [lo, hi]` born at bar `b` and dying at
bar `d` (first break or the 100-bar age cap), with `h = hi - lo` and
`A_b` = ABR at birth:

**Arm OUT (serves F-FB pokes).** Two fake edges beyond the box, seeded
by `crc32(sym | box_index | side)`:

- `E_up  = hi + g*A_b`,  fake opposite target `O_up  = E_up - h`;
- `E_dn  = lo - g*A_b`,  fake opposite target `O_dn  = E_dn + h`;
  with `g ~ U[0.5, 2.0]` per edge.
- Each fake edge is alive exactly during `[b, d)` and dies at its own
  first break, whichever comes first.  (A close beyond an OUT edge also
  closes beyond the real edge, so OUT edges almost never produce breaks
  — they exist to generate pokes.)

**Arm IN (serves F-BO breaks).** One fake interior level per box,
seeded by `crc32(sym | box_index | "in")`:

- `E_in = lo + u*h` with `u ~ U[0.2, 0.8]` — a non-edge level inside
  the range.
- Alive during `[b, d)`; dies at its first fake break or the parent's
  death.
- Fake BREAK = the first close >= `tol` beyond `E_in` in either
  direction (side = crossing direction).  This is the exchangeable
  counterpart of a real edge break: a close crossing a level from the
  inside, same `tol`, same session/lifetime; only the level's position
  (interior, non-structural) differs.  It identifies "is leaving the
  box special vs crossing inside it".

Exchangeability: the fake edge carries the real box's height `h` as its
declared traversal distance, the same lifetime and the same
session/day/ABR context; only its price coordinate sits at a
non-structural location `g*A_b` beyond the real edge.  A fake poke at
`E_up` (price below wicks through and closes back below) is the same
geometric event as a real top-edge poke (price inside wicks through and
closes back inside), and the reversal target sits at distance `h` in the
reversal direction — exactly the real box's traversal distance.

## Events on each fake edge — identical machinery to §5

- BREAK dir +1 on `E_up`: `c[t] > E_up + tol[t]` while alive (one break
  per edge; the edge dies at its first break).  Mirror on `E_dn`.
- POKE dir +1 on `E_up`: `h[t] > E_up` and `c[t] <= E_up`; consecutive
  poking bars merge into one event with max penetration.  Mirror on
  `E_dn` (`l[t] < E_dn` and `c[t] >= E_dn`).
- No extra freshness filter: the §5 real detector applies streak-merge
  only, so fake edges get exactly the same rule.
- Warmup bars excluded; event fields identical to real events
  (day/year/cet_min/dow/side/abr, box_h_pips = parent height).

## Outcomes — identical to §5

- Fake break → `race24` (>=1*ABR beyond the fake edge before >=1*ABR
  back through it, H=24), `fwd_{6,12,24,48}`, `mfe24`.
- Fake poke → `reach_opp` = reach the fake opposite target `O` within 24
  bars; `converted` = close beyond the fake edge within 3 bars.

## Family F-Xb (BH-FDR q=0.10, 5 tests)

1. `race24`: D = P(race win | real break) − P(race win | fake-edge break).
2–5. `poke->reach_opp` D by disjoint depth bins (0,1],(1,2],(2,3],(3,5]
   pips, real vs fake-edge pokes.

Descriptive only (no q): `fwd_*`, `mfe24`, `buildup_minus_none` (the
buildup contrast is real-vs-real and already reported in M4), pooled
rates.

Strata: side × dow × 4h-bucket × ABR-tercile × height-tercile × symbol,
per-symbol quantile edges — same construction as M4.  `min_cell=5`,
day-block bootstrap B=2000, stability 4/6y + 3/4s — unchanged.

## Acceptance criterion declared up-front

F-Xb is identified iff the placebo arm contributes >= 500 breaks and
>= 500 pokes pooled across symbols AND >= 30 per symbol per arm; if it
fails, report descriptive real rates only and mark the family
unidentified — no further placebo redesign inside this lane.
