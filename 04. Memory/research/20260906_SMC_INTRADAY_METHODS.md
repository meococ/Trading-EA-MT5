# SMC intraday methods → TB SMC 2026 display map

Date: 2026-09-06
Author: independent researcher (did not implement `TB_Smart_Money_Concept_2026.mq5`)
Scope: how serious retail / ICT-style day traders *use* Smart Money Concepts on an
intraday chart, which building blocks actually combine, and how that should change
**logic display and labels** on our MT5 port. Not a new EA. Not an edge claim.
Buffer contract **2.3 stays**. Do **not** rename CELL to OB.

Evidence:
- Web: ICT 2022 mentorship (YouTube, public), secondary ICT notes, LuxAlgo concept
  pages, TBalgo Pine listing IM2GxnOK
- Local: `TB_Smart_Money_Concept_2026.mq5` visual 2.45 / contract 2.3
- Snapshots: `02. AlphaFactory/tmp/smc_M5_v245.png`, `smc_M15_v245.png`
- Prior review: `04. Memory/research/20260905_TB_SMC_CHART_EFFECTIVENESS_REVIEW.md`

Legend used below:
- **Documented** — ICT public teaching, TBalgo listing, or LuxAlgo education that
  matches a checkable chart sequence (still not proof of expectancy).
- **Folklore** — retail blogs, Discord grammar, or contested definitions. Useful
  as chart-language, not as a spec.

No profitability claims. One backtest is never proof. Raw BOS/MSS/void flags are
structural facts, not entries (`mq5` header ~54–58).

---

## Intraday SMC playbook (short)

The usable intraday loop is **top-down, then wait**. It is not “paint every SMC
object and pick one.”

### Timeframe stack (typical, not unique)

| Layer | Common TFs | Job |
| --- | --- | --- |
| Bias | Daily and/or **H4** (sometimes H1) | Direction + draw on liquidity |
| Location | **H1 / M15** | Has price reached the HTF zone? Session / PDH-PDL raid? |
| Trigger | **M5 / M1** (sometimes M15 as execution) | Sweep → displacement/MSS → retrace into the void |

