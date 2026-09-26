# DR-MARK — The Essence of a Pro's Event Marks

Deep-research lane, 23/09 (R73 §73.4, resumed under R75 §75.7).
Third and last essence note: the event grammar that sits **on** the
structure (BRACKET, LABEL_TF T/F, SQUEEZE, FALSE_EXT).  Boxes, lines
and levels answer "where is the structure"; marks answer "what just
happened there".

Method identical to DR-BOX / DR-LINE: essence first (E1), causal
definitions (E2), read-only measurements (E3), proposals only (E4-E5).
No engine, ruler, fixture or threshold was touched.  Log:
`DR_MARK_LOG.md`.  Scripts and JSONL: `DR_MARK_{fidelity,consistency,
validity}.{py,jsonl}`.

---

## E1 — First principles, per mark type

### E1.0 The shared grammar

Every professional source — Volman's casebook, Brooks, Wyckoff, AMT,
Edwards & Magee — treats these marks as **verdicts on an auction at a
reference**, never as free-standing patterns.  Three primitives recur:

1. **A reference must already exist.**  A poke is meaningless mid-air.
   Every mark is relative to an established edge: a drawn box edge, a
   line, a level, a session extreme.  The mark records what the market
   *did to* that reference.
2. **The event is the resolution of a probe, not the probe itself.**
   A wick through the edge is only a question.  The answer — accepted
   or refused — arrives when the bar closes back inside (tease), when
   the close-through fails (false break), or when the excursion is
   abandoned (failed auction).  Knowability is the resolution bar, not
   the extreme bar.
3. **Marks are information, not signals.**  Volman is explicit:
   "T and F are information only; the eventual break came after both"
   (lesson 9.20a).  The mark compresses a multi-bar argument into one
   letter so the *next* decision reads faster.

### E1.1 LABEL_TF — tease vs false

**T (tease).**  A shallow wick through a defended edge that closes back
inside.  Volman: "pokes of a few pips during a flat EMA are teases"
(9.45a).  What it means: the poking side *probed* the level and found
it held — for now.  Repeated teases are the signature of pressure
building at a wall: "several teases below a range floor precede the
real break" (9.50b); "two teases below the neckline come before the
real break" (9.15a).  A tease is evidence of *intent*, not failure —
the author marks each tease even when the break later succeeds.

**F (false).**  A break attempt that failed: either a wick-poke whose
rejection was forceful (price visibly driven back across the box), or
a genuine close-through that re-entered.  "a break with no build-up is
labelled false even though it ran well above the box" (9.8b) — the
verdict attaches to the *failure*, not to the excursion's size.  The
microstructure: a failed break traps the breakout side (Wyckoff's
spring/upthrust; AMT's failed auction), and their covering fuels the
counter-move: "the failed upside poke fuels the downside break" (9.13a);
"once a false break has tagged the magnets behind the entry, they no
longer block it" (9.50c).

**For/against.**  For: Osler (2003) shows stop orders cluster just
beyond round numbers and their execution produces the rapid move —
the F mechanism is real market plumbing; Brooks: ~80% of range
breakouts fail and "the best failed breakouts happen when 5 or fewer
bars have traded outside"; Wyckoff grades springs by penetration depth
and recovery speed.  Against: the same sources stress the label is
earned in hindsight — an undercut that keeps falling was "simply a
breakdown"; a failed failure is itself a strong continuation signal
(Brooks).  So F is a *verdict on what already happened*, not a
prediction — its value is structural (the edge was attacked and held),
not prophetic.

### E1.2 BRACKET — the middle section of a reversal formation

Volman's M/W/Mm/Ww/SHS mark the *time span* of a double-extreme-plus-
middle formation: two tests of roughly the same price with a real
interim dip between them.  Edwards & Magee's double top/bottom and
head-and-shoulders, compressed to M5 scale (sep 4–40 bars, equality
≈ max(3p, 0.5·ABR)).

What it means: one side pushed to an extreme, failed to continue, was
driven back (the middle), and the *second* push failed at the same
price — the second failure is the information.  "a W on a round number
stops the follow-through short" (9.13b).  But the bracket alone is not
a trade: "a W bottom is recognised early, but no long is taken until
the turn has happened" (9.24c); "an incomplete W middle section is not
yet a reason to exit" (9.4a).  The middle section is the *trigger* —
its price becomes a level (the engine already spawns `formation_mid`
mini-levels, patterns.py:223-225).  Alternating M/W = range, no trade
(9.43a) — brackets also describe *absence* of directional resolution.

**For/against.**  For: Chang & Osler (1999) found H&S profitable in FX
(though dominated by simpler rules); Lo–Mamaysky–Wang (2000) showed
patterns carry incremental information at matched scales.  Against:
pattern fidelity to one author's eyeball is bounded (DR-BOX ceiling
~30%; DR-LINE: proposal-flood-bound).  The honest reading: brackets
encode *where the fight is*, and the useful part is the level it
produces (the middle), not the letter.

