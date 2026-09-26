# VOLMAN PERCEPTION SPEC v1 — the "eyes" of PA-PRO

Owner of this spec: Lead (Linh). Issued 2026-09-21T05:59Z. Binding on the PERCEPTION lane (Python reference) and the EA lane (MQL5 port).

Source: a fresh, page-by-page reading of Bob Volman, *Understanding Price Action* (Vietnamese edition, 447 pages), done by 12 readers under the Lead's direction. Every page image was viewed and all 400+ charts were catalogued.
- Reading notes: `EA_VolmanPA/PLAN/book/_private/notes_perception/notes_NN_pAAA-BBB.md` (private, gitignored; paraphrase only, as the book is copyrighted).
- Page refs below are book pages. "[cb]" means casebook evidence (chapter 9, 1 Mar – 31 Aug 2012). "[m]" means pixel-measured from the figures.

The Owner's standing rule also applies: support and resistance are **small zones** that can shift, not exact "pretty" lines. Hard lines clutter the chart.

---

## 0. Why this spec exists

**Symptoms.** The zone generators we have are dense. Up to 6 armed zones sit within ±2 ATR(H1), about one every 10 pips on EURUSD. The SF01 "box" was loose (F6 at 4×ATR was a spike and a fade, not a box). The Owner's verdict: the drawing is not good enough.

**How Volman actually reads a chart:**
- The chart is almost bare.
- He draws **one box or one line per structure**, about 3 objects per chart (0–8) [cb].
- Box and line edges are **fixed** once set. Later pokes become **events** (T = tease, F = false), not new edges.
- He never draws round numbers; the 00/50 levels are the platform's grid, which he uses as context.
- Squeezes, domes, M/W middle sections and obstacles are read against a few well-chosen edges.

The EA's eyes must reproduce **that economy and that stability**.

---

## 1. Canvas and units

- **Series:** M5 bid OHLC, closed bars only. The engine is causal: objects at bar t use bars ≤ t only.
- **EMA25** on close, the only indicator (p47). Keep its history longer than the window so the slope at the left edge is known (p60, p76).
- **Round-number grid (context layer, never drawn as structure):**
  - 00/50 levels (p43–48).
  - In a declared low-volatility regime, the 20-grid (00/20/40/60/80) (p417). Default regime switch: rolling median daily range < 60 pips on EURUSD, scaled by symbol.
- **Visible window:** about 84 bars (7 h), never more than 1 trading day of structure (p47–48). Carried levels may originate earlier in the same day.
- **Clock:** Volman's charts are CET/CEST. Session marks: Asia 00:00, EU 08:00, London 09:00, US 15:30 (p48). Keep a helper that converts any series to CET/CEST, with tests on both DST switch weeks.
- **Scale unit:** ABR = average bar range (high−low) of the last 50 closed M5 bars. Every tolerance is written in pips for EURUSD with its ABR equivalent, so the engine ports to other symbols. On EURUSD 2012, ABR ≈ 4–7 pips.
- **Edge tolerance:** tol = max(1.0 pip, 0.25·ABR); on EURUSD about 1–2 pips. Volman's lines pass within 1–2 pips of the wicks they touch (p88–109 [m]). Touches may stop short of the edge or pierce it slightly (p16–45).

---

## 2. Object model (what may appear on the chart)

Every object has: `id`, `type`, `style`, `t_birth` (bar at which it became drawable), `t_left`, `t_right` (open or closed), geometry, `state`, `touches[]`, `events[]`, `role`, and `why` (a short machine-readable reason code).

**Edges are bands, not lines.** Render each edge as a thin band ±tol around its price. It is still stored as one price.

