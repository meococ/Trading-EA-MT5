# ROUND_L12 — the zero-sum test: per-family ledger + defended LC (R25 §25.5)

**Hash note:** arms were measured at `2795e5e0`; a later params-file
byte-encoding repair (literal UTF-8 → `\uXXXX` escapes, zero parsed-value
change) moved the live hash to `9283b389`.  Verified two ways: identity
check at `9283b389` vs `584c7743` is 198/198 identical (objects +
cand_log), and the full paired A/B re-run at `9283b389` reproduces every
number below exactly (LC born .229, keep-rule deltas identical, CIs
+.120/+.119).  Trusted-subset LC recall@k under (c): @1 .077, @2 **.154**
(default .026 at all k).

Build lane landed `salience.fam_ledger` (default OFF): the joint
`rate_total` pool is replaced by per-kind shares (PL 2, BOX 1, LC 1,
BRA 1 — largest-remainder of the `584c7743` birth mix).  A defended LC
birth draws on LEVEL_CARRIED's own share — it can no longer starve
BOX/PATTERN_LINE births.

Three arms, one invocation, one engine hash `2795e5e0`, ruler
`50e11fd5`, 198 TUNE:

- **(a) default** — shipped params
- **(b) ledger only** — `salience.fam_ledger=true`
- **(c) ledger + defended LC** — `fam_ledger` + `defended_origin` +
  `def_mini_off` (the v2 level config)

## Results

| metric | (a) default | (b) ledger | (c) ledger+v2 |
|---|---|---|---|
| LC born recall | .146 (7/48) | .125 (6/48) | **.229 (11/48)** |
| LC trusted born | .150 | .150 | **.275 (11/40)** |
| LC snapshot @τ | .021 | .021 | **.128** |
| LC recall@1 | .021 | .021 | .064 |
| LC recall@2 | .021 | .021 | **.128** |
| LC recall@3 | .021 | .021 | **.128** |
| MINI born recall | .065 | .032 | .065 |
| all births/panel (med) | 6.0 | 6.0 | 6.0 |
| clutter ratio (med) | 2.50 | 2.50 | 2.50 |
| live levels @τ (med) | 0.0 | 0.0 | 0.0 |
| flicker (med ch/h) | 0.33 | 0.33 | 0.33 |
| defended born | — | — | 165 |

## Keep-rule (R18)

**b − a:** BOX **−2** (loses >1), BRACKET +5, CL +1, CR −1, LC −1,
MINI −1 → ledger alone **FAILS** (it reallocates the birth mix; BOX's
old share of the joint pool was bigger than its new 1/72 share).

**c − a:** BRACKET +5†, CONTEXT_LINE +1, CONTEXT_RANGE −1,
**LEVEL_CARRIED +4** — BOX 0, PATTERN_LINE 0, MINI 0.  No family loses
more than 1.  Recall rises (+9/−1 aggregate), clutter ratio equal,
live@τ equal → **KEEP-RULE PASSES — the first defended-origin
configuration to satisfy every leg.**

† BRACKET deltas are an **upper bound** — the ruler's BRACKET rule
has no price check (R30 §30.3).  The +5 counts price-shifted
brackets that may not match the author's price.

Scoreboard rows at the same hash confirm: `famledger_v2` LC .21 vs
flag_off .12, BOX .06 = .06, PL .10 = .10, live clutter 10 = 10,
snap .10 → .11.

## CIs (paired day-bootstrap, vs default)

| diff | (b) ledger | (c) ledger+v2 |
|---|---|---|
| LC born | +.013 [−.096,.129] weak | **+.120 [.009,.242] POSITIVE** |
| LC@2 | +.004 [−.019,.031] weak | **+.119 [.021,.233] POSITIVE** |

## Interpretation — narrowed by R29 §29.2

**Pack wording (verbatim): "famledger v1 + defended LC: keep-rule
pass on born recall (verified); four kinds silenced (defect); no
gain at the author's budget"** — a direction, not a result.

Under the shared ledger every defended gain displaced a BOX or
PATTERN_LINE birth; under per-family shares the defended route keeps
its full flag_on-era born recall (LC .229) while no family loses
more than one.  But three famledger-v1 defects bound the claim:

1. zero-share kinds are silenced (MINI/CR/CL/SQUEEZE non-cont cands
   can never birth — `def_mini_off` is redundant under the flag);
2. shared live budget / NMS / bar timing still couple families
   (my scheduling-leak finding — §"why (b) loses 2 BOX" — is the
   same coupling EVAL-AUDIT named);
3. continuation routes bypass the ledger.

And at the **author's budget under the engine's top-k ranker** (not
my lab ranker), (c) is flat: .006/.025/.088 at k=1/2/5 vs base
.01/.01/.07 — the born-recall gain does not currently surface as
live-at-τ advantage under engine ordering.  My @k/snapshot figures
are lab-ranker readings, labelled as such.