### E1.3 SQUEEZE — compression between two walls

A dashed ellipse around 2–8 small bars trapped between two converging
walls (line, level, box edge, or EMA25).  "a box teased on both sides
breaks out of its small inner squeeze in the direction of the
prevailing pressure" (9.6a); "a thin squeeze makes the entry bold"
(9.21a); the squeeze must be a clean wedge (9.63b).

What it means: **balance before imbalance** — AMT's equilibrium inside
a narrowing corridor; Bollinger's squeeze claim (bandwidth compression
precedes expansion); the volatility-clustering literature gives the
deep basis (low-vol regimes persist then revert).  Crucially the
squeeze predicts *expansion*, not *direction* — direction comes from
prevailing pressure (9.6a) or which wall fails first.

**For/against.**  For: volatility clustering is one of the most robust
stylised facts in finance.  Against: the practitioner's "squeeze
breakout" edge is weak-to-absent once costs and multiple testing are
counted (Park & Irwin survey); and with n=2 golden squeezes on TUNE,
fidelity there is descriptive only.

### E1.4 FALSE_EXT — the failed extreme

A short tick at a bar whose excursion beyond the previous extreme was
refused: spec §3.9's three-bar signature (up-break of the prior bar's
high, bearish reply, reply's low broken).  "a signal bar that spikes
above the M highs and closes down is a false high, which strengthens
the short" (9.3a); "repeated false highs at EMA25 set up the entries"
(9.2b); "a false high at a pullback top is where pbp/pr trigger"
(9.56b); "a Ww with a false low ends the down-move" (9.16c).

What it means: the smallest footprint of a trapped-trader event — a
single-bar stop run whose failure is confirmed by the next bar's
reversal through the reply bar's opposite extreme.  It is Wyckoff's
spring/upthrust and AMT's *excess* at bar scale.

**Representation gap.**  The golden TUNE set contains **zero**
normalized `FALSE_EXT` objects — the author encodes false highs/lows
in free text and ARROW marks, not as object records.  The engine
computes the signature as a `bar_facts` entry (engine.py:696-703) but
no object channel emits it; render.py:137 knows how to draw it.
So FALSE_EXT is today a *detected fact without ink* — the report
treats it as a proposed object, not a fidelity target.

### E1.5 The essence, compressed

A professional's event marks answer one question at each defended
price: **"the attack on this edge — did it probe (T), fail visibly
(F), compress (SQUEEZE), get refused at the extreme (FALSE_EXT), or
complete a reversal formation (BRACKET)?"**  The marks exist because
the *next* event at the same edge will be read through them.  They are
the chart's working memory of who tried what, and who is trapped.

---

## E2 — Causal, measurable definitions

Common normalisation: `tol = max(1.0 pip, 0.25·ABR)`, `ABR` = mean
range of last 50 closed M5 bars (spec §3.1).  All events use only bars
≤ the decision bar; ink positions may be back-dated to the excursion
bar (placement ≠ knowledge — same convention as box build windows).

