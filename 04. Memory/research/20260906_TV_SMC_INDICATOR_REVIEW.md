# TV SMC overlay review vs TB SMC 2026 MT5 (visual 2.45)

Date: 2026-09-06
Reviewer: independent (did not implement `TB_Smart_Money_Concept_2026.mq5`)
Scope: how the SMC overlays that day traders actually load on TradingView *draw*, then the gaps in our MT5 chart. Not a trading-edge claim. Not a git-diff. Engine buffers 2.3 stay out of scope unless a visual fix needs an input that the nested chart already has.

Evidence
- Snapshots: `02. AlphaFactory/tmp/smc_M5_v245.png`, `smc_M15_v245.png`
- Code: `TB_Smart_Money_Concept_2026.mq5` visual 2.45
- Prior notes: `04. Memory/research/20260905_H4_OBJ_CHART_INSET.md`, `20260905_TB_SMC_CHART_EFFECTIVENESS_REVIEW.md`, `20260905_TB_SMC_TV_CONVERT_LOOK.md`
- Pine / docs cited inline. Pine source for IM2GxnOK is open on TradingView but is not mirrored in this repo; visual contract is taken from the published page, the official preview, and the convert-look note (Playwright). LuxAlgo SMC drawing is taken from published Pine (`display_Structure`, Present-mode deletes, Strong/Weak at `n+20`).

Usage counts below are a *who actually loads this* proxy as of 2026-09-06 fetches, not quality.

---

## Ranking — which TV SMC overlays are actually best for a readable day-trading chart, and why

Rank is **tape readability on an execution TF (M5/M15)**, not feature count and not popularity.

| Rank | Overlay | Why it wins / loses on a day-trading chart | Uses (fetched) | URL |
| --- | --- | --- | --- | --- |
| 1 | **TB Smart Money Concept 2026 (TBalgo)** | Explicitly a *clarity* toolkit: Focus Mode, module on/off, one bias HUD, origin cells + voids + sweeps + trail. Preview keeps the working candles free and parks live language in the right-side shift gap. **No LTF H4 box.** This is the Pine we ported; it is the right *contract*, not the most loaded script. | ~1.7k | https://www.tradingview.com/script/IM2GxnOK-TB-Smart-Money-Concept-2026/ |
| 2 | **Smart Money Concepts [LuxAlgo]** | What day traders actually run in 2025–2026 (millions of uses). Dual layer (internal dashed / swing solid), Present vs Historical, last-N order blocks, FVG **off** by default, Strong/Weak High/Low parked in the future gap. Default Historical + all internals on is noisy; **Present + tiny internals + OB last-5** is the readable setup YouTube 2025–2026 still teaches. | ~4.8M | https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/ |
| 3 | **ICT Concepts [LuxAlgo]** | ICT grammar (MSS not CHoCH, BSL/SSL boxes, killzones, NWOG/NDOG) with **Present = latest trend only**, last-N OBs, visible FVG cap 20, liquidity boxes cap 50. Default “most recent only” is the closest thing TV has to IM2GxnOK Focus. Heavier than (1)/(2) if you enable everything. | ~1.1M | https://www.tradingview.com/script/ib4uqBJx-ICT-Concepts-LuxAlgo/ |
| 4 | **FVG & Order Blocks (ICT/SMC) — Danny_81** | 2026 zone *hygiene*: per-category max-shown, max age, display-length cap, overlap merge. Does not try to be a full SMC HUD. Steal the lifecycle, not the whole overlay. | ~1.0k | https://www.tradingview.com/script/nC8SXvhS-FVG-Order-Blocks-ICT-SMC/ |
| 5 | **Multi Timeframe Smart-money Toolkit [S7N]** | Best *HTF without covering LTF* pattern: HTF candles + FVG/OB projected **to the right of price**, nearest-N, auto-mitigate. Not a BOS/MSS overlay. Use as the HTF-display reference, not as a second engine. | ~0.9k | https://www.tradingview.com/script/zr0UJE1Z-Multi-Timeframe-Smart-money-Toolkit-S7N/ |
| 6 | **Smart Money Pro — LonesomeTheBlue (2026-09)** | Paid, dense, but the display contract is professional: Max POI, HTF imbalances/blocks on the **right**, mitigated zones fade, MTF matrix HUD is a table not a candle stamp. Too much for our port to copy. | ~2.4k | https://www.tradingview.com/script/0z6C7YVt-Smart-Money-Pro/ |
| 7 | **ICT SMC Custom — BOS/MSS + OB + FVG** | Honest small overlay: last-N boxes, HTF as **swing lines** (not a nested chart), fade mitigated OBs. Fine community script; not the day-trader default. | ~16k | https://www.tradingview.com/script/mmebBmJL-ICT-SMC-Custom-BOS-MSS-OB-FVG/ |

