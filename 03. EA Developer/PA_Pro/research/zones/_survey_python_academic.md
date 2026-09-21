# Zone generators — Python/quant methods and academic literature

- Task: T-PAPRO-ZONE-1 (program PA-PRO), research only.
- Date of survey: 2026-09-20.
- Scope: support/resistance (S/R) **zone** generators for a preregistered zone-physics
  bake-off on EURUSD M5/M15 with H1/H4 context, plus the academic evidence on S/R and
  round numbers.
- Evidence convention: `[fetched]` = content retrieved with the fetch tool;
  `[fetched — search-extracted]` = page text retrieved through the search tool's
  page-content extraction (raw page not opened), so numbers are quoted from that
  extraction; `[NOT FETCHED — cite only]` = citation only, no content read.
- This file writes no code and proposes no trading. All ATR/pip figures are
  **ASSUMPTION** placeholders to be measured on the actual MT5 history before use.

---

# Part A — Python / quant methods

## A1. ZigZag pivots (PyPI `zigzag`)

1. **Name / maintainer:** `zigzag` 0.3.2 (released 2022-08-06), author "generativist"
   / `jbn` (johnbnelson); repo `jbn/ZigZag`. Latest release 0.3.2; Python >= 3.8.
2. **Category:** Python library (swing-point / pivot extraction).
3. **Source URL:** `https://pypi.org/project/zigzag/` [fetched];
   `https://github.com/jbn/ZigZag/blob/main/zigzag/core.pyx` [fetched].
4. **License:** BSD-3-Clause (PyPI: "License: BSD License (BSD-3-Clause)", classifier
   `OSI Approved :: BSD License`; GitHub license badge BSD-3).
5. **Output:** `peak_valley_pivots(X, up_thresh, down_thresh)` returns an int array
   the same length as `X`, with `+1` at peaks, `-1` at valleys, `0` elsewhere.
   Also `pivots_to_modes`, `compute_segment_returns`, `max_drawdown`. It returns
   **points**, not zones.
6. **Algorithm:** A relative-change ZigZag. It first determines an initial pivot by
   scanning the series for the first move that exceeds `up_thresh` (upward) or
   `down_thresh` (downward, negative). It then tracks the current trend; while in a
   downtrend it keeps the running minimum, and when price rises by `up_thresh`
   relative to that minimum it finalizes the minimum as a valley and flips to an
   uptrend (mirror logic for peaks). Thresholds are **relative** (fractional price
   change), not absolute. The last annotated pivot is provisional: only the previous
   pivot is final once a threshold reversal has occurred. The first and last elements
   are always annotated as a pivot even if the segment is too small (documented
   trade-off), unless `limit_to_finalized_segments=True` is used.
7. **Repaint?** Partly. The library exposes a causal mode
   (`peak_valley_pivots_detailed(..., limit_to_finalized_segments=True,
   use_eager_switching_for_non_final=False)`), which `peak_valley_pivots` uses.
   But the **initial pivot** determination reads forward through the whole array, and
   the last element can still be labeled as a tentative pivot. Treated naively, the
   most recent pivot label can change until the threshold reversal occurs.
8. **How to make it causal:** Feed only bars closed at or before `t`; discard/ignore
   the last annotated pivot (it is the "forming" one); use only pivots that have been
   superseded by a later threshold reversal. Do not re-run the initial-pivot scan on
   an ever-growing array and reuse old labels without re-verification.
9. **Parameters + ATR scaling:** `up_thresh`, `down_thresh` (relative fractions;
   `down_thresh` must be negative). Convert an ATR budget into relative terms:
   `threshold ≈ k * ATR(14, TF) / price`. For EURUSD near 1.10, 1 pip ≈ 0.0000909
   relative. Typical M5 ATR(14) is on the order of 1–2 pips, H1 ~5–9 pips, H4 ~12–25
   pips (**ASSUMPTION — measure on the actual history**). Suggested sweeps:
   `k ∈ {0.5, 1.0, 1.5}`; consider asymmetric up/down thresholds only if the
   preregistration allows it.
10. **Zone width logic:** None — output is points. Zone width must be added
    externally, e.g. ±0.25 × ATR around the pivot price, or ±half the median
    pivot-to-pivot amplitude.
11. **Strength / freshness logic:** None. Can be added from pivot age (bars since
    confirmation) and pivot-to-pivot amplitude; no volume/volume-at-price input.
12. **Typical number of zones:** A threshold of ~1 × ATR(H1) on H1 gives roughly
    2–6 pivots per 100 bars; after de-duplication expect ~3–8 levels in a 20-day H1
    window. More pivots on M5 with the same ATR multiple.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Good as the **swing extractor** for
    H1/H4 context pivots (few, meaningful turning points) and as the raw input to a
    clustering step on M5/M15. Not a zone generator by itself.
14. **Confidence:** High for existence/licence/behaviour (source read); Medium for
    causal use (the initial-pivot scan and provisional last pivot must be handled).

## A2. Classical pivot points (and the `pivotpoints` PyPI question)

1. **Name / maintainer:** Several implementations, no single canonical Python
   package: `stock-indicators` (Dave Skender / maintainer Dong-Geon Lee),
   `freqtrade/technical` (Freqtrade project), `backtrader` (`PivotPoint`,
   `FibonacciPivotPoint`, `DemarkPivotPoint` — mementum). The PyPI project name
   **`pivotpoints` does not exist**: `https://pypi.org/pypi/pivotpoints/json`
   returned HTTP 404 on 2026-09-20 [fetched]. Do not plan a dependency on it.
2. **Category:** Python library (classic floor-trader S/R levels) / quant method.
3. **Source URL:** `https://python.stockindicators.dev/indicators/PivotPoints/`
   [fetched — search-extracted];
   `https://python.stockindicators.dev/indicators/RollingPivots/`
   [fetched — search-extracted]; `https://pypi.org/pypi/stock-indicators/json`
   [fetched]; `https://github.com/freqtrade/technical/blob/main/technical/pivots_points.py`
   [fetched — search-extracted]; `https://api.github.com/repos/freqtrade/technical`
   [fetched]; `https://api.github.com/repos/mementum/backtrader` [fetched].
4. **License:** `stock-indicators` Apache-2.0 (PyPI license field "Apache 2.0");
   `freqtrade/technical` GPL-3.0 (GitHub API license `gpl-3.0`);
   `backtrader` GPL-3.0 (GitHub API license `gpl-3.0`). GPL-3 code is a
   distribution-copyleft risk for the host package; prefer permissive
   implementations or implement the 4-line formulas in-repo.
5. **Output:** `PP` plus `R1..R3`, `S1..S3` per period; variants Standard (floor),
   Woodie, Camarilla, Demark, Fibonacci. `stock-indicators` returns a full
   time-series aligned to the input quotes with `None` during warmup;
   `RollingPivots` uses a `window_periods` + `offset_periods` rolling window.
6. **Algorithm:** Aggregate the **previous** period's high, low and close:
   `PP = (H+L+C)/3`, `R1 = 2*PP − L`, `S1 = 2*PP − H`, `R2 = PP + (H − L)`,
   `S2 = PP − (H − L)`, `R3`/`S3` extend by the same range; Fibonacci variant scales
   (H−L) by 0.382/0.618/1.000. The freqtrade version computes rolling means of
   high/low/typical price over `timeperiod`, then derives levels recursively.
7. **Repaint?** No, under the standard definition: levels for period `t` are computed
   from the completed prior period and are frozen for the whole period. Confirmation
   lag is therefore the period boundary (daily pivots exist at the start of the day,
   H1 pivots at the top of the hour). Intraday "rolling" variants behave differently:
   the level changes as the window slides, so for those the confirmation lag is
   `window_periods + offset_periods − 1` bars (documented for `RollingPivots`).
8. **How to make it causal:** Use the period-boundary definition on closed bars
   only; or use `RollingPivots` with `offset_periods >= 1` so the window ends before
   the bar being evaluated.
