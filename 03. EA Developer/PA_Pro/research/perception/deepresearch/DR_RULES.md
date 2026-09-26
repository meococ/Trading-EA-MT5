# DR-RULES — do the author's own drawings obey the Owner's rules?

Ruling 77 §77.3 lane (read-only). Lead 23/09 08:05Z; this report
written 08:56Z same day. Everything below is measured on the TUNE
golden casebook (`golden/draft/BOOK2012_TUNE_v2.jsonl`, 179 scored
panels: 119 boxes, 76 levels, 193 lines) and on the canonical C-3
arm (`uip2_pbbirth@8361fe85e73f9437`, the 623 cached windows of
R75 §75.6). HOLD stayed sealed; the Owner-pack key was never
opened (Part E, ESCALATE).

## Method in one breath

- Units: engine EMA25 and ABR20 from each window's cached engine
  (fed bars ≤ τ only), swing-book pivots `e.book.seq`.  All bars are
  M5; width in bars = minutes/5.
- Span of a measure: bars ≤ min(t1, τ); start at drawn t0 (golden)
  or drawn left edge (engine).  Decision time τ per `snapshot.py::
  tau_of` (box/line: build_end/t1; level: t0+10 min).
- Matching: `evalcheck/eval_v2.py` imported, never copied.  Matched
  = live engine object matching a golden whose decision time is τ.
- First-order estimate (Part D): the existing replay path —
  `snapshot.live_records` + `recall_at_k.rank_live`/`score_map` on
  cached pickles, per-family budgets box@1 line@2 level@1 — with each
  rule applied as a pick filter.  Baseline reproduced exactly: hits
  box 16, line 20, level 7, bracket 29; loose live-census 3.89.
- Clutter is reported as the live-at-τ census median
  (objects+marks at golden-decision τ per panel ÷ scorable goldens),
  the selection-only analogue of the published cumulative window
  census (4.33).  Baseline: 3.89, 125/179 panels ≤5.
- Verdict reading (binding letter of §77.3): *“every other family”*
  = families the rule does not target.  In-family hit cost is
  reported (pass_matched, Δhits) but not thresholded — that is the
  Owner's trade-off to weigh.  A strict all-families reading of the
  −1-hit leg is shown as a sensitivity in Part G.

## A. Book check (notes via `golden/book_loader.py` window only;
paraphrase, quotes ≤15 words)

| claim | page | verdict |
|---|---|---|
| C1 EMA near object (box) | p54, p136, p153–154 | supports — rallies “from far below EMA25 … breeds doubt”; entries far from EMA refused; flags far from EMA skipped |
| C1 EMA near object (level) | — | silent — levels are swing extremes; the book never asks a level to sit on the EMA |
| C2 EMA not steep | p101, p60/76 | supports — flat-EMA mode reads structure (domes, failed attempts); left-edge slope carries the prior wave |
| C3 no shock bar inside | p109, p141, p211 | supports — oversized/news bars degrade setups; abnormally-long-bar check in RULEBOOK |
| C4 no impulse inside | p20 | partial — break “from far away with acceleration and no buildup” is weak; span crossing a leg not addressed |
| C5 bounded box width | p147–156, 5.3 meas | contradicts the 20-bar form — author boxes measured ≈70 and ≈85 bars; supports only “bounded” weakly |
| C6 cluster edges, no lone wick | p217, p120 | supports — spike low left outside the box to show “the dense character of the block”; ~5-p spike wicks ignored |
| C7 delete zombie levels/lines | p56/66, p89 | mixed/contradicts — broken lines kept for pullbacks; an edge is deleted only when it “stopped making sense” |
| C8 newer extreme supersedes | p154, p170 | partial — consumed/touched levels retire; untested broken level stays a magnet (not superseded) |
| EMA period | p47 | supports — only indicator is EMA25 (18–30 “works”) |
| “daylight” (price far from EMA) | p54, p136, p153–154 | supports (see C1) |
| build-up before break | p20, p78 | supports — buildup should flatten with shrinking bars |
| block size | p153–156 | supports — measured sizes given; no upper bar bound |
| shock/news bars | p109, p141 | supports (see C3) |
| deleting broken levels | p56, p154 | contradicts blanket-deletion — broken-but-untested stays a magnet |

## B. Author compliance (TUNE golden; Wilson 95% CI)

n = author's objects of that family; pass-rate with CI.