Honorable mention, **not** ranked for a clean tape: TradingFinder SMC (~547k uses, six OB subtypes — popular, cluttered); LuxAlgo Price Action Concepts (paid PAC: CHoCH+, volumetric OB, MTF dashboard — a second product); Quantum Algo “Confluence Score 0–100”.

**Why (1) over (2) for *our* chart:** IM2GxnOK already chose MSS (not CHoCH), Origin Cell (not OB), Void+CE (not unbounded FVG history), Focus last-N, and a 2×4 HUD. That is a tighter day-trading map than LuxAlgo-with-everything-on. LuxAlgo still wins as the **label geometry** reference (midpoint, transparent, up/down dodge, future-gap Strong/Weak).

---

## How the best ones place labels (offset, dodge candles/wicks, last-N, HTF)

### Shared grammar (what a readable SMC overlay actually draws)

- Structure is a **horizontal line at the broken swing**, not a tag glued to the impulse candle.
- The **word** (BOS / CHoCH / MSS) sits on that line, usually at the **midpoint**, with a transparent chip and a pointer that faces the line so the glyph is *off* the candles.
- Bullish structure: label **above** the line. Bearish: **below**. Wicks are dodged by construction (the line is at the swing extreme; the label is on the other side of that extreme).
- Live extremes (Strong/Weak, Protected/Soft, PDH/PDL) live in the **right-side empty gap** (TradingView chart shift / `n+20` bars), not on the last closed candle.
- Zones are **capped** (last 3–5, max age, stop stretching). Old boxes die or fade; they do not accumulate for years.
- HTF is **not** a second full SMC chart pasted on the LTF candles. TV does lines-on-LTF, right-side HTF candles, or a table. IM2GxnOK does **none**.

### LuxAlgo SMC — exact draw (open Pine)

Source (community mirror of the published script): `display_Structure` in https://raw.githubusercontent.com/acepriority/PineScript/main/smart%20money%20concepts.pinescript and the TV page above.

```
structure_line = line.new(x, y, n, y, style = dashed ? dashed : solid)
structure_lbl  = label.new(int(math.avg(x, n)), y, txt,
                           color = transparent,
                           style = down ? label.style_label_down : label.style_label_up)
if mode == 'Present'
    line.delete(structure_line[1])
    label.delete(structure_lbl[1])
```

| Element | Placement | Dodge | Last-N / hide |
| --- | --- | --- | --- |
| Internal BOS/CHoCH | Midpoint of dashed line; **tiny** | `label_down` (bull, above) / `label_up` (bear, below). Transparent fill. | Present: keep latest only. Confluence Filter can drop “non-significant” internals. |
| Swing BOS/CHoCH | Same geometry; **small**, solid, thicker | Same | Present: last ~two swing marks (community docs / 2025 setup videos). Historical = all of them — that is the clutter mode. |
| HH/HL/LH/LL | On the pivot bar, `label_down` at high / `label_up` at low | Off by default (`show_swings = false`) | Present deletes previous. |
| Strong / Weak High/Low | `n + 20` (future), `label_down` / `label_up` | In the shift gap, not on wicks | One live pair. |
| Internal OB | Last **5**, extend.right, fill ~80% transparent | Box is the zone; no extra word on the candle | Swing OB **off** by default. Mitigated boxes disappear. |
| FVG | **Off** by default. When on: two stacked boxes (gap + CE half), `Extend FVG` bars | No label on the gap by default | Auto Threshold; extend is a bar count, not “to 2099”. |
| EQH/EQL | Midpoint of a dotted line, tiny | Same up/down dodge | Present deletes previous. |
| MTF PDH/PDL | Line to `time + 20*bar`, label `style_label_left` at the **right end** | Future gap | Optional, off by default. |
| Premium/Discount | Boxes on the trailing swing range; words at the box, not on LTF wicks | Off by default | One live range. |
| HTF overlay | None as a nested pane. Optional Daily/Weekly/Monthly high/low **lines**. | — | — |
| Color | Default `#089981` / `#F23645`. Monochrome optional. Color-candles **off**. | — | — |