| mark | becomes knowable at | trigger (causal) | principle-fixed | arbitrary (standardise) |
|---|---|---|---|---|
| **T** | close of the poke bar | `h > edge + tol` and `c <= edge` (above), mirror below; poke side | needs a live defended edge; wick beyond tol; close inside | depth cap `max(1.5·ABR, 2p)` — a deeper tease is still a tease; dedup one-per-excursion |
| **F (direct)** | the re-entry bar | close beyond edge > tol at bar j, then close inside at j+k | failure = re-entry after a *close* through | pending window (engine: next bar); F position drawn on the excursion bar, not the resolution bar |
| **F (relabel)** | the relabel bar | T exists, then within `tf_relabel_bars` (3) close moved `>= 0.5·hgt` the other way while still inside | escalation requires a *sized* counter-move | 0.5·hgt / 3 bars are author-eyeball constants — fix by ABR not box height? (proposal) |
| **BRACKET** | confirmation bar of the 2nd equal pivot | two same-side pivots within `max(3p, 0.5·ABR)`, sep 4–40 bars, interim opposite pivot with dip `>= 0.5·ABR` | pair equality + intervening real middle | eq tolerance, sep band, mid depth are author-scale constants — defensible |
| **Mm/Ww** | same | same + minor (theta1) inner turn | "smaller middle" | floor_struct comparison |
| **SHS** | confirmation of 2nd shoulder | chain s1 n1 h n2 s2 on structural stream; shoulders within 0.6·ABR; head `>= 1.0·ABR` | head must exceed shoulders | tolerances |
| **SQUEEZE** | last qualifying bar's close | `>=3` consecutive bars each `<= 0.8·ABR`; two live walls within `2·ABR` straddling price; gap_now `<= 0.6·gap` at span start; walls cross within 15 bars | compression *between named walls* (a quiet patch alone is not a squeeze) | min_bars (spec allows 2–8), shrink fraction, apex window |
| **FALSE_EXT** | the bar that breaks the reply bar's opposite extreme | b1 breaks b0's extreme; b1 reverses (c<o for high); b2 breaks b1's low | three-bar refusal signature | none — fully determined by spec §3.9 |

Subjective choices the principle fixes: the *reference* (edge must be
live and defended), the *resolution* (close-back-inside vs close-
through), the *convergence* (two named walls for a squeeze).  What
remains arbitrary: poke-depth caps, relabel fractions, letter equality
tolerances — all expressible in ABR and should stay so.

---

## E3 — Measurements (read-only)

### E3a Fidelity on TUNE (ruler = evalcheck/eval_v2.py imported via
`funnel.funnel_panel`; golden = scorable subset)

Golden density first — the author's marks are *sparse*: median 0
LABEL_TF per panel (158/198 panels have none; mean 0.30), median 0
BRACKETs (128/198 none; mean 0.43), 2 SQUEEZE total, 0 FALSE_EXT
objects.  The mark grammar fires roughly once every 2-3 panels — any
engine producing marks faster is over-dense by construction.

| family | golden | engine born (in-window) | matched | recall | precision | misses |
|---|---|---|---|---|---|---|
| BRACKET | 85 | 296 | 33 | **0.388** | 0.111 | wrong_geometry 32, not_born 20, never_proposed **0** |
| LABEL_TF | 60 (55 T / 5 F) | 77 | 7 | **0.117** | 0.091 | never_proposed 15, wrong_geometry 25, not_born 13 |
| SQUEEZE | 2 | 20 | 0 | 0.000 | 0.000 | wrong_geometry 1, never_proposed 1 |
| FALSE_EXT | 0 objects (28 untimed text refs) | 2814 bar_facts events | n/a | n/a | n/a | not a ruler family |

Density check: the engine births ~1.5 brackets and ~0.4 marks per
panel — brackets are ~3.5x over-dense, marks are at roughly the
author's *rate* but at the wrong edges (precision 9%).  The mark
problem is placement and host availability, not volume.

Reach funnel (cand_log outcomes, whole stream):

* BRACKET: 11,666 template instances proposed -> `vetoed_irrelevant`
  only **25** (the relevance gate is nearly free) -> expired 4,737 /
  rate_limited 4,415 / outranked 2,116 / nms 8 -> **born 365**.
  Legal-stream coverage is effectively 100% (zero never_proposed);
  the loss is selection under the shared rate window, then geometry.
