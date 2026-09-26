# PRIMITIVES_CATALOGUE — the bar-computable vocabulary of the perception engine

**Lane:** RESEARCH-SYNTH (B4). **Written:** 2026-09-21 ~16:30Z.
**Inputs:** `DR_THEORY_BRIEF.md`; RT1–RT4 (accepted, Ruling 4); RT5_REVIEW (adversarial, this folder);
the eight design notes `research/perception/design/DN_*.md`; golden measurements `Q2_MEASUREMENTS.md`
and `GOLDEN_AUDIT.md` (D8/D9 semantics); `LEAD_RULINGS.md` Rulings 2–7.
Market numbers appear only where marked **provisional (DR-MARKET, under review)** — REVIEW_2
invalidated all M3 outcome-derived contrasts (F1/F2) pending re-run; they are listed as
*hypotheses to re-measure*, never as provenance.

**Conventions.** All primitives are causal on closed M5 bars: state at bar `t` uses bars `≤ t` only.
Units: pips (1e-4 EURUSD), `ABR` = mean high−low of the last `abr_len` = 50 closed bars
(spec §1; on the 2012 feed ≈ 4–7 pips), bars, CET minutes.
Provenance tags: **[spec §n]**, **[book p.n]** (VN-edition pages via RT1), **[RTn §x]**,
**[Q2]**, **[D8/D9]** (GOLDEN_AUDIT), **[Ruling n]**, **[MEASURE]** = parameter must be set
from TUNE/golden data — never invented.

**Reading order.** Sections A→F are dependency-ordered: scale → swing skeleton → price-memory
primitives → structure assembly → context/gates → selection. Every object type in spec §2
is served by a composition of these primitives; nothing reaches the chart except through F.

---

## A. Scale and clock

### A1. ABR — the volatility yardstick
- **Definition.** `ABR(t) = mean_{i=t-49..t}(high_i − low_i)` over closed bars. Recompute per bar.
- **Parameters.** `abr_len = 50` bars [spec §1; provisional (DR-MARKET): all level results ABR-relative and stable → keep 50].
- **Cost.** O(1) rolling sum.
- **Failure modes.** ABR collapses in dead tape (Asia 2012 ~4 pips) — every ABR-relative threshold must have a pip floor; ABR inflates on news bars — gates (E4) must not let one spike poison the next hour's tolerances.
- **Serves.** Every tolerance and threshold; the θ parameters of B1.
- **TUNE.** `abr` at birth is already a logged candidate feature (Q2: drawn lines born at ABR 6.4 vs ignored 4.4 — regime dependence is real).
- **DN refs.** DN_SWING §5, DN_BOX §5, DN_LEVEL §5.

### A2. CET_CLOCK — session time
- **Definition.** Deterministic map bar timestamp → CET minute-of-day. BOOK feed: identity (Berlin wall, D3); DESIGN feed: `CET = server − 1h` (EET; Ruling 2 §2.2.5). The engine never infers the clock from bars.
- **Parameters.** none (feed flag, set per data source).
- **Cost.** O(1).
- **Failure modes.** DST switch weeks (spec §6.2 fixture); a feed silently changing epoch — caught only by news-bar probes (Ruling 1 method).
- **Serves.** RANGE_OPEN birth window, session salience prior, all calendar gates (E3).
- **TUNE.** Regression on the 2012 NFP/ECB captioned panels (D3 fixtures).
- **DN refs.** DN_TF §5; spec §1.

---

## B. Swing skeleton

### B1. DC_PIVOT — directional-change pivot stream
- **Definition.** Mode ∈ {up, down}; track running extreme `xext` (wick). When the opposite-side price retraces `≥ θ` from `xext`, the extreme confirms as a pivot `(t_ext, t_conf, price, dir)` and mode flips. Two nested thresholds on the same stream: `θ₁ = k₁·ABR` (micro), `θ₂ = k₂·ABR` (structural). [RT4 §2.3, DN_SWING §5]
- **Parameters.**
  - `k₁ ≈ 0.8` [RT4 §12.1 prior; MEASURE: golden micro-anchors must survive — DN_SWING §7a]
  - `k₂ ≈ 2–3` [RT4 §6: invert the DC count law to 4–8 events per 84-bar window; MEASURE: ≥90% of golden anchor legs survive, θ₂ count ≤ ~8/panel — DN_SWING §7a–b]
  - confirm mode: wick-retrace default; A/B vs close-retrace on TUNE [RT4 §11]
  - expected confirm lag ~θ^1.9, ≈5–15 bars at k₂ [Glattfelder et al. 2011, EVIDENCE on ticks — exponent re-check on our feed, DN_SWING §7c]
