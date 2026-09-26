# R02 PREREG — arrival-matched zone-physics test (PRE-FREEZE DRAFT FOR RE-REVIEW)

Status: **NOT FROZEN**. Second draft — revised after the neutral review
(`rounds/R02/REVIEW_R02_PREREG.md`, verdict FAIL, findings R02-F1..F10)
per LEAD RULING R02-C1. All four MAJOR findings are fixed in code and in
this text; every support number in §3 was re-measured under the corrected
definitions. No outcome has been computed on real data anywhere in this
round; the resolver (`arrival_outcome.py`) and the estimator
(`arrival_estimate.py`) exist and are unit-tested on synthetic data only
(11/11 pass). Everything measurable below is event-level, `<= t`.

Round context: R01's bounce verdict was withdrawn by the Lead after
adversarial review F1 (real-vs-control approach-distance confound, 0.3 vs
2.2 ATR median). R01 now reports "no valid evidence about zone physics in
either direction". R02 asks the same question with both arms drawn by one
event-generating process.

## 0. DEVIATIONS AND DECISIONS (pre-declared, with the measurement that forced each)

This section is the "diff vs draft" required by the R01 process defect
(the draft→frozen §3.2 freshness tightening slipped through undeclared).
Every number cited was measured outcome-blind on DESIGN data only; the
tables live in `rounds/R02/FEASIBILITY.md` and the `arrival_freeze.py`
JSON log (frozen spec, all four symbols).

D0. PRIOR DESIGN (R01, withdrawn): per real event, K=5 arbitrary bands
    drawn Uniform over the same-side 5-day range, near edge >= 1 ATR from
    `c[t-1]`. Confounded: real zones sit next to price (median 0.3 ATR),
    controls sit ~2.2 ATR away; controls only fire after an impulse, so
    the comparison was "hover/retest episode" vs "post-impulse arrival".
    REPLACED, not patched — see D1.

D1. EVENT PROCESS ON A ZONE-INDEPENDENT GRID (LEAD RULING R02-B-1).
    A literal same-distance same-side control is degenerate (same
    distance + same side + same bar = the same price as the zone), so
    controls are not drawn around events; instead both arms come from
    arrival events on a daily price grid that does not know where zones
    are. Forcing measurement: `dist_cp` (band mid to `c[t-1]`, in A(t))
    = 0.35-0.68 treated vs 0.37-0.70 control across all 24
    symbol-generator cells — vs 0.3 vs 2.2 in R01. The confound is
    removed by construction.

D2. `w_g = 0.75 x median armed width` (not 1.0x), `margin = 0.5 x w_g`,
    anchor = day open, prevclose pre-declared as robustness rerun,
    NO distance restriction (R02-B-1). Forcing measurements, all at the
    frozen spec (w=0.75, m=0.5, anchor=open), PRIMARY-key supT:
    `line1_cluster` 0.951/0.950/0.962/0.956 (EURUSD/GBPUSD/AUDUSD/USDJPY)
    — the only setting where the densest generator clears supT >= 0.95;
    at w=1.0 it was 0.912/0.900/—/—. All other generators >= 0.986.
    Anchor moved supT < 0.02 and counts < 3% in every cell tested —
    immaterial, kept day-open for determinism. The `dist_cp <= 2.5`
    restricted control arm changed supT < 0.005 everywhere (`supTn ~=
    supT`) — distance restriction killed by measurement, recorded as the
    reason.

D3. `since_touch` SPLIT AS CO-PRIMARY (R02-B-2 — the ruling's stated
    top priority). Shorter `since_touch` for treated bands is partly
    the treatment itself (zones arm where price recently was), so the
    primary key does NOT include it; instead the same estimate is
    always reported under a co-primary key that adds a `since_touch`
    TERCILE. Decision rule, frozen before any outcome: a "zones matter"
    claim requires the PRIMARY to pass the gate AND the CO-PRIMARY to
    keep the same sign with at least HALF the magnitude. Primary pass +
    co-primary collapse or flip => verdict "RECENCY, NOT STRUCTURE" —
    reported as the finding; no generator is promoted on it.
    Forcing measurement (fine-key supT at frozen spec, m=0.5):
    line1 0.696/0.706/0.626/0.639; fractal_h1 0.965/0.966/0.973/0.973;
    kde_swing 0.914/0.923/0.916/0.924; profile_va 0.967/0.960/0.983/0.977;
    sd_base 0.985/0.982/0.992/0.989; ref_levels 0.985/0.984/0.994/0.993.
    **`line1_cluster` is declared UNDERPOWERED FOR THE CO-PRIMARY in
    advance** (fine-key supT < 0.90 on every symbol). A coarser median
    split does not rescue it (supT 0.691-0.770, all four symbols) — the
    treated arm is recency-concentrated by construction. Consequence:
    a line1 primary pass cannot be confirmed or falsified by the
    co-primary; its line reads "PRIMARY ONLY — recency not separable"
    and it may win only under the doubled bar of D7. See
    `rounds/R02/ASK_LEAD.md` for the measurement history.

D4. ENDPOINTS AND MULTIPLICITY (R02-B-3). Primary family = 6 generators
    x 2 endpoints (bounce, break-continuation) under the primary
    stratification = 12 hypotheses, BH-FDR q <= 0.10 across all 12.
    The co-primary is a CONFIRMATORY CONDITION, not a family: it can
    only downgrade a claim, never create one; it does not enter BH.
    The stall endpoint (NONE share) is descriptive with CIs, never
    gated. The T-vs-X-vs-C three-way contrast (zone present / zone
    nearby / zone absent) is a pre-declared SECONDARY, reported with
    CIs, never gated.

D5. ESTIMATOR (R02-B-4). Stratified ATT:
    `D = sum_s omega_s (p_T,s - p_C,s)` with `omega_s` = treated share
    of stratum s over the common-support set (strata containing >= 1
    treated AND >= 1 control); percentile CI from bootstrap clustered
    by server day, B = 10,000, seed 20260920; dropped share per arm
    reported. New pre-declared floor: supT >= 0.90 at freeze, else that
    generator is UNDERPOWERED and cannot win. Gate thresholds are the
    charter's unchanged: D >= +5.0pp, CI lower bound > 0, monotone
    across strength terciles (treated arm, terciles fixed before any
    outcome join), D > 0 in >= 3/4 core symbols and >= 4/6 DESIGN
    years, BH q <= 0.10, >= 1,000 resolved events per arm per
    generator. Winner rule: see D6/D7 (supersedes the SHORTLIST §4
    incumbent rule — there is no incumbent in R02).

D6. NO INCUMBENT — TIE-SET WINNER RULE (R02-B2-1). R01 promoted nobody;
    `line1_cluster` was the working default by inertia, not merit, and
    an inertia default does not get the +2.0pp materiality protection
    that exists to stop churn among *proven* things. Rule: rank
    gate-passers by primary D_top; the leader is a clear winner only
    if it beats the RUNNER-UP by >= +2.0pp; otherwise declare a TIE
    SET (every gate-passer within 2.0pp of the leader) and carry the
    whole set forward, ordered by pre-declared tie-breaks (fewer
    parameters, then fewer armed zones per bar). Forcing measurement:
    ASK_LEAD item 1 — the winner-rule baseline's own mechanism is
    unidentifiable (D3), so no candidate may be privileged.

D7. `line1_cluster` DOUBLED BAR (R02-B2-2). Stays a candidate, declared
    UNDERPOWERED-CO-PRIMARY per D3. The winner is the object family the
    next round builds on, so carrying an object whose mechanism cannot
    be identified is a real cost. Pre-declared: `line1_cluster` is
    declared winner only if it beats the best co-primary-CONFIRMED
    generator by >= +5.0pp on the primary (twice the materiality
    margin — the price of an unidentifiable mechanism). Below that the
    winner is the best co-primary-confirmed generator and line1's line
    reads "PRIMARY ONLY — recency not separable". Forcing measurement:
    fine-key supT 0.626-0.706 tercile, 0.691-0.770 median split —
    unidentifiable at ANY recency granularity.

D8. THIN SUPPORT FLAG (R02-B2-3). Any generator within 0.02 of a
    support floor is flagged THIN SUPPORT at freeze: its co-primary
    result must additionally hold under the prevclose-anchor
    robustness rerun; a sign flip there downgrades it to
    UNDERPOWERED-CO-PRIMARY. Forcing measurement: `kde_swing` fine-key
    supT 0.914/0.923/0.916/0.924 — clears 0.90 by <= 0.024 on every
    symbol. Declared before any outcome so it cannot be argued about
    afterwards. Current flag list: `kde_swing` (co-primary only).

