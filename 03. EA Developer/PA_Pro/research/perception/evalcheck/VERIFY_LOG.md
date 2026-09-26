# VERIFY_LOG — independent verification of builders' claims (Z5)

Each entry is independently re-measured by the EVAL-AUDIT lane with
`eval_v2.py` (ruler `50e11fd5a2ab7974`), `funnel.py::cand_right` and
`e4_bridge.py` on all 198 TUNE panels.  Verdicts: CONFIRMED or
DISPUTED, with numbers.

## 2026-09-21 18:32Z — LINE-LAB L5 integration (engine v1 `694313a38abc2da6`)

Claim under test (linelab/INTEGRATION_LOG.md 18:26Z): L5 port adds
anchor proposals on any confirmed pivot/loc-extreme, relaxes
over-pivot veto and slope drift, span_max_min 360, 3-touch birth
gate, anti-churn revive/retire.  Test-side claim: 34/34 PASS.

Baseline: previous accepted v1 `cf2a7c1abc3c21d6` (bridge_report.md)
and funnel labels `labels_v1_504eb8ef53e5c492.jsonl` (deleted file —
R12 §12.5 deviation; its numbers are cited from FUNNEL.md/E12 logs).

- test suite: `tests/test_engine_v1.py` run independently ->
  **34/34 PASS — CONFIRMED.**
- PATTERN_LINE eval_v2 recall: 0.08 (14/186) -> **0.11 (20/186) —
  CONFIRMED small improvement** (+6 matches; trusted subset 0.08 ->
  0.12).
- PATTERN_LINE funnel oracle: 0.40 -> **0.36** and born 0.08 -> 0.11 —
  **DISPUTED as a proposal-quality win**: more lines are born, but the
  oracle ceiling (a right proposal exists at all) went DOWN 4 pts.
  The port helps selection/birth, not coverage.
- Q2-loose PL coverage: 0.90 -> **0.78** — loose coverage dropped;
  the new anchor/veto rules produce fewer or later proposals overall.
- Side effects (eval_v2): LEVEL_CARRIED 0.15 -> **0.12**, BRACKET
  0.21 -> 0.20, CONTEXT_LINE 0.22 -> 0.22, BOX 0.05 -> 0.05.
  Net: line recall +3 pts paid for with -3 pts carried levels.
- Snapshot check (Z2): linelab prototype `ceef7d3f` PATTERN_LINE
  snapshot recall 0.14 with clutter 4.0; integrated v1 0.11 with
  clutter 12.0 — the lab engine still beats the integrated engine on
  both axes.
- Evidence: `bridge_694313a3.md`, `labels_v1_694313a38abc2da6.jsonl`,
  `FUNNEL.md` (v1 section regenerated for this hash), `SNAPSHOT.md`.

## pending

- BOX-LAB: no oracle-ceiling / born-recall claim published yet
  (boxlab/BOX_LOG.md still at session start, 18:14Z).  When it lands,
  rerun `funnel.py` + `eval_v2` against the prototype and log
  CONFIRMED/DISPUTED here.
- LINE-LAB L6-L8 (coverage / selection) not yet claimed.

## 2026-09-21 18:58Z — build lane zombie retirement (engine v1 `ef06f265ab84889f`)

Claim under test (PERCEPTION_LOG.md 18:45Z/18:55Z): §11.4a generic
retirement implemented (retire_far 3xABR x 24 bars, retire_stale 72
bars, SQUEEZE wall_exit); post-retirement eval_v2 claimed
BOX 5, BRACKET 16, LEVEL 7, PATTERN_LINE 18, clutter 4.58.

Independent re-measure at hash ef06f265ab84889f (scoreboard row
18:57Z, ruler 50e11fd5):
- matched counts (eval_v2, scorable denominators): BOX 6/108,
  BRACKET 18/85, LEVEL_CARRIED 6/48, PATTERN_LINE 19/186.
- Direction CONFIRMED: retirement costs ~0-2 matches per type vs
  694313a3 (was BOX 5, BRACKET 17, LC 6, PL 20) — small as claimed;
  live clutter at decision times 11 -> 10 (scoreboard median).
- Exact counts DISPUTED: claimed 5/16/7/18 vs measured 6/18/6/19.
  Probable cause: the engine was mid-edit when they ran (their run
  predates the pinned hash); differences are +-1-2 objects per type.
  Their clutter metric (4.58) is a different definition
  (objects/golden ratio, not live-at-tau) — not comparable.
- Clutter DID fall as §11.4a intends: scoreboard live-median 11 -> 10.

## 2026-09-21 19:13Z — v1 @97cc437f + BOX-LAB X2 consistency

- Engine hash drifted again (694313a3 -> ef06f265 -> 97cc437f).
  Independent eval_v2 row (scoreboard 19:12Z): BOX 16/108 = .15
  (was .06), PATTERN_LINE 35/184 = .19 (was .10), LEVEL_CARRIED 6/48
  = .12, located .16, oracle BOX .32 / PL .41, clutter med 15,
  snapshot .14.  BOX recall tripled vs ef06f265 — CONFIRMED
  improvement direction; still far under the 0.70 gate.
- BOX-LAB X2 (boxlab/BOX_LOG.md ~18:5xZ) reports oracle v0=34,
  v1=32 — matches MY funnel/cand_right counts independently
  (34 = .31*108, 32 = .30*108): CONFIRMED, two implementations agree.
- Their claim "both engines propose ~45-55 min after golden
  build_end on median" is consistent with my Z1 miss taxonomy
  (edges_ok_start_wrong dominant for v0): CONFIRMED qualitatively.
- GATE_PACK.md refreshed for the 01:00Z decision: gate table + CI95
  + trusted-subset recall + scoreboard history per engine.

## 2026-09-21 19:44Z — v1 is mid-edit; measurements unstable

- GATE_PACK run at ~19:40Z measured v1 under hash 92f09c8e:
  BOX .06 (16/108->6/108), PL .10, LC .12 — a REGRESSION vs the
  97cc437f row logged at 19:12Z (BOX .15, PL .19).  Hash drifted
  again to 54756075 within minutes (params provenance currently
  fails: engine not instantiable).  VERDICT: builder claims for
  v1 cannot be verified while the file churns; the 00:30Z refresh
  will pin whatever hash is stable then.  Both rows stay on the
  scoreboard — history is append-only.

## 2026-09-21 19:47Z — CORRECTION on the 97cc437f row

- Builder's PERCEPTION_LOG (~19:3xZ) discloses: the 19:12Z
  scoreboard row (BOX .15 / PL .19 / clutter 15) measured a
  TRANSIENT rate-window displacement experiment that they later
  REJECTED and reverted (their own A/B: hit/birth flat ~1.7%,
  D18 churn signature).  The row is honest as a measurement of
  that hash — scoreboard history stays append-only — but it does
  NOT represent live v1.  Flagging here so nobody reads .15/.19
  as the v1 baseline.
- Gate-pack rerun under hash 92f09c8e (closer to live):
  BOX .06 / PL .10 / LC .12 — consistent with the reverted state.
- Live hash is still churning (54756075 -> df15a53d within min).
  Builder notes a post-ef06f265 salience change (refusal-expiry
  extension) pending its own paired A/B under R14 §14.2 — flagged
  as UNVERIFIED until they publish numbers I can reproduce.
- New claim to queue for verification when stable: joint
  rate-cap analysis (context births flooding the budget) and the
  HANDOFF_BUILD_TO_LEVELLAB note for LEVEL-LAB.

## 2026-09-21 20:17Z — W1b negative controls: protocol note + pending numbers

- Batch-A judge (neg_000-014) self-disclosed an incidental manifest
  exposure (grep surfaced _plaus_neg.jsonl metadata mid-run).  All 15
  verdicts DISCARDED under the visual-only rule; a fresh judge was
  dispatched on the same 17-item set after neg_005/018/022 were
  regenerated to render inside the visible band (originals preserved
  in _plaus_neg_r1.jsonl, rows carry rev=2).
- Batch-B judge (neg_015-029 minus regenerated items) visually
  confirmed per-item reasons; 13 verdicts kept.
- sensitivity/specificity + Rogan-Gladen corrected plausible-FP
  shares land in PLAUSIBILITY.md once the re-judge returns.
- Recall@k (R17 §17.3) measured: RECALL_AT_K.md, rank = born
  cand_log score when linkable (~97%), else recency.  v1 numbers are
  on hash a01bf298 (mid-edit); re-run on the frozen stable hash for
  the final pack.

## 2026-09-21 20:25Z — W3 verify: builder A/B arms reproduce on my ruler

- Re-measured cumulative recall from cached engine pickles, ruler
  50e11fd5, scoreboard semantics (match_panel on raw goldens):
  - a01bf298 (retirement allOn baseline): BOX 6/108, PL 19/184,
    LC 6/48, BRACKET 25/85, CONTEXT_LINE 2/9 -> matches builder's
    20:05Z baseline EXACTLY. CONFIRMED.
  - 03dbe495 (REQ-1(b) revive ON): BOX 9/108, PL 19/184, LC 5/48,
    BRACKET 32/85 -> matches builder's 20:11Z ON arm
    (BOX 6->9, BRACKET 25->32, LC 6->5, PL 19/19). CONFIRMED.
  - noFar a3feb448 and reviveOff 03917fd5 have no cached runs in
    _cache (builder's harness stored elsewhere); OFF-arm numbers
    remain UNVERIFIED until the stable-hash re-measure.
- W1b closed: specificity 20/30 = 0.67 < 0.70 -> PLAUSIBILITY.md now
  carries the UNRELIABLE flag; sensitivity 27/30 = 0.90; Rogan-Gladen
  corrected plausible-FP: v0 .71 (CI .33-1.00), v1@ef06f265 .65
  (CI .29-1.00), linelab .82 (CI .50-1.00).  Read: direction holds
  (most engine FPs are visually defensible marks) but the correction
  interval is too wide to bank on.

## 2026-09-21 20:31Z — W3 verify: builder paired-A/B arms, frozen ruler 50e11fd5

Re-measured cumulative recall on all 198 TUNE panels from cached
engine pickles; every claimed arm reproduces EXACTLY:

| arm | hash | measured | claimed | verdict |
|---|---|---|---|---|
| ctx off (A) | 92f09c8e6dd1 | BOX6 PL19 LC6 BRA18 CL2 | same | CONFIRMED |
| ctx 2/288 (B, kept) | 54756075e199 | BOX6 PL19 LC6 BRA25 CL2 CR1 | same | CONFIRMED |
| ctx 1/288 (C) | df15a53dc903 | BOX5 PL17 LC7 BRA35 CL2 | same | CONFIRMED |
| ctx 1/144 (D) | f9ae8fad7d12 | BOX5 PL18 LC7 BRA24 CL2 | same | CONFIRMED |
| retire_far OFF | a3feb4480ff8 | BOX5 PL22(.12) LC5(.10) | .05/.12/.10 | CONFIRMED |
| revive OFF | 03917fd57efc | BOX6 PL19 LC6 BRA25 | same | CONFIRMED |
| retire all OFF | 0cf85d730f8e | BOX5 PL22 LC6 BRA25 | same | CONFIRMED |

Earlier caveat: builder claimed B kept because "zero family losses"
— on my ruler C loses PL 19->17 (their own table agrees) and D loses
PL 19->18, so B is indeed the only zero-loss arm. CONFIRMED.
Bad-retirement counts (0 for every rule) NOT yet re-measured — that
needs the retirement-event log per arm; queued for the stable-hash
pass.

## 2026-09-21 20:33Z — W3 verify: bad retirements (R14 §14.3), measured myself

Method: object events carry ('close', reason) at a bar index.  A
retirement = close reason in (retire_far, retire_stale, wall_exit).
Bad = the retired object matches a golden under ruler geometry AND
the golden span runs >= 15 min (3 bars) past the retirement bar.
Measured on cached a01bf298 (allOn):

- counts: retire_far 430 (builder 426, +4), wall_exit 60 (builder
  60, exact), retire_stale 15 (builder 12, +3) — small counting
  convention drift, same order.
- BAD retirements: 1 total (a retire_far), builder claimed 0 for
  every rule.  VERDICT: builder's conclusion stands (bad rate ~0.2%,
  far under the 10% keep-rule), but the literal "0" is off by one —
  flagged, not blocking.