| rule | fam | pass |
|---|---|---|
| C1@0.5 | box | 92/119 = 0.773  [0.69–0.84] |
| C1@0.5 | level | 13/76 = 0.171  [0.10–0.27] |
| C1@1.0 | box | 98/119 = 0.824  [0.75–0.88] |
| C1@1.0 | level | 28/76 = 0.368  [0.27–0.48] |
| C1p@2 | box | 88/119 = 0.739  [0.65–0.81] |
| C1p@2 | level | 4/76 = 0.053  [0.02–0.13] |
| C2@q95 | box | 113/119 = 0.950  [0.89–0.98] |
| C2@q95 | level | 72/76 = 0.947  [0.87–0.98] |
| C2@q95 | line | 183/193 = 0.948  [0.91–0.97] |
| C2@q90 | box | 107/119 = 0.899  [0.83–0.94] |
| C2@q90 | level | 68/76 = 0.895  [0.81–0.95] |
| C2@q90 | line | 173/193 = 0.896  [0.85–0.93] |
| C3@2.5 | box | 83/119 = 0.697  [0.61–0.77] |
| C3@3.0 | box | 99/119 = 0.832  [0.75–0.89] |
| C4@3 | box | 71/119 = 0.597  [0.51–0.68] |
| C4@4 | box | 107/119 = 0.899  [0.83–0.94] |
| C5@q95 | box | 113/119 = 0.950  [0.89–0.98] |
| C5@q90 | box | 107/119 = 0.899  [0.83–0.94] |
| C5@20 | box | 73/119 = 0.613  [0.52–0.70] |
| C6@clu | box | 40/119 = 0.336  [0.26–0.42] |
| C7@2 | level | 76/76 = 1.000  [0.95–1.00] |
| C7@2 | line | 162/190 = 0.853  [0.80–0.90] |
| C7@3 | level | 76/76 = 1.000  [0.95–1.00] |
| C7@3 | line | 174/190 = 0.916  [0.87–0.95] |
| C8@1 | level | 76/76 = 1.000  [0.95–1.00] |
| C8@2 | level | 76/76 = 1.000  [0.95–1.00] |

### Continuous distributions (author, p10/25/50/75/90/95)

**box**

| measure | p10 | p25 | p50 | p75 | p90 | p95 |
|---|---|---|---|---|---|---|
| c1_pip | 0.00 | 0.00 | 0.00 | 2.13 | 11.04 | 16.59 |
| c1_abr | 0.00 | 0.00 | 0.00 | 0.32 | 1.68 | 2.16 |
| c2_s | 0.01 | 0.04 | 0.07 | 0.12 | 0.17 | 0.20 |
| c3_r | 1.38 | 1.64 | 2.06 | 2.61 | 3.24 | 3.82 |
| c4_r | 1.26 | 1.73 | 2.60 | 3.37 | 3.99 | 4.79 |
| width_bars | 2.00 | 5.00 | 17.00 | 35.50 | 55.60 | 75.40 |
| c6_dhi | 0.00 | 0.00 | 1.50 | 5.55 | 13.96 | 19.08 |
| c6_dlo | 0.00 | 0.00 | 1.40 | 4.25 | 8.78 | 14.23 |
| c6_maxd | 0.00 | 0.70 | 3.70 | 8.60 | 16.72 | 22.42 |
| c3_r_win | 1.30 | 1.57 | 1.96 | 2.50 | 3.16 | 3.82 |
| c4_r_win | 1.01 | 1.51 | 2.27 | 3.09 | 3.54 | 4.04 |
| width_win_bars | 1.00 | 4.00 | 14.00 | 32.50 | 50.40 | 74.10 |

**level**

| measure | p10 | p25 | p50 | p75 | p90 | p95 |
|---|---|---|---|---|---|---|
| c1_pip | 2.67 | 4.99 | 9.12 | 14.58 | 20.69 | 22.72 |
| c1_abr | 0.35 | 0.76 | 1.25 | 2.20 | 3.29 | 4.86 |
| c2_s | 0.02 | 0.03 | 0.07 | 0.12 | 0.17 | 0.20 |
| c7_sw | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| c7_sw_full | 0.00 | 1.00 | 3.00 | 6.00 | 9.50 | 11.25 |
| c8_beyond_abr | 0.00 | 0.00 | 0.00 | 0.00 | 0.13 | 0.47 |

**line**

