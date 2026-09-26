# THEORY_SURVEY — how a pro "sees" a chart, concept by concept

**Lane:** RESEARCH-SYNTH (B4). **Written:** 2026-09-21 ~17:00Z.
**Basis:** RT1 (Volman's craft), RT2 (other schools), RT3 (microstructure evidence),
RT4 (algorithms) — all accepted under Ruling 4 — corrected by `RT5_REVIEW.md`
(adversarial pass; upheld objections applied in §U). Design notes `DN_*.md`,
golden measurements `Q2_MEASUREMENTS.md` / `GOLDEN_AUDIT.md` (D8, D9), Lead Rulings 2–7.
Market-study numbers are **provisional (DR-MARKET, under review)** wherever they appear.

**Format per concept:** mechanism → operational definition (causal, bars ≤ t) →
evidence grade → primitive(s) it implies (PRIMITIVES_CATALOGUE id) → test and
the result that would falsify it. Grades: **EVIDENCE** / **PRACTITIONER** /
**FOLKLORE** / **THEORY**.

**Honest summary up front.** Only three claims in this whole survey sit on direct
FX microstructure evidence: (i) resting orders cluster asymmetrically around round
numbers and levels (Osler 2003); (ii) trends run faster just after round numbers are
crossed (Osler 2005; mechanism alive post-2010 — BIS 2017); (iii) intraday volatility
is a deterministic-ish function of the clock plus scheduled jumps (Dacorogna 1993,
Andersen & Bollerslev 1998, ABDV 2003, Krohn 2024, Evans 2018). Everything else —
the drawn-object grammar — is PRACTITIONER craft (Volman, Brooks, Wyckoff, Dalton,
Darvas) with one statistical exception (Bulkowski, daily US equities). No school,
and no paper, validates the geometry at M5 on post-2010 EURUSD: the golden set and
the DESIGN measurements are the arbiters. The survey below keeps that epistemic
split visible in every row.

---

## 1. Levels and zones — "the price the market remembers"

- **Mechanism.** Resting liquidity is asymmetric around a level: take-profit/limit
  depth at the level, stop depth just beyond it (Osler 2003, EVIDENCE on dealer
  order data incl. EURUSD — ~9.7k orders, one bank, 1999–2000; magnitudes are
  DEM-era priors and the zone pip offsets are ours to measure, RT5 C1). Technical
  levels coincide with limit-book depth peaks, and depth *precedes* the level's
  recognition (Kavajecz & Odders-White 2004, EVIDENCE — NYSE equities, mechanism
  transfer; the paper shows coincidence, it did **not** measure per-touch
  depletion). Corollary the schools never state: each touch *may* consume part of
  the book → a level *weakens* with use — a plausible inference but **a hypothesis,
  not a sourced result** (RT5 C5 WEAKENED): it stands pending the TUNE
  hold-rate-vs-touch-count test, and until then every `depth_consumed` term is a
  signed prior. "Stronger with each touch" is FOLKLORE; analysts' *asserted*
  strength labels were falsified outright (Osler 2000 — that kills claimed labels;
  it does not forbid causal, measurable salience ranking — see §15).
- **Operational definition.** A level = cluster of ≥2 same-side swing extremes within
  `eps = max(1 pip, 0.25·ABR)` (lone spikes excluded — D9); zone rendered asymmetric,
  far side wider (stops sit beyond). Touch = bar extreme within the zone; consume =
  close through far side.
- **Grade.** Mechanism EVIDENCE (FX order data + equity book); any specific zone
  geometry = PRACTITIONER; touch-strengthening = FOLKLORE.
- **Primitives.** C1 BUCKET_MERGE, C2 LEVEL_ZONE, C5 CARRY.
- **Test / falsifier.** On TUNE golden levels: price = extreme-with-company (9.15b
  ruling). On DESIGN (provisional track): bounce excess vs matched placebos — if the
  remediated M3 contrast shows no first-touch premium, the "defended" reading drops
  to PRACTITIONER-only and zone widths revert to pure golden calibration.

## 2. Round numbers — the magnet lattice

- **Mechanism.** Order placement is a human act done in round numbers: 95.5% of
  published S/R levels end 0/5 (Osler 2000); TP orders sit AT the round number,
  stops just beyond (Osler 2003); quotes cluster on 0/5 digits, more in high-vol
  regimes (Sopranzetti & Datar 2002). Net: a round level is a partially reflecting
  barrier — stall/absorb on approach, accelerate once traversed.
- **Operational definition.** Context grid .00/.50 (20-grid in low-vol regime);
  features only: `magnet` ahead ~12–30 pips, `counter-magnet` ~7–10 pips on the
  stop side, `battle` flag on straddling boxes. Never a drawn structure, never an
  anchor for geometry.
- **Grade.** EVIDENCE (clustering + asymmetry). Round-number *bounce* on our era:
  provisional (DR-MARKET) contrast was ns even before its inference was invalidated —
  treat magnets as attention context, not reversal levels.
- **Primitives.** E1 ROUND_GRID.
- **Test / falsifier.** Negative fixture: a gridline alone must never birth a level
  (DN_LEVEL §7d). Feature check: distance-to-grid term enters F1 scoring; if the
  remediated cascade test still shows nothing, drop the continuation-speed prior (§3).

## 3. Boxes / ranges — two-sided resting flow made visible

- **Mechanism.** A range is a region bounded by two-sided depth; inside, mean-
  reverting liquidity provision dominates (K&OW mechanism via Osler orders, RT3 §6).
  Cross-school agreement on geometry (Brooks TR, Wyckoff phases, AMT balance,
  classical rectangle, ICT dealing range) — disagreement only on the confirmation
  currency (bar close vs volume vs time-at-price vs statistics vs structure-shift).
- **Operational definition.** Birth: alternating θ₂ pivots + second touch on the
  breakout edge (spec constructive rule, Darvas gestation root). Edges = cluster
  extremes with company over the *buildup* window `build_start..build_end` (D9:
  stated height = pre-break range; drawn span may outlive containment). Freeze at
  birth; pre-break re-anchor only on a confirmed new alignment (RT1 §6.3). RT5 C6
  note: spec v1 is *internally split* — §20 says edges are "fixed once set" while
  §109–111 already encode re-anchor/tighten rules; this survey adopts the
  versioned pre-break re-anchor reading and flags the §20 wording for the spec's
  next revision (SPEC_v1_CRITIQUE P2).
- **Grade.** Geometry PRACTITIONER with EVIDENCE-grade mechanism underneath; box
  *statistics* EVIDENCE only on daily equities (Bulkowski) — direction, not pips.
- **Primitives.** D1 BOX_LIFECYCLE (BOX/RANGE_OPEN/CONTEXT_RANGE), C1, B3, C4.
- **Test / falsifier.** Golden: stated-height boxes rebuild to text within ~1.5 pips;
  buildup containment ≥90%; straddle rule. Falsifier for the construct: if bucket-merge
  edges cannot reproduce golden edges within tol on ≥90% of repaired boxes, the
  cluster model of "what the author drew" is wrong — fall back to text-anchored edges.

## 4. Breakouts — proper vs tease vs false

- **Mechanism.** Traversing an edge detonates stored pro-trend stop flow
  (Osler 2005; Osler & Savaşer 2011: price-contingent orders generate >half of FX
  excess kurtosis). Whether the break *holds* depends on whether the move was
  argued at the boundary (buildup) or merely probed.
- **Operational definition.** Break = close beyond edge by > tol (wick excursion =
  poke, never a break). Class at break time from structure only: `proper` = buildup
  resting at the edge; `tease` = break originating mid-range / thin buildup; `false`
  = straight traverse with no buildup. Labels may overlap — primary label +
  attributes (RT1 §7 contradiction resolved in favour of the book).
- **Grade.** Post-crossing acceleration EVIDENCE (mean effect small, fat-tailed —
  Osler 2005's honest number is ~0.7bp/15min on DEM-era quotes; the "first 1–3 M5
  bars = cascade window" framing is an engineering choice inside hours-scale
  persistence, not a sourced constant — RT5 C2). The break *taxonomy* is
  PRACTITIONER (Volman/Brooks); "most breakouts fail" is a PRACTITIONER base-rate
  claim — Brooks's ~80% counts breakout *attempts* returning to the range in a
  trading-range context on E-mini 5-min charts, incommensurate with Bulkowski's
  ≥10%-travel confirmed-close failures on daily equities (15–34%, [snippet-only,
  HTTP 406]) and with Darvas's continuation assumption — unresolved; our own
  labelled data must decide posture (RT2 §7 test 7).
- **Primitives.** C4 EDGE_ACCEPTANCE, C3 POKE_EVENT, buildup gauge (D6/E5 input).
- **Test / falsifier.** Golden: `build_end` ≤ breakout bar for stated-height boxes;
  T/F agreement ≥0.60. Falsifier: if tease-vs-proper attribution does not separate
  golden follow-through cases at all, collapse the taxonomy to two classes.

## 5. The poke-and-fail — the highest-consensus structure in the literature

- **Mechanism.** Stops parked beyond the edge fire into TP depth; the excursion
  cannot hold; trapped breakout traders must exit, fuelling the return. It is the
  most *re-described* object in the literature — Brooks failed breakout, Wyckoff
  spring/upthrust, AMT look-above-and-fail/excess, classical busted pattern, ICT
  liquidity sweep — but the five descriptions are not five independent
  measurements (ICT rebrands Wyckoff; AMT and Brooks share floor lineage; only
  Bulkowski is an independent measurement — RT5 C8).
- **Operational definition.** Bar extreme beyond a live edge by ≤ tease_tol with
  close back inside → `tease`; subsequent traverse within ≤3 bars → `false`
  (relabel, attributes kept). Edge never moves on a poke.
- **Grade.** Cross-school geometry PRACTITIONER; mechanism EVIDENCE (order
  asymmetry); the *named* pattern untested in FX intraday (RT3 §4); Bulkowski's
  bust rates (36% of double tops bust; +54% avg post-bust) are daily-equity
  EVIDENCE confirmed [snippet-only, HTTP 406] by RT5 — quarantined to bull-market
  daily equities pending a successful re-fetch.
- **Primitives.** C3 POKE_EVENT → LABEL_TF; feeds break classifier.
- **Test / falsifier.** T/F agreement gate ≥0.60 on matched boxes; falsifier: if
  golden T/F marks correlate with no computable poke predicate (depth, close-back,
  edge age), the label is hindsight ink — demote to annotation-only.

## 6. Buildup — the argument at the barrier

- **Mechanism.** A buildup is price accepting the edge's neighbourhood: both sides
  transact at the boundary, consuming TP depth while stops accumulate — stored
  energy with a sign (RT3 §6 + §4).
- **Operational definition.** Congestion of alternating bars within ~1·ABR of the
  edge, ranges shrinking relative to the prior buildup; no fixed minimum (1–2 bars
  at a pullback end, ≥4 for a pattern break — book); thickness measured relative to
  previous buildup [spec §3.7].
- **Grade.** PRACTITIONER (Volman, Brooks "tight TR at the line"); provisional
  (DR-MARKET): buildup-before-break contrast ns even before invalidation — the
  *descriptive* claim (buildup exists before drawn breaks) holds in the golden set
  (median buildup 65 min, last buildup close 2.7 p off the edge — Q2 §1).
- **Primitives.** D1 birth gate; F1 score term.
- **Test / falsifier.** Golden: drawn boxes show the buildup signature (median
  numbers above); falsifier: candidate boxes with vs without buildup signature draw
  at equal rates → the feature carries no drawing information, demote.

## 7. Squeeze / contraction — stored energy, not a shape

- **Mechanism.** As edge depth is consumed (hypothesis — §1, RT5 C5) and stops
  accumulate just beyond, the executable corridor narrows; the traverse detonates
  it (RT3). "Contraction precedes expansion" is the most *re-described* observation
  across schools (RT2 §3) — not five independent measurements — and under
  volatility clustering it is nearly tautological. The only measured family member
  is weak: Bulkowski's symmetrical triangle ranks 36/39 with a 37% down-breakout
  failure (daily equities, [snippet-only]). Keep it a wall-bracketed *context
  state*, never a signal.
- **Operational definition.** ≥2–3 bars ≤ 0.8·ABR between two *named live walls*,
  gap narrowing (≤0.6), apex within ~10–15 bars. Rendered as short inner lines,
  not ellipses (golden shows lines).
- **Grade.** Regime claim PRACTITIONER+mechanism; the drawn object is rare
  (golden n=2) — mostly a context state.
- **Primitives.** D3 SQUEEZE_WALLS, D6 DOME_SEQ, E4 contraction channels.
- **Test / falsifier.** The two golden squeezes must get candidates; born count
  must collapse (176 → O(10s)) via the named-walls gate. Falsifier: if wall-bracketed
  contractions do not precede drawn breaks more than ambient ones on TUNE, keep the
  regime for salience but drop the object.

## 8. Pullbacks and flags — the orderly correction

- **Mechanism.** Countertrend probes fail into latent depth; each failure re-arms
  the dominant side (Brooks H2/L2 second entry; Wyckoff LPS/BUEC; classical flag).
- **Operational definition.** Correction moving diagonally, gently, orderly — few
  strong counter-bars; typical depth 40–60% of prior wave, often ending at EMA25
  [book]. Pullback-end births a box at the first counter-extreme (spec §3.1a).
  Second-probe extreme → MINI_LEVEL; its break = trigger.
- **Grade.** PRACTITIONER throughout; Bulkowski's flag stats (44–45% failure, ~9%
  avg move, daily stocks) say flags are *weak* — EVIDENCE for caution.
