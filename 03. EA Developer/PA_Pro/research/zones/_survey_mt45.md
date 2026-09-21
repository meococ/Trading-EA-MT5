# Survey — MT4/MT5 Support/Resistance Zone & Supply/Demand Generators

Task: T-PAPRO-ZONE-1 (program PA-PRO). Purpose: candidate zone GENERATORS for a preregistered
zone-physics bake-off on EURUSD M5/M15 with H1/H4 context.
Method: web research only (websearch + webfetch); no code execution, no MT5, no OCR.
Date: 2026-09-20.

Confidence convention used below:
- **high** = page fetched and algorithm/parameters described on that page, or source read.
- **medium** = page fetched but internals partly unknown (closed source), or cite-only with strong corroboration.
- **low** = cite-only and unverified.

Global caveats:
- MQL5 CodeBase pages (mql5.com/en/code/*) do **not** state a license name. Where no license is shown I write
  `unknown`; the MQL5.com Terms of Use govern the site, and the authors retain their copyright. None of these
  are OSI open-source unless explicitly stated. Treat CodeBase as "source available for reading".
- MQL5 Market products (mql5.com/en/market/*) are closed binaries (`.ex5`/`.ex4`) unless the author states
  otherwise; they can never be re-implemented exactly, only benchmarked.
- No source code is pasted in this survey; algorithms are described in my own words.

---

## 1. Shved Supply and Demand (v1.7)

1. **Name + author/handle**: Shved Supply and Demand — original by "Shved", upgraded by eevviill7, MQL5 port
   and maintenance by **Behzad Movaghar** (`behzad.mvr`).
2. **Category**: S/R zones (fractal + ATR; "supply/demand" naming).
3. **Source URL**: https://www.mql5.com/en/code/29395 [fetched]
4. **License**: `unknown` (no license stated on the CodeBase page).
5. **Output**: horizontal zones (rectangles) with type/strength labels. Zone types: weak, untested, verified,
   proven, broken. Optional multi-timeframe mode (v1.5+) to draw zones of another TF on the current chart.
   Data-window buffers expose zone strength/type (v1.7). ~38.6 KB mq5 (v1.7), plus a v1.6 file.
6. **Algorithm in my own words**: It detects fractal highs/lows (Bill Williams-style fractals) on the selected
   timeframe. Each significant fractal becomes a zone whose vertical extent is derived with the ATR indicator
   (ATR-scaled, not fixed pips). Zones are then classified by subsequent price behavior: "weak" = trend
   high/low; "untested" = never revisited; "verified" = touched but not broken; "proven" = at least four
   unsuccessful tests; "broken" = price closed through (not applied to weak zones). Broken zones are handled/
   pruned per settings. A "history mode" lets the user double-click a past chart point to reconstruct which
   zones existed at that moment. A prefix parameter allows multiple instances.
7. **Repaint?** **partial**. Fractals need 2 bars to the right to confirm, so a zone is created 2+ bars after
   its pivot. Zone *status* changes over time as price tests/breaks (verified → proven → broken); whether a
   past bar's display matches live evolution is exactly what "history mode" was added for. No future bars are
   used beyond the fractal confirmation window.
8. **How to make it causal**: confirm fractals only after 2 closed bars; rebuild the zone state machine
   left-to-right bar by bar; apply status transitions only at bar close; never use history mode for backtest
   (it is a reconstruction, not the live sequence).
9. **Parameters + ATR**: fractal depth/period, ATR period and multipliers, toggles for each zone type, TF
   selection, prefix, alerts. **ATR-scaled** (per the page: "uses fractals and ATR indicator").
10. **Zone width logic**: fractal level ± ATR-derived amount (exact multipliers not published on the page).
11. **Strength/freshness**: touch/break counts drive the weak/untested/verified/proven/broken classes;
    "proven" requires 4 failed breaks. No volume component described.
12. **Typical number of zones**: not stated. Implied: many across history if weak zones are shown; a handful
    of active verified/proven zones near price. `ASSUMPTION:` 5–20 active on M15.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: strong. Built-in MTF option, ATR-scaled widths and a
    proven/verified ranking map well to the bake-off; raise fractal depth on M5 to avoid noise.
14. **Confidence**: **high** — page fetched, behavior and zone taxonomy documented; exact ATR multipliers
    unverified.

---

## 2. Smart S/R Zones MT4 — Swing-Pivot Support and Resistance

1. **Name + author/handle**: Smart S/R Zones MT4 — **Antonios Kokkalis** (`palaki06`), ArgosWatch.
2. **Category**: S/R zones (swing-pivot clustering, touch-count ranked, HTF overlay).
3. **Source URL**: https://www.mql5.com/en/code/76075 [fetched]
4. **License**: `unknown` (no license stated; author advertises "Free, full source").
5. **Output**: rectangles (zones) with on-chart touch-count labels (e.g. "x8"); optional higher-timeframe
   zones overlaid in a distinct color; zones far from price hidden. 13.76 KB mq4.
6. **Algorithm in my own words**: It finds real swing pivots (configurable pivot strength), not N-bar
   highest/lowest shortcuts. Nearby pivots are clustered into zones. Each zone is ranked by how many times
   price has actually tested it, and the touch count is printed on the zone. Zone thickness adapts so zones
   never visually overlap, and zones beyond a distance filter are hidden to keep the chart readable. An
   optional HTF overlay draws zones from a longer timeframe (auto-disabled if redundant). Proximity alerts
   (popup + sound) have a cooldown.
7. **Repaint?** **partial**. Pivots need `strength` bars to the right → creation lag; touch counts increase
   with new tests (labels update); the distance filter makes zones appear/disappear as price moves. No future
   data. A deterministic rebuild from bars gives the same final picture, but a live snapshot differs from a
   replay of intermediate states.
8. **How to make it causal**: confirm pivots after `strength` closed bars; add pivots to clusters only at
   confirmation; snapshot cluster membership and touch counts at each bar close; compute the distance filter
   from the last close.
9. **Parameters + ATR**: pivot strength, cluster tolerance, max zones, HTF timeframe, distance filter, alert
   cooldown, colors. Page says "adaptive zone thickness" but **does not state ATR** — likely point/pip-based
   (`ASSUMPTION`, unverified).
10. **Zone width logic**: adaptive thickness + cluster tolerance; formula not published.
11. **Strength/freshness**: direct touch count per zone; recency via the distance filter.
12. **Typical number of zones**: implied small (design goal is a readable chart; screenshot shows a handful
    per chart).
13. **Fit for EURUSD M5/M15 + H1/H4 context**: strong — the built-in HTF overlay and touch-count ranking are
    exactly the "M5/M15 with H1/H4 context" pattern; verify whether thickness is ATR-based before comparing
    widths.
14. **Confidence**: **high** for features; **medium** for width/ATR internals (not on the page).

---

## 3. ExMachina Supply & Demand Zones v2.0

1. **Name + author/handle**: ExMachina SupplyDemand Indicator — **WilliamMukam** / Emmanuel Nana Nana.
2. **Category**: supply-demand (impulse-based order blocks).
3. **Source URL**: https://www.mql5.com/en/code/70709 [fetched]
4. **License**: `unknown` (no license stated on the CodeBase page).
5. **Output**: rectangles for supply/demand zones with labels (type, freshness ●/[T], strength, touch count),
   optional midline, right-extension, and a dashboard panel. 34.6 KB mq5.
6. **Algorithm in my own words**: It scans the last N bars (default 1000). Over a 2–3 bar window it sums
   either total range (H−L) or net move (C−O) and compares to ATR(14); if the move is ≥ Min Impulse
   (default 1.0×ATR) it qualifies as an impulse and the base candle *before* the move is marked as a
   supply or demand zone. Same-type zones at similar prices are merged (Merge Distance 0.5×ATR). Each zone
   gets a strength score (impulse size relative to ATR), a freshness flag and a touch count, updated as
   price interacts. Proximity alerts default to 50 points. The optional dark theme recolors the whole chart.
7. **Repaint?** **partial**. A zone exists only after the impulse window (2–3 bars) closes → creation lag of
   2–3 bars. Freshness/touch labels update live. A full scan from scratch is deterministic if merge/touch
   logic is deterministic, but merged zone identity may be rewritten. No future bars are used.
8. **How to make it causal**: at bar t emit only zones whose impulse window closed at ≤ t; recompute touches
   from bars ≤ t; apply merging only at bar close and freeze zone IDs; disable the theme in research runs.
9. **Parameters + ATR**: Lookback 1000, Min Impulse 1.0×ATR, ATR Period 14, Multi-Candle Window 3, Use Range
   vs Body, Merge Distance 0.5×ATR, Show Only Fresh, proximity 50 points, visual/theme/dashboard toggles.
   Thresholds are **ATR-scaled**; proximity is in points.
10. **Zone width logic**: the base candle's full range (or body, per "Use Range (vs Body)"); merged zones
    union the participants.
11. **Strength/freshness**: impulse size ÷ ATR (strength score), touch count, fresh vs tested status.
12. **Typical number of zones**: the page says "if you see fewer than 5 zones on H1, lower Min Impulse to
    0.8" → order of ~5–20 on H1; more on M5.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: good. Author recommends H1/H4 and ATR-normalizes everything,
    but M5 will over-detect unless Min Impulse is raised and merging is active; theme/dashboard must be
    suppressed for clean comparisons.
14. **Confidence**: **high** — page fetched with full parameter table and algorithm text.

---

## 4. Support Resistance zig zag based (SNR.mq5)

1. **Name + author/handle**: Support Resistance zig zag based — **Ahmad Arju Sholeh** (`Arju0612_`).
2. **Category**: S/R zones + role reversal (SBR/RBS flip zones).
3. **Source URL**: https://www.mql5.com/en/code/76644 [fetched]
4. **License**: `unknown` (no license stated on the CodeBase page).
5. **Output**: rectangular zones with role colors (support/resistance → SBR/RBS after break); dashboard with
   market-bias gauge; retest alerts. 39.1 KB mq5 (screenshot is BTCUSD M5).
6. **Algorithm in my own words**: A ZigZag core finds swing highs/lows; a "Confirm Bars" input validates
   extremes before anything is drawn (explicit anti-repaint design). Zone width is normalized against
   historical average price movement so zones neither balloon nor collapse. A candle close beyond a zone
   converts support into SBR (support-becomes-resistance) or resistance into RBS, unless the user disables
   flipping so broken zones are deleted. A "Min Move Away" multiplier must be traveled before a zone
   activates and alerts only fire on a subsequent retest. Overlap resolution keeps either the most extreme
   or the newest zone. A dashboard computes the bullish/bearish ratio from recent ZigZag legs.
7. **Repaint?** **no/partial**. The author explicitly designed "Anti-Flicker & Repaint Safety: uses a
   confirmation delay to validate pivot points before drawing zones". Standard ZigZag caveat applies (the
   in-progress leg can move until confirmed), but drawn zones wait for confirmation and flips act on candle
   closes. Historical display should match live if parameters are unchanged.
8. **How to make it causal**: keep Confirm Bars ≥ 2, evaluate everything on closed bars, apply flips only at
   bar close, and treat the "Min Move Away" activation as an event on the bar where the distance is reached.
9. **Parameters + ATR**: ZigZag depth/deviation/backstep, Confirm Bars, Min Move Away, width normalization,
   overlap mode (Most Extreme / Newest), alerts. Width normalization is volatility-based (average movement),
   effectively ATR-like but not stated as ATR.
10. **Zone width logic**: proportional zone, normalized against historical average price movements.
11. **Strength/freshness**: freshness + retest after Min Move Away; overlap resolution; dashboard bias.
    No explicit touch counter described.
12. **Typical number of zones**: not stated; implied a handful (flip logic removes or converts zones).
13. **Fit for EURUSD M5/M15 + H1/H4 context**: good — designed and screenshotted on M5, causal by
    construction. **But there is no MTF input** (a user requested it and the author deferred), so H1/H4
    context must be produced by running the same generator on H4 data in Python.
14. **Confidence**: **high** — page fetched with explicit algorithm/feature list.

---

## 5. ATR Ranked Support and Resistance Zones

1. **Name + author/handle**: ATR Ranked Support and Resistance Zones — **Talal N Z Aljarusha** (`TalalEissa`).
2. **Category**: S/R zones (pivot clustering + ranking).
3. **Source URL**: https://www.mql5.com/en/code/74421 [fetched]
4. **License**: `unknown` (no license stated; author says "shared for educational purposes").
5. **Output**: horizontal price areas (rectangles) for only the highest-ranked zones, with a strength score
   label; zones below current price are shown as support and above as resistance. 13.0 KB mq5.
6. **Algorithm in my own words**: It starts from confirmed pivot highs/lows. Nearby pivots are merged using
   an ATR-based distance so the same logic adapts to symbol and timeframe. Each area receives a score from
   three parts: how many reactions were grouped inside it, how far price moved after those reactions, and
   how recently the area was tested. Only the highest-ranked areas are drawn. Support/resistance role is
   assigned purely by position relative to the current price. The author notes this role assignment is a
   simplification and suggests a confirmed break-and-retest would be better.
7. **Repaint?** **partial**. Pivots need right-side bars to confirm; the three-part score and the recency
   component change every bar; the support/resistance role flips as price crosses. A full scan reproduces
   the final state, not the live sequence of intermediate states.
8. **How to make it causal**: confirm pivots after a fixed lag; compute the score from past data only;
   replace role-by-position with an event-based role transition (break + retest), as the author himself
   suggests.
9. **Parameters + ATR**: pivot lookback, ATR period and merge multiplier, max number of drawn zones, score
   threshold. **ATR-scaled** merging.
10. **Zone width logic**: ATR-based merge distance (cluster span), not fixed pips.
11. **Strength/freshness**: three-part score = reaction count + post-reaction travel + recency.
12. **Typical number of zones**: only the top-ranked are drawn → few (single digits to low tens).
13. **Fit for EURUSD M5/M15 + H1/H4 context**: conceptually a good match (ATR-normalized clustering plus a
    strength score), but pivot lag and role-by-position must be fixed; it is explicitly a starting-point
    code, not a finished tool.
14. **Confidence**: **high** — page fetched, algorithm described by the author.

---

## 6. Price Action Zones (PAZ) MT4

1. **Name + author/handle**: PAZ Indicator — Price Action Zones — **capitafix** (Capitafix Inc.).
2. **Category**: S/R zones (swing-point clustering with ATR tolerance).
3. **Source URL**: https://github.com/capitafix/Price-Action-Zones-Indicator [fetched];
   LICENSE at https://raw.githubusercontent.com/capitafix/Price-Action-Zones-Indicator/main/LICENSE [fetched]
4. **License**: **GNU GPL v3** (LICENSE file begins "GNU GENERAL PUBLIC LICENSE Version 3"). Note: the README
   footer says "Copyright © 2025 Capitafix Inc. All rights reserved." — conflicting statements; the LICENSE
   file is GPL-3.0, so treat it as GPL-3.0.
5. **Output**: colored rectangles; color intensity = touch count (≤2 RosyBrown weak, 3–4 Chocolate,
   5–6 OrangeRed, >6 Red); zones extend `ZoneExtendBars` into the future; min-touch filter.
6. **Algorithm in my own words**: Classic swing detection using ExtDepth / ExtDeviation / ExtBackstep
   (ZigZag-style local extremes). Each detected swing is assigned to a zone if its distance to the zone
   centroid is within `eps = MergeATR × ATR(14)`; otherwise it opens a new zone. Adding a swing updates the
   zone centroid and its top/bottom bounds. Zones with fewer than `MinTouches` reactions are hidden. Objects
   are only redrawn when the zone count changes (anti-flicker). The scan window is `BarsMax` bars.
7. **Repaint?** **partial**. Swings need ExtDepth bars to the right → lag; when a new swing joins a zone the
   centroid and the whole rectangle's bounds update retroactively; the sliding `BarsMax` window drops old
   zones (expiry, not repaint). A deterministic rebuild gives a consistent final picture.
8. **How to make it causal**: confirm swings after ExtDepth bars; add swings to clusters only at
   confirmation; snapshot zone bounds and touch counts at each bar close.
9. **Parameters + ATR**: TimeFrame, BarsMax 168, ExtDepth 7, ExtDeviation 3, ExtBackstep 4, MergeATR 0.8,
   ATRPeriod 14, MinTouches 2, ZoneExtendBars 500, colors. **ATR-based tolerance** (documented explicitly).
10. **Zone width logic**: cluster span = min/max of member swings; membership governed by MergeATR × ATR.
11. **Strength/freshness**: MinTouches filter + touch-count color tiers; no volume or recency term.
12. **Typical number of zones**: with MinTouches = 2, a handful per chart (README/screenshots); no explicit
    cap besides a 2000-object limit.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: good and well documented; scale BarsMax up for M5/M15;
    GPL-3.0 is the main caution; H1/H4 context requires separate runs.
14. **Confidence**: **high** — README + LICENSE + behavior fully fetched.

---

## 7. ZigZag Support and Resistance Detection

1. **Name + author/handle**: ZigZag Support and Resistance Detection — **Tshidiso Ephraim Mpakanyane**
   (`protimetrader`).
2. **Category**: S/R (ZigZag pivots → lines; pivot-cluster highlighting).
3. **Source URL**: https://www.mql5.com/en/code/60339 [fetched]
4. **License**: `unknown` (no license stated on the CodeBase page).
5. **Output**: horizontal levels (lines) from pivots; open levels extend to the current bar, closed levels
   are broken; optional ZigZag line and labels; clusters of pivots highlighted. 26.5 KB mq5.
6. **Algorithm in my own words**: ZigZag with depth/deviation/backstep is run over a lookback; low pivots
   become support lines and high pivots resistance lines. A level that price has broken becomes "closed".
   Nearby converged pivots are highlighted as areas of interest, i.e. proto-zones. A later v2.0 added a
   `LookbackDays` parameter (mentioned in the comments).
7. **Repaint?** **yes/partial**. Standard ZigZag: the last leg can be redrawn until the next reversal is
   confirmed; "closed" status changes when broken. Historical display is rebuilt from scratch.
8. **How to make it causal**: use a confirmed ZigZag (fixed confirmation lag or reversal-confirmed legs);
   extend levels only from confirmed pivots; add an explicit width rule to turn lines into bands.
9. **Parameters + ATR**: InpLookback, InpDepth, InpDeviation, InpBackstep, InpDrawClosed, InpDrawZigZag,
   InpDrawLabels; v2 LookbackDays. **Not ATR** — classic ZigZag deviation is points/percent.
10. **Zone width logic**: none (lines only); zone conversion is an external decision.
11. **Strength/freshness**: pivot convergence (cluster) only; no touch count, no volume.
12. **Typical number of zones**: many lines; clusters fewer.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: weak as a zone generator by itself; useful as the simplest
    ZigZag-family baseline and as a pivot source. Needs an external width rule and MTF context.
14. **Confidence**: **high** — page fetched with parameter table.

---

## 8. SupplyDemandZones.mq5 (Miron Konkov)

1. **Name + author/handle**: SupplyDemandZones.mq5 — **Miron Konkov** (`mironkonkov30-design`).
2. **Category**: supply-demand (swing extremes → rectangles).
3. **Source URL**: https://github.com/mironkonkov30-design/mql5-indicators [fetched];
   raw source https://raw.githubusercontent.com/mironkonkov30-design/mql5-indicators/main/SupplyDemandZones.mq5 [fetched]
4. **License**: **MIT** (README: "MIT License — free to use, modify and distribute"; GitHub metadata
   "MIT license").
5. **Output**: rectangles, max 6 per type (input). Supply = from max(open,close) up to the swing bar's high;
   demand = from the low up to min(open,close); all extend 10 bars right of the last bar.
6. **Algorithm in my own words**: Scans the last `InpScanBars` (400) bars. A swing high/low is a bar whose
   high (low) is strictly above (below) all `InpSwing` (3) neighbors on both sides. Each such bar produces
   one rectangle from its body edge to its wick (supply above the body, demand below), capped per type. All
   objects are deleted and rebuilt on every new bar.
7. **Repaint?** **partial**. Swings need 3 bars to the right → 3-bar lag; the sliding scan window makes zones
   disappear when they fall out of range (expiry, not repaint); the rebuild is deterministic, so history
   matches live.
8. **How to make it causal**: trivially causal — process bar by bar with a 3-bar confirmation delay and keep
   your own persistent zone list instead of the sliding window.
9. **Parameters + ATR**: InpSwing 3, InpScanBars 400, InpMaxZones 6, colors. Fixed bar counts — **no ATR**.
10. **Zone width logic**: body-to-wick of the swing candle (neither ATR nor fixed pips).
11. **Strength/freshness**: none (no touches/volume/recency), only implicit recency via the scan window.
12. **Typical number of zones**: ≤ 6 supply + ≤ 6 demand = 12 max.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: simple readable baseline; too naive on M5 (3-bar swings are
    everywhere) but a good "minimal generator" control in the bake-off. No MTF.
14. **Confidence**: **high** — full source read (MIT, so reading is unrestricted).

---

## 9. Volume Profile Levels Indicator

1. **Name + author/handle**: Volume Profile Levels Indicator — **Olamide Daniel Adebayo** (`Stridz_z`).
2. **Category**: market profile / volume profile (POC + Value Area band).
3. **Source URL**: https://www.mql5.com/en/code/76610 [fetched]
4. **License**: `unknown` (no license stated on the CodeBase page).
5. **Output**: horizontal volume histogram sidebar + POC line + VAH/VAL lines. The Value Area is a
   horizontal band (zone-like); there are no rectangles. 13.3 KB mq5.
6. **Algorithm in my own words**: The recent lookback (default 200 bars) is sliced into equal price rows
   (default 24). Each bar's entire volume is assigned to the row containing its typical price (H+L+C)/3 —
   a deliberate simplification for bounded cost. The busiest row is the Point of Control. The Value Area is
   built outward row by row from the POC until it contains the chosen share of total volume (default 70%),
   using the standard TPO/volume value-area expansion rather than a fixed percentage of range. Rows are
   colored by whether up-closing or down-closing bars dominated. Rebuilds once per bar by default.
7. **Repaint?** **no future data**. POC/VA change bar to bar because the window slides (by design); with
   "update on new bar only" it refreshes at bar close. A fixed historical window recomputed later is
   deterministic.
8. **How to make it causal**: inherently causal; use closed bars only if stable values are wanted.
9. **Parameters + ATR**: LookbackBars 200, NumRows 24, VolumeType Tick/Real, ValueAreaPercent 70,
   UpdateOnNewBarOnly true, ShowProfile/POC/ValueArea, sidebar width 30 bars, colors. **Not ATR** — rows are
   equal-height divisions of the window's price range.
10. **Zone width logic**: the Value Area band (row-by-row expansion from POC); row height = range/rows.
11. **Strength/freshness**: volume concentration (POC prominence); no touch count.
12. **Typical number of zones**: 1 POC + 1 VA band per chart/window.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: good orthogonal candidate — acceptance zones (VA) vs
    rejection levels from swing tools. Caveats: MT5 FX "volume" is tick volume (the author states this);
    one band per chart, so H1/H4 context requires separate profiles per session/TF.
14. **Confidence**: **high** — page fetched with full input table and algorithm text.

---

## 10. Liquidity Zone Flips (HTF base-impulse + zone flip)

1. **Name + author/handle**: "From Novice to Expert: Detecting Liquidity Zone Flips Using MQL5" —
   **Clemence Benjamin** (`billionaire2024`); attached source.
2. **Category**: supply-demand zones + role flip (base-impulse, HTF detection).
3. **Source URL**: https://www.mql5.com/en/articles/21677 [fetched]
4. **License**: **restrictive** — page states verbatim: "Warning: All rights to these materials are reserved
   by MetaQuotes Ltd. Copying or reprinting of these materials in whole or in part is prohibited." Source is
   attached for reading; do not copy code.
5. **Output**: rectangles on the chart timeframe, detected on a chosen higher timeframe (default H1); green
   demand / red supply; flip changes color/role; reaction arrows; zones expire after `ExtendBars`.
6. **Algorithm in my own words**: On the selected HTF it looks for a base bar followed by an impulse bar:
   both bars same direction, impulse range ≥ `RatioMultiplier` (3.0) × base range. The base bar's high–low
   becomes the zone, with expiry = start + `ExtendBars` × HTF period. When a later bar closes beyond the
   zone AND that bar's range ≥ `ViolationMultiplier` (1.5) × zone height, the zone flips role (color swap,
   expiry extended from the violation, original start time kept). Reaction signals use engulfing / pin bar /
   inside-bar breakout at `signal_bar = 1` (last closed bar).
7. **Repaint?** **partial**, and there is an important replay discrepancy: a zone appears only after the
   impulse bar closes (≥ 1 HTF bar lag), and flips are evaluated only on the last closed bar during live
   operation. On a fresh attach it scans history and draws old zones but does **not** replay historical
   flips, so the historical picture differs from what the live chart evolved through.
8. **How to make it causal**: replay both detection and flips bar by bar from the start; create a zone only
   when the impulse bar closes; evaluate flips at every bar close; keep zone identity by start time.
9. **Parameters + ATR**: ZoneTimeframe H1, LookbackBars 1000, RatioMultiplier 3.0, ExtendBars 50,
   EnableZoneFlipping, ViolationMultiplier 1.5, colors. **Fixed ratios, not ATR** (though the zone height is
   used as the natural scale in the violation test).
10. **Zone width logic**: the base candle's high–low.
11. **Strength/freshness**: no touch count; time-based expiry; the flip is the structural event; one signal
    per zone.
12. **Typical number of zones**: not stated; with 1000 HTF bars and ratio 3.0, implied a few dozen created
    over history, most expired.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: very good conceptually — HTF (H1/H4) zone detection on an
    M15 chart is exactly this design. Main problems: restrictive license and the flip-replay bug that must
    be fixed in any reimplementation.
14. **Confidence**: **high** — full article and code path fetched.

---

## 11. SRSI — Support and Resistance Strength Indicator

1. **Name + author/handle**: "From Novice to Expert: Support and Resistance Strength Indicator (SRSI)" —
   **Clemence Benjamin** (`billionaire2024`); attached `_SRSI.mq5`.
2. **Category**: S/R zones (swing + test count).
3. **Source URL**: https://www.mql5.com/en/articles/17450 [fetched]
4. **License**: **restrictive** — same MetaQuotes warning: "All rights to these materials are reserved by
   MetaQuotes Ltd. Copying or reprinting of these materials in whole or in part is prohibited."
5. **Output**: rectangles for strong levels (top/bottom = price ± TestProximity) plus solid lines and labels
   (SS / SR); dashed lines and labels for weak levels (WS / WR).
6. **Algorithm in my own words**: A swing high (low) is a bar whose high (low) exceeds the 5 bars on each
   side. For each swing it counts "tests": later bars whose high or low comes within `InpTestProximity`
   (default 0.0007 price units, ≈ 7 pips on EURUSD) of the level. If tests ≥ `InpMinTests` (3) the level is
   strong and gets a zone of ± proximity; otherwise it is weak. Zones extend to the current time. All
   objects are cleared and rebuilt on start/new bar. Alerts are throttled to one per hour.
7. **Repaint?** **yes**. Swings need 5 future bars to confirm; the test count changes as new bars arrive;
   the whole object set is rebuilt each new bar, so the live sequence and the historical rebuild differ.
8. **How to make it causal**: confirm swings after 5 bars; count tests only from pivot+1 up to the current
   bar; freeze zones at bar close.
9. **Parameters + ATR**: InpLookBack 1000, InpTestProximity 0.0007 (fixed price units), InpMinTests 3,
   InpShowRectangles. **NOT ATR** — fixed pips. Commenters replaced proximity with ATR multiples
   (e.g. max(75/Digits, 0.10×ATR)), and the author approved the idea.
10. **Zone width logic**: fixed ± TestProximity (7 pips default) — symbol-dependent, not adaptive.
11. **Strength/freshness**: test count ≥ 3 → strong; no volume, no recency term.
12. **Typical number of zones**: many (1000-bar lookback, 5-bar swings, 3-test filter) — dozens on M15.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: medium. Simple and reimplementable, but fixed-pip widths and
    5-bar swing lag must be converted to ATR for M5/M15; no MTF context.
14. **Confidence**: **high** — article fetched, full algorithm and inputs published.

---

## 12. FXSSI Supply&Demand (closed source — benchmark)

1. **Name + author/handle**: Supply&Demand — **FXSSI** (FXSSI LTD).
2. **Category**: supply-demand (ZigZag + histogram levels).
3. **Source URL**: https://fxssi.com/supply-and-demand [fetched]
4. **License**: **proprietary freeware** — page footer: "©2026 fxssi.com All Rights Reserved"; free download
   for MT4/MT5; installation instructions require "Allow DLL imports"; no source provided.
5. **Output**: histogram bars representing levels above/below price (supply red above, demand green below);
   broken levels shown lighter (inactive); optional ZigZag overlay and peaks/lows dots.
6. **Algorithm in my own words** (as documented): ZigZag finds swings; significant highs/lows become
   supply/demand levels. The histogram height encodes strength based on how close price is to the level,
   scaled by a separate "bars used for histogram height" setting (visual scaling, not volume). ZigZag depth/
   backstep and bars-to-calculate are user inputs.
7. **Repaint?** **unknown** (closed source). ZigZag-based tools typically move the last leg until confirmed.
8. **How to make it causal**: not applicable without source; benchmark only.
9. **Parameters + ATR**: ZigZag depth/backstep, bars to calculate, histogram height %, bars for height,
   infill, display toggles, color presets. **Not ATR**.
10. **Zone width logic**: none — the level is a line/histogram, not a price band.
11. **Strength/freshness**: proximity-based histogram height; active/inactive after break.
12. **Typical number of zones**: many ZigZag-derived levels.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: cannot be re-implemented; useful only as a visual sanity
    benchmark. DLL import is a red flag for an automated research pipeline.
14. **Confidence**: **medium** — page fetched; internals unknown, repaint unverifiable.

---

## 13. Advanced Supply Demand (closed, paid — benchmark)

1. **Name + author/handle**: Advanced Supply Demand — **Bernhard Schweigert** (`bernardo33`).
2. **Category**: supply-demand (ATR-factor zone strength, MTF nested zones).
3. **Source URL**: https://www.mql5.com/en/market/product/20582 [fetched]
4. **License**: **proprietary commercial** — rent 58 USD / 3 months or 98 USD / year, 5 activations; no source.
5. **Output**: rectangles for supply/demand zones; MTF and nested (within higher-TF) zones; old zones shown;
   a counter of how many zones have been broken in a row; fake-breakout alerts; inner/outer price labels.
6. **Algorithm in my own words** (as documented): zones are built from candles with a proprietary formula.
   Two user factors control zone quality: a minimum "X-factor of price travel away" (in ATR) and a minimum
   "Y-factor" for zone size (in ATR); an oversized zone is clamped by a Max factor (ATR). A "minimum candles
   before a zone is printed" input adds a deliberate confirmation lag for live charts. The same factors are
   duplicated for the MTF zones, and zones nested inside higher-TF zones are flagged. Alerts cover zone hit,
   zone break, reversal candle, and fake breakout.
7. **Repaint?** **unknown** (closed source); the "min candles before a zone is printed" is a deliberate lag,
   not proof of causality either way.
8. **How to make it causal**: not applicable; but the X/Y-factor parameterization is a good template for a
   causal strength score (travel-away in ATR, size in ATR).
9. **Parameters + ATR**: Min candles, Min X-factor (ATR), Min Y-factor (zone size, ATR), Max factor (ATR),
   the same for MTF, alert options, max supply/demand zones, PIN. **ATR-based** — the clearest ATR-scaling
   of both zone size and strength in this survey.
10. **Zone width logic**: constrained by Y-factor (minimum) and Max factor (maximum), both in ATR units.
11. **Strength/freshness**: X-factor (price travel away in ATR) + broken-in-a-row counter + nested flag +
    fake-breakout detection.
12. **Typical number of zones**: user-capped by "show max number of supply/demand zones".
13. **Fit for EURUSD M5/M15 + H1/H4 context**: cannot be re-implemented (closed), but its X/Y-factor design
    is worth copying conceptually in the Python generator, and it is a strong benchmark reference.
14. **Confidence**: **high** for documented parameters (page fetched); internals unknown.

---

## 14. Supports And Resistances Lines (free, closed — benchmark)

1. **Name + author/handle**: Supports And Resistances Lines — **Francisco Gomes Da Silva**
   (`franciscogomes5`).
2. **Category**: S/R (fractal lines, optional tick-width zones).
3. **Source URL**: https://www.mql5.com/en/market/product/83772 [fetched] (MT4 sibling:
   https://www.mql5.com/en/market/product/95853 [NOT FETCHED — cite only])
4. **License**: **free download on MQL5 Market**; no license stated; closed source (`.ex5` only).
5. **Output**: horizontal support/resistance lines, with an optional zone width set in ticks; tops and
   bottoms identified automatically.
6. **Algorithm in my own words** (as documented): Fractals define tops/bottoms. Each new fractal bottom
   creates a support line (also when a bottom is lower than the previous one); each new fractal top creates
   a resistance line (also when a top is higher than the previous one). A "tick width" input turns the line
   into a support/resistance region instead of a bare line. The selling point is trading the empty gaps
   between levels.
7. **Repaint?** **partial/unknown**. Fractals need 2 bars to the right; lines accumulate and are not removed
   in the description; closed source → unverified.
8. **How to make it causal**: use fractals confirmed after 2 bars; build lines incrementally; no future data
   needed beyond the fractal window.
9. **Parameters + ATR**: fractal depth (standard MT5 Fractals semantics implied), tick width for the zone.
   **Not ATR** — fixed ticks.
10. **Zone width logic**: user-set tick width (fixed, symbol-dependent).
11. **Strength/freshness**: none beyond recency; no touch count, no volume.
12. **Typical number of zones**: many lines accumulate over history.
13. **Fit for EURUSD M5/M15 + H1/H4 context**: simple baseline; line→zone conversion is trivial (±ticks),
    but it is not adaptive, has no touch counting and no MTF.
14. **Confidence**: **medium** — page fetched; exact fractal/input semantics not listed (closed source).

---

## 15. PZ Support Resistance (closed, paid — benchmark)

1. **Name + author/handle**: PZ Support Resistance MT5 — **PZ TRADING SLU** (Arturo López Pérez).
2. **Category**: S/R lines (importance encoded as line thickness/darkness).
3. **Source URL**: https://www.mql5.com/en/market/product/1397 [NOT FETCHED — cite only];
   vendor page https://www.pointzero-trading.com/products/view/pzsupportresistance [NOT FETCHED — cite only]
   (both appeared in search results with quoted text).
4. **License**: **proprietary commercial** — 99 USD, 20 activations; no source.
5. **Output**: horizontal lines only; line thickness/darkness increases with the number of tests/importance;
   optional age labels; multi-timeframe (choose which TF's levels to read).
6. **Algorithm in my own words** (as advertised): iterates over "Max History Bars" to find levels "the same
   precision as a human eye would"; a sensitivity parameter controls how many lines are produced (higher =
   fewer); as levels are tested their importance grows and they are drawn thicker/darker; unimportant levels
   are removed; multi-timeframe levels can be read on one chart.
7. **Repaint?** **unknown** (closed source). Line thickness encodes a cumulative test count, so the visual
   state necessarily changes as tests accumulate; historical replay unverifiable.
8. **How to make it causal**: not applicable; benchmark/reference only. To reuse the idea causally: count
   tests up to the current bar and render width/importance as of that bar.
9. **Parameters + ATR**: sensitivity, Max History Bars, colors, labels, timeframe selection. **ATR not
   mentioned** — fixed.
10. **Zone width logic**: none (line width encodes importance); a band must be synthesized externally.
11. **Strength/freshness**: test count encoded as thickness/darkness; age labels; unimportant levels pruned.
12. **Typical number of zones**: few ("clean chart", higher sensitivity = fewer lines).
13. **Fit for EURUSD M5/M15 + H1/H4 context**: cannot be used directly (closed, paid); its MTF and
    test-count-to-importance ideas overlap Smart S/R Zones and PAZ.
14. **Confidence**: **low/medium** — pages not fetched; claims come from search-result excerpts of the
    vendor and MQL5 Market pages.

---

## Notes for the bake-off

- **Realistic to re-implement causally in Python in <200 lines**: Miron SupplyDemandZones (~40 lines:
  N-bar swing + body/wick rectangle), Volume Profile POC/VA (~80: bin volumes, expand to 70%), Smart S/R
  Zones core (~120: confirmed pivots + clustering + touch count), PAZ core (~130: ZigZag swings + ATR-
  tolerance clustering + centroid update), ATR Ranked (~150: pivots + ATR merge + 3-part score), Shved
  (~180: fractals + ATR zone build + verified/proven/broken state machine). Slightly over but feasible:
  ExMachina (impulse window + merge + touch tracking, ~150–180), SNR zigzag (needs a confirm-bars ZigZag,
  ~150), Liquidity Zone Flips (~120 but must replay flips, not just draw them), SRSI (~80 with the fixed-pip
  proximity converted to ATR).
- **License problems**: PAZ is GPL-3.0 (copyleft — a clean-room Python reimplementation of the *algorithm*
  is fine, but copying its code would infect the pipeline); SRSI and Liquidity Zone Flips are MetaQuotes
  articles with an explicit "all rights reserved / copying prohibited" notice — do not copy their code;
  MQL5 CodeBase pages state no license at all (treat as reference-only, do not redistribute source); FXSSI,
  PZ, Advanced Supply Demand and Supports And Resistances Lines are closed/proprietary — benchmarks only,
  never part of the Python pipeline.
- **Known duplicates / lineages**: (a) swing-clustering family — PAZ ≈ Smart S/R Zones ≈ ATR Ranked ≈
  Miron's SupplyDemandZones (same idea, different polish); (b) ZigZag family — SNR zigzag ⊃ ZigZag SNR
  Detection, and FXSSI is the closed ZigZag+histogram variant; (c) base-impulse family — ExMachina (same-TF
  multi-bar impulse) vs Liquidity Zone Flips (HTF base-impulse + role flip); (d) Shved is the ancestor of
  the paid MQL Ideas "Support/Resistance Zones" dashboard (the vendor page states it is based on Shved).
- **Suggested core set (5)**: Shved (fractal + ATR, MTF, state machine), Smart S/R Zones MT4 (pivot cluster
  + touch rank + HTF overlay), ExMachina (impulse, ATR-normalized), SNR zigzag (causal by design, SBR/RBS),
  Volume Profile Levels (orthogonal POC/VA). Optional 6th/7th: PAZ (ATR clustering, GPL caution) and
  Liquidity Zone Flips (HTF context, restrictive license).
- **Parameter normalization warning**: only Shved, ExMachina, ATR Ranked, PAZ, Smart S/R (claimed), SNR
  and Advanced Supply Demand scale with ATR/volatility; SRSI and Supports And Resistances Lines use fixed
  pips/ticks. Convert everything to ATR multiples before comparing zone widths on EURUSD.
- **Repaint handling common rule**: every candidate here creates zones after a confirmation lag (fractal 2
  bars, pivot N bars, impulse 1–3 bars, ZigZag confirm). The Python generators must process bar-by-bar and
  freeze zone sets at bar close; any tool that rebuilds all objects from scratch each bar (SRSI, Miron,
  Liquidity Zone Flips, Smart S/R, ATR Ranked) must be replayed rather than snapshotted, or the bake-off
  will measure hindsight rather than live behavior.