Docs: https://www.luxalgo.com/library/indicator/smart-money-concepts-smc/ and PAC market-structure (internal dashed + smaller type vs swing solid + larger): https://docs.luxalgo.com/docs/algos/price-action-concepts/market-structures

Day-trader setup that keeps the tape readable (2025–2026 videos, e.g. “How To Setup Smart Money Concepts | LuxAlgo 2026 Update”): M5/M15 → **Present**, internals on (tiny/small), swing on, Strong/Weak on, internal OB 4–5, swing OB off or 2–3 on H1, FVG optional with extend 5–20, PDH/PDL off unless you want them, color-candles optional. Historical is for H1+ “memory”, not for a 5-minute working chart.

### IM2GxnOK (TBalgo) — exact draw (page + official preview)

Page: https://www.tradingview.com/script/IM2GxnOK-TB-Smart-Money-Concept-2026/
Preview (XAUUSD M5, dark, 2026.2.0): HUD top-right `TB SMC 2026 / Bias BEAR / Swing 5 / Edge FOCUS`; teal `#2DD4BF` / pink `#FB7185` fills; blue `×` sweeps on wicks; **Protected H** and **Soft L** sit on dotted rays in the **right empty shift**, not on the last candle; one compact pink origin box + large teal void boxes stretching toward now; **no H4 inset**. Convert-look note: HUD `table.top_right` 2×4, bgcolor `#0F172A`; trail language is Protected/Soft; no LTF H4 overlay.

| Element | Placement | Dodge | Last-N / hide |
| --- | --- | --- | --- |
| BOS / MSS | On the structure level; MSS vs BOS (not CHoCH). Displacement-confirmed. | Small type; Focus Mode hides the archive | Focus = “only the most relevant”; settings are module toggles, not 40 knobs. |
| Origin Cell | Last impulsive zone **before** the break; auto-remove when invalidated | Compact box, not a 2099 wall | Kept-N (Pine default 3). |
| FVG + CE | 3-candle gap + 50% CE | Fill is the zone; CE is a mid | Module toggle. Preview shows large forward fills (TV boxes may extend; our MT5 cropped this on purpose — see Gaps). |
| Sweeps | `×` on the wick that ran the swing and closed back | Marker is *on* the wick by design (that is the event) | Plot, not a stack of words. |
| Protected / Soft H/L | Active range extreme **by bias**; labels in the right gap | Future/shift, not the last body | One live pair. |
| Bias HUD | Top-right table | Away from candles and away from the price axis on TV | Always on in the preview. |
| HTF | **None.** No LTF H4 box, no HTF candles, no PDH lines. | — | — |

Suggested-usage on the TV page is module-off for anything you do not use. That is the hide-contract.

### ICT Concepts [LuxAlgo]

Present mode: **only the latest market-structure trend**. Historical = previous trends too. Last bullish/bearish OB counts. Visible FVG max 20 per direction. Liquidity boxes max 50 per side. Default is “draw what a trader would still have on the chart by hand” (script text). Killzones are session *windows*, not extra words on wicks.

### Danny_81 FVG/OB (2026 hygiene)

Six categories (bull/bear × FVG/OB/Breaker), each with on/off, color, **max-shown**, **max age**, **display length** (stop stretching toward now), overlap merge. Decluttering does not change mitigation. This is the 2026 answer to “every free script leaves 200 boxes”.

### S7N MTF toolkit — HTF without eating LTF

Projects up to 5 HTF candle clusters **to the right of current price** (wicks, bodies, countdown). OB/FVG of those TFs are nearest-N horizontals with a TF tag (`1H OB`), auto-remove on invalidation. Session labels **merge** when they overlap. Debug / prediction table **off** by default. This is the pattern to steal if we keep an HTF affordance on M5/M15.

