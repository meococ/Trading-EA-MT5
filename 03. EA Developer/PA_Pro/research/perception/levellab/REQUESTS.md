# REQUESTS — LEVEL-LAB

## REQ-L1 — salience slot pressure on level proposals (evidence, no ask yet)

Measured on engine `ef06f265ab84889f`, ruler `50e11fd5`, TUNE 198 panels
(`evalcheck/labels_v1_ef06f265ab84889f.jsonl`):

- Right LEVEL_CARRIED proposals (matched a golden): 46.
  Born 6 / rate_limited 25 / expired 16 / outranked 7  → **87% die in
  salience**. Born recall 0.146 vs oracle 0.50.
- Slot spenders near the kills: PATTERN_LINE hull_max_touch (30),
  BAR_MARKER star_extreme (24), BOX cluster_range (17), CONTEXT_LINE (16),
  LEVEL_CARRIED broken_line_edge (15) — the family does not crowd itself;
  it is starved by lines/markers/boxes.
- Per-golden: of the 24 oracled LEVEL_CARRIED goldens, 17 died
  `proposed_not_born` (rate_limited in 16/17).

§15.3 check — can a cap raise be justified? On the production stream
(select_levels.py, day 5-fold AUC): **no candidate feature reaches 0.60
on every fold** for either level type (best: `score` 0.58, `prom_abr`
0.59, `touches` 0.56). A cap raise without a separator would raise ink
57:1 wrong:right — not filed as an ask.

Variant menu for the Lead (after V4 shows whether right proposals become
separable under a tighter proposer):

1. **Family-floor allocation**: reserve 1 slot per salience window for the
   level family when a candidate exists (policy change, no feature needed).
2. **Post-V4 re-measure**: if the lab proposer makes right level proposals
   separable (touches/defence AUC ≥0.60 all folds), then request
   `rate_level_carried` ↑ with the measured separator.
3. **Cross-family dedup**: `broken_line_edge` levels duplicate live
   PATTERN_LINE geometry — let them inherit, not compete for, a slot.
   *V8 update (ROUND_L7): dedup measured — recall@k goes DOWN slightly when
   level proposals near live box/line prices are suppressed (lab combo k2
   .271 vs .312). Item 3 withdrawn: families duplicate because the barrier
   is real.*

## REQ-L2 — ret_24 ranker for level proposals (re-measured, borderline)

HANDOFF_BUILD_TO_LEVELLAB §3 reports ret_24 ("birth within 24 bars of a
same-direction touch") AUC ≈ 0.645 on the line stream. Re-measured on the
level proposal stream (`ret24_measure.py`, 12 179 dedup'd level candidates,
funnel labels, engine `ef06f265`):

- Overall AUC **0.606**; day-level 5-fold: .612 / .651 / .702 / **.526 /
  .558** — 2 of 5 folds below 0.60.
- In the matched-ink ranking task (ROUND_L7) ret24 is the CV-chosen ranker
  for the lab stream (3/5 folds) and lifts LC recall@2 .271 → .333 vs
  birth_score. It also tops naive (.292@2) and MINI (.387@2).

Verdict: **useful as a ranker inside a small live pool, not a clean
per-fold proposal-level separator.** Not filed as an ask for a cap raise;
documented so the Lead can weigh it as a ranking feature under a live
budget (see LEVEL_INTEGRATION v2).

## REQ-L3 — defended_origin births starved by the shared rate ledger (measured post-integration)

Measured on engine `1c24be53`, flag ON, 198 TUNE (ab_engine.py):

- 293,698 defended_origin proposals -> **262 born** (1.3/panel).
- `rate_limited` 3,123; pool `expired` 2,895; `outranked` 428;
  `suppressed_budget` 122,913 — the local 2+1 gate spends most of its
  force on its own queue (pending pool members count toward occupancy).
- The design point "2 live LC at tau" is unreachable while
  `rate_level_carried=1/72` and `rate_total=5/72` govern births: two
  live defended LCs need two births inside overlapping windows.
- Flicker cost of the workaround: suppressed losers transiently birth
  through the pool, then close 'superseded' (+0.10 ch/h vs flag off).

Options for the Lead (any one needs a salience-param decision, outside
LEVEL-LAB scope — not applied):

1. Treat `defended_origin` births as continuations (the route already
   carries the defence evidence; the birth is the *notice*, not new
   ink) — exempt from `rate_total`, keep `rate_level_carried`.
2. Raise `rate_level_carried` to 2/72 only while the flag is on
   (paired A/B needed; risk: old routes share the counter).
3. Let the family budget live in `level.def_*` and give defended
   births a dedicated `rate_defended` counter (cleanest separation).

Post-A/B addendum (21:16Z): the contention is **bidirectional**. On the
4 panels where BOX lost matched hits (9.2b#3, 9.18a#0, 9.40c#2,
9.45b#0), flag_on shows 1–3 defended births per panel (none inside the
golden box span) and BOX born counts drop (9.18a 2->1, 9.40c 3->2) with
rate_limited shifting up.  The shared `rate_total` ledger is the
mechanical cause of the keep-rule loss — a dedicated `rate_defended`
ledger (option 3) fixes BOTH directions: defended births stop starving
BOX, and stop being starved themselves.

## REQ-L3 addendum — v3 spec (R24 §24.2 item 3, spec-only: salience.py is build lane)

Trigger condition read literally: v2 did NOT lose BOX (+1).  But the
same ledger mechanism re-appeared one family over — v2 loses
PATTERN_LINE −2 (9.27c#0, 9.46b#0; both panels show a defended LC
birth inside/near the golden PL span and PL candidates flipping
born -> rate_limited).  So the exemption spec is still needed.

v3 spec (REQ-L3 option 1), to be applied by the build lane in
`salience.py` around line 493:

    cont = c.route.startswith("broken_") or \
        c.route == "congestion_edge" or \
        c.route == "defended_origin"        # <-- v3 addition

Rationale identical to the existing comment: a defended-origin birth
is the *notice* of an already-qualified structure (the defence count
was earned before the proposal), the same way a broken-edge carry is
the parent's continuation.  `rate_level_carried` still applies (per-
kind ceiling kept).  Predicted effect from measured mechanism: defended
LC births stop spending `rate_total` -> BOX/PATTERN_LINE/BRACKET births
stop being displaced -> keep-rule family losses from ledger contention
go to ~0; defended born count rises (rate_limited 2,268 of 283,638 v2
proposals would partially convert).  Needs a paired A/B at one hash
before any default change.

## REQ-L3 RESOLVED by measurement (22:20Z, engine 2795e5e0)

The build lane's `salience.fam_ledger` (default OFF) implements the
spirit of option 3 — each family draws on its own rate share instead
of the joint `rate_total`.  Three-arm A/B at one hash (ROUND_L12):

- ledger alone: BOX −2 -> keep-rule FAILS (share reallocation is not
  neutral for BOX, whose old joint-pool share exceeded 1/72);
- ledger + defended-LC (v2 config): **keep-rule PASSES** — LC +4
  (.146->.229 born, .021->.128 @2), BOX 0, PL 0, worst CONTEXT_RANGE
  −1; clutter ratio, live@tau, flicker all unchanged; day-bootstrap
  CIs positive (LC born +.120 [.009,.242], LC@2 +.119 [.021,.233]).

Remaining intra-family note: LEVEL_CARRIED's own share (1/72) now
carries both defended-origin and broken-edge emitters — 4 flag_on-era
hits that came from `broken_box_edge_up`/`broken_line_edge` objects
flip to defended births (and 5 new goldens are gained).  If both
emitters stay on, the LC share is the next selection bottleneck.