- **Primitives.** B1 legs, D1(a) birth route, C6/C5 middle-section levels, E5 retest.
- **Test / falsifier.** Second-probe vs first-probe trigger quality on labelled
  setups (RT2 §7 test 5) — if second probes show nothing, drop the H2 preference
  to PRACTITIONER annotation.

## 9. Trendlines and channels — the drifting barrier

- **Mechanism.** No direct microstructure validation exists (RT3 §4). The defensible
  reading: a line through confirmed extremes is the market's marginal rejection
  price drifting at a fixed rate — same depth-consumption structure as a horizontal
  edge, tilted. AMT pointedly does not draw lines; ICT draws them only as sweep
  targets — whether a *line* adds anything over its anchor swings is a live
  disagreement (RT2 §4.4).
- **Operational definition.** Hull-vertex anchors (only least-touch candidates),
  slope classes per book (upside-defining lines horizontal/falling; downside
  horizontal/rising), freeze on ≥2-touch confirm, re-anchor only on the logged
  margin rule; pierced ≠ dead — conversion to dashed carry on confirmed traverse.
- **Grade.** PRACTITIONER (all schools); classical "third touch validates" is
  FOLKLORE (no FX test found; analyst strength labels falsified in Osler 2000).
  Provisional (DR-MARKET): M5 third-touch bounce premium point estimate plausible
  but inference REVIEW_2-invalidated — do not cite as provenance.