| measure | p10 | p25 | p50 | p75 | p90 | p95 |
|---|---|---|---|---|---|---|
| c2_s | 0.01 | 0.03 | 0.07 | 0.11 | 0.14 | 0.17 |
| c7_sw | 0.00 | 0.00 | 0.00 | 2.00 | 3.00 | 4.00 |
| c7_sw_full | 0.00 | 0.00 | 1.00 | 3.00 | 5.00 | 7.00 |

Derived thresholds used for q95/q90 variants:

- C2 steepness s: box q95 0.195 / q90 0.167; level 0.204 / 0.169; line 0.166 / 0.142
- C5 width W: drawn q95 75 / q90 56 bars; containment q95 74 / q90 50

### Sensitivities (author)

| variant | fam | pass |
|---|---|---|
| C6g@clu | box | 50/119 = 0.420  [0.34–0.51] |
| C7s@2 | level | n=76 (no evaluable) |
| C7s@2 | line | n=193 (no evaluable) |
| C7s@3 | level | n=76 (no evaluable) |
| C7s@3 | line | n=193 (no evaluable) |
| C7f@2 | level | 35/76 = 0.461  [0.35–0.57] |
| C7f@2 | line | 128/190 = 0.674  [0.60–0.74] |
| C8a@1 | level | n=76 (no evaluable) |
| C8a@2 | level | n=76 (no evaluable) |
| C3w@2.5 | box | 89/119 = 0.748  [0.66–0.82] |
| C3w@3.0 | box | 102/119 = 0.857  [0.78–0.91] |
| C4w@3 | box | 84/119 = 0.706  [0.62–0.78] |
| C4w@4 | box | 112/119 = 0.941  [0.88–0.97] |
| C5w@q95 | box | 113/119 = 0.950  [0.89–0.98] |
| C5w@q90 | box | 107/119 = 0.899  [0.83–0.94] |
| C5w@20 | box | 76/119 = 0.639  [0.55–0.72] |

Reading: C3w/C4w/C5w measure the containment window
(build_start..build_end), not the drawn span — the drawn span of an
author box includes the break bar and follow-through, which is why
drawn-span C3/C4 compliance is lower.  C7s/C7f (span/full history)
show the zombie measure the birth window hides: author levels had a
median of 3 close-switches before τ (C7f@2 pass 0.461) — the author
does draw across already-weaved prices.  C6g relaxes the strict
cluster tolerance to the ruler's golden tolerance (label noise):
pass 0.336→0.420, still far below 0.90 — the author draws edges
*inside* the outermost cluster (median 3.7 p, p75 8.6 p off), i.e.
he trims spikes rather than sitting on the cluster extreme.

## C. C-3 split (canonical 623 windows; pass-rate on matched vs
unmatched live objects)

matched = engine pick that matches a golden at its τ (hits a gate
would lose); unmatched = false objects the gate could remove.
removal = 1 − pass(unmatched).

| rule | fam | pass match (n) | pass unmatch (n) | removal |
|---|---|---|---|---|
| C1@0.5 | box | 0.94/16 | 0.89/609 | 0.105 |
| C1@0.5 | level | 0.00/7 | 0.22/590 | 0.781 |
| C1@1.0 | box | 1.00/16 | 0.93/609 | 0.074 |
| C1@1.0 | level | 0.29/7 | 0.45/590 | 0.551 |
| C1p@2 | box | 0.94/16 | 0.88/609 | 0.125 |
| C1p@2 | level | 0.00/7 | 0.18/590 | 0.817 |
| C2@q95 | box | 1.00/16 | 0.96/609 | 0.043 |
| C2@q95 | level | 1.00/7 | 0.98/590 | 0.019 |
| C2@q95 | line | 0.84/25 | 0.91/1110 | 0.095 |
| C2@q90 | box | 1.00/16 | 0.91/609 | 0.089 |
| C2@q90 | level | 0.86/7 | 0.91/590 | 0.088 |
| C2@q90 | line | 0.84/25 | 0.87/1110 | 0.134 |
| C3@2.5 | box | 0.12/16 | 0.09/609 | 0.908 |
| C3@3.0 | box | 0.44/16 | 0.35/609 | 0.647 |
| C4@3 | box | 0.00/16 | 0.02/609 | 0.979 |
| C4@4 | box | 0.56/16 | 0.29/609 | 0.713 |
| C5@q95 | box | 0.06/16 | 0.03/609 | 0.967 |
| C5@q90 | box | 0.06/16 | 0.02/609 | 0.979 |
| C5@20 | box | 0.00/16 | 0.00/609 | 0.997 |
| C6@clu | box | 0.06/16 | 0.01/609 | 0.990 |
| C7@2 | level | 0.71/7 | 0.86/590 | 0.144 |
| C7@2 | line | 0.92/25 | 0.96/1110 | 0.042 |
| C7@3 | level | 0.71/7 | 0.90/590 | 0.097 |
| C7@3 | line | 1.00/25 | 0.98/1110 | 0.015 |
| C8@1 | level | 0.43/7 | 0.64/590 | 0.361 |
| C8@2 | level | 0.71/7 | 0.77/590 | 0.232 |

