# ROUND_L10 — v2: flag ON with defended MINIs OFF (R24 §24.2)

Engine `a9d6af1c6eb3088c` (one hash, both arms one process), ruler
eval_v2 `50e11fd5`, 198 TUNE panels.  v2 = `level.defended_origin=true`
+ `level.def_mini_off=true` — defended LC births only; MINI-destined
triggers are skipped at typing (a young origin can still birth later
as LC once `age > def_mini_max_age_min`).

## Result table (v2 vs flag_off; flag_on from ROUND_L9 for contrast)

| metric | flag_off | flag_on (L9) | v2 |
|---|---|---|---|
| LC born recall | .146 (7/48) | .229 (11/48) | **.167 (8/48)** |
| LC trusted | .150 | .250 | .175 (7/40) |
| LC snapshot @τ | .021 | .106 | .085 (4/47) |
| LC recall@1 | .021 | .085 | .064 |
| LC recall@2 | .021 | .106 | .085 |
| LC recall@3 | .021 | .106 | .085 |
| MINI born recall | .065 (2/31) | .065 | .065 (2/31) |
| MINI snapshot | 0 | 0 | 0 |
| LC births/panel | 0.98 | 1.03 | 1.01 |
| MINI births/panel | 0.04 | 0.07 | 0.01 |
| all births/panel (med) | 6.0 | 6.5 | 6.0 |
| clutter ratio (med) | 2.50 | 2.50 | 2.50 |
| live levels @τ (med) | 0.0 | 0.0 | 0.0 |
| flicker (med, ch/h) | 0.33 | 0.43 | **0.33** |

Defended funnel (v2): 283,638 proposed → **88 born**;
suppressed_budget 114,931; rate_limited 2,268; expired 1,991;
outranked 286; nms 7.

## Keep-rule verdict — **FAILS, on a different family**

| family | off→v2 hits | delta |
|---|---|---|
| LEVEL_CARRIED | 7→8 | +1 |
| MINI_LEVEL | 2→2 | 0 |
| BOX | 6→7 | **+1 (healed)** |
| BRACKET | 25→28 | +3 |
| PATTERN_LINE | 19→17 | **−2 ← loses >1** |
| others | — | 0 |

The BOX loss is healed (removing 201 zero-hit MINI births freed the
ledger).  But the same mechanism bites PATTERN_LINE: on 9.27c and
9.46b a defended LC birth inside/near the golden line span displaced
the matching PL proposal (PL `rate_limited` 10→12 on 9.27c; a BRACKET
took the birth slot on 9.46b).  Root cause unchanged: defended births
spend the shared `rate_total` ledger — the victim family moved, the
mechanism did not.  Fix is REQ-L3 option 1, specced in REQUESTS.md
(salience.py is build lane's file per R24 §24.4).

## Why LC recall fell vs flag_on (.229 → .167)

V6 finding confirmed at engine level: the family match is
type-agnostic — under flag_on, defended MINIs at right prices counted
as LC hits.  Of flag_on's 11 LC hits, ~3 were carried by MINI-typed
defended objects at young origins; v2 removes them.  So the defended
MINIs were not entirely wasted ink — they held ~3 LC hits — but they
cost more (BOX −2, flicker +0.10) than they earned.

## Bootstrap CIs (paired day-level, v2 − off)

- LC born recall: **+.025 [−.081, .136]** over 33 days — weak evidence.
- LC recall@2: **+.073 [0.000, .167]** over 32 days — CI touches 0,
  weak/borderline.
- MINI born / recall@2: 0.000 (no defended MINIs; identical arms).

## Identity check (R23 §23.4) — PASS

flag OFF @`a9d6af1c` vs STABLE `584c7743` default (cached marker_off
pickles): canonical objects + cand_log + bars compared on all 198 TUNE
panels — **198 identical, 0 different, 0 missing** (identity_check.py).
Flagged code adds zero behavior at defaults.

## Scoreboard

Both rows appended in one invocation at `a9d6af1c` (R24 §24.3):
`--lane levellab --variant flag_off` / `v2`.  (Scoreboard's own
measure counts LC .12→.15, PL .10→.09, BOX .06→.06, clutter 10→11,
snap .10→.10 — same directions as this table modulo counting
conventions.)

## Verdict

v2 heals BOX and removes the flicker cost, but does not satisfy the
keep-rule (PATTERN_LINE −2, same ledger mechanism) and gives back most
of flag_on's LC gain (.167 vs .229) because defended MINIs were
carrying LC hits through the family match.  Flag stays OFF.  The lever
ordering for the Owner is now: flag_on (max recall, BOX −2) > v2
(BOX-safe, PL −2, smaller gain) > v3-spec (needs build lane's
salience.py one-line `cont` extension; predicted to keep v2's recall
while healing PL).

## Addendum — per-golden anatomy + churn under v2

Gained under v2 (8): LC 9.33c#0 (theta2, n_def=17), 9.39b#2 (asia,
n_def=18), 9.40c#1 (theta1, n_def=16) — all heavily-defended origins
re-approached, the intended grammar; BOX 9.39a#0 (slot freed);
BRACKET x4 incidental birth-order shifts.

Lost under v2 (5): PL 9.27c#0 + 9.46b#0 (rate_total displacement,
verified in cand_log); LC 9.3c#0 — under flag_on it was matched by a
`broken_box_edge_up` level whose birth was displaced by a defended
birth under v2 (same ledger, reverse direction); LC 9.32b#0 — was a
defended-MINI-carried hit under flag_on, removed by mini_off; BRACKET
9.65c#0 incidental.

Churn counts (defended objects, all events): flag_on 262 born (201
MINI + 61 LC), ~313 supersession closes, traversed 328, price_left
574, stale 162, revives 756, reprices 7004 (reprice fires every bar
price sits in-band — the 'proposed' log volume driver).  v2: 88 born
(LC only), ~186 supersession closes, traversed 124, price_left 142,
stale 28, revives 266, reprices 1142.  Flicker .33 = flag_off: the
flag_on flicker premium (+0.10 ch/h) was entirely MINI churn.
