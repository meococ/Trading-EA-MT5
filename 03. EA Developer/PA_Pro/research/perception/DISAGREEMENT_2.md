# DISAGREEMENT_2 — B3 round 2: box buildup geometry + drawn-span eval

Date: 2026 (B3, second disagreement round).  Scope: BOX construction
(`boxes.py`) + one eval-side fix.  v1 metrics move vs end of round 1:

| metric | r1 end | r2 | gate |
|---|---|---|---|
| BOX recall | 0.05 | **0.12** (13/111) | >=0.70 |
| RANGE_OPEN recall | 0.12 | 0.25 | — |
| BRACKET recall | 0.01 | 0.02 | — |
| clutter median | 4.33 | 4.33 | <=1.5 |
| PATTERN_LINE recall | 0.02 | 0.02 | >=0.50 |

## What changed (all measured, no hand tuning)

1. **`_propose_window` rewritten to the D9 buildup semantics.**
   Before: cluster edges over a whole pivot-leg window, then the
   longest contained run — outermost clusters let excursion pokes set
   the edges (engine drew 44-pip boxes where golden drew ~13).
   Now: the confirming pivot IS the second touch —
   - anchor edge = the defended cluster within `tease_tol` of the
     pivot's price on its side (a touch 20 pips inside a wide band is
     not a touch of that band);
   - opposite edge = tightest cluster whose band yields a contained
     run of >=min_build closes through the touch bar (golden prefers
     the tight core; buildup median = 7 bars, p90 = 28, max = 45 —
     measured);
   - edges rebuilt on the run to a fixed point (<=3 iters);
   - alternation prior measured on the candidate span [s, i], not the
     tight run (a 9-bar buildup contains only the confirming pivot —
     golden's own drawn span holds the alternating sequence).
   Canonical check (9.23c): engine proposes [13291.1–13302.8]
   t0=920 vs golden [13292–13305] t0=890.

2. **`congestion_scan` route (bar-driven birth).** Tight buildups
   (9.44a class, DN_BOX §6 listed false-negative) never confirm a
   pivot inside their own range — the swing stream's k1/pmin floors
   are above the wiggle size.  Per-bar route: last-k-bars seed
   clusters -> `_buildup_run` -> same gates.  Micro pivots also feed
   `on_pivot` now (the *touch* may be micro; the window/alternation
   prior stays theta2).

3. **eval.py fix (yardstick bug, not engine):** objects still alive at
   the panel's right edge reported `t1 = day end (1430)` instead of
   `t1 = w1`.  Every live-at-edge object's drawn span was inflated to
   the full day — killed IoU for every correct box.  Born-with-edges
   30 -> IoU>=0.5 went 7 -> 18 after the fix.

## Funnel after round 2 (111 golden BOX)

- proposed with golden geometry (edges within 6p): **86**
- actually born with golden geometry: **32**
- eval-matched (IoU>=0.5 + edge tol): **13**
- never proposed with right geometry: **25**

Outcomes of the 54 proposed-but-not-born: `rate_limited` dominates
(223 log rows) then `expired` (140) — right candidates sit in the
pool behind a rate slot an earlier non-golden box already spent,
then die on `cand_ttl` (24 bars) before the 72-bar window rolls.

## Open for round 3

- **Rate-slot ordering**: first-come-first-served spends the family
  rate on whichever congestion confirms first; golden-right candidates
  arriving later lose.  Options: (a) longer `cand_ttl` so they survive
  until the window rolls; (b) let a rate-blocked challenger displace
  the recent same-kind birth by hysteresis margin (needs ledger
  refund semantics); (c) accept the rate and improve what arrives
  first (score can't separate golden-right from golden-wrong —
  matched/unmatched medians were both ~8.5 in round 1).
- **25 never-proposed**: mostly boxes at panel edges / post-window
  (9.44a's box is outside w1), or bands whose extremes lack company.
- **Span offsets**: golden t0 precedes build_start by ~10 min median;
  our t0 = first contained close.  Cheap improvement candidate: t0 =
  extreme bar of the pivot that began the congestion.
- LINE selection still unsolved: 4/186 matched; ~30% of golden lines
  not expressible by the confirmed-pivot stream even with named-bar
  anchors.
