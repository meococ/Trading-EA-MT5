# Survey — TradingView open-source (Pine) zone generators

Task: T-PAPRO-ZONE-1 (program PA-PRO). Date: 2026-09-20. Author: research sub-agent.
Scope: support/resistance zones, S/R channels and sloping bands, supply/demand and
order-block zones, market-structure zone sources, volume-profile value areas.
Target instrument for the bake-off: EURUSD M5/M15 with H1/H4 context.

## Method and licence-verification note

- Every claim below is from a page fetched or a search snippet seen in this session.
  Source status is marked `[fetched]` (page/source read this session) or
  `[NOT FETCHED — cite only]` (search snippet only).
- TradingView script pages do NOT expose the licence text in the fetched HTML.
  I fetched the raw HTML of one LuxAlgo script page and grepped it: no `Mozilla`,
  no `license` string. The licence picker is rendered client-side.
- Authority for the default: the official Pine Script docs (Writing / Publishing)
  fetched at <https://www.tradingview.com/pine-script-docs/writing/publishing/> state
  verbatim: *"All open-source scripts on TradingView use the Mozilla Public License 2.0
  by default. Authors wanting to use alternative licenses can specify them in the
  source code."* [fetched]
- Where possible I read mirrored source headers. Verified licence headers:
  - `Support and Resistance Levels with Breaks [LuxAlgo]` — CC BY-NC-SA 4.0
    (header quoted in a GitHub gist and in the useThinkScript thread).
  - `Smart Money Concepts [LuxAlgo]` — CC BY-NC-SA 4.0 (two GitHub gists).
  - `Trendlines with Breaks [LuxAlgo]` — CC BY-NC-SA 4.0 (two GitHub mirrors, plus the
    MT5 port keeps the same licence link).
  - `Support Resistance Channels` (LonesomeTheBlue) — MPL 2.0 (header in a GitHub gist
    mirror of the script).
- Unverified licences below are marked `unknown`; do not assume MPL-2.0 there, because
  LuxAlgo verifiably states CC BY-NC-SA 4.0 on several of its scripts.
- No code is reproduced below; algorithms are paraphrased.

## Candidate index

| # | Name | Author | Category | Licence (verification) | Page |
|---|------|--------|----------|------------------------|------|
| 1 | Support and Resistance Levels with Breaks | LuxAlgo | pivot S/R lines + break filter | CC BY-NC-SA 4.0 (mirror header) | [fetched desc.] |
| 2 | Support & Resistance Signals MTF | LuxAlgo | MTF pivot zones + break/test/retest | CC BY-NC-SA 4.0 (source quoted on 3rd-party forum) | cite only |
| 3 | S/R Zones Strength Classifier | LuxAlgo | clustered pivot zones + test count | unknown | [fetched] |
| 4 | S/R Pro Toolkit | LuxAlgo | 4-engine levels/ATR zones + filters | unknown | [fetched] |
| 5 | Support Resistance Channels | LonesomeTheBlue | pivot channel zones, strength-sorted | MPL 2.0 (mirror header) | [fetched] |
| 6 | S/R Channels/Zones Multi Time Frame | LonesomeTheBlue | HTF pivot zones on LTF chart | MPL 2.0 (same author, inferred) | [fetched] |
| 7 | Trendlines with Breaks | LuxAlgo | sloping channel + breakout | CC BY-NC-SA 4.0 (mirror source) | cite only |
| 8 | Supply and Demand Zones [Ranked] | LuxAlgo | leg-in/base/leg-out S&D boxes, scored | unknown | cite only |
| 9 | Supply and Demand Visible Range | LuxAlgo | volume-binned supply/demand areas | unknown | cite only |
| 10 | Smart Money Concepts (SMC) | LuxAlgo | market structure + OB + FVG + premium/discount | CC BY-NC-SA 4.0 (mirror headers) | [fetched] |
| 11 | Order Blocks Finder | TradingFinder | BOS/CHoCH order-block boxes | unknown | cite only |
| 12 | Auto Support & Resistance | ForexCracked | confirmed pivots -> zones, HTF on LTF, 1–5 stars | unknown (claim: open-source) | cite only |
| 13 | Pivot Points High Low | TradingView (built-in) | raw pivot levels | proprietary/unknown | [fetched via support docs] |
| 14 | Zig Zag | TradingView (built-in) | deviation swings / structure | proprietary/unknown | [fetched via support docs] |
| 15 | Volume Profile (Session/VRVP/Periodic) | TradingView (built-in) | volume histogram, POC, value area | proprietary (paid tier) | [fetched via support docs] |

---

## 1. Support and Resistance Levels with Breaks — LuxAlgo

1. **Name + author**: Support and Resistance Levels with Breaks [LuxAlgo]; author LuxAlgo.
2. **Category**: pivot-based horizontal S/R levels with breakout markers (lines, not zones). The
   direct ancestor of candidate 2.
3. **Source URL**: <https://www.tradingview.com/script/JDFoWQbL-Support-and-Resistance-Levels-with-Breaks-LuxAlgo/>
   `[fetched]`; Pine v4 source mirrored at
   <https://gist.github.com/themodernpk/5b5b4997229643d423da1bbddc425964> and quoted in
   <https://usethinkscript.com/threads/support-and-resistance-levels-with-breaks-lux-for-thinkorswim.11556/> `[NOT FETCHED — cite only]`.
4. **License**: CC BY-NC-SA 4.0. Verbatim from the mirrored source header: *"This work is
   licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
   https://creativecommons.org/licenses/by-nc-sa/4.0/"* and *"© LuxAlgo"*.
5. **Output**: two horizontal lines (last usable pivot high = resistance, last pivot low =
   support) plus `B` / `Bull Wick` / `Bear Wick` break labels. No band.
6. **Algorithm**: take `ta.pivothigh(leftBars, rightBars)` / `ta.pivotlow`, hold the last non-na
   value, plot the line with a bar offset so it visually starts at the pivot bar (not at the
   confirmation bar). Break detection = close crossing the level. Two filters: a volume
   oscillator (EMA 5 vs EMA 10 of volume, percent spread) above `volumeThresh`, or a wick
   asymmetry condition. Alerts on both break directions.
7. **Repaint?**: no `security()`, no lookahead; `max_bars_back=1000`. The pivot value is only
   known `rightBars+1` bars after the pivot bar (the source also indexes the pivot result by
   `[1]`), so historical bars are redrawn at that confirmation moment — normal, bounded lag.
   The current bar's cross can flicker intrabar; alerts fire on ticks unless set to bar close.
