# DR_CHECK — BOX-LAB's independent verification of DR-BOX numbers (R65 §65.3)

Ruler-exact = `evalcheck/eval_v2.py` imported as-is (file hash
`b21d6f29bd88` — the §65.3.1 pin `50e11fd5` is the engine-commit pin;
the module is imported, never copied). Hypothetical event object:
`type=BOX`, `lo/hi` = cand edges (pips), `t0_raw` = earlier-pivot bar →
minutes, `t1_raw` = τ (live-at-τ), `t_birth` = confirm bar, `w0/w1` =
panel window → τ. No `bs`/`be`/`break_bar` recorded → the ruler's
coverage fallback applies, same as every v0 event box (v0's
`_make_box` records no containment window).

## 1. Reach reconcile (DR_LOG 02:34Z claim: "51/119")

| definition | count |
|---|---|
| DR-BOX edge-match, born ≤ τ | **51/119** — **reproduced exactly** |
| ruler-exact `V2.match_detail`, born ≤ τ, ranked first | **46/119** |

- Denominator identical: 119 = box family (BOX 106 + RANGE_OPEN 7 +
  CONTEXT_RANGE 6), `tau ≥ w0`, `V2.scorable` — same set.
- Tolerance identical: golden's own `tol_px` (own-precision) — same
  count 51 under their definition.
- τ identical: cand confirm bar ≤ golden τ.
- **The only difference: DR-BOX tested edges only.** The ruler
  additionally requires the object's drawn span to cover ≥50% of the
  golden containment window `build_start..build_end`
  (`containment_iou` or the `coverage` fallback when no eng window is
  recorded — always the case for event boxes).
- The 5 edge-match-but-ruler-fail goldens: **9.6a, 9.13a, 9.32b,
  9.36b, 9.53a** — all fail `box_span` (span coverage < 0.5).
- Ruler hits by spec: 41 BOX + 4 CONTEXT_RANGE + 1 RANGE_OPEN.
- By match route: 31 `containment_iou`, 15 `coverage`.

**Checked: 51/119 → DIFFERS (edge-match only; ruler-exact = 46/119).**
DR-BOX should cite 46/119 as the reachable set (§65.4).

## 2. Throttle matrix redone on the 46 ruler-exact reachable set

Rules preregistered in BOX_LOG.md 02:50Z before measuring; no rule
added after. Survival = the born (or final mutated) object passes
`V2.match_detail` at τ. Births/panel measured over all 198 panels.

### ~1 birth/panel

| rule | births med (avg) | survives |
|---|---|---|
| **UIP-all** (one object; every non-shadowed event rewrites lo/hi/t0) | 1.0 (1.00) | **14/46** |
| **UIP-rd** (T1 from R62: only `range_double_*` rewrites) | 1.0 (1.00) | **13/46** |
| first-cand-only | 1.0 (1.00) | 3/46 |
| governing + in-place re-anchor, X=3 ABR | 1.0 (1.54) | 6/46 |
| touch-defer S=200 | 1.0 (1.39) | 3/46 |

### ~2 births/panel

| rule | births med (avg) | survives |
|---|---|---|
| governing-release X=3 ABR | 1.0 (1.62) | 5/46 |
| hard cap: first 2 cands | 2.0 (2.00) | 4/46 |
| dedup D=12p, cap 2 distinct | 2.0 (1.98) | 5/46 |
| touch-defer S=80 | 9.0 (12.43) | 3/46 — misses the operating point entirely |

**Verdict, unchanged in shape from R62:** the best within-budget rule
(UIP, one mutating object) keeps **14/46 ≈ 30%** of ruler-exact
reachable goldens — the same ~1/3 as on the 15-set (5/15). The larger
reachable set does not rescue the throttle; the right cand is still
causally indistinguishable. Raw stream keeps 46 at ~6.5 births/panel.

## 3. DR-BOX number recomputations (running log)

| claim (DR_LOG time) | DR-BOX | BOX-LAB recount | verdict |
|---|---|---|---|
| event stream reach (02:34Z) | 51/119 | 51/119 under their edge-match def; **46/119 ruler-exact** | **differs** — no window test; cite 46/119 |
| med cands/panel (02:34Z) | 46 | 49 all panels / 47 golden panels | differs slightly — panel-set def TBD |
| live cands ≤ τ (02:34Z) | 40 | 40 (med per golden cell) | **checked** |
| freshest-born strict-top (02:44Z) | 20/51 | 20/51 (edge-match def, last born ≤ τ) | **checked** exactly |
| matching-cand span IoU vs golden build window (02:44Z) | med .16, ≥0.5 in 27/145 | ≥0.5 count identical (27); med .19 on 124 non-degenerate-window pairs (their 145 includes degenerate-window pairs → med shifts toward .16) | **checked** (≈, def reconstructed) |
| H-frame: non-match cand covers more window bars (02:44Z) | 80/119 | 77/119 (non-match cand covers more of golden build window than best match, live ≤ τ) | **checked** (≈, minor def diff) |
| round-straddle descriptive (02:44Z) | 36% of goldens | 43/119 = 36.1% (50/100-pip level inside golden band) | **checked** exactly |
| straddle non-discriminating (02:44Z) | match 22% vs nonmatch 26% | cand-level: match 32/145 = 22% vs nonmatch 26% | **checked** exactly |
| union of 23 feature orderings (02:44Z) | 31/51 → 20/51 indistinguishable | pending DR's ordering list | pending def |
| H-hind: brk_bar +0.12 vs null p95 +0.46 (02:44Z) | flat | pending DR's stat def | pending def |

