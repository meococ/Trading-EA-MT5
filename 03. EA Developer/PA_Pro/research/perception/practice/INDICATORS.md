# INDICATORS — existing drawing tools & algorithms (PA-ATLAS Step 4)

Scope: tools that auto-draw ranges/boxes, trend lines, S/R
levels/zones, or pattern marks. For each: algorithm in my own words
(no copied code), causal status stated exactly.

**Causality classes:**
- `CAUSAL` — uses only bars ≤ t at decision time.
- `DELAY(k)` — causal but confirms k bars late (e.g., k-bar pivot).
- `REPAINT` — last/current value changes as new bars arrive
  (classic ZigZag leg, unconfirmed pivots).
- `LOOKAHEAD` — right-side data baked into past output (only OK as
  hindsight tool, never for decisions).
- `UNKNOWN` — public description insufficient.

## TradingView scripts

| Name | URL | Author | Licence | Objects | Algorithm (my words) | Params | Causal status | Popularity | Rel |
|---|---|---|---|---|---|---|---|---|---|
| Trendlines with Breaks | tradingview.com/script/IYL88A1N-… | LuxAlgo | invite/closed | lines | Pivot-based trendlines; slope via ATR-normalised or price/bar; marks real-time breakouts | pivot len, slope method, steepness | breaks CAUSAL; lines REPAINT unless locked (author states) | top-published LuxAlgo | 4 |
| Support & Resistance Pro Toolkit | tradingview.com/script/n2ODj57p-… | LuxAlgo | closed | levels, zones | 4 detectors: pivots (left/right), Donchian-alternating state machine (new HH confirms prior LL — no fixed lag), CSID momentum sequence, ZigZag; optional ATR zones, volume/sweep/retest filters, 25-bar projections | engine choice, pivot len, ATR zone depth, min retests, sweep filter | pivots/zigzag DELAY(right) or REPAINT; Donchian-alternating CAUSAL (state change confirms previous extreme) | top-published | 5 |
| Support & Resistance Dynamic | tradingview.com/script/yRHQ9ufY-… | LuxAlgo | closed | zones | Central-tendency estimate; trend-direction-gated S/R zones only (supports in uptrend, resistances in downtrend); extends past levels | multiplicative factor, extension count | CAUSAL (regression/central tendency on window) | high | 3 |
| Auto Trendlines – Dynamic S/R | tradingview.com/script/BjqrEXWg-… | zazenio | closed | lines | Multi-factor scored ranking of candidate pivot-to-pivot lines: pivot quality, touches, survival, proximity to price, S/R flip history, angle, age decay, duplicate & crossed-line filters; shows only top scorers | scoring weights, touch strictness, distance hide, decay | CAUSAL per-bar (scores on history ≤ t); anchor pivots DELAY(right) | new, niche | 5 |
| Auto TrendLines & S/R Ultimate | tradingview.com/script/Iy5iWTCR-… | Trendoscope | open+closed | lines, levels | Considers existing trendlines before scanning new; strength = weighted touches incl. per-candle weight vs line; ATR-normalised angle filter (too flat/too steep rejected); invalidation points emitted | angle ATR loopback, strength factors, max 4 lines | mostly CAUSAL on confirmed pivots → DELAY(k) | mid | 4 |
| Advanced Intraday Darvas Box | tradingview.com/script/hZV01YX6-… | darshakssc | closed | boxes | Confirmed pivots → box top/bottom; min height = ATR multiple; EMA/SMA/VWAP trend filter; volume confirm; breakout needs close beyond by set amount | pivot len, ATR box-min, trend filter, vol threshold, max boxes | CAUSAL + DELAY(pivot confirm) | mid | 4 |
| Auto Darvas Boxes | tradingview.com/script/kYuCIxXq-… | garysebastianbrowniii | closed | boxes | 4-state machine: STATE0 record rangeHigh/Low over N bars + tol → STATE1 validate next N bars (any violation resets from violating bar) → STATE2 active box → STATE3 first close beyond = breakout | N (def 7), tolerance | **fully CAUSAL** state machine | low | 5 |
| Darvas box | tradingview.com/script/EfgGtIXp-… | danilogalisteu | open-source (TV house rules) | boxes | thinkorswim Darvas port; box activates after one higher low; alerts on break | standard TOS params | CAUSAL | mid | 3 |
| Smart Money Concepts (SMC) | luxalgo.com/library/indicator/smart-money-concepts-smc/ | LuxAlgo | closed | levels, zones, marks | Internal vs swing structure lines; BOS/CHoCH labels; order blocks; EQH/EQL; FVGs; premium/discount zones — full SMC grammar automated | internal/swing lookbacks, #blocks shown | CAUSAL labels on confirmed swings → DELAY(k) | very high (most-used SMC tool) | 4 |
| Zero Lag Kalman Structure | tradingview.com/script/LW8nOcaq-… | BOSWaves | closed | zones, structure | Kalman velocity tracking; deviation-normalised structural extremes form zones persisting until invalidated; BOS/CHoCH on top | Kalman params, ATR dev | CAUSAL | mid | 3 |