### Sensitivities (engine)

| variant | fam | pass match (n) | pass unmatch (n) | removal |
|---|---|---|---|---|
| C7s@2 | level | 0.29/7 | 0.61/590 | 0.392 |
| C7s@2 | line | 0.72/25 | 0.84/1110 | 0.159 |
| C7s@3 | level | 0.43/7 | 0.74/590 | 0.263 |
| C7s@3 | line | 0.92/25 | 0.94/1110 | 0.062 |
| C7f@2 | level | 0.14/7 | 0.27/590 | 0.725 |
| C7f@2 | line | 0.68/25 | 0.68/1110 | 0.319 |
| C8a@1 | level | 0.29/7 | 0.27/590 | 0.725 |
| C8a@2 | level | 0.57/7 | 0.55/590 | 0.447 |
| C3w@2.5 | box | 0.44/16 | 0.48/609 | 0.522 |
| C3w@3.0 | box | 0.69/16 | 0.80/609 | 0.204 |
| C4w@3 | box | 0.50/16 | 0.42/609 | 0.576 |
| C4w@4 | box | 0.88/16 | 0.88/609 | 0.120 |
| C5w@q95 | box | 1.00/16 | 0.96/609 | 0.041 |
| C5w@q90 | box | 1.00/16 | 0.92/609 | 0.079 |
| C5w@20 | box | 0.56/16 | 0.56/609 | 0.435 |

Reading: engine boxes are far wider than the author's (C5 drawn
removal 0.967 vs author pass 0.950 — the asymmetry is lifetime, not
congestion width: C5w containment removal is only 0.041).  Engine
levels sit far from the EMA (C1@1.0 removal 0.55) while the
author's do too — C1 is a *box* rule in the author's grammar.
Engine zombie exposure (C7s/C7f/C8a) is much larger than the
author's: C7f@2 removes 72.5% of unmatched levels; C8a@1 72.5%
(anchor-based supersession).

## D. Joint first-order estimate (selection-only; existing replay
path, per-family budgets)

Baseline hits: box 16, line 20, level 7, bracket 29; live-census
clutter median 3.89.

| rule | hits after | Δhits | freed fills (matched) | lost picks | clutter med |
|---|---|---|---|---|---|
| C1@0.5 | bo+15 li+20 le0 br+29 | bo-1 li0 le-7 br0 | 104 (0) | 533 | 3.00 |
| C1@1.0 | bo+16 li+20 le+2 br+29 | bo0 li0 le-5 br0 | 140 (0) | 375 | 3.00 |
| C1p@2 | bo+15 li+20 le0 br+29 | bo-1 li0 le-7 br0 | 98 (0) | 566 | 2.89 |
| C2@q95 | bo+16 li+18 le+7 br+29 | bo0 li-2 le0 br0 | 65 (1) | 146 | 3.78 |
| C2@q90 | bo+16 li+18 le+6 br+29 | bo0 li-2 le-1 br0 | 118 (1) | 260 | 3.67 |
| C3@2.5 | bo+3 li+20 le+7 br+29 | bo-13 li0 le0 br0 | 46 (1) | 567 | 3.11 |
| C3@3.0 | bo+7 li+20 le+7 br+29 | bo-9 li0 le0 br0 | 63 (0) | 403 | 3.50 |
| C4@3 | bo0 li+20 le+7 br+29 | bo-16 li0 le0 br0 | 52 (0) | 612 | 3.00 |
| C4@4 | bo+9 li+20 le+7 br+29 | bo-7 li0 le0 br0 | 65 (0) | 441 | 3.33 |
| C5@q95 | bo+2 li+20 le+7 br+29 | bo-14 li0 le0 br0 | 105 (1) | 604 | 3.22 |
| C5@q90 | bo+2 li+20 le+7 br+29 | bo-14 li0 le0 br0 | 79 (1) | 611 | 3.22 |
| C5@20 | bo0 li+20 le+7 br+29 | bo-16 li0 le0 br0 | 18 (0) | 623 | 3.00 |
| C6@clu | bo+1 li+20 le+7 br+29 | bo-15 li0 le0 br0 | 55 (0) | 618 | 3.00 |
| C7@2 | bo+16 li+19 le+5 br+29 | bo0 li-1 le-2 br0 | 76 (2) | 136 | 3.67 |
| C7@3 | bo+16 li+20 le+5 br+29 | bo0 li0 le-2 br0 | 45 (1) | 76 | 3.67 |
| C8@1 | bo+16 li+20 le+3 br+29 | bo0 li0 le-4 br0 | 133 (0) | 217 | 3.56 |
| C8@2 | bo+16 li+20 le+5 br+29 | bo0 li0 le-2 br0 | 89 (0) | 139 | 3.67 |

