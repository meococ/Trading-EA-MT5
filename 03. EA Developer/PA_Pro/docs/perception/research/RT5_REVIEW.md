# RT5 — Adversarial review of RT1–RT4

**Written:** 2026-09-21 16:31Z (UTC). **Lane:** PERCEPTION. **Scope:** attack the
ten load-bearing claims that `THEORY_SURVEY.md` and the `DN_*` notes inherit
from RT1–RT4; verify the citations underneath them; audit folklore handling.
Mandate: refute, not summarise. **Verdicts:** HELD / HELD-WITH-CAVEAT /
WEAKENED / REFUTED / UNVERIFIABLE.

**Method.** Each claim was checked against its primary source via official
landing pages (Wiley DOI, New York Fed, arXiv, NBER, SSRN, RePEc, ScienceDirect,
AEA, FRB, BIS, CCFEA). Journal PDFs return binary through `webfetch`; where a
number rests on abstract text or search-extracted official text it is marked
**[snippet]** rather than presented as full-text verification. No books or book
PDFs were fetched; no shadow sources were used. Internal RT1 claims were
re-checked against the local author-excerpt files
(`rt1_author_excerpts/fpas_excerpts.txt`, `upa_excerpts.txt`).

**Headline.** No claim is fabricated; the corpus is honest about its weakest
links. The real damage is concentrated in three places: (1) a mechanism
hypothesis — *a level weakens per touch* — has been promoted to design axiom in
four DN files on the strength of an NYSE study that never measured per-touch
depletion; (2) two citation slips — a ~2bp number written as ~2.5bp, and the
10:00 ET option-cut spike attributed to the wrong paper; (3) every quantitative
anchor (Osler's magnitudes, DC scaling exponents, Bulkowski's rates) is
era- or market-foreign to post-2010 EURUSD M5 — RT3/RT4 mostly say so, but the
synthesis must not let "prior" harden into "parameter".

---

## A. The ten claims

### C1 — Osler (2003): TP orders cluster at round numbers, stops just beyond → asymmetric zones, magnet-then-accelerator
**Depended on by:** RT3 Q1/P1/P3; THEORY_SURVEY §1–§2; DN_LEVEL zone asymmetry.
**Attack.** Verified: JF 58(5):1791–1819, DOI 10.1111/1540-6261.00588 (Wiley
page; FRBNY SR125 search text). The abstract supports the asymmetry claim
verbatim in substance. Weaknesses: ~9,700 orders at *one* dealing bank, Aug
1999–Apr 2000 — one institution's book, pre-algo era; orders ≠ executed flow;
no published replication on post-2010 EURUSD exists (RT3 §5 admits this). The
*asymmetric-zone* inference is a fair mechanism reading; the *exact pip offsets*
(near side vs far side) are not in the paper — RT3 correctly assigns them to
self-measurement (P7).
**Verdict: HELD-WITH-CAVEAT.** Mechanism real and correctly attributed; zone
geometry magnitudes are ours, not Osler's; era = 1999–2000.

### C2 — Osler (2005): post-round-number crossing acceleration → cascade window
**Depended on by:** RT3 Q2/P3; THEORY_SURVEY §4; DN_TF/BOX "post-break run".
**Attack.** Verified via FRBNY SR150 page and Georgetown-hosted PDF text. The
headline numbers are real: USD/DEM mean move 0.061% vs 0.054% in the 15 min
after crossing round vs arbitrary numbers, 1-min indicative quotes, 1996–98.
The catch the RT file mostly carries: that is a **0.7bp mean excess** — a small
shift, fat-tailed; "reaching" = within 0.01% (~1 pip); DEM-era quotes. RT3's
"first 1–3 M5 bars = cascade window" is an *engineering choice* inside the
documented "hours-scale" persistence, not a documented M5 result. The
directional claim survives; any EURUSD M5 window length or pip expectation must
come from our own post-2010 data.
**Verdict: HELD-WITH-CAVEAT.** Effect verified; magnitude tiny on average;
cascade-window parameterisation is unverified extrapolation.

