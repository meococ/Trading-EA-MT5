# PERCEPTION — LEAD RULINGS — ARCHIVE R0–R50

Moved verbatim from `LEAD_RULINGS.md` by Ruling 67 §67.5 (23/09 03:35Z). Nothing was changed or deleted. Rulings R51 onward live in `LEAD_RULINGS.md`. Citations such as "R34 §34.5" resolve here.

## Ruling 0 (06:01Z) - mandate issued
- The mandate is `research/perception/MANDATE.md`. The binding spec is `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md`, and the data wall is `docs/CHARTER_ADDENDUM_4.md`.
- The Lead checks the `## SUMMARY` of `PERCEPTION_LOG.md` about every 60 minutes and QA-checks your overlay PNGs by eye.

## Ruling 1 (07:18Z) - STOP: the golden-set time alignment is probably off by 1 hour; re-verify before anything else
**Your conclusion "book chart time == feed server time (offset 0)" contradicts three independent facts:**
1. **The book itself.** Every session time in the text and captions is CET: Asia 00:00, EU 08:00, UK 09:00, US 15:30, ECB 13:45/14:30, US data 14:30 (p48, p267; captions 9.6c, 9.25c, 9.27b).
2. **A news event visible in the casebook.** 2012-03-09 was an NFP Friday. NFP is released at 13:30 UTC, i.e. CET 14:30 (US and EU were both on winter time that day). The reader catalogued "a sharp drop follows at ~14:30 (a news bar)" in panel 9.7b.
3. **Our feed.**
   - The Lead checked 8 DESIGN NFP days (2016-02-05, 2017-03-10, 2018-02-02, 2019-03-08, 2019-07-05, 2020-02-07, 2021-06-04, 2021-11-05).
   - The largest M1 bar sits at server 15:31 in both winter and summer. The one exception is 2021-11-05 at 14:31, when the US was still on summer time and the EU on winter time, so NFP fell at 14:30 server.
   - So the feed is UTC+2/+3 (EET/EEST): pa_clock is right, and **CET = server − 1 h**.
   - The script is `_scratch/tools/nfp_tz_check.py`.
   - Therefore the chart's 14:30 NFP bar must be server 15:30. That is **offset −12 M5 bars, not 0.**

**Your own residuals also look wrong for a correct alignment:**
- inlier fraction median 0.52 (10th percentile 0.24);
- p90 residual 27 pips on the median panel;
- 9.7b: inlier fraction 0.42, p90 46 pips.

With the right offset, most extracted extremes should be inliers.

