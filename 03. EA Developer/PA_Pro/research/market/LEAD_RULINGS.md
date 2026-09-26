# DR-MARKET — LEAD RULINGS

Append-only; newest entries last. Re-read this file at every queue item.

## Ruling 0 (08:16Z) - mandate issued
- The mandate is `research/market/MANDATE.md`. The walls are in its "Walls" section and in `docs/CHARTER_ADDENDUM_4.md`.
- The lane starts as soon as a Devin slot frees (machine cap: 6 concurrent Devin jobs).
- The Lead reads the `## SUMMARY` of `MARKET_LOG.md` about every 60 minutes and checks the prereg hash before any forward statistic.

## Ruling 1 (11:01Z) - M0–M3 accepted; fix timestamps; carry on
- **Accepted:**
  - M0: the DESIGN clock is confirmed as EET, CET = server − 1 h.
  - M1: prereg T000364, recorded before any forward statistic.
  - M2: RHYTHM.
  - M3: LEVELS, T000367–372.
  - D1–D4: each was logged before use. D4 is a correctness fix.
  - The rigour is what this program needs.
- **Timestamps.** Two MARKET_LOG entries are wrong:
  - "~09:10Z — M0 complete": the lane started at 09:56Z;
  - "~17:55Z — M1–M3 complete": 17:55 is local time (UTC+7).

  Append a correction; never rewrite past entries. From now on take UTC from the system clock (`datetime.now(timezone.utc)`) and label it Z.
- **Hand-off.** Your M3 results go to the Perception lane through its Ruling 5. Never write into other lanes' folders.
- **Carry on** with M4–M8.
  - M4 uses the detector preregistered in STUDY_PLAN §5. Any change is a deviation, logged before results.
  - In M7, `PERCEPTION_IMPLICATIONS.md` maps each result to a `params_v1.json` parameter or a `DN_*` section in `research/perception/design/`. Read those design notes; do not edit them.

## Ruling 2 (12:23Z) - the M8 review found real defects: remediate properly, then review again
- **Good.** The independent review did its job:
  - look-ahead in about 10% of ASIA events;
  - a non-exchangeable placebo in F-TL, which may flip the −13.7 pt headline;
  - about 15 spec↔code divergences that were never logged.

  Finding these before anything was promoted is the system working.
- **From now until a second review passes, every DR-MARKET result is PROVISIONAL.** That covers M2–M6, MARKET_MECHANICS, PERCEPTION_IMPLICATIONS and TOM_TAT_VN.
  - Put a `PROVISIONAL — under remediation (Ruling 2)` banner at the top of each of those files now.
  - The Perception lane has been told to treat them as priors only.
- **Remediation protocol:**
  1. Log every divergence the reviewer found as its own deviation (D6, D7, …). Classify each as:
     - harmless;
     - changes a result — say which family;
     - or a plan defect.
  2. Fix the code and re-extract everything affected. The look-ahead fix applies to every family that uses ASIA events, not only the one where it was found.
  3. Re-analyse, and append **new** ledger rows for each re-run family. Each new row references the rows it supersedes (T000367–379). Never edit old rows.
  4. Where the preregistered plan itself was the problem (e.g. the F-TL placebo design), record the plan fix as a deviation **before** the re-run, with the reason. Report both the prereg-conform result and the corrected result.
- **Second review.** A fresh reviewer sub-agent, which has not seen the first review's text, re-checks the fixed code: causality, placebo exchangeability, multiple testing, data walls. Only then may results be final.
- **Output.** MARKET_MECHANICS, PERCEPTION_IMPLICATIONS and TOM_TAT_VN become **v2**, each with a short "what changed vs v1" table, so the Owner can see which facts survived.
- **Scope note (D5).** RND and cascade results are about round numbers near the day open. Say so in the Vietnamese summary.

## Ruling 3 (15:34Z) - REVIEW_2 FAIL: prove the code on known answers before any re-run
- **REVIEW_2 did its job.** Two blockers:
  - **F1:** the M3 resolver has its barriers inside-out for side = +1;
  - **F2:** `contrast_boot` zero-fills an empty placebo resample.

  Plus F3 (symbol decode), F5 (full-day look-ahead in the grid envelopes), F6 (ledger reproducibility) and F4/F7–F9. Every headline stays PROVISIONAL.
- **The root problem.** This pipeline was never checked against known answers. Charter Addendum 3 already requires an execution gate on synthetic fixtures before results count. **Build it now, before any re-run:**
  1. **Resolver unit tests on hand-made paths**, for both sides (+1 / −1), bounce vs continuation, overshoot and freeze-at-resolution. F1 must fail the old code and pass the new.
  2. **Planted-effect test.** Generate synthetic M1 paths where levels reverse with probability p_real and placebo levels with p_plac.
     - The full pipeline (extract → strata → `contrast_boot` → BH) must recover D = p_real − p_plac within its CI.
     - With p_real = p_plac it must give a null at about the nominal rate.
     - Run it at small n too, so empty resamples occur (F2).
  3. **Future-mutation canary.** Change every bar after t. The event features at t, and the placebo envelopes, must not change. This catches F5-type look-ahead.
  4. **Symbol-decode test:** a round trip across all 4 symbols (F3).
  5. The tests live in `research/market/tests/` and must run green before any extraction.
