# MINI_LEVEL follow-up (V6)

Same method as LEVEL_CARRIED — V1 audit, V2 anatomy, V3 funnel, V4 lab
rounds already cover both types. This note collects the MINI-specific
findings.

## Golden shape (V1/V2)

- 32 objects (31 scorable); `edge_from_bars` 19, `text_anchor_bars` 8,
  `text_price` 4. Trusted 27.
- Spans short (p50 25 min vs LC 110), touches dense (p50 11.5),
  zone width 5.4p. **Origin age is NOT the discriminator**: MINI origin
  age p50 325 min ≈ LC 365 min. What differs is the *drawn role* — a
  micro support step under live price vs a carried wall.
- Origin classes: θ2 50%, asia 18%, session 11%, θ1 11% — same
  universe as LC. 12/32 goldens are `span-only` labels ("a short
  horizontal ~HH:MM") — the weakest definitional tier.

## Lab performance (final config: edge + side-free reprice + ms=1.0 + grace48)

| ruler | recall | trusted | oracle | snapshot |
|---|---|---|---|---|
| eval.py | 0.719 | 0.759 | — | — |
| eval_v2 | 0.677 | 0.714 | 0.774 | 0.667 |

vs engine v1: born recall 0.065, oracle 0.16 → **10× recall, 5× oracle**.
(L4b interim numbers were 0.613/0.643 — the L5 reprice + score-floor
changes lifted MINI too.)

## Type-emission rule — caveat for integration

Lab emits `MINI_LEVEL` when origin age ≤ 90 min, else LEVEL_CARRIED.
The ruler matches at family level (`FAMILY: both -> "level"`), so the
split is recall-neutral — measured: LC goldens are hit by MINI objects
18× vs LC objects 15×; MINI goldens hit by MINI 12× vs LC 8×. The
emission rule should follow *role* (micro step vs carried wall), not
age — keep `mini_max_age=90` as a cheap proxy, flagged lab-only.

## Residual misses (19/31)

- 5 `span-only` labels + 3 Tier-B + 2 Tier-A — half the misses are weak
  or suspect labels, not proposable structures.
- 9 clean misses: mostly micro steps under congestion where defences
  never reach 2 before the span, or price never re-approaches within
  1.75 ABR inside the golden span. The `formation_mid` route in
  production (cluster of micro pivots) may cover these — worth keeping
  alongside the defended-origin route.

## Post-ledger addendum (R25/R27, measured 22:4xZ)

Under `salience.fam_ledger` the MINI picture changes structurally:
MINI_LEVEL has **no `fam_rate_*` entry**, so the per-family ledger
gives it share 0 — every non-continuation MINI candidate is
`rate_limited` at every tick (EVAL-AUDIT caveat 1, VERIFY_LOG
22:41Z).  Consequences:

- `def_mini_off` is **redundant** while `fam_ledger` is on — MINI
  births/panel is 0.00 under arm (b) and arm (c) alike.  The defended
  MINI suppression that defined "v2" is subsumed by the ledger.
- The 2 MINI golden hits under arm (c) come from LC-typed objects
  (`9.4a#2` defended_origin, `9.38c#2` broken_line_edge) — the family
  match absorbs them, exactly as the type-emission caveat predicted.
- If MINI is ever wanted under the ledger it needs a
  `fam_rate_mini_level` entry (share 1 would restore the 584c7743
  birth mix) — a build-lane param decision, not a levels.py one.