D9. ARMS AT t-1, LIVE-ZONE CONTROL (R02-C1-1/2; reviewer R02-F3, MAJOR).
    Two defects in the pre-review arm rule: (a) arms were evaluated on
    zone state replayed THROUGH bar t — a zone that broke on the
    arrival bar itself was unarmed at t, so the most break-y treated
    episodes leaked into CONTROL (measured: 14.9% of line1 controls
    were TREATED at t-1); (b) CONTROL meant "no ARMED zone", so bands
    sitting on live-but-unarmed structure (broken/deduped/capped
    zones) were called zone-free (measured: 22.2% of line1 controls
    overlapped a live unarmed zone). Corrected definitions: labels are
    computed at `tp = t-1` (the measured bar can never decide its own
    arm); TREATED = an ARMED zone overlaps G at tp; CONTROL = NO LIVE
    zone of g — armed or not, broken or intact — within
    `margin * w_p` at tp; EXCLUDED = everything between. The three-way
    contrast is now "armed zone / something live but not armed /
    genuinely nothing". Forcing measurement: EURUSD line1 at m=0.5
    moved to T=15921/C=4117/X=4436 (was 15448/6723/2303) — the honest
    control pool is ~39% smaller.

D10. ANCHOR-DISTANCE DECILE IN BOTH STRATUM KEYS (R02-C1-3; R02-F2,
    MAJOR). Zones arm near where price hangs out, so treated bands
    cluster near the day anchor; a control event requires genuinely
    empty space, which lives further from the open. Measured medians
    |mid-anchor|/A(t): treated 1.24-1.57 vs control 1.87-2.48 ATR
    across all four symbols — R01's F1 confound surviving through the
    anchor coordinate. The fix is to put it IN the key, not around it:
    `anchor_dist` decile (pooled T+C per (generator, symbol)) is added
    to BOTH the primary and co-primary stratum keys. Consequence
    measured in D14: this is the single largest driver of the support
    collapse, and the collapse is real — the far-from-anchor region
    genuinely contains almost no zones to compare.

D11. SYMMETRIC RECENCY + FRESH-TO-ZONE (R02-C1-4; R02-F1, MAJOR).
    Band-level `since_touch` is blind to the channel that matters: a
    zone overlapping G is typically wider than G, so bars in
    `[t-24,t-1]` can touch the zone's overhang without touching G —
    the event fires "fresh to the band" while price is mid-retest of
    the actual structure. Measured at full scale: the share of treated
    events whose overlapping armed zone was touched in `[t-24,t-1]`
    (`zone_stale_share`) is 28.7%-63.9% per (generator, symbol) —
    line1 0.605-0.639, kde_swing 0.482-0.524, profile_va 0.408-0.439,
    fractal_h1 0.374-0.417, sd_base 0.350-0.385, ref_levels
    0.287-0.314. Two corrections: (a) the co-primary key uses
    `since_near` = bars since the last bar whose range intersected
    `[mid - w_p/2, mid + w_p/2]` — symmetric, computable identically
    in both arms; band-level `since_touch` remains as a reported
    diagnostic only; (b) FRESH-TO-ZONE clause added to D3's decision
    rule — the co-primary same-sign + >= half-magnitude test must ALSO
    hold when the treated arm is restricted to `zone_fresh` events
    (no overlapping armed zone intersected in `[t-24,t-1]`); the
    excluded share is reported per generator. Controls need no clause
    — they have no zone by construction.

D12. ESTIMATOR PINNED IN CODE (R02-C1-5; R02-F4, MAJOR).
    `research/arrival/arrival_estimate.py` is written and unit-tested
    on synthetic data (never run on real data pre-freeze). §6 quotes
    its frozen behaviour sentence-for-sentence. Rulings it freezes:
    `omega_s = n_T,s / n_T(CS)` (treated share, sums to 1 on the
    common-support set); strata computed WITHIN each symbol; headline
    `D_g` = treated-share-weighted mean of the four per-symbol Ds,
    each reported; hour bucket = `utc_min // 240` (six 4h buckets);
    `D_top` = the same stratified ATT restricted to treated events
    whose `zone_S` is in the top tercile, versus ALL control events
    sharing their strata (common support recomputed on the restricted
    treated set); multi-zone overlap strength = MAX `zone_S` over
    armed zones overlapping G; tercile bounds computed before any
    outcome join and recorded in FREEZE.json; "monotone" =
    non-decreasing across terciles (`D_bot <= D_mid <= D_top`);
    "resolved" = BOUNCE or BREAK, and the >=1,000 floor is per arm per
    generator pooled across the four symbols. R02-F6: a week-cluster
    CI (same bootstrap, `cluster = bar_t // 604800`) is a pre-declared
    robustness rerun, reported alongside, never gated. R02-F8: the
    co-primary estimate uses its own fine-key common-support set; the
    comparison to the primary D is a point-estimate rule
    (`D_fine >= 0.5 * D_primary`, same sign) across differing support
    populations, declared as such — likewise D8's "holds under
    prevclose" means the same sign + half-magnitude rule. R02-F9:
    `u_g` is a fixed design constant per (generator, symbol) measured
    once over the whole DESIGN window. R02-F7: coverage fraction
    (`cover` = overlap width / `w_p`, max over overlapping armed
    zones) is a reported secondary split of the treated arm with CIs,
    never gated.

D13. ADVERSE-DIRECTION VERDICT (R02-C1-5; R02-F5, MODERATE). A
    significant NEGATIVE D (CI upper bound < 0) is a finding —
    **"zones ADVERSE"**: arriving at a marked band is measurably WORSE
    than arriving at an unmarked one of the same geometry. It is
    reported symmetrically with the positive gate, is not a PASS, and
    is not a null. R01's actual answer (-5..-7pp) was exactly this
    shape; the verdict language must not leave the most likely
    surprise unscripted.

D14. RE-MEASURED SUPPORT UNDER THE FINAL KEY (R02-C1-6) — the
    corrected definitions collapse common support. PRIMARY-key supT at
    m=0.5 (all four symbols): `line1_cluster` 0.244-0.290;
    `fractal_h1` 0.756-0.791; `kde_swing` 0.574-0.626; `profile_va`
    0.807-0.834; `sd_base` 0.900-0.913; `ref_levels` 0.845-0.886.
    FINE-key supT: ALL SIX below the floor (max 0.723, sd_base
    GBPUSD). Declarations frozen before any outcome:
    * `line1_cluster`: UNDERPOWERED — primary AND co-primary. A
      generator that marks nearly every location cannot be compared
      against locations it has not marked; that is a finding about the
      generator, not a defect of the design.
    * `fractal_h1`, `kde_swing`, `profile_va`, `ref_levels`:
      UNDERPOWERED — primary (hence co-primary); supT < 0.90 on every
      symbol.
    * `sd_base`: clears the primary floor on all four symbols — and is
      THIN SUPPORT under D8 (0.9002 EURUSD, within 0.02 everywhere);
      it does NOT clear the co-primary floor (0.704-0.723) ->
      UNDERPOWERED FOR THE CO-PRIMARY.
    Consequence: under the floor as ruled, R02 can produce at most ONE
    primary-evaluable generator (`sd_base`) and ZERO co-primary-
    confirmable claims; the BH family reduces to the hypotheses that
    clear the floor (an UNDERPOWERED generator produces no test, not a
    failed test). Whether to relax the floor or the key granularity is
    a Lead decision — flagged in `ASK_LEAD.md`, not silently repaired:
    coarsening the anchor decile to quintiles partially rescues
    primary supT (EURUSD: fractal 0.909, profile_va 0.940, sd_base
    0.960, ref_levels 0.965; line1 still 0.388) but does not rescue
    the co-primary anywhere. The earlier "all 24 primary cells >=
    0.90" measurement (§0-D2) was made under the superseded armed-only
    arm definitions and no longer holds — recorded, not erased.

D15. THE PIVOT (R02-D): the binary marked-vs-unmarked contrast fails
    positivity BY CONSTRUCTION — a zone exists because price did
    something there, so "place with a zone" and "place without a zone"
    are different kinds of location and do not overlap on the
    covariates that decide behavior. That non-identifiability is R02's
    first finding (`rounds/R02/FINDING_1_NONIDENTIFIABILITY.md`), not
    an obstacle. The round re-scopes to contrasts where BOTH arms are
    zone arrivals: E1 strength (primary) and E2 cross-generator
    (secondary). The binary T/C/X tables remain in the record as the
    evidence for FINDING_1; the binary estimand is retired, not
    silently continued.

D16. E1 — STRENGTH CONTRAST (primary). Among arrivals at ARMED zones of
    generator g (state at t-1, per D9): does the TOP `zone_S` tercile
    behave differently from the BOTTOM? Arms: top vs bottom tercile of
    pooled treated `zone_S` per (generator, symbol) — bounds computed
    before any outcome join, recorded in FREEZE.json; middle tercile
    excluded from the contrast, reported descriptively. This is the
    question the trading system actually asks: not "do lines exist"
    but "does my ranking of lines carry information".