- **Primitives.** D2 LINE_HULL; slope-class filter.
- **Test / falsifier.** Hull-vertex recall ≥90% of golden anchors; slope-class match.
  The discriminating measurement: do drawn lines carry information *beyond* their
  anchor swings (CONTEXT_LINE-vs-swing-only comparison, RT2 §4.4) — if not, the
  object simplifies to its anchors.

## 10. Carried levels / role reversal — memory of where value broke

- **Mechanism.** A traversed edge has fired its stop cluster; what remains is TP
  depth on the other side — the same price now caps from the far side (RT3 §6).
  Cross-school: Brooks breakout test, Wyckoff BUEC, AMT prior-VA edges, classical
  polarity, ICT breaker — the most cross-validated object in RT2 (P10).
- **Operational definition.** Broken edge → level at frozen price, dashed, span =
  carry era (from source event to stated/implied end — 9.5c ruling); multi-route
  birth (broken_edge, congestion_edge, continuation, session_extreme,
  formation_extreme, marker); consumption = weight decay, not deletion.
- **Grade.** Object = PRACTITIONER; mechanism EVIDENCE-adjacent; "retest/role-
  reversal edge" as a market statistic: provisional (DR-MARKET) F-B was null even
  before invalidation — LEVEL_CARRIED is a *fidelity* object (the author draws it),
  not a validated alpha source (Ruling 5d.5 stands: no extra salience weight).