**Required now, before any normalisation or refinement work:**
- **(a) Re-run the candle alignment with an offset search over −24…+24 M5 bars for every panel.** Report the residual profile per panel (inlier fraction and p90 at each offset), plus a global histogram of the best offsets.
- **(b) Validate on the news bars you can locate.** Check 2012-03-09 NFP (9.7b), the ECB day 2012-03-08 (9.6c) and every other captioned news spike. The spike bar must land at the captioned CET time.
- **(c) Fix the clock and regenerate.** If the evidence confirms CET = server − 1 h, fix the mapping in `calibrate.py` / `book_loader` (chart time = CET, the book's clock) and regenerate `calib.jsonl`. All session logic in the engine (Asian RANGE_OPEN from 00:00, EU open 08:00, news windows 14:30/16:00) is in **CET**, as the spec says.
- **(d) Log it** in DECISIONS as D3, with the before/after residual tables.
- **(e) If the evidence really says offset 0,** show the NFP bar on 9.7b at chart 14:30 matching a server-14:30 bar with a large range, and say so in ASK_LEAD.md.

**Minor:** debug images derived from the book scans (`golden/_dbg_*.png`) are allowed only as local, gitignored scratch. Keep them few, and keep them inside `golden/_scan_cache/`.

## Ruling 2 (08:13Z) - STOP engine tuning. Fix the yardstick first, then reason before you code. Deep research added (Owner directive)

**Owner directive (2026-09-21 ~08:00Z, paraphrased):** Devin's drawing work is not good enough yet. Do more and research more, deeply. This part needs deep reasoning, a sound understanding of how to draw, and an understanding of the market and the chart.

**Accepted:** D3 is good work. NFP prints at server 14:30 in both seasons, so the BOOK feed runs on Berlin wall time; the sweep moved 341/386 → 375/386 to offset 0. The TUNE/HOLD split and the HOLD hash (T000361) stand.

### 2.1 The golden set is not yet a yardstick
The Lead checked TUNE only; HOLD was not opened.
- **PATTERN_LINE (199).**
  - 52 have no price.
  - Of the 79 refined lines whose catalogue note contains a slope word, **28 (35%) slope the opposite way**:
    - 9.1a "long rising line under the lows" → refined −30.8 pips (rms 8.9 px);
    - 9.6c "falling line" → +26.2;
    - 9.14c "bull-flag falling line" → +32.0;
    - 9.17c "rising line" → −16.1;
    - 9.1b "rising line under the lows" → −12.2, even at rms 1.45 px.
  - A low rms proves nothing: the refiner found *a* straight segment, not *the* line in the text.
- **BOX (116).**
  - 21 have no price.
  - Of the 55 with catalogue prices, 15 deviate > 3 pips after refinement. Example, 9.6a: text 1.3173–1.3179, refined 1.3167–1.3185.
  - 9.54a's "~22-pip Asian BOX 02:00–09:10" has one edge only.
- **Levels.** LEVEL_CARRIED 28/48 and MINI_LEVEL 28/32 have no price, so the LEVEL_CARRIED gate cannot be scored as the spec defines it.
- **Schema.** Refined times are ints (CET minutes); unrefined times are "HH:MM" strings.
- **Your QA overlays** (the Lead viewed them):
  - 9.1a: the neckline is a falling line through empty space below the bars, and a T floats below the bars at 07:15.
  - 9.54a: the Asian box renders as one horizontal under the lows, and the rising TL is missing.
  - You logged these overlays as "looks reasonable". That is the core problem: you did not check the drawing against the text or against the bars.

**G-AUDIT — next, before any TUNE scoring:**
- **(a) `golden/validate.py`.** A semantic validator per object, using the catalogue text AND the real bars (book_loader). At minimum:
  - **slope** sign vs text: rising/falling/flat, bull-flag/bear-flag, neckline direction;
  - **side** vs text: a line "under the lows" or "over the highs" has ≥ 2 bar touches within tol on that side, and no more closes beyond it than the text allows ("broken", "pierced");
  - **anchors**: "from the ~15:45 high" ⇒ the line's start lies within tol of that bar's extreme, ±2 bars;
  - **BOX**:
    - both edges touched (≥ 2 bars within tol, or as the text says);
    - ≥ 80% of the bar extremes in the span lie inside the box ± tol;
    - pokes only where T/F marks say so;
  - **LEVEL_CARRIED / MINI_LEVEL**: within tol of the referenced swing extreme or breakout base;
  - **marks**: T/F on the right edge side and inside the box span; brackets over or under the named formation;
  - **time** inside the panel window; **type** consistent with style (dotted ⇒ CONTEXT_*, long-dashed ⇒ LEVEL_CARRIED).
- **(b) Repair every failure,** in this order:
  1. constrained re-refinement, with the text's slope sign and anchors as hard constraints;
  2. anchor from bars: snap to the named bar extremes;
  3. mark `unusable` with a reason.

  Never keep geometry that contradicts the text.
- **(c) Missing prices.** Derive them from the bars the text names. If none are named, mark the object `time_only`; it is scored on time and type only, and reported separately.
- **(d) Schema.** Normalise it: CET minutes as ints everywhere, `price_hi/price_lo` for boxes, `price0/price1` for lines. Version the result `BOOK2012_v2`.
- **(e) HOLD.** Run the **same code** on HOLD, blind, and report only pass/fixed/unusable counts. No engine output may ever be produced on HOLD before the Lead's go. Re-hash HOLD v2 into the ledger as a new `perception_golden` row referencing T000361 (append-only).
- **(f) Independent spot check** by a sub-agent that did not write validate.py:
  - 40 TUNE objects, stratified by type;
  - for each, it sees our own rendering plus the catalogue text and answers matches / does not match / can't tell;
  - target ≥ 90% "matches" after repair.
- **Write-up.** `golden/GOLDEN_AUDIT.md`: before/after tables per type, examples and the spot-check result.

### 2.2 Reason before you code (the Owner's main complaint)
**The problem.** Your log shows thresholds and tests bent until green: "relax this test", "shrinking fixture wicks", "loosening to 1.2×ABR", "fixing the test to assert on edges, not the route label". That is tuning to synthetic fixtures, not to the book or the market.

**From now on:**
1. **One design note per object type, before its code changes.** Write `research/perception/design/DN_<TYPE>.md` for:
   - BOX (with RANGE_OPEN/CONTEXT_RANGE), PATTERN_LINE/CONTEXT_LINE, LEVEL_CARRIED/MINI_LEVEL, SQUEEZE, T/F, BRACKET;
   - **DN_SWING**: the pivot/leg definition, which everything else depends on;
   - **DN_SALIENCE**: what gets drawn at all.

   Each note has seven parts:
   - i. **Market mechanism.** Who acts at this structure and why: stop orders, breakout entries, trapped traders, profit-taking, absence of opposition. What does the structure predict about order flow?
   - ii. **Volman's criteria,** with page refs; quotes ≤ 15 words.
   - iii. **Other schools'** definitions of the same thing (from DR-THEORY, 2.3).
   - iv. **Golden measurements on TUNE,** as distributions in pips and in ABR: height, width, touches, age at birth, distance to price, slope, pierce count.
   - v. **The operational rule:** birth, maintenance and death. Every parameter has a provenance: a page, a golden percentile or a market-study result. "Tuned until a fixture passed" is not a provenance.
   - vi. **Failure modes:** ≥ 3 false-positive and ≥ 3 false-negative cases, each with a TUNE panel id.
   - vii. **Tests:** golden-derived fixtures on real TUNE bars, plus theory fixtures that encode the book rule, not the implementation.
2. **Test integrity.**
   - An assertion or fixture may be weakened only with a DECISIONS entry that cites the design note and explains why the old assertion was wrong **about the book**.
   - Log every weakening done since 07:19Z retroactively (D4, …).
3. **Drawn vs not drawn is the core question.**
   - For each TUNE panel, enumerate every candidate structure the engine can find, and label the ones Volman drew.
   - Tabulate what separates drawn from ignored: recency, distance to price, touches, relation to the EMA, session, being the last structure before the move, room to the next obstacle, and so on.
   - The salience rule (DN_SALIENCE) comes from these tables, not from caps and cooldowns.
4. **Disagreement analysis** after the first TUNE eval.
   - Take the ~50 worst panels. For each, write what Volman drew, what the engine drew and why they differ: timing, anchor, scope, over-drawing, missing context or wrong type.
   - Output: `DISAGREEMENT_<n>.md`, then rule changes, each a DECISIONS entry with metric deltas.
   - At most 3 rounds before READY FOR HOLD.
5. **Clock.**
   - The engine takes CET from a feed-aware clock:
     - BOOK feed = Berlin wall (identity, D3);
     - DESIGN feed = EET (CET = server − 1 h; 8 NFP checks 2016–2021).
   - Test both.
   - The engine never infers the clock from bars.

### 2.3 DR-THEORY — deep research by your own sub-agents
**Why here.** The machine's Devin cap (6 concurrent) is full, so this research runs inside this lane.
- Dispatch sub-agents now with `run_subagent` (background), and work on G-AUDIT while they run.
- Fold their results into the design notes.
- The brief — topics, questions, deliverables and quality bar — is `docs/perception/research/DR_THEORY_BRIEF.md`. Follow it.
- **Fallbacks:**
  - if sub-agents cannot write files, they return full markdown and you write it verbatim;
  - if `run_subagent` is unavailable, work through the brief yourself between G-AUDIT steps.

A separate empirical lane, DR-MARKET (`research/market/MANDATE.md`, DESIGN only), starts when a Devin slot frees. Its results reach you through Lead rulings.

### 2.4 New queue
It replaces P2–P3 of MANDATE.md. P4–P6 are unchanged.
- **Q0.** Dispatch the DR-THEORY sub-agents.
- **Q1.** G-AUDIT (2.1).
- **Q2.** TUNE measurements and the drawn-vs-not-drawn tables.
- **Q3.** Design notes (2.2.1), merging DR-THEORY as it lands.
- **Q4.** Rewrite the engine from the notes; theory + golden tests.
- **Q5.** TUNE eval → disagreement rounds (≤ 3).
- **Q6.** DR adversarial review (RT5) and `SPEC_v1_CRITIQUE.md`. These are proposals; the Lead rules on v1.1.
- **Then** P4–P6.

**Box.** A new 12-hour box starts at this resume.

**Walls.** Unchanged: Addendum 4; no outcomes; ≤ 2 pa_slots, BelowNormal; no OCR/ML; no commits or pushes; no deletes.

### 2.5 Data note (for the record; not this lane's work)
- D3 implies the M1 parquet is not on one clock across years: BOOK 2012 = Berlin; DESIGN 2016–2021 = EET.
- Addendum 4 forbids reading any other 2010–2015 bar, so do not investigate further.
- The Lead records it as a **CONFIRM-PRE blocker**. Before any CONFIRM-PRE look, the unseal tooling must establish the clock regime per year (timestamp-only) and route all session logic through it.

## Ruling 3 (08:52Z) - resume after the quota stop; findings accepted; book-material hygiene
- **The stop.** The lane died at 08:32Z: Devin's daily quota for the premium model was exhausted. It resumes on swe-2-max. Ruling 2 binds unchanged.
- **Accepted as D8** (log the numbers):
  - 37/77 slope-worded refined lines have the wrong sign.
  - Root cause: `corridor_fit` fits all the ink, and `drawn_ink` removes only the longest run per column, so the fit traces the price path.
  - Refinement overwrote catalogue prices in place, so `draft/BOOK2012_draft.jsonl` is the only surviving catalogue truth.
- **Line repair.**
  - Anchor lines on the bars the text names.
  - Ink may confirm or break a tie; it never sets a slope sign against the text.
  - Each repaired object records its method: `text_anchor_bars`, `constrained_fit` or `unusable`.
- **Book-material hygiene** (Addendum 4 A4.3).
  - Move (never delete) `docs/perception/research/_tmp_rt1/`, which holds the author's excerpt PDFs and their text extractions, to `..\EA_VolmanPA\PLAN\book\_private\web_excerpts\`, with a `SOURCE.md` giving the URLs.
  - Research scratch never lives under `docs/`. `docs/perception/research/.gitignore` is a backstop.
- **Sub-agents.**
  - At most 4 at once.
  - No full books, and no book PDFs except the author's or publisher's own samples. Those are stored under `_private/` only.
  - Re-dispatch RT1–RT4; they died with the process.

## Ruling 4 (09:57Z) - research accepted; close G-AUDIT with a frozen yardstick
- **Record note.** Ruling 3 was delivered in the RESUME 3 prompt, but a sync fault kept it out of this file until now. It is restored above, unchanged.
- **RT1–RT4: accepted.** They are strong work.
  - Sources are verified, and claims are graded.
  - Caveats are explicit: equity-only evidence, 1990s-era data.
  - The Lead spot-checked two citations and both are real and correctly cited: Krohn, Mueller & Whelan (2024), *J. Finance* 79:541–578; and FCA Occasional Paper 46 (Evans, O'Neill, Rime & Saakvitne, 2018).
  - Keep this standard in THEORY_SURVEY. RT5, the adversarial review, is still due.
- **Freeze the yardstick before Q2.** The validator/repair code changed several times after the HOLD v2 run was hashed as T000362, so that hash may no longer match the file. Close G-AUDIT as follows:
  - **(a) Freeze and hash the code.** Freeze `textfeat.py`, `validate.py` and the repair code. Record their sha256 in `GOLDEN_AUDIT.md`.
  - **(b) Final run and ledger row.**
    - Regenerate TUNE v2 and HOLD v2 **once** with the frozen code.
    - Append **one** superseding `perception_golden` ledger row for HOLD v2 that references T000361 and T000362.
    - HOLD v2 is then frozen. No code runs on HOLD again until the Lead's scoring go.
  - **(c) Repair iterations run on TUNE only.**
  - **(d) Independence.** The repair code must not import `engine.py` or share its swing/pivot logic: the yardstick must stay independent of what it measures. State this in `GOLDEN_AUDIT.md`.
  - **(e) Usable rates.** Report TUNE and HOLD usable rates side by side (about 94.1% vs 83.6%) and explain the gap by category (catalogue fragments, out-of-window, …). HOLD is counts only.
  - **(f) Time box.** G-AUDIT closes by about 11:30Z. Anything still unrepaired by then is `unusable`, with a reason. Then Q2.
- **DR-MARKET is running** (job `20260921095608-913527`, DESIGN only). Its results reach you only through Lead rulings.
- **Lead correction (09:58Z):** the 9.6a example in Ruling 2 §2.1 was an artefact of the Lead's own quick regex, which read a compound note. The object's own clause says 1.3167–1.3185 (18 pips). Your clause-level parse is right. The other numbers in §2.1 stand, and your D8 count (48%) supersedes the Lead's 35%.

## Ruling 5 (11:01Z) - G-AUDIT accepted; one fresh spot check; fwd_* withdrawn; market facts in
- **G-AUDIT: accepted.** Excellent work.
  - Yardstick v2 is frozen: textfeat `ada60dd1…`, validate `2224ea3b…`, repair `df56cecd…`.
  - HOLD v2 is frozen under T000366.
  - The D9 box semantics are right: drawn edge ≠ containment end; the stated height is the pre-break range.
- **(a) One fresh spot check.**
  - **Why:** Round 2 re-judged the same 45 objects whose round-1 failures drove the fixes, so 97.7% is optimistic.
  - **Round 3:** a new agent, which saw neither round, judges a **fresh** stratified sample of 40 TUNE objects that were not in rounds 1–2. Gate ≥ 90%.
  - **Pass:** v2 stands.
  - **Fail:** fixes go into v3, with new code hashes; run TUNE v3 and HOLD v3 once and add one ledger row. Never patch v2 in place.
- **(b) `fwd_*` is withdrawn.**
  - **What:** Q2 §4's `fwd_range_60` and `fwd_rng_pctile` measure price movement after birth on BOOK bars. That is an outcome-type measurement, which Addendum 4 A4.2 forbids in the BOOK window.
  - **Cause:** the Lead's own wording in Ruling 2 §2.2.3 ("being the last structure before the move"). This is logged as a Lead deviation, not yours.
  - **Actions:**
    - stop computing `fwd_*` (remove it from `measure.py`);
    - mark those Q2 §4 rows "WITHDRAWN (A4.2)" — files stay, no deletes;
    - no DN or DECISIONS entry may cite them as provenance.
  - **The lesson to keep:** the golden set is hindsight-selected — the author annotates what mattered for the trades he discusses.
    - DN_SALIENCE must use causal correlates only: compression, buildup against a barrier, span, touches, `n_active`, session.
    - Read the recall gate with that bias in mind.
  - The DESIGN-side question ("does causal compression precede expansion?") belongs to DR-MARKET M4.
- **(c) Consistency in the DN notes.**
  - Every number must be defined and cite its table row. Example: DN_SWING §4 says "PATTERN_LINE median span 85 min", while Q2 gives "~3.4 h" (§1) and "205 vs 95 min" (§4). Say which span you mean: anchor-to-anchor or drawn extent.
  - Page refs must be real pages from the notes. No "p.~approx".
- **(d) Market facts from DR-MARKET M3.**
  - Source: DESIGN 2016–2021, 4 majors, placebo-matched. Prereg T000364; results T000367–372; file `research/market/LEVELS.md`.
  - Use them as priors for DN_LEVEL, DN_BOX and DN_SALIENCE. Golden fidelity decides *what* is drawn; market facts inform lifetimes, zone widths and salience weights.
  1. Swing levels bounce more than placebo, by +1.1 to +1.5 pt. The effect is small but stable: 6/6 years and 4/4 symbols.
  2. The first touch is strongest (+4.4 pt); touch 2 gives +0.8; touch 3+ gives ≈ 0. This supports "consumed after one touch".
  3. Level age has a half-life of about 0.7–2.5 h. Levels are perishable: carried levels should live hours, not days.
  4. Overshoot p90 is about 0.5–0.7 ABR (≈ 2–5 pips), so a zone half-width of about 0.25–0.35 ABR fits. T/F pokes of 1–3 pips are normal overshoot.
  5. Retest or role reversal after a clean break has no incremental effect vs placebo. LEVEL_CARRIED is a fidelity object; do not give it extra salience weight.
  6. Round numbers show no robust bounce effect (year-unstable). 00/50 stay context only.
  7. The Asia range median is about 22.6 pips on EURUSD (≈ 9–11 ABR). Check the spec's Asian thresholds against the golden RANGE_OPEN height (~19 p).
- **(e) Overlays.** Re-render the 12 QA overlays in `golden/qa/` from BOOK2012_v2 now, as new files `*_v2_overlay.png`; keep the old ones. Make them large enough to read: ≥ 1600 px wide, with the price axis labelled. The Lead will check them against the catalogue text and show the Owner. Keep rendering our own bars; never re-save book images.

## Ruling 6 (14:30Z) - B0 accepted; make B1/B2 measurable before tuning further
- **B0: accepted.**
  - Spot-check R3 on a fresh sample: 38/40 = 95%.
  - `fwd_*` is withdrawn (D12).
  - The Lead viewed the v2 overlays for 9.1a and 9.54a: both are right. They were shown to the Owner.
- **The first v1 eval shows the gap** (30 panels): BOX recall 0.24 and precision 0.02; PATTERN_LINE 0/29; clutter median 9.25. Expected at this stage. But the next hours must not become an untracked tuning loop inside B1. Do this, in order:
  1. **Freeze a baseline.** Tag the current code as `v1.0` (hash in DECISIONS). Run `eval.py` on **all** TUNE v2 panels for both **v0** (`engine_v0.py`) and **v1.0**. Report them side by side in EVAL_TUNE.md, together with the matching rules used.
  2. **Explain PATTERN_LINE 0/29 first.** It is the largest golden family. Tell apart:
     - a matching-rule bug (tolerances, slope and anchor handling vs spec §6.1);
     - a systematic geometry mismatch (anchors, extension, scale θ₁ vs θ₂).

     Put the answer in DISAGREEMENT_1.md, with 5 worked panels.
  3. **Churn and clutter are salience questions (DN_SALIENCE §5).**
     - The mechanisms added today — grave registry, band-proximity dedupe, structural-pivot gating for boxes — are acceptable only as instances of rank hysteresis and NMS (RT4 §9.4). Each needs a DECISIONS entry that cites that section, plus a short DN_SALIENCE addendum.
     - No free-floating thresholds. A number without provenance is `MEASURE-TUNE`, with the table that set it.
  4. **Then start the B3 rounds proper** (≤ 3), each with its DISAGREEMENT_n.md and metric deltas on all TUNE panels.
- **Hindsight reminder (Ruling 5b).** The golden set is setup-selected. Volman draws what matters for the trades he discusses. The causal answer is "signal ink only near a decision point" (a buildup against a barrier, a pullback into a structure), with context ink kept to 1–2 objects. Do not chase recall by drawing more.

## Ruling 7 (15:34Z) - measure the ruler before measuring with it
- **Good work in DISAGREEMENT_1 and the PATTERN_LINE dive.** These are real engine defects:
  - phantom hull vertices from the reverse pass;
  - no recency bound on the pool;
  - touches counted on pivots instead of bar wicks;
  - an overshoot penalty that is too weak.

  Fix them per DN_LINE.
- **Validate `eval.py` before any further tuning.** At 198 panels, v1 BOX recall is 0.05, yet Q2 found that v0 candidates covered 95% of golden boxes under looser matching. A gap that large may be a ruler problem as much as an engine problem. Add to `eval.py` and report in EVAL_TUNE.md:
  1. **Self-test.** Feed the golden v2 objects in as if they were engine output → recall and precision must be ≈ 1.0. Anything less is an eval bug.
  2. **Jitter test.** Perturb the golden objects within their own label precision (eye ±5 p / ±10 min; meas ±2 p) → recall must stay high. If it collapses, the matching tolerance is tighter than the labels can support. Tie the tolerances to the object's precision flag and write that down.
  3. **Semantics (D9).** Match a box on its containment window `build_start..build_end` and its edges, not on the drawn span that runs past the break. Apply the same principle to lines: pre-break anchors plus slope, with extension excluded.
  4. **Bridge to Q2.** Report the Q2 loose-matching coverage and the §6.1 strict matching side by side for v0 and v1, so the drop is explained.
  5. **Still owed from Ruling 6:** the v0 vs v1.0 table on all 198 panels.
- **Budget caps.** The per-kind birth-rate caps (golden p90 counts) are an acceptable budget per DN_SALIENCE §5 stage 5. But they cap *how many*; they do not choose *which*. When recall falls after a cap, the ranking score is the problem. Work on the separator: matched median 8.5 vs unmatched 4.1 is a start.
- **Order from here:** eval validation → line fixes → B3 round 2 on all TUNE panels. Each change is a DECISIONS entry with metric deltas. Keep going; the box has ~8 h left.

## Ruling 8 (16:12Z) - speed-up: two helper lanes take work off you
- **Owner directive (~16:10Z): push faster.** Two new Devin lanes run in parallel from now on, so that you can spend your whole box on the engine.
  1. **EVAL-AUDIT** (`research/perception/MANDATE_EVAL_AUDIT.md`) now owns the ruler checks of Ruling 7, items 1–4: the self-test, the jitter test, D9-consistent matching (`evalcheck/eval_v2.py`), and the Q2 ↔ strict ↔ eval_v2 bridge for v0 and the current engine.
     - It writes only under `research/perception/evalcheck/` and never edits your files.
     - Keep using `eval.py` for iteration. When the Lead adopts eval_v2 in a ruling, switch to it.
  2. **RESEARCH-SYNTH** (`docs/perception/research/MANDATE_RESEARCH_SYNTH.md`) now owns B4: RT5, THEORY_SURVEY, PRIMITIVES_CATALOGUE, SPEC_v1_CRITIQUE and 10_NGUYEN_TAC. **Drop B4 from your queue.**
- **Your queue now:**
  1. Finish the engine fixes: box proposals per D9, which is in progress and good; the line defects from DISAGREEMENT_1; the salience separator.
  2. B3 rounds (≤ 3) on all 198 TUNE panels, each with metric deltas.
  3. B5 DESIGN gallery.
  4. B6 independent code review.
  5. READY FOR HOLD.
- **Pace.**
  - Write a short PERCEPTION_LOG entry at least every 45 min, so the Lead's 10-minute checks can see progress.
  - Do not stop at checkpoints.
  - `pa_slots` is shared by all lanes (4 in total). Hold at most 2, and release them promptly.

## Ruling 9 (16:32Z) - a ruler bug the Lead found; caps must not choose; clock
For PERCEPTION-BUILD (§9.1–§9.5). EVAL-AUDIT gets §9.1–§9.2 through `evalcheck/LEAD_NOTE_R9.md`.

**§9.1 `eval.py` stretches live engine objects to the end of the day.** Found by reading `eval_panel` and `eng_objects`.
- The code: `t1_src = o.geometry.get("t1_drawn") or (o.t_right if o.t_right is not None else len(m) - 1)`. Here `m` is the whole day's `cet_min` array, but the engine was only fed bars up to `w1`.
- So every object still ACTIVE at the panel edge gets `t1` ≈ 23:55 CET. Golden open spans end at `w1`.
- The left side has the same asymmetry: an engine `t0` before `w0` is not clipped, but golden partial spans are.
- Example: a 60-minute golden box against an exact engine copy that is still alive at `w1` = 16:00. The engine span becomes 15:00→23:55, so the overlap score is about 0.1 and the match fails.
- This hits BOX, the span route for PATTERN_LINE, and every type matched at overlap ≥ 0.3. It fits your own finding that 26 boxes were born with correct edges but only 4 matched.
- **Fix (exact and symmetric):** after computing `t0m` and `t1m`, clip both to the panel window: `t0m = max(t0m, w0); t1m = min(t1m, w1)`. Golden spans are panel-visible by construction, so the same rule now holds on both sides.
- **Who does it.** You apply it in `eval.py` now; it is your file, and the Lead specified the fix, so the builder is not choosing its own ruler.
  - Log it as its own DECISIONS entry: "ruler fix R9.1, no engine change".
  - Re-run EVAL_TUNE for the current engine and for v0, with a before/after table.
  - Make no engine change in the same run, so the effect stays isolated.

**§9.2 `iou()` is not IoU.** It computes intersection / max(length), which is always ≥ true IoU, so it is more lenient. Spec §6.1 says IoU.
- EVAL-AUDIT uses true IoU (intersection / union) in eval_v2 and reports both in E4.
- You leave `iou()` alone until eval_v2 is adopted: one ruler change at a time.

**§9.3 Caps must not choose (Ruling 7, now with a test).** 48 of the 74 proposals with correct geometry were refused birth because the family cap was already full. That is selection by arrival order.
- **Change:** when a family is at its cap and a new candidate outscores the weakest live object of that family by at least the hysteresis margin, close the weakest (`outranked_cap`, with both scores logged) and give birth to the new one.
- **Invariant, reported each round:** refusals by cap where the refused candidate outscored the weakest live object = 0.
- **Also report, for the 74 correct proposals:** how many were born, and how many were refused by cap, by NMS and by the score floor.

**§9.4 Clock.** PERCEPTION_LOG contains "rulings read ~16:40Z" in an entry saved at 16:20Z. Every log time comes from the clock: `datetime.now(timezone.utc)` in Python or `(Get-Date).ToUniversalTime()` in PowerShell, never typed by hand. Correct that line with a note; do not rewrite history.

**§9.5 Order:**
1. R9.1 fix and re-run (≤ 20 min), with the before/after table in PERCEPTION_LOG.
2. R9.3 cap pre-emption.
3. Line fixes.
4. B3 round 2 on all 198 TUNE panels.

Iterate with `eval.py` plus R9.1. Switch to eval_v2 only when the Lead adopts it in a ruling.

## Ruling 9a (16:44Z) - correction to §9.1; the missing term behind "the score can't separate"
**§9a.1 Credit and correction.** You found the same day-end stretch bug yourself and fixed it at 16:28Z (`len(m) - 1` → `len(e.bars) - 1`, DECISIONS D15.3). The Lead read the 15:37Z copy of `eval.py`, so the fix came before Ruling 9. Good catch.

Two parts of §9.1 are still open:
1. The left clip: `t0m = max(t0m, w0)`. Golden partial spans already get this.
2. Re-run the v0 column of EVAL_TUNE under the fixed ruler, so the v0 vs v1 comparison stays fair. Both engines take a few minutes on 198 panels.

D15.3 was bundled with two engine changes in one round. The isolated figure in DISAGREEMENT_2 (7 → 18 of the 30 boxes born with golden edges now reach the 0.5 overlap) is accepted as the isolation. From now on, a ruler change gets its own run.

**§9a.2 The separator: the score has no barrier term.** Your notes disagree about the score:
- DISAGREEMENT_2 says it cannot separate golden-right from golden-wrong candidates (medians both ~8.5).
- D14.3 says it can (8.5 vs 4.1).

Settle it with one number: the AUC of the birth score for golden-right vs golden-wrong, measured on the candidates that competed for a full cap slot.

The Lead read `salience.score()`. Its terms are touches, span, prominence, recency, proximity to the close, session and consumption. None of them says *where* the box sits relative to anything.

The accepted research (RT1_VOLMAN, entries Box / Barrier / Buildup) describes the box Volman draws as a buildup pressed against a barrier:
- repeated equal extremes on one side;
- the other side creeping toward them;
- small, shrinking bars;
- often the EMA guiding price in.

A tease break is defined by the absence of this. DN_BOX and spec v1 contain the word "barrier" 0 times. The engine was built without the concept that makes Volman draw the box. The golden set is setup-selected (Ruling 5b), so this term is the precision lever as much as the recall lever: BOX precision is 0.04 against a gate of 0.60.

**Candidate features.** All causal, all computed at birth time, TUNE only:
1. **Barrier coincidence.** The anchor edge lies within `tease_tol` of something that existed before the box: a carried level, an earlier structural swing extreme of the day, or the day's high or low so far.
2. **Pressure.** Inside the run, the opposite-side extremes trend toward the anchor edge: rising lows under a ceiling, falling highs above a floor. Use the sign and the size relative to ABR.
3. **Compression.** Median bar range over the last `min_build_bars` bars, divided by ABR.
4. **EMA guidance.** Distance from the close to `e.ema` shrinking toward the anchor edge. EMA25 already exists in `patterns.py`.

**Protocol (few degrees of freedom on purpose):**
- Measure each feature's AUC on the capped-candidate pool with a day-level 5-fold split.
- Keep only features with AUC ≥ 0.60 on every fold, and at most 4 of them.
- Combine the kept features with equal weights on rank-normalised values. No fitted weights.
- Write DN_BOX §Barrier citing RT1, and a DECISIONS entry with the per-fold AUCs.
- Then §9.3's pre-emption has something real to rank by.

`cand_ttl` 24 → 72 is fine as a companion change. On its own it is still arrival order.

**§9a.3 Order (replaces §9.5):**
1. Left clip and v0 re-run (≤ 15 min).
2. AUC of the current score on the capped pool.
3. Barrier features plus the §9.3 pre-emption.
4. B3 round 3 on all 198 panels. The headline is the funnel: proposed with right geometry → born with right geometry → matched, plus BOX precision.
5. Line fixes. PATTERN_LINE is still 4/186.

Log every step in PERCEPTION_LOG with clock timestamps (§9.4).

## Ruling 9b (16:59Z) - lines move to a sandbox lane; your queue gets shorter
- **New lane LINE-LAB** (mandate `research/perception/linelab/MANDATE_LINE_LAB.md`). It owns trendlines from now on:
  - line yardstick audit, line anatomy, an anchor-first prototype, and an integration note;
  - it writes only under `linelab/` and never edits `lines.py`.
  - The reason for the audit: all 198 golden PATTERN_LINE labels are `eye`, and 122 of them are `constrained_fit` repairs. The labels must be measured before anyone tunes against them.
- **Drop "line fixes" from your queue** (item 5 of §9a.3). Touch `lines.py` only for a bug a test exposes, and log it.
- When LINE-LAB delivers `LINE_INTEGRATION.md`, the Lead rules and you integrate.
- Your queue is §9a.3 items 1–4: boxes, the salience separator, barrier features, cap pre-emption, and round 3. Then B5 and B6.

## Ruling 10 (17:16Z) - one ruler; v1 must beat v0 before anything else
**§10.0 You stopped too early and missed four rulings.**
- Your job ended at 17:02Z with "do you want me to continue?". The mandate says no early stop, so the answer is always yes. Never end a session to ask. When the queue is empty, take the next item from your own "Still open" list and log it.
- Your summary says the next step is B4. Ruling 8 (16:12Z) moved B4 to RESEARCH-SYNTH, and that lane finished it at 16:43Z. You worked through Rulings 8, 9, 9a and 9b without reading them.
- **New rule:** read `LEAD_RULINGS.md` at the start of every round. Log "rulings read up to R_n at HH:MMZ" with the clock time.
- Your round 3 work was good and is accepted (D16):
  - the same-bar race fix;
  - the persistent footprint grave;
  - rejecting the ledger refund. The reasoning that "the ledger must count births, not live structures" is exactly right.
  - `cand_ttl` reverted by measurement.

**§10.1 Official ruler = `evalcheck/eval_v2.py`.** EVAL_AUDIT.md is accepted. eval_v2 is the only ruler that passes its own calibration: E1 = 1.0000 on both copies, and E2 at 1× jitter ≥ 0.96 on every type.
- The frozen ruler state:
  - `eval_v2.py` `04c6f7bdff6459d5`;
  - `common.py` `7eddcc85ebf45bb4`;
  - `eval.py` `8d016922aecae265`, which eval_v2 imports;
  - `golden/book_loader.py` `b40c2cab5c2ffe7d`.
- **You no longer edit `eval.py`.** It is now part of the ruler. Changes to any of these files come only from EVAL-AUDIT, through a Lead ruling, with E1 and E2 re-run.
- All gate numbers, DECISIONS deltas and DISAGREEMENT tables use eval_v2 from now on. Report the BOX route counts every time: containment-IoU matches vs coverage matches.
  - A coverage-route BOX match is weak evidence: in the audit, all 8 of v1's failed true containment IoU.
  - The final BOX rule comes in Ruling 11, after EVAL-AUDIT classifies those pairs as nested (same episode) or disjoint (different episode).
- `eval.py` stays as the legacy column only. §9.1's left clip and the v0 re-run are withdrawn; the bridge did the re-run.

**§10.2 The honest picture on 198 TUNE panels, eval_v2** (from `bridge_report.md`, v1 = hash `504eb8ef`, your round-3 code):

| | v0 | v1 |
|---|---|---|
| BOX recall | 0.21 | **0.07** |
| BRACKET recall | 0.73 | **0.07** |
| LEVEL_CARRIED recall | 0.17 | 0.10 |
| PATTERN_LINE recall | 0.10 | 0.09 |
| clutter median | 8.00 | 4.33 |

- v1 halved the ink but lost two thirds of the boxes and nine tenths of the brackets.
- Round 3's "BOX 0.16" was the legacy ruler; under eval_v2 it is 0.07.
- **v1 must beat v0 under eval_v2 before any more selection tuning.**

**§10.3 Your queue now (replaces §9a.3):**
1. **Regression analysis** → `REGRESSION_V0_V1.md`. For BOX, BRACKET and LEVEL_CARRIED:
   - list every golden object that v0 matches and v1 misses under eval_v2, and the reverse;
   - for each v1 miss, give the reason:
     - never proposed;
     - proposed with right geometry but not born, and which gate refused it (rate cap, NMS, budget, grave, score floor, family gate);
     - born with wrong edges;
     - born with right edges but a different episode (containment window disjoint);
     - closed too early.
   - Totals per reason, and 5 annotated examples per type.
   - Use EVAL-AUDIT's `evalcheck/FUNNEL.md` labels as soon as they exist: they are the independent "right/wrong" labels. Until then, import eval_v2 read-only.
2. **Fix the top 2–3 causes, DN-faithfully.** One DECISIONS entry per change, with eval_v2 deltas for BOX, BRACKET and LEVEL, plus clutter.
   - BRACKET first if the cause is a gate or cap: 0.73 → 0.07 is the biggest single loss.
   - Rounds 4–6 are allowed. This extends the B3 budget; each round gets a `DISAGREEMENT_n.md`.
3. **Ruling 9a separator work, only after (2):**
   - AUC of the birth score on EVAL-AUDIT's labels;
   - the barrier features (≤ 4, per-fold AUC ≥ 0.60, equal-weight ranks);
   - cap pre-emption by score.
4. **B5 gallery** once v1 ≥ v0 on BOX and BRACKET under eval_v2. Then B6.

**§10.4 Ledger hygiene.** Rows T000365/T000366 (`perception_golden`) were written without `pa_ledger.append`, and they break `verify()` (market REVIEW_3 N1). Any future ledger row from this lane goes through `pa_ledger.append` only.

**§10.5 Pace.**
- `pa_slots`: at most 2.
- PERCEPTION_LOG every ≤ 45 min, with clock times.
- EVAL-AUDIT now builds your shared tools: funnel labels, a bars/ABR/engine-output cache, a known-answer suite and the data-wall check. Pull them in as they land.

## Ruling 11 (17:34Z) - BOX rule, funnel rule, line sigma; what the Lead saw in the renders; market facts adopted
Good work since R10:
- the rulings were read and logged at 17:18Z;
- `REGRESSION_V0_V1.md` is clear;
- starting with BRACKET generation is right.

EVAL-AUDIT's FUNNEL and renders, and LINE-LAB's L1/L2, give the Lead enough to settle five things.

**§11.1 BOX rule (ruler; EVAL-AUDIT implements it, with E1/E2 re-run and a new ruler hash).**
- **Match = true IoU of the containment windows ≥ 0.5, plus both edges within tol.**
- The drawn-span coverage fallback is removed. It stays only for a side that records no containment window at all, and its use is counted.
- The reason: coverage accepted different episodes. v0 had 7 disjoint pairs and v1 had 5. 9.40c "matched" with IoU 0.00.
- The same-episode pairs with IoU < 0.5 are real extent disagreements, not label noise; the label time noise is ±10 min. Example: 9.4b, where the engine window is 675–720 and the golden one is 675–815, because the engine closed the box 95 min early. That is an engine defect to fix, not something the ruler should forgive.
- New **diagnostic column "located"**: overlap coefficient ≥ 0.5 and both edges within tol. It is reported next to the recall and never counts as a match. It tells you where the engine has the right place with the wrong extent.

**§11.2 Funnel rule for candidates (prefix-consistent).**
- A candidate proposed at bar i is a *right proposal* for golden g when:
  - **BOX:** both edges within tol, the candidate start within 20 min (2σt) of g's `build_start` (fallback t0), and i ≤ g.`build_end` + 10 min;
  - **line:** the two-point check on the shared span, and i ≤ g.t1;
  - **level:** price within tol, and i inside g's span.
- The reason: a candidate's window is the buildup *so far*. Judging it by full containment IoU biases the oracle ceiling low (v1 BOX oracle 0.29, against your own count of 74–86 proposals with the right edges).
- EVAL-AUDIT re-runs FUNNEL under this rule.
- **From then on the FUNNEL labels are the only source of "right proposal" counts.** Your own counts must be reconciled to them or dropped.

**§11.3 Line sigma (ruler; from LINE-LAB L1).**
- Repaired-line price σ goes from 1.5 p to **2.0 p**, because the mid-span hug is p95 = 2.0 p. The time term (|slope| · 10 min) stays.
- No point check at golden t1, as eval_v2 already does.
- The 44 Tier-A suspect lines are excluded from tuning and AUC work. They stay in the recall denominators, and trusted-subset recall (n = 141) is reported alongside.

**§11.4 What the Lead saw in the v1 renders (`504eb8ef`). Both findings are in your scope.**
- **(a) Zombie objects.**
  - On 9.23c, v1 keeps several objects alive from 12:00 to 18:00 while price trades 30–90 pips below them:
    - a box at 1.3367–1.3375 in empty space;
    - three squeeze ellipses at about 1.3345.
  - Meanwhile the afternoon golden box (14:50–17:35) and the carried level at 1.3318 are never drawn; after 14:30 there is no engine ink at all.
  - On 9.54a, 6-hour squeeze ellipses run through the whole range.
  - **Rule (DN_SALIENCE plus market Q-A):** retire an object (its ink stops, log `retire_far` / `retire_stale`) when:
    - price has stayed more than 3·ABR away for ≥ 24 bars; or
    - it has had no touch for N bars, with N chosen inside **48–96** (market: the level premium is ≈ 0 by about 5 h; PERCEPTION_IMPLICATIONS says 48–96 bars) by one logged TUNE measurement.
  - A **SQUEEZE ends when a close leaves its walls.** It is an annotation that completes a setup (RT1), not a structure.
  - Report how many rate and budget refusals disappear.
- **(b) Excursions still set box edges.**
  - On 9.54a, both engines put the box top at the 08:00 breakout thrust (about 1.2848) instead of the congestion top (about 1.2837).
  - On 9.23c, v0 puts the bottom at the 15:15 spike.
  - Check every box-family route (`asia` / RANGE_OPEN, CONTEXT_RANGE, pullback, congestion_scan). Edges come from the contained run *before* the break. A bar that closes beyond an edge by more than tol ends the window; it does not widen it (D9).

**§11.5 Market facts adopted** (DR-MARKET FINAL v2, market Ruling 4).
- Adopted for drawing:
  - age and staleness retirement, per §11.4a;
  - the selection score prefers young (< 3 h) and first-touch levels (a DN_SALIENCE term);
  - `edge_tol` 0.25–0.35·ABR is confirmed;
  - Asia H/L and PDH/PDL are *break context*, never bounce levels;
  - no EMA-touch events. EMA stays as a squeeze wall, for drawing fidelity only.
- Not adopted:
  - "news window 07:55–09:30 CET" as a hard gate. It would block the EU-open breaks Volman draws (9.54a breaks at 08:00). Tag it as an `eu_open` attribute only.
- Noted: buildup-before-break is ns in the market data. The Ruling 9a barrier features stay, because they are about *what Volman draws* (fidelity), not a predictive claim.

**§11.6 Your queue now:**
1. Finish BRACKET generation.
2. §11.4a retirement.
3. §11.4b excursion edges.
4. The Ruling 9a separator.

Report every step under the current ruler hash. When EVAL-AUDIT lands §11.1–§11.3, switch and re-baseline v0 and v1 in the same table.

## Ruling 12 (18:02Z) - new ruler hash; BOX generation to BOX-LAB; lines to LINE-LAB integration; build lane re-scoped
**§12.1 Official ruler, as of R11:**
- `evalcheck/eval_v2.py` `50e11fd5a2ab7974`;
- `evalcheck/common.py` `c6b3fa0d28713204`;
- `eval.py` `8d016922aecae265` (unchanged, imported);
- `golden/book_loader.py` `b40c2cab5c2ffe7d`.

The Lead checked the gates:
- E1 = 1.0000 on both copies;
- E2 at 1× jitter: minimum 0.949 (BOX), all types ≥ 0.9;
- `test_ruler`: all cases pass, including the 3 new R11 cases;
- the known-answer ruler suite: 7/7.

`pa_ledger.verify()` now returns `(True, None)`. The pinned exception is narrow: index 365 plus the literal digest plus a recompute check.

**§12.2 Re-baseline under this ruler** (bridge + FUNNEL; v1 = `cf2a7c1a`, which includes your bracket work). Oracle = recall if selection were perfect; born = what is actually drawn.

| type | v0 oracle / born | v1 oracle / born | gate |
|---|---|---|---|
| BOX | 0.31 / 0.21 | 0.31 / **0.05** | ≥ 0.70 |
| BRACKET | 0.73 / 0.73 | 0.62 / 0.21 | — |
| PATTERN_LINE | 0.24 / 0.11 | 0.40 / 0.08 | ≥ 0.50 |
| LEVEL_CARRIED | 0.17 / 0.17 | 0.52 / 0.15 | ≥ 0.60 |

- **BOX is capped by generation in both engines** (oracle 0.31 vs gate 0.70). No selection work can fix that.
- BRACKET, LEVEL_CARRIED and PATTERN_LINE in v1 have real proposals that are never born. That is selection.

**§12.3 Ownership changes:**
- **BOX generation moves to a new sandbox lane, BOX-LAB** (`research/perception/boxlab/`), on the LINE-LAB pattern: audit → anatomy → prototype → integration note. It owns box *proposal geometry*: routes, edges, start and draw moment. **§11.4b (excursion edges) moves there.**
- **Lines:** LINE-LAB's `LINE_INTEGRATION.md` is accepted, and LINE-LAB integrates it itself (mandate `linelab/MANDATE_LINE_LAB_2.md`).
  - **During integration LINE-LAB owns `lines.py` and the `pattern_line` / `context_line` sections of `params_v1_1.json`.** Do not edit them.
  - For any param edit, by anyone: str_replace-style edits only, never a whole-file rewrite. Two lanes share this file.

**§12.4 Your queue (replaces §11.6):**
1. Log "rulings read up to R12" now.
2. Finish BRACKET: close the selection gap (oracle 0.62, born 0.21) without losing v0's 0.73 coverage.
3. §11.4a retirement: zombie objects, and a SQUEEZE ends when a close leaves its walls.
4. The LEVEL_CARRIED selection gap: 0.52 → 0.15, with 17 rate-limited refusals.
5. Selection (R9a):
   - use EVAL-AUDIT's FUNNEL prefix labels as the only source of "right proposal";
   - start from the honest finding that the current birth score has AUC 0.53;
   - LINE-LAB found `age_min` to be the only fold-stable line feature (AUC 0.73–0.85). Test the analogous structure-age feature for your types, along with the barrier features.
6. B5/B6 come later, once v1 ≥ v0 on BOX/BRACKET under this ruler.

`pa_slots`: **at most 1** for you while 4 lanes run.

**§12.5 Discipline, all lanes:**
- **No deletes, not even of your own derived artifacts.** EVAL-AUDIT deleted `labels_v1_504eb8ef53e5c492.jsonl` at 17:58Z. That was a wall breach; the engine state behind it is gone, so the file cannot be regenerated. Superseded files stay where they are.
- **Log times come from the clock.** EVAL-AUDIT wrote "~18:00Z" and "~18:05Z" entries into a file saved at 17:57Z. A log line records when something happened, never when it is expected to happen.

## Ruling 13 (18:43Z) - box ceiling = generation; snapshot is the second lens; lines accepted; features amended by evidence
**§13.1 BOX_CEILING is accepted. The ceiling is set by generation, and the start rule stays.**
- BOX-LAB X1 measured the labels' start precision directly: `t0 − build_start` median 0 (p10 −15 min); `first_touch − build_start` median +5 min. So the funnel's ±20-min start rule matches what the labels support. It is not over-strict.
- EVAL-AUDIT found the rest: v1 has 36/77 misses with **no candidate within 2× tol at all**, and v0 has 32 "right edges, wrong start". Across both engines, **the nearest candidate is proposed about 45–55 minutes after the golden `build_end`, i.e. after the break.** The engines recognise a box only once it is over.
- The containment-IoU match rule for born objects (§11.1) is unchanged.

**§13.2 Snapshot is the second official lens.** Report it next to the cumulative numbers, always. From SNAPSHOT.md:
- at the golden author's decision moments, the engines have a **median of 12 (v1) to 18 (v0) live objects**, against about 2.7 per golden panel;
- snapshot precision is 0.03;
- snapshot BOX recall is v0 0.14, v1 0.01.

**Clutter is the whole-engine problem.** Every engine change now gets a `evalcheck/scoreboard.py` row. The build lane runs it after each change, and the labs run it on their prototypes.

**§13.3 LINE-LAB's L5 integration is accepted** (VERIFY_LOG CONFIRMED).
- PATTERN_LINE recall 0.08 → 0.11; trusted-subset 0.08 → 0.12; precision up; line ink down 42% vs v0. 34/34 tests pass. The fixture changes are logged with their intent. The T1 known-answer test asserts at the proposal layer, with the reason recorded and REQ-1 filed. Accepted.
- Noted: the PL oracle fell 0.40 → 0.36 (the ≥ 3-touch gate removed some right proposals), and LEVEL_CARRIED fell 0.15 → 0.12 (`broken_line_edge` candidates now share `rate_level_carried`). The build lane owns the LEVEL_CARRIED item.
- **REQ-1 is approved in principle, variant (b) only.** A re-proposal that revives a closed same-geometry structure must not spend a birth slot, because it is not new ink.
  - The build lane implements it in the salience rate accounting.
  - **Rate caps are not raised.** Raising them buys recall with volume (D16, D18).
- REQ-2 (candidate TTL) is deferred.

**§13.4 R9a feature list amended by BOX-LAB's anatomy evidence.**
- **Dropped:**
  - compression: the median in-box bar range is 1.08× ABR, so boxes are not tighter tape;
  - EMA guidance: the EMA sits inside the box 48/67 times.
- **Kept:**
  - pre-existing barrier: about half of breakout edges were a level before the window;
  - pivot prominence: the build lane measured `prom_abr` at AUC 0.75 within-window on BOX;
  - structure age.
- **Added:** late-window close lean toward an edge. It is causal when "toward an edge" means whichever edge the closes lean to, never the side that later breaks.
- The AUC protocol is unchanged (≤ 4 features, every fold ≥ 0.60, equal-weight ranks).
- The anatomy's generation blueprint goes to BOX-LAB X3:
  - edges are confirmed pivot extremes (the extreme with company);
  - the start is the anchor pivot's `t_ext`;
  - emit when both edges show defence and there are K contained closes. That lands about 15–25 min *before* `build_end`.

**§13.5 Integration plan for boxes.** When X3 reaches its oracle target, or its best after 4 rounds, **BOX-LAB integrates into `boxes.py` itself** and owns box proposal geometry during integration, as LINE-LAB did for lines. The build lane keeps salience and lifecycle. The Lead will rule when X4 lands.

**§13.6 Build lane, now:**
- post the zombie-retirement delta (eval_v2 plus a scoreboard row, snapshot live clutter included);
- then REQ-1 (b);
- then the LEVEL_CARRIED gap;
- then selection with `prom_abr`, structure age and late-close lean on the FUNNEL labels.

**§13.7 Walls check.** Replace file-level exemptions (e.g. `BARS_CACHE_EXEMPT`) with positive checks:
- the file must import `book_loader`, or `evalcheck/cache.py`;
- it must not open parquet or csv bar paths directly;
- HOLD-string matches are ignored only on comment or docstring lines.

EVAL-AUDIT does this in mandate 4.

## Ruling 14 (18:52Z) - clock stamps come from a command; paired A/B for every delta; lifecycle judged on the snapshot

**§14.1 Clock. Third time, so now it is mechanical.**
- PERCEPTION_LOG has entries stamped **18:45Z** and **18:55Z**. The system clock says the file was last written at **18:42:24Z**, so those stamps were up to 13 minutes in the future.
- The Lead did the same thing. `evalcheck/LEAD_NOTE_R13.md` says 18:47Z in its header, but the file was written at 18:44:47Z. A correction line has been appended to that note.
- This is the third occurrence (§9.4, §12.5). Rules have not fixed it, so a tool will.

Effective now, for every lane and for the Lead:
1. Every time written in a log, note, ruling or report is copied from a command run in the same step. The tool is `research/perception/tools/logline.py` (stdlib only):
   - `python "03. EA Developer/PA_Pro/research/perception/tools/logline.py" <log> "text"` takes `- HH:MMZ` from the system clock and appends the entry itself. For multi-line text use `@file.txt`.
   - `... logline.py --now` prints the time only.
2. A time you plan, rather than one you observed, is written as "plan ~HH:MMZ".
3. Wrong stamps already written stay where they are. Append a correction line under them. **Build lane:** correct the 18:45Z and 18:55Z entries this way.
4. **EVAL-AUDIT** adds a `clock` check to `walls_check.py` (part of W4). It checks the entry stamps in the last 40 lines of every `*_LOG.md`, plus the header stamps of `LEAD_NOTE*` and `LEAD_RULINGS`. A stamp is a **FAIL**, naming the file and line, if it is later than the file's mtime + 2 min or later than the check time. Plan-labelled times are ignored. The Lead runs this check at every check-in.

**§14.2 Paired A/B for every delta.**
- Three lanes edit engine files at the same time. Between 18:30Z and 18:49Z the v1 engine hash changed four times: 694313a3 → c3165fcd → ebf320a2 → ef06f265.
- A before/after table taken at two different times therefore mixes in other lanes' edits. The retirement table in PERCEPTION_LOG (BRACKET 19→16, LEVEL 9→7, clutter 4.33→4.58) cannot be attributed yet.

The rule:
- Every delta a lane reports is a **paired A/B at one code state**. Both arms run back-to-back, and the only difference between them is the lane's own switch (a params flag or an override). Both rows go into the scoreboard.
- Scoreboard rows gain two fields, `lane` and `variant`. EVAL-AUDIT adds them to `scoreboard.py`; old rows keep them blank.
- **The variant must be part of the run-cache key.** Otherwise `evalcheck/_cache` (keyed by engine hash) will serve arm A's runs to arm B. EVAL-AUDIT makes this change and adds a test for it.

**§14.3 Lifecycle (zombie retirement) is judged on the snapshot lens.**
- Retirement exists to take dead ink off the screen at the moments the author decides.
- It is expected that the cumulative born count rises a little, because freed slots allow new births. That is not a reason to reject retirement.

Report per rule (far / stale / wall-exit), as a paired A/B:
- the number of retirements;
- **bad retirements**: the retired object matches a golden object (by the ruler's geometry rule) whose span runs ≥ 3 bars past the retirement bar;
- snapshot live clutter median, and snapshot recall per family;
- cumulative recall per family.

The decision rule:
- A rule stays if snapshot clutter falls **and** its bad retirements are ≤ 10% of its retirements.
- Otherwise, narrow it once and re-measure. One candidate narrowing, if the LEVEL losses come from retire_far: exempt level-family objects with ≥ 2 defended touches from retire_far, and keep stale (48–96 bars) as their only exit.

**§14.4 Lanes do not debug each other.**
- If a test fails in a file you do not own:
  - log the test name, the first traceback lines and the engine hash;
  - write one line in the owner lane's REQUESTS file or log;
  - carry on with your own work.
- Owners:
  - `engine.py`, salience and lifecycle params → build lane;
  - `lines.py` and line params → LINE-LAB;
  - `boxlab/*` (and box proposal geometry in `boxes.py` once §13.5 integration is ruled) → BOX-LAB;
  - `evalcheck/*` → EVAL-AUDIT.

**§14.5 Cadence and the morning.**
- Every lane logs at least every 45 min, through `logline.py`, and acks rulings by number ("rulings read up to R14").
- **LINE-LAB:** your last LINE_LOG entry is 17:59Z. Your work since then shows only in stdout. Log now.
- **EVAL-AUDIT:** W0 comes before W1 (LEAD_NOTE_R13). `W0_BOX_WINDOW.md` is due by **19:30Z**, because the morning pack's BOX numbers depend on it.
- By **00:15Z**, every lane's latest log entry is a one-screen status covering:
  - what is measured, with hashes;
  - what is not measured yet;
  - the next step.

  The Lead builds the Owner's gate pack from these entries at about 00:30Z.

## Ruling 15 (19:00Z) - LINE-LAB mandate 2 accepted; LEVEL_CARRIED moves to a new LEVEL-LAB; REQ-1 restated; gate definitions for the morning pack

**§15.1 LINE-LAB mandate 2 is accepted.** The job ended cleanly at 18:53Z with its queue complete.
- **L6:** the salience cut is quantified. 70–76 of about 125 right line proposals die `rate_limited`, and 34 expire.
- **L7:** the θ1 terminal anchor is kept, second-class via the two-pass `_scan`. The oracle rose 0.36 → 0.38 and trusted recall to 0.135, at +8% proposal volume. The failed argmax variant was measured and dropped.
- **L8:** an honest negative. On the production proposal stream no candidate feature reaches AUC 0.60 on every fold. `age_min` scored 0.81 on the lab pair-dump but only 0.51 on production.
- The lane wrote its own attribution caveat: concurrent `engine.py` edits mix into its hash deltas. That caveat is exactly why §14.2 exists.

**Lesson, now a rule for every lab:** a feature counts only after it is measured on the **production proposal stream** (funnel prefix labels). An AUC measured on a lab stream is a hypothesis, not evidence.

**§15.2 LEVEL_CARRIED moves from the build lane to LEVEL-LAB.**
- LEVEL-LAB is LINE-LAB's session (sprout-duchess) under a new mandate: `research/perception/levellab/MANDATE_LEVEL_LAB.md`.
- Why: it is a charter gate (recall ≥ 0.60). On v1 `ef06f265` the numbers are golden 48, oracle 0.50, born 0.13–0.15. The gap is mostly selection, and the lane that caused part of it (`broken_line_edge` now shares `rate_level_carried`, §13.3) knows that interplay best.
- LEVEL-LAB works only in `levellab/` until the Lead rules on integration. It then owns `levels.py` and the level params during integration, as LINE-LAB did for lines.
- **The build lane's queue is now:**
  1. the retirement paired A/B (§14.3);
  2. REQ-1 (b);
  3. selection with `prom_abr`, structure age and late-close lean. Measure every feature on the FUNNEL labels, per §15.1.

**§15.3 REQ-1, restated.**
- **(a) Raising `rate_pattern_line` stays refused.** L6 proves the cap binds. L8 also proves that nothing yet separates right proposals from wrong ones (AUC ≤ 0.56). A higher cap would therefore buy recall with junk volume (D16, D18).
- **(b) The revive exemption stays in the build lane's queue as item 2.** The build lane reports, as a paired A/B, how many of the rate-limited right proposals are revivals, i.e. what (b) can recover.

**§15.4 Gate definitions for the morning pack.** The HOLD gates are in `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md` §6.1:

| Gate | Threshold |
|---|---|
| BOX recall | ≥ 0.70 |
| BOX precision | ≥ 0.60 |
| PATTERN_LINE recall | ≥ 0.50 |
| LEVEL_CARRIED recall | ≥ 0.60 |
| LABEL_TF agreement on matched boxes | ≥ 0.60 |
| Clutter **ratio** (engine count ÷ golden count, per panel) | median ≤ 1.5 |
| Edge stability | no unlogged edge move |

- The scoreboard's "clutter" column is the median **live count**, not this ratio. GATE_PACK reports the ratio for the gate and the live count as a diagnostic, on both lenses.
- LABEL_TF is measured only on matched boxes, so it cannot be read meaningfully while BOX recall is near 0.06. GATE_PACK says so, with its n.
- The spec allows a gate revision before HOLD is scored, but only with TUNE evidence. That is the route for any option B the Owner may choose.

**Reproducibility: two EVAL-AUDIT tools disagree on the same hash `ef06f265`.**

| Quantity | SCOREBOARD | FUNNEL |
|---|---|---|
| PATTERN_LINE oracle | 0.397 | 0.375 |
| LEVEL_CARRIED born | 0.125 | 0.146 |

EVAL-AUDIT reconciles them, or documents the definitional difference, before GATE_PACK. Every number in the pack must trace to one tool and one hash.

## Ruling 16 (19:24Z) - build lane stopped and resumed (again); a reverted experiment in the scoreboard; handoffs; what the displacement test proves

**§16.1 The build lane was stopped at 19:23Z and resumed (resume 6).** The reason is the same as at 18:18Z:
- no "rulings read" entry since R12 at 18:20Z;
- a log silent for 41 minutes;
- it had started LEVEL_CARRIED work in `salience.round()` (an "armed-carry" gate). §15.2 moved that item to LEVEL-LAB.

The work itself was good. Its findings are to be logged now, with hashes.

The build queue order is now:
1. **context-class births.** CONTEXT_LINE is born 267 times against 9 golden, and CONTEXT_RANGE 215 against 6. Together they take about 18% of the joint `rate_total` budget;
2. retirement paired A/B;
3. REQ-1 (b);
4. BOX selection with `prom_abr` and box height.

**§16.2 EVAL-AUDIT, at your next item boundary.** Do not interrupt judge sub-agents that are already running.
- **Rulings:** your last "rulings read" entry is R12 at 18:06Z. Log "rulings read up to R16".
- **The `97cc437f` scoreboard row** (BOX .15, PL .19, live clutter 15) is very likely the build lane's rate-window displacement experiment. The lane rejected that experiment for D18 churn (BOX births 962) and reverted it.
  - Append a line to SCOREBOARD marking `97cc437f` as a reverted experiment. It is append-only, so do not delete the row.
  - **Never use it in GATE_PACK.**
  - This is exactly why §14.2 requires `lane` and `variant` fields. Add them now.
- **W0 is due at 19:30Z and has not started.** Do it next, before any more W2 work.
- **Still owed:**
  - in W4: the §14.1 clock check and the §14.2 variant cache key;
  - in W2: the §15.4 gate definitions and the reconciliation of SCOREBOARD with FUNNEL.

**§16.3 Handoffs.** The build lane writes `research/perception/HANDOFF_BUILD_TO_LEVELLAB.md`. It contains:
- the `session_extreme` route: 990 proposals, 12 right, 0 born;
- the golden `raw_note` semantics ("old breakout base / congestion top projected / neckline");
- `ret_24`: price returns to the level within 24 bars of the proposal. On production labels it scores AUC 0.645 overall; folds run 0.61–0.73, and one fold had no positives. That is a birth-on-return candidate.

**LEVEL-LAB** re-measures it under the protocol (every fold ≥ 0.60; a fold with too few positives is inconclusive, not a pass). If it holds, request the gate as REQ-L2 with a lab paired A/B. Salience gates are implemented by the build lane.

**§16.4 What the displacement test proves.**
- When a strong candidate was allowed to take the weakest incumbent's slot, matched objects rose: BOX 5 → 16, BRACKET 16 → 22, lines 18 → 35. Births exploded at the same time.
- So **the right objects are already proposed; the engine cannot tell them apart from the wrong ones in time.** Selection, not only generation, is the bottleneck.
- The only causal separators measured so far on production streams are:
  - `prom_abr` for boxes (AUC 0.75 within-window);
  - box height (golden boxes are short; 0.66 inverted, BOX-LAB lab stream, to be confirmed on production);
  - `ret_24` for levels, which is provisional.
- BRACKET and lines have honest negatives.
- This finding goes into the Owner's morning pack.

## Ruling 17 (19:39Z) - LEVEL-LAB's gain is coverage bought with ink; selection at the author's budget is now the program's core measure; negative controls for the judge

**§17.1 LEVEL-LAB V1–V7: accepted as analysis and as a coverage result.** The work was fast and honest; the dead-end rounds were kept on record.

What the anatomy found:
- The author's levels are **old, defended pivots**. θ2 accounts for 41% (LC) / 50% (MINI), θ1 for 28% / 11%, and session/Asia extremes for about 20–29%.
- **Prior-day high/low: zero matches.** Round numbers fall below the grid's base rate, so the author does not pick them.
- The **draw trigger is approach**: at τ the level is a median 1.6 ABR from price, and it has been knowable for about 6 hours. 85% / 79% of levels have ≥ 3 prior defences.

What the lab proposer achieved:
- LC oracle 0.50 → **0.79**.
- Born recall 0.146 → **0.542** (trusted subset 0.650).
- MINI 0.065 → 0.61.
- Live levels at τ: median 4.

**But the recall gain is volume, not selection:**
- Born precision is **0.033 in the lab vs 0.027 in the engine**, so the hit rate per level drawn has not changed.
- The lab births about 9 levels per panel (LC ~5 + MINI ~4). The engine births about 1.3 LC per panel. The author draws about 2 objects per panel in total.
- Per unit of ink, LC recall is about 0.11 per born LC per panel in both the engine and the lab.

So the integration as proposed (+~3 levels per panel) would lift LC recall by adding ink, which is the D16/D18 trap. The clutter ratio is already about 8× golden against a gate of 1.5. **Integration is not ruled yet.** REQ-L1 (family floor) is deferred as well.

**§17.2 LEVEL-LAB next: V8, selection at the author's budget.**
- **Recall@k:**
  - keep only the top-k levels live at each τ (snapshot lens), for k = 1, 2, 3;
  - also cap cumulative births at 1, 2, 3 and 5 per panel.

  Report recall with CIs for LC and MINI, and the trusted subset.
- **Compare three proposers at matched ink:**
  - (a) the lab proposer, ranked by its score;
  - (b) the current `levels.py` routes with the rate caps removed, ranked by their own score (from the funnel labels);
  - (c) a naive baseline: every θ1/θ2 pivot with ≥ 2 defences, ranked by distance to price.
- **Ranking features to try:**
  - approach distance, defence count, age and origin class;
  - `ret_24` / birth-on-return (from HANDOFF_BUILD_TO_LEVELLAB §3);
  - "next barrier in the direction of travel": the first level price would hit next;
  - cross-family dedup: a level already carried by a live box edge or line.
- **Integration condition:** the lab proposer earns integration only if it beats both (b) and (c) at k ≤ 2 live levels per τ. If it does, write the integration diff with a live budget (e.g. ≤ 2 levels at a time) instead of raw births.

**§17.3 Selection at the author's budget is now the core measure of the program.** Every lab has now shown the same thing:
- **Coverage is solvable.** Labs reach oracle BOX 0.56, PL 0.41 and LC 0.79.
- **Selection is not solved.** Nothing yet picks the 2–3 structures the author draws.
  - On production streams no candidate feature separates right from wrong for lines, levels or brackets.
  - For boxes, only `prom_abr` (0.75) and box height (0.66 inverted) are promising.
  - The build lane's displacement test showed that right objects are already proposed and simply lose the race.

**EVAL-AUDIT adds a recall@k table to GATE_PACK.** For each engine:
- keep only the top-k live objects at each τ, for k = 1, 2, 3 and 5. Rank by the engine's own salience score if objects carry one, otherwise by recency, and say which;
- report recall per family plus snapshot recall.

This is the Owner's question in numbers: at the ink a pro uses, how much of what the pro draws does the engine show?

**§17.4 EVAL-AUDIT**
- **The R16 items stand.** `97cc437f` is the reverted displacement experiment.
  - GATE_PACK must be regenerated with the **live** v1 hash.
  - The VERIFY_LOG entry at 19:13Z ("BOX recall tripled … CONFIRMED improvement") needs a correction line saying it measured a reverted experiment.
- **W0 is now overdue.** It was due at 19:30Z.
- **W1 needs negative controls.** The Lead's preliminary count of the 135/150 judged items:

  | Item group | Judged plausible |
  |---|---|
  | Golden controls | 27/30 (0.90) |
  | Golden misses | 22/24 (0.92); knowable 0.92 |
  | Engine FPs, v0 | 22/30 (0.73) |
  | Engine FPs, v1 | 15/21 (0.71) |
  | Engine FPs, linelab | 24/30 (0.80) |

  Without negatives the judge's specificity is unknown: a lenient judge would call everything plausible.
  - **Build 30 negative controls** that are causally wrong:
    - golden objects shifted by 3–5 ABR in price, or by about 2 h in time, onto places with no structure;
    - lines through non-pivot points;
    - boxes spanning a trend leg.
  - Have them judged blind, in fresh batches, by fresh judges using the same grammar and format.
  - Report the judge's sensitivity (golden controls) and specificity (negatives).
  - Report the corrected plausible share of FPs by Rogan–Gladen, (p_obs + spec − 1) / (sens + spec − 1) clipped to [0, 1], with CIs.
  - **If specificity is below 0.70, the plausibility result goes into the pack as unreliable.**

**§17.5 BOX-LAB stopped and resumed.** BOX_LOG has been silent since 18:29:44Z (70 min) and there are no ROUND files, although the stdout shows several X3 rounds (oracle 0.556 at one point; break-triggered birth; a birth-edge rule). The resume prompt asks it to:
- read R13–R17;
- log through `logline.py`;
- write a ROUND file for every round done, with numbers and hashes;
- then continue X3.

Inputs now available to BOX-LAB:
- `levellab/NOTES_FOR_BOXLAB.md` (a causal barrier registry for pre-existing walls);
- box height (golden boxes are short);
- `prom_abr`;
- the §17.3 recall@k framing. BOX-LAB's own target is already "born > 0.21 at ≤ 2 boxes per panel".

**§17.6 Build lane.** Resume 6 did everything asked in steps 1–3 and 5:
- ack;
- correction line;
- findings with hashes;
- handoff.

Still open:
- the candidate-expiry extension (`b870074c`) stays only if its paired A/B holds;
- scoreboard rows `cb2794f5` and `1f4bed5b` (19:31Z / 19:33Z) show exactly ef06f265's numbers. Label them in the log: which arm and which variant. If the numbers are identical because `_cache` served an old run, say so; that is the §14.2 cache-key bug.

## Ruling 18 (19:55Z) - context sub-cap accepted; the keep-rule restated as "recall at equal ink"; EVAL-AUDIT and LEVEL-LAB stopped and resumed; code freeze for the morning pack

**§18.1 Build lane: context sub-cap accepted (arm B, `54756075`).** The paired A/B was clean: four arms at one code state, params inside the hash, scoreboard rows labelled.
- **B** (`rate_context` 2 per 288 bars): BRACKET 18 → 25, and no other family lost anything. Snapshot recall .084 → .096 at the same live clutter (10). Context births fell 16%.
- **C** gained more BRACKET (35) but lost PATTERN_LINE −2 and BOX −1, both gate families, at live clutter 11. B is the right choice.

**The keep-rule is restated for every lane.** A change is kept when:
- recall rises at **equal or lower ink** (neither the clutter ratio nor the live clutter median goes up);
- no family loses more than one matched object.

The earlier wording ("clutter ratio falls") was too narrow. More right objects for the same ink is exactly the selection progress the program needs (§17.3).

**The candidate-expiry extension** (`cb2794f5` off vs `1f4bed5b` on) shows identical scoreboard rows. Unless the per-family counts show a real gain, **revert it.** It is TTL-adjacent, and REQ-2 is deferred. Log the decision with the counts.

**Code freeze.**
- Whenever the suite is green and params provenance is valid, log "STABLE `<hash>`".
- At about **00:05Z**, stop editing engine files and log the final STABLE hash in your one-screen status.
- No engine edits between 00:05Z and the Lead's morning ruling, so that EVAL-AUDIT can measure one fixed engine for the Owner.

**§18.2 EVAL-AUDIT stopped and resumed (resume 5).**
- **Why:** its last "rulings read" was R12 at 18:06Z, so it missed R13–R17:
  - W0 is still not done (due 19:30Z);
  - W1 has no negative controls;
  - no recall@k table;
  - §15.4 gate definitions and the reconciliation are not done.
- **Credit:** W1 completed properly: 150/150 judged, three non-blind batches rejected, and a rendering bug fixed before judging. It also corrected the `97cc437f` row on its own at 19:47Z.
- **The resume prompt sets the order:**
  1. W0;
  2. negative controls with sensitivity, specificity and a corrected plausible share;
  3. recall@k;
  4. definitions and reconciliation;
  5. the W4 remainder;
  6. the final GATE_PACK on the frozen hash, 00:15–00:35Z.

**§18.3 LEVEL-LAB stopped and resumed (resume 4).**
- **Why:** it has not read R17. Since then it has been sweeping its own config for recall (`min_score` 1.5 → LC 0.688; trying 1.0/1.2, `min_defences` 1, `approach_abr` 2.5, leg origins). This is recall bought with ink, and in-sample selection over about 48 objects. R17 §17.2 (V8) comes first.
- **Wall breach:** its stdout says it deleted a variant file ("xóa file variant", about 19:5xZ). The mandate says **no deletes, not even your own files.** Log what was deleted. Do not repeat.
- **From now on:**
  - every lab number carries its ink (births per panel and live levels at τ);
  - config choices are validated by **day-level 5-fold CV** (choose on 4 folds, score on the 5th). The in-sample best is not a result.

**§18.4 BOX-LAB.** ROUND_X3 is honest and useful:
- oracle .556 (trusted .662);
- born .019 at about 2 boxes per panel, versus .352 at 37.6 per panel in r1. That is recall bought with ink, stated plainly;
- the day cap is shown to be the wrong budget.

The r17 plan is approved: live budget ≤ 2 with score displacement, birth at the knowable moment, and a barrier term.
- **Displacement inside a live budget is acceptable in the lab as a ranking measurement** (recall@k).
- Report births per panel and **flicker** next to it: how often the live top-k set changes per hour. A pro does not redraw every bar, so a design that churns cannot be integrated even if its recall@k is good.

**§18.5 Morning schedule.**

| Time | Who | What |
|---|---|---|
| ~00:05Z | Build lane | Code freeze, final STABLE hash |
| ~00:15Z | Every lane | One-screen status |
| 00:15–00:35Z | EVAL-AUDIT | Final GATE_PACK and PLAUSIBILITY on the frozen hash, including recall@k and judge sensitivity/specificity |
| ~00:45Z | Lead | Owner pack |

## Ruling 19 (20:09Z) - W0 closed with no ruler change before the morning; retirement kept; LEVEL-LAB may integrate behind a flag with a live budget; deletes are quarantines

**§19.1 W0 is accepted. The ruler stays frozen (`eval_v2` `50e11fd5`) through the Owner's decision.**
- **The 9.54a MISS is real.** The object the Lead read as "the same box" is a RANGE_OPEN. Its containment IoU is 0.77, a pass, but its low edge is 1.9 p from a *repaired* golden edge with a 1.5 p tolerance. The ruler did its job; the Lead's visual read was wrong.
- **The semantic gap is real.** Engine `meta_build_end` is the proposal time, while golden `build_end` sits next to the break.
- **The proposed conversion to `bs..break_bar` would add only about +2 of 108 boxes.** It is **not adopted before the morning pack.** GATE_PACK notes it as a known ruler caveat: "v1 BOX windows use proposal-time ends; conversion to break-time ends would move BOX recall by about +0.02 (net not yet measured)".
- **Correction to W0 §4.** The claim that the conversion is "monotone-safe, IoU only grows" is false. Extending an engine window past the golden `build_end` enlarges the union without adding intersection, so IoU can fall and an existing match can be lost.
  - If the conversion is proposed again, report **net** gains and losses.
  - EVAL-AUDIT: append a correction line under W0 §4. Do not edit the original text.

**§19.2 Build lane.**
- **Extension:** the flag-only A/B shows zero delta, so the flag stays OFF, and the earlier "gain" was harness noise. Honest and correct.
- **Retirement:** the per-rule A/B gives 0 bad retirements for every rule. Live clutter at τ is 10 with retirement vs 11 without. **Keep all three rules.** R14 §14.3 is the specific rule for lifecycle and it governs here.
  - The cost is PATTERN_LINE 22 → 19. This comes from freed budget being re-spent on other births (selection again), not from bad kills. It goes into the pack as a noted cost.
- **Breach.** The log says "deleted" for the polluted cache runs `run_1f4bed5b_*`. That is a delete, in another lane's folder (`evalcheck/`).
  - **No lane deletes anything, ever.** A polluted or unwanted file is *moved* into a `_quarantine/` subfolder of its own directory, and the move is logged. If it is in another lane's folder, that lane is told through its log or REQUESTS.
  - EVAL-AUDIT: check `_cache` for other truncated-key entries, and make the §14.2 variant/cache-key fix a priority, since a cache that can serve the wrong arm is a measurement hazard for the morning.
- **Next:** REQ-1 (b), then BOX selection with `prom_abr` and box height, measured on the production FUNNEL labels. BOX-LAB's lab-stream `-hgt` of about 0.686 is not fold-stable and is not yet evidence. Then log STABLE hashes and freeze at about 00:05Z.

**§19.3 LEVEL-LAB V8. Integration is authorized behind a flag with a live budget.**
- **The measure** is recall at the author's budget: LC recall with the top 2 live levels at τ, under day-level 5-fold CV.
- **Result:** lab 0.267 > production 0.208 > naive 0.203. The R17 condition is met on point estimates. The margin is small (about 3 objects of 48), so the CI must be reported.
- **Conditions:**
  1. **Scope:** `levels.py` and the level params only, str_replace with provenance. The route is behind a flag, **default OFF**.
  2. **Budget inside the proposer:** the live budget is enforced inside `levels.py`, so the new route proposes at most 2 live levels at a time, ranked by the CV-chosen ranker. Salience then never sees more than 2 from it. Anything that needs `salience.py` goes through REQUESTS to the build lane.
  3. **Evidence in ROUND_L7:**
     - a paired day-bootstrap CI for (lab − prod) and (lab − naive) at k = 2;
     - if a CI includes 0, the pack labels the integration "weak evidence";
     - state that the proposer config (`min_score` and so on) was chosen in-sample before V8, so CV covered the ranker only.
  4. **Engine-level paired A/B** at one code state, flag ON vs OFF. The flag goes default ON only if it passes the R18 keep-rule: recall up at equal or lower ink (clutter ratio and live clutter), and no family losing more than one matched object.
  5. **Deadline:** the A/B is complete and logged by **23:30Z**. Otherwise the flag stays OFF, and the code state freezes with the build lane's freeze at about 00:05Z.
  6. **Tests:** the suite stays green. Report the counts before and after.
- **`ret_24`:** folds 0.612 / 0.651 / 0.702 / 0.526 / 0.558, so it is not a clean separator. **No REQ-L2 gate.** It may stay as a ranking input inside the CV'd ranker.
- **The confessed delete** (`levels_lab_gt.py`, `levels_lab_xs.py`) is noted, and the honesty is noted too. Quarantine from now on (§19.2).

**§19.4 For the pack.** GATE_PACK adds LEVEL-LAB's V8 recall@k table next to the engine recall@k, labelled "lab, TUNE, CV". Every engine number comes from the frozen STABLE hash.

## Ruling 20 (20:23Z) - REQ-1(b) off by the keep-rule; timing, not score, decides selection under FCFS caps; LEVEL-LAB resumed to integrate; build lane's last items before the freeze

**§20.1 REQ-1(b), the revive exemption, defaults OFF.**
- The paired A/B (`03917fd5` off vs `03dbe495` on) is clean:

  | Measure | Off | On |
  |---|---|---|
  | BOX | 6 | 9 |
  | BRACKET | 25 | 32 |
  | LC | 6 | 5 |
  | Snapshot recall | .096 | .109 |
  | **Live clutter at τ** | **10** | **12** |
  | **Clutter ratio** | **4.50** | **5.00** |

- The R18 keep-rule is "recall up at **equal or lower** ink". It fails on ink. The R13 premise ("a revival is not new ink") is refuted by the lane's own measurement: a revived object is ink on the chart at τ.
- **The Lead's rules bind the Lead too.** The flag defaults OFF for the freeze and the code stays dormant.
- The measured trade-off goes into the Owner's pack as a **lever**: +3 BOX and +7 BRACKET for +2 live objects.
- The lane was right to flag it rather than hide it.

**§20.2 BOX selection: `prom_abr` is real but does not move recall. The reason matters.**
- `prom_abr` separates right from wrong on the production stream: AUC 0.743, folds 0.70–0.79. It is the program's first fold-stable causal separator.
- **Box height fails on production** (0.524, worst fold 0.36). BOX-LAB's lab-stream "golden boxes are short" does not reproduce, which confirms the §15.1 rule.
- **Weighting `prom_abr` into the score changed nothing:** BOX 9/9, with LC −1 and MINI −1, so it was reverted.
- **Why:** under first-come-first-served rate caps, a candidate's fate is decided by **when** it arrives (is the window already full?), not by how it scores. A score only matters when candidates compete at the same moment.
- **Therefore:** selection needs a **live budget with displacement by score**, i.e. a fixed number of live slots per family where a stronger candidate evicts the weakest, bounded by a flicker limit. It should be measured on the snapshot / recall@k lens.
  - LEVEL-LAB's `_budget_ok` and BOX-LAB's r17 plan are both prototypes of this.
  - The earlier displacement test (R16 §16.4) was rejected on **births** (D18). A live budget changes the lens from births to what is on screen at τ. The Owner decides in the morning which lens defines success.

**§20.3 LEVEL-LAB resumed (resume 5).** The lane ended at 20:21Z after V8, before reading R19.
- **V8 is accepted.**

  | Measure (CV) | Lab | Prod | Naive |
  |---|---|---|---|
  | LC@2 | .267 | .208 | .203 |
  | MINI@2 | .264 | .082 | .137 |

  - At k = 1 the lab loses (.107 vs .171), stated honestly.
  - The folds are very noisy: lab LC@2 per fold .10 / .33 / .00 / .40 / .50.
- **Its task now is R19 §19.3:**
  - flagged integration, default OFF, with the live budget 2 LC + 1 MINI inside `levels.py`;
  - engine-level paired A/B by 23:30Z under the keep-rule;
  - the paired day-bootstrap CI for (lab − prod) at k = 2;
  - also report **flicker** (changes of the live level set per hour) and births per panel. At 2+1 the lab still births about 9 per panel, and evictions plus revivals are churn.
- **Answer to the lane's question** (charter metric: born recall or recall@τ): **report both for every arm.** The charter gate is born recall (spec §6.1) until the Owner decides otherwise. Do not trade one for the other silently.

**§20.4 Build lane: the queue is done. Last items before the freeze, in order.**
1. **Set REQ-1(b) OFF** (§20.1). Log "STABLE `<hash>`" once the suite is green.
2. **Expose each live object's salience score** in the engine output, so EVAL-AUDIT's recall@k can rank by the engine's own score instead of recency. This is output only, with no behaviour change. Confirm with a paired identity check (all recall numbers identical).
3. **Flagged prototype, default OFF regardless of result: `live_budget`.**
   - At most k live objects per signal family (BOX, BRACKET, PATTERN_LINE, levels) at any moment.
   - A stronger candidate (by the current score) evicts the weakest live member.
   - Evicted objects close as `superseded`.
   - Bound flicker with a minimum dwell (e.g. ≥ 6 bars before an object can be evicted).
   - Measure k = 2 per family against the frozen default, as a paired A/B. Report:
     - cumulative recall per family and births per panel;
     - snapshot recall and live clutter;
     - recall@k;
     - flicker (changes to the live set per hour).
   - This answers the Owner's core question with numbers: "if the engine may swap objects the way a pro redraws, how much of the pro's chart does it show at the pro's ink?"
   - Timebox: by 23:45Z. If it is not measured by then, log it as not done.
4. **Freeze at about 00:05Z** with the final STABLE hash and the one-screen status.

**§20.5 EVAL-AUDIT.**
- Recall@k goes in GATE_PACK for:
  - v0;
  - v1 at the frozen hash;
  - two **levers**, each clearly labelled as a lever and not as the engine: revive ON (`03dbe495` vs `03917fd5`), and `live_budget` ON if the build lane delivers it by about 23:45Z.
- When the engine exposes salience scores (§20.4 item 2), rank by them.
- The W1b negative controls remain the priority before recall@k.

## Ruling 21 (20:38Z) - full review; boxes must stay drawn after the break; build queue order to the freeze; BOX-LAB resumed (again)

**§21.1 Full review at 20:37Z.**
- Seals: f0462985 / 97e17afb, OK.
- Ledger: 398 rows, `verify()` = (True, None).

**§21.2 EVAL-AUDIT is on track.**
- All 7 builder A/B arms were re-measured independently on the frozen ruler and **CONFIRMED**.
- The W0 net number is measured: +2 gains, −1 loss, so **net +1 of 108** for the break-time conversion. This confirms R19's correction.
- `_cache` is clean (full keys only), and the cache/variant fix has a test.
- **Next:** W1b negative controls → recall@k → definitions and reconciliation → final pack.
- **Add one line to the definitions:** the τ used for each family in SNAPSHOT/recall@k. For BOX, is τ the golden `build_end` (the last contained bar) or the break bar? §21.3 depends on this.

**§21.3 Boxes must stay drawn after the break (finding from BOX-LAB r28).**
- The author keeps a box on the chart for about 60 minutes after the break, and golden drawn spans run past `build_end`.
- Engine and lab boxes **close at the break**. If τ sits at or after the break, a correctly drawn box is already gone at the author's decision moment, and the snapshot lens scores it as absent.
- In the lab, adding a `BROKEN` state (drawn, no longer a live barrier) raised live boxes at τ to 2.0 and brought born recall to 19/108 = 0.176 at ~2 live boxes. That is the closest any design has come to the "born > 0.21 at ≤ 2 boxes" target.
- **The engine lifecycle belongs to the build lane.** A drawn tail after the break (box stays drawn for `tail_bars` after its break, then closes) is added to the build queue below, as a paired A/B on the snapshot lens.
  - Golden anatomy: drawn tail about 60 min, i.e. `tail_bars` ≈ 12, measured on TUNE labels. Log the provenance.

**§21.4 Build lane: order from now to the freeze.** The lane has not acked R19/R20. Its live default still has REQ-1(b) ON (`ef049c28` = `b4913da0` behaviour).
1. Log "rulings read up to R21". **Set REQ-1(b) OFF** (R20 §20.1) and log STABLE `<hash>`.
2. **BRACKET furthest-anchor** (in progress): the lane measured that the right proposal is always the longest-sep sibling (85/85). That is a causal fix for proposal precision. Finish its paired A/B under the keep-rule (recall equal or up, less ink).
3. **BOX drawn tail** (§21.3): paired A/B. Report snapshot BOX recall, cumulative BOX recall, live clutter at τ and the clutter ratio. Keep it if the snapshot recall gain comes with no more than 0.5 extra live objects (median) at τ. Otherwise log it as a lever.
4. **Expose the live salience score** in the engine output. This is output only; confirm it with an identity check.
5. **`live_budget` prototype** (R20 §20.4), flagged and default OFF, measured by 23:45Z if possible. If not, log it as not done.
6. **Freeze at about 00:05Z** with the final STABLE hash and the one-screen status.

**§21.5 BOX-LAB stopped and resumed again (resume 2).**
- BOX_LOG had been silent for 52 minutes, and rounds r17–r28 were run but not logged. This is the second time tonight.
- **The rule has no exceptions:** a round that is not in ROUND_X3.md did not happen.
- The resume prompt asks it to:
  - ack R18–R21;
  - write r17–r28;
  - log;
  - then continue.
- **Also:**
  - box height failed on the production stream (R20 §20.2), so do not rely on it;
  - `prom_abr` is the validated separator;
  - report the r28 numbers **under the frozen ruler's conventions as well**. If the lab sets `build_end` = break bar, that is the W0 conversion, which is worth net +1. Report both the lab convention and the ruler convention so the engine and the lab stay comparable.

## Ruling 22 (20:53Z) - the salience score cannot select; the author has one object live; the judge is too lenient; build lane stopped and resumed (third time)

**§22.1 Build lane's HOLD-gate probes are accepted. They change the plan.**
- **The author keeps about one object live at a time.** Golden live count per bar: median 1, p90 1, max 4. The engine is at a median of 8 (ratio about 9.75). The clutter gate (≤ 1.5) therefore means about 1–2 live objects. This calibrates the recall@k lens: k = 1 and k = 2 are the author's real budget.
- **The current salience score cannot select.**
  - Golden-faithful live budgets (signal 2 / context 1 / annot 2 / hard 4) cut live clutter from 12 to 7, but **halved recall** (BOX .08 → .05, snapshot .11 → .06).
  - Right challengers that lose score a median of 2.16, against incumbents at about 14. Wrong structures score as high as right ones.
  - **So R20 §20.4 item 3 (`live_budget` with displacement by the current score) is withdrawn.** The answer is already measured, and it is negative.
- **LABEL_TF agreement is 0/14.** Marks are emitted by the parent object, and the matched engine parent has usually ended before the author's marks.
  - This gate depends on BOX/LINE recall **and on lifespan**.
  - The drawn tail (R21 §21.3) is the relevant lever here too.
- **BRACKET furthest-anchor was a wash** (32 → 33 matches, PATTERN_LINE −1) and was reverted. Accepted.
- **The lane's conclusion is adopted as the program's position:** the HOLD gates cannot be reached from salience alone. What is needed is **proposal precision in the generators**: fewer and better candidates per family, ranked by family-specific evidence. That is what the labs build:
  - levels: defended origin, approach, ret24;
  - boxes: pivot-anchored edges, `prom_abr`, `deep_piv`, drawn tail.

**§22.2 Build lane stopped and resumed (resume 7).** Its 20:40Z round re-read only R13–R15, so REQ-1(b) is still ON (live `80fe9f1b` behaves like `b4913da0`), against R20 §20.1. **The queue until the freeze:**
1. Log "rulings read up to R22".
2. **Set REQ-1(b) OFF.** Log STABLE `<hash>`.
3. **BOX drawn tail paired A/B** (R21 §21.3, about 12 bars after the break; derive the provenance from golden drawn tails on TUNE). Report:
   - snapshot BOX recall;
   - cumulative BOX recall;
   - live clutter at τ;
   - clutter ratio;
   - LABEL_TF agreement n/N.

   Keep it by the R21 criterion. Otherwise log it as a lever.
4. **Expose each live object's salience score in the output** (output only, identity check).
5. **Freeze at about 00:05Z,** with the one-screen status.

**§22.3 EVAL-AUDIT: the blind judge is too lenient to support a plausibility claim.**
- Specificity is 0.67: a third of deliberately wrong drawings were judged plausible.
- The Rogan–Gladen corrected plausible-FP shares are v0 .71 (CI .33–1.00), v1 .65 (.29–1.00) and linelab .82 (.50–1.00). The CIs are too wide to conclude anything.
- **In the Owner's pack, the plausibility result is labelled inconclusive.** The pack does **not** claim that "most engine extras are defensible".
- The Lead will offer the Owner a small human-judged sample instead: about 20 blind items, about 10 minutes of his time. EVAL-AUDIT prepares `evalcheck/OWNER_JUDGE_PACK/`:
  - 20 items: 8 engine FPs (v1), 6 golden controls, 6 negatives;
  - order shuffled, no labels, the same renders as W1;
  - a one-page instruction in Vietnamese: "would you draw this on your chart? yes / no / can't tell";
  - an answer key kept separately (`_key.json`, never shown in the pack).

  Do it after recall@k, before the final pack.

**§22.4 Morning framing (for everyone's one-screen status).** Structure your status around these points:
1. What coverage the lane reached.
2. What selection it achieved at the author's budget (k = 1–2 live; recall@k), with CIs.
3. What remains, stated as proposal-precision work in the generator.

No lane changes a gate or the ruler. The Owner decides the success definition in the morning.

## Ruling 23 (21:08Z) - pre-freeze STABLE accepted; EVAL-AUDIT rehearses the pack now instead of waiting; BOX-LAB r33 needs day-CV and a shuffle control; the judge key leaves the pack

**§23.1 Build lane: STABLE `584c7743924a8b1b` (20:57Z) is accepted as the pre-freeze production default.**
- It acked R22 at 20:54Z. State: REQ-1(b) OFF, `marker.day_extreme_only` flag added with default OFF, retirement all-ON, context cap 2/288, rate_total 5, suite 72/72.
- The REQ-1(b) line (+3 BOX, +7 BRACKET for +2 live objects) goes into the Owner's lever table as measured.
- Continue the R22 §22.2 queue (items 3–5).
- BAR_MARKER: a paired A/B on `584c7743` with the flag ON vs OFF, with per-family deltas. It stays OFF by the keep-rule unless a variant keeps every family within −1.

**§23.2 EVAL-AUDIT: do not idle until the freeze.** Between now and about 00:05Z:
1. **Identity check (reviewer role).** Compare `584c7743` default against the W3-confirmed reviveOff arm. Objects must be equal on all 198 TUNE panels, or explain each difference. Write a VERIFY_LOG line.
2. **Dress rehearsal on `584c7743`:**
   - GATE_PACK;
   - PLAUSIBILITY, labelled inconclusive (R22 §22.3);
   - recall@k at k = 1, 2, 3, 5 for v0, v1@`584c7743` and the levers:
     - revive ON;
     - BAR_MARKER ON, once the build lane logs its hash;
     - the LEVEL-LAB flag ON, once LEVEL-LAB logs it.

   Write it to a NEW file, `GATE_PACK_DRESS_584c7743.md`. At the freeze, the final pack is a re-run on the STABLE hash and reads as a diff against the dress rehearsal.
3. **Move `_key.json` out of `OWNER_JUDGE_PACK/`** into `evalcheck/_owner_judge_key/`. This is a move, not a delete; log it. Drop the key line from INSTRUCTIONS.md. The Owner's folder must contain only INSTRUCTIONS.md, ANSWERS.md and `items/`.
4. **Verify BOX-LAB r33 on the ruler** from its artifacts (born, recall@1, recall@2, ink per panel, live@τ), once BOX-LAB has written them (§23.3).

Keep the ~25-minute cycle for reading rulings.

**§23.3 BOX-LAB r29–r33: the best BOX lab result tonight, not yet an out-of-sample one.**
- r33 (r28 score, −0.75·barrier, deeper_lv term):
  - born 21/108 = .194;
  - recall@1 = recall@2 = 16/108 = .148;
  - 5.30 ink per panel (r28: 9.49);
  - live@τ 1.0, which is the author's budget (R22 §22.1).
- But the weights were chosen on the same 108 goldens after five rounds. Before r33 goes into BOX_INTEGRATION:
  1. **Write r29–r33 into ROUND_X3.md now,** with both build_end conventions. ROUND_X3 still ends at r28 (20:42Z).
  2. **Leave-one-day-out CV** of the r33 score. Re-fit the weights inside each fold, or keep them frozen if nothing is fitted, and say which. Use the same folds as LEVEL-LAB V8. Report CV born recall and recall@1 and recall@2, with a day-bootstrap CI.
  3. **Negative control:** shuffle deeper_lv (and barrier) across candidates within each panel. Recall should fall back to the r28 level. If it does not, the gain is not coming from the feature.
  4. **"Barrier is anti-predictive":** show the sign on every fold before anyone relies on it.
- X4 BOX_INTEGRATION.md stays due at about 23:30Z, and it reports the CV numbers, not the in-sample ones.
- Log "rulings read up to R23" first. The lane has not logged R22 yet.

**§23.4 LEVEL-LAB: the integration is going as mandated** (38 KATs green; the `_budget_ok` foreign-route bug is fixed).
- In the A/B note, show that flag OFF is bit-identical to the `584c7743` default (objects and cand_log, all 198 panels).
- The freeze hash must contain the integration with the flag OFF.
- Measure and report the birth-lag flicker you noted.

**§23.5 Morning-pack wording.** BOX-LAB and LEVEL-LAB numbers are **lab results, not engine results,** until they are integrated and measured on the production stream (R15 §15.1). The pack shows them in a separate table labelled "lab, not engine".

No lane changes a gate or the ruler.

## Ruling 24 (21:21Z) - LEVEL-LAB flag stays off by the keep-rule; one more step on the ledger; A/B arms must share one engine hash; code ownership until the freeze; LEVEL-LAB resumed (it ended early)

**§24.1 LEVEL-LAB's engine A/B is accepted** (ROUND_L9: engine `1c24be53`, both arms re-measured at that hash, 198 TUNE, ruler `50e11fd5`).
- **Flag ON:**
  - LC born recall .146 → .229 (+4 objects; all are "old defended price, re-approached");
  - LC snapshot and recall@2 .021 → .106;
  - MINI flat;
  - clutter ratio 2.50 = 2.50;
  - flicker .33 → .43 changes/h.
- **BOX −2 net** (4 lost, 2 won). This fails the keep-rule's "no family loses more than 1", so **the flag stays OFF.**
- It enters the Owner's lever table as measured, with its CIs. Both are weak (each CI includes 0):
  - lab − prod LC@2: +.056 [−.086, .202];
  - lab − naive: +.067 [−.039, .179].
- **Accepted:**
  - the BOX loss mechanism (defended births spend the shared `rate_total` ledger that BOX births also need);
  - the MINI finding (201 defended MINI births, about 43% of defended births, with 0/31 golden MINIs hit).

**§24.2 LEVEL-LAB is resumed (resume 6).** It ended at 21:17Z after finishing items 1–6. The Lead's resume-5 prompt allowed that: it said "then stop". The Lead wants the lane to run until 23:50Z, so this queue has no stop point. *(Corrected at 21:22Z. The first version of this line said the lane broke its mandate. It did not.)* Queue to about 23:50Z:
1. Log "rulings read up to R24".
2. **v2: flag ON with defended MINIs OFF** (a sub-flag in `levels.py`; defended LC only). The reason is that the MINIs are 43% of defended births, produce zero hits, and spend the ledger that BOX needs.
   - Run a paired A/B against flag OFF: both arms in one process at one hash, as `ab_engine.py` does.
   - Report the keep-rule, the day-bootstrap CI and flicker, as in ROUND_L9.
3. **v3, only if v2 still loses BOX:** REQ-L3 option 1 (defended LC births exempt from `rate_total`; `rate_level_carried` kept).
   - Only if it can be done inside `levels.py`, for example by marking the birth the way the ledger already exempts continuations.
   - If it needs an edit to `salience.py`, do not make it. Write the patch as a spec in REQUESTS.md instead (§24.4).
4. **R23 §23.4:** show that flag OFF is bit-identical to the current default (objects and cand_log, all 198 panels).
5. Update item 10 of FOR_THE_OWNER.md with the v2 (and v3) result.

Never end the session to ask. After the queue, extend the CI and the anatomy of v2 until 23:50Z.

**§24.3 Pairing rule, restated (R14 §14.2).** The scoreboard shows A/B arms at **different** engine hashes:
- build tail_off `a7b09b74` vs tail_on `1c24be53`;
- build marker_off `a606f9b1` vs marker_on `e9fd5283`.

Two lanes are editing engine files at the same time, so the hash moves under both of them. From now on:
- An arm is switched at runtime (variant or config), never by editing a file. Both arms run in the same invocation, and both rows carry the same engine hash.
- **Build lane:** re-run the drawn-tail and BAR_MARKER pairs that way before the freeze. Alternatively, show the diff proving that the two hashes differ only by the flag default.
- **EVAL-AUDIT:** the lever table in the dress rehearsal and in the final pack uses only pairs that share one hash. Where a pair does not, re-run both arms at one hash yourself.
- LEVEL-LAB's ROUND_L9 pair (both arms at `1c24be53`) already meets this rule.

**§24.4 Code ownership until the freeze.**
- The build lane owns every engine file except `levels.py`, including `salience.py`.
- LEVEL-LAB owns `levels.py`, for flagged code only. The default path stays untouched.
- No other lane edits engine files.
- The freeze STABLE hash contains both lanes' flags with defaults OFF. At default settings it must be behavior-identical to `584c7743`. EVAL-AUDIT checks this (R23 §23.2 item 1).

No lane changes a gate or the ruler.

## Ruling 25 (21:37Z) - full review; v1 does not select better than v0; the owner judge pack is not blind yet; the shared ledger makes every gain cost another family; BOX-LAB resumed (third time)

**§25.1 Full review (21:34Z).**
- Seals: FREEZE_v3 `f0462985`, runner `97e17afb`. Ledger: 398 rows, verify (True, None).
- Last ruling acknowledged by each lane:
  - build lane: R24 (21:26Z);
  - LEVEL-LAB: R24 (21:23Z);
  - EVAL-AUDIT: R23 (21:21Z);
  - BOX-LAB: R21 (20:39Z). Its resume-2 prompt did not ask it to re-read rulings, which is the Lead's omission. See §25.6.

**§25.2 The dress rehearsal (`GATE_PACK_DRESS_584c7743.md`, 21:31Z) is accepted as the template.** Changes for the final pack:
1. **Remove "plaus-adj" from the BOX precision row.** A number from a judge ruled unreliable (R22 §22.3) must not sit next to a gate. It may appear only in the plausibility section, labelled unreliable.
2. **At the top, state the v1-vs-v0 finding plainly,** with the CIs you already have. At the author's budget, v1@`584c7743` selects worse than v0 at every k:

   | | k = 1 | k = 2 | k = 5 |
   |---|---|---|---|
   | v1 | .01 [.00–.02] | .01 | .07 |
   | v0 | .04 [.02–.06] | .07 | .14 |

   - Cumulative BOX recall: v1 .06, v0 .21.
   - v1's gain is ink only: clutter ratio 5.0 vs 9.0, live objects at τ 10 vs 16.
3. **Add per-family recall@k:** top-k *within each family*, at k = 1 and 2, for v0, v1, linelab and every lever.
   - Keep the current all-family table beside it.
   - The lab numbers are per-family (BOX-LAB recall@2 counts boxes only; LEVEL-LAB LC@2 counts levels only), so only the per-family engine numbers are comparable with them.
   - Lab rows go in a separate table labelled "lab, not engine" (R23 §23.5).
4. **Lever table: same-hash pairs only (R24 §24.3).**
   - The build lane is re-running the drawn-tail and BAR_MARKER pairs.
   - The revive pair (`03dbe495` vs `03917fd5`) is also a two-hash pair. Re-run revive ON as a runtime variant at the freeze hash (your cache harness with the params file is enough), or show that the code diff is the default only.
   - The LEVEL-LAB pairs are already same-hash: flag_on at `1c24be53`, v2 at `a9d6af1c`.
5. Under each recall@k table, add one line naming the ranking: born cand_log score, with recency as the fallback.

**§25.3 OWNER_JUDGE_PACK: not ready to show the Owner.** The Lead viewed items p01, p07, p14 and p19.
1. **Every item carries a title line** with the panel id, the date, the book figure number and the words "TUNE v2 golden".
   - That is not blind. The Owner owns the book, and "golden" pushes toward "yes".
   - Strip the title; print only the item id (p01…p20).
2. **p07 has no dashed τ line and no visible drawing** (only a tiny dash near 08:00).
   - Every item must show exactly one clearly visible drawing and the dashed τ line.
   - Draw ticks and markers at a visible size, or replace a marker item with another item of the same class.
3. **Re-render all 20** from the same sample (same seed, same class mix).
   - The key changes only for replaced items; log replacements in `_owner_judge_key/`, not in the pack.
   - Add one VERIFY_LOG line per item: id, drawing visible (y/n), τ line visible (y/n), title stripped (y/n).
   - Due before the final pack.

**§25.4 LEVEL-LAB v2 is accepted** (ROUND_L10, one hash `a9d6af1c`).
- Identity check PASS, 198/198 panels.
- v2 heals BOX (+1) and removes the flicker cost. But PATTERN_LINE −2, so the keep-rule fails and the flag stays OFF.
- **The structural finding:** under one shared `rate_total` ledger, one family's gain is paid for by another family (BOX under flag_on, PATTERN_LINE under v2). The same will hold for any lab integration, BOX-LAB's included.
- flag_on and v2 go into the lever table with their CIs.

**§25.5 Build lane: one more flagged lever before the freeze — a per-family ledger** (`salience.py`, which the build lane owns under R24 §24.4).
- **What it does:** each family gets its own rate budget, and the budgets sum to today's `rate_total`. Take each family's share from the `584c7743` default birth mix. Defended LC births draw on LEVEL_CARRIED's share.
- **Default:** OFF, behavior-identical to `584c7743`.
- **Deadline:** after the re-paired tail and marker rows. Log the flag name and hash by 23:15Z, or log why it cannot be done.
- **Then LEVEL-LAB runs three arms in one invocation at one hash:**
  - (a) default;
  - (b) per-family ledger only;
  - (c) per-family ledger + defended LC (def_mini_off).

  Report the keep-rule for (b) vs (a) and for (c) vs (a), with the day-bootstrap CIs. This tests whether the zero-sum cost can be removed.

**§25.6 BOX-LAB is stopped and resumed (third time).**
- **Hand-written stamps later than the file times:**
  - the BOX_INTEGRATION.md header says "~22:40Z", but the file was written at 21:33:45Z;
  - ROUND_X3 says "Final state (post-r40, ~22:35Z)", but the file was written at 21:32:44Z.

  R14 requires stamps from a command. Add correction lines to both files; no deletes.
- **BOX_INTEGRATION reports in-sample numbers** and says "born recall > v0 is met". R23 §23.3 applies before any such claim.
- **Queue:**
  1. Log "rulings read up to R25".
  2. Write the two correction lines.
  3. Leave-one-day-out CV for r33 and r37, with a day-bootstrap CI. The weights were hand-set on the same 108 goldens, so either freeze them or re-fit per fold, and say which.
  4. Shuffle control: shuffle deeper_lv and barrier within each panel. Recall should fall back to the r28 level.
  5. Show the barrier sign on every fold.
  6. Report recall@1 as well as recall@2. The author's median live count is 1.
  7. Revise BOX_INTEGRATION with the CV numbers, labelled "lab, not engine". Show r33 and r37 as two points on one ink–recall frontier, with CIs.
  8. Express born ink against the author's rate: 108 golden boxes over 198 panels is about 0.55 per panel, so r37's 17.5 per panel is about 30×.
- X4 stays due at about 23:30Z. The lane stops at about 23:50Z.

**§25.7 Morning framing** (for every lane's one-screen status):
1. v1 as built tonight lowers ink but does not select better than v0 at the author's budget.
2. The labs raise per-family recall at k = 1–2: LEVEL-LAB under CV; BOX-LAB pending CV.
3. Under the shared ledger, each gain costs another family. The per-family ledger lever tests whether that cost is removable.

No lane changes a gate or the ruler.

## Ruling 26 (21:52Z) - verdicts for the lever table: v2b not kept; BOX-LAB CV accepted with its limits; the drawn tail is a real lever after all; one cache check before the final pack

**§26.1 LEVEL-LAB v2b (def_all_lc, `a62edc19`): not kept. It goes into the lever table as measured.**
- LEVEL-LAB lists no family losing more than 1 (BOX −1, PATTERN_LINE −1, RANGE −1, MINI +1). But the keep-rule has two more legs, and both fail on the scoreboard rows at one hash:
  - **Recall:** aggregate cumulative recall is net −2 objects (LC flat 7 → 7).
  - **Ink:** live clutter at τ rises from 10 to 11.
- The LC snapshot gain (.021 → .085) is real. It is reported under recall@k, not as a keep.
- The lever table at `a62edc19` now has flag_on, v2 and v2b. Good.

**§26.2 BOX-LAB CV is accepted, and the pack states its limits.**
- r33 and r37 were cross-validated with the weights frozen (day folds from V8):
  - r33: born .194 [.127–.274], recall@1 .148, recall@2 .148, ink 5.3 per panel;
  - r37: born .278 [.198–.357], recall@1 .130, recall@2 .241 [.168–.316], ink 17.5 per panel.
- **Limit:** the weights were chosen over about 40 rounds on these same 108 goldens. Frozen weights make the CI a day-sampling interval only. It does not cover the selection. The pack labels these numbers "lab, TUNE, selection-optimistic".
- **Shuffle control:** born recall does not fall back (.306 at 35.8 ink per panel), but recall@2 does (.241 → .185).
  - Read: cumulative born recall is bought with ink.
  - The features carry signal for *which* box is live at τ.
  - At k = 1 the low-ink r33 (.148) is at least as good as r37 (.130). This matches LEVEL-LAB, where k = 1 favours lower ink.
- The barrier sign holds on all 5 folds. Accepted.

**§26.3 Build lane: the one-hash re-pair corrects the drawn-tail result.**
- The earlier "zero delta" came from the cache trap (the variant was not passed, so both arms ran on the same params).
- At one hash, the tail gives:
  - BOX snapshot 2 → 3;
  - BRACKET +1;
  - PATTERN_LINE −1;
  - live clutter at τ 10 → 11.
- It stays OFF by the R21 criterion (at most +0.5 live), but it is a real lever. The lever table uses the one-hash numbers.
- BAR_MARKER at one hash: LABEL_TF agreement 0 → 2/51 and BOX snapshot +1, but PATTERN_LINE −2. Still OFF.
- Log "rulings read up to R26". Then the per-family ledger (R25 §25.5) by 23:15Z.

**§26.4 EVAL-AUDIT, before the final pack:** check that no number in the pack was read from a bad cache entry.
- The build lane quarantined 5996 zero-byte pickles and then a batch of `__main__` pickles from `_cache/`.
- Verify that `gate_pack.py`, `recall_at_k.py` and `arm_ab.py`:
  - refuse zero-byte or unloadable entries;
  - re-run instead of reusing them;
  - key every lever arm by variant.
- Write one VERIFY_LOG line with the counts.
- Then continue with R25 §25.2–25.3.

No lane changes a gate or the ruler.

## Ruling 27 (22:16Z) - the zero-sum cost is removable: first lever tonight to pass the keep-rule, pending independent verification; the freeze default does not change; params hygiene

**§27.1 The per-family ledger result (lane claims, one hash `2795e5e0`).**
- The build lane delivered the `famledger` flag by 22:10Z, well ahead of the 23:15Z deadline. LEVEL-LAB then ran the three arms of R25 §25.5 in one invocation (22:14Z, ROUND_L12).
- **(b) ledger alone:** fails the keep-rule (BOX −2; each family's share of the ledger is reallocated).
- **(c) ledger + defended LC (def_mini_off):** passes every leg of the keep-rule.
  - **Recall:**
    - LC born .146 → .229 (+4); trusted .275;
    - LC snapshot .128; LC@2 .128.
  - **Families:** BOX 0, PATTERN_LINE 0, MINI 0; the worst is CONTEXT_RANGE −1.
  - **Ink and churn, all unchanged:** clutter ratio, live clutter, flicker and births per panel.
  - **CIs:** LC born +.120 [.009–.242]; LC@2 +.119 [.021–.233].
- This is the first lever tonight to pass the pre-registered keep-rule. It also confirms the mechanism: the defended route produces the gain, and separate family budgets remove the cost to other families.

**§27.2 Independent verification before anything is built on it** (builder ≠ reviewer). EVAL-AUDIT re-runs (a), (b) and (c) itself, with its own `arm_ab.py`, at one hash:
1. **Per-golden gains and losses.**
2. **Explain why (b) loses 2 BOX and (c) loses none.** With truly separate family budgets, adding defended LC births should not move BOX at all. If it does, the budgets are not fully separate; find where they leak.
3. **Recall@k for (c),** per family and across families, at k = 1 and 2.
4. **One VERIFY_LOG line:** CONFIRMED, or the differences found.

Priority: after R26 §26.4, before the OWNER_JUDGE_PACK re-render.

**§27.3 The default at the freeze does not change.**
- The freeze default stays behavior-identical to `584c7743` (R24 §24.4). The Lead does not flip a default hours before the pack.
- The pack shows two columns side by side:
  - **v1 frozen default;**
  - **v1 + famledger + defended LC,** marked "keep-rule pass" and either "verified" or "unverified".
- **Caveat:** about 8 level variants were tried tonight on TUNE, and the CI's lower bound is near 0 (.009). The pack says "TUNE; several variants tried; confirm out of sample".
- If it is verified, the Lead will recommend it as the first change after the Owner's morning decision.

**§27.4 Params hygiene.**
- EVAL-AUDIT's runs crashed in `load_params` while a params file was mid-edit (`def_price_mode` had no provenance yet). Any lane editing params must:
  1. write to a temp file;
  2. validate it by loading it;
  3. rename it into place;

  with the provenance in the same write.
- No params schema changes after 23:30Z.

**§27.5 R22's framing is refined by tonight's measurements.**
- **Levels:** coverage is solved. A defended proposal lies within tolerance during the golden span for LC .851 (trusted .923) and MINI .867. The loss was selection under the shared ledger, and a per-family budget plus the defended route fixes most of it.
- **Boxes:** generation still limits (oracle .556 → .630 with BOX-LAB's r43 edge sources, while born recall is flat at .287).
- The program's next architecture, for the Owner to confirm in the morning:
  - per-family generators;
  - per-family budgets;
  - per-family ranking at the author's live budget.

**§27.6 BOX-LAB:** r41–r43 are accepted as lab findings (r43 oracle .630, located .769). X4 BOX_INTEGRATION stays due at about 23:30Z and includes r43 and the per-family-ledger dependency. There is still no `boxes.py` edit.

No lane changes a gate or the ruler.

## Ruling 28 (22:35Z) - full review; the pack is close; the owner judge pack still has a τ defect and its negatives need an audit; no new level variants; BOX-LAB closed

**§28.1 Full review (22:33Z).**
- Seals `f0462985` / `97e17afb` OK. Ledger 398 rows, verify (True, None).
- Build lane: last log 22:10Z; working on exposing the salience score before the freeze.
- LEVEL-LAB: active; last log 22:31Z.
- EVAL-AUDIT: active (VERIFY_LOG 22:24Z, pack files 22:32Z), but EVAL_LOG has been silent since 21:47Z. Log in EVAL_LOG at least every 45 min.
- BOX-LAB: ended at 22:23Z with its one-screen status and X4. **Accepted and closed; not resumed.** More in-sample rounds tonight would only add selection optimism.

**§28.2 Dress rehearsal (22:32Z): the R25 changes are in.**
- Done:
  - "plaus-adj" is out of the gate rows;
  - the v1-vs-v0 table is stated plainly;
  - the lever table uses same-hash arms only, revive included (`a62edc19`);
  - the ranking provenance line is there;
  - the cache audit is done: 0 zero-byte entries; 1728 unloadable stale-class pickles, confined to arms the pack does not read; loaders hardened.
- **Still missing:**
  - **per-family recall@k** (R25 §25.2 item 3): top-k within each family, k = 1 and 2, for v0, v1, linelab and the famledger (c) arm. Without it, the lab numbers cannot be compared with the engine's.
  - The famledger arms appear only in the scoreboard history. After R27 §27.2 verification they go into the lever table, marked verified or unverified.

**§28.3 OWNER_JUDGE_PACK: titles are stripped (good), but two defects remain.** The Lead viewed p01, p05, p07, p12, p16 and p20.
1. **τ placement.**
   - p01 (BAR_MARKER, item_043) and p07 (BOX, item_058) show the τ line near the left edge (about 05:50), while the drawing is hours later.
   - "τ visible" is not "τ correct". A τ before the drawing makes the question unanswerable, and a τ far from the drawing is a class tell.
   - Compute τ for every item from the drawn object's own times, per R21 §21.2:
     - BOX and lines: build end or break bar;
     - BAR_MARKER: t0;
     - levels: t0 + 10 min;
     - BRACKET and SQUEEZE: t1.
   - Log |τ − expected| in bars for each item.
2. **Negatives validity.** p05 (labelled neg_025) looks like a well-fitted box on its panel. Audit every W1b negative (30) and the 6 in the pack:
   - how each was constructed;
   - its geometry against the nearest golden on that panel under the ruler's matching.

   A negative that would *match* a golden is invalid. Recompute W1b specificity on the valid negatives only. The pack's plausibility section uses the recomputed number, with its CI. If invalid negatives were counted as judge errors, the "judge unreliable" conclusion (R22 §22.3) may be partly an artefact. Say which.
3. **If items 1–2 are not done by 23:50Z,** the owner judge pack is withheld from the morning pack. Say so in the pack; the Lead will offer it later.

**§28.4 EVAL-AUDIT priority until the freeze:**
1. R27 §27.2: famledger verification (three arms, one hash; explain the BOX behaviour).
2. Per-family recall@k.
3. Negatives audit and the W1b recompute.
4. OWNER_JUDGE_PACK τ fix.
5. Final GATE_PACK and PLAUSIBILITY, 00:15–00:35Z, on the STABLE freeze hash.

Log "rulings read up to R28".

**§28.5 LEVEL-LAB: no new level variants.** About 8 have been tried on TUNE tonight. More tuning only raises selection optimism. Until 23:50Z:
1. LC recall@1 for arm (c). The author's median live count is 1.
2. Document the intra-family competition inside the LC share (defended route vs external emitters `broken_box_edge_up` / `broken_line_edge`) as the next step. Do not run it as a new arm tonight.
3. Final LEVEL_INTEGRATION.md and the one-screen status.

Your params-file byte repair (non-ASCII escaped; hash `2795e5e0` → `9283b389`; identity 198/198) is accepted. From now on only the build lane edits the params file, and nobody edits it after 23:30Z (R27 §27.4).

**§28.6 BOX-LAB closing record (lab, not engine):**
- **Oracle ladder:** .556 → .583 → .630 → .667 (r47; located .833).
- **Selection:**
  - r37: born .278 [.198–.357], recall@2 .241 [.168–.316], ink 17.5 per panel;
  - r33: born .194, recall@1 .148, ink 5.3.
  - Weights frozen; label: selection-optimistic.
- **X4:** six proposed changes, with the famledger dependency.
- **Housekeeping:** the header stamp "~22:40Z" has its correction line directly below it. No delete; this is complete.

**§28.7 Build lane: freeze at about 00:05Z.**
- The STABLE hash must contain the famledger flag and LEVEL-LAB's flags, all defaulting OFF.
- Identity vs `584c7743` 198/198 at that hash; suites green; one-screen status in the R22 §22.4 framing.
- Log "rulings read up to R28".

No lane changes a gate or the ruler.

## Ruling 29 (22:49Z) - the reviewer's famledger check stands, and it narrows R27; the pack says exactly that

**§29.1 EVAL-AUDIT's independent check (VERIFY_LOG 22:41Z, own `arm_ab.py`, hash `9283b389`) is the source of truth for the pack.**
- **The keep-rule pass on born recall is CONFIRMED:**
  - LC .12 → .21;
  - BOX net 0, PATTERN_LINE 0;
  - BRACKET .29 → .35 under both (b) and (c);
  - (c) per golden: 27 gained, 15 lost.
- (b) ledger-only fails (BOX −2), also confirmed.

**§29.2 Correction to R27 §27.1 and §27.5.** R27 said "the zero-sum cost is removable". That is only partly shown. famledger v1 has three defects:
1. **Kinds with no share entry get zero share.** CONTEXT_RANGE, CONTEXT_LINE, MINI_LEVEL and SQUEEZE are never born under the flag. Any adoption needs a floor share for every kind.
2. **The live budget, geometric NMS and bar timing are still shared.** "(c) loses no BOX" is partly outcome luck through those channels, not proof of isolation. LEVEL-LAB found the same timing coupling: the 72-bar windows shift.
3. **The `cont` routes bypass the ledger.**

**At the author's budget, (c) is flat** (engine top-k, all families):

| | k = 1 | k = 2 | k = 5 |
|---|---|---|---|
| (c) | .006 | .025 | .088 |
| base | .01 | .01 | .07 |

LC at τ is .065, not the lab's .128. The lab figure uses its own ranker, and that ranker was never the engine's.

**The pack's second column reads:** "famledger v1 + defended LC: keep-rule pass on born recall (verified); four kinds silenced (defect); no gain at the author's budget". The Lead will frame it to the Owner as a direction, not a result.

**§29.3 LEVEL-LAB.**
- **d2 ceiling probe** (LC share 2; rate_level_carried 2): LC born .229 → .292, but the ink leg fails (births 6 → 7 per panel, clutter 2.5 → 3.0, live +1, flicker ×2). It is a priced trade: it goes into the Owner's lever table and is not kept. The disclosure that it ran before R28 was read is accepted.
- **Clock (R14).** The 22:47Z LEVEL_LOG entry has two hand-written times:
  - "R28 read at ~22:52Z" is later than the entry itself;
  - "d2 launched ~22:47Z" contradicts the 22:45Z result entry.

  Append one correction line. Every time must come from `logline.py`.
- **Lab figures** (LC snapshot .128, LC@2 .128) go into the lab table only, labelled with their ranker. The engine column uses EVAL-AUDIT's numbers.
- The residual decomposition is accepted: LC 11 hit, 33 covered but unhit (19 of them rate-limited within the family), 4 with no proposal. The next level step is selection *within* the LC share, not generation.

**§29.4 Build lane: no fix tonight.**
- The freeze default stays behavior-identical to `584c7743`, and famledger v1 stays OFF.
- Do **not** patch the zero-share defect before the freeze. It would be an untested change hours before the pack.
- Put it first in the next build round:
  - a floor share for every kind;
  - a per-family live budget;
  - NMS limited within each family.

**§29.5 EVAL-AUDIT: R28 is next** (§28.3 OJP τ placement and the negatives audit, deadline 23:50Z; per-family recall@k). Log "rulings read up to R29". In the final pack, the famledger row uses §29.2's wording.

No lane changes a gate or the ruler.

## Ruling 30 (23:16Z) - the negatives are cleared; the owner judge pack has one class tell left (box τ) and one readability defect; the ruler's BRACKET rule ignores price

**§30.1 EVAL-AUDIT resume 6: the negatives audit is accepted** (EVAL_LOG 23:03Z and 23:09Z).
- Rulings read up to R29 at 23:03Z.
- 2 of 30 W1b negatives are invalid: neg_002 and neg_011. Both are BRACKET price shifts that still match a golden.
- p05 / neg_025 is valid; it does not match any golden under the ruler.
- Specificity: .67 on all 30 → **.68 [.50–.86] on the 28 valid negatives**.
- **Answer to R28 §28.3.2:** the invalid negatives do **not** explain the judge's low specificity. R22 §22.3 stands: the blind judge is unreliable on specificity, and plausibility stays INCONCLUSIVE. The pack says so in one line.

**§30.2 OWNER_JUDGE_PACK after the 23:05Z re-render.** The Lead viewed 18 of 20 items.
- **Fixed:** engine items now show τ at their own times.
  - p01 and p10 (BAR_MARKER): τ at t0, on the marker.
  - p07 and p18 (BOX): τ at the drawn right edge.
  - p20 (LEVEL_CARRIED): τ at t0 + 10 min.
  - Lines are consistent across classes: τ at the right end for p02, p04, p11 and p17.
- **New class tell, boxes only:**
  - The two golden BOX controls (p03, p09) show τ *inside* the box, at build_end, 2.5–3.5 hours before the drawn right edge.
  - All 7 engine and negative box-like items (p05, p06, p07, p13, p16, p18, p19) show τ exactly on the right edge.
  - 2 vs 7, perfectly separated. A judge could learn "τ inside the box = the author's".
- **Fix:** use one τ event per kind, the same for every class.
  - BOX and CONTEXT_RANGE: τ = the drawn right edge (the break bar; R21 §21.2 allows it), goldens included.
  - Log |dτ| for p03 and p09 in VERIFY_LOG.
- **Readability:** in p04 the engine line lies on the EMA and is almost invisible.
  - Draw the object in one distinct colour and weight for every item (e.g. blue, 2.5 px).
  - Keep the EMA thin and light grey.
  - Same style for all classes; re-render all 20.
- **The deadline stays 23:50Z.** Both fixes done → OJP GO; log "OJP GO" in EVAL_LOG with the spot-check of p03, p04 and p09. Otherwise → "OJP WITHHELD".

**§30.3 Ruler finding: the BRACKET matching rule does not check price.** A price-shifted bracket still counts as a hit (neg_002, neg_011).
- **Consequences for tonight's numbers:**
  - Every BRACKET recall figure is an upper bound. This includes famledger's BRACKET .29 → .35.
  - All-family recall@k includes BRACKET hits.
- **In the pack:**
  - The per-family table shows BRACKET in its own row, with the note "ruler: BRACKET rule has no price check; upper bound".
  - The all-family recall@k line gets the same footnote.
- **No ruler change tonight.** The ruler stays frozen until the Owner decides. The Lead lists it for the Owner as a ruler-v3 candidate.

**§30.4 Build lane:** acked R29 at 23:03Z. Holding until ~23:48Z, then freeze ~00:05Z as ruled (R28 §28.7). If "expose the live salience score" is not done by the freeze, write "not in STABLE" in the one-screen status. It then goes into the next build round, and EVAL-AUDIT ranks with the born cand_log score as ruled.

**§30.5 LEVEL-LAB:**
- Accepted: the R29 ack (22:52Z), the clock correction line, and the docs reframed to R29 §29.2 wording.
- One-screen status by 23:53Z. Do not end before 23:50Z.

No lane changes a gate or the ruler.

## Ruling 31 (23:29Z) - full review; the owner judge pack is GO; the per-family table is the pack's headline selection table

**§31.1 Full review (23:27Z).**
- Seals `f0462985` / `97e17afb` OK. Ledger 398 rows, verify (True, None).
- Build: acked R29 at 23:03Z; holding for the freeze.
- LEVEL-LAB: last log 22:53Z; one-screen status due by 23:53Z.
- EVAL-AUDIT: R30 read and applied at 23:19Z; items 1–4 of its queue logged done at 23:27Z.

**§31.2 OWNER_JUDGE_PACK: GO.** The Lead viewed 8 re-rendered items: p03, p04, p05, p07, p09, p16, p18, p20.
- Objects are blue for every class.
- BOX and CONTEXT_RANGE τ sits on the drawn right edge for goldens and engine alike (p03 +41 bars, p09 +33 bars).
- p04 is now readable.
- The LEVEL_CARRIED item keeps τ at t0 + 10 min, as ruled.
- No titles.

The Lead will offer the pack to the Owner in the morning pack. Do not re-render it unless a ruling asks.

**§31.3 Per-family recall@k (RECALL_AT_K.md, 23:22Z) is accepted, and it is the pack's headline selection table.** The author's per-family budget is box k=1, level k=1, line k=2, bracket k=1:

| arm | box @1 | level @1 | line @2 | bracket @1 † |
|---|---|---|---|---|
| v0 | .134 [.07–.20] | .066 [.01–.12] | .093 [.05–.14] | .388 |
| v1 STABLE `584c7743` | .025 [.00–.06] | .013 [.00–.04] | .078 [.04–.12] | .224 |
| linelab | .000 | .000 | .124 [.08–.18] | .000 |
| famledger (c) | .025 | .026 | .104 [.06–.15] | .271 |

† Upper bound (R30 §30.3).

**Reading:**
- At the author's budget, v1 selects boxes worse than v0, and the CIs do not overlap (.00–.06 vs .07–.20).
- Levels are also lower in v1.
- Lines are about equal between v0 and v1; linelab is the best line arm.
- famledger (c) lifts lines a little (.078 → .104, CIs overlap) and nothing else.
- No arm is near a gate.

In the pack, put this table right after the gate rows, with one sentence: "at the author's own budget, per family".

**§31.4 EVAL-AUDIT clock (R14).** The 23:19Z EVAL_LOG entry says "R30 fixes in by 23:25Z". That time is later than the entry's own stamp; the items' mtimes are 23:18:59–23:19:13. Append one correction line. Times come from `logline.py` only.

**§31.5 Final pack (00:15–00:35Z), on the STABLE freeze hash.** It contains, in order:
1. The gate rows.
2. The v1-vs-v0 all-family table.
3. The §31.3 per-family table.
4. Plausibility: sensitivity .90; specificity .68 [.50–.86] on valid negatives → INCONCLUSIVE.
5. The lever table: same-hash arms only; the famledger row in R29 wording; d2 as a priced trade.
6. The lab table ("lab, not engine").
7. The BRACKET footnote.
8. OJP status: GO.

End with the one-screen status.

No lane changes a gate or the ruler.

## Ruling 32 (23:55Z) - the freeze is accepted (STABLE 9283b389); LEVEL-LAB is closed; the final pack may start now

**§32.1 Freeze accepted.** The build lane declared STABLE `9283b389` at 23:50Z, 15 minutes early. It meets R28 §28.7:
- all tonight's flags are present and OFF by default: `salience.revive_exempt`, `salience.fam_ledger`, the two `marker.day_extreme*` flags, `box.tail_bars=0`, `level.defended_origin` and `level.def_mini_off`;
- canonical-equal to `584c7743` on 198/198 TUNE panels;
- suite 72/72;
- ruler `50e11fd5`.

The live salience score is in STABLE as output only (`Obj.score`), with identity proven. The one-screen status is accepted. From now on, nobody edits engine files or the params file tonight.

**§32.2 LEVEL-LAB closed.** Its one-screen status (23:47Z) is accepted, and the job ended at 23:52Z, after 23:50Z as required. The closing record, lab-ranker figures labelled as such:
- LC coverage is solved: 44 of 48 goldens have a defended proposal; trusted coverage .92.
- The remaining LC work is selection inside the family: of the 33 covered but unhit, 19 are blocked by the `rate_level_carried=1` cap.
- d2 is a priced trade, not kept.
- famledger v1 plus defended LC is "a direction, not a result".

Do not resume.

**§32.3 EVAL-AUDIT: start the final pack now.** Use STABLE `9283b389`, since your cache is already at that hash, and follow the R31 §31.5 order.
- State the ranker change in the pack: the object-carried score was wired at 23:39Z. Every arm must use the same rule: object score, else born cand_log score, else recency. Give the provenance line per arm.
- Where numbers moved against R31 §31.3, the pack's numbers supersede them. Give the reason in one line.
- Clutter: the build lane's final scoreboard row says ratio 4.50, while the dress rehearsal said 5.0. The pack uses one definition, the median per panel of the clutter ratio, and says which.
- Publish GATE_PACK_<hash>.md and PLAUSIBILITY.md, then the one-screen status, by 00:35Z at the latest.

No lane changes a gate or the ruler.

## Ruling 33 (00:10Z) - full review; the final pack is accepted; the night's lanes close

**§33.1 Full review (00:09Z).**
- Seals `f0462985` / `97e17afb` OK. Ledger 398 rows, verify (True, None).
- Build lane closed at 00:05Z after acking R32. LEVEL-LAB closed at 23:52Z. EVAL-AUDIT is the only running job.

**§33.2 GATE_PACK_9283b389.md (generated 00:07Z, rewritten 00:09Z) is accepted as the pack for the Owner.** It has, in the R31 §31.5 order:
- the gate rows on STABLE with CIs;
- the v1-vs-v0 all-family table and the per-family table at the author's budget;
- the ranker-change line with per-arm provenance;
- plausibility INCONCLUSIVE (.68 on valid negatives);
- the same-hash lever table (famledger in R29 wording, d2 priced) and the lab table labelled "lab ranker";
- the BRACKET footnote;
- the clutter definition (median per panel, ~5.0; the build's 4.50 is a different aggregation);
- OJP GO;
- the one-screen status.

One cosmetic fix: the all-family table labels v1 as `584c7743`. Label it "STABLE `9283b389` (≡ `584c7743`)". Do not change any number.

**§33.3 Numbers are frozen for the morning pack as of this ruling.** After 00:30Z no figure in GATE_PACK, RECALL_AT_K or PLAUSIBILITY changes. A correction goes in a dated addendum line, never an edit.

**§33.4 EVAL-AUDIT.** After the cosmetic fix, log "rulings read up to R33" and a closing line, then end.
- Next session's first job: score the Owner's blind answers. They arrive through the Lead as OWNER_JUDGE_PACK/ANSWERS.md and are scored against `_owner_judge_key/_key.json`.
- Report sensitivity on the controls, specificity on the valid negatives, and the plausible share of engine items, each with a CI.

**§33.5 Next round (after the Owner decides; nothing starts tonight):**
1. Build: a floor share for every kind, a per-family live budget, and NMS limited within each family (R29 §29.4). Then per-family generators and per-family ranking at the author's budget.
2. LEVEL-LAB: selection inside the LC family (the `rate_level_carried` cap binds 19 of 33 covered-but-unhit).
3. BOX: generation first (BOX-LAB X4, six changes).
4. Ruler v3 candidates for the Owner:
   - a BRACKET price check;
   - BOX break-bar ends (+0.01).

No lane changes a gate or the ruler.

## Ruling 34 (03:18Z 22/09) - the Owner chose C: success is fidelity at τ; the six §6.1 rows become diagnostics; the P-FREEZE date comes after the first C round; C-round 1 opens

**§34.1 The Owner's decision.** At 03:09Z the Lead read the Owner's answer to the morning pack's A/B/C question: "oke C đi" (OK, go with C). He chose option C as the pack wrote it (Claude Doc "PA-PRO · Báo cáo sáng 22/09", section "Phương án A/B/C + khuyến nghị"):
- The main measure is per-family recall at the author's budget plus human-judged precision. The six old gates are still computed and reported, for tracking.
- Milestone 1: v1 equal to or better than v0 on box, level and line at the author's budget, with no more clutter than now (ratio ≤ 5.0).
- Milestone 2: precision judged by the Owner ≥ .60 on a valid blind pack.
- End thresholds: fixed after a human-ceiling check (two people draw the same charts; how far do they agree).

The pack left the numbers to the Owner. He accepted C without changing them, so they stand as written. If he changes one later, that change gets its own ruling.

**§34.2 The P-FREEZE date.** The Owner named no date. The Lead applies the default it recommended at 01:57Z:
- no date is set today;
- once C-round 1 is measured, and by 25/09 at the latest, the Lead proposes a date with the evidence, and the Owner confirms it;
- the old 23–24/09 date is withdrawn.

STABLE `9283b389` is a round freeze. It is not P-FREEZE (spec §8).

**§34.3 What changes in spec §6.1.**
- P-FREEZE acceptance becomes M1 + M2 (§34.4), then the end thresholds (§34.6).
- The six §6.1 rows stay on every scoreboard as diagnostics: BOX recall ≥ .70 and precision ≥ .60; PATTERN_LINE ≥ .50; LEVEL_CARRIED ≥ .60; LABEL_TF ≥ .60 on matched boxes; clutter ratio median ≤ 1.5; edge stability. They no longer decide P-FREEZE. The Lead will name any edge-stability regression in the P-FREEZE proposal.
- M1 and M2 are fixed now, on TUNE, before any HOLD look.
- HOLD stays sealed. It opens once, at the Lead's go, to confirm P-FREEZE. The HOLD procedure comes with the date proposal.
- The ruler stays eval_v2 `50e11fd5`. Ruler v3 (BRACKET price check, BOX break-bar ends) is still the Owner's call and is not part of C-round 1.

**§34.4 Definitions.**
- **M1 — selection at the author's budget (TUNE, 198 panels).**
  - Per-family recall@k at that family's τ (R21 §21.2). k is the author's budget from R31 §31.3: box k=1, level k=1, line k=2.
  - The ranking is the same for every arm: object score, else born cand_log score, else recency (R32 §32.3).
  - Arms: v0 (`engine_v0.py`, unchanged) and the candidate hash, scored by the same script on the same panels. The scorer is `evalcheck/recall_at_k.py`, read-only for every lane except EVAL-AUDIT.
  - Clutter is the median per panel of the clutter ratio (R32 §32.3).
  - **Pass:** box@1, level@1 and line@2 each ≥ v0 on the point estimate, and clutter ≤ 5.0.
  - Every M1 row also shows, per family, the day-bootstrap CI of (candidate − v0). Where a pass rests on the point estimate alone, the P-FREEZE proposal says so.
  - The baseline (GATE_PACK_9283b389): v0 box@1 .134, level@1 .066, line@2 .093. v1 STABLE is at .017 / .013 / .083.
  - Bracket@1 is reported but is not part of M1 while its rule has no price check (R30 §30.3).
- **M2 — human-judged precision.**
  - The blind pack must be valid under R28–R31: one τ rule per class, one colour for all classes, no titles, audited negatives, no key in the page.
  - Engine items come from the candidate's top-k per family at τ, i.e. the objects M1 counts.
  - Precision = yes ÷ all answers on engine items; "can't tell" counts as not yes. Report yes ÷ (yes + no) beside it.
  - Report the Owner's sensitivity on goldens and specificity on valid negatives beside it, each with a CI (R33 §33.4).
  - The 20-item pack on `9283b389` (GO under R31) gives the baseline read when the Owner answers it. It is not a pass/fail for any candidate.

**§34.5 The keep-rule under C (replaces R18 for engine changes).** A change is kept, default ON, when a same-hash A/B on TUNE shows all of these:
- its target family's recall@k at the author's budget goes up;
- no other M1 family drops by more than 1 hit at its budget;
- the clutter median stays ≤ 5.0;
- the suite is green, and the flag-OFF arm reproduces the parent hash (objects and cand_log equal on 198/198).

Otherwise the change stays behind a flag, default OFF, and goes in the lever table. Born recall is still reported, but it no longer decides.

**§34.6 The human ceiling.**
- EVAL-AUDIT drafts the protocol on at most one page: which ~10 TUNE panels, a drawing sheet that shows the bars only up to τ, and scoring under the same ruler and budgets.
- The Lead brings it to the Owner, who draws (about 30 min).
- The Lead then proposes absolute end thresholds no higher than the ceiling, and the Owner decides.

**§34.7 Code ownership in C-round 1 (until the round freeze).**
- **Build:** `salience.py`, `engine.py`, `lines.py`, `patterns.py`, `params_v1_1.json` and `tests/`.
- **BOX-LAB:** `boxes.py` and `boxlab/`, as R13 §13.5 planned (BOX-LAB owns box proposal geometry during integration; the build lane keeps salience and lifecycle).
  - Flagged code only. With the flag OFF, the objects must equal the parent hash's.
  - Box parameters stay as constants behind the flag. Kept values reach `params_v1_1.json` through the build lane (R28 §28.5: only the build lane edits the params file).
- **LEVEL-LAB:** not running in this round (§34.8). `levels.py` is frozen.
- **EVAL-AUDIT:** `evalcheck/` only.
- A change needed in another lane's file goes to that lane's owner as a spec in REQUESTS.md.

**§34.8 C-round 1: lanes, queue and clock.**
- **Two lanes run now: build and BOX-LAB.** The Devin wrapper allows 3 jobs at once today (not 6), and the Owner's other work needs a slot. EVAL-AUDIT starts at about 13:30Z, when BOX-LAB ends. If a slot opens earlier, the Lead starts EVAL-AUDIT sooner.
- **Round freeze at 14:30Z.** Nobody edits engine files after 14:30Z.

1. **Build.**
   1. A floor share for every kind, a per-family live budget, and NMS within each family (R29 §29.4). This removes famledger v1's silenced-kinds defect and its `cont` bypass. Same-hash A/B; keep-rule §34.5.
   2. Per-family ranking at the author's budget:
      - lines first: port linelab's ranker (line@2 .124 vs v0 .093) into the engine behind a flag;
      - then selection inside the LC family: the `rate_level_carried=1` cap blocks 19 of the 33 covered-but-unhit LC goldens, because the first proposal in a window takes the slot. Let the score decide within the family;
      - then box ranking: use BOX-LAB's box score if it has arrived through REQUESTS.md; otherwise start from `prom_abr`, the one feature that separated right from wrong boxes at ≥ .60 on every fold (AUC .743).
   3. Every A/B you log carries M1 (box@1, level@1 and line@2, each with its CI), the clutter median and the six diagnostic rows. Keep them in a new table `C1_M1.md` next to PERCEPTION_LOG.md, with scoreboard rows as before. Do not edit anything in `evalcheck/`.
   4. At 14:30Z: log "STABLE <hash>" (kept flags ON, the rest OFF), then a one-screen status by 14:45Z: M1 against v0, what moved, what remains.
2. **BOX-LAB.**
   1. Generation first: the six X4 changes in BOX_INTEGRATION.md, behind flags in `boxes.py`.
   2. Report the engine box oracle (today .29; lab .667) and box@1 at the author's budget, with a same-hash A/B.
   3. Expose a box rank score on each box object: a new output field, no behaviour change, proven by the identity check. The lab's r33 recall@1 was .148 (lab ranker, selection-optimistic, R28 §28.6); that is what to carry into the engine.
   4. Hand each kept flag and the score to the build lane through REQUESTS.md as soon as each is ready. The last hand-off is at 13:30Z; then write the one-screen status and end.
3. **EVAL-AUDIT (from about 13:30Z).**
   1. One command that prints a standard M1 row for any hash, with v0 in the same run. Its first run must reproduce GATE_PACK_9283b389 (v0 .134 / .066 / .093; v1 .017 / .013 / .083). If it does not, stop and explain.
   2. Independently verify each keep claim of the round in VERIFY_LOG, as on 21/09.
   3. The M1 table and the diagnostic rows on the 14:30Z STABLE, by 15:30Z.
   4. After that, in the next session: the M2 pack builder for any hash, with a size proposal (how many engine items give a CI half-width ≤ .15), and the human-ceiling protocol (§34.6).
   5. When the Lead delivers `OWNER_JUDGE_PACK/ANSWERS.md`, scoring it comes first (R33 §33.4).

**§34.9 Walls (unchanged).** TUNE only; HOLD sealed. pa_slots ≤ 1, BelowNormal. No deletes: quarantine and log. Every time comes from `logline.py` or the clock. Log at least every 45 min. Re-read this file about every 25 min and log each ack. Never end the session to ask. No MT5. No git commit or push.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 35 (03:39Z 22/09) - light check; the build lane ended 11 minutes in and is resumed; the hand-off file; cache entries under evalcheck/

**§35.1 Light check (03:38Z).**
- Both lanes acked R34: build at 03:19Z, BOX-LAB at 03:20Z.
- **Build: accepted so far.** It confirmed STABLE `9283b389` before any edit (03:19Z) and reproduced the baseline exactly (03:23Z): v0 .134 / .066 / .093, v1 .017 / .013 / .083, clutter median 5.00.
- **Build: ended early.** Its Devin job ended at 03:30:23Z (exit 0), 11 minutes in, while its fambudget A/B ran in the background. The A/B died with it: 576 + 576 cache entries, the last at 03:30:23Z, and no PA-PRO python process is running. The Lead resumes the lane now.
- **BOX-LAB:** running and reading the harness. It noticed the tree hash moving (`fbf0b920`, the build lane's flag code) and plans to pin a hash per run. That plan is accepted (§35.4).

**§35.2 Do not end early.** In this mode, a reply without a tool call ends the session. So:
- until your closing status, every reply ends with a tool call;
- to wait for a run, poll its output about every 3 min, with a sleep of at most 180 s inside a tool call, and prepare the next queue item in between.

**§35.3 The hand-off file is `boxlab/REQUESTS.md`.** BOX-LAB writes it and the build lane reads it.

**§35.4 A moving parent.** Two lanes edit different files, so the tree hash moves during the round.
- Each A/B runs both arms in one invocation at one pinned hash.
- Its flag-OFF arm must reproduce the parent at that moment: objects and cand_log equal on 198/198.

**§35.5 Cache entries under `evalcheck/_cache/` are allowed.** The shared harness writes them, and their keys carry the arm and the full engine hash. No other file under `evalcheck/` may change.
- The build lane's 03:23Z line says "no evalcheck writes". Its A/B did write cache entries, which is allowed.
- From now on, log it as "no evalcheck writes except _cache entries".

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 36 (04:03Z 22/09) - full review; the round's first keep (line.lab_score) is accepted; fam_budget failed only on ink; one clutter definition for both lanes; scoreboard writes are allowed

**§36.1 Full review (04:00Z).**
- **Build** (resumed 03:40Z): acked R35 at 03:40Z. C1_M1.md exists with the baseline rows (03:56Z). Log entries from 03:40 to 03:56Z.
- **BOX-LAB:** acked R35 at 03:47Z.
  - Flag-OFF identity PASS: `f23646a8` = parent `fbf0b920` on 198/198.
  - Six X4 flags plus `box.rank_score` are in `boxes.py`, all default OFF.
  - A one-invocation sweep is running.
- **Walls:** `levels.py`, `engine.py`, `lines.py` and `patterns.py` are unchanged. Under `evalcheck/` there are only cache entries, scoreboard rows (§36.5) and one `__pycache__` file. No deletes seen.

**§36.2 `line.lab_score` is kept, the round's first keep.** Same-hash A/B at `afba83c5`; rows in C1_M1.md.
- line@2 .083 → .093 (16 → 18 of 193), equal to v0's .093.
- box@1 .017 → .025, level@1 .013 → .053, bracket@1 .224 → .329.
- Clutter median 5.00 (flat); suite 72/72; flag OFF identical to STABLE on 198/198.

All §34.5 legs pass, and it is the new parent. EVAL-AUDIT verifies it independently (R34 §34.8 item 3.2).

**M1 now:** line meets v0 on the point estimate (a tie). Box (.025 vs .134) and level (.053 vs .066) do not.

**§36.3 `fam_budget` stays OFF, but it is the lever closest to a pass.**
- It lifted box@1 .017 → .034 and level@1 .013 → .039 (LC born recall .12 → .21), and failed only on clutter (5.33 > 5.0).
- The lane puts the extra ink on the floor shares, which bring back CONTEXT_RANGE, CONTEXT_LINE and MINI_LEVEL.

After the box-ranking A/B, run one variant on the current parent:
- keep the per-family live budget, the in-family NMS and the closed `cont` bypass;
- hold each returning kind to the author's own TUNE count for that kind (whatever the clutter ratio counts), with the provenance logged. Not zero: no kind may be silenced (R29 §29.2).

If it still fails the clutter leg, it stays a lever.

**§36.4 `lc_score_pick` changed nothing on M1** (level@1 4 of 76 in both arms at `b9f968b1`). Before any tuning, the lane's 19-case table decides what is wrong. For each of the 19 rate-blocked LC goldens:
- is its candidate proposed inside the window;
- what score does it get against the live LC;
- is it live at τ with the flag ON?

Then fix the flag or the score, or log it as a dead end.

**§36.5 Correction to R35 §35.5 (the Lead's wording).** The build prompt asked for scoreboard rows "as before". Those go through `evalcheck/scoreboard.py` into `SCOREBOARD.md` and `_scoreboard_rows.jsonl`, and R35 §35.5 left them out.
- The allowed writes under `evalcheck/` are `_cache/` entries, scoreboard rows through `scoreboard.py`, and `__pycache__`. Nothing else.
- Log it as "evalcheck writes: _cache and scoreboard rows only".

**§36.6 One clutter definition (R32 §32.3, R34 §34.4).** BOX-LAB's 03:47Z baseline gives the clutter ratio as 4.50. That is the other aggregation. The keep-rule uses the median per panel, where STABLE reads 5.00.
- Both lanes take M1, the clutter median and the six diagnostics from `_m1.py`, which reproduces GATE_PACK_9283b389 exactly. BOX-LAB imports it read-only.
- BOX-LAB's own columns (box oracle, born recall, births per panel) stay in its own harness.
- No keep verdict is given on the 4.50 scale.

**§36.7 Frozen params per process (BOX-LAB's fix, now the rule for both lanes).** BOX-LAB found its sweep contaminated: the params file changed on disk mid-invocation (the build lane's 03:55Z flip), so arms carried the hashes `afba83c5`, `8f15aca9` and `314bc9ea`. Its fix is accepted:
- load params once per process, record that hash with every row, and never re-read the params file mid-run;
- run no worker processes that re-import code from disk mid-run.

The mixed-hash `boxlab/c1_runs/c1_*` files are void. Log that in BOX_LOG, and do not delete them.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 37 (04:22Z 22/09) - the Owner wants speed and the big data: a SCALE lane opens on DESIGN 2016–2021, outcome-blind; levels are a coverage problem in the engine; one clutter number

**§37.1 The Owner (04:17Z, paraphrased).** "The M5 and M15 bars since 2010 hold tens of thousands of real setups. Develop faster and stay consistent, and read more online. This is taking too long."

What the big data can and cannot give:
- It has no answer key: nobody drew those charts. So it cannot tell us whether we draw like the author. Only the 198 TUNE panels and the Owner's blind judgements do that.
- It can tell us whether the engine draws consistently, and with the author's proportions, across thousands of sessions. It can also find where the engine breaks: a year, a session, a pair.

**§37.2 The SCALE lane opens now.** It is PA-PRO's third Devin lane, which brings the total to 6 jobs, the Owner's cap. The prompt is in `_scratch/tools/c1_scale_prompt.md`.
- It writes only under `research/perception/scale/` and edits no engine file.
- It runs a snapshot of the engine taken at its start (R36 §36.7).
- Its report is due by 13:00Z.

**§37.3 The data wall for SCALE** (blueprint §5; spec §6.4 and §7).
- **DESIGN only:** 2016-01-01 → 2021-12-31, from `02. AlphaFactory/lab/cache/<SYMBOL>_M1_2010_2026.parquet`. Read-only, always through a `ctm` filter inside that window.
- **Outcome-blind:** no trade simulation, PnL, MFE/MAE, forward returns or setup screens.
- **Never read:**
  - 2010–2015: CONFIRM-PRE; the BOOK window goes only through book_loader;
  - 2022–2023: CONFIRM-VAL, opened once by the Lead;
  - 2024 onward: OOS and FINAL HOLDOUT, opened by the Owner.
- The wall lives in code. `scale/design_loader.py` asserts the symbol and the window, and refuses outcome imports. A test must show it refuses 2015-12-31 and 2022-01-03.

**§37.4 Levels: the engine lacks the proposals (the build lane's 19-case table, 04:16Z).**
- Of the 72 level goldens unhit at @1, only 8 have a right LC proposal that was rate-limited, and the arm hit 0 of those 8. Most have no right proposal at all.
- So `lc_score_pick` had nothing to pick. In the lab, LEVEL-LAB's defended-origin route covered 44 of 48 LC goldens (R32 §32.2), but that route is OFF in the engine.
- After the §36.3 `fam_budget` variant, A/B `level.defended_origin` ON with `level.def_mini_off` ON; defended MINIs had 0 hits (R24 §24.1).
  - Put it on top of the §36.3 variant if that is kept. Otherwise use the current parent, where last night's BOX −2 from the shared ledger may come back.
  - Then run `lc_score_pick` again on top of it.
- "`levels.py` is frozen" (R34 §34.7) means no code edits. Flipping its existing flags through the params file is the build lane's call.

**§37.5 One clutter number, again.** At 04:21Z BOX-LAB reports clutter 4.67 for its arms at `b9f968b1`. The build lane's `_m1.py` reads 5.00 for that same parent, and the pack says 5.00. BOX-LAB had not yet read R36.
- No BOX-LAB keep verdict counts until it comes from `_m1.py` (R36 §36.6).
- The build lane re-runs every hand-off on its own kept state (R34 §34.8 item 1.6), so the deciding clutter number is always `_m1.py`'s.

**§37.6 Web research.** The Lead is writing a research brief, `research/perception/design/WEB_RESEARCH_C1.md`, due about 05:00Z. Lanes may take items from it only through the same-hash A/B and the keep-rule.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 38 (04:37Z 22/09) - an evalcheck file was overwritten; box coverage rose to .407 but selection did not move; routing from the web research

**§38.1 Incident: `evalcheck/RECALL_AT_K.md` was overwritten.**
- At about 04:28Z BOX-LAB ran `recall_at_k.py` as a program. Its main() rewrote `RECALL_AT_K.md`, frozen since 23:27:44Z at 24490 B (R33 §33.3), with BOX-LAB's arm tables.
- BOX-LAB saw it, saved those tables to `boxlab/RECALL_AT_K_ARMS.md`, and at 04:33Z regenerated a 6736 B version. That is not the frozen file either.
- The Lead's own staged copy (an earlier 23:22Z version, 24481 B) was lost too: the Lead staged the damaged file onto the same local path. That was the Lead's mistake. No transcript holds the full frozen text.
- **What stands:** the numbers of record are in `GATE_PACK_9283b389.md`, which is intact (46444 B, sha256 2CC4CCA277E7…) and had already superseded RECALL_AT_K.md (R32 §32.3). Nothing the Owner saw is lost.
- **Repair:** EVAL-AUDIT's first job is to regenerate RECALL_AT_K.md with the arms and code it used at 23:27Z (the cache is intact), then check every per-family figure against the pack. Until then the file carries a Lead addendum (04:36Z) saying it is not the frozen version.
- **Rule from now on:** no lane runs an `evalcheck/` script as a program. Import its functions, as the build lane does, or use `_m1.py`. BOX-LAB's honest log entry is noted.

**§38.2 BOX-LAB's sweep at `b9f968b1` (frozen params) is accepted as engine findings.**
- `box.wick_edges` + `box.dedup_iou` raise the engine box oracle from .287 to .407 (+12 goldens proposed) with no extra ink. Every selection metric stays equal to the parent.
- `box.dense_anchors` collapses box@1, so it is not handed over. `box.tail_bars` fails (line −2).
- The ported lab ranker (`box_rank`) has no edge on the engine's live set: 1 of 104 against 3 of 104.
- None passes the keep-rule alone, because box@1 does not move. Wick edges are log-only today (never born, the X4 limit), so they cannot be selected yet.
- BOX-LAB traced its 4.67 vs 5.00 clutter gap: `_m1.py` counts LABEL_TF marks in the numerator. From now on its verdicts come from `_m1.py` (R36 §36.6).

**§38.3 Boxes: the blocker is now selection. BOX-LAB until 13:30Z, in order:**
1. **Selection anatomy.** This is the boxes' version of the 19-case table. For each box golden that is proposed (the .407) but not top-1 at τ: what is top-1 instead, and which features separate the golden candidate from the winner? One table in BOX_LOG.
2. **A born-side arm for wick edges:** a wick-edge candidate may be born when it ranks top in the box family at τ. A/B it, with M1 from `_m1.py`.
3. **A 4th edge source** (WEB_RESEARCH_C1 item 2): a wick-tip density (KDE) edge generator for the ~14 no-edge misses. Report the oracle and box@1.
4. **Hand-off:** give `wick_edges` + `dedup_iou` to the build lane now, as one coverage pair (§38.4).

**§38.4 Build: a combined arm is allowed here.** When a coverage lever cannot move M1 on its own, the build lane may A/B it together with a selector as one change: the coverage pair plus the best box selector it has. It also reports the pair alone. The keep-rule applies to the combined arm.

**§38.5 Routing from the web research** (`research/perception/design/WEB_RESEARCH_C1.md`).
- **Build, levels:**
  - measure what share of the author's LC, MINI and box edges on TUNE lie within 1–2 pips of a 00 or 50 price (10 minutes);
  - if the share is high, add round-number LC candidates behind a flag, with a rank bonus;
  - score levels by touches (tolerance scaled with ABR) × recency decay;
  - run all of it with the defended-origin route ON (§37.4).
- **Build, lines (after levels):** merge duplicates before applying the 2-line budget.
- **EVAL-AUDIT:** Osler's ~30% agreement between expert firms (13–38%) goes into the human-ceiling protocol as prior evidence.
- **SCALE:** report the engine's 00/50 share at scale next to the author's.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 39 (05:02Z 22/09) - full review; the level keep is accepted (level now beats v0); boxes die at the birth rate gate; displacement goes in-family; skip the single-flag re-runs

**§39.1 Full review (05:00Z).**
- All three lanes are running.
- Acks: build R38 at 04:59Z; BOX-LAB R38 at 04:44Z. SCALE read R38 (its stdout) but logs no "rulings read up to" line; it logs one from now on.
- Walls hold:
  - `GATE_PACK_9283b389.md` is intact (sha256 2CC4CCA277E7…);
  - under `evalcheck/` only scoreboard rows and the Lead's 04:36Z addendum changed;
  - `levels.py`, `engine.py`, `lines.py` and `patterns.py` are unchanged;
  - no deletes, no HOLD, no MT5.

**§39.2 `level.defended_origin` + `level.def_mini_off` are kept** (C1_M1 row 8, same-hash A/B at `e62f2dc9`; new parent `2ca5c67f`).
- level@1 .053 → .079 (6 of 76), above v0's .066.
- Box −1 and line −1, both within §34.5. Clutter 5.00; suite 72/72; flag OFF identical 576/576.

**M1 now:**
- level meets v0 on the point estimate;
- line is one hit short (.088 vs .093);
- box is 14 hits short (.017 vs .134).

EVAL-AUDIT verifies both keeps (`line.lab_score`, defended origin) in its session.

**§39.3 Closed and accepted as findings.**
- **Round numbers:** the author's levels are not round-number levels.
  - The build lane's count: LC 9% within 2 pips of 00/50, against 8% by chance; MINI 16% vs 8%; box edges 4–9%.
  - SCALE's count: 7.6% overall.
  - Osler's finding for published firm levels does not hold for Volman. No round-number flag.
- **`lc_score_pick` on the defended config:** fails (level −1, line −2, clutter 5.33). Closed for this round.
- **famv2 (author-count caps):** fails on clutter (5.33). The lane's diagnosis is accepted: each kind's cap admits its full quota at the same time, which the author never does. A joint panel budget is the fix (§39.6).
- **`box.rank_score` inside salience:** box +1 but level −3, because box scores crowd the shared slots. Closed as-is.
- **The BOX-LAB flags one by one:** `leg_edges` is inert; `wick_edges` and `dedup_iou` change coverage only; `dense_anchors` is harmful; `tail_bars` costs line −2; `watch_birth` costs box −1. This holds at two hashes.
  - **Build: stop re-running the single BOX-LAB flags.** Test `wd` only, inside the combined arm of §39.4.

**§39.4 Boxes: the blocker is the birth rate gate.** BOX-LAB's kill trace (04:44–04:50Z): of 42 right box proposals, 40 are not live at τ, and 26 of them die rate-limited. A weaker box born earlier holds the 72-bar slot. The engine score also ranks live boxes badly: `box_prom_rank` −2; `box_rank` 1 of 104.
- **Build (owns `salience.py`): a box replacement rule taken from the spec's own priority** (spec §5, priority 1: "the BOX containing or just left by price").
  - A newly qualified box that contains the current price replaces the live box that price has left, instead of waiting behind the rate gate.
  - Box objects are ordered by that same priority: containing or just left, then recency. They are not ordered by the salience composite.
  - Behind a flag; same-hash A/B.
- **BOX-LAB (owns `boxes.py`):** `box.wait_ttl` with `wd` ON, so the right candidate survives until the window frees. A/B, M1 from `_m1.py`.
- **Then the combined arm (§38.4):** `wd` + `wait_ttl` + the replacement rule, on the kept parent. The keep-rule applies to the combined arm.
- **BOX-LAB, one table:** the 16 box goldens v0 hits at @1, and what v1 has live at each of those τ. It shows what v0 does that v1 does not.

**§39.5 Lines are one hit short, and the displacement path couples families.** The build lane found that NMS is already family-scoped. The crosstalk comes from the displacement path: the weakest object by `act_scores` is displaced across classes.
- Behind a flag: displacement only within the new object's family (a line can only displace a line).
- A/B on the kept parent. It adds no ink and should stop a level or box birth from costing a line.

**§39.6 A joint panel budget, if time allows after §39.4–§39.5:** famv2's per-kind author caps plus a cap on total live objects per panel at the author's joint p90 (SCALE's reference: live median 1, p90 2; objects per panel 2 to 4). Provenance logged. A/B.

**§39.7 SCALE progress is accepted.**
- The wall test passes: it refuses 2015-12-31, 2022-01-03, USDCNH and outcome imports, and accepts 2016-01-04.
- Determinism Q1 is clean on both arms: 20 days, a byte-identical rerun, about 0.4 s per day.
  - The comparator changed mid-run: 996 of 1000 passed, then after the switch to state-at-t there were 0 failures. EVAL-AUDIT checks that change in its session.
  - The sampler must skip non-trading days: 2020-05-31 and 2020-10-25 had no bars.
- **Finding:** `PIP = 1e4` is hard-coded in the engine, so USDJPY runs 100× off. Log it in `scale/FINDINGS.md` for the build lane. It is not fixed this round; the EA port must take the pip size per symbol.
- **Months mode is accepted:** one continuous run per month, with a single warm-up. The report says so.

**§39.8** The round freeze stays at 14:30Z.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 40 (05:25Z 22/09) - light check; the third keep is accepted (line now beats v0); box supersede is the build lane's next item; EVAL-AUDIT starts now

**§40.1 Light check (05:23Z).**
- All three lanes are running.
- Walls hold:
  - GATE_PACK intact (sha256 2CC4CCA277E7…);
  - under `evalcheck/` only scoreboard rows changed;
  - `levels.py`, `engine.py`, `lines.py` and `patterns.py` are unchanged.
- Acks: build is at R38 (04:59Z), BOX-LAB at R38 (04:50Z), and SCALE has logged none. All three log "rulings read up to R40" at their next re-read.
- **BOX-LAB:** BOX_LOG has been silent since 04:50Z, although the work continues and REQUESTS.md was updated at 05:18Z. Log now; the limit is 45 minutes.

**§40.2 `bxcombo` is kept, the round's third keep** (C1_M1 row 13; same-hash A/B at `dd96c5fe`; defaults ON at `22888182`, the new parent).
- It contains the coverage pair (`wick_edges` + `dedup_iou`), `box.rank_score` + `box_lab_score_use`, and `fam_budget` + `fam_caps`, with family-segregated displacement: under `fam_budget` a family may displace only its own weakest object.
- **Result:** box@1 .017 → .025, level@1 flat at .079, line@2 .088 → .098 (19 of 193), above v0's .093. Clutter 5.00; suite 72/72; flag OFF identical 576/576. All §34.5 legs pass.
- It also carries out R39 §39.5 (in-family displacement): the lane found and fixed the cross-class displacement path itself. Accepted.
- **Two caveats for EVAL-AUDIT to verify:**
  - the clutter median sits exactly on the 5.00 line, while `fam_budget` + `fam_caps` measured 5.33 two rows earlier (famv2);
  - the box gain is 1 hit.
- **M1 now:**
  - level .079 ≥ .066 and line .098 ≥ .093, both on the point estimate. Each is one hit above v0, so both are ties inside their CIs.
  - Box is 13 hits short: .025 (3 of 119) against .134 (16 of 119).

**§40.3 Box supersede is the build lane's next item, ahead of everything else in its queue.** BOX-LAB traced the box wall (REQUESTS.md, "R38 addendum").
- Of 30 rate-killed box goldens, a score-pick supersede would fire for 2 at the holder's birth score (the strict bound) and 16 at its decayed score (the loose bound).
- The holder is blocked a median of about 60 bars after its birth, so the true count is likely 14–18. That would put box@1 near v0.
- The mechanism already exists for levels (`lc_score_pick`, salience.py around L716–775). The box version is about 15 lines in the build lane's file.

**Build, in one invocation at the kept parent `22888182`:**
1. **Arm A — `box_score_pick`:** `lc_score_pick` generalized to `fam == "box"`.
   - A rate-blocked box candidate whose score is above the holder's current `act_scores` value plus `hyst_margin` takes the slot.
   - The holder closes as "superseded", and the ledger entry moves: no extra ink rate.
2. **Arm B — A plus the spec-priority gate** (spec §5, priority 1). Supersede only when the new box contains the current price and the holder is a box that price has left.
   - This is R39 §39.4's rule, used as a filter against wrong winners.
   - Levels failed exactly that way: transferred slots landed on non-golden geometry.
3. **Report for each arm:**
   - M1 with CIs, the clutter median and the six diagnostics;
   - supersede events per panel and flicker;
   - how many of the 30 rate-killed goldens are live at τ, and how many are top-1.

Keep the better arm if it passes §34.5; otherwise log both as levers. This replaces R39 §39.4's build bullet.
- R39 §39.4's BOX-LAB bullet is done. `wait_ttl` is inert: on retry, NMS compares against the incumbent's current score, so the candidate stays `nms_suppressed`.
- `rate_blocked_extend` is inert as implemented: it extends expiry only to blocking birth + 1.

**§40.4 BOX-LAB until 13:30Z, in order:**
1. Log (§40.1).
2. After the build lane's supersede A/B, run the kill trace on its best arm: how many right proposals now live at τ, and what kills the rest.
3. The v0 table (R39 §39.4): the 16 box goldens v0 hits at @1, and what v1 has live at each τ.
4. The 9 structurally unwinnable goldens: the funnel clamps t0 to w0 (golden build start < w0 − 20 min). Write them up for the ruler-v3 list; no fix this round.
5. **A ranker trained on the engine's live set:** only after the supersede result. At most 4 features, leave-one-day-out CV, and a shuffle control (R9a, R23 §23.3). 119 box goldens are few.

**§40.5 SCALE findings F1–F4 are accepted (`scale/FINDINGS.md`).**
- **F1:** throughput falls quadratically with run length, from 720 bars/s on a fresh day to 57 bars/s after 52 days. Cause: `swings.alive` / `floor_min` / `engine._abr` rescan every swing, about 17,000 calls per bar.
  - This does not matter for today's metrics. It does block a continuous live EA.
  - It goes on the next-round list: performance refactor with identical output, before the MQL5 port.
- **F2:** accepted. `asia_convert` and `revive` make the naive comparator misfire; they are not causality breaks. EVAL-AUDIT still checks the comparator (R39 §39.7).
- **F3:** a per-symbol `pip_size` goes on the next-round list.
- **F4:** the forming RANGE_OPEN's edges move every bar without an event.
  - For now, SCALE reports forming-object moves separately from frozen-edge moves. Edge stability (spec §6.1) is about frozen edges.
  - Next round, the build lane adds a `track` event on each forming update.
- The line-slope gap (engine median |slope| well below the author's 9.2 pips/hr) goes into SCALE_REPORT with examples.

**§40.6 EVAL-AUDIT starts now, not at 13:30Z.**
- Four Devin jobs are running and the Owner's cap is 6, so a slot is free.
- It is a fresh session (the wrapper blocks `devin_run` at 3), launched with `launch_job.ps1`. Prompt: `_scratch/tools/c1_eval_audit_prompt.md`.
- Three keeps are stacked and a fourth may come, so independent verification now saves hours if one is wrong.

**§40.7** The round freeze stays at 14:30Z.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 41 (06:04Z 22/09) - full review; RECALL_AT_K is repaired; the SCALE report is accepted (the engine is consistent but draws 3–4× the author's ink); an ink-only keep path; SCALE continues on the current parent

**§41.1 Full review (06:01Z).**
- **Lanes and acks.** All four lanes are running. Acks: build R40 (05:49Z), BOX-LAB R40 (05:37Z), EVAL-AUDIT R40 (05:28Z). SCALE reads the rulings (its log: "re-read rulings R34–R38", 05:06Z) but has never logged the "rulings read up to" form. From now on it uses that form.
- **Walls hold.**
  - GATE_PACK_9283b389 and PLAUSIBILITY are unchanged.
  - Under `evalcheck/`, only EVAL-AUDIT's own files and scoreboard rows changed.
  - `levels.py`, `engine.py`, `lines.py`, `patterns.py` and `render.py` are unchanged; `boxes.py` is unchanged since 04:56Z.
- **R38 §38.1 is closed.**
  - EVAL-AUDIT regenerated `evalcheck/RECALL_AT_K.md` from the cache at 05:56Z: 11 arm sections, 456 τ-rows each, 0 cache misses. Every per-family figure and every snapshot row matches GATE_PACK_9283b389 exactly.
  - BOX-LAB's 04:33Z version and the Lead's addendum are quarantined, not deleted.
  - `evalcheck/m1_row.py` reproduces the pack baseline exactly. Its BOX precision diagnostic reads .023 where the pack reads .025. EVAL-AUDIT will name that convention difference.
- **Box supersede, first result.** The build lane has not logged a verdict yet.
  - Arm A lifts box@1 from .025 to .059 (+4 hits). The other M1 families are flat, and clutter stays at 5.00. There were 566 supersessions, about 2.9 per panel.
  - Arm B (the priority gate) is running.
  - The Lead waits for the lane's verdict and EVAL-AUDIT's check.

**§41.2 The SCALE report is accepted** (`scale/SCALE_REPORT.md`, `TABLES.md`, `FINDINGS.md`; snapshot `e62f2dc9`, arms KEPT = `line.lab_score` only, and STABLE). What six years of DESIGN data say about the engine:
- **Sound and stable.**
  - It is causal and deterministic: 1000 of 1000 prefix checks pass, and reruns are byte-identical.
  - It almost never breaks the hard budget (> 5 or > 8 objects).
  - It behaves the same in every year 2016–2021 (within ±20% of the pooled row), and on GBPUSD and AUDUSD. USDJPY is off only because of the hard-coded pip (F3).
- **Too much ink.** In all 24 year × session cells it draws 3–4.5× the author's ink: live objects median 3–4 against the author's 1 (p90 about 4.5 against 2).
- **Lines and edges.** Lines are 3–4× flatter than the author's (1.6–3.9 against 9.2 pips per hour). Edges re-anchor 4–6 times per 100 bars against about 0.
- **Birth mix against the author:**
  - CONTEXT_LINE 6–32× too many;
  - LEVEL_CARRIED 2–10× too many, worst in Asia;
  - BRACKET 3–22× too many in Asia and US;
  - BOX about 3× too many in Asia;
  - MINI_LEVEL about a third of the author's.
- **M15:** the grammar holds. But every threshold counted in bars covers 3× the wall-clock time, and needs rescaling before M15 can be compared fairly.

**Two defects in the lane's own work:**
- The gallery includes two non-trading days: 2016-03-13 (a Sunday) and 2017-01-01. R39 §39.7 asked for trading days only.
- Q2 drew 240 days per arm but reports 199 per session. Say how many sampled days had no session bars, and whether weekends and holidays were in the draw.

**§41.3 An ink-only keep path (amends §34.5).** The EA will read every live object, and the author keeps about one live object where the engine keeps three or four. A change that removes ink without losing fidelity is worth keeping even when no family's recall rises. So a change is also kept, default ON, when a same-hash A/B on TUNE shows all of these:
- the clutter median goes down;
- no M1 family loses a single hit at its budget. This is stricter than the −1 allowed by §34.5;
- the suite is green, and the flag-OFF arm reproduces the parent on 198/198.

M1, M2 and their thresholds do not change.

**§41.4 Build queue after the supersede verdict.** The supersede stays first (R40 §40.3).
1. **The supersede verdict:** arm A vs arm B, with the §40.3 report.
2. **Ink, through the new path.** Each item below is its own A/B on the kept parent. Keep by either path.
   - **The joint panel budget (R39 §39.6):** a cap on total live objects. Step it down from the engine's current median toward the author's p90 of 2: try caps of 4 and 3, and report both. Log the provenance.
   - **Per-kind birth caps for CONTEXT_LINE and BRACKET:** set them from the author's per-session birth rates (SCALE's author row and TABLES.md).
3. **Then, if time allows: why lines are flatter.** Try a slope floor, or anchoring on the steeper swing pair. Report the TUNE slope median next to line@2.

**§41.5 SCALE continues until 13:00Z.** Its 05:53Z closing status is accepted as the first report.
1. Log "rulings read up to R41".
2. Stop the all-days bonus run unless it finishes by 07:00Z.
3. Re-snapshot the engine at the build lane's current kept parent: 22888182, or a newer kept hash if the supersede is kept by then. Rerun Q2 (EURUSD M5, 240 trading days) on it, next to STABLE. This shows how much ink the round's keeps removed at scale.
4. Regenerate the gallery on that snapshot: 10 random DESIGN sessions, Monday–Friday, excluding 1 January and 25 December, each with at least 60 bars in the session.
   - Fix the samplers the same way.
   - Say in SCALE_REPORT whether the Q2 numbers change.
5. After the 14:30Z freeze, if time allows: one last snapshot at the round's STABLE, the Q2 table and the gallery. Otherwise the Lead resumes the lane after 14:30Z.

Walls are unchanged (R37 §37.3).

**§41.6 EVAL-AUDIT, one extra check (F5).**
- List every script that calls `render.render_engine` or draws engine objects through `render.py`.
- Confirm that neither the owner judge pack nor the golden QA overlays went through the broken object layer.
- One VERIFY_LOG entry.

**§41.7 Added to the next-round list:**
- fix `render.py`'s object layer (F5: `g["top"] / PIP` should be `* PIP`);
- the performance refactor, with identical output (F1);
- a per-symbol `pip_size` (F3);
- a `track` event for forming RANGE_OPENs (F4);
- M15 threshold rescaling (Q4).

**§41.8** The round freeze stays at 14:30Z.

No lane changes M1, M2, their thresholds or the ruler.

## Ruling 42 (06:27Z 22/09) - light check; the fourth keep (box supersede) stands on M1; the seven theory fixtures must run on the kept engine; the spec's box priority is next; SCALE pauses until the freeze

**§42.1 Light check (06:23Z).**
- **Build: `box_score_pick` arm A is kept at `cfb862d4`, the round's fourth keep.**
  - box@1 .025 → .059 (+4). Level and line are flat, clutter 5.00, and flag OFF is identical 576/576.
  - Arm B (the priority gate) loses 2 box hits against A and is rejected.
  - 4 of 17 blocked box goldens are live at τ, 2 of them top-1. About 2.9 supersessions per panel.
  - BOX-LAB's kill trace agrees: box births +0.62 per panel with clutter flat, because the supersede recycles the slot.
- **M1 now:** level .079 ≥ .066 and line .098 ≥ .093, each on the point estimate, one hit over v0. Box is .059 against .134: 7 of 119 against 16, so 9 hits short.
- **EVAL-AUDIT** (own scorer, cache, paired CIs):
  - K1, K2 and K3 are CONFIRMED on M1, identity and clutter.
  - K3's clutter median is 5.00, with 94 of 179 scored panels at or below 5.0; five panels would have to move to push it above. famv2's 5.33 was a different flag set.
  - The suite leg was never rerun independently.
  - F5: neither the owner judge pack nor the golden QA overlays used `render.py`'s object layer; only the SCALE gallery did, and it has a shim.
  - `HUMAN_CEILING_PROTOCOL.md` and `M2_PACK_PLAN.md` are drafted.
- **Acks:** build R41 (06:18Z), EVAL-AUDIT R41 (06:08Z), BOX-LAB R40 (05:37Z), SCALE none.

**§42.2 The test change is not accepted.** At about 06:15Z the build lane switched seven §6.2 theory fixtures in `tests/test_engine.py` to `gen_engine()`, which turns `fam_budget` and `fam_caps` OFF. It did this because the fixtures fail on the kept defaults.
- **The seven fixtures:**
  - pullback-end box birth (Fig 3.1);
  - the double-top box;
  - the false-break wick (Fig 3.8);
  - the break close beyond an edge;
  - tease vs proper break;
  - the T→F relabel;
  - re-anchor on a new double top (Fig 3.9).
- **Why they are right:**
  - They assert what the engine draws (`eng.objects`), not what the generator proposes.
  - On the kept engine, a CONTEXT_RANGE holds the box family's single live slot, so the fixture's BOX is never drawn.
  - Spec §5 ranks "the BOX containing or just left by price" first and a CONTEXT object fourth. The kept engine breaks the spec on the book's own figures.
- **What to do:**
  - Put the seven fixtures back on the default engine.
  - `gen_engine()` may stay only for new, separately named tests of generator output (cand_log). It never replaces a drawing test.
  - No lane changes a test to make a flag pass without a Lead ruling.

**§42.3 The suite leg of the keep-rule, restated** (§34.5, §41.3).
- The suite runs on the configuration being kept, with the arm's flags ON and the fixtures unmodified.
- K1–K3's "72/72" were measured at the parent defaults, and K4's after the re-scoping.
- K3 and K4 stay kept on their verified M1 gains, but provisionally, until §42.4 lands.
- EVAL-AUDIT reruns the unmodified suite on the K1, K2, K3 and K4 configurations and lists every failure with its cause in VERIFY_LOG.

**§42.4 Build, now, ahead of the joint budget and the BRACKET cap: the spec's box priority inside the box family.** For the box family's live slot:
- A BOX or RANGE_OPEN that contains the current price, or that price left within the last 12 bars, outranks every CONTEXT_RANGE and every box that price is neither in nor just left. This holds whatever the scores. (R21 §21.3: the author keeps a broken box drawn about 60 minutes.)
- Among equals, the score decides as now.
- A CONTEXT_RANGE holds the slot only when no such box is live.

Behind a flag, default OFF; same-hash A/B on the kept parent. It is kept only if both hold:
1. the seven fixtures pass, unmodified, on the kept defaults plus this flag;
2. §34.5 or §41.3 passes.

Also report BOX-LAB's three rank-2 misses. In each, a stale structural envelope (365–685 bars old, in another price band) outscores the fresh right box, and this rule should fix them. If the rule is kept, K3 and K4 become final.

**§42.5 If §42.4 has not passed by 12:30Z**, the Lead chooses at the freeze between:
- the kept configuration, with the seven fixture failures listed as known spec violations in GATE_PACK_C1;
- the same configuration with `fam_budget` and `fam_caps` OFF.

Build prepares both M1 rows at one hash by 13:00Z. The supersede works in the rate-blocked branch, so measure K4 both ways.

**§42.6 BOX-LAB.**
- Log "rulings read up to R42".
- Hand the three rank-2 cases to the build lane in REQUESTS.md now; they are §42.4's test cases.
- The LODO ranker continues only with its shuffle control. It has 9 coverable positives, so report it as a lab finding, not a hand-off, unless the shuffle control separates clearly.

**§42.7 SCALE pauses until the freeze.**
- It finished its first report at 05:54Z, but its job then stayed blocked on the all-days bonus run and never read R41.
- The Lead cancelled the job at 06:26Z and stopped the orphaned bonus process at 06:27Z, as R41 §41.5 item 2 ordered. The rows it had written (through 2017-08-23) stay on disk.
- This also brings the Devin total back to 6; the Bot Future session started two lanes at 06:09Z.
- After the 14:30Z freeze the Lead relaunches SCALE on the round's STABLE to do R41 §41.5 items 3–4: Q2 over 240 trading days against STABLE `9283b389`, and a gallery of 10 trading-day sessions.

**§42.8 EVAL-AUDIT.**
- Do §42.3 before GATE_PACK_C1.
- The human-ceiling protocol and the M2 plan are accepted as drafts. The Lead takes them to the Owner after the round.

The round freeze stays at 14:30Z. No lane changes M1, M2, their thresholds or the ruler.

## Ruling 43 (07:02Z 22/09) - full review; the fifth keep (line slope floor) is accepted on M1; the suite leg says the break enters with K3's family flags; box_prio decides K3–K5; ink needs a joint cap that knows the spec's priority

**§43.1 Full review (07:00Z).**
- **Lanes and acks.** All three lanes are running. Acks: EVAL-AUDIT R42 (06:36Z), BOX-LAB R42 (06:29Z). Build read R42 (its stdout) but its PERCEPTION_LOG still shows R41; it logs "rulings read up to R43".
- **Walls hold.**
  - GATE_PACK_9283b389, PLAUSIBILITY and the owner judge pack are unchanged.
  - Under `evalcheck/`, only EVAL-AUDIT's own files and scoreboard rows changed.
  - `levels.py`, `engine.py`, `patterns.py` and `render.py` are unchanged. `lines.py` (build) and `boxes.py` (BOX-LAB) were edited by their owners.
- **The fixtures are back.** `tests/test_engine.py` no longer calls `gen_engine()` (06:50Z), as §42.2 ordered.
- **Build since R42:**
  - Joint live caps of 4, 3 and 2 all fail. For example, cap 4 brings clutter from 5.00 to 3.00, but costs box −1, level −4 and line −8. The count included annotation transients.
  - BRACKET cap = 2 fails (bracket@1 −1). `lnsteep` fails (line −2).
  - `line.slope_floor = 0.25` is kept (§43.2).
  - `box_prio` (§42.4) is implemented. The seven fixtures pass unmodified with it ON, and its full A/B is running.
- **BOX-LAB's finding:** the author's box edges sit on old structure. The pivots that define them are a median of about 7 hours (413 min) older than the box's build start: prior-session swing levels that the buildup revisits. The production proposer clusters only its window's own extremes, so it can never emit them. BOX-LAB is testing `box.level_edges`, a fallback to old confirmed pivot levels. Its wrong-t0 re-anchor is a dead end: the author's build start is a judgment, not a pivot event.

**§43.2 K5, `line.slope_floor = 0.25` at `75a9650c`, is kept on M1** (EVAL-AUDIT CONFIRMED 06:58Z).
- line@2 .098 → .104 (19 → 20 of 193); box and level flat.
- Engine line slope median 4.31 → 5.37 pips per hour, against the author's 9.2.
- Flag OFF is identical 1728/1728.
- Clutter margin: 90 of 179 panels sit at or below 5.0, so one raised panel would lift the median above 5.0. K4's margin was 2 panels, K3's 5.

**M1 now** (vs v0):
- level .079 ≥ .066;
- line .104 ≥ .093;
- box .059 (7 of 119) against .134 (16 of 119), 9 hits short.

**§43.3 The suite leg (EVAL-AUDIT, §42.3, unmodified fixtures on each keep's own configuration):**
- K1 and K2: 72/72.
- K3, K4 and K5: 65/72. The same seven fixtures fail each time, because `fam_budget` + `fam_caps` (introduced in K3) let a CONTEXT_RANGE hold the box family's single slot.
- The flags of K4 and K5 add no failure of their own.
- So K3's M1 gains stand. K3, K4 and K5 stay provisional until `box_prio` is kept with 72/72 unmodified on its own configuration; then all three are final.
- **Correction lines, appended, no edits:** the build lane's "suite 72/72" entries for K3, K4 and K5 were measured on the parent defaults or on the re-scoped suite. Append one correction line each to PERCEPTION_LOG and C1_M1.md.

**§43.4 Build, in order.**
1. **`box_prio` verdict.** It is kept only if:
   - the suite is 72/72 on the kept defaults plus `box_prio`, fixtures unmodified;
   - §34.5 or §41.3 passes, with the clutter median from `_m1.py`. The margin is one panel, so report the per-panel clutter count at or below 5.0 as well.
   - Also report BOX-LAB's three rank-2 stale-envelope cases.
   If it fails only on clutter, report it anyway; the Lead decides at the freeze together with §42.5.
2. **Joint cap v2** (ink path §41.3), time-boxed to 11:00Z:
   - Count structure only. Annotations (LABEL_TF, BAR_MARKER) and transients are not counted.
   - Over the cap, drop in reverse spec §5 priority:
     - CONTEXT objects first;
     - then levels that are not the nearest one ahead in either direction;
     - then lines not tied to the live box's breakout side;
     - then the oldest.
   - Never drop the §5 priority-1 box.
   - Caps 4 and 3; provenance logged.
3. **BOX-LAB hand-offs** (`box.level_edges`) as they arrive: A/B on the latest kept state.
4. **Freeze at 14:30Z.** Log "STABLE <hash>". By 14:45Z, a one-screen status:
   - M1 against v0 with CIs;
   - clutter median with its margin;
   - the six diagnostics;
   - the suite on the frozen configuration;
   - K1–K5 plus any keeps since.
   If `box_prio` has not been kept, have the §42.5 rows ready by 13:00Z.

**§43.5 BOX-LAB until 13:30Z.**
1. `box.level_edges`: report the engine oracle and box@1 from `_m1.py` against the flag-OFF parent, same hash. Hand off by 12:30Z, so the build lane can A/B it before the freeze.
2. Then the "mid-band eye-level" source that the residual taxonomy points to (51 no-edge goldens), if time allows.
3. Write the old-structure finding into BOX_INTEGRATION.md: it is the main generation lesson of the round.
4. One-screen status at 13:30Z.

**§43.6 EVAL-AUDIT.**
- Verify `box_prio` when it is logged: M1, identity, and the unmodified suite on its configuration.
- Check `box.level_edges` if the build lane keeps it.
- At the freeze, GATE_PACK_C1 with `_gate_pack_c1.py`. It includes:
  - the suite on the frozen configuration;
  - the per-panel clutter margin;
  - K1–K5 plus later keeps, each with its verdict.

The freeze stays at 14:30Z. No lane changes M1, M2, their thresholds or the ruler.

## Ruling 44 (07:27Z 22/09) - light check; birth-path priority keeps adding ink; give the context objects their own family; BOX-LAB found why the author's boxes are never proposed; both lanes log now

**§44.1 Light check (07:26Z).**
- **Build tried three birth-path versions of `box_prio`.** Each passes the seven fixtures and fails the keep-rule:
  - v1: level −3, clutter 6.33;
  - v2 (plus a τ score bonus): box +1, level −4, clutter 6.00;
  - v3 (the RANGE_OPEN exclusion only for prio-1 candidates): box +2 (.076), level −2, clutter 6.33.
- **The lesson, which is the lane's own:** every eviction on the birth path adds a birth, so ink rises. A fourth arm, `box_tau_prio` (the τ ranking bonus only, with no birth change), is running.
- **Logs are behind.**
  - PERCEPTION_LOG and C1_M1.md have not changed since 06:48Z. Neither v1–v3, nor the R42/R43 acks, nor the R43 §43.3 correction lines are logged.
  - BOX_LOG has not changed since 06:45Z.
  - Both lanes log now (§44.5).

**§44.2 The fixtures fail on a family assignment.** `salience.py` puts CONTEXT_RANGE in the "box" family (the family map, line 33). Under `fam_budget`, that family has one live slot, so a context range born first blocks the book's BOX.
- Spec §5 treats CONTEXT as its own item: priority 4, "one CONTEXT object". It never competes with the priority-1 box.
- **Arm, next, same hash:** under `fam_budget`, CONTEXT_RANGE and CONTEXT_LINE form their own "context" family with a live budget of 1.
  - No eviction and no score bonus: the book's BOX simply gets the box slot.
  - RANGE_OPEN stays in the box family: it is the forming Asian box.
- **Keep it only if** the suite is 72/72 unmodified on the kept defaults plus this change, and §34.5 or §41.3 passes. Report the clutter median with its margin.
- If clutter goes above 5.0, also run the same arm with CONTEXT_RANGE births OFF under `fam_budget`. The author draws about 0.08 context ranges a day, and v0 hit 0 of 6 at @1.
- **This arm is the §42.4 route.** `box_tau_prio` is a ranking-layer change: it can be kept on its own under §34.5, but it cannot fix the fixtures, because no BOX is ever born in them.

**§44.3 BOX-LAB's finding (seen in its output at 07:25Z; log it, §44.5): the author's boxes form in congestion that has no pivots.**
- All 51 no-edge box goldens have zero structural pivot confirmations during their buildup, so `on_pivot` never fires while the author's box forms.
- `congestion_scan` is the bar-driven route meant for exactly this. It bails out on the alternating-pivot check (impossible without pivots) and on the Asian-session bound.
- So the generation gap is a missing trigger, not a missing edge source. It also fits the old-structure finding (§43.1): the edges come from old levels, while the box itself is born out of pivot-less congestion.

**BOX-LAB until 13:30Z:**
1. A flagged, bar-driven congestion trigger in `boxes.py`.
   - It proposes a box when bars overlap inside a band of height ≤ k·ABR for at least N bars, with no pivot requirement.
   - Edges: the band's own extremes, plus `box.level_edges` from old structure where one lies within the tolerance.
   - Set N and k from the TUNE goldens' buildup shapes and log the provenance. The book's "buildup" is a run of small, overlapping bars.
2. Report the engine oracle and box@1 from `_m1.py`, same hash, flag OFF vs ON. Hand off by 12:30Z.
3. Whatever the result, BOX_INTEGRATION.md records the two findings: old-structure edges, and pivot-starved congestion. They are the round's generation lessons.

**§44.4 EVAL-AUDIT:** no change. Verify whatever the build lane keeps, including the suite on its configuration. GATE_PACK_C1 at the freeze.

**§44.5 Logging (R34 §34.9, at least every 45 minutes).**
- **Build:** log now:
  - "rulings read up to R44";
  - v1–v3 with their numbers, in PERCEPTION_LOG and C1_M1.md;
  - the R43 §43.3 correction lines.
- **BOX-LAB:** log now:
  - "rulings read up to R44";
  - the level_edges results;
  - the pivot-starved finding with its count (51 of 51).

The freeze stays at 14:30Z, and R42 §42.5's 12:30Z decision point stands. No lane changes M1, M2, their thresholds or the ruler.

## Ruling 45 (08:02Z 22/09) - full review; the context family cures the fixtures but costs ink; BOX-LAB's congestion trigger is the round's first generation gain; its flag-OFF path leaks and must be fixed first; the freeze choice is decided now

**§45.1 Full review (08:00Z).**
- **Acks:** all three lanes are at R44 (build 07:32Z, BOX-LAB 07:46Z, EVAL-AUDIT 07:37Z). The build lane's backlog and its §43.3 correction lines are logged.
- **Walls hold:** GATE_PACK_9283b389 and PLAUSIBILITY are unchanged, the fixtures are unmodified (`gen_engine` 0 uses), and `engine`, `levels`, `patterns` and `render` are unchanged.
- **Build: all failed; flags OFF.**
  - `box_prio` v1–v3 and `box_tau_prio` (C1_M1 rows 24–27).
  - `fam_context` passes the fixtures 72/72 unmodified (EVAL-AUDIT) but costs level −2 and line −1, with clutter 5.67.
  - Adding CONTEXT_RANGE births OFF: box +1, but level −2, line −2 and clutter 5.67.
- **The §42.5 rows (EVAL-AUDIT confirmed):**

| configuration | box | level | line | clutter | suite |
|---|---|---|---|---|---|
| kept (K1–K5) | .059 | .079 | .104 | 5.00 | 65/72 |
| famoff | .067 | .053 | .067 | 5.67 | 72/72 |
| famoff without the supersede | .042 | .053 | .073 | 5.00 | — |

- **BOX-LAB:**
  - `box.level_edges` is negative both ways.
  - `box.cong_trigger` (at `4dcc44d7`) is a bar-driven congestion trigger with no pivot requirement (N = 6 bars, band ≤ 4.0 ABR, from TUNE buildup shapes).
    - box@1 7 → 9 of 119 (.076), with every other family identical and clutter 5.00.
    - The mechanism: fresh congestion boxes outrank stale structural envelopes (9.2b g0 rank 2 → 1; 9.4b g0 none → 1).
    - Snapping to old levels loses the gain; rejected.
    - A sensitivity grid (k 3 and 5.5, N 8) is running.

**§45.2 A flag-OFF leak in `boxes.py` must be fixed before anything else** (EVAL-AUDIT, VERIFY_LOG 07:55Z).
- At the build lane's recent hashes (`cd00d0be`, `88438120`), the congestion code logs its candidates to `cand_log` even with the flag OFF: 1107 extra entries.
- It also changes one BOX's birth reason from `cluster_range` to `congestion_scan` (2012-04-04, panels 9.25a/b/c). Geometry, state and score are unchanged.
- So "flag OFF ≡ parent" now fails on the letter, for every A/B built on this lineage. The ranking falls back to cand_log scores when an object carries none.

**BOX-LAB, now:**
- Make every `cong_trigger` / `level_edges` effect conditional on its flag: candidate logging, labels, and any shared-state change.
- Show flag OFF ≡ K5 (`75a9650c`) on objects and cand_log, 1728/1728, with events. EVAL-AUDIT re-checks it.

Until then, the build lane runs no A/B with the `boxes.py` changes.

**§45.3 Build, in order until the freeze.**
1. After §45.2, **A/B `box.cong_trigger`** on your kept parent, at one hash, with BOX-LAB's defaults.
   - Keep-rule §34.5. Report the flipped goldens.
   - Kept → K6. BOX-LAB's sensitivity grid is the robustness note.
2. **`fam_context` + joint cap v2**, then joint cap v2 alone. Time-boxed to 11:30Z.
   - The cap counts structure only and drops in reverse spec §5 order: context first, then levels that are not the nearest ahead, then lines not on the live box's breakout side, then the oldest. It never drops the priority-1 box.
   - Caps 4 and 3.
   - Why: `fam_context` cures the fixtures but gives context its own slot, which adds ink. The cap takes that ink back from the context family first.
   - Report the fixtures, M1 and clutter.
3. **Freeze at 14:30Z**, as ruled (R43 §43.4).

**§45.4 The freeze choice, decided now (R42 §42.5).**
- **Default:** unless an arm from §45.3 item 2 passes both the unmodified fixtures and the keep-rule by 12:30Z, the round's STABLE is the kept configuration: K1–K5, plus K6 if it is kept.
- **Why not famoff:** it drops level (.053 < .066) and line (.067 < .093) below v0 and fails clutter (5.67). The kept configuration meets v0 on two of three families.
- **The seven fixture failures go into GATE_PACK_C1 as a named, known spec violation:** "under `fam_budget`, a CONTEXT_RANGE can hold the box family's single slot, so the book's BOX is not drawn in the textbook patterns of Fig 3.1, 3.8 and 3.9".
  - The frozen suite runs unmodified: 65/72, with the seven named.
  - This defect is first on the next round's list, with `fam_context` + cap as its lead candidate.
- No lane edits the fixtures.

**§45.5 BOX-LAB until 13:30Z:**
1. §45.2.
2. The sensitivity grid, and REQUESTS.md updated with the grid and the new flag-OFF hash.
3. BOX_INTEGRATION.md with the generation lessons:
   - old-structure edges;
   - pivot-starved congestion;
   - the congestion trigger;
   - why snapping misses the tolerance.
4. The one-screen status.

A richer level source for the band scan (eye level, tick density) is a lab note for the next round, not a hand-off.

**§45.6 EVAL-AUDIT:**
- Re-check §45.2's identity.
- Verify K6 if it is kept, including the unmodified suite on its configuration.
- At the freeze, regenerate GATE_PACK_C1 on the STABLE hash. The 07:39Z file at `75a9650c` is a rehearsal. Include the §45.4 violation section, and the per-panel clutter margin.

The freeze stays at 14:30Z. No lane changes M1, M2, their thresholds or the ruler.

## Ruling 46 (09:04Z 22/09) - full review; the leak is found and fixed; the congestion trigger becomes K6 once verified; item-2 arms are judged against the kept parent; BOX-LAB spends its spare hours on the wick-density edge source

**§46.1 Full review (09:00Z).**
- **Acks:** build read R45 at 08:22Z and EVAL-AUDIT at 08:09Z. BOX-LAB logged no "rulings read" line, but its 08:52Z entry works §45.2 by name, which counts. BOX-LAB logs the line from now on.
- **§45.2 is closed.** The leak was in BOX-LAB's `level_edges` restructure of `_propose_window`, not in `cong_trigger`.
  - The dir<0 anchor window was written `piv.price - eps <= min(c) <= piv.price + eps`. The mirror of the dir>0 rule needs `+ tease` on the inside.
  - The narrower window killed ~450 bottom-anchored `cluster_range`/`cluster_range_wick` proposals and flipped the 9.25c birth route.
  - Fixed at `df79ade3`. Flag OFF ≡ K5 `75a9650c`: BOX-LAB 198/198 panels (objects, cand_log, bars, events); build 198/198 records and 576/576 τ-pickles. EVAL-AUDIT's re-check is running.
  - **What the leak does to earlier numbers:**
    - Every A/B at a leaky hash carried the leak in both arms, so its deltas stand.
    - The kept configuration scores the same on leaky and clean code (p2_base = p3_base: 7/6/20/29, clutter 5.00), so the leak moved no M1 hit there.
    - The rejected arms failed by 2 or more hits on level, line or clutter, so their rejections stand.
    - Absolute numbers from leaky hashes get a caveat line. BOX-LAB's engine box oracle .398 is really .407.
- **K6, `box.cong_trigger`:** N = 6 bars, band ≤ 5.5 ABR, edges at the pure run extremes. The build lane's A/B at `df79ade3` on the K5 parent:

| metric | K5 | K5 + cong |
|---|---|---|
| box@1 | 7/119 (.059) | 9/119 (.076) |
| level@1 | 6/76 | 6/76 |
| line@2 | 20/193 | 20/193 |
| bracket@1 | 29/85 | 29/85 |
| clutter | 5.00 | 5.00 |
| born BOX recall | .093 | .111 |

  - The suite on kept + cong is 65/72: the same seven named failures, nothing new (08:30Z, on the leaky hash). EVAL-AUDIT re-runs it at `df79ade3`.
  - §34.5 passes by the letter. **K6 is kept once EVAL-AUDIT confirms M1, identity and the unmodified suite at `df79ade3`.**
  - **Robustness note for GATE_PACK_C1:**
    - k 4.0–5.5 and N 6–8 hold the +2; k 3.0 loses it.
    - +2/119 is within noise.
    - The claim is only that the mechanism is real: fresh congestion boxes outrank stale envelopes at τ. It is not a claim that box fidelity improved significantly.
  - **M1 after K6:** level .079 ≥ .066; line .104 ≥ .093; box .076 < .134 (9 hits against 16, 7 short).
- **Build item 2:**
  - `fam_context` + `joint_struct` cap 4 passes the suite 72/72 unmodified.
  - Cap 3 breaks `test_pierce_and_keep` (71/72) and is out.
  - The M1 leg for cap 4 is running.

**§46.2 Item-2 arms are judged against the current kept parent.**
- Once K6 is confirmed, the parent is K6 (K5 + cong).
- A cap-4 result measured against K5 is enough to fail the arm if it loses level or line hits, because `cong_trigger` changes neither family.
- A pass against K5 must be re-run against K6 at one hash before it can change the freeze choice (§45.4). The keep test is R44 §44.2: the suite is 72/72 unmodified, and §34.5 or §41.3 passes.
- 12:30Z stays the cut-off.

**§46.3 BOX-LAB until 13:30Z: one more generation lever, time-boxed (amends the last line of §45.5).**
BOX-LAB closed §45.2 early, and box is the only M1 family still under v0. The Owner asked for speed. The spare hours go to the edge source the web research named (WEB_RESEARCH_C1, item 2): box edges from wick-tip density.
1. **First, in ≤ 20 min: diagnose the 51 no-edge goldens with `cong_trigger` ON.** For each golden:
   - Does a congestion proposal overlap it in time?
   - If so, what are its top and bottom edge errors against the golden, in pips and in ABR?
   - Does it fail on tolerance, on band height (> 5.5 ABR) or on run length (< 6 bars)?

   Put one table in BOX_LOG.
2. **Then one flagged edge variant for the congestion band,** chosen from that table. Default OFF.
   - **Lead candidate:** a density over the run's wick tips, with kernel width = bar range. Edges go at the outermost density peaks (or at high/low quantiles) instead of at the run extremes. Peaks closer than an ABR-scaled spacing merge.
   - **The §45.2 lesson:** every effect goes behind the flag, including candidate logging. Check flag OFF ≡ the K6 parent (objects, cand_log, events) as soon as the code is written, not at A/B time.
3. **Lab A/B at one hash against the K6 parent, by 11:30Z.**
   - Hand off in REQUESTS.md only if §34.5 passes in the lab and flag-OFF identity holds.
   - The build lane runs the formal A/B only if it can finish by 12:30Z. Otherwise this is the next round's first lever, with the lab numbers recorded.
4. §45.5 items 3–4 (BOX_INTEGRATION.md with the generation lessons, and the one-screen status) are still due by 13:30Z.

**§46.4 EVAL-AUDIT:** as §45.6. Also:
- In VERIFY_LOG, list which recorded verdicts were measured on leaky hashes, and confirm that no kept verdict (K1–K5) rests on one.
- The K6 row of GATE_PACK_C1 carries the §46.1 noise note.

**§46.5 Build after item 2:** record K6 in C1_M1 once EVAL-AUDIT confirms it, then prepare the freeze (R43 §43.4). Run BOX-LAB's hand-off only under §46.3 item 3. No new levers.

**§46.6 Devin** runs 4 jobs now. PA-PRO launches nothing new before the freeze. SCALE relaunches after the freeze on the round's STABLE (R41 §41.5 items 3–4).

The freeze stays at 14:30Z. No lane changes M1, M2, their thresholds or the ruler.

## Ruling 47 (10:03Z 22/09) - full review; the density edges fail and BOX-LAB's sub-band arm is allowed; engine code closes at 12:30Z and the freeze moves to 13:30Z; the build lane profiles the throughput collapse while it waits

**§47.1 Full review (10:00Z).**
- **Acks:** all three lanes are at R46 (build 09:08Z, EVAL-AUDIT 09:26Z, BOX-LAB 09:34Z).
- **BOX-LAB went idle.** It wrote its §45.5 status at 09:12:55Z, never read R46, and sat at 0 CPU. The Lead cancelled the job at 09:33Z and resumed the same session (job `20260922093313-4fc694`).
  - **The lesson:** a lane that empties its queue ends its turn. Every lane keeps a standing queue until its end time.
- **K6 is kept and confirmed.** The build lane kept it at 09:08Z and flipped the defaults. The default engine is `9acaa206` (K1–K6).
  - The build lane's freeze audit (09:13Z): exactly K1–K6 are ON and every rejected arm is OFF.
  - EVAL-AUDIT confirmed at 09:14Z: M1 .076/.079/.104, clutter 5.00 (90/179 panels ≤ 5.0), suite 65/72 with the seven named, and the default engine reproduces the ON arm. The canonical flip list is 9.4b t815 and 9.48b t705.
  - EVAL-AUDIT's leak ledger (09:26Z): no keep rests on a leaky hash.
- **Build item 2 failed at both caps; OFF.** `fam_context` + joint cap at `df79ade3`:

| cap | suite | box | level | line | bracket | clutter |
|---|---|---|---|---|---|---|
| 4 | 72/72 | +2 | −4 | −4 | −9 | 5.67 |
| 3 | 71/72 | +2 | −1 | −3 | −15 | 5.67 |

  - The §45.4 freeze choice stands: K1–K6, suite 65/72 with the seven named.
- **BOX-LAB §46.3, the 51 no-edge goldens under K6.** The class shrank to 38, because congestion proposals now carry matching edges for 13. The rest:

| class | count | what fails |
|---|---|---|
| edge_tol | 22 | A congestion proposal overlaps the buildup, but the edges miss: median error ~9 pips, direction mixed (7 too wide, 7 too narrow, 8 shifted). Often one edge is exact (0.0–0.5 pips on 6 cases). |
| too_tall | 11 | The run qualifies at ≤ 5.5 ABR, but the band exceeds min(6 ABR, 34 pips). The 34-pip absolute cap binds when ABR is high. |
| other | 4 | Live cover, dedup and other gates. |
| no_window | 1 | The buildup lies outside the panel. |

- **`box.cong_density` (wick-tip density edges) fails both ways; no hand-off.**
  - Peak mode (`0a100806`) is inert: box 9/119 flat, all families identical. Density substitutes on only 8% of congestion candidates and never reaches the 38 windows. Its peaks collapse onto interior wick clusters.
  - Quantile mode (`13b3f53d`) loses 2 boxes (7/119). The trimmed edges were exactly what let the congestion boxes match at τ.
  - BOX-LAB checked flag-OFF ≡ K6 at both hashes before each A/B (198/198). That is the §45.2 lesson applied.
  - **Finding:** the author's box edges are not a statistic of the local run. Run extremes overshoot, interior clusters undershoot and quantiles still miss the tolerance. This agrees with R44: the edges sit on old structure, about 7 hours back. An old-structure level source is the next round's first box lever.
- **Walls hold:**
  - GATE_PACK_9283b389 is unchanged (`2CC4CCA277E7`).
  - `test_engine.py` is unchanged (06:50:46Z), with `gen_engine` at 0 uses.
  - `levels`, `engine`, `patterns` and `render` are unchanged since 21/09.
  - `salience.py` and `lines.py` are unchanged since this morning. `boxes.py` changes only under BOX-LAB's flags.
  - evalcheck changes only in EVAL-AUDIT's files.
  - Devin is at 6 (3 PA-PRO + 3 W10).

**§47.2 BOX-LAB: `box.cong_subband` is allowed as the second variant under §46.3.** It extracts a sub-band inside an over-cap envelope, aimed at the too_tall class (11). Same conditions as §46.3:
- flagged, default OFF;
- flag-OFF ≡ the K6 parent (objects, cand_log, events) checked as soon as the code is written;
- lab A/B against K6 with canonical `_m1`, by 11:30Z.

Hand off in REQUESTS.md by 11:40Z, and only if §34.5 passes and identity holds. That leaves the build lane time to finish the formal A/B by 12:30Z. If it fails, record it as lab data. Then write BOX_INTEGRATION.md and the one-screen status (§45.5 items 3–4). The lessons to record:
- the 38-goldens table;
- why the density edges fail;
- old structure as the edge source;
- the one-exact-edge cases (a next-round idea: keep the exact run edge, take the other edge from old structure).

**§47.3 Engine code closes at 12:30Z; the freeze moves to 13:30Z; the pack moves to 14:30Z.**
- **Why:** the round's decisions are made, and the Owner asked for speed. SCALE can relaunch on STABLE as soon as a Devin slot frees.
- **12:30Z: last change to any engine file** (the files the engine hash covers). This covers BOX-LAB's flagged code and a kept hand-off alike. After 12:30Z, lanes write only logs, docs and lab scripts.
- **If a hand-off is kept by 12:30Z it becomes K7.** EVAL-AUDIT verifies it, including the unmodified suite, by 13:15Z.
- **By 13:15Z, EVAL-AUDIT checks final-hash identity.**
  - Flagged-OFF code changes the file hash, so the hash at 12:30Z will not be `9acaa206`.
  - EVAL-AUDIT checks that the final default engine ≡ the last verified keep (`9acaa206`, or K7's ON arm) on objects, cand_log and events, 1728/1728.
  - If identity fails, the build lane restores the `9acaa206` file set from its snapshot (§47.4), and that is frozen.
- **13:30Z:** the build lane logs "STABLE <hash>". It writes the one-screen status (R43 §43.4 item 4) by 13:45Z.
- **By 14:30Z:** EVAL-AUDIT writes GATE_PACK_C1 on STABLE (§47.5).
- This replaces the 14:30Z freeze in R43 §43.4, R45 and R46.

**§47.4 Build until 12:30Z.**
1. **Now, 5 minutes:** snapshot the engine files at `9acaa206` into `_scratch/freeze_candidates/9acaa206/`, with sha256s, as the rollback for §47.3.
2. **Priority:** any BOX-LAB hand-off, as a formal A/B against K6 at one hash, by 12:30Z.
3. **Otherwise, F1, the throughput collapse** (SCALE FINDINGS F1: 720 bars/s on a fresh day, 57 bars/s after 52 days).
   - Profile only. Do not edit engine files before the freeze.
   - Use DESIGN days via `scale/design_loader.py` only. The run is outcome-blind, and CONFIRM, OOS and HOLD stay sealed.
   - Python via pa_slots ≤ 1, BelowNormal. It yields the slot to a hand-off A/B.
   - Start from SCALE's cProfile. Show which structure grows (cand_log, live or retired object lists, swing history, rescans), with bars/s against day and the top functions at about day 5 against day 50.
   - **Deliverable:** `research/perception/perf/F1_PROFILE.md`, with a proposed patch in `_scratch/perf/` and its identity plan: TUNE 1728/1728, plus a byte-identical 20-day DESIGN run.
   - The patch lands in the next round, not this one.
4. **Heartbeat:** log a line at least every 30 minutes, even while waiting. PERCEPTION_LOG was silent from 09:13Z to 10:00Z.

**§47.5 EVAL-AUDIT.**
- Verify any K7, and check final-hash identity (§47.3), by 13:15Z.
- **GATE_PACK_C1 on STABLE by 14:30Z.** It carries:
  - the §45.4 violation section, with the seven fixtures named;
  - the per-panel clutter margin;
  - the K6 noise note (§46.1);
  - the leak ledger in brief;
  - a "tested and rejected" table of the round's arms, including both density modes and `cong_subband` if it fails.

**§47.6** No lane changes M1, M2, their thresholds or the ruler.

## Ruling 48 (10:34Z 22/09) - light check; no hand-off, so the freeze comes forward to STABLE 9acaa206; BOX-LAB closes; SCALE relaunches now on the frozen snapshot; the F1 patch must keep every lookback

**§48.1 Light check (10:30Z).**
- **Acks:** all three lanes are at R47 (BOX-LAB 10:10Z, build 10:11Z, EVAL-AUDIT 10:11Z).
- **BOX-LAB §47.2:** `box.cong_subband` (`5928a0e2`) is rejected. Box stays flat at 9/119 and clutter rises to 5.33; 1123 candidates, 0 born; identity 198/198. **No hand-off**, and REQUESTS.md says so.
- **BOX-LAB also tested the one-exact-edge hybrid offline** (`cong_mixedge`). It was disproven before any A/B and reverted:
  - wick-tip support does not separate exact edges from wrong ones;
  - among the old interior levels, neither "nearest to the extreme" nor "most support" picks the golden one.
- **Reachability census (BOX_LOG 10:15Z).** A union of causal sources contains both edges of 27 of the 38 no-edge goldens. The sources are 10-pip round numbers, pivots, buildup close extremes, 6-hour session high/low and prior-day high/low. The other 11 sit on no standard structure.
  - **Lead's caveat:** with a 1.5–5 pip tolerance, a 10-pip grid covers a large share of all prices by chance. Its 15 both-edge hits prove nothing until they are compared with a null: random or shuffled edges at the same tolerance. R39 found the author's levels no rounder than chance (9% against 8%).
  - The same null applies to every source in the union. The next round measures it before building on it.
- **Build §47.4:**
  - The snapshot is done: `research/perception/_scratch/freeze_candidates/9acaa206/`, 10 files plus SHA256.txt. boxes.py was reconstructed byte-exact, and the code hash recomputes to `9acaa206c8d386dc`.
  - **F1 profiled by 10:24Z:** 991 → 32 bars/s over 55 continuous DESIGN days.
    - `book.seq` grows about 92 swings a day, and `alive()`, `floor_min()` and `_floors()` rescan all of it every bar.
    - Dead objects are never pruned (808 by day 54), and `active()` scans them.
    - The `_births` ledger never trims.
    - Bounded: live objects 5–8, pool 15–27.
- **Walls hold.**
  - GATE_PACK_9283b389 is unchanged, and so is `test_engine.py` (06:50:46Z; `gen_engine` 0 uses).
  - `levels`, `engine`, `patterns` and `render` are 21/09 files; `salience` and `lines` are unchanged since this morning.
  - boxes.py on disk is `5928a0e2`: the subband code with its flags OFF, identity against K6 198/198.

**§48.2 No K7 is possible, so the freeze comes forward.** BOX-LAB's queue is exhausted and nothing else can change the engine's behaviour this round.

**Build, by 11:15Z:**
1. Copy the current boxes.py to `research/perception/_scratch/lab_variants/boxes_5928a0e2.py`. It keeps the flagged lab variants for the next round.
2. Restore the engine files from `_scratch/freeze_candidates/9acaa206/`. Only boxes.py should differ.
3. Recompute the code hash; it must be `9acaa206c8d386dc`.
4. Run the unmodified suite once on the defaults. Expect 65/72 with the seven named.
5. Log "STABLE 9acaa206c8d386dc".
6. Write the one-screen status by 11:30Z (R43 §43.4 item 4).

Why restore rather than freeze `5928a0e2`:
- STABLE then carries the exact hash EVAL-AUDIT verified at 09:14Z: M1, identity, suite and the default-engine reproduction.
- Dead lab code does not ship in the frozen engine.

**Engine files close at the STABLE line.** This replaces the 12:30Z close in §47.3. From that line until the next round opens, no lane edits an engine file.

**EVAL-AUDIT:**
- Confirm that the on-disk code hash is `9acaa206c8d386dc`, the configuration verified at 09:14Z. A 3-panel spot check is enough; the hash carries the §47.3 identity leg.
- **GATE_PACK_C1 on STABLE by 12:30Z** (replaces 14:30Z), with:
  - the §47.5 contents;
  - BOX-LAB's reachability census with the null caveat (§48.1).

This ruling replaces the times in §47.3.

**§48.3 BOX-LAB closes now.**
- Its queue is done, and a Devin slot is worth more to SCALE than to monitoring.
- Its closing status is BOX_LOG 10:10–10:31Z plus BOX_INTEGRATION.md §R46 (10:16Z). Both are accepted.
- The Lead ends job `4fc694`. The session (woolen-bugle) is kept for the next round.
- **Next-round box lever:**
  - edges seeded from old structure inside qualified congestion runs;
  - a causal rule that picks the edge;
  - measured first against the null.

**§48.4 SCALE relaunches now on the STABLE snapshot** (session changeable-primula).
- **Engine:** `_scratch/freeze_candidates/9acaa206/`, copied to `scale/engine_9acaa206/`. It is byte-identical to STABLE, so its numbers hold for the frozen engine.
- **Queue:**
  1. Q2 at scale: STABLE (C1) against the old STABLE (`9283b389`) on the same 240 days.
  2. A census over every DESIGN trading day, 2016–2021, EURUSD M5, arm C1:
     - boxes born, breakouts, levels and lines, per day;
     - per year and per session, with the spread between years;
     - outcome-blind: drawing counts only.
  3. The gallery: 10 trading-day sessions, both arms side by side.
- **Report:** `scale/SCALE_REPORT_C1.md` by 14:00Z.
- This answers the Owner's 04:17Z question with the round's engine: how consistently it draws over six years of real sessions.

**§48.5 Build after STABLE: F1 only.**
- **Deliverables:**
  - `research/perception/perf/F1_PROFILE.md`;
  - a proposed patch in `_scratch/perf/`;
  - its identity plan: TUNE 1728/1728, a byte-identical 20-day DESIGN run, and a 55-day speed run.
- **The patch must not shorten any lookback a rule uses.**
  - Prefer indexing or caching the scans: a sorted or bucketed store of live swings, and ABR cached per bar.
  - Trim history only as a last resort. If it prunes, first list every consumer of `book.seq`, the object list and `_births`, each with its maximum lookback. Prune only what no rule can reach.
  - The next round's box lever needs structure from hours back (§48.1).
- The patch lands in the next round, after its identity plan passes.
- Heartbeat ≤ 30 min; pa_slots ≤ 1.

**§48.6 Devin** runs 6 jobs: 3 PA-PRO (build, EVAL-AUDIT, SCALE) and 3 W10.

**§48.7** No lane changes M1, M2, their thresholds or the ruler.

## Ruling 49 (11:04Z 22/09) - C-round 1 closes on STABLE 9acaa206 and its pack is accepted; C-round 2 opens now; box edges from old structure, null first; the fixture debt by yielding, not evicting; the F1 patch lands at the round's close behind an identity gate

**§49.1 C-round 1 is closed.**
- **STABLE is `9acaa206c8d386dc`**, logged at 10:41Z. The Lead checked all ten engine files against the snapshot at 11:02Z: each is byte-identical. The suite is 65/72, with the seven named failures.
- **GATE_PACK_C1_9acaa206.md** (EVAL-AUDIT, 11:00Z) is the pack of record, and it is accepted.
  - One correction. Under "Carried debt", "box −110 misses vs v0" must read "box is 7 hits short of v0 (9 against 16 of 119)". EVAL-AUDIT fixes that line when it resumes.
- **M1 against v0:**
  - Box .076 [−.142..−.003]: below v0, and the CI excludes 0.
  - Level .079 and line .104 beat v0 on the point estimate; their CIs straddle 0.
  - Clutter median 5.00, against v0's 9.00. The margin is one panel (90/179).
- **The round in numbers:** 6 keeps out of about 26 arms. From the round's start (STABLE `9283b389`):

| family | start | now |
|---|---|---|
| box | .017 | .076 |
| level | .013 | .079 |
| line | .083 | .104 |

**§49.2 C-round 2 opens now.**
- **Goals:** box ≥ v0 (16/119) without losing level, line or clutter; and the seven-fixture debt.
- **Parent:** STABLE `9acaa206`.
- **Keep-rules are unchanged:**
  - §34.5 or §41.3;
  - a same-hash A/B;
  - the unmodified suite on the kept configuration (R42 §42.3);
  - flag-OFF ≡ parent, including cand_log.
  - A cure for the seven fixtures is kept when the suite is 72/72 unmodified and §34.5 or §41.3 passes (R44 §44.2).
- **Times:**
  - engine code closes at 20:30Z;
  - STABLE at 21:30Z (after the F1 landing, §49.4);
  - GATE_PACK_C2 by 22:30Z.
- **Lanes:**
  - build: now;
  - BOX-LAB: now, resumed;
  - EVAL-AUDIT: pauses now and resumes when SCALE ends at about 14:15Z;
  - SCALE finishes its R48 queue.

**§49.3 BOX-LAB (session woolen-bugle), in order.**

1. **The null first, by 13:00Z.**
   - Measure each causal source from the 10:15Z census, and their union. The sources are 10-pip rounds, pivots, buildup close extremes, 6-hour session high/low and prior-day high/low.
   - For each, find the share of golden boxes whose two edges both lie within tolerance of a level the source had produced by τ. Do this for the 38 no-edge goldens and for all 119.
   - **The null:** the same goldens, shifted vertically by a random offset: uniform in ±1 to 3 box heights, height unchanged, same tolerance, 200 draws.
   - Report the observed share, the null mean and the null p95.
   - A source that does not beat the null p95 is dropped.
   - The method goes in BOX_LOG with the script name. EVAL-AUDIT reviews it on resume.
2. **Then one flagged generator, built only from sources that beat the null:**
   - edges seeded from that old structure, inside congestion runs that qualify under K6's trigger;
   - a causal rule that picks the edge pair: state it, and report its coverage (oracle) and box@1;
   - flag-OFF ≡ STABLE on objects, cand_log and events, checked when the code is written (the §45.2 lesson).
3. **Lab A/B at one hash against the parent, by 17:00Z.** Hand off in REQUESTS.md only if §34.5 passes and identity holds. The build lane runs the formal A/B by 20:30Z.
4. **If no source beats the null, say so plainly.** That is a finding, not a failure, and the Lead decides the next box lever.
5. **Standing rules:**
   - Log at least every 30 minutes, with "rulings read up to Rnn" at each loop.
   - Never end before 20:15Z.
   - When the queue empties, write BOX_INTEGRATION.md updates and keep checking the rulings. The Lead adds work at each check.

**§49.4 Build.**

1. **The F1 patch.**
   - Finish its identity plan against `9acaa206` by 14:00Z:
     - TUNE 1728/1728 via canonical;
     - a byte-identical 20-day DESIGN run;
     - a 55-day speed run, with bars/s by day.
   - The patch stays in `_scratch/perf/` until the round closes.
   - At 20:30Z the build lane merges it onto the round's kept configuration. EVAL-AUDIT re-proves identity (TUNE 1728/1728) by 21:15Z, and STABLE follows at 21:30Z.
   - It is a behaviour-neutral change, so it lands only on identity. It must not shorten any lookback (§48.5).
2. **The seven-fixture debt, from 14:00Z: yield, not evict.** Every cure tried so far evicted and re-birthed objects, and that churn cost ink and levels. The lead candidate:
   - CONTEXT_RANGE gets its own family, as `fam_context` did.
   - A context object is drawn only while no priority-1 box (spec §5) is live. While hidden it is neither evicted nor re-born, and it counts neither as ink nor against any budget.
   - Behind a flag, with an A/B against the parent. Keep it per R44 §44.2, and report the per-panel clutter margin.
   - If it fails, record why, and hand the cause to the next round.
3. **Then F3 and F5**, both behaviour-neutral on EURUSD:
   - F3: the pip size taken from the symbol;
   - F5: the `render.py` object layer.
   - Each lands only on identity (TUNE 1728/1728), and before 20:30Z.
4. **Formal A/B** of any BOX-LAB hand-off, by 20:30Z.
5. **Your job ends at 15:40Z** (its timeout). Write a hand-over line at 15:35Z; the Lead resumes the session.
   - Heartbeat at least every 30 minutes.

**§49.5 EVAL-AUDIT** (session platinum-airedale) resumes at about 14:15Z:
1. Fix the pack line (§49.1).
2. Review BOX-LAB's null method, and reproduce one source's numbers.
3. Verify the F1 identity plan independently: TUNE 1728/1728 on objects, cand_log and events; the 20-day byte identity; the speed claim.
4. **The Owner's human-ceiling kit**, per `HUMAN_CEILING_PROTOCOL.md`, ready by 23/09 06:00Z:
   - the 10 stratified TUNE panels, rendered up to τ with no engine or author drawings;
   - a one-page instruction in Vietnamese;
   - an answer format the Owner can use on a PC or a phone.
5. Verify the C-round 2 keeps. The F1 merge identity by 21:15Z; GATE_PACK_C2 by 22:30Z.

**§49.6 Devin** runs 6 jobs:
- build, BOX-LAB and SCALE;
- then build, BOX-LAB and EVAL-AUDIT once SCALE ends;
- plus 3 W10.

**§49.7 P-FREEZE.** The Lead proposes the date to the Owner today, with evidence.
- **The target:** 25/09.
- **It is conditional on three things:**
  - M1 on the last STABLE by 24/09;
  - the human ceiling measured on 23/09;
  - M2 ≥ .60 from the Owner's blind judging on that STABLE.
- **If only box is short on 24/09,** the Owner chooses between one more round and adjusting the box criterion from the human ceiling.
- **The Owner decides. No lane changes M1, M2, their thresholds or the ruler.**

## Ruling 50 (12:02Z 22/09) - full review; clutter headroom is the binding constraint, so buy it first with an ink-only keep; the fixture debt goes to the next round as a spec-vs-author conflict; BOX-LAB maps the covered-but-missed boxes

**§50.1 Full review (12:00Z).**
- **Acks:** all lanes are at R49 (BOX-LAB 11:06Z, build 11:13Z, SCALE 11:16Z).
- **BOX-LAB's null test** (`boxlab/c1_nullsrc.py`, 11:08Z):
  - Pivots beat the null: 38 no-edge .789 against null p95 .316; all 119, .880 against .343.
  - Close extremes beat it; session high/low beats it thinly.
  - 10-pip rounds do not (at the null p95), and prior-day high/low fails on the 119. Both are dropped.
- **`box.cong_pivedge`** (a clean same-process pair at `fcd56aaf`):
  - box 9 → 10, level 6 → 7, line and bracket flat;
  - coverage +3; identity holds;
  - **but clutter 5.00 → 5.33, so it fails §34.5.**
  - Of 4199 candidates emitted, 54 are born. The extra births are distinct geometries, not duplicates. Tighter cuts are running.
- **The build lane's F1 identity plan is complete** (11:22Z):
  - 1728/1728 byte-identical;
  - a byte-identical 20-day DESIGN run;
  - a 55-day speed run;
  - suite 65/72.
  - It waits for the 20:30Z merge.
- **The fixture debt: three yield variants fail the same way** (fam_context lane `a3742b16`, standalone, overlap-gated `99249af2`):
  - All pass the suite 72/72, and all fail §34.5. For example, ctxyf: box +2, level −3, bracket −1, clutter 5.67.
  - **Mechanism:** a yield starts a birth–death cycle. The context yields, a box is born, the box is outranked or closed, the slot frees, the context is re-born, and the next box candidate yields again. That is +282 BOX births on 60 panels.
  - The fixtures demand a box priority that ignores score, and the author's TUNE drawings punish it.
- **SCALE:**
  - Q2 C1 is done: 3843 objects against 4168 for V1 (−7.8%).
  - The census reached 811/1868 days at 11:56Z; ETA about 13:00Z. On partial data, the spread between years is 2–11%.
  - The gallery is done for both arms. C1 is visibly sparser than V1.
- **Walls hold:**
  - GATE_PACK_9283b389 is unchanged, and so is `test_engine.py` (`gen_engine` 0 uses).
  - `render.py` is unchanged.
  - Engine files differ from the 9acaa206 snapshot only in boxes.py, salience.py and params (flagged code).
  - evalcheck is untouched.

**§50.2 Clutter headroom first: the round's next keep is ink-only.**
- **The binding constraint is the clutter margin, not generation.** The median sits at exactly 5.0, 90/179 panels are ≤ 5.0, and the ratios are discrete. Any lever that adds one object on one marginal panel flips the median. pivedge (+1/+1) and the fixture cures (+2 box) both died on that leg.
- SCALE shows where the excess ink is. At scale the engine draws CONTEXT_LINE at 6–32×, BRACKET at 3–22× and LEVEL_CARRIED at 2–10× the author's rate, and none of these is in M1 except LEVEL_CARRIED hits.

**Build, from now until 17:00Z:**
1. **Marginal-panel anatomy (30 min).** Take the panels with clutter in [4.5, 6.0]. For each, list the engine objects live at τ by family, and mark which are M1 hits.
   - Find the family whose removal on those panels frees the most margin without touching an M1 hit.
   - Write one table to PERCEPTION_LOG.
2. **One flagged ink-only arm from that table**, for example:
   - CONTEXT_LINE only while no structural line is live;
   - one BRACKET at a time;
   - LEVEL_CARRIED only when it is the nearest level ahead of price.
   Same-hash A/B against the parent.
3. **The keep test.** §41.3 applies, amended for this round: an ink-only arm is also kept if
   - no M1 family loses any hit;
   - the clutter median does not rise;
   - the number of panels ≤ 5.0 rises by at least 5;
   - the unmodified suite shows no new failure;
   - flag-OFF ≡ parent.
   - Report the margin (panels ≤ 5.0) as the headline number.
4. **When an ink-only keep lands, BOX-LAB's pivedge hand-off is A/B'd on top of it** (R38 §38.4 combined order: headroom keep first, then the generator as a separate keep).
5. **F3 and F5** (identity-gated) after that, before 20:30Z.

**§50.3 The fixture debt closes for this round.**
- The build lane writes `research/perception/FIXTURE_CONFLICT.md` (one page): the seven fixtures, the three variants, the birth–death mechanism, and the M1 cost of each.
- The Lead treats it as a possible **spec-versus-author conflict.** The spec ranks a box above a context range (§5); the author's TUNE drawings do not always.
- It may need the Owner's decision, alongside the P-FREEZE package, if the next round cannot cure it. No lane edits the fixtures or the spec.

**§50.4 BOX-LAB.**
1. **Finish the pivedge cuts, and keep the best arm ready.** Its lab A/B is re-run on the headroom parent once one lands (§50.2 item 4). The 17:00Z lab deadline stands.
2. **Then, by 14:30Z: a covered-but-missed anatomy at `9acaa206`.** About 36 goldens have a matching engine proposal but no hit at τ. For each:
   - Was it born? If not, why: rate gate, below minimum score, NMS?
   - Was it alive at τ? If not, how did it die: expiry, supersede, break?
   - If alive, what was its rank at τ, and what outranked it (kind, age, score)?
   - Put one table in BOX_LOG. The largest bucket is the next selection lever. In C-round 1, selection gave 6 of the 7 box hits; generation gave 1.
3. **Heartbeat.** BOX_LOG was silent from 11:30Z to 12:00Z. Log every 30 minutes, even mid-sweep.

**§50.5 EVAL-AUDIT on resume (about 14:15Z)** adds two checks to its null review (§49.5 item 2):
- **A density-matched null.** Shift each golden only within the price range traded in its lookback, so the pivot density is comparable. A plain vertical shift can land in empty price and flatter pivots.
- **Is `close_ext` circular?** It used the golden's own buildup window. The engine must use the trigger's window, so re-measure it on the trigger's run.

**§50.6** SCALE continues. The build job ends at 15:40Z; the Lead resumes the session with the §50.2 queue. No lane changes M1, M2, their thresholds or the ruler.
