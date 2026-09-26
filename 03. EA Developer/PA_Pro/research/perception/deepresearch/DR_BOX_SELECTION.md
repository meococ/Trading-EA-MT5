# DR-BOX — Is the author's box predictable at τ?

Lane DR-BOX (Lead mandate 23/09 02:30Z, Ruling 64). Fresh-eyes review.
Research only; no engine edits, no fits, TUNE panels only, book via
`book_loader`/`BOOK2012_TUNE_v2.jsonl` only, HOLD untouched.

Scripts: `dr_extract.py` (pool extraction), `dr_analyze.py`,
`dr_final.py` (all hypothesis tests + bounds), `dr_table.py` (D2 table).
Data: `dr_rows.pkl` — 119 goldens, 4,730 available event cands.

---

## Verdict (up front)

**Partly predictable, with a hard causal ceiling well below 50%.**

- The author's box is the *freshest established congestion* far more
  often than chance: "youngest-born event candidate" picks the golden
  edges in **20/51 reachable** cases (random null p95 = 7). This is the
  only causal rule that survives every null.
- But among the 51 goldens the event stream can even draw, **≥17/51
  remain indistinguishable** under every tested causal feature and a
  stated 35-rule conjunction family (oracle bound 34/51). The author is
  choosing among look-alike candidates using narrative framing the
  geometry does not carry: which episode is *the* setup (Asia range,
  post-spike absorption base, W/M container, "the first sideways block
  after the leg").
- **Hindsight is rejected**: picking the candidate that breaks first or
  runs furthest after τ finds the golden only 2–6/51 — *below* the
  random null. The author is not drawing around the soon-to-break box.
- Decomposition of the miss: **reach 68** (edges never proposed) +
  **select ~31** (edges exist, wrong cand picked under best rule) +
  **window** (right edges, wrong span: only 9/20 rule-hits have drawn
  span IoU ≥ 0.5 vs the golden containment window).
- Predictable fraction under the demonstrated causal ceiling:
  **≈20–34 of 119 (17–29%)** edge-exact at one-box economy.
  Unpredictable-by-causal-geometry fraction of what the event stream
  reaches: **≈41% (21/51)** indistinguishable + the oracle-vs-rule gap.

---

## Conventions used

- Golden τ = `snapshot.tau_of(g)` (build_end else t1); scored like the
  ruler: both price edges within `eval_v2.tol_px`.
- `avail` = cand `born <= j_tau`. `live` = avail AND (price inside band
  OR band touched within last 12 bars). LIVE_WIN = 12 (stated before
  measurement).
- Edge-match = lab convention `label_edge` (both edges within tol).
  Ruler-strict additionally needs containment-window IoU ≥ 0.5.
- Nulls: within-panel label shuffle, 200 draws, seed 20260923;
  price-position features use the density-aware null (random avail cand
  in the same panel), stated in `dr_final.py`.
- Post-τ bars used ONLY inside H-hind, never as features.

---

## D1 — Literature

Web access worked. Sources (title — URL):

1. Lo, Mamaysky & Wang (2000), *Foundations of Technical Analysis:
   Computational Algorithms, Statistical Inference, and Empirical
   Implementation*, J. Finance 55:1705-1765 —
   https://doi.org/10.1111/0022-1082.00265 (PDF:
   https://web.mit.edu/Alo/www/Papers/1705-1765.pdf).
   Kernel-smooth extrema → pattern prototypes. Principle taken:
   *pattern identity is scale-dependent; the detector's smoothing width
   decides which structures exist at all.* Our pivot/t_ext scale fixes
   which boxes can exist — a reachability bound, not a selection bound.
2. Osler (2000), *Support for Resistance: Technical Analysis and
   Intraday Exchange Rates*, NY Fed EPR 6(2):53-68 —
   https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf
   Verified directly: **~30% of possible matches realized** across six
   firms' published S/R levels at ±5pt tolerance (pairwise 13–38%; ~18%
   at ±2pt). >70% of levels end in 0, 96% end in 0/5; 00/50
   over-represented. And crucially (Table 11) **agreement carries no
   extra predictive power** — consensus levels predict interruptions no
   better than others. Principle: *expert level-picking is genuinely
   idiosyncratic; ~30% inter-expert agreement is the human ceiling on
   level identity.* A causal engine trying to match one specific human's
   pick faces the same ceiling.
