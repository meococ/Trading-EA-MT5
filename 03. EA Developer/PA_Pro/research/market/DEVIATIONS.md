# DR-MARKET — DEVIATIONS

Append-only. Every departure from the mandate / preregistered plan is logged
here with reason and impact.

## D1 — M0 verdict logic (recorded 2026-09-21, same session as M0)
- **Plan:** flag any NFP month whose max-range M1 bar is not at the expected
  release minute; exclude pending Lead ruling.
- **Observed:** 40 symbol-months had a max-range bar at another minute; all
  deviations sat at 16:0x–16:4x or 13:4x–14:3x server, i.e. 10:00 ET releases
  (ISM/University of Michigan) or London-fix effects that were simply bigger
  than that day's NFP.
- **Change:** verdict criterion switched to *spike-presence*: a month counts
  as clock-confirmed iff a bar exists at the expected NFP minute AND its
  range ≥ 3× that day's median bar range. Result: 262/288 confirmed; the 26
  remainder had a bar at the right slot but a quiet NFP (no spike) — a
  property of the release, not the clock. No month was excluded.
- **Impact:** none on downstream data use; the clock was proven
  (server = UTC+2/+3 EU DST), which is what M0 exists to establish.
  Logged for the reviewer; Lead may overrule.

## D2 — CLOCK_AUDIT_DESIGN.md header timestamp
- `Generated:` line was written empty in the first version.  Corrected on
  regeneration; historical evidence untouched.

## D3 — M3 placebo seeds made process-deterministic
- First extraction draft used Python `hash(sym)` (per-process randomized) to
  seed PRAND grids.  Replaced by `crc32(sym)` before any saved output, so all
  artifacts derive from stable seeds.  No results were produced with the
  randomized seeds.

## D4 — M3 resolution starts at the touch minute, not the touch-bar open
- The plan says outcomes are measured after the touch.  First implementation
  scanned M1 from the open of the touching M5 bar, which admits pre-touch
  movement inside that bar.  Now: the first M1 bar intersecting the zone is
  located, and the outcome path starts at the next M1 bar.
- Same fix: `overshoot_x1` now freezes at the x1 resolution bar (was:
  accumulated until *both* barriers hit), and `retest_12/48` are `False`
  (not missing) when a break never retests within the horizon.
- An EURUSD npz was written once under the old convention and was
  overwritten by the corrected run before any analysis consumed it.

## D5 — Grid level columns are anchored near the daily open (scope limit)
- `grid_columns` builds RND/PRND20/PRND10/PRAND levels inside
  day_open ± 3.5·ABR (≈±9 pips EURUSD).  Therefore the RND and
  cascade (XRND) results condition on **round levels near the day open**,
  not all 00/50 levels; days whose open is far from a round contribute
  no RND column at all.  The placebo arms share the identical anchoring,
  so the contrasts remain valid for that subpopulation; the absolute
  round-level coverage is incomplete.
- Recorded 2026-09-21 during self-audit while M8 ran.  Noted in
  LEVELS.md/MARKET_MECHANICS.md as a scope limitation.

---

# Post-M8 remediation block (reviewer findings → corrections → rerun)

The M8 independent review (`REVIEW.md`) found that the first execution
deviated from `STUDY_PLAN.md` in ~15 places, two of which were causal
(lookahead) and two of which voided/weakened headline results.  All items
below were fixed in code, extraction was re-run, and the reports were
rewritten.  Ledger rows T000367–T000379 describe the **pre-review**
numbers; corrected rows supersede them.

## D6 — ASIA level columns had a server-day/CET wraparound lookahead
- **Defect:** `asia_columns` keyed Asia levels by server day.  Bars with
  CET ≥ 23:00 (server day+1 already past midnight CET) were scored
  against the Asia window of the *current* CET date, i.e. levels built
  from bars that had not all happened yet.  ~9–10% of ASIA events were
  contaminated (reviewer measured on EURUSD).
- **Fix:** Asia columns are computed from the completed 00:00–08:00 CET
  window and armed only strictly after it closes: same server day for
  CET minutes in (480, 1380), next server day for CET ≥ 1380 (those bars
  belong to the prior CET date).
- **Impact:** causal defect; all ASIA results re-derived.