### LonesomeTheBlue Smart Money Pro

Swing vs internal BOS/CHoCH; CHoCH+ is a failed-continuation then break of a **protected** opposite extreme. HTF POI drawn on the **right**. Max POI count. Mitigated zones increase transparency rather than vanishing instantly. HUD is a **status matrix** (bias / event / PD per TF), relocatable — not a stamp on the tape. Do not copy the alert/JSON/strategy surface.

### MarkitTick Liquidity Flow (invite-only, cited for geometry only)

BOS/CHoCH as a dashed line from origin swing to break bar, **label at midpoint**, transparent background. Same midpoint rule as LuxAlgo.

---

## IM2GxnOK (our Pine source) vs LuxAlgo vs others — label/display contract

| Contract | IM2GxnOK (Pine we ported) | LuxAlgo SMC | ICT Concepts / 2026 hygiene / S7N |
| --- | --- | --- | --- |
| Structure words | BOS / **MSS** | BOS / **CHoCH** (PAC: CHoCH+) | ICT: BOS / **MSS**. Do not rename our MSS to CHoCH. |
| Structure geometry | Level + small word (Focus) | Midpoint of line, transparent chip, up/down pointer | Same midpoint family |
| Archive vs live | **Focus Mode** last-N | **Present** deletes previous; Historical keeps years | ICT Present = latest trend only |
| Origin zone | **Origin Cell** (not an OB) | Internal OB last-5; swing OB off | Danny: BOS-confirmed OB + breaker flip |
| Imbalance | Void + **CE**; fill = half-span | FVG off by default; extend N bars | Visible FVG cap; display-length cap |
| Live extremes | **Protected / Soft** H/L by bias, in the right gap | **Strong / Weak** High/Low at `n+20` | Lonesome: HRLR/LRLR; LuxAlgo PAC: Strong/Weak |
| Sweeps | `×` on wick + reclaim | Not in classic SMC; PAC/ICT have liquidity boxes | Keep `×`; do not add BSL/SSL boxes unless asked |
| HUD | 2×4 top-right, Bias/Swing/FOCUS | None (optional color-candles instead) | Lonesome: MTF matrix; S7N: optional table **off** |
| HTF on LTF | **None** | Optional PDH/PWH/PMH **lines** | S7N: right-side HTF candles; Lonesome: right-side HTF POI; ICT: none as a pane |
| Color | `#2DD4BF` / `#FB7185` / `#818CF8` / `#64748B` | `#089981` / `#F23645` | Do not flatten our overlay to B&W (`default.tpl` is candles only) |
| What they hide | Unused modules; Focus archive | FVG, swing OB, swing points, PD zones, MTF HL — all off by default | Debug labels, prediction tables, historical structure |

Language collision to keep straight: LuxAlgo “Strong High” ≈ IM2GxnOK “Protected H” (bias-side extreme). ICT “protected high/low” is a *swing that has not been broken*. Our buffer comment already says trail is **not** a protected swing (`mq5:17`, `mq5:83`, `mq5:152`). The *visual* still prints `"Protected H"` (`mq5:2168-2171`). That is Pine parity with IM2GxnOK’s published wording, and it is also how a reader who knows ICT (or LuxAlgo Strong/Weak) will misread the chart when the HUD is gone.

---

## Gaps in our MT5 chart vs those best practices (cite snapshot + mq5:line)

Snapshots: EURUSD M5 and M15, last print 1.16132 on 4 Sep 2026, B&W `default.tpl`, teal/pink overlay, nested H4 `OBJ_CHART` bottom-left. HUD navy box is off (visual 2.45). Prior effectiveness review is still right on density; this section is the TV-best-practice delta.

### G1 — Structure words sit on the event candle, not on the line midpoint (visual)

`RebuildVisuals` (`mq5:2049-2072`): BOS/MSS `OBJ_TEXT` is at `time[index]` (the **event bar**) with `labelPrice = level ± atrNow*0.06` and `ANCHOR_LOWER` (bull) / `ANCHOR_UPPER` (bear), font 8.

LuxAlgo / MarkitTick put the word at `avg(pivot, now)` on the **line**, transparent, pointer toward the line. IM2GxnOK’s preview does not glue a stack of BOS/MSS onto one session the way M5 v245 does.