8. **How to make it causal**: level becomes usable at bar `pivot_index + rightBars + 1`; only
   evaluate breaks on closed bars; keep the level frozen until a newer pivot replaces it. The
   Pine offset is cosmetic and irrelevant to a Python port.
9. **Parameters + ATR scaling**: `leftBars=15`, `rightBars=15`, `volumeThresh=20` (%),
   `toggleBreaks`. **No ATR at all**; volume EMAs 5/10 substitute for a strength filter.
10. **Zone width logic**: none — single price lines.
11. **Strength / freshness**: none beyond the volume filter; a level is implicitly "fresh"
    until first cross, then stays replaced by the next pivot.
12. **Typical number of zones on a chart**: 2 lines.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: usable only as a baseline level generator
    (15 right bars ≈ 75 min lag on M5). No zones, no HTF logic. Too thin for the bake-off.
14. **Confidence**: **high** — full source read via mirror; licence header seen verbatim.

## 2. Support & Resistance Signals MTF — LuxAlgo

1. **Name + author**: Support and Resistance Signals MTF [LuxAlgo]; author LuxAlgo.
2. **Category**: MTF pivot S/R zones plus event signals (breakout, test, retest, rejection).
3. **Source URL**: <https://www.tradingview.com/script/iOrhpIqc-Support-and-Resistance-Signals-MTF-LuxAlgo/>
   `[NOT FETCHED — cite only]` (search snippet has the full description; Pine source quoted on
   <https://www.prorealcode.com/topic/conversion-de-lindicateur-support-and-resistance-signal-mtf/>).
4. **License**: CC BY-NC-SA 4.0 — the header is quoted together with the full source on the
   ProRealCode thread: *"This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0
   International (CC BY-NC-SA 4.0)"*, *"© LuxAlgo"*.
5. **Output**: S/R zones (boxes; `max_boxes_count=500, max_lines_count=500,
   max_labels_count=500`), swing lines, and labelled signals. Detection runs on a user-chosen
   timeframe (default = chart), so H1/H4 zones can be drawn on M5.
6. **Algorithm**: swing highs/lows are detected with `Detection Length` on the detection
   timeframe; each becomes a level/zone. Events: **breakout** = close beyond the level (volume
   of the breaking bar is reported but not used as a filter); **test** = touch of the zone;
   **retest** = breach then return; **rejection** = pin bar with high volume at a level.
   Optional "check previous historical level" keeps more levels alive. An "Avoid False
   Breakouts" filter exists. Documented as an extended version of candidate 1.
7. **Repaint?**: MTF detection is almost certainly `request.security`; the exact `lookahead`
   argument is **not verified**. If the detection-TF series is requested without offset and with
   `lookahead_on`, the HTF zones leak; with `lookahead_off` + `[1]` indexing they are safe.
   Signals on the chart TF can flicker on the forming bar. Treat as medium-confidence causal
   until the source is inspected.
8. **How to make it causal**: compute swings on closed detection-TF bars only
   (`lookahead_off`, use the previous completed HTF bar), then evaluate touches/breaks on
   closed chart bars. Freeze the zone list between HTF confirmations.
9. **Parameters + ATR scaling**: Detection Timeframe, Detection Length, Check Previous
   Historical Level, signal toggles, Avoid False Breakouts. No ATR mentioned in the docs;
   zone thickness (if any) is unverified.
10. **Zone width logic**: unverified from the description; zones appear to be drawn around
    swing levels (exact thickness must be read from source).
11. **Strength / freshness**: implicit via test/retest counts (signals), volume reported on
    breakouts; no documented numeric score.
12. **Typical number of zones**: several (object caps 500 suggest a busy chart; in practice
    ~5–15 active levels depending on Detection Length).
13. **Fit for EURUSD M5/M15 with H1/H4 context**: conceptually the best LuxAlgo fit — but the
    licence and the unverified MTF lookahead are the two caveats. Re-implement the idea
    (HTF swings + event classification), not the code.
14. **Confidence**: **medium** — description and licence mirror seen; source internals unverified.

## 3. Support & Resistance Zones Strength Classifier — LuxAlgo

1. **Name + author**: Support & Resistance Zones Strength Classifier [LuxAlgo]; author LuxAlgo
   (published 2026-02-16).
2. **Category**: clustered pivot S/R zones with a test-count "strength" classifier.
3. **Source URL**: <https://www.tradingview.com/script/KBEYcjCd-Support-Resistance-Zones-Strength-Classifier-LuxAlgo/> `[fetched]`.
4. **License**: unknown. The page shows only the open-source badge; the fetched HTML contains no
   licence text (the TV default MPL-2.0 applies only if the code header does not override it,
   which I could not read).
5. **Output**: horizontal boxes (zones) per side, with optional test-count labels; opacity
   encodes strength; broken zones are deleted; zones extend right.
6. **Algorithm**: `Pivot Lookback` bars on each side confirm pivots; each pivot opens a zone
   whose thickness is a multiple of the average bar range (volatility-adjusted). Overlapping
   zones **merge**, summing test counts. A zone's count increments every time price returns into
   it without a close through the far boundary. A close beyond a support/resistance boundary
   deletes the zone. Caps: max active zones per type, max zone height.
7. **Repaint?**: pivots confirm with `Pivot Lookback` bars of lag; merging means the historical
   zone layout changes as new pivots arrive. No `security()` mentioned. Touch counting on the
   forming bar can update intrabar. No `barstate` behaviour documented.
8. **How to make it causal**: only open a zone when the pivot is confirmed (lookback lag);
   count touches on closed bars; apply merge/delete rules in bar order; snapshot the active
   zone list per bar for the bake-off.
9. **Parameters + ATR scaling**: Pivot Lookback; Zone Width (multiplier of average bar range);
   Minimum Tests to Highlight; Max Active Zones Per Type; Max Zone Height (multiplier). The
   docs say "average bar range", **not explicitly `ta.atr()`** — treat as ATR-like but verify.
10. **Zone width logic**: volatility-adjusted average bar range × multiplier; grows when zones
    merge (with a max-height kill switch).
11. **Strength / freshness**: test count (increments on re-entry, merges sum counts); visual
    weight by count; no time decay documented, expiry is by breakout deletion only.
12. **Typical number of zones**: several per side (capped by Max Active Zones Per Type); expect
    ~5–10 total on M15.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: good, simple and cheap to port; the
    test-count strength signal is exactly the kind of zone physics the bake-off can score. No
    built-in HTF mode — run it separately on H1/H4 series if needed.
14. **Confidence**: **medium** — description fetched; source internals and licence unverified.

## 4. Support & Resistance Pro Toolkit — LuxAlgo

1. **Name + author**: Support & Resistance Pro Toolkit [LuxAlgo]; author LuxAlgo (2026-03-09).
2. **Category**: multi-engine structural levels/zones with institutional-style filters and a
   performance dashboard.
3. **Source URL**: <https://www.tradingview.com/script/n2ODj57p-Support-Resistance-Pro-Toolkit-LuxAlgo/> `[fetched]`;
   companion page <https://www.luxalgo.com/library/indicator/support-resistance-pro-toolkit/>.
4. **License**: unknown (no licence text on the page; header not readable).
5. **Output**: either precise lines or ATR-based zones; 25-bar forward projections; sweep dots;
   labels carrying score shorthand (E entries, S strength, SW sweeps, V traded volume, D
   duration); dashboard with mitigation %, avg duration, avg volume, total sweeps.
6. **Algorithm**: four selectable swing engines — **Pivots** (left/right lookback), **Donchian
   alternating** (state machine that confirms the previous extreme when direction flips),
   **CSID** (N consecutive candles of one direction mark the extreme), **ZigZag** (percentage
   deviation). Each confirmed swing becomes a level; zones = ATR depth inward + ATR breakout
   buffer outward. Unmitigated zones extend 25 bars. Overlap handling: merge (older absorbs
   newer), hide oldest, hide youngest. Filters: min re-tests, min internal-swing strength, min
   sweeps (wick-only violations), min accumulated traded volume inside the zone, min duration
   in bars. Mitigation (break) deletes/hides the zone.
7. **Repaint?**: Pivots lag; Donchian/CSID confirm at the state change (no fixed lag but only
   after the new extreme forms); ZigZag's last leg is provisional by construction. Volume and
   duration counters accumulate live. No `security()` mentioned. Expect the normal
   confirmation-time redraw, not lookahead.
8. **How to make it causal**: use only confirmed swings (pivot lag or state-flip confirmation);
   treat the current ZigZag leg as unknown until a deviation-complete reversal; accumulate
   volume/duration/touches on closed bars.
9. **Parameters + ATR scaling**: Detection Method; Swing Sensitivity; Display Style (line vs
   zone); **ATR Period**, **Zone Depth (ATR mult)**, **Breakout Buffer (ATR mult)**; Min Price
   Entries; Min Overall Strength; Min Sweeps; Min Traded Volume; Min Duration (bars); Max Active.
10. **Zone width logic**: ATR-based on both sides (depth inward toward price, buffer outward on
    the breakout side). This is the most explicit ATR-scaled zone model in the LuxAlgo family.
11. **Strength / freshness**: richest documented: re-test entries, internal swing-point count,
    wick sweeps, cumulative traded volume, survival duration; dashboard aggregates them.
12. **Typical number of zones**: user-capped ("Max Active"), typically a handful (≈5–10).
13. **Fit for EURUSD M5/M15 with H1/H4 context**: the ATR buffer is directly relevant to M5
    noise; the volume filter is weaker on FX (tick volume) but still informative; no built-in
    HTF mode. Heavy to port, but each sub-rule is simple.
14. **Confidence**: **medium** — detailed official description; internals and licence unverified.

## 5. Support Resistance Channels — LonesomeTheBlue

1. **Name + author**: Support Resistance Channels; author LonesomeTheBlue (2021-04-08, upgraded
   to Pine v6 on 2025-07-04; Editors' pick).
2. **Category**: pivot-cluster horizontal channel zones, strength-sorted.
3. **Source URL**: <https://www.tradingview.com/script/Ej53t8Wv-Support-Resistance-Channels/> `[fetched]`;
   v4 source mirrored at <https://gist.github.com/Planxnx/c27927832553af1f6e94b9720b4948ef> `[NOT FETCHED — cite only]`.
4. **License**: MPL 2.0. Verbatim from the mirrored source header: *"This source code is subject
   to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/"*, *"© LonesomeTheBlue"*.
   (The derivatives' pages also state the original engine is MPL 2.0.)
5. **Output**: up to N horizontal channel boxes (zones) with automatic color by position
   (support/resistance/inside), optional pivot markers, and break shapes + alerts.
6. **Algorithm** (read from the v4 mirror): `pivothigh/src1(prd,prd)` and `pivotlow/src2(prd,prd)`
   with High/Low or Close/Open source (default prd=10); pivots are stored in arrays and pruned
   beyond `loopback` (default 290 bars). Maximum channel width = `(highest(300) − lowest(300))
   × ChannelW%` (default 5%). For each pivot, all other pivots within that width are merged into
   one zone. Strength = 20 per included pivot + count of bars in the loopback whose high or low
   intersects the zone. Zones are greedy-selected strongest-first (dropping pivots already
   covered), sorted descending, capped at `maxnumsr` (default 6). Break = close crossing a
   boundary while price is not inside any channel.
7. **Repaint?**: no `security()`; `max_bars_back=501`. Pivots are only known `prd` bars late;
   the entire zone list is recalculated on every new pivot, so historical boxes can appear,
   move or vanish when a new pivot confirms. The break test uses `close`, so it can flip during
   the forming bar. This is bounded confirmation lag, not lookahead.
8. **How to make it causal**: rebuild the zone list only at pivot-confirmation bars; treat the
   list as immutable until then; test breaks on closed bars. The result is a well-defined
   event-time zone sequence for the bake-off.
9. **Parameters + ATR scaling**: Pivot Period 10; Source High/Low|Close/Open; Maximum Channel
   Width % 5 (of the 300-bar range); Minimum Strength 1 (internally ×20); Max Number of S/R 6;
   Loopback 290/300 bars; optional start date/bar and MAs. **No ATR** — width is a percentage of
   the recent range.
10. **Zone width logic**: percentage of the 300-bar high-low range; pivots merge while the
    resulting band stays within that maximum width.
11. **Strength / freshness**: strength = 20 × pivots + bar-touch count over the loopback;
    strongest zones are redrawn each pivot event; no explicit decay other than the loopback
    window and the max-zones cap.
12. **Typical number of zones**: ≤6 by default (max 10).
13. **Fit for EURUSD M5/M15 with H1/H4 context**: very good and simple; the strength-then-cap
    selection gives stable, few zones. `prd=10` on M5 = 50 min confirmation lag; on H1 = 10 h.
    Run once per timeframe (M5/M15 + H1/H4) for the bake-off. Caveat: the mirrored source is
    v4; the 2025 v6 upgrade may have changed details.
14. **Confidence**: **high** for the v4 algorithm and licence (source read); **medium** that the
    current v6 code is unchanged.

## 6. Support Resistance Channels/Zones Multi Time Frame — LonesomeTheBlue

1. **Name + author**: Support Resistance Channels/Zones Multi Time Frame; author
   LonesomeTheBlue (2022-09-06).
2. **Category**: HTF pivot-cluster zones projected onto the LTF chart, strength-sorted, plus a
   table of bands.
3. **Source URL**: <https://www.tradingview.com/script/DrcEUv8C-Support-Resistance-Channels-Zones-Multi-Time-Frame/> `[fetched]`.
4. **License**: MPL 2.0 (high confidence, inferred: same author and same engine as candidate 5,
   whose header is verified MPL 2.0; the fetched page shows the open-source badge but the
   licence text itself is not in the HTML).
5. **Output**: zone boxes from the selected higher timeframe drawn on the current chart, plus a
   table listing each zone's lower/upper band; zones ranked by strength.
6. **Algorithm**: user picks a Higher Time Frame (must be above the chart TF) and a Pivot Period;
   pivots are searched over a `Loopback Period` of HTF bars. Zones merge pivots within
   `Maximum Channel Width %`. Strength counts included pivots plus Open/High/Low/Close
   interactions. Up to `Maximum Number of S/R` zones are shown, strongest first. Optional
   "Show S/R that fits the Chart" filters zones to the current visible price range; the table
   can show all zones regardless.
7. **Repaint?**: HTF data is involved. Unlike the author's separate "Support Resistance MTF"
   (which explicitly avoids `security()`), this script gives no such statement, so
   `request.security` is likely; lookahead is unverified. The visible-range filter makes the
   zone set **zoom-dependent**, which is a stability problem independent of repainting. HTF
   pivots need HTF pivot-period bars to confirm (e.g. H4 prd=10 → 40 h).
8. **How to make it causal**: compute pivots on closed HTF bars with `lookahead_off` and
   previous-bar indexing; disable "fits the chart" and cap zones by count; rebuild the zone set
   only when a new HTF pivot confirms.
9. **Parameters + ATR scaling**: Higher Time Frame; Pivot Period; Loopback Period; Maximum
   Channel Width %; Minimum Strength; Maximum Number of S/R; Show S/R that fits the Chart;
   table options. No ATR.
10. **Zone width logic**: percent of the HTF price range (same family as candidate 5).
11. **Strength / freshness**: pivot count + OHLC touches on the HTF; sorted strongest first;
    no expiry other than loopback and the count cap.
12. **Typical number of zones**: ≤ Maximum Number of S/R (user-set; the author's screenshots
    show a handful, ~3–6).
13. **Fit for EURUSD M5/M15 with H1/H4 context**: this is exactly the "HTF context on LTF chart"
    pattern the bake-off wants. Two traps: the visible-range filter (disable it) and unverified
    `request.security` lookahead (verify before trusting). The algorithm itself is the same
    pivot-clustering as candidate 5, which is a plus for re-implementation.
14. **Confidence**: **medium-high** — page and full description fetched; licence inferred;
    security/lookahead details unverified.

## 7. Trendlines with Breaks — LuxAlgo

1. **Name + author**: Trendlines with Breaks [LuxAlgo]; author LuxAlgo (2023-07-18).
2. **Category**: sloping pivot trendlines / S/R channel with breakout signals.
3. **Source URL**: <https://www.tradingview.com/script/IYL88A1N-Trendlines-with-Breaks-LuxAlgo/>
   `[NOT FETCHED — cite only]`; full Pine v5 source mirrored at
   <https://github.com/iamc1oud/Tradingview-Scripts/blob/master/Trendlines%20with%20Breaks.pine>
   and <https://github.com/traderfour/trend-line> `[NOT FETCHED — cite only]`.
4. **License**: CC BY-NC-SA 4.0. Verbatim header in both mirrors: *"This work is licensed under
   a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
   https://creativecommons.org/licenses/by-nc-sa/4.0/"*, *"© LuxAlgo"*. The MT5 port repeats
   the licence link in `#property link`.
5. **Output**: two sloping lines (upper trendline from pivot highs, lower from pivot lows),
   with `B` break labels; "Show Only Confirmed Breakouts" option.
6. **Algorithm** (read from mirrors): `ph = pivothigh(length,length)` / `pl = pivotlow(...)`,
   default length 14. Slope per bar = `ta.atr(length)/length × k` (default k=1), or stdev or
   linreg of price vs bar_index, selectable. On a new pivot the anchor price and slope are
   reset; otherwise the line walks forward `upper[1] − slope` (and `lower[1] + slope`). A
   breakout is flagged when the source at `[length]` crosses the projected line. Trendlines are
   backpainted by default — plotted with a negative offset so they start at the old pivot.
7. **Repaint?**: two distinct behaviours, both documented: (a) **trendlines repaint** unless
   backpaint is disabled — the last leg is redrawn when a new pivot resets the slope; (b) the
   **breakout signals are real-time and not backpainted**. `pivothigh(14,14)` confirms with a
   14-bar lag. No `security()`. Classic Pine confirmation-lag behaviour, no lookahead.
8. **How to make it causal**: turn backpaint off; use only confirmed pivots; a line exists at
   bar t only from the confirmation bar of its last anchor; evaluate breaks against the line
   value computed from closed-bar data.
9. **Parameters + ATR scaling**: Length 14 (pivot); Slope k 1.0; method Atr|Stdev|Linreg
   (default Atr); Show Only Confirmed Breakouts; Backpaint on/off. **ATR is used for the slope**
   (`ta.atr(length)/length*k`), not for width.
10. **Zone width logic**: none — single-pixel lines; the ATR only controls the angle.
11. **Strength / freshness**: one pivot per line; no scoring, no touch count.
12. **Typical number of zones**: 2 lines.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: useful as a sloping S/R channel generator
    (ATR slope is volatility-adaptive), but it produces geometry, not zones. Pivot lag 14 bars
    (70 min on M5). Good as a secondary "channel" arm of the bake-off, not as a zone source.
14. **Confidence**: **high** on algorithm and licence (full source read via mirrors).

## 8. Supply and Demand Zones [Ranked] — LuxAlgo

1. **Name + author**: Supply and Demand Zones [Ranked]; author LuxAlgo (LuxAlgo Library page
   dated 2026-04-10).
2. **Category**: supply/demand (leg-in → base → leg-out) boxes with an Odds-Enhancer score.
3. **Source URL**: <https://www.luxalgo.com/library/indicator/ssBOX4V7-supply-and-demand-zones/>
   `[NOT FETCHED — cite only]` (search snippet contains the full description). The TradingView
   page was not located; guessed slug `…/script/ssBOX4V7-Supply-and-Demand-Zones/` returned 404.
4. **License**: unknown (no licence text seen; LuxAlgo headers on other scripts are
   CC BY-NC-SA 4.0, so assume non-commercial until verified).
5. **Output**: supply and demand boxes labelled with a 1–7 score; broken/touched zones managed
   automatically.
6. **Algorithm**: scan for the Leg-In → Base → Leg-Out pattern. Classify by the base type:
   DBR (demand reversal), RBR (demand continuation), RBD (supply reversal), DBD (supply
   continuation). Candles are classed ERC when the body is ≥ 75 % of range, NRC when ≤ 50 %.
   Score = freshness (max 3, untouched = full) + departure strength (max 2: gap = 2, strong ERC
   = 1) + base time (max 2: 1–3 candles = 2, 4–6 = 1). Zones invalidate after two touches or
   when price closes through the distal line; overlapping same-type zones merge.
7. **Repaint?**: not documented. By construction a zone can only be declared once the leg-out
   move has completed (the information is available then), so the design is causal with a lag
   of base length + leg-out confirmation. Score/freshness updates on touches are live. Source
   not readable, so unverified.
8. **How to make it causal**: declare the zone at the close of the leg-out candle, update
   freshness/touches on closed bars only, invalidate on close beyond the distal line.
9. **Parameters + ATR scaling**: ERC/NRC Body %; Max Base Candles; ranking filter (e.g. 5+);
   Max Zones on Chart. No ATR mentioned — zone height comes from the base candles, not
   volatility.
10. **Zone width logic**: proximal/distal = base candle high/low (the base's range); no ATR
    pad documented.
11. **Strength / freshness**: this is the selling point — explicit 1–7 score with freshness
    penalised on revisits, departure strength, base time; invalidate after 2 touches.
12. **Typical number of zones**: capped by Max Zones on Chart; a handful (≈3–8).
13. **Fit for EURUSD M5/M15 with H1/H4 context**: strong candidate. Base-time and freshness
    scoring is a ready-made zone-physics signal; M15/H1 bases map naturally, and GBP/USD-style
    M5 displacement candles give leg-out confirmation quickly. No HTF mode; score HTF
    separately.
14. **Confidence**: **medium** — detailed official description, but page only on luxalgo.com;
    TV URL, source and licence unverified.

## 9. Supply and Demand Visible Range — LuxAlgo

1. **Name + author**: Supply and Demand Visible Range [LuxAlgo]; author LuxAlgo (2023-04-13).
2. **Category**: volume-distribution supply/demand areas over the visible range.
3. **Source URL**: <https://www.tradingview.com/script/UpWXXsbC-Supply-and-Demand-Visible-Range-LuxAlgo/> `[NOT FETCHED — cite only]`;
   companion <https://www.luxalgo.com/library/indicator/supply-and-demand-visible-range/>.
4. **License**: unknown (page fetched only via search snippet; no header seen).
5. **Output**: supply area (built down from the highest visible price) and demand area (built up
   from the lowest), plus solid average lines and dashed weighted-average lines; per-bin volume
   accumulation displayed; intra-bar data used for precision.
6. **Algorithm**: take the total volume in the visible chart range; split the range into N equal
   price bins (`Resolution`); for supply, accumulate volume from the top downwards until the
   accumulated share reaches `Threshold %` of total volume — the accumulated range becomes the
   area; demand is the mirror from the bottom. A higher threshold gives wider areas. The
   weighted-average lines highlight more liquid price levels inside each area.
7. **Repaint?**: by design it **recalculates whenever the visible range changes** — the author
   calls it "a descriptive tool". That is zoom-dependent, therefore not a stable causal
   generator. Intra-bar data via lower-timeframe requests (function name unverified) also
   changes with data availability.
8. **How to make it causal**: replace the visible range with a fixed window (e.g. previous
   H4/D1 session) and compute only from completed lower-TF bars; freeze the area when the
   window closes.
9. **Parameters + ATR scaling**: Threshold %; Resolution (bins); Intra-bar TF. No ATR.
10. **Zone width logic**: width is emergent — the accumulated-volume threshold determines the
    band edges, not a fixed multiplier.
11. **Strength / freshness**: bin volume accumulation rate is displayed; no touch count or
    expiry — areas persist until the window moves.
12. **Typical number of zones**: 2 areas (one supply, one demand) per calculation.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: as published, poor (zoom-dependent). The
    *algorithm* (volume-threshold areas over a fixed completed session/anchor) is a good
    daily/H4 zone generator for EURUSD, keeping in mind FX "volume" is broker tick volume.
14. **Confidence**: **medium** — the algorithm is fully documented in the official description;
    licence and intra-bar internals unverified.

## 10. Smart Money Concepts (SMC) — LuxAlgo

1. **Name + author**: Smart Money Concepts (SMC) [LuxAlgo]; author LuxAlgo (2022-10-11,
   updated 2025-09-23).
2. **Category**: market structure + order blocks + FVG + EQH/EQL + premium/discount zones.
3. **Source URL**: <https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/> `[fetched]`;
   source mirrors: <https://gist.github.com/thino-dev/5fc81d23ebc2a2113207fd850e340962> and
   <https://gist.github.com/niquedegraaff/8c2f45dc73519458afeae14b0096d719> `[NOT FETCHED — cite only]`.
4. **License**: CC BY-NC-SA 4.0. Verbatim header in both mirrors: *"This work is licensed under
   a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
   https://creativecommons.org/licenses/by-nc-sa/4.0/"*, *"© LuxAlgo"*.
5. **Output**: internal + swing structure labels and lines (BOS/CHoCH), internal and swing
   order-block boxes (last N, default 5), equal highs/lows, FVG boxes, previous D/W/M highs and
   lows, premium/equilibrium/discount bands. Objects capped at 500 boxes/lines/labels;
   `max_bars_back = 500` in the mirrored v5 header.
6. **Algorithm**: two pivot scales (internal, swing) with configurable lengths produce HH/HL/LH/LL
   swings; a break of the last swing in the trend direction is BOS, against it is CHoCH. Order
   blocks are the last opposite candle at the origin of the displacement that broke structure;
   they are mitigated (removed) when price passes through. FVG = three-candle imbalance;
   EQH/EQL = two equal pivots within tolerance confirmed after `Bars Confirmation`. Premium /
   discount = halves of the active dealing range. MTF previous D/W/M levels via `security`.
7. **Repaint?**: pivot-based structure confirms with the pivot length of lag and is drawn back
   at the swing bar; the newest structure/order block can be revised until its confirmation leg
   closes. The MTF highs/lows use `security` (lookahead unverified in the mirror). FVGs fill
   over time. This is standard lag + last-leg revision, not a lookahead guarantee.
8. **How to make it causal**: only consume structure events at pivot confirmation; only accept
   an order block after the displacement candle closes and it breaks a confirmed swing; compute
   MTF levels from completed D/W/M bars.
9. **Parameters + ATR scaling**: internal/swing lengths; OB display count; OB filter (2 methods);
   EQH/EQL Bars Confirmation; FVG Auto Threshold and FVG Timeframe; Extend FVG; MTF Highs & Lows;
   premium/discount toggles. No explicit ATR scaling in the documented settings.
10. **Zone width logic**: order block = origin candle range (wick-to-wick); FVG = the 3-candle
    gap; premium/discount = range halves. No ATR pad.
11. **Strength / freshness**: recency (only the last N OBs are shown), OB filter for volatile
    blocks, mitigation on break; no explicit touch-score.
12. **Typical number of zones**: busy — up to 5 swing + 5 internal OBs plus FVGs and MTF levels;
    commonly 10–20 objects.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: good structure/OB arm for the bake-off; its
    CHoCH/BOS displacement definition is a natural "freshness/strength" input. Heavy to port
    faithfully, and CC BY-NC-SA means no code reuse in a commercial product (clean-room
    re-implementation only).
14. **Confidence**: **high** on licence; **medium** on internals (mirror headers and description
    read, not the full source).

## 11. Order Blocks Finder [TradingFinder]

1. **Name + author**: Order Blocks Finder [TradingFinder] Major OB | Supply and Demand; author
   TradingFinder.
2. **Category**: supply/demand and ICT order blocks anchored to Break of Structure / CHoCH.
3. **Source URL**: <https://www.tradingview.com/script/MRx6ze6n-Order-Blocks-Finder-TradingFinder-Major-OB-Supply-and-Demand/> `[NOT FETCHED — cite only]`.
4. **License**: unknown (open-source badge; no header seen; do not assume MPL-2.0).
5. **Output**: active OB boxes (green bullish / red bearish) extended to the right until price
   reaches them, a 50 % equilibrium line in every block, optional major high/low levels, alerts
   carrying proximal (near edge) and distal (far edge) prices.
6. **Algorithm**: find structure breaks (BOS/CHoCH, also called MSS) using swing points; the OB
   is the origin of the break leg. Two range modes: **Refine off** = whole order block range;
   **Refine on** = an error-correction algorithm with Defensive (tighten to standard) and
   Aggressive (maximize the range to reduce stop-outs) settings. Boxes stay active until price
   reaches the zone; alerts on proximal/distal touches. The vendor states suitability for
   M1–H1–H4 and Tokyo/Sydney/London sessions.
7. **Repaint?**: not documented. A structure break is only known once the breaking candle closes,
   so the OB is declared with that lag; there is no visible-range or security logic described.
   Unverified whether the script redraws older boxes when structure re-evaluates.
8. **How to make it causal**: emit the OB at the close of the structure-breaking candle; treat
   prior boxes as immutable thereafter; evaluate touches on closed bars (or intrabar if the
   bake-off allows, but then tag it).
9. **Parameters + ATR scaling**: Order block refine on/off; Refine type Defensive|Aggressive;
   Show high level; Show low level. No ATR documented.
10. **Zone width logic**: origin candle range, optionally refined (defensive/aggressive
    adjustment); no volatility scaling.
11. **Strength / freshness**: none beyond "major OBs only" (breaks of structure) and the active
    until reached lifecycle.
12. **Typical number of zones**: one per valid structure break; accumulates over the chart —
    typically several per session on M5.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: decent light-weight OB arm; the vendor's own
    timeframe note covers M5/M15 and H1/H4. No MTF mode, no touch scoring — weaker than SMC or
    S&D Ranked for zone physics, simpler to port.
14. **Confidence**: **medium** — description read; source, licence and repaint internals
    unverified.

## 12. Auto Support & Resistance — ForexCracked

1. **Name + author**: Auto Support & Resistance [ForexCracked]; author ForexCracked (2026-08-01
   vendor article).
2. **Category**: confirmed-pivot S/R zones with touch-based star ratings and HTF zones drawn on
   the LTF chart.
3. **Source URL**: <https://www.forexcracked.com/forex-indicator/auto-support-resistance-indicator-tradingview/>
   `[NOT FETCHED — cite only]`. The article links to a TradingView script page but the exact URL
   was not retrieved; no TV script ID to cite.
4. **License**: unknown ("free and open-source" claimed in the article; no licence text seen).
5. **Output**: teal support / pink resistance zones, merged from close pivots; 1–5 star rating
   per zone (darker = stronger); H4 and Daily zones with thicker borders and TF tags; a
   dashboard with the nearest level above/below, pip distance and stars.
6. **Algorithm** (as described): swing pivots are confirmed (a set number of bars on each side)
   before any zone is drawn; each confirmed pivot becomes a zone, and pivots within a merge
   distance are merged into one zone with an extra touch; zones break and **flip role** when
   price closes beyond them by more than an ATR buffer (resistance becomes support, touch count
   resets); weak untouched zones age out, 4–5 star zones persist. Two higher timeframes (4H and
   Daily by default) are detected and drawn on the current chart with their own pivot strength
   and caps.
7. **Repaint?**: the vendor explicitly claims non-repainting through confirmed pivots (zone
   appears a few bars after the swing, then does not move). HTF levels via requests (presumably
   `security`); lookahead not documented. The claim is plausible but unverified.
8. **How to make it causal**: confirm pivots before emitting zones; update touches on closed
   bars; evaluate the ATR-buffered break on closes; request HTF pivots from completed HTF bars.
9. **Parameters + ATR scaling**: Pivot strength 10; **Merge distance 0.5×ATR**; **Zone height
   0.15×ATR**; Max levels per side; HTF levels (4H, Daily) with own pivot strength and caps;
   **Break buffer 0.1×ATR**; Max zone age; Keep strong levels.
10. **Zone width logic**: fixed 0.15×ATR around the pivot cluster; merging broadens the zone.
11. **Strength / freshness**: 1 star per touch, capped at 5; merges count as touches; weak zones
    decay with age, strong (4–5 star) survive until a genuine break; role flip on break.
12. **Typical number of zones**: capped per side (a handful, ~4–8 including HTF levels).
13. **Fit for EURUSD M5/M15 with H1/H4 context**: if the claims hold, this is the closest match
    to the bake-off brief (confirmed pivots + ATR-tuned widths + HTF context + strength rating).
    But nothing is verifiable from a vendor page: locate the TV page, read the header licence and
    the `security` calls before using it as a reference.
14. **Confidence**: **low** — all details are vendor claims on a third-party site; script page,
    source and licence unverified.

## 13. Pivot Points High Low — TradingView (built-in)

1. **Name + author**: Pivot Points High Low; built-in TradingView indicator (not a community
   publication).
2. **Category**: raw pivot levels — the primitive most other generators build on.
3. **Source URL**: <https://www.tradingview.com/support/solutions/43000589195-pivot-points-high-low/> `[NOT FETCHED — cite only]`;
   behaviour corroborated by a third-party implementation guide
   (<https://pineify.app/pine-script/indicators/pivot-points-high-low>) `[NOT FETCHED — cite only]`.
4. **License**: proprietary/unknown. It is a built-in study; the code can be opened in the Pine
   editor but is not published under a community licence, and no licence statement was found.
   Do not treat as open-source.
5. **Output**: price labels (levels) at pivot highs and lows; lines can be plotted from them. No
   zones.
6. **Algorithm**: a pivot high is a bar whose high is higher than the highs of N bars to the
   left and N bars to the right (the right side must be lower highs); pivot low is the mirror.
   Default 10/10 for both in the built-in. No smoothing, no weighting.
7. **Repaint?**: the pivot can only be known once the right window has closed, so labels are
   drawn back onto the pivot bar with a confirmation lag of `rightLen`. After confirmation the
   pivot does not move (individual candles cannot retroactively change); the "repaint" people
   see is the delay, plus a pivot being superseded by an extreme that forms inside the window.
8. **How to make it causal**: at bar t, use pivots with index ≤ t − rightLen; a pivot at bar p is
   usable only at p + rightLen and stays fixed.
9. **Parameters + ATR scaling**: left/right lengths (built-in default 10/10; four values in the
   basic version, independently for highs and lows). No ATR.
10. **Zone width logic**: none.
11. **Strength / freshness**: none (level only).
12. **Typical number of zones**: one per pivot; on M5 with right=10, roughly one pivot every
    ~20+ bars per side — dozens of levels over a few days.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: not a zone generator by itself, but the
    correct causal primitive for every pivot-based candidate above. For the bake-off, use
    `rightLen ≈ 24` on M5 (≈2 h) or 10 on H1/M15 and cluster pivots in Python.
14. **Confidence**: **medium** — official help page plus a third-party guide; licence proprietary.

## 14. Zig Zag — TradingView (built-in)

1. **Name + author**: Zig Zag; built-in TradingView indicator.
2. **Category**: market-structure swing detector (deviation-filtered pivots).
3. **Source URL**: <https://www.tradingview.com/support/solutions/43000591664-zig-zag/> `[NOT FETCHED — cite only]`;
   also the official Pine library publication <https://www.tradingview.com/script/bzIRuGXC-ZigZag/> `[NOT FETCHED — cite only]`.
4. **License**: proprietary/unknown for the built-in; the Pine library publication by TradingView
   is a community open-source publication (licence not read — unknown).
5. **Output**: alternating swing lines and labels; no zones (swing points can seed zones).
6. **Algorithm** (official docs): pivots are confirmed with `Pivot legs` split evenly left/right;
   a swing is only added if the reversal from the last point meets the `Price deviation (%)`
   threshold; the indicator connects confirmed alternating pivots. Optionally it can display a
   **projected** (unconfirmed) pivot on realtime bars.
7. **Repaint?**: the docs are explicit — the latest solid line is not final and can be redrawn;
   the projected line updates every bar; it lags by the pivot-leg confirmation; drawings are
   capped at ~500 lines so deep history is truncated. This is a heavy repainter by design.
8. **How to make it causal**: never use the current (last) leg or projected pivots; only use
   pivot points that are confirmed by the `Pivot legs` window and by the deviation threshold;
   replay with a per-bar snapshot of the confirmed structure.
9. **Parameters + ATR scaling**: Price deviation for reversals (%); Pivot legs (total, split
   left/right); Calculate projected pivots (on/off); label mode. No ATR.
10. **Zone width logic**: none (a percentage-deviation channel around the last pivot could be
    derived but is not part of the indicator).
11. **Strength / freshness**: none.
12. **Typical number of swings**: frequent on M5 — dozens of swings; deeper history truncated by
    the ~500-line cap.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: useful as the swing skeleton for structure
    zones; the deviation % threshold is naturally volatility-adaptive. Because of the repaint
    behaviour, only the confirmed subset should be used in the bake-off.
14. **Confidence**: **medium** — official docs read; licence and Pine internals of the built-in
    unverified.

## 15. Volume Profile (Session / Visible Range / Periodic) — TradingView (built-in)

1. **Name + author**: Volume Profile family (Session Volume Profile, Visible Range Volume
   Profile, Periodic Volume Profile, plus Fixed Range/Anchored drawing tools); built-in,
   TradingView. Requires a paid plan (Essential or higher).
2. **Category**: volume-at-price histogram; the value area is the zone (VAH→VAL band), POC is
   the strongest level.
3. **Source URL**: <https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/>
   `[NOT FETCHED — cite only]`; per-indicator pages for Session/Periodic also seen.
4. **License**: proprietary, closed-source, no community publication. Cannot be reused;
   algorithm can be reimplemented from the public documentation.
5. **Output**: horizontal histogram binned by price; POC line; VAH/VAL lines; the value-area
   band is the zone; HVN/LVN shape is visible inside the profile.
6. **Algorithm** (official docs): lower-timeframe bars of the same symbol are loaded for the
   period; each bar's volume is distributed across the price levels it traded; direction
   up/down by `close >= open`; POC = row with the highest total volume; the value area (default
   **70 %**) is built by starting at the POC and repeatedly comparing the adjacent row above
   and below, adding the heavier side until the target volume is reached; ties prefer the row
   nearer the POC, then the row above. VAH/VAL are the outermost rows added.
7. **Repaint?**: historical profiles are stable; the profile-of-the-current-period updates on
   every bar/tick (that is expected). Visible Range VP recalculates with zoom — descriptive
   only. Session/Periodic profiles are deterministic per completed session/period.
8. **How to make it causal**: build the histogram only from completed lower-TF bars of a closed
   period (previous session, previous H4), then freeze VAH/VAL/POC for the next period; do not
   use the Visible Range variant.
9. **Parameters + ATR scaling**: Value Area Volume 70 % (knob), row size (ticks per row), anchor
   period for the anchored variants, lower-TF selection table. No ATR.
10. **Zone width logic**: emergent from the histogram and the value-area percentage — VA can be
    wide or narrow depending on distribution; not a fixed multiple.
11. **Strength / freshness**: POC volume mass, HVN/LVN; no touch count. Value-area edge is a
    statistical level (70 % convention ≈ 1 σ of a normal distribution, per the docs).
12. **Typical number of zones**: one VA band + POC per period.
13. **Fit for EURUSD M5/M15 with H1/H4 context**: good as the H4/D1 context arm (previous
    session's VAH/VAL/POC as horizontal zones for M5/M15). Caveat: FX volume is tick volume —
    broker-dependent, but consistent enough for level location; the same caveat applies to
    candidates 1, 4, 9, 10.
14. **Confidence**: **high** on algorithm (official docs quote the build procedure); **high**
    that the licence is proprietary.

---

## Notes for the bake-off

**Verified vs unverified, in one line**

- Verified licences: #1, #2, #7, #10 = CC BY-NC-SA 4.0; #5 (and by inference #6) = MPL 2.0;
  built-ins = proprietary. Everything else is `unknown`.
- Verified algorithms from full source mirrors: #1, #5 (v4), #7. All other sections are
  description-level only — treat internals (especially `request.security` usage) as assumptions.

**Realistic to re-implement causally in Python in < 200 lines**

- Easy: #1 (two levels + volume filter), #5 (pivot clustering + strength scan + greedy select),
  #7 (pivot + ATR-slope line), #13 (pivot primitive), #14-confirmed-only (deviation ZigZag),
  #3 (pivot zones + touch counters + merge), #8 (leg-in/base/leg-out detector — moderate, ~150
  lines), #12 (same family as #3 with ATR merge/buffer; but unverified).
- Moderate: #9 (fixed-window volume bins — needs lower-TF data), #11 (BOS/CHoCH OB detector),
  #15 (histogram + value-area expansion — needs tick data or intra-bar OHLC distribution).
- Heavy: #2 (MTF event machine), #4 (four engines + filters), #6 (HTF security + visible-range
  filter), #10 (structure + OB + FVG + EQH/EQL + MTF).

**Duplication — do not test all of these as if independent**

- Pivot-cluster horizontal S/R: #1 → #2 → #3 → #4 → #5 → #6 → #12 all share the same primitive
  (`pivothigh/pivotlow` + cluster/merge + strength). Pick one representative per structural
  choice: `rightBars` lag, merge width model (range % vs ATR vs avg bar range), and strength
  definition (touch count vs bar-touch scan vs composite score). #5 (range % width, bar-touch
  strength, verified source) vs #3 (avg-range width, test count, simple) are the best two
  representatives; #4's ATR buffer is a third useful variant if ported minimally.
- Order-block / S&D: #8 (leg-in/base/leg-out), #9 (volume bins), #10 (SMC), #11 (BOS-anchored OB)
  overlap conceptually. #8 and #11 are the light ones; #10 is the heavy reference.
- Volume-at-price: #9 (fixed window) and #15 (value area) are the same family — one
  implementation with two parameter sets is enough.
- Sloping channels: #7 is the only surveyed representative; a linear-regression channel can be
  added cheaply in Python as a second arm (the built-in TV Linear Regression Channel is
  proprietary; not surveyed).

**License traps**

- CC BY-NC-SA 4.0 (#1, #2, #7, #10): **non-commercial and share-alike**. Algorithms/ideas can
  be re-implemented clean-room for internal research, but code must not be copied into a
  product; if code were reused, the file would have to stay CC BY-NC-SA. #7 additionally ships
  an MT5 port under the same licence, so MT5-side copying is covered by the trap too.
- Invite-only / protected scripts referenced during the search (e.g. "ICT - Multi-Timeframe
  Order Blocks & Fair Value Gaps Levels" by onkelgo2, "OrderBlock/SupplyDemand PRO") are not
  usable — no source, no licence.
- Built-ins (#13, #14, #15) are proprietary; only the public documentation may inform a
  re-implementation.
- Visible-range/zoom-dependent tools (#9, #6's "fits the chart", Visible Range VP) are not
  causal even though they are deterministic at a fixed zoom — exclude them from the bake-off or
  freeze the window.
- `request.security` without lookahead discipline leaks HTF data on historical bars; audit the
  source before trusting #2, #6, #10's MTF parts, #12.

**Coverage gap / things I could not verify**

- "FVG & Order Blocks (ICT/SMC) — Danny_81": no such script surfaced in searches; the closest
  verified substitutes are #10 (SMC) and #11 (TradingFinder OB). Marking the exact
  Danny_81 candidate as not found rather than speculating.
- No standalone "[LuxAlgo] Market Structure" script was located; structure zones are covered by
  #10 in this survey.
- The exact TradingView URL and licence for #8 and #12, and the licence text of every newer
  LuxAlgo script (#3, #4, #8, #9) remain unverified because TV script pages do not render the
  licence in fetched HTML and no source mirrors exist yet.