Reading: freed slots almost never recover hits (fills_matched ≈ 0)
— the filter drops the pick and the next candidate in line is
unmatched; consistent with R75 §75.2(b) (the right object is not
live at τ; the deficit is on the generation side).  Cross-family
damage: C1 applied to box+level also kills all 7 level hits (the
level family is structurally far-from-EMA); C2@q95 costs 2 line
hits as collateral.

## E. Owner pack — ESCALATE

ESCALATE: pack geometry only in keyed file
(`evalcheck/_owner_judge_key/m2_c3_key.json`).  `manifest.jsonl`
holds seq+png only; items are blind PNGs; no non-keyed geometry
exists.  Per §77.3 Part E is skipped; `DR_RULES_pack_features.csv`
is not written.  No OCR, no key inspection.

## F. PA-ATLAS baselines under the same gates

Baseline hits reproduce published: bl_tdlines_k2 line@2 29/193, clutter 6.67; bl_donchian_alt level@1 16/76, clutter 10.33.

### bl_tdlines_k2 (fam=line, k=2, live objects=492)

| rule | hits (Δ) | removed live | clutter after |
|---|---|---|---|
| C2@q95 | 26 (-3) | 27/492 | 6.33 |
| C2@q90 | 25 (-4) | 47/492 | 5.67 |
| C7@2 | 29 (+0) | 0/492 | 4.67 |
| C7@3 | 29 (+0) | 0/492 | 5.67 |

### bl_donchian_alt (fam=level, k=1, live objects=1882)

| rule | hits (Δ) | removed live | clutter after |
|---|---|---|---|
| C1@0.5 | 9 (-7) | 1600/1882 | 1.25 |
| C1@1.0 | 16 (+0) | 1274/1882 | 2.50 |
| C1p@2 | 6 (-10) | 1696/1882 | 1.00 |
| C2@q95 | 15 (-1) | 57/1882 | 9.67 |
| C2@q90 | 14 (-2) | 160/1882 | 9.33 |
| C7@2 | 16 (+0) | 0/1882 | 7.00 |
| C7@3 | 16 (+0) | 0/1882 | 8.00 |
| C8@1 | 16 (+0) | 9/1882 | 4.67 |
| C8@2 | 16 (+0) | 0/1882 | 6.33 |
| C8a@1 | 16 (+0) | 9/1882 | 4.67 |
| C8a@2 | 16 (+0) | 0/1882 | 6.33 |

Reading: on donchian levels **C1@1.0 removes 68% of live objects,
keeps all 16 hits, clutter 10.33→2.50** — the single best free
filter in the study (baseline-side; engine matched levels are not
so lucky).  C7/C8 barely touch baselines that already retire or
deduplicate their objects.

(`clutter after` = filtered cumulative census measured at w1;
`removed live` counts filters at golden-decision τ — the two
windows differ, so clutter can drop with zero τ-removals, e.g.
C7 on tdlines.)

## G. Verdicts (§77.3, literal reading; in-family hit cost shown)