D17. E2 — CROSS-GENERATOR (secondary, conditional on overlap). For
    unordered pair {g,h}: arrivals at a band marked by g but not h
    versus marked by h but not g, on the FINER of the two grids
    (smaller `u_atr` — declared rule, not chosen per pair). "Marked by
    g" = armed_g overlaps G at t-1; "not marked by h" additionally
    requires NO LIVE zone of h (armed or not) overlapping G at t-1.
    Generators become each other's controls, holding "a place price
    has been" roughly fixed while varying how it was drawn.

D18. ESTIMATOR PIVOT (R02-D §4): propensity-weighted ATT is the
    PRIMARY estimator for E1/E2 — the right tool once overlap exists,
    not a rescue of the binary contrast. Frozen spec (also the module
    docstring of `arrival_contrast.py` / `arrival_estimate.py`):
    unpenalized IRLS logistic regression of the arm indicator on
    {approach_atr, anchor_dist, log ATR, sin/cos(2*pi*utc_min/1440),
    since_near, pos_r5, side} (D24), features standardized inside the
    fit, fitted
    per symbol per generator (per pair for E2); ATT weights w_A=1,
    w_B=e/(1-e); trim e outside [0.05, 0.95] in both arms (trimmed
    share reported); control weights winsorized at their own 99th
    percentile within the cell; outcome means over resolved events
    only; day-cluster bootstrap B=10,000 seed 20260920 REFITS the
    propensity model inside every replicate — and for residual
    cells the residual OLS AND tercile assignment as well (D29a) —
    (week-cluster rerun reported alongside, ungated). Every
    `bootstrap_*` RETAINS its replicate array and returns
    {lo, hi, p, n_boot, boots}; the p-value recipe is one sentence,
    identical for every experiment: `p = (1 + #{D_b <= 0}) / (B + 1)`,
    one-sided (D39a). The generator-level statistic is the
    sample-size-weighted mean of contributing-cell D's, and
    `bootstrap_pooled` resamples days within each cell and recomputes
    that weighted mean per replicate (D39c). Exact-strata
    ATT stays as the
    pre-declared robustness view. BALANCE GATE: max |SMD| <= 0.10 on
    all eight features after weighting, measured and declared BEFORE
    the freeze — a cell that cannot reach balance is UNDERPOWERED
    (R02-D §5) and produces no test. Nothing about the specification
    may be chosen after an outcome is seen.

D19. FRESH-RESTRICTED CONFIRMATORY DROPPED (R02-E §1). Measured
    before any outcome: the fresh-to-zone restricted contrast fails
    its own balance gate in 23/24 cells (post-weighting max |SMD|
    0.077-0.697; only AUDUSD line1 passes at 0.098). The failure is
    MECHANICAL, not evidential — strong zones attract retests, so
    restricting to fresh zones starves one arm and the propensity
    saturates. A test that can only fail is theatre, not a gate: it
    is dropped from the design, with the measurement kept here and in
    FEASIBILITY.md §12 as the record. The D11 `zone_fresh` fields
    remain computed and reported as diagnostics only.

D20. RECENCY SUB-GATE (R02-E §2). `since_near` is already a
    propensity feature, so every balance-passing estimate is
    recency-adjusted — the thing the dropped restriction was meant
    to buy, bought more cheaply by weighting. Pinned: in any E1 cell
    that will carry a strength claim, `since_near` must balance to
    |SMD| <= 0.05 after weighting (stricter than the 0.10 general
    gate); a cell that passes the general gate but misses 0.05 on
    `since_near` is stamped RECENCY-UNSEPARATED, produces an estimate,
    and cannot carry the claim. Measured blind, all four symbols
    (since_near post-weighting |SMD|): line1 0.018-0.042 PASS 4/4;
    fractal_h1 0.013-0.027 PASS 4/4; sd_base 0.040-0.058 PASS 2/4
    (EURUSD 0.051, USDJPY 0.058 unseparated); kde_swing 0.069-0.103
    FAIL 4/4 — RECENCY-UNSEPARATED everywhere despite passing the
    general gate on 3/4; profile_va and ref_levels fail regardless
    (already UNDERPOWERED).

D21. RESIDUAL-STRENGTH CONFIRMATORY (R02-E §3, regressor set
    corrected by R02-G-2/D25 — the real test of the scoring layer).
    Pinned spec (`arrival_contrast.py`): `zone_S` is regressed by
    unpenalized OLS on the eight propensity features plus
    `zone_touches`, `zone_since_touch` (min(tp - last_touch, 1440)),
    and `zone_fresh` (0/1) of the argmax armed zone at t-1 — the
    zone's own retest history is IN the regressor set, so "the part
    recency cannot explain" is a description of the code, not a hope.
    Features standardized inside the fit, per symbol
    per generator over the pooled treated set; the identical
    top-vs-bottom tercile contrast (same estimator, same gates, same
    endpoints) is then run on the RESIDUALS — the part of the score
    that recency/touch-history cannot explain. Unlike the dropped
    restriction this can actually pass: measured blind under the
    corrected regressor set, the residual contrast balances in all 24
    cells (max post-weighting |SMD| <= 0.035, near-zero by
    construction since the residual is orthogonal to the
    regressors); its own zone-recency sub-gate passes in 6/24 cells
    (D25 table in §3b). Verdict language (frozen): a
    "strength score measures structure" claim requires the PRIMARY to
    pass AND the residual contrast to keep the same sign with at least
    HALF the magnitude; otherwise the cell reads "RECENCY-DOMINATED
    — the ranking works but it is a recency proxy", the generator
    is still carried forward on the primary, and the scoring layer
    gets no credit. The residual confirmatory is a confirmatory
    condition, not a member of either hypothesis family — it can
    only downgrade a claim, never create one. D7's doubled-bar
    machinery is superseded: the confirmatory is now evaluable in
    every cell, so there is no "unconfirmable" case left for a
    doubled bar to govern.

D22. UNDERPOWERED-BY-CONSTRUCTION DECLARED (R02-E §4).
    `ref_levels` fails balance at max |SMD| 0.548-0.678 on every
    symbol — its strength score is nearly a deterministic function
    of the covariates (the propensity model separates the arms, trim
    shares reach 28-52%), leaving no independent variation to test.
    That is a finding about the score, not a power problem: its
    ranking carries nothing beyond what the covariates already say.
    `profile_va` fails at 0.146-0.228 with only ~745-877 events/arm —
    same declaration, weaker form. Both are UNDERPOWERED for E1 in all
    four symbols, declared before outcomes; their residual-contrast
    balance (PASS everywhere, §D21) is reported but cannot rescue
    an unidentified primary.
D23. ATTENUATION GUARD ON THE RESIDUAL CONFIRMATORY (R02-E2). The
    residual contrast's 24/24 balance is MECHANICAL — residualizing
    makes the residual orthogonal to the covariates by construction,
    so clean balance there is evidence of nothing. The real weakness
    is the opposite of confounding: ATTENUATION. If a score is mostly
    a function of recency and geometry, stripping that part leaves
    mostly noise, and a contrast on noise returns a null every time;
    reading that null as "the score is a recency proxy" repeats R01's
    error (uninformative measurement mistaken for a negative finding).
    Pre-declared, fixed blind, never movable after outcomes: (a) every
    residual result is reported next to the regression's R-squared
    (share of the score that recency + geometry already explain) and
    the residual's variance share; (b) a cell with R-squared >= 0.90
    has its residual confirmatory declared UNDERPOWERED-BY-CONSTRUCTION
    in advance — a null there is uninformative and may never be
    quoted as evidence that the score is a recency proxy; (c) a null
    residual result carries evidential weight ONLY when the residual
    retains meaningful variance (R-squared < 0.90); otherwise the cell
    reports "no usable residual signal to test". The 0.90 and 0.05
    thresholds are both frozen here.

D24. `side` JOINS THE PROPENSITY MODEL AND THE BALANCE GATE (R02-G-1,
    review R2-F3). Arrival direction (+1/-1) was in neither the model
    nor the gate; the reviewer measured arm imbalance up to SMD ~0.32
    (sd_base side-share 0.484/0.645), which fails the gate outright if
    checked. FEATURES is now 8: the seven R02-D features plus `side`;
    the balance gate applies to all eight. Balance re-measured under
    the 8-feature model in the same blind pass (section 3b tables).
    Cells that fail only because of `side` are reported as such.

D25. ZONE-LEVEL RECENCY ENTERS THE RESIDUAL OLS AND THE SUB-GATE
    (R02-G-2, review R2-F1/F2). `since_near` is band-level and floored
    at >= 24 bars by the freshness rule — it cannot see in-window
    retests of the (wider) zone, and the reviewer measured zone_fresh
    shares of 0.23-0.51 (top tercile) vs 0.52-0.97 (bottom): top-tercile
    selection IS partly a recency selection. Fixes: (a) the residual
    OLS regressor set is now the 8 propensity features plus
    `zone_touches`, `zone_since_touch` (= min(tp - zone's last_touch,
    1440) bars; never-touched -> 1440) and `zone_fresh` (0/1) of the
    argmax armed zone at t-1 — "the part recency cannot explain" is
    now true of the variable set, not aspirational; (b) the claim
    sub-gate (D20) applies to THREE recency features at |SMD| <= 0.05:
    `since_near`, `zone_since_touch`, and `zone_fresh` share, all under
    the same fitted propensity weights. A cell failing any is
    RECENCY-UNSEPARATED.