9. **Parameters + ATR scaling:** Standard: window = prior day/week/hour; variants
   above. No ATR inside the formula — levels are range-scaled. If a zone instead of a
   line is needed, use `±0.25 × ATR(14, TF)`; `R2−R1 = H−L` is itself an
   ATR-like band.
10. **Zone width logic:** None (lines); zone = manually widening each level, or use
    the band between adjacent levels (e.g. PP–R1) as the zone.
11. **Strength / freshness logic:** None. Levels are recalculated every period and
    are "fresh" for one period by construction; confluence with other generators is
    the natural strength proxy.
12. **Typical number of zones:** 1 PP + 6 levels per period (standard); with
    `stock-indicators` day-based data on EURUSD that is 7 lines per day.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Good as **context/rails** (H1 and
    H4 pivots as H1/H4-level lines the M5 engine can test), weak as the primary zone
    generator because it is line-based and mechanical.
14. **Confidence:** High on formulas/output (docs fetched); High that `pivotpoints`
    is not a PyPI project (404 JSON API); Medium on which implementation to vendor
    (licence trade-offs).

## A3. KDE of swing-point prices — `scipy.stats.gaussian_kde`

1. **Name / maintainer:** `scipy.stats.gaussian_kde`, SciPy Developers.
2. **Category:** Python library (density estimation) / quant method.
3. **Source URL:** `https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html`
   [fetched]; `https://api.github.com/repos/scipy/scipy` [fetched].
4. **License:** BSD-3-Clause (GitHub API license `bsd-3-clause`; SciPy docs
   copyright "The SciPy community").
5. **Output:** A KDE object; `evaluate`/`pdf` returns density values at arbitrary
   price points. Zones = local maxima of the density over the price axis (peaks) or
   regions whose density exceeds a chosen quantile. Points in, density curve out.
6. **Algorithm:** Place a Gaussian kernel at every swing price, sum the kernels, and
   scale by `1/(n·h)`. The result is a smooth 1-D price-density. Local maxima are the
   price levels where swings historically clustered most; a density threshold turns
   the peak's neighbourhood into a zone. Weights (`weights=`) allow recency or
   volume-at-price weighting of the swing samples. SciPy computes the bandwidth
   factor automatically (Scott by default: `n**(-1/(d+4))`), and documents that the
   estimate works best for unimodal data — bimodal/multimodal densities tend to be
   **oversmoothed**.
7. **Repaint?** Not applicable in the usual sense: the density is computed from the
   sample of confirmed swing prices. No future bars are used **provided** the swing
   sample contains only confirmed pivots (see A1/A6/A9 confirmation lags). If the
   swing extractor is non-causal, the KDE inherits the leak.
8. **How to make it causal:** Build the swing sample from pivots confirmed at least
   `L` bars ago; recompute the KDE on each closed bar using only the trailing window
   (e.g. last `N` days). Never fit bandwidth on the test window (see Notes).
9. **Parameters + ATR scaling:** `bw_method` = `'scott'` (default), `'silverman'`,
   a scalar factor, or a callable. Scott's factor from `n` points is
   `n**(-1/5)`, which is **not** ATR-aware; for price zones, pass a callable that
   returns `bandwidth = c * ATR(14, TF)` because SciPy's `factor` multiplies the
   data standard deviation. Practical sweep `c ∈ {0.25, 0.5, 1.0}` on H1 ATR.
   `weights=` optional (recommend recency weights with a half-life of 1–2 sessions
   on M5, ~5 days on H1).
10. **Zone width logic:** Natural: the density peak's width. Practically, define the
    zone as the contiguous price range around a peak where density ≥
    `q × peak_density` (`q` = 0.5–0.7), or simply `±0.25 × ATR` around the peak
    centre. The bandwidth directly sets the floor on zone width.
11. **Strength / freshness logic:** Peak height (probability mass) is a natural
    strength proxy; recency enters only through `weights=` or by window length.
    Nothing in the method tracks time-since-touch unless added.
12. **Typical number of zones:** Depends on the bandwidth; with `c ≈ 0.5 × ATR(H1)`
    on a 20-day H1 swing sample expect ~4–10 peaks; on M5 with a 2–3 session window
    expect ~3–8.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Good — this is the most direct
    "price memory" generator: swing prices in, density peaks out. It naturally fuses
    H1/H4 context (their swings are rarer and heavier) with M5/M15 swings if the
    sample pools TFs with weights.
14. **Confidence:** High on API/licence (docs fetched); Medium on zone quality
    (bandwidth choice dominates; SciPy documents oversmoothing of multimodal data).

## A4. KDE alternative — `sklearn.neighbors.KernelDensity`

1. **Name / maintainer:** scikit-learn developers.
2. **Category:** Python library (density estimation) / quant method.
3. **Source URL:** `https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KernelDensity.html`
   [fetched]; `https://api.github.com/repos/scikit-learn/scikit-learn` [fetched].
4. **License:** BSD-3-Clause (GitHub API license `bsd-3-clause`).
5. **Output:** Fitted estimator; `score_samples(X)` returns **log** density on a price
   grid. Same downstream use as A3 (peaks → zones).
6. **Algorithm:** Sum of kernels centred on the samples, evaluated via a KD-tree or
   BallTree; kernels available: `gaussian`, `tophat`, `epanechnikov`, `exponential`,
   `linear`, `cosine`. Because the tree-based evaluation is lazy, it scales better
   when scoring a dense grid or many windows, at the cost of an extra dependency
   iteration path. `sample_weight=` is supported in `fit` (equivalent of A3 weights).
7. **Repaint?** Not applicable / no future bars if the swing sample is causal. Same
   caveat as A3.
8. **How to make it causal:** Same as A3: trailing swing sample, closed bars only.
9. **Parameters + ATR scaling:** `bandwidth` is in **data units** (default `1.0` —
   dangerous on EURUSD: an absolute bandwidth of 1.0 is wider than the whole price!).
   Set `bandwidth = c × ATR(14, TF)` directly, or pass `'scott'`/`'silverman'`.
   `kernel='gaussian'` for smooth peaks, `'tophat'` when hard zone edges are wanted.
   Sweep `c ∈ {0.25, 0.5, 1.0}`.
10. **Zone width logic:** As A3; `tophat`/`epanechnikov` kernels produce
    finite-support peaks with a natural half-width ≈ bandwidth.
11. **Strength / freshness logic:** As A3 (`sample_weight` for recency or tick
    volume).
12. **Typical number of zones:** As A3.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Same as A3; slightly better when
    the grid is dense or when a non-Gaussian kernel is desired.
14. **Confidence:** High on API/licence (docs fetched); Medium on zone quality
    (same bandwidth issue). Choose A3 or A4, not both, unless the bake-off wants the
    kernel family as an axis.

## A5. Market profile / value area — PyPI `marketprofile`

1. **Name / maintainer:** `MarketProfile` 0.2.0 (released 2020-01-19), Brad Folkens
   (`bfolkens`), repo `bfolkens/py-market-profile`. Package is stale (no release
   since 2020).
2. **Category:** Python library (market profile / volume profile / TPO) / quant
   method.
3. **Source URL:** `https://pypi.org/pypi/marketprofile/json` [fetched];
   `https://raw.githubusercontent.com/bfolkens/py-market-profile/master/src/market_profile/__init__.py`
   [fetched]; `https://raw.githubusercontent.com/bfolkens/py-market-profile/master/LICENSE`
   [fetched].
