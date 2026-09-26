# ROUND_L11 — v2b: defended births all typed LEVEL_CARRIED (post-L10 variant)

Motivation: v2 (mini_off) showed flag_on's extra LC hits were carried
by MINI-typed defended objects through the type-agnostic family match.
v2b keeps those young-origin births but types them LC — consolidating
all defended ink on the 2-live LC budget instead of a separate MINI
slot.  Flag: `level.def_all_lc` (default false).  Arms run in one
process at engine `a62edc19` (both scoreboard rows carry this hash;
R24 §24.3), ruler `50e11fd5`, 198 TUNE.

## Result (v2b vs flag_off)

| metric | flag_off | flag_on (L9) | v2 (L10) | **v2b** |
|---|---|---|---|---|
| LC born recall | .146 (7/48) | .229 | .167 | .146 (7/48) |
| LC trusted | .150 | .250 | .175 | .175 (7/40) |
| LC snapshot @τ | .021 | .106 | .085 | .085 (4/47) |
| LC recall@2 | .021 | .106 | .085 | .085 |
| MINI born recall | .065 (2/31) | .065 | .065 | **.097 (3/31)** |
| LC births/panel | 0.98 | 1.03 | 1.01 | 1.03 |
| MINI births/panel | 0.04 | 0.07 | 0.01 | 0.01 |
| all births/panel (med) | 6.0 | 6.5 | 6.0 | 7.0 |
| clutter ratio (med) | 2.50 | 2.50 | 2.50 | 2.50 |
| live levels @τ (med) | 0.0 | 0.0 | 0.0 | 0.0 |
| flicker (med, ch/h) | 0.33 | 0.43 | 0.33 | 0.33 |

Defended funnel (v2b): 300,745 proposed → **310 born** (all LC);
suppressed_budget 131,370; rate_limited 2,488; expired 2,355;
outranked 155.

## Keep-rule (R18 §18.1) — **NOT KEPT (Lead Ruling 26 §26.1)**

- No family loses more than 1 matched object: BOX −1, PATTERN_LINE −1,
  RANGE_OPEN −1, MINI +1, all others 0.  First variant to satisfy this.
- But the rule's other two legs fail on the one-hash scoreboard rows:
  **recall** — aggregate cumulative recall is net −2 objects (LC flat
  7→7); **ink** — live clutter at τ 10 → 11.
- The LC snapshot gain (.021 → .085) is real but is reported under
  recall@k, not as a keep.  v2b goes into the lever table as measured.
  *(Correction: an earlier draft of this section called the verdict a
  "marginal pass"; R26 §26.1 ruled it not kept.)*

## CIs (paired day-bootstrap, v2b − off)

- LC born: +.004 [−.096, .100] 33d — weak.
- MINI born: +.062 [−.042, .208] 24d — weak.
- LC recall@2: +.061 [−.006, .150] 32d — weak.
- MINI recall@2: 0.

## Reading the three arms together

- flag_on: biggest LC gain (+4) but BOX −2, flicker +0.10.
- v2: BOX-safe and flicker-free, but LC only +1 and PL −2.
- v2b: no family loses >1 (the only variant), recall gain is
  MINI/snapshot-shaped not LC-born, +1 all-objects ink, flicker flat.

The shared-`rate_total` bleed persists under every flag-ON variant —
it just moves victims (BOX under flag_on, PL under v2, spread −1s
under v2b).  REQ-L3 option 1 (exempt defended births from the joint
counter inside `salience.py`, build lane) remains the real fix; spec
in REQUESTS.md.

## Scoreboard

`--lane levellab --variant flag_off|v2b` appended in one invocation at
`a62edc19` (sb_pair.py).  Scoreboard conventions: BOX .06→.05,
PL .10→.10, LC .12→.12, clutter 10→11, snap .10→.10.

## Addendum — per-golden matrix (level goldens that differ across arms)

off -> flag_on -> v2 -> v2b (matched engine object type):

| golden | gold | off | flag_on | v2 | v2b |
|---|---|---|---|---|---|
| 9.14c#0 | MINI | LC | – | LC | – |
| 9.32b#0 | LC | LC | MINI | – | – |
| 9.33c#0 | LC | – | – | LC | – |
| 9.36b#3 | MINI | – | – | – | LC |
| 9.39b#2 | LC | – | LC | LC | – |
| 9.3c#0 | LC | LC | LC | – | – |
| 9.40c#1 | LC | – | LC | LC | LC |
| 9.48c#2 | LC | – | – | – | LC |
| 9.4a#2 | MINI | – | LC | – | – |
| 9.51b#2 | MINI | – | – | – | LC |
| 9.57b#3 | LC | LC | LC | LC | – |
| 9.57b#4 | LC | – | – | – | LC |
| 9.57c#0 | LC | LC | LC | LC | – |
| 9.59a#2 | LC | – | LC | – | LC |
| 9.66c#1 | LC | – | MINI | – | – |