D26. THRESHOLD PROVENANCE, STATED PLAINLY (R02-G-3). The 0.05 recency
    sub-gate was fixed AFTER the blind feasibility numbers existed —
    it is set at half the general balance gate, and it is retained
    because the asymmetry is one-directional: it can only withhold a
    claim, never manufacture one. The 0.90 attenuation guard is INERT
    on current data (max R-squared 0.545) and is kept as a declared
    guard that does not bind. Neither threshold may move after an
    outcome is seen.

D27. WINNER ELIGIBILITY RESTORED (R02-G-4). The doubled-bar principle
    returns in the new frame: a generator stamped RECENCY-DOMINATED or
    RECENCY-UNSEPARATED may be carried forward on the primary, but may
    be declared winner only if it beats the best FULLY-CONFIRMED
    generator by >= +5.0pp. Same reasoning as D7 — that is the price
    of carrying an object whose mechanism we cannot identify into the
    next round's family layer. If NO fully-confirmed generator exists,
    the +5.0pp benchmark is undefined and no winner may be declared
    from the primary alone — estimates are reported stamped, and the
    scoring-layer verdict rests on the residual confirmatory's
    evaluable-and-separated cells.

D28. MONOTONICITY DROPPED; DOSE-RESPONSE MADE DESCRIPTIVE (R02-G-5).
    The monotone gate `D_bot <= D_mid <= D_top` was designed for the
    three-group exact-strata comparison; under the weighted
    top-vs-bottom contrast the mid tercile has no defined weight, and
    inventing one post-hoc would be a degree of freedom. The gate is
    removed. Replaced by a pre-declared descriptive view: the weighted
    arm mean of the MID tercile (weights w=1 like arm A, its own
    propensity vs bottom for reporting) reported beside top and
    bottom, never gating.

D29. REMAINING DEGREES OF FREEDOM CLOSED (R02-G-6). (a) The residual
    confirmatory's bootstrap REFITS the residual OLS, recomputes
    tercile bounds, rebuilds arms, and refits the propensity inside
    every replicate (`arrival_estimate.bootstrap_resid`) — nothing
    fitted survives across replicates. (b) E2 arm A (y=1) is fixed as
    the ALPHABETICALLY-FIRST generator's arm; sign convention only.
    (c) E2->E1 downgrade mechanics, one sentence: if the E1-winning
    generator g belongs to an evaluable E2 pair whose BH-flagged
    estimate is significant and sign-opposed to g's primary direction
    (arrivals marked by the OTHER generator do better), g's claim
    carries the stamp E2-CONTRADICTED — reported alongside, never
    erased, and E2 can never create or promote a claim. (d) "every
    symbol-cell contributing to the claim" means exactly the cells
    whose D_sym enters the pooled D — a cell that fails the balance
    gate contributes no D_sym and is outside the claim's scope by
    construction. (e) Verdict strings are single sentences, verbatim:
    "RECENCY-UNSEPARATED" = the cell passes the general gate but a
    recency feature misses 0.05; "RECENCY-DOMINATED" = primary passes,
    R-squared < 0.90, and the residual contrast fails sign/half-
    magnitude; "RESIDUAL UNINFORMATIVE" = R-squared >= 0.90, no usable
    residual signal to test; "E2-CONTRADICTED" as in (c); and
    "THIN-RESIDUAL" per D31.

D30. E1 INVERSION — THE RESIDUAL IS THE CLAIM-BEARING ESTIMAND
    (R02-H §1–§2). Measured: the raw top-vs-bottom zone_S
    contrast fails the zone-recency sub-gate in ALL 24 cells
    (zone_fresh |SMD| 0.64-1.13; zone_since_touch 0.32-48.98) —
    FINDING_2. Therefore: the raw-strength contrast is retained as
    the recency-contaminated view it is — reported, descriptive,
    NEVER claim-bearing. E1's claim-bearing estimand is the
    RESIDUAL-strength contrast (D21), restricted to cells whose
    residual arms pass BOTH the general balance gate AND the
    zone-recency sub-gate: 6 cells — sd_base EURUSD+GBPUSD,
    fractal_h1 AUDUSD+USDJPY, line1_cluster GBPUSD, ref_levels
    USDJPY. The E1 multiplicity family is redefined accordingly:
    evaluable residual cells x {bounce, continuation}. D27 stands
    unchanged.

D31. THIN-RESIDUAL FLAG (R02-H §2). ref_levels residual cells sit
    at R-squared 0.888-0.898 — under the 0.90 attenuation guard
    (D23) but within 0.012 of it. They are reported with the stamp
    THIN-RESIDUAL: the confirmatory is technically evaluable but the
    residual retains barely a tenth of the score's variance; any null
    or pass there is quoted with that caveat attached, never silently.

D32. E3 — RECENCY TESTED HEAD-ON (R02-H §3). Every measurement
    this round points the same way: recency is the active ingredient
    hiding inside "strength". So it is tested directly. Within
    armed-overlap treated events of a (symbol, generator) cell:
    arm A (y=1, RECENT) = bottom tercile of `zone_since_touch`;
    arm B (STALE) = top tercile; middle tercile descriptive only.
    Propensity and balance on E3_FEATURES = {approach_atr,
    anchor_dist, log_atr, sin_hour, cos_hour, pos_r5, side} —
    NO recency variable appears (they are the treatment, not
    controls). Same estimator verbatim (IRLS logit, ATT weights,
    trim [0.05,0.95], winsorize 99th, day-cluster bootstrap B=10,000
    seed 20260920 refitting tercile bounds AND propensity inside
    every replicate — `arrival_estimate.bootstrap_e3`).
    Degenerate bounds (q33 >= q67 — e.g. all zones capped at
    SINCE_CAP) make the cell NON-EVALUABLE, reported as such.
    Balance gate |SMD| <= 0.10 on the 7 features is the evaluability
    gate, measured blind before any outcome. E3 is its own
    pre-declared BH family: evaluable generators x {bounce,
    continuation}, alongside E1 and E2. If E3 fails balance the
    round reports three honest non-identifiabilities and stops.

D33. E3 COVARIATE SET CORRECTED (R02-J §1). `since_near` and
    `zone_touches` JOIN E3_FEATURES (now 9): measured raw arm SMD
    0.13-0.61 and 0.34-1.36 respectively, and neither is the zone's
    retest recency — `since_near` is band-level proximity (price
    loitering near the location without touching the zone) and
    `zone_touches` is validation COUNT, not RECENCY. Both are
    confounders of the recency contrast and are controlled.
    `zone_since_touch` and `zone_fresh` remain OUT — they ARE the
    treatment.

D34. `zone_S` DELIBERATELY EXCLUDED FROM E3 — Lead decision, reason
    recorded so nobody silently "fixes" it (R02-J §2): the arms
    differ on zone_S (measured SMD 0.52-4.32) but `s_rec` is
    literally a component of the strength score, so `zone_S` is a
    CONSEQUENCE of the treatment, not a cause of the outcome.
    Conditioning on it would strip the very effect E3 measures and
    could open a collider path. Its SMD is reported beside every E3
    result as a transparency diagnostic (`zone_s_smd_diag`); it
    enters neither model nor gate. A future objection must argue
    the causal direction, not the imbalance size. REVIEWER PASS-4
    CONCEDED this point on the merits (T -> S descendant; exclusion
    correct) — recorded. Residual caveat the reviewer raised and
    the Lead accepts: zone_S's NON-recency components (zone age,
    density) are not treatment descendants and stay uncontrolled —
    exactly why D36's claim sentence is a bundled contrast.

D35. STALE-ARM NEVER-TOUCHED STAMP (R02-J §3). Threshold fixed
    blind: if the stale arm's share at SINCE_CAP (`cap_share_stale`)
    exceeds 0.50, the cell is stamped `STALE≈NEVER-TOUCHED`, its
    estimand reads "ever-validated vs never-validated" rather than
    "recent vs stale", and it is NEVER pooled into an E3 recency
    claim. Measured: ref_levels stale arms are ~100% capped
    (cap_s ≈ 1.00) on all four symbols — stamped. No other
    generator's stale arm exceeds the threshold.

