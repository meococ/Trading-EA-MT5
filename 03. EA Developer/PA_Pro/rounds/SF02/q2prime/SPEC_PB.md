# Q2' SPEC DRAFT — PB: Pattern Break (Volman)

Status: DRAFT against the Snapshot contract (SNAPSHOT_CONTRACT.md).
NO prereg, NO census, NO screen — binding spec comes after P-FREEZE.

## Mechanism

A frozen BOX (or established PATTERN_LINE) breaks WITH the dominant
pressure out of a proper buildup resting on the edge. Double pressure:
with-side opens, opposite-side stops fire.

## Entry rules (all must hold at signal bar t, causal)

1. `facts.stand_aside` empty.
2. `pressure.state` agrees with the break side (UP for a top-edge
   break). An H1 trend never overrides steep opposite M5 pressure —
   pressure is the M5 EMA25 slope-with-hysteresis output, not HTF.
3. A live BOX exists whose breakout-side edge has >= 2 touches
   (non-breakout edge may be single-touch) and whose edges stayed
   frozen (no unlogged moves).
4. Buildup: the bars immediately before the break rest ON the edge
   (within 1*ABR of it) with shrinking ranges — the break class must
   be `proper` per facts.break_class or equivalently derived here.
5. Signal bar: CLOSES beyond the edge, or ON it when the squeeze rules
   say "fills the last gap" — the signal bar may close on the line
   (corrected rule; NOT necessarily beyond it).
   For a PATTERN_LINE/MINI_LEVEL trigger, the break is of the SHORT
   trigger line, not the big edge alone.
6. Room rule: first real obstacle in the trade direction >= 14 pips
   from the entry (facts.obstacles_*; soft floor ~13). Skip otherwise.
   Obstacles include LEVEL_CARRIED, box edges, double tops, TL
   extensions, dense congestion — a touched/carried level counts once.
7. Veto: news window in facts.stand_aside; abnormal long bars
   (>= 2*ABR) in the signal area; counter-magnet within ~10 pips behind
   the entry.

## Order semantics (post-P-FREEZE binding)

- Entry: stop order 1 pip beyond the signal bar's extreme
  (long: above signal high; short: below signal low).
- Invalidation: far side of the buildup/box — the nearest clear swing
  behind entry (structural stop).
- Target: first real obstacle >= 14 pips, or 20 pips standard —
  decided at entry (fixed-R engine maps this to tp_mult choice later).

## Detector signature (fixture phase)

`detect(snap, params) -> dict|None` evaluated per bar; returns
{sig, side, order_px, inv, why}.