* LABEL_TF: 1,892 -> expired 924 / rate_limited 607 -> born 361
  (~19%).  Born marks by parent: PATTERN_LINE 52, CONTEXT_LINE 21,
  BOX **4** — the author's marks sit mostly on box edges and old
  levels, but the engine's mark channel lives almost entirely on
  lines (they stay alive longest).  Letters born: T 73 / F 4;
  T->F relabels seen: 4 (lags 1-3 bars — the channel works, rarely).
* SQUEEZE: 225 -> born 68 (fam_capped 46) — proposed often, wrong
  places.

Nulls (LABEL_TF): cross-panel 3.4%, golden t+30min 2.0%, t+60min 0% —
the 11.7% real match is ~4-5x chance, so matched marks are real but
the absolute level is low.  BRACKET cross-panel null 14.3% vs 38.8%
real (~2.7x lift).

**Host-edge coverage (M9 diagnostic).**  Golden marks carry only
time + side (no price), so the poked level was proxied by the prior
12-bar extreme on the mark's side.  Of 23 timed+sided golden marks,
**11 (48%) had a live engine edge within 3 pips at mark time** — the
rest could never have been marked because no host edge existed at all
(the `never_proposed` mechanism; the proxy is a lower bound since the
author often references session-old levels).  Mark fidelity is bounded
above by structure recall *at the moment of the poke* — the deepest
finding of this lane.