D36. E3 CLAIM LANGUAGE IS A BUNDLED CONTRAST (R02-J §4). With D33
    applied the arms still differ in recency AND in
    strength-as-a-consequence (D34). The claim sentence is therefore
    exactly: "arrivals at recently-tested levels resolve differently
    from arrivals at long-untested ones" — NOT "recency is the
    causal ingredient". Arm SMD diagnostics (including
    `zone_s_smd_diag` and `cap_share_stale`) are reported beside
    every E3 result.

D37. RULE PINNING (R02-J §5). (a) The ">= 3/4 symbols"
    consistency rule is fixed as: ">= 3/4, ROUNDED UP, of
    CONTRIBUTING symbol-cells"; a generator with fewer than 3
    contributing cells is declared INELIGIBLE for the claim
    (applies identically to E1-residual and E3). (b) The
    winner rule reads `D_resid` for E1 — the claim-bearing
    estimand per D30, not the raw top-vs-bottom D. (c) E3 ENTERS
    winner eligibility: an E3-supported candidate is subject to the
    same +5.0pp-over-best-FULLY-CONFIRMED bar as any
    recency-proxy-flagged candidate (D27 logic) — its mechanism
    is named (recency) but bundled (D36), so it is not a free win.
    (d) ">= 1,000 resolved events per arm" is POOLED across the
    contributing symbol-cells, per generator.

D38. E1 CLAIM LANGUAGE LIMIT (R02-J §6). A positive residual
    result licenses exactly: "the component of the score orthogonal
    to recency and geometry ranks outcomes" — nothing more. The
    sentence is pinned verbatim; no stronger reading (e.g. "the
    score measures structure") may be attached.

D39. B1 CLOSED — MULTIPLICITY MACHINERY PINNED AND IMPLEMENTED
    (R02-K §1). (a) p-value recipe, one sentence, identical for
    every experiment: one-sided bootstrap `p = (1 + #{D_b <= 0}) /
    (B + 1)` over the RETAINED replicate array — every
    `bootstrap_*` in `arrival_estimate.py` returns
    {lo, hi, p, n_boot, boots}; nothing is discarded. (b) Family
    unit, consistent across E1/E2/E3: the claim unit is the
    GENERATOR (pair for E2) x ENDPOINT; per-symbol cells are that
    unit's evidence, not separate hypotheses; BH-FDR q <= 0.10
    within each family over those units. (c) The generator-level
    statistic is the sample-size-weighted mean of its per-symbol
    cell D's (`w_c` = the cell's observed contributing-event count),
    and `arrival_estimate.bootstrap_pooled` resamples DAY clusters
    independently within each contributing cell, recomputes each
    cell's D through the full refit chain (resid: OLS+terciles+
    propensity; e3: terciles+propensity; pair: propensity), and
    recomputes the weighted mean in every replicate — nothing
    fitted survives across replicates.

D40. B2 CLOSED — CROSS-EXPERIMENT WINNER RULE (R02-K §2).
    Candidates rank by their OWN experiment's claim statistic, named
    explicitly: E1 by `D_resid`, E2 by the pair statistic `D_{g,h}`,
    E3 by the recency statistic `D_recency`. FULLY-CONFIRMED is
    defined: a candidate passes its own experiment's gate AND
    carries none of {RECENCY-UNSEPARATED, RECENCY-DOMINATED,
    STALE≈NEVER-TOUCHED, THIN-RESIDUAL}. **E3 candidates are NOT
    recency proxies** — recency is E3's declared treatment, not a
    hidden substitute for something else — so an unflagged E3
    pass is FULLY-CONFIRMED and can serve as the +5.0pp benchmark.
    That sentence is the distinction the +5.0pp bar turns on.

D41. REVIEWER DECLARES ACCEPTED (R02-K pass-4 D1-D5). (a) THE BIG
    DECLARE — stated at the top of this document, see §1:
    under D37(a) no E1 generator reaches 3 contributing cells, so
    E1 cannot carry a claim this round; the round's single claim
    path is E3 on `line1_cluster`. (b) D37(a)'s "minimum 2 cells"
    clause deleted as dead text; ">= 4/6 DESIGN years" reads
    "within contributing cells". (c) fractal_h1 GBPUSD E3 passes at
    0.100 — knife-edge, deterministic, noted as MARGINAL.
    (d) `since_near` in E3_FEATURES is plausibly part-descendant of
    the treatment; controlling it is the CONSERVATIVE choice (it can
    only shrink the measured effect) — stated once, here.
    (e) The saturation guard (kept arms < 50 post-trim ⇒ fail)
    applies to all three experiments via shared `balance_report` —
    echoed in §6.

## 1. Question, estimand, falsifier

**HEADLINE DECLARE (R02-K §3, D41a): E1 cannot carry a claim this
round** — under the pinned D37(a) eligibility rule no generator
reaches 3 contributing residual cells (sd_base 2, fractal_h1 2,
line1_cluster 1, ref_levels 1). E1's raw AND residual contrasts are
descriptive-only. The round's single claim path is **E3 on
`line1_cluster`** (4 contributing cells; fractal_h1 GBPUSD is a
second E3 cell but its generator is ineligible with 1 cell). Also
declared: `zone_S`'s non-recency components (zone age, density)
remain uncontrolled — which is exactly why the E3 claim sentence
is a bundled contrast (D36), not a causal isolation of recency. A
round with one honest claim path outranks three dressed-up ones.

Question (post-pivot, R02-D): the binary "marked vs unmarked" question
is answered by FINDING_1 — *non-identifiable by construction*. What
remains identifiable, and what the trading system actually needs:

- **E1 (primary):** when price arrives at an armed zone of generator
  g, does the zone's STRENGTH rank carry information — do top-tercile
  zones behave differently from bottom-tercile zones?
- **E2 (secondary):** at places marked by one generator but not
  another, does the DRAWING METHOD carry information beyond the bare
  fact that price has been there?
- **E3 (R02-H):** among armed zones, does RECENCY itself carry
  information — do arrivals at recently-touched zones behave
  differently from arrivals at long-untouched ones?

The logic of the round, stated once: we could not test "does a level
matter" (FINDING_1 — positivity fails by construction), we could
not separate "strong" from "recent" (FINDING_2 — the strength score
is a recency proxy on this data), so E3 tests the thing that is left
and that we can actually measure.

Estimand (one sentence each):
- E1: `D_g = P(bounce | armed-arrival at a top-tercile zone_S band) -
  P(bounce | armed-arrival at a bottom-tercile zone_S band)`,
  propensity-weighted ATT per (generator, symbol) and pooled.
- E2: `D_{g,h} = P(bounce | arrival marked by g, not h) -
  P(bounce | arrival marked by h, not g)`, propensity-weighted ATT per
  (pair, symbol) and pooled.
- E3: `D_g = P(bounce | armed-arrival at a RECENTLY-touched zone) -
  P(bounce | armed-arrival at a LONG-untouched zone)` — recency
  terciles of `zone_since_touch`, propensity-weighted ATT per
  (generator, symbol) and pooled. Arm A = recent.

Falsifier: if strength scores carry no information, D ~ 0 for every
generator-endpoint pair in E1; if drawing method is irrelevant given
"a place price has been", D ~ 0 for every E2 pair.

Failure language (exact): **a FAIL means no measurable difference
between arrivals at high-strength and low-strength marked bands of the
same geometry.** A FAIL does not prove the scoring layer is worthless —
it proves this measurement found nothing; a significant NEGATIVE D is
"strength ADVERSE" (D13 logic, symmetric) — a finding, not a null.
The fresh-to-zone clause is dropped (D19, mechanical failure); the
raw-strength contrast is the recency-contaminated descriptive view
(D30), and the claim-bearing E1 estimand is the residual contrast in
its 6 evaluable-and-separated cells.

## 2. Data, splits, symbols, clock

Identical to R01 §2 verbatim: DESIGN split only 2016-01-01..2021-12-31;
core symbols EURUSD, GBPUSD, USDJPY, AUDUSD; M5 execution timeframe;
ATR14(H1) frozen at the event bar; seed 20260920; no fills, no PnL, no
costs; `pa_data.load_m1` (assert_allowed path) is the only data source;
`pa_clock.server_year` for year attribution; warm-up bars excluded.

## 3. Event — fresh arrival to a grid band (exact)

GRID. At the first bar of each server day (`t // 86400` rollover on
bar-open time), lay bands of width `w_p` at spacing `w_p`, edges at
`anchor + k*w_p`, covering `anchor +- 5*A(day-open bar)`;
`w_p = 0.75 * u_g * A(day-open bar)` where `u_g` = generator g's median
armed-zone width in ATR units (measured on a strided armed-snapshot
sample, step 288). Anchor = the day's open. Grid fixed for the day,
causal (day-open bar and ATR known at that bar only). Grid band count
per day reported (~40 bands/day at w=0.75).