### C3 — Osler (2000): published S/R predict interruptions; 95.5% end in 0/5; strength labels useless → no ex-ante strength scoring
**Depended on by:** RT3 Q3/P6; THEORY_SURVEY §1, §15; DN_LEVEL/DN_SALIENCE
rejection of touch-count strength.
**Attack.** Verified via FRBNY EPR HTML/PDF and the Fed's press release. All
three sub-claims hold: six firms' levels predicted intraday interruptions
(1996–98, DEM/JPY/GBP, indicative quotes, NY hours); 95.5% end in 0/5; the
firms' own strong/weak categories did not discriminate outcomes. **Misreading
risk:** the paper does *not* show that no salience ranking is possible — the
levels themselves were predictive. It falsifies *analysts' asserted* strength
tiers, not causal, structure-derived scoring. THEORY_SURVEY §15's feature-based
salience is therefore consistent with, not forbidden by, Osler 2000 — but
"Osler falsified strength labels" must never be cited against our own
measurable salience features.
**Verdict: HELD-WITH-CAVEAT.** Sub-claims verified; the corollary must be
narrowed to "no *unverifiable* ex-ante strength labels", not "no ranking".

### C4 — Glattfelder, Dupuis & Olsen (2011): DC count ∝ θ^1.88, overshoot ≈ θ → ABR-scaled pivots and zones
**Depended on by:** RT4 §2.3, §6, §12.1; THEORY_SURVEY §17; DN_SWING θ=k·ABR.
**Attack.** Verified via arXiv:0809.1040 (HTML full text) and DOI
10.1080/14697688.2010.481632 — 12 scaling laws on tick data, 13 pairs,
2003–2007 EBS era. The exponents are real. The transfer is the soft spot: the
laws are **tick-level**, event-time; RT4's θ=k·ABR on M5 bar extremes with
close-confirmation is an adaptation, and the quoted constants (C=1.1e-3,
coastline 6.4%/day at θ=0.05%) are priors, not parameters. RT4 §11 already
flags this honestly; the exposure is downstream — DN_SWING/LEVEL must not
treat k≈2–3 or half-width=q75(poke) as literature-backed constants. There is
also no evidence that a DC pivot is what Volman *perceives* — perceptual
fidelity is a golden-set question only.
**Verdict: HELD-WITH-CAVEAT.** Scaling laws verified as priors; bar-level
exponent, k values, and perceptual fidelity all require TUNE measurement.