- **Cost.** O(1) per bar per threshold.
- **Failure modes.** FP: none at θ₂ by construction (that's the point); risk is FN — steep legs confirm *pauses* as pivots (mitigate: steep-slope candidate lines may use θ₁ anchors, DN_SWING §6), slow-held tops never confirm a reverse (mitigate: level objects also accept cluster extremes, B4/C1). Gap open fires instantly → mark `gap` event. Lone news spike becomes a pivot — acceptable, it IS what Volman marks, but flag `lone_spike` so C1/D2 don't anchor on it without company.
- **Serves.** anchors for PATTERN_LINE, CONTEXT_LINE, BOX edges, BRACKET templates, MINI_LEVEL, BAR_MARKER.
- **TUNE.** leg-size calibration + micro-suppression + lag distribution (DN_SWING §7); hierarchy exactness θ₂ ⊆ pruned θ₁ (§7i).
- **DN refs.** DN_SWING throughout; consumed by every other DN.

### B2. PROMINENCE — persistence pruning
- **Definition.** Over the alternating θ₁-pivot sequence, `prom(p)` = height of p above the nearest opposite extreme whose level would merge p into a dominating swing (topographic prominence; merge-tree / union-find, amortised O(α(n)) per confirm [RT4 §9.1]). Kill θ₁-pivots with `prom < pmin`; the θ₂ set = persistence-filtered θ₁ — strictly hierarchical, the two scales cannot disagree.
- **Parameters.** `pmin ≈ 0.5·ABR` [RT4 §9.1; MEASURE at the precision/recall knee on "is this pivot a golden anchor"].
- **Cost.** O(α(n)) amortised per pivot.
- **Failure modes.** Final persistence is known only once dominated — use prominence-so-far (monotone non-decreasing) for ranking; a slow grind produces many low-prom pivots that die at the floor (intended: kills the micro-pivot flood, Q2's core defect).
- **Serves.** input filter for D1–D5; salience term `w3` in F1.
- **TUNE.** rank correlation of prom vs golden-anchor membership; floor at knee.
- **DN refs.** DN_SWING §5, DN_SALIENCE §5 stage 1.

### B3. FALSE_EXT / lone-spike flag
- **Definition.** A wick extreme with no company: more than `tol` beyond the next-most-extreme bar AND tail > 50% of its bar range → flagged `lone_spike`, excluded from edge/hull input unless text names it. [spec §3.1; D9 company rule: "a lone spike is a poke, not an edge" — 9.15b ceiling ruling]
- **Parameters.** `tol = max(1 pip, 0.25·ABR)` [spec §1]; tail fraction 0.5 [spec §3.1].
- **Cost.** O(1) per bar (neighbour comparison).
- **Failure modes.** FN: the *named* spike edge ("bottom = the 10:25 spike low", D9) — flag is a default, not a ban. FP: dense tape where every bar has company → flag silent (fine).
- **Serves.** B4 cluster input, D2 hull input exclusion, LABEL_TF context.
- **TUNE.** 9.15b ceiling-cluster regression (company-rule edge = cluster top, not the spike).
- **DN refs.** DN_SWING §6, DN_BOX §5, DN_LEVEL §5.

---

## C. Price memory — edges, zones, pokes, carries

### C1. BUCKET_MERGE — edge cluster on extremes
- **Definition.** Sorted cluster list over member extremes (wick-inclusive, lone-spike-excluded) inside the object's span: new extreme merges into the nearest cluster within `eps`, else opens one; transitive merge when centroids approach within `eps`. Edge price = most extreme cluster with `minPts` support; level price = support-weighted mean. 1-D DBSCAN (IncrementalDBSCAN equivalence ⇒ deterministic). [RT4 §4.1; DN_BOX §5; D9]
- **Parameters.** `eps = max(1 pip, 0.25·ABR)` [spec §1]; `minPts = 2` [spec §3.1 breakout-edge rule + D9 company rule; MEASURE vs golden touch histogram].
- **Cost.** O(log n + k) insert, trivially O(n) rebuild; n ≤ ~50 per window.
- **Failure modes.** FP: poke wicks merging into the cluster inflate the edge (D9 tease texture) — exclude bars already labelled as pokes from cluster input where identifiable. Cluster centroid drift → freeze price at draw time (F4); membership may update internally.
- **Serves.** BOX/RANGE_OPEN/CONTEXT_RANGE edges; LEVEL_CARRIED and MINI_LEVEL prices; BRACKET equality test input.
- **TUNE.** golden edge-touch histograms (bottom edges 3–22 touches); stated-height boxes rebuilt within ~1 pip (9.63a 13.0p, 9.50a 13.0p regressions, DN_BOX §7b).
- **DN refs.** DN_BOX §5, DN_LEVEL §5, DN_LINE §5 (anchor-side).

### C2. LEVEL_ZONE — asymmetric zone, stored line
- **Definition.** Store the defended extreme price (single number); render/reason with an asymmetric band: near side `z_near = max(1 pip, 0.15·ABR)`, far side `z_far = z_near + q75(poke-depth-past-level)`, cap `~0.5·ABR`. Rationale: TP depth sits at the level, stop depth just beyond it (Osler 2003 mechanism, EVIDENCE — ~9.7k orders, one bank, 1999–2000; the pip offsets/magnitudes are DEM-era priors, ours to measure — RT5 C1). [RT3 P1; DN_LEVEL §5]
- **Parameters.** `z_near`, `z_far` as above; `q75` of the TUNE poke-depth distribution [MEASURE — RT4 §12.5; provisional (DR-MARKET): F-O overshoot p90 ≈ 0.5–0.7 ABR is REVIEW_2-invalidated, re-measure].
- **Cost.** O(1) per level.
- **Failure modes.** Width calibrated on pokes may under-cover the *traverse* side during cascades — the zone is a perception aid, not a break test; breaks use close-vs-price (C4).
- **Serves.** LEVEL_CARRIED, MINI_LEVEL, box edge bands (rendering convention spec §2 "edges are bands").
- **TUNE.** poke-depth histogram; `edge_tol` sanity vs spec's `max(1, 0.25·ABR)` sitting at ~p75–p90 of overshoot (provisional F-O).
- **DN refs.** DN_LEVEL §5, DN_BOX §5, DN_TF §5 tease_tol.

### C3. POKE_EVENT — tease/false labelling (T → F)
- **Definition.** On a live edge: bar extreme beyond edge by `≤ tease_tol` with close back inside → `tease` event (depth recorded). A tease window where price then traverses the edge (close beyond far side, no immediate re-entry) within `≤3` bars → relabel `false`. Labels are *attributes on the object*, one per edge per excursion; primary label + attributes model (overlap allowed). [spec §3.2; RT1 §9.9–10; RT2 P1; DN_TF §5]
- **Parameters.** `tease_tol ≈ max(1–3 pips, ~0.4·ABR)` [spec §3.2; MEASURE poke-depth distribution]; relabel window 3 bars, depth rule ≥ ½ edge height [spec §3.2].
- **Cost.** O(1) per bar per live edge.
- **Failure modes.** FP: mechanical label spam (209 born, Asia-heavy — Q2); labels must attach to decision-relevant edges only (F1 score gate). FN: deep excursions (>½ height immediately) are already traversals, not pokes.
- **Serves.** LABEL_TF; feeds break classifier (D6) and edge-quality scoring.
- **TUNE.** T/F agreement ≥0.60 on matched boxes [spec §6.1 gate]; dedupe ≤1 label/edge/excursion.
- **DN refs.** DN_TF §5, DN_BOX §5 death rule, DN_SALIENCE.

### C4. EDGE_ACCEPTANCE — break confirmation
- **Definition.** A break is confirmed when `accept_closes` consecutive closes lie beyond the edge (default 1–2) **or** price has traded beyond `accept_bars` bars without closing back (default 3–5). A wick-only excursion is a poke (C3), never a break. [spec §3.3 close-beyond-tol; RT2 P2 = Dalton acceptance + Brooks "no breakout until follow-through" + classical close-confirmation]
- **Parameters.** `accept_closes`, `accept_bars` [MEASURE — the discriminating test: P(follow-through ≥1 ABR in 10 bars) under wick-break vs close-break vs 2-close definitions, RT2 §7]. `tol` as C1.
- **Cost.** O(1).
- **Failure modes.** News-window traverses are jump events, not structure (E3 suppresses *initiation*, not in-flight traverses — DN_TF §6). Back-and-forth close-outs demote to tease and may delete the box (spec §3.2).
- **Serves.** BOX death/conversion, line PIERCED state, LEVEL_CARRIED birth trigger.
- **TUNE.** golden `build_end` must equal the first unreversed close-beyond (D9); T→F relabel fixtures.
- **DN refs.** DN_BOX §5 death, DN_LINE §5 death/conversion, DN_TF §5.

### C5. CARRY / ROLE_REVERSAL — the level book
- **Definition.** A broken edge that price retests from the far side without re-penetrating within `retest_bars` becomes a carried level at the frozen edge price (dashed, projected right). Multi-route birth: `broken_edge`, `congestion_edge`, `continuation`, `session_extreme`, `formation_extreme` (MINI_LEVEL), `marker`. [spec §3.3/§3.6; RT2 P10 — cross-school: Brooks breakout test, Wyckoff BUEC, AMT prior-VA edges, classical throwback (Bulkowski return rates 62–68% daily stocks), ICT breaker; DN_LEVEL §5]
- **Parameters.** `retest_bars` [MEASURE]; zone per C2; consumption weight `depth0 ≈ 3` decremented per touch — demotes *decision weight*, not the drawing [DN_LEVEL §5]. **RT5 C5 WEAKENED:** per-touch depletion/weakening is a plausible inference, not a measured result — K&OW (2004) showed levels *coincide* with depth peaks and never measured consumption; `depth_consumed` ships as a signed prior pending the TUNE hold-rate-vs-touch-count test. Provisional (DR-MARKET) touch-ordinal numbers are invalidated, do not cite.
- **Cost.** O(1) per level per bar.
- **Failure modes.** FP: mechanical birth on every box break (460 born vs 48 drawn — Q2; the routes are *candidates*, F-layer decides ink). FN: all five non-broken-edge routes missing in v1 (Q2 coverage 23%/19%). Consumption-blind carries keep emitting context after depth exhaustion.
- **Serves.** LEVEL_CARRIED, MINI_LEVEL; obstacle list for F1 room term.
- **TUNE.** coverage ≥~80% via new routes [DN_LEVEL §7a]; sibling-price regression 9.5c → 1.3137; stated-end dash `t1` rule.
- **DN refs.** DN_LEVEL throughout; DN_SALIENCE stage 2 depth term.

### C6. EQUAL_EXTREMES — matched highs/lows
- **Definition.** Two same-side pivots with `|p₁−p₂| ≤ eq_tol`, separation `s ∈ [smin, smax]` bars. The middle pivot is the "middle section". [spec §3.8: tol ~2 pips (≤4 allowed), sep 4–28 bars; RT2 P6]
- **Parameters.** `eq_tol ≈ 2–4 pips ≈ 0.4–0.6·ABR` [golden, MEASURE in ABR units]; `smin/smax` from the golden separation histogram [MEASURE; RT4 prior 4–28].
- **Cost.** O(m²) over live pivots, m small.
- **Failure modes.** FP: shape-only pairs without relevance (529 born vs 85 drawn — Q2; needs the F-gate). The "liquidity pool above equal highs" motive is ICT FOLKLORE-as-mechanism; the *geometry* is testable: does poke-then-reject occur more after equal extremes than lone ones (RT2 §7 test 2).
- **Serves.** BRACKET M/W (+Mm/Ww inner-leg variants), MINI_LEVEL trigger side.
- **TUNE.** equality-tolerance and separation histograms [DN_BRACKET §7b].
- **DN refs.** DN_BRACKET §5; feeds DN_LEVEL formation_extreme.

### C7. POOR_EXTREME — unfinished-business flag
- **Definition.** An extreme formed by a flat cluster (≥3 bars ending within `tol`, no terminal rejection bar) is tagged POOR — elevated revisit expectation. [RT2 P5; Dalton poor highs/lows, PRACTITIONER]
- **Parameters.** flat-cluster length ≥3, `tol` [MEASURE revisit-within-N for tails vs flat extremes — RT2 §7 test 3].
- **Cost.** O(1) at pivot confirm.
- **Failure modes.** Untested in FX; treat as a *feature* on edges (quality downgrade), never a veto.
- **Serves.** edge-quality attribute on BOX/LEVEL objects; salience term.
- **DN refs.** DN_BOX §5 edge quality, DN_SALIENCE §5.

---

## D. Structure assembly — objects

### D1. BOX_LIFECYCLE — birth / buildup / freeze / death
- **Definition.** Birth when a sideways sequence (≥1 alternating θ₂ pivot pair inside the candidate span) produces a **second touch on the eventual breakout edge** [spec §3.1 constructive rule; Darvas gestation root, RT2 P13]. Edges from C1 over the *buildup window* `[build_start, build_end]` where `build_end` = last bar before the first never-re-entered close beyond an edge, `build_start` = first close of the longest contained run (D9). Edges frozen at birth; re-anchor only on ≥2 new extremes aligned within `eps` pre-break (logged `re_anchor`). Death: C4 traverse → edge spawns C5 level; drawn span may outlive buildup (D9).
- **Parameters.** height `h ∈ [~1·ABR, ~5·ABR]` (spec fixed 6–34 pips → re-express in ABR, MEASURE TUNE height/ABR histogram); width 9–100 bars [spec; provisional (DR-MARKET): detector life p50 11–13 bars]; containment ≥ ~90% of buildup closes inside [D9, MEASURE]; `buildup` definition: alternating bars within `1·ABR` of the edge, shrinking ranges, no fixed minimum [spec §3.7].
- **Cost.** O(span) per candidate evaluation; evaluations only on new θ₂ pivots.
- **Failure modes.** FP: `asia_session` auto-birth (66 born, 0 drawn — Q2; must compete on salience, DN_BOX §6); premature boxes on unconfirmed pivots (gestation gate helps — MEASURE precision/recall trade, RT2 P13); cluster edges taking poke wicks → bands too wide (DISAGREEMENT_1 9.23c). FN: tight mid-morning congestion with no session anchor (9.44a); boxes born at panel edge (9.48a, 9.22a) — partial-span evaluation required.
- **Serves.** BOX, RANGE_OPEN (session variant: running min/max 00:00–08:00 CET, converts on post-open containment or dies on break), CONTEXT_RANGE (one per window, coarse θ₂, 20–40 pips, dedupe by containment).
- **TUNE.** coverage ≥95% retained [DN_BOX §7a]; stated-height regressions; straddle rule (figure inside edges, 9.63a); buildup containment ≥90%.
- **DN refs.** DN_BOX throughout; DN_TF for calendar suppression.

### D2. LINE_HULL — anchored support/resistance lines
- **Definition.** Lower hull of confirmed swing lows / upper hull of highs over the θ₂ stream (monotone-chain append, O(1) amortised; O(n) rebuild on window eviction — n ≤ ~30). Candidate lines = hull edges through the newest pivot + tolerance-feasible non-adjacent pairs (ray semantics: "from the ~15:45 high" pins the start). Score = touches within `tol` − defended-side overshoot penalty − age penalty beyond `span_max`; select max; freeze on ≥2-touch confirm; re-anchor only via the logged margin rule. [RT4 §3.1, §12.3; DN_LINE §5]
- **Parameters.** `tol ≈ 1–1.5 pips` [golden touch convention; spec `max(1p, 0.25·ABR)`]; `span_max` for CONTEXT_LINE 3–8 h [spec §3.5]; steep legs `|slope| ≥ ~2·ABR/hr` may anchor on θ₁ [DN_LINE §5, MEASURE]; hysteresis margin `m` [RT4 §10].
- **Cost.** O(h²) candidate enumeration on tiny hull; per-bar O(1).
- **Failure modes.** FP: any late-day pivot pair births a line today (846 born vs 186 drawn; vetoed_offline drawn 36% — distance must demote, not veto, DN_LINE §6). Spike-vertex drag → B3 exclusion. FN: steep legs (9.21b/c), short local lines (9.19a, 9.17a), session-scale 7-h lines (9.23b). **Engine note (DISAGREEMENT_1):** max-touch hull pairs ≠ the neckline-style anchors Volman draws — only 2/57 endpointed golden lines have an engine line within 6 pips of both endpoints; anchors must prefer *named-bar/first-extreme* rays, not generic max-touch pairs.
- **Serves.** PATTERN_LINE, CONTEXT_LINE, squeeze walls, BRACKET necklines.
- **TUNE.** hull-vertex recall ≥90% of golden anchors [DN_LINE §7a]; slope-class match; born-span distribution ≈ golden (median 85 min).
- **DN refs.** DN_LINE throughout; DN_SWING for anchor input.

### D3. SQUEEZE_WALLS — compression between named barriers
- **Definition.** ≥2–3 consecutive bars with range ≤ `0.8·ABR` **and** bracketed by two existing live objects (box edges, lines, levels) within ~2·ABR of price, with the wall gap narrowing (`gap_t1 ≤ ~0.6·gap_t0`) and apex within ~10–15 bars of now. Rendered as short line(s) along micro-extremes (θ₁ hull) — golden shows lines, not ellipses. [spec §3.7; RT2 P12; DN_SQUEEZE §5]
- **Parameters.** bar-range ≤ 0.8·ABR [spec; MEASURE golden squeeze bars vs ambient]; min bars 2 (3 preferred) [spec]; narrowing 0.6 [RT4]; apex window 10–15 bars [RT1 decision-relevance].
- **Cost.** O(1) predicate + O(walls) gap check.
- **Failure modes.** FP: fires everywhere in flat Asia tape with no walls (176 born, ~0 drawn — Q2); the two-*named*-walls requirement is the fix. FN: walls of *different* types (box edge + rising line, 9.39a) — predicate must read the live-object book, not bar ranges alone. Post-hoc annotation path at the break bar = EXPERIMENTAL, golden-only [DN_SQUEEZE §6].
- **Serves.** SQUEEZE (rare — golden n=2); contraction regime as *context state* for salience is the common case.
- **TUNE.** both golden squeezes get candidates; born count collapses 176 → O(10s) [DN_SQUEEZE §7].
- **DN refs.** DN_SQUEEZE throughout.

### D4. BRACKET_MATCH — letter patterns on the pivot sequence
- **Definition.** Deterministic sequence predicates on the *persistence-pruned* θ₂ stream: `M` = H L H′ with |H−H′| ≤ eq_tol, sep ∈ [smin,smax], L the intervening low; `W` mirror; `Mm/Ww` = same template with a θ₁-scale inner leg flagged minor; `SHS` = L H L′ with |L−L′| ≤ shoulder_tol and H exceeding both by ≥ `head_min ≈ 1·ABR`; neckline = line through the intervening lows (D2 short-line path). Emitted only when decision-relevant: completing pivot within ~1–2·ABR of price, or its middle is a live barrier. [spec §3.8; RT2 P6; RT4 §12.7; DN_BRACKET §5]
- **Parameters.** `eq_tol`, `smin/smax`, `shoulder_tol`, `head_min` — all MEASURE from golden M/W histograms (ABR units).
- **Cost.** O(m) over the pivot sequence per new pivot.
- **Failure modes.** FP: equal-extreme births with no relevance gate (9.36a, 9.14a — most of 529). Nested duplicates sharing a pivot → NMS on pivot-id footprint. FN: SHS route absent; mixed-scale letters need the θ₁ marker; session-spanning brackets need pivot memory across session edges.
- **Serves.** BRACKET (all letters); middle section → MINI_LEVEL via C5 formation_extreme.
- **TUNE.** coverage ≥80% of 85, per-letter recall [DN_BRACKET §7a].
- **DN refs.** DN_BRACKET throughout.

### D5. BAR_MARKER — named-bar event ticks
- **Definition.** On a confirmed θ₁ pivot where the middle bar's extreme exceeds both neighbours by ≥ ~0.5·ABR → marker tick at that bar's extreme (evening/morning-star pattern), or a text-named single bar. [DN_TF §5; golden: 9.37c, 9.41b, 9.62a, 9.66a — 0/4 covered today]
- **Parameters.** dominance ≥ 0.5·ABR [MEASURE on the 4 goldens].
- **Cost.** O(1) at pivot confirm.
- **Failure modes.** FP: every 3-bar bump → marker spam; require pivot-confirm + dominance. FN: multi-bar ticks (9.66a "ticks over highs") may need a variant.
- **Serves.** BAR_MARKER.
- **TUNE.** ≥3/4 golden markers covered [DN_TF §7a].
- **DN refs.** DN_TF §5.

### D6. DOME_SEQ — shrinking counter-swings (computed fact, never drawn)
- **Definition.** Each counter-swing rising from a level/line and falling back = a dome; record height above/below the anchor per dome; flag mostly-shrinking sequences (golden-measured examples 22→13→15→8, 30→25→18→10 pips). The last flattened dome is where the squeeze forms. [spec §3.8; RT1 §4]
- **Parameters.** none additional — heights computed from the pivot stream.
- **Cost.** O(1) per dome.
- **Failure modes.** Dome vs pullback boundary is soft — measure on golden sequences before using as a signal input.
- **Serves.** derived fact for F1 scoring and the setup layer (pressure decay read).
- **DN refs.** spec §3.8; DN_SALIENCE (compression correlate).

---

## E. Context and gates

### E1. ROUND_GRID — the 00/50 reference lattice
- **Definition.** Context gridlines at .00/.50 (20-grid 00/20/40/60/80 in a declared low-vol regime). Never emitted as structure objects; only features: `magnet` (obstacle-side gridline within ~15 pips ahead), `counter-magnet` (within ~7–10 pips on stop side), `battle` (box straddling a round number with failures both ways). [spec §1/§4; RT1 §9.14; RT3 P2]
- **Parameters.** grid levels; low-vol switch `daily range < 60 pips` [spec — provisional (DR-MARKET, M2 descriptive): fires on 36% EURUSD days but only 9% GBPUSD → per-symbol quantile recommended]; magnet 12–30 pips, counter-magnet ~10 pips [spec §4; book pp.201–220].
- **Cost.** O(1).
- **Failure modes.** Treating gridlines as reversal levels — provisional (DR-MARKET): RND bounce contrast ns *and* F1/F2-invalidated; keep magnets as context features only. Never snap object geometry to the grid (RT4 §4.2 — fabricates agreement).
- **Serves.** salience feature, obstacle enumeration, battle flag.
- **DN refs.** DN_TF §5, DN_SALIENCE §5, DN_LEVEL §2 ("round numbers never birth a level").

### E2. SESSION_MARKS — the intraday rhythm prior
- **Definition.** CET-anchored regime labels: Asia 00:00–08:00 (documented low-activity trough — EVIDENCE: Dacorogna 1993, Ito & Hashimoto 2006), EU open ramp 08:00–10:00 (EVIDENCE: open-time activity jumps), EU lull ~12:00–14:00 and US lull ~18:00–20:00 [book/RT1 §5 PRACTITIONER], UK first hour 09:00–10:00 caution [PRACTITIONER]. Used as *salience priors* and evaluation demotions — not bans; Asia breakout attempts are low-conviction (thin liquidity → cascades cut both ways, BIS 2017). [RT3 §3 Q5; DN_TF §5]
- **Parameters.** window bounds above; suppression strength [MEASURE — per-15-min CET volatility curve on our feed is RT3 P7iii's pending self-measurement].
- **Cost.** O(1).
- **Failure modes.** The priors are era-stable physically (who is awake) but magnitudes drift; do not hardcode pip values per session — read through ABR.
- **Serves.** RANGE_OPEN birth window, F1 session term, STAND_ASIDE context.
- **DN refs.** DN_TF §5, DN_BOX RANGE_OPEN, DN_SALIENCE §5.

### E3. NEWS_WINDOWS — scheduled-event stand-asides
- **Definition.** Hard calendar windows (CET) inside which level/edge breaks are not *initiated* as structure and objects are neither born nor killed on the window's bars alone:

  | window (CET) | basis |
  |---|---|
  | 14:30 ±15m — US data | EVIDENCE: ABDV 2003 conditional-mean jumps; Chaboud 2014 liquidity thinnest first minute |
  | 14:15 ±10m — ECB fix | EVIDENCE: Krohn-Mueller-Whelan 2024 ~2bp pre-fix USD drift then reversion — **new vs spec v1** (RT3's "~2.5bp" was a misquote — RT5 C9) |
  | 16:50–17:10 — WMR fix | EVIDENCE: Evans 2018 (5-min window since Feb-2015; month-end amplified) — **spec v1's "16:00 CET" is the London-local time; correct CET/CEST is 17:00 year-round** |
  | 16:00 ±10m — NY option cut | volume spike EVIDENCE (Berger, Chaboud, Chernenko, Howorka & Wright 2008, FRB IFDP 863 → JIE — RT3's Ito & Hashimoto attribution was a mis-citation, RT5 C9); pinning unproven in FX → soft gate |
  | 01:55 — Tokyo fix (winter-only; 02:55 CEST in summer — JST never shifts) | noise source inside Asia range, not an edge signal |

  All window widths (±15, ±10, the WMR span) are our engineering choice, not the
  papers' (RT5 C9).

  Provisional (DR-MARKET, M2 descriptive): largest spike cluster sits at **08:00–09:00 CET** (8.9–10.9% EURUSD/GBPUSD) — a ~07:55–09:30 caution window is a v1.1 proposal (SPEC_v1_CRITIQUE).
- **Parameters.** window bounds above; `N ≈ ±30 min` seed for unscheduled major releases [RT1 §9.16]; hard-veto trigger: bar range > `ξ·ABR`, `ξ ≈ 2`, plus spread expansion [RT1 §9.16–17].
- **Cost.** O(1).
- **Failure modes.** A real traverse already underway through a window must not be retroactively suppressed (DN_TF §6). Windows are CET — the feed-clock mapping (A2) must be right or the gates fire one hour off (Ruling 1 lesson).
- **Serves.** STAND_ASIDE reasons; suppression flags on D1/D2 births.
- **DN refs.** DN_TF §5 table.

### E4. VOL_REGIME — chop/abnormal-volatility vetoes
- **Definition.** Three cheap detectors feeding STAND_ASIDE: (i) `CI(n)` Dreiss choppiness — high → overlapping directionless tape [PRACTITIONER, RT4 §5.1]; (ii) `ER(n)` Kaufman efficiency on closes [PRACTITIONER]; (iii) range-shift alarm — CUSUM/FOCuS on the bar-range stream, or `range_t > q95` of rolling same-time-of-day ranges [RT4 §5.2, EVIDENCE as algorithms]; plus book rules: >τ fraction of last W bars >2·ABR → frantic-vol veto; median range < ρ pips → dead-vol veto [RT1 §9.17].
- **Parameters.** `n ≈ 14` (CI), `≈ 10` (ER) [RT4 §12.9]; `τ`, `ρ`, `ξ` [MEASURE — calibrate on golden no-object vs drawn panels, RT4 §12.9].
- **Cost.** O(1) rolling; FOCuS ~O(log n) if used.
- **Failure modes.** M5 EURUSD is mildly mean-reverting everywhere (provisional DR-MARKET M6: lag-1 −0.03…−0.07) — chop is baseline behaviour, so the veto must separate *extreme* chop, not ordinary overlap. Thresholds uncalibrated = today's "everything fires" bug.
- **Serves.** STAND_ASIDE reasons {news, lull, chop, frantic-vol, dead-vol}; F1 demotion terms.
- **DN refs.** DN_TF §5, DN_SALIENCE §5.

### E5. EMA_PRESSURE — dominant-side state with hysteresis
- **Definition.** `pressure ∈ {UP, DOWN, NEUTRAL}`: EMA25 slope sign over `m` bars + side-of-EMA occupancy + HH/HL structure, with **hysteresis** — a flattening average keeps its prior sign until the average truly turns or bars persist on the other side ≥ `p` bars. [spec §4; book p.200/p.227, Fig 7.9 ~50-min counter-drift inside a bearish box; RT1 §9.7–8]
- **Parameters.** `ema_len = 25` [spec; provisional (DR-MARKET M6 — module passed review): no kink at 25, L≈20–50 equivalent → treat EMA touches as context, not events]; `m`, `p` [MEASURE; seed p ≈ 10 bars from Fig 7.9].
- **Cost.** O(1).
- **Failure modes.** EMA-direction ban (veto counter-pressure trades) is a *trading* rule — for perception it is a salience/validation prior; a long pullback may legitimately turn the average (book exception, RT1 §5.6). Whipsaw around a flat EMA → hysteresis, not twitching.
- **Serves.** break-classifier confluence, squeeze wall (pattern vs EMA), salience direction prior.
- **DN refs.** DN_TF §5, DN_SQUEEZE walls, DN_SALIENCE.

### F. Selection layer — what gets drawn

### F1. SALIENCE_SCORE — causal ranking of candidates
- **Definition.** Every evaluated candidate (born or not — the cand_log universe) gets
  `score = w1·touches_in_tol + w2·span + w3·prom(anchors) + w4·recency + w5·proximity(dist/ABR) + w6·session_prior − w7·depth_consumed − penalty_per_object (MDL)`. All terms causal. `w7·depth_consumed` is a **signed prior, not a fact** — per-touch depletion is unmeasured (RT5 C5; validate via the TUNE hold-rate-vs-touch-count test before trusting the sign). Weights hand-set from the TUNE drawn/ignored separator tables with documented provenance — no learned search [DN_SALIENCE §5; RT4 §9].
- **Parameters.** w1..w7, penalty, margin `m` [MEASURE; separators today: line span 205 vs 95 min, touches 4.5 vs 3.4, n_active 6.4 vs 5.4; `fwd_*` terms are WITHDRAWN A4.2 — banned as inputs (Ruling 5b)].
- **Cost.** O(candidates), tiny.
- **Failure modes.** Weight-set without provenance recreates the D5 hidden-coefficient failure; the score must separate *drawn* from *evaluated* (gates that answer "is another structure active" do not select — Q2 headline).
- **Serves.** all object types; decides ink.
- **TUNE.** born set ≈ drawn set (coverage ≥ Q2 levels at new born counts); per-panel counts inside the golden distribution.
- **DN refs.** DN_SALIENCE §5 stages 2.

### F2. NMS + HYSTERESIS + BUDGET — the drawing discipline
- **Definition.** Rank candidates; suppress any whose footprint (type-family × price band × time-IoU on the 84-bar canvas) overlaps a higher-ranked live object, with a per-type-pair "nested-allowed" flag (didactic inner box coexists with parent, 9.6a). Rank hysteresis: incumbent displaced only if challenger exceeds score by margin `m`, plus minimum dwell bars. Budget = consequence: emit top-k, signal sub-budget ~3, context sub-budget small, hard ceiling ~8–9; if < ~1–2 signal objects score positive → emit STAND_ASIDE, never fill with noise. [RT4 §9.4–10; DN_SALIENCE §5 stages 3–5; spec §5]
- **Parameters.** IoU thresholds per type pair [MEASURE]; `m` [RT4]; budgets: median ~3, p90 ≤ ~6 golden distribution [Q2].
- **Cost.** trivial.
- **Failure modes.** Containment-blind IoU kills legitimately nested boxes; cooldown-style vetoes kill real structures (40% of cooldown-vetoed boxes were drawn — Q2). Rate caps bound *how many*; the score chooses *which* — caps alone don't fix selection (Ruling 7).
- **Serves.** the canvas itself.
- **DN refs.** DN_SALIENCE §5; DN_BOX §6 nested cases.

---

## Dependency order (build sequence implied)

A1–A2 (scale, clock) → B1–B3 (pivots, prominence, spike flags) → C1–C7 (clusters, zones, pokes,
acceptance, carries, equality, extremes) → D1–D6 (box, line, squeeze, bracket, marker, dome) →
E1–E5 (grid, sessions, news, regime, pressure) → F1–F2 (score → NMS → hysteresis → budget →
STAND_ASIDE). Nothing in D may reference future bars; nothing in F may reference outcomes.

## The measurement queue (what fixes each MEASURE parameter)

| primitive | parameter | measurement on TUNE (golden + bars) |
|---|---|---|
| B1 | k₁, k₂ | golden anchor-leg displacement histogram; θ₂ count/panel ≤ ~8 (DN_SWING §7) |
| B2 | pmin | prom-rank vs golden-anchor membership knee |
| C1 | eps, minPts | golden edge touch histogram; company-rule cases (9.15b, 9.63a) |
| C2 | z_near, z_far | poke-depth-past-level q75 (RT4 §12.5) |
| C3 | tease_tol | poke-depth distribution vs edge height |
| C4 | accept_closes/bars | wick vs close vs 2-close follow-through comparison (RT2 §7 test 1) |
| C6/D4 | eq_tol, smin/smax | golden M/W equality + separation histograms (ABR units) |
| D1 | height bounds | golden box height/ABR histogram (spec 6–34 p fixed-pip → ABR) |
| D2 | tol, span_max, steep gate | golden line touch/spans; steep-leg anchor check (9.21b/c) |
| D3 | 0.8·ABR, 0.6 narrowing | golden squeeze bars vs ambient |
| D5 | dominance 0.5·ABR | the 4 golden markers |
| E3 | windows | per-15-min CET volatility curve on feed (RT3 P7iii) |
| E4 | CI/ER/τ/ρ | golden no-object vs drawn panels |
| E5 | m, p | Fig 7.9-type counter-drift cases on TUNE |
| F1 | w1..w7, m, IoU | drawn-vs-ignored separator tables (Q2 §4 causal features only) |

— End of PRIMITIVES_CATALOGUE —