Notable mechanism detail: defended births under (c) = 165 vs v2's 88 —
under the joint pool defended proposals were ALSO losing to
`rate_total` competition from other families; the per-family share
lets LC's own 1/72 flow through.

Caveats for the pack: (b) alone shows the ledger is not neutral for
BOX (−2) — turning it on by default needs its own keep-rule review;
the (c) config that passes keeps BOTH flags off at defaults.

## Hit-composition anatomy (flag_on vs arm c)

Same .229 LC born recall, **different set.**  Under flag_on the LC
hits were a mix — several contested panels were actually hit by
`broken_box_edge_up`/`broken_line_edge` objects and defended
MINI_LEVELs.  Under (c) every surviving LC hit is `defended_origin`:

- c gains 5 goldens flag_on never hit: `9.48c#2, 9.49a#0, 9.51a#1,
  9.57b#4, 9.60b#0` — the freed LC share lets defended births through
  that used to lose the joint pool.
- c loses 4 hits flag_on had via external emitters: `9.3c#0,
  9.57b#3, 9.57c#0` (`broken_box_edge_up`), `9.59a#2`
  (`broken_line_edge`) — these now compete with defended births for
  the same LC share of 1 per window.

So the ledger removes **cross-family** zero-sum but introduces
**intra-family** competition between defended-origin and
broken-edge emitters inside LEVEL_CARRIED's own share.  The 1-slot
LC share is the next selection bottleneck if both emitters stay on.

Per-golden decomposition of the 4 losses (cand_log audit): it is
**double jeopardy**, not share-loss alone.  On all four panels the
external emitter's candidate was `rate_limited` by the LC share
(e.g. `9.57b`: `broken_box_edge_up` score 13.16 rate_limited), AND
same-price `defended_origin` proposals sat at `proposed`/
`suppressed_budget` — the local 2-LC live budget rejected them
because two other defended LCs were live.  The generator reached
all four prices; both selection layers said no.  If the route is
ever promoted, raising `def_level_max_live` or exempting
external-emitter LC births from the defended budget are the two
levers that reach these goldens.

## Why (b) loses 2 BOX but (c) loses none — the leak is scheduling, not counters

(For EVAL-AUDIT's §27.2.2 verification question — evidence from
cand_log, measured on the same runs.)

BOX golden diffs (b/c vs a): `9.2b#3` and `9.45b#0` are lost under
**both** b and c — pure share reallocation (BOX share 1/72 < its old
joint-pool share); their cand_logs are identical between b and c.
The interesting pair:

- `9.40c#2` (hit under a, missed under b, hit under c): under (b) a
  BOX births at cet 590; the golden-matching candidate
  `[13213.1,13225.2]` at cet 945 lands inside its 72-bar rate window
  → `rate_limited`; the box that does get born (cet 995,
  `[13195.4,13225.4]`) has wrong geometry.  Under (c) the same box
  births at cet 605 → its window ends 965 → the right-geometry cand
  births exactly at cet 965 → **hit**.
- `9.7b#0` (missed under a and b, hit under c): same pattern — the
  earlier BOX birth shifts 485 → 475 and a second BOX births at 835.

So the family budgets ARE separate in accounting — a defended LC
birth never touches `fam_rate_box`.  The residual coupling is
**bar-level scheduling**: defended proposals change the pending /
outrank mix on each bar, which shifts other families' birth times
by a few bars, which slides the 72-bar rate windows, which flips
whichever borderline candidate sits at the window edge.  Deterministic
but chaotic — equal-probability gain/loss per boundary candidate.
Here it happened to recover one BOX and gain another.

## What remains: the LC share itself (48 LC goldens under arm c)

11 hit / 33 covered-but-unhit / 4 no-proposal.  Dominant killer of
the 33 covered-unhit goldens (nearest right-price defended proposal):

| killer | n | meaning |
|---|---|---|
| `rate_limited` | **19** | the day's LC share (1/72) was already spent on a different LC-family birth — intra-family contention, the residual bottleneck |
| `suppressed_budget` | 6 | local 2-LC live budget full with wrong-price defended objects |
| `proposed_only` | 4 | proposed but never reached a born decision |
| born but unmatched | 4 | a defended object WAS born within 2.5 p — timing/geometry miss (e.g. `9.52a#1` born 12932.5 vs golden 12932, off-window) |
| NO-PROPOSAL | 4 | generator floor: `9.17b#3, 9.18c#0, 9.63a#1, 9.65a#0` |