- **Then:**
  - fix all REVIEW_2 findings;
  - re-run every affected family, with new ledger rows that reference the ones they supersede;
  - update the v2 docs and the "what changed" tables.
- **REVIEW_3.** A fresh reviewer verifies each REVIEW_2 finding is closed, re-runs the known-answer suite, and scans for new look-ahead.
  - Only a REVIEW_3 PASS makes results FINAL.
  - If time runs out first, stop cleanly with everything marked PROVISIONAL. Better unfinished than wrong.
- **M4b.** It stays in scope under the same rules. Its prereg hygiene (the re-registration as T000392 before the re-run, and the deviation logged) is accepted.

## Ruling 4 (17:15Z) - N1 ruled; REVIEW_3 converts to PASS; go FINAL v2
- **REVIEW_3 is excellent work.** It verified every closure from current bytes, re-ran the suite fresh and recomputed all 12 event hashes. It also found the one thing that was still wrong (N1) and proved it benign rather than guessing.
- **N1 ruling: branch (b), a Lead deviation. Do NOT byte-edit the ledger.** Log this text verbatim as **D33**:
  > "Chain break at `ledger/TRIALS.jsonl` index 365 (rows T000365/T000366, perception lane `perception_golden`, written ~10:23–10:26Z) is a known foreign-writer serialization-basis defect: spaced separators + CRLF, prev hash computed over the spaced re-serialization instead of raw bytes. Mechanism proven benign in REVIEW_3 N1 (stored prev `46a823b5…` = sha256(line 364 without `\r`)). The suffix chain T000366→EOF verifies, and DR-MARKET rows T000367–T000398 are unaffected. The file is not edited; history is not rewritten. Accepted by Lead Ruling 4."
- **Root cause is on the Lead side, not yours.** The perception lane wrote ledger rows with its own writer. From now on, all lanes write the ledger only through `pa_ledger.append`.
  - The EVAL-AUDIT lane will add a pinned, hash-specific exception for edge 365 to `pa_ledger.verify()`. Only that edge; every other edge stays strict.
  - It will also add a lint that every ledger line is compact JSON + LF.
  - Neither of these blocks you.
- **Verdict.** Per REVIEW_3 §8, this ruling converts REVIEW_3 to **PASS**. No recomputation is needed. Do not edit REVIEW_3.md; this ruling and your MARKET_LOG entry are the record.
- **Now, FINAL v2:**
  1. Log D33 in DEVIATIONS.md.
     - Run `verify()` and log the result in MARKET_LOG: expected `(False, 365)` until the pinned exception lands.
     - Separately verify the suffix T000366→EOF and log that result too.
  2. Flip the PROVISIONAL banner to **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)** on all 8 docs. Keep the per-claim caveats: descriptive rows stay "descriptive, no inference"; F-BO/F-FB stay "not identified".
  3. Update the "what changed vs v1" table to the r2/r2b numbers (T000393/T000395/T000397/T000398 plus the M3 rows).
  4. Rewrite TOM_TAT_VN.md for the Owner: plain Vietnamese, facts only, 10–15 lines. For each fact give the number, whether it held in ≥4/6 years and ≥3/4 pairs, and what it means for how the EA should *draw* (not trade).
  5. MARKET_LOG entry, then a final message in Vietnamese of 12 lines or fewer: the headline facts with q/stability, and which PERCEPTION_IMPLICATIONS the perception lane should adopt.
- **Scope stays DESIGN only.** No new studies, no new families, no tuning.

## Ruling 5 (17:34Z) - FINAL v2 accepted; lane closed
- **Accepted.** D33 carries the ruling text; `verify()` was run, and the suffix chain T000366→EOF was verified separately; the banners read FINAL v2; TOM_TAT_VN was rewritten. The numbers were spot-checked by the Lead against MARKET_MECHANICS: S1/S2, age decay, touch decay, F-TL, ASIA, PDH/PDL, RND, race24 and the overshoot quantiles all match.
- **Two Lead corrections:**
  1. TOM_TAT_VN item 2 said "~2 ngày M5". 48–96 M5 bars is 4–8 hours. The Lead corrected the file, with a note.
  2. The D33 verification line uses the local date (2026-09-22). The UTC time was 2026-09-21 ~17:18Z. EVAL-AUDIT adds a one-line note under D33 when it writes D35.
- PERCEPTION_IMPLICATIONS still says "M4b race24 … pending REVIEW_3". That is stale; REVIEW_3 is PASS by Ruling 4. Read it that way; no edit is needed.
- **Adoption** of the implications into the perception engine is decided in perception Ruling 11 §11.5. The "news window 07:55–09:30 CET" is *not* adopted as a hard gate; it becomes an `eu_open` attribute.
- **The DR-MARKET lane is closed.** Any further market study needs a new mandate, a prereg, and the known-answer suite green first.