## MQL5 CodeBase / Market

| Name | URL | Author | Licence | Objects | Algorithm | Params | Causal | Popularity | Rel |
|---|---|---|---|---|---|---|---|---|---|
| AutoTrendLines (WazaTrader) | mql5.com/en/code/61217 | WazaTrader | free code | lines | Mode A: two-pivot lines; Mode B: adaptive slope; breakout arrows; auto-adjust stores ≤3 history lines | 15+ (lookback, offsets, breakout pips) | DELAY(pivot) | new 2025 | 4 |
| AutoTrendLines (Rone, 2012) | mql5.com/en/code/1220 | Rone | free code | lines | Type1: two N-bar fractal extremums; Type2: extremum + lowest-delta bar (delta = distance measure between candidate bars); redraws on new bar | InpLineType, left/right extremum sides, offsets | DELAY(N) (fractal needs right bars); redraws on each new bar → last line REPAINTs until anchors confirm | classic, high downloads | 4 |
| Support and Resistance (Mullerp04) | mql5.com/en/code/45132 | Mullerp04 | free code | levels | Support[i] = lowest low of last `period` bars AND equal to lowest low of `period+overlook` bars (i.e., a low that stays the extreme over a longer window); resistance mirrored; shown only while price between them | period, overlook | **CAUSAL** (all lookback) | mid | 4 |
| Support and Resistance (GODZILLA) | mql5.com/en/code/401 | GODZILLA | free code | levels | Bill Williams fractals (5-bar) as S/R | fractal params | DELAY(2) | high (classic) | 3 |
| Simple_Support_Resistance (Scriptor) | mql5.com/en/code/20435 | Scriptor | free code | levels | Formulaic: Support = 2·Min − Max, Resistance = 2·Max − Min over period | period, line length | CAUSAL (but heuristic formula, not structure) | mid | 2 |
| VibeFox Darvas | mql5.com/en/market/product/181312 | VibeFox | paid | boxes | Darvas box: top = fresh high in lookback; confirmed after N bars unbroken; breakout marks on pierce or close | lookback 20, confirm 3, bars 500 | CAUSAL | n/a (paid) | 3 |

## GitHub / Python

