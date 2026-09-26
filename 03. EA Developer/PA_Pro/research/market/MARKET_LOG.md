# DR-MARKET — MARKET_LOG

Append-only. `## SUMMARY` stays on top, updated at each queue item.

## SUMMARY

**POST-M8 REMEDIATION COMPLETE.** The independent review (`REVIEW.md`)
upheld material defects; all extractors/analyzers were corrected,
re-extracted, re-analyzed.  Corrected ledger rows: T000380–387 (M3
T000380–384, M4 T000385, M5 T000386, M6 T000387); pre-review rows
T000367–379 are superseded, not erased.  Deviations D6–D22 logged.

- **M0 DONE**: server clock CONFIRMED = UTC+2/+3 EU DST. CET = server−1h.
- **M1 DONE**: `STUDY_PLAN.md` preregistered, T000364, sha256 `abc8b5ba…`.
- **M2 DONE**: `RHYTHM.md`. Asia range median 22.6p EURUSD / 31–32p
  others; spike clusters 08:00, 09:00, 14:30 CET.
- **M3 CORRECTED** (`LEVELS.md`, T000380–384):
  - Pivot levels: S1 +1.48pt, S2 +1.09pt — small, stable (6/6y, 4/4s).
  - **ASIA flips sign after the lookahead fix: −1.61pt stable** — Asian
    H/L attract continuation, not bounces.
  - Age: <3h +5.01pt; gone by ~8h; half-life ≈0.5h.  Touch: 1st +4.5pt,
    2nd +0.8pt, 3rd+ ≈0.
  - Overshoot p90 ≈ 0.5–0.7 ABR → zone half-width 0.25–0.35 ABR.
  - Retest/role-reversal: no effect.  Cascades: weak positive, ns.
  - PDHPDL/RND: no stable effect (old −2.4pt RND was a placebo-mapping
    artefact).
- **M4 CORRECTED** (`BOXES.md`, T000385): declared detector now yields
  ~9.4–10.4k boxes/symbol, heights 12–35p, life ~12 bars.
  **F-BO race24 and F-FB are NOT IDENTIFIED** (D22): the declared P-RAND
  fake-edge placebo gives ~48 breaks/~60–110 pokes per symbol and
  traversal heights ~0.2 ABR vs real ~5 ABR — strata barely overlap.
  The pre-review "+13.8pt deep-poke" claim is VOIDED.  Descriptives are
  honest: poke depth median ~0.8p, P(opp edge ≤24b) ≈ 0.21.
- **M5 CORRECTED** (`LINES.md`, T000386): **sign reversal** — with
  exchangeable shifted-line placebos, third+ touches on real θ2-pivot
  lines bounce +7.16pt (x1) / +8.39pt (x2), stable.  The voided −13.7pt
  headline must not be quoted.  Slope class: no post-break effect.
- **M6 CORRECTED** (`MOMENTUM.md`, T000387): lag-1 autocorr −0.03…−0.07
  significant everywhere; corrected VR(12) ≈ 0.90–0.97, significantly
  <1 in ASIA/EU.  Pullbacks retrace ~100% of prior leg.  EMA25 = just a
  moving average (no kink at L=25).
- **M7 DONE**: `MARKET_MECHANICS.md`, `PERCEPTION_IMPLICATIONS.md`,
  `TOM_TAT_VN.md`, figs regenerated on corrected results.
- **M8 DONE**: `REVIEW.md` written; all upheld findings remediated and
  logged; residual limitations (F-FB/F-BO identification, F-A >24h bins,
  grid scope D5) documented for the Lead.

## LOG

### 2026-09-21 ~09:10Z — M0 complete
- Built `mk_common.py` (loader/ABR/CET/DC pivots/touch events/M1 resolver/
  day-block bootstrap/strata matching/ledger wrapper) and `mk_m0_clock.py`.
- Findings in `CLOCK_AUDIT_DESIGN.md`. No ASK_LEAD needed: no deviation.

### 2026-09-21 ~17:55Z — M1–M3 complete
- STUDY_PLAN hashed (T000364). RHYTHM.md written; descriptive family row
  logged as T000373.
- M3 pipeline: `mk_m3_levels.py` (extraction → `out/m3_events_*.npz`, sha
  logged) + `mk_m3_analyze.py` (matched-strata Hajek contrasts, joint
  day-block bootstrap via matrix-batch multinomial, BH-FDR per family,
  4/6-year + 3/4-symbol stability). Deviations D1–D4 logged.
- ~4.3M touch events + ~10k cross events across 4 symbols resolved on M1
  paths; extraction deterministic under crc32 seeds.

### 2026-09-22 — M4–M7 complete (pre-review)
- M4 boxes, M5 lines, M6 momentum, M7 synthesis docs + figs.
- Ledger T000374–379. Pre-review numbers now SUPERSEDED (see below).

### 2026-09-22 — M8 review + full remediation
- Independent auditor (`REVIEW.md`) upheld: ASIA lookahead (~10% events),
  non-exchangeable M5 placebo (voided −13.7pt), ~15 spec↔code
  divergences, analyzer key-decode bug, VR missing /k, cross/retest
  semantics.
- Remediated: rewrote M3 ASIA arming/freshness/cross/retest; M4 declared
  detector + P-RAND fake-edge placebo; M5 shifted-line placebos +
  bar-index geometry + zone-hit freshness; M6 θ-scales, warmup, gap
  segments, VR/k, 12 formal tests; analyzers per-symbol strata + declared
  families.  D6–D22 logged; all artifacts re-extracted & re-analyzed.