## D7 — M3 freshness counted intersections with the column zone, not the event zone
- **Defect:** the "no prior bar in [t−24,t) intersects the zone" check
  used each candidate bar's *current column* zone.  When a column's
  zone moved between visits, earlier touches of the same price area were
  missed → events admitted that the declared rule forbids.
- **Fix:** per-candidate check against the event's own `[zlo,zhi]`,
  bounded below by the level's birth bar; applied identically to
  `detect_touches` and `detect_crosses`.
- **Impact:** event sets changed; all touch/cross contrasts re-derived.

## D8 — M3 cross/retest/forward-index defects
- **Defects:** (a) the cross trigger did not consistently require a close
  beyond the *outer* zone edge; (b) cascade forward values had an
  off-by-one (value at t+H must be bar t+H); (c) retest lag was measured
  from the touch candidate rather than the actual break bar;
  (d) role-reversal lacked the declared post-retest path condition.
- **Fix:** crosses trigger on close ≥ zhi / ≤ zlo; fwd uses t+H;
  retest lag anchored at the break bar; role-reversal uses the declared
  post-retest path.
- **Impact:** F-B and F-C event tables rebuilt.

## D9 — M4 detector was not the declared §5 detector
- **Defect:** shipped code used a longest-trailing-window scan with fixed
  6–34 pip height limits; the plan declares a 30-bar window, height
  1.5–6 ABR, ≥2 touches per edge, interleaved edge-touch sequence,
  ≥9-bar first-to-last span, edges frozen at confirmation, expiry at
  100 bars or first close beyond an edge.
- **Fix:** detector rewritten to the declared rule; height/lifetime
  distributions (F-BX) re-derived — the old "heights cluster at 27–33 p"
  was a detector artefact and is withdrawn.
- **Impact:** box universe changed → all M4 results re-derived.

## D10 — M4 placebo was non-exchangeable (random bars); F-FB headline weakened
- **Defect:** placebo events were random bars; they did not condition on
  an actually-touched comparable edge, so the traversal-distance
  distribution was not matched.  The F-FB "+13.8pt at 5 pips" headline is
  therefore unreliable and is treated as unverified until the corrected
  run.
