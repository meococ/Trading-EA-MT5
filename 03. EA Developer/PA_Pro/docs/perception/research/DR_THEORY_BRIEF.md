# DR-THEORY BRIEF — deep research for the Perception engine

- **Issued:** Lead, 2026-09-21 08:15Z.
- **Executed by:** the PERCEPTION lane's own sub-agents (LEAD_RULINGS Ruling 2 §2.3).
- **Output folder:** `docs/perception/research/`.

## Why
The engine must see a EUR/USD M5 chart the way a professional price-action trader does. A pro does not "find pivots". He reads:
- **where the resting orders are:** stops beyond equal highs, breakout entries at a box edge;
- **who is trapped** after a false break, and where they must get out;
- **where the opposition has gone:** a buildup against a barrier with shrinking pullbacks;
- **which structure matters now** and which is history.

We need that model explicit, sourced and testable, so that every perception rule has a reason.

## Rules for every research sub-agent
1. **Tools and sources.**
   - Use web_search and webfetch (the browser if needed).
   - Primary sources first: journal pages, SSRN, NBER, Fed/ECB/BIS working papers, authors' own sites, interviews.
   - For books: publisher pages, author talks, reputable reviews.
   - **Never** use shadow libraries or pirated PDFs.
2. **Citations.** Cite every factual claim: author, year, title, venue, URL. Fetch the page; never cite from memory.
3. **Grade every claim:**
   - **EVIDENCE** — empirical: data, method, sample, result;
   - **PRACTITIONER** — a named trader's rule or observation, untested;
   - **FOLKLORE** — widely repeated, with no source or test.
4. **Quotes.** Paraphrase; quotes ≤ 15 words, and few of them.
5. **For every concept,** give:
   - the mechanism;
   - an operational definition on bars only, causal (uses bars ≤ t);
   - the evidence grade;
   - the primitive(s) it implies;
   - how to test it on DESIGN bars, and which result would falsify it.
6. **Be critical.** For each claim, say how it could be wrong, whether it is era- or market-specific (pre-2008 FX, futures vs spot FX), and whether it applies to EURUSD M5.
7. **Output.** One markdown file at the given path, ≤ ~6,000 words, ending with **"What this means for our engine"**: concrete primitives with definitions and parameters.

## Sub-agents
Dispatch RT1–RT4 in parallel, in the background.

### RT1 — Volman's craft, beyond our reading notes
**Questions:**
- How does Volman decide what to draw and what to ignore?
- How does he define the box/barrier, buildup, false break, pullback, tease, pressure, the 14-pip room rule and the EMA's role?
- What are his no-trade conditions?

**Sources:**
- his interviews, forum posts and talks;
- the publisher pages for *Forex Price Action Scalping* (2011) and *Understanding Price Action* (2014);
- serious reviews and study notes by others, labelled second-hand.