`0.06 * ATR(14)` on EURUSD M5 is a few tenths of a pip. It does **not** clear wicks. On `smc_M5_v245.png` the pre-gap cluster (`BOS`/`MSS`/`CELL` stacked 04:25–15:05) sits inside the bodies. On `smc_M15_v245.png` the same words sit on the 3 Sep rally candles. No second-pass collision offset exists (`CreateTextObject` `mq5:848-862` is a raw `OBJ_TEXT`).

### G2 — Trail language is on the last closed bar, not in the shift gap (visual)

`mq5:2165-2171`: `DRAW_TRAIL_HL/LL` at `lastClosedTime` with `ANCHOR_RIGHT` (text grows **left**, into the last candles).

IM2GxnOK preview and LuxAlgo Strong/Weak put that word in the **right empty gap** (`n+20` / chart shift). On both v245 shots, `Protected H` / `Soft L` sit on the live tape to the right of the last swing, not in a reserved gap. MT5 can do this with `CHART_SHIFT` plus a future datetime (`lastClosedTime + k*PeriodSeconds()`) and `ANCHOR_LEFT`.

### G3 — CELL word is inside the box (visual)

`mq5:2091-2096`: nearest cell only, `"CELL"` at `left, g_cells[i].top`, `ANCHOR_RIGHT_UPPER` font 7 — text grows left and down **into** the rectangle. On M15 v245 the `CELL` chip sits in the pink box on the 4 Sep spike. TV origin/OB labels sit on the **edge**, often at the right of the box or above the high, not in the fill.

There is **no** `"CE"` `OBJ_TEXT` in this file (CE is the dotted mid `mq5:2130-2154`). If a snapshot looks like `CE`, it is the midline or a crushed `CELL`.

### G4 — Focus last-N=10 is the LTF archive mode, then it is copied onto nested H4 (visual, nested density)

`mq5:143-144` default `InpFocusMode=true`, `InpFocusLastN=10`. Cap at `mq5:2044-2046`. Nested H4 is the **host template** `tb_smc_inset.tpl` (`mq5:1539-1602`), so the child inherits 10. `CreateHtfChildHandle` also forwards `InpFocusMode` / `InpFocusLastN` (`mq5:1235-1236`) for the spark-handle path.

LuxAlgo Present on a working chart keeps **the latest** internal and ~**two** swing marks. ICT Concepts Present keeps **the latest trend**. IM2GxnOK Focus in the official preview looks like **live trail + one recent MSS/cell**, not ten structure chips.

On both v245 H4 children, the Aug high is a pile: `MSS`/`BOS`/`CELL`/`Soft H`/`Protected L` on a few bars at `CHART_SCALE=1` (`mq5:177`, `mq5:1357-1360`). That is the worst read on the screen. Nested also copies parent **grid** (`mq5:1361`).

### G5 — Nested H4 is an MT5 affordance IM2GxnOK does not have, and it eats LTF tape (layout)

Confirmed: Pine IM2GxnOK has **no** LTF H4 overlay (`20260905_H4_OBJ_CHART_INSET.md`, convert-look note). TV-best HTF is **right-side** (S7N candles, Lonesome HTF POI, LuxAlgo PDH lines).

Our inset: `InpHtfInsetWidthPct=52`, `HeightPct=46`, floor 460×260, pad X=10 Y=24 (`mq5:175-176`, `mq5:189-192`, `HtfInsetGeometry` `mq5:1327-1353`). Clip AABB pad **80** (`mq5:1469`). On M5 v245 the box covers almost the entire pre-gap session. That is the opposite of S7N (HTF lives in the empty right).

### G6 — Clip hides whole live rays, not the segment under the box (layout / failure mode)

`ClipDrawObjectsUnderInset` `mq5:1460-1517`: any `OBJ_TREND` with `RAY_RIGHT` sets `x2=chartW`, then if the AABB hits the inset+80px the **entire** object goes `OBJ_NO_PERIODS`. Live `Protected H` / void / nearest BOS rays will vanish from the **right** too if working price sits in the lower ~half. These two shots do not show it (trails are above the box). It is still the wrong clip vs “keep live edges, hide archive under the pane”.

### G7 — HUD off with inset removes the only explicit bias/Focus legend (visual)