- **Fix:** placebo = the declared §5 design: per-day P-RAND prices (same
  generator as M3's pool) conditioned on ≥2 zone touches in the trailing
  30 bars → "fake edge"; poke = wick beyond + close back, break = first
  close ≥ tol beyond with the previous close not already beyond; one
  break per direction per edge; the traversal target is the nearest
  same-day pool level on the opposite side (self-contained fake height).
  F-FB strata add the height tercile as declared.
  (An intermediate Donchian fake-edge draft was written and replaced by
  this declared design before any results were produced.)
- **Impact:** F-FB and F-BO contrasts re-derived against an exchangeable
  control.

## D11 — M5 placebo lines were non-exchangeable; F-TL −13.7pt voided
- **Defect:** placebo "lines" were random bars; ~70% never intersected the
  synthetic line, so the placebo event stream was not generated by the
  same machinery and the −13.7pt third-touch contrast is **void**.
- **Fix:** placebo = two price-shifted copies per real line (same anchor
  times, same slope, shift ±δ·ABR[t2], δ~U[1.5,4]) scanned by the
  identical touch machinery.
- **Impact:** F-TL re-derived; the pre-review sign must not be quoted.

## D12 — M5 line geometry inconsistent between detection and resolution
- **Defect:** touch detection evaluated the line in M5 bar-index units
  while resolution extrapolated in M1 *timestamp* units; feed gaps
  (weekends) produced large geometric discrepancies.
- **Fix:** detection, death and resolution all evaluate the line at M5
  bar index.
- **Impact:** all M5 touch/break outcomes re-derived.

## D13 — M5 freshness rule weaker than declared
- **Defect:** freshness required 24 bars since the last *accepted event*,
  not since the last *zone intersection* — later touches could be
  declared "fresh" while price was still sitting on the line.
- **Fix:** every line-zone intersection updates the freshness clock;
  only a touch after >24 bars without any intersection is an event.
- **Impact:** touch event set re-derived.

## D14 — M6 divergences: θ scale, warmup, sessions, gaps, missing tests
- **Defects:** (a) trend legs used θ=2.0·ABR labelled as θ₂=2.5;
  (b) warmup bars could generate pivots/events; (c) session stats were
  not split at feed gaps >300 s; (d) session edges did not match the
  declared CET 480/870/1080; (e) VR horizons {24,48} and EMA lengths
  {15,35} were missing; (f) the declared 12-test F-M family (4 lag-1
  session tests, 4 VR(12) tests, 4 EMA comparisons) was not assembled.
- **Fix:** θ₁=1.0/θ₂=2.5; warmup excluded; gap-segmented returns;
  declared session edges; full VR/EMA grids; F-M = 12 tests under one
  BH-FDR.
- **Impact:** all M6 numbers re-derived; the "EMA25 not special" claim is
  re-tested on the declared grid.

## D15 — Analyzer strata pooled quantile edges across symbols
- **Defect:** ABR-tercile and approach-decile edges were computed on the
  pooled all-symbol sample, collapsing the ABR strata for USDJPY
  (different price/ABR scale) and blurring matching.
- **Fix:** edges computed per symbol on that symbol's pooled
  real+placebo events, per the plan's strata definition.
- **Impact:** all contrast families re-computed.

## D16 — Analyzer family structure did not match the plan
- **Defects:** (a) F-A used ad-hoc age bins and per-set tests instead of
  the 5 declared bins on pooled S1+S2; (b) F-T ran per-set tests instead
  of the 6 declared pooled tests (3 touch classes × x∈{1,2});
  (c) F-B ran 5 per-set pairs instead of the 4 declared pooled tests
  (retest@12/48, role-reversal@12/48); (d) F-C included an undeclared
  h48 formal test — plan reserves h∈{3,12} for formal and allows h48
  descriptive only; (e) F-R lacked the declared secondary estimand
  (resolved-only bounce probability) — 24 declared tests total.
- **Fix:** `mk_m3_analyze.py` rebuilt to the declared families; h48 is
  reported as descriptive only.
- **Impact:** family counts now conform; q-values re-computed.

## D17 — M4 event semantics for moving fake edges
- **Defect (self-found during remediation):** first Donchian placebo
  draft merged consecutive pokes into streaks against a frozen edge,
  but the fake edge moves every bar → the streak was measured against a
  stale level.
- **Fix:** placebo pokes are single-bar events with the same freshness
  filter; depth is measured against that bar's edge.  (Superseded anyway
  by the declared P-RAND design — see D10.)
- **Impact:** internal only; fixed before any output was consumed.

## D18 — Event-table hashes superseded
- The npz files regenerated by the corrected extraction carry new
  SHA256 hashes (printed at extraction, recorded in the ledger rows).
  Pre-review hashes are archived implicitly by the old ledger rows.

## D19 — M5 lines anchored on θ1 instead of θ2 pivots (self-found)
- **Defect:** `build_lines` used `abr*1.0` pivots; plan §6 declares
  "two consecutive confirmed θ₂ pivots" (2.5·ABR).
- **Fix:** `dc_pivots(..., abr*2.5)`; docstring updated.
- **Impact:** line universe shrinks to the declared scale; all M5
  results re-derived.

## D20 — F-O ran contrasts although declared descriptive-only
- **Defect:** the analyzer computed placebo contrasts + BH for
  overshoot; plan §4 declares F-O descriptive (quantiles only).
- **Fix:** contrasts removed; report shows quantiles only.
- **Impact:** none on other families; report shape corrected.

## D21 — M6 VR missing the 1/k factor; segment-boundary returns
- **Defect (self-found during remediation):** `vr_from` returned
  Var(k-sum)/Var(r) — i.e. k·VR(k) — and the first return of each
  session/gap segment spanned the boundary break.
- **Fix:** VR(k) = Var(k-sum)/(k·Var r) per the plan's definition;
  the first return of every segment is dropped.
- **Impact:** all VR numbers (incl. the VR(12)-vs-1 tests) re-derived.

