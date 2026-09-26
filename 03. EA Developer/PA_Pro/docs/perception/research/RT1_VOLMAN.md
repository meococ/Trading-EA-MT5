# RT1 — Volman's craft, beyond our reading notes

Research sub-task RT1 for the PA-PRO perception lane. Question: how does Bob
Volman decide what to draw on a EUR/USD M5 chart, how does he define his
objects and trade conditions, and what must our engine reproduce so its output
looks like his sparse canvas instead of zone soup?

## 1. Scope, method, and what was verified

**In scope.** Volman's drawing/ignoring logic, operational definitions
(box/barrier, buildup, false/tease/proper break, pullback and pullback
reversal, pressure, the 14-pip room rule, EMA25, round numbers), his
no-trade conditions, and his drawing discipline (object counts, re-anchoring,
extensions, lines vs zones). Everything is assessed for use in a causal,
closed-M5-bar engine.

**Verified.** (a) The official free excerpt texts already in the repo
(`fpas_excerpts.txt` / `upa_excerpts.txt`, read via UTF-8 conversions), which
the publisher released as promotional PDFs — these are primary material.
(b) The project's own reading notes (`notes_01`–`notes_12`, Vietnamese
edition of *Understanding Price Action*) and `VOLMAN_PERCEPTION_SPEC_v1.md`.
(c) Six pages of the Trade2Win "Bob Volman price action scalping" thread,
one Trade2Win precursor thread, one Elite Trader thread, three review pages —
all fetched and read. (d) Search-result material that could not be fetched is
listed separately in §8 and never presented as verified.

**Not verified / does not exist.** No genuine interview with Volman was found
in any form. The publisher's own note (Google Books listing for FPAS, fetched)
warns that YouTube videos claiming author affiliation are fake. Volman's
"Response from Bob" answers on Trade2Win are relayed by members, not posted
by him. His emailed weekly charts (sent 2012 to ~2014+, per Trade2Win and
Elite Trader testimony) are not publicly archived — the Dropbox links are
dead — so forum descriptions of them are second-hand.

**Grades used below.** `EVIDENCE` = empirical claim with named data, method,
sample, result. `PRACTITIONER` = a named trader's rule or observation,
untested. `FOLKLORE` = repeated claim with no source or test. Volman's own
book rules are `PRACTITIONER` unless a measurement is given; the project's
casebook measurements can be `EVIDENCE` when sample and method are stated.

## 2. Sources