- **Primitives.** C5 CARRY, C2 LEVEL_ZONE.
- **Test / falsifier.** Coverage ≥80% via new routes; sibling-price and stated-end
  regressions. Falsifier: if congestion_edge/session_extreme routes don't lift
  coverage, the "levels book" model is wrong — inspect anchors directly.

## 11. Equal extremes, M/W, SHS — the second probe

- **Mechanism.** Two attacks on the same latent depth: under the consumption
  hypothesis (§1, RT5 C5 — unmeasured) the second probe meets a thinner wall and
  either breaks it or fails harder. Every school reads equal highs as a *magnet
  to be probed*, the opposite of the retail "double top = sell" (RT2 §4.4).
  ICT's "liquidity pool" is the same geometry with an unverifiable motive layer.
- **Operational definition.** Equal-extreme pairs within eq_tol on the pruned θ₂
  stream → M/W brackets; inner θ₁ leg → Mm/Ww; SHS = three-extreme template with
  head ≥ ~1·ABR proud; middle section → MINI_LEVEL. Emitted only when decision-
  relevant.
- **Grade.** Geometry PRACTITIONER; confirmation/failure rates EVIDENCE on daily
  equities only (Bulkowski — confirmed [snippet-only, HTTP 406] by RT5; every
  number pending a successful re-fetch); "liquidity engineering" motive FOLKLORE.
