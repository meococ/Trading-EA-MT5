# INDICATOR SURVEY — support/resistance ZONE generators (T-PAPRO-ZONE-1)

Purpose: candidate zone GENERATORS for the PA-PRO preregistered zone-physics bake-off on EURUSD M5/M15 with H1/H4 context, which needs >= 12 generator candidates. Provenance: this file is a synthesis of four research files already on disk in this folder — `_survey_mt45.md` (15 MT4/MT5 candidates), `_survey_tv.md` (15 TradingView scripts), `_survey_python_academic.md` (9 Python/quant methods + 10 academic items) and `_legacy_kills.md` (18 legacy kill entries). Those files were produced by web-research sub-agents on 2026-09-20; the confidence labels, licence statuses and URL fetch markers below are carried over from the source files and were **not re-verified here**. No code was copied from any source: every algorithm below is paraphrased. This task computes no outcomes: no bounce/break rates, no returns, no win rates — that measurement belongs to the preregistered R01 physics run.

## 0. Reading rules

- **Licence / redistribution.** No source code may be copied from a restrictive licence into this repo; only algorithms, paraphrased in our own words, travel. Restrictive families: CC BY-NC-SA 4.0 (non-commercial + share-alike), GPL-3.0 / MPL 2.0 (copyleft), the MetaQuotes articles ("all rights reserved … copying … prohibited"), MQL5 CodeBase (no licence stated → "source available for reading", reference-only), MQL5 Market and vendor binaries (proprietary → benchmark only). Any future code reuse must respect the source licence; a clean-room re-implementation of the algorithm is the intended route.
- **Licence-status wording.** Where a source marks a licence unverified, this file writes `unknown (source: unverified)`. An `unknown` licence is never upgraded here, and a `[NOT FETCHED — cite only]` URL stays marked as such.
- **Confidence legend** (carried from `_survey_mt45.md`): **high** = page fetched and algorithm/parameters described on that page, or source read; **medium** = page fetched but internals partly unknown (closed source), or cite-only with strong corroboration; **low** = cite-only and unverified. `[fetched]` / `[NOT FETCHED — cite only]` tags mark how the URL was reached in the source session.
- **Line → zone rule.** A tool that outputs lines is not a zone generator. Before it may enter the bake-off, its line must be converted to a ZONE: a band with a stated width rule; the default conversion used here is ±0.25×ATR(14, TF) around the line (the common choice in `_survey_python_academic.md`), with the band inheriting the tool's strength/age metadata. The conversion is provenance, not part of the source algorithm.
- **No outcomes.** Nothing in this file reports or predicts bounce/break rates, returns or win rates. Section 5 explains why the legacy kill metrics do not answer the R01 question.

---

## 1. MT4/MT5 indicators

15 candidates. MQL5 CodeBase pages state no licence name (MQL5.com terms govern the site); MQL5 Market products are closed binaries unless stated otherwise. Line-only tools are marked and require the §0 zone conversion.

### 1.1 Shved Supply and Demand (v1.7)
- output: horizontal rectangles with type/strength labels (weak, untested, verified, proven, broken); MTF mode (v1.5+); buffers expose zone strength/type (v1.7).
- algorithm: Bill Williams-style fractal highs/lows on the selected TF; each significant fractal becomes a zone extended with the ATR indicator; zones classified by subsequent price behaviour (verified = touched but not broken; proven = at least four unsuccessful tests; broken = close through); history mode reconstructs the past state.
- repaint: **partial** — a fractal needs 2 bars to its right, so the zone appears 2+ bars after the pivot; zone status evolves with tests/breaks; no future bars beyond the fractal window.
- causalize: confirm fractals after 2 closed bars; rebuild the state machine left-to-right bar by bar; apply status transitions only at bar close; never use history mode for replay.
- params/ATR: fractal depth/period, ATR period and multipliers, per-type toggles, TF, prefix, alerts. **ATR-scaled** (page: "uses fractals and ATR indicator"); exact multipliers not published.
- width: fractal level ± an ATR-derived amount (exact multipliers unverified).
- strength/freshness: touch/break counts drive weak/untested/verified/proven/broken; "proven" requires 4 failed breaks; no volume component.
- zones/chart: not stated; `ASSUMPTION:` 5–20 active on M15 (source assumption); many across history if weak zones are shown.
- license: `unknown (source: unverified)` — no licence stated on the CodeBase page.
- URL: https://www.mql5.com/en/code/29395 [fetched]
- fit: strong — built-in MTF option, ATR-scaled widths and a proven/verified ranking map well to the bake-off; raise fractal depth on M5 to avoid noise.
- confidence: **high** (page fetched; exact ATR multipliers unverified).

### 1.2 Smart S/R Zones MT4
- output: rectangles (zones) with on-chart touch-count labels (e.g. "x8"); optional HTF zones overlaid in a distinct colour; zones far from price hidden.
- algorithm: real swing pivots (configurable pivot strength, not N-bar highest/lowest); nearby pivots clustered into zones; each zone ranked by actual test count; adaptive thickness so zones never overlap; distance filter; optional HTF overlay (auto-disabled if redundant); proximity alerts with cooldown.
- repaint: **partial** — pivots need `strength` right-side bars (creation lag); touch counts/labels update; the distance filter makes zones appear/disappear as price moves; no future data.
- causalize: confirm pivots after `strength` closed bars; add pivots to clusters only at confirmation; snapshot cluster membership and touch counts at each bar close; compute the distance filter from the last close.
- params/ATR: pivot strength, cluster tolerance, max zones, HTF timeframe, distance filter, alert cooldown, colours. "Adaptive zone thickness" but **ATR is not stated** — likely point/pip-based (`ASSUMPTION`, unverified).
- width: adaptive thickness + cluster tolerance; formula not published.
- strength/freshness: direct touch count per zone; recency via the distance filter.
- zones/chart: implied small (readable-chart design; screenshot shows a handful).
- license: `unknown (source: unverified)` — no licence stated; author advertises "Free, full source".
- URL: https://www.mql5.com/en/code/76075 [fetched]
- fit: strong — built-in HTF overlay and touch-count ranking match the "M5/M15 with H1/H4 context" pattern; verify the thickness basis before comparing widths.
- confidence: **high** for features; **medium** for width/ATR internals (not on the page).

### 1.3 ExMachina Supply & Demand Zones v2.0
- output: supply/demand rectangles with labels (type, freshness ●/[T], strength, touch count), optional midline, right-extension, dashboard panel.
- algorithm: scan last N bars (default 1000); over a 2–3 bar window sum total range (H−L) or net move (C−O) and compare with ATR(14); a move ≥ Min Impulse (default 1.0×ATR) is an impulse and the base candle before it becomes a supply/demand zone; same-type zones at similar prices merge (Merge Distance 0.5×ATR); strength score = impulse size relative to ATR; freshness flag and touch count update as price interacts; proximity alerts default 50 points.
- repaint: **partial** — the zone exists only after the 2–3 bar impulse window closes; freshness/touch labels update live; merged zone identity may be rewritten; no future bars.
- causalize: emit only zones whose impulse window closed at ≤ t; recompute touches from bars ≤ t; merge only at bar close and freeze zone IDs; disable theme/dashboard in research runs.
- params/ATR: Lookback 1000, Min Impulse 1.0×ATR, ATR Period 14, Multi-Candle Window 3, Use Range vs Body, Merge Distance 0.5×ATR, Show Only Fresh, proximity 50 points, visual toggles. Thresholds **ATR-scaled**; proximity in points.
- width: the base candle's full range (or body per "Use Range (vs Body)"); merged zones union the participants.
- strength/freshness: impulse size ÷ ATR, touch count, fresh vs tested status.
- zones/chart: page says "if you see fewer than 5 zones on H1, lower Min Impulse to 0.8" → order ~5–20 on H1; more on M5.
- license: `unknown (source: unverified)` — no licence stated on the CodeBase page.
- URL: https://www.mql5.com/en/code/70709 [fetched]
- fit: good — author recommends H1/H4 and ATR-normalises everything, but M5 over-detects unless Min Impulse is raised and merging is active; suppress theme/dashboard for clean comparisons.
- confidence: **high** (page fetched with full parameter table and algorithm text).

### 1.4 Support Resistance zig zag based (SNR.mq5)
- output: rectangular zones with role colours (support/resistance → SBR/RBS after break); dashboard market-bias gauge; retest alerts. Screenshot is BTCUSD M5.
- algorithm: ZigZag core finds swing highs/lows; a "Confirm Bars" input validates extremes before drawing (explicit anti-repaint design); width normalized against historical average price movement; a candle close beyond a zone flips support→SBR / resistance→RBS unless flipping is disabled (then broken zones are deleted); "Min Move Away" multiplier must be travelled before a zone activates, and alerts only fire on a later retest; overlap resolution keeps most-extreme or newest; dashboard computes the bullish/bearish ratio from recent ZigZag legs.
- repaint: **no/partial** — author explicitly designed "Anti-Flicker & Repaint Safety: uses a confirmation delay to validate pivot points before drawing zones"; standard ZigZag caveat applies to the in-progress leg, but drawn zones wait for confirmation and flips act on closes.
- causalize: keep Confirm Bars ≥ 2; evaluate on closed bars; apply flips only at bar close; treat Min Move Away activation as an event on the bar the distance is reached.
- params/ATR: ZigZag depth/deviation/backstep, Confirm Bars, Min Move Away, width normalization, overlap mode (Most Extreme / Newest), alerts. Width normalization is volatility-based (average movement), effectively ATR-like but **not stated as ATR**.
- width: proportional zone normalized against historical average price movements.
- strength/freshness: freshness + retest after Min Move Away; overlap resolution; dashboard bias; no explicit touch counter.
- zones/chart: not stated; implied a handful (flip logic removes/converts zones).
- license: `unknown (source: unverified)` — no licence stated on the CodeBase page.
- URL: https://www.mql5.com/en/code/76644 [fetched]
- fit: good — designed and screenshotted on M5, causal by construction; **no MTF input**, so H1/H4 context must be produced by running the same generator on H4 data in Python.
- confidence: **high** (page fetched with explicit algorithm/feature list).