4. **License:** BSD (LICENSE file is the 3-clause BSD text, "Copyright (c) 2017,
   Brad Folkens"; PyPI classifier "BSD License").
5. **Output:** Per slice (time window): `poc_price`, `value_area` = `(VAL, VAH)` at
   `value_area_pct` (default 70%), `balanced_target`, `profile_range`,
   `low_value_nodes`, `high_value_nodes`, `open_range`, `initial_balance`; the
   underlying `profile` is a pandas Series of volume-per-row or count-per-row.
6. **Algorithm:** Rounds each bar's **Close** to a price row (`row_size =
   tick_size × prices_per_row`, default tick 0.05), then aggregates by row: `vol`
   mode sums `Volume`, `tpo` mode counts closes. POC = row with maximum aggregate.
   The value area is then grown outward from the POC row, one neighbouring row at a
   time, always adding the adjacent row with the larger aggregate, until
   `value_area_pct` (70%) of the total is covered; VAL and VAH are the extremes of
   that set. LVN/HVN are local minima/maxima of the row aggregates found with
   `scipy.signal.argrelextrema`.
7. **Repaint?** Not inherently: POC/VA are computed from the bars inside the chosen
   slice. They **change when the slice rolls** (a new session adds rows), so the
   value area is only final at slice close. No future bars if the slice ends at `t`.
8. **How to make it causal:** Use slice = previous completed session(s) (or a rolling
   window ending at bar `t−1`); recompute at each closed bar; expose POC/VAH/VAL to
   the strategy only for the next bar onward. For intraday context, compute an H1/H4
   profile over the trailing 5–20 sessions.
9. **Parameters + ATR scaling:** `tick_size` / `row_size`: row size should scale with
   volatility — a good default is `row_size ≈ 0.1 × ATR(14, TF)` (on M5 EURUSD that
   is roughly 0.1–0.2 pip; a 1-pip row is a practical coarse alternative);
   `value_area_pct = 0.70` (Steidlmayer convention); `mode='tpo'` to avoid fake
   volume (see below); `open_range_size=10 min`, `initial_balance_delta=1 h`.
10. **Zone width logic:** The value area **is** a zone: `[VAL, VAH]`, typically
    1–2 × ATR(H1) wide on a daily EURUSD window. POC is a line inside it.
11. **Strength / freshness logic:** POC volume, value-area width vs ATR, and
    whether the current price is inside/outside the VA. Freshness = age of the
    session (a prior-day VA is fresh for the next day only).
12. **Typical number of zones:** 1 VA + 1 POC per session; with a 5–10 session
    context window, 5–10 zones (many overlapping; de-duplication needed).
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Good as a **slower context**
    generator (prior H1/H4/daily value areas as H1/H4 zones). Note MT5 FX "volume"
    is **tick volume**, not real traded volume, and the library's `vol` mode just
    sums it; `mode='tpo'` is the safer default for FX. The library rounds only
    **Close**, so it does not distribute the candle's range — a real TPO/volume
    profile distributes each candle's activity across its high-low range.
14. **Confidence:** High on existence/licence/API (source and LICENSE read);
    Medium on zone quality for FX (Close-only rows, stale package, tick volume).

## A6. Williams Fractals

1. **Name / maintainer:** Original concept Larry Williams ("Trading Chaos"); Python
   implementation `stock-indicators` (Dave Skender et al.); native MT5
   `iFractals` uses the same 5-bar template.
2. **Category:** Quant method / Python library / MT5 indicator.
3. **Source URL:** `https://python.stockindicators.dev/indicators/Fractal/`
   [fetched]; `https://pypi.org/pypi/stock-indicators/json` [fetched].
4. **License:** `stock-indicators` Apache-2.0. (MT5 `iFractals` is platform-native,
   no separate licence.)
5. **Output:** `get_fractal(quotes, window_span=2, end_type=HIGH_LOW)` returns, for
   each bar, an optional `fractal_bear` (a **high** pivot) and `fractal_bull` (a
   **low** pivot) at the centre bar. Points only.
6. **Algorithm:** A bar is a fractal high if its high exceeds the highs of the `S`
   bars on each side (`S=2` ⇒ 5-bar pattern); a fractal low is the mirror with lows.
   `end_type` can use close instead of high/low. The docs state the total window is
   `2S+1`. No clustering, no zones — just the central extrema.
7. **Repaint?** Yes by construction. The docs carry an explicit warning: "this price
   pattern uses future bars and will never identify a fractal in the last `S` periods
   of quotes. Fractals are retroactively identified." Confirmation lag = `S` bars
   after the centre bar (`S=2` default).
8. **How to make it causal:** Only accept a fractal at centre bar `i` once bar
   `i+S` has closed. In a loop, emit the fractal with an `S`-bar delay (or store it
   with its confirmation timestamp). Never read a fractal whose right window is not
   complete.
9. **Parameters + ATR scaling:** `window_span`/`left_span,right_span` (`S`, default 2,
   minimum 2). `S=2` on M5 is noisy (many fractals); `S=3` or `S=4` on M15/H1
   reduces count. No ATR inside; after extraction, merge fractals within
   `0.5 × ATR(14, TF)` and/or widen the zone by `±0.25 × ATR`.
10. **Zone width logic:** None — needs external clustering/width. Common choice:
    zone = `[price − 0.25×ATR, price + 0.25×ATR]`, or the min/max of merged
    fractals in a cluster.
11. **Strength / freshness logic:** None native. Touch count (number of fractals
    merged), recency (bars since confirmation), and fractal rank (S) are all
    external.
12. **Typical number of zones:** Raw `S=2` fractals: several per hour on M5 — far too
    many. After merging within 0.5 × ATR(H1) on a 20-day window: ~5–12 levels.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Medium as a raw feature; good as
    a cheap swing detector for H1/H4 context (with S=3–4), then clustered. Needs the
    explicit confirmation delay, otherwise it leaks future bars.
14. **Confidence:** High on algorithm/repaint behaviour (official docs fetched);
    Medium as a standalone zone generator (too noisy; clustering required).

## A7. Unsupervised 1-D clustering of swing prices (k-means / mean-shift / natural breaks / gap statistic)

1. **Name / maintainer:** `sklearn.cluster.KMeans`, `sklearn.cluster.MeanShift`
   (scikit-learn devs); `jenkspy` (mthh, 240 stars, Fisher-Jenks natural breaks);
   `kneed` (used in the TDS tutorial for elbow detection — package not independently
   verified here, **ASSUMPTION**); gap statistic (Tibshirani, Walther & Hastie 2001
   method; no canonical maintained package verified).
2. **Category:** Quant methods / Python libraries.
3. **Source URL:** `https://api.github.com/repos/mthh/jenkspy` [fetched];
   sklearn API pages are covered by A4's fetch; the clustering use is documented in
   the practitioner sources of A8 [fetched — search-extracted]. Gap statistic:
   `[NOT FETCHED — cite only]` (Tibshirani et al. 2001, JRSS-B).
4. **License:** scikit-learn BSD-3-Clause; `jenkspy` MIT (GitHub API license `mit`);
   `kneed` not verified (**ASSUMPTION**: MIT per its repo).
5. **Output:**
   - KMeans: `k` centroids + per-sample labels → zone centres; zone extent from
     cluster min/max or `±0.25 × ATR`.
   - MeanShift: cluster centres without specifying `k`; bandwidth from
     `estimate_bandwidth` or a quantile.
   - jenkspy: `jenks_breaks(values, n_classes)` → class boundaries (natural breaks)
     → zones are the intervals.
   - Gap statistic: estimate of the best `k` by comparing within-cluster dispersion
     to a null reference.
6. **Algorithm:** KMeans alternates assigning each swing price to the nearest of `k`
   centroids on the 1-D price axis and recomputing centroids as means, minimising
   within-cluster variance; on 1-D prices this segments the price axis into `k`
   contiguous-ish bands (initialisation matters). MeanShift moves each point toward
   the mode of the density within a bandwidth until convergence, so it finds dense
   price levels without choosing `k`. Fisher-Jenks (jenkspy) finds `k−1` breakpoints
   that minimise within-class variance exactly via dynamic programming — a natural
   fit for 1-D price histograms. The gap statistic compares the observed
   within-cluster dispersion curve with that of uniform reference data to pick `k`.
7. **Repaint?** No future bars if the cluster model is fitted only on confirmed swing
   pivots from the trailing window. Instability instead of repaint: cluster
   assignments/centroids can jump when new pivots arrive (especially KMeans with
   random init), making the zone set non-stationary bar to bar.
8. **How to make it causal:** Fit on pivots confirmed before the current bar; fix
   `random_state` and/or use `n_init` large; prefer deterministic jenkspy/MS where
   possible; smooth zone turnover with a "zone must exist for ≥ m bars before use"
   rule.
9. **Parameters + ATR scaling:** KMeans `n_clusters` (sweep 2–12; use elbow/silhouette
   or the gap statistic, but note elbow unreliability below), `n_init=10+`,
   `random_state` fixed. MeanShift `bandwidth ≈ c × ATR(14, TF)` (`c ∈ {0.5, 1.0}`)
   or `estimate_bandwidth(quantile=0.2)`. jenkspy `n_classes` (sweep 3–12).
10. **Zone width logic:** Cluster extent (min–max of member prices) is the most
    natural; shrink to `±0.25 × ATR` around the centroid if the cluster is too wide
    (a cluster spanning several ATRs is a range, not a zone). Gap between adjacent
    cluster min/max is exactly what A8's tutorials call the boundary.
11. **Strength / freshness logic:** Member count (touches) per cluster; mean recency
    of members; ATR-normalised cluster width. KMeans itself gives no uncertainty.
12. **Typical number of zones:** `k`-dependent; with `k = 6–10` on a 20-day H1 swing
    set expect 6–10 zones (some too wide to be useful).
13. **Fit for EURUSD M5/M15 with H1/H4 context:** The clustering step is
    TF-agnostic and can merge M5/M15/H1/H4 swings into one pool (with weights).
    Recommend mean-shift or natural breaks over KMeans (see A8 negative evidence).
14. **Confidence:** High on licences/API for sklearn and jenkspy; Medium-Low on zone
    quality: the published walkthroughs show KMeans "not a great solution" for
    high-timeframe S/R (A8), and `k` selection is the known weak point.

## A8. Practitioner S/R-clustering pipelines (blogs / GitHub walkthroughs)

1. **Name / maintainer:** (i) "Calculating Support & Resistance in Python using
   K-Means Clustering", Zαck West, alpharithms.com (2023-03-29);
   (ii) "Using K-means Clustering to Create Support and Resistance", Victor Sim,
   Towards Data Science (2020-09-06);
   (iii) "Picking Support and Resistance Levels with K-Means", lambdalearner.com;
   (iv) "I Tried Building an Automatic Support & Resistance Detector in Python",
   Ayushman Pranav, Medium/DataDrivenInvestor (2026-05-03);
   (v) `boysugi20/python-stock-support-resistance` (GitHub).
2. **Category:** Practitioner algorithms / tutorials (not peer-reviewed).
3. **Source URL:** (i) `https://www.alpharithms.com/calculating-support-resistance-in-python-using-k-means-clustering-101517/`
   [fetched — search-extracted]; (ii) `https://towardsdatascience.com/using-k-means-clustering-to-create-support-and-resistance-b13fdeeba12/`
   [fetched — search-extracted]; (iii) `https://lambdalearner.com/picking-support-and-resistance-levels-with-k-means/`
   [fetched — search-extracted]; (iv) `https://medium.datadriveninvestor.com/i-tried-building-an-automatic-support-resistance-detector-in-python-heres-what-actually-worked-524686e3f667`
   [fetched — search-extracted]; (v) `https://github.com/boysugi20/python-stock-support-resistance`
   [fetched — search-extracted].
4. **License:** Tutorials: site copyright (text/code snippets have no explicit
   licence). `boysugi20` repo: no licence stated in the search-extracted README
   (**ASSUMPTION**: all rights reserved; treat as reference, re-implement).
5. **Output:** (i)(ii)(v) price lines at KMeans cluster boundaries (min/max); (iii)
   lines/zones (rectangles) from extremes clusters; (iv) clustered zones from swing
   highs/lows plus a KDE "density gradient" of swing prices.
6. **Algorithm:** (iv) is the closest to the plan and is a complete recipe:
   `scipy.signal.argrelextrema` on High/Low with an order/window (`SWING_WINDOW=30`)
   → collect swing highs/lows → greedy 1-D clustering with a **relative tolerance**
   (0.5% in the article) merging levels within tolerance of the cluster mean →
   horizontal segments spanning the cluster's first-to-last swing ± window → colour
   by majority type (support/resistance) → finally `scipy.stats.gaussian_kde` over
   the pooled swing prices to draw a density gradient (peaks = strongest levels).
   (i)(ii)(v) instead cluster all closes or all extremes with KMeans and use the
   min/max of each cluster as S/R, choosing `k` by elbow/`kneed`.
7. **Repaint?** The pipelines use only historical bars in the tutorials, but the
   swing window (`argrelextrema` order=30) is non-causal for the most recent 30 bars,
   and KMeans clusters change as data arrives. Same causal fixes as A7/A9.
8. **How to make it causal:** Confirmed swings only (`order`-bar delay); trailing
   window; recompute per closed bar; freeze zones between recomputes.
9. **Parameters + ATR scaling:** (iv) `SWING_WINDOW=30`, `CLUSTER_DISTANCE=0.5%`.
   For EURUSD, 0.5% is ~55 pips — far too wide for M5/M15; replace with
   `CLUSTER_DISTANCE = 0.25–0.5 × ATR(14, TF)`. KMeans: `k` 4–12.
10. **Zone width logic:** (iv): lines with a segment length; (iii): rectangles
    between cluster support and neighbouring resistance (the article explicitly says
    traders use rectangles rather than lines).
11. **Strength / freshness logic:** (iv) uses density (KDE) height as a strength
    proxy and majority type; the others use cluster size only.
12. **Typical number of zones:** (iv) with window 30 and 0.5% tolerance produced a
    handful of zones on 6 months of NIFTY; expect 5–15 before de-duplication.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Good as a **design template**:
    swing extraction + tolerance clustering + KDE density is exactly the A1/A3/A9
    stack. Do not copy parameters (they are equity-daily/percentage based).
14. **Confidence:** Medium on the recipes (source text read); Low on their
    validation — none of these articles reports out-of-sample evaluation or costs,
    and (i) explicitly concludes KMeans "is not a great solution" for high-timeframe
    S/R. Use as implementation references only.

## A9. `scipy.signal.argrelextrema` + tolerance clustering (the minimal swing primitive)

1. **Name / maintainer:** SciPy Developers (`scipy.signal.argrelextrema`).
2. **Category:** Python library (local extrema) / quant method.
3. **Source URL:** SciPy API (same repo/docs as A3) [fetched]; used in A8(iv)
   [fetched — search-extracted].
4. **License:** BSD-3-Clause.
5. **Output:** Tuple of integer indices where `data[i]` is greater/less than the
   `order` neighbours, e.g. `argrelextrema(highs, np.greater_equal, order=n)`. The
   caller extracts the prices. Points only.
6. **Algorithm:** A comparison against the previous and next `order` samples
   (`mode='clip'` by default at the boundaries). With `order=30` on daily highs, the
   centre bar must be the maximum of a 61-bar window. It is a symmetric window, so
   the extremum is only known after the right half has printed. Then a second pass
   clusters the extracted prices within a tolerance (greedy merge in the A8
   pipeline).
7. **Repaint?** Yes for the last `order` bars: an extremum inside the right window is
   not confirmed until `order` further bars close. Also, `greater_equal` can mark
   plateaus/multiple bars.
8. **How to make it causal:** Emit an extremum at index `i` only when the newest
   closed bar index is `≥ i + order`; maintain a pending buffer. Alternatively use
   `order` small (2–3) if a small lag is acceptable, or a one-sided running-extreme
   rule (like ZigZag) that finalises when price retraces by a threshold.
9. **Parameters + ATR scaling:** `order` (sweep 3–10 on M5/M15; 20–50 on H1/H4 in
   the tutorials is equity-daily scale). There is no ATR inside; couple with
   tolerance clustering `tol = 0.25–0.5 × ATR(14, TF)`.
10. **Zone width logic:** From the clustering tolerance (merged extremes within
    `tol` form a zone whose width is the cluster's min–max), or `±0.25 × ATR`.
11. **Strength / freshness logic:** Number of merged extremes, type balance
    (support vs resistance), recency.
12. **Typical number of zones:** On EURUSD M5 with `order=5` and a 2-session window,
    dozens of extremes → after tolerance clustering, ~5–10 zones.
13. **Fit for EURUSD M5/M15 with H1/H4 context:** Good and dependency-light; the
    natural baseline against which A1 (ZigZag) and A3/A4 (KDE) are compared. Its
    `order` parameter gives an explicit, easily auditable confirmation lag.
14. **Confidence:** High on API/behaviour (SciPy docs); High on causality analysis
    (symmetric window is definitional); Medium on zone quality (needs clustering).

---

# Part B — Academic literature

## B1. Osler (2000), "Support for Resistance: Technical Analysis and Intraday Exchange Rates"

1. **Name / author:** Carol L. Osler, FRBNY Economic Policy Review, Vol. 6, No. 2,
   July 2000 (16 pp).
2. **Category:** Academic paper (market microstructure / technical analysis).
3. **Source URL:** `https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html`
   [fetched]; PDF `https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf`
   [fetched — search-extracted]; SSRN `https://ssrn.com/abstract=888805` (cite only).
4. **Copyright:** Federal Reserve Bank of New York (2000).
5. **Object studied:** **Lines** — the support and resistance levels published daily
   by six FX firms to clients (not zones).
6. **Method:** Bootstrap. A level is "hit" if the bid (support) / ask (resistance)
   comes within 0.01% of it; a trend is "interrupted" ("bounce") if the price has not
   crossed the level 15 minutes later (30-min and 0.00%/0.02% cutoffs as
   robustness). Bounce frequencies for published levels are compared month by month
   with the average bounce frequency of 10,000 sets of artificial levels per day.
7. **Data / sample:** Six firms, January 1996 – March 1998; USD/DEM, USD/JPY,
   USD/GBP; indicative quotes sampled at **one-minute** intervals, 9:00–16:00 New
   York. Approximately 23,700 (DEM), 22,800 (JPY) and 17,700 (GBP) published S/R
   values; two of six firms did not publish GBP levels.
8. **Measured effect:** Published levels bounced **60.8%** of the time on average vs
   **56.2%** for arbitrary levels; published exceeded arbitrary in **all 16
   firm-currency pairs**; by currency the edge was **+4.2 pp (DEM), +5.6 pp (JPY),
   +4.0 pp (GBP)**; statistically significant at 5% for all but three
   firm-currency pairs; the best and worst firms differed by ~4.0 pp; predictive
   power lasted **at least five business days** after publication; finally, the
   strength labels published with the levels were **not informative** (firms did not
   correctly rank which levels were more likely to hold).
9. **Cost treatment:** None. This is a hit/bounce-frequency test, not a P&L test;
   spreads, slippage and execution are not modelled. **"Survives costs" = NOT
   TESTED.**
10. **How it maps to a zone generator:** Justifies S/R as a real intraday
    phenomenon with a measurable edge over arbitrary levels; supports (a) generating
    zones rather than lines (the 0.01% hit tolerance is effectively a small zone),
    (b) a **freshness window of ~5 business days** for levels, and (c) computing
    strength from data, since firm-provided strength labels failed.
11. **Caveats:** Pre-euro, pre-algo sample (1996–98); indicative rather than dealable
    quotes; a 15-minute bounce definition is a horizon choice; a 4–5.6 pp edge in
    bounce frequency may be far too small to pay the spread.
12. **Confidence:** High (full article text and abstract read; numbers quoted from
    the publisher's own summary/PDF extraction).

## B2. Osler (2003), "Currency Orders and Exchange Rate Dynamics"

1. **Name / author:** Carol L. Osler, Journal of Finance 58(5), 1791–1819.
2. **Category:** Academic paper (FX order flow / round numbers).
3. **Source URL:** Wiley `https://onlinelibrary.wiley.com/doi/10.1111/1540-6261.00588`
   [fetched — search-extracted]; working-paper PDF
   `https://www.econstor.eu/bitstream/10419/60582/1/331762730.pdf`
   [fetched — search-extracted]; `https://www.chesler.us/resources/academia/osler_ta.pdf`
   [fetched — search-extracted].
4. **Copyright:** The American Finance Association / Wiley (2003).
5. **Object studied:** **Order-level round numbers** (requested execution rates of
   stop-loss and take-profit orders), and the round-number levels themselves.
6. **Method:** Cross-sectional distribution of the last digits of requested
   execution rates, by order type (stop-loss buy/sell, take-profit buy/sell);
   Anderson–Darling tests against uniformity; bootstrap tests of asymmetry between
   order types; a simulation of exchange-rate behaviour conditional on order
   clustering.
7. **Data / sample:** The complete set of stop-loss and take-profit orders placed at
   one large FX dealing bank, **1 August 1999 – 11 April 2000**, covering USD/JPY,
   GBP/USD and EUR/USD, with total order value reported in excess of **$55 billion**
   (working-paper version).
8. **Measured effect:** Requested rates cluster strongly at round numbers; the single
   largest cluster is at rates ending in **00** (about **8.7%** of all orders on
   average, vs ~1% under uniformity; the arrival of any rounding is rejected at
   better than the 0.01% level). Executed **take-profit** orders are executed at
   `00` far more often than stop-loss orders: **9.8% of take-profit order value vs
   4.3% of stop-loss order value** (working-paper version; the JF-summary text uses
   ~**9.3% vs 4.4%** for the equal-weighted/executed variant). Asymmetry 2:
   stop-loss **buy** orders cluster just **above** round numbers and stop-loss
   **sell** orders just **below**; take-profit orders show no such asymmetry — e.g.
   4.5% of executed stop-loss sell orders sit at rates ending in 45 vs 2.0% of
   take-profit buy orders. Simulation: bounce frequency at round numbers exceeds
   arbitrary numbers in **20 of 20 cases** across two horizons (significant at the
   0.01% level).
9. **Cost treatment:** None. The paper explains *why* S/R predictions work; it does
   not run a trading strategy. **"Survives costs" = NOT TESTED.**
10. **How it maps to a zone generator:** Provides the microfoundation for a
    **round-number zone generator**, and — more importantly for zone physics — the
    prediction is **side-dependent**: take-profit clusters (reversal pressure) at
    round numbers, stop-loss clusters (acceleration) just beyond them. A zone
    engine can therefore emit asymmetric zones (reversal zone at round numbers,
    breakout zone just beyond).
11. **Caveats:** One bank, nine months, 1999–2000; the two published versions differ
    slightly in the headline percentages; no cost analysis; modern algo/HFT order
    placement may have changed the clustering.
12. **Confidence:** High on the existence of order clustering at round numbers and on
    the direction of the asymmetries (multiple independent extracts agree); Medium
    on exact percentages (two version variants quoted above).

## B3. Osler (2005), "Stop-Loss Orders and Price Cascades in Currency Markets"

1. **Name / author:** Carol L. Osler, Journal of International Money and Finance
   24(2), 219–241 (March 2005); earlier version = FRBNY Staff Report 150.
2. **Category:** Academic paper (FX microstructure / round numbers).
3. **Source URL:** FRBNY Staff Report PDF
   `https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf`
   [fetched — search-extracted]; Georgetown copy
   `https://faculty.georgetown.edu/evansm1/New%20Micro/osler1.pdf`
   [fetched — search-extracted].
4. **Copyright:** Elsevier / The Journal of International Money and Finance (2005).
5. **Object studied:** **Round-number levels** (rates ending in 00 or 50) as proxies
   for stop-loss clusters; measurable as levels/zones.
6. **Method:** Find every episode where the rate comes within 0.01% of a round
   number; split into crossing vs reversal subsamples; compare the average signed
   log price change after reaching round numbers (`MVR`) with that after arbitrary
   numbers (`MVA`) at 15 min and longer horizons, with 10-day-interval bootstrap
   tests; contrast responses to stop-loss vs take-profit clusters.
7. **Data / sample:** Over two years of **minute-by-minute** quotes for USD/DEM,
   USD/JPY and GBP/USD.
8. **Measured effect:** After crossing a round number the rate moves faster than
   after crossing an arbitrary number: USD/DEM averages **0.061% in the 15 minutes
   after a round-number crossing vs 0.054% for arbitrary numbers**; the round-number
   average exceeded the arbitrary average in **51 of 58 10-day intervals**
   (marginal significance below 0.001%). USD/JPY moves **0.0130 pp more** after a
   crossing than after a reversal at a round number (positive in 46 of 58 intervals,
   p < 0.001%). The reversal ("bounce") tendency at round numbers is significant only
   for horizons **shorter than 30 minutes**; the post-crossing acceleration remains
   significant for **at least two hours**; results are significant for **hours, not
   days**.
9. **Cost treatment:** None (no P&L test), but the effect sizes are directly
   informative: the round-vs-arbitrary **differential** is on the order of
   0.007 percentage points, i.e. well under 1 pip on EURUSD-scale prices
   (**ASSUMPTION: my own unit conversion, not in the paper**). At the 15-minute
   horizon this is far below any realistic spread. **"Survives costs" = NOT
   TESTED**, and the raw magnitudes suggest the naive version would not.
10. **How it maps to a zone generator:** Supports two distinct zone phenomena:
    (i) a short-lived **reversal zone at round numbers** (<30 min) and (ii) an
    **acceleration zone just beyond round numbers** (≥2 h). Both are time-limited —
    a zone engine needs an explicit decay/horizon parameter, not a static line.
11. **Caveats:** Pre-2005 sample; magnitudes are tiny relative to FX costs; "hours,
    not days" means any M5/M15 use must be intraday and fast.
12. **Confidence:** High on direction and significance (publisher summary + full
    PDF extraction agree); High that costs were not tested.

## B4. Menkhoff & Taylor (2007), "The Obstinate Passion of Foreign Exchange Professionals: Technical Analysis"

1. **Name / author:** Lukas Menkhoff & Mark P. Taylor, Journal of Economic
   Literature 45(4), 936–972 (December 2007).
2. **Category:** Academic survey.
3. **Source URL:** `https://www.aeaweb.org/articles?id=10.1257%2Fjel.45.4.936`
   [fetched]; working paper `http://www.econstor.eu/handle/10419/22464`
   [fetched — search-extracted].
4. **Copyright:** American Economic Association (2007).
5. **Object studied:** The literature on TA in FX; S/R is discussed as the most
   widely used chart output rather than measured separately.
6. **Method:** Narrative survey; establishes stylised facts and evaluates four
   explanations (not-fully-rational behaviour; central-bank intervention;
   information processing; non-fundamental influences).
7. **Data / sample:** The FX TA literature, including the dealer surveys (e.g. more
   than 90% of London FX participants using TA as a primary or secondary source —
   Allen & Taylor 1992, Lui & Mole 1998; 25–30% basing most trades on TA — Cheung &
   Chinn 1999; these figures are quoted from Osler 2000's literature summary).
8. **Measured effect:** The paper's own conclusion is qualitative: "applying certain
   technical trading rules over a sustained period may lead to significant positive
   excess returns", while the survey also stresses that evidence is heterogeneous
   and sensitive to costs/data mining. It does not report a single effect size for
   S/R zones.
9. **Cost treatment:** Survey-level discussion; the paper does not normalise costs
   across studies — it flags them as a key caveat.
10. **How it maps to a zone generator:** Justifies S/R as a market-relevant object
    (near-universal use) and supports the "non-fundamental influences" explanation,
    which is the mechanism by which price-memory zones can work.
11. **Caveats:** Survey, not new evidence; the "may be profitable" claim is not
    conditional on costs. Use as motivation, not as evidence for a zone edge.
12. **Confidence:** High on citation and abstract (AEA page fetched); Medium on
    specific usage percentages (they are second-hand within the survey).

## B5. Neely & Weller (2003), "Intraday Technical Trading in the Foreign Exchange Market"

1. **Name / author:** Christopher J. Neely & Paul A. Weller, Journal of
   International Money and Finance 22(2), 223–237; earlier version = FRB St. Louis
   Working Paper 1999-016.
2. **Category:** Academic paper (intraday FX, costs).
3. **Source URL:** `https://files.stlouisfed.org/files/htdocs/wp/1999/99-016.pdf`
   [fetched — search-extracted]; `https://ideas.repec.org/a/eee/jimfin/v22y2003i2p223-237.html`
   [fetched — search-extracted].
4. **Copyright:** Elsevier (2003).
5. **Object studied:** Trading rules (genetic program and linear forecasting) on
   intraday FX — not S/R levels specifically, but the best available benchmark for
   "does intraday FX predictability survive costs".
6. **Method:** Select rules in-sample (genetic program; AR/linear forecasting model),
   then evaluate out-of-sample; vary the transaction cost in training/selection
   (0, 1, 2 bp one-way); compute break-even costs; separately restrict trading to
   12 business hours.
7. **Data / sample:** Intraday quotes for USD/DEM, USD/JPY, USD/CHF, GBP/USD; 25
   rules per currency per cost assumption.
8. **Measured effect:** With zero costs, rules trained at zero cost produce "over
   100% per annum" out-of-sample returns in three of four cases, trading roughly
   once an hour; the highest all-day break-even cost is **1.01 bp** one-way (GBP).
   For the linear model, DEM zero-cost return falls from **102% to 40%** and trades
   from **3,611 to 61** as the in-sample cost goes 0→2 bp, with break-even cost
   **19.15 bp** for DEM all-day. Once trading is restricted to business hours
   (DEM 06:00–18:00 GMT, etc.), break-even costs fall below the level a large
   institutional trader would face and there is **no evidence of excess returns net
   of costs**.
9. **Cost treatment:** Central; assumes 2.5 bp one-way as the large-institution
   benchmark; conclusion: predictability is real, profitability after costs is not.
10. **How it maps to a zone generator:** A direct warning: a zone generator can show
    statistically clean conditional behaviour and still be untradeable once costs
    enter. The bake-off should treat break-even cost as a first-class output.
11. **Caveats:** Rules are not S/R-zone-based; sample is 1990s FX; "zero-cost
    predictability" ≠ "tradeable edge" is the whole point.
12. **Confidence:** High (full text extraction read; numbers quoted verbatim from
    the working paper).

## B6. Park & Irwin (2007), "What Do We Know About the Profitability of Technical Analysis?"

1. **Name / author:** Cheol-Ho Park & Scott H. Irwin, Journal of Economic Surveys
   21(4), 786–826.
2. **Category:** Academic survey.
3. **Source URL:** `https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-6419.2007.00519.x`
   [fetched — search-extracted].
4. **Copyright:** Blackwell Publishing / Wiley (2007).
5. **Object studied:** 95 "modern" studies of technical trading profitability across
   FX, futures and stocks.
6. **Method:** Systematic literature classification into "early" vs "modern"
   studies; counts of positive/negative/mixed results; critique of testing
   procedures.
7. **Data / sample:** 95 modern studies (exact study list in the paper).
8. **Measured effect:** **56 studies positive, 20 negative, 19 mixed.** Early
   studies: profitable in FX and futures, not in stocks. Modern studies: economic
   profits in a variety of speculative markets "at least until the early 1990s".
9. **Cost treatment:** Reviewed explicitly as a weakness: "most empirical studies
   are subject to various problems … e.g. data snooping, ex post selection of
   trading rules or search technologies, and difficulties in estimation of risk and
   **transaction costs**." The positive counts are therefore not cost-corrected.
10. **How it maps to a zone generator:** Sets expectations: most published TA
    effects are positive *before* costs and *before* data-snooping corrections; a
    zone bake-off must declare costs and a snooping correction up front.
11. **Caveats:** Survey; counting studies is not a meta-analysis of effect sizes;
    the "modern" cutoff is ~1990.
12. **Confidence:** High (abstract and counts read from the publisher/RePEc pages).

## B7. Bajgrowicz & Scaillet (2012), "Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs"

1. **Name / author:** Pierre Bajgrowicz & Olivier Scaillet, Journal of Financial
   Economics 106(3), 473–491.
2. **Category:** Academic paper (data snooping + costs).
3. **Source URL:** `https://www.sciencedirect.com/science/article/abs/pii/S0304405X1200116X`
   [fetched — search-extracted]; full PDF `https://scaillet.ch/pdfs/BajSca.pdf`
   [fetched — search-extracted].
4. **Copyright:** Elsevier (2012).
5. **Object studied:** The 7,846 Sullivan–Timmermann–White trading rules (MA and
   trading-range/filter rules) on the DJIA.
6. **Method:** False Discovery Rate (FDR) for data-snooping control + persistence
   tests (monthly rule selection, genuinely out-of-sample evaluation) + transaction
   costs made endogenous to the selection.
7. **Data / sample:** Daily DJIA, **January 1897 – July 2011**.
8. **Measured effect:** One-way proportional costs of **16, 35 and 70 bp** are
   enough to eliminate FDR-selected outperformance in the three sub-periods
   1897–1962; in period 3 (1939–1962) **75%** of rules have positive in-sample
   performance before costs and costs below **25 bp** prevent the vast majority from
   breaking even; in period 4 (1962–1986) the positive-before-cost share falls to
   **44%** and most need costs below **10 bp**. Out-of-sample persistence: "an
   investor would never have been able to select ex ante the future best-performing
   rules"; no hot-hands effect.
9. **Cost treatment:** Core result — even low costs offset the in-sample
   performance, and costs change which rules look good.
10. **How it maps to a zone generator:** The strongest available ceiling: if a
    zone-based strategy trades frequently, assume its apparent edge is measured
    pre-cost and will need break-even costs well above a retail FX spread to
    matter. Also: rule/parameter selection on the same data must be FDR-aware.
11. **Caveats:** Equity index, not FX; daily frequency, not M5/M15; longer sample
    than any FX intraday study.
12. **Confidence:** High (abstract + full-text extraction read; exact bp figures
    quoted from the PDF text).

## B8. Lo, Mamaysky & Wang (2000), "Foundations of Technical Analysis"

1. **Name / author:** Andrew W. Lo, Harry Mamaysky & Jiang Wang, Journal of
   Finance 55(4), 1705–1765.
2. **Category:** Academic paper (pattern recognition / zone-like objects).
3. **Source URL:** `https://web.mit.edu/Alo/www/Papers/1705-1765.pdf`
   [fetched — search-extracted]; NBER w7613 [fetched — search-extracted].
4. **Copyright:** The American Finance Association (2000).
5. **Object studied:** Automatic **local extrema and geometric patterns**
   (head-and-shoulders, double tops/bottoms, etc.) — the closest academic object to
   swing-point zones.
6. **Method:** Nonparametric **kernel regression** (Nadaraya–Watson smoother) to
   filter noise; local maxima/minima of the smoothed series define pivots; pattern
   templates (e.g. HS, BTOP, DBOT) matched on those extrema; conditional vs
   unconditional return distributions compared with goodness-of-fit tests and Monte
   Carlo calibration.
7. **Data / sample:** Several hundred US stocks, **1962–1996** (31 years), NYSE/AMEX
   and Nasdaq.
8. **Measured effect:** Conditional return distributions differ significantly from
   the unconditional for **7 of 10 patterns on NYSE/AMEX** (exceptions: BBOT
   p = 5.1%, TTOP p = 21.2%, DBOT p = 16.6%) and for **all 10 patterns on Nasdaq**;
   the paper concludes several indicators "do provide incremental information and
   may have some practical value". Informativeness ≠ profitability (explicit).
9. **Cost treatment:** None (the test is distributional, not P&L). **"Survives
   costs" = NOT TESTED.**
10. **How to map it to a zone generator:** The kernel-regression + local-extrema
    pipeline is a direct, citable precedent for the KDE/clustering approach: smooth
    first, extract extrema second, define zones around them. It also gives a
    credible academic precedent for testing zones by comparing conditional vs
    unconditional next-k-bar return distributions rather than only P&L.
11. **Caveats:** Equity daily data; pattern templates are not S/R zones; no costs;
    the paper's own tone is "mixed support".
12. **Confidence:** High (abstract + full-text extraction read).

## B9. Round-number barriers: Mitchell & Izan (2006); De Grauwe & Decupere (1992); Westerhoff (2003)

1. **Name / author:**
   (i) Jason Mitchell & H.Y. Izan, "Clustering and psychological barriers in
   exchange rates", Journal of International Financial Markets, Institutions and
   Money 16(4), 318–344 (October 2006);
   (ii) Paul De Grauwe & Danny Decupere, "Psychological Barriers in the Foreign
   Exchange Market", CEPR Discussion Paper No. 621 (1992);
   (iii) Frank Westerhoff, "Anchoring and Psychological Barriers in Foreign
   Exchange Markets", Journal of Behavioral Finance 4(2) (2003).
2. **Category:** Academic papers (round-number clustering and barriers).
3. **Source URL:** (i) `https://doi.org/10.1016/j.intfin.2005.03.003` and
   `https://www.sciencedirect.com/science/article/abs/pii/S1042443105000508`
   [fetched — search-extracted];
   (ii) `https://cepr.org/publications/dp621` [fetched];
   (iii) `https://www.uni-bamberg.de/fileadmin/uni/fakultaeten/sowi_lehrstuehle/vwl_wirtschaftspolitik/Team/Westerhoff/Publications/2003/2003_Westerhoff_VIII.pdf`
   [fetched — search-extracted].
4. **Copyright:** (i) Elsevier (2006); (ii) CEPR (1992); (iii) Taylor & Francis
   (Journal of Behavioral Finance, 2003).
5. **Object studied:** Last-digit clustering and **round-number barriers** in FX
   (whole numbers, 00/50 levels). Barriers behave as resistance before the level and
   as acceleration after the crossing — i.e. they are zonal in time, not static
   lines.
6. **Method:** (i) Frequency tests on trailing digits plus "passing" / transgression
   tests against simulated benchmark series; (ii) barrier tests on USD/DEM and
   USD/JPY; (iii) a deterministic chartist–fundamentalist model where the perceived
   fundamental is anchored to the nearest round number.
7. **Data / sample:** (i) daily AUD crosses (DEM, FRF, ITL, GBP, CHF, USD, JPY vs
   AUD), **1 Jan 1978 – 31 Dec 1992** (FRF from 1981); (ii) USD/DEM and USD/JPY
   (1980s); (iii) simulation only, no data.
8. **Measured effect:** (i) **widespread clustering** in exchange-rate digits —
    "there is partial information content in the actual numbers of the exchange
    rates themselves" — but only "some, but not strong, evidence" that psychological
    barriers exist; the location and form of both clustering and transgressional
    effects differ across pairs and are "in most instances … not in the expected
    direction". (ii) Barriers **significant in USD/JPY** (rates resist 130, 140, …
    yen/dollar, then accelerate away once crossed); evidence for USD/DEM
    "less clear-cut". (iii) The model generates bands around anchors that resemble
    support/resistance levels and produces persistent misalignment, excessive
    volatility and volatility clustering as stylised outcomes; no empirical effect
    size.
9. **Cost treatment:** None in any of the three (statistical/behavioural tests).
10. **How it maps to a zone generator:** Round-number grids are a cheap,
    zero-parameter zone generator (levels ending in 00/50, and possibly 25/75 for
    EURUSD quarter zones). The literature supports the mechanism but (i) and (ii)
    disagree on robustness, and (iii) shows the effect can be model-endogenous
    rather than a market fact.
11. **Caveats:** (i) daily 1978–1992, AUD crosses; (ii) 1980s; (iii) purely
    theoretical. The mixed replication record is the key input: round numbers
    deserve a slot in the bake-off, not a default role.
12. **Confidence:** High on citations and on the mixed nature of the evidence;
    Medium on effect magnitudes (different eras, different definitions of barrier).

## B10. Brock, Lakonishok & LeBaron (1992), "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns"

1. **Name / author:** William Brock, Josef Lakonishok & Blake LeBaron, Journal of
   Finance 47(5), 1731–1764.
2. **Category:** Academic paper (classic S/R-breakout and MA rule evidence).
3. **Source URL:** Wiley abstract
   `https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04681.x`
   [fetched — search-extracted]; full PDF mirror
   `https://finance.martinsewell.com/stylized-facts/distribution/BrockLakonishokLeBaron1992.pdf`
   [fetched — search-extracted].
4. **Copyright:** The American Finance Association (1992).
5. **Object studied:** Two rule families: moving-average oscillator and
   **trading-range break** (`TRB`). The TRB is literally an S/R-breakout generator:
   buy when price exceeds the resistance level (highest high of the past 50/150/200
   days), sell when it falls below the support level (lowest low), with a 1%
   band variant.
6. **Method:** Standard t-tests plus bootstrap inference against four null models
   (random walk, AR(1), GARCH-M, EGARCH); comparison of returns following buy vs
   sell signals, including volatility and sign fractions.
7. **Data / sample:** Dow Jones Industrial Average, **1897–1986** (90 years), daily.
8. **Measured effect:** For the variable-length moving-average rules, buy periods
   average **+0.042% per day (~12% p.a.)**, sell periods average **−0.025% per day
   (~−7% p.a.)**, against an unconditional **+0.017% per day**; the fraction of
   positive days is ~53–54% for buys vs ~49% for sells; buy-sell differences are
   positive and mostly significant. The paper states the TRB (support/resistance
   breakout) results also support the technical strategies and that returns are
   inconsistent with all four null models; sell-signal returns being negative is
   the result hardest to reconcile with equilibrium models. (The precise VMA numbers
   above are the ones read from the paper; the TRB table was not extracted
   numerically.)
9. **Cost treatment:** No transaction costs are applied; the paper is the canonical
   pre-cost result and is the direct target of later cost/data-snooping critiques
   (B6, B7). **"Survives costs" = NOT TESTED.**
10. **How it maps to a zone generator:** The TRB rule is the simplest possible S/R
    zone-breakout logic and provides the shape of a zone-physics hypothesis:
    "break of a multi-month extreme → continuation". It also sets the bar for
    statistical hygiene (bootstrap vs null models) that a bake-off should copy.
11. **Caveats:** Equity index, daily, pre-cost, pre-data-snooping-correction; B7
    shows the performance is offset by low costs and not ex-ante selectable.
12. **Confidence:** High on citation/sample/qualitative result; High on the quoted
    VMA numbers (read from the paper text); Medium on TRB-specific magnitudes.

---

# Notes for the bake-off

- **Realistic to implement causally in <200 lines each (Python, offline):**
  (1) ZigZag pivots (A1) — points only, needs a 10-line wrapper;
  (2) `argrelextrema` + tolerance clustering (A9) — the minimal baseline, ~60 lines;
  (3) KDE of swing prices (A3/A4) — ~30 lines once the swing sample exists;
  (4) round-number grid (B2/B3/B9) — ~10 lines, zero parameters;
  (5) Williams Fractals (A6) — ~20 lines with the `S`-bar confirmation delay;
  (6) classic pivots (A2) — ~20 lines of formulas on resampled H1/H4 bars;
  (7) market profile value area (A5) — ~80 lines if re-implemented from the
  `marketprofile` logic on closed bars (do not depend on the stale package).
  Realistically two heavy items for the first round: **ZigZag+merge** and
  **KDE+merge**; everything else is an axis (width rule, round numbers).
- **Default ATR-scaled parameters (sweep in the bake-off, do not hard-code):**
  swing threshold `k × ATR(14, TF)` with `k ∈ {0.5, 1.0, 1.5}`; KDE/MS bandwidth
  `c × ATR(14, TF)` with `c ∈ {0.25, 0.5, 1.0}`; merge tolerance
  `0.25–0.5 × ATR`; zone half-width `±0.25 × ATR`; row size for profiles
  `≈0.1 × ATR` (or 1 pip); value area 70%; fractal span `S=2` on H1/H4, `S=3` on
  M5/M15; freshness half-life 1–2 sessions (M5) / ~5 days (H1/H4).
- **Confirmation lags are the causal constraint, and they differ per generator:**
  fractals `S` bars; `argrelextrema` `order` bars; ZigZag = time until the
  threshold reversal (unknown in advance, typically 1–10 bars at 1×ATR); classic
  pivots = prior-period close; KDE/clustering = the staleness of the oldest pivot
  required to keep the sample stable. Record each generator's lag distribution —
  the bake-off should regress zone-edge outcomes on lag, because a generator that
  "wins" only with a 30-bar lag is not the same as one that wins with 2.
- **Known pitfalls, in priority order:**
  1. **KDE bandwidth dominates the result** (SciPy's own docs say so, and warn
     that Scott/Silverman oversmooth multimodal data). Fix the sweep, log it, and
     never choose it on the evaluation window.
  2. **Value-area window choice**: POC/VAH/VAL move with the session/window
     definition; `marketprofile` builds rows from **Close only** and `vol` mode
     sums MT5 **tick volume**, not real volume. Prefer `tpo` mode or a
     re-implementation that distributes each candle over its high-low range.
  3. **Causal leaks**: ZigZag's initial-pivot scan, the last provisional pivot,
     `argrelextrema` right window, fractal right window — all silently use future
     bars if the raw library output is taken at face value.
  4. **K-means `k` selection is unreliable** (elbow failed on price histograms in
     the published walkthroughs; alpharithms concludes KMeans "is not a great
     solution" for high-timeframe S/R). Prefer mean-shift/KDE or Fisher-Jenks, or
     fix `k` by preregistration.
  5. **Strength labels from chart vendors are not evidence of strength** — Osler
     (2000) found published strength estimates were not informative. Compute
     strength from data (touch count, recency, density height), and test it.
  6. **Round-number zones have a mixed replication record** — Osler's positive
     order-flow evidence vs Mitchell & Izan's weak/unexpected barriers, plus a
     practitioner replication that found round-50 sweep effects with z = −2.59 in a
     13-month window but mean z = +0.08 and 0 of 12 significant across 12 longer
     windows ("window luck": `https://hadalinstruments.com/research/do-round-numbers-matter-in-forex/`
     [fetched — search-extracted]). Keep round numbers as a candidate generator,
     with the same preregistered window-stability test as every other generator.
  7. **Costs kill most of what survives significance**: break-even costs of
     ~1 bp (Neely & Weller) and offsets at 10–70 bp (Bajgrowicz & Scaillet) mean
     the bake-off's cost model is not a side-check; report break-even cost per
     generator, not just pre-cost conditional probabilities.
  8. **Output-type mismatch**: pivots/fractals/pivots-points return **lines**;
     profiles return **bands**; KDE/clustering return **variable-width peaks**.
     Normalise everything to `(price_low, price_high, born_at, confirmed_at,
     provenance)` before the bake-off so width logic is a shared axis rather than
     an artefact of each generator. (This observation assumes the harness can
     express zones that way; the repo already ships `PA_Pro/lib/pa_clock.py`,
     `pa_data.py` and `pa_costs.py` per the directory listing — AS ASSUMPTION about
     their interfaces, no files were read.)
- **What was not verified here:** the `pivotpoints` PyPI project (404 — treat as
  non-existent); gap-statistic and `kneed` packages (cite only); the TRB-specific
  numbers in BLL (numbers quoted are for the VMA rules); exact order-value
  percentages in Osler (2003) differ slightly between the working-paper and JF
  versions (both quoted); no attempt was made to run any of these generators on
  EURUSD data — all fit assessments are analytical.