- **Primitives.** C6 EQUAL_EXTREMES, D4 BRACKET_MATCH.
- **Test / falsifier.** Per-letter recall ≥80%; falsifier for the magnet claim:
  poke-then-reject no likelier after equal extremes than lone ones (RT2 §7 test 2)
  → drop the equality feature, keep only the pivot pair.

## 12. Domes — decaying counter-pressure (computed, never drawn)

- **Mechanism.** Each weaker retest of a level shows the attacking side's depth
  thinning — diminishing excursions = exhaustion profile.
- **Operational definition.** Counter-swing heights above/below the anchor recorded
  per dome; mostly-shrinking sequence flagged; the last flattened dome hosts the
  squeeze.
- **Grade.** PRACTITIONER (Volman only).
- **Primitives.** D6 DOME_SEQ.
- **Test / falsifier.** Golden shrinking-dome sequences (22→13→15→8, 30→25→18→10)
  must flag; falsifier: flagged sequences don't co-locate with drawn squeezes/breaks.

## 13. Session rhythm and the calendar — when structure can even exist

- **Mechanism.** Volatility follows the geographic workday (EVIDENCE: Dacorogna
  1993, A&B 1998, Ito & Hashimoto 2006 — the U-shape/seasonality claim);
  scheduled events inject jump-like price discovery (ABDV 2003), fix
  drift-and-revert (Krohn, Mueller & Whelan 2024 — ~2bp pre-fix USD drift, *not*
  2.5bp as RT3 printed — RT5 C9), fix-window anomalies (Evans 2018), thin-session
  cascades (BIS 2017). The 10:00 ET option-expiry EBS spike is documented by
  Berger, Chaboud, Chernenko, Howorka & Wright (IFDP 863 → JIE 2008) — RT3's
  attribution to Ito & Hashimoto was a mis-citation (RT5 C9). Structure evaluated
  through these windows reads flow noise as geometry.