| Name | URL | Author | Licence | Objects | Algorithm | Params | Causal | Popularity | Rel |
|---|---|---|---|---|---|---|---|---|---|
| trendln | github.com/GregoryMorse/trendln | Gregory Morse | MIT | lines, levels | Several methods: (a) extrema of windowed mins/maxs; (b) best-fit lines through local extrema sorted by error; (c) histogram/cluster modes. Caller supplies a series — pass a window ending at t to stay causal | method, window sizes, error sort | CAUSAL if caller truncates; internal extrema detection uses centred windows → LOOKAHEAD if misused | 728★ | 4 |
| support_resistance | github.com/day0market/support_resistance | day0market | (check) | levels | ZigZag pivots (or raw highs/lows) → AgglomerativeClustering merges near pivots into level prices (mean/median) | peak_pct_delta, merge_distance/percent, min_bars_between_peaks | ZigZag last leg REPAINTs; with confirmed pivots → DELAY | 466★ | 4 |
| pytrendline | github.com/ednunezg/pytrendline | ednunezg | MIT | lines | Brute-force all-pairs scan over points [(i,j)]; validity = min points on line + RMSE bound + no candle-body crossing (breakout_tolerance) + optional pivot anchors | min_points, error metrics, ignore_breakouts, pivot req | CAUSAL on truncated window; O(N²) pairs → cheap enough on 84-bar windows | 141★ | 4 |
| Algorithmic-Support-and-Resistance | github.com/BatuhanUsluel/Algorithmic-Support-and-Resistance | BatuhanUsluel | MIT | levels | ZigZag reversal points; reversals within `dif`% and `time` bars averaged into one level; needs ≥`number` points | dif 0.05, time 150, number 3 | DELAY(zigzag confirm); last leg REPAINT | 325★ | 3 |
| sup-res | github.com/arabacibahadir/sup-res | arabacibahadir | GPL-3.0 | levels/zones | Swing-based S/R + "liquidity" levels; sensitivity knob; Pine export | sensitivity | DELAY(pivot) | 183★ | 3 |
| Kairos-v2 feature engine | github.com/PVinh-Quant/Kairos-v2 | PVinh-Quant | (check) | levels, marks | Feature engine incl. ZigZag, fractals, FVG, BOS/CHoCH, S/R blocks across 8 TFs | many | mixed; structure features DELAY(k) | n/a | 2 |
| backtesting.py #395 | github.com/kernc/backtesting.py/discussions/395 | kernc community | — | levels | Community thread: how to add S/R to backtesting.py; links reddit volume-profile code | — | — | n/a | 2 |

## Academic / objective methods

| Name | Source | Objects | Algorithm | Causal | Rel |
|---|---|---|---|---|---|
| Lo–Mamaysky–Wang (2000) | web.mit.edu/Alo/www/Papers/1705-1765.pdf (S20) | patterns, levels | Kernel-regression smooth price → local extrema sequence → pattern definitions (e.g., rectangle = 5 alternating extrema, tops within ~0.75% band; DT within 1.5% of mean) | LOOKAHEAD unless kernel truncated one-sided (right-edge bias acknowledged in paper); with one-sided kernel → CAUSAL with edge noise | 5 |
| DeMark TD Lines | S16/S17 | lines | TD Point level-k = bar extreme with k lower highs (or higher lows) each side; supply line connects two most recent level-k high points (always downsloping); qualified break = close beyond by ≥N ticks + qualifier conditions | DELAY(k): a level-k point confirms k bars late; thereafter fully mechanical | 5 |
| arXiv 2101.07410 SR heuristic | arxiv.org/abs/2101.07410 (S22) | levels | Finds S/R as price levels where direction changes cluster; bounce probability decays with level age | CAUSAL construction | 4 |
| Mullerp04 period+overlook | MQL5 45132 | levels | Extreme that survives both `period` and `period+overlook` windows = standing extreme | CAUSAL | 4 |
| Osler 2000/2003 | S18/S19 | levels | Not an algorithm — evidence that published S/R levels predict interruptions & orders cluster at round numbers | — | 4 (motivation) |
| Garzarelli 2014 | S21 | levels | Bounce prob ∝ prior bounce count — supports touch-count level scoring | — | 3 |

## Top-3 causal algorithms not in our engine — clean-room specs

### C1 — DeMark TD Lines (DELAY(k), fully objective)

From S16/S17 public descriptions only.

```
TDPoint[k] at bar j  <=>  h_j is max of h over [j-k, j+k]   (supply point)
                          l_j is min of l over [j-k, j+k]   (demand point)
confirm time t_conf = j + k
TD Supply Line = segment through the two most recent confirmed
                 level-k supply points; MUST have negative slope,
                 else discard and try next-older point pair.
TD Demand Line mirrored; must have positive slope.
Line extends right until a QUALIFIED break:
  break = close beyond line by >= N ticks (N param, e.g. 1-3 pips);
  qualifiers (public description): prior bar did NOT itself close
  beyond; breakout bar's true range not an extreme spike
  (disqualifier), etc. Qualified break => price projection =
  line price at break ± largest line-to-price distance seen.
Params: k in {1..3} (M5: k=1 or 2), N_ticks, span_max.
```