**Compare** with our reading notes (`..\EA_VolmanPA\PLAN\book\_private\notes_perception\`) and spec v1. List agreements, contradictions and gaps.

**Output:** `RT1_VOLMAN.md`.

### RT2 — Other schools, operationally
**Scope:** the structures in our grammar — range/box, breakout, failed breakout/trap, pullback/flag, trendline/channel, double top/bottom (M/W), head and shoulders, squeeze/wedge/triangle, carried levels.

**For each school:** how it defines and draws them, the mechanism it claims, and what it deliberately ignores.
- **Al Brooks:** trading ranges, breakout mode, barbwire, micro channels, second entries, measured moves, "most breakouts fail".
- **Wyckoff:** trading-range phases, spring/upthrust, sign of strength/weakness, absorption, effort vs result.
- **Auction Market Theory / Market Profile** (Steidlmayer; Dalton): balance vs imbalance, value area, excess, poor highs/lows, initial balance.
- **Darvas box** and the classical chartists: Edwards & Magee; Bulkowski's pattern statistics, including his failure rates.
- **ICT/SMC** — treat critically: liquidity pools above equal highs, stop hunts, order blocks, fair value gaps. Say what is testable, what is a rebranding of older ideas, and what cannot be falsified.

**Output:** `RT2_SCHOOLS.md`, with a cross-school table: concept × school → definition, mechanism, drawn/ignored, operationalization.

### RT3 — Market microstructure: why levels and boxes matter in spot FX
**Start list.** Verify that each exists and fetch its official page.
- Osler (2000), "Support for resistance: technical analysis and intraday exchange rates", *FRBNY Economic Policy Review*.
- Osler (2003), "Currency orders and exchange rate dynamics: an explanation for the predictive success of technical analysis", *Journal of Finance*.
- Osler (2005), "Stop-loss orders and price cascades in currency markets", *Journal of International Money and Finance*.
- Chang & Osler (1999), "Methodical madness: technical analysis and the irrationality of exchange-rate forecasts", *Economic Journal* (head and shoulders in FX).
- Kavajecz & Odders-White (2004), "Technical analysis and liquidity provision", *Review of Financial Studies*.
- Lo, Mamaysky & Wang (2000), "Foundations of technical analysis", *Journal of Finance*.
- Sopranzetti & Datar (2002), "Price clustering in foreign exchange spot markets", *Journal of Financial Markets*.
- Evans & Lyons (2002), "Order flow and exchange rate dynamics", *Journal of Political Economy*.
- Andersen & Bollerslev (1998), "Deutsche mark–dollar volatility: intraday activity patterns, macroeconomic announcements, and longer run dependencies", *Journal of Finance*.
- Andersen, Bollerslev, Diebold & Vega (2003), "Micro effects of macro announcements", *American Economic Review*.
- Chaboud, Chiquoine, Hjalmarsson & Vega (2014), "Rise of the machines: algorithmic trading in the foreign exchange market", *Journal of Finance*.
- Melvin & Prins (2015) and Evans (2018), on the WM/Reuters 4 pm fix.
- Search further: round-number order clustering in FX; the NY 10:00 option-expiry cut, barrier options and "pinning".

**Questions:**
- Where do stop-loss and take-profit orders cluster: at round numbers, just beyond them, beyond swing extremes?
- Do trends accelerate after a level is crossed (cascades)? Do reversals concentrate at round numbers?
- How large are these effects, in pips, and at what horizon?
- Do they survive after 2010, in electronic and algorithmic markets?
- What does intraday seasonality imply for session boxes: the Asian range, the EU open, US data at 14:30 CET?

**Output:** `RT3_MICROSTRUCTURE.md`.
- A paper table: claim, data and era, method, effect size, horizon, caveats, relevance to EURUSD M5.
- Then the implications.

### RT4 — Algorithms for chart perception
**Question:** which algorithms turn bars into the structures a trader sees, causally and robustly?
- **Swings and pivots:**
  - zigzag with percent or ATR thresholds; fractals;
  - directional change / intrinsic time: Guillaume et al. (1997); Glattfelder, Dupuis & Olsen (2011); Tsang et al.;
  - perceptually important points: Chung, Fu et al. (2001); Fu et al. (2007);
  - Ramer–Douglas–Peucker.
- **Lines:** least-touch or convex-hull trendlines, RANSAC, Hough transform; how to choose anchors; slope classes.
- **Levels and zones:** clustering of swing extremes (KDE, DBSCAN); touch weighting; zone width from overshoot distributions.
- **Ranges and boxes:**
  - volatility contraction and choppiness;
  - change-point detection: PELT (Killick et al. 2012), Bayesian online change-point (Adams & MacKay 2007);
  - Darvas-style rules.
- **Multi-scale:** scale-space; multiple-threshold directional change; hierarchical swings — which scale a trader reads on M5?
- **Image-based learning, as a source of insight only** (no ML training on the Owner's PC): Jiang, Kelly & Xiu (2023), "(Re-)Imag(in)ing price trends", *Journal of Finance*; Cohen, Balch & Veloso (2020), "Trading via image classification", ICAIF. Which visual features carried information?

**For each method, give:**
- the definition and a causal implementation;
- parameters, with units;
- complexity;
- failure modes on M5 FX: news spikes, overnight low volatility, whipsaw;
- which of our object types it serves.

**Output:** `RT4_ALGORITHMS.md`, with a recommendation table: object type → best algorithm family → why → risks.

### RT5 — Adversarial reviewer (after RT1–RT4 return)
A fresh sub-agent that wrote none of RT1–RT4. It must:
- take the 10 claims our engine leans on most and try to refute each: counter-evidence, weak methods, era dependence, misreadings;
- fetch ≥ 10 citations and check that each exists and says what is claimed, flagging any hallucinated reference;
- flag folklore dressed up as evidence.

**Output:** `RT5_REVIEW.md`. The lane corrects THEORY_SURVEY for every objection it upholds.

## Lane deliverables (the synthesis, written by the lane itself)
All go in `docs/perception/research/`.
1. **`THEORY_SURVEY.md`.** Per concept: mechanism → operational definition → evidence grade → primitive → test.
2. **`PRIMITIVES_CATALOGUE.md`.** For each candidate primitive:
   - a formal causal definition;
   - parameters with units and provenance;
   - cost and failure modes;
   - the object types it serves;
   - how it is measured on golden TUNE.
3. **`SPEC_v1_CRITIQUE.md`.** Where spec v1 is weak, missing or contradicted by evidence. The v1.1 diffs are proposals only; the Lead rules on them.
4. **`10_NGUYEN_TAC.md`.** For the Owner, in Vietnamese, ELI5: 10 principles of how a pro "sees" a chart. Each principle names the primitive or object that implements it and one example panel.

The design notes (Ruling 2 §2.2) cite these files.

## Quality bar (the Lead will check)
- No uncited factual claim, and no reference that cannot be fetched.
- Evidence, practitioner and folklore are always labelled.
- Every principle ends in something measurable on bars.
- Contradictions between sources are reported, not smoothed over.