- **Operational definition.** CET session marks (Asia 00:00–08:00 balance; EU ramp
  08:00–10:00; lulls ~12–14 / ~18–20; UK-hour caution 09–10); hard windows
  14:30 ±15, 14:15 ±10, 16:50–17:10 WMR (spec v1's "16:00 CET" is wrong — London
  16:00 = 17:00 CET/CEST year-round), 16:00 ±10 option-cut soft; Tokyo fix 01:55
  CET is winter-only (02:55 CEST summer — JST never shifts). All window widths
  are our engineering choice, not the papers'. Suppress *initiation* inside
  windows, not in-flight traverses.
- **Grade.** Seasonality + event windows EVIDENCE; lull micro-windows PRACTITIONER
  (book); provisional (DR-MARKET M2, descriptive — survived review): spike clusters
  08:00/09:00 CET are the largest un-gated bursts.
- **Primitives.** A2 CET_CLOCK, E2 SESSION_MARKS, E3 NEWS_WINDOWS.
- **Test / falsifier.** DST-switch fixtures; NFP/ECB captioned-bar regressions (D3);
  falsifier: if golden objects initiate inside 14:30-window at the ambient rate,
  the hard gate is over-strong — soften to demotion.

## 14. Pressure — the EMA as gauge, never as wall

- **Mechanism.** Not microstructure — a smoothed-consensus proxy: which side has
  been winning the recent auction. Book rules: slope is "the main tool nearly all
  the time"; flattening ≠ flat (hysteresis); EMA is *not* S/R by itself.
- **Operational definition.** EMA25 slope sign over m bars + side-occupancy + HH/HL,
  with hysteresis (state flips only on a real turn or ≥p bars persistence on the
  other side).
- **Grade.** PRACTITIONER (Volman); provisional (DR-MARKET M6 — passed review):
  no kink at period 25; L≈20–50 equivalent → the *period* is arbitrary; the
  *state variable* is what matters.
- **Primitives.** E5 EMA_PRESSURE.
- **Test / falsifier.** Hysteresis fixture (Fig 7.9-type counter-drift stays
  bearish); falsifier: pressure state shows no drawn-vs-ignored separation on TUNE
  → demote to context.

## 15. Salience — the real object of the whole exercise

- **Mechanism.** Attention concentrates orders: levels matter partly *because*
  they are visible (Osler 2000 inverts nicely — published levels work because the
  audience exists; NB Osler falsified analysts' *asserted* strength labels, not
  causal measurable ranking — RT5 C3, never cite it against our own features).
  Depth consumption may add time structure — "an untested object outranks a
  consumed one" is a hypothesis pending the TUNE hold-rate test (RT5 C5).
- **Operational definition.** Score every evaluated candidate on causal features
  (touches, span, anchor prominence, recency, distance/ABR, session prior, depth
  consumed) − per-object MDL penalty; NMS on footprint; hysteresis on displacement;
  budget = golden count distribution (~3 median, ≤8–9); empty scoreboard →
  STAND_ASIDE, never fill with noise.
- **Grade.** The *specific weights* are our own MEASURE-class craft; the *necessity*
  is EVIDENCE about the current engine — gates that ask "is another structure
  active" do not select (Q2: vetoed candidates drawn at equal-or-higher rates).
  Hindsight caveat (Ruling 5b): the golden set is setup-selected — causal correlates
  only; `fwd_*` is withdrawn (A4.2) and may not feed any rule.
- **Primitives.** F1 SALIENCE_SCORE, F2 NMS+HYSTERESIS+BUDGET.
- **Test / falsifier.** Born set ≈ drawn set at the new born counts; object counts
  inside golden distribution; falsifier: no causal feature set separates drawn from
  ignored → the drawn-vs-not question is irreducible to our features, escalate.

## 16. Stand-aside — a first-class output

- **Mechanism.** Jump events (news), dead tape (no flow), and frantic tape
  (unreadable structure) are states where "no drawing" is the correct drawing.
  The casebook marks skips roughly as often as entries (RT1 §5 — project
  measurement, 138 charts).
- **Operational definition.** STAND_ASIDE with reason codes {news, lull, room<14,
  ema-ban, barbwire/chop, dead-vol, frantic-vol, counter-magnet, mid-grid} —
  emitted, never silent.