Cost: O(k) per bar maintain + O(#TDpoints²) rare pair rebuild.
Relation to engine: complementary anchor universe (mechanical TD
points vs our DC/hull pivots) — a clean flagged variant for
`lines.py::_pool`.

### C2 — Donchian-alternating structure detector (CAUSAL, zero fixed lag)

From LuxAlgo S&R Pro Toolkit public description (n2ODj57p).

```
State machine on highs/lows:
  track run_hi = max high since last down-state,
        run_lo = min low since last up-state.
  When price closes below run_hi - d (d = tol or ATR frac):
      the bar that printed run_hi is confirmed as a swing high
      (DELAY = time until state flip, not fixed k); enter down-state.
  Mirrored for swing lows.
Yields an alternating, non-repainting swing stream with variable
confirm lag — usable directly as our line/level anchor pool.
Params: d (reversal threshold, ABR-normalised), min_swing.
```

Cost: O(1)/bar. Relation: replaces `loc_ext_bars`/`DC` pivot
confirmation with an event-driven alternative; similar in spirit to
the engine's DC stream but state-based and tolerance-driven.

### C3 — Darvas 4-state range machine (CAUSAL)

From garysebastianbrowniii "Auto Darvas Boxes" public description +
darshakssc's filters.

```
STATE 0 (define): over last N bars set top = max h + tol,
  bot = min l - tol; remember window start bar.
STATE 1 (validate): next N bars must satisfy h<=top, l>=bot;
  first violating bar -> reset to STATE 0 starting AT that bar
  (no overlap, no half boxes).
STATE 2 (active): box drawn [start, now]; optional quality gates:
  height >= q*ATR (darshakssc), optional rising-box-only flag.
STATE 3 (break): first CLOSE beyond edge marks breakout; box closes,
  edges may carry to a level (role reversal).
Params: N (7), tol, q_min_height_ABR, close-break requirement.
```

Cost: O(1)/bar. Relation: a second, purely mechanical box birth
channel — complementary to `congestion_scan`/`_pivedge_emit`;
implements the "episode container" idea DR-BOX floated, with zero
clustering ambiguity.

## Honourable mentions rejected for top-3

- **zazenio scoring engine** — the closest public analogue to our
  selection problem, but closed-source and only describable at
  factor-list level; absorbed as design input for `salience.py`
  rather than a clean-room baseline.
- **pytrendline all-pairs scan** — causal but O(N²) and duplicates
  what `_scan` already does; its one transferable idea (penalise
  candle-body crossings separately from wick crossings) is noted in
  the atlas (LD2).
- **day0market / BatuhanUsluel zigzag+cluster levels** — functional,
  but ZigZag's last-leg repaint makes them DELAY-class tools our
  pivot stream already covers.

## Implementation status

Baseline scripts for C1–C3 implemented under `practice/baselines/`
(`b_tdlines.py`, `b_donchian.py`, `b_darvas.py` + shared
`bl_common.py` harness and `run_all.py` scorer).  All three are fully
causal: births/dies are computed from bars up to the decision bar;
the only lookahead-style delay is the honest pivot-confirm lag
(TD point usable at `p+k`; swing extreme confirmed on `d` reversal),
stated per algorithm.

Scored on TUNE (198 panels, 456 tau-rows) via
`evalcheck/eval_v2.py` imported through `bl_common.py`, run under
`heavy_run.py` lane `pa-atlas`, 2026-09-23T07:43Z:

| baseline | arm | box@1 | level@1 | line@2 | clutter med |
|----------|-----|-------|---------|--------|-------------|
| C1 TD Lines k=2 | `bl_tdlines_k2` | 0/119 | 0/76 | **29/193** | 6.67 |
| C2 Donchian-alt | `bl_donchian_alt` | 0/119 | **16/76** | 0/193 | 10.33 |
| C3 Darvas N=7 | `bl_darvas_n7` | 2/119 | 0/76 | 0/193 | 0.67 |

Reference: engine v0 author-budget = box 16/119, level 7/76,
line 20/193.  Single-family emitters score structural zeros in the
other families.

Read: the **objective anchor rules alone** already reach 1.5× (lines)
and 2.3× (levels) the engine's author-match — but at far higher
clutter, and without the engine's selection economy.  Darvas reaches
almost nothing (2/119): golden boxes are touch-based, not
containment-state machines — consistent with DR-BOX.

Result rows: `result_row.py show --lane pa-atlas`.
