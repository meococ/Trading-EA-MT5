# SPEC_v1_CRITIQUE — where spec v1 is weak, missing, or contradicted

**Lane:** RESEARCH-SYNTH (B4). **Written:** 2026-09-21 ~17:30Z.
**Object under review:** `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md` + `params_v1.json`.
**Evidence base:** RT1–RT4 (accepted, Ruling 4); RT5 adversarial review (this folder);
golden measurements `Q2_MEASUREMENTS.md`, `GOLDEN_AUDIT.md` (D8/D9); first TUNE eval
(`EVAL_TUNE.md`, `DISAGREEMENT_1.md`); Lead Rulings 2–7.
**Status:** the v1.1 diffs below are **numbered proposals only — the Lead rules.**
Market-study numbers are **provisional (DR-MARKET, under review)** and are flagged
per-row; REVIEW_2 invalidated all M3 outcome-derived inference (F1/F2) and the M4/M4b
per-symbol leg (F3) — nothing resting on them may become provenance until re-run.

---

## 1. Contradicted by the book itself (RT1 §7 verdict table)

| spec v1 says | the book actually does | source |
|---|---|---|
| "Edges are fixed once set" (§20) — **but §109–111 already encode re-anchor/tighten rules: the spec contradicts itself** (RT5 C6) | Two-sided rule: immutable to pokes, **adjustable pre-break on a confirmed new alignment** (bar-13 adjustment; p.223 re-draw); adopt the versioned reading, fix §20 wording | RT1 §6.3 |
| Tease and false as separate classes (§3.3) | One event can be both; labels overlap — primary label + attributes | RT1 §4.4/§7 |
| Room gate unspecified (§4 mentions 14-pip rule only in passing) | **14 pips is a hard gate**: <14 skip; ~13 soft; ≤10 never; first obstacle at 14–20 → exit *at* the obstacle, not at 20 (pp.167–171) | RT1 §4.4 |
| Dotted style = CONTEXT_* (§2, convention) | Book gives no style rule — our convention exceeds evidence (mark as convention, not claim) | RT1 §7 |
| Draw only emitted objects | Author *names* obstacles he does not draw — the drawn set is a ranked subset of the considered set; spec has no such ranking | RT1 §7 + Q2 §4 |
| Boxes as primary objects | Box is often didactic; the minimal live object is the signal line (FPAS ch.10) | RT1 §4.1 |
| EMA ban absolute | Long, drawn-out pullbacks may turn the average — counter-EMA trades allowed then (p.227 exception) | RT1 §5.6 |

## 2. Weakened by evidence (RT3)