- Post-remediation ledger: T000380–387 (sha256 per-symbol event tables
  embedded).  Notable corrections: F-TL sign flip (−13.7→+7.2pt), ASIA
  sign flip (+?→−1.6pt), F-FB/F-BO unidentified under declared placebo,
  RND effect was a placebo-mapping artefact.
- Residual for Lead: fake-edge placebo redesign (D22); F-A >24h bins;
  D5 grid scope.

## 2026-09-21 15:36Z — Ruling 3: re-extraction halted pending known-answer suite
- REVIEW_2 verdict FAIL (blockers F1 resolver barriers side=+1, F2
  contrast_boot empty-arm zero-fill; plus F3 decode, F5 grid look-ahead,
  F6 ledger wiring, F4/F7-F9).
- Per Ruling 3 all in-flight re-extraction was STOPPED at 2026-09-21 15:36Z.
  Partial outputs on disk (out/m3_events_*.npz, out/m4_events_*.npz as
  currently written) are STALE — mid-fix snapshots, not usable results.
  Nothing deleted; they will be overwritten by the gated re-run.
- Code fixes already applied pre-halt: D25 (resolver barriers),
  D26 (both-arms-present replicate mask), D27 (sym factors 252/756),
  D28 (causal day-open ABR in grid envelopes), D29 (F-B pool scope),
  D30 (P-RAND poke streak-merge), D31 (F6 mk_ledger.py + minors).
- Next: research/market/tests/ known-answer suite must go green before
  any re-extraction.

## 2026-09-21 15:44Z — Known-answer suite GREEN; gated re-extraction started
- tests/run_tests.py: 22/22 PASS on fixed code.  Each module embeds
  verbatim pre-fix logic and asserts the OLD behaviour fails the same
  fixture (F1 mislabels a support break as BOUNCE; F2 bootstrap
  upward-biased on concentrated-thin placebos; F3 decode collapses to
  EURUSD; F5 envelope moves under future-ABR mutation).
- Re-extraction M3 + M4 launched under the fixed code (D25-D31).
  Analyzers + ledger (mk_ledger.py run_tag=r2) follow; then REVIEW_3.

## 2026-09-21 16:23Z — r2 remediation complete; REVIEW_3 pending
- Known-answer suite green (22/22) gated the re-run (D32).
- Re-extracted: m3_events_* (resolver+grid fixes), m4_events_*
  (grid pool + P-RAND streak-merge).  m4b_events_* re-extracted —
  byte-identical shas to T000391 (boxes unchanged).  M5 events
  unchanged (analyzer-only fix); M6 untouched.
- Re-analyzed M3/M4/M4b/M5 with fixed bootstrap + decode.  New ledger
  rows: T000393 (M3), T000394 (M4), T000395 (M4b, spec 4abca652),
  T000396 (M5) — each carries supersedes + per-symbol event sha256.
- Reports regenerated: LEVELS/BOXES/BOXES_M4B/LINES (writers now emit
  the PROVISIONAL banner); MARKET_MECHANICS/PERCEPTION_IMPLICATIONS/
  TOM_TAT_VN rewritten from fresh JSONs (F4 closed); v1→v2 tables
  updated to r2 numbers.
- Headline deltas post-fix: S1 +2.45pt / S2 +1.75pt stable; F-T t1
  +7.32pt; F-B all ns; M4b race24 +1.14pt now stable (decode fix);
  F-TL +7.16/+8.39pt survives; F-BO/F-FB P-RAND arm still unidentified.
- Next: fresh REVIEW_3 (closure check + suite re-run + leak scan).

## 2026-09-21 17:12Z — REVIEW_3 returned FAIL (governance only); minors remediated
- REVIEW_3.md written by fresh reviewer: science all-closed (F1-F9,
  suite 22/22 fresh run, 12/12 event shas recompute, zero stability
  mismatches, no new look-ahead).  Single blocker N1: shared ledger
  verify() fails at line 365 — foreign-writer CRLF basis, proven
  benign, unhealable by byte edit.  Needs Lead ruling (D33).
- Minors fixed in-pass (D34): N2 mk_ledger extractors -> r2b rows
  T000397/T000398 superseding T000394/T000396; N3 dead code deleted;
  N4 stable flag hidden on desc rows; N5 docstring + strict JSON.
- Suite re-run after dead-code removal: 22/22 PASS.
- Awaiting Lead ruling on N1; banners stay PROVISIONAL.

## 2026-09-21 17:20Z — Ruling 4 executed: N1 ruled (b); REVIEW_3 = PASS; FINAL v2
- Lead Ruling 4: N1 accepted as Lead deviation, no byte edit.  D33
  now carries the ruling text verbatim.
- verify() re-run: (False, 365) — expected until the EVAL-AUDIT pinned
  exception lands.  Independent suffix check T000366→EOF: all edges
  verify, tail sidecar matches last-line sha256 (adedb98c...).
- Per REVIEW_3 section 8 this ruling converts REVIEW_3 to PASS —
  REVIEW_3.md untouched; this entry + D33 are the record.
- Banners flipped to FINAL v2 (REVIEW_3 PASS by Lead Ruling 4) on all
  9 docs; writers patched so regen keeps the banner.  Per-claim
  caveats kept (desc rows '—', F-BO/F-FB not identified on the
  declared arm).
- TOM_TAT_VN rewritten for the Owner (12 facts, numbers + stability +
  drawing implication).  Lane DR-MARKET closed at FINAL v2.