## D22 — Declared M4 fake-edge placebo is underpowered and
##     traversal-matched strata barely overlap (design limitation)
- **Observed on the corrected run:** the declared P-RAND fake edges yield
  only ~48 breaks and ~60–110 pokes per symbol (the ±3.5·ABR day-open
  pool is narrow, and the ≥2-touches-in-30 conditioning is restrictive).
  The fake "opposite edge" (nearest same-day pool level) sits at median
  ~0.2·ABR vs real box heights ~5·ABR, so the height-tercile stratum
  almost never overlaps — F-FB's D is identified on a thin, atypical
  subpopulation and its sign is dominated by the mechanical distance
  gap (placebo pokes trivially "reach the opposite edge").
- **Disposition:** F-BO race24 and F-FB are reported with n_real/n_plac
  columns and an explicit "not identified" warning in BOXES.md.  The
  descriptive rates (P(reach opposite edge ≤24b) ≈ 0.21 real, ≈0.96
  placebo) are honest; the contrast D is not interpretable as a level
  effect.  A better placebo needs a declared redesign — flagged for the
  Lead rather than silently substituted (again).

## D23 — min_cell eligibility applied to weighted bootstrap counts
- **Defect:** `contrast_boot` applied the ≥5-events-per-arm stratum
  filter to the *weighted* day-multiplicity counts inside each bootstrap
  replicate, so a stratum ineligible on pooled support could qualify in
  replicates — yielding `D=nan` beside a finite CI/p.
- **Fix:** eligibility is computed once from unweighted pooled stratum
  sums and held fixed across the point estimate and all replicates.
- **Impact:** cosmetic consistency — previously a handful of thin-strata
  contrasts (F-FB bins, F-A high-age bins) showed nan D with a finite
  CI; they now show nan coherently.  Point estimates in well-supported
  strata are unchanged.

## D24 — M4b placebo redesign declared via addendum (plan-level change)
- Per Ruling 2 item 4 and the remediation protocol ("plan fix logged
  before the re-run"): `STUDY_PLAN_ADDENDUM_M4B.md` declares the P-SHIFT
  placebo (OUT arm: fake edges g·ABR beyond real edges; IN arm: interior
  level lo+u·h), hashed to the ledger as `market_study_prereg` T000390
  **before** any F-Xb statistic was computed (iterations T000388/389
  were amended pre-compute for degenerate semantics).
- The first box-copy implementation produced a degenerate event stream
  (price outside the copy → instant break, 0 pokes); this was caught by
  inspection, the design re-declared as shifted edges, and only then
  computed.  The M4 main results (declared P-RAND placebo) remain
  reported as-is; F-Xb is a parallel identified arm.


## D25 — M3 resolver: side=+1 barriers pointed inward (REVIEW_2 F1)
- **Defect:** for `side=+1` (approach from above = support touch),
  `resolve_event` set break = `zlo + x·A` and bounce = `zhi − x·A`, both
  inside/on the wrong side of the zone, so both fired on the first M1
  bar and the tie-break defaulted to BOUNCE.  Fingerprint: raw
  P(bounce x1) ≈ 0.98 for side +1 vs ≈ 0.64 for side −1, identical on
  real and placebo sets.
- **Fix:** support touch now uses outward barriers — break =
  `zlo − x·A` (down through the zone), bounce = `zhi + x·A` (reversal
  up).  Same fix applied to the unused legacy helper
  `resolve_touch_outcome` in mk_common.py so it cannot propagate.
- **Impact:** every M3 outcome-derived result (F-R, F-A, F-T, F-B, F-C,
  F-O overshoot/retreat) recomputed from a full re-extract; ledger rows
  T000380–T000384 superseded.

## D26 — Bootstrap emptied-arm cells were zero-filled (REVIEW_2 F2)
- **Defect:** after D23, `contrast_boot` still treated a stratum whose
  placebo (or real) arm resampled to zero as a valid zero-valued cell,
  biasing the bootstrap distribution (fingerprint: point D below its
  own CI on F-T x1_t3p).
- **Fix:** inside `stats()`, a replicate contributes a stratum only when
  `RN_ > 0 AND PN_ > 0` in that resample, in addition to the pooled
  eligibility mask.  Point estimate unchanged (pooled support always
  positive on eligible strata).
- **Impact:** all pooled CI/p/q for M3/M4/M4b/M5 recomputed; rows
  T000380–T000387, T000391 superseded.

## D27 — M4/M4b per-symbol strata decode used wrong key factor
  (REVIEW_2 F3)
- **Defect:** M4/M4b `key_ints` encode the symbol index at coefficient
  252 (no height tercile) or 756 (with hgt), but `run_contrast` decoded
  with the M3 factors 2772/8316 → every stratum decoded to EURUSD and
  the 3/4-symbol stability criterion was structurally unattainable.
- **Fix:** pass `sym_factor=252` (F-BO, race24) or `756` (F-FB bins)
  matching the actual encodings.  M3 (2772) and M5 (2772/8316 incl.
  slope class) already matched their encodings.
- **Impact:** per-symbol contrast columns and stability flags for F-X
  and F-Xb recomputed.

## D28 — Grid-level span used full-day median ABR (REVIEW_2 F5)
- **Defect:** `grid_columns` (RND/PRND/PRAND level sets) and
  `K.placebo_grid_levels` set the ±3.5·A band from `nanmedian(abr)` over
  the whole day — future information inside the level coordinates.
- **Fix:** both now use `abr` at the day's first bar (causal, past-50-bar
  ABR).