3. Osler (2003/staff report 125), *Currency Orders and Exchange-Rate
   Dynamics* — https://www.newyorkfed.org/research/staff_reports/sr125.html
   Stop-loss/take-profit orders cluster at round numbers → round numbers
   are real S/R *because* orders sit there. Principle: round-number
   edges are plausible a priori but density-corrected they must still
   beat the null (they don't — H-round50 below).
4. Bulkowski, *Rectangle Tops/Bottoms* — thepatternsite.com:
   https://www.thepatternsite.com/recttops.html ,
   https://www.thepatternsite.com/rectbots.html .
   Definition: two near-horizontal trendlines, ≥5 touches (3+2) on
   distinct peaks/valleys. Principle taken: *a real rectangle needs
   ≥5 edge contacts.* Our data shows the author's box often has
   *fewer* measurable touches than rivals — the classic textbook defn
   does not match Volman's usage.
5. Darvas box — e.g. MQL5 implementation notes
   https://www.mql5.com/en/articles/24111 : box top = high not exceeded
   for 3 sessions; box = *event-anchored* rolling state machine.
   Principle: the box is born at a defined event (failure to make a new
   high) and lives until violated — matches our event-route design.
6. Wyckoff trading range / Springs & Upthrusts —
   https://www.profectus.ai/post/rychard-wyckoffs-mean-reversion-strategy-automated
   TR = institutional accumulation/distribution zone; edges defined by
   springs/upthrusts (terminal shakeouts). Principle: the *last*
   extreme event defines the edge — recency-anchored.
7. Al Brooks, *Trading Price Action Ranges* (glossary + ch.6-10) —
   https://dl.kohanfx.com/pdf/Al-Brooks-Trading-Price-Action-Ranges-(KohanFx.com).pdf
   Trading range = "two-sided trading", minimum one overlapped bar;
   "breakout mode"; magnets = round numbers, prior day H/L, measured
   moves. Principle: *the relevant range is the most recent zone of
   two-sided trade* — recency again, plus magnet anchoring of edges.
8. Truong, Oudre, Vayatis (2020), *Selective review of offline change
   point detection* — https://arxiv.org/abs/1801.00718 : segmentation =
   cost fn + search + penalty; online vs offline regimes. Principle: a
   congestion episode is a segment boundary problem; offline
   segmentation sees the whole crop — the author is an *offline*
   segmenter, the engine must be *online*. This asymmetry is the
   deepest causal gap.
9. Inter-rater annotation studies (crypto candlestick kappa 0.78–0.85
   on crisp binary labels —
   https://doi.org/10.3390/computation12070132 ) show humans agree on
   *labels* when the decision is forced, but Osler shows they do NOT
   agree on *levels*. Box-edge placement is a level problem, not a
   label problem.

Testable principles extracted and taken to D3: recency (freshest
two-sided zone), event-birth anchoring (Darvas/Wyckoff), touch-count
≥5 (Bulkowski — fails), round-number magnets (Osler — fails as a
discriminator), episode segmentation (changepoint view), and the
inter-expert ceiling (~30-40% agreement ⇒ author-matching is bounded).

---

## D2 — The book (119 box goldens, book_loader only)

What the text says the box frames (clause + lesson tags):

| what the box frames | n/119 |
|---|---|
| plain congestion rectangle | 79 |
| post-leg base / absorption after spike/drop | 18 |
| Asia / overnight range | 11 |
| pattern container (W/M/SHS/bracket) | 9 |
| session/day range (the day's range) | 2 |

Edge specificity in the text:

- **106/119** clauses carry explicit HH:MM times for the span edges.
- **36/119** name an edge-defining event (first touch, tease, spike,
  test, breakout bar, named extreme, bounce).
- **32/119** are `meas` precision (author measured exact pips).
- 29/119 goldens' text (9 clauses + 23 lessons, overlapping) explicitly
  anchors to a round level ("straddling 1,325", "just above 1,32",
  "on the 1,315 level", "under 1.30") — descriptive magnet talk, but
  the edges themselves are NOT rounder than chance (H-round50 below).
- Recurring semantics: "the Asian box", "the day's range", "the first
  sideways block after the leg", "an absorption box after a spike
  includes the spike extreme", "kept past the break". The box is the
  *episode container* for the setup being taught (pb 38, tff 15,
  pbc 14, pr 12, pbp 12 arrows across the panels).

Setup-tag → reachability (H-setup, details in D3):

| tag | n | reachable | rate |
|---|---|---|---|
| pb | 38 | 19 | 0.50 |
| pbc | 14 | 8 | 0.57 |
| tff | 15 | 8 | 0.53 |
| pr | 12 | 6 | 0.50 |
| pbp | 12 | 5 | 0.42 |
| pattern_container | 24 | 8 | 0.33 |
| asia_box | 11 | 3 | 0.27 |
| post_leg_base | 12 | 3 | 0.25 |
| round_named | 9 | 3 | 0.33 |

Reading: setups whose box is a *fresh congestion after a leg* (pb/pbc/
tff/pr/pbp) are reachable ~half the time; boxes that are *semantic
containers* (W/M/SHS patterns, the Asia range, post-spike bases) are
reachable only ~1/4-1/3 — the event stream structurally cannot draw
them (wrong edge source: the box edge is a spike extreme or a session
extreme, not a pivot pair).

Full per-golden table (setup codes from arrow marks; `frames` = what
the clause says the box contains; `edge-named` = edge-defining event
in text; `reach` = ≥1 avail cand edge-matches; `nM` = #matching cands;
`yRank` = match's rank by birth-freshness):

| panel | tau | h(p) | span(m) | setup | frames | edge-named | reach | nM | yRank |
|---|---|---|---|---|---|---|---|---|---|
| 9.10a | 580 | 16 | 280 | - | congestion | - | Y | 2 | 7 |
| 9.10a | 660 | 21 | 65 | - | congestion | - | n | 0 | - |
| 9.10c | 980 | 14 | 105 | - | pattern | - | n | 0 | - |
| 9.11a | 660 | 36 | 215 | pbp | round | test,brk-bar | Y | 2 | 1 |
| 9.11c | 1070 | 46 | 375 | pb,pbc,pr | post-leg | - | n | 0 | - |
| 9.12c | 1020 | 11 | 85 | - | congestion | - | n | 0 | - |
| 9.13a | 190 | 12 | 415 | pb,pbp | asia | - | Y | 2 | 1 |
| 9.13a | 505 | 12 | 80 | pb,pbp | congestion | - | Y | 13 | 1 |
| 9.13b | 545 | 11 | 130 | - | round | - | n | 0 | - |
| 9.14a | 530 | 14 | 20 | - | congestion | - | Y | 18 | 2 |
| 9.14b | 515 | 12 | 80 | pbc,pr,tff | congestion | - | Y | 3 | 1 |
| 9.14b | 615 | 13 | 45 | pbc,pr,tff | 2nd/inner | - | Y | 4 | 12 |
| 9.15b | 895 | 20 | 90 | pbc | pattern | - | Y | 1 | 1 |
| 9.15b | 900 | 24 | 150 | pbc | congestion | - | Y | 2 | 3 |
| 9.15c | 980 | 20 | 110 | - | congestion | spike | n | 0 | - |
| 9.16b | 625 | 24 | 350 | tff | post-leg | - | n | 0 | - |
| 9.16c | 1035 | 55 | 365 | pb | day-range | - | n | 0 | - |
| 9.16c | 1070 | 14 | 95 | pb | congestion | - | Y | 2 | 1 |
| 9.17a | 475 | 9 | 115 | pb | congestion | - | Y | 2 | 1 |
| 9.17b | 705 | 7 | 60 | pb | congestion | - | Y | 1 | 2 |
| 9.17b | 775 | 12 | 95 | pb | congestion | - | n | 0 | - |
| 9.17c | 830 | 29 | 95 | - | pattern | - | n | 0 | - |
| 9.18a | 515 | 13 | 150 | pb,pr,tff | congestion | - | Y | 6 | 1 |
| 9.18a | 660 | 14 | 35 | pb,pr,tff | round | - | n | 0 | - |
| 9.18b | 635 | 17 | 100 | - | post-leg,round | - | n | 0 | - |
| 9.19a | 560 | 14 | 65 | - | congestion | - | n | 0 | - |
| 9.19b | 840 | 10 | 20 | pb | congestion | - | n | 0 | - |
| 9.1c | 795 | 15 | 135 | pbc | congestion | - | Y | 2 | 2 |
| 9.20a | 535 | 19 | 435 | - | congestion | - | Y | 1 | 25 |
| 9.20b | 605 | 18 | 95 | - | congestion | - | n | 0 | - |
| 9.20b | 715 | 15 | 95 | - | congestion | - | n | 0 | - |
| 9.20c | 1080 | 10 | 125 | pr | congestion | - | Y | 1 | 67 |
| 9.22a | 600 | 15 | 40 | pb | 2nd/inner | - | n | 0 | - |
| 9.22b | 640 | 17 | 114 | - | pattern,post-leg | - | n | 0 | - |
| 9.22c | 1010 | 13 | 100 | - | congestion | - | n | 0 | - |
| 9.23c | 985 | 13 | 165 | - | congestion | - | n | 0 | - |
| 9.24a | 720 | 22 | 400 | pbc | congestion | spike | Y | 2 | 3 |
| 9.24b | 820 | 26 | 370 | pb | congestion | - | Y | 4 | 11 |
| 9.24b | 825 | 0 | 225 | pb | congestion | - | n | 0 | - |
| 9.24c | 1015 | 39 | 30 | - | congestion | - | n | 0 | - |
| 9.25b | 775 | 14 | 150 | - | ema | - | Y | 3 | 2 |
| 9.27a | 600 | 16 | 135 | - | asia | - | n | 0 | - |
| 9.29b | 705 | 23 | 145 | pb | kept-past-break | - | n | 0 | - |
| 9.2a | 250 | 12 | 305 | pbc | round | - | n | 0 | - |
| 9.2b | 765 | 22 | 230 | pr,tff | round | named-extreme | Y | 3 | 4 |
| 9.2b | 835 | 13 | 85 | pr,tff | 2nd/inner | named-extreme | Y | 1 | 2 |
| 9.2c | 780 | 16 | 195 | tff | round | named-extreme | n | 0 | - |
| 9.30a | 430 | 21 | 395 | pbp | congestion | - | n | 0 | - |
| 9.30c | 880 | 12 | 100 | pbc | congestion | - | Y | 2 | 17 |
| 9.31c | 950 | 12 | 140 | - | congestion | - | n | 0 | - |
| 9.32a | 478 | 10 | 258 | pb | congestion | - | Y | 4 | 1 |
| 9.32a | 510 | 8 | 25 | pb | congestion | - | Y | 1 | 1 |
| 9.32b | 735 | 16 | 140 | - | congestion | - | Y | 1 | 1 |
| 9.33c | 1055 | 15 | 140 | pbp,pr | congestion | - | n | 0 | - |
| 9.34a | 465 | 22 | 435 | pb | post-leg,kept-past-break | - | n | 0 | - |
| 9.34a | 495 | 10 | 30 | pb | congestion | - | n | 0 | - |
| 9.34b | 655 | 56 | 265 | - | congestion | - | n | 0 | - |
| 9.35a | 260 | 15 | 415 | - | congestion | - | n | 0 | - |
| 9.35a | 595 | 9 | 73 | - | 2nd/inner | - | n | 0 | - |
| 9.36b | 560 | 18 | 145 | - | congestion | - | Y | 13 | 2 |
| 9.36b | 645 | 7 | 90 | - | pattern | - | Y | 1 | 3 |
| 9.37b | 645 | 50 | 85 | tff | congestion | named-extreme | n | 0 | - |
| 9.38c | 1010 | 13 | 67 | tff | congestion | - | n | 0 | - |
| 9.39a | 475 | 11 | 445 | pb | congestion | - | Y | 7 | 2 |
| 9.3b | 745 | 13 | 95 | - | ema | - | Y | 5 | 22 |
| 9.40c | 960 | 12 | 120 | pb | congestion | - | Y | 1 | 16 |
| 9.41b | 835 | 16 | 155 | - | congestion | - | Y | 5 | 1 |
| 9.42b | 640 | 47 | 255 | - | congestion | - | n | 0 | - |
| 9.42b | 780 | 84 | 360 | - | pattern | - | n | 0 | - |
| 9.43b | 840 | 20 | 155 | - | pattern,post-leg,ema | - | n | 0 | - |
| 9.43c | 870 | 16 | 130 | pbp | congestion | - | n | 0 | - |
| 9.43c | 1080 | 16 | 110 | pbp | kept-past-break | - | Y | 1 | 4 |
| 9.44a | 600 | 10 | 34 | - | 2nd/inner | - | n | 0 | - |
| 9.44b | 685 | 20 | 115 | - | congestion | - | n | 0 | - |
| 9.44b | 730 | 10 | 20 | - | pattern | - | Y | 1 | 1 |
| 9.45a | 350 | 18 | 430 | - | asia | tease | Y | 2 | 1 |
| 9.45b | 740 | 15 | 95 | - | post-leg,round | - | Y | 1 | 1 |
| 9.46a | 660 | 32 | 420 | pb,pbp | congestion | - | n | 0 | - |
| 9.47a | 130 | 18 | 420 | - | asia | - | n | 0 | - |
| 9.47b | 840 | 18 | 190 | - | asia | - | n | 0 | - |
| 9.48a | 70 | 29 | 360 | - | congestion | spike,bounce | n | 0 | - |
| 9.48a | 420 | 11 | 45 | - | asia | spike | n | 0 | - |
| 9.48a | 420 | 29 | 360 | - | post-leg | spike | Y | 1 | 25 |
| 9.48b | 480 | 0 | 80 | pb,pbc | asia | - | n | 0 | - |
| 9.48b | 705 | 30 | 250 | pb,pbc | congestion | - | Y | 2 | 4 |
| 9.48c | 1080 | 37 | 260 | pr | congestion | - | n | 0 | - |
| 9.4b | 815 | 19 | 245 | tff | congestion | - | Y | 1 | 7 |
| 9.4b | 855 | 11 | 35 | tff | pattern | - | Y | 2 | 1 |
| 9.4b | 890 | 21 | 20 | tff | 2nd/inner,kept-past-break | - | n | 0 | - |
| 9.50a | 590 | 13 | 115 | pb | round | - | Y | 2 | 2 |
| 9.50c | 875 | 12 | 135 | tff | post-leg | - | n | 0 | - |
| 9.51a | 300 | 18 | 390 | pb | asia | - | n | 0 | - |
| 9.51b | 840 | 36 | 245 | - | asia | - | n | 0 | - |
| 9.52a | 250 | 23 | 360 | pb,pbc | congestion | - | n | 0 | - |
| 9.52b | 840 | 23 | 155 | - | congestion | - | n | 0 | - |
| 9.53a | 250 | 16 | 360 | pbp | asia | - | Y | 1 | 1 |
| 9.53b | 840 | 15 | 140 | pb,pbp | congestion | test | n | 0 | - |
| 9.54a | 470 | 22 | 430 | - | congestion | tease | Y | 1 | 18 |
| 9.56a | 125 | 13 | 425 | - | round | test | n | 0 | - |
| 9.56a | 540 | 17 | 40 | - | congestion | test | n | 0 | - |
| 9.56b | 780 | 40 | 170 | pbc,pbp,pr | asia | named-extreme | n | 0 | - |
| 9.56c | 840 | 8 | 100 | - | post-leg | - | n | 0 | - |
| 9.57c | 980 | 13 | 65 | - | congestion | - | Y | 1 | 6 |
| 9.58a | 545 | 16 | 40 | pb,tff | post-leg | - | Y | 1 | 1 |
| 9.59c | 1035 | 29 | 85 | pb | congestion | - | Y | 1 | 3 |
| 9.60b | 770 | 49 | 175 | - | congestion | - | n | 0 | - |
| 9.60b | 900 | 66 | 420 | - | 2nd/inner | - | n | 0 | - |
| 9.61b | 895 | 30 | 75 | - | congestion | - | Y | 1 | 3 |
| 9.62a | 600 | 26 | 55 | pbc | congestion | tease | n | 0 | - |
| 9.62b | 675 | 19 | 295 | pb | congestion | test | n | 0 | - |
| 9.62b | 840 | 66 | 420 | pb | post-leg,2nd/inner | test | n | 0 | - |
| 9.63a | 450 | 13 | 349 | pbp | round | test | n | 0 | - |
| 9.66c | 1140 | 32 | 200 | pb | congestion | - | Y | 1 | 5 |
| 9.6a | 565 | 6 | 45 | pb | 2nd/inner | tease | Y | 2 | 10 |
| 9.6a | 600 | 18 | 275 | pb | congestion | tease | Y | 3 | 1 |
| 9.7a | 580 | 12 | 115 | pb,pr | pattern | - | n | 0 | - |
| 9.7b | 540 | 17 | 350 | pb | day-range | - | Y | 3 | 1 |
| 9.8b | 600 | 22 | 240 | - | kept-past-break | - | Y | 2 | 4 |
| 9.8c | 805 | 28 | 410 | pb | congestion | tease | n | 0 | - |

---

## D3 — Hypotheses, null-first

All parameters stated in `dr_final.py` header before measurement.
Null = within-panel label shuffle, 200 draws; positional features use
the density-aware null. Bold = survives.

**H-hind (hindsight selection) — REJECTED, strongly.**
If the author picked the box that subsequently breaks/runs, a post-τ
rule would recover the golden. It does not: pick fastest post-τ break
→ **2/51 (avail), 6/50 (live)** vs random 4.1/8.1; pick max post-break
excursion → 2/51. Matching cands' post-τ excursion is *lower* than
non-matches (-2.51 ABR). There is a weak base-rate elevation — match
cands close outside their band within 24 bars at 89.7% vs 71.5% — but
it is unusable as a selector because breaks are near-universal and
immediate in both groups (median brk_bar = 1). The arrows themselves
straddle τ (43% before, median +5min). The author does not draw around
the soon-to-break box; he draws the box the setup is *already about*.
Goldens explained by hindsight: **≈0**.

**H-frame (dominant congestion in the crop) — REJECTED as a
mechanism.** Golden spans 36% of the window (med), 33% of its price
range; in **80/119** panels a *non-matching* cand covers more window
bars than the golden. The author crops around the story, not around
the biggest range. Crop choice is evidence of narrative framing, and
it is not usable as a τ-feature anyway.

**H-round50 — REJECTED at the edges.** Golden edge within 1.5p of a
00/50: **11/119 = 9.2%**, density-aware null mean **10.1** (p95 14.0).
Golden bands do straddle a 00/50 at 36% vs 26% for cands — descriptive
context the author *mentions*, not what discriminates the pick
(matching cands straddle *less*, 22% vs 26%).

**H-prior (Asia range / day open / day extremes as edge anchors) —
REJECTED, reversed.** Matching cands sit *farther* from the Asia range
edges (diff -2.93p, null p95 +1.18) and day open (-7.2p) than
non-matches. The author's edges are episode-local, not session-anchored
— except for the 11 asia_box goldens where the box IS the session
range (those are mostly unreachable anyway).

**H-setup — WEAK coverage signal, no selection signal.** Setup tags
predict *reachability* (pattern/session containers 25-33% vs fresh-
congestion setups ~50%) but among reachable goldens no setup group is
picked better by any rule. Reachability, not selection, is where the
setup bites.

**H-shape — REJECTED on stated summary.** n_swings (zigzag 0.3·ABR)
diff -0.05 vs null ±0.9; compression 0.007 vs ±0.08; both dead. Two
shape-adjacent features DO survive but reversed/partial: matching cands
have **fewer** edge touches (diff -2.44, null p95 +1.06 — the author's
box is a *cleaner* container than the touched-to-death rivals), and
higher `px_frac` (+0.77: price sits higher in the band) and lower
`dist_close_edge` (+1.95 ABR-closer) at τ. So the surviving shape
story is "price is parked inside/near the fresh box", not "the box
contains a tidy ≥2-swing rectangle".

**H-fresh (own, strongest) — the one survivor.** Youngest-born cand
picks 20/51 (avail) / 20/50 (live); vs null p95 7/12. Freshness is
real on both `age_bars` (+39 bars younger, null p95 ±7) and
`bars_since_touch` (+21, p95 ±4). Not a small-pool artifact: hit-rate
by pool size 100% (≤20 cands) → 53% (20-35) → 29% (35-50) → 25%
(50+) while random falls 13%→3% — the *lift* grows with clutter. But
establishment gates (age≥k, span≥k) *hurt* (20→13-16): it is not
"freshest sufficiently-formed", it is literally "the newest event
structure". The indistinguishable goldens' matches sit at birth-rank
2-6 — the author often boxes the *penultimate* episode when the
newest thing is a micro-fragment.

**H-cluster (own) — partial.** Golden's cluster contains price 44/51,
is most-recently-born 38/51, biggest only 22/51. Cluster pick
(contains-px → freshest cluster → youngest member) = 19/51, no gain
over flat youngest.

**H-pivot (own, mechanistic) — confirms the freshness story.** The
last zigzag pivot before τ (0.5·ABR amplitude) sits *inside* the
golden band in **82%** of goldens vs 21% for a random avail cand;
median distance pivot→golden edge 0.56 ABR vs 2.56. The author's box
wraps the most recent swing point — which is *why* youngest-born works
(the freshest birth is the one anchored on that pivot). As a selection
gate it adds nothing over youngest (16/48 vs 20/51): it is the same
signal, not a second one.

**H-span (own, diagnostic).** Matching cands' drawn span covers only
62% of the golden window (med), IoU≥0.5 in 27/145; for the 20
youngest-rule hits, 9/20. Even a perfect edge-picker loses ~half at
the ruler unless `build_start` is set to the *episode* start, not the
pivot pair's first leg.

### Numbers table (selection rules, recall@1, reachable goldens)

| rule | pool | hits | ties |
|---|---|---|---|
| random null | avail | 4.1 (p95 7) | - |
| random null | live | 8.1 (p95 12) | - |
| **youngest-born** | avail | **20/51** | 0 |
| **youngest-born** | live | **20/50** | 0 |
| px_in → youngest | avail | 18/51 | 0 |
| touch==0 → youngest | avail | 20/51 | 0 |
| cluster(px,fresh) | avail | 19/51 | - |
| mid-band → youngest | live | 10/50 | 0 |
| max-overlap | avail/live | 3-6 | most |
| freshest-touch | live | 5/50 | 48 |

---

## D4 — Causal upper bound

Candidate universe: event_cands stream (rd 7,706 + pb 2,014), `born<=τ`.
Reachable = ≥1 avail cand edge-matches the golden: **51/119 (43%)**.

- Best demonstrated *stated* rule: youngest-born → **20/51 = 39%** of
  reachable = **17% of all 119**.
- Oracle over 19 single features (any one strict-tops a match):
  **30/51 (59%)**.
- Oracle over 35 stated 2-level conjunctions: **34/51 (67%)**.
- **Indistinguishable: 21/51 single-feature, 17/51 under conjunctions**
  — no tested causal ordering puts a match strictly on top.
- Ruler-strict haircut: of 20 rule-hits only ~9-10 would also satisfy
  containment-window IoU≥0.5 as drawn.

Accounting over all 119:

| stage | count | cum. rate |
|---|---|---|
| unreachable (no avail cand with golden edges) | 68 | — |
| reachable, picked by best rule | 20 | 17% |
| reachable, oracle-conjunction | +14 | 29% |
| reachable, indistinguishable | 17 | — |

Unreachable joint decomposition (edges-seen in born level vocabulary
× 6-34p envelope):

| golden edges found among born cands | env-ok | env-viol | total |
|---|---|---|---|
| both edges, never paired | 17 | 10 | 27 |
| one edge only | 20 | 5 | 25 |
| neither edge | 16 | 0 | 16 |

So: **27/68 have both edges already in the stream but never paired**
(pairing-rule loss — double-touch/pullback event spec too narrow);
15/68 violate the 6-34p envelope (tall Asia/range boxes); only 16/68
are a pure level-discovery gap. A relaxed pairing channel ("latest
tested-high × latest tested-low within envelope") could reach the
env-ok half of the unpaired set. Separately, scanning the raw stream
(incl. post-τ births): **14/68 get a matching cand born 1-51 bars
AFTER τ** — a birth-latency class: the author draws around visible
congestion before the second pivot confirms, so confirmed-pivot routes
are structurally late on ~12% of all goldens. (No edge asymmetry in
the one-edge cases: 10 only-top-seen vs 15 only-bottom-seen.)

Unreachable-set probes: nearest *single* cand to golden edges is a
median **10.5p combined** away (7/68 within 3p, 28/68 within 8p) — so
no existing cand is a near-miss needing only a tolerance tweak; the
edges exist scattered across different cands (above) but are never
combined. Naive session proxies don't rescue it either: golden ≈
Asia-00-07 range 0/68, ≈ day-so-far range 3/68, ≈ last-40-bars range
8/68 — and 50/68 goldens sit strictly *inside* the last-120-bar range:
the author's edges are **inset** (drawn where price held, not to wick
extremes). A second birth channel must snap to *holding* edges
(touched-and-respected levels), not to session/window extremes.

Birth-order interaction (which throttle can even see the matches):
matching cands' earliest birth rank within their panel is **median 32**
of ~40 — they are the *late* births, not the early ones. A throttle
that keeps the first N births reaches only **4/51** at N=2, 10/51 at
N=8, 18/51 at N=20. But 20/51 goldens have a match at the *youngest*
birth rank.

Keep-last-K funnel (retain the K most recent births at τ, pick
youngest): K=1 already reaches **20/119 with 20 hits** — a single
freshest-birth object per panel doubles C-2's class (10/119) at the
author's own one-object economy. K=2..20 reaches 28→47 goldens but
adds **zero** hits under youngest-pick (their matches sit at rank ≥2).
Rule robustness: youngest@live is 20/50 at every LIVE_WIN in 4-40
bars; excluding τ-broken cands gives 16/41 (same ~39% rate; the
dropped goldens are the "kept past break" boxes). Conclusion: the only
affordable funnel is **keep-freshest** — live-at-τ ink, keep-last-K
retention, youngest selection are one mechanism.

Channel complementarity (per-cell hits from
`evalcheck/_hybrid_rows_evalcheck.pkl` on the same 119 cells): v1=10,
v0=16, hybrid=16. keep-last-1 hits overlap v1 only **3** → oracle
union **27/119**; overlap hybrid 4 → union **32/119**. The event
channel and the structural channel hit *different* goldens — the
recoverable mass lives in the family rank-1 arbitration (when to trust
the event object vs CONTEXT_RANGE), which is exactly the pick-pollution
the §20 arm paid (-14 flips). An oracle arbiter over the two channels
would land ~27 — above the single-channel edge ceiling.

**Unpredictable fraction**: of the 51 the stream can draw, ≥17-21
(33-41%) are causally indistinguishable; scaled to all goldens, the
ceiling on causal reproduction of the author's pick is ~29% at oracle,
~17% demonstrated — the **unpredictable part is ≥70% of the author's
boxes under a one-box, edges-exact standard**, dominated by a
reachability gap (57%) and a semantic selection residual (~33% of
reachable).

*Consistency with the prior ledger* (fresh-eyes check, not blind
acceptance): the previous round's oracle "any pivot-cluster pair
inside the golden span = 50/119" matches my event-stream reachability
51/119 — same wall, one more golden. Its surviving formulation
"liveness-scoped, liveness-ranked birth slot" is the same direction my
youngest-among-live rule measures (20/50); I add that the birth-side
funnel must be keep-freshest (matches are median birth-rank 32, last
births), and that selection tops out ~40% of reachable even at oracle
— the residual is semantic, not rankable. Its episode-start detector
"lands inside the episode (741 vs t0 580)" differs from my simple
walk-back-while-overlap estimator (14/20 IoU) — mine walks the *band
edges*, theirs detected episode onset on the time axis; both are
causal, results differ, the walk-back is worth one honest A/B.

---

## Frontier — plain words

*What the event routes are.* The old engine drew a box when price made
a confirmed pivot pair: two swing highs within 2 pips = `range_double_
top`, two swing lows = `range_double_bottom`, a pullback that stalls =
`pullback_end`. Each birth anchors the box edges on those pivot prices.

*Why births cost ink.* The ruler charges "ink" for every object whose
drawn span intersects the window — dead or alive. v0 birthed ~6.5-9
boxes/panel; the author draws ~1. At an author-level economy we can
afford ~1-2 births per panel, so we must *select*, not just generate.

*The throttle matrix.* Tried: birth cooldowns, ≤2 births/panel,
update-in-place (one event object), dedup, envelope 6-34p. Result:
under ≤2 births the right cand is often never born (pre-birth loss);
update-in-place keeps 5/15; the wide stream reaches 51/119 edges but
is unaffordable under cumulative ink.

*Why no causal rule picks the right box.* The candidate pool at τ holds
~40 born cands (~17 still live) of look-alike ranges. The golden is usually *fresh* (youngest works
20/51) but in 2/5 of reachable panels the author picks a penultimate or
semantically-framed sibling — the Asia range, the W-container, the
absorption base — whose only distinguishing marks are the episode label
and the crop, neither of which is a causal feature. Post-τ outcome
doesn't separate them either. Worst case for intuition: 9.20c — the
golden is the 16:25–18:30 rectangle [13312–13322]; the only
edge-matching cand in the whole stream was born at bar 8 and last
touched 23 bars before τ — an ancient dead box at coincidentally-
identical prices — while every live cand (9 at τ) sits at other edges.
"The author's edges" is not a property any ranking can see.

*The live-at-τ option.* Most of v0's ink is dead-object residue:
strict live clutter median is 2.0 objects/panel vs the author's ~1.
Counting ink only for objects alive at τ makes the wide event stream
nearly affordable (loose live 4.25), turning the problem from "can't
afford births" back into "must select well" — where the demonstrated
ceiling is ~20-34/119 edges-exact, ~14-20 after the span-IoU haircut (measured: episode-anchored build_start lifts 9->14 of 20).

---

## Recommendations (for the Owner's three-way choice)

1. **Count clutter only for objects live at τ** — this is the honest
   accounting and unlocks the only lever that demonstrably moves
   coverage (reach is the biggest loss pool: 68/119). Recommend
   re-running v0-width stream scored live-at-τ.
2. **The buildable rule with explicit parameters** — and it already
   exists: `ev_uip_persist` (one event object, rd rewrites in place,
   close-veto) measured **16/119 = v0 parity at births 1.0/panel** in
   the §20 A/B. My measurements explain it (keep-last-1 re-anchor =
   the author's recency) and bound it (edge-exact ceiling ~20/119;
   the arm is at 16 — near the mechanism's ceiling). Two measured
   headroom items, in priority order:
   (a) let `pullback_end` rewrites count too: youngest-either 20/51 vs
   youngest-rd 18/38 — worth ~+2 edge-exact goldens (T1/UIP-rd was
   rd-only);
   (b) `build_start` = episode anchor (walk back from t0 while bars
   overlap the band): span-IoU≥0.5 goes 9→14 of 20 rule-hits measured.
   Known cost from §20: the persistent slot perturbs the level stream
   (-4) via edge-seeded competing LEVEL_CARRIED — candidate fix noted
   there (exempt the ev object from the box-family cap).
   Reconciliation: T1/UIP-rd was the same keep-last-1 mechanism scored
   on the 15-cell v0 subset (5/15); re-run over all 119 gives
   youngest-rd 18/38, pb 13/28, either 20/51.
   (c) the arbitration layer: event-channel and structural-channel hits
   are nearly disjoint (overlap 3-4; oracle union 27-32/119). Tested
   stated arbiters (event iff age≤k, iff close-in-band, iff overlap≥.5)
   all land at 20/119 — they never rescue v1's disjoint hits, because
   when the event pick is wrong the event object's own features don't
   say so. The +7-11 union gap is a genuine FIT problem — logged as
   `ESCALATE: FIT arbiter` below if the Owner wants it pursued.
3. **Do NOT chase a bigger salience model on the same features** — the
   oracle bound (34/51) says the residual is semantic. If more
   coverage is wanted, attack *reachability* instead: a second birth
   channel for session/episode containers (Asia range box, post-spike
   base, "first sideways block after a leg ≥N bars") — these are
   text-bookable, causal, and orthogonal to pivot pairs.
4. Accept that author-exact box picking is a ~30%-ceiling problem
   (consistent with Osler's ~30% inter-expert level agreement): the
   practical goal should be *a* tradeable box per panel (any
   reasonable episode), not *his* box — the ruler already pays for
   correct geometry, so optimize the engine's own precision, not
   golden-matching.

One escalation filed: `ESCALATE: FIT arbiter` — dataset
`deepresearch/arbiter_rows.pkl` + deterministic protocol stub
`dr_arbiter_fit.py` (baselines verified: always-event 20, always-v1
10, oracle union 27/32). The +7-11 union gap is the only place a fit
might still buy points; everything else in this report is measured,
not fitted.

---

## Owner summary (10 lines)

1. Câu hỏi: box của Volman có đoán được từ thông tin tại τ không? Trả
   lời: **một phần — trần nhân-quả ~20-34/119 (17-29%)**.
2. Event stream vẽ đúng cạnh cho 51/119 golden; 68/119 không bao giờ
   có candidate đúng cạnh (lỗ hổng lớn nhất = reach, không phải chọn).
3. Rule nhân-quả tốt nhất: "box event mới nhất còn sống" → 20/51
   reachable; oracle mọi rule đã test chỉ 34/51.
4. ≥17/51 reachable không phân biệt được bằng mọi feature nhân-quả —
   tác giả chọn theo ngữ nghĩa (Asia range, W/M container, base sau
   spike), không phải hình học.
5. Hindsight bị bác mạnh: box tác giả KHÔNG phải cái break sớm/chạy xa
   sau τ (2-6/51, dưới cả random).
6. Round-50, Asia/day anchors, shape, dominant-congestion: đều chết
   dưới null density-aware.
7. Bớt gánh ink: đếm clutter chỉ cho object sống tại τ (live med 2.0)
   — stream rộng gần như affordable.
8. Đề xuất: live-at-τ accounting; arm `ev_uip_persist` đã đạt 16/119
   (≈ trần của cơ chế keep-freshest); headroom đo được: +pb rewrites
   (~+2), build_start neo episode (+5 span-IoU); đừng fit thêm trên
   cùng feature set.
9. Khớp Osler 2000: experts chỉ đồng thuận ~30% trên levels — replicate
   một human cụ thể có trần tự nhiên ~30%.
10. Chi tiết: mục D1-D5 ở trên; scripts `dr_*.py`, log `DR_LOG.md`.
