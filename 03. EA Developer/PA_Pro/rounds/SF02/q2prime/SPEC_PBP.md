# Q2' SPEC DRAFT — PBP: Pattern Break Pullback (Volman)

Status: DRAFT, pre-P-FREEZE. No prereg/census/screen.

## Mechanism

A proper break already happened (PB fired or not). Price returns to the
broken edge's extension (role reversal) or stalls just outside it. The
retest offers the second-chance entry with the dominant pressure.

## Entry rules (signal bar t)

1. `facts.stand_aside` empty.
2. A BOX/PATTERN_LINE is in state `broken` (close >= tol beyond edge
   earlier), its extension still drawn (t_right open or covering t).
3. The earlier break was `proper` (break_class) — tease/false breaks do
   not qualify for the pullback continuation read.
4. Pressure still agrees with the break direction.
5. Pullback path: price came back to the extension — within tol of the
   carried level — AND one of:
   a. signal bar pokes through the extension and closes back on the
      with-trend side (the classic PBP trigger), or
   b. price stalls at the line: 1-3 small bars (range <= 0.8*ABR)
      sitting on the extension, then a with-trend bar closes on/through
      the mini trigger line (MINI_LEVEL at the stall's extreme).
6. The pullback must not re-enter deep: a pullback that closes back
   INSIDE the box (beyond the far half) reads as a failed break —
   skip (that is TFF territory, not PBP).
7. Room rule: first obstacle in trade direction >= 14 pips.
8. First-retest preference: flag `is_first_retest` when this is the
   first touch of the broken edge since the break; later retests are
   weaker (recorded, not vetoed).

## Order semantics

- Stop entry 1 pip beyond the signal bar extreme (with-trend side).
- Invalidation: pullback extreme (the dip back through the edge), or
  box far edge if tighter to structure.
- Target: 14-pip rule as PB.