ARRIVAL EVENT on band G at bar t (t inside the grid's day) — the frozen
R01 event rule verbatim with G in place of the zone: bar t's range
intersects G; NO bar in `[t-24, t-1]` intersects G (strict window, the
same semantics the R01 frozen prereg adopted); at least one bar in that
window has close distance `max(glo - c_j, c_j - ghi) >= 1.0 * A(t)`;
side from `c[t-1]` (-1 if `<= glo`, +1 if `>= ghi`, else reject); A(t)
valid; t not warm-up. The 24-bar lookback may cross the day boundary —
G is a fixed price interval and pre-grid intersections count as
touches, identical to R01's zone-existed-before-event semantics.

ARMS (per event, per margin; LEAD RULING R02-C1 — labels from the zone
state at `tp = t-1`, the close of the bar BEFORE the event bar, so the
measured bar never decides its own arm). For zones Z of generator g at
`tp`, `gap(Z,G) = max(glo - z_hi, z_lo - ghi, 0)`:
TREATED iff an ARMED zone overlaps G at tp (`armed_views_cached(tp)` —
the R01 parity-certified arming path, imported read-only, not copied).
CONTROL iff NO LIVE zone of g (`active_at_fast(tp)` — armed or not,
broken or intact) lies within `margin * w_p` of G at tp.
EXCLUDED-MIDDLE otherwise — counted, reported, used in the pre-declared
secondary T/X/C contrast ("armed zone / something live but not armed /
genuinely nothing"). Days with zero live zones yield CONTROL events
(min gap = inf). Each treated event also records `zone_S` = MAX
strength over armed zones overlapping G (controls: `zone_S = None`),
`cover` = max overlap width / `w_p`, and `zone_fresh` = True iff no
overlapping armed zone's band was intersected by any bar in
`[t-24,t-1]` (controls: `zone_fresh = None`).

Measured arms at the frozen spec (m = 0.5 x w_g), CORRECTED definitions
(arms at t-1, live-zone control, anchor-dist in both keys, `since_near`
co-primary) — the earlier armed-only table is superseded, see D14:

| symbol | generator | events | T | C | X | staleT | supT | supC | supT_fine | supC_fine |
|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | line1_cluster | 24474 | 15921 | 4117 | 4436 | 0.620 | 0.264 | 0.768 | 0.156 | 0.592 |
| EURUSD | fractal_h1 | 36597 | 14821 | 15506 | 6270 | 0.377 | 0.770 | 0.767 | 0.531 | 0.553 |
| EURUSD | kde_swing | 20853 | 10046 | 8133 | 2674 | 0.487 | 0.611 | 0.677 | 0.394 | 0.454 |
| EURUSD | profile_va | 19293 | 2234 | 15824 | 1235 | 0.430 | 0.831 | 0.281 | 0.617 | 0.161 |
| EURUSD | sd_base | 36171 | 5262 | 27356 | 3553 | 0.361 | 0.900 | 0.479 | 0.707 | 0.279 |
| EURUSD | ref_levels | 47555 | 12537 | 27405 | 7613 | 0.292 | 0.864 | 0.645 | 0.660 | 0.430 |
| GBPUSD | line1_cluster | 24525 | 15676 | 4272 | 4577 | 0.605 | 0.290 | 0.782 | 0.171 | 0.599 |
| GBPUSD | fractal_h1 | 36662 | 14446 | 16156 | 6060 | 0.374 | 0.791 | 0.776 | 0.559 | 0.566 |
| GBPUSD | kde_swing | 20951 | 10029 | 8269 | 2653 | 0.482 | 0.626 | 0.704 | 0.405 | 0.478 |
| GBPUSD | profile_va | 19382 | 2286 | 15781 | 1315 | 0.408 | 0.827 | 0.292 | 0.608 | 0.167 |
| GBPUSD | sd_base | 36823 | 5570 | 27516 | 3737 | 0.350 | 0.910 | 0.523 | 0.723 | 0.305 |
| GBPUSD | ref_levels | 47808 | 12458 | 27715 | 7635 | 0.292 | 0.845 | 0.615 | 0.646 | 0.416 |
| AUDUSD | line1_cluster | 26267 | 17955 | 3935 | 4377 | 0.639 | 0.244 | 0.760 | 0.129 | 0.563 |
| AUDUSD | fractal_h1 | 40538 | 16704 | 17327 | 6507 | 0.417 | 0.776 | 0.772 | 0.517 | 0.541 |
| AUDUSD | kde_swing | 22402 | 11366 | 8458 | 2578 | 0.524 | 0.574 | 0.670 | 0.353 | 0.432 |
| AUDUSD | profile_va | 22248 | 2630 | 18216 | 1402 | 0.439 | 0.834 | 0.269 | 0.593 | 0.150 |
| AUDUSD | sd_base | 41132 | 5544 | 32172 | 3416 | 0.385 | 0.907 | 0.439 | 0.708 | 0.248 |
| AUDUSD | ref_levels | 52798 | 13423 | 31326 | 8049 | 0.314 | 0.886 | 0.670 | 0.677 | 0.427 |
| USDJPY | line1_cluster | 25561 | 17286 | 3804 | 4471 | 0.620 | 0.246 | 0.741 | 0.130 | 0.544 |
| USDJPY | fractal_h1 | 38917 | 16191 | 16316 | 6410 | 0.399 | 0.756 | 0.742 | 0.496 | 0.514 |
| USDJPY | kde_swing | 21740 | 10329 | 8860 | 2551 | 0.504 | 0.581 | 0.644 | 0.351 | 0.405 |
| USDJPY | profile_va | 20690 | 2331 | 17109 | 1250 | 0.410 | 0.807 | 0.241 | 0.562 | 0.136 |
| USDJPY | sd_base | 41021 | 5650 | 31706 | 3665 | 0.368 | 0.913 | 0.457 | 0.704 | 0.255 |
| USDJPY | ref_levels | 50695 | 12898 | 30093 | 7704 | 0.287 | 0.882 | 0.635 | 0.667 | 0.417 |

Under the corrected definitions the support picture inverts: only
`sd_base` clears the 0.90 primary floor (thin — 0.9002 EURUSD), and NO
generator clears the co-primary floor (D14 declarations apply). This
table is now the EVIDENCE for FINDING_1 (non-identifiability of the
binary contrast, D15); the binary arms are not used for any estimate.

Covariate agreement (medians, m=0.5, all four symbols, corrected arms):
`dist_cp` treated 0.39-0.55 vs control 0.41-0.63 ATR — still matched
(R01's confound stays removed); `approach_atr` treated 1.50-1.60 vs
control 1.68-2.35; `since_near` treated 95-123 vs control 207-817 bars;
`anchor_dist` treated 1.24-1.57 vs control 1.87-2.48 ATR — the residual
asymmetry the stratum key now carries (D10); `pos_r5` ~0.5 both; ATR
matched by construction of the decile key.

## 3b. E1/E2 arms and measured feasibility (R02-D)

E1 ARMS (per generator g, per symbol): among TREATED events at m=0.5
(armed zone overlaps G at t-1, D9), `zone_S` = max strength over
overlapping armed zones; arm A = TOP tercile of pooled treated
`zone_S`, arm B = BOTTOM tercile; bounds pre-outcome, recorded in
FREEZE.json; middle tercile reported descriptively.

E2 ARMS (per unordered pair {g,h}, on the FINER of the two grids):
arm g = armed_g overlaps G at t-1 AND no live_h zone overlaps G;
arm h = mirror; X = both/neither/contaminated. `zone_fresh_*` recorded
per arm against its own marking zones.

Measured feasibility (propensity-weighted balance, all four symbols;
`smd` = max post-weighting |SMD| over the 8 features incl. `side`;
gate <= 0.10).

E1 — balance gate results under the 8-feature model (D24;
general gate |SMD| <= 0.10 over all 8 incl. `side`; zone-recency
sub-gate D25 in brackets = max of since_near / zone_since_touch /
zone_fresh |SMD| vs 0.05; resid = R2 / residual-arm recency gate):

| generator | EURUSD | GBPUSD | AUDUSD | USDJPY | verdict |
|---|---|---|---|---|---|
| line1_cluster | 0.065 [0.693] | 0.063 [0.640] | 0.037 [0.661] | 0.024 [0.663] | balance PASS; RECENCY-UNSEPARATED 4/4 |
| fractal_h1 | 0.026 [1.066] | 0.027 [1.094] | 0.014 [1.022] | 0.020 [1.014] | balance PASS; RECENCY-UNSEPARATED 4/4 |
| kde_swing | 0.088 [2.202] | 0.103 F | 0.069 [1.723] | 0.076 [1.830] | RECENCY-UNSEPARATED 4/4 |
| profile_va | 0.226 F | 0.189 F | 0.146 F | 0.151 F | UNDERPOWERED-BY-CONSTRUCTION (D22) |
| sd_base | 0.054 [0.972] | 0.048 [0.906] | 0.049 [0.868] | 0.061 [0.826] | balance PASS; RECENCY-UNSEPARATED 4/4 |
| ref_levels | 0.677 F | 0.631 F | 0.544 F | 0.549 F | UNDERPOWERED-BY-CONSTRUCTION (D22) |

`side` entered the model AND the gate (D24): it cost NO cell its
balance pass — post-weighting side |SMD| is <= 0.086 in every cell
(the reviewer's raw 0.14-0.32 imbalance is fully absorbed by
weighting). The consequential measurement is the zone-recency
sub-gate: EVERY primary cell fails it (zone_fresh |SMD| 0.64-1.13;
zone_since_touch 0.32-48.98 — ref_levels zones are essentially
never touched so the capped feature saturates). Top-tercile zone_S
selection is inseparable from in-window zone retesting on this data:
the F1 channel measured inside E1, exactly as review R2-F1 predicted.

Residual confirmatory after D25 (zone_last_touch + zone_fresh now in
the OLS): balance PASS 24/24 (post |SMD| <= 0.035); R2 rises to
0.36-0.90 — line1 0.36-0.38, fractal 0.46-0.48, sd_base 0.48-0.52,
kde 0.80-0.81, profile_va 0.82-0.84, ref_levels 0.888-0.898 (a hair
under the 0.90 attenuation guard — does NOT trigger, but flagged
as near-boundary). Residual-arm recency sub-gate passes in 6/24
cells: sd_base EURUSD/GBPUSD, fractal_h1 AUDUSD/USDJPY, line1 GBPUSD,
ref_levels USDJPY (whose primary is underpowered anyway). So the
adjudication path that survives is: residual contrast in the cells
where it is both balanced and recency-separated.

Fresh-restricted confirmatory (D11 clause): DROPPED per D19 —
fails its own balance gate in 23/24 cells by construction (strong
zones attract retests, so restriction starves one arm). Replaced by
the recency sub-gate (D20) and the residual-strength confirmatory
(D21), both measured blind: recency-separated cells per D20
(line1 4/4, fractal 4/4, sd_base 2/4, kde 0/4); residual contrast
balances in 24/24 cells (post |SMD| <= 0.035).

E2 — balance gate results under the 8-feature model (D24;
PASS/FAIL per pair, 15 pairs; `side` cost no previously-passing cell
its pass):

| pair | EURUSD | GBPUSD | AUDUSD | USDJPY |
|---|---|---|---|---|
| line1|fractal | 0.117 F | 0.088 P | 0.130 F | 0.113 F |
| line1|kde | 0.174 F | 0.186 F | 0.156 F | 0.184 F |
| line1|profile | 0.266 F | 0.243 F | 0.336 F | 0.409 F |
| line1|sd | 0.064 P | 0.055 P | 0.140 F | 0.103 F |
| line1|ref | 0.105 F | 0.045 P | 0.102 F | 0.144 F |
| fractal|kde | 0.030 P | 0.008 P | 0.018 P | 0.022 P |
| fractal|profile | 0.021 P | 0.028 P | 0.023 P | 0.040 P |
| fractal|sd | 0.084 P | 0.081 P | 0.094 P | 0.115 F |
| fractal|ref | 0.109 F | 0.156 F | 0.082 P | 0.107 F |
| kde|profile | 0.219 F | 0.621 F | 0.340 F | 0.258 F |
| kde|sd | 0.031 P | 0.034 P | 0.043 P | 0.060 P |
| kde|ref | 0.046 P | 0.090 P | 0.028 P | 0.033 P |
| profile|sd | 0.080 P | 0.082 P | 0.062 P | 0.086 P |
| profile|ref | 0.025 P | 0.027 P | 0.014 P | 0.013 P |
| sd|ref | 0.074 P | 0.083 P | 0.014 P | 0.023 P |

Pairs evaluable on all 4 symbols: fractal|kde, fractal|profile,
kde|sd, kde|ref, profile|sd, profile|ref, sd|ref (7 pairs). line1
pairs fail almost everywhere (its "marked by line1 but not h" arm is
too heterogeneous for the pinned feature set), kde|profile fails
everywhere (arm B ~230 events, propensity saturates). Evaluable pair
arm sizes range 1.9k-15.6k vs 2.2k-12.0k — power is not the
constraint.

E3 (R02-H, recency head-on). Arms on the same armed-overlap treated
set: RECENT (y=1) = bottom `zone_since_touch` tercile, STALE = top
tercile (s >= q67, so the SINCE_CAP mass — never/long-ago touched —
lands in stale where it belongs); middle descriptive. Propensity and
balance on E3_FEATURES = {approach_atr, anchor_dist, log_atr,
sin_hour, cos_hour, since_near, pos_r5, side, zone_touches} (D33 —
band-proximity and validation-count confounders controlled; the
zone's own retest recency IS the treatment and stays out; zone_S
stays out as a treatment consequence, D34).
Measured balance gate under the 9-feature model (D33:
since_near + zone_touches added; zone_S reported-but-excluded D34),
all cells, blind. `cap_s` = stale-arm share at SINCE_CAP (D35 stamp
threshold 0.50); `zs` = zone_S arm SMD, diagnostic only:

| generator | EURUSD | GBPUSD | AUDUSD | USDJPY | verdict |
|---|---|---|---|---|---|
| line1_cluster | 0.061 P | 0.062 P | 0.045 P | 0.059 P | evaluable 4/4 |
| fractal_h1 | 0.138 F | 0.100 P | 0.147 F | 0.115 F | evaluable 1/4 (GBP only) |
| kde_swing | 0.199 F | 0.308 F | 0.132 F | 0.134 F | underpowered; cap_s 0.63-0.76 STALE≈NEVER-TOUCHED |
| profile_va | 0.487 F | 0.344 F | 0.238 F | 0.394 F | underpowered; cap_s 0.72-0.84 STALE≈NEVER-TOUCHED |
| sd_base | 0.159 F | 0.241 F | 0.167 F | 0.166 F | underpowered (cap_s 0.00 — fails balance, not the stamp) |
| ref_levels | SAT | SAT | SAT | SAT | propensity saturates (trim 1.00/1.00); cap_s 1.00 — never-touched arm is a different experiment |

`zone_s_smd_diag` measured 0.64-4.23 (reported beside every result,
never a covariate — D34). Adding the two confounders killed the
naive E3 picture: only line1_cluster survives 4/4, fractal keeps GBP.
A saturation guard was added to `balance_report`: a cell whose kept
arms fall below 50 events post-trim can never gate-pass (a pass on
zero data is not a pass) — ref_levels E3 is non-evaluable by it.

## 4. Outcome over <= 48 M5 bars (exact)

R01 §4 verbatim with grid band G in place of the zone. Window
`j = t+1 .. t+48`; events without all 48 bars are dropped at resolution
(counted). Barrier `m = 1.0 x A(t)` frozen at the event bar. BOUNCE:
first bar whose range touches `e_near - m` (s=-1) / `e_near + m` (s=+1),
`e_near = glo` (s=-1) / `ghi` (s=+1). BREAK: first bar whose CLOSE is
`>= e_far + m` (s=-1) / `<= e_far - m` (s=+1). Adverse-first: same bar
shows both -> BREAK wins; otherwise the earlier bar wins. NONE:
neither by t+48. Proportions conditional on resolution with raw shares
reported side by side (R01 F7 carried forward — raw shares are MANDATORY
in the results table). BREAK continuation: `b_b` = break bar, `c_b` its
close, `side_b = -s`; window `b_b+1 .. b_b+48`: CONT = first touch of
`c_b + side_b * m`; RETURN = first touch of the band midpoint; same bar
-> RETURN wins. M1-path note unchanged: M5 bars are complete 5xM1
buckets; within-bar ordering is settled by adverse-first.

Implementation: `research/arrival/arrival_outcome.py` maps arrival
events onto `phys_resolve.resolve_events` (the R01 frozen resolver,
imported read-only — identical code path, not a reimplementation).
Unit-tested on synthetic data only; NEVER run on real data pre-freeze.

## 5. Strata and descriptive views

Exact strata (robustness view only post-pivot, D18): `side x
approach-distance decile x ATR decile x hour bucket (utc_min // 240,
six 4h buckets) x anchor-distance decile`, computed within each
(symbol, contrast) cell over pooled arm-A+arm-B events; common-support
set = strata with >= 1 event in each arm. Descriptives per cell (E1:
generator x symbol; E2: pair x symbol): arm counts, E1 tercile bounds,
propensity coefficient table, propensity range per arm, trimmed share
per arm, winsorized weight quantiles, effective sample size after
weights, pre/post SMD per feature (the table the balance gate reads),
per-stratum counts and `supT_exact`, median covariates per arm
(approach_atr, since_near, ATR decile, hour share, pos_r5, dist_cp,
anchor_dist, cover, zone_S), `zone_fresh` share per arm, NONE share
with CI, and for E2 the cross-marking matrix (n_a, n_b, n_x) plus
`zone_fresh_g`/`zone_fresh_h` shares.

## 6. Statistics, gate, multiplicity, winner rule

Estimator — post-pivot (D18), `arrival_estimate.py` +
`arrival_contrast.py`, quoted sentence-for-sentence: the propensity
model is an unpenalized IRLS logistic regression of the arm indicator
on the eight pinned features {approach_atr, anchor_dist, log ATR,
sin(2*pi*utc_min/1440), cos(2*pi*utc_min/1440), since_near, pos_r5,
side},
standardized inside the fit (mu/sd carried with the model), fitted per
symbol per generator for E1 (per pair for E2); arm A (y=1) is the arm
whose effect is estimated — E1: top `zone_S` tercile; E2: the pair's
first generator. Weights `w_A = 1`, `w_B = e/(1-e)`; events with e
outside [0.05, 0.95] are trimmed in BOTH arms and the trimmed share is
reported; control-side weights are winsorized at their own 99th
percentile within the cell. The outcome value per event is 1.0/0.0
conditional on resolution (BOUNCE=1, BREAK=0; CONT=1, RETURN=0;
NONE/DROPPED excluded from the proportion — raw shares reported
alongside, never hidden); the weighted arm mean is over resolved
events only. `D_sym` per (generator|pair, symbol); headline
`D = sum_sym w_sym D_sym` with `w_sym = n_A,sym / sum n_A,sym`. CI:
percentile (2.5/97.5) bootstrap clustered by server day, B = 10,000,
seed 20260920 — the propensity model is REFIT inside every replicate;
the week-cluster rerun (`cluster = bar_t // 604800`) is reported
alongside, never gated. The exact-strata ATT of D12 remains the
pre-declared robustness view (its own support is reported as
`supT_exact`, not gated). BALANCE GATE: max |SMD| <= 0.10 over all
eight features after weighting, measured BEFORE freeze; a cell that
fails it is UNDERPOWERED and produces no test (D18/R02-D §5).

Multiplicity (R02-E §5 + R02-H, pinned): BH-FDR q <= 0.10 applied
WITHIN each experiment family separately, declared as THREE families.
E1 family = evaluable RESIDUAL-strength cells x {bounce,
break-continuation} (D30 — evaluable = residual arms pass the
general balance gate AND the zone-recency sub-gate; the measured set
is sd_base EURUSD+GBPUSD, fractal_h1 AUDUSD+USDJPY, line1_cluster
GBPUSD, ref_levels USDJPY-THIN). The raw-strength contrast is outside
the family — descriptive only, never claim-bearing (D30). E2 family
= evaluable pairs x {bounce, break-continuation}, BH within the E2
family for flagging only — E2 can support or downgrade an E1
claim, never create the round's primary claim. E3 family (D32) =
evaluable generators x {bounce, break-continuation} — evaluable =
the E3 balance gate passes in that symbol-cell. The stall endpoint
(NONE share) is descriptive with CIs, never gated. The dropped fresh
restriction (D19) appears nowhere in the families.

Gates for an E1 "residual strength ranks carry information" claim
(D30 — the claim-bearing estimand is now the residual contrast;
all must hold): `D_resid >= +5.0pp` (top minus bottom residual
tercile); CI lower bound > 0; the weighted MID-tercile arm mean
reported descriptively beside top and bottom (dose-response view,
never gating — D28); D_resid > 0 in >= 3/4 (rounded up) of
CONTRIBUTING symbol-cells and >= 4/6 DESIGN years within
contributing cells; a generator with fewer than 3 contributing
cells is INELIGIBLE (D37a);
BH q <= 0.10 within the E1 family; >= 1,000 resolved events per arm
pooled across the contributing symbol-cells (D37d); general balance
gate (|SMD| <= 0.10) AND zone-recency sub-gate (since_near,
zone_since_touch, zone_fresh share, all <= 0.05) passed on the
residual arms in every symbol-cell contributing to the claim
(D20/D25/D30). The RAW-strength D is reported beside every residual
result as the recency-contaminated view, stamped
RECENCY-UNSEPARATED, and can never carry the claim. THIN-RESIDUAL
cells (D31, ref_levels) report with the caveat attached. A null
residual result carries evidential weight ONLY when the residual
retains meaningful variance (R-squared < 0.90); R-squared >= 0.90 ⇒
"RESIDUAL UNINFORMATIVE — no usable residual signal to test", the
null is uninformative and may never be quoted as evidence that the
score is a recency proxy. Adverse direction (D13): CI upper < 0 ⇒
"strength ADVERSE" — a finding, reported symmetrically.

Gates for an E3 claim (D32/D33/D36; all must hold): `D >= +5.0pp`
(recent minus stale); CI lower bound > 0; D > 0 in >= 3/4 (rounded
up) of CONTRIBUTING symbol-cells and >= 4/6 DESIGN years within
contributing cells (a generator with < 3 contributing cells is
INELIGIBLE, D37a);
BH q <= 0.10 within the E3 family; >= 1,000 resolved events per arm
pooled across contributing cells (D37d); balance gate (|SMD| <= 0.10
on E3_FEATURES, 9 features incl. since_near + zone_touches) passed
at freeze; `cap_share_stale` <= 0.50 else the cell is stamped
`STALE≈NEVER-TOUCHED` and excluded from any pooled recency claim
(D35). NO recency sub-gate applies — recency is the treatment;
arms differ on it by construction. Claim language is the bundled
contrast (D36): "arrivals at recently-tested levels resolve
differently from arrivals at long-untested ones". Adverse direction
symmetric (D13): CI upper < 0 ⇒ "recency ADVERSE" — arrivals at
recently-touched zones do WORSE — a finding, reported as such.

Winner rule (D6 under R02-K, cross-experiment per D40): rank every
candidate by ITS OWN experiment's claim statistic — E1 by
`D_resid`, E2 by `D_{g,h}`, E3 by `D_recency`. A candidate is
FULLY-CONFIRMED iff it passes its own experiment's gate AND carries
none of {RECENCY-UNSEPARATED, RECENCY-DOMINATED,
STALE≈NEVER-TOUCHED, THIN-RESIDUAL}; an unflagged E3 pass IS
fully-confirmed (recency is E3's declared treatment, not a hidden
proxy — D40) and can set the +5.0pp benchmark. The leader is a
clear winner only if it beats the runner-up by >= +2.0pp, else
declare the TIE SET ordered by tie-breaks (fewer parameters, then
fewer armed zones per bar). A generator that cannot pass its
experiment's gate cannot win; a flagged candidate may be declared
winner only if it beats the best FULLY-CONFIRMED candidate by
>= +5.0pp (D27); if no fully-confirmed candidate exists, no winner
is declared from estimates alone. Saturation guard (D41e): a cell
whose kept arms fall below 50 post-trim never gate-passes, in all
three experiments.

## 7. Ledger, freeze bundle, run plan

Freeze bundle (narrowed to outcome-path modules only, per R02-B):
`research/arrival/arrival_common.py`, `arrival_contrast.py`,
`arrival_run.py`, `arrival_freeze.py`, `arrival_feas2.py`,
`arrival_outcome.py`,
`arrival_estimate.py` (written, synthetic-tested, hashed at freeze),
`tests/test_arrival.py`, plus read-only imports on the outcome path:
`research/physics/phys_resolve.py`, `phys_source.py`, `phys_common.py`,
`struct/zones/registry.py` + the six generators, `lib/pa_data.py`,
`pa_clock.py`, `pa_sealed.py`, `pa_ledger.py`, `pa_eval.py`,
`pa_metrics.py`. FREEZE_ADDENDUM policy (carried from the Lead's R01
ruling): any post-freeze edit inside the bundle gets an addendum
recording old hash, new hash, reason, authorizing order — no silent
edits. Run plan: per symbol, `arrival_freeze`-equivalent extraction
with outcome join AFTER freeze, one process, OMP_NUM_THREADS=4,
BelowNormal; results into `rounds/R02/RESULTS.md`; ledger append
PHYSICS entries per generator.

## 8. What this prereg deliberately does not do

- No fills, PnL, costs, or tradability claims — physics only.
- No distance-restricted controls (measured unnecessary, D2).
- No re-run of R01; R01's frozen answer stands with its changed
  interpretation.
- No claim about zones outside the six frozen generators.
- The binary marked-vs-unmarked contrast is retired (FINDING_1): it
  produces no estimate, and propensity weighting is NOT used to rescue
  it (D15/D18).
- The dropped fresh restriction (D19) appears nowhere in the
  families. The raw-strength E1 contrast is descriptive only
  (RECENCY-UNSEPARATED 24/24, FINDING_2, D30); the claim-bearing E1
  estimand is the residual-strength contrast, itself gated by the
  recency sub-gate on its own arms (D20/D25/D30). ref_levels residual
  cells are stamped THIN-RESIDUAL (D31). E3 carries no recency
  sub-gate — recency is the treatment there (D32).