- **Impact:** grid level sets re-derived; all grid-set event tables
  (M3 grid columns, M4 P-RAND pool) re-extracted.

## D29 — F-B pooled RND alongside structural sets (REVIEW_2 consistency)
- **Defect:** F-B pooled {S1,S2,PDHPDL,ASIA,RND} while F-T pools only
  the four structural sets; the plan's F-B text does not list sets.
- **Fix:** F-B pooled tests now use the same four sets as F-T; RND
  retest/role-reversal kept as descriptive-only rows.
- **Impact:** F-B pooled contrast recomputed on four sets.

## D30 — P-RAND fake-edge pokes not streak-merged (REVIEW_2 F7)
- **Defect:** placebo poke `depth` took only the first bar of a wick
  streak (the 24-bar freshness dedup swallowed the rest), while real
  pokes merge a streak into one event with depth = max penetration.
- **Fix:** `prand_edge_events` now merges consecutive poking bars into
  one event (depth = max over the streak; freshness measured from the
  streak end), mirroring the real-poke machinery and M4b's SPK arm.
- **Impact:** placebo poke depth distribution shifted deeper; F-FB/F-BO
  remain not-identified (sparsity unchanged) but the depth-bin contrast
  is now honest.

## D31 — Minor conformance items (REVIEW_2 F6/F8/F9)
- **F6:** `ledger_row` had no call sites — result rows were appended via
  interactive invocation of the same function.  Now wired: `mk_ledger.py`
  emits one `market_study` row per family from `out/*_results.json`,
  idempotent on (family, run_tag), carrying event-table sha256 per
  symbol and `supersedes` references.  All r2+ rows come from that
  script.
- `resolve_touch_outcome` (dead code) carried the same inward-barrier
  defect — corrected (see D25).
- M2 Asia mask `cet<480` aligned to the M3 convention `(0 < cet <= 480)`
  for a consistent session boundary.
- `mk_m4b_shifted.py` docstring cited prereg sha 9c1972ac while the
  addendum file on disk hashed 4abca652 (post-T000390 caveat edits);
  the current file re-registered as T000392 before the M4b re-run.
- `placebo_lines` per-symbol RNG: verified already seeded per symbol
  (`SEED ^ crc32(sym)`) — no change required.
- M5 freshness `(t - last_hit) > FRESH`: verified identical semantics
  to M3's `[t-FRESH, t)` window — no change required.
- F-M family scope (12 tests per symbol) is an accepted reading of the
  plan's "per symbol" wording; documented as such.

## D32 — Known-answer suite (Ruling 3 execution gate)
- `research/market/tests/` now holds a gated suite, run BEFORE the
  r2 re-extraction: 22/22 pass on the fixed code.
- **Resolver** (`test_resolver.py`, 8 tests): hand-made M1 paths both
  sides — support/resistance break+bounce, NONE, overshoot=0.0005
  measured at a known wick, outcome frozen at the resolution bar.
  The verbatim pre-fix barrier logic labels a clear support break
  "BOUNCE" (old code demonstrably wrong on the same fixture).