`UpdateHud` `mq5:1081-1124`: when `InpShowHtfInset` and chart TF ≠ H4, return. Nested H4 also returns on `CHART_IS_OBJECT`. Visual 2.45 honors Owner “delete the blue box”. TV IM2GxnOK **keeps** the 2×4 HUD. Cost: Swing=5 and FOCUS are gone; LTF bias is only `Protected H`+`Soft L`. A reader who treats those words as ICT protected swings will invert the map. Buffer contract still says the trail is **not** a protected swing (`mq5:17`, `mq5:83`).

### G8 — We draw more modules at once than LuxAlgo’s *defaults*

Our map defaults (`mq5:148-154`): structure, cells, voids, sweeps, trail, HUD, **plus** inset. LuxAlgo defaults: internals+swing on, FVG **off**, swing OB **off**, swing points **off**, MTF HL **off**, PD **off**, color-candles **off**. ICT Concepts’ published intent is “most recent only”. We then run that full map **twice** (parent + nested H4).

Sweeps are plots, not objects: arrow 251, `high+0.12*ATR` / `low-0.12*ATR` (`mq5:787-797`, `mq5:2673-2675`). The `×` on the wick is correct (IM2GxnOK / ICT sweep mark). Do not turn them into `SwpH` words on the nested pane.

### G9 — No type hierarchy on nested vs parent (visual)

Parent and child both use font 8 for BOS/MSS and trail (`mq5:2070-2071`, `mq5:2168-2171`). LuxAlgo: internal **tiny**, swing **small**. A scale-1 H4 overview needs tiny or fewer labels, not the LTF size.

### What is already aligned (do not “fix”)

- Teal/pink overlay on B&W candles (convert-look; `default.tpl` ≠ SMC colors). `mq5:139-142`.
- Focus exists as a cap (`mq5:143-144`).
- Zone fills cropped to origin, no 2099 walls (`mq5:2017-2018`, `ZoneBoxRight` `mq5:880-886`). TV preview *does* stretch voids; our crop is the more readable choice — keep it.
- CELL ≠ OB (`mq5:83`).
- Nested HUD off; host not gated on `CHART_IS_OBJECT` alone (`mq5:1088-1099`).
- Clip + `CHART_FOREGROUND=false` so LTF text does not paint *through* the H4 interior on these shots (`mq5:1570`, `mq5:1460-1517`).
- Inset skipped when chart TF == H4 (`HtfInsetAllowed` `mq5:1322-1323`).

---

## Concrete recommendations for the implementer (ordered, visual-only vs engine)

Do **not** change detection, buffers, or iCustom contract 2.3 unless a row says engine. Ordered by how much they improve a day-trading read.

### 1. Dodge BOS/MSS off the candle (visual) — highest leverage

In `RebuildVisuals` `mq5:2064-2071`:

- Place the word at the **midpoint time** of the structure line: `time[(pivot+index)/2]`, price = `level` (the line), **not** `time[index]`.
- Raise the offset from `0.06*ATR` to about **`0.25–0.40*ATR`**, still bull above / bear below. If a wick at that bar still hits the text, bump once more by `0.15*ATR` (one retry is enough; do not search the whole pane).
- Keep `ANCHOR_LOWER` (bull, text above the point) / `ANCHOR_UPPER` (bear). Font **8 on LTF**, **6–7 on `CHART_IS_OBJECT`**.
- Optional LuxAlgo-faithful extra: transparent `OBJ_RECTANGLE_LABEL` is the wrong tool (pixel HUD). Stay with `OBJ_TEXT`. The midpoint + ATR offset is the dodge.

This is the IM2GxnOK/LuxAlgo “word sits on the line, not on the impulse” rule.

### 2. Park Protected/Soft in the right gap (visual)

In `mq5:2165-2171`:

- Anchor time = `lastClosedTime + k*PeriodSeconds()` with `k` ≈ 3–8 (or `ChartGetInteger(CHART_SHIFT_SIZE)` if shift is on). `ANCHOR_LEFT` so the word grows **into the empty right**, not back through the last bodies.
- Ask for / assume `CHART_SHIFT` on the host (TV preview depends on it). Do not invent a second price scale.
- Keep one live pair. Do not print both Strong/Weak *and* Protected/Soft.