- **Grade.** News/lull EVIDENCE-backed (E3/E4); the composite PRACTITIONER.
- **Primitives.** E3, E4, F2 empty-score path.
- **Test / falsifier.** Quiet fixture: no positive scores → STAND_ASIDE + zero ink;
  falsifier: engine draws inside golden no-object panels at an unacceptable rate.

## 17. Volatility regime — every threshold in ABR units

- **Mechanism.** The same geometry at different volatility is a different object.
  JKX 2023 (CNN on rendered OHLC images transfers across scales and markets) is
  *motivation for testing* ABR-normalisation and an extrema grammar — not evidence
  for them: predictive information ≠ perceptual fidelity, and JKX's learned
  patterns "differ significantly from commonly analysed trend signals" (RT5 C10).
- **Operational definition.** All tolerances parameterized as max(pip floor,
  ABR fraction); low-vol regime switches the grid to the 20-lattice.
- **Grade.** PRACTITIONER; JKX/LMW = academic bridge making extrema-geometry a
  plausible, testable representation — nothing more (RT5 C10).
- **Primitives.** A1 ABR, E1 low-vol switch.
- **Test / falsifier.** Per-regime golden split (Asia-thin panels vs US panels):
  ABR-parameterized rules must hold in both or the regime layer is incomplete.

---

## U. Corrections applied from RT5 (the adversarial pass)

`RT5_REVIEW.md` verdicts on the ten load-bearing claims: **0 fabricated,
0 REFUTED, 1 WEAKENED** (C5 — K&OW showed levels coincide with depth peaks but
never measured per-touch depletion; "weakens per touch" is RT3's inference), and
**9 HELD-WITH-CAVEAT** (all era-, market-, or definition-bounded). Applied:

| # | RT5 correction | where applied |
|---|---|---|
| 1 | per-touch weakening → hypothesis pending TUNE hold-rate-vs-touch-count test | §1, §7, §10, §11, §15; PRIMITIVES C5/F1; **propagation to DN_SWING:16, DN_LEVEL:22, DN_SALIENCE `w7`, DN_BRACKET:11 is flagged for the design lane — this lane may not edit them (documents-only wall)** |
| 2 | Krohn pre-fix drift ~2.5bp → ~2bp | §13; PRIMITIVES E3; CRITIQUE §2.1/P7 |
| 3 | 10:00 ET option-cut spike → Berger et al. 2008 (IFDP 863/JIE), not Ito & Hashimoto | §13; PRIMITIVES E3; CRITIQUE §2.1/P7 |
| 4 | Tokyo fix 01:55 CET winter-only; all window widths = engineering choice | §13; PRIMITIVES E3; CRITIQUE P7 |
| 5 | 16:00 CET = option cut (soft); WMR fix = 17:00 CET/CEST year-round (hard) | §13; PRIMITIVES E3; CRITIQUE §2.1/P7 |
| 6 | Osler-2000 corollary narrowed to *asserted* labels; never cite vs causal ranking | §1, §15; CRITIQUE §2.2/P8 |
| 7 | Brooks ~80% = breakout *attempt* failures in TR context, E-mini M5; incommensurate with Bulkowski | §4; CRITIQUE §2.3 |
| 8 | all Bulkowski stats [snippet-only, HTTP 406], quarantined to bull-market daily equities | §4, §5, §11; CRITIQUE §2.3 |
| 9 | "five independent traditions" → "most re-described"; measured member weak (triangle 36/39) | §5, §7 |
| 10 | JKX retagged motivation-for-testing; predictive ≠ perceptual | §17 |
| 11 | spec §20 "fixed once set" vs §109–111 re-anchor — internal split recorded | §3; CRITIQUE §1 row 1/P2 |
| 12 | Osler magnitudes = DEM-era priors; 1–3-bar cascade window and pip offsets are ours, not sourced | §1, §4; PRIMITIVES C2/E3 |

— End of THEORY_SURVEY —