- 20:45Z noFar a3feb448 follow-up: builder claim was DECIMAL recalls (.12/.10), not counts — matches measured 22/184 and 5/48 and the 19:59Z scoreboard row exactly. Earlier count-vs-decimal readout was a transcription error on my side. CLOSED: CONFIRMED, no engine discrepancy.
- 21:23Z IDENTITY CHECK (R23): STABLE 584c7743 (marker_off variant files) vs reviveOff 03917fd5 - canonical objects compared on all 198 TUNE panels (type,t_left,t_right,t_birth,state,geometry): 0 diffs, 0 missing. CONFIRMED bit-identical; consistent with REQ-1(b) OFF + all new flags default OFF.
- 21:35Z BOX-LAB artifacts verified vs ROUND_X3 claims (r33/r37, eval_lab_rNN.json, 198 panels): r33 oracle 60/108=.556 born 21=.194 rec@1=rec@2=16=.148 ink 1050/198=5.30/panel live_tau_med 1.0 - ALL CONFIRMED. r37 born 30=.278 rec@2 26=.241 ink 3464/198=17.5/panel live_tau_med 2.0 - ALL CONFIRMED. OWED by BOX-LAB per R23.3: LODO-CV of the score, deeper_lv/barrier shuffle control, barrier sign per fold - not in ROUND_X3 yet (X4 due (plan ~23:30Z)). Lab numbers remain lab-stream hypotheses (R15.1), not engine results.
- 21:47Z R24 same-hash re-runs at a62edc19 (runtime flags, arm_ab.py, variants ab_*): base reproduces STABLE 584c7743 exactly (BOX .06 PL .10 LC .12 BRA .29 snapR .10 clutter 10) = bonus identity proof for S24.4. reviveON: BOX .08 BRA .38 LC .10 snapR .11 clutter 12 - CONFIRMS lane claim (+3 BOX +7 BRA for +2 live). markerON: PL .09 BRA .32 clutter 9 - CONFIRMED. budgetGOLD: BOX .04 BRA .11 snapR .06 clutter 7 - CONFIRMS rejection. tailON: BOX .06 LC .12 BRA .31 clutter 11 - NOT exactly zero delta as claimed (BRACKET .29->.31, clutter 10->11; small but real) - flagged. LABEL_TF arm is a code change, not a runtime flag - cannot re-run same-hash; excluded from lever table per S24.3.
- 22:05Z LEVEL-LAB flag verification (arm_ab.py, runtime level.defended_origin): source moved a62edc19 -> e3538ee7 mid-run; params file then broke load_params (level.def_price_mode added without provenance - transient mid-edit). labON@e3538ee7: LC born .21 (claim .229), BOX .04 (=-2 vs base .06 - CONFIRMS keep-rule FAIL direction), PL .10, BRA .29, snapR .10, clutter 11. labV2@e3538ee7: LC .15 (claim .167), BOX .06 healed, PL .09 (-1) - direction CONFIRMED. labV2B aborted mid-run (params edit) - partial pickles old-state only, rerun at freeze. PRELIMINARY verdict: flag_on keep-rule FAIL confirmed (BOX -2), LC gain confirmed direction.
- 22:17Z R26 S26.4 cache audit: _cache has 39792 pkl, 0 zero-byte, 1728 unloadable (all AttributeError stale-class) confined to run_famledger_v2_2795e5e0 (576), run_fam_ledger_2795e5e0 (576), run_flag_on_1c24be53 (576) - none are read by pack arms (ab_*/marker_*/plain hashes). Hardened: cache.run now catches ANY unpickle failure and re-runs fresh; recall_at_k.per_panel_pkl refuses+counts bad entries (BAD_PKL); gate_pack._pickled already refuses (returns None, panel skipped - cls=None path cannot re-run by design). All lever arms keyed by variant in filename.


## 2026-09-21 22:24Z — R25 §25.3 OWNER_JUDGE_PACK remediation

Re-rendered all 20 items via plausibility.render_item(blind=True):
title band erased, view expanded so the tau divider is always in
frame, BAR_MARKER now drawn as triangle+stem (was an 8px dash).
Degenerate zero-width CONTEXT_RANGE item_010 replaced by same-
class item_094 (fp/no) per §25.3.2; key regenerated outside the
pack at _owner_judge_key/_key.json. Pack = INSTRUCTIONS.md,
ANSWERS.md, items/ only. Same seed 20260921, same class mix
(8 fp / 6 control / 6 neg).

Per-item check (drawing / tau line / title):
- p01 BAR_MARKER item_043: drawing yes, tau yes, title stripped
- p02 PATTERN_LINE item_004: drawing yes, tau yes, title stripped
- p03 BOX item_091: drawing yes, tau yes, title stripped
- p04 PATTERN_LINE item_032: drawing yes, tau yes, title stripped
- p05 BOX neg_025: drawing yes, tau yes, title stripped
- p06 BOX neg_013: drawing yes, tau yes, title stripped
- p07 BOX item_058: drawing yes, tau yes, title stripped
- p08 BRACKET item_117: drawing yes, tau yes, title stripped
- p09 BOX item_052: drawing yes, tau yes, title stripped
- p10 BAR_MARKER item_083: drawing yes, tau yes, title stripped
- p11 PATTERN_LINE item_129: drawing yes, tau yes, title stripped
- p12 BRACKET neg_018: drawing yes, tau yes, title stripped
- p13 BOX neg_003: drawing yes, tau yes, title stripped
- p14 PATTERN_LINE item_112: drawing yes, tau yes, title stripped
- p15 BAR_MARKER item_002: drawing yes, tau yes, title stripped
- p16 CONTEXT_RANGE neg_012: drawing yes, tau yes, title stripped
- p17 PATTERN_LINE item_005: drawing yes, tau yes, title stripped
- p18 BOX item_094: drawing yes, tau yes, title stripped
- p19 BOX neg_004: drawing yes, tau yes, title stripped
- p20 LEVEL_CARRIED item_108: drawing yes, tau yes, title stripped

## 2026-09-21 22:41Z — R27 §27.2 famledger independent verification (own arm_ab.py, one hash 9283b389)

Lane's 2795e5e0 pickles are stale-class/unloadable (R26 audit), so I
re-ran the three arms myself at hash 9283b389 via runtime flags:
base, famledger (b), famledgerV2 = fam_ledger+defended_origin+
def_mini_off (c).  Same-hash deltas (my ruler, born recall):

| arm | BOX | PL | LC | BRA | snapR | live@tau |
|---|---|---|---|---|---|---|
| base | .06 | .10 | .12 | .29 | .10 | 10 |
| (b) famledger | .04 | .10 | .10 | .35 | .10 | 10 |
| (c) famledgerV2 | .06 | .10 | .21 | .35 | .11 | 10 |

Per-golden diff vs base (any-object match, all families):
- (b): 17 lost (BOX x2, PL x4, LC x4, BRA x4, MINI x1, CR x1),
  20 gained -> net +3 goldens but BOX net -2: keep-rule FAIL
  CONFIRMED.
- (c): 15 lost (BOX x1, PL x3, LC x3, BRA x3, MINI x1, CR x1),
  27 gained (LC +7) -> LC born .12->.21 (+4), BOX net 0, PL 0:
  keep-rule PASS CONFIRMED directionally (lane: LC .146->.229 at
  2795e5e0; mine .12->.21 at 9283b389 — same direction, slightly
  different hash).

§27.2.2 why (b) loses 2 BOX but (c) loses none — the budgets are NOT
fully separate:
1. fam_ledger gives every kind without a fam_rate_* entry a ZERO
   share: CONTEXT_RANGE/CONTEXT_LINE/MINI_LEVEL/SQUEEZE can never be
   born (cand_log shows rate_limited at every tick; objects dict has
   none).  Removing that ink changes the NMS landscape -> BOX birth
   timing shifts (9.40c: base BOX born t=950, (b) outranked at 950
   then born 995 -> missed golden span).
2. The live budget stays shared: signal-class cap + budget_hard +
   score displacement pick the weakest across ALL signal-class live
   objects, and NMS suppression is geometric across families.  In
   (c) defended LC births enter that shared competition and happened
   to restore the 2 BOX matches (born 965 vs 995).  "(c) loses no
   BOX" is partly outcome luck via these shared channels, not proof
   of isolation.
3. cont routes (broken_*/congestion_edge) bypass fam_ledger
   entirely (joint_full=False for cont) — unbudgeted by the fam
   ledger, still capped by rate_level_carried.

§27.2.3 recall@k for (c) ab_famledgerV2 @9283b389 (456 tau-rows,
engine ranking = object score / born cand_log score / recency):
k1 .006 snapR (LC .00) | k2 .025 (LC .00) | k3 .035 | k5 .088
(LC .02).  LC snapshot unbudgeted at tau = 3/46 = .065 vs lane's
.128 claim — DIFFERENT: hash delta and/or ranker (their LC@2=.128
looks like a lab-ranker number, not engine top-k).  The keep-rule
claim (born recall +4 LC, zero family losses) is CONFIRMED; the
snapshot/recall@k magnitudes are NOT reproduced — flagged.

VERDICT: CONFIRMED with caveats — (c) is the first lever to pass
the keep-rule in my measurement too, but the ledger is not fully
per-family (zero-share kinds + shared live budget + shared NMS +
cont bypass), and lane's LC snapshot/.128 figures are not
reproduced at this hash.

- 22:48Z IDENTITY CHECK (R27 §27.3): ab_base @9283b389 (all new flags
  OFF incl. fam_ledger) vs STABLE 584c7743 (marker_off) — canonical
  objects (type,t_left,t_right,t_birth,state,geometry) equal on
  198/198 panels, 0 diffs. CONFIRMED: current source at default
  params is behavior-identical to the frozen pre-freeze STABLE.
- 22:48Z walls_check PASS incl. fixed clock check: entry stamps anchored
  at line start only; mid-line deadline mentions (LEVEL_LOG
  'till 23:50Z') no longer flagged. Earlier 5 'fails' were false
  positives of my own over-broad scan.

## 2026-09-21 23:06Z — R28 §28.3.1 tau fix (per-item)

tau = drawn object's own decision time (R21 §21.2 by kind):
BOX/lines -> drawn t1; BAR_MARKER -> t0; LEVEL_*/MINI -> t0+10;
BRACKET/SQUEEZE -> t1.  Controls keep golden build_end (manifest
tau already = build_end).  |tau-expected| = 0 by construction;
the column shows |old-tau - new-tau| in bars (the fix magnitude).

- p01 BAR_MARKER item_043: tau=480 old=145 |dTau|=67 bars, drawing yes, no title
- p02 PATTERN_LINE item_004: tau=630 old=630 |dTau|=0 bars, drawing yes, no title
- p03 BOX item_091: tau=805 old=805 |dTau|=0 bars, drawing yes, no title
- p04 PATTERN_LINE item_032: tau=230 old=85 |dTau|=29 bars, drawing yes, no title
- p05 BOX neg_025: tau=1020 old=1020 |dTau|=0 bars, drawing yes, no title
- p06 BOX neg_013: tau=745 old=745 |dTau|=0 bars, drawing yes, no title
- p07 BOX item_058: tau=715 old=30 |dTau|=137 bars, drawing yes, no title
- p08 BRACKET item_117: tau=840 old=810 |dTau|=6 bars, drawing yes, no title
- p09 BOX item_052: tau=675 old=675 |dTau|=0 bars, drawing yes, no title
- p10 BAR_MARKER item_083: tau=720 old=430 |dTau|=58 bars, drawing yes, no title
- p11 PATTERN_LINE item_129: tau=545 old=545 |dTau|=0 bars, drawing yes, no title
- p12 BRACKET neg_018: tau=1065 old=1065 |dTau|=0 bars, drawing yes, no title
- p13 BOX neg_003: tau=660 old=660 |dTau|=0 bars, drawing yes, no title
- p14 PATTERN_LINE item_112: tau=650 old=650 |dTau|=0 bars, drawing yes, no title
- p15 BAR_MARKER item_002: tau=780 old=455 |dTau|=65 bars, drawing yes, no title
- p16 CONTEXT_RANGE neg_012: tau=835 old=835 |dTau|=0 bars, drawing yes, no title
- p17 PATTERN_LINE item_005: tau=550 old=550 |dTau|=0 bars, drawing yes, no title
- p18 BOX item_094: tau=485 old=30 |dTau|=91 bars, drawing yes, no title
- p19 BOX neg_004: tau=600 old=600 |dTau|=0 bars, drawing yes, no title
- p20 LEVEL_CARRIED item_108: tau=490 old=665 |dTau|=35 bars, drawing yes, no title

## 2026-09-21 23:19Z — R30 §30.2: uniform tau + blue item style

One tau event per kind, same for every class: BOX/CONTEXT_RANGE tau
= drawn right edge (break bar) for goldens too — kills the "tau
inside the box = author" class tell (was 2 controls vs 7 others).
Items now drawn blue ~2.5px on all classes (EMA stays thin grey) —
fixes p04 line hidden on the EMA.  |dTau| vs the 23:05Z render in
bars; drawing/title checks from the CHECK lines of owner_pack.py.