### 3. CELL word on the rim, not in the fill (visual)

`mq5:2095`: `ANCHOR_LEFT_UPPER` (or `ANCHOR_LOWER` above `top + 0.15*ATR`) at the **right** of the box (`boxRight`), not at `left`. Nearest cell only (already). **Skip the word** if that bar already has a BOS/MSS chip (nested Aug high is the example).

### 4. Nested H4 density — do not copy LTF FocusLastN (visual, `CHART_IS_OBJECT`)

When `ChartGetInteger(CHART_IS_OBJECT)` (the H4 child):

- Structure cap **3** (or 2), not `InpFocusLastN=10`.
- Font 6–7.
- Drop `"CELL"` text (keep the box). Drop trail **words** or keep a single `H`/`L` glyph; the nested scale cannot carry `Protected L`.
- `CHART_SHOW_GRID=false` on the child (`ApplyHtfInsetTheme` `mq5:1361` currently copies the parent grid).
- Do **not** pass host `InpFocusLastN` through `tb_smc_inset.tpl` as the child’s working cap. Template copy is why v245 H4 is an LTF label set at HTF scale (`mq5:1539-1602`).

This matches LuxAlgo Present / ICT “latest trend” / Danny last-N, on a months-long scale-1 pane.

### 5. Stop drawing these (visual hide-contract)

Stop / don’t add, on a day-trading chart:

| Stop | Why | Where |
| --- | --- | --- |
| BOS/MSS beyond last **3** on nested H4; beyond last **6–8** on M5 if the session is a stack | Focus last-10 is archive mode | `mq5:2044-2072` + G4 |
| `"CELL"` on any but the nearest, and on nested | Box is enough | `mq5:2091-2096` |
| Void **fills** older than the nearest 1–2 (keep edges/CE of the live void) | Danny display-length / LuxAlgo FVG-off default | `mq5:2100-2154` |
| Historical structure **under** the inset (already clipped) **and** live `RAY_RIGHT` that only *cross* the inset band | Clip is hide-whole | G6, `mq5:1460-1517` |
| Nested grid, nested OHLC (OHLC already false), nested volume | Scale-1 noise | `mq5:1356-1362` |
| HTF spark panel + inset at once | Inset already replaces it (`mq5:2175-2176`) | keep |
| A second structure dialect (CHoCH, CHoCH+, HH/HL/LH/LL, EQH/EQL) | IM2GxnOK is MSS/BOS | engine+visual — don’t |

### 6. Clip live edges, not the working tape (visual)

`mq5:1460-1517`:

- Never `OBJ_NO_PERIODS` the nearest BOS line, nearest void edges/CE, or trail rays (`DRAW_TRAIL_*`, `DRAW_STRUCT_*` with `created==0`, `DRAW_VOID_*` nearest).
- Shrink pad 80 → ~16–24 (border, not a second inset).
- Hit-test the **visible segment**, not `x2=chartW`.

### 7. Inset footprint vs TV HTF (layout, visual)

Two honest options — pick one, don’t mix:

**A. Keep nested H4 (current Owner affordance)**  
Drop toward clamp floor **45% × 40%** (still ≥ the 45/40 clamps at `mq5:1331-1332`). That is still large enough to read H4 shape; it gives M5 Asia back. Update `20260905_H4_OBJ_CHART_INSET.md` (it still documents 2.40 42%×36%). Nested recommendations in (4) are mandatory if A stays.

**B. TV-native HTF (S7N / Lonesome / LuxAlgo PDH)**  
No `OBJ_CHART`. One H4 BOS/MSS ray + H4 Protected/Soft in the **right gap**, or HTF candles to the right. IM2GxnOK parity is **B with nothing**. A is the extra.

Do not put HTF boxes on LTF candles (that is the spark we already rejected).

### 8. Bias without the navy HUD (visual, optional)

Keep HUD off if Owner wants the top-left candles. Replace with **one** short `CHART_COMMENT` or inset header fragment: `M5 BEAR · H4 BULL` (from buffer 2 / nested bias). No 200×88 box, no price-axis corner. This restores IM2GxnOK’s “bias is written down” without the v244 occlusion.

