# FOR THE OWNER — what the author's levels are (10 lines, LEVEL-LAB)

1. The author draws few levels (~1–2 per panel) and each is a *defended
   price*: a swing pivot, session high/low, or Asia extreme that price
   came back and respected at least twice.
2. The level is drawn when price *approaches* it again — not when it
   forms.  Its job is to mark where resting orders may still sit.
3. Same price, different story: a retested pivot is carried forward
   (LEVEL_CARRIED); a fresh micro-extreme is a MINI_LEVEL with a short
   life (~90 min) — young vs old ink.
4. When two defences disagree by a pip or two the author keeps the
   *outer* edge — the worst price that was defended, never the average.
5. The author lets levels die: a close through them, price walking
   away, or hours without a touch — and will redraw the same price if
   it becomes relevant again.
6. Example 1 (panel 9.3c): "a solid horizontal support ~14:10–16:45 at
   ≈1.3215" — a pivot defended all afternoon, then carried as a dashed
   continuation (~16:45–17:25) once it became history.
7. Example 2 (panel 9.1b): "a long-dashed horizontal ~09:30–12:00 at
   ≈1.3318 (the old breakout base)" — the morning's defended base,
   marked when price rallied back to it.
8. What the engine now does with the flag on: register every pivot /
   session extreme as an *origin*, count distinct retests (defences),
   and propose the level only when price returns within ~1.75 ABR.
9. A 2-LC + 1-MINI live budget keeps the strongest defended origins
   (score = defences − distance + a fresh touch), evicting the weakest.
10. Net measured effect on TUNE: +4 LEVEL_CARRIED matched (recall .23
    vs .15), same clutter — but it cost 2 BOX objects, so the flag
    stays off until the Lead weighs it (REQUESTS.md REQ-L3).
    A "carried-levels-only" variant (v2, defended MINIs off) keeps the
    boxes safe (+1 BOX, no flicker) but gives back most of the gain
    (recall .17) and still bumps 2 PATTERN_LINEs off the birth queue.
    A second variant (v2b, every defended birth typed LEVEL_CARRIED)
    keeps every family within one drawing of baseline — but the Lead
    ruled it not kept: total recall does not rise and it adds one live
    object at decision time.  Every variant still spends the same
    shared "5 births per ~6 hours" ledger that lines and boxes need.
    The fix landed (R25 §25.5, verified by the reviewer at 9283b389):
    with each family on its own ledger (`fam_ledger`), the
    defended-LC route keeps its +4 LEVEL_CARRIED born gain
    (recall .21 vs .12 on the reviewer's ruler) and **no family
    loses more than one drawing** — same clutter, same flicker.
    Honest caveats the pack carries (R29 §29.2): the ledger v1
    silences four kinds that have no share entry, its isolation is
    partial (shared live budget/NMS/timing), and at the author's
    1-drawing budget under the engine's own ranking the gain is not
    yet visible — so it is a **direction, not a result**.  Two flags
    stay OFF by default (ROUND_L12).
