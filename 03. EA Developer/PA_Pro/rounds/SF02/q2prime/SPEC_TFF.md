# Q2' SPEC DRAFT — TFF: Trade-for-Failure (Volman)

Status: DRAFT, pre-P-FREEZE. No prereg/census/screen.
Source: notes_07 (pp.197-231), the barrier-reclaim rule is the key
perception test.

## Mechanism

A pattern breaks AGAINST the dominant pressure — toward/into a trending
EMA25. The trapped side must exit; their stop-outs fuel the with-trend
move. We do not take the counter-break; we wait for it to FAIL, then
enter with the pressure.

## Entry rules (signal bar t)

1. `facts.stand_aside` empty.
2. `pressure.state` trending (sloped EMA25 with hysteresis); the
   intended trade is WITH that pressure.
3. A pattern (BOX edge, dashed barrier/flag line, LEVEL_CARRIED) broke
   AGAINST the pressure within the last ~1-24 bars — the counter-break
   bar crossed the edge.
4. Context preference: the counter-break happened at/near the FIRST
   retest of EMA25 since the dominant wave began
   (facts.ema_retouch_count); later counter-breaks are weaker
   (recorded as optional, not vetoed).
5. No follow-through: after the counter-break, price failed to hold
   beyond the barrier (no second counter-close beyond it, or an
   immediate stall).
6. **Barrier-reclaim rule (hard veto):** the signal bar's extreme must
   be back across the barrier.
   - long (failed down-break): signal bar's HIGH >= barrier - tol;
     never buy while its high is still below the barrier;
   - short (failed up-break): signal bar's LOW <= barrier + tol.
7. Signal: a strong reversal bar in the dominant direction (range
   >= ~1*ABR, closes in its with-trend third) — OR a combi whose break
   crosses back.
8. Pluses (recorded): small W/Morning-Star in the failure zone; signal
   bar also breaking a diagonal pullback line; entry via a combi.
9. Room rule: first obstacle in the dominant direction >= 14 pips.
10. Skips: price still parked on the wrong side of the broken barrier;
    counter-break holding consistently (trend may have changed —
    stand aside); abnormally long bars.

## Order semantics

- Stop entry 1 pip beyond the signal bar's with-trend extreme.
- Invalidation: the failure-zone extreme (the counter-break's deepest
  poke) or the nearest with-trend swing.
- Target: 14-pip rule.