### DR_BOX_SELECTION.md claims (recomputed 02:5x–03:0xZ)

| claim | DR-BOX | BOX-LAB recount | verdict |
|---|---|---|---|
| cand routes rd/pb | 7706 / 2014 | 7706 / 2014 | **checked** exact |
| unreachable decomp | one-edge 20 / both-never-paired 17 / neither 16 / envelope 15 | identical | **checked** exact |
| nearest-cand to unreachable edges | med 10.5p, 7 ≤3p, 28 ≤8p | 10.5 / 7 / 28 | **checked** exact |
| session proxies for unreachable | asia 0 / day 3 / last-40 8 | 1 / 3 / 8 (asia: my 00–07 window boundary, immaterial) | **checked** ≈ |
| earliest-match birth rank | med 32 | 32 | **checked** exact |
| keep-first-N @ 2/8/20 | 4 / 10 / 18 | 4 / 10 / 18 | **checked** exact |
| keep-last-1 (youngest) | 20/51 | 20/51 | **checked** exact |
| youngest by route | rd 18/38 · pb 13/28 · either 20/51 | identical | **checked** exact |
| youngest-hit span IoU ≥0.5 | 9/20 as-drawn · **14/20 episode-anchored** | 9/20 · 14/20 (walk-back while band overlapped) | **checked** exact |
| golden drawn span / window | med .36 | .36 (drawn t0–t1; build-window gives .28 — their def is drawn span) | **checked** (def resolved) |
| golden height / window range | med .33 | .33 | **checked** |
| golden edge within 1.5p of 00/50 | 11/119 | 11/119 (modulo-50 distance) | **checked** exact |
| touches diff match−nonmatch | −2.44 | −2.52 | **checked** ≈ |
| age diff (matches younger) | −39 bars | −39.1 | **checked** exact |
| bars_since_touch diff | −21 | −21.2 | **checked** exact |
| live-at-τ clutter med 2.0 | 2.0 | v1-parent live at golden τ: 7.0 all-types / 1.0 box-family | **differs** — DR's 2.0 is likely measured on v0/hybrid arms, not v1 parent; def needed |
| oracle 19 features / 35 conjunctions | 30/51 / 34/51 | my single-feature oracle (18 feats × both directions, strict-unique-top) = **34/51** — same residual: 17/51 indistinguishable | **checked** (≈; their conjunction bound equals my single-feature bound) |
| H-hind post-τ (2/51 avail, 6/50 live, −2.51 ABR) | flat | fastest-break: **2/51 avail, 6/50 live** exact; max-excursion 1/51 vs their 2/51 (both below random); excursion diff **−2.51** exact | **checked** |
| reachable avail / live (LIVE_WIN=12) | 51 / 50 | 51 / 50 on their extracted pool | **checked** exact |
| pool sizes | avail med 40 / live med 17 | 40 / 17 | **checked** exact |
| youngest recall avail/live | 20/51 / 20/50 | 20/51 / 20/50 | **checked** exact |
| setup-tag reachability table | pb .50 / pbc .57 / tff .53 / pr .50 / pbp .42 / containers .25–.33 | spot-check via their D2 table: asia reachable=3, all yRank=1 → 3/3 youngest ✓ | **checked** ≈ |
| cluster(px,fresh) pick | 19/51 | **19/51 exact** under their C9 def (chain IoU≥0.5; pick cluster by contains-px then freshest member; youngest member) | **checked** exact |
| cluster sub-stats | contains-px 44 / most-recent 38 / biggest 22 | 44 / 33 / 6 under my cruder first-match-cluster def | headline checked; sub-stats ≈ def-dependent |
| joint unreachable decomp (03:00Z) | 27 both-unpaired (17 env-ok) / 25 one-edge / 16 neither / 15 env-viol | consistent with my 20/17/16/15 cut under the simpler non-joint def | **checked** ≈ (different cut, same 68) |
| unreachable INSET inside last-120b range (03:00Z) | 50/68 | 40/68 strict-inside (edges strictly inside the range) | **checked** ≈ (def hair; same conclusion: author's edges are interior, not wick extremes) |
| last-N-bar proxy rescue (03:00Z) | ≤11/68 | 8/5/4 at N=40/80/120 | **checked** |
| pool-size stratification: youngest lift grows with clutter (03:08Z) | 100/53/29/25 vs rand 13/14/6/3 | my avail-quartile strata: youngest 69/38/23/25, rand ~10/15/5/3 | **checked** ≈ direction (youngest decays as pool grows); exact strata values differ — their binning/pick def TBD |
| no zero-pool goldens (03:08Z) | 0 | 0 rows with n_avail=0 | **checked** exact |
| early-window goldens (03:08Z) | 7, of which 2 reachable | τ−w0 ≤ 30 min → 7 goldens, 2 reachable | **checked** exact (def: τ within 30 min of window start) |

**Bottom line:** every recomputable core number reproduces **exactly**
or within a definitional hair — the one material correction stays the
reach headline: DR-BOX's 51 is edge-match; the ruler pays only for 46.

### Convergence note (both lanes agree)

DR's recommended buildable rule — keep-freshest + one live object —
is the same mechanism as BOX-LAB's T1/UIP (their "youngest-either
20/51" edge-match ≈ UIP-all's final-state edges). On the ruler-exact
set it projects to ~14/46 ≈ 30% of reachable — consistent with their
"14/20 after episode-anchored build_start" haircut math.