1. **The fix clock is wrong.** Spec `news_windows_cet` lists "15:55–16:10" for fixes
   and notes "16:00 CET" — the WMR fix is London 16:00 = **17:00 CET/CEST
   year-round** (Evans 2018; 5-min window since Feb-2015). The ECB fix at
   **14:15 CET** is absent entirely (Krohn-Mueller-Whelan 2024: **~2bp** pre-fix
   drift then revert — RT3's "~2.5bp" was a misquote, RT5 C9). The NY 10:00 ET
   option cut (**16:00 CET**) has a volume spike (EVIDENCE: Berger, Chaboud,
   Chernenko, Howorka & Wright, IFDP 863 → JIE 2008 — not Ito & Hashimoto as
   RT3 printed, RT5 C9) but no proven pinning in FX → soft gate only. All window
   widths are our engineering choice, not the papers'. *(RT3 §2 table, P4; RT5 C9)*
2. **"Strength" vocabulary creeps in.** Spec §4 grades obstacles "minor / double /
   dense" — fine as a geometry description, but no touch-count strengthening and no
   *asserted* level-strength score may follow: Osler (2000) falsified analysts' own
   strong/weak labels — note this kills claimed labels, it does not forbid causal,
   measurable ranking (RT5 C3). The mirror claim "levels weaken per touch" is an
   unmeasured hypothesis, not a K&OW result (RT5 C5): `depth_consumed` ships as a
   signed prior pending the TUNE hold-rate-vs-touch-count test. (RT3 §4)
3. **Post-break expectations are unpriced.** Spec assumes a break "works" as
   continuation; the cross-school base-rate fight is unresolved *and
   incommensurate* (Brooks ~80% of breakout *attempts* fail in a trading-range
   context, E-mini M5; Bulkowski 15–34% ≥10%-travel confirmed-close failures,
   daily equities — [snippet-only, HTTP 406] pending re-fetch; Darvas assumes
   continuation). Perception should report the break *class*, not a directional
   prior. (RT2 §4.1, §7 test 7; RT5 C7)
4. **Cascade window is real but small on average.** Osler 2005's honest effect is
   ~0.7bp/15min mean, fat-tailed — supports a post-traverse watch window, not a
   chase rule. (RT3 Q2)
5. **Level = zone, not line.** Spec §2 already renders edges as bands — good —
   but the *storage* should carry the asymmetry (near side TP wall, far side stop
   cluster); the far side extends further. (RT3 P1)

## 3. Missing entirely (RT2/RT4 + Q2 + DISAGREEMENT_1)

1. **No amplitude-filtered pivot definition.** Spec never defines a swing. The v1
   engine's raw-pip retrace produces the micro-pivot flood → 620 born vs 111 drawn
   boxes, 846 vs 186 lines (Q2). The DC skeleton (θ = k·ABR) with persistence
   pruning is the documented fix. (RT4 §2.3, §12.1; DN_SWING)
2. **No selection layer.** Spec §5 is a priority *list*; the engine needs a
   *ranking* — Q2's headline: vetoed candidates are drawn at equal-or-higher rates
   than born ones (cooldown-vetoed boxes 40% drawn). Gates that ask "is another
   structure active?" cannot answer "would Volman draw it?".
3. **No hysteresis/NMS.** Rank-boundary flicker and near-twin rebirths are logged
   failure modes (DISAGREEMENT_1 §3); the spec's "edge stability ≈ 0 unlogged
   moves" gate has no mechanism to achieve it.
4. **MINI_LEVEL has no birth route; LEVEL_CARRIED has one route of six.** Coverage
   19%/23% (Q2 §3): congestion_edge, continuation, session_extreme,
   formation_extreme, marker routes are all absent. BAR_MARKER: no route (0/4).
5. **SQUEEZE fires on bar ranges alone** — no wall requirement: 176 born, ~0 drawn.
   Golden shows squeezes drawn as *short lines between named walls*, not ellipses.
6. **LABEL_TF as standalone objects** (209 mechanical births) instead of attribute
   events on live edges, deduped per excursion.
7. **Window vs memory conflated.** The 84-bar draw window is right, but structural
   pivots and context anchors must persist for the session (7-h CONTEXT_LINE 9.23b;
   carried levels "earlier same day" per §1). Spec §1 conflates the two.
8. **Box semantics underspecified for eval.** D9: drawn right edge ≠ containment
   end; stated height = pre-break range. Spec §3.3's "right edge closes 6–18 bars
   after break" describes *drawing*, while matching must use `build_start..build_end`
   (Ruling 7.3). The spec must state both clocks.
9. **Anchor semantics.** Lines are "from the ~15:45 high" — named-bar ray
   semantics. Generic max-touch fits miss the neckline-style anchors
   (DISAGREEMENT_1: 2/57 endpointed golden lines matched both ends). Spec §3.4's
   "fit for maximum touches" needs the named-anchor clause first.
10. **No draw-vs-consider distinction.** The author considers more than he draws;
    spec has no considered-set concept — hence no room-rule obstacles that aren't
    drawn (14-pip check needs *unseen* obstacles enumerated).
11. **Stand-aside under-powered.** Spec emits STAND_ASIDE but the perception output
    has no first-class reason codes; the casebook marks skips at ~entry frequency
    (RT1 §5, 138-chart measurement).
12. **Provenance discipline absent.** v1 params carry numbers with no source; the
    D4 retroactive log shows thresholds bent until fixtures passed. Every parameter
    needs a provenance tag (SPEC/book page/MEASURE/EVIDENCE) — lintable. (Ruling 2 §2.2.2)

## 4. Contradicted or corrected by golden measurements (Q2 / D8 / D9 / eval)

| spec v1 | golden/eval fact | consequence |
|---|---|---|
| Gates/cooldowns/envelopes as selectors (params: `birth_cooldown_bars`, `one_active`, offline/stale vetoes) | vetoed-but-drawn rates 23–40% ≈ or > born rates (Q2 §4) | selection must be ranking, not vetoes |
| ~3 objects typical, cap 8 (§5) | mean 3.0, max ~9 over 138 charts (RT1 EVIDENCE-lite); v1 engine emits ~57/day | budget = measured distribution; split signal/context sub-budgets |
| Squeeze = dashed ellipse (§2) | golden squeezes are short inner *lines* (9.33a, 9.39a) | render grammar fix |
| PATTERN_LINE "fit for maximum touches" (§3.4) | endpoints matter (named-bar rays); only 2/57 golden endpointed lines have an engine line within 6p of both ends | anchor-first selection rule |
| Asia RANGE_OPEN converts to BOX routinely (§3.1c) | asia_session route: 66 born, **0 drawn** | Asia box is context ink; competes on salience |
| Match criteria fixed tolerances (§6.1) | eye-labelled golden coords carry ±5p/±10min | tie match tolerances to the object's precision flag (Ruling 7.2) |
| "never more than 1 trading day of structure" (§1) | carried levels legitimately originate earlier same day — already allowed; but multi-hour CONTEXT_LINE anchors need session-scale pivot memory | window ≠ memory (§3.7 above) |
| right edge closes 6–18 bars post-break (§3.3) | drawn span may outlive the buildup era arbitrarily (D9) | separate containment clock from drawing clock |

## 5. Provisional market facts (DR-MARKET, under review — none is provenance)

**Module status after REVIEW_2:** M0 clock, M2 rhythm (descriptive) and M6 momentum
passed; M3 levels, M4/M4b boxes, M5 lines failed (F1–F3); every pooled CI/p/q in
M3–M5 is anti-conservative (F2). Facts below are grouped by exposure.

**Descriptive, module passed review — still provisional:**
- Asia range height: EURUSD median **22.6 pips**, p90 42; ≤10p only ~3%; >27p ~35%
  (M2). Spec `asia.height_max_pips = 27` truncates a third of days.
- Daily range ≤60p: EURUSD 36%, GBPUSD **9%** — the low-vol grid switch is
  symbol-biased (M2/M7).
- Spike clusters at **08:00 and 09:00 CET** (8.9–10.9% EURUSD/GBPUSD) — the largest
  bursts sit outside every current window (M2).
- EU-open range multiplier ~1.4–1.9×; no end-of-day NY surge (M2 — matches
  Ito & Hashimoto EVIDENCE).
- EMA25 not special: counter-pivot distance to EMA_L monotone in L (M6) — keep
  EMA25 as *arbitrary smooth guide*; no EMA-touch events.
- M5 returns mildly mean-reverting in all sessions (M6): chop is baseline, the
  veto must target extreme overlap only.
- Detector-declared boxes (M4, descriptive only): height p50 ~17p EURUSD,
  life median ~12 bars, poke depth median ~0.8–1.0p.

**Invalidated pending remediation — may not support any rule:**
- Swing-level bounce premium (+1.1–1.5pt), first-touch dominance, ~1h level
  half-life, overshoot p90 ≈0.5–0.7 ABR (zone-width claim), retest/role-reversal
  null, round-number null, Asia-H/L continuation sign, third-touch line premium —
  all F1/F2-exposed (REVIEW_2 headline invalidation). Ruling 5(d) items 1–5 cited
  these as priors; they revert to *unproven hypotheses to re-measure*.
- The voided pre-review +13.8pt deep-poke claim stays voided (D22).

## 6. v1.1 proposals (numbered; the Lead rules)

**P1 — Insert spec §3.0 "Swing skeleton".** Define pivots as a two-threshold
directional-change state machine on wick extremes (θ₁ ≈ 0.8·ABR micro,
θ₂ ≈ 2–3·ABR structural) with a persistence floor (~0.5·ABR) and `confirm_lag`
telemetry. *Rationale:* the missing definition is the root of v1 over-production;
the only family with published FX scaling laws (RT4 §2.3, Glattfelder 2011).

**P2 — Rewrite §3.2 edge fixity.** "Edges are immutable to pokes; pre-break
re-anchor allowed only on ≥2 new extremes aligned within tol (logged, versioned);
pre-break tighten to the latest touch when within tol." *Rationale:* RT1 §6.3
book evidence — v1's "fixed once set" is half the rule.

**P3 — Break classes become labels-with-attributes.** `primary ∈ {proper, tease,
false}` plus attribute flags; overlaps legal. *Rationale:* book usage overlaps
(RT1 §7); a graded confidence output beats binarised classes (p.223).

**P4 — Encode D9.** Objects carry `build_start/build_end` (containment era)
distinct from drawn span `t0/t1`; height statements bind to the buildup window;
eval matches containment on buildup, drawing on span. *Rationale:* GOLDEN_AUDIT D9;
Ruling 7.3.

**P5 — Room rule explicit.** `room = distance to nearest enumerated obstacle`;
veto <14 pips, soft 13, hard floor 10; obstacle at 14–20 → exit target = obstacle.
Obstacles include *undrawn* named extremes (considered set). *Rationale:*
pp.167–171 via RT1; contradicts any 2R-style gate elsewhere.

**P6 — Levels stored as asymmetric zones.** Price = defended extreme; near side
`max(1p, 0.15·ABR)`, far side near + q75(poke depth), cap ~0.5·ABR. *Rationale:*
Osler 2003 order asymmetry; q75 measured on TUNE (RT4 §12.5). *(The DR-MARKET
0.25–0.35·ABR figure is provisional/invalidated — do not copy it.)*

**P7 — Fix the calendar.** WMR window → 16:50–17:10 CET (London 16:00 local,
year-round); add ECB fix 14:15 ±10m; demote NY option cut (16:00 ±10m) to soft;
note Tokyo fix 01:55 CET is winter-only (02:55 CEST summer); state that all
window widths are engineering choices; add caution demotion ~07:55–09:30 CET
*(provisional M2 spike clusters)*. *Rationale:* RT3 P4 corrections; Evans 2018;
Krohn-Mueller-Whelan 2024 (~2bp — RT3 misquoted 2.5bp); the option-cut spike
source is Berger et al. 2008, not Ito & Hashimoto (RT5 C9).

**P8 — Ban ex-ante strength scoring.** Remove/forbid touch-count strengthening,
"strong level" ratings, nth-touch rules anywhere in the object model; replace with
`depth_consumed` weight that decays per touch. *Rationale:* Osler 2000 falsified
*asserted* strength labels (it does not forbid causal measurable ranking — RT5
C3); per-touch depletion is an unmeasured hypothesis (K&OW showed coincidence
with depth, never consumption — RT5 C5): ship it as a signed prior, then run the
TUNE hold-rate-vs-touch-count test.

**P9 — Replace vetoes with the selection layer.** §5 becomes: score (causal
features) → NMS (footprint IoU, nested-allowed flags) → rank hysteresis (margin m,
dwell) → budget as consequence (signal ~3 median / context small / hard ~8–9).
Cooldown, governing, offline/stale and envelope vetoes are deleted as killers and
demoted to score terms. *Rationale:* Q2 §4 + Ruling 7; DISAGREEMENT_1.

**P10 — Add the missing birth routes.** MINI_LEVEL `formation_extreme`; LEVEL_
CARRIED routes `congestion_edge`, `continuation`, `session_extreme`, `marker`;
BAR_MARKER route (θ₁-pivot middle-bar dominance). *Rationale:* Q2 coverage
19–36%/0-of-4; DN_LEVEL §5, DN_TF §5.

**P11 — SQUEEZE requires two named live walls** + narrowing gap + apex proximity;
render as short inner lines (golden grammar), not the spec's dashed ellipse.
*Rationale:* 176-born/~0-drawn (Q2); DN_SQUEEZE; golden evidence.

**P12 — LABEL_TF = attribute event.** One label per edge per excursion; T→F
relabel ≤3 bars; never a standalone object. *Rationale:* 209 mechanical births
vs the book's attribute usage (RT1 §6.2–6.3; DN_TF §5).

**P13 — RANGE_OPEN is context ink.** The Asian range tracker runs 00:00–08:00 CET
but competes in the *context* sub-budget; converts to BOX only when the session
range is the referenced structure; `asia.height_max` → ~40 pips or ABR-scaled
*(provisional M2: median 22.6, p90 42)*; thin-flag ≤10p stays (rare: ~3%).
*Rationale:* 66 born / 0 drawn (Q2); provisional market distribution.

**P14 — Split the budget.** `signal` sub-budget (book's ~3) vs `context`
sub-budget (dotted RANGE_OPEN/CONTEXT_LINE/CONTEXT_RANGE); T/F letters and
markers consume neither. *Rationale:* RT1 didactic-vs-live distinction; spec §5
already half-implies it.

**P15 — Line anchors are named-bar rays first.** Candidate lines anchor on hull
vertices *with the first-anchor = wave-origin/named extreme*; max-touch selects
among anchored candidates; steep legs (≥~2·ABR/hr) may use θ₁ anchors; distance
demotes, never vetoes. *Rationale:* DISAGREEMENT_1 (2/57); DN_LINE §5–6; RT1
named-anchor grammar.

**P16 — Freeze discipline becomes law.** All geometry commits once; every change
is a named logged event {re_anchor, tighten, break, consume, convert}; the §6.1
"no unlogged edge move" gate extends to all object types. *Rationale:* RT4 §10;
Ruling 7's jitter findings.

**P17 — Separate memory from window.** Pivot store and object memory persist for
the session; the 84-bar window governs *drawing*, not *knowing*. *Rationale:*
9.23b 7-h context line; carried levels earlier-same-day (§1); DN_SWING §6 FN.

**P18 — Eval tolerances follow label precision.** §6.1 matching keyed to the
golden object's `prec` flag (eye ±5p/±10min vs meas ±2p); the jitter/self-test
requirements move into the spec's validation protocol (Ruling 7 items 1–2).
*Rationale:* a ruler tighter than its labels measures noise — v1's 0.05 box
recall is partly a ruler artifact (Q2 loose-match coverage was 95%).

**P19 — Parameter provenance is a build gate.** Every entry in params carries
`prov: SPEC|book|MEASURE:<table>|EVIDENCE:<ref>`; a CI lint rejects untagged
numbers. *Rationale:* Ruling 2 §2.2.2 / D4 — numbers bent until green is the
failure mode this spec exists to prevent.

**P20 — Codify the hindsight caveat.** Golden is setup-selected; recall gates are
read with that bias; `fwd_*`-type outcome fields are banned as inputs (A4.2 /
Ruling 5b); selection features must be causal correlates (compression, buildup-at-
barrier, span, touches, n_active, session). *Rationale:* the withdrawn columns
were the strongest separators — the honest replacements must be engineered.

**P21 — Market-fact contingency clause (provisional, DR-MARKET).** When the
remediated M3/M4 lands, revisit in order: (i) level age-decay term in F1 if the
half-life survives; (ii) consumption semantics if touch-ordinal decay survives;
(iii) zone half-widths from remediated F-O quantiles; (iv) Asia H/L
directional-context flag if the continuation sign survives. Until then none of
these may enter params. *Rationale:* REVIEW_2 F1/F2 invalidation list.

## 7. What spec v1 already gets right (keep)

- The object grammar (types, styles, "never drawn" list) — validated by the
  golden audit as the author's actual vocabulary.
- `tol = max(1p, 0.25·ABR)` — sits inside the plausible overshoot band.
- Close-based break definition, poke-never-moves-edge, T→F relabel window,
  freeze-then-logged-reanchor *principle* (needs the P2/P16 completion).
- CET clock mandate and DST test requirement (D3 proved it matters).
- The golden-set methodology itself (calibrate → refine → validate → overlay QA)
  — the yardstick is the strongest artifact the project has.

— End of SPEC_v1_CRITIQUE —