Sources: ICT 2022 mentorship (community name **Model 2022**); LuxAlgo
[Model 2022](https://www.luxalgo.com/library/concept/model-2022/) (“raid → MSS →
FVG entry”; bias/pools on 15m–H1, execution 1–5m inside London/NY);
[The Inner Circle Traders, LTF entry](https://www.theinnercircletraders.com/ict-lower-timeframe-entry/)
(HTF Daily/4H = where; MTF 1H/15M = arrival + sweep; LTF 5M/1M = MSS + FVG);
TBalgo [TB Smart Money Concept 2026](https://www.tradingview.com/script/IM2GxnOK-TB-Smart-Money-Concept-2026/)
(“trade in the direction of the displayed market bias”; “watch for liquidity
sweeps into Origin Cells or Fair Value Gaps before looking for confirmation”).

**Documented sequence (ICT 2022, public):**

1. HTF bias and a draw (old high/low, session extreme, equal highs/lows).
2. During a **killzone**, price **raids** the opposite pool (Judas / stop hunt).
3. **Displacement** closes through the recent opposing swing (**MSS** in ICT
   2022 language).
4. Enter the **FVG** that displacement left (often at **CE** = 50%), stop beyond
   the raid, target the far-side pool.

LuxAlgo’s Model 2022 page is honest that “Model 2022” is **community shorthand**,
not a formal spec, and that the smart-money *mechanism* is interpretation; the
checkable thing is the **sequence**. Treat it that way.

### Building blocks — what they are, and how they combine

**Market structure: BOS vs MSS / CHoCH**

- **BOS** (**documented**, LuxAlgo SMC + ICT secondary): break of a swing *in*
  the existing trend. Continuation. You do not re-decide bias on every BOS.
- **CHoCH** (**documented** as “first break against the trend”): warning that
  character changed. Not automatically an entry.
- **MSS** (**contested / folklore at the definition layer**): ICT 2022 uses MSS
  as the LTF *trigger* after a raid (close through the opposing short-term
  swing, with displacement). Later blogs disagree with each other:
  - some: MSS = CHoCH + displacement + FVG
  - some: MSS = CHoCH + preceding sweep
  - some: MSS is a later confirming HH/LL after CHoCH
  Our engine does **not** implement any of those extra ICT filters. In
  `ProcessClosedEngineBar`, a close-through + ATR impulse against current bias
  is **MSS**; same-direction or first break from FLAT is **BOS**
  (`mq5:2511–2561`). That is **LuxAlgo-style BOS/CHoCH**, with the reversal
  label named **MSS** to match TBalgo — not ICT’s “MSS = raid + displacement.”

**Liquidity sweep / stop hunt, then displacement**

- Sweep (**documented** as a chart event): wick beyond a *live* pool, close back
  inside. Our engine: live swing required, close back by `ATR * sweepReclaim`
  (`mq5:50, 2659–2675`). A level already consumed by BOS is not swept — that
  matches the “don’t hunt a broken swing” idea.
- Displacement (**documented** as *energy*, not a separate object): large-bodied
  impulse that breaks structure and usually prints a void. Our impulse flag is
  `body >= ATR * 0.45` on *every* such candle (`mq5:11–12, 2432–2436`), not
  “displacement of the BOS bar.” Chart should not label every impulse.

**FVG / imbalance / price void + CE**

- 3-candle gap (**documented**, ICT + LuxAlgo CE page + TBalgo “FVG + CE”).
- **CE** = 50% of the gap (**documented** as ICT *consequent encroachment*).
  Folklore: “always enter at CE.” ICT also teaches the gap *edge* (IOFED) and
  does not require a full fill.
- Our void fill is **half-span**, not “touch CE” (`mq5:48–49, 2640–2656`).
  Touching CE does not mitigate. That is stricter than much retail FVG folklore
  and should stay visible as a *rule*, not as a second product.

**Order block vs Origin Cell**

- Classic **OB** (**documented** ICT): last *opposing* candle before a
  displacement that breaks structure. Entry often at the body mean threshold.
- **CELL** (**TBalgo dialect, documented on IM2GxnOK, not ICT**): “last
  impulsive zone before a valid structure break,” auto-removed when
  invalidated. Our geometry is an 8-bar lookback to the **extreme candle**
  (lowest low for a bull break, highest high for a bear break), inclusive of
  the break bar (`mq5:46–47, 182, 2525–2546`). Header is explicit: **not an
  Order Block; not necessarily this bar’s BOS.**
- Do not draw classic OBs on top of CELLs. They occupy the same narrative slot
  (“origin of the impulse”) with different boxes. Contract 2.3 forbids treating
  buffers 19–21 as OB.

**Premium / discount, killzone / session**

- **Premium/discount** (**documented** ICT dealing-range): buy in the lower half
  of the active range, sell in the upper half. Folklore: any fib 50% anywhere.
- **Killzones** (**documented** ICT, NY local time; windows vary by lecture):
  - London open **02:00–05:00** NY — ICT 2022 Episode 20 transcript:
    “two o’clock in the morning to five o’clock in the morning new York local
    time”
  - New York AM commonly **07:00–10:00** NY (7–9 in some notes; 7–10 in others)
  - Asia is usually a *range to raid*, not an entry window
- Our indicator has **no session, no PD array, no killzone inputs**
  (`mq5` Look/Map/HTF groups `137–177`). Time-of-day is currently invisible.

**Trailing Protected / Soft vs live swings**

- ICT “protected” swing (**folklore-adjacent ICT talk**): a swing that has not
  been taken, so stops still rest there.
- TBalgo **Protected & Soft Highs/Lows** (**documented** on IM2GxnOK): “active
  range extremes based on the current market bias.”
- Our **buffers 17/18 are running extrema**, not protected swings
  (`mq5:17, 83, 152, 2702–2713`). Visuals still stamp **“Protected H/L”** vs
  **“Soft H/L”** from `ExtBias` (`mq5:2167–2171`). Bear bias → Protected High +
  Soft Low; bull bias → Soft High + Protected Low. That is a **bias legend**,
  not ICT “this high still has stops.” Contract text: “Trail not Protected.”

### First two seconds vs noise

A day trader who already knows the grammar glances for **two or three facts**:

1. **HTF sentence** — is H4 still bull or bear? Where is the last H4 MSS / the
   dealing-range extreme?
2. **Location** — is LTF at a raid (session/PDH-PDL/live swing) or mid-range
   chop?
3. **Trigger** — did LTF just **sweep then MSS** in the HTF direction, leaving a
   **living void**?

Everything else is inventory: every historical BOS, old CELLs, filled void
halves, impulse dots, nested-H4 labels from July, HUD version strings.

If the method is “HTF bias, then wait for LTF sweep + MSS,” the chart should
**shout those 2–3 facts and stay quiet on the rest.**

---

## Coherent method combinations (and what not to mix)

### Combinations that form one story

These are **one sequence**, not five confluences stacked for a higher “score.”

| Combo | Role of each piece | Status |
| --- | --- | --- |
| **HTF bias + LTF sweep + MSS + FVG** | Bias = permission. Sweep = fuel. MSS = confirmation. Void/CE = entry map. | **Documented** ICT 2022 / LuxAlgo Model 2022. TBalgo suggested usage is the same shape with CELL as the origin zone. |
| **Sweep of a live extreme + displacement + void** | Raid then energy then imbalance. Stop beyond the raid. | **Documented** sequence. Our live-swing sweep rule already encodes “don’t sweep a consumed BOS.” |
| **Session liquidity + MSS** | Asia/London/PDH-PDL is the pool; MSS is the turn after the raid, preferably in a killzone. | **Documented** time+liquidity. We do not draw sessions today. |
| **HTF void/CELL as location + LTF MSS as timing** | HTF box = where. LTF MSS = when. Do not hunt LTF MSS in the middle of nowhere. | **Documented** top-down. Nested H4 exists for this. |
| **Premium/discount as a mute filter** | Longs from discount of the *H4 dealing range*, shorts from premium. Not a signal. | **Documented** ICT PD. We do not draw EQ. |

LuxAlgo’s free SMC write-up (internal vs swing BOS/CHoCH, OB in premium/discount,
EQH/EQL as pools) is the same **filter stack**: swing structure = bias, internal
= timing, zone = location. Their Confluence Filter exists because **internal
BOS spam is noise**.

### What conflicts or double-counts

| Mix | Why it hurts the chart |
| --- | --- |
| **CELL + classic OB** | Same narrative slot, different geometry. Contract: CELL ≠ OB. Do not add OB boxes. |
| **Void labeled “FVG” plus a second FVG indicator** | Same 3-candle gap. We already have voids + CE. |
| **Every BOS labeled at equal weight to MSS** | BOS is continuation tape. The playbook trigger is the **latest MSS after a sweep**. Ten equal BOS/MSS words is a kitchen sink. |
| **CHoCH labels on top of our MSS** | We already use MSS for the against-bias break. A second name is folklore collision. |
| **Protected trail + live swing both labeled as “the” high** | Trail = running extreme (`17/18`). Live swing = `13–16`. ICT stops sit at the **swing**, not necessarily the running high. Two pink highs without a legend mis-teach “protected.” |
| **HUD Bias + Protected/Soft** | Same fact twice. Fine if one is a 12-px chip; not fine as a 200×88 navy box *and* two trail words. v245 already dropped the box when the inset is on. |
| **FocusLastN=10 copied onto nested H4** | LTF Focus density on a months-long scale-1 pane. Double-count in *time*: July BOS is not today’s HTF sentence. |
| **Internal + swing structure both fully labeled** | LuxAlgo’s own answer is a confluence filter. We have one swing length (default 5). Do not add a second structure layer. |
| **Killzone shading as a “buy now” tint** | Time filter, not a setup (LuxAlgo Model 2022: killzones are not setups). |
| **OB+FVG overlap as automatic A+** | Retail folklore. Overlap is one location, not two reasons, if CELL *is* the origin of the same displacement that printed the void. |

TBalgo’s own suggested usage is already a **filter**, not a union: bias first,
then sweep *into* a CELL or FVG, *then* confirmation. That is combo 1 with CELL
standing in for OB. Honor that; do not also paint ICT OBs.

---

## What must be visible on M5/M15 + nested H4 for that playbook

Assume the working chart is **EURUSD M5 or M15** with nested **H4** (current
Owner layout). Playbook = HTF bias, then wait for LTF sweep + MSS into a living
void/CELL.

### Must shout (readable in two seconds)

**On the parent (M5/M15), right-hand working area:**

1. **LTF bias in one token** — currently encoded only as `Protected H` + `Soft L`
   (bear) vs `Soft H` + `Protected L` (bull) (`mq5:2167–2171`). Keep the live
   trail rays. A reader who does not know the legend cannot read bias
   (review Issue 3).
2. **The latest LTF MSS** (solid, thicker — already `STYLE_SOLID` width 2 vs BOS
   dash width 1, `mq5:2065–2071`) and **only that MSS** as a word. Older BOS
   can stay as quiet dashes without text.
3. **The latest live-swing sweep** if it still matters (accent `x` on the bar
   that raided a *live* swing). Historical `x` scatter is tape, not the trigger.
4. **Newest living void + CE** — half-boxes at the origin, CE midline, **one
   “CE” word** on the nearest living gap. Entry map of combo 1.
5. **Newest CELL** as a box + one `CELL` word (not every kept cell). Location
   of the impulse, TBalgo dialect.

**On nested H4 (bias pane, not an execution pad):**

1. **H4 bias** — trail Protected/Soft *or* one short `H4 BULL|BEAR` in the child
   header. The 2026-09-05 review already noted LTF Protected H / Soft L vs H4
   Protected L as the dual-TF sentence. That disagreement is the feature.
2. **Last 1–2 H4 MSS/BOS** so the dealing-range direction is obvious. Not ten.
3. **H4 live extreme** (Protected/Soft rays). Optional: one H4 CELL *shape*
   without a word if it collides.

**Optional, mute, still playbook-true:**

- One H4 structure level projected on the parent (`InpShowHtfBreakOnChart`,
  currently **false**, `mq5:171, 1947–1970`). That is the HTF sentence on the
  LTF tape without reading the inset.
- Session bands (London / NY AM) as **background**, no labels in the price
  path. Time filter, not a signal.
- A 12-px chip `M5 BEAR · H4 BULL` that does not cover candles or the price
  axis (review Issue 3 suggestion). Not the old 200×88 navy HUD.

### Must stay quiet

- Historical BOS words on M5 (Friday stack on `smc_M5_v245.png`).
- Nested-H4 label pile at the August high (`MSS`/`BOS`/`CELL`/`Protected L`
  on a few bars — review Issue 1).
- CE unlabeled *and* CELL labeled on the same cluster (the gap should speak
  as a fill + midline; CELL as a separate origin box).
- Impulse flags, ATR, swing length, FOCUS/FULL, version string.
- Nested HUD, nested grid extras, HTF spark panel while the inset is on
  (already deleted, `mq5:2175–2176`).

---

## Gaps vs our current chart (snapshot + mq5:line)

Snapshots: EURUSD 4 Sep 2026, last 1.16132, B&W `default.tpl`, overlay teal
`#2DD4BF` / pink `#FB7185`. Nested `OBJ_CHART` H4 ~Jul–Sep. Visual 2.45, HUD
panel off when inset on.

| Playbook need | What the v245 chart actually shows | Gap |
| --- | --- | --- |
| HTF bias in two seconds | Nested H4 *shape* is a Jul–Aug rally then pullback; `Protected L` on H4 ⇒ nested bull. No written `H4 BULL`. | Reader must know the trail legend. `UpdateHud` returns early when inset on (`mq5:1088–1099`). |
| LTF bias | Parent `Protected H` + `Soft L` ⇒ LTF bear. Correct encoding, cryptic. | Same legend problem. Dual-TF **disagreement is correct** and currently implicit. |
| Latest MSS louder than BOS tape | M15 right side: recent pink `MSS`/`BOS` + CELL is usable. M5 left of the weekend gap: Focus last-N=10 words stacked on one session (`mq5:2044–2072`). | M5 fails the “shout 2–3 facts” test. M15 is closer. |
| Sweep then MSS | Sweeps are accent Wingdings 251 (`x`), plots 0/1 (`mq5:787–797, 2670–2675`). No `SwpH`/`SwpL` DRAW_ text. String exists only in HUD last-event (`mq5:1070–1072`). Reviewer shorthand `SwpH` on nested H4 is HUD dialect, not a live object. Historical `x` on H4 left (July) and M5 Friday are noise. | The *latest live-swing* raid is not distinguished from old `x`. |
| Living void + CE | Nearest void halves + dotted CE ray (`mq5:2100–2154`). **No “CE” text.** Fill = half-span (good, undocumented on-chart). | CE does not shout. Trader looking for the 50% word will not find it. |
| CELL as origin, not OB | Newest CELL box + `CELL` word (`mq5:2091–2095`); older cells are boxes without text. Geometry = 8-bar extreme, not last opposing candle. | Correct dialect. Risk: readers still call it OB. Do not “fix” by renaming. |
| Trail vs protected swing | Rays + Protected/Soft words (`mq5:2157–2171`). Engine is running extreme (`mq5:2702–2713`). | Label lies relative to contract (“Trail not Protected”, `mq5:83`). Teaches the wrong ICT meaning of “protected.” |
| Session / killzone | Absent. | Playbook combo 3 is invisible. Friday vs Sunday gap on M5 is FX weekend, not a session map. |
| Premium/discount | Absent. Trail high/low *could* imply a dealing range; 50% is not drawn. | Filter layer missing. Do not auto-trade it. |
| Nested H4 as bias pane | Real H4 child, scale 1, usable as *overview*. Labels collide on the last swing (review Issue 1, `mq5:2044–2071` FocusLastN inherited). Grid copied in (`ApplyHtfInsetTheme`). | HTF *detail* unreadable; HTF *shape* OK. |
| LTF tape under the inset | Inset ~52%×46% + clip pad 80 (`mq5:175–176, 1469`). M5 Asia/London morning sits under the box. Clip hides **whole** rays whose Y overlaps the band (`mq5:1506–1514`). | Playbook does not need that much LTF history, but live trail/void rays must survive on the right. |
| One H4 level on LTF | `InpShowHtfBreakOnChart=false`. | Missed cheap way to shout HTF on the working pane. |

What already matches the playbook (do not regress):

- Teal/pink on B&W candles (TV colors, not greyscale SMC).
- MSS solid vs BOS dashed.
- CELL ≠ OB in code and inputs (`mq5:149`).
- Live-swing-only sweeps.
- Void CE deleted when both halves die (no orphan CE, `mq5:48–49, 2130–2145`).
- Nested H4 is a real chart, not an 8-bar spark.
- LTF DRAW_ text is clipped out of the H4 interior on these two shots.
- Buffer 2.3 mapping (bias, BOS/MSS, sweeps, voids, cell, trail, CE).

---

## Concrete implementer list

Visual / logic-display only. Keep iCustom buffers 0–43 = contract 2.3. Keep
`ExtTrueRange` as buffer 44. No public HTF buffers. No new strategy EA.

### Logic / display (not a new strategy EA)

1. **Define a display mode for the playbook, not a new engine.** Default
   Focus on M5/M15+inset should mean: *latest MSS word, latest living void+CE,
   newest CELL, live trail, latest live-swing sweep*. Historical BOS remain
   dashes without text. Do not change how BOS/MSS/voids are *calculated*.
2. **Keep CELL labeled CELL.** Never alias to OB in UI, comments, or alerts.
   If a tooltip/comment is added, say “origin cell (not order block; 8-bar
   extreme before the break).”
3. **Stop teaching ICT “protected swing” with trail labels.** Options that
   stay honest to buffers 17/18:
   - `Trail H` / `Trail L` plus a tiny `BEAR`/`BULL` chip, or
   - keep Protected/Soft **only** as the bias legend but add a one-line
     comment that these are running extrema, not untaken swings.
   Contract header already says “Trail not Protected.”
4. **Make CE a word once.** Nearest living midline only (`g_voidMids` loop
   `mq5:2132–2154`). Do not stamp `CE` on every half-box.
5. **Distinguish latest live sweep from historical `x`.** Cap visible sweep
   markers to last 1–2 live-swing events, or mute alpha on older arrows.
   Do not invent `SwpH` objects unless they are clipped-safe and last-N.
6. **Nested H4 is a bias map.** When `CHART_IS_OBJECT` (or `_Period ==
   InpHtfPeriod` inside the inset): structureCap ≈ 3–4, drop CELL/Protected
   *text* if they share an anchor bar, smaller font, no FocusLastN=10
   (review Issue 1). Keep H4 CELL *boxes* if they still read as zones.
7. **Optional mute HTF sentence on the parent:** allow
   `InpShowHtfBreakOnChart` as a display default for M5/M15+inset, one dashed
   H4 BOS/MSS ray with `H4 MSS↓` (or similar) on the right — not a second
   full SMC overlay.
8. **Optional mute session bands** (London 02:00–05:00 NY, NY AM 07:00–10:00
   NY). Background only. No “KZ” stamps in the candle path. Document that
   windows are ICT lecture ranges, not an edge. Crypto/H4 Saturday close is
   a known past mistake for countdown text — do not revive `HtfCountdownText`
   `gap` logic as a session map.
9. **Do not add classic OB, EQH/EQL, breaker, OTE, or a second FVG layer.**
   Those double-count CELL/void/sweep.
10. **Do not add CHoCH as a third structure word.** Our MSS already is the
    against-bias break. Document the ICT terminology mismatch in a comment
    near `isMss=(g_bias<0)` (`mq5:2513`) so the next port does not “fix” it
    into a different engine.
11. **Clip live working rays out of the hide list** (review Issue 2,
    `mq5:1460–1514`). Playbook rays (trail, nearest void, nearest MSS) must
    remain on the right even if their Y overlaps the inset band.
12. **Keep HUD off with inset on.** If bias must be written, use a chip or
    inset-header fragment, not `HUD_BACKGROUND` 200×88 (`mq5:1102–1123`).

### Label rules: dodge candles/wicks, last-N, nested H4 quieter

Current text placement is **unoffset** except BOS/MSS `± ATR*0.06`
(`mq5:2067–2071`). CELL uses `ANCHOR_RIGHT_UPPER` on the box top
(`mq5:2095`). Trail uses `ANCHOR_RIGHT` on the last closed time
(`mq5:2168–2171`). No collision walk.

Implement:

- **Dodge:** if the label AABB overlaps a wick/body or another DRAW_ text,
  step ±0.5–1.0 ATR or one bar, then give up (hide the older word). Do not
  invent a layout engine; a single retry is enough.
- **Parent last-N (Focus):** structure *words* default **4** on M5, **6** on
  M15 (not 10). Structure *dashes* may keep a higher cap. CELL word = newest
  only (already). CE word = newest living only (new). Trail words = two,
  always, on the right.
- **Nested H4 last-N:** structure words **3**. No CELL/CE/Protected text if
  two labels share the same bar or sit inside 1 ATR. Font 6–7 vs parent 8.
- **Z-order:** trail + latest MSS + CE above old BOS. Inset clip after
  rebuild (`mq5:2180–2183`) stays.
- **Never park words on the price axis** (Owner past mistake:
  `CORNER_RIGHT_UPPER` HUD). Trail `ANCHOR_RIGHT` at last-bar time is the
  correct side as long as `CHART_SHIFT` leaves a pad; if the last bar is
  against the scale, nudge left by one bar.

### What to hide

- BOS **text** older than last-N; keep quiet dashes if Focus still wants
  structure context.
- CELL **text** on cells `i>0` (already). Consider hiding CELL boxes `i>1`
  on M5 Focus.
- Void half-boxes that are not the newest *or* not intersecting the visible
  time window; keep newest always.
- All impulse plots (already `DRAW_NONE` for buffers 11/12 — keep).
- Navy HUD, HTF spark panel, HTF countdown, version/Swing/FOCUS strings
  while the inset is the HTF pane.
- Nested chart grid if it fights H4 candles (`ApplyHtfInsetTheme`).
- Historical sweep `x` beyond last 1–2 live events.
- Any future “A+/confluence score” dashboard. Folklore.

---

## Out of scope (do not recommend)

- New EA, iCustom consumer, or “entry model” that fires on sweep+MSS+FVG.
  Header already: raw events are not signals; host must apply its own risk,
  session, spread (`mq5:54–58`).
- Renaming CELL → OB, or drawing ICT order blocks beside CELLs.
- Changing buffer indices, adding public HTF buffers, or moving
  `ExtTrueRange` off 44.
- Claiming expectancy from these snapshots, from ICT lectures, or from one
  tester pass. LuxAlgo Model 2022: no published independently verified
  track record; discretion at every joint.
- Silver Bullet / 2024-model **timeboxed auto entries**.
- Killzone as a buy/sell tint or alert.
- Stacking LuxAlgo SMC, a second FVG, or an OB detector on this EX5.
- `mt5__trade_*`, `terminal64.exe`, Owner-GUI `path=`, worktrees, commits.
- Recoloring B&W `default.tpl` candles to match TV. Overlay stays teal/pink.
- Using `HtfCountdownText` weekend `gap` as session logic (past mistake).
- Treating nested H4 as an execution pad (scale 1, months of history).

---

## Source notes (documented vs folklore)

**Closer to primary / vendor docs**

- ICT 2022 YouTube mentorship, Episode 20 (London killzone 2–5 AM NY, public
  transcript). Playlist: Inner Circle Trader, 2022 Mentorship.
- TBalgo, *TB Smart Money Concept 2026*, TradingView `IM2GxnOK` (BOS & MSS +
  ATR displacement, Origin Cells, FVG+CE, sweeps, Protected/Soft, Focus,
  suggested usage).
- LuxAlgo, [Model 2022](https://www.luxalgo.com/library/concept/model-2022/)
  (raid → MSS → FVG; killzones as time filters; caveats on discretion and
  mechanism).
- LuxAlgo, [Smart Money Concepts (SMC) indicator](https://www.luxalgo.com/library/indicator/smart-money-concepts-smc)
  and [SMC overview](https://www.luxalgo.com/blog/smart-money-concept-indicator-for-tradingview-free/)
  (BOS vs CHoCH, internal vs swing, premium/discount, confluence filter).
- LuxAlgo, [Consequent Encroachment](https://www.luxalgo.com/library/concept/consequent-encroachment/)
  (CE = 50% of the 3-candle gap).
- This repo: `TB_Smart_Money_Concept_2026.mq5` contract 2.3 / visual 2.45;
  `04. Memory/research/20260905_TB_SMC_CHART_EFFECTIVENESS_REVIEW.md`.

**Secondary / mixed (use as language, not spec)**

- innercircletrader.net / theinnercircletraders.com / ictkillzone.com —
  useful restatements of 2022 flow; MSS vs CHoCH tables **conflict across
  articles** (folklore at the definition layer).
- Retail “7 SMC setups,” “A+ confluence,” “OB+FVG = highest probability” —
  folklore. Sequence beats score.
- ICT 2024 model write-ups (time window + sweep + displacement MSS + FVG) —
  later mentorship restatement, not required for this display map.

**Our dialect vs ICT (do not “correct” silently)**

| Word | ICT public use | TB / this EX5 |
| --- | --- | --- |
| MSS | LTF trigger after raid + displacement | Against-bias close-through + ATR impulse |
| CHoCH | First countertrend break | Not a label (MSS covers that slot) |
| OB | Last opposing candle | Not drawn |
| CELL | — | 8-bar extreme origin; **not OB** |
| FVG | 3-candle imbalance | Price void; extra `close[index-1]` gate (`mq5:2600–2603`) |
| Protected | Untaken swing (talk) | Running trail labeled from bias |
| Focus | — | Last-N structure words + nearest rays |

Implementers should display **TB’s map more clearly for the 2022-style
playbook**, not re-spec the engine to a different ICT blog.