| Type | Style (casebook grammar [cb]) | Meaning |
|---|---|---|
| BOX | solid rectangle | Congestion block; the main object (in about 57% of casebook charts) |
| RANGE_OPEN | two horizontal lines, no vertical ends | A range still forming, typically Asia 00:00–08:00. It becomes a BOX once it completes or breaks |
| CONTEXT_RANGE | dotted rectangle | Wider range whose edges act as targets/obstacles. Smaller patterns inside it are drawn solid |
| PATTERN_LINE | solid diagonal | Flag edge, pullback line, M/W inner trigger line, neckline, squeeze edge |
| CONTEXT_LINE | fine-dotted diagonal, 3–8 h | Long lower-high / higher-low guide; not a setup boundary |
| LEVEL_CARRIED | long-dashed horizontal, projected right | Old block edge, dome zone or ceiling-test level: the future exit/obstacle/ceiling |
| MINI_LEVEL | short horizontal, 2–8 bars | Top/floor of a mini-congestion or squeeze (trigger line), or an M/W middle section |
| SQUEEZE | dashed ellipse | 2–8 small bars trapped between two walls |
| LABEL_TF | letter T or F beside the poking bar | Tease or false poke through an established edge |
| BRACKET | "—M—", "—W—", "—Mm—", "—Ww—", "—SHS—": horizontal span with a centred letter | Time span of a reversal formation's middle section, above the tops or below the lows. Not a price level |
| FALSE_EXT | short tick at the failed extreme | False high/low (bar-level definition, §3.9) |

**Never drawn:**
- 00/50 or 20-grid lines (they are context);
- Fibonacci or retracement lines;
- stop/target lines;
- parallel channels (none in 400+ charts);
- pattern names other than the brackets;
- objects inside unreadable chop, news spikes or clean trend legs. Emit a STAND_ASIDE tag instead.

---

## 3. Construction rules

Defaults are for EURUSD M5. The ABR form appears in brackets. Every threshold is a named parameter.

### 3.1 BOX — birth

A box is born by one of three routes.

- **(a) Pullback-end box (p51).** Take the current correction low L and the first swing high H after it. Once price turns down from H, the box [L, H] is drawable and extends right. Mirror this for highs.
- **(b) Range box (p59, p79).** A second top reaches the first within the double-top tolerance (about 2 pips, up to about 4 pips allowed [m]). The same holds for bottoms. The box is drawn at that moment.
- **(c) Session box (Asia).** From 00:00 CET, keep a RANGE_OPEN over the Asian drift. Convert it to a BOX at the first close outside plus follow-through, or at 08:00 if it is complete.
  - Asian boxes are 8–27 pips, median about 15 [cb].
  - A thin Asian range (≤ about 10 pips) is flagged false-break prone (9.40a).

A provisional box may be born with 1 touch per edge. The **breakout-side edge needs ≥ 2 touches** before any break is treated as meaningful. The non-breakout edge is secondary and may stay single-touch (p59, p156).

**Density over extremes (p217, Fig 5.5).** Edges sit on the cluster of highs/lows of the dense block, wicks included. Exclude an isolated spike wick that is:
- more than tol beyond the next-most-extreme bar, **and**
- a long tail (tail > 50% of its bar range).

Mark such a spike as FALSE_EXT.

**Size envelope** (flag anything outside it; do not draw it silently):

| Measure | Typical | Allowed |
|---|---|---|
| Height | 11–29 pips, median about 15–16 | 6–34 pips [cb] |
| Width | 18–36 bars | 9–100 bars (Asian boxes 60–100) |
| Height : length | about 1 : 3 (p156) | — |

### 3.2 BOX — maintenance

- **Freeze on confirmation.** Once confirmed (≥ 2 touches on the breakout edge), the edges do not move for pokes.
- **Pokes are events.** A bar that trades beyond an edge and closes back inside, or goes 1–3 pips past it, gets a LABEL_TF. It never widens the box (p76–77; about 20 T and 2 F in Jul–Aug alone [cb]).
  - Initial label: **T**.
  - Relabel to **F** when price closes back inside within 1–3 bars **and** moves ≥ ½ box height the other way.
  - Keep both labels in history. The same bar can be T in one panel and F later [cb 9.66b/c].