- **Bootstrap** (`test_contrast_boot.py`, 5 tests): planted D=+0.10
  recovered inside its CI; planted null straddles 0; thin-placebo
  concentrated cells (the F2 configuration) keep the point inside its
  CI on all 20 seeds while the verbatim pre-fix statistic's bootstrap
  is systematically shifted upward (>=80% of seeds) — the mechanism
  that pushed real points outside their own CIs.
- **Look-ahead canary** (`test_lookahead.py`, 3 tests): mutating all
  bars after t leaves grid_columns/placebo_grid_levels envelopes and
  detect_touches features <= t unchanged; the pre-fix full-day-median
  sizing demonstrably moves under the same mutation.
- **Symbol decode** (`test_decode.py`, 6 tests): round trip across all
  4 symbols under each module's declared factor (M3 2772; M5 2772/8316;
  M4/M4b 252/756); the pre-fix 2772/8316 decode on M4 keys collapses
  every symbol to EURUSD, reproducing F3.

### D33 — shared ledger verify() break at T000365/366 (REVIEW_3 N1) — LEAD DEVIATION (Ruling 4)
*Opened 2026-09-21 17:11Z; completed by Lead Ruling 4 (17:15Z).*

> "Chain break at `ledger/TRIALS.jsonl` index 365 (rows T000365/T000366,
> perception lane `perception_golden`, written ~10:23–10:26Z) is a known
> foreign-writer serialization-basis defect: spaced separators + CRLF,
> prev hash computed over the spaced re-serialization instead of raw
> bytes. Mechanism proven benign in REVIEW_3 N1 (stored prev
> `46a823b5…` = sha256(line 364 without `\r`)). The suffix chain
> T000366→EOF verifies, and DR-MARKET rows T000367–T000398 are
> unaffected. The file is not edited; history is not rewritten.
> Accepted by Lead Ruling 4."

Verification (2026-09-22, system clock): `pa_ledger.verify()` returns
`(False, 365)` — expected until the pinned exception lands (EVAL-AUDIT
lane, per Ruling 4).  Independent suffix check: every edge
T000366→T000398 verifies against raw-byte hashing and the tail sidecar
matches the last line's sha256 (`adedb98c…`).  This lane now writes the
ledger only through `pa_ledger.append` (see `mk_ledger.py`).

Verification date above is the local date; the UTC time was 2026-09-21 ~17:18Z (Lead note, R11).

### D34 — REVIEW_3 minors N2–N5 fixed
*Logged 2026-09-21 17:11Z.*
- N2: `mk_ledger.py` `_fx`/`_fl` read wrong family keys → T000394/T000396
  shipped empty `key_metrics`.  Fixed with generic `_metrics` extractor;
  re-emitted as run_tag=r2b → **T000397 (M4, supersedes T000394)** and
  **T000398 (M5, supersedes T000396)** with full metrics, strict JSON.
- N3: dead machinery deleted — `first_touch_events`,
  `resolve_touch_outcome`, `level_arrays_from_daily`, `match_strata`,
  `block_boot_stat`, `block_boot_diff` (mk_common), `contrast`
  (mk_m3_levels).  `placebo_grid_levels`/`grid_columns` kept — live in
  the suite.  Suite re-run: 22/22 PASS.
- N4: `_stab()` renders YES/no only on formal rows (finite q); desc
  rows now render "—".  All 4 reports regenerated.
- N5: `mk_m4b_analyze.py` docstring now cites T000392; `key_metrics`
  NaN-sanitized via `_clean()`.

### D35 — infra: pinned verify exception, Lead Ruling 4
*Logged 2026-09-21 17:40Z by the EVAL-AUDIT lane (mandate 2, item 6).*

`lib/pa_ledger.py` `verify()` now carries the pinned exception authorised
by Lead Ruling 4 for edge 365 only: the stored prev `46a823b5…` is
accepted iff it equals sha256(raw line 364 with `\r` stripped); the raw
hash still propagates outbound and every other edge stays strict.
Real ledger verifies `(True, None)`; tamper tests (mutate any other
line, extra `\r` elsewhere, different stored prev at edge 365) all fail
closed.  Checker: `research/perception/evalcheck/walls_check.py`.