If the comment is too much, rename trail words on the **host only** to `Trail H` / `Trail L` (buffer-honest, `mq5:17`) **or** keep Protected/Soft but then the comment is required. Do not leave Protected/Soft as the only legend.

### 9. Engine — do not touch for this pass

- Do not add OB / breaker / EQH / PD zones / killzones / CHoCH+ / confluence score / color-candles.
- Do not change sweep math; `×` at `0.12*ATR` is the right mark.
- Do not publish HTF as buffers (`mq5:77`).
- Do not stretch void rectangles to 2099 to “look like” the TV preview; the crop is the better tape.
- Nested `ChartApplyTemplate` one-shot (`mq5:1585-1588`) is a cold-start footgun, not a look issue; retry is optional hygiene.

---

## What NOT to copy (signal arrows, repainting HUD spam, second strategy)

- **Signal arrows / stars / LONG SHORT.** Quantum Algo ★/○ confluence, S7N C2 prediction table, All-in-One SMC Pro “entries”, ICT SMC PRO “STRONG LONG”. Our events are structural facts (`mq5:56-58`). Plots 3–6 are flags, not orders.
- **Repainting or forming-bar HUD.** Lonesome documents `(Live)` on the current bar; our contract is closed-bar only (`mq5:51-52`). Do not put Bias on bar 0.
- **Color-candles.** LuxAlgo option; it fights Owner `default.tpl` B&W. Overlay stays `#2DD4BF`/`#FB7185`.
- **A second SMC dialect on the same pane.** Do not stack LuxAlgo CHoCH + our MSS, or PAC CHoCH+, or TradingFinder’s six OB classes. One grammar: BOS/MSS, CELL, void/CE, sweep `×`, trail.
- **Historical-everything mode on M5.** LuxAlgo Historical on a 5-minute chart is the clutter those Present-mode videos exist to kill.
- **Invite-only “AI Elite” / 0–100 score / webhook JSON strategy.** Wrong product. Lonesome’s JSON alerts are a strategy surface; we already have closed-bar `EmitTbAlert`.
- **HTF as another full indicator in the LTF fill.** S7N puts HTF in the empty right; we currently put it on top of M5 history. Do not also add PDH/PWH/NWOG/killzone fills.
- **Renaming MSS → CHoCH** to “look like LuxAlgo”. IM2GxnOK and ICT Concepts use MSS; LuxAlgo SMC uses CHoCH. Pick one (we already picked MSS).
- **Treating this review as a reason to change buffer 2.3 or to claim expectancy.** Snapshots are not a backtest.

---

## Source list

- TBalgo IM2GxnOK: https://www.tradingview.com/script/IM2GxnOK-TB-Smart-Money-Concept-2026/
- LuxAlgo SMC: https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/
- LuxAlgo library blurb: https://www.luxalgo.com/library/indicator/smart-money-concepts-smc/
- LuxAlgo SMC Pine (community copy of the open script): https://raw.githubusercontent.com/acepriority/PineScript/main/smart%20money%20concepts.pinescript
- PAC structure (internal dashed / swing solid): https://docs.luxalgo.com/docs/algos/price-action-concepts/market-structures
- ICT Concepts [LuxAlgo]: https://www.tradingview.com/script/ib4uqBJx-ICT-Concepts-LuxAlgo/
- Danny_81 FVG/OB: https://www.tradingview.com/script/nC8SXvhS-FVG-Order-Blocks-ICT-SMC/
- S7N MTF toolkit: https://www.tradingview.com/script/zr0UJE1Z-Multi-Timeframe-Smart-money-Toolkit-S7N/
- LonesomeTheBlue Smart Money Pro: https://www.tradingview.com/script/0z6C7YVt-Smart-Money-Pro/
- ICT SMC Custom: https://www.tradingview.com/script/mmebBmJL-ICT-SMC-Custom-BOS-MSS-OB-FVG/
- MarkitTick (midpoint labels): https://www.tradingview.com/script/gbJey0M4-Smart-Money-Liquidity-Flow-System-MarkitTick/

Workspace: `TB_Smart_Money_Concept_2026.mq5`; `02. AlphaFactory/tmp/smc_M5_v245.png`; `smc_M15_v245.png`; `04. Memory/research/20260905_*`.