Reading: v2b's flat LC headline masks churn — it *loses* hits that even
flag_off held (9.57b#3, 9.57c#0: all-LC budget thrash displaced stable
levels) while winning a different set (9.36b#3, 9.48c#2, 9.51b#2,
9.57b#4 — young-origin LC-typed objects hitting both LC and MINI
goldens).  The 2-live budget under heavier competition no longer
preserves the matched set.

Day-level LC@2 drivers (v2 − off): +1.0 on 04-16, +1.0 on 04-24,
+.33 on 04-25 — the whole signal rests on ~3 days.  v2b drivers:
+.67 04-25, +.50 05-22, +1.0 05-24, −.20 05-18.  Sparse day-level
signal is why every CI includes 0 — honest weak evidence, not noise
in the harness.

Scoreboard one-hash lever table now complete at `a62edc19`:
flag_off / flag_on / v2 / v2b all appended (R24 §24.3 compliant).

## Addendum 2 — why v2b loses stable hits; v2c negative control

v2b losses are budget thrash, measured per-object: 9.57b#4's matching
level (born b150 @12688.7 vs golden 12690) was superseded by a def=12
challenger at b151, revived, superseded again at b152 — 2 evictions in
2 bars.  9.57c: 288 proposals near the golden price, 0 born, 222
suppressed_budget — under all-LC typing the young-origin proposals
lose the 2-slot competition to mature heavy origins (score =
n_def − dist + ret24 favors them); under flag_on/v2 they lived in the
separate MINI slot.

v2c negative control (all_lc + level_max_live=3): **worse** — LC born
.125, BRACKET −3, PL −2, clutter 2.67.  Extra live slots spend more
rate_total, so collateral grows; the thrash is ordering-driven, not
capacity-driven.  Budget 2 stays optimal; not adopted (no param added).

Minor hygiene note: defended objects can log duplicate close events
(same bar, same reason — e.g. price_left twice); cosmetic, flag-path
only.

## Extended CIs (pooled, v2b − off)

- level-family born recall (LC+MINI pooled): **+.025 [−.059, .112]**
  over 46 days — weak.
- LC snapshot recall at τ (any live level matches): **+.061
  [−.006, .150]** over 32 days — weak/borderline.

Consistent picture: every v2b diff is weak; the only positive-CI
result anywhere in the flag family is flag_on LC born
+.071 [.010,.152].

## Addendum 3 — flicker tails + trusted flags on the moving set

Flicker distribution (changes/hour): off med .33 p90 .50 max .71;
flag_on .43/.57/.83; v2 .33/.50/.67; v2b .33/.50/.71 — the flag_on
premium is MINI churn only; both LC-only variants match off at every
quantile.

Tier flags on the moving set: every v2/v2b gain is a trusted label
(9.33c#0, 9.39b#2, 9.40c#1, 9.36b#3, 9.48c#2, 9.51b#2, 9.57b#4);
the only Tier-A member of the moving set is a *loss* (9.57b#3, lost
under v2b).  The defended route's wins are clean-label wins.

## Addendum 4 — measured negatives (both kept as flagged knobs, defaults safe)

- **v2d** (`all_lc` + `def_evict_margin=1.0`): LC born .125 (−1 vs v2b),
  PL −2 — hysteresis does not recover hits; the evictions that cost
  recall were by *substantially* stronger challengers (def=12 vs ~5),
  and suppressing legitimate evictions starves real births.
- **modal** (`def_price_mode="modal"`): LC born .208 vs flag_on .229 —
  the modal defence touch is *not* the author's anchor either; the
  residual 6 trusted misses (1.0–2.2p) are genuine sub-tolerance
  scatter, not a systematic edge-vs-mean bias.  Consistent with L4/L5
  where edge beat mean/median.  Param kept at `"edge"`.

Suite: 38/38 engine tests green; all five def_* flags default-safe
(defended_origin OFF / mini_off OFF / all_lc OFF / margin 0 / edge).

---
**Continued in ROUND_L12** — the R25 §25.5 zero-sum test: build lane's
`fam_ledger` + v2 config passes every keep-rule leg (LC .146->.229,
CIs positive, ink unchanged); EVAL-AUDIT confirmed directionally at
9283b389.  The residual bottleneck moved intra-family
(`rate_level_carried=1` per kind).