### C5 — Kavajecz & Odders-White (2004): S/R coincide with limit-book depth peaks → depth consumption, weakening-per-touch
**Depended on by:** RT3 table/Q6/P6; THEORY_SURVEY §1 ("each touch executes
part of the book — a level *weakens* with use"); DN_SWING line 16–17, DN_LEVEL
line 22, DN_SALIENCE line 16/77 (`w7·depth_consumed` "K&OW anti-strength"),
DN_BRACKET line 11–13.
**Attack.** Verified via RePEc and SSRN/DOI (10.2139/ssrn.315660): NYSE
SuperDOT limit-book data, ~150 stocks, pre-decimalization. The paper shows
technical S/R forecasts *coincide with* pre-existing depth peaks — a locational
correlation. What it does **not** measure: that touches *consume* depth, or
that hold-probability declines monotonically per touch. "Weakens per touch" is
RT3's inference (plausible — executed orders leave the book), not a result of
this paper, and it is equity-book evidence applied to dealer-market FX. Yet
four DNs now encode it as design truth. The falsifiable version exists and is
cheap: on labelled levels, does hold-rate fall with touch count conditional on
prominence? Until that runs, `w7·depth_consumed` is a signed prior, not a fact.
**Verdict: WEAKENED.** Half verified (levels coincide with depth); half
promoted hypothesis (per-touch depletion → weakening) presented as sourced.

### C6 — Volman practitioner claims: ~3-object budget, edge behaviour, 14-pip room, EMA25-as-pressure, barrier-reclaim/TFF
**Depended on by:** spec throughout; RT1 §4–§6; THEORY_SURVEY §6, §14, §16.
**Attack.** Re-checked against local official excerpts: the barrier-reclaim
rule (signal-bar extreme must be back across the barrier), poke≠adjustment,
pre-break tighten, TFF, EMA25-as-pressure-not-S/R, and the 14-pip floor are
all genuinely in the primary material. Three exposures: (i) these are
**PRACTITIONER** rules — correctly graded in RT1, but the synthesis must not
let them drift to EVIDENCE; (ii) the parameters are 2010–2012 EURUSD
(~1-pip spread, 4–7-pip ABR) — RT1 §9 marks every number `[measure]`, and
THEORY_SURVEY must preserve that tag; (iii) **spec internal tension found:**
spec §1/line 20 says edges are "fixed once set" while spec §109–111 already
contains the re-anchor and tighten rules — RT1's "spec is half the rule"
critique is really *the spec contradicting itself*; adopt the versioned
pre-break re-anchor reading (which THEORY_SURVEY §3 does) and flag the §20
wording for the spec's next revision.
**Verdict: HELD-WITH-CAVEAT.** Rules verified as Volman's own; all remain
PRACTITIONER with era-bound parameters; the spec is internally split on edge
fixity.

### C7 — Brooks "most breakouts fail" vs Bulkowski rectangles vs Darvas continuation → BOX-break posture
**Depended on by:** RT2 §4.1, §7 test 7; THEORY_SURVEY §4.
**Attack.** Brooks's rule verified on his own site: ~80% of *breakout attempts*
in a TR context fail — note "attempts" includes mere pokes, E-mini M5, PRACTITIONER.
Bulkowski's numbers verified only via consistent multi-page search snippets
(direct fetch: HTTP 406 on every thepatternsite URL): rectangle breakeven-failure
15% up / 34% down, throwback/pullback 66%/64%, double-top non-confirmation
53%/63% (bear/bull), busted double tops 36%, sym-triangle 25%/37% failure,
rank 36/39; flags 44%/45%, pennants 54%. **The comparison is definitional:**
Brooks counts poke-attempts returning to the range on 5-min futures; Bulkowski
counts confirmed *daily closes* failing to travel ≥10% in bull-market equities.
Neither is a EURUSD M5 base rate. RT2 already refuses to pick a winner ("only
our own labelled data can settle") — correct. Darvas adds no statistics at all.
**Verdict: HELD-WITH-CAVEAT.** Disagreement is real but incommensurate;
Bulkowski stays [snippet-only] until refetched; posture default must be a
measured prior, not a school vote.

### C8 — Cross-school "contraction precedes expansion" → SQUEEZE/buildup salience
**Depended on by:** RT2 §4 conv. 3; THEORY_SURVEY §7; DN_SQUEEZE.
**Attack.** The convergence is real as description — Brooks tight-TR/barbwire,
Wyckoff phase-C contraction, AMT narrow-IB, classical triangle (volume declines
84–86% [snippet]), ICT AMD. Three problems: (i) the five schools are **not
independent** — ICT explicitly rebrands Wyckoff, AMT and Brooks share the
floor/tape lineage — convergence shows durability of a description, not five
measurements; (ii) the only measured family member is *weak*: Bulkowski's
symmetrical triangle ranks near the bottom (36/39) with 37% down-breakout
failure — "contraction" as a drawn object underperforms in the one dataset that
measured it; (iii) under volatility clustering, "contraction precedes
expansion" is nearly tautological — regimes alternate; the load-bearing claim
must be the narrower "a *wall-bracketed* contraction before a named edge
predicts the break better than ambient chop", which no school measured.
THEORY_SURVEY §7 already hedges correctly ("magnitude is folklore", golden n=2);
keep it a regime/context feature with the named-walls gate, never a signal.
**Verdict: HELD-WITH-CAVEAT.** Convergence verified; independence overstated;
predictive content unmeasured and the one measurement is unfavourable.

### C9 — Scheduled-event windows: US data 14:30 CET, ECB fix 14:15, option cut 16:00, WMR fix 17:00 CET, session clocks
**Depended on by:** RT3 Q5/P4–P5; THEORY_SURVEY §13; DN_TF; spec §213.
**Attack.** Verified: ABDV 2003 (AER 93(1):38–62) — announcement surprises
produce conditional-mean *jumps*, bad news asymmetric — supports the hard 14:30
gate. Krohn, Mueller & Whelan 2024 (JF, DOI 10.1111/jofi.13306; Warwick/BIS WP
texts fetched) — USD appreciates pre-fix, reverts post-fix at Tokyo 9:55 JST,
**ECB 14:15 Frankfurt**, London 16:00 — **but the paper's number is ~2bp, not
~2.5bp** (abstract, both WP versions): correct RT3's figure. Evans 2018
(JBF 87:233–247) — extraordinary fix-window volatility + negative serial
correlation, worst month-end; FCA OP46 — window now 5 min centred 16:00 London
= **17:00 CET/CEST year-round** (RT3's correction of the spec is right).
Option cut: the 10:00 ET EBS EURUSD volume/volatility spike is documented in
**Berger, Chaboud, Chernenko, Howorka & Wright (FRB IFDP 863 / JIE 2008)**,
*"when most foreign exchange options expire"* — RT3's attribution to Ito &
Hashimoto is a mis-citation (they own the U-shape seasonality claim, not this
spike). Tokyo fix 01:55 CET is winter-only (02:55 CEST summer — JST has no
DST). Window widths (±15, ±10) are our engineering choice, not the papers'.
**Verdict: HELD-WITH-CAVEAT.** Every event real and correctly timed after the
WMR correction; fix the 2.5→2bp slip and the option-cut attribution; treat
pinning (Ni et al. is equities) as unproven in FX — soft gate only.

### C10 — Jiang, Kelly & Xiu (2023) + Lo, Mamaysky & Wang (2000): extrema geometry as a valid *representation*
**Depended on by:** RT4 §7, §12; THEORY_SURVEY §15, §17.
**Attack.** Both verified: JKX (JF 78(6), DOI 10.1111/jofi.13268 — CNN on
rendered OHLC images beats numeric CNN, patterns transfer across scales and
markets); LMW (JF 55(4):1705–1765, NBER w7613 — kernel-smoothed extrema
templates carry incremental information, US stocks 1962–96). The over-reach:
these papers show *predictive information exists in geometric/visual
representations of price* — they do not show that *our specific drawn-object
grammar* (boxes, lines, levels) is the right representation. JKX actually
reports learned patterns "differ significantly from commonly analysed trend
signals" — which cuts against assuming textbook geometry is what carries signal.
And §17's use of JKX for ABR-normalisation is a motivated analogy, not a result
about FX M5 or about hand-coded objects. LMW does directly support "patterns =
relations among few extrema" — that half stands.
**Verdict: HELD-WITH-CAVEAT.** Keep as "academic bridge" — evidence that
extrema-geometry is a *plausible, testable* representation, not proof it is
Volman's or the predictive one.

---

## B. Citation verification table

| # | Citation (as used) | Exists? | URL fetched/attempted | Supports RT claim? |
|---|---|---|---|---|
| 1 | Osler 2000, FRBNY EPR 6(2):53–68 | Yes | newyorkfed.org/research/epr/00v06n2/0007osle.html (+.pdf, binary) | **Yes** — interruptions, 95.5% 0/5, labels null; era caveats apply |
| 2 | Osler 2003, JF 58(4):1791–1819 | Yes | onlinelibrary.wiley.com/doi/10.1111/1540-6261.00588; SR125 PDF [snippet] | **Yes** — TP at round, SL just beyond; one bank, 1999–2000 |
| 3 | Osler 2005, JIMF 24(2):219–241 | Yes | newyorkfed.org/medialibrary/media/research/staff_reports/sr150.html; faculty.georgetown.edu/…/osler1.pdf [snippet] | **Yes** — 0.061% vs 0.054%/15min; small-mean, DEM-era |
| 4 | Glattfelder, Dupuis & Olsen 2011, QF 11(4) | Yes | arxiv.org/abs/0809.1040; arxiv.org/html/0809.1040v2 (full text) | **Yes** — θ^1.88, overshoot≈θ on ticks; bar transfer unproven |
| 5 | Kavajecz & Odders-White 2004, RFS 17(4) | Yes | ideas.repec.org/a/oup/rfinst/v17y2004i4p1043-1071.html; SSRN 315660 | **Partial** — depth coincidence yes; per-touch depletion not studied |
| 6 | Bulkowski thepatternsite stats | Yes (site) | thepatternsite.com/recttops.html, /st.html, /BustDoubleTops.html, /Confirmation.html, /pennants.html — **all HTTP 406** | **Partial [SNIPPET-ONLY]** — every number via search snippets; internally consistent, matches his books' methodology; re-fetch before spec use |
| 7 | Brooks "80% rule" | Yes | brookstradingcourse.com/analysis/market-update/sp-cash-index-new-all-time-high/ [snippet] | **Yes** — real claim; but *attempts in TR context*, E-mini, PRACTITIONER |
| 8 | Andersen, Bollerslev, Diebold & Vega 2003, AER 93(1) | Yes | aeaweb.org/articles?id=10.1257/000282803321455151; nber.org/papers/w8959 | **Yes** — conditional-mean jumps, asymmetric news |
| 9 | Krohn, Mueller & Whelan 2024, JF 79 | Yes | onlinelibrary.wiley.com/doi/10.1111/jofi.13306; bis.org/…/mueller.pdf; wrap.warwick.ac.uk WP | **Partial** — pattern + fixes verified incl. ECB 14:15; **RT3's ~2.5bp is wrong: paper says ~2bp** |
| 10 | Evans 2018, JBF 87:233–247 | Yes | sciencedirect.com/science/article/abs/pii/S0378426617302327; SSRN 2487991 | **Yes** — fix-window volatility, negative serial corr., month-end |
| 11 | Ito & Hashimoto 2006 (10:00 ET option-cut spike) | Yes (paper) | federalreserve.gov/pubs/ifdp/2006/863/ifdp863.htm | **Partial — mis-citation:** the option-expiry spike is documented by **Berger et al. IFDP 863/JIE 2008**; I&H own the U-shape/seasonality claim |
| 12 | Tsang WP050-10 "Directional Changes, Definitions" | Yes | bracil.net/ccfea/WorkingPapers/ (listing) | **Yes** — exists as listed; content not fetched (PDF not opened) |
| 13 | Dreiss 1992 choppiness, CTCR Jul/Aug | Yes | Secondary only: Futures Mag Oct 1993 (Gibbons Burke), Wealth-Lab wiki refs | **Partial [snippet/secondary]** — article, author, date and CI construction confirmed via citations; original not fetchable; PRACTITIONER grade correct |
| 14 | Jiang, Kelly & Xiu 2023, JF 78(6) | Yes | doi.org/10.1111/jofi.13268; SSRN 3756587; economics.yale.edu PDF | **Yes** — image-CNN predictability, context transfer; equities, predictive ≠ perceptual |
| 15 | Lo, Mamaysky & Wang 2000, JF 55(4) | Yes | nber.org/papers/w7613; web.mit.edu/Alo/www/Papers/1705-1765.pdf | **Yes** — extrema-template formalisation, incremental info; equities daily |

**Failed or degraded fetches to record:** all thepatternsite.com pages (HTTP
406 — every Bulkowski number remains snippet-only); FRBNY/journal PDFs
(binary — headline numbers taken from official abstracts/HTML); CTCR 1992
(unfetchable — secondary citations only). No hallucinated citation was found;
the two genuine defects are the **~2.5bp→~2bp misquote (Krohn et al.)** and the
**Ito & Hashimoto ↔ Berger et al. attribution slip**.

## C. Folklore audit

| Folklore item | Where it appears | Graded correctly? | Consumed as evidence anyway? |
|---|---|---|---|
| "Levels strengthen with touches" | RT3 §4; THEORY_SURVEY §1 | **Yes** — FOLKLORE, mechanism argues opposite | No — but see next row |
| **"Levels weaken per touch"** (mirror-image claim) | RT3 Q6/P5–P6; DN_SWING:16, DN_LEVEL:22, DN_SALIENCE:16,77, DN_BRACKET:11 | **No** — presented as K&OW mechanism; it is an untested inference | **Yes** — `w7·depth_consumed` and per-touch consumption bookkeeping built on it; must be TUNE-tested |
| "Third touch validates the line" | RT2 matrix/P11; THEORY_SURVEY §9 | **Yes** — FOLKLORE | Partially — P11 uses it as a design rule; keep as hypothesis only |
| Nth-touch / "third touch is best" rules | RT3 §4 | **Yes** — FOLKLORE | No |
| ICT/SMC mechanism language ("the algorithm", engineered sweeps, liquidity pools as motive) | RT2 ICT column; THEORY_SURVEY §11 | **Yes** — P/F, motive layer flagged unverifiable | Borderline — DN_BRACKET's "consumed wall" borrows the vocabulary; the *geometry* is fine, the motive is not load-bearing |
| "Stored energy"/"coiling" causal language | RT2 AMT cell (flagged "descriptive, not doctrinal"); THEORY_SURVEY §7 title | Mostly — §7 hedges | Watch it: "stored energy" must stay bound to the depth/stop-cluster mechanism, not float free as a claim |
| Cross-school convergence as *independent* corroboration | RT2 §4 ("independent schools"); THEORY_SURVEY §5 ("five independent traditions") | **Partially wrong** — ICT derives from Wyckoff; AMT/Brooks share floor lineage; Bulkowski is the only independent measurement | Yes, mildly — §5's "highest-consensus" framing should read "most *re-described*", not "independently corroborated" |
| "Equal highs = liquidity magnet" | RT2 P6; THEORY_SURVEY §11 | **Yes** — P6 is falsifiable version with a stated test | No — correctly staged |
| Tick-volume as Wyckoff volume | RT2 P9 | **Yes** — explicit hypothesis flag | No |
| Volman's numeric rules (14-pip, 20/10 bracket, EMA25) | RT1 §4–§5; spec | **Yes** — PRACTITIONER, every parameter `[measure]` | No — but they must never graduate to EVIDENCE without the TUNE numbers |
| "Most breakouts fail" as base rate | RT2 §4.1 | **Yes** — flagged incommensurate with Bulkowski | No — RT2 test 7 correctly defers to labelled data |
| Osler 2000 → "no ex-ante strength" | RT3 P6; THEORY_SURVEY §15 | **Over-broad corollary** — falsified analyst labels, not causal ranking | Borderline — ensure it is never cited against our own measurable salience features |
| Analyst/publisher "strong level" labels | RT3 §4 | **Yes** — falsified outright | No |

## Corrections THEORY_SURVEY must absorb

1. §1, §7, §15 — downgrade "each touch consumes the book → levels weaken per touch" from sourced mechanism to an explicit hypothesis pending the touch-count-vs-hold-rate TUNE test, and propagate the downgrade to DN_SWING, DN_LEVEL, DN_SALIENCE (`w7`), DN_BRACKET.
2. §13 — correct Krohn et al. 2024's pre-fix drift from ~2.5bp to ~2bp.
3. §13 — attribute the 10:00 ET option-expiry EBS spike to Berger, Chaboud, Chernenko, Howorka & Wright (IFDP 863 / JIE 2008), not Ito & Hashimoto.
4. §13 — note the Tokyo fix is 01:55 CET in winter only (02:55 CEST in summer; JST never shifts) and state that all window widths are our engineering choice, not the papers'.
5. §13/spec §213 — the spec's "news window 14:30/16:00 CET" is ambiguous: keep 16:00 CET for the option cut (soft) and write 17:00 CET/CEST explicitly for the WMR fix (hard).
6. §1, §15 — narrow the Osler-2000 corollary to "analysts' asserted strength labels carry no predictive content", never cite it against our own causal salience features.
7. §4 — label Brooks's 80% as "breakout *attempt* failure in a TR context on E-mini", incommensurate with Bulkowski's ≥10%-travel daily-equity definition.
8. §5, §11 — mark every Bulkowski statistic [snippet-only, HTTP 406] pending a successful re-fetch, and keep his directional asymmetries quarantined to bull-market daily equities.
9. §7 — restate the convergence as "most re-described" rather than "five independent traditions" and add that the only measured member (Bulkowski's symmetrical triangle, rank 36/39) is a weak performer.
10. §17 — retag JKX as motivation for *testing* ABR-normalisation and extrema grammar, not as evidence for them; the predictive≠perceptual caveat belongs wherever the citation appears.
11. §3 — record that spec v1 is internally split ("edges fixed once set" at §1 vs the re-anchor/tighten rules at §109–111) and that the survey adopts the versioned pre-break re-anchor reading; flag §20 for the spec's next revision.
12. §1/P3 — keep Osler's cascade/zone magnitudes explicitly marked "DEM-era priors requiring post-2010 EURUSD measurement", and do not let the 1–3-bar cascade window or asymmetric pip offsets appear as sourced constants anywhere downstream.

— End of RT5_REVIEW —