- p01 BAR_MARKER item_043: tau=480 |dTau_vs_old_manifest|=67 bars, drawing yes, no title
- p02 PATTERN_LINE item_004: tau=630 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p03 BOX item_091: tau=1010 |dTau_vs_old_manifest|=41 bars, drawing yes, no title
- p04 PATTERN_LINE item_032: tau=230 |dTau_vs_old_manifest|=29 bars, drawing yes, no title
- p05 BOX neg_025: tau=1020 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p06 BOX neg_013: tau=745 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p07 BOX item_058: tau=715 |dTau_vs_old_manifest|=137 bars, drawing yes, no title
- p08 BRACKET item_117: tau=840 |dTau_vs_old_manifest|=6 bars, drawing yes, no title
- p09 BOX item_052: tau=840 |dTau_vs_old_manifest|=33 bars, drawing yes, no title
- p10 BAR_MARKER item_083: tau=720 |dTau_vs_old_manifest|=58 bars, drawing yes, no title
- p11 PATTERN_LINE item_129: tau=545 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p12 BRACKET neg_018: tau=1065 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p13 BOX neg_003: tau=660 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p14 PATTERN_LINE item_112: tau=650 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p15 BAR_MARKER item_002: tau=780 |dTau_vs_old_manifest|=65 bars, drawing yes, no title
- p16 CONTEXT_RANGE neg_012: tau=835 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p17 PATTERN_LINE item_005: tau=550 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p18 BOX item_094: tau=485 |dTau_vs_old_manifest|=91 bars, drawing yes, no title
- p19 BOX neg_004: tau=600 |dTau_vs_old_manifest|=0 bars, drawing yes, no title
- p20 LEVEL_CARRIED item_108: tau=490 |dTau_vs_old_manifest|=35 bars, drawing yes, no title

## 2026-09-21 23:30Z — W1b negatives audit (R28 §28.3.2)

neg_audit.py: each synthetic negative converted to an engine record
and matched against every scorable golden on its panel under the
official ruler (eval_v2.match).

- 30 negatives audited; 2 invalid (match a golden): neg_002, neg_011
  both are BRACKET price-shifts — the bracket rule (coverage>=0.3
  + same letter) ignores price, so the shift leaves the match.
  Construction defect; only a time shift or letter change makes a
  true BRACKET negative.
- 6 owner-pack negatives cross-referenced: neg_003, neg_004, neg_012, neg_013, neg_018, neg_025 — all valid.
- neg_025 (pack p05): no ruler match despite looking well-fitted —
  valid; judge rejected it anyway.
- W1b recomputed: sensitivity 27/30=.90 [.77-1.00]; specificity
  all-30 20/30=.67 [.50-.83]; valid-28 19/28=.68 [.50-.86].
- RG-corrected plausible-FP shares move <=.01 (v1 .65->.65).
- Verdict: R22 §22.3 "judge unreliable" STANDS — the 2 invalid
  negatives explain only .01 of the shortfall; not an artefact.
  Detail: PLAUSIBILITY.md "negatives audit + W1b recompute".