FALSE_EXT: the engine's `bar_facts` fires ~14x/panel-day while the
author mentions false highs/lows ~28 times across the whole TUNE set,
always untimed and always attached to named structure ("false highs
in the squeeze", "false high at a pullback top").  Conclusion: the
author treats it as a *context verdict*, not a point object — the
2814-event signature stream is a detector, not a drawing.

### E3b Consistency

`DR_MARK_consistency.py` (research-only, same battery as
DR_LINE_consistency): base run hashed twice for determinism, then
start-shifts 1/2/3/5/10 bars, +-0.3-pip jitter seeds 1-3, and M15
resampling over all 198 TUNE panels.  Retention = per BASE engine mark,
a same-type/same-side mark within +-10 min (BRACKET/SQUEEZE also need
span coverage >= 0.3); letter flips counted separately.

**Determinism: 0/198 panels differ on identical re-run.**

Retention of base marks (kept / 298 BRACKET, 363 LABEL_TF, 20 SQUEEZE,
2814 FALSE_EXT base marks):

| family | jitter +-0.3p | shift1 | shift3 | shift5 | shift10 | M15 |
|---|---|---|---|---|---|---|
| BRACKET | .86-.91 | .94 | .86 | .81 | .78 | .55 |
| LABEL_TF | **.41-.51** | .77 | .54 | .44 | .27 | .08 |
| SQUEEZE | .65-.70 | .95 | .95 | .90 | .80 | .15 |
| FALSE_EXT (facts) | .91-.92 | 1.00 | 1.00 | 1.00 | 1.00 | .23 |

Letter flips among retained marks (T<->F, M<->W family):

| family | jitter | shift1 | shift10 | M15 |
|---|---|---|---|---|
| BRACKET | 27-37 | 24 | 79 (34% of kept) | 93 |
| LABEL_TF | 12-18 | 9 | 9 | 3 |

Churn (births+closes+relabels, mark kinds): median 0.33/h, p90 0.57/h
on base; identical under shift3/jitter1; lower on M15 (0.14/h — fewer
events exist at all).

Reading, per family:

* **LABEL_TF is the fragile mark** — a single-bar edge-poke predicate
  dies under a 0.3-pip tick perturbation half the time.  That is not
  engine flakiness so much as essence: a tease is defined by ~1-3 pips
  of poke depth, and half the drawn marks sit within noise of the
  depth gate.  The 10-bar start shift retains only 27% — a mark's
  existence depends on whether its *host edge* was discovered in time,
  tying mark stability to structure warm-up.
* **BRACKET spans are stable, letters are not.**  Span retention is
  .78-.94 under shifts/jitter, but up to a third of retained brackets
  flip letter family (M<->W) under noise — the equality tolerance
  (3p / 0.5*ABR) is thin relative to the perturbation, and which of
  the two extremes reads "higher" swaps.  The *event* (repeated
  rejection of a level) is robust; the *letter* is the fragile part.
* **SQUEEZE** survives shifts (.80-.95) — runs of small bars are a
  regional property — but jitter kills a third (bars near the 0.8*ABR
  line flip) and M15 destroys it (.15): 3-bar groups rarely stay
  "small" after aggregation.
* **FALSE_EXT facts are perfectly stable under shifts (1.00)** — a
  3-bar local pattern does not care where the feed started — and
  .91-.92 under jitter.  M15 keeps only .23 (the undercut leg usually
  merges into the extreme bar's range).
* **M15 resampling is a different chart** — retention .08-.55 across
  families.  Marks are M5-native ink; reporting M15 retention as a
  failure would be wrong — it is a boundary statement, not a defect.
* **Churn is low** (0.33 events/h median): the mark layer is not
  flicker-prone per se; its instability is *existence* (edge
  discovery + thin tolerances), not birth/death cycling.

### E3c Validity on DESIGN 2016-2021

Pre-registered 06:23Z in DR_MARK_LOG.md; detectors replayed causally
on the engine's pivot stream (`DR_MARK_validity.py`), 623 days
(every 3rd `day_list()` entry), 194,704 events:
POKE 26,286 / FBREAK 11,020 / BRACKET 111,155 (loose unfiltered
detector — every equal pivot pair; the engine's own bracket pipeline
is stricter) / FX 24,606 / SQUEEZE 3,466 / CTRL_POKE 1,232 /
CTRL_FX 11,418 / CTRL_QUIET 2,998 / CTRL_SWING 2,523.

**Mechanical-bias caveat (stated before reading):** the first
+-0.5*ABR-exit stat is asymmetric — an event defined by "closed back
inside" starts closer to the inside band.  All side-exit rates below
carry that head-start; only *differences between matched classes* and
the symmetric `mx_poke` (forward wick excursion) are informative.

| contrast | support | result | verdict |
|---|---|---|---|
| C1 F vs T (matched depth +-0.5ABR, speed +-0.25, side, hour, ABR-decile) | 10,861 pairs | P(rejection-side exit): F .667 / T .653 (+1.4pp); undefended CTRL_POKE .684 | F adds ~nothing over T on this stat; "edge presence" does not raise rejection vs raw extremes — descriptive, near-null |
| C2 FX vs CTRL_FX (matched side, hour, ABR-decile, speed +-0.25) | 24,305 pairs | P(expected side): FX **.854** / CTRL **.645** (+21pp); mx_poke 3.4p vs 6.0p | **the one large contrast**: the undercut leg carries real information; failed extremes hold better (mx halved).  Part of the exit-side gap is mechanical; mx_poke is not |
| C3 SQUEEZE vs CTRL_QUIET (matched hour+decile) | 3,450 pairs | time-to-exit: med 2.0 vs 2.0 bars | null — compression between detected walls does NOT exit faster than equal quiet runs elsewhere; "squeeze predicts expansion speed" unsupported on this stat |
| C4 BRACKET mid vs CTRL_SWING | 72,719 vs 1,514 | post-revisit up-exit: .499 vs .510; M→down .418, W→up .410 | M/W midpoints do not repel — after mid revisit, an M resolves *down* only 42% (up-continuation more common, +7pp vs plain swings); descriptive |

Honest read of the whole lane's validity layer: **the only mark whose
event carries a clearly measurable forward footprint is FALSE_EXT**
(the failed extreme holds — median re-excursion 3.4p vs 6.0p, exit
side +21pp matched).  T-vs-F depth of break, squeeze-between-walls,
and M/W midpoint all read near-null on value-blind path stats — i.e.
these marks are *chart grammar* (they narrate what just happened at a
defended edge) more than *forecasting devices*.  That is consistent
with the essence finding (E1.5): the author draws them to mark
communication, not to predict.

---

## E4 — Current-engine compliance & violations

Emission map (all v1, current working tree):

| mark | emitted by | key params |
|---|---|---|
| T (box) | `boxes.py:1269-1284` wick beyond edge > `tol`, close inside, depth `<= max(1.5*ABR, 2p)` | `tease_max_abr=1.5`, `tease_tol_pips=2.0` |
| F (box, direct) | `boxes.py:1191-1203` pending close-through re-enters -> `tease_break` + `label(F)` at edge price | pend resolves next bar |
| T->F relabel | `patterns.py:330-348` (called `boxes.py:1288`) | `tf_relabel_bars=3`, `tf_relabel_frac_height=0.5` |
| T (line) | `lines.py:417-426` wick beyond line, close inside | **no depth cap** |
| F (line) | **never emitted** — `tease_pierce` event only (`lines.py:427-441`) | — |
| BRACKET | `patterns.py:112-225` | `eq=max(3p,0.5ABR)`, sep 4-40, `mid>=0.5ABR`, shoulders 0.6, head 1.0, relevance 2.0·ABR |
| SQUEEZE | `patterns.py:229-305` | small bar <=0.8·ABR, n>=3, walls <=2.0·ABR, gap shrink <=0.6, apex <=15b |
| FALSE_EXT | **never emitted** — `bar_facts` only (`engine.py:696-703`); `render.py:137` can draw it | — |
| label dedupe | `patterns.py:309-321` one label per edge/side/excursion; T upgraded in place | — |
| lifecycle | squeeze dies on `wall_gone`/`wall_exit` (`engine.py:640-668`) | — |
| budget | `rate_label_tf=2`/72b window, `budget_annot=4`, hard cap 9 (`params_v1_1.json` salience) | marks compete with structure |

Compliance vs the E1 principles:

* **C1 reference-first** — every T/F/label call requires a live object
  edge; squeeze requires two live walls.  Compliant — but it makes
  marks *hostages of structure recall*: a missed box or an
  early-retired line can never carry a mark (the dominant fidelity
  loss; measured in E3a).
* **C2 resolution-not-probe** — T on close-inside; F on re-entry;
  relabel on sized counter-move; bracket on second-pivot
  *confirmation* (t_conf), not the extreme bar.  Compliant.
* **C3 information-not-signal** — marks are annot-class; they never
  change structure state (poke/relabel don't move edges).  Compliant
  — edges stay fixed, pokes become events (spec §3).
* **V1 asymmetric F** — a close-through that fails earns `F` on a box
  (`boxes.py:1197-1203`) but only an internal `tease_pierce` event on
  a line (`lines.py:433-441`): same market event, different ink.
  Violation of the uniform-verdict principle.
* **V2 deep-refusal hole** — a wick poke deeper than
  `max(1.5*ABR, 2p)` that closes back inside produces *no mark at all*
  (`boxes.py:1274-1275` depth gate).  Wyckoff's terminal shakeout —
  the loudest refusal — is exactly this case.  Violation: the mark
  grammar cannot express "deep and refused".
* **V3 F anchoring on resolution bar** — `label(i,...)` stamps F at
  the re-entry bar (`boxes.py:1201`), while the golden convention
  places the letter beside the excursion bar; the ruler tolerates
  +-10 min (`eval_v2.py:463`), so F events resolved >2 bars after the
  excursion miss even when detected right.  Partial violation —
  knowability is right, placement is wrong (placement can be
  back-dated like bracket spans).
* **V4 FALSE_EXT detected but not inked** — `bar_facts` computes the
  §3.9 signature per bar (`engine.py:696-703`) yet no object channel
  consumes it; golden encodes false highs/lows only inside ARROW raw
  text (0 normalized objects).  Violation of the spec grammar, and a
  golden-normalization gap on the other side.
* **V5 squeeze hostage** — `squeeze_scan` needs *two named live walls*
  (`patterns.py:248-281`); on panels where box/line recall is low the
  squeeze can never be proposed even when the compression is real.
  Structural coupling, by design, but it caps reach at the structure
  ceiling.
* **V7 mark channel dies at the box->level handoff** — when a box
  breaks, its edges become `LEVEL_CARRIED`/`MINI_LEVEL` objects
  (`boxes.py:1211-1223`), but `levels.maintain` (`levels.py:184-221`)
  has no poke/label path at all: a tease of a *carried* edge can never
  be marked, even though the author marks teases at old levels all the
  time (9.45a, 9.54a).  The event grammar currently lives only on the
  box and line kinds.
* **V6 marks fight structure for ink** — LABEL_TF shares the joint
  `rate_total` window and the hard cap; measured history: 40 right T/F
  proposals died `outranked` when BAR_MARKER was unsuppressed
  (PERCEPTION_LOG ~20:11Z).  Information marks competing with the
  structure they annotate is an essence violation — the mark is cheap
  ink, the edge already paid for itself.

**Ruler findings (Owner-only proposals — no ruler change made):**

* `eval_v2.py:353-354` `_fam_letter` strips only lowercase, so golden
  `WW`/`MM` can never equal engine `Ww`/`Mm` → 11 scorable golden
  brackets structurally unmatchable (+5 letterless ones never match).
* `eval_v2.py:455-463` `match_mark` compares side + time only — the
  T/F letter itself is never judged.  An engine `T` matches a golden
  `F` at the same bar.  If the Owner wants letter fidelity measured,
  that is a ruler decision.
* LABEL_TF `t=None` goldens (9) match on side alone
  (`eval_v2.py:461-462`) — they can only inflate the count, not test
  timing.

---

## E5 — Proposals and structure implications

### E5.1 Proposed build-lane experiments (<=2 variants each, all params
stated; ranked by expected gain)

**P1 — F on line false-breaks (fixes V1).**
Variant A: on `tease_pierce` (`lines.py:440`) call
`e.patterns.label(i, o, side="above" if side=="top" else "below",
letter="F", price=line_at_i)`; label `t0` = `pierce_bar` (placement
back-dated, decision causal).
Variant B: A + per-excursion dedup (`_poke_exc`-style flag on the
line geometry).
Expected gain: closes the F asymmetry; golden has 5 F letters + 8
timed `tff` arrows to reach.

**P2 — deep-refusal mark (fixes V2).**
Variant A: wick poke `depth > max(1.5*ABR, 2p)` closing back inside
emits `F` directly (not T) — "deep and refused" = failed break.
Variant B: raise `tease_max_abr` to 2.5 and let the relabel channel
upgrade.
Expected gain: covers golden "false break ran well above the box"
(9.8b) and the deep-shakeout class Wyckoff describes; also absorbs
the deep-poke cases currently invisible.

**P3 — F placement on the excursion bar (fixes V3).**
Single variant: `label()` accepts `t_anchor`; box-F path stamps
`t0 = _pend_break["bar"]` (the close-through bar) instead of the
re-entry bar.  Decision stays at re-entry; ink position back-dates —
same convention as bracket spans.  Expected gain: converts detected
F events into ruler-visible marks when the excursion ran >2 bars.

**P4 — mark channel on carried edges (fixes V7).**
Variant A: `levels.maintain` zone-touch branch emits T on wick-poke
into the zone that closes short of traverse (same tease predicate as
boxes, same depth cap).
Variant B: A + traverse survivors: a level closed `traversed` that
re-enters within `tf_relabel_bars` emits F (re-entering a carried
edge = the edge's failure verdict).
Expected gain: marks can live on old edges — the author's most
frequent mark location (teases at hours-old levels, 9.45a/9.54a).

**P5 — FALSE_EXT object (fixes V4).**
Variant A: new annot-class object emitted when `bar_facts` gains
`false_high`/`false_low`; `t0 = i-1` (the extreme bar, back-dated),
`side`, `price` = b1 extreme; ttl 6; shares the annot budget.
Variant B: fold into BAR_MARKER — same slot, `letter=false_high/low`,
gated by `marker.day_extreme_only`-style relevance (extreme must sit
on a live edge or be the session extreme).
Expected gain: makes the spec §3.9 grammar drawable; golden has no
normalized objects to match, so measured gain = consistency + DESIGN
validity only (honest expectation: fidelity unmeasurable).

**P6 — marks exempt from the joint rate window (mitigates V6).**
Variant A: LABEL_TF births consume the annot budget + their own
`rate_label_tf` window but not `rate_total` (marks ride the parent's
slot — cheap ink).
Variant B: no change (the 28de3f03 arm — full exemption incl. hard
cap — was measured and rejected; A is the narrower version).
Expected gain: fewer right marks dying `outranked`/`rate_limited` in
hot windows.

**P7 — squeeze walls from the pivot stream (mitigates V5).**
Variant A: when <2 live object walls exist, allow confirmed same-side
pivot pairs (the bracket template's edges) to serve as walls —
compression between *detected* edges, not only *drawn* ones.
Variant B: accept the structure ceiling (squeeze stays hostage).
Expected gain: bounded by the structure-recall ceiling either way;
golden n=2 keeps this descriptive.

### E5.2 What the structure families need (the Lead's question)

"Edges fixed, pokes become T/F" is already the architecture (C3): the
engine never moves an edge on a poke — it records an event.  What the
marks teach back:

* **Boxes** — the mark channel must outlive the object: the drawn
  tail (`t1_drawn`, `boxes.py:1234-1239`) keeps the box visible after
  close, and the author marks teases at those edges; marks should
  follow *drawn* life, not *active* life.
* **Levels** — carried edges are where late teases land; they need
  the poke/F channel (P4).  A level that dies `traversed` should still
  be able to report "the traverse failed" once — that IS the F at a
  carried edge.
* **Lines** — need the symmetric F (P1); the `stale_retire_bars=60`
  death is right for ink but also ends the mark channel — acceptable
  only if the edge's carried successor (a spawned level) inherits it.
* **Coupling verdict** — marks should be emitted by the *edge*, not
  by the object kind: one `emit_tf(edge_state, bar)` shared by box
  edges, line traces and level zones would erase V1/V7 in one stroke
  and make the grammar uniform.  That is the single biggest
  structural recommendation: **marks attach to edges, edges attach to
  objects** — today marks attach to objects directly.

### E5.3 Proposed extra metrics (Owner decides; nothing gates on them)

* **M6 mark-stability** — retention of engine marks under +-0.3 pip
  jitter / 1-10 bar shifts / M15 (the consistency JSONL already
  computes it).
* **M7 relabel-flicker** — T->F flips per panel; should be low and
  monotone-in-time (a relabel that flips back and forth under noise
  is noise).
* **M8 letter fidelity** — if the Owner chooses letter-aware
  matching: P(letter correct | mark matched).  Currently the ruler
  can't see it.
* **M9 edge-coverage** — fraction of golden mark times at which any
  live engine edge existed within `tol` of the mark's implied level:
  the mark family's reach ceiling independent of selection.

---

## E6 — 10-line Vietnamese summary (ELI5)

1. Mấy dấu T/F, M/W, squeeze, false-high là "ghi chú sự kiện" lên cạnh đã có — không phải tín hiệu vào lệnh.
2. Người pro đánh dấu khi giá "thò" qua mép rồi bị đẩy lại: T là thử nhẹ, F là phá rồi thất bại.
3. Bản chất: cạnh đứng yên, sự kiện là tin nhắn — ai bị kẹt hàng, ai vừa bị quét stop.
4. Đo trên TUNE: engine chỉ bắt được 12% dấu T/F và 39% khung M/W của tác giả — chủ yếu vì cạnh chủ chưa tồn tại.
5. Gần một nửa dấu T/F của tác giả nằm ở mép mà engine không vẽ — dấu bị "con tin" của độ phủ structure.
6. Line có T mà không có F; level kế thừa từ box mất hẳn kênh mark — bất đối xứng cần sửa (P1, P4).
7. Dấu T/F rất mỏng: nhiễu 0.3 pip làm mất một nửa; chữ M/W thì dễ lật nhau (34%) dù khung ổn định.
8. Trên DESIGN, dấu false-extreme là mark duy nhất có "dấu chân" đo được: cực bị phá giữ tốt hơn rõ (+21pp, excursion giảm nửa).
9. F-vs-T, squeeze-giữa-hai-tường, điểm-giữa M/W gần như null — chúng là ngữ pháp kể chuyện trên chart hơn là máy dự báo.
10. Đề xuất lớn nhất: mark nên gắn vào CẠNH (edge), cạnh gắn vào object — một kênh emit_tf chung sẽ xóa cả bất đối xứng lẫn lỗi bàn giao.