| rule | fam | author pass | pass matched | removal | Δhits (all fams) | clutter | verdict |
|---|---|---|---|---|---|---|---|
| C1@0.5 | box | 0.773 | 0.94 | 0.105 | bo-1 li0 le-7 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -7** |
| C1@0.5 | level | 0.171 | 0.00 | 0.781 | bo-1 li0 le-7 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -7** |
| C1@1.0 | box | 0.824 | 1.00 | 0.074 | bo0 li0 le-5 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -5** |
| C1@1.0 | level | 0.368 | 0.29 | 0.551 | bo0 li0 le-5 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -5** |
| C1p@2 | box | 0.739 | 0.94 | 0.125 | bo-1 li0 le-7 br0 | 2.89 | TRADER-ONLY  **⚠ in-fam -7** |
| C1p@2 | level | 0.053 | 0.00 | 0.817 | bo-1 li0 le-7 br0 | 2.89 | TRADER-ONLY  **⚠ in-fam -7** |
| C2@q95 | box | 0.950 | 1.00 | 0.043 | bo0 li-2 le0 br0 | 3.78 | INFO  **⚠ in-fam -2** |
| C2@q95 | level | 0.947 | 1.00 | 0.019 | bo0 li-2 le0 br0 | 3.78 | INFO  **⚠ in-fam -2** |
| C2@q95 | line | 0.948 | 0.84 | 0.095 | bo0 li-2 le0 br0 | 3.78 | INFO  **⚠ in-fam -2** |
| C2@q90 | box | 0.899 | 1.00 | 0.089 | bo0 li-2 le-1 br0 | 3.67 | TRADER-ONLY  **⚠ in-fam -2** |
| C2@q90 | level | 0.895 | 0.86 | 0.088 | bo0 li-2 le-1 br0 | 3.67 | TRADER-ONLY  **⚠ in-fam -2** |
| C2@q90 | line | 0.896 | 0.84 | 0.134 | bo0 li-2 le-1 br0 | 3.67 | TRADER-ONLY  **⚠ in-fam -2** |
| C3@2.5 | box | 0.697 | 0.12 | 0.908 | bo-13 li0 le0 br0 | 3.11 | TRADER-ONLY  **⚠ in-fam -13** |
| C3@3.0 | box | 0.832 | 0.44 | 0.647 | bo-9 li0 le0 br0 | 3.50 | TRADER-ONLY  **⚠ in-fam -9** |
| C4@3 | box | 0.597 | 0.00 | 0.979 | bo-16 li0 le0 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -16** |
| C4@4 | box | 0.899 | 0.56 | 0.713 | bo-7 li0 le0 br0 | 3.33 | TRADER-ONLY  **⚠ in-fam -7** |
| C5@q95 | box | 0.950 | 0.06 | 0.967 | bo-14 li0 le0 br0 | 3.22 | BUILD-CANDIDATE  **⚠ in-fam -14** |
| C5@q90 | box | 0.899 | 0.06 | 0.979 | bo-14 li0 le0 br0 | 3.22 | TRADER-ONLY  **⚠ in-fam -14** |
| C5@20 | box | 0.613 | 0.00 | 0.997 | bo-16 li0 le0 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -16** |
| C6@clu | box | 0.336 | 0.06 | 0.990 | bo-15 li0 le0 br0 | 3.00 | TRADER-ONLY  **⚠ in-fam -15** |
| C7@2 | level | 1.000 | 0.71 | 0.144 | bo0 li-1 le-2 br0 | 3.67 | INFO  **⚠ in-fam -2** |
| C7@2 | line | 0.853 | 0.92 | 0.042 | bo0 li-1 le-2 br0 | 3.67 | TRADER-ONLY  **⚠ in-fam -2** |
| C7@3 | level | 1.000 | 0.71 | 0.097 | bo0 li0 le-2 br0 | 3.67 | INFO  **⚠ in-fam -2** |
| C7@3 | line | 0.916 | 1.00 | 0.015 | bo0 li0 le-2 br0 | 3.67 | INFO  **⚠ in-fam -2** |
| C8@1 | level | 1.000 | 0.43 | 0.361 | bo0 li0 le-4 br0 | 3.56 | BUILD-CANDIDATE  **⚠ in-fam -4** |
| C8@2 | level | 1.000 | 0.71 | 0.232 | bo0 li0 le-2 br0 | 3.67 | BUILD-CANDIDATE  **⚠ in-fam -2** |

Strict-reading sensitivity (if the −1-hit leg bounded *every*
family including the target): C5@q95 (−14), C8@1 (−4), C8@2 (−2)
would all drop to INFO — zero BUILD-CANDIDATEs.  Reported so the
Lead can re-cut without re-running the lane.