So after the ledger fix the chain reads: **coverage solved**
(44/48 proposals within 2.5 p) → **the next selection bottleneck is
intra-family**: the LC kind is capped at 1 birth per 72-bar window —
`rate_level_carried=1` binds first (per-kind cap, applies to every
candidate including continuations; salience.py:483), with
`fam_rate_level_carried=1` as the second layer.  The day's LC slot
gets spent on an earlier/different-price birth while the
golden-adjacent proposal waits.  Candidate levers (all need Lead
ruling + paired A/B): `rate_level_carried` 1→2 (measured below —
costs ink), intra-LC ranking by golden-proximity features, or
exempting external-emitter LC births from the defended budget's
occupancy.

## Ceiling test: the second LC slot has a measured price (arm d)

Correction to the lever name: the binding cap is the **per-kind**
`rate_level_carried=1` (salience.py:483 binds every candidate,
continuations included), with `fam_rate_level_carried` second.
Raising only `fam_rate_level_carried` to 2 changed literally nothing
(bit-identical run).  Arm **d2** = (c) + `rate_level_carried=2` +
`fam_rate_level_carried=2`:

| | (c) | (d2) |
|---|---|---|
| LC born recall | .229 | **.292** (14/48) |
| trusted LC born | .275 | **.350** |
| LC@2 | .128 | **.170** (tr .205) |
| LC snapshot | .128 | .170 |
| keep-rule families | pass | pass (worst −1: BOX, PL, CR) |
| births/panel | 6.0 | **7.0** |
| clutter ratio | 2.50 | **3.00** |
| live@τ med | 0.0 | **1.0** |
| flicker med | .33 | **.67 ch/h** |
| LC born CI | +.120 [.009,.242] | **+.181 [.049,.323]** |

Verdict: the second LC slot buys +3 matched goldens (and stronger
CIs) at +1 object/panel, +0.5 clutter ratio, live@τ 0→1, and doubled
flicker — **the ink leg of R18 fails**, so d2 is a priced trade for
the Owner, not a free keep.  The middle 19 `rate_limited` goldens
are thus reachable only by spending ink the author doesn't spend,
or by ranking the same single slot better (the remaining
proposal-precision problem).

## Independent verification (EVAL-AUDIT, R27 §27.2, 22:41Z @9283b389)

**CONFIRMED with caveats.**  Their own `arm_ab.py` re-run reproduces
the keep-rule pass directionally: LC .12→.21 (+4), BOX net 0, PL 0 —
same direction as this document's .146→.229 at `2795e5e0`.

Caveats they logged, all consistent with the mechanisms above:

1. **The ledger is not fully per-family.**  Kinds without a
   `fam_rate_*` entry get share 0 — non-continuation CONTEXT_LINE /
   CONTEXT_RANGE / MINI_LEVEL / SQUEEZE candidates are `rate_limited`
   at every tick.  **Correction to my earlier attribution:** MINI
   births/panel = 0.00 under arms (b) and (c) alike — the zero share
   does it, `def_mini_off` is redundant while `fam_ledger` is on.
2. **Residual coupling confirmed.**  Shared live budget + shared NMS
   + continuation-route bypass mean "(c) loses no BOX" is partly
   boundary luck via shared channels — same conclusion as the
   scheduling-leak section above, independently reached.
3. **Snapshot/recall@k magnitudes differ by convention.**  Their
   engine-ranker at τ (object score / born score / recency) gives
   LC snapshot .065 and LC@k≈0 at k≤3; my numbers (.128, @2 .128)
   use the lab ranker (cand_log birth score, level objects only).
   Keep-rule claim is convention-free and confirmed by both; the
   @k/snapshot magnitudes are lab-ranker readings — the pack should
   quote EVAL-AUDIT's engine-convention numbers where they differ.

## Defended-route lifecycle (198 TUNE, object events)

| | v2 (shared pool) | flag_on | (c) fam_ledger+v2 |
|---|---|---|---|
| defended born | 88 LC | 262 (61 LC + 201 MINI) | **165 LC** |
| superseded | 186 | 313 | 313 |
| reprice | 1,142 | 7,004 | 2,059 |
| revive | 266 | 756 | 414 |
| outranked | 2 | 125 | 10 |
| end-state ACTIVE | 9 | 31 | 20 |

Two mechanisms visible:

1. **The LC share is reserved, not just capped.**  `fam_rate_level_
   carried=1/72` is smaller than `rate_total=5/72`, yet defended LC
   births rise 88 -> 165: under the joint pool defended proposals
   arrived to find the pool already spent by BOX/PATTERN_LINE births;
   under the ledger the LC share cannot be poached.  `outranked`
   collapses 125 -> 10 for the same reason.
2. **Churn is internal, not visible ink.**  313 supersessions + 414
   revives + 2,059 reprices under (c), yet panel-level flicker stays
   .33 ch/h — supersede/revive pairs keep the live *price* set stable
   (a revived same-price level is not a flicker event).  The author's
   flicker measure counts set changes, not lifecycle events.