- 05:56Z RECALL_AT_K regen verified: every per-family figure (box/level/line/bracket/annot/squeeze @ k=1,2,5) and every snapshot k-row in the pack matches my independent cache re-measurement exactly. No mismatches. Checker: evalcheck/_check_recall_vs_pack.py.
- 06:11Z F5 render check (R41 s.41.6). render.render_engine callers in tree: ONLY scale/gallery.py (line 152) - and it already carries an explicit unit shim compensating the /PIP bug (gallery.py:32-44). OWNER_JUDGE_PACK items: built by evalcheck/owner_pack.py -> plausibility.render_item -> _render_v2 (golden/qa) base panel + plausibility.draw_item; all price-space vm.y(), never touches render.py. Golden QA overlays: golden/overlay.py - own PIL renderer, vm.y(price) direct, never touches render.py. evalcheck/render_compare.py and boxlab/render_audit.py also draw via _render_v2 / own PIL, not render.py. VERDICT: neither the owner judge pack nor the golden QA overlays went through the broken object layer; the only F5-affected renders are scale/gallery PNGs (shimmed).
- 06:11Z Naming the BOX-precision diagnostic difference (R41 s.41.1): m1_row.py reports eh[BOX]/en[BOX] = 7/301 = .0233 -> '.023'. GATE_PACK_9283b389's own row is the same fraction '0.02 (7/301)'. The '.025' in C1_M1.md is the build lane's _m1.py print of the same formula on a different object set (en=280 implied) - an upstream context difference, not a scorer disagreement. My scorer reproduces the pack verbatim.
- 06:15Z KEEP VERDICTS (R34 s.34.8/3.2) - own scorer m1_row.py on cache, both arms one process one hash, paired day-bootstrap CIs vs v0 (seed 20260921, 1000x). Script: evalcheck/_verify_keeps_c1.py; raw: evalcheck/_verify_keeps_c1.out.txt.
- 06:15Z K1 line.lab_score @afba83c5: CONFIRMED. line@2 16->18 hits (.083->.093, target up); box 2->3 and level 1->4 (improvements, no drop); clutter 5.00; OFF-arm = STABLE numbers (.017/.013/.083) and OFF-id vs ab_base@9283b389: 1728/1728 runs identical incl. events, 0 missing. Pickled e.p confirms lab_score False/True across arms; parent ab_base lacks the key entirely (pre-flag code). Suite 72/72 is build-lane-reported (not independently rerun). vs-v0 CIs: box -.110 [-.181..-.047], level -.001 [-.051..+.058], line +.003 [-.048..+.058].
- 06:15Z K2 level.defended_origin+def_mini_off @e62f2dc9 (parent 2ca5c67f): CONFIRMED. level@1 4->6 hits (.053->.079, above v0 .066); box 3->2 (-1) and line 18->17 (-1) both inside the -1 allowance; clutter 5.00. OFF-id vs labscore_on@afba83c5 (cross-hash parent): 1728/1728 objects+cand_log+events identical - the afba83c5->e62f2dc9 code edits did not touch kept-state behavior. Also vs famv2_off@e62f2dc9 same-hash: 1728/1728. vs-v0 CIs: box -.115 [-.187..-.056], level +.021 [-.039..+.089], line -.001 [-.052..+.055].
- 06:15Z K3 bxcombo @dd96c5fe (parent 22888182): CONFIRMED. box@1 2->3 (+1 hit, .017->.025), level 6->6 flat, line@2 17->19 (+2, .088->.098 above v0 .093); clutter median exactly 5.00. OFF-id vs lcpick2_off@2ca5c67f (cross-hash K2-kept state): 1728/1728 identical incl. events; vs c1r_base@dd96c5fe same-hash: 1728/1728. vs-v0 CIs: box -.118 [-.199..-.053], level +.028 [-.039..+.094], line +.018 [-.037..+.078].
- 06:15Z K3 clutter special check (R40 s.40.2): ON-arm per-panel ratio distribution n=179 (19 panels have 0 scorable goldens -> NaN excluded): min 1.43 p25 3.45 med 5.00 p75 7.25 max 16.0; 94/179 panels <=5.0. Median>5.0 requires >=5 panels moved above 5.0; >5.33 requires >=5 (the 5.33-bucket panels all sit in (5.34,5.5]). The famv2 5.33 is a DIFFERENT arm: famv2_on@e62f2dc9 = {lab_score, fam_budget, fam_caps} only -> median 5.333 (89/179 <=5). bxcombo adds wick_edges+dedup_iou+rank_score+box_lab_score_use on the K2-kept parent and pulls it back to 5.00. No contradiction - different hash, different flag set.
- 06:17Z SCALE comparator (R39 s.39.7) verified. Read scale_q1.py + harness.py + FINDINGS F2: the state-at-t projection takes type-at-t from the event log (asia_convert RANGE_OPEN->BOX at boxes.py:755 is the ONLY type mutation and it logs an event), liveness at t (not final state - handles lines.py/levels.py revive reopening same ids), live edge-sigs at t, and events<=t. A real causality break would have to change objects/events at or before t without changing the prefix run's own state - the comparator checks every prefix object vs same-id full-run AND every full-run-live id missing from prefix, so a hidden break cannot pass silently. RERUN: scale_q1.py --days 5 --seed 20260922 (KEPT arm, snapshot e62f2dc9, DESIGN days 2018-05-18, 2020-06-05, 2020-09-25, 2020-10-14, 2021-12-13 - all trading days inside 2016-2021): 250/250 prefix ts clean, all reruns byte-identical, 0 failures, ~0.4s/day. Consistent with F2's 1000/1000.
- 06:25Z K4 salience.box_score_pick (box supersede arm A, R40 s.40.3) @cfb862d4: CONFIRMED. box@1 3->7 hits (.025->.059, target up +4); level 6->6, line 19->19 flat; clutter 5.00 (note: 91/179 <=5.0, median would break with only 2 panels raised - thinner margin than K3's 5). OFF-id vs bxcombo_on@dd96c5fe (cross-hash K3-kept parent): 1728/1728 objects+cand_log+events identical. Pickled e.p: off=K3-state (9 flags ON, box_score_pick OFF), on=+box_score_pick. vs-v0 CIs: box -.077 [-.156..-.012], level +.028 [-.039..+.094], line +.018 [-.037..+.078]. Suite 72/72 build-lane-reported. Raw: evalcheck/_verify_k4.out.txt.
- 06:25Z K4B box_score_pick_prio (arm B, REJECTED): rejection CONFIRMED. vs arm-A parent (bxsupp_off = bxsup_on params, verified same-hash OFF-id 1728/1728): box@1 7->5 (-2 hits, exceeds -1 AND target down), level 6->7 (+1), line flat, clutter 5.00. A is correctly the kept form.
- 06:35Z R42 s.42.3 suite leg (own rerun, unmodified-fixture semantics via gen_engine->default-engine restore; load_params patched per config; subprocess per config, evalcheck/_suite_keeps.py). DISK defaults (params_v1_1.json as-is, i.e. K4-kept config): 7 FAILED / 65 passed of 72. The seven are exactly s.42.2's list: test_pullback_end_box_birth (Fig 3.1), test_range_box_double_top, test_false_break_wick_keeps_edge (Fig 3.8), test_break_close_beyond_edge, test_tease_vs_proper_break_class, test_tf_relabel, test_reanchor_on_new_double_top (Fig 3.9). Failure mode on inspection: no BOX born (CONTEXT_RANGE holds the box-family live slot under fam_budget/fam_caps) - consistent with s.42.2's diagnosis. K1-K4 per-config runs in flight.
- 06:52Z R42 s.42.3 suite leg - per-config results (unmodified-fixture semantics; params = the keep's own pickled e.p; current on-disk code). K1 labscore_on: 72/72 PASS - the reported 72/72 is valid on its own config. K2 deforig_on: 72/72 PASS - valid. K3 bxcombo_on: 65/72 - the SAME 7 fixtures fail (pullback-end box birth, double-top box, false-break wick, break-close, tease-vs-proper, T->F relabel, re-anchor double-top). Cause: fam_budget+fam_caps (introduced by K3) let a CONTEXT_RANGE hold the box family's single live slot, so no BOX is born - the fixture's drawn-object asserts fail. The 72/72 K3 reported was measured at parent defaults before the defaults flip (per s.42.3's note), not on its ON config. K4 bxsup_on: 65/72 - identical 7 failures; box_score_pick (K4's flag) does not change the failure set since it only works the rate-blocked branch. Attribution: the suite-leg break enters with K3's fam flags, not K1/K2/K4's own flags. Raw outputs: evalcheck/_suite_k{1..4}.out.txt.
- 06:58Z K5 line.slope_floor=0.25 @75a9650c (R41 s.41.4 flatness item): CONFIRMED. line@2 19->20 hits (.098->.104, target up); box 7->7, level 6->6 flat; clutter 5.00. Pickled e.p: slope_floor 0.0->0.25, all 10 K4-kept flags carried. OFF-id vs bxsup_on@cfb862d4 (cross-hash K4 parent): 1728/1728 objects+cand_log+events. vs-v0 CIs: box -.077 [-.156..-.012], level +.039 [-.028..+.122], line +.015 [-.038..+.071]. NOTE thin clutter margin: 90/179 panels <=5.0 - ONE panel raised above 5.0 pushes the median over (K3 needed 5, K4 needed 2). Suite leg on K5 config: running now, expected same 7 fam-flag failures as K3/K4. Raw: evalcheck/_verify_k5.out.txt. Rejected arms spot-checked: jointbud cap2 @fbb3a173 reproduces C1_M1 exactly (.042/.026/.057, clutter 1.50); arm-B prio rejection confirmed earlier.
- 07:01Z K5 suite leg: 65/72 - same 7 theory fixtures fail (slope_floor does not touch the fam-slot issue). So the suite-leg break remains attributable to K3's fam flags through the whole chain. Rejected-arm numbers all reproduce C1_M1 exactly on my scorer: jointbud cap4 .050/.026/.057 clutter 3.00; cap3 .042/.066/.062 clutter 2.33; cap2 .042/.026/.057 clutter 1.50 (cap counts transient annot kinds - blunt, correctly rejected); famcap_bracket=2 M1-flat with bracket@1 -1 (28/85) correctly OFF; lnsteep .059/.079/.088 line -2 correctly OFF.
- 07:32Z BXP salience.box_prio (R42 s.42.4 / R43 s.43.6) — verified at BOTH cached revs, pre-verdict. Flag provenance clean: bxprio_off carries K5-kept set + box_prio OFF; bxprio_on adds box_prio=True only (pickled e.p). M1 (own scorer, cache-only): @cd14f5fc ON = .059(7/119)/.039(3/76)/.098(19/193) clutter med 6.33 (69/179 <=5.0); @cd00d0be ON = .067(8/119)/.026(2/76)/.098(19/193) clutter med 6.00 (69/179 <=5.0). vs OFF parent row .059/.079/.104: level -3 / -4 hits — exceeds the -1 allowance at both revs; clutter UP at both. OFF-identity vs lnfloor_on@75a9650c (K5 parent): cd14f5fc = 1728/1728 objects+cand_log+events CLEAN; cd00d0be = objects 1725/1728 (3 diffs), cand_log 621/1728 (1107 runs differ — new rev writes cand_log entries with flag OFF) — OFF-id leg FAILS at the newer rev. Unmodified suite on bxprio_on@cd00d0be config (own runner, gen_engine restore): 72/72 PASS — build lane's claim independently confirmed; the K3 fam-slot fixture break is cured under box_prio. BOX-LAB three rank-2 stale-envelope cases (REQUESTS.md s.42.4): 9.2b t765 FLIPS to right box 13240-13259 (hit); 9.2b t835 FLIPS to 13212-13222 (hit); 9.18a t515 promotes WRONG box 13261-13269 (1 pip off golden 13250-13260) — the expected 13252-13260 sits rank 3. Net +1 box@1 at cd00d0be, +0 net at cd14f5fc (2 flips offset by losses elsewhere). VERDICT: FAILS keep rule at both revs — s.34.5 broken on level (-3/-4 > -1) and clutter (6.00/6.33 > 5.0), s.41.3 inapplicable (clutter up), plus OFF-id broken at cd00d0be. Not a clutter-only fail (s.43.6 reporting clause does not apply cleanly); suite leg is the one green leg. If the Lead keeps it anyway for the suite fix, K3-K5's provisional suite debt is cured but M1 pays level -4 and clutter 6.00.
- 07:36Z box_prio v3/v4 + s.42.5 famoff arms verified (own scorer, cache-only). v3 bxprio_on@afe99034: .076(9/119)/.053(4/76)/.098(19/193) clutter 6.33 - reproduces C1_M1 row 26 exactly; FAIL confirmed (level -2, clutter breach). v4 bxtauprio_on@c14060cb: .034(4/119)/.079(6/76)/.104(20/193) clutter 5.00 - reproduces row 27 exactly; FAIL confirmed (target box -3). All 4 box_prio forms rejected correctly. s.42.5 freeze-choice arm famoff_on (K5 minus fam_budget+fam_caps, box_score_pick kept): a7f35026 and e1edc511 give identical rows .067(8/119)/.053(4/76)/.067(13/193) clutter 5.67 - vs kept .059/.079/.104: box +1, level -2, line -7 (falls BELOW v0 .093), clutter +0.67 over gate. Suite on famoff_on@e1edc511 config: 72/72 PASS - removing fam flags cures the 7 fixtures as expected. Net: famoff trades the suite debt for worse M1 on every leg (line -.037 vs v0, clutter breach). famoff_nosup_on@e1edc511 (also box_score_pick OFF) filling - 82/576 runs so far.
- 07:38Z famoff_nosup_on@e1edc511 (s.42.5: fam OFF + box_score_pick OFF) now full 576 runs: .042(5/119)/.053(4/76)/.073(14/193) clutter 5.00 - strictly worse than kept on box AND line; the famoff choice rows are all M1-worse than the kept config (kept .059/.079/.104 cl5.00 suite65/72; famoff .067/.053/.067 cl5.67 suite72/72; famoff_nosup .042/.053/.073 cl5.00).
- 07:41Z box.level_edges (R43 queue / R44 s.44.3 handoff pending) - BOX-LAB probe pair c1r_p_base/c1r_p_lev pre-measured: @9d76b883 zero-delta on all M1 (box 7/7, clutter 5.00); @e1edc511 box -1 (7->6), else flat, clutter 5.00. No box@1 gain at either rev - consistent with s.44.3's deeper finding that the generation gap is a missing TRIGGER (51/51 no-edge goldens have zero pivot confirmations in buildup), not a missing edge source. flag provenance: p_lev = kept K5 + box.level_edges=True only.
- 07:52Z FAMCTX salience.fam_context (R44 s.44.2) @88438120 - full s.43.6 verification, pre-verdict. Provenance clean (off=K5 set + fam_context OFF; on adds fam_context=True only). M1: box 7->7 (target NOT up), level 6->4 (-2 exceeds allowance), line 20->19 (-1), clutter 5.67 >5.0 (76/179 <=5.0). OFF-id vs lnfloor_on@75a9650c: objects 1725/1728 (3 diffs), cand_log 621/1728 - the 88438120 rev inherits cd00d0be's unconditional cand_log writes + the same 3-run object delta; OFF-identity leg fails. Suite on famctx_on config (unmodified fixtures): 72/72 PASS - the context-family split cures the 7 fixtures exactly as designed (CONTEXT_RANGE leaves the box slot). VERDICT: FAILS keep-rule - target not up, level -2, clutter breach, OFF-id broken; the suite leg is green. Per s.44.2 contingency (clutter>5.0) a CONTEXT_RANGE-births-OFF sibling arm may follow.
- 07:55Z OFF-id diff anatomy at 88438120 (and same signature at cd00d0be): the 3 object-diff runs are 2012-04-04 w1=1140 (panels 9.25a/b/c, same day) - one BOX whose 'why' label changed cluster_range->congestion_scan; geometry/state/score identical. The 1107 cand_log diffs are the congestion_scan candidate entries now logged unconditionally (s.44.3's bar-driven trigger landed in this code lineage). So OFF-identity fails literally on objects+cand_log, but the underlying drawn-object behavior is unchanged apart from one birth-reason label.
- 08:08Z FAMCTX2 fam_context+famcap_context_range=-1 (R44 s.44.2 contingency) @4dcc44d7: M1 box 7->8 (+1 target UP), level 6->4 (-2), line 20->18 (-2), clutter 5.67 (79/179 <=5.0) - FAILS s.34.5 on TWO non-target families and clutter; s.41.3 inapplicable (clutter up). Suite on ON config: 72/72 PASS. OFF-id vs K5 parent: same 3-obj(label-only congestion_scan rename)+1107-cand_log diffs as 88438120. VERDICT: FAIL - both fam_context forms fix the suite but cost M1. Scoreboard of suite-curing options (all independently measured): kept K5 .059/.079/.104 cl5.00 suite65/72 | box_prio-v2 .067/.026/.098 cl6.00 suite72/72 | famctx .059/.053/.098 cl5.67 suite72/72 | famctx_nocr .067/.053/.093 cl5.67 suite72/72 | famoff .067/.053/.067 cl5.67 suite72/72 | famoff_nosup .042/.053/.073 cl5.00.
- 08:10Z congestion trigger probes @4dcc44d7 (pre-official-AB, s.45.2 fix pending): c1r_p_cong (cong_trigger N=6 band<=4ABR) box@1 9/119 .076 = +2 vs kept parent, level/line/bracket flat, clutter 5.00 - reproduces BOX-LAB's claim exactly. c1r_p_cong_lev (+level_edges) box flat 7 - snapping loses the gain. c1r_p_cong_k3 (h_abr 3.0) box flat 7. If kept after the flag-gating fix this is K6: box .076 vs v0 .134 (-7 hits).
- 08:23Z s.45.2 leak re-check at 30486c39 (the cong_trigger A/B hash): STILL LEAKING. cong_off vs lnfloor_on@75a9650c = objects 1725/1728 (same 2012-04-04 BOX why-label cluster_range->congestion_scan on 9.25a/b/c), cand_log 621/1728. The flag-gating fix has NOT landed at this hash - K6 cannot be declared on it until flag OFF is clean. Separately the cong A/B M1 reproduces BOX-LAB: cong_on (h_abr 5.5) and cong40_on (4.0) both box@1 7->9 (.076), level/line/bracket flat, clutter 5.00 - target +2 with zero collateral; pending only the OFF-id leg. jstruct v2 (structure-only joint cap, s.43.4.2) reproduces build-lane FAILs exactly: cap4 lvl-4/line-4/cl5.33; cap3 lvl-3/line-4/bracket-7/cl5.33.
- 09:04Z K6 box.cong_trigger @df79ade3 (post-s.45.2 fixed hash) - full verification pre-verdict: s.45.2 FIX CONFIRMED, cong_off vs lnfloor_on@75a9650c = 1728/1728 objects+cand_log+events identical (leak gone). M1: cong_on (h_abr 5.5) and cong40_on (4.0) both box@1 7->9 (.076, +2 target UP), level/line/bracket flat, clutter 5.00 (BOX rec .111 at k5.5). Suite on cong_on config: 65/72 - same 7 named fam-flag fixtures, ZERO new failures from cong_trigger. Provenance: cong_trigger False->True; cong_on also carries cong_h_abr 4.0->5.5 (BOX-LAB's recommended point; same M1 row). VERDICT: passes every s.34.5 leg incl OFF-id at the fixed hash - CONFIRMED pending the build lane's formal keep. jstruct v2 FAILs reproduced (cap4 lvl-4/line-4, cap3 lvl-3/line-4/bra-7, cl 5.33 both).
- 09:14Z K6 box.cong_trigger @df79ade3 KEPT 09:08Z - independently CONFIRMED, every leg: (1) M1 .076/.079/.104 cl 5.00 - box 7->9 +2, zero losses; (2) flipped goldens exactly 9.4b t815 + 9.48b t705, both miss->hit, zero hit->miss; (3) OFF-id vs lnfloor_on@75a9650c 1728/1728 clean (s.45.2 fix verified); (4) suite 65/72 same-7 zero new fails; (5) defaults-flipped engine m1_v1@9acaa206 reproduces cong_on row identically (.076/.079/.104 cl5.00) - defaults flip is faithful. fcjs arms (s.45.3.2) reproduce C1_M1 rows 34-35 exactly: fcjs4 .076/.026/.083 brk-9 cl5.67; fcjs3 .076/.066/.088 brk-15 cl5.67 - FAILs confirmed, both OFF. Round keeps now K1-K6; freeze candidate = defaults engine 9acaa206 per s.45.4.
- 09:26Z s.46.4 leak-ledger (leak = level_edges _propose_window narrowing + unconditional congestion_scan cand_log writes; signature = cand_log diffs + single BOX why-label flip on 2012-04-04). Hashes verified CLEAN: cd14f5fc (bxprio_off 1728/1728), 75a9650c (K5 OFF-id clean), df79ade3 + 9acaa206 (post-fix). Hashes carrying the leak: cd00d0be, afe99034, c14060cb, a7f35026, e1edc511, 69cda24a, 88438120, 4dcc44d7, 30486c39. Object-level footprint is one why-label only (cluster_range->congestion_scan, 9.25a/b/c); cand_log footprint ~1107 runs. Verdicts measured on leaky hashes - ALL are FAILs or zero-delta rows: box_prio v2/v3/v4, famoff/famoff_nosup choice rows, famctx both forms, jstruct v2 both caps, fcjs both caps, cong A/B first pass @30486c39, c1r_p_* probes. Jointcap hashes (10c34e28/fbb3a173) are obj-clean vs their K4 parent (cand_log diff only, likely fam_total_live-era logging). NO keep verdict rests on a leaky hash: K1-K5 all verified pre-leak with their own OFF-id 1728/1728; K6 verified post-fix. Per s.46.1 every rejection stands (margins >=2 hits, leak symmetric across arms).
- 09:40Z freeze-candidate equivalence: m1_v1@9acaa206 (defaults-flipped engine) vs cong_on@df79ade3 = 1728/1728 runs identical on objects+cand_log+events - the defaults flip is byte-faithful, stronger than the build lane's 5/5 spot check. If STABLE lands at 9acaa206 the frozen engine is exactly the verified K6 configuration.
- 09:56Z wick-density probes (s.46.3, pre-handoff): c1r_p_dens@0a100806 = K6 + box.cong_density -> M1 identical to K6 (.076/.079/.104 cl5.00) - density edges pick the same winners, zero-delta. c1r_p_dens_q@13b3f53d = K6 + cong_density + dens_mode='q' -> box 9->7 (LOSES the K6 gain) but level 6->7 (.092): FAILs s.34.5 on target. As measured, neither density form is a keep: dens inert, dens_q trades away the cong hits.
- 11:00Z FREEZE VERIFIED: on-disk code_hash == 9acaa206c8d386dc (snapshot restore confirmed). Live 3-panel spot check (9.1a/b/c) byte-identical to cached m1_v1@9acaa206 runs. Unmodified suite on frozen defaults: 65/72, exactly the seven fam_budget fixtures (pullback_end_box_birth, range_box_double_top, false_break_wick_keeps_edge, break_close_beyond_edge, tease_vs_proper_break_class, tf_relabel, reanchor_on_new_double_top). No K7.
- 11:00Z GATE_PACK_C1_9acaa206.md generated by own scorer (m1_row.py): box .076 -0.069 [-0.142..-0.003]; level .079 +0.039 [-0.033..+0.117]; line .104 +0.015 [-0.040..+0.070]; bracket .341 -0.015 [-0.172..+0.134]; clutter med 5.00 (v0 9.00), 90/179 <=5.0; diags BOX rec .111 prec .044 | PL .114 | LC .188 | LTF 0/1. K1-K6 CONFIRMED; rejected-arm table + leak ledger + no-edge census incl.; status block filled.
- 11:00Z Superseded draft GATE_PACK_C1_75a9650c.md (K5-config, pre-R48) quarantined to evalcheck/_quarantine/; GATE_PACK_C1_9acaa206.md is the pack of record.
- 14:27Z E4 done: GATE_PACK_C1 carried-debt line corrected per R49 s.49.1 ('box -110 misses' -> '7 hits short of v0, 9 against 16 of 119').
- 14:43Z K7 marker.off @66f596dc (A/B bmoff_on vs ctxy_off): CONFIRMED under playbook 3.2. Own scorer: box 9->9 =, level 6->7 (+1), line 20->20 =, bracket 29->29 =; clutter 5.00->4.67; margin 90->103 (+13>=+5); OFF-id vs m1_v1@9acaa206 1728/1728 obj+cand_log+events; suite unmodified 65/72 named-seven (pullback_end_box_birth, range_box_double_top, false_break_wick_keeps_edge, break_close_beyond_edge, tease_vs_proper_break_class, tf_relabel, reanchor_on_new_double_top) - ZERO cured, confirms s.53.2 reconcile. bmday alt FAILED: margin +4 < +5 (correctly rejected).
- 14:43Z K8 box.cong_pivedge @81f7503f (pedg_on vs pedg_off on K7 parent): CONFIRMED under playbook 3.1. Own scorer: box 9->10 (+1 target UP), level 7->8 (+1), line 20->20 =, bracket 29->29 =; clutter 4.67->4.67; margin 103->101 (-2, not a 3.1 leg); OFF-id 1728/1728 same-hash vs c1r_p_base AND cross-hash vs bmoff_on@66f596dc; suite 65/72 same named-seven, zero new. Chain: ltfcap_off@759d9036 == pedg_on 1728/1728 (K8 default flip consistent).
- 14:43Z K9 salience.rate_label_tf=2 @759d9036 (ltfcap_on vs ltfcap_off): CONFIRMED under playbook 3.2. Own scorer: box 10->10 =, level 8->8 =, line 20->20 =, bracket 29->29 = (M1 flat); clutter 4.67->4.33; margin 101->114 (+13>=+5); OFF-id vs pedg_on@81f7503f 1728/1728; suite 65/72 named-seven zero-new. Chain: c1r_p_base@ee2cbf12 == ltfcap_on 1728/1728 (K9-as-default consistent). Parent chain end-to-end: 9acaa206 -> K7 -> K8 -> K9 all identity-clean.
- 14:45Z E2 null review (evalcheck/_null_review_c2.py, own seed 20260923, golden-tau visibility window): PLAIN shift null reproduces BOX-LAB direction - no-edge piv .711 vs .289 KEEP, cext_trig .368 vs .289 KEEP, sess72 .158 vs .079 KEEP-ish, rnd10 .395 AT p95, prior .053 vs .028. DENSITY-MATCHED null (shift confined to buildup->tau traded range): piv .711 vs null .715/p95 .763 -> does NOT beat; cext_trig .368 vs .472/.528 DROP; sess72 .168 vs .211 DROP; sess360 DROP; union .868 vs .921 DROP; only rnd10 .395 vs .368 marginal. All-108 same direction: piv .787 vs .770/.806 fail. CIRCULARITY: close_ext on golden's own window was circular as suspected; on K6 trigger windows it drops to chance (.368 vs dense .528) - confirmed. CAVEAT: my dense null is uniform-inside-range (stricter than BOX-LAB's +-0.5*room local perturbation under which piv passed .585); the KEEP/drop verdict for piv is null-design-sensitive. Net: pivot coverage is near-ubiquitous inside the traded range -> viable as candidate GENERATOR but carries no discriminative evidence; any registry lever needs a which-pivot selection rule and must prove on M1.
- 15:06Z E3 F1 identity (independent, own runner _f1_identity_c2.py + _f1_speed_spot.py): v2 merge candidate (_scratch/perf/v2 = K9-era engine.py+swings.py + perf hunks, F3 retained, params file identical to disk) -> TUNE 1728/1728 byte-identical vs ee2cbf12 caches (c1r_p_base+lnsf42 pair; canonical objects+cand_log+events). 35-day DESIGN continuous EURUSD 2019-01: canonical EQ at end, crossover day~20 (patched slower <day15 overhead, faster after: d24 189v131, d27 188v141, d33 179v140; consistent with build's 55d day50 118v12). Suite on patched modules via PERF_DIR injection: 65/72 same named-seven. CAUTION for merge: perf/ (v1) files are pre-F3 stale - merge must copy v2/ only; v2 files are LF-ending (hash will differ from a CRLF write - fine, just record actual). VERDICT: F1 merge identity CONFIRMED on current config; may land.
- 15:06Z E2-extended (s.56.6.3): BOX-LAB r1_hyp.py reproduced exactly (107 pairs, seed 56) and seed-777 rerun gives identical verdicts - nulls stable. KEEP: H5 recency +14.4 (huge), H4 prior_leg +0.59, H10 tall +1.19, H6 height_r +0.014, H1 press +0.078 thin, H3 probes +1.08 thin. DROP: H2 flat_ema (reversed), H7 overlap, H8 wick-tip, H9 rnd50. CAVEAT: H5's feature uses the golden's author t1_drawn (post-tau information) - as evidence it says 'author boxes extend past tau'; a causal implementation must proxy it (latest open structure), not read the golden's end. Thin KEEPs are weak evidence; H5/H4/H10 carry the table.
- 15:08Z STABLE C-2 4c2df34d7a2a8ee3 VERIFIED post-merge: on-disk code_hash recomputes exact; engine.py+swings.py == _scratch/perf/v2 (EOL-normalized); snapshot dir present with SHA256.txt; 5-panel live spot check == c1r_p_base@ee2cbf12 byte-identical; my prior 1728/1728 on v2 files carries to merged state; unmodified suite on merged disk 65/72 same named-seven. F1 merge stands: STABLE C-2 = 9acaa206 + K7 + K8 + K9 + F1.
- 15:10Z Ceiling-kit review (build lane F-B3, low-prio item kept by s.56.1): PASS. Blind - 9.19a.png inspected: candles+EMA25+faint 00/50 grid, bars stop at dashed tau divider, zero engine/author ink, no titles. Seed 20260922 reproduces the 10-panel list exactly (4EU/3US/3AS x 5sparse/5busy, Asia busy = single qualifying panel 9.62a, all >=2 M1 fams). Axis JSON carries plot rect + px<->(time,price) + bar_open_times + tau - sufficient for scoring. Key held separately in _ceiling_key/.
- 15:16Z GATE_PACK_C2_4c2df34d.md generated (own scorer): STABLE C-2 box .084 (10/119) -.064 [-.137..-.001], level .105 +.072 [-.011..+.167], line .104 +.015 [-.040..+.070], bracket .341 -.015; clutter 4.33 (v0 9.00), margin 114/179; diags BOX rec .102 prec .036 PL .114 LC .208 LTF 0/1. Flipped goldens named per keep (K7 9.64c MINI_LEVEL; K8 9.2b BOX + 9.49a LEVEL_CARRIED; K9 none). Rejected arms re-measured and reproduce C1_M1 exactly: bmday .076/.079/.104 margin+4; ctcv_loose .101/.053/.088 (lvl -4); ctcv_wraps .092/.092/.093 (lvl -1, line -2); lnsf42 .084/.092/.083 (line -4). Pack records C-2 end state under R56 (freeze withdrawn, C-3 = box research).
- 15:18Z H5-causal re-test reviewed independently (_h5causal_review.py on r_dataset v2, 115 cells -> 12 paired): every BOX-LAB direction reproduced (recency -64.7, in_band -26.8, touch -22.2, dist_edge -2.25, px_in_box +0.58, ema_slope +0.55, probes_bot -2.58; all beat 200-draw label-shuffle null). EXTRA in my run: age_bars -72.0 BEAT; prior_leg_abr +0.40 BEAT (BOX-LAB called it flat - discrepancy, thin); h_rel_day +0.017 marginal (p95 +0.014). CAVEATS: n=12 thin; a second weaker null (random-pick) is also beaten so significance is robust to null choice but not to n; px_in_box/dist_close_edge are price-position feats - the right-cand label is defined by golden geometry and authors draw near price-at-tau, so these are near-tautological as 'author intent' evidence though still usable as causal features for selection. overlap_ratio degenerate (all-zero diffs).
- 15:20Z Build-lane selection sim on r_dataset reproduced independently: over live cand pool (pending/born at tau) per cell - argmax score_last = 1/115 hits; min age_bars = 15/115; youngest+touches = 16/115 (~v0's 16). EXTRA: argmax score on live pool NEVER equals the incumbent pick (0/115) - the dwell/hysteresis incumbent is not the best-scored live cand; consistent with 'stale envelope holds the slot'. Caveats stand: counterfactual pick != drawn object (clutter/floor/incumbent competition unpriced), cells conditioned on live pool existing. Supports the A1 current-episode scope direction but the birth-slot simulation is the real test.
- 15:33Z A1 spec (boxlab REQUESTS.md ~16:55Z: salience.box_live_scope, cand.t1>=now-30 or span-contains-now, score order unchanged) - independent falsify-check on r_dataset v2: (1) direction CONFIRMED - 45/61 covered-missed cells hold a LIVE right cand with recency<=30 at tau (build lane's 49 incl. wider eligibility - same ballpark); right cands ARE current while incumbents are stale. (2) BUT the '+6-10 box@1' ceiling is NOT readable from cand_log: only 7/45 cells have a SCORED eligible right cand (scores 4.03-16.02; 5 top their scored pool) - the remaining ~38 right cands are pending=never scored. A1's true effect = making them scoreable at the birth bar; conversion depends on the live score fn vs 5.0 floor + eligible rivals, not on cand_log. (3) scored-argmax over eligible pool hits right cand in 5 cells only - 'score order unchanged' may still lose. Net: A1 worth an A/B but its expected gain is honest 'unknown, bounded by ~45 cells', not +6-10.
- 16:12Z A1 lvs arm @c9f240f8 (salience.box_live_scope K=30) pre-verdict measured: lvs_on = .084/.105/.104/.341 cl 4.33 margin 114/179 - byte-flat vs lvs_off AND vs K9 parent row. OFF-id lvs_off@c9f240f8 vs c1r_p_base@ee2cbf12 = 1728/1728 obj+cand_log+events CLEAN (flag inert OFF). Confirms build's 15:43Z arithmetic: only ~1/309 BOX births are stale-at-birth - cand-side scope cannot move M1; the staleness lives in incumbent OBJECTS. If build lane proposes A1-v2 (incumbent-age contest), that is the variant matching the evidence.
- 16:13Z A3 ranker review (r3_fit.py + c1_runs/r3_*.txt): (1) liveness4 model REPRODUCES exactly - CV cell@1 18/67=.269 vs within-cell shuffle p95 .254, score_last baseline 5/67 (I bypassed the gate and re-ran the same pipeline). (2) BUT current r3_fit.py as committed reports 'A3 not viable': its in-script per-feature gate drops ALL 7 causal feats (best neg_recency .149 vs p95 .149 - argmax-level, no single feat separates). The logged PASS came from the un-gated model; the two conventions disagree and the gate is defensible (features separate on MEAN not argmax). (3) PASS margin is 1 cell (.269 vs .254). (4) boxlab's own 15:58Z honesty pass: only 3/18 hit cells have a right cand clearing the 5.0 birth floor; strict ruler label (label_golden, n=14) model 1/14 vs baseline 3/14 - label_edge is more generous than the ruler and the model INVERTS under it. Net: A3 is real but thin and fragile; if used, it must be as birth-order under an explicit disclose, and the strict-label inversion needs a second look before any engine arm.
- 16:13Z r57_causal.py review (boxlab, c1_runs/r57_causal.txt): methodology sound - PAIRED vs VS-REST designs + band-overlap density-aware null all reasonable. ONE BUG: bars_since_in_band is tested RAW (upper-tail) where lower-is-better - obs -26.5 < null p5 (~-10) actually BEATS the null on the low side but is printed 'drop'. Under the negated convention used for recency/touch it is a KEEP (consistent with the 15:10Z pre-test listing it KEEP). Does not change the liveness-cluster conclusion (5 other feats KEEP cleanly). Survivor audit holds: H4c/H6c/H10c all thin-to-razor, H1c/H3c drop, H2c/H7c dead. Caveat: PAIRED null draws pseudo-right from 'others' which INCLUDES the engine pick (delta 0 dilution, minor at ~80 cands/cell).
- 16:22Z yng_on@97061ac5 (A1v2 box_young_first) + lvb_on@29de0689 (box_live_at_birth 0.5ABR) REJECTIONS CONFIRMED on own scorer: both M1-flat .084/.105/.104/.341 cl 4.33 margin 114 = parent row exactly; diag BOX prec shifts slightly (yng .032, lvb .037 vs parent .036) proving the flags DO fire but produce zero M1 delta. OFF-id: yng_off and lvb_off both 1728/1728 obj+cand_log+events vs c1r_p_base@ee2cbf12. A1 CLOSED correctly (2/2 inert); lvb flat as logged. Selection-side on candidates exhausted - consistent with R59's read.
- 16:41Z A4v1 a4_on@b1d94617 (box_live_birth): INERT CONFIRMED - M1 = parent row exactly (.084/.105/.104/.341 cl4.33 margin114); canonical identity claim consistent. A4v2 a4b_on@54bd315b (box_edge_birth asymmetric contest): REJECTION CONFIRMED - box@1 .067 (8/119) = -2 vs parent, exceeds -1 allowance on target fam; level/line/bracket flat, clutter 4.00 (margin gain irrelevant under gen rule). OFF-id: both OFF arms 1728/1728 obj+cand_log+events vs c1r_p_base@ee2cbf12. A4 contest line correctly closed. Selection-side class now exhaustively falsified on TUNE: scope flat, youngest flat, liveness-gate flat, contest -2.
- 16:52Z Anchoring-framing correction (build 16:48Z) reproduced on r1_table+r_dataset join (117 pairs): pick-vs-golden band-IoU med: CONTEXT_RANGE .038, BOX .187, RANGE_OPEN .469 (n=2) - direction CONFIRMS 'wrong anchor, right height': height-ratio med ~1.0 all types (CR .98, BOX 1.00), center-offset ~1.5p (their '15.1p' = points, same value). My IoU .038 vs their .122 = union-vs-containment/pair-set convention (117 golden-rows vs 134 cell-pairs); qualitative claim holds: envelopes are same-height objects anchored to a DIFFERENT episode's structure, not too-wide. Supports 'anchoring = level-pair judgment' diagnosis over 'width'.
- 17:04Z Phantom-envelope check (16:57Z boxlab claim) reproduced with corrected units: over ALL 80 CONTEXT_RANGE-picked cells, band-IoU vs ANY scorable BOX golden in panel: med .011, only 30/80 >=.3 (vs BOX picks 25/34 >=.3, med .565; RO 1/1). Their 6/61 was on the stale-picked subset - same direction, broader population. CONFIRMS: when a CONTEXT_RANGE tops the box-family slot it is typically geometrically unrelated to anything the author drew in that panel; when a BOX tops it usually sits on golden structure. The asymmetry is real and large (med IoU .011 vs .565).
- 17:08Z §60.5.1 BOX miss decomposition DONE (own code, ruler's own components, c1r_p_base@ee2cbf12 = parent/K9 world): 119 box-family goldens (108 BOX + 8 RANGE_OPEN + 3 CONTEXT_RANGE scored) -> rank-1 hits 10 (9 BOX + 1 RANGE_OPEN, matches box@1 .084). 109 misses partition: edges-ok-but-window-fail = 0 | window-pass-but-edges-fail = 69 (60 via coverage-fallback, 9 via true containment IoU>=.5) | both-fail = 38 | no-candidate = 2. => 100% of misses fail on PRICE EDGES; time/episode window never the sole failure. On the 69 window-passing misses the pick's worst edge is median 21 pips off the golden edge (p25 13 / p75 31) - wrong price anchor, not a marginal miss. pick types on misses: CONTEXT_RANGE 80, BOX 21, RANGE_OPEN 6, none 2. vs best-coverage live object (any rank): edges-fail-with-window-pass 75, both 32, none 2. detail evalcheck/_miss_split_detail.txt; code _miss_split_c3.py. Interpretation: consistent with phantom-anchor finding - incumbent box ink lives through the right episode window but is pinned to wrong price levels; the gap is edge placement, not liveness.
- 17:17Z s.60.3 HYBRID independently measured (own code evalcheck/_hybrid_check_c3.py, NOT the build lane's script; cache-only, a4b_off@54bd315b + m1_v0@63c771d6). v0 box objects taken UNCHANGED - stated and enforced by construction. Pre-check: a4b_off@54bd315b == c1r_p_base@ee2cbf12 (C-2 defaults) on 1728/1728 runs incl events. HYBRID row: box@1 .134 (16/119, =v0 exactly, CI +0.000) | level@1 .105 (8/76 =v1) | line@2 .104 (20/193 =v1) | bracket@1 .341 (29/85 =v1) | clutter med 5.67 | margin 77/179. Sanity rows through same machinery: v0 .134/.066/.093 clutter 9.00 (matches pack); v1-pure .084/.105/.104 clutter 4.33 (matches K9 parent). s.60.3.2 GATE: box>=16 PASS, others d=+0 PASS, clutter 5.67>5.0 FAIL -> s.60.3.3 path. Extra ink for BOX-LAB: v0 box family adds med +4.0 objects/panel (mean +4.16, p75 +5, max +9) vs v1 box family; margin cost -37 panels (114->77). Build lane's own count not yet posted - will compare when it lands.
- 17:18Z s.60.3 hybrid build-lane count (17:17Z) CONFIRMED - every number reproduced by my independent run: box@1 16/119 | level 8 | line 20 | bracket 29 | clutter 5.67 | margin 77/179 | ink +4.0 med/+4.16 mean. Composition claim verified on all 198 panels (they sampled 30): v0 box family = BOX 1113 (89.7%) + RANGE_OPEN 127 (10.3%), ZERO CONTEXT_RANGE, med 6.0 objs/panel p90 8. Gate s.60.3.2: FAILS on clutter 5.67>5.0 -> no port; s.60.3.3 ink number +4.0/panel handed to BOX-LAB confirmed. rows artifact evalcheck/_hybrid_rows_evalcheck.pkl.
- 00:46Z s.61.4.2 INK BUDGET published (VERIFY_LOG + REQUESTS.md): parent C-2 4c2df34d (a4b_off@54bd315b == ee2cbf12 1728/1728 == 4c2df34d via F1). Ruler counts every window-intersecting object incl. dead. UNIFORM: +1/panel -> med 4.67 margin 106 SAFE; +2 -> med 5.00 margin 92 (zero headroom); +3 -> 5.33 FAIL. Per-panel headroom med=1. CONCENTRATED: 40 panels x +6 -> med ~4.67 worst 5.00. Design budget: <=+1 obj/panel average, or births concentrated on <=~40 panels. v0's 6/panel everywhere = the 5.67 failure mode.
- 00:59Z evb_on@be204b98 (ev-route port, salience.ev_route_box) INDEPENDENTLY VERIFIED: FAIL s.3.1 - own scorer reproduces build's 00:57Z verdict. box@1 .059 7/119 (-3 vs parent) | level .092 7/76 (-1) | line .109 21/193 (+1) | bracket .353 30/85 (+1) | clutter med 6.00 (>5.0) | margin 71/179 (parent 114, -43). OFF-id evb_off==c1r_p_base@ee2cbf12: 1728/1728 obj+log+events. Live box-family objs/panel at window end: med 6.0 mean 6.28 (parent 1.0/2.10) - port reproduces v0's ~6-box ink, not the ~1-live design intent. Flipped box-family goldens: +5 gained / -8 lost (13 total; build logged 12 +5/-7 - delta is my RANGE_OPEN loss at 9.14a t530 counted at family level). Mechanism matches build's read: newest-ev-box +100 outranks incumbent CONTEXT_RANGE carriers; pullback route = net -3. Awaiting variant 2 (double-only, ev_route_pullback=False, stated 00:57Z) on tree b07b8af4.
- 01:00Z evb_on suite (unmodified, on current tree b07b8af4 + ON params): 71/72 - the seven fam_budget fixtures CURED (event-route boxes take the box slot, CONTEXT_RANGE no longer blocks them); NEW failure test_tf_relabel (ev-box births interact with the tf-relabel expectation). Structurally confirms s.60.2: fixture debt and box gap are one problem - but M1 still fails on pick pollution + ink. Note: suite ran on tree b07b8af4 (build iterating past be204b98).
- 01:02Z evb2_on@b07b8af4 (variant 2, double-only: ev_route_pullback=False) INDEPENDENTLY VERIFIED: FAIL s.3.1 - box@1 .059 7/119 (-3) | level .092 7/76 (-1) | line .093 18/193 (-2) | bracket .329 28/85 (-1) | clutter med 5.67 | margin 80/179 (-34). OFF-id 1728/1728 vs c1r_p_base. Live box @end med 5.0/panel (parent 1.0) - still the v0-ink flood. Flips +6/-9 net -3 (gained 9.10a/9.13a/9.15b/9.41b/9.45a/9.4b; lost 9 incl RANGE_OPEN 9.14a). BOX rec .213 = v0 coverage achieved by the route births, but newest-ev-box rank-1 picks wrong AND now costs line -2. Both port variants exhausted (s.3.7): verbatim FAIL, double-only FAIL.
- 01:03Z evb2_on suite (unmodified, tree b07b8af4 + ON params): 71/72 - seven fam_budget fixtures cured again; sole failure test_pullback_end_box_birth EXPECTED (variant disables the pullback route the fixture encodes). Summary of the s.61.2 port as implemented: event births DO cure the fixture debt (structural confirmation that box gap == fixture debt) but the newest-ev-box rank-1 grant + ~5-6 live boxes/panel flood costs more hits than it gains. Both variants verified FAIL; awaiting build's next move.
- 01:15Z evb_on@65c8f635 (arm 3, SPEC-DEFAULT: propose->pool + best-score rank-1 grant) VERIFIED: materially inert but NOT byte-flat as build claimed. Own scorer: box 10/119 level 8/76 line 20/193 bracket 29/85 clutter 4.33 - identical to parent; margin 113/179 (parent 114, -1 panel). Canonical: obj diffs 18/1728 runs, cand_log diffs all runs (proposal logging), 4 LIVE ev-route objects at window end (panels 9.29c/9.44c/9.50b/9.50c) - 'zero born' is wrong; a few survive admission. cand_log funnel (60 panels): ev_pullback_end 279 proposed -> outranked 222/below_min 104/expired 241/cooldown 312/shadow 793; ev_range_double_* 490 proposed -> outranked 388/below_min 278/expired 424/cooldown 1665 - v1 admission kills the event stream at the generation boundary, same wall as the right-cand pool. Port closed: 3 arms FAIL/FAIL/INERT verified; missing piece = a birth-side seat mechanism.
- 02:24Z s.63.3 OPTION C PRICED (live-at-tau clutter, own code _live_clutter_c3.py, cache-only; defs: STRICT = state==ACTIVE at tau-truncated run end = on screen at decision | LOOSE = not-DELETED = ranker's world incl CLOSED; LABEL_TF counted when live; panel ink = mean over its golden taus, last-tau as sensitivity). STRICT: parent 2.00 margin166 | v0 2.67 margin150 | HYBRID 2.00 margin167 | evb_on 2.44 margin156 | evb2_on 2.33 margin160. LOOSE: parent 3.50/128 | v0 6.83/53 | hybrid 4.25/111 | evb_on 5.00/90 | evb2_on 4.78/96. READ: v0's 'ink' is dead-object residue - at any decision moment ~2.7 objects are on screen; the hybrid's v0-box stream costs ZERO extra live ink vs parent under strict-C (2.00 vs 2.00, margin +3). Under C the hybrid passes clutter trivially; even the loose form passes (4.25<5.0, margin 111~114). CAVEAT: C does not rescue the port arms' M1 - their box@1 -3 is a pick-pollution problem independent of clutter. T1 not computable from cache (offline replay; build verified its single ev-object live at tau 15/15 -> est live-ink ~parent+1). rows _live_clutter_rows.pkl.
- 02:47Z UIP arms @6d955783 INDEPENDENTLY VERIFIED (own scorer, cache-only): uip_on (strict lifecycle): box 7/119(-3) level 4/76(-4) line 22(+2) bracket 29 clutter 4.50 margin 100 - FAIL. uip2_on (ev_uip_persist, close-exempt): box 16/119 =V0 PARITY (+6) | level 4/76(-4) | line 23(+3) | bracket 29 | clutter 4.67 | margin 95/179 | births exactly 1.0/panel | live box@end med 2.0 (parent 1.0) - FAIL s.3.1b on level -4 (allowance -1). OFF-id evb_off@6d955783==c1r_p_base 1728/1728 obj+log+events. Suite both arms 71/72, sole failure test_pullback_end_box_birth (expected: UIP-rd spec has pullback route never writing; named-six cured). Level flip set (level@1): +9.40b / -9.40c,9.49a,9.56b,9.61c,9.64c. Box flips golden-level rank-1: +15/-9 net +6 =16 (build logged +19/-14 - different counting convention, mine reconciles with 10->16). NOTABLE: first arm to reach box parity at ~1 birth/panel and clutter PASS; the residual cost moved to the LEVEL stream (ev-box edges seed competing LEVEL_CARRIED + persistent slot suppresses level presence at tau - build 02:41Z mechanism).
- 03:10Z option-B PREP verified: v0box_off@8b67d0eb vs c1r_p_base@ee2cbf12 = 594/594 canonical identical (all available coverage incl tau rows), miss=0. flag salience.box_v0_family inert when OFF. A/B not run by anyone - Owner has not chosen B. R66 read; awaiting uip2_lvfree arms (s.66.3) for s.66.5 verification
- 03:33Z s.66.3 LVFREE arms @23504c93 INDEPENDENTLY VERIFIED (own scorer, cache-only, heavy_run). uip2_lvfree: box 16/119(.134)=V0-PARITY +6 | level 7/76(.092) -1 | line 20/193 0 | bracket 29 | clutter 4.33 =parent | margin 111/179 | births 1.0/panel | live-box@end med 2.0. uip2_lvfree_pb: IDENTICAL M1 row + identical flip set (pb-write = ZERO pick change on TUNE, +0/-0 vs lvfree). OFF-id: evb_off@23504c93 vs c1r_p_base = 1728/1728 identical (141 unshared). Params probed from pickle: lvfree={ev_uip,persist,lvfree=T,pb_write=F}; pb arm adds pb_write=T - match build s.3.6 statement. M1 KEEP-RULE s.3.1: BOTH PASS on my scorer (box up, level -1<=1, clutter<=5). SUITE DISCREPANCY: my unmodified tests/test_engine.py collects 72 -> BOTH arms 71/72, sole fail test_pullback_end_box_birth (persists even with pb_write=T; UIP persist object is not a BOX-type birth in fixture envelope) - s.66.3: 'a failing test_pullback_end_box_birth blocks a keep' -> BOTH BLOCKED on my run. Build logged 'suite 67/67' - NOT REPRODUCED here (72 collected); likely different test selection. Flag for Lead.
- 03:33Z s.66.5 OPTION-C rows for lvfree arms (live-at-tau clutter, _live_clutter_c3.py): uip2_lvfree STRICT 2.33 margin161 LOOSE 3.78 margin127 | uip2_lvfree_pb IDENTICAL (strict 2.33/161, loose 3.78/127) | vs parent strict 2.00/166 loose 3.50/128. Both arms pass C trivially.
- 03:36Z CORRECTION to 03:33Z suite note: suite on OFF arm (evb_off@23504c93 params = parent state at hash) = 65/72, failing the named SEVEN which INCLUDE test_pullback_end_box_birth (+range_box_double_top, false_break_wick_keeps_edge, break_close_beyond_edge, tease_vs_proper_break_class, tf_relabel, reanchor_on_new_double_top). So on lvfree arms pb is NOT a new failure - it is the parent's own residual, and the arms CURED the other six (71/72 vs 65/72 parent). Under 'no new test failure outside the known seven' BOTH arms PASS with suite strictly improved; under the literal s.66.3 clause 'a failing test_pullback_end_box_birth blocks a keep' they remain blocked (clause presumed pb passed on parent - it does not at this hash). Fixture diagnosis: under lvfree params the pattern births RANGE_OPEN/LEVEL_CARRIED/CONTEXT_RANGE, zero BOX-type objects -> assertion 'boxes' empty regardless of pb_write. Lead to rule on the clause's intent. Build's '67/67' still unexplained vs 72-test collection (off=65/72, arms=71/72 here).
- 03:52Z s.66.4 uip2_bs @c06365ce VERIFIED (own scorer, cache-only): M1 IDENTICAL to uip2_lvfree_pb (box 16/119, lvl 7/76, line 20/193, brk 29, clut 4.33, margin 111/179); flip lists byte-identical (+15/-9 same panels) = BYTE-FLAT picks on TUNE confirmed. OFF-id evb_off@c06365ce vs c1r_p_base 1728/1728 (141 unshared). Prereg +0..+5 -> landed +0 confirmed.
- 04:15Z s.68.3 V3 uip2_pbbirth @8361fe85 INDEPENDENTLY VERIFIED - FIRST ARM PASSING EVERY LEG: box 16/119(.134)=V0-PARITY +6 | level 7/76 -1 | line 20/193 0 | bracket 29 | clutter 4.33=parent | margin 110/179 | births 1.0/panel | live-box@end med 2.0 | OFF-id evb_off@8361fe85 vs c1r_p_base 1728/1728 (141 unshared) | SUITE OF RECORD 72/72 ALL PASS - test_pullback_end_box_birth CURED (pb cand births UIP obj as BOX at v0's idx-t0a>=3 gate; named six stay cured). Params probed: {ev_uip,persist,lvfree,pb_birth=T; pb_write absent - V2 retired per R68}. M1 keep-rule + suite leg both PASS on my scorer. Ready for STABLE C-3 verification + GATE_PACK_C3 when build logs the keep.
- 04:29Z STABLE C-3 1a5502129b4c1554 FREEZE VERIFIED (s.68.4/s.70.2): (1) snapshot _scratch/freeze_candidates/1a5502129b4c1554 recomputes to stable hash exactly (kernel.py postdates fold - added to V1_FILES during A1). (2) params fold confirmed: ev_uip+persist+lvfree+pb_birth=T, pb_write/buildstart/box_v0_family=F. (3) default-engine run vs measured arm uip2_pbbirth@8361fe85 = 198/198 canonical identical (objects+cand_log+events) - ALSO covers A1 kernel extraction as identity-clean (disk mid-migration, hashes 18ea3147->402af8c9 during run, all panels still identical). (4) suite of record on folded params: 72/72. GATE_PACK_C3_1a550212.md written - M1+CIs vs v0, option-C rows, suite, flip lists.
- 04:30Z GATE-TIMING NOTE (neutral): MIGRATION A1 landed 04:24Z before s.70.3's two gates formally closed - my C-3 verification logged 04:29Z and ARCH_REVIEW.md is still unwritten (review in progress). Substance unaffected: my independent 198/198 identity check corroborates A1 as a clean pure-move. Process flag only, no rework needed.
- 04:54Z ARCH MIGRATION identity checks (s.70.3 - OFF==parent byte-for-byte per step): cumulative disk-vs-uip2_pbbirth@8361fe85 canonical check = 198/198 objects+cand_log+events identical at hash 350b5b69 (stable during run), covering A1 kernel.py + A2 objects.py/ObjectStore + A3 pipes.py shells + A4 salience.round() stage split. (Earlier pass at 04:27Z already verified A1+mid-A2; an intervening run hit a transient mid-edit AttributeError in salience.py at 04:39Z - normal during A4, resolved.) Each landed step keeps canonical output byte-identical; will re-verify at each further landing.
- 05:25Z s.71.4 DONE - Owner's two tasks on C-3 prepared: (a) M2 blind pack built to owner_pack/: 102 items = 48 engine top-k objects (uip2_pbbirth@8361fe85, deduped (panel,id) - first build had an id-collision bug collapsing to 65 pool, fixed; pool 773: box180/lvl201/line392 -> sampled box11/lvl12/line25) + 30 golden controls + 24 audited negatives; all rendered blind via plausibility.render_item price-space path, 0 undrawable swaps; manifest.jsonl public, ANSWERS.md blank, HUONG_DAN.md Vietnamese; truth key OUTSIDE pack at evalcheck/_owner_judge_key/m2_c3_key.json (engine_hit 11 / engine_fp 37 / golden 30 / negative 24); seed 20260923, ~40-50min judging time. (b) ceiling_kit/: inspected - panels+tau divider only, zero engine objects -> engine-independent, NO refresh needed.
- 05:37Z STABLE C-3 + MIGRATION A1-A5 - FULL identity check extended: disk @2d497427 (C-3 + A1-A5 landed, A6 reverted per ARCH_REVIEW BLOCK) vs uip2_pbbirth@8361fe85 = 623/623 canonical identical INCLUDING all tau-truncated runs (was 198/198 full-window; now covers every cached file). Hash stable throughout the run. The folded defaults produce exactly the measured arm on every scored and unscored slice.
- 06:58Z L-1 V1 l1_close@8b330117 (line.over_veto_mode=close_only + line.rank=young_a): FAILED on own scorer - line@2 19/193 (.098, -1 vs parent 20, target >=21); level@1 2/76 (.026, -5 BREAKS <=1 allowance); box/bracket flat; clutter med 4.00 (margin 112/179); OFF-id evb_off==uip2_pbbirth 1869/1869 miss 0; births flat (line 5.72 vs 5.58); line cands med 54->78 (+44%, bounded); flips +7/-8.
- 06:58Z L-1 V2 l1_soft@8b330117 (over_veto_mode=soft + rank=young_a): FAILED - line@2 14/193 (.073, -6); level@1 2/76 (-5); box/bracket flat; clutter 4.00 (margin 112); line cands med 54->96 (+78%); flips +6/-12. Both V1/V2 lose level -5 and line net-negative: young_a selection + relaxed legality did NOT move line recall up on TUNE.
- 07:56Z L-2 V1 l2_near@2e8a7007 (level.def_nearest): FAILED own scorer - level@1 4/76 (-3 > allowance, target >=8); line 19/193 -1; box/bracket flat; clutter 4.33; OFF-id evb_off==parent 1869/1869; level cands med 1313->456 (-65%, economy confirmed but cuts recall); flips +0/-3.
- 07:56Z L-2 V2 l2_near_ret24@2e8a7007 (+def_ret24_req): FAILED - level 5/76 (-2), line -1, clutter 4.33, cands med ->432; flips +1/-3.
- 07:56Z L-3 V1 l3_ink@66c6ea8a (line.reanchor_ink): FAILED - line@2 10/193 (-10!), level 4/76 (-3), clutter 4.00; sibling-restart kills incumbent touch count as build's note says; flips +3/-13.
- 07:56Z L-3 V2 l3_revise@66c6ea8a (reanchor_log=revise): INFO CONFIRMED precisely - ON-vs-OFF same-hash: objects 1869/1869 + cand_log 1869/1869 identical; events differ only by re_anchor->revise relabel carrying old+new geometry payload (3877 revise evts, 618/623 panels, 0 other deltas spot-checked).
- 07:56Z L-4 V1 l4_snap@66c6ea8a (line.anchor_snap=0.5tol): INFO recorded, no keep per spec - line 15/193 (-5), level 4/76 (-3), clutter 4.33, cands flat; M3 jitter metric pending Owner ruling so recall cost shown but stability benefit unmeasured.
- 08:13Z B1 VERIFIED (s.75.3.3 gate): disk a3b277d6 (=B1@89524e06 + R-1 pool_peak probe) vs uip2_pbbirth@8361fe85 parent - canonical 623/623 objects+cand_log+events (extended tuple incl score/priority/touches), miss 0, hash stable; suite of record on current defaults 72/72; static: pool_view returns [] under arch_v2=0 (no v2 state on OFF path), FamilyPipe __getattr__ guard present, pool_peak additive-only. B5 may proceed per gate.
- 08:13Z s.75.4 tree 2e8a7007 (A3 pickle-fix) independently verified: evb_off@2e8a7007 == uip2_pbbirth 1869/1869 canonical+cand_log+events miss 0 (via L-2 check); suite on that tree's params via L-arm runs exercised the same code. Fix is load-path-only as claimed.
- 08:23Z L-4 @15682ea3 (post lambda->bound-method repair): l4_snap identical to pre-repair measurement (line -5, level -3, cl 4.33, flips +3/-8, suite 72/72) - repair content-neutral confirmed. l4_promsnap: box 14/119 -2, level 3/76 -4, line -1, cl 4.00; suite 71/72 (same test_squeeze_between_line_and_ema new-fail as L-1/L-2 arms). Both INFO per spec; OFF-id 1869/1869 both hashes.
- 08:29Z s.77.4a PA-ATLAS baselines VERIFIED (_atlas_bl_verify.py): bl_tdlines_k2 line@2 29/193 cl 6.67 | bl_donchian_alt level@1 16/76 cl 10.33 | bl_darvas_n7 box@1 2/119 cl 0.67 - all reproduce exactly under my own scoring loop. Budget accounting identical to C-3 (their global max_objs=6 cap never binds: cap6==nocap on every family). Prefix invariance 15/15 (3 baselines x 5 panels) after correcting my tau-boundary slice (m<=tau inclusive).
- 08:42Z B5 VERIFY CONFIRMED @bbdee030512d7cfa: _ev_uip_step -> BoxPipe.event_step verbatim move is canonical-identical 623/623 (objects+cand_log+events incl score/priority/touches) vs uip2_pbbirth@8361fe85; DISK suite 72/72; static: same call-site position in pivot fan-out (engine.py:416), __setstate__ routes legacy _ev_uip_born/_last_ev_birth into pipes.box (pickle back-compat ok), _ev_box_birth shares pipes.box._last_ev_birth cooldown as specced. Gate item clear.
- 09:05Z s.77.4b JOIN DONE (Part E bridged evalcheck-side): DR-RULES closed 08:56Z before seeing the 08:31Z geom unblock, so I ran THEIR measure code (DR_RULES_measure.gold_stats + report thresholds/predicates verbatim) on the blind dr_rules_item_geom.jsonl -> evalcheck/DR_RULES_pack_features.csv (102/102, 0 miss; item-own tau; full-run fallback sliced <=tau). Join vs key -> evalcheck/M2_RULES_JOIN.txt. Classes golden30/neg24/ehit11(10line+1level,0box)/efp37. Per-cell n small (4-37). Notables: C1@0.5 keeps 0/1 ehit vs removes 59% box/level efp; C6@clu removes ALL 11 box efp AND 4/7 golden boxes; C7@2 passes goldens .82/efp .92 (weak sep); C8 level n tiny. C7s/C8a NA (engine-object-only fields). Provenance: feature values=DR code on blind inputs; join+key mine.
- 09:07Z DR-RULES B/C numbers independently recounted from their artifacts: Part B C5@q95 box author compliance 113/119=0.950 OK, C8@1 level 76/76=1.000 OK (my recount identical). Part C (picks-only set): C5@q95 box pass_matched 1/16=0.06, pass_unmatched 20/609=0.033 -> removal .967; C8@1 level matched 3/7=.43, unmatched 377/590=.64 -> removal .361. All match DR_RULES.md tables. Verdict tension flagged for R78: literal 'BUILD-CANDIDATE' legs pass (other-family -1 holds trivially since rules are family-scoped) but Part D replay shows in-family cost bo16->2 (-14), le7->3 (-4)/le7->5 (-2) - the pre-registration has no in-family hit floor. Numbers verified; interpretation is Lead's.
- 09:37Z S1 VERIFY CONFIRMED (independent recount + transform replay): 456 box-decision events; hits base16 -> S1a 15 (keep-rule FAIL target leg, 23 events changed pick, 54 objects dropped - all 3 sampled drops reproduce <3-bar rule) -> S1b 16/16 PASS; non-box fams line20/level7/bracket29 identical; prefix invariance 178/178 recounted from S1_prefix.jsonl; transform mechanics 5/5 + 3/3 samples byte-match (last_event_end + cap jge). Owner-clean: S1a C3w 37->100% C4w 31->100% C5 4->65%; S1b C5 4->100% C3w 37->54% C4w 31->59% - all match DR_RULES_S1.md. Author-start stat (4.8% <=2bars, med36) = their claim, plausible from golden_starts artifact.
- 10:05Z TT VERIFY CONFIRMED @d8daa611c11bbed2 (R78 s.78.4(3), s.79.3 step-1): OFF==parent 623/623 canonical (objects+cand_log+events); ON(trade_tags=1)==parent 623/623 -> ON==OFF (facts excluded from canonical by construction); facts written ON=5027 live objects / OFF=0; equivalence TT.object_stats==DM.eng_stats 1392/1392 rule-fam objects field-for-field (bracket/annot return None-fam by design, no tags); suite DISKTT 83/83 (72+11 test_tt_*); static: _trade_tag_step post-selection per bar, single-source predicates (DR_RULES_measure+r73_edges re-import trade_tags.py), render.py grey-style behind flag. Tradeable fraction of budget picks at golden taus (my recount): box 1.7% level 15.6% line 72.8% bracket 100% (build's s.27-TT used all-live basis: 6.5/9.9). NOTE: C2_Q95 hardcoded 3dp vs measured 0.19548/0.20447/0.16613 - spec said import never copy; gap (0.195,0.19548] etc holds 0/4033 live objects -> cosmetic on TUNE, flagged not blocking.
- 10:35Z H0 VERIFY CONFIRMED (practice/H0_HYBRID.md): parent C-3 reproduced exactly (box16/level7/line20/bracket29 + clutter 4.33). Arms recounted from per-event rows: H0a level 16/76 (+9), H0b line 29/193 (+9), H0c both; box/bracket untouched. Census recomputed independently over all 179 golden panels: c3 4.33, a 6.00, b 7.67, c 10.00 - identical to report; keep-rule clutter leg (>5.0) FAILS all three arms as reported. Prefix invariance on my own sample (5 panels x 2 taus x 2 sources, live-set keys): 20/20. Owner-clean diag spot-consistent (donchian levels C8a~1.0 plausible from generator construction). Verdict: hits real, clutter binding - matches their keep-rule FAIL.
- 14:49Z ARM Y box_yield @e7d13384 CONFIRMED-as-measured / KEEP-RULE FAIL (own scorer, fresh engines): Y1==Y2 identical everywhere - box 7/118 (one same-date attribution gap vs their 119; numerator identical), level 3/76, line 18/193, bracket 30/85 EXACT vs build's 7/119 3/76 18/193 30/85 | flips box -14/+5 level -4/+0 line -3/+1 bracket -0/+1 = theirs exactly | clutter 4.67<=5.0 (179) exact | yield mechanics: 1674 kill-events 246 distinct objects, my s_box_broken re-agrees at t_right 60/60, 15/60 kills are meta_uip_persist incumbents (veto-bypass CONFIRMED incl UIP) | stale_far adds zero (Y1=Y2 picks+kills identical) | prefix invariance Y1 35/35 | KEEP RULE FAILS: box 7<16, level 3<6(parent-1), line 18<19(parent-1) - both variants rejected, no G-KIT/G-REVIEW pairing needed | OFF: box_yield absent from params_v1_1 -> mode0 early-return, OFF==parent covered by the 623/623 canonical on same tree (13:52Z legs). Suite DISK queued.
- 15:01Z s84.5 Y3_EST cross-check CONFIRMED (evalcheck/_y3_verify.py, own band-reconstruction + s_stale_far recompute on arm caches): stale@kill 5 = stale@tau 5 (same set: 9.17b x2, 9.17c, 9.23c, 9.45b) | onset<=pend_end frees 20 rows/17 unique incumbents | edge-matched frees 11 rows/10 unique - my free-row list identical to theirs incl all 11 edge rows | 0/16 hits stale (my _y3_est.py). s84.5 literal bar MET: 0 hits lost, >=5 edge-matched freed (10 unique). Correction to my 14:59Z note: the >=5 test is the onset-window count 11/10 not the stale@tau 5 - marginally comfortable not boundary. UNVERIFIED legs: their item-4 stats (box@1 age med 119b, retest 21/23 within 24b) and 'pool promotion unmeasured' caveat - Y1 precedent says freed!=converted (5/14).
- 16:05Z s85.3 YS_EST CONFIRMED on all decisive gates (evalcheck/_ys_verify.py, own sim on canonical caches): YS-a frees 1 row / 0 edge-matched = theirs exactly (same row 9.62b@840, BOX0003 stale-onset@126 inside cand window [115,162]) - under their def the incumbent must yield INSIDE the cand's pending window; sticky yield fires once so onsets landing before w0c leave the cand blocked by the promoted successor (my 19 remaining onsets all precede windows) | YS-b hits 16/16 LOST = theirs exactly: every hit incumbent box_broken pre-tau on some band version + post-exit_bar cand pending -> yield bars ~6-44 << tau (independent check: break on live band version + cand first-idx > exit_bar <= j_tau) | corroboration: 7/7 arm-Y cross-family loss panels show 4-12 YS-b yield events pre-tau (their s3 claim exact); 'demote without close not expressible' CONFIRMED - ctx_yield (salience.py:604-654) = DELETED+restore context-only, lvfree keeps rank-1 | GATE TABLE STANDS: YS-a FAIL frees (0<5), YS-b FAIL all three (16 lost, 1<5 frees, 6/17/15 at-risk) - no build; secondary cols (YS-b frees detail, exact at-risk split) corroborated not fully recounted - immaterial to verdict
- 16:34Z s86.4 AD_EST CONFIRMED on all decisive numbers (evalcheck/_ad_verify.py, own sim on canonical caches): AD-a lost 1 (9.7b@540, 2 adopt) gained 2 (9.16c@1070, 9.23c@985) med-adopt 5 p90 9 max16 = theirs EXACTLY | AD-b lost 1 same, gained 4 (9.4b, 9.16c, 9.45b, 9.56c - same panels+counts) med 4 p90 7 max 11 EXACT | mechanism: adoption chains verified per-event on 9.6a (identical events+final band); early diff resolved - er record anchor must be engine convention (ob.t_left real / cand.t0 adopted), not band t0 | PART1a anatomy on hit incumbents EXACT: id-age med 98 (83-112), band-ver age med 2 (1-2), drawn width 24 (16-35); misses n=102 vs their 103, ver 4 vs 3, wid 32 vs 30 - same conclusion: R85 s85.2(d) correctly withdrawn (identity ~7x author but band young, width in author's range) | 12 fixed panels: 0 author-geom matches (my sim too - no adopted band ends on V2.match) | GATE TABLE STANDS: AD-a FAIL lost1/gained2<3/med5>3; AD-b FAIL lost1/med4>3 (gained4 passes) - no build; at-risk 0/0/0 plausible (no live carry levels from box edges in corpus; adoption keeps id+src)
- 17:24Z s87.x RW_EST CONFIRMED-as-measured / GATE FAIL both variants (evalcheck/_rw_verify.py, own sim on canonical caches, e.abr axis): parent replay band parity 621/621 file-exact | RW-E (opposite edge=cluster_edge tol_e@conf): lost4 (9.6a@600 9.15b@900 9.32a@510 9.44b@730) gained1 (9.15b@895) net -3 = their jsonl ROW-EXACT | RW-G (pair gate dtol=max(1,0.25*e.abr[i])): lost3 (9.17a@475 9.34a@495 9.44b@730) gained1 (9.25b@775) net -2 = theirs ROW-EXACT (my earlier -4 was CA.abr full-day-axis bug, fixed+rerun) | med rewrites e 30=parent / g 24<parent (+1 cap is on increase - passes) | cross-family at-risk reproduced exactly: e {level1,bracket2} g {level1,line1,bracket2} 'birth-bar-differs' - bracket 2>1 fails that leg too | PART0b: dtol rescues 0 pivots on 12 no_cand rows (their p0b no DTOL_pass_if_dtol, e.abr correct) | mechanism verified: cluster edge systematically INWARD of raw extreme (9.6a: cluster top 13180.3 < 13184.3 -> band thins off golden 13185.0) | note: their jsonl fidelity 0/66 is a stale unsliced-vs-sliced artifact, sliced replay is exact (my 23/23+38/38 runs). GATE TABLE: RW-E FAIL (net-3<+3, lost4>2, atrisk bracket2>1), RW-G FAIL (net-2<+3, lost3>2, atrisk bracket2>1) - no build; per s87.4 E3 returns to birth-side research