### What the builder would flag

- **C8 supersede-gate** (level): kill or retire a level once a
  confirmed same-polarity swing extreme born after it lies ≥1·ABR
  beyond it.  Variants: k=1 (removal .361, keeps 3/7 hits) and k=2
  (removal .232, keeps 5/7).  Parameters: pivot set = engine
  swing-book (confirmed pivots), beyond = (pivot−level)/ABR20 at τ.
  Anchor variant (born after the level's *structural* bar) removes
  72.5% — flagged, not verdicted.  This mirrors the engine's own
  `consumed`/retire semantics, so it is the least foreign rule to
  build.
- **C5 width gate** (box): drawn width ≤75 bars is the author's q95,
  but as a *hard filter* it keeps only 2/16 hits — engine boxes are
  wide because they persist, not because congestion is wide (C5w
  containment removal .04).  A builder should NOT filter the drawn
  box; the equivalent mechanic is **bounded persistence** — retire/
  shrink a box whose drawn age exceeds ~75 bars unless re-anchored.
  Flag name: `box_max_drawn_age`; parameter: 75 bars (q95),
  alternative 56 (q90).
- **C1 daylight** is a *box-shaped* rule in the author's grammar —
  author levels sit 1.25 ABR (median) from the EMA by construction.
  If ever built, restrict to box family only (box pass .824@1.0,
  removal .07) — below the removal bar anyway; TRADER-ONLY stands.

## Limitations

- τ for golden levels = t0+10 min, so C7/C8 author windows are ~2
  bars — literal compliance is vacuous (hence C7f/C8a sensitivities).
- Golden box edges are eyeballed ±5 p — C6 strict pass 0.336 is a
  lower bound on the intended definition, not a refutation of
  “edges on clusters”.
- The first-order estimate is selection-only: the engine's birth
  side is untouched, so a rule can never *gain* a hit here, only
  lose or leave them.  fills_matched≈0 is a property of the pool.
- q95/q90 thresholds are author-derived per family (n=76–193),
  so they are calibrated, not universal.
- Part E skipped (keyed geometry); pack-side evidence absent.

## Tóm tắt cho anh (10 dòng, mỗi rule một dòng)

- Kết luận: 8 rule của anh, tác giả chỉ tuân thủ sạch 3 rule (C2, C7, C8); BUILD-CANDIDATE = C8 (level) và C5@q95 (box).
- C1 EMA-gần: tác giả tuân thủ 77–82% ở box (level chỉ 17–37% — tác giả vẽ level xa EMA sẵn), bỏ được 7–10% box / 55–78% level vật sai của máy.
- C2 EMA-phẳng: tác giả tuân thủ 95% ở ngưỡng q95, bỏ được 2–10% vật sai của máy; mất 2 line-hit vật xui.
- C3 không-bar-sốc: tác giả tuân thủ 70–83%, bỏ được 65–91% vật sai của máy nhưng mất 9–13/16 box-hit.
- C4 không-xung-lực: tác giả tuân thủ 60–90%, bỏ được 71–98% vật sai của máy, mất 7–16 box-hit.
- C5 hộp-hữu-hạn: tác giả tuân thủ 95% ở q95 (75 bar; ~40% hộp tác giả >20 bar nên mốc 20-bar của anh không đúng), bỏ được 97% vật sai nhưng chỉ giữ 2/16 hit.
- C6 cạnh-theo-cụm: tác giả tuân thủ 34–42% (tác giả vẽ mép TRONG cụm cực-trị, cắt wick), bỏ được 99% vật sai của máy, mất 15/16 box-hit.
- C7 xoá-mức-zombie: tác giả tuân thủ 100% theo cửa sổ sinh (nhưng đo cả-đời thì chỉ 46% — tác giả vẽ level qua giá đã đan-xen), bỏ được 10–14% vật sai level của máy.
- C8 mức-bị-thay: tác giả tuân thủ 100%, bỏ được 23–36% vật sai level của máy, giữ 3–5/7 hit — rule khả-dĩ nhất để build.
- Nói gọn: rule đáng build là C8 (xóa level bị swing mới vượt) và C5-dạng-tuổi-hộp; mấy rule khác nên hỏi lại anh cách chú áp dụng, vì tác giả chính ông ấy cũng không vẽ theo kiểu đó.
