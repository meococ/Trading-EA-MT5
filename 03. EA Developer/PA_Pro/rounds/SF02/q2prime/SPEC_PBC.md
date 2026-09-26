# Q2' SPEC DRAFT — PBC: Pattern Break Combi (Volman)

Status: DRAFT, pre-P-FREEZE. No prereg/census/screen.

## Mechanism

A combi is ONLY an entry-timer inside an already-valid breakout
situation — never a reason to trade by itself. Core pair: a strong bar
(dominant pressure) followed by an inside bar (pressure building next
to it). The break of the pair is the entry.

## Entry rules (signal = second bar of the pair, at bar t)

1. `facts.stand_aside` empty.
2. Context (required): the pair sits at a breakout boundary — a frozen
   BOX edge, a PATTERN_LINE, or an M/W middle MINI_LEVEL — with the
   dominant pressure aligned.
3. Pair anatomy (bar t-1 = strong bar, bar t = inside):
   - strong bar: range >= ~1.5*ABR, closes strongly in the pressure
     direction (close in its extreme third);
   - inside bar: high <= strong high and low >= strong low (slight
     protrusion tolerated in a cluster);
   - colour: inside bar preferably same direction as the strong bar,
     or flat/neutral; opposite colour acceptable only if it sits in the
     with-trend half of the strong bar;
   - variants accepted: doji as the inside bar; 3-bar combi (two inside
     bars); two long same-direction dojis; reversed combi (inside bar
     first, third bar confirms the false extreme).
   - plus: both bars share the break-point extreme (two-bar break).
4. Entry: stop order 1 pip beyond the inside bar's with-trend extreme;
   when the pair's shared extreme is the strong bar's, the strong-bar
   break may be used instead.
5. Room rule: first obstacle >= 14 pips.
6. Skips: combi forming a bull/bear trap against pressure (that is TFF
   territory); combi right at a prior high far from EMA25 with a round
   number behind; break straight after a rally with no pause;
   unpredictable-range context; news bars.

## Order semantics

- Stop entry beyond the inside bar (or shared extreme).
- Invalidation: opposite end of the combi (inside bar's other extreme)
  or the pattern edge if structurally nearer.
- Target: 14-pip rule.
