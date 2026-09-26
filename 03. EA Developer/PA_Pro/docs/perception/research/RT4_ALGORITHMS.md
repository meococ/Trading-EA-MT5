# RT4 — Algorithms for chart perception

**Lane:** PA-PRO PERCEPTION. **Agent:** RT4. **Scope:** candidate algorithms for detecting, ranking and freezing the objects in `VOLMAN_PERCEPTION_SPEC_v1.md` (swings/pivots, lines, levels/zones, boxes/ranges, squeezes, brackets) under the hard requirements: causal, deterministic, cheap (O(1)/O(window) per bar), stable geometry, sparse output (~3 objects per chart).
**Units:** pips = 1e-4 on EURUSD; ABR = mean M5 bar range of last 50 closed bars (~4–7 pips in the 2012 book data); lag in M5 bars.

## 1. Scope, method, verification status

Every work below was located via `web_search` and its official page (journal DOI page, arXiv, NBER, ACM/VLDB/IEEE records, publisher, or author-university page) was fetched or snippet-verified. No shadow sources; no book downloads. Claim grades: **EVIDENCE** (published empirical/algorithmic result), **PRACTITIONER** (named author's rule, untested), **FOLKLORE** (repeated, no source).

| # | Work | Venue / identifier | Verified | Grade |
|---|------|--------------------|----------|-------|
| 1 | Guillaume, Dacorogna, Davé, Müller, Olsen, Pictet (1997), "From the bird's eye to the microscope" | *Finance and Stochastics* 1(2):95–129, DOI 10.1007/s007800050018 | RePEc/Springer record | EVIDENCE (tick FX, 1997-era) |
| 2 | Glattfelder, Dupuis, Olsen (2011), "Patterns in high-frequency FX data: 12 empirical scaling laws" | *Quantitative Finance* 11(4):599–614, DOI 10.1080/14697688.2010.481632; arXiv:0809.1040 | arXiv full text fetched (pseudocode + EUR-USD tables) | EVIDENCE |
| 3 | Tsang (2010), "Directional Changes, Definitions" | CCFEA Working Paper WP050-10, Essex | Listed on CCFEA page | PRACTITIONER (formalisation) |
| 4 | Tsang, Tao, Serguieva, Ma (2017), "Profiling High Frequency Equity Price Movements in Directional Changes" | *Quantitative Finance* 17(2):217–225, DOI 10.1080/14697688.2016.1164887 | DOI + CCFEA listing | EVIDENCE |
| 5 | Bakhach, Chinthalapati, Tsang, El Sayed (2018), "Intelligent Dynamic Backlash Agent" | *Algorithms* 11(11):171, DOI 10.3390/a11110171 | DOI + Essex repository PDF | EVIDENCE (DC trading is causal-by-construction) |
| 6 | Chung, Fu, Luk, Ng (2001), "Flexible time series pattern matching based on perceptually important points" | IJCAI 2001 workshop | PolyU Scholars page | EVIDENCE (algorithm) |
| 7 | Fu, Chung, Luk, Ng (2008), "Representing financial time series based on data point importance" | *Eng. Applications of AI* 21(2):277–300, DOI 10.1016/j.engappai.2007.04.009 | DOI page | EVIDENCE |
| 8 | Douglas & Peucker (1973), line simplification | *Cartographica* 10(2):112–122, DOI 10.3138/fm57-6770-u75u-7727 | Journal record | EVIDENCE |
| 9 | Abam, de Berg, Hachenberger, Zarei (2007), "Streaming algorithms for line simplification" | SoCG'07, DOI 10.1145/1247069.1247103 | ACM record | EVIDENCE |
| 10 | Lin, Ma, Zhang, Wo, Huai (2017), "One-Pass Error Bounded Trajectory Simplification" (OPERB) | PVLDB 10(7):841–852, DOI 10.14778/3067421.3067432 | VLDB PDF | EVIDENCE |
| 11 | Keogh, Chu, Hart, Pazzani (2001), "An online algorithm for segmenting time series" (SWAB) | ICDM 2001, DOI 10.1109/icdm.2001.989531 | IEEE + UCI copy | EVIDENCE |
| 12 | Andrew (1979), monotone-chain convex hull | *Inf. Proc. Letters* 9(5):216–219, DOI 10.1016/0020-0190(79)90072-3 | ScienceDirect | EVIDENCE |
| 13 | Preparata (1979), real-time planar hull | CACM 22(7):402–405, DOI 10.1145/359131.359132 | ACM | EVIDENCE |
| 14 | Overmars & van Leeuwen (1981), dynamic hull with deletions | *J. Comp. Sys. Sci.* 23(2):166–204, DOI 10.1016/0022-0000(81)90012-X | Elsevier | EVIDENCE |
| 15 | Fischler & Bolles (1981), RANSAC | CACM 24(6):381–395, DOI 10.1145/358669.358692 | ACM | EVIDENCE |
| 16 | Duda & Hart (1972), Hough (angle-radius form) | CACM 15(1):11–15, DOI 10.1145/361237.361242 | ACM | EVIDENCE |
| 17 | Ester, Kriegel, Sander, Xu (1996), DBSCAN | KDD'96:226–231 | AAAI/dblp record | EVIDENCE |
| 18 | Ester, Kriegel, Sander, Wimmer, Xu (1998), IncrementalDBSCAN | VLDB'98:323–333 | VLDB PDF | EVIDENCE (incremental result provably = batch) |
| 19 | Cheng (1995), mean shift | *IEEE TPAMI* 17(8):790–799, DOI 10.1109/34.400568 | IEEE | EVIDENCE |
| 20 | Kristan, Skočaj, Leonardis (2010), online KDE | *Image and Vision Computing* 28(7):1106–1116, DOI 10.1016/j.imavis.2009.09.010 | ScienceDirect | EVIDENCE |
| 21 | Killick, Fearnhead, Eckley (2012), PELT | *JASA* 107(500):1590–1598, DOI 10.1080/01621459.2012.737745; arXiv:1101.1438 | JASA/Lancaster | EVIDENCE — **offline/batch**, see §4 |
| 22 | Adams & MacKay (2007), Bayesian online changepoint detection | arXiv:0710.3742 (Cambridge Cavendish) | arXiv PDF | EVIDENCE |
| 23 | Page (1954), CUSUM | *Biometrika* 41(1/2):100–115, DOI 10.1093/biomet/41.1-2.100 | OUP/JSTOR record | EVIDENCE |
| 24 | Romano, Eckley, Fearnhead, Rigaill (2023), FOCuS | *JMLR* 24(81):1–36, arXiv:2110.08205 | JMLR page | EVIDENCE |
| 25 | Witkin (1983), scale-space filtering | IJCAI'83:1019–1022 | IJCAI proceedings PDF | EVIDENCE |
| 26 | Edelsbrunner, Letscher, Zomorodian (2002), topological persistence | *Discrete & Comput. Geom.* 28(4):511–533, DOI 10.1007/s00454-002-2885-2 | Springer/Stanford page | EVIDENCE |
| 27 | Gidea & Katz (2018), TDA of financial time series | *Physica A* 491:820–834, DOI 10.1016/j.physa.2017.09.028 | ScienceDirect | EVIDENCE (different use: point-cloud loops, not swing ranking) |
| 28 | Jiang, Kelly, Xiu (2023), "(Re-)Imag(in)ing Price Trends" | *J. Finance* 78(6), DOI 10.1111/jofi.13268; SSRN 3756587 | Wiley/Yale/SSRN | EVIDENCE |
| 29 | Cohen, Balch, Veloso (2020), "Trading via Image Classification" | ICAIF'20, DOI 10.1145/3383455.3422544; arXiv:1907.10046 | ACM/arXiv | EVIDENCE |
| 30 | Lo, Mamaysky, Wang (2000), "Foundations of Technical Analysis" | *J. Finance* 55(4):1705–1765; NBER WP 7613, DOI 10.3386/w7613 | NBER/MIT | EVIDENCE |
| 31 | Wilder (1978), *New Concepts in Technical Trading Systems* | Trend Research, ISBN 0-89459-027-8 | OpenLibrary/publisher | PRACTITIONER (ATR) |
| 32 | Kaufman (1995), *Smarter Trading* | McGraw-Hill, ISBN 0-07-034002-1 | Publisher citation | PRACTITIONER (efficiency ratio) |
| 33 | Williams & Gregory-Williams (1995/2004), *Trading Chaos* | Wiley, ISBN 978-0471463085 (2nd ed.) | Wiley/Google Books | PRACTITIONER (5-bar fractal) |
| 34 | Dreiss (1992), choppiness index | *Commodity Traders Consumer Report*, Jul/Aug 1992 | Secondary citations (Futures Mag. Oct 1993) | PRACTITIONER |
| 35 | Darvas (1960), *How I Made $2,000,000 in the Stock Market* | American Research Council, Larchmont NY | OpenLibrary/Harriman reprint | PRACTITIONER (box rules) |

Caveat kept sharp throughout: an algorithm being published is **not** evidence it reproduces trader perception. The EVIDENCE grade covers "the method computes X in Y time"; perceptual fidelity is our golden-set question (spec §6.1).

---

## 2. Topic 1 — Swings and pivots (the foundation)

All methods below produce a sequence of alternating extremal points (pivots). The discriminating questions: what counts as a reversal, when is a pivot *confirmed*, and how many pivots per 84-bar window.

### 2.1 Williams fractal (k-bar extremum)
Pivot high at *t* iff high[t] > highs of the k bars on each side (Williams uses k=2). **Lag:** fixed k bars. **Units:** bars only — no amplitude filter. Per-bar cost O(1) with a deque. **Failure modes on M5 FX:** in flat Asia it emits a pivot every few bars (wick noise → micro-pivots, exactly our current over-production bug); a 40-pip news bar swallows the k-neighbourhood and pivots are *missed* near the spike's own shoulders. **Verdict:** usable only as a pre-filter feeding an amplitude rule; never as the swing definition. Grade PRACTITIONER (Williams 2004).

### 2.2 ZigZag (percent / absolute retrace)
State machine: track running extreme `xext` and direction; when price retraces ≥ z from `xext`, mark `xext` a pivot and flip direction. **Lag:** variable — pivot confirmed when the θ-retrace completes (data-dependent). **Units:** z in %, pips, or ABR multiples. FOLKLORE as a platform indicator — but mathematically it *is* the directional-change dissection, which is the best-studied member of this family.

### 2.3 Directional change (DC) / intrinsic time — evaluate seriously: yes
Origin: Guillaume et al. (1997) count directional changes of size Δχ in tick FX and find the count scales as N ∝ Δχ^{E}, E ≈ −2. Glattfelder, Dupuis & Olsen (2011) publish the full event framework (their Algorithm 2) and 12 scaling laws on 5 years of ticks, 13 pairs. Tsang's CCFEA line (WP050-10; Tsang et al. 2017; Bakhach et al. 2018) makes DC a threshold-parameterised FX analysis/trading framework.

**Definition (adapted to bars).** Mode ∈ {up,down}; track `xext` (highest high / lowest low since mode start). A DC *event* fires when the opposite-side price moves ≥ θ from `xext`; the old extreme becomes a confirmed pivot; mode flips. Between DC event and the next one is an *overshoot* leg.

**Incremental state:** {mode, xext, t_ext, last pivot}. Per-bar update: O(1) — compare h/l to xext, test retrace ≥ θ.

**Key EUR-USD numbers (Table 1 / Table A9 of [2], tick data 2003–2007, EBS):**
- Time between DC events scales as θ^{1.88} (C = 1.1e-3, θ in %). Sanity-checked unit: θ=0.1% → ≈4,800 s ≈ 16 M5 bars; θ=0.05% → ≈1,300 s ≈ 4–5 bars; θ=0.08% (~2×ABR, 10 pips) → ≈3,000 s ≈ 10 bars → ~8 DC events per 84-bar window.
- **Overshoot ≈ θ on average** (E_os ≈ 1.0, C_os ≈ 0.99) and total move ≈ 2θ; overshoot *time* ≈ 2× DC-section time. Direct use: expected poke depth beyond a level ≈ θ-scale — feeds zone widths (§3) and explains why edges need tolerance.
- Coastline: at θ=0.05%, ~6.4%/day cumulative — warns that fine thresholds explode object counts.

**Confirmation lag:** pivot at `t_ext` is confirmed at the DC event; expected lag ~ θ^{1.9} → for θ = 2×ABR ≈ 10 pips, ~5–10 bars typical; the lag is *data-dependent* (fast in trends, long in drift). This is the honest price of amplitude filtering.

**Behaviour on our edge cases:** news spike — retrace past θ fires quickly, spike tip becomes a pivot fast (good: the spike high is exactly what Volman marks); flat Asia — DC events go rare, no micro-pivots (good); whipsaw — each θ-sized alternation is a real pivot by construction (acceptable — whipsaw is then filtered by *salience*, §5, not by the detector); weekend gap — opens >> θ away: fire one DC event on the first bar, flag `gap` event; DST — orthogonal (θ in price units, session rules in CET helpers).

**Threshold units:** express θ = k·ABR (percent of price ≈ ABR-fraction for EURUSD). k is the *one* tuning parameter of the whole stack; §7 shows how to fix it from golden.

**Adaptation caveat (ours, not the papers'):** DC is defined on ticks. On bars we must choose the extreme source. Recommendation: track extremes on **high/low** (wick-inclusive — Volman's edges sit on wicks) but optionally require the retrace on **close** for confirmation; measure both on TUNE.

### 2.4 Perceptually Important Points (PIP)
Chung et al. (2001) / Fu et al. (2008): order points by importance = max distance of a point to the chord between its two already-selected neighbours (variants ED/PD/VD); recursively split. Designed for representation and retrieval, includes a tree supporting incremental update. **Lag:** importance of point i is evaluable only once it has a right neighbour — in a stream this means deferred evaluation at the next pivot's confirmation. **Causal use sketch:** on each confirmed pivot P, score `imp(P) = vertical distance from P to the chord (prev pivot → next pivot)` once the next pivot exists — O(1), deterministic. This is essentially a *prominence-like* salience score (§5). Direct fit: cheap, principled ranking of already-detected pivots rather than a detector itself. EVIDENCE as an algorithm; the perceptual claim is the authors' terminology, not measured against traders — treat as plausible.

### 2.5 Ramer–Douglas–Peucker (RDP)
Recursive chord-farthest-point split with tolerance ε (Douglas & Peucker 1973). **Non-causal as stated:** the vertex set over [0,t] can change when future points arrive (a new extreme can retroactively promote intermediate vertices). Causal cousins exist in the trajectory-compression literature — opening-window DP, one-pass bounded-error algorithms (OPERB, Lin et al. 2017: O(n) time, O(1) space, bounded error), and streaming simplification with competitive guarantees (Abam et al. 2007). **Verdict:** for us, DC beats RDP-family: RDP vertices minimise a chord-error, not "extreme of a ≥θ move", and its output points need not be wick extremes. Keep OPERB-style one-pass simplification in the toolbox only as a cheap polyline for CONTEXT_LINE decimation or offline golden analysis. EVIDENCE (algorithms), but wrong objective for wick-anchored pivots.

### 2.6 Confirmation-lag comparison (Topic 1)
| Method | Lag | Threshold unit | News spike | Flat Asia |
|---|---|---|---|---|
| k-bar fractal | k bars (fixed) | bars only | misses shoulders | floods |
| ZigZag/DC | time for θ-retrace, ~θ^1.9 | % / pips / ABR-mult | fast confirm | silent |
| PIP | = successor pivot lag | chord distance | fine | ranks only |
| RDP | retroactive (non-causal) | ε (price) | n/a offline | n/a |

**Recommendation:** DC state machine, θ = k·ABR, wick extremes, close-confirmed variant as a TUNE comparison. It is the only family here with published FX scaling laws giving us a priori lag/count estimates.

---

## 3. Topic 2 — Lines (PATTERN_LINE, CONTEXT_LINE)

A Volman line = a *supporting* line through ≥2 same-side swing extremes with all intervening extremes within tol on the correct side (tol = max(1 pip, 0.25·ABR), spec §1). Anchors must come from the confirmed-pivot set — never from a refit that moves the line.

### 3.1 Incremental convex hull — the principled anchor set (assess seriously: strong yes)
Take confirmed swing lows as points (t, price). **Fact (computational geometry):** any line touching ≥2 lows with all lows on/above it touches the set's *lower convex hull* at its support points; support points are hull vertices or lie on hull edges. So the candidate anchor set ⊆ lower-hull vertices — parameter-free, exactly the "least-touch trendline" anchors.

**Incremental update:** insertions only at increasing t → monotone-chain style append (Andrew 1979): each new point walks back the hull deleting non-convex vertices; amortised O(1) per insertion. Deletions as pivots leave the 84-bar window: dynamic hull (Overmars & van Leeuwen 1981, O(log² n)) exists, but with ≤ ~30 window pivots a plain O(n) rebuild per bar is trivial — recommend rebuild, simplest to port to MQL5. (Preparata 1979 gives the real-time O(log n) insertion result.)

**Candidate lines:** hull edges (adjacent vertex pairs) are the maximal-support lines; also test non-adjacent vertex pairs whose chord leaves all intervening lows within [−tol, +tol] — covers Volman's "lows a few pips above the line are fine". Deterministic enumeration over a tiny candidate set; O(h²) with h = hull size ≪ 30.

**Failure modes:** a news-spike wick becomes a hull vertex and can drag a line — mitigate by *excluding FALSE_EXT-flagged pivots from hull input* (spec §3.1 spike rule) and by scoring candidates by touch count before drawing. Weekend gap pivots similarly flagged.

### 3.2 RANSAC (Fischler & Bolles 1981)
Robust to outliers, but random by design: violates byte-determinism unless seeded, and with ≤30 candidate points exhaustive pair enumeration is cheaper and exact. **Verdict: reject** — wrong tool; use the hull.

### 3.3 Hough transform (Duda & Hart 1972)
Vote in a quantised (ρ,θ) accumulator; peaks = lines. Two mismatches: (a) quantisation → line parameters snap to bins → *jitter* (exactly our stability failure); (b) no notion of one-sided support — Hough finds collinearity, not support. **Verdict: reject as detector.** Useful insight retained: peaks + hysteresis on vote counts is a model for line *salience* and for "when to stop extending" (votes stop accumulating).

### 3.4 Least-squares refit
Fits move with every new point → jitter; residuals-to-line also treat both sides symmetrically. Reject for drawn lines; acceptable only inside quality scoring of an already-anchored candidate.

### 3.5 Anchor selection, slope classes, quality scoring, extension
- **Anchors:** hull vertices (§3.1); first anchor = wave-origin extreme (spec §3.4) is the hull vertex at the leg origin — consistent.
- **Slope classes:** Volman's rule — upside-defining lines are horizontal/falling through lower highs, downside-defining horizontal/rising through higher lows (spec §3.4). Implement as a *filter* on hull-edge candidates, not as a fitter.
- **Quality score** (deterministic, computed once at birth and on each candidate-touch): touches within tol; max overshoot beyond line; span (bars); recency of last touch; and "coverage" = fraction of window lows within tol. Rank, then NMS (§5).
- **When to stop extending:** spec rule (3–17 bars past break, or window edge for flag lines); principled addition — stop extending when the line's *support hypothesis* is void (close beyond by ≥ tol → mark PIERCED, keep for retest detection per spec; re-fit only on the ≥2-new-aligned-swings re-anchor rule).

---

## 4. Topic 3 — Levels and zones (LEVEL_CARRIED, MINI_LEVEL, box edges)

Input: stream of confirmed swing extremes (price, t, side, weight). Task: merge nearby extremes into few zones; assign each a level price and a half-width.

### 4.1 Candidates compared
- **KDE + modes** (Parzen-style; online variant: Kristan et al. 2010, bounded-complexity GMM). Bandwidth h ≈ 0.25–0.5×ABR. Modes are smooth but *drift* as points arrive → freeze-on-draw needed. For ≤50 points, per-bar O(n·k) recompute is fine; the online-KDE machinery is overkill.
- **DBSCAN** (Ester et al. 1996): eps = tol, minPts = 2 — a "double top" is literally a 2-point cluster. **IncrementalDBSCAN** (Ester et al. 1998) proves insert-only updates give the *same* clustering as batch → perfect determinism and cheap. In 1-D this degenerates to sort + gap-merge — i.e., bucket-merge is the 1-D instance.
- **Mean-shift** (Cheng 1995): mode-seeking on a KDE — same answer class as KDE-modes; adds nothing over bucket-merge in 1-D.
- **Bucket-and-merge (recommended):** maintain sorted cluster list; new extreme merges into the nearest cluster within eps, else opens one; clusters merge transitively when centroids come within eps. Level price = weighted mean of member extremes. O(log n) insert + O(k) merge scan, trivially deterministic, ports cleanly.

### 4.2 Touch weighting, recency decay, zone width, round numbers
- **Weights:** w_i = 1 for each confirmed extreme; optional recency factor λ^{(t−t_i)} — keep λ = 1 unless TUNE shows old extremes over-weighted (spec wants edges on *clusters*, not last-touch).
- **Zone width from overshoot:** the DC law ⟨overshoot| ≈ θ (EVIDENCE, §2.3) says excursions past a turning point average the local θ. Proposed rule: half-width = q75 of observed penetration depths beyond the level (the T/F poke distribution) capped at ~0.5×ABR and floored at tol. Measure the poke-depth distribution on TUNE (spec reports pokes of ~1–3 pips).
- **Round-number snapping: do not do it.** Spec §2 forbids drawing round numbers; snapping levels to the 00/50 grid would fabricate agreement. Use distance-to-nearest-00/50 as a *feature* (magnet rules), never as a geometry constraint.

---

## 5. Topic 4 — Ranges, boxes, squeeze (BOX, RANGE_OPEN, CONTEXT_RANGE, SQUEEZE)

### 5.1 Volatility contraction / choppiness / efficiency — regime gates
- **Dreiss choppiness index** (1992, PRACTITIONER): CI = 100·log10(ΣATR_n / (maxHigh−minLow)) / log10(n). O(1) rolling sums. High → range; low → trend. No published validation; use as a *gate* (chop veto / box-supporting regime), not a drawer.
- **Kaufman efficiency ratio** (1995, PRACTITIONER): ER = |close_t − close_{t−n}| / Σ|Δclose|. O(1). Direction-free trendiness; complements CI on closes-only (blind to wicks).
- **Squeeze primitive (spec-grounded):** ≥2–3 consecutive bars with range ≤ 0.8·ABR inside narrowing walls — a pure per-bar predicate + gap-width tracker. O(1).

### 5.2 Change-point detection — the honest causal split
- **PELT** (Killick, Fearnhead, Eckley 2012): exact penalised-likelihood multiple-changepoint segmentation, expected O(n) — but **batch/offline**: adding observations can relocate earlier boundaries → retroactive redraws, violating causality. Legitimate roles: offline analysis of TUNE windows, or as a frozen-window helper. Must not drive live object birth.
- **BOCPD** (Adams & MacKay 2007): exact recursive posterior over run length; causal; Gaussian mean/variance-change model fits our bar-range/log-return streams; cost O(t) memory naively, prunable. Output = P(boundary now) — a *box death / regime-break* evidence signal, not geometry.
- **CUSUM** (Page 1954): O(1) cumulative deviation vs reference → detects level/range shifts cheaply; **FOCuS** (Romano et al. 2023) modernises it — online CUSUM-equivalent for all window sizes/change sizes at once, ~O(log n) per observation. Both suit a live "something changed" flag → feed `STAND_ASIDE` news-spike detection and box-death evidence.
- **Verdict:** changepoint machinery answers *when regime changed*, not *where edges sit*. Use FOCuS/CUSUM for the news-window gate and break confirmation; keep the constructive spec rules for geometry.

### 5.3 Darvas-style constructive rules
Darvas (1960, PRACTITIONER): box top = a high not exceeded for n bars; bottom = the low after the top is established; freeze; buy the upside break. This is essentially spec §3.1(b)+(c) — the spec already encodes it; cite as historical root, not as evidence.

### 5.4 Box lifecycle (birth/frozen edges/death)
Literature adds three things to the spec's constructive rules: (a) the DC overshoot prior on poke depth → tolerance and false-break flags for thin ranges; (b) CUSUM/BOCPD break-evidence channels; (c) edge placement on the *cluster* of extremes (§4.1 bucket-merge over the box's member highs/lows, wicks included, with the spec's isolated-spike exclusion). Birth lag = second touch on the breakout edge (spec); death = back-and-forth break rule + changepoint vote.

---

## 6. Topic 5 — Multi-scale

- **Scale-space** (Witkin 1983): smooth at increasing σ; extrema merge/die as σ grows; the scale-space tree gives a hierarchy of events by survival. Beautiful, but the Gaussian kernel is centred → non-causal on a stream. Causal surrogates: one-sided/exponential smoothing (introduces lag and lag-dependent extreme positions) or — better for us — the **DC amplitude hierarchy**.
- **Multiple-threshold DC:** run the §2.3 state machine at nested θ₁ < θ₂ (e.g., 0.8×ABR and 2.5×ABR). Cost O(#θ) per bar, memory O(#θ). The fine stream feeds MINI_LEVEL/squeeze micro-structure; the coarse stream feeds structural anchors. Caveat: θ₂-pivots are *approximately* a subset of θ₁-pivots, not exactly (unlike scale-space extrema) — measure the mismatch on TUNE; if it matters, derive the coarse pivot set by persistence-filtering the fine one (§5) instead of a second detector. Prefer the latter: **one detector + persistence pruning is strictly hierarchical and cannot disagree with itself.**
- **Which scale does a trader read on M5?** A principled choice exists: the visible window is 84 bars and the target density is ~3 structural objects (spec §5). Invert the DC count law: θ such that expected DC events per 84-bar window ≈ 4–8 → θ ≈ 0.08–0.12% ≈ 10–15 pips ≈ **2–3×ABR** on the 2012 feed — independently corroborated by the golden medians (box height ~15 pips ≈ 3×ABR; double-top tol ~2 pips ≈ 0.4×ABR). So the coarse scale falls out of `θ = k·ABR` with k ≈ 2–3, fixed by measurement, not tuning.

---

## 7. Topic 6 — Image-based learning: insight only (no models will be trained)

- **Jiang, Kelly & Xiu (2023, EVIDENCE):** CNN on rendered 5/20/60-day OHLC (+volume bars + moving-average overlay) images predicts return direction; a 2-D CNN on images beats a 1-D CNN on the same data numerically; learned patterns transfer across horizons and markets ("context-independent") and differ from textbook trend signals. **What carried information:** the spatial layout of the bar envelope and the MA overlay — i.e., *geometry*, and a smoothed-price reference — rather than any hand-coded oscillator. Caveat: predictive ≠ perceptual, and their equity daily/weekly domain ≠ our FX M5.
- **Cohen, Balch & Veloso (2020, EVIDENCE):** models trained on candlestick *images* recover algebraically-defined TA rules (Bollinger/RSI/MACD-labelled) — the rendering preserves rule-relevant information.
- **Lo, Mamaysky & Wang (2000, EVIDENCE):** kernel-regression smoothing + *extrema-sequence* templates operationalise head-and-shoulders, double tops, etc.; several patterns showed incremental information over 1962–96 US stocks. The academic bridge: patterns = relations among few extrema.
- **Implication for our grammar:** encode structures as spatial relations among few high-persistence extrema plus one smooth reference (EMA25) — which is precisely the spec's grammar. The JKX scale-transfer result supports expressing every threshold in ABR units so the same code reads any volatility regime.

---

## 8. The recommendation table

| Object | Algorithm family | Why | Params (units) | Risks / failure modes | Confirm lag |
|---|---|---|---|---|---|
| SWING/PIVOT | **DC state machine** (wick extremes; close-confirm variant on TUNE) + persistence pruning | Only family with published FX scaling laws; causal O(1); self-thinning in chop | θ = k·ABR, k≈2–3 structural / ≈0.8 micro (pips, %); persistence floor ≈0.5×ABR | Gap open fires instantly; θ too small → micro-pivot flood (our current bug) | θ-retrace; ~θ^1.9, ~5–15 bars at k≈2 |
| BOX | Bucket-merge clusters on member extremes for edges + spec freeze rules; CI/ER + CUSUM/FOCuS gates | Edges sit on dense clusters (spec §3.1); gates veto chop | eps = tol (~1–2 pips); minPts=2; CI window n≈14 bars | Spike wick distorts cluster → FALSE_EXT exclusion; frozen edges need logged re-anchors only | 2nd touch on breakout edge |
| RANGE_OPEN | Session running min/max (Asia 00:00–08:00 CET) + contraction check | Constructive, deterministic | session minutes CET; thin-range flag ≤10 pips | News at open inflates; DST handled by cet.py | Converts to BOX on close-out + follow-through or 08:00 |
| CONTEXT_RANGE | Same cluster machinery at coarse θ₂ on session/window extremes | One per window; dotted budget | θ₂ ≈ 2.5–3×ABR; width 20–40 pips | Overlaps box → dedupe by containment | Same as box |
| PATTERN_LINE | **Lower/upper incremental convex hull** over confirmed pivots → candidate support lines → max-touch-in-tol select | Hull vertices are the only possible least-touch anchors; parameter-free; O(1) amortised | tol; min touches 2; trigger span ~12 bars | Spike vertex → exclude flagged pivots; never re-fit on first pierce (spec) | 2nd anchor pivot confirm |
| CONTEXT_LINE | Hull/DC extremes at coarse scale over 3–8 h | Same machinery, longer span | 2–4 anchors, 3–8 h span | Drift across sessions — tie to session extreme | Coarse pivot confirm (~10–30 bars) |
| LEVEL_CARRIED | Role-reversal of broken edge; dome-zone span; ceiling-test congestion | Spec-defined sources; cluster zone width from poke-depth quantile | half-width = q75(poke depth), cap ~0.5×ABR | Consumed-after-touch bookkeeping must be exact | Broken-edge event (immediate) |
| MINI_LEVEL | Micro-θ DC extremes clustered at trigger side | Short horizontals 2–8 bars | θ₁ ≈ 0.8×ABR; span 2–8 bars | Micro-pivot noise — persistence floor applies | Micro-θ retrace (~1–5 bars) |
| SQUEEZE | Bar-range predicate (≤0.8·ABR, ≥2–3 bars) + wall-gap narrowing tracker | Spec-measurable; O(1) | bar range fraction; gap narrowing fraction 0.6 | Flat Asia produces many — require two *named* walls | Last qualifying bar close |
| BRACKET (M/W/SHS) | Pattern match on confirmed-pivot sequence: equal-extreme pair within tol, 4–28 bars apart; middle-section level → MINI_LEVEL | Operates on stable swing objects, not raw bars | equality tol ~2–4 pips; separation 4–28 bars | Persistence too low → bracket noise | 2nd top's confirm lag |
| LABEL_TF | Edge-poke event rule (spec §3.2): excursion past edge + close back inside | Deterministic bar predicate | poke 1–3 pips; relabel ≤3 bars, ≥½ height | Needs frozen edges to be meaningful | 1–3 bars (T→F relabel) |
| (gate) STAND_ASIDE | CI/ER chop gates + FOCuS/CUSUM change alarms + news windows | Prevents drawing inside unreadable tape | CI n≈14; ER n≈10; news windows CET | Thresholds need TUNE calibration | n/a |

---

## 9. Sparsity and salience — selecting the ~3 that matter

A trader draws ~3 objects; our failure today is over-production. The literature offers four combinable mechanisms:

1. **Topological persistence / prominence (recommended core ranker).** For a function on a line, 0-D persistent homology pairs each extremum with the saddle where its basin merges; an extremum's persistence = its height above that merge level — for a swing high, exactly its *topographic prominence* (height above the highest valley separating it from a higher high). Formal basis: Edelsbrunner, Letscher, Zomorodian 2002; financial TDA precedent exists (Gidea & Katz 2018 — though they analyse point-cloud loops, not scalar extrema: our application is a proposal, not their result). **Incremental computation:** over the alternating pivot sequence, maintain a merge tree via stack/union-find — each confirmed pivot updates in amortised O(α(n)); pairing decisions are deterministic. **Causality, honestly:** a pivot's prominence *so far* is computable online and monotone non-decreasing until a dominating swing appears — its *final* persistence is known only once dominated. That is fine for a ranker: use prominence-so-far with a floor (~0.5×ABR) to kill micro-pivots the moment they confirm.
2. **PIP importance** (§2.4) — a near-equivalent chord-distance score; use as a cross-check on the persistence ranking, not a second system.
3. **MDL / penalised fit.** PELT's penalised likelihood is the formal "few objects" principle: each object must pay for its description length in touches/residual explained. Practical form: score = explained touches − penalty per object; admit only positive scores. Deterministic, tunable to the golden count distribution.
4. **Non-maximum suppression + hysteresis.** Rank all candidate objects; suppress any whose (type-family, price, time) footprint overlaps a higher-ranked one (IoU-style on the 84×price canvas — cheap on ~10 candidates). Then **rank hysteresis**: an incumbent object is displaced only if a challenger exceeds its score by margin m — prevents boundary flicker at rank 5/6.

Budget enforcement stays a *consequence* of scoring+NMS, not ad-hoc cooldowns (the D5 finding: current caps have no provenance).

---

## 10. Stability — non-jittering geometry

Jitter sources and fixes, matched to methods:
- **Micro-pivot noise →** θ ≥ ~2×ABR + persistence floor; pivots become rare, discrete events.
- **Line refits →** hull-anchored candidate lines, evaluated once; **freeze on ≥2-touch confirm**; move only via the logged re-anchor rule (≥2 new extremes aligned within tol). Never least-squares-refit a drawn line.
- **Cluster centroid drift →** freeze the level price at draw time; update membership internally, geometry externally only on re-anchor.
- **Boundary flicker (ranks, regime flags) →** hysteresis everywhere: enter-threshold > exit-threshold; minimum dwell bars per state; EMA-slope hysteresis already in spec.
- **Determinism →** fixed candidate ordering (price, then birth bar); no RNG anywhere (RANSAC excluded for this reason); all incremental structures used here (monotone-chain hull, bucket-merge, union-find merge tree, DC state machine) are deterministic by construction.
- Freeze discipline in one sentence: **detection is continuous; geometry is committed once and revised only by named events** (re-anchor, tighten, break, consume) — matching spec §3.2 and the Lead's edge-stability gate (≈0 unlogged moves per 100 bars).

---

## 11. Limitations

- **[SNIPPET-ONLY, NOT FETCHED]:** Dreiss (1992) choppiness index — verified only via secondary citations (Futures Magazine Oct 1993 summary; vendor write-ups), not the original CTCR article. Kaufman (1995), Williams (2004), Wilder (1978), Darvas (1960) — publisher/catalogue pages verified; formulas are industry-standard but I did not fetch the books (no book downloads allowed).
- **Tsang WP050-10** verified as a listed CCFEA working paper (bracil.net); content not fetched (PDF not opened).
- **DC on bars is our adaptation:** the cited DC work is tick-based (2003–2007 EBS). Applying θ to M5 bar extremes and close-confirming is a modification; the θ^{1.9} lag law may not transfer exactly — the exponent check is a listed TUNE measurement.
- **JKX/Cohen evidence is equities and synthetic labels,** not FX M5, and shows *predictive* information in images — it does not prove which *drawn objects* a trader needs; used here only to justify the extrema-geometry grammar.
- **Persistence-as-salience** is a principled math object with financial-TDA precedent, but no published test that prominence ranking matches trader-drawn swing selection — our golden set is the test.
- **Overshoot→zone-width** uses the DC overshoot law as a prior; the actual width must come from the TUNE poke-depth distribution.
- **Incremental hull** gives the anchor *set*; the proof it reproduces Volman's lines is empirical (golden recall), not theoretical.
- Scaling-law numbers quoted (θ^{1.88} lag, overshoot ≈ θ, coastline 6.4%/day at θ=0.05%) come from 2003–2007 tick data and are used as *priors* for parameter magnitudes, re-measured on our feed.
- No scratch files created under `docs/`; deliverable only.

---

## 12. What this means for our engine

Prioritised, in dependency order, with the measurement that fixes each parameter instead of guessing:

1. **SWING/PIVOT — replace the current detector with a DC state machine, two nested thresholds.** Keep `swing.confirm_pullback` but re-derive it: θ₁ = k₁·ABR ≈ 0.8×ABR (~4 pips — current value is *right-sized for micro structure but wrong for anchors*), θ₂ = k₂·ABR ≈ 2–3×ABR (~10–15 pips) for structural pivots. Wick-tracked extremes; confirm on close-vs-extreme retrace (A/B on TUNE). Expected lag ~5–15 bars at k₂ — log it as `t_birth` vs `t_ext`. **Measurement:** on TUNE golden panels, (a) leg sizes between author-anchored pivots → set k₂ so ~90% of golden swings survive and micro-pivots die; (b) verify inter-DC count vs θ^{1.9} on our feed; (c) tick-vs-close retrace effect on lag.
2. **Salience — implement prominence ranking on the confirmed-pivot stream** (merge tree, union-find, O(α) amortised). Floor at ~0.5×ABR. **Measurement:** correlation of prominence rank vs "is this pivot a golden anchor" on TUNE; pick floor at precision-recall knee. This one mechanism should delete most of the D5 ad-hoc caps.
3. **PATTERN_LINE / CONTEXT_LINE — incremental convex hull anchors.** Maintain lower-hull of confirmed swing lows and upper-hull of highs (monotone-chain append; rebuild O(n) on window eviction). Candidate lines = hull edges + tolerance-feasible non-adjacent pairs; select max touches-in-tol; freeze; re-anchor only per spec rule. **Measurement:** hull-vertex recall of golden line anchors on TUNE (if < ~90%, hull input needs the FALSE_EXT exclusion); slope-class match rate.
4. **BOX / RANGE_OPEN / CONTEXT_RANGE — keep spec constructive rules; swap edge placement to bucket-merge clusters** (eps = tol = max(1 pip, 0.25·ABR); minPts = 2), edges at cluster extremes with isolated-spike exclusion. **Measurement:** TUNE distribution of (a) double-top separation tolerances (sets `double_top_tol`), (b) box-edge touch counts (sets minPts / breakout-edge 2-touch gate), (c) box height/width vs the 6–34 pip / 9–100 bar envelope.
5. **LEVEL_CARRIED / MINI_LEVEL — zone width from measured overshoot:** half-width = q75 of poke-depth-past-level on TUNE, floor tol, cap ~0.5×ABR; consume-after-touch unchanged. **Measurement:** the poke-depth distribution itself; compare to DC-overshoot prior (≈θ₁).
6. **SQUEEZE — keep the bar-range predicate;** add optional CUSUM/FOCuS "range contracted" channel as evidence, not geometry. **Measurement:** golden squeeze bars' range/ABR ratio (sets 0.8 threshold check) and gap-narrowing fractions.
7. **BRACKET — pattern-match on the *pruned* pivot sequence only** (equal tops within 2–4 pips, 4–28 bars apart; SHS as three-extreme template à la Lo-Mamaysky-Wang). **Measurement:** golden M/W separation and equality-tolerance distributions.
8. **LABEL_TF — unchanged spec rule;** depends on frozen edges from (3)/(4). **Measurement:** T/F agreement on matched boxes (gate ≥0.60).
9. **Regime gates for STAND_ASIDE:** CI(n≈14) and ER(n≈10) as chop vetoes + FOCuS alarm for the 14:30/16:00 CET windows — all O(1)/O(log n), all deterministic. **Measurement:** CI/ER distribution inside golden "no-object" panels vs drawn panels; set veto at the separating percentile — no guessing.
10. **Causality discipline:** every candidate object carries `confirm_lag_bars` in telemetry; the prefix-invariance tests (D7) then verify object-level causality empirically, not just by construction.

**Single biggest expected win:** the DC+persistence pivot core directly attacks both logged failures — micro-pivot over-production (θ amplitude filter + prominence floor) and edge wobble (pivot rarity makes hull anchors stable; freeze discipline keeps them still).