### 1.5 ATR Ranked Support and Resistance Zones
- output: horizontal price rectangles for only the highest-ranked zones, with a strength-score label; zones below current price shown as support, above as resistance.
- algorithm: start from confirmed pivot highs/lows; merge nearby pivots using an ATR-based distance; score each area from three parts — grouped reaction count, post-reaction price travel, and recency of the last test; draw only the highest-ranked; support/resistance role assigned by position vs current price (author notes this is a simplification and suggests a confirmed break-and-retest instead).
- repaint: **partial** — pivots need right-side bars; the three-part score and recency change every bar; the role flips as price crosses; a full scan reproduces the final state, not the live sequence.
- causalize: confirm pivots after a fixed lag; compute the score from past data only; replace role-by-position with an event-based break+retest transition (author's own suggestion).
- params/ATR: pivot lookback, ATR period and merge multiplier, max zones drawn, score threshold. **ATR-scaled** merging.
- width: ATR-based merge distance (cluster span), not fixed pips.
- strength/freshness: three-part score = reaction count + post-reaction travel + recency.
- zones/chart: top-ranked only → few (single digits to low tens).
- license: `unknown (source: unverified)` — no licence stated; author says "shared for educational purposes".
- URL: https://www.mql5.com/en/code/74421 [fetched]
- fit: conceptually good (ATR-normalized clustering + strength score), but pivot lag and role-by-position must be fixed; explicitly a starting-point code, not a finished tool.
- confidence: **high** (page fetched; algorithm described by the author).

### 1.6 Price Action Zones (PAZ) MT4
- output: coloured rectangles; colour intensity = touch count (≤2 RosyBrown weak, 3–4 Chocolate, 5–6 OrangeRed, >6 Red); zones extend `ZoneExtendBars` into the right; min-touch filter.
- algorithm: ZigZag-style swing detection (ExtDepth/ExtDeviation/ExtBackstep); a swing joins a zone if its distance to the zone centroid ≤ `eps = MergeATR × ATR(14)`, otherwise it opens a new zone; adding a swing updates the zone centroid and top/bottom bounds; zones with fewer than `MinTouches` reactions are hidden; objects redraw only when the zone count changes; scan window `BarsMax` bars.
- repaint: **partial** — swings need ExtDepth bars to the right; joining a new swing updates the whole rectangle retroactively; the sliding BarsMax window drops old zones (expiry, not repaint); a deterministic rebuild gives a consistent final picture.
- causalize: confirm swings after ExtDepth bars; add swings to clusters only at confirmation; snapshot zone bounds and touch counts at each bar close.
- params/ATR: TimeFrame, BarsMax 168, ExtDepth 7, ExtDeviation 3, ExtBackstep 4, MergeATR 0.8, ATRPeriod 14, MinTouches 2, ZoneExtendBars 500, colours. **ATR-based tolerance** documented explicitly.
- width: cluster span = min/max of member swings; membership governed by MergeATR × ATR.
- strength/freshness: MinTouches filter + touch-count colour tiers; no volume, no recency term.
- zones/chart: with MinTouches = 2, a handful (README/screenshots); no explicit cap besides a 2000-object limit.
- license: **GNU GPL v3** (LICENSE file fetched; README footer says "All rights reserved" — conflicting statements; treat as GPL-3.0).
- URL: https://github.com/capitafix/Price-Action-Zones-Indicator [fetched]; LICENSE https://raw.githubusercontent.com/capitafix/Price-Action-Zones-Indicator/main/LICENSE [fetched]
- fit: good and well documented; scale BarsMax up for M5/M15; GPL-3.0 is the main caution; H1/H4 context requires separate runs.
- confidence: **high** (README + LICENSE + behaviour fully fetched).

### 1.7 ZigZag Support and Resistance Detection
- output: horizontal levels (lines) from pivots; open levels extend to the current bar, closed levels are broken; optional ZigZag line and labels; clusters of converged pivots highlighted (proto-zones). **Line tool → §0 zone conversion required.**
- algorithm: ZigZag (depth/deviation/backstep) is run over a lookback; low pivots become support lines, high pivots resistance lines; a level price has broken becomes "closed"; nearby converged pivots are highlighted as areas of interest; v2.0 added `LookbackDays`.
- repaint: **yes/partial** — standard ZigZag: the last leg can be redrawn until the next reversal is confirmed; "closed" status changes on break; historical display is rebuilt from scratch.
- causalize: use a confirmed ZigZag (fixed confirmation lag or reversal-confirmed legs); extend levels only from confirmed pivots; add an explicit width rule to turn lines into bands.
- params/ATR: InpLookback, InpDepth, InpDeviation, InpBackstep, InpDrawClosed, InpDrawZigZag, InpDrawLabels; v2 LookbackDays. **Not ATR** — classic deviation in points/percent.
- width: none (lines only); zone conversion is an external decision.
- strength/freshness: pivot convergence (cluster) only; no touch count, no volume.
- zones/chart: many lines; clusters fewer.
- license: `unknown (source: unverified)` — no licence stated on the CodeBase page.
- URL: https://www.mql5.com/en/code/60339 [fetched]
- fit: weak as a zone generator by itself; useful as the simplest ZigZag-family baseline and as a pivot source; needs an external width rule and MTF context.
- confidence: **high** (page fetched with parameter table).

### 1.8 SupplyDemandZones.mq5 (Miron Konkov)
- output: rectangles, max 6 per type (input). Supply = from max(open,close) up to the swing bar's high; demand = from the low up to min(open,close); all extend 10 bars right of the last bar.
- algorithm: scan the last `InpScanBars` (400) bars; a swing high/low is a bar whose high (low) is strictly above (below) all `InpSwing` (3) neighbours on both sides; each such bar produces one rectangle from its body edge to its wick (supply above the body, demand below), capped per type; all objects deleted and rebuilt on every new bar.
- repaint: **partial** — swings need 3 right-side bars; the sliding scan window expires old zones; the rebuild is deterministic, so history matches live.
- causalize: trivially causal — process bar by bar with a 3-bar confirmation delay and keep a persistent zone list instead of the sliding window.
- params/ATR: InpSwing 3, InpScanBars 400, InpMaxZones 6, colours. Fixed bar counts — **no ATR**.
- width: body-to-wick of the swing candle (neither ATR nor fixed pips).
- strength/freshness: none (no touches/volume/recency); only implicit recency via the scan window.
- zones/chart: ≤ 6 supply + ≤ 6 demand = 12 max.
- license: **MIT** (README: "MIT License — free to use, modify and distribute"; GitHub metadata "MIT license").
- URL: https://github.com/mironkonkov30-design/mql5-indicators [fetched]; raw source https://raw.githubusercontent.com/mironkonkov30-design/mql5-indicators/main/SupplyDemandZones.mq5 [fetched]
- fit: simple readable baseline; too naive on M5 (3-bar swings are everywhere) but a good "minimal generator" control; no MTF.
- confidence: **high** (full source read; MIT so reading is unrestricted).

### 1.9 Volume Profile Levels Indicator
- output: horizontal volume histogram sidebar + POC line + VAH/VAL lines; the Value Area is a horizontal band (zone-like); no rectangles.
- algorithm: the recent lookback (default 200 bars) is sliced into equal price rows (default 24); each bar's entire volume is assigned to the row containing its typical price (H+L+C)/3 (a deliberate simplification for bounded cost); the busiest row is the POC; the Value Area is built outward row by row from the POC until it contains the chosen share of total volume (default 70%), using the standard TPO/volume expansion; rows are coloured by up/down-closing dominance; rebuilds once per bar by default.
- repaint: **no future data** — POC/VA change bar to bar because the window slides (by design); with "update on new bar only" it refreshes at bar close; a fixed historical window recomputed later is deterministic.
- causalize: inherently causal; use closed bars only for stable values.
- params/ATR: LookbackBars 200, NumRows 24, VolumeType Tick/Real, ValueAreaPercent 70, UpdateOnNewBarOnly true, display toggles, sidebar width 30 bars, colours. **Not ATR** — rows are equal-height divisions of the window's price range.
- width: the Value Area band (row-by-row expansion from the POC); row height = range/rows.
- strength/freshness: volume concentration (POC prominence); no touch count.
- zones/chart: 1 POC + 1 VA band per chart/window.
- license: `unknown (source: unverified)` — no licence stated on the CodeBase page.
- URL: https://www.mql5.com/en/code/76610 [fetched]
- fit: good orthogonal candidate — acceptance zones (VA) vs rejection levels from swing tools; MT5 FX "volume" is tick volume (author states this); one band per chart, so H1/H4 context needs separate profiles per session/TF.
- confidence: **high** (page fetched with full input table and algorithm text).

### 1.10 Liquidity Zone Flips (HTF base-impulse + zone flip)
- output: rectangles on the chart timeframe, detected on a chosen higher timeframe (default H1); green demand / red supply; flip changes colour/role; reaction arrows; zones expire after `ExtendBars`.
- algorithm: on the selected HTF look for a base bar followed by an impulse bar — both same direction, impulse range ≥ `RatioMultiplier` (3.0) × base range; the base bar's high–low becomes the zone, with expiry = start + `ExtendBars` × HTF period; when a later bar closes beyond the zone AND its range ≥ `ViolationMultiplier` (1.5) × zone height, the zone flips role (colour swap, expiry extended from the violation, original start time kept); reaction signals use engulfing / pin bar / inside-bar breakout at `signal_bar = 1` (last closed bar).
- repaint: **partial**, with an important replay discrepancy — a zone appears only after the impulse bar closes (≥ 1 HTF bar lag), and flips are evaluated only on the last closed bar during live operation; on a fresh attach it scans history and draws old zones but does **not** replay historical flips, so the historical picture differs from the live evolution.
- causalize: replay both detection and flips bar by bar from the start; create a zone only when the impulse bar closes; evaluate flips at every bar close; keep zone identity by start time.
- params/ATR: ZoneTimeframe H1, LookbackBars 1000, RatioMultiplier 3.0, ExtendBars 50, EnableZoneFlipping, ViolationMultiplier 1.5, colours. **Fixed ratios, not ATR** (zone height is the natural scale in the violation test).
- width: the base candle's high–low.
- strength/freshness: no touch count; time-based expiry; the flip is the structural event; one signal per zone.
- zones/chart: not stated; with 1000 HTF bars and ratio 3.0, implied a few dozen created over history, most expired.
- license: **restrictive** — page states verbatim: "Warning: All rights to these materials are reserved by MetaQuotes Ltd. Copying or reprinting of these materials in whole or in part is prohibited." Source attached for reading; do not copy code.
- URL: https://www.mql5.com/en/articles/21677 [fetched]
- fit: very good conceptually — HTF (H1/H4) zone detection on an M15 chart is exactly this design; main problems are the restrictive licence and the flip-replay behaviour that must be fixed in any reimplementation.
- confidence: **high** (full article and code path fetched).

### 1.11 SRSI — Support and Resistance Strength Indicator
- output: rectangles for strong levels (top/bottom = price ± TestProximity) plus solid lines and labels (SS/SR); dashed lines and labels for weak levels (WS/WR).
- algorithm: a swing high (low) is a bar whose high (low) exceeds the 5 bars on each side; for each swing count "tests" — later bars whose high or low comes within `InpTestProximity` (default 0.0007 price units, ≈ 7 pips on EURUSD) of the level; tests ≥ `InpMinTests` (3) → strong, with a zone of ± proximity, otherwise weak; zones extend to current time; all objects cleared and rebuilt on start/new bar; alerts throttled to one per hour.
- repaint: **yes** — swings need 5 future bars to confirm; the test count changes as new bars arrive; the whole object set is rebuilt each new bar, so the live sequence and the historical rebuild differ.
- causalize: confirm swings after 5 bars; count tests only from pivot+1 to the current bar; freeze zones at bar close.
- params/ATR: InpLookBack 1000, InpTestProximity 0.0007 (fixed price units), InpMinTests 3, InpShowRectangles. **NOT ATR** — commenters replaced proximity with ATR multiples (e.g. max(75/Digits, 0.10×ATR)) and the author approved the idea.
- width: fixed ± TestProximity (7 pips default) — symbol-dependent, not adaptive.
- strength/freshness: test count ≥ 3 → strong; no volume, no recency term.
- zones/chart: many (1000-bar lookback, 5-bar swings, 3-test filter) — dozens on M15.
- license: **restrictive** — same MetaQuotes notice: "All rights to these materials are reserved by MetaQuotes Ltd. Copying or reprinting of these materials in whole or in part is prohibited."
- URL: https://www.mql5.com/en/articles/17450 [fetched]
- fit: medium — simple and reimplementable, but fixed-pip widths and the 5-bar swing lag must be converted to ATR for M5/M15; no MTF context.
- confidence: **high** (article fetched; full algorithm and inputs published).

### 1.12 FXSSI Supply&Demand (closed source — benchmark only)
- output: histogram bars representing levels above/below price (supply red above, demand green below); broken levels lighter (inactive); optional ZigZag overlay and peak/low dots.
- algorithm (as documented): ZigZag finds swings; significant highs/lows become supply/demand levels; histogram height encodes strength based on how close price is to the level, scaled by a separate "bars used for histogram height" setting (visual scaling, not volume); ZigZag depth/backstep and bars-to-calculate are inputs.
- repaint: **unknown** (closed source); ZigZag-based tools typically move the last leg until confirmed.
- causalize: not applicable without source; benchmark only.
- params/ATR: ZigZag depth/backstep, bars to calculate, histogram height %, bars for height, infill, display toggles, colour presets. **Not ATR**.
- width: none — the level is a line/histogram, not a price band.
- strength/freshness: proximity-based histogram height; active/inactive after break.
- zones/chart: many ZigZag-derived levels.
- license: **proprietary freeware** — page footer "©2026 fxssi.com All Rights Reserved"; free MT4/MT5 download; installation requires "Allow DLL imports"; no source.
- URL: https://fxssi.com/supply-and-demand [fetched]
- fit: cannot be re-implemented; useful only as a visual sanity benchmark; DLL import is a red flag for an automated research pipeline.
- confidence: **medium** (page fetched; internals unknown, repaint unverifiable).

### 1.13 Advanced Supply Demand (closed, paid — benchmark only)
- output: rectangles for supply/demand zones; MTF and nested (within higher-TF) zones; old zones shown; a counter of zones broken in a row; fake-breakout alerts; inner/outer price labels.
- algorithm (as documented): zones built from candles with a proprietary formula; two user factors control zone quality — a minimum "X-factor of price travel away" (in ATR) and a minimum "Y-factor" for zone size (in ATR); an oversized zone is clamped by a Max factor (ATR); a "minimum candles before a zone is printed" input adds a deliberate confirmation lag; the same factors are duplicated for MTF zones; zones nested inside higher-TF zones are flagged; alerts cover zone hit, break, reversal candle, fake breakout.
- repaint: **unknown** (closed source); the "min candles before a zone is printed" is a deliberate lag, not proof either way.
- causalize: not applicable; but the X/Y-factor parameterization is a good template for a causal strength score (travel-away in ATR, size in ATR).
- params/ATR: Min candles, Min X-factor (ATR), Min Y-factor (zone size, ATR), Max factor (ATR), the same for MTF, alert options, max supply/demand zones, PIN. **ATR-based** — the clearest ATR-scaling of both zone size and strength in this survey.
- width: constrained by Y-factor (minimum) and Max factor (maximum), both in ATR units.
- strength/freshness: X-factor (price travel away in ATR) + broken-in-a-row counter + nested flag + fake-breakout detection.
- zones/chart: user-capped by "show max number of supply/demand zones".
- license: **proprietary commercial** — rent 58 USD / 3 months or 98 USD / year, 5 activations; no source.
- URL: https://www.mql5.com/en/market/product/20582 [fetched]
- fit: cannot be re-implemented (closed), but its X/Y-factor design is worth copying conceptually in the Python generator; strong benchmark reference.
- confidence: **high** for documented parameters (page fetched); internals unknown.

### 1.14 Supports And Resistances Lines (free, closed — benchmark only)
- output: horizontal support/resistance lines, with an optional zone width set in ticks; tops and bottoms identified automatically. **Line tool → §0 zone conversion required.**
- algorithm (as documented): fractals define tops/bottoms; each new fractal bottom creates a support line (also when a bottom is lower than the previous one); each new fractal top creates a resistance line (also when a top is higher than the previous one); a "tick width" input turns the line into a region; the selling point is trading the empty gaps between levels.
- repaint: **partial/unknown** — fractals need 2 right-side bars; lines accumulate and are not removed in the description; closed source → unverified.
- causalize: use fractals confirmed after 2 bars; build lines incrementally; no future data beyond the fractal window.
- params/ATR: fractal depth (standard MT5 Fractals semantics implied), tick width for the zone. **Not ATR** — fixed ticks.
- width: user-set tick width (fixed, symbol-dependent).
- strength/freshness: none beyond recency; no touch count, no volume.
- zones/chart: many lines accumulate over history.
- license: **free download on MQL5 Market**; no licence stated; closed source (`.ex5` only).
- URL: https://www.mql5.com/en/market/product/83772 [fetched] (MT4 sibling https://www.mql5.com/en/market/product/95853 [NOT FETCHED — cite only])
- fit: simple baseline; line→zone conversion is trivial (±ticks), but it is not adaptive, has no touch counting and no MTF.
- confidence: **medium** (page fetched; exact fractal/input semantics not listed, closed source).

### 1.15 PZ Support Resistance (closed, paid — benchmark only)
- output: horizontal lines only; line thickness/darkness increases with the number of tests/importance; optional age labels; multi-timeframe (choose which TF's levels to read). **Line tool → §0 zone conversion required.**
- algorithm (as advertised): iterate over "Max History Bars" to find levels "the same precision as a human eye would"; a sensitivity parameter controls how many lines are produced (higher = fewer); as levels are tested their importance grows and they are drawn thicker/darker; unimportant levels are removed; MTF levels can be read on one chart.
- repaint: **unknown** (closed source); line thickness encodes a cumulative test count, so the visual state necessarily changes as tests accumulate; historical replay unverifiable.
- causalize: not applicable; benchmark/reference only. To reuse the idea causally: count tests up to the current bar and render width/importance as of that bar.
- params/ATR: sensitivity, Max History Bars, colours, labels, timeframe selection. **ATR not mentioned** — fixed.
- width: none (line width encodes importance); a band must be synthesized externally.
- strength/freshness: test count encoded as thickness/darkness; age labels; unimportant levels pruned.
- zones/chart: few ("clean chart"; higher sensitivity = fewer lines).
- license: **proprietary commercial** — 99 USD, 20 activations; no source.
- URL: https://www.mql5.com/en/market/product/1397 [NOT FETCHED — cite only]; vendor page https://www.pointzero-trading.com/products/view/pzsupportresistance [NOT FETCHED — cite only]
- fit: cannot be used directly (closed, paid); its MTF and test-count-to-importance ideas overlap Smart S/R Zones and PAZ.
- confidence: **low/medium** — pages not fetched; claims come from search-result excerpts of the vendor and MQL5 Market pages.

---

## 2. TradingView open-source scripts

15 candidates. **TradingView built-in studies (#2.13–#2.15) are proprietary and are listed here for algorithm reference only; their code cannot be reused and only the public documentation may inform a re-implementation.** TradingView script pages do not expose licence text in fetched HTML; the official Pine docs state verbatim (fetched at <https://www.tradingview.com/pine-script-docs/writing/publishing/>): "All open-source scripts on TradingView use the Mozilla Public License 2.0 by default. Authors wanting to use alternative licenses can specify them in the source code." Licences verified from mirrored source headers: #2.1, #2.2, #2.7, #2.10 = CC BY-NC-SA 4.0; #2.5 = MPL 2.0; #2.6 inferred MPL 2.0 (same author/engine). All other licences `unknown (source: unverified)`.

### 2.1 Support and Resistance Levels with Breaks [LuxAlgo]
- output: two horizontal lines (last usable pivot high = resistance, last pivot low = support) plus `B` / `Bull Wick` / `Bear Wick` break labels. No band. **Line tool → §0 zone conversion required.**
- algorithm: `ta.pivothigh(leftBars, rightBars)` / `ta.pivotlow`, hold the last non-na value, plot with a bar offset so the line visually starts at the pivot bar; break detection = close crossing the level; filters: a volume oscillator (EMA 5 vs EMA 10 of volume, percent spread) above `volumeThresh`, or a wick-asymmetry condition; alerts both directions.
- repaint: **no `security()`, no lookahead**; `max_bars_back=1000`; the pivot value is only known `rightBars+1` bars after the pivot bar (the source also indexes the pivot result by `[1]`), so historical bars are redrawn at that confirmation moment — normal, bounded lag; the current bar's cross can flicker intrabar.
- causalize: level becomes usable at bar `pivot_index + rightBars + 1`; evaluate breaks on closed bars only; keep the level frozen until a newer pivot replaces it; the Pine offset is cosmetic and irrelevant to a Python port.
- params/ATR: `leftBars=15`, `rightBars=15`, `volumeThresh=20` (%), `toggleBreaks`. **No ATR at all**; volume EMAs 5/10 substitute for a strength filter.
- width: none — single price lines (conversion external).
- strength/freshness: none beyond the volume filter; a level is implicitly "fresh" until first cross, then stays replaced by the next pivot.
- zones/chart: 2 lines.
- license: **CC BY-NC-SA 4.0** (mirrored source header quoted: "This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)"; "© LuxAlgo").
- URL: https://www.tradingview.com/script/JDFoWQbL-Support-and-Resistance-Levels-with-Breaks-LuxAlgo/ [fetched]; mirror https://gist.github.com/themodernpk/5b5b4997229643d423da1bbddc425964 [NOT FETCHED — cite only]
- fit: usable only as a baseline level generator (15 right bars ≈ 75 min lag on M5); no zones, no HTF logic; too thin for the bake-off.
- confidence: **high** — full source read via mirror; licence header seen verbatim.

### 2.2 Support & Resistance Signals MTF [LuxAlgo]
- output: S/R zones (boxes; `max_boxes_count=500, max_lines_count=500, max_labels_count=500`), swing lines, and labelled signals; detection runs on a user-chosen timeframe (default = chart), so H1/H4 zones can be drawn on M5.
- algorithm: swing highs/lows are detected with `Detection Length` on the detection timeframe; each becomes a level/zone; events: **breakout** = close beyond the level (volume of the breaking bar is reported but not used as a filter); **test** = touch of the zone; **retest** = breach then return; **rejection** = pin bar with high volume at a level; optional "check previous historical level" keeps more levels alive; an "Avoid False Breakouts" filter exists; documented as an extended version of #2.1.
- repaint: MTF detection is almost certainly `request.security`; the exact `lookahead` argument is **not verified** — with `lookahead_on` the HTF zones leak, with `lookahead_off` + `[1]` indexing they are safe; signals on the chart TF can flicker on the forming bar; treat as medium-confidence causal until the source is inspected.
- causalize: compute swings on closed detection-TF bars only (`lookahead_off`, previous completed HTF bar); evaluate touches/breaks on closed chart bars; freeze the zone list between HTF confirmations.
- params/ATR: Detection Timeframe, Detection Length, Check Previous Historical Level, signal toggles, Avoid False Breakouts. **No ATR mentioned**; zone thickness (if any) is unverified.
- width: unverified from the description; zones appear to be drawn around swing levels — exact thickness must be read from source.
- strength/freshness: implicit via test/retest counts (signals); volume reported on breakouts; no documented numeric score.
- zones/chart: several (object caps 500 suggest a busy chart; in practice ~5–15 active levels depending on Detection Length).
- license: **CC BY-NC-SA 4.0** — the header is quoted together with the source on the ProRealCode thread ("… Attribution-NonCommercial-ShareAlike 4.0 …"; "© LuxAlgo").
- URL: https://www.tradingview.com/script/iOrhpIqc-Support-and-Resistance-Signals-MTF-LuxAlgo/ [NOT FETCHED — cite only]; source quoted on https://www.prorealcode.com/topic/conversion-de-lindicateur-support-and-resistance-signal-mtf/ [NOT FETCHED — cite only]
- fit: conceptually the best LuxAlgo fit — but the licence and the unverified MTF lookahead are the two caveats; re-implement the idea (HTF swings + event classification), not the code.
- confidence: **medium** — description and licence mirror seen; source internals unverified.

### 2.3 Support & Resistance Zones Strength Classifier [LuxAlgo]
- output: horizontal boxes (zones) per side, with optional test-count labels; opacity encodes strength; broken zones are deleted; zones extend right.
- algorithm: `Pivot Lookback` bars on each side confirm pivots; each pivot opens a zone whose thickness is a multiple of the average bar range (volatility-adjusted); overlapping zones **merge**, summing test counts; a zone's count increments every time price returns into it without a close through the far boundary; a close beyond a support/resistance boundary deletes the zone; caps: max active zones per type, max zone height.
- repaint: pivots confirm with `Pivot Lookback` bars of lag; merging means the historical zone layout changes as new pivots arrive; no `security()` mentioned; touch counting on the forming bar can update intrabar; no `barstate` behaviour documented.
- causalize: only open a zone when the pivot is confirmed (lookback lag); count touches on closed bars; apply merge/delete rules in bar order; snapshot the active zone list per bar for the bake-off.
- params/ATR: Pivot Lookback; Zone Width (multiplier of average bar range); Minimum Tests to Highlight; Max Active Zones Per Type; Max Zone Height (multiplier). The docs say "average bar range", **not explicitly `ta.atr()`** — treat as ATR-like but verify.
- width: volatility-adjusted average bar range × multiplier; grows when zones merge (with a max-height kill switch).
- strength/freshness: test count (increments on re-entry, merges sum counts); visual weight by count; no time decay documented, expiry is by breakout deletion only.
- zones/chart: several per side (capped by Max Active Zones Per Type); expect ~5–10 total on M15.
- license: `unknown (source: unverified)` — the fetched HTML contains no licence text; the TV default MPL-2.0 applies only if the code header does not override it, which was not readable.
- URL: https://www.tradingview.com/script/KBEYcjCd-Support-Resistance-Zones-Strength-Classifier-LuxAlgo/ [fetched]
- fit: good, simple and cheap to port; the test-count strength signal is exactly the kind of zone physics the bake-off can score; no built-in HTF mode — run it separately on H1/H4 series if needed.
- confidence: **medium** — description fetched; source internals and licence unverified.

### 2.4 Support & Resistance Pro Toolkit [LuxAlgo]
- output: either precise lines or ATR-based zones; 25-bar right-extension of unmitigated zones; sweep dots; labels carrying score shorthand (E entries, S strength, SW sweeps, V traded volume, D duration); dashboard with mitigation %, avg duration, avg volume, total sweeps.
- algorithm: four selectable swing engines — **Pivots** (left/right lookback), **Donchian alternating** (state machine that confirms the previous extreme when direction flips), **CSID** (N consecutive candles of one direction mark the extreme), **ZigZag** (percentage deviation); each confirmed swing becomes a level; zones = ATR depth inward + ATR breakout buffer outward; unmitigated zones extend 25 bars; overlap handling: merge (older absorbs newer), hide oldest, hide youngest; filters: min re-tests, min internal-swing strength, min sweeps (wick-only violations), min accumulated traded volume inside the zone, min duration in bars; mitigation (break) deletes/hides the zone.
- repaint: pivots lag; Donchian/CSID confirm at the state change (no fixed lag but only after the new extreme forms); ZigZag's last leg is provisional by construction; volume and duration counters accumulate live; no `security()` mentioned; expect normal confirmation-time redraw, not lookahead.
- causalize: use only confirmed swings (pivot lag or state-flip confirmation); treat the current ZigZag leg as unknown until a deviation-complete reversal; accumulate volume/duration/touches on closed bars.
- params/ATR: Detection Method; Swing Sensitivity; Display Style (line vs zone); **ATR Period**, **Zone Depth (ATR mult)**, **Breakout Buffer (ATR mult)**; Min Price Entries; Min Overall Strength; Min Sweeps; Min Traded Volume; Min Duration (bars); Max Active.
- width: ATR-based on both sides (depth inward toward price, buffer outward on the breakout side) — the most explicit ATR-scaled zone model in the LuxAlgo family.
- strength/freshness: richest documented: re-test entries, internal swing-point count, wick sweeps, cumulative traded volume, survival duration; dashboard aggregates them.
- zones/chart: user-capped ("Max Active"), typically a handful (≈5–10).
- license: `unknown (source: unverified)` — no licence text on the page; header not readable.
- URL: https://www.tradingview.com/script/n2ODj57p-Support-Resistance-Pro-Toolkit-LuxAlgo/ [fetched]; companion https://www.luxalgo.com/library/indicator/support-resistance-pro-toolkit/ [fetched]
- fit: the ATR buffer is directly relevant to M5 noise; the volume filter is weaker on FX (tick volume) but still informative; no built-in HTF mode; heavy to port, but each sub-rule is simple.
- confidence: **medium** — detailed official description; internals and licence unverified.

### 2.5 Support Resistance Channels — LonesomeTheBlue
- output: up to N horizontal channel boxes (zones) with automatic colour by position (support/resistance/inside), optional pivot markers, and break shapes + alerts.
- algorithm (read from the v4 mirror): `pivothigh/src1(prd,prd)` and `pivotlow/src2(prd,prd)` with High/Low or Close/Open source (default prd=10); pivots are stored in arrays and pruned beyond `loopback` (default 290 bars); maximum channel width = `(highest(300) − lowest(300)) × ChannelW%` (default 5%); for each pivot, all other pivots within that width are merged into one zone; strength = 20 per included pivot + count of bars in the loopback whose high or low intersects the zone; zones are greedy-selected strongest-first (dropping pivots already covered), sorted descending, capped at `maxnumsr` (default 6); break = close crossing a boundary while price is not inside any channel.
- repaint: no `security()`; `max_bars_back=501`; pivots are only known `prd` bars late; the entire zone list is recalculated on every new pivot, so historical boxes can appear, move or vanish when a new pivot confirms; the break test uses `close`, so it can flip during the forming bar — bounded confirmation lag, not lookahead.
- causalize: rebuild the zone list only at pivot-confirmation bars; treat the list as immutable until then; test breaks on closed bars; the result is a well-defined event-time zone sequence for the bake-off.
- params/ATR: Pivot Period 10; Source High/Low|Close/Open; Maximum Channel Width % 5 (of the 300-bar range); Minimum Strength 1 (internally ×20); Max Number of S/R 6; Loopback 290/300 bars; optional start date/bar and MAs. **No ATR** — width is a percentage of the recent range.
- width: percentage of the 300-bar high-low range; pivots merge while the resulting band stays within that maximum width.
- strength/freshness: strength = 20 × pivots + bar-touch count over the loopback; strongest zones are redrawn each pivot event; no explicit decay other than the loopback window and the max-zones cap.
- zones/chart: ≤ 6 by default (max 10).
- license: **MPL 2.0** — verbatim from the mirrored source header: "This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/"; "© LonesomeTheBlue".
- URL: https://www.tradingview.com/script/Ej53t8Wv-Support-Resistance-Channels/ [fetched]; v4 source mirror https://gist.github.com/Planxnx/c27927832553af1f6e94b9720b4948ef [NOT FETCHED — cite only]
- fit: very good and simple; the strength-then-cap selection gives stable, few zones; `prd=10` on M5 = 50 min confirmation lag; on H1 = 10 h; run once per timeframe (M5/M15 + H1/H4) for the bake-off; caveat: the mirrored source is v4, the 2025 v6 upgrade may have changed details.
- confidence: **high** for the v4 algorithm and licence (source read); **medium** that the current v6 code is unchanged.

### 2.6 Support Resistance Channels/Zones Multi Time Frame — LonesomeTheBlue
- output: zone boxes from the selected higher timeframe drawn on the current chart, plus a table listing each zone's lower/upper band; zones ranked by strength.
- algorithm: user picks a Higher Time Frame (must be above the chart TF) and a Pivot Period; pivots are searched over a `Loopback Period` of HTF bars; zones merge pivots within `Maximum Channel Width %`; strength counts included pivots plus Open/High/Low/Close interactions; up to `Maximum Number of S/R` zones are shown, strongest first; optional "Show S/R that fits the Chart" filters zones to the current visible price range; the table can show all zones regardless.
- repaint: HTF data is involved; unlike the author's separate "Support Resistance MTF" (which explicitly avoids `security()`), this script gives no such statement, so `request.security` is likely; lookahead is unverified; the visible-range filter makes the zone set **zoom-dependent** — a stability problem independent of repainting; HTF pivots need HTF pivot-period bars to confirm (e.g. H4 prd=10 → 40 h).
- causalize: compute pivots on closed HTF bars with `lookahead_off` and previous-bar indexing; disable "fits the chart" and cap zones by count; rebuild the zone set only when a new HTF pivot confirms.
- params/ATR: Higher Time Frame; Pivot Period; Loopback Period; Maximum Channel Width %; Minimum Strength; Maximum Number of S/R; Show S/R that fits the Chart; table options. **No ATR.**
- width: percent of the HTF price range (same family as #2.5).
- strength/freshness: pivot count + OHLC touches on the HTF; sorted strongest first; no expiry other than loopback and the count cap.
- zones/chart: ≤ Maximum Number of S/R (user-set; the author's screenshots show a handful, ~3–6).
- license: **MPL 2.0** (high confidence, inferred: same author and same engine as #2.5, whose header is verified MPL 2.0; the fetched page shows the open-source badge but the licence text itself is not in the HTML).
- URL: https://www.tradingview.com/script/DrcEUv8C-Support-Resistance-Channels-Zones-Multi-Time-Frame/ [fetched]
- fit: exactly the "HTF context on LTF chart" pattern the bake-off wants; two traps: the visible-range filter (disable it) and unverified `request.security` lookahead (verify before trusting); the algorithm is the same pivot clustering as #2.5, which helps re-implementation.
- confidence: **medium-high** — page and full description fetched; licence inferred; security/lookahead unverified.

### 2.7 Trendlines with Breaks [LuxAlgo]
- output: two sloping lines (upper trendline from pivot highs, lower from pivot lows), with `B` break labels; "Show Only Confirmed Breakouts" option. **Line tool → §0 zone conversion required.**
- algorithm (read from mirrors): `ph = pivothigh(length,length)` / `pl = pivotlow(...)`, default length 14; slope per bar = `ta.atr(length)/length × k` (default k=1), or stdev or linreg of price vs bar_index, selectable; on a new pivot the anchor price and slope are reset; otherwise the line walks forward; a breakout is flagged when the source at `[length]` crosses the projected line; trendlines are backpainted by default.
- repaint: two documented behaviours — (a) **trendlines repaint** unless backpaint is disabled (the last leg is redrawn when a new pivot resets the slope); (b) the **breakout signals are real-time and not backpainted**; `pivothigh(14,14)` confirms with a 14-bar lag; no `security()`.
- causalize: turn backpaint off; use only confirmed pivots; a line exists at bar t only from the confirmation bar of its last anchor; evaluate breaks against the line value computed from closed-bar data.
- params/ATR: Length 14 (pivot); Slope k 1.0; method Atr|Stdev|Linreg (default Atr); Show Only Confirmed Breakouts; Backpaint on/off. **ATR is used for the slope** (`ta.atr(length)/length*k`), not for width.
- width: none — single-pixel lines; the ATR only controls the angle.
- strength/freshness: one pivot per line; no scoring, no touch count.
- zones/chart: 2 lines.
- license: **CC BY-NC-SA 4.0** — verbatim header in both mirrors ("This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)"; "© LuxAlgo"); the MT5 port repeats the licence link in `#property link`.
- URL: https://www.tradingview.com/script/IYL88A1N-Trendlines-with-Breaks-LuxAlgo/ [NOT FETCHED — cite only]; mirrors https://github.com/iamc1oud/Tradingview-Scripts/blob/master/Trendlines%20with%20Breaks.pine and https://github.com/traderfour/trend-line [NOT FETCHED — cite only]
- fit: useful as a sloping S/R channel generator (ATR slope is volatility-adaptive), but it produces geometry, not zones; pivot lag 14 bars (70 min on M5); good as a secondary "channel" arm, not as a zone source.
- confidence: **high** on algorithm and licence (full source read via mirrors).

### 2.8 Supply and Demand Zones [Ranked] — LuxAlgo
- output: supply and demand boxes labelled with a 1–7 score; broken/touched zones managed automatically.
- algorithm: scan for the Leg-In → Base → Leg-Out pattern; classify by the base type: DBR (demand reversal), RBR (demand continuation), RBD (supply reversal), DBD (supply continuation); candles are classed ERC when the body is ≥ 75 % of range, NRC when ≤ 50 %; score = freshness (max 3, untouched = full) + departure strength (max 2: gap = 2, strong ERC = 1) + base time (max 2: 1–3 candles = 2, 4–6 = 1); zones invalidate after two touches or when price closes through the distal line; overlapping same-type zones merge.
- repaint: not documented; by construction a zone can only be declared once the leg-out move has completed, so the design is causal with a lag of base length + leg-out confirmation; score/freshness updates on touches are live; source not readable, so unverified.
- causalize: declare the zone at the close of the leg-out candle; update freshness/touches on closed bars only; invalidate on close beyond the distal line.
- params/ATR: ERC/NRC Body %; Max Base Candles; ranking filter (e.g. 5+); Max Zones on Chart. **No ATR mentioned** — zone height comes from the base candles, not volatility.
- width: proximal/distal = base candle high/low (the base's range); no ATR pad documented.
- strength/freshness: this is the selling point — explicit 1–7 score with freshness penalised on revisits, departure strength, base time; invalidate after 2 touches.
- zones/chart: capped by Max Zones on Chart; a handful (≈3–8).
- license: `unknown (source: unverified)` — no licence text seen; LuxAlgo headers on other scripts are CC BY-NC-SA 4.0, so assume non-commercial until verified.
- URL: https://www.luxalgo.com/library/indicator/ssBOX4V7-supply-and-demand-zones/ [NOT FETCHED — cite only] (the TradingView page was not located; the guessed slug returned 404)
- fit: strong candidate; base-time and freshness scoring is a ready-made zone-physics signal; M15/H1 bases map naturally and M5 displacement candles give leg-out confirmation quickly; no HTF mode, so score HTF separately.
- confidence: **medium** — detailed official description, but page only on luxalgo.com; TV URL, source and licence unverified.

### 2.9 Supply and Demand Visible Range — LuxAlgo
- output: a supply area built down from the highest visible price and a demand area built up from the lowest, plus solid average lines and dashed weighted-average lines; per-bin volume accumulation displayed; intra-bar data used for precision.
- algorithm: take the total volume in the visible chart range; split the range into N equal price bins (`Resolution`); for supply, accumulate volume from the top downwards until the accumulated share reaches `Threshold %` of total volume — the accumulated range becomes the area; demand is the mirror from the bottom; a higher threshold gives wider areas; the weighted-average lines highlight more liquid price levels inside each area.
- repaint: by design it **recalculates whenever the visible range changes** — the author calls it "a descriptive tool"; zoom-dependent, therefore not a stable causal generator; intra-bar data via lower-timeframe requests (function name unverified) also changes with data availability.
- causalize: replace the visible range with a fixed window (e.g. previous H4/D1 session) and compute only from completed lower-TF bars; freeze the area when the window closes.
- params/ATR: Threshold %; Resolution (bins); Intra-bar TF. **No ATR.**
- width: emergent — the accumulated-volume threshold determines the band edges, not a fixed multiplier.
- strength/freshness: bin volume accumulation rate is displayed; no touch count or expiry — areas persist until the window moves.
- zones/chart: 2 areas (one supply, one demand) per calculation.
- license: `unknown (source: unverified)` — page reached only via a search snippet; no header seen.
- URL: https://www.tradingview.com/script/UpWXXsbC-Supply-and-Demand-Visible-Range-LuxAlgo/ [NOT FETCHED — cite only]; companion https://www.luxalgo.com/library/indicator/supply-and-demand-visible-range/ [NOT FETCHED — cite only]
- fit: as published, poor (zoom-dependent); the *algorithm* (volume-threshold areas over a fixed completed session/anchor) is a good daily/H4 zone generator for EURUSD, keeping in mind FX "volume" is broker tick volume.
- confidence: **medium** — the algorithm is fully documented in the official description; licence and intra-bar internals unverified.

### 2.10 Smart Money Concepts (SMC) — LuxAlgo
- output: internal + swing structure labels and lines (BOS/CHoCH), internal and swing order-block boxes (last N, default 5), equal highs/lows, FVG boxes, previous D/W/M highs and lows, premium/equilibrium/discount bands; objects capped at 500 boxes/lines/labels; `max_bars_back = 500` in the mirrored v5 header.
- algorithm: two pivot scales (internal, swing) with configurable lengths produce HH/HL/LH/LL swings; a break of the last swing in the trend direction is BOS, against it is CHoCH; order blocks are the last opposite candle at the origin of the displacement that broke structure and are mitigated (removed) when price passes through; FVG = three-candle imbalance; EQH/EQL = two equal pivots within tolerance confirmed after `Bars Confirmation`; premium/discount = halves of the active dealing range; MTF previous D/W/M levels via `security`.
- repaint: pivot-based structure confirms with the pivot length of lag and is drawn back at the swing bar; the newest structure/order block can be revised until its confirmation leg closes; the MTF highs/lows use `security` (lookahead unverified in the mirror); FVGs fill over time — standard lag + last-leg revision, not a lookahead guarantee.
- causalize: only consume structure events at pivot confirmation; only accept an order block after the displacement candle closes and it breaks a confirmed swing; compute MTF levels from completed D/W/M bars.
- params/ATR: internal/swing lengths; OB display count; OB filter (2 methods); EQH/EQL Bars Confirmation; FVG Auto Threshold and FVG Timeframe; Extend FVG; MTF Highs & Lows; premium/discount toggles. **No explicit ATR scaling** in the documented settings.
- width: order block = origin candle range (wick-to-wick); FVG = the 3-candle gap; premium/discount = range halves; no ATR pad.
- strength/freshness: recency (only the last N OBs are shown), OB filter for volatile blocks, mitigation on break; no explicit touch-score.
- zones/chart: busy — up to 5 swing + 5 internal OBs plus FVGs and MTF levels; commonly 10–20 objects.
- license: **CC BY-NC-SA 4.0** — verbatim header in both mirrors ("This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)"; "© LuxAlgo").
- URL: https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/ [fetched]; mirrors https://gist.github.com/thino-dev/5fc81d23ebc2a2113207fd850e340962 and https://gist.github.com/niquedegraaff/8c2f45dc73519458afeae14b0096d719 [NOT FETCHED — cite only]
- fit: good structure/OB arm for the bake-off; its CHoCH/BOS displacement definition is a natural freshness/strength input; heavy to port faithfully, and CC BY-NC-SA means no code reuse in a commercial product (clean-room re-implementation only).
- confidence: **high** on licence; **medium** on internals (mirror headers and description read, not the full source).

### 2.11 Order Blocks Finder [TradingFinder]
- output: active OB boxes (green bullish / red bearish) extended to the right until price reaches them; a 50 % equilibrium line in every block; optional major high/low levels; alerts carrying proximal (near edge) and distal (far edge) prices.
- algorithm: find structure breaks (BOS/CHoCH, also called MSS) using swing points; the OB is the origin of the break leg; two range modes — **Refine off** = whole order-block range; **Refine on** = an error-correction algorithm with Defensive (tighten to standard) and Aggressive (maximize the range to reduce stop-outs) settings; boxes stay active until price reaches the zone; alerts on proximal/distal touches; the vendor states suitability for M1–H1–H4 and Tokyo/Sydney/London sessions.
- repaint: not documented; a structure break is only known once the breaking candle closes, so the OB is declared with that lag; there is no visible-range or security logic described; unverified whether the script redraws older boxes when structure re-evaluates.
- causalize: emit the OB at the close of the structure-breaking candle; treat prior boxes as immutable thereafter; evaluate touches on closed bars (or intrabar if the bake-off allows, but then tag it).
- params/ATR: Order block refine on/off; Refine type Defensive|Aggressive; Show high level; Show low level. **No ATR documented.**
- width: origin candle range, optionally refined (defensive/aggressive adjustment); no volatility scaling.
- strength/freshness: none beyond "major OBs only" (breaks of structure) and the active-until-reached lifecycle.
- zones/chart: one per valid structure break; accumulates over the chart — typically several per session on M5.
- license: `unknown (source: unverified)` — open-source badge; no header seen; do not assume MPL-2.0.
- URL: https://www.tradingview.com/script/MRx6ze6n-Order-Blocks-Finder-TradingFinder-Major-OB-Supply-and-Demand/ [NOT FETCHED — cite only]
- fit: decent light-weight OB arm; the vendor's own timeframe note covers M5/M15 and H1/H4; no MTF mode, no touch scoring — weaker than SMC or S&D Ranked for zone physics, simpler to port.
- confidence: **medium** — description read; source, licence and repaint internals unverified.

### 2.12 Auto Support & Resistance [ForexCracked]
- output: teal support / pink resistance zones merged from close pivots; 1–5 star rating per zone (darker = stronger); H4 and Daily zones with thicker borders and TF tags; a dashboard with the nearest level above/below, pip distance and stars.
- algorithm (as described): swing pivots are confirmed (a set number of bars on each side) before any zone is drawn; each confirmed pivot becomes a zone, and pivots within a merge distance are merged into one zone with an extra touch; zones break and **flip role** when price closes beyond them by more than an ATR buffer (resistance becomes support, touch count resets); weak untouched zones age out, 4–5 star zones persist; two higher timeframes (4H and Daily by default) are detected and drawn on the current chart with their own pivot strength and caps.
- repaint: the vendor explicitly claims non-repainting through confirmed pivots (zone appears a few bars after the swing, then does not move); HTF levels via requests (presumably `security`); lookahead not documented; the claim is plausible but unverified.
- causalize: confirm pivots before emitting zones; update touches on closed bars; evaluate the ATR-buffered break on closes; request HTF pivots from completed HTF bars.
- params/ATR: Pivot strength 10; **Merge distance 0.5×ATR**; **Zone height 0.15×ATR**; Max levels per side; HTF levels (4H, Daily) with own pivot strength and caps; **Break buffer 0.1×ATR**; Max zone age; Keep strong levels.
- width: fixed 0.15×ATR around the pivot cluster; merging broadens the zone.
- strength/freshness: 1 star per touch, capped at 5; merges count as touches; weak zones decay with age, strong (4–5 star) survive until a genuine break; role flip on break.
- zones/chart: capped per side (a handful, ~4–8 including HTF levels).
- license: `unknown (source: unverified)` — "free and open-source" claimed in the article; no licence text seen.
- URL: https://www.forexcracked.com/forex-indicator/auto-support-resistance-indicator-tradingview/ [NOT FETCHED — cite only] (the article links to a TradingView script page but the exact URL was not retrieved; no TV script ID to cite)
- fit: if the claims hold, this is the closest match to the bake-off brief (confirmed pivots + ATR-tuned widths + HTF context + strength rating); but nothing is verifiable from a vendor page — locate the TV page, read the header licence and the `security` calls before using it as a reference.
- confidence: **low** — all details are vendor claims on a third-party site; script page, source and licence unverified.

### 2.13 Pivot Points High Low — TradingView (built-in)
- output: price labels (levels) at pivot highs and lows; lines can be plotted from them. No zones. **Line tool → §0 zone conversion required.**
- algorithm: a pivot high is a bar whose high is higher than the highs of N bars to the left and N bars to the right (the right side must be lower highs); pivot low is the mirror; default 10/10 for both; no smoothing, no weighting.
- repaint: the pivot can only be known once the right window has closed, so labels are drawn back onto the pivot bar with a confirmation lag of `rightLen`; after confirmation the pivot does not move; the "repaint" people see is the delay, plus a pivot being superseded by an extreme that forms inside the window.
- causalize: at bar t, use pivots with index ≤ t − rightLen; a pivot at bar p is usable only at p + rightLen and stays fixed.
- params/ATR: left/right lengths (built-in default 10/10; four values in the basic version, independently for highs and lows). **No ATR.**
- width: none (conversion external).
- strength/freshness: none (level only).
- zones/chart: one per pivot; on M5 with right=10 roughly one pivot every ~20+ bars per side — dozens of levels over a few days.
- license: **proprietary/unknown** (built-in study; the code can be opened in the Pine editor but is not published under a community licence; no licence statement was found; do not treat as open-source).
- URL: https://www.tradingview.com/support/solutions/43000589195-pivot-points-high-low/ [NOT FETCHED — cite only]; third-party implementation guide https://pineify.app/pine-script/indicators/pivot-points-high-low [NOT FETCHED — cite only]
- fit: not a zone generator by itself, but the correct causal primitive for every pivot-based candidate above; for the bake-off use `rightLen ≈ 24` on M5 (≈2 h) or 10 on H1/M15 and cluster pivots in Python.
- confidence: **medium** — official help page plus a third-party guide; licence proprietary.

### 2.14 Zig Zag — TradingView (built-in)
- output: alternating swing lines and labels; no zones (swing points can seed zones).
- algorithm (official docs): pivots are confirmed with `Pivot legs` split evenly left/right; a swing is only added if the reversal from the last point meets the `Price deviation (%)` threshold; the indicator connects confirmed alternating pivots; optionally it can display a **projected** (unconfirmed) pivot on realtime bars.
- repaint: the docs are explicit — the latest solid line is not final and can be redrawn; the projected line updates every bar; it lags by the pivot-leg confirmation; drawings are capped at ~500 lines so deep history is truncated; this is a heavy repainter by design.
- causalize: never use the current (last) leg or projected pivots; only use pivot points that are confirmed by the `Pivot legs` window and by the deviation threshold; replay with a per-bar snapshot of the confirmed structure.
- params/ATR: Price deviation for reversals (%); Pivot legs (total, split left/right); Calculate projected pivots (on/off); label mode. **No ATR.**
- width: none (a percentage-deviation channel around the last pivot could be derived but is not part of the indicator).
- strength/freshness: none.
- zones/chart: dozens of swings on M5; deeper history truncated by the ~500-line cap.
- license: **proprietary/unknown** for the built-in; the Pine library publication by TradingView (https://www.tradingview.com/script/bzIRuGXC-ZigZag/ [NOT FETCHED — cite only]) is a community open-source publication (licence not read — unknown).
- URL: https://www.tradingview.com/support/solutions/43000591664-zig-zag/ [NOT FETCHED — cite only]
- fit: useful as the swing skeleton for structure zones; the deviation % threshold is naturally volatility-adaptive; because of the repaint behaviour, only the confirmed subset should be used in the bake-off.
- confidence: **medium** — official docs read; licence and Pine internals of the built-in unverified.

### 2.15 Volume Profile (Session / Visible Range / Periodic) — TradingView (built-in)
- output: horizontal histogram binned by price; POC line; VAH/VAL lines; the value-area band is the zone; HVN/LVN shape is visible inside the profile. Requires a paid plan (Essential or higher).
- algorithm (official docs): lower-timeframe bars of the same symbol are loaded for the period; each bar's volume is distributed across the price levels it traded; direction up/down by `close >= open`; POC = row with the highest total volume; the value area (default **70 %**) is built by starting at the POC and repeatedly comparing the adjacent row above and below, adding the heavier side until the target volume is reached; ties prefer the row nearer the POC, then the row above; VAH/VAL are the outermost rows added.
- repaint: historical profiles are stable; the profile of the current period updates on every bar/tick (that is expected); Visible Range VP recalculates with zoom — descriptive only; Session/Periodic profiles are deterministic per completed session/period.
- causalize: build the histogram only from completed lower-TF bars of a closed period (previous session, previous H4), then freeze VAH/VAL/POC for the next period; do not use the Visible Range variant.
- params/ATR: Value Area Volume 70 %; row size (ticks per row); anchor period for the anchored variants; lower-TF selection table. **No ATR.**
- width: emergent from the histogram and the value-area percentage — the VA can be wide or narrow depending on distribution; not a fixed multiple.
- strength/freshness: POC volume mass, HVN/LVN; no touch count; the value-area edge is a statistical level (70 % convention ≈ 1 σ of a normal distribution, per the docs).
- zones/chart: one VA band + POC per period.
- license: **proprietary, closed-source, no community publication**; the algorithm can be re-implemented from the public documentation.
- URL: https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/ [NOT FETCHED — cite only]; per-indicator pages for Session/Periodic also seen [NOT FETCHED — cite only]
- fit: good as the H4/D1 context arm (previous session's VAH/VAL/POC as horizontal zones for M5/M15); caveat: FX volume is tick volume — broker-dependent, but consistent enough for level location.
- confidence: **high** on algorithm (official docs quote the build procedure); **high** that the licence is proprietary.

---

## 3. Python / quant methods

9 candidates (A1–A9 in `_survey_python_academic.md`). These are the building blocks and baselines for a causal, offline re-implementation; all ATR/pip figures marked `ASSUMPTION` in the source are to be measured on the actual MT5 history before use.

### 3.1 ZigZag pivots (PyPI `zigzag` 0.3.2)
- output: `peak_valley_pivots(X, up_thresh, down_thresh)` returns an int array, `+1` peaks / `-1` valleys / `0` elsewhere; points, not zones.
- algorithm: a relative-change ZigZag — determine the initial pivot by scanning for the first move exceeding `up_thresh` (upward) or `down_thresh` (downward, negative); track the trend keeping the running minimum; when price rises `up_thresh` relative to that minimum, finalize the minimum as a valley and flip trend (mirror logic for peaks); thresholds are **relative** fractional price changes, not absolute; the last annotated pivot is provisional until a threshold reversal occurs.
- repaint: **partly** — a causal mode exists (`peak_valley_pivots_detailed(..., limit_to_finalized_segments=True, use_eager_switching_for_non_final=False)`, which `peak_valley_pivots` uses), but the **initial-pivot** determination reads forward through the whole array, and the last element can still be labelled as a tentative pivot.
- causalize: feed only bars closed at or before t; discard/ignore the last annotated pivot (the "forming" one); use only pivots that have been superseded by a later threshold reversal; do not re-run the initial-pivot scan on an ever-growing array and reuse old labels without re-verification.
- params/ATR: `up_thresh`, `down_thresh` (relative fractions; `down_thresh` negative); convert an ATR budget: `threshold ≈ k * ATR(14, TF) / price`; for EURUSD near 1.10, 1 pip ≈ 0.0000909 relative; typical M5 ATR(14) on the order of 1–2 pips, H1 ~5–9 pips, H4 ~12–25 pips (`ASSUMPTION — measure on the actual history`); suggested sweep `k ∈ {0.5, 1.0, 1.5}`.
- width: none — output is points; zone width must be added externally, e.g. ±0.25 × ATR around the pivot price, or ±half the median pivot-to-pivot amplitude.
- strength/freshness: none; can be added from pivot age (bars since confirmation) and pivot-to-pivot amplitude; no volume input.
- zones/chart: a threshold of ~1 × ATR(H1) on H1 gives roughly 2–6 pivots per 100 bars; after de-duplication expect ~3–8 levels in a 20-day H1 window; more pivots on M5 with the same ATR multiple.
- license: **BSD-3-Clause** (PyPI "License: BSD License (BSD-3-Clause)", OSI approved classifier; GitHub license badge BSD-3).
- URL: https://pypi.org/project/zigzag/ [fetched]; https://github.com/jbn/ZigZag/blob/main/zigzag/core.pyx [fetched]
- fit: good as the swing extractor for H1/H4 context pivots (few, meaningful turning points) and as the raw input to a clustering step on M5/M15; not a zone generator by itself.
- confidence: **high** on existence/licence/behaviour (source read); **medium** on causal use (initial-pivot scan and provisional last pivot must be handled).

### 3.2 Classical pivot points (and the `pivotpoints` PyPI question)
- output: `PP` plus `R1..R3`, `S1..S3` per period; variants Standard (floor), Woodie, Camarilla, Demark, Fibonacci; `stock-indicators` returns a full time-series aligned to the input quotes with `None` during warmup; `RollingPivots` uses a `window_periods` + `offset_periods` rolling window.
- algorithm: aggregate the **previous** period's high, low and close — `PP = (H+L+C)/3`, `R1 = 2*PP − L`, `S1 = 2*PP − H`, `R2 = PP + (H − L)`, `S2 = PP − (H − L)`, `R3`/`S3` extend by the same range; Fibonacci variant scales (H−L) by 0.382/0.618/1.000; the freqtrade version computes rolling means of high/low/typical price over `timeperiod`, then derives levels recursively.
- repaint: **no** under the standard definition — levels for period t are computed from the completed prior period and are frozen for the whole period (confirmation lag = the period boundary); intraday "rolling" variants change as the window slides, so their lag is `window_periods + offset_periods − 1` bars (documented for `RollingPivots`).
- causalize: use the period-boundary definition on closed bars only; or use `RollingPivots` with `offset_periods >= 1` so the window ends before the bar being evaluated.
- params/ATR: standard window = prior day/week/hour; variants above. **No ATR inside the formula** — levels are range-scaled; if a zone instead of a line is needed, use ±0.25 × ATR(14, TF); `R2−R1 = H−L` is itself an ATR-like band.
- width: none (lines); zone = manually widening each level, or using the band between adjacent levels (e.g. PP–R1) as the zone.
- strength/freshness: none; levels are recalculated every period and are "fresh" for one period by construction; confluence with other generators is the natural strength proxy.
- zones/chart: 1 PP + 6 levels per period (standard); day-based data on EURUSD = 7 lines per day.
- license: `stock-indicators` **Apache-2.0**; `freqtrade/technical` **GPL-3.0**; `backtrader` **GPL-3.0** (GPL-3 is a distribution-copyleft risk for the host package; prefer permissive implementations or implement the 4-line formulas in-repo). The PyPI project **`pivotpoints` does not exist** — the JSON API returned HTTP 404 on 2026-09-20 [fetched].
- URL: https://python.stockindicators.dev/indicators/PivotPoints/ [fetched — search-extracted]; https://python.stockindicators.dev/indicators/RollingPivots/ [fetched — search-extracted]; https://pypi.org/pypi/stock-indicators/json [fetched]; https://github.com/freqtrade/technical/blob/main/technical/pivots_points.py [fetched — search-extracted]; https://api.github.com/repos/freqtrade/technical [fetched]; https://api.github.com/repos/mementum/backtrader [fetched]
- fit: good as context rails (H1/H4 pivots as levels the M5 engine can test), weak as the primary zone generator because it is line-based and mechanical.
- confidence: **high** on formulas/output (docs fetched); **high** that `pivotpoints` is not a PyPI project; **medium** on which implementation to vendor (licence trade-offs).

### 3.3 KDE of swing-point prices — `scipy.stats.gaussian_kde`
- output: a KDE object; `evaluate`/`pdf` returns density values at arbitrary price points; zones = local maxima of the density over the price axis (peaks) or regions whose density exceeds a chosen quantile.
- algorithm: place a Gaussian kernel at every swing price, sum the kernels, scale by `1/(n·h)`; local maxima are the price levels where swings historically clustered most; a density threshold turns the peak's neighbourhood into a zone; `weights=` allows recency or volume-at-price weighting of the swing samples; bandwidth factor automatic (Scott default: `n**(-1/(d+4))`); SciPy documents that the estimate works best for unimodal data — bimodal/multimodal densities tend to be **oversmoothed**.
- repaint: not applicable in the usual sense — the density is computed from the sample of confirmed swing prices; no future bars are used **provided** the swing sample contains only confirmed pivots (see 3.1/3.6/3.9); if the swing extractor is non-causal, the KDE inherits the leak.
- causalize: build the swing sample from pivots confirmed at least `L` bars ago; recompute the KDE on each closed bar using only the trailing window (e.g. last `N` days); never fit bandwidth on the test window.
- params/ATR: `bw_method` = `'scott'` (default), `'silverman'`, a scalar factor, or a callable; Scott's factor from `n` points is `n**(-1/5)`, which is **not** ATR-aware; for price zones pass a callable returning `bandwidth = c * ATR(14, TF)`; practical sweep `c ∈ {0.25, 0.5, 1.0}` on H1 ATR; `weights=` optional (recency weights with half-life 1–2 sessions on M5, ~5 days on H1).
- width: natural — the density peak's width; practically the contiguous price range around a peak where density ≥ `q × peak_density` (`q` = 0.5–0.7), or simply ±0.25 × ATR around the peak centre; the bandwidth sets the floor on zone width.
- strength/freshness: peak height (probability mass) is a natural strength proxy; recency enters only through `weights=` or window length; nothing tracks time-since-touch unless added.
- zones/chart: with `c ≈ 0.5 × ATR(H1)` on a 20-day H1 swing sample expect ~4–10 peaks; on M5 with a 2–3 session window expect ~3–8.
- license: **BSD-3-Clause** (GitHub API license `bsd-3-clause`; SciPy docs copyright "The SciPy community").
- URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html [fetched]; https://api.github.com/repos/scipy/scipy [fetched]
- fit: good — the most direct "price memory" generator: swing prices in, density peaks out; naturally fuses H1/H4 context (rarer, heavier swings) with M5/M15 swings if the sample pools TFs with weights.
- confidence: **high** on API/licence (docs fetched); **medium** on zone quality (bandwidth choice dominates; SciPy documents oversmoothing of multimodal data).

### 3.4 KDE alternative — `sklearn.neighbors.KernelDensity`
- output: fitted estimator; `score_samples(X)` returns **log** density on a price grid; same downstream use as 3.3 (peaks → zones).
- algorithm: sum of kernels centred on the samples, evaluated via a KD-tree or BallTree; kernels available: `gaussian`, `tophat`, `epanechnikov`, `exponential`, `linear`, `cosine`; because the tree-based evaluation is lazy, it scales better when scoring a dense grid or many windows, at the cost of an extra dependency iteration path; `sample_weight=` is supported in `fit` (equivalent of the 3.3 weights).
- repaint: not applicable / no future bars if the swing sample is causal — same caveat as 3.3.
- causalize: same as 3.3 — trailing swing sample, closed bars only.
- params/ATR: `bandwidth` is in **data units** (default `1.0` — dangerous on EURUSD: an absolute bandwidth of 1.0 is wider than the whole price!); set `bandwidth = c × ATR(14, TF)` directly, or pass `'scott'`/`'silverman'`; `kernel='gaussian'` for smooth peaks, `'tophat'` when hard zone edges are wanted; sweep `c ∈ {0.25, 0.5, 1.0}`.
- width: as 3.3; `tophat`/`epanechnikov` kernels produce finite-support peaks with a natural half-width ≈ bandwidth.
- strength/freshness: as 3.3 (`sample_weight` for recency or tick volume).
- zones/chart: as 3.3.
- license: **BSD-3-Clause** (GitHub API license `bsd-3-clause`).
- URL: https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KernelDensity.html [fetched]; https://api.github.com/repos/scikit-learn/scikit-learn [fetched]
- fit: same as 3.3; slightly better when the grid is dense or a non-Gaussian kernel is desired. Choose 3.3 or 3.4, not both, unless the bake-off wants the kernel family as an axis.
- confidence: **high** on API/licence (docs fetched); **medium** on zone quality (same bandwidth issue).

### 3.5 Market profile / value area — PyPI `marketprofile` 0.2.0
- output: per slice — `poc_price`, `value_area` = `(VAL, VAH)` at `value_area_pct` (default 70 %), `balanced_target`, `profile_range`, low/high value nodes, `open_range`, `initial_balance`; the underlying `profile` is a pandas Series of volume-per-row or count-per-row.
- algorithm: round each bar's **Close** to a price row (`row_size = tick_size × prices_per_row`, default tick 0.05), then aggregate by row — `vol` mode sums `Volume`, `tpo` mode counts closes; POC = row with maximum aggregate; the value area grows outward from the POC row, one neighbouring row at a time, always adding the adjacent row with the larger aggregate, until `value_area_pct` (70 %) of the total is covered; VAL and VAH are the extremes of that set; LVN/HVN are local minima/maxima of the row aggregates found with `scipy.signal.argrelextrema`.
- repaint: not inherently — POC/VA are computed from the bars inside the chosen slice; they **change when the slice rolls** (a new session adds rows), so the value area is only final at slice close; no future bars if the slice ends at t.
- causalize: use slice = previous completed session(s) (or a rolling window ending at bar `t−1`); recompute at each closed bar; expose POC/VAH/VAL to the strategy only for the next bar onward; for intraday context compute an H1/H4 profile over the trailing 5–20 sessions.
- params/ATR: `tick_size`/`row_size` should scale with volatility — a good default is `row_size ≈ 0.1 × ATR(14, TF)` (on M5 EURUSD roughly 0.1–0.2 pip; a 1-pip row is a practical coarse alternative); `value_area_pct = 0.70` (Steidlmayer convention); `mode='tpo'` to avoid fake volume; `open_range_size=10 min`, `initial_balance_delta=1 h`.
- width: the value area **is** a zone — `[VAL, VAH]`, typically 1–2 × ATR(H1) wide on a daily EURUSD window; POC is a line inside it.
- strength/freshness: POC volume, value-area width vs ATR, and whether the current price is inside/outside the VA; freshness = age of the session (a prior-day VA is fresh for the next day only).
- zones/chart: 1 VA + 1 POC per session; with a 5–10 session context window, 5–10 zones (many overlapping; de-duplication needed).
- license: **BSD-3-Clause** (LICENSE file is the 3-clause BSD text, "Copyright (c) 2017, Brad Folkens"; PyPI classifier "BSD License"); package stale — no release since 2020-01-19.
- URL: https://pypi.org/pypi/marketprofile/json [fetched]; https://raw.githubusercontent.com/bfolkens/py-market-profile/master/src/market_profile/__init__.py [fetched]; https://raw.githubusercontent.com/bfolkens/py-market-profile/master/LICENSE [fetched]
- fit: good as a slower context generator (prior H1/H4/daily value areas as H1/H4 zones); caveats: MT5 FX "volume" is tick volume, not real traded volume, and the library's `vol` mode just sums it (`mode='tpo'` is the safer default for FX); the library rounds only **Close**, so it does not distribute the candle's range.
- confidence: **high** on existence/licence/API (source and LICENSE read); **medium** on zone quality for FX (Close-only rows, stale package, tick volume).

### 3.6 Williams Fractals
- output: `get_fractal(quotes, window_span=2, end_type=HIGH_LOW)` returns, per bar, an optional `fractal_bear` (a high pivot) and `fractal_bull` (a low pivot) at the centre bar; points only.
- algorithm: a bar is a fractal high if its high exceeds the highs of the `S` bars on each side (`S=2` ⇒ 5-bar pattern); a fractal low is the mirror with lows; `end_type` can use close instead of high/low; the total window is `2S+1`; no clustering, no zones — just the central extrema.
- repaint: **yes by construction** — the docs carry an explicit warning: "this price pattern uses future bars and will never identify a fractal in the last `S` periods of quotes. Fractals are retroactively identified."; confirmation lag = `S` bars after the centre bar (`S=2` default).
- causalize: only accept a fractal at centre bar `i` once bar `i+S` has closed; in a loop, emit the fractal with an `S`-bar delay (or store it with its confirmation timestamp); never read a fractal whose right window is not complete.
- params/ATR: `window_span`/`left_span,right_span` (`S`, default 2, minimum 2); `S=2` on M5 is noisy (many fractals), `S=3` or `S=4` on M15/H1 reduces count; no ATR inside; after extraction, merge fractals within `0.5 × ATR(14, TF)` and/or widen the zone by `±0.25 × ATR`.
- width: none native — needs external clustering/width; common choice: zone = `[price − 0.25×ATR, price + 0.25×ATR]`, or the min/max of merged fractals in a cluster.
- strength/freshness: none native; touch count (number of fractals merged), recency (bars since confirmation) and fractal rank (`S`) are all external.
- zones/chart: raw `S=2` fractals are several per hour on M5 — far too many; after merging within 0.5 × ATR(H1) on a 20-day window: ~5–12 levels.
- license: **Apache-2.0** (`stock-indicators`); MT5 `iFractals` is platform-native, no separate licence.
- URL: https://python.stockindicators.dev/indicators/Fractal/ [fetched]; https://pypi.org/pypi/stock-indicators/json [fetched]
- fit: medium as a raw feature; good as a cheap swing detector for H1/H4 context (with S=3–4), then clustered; needs the explicit confirmation delay, otherwise it leaks future bars.
- confidence: **high** on algorithm/repaint behaviour (official docs fetched); **medium** as a standalone zone generator (too noisy; clustering required).

### 3.7 Unsupervised 1-D clustering of swing prices (k-means / mean-shift / natural breaks / gap statistic)
- output: KMeans `k` centroids + per-sample labels → zone centres (extent from cluster min/max or ±0.25 × ATR); MeanShift cluster centres without specifying `k` (bandwidth from `estimate_bandwidth` or a quantile); jenkspy `jenks_breaks(values, n_classes)` → class boundaries (natural breaks) → zones are the intervals; gap statistic = estimate of the best `k` by comparing within-cluster dispersion to a null reference.
- algorithm: KMeans alternates assigning each swing price to the nearest of `k` centroids on the 1-D price axis and recomputing centroids as means, minimising within-cluster variance (initialisation matters); MeanShift moves each point toward the mode of the density within a bandwidth until convergence, finding dense price levels without choosing `k`; Fisher-Jenks (jenkspy) finds `k−1` breakpoints minimising within-class variance exactly via dynamic programming — a natural fit for 1-D price histograms; the gap statistic compares the observed within-cluster dispersion curve with that of uniform reference data to pick `k`.
- repaint: no future bars if the cluster model is fitted only on confirmed swing pivots from the trailing window; **instability instead of repaint** — cluster assignments/centroids can jump when new pivots arrive (especially KMeans with random init), making the zone set non-stationary bar to bar.
- causalize: fit on pivots confirmed before the current bar; fix `random_state` and/or use large `n_init`; prefer deterministic jenkspy/MeanShift where possible; smooth zone turnover with a "zone must exist for ≥ m bars before use" rule.
- params/ATR: KMeans `n_clusters` (sweep 2–12; elbow/silhouette or gap statistic, but elbow is unreliable below), `n_init=10+`, `random_state` fixed; MeanShift `bandwidth ≈ c × ATR(14, TF)` (`c ∈ {0.5, 1.0}`) or `estimate_bandwidth(quantile=0.2)`; jenkspy `n_classes` (sweep 3–12).
- width: cluster extent (min–max of member prices) is the most natural; shrink to ±0.25 × ATR around the centroid if the cluster is too wide (a cluster spanning several ATRs is a range, not a zone); the gap between adjacent cluster min/max is what the practitioner pipelines call the boundary.
- strength/freshness: member count (touches) per cluster; mean recency of members; ATR-normalised cluster width; KMeans itself gives no uncertainty.
- zones/chart: `k`-dependent; with `k = 6–10` on a 20-day H1 swing set expect 6–10 zones (some too wide to be useful).
- license: scikit-learn **BSD-3-Clause**; `jenkspy` **MIT** (GitHub API license `mit`); `kneed` not verified (`ASSUMPTION`: MIT per its repo); gap statistic = Tibshirani, Walther & Hastie 2001 method, no canonical maintained package verified.
- URL: https://api.github.com/repos/mthh/jenkspy [fetched]; sklearn API pages covered by 3.4's fetch; clustering use documented in the practitioner sources of 3.8 [fetched — search-extracted]; gap statistic [NOT FETCHED — cite only] (Tibshirani et al. 2001, JRSS-B)
- fit: the clustering step is TF-agnostic and can merge M5/M15/H1/H4 swings into one pool (with weights); prefer MeanShift or natural breaks over KMeans (see 3.8 negative evidence).
- confidence: **high** on licences/API for sklearn and jenkspy; **medium-low** on zone quality — the published walkthroughs show KMeans "not a great solution" for high-timeframe S/R (3.8), and `k` selection is the known weak point.

### 3.8 Practitioner S/R-clustering pipelines (blogs / GitHub walkthroughs)
- output: (i)(ii)(v) price lines at KMeans cluster boundaries (min/max); (iii) lines/zones (rectangles) from extremes clusters; (iv) clustered zones from swing highs/lows plus a KDE "density gradient" of swing prices.
- algorithm: (iv) is the closest to the plan and is a complete recipe — `scipy.signal.argrelextrema` on High/Low with an order/window (`SWING_WINDOW=30`) → collect swing highs/lows → greedy 1-D clustering with a **relative tolerance** (0.5 % in the article) merging levels within tolerance of the cluster mean → horizontal segments spanning the cluster's first-to-last swing ± window → colour by majority type (support/resistance) → finally `scipy.stats.gaussian_kde` over the pooled swing prices to draw a density gradient (peaks = strongest levels); (i)(ii)(v) instead cluster all closes or all extremes with KMeans and use the min/max of each cluster as S/R, choosing `k` by elbow/`kneed`.
- repaint: the pipelines use only historical bars in the tutorials, but the swing window (`argrelextrema` order=30) is non-causal for the most recent 30 bars, and KMeans clusters change as data arrives; same causal fixes as 3.7/3.9.
- causalize: confirmed swings only (`order`-bar delay); trailing window; recompute per closed bar; freeze zones between recomputes.
- params/ATR: (iv) `SWING_WINDOW=30`, `CLUSTER_DISTANCE=0.5%` — for EURUSD, 0.5 % is ~55 pips, far too wide for M5/M15; replace with `CLUSTER_DISTANCE = 0.25–0.5 × ATR(14, TF)`; KMeans: `k` 4–12.
- width: (iv) lines with a segment length; (iii) rectangles between cluster support and neighbouring resistance (the article explicitly says traders use rectangles rather than lines).
- strength/freshness: (iv) uses density (KDE) height as a strength proxy and majority type; the others use cluster size only.
- zones/chart: (iv) with window 30 and 0.5 % tolerance produced a handful of zones on 6 months of NIFTY; expect 5–15 before de-duplication.
- license: tutorials: site copyright (text/code snippets have no explicit licence); `boysugi20/python-stock-support-resistance` repo: no licence stated in the search-extracted README (`ASSUMPTION`: all rights reserved; treat as reference, re-implement).
- URL: (i) https://www.alpharithms.com/calculating-support-resistance-in-python-using-k-means-clustering-101517/ [fetched — search-extracted]; (ii) https://towardsdatascience.com/using-k-means-clustering-to-create-support-and-resistance-b13fdeeba12/ [fetched — search-extracted]; (iii) https://lambdalearner.com/picking-support-and-resistance-levels-with-k-means/ [fetched — search-extracted]; (iv) https://medium.datadriveninvestor.com/i-tried-building-an-automatic-support-resistance-detector-in-python-heres-what-actually-worked-524686e3f667 [fetched — search-extracted]; (v) https://github.com/boysugi20/python-stock-support-resistance [fetched — search-extracted]
- fit: good as a **design template** — swing extraction + tolerance clustering + KDE density is exactly the 3.1/3.3/3.9 stack; do not copy parameters (they are equity-daily/percentage based).
- confidence: **medium** on the recipes (source text read); **low** on their validation — none of these articles reports out-of-sample evaluation or costs, and (i) explicitly concludes KMeans "is not a great solution" for high-timeframe S/R; use as implementation references only.

### 3.9 `scipy.signal.argrelextrema` + tolerance clustering (the minimal swing primitive)
- output: tuple of integer indices where `data[i]` is greater/less than the `order` neighbours, e.g. `argrelextrema(highs, np.greater_equal, order=n)`; the caller extracts the prices; points only.
- algorithm: a comparison against the previous and next `order` samples (`mode='clip'` by default at the boundaries); with `order=30` on daily highs, the centre bar must be the maximum of a 61-bar window; it is a symmetric window, so the extremum is only known after the right half has printed; a second pass clusters the extracted prices within a tolerance (greedy merge in the 3.8 pipeline).
- repaint: **yes for the last `order` bars** — an extremum inside the right window is not confirmed until `order` further bars close; also, `greater_equal` can mark plateaus/multiple bars.
- causalize: emit an extremum at index `i` only when the newest closed bar index is `≥ i + order`; maintain a pending buffer; alternatively use a small `order` (2–3) if a small lag is acceptable, or a one-sided running-extreme rule (like ZigZag) that finalises when price retraces by a threshold.
- params/ATR: `order` (sweep 3–10 on M5/M15; 20–50 on H1/H4 in the tutorials is equity-daily scale); there is no ATR inside; couple with tolerance clustering `tol = 0.25–0.5 × ATR(14, TF)`.
- width: from the clustering tolerance (merged extremes within `tol` form a zone whose width is the cluster's min–max), or ±0.25 × ATR.
- strength/freshness: number of merged extremes, type balance (support vs resistance), recency.
- zones/chart: on EURUSD M5 with `order=5` and a 2-session window, dozens of extremes → after tolerance clustering, ~5–10 zones.
- license: **BSD-3-Clause** (SciPy).
- URL: SciPy API (same repo/docs as 3.3) [fetched]; used in 3.8(iv) [fetched — search-extracted]
- fit: good and dependency-light; the natural baseline against which 3.1 (ZigZag) and 3.3/3.4 (KDE) are compared; its `order` parameter gives an explicit, easily auditable confirmation lag.
- confidence: **high** on API/behaviour (SciPy docs); **high** on causality analysis (symmetric window is definitional); **medium** on zone quality (needs clustering).

---

## 4. Academic literature on S/R and round numbers

10 items (B1–B10 in `_survey_python_academic.md`). Numbers below are copied exactly from the source file's extractions; cost treatment is reported as the source states it.

### 4.1 Osler (2000), "Support for Resistance: Technical Analysis and Intraday Exchange Rates"
- object: **lines** — the support/resistance levels published daily by six FX firms to clients (not zones).
- method: bootstrap; a level is "hit" if the bid (support) / ask (resistance) comes within 0.01% of it; a trend is "interrupted" ("bounce") if price has not crossed the level 15 minutes later (30-min and 0.00%/0.02% cutoffs as robustness); bounce frequencies for published levels compared month by month with the average bounce frequency of 10,000 sets of artificial levels per day.
- data/sample: six firms, January 1996 – March 1998; USD/DEM, USD/JPY, USD/GBP; indicative quotes sampled at **one-minute** intervals, 9:00–16:00 New York; approximately 23,700 (DEM), 22,800 (JPY) and 17,700 (GBP) published S/R values; two of six firms did not publish GBP levels.
- measured effect: published levels bounced **60.8%** of the time on average vs **56.2%** for arbitrary levels; published exceeded arbitrary in **all 16 firm-currency pairs**; by currency the edge was **+4.2 pp (DEM), +5.6 pp (JPY), +4.0 pp (GBP)**; statistically significant at 5% for all but three firm-currency pairs; best and worst firms differed by ~4.0 pp; predictive power lasted **at least five business days** after publication; the strength labels published with the levels were **not informative** (firms did not correctly rank which levels were more likely to hold).
- cost treatment: none — a hit/bounce-frequency test, not a P&L test; spreads, slippage and execution not modelled; **"Survives costs" = NOT TESTED.**
- maps to a zone generator: justifies S/R as a real intraday phenomenon with a measurable edge over arbitrary levels; supports generating zones rather than lines (the 0.01% hit tolerance is effectively a small zone), a **freshness window of ~5 business days**, and computing strength from data (firm-provided labels failed).
- caveats: pre-euro, pre-algo sample (1996–98); indicative rather than dealable quotes; 15-minute bounce definition is a horizon choice; the 4–5.6 pp edge in bounce frequency may be far too small to pay the spread.
- URL: https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html [fetched]; PDF https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf [fetched — search-extracted]
- confidence: **high** (full article text and abstract read; numbers from the publisher's own summary/PDF extraction).

### 4.2 Osler (2003), "Currency Orders and Exchange Rate Dynamics"
- object: **order-level round numbers** (requested execution rates of stop-loss and take-profit orders) and the round-number levels themselves.
- method: cross-sectional distribution of the last digits of requested execution rates by order type; Anderson–Darling tests against uniformity; bootstrap tests of asymmetry between order types; simulation of exchange-rate behaviour conditional on order clustering.
- data/sample: complete set of stop-loss and take-profit orders placed at one large FX dealing bank, **1 August 1999 – 11 April 2000**, covering USD/JPY, GBP/USD and EUR/USD; total order value reported in excess of **$55 billion** (working-paper version).
- measured effect: requested rates cluster strongly at round numbers; the single largest cluster is at rates ending in **00** (about **8.7%** of all orders on average vs ~1% under uniformity; the arrival of any rounding is rejected at better than the 0.01% level); executed **take-profit** orders are executed at `00` far more often than stop-loss orders: **9.8% of take-profit order value vs 4.3% of stop-loss order value** (working-paper version; the JF-summary text uses ~**9.3% vs 4.4%** for the equal-weighted/executed variant); asymmetry 2: stop-loss **buy** orders cluster just **above** round numbers and stop-loss **sell** orders just **below**, while take-profit orders show no such asymmetry — e.g. 4.5% of executed stop-loss sell orders sit at rates ending in 45 vs 2.0% of take-profit buy orders; simulation: bounce frequency at round numbers exceeds arbitrary numbers in **20 of 20 cases** across two horizons (significant at the 0.01% level).
- cost treatment: none — explains *why* S/R predictions work, does not run a trading strategy; **"Survives costs" = NOT TESTED.**
- maps to a zone generator: microfoundation for a **round-number zone generator**; the prediction is **side-dependent** — take-profit clusters (reversal pressure) at round numbers, stop-loss clusters (acceleration) just beyond them; a zone engine can emit asymmetric zones (reversal zone at round numbers, breakout zone just beyond).
- caveats: one bank, nine months, 1999–2000; the two published versions differ slightly in the headline percentages; no cost analysis; modern algo/HFT order placement may have changed the clustering.
- URL: https://onlinelibrary.wiley.com/doi/10.1111/1540-6261.00588 [fetched — search-extracted]; working-paper PDF https://www.econstor.eu/bitstream/10419/60582/1/331762730.pdf [fetched — search-extracted]; https://www.chesler.us/resources/academia/osler_ta.pdf [fetched — search-extracted]
- confidence: **high** on the existence of clustering and the direction of the asymmetries (multiple independent extracts agree); **medium** on exact percentages (two version variants quoted above).

### 4.3 Osler (2005), "Stop-Loss Orders and Price Cascades in Currency Markets"
- object: **round-number levels** (rates ending in 00 or 50) as proxies for stop-loss clusters; measurable as levels/zones.
- method: find every episode where the rate comes within 0.01% of a round number; split into crossing vs reversal subsamples; compare the average signed log price change after reaching round numbers (`MVR`) with that after arbitrary numbers (`MVA`) at 15 min and longer horizons, with 10-day-interval bootstrap tests; contrast responses to stop-loss vs take-profit clusters.
- data/sample: over two years of **minute-by-minute** quotes for USD/DEM, USD/JPY and GBP/USD.
- measured effect: after crossing a round number the rate moves faster than after crossing an arbitrary number: USD/DEM averages **0.061% in the 15 minutes after a round-number crossing vs 0.054% for arbitrary numbers**; the round-number average exceeded the arbitrary average in **51 of 58 10-day intervals** (marginal significance below 0.001%); USD/JPY moves **0.0130 pp more** after a crossing than after a reversal at a round number (positive in 46 of 58 intervals, p < 0.001%); the reversal ("bounce") tendency at round numbers is significant only for horizons **shorter than 30 minutes**; the post-crossing acceleration remains significant for **at least two hours**; results are significant for **hours, not days**.
- cost treatment: none (no P&L test), but effect sizes are informative: the round-vs-arbitrary **differential** is on the order of 0.007 percentage points, i.e. well under 1 pip on EURUSD-scale prices (`ASSUMPTION: my own unit conversion, not in the paper`); at the 15-minute horizon this is far below any realistic spread; **"Survives costs" = NOT TESTED**, and the raw magnitudes suggest the naive version would not.
- maps to a zone generator: supports two distinct zone phenomena — (i) a short-lived **reversal zone at round numbers** (<30 min) and (ii) an **acceleration zone just beyond round numbers** (≥2 h); both are time-limited, so a zone engine needs an explicit decay/horizon parameter, not a static line.
- caveats: pre-2005 sample; magnitudes are tiny relative to FX costs; "hours, not days" means any M5/M15 use must be intraday and fast.
- URL: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf [fetched — search-extracted]; https://faculty.georgetown.edu/evansm1/New%20Micro/osler1.pdf [fetched — search-extracted]
- confidence: **high** on direction and significance (publisher summary + full PDF extraction agree); **high** that costs were not tested.

### 4.4 Menkhoff & Taylor (2007), "The Obstinate Passion of Foreign Exchange Professionals: Technical Analysis"
- object: the literature on TA in FX; S/R is discussed as the most widely used chart output rather than measured separately.
- method: narrative survey; establishes stylised facts and evaluates four explanations (not-fully-rational behaviour; central-bank intervention; information processing; non-fundamental influences).
- data/sample: the FX TA literature, including dealer surveys (e.g. more than 90% of London FX participants using TA as a primary or secondary source — Allen & Taylor 1992, Lui & Mole 1998; 25–30% basing most trades on TA — Cheung & Chinn 1999; figures quoted from Osler 2000's literature summary).
- measured effect: qualitative — "applying certain technical trading rules over a sustained period may lead to significant positive excess returns", while the survey stresses that evidence is heterogeneous and sensitive to costs/data mining; it does not report a single effect size for S/R zones.
- cost treatment: survey-level discussion; costs are not normalised across studies and are flagged as a key caveat.
- maps to a zone generator: justifies S/R as a market-relevant object (near-universal use) and supports the "non-fundamental influences" explanation, the mechanism by which price-memory zones can work.
- caveats: survey, not new evidence; the "may be profitable" claim is not conditional on costs; use as motivation, not as evidence for a zone edge.
- URL: https://www.aeaweb.org/articles?id=10.1257%2Fjel.45.4.936 [fetched]; working paper http://www.econstor.eu/handle/10419/22464 [fetched — search-extracted]
- confidence: **high** on citation and abstract (AEA page fetched); **medium** on specific usage percentages (second-hand within the survey).

### 4.5 Neely & Weller (2003), "Intraday Technical Trading in the Foreign Exchange Market"
- object: trading rules (genetic program and linear forecasting) on intraday FX — not S/R levels specifically, but the best available benchmark for "does intraday FX predictability survive costs".
- method: select rules in-sample (genetic program; AR/linear forecasting model), then evaluate out-of-sample; vary the transaction cost in training/selection (0, 1, 2 bp one-way); compute break-even costs; separately restrict trading to 12 business hours.
- data/sample: intraday quotes for USD/DEM, USD/JPY, USD/CHF, GBP/USD; 25 rules per currency per cost assumption.
- measured effect: with zero costs, rules trained at zero cost produce "over 100% per annum" out-of-sample returns in three of four cases, trading roughly once an hour; the highest all-day break-even cost is **1.01 bp** one-way (GBP); for the linear model, DEM zero-cost return falls from **102% to 40%** and trades from **3,611 to 61** as the in-sample cost goes 0→2 bp, with break-even cost **19.15 bp** for DEM all-day; once trading is restricted to business hours (DEM 06:00–18:00 GMT, etc.), break-even costs fall below the level a large institutional trader would face and there is **no evidence of excess returns net of costs**.
- cost treatment: central; assumes 2.5 bp one-way as the large-institution benchmark; conclusion: predictability is real, profitability after costs is not.
- maps to a zone generator: a direct warning — a zone generator can show statistically clean conditional behaviour and still be untradeable once costs enter; the bake-off should treat break-even cost as a first-class output.
- caveats: rules are not S/R-zone-based; sample is 1990s FX; "zero-cost predictability" ≠ "tradeable edge" is the whole point.
- URL: https://files.stlouisfed.org/files/htdocs/wp/1999/99-016.pdf [fetched — search-extracted]; https://ideas.repec.org/a/eee/jimfin/v22y2003i2p223-237.html [fetched — search-extracted]
- confidence: **high** (full text extraction read; numbers quoted verbatim from the working paper).

### 4.6 Park & Irwin (2007), "What Do We Know About the Profitability of Technical Analysis?"
- object: 95 "modern" studies of technical trading profitability across FX, futures and stocks.
- method: systematic literature classification into "early" vs "modern" studies; counts of positive/negative/mixed results; critique of testing procedures.
- data/sample: 95 modern studies (exact study list in the paper).
- measured effect: **56 studies positive, 20 negative, 19 mixed.** Early studies: profitable in FX and futures, not in stocks. Modern studies: economic profits in a variety of speculative markets "at least until the early 1990s".
- cost treatment: reviewed explicitly as a weakness — "most empirical studies are subject to various problems … e.g. data snooping, ex post selection of trading rules or search technologies, and difficulties in estimation of risk and **transaction costs**." The positive counts are therefore not cost-corrected.
- maps to a zone generator: sets expectations — most published TA effects are positive *before* costs and *before* data-snooping corrections; a zone bake-off must declare costs and a snooping correction up front.
- caveats: survey; counting studies is not a meta-analysis of effect sizes; the "modern" cutoff is ~1990.
- URL: https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-6419.2007.00519.x [fetched — search-extracted]
- confidence: **high** (abstract and counts read from the publisher/RePEc pages).

### 4.7 Bajgrowicz & Scaillet (2012), "Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs"
- object: the 7,846 Sullivan–Timmermann–White trading rules (MA and trading-range/filter rules) on the DJIA.
- method: False Discovery Rate (FDR) for data-snooping control + persistence tests (monthly rule selection, genuinely out-of-sample evaluation) + transaction costs made endogenous to the selection.
- data/sample: daily DJIA, **January 1897 – July 2011**.
- measured effect: one-way proportional costs of **16, 35 and 70 bp** are enough to eliminate FDR-selected outperformance in the three sub-periods 1897–1962; in period 3 (1939–1962) **75%** of rules have positive in-sample performance before costs and costs below **25 bp** prevent the vast majority from breaking even; in period 4 (1962–1986) the positive-before-cost share falls to **44%** and most need costs below **10 bp**. Out-of-sample persistence: "an investor would never have been able to select ex ante the future best-performing rules"; no hot-hands effect.
- cost treatment: core result — even low costs offset the in-sample performance, and costs change which rules look good.
- maps to a zone generator: the strongest available ceiling — if a zone-based strategy trades frequently, assume its apparent edge is measured pre-cost and will need break-even costs well above a retail FX spread to matter; also rule/parameter selection on the same data must be FDR-aware.
- caveats: equity index, not FX; daily frequency, not M5/M15; longer sample than any FX intraday study.
- URL: https://www.sciencedirect.com/science/article/abs/pii/S0304405X1200116X [fetched — search-extracted]; full PDF https://scaillet.ch/pdfs/BajSca.pdf [fetched — search-extracted]
- confidence: **high** (abstract + full-text extraction read; exact bp figures quoted from the PDF text).

### 4.8 Lo, Mamaysky & Wang (2000), "Foundations of Technical Analysis"
- object: automatic **local extrema and geometric patterns** (head-and-shoulders, double tops/bottoms, etc.) — the closest academic object to swing-point zones.
- method: nonparametric **kernel regression** (Nadaraya–Watson smoother) to filter noise; local maxima/minima of the smoothed series define pivots; pattern templates (e.g. HS, BTOP, DBOT) matched on those extrema; conditional vs unconditional return distributions compared with goodness-of-fit tests and Monte Carlo calibration.
- data/sample: several hundred US stocks, **1962–1996** (31 years), NYSE/AMEX and Nasdaq.
- measured effect: conditional return distributions differ significantly from the unconditional for **7 of 10 patterns on NYSE/AMEX** (exceptions: BBOT p = 5.1%, TTOP p = 21.2%, DBOT p = 16.6%) and for **all 10 patterns on Nasdaq**; the paper concludes several indicators "do provide incremental information and may have some practical value" — informativeness ≠ profitability (explicit).
- cost treatment: none (the test is distributional, not P&L); **"Survives costs" = NOT TESTED.**
- maps to a zone generator: the kernel-regression + local-extrema pipeline is a direct, citable precedent for the KDE/clustering approach — smooth first, extract extrema second, define zones around them; also gives an academic precedent for testing zones by comparing conditional vs unconditional next-k-bar return distributions rather than only P&L.
- caveats: equity daily data; pattern templates are not S/R zones; no costs; the paper's own tone is "mixed support".
- URL: https://web.mit.edu/Alo/www/Papers/1705-1765.pdf [fetched — search-extracted]; NBER w7613 [fetched — search-extracted]
- confidence: **high** (abstract + full-text extraction read).

### 4.9 Round-number barriers: Mitchell & Izan (2006); De Grauwe & Decupere (1992); Westerhoff (2003)
- object: last-digit clustering and **round-number barriers** in FX (whole numbers, 00/50 levels); barriers behave as resistance before the level and as acceleration after the crossing — i.e. zonal in time, not static lines.
- method: (i) frequency tests on trailing digits plus "passing"/transgression tests against simulated benchmark series; (ii) barrier tests on USD/DEM and USD/JPY; (iii) a deterministic chartist–fundamentalist model where the perceived fundamental is anchored to the nearest round number.
- data/sample: (i) daily AUD crosses (DEM, FRF, ITL, GBP, CHF, USD, JPY vs AUD), **1 Jan 1978 – 31 Dec 1992** (FRF from 1981); (ii) USD/DEM and USD/JPY (1980s); (iii) simulation only, no data.
- measured effect: (i) **widespread clustering** in exchange-rate digits — "there is partial information content in the actual numbers of the exchange rates themselves" — but only "some, but not strong, evidence" that psychological barriers exist; the location and form of both clustering and transgressional effects differ across pairs and are "in most instances … not in the expected direction". (ii) Barriers **significant in USD/JPY** (rates resist 130, 140, … yen/dollar, then accelerate away once crossed); evidence for USD/DEM "less clear-cut". (iii) The model generates bands around anchors that resemble support/resistance levels and produces persistent misalignment, excessive volatility and volatility clustering as stylised outcomes; no empirical effect size.
- cost treatment: none in any of the three (statistical/behavioural tests).
- maps to a zone generator: round-number grids are a cheap, zero-parameter zone generator (levels ending in 00/50, and possibly 25/75 for EURUSD quarter zones); the literature supports the mechanism but (i) and (ii) disagree on robustness, and (iii) shows the effect can be model-endogenous rather than a market fact.
- caveats: (i) daily 1978–1992, AUD crosses; (ii) 1980s; (iii) purely theoretical; the mixed replication record is the key input — round numbers deserve a slot in the bake-off, not a default role.
- URL: (i) https://doi.org/10.1016/j.intfin.2005.03.003 and https://www.sciencedirect.com/science/article/abs/pii/S1042443105000508 [fetched — search-extracted]; (ii) https://cepr.org/publications/dp621 [fetched]; (iii) https://www.uni-bamberg.de/fileadmin/uni/fakultaeten/sowi_lehrstuehle/vwl_wirtschaftspolitik/Team/Westerhoff/Publications/2003/2003_Westerhoff_VIII.pdf [fetched — search-extracted]
- confidence: **high** on citations and on the mixed nature of the evidence; **medium** on effect magnitudes (different eras, different definitions of barrier).

### 4.10 Brock, Lakonishok & LeBaron (1992), "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns"
- object: two rule families — moving-average oscillator and **trading-range break** (`TRB`); the TRB is literally an S/R-breakout generator: buy when price exceeds the resistance level (highest high of the past 50/150/200 days), sell when it falls below the support level (lowest low), with a 1% band variant.
- method: standard t-tests plus bootstrap inference against four null models (random walk, AR(1), GARCH-M, EGARCH); comparison of returns following buy vs sell signals, including volatility and sign fractions.
- data/sample: Dow Jones Industrial Average, **1897–1986** (90 years), daily.
- measured effect: for the variable-length moving-average rules, buy periods average **+0.042% per day (~12% p.a.)**, sell periods average **−0.025% per day (~−7% p.a.)**, against an unconditional **+0.017% per day**; the fraction of positive days is ~53–54% for buys vs ~49% for sells; buy-sell differences are positive and mostly significant. The paper states the TRB (support/resistance breakout) results also support the technical strategies and that returns are inconsistent with all four null models; sell-signal returns being negative is the result hardest to reconcile with equilibrium models. (The precise VMA numbers above are the ones read from the paper; the TRB table was not extracted numerically.)
- cost treatment: no transaction costs are applied; the paper is the canonical pre-cost result and the direct target of later cost/data-snooping critiques (4.6, 4.7); **"Survives costs" = NOT TESTED.**
- maps to a zone generator: the TRB rule is the simplest possible S/R zone-breakout logic and provides the shape of a zone-physics hypothesis — "break of a multi-month extreme → continuation"; it also sets the bar for statistical hygiene (bootstrap vs null models) that a bake-off should copy.
- caveats: equity index, daily, pre-cost, pre-data-snooping-correction; 4.7 shows the performance is offset by low costs and not ex-ante selectable.
- URL: https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04681.x [fetched — search-extracted]; full PDF mirror https://finance.martinsewell.com/stylized-facts/distribution/BrockLakonishokLeBaron1992.pdf [fetched — search-extracted]
- confidence: **high** on citation/sample/qualitative result; **high** on the quoted VMA numbers (read from the paper text); **medium** on TRB-specific magnitudes.

---

## 5. What the legacy repo already killed in this space

18 entries from `_legacy_kills.md`, each with the exact metric quoted in the source. Scope note carried from the source: the catalog is an evidence catalog, not a family blacklist — each entry blocks only its bound hypothesis/candidate identity and direct post-hoc rescue; a materially new mechanism under a new ID with a declared delta may proceed. Charter context (`PA_PRO_CHARTER.md:15-24`): the VPA DR3 "micro-line + tight-stop object is dead"; dead families include "pin bar, engulfing, fractal, order block, OTE, ICT FVG chains, liquidity sweeps at PDH/PDL/Asia range (PF 0.56-1.01), round-number fade (PF 0.74 on 26,819 trades), ORB/session breakouts (regime pockets), inside-bar/squeeze compression, VWAP family, z-fade mean reversion (8,100 sims, max gross PF 1.25), exit overlays, AND-stacks". ERA-2 board: "Cost drag is ~30% of PF: median cost PF x1.0 ≈ 0.68 vs gross ≈ 0.83. Even a hypothetically break-even gross signal cannot reach 1.30." Any kill below is a trade-strategy/PnL verdict, not a zone-reaction measurement.

1. **Round-number FADE (00/50 touch-and-reverse)** — `HYP-RND-GB-M5-001` / `EA_Rnd`, GBPUSD M5 with H4 EMA filter, 1.5xATR stop / 1.5R target, window 1999.01.01–2026.09.11, run `20260912_134228`. Metric: verdict `KILLED_AT_MODEL_0`, reason "gross PF 0.742, net -9200, DD 92.0%, cost PF x1.0=0.677 x1.5=0.627 x2.0=0.581. Cadence 18.6/wk PASS but economics gross-negative."; `"trades":26819`, `"profit_factor":0.7422722490091693`, `"net_profit":-9200.19`, `"max_drawdown_pct":92.02802416480958`, `"win_rate_pct":38.5`, cost PF 0.676961499 / 0.626886964 / 0.580726287, `"nonrepaint_audit":"PASS"`; charter states "round-number fade (PF 0.74 on 26,819 trades)". Why a zone-physics event study is a different question: the kill tested a touch-and-fade *trade* (entry, stop, target, cost) at the round grid; it never measured the conditional reaction proportion at real 00/50 levels vs matched fake levels at the same time/side/distance/width. Different question, no fills.
2. **Round-number cascade / round-grid continuation (EURUSD M5)** — `HYP-ROUND-CASCADE-EURUSD-M5-001..011`. TRUE arm vs SHIFTED-grid control; source probes: `TRUE_0050 produced 1,229 signals at 4.7166 per elapsed week and SHIFTED_0025 produced 1,220 at 4.6820`; eligible population `2,431 rows (TRUE=1,218; SHIFTED=1,213)`. Metric (HYP-011, 1.50 pips): "the TRUE arm produced PF=0.6762, mean=-0.12339R, total=-150.28R, zero positive years, DSR=1.55e-7 and 32.54% compounding drawdown; only cadence passed, while ten of eleven frozen gates failed. Higher costs worsened PF to 0.5655 and 0.4747. The SHIFTED control was also negative, and TRUE-minus-SHIFTED separation was far below the frozen thresholds." Different question: it measured traded PnL on grid crossings; its control was a grid shifted by 25 pips, not fake zones matched per event on time, side, distance and width — do not cite HYP-011 as proof that "round levels do nothing" or that "they matter".
3. **PDH/PDL closed-bar sweep-reclaim fade (XAUUSD H1)** — `HYP-SWEEPFADE-XAUUSD-H1-001`, train run `20260816_130548`. Metric: "HQ 99% / N=1150 / PF 1.01 / net +85 / DD 4.70% / exp +0.07. Six years PF 0.78–1.21 around 1; none ≥1.30. Exit mix SL-like ~48% / TP-like ~29% / DAILY_FLAT ~17% / FRIDAY_FLAT ~5% / TIME_STOP ~0 — no single exit defect."; radius is this PDH/PDL fade envelope only. Different question: the fade trade's PF ~1.0 says the entry/exit/cost structure had no edge, not that price does not react at PDH/PDL; the R01 event is a fresh approach census with no order, stop or target.
4. **Multi-level liquidity-sweep reversion (EA_LiquiditySweep, EUR + XAU M5)** — `HYP-LSWEEP-EUR-M5-001`, `HYP-LSWEEP-XAU-M5-001`; Osler-2003 stop-cluster reversion, `InpRoundStep` 0.0050 EURUSD / 5.0 XAUUSD, 1.3R / 24-bar, governed Model 0. Metric EUR: "Trades | **172 — cadence 0.12/wk, FAIL outright**", "Report PF / Net / DD | 0.68 / -887 USD / 10.0%", "Cost PF x1.0 / x1.5 / x2.0 | **0.620** / 0.592 / 0.566"; registry `"profit_factor":0.6776`, `"cost_pf_x1_00":0.6196`, WR 28.5%. Metric XAU: "N=136, report PF=0.556, net -950 USD, max DD 9.9%, WR 26.5%. Cadence FAIL outright", `"PF 0.479 @x1.0, 0.443 @x1.5, 0.411 @x2.0"`; mechanism "hiếm một cách cấu trúc (~6 sweep/năm)" on both EUR and XAU. Different question: both sleeves are sweep-reversion trades that died on cadence/cost, not on whether the swept level is a zone where price reacts; R01's fresh-approach census does not require the sweep event and takes no fill.
5. **Prior-day-liquidity raid → displacement/MSS → FVG (KLR, XAU M5)** — `HYP-KLR-USD-PDLRAID-M5-XAU-001`, `HYP-KLR-MT5-REPLICATION-M5-XAU-001`. Metric offline: "Frozen 2022-2024 probe produced 210 prior-day raids, 42 displacement+MSS events, 16 FVGs and 3 retests, but only 2 ungated core trades (0.0128/week, PF 0, -1.5083R) and zero USD-aligned challenger trades. Nine of eleven gates failed"; metrics `"sweeps":210`, `"sweep_control_profit_factor":0.414160282`, `"sweep_control_net_r":-54.329372682`. Metric MT5: "KILL_AT_MODEL0_CADENCE_REPLICATION … the core produced 4 trades (0.02555/week) … over 156.57 elapsed weeks"; `"native_sweeps":346`, `"native_displacements":61`, `"native_strict_fvgs":26`. Different question: the full trade chain died on event rarity and economics; R01 measures whether a fresh approach to a real zone bounces more than at a matched fake zone, with the raid/MSS/FVG chain removed entirely.
6. **Range / session / weekly-extreme level fades (Asia, W1, Camarilla, ORF)** — `HYP-ASIA-GB-M5-001`, `HYP-W1-GB-M5-001`, `HYP-CAMF-EU-M15-001`, `HYP-ORF-GB-M5-001`. Metric Asia: "Gross PF 0.770, net -4953 USD, DD 49.7% over 27.7y; cadence ~4.2/wk below floor; cost PF x1.0 0.663 / x1.5 0.612 / x2.0 0.565"; `"trades":6119`. Metric W1: "Gross PF 0.552, net -97 USD, only 42 trades over 27.7y = 0.03/wk - weekly extremes almost never touched intraday; cadence catastrophic". Metric CAMF: "Trades | 14,755 — cadence **10.21/wk PASS**", "Report PF / Net / DD | 0.886 / -5,458 USD / 57.1%", "Cost PF x1.0 / x1.5 / x2.0 | **0.763** / 0.702 / 0.646". Metric ORF: "gross PF 0.822, net -4673, DD 47.3%, cost PF x1.0=0.712 x1.5=0.657 x2.0=0.606. Cadence 5.4/wk below 10/wk floor." Different question: each is a fade strategy at a range boundary or daily/weekly level with stop/target/cost and no per-event matched fake-zone control; R01 supplies the missing reaction measurement and is not a fade entry.

7. **Session-VWAP deviation fade + VRAS VWAP/fractal object** — `HYP-VWF-XAU-M5-001` / `EA_VwapFade`; `HYP-VRAS-EURUSD-M5-003/004/005/006/008`. Metric VWF: "Trades | 25,417 (~8.6/week — below 10–40 cadence band)", "Report PF | 0.87; Net -7,645 USD; Max DD 76.8%; WR 43.8%", "Cost-bound PF | **0.50** @x1.0 / **0.38** @x1.5 / **0.29** @x2.0". Metric VRAS seven-gap: "N=93, PF0.5914, net -$5,243.22 and only 0.4465 trades/elapsed week; Range PF0.1331 and Trend PF0.6412 both failed."; HYP-005: "Net Profit -$10,040.86, PF 0.74, WR 44.72% (144W/178L), Expectancy -$31.18/trade, Equity DD 12.71%, Balance DD 12.45%, Cadence 28.69 trades/week"; path-confirmed: "full challenger PF was 0.8996 with negative expectancy, only 1.385 trades/week and 252 total trades", "The filter improved PF by only 0.0069 and mean realized R by 0.0065R"; tick-plane: "VWAP reversion (AUDUSD ticks, 110d): dead, PF 0.42-0.58 at all thresholds — tick deviations continue rather than revert." Refusal row R10: "VWAP / session-VWAP / AVWAP deviation fade or reclaim … Whole family dead including the VRAS seven-gap object". Different question: VWAP is a running volume-weighted mean, not a horizontal support/resistance zone formed by price structure; these were fade/reclaim trades with stops and targets, and R01's objects are swing-clustered zones and reference levels with matched fakes.
8. **Volume-clock exhaustion (time/volume-at-level fade, VCEX)** — `HYP-VCEX-EURUSD-M15-002` / `EA_VolumeClockExhaustion`, 807 matched TRUE fade and FOLLOW_CONTROL continuation pairs (public DESIGN). Metric: "At 1.50 pips TRUE PF was 0.655314, mean -0.201794R, total -162.848100R, fixed-initial-equity DD 83.0077%, DSR `2.22e-9`, and positive years 0/5. TRUE was slightly worse than FOLLOW_CONTROL (PF delta -0.004031; mean-R delta -0.002629), so flipping polarity does not rescue the mechanism."; "Only cadence passed (`1/11` gates)."; "Failure radius is the exact VCEX M15 tau0.40/early0.45ATR/exhaustion0.30/07-16UTC/max-one-per-day/120-minute/source-stop/1R-TP object on these 807 pairs." Different question: VCEX is a volume-time exhaustion fade with a 120-minute horizon; its "exhaustion" variable is clock/volume state, not distance-to-a-real-zone versus a matched fake.
9. **Volume-profile POC / value-area reversion** — no hypothesis/EA/metric found: a word-boundary search for `POC`, `value area`, `market profile`, `volume profile` across `04. Memory/` and `03. EA Developer/` returns no matching hypothesis, EA or metric. Evidence: NOT FOUND. Nearest tested object is the VWAP family (§7 above; `HYP-VWF-XAU-M5-001`, VRAS, tick VWAP "PF 0.42-0.58 at all thresholds"); those are volume-weighted means, not POC/value-area histograms. Different question: no legacy evidence exists either way; PA-PRO must not cite a POC kill that does not exist — if a POC/value-area family is proposed later it needs its own de-dup against the VWAP family and a fresh prereg.
10. **3-bar FVG continuation (EA_FVG, EURUSD M15)** — `HYP-FVG-EU-M15-001`, 1 ATR / 8-bar, governed Model 0, 1999.01.01–2026.09.11. Metric: "29,370 trades (~20.3/wk PASS), PF **0.776**, net **−$9,259**, DD **92.6%**, WR 31.0%.", "Cost PF x1.0 **0.686** / x1.5 0.627 / x2.0 0.574.", "**Verdict: KILL.** Price-void continuation is gross-negative." Different question: it tests whether an imbalance gap persists, not whether price reacts at a zone versus a matched fake zone; R01's zones are swing clusters and reference levels, FVG is not required and no continuation position is taken.
11. **ICT FVG report-fidelity chain (HYP-ICT-FVG-007..026) + FVG confluence de-dup** — `EA_ICTFVGReportFidelity`, `EA_FVGConfluence`, `HYP-H1-DISPLACE-FVG-CONT-001`, 2018–2026. Metrics: HYP-012 "3,385 positions, PF 0.8104, -0.09799R/position, 7.592 trades/week and zero positive entry years"; HYP-011 "returned PF 0.7588, -0.13775R per defined-risk position, 9.736 trades/week and PF<1 after commission in every entry year"; HYP-010 "2,070 exactly reconciled positions, 9.925 trades per elapsed week, PF 0.7625, -0.1348R/trade and negative net/PF<1 in every year"; HYP-008 "it lost USD 7,944.29 at PF 0.5774 and 0.585 trades/week"; HYP-007 "produced 12,340 sweeps, 293 displacement/FVG events, 149 closed-M15 MSS events, 144 pre-MSS mitigations, one valid first retest, one ADX rejection and zero entries/trades."; HYP-017 "PF 0.7553; after the frozen additional 1.5-pip diagnostic PF was 0.3513 and expectancy -0.52139R/trade with week-block 95% CI `[-0.55998,-0.48317]`"; HYP-014 "PF 0.9577, -0.01577R/accepted trade and -0.0000927R/opportunity"; HYP-022 "659 repeated-churn cases among 6,399 defined confirmations (10.2985%, 1.477578/elapsed week)"; HYP-024 "FAVORABLE_DOMINANT in 6,396 and ADVERSE_DOMINANT in only 3 (0.04688%, 0.006726/week)"; HYP-026 "pivot-relative ADVERSE_DOMINANT was only 181 (2.8290%, 0.40583/week) versus 6,217 favorable rows"; confluence de-dup: "Its M5 three-candle FVG plus 40-60% fill/rejection is the same primary object as killed `HYP-H1-DISPLACE-FVG-CONT-001`; HTF BOS, OB, premium/discount, liquidity sweep, session and management scoring only densify the dead price-only family." Different question: the whole chain is an entry sequence with tight sweep-extreme stops; R01 has no sweep, no displacement, no FVG, no MSS and no fill — a conditional reaction census on real vs matched fake zones.
12. **Order-block / SMC report-fidelity (LSS-OB, Unicorn, PO3-AMD, DRAT)** — `HYP-LSS-OB-REPL-EURUSD-M15-001/002`; `HYP-UPSC-XAU-M5-002`, `HYP-UPS-XAU-M5-006/007/008`; `HYP-PO3-AMD-SCALP-M5-XAU-001/002/003`; `HYP-DRAT-ONNX-ICT-M15-EUR-001`. Metrics: LSS-OB offline "Over 2019-2022 it has only 383 upstream context-aligned sweeps versus the frozen cadence floor of 417 before any downstream rejection; the full challenger has zero events."; archived `"context_aligned_sweeps":383`, `"displacement_fvg":0`, `"valid_ob_fvg_overlap":0`, `"challenger_events":0`; native "Both produced 388 context-aligned sweeps but zero 1.8x-ATR displacement/FVG, zero entries and zero trades."; Unicorn four-bar "N=138, 1.334/week, report PF 0.986/net -$233.83; research full-cost PF 0.688, x1.5 0.574, x2 0.481; robustness 0%, MC P95 DD 5.654%"; Unicorn event-anchored "N=130, 1.257/week, report PF 0.724/net -$4,396.90; research full-cost PF 0.498, x1.5 0.413, x2 0.343; robustness 0%, MC P95 DD 7.118%, equity REJECT."; Unicorn FVG-CE limit "115/251 fills in 3 bars, 45.82% fill rate, 1.110/week, 87 long/28 short."; Unicorn RR1.5 "N=132, WR 35.606%, report PF 0.697/net -$4,904.75, full-cost PF 0.475/x1.5 0.391/x2 0.322"; PO3-AMD v1 "only 6 dates met the frozen 80..300-point Asian range; sweep control N=1, full PO3 N=0", v2 "121 sweeps -> 1 displacement+MSS -> 1 FVG -> 0 retests; control N=36, PF 0.511, -10.71R", v3 "122 sweeps -> 0 displacement+MSS; control N=37, PF 0.674, -5.42R and all three years negative; challenger N=0"; DRAT "rules-only PF 0.764 / -67.75R; ONNX gate PF 0.749 / -52.82R; all year buckets negative". Display note: "Raw BOS/MSS/void flags are structural facts, not entries" and "Snapshots are not a backtest." Different question: all four families are complete SMC trade chains with entries, structural stops and targets; none measured whether price reacts at a real OB/SMC zone more than at a matched fake zone.

13. **Fractal / confirmed-pivot setups (ASRS, SCC)** — `HYP-ASRS-EURUSD-M5-001` / `EA_ASRS_AdaptiveSweepReclaim`; `HYP-SCC-EURUSD-M5-001`, `HYP-SCC-MT5-REPLICATION-EURUSD-M5-002/003/004` / `EA_SweepCascadeContinuation`. Metric ASRS (Stage-0 park, no outcome): "280 candidates (1.3415/elapsed week), median risk 7.9482 pip, median/p75 1.5-pip proxy cost 0.1887R/0.2874R, and max year concentration 29.29%"; "only 45.81% of all volume-qualified events occurred inside the report's London-NY wall, below the frozen 50% materiality floor. This is PARK with zero outcome, not an economic edge verdict." Metric SCC Stage-0: "1,242 raw daily BREAK arms, 878 HOLD passes and 286 accepted retests = 1.3703 per elapsed week. Pooled and every-year cadence missed the frozen 2.0/week floor; N missed 418."; "median/p25 risk was only 3.1866/2.1107 pip; a 1.5-pip RT proxy consumed median/p75 0.4707R/0.7107R before commission/slippage." Metric SCC Model 0: "The raw first-close BREAK control lost with N1112, PF0.698096 and mean realized R=-0.215618. HOLD→retest reduced fills to N261 but also lost with PF0.691278 and mean R=-0.231790"; "fixed 1.5-pip stress reduced PF to 0.354074, and only one of four calendar years had PF>1." Different question: ASRS/SCC are sweep-reclaim and break-retest continuation trades on fractal/pivot objects with tight stops, killed on cadence/geometry or PnL; R01's objects are multi-scale swing-cluster zones with touches/role-flip/age, not N=2 fractals, and R01 takes no trade.
14. **DR3 micro-barrier Volman pattern break (EA_VolmanPA / ECON-1)** — `HYP-VPA-EURUSD-M5-001`, stop 8 pips / target 2R, DESIGN 2016-2021, matched random bracket control (K=20, 84,320 entries / 42,257 fills). Metric: gate table — "| PF x1 > 1.30 | x1 | 0.795 | > 1.3 | FAIL |", "| gross PF >= 1.10 | gross | 0.992 | >= 1.1 | FAIL |", "| N >= 500 | x1 | 2436 | >= 500 | PASS |", "| LIFT x1 >= +14.1pp | x1 | +0.24pp (CI [-1.61, +2.14]) | >= 14.1 | FAIL |"; per-scenario gross 0.992 / x1 0.795 / x2 0.667; "Fills 2436; final equity at 0.5%/trade: **17.6%** of start; max DD **84.19%**"; charter: "gross PF 0.992, x1 PF 0.795, lift vs matched random +0.24pp, CI [-1.61, +2.14], every year negative. … The micro-line + tight-stop object is dead." Different question: ECON-1 shows the pattern-break trade is cost-dominated and does not beat a matched random bracket, not that price fails to react at real zones; the matched-random control was random entries, not fake zones at matched geometry, and R01 replaces micro-lines with scored multi-touch zones and takes no fill.
15. **Tight-stop sweep objects (ICTVIS visual feature discovery)** — `HYP-ICTVIS-EURUSD-M5-001`, 39,122 DESIGN events. Metric: "The generous M5 sweep-reversion universe is near-random gross (PF 1.019 at zero cost) and its stops are too tight (median 4.5 pips) for realistic EURUSD cost; even the best in-sample DESIGN feature selection (range-position + wick morphology) posts PF 0.573 at 1.5 pip RT and dies by 0.5 pip."; metrics `"design_n":39122`, `"universe_pf_zero_cost":1.019`, `"top10_pf_zero_cost":1.12`, `"top10_pf_050pip":0.887`, `"top10_pf_150pip":0.573`, `"risk_pip_median":4.5`, `"F5_rangepos_rho":0.886`, `"F4_wick_rho":-0.915`. Different question: the verdict is about cost/stop geometry in a tight-stop sweep trade object; R01 has no stops and no cost drag at all — a no-fill reaction census, so the cost axis that killed ICTVIS cannot apply.
16. **Day-open sweep fade probe (withdrawn, not a kill to cite)** — 2026-09-18 day-boundary Stage-0 probe, M5 bars 00:00–00:30 server piercing the prior-6h range → fade, next-bar-open entry, 1–4 h hold, 7 majors; claimed per-bar PF 1.45–5.56 (e.g. NZDUSD 5.56, USDCHF 3.88, AUDUSD 5.12; EURUSD 1.45). Metric: "deep-history event-level verification (M1 .hcc, 2010→2025) FALSIFIED the pierce-fade claim below — up-pierces CONTINUE (fade loses −2 to −7.7p, win 15–35%, all symbols all years). The verified mechanism is **roll-reopen gap reversion**, not sweep-fade."; "Treat all "fade PF 1.45–5.56" numbers here as withdrawn." Different question: no real-vs-fake zone control and no reaction-probability measurement; R01's event is a fresh approach to an existing zone, not a day-open pierce.
17. **Detrended-z mean reversion grid (MR-GRID) — boundary case** — `HYP-MR-GRID-EURUSD-H1-002` (`HYP-MR-REGIME-EURUSD-H1-001` stays terminal); EURUSD H1 std-normalized detrended-z, full legal variant grid, 2015-2022 unsealed splits, DSR over the full trial count. Metric: "the grid ran and the family IS `CLOSED_EXHAUSTIVE`. 8100 simulations, ZERO arms reached the necessary condition gross PF ≥ 1.25 (max 1.2476, median 0.8902); max net PF@x1 anywhere 1.0991; best deflated arm DSR 0.0129 vs floor 0.95 with negative expectancy; Stage-2 auto-skipped. The failure is the object, not the tuning." Different question: the MR object is a statistical price-deviation z, not a support/resistance zone, and the grid is a trade strategy with stops/targets; R01 measures geometry-defined zones against matched fakes with no strategy and no tuning grid.
18. **Liquidity-vacuum overshoot reversal (LVOR) — no market verdict** — `HYP-LVOR-EURUSD-M15-001/002/003` / `EA_LiquidityVacuumOvershootReversal` (ghost package). Metric: HYP-003 parked row `"SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"` — "PRIMARY produced 197 source-executable candidates over 260.5714 elapsed calendar weeks, or 0.7560 per week, below the preregistered 2.0 minimum."; HYP-001/002 are `"ENGINEERING_INVALID_NO_MARKET_VERDICT"` (schema-guard false positives). De-dup note: "no readout; … no verdict exists, so it is not a kill but cannot be cited as evidence either". Different question: there is no market verdict at all, so it must not be cited in either direction; R01 is unaffected.

### Zone physics is a different question

- PA-PRO R01 tests one question only: does price react at REAL zones more than at MATCHED FAKE zones? Outcome = BOUNCE / BREAK / NONE proportions over ≤ 48 M5 bars with symmetric barriers m = 1.0 × ATR14(H1) from the zone edge (`PA_PRO_CHARTER.md:105-118`). It is an event study: no orders, no fills, no PnL, no stop, no target.
- **This task computes NO outcomes: no bounce/break rates, no returns, no win rates. Those belong to the preregistered R01 physics run.** The killed families above are trade strategies (entry + stop + target + cost) on the same objects; their verdicts measure PnL, not reaction probability. None of them measured P(BOUNCE | real zone) minus P(BOUNCE | matched fake zone).
- R01's control is per-event matched fake zones: K=5, same time, same side, same distance from price, same width, placed where no real zone or reference level is within 2 widths (`PA_PRO_CHARTER.md:111-113`). Legacy controls were shifted grids (HYP-011), random entries (ECON-1), or no control at all — they do not pre-empt this design.
- The cost drag that killed the legacy board (~30% of PF; `20260912_ERA2_FALSIFICATION_BOARD.md:44`) does not apply to R01 because R01 books no trades; conversely, a positive R01 result is not evidence of a cost-feasible edge.
- R01 is forbidden from being turned into any killed strategy by rename or parameter change: no round-number fade/continuation, no PDH/PDL sweep fade or reclaim, no Asia/weekly/Camarilla/session-open range fade, no VWAP or volume-clock fade, no FVG/OB/SMC/ICT chain, no DR3 micro-line break, no fractal-sweep or pivot-retest trade, no tight-stop sweep object. The refusal table `HYPOTHESIS_BANK.md:1034-1057` (R1-R18) already encodes these rows.
- If LINES MATTER passes, it licenses only the next preregistered setup family (F1-F9) with structural stops ≥ 10 × c_rt (`PA_PRO_CHARTER.md:100`); it does not revive any killed hypothesis ID and does not authorize a trade on the R01 event set. A setup built on R01 must be a new hypothesis with a stated mechanism delta and its own frozen prereg.

---

## 6. Recommendations feeding SHORTLIST.md

This is a recommendation; the shortlist itself is written by the worker. The surveyed pool is large enough for the ≥ 12 generators required.

### 6.1 Dedup map — which surveyed candidates are the same structural idea

- **Pivot-cluster horizontal S/R (the largest family).** MT4/5: 1.1 Shved, 1.2 Smart S/R Zones, 1.5 ATR Ranked, 1.6 PAZ, 1.8 Miron; TV: 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.12 all share the same primitive (`pivothigh`/`pivotlow` + cluster/merge + strength); Python primitives: 3.1 ZigZag, 3.6 Fractals, 3.9 `argrelextrema`, with 3.3/3.4 KDE and 3.7/3.8 clustering as the merge step. Pick one representative per *structural choice*: confirmation lag (`rightBars` vs `strength` vs ZigZag reversal), width model (range % vs ATR vs average bar range vs fixed pips vs cluster span), and strength definition (touch count vs bar-touch scan vs composite score vs test count vs density height).
- **ZigZag family.** 1.4 SNR zigzag ⊃ 1.7 ZigZag S/R Detection; 1.12 FXSSI is the closed ZigZag+histogram variant; 2.14 TV built-in Zig Zag; 3.1 PyPI `zigzag` is the Python implementation. One implementation with different confirmation rules covers most of these.
- **Base-impulse / leg-based supply-demand.** 1.3 ExMachina (same-TF multi-bar impulse) vs 1.10 Liquidity Zone Flips (HTF base-impulse + role flip); TV: 2.8 leg-in/base/leg-out, 2.10 SMC, 2.11 TradingFinder OB; 1.11 SRSI is swing+test-count, adjacent but not impulse-based.
- **Volume-at-price / value area.** 1.9 MT5 Volume Profile Levels, 3.5 `marketprofile`, 2.15 TV Volume Profile; 2.9 Visible Range variant is the same family with a zoom-dependent window. One implementation with two parameter sets (session anchor, 70 % VA) is enough.
- **Density/clustering zone builders.** 3.3 and 3.4 are the same KDE idea (choose one); 3.7 clusters swing prices (KMeans/MeanShift/jenkspy), 3.8 is the practitioner recipe combining swing extraction + tolerance clustering + KDE, and 3.9 is the minimal swing primitive underneath.
- **Sloping channels.** 2.7 Trendlines with Breaks is the only surveyed representative; a linear-regression channel can be added cheaply in Python as a second arm.
- **Round numbers.** Not an indicator but a zero-parameter generator (build from 4.2/4.3/4.9 — 00/50 levels, optionally 25/75 for EURUSD); the legacy kill family (5.§1–2) is its trade-strategy cousin and does not pre-empt the reaction census.
- Lineage note: Shved is the ancestor of the paid MQL Ideas "Support/Resistance Zones" dashboard (vendor states it is based on Shved) — do not treat them as independent.

### 6.2 Licence traps

- **GPL-3.0 (copyleft):** 1.6 PAZ — a clean-room Python reimplementation of the *algorithm* is fine, but copying its code would infect the pipeline; also `freqtrade/technical` and `backtrader` under 3.2 — prefer permissive implementations or the in-repo 4-line formulas.
- **MPL 2.0:** 2.5 Support Resistance Channels and (inferred) 2.6 — file-level copyleft for copies of the source; clean-room reimplementation is fine.
- **CC BY-NC-SA 4.0 (non-commercial + share-alike):** 2.1, 2.2, 2.7, 2.10; also assume non-commercial for LuxAlgo 2.3/2.4/2.8/2.9 where the licence is `unknown (source: unverified)`. Ideas may be re-implemented clean-room for internal research; code must not be copied into a product.
- **MetaQuotes articles ("all rights reserved; copying prohibited"):** 1.10 Liquidity Zone Flips, 1.11 SRSI — do not copy their code; the algorithms may inform a reimplementation.
- **MQL5 CodeBase:** no licence stated (1.1, 1.2, 1.3, 1.5, 1.7, 1.9, 1.4) — reference-only, do not redistribute source.
- **Closed/proprietary (benchmark only, never in the Python pipeline):** 1.12 FXSSI, 1.13 Advanced Supply Demand, 1.14 Supports And Resistances Lines, 1.15 PZ; TradingView built-ins 2.13–2.15 (proprietary; algorithm reference only, as stated in §2).
- **Permissive and safe:** 1.8 Miron (MIT), 3.1 BSD-3, 3.2 `stock-indicators` Apache-2.0, 3.3/3.4/3.9 BSD-3, 3.5 BSD-3 (stale package — reimplement the logic on closed bars rather than depending on it), 3.6 Apache-2.0, 3.7 sklearn BSD-3 + jenkspy MIT (`kneed` unverified).
- **Unknown/unverified:** 2.12 Auto S/R, 2.11 Order Blocks Finder, 2.3/2.4/2.8/2.9 LuxAlgo licences, 3.8 tutorial code (site copyright; `boysugi20` repo no licence → treat as reference, re-implement).

### 6.3 Realistic to re-implement causally in < 200 lines (Python, offline)

- **Easy (≈20–80 lines):** 1.8 Miron (~40), 1.9 Volume Profile POC/VA (~80), 1.11 SRSI (~80 with fixed-pip proximity converted to ATR), 2.1 two levels + volume filter, 2.5 pivot clustering + strength + greedy select, 2.7 pivot + ATR-slope line, 2.13 pivot primitive, 2.14-confirmed-only ZigZag, 2.3 pivot zones + touch counters + merge, 3.1 wrapper (~10 lines around the library), 3.2 classic pivots (~20), 3.3/3.4 KDE (~30 once the swing sample exists), 3.6 fractals (~20 with the `S`-bar delay), 3.9 `argrelextrema` + tolerance clustering (~60), round-number grid (~10).
- **Moderate (~120–180):** 1.1 Shved (~180: fractals + ATR zone build + verified/proven/broken state machine), 1.2 Smart S/R Zones core (~120), 1.3 ExMachina (~150–180), 1.4 SNR zigzag (~150), 1.5 ATR Ranked (~150), 1.6 PAZ core (~130), 1.10 Liquidity Zone Flips (~120 but must replay flips, not just draw them), 2.8 leg-in/base/leg-out detector (~150), 2.9 fixed-window volume bins, 2.12 same family as 2.3 with ATR merge/buffer (unverified), 3.5 profile value area (~80 if reimplemented from the `marketprofile` logic on closed bars).
- **Heavy first round:** 2.2 (MTF event machine), 2.4 (four engines + filters), 2.6 (HTF security + visible-range filter), 2.10 (structure + OB + FVG + EQH/EQL + MTF). Realistically two heavy items for the first round: **ZigZag+merge** and **KDE+merge**; everything else is an axis (width rule, round numbers).

### 6.4 The three structural families the shortlist should draw from

1. **Pivot-cluster zones with ATR-scaled widths and touch/test-count strength** — the family with the most causal-by-design implementations (1.1 Shved, 1.2 Smart S/R, 1.5 ATR Ranked, 1.6 PAZ, 2.3, 2.5; primitives 3.1/3.6/3.9; merge variants 3.3/3.4/3.7). Representative scale choices: ATR merge (PAZ/ATR Ranked), range % (2.5), average bar range (2.3).
2. **Base-impulse / leg-based supply-demand zones** — object built from the candle(s) that produced a displacement (1.3 ExMachina, 1.10 Liquidity Zone Flips, 2.8 leg-in/base/leg-out; OB variants 2.10/2.11 as secondary references). Strength/freshness comes from impulse size, base time and touch invalidation rather than touch counting.
3. **Volume-at-price / value-area zones** — orthogonal acceptance-vs-rejection geometry (1.9, 3.5, 2.15; 2.9 only with a fixed completed-session window). Keep the FX tick-volume caveat in the provenance.
4. As a **zero-parameter reference arm**, the round-number grid (4.2/4.3/4.9) — the academic record explicitly says the mixed replication evidence justifies a slot in the bake-off, not a default role.

### 6.5 Normalization rules carried from the sources

- **Width normalization warning:** only Shved, ExMachina, ATR Ranked, PAZ, Smart S/R (claimed), SNR and Advanced Supply Demand scale with ATR/volatility; SRSI and Supports And Resistances Lines use fixed pips/ticks. Convert everything to ATR multiples before comparing zone widths on EURUSD.
- **Repaint handling common rule:** every candidate creates zones after a confirmation lag (fractal 2 bars, pivot N bars, impulse 1–3 bars, ZigZag confirm). Python generators must process bar-by-bar and freeze zone sets at bar close; any tool that rebuilds all objects from scratch each bar (SRSI, Miron, Liquidity Zone Flips, Smart S/R, ATR Ranked) must be replayed rather than snapshotted, or the bake-off will measure hindsight rather than live behaviour.
- **Output-type normalization:** pivots/fractals/pivot-points return lines; profiles return bands; KDE/clustering return variable-width peaks. Normalize everything to `(price_low, price_high, born_at, confirmed_at, provenance)` before the bake-off so width logic is a shared axis rather than an artefact of each generator.
- **Confirmation-lag awareness:** record each generator's lag distribution — a generator that wins only with a 30-bar lag is not the same as one that wins with 2.
- **Known pitfalls (priority order, from the Python/quant notes):** KDE bandwidth dominates the result (fix the sweep, never choose it on the evaluation window); value-area window choice and tick-volume/Close-only rows in `marketprofile`; causal leaks in ZigZag initial-pivot scan, the last provisional pivot, `argrelextrema` right window, fractal right window; K-means `k` selection unreliable (prefer mean-shift/KDE/Fisher-Jenks or fix `k` by preregistration); vendor strength labels are not evidence of strength (Osler 2000); round-number zones have a mixed replication record, including a practitioner replication with z = −2.59 in a 13-month window but mean z = +0.08 and 0 of 12 significant across 12 longer windows ("window luck": https://hadalinstruments.com/research/do-round-numbers-matter-in-forex/ [fetched — search-extracted]); costs kill most of what survives significance.
- **Coverage gaps not carried over as candidates:** "FVG & Order Blocks (ICT/SMC) — Danny_81" was not found in searches (verified substitutes 2.10/2.11); no standalone LuxAlgo Market Structure script was located (covered by 2.10); the exact TradingView URL and licence for 2.8 and 2.12, and the licence text of every newer LuxAlgo script (2.3, 2.4, 2.8, 2.9), remain unverified. Python: `pivotpoints` is not a PyPI project (404); gap-statistic and `kneed` packages are cite-only; TRB-specific numbers were not extracted from 4.10; no generator was run on EURUSD data — all fit assessments are analytical.