- **Re-anchor only on alignment (p79, 102).** Move an edge only when ≥ 2 later extremes line up (within tol) at a new level, i.e. a new double top/bottom. After a re-anchor, the old poke extremes are ignored. Record the adjustment as an event.
  - Casebook adjustments are rare and are called "uncertain" (9.97b, 9.117a).
- **Tighten before the break (optional, p52).** On the bar before the break, the breakout edge may snap to the latest touch high/low if that is within tol of the frozen edge. Record it.
- **Delete when it stops making sense (p89).** An edge broken back and forth with no resolution is deleted, and the chart is read another way. Record the reason.

### 3.3 BOX — break and after

- **Break = a close beyond the edge by ≥ tol.** A plain penetration is not a break (p88). A wick-only excursion is a poke (§3.2).
- **Classify the break by where the buildup sat (p24–27, 40 fn):**
  - **proper** — a buildup with one side resting on the edge;
  - **tease** — the buildup sat mid-range, away from the edge;
  - **false** — no buildup (price ran from far away straight through).
  - The class is set **at break time**, from structure only, never from the outcome.
- **Right edge.** Stays open while price is inside or near the box. It closes 6–18 bars (30–90 min) after the break, so that a retest or ceiling test still falls inside [cb].
- **Role reversal (p20, 81; 9.96b, 9.107c).** The broken edge is spawned as a LEVEL_CARRIED (dashed) on the other side of price.
- **Carry-over.** A broken box may be carried into the next window, cut down to its remaining part. A box can outlive a failed break (9.34a).
- **Nested box (p52; 9.6a, 9.14b).** A small box inside or next to the big one, at the breakout edge, marks the final tight squeeze. It is allowed as a second BOX with role=NESTED.

### 3.4 PATTERN_LINE (trendlines, flag and pullback lines, M/W trigger lines)

- **Slope rule (p49).**
  - A line that defines an upside break is horizontal or **falling**, through lower highs.
  - A line that defines a downside break is horizontal or **rising**, through higher lows.
  - A rising line never defines an upside break.