| # | Source | Type | URL | Usefulness | Reliability |
|---|--------|------|-----|------------|-------------|
| S1 | Volman, *Forex Price Action Scalping*, Light Tower Publishing, 2011 — official free excerpts (chs. 10–14 incl. "The Box Break", "False, Tease and Proper Breaks", "Range Break", "Trade Breakdown") | Primary (author) | local: `…/rt1_author_excerpts/fpas_excerpts.txt` (publisher promo PDF) | Highest: author's own words on boxes, buildup, break taxonomy | High; excerpt subset of the book, not the whole text |
| S2 | Volman, *Understanding Price Action*, Light Tower Publishing, 2014 — official free excerpts (theory chapters: pressure, S/R, break types, pullback reversal, pattern breaks, round numbers; low-volatility chapter) | Primary (author) | local: `…/rt1_author_excerpts/upa_excerpts.txt` | Highest: EMA25 role, pullback-end box birth, edge-adjustment rule | High; same caveat |
| S3 | Project reading notes, `notes_01`–`notes_12` (VN edition of UPA) | Second-hand (analyst notes on the book + figure-level catalogue) | local repo | Very high: per-figure object lists, measured object counts, skip annotations | Good; paraphrase of a translation, times ±5 min, prices ±1–2 pips |
| S4 | `VOLMAN_PERCEPTION_SPEC_v1.md` | Internal binding spec | local repo | Baseline to compare against | Internal authority |
| S5 | Trade2Win thread "Bob Volman price action scalping" (153716), pages 40, 48, 129, 130, 132, 148 | Second-hand practitioner forum + relayed author Q&A | https://www.trade2win.com/threads/bob-volman-price-action-scalping.153716/page-40 (and /48, /129, /130, /132, /148) | High: how serious readers applied/adapted the method; what "Bob" confirmed via relay; weekly-chart descriptions | Medium: paraphrases, self-reported results unverifiable |
| S6 | Trade2Win "Eurusd" precursor thread (150178), p.1 | Second-hand forum | https://www.trade2win.com/threads/eurusd-19.150178/ | Low-moderate: community context | Medium |
| S7 | DaytradingBias review of UPA | Second-hand review | https://www.daytradingbias.com/understanding-price-action-practical-analysis-of-the-5-minute-time-frame-by-bob-volman/ | Moderate: confirms EMA25, 1:2 bracket, reviewer's "no full justification for skips" observation | Medium: opinion |
| S8 | Elite Trader thread on FPAS | Second-hand forum | fetched earlier (elitetrader.com) | Moderate: practitioner's 10-pip-stop practice; note that weekly emails ran to ~2018 | Medium |
| S9 | Google Books FPAS listing (publisher's note) | Publisher metadata | https://books.google.com/books/about/Forex_Price_Action_Scalping.html?id=1xObtgAACAAJ | Confirms publisher, ISBN, author bio, fake-video warning | High for metadata |
| S10 | Amazon customer review quoted on Trade2Win p.1–2 (fetched within thread page) | Third-hand quote | (via S5 page-1/2 fetch) | One line: skepticism that fixed-stop rules transfer | Low-medium |

Snippet-only and failed-fetch sources are itemised in §8 and are not used for
any graded claim below.

## 3. Q1 — How Volman decides what to draw and what to ignore

**The drawn set is a working hypothesis, not a map.** Across the casebook
the author draws only objects that carry a *current* technical role:
something that bounds live congestion, arms a breakout trigger, preserves a
broken level for a retest, exposes a squeeze, marks a false break, or names
the nearest obstacle. Everything else — however "real" it looks — is ignored.
`PRACTITIONER` (S2/S3, throughout).

**Measured load.** Our own catalogue of the UPA Part-2 casebook block
(ch. 9, 46 sessions × 3 panels = 138 annotated charts, March–August 2012
EUR/USD M5) gives: mean ≈ 3 author-drawn objects per panel, typical 2–5,
max ≈ 9; only 3 of 138 panels carry no author object; boxes/congestion
rectangles appear in ~57% of panels; horizontal and diagonal lines ~30%;
T/F labels frequent; dashed ellipses rare. `EVIDENCE` — project measurement,
method: per-figure inventory in `notes_10` (sample 138 charts). Consistent
with the spec's target of ~3 objects and 0–8 range.

**What earns an object (criteria, all `PRACTITIONER` from S1/S2/S3):**

1. **Containment now.** A box is wrapped around active congestion the moment
   it exists — the official UPA excerpt describes boxing a pullback the
   instant price edges down from the pullback's first high, and extending the
   box rightward. Boxes also appear at the chart's right edge mid-formation
   (notes_10).
2. **Trigger armament.** Short horizontal "signal lines" over small buildup
   sections; flag/pattern trendlines; the FPAS excerpt states the minimal
   useful drawing is the signal line itself — the box is a teaching aid, and
   a horizontal line across tops plus one under lows "will do just fine"
   (paraphrase, FPAS ch.10).
3. **Last structure before the move.** Carried/ceiling levels: a broken
   barrier extended as a dashed line, kept because a retest ("ceiling test",
   role reversal) is expected; most reliable when it sits immediately left of
   the pullback (UPA p.215 via notes_07).
4. **Named obstacles.** Before entry the obstacles are enumerated as specific
   bar extremes — "top of 5", "low of 2", the 50-level — even when no line is
   drawn for them; drawings are selective, "only the lines needed for the
   trades being discussed" (notes_06, p.169 observation).
5. **Event labels.** T (tease) and F (false) letters on pokes; arrows and
   skip/optional annotations in the casebook.

**What he ignores (`PRACTITIONER`):**

- Isolated minor swings inside a trend; most bars are never numbered
  (notes_07 figure catalogue).
- Spike wicks for anchors: a pullback trendline is drawn *ignoring* a bar's
  tail (Fig 7.6, p.220); a spike low is left *outside* the box to show the
  block's dense character — "density over extremes" (Fig 7.6, p.217).
- Stale structure: levels behind price are dropped unless they are the next
  obstacle or a carried retest level. Context beyond ~one session day is
  not drawn; the FPAS excerpt says about an hour and a half of 70-tick
  action "usually does" for the overall picture, and UPA's panels show
  ~6–7 h (72–90 bars) per window (notes_10).
- Round numbers as *drawn objects*: the 00/50 gridlines are the platform's
  own dash-dot grid (notes_07, notes_10); the FPAS excerpt says thin 20-level
  guides may be plotted but never as absolute levels.
- Interior detail: false highs/lows inside a box are "small parts of the
  whole" — judged quickly, not always drawn (p.226).
- The EMA itself is never annotated; it is context, only ever mentioned in
  callouts (notes_10).

**Second-hand corroboration.** Trade2Win members who received the author's
emailed weekly charts (from ~week 38/2012) report they look like the book's
charts — same sparse grammar (member "BLS", S5 p.129/132). One practitioner
("samich1262", S5 p.40) observed Volman trading very clear bear flags with
only a trendline drawn — i.e., the author's real charts are slightly more
flexible than the book's rigid setup list. Both are `PRACTITIONER`-grade
second-hand observations, and the second is a genuine *contradiction* worth
keeping (see §7).

**Distance/recency filter.** Objects outside the visible price corridor are
almost never drawn; an obstacle must be *on the path* to matter. Room is
checked forward (14-pip rule, §4) and obstacles backward (levels "on the
left"). The result: recency + proximity + active role ≈ 3 objects.

## 4. Q2 — Operational definitions

All definitions below are `PRACTITIONER` (author's rules via S1/S2/S3) unless
marked otherwise. Page numbers are the VN-edition book pages recorded in the
reading notes; excerpt chapters are as printed in the official PDFs.

**Box / congestion.** A rectangle around sideways price action, drawn the
moment the sideways phase exists; its edges are touch clusters. FPAS ch.10's
canonical example: repeated equal highs, rising bottoms, tension against the
barrier, EMA guiding price toward it. Edges may be set by the extremes of a
single pullback (p.209). A slightly pierced edge does not disqualify the
barrier — only a severe violation does (UPA excerpt). Height seen in ch.7
examples: ~13–24 pips; length 10–26 bars (`EVIDENCE`-lite: notes_07
section D measurements from the printed charts).

**Barrier / edge.** A horizontal line through 1–3 touches. Important caveat
for our spec: obstacles and exit levels are often *single-bar* extremes
("top of 5", "the high of 7") — a strict ≥2-touch rule would miss obstacles
Volman actually uses (notes_06 finding #6). Touch tolerance is visual; the
spec's `max(1 pip, 0.25·ABR)` is an internal convention, not a book number.

**Buildup.** A few small, often shrinking bars parked at the barrier before
the break. One inside bar can suffice at an important location; for a Ww
squeeze "at least four bars" is offered as a helpful but explicitly
non-rigid guide (p.223). Buildup is *required* for a tradable barrier break;
a pullback reversal may rest on a single reversal bar instead (notes_02).
Two tease causes only (p.222): the break starts too deep inside the pattern,
or it starts at the barrier with buildup too thin.

**Squeeze (*cú nén*).** Bars trapped between a pattern boundary and EMA25
(or another opposing boundary) with no room left — they must exit one way
(p.204, p.208). Drawn as a dashed ellipse only when it completes a setup;
it is an annotation, not a structure line.

**False break.** A break that comes "straight from the other side" of the
range with no buildup (FPAS ch.11 taxonomy, official excerpt); on bars: a
penetration then a rapid close back inside. In the casebook a false-break
sequence can span several bars; the T/F letter marks the poke.

**Tease break.** A break that originates mid-range or off the average
without a proper squeeze at the barrier (FPAS ch.11); equivalently thin
buildup (p.222). Tease and false overlap: UPA examples label one event with
both ideas — an early break *and* a trap. Treat as overlapping labels or a
primary class plus causal attributes, not exclusive bins.

**Proper break.** Buildup positioned at the boundary, usually with
confluence: pressure direction, EMA25 nearby, a round number behind the
move, a pattern edge. Hard to distinguish from a tease in real time —
"proper and tease breaks can be very hard to tell apart" (p.223); the
engine should grade, not binarise.

**Pullback.** A correction that moves diagonally, gently, orderly, with few
strong counter-bars (p.210). Typical depth 40–60% of the prior wave, often
landing on EMA25 (40–60% zone named in the FF notes thread, snippet-only;
50%, 50–60%, ~60% retracements appear on pp.200–218). Invalid when
near-vertical, too strong, too shallow, or partly inside the box with strong
counter-bars (pp.210–226).

**Pullback reversal / TFF.** At the average, the first strong reversal bar in
the dominant direction can complete the setup (pp.201, 218). The
**barrier-reclaim rule** is the key perception test: after a failed
down-break, the buy signal bar's high must be at or above the reclaimed
barrier — never buy while the reversal bar's high is still below it (p.201;
the mirror for shorts, p.218). Best at the *first* retest of the average
since the dominant wave began (p.218).

**Pressure.** Which side dominates: EMA25 slope is "the main tool nearly all
the time" (p.200); supplemented by which side of the average bars
consistently trade on, and HH/HL structure. A flattening average still counts
as directional — the state flips only when the average has really turned or
bars persist on the other side (Fig 7.9, ~50 min of drift above a flat EMA
inside a bearish box; the up-break was still the trap). This demands
**hysteresis** in our slope state.

**The 14-pip room rule.** Standard bracket 20-pip target / 10-pip stop
(presented as "only a suggestion", pp.155, 161). Minimum acceptable room to
the first real obstacle is **14 pips**; below that, *skip the trade*
(p.167). ~13 pips is accepted occasionally; ~10 pips means the trade should
never have been taken (pp.170–171). When the first obstacle sits at 14–20
pips, exit at the obstacle, not the 20. Obstacles are named before entry as
specific extremes; a touched level is "used up". This directly contradicts a
2R-style room gate — flagged in §7.

**EMA25.** The only indicator. Explicitly *not* support/resistance by itself
— "an average whose location often coincides" with pullbacks and technical
support (UPA excerpt, paraphrased). Roles: pressure gauge (slope), magnet/
counter-magnet (a nearby EMA on the stop side vetoes), squeeze boundary,
first-retest reference for TFF. FPAS used a 20EMA on 70-tick charts; UPA
uses 25 on M5 — same role, period scaled to the frame.

**Round numbers.** Context gridlines, not hand-drawn structure. Normal M5
grid: 00 and 50 (the platform draws them; notes_07 confirms the dash-dot
gridlines are not author objects). Low-volatility adaptation: the 20-grid
00/20/40/60/80 (UPA ch.11; notes_12). EUR/USD action clusters in ~20-pip
increments; the 40/60 pair acts as a "mishmash" around the 50 (FPAS
excerpt). A round number ~15 pips ahead is a magnet that tempts entries
(pp.201, 205); ~7 pips away on the stop side is a counter-magnet (p.220);
a 50-level already broken shortly before is a skip reason (p.202). Proximity
alone never justifies drawing or trading.

## 5. Q3 — No-trade / stand-aside conditions

From the book (via notes/excerpts) and practitioner testimony — all
`PRACTITIONER` unless noted:

1. **News.** Do not trade major announcements: accelerated bars, evaporating
   levels, spikes, slippage (news slippage >10 pips vs a few pipettes
   normally, p.165), spread expansion. Practitioners report Volman skipped
   NFP days entirely (S5, second-hand).
2. **Session lulls (CET, as printed on the axes).** Hour before the Asian
   open very quiet; EU midday lull 12:00–14:00 usually quiet and poor for
   continuation after a strong morning; US midday lull 18:00–20:00. The
   09:00–10:00 UK hour is "very unpredictable" — caution, not a ban. Breaks
   right at quiet session opens are deliberately ignored in the
   low-volatility chapter (notes_12). *Reconciliation:* the UPA excerpt's
   "12:00–14:00" and the casebook's later US-lunch window are CET-axis
   labels from different halves of the day, not a contradiction.
3. **Insufficient room.** <14 pips to the first obstacle → skip (§4). Forum
   example: a setup with only ~5 pips to blocky resistance skipped; "weak
   pressure and insufficient room cause skips" (S5 p.40, second-hand).
4. **Mid-grid ambiguity.** Setups "dead in the middle of two 20-levels" need
   extra clarity (S5 p.48, second-hand).
5. **Chop / barbwire.** Overlapping directionless ranges; doji clusters;
   awkward congestion — no edge. "Nine times out of ten the situation can be
   judged in a blink; if you have to search for a trade it probably isn't
   there" (p.225).
6. **The EMA-direction ban.** While EMA25 still has a direction — even
   slowly flattening — every trade against that direction is disallowed
   (p.227). Exception: a break out of a *long, drawn-out* pullback may be
   traded against the average's current direction, because a long
   correction can itself turn the average.
7. **Volatility regime.** Most bars oversized (frantic action) → skip;
   widen the bracket only if abnormal volatility persists across sessions
   (p.211). Thin one-pip bars and dead sessions → unsuitable for
   continuation scalps (notes_12). Abnormally long signal bars unusable;
   too-small signal bars invalid (pp.211, 228).
8. **Continuation at range extremes / post-turn.** A counter-break at the
   range edge is information or an exit signal, not an entry; after a
   trend turn, continuation attempts need a proven new pressure regime.
9. **Counter-magnets.** Round number or EMA just behind entry on the stop
   side; entry far from the average; a 50-level freshly broken (p.202).
10. **Cost precondition.** FPAS assumes total round-trip cost ≲1 pip
    (spread+commission); an era-specific gate our backtest must check rather
    than inherit (from FPAS accounting chapters and reader notes —
    snippet-flagged, see §8).

The casebook marks skips roughly as often as entries (notes_07 arrows lists:
several panels carry all-skip arrows) — stand-aside is a first-class output,
not a default. `EVIDENCE` (project measurement, same 138-chart sample).

## 6. Q4 — Drawing discipline

- **Budget.** ≈3 objects per panel (mean 3.0, max ≈9; §3 measurement). The
  spec's ~3 target is consistent.
- **Birth.** Boxes appear the moment congestion/pullback exists — even at
  the chart's right edge; provisional edges are drawn, then confirmed by
  further touches (notes_10 lifecycle; official excerpt on wrapping the box
  at the pullback's first high).
- **Edge fixity vs re-anchoring — the real rule is two-sided.** A poke does
  *not* move an edge: "they usually do not qualify … only when severely
  violated" (UPA excerpt) — T/F pokes are events, not new anchors. *But* a
  pre-break tighten is explicitly allowed: the author "adjusted the top
  barrier a little to match the high of bar 13" (UPA excerpt) and re-drew a
  lower barrier through new lows 13–15 after they formed (p.223). The
  discipline: **edges are immutable to pokes, adjustable to a confirmed new
  alignment before the break.** The spec's "fixed once set" is half of this;
  §7 flags it.
- **Forward extension.** Broken barriers extend rightward as dashed lines
  and keep acting (ceiling tests on extensions, trendline-extension support;
  pp.206, 210–211). Extensions die when consumed or when they leave the
  window.
- **Lines, not zones.** All barriers are exact lines through touches; the
  only zone-like marks are the rare dashed ellipse (squeeze) and the
  platform's round-number grid. Practitioner confirmation: "only horizontal
  trendlines" on the weekly charts (S5, second-hand).
- **Selectivity.** Obstacles are often named in text but *not* drawn
  (notes_06, p.169) — the drawn set is a subset of the considered set.
- **Minimal form.** In live trading the signal line alone suffices; the box
  is didactic (FPAS ch.10, paraphrased).

## 7. Agreements / contradictions / gaps

| Topic | Outside sources | Reading notes (UPA, VN ed.) | Spec v1 | Verdict |
|---|---|---|---|---|
| Object count/panel | Weekly charts "look like the book's" — sparse (S5, 2nd-hand) | Mean ≈3, max ≈9, measured 138 charts | ~3 typical, 0–8 | **Agree** |
| Box dominance | Boxes described as teaching aid; signal line is the minimal object (S1) | Boxes in ~57% of panels | Boxes primary object | **Agree**; note the box-as-aid nuance |
| Edge fixity | Weekly-chart grammar unchanged (S5) | Both: poke ≠ move; pre-break tighten allowed (p.223, excerpt) | "Edges fixed once set" | **Contradiction (partial)** — spec must allow versioned pre-break re-anchor |
| Tease vs false | FPAS ch.11 separates them by break origin (S1) | One event can be both; overlap common | Separate classes | **Contradiction** — allow overlapping labels / primary+attributes |
| EMA period | FPAS 20EMA on 70-tick (S1); practitioners carried 20EMA habits to M5 (S5) | EMA25 on M5 | EMA25 | **Agree for M5**; flag frame-dependence |
| EMA as S/R | Forums treat EMA proximity as filter (S5 p.48) | "Never provides S/R by itself" (S2) | Pressure gauge only | **Agree** |
| Context window | FPAS: ~1.5 h of 70-tick for the picture (S1) | Panels ~6–7 h / 72–90 bars | ~84 bars / 7 h | **Agree in spirit**; bar-count differs by frame — keep spec's 84 |
| Room rule | Practitioner skips with ~5 pips to resistance (S5 p.40) | 14-pip minimum; <14 skip; 13 soft; ≤10 never (p.167–171) | Room gate unspecified/2R elsewhere in RULEBOOK | **Contradiction** — adopt 14-pip gate, exit at obstacle when 14–20 |
| Round numbers | FF notes: 00/50, magnets (snippet-only) | Gridlines, never drawn; 20-grid in low-vol | Same | **Agree** |
| News | Practitioners skip NFP (S5) | Slippage/spread/ban | Stand-aside | **Agree** |
| Lunch windows | Reviews repeat "avoid lunch" (S7) | EU 12–14, US 18–20 CET; UK hour caution | CET session marks | **Agree**; two different lulls, don't merge |
| Flag-only entries | Volman traded flags with just a trendline (S5 p.40, 2nd-hand) | Book demands buildup/pattern context | Setups list | **Contradiction (soft)** — author's live flexibility > book rigidity |
| Dotted vs solid | — | notes_11: book gives no rule for dotted | Spec assigns "context range" | **Gap** — spec convention exceeds evidence; mark as convention |
| Drawn vs considered | Reviews complain skips lack full justification (S7) | Obstacles named but undrawn | Draw only emitted objects | **Gap** — need salience ranking to pick the drawn subset; no author rule exists |
| Numeric thresholds | Forums supply ad-hoc numbers (EMA distance flexible, S5 p.48) | Book deliberately non-numeric ("bars will guide the way") | Some fixed numbers | **Gap** — list of must-measure parameters in §9 |
| Fixed stops mechanical? | Amazon reviewer doubts transfer (S10); EliteTrader member used flat 10 | Bracket "only a suggestion" | — | **Contradiction (external)** — treat bracket as default, not law |
| "Author trades his own method" | Minions Labs hostile review claims he doesn't (fetched earlier); Personal-reviews blog alleges stooge posting (fetched earlier) | — | — | **FOLKLORE/hostile** — note as dissent, no effect on geometry |

## 8. Limitations

- **No interview corpus exists.** The publisher itself warns that YouTube
  videos claiming author affiliation are fake (S9). Every "author said"
  outside the books is forum-relayed ("Response from Bob" via members) or
  the emailed weekly charts — which are not publicly archived and were
  verified only through participant testimony (S5, S8).
- **`[SNIPPET-ONLY, NOT FETCHED]` items** (search results seen, pages never
  retrieved — no claim above relies on them beyond the flagged lines):
  - EarnForex FPAS review — https://www.earnforex.com/guides/book-review-forex-price-action-scalping/ (fetch failed);
  - ForexFactory "Volman-style 70 tick chart" — https://www.forexfactory.com/thread/578183-volman-style-70-tick-chart (fetch failed);
  - ForexFactory "Dissent Channel" thread (practitioner adaptation of UPA) — fetch failed;
  - ForexFactory UPA study-notes thread (member nicksergeant's compiled notes; supplied the 40–60% pullback-zone wording used once above) — fetch failed;
  - "Notes On BOB VOLMAN" digest hosted on PDFCoffee — HTTP 503; the host is
    a questionable document-sharing site and nothing was retained;
  - tertulia.com.au UPA listing; Scribd/Quizlet derivative notes — rejected
    as low-reliability or copyright-questionable hosts, not cited;
  - BooksWithCloud "UPA pdf" result — ignored entirely (likely infringing
    copy; per rules, no pirated sources).
- **Translation layer.** Reading notes are from the Vietnamese edition;
  quoted phrases are re-translations, page numbers track the VN printing.
  Quotes here are paraphrases; the few near-quotes are ≤15 words.
- **Era specificity.** All primary material is EUR/USD 2010–2012: ~1-pip
  spreads, 4–7-pip typical M5 ranges, 20-pip grid salience. Parameter values
  must be re-validated on current data.
- **Measurement scope.** The ~3-objects mean and 57% box figure come from
  our ch.9 catalogue (138 charts); the spec cites a 132-session/396-panel
  casebook for the whole Part 2 — different samples, same order of
  magnitude.
- **Hostile second-hand items** (Minions Labs, personal-reviews blog) are
  opinions, not evidence; they matter only as reminders that the method's
  discreteness is contested.
- The FPAS 10-pip-stop practice is attested by practitioners (S8/S5); the
  book itself uses a 10-target with managed/tipping-point exits — a
  distinction the engine should keep.

## 9. What this means for our engine

All primitives are causal on closed M5 bars at time *t*. Units: pips, ABR
multiples (ABR = mean high−low of last 50 closed bars, spec), bars, CET
minutes. Provenance tagged: **[book p.X]**, **[excerpt]**, **[casebook]**,
**[spec]**, **[measure]** (Volman gives no number — estimate from casebook).

1. **Canvas window** — objects may be born only from the last `W=84` bars,
   hard cap one session-day. **[spec; book ~6–7 h panels, notes_10]**
2. **Candidate edge** — cluster of swing extremes within
   `tol = max(1 pip, 0.25·ABR)`; provisional at 1 touch, confirmed at ≥2;
   obstacles for the room check may be single extremes. **[spec; notes_06]**
3. **Poke event vs edge move** — a bar whose extreme crosses an edge while
   the close stays inside records a `poke(depth_pips)` event; the edge never
   moves on a poke. Only a confirmed *new alignment* (≥2 newer touches at a
   shifted price, before any proper break) may re-anchor, as a versioned
   edge. **[excerpt: "severely violated" clause + bar-13 adjustment; p.223]**
4. **Box lifecycle** — born at pullback end (first counter-extreme after the
   pullback extreme), provisional → confirmed on second touch of each side;
   right edge open; density-over-extremes option: a lone spike may sit
   outside when the block is dense. **[excerpt; p.217]**
5. **Buildup detector** — of the `k` bars (`k∈[1,6]`, **[measure]**) before
   the break bar: median range `≤ θ·ABR` (`θ≈0.5` **[measure]**), located
   within `tol` of the edge, shrinking-range bonus; a single inside bar may
   count at a high-salience edge; Ww squeezes use `k≥4` as soft guide.
   **[p.222–223; measure]**
6. **Squeeze** — opposing boundaries (pattern line vs EMA25 or edge vs edge)
   with gap `< s` pips (`s` **[measure]**, casebook typical ~2–6); emit the
   ellipse only when it completes a setup. **[pp.204, 208; measure]**
7. **Pressure state** — EMA25 slope sign over `m` bars with hysteresis:
   flattening stays directional until the average turns or bars persist on
   the other side `≥ p` bars (`p≈10` seed from Fig 7.9's ~50-min drift,
   **[measure]**); plus side-of-EMA occupancy and HH/HL. **[p.200; Fig 7.9]**
8. **EMA-direction ban** — while `pressure ≠ flat`, veto entries against it;
   exception when pullback age `≥ a` bars (`a` **[measure]**) — a long
   correction may turn the average. **[p.227]**
9. **False-high / false-low** — poke beyond a prior swing extreme by `≤ tol`
   with close back inside within `f` bars (`f∈[1,5]` **[measure]**); label
   `T/F`, never re-anchor. **[excerpt; casebook]**
10. **Break classifier** — inputs: buildup flag, break-origin depth
    (opposite-edge / mid / at-edge), close-back speed, squeeze presence,
    confluence (pressure direction, EMA side, gridline proximity). Output a
    *primary* label {tease, false, proper} plus attribute flags allowing
    tease∧false overlap; emit graded confidence, not binary. **[FPAS ch.11;
    p.222–223]**
11. **Barrier-reclaim (TFF)** — after a failed counter-break, the signal
    bar's relevant extreme must be back across the barrier (high ≥ barrier
    for the buy mirror); else veto. Prefer first EMA retest of the wave.
    **[pp.201, 218]**
12. **Carried level** — broken edge persists as a forward dashed line until
    consumed (close beyond by `> tol` without retest) or it exits `W`;
    salience bonus when immediately left of a pullback. **[pp.206, 210, 215]**
13. **Room check** — `room = dist(entry → nearest of {confirmed edges,
    carried levels, gridline ± tol})`; veto if `room < 14` pips; soft floor
    13; hard floor 10; if 14 ≤ room < 20, exit target = obstacle.
    **[pp.167–171]** — replaces any 2R gate.
14. **Round-number grid** — context only: 00/50 normal; switch to the
    20-grid when `ABR < γ` (`γ` **[measure]**, low-vol regime ~3–4-pip ABR);
    gridlines never emitted as structure objects; magnet flag if obstacle
    side gridline within ~15 pips, counter-magnet if within ~7 pips on the
    stop side. **[excerpt; pp.201, 205, 220; notes_12]**
15. **Session filters (CET)** — quiet pre-Asia hour; EU lull 12:00–14:00
    (poor for continuation); US lull 18:00–20:00; UK first hour 09:00–10:00
    caution flag; suppress break signals in the first `o` minutes of a quiet
    session (`o` **[measure]**). **[pp.202–221; notes_12]**
16. **News veto** — block `±N` min around scheduled major releases
    (`N≈30` seed **[measure]**); hard veto when bar ranges spike `> ξ·ABR`
    (`ξ≈2`) with spread expansion. **[pp.165, 211]**
17. **Volatility regime** — if `> τ` fraction of last `W` bars have range
    `> 2·ABR`, stand aside (`τ` **[measure]**); if median range `< ρ` pips
    (one-pip-bar regime, `ρ` **[measure]**), dead-session veto. **[p.211;
    notes_12]**
18. **Counter-magnet veto** — entry farther than `d` pips from EMA25, or a
    round number/edge on the stop side within ~7 pips → flag/skip
    (`d` **[measure]**, casebook suggests ~10–15). **[pp.202, 204, 212, 220]**
19. **Object budget & salience** — score candidates: touch count, recency,
    distance to price, role (containing > trigger > obstacle > context),
    EMA involvement; emit top ~3, hard max 8; T/F letters and skip/optional
    annotations do not consume budget. **[casebook mean 3.0 / max 9; spec]**
20. **Pattern brackets** — M/W via 3–5 alternating pivots; SHS via
    head>shoulders triple; Ww/Mm = W/M plus squeeze against its top;
    harmony check via flag:pole height & duration ratio within bounds
    (**[measure]**); emit as bracket objects only when they inform the
    current decision. **[pp.204–226; notes_09]**
21. **Stand-aside output** — a first-class verdict with a reason code
    {news, lull, room<14, ema-ban, barbwire, dead-vol, frantic-vol,
    counter-magnet, mid-grid-ambiguous}; the casebook marks skips at
    roughly entry frequency — the engine should be comparably quiet.
    **[throughout; casebook]**

**Thresholds Volman never supplies — must be measured from the casebook,
not invented:** buildup thinness (`θ`, `k`), tease depth and close-back
speed (`f`), squeeze gap (`s`), EMA-distance veto (`d`), hysteresis windows
(`m`, `p`), pullback-age exception (`a`), low-vol grid switch (`γ`), regime
fractions (`τ`, `ρ`), quiet-open suppression (`o`), news blackout (`N`).
Until measured, seed with the stated casebook-typical values and mark each
`[measure]` parameter uncalibrated.

— End of RT1 —
