# Q2' SPEC DRAFT — PR: Pullback Reversal (Volman)

Status: DRAFT, pre-P-FREEZE. No prereg/census/screen.

## Mechanism

A counter-wave (price or time correction) against the dominant pressure
exhausts at/near the EMA25 and turns back with the trend. Best case:
the FIRST pullback after a new wave/trend leg.

## Entry rules (signal bar t)

1. `facts.stand_aside` empty.
2. `pressure.state` = with-trend direction of the intended trade.
3. Pullback exists: a counter-wave off the main-wave extreme; the
   wave anchor is the start of the impulsive leg (first wide-range bar
   leaving the EMA area), not an older congestion extreme.
   Depth ~40-70% of the main wave (recorded, softly gated).
4. EMA test: the pullback touched or slightly pierced EMA25 — this
   rule alone avoids most PR traps. Skip corrections that reverse far
   from the average without touching it.
5. Reversal evidence at the pullback extreme, any of:
   a. buildup: >= 1-3 congestion bars at the extreme, then a
      with-trend signal bar;
   b. M/W middle-section break: the counter-wave itself forms an M
      (in a rising pullback) — entry on the break of the bar that
      completes the middle section (MINI_LEVEL);
   c. second break: a first with-trend break failed, the next
      with-trend bar (the second break) is the trigger — stronger than
      the first attempt;
   d. the pullback's own trendline (PATTERN_LINE, slope rule applies)
      is broken by a bar closing on/through it.
6. Prefer facts.first_pullback == True; later pullbacks allowed but
   flagged weaker.
7. Room rule: first obstacle >= 14 pips (a PR that must cross a
   sideways zone runs into more trouble — range context is a minus).
8. Skips: abnormally long bars nearby (>= 2*ABR — market abnormal,
   stops unsafe); counter-magnet behind entry; pullback that never
   retested an existing element.

## Order semantics

- Stop entry 1 pip beyond the signal-bar extreme (with-trend).
- Invalidation: pullback extreme (the far end of the counter-wave).
- Target: 14-pip rule.