- **Anchoring (p88–109).**
  - First anchor: the extreme wick of the wave, i.e. the wave origin.
  - The line then runs along later touches. Fit for the **maximum number of touches within tol**.
  - Skip long-tail false extremes (Fig 5.5 #4). Lows a few pips above a refitted line are fine.
- **Size.**
  - Small lines of about 1 h (≈ 12 bars) are the useful trigger lines (p49).
  - Pattern boundaries may span several hours (p55–56).
- **Most common casebook trigger [cb].** An **M (or W) plus a short line through its 2–3 higher lows (lower highs)**. The PB trigger is a close through that line.
- **Pierce policy (p66).** A close through the line marks it PIERCED; the line is kept. Re-fit only when newer swings line up. Never re-fit on the first pierce.
- **Extension.** Extend 3–17 bars past the break (p88–110 [m]), or to the window edge for flag lines. Broken lines are kept because pullbacks come back to them: the PBP retest (p56, p111–123).
- **Last-touch refit (p61).** The most valuable line often becomes clear only at its last touch before the pierce. The engine may refit up to the last closed bar. Do this causally, and log the version.

### 3.5 CONTEXT_LINE and CONTEXT_RANGE

- **CONTEXT_LINE.** Anchor at the session extreme and fit through 2–4 swings over 3–8 h. Draw it dotted and project it forward, so that later TL-extension touches can be detected [cb 9.4a, 9.23a/b, 9.29a/b].
- **CONTEXT_RANGE.** A wide range (≈ 20–40 pips), such as the range around a 50 level. Its edges are targets/obstacles, not setup triggers [cb 9.11, 9.24].
- **Budget.** At most 1 of each per window.

### 3.6 LEVEL_CARRIED (exit / obstacle / ceiling-test levels)

**Sources:**
- a broken box edge (role reversal);
- a prior block edge, high or low, in the trade direction;
- the **dome zone**: the low→high span of the bar that made the prior top, about 8 pips thick. For a long, the two valid exit prices are the **underside of the prior top area** and the **tip of the prior high** (p169–170). Mirror for shorts;
- the ceiling-test level: after a break, the nearest inner small congestion beyond the broken edge, not just the edge itself (p40–42).

**Lifecycle.** Drawn dashed and projected right. **Consumed after one touch.** Once touched, it no longer counts as an obstacle or exit for the next trade (p170).

### 3.7 MINI_LEVEL, SQUEEZE, buildup

- **MINI_LEVEL.** A short horizontal (2–8 bars) at the trigger side of a tiny zigzag: its lows for a short, its highs for a long. The trade trigger is the break of that short line, not of the big edge alone (p19, 31, 37).
- **SQUEEZE (p57, 99).** At least 2 consecutive small bars (≥ 3 preferred), each with range ≤ 0.8·ABR.
  - They sit between two opposing walls: box edge or PATTERN_LINE vs EMA25, or vs a 00/50 level.
  - The gap must narrow. Examples go 7→4 pips and 15→3 pips [m].
  - The signal bar "fills the last gap". It may close **on** the line, not necessarily beyond it (p95).
  - Drawn as a dashed ellipse.
  - A squeeze that is short relative to the whole pattern is weak [cb 9.21a, 9.38a].
- **Buildup (p18–19, 89–90, 103).** Congestion of alternating bars within 1·ABR of the edge, with shrinking ranges. Nested is best (a small box inside a big one).
  - No fixed minimum: 1–2 bars at a pullback end, ≥ 4 bars for a pattern break.
  - Buildup should grow with pattern size.
  - Measure its **thickness in pips relative to the previous buildup** (p418–419).

### 3.8 Domes and M/W

- **Dome (p39, 101–110).** A rounded swing that rises from a level or line and falls back to it (mirror: a U hanging under resistance).
  - Record the height above/below the level for each dome in sequence.
  - Flag a **mostly shrinking** sequence, e.g. 22→13→15→8 or 30→25→18→10 pips [m].
  - The last, flattened dome is the focus: it is where the squeeze forms.
  - Domes are **never drawn**; they are stored as facts.
- **M/W.** Two tops (bottoms) within the double-top tolerance, 4–28 bars apart [cb].
  - The **middle section** (the dip between the tops / the peak between the lows) is a key level.
  - Its break is the reversal-exit trigger; the rule is "break of the bar that completes the middle" (p175–196).
  - Drawn only as a BRACKET, plus a MINI_LEVEL when used as a trigger.
  - Mm/Ww: the small m/w must be in harmony with the big M/W (p221–223, 258–260).
  - SHS: bracket over or under the whole formation.

### 3.9 Bar-level facts

- **Breakout bar (p28).** A bar trading beyond the previous bar's high (low).
- **False high (p28).** An up-break, then a bearish reply bar, then that reply bar is broken downward. Mirror for a false low. It is confirmed by the first opposite breakout bar (p29).
- **Strong/power bar (p73).** Large versus the average of neighbouring bars, opening at one end and closing strongly at the other.
- **Inside bar.** High ≤ previous high and low ≥ previous low; a slight protrusion is tolerated in a cluster (p79–81).
- **Doji.** Stored as a fact; it is not automatically a reversal bar (p66–67).

---

## 4. Derived facts the setup layer will read (computed, not drawn)

- **Dominant pressure (p21, 47, 101, 227).** Combine:
  - EMA25 slope, with **hysteresis**: slope-state changes need persistence, and "flattening" keeps the prior sign (p227);
  - EMA curvature;
  - structure: new highs and corrections holding above the last important low.
  - Output: UP / DOWN / NEUTRAL, plus a confidence value.
- **Round-number relations.**
  - magnet ahead: the next 00/50 in the trade direction, typically 12–30 pips away, often about 20;
  - counter-magnet behind: a 00/50, EMA25 or TL extension within about 10 pips on the stop side;
  - battle: a box straddling a round number with failures both ways;
  - failed-attempt counter per level (p94, 105).
- **Obstacles ahead** for either side: nearest LEVEL_CARRIED, box edge, double top, TL extension, dense congestion on the left. Graded minor / double / dense (p98). Report the distance in pips and apply the 14-pip room rule (p167).
- **Break class** (§3.3), **ceiling-test pending**, **dome sequence**, **squeeze present**, **T/F history** per edge.
- **STAND_ASIDE reasons:** chop (long bars), news window (14:30 / 16:00 CET), round-number battle, quiet session, or trend leg without structure.

---

## 5. Salience and budget

- At most **5 structural objects** in the 84-bar window; hard cap 8. Casebook median is about 3 [cb].
- **Priority:**
  1. the BOX containing or just left by price;
  2. the breakout-side edge and its PATTERN_LINE / MINI_LEVEL trigger;
  3. the nearest LEVEL_CARRIED ahead in each direction;
  4. one CONTEXT object.
- **Drop:**
  - an object that has left the window;
  - a level consumed by a touch;
  - a line that has been broken and retested;
  - a box whose break has been retested.
- **No object inside chop** (bars ≥ 2·ABR, overlapping chaotically) — emit STAND_ASIDE instead.

---

## 6. Validation protocol (how "good drawing" is proven)

### 6.1 BOOK golden set (the primary yardstick)

The casebook shows 132 consecutive EUR/USD sessions, **2012-03-01 → 2012-08-31**, 3 panels per day (396 panels). The author drew every object himself, and every session carries a date.

Build `golden/BOOK2012.jsonl` with one record per panel. Each record holds: date, CET window, and every author object (type, style, time span, prices), with a precision flag per coordinate.

Construction:
1. Parse the reading notes' figure catalogue (times ±10 min; prices ±5 pips eyeballed, ±1–2 pips where marked [meas]).
2. **Calibrate each panel.** Use the axis labels: hour ticks and the 00/50 gridline labels, about 2.8 px per pip and 10 px per bar on the 1200 px scans in `_private/pages/`.
3. Verify the calibration by aligning the scanned candles to real EURUSD M5 bars of that date. This also yields the CET offset of our feed and any feed difference.
4. Refine each object's coordinates by line detection near the catalogue position.
5. Emit an overlay PNG per panel: the engine's objects over **our own** rendering of the real bars, plus the golden objects. The Lead QA-checks a sample.

Split:
- **TUNE** = Mar–May 2012.
- **HOLD** = Jun–Aug 2012. HOLD is scored **once** with frozen parameters.

**Metrics** (per object type; a match needs the same type family):

| Type | Match criteria |
|---|---|
| BOX | time IoU ≥ 0.5 **and** both edges within ±3 pips (±6 if the golden coordinate is eyeballed) |
| PATTERN_LINE | endpoints within ±3 bars / ±3 pips, or same anchor swings |
| LEVEL_CARRIED, MINI_LEVEL | same level ±2 pips, overlapping span |
| LABEL_TF | same poking bar ±1 bar, same side |
| BRACKET | overlapping span, same letter family |

Also report:
- object count per panel versus golden (median, IQR);
- the clutter ratio (engine ÷ golden count);
- **edge stability**: how often a frozen edge moves per 100 bars. Target ≈ 0 except logged re-anchors.

**P-v1 acceptance gates (HOLD, one look):**

| Metric | Gate |
|---|---|
| BOX recall | ≥ 0.70 |
| BOX precision | ≥ 0.60 |
| PATTERN_LINE recall | ≥ 0.50 (Volman calls lines subjective, p50) |
| LEVEL_CARRIED recall | ≥ 0.60 |
| LABEL_TF agreement on matched boxes | ≥ 0.60 |
| Clutter ratio | median ≤ 1.5 |
| Edge stability | no unlogged edge move |

- If a gate is clearly mis-set, the lane may propose a revision **before** HOLD is scored, with evidence from TUNE only.

### 6.2 Theory fixtures (unit tests)

Build synthetic bar sequences that reproduce the geometry of the theory figures, one test per rule:
- false-break wick keeps the edge (Fig 3.8);
- re-anchor on a new double top (Fig 3.9);
- slope rule;
- pierce-and-keep (Fig 3.5);
- pullback-end box birth (Fig 3.1);
- squeeze between a line and EMA25 (Fig 5.1);
- shrinking domes (Fig 5.3/5.5);
- M middle-section trigger;
- T→F relabel;
- consumed exit level (Fig 6.1);
- the 14-pip room rule (p167);
- Asian RANGE_OPEN → BOX;
- a thin Asian range flagged;
- 20-grid switch;
- CET/DST conversion (both switch weeks).

### 6.3 Causality and determinism

- Prefix invariance: objects at t are identical when computed on bars[:t+1] alone.
- Future mutation: changing bars after t changes nothing at t.
- Warm-up handling.
- Byte-identical output across runs.

### 6.4 Visual QA on DESIGN (outcome-blind)

- 30 random DESIGN sessions (2016–2021, EURUSD, plus 5 each for GBPUSD, USDJPY and AUDUSD), rendered in the book grammar with **no trades and no outcomes**.
- The Lead reviews them against a checklist:
  - ≤ 5 objects;
  - no stacked zones;
  - edges on clusters, not spikes;
  - pokes labelled, never absorbed;
  - lines obey the slope rule;
  - nothing drawn in chop.
- The Owner gets 10 of them in a gallery.

---

## 7. Data wall — BOOK carve-out (Lead ruling, recorded in CHARTER_ADDENDUM_4)

- **BOOK window** = EURUSD M1/M5, **2012-02-13 00:00 → 2012-09-07 23:59 CET**: the casebook plus 2 weeks of warm-up on each side.
- **Allowed:** perception fidelity only. Load bars, compute the EMA, build objects, compare with golden labels.
- **Forbidden inside BOOK:** any trade simulation, PnL, outcome, MFE/MAE or setup screen.
- **Permanently excluded from CONFIRM-PRE (2010–2015).** Any future CONFIRM evaluation must mask this window. Rationale: the casebook shows the outcomes of these sessions, so they can never serve as a blind confirmation.
- **Access** goes only through a dedicated loader that asserts the symbol, the window and "no outcome functions imported". No other 2010–2015 bars may be read.

---

## 8. Architecture and deliverables

**Python reference: `PA_Pro/research/perception/`**
- `engine.py` — an incremental, causal `PerceptionEngine.step(bar) -> Snapshot` with a pure-function core.
- `objects.py` — dataclasses plus a JSON schema, `schema/perception_v1.json`.
- `render.py` — matplotlib renderer in the book's grammar: solid box, dotted context, long-dashed carried level, dashed-ellipse squeeze, T/F letters, M/W brackets, EMA25, and 00/50 as faint grid.
- `golden/` — the golden set: parser, calibrator, refiner, overlays, BOOK2012.jsonl.
- `eval.py` — the §6.1 metrics.
- `tests/` — §6.2 and §6.3.
- `PERCEPTION_LOG.md` (## SUMMARY) and `DECISIONS.md`.

**P-FREEZE.** Once §6 passes, freeze v1: hash the code and parameters into the ledger (kind `perception_freeze`).

**MQL5 port (EA lane, after P-FREEZE).** `mql5/PA_Perception.mqh` plus drawing in `PA_Visual.mqh` with the same grammar. Parity = the object set per bar matches Python within 1e-9 on prices and exactly on types/ids, on DESIGN sample weeks, ≥ 99.5% of bars.

**Setups consume only the Snapshot API.** Nothing reads raw zones directly any more.
