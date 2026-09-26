# PERCEPTION — LEAD RULINGS

Append-only; newest entries last. Re-read this file at every queue item.

> R0–R50 are archived verbatim in `research/perception/LEAD_RULINGS_ARCHIVE_R00-R50.md` (Ruling 67 §67.5). Citations of those rulings stay valid and resolve there.

## Ruling 51 (12:33Z 22/09) - light check; the marker cut buys the headroom and becomes K7 on verification; box levers move before birth; conversion-in-place reopens the fixture debt; two log lines are stamped in the future

**§51.1 Light check (12:30Z).**
- **Acks:** build and BOX-LAB are at R50 (12:11Z, 12:20Z). SCALE is at R49 and needs nothing from R50.
- **The headroom arm `marker.off`** (`66f596dc`, build lane):
  - box .076 =, level .092 (+1), line .104 =, bracket .341 =;
  - clutter median 4.67 (was 5.00);
  - panels ≤ 5.0: 103 against 90 (+13);
  - OFF ≡ parent 576/576.
  - BAR_MARKER is not an M1 family. On the marginal panels the engine drew 117 of them with 0 hits, and the only golden marker hit lost is 9.37c.
  - The gentler `bmday` (day-extreme markers only) is running.
- **BOX-LAB's covered-but-missed anatomy** (`c1_missed.py`, `9acaa206`). 55 of 119 goldens are covered: 9 hit, 46 missed. Of the 46, none was born and then lost; the funnel kills the right box before birth.

| bucket | count | what happens |
|---|---|---|
| below_min_score | 14 | Right edges, but the score is under the 5.0 birth floor. |
| log_only | 11 | Only the wick-edge variant stream matches; `wick_birth` is OFF, so they never enter the pool. |
| outranked | 10 | They lose the live-slot displacement to the incumbent. |
| rate_limited | 8 | The 1-per-72-bar box rate is already spent on a wrong box. |
| expired | 3 | Their TTL runs out while pending. |

  32 of the 46 are score-starved (the first, third and fourth rows).
- **`box.cong_pivedge` is a lever, not a keep, at `9acaa206`:** box +1 and level +1, but clutter 5.33 in every configuration that keeps the gain.
  - Its one flip (9.2b g0) wins because pivot-seeded bands carry high confirmation density, so they score 9.31 against the stale envelope's 6.56.
- **F3 and F5 landed** (12:08Z). F3 adds a per-symbol pip; EURUSD is identical, spot 15/15, and the full 1728 run is in progress. F5 fixes the `render.py` object layer; render is not an engine file. engine.py and patterns.py now differ from the snapshot for F3.
- **FIXTURE_CONFLICT.md is written** (12:13Z) and accepted. Its "conversion-in-place" direction (the context becomes the box, zero net births) is the most promising cure.
- **Walls hold:** GATE_PACK_9283b389 is unchanged, and so is `test_engine.py` (`gen_engine` 0 uses).

**§51.2 Two log lines carry future times.**
- PERCEPTION_LOG line 581 says "13:00Z", but the file was last written at 12:25:37Z.
- BOX_LOG's heading "12:40Z" was written by 12:29:39Z.
- **Each lane appends one correction line with the true time, and leaves the old line as it is** (R31 §31.4).
- From now on, every stamp comes from `logline.py` or the clock, never from a plan.

**§51.3 K7: the headroom keep.**
- Choose between `bmday` and `marker.off` with the amended ink-only rule (§50.2 item 3):
  - no M1 hit lost;
  - the median does not rise;
  - panels ≤ 5.0 up by at least 5;
  - no new suite failure;
  - OFF ≡ parent.
- **Prefer `bmday` if it passes,** because it keeps the markers the author can draw. Otherwise take `marker.off`.
- **Reconcile the suite line.** It says 65/72, and also that `pullback_end_box_birth` and `range_box_double_top` are cured. Two cures should give 67/72. List the exact failing tests under the chosen arm. A test outside the seven that fails is a new failure and blocks the keep.
- The kept arm is **K7**. EVAL-AUDIT verifies it on resume (about 14:15Z), with M1, identity, the suite and the margin.

**§51.4 Build, after K7.**
1. **Formal A/B of `cong_pivedge`** (BOX-LAB's arm: npairs 6, top-4, sig-memo) on the K7 parent, at one hash, by 16:00Z. With the median at 4.67, the +1 box may now fit. Keep by §34.5.
2. **Conversion-in-place for the fixture debt, reopened this round** (amends §50.3). A CONTEXT_RANGE that meets a priority-1 box candidate becomes that box, like the `asia_convert` precedent: the same object is relabelled and re-edged, with zero net births.
   - Flagged, with an A/B on the latest parent.
   - Keep it per R44 §44.2: the suite 72/72 unmodified, and §34.5 or §41.3.
   - Time-boxed to 18:00Z.
   - If it fails, FIXTURE_CONFLICT.md gains the numbers and the debt goes into the P-FREEZE package.
3. **The F3 full-1728 identity result** goes in the log. Then write the 15:35Z hand-over line (the job ends at 15:40Z; the Lead resumes the session).

**§51.5 BOX-LAB: box levers move before birth.**
1. **Pivot-edge support as a box score term.** This is the null-validated source (§50.1) used for selection, not generation.
   - First, a diagnosis on the 32 score-starved right candidates: does "both edges within tolerance of a prior confirmed pivot (`t_conf` ≤ i)" separate them from the objects that beat or blocked them?
   - If it does, add it to the box birth score as one flagged term with one weight, and run a lab A/B on the K7 parent.
   - A re-ranking term moves births from wrong boxes to right ones. It should not add ink, but report the margin anyway.
2. **`wick_birth` re-tested on the K7 parent** (the 11 log-only goldens). It was neutral on an older parent (06:3xZ), but the headroom has changed.
3. Hand off either one in REQUESTS.md only if §34.5 passes in the lab and identity holds. The lab deadline is 17:00Z; the build lane's formal A/Bs are due by 20:30Z.
4. **Guard against overfitting.** Every change is scored on TUNE, where M1 is measured, so prefer one mechanism and one parameter. Do not fit weights on TUNE goldens.

**§51.6** No lane changes M1, M2, their thresholds or the ruler.

## Ruling 52 (12:48Z 22/09) - PLAYBOOK_C2.md takes over: lanes run to the end and decide their own keeps; K7 and K8 stand provisionally; the Lead checks hourly

**§52.1 `research/perception/PLAYBOOK_C2.md` (sha256 `EEC61DBA2C8A`) is in force for every lane**, from now until the FINAL STABLE (24/09 05:30Z).
- Lanes decide their own keeps under its section 3, and escalate only for its section 8.
- It replaces step-by-step rulings. The Lead checks once an hour and at each round close.
- **Why:** the keep rules are mechanical, and the Owner asked (12:4xZ) that the lanes work to the end without waiting on the Lead.
- **Read it in full once.** After that, read its section 1 and any new ruling.

**§52.2 K7 and K8 are accepted as provisional keeps.** EVAL-AUDIT verifies both first (playbook E1).

| keep | change | hash | box | level | line, bracket | clutter | margin |
|---|---|---|---|---|---|---|---|
| K7 | `marker.off` (ink-only) | parent `81f7503f` | = | +1 | = | 4.67 | 90 → 103 |
| K8 | `box.cong_pivedge` on K7 | default engine `be4eea26` | 10/119 (+1) | 8/76 (+1) | = | 4.67 | 101 |

- K8 re-breaks the two named fixtures that K7 had cured. Under playbook 3.4 that is a fixture regression: it is logged, and it does not block.
- **Rejected:** `bmday` (margin +4 < +5); `wick_birth` on K7 (box −1).

**§52.3 Timestamps.** The build lane stamped two lines "13:25Z" and "13:48Z", but both were written before 12:46Z. Its "12:47Z" correction line was also written ahead of the clock.
- The build lane appends one correction line that gives the true write times of those entries.
- From now on, playbook §9 applies: every stamp comes from `logline.py`.

**§52.4 Job hand-offs.**
- The build job ends at 15:40Z. The Lead resumes the session with "continue PLAYBOOK_C2 from your HANDOVER line".
- EVAL-AUDIT resumes when SCALE ends (about 14:15Z), with the playbook as its prompt.

**§52.5** No lane changes M1, M2, their thresholds, the ruler, the fixtures or the spec.

## Ruling 53 (13:01Z 22/09) - hourly check; BOX-LAB's escalation: X2 moves to the build lane

**§53.1 BOX-LAB escalated at 12:54Z (playbook 8.4, same-file contention).**
- X2 needs a flag in `salience.py`'s rate gate, and the build lane is editing that file for B1.
- **Ruling:** X2 moves to the build lane, which owns `salience.py`.
  1. BOX-LAB writes the spec into REQUESTS.md now:
     - the rule: a box candidate inside the 72-bar rate window that outscores the box born earlier in that window replaces it (the `lc_score_pick` pattern);
     - its pre-diagnosis: of the 8 rate-limited right candidates, only 9.17b both clears the floor and outscores the holder, so the expected gain is ≤ +1 box.
  2. The build lane runs it as a normal hand-off (playbook B2), after B1's verdict. Keep per 3.1.
  3. A general rule is not a one-case fit, so it is allowed under 3.6. It needs no tuning parameter beyond the existing score and hysteresis.
- BOX-LAB continues with X3, X4 and X.S.

**§53.2 Noted, no action:**
- **X1 is closed correctly.** Pivot support saturates: it is present at birth for 89% of the right candidates and 96 of 103 of the wrong ones, so it separates nothing.
- **The build lane's suite reconcile (12:56Z):** `marker.off` cures no fixture; the earlier claim was a truncated read. K7's legs stand.
- **`ctx_convert` (conversion-in-place):** suite 72/72, all seven cured; A/B at `084caa52` running.
- **The build lane still owes the R52 §52.3 correction** for its "13:25Z" and "13:48Z" lines.

## Ruling 54 (14:02Z 22/09) - hourly check; Devin capacity drops to two PA-PRO slots, so the build lane yields its slot to EVAL-AUDIT until the round close; K9 is noted; the fixture debt goes to the Owner

**§54.1 Capacity.** Since 13:35Z the Owner's other project (W11) runs 4 Devin jobs. The Owner's cap is 6 in total, which leaves PA-PRO **two** slots.
- EVAL-AUDIT, the independent verifier, could not start: K7, K8 and K9 are unverified, and the F1 identity check is due before the 20:30Z merge.
- The build lane's queue was empty (its log, "Queue sạch"). The Lead wrote `pause build` into the keeper and ended build job 9e6cab at 14:02Z. The keeper now starts EVAL-AUDIT.
- **The Lead asks the Owner whether to raise the cap.** Until he answers, PA-PRO runs two lanes.

**§54.2 Until the C-2 close, with two slots (BOX-LAB and EVAL-AUDIT):**
- **EVAL-AUDIT works playbook E1–E5:**
  - verify K7, K8 and K9;
  - the F1 identity check, before 20:15Z;
  - the null review;
  - the pack-line fix;
  - the human-ceiling kit.
- **A BOX-LAB hand-off before 20:30Z:** EVAL-AUDIT's independent same-hash A/B on the current parent, with its own scorer, counts as the formal A/B (playbook B2). A CONFIRMED hand-off is a keep. The build lane flips the defaults when it resumes.
- **At 20:30Z** the Lead pauses BOX-LAB and resumes the build lane. The build lane then:
  1. flips any confirmed hand-off;
  2. merges F1 (playbook 3.5);
  3. logs STABLE.
  EVAL-AUDIT re-proves identity (TUNE 1728/1728) by 21:15Z, and writes GATE_PACK_C2 by 22:30Z.

**§54.3 K9 noted (build lane, 13:36Z; provisional until EVAL-AUDIT confirms it):**
- `rate_label_tf = 2` per day (ink-only): M1 flat, clutter 4.67 → 4.33, margin 101 → 114, suite 65/72 with the named seven, OFF ≡ parent 576/576.
- **PARENT `ee2cbf1202db47b6`** = STABLE `9acaa206` + K7 + K8 + K9, with a snapshot.

**§54.4 The fixture debt is closed for C-2 and goes to the Owner.**
- Conversion-in-place cures all seven fixtures, and fails M1:
  - loose: box +2, level −4, line −3;
  - wraps: box +1, level −1, line −2.
- **Five mechanisms now pass the suite and fail M1.** The consumed CONTEXT_RANGE carries level and line hits, so removing it costs them.
- FIXTURE_CONFLICT.md is updated. It goes into the P-FREEZE package as an Owner decision: keep spec §5 as the fixtures encode it, or relax it to what the author draws.

**§54.5 Noted:**
- X2 was already live as K4 `box_score_pick`, so there was nothing to A/B.
- `slope_floor` 0.42 is rejected (line −4).
- **Level misses are score-starved like box misses.** All 18 priced misses have a same-price candidate that dies at the birth gate (score 0.6–2.4 against 7–9 born).
- The build lane's timestamp correction is done (13:18Z).
- **Score starvation is now the round's main lever class** for both boxes and levels. Playbook 3.6 (no weight fitting on TUNE) applies in full.

## Ruling 55 (14:33Z 22/09) - the Owner's two decisions: the Devin cap is 7, and P-FREEZE is now; engine code closes on PARENT ee2cbf12; verify, merge F1, FINAL STABLE, then the Owner's package for the morning of 23/09; HOLD stays sealed until the Owner decides

**§55.1 The Owner's decisions.** Before 14:24Z the Owner answered the Lead's two open questions (R54 §54.1 and R49 §49.7) in two lines.

| his words | meaning | status |
|---|---|---|
| "nâng trần Devin lên 7" | raise the Devin cap from 6 to 7 | done at 14:24Z |
| "chốt ngay bây giờ" | lock it right now | this ruling |

- **The cap.**
  - `lane_keeper2.ps1` now has `capTotal = 7`.
  - The `pause build` line is gone from `lane_keeper.ctl`.
  - The keeper restarted as PID 23760 and resumed the build lane at 14:24:10Z (job `20260922142410-47aacc`).
  - PA-PRO keeps 3 slots and W11 keeps 4.
- **"chốt ngay bây giờ"** answered the question "Có chốt P-FREEZE ngày 25/09 không?" (do we lock P-FREEZE on 25/09?).
  - The Lead reads it as: **freeze now, and do not wait for C-3 and C-4.** This matches the Owner's 04:17Z directive ("develop faster"; "quá tốn time").
  - If he meant "confirm 25/09 now", he says so. The Lead then restores the playbook §7 calendar, and about an hour is lost.
  - Nothing below is irreversible before HOLD, and HOLD stays sealed until the Owner decides (§55.6).

**§55.2 What "freeze now" means.**
- **Engine code is closed from the commit time of this ruling.** From then on there is no new arm, no new keep and no default flip, with two exceptions:
  1. reverting a keep that EVAL-AUDIT fails (playbook 4.6);
  2. the F1 merge, which is behaviour-neutral and lands only on identity (playbook 3.5).
- **The freeze parent is PARENT `ee2cbf1202db47b6`** = STABLE `9acaa206` + K7 `marker.off` + K8 `cong_pivedge` + K9 `rate_label_tf=2`, subject to EVAL-AUDIT's verification (§55.3).
- An arm that is already running may finish. Its verdict goes in the log as a post-freeze note, and it cannot become a keep.
- **C-3 and C-4 are cancelled.** §55.4 replaces the playbook §7 calendar.
- **M1 on the freeze parent** (build lane numbers, which EVAL-AUDIT confirms):

| family | freeze parent | v0 | M1 |
|---|---|---|---|
| box@1 | .084 (10/119) | .134 (16/119) | **not met: 6 hits short** |
| level@1 | .105 (8/76) | .066 | met (point estimate) |
| line@2 | .104 (20/193) | .093 | met (point estimate) |
| clutter median | 4.33 (114/179 panels ≤ 5.0) | ≤ 5.0 | met |

- **Box is not passed, and the Lead does not relabel it as passed.** Under R49 §49.7 the box criterion goes to the Owner together with the human ceiling (§55.5).
- **Why the Lead does not ask for another round:**
  - C-2 added one box hit (K8, about 12:50Z) in 3.5 hours, and none since.
  - BOX-LAB's 14:14Z finding: every point on the `deeper` dial is dead. The remaining score terms have no failure mechanism, so moving them is weight fitting on TUNE, which 3.6 bans. "Outranked" is budget displacement, so buying those hits costs other families.
  - The build lane reached the same end at 14:31Z, on the K9 cache:
    - the 21 outranked right candidates lose on the score itself (median gap −5.83 to the weakest incumbent), so even zero hysteresis rescues none and floods 112 wrong ones;
    - the 30 below-floor right candidates sit inside the wrong bulk, and cutting the floor floods 2488;
    - no score term separates right from wrong.
    - Its words: the deficit "needs a signal source not in the feature set".
  - 12 of 119 box goldens have no causal edge pair at τ (BOX_LOG, 13:08Z).
  - The next box gain needs a new mechanism, not more tuning. That is v2 work, after P-FREEZE.

**§55.3 Lane queues until the package.** These replace playbook §5. Work top to bottom; stamp every line with `logline.py`; read the rulings at every loop.

- **EVAL-AUDIT** (session platinum-airedale):
  1. **F-E1. Verify K7, K8 and K9 by 16:00Z** (E1 as written: own-scorer M1 row, margin, OFF identity, suite by name, flipped goldens).
     - A failed keep gets the log line "ESCALATE: Kn failed <leg>", and the build lane reverts it (4.6).
  2. **F-E2. Independent identity of the FINAL STABLE**, after the build lane logs it:
     - the on-disk hash equals the snapshot;
     - TUNE 1728/1728 on objects + cand_log + events, FINAL against the verified parent;
     - the unmodified suite by name.
     - Log "FINAL STABLE VERIFIED <hash>".
  3. **F-E3. `GATE_PACK_FINAL_<hash>.md` by 20:00Z**, in the GATE_PACK_C1 format:
     - M1 rows with the day-bootstrap CIs against v0 (§34.4), saying where a pass rests on the point estimate alone;
     - the clutter median and the margin;
     - bracket@1, reported but outside M1;
     - the six §34.3 diagnostics, with any edge-stability regression named;
     - the K7–K9 table with flipped goldens;
     - the rejected C-2 arms;
     - the fixture conflict (FIXTURE_CONFLICT.md);
     - the box gap, summarized from BOX-LAB's dossier.
  4. **F-E4. The M2 pack on the FINAL hash**, per M2_PACK_PLAN.md:
     - 48 engine items + 30 golden controls + 24 audited negatives = 102 items;
     - validity per R28–R31; the seed, the hash, the τ list and the mix logged in VERIFY_LOG;
     - output: PNGs + `manifest.json` (item id → file, **no key**) in `evalcheck/M2_PACK_<hash>/`; the key stays outside the pack, as M2_PACK_PLAN.md says.
     - F1 is behaviour-neutral, so you may build the items from the verified parent's cache now and stamp the FINAL hash once F-E2 passes.
     - The Lead publishes the answer page.
  5. **F-E5. Review the build lane's ceiling kit (F-B3):**
     - it is blind: no engine ink, no author ink, no titles, no key;
     - the stated seed reproduces the panel list;
     - the axis JSON is correct on 2 spot panels (a known candle's high and time map to the right pixels).
     - Log the seed and the panel list in VERIFY_LOG (protocol §Panels).
  6. **F-E6. `HOLD_PROCEDURE.md`**, a pre-registration written **without reading HOLD**. It fixes:
     - the exact hash, the scorer and the HOLD panel list with its sha256;
     - the metrics and the decision rule ("the thresholds the Owner sets");
     - one run only, and who runs it;
     - the seal check before and after.
  7. **F-E7. E2 null review** (density-matched null; close_ext circularity), for the record and for v2.
  - **Due:** F-E4, F-E5 and F-E6 by 23/09 00:30Z.
- **Build** (session longing-animal):
  1. **F-B1. No engine edits from now.** Wait for the F-E1 verdicts. Revert any failed keep (4.6) and re-snapshot.
  2. **F-B2. Merge F1** (`_scratch/perf/`) onto the verified parent:
     - your own identity: TUNE 1728/1728 against the parent (canonical objects + cand_log + events), plus the unmodified suite by name;
     - snapshot to `_scratch/freeze_candidates/<hash>/` with SHA256.txt;
     - log "FINAL STABLE <hash> = STABLE 9acaa206 + K7 + K8 + K9 + F1" with the one-screen status (R43 §43.4 item 4). Target 17:30Z.
     - **Fallback:** if identity fails and the cause is not found in 30 minutes, the FINAL STABLE is the verified parent without F1. Log it; F1 waits for v2.
  3. **F-B3. The human-ceiling kit**, render-only, per `evalcheck/HUMAN_CEILING_PROTOCOL.md`. Target 21:00Z.
     - Write the sampler's seed in your log BEFORE you draw the panels. Stratify as the protocol says: 4 EU / 3 US / 3 Asia; 5 sparse / 5 busy; at least 2 M1 families per panel.
     - One base render per panel: candles, EMA25, faint 00/50 grid, bars stopping at τ, a dashed τ divider. Use the judge-pack path (`plausibility.render_item` base + `_render_v2`). No engine ink, no author ink, no titles.
     - Per panel, write a PNG and an axis JSON: the plot rectangle in pixels, pixel ↔ bar open time, pixel ↔ price, and the τ bar's time.
     - Write to `research/perception/ceiling_kit/` (kit) and `research/perception/_ceiling_key/` (panel → goldens mapping, kept out of the kit).
     - Do not write into `evalcheck/`; EVAL-AUDIT reviews the kit (F-E5).
  4. **F-B4. `FREEZE_STATUS.md`**: one page of facts:
     - the frozen hash and file list, and the flags ON;
     - the M1 row;
     - the known limits: the box gap, the fixture conflict, ink about 3× the author's, drawing that follows the calendar (SCALE C-1).
  5. Then write "FREEZE QUEUE DONE", append `pause build` to `_scratch/tools/lane_keeper.ctl`, write the HANDOVER line and end the job.
- **BOX-LAB** (session woolen-bugle):
  1. **F-X1. `boxlab/BOX_GAP_DOSSIER.md` by 16:30Z**, for the Owner's box decision and for v2:
     - the funnel: 119 → 107 causally reachable → 57 covered → 10 hit, with the buckets;
     - every C-1/C-2 box arm, one line each with its verdict;
     - the levers left, and why each is banned by 3.6 or trades other families;
     - the one or two v2 mechanisms you would try first, with the evidence.
     - No engine edits; lab code stays flagged OFF.
  2. Then log "BOX-LAB CLOSED", append `pause box-lab` to `lane_keeper.ctl` and end the job. This overrides playbook §9's "never end early" for this lane only.
- **SCALE:** after "FINAL STABLE VERIFIED", the Lead relaunches SCALE in the slot BOX-LAB frees, for the final census on DESIGN 2016–2021 (outcome-blind).

**§55.4 Calendar.** This replaces playbook §7. The order is fixed; the times are targets.

| time (Z) | step |
|---|---|
| now | engine code closed |
| 16:00 | K7–K9 verdicts (F-E1) |
| 16:30 | BOX_GAP_DOSSIER (F-X1) |
| 17:30 | FINAL STABLE (F-B2) |
| 18:30 | FINAL STABLE VERIFIED (F-E2) |
| 20:00 | GATE_PACK_FINAL (F-E3) |
| 21:00 | ceiling kit (F-B3), then EVAL-AUDIT's review (F-E5) |
| 23/09 00:30 | M2 pack (F-E4) and HOLD_PROCEDURE (F-E6) |
| 23/09 01:00 | the Lead publishes the Owner's answer pages and the P-FREEZE package, in Vietnamese (08:00 in Ho Chi Minh City) |
| 23/09, the Owner's day | ceiling kit (~30 min), M2 pack (~40 min), two decisions (fixtures; the box criterion) |
| after his answers | EVAL-AUDIT scores M2 and the ceiling. The Lead proposes end thresholds at or below the ceiling, and the Owner confirms them. HOLD opens once (§55.6), and the Lead writes the P-FREEZE verdict. |

**§55.5 The ceiling comparison.** HUMAN_CEILING_PROTOCOL.md pairs two human drawers: the Owner and one other person, or the Owner twice more than 24 h apart. A second sitting would push the ceiling to 24/09 at the earliest. The scoring therefore reports two numbers:
- **(a) The Owner against the author's goldens** on the same panels.
  - It is ready after one sitting.
  - It uses the same information the engine has: bars up to τ, scored against what the author drew.
  - It is the number directly comparable with M1.
- **(b) Human–human agreement**, as the protocol defines it, if a second drawing exists.
- The Owner chooses which one sets the end thresholds.
- **Memory caveat.** The Owner may remember some of the book's figures, which would inflate (a). The answer page gives each panel a "tôi nhớ hình này" (I remember this chart) box. Panels he ticks are reported separately.

**§55.6 HOLD stays sealed.** It opens once, at the Lead's go, per HOLD_PROCEDURE.md, and only after:
- the Owner's M2 answers are scored;
- the end thresholds are set by him.
No lane reads HOLD before that.

**§55.7 Devin.** The cap is 7 in total (4 W11 + 3 PA-PRO); the keeper keeps `capPaPro = 3`.
- A lane may append one line, `pause <its own lane>`, to `lane_keeper.ctl` when its freeze queue is done. It writes nothing else in that file.

**§55.8 The 20-item judge pack is retired.** Artifact QhDaHmne88q13RaptSgDfJ, on `9283b389`, has no answers. It was a baseline read, not a pass/fail (§34.4), and the 102-item M2 pack on the FINAL hash replaces it. This saves the Owner a sitting.

**§55.9** No lane changes M1, M2, their thresholds, the ruler, the fixtures or the spec. The Owner decides P-FREEZE, the box criterion, the fixture conflict and the thresholds.

## Ruling 56 (14:41Z 22/09) - the Owner rejects the freeze: the machine is wrong on boxes, so Devin researches a different approach; R55's freeze is withdrawn; C-round 3 is a box research round

**§56.1 The Owner's words.** After the Lead reported R55, the Owner wrote:

> "em làm vầy là sai, nếu máy bắt sai, hãy kêu devin research và tiếp cận cách khác đi em"
> (this is wrong; if the machine gets it wrong, have Devin research it and take a different approach)

- **The Lead misread "chốt ngay bây giờ".** R55 §55.2 to §55.8 are withdrawn:
  - no freeze;
  - no FINAL STABLE;
  - no M2 pack;
  - no P-FREEZE package on 23/09.
- **Still in force from R55:**
  - §55.1: the Devin cap is 7;
  - F-E1: EVAL-AUDIT verifies K7–K9;
  - F-B2: the F1 merge, but it now lands as STABLE C-2 (§56.5);
  - the null review;
  - the ceiling kit and HOLD_PROCEDURE.md, both at low priority.
- **§55.7 is withdrawn.** No lane pauses itself or ends its job early. Playbook §9 applies again: never end early, and write a HANDOVER line before the timeout.
- **Engine code is open again** under the keep rules of playbook §3.

**§56.2 The diagnosis that forces a new approach.** Two lanes found it independently (BOX-LAB 14:14Z, build 14:31Z). The current box pipeline cannot pick the author's box:

```
candidate scan → hand-weighted salience score → birth gates → budget
```

- The right candidates lose on the score itself: the median gap to the weakest incumbent is −5.83.
- No score term separates right from wrong candidates.
- Opening the gates floods wrong boxes: 112 at zero hysteresis, 2488 with no floor.
- Tuning this pipeline is closed (3.6, 3.7). The next gain needs a different formulation of the problem, not another term in `score()`.

**§56.3 C-round 3 is a box research round.**
- **Goal:** box@1 ≥ 16/119 (v0) on TUNE, with M1 unchanged:
  - level and line lose at most 1 hit each against the parent;
  - the clutter median stays ≤ 5.0.
- **Parent:** `ee2cbf1202db47b6`, and STABLE C-2 (`ee2cbf12` + F1) once it is logged.
- **Keep rules:** unchanged (playbook §3, §4).

**§56.4 BOX-LAB's new mandate: BOX RESEARCH** (session woolen-bugle).
- Work the phases in order. Log at least every 30 minutes, read the rulings at every loop, and never idle.
- **Write-up:** `boxlab/BOX_RESEARCH.md`, one chapter per phase.
- **Files:** you own new files you create (e.g. `box_select_v2.py`). Changes to `salience.py` go through REQUESTS.md (playbook 4.4).
- **R1. Evidence: why the author draws the box he draws** (by 17:30Z).
  1. **The author-vs-engine table**, all 119 box goldens at τ. Per golden:
     - its edges and times;
     - the engine's box@1 pick at τ;
     - the best-matching candidate, if one is covered, with every score term;
     - the funnel bucket.
     - Your unfinished BOX_GAP_DOSSIER becomes this chapter's opening section.
  2. **30 lab renders** in `boxlab/r_renders/`: 10 hits, 10 covered-but-missed, 10 not covered.
     - Each shows the golden box, the engine's pick and the right candidate.
     - Give each one line: what the author sees that the engine does not.
     - Lab renders only. Never write into `evalcheck/`.
  3. **The book, via `book_loader`:** what makes a box "the" box in the author's text (quotes ≤ 15 words, otherwise paraphrase).
     - Tag each golden with the setup its figure illustrates, e.g. pullback-end box, range box, double top, tease or break.
     - **Hypothesis H1:** the author draws the box that matters for the trade at τ.
  4. **A hypothesis table.** Each row is a signal the current features lack, with a paired test: the golden box against the engine's wrong pick in the same panel.
     - **Null for every row:** shuffle the golden label among that panel's candidates, 200 draws.
     - Keep only the rows that beat the null p95.
     - Start from the rows below, and add your own.

| id | hypothesis |
|---|---|
| H1 | trade context: the box price is leaving, or about to break, at τ |
| H2 | a flat EMA25 through the box |
| H3 | rejected probes at the edge that later breaks |
| H4 | a prior leg in ABR (the pullback-end box) |
| H5 | recency: the latest completed structure wins over older ones |
| H6 | box height relative to the day's range or ATR |
| H7 | bar-overlap ratio inside the box |

- **R2. Approaches** (by 19:30Z). Write at least three formulations that are different from "add a term to `score()`". For each:
  - state the rule and every parameter BEFORE you measure anything (3.6);
  - give the test that would prove it wrong;
  - give the expected coverage and conversion, from R1.
  - **A1. Context-first selection:** at τ, choose among live candidates by the trade context (H1 plus the winning rows), not by a global salience score.
  - **A2. Segmentation-first:**
    - split each session into legs and congestions with a rule stated in advance, then draw the congestion that is live at τ;
    - rule families to consider: a Darvas-style box state machine, swing-structure grammar, choppiness or ADX, change-point detection (PELT or BOCPD), a two-state range/trend model;
    - literature seeds: Darvas box; Wyckoff trading range; swing-point clustering (DBSCAN/KDE) for S/R zones; volatility contraction;
    - search the web if your environment allows it, and cite sources.
  - **A3. A small learned ranker** (R40 §40.5):
    - at most 4 features, taken only from hypotheses that beat the null;
    - leave-one-day-out CV and a shuffle control; the reported M1 is the CV number.
    - **The Owner's wall (no ML training on his PC) holds.** Write `boxlab/r_dataset/` and a deterministic numpy fitting script, then log "ESCALATE: A3 ready". The Lead runs the fit in the cloud and returns the per-fold predictions.
- **R3. Prototype** (from 19:30Z).
  1. Implement the most promising rule-based approach behind a flag, OFF ≡ parent.
  2. Run a lab A/B at one hash against the parent: the full M1 row, a day-bootstrap CI, the margin and the flipped goldens.
  3. If 3.1 passes, hand off in REQUESTS.md. The build lane runs the formal A/B within 90 minutes, and EVAL-AUDIT verifies it.
  4. If it fails, log the verdict with numbers and move to the next approach. Allow two variants per approach (3.7).
- **Escalate only per playbook §8.** Before your timeout, write a HANDOVER line.

**§56.5 Build** (session longing-animal).
1. **F-B1.** Wait for EVAL-AUDIT's K7–K9 verdicts, revert any that fails (4.6), and re-snapshot.
2. **F1 merge** (3.5):
   - TUNE 1728/1728 identity against the parent;
   - the unmodified suite by name;
   - snapshot, then log "STABLE C-2 <hash> = 9acaa206 + K7 + K8 + K9 + F1". Target 17:00Z.
   - If identity fails and the cause is not found in 30 minutes, STABLE C-2 is the verified parent without F1.
3. **The research dataset for BOX-LAB, by 18:30Z**, in `boxlab/r_dataset/`:
   - one row per box candidate per τ on TUNE;
   - the cand_log fields and every score term;
   - raw features computed from bars ≤ τ only (BOX-LAB's H list, or the §56.4 list until theirs arrives);
   - the eval_v2 golden-match label, and panel and day ids;
   - a data dictionary.
   - TUNE only. Never HOLD.
4. **The formal A/B of every BOX-LAB hand-off,** within 90 minutes.
5. **Backlog:**
   - carry the winning approach over to levels (the same score starvation, §54.5);
   - the ceiling kit (R55 F-B3, render-only).

**§56.6 EVAL-AUDIT** (session platinum-airedale).
1. **F-E1:** verify K7–K9 (under way).
2. **The F1 identity check** after the merge.
3. **E2 null review.** It now also covers:
   - BOX-LAB's hypothesis nulls;
   - any CV: features from bars ≤ τ only, folds by day, no golden information inside a feature.
4. **Independent re-measure** of every hand-off.
5. **Low priority:** HOLD_PROCEDURE.md.
- No M2 pack until box passes M1.

**§56.7 Calendar.**
- There is no P-FREEZE date. P-FREEZE is proposed only after box ≥ v0 on M1, and then M2, the ceiling and HOLD follow as R34 set them.
- **23/09 01:00Z (08:00 HCMC):** the Lead reports the research to the Owner: R1's findings, the approaches and the first prototype numbers.

**§56.8 Walls are unchanged.**
- HOLD stays sealed.
- No model training on the Owner's PC beyond what §56.4 A3 routes to the Lead.
- pa_slots ≤ 1 per lane, BelowNormal.
- No lane changes M1, M2, their thresholds, the ruler, the fixtures or the spec.

## Ruling 57 (15:03Z 22/09) - hourly check; H5 must be re-tested in its causal form before it shapes R2; K7–K9 confirmed; Devin load is 11 jobs

**§57.1 H5 is partly hindsight.**
- **What H5 measured:** the golden's drawn right edge (t1) against the candidates' span ends, with a +14.4 bar effect against a null p95 of −35.7.
- **Why that is not causal:** the author drew t1 after the fact, so "t1 past τ" is not something a detector can see at τ. The result mixes a real signal (the author's box is the live congestion at τ) with the label's own hindsight. No candidate can end past τ, so the comparison favours the golden by construction.
- **Re-test H5 causally before R2 uses it.** For each covered golden, compare the right candidate with the engine's wrong pick at τ, using only quantities computable from bars ≤ τ:
  - bars from the candidate's last inside bar to τ;
  - whether close[τ] is inside the box or within X of an edge (state X before you measure);
  - the candidate's age at τ.
  - Use the same within-panel label-shuffle null. For any price-position feature, also run the density-aware null (EVAL-AUDIT, 14:45Z).
- **Log H5 twice:** "H5-drawn (descriptive, hindsight)" and "H5-causal". Only the causal form may enter A1–A3 (§56.6).
- **Check the other survivors the same way.** For H4, H6, H10, H1 and H3, check that the golden side of each test uses what was visible at τ.

**§57.2 Noted, no action:**
- **K7, K8 and K9 are CONFIRMED** (EVAL-AUDIT, 14:43Z): own scorer, OFF identity 1728/1728, suite named-seven only.
- **F1 identity is complete:** TUNE 1728/1728 plus the 20-day DESIGN run (build, 14:46–14:49Z). The merge to STABLE C-2 is under way.
- **The density-matched null (EVAL-AUDIT, 14:45Z):** pivot coverage does not beat density (.711 against p95 .763).
  - Pivots are a candidate generator, not evidence for which box to pick.
  - K8 stands on its M1 result.
  - close_ext's earlier pass was circular, as suspected.
- **All three lanes are at R56:** BOX-LAB 14:45Z, EVAL-AUDIT 14:53Z, build 14:59Z. No ESCALATE since 14:42Z. Wall audit clean (EVAL-AUDIT, 15:00Z).
- **The ceiling kit is rendered** (build, 14:42–14:44Z, seed 20260922) and is held for later. The panel ids in its file names must not reach the Owner.
- **BOX-LAB R1, early read (14:56Z):**
  - 62 of 119 goldens have no coverage.
  - H2 is reversed: the author's boxes sit on a sloping EMA, not a flat one.
  - H7, H8 and H9 are dropped.

**§57.3 Devin load.** At 15:01Z there were 11 jobs live: 8 W11 and 3 PA-PRO. The Owner's cap is 7 in total.
- The keeper does not relaunch a PA-PRO lane while the total is at 7 or more. If your job ends, it may stay down until W11 jobs finish.
- So never end early, and write your HANDOVER line.
- The W11 lanes are not the Lead's to touch. The Lead tells the Owner.

## Ruling 58 (16:03Z 22/09) - hourly check; a wall breach: model fits ran on the Owner's PC, so all fits move to the Lead now; the recency evidence; the next mechanism is the birth criterion

**§58.1 Wall breach.** R56 §56.4 A3 said the fit runs in the Lead's cloud. That rule enforces the Owner's wall: no ML training on his PC.
- The build lane did it right: it delivered the dataset and `fit_ranker.py`, and logged "ESCALATE: A3 ready" (15:07Z).
- **BOX-LAB then fitted models itself on the PC:**
  - `r3_lodo` at 15:47Z;
  - `r3_pooled` at 15:55Z;
  - a third run, `r3_final`, from 16:00:14Z. It had used about 2 CPU-minutes by 16:02Z.
- **Stop now.** No lane fits, trains or cross-validates a model on the PC, whatever its size: no LODO fits, no parameter searches, no rankers. Counting rules and running engine A/Bs are fine.
- **Model numbers from the PC runs are not evidence** until the Lead reproduces them in the cloud. The Lead has staged `rows.csv` and both scripts, and reproduces them this hour.
- **If a lane needs a fit:** write the data and the script, log "ESCALATE: FIT <name>", and move on to other work. The Lead runs it at the next check.
- The Lead reports the breach to the Owner.

**§58.2 Noted, no action.** What the research found this hour:
- **The engine's score cannot pick among live candidates.** Over the live pool:
  - argmax score hits 1/115 cells;
  - the youngest live candidate hits 15/115;
  - youngest plus touches hits 16/115.
  - Source: build lane 15:16Z, reproduced by EVAL-AUDIT 15:20Z. This is counterfactual only: floors, incumbents and clutter are not priced in.
- **H5-causal survives** on both designs and against the density-aware null: px_in_box, close_at_box, dist_to_edge, recency, bars_since_touch (BOX-LAB 15:48Z). EVAL-AUDIT reproduced the directions at 15:18Z, but on only 12 pairs, so the evidence is thin.
- **A1's live-scope gate is REJECTED:** M1 was flat, because stale-at-birth candidates are 1 in 309.
- **Every generation-side rule so far is falsified:** A2 ×2, A2' ×5, live_emit, pivsup, deeper, wick_birth.
- **STABLE C-2 is `4c2df34d7a2a8ee3`** (verified 15:08Z). GATE_PACK_C2_4c2df34d.md was written at 15:16Z.

**§58.3 The next mechanism.** 3.7 allows it because BOX-LAB's 15:58Z diagnosis names a different mechanism: the birth criterion.
1. **A1v2 `box_young_first`** (@97061ac5) is running. Finish it and log the verdict. It is A1's second and last variant.
2. **If A1v2 fails because the right candidates never clear the 5.0 floor, the next arm is A4:**
   - the BOX birth slot admits candidates by liveness order among current candidates (BOX-LAB's spec in REQUESTS.md, 15:58Z);
   - the floor drops to a sanity minimum, stated before the A/B;
   - the order comes from a stated rule, e.g. min bars_since_touch with dist_close_edge as the tiebreak, with no fitted weights.
3. **If A3's fitted order is ever used in the engine,** its weights come from the Lead's cloud fit: frozen, one set, stated in the hand-off.

**§58.4 A tries ledger.** Many rules are being tried on the same 198 TUNE panels.
- BOX-LAB keeps a ledger in BOX_RESEARCH.md: every rule or arm tried, offline or A/B, with its parameters and its result.
- The final report must say how many were tried. HOLD stays the one-shot test of all of them.

**§58.5 Devin.**
- At 15:44Z the total was back to 6 (3 W11 + 3 PA-PRO).
- The build lane ended two jobs early (HANDOVER at 15:17Z, then job 77d13f). The keeper relaunched it at 15:38Z and 15:56Z.
- Never end early. When your queue is empty, watch REQUESTS.md and work the backlog.

## Ruling 59 (16:10Z 22/09) - the Lead's cloud fit reproduces A3 exactly, but a stated recency rule does as well without any fitting, so A3 closes; the strict label disagrees, so only M1 A/Bs decide; the §58.3 example order is withdrawn

**§59.1 A3 reproduced in the Lead's cloud** (`boxlab/c1_runs/lead_cloud_A3.txt`; rows.csv sha256 `8a7ff75c1179fce7`; r3_fit.py `73f56159398daa2c`):
- MODEL CV cell@1 = 18/57 = .316, against a shuffle p95 of .298: PASS, and byte-identical to BOX-LAB's run.
- Baselines: score_last 5/57 and box_rank 5/57.
- **The shuffle control is lenient.** The features were chosen with the true labels, and the null does not repeat that choice. A model trained on shuffled labels with the same four features still reaches about .30, so almost all of the skill comes from which features were chosen, not from the fitted weights.

**§59.2 Stated rules with no fitting** (the same pooled set, expected cell@1 with random tie-breaks):

| rule | label_edge (57 cells) | label_golden, strict (14 cells) |
|---|---|---|
| chance (random pick) | 6.4 | 2.1 |
| engine score_last | 5.0 | 3.0 |
| recency (min recency_bars) | 19.2 | 1.0 |
| recency, then age | 21.5 | 1.0 |
| youngest (min age_bars) | 17.9 | 0.0 |
| close_at_box | 12.6 | — |
| min bars_since_touch | 11.8 | — |
| min dist_close_edge | 6.7 | — |
| touch, then edge (the §58.3 example) | 6.7 | — |

- **A3 closes.** A stated freshness rule (recency, age) matches or beats the fitted model. No fitted ranker is needed, so no model fits run anywhere for boxes this round.
- **The §58.3 example order is withdrawn.** "Min bars_since_touch, then dist_close_edge" scores at chance (6.7/57). Distance to the edge is a poor key.
- **The engine's own score picks worse than chance** among the live candidates (5.0 against 6.4).

**§59.3 The strict label disagrees.** On label_golden (the eval_v2 match, 14 cells), the freshness rules score 0–1 of 14, below both chance and the engine.
- **Likely cause:** a fresh candidate has the right edges but covers only the latest part of the author's episode, so it fails the ruler's span IoU ≥ .5.
- DATA_DICT notes that label_golden is conservative, because candidates carry no containment window, so it may undercount.
- **Either way, offline counts on label_edge are not M1.** Only engine A/Bs scored by the ruler decide.
- Any freshness arm must also report its effect on the span, e.g. the box's left edge: a fresh candidate may need to be extended back over the episode to match what the author draws.

**§59.4 Noted:**
- **A1 is CLOSED** after 2 of 2 variants. `yng_on` was flat: reordering births cannot create a birth that the floor or the rate gate kills.
- **`lvb_on` (@29de0689) is running.** It births BOXes only while the close is inside the band or within 0.5 ABR of an edge. It is a new mechanism (the birth gate), so 3.7 allows it.
- **In 80 of 115 cells the engine's top box-family object at τ is a CONTEXT_RANGE,** not a BOX (DATA_DICT, pick_type). Every A4 arm must report what it does to that envelope-versus-box contest. That is the same contest as the fixture debt (R54 §54.4).
- **Tries ledger (§58.4):** the Lead's cloud check added 13 single-key rules and 3 composite rules, all offline. BOX-LAB adds them to the ledger.
- **BOX-LAB wrote a HANDOVER at 16:05Z and may end its job.** The keeper relaunches it; the total is under the cap.

## Ruling 60 (17:03Z 22/09) - hourly check; C-3 phase 1 is closed (43 tries, every mechanism falsified); phase 2 goes where the known box hits are: v0's event routes, first as an offline hybrid count, then as an engine arm; EVAL-AUDIT splits the misses into time and price failures

**§60.1 Phase 1 is closed.** 43 tries, counted in BOX_RESEARCH.md's ledger:

| class | count | result |
|---|---|---|
| generation rules | 15 | all dead |
| selection mechanisms | 7 | all closed by A/B or arithmetic: scope, order, gate, containment, edge, recency, positional staleness |
| lifecycle mechanisms | 2 | closed |
| A3 fit | 1 | closed (R59) |

- **Verdicts** (EVAL-AUDIT confirmed each): A4v1 inert; A4v2 box −2; lvb and yng flat.
- **The diagnosis, confirmed three ways** (BOX-LAB 16:44–16:57Z, build 16:48Z, EVAL-AUDIT 16:52Z):
  - The right candidates die before birth. No right box is born and then missed.
  - At τ, the box-family rank-1 is usually an envelope with the golden's height, anchored to structure the author never drew (only 6 of 61 have band-IoU ≥ .3 against any golden in the panel). Nothing better sits beneath it.
  - The 20 right candidates that are born are fresh fragments, at a median of 0.11× the golden's span, and all fail the strict match.
- **Two more PC fits:** EVAL-AUDIT disclosed LODO fits at 16:13Z, run before it had read R58. This is the same breach class. It self-reported, and no further fits have run. The Lead tells the Owner.

**§60.2 Where the known box hits are.** BOX-LAB's v0 table (05:37Z):
- 15 of v0's 16 box hits ride event routes (`pullback_end`, `range_double_*`).
- v1 has a matching object live at τ in only 2 of those 15.
- The seven named fixtures encode exactly those event births. The fixture debt and the box gap are one problem: every earlier cure (ctx_convert, box_prio, fam_context) bought box +1 or +2 and paid for it in level and line hits.
- **Phase 2 asks one question: can event-route boxes be born and ranked first in the box family at τ WITHOUT removing the objects that carry level and line hits?**

**§60.3 Build: the hybrid count first, offline** (read-only on caches; no engine edit until it passes).
1. Compute one M1 row, "v1 with v0's box family": v0's box objects for box@1 and v1's levels and lines unchanged.
   - Clutter is counted on the combined object set per panel: v1's objects minus v1's box-family objects, plus v0's box objects.
   - Report box@1, level@1, line@2, bracket@1, the clutter median and the margin, with day-bootstrap CIs against v0.
   - State now, before running: v0's box objects are taken unchanged.
2. **If the hybrid passes 3.1** (box ≥ 16, the others within −1, clutter ≤ 5.0):
   - port v0's event-route box births and v0's box ordering into v1 behind one flag;
   - run a same-hash A/B and keep per 3.1.
   - Say plainly in the log that box parity would come from v0's logic.
3. **If it fails on clutter,** report how much ink v0's box family adds per panel, and hand the number to BOX-LAB.

**§60.4 BOX-LAB: event-first boxes that do not consume the carriers.**
1. **For the 15 event-route goldens:** what kills v1's event birth at each τ (funnel bucket, and the object holding the slot), and which level or line hits that object carries.
2. **At most two variants, parameters stated first.** An event-route box, when the event fires, becomes box-family rank-1 at τ (spec §5 priority 1) while the incumbent CONTEXT_RANGE stays alive as a level and line carrier (demoted in the box ranking only). Report the extra ink.
3. Hand off per 4.3. The build lane owns `salience.py`, so BOX-LAB writes the spec in REQUESTS.md.

**§60.5 EVAL-AUDIT.**
1. **Split the 109 box misses by the ruler's own match components** (read-only use of eval_v2):
   - price edges within tolerance but the time window fails;
   - time window fine but the edges fail;
   - both fail;
   - no candidate at all.
   - This is for the Owner's information. No ruler change: the ruler is the Owner's.
2. Verify the build lane's hybrid count independently.
3. Standing items: re-measure hand-offs, the null review, the wall audit.

**§60.6 Rules for phase 2.**
- Two variants per mechanism (3.7), and parameters stated before measuring (3.6).
- Every try goes in the ledger.
- No fits on the PC (R58).
- Never end a job early. A lane with an empty queue works its item in this ruling.

## Ruling 61 (00:42Z 23/09) - the machine slept, so C-3 stopped at 17:19Z; the hybrid reaches box parity and fails only on v0's ink, so the event-route birth is ported under v1's budget; the misses are a price-anchor problem, not a timing one

**§61.1 The outage.**
- The lanes worked to 17:19Z. The Owner's PC then slept: the bridge was unreachable from 18:01Z to 00:40Z, and all three Devin jobs ended.
- The keeper escalated at 17:06Z ("lane box-lab ended twice in under 10 min; paused") and then died with the machine.
- Nothing was lost. Every result was in the logs before the stop.
- The Lead cleared the `pause box-lab` line and restarted the three lanes at about 00:55Z, launching them directly because the opencode server was down.
- **Until the keeper runs again, no lane is relaunched automatically.** So never end your job early; if it does end, the Lead restarts it at the next hourly check.

**§61.2 The hybrid count is accepted, and it does not kill the port.**
- Build (17:17Z) and EVAL-AUDIT (17:17–17:18Z, its own code) agree exactly on "v1 with v0's box family":

| row | value | gate |
|---|---|---|
| box@1 | 16/119 (.134), v0 parity, +6 | PASS |
| level@1 | 8/76 (.105) | unchanged |
| line@2 | 20/193 (.104) | unchanged |
| clutter median | 5.67 | **FAIL (> 5.0)** |
| margin | 77/179 (parent 114) | — |

- v0's box family is 6.0 objects per panel (median), +4.0 against v1: 89.7% BOX, 10.3% RANGE_OPEN, and **zero CONTEXT_RANGE**.
- **The gate failed on v0's ink, not on v0's birth criterion.** v0 keeps about six boxes alive; the author keeps about one (box live p90 = 1).
- **So port the birth criterion, not v0's lifecycle.** Build's feasibility check (17:19Z): v0's box births are pivot-event driven, 266 births in 40 panels on `pullback_end` and `range_double_*`, and every one coincides with a v1 SwingBook pivot-confirm within 30 minutes.
  - Hook v1's own pivot stream: on a confirmed pivot, evaluate v0's two routes.
  - Keep v1's budget and lifecycle, so the live count stays at the author's level.
  - The event box takes box-family rank-1 at τ; the incumbent CONTEXT_RANGE stays alive as the level and line carrier.
  - **Target: box ≥ 16 with the clutter median ≤ 5.0.** Report the live-objects-per-panel number in every arm.

**§61.3 The misses are a price-anchor problem.** EVAL-AUDIT's decomposition (17:08Z), on the ruler's own components, over the 109 misses:

| failure | count |
|---|---|
| edges fine, time window fails | **0** |
| time window fine, edges fail | 69 |
| both fail | 38 |
| no candidate at all | 2 |

- The worst edge on the 69 is a median of 21 pips from the golden edge (p25 13, p75 31). These are not marginal misses.
- **Correction to R59 §59.3 and to the 16:48–16:57Z framing:** timing is never the sole failure. The engine's box sits at the wrong price. That is exactly what the author's event routes fix, because they anchor the box to the pivots he reads.

**§61.4 Queues.**
- **Build** (`salience.py`, engine):
  1. Implement the event-route port behind one flag, to BOX-LAB's spec (§61.2). State every parameter before the A/B.
  2. Same-hash A/B against STABLE C-2 `4c2df34d`: the full M1 row, clutter median and margin, live objects per panel, flipped goldens, OFF identity.
  3. Keep per 3.1 if it passes. Two variants at most.
- **BOX-LAB** (`boxes.py`, lab):
  1. Write the §61.2 spec into REQUESTS.md now: which pivot confirms qualify, the two routes' rules, the edge pair, the birth conditions, and what happens to the incumbent.
  2. Then, for the 15 event-route goldens v0 hits, check on the cache that the ported rule would reach them, and say how many.
  3. The ledger continues; the count stands at 43 plus phase 2.
- **EVAL-AUDIT:**
  1. Verify the port's A/B independently.
  2. Give the build lane the per-panel ink budget: how many extra live box objects the clutter median can absorb before it crosses 5.0.
  3. Standing: wall audit, the null review, no fits on the PC.

**§61.5 Unchanged.** M1, M2, the ruler, the fixtures and the spec are the Owner's. HOLD stays sealed. No model fits on the Owner's PC. Two variants per mechanism, parameters stated first, every try in the ledger.

## Ruling 62 (02:03Z 23/09) - the event-route port cures the seven fixtures and fails M1 on ink; the ruler charges every birth, so the author's economy (about one box per panel) is the design constraint; one throttle mechanism is left, then the trade-off goes to the Owner

**§62.1 The three arms, all verified by EVAL-AUDIT:**

| arm | box@1 | level | line | clutter | verdict |
|---|---|---|---|---|---|
| evb_on `be204b98` (both routes, newest event box takes rank-1) | −3 | — | — | 6.00 | FAIL |
| evb2_on `b07b8af4` (double-top route only) | 7/119 (−3) | −1 | −2 | 5.67 | FAIL |
| evb_on `65c8f635` (spec default: propose into the pool, best score takes rank-1) | 10/119 (=) | = | = | 4.33 | inert |

- Live boxes per panel: 5.0 against the parent's 1.0. Margin 80/179 against 114.
- The inert arm is not byte-flat: 4 event objects survive admission, and of 279 `ev_pullback_end` proposals 222 are outranked.
- **BOX recall reaches .213, which is v0's coverage.** The generation problem is solved. What is left is selection and ink.

**§62.2 The structural confirmation.** With event births ON the unmodified suite is 71/72: **the seven named fixtures are cured.** The box gap and the fixture debt are one problem, as R60 §60.2 said. Each arm's single remaining failure is named and expected.

**§62.3 The decisive arithmetic** (build 01:16Z, on EVAL-AUDIT's budget table). The ruler charges ink for every object whose span intersects the window, dead ones included.
- So a supersede economy does not help: about 6.5 event births per panel spend about 6 ink whatever their lifespan. That is v0's profile.
- The budget is **+1 object per panel**.
- **Event births must therefore throttle to about 1 or 2 per panel, six times tighter than the route stream produces.**
- The author draws about one box per panel. The engine has to decide once per episode instead of proposing six times.

**§62.4 The last mechanism of this round: throttled event birth.**
- BOX-LAB states the rule and every parameter in its log BEFORE any measurement (3.6), hands off through REQUESTS.md, and keeps to **two variants at most**.
- The rule must cut births to 2 or fewer per panel while keeping the 12 of 15 reachable event goldens in the candidate stream.
- Shapes worth stating, with your own stream's numbers behind the choice:
  - **(a) one birth per episode:** after an event birth, no further event birth until price has left the envelope by more than X ABR, or K bars have passed. State X and K.
  - **(b) qualifying events only:** birth only when the event's own strength passes a stated bar - a prior leg of at least Y ABR (H4's causal form), or at least two touches on each edge - with the bar chosen so the stream falls to about one birth per panel.
  - **(c) first of the session segment:** at most one event birth per segment, the first that qualifies.
- **Every arm reports:** the M1 row, the clutter median and the margin, **births per panel and live objects per panel**, the flipped goldens, flag-OFF identity and the suite by name.

**§62.5 If the throttle fails, this is a real frontier and it goes to the Owner, not to a fiftieth mechanism.** The evidence is already in hand:
- v0 reaches box 16/119 while drawing clutter 9.00. The cap is 5.00. **v0 buys its box recall with ink.**
- The engine matches v0's box coverage the moment event births are on, and breaks the cap in the same step.
- So "box ≥ v0 with clutter ≤ 5.0" may be infeasible under the current ruler. The Owner's options are then: accept a box gap at P-FREEZE; raise the clutter cap; or change what clutter counts (live objects at τ instead of every object intersecting the window).
- All three are his: they are thresholds and the ruler. No lane and not the Lead touches them. The Lead prepares the numbers.

**§62.6 Housekeeping.**
- The keeper died again (PID 14280, at about 01:2xZ) and was restarted (PID 31476, 02:02:30Z). It had paused build and box-lab under the two-short-jobs guard, so the Lead relaunched those two directly.
- **Lanes: stop ending your job when your queue empties.** Work the standing backlog, keep logging, and wait for the next ruling inside the same job. Two jobs under ten minutes pauses your lane and costs the round an hour.

## Ruling 63 (02:16Z 23/09) - the frontier is reached: no stated throttle keeps the event goldens at the author's economy; the decision goes to the Owner; EVAL-AUDIT prices option C (clutter counted at τ) so he chooses with all three rows

**§63.1 BOX-LAB's throttle matrix (02:15Z) is accepted as the round's last result.**

| throttle | event births per panel | reachable event goldens (of 15) |
|---|---|---|
| raw event stream | 6.5 | 12 |
| update-in-place, one object (T1) | 1.0 | 5 |
| touch-defer S=80 / 200 | 2 / 1 | 2 / 0 |
| governing-release X = .5–3 ABR | 5.5 → 1.8 | 1 |
| dedup D = 5 / 8 / 12 pips | 13 / 9 / 6 | 11 / 8 / 6 |
| leg floor, growth-supersede, other update-in-place forms | 1–7 | 0–5 |

- No stated shape reaches 2 or fewer births per panel while keeping the 12.
- The matching candidate is causally indistinguishable on leg, prominence, pair separation, span, touches and stream order.
- These were offline negatives, so nothing is kept and no forking-paths risk arises. Every row goes in the tries ledger.

**§63.2 The frontier (R62 §62.5) goes to the Owner.** The Lead lays out three options and keeps all three open until he chooses:
- **(A) Accept the box gap.** Box 10/119 against v0's 16; level, line and clutter pass. P-FREEZE then proceeds to M2, the human ceiling and HOLD.
- **(B) Raise the clutter cap.** The hybrid (v1's levels and lines plus v0's box family, unchanged) scores box 16/119, level 8/76, line 20/193, clutter 5.67. A cap of 5.7 or higher passes M1 at once. The build lane then ports v0's box family wholesale (births, lifecycle and ranking) behind one flag and runs the same-hash A/B.
- **(C) Count clutter at τ.** Count only the objects live at τ - what is actually on the screen when the decision is made - instead of every object whose span touches the window. No number exists for C yet. EVAL-AUDIT prices it now (§63.3).

**§63.3 EVAL-AUDIT, now:** the live-at-τ clutter median and margin (information only; the ruler does not change) for:
1. the parent, STABLE C-2 `4c2df34d`;
2. the hybrid (v1 + v0's box family);
3. the event-port arms: evb_on `be204b98` and evb2_on `b07b8af4`;
4. BOX-LAB's T1 throttle, if it can be computed from the cache.

- Report each row beside today's clutter definition. Post it in VERIFY_LOG and REQUESTS.md by 03:30Z.

**§63.4 Build, while the Owner decides:**
- Prepare, but do not run, the option-B port: v0's box family moved wholesale behind one flag, with v0's own births, lifecycle and ranking.
- Check flag-OFF identity when the code is written.
- If the Owner picks B, the A/B can start within the hour.

**§63.5 BOX-LAB:** a one-page `boxlab/FRONTIER.md` for the Owner, in plain words:
- what the event routes are;
- why their births cost ink;
- the throttle matrix;
- why the right box cannot be picked from the stream by any causal rule tried.
- Keep the ledger current.

**§63.6 Unchanged:** M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's. HOLD stays sealed. No model fits on the Owner's PC. Never end a job early.

## Ruling 64 (02:23Z 23/09) - the Owner asks for deep research before choosing; a fresh DR-BOX lane opens; BOX-LAB pauses and its frontier page folds into the DR report

**§64.1 The Owner's words.** After the Lead laid out options A, B and C at about 02:17Z, the Owner wrote: "thế thì hơi khó, nhưng anh muốn em kêu devin deep research thêm vụ này đi em" ("that is hard, but I want Devin to do deeper research on this").
- **The A/B/C choice is deferred until the deep research reports.** No option is taken, and no threshold or ruler changes.

**§64.2 A new lane, DR-BOX,** runs in a fresh Devin session, so that someone with no stake in the 70 tries looks at the problem.
- **Its question:** is the author's choice of box predictable from information available at τ? If yes, from what information, and by what rule? If no, prove it and quantify the part that cannot be predicted.
- **Its plan, in stages:**
  - D1: literature;
  - D2: the book, figure by figure;
  - D3: new hypotheses tested null-first. The key one is **H-hind**: does the author pick, with hindsight, the box that led to a trade?
  - D4: a causal upper bound;
  - D5: a report ending in a plain-language summary for the Owner.
- **Output:** `research/perception/deepresearch/` (DR_LOG.md, DR_BOX_SELECTION.md). Timebox 6 hours.
- **Walls:** research only, with no engine edits; no model fitting on the PC; TUNE and DESIGN bars only; post-τ bars only inside the panel's own window, and only to test hypotheses, never as a feature; HOLD sealed; the book through `book_loader` only.

**§64.3 BOX-LAB pauses** (`pause box-lab` in the keeper ctl). This keeps the seventh Devin slot for DR-BOX: 4 W11 + build + EVAL-AUDIT + DR-BOX = 7. The one-page FRONTIER.md from R63 §63.5 becomes a section of the DR report.

**§64.4 The other lanes carry on:**
- EVAL-AUDIT prices option C: clutter counted live at τ (R63 §63.3), due 03:30Z.
- Build prepares the option-B port without running it (R63 §63.4).
- Both lanes answer DR-BOX's data questions, which it posts in `boxlab/REQUESTS.md`.


## Ruling 65 (02:45Z 23/09) - the Owner lifts the Devin job cap; the only rule left is no heavy work on Devin and no heavy runs in parallel; BOX-LAB returns as DR-BOX's independent checker

**§65.1 The Owner's words** (about 02:40Z): "bỏ vụ giới hạn devin đi em, chỉ có rule là cấm dùng devin cho tác vụ nặng như orc, chạy task nặng mà song song thôi" ("drop the Devin limit; the only rule is: no Devin for heavy tasks like OCR, and no heavy tasks run in parallel").
- **The job-count caps are gone:** the total cap (6, then 7) and the PA-PRO cap of 3.
- The lane keeper no longer counts jobs. Its short-job guard stays: a lane whose last two jobs each ended in under 10 minutes is paused, with an ESCALATE line.

**§65.2 The rule that replaces the cap.**
- **(a) No heavy task on Devin.** Heavy means the OCR class:
  - OCR, or rendering the book's pages at scale;
  - model training or fitting (the R58 ban stands);
  - GPU work;
  - bulk downloads;
  - multi-core sweeps.
- **(b) Heavy runs never run in parallel.** A heavy run is any of these:
  - a full-corpus ruler or engine run;
  - a cache rebuild;
  - any script expected to run longer than 3 minutes or to use more than one core.
- **Every heavy run goes through the lock:** `python research/perception/tools/heavy_run.py --lane <your lane> -- <command>`. The tool:
  - holds the one PA-PRO heavy lock;
  - runs the command at BelowNormal, with one thread per math library;
  - logs to `research/perception/tools/heavy_run.log`;
  - frees the lock by itself if the process dies.
- **If the lock is held,** the tool waits and logs the wait, and the lane does light work meanwhile. If the tool gives up (exit code 75), retry later.
- **Never bypass the lock,** and never start a second heavy run from the same lane. `--status` shows who holds the lock.
- **(c) Light work runs freely in parallel across lanes:** reading, writing logs, single-panel checks, and small pandas work on existing pickles.
- **Scope:** the W11 lanes are the Owner's and sit outside this lock. `pa_slots <= 1` and BelowNormal stay.

**§65.3 BOX-LAB resumes with a new role: DR-BOX's independent checker.** Builder is not reviewer, and that holds for research too. BOX-LAB's queue was empty, so it gets these items, in order.
1. **Reconcile the reach number.**
   - DR-BOX logged at 02:34Z that the event stream reaches 51/119 box goldens at τ (edge match, born ≤ j_τ).
   - BOX-LAB's reach check found 12/15 on the v0-hit subset, and the throttle matrix (R62) worked on the event goldens reachable in that subset.
   - The two numbers answer different questions, and only the ruler's match decides.
   - Recount with the ruler's own match code (eval_v2 `50e11fd5`, imported, never copied): how many of the 119 box goldens have at least one event candidate, born at or before τ, that the ruler would score as a hit if it were ranked first?
   - Report the count, the list, and exactly where DR-BOX's definition differs (edge tolerance, time window, family, τ).
   - Write it to `boxlab/DR_CHECK.md`.
2. **If the ruler-exact reachable set is larger than R62's,** redo the throttle matrix on the larger set: how many goldens survive at 1 and at 2 births per panel. State the throttle rules before measuring; add no rule after seeing the answer. Enter each rule as a try in the ledger.
3. **Recompute DR-BOX's numbers.** Recompute every numeric claim DR-BOX writes in `deepresearch/DR_LOG.md` or `DR_BOX_SELECTION.md` independently, and log each as "checked" or "differs (why)" in `boxlab/DR_CHECK.md`.
4. **Answer DR-BOX's data questions** in `boxlab/REQUESTS.md`, alongside build and EVAL-AUDIT.
- **Walls unchanged:**
  - edit only `boxes.py` (flagged code) and `boxlab/*`;
  - no model fits;
  - HOLD sealed;
  - every heavy run through `heavy_run.py`.

**§65.4 DR-BOX.** Its 51/119 reach number is provisional until BOX-LAB's ruler-exact count lands. When DR-BOX reads this ruling, it reads `boxlab/DR_CHECK.md` at every loop, and cites the checked number rather than its own where the two differ.

**§65.5 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- A/B/C stays deferred until DR-BOX reports.
- HOLD stays sealed.
- No model fits on the Owner's PC.
- Never end a job early.

## Ruling 66 (03:05Z 23/09) - the frontier moved: a single persistent event box reaches v0 box parity at the author's ink; the level stream is now the only M1 blocker; build tries a level decoupling (2 stated variants); DR-BOX's report is accepted with one correction

**§66.1 What the Lead missed at R63/R64, now on the record.** Build ran the R62 §62.4 UIP arms at 02:27–02:39Z (PERCEPTION_LOG). EVAL-AUDIT verified them independently at 02:47Z (VERIFY_LOG, own scorer, OFF-identity 1728/1728).

`uip2_on` (`ev_uip_persist`: one event object per panel, rd candidates rewrite lo/hi/t0 in place, close-exempt), measured at `6d955783` against the C-2 parent:

| family | result | change from parent | M1 bar |
|---|---|---|---|
| box@1 | **16/119 (.134)** | +6, **v0 parity** | met (≥ .134) |
| level@1 | **4/76 (.053)** | −4 | **fails** (needs ≥ .066) |
| line@2 | 23/193 | +3 | met |
| bracket | 29/85 | 0 | — |
| clutter | **4.67** | margin 95/179 | met (≤ 5.0) |

- Births: exactly 1.0 per panel.
- Suite: 71/72. The named seven fixtures are cured. `test_pullback_end_box_birth` fails, because the rd-only spec never lets the pullback route write.
- Keep rule: FAIL on §3.1b, because level −4 exceeds the −1 allowance.

**Why this matters.** This is the first arm ever to reach the box bar at author-level ink. R63's premise, that box parity costs ink we cannot afford, is superseded. **The frontier is now box versus level, not box versus ink.**

**The mechanism of the level loss** (build 02:41Z, from the cache): the loss is at the pick.
- (a) The mutating box's edges seed competing LEVEL_CARRIED objects that outrank the correct level (9.40c).
- (b) The persistent box keeps level presence off the screen at τ (9.61c has zero live levels).

**§66.2 DR-BOX's report (`deepresearch/DR_BOX_SELECTION.md`, 03:00Z) is accepted.** BOX-LAB recomputed it independently (`boxlab/DR_CHECK.md`): every core number reproduces exactly or within a definitional hair.

**One correction for everything the Owner reads.** The reachable set is **46/119 ruler-exact**, not 51. DR-BOX's 51 counts edges only. Five goldens (9.6a, 9.13a, 9.32b, 9.36b, 9.53a) match on edges but fail the ruler's span test.

Findings the programme now takes as settled:
- **H-hind is rejected.** The author does not draw the box that breaks first or runs furthest after τ: that rule finds the golden only 2–6 times out of 51, below random.
- **Youngest-born** (keep the freshest) is the only causal rule that survives every null: 20/51 on edges.
- **At least 17/51** reachable goldens are indistinguishable under every stated causal feature and conjunction.
- The largest loss pool is **reach**: 68/119 goldens never get an edge-matching candidate.
- BOX-LAB's throttle matrix on the 46 set: the best one-birth rule keeps **14/46, about 30%**, the same law as R62.

DR-BOX's recommendation 4 (optimise the engine's own precision rather than golden matching) would change the programme's goal. It is **the Owner's call**. The Lead reports it and does not act on it.

**§66.3 Build, now: one mechanism, "UIP object invisible to the level family", two variants.** State both parameter sets in PERCEPTION_LOG before measuring (§3.6). Run on the current tree, same-hash, against the C-2 parent and against `uip2_on`.

- **V1 `uip2_lvfree`** = `uip2_on`, plus:
  - (a) the UIP object's edges never seed or count as LEVEL_CARRIED or MINI_LEVEL candidates;
  - (b) the UIP object is exempt from every shared or joint structure cap and slot that can block or evict a level (it is counted as box ink only).
  - Nothing else changes.
- **V2 `uip2_lvfree_pb`** = V1, plus `pullback_end` candidates rewrite the UIP object too (BOX-LAB's UIP-all rule).
  - Measured headroom: UIP-all 14/46 versus UIP-rd 13/46 ruler-exact; DR-BOX youngest-either 20/51 versus rd 18/38.
  - It is also expected to cure `test_pullback_end_box_birth`.
- **Report for each arm:**
  - the M1 row, clutter and margin;
  - births and live objects per panel;
  - level flips against the parent;
  - the suite;
  - OFF-identity.
- **Keep rule is unchanged (§3.1, §3.4):**
  - box up;
  - no other M1 family down by more than 1;
  - clutter ≤ 5.0;
  - no new test failure outside the known seven. A failing `test_pullback_end_box_birth` blocks a keep; it does not block the measurement.
- **Heavy runs go through `heavy_run.py`** (R65).
- **Priority.** This comes before the option-B full canonical check. The option-B port stays prepared and unrun; the Owner has not chosen B.
- **If both variants fail,** log the mechanism of the failure, then stop this direction (§3.7).

**§66.4 Queued after §66.3 (not before), one at a time on whatever parent stands:** the episode-anchored `build_start`. Walk back from t0 while bars overlap the band. Measured by DR-BOX and BOX-LAB: span IoU ≥ 0.5 goes from 9 to 14 of 20 rule-hits. BOX-LAB writes the exact spec in REQUESTS.md, with parameters stated.

**§66.5 EVAL-AUDIT.** Verify §66.3 independently, as for the UIP arms. Report option C's rows for the V1 and V2 arms beside today's clutter definition (information only; the ruler does not change).

**§66.6 BOX-LAB.** Keep DR_CHECK current. Write the §66.4 spec. Pre-register, in the ledger and before build measures, what you expect V1 and V2 to do to level@1, and why. That lets us see whether the level mechanism is understood.

**§66.7 DR-BOX.** Its core report is done. If its job runs on, it continues D2/D3 detail only; no engine edits. It cites 46/119 wherever it states reach.

**§66.8 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- A/B/C stays deferred. If §66.3 keeps an arm that passes M1 under today's ruler, options B and C become unnecessary for the box. The Lead will tell the Owner either way.
- HOLD stays sealed. No model fits on the Owner's PC. Never end a job early.

## Ruling 67 (03:35Z 23/09) - the Owner keeps all capacity on perception; no economic-probe lane; a new ARCH lane designs Perception Architecture v2; every measured arm gets one machine-readable row; BOX-LAB specs a second birth channel for episode containers

**§67.1 The Owner's words** (about 03:30Z): "mắt rất quan trọng vì đây là phần khó nhất, nếu thành công nó là 1 thứ có edge vì bob volman đã có lợi nhuận ổn định và chứng minh. nên là tập trung vô kiến trúc nhận diện và vẽ line, box,... theo bobvolman". In English: perception is the hardest part and, if it succeeds, it carries the edge, because Volman's trading is proven; so focus on the architecture that recognises and draws lines, boxes and the rest the way Volman does.
- **Decision:** there is no economic-probe lane. Charter Addendum 4 (perception first) stands.
- All PA-PRO capacity goes to recognising and drawing Volman's objects: boxes, levels, lines, brackets and markers.

**§67.2 One machine-readable row per measured arm.** From now on, every A/B, independent verification, or lab count that reports M1 numbers also writes one row with `research/perception/tools/result_row.py add ...` into `research/perception/status/results.jsonl`.
- **What goes in a row:** lane, arm, hash, parent, the M1 counts as hits/total, clutter, margin, births, suite, OFF-identity, a verdict, and who produced the number. `--by self` means the lane's own number; `--by <lane>` means an independent check.
- **Rules:** the time comes from the clock. A correction is a new row, never an edit.
- **Why:** the Lead missed the `uip2_on` result for about 20 minutes because it sat in prose. The Lead now reads this table by script at every check.
- The prose logs stay as they are. The Lead has backfilled the reference rows (C-2 parent, `uip_on`, `uip2_on`).

**§67.3 A new lane, ARCH: Perception Architecture v2 (design only).** A fresh Devin session with no stake in the 66 rulings writes to `research/perception/arch/`.

Deliverables:
1. **`ARCH_V2.md`: the target architecture for Volman's drawing grammar.**
   - Per-family pipelines: generate, then lifecycle, then the family's own budget.
   - One display arbiter at the end that enforces the author's economy (about 1 box, 1–2 levels, lines) and the spec §5 priorities.
   - No shared quota between families. The `uip2_on` level loss (−4) is the measured example of why.
   - An incremental per-bar design with bounded cost per bar, fit for a direct MQL5 port.
2. **`FLAG_LEDGER.md`:** one row for each of the 45 boolean flags and each key parameter in `params_v1_1.json`.
   - Each row gives the ruling it came from, its measured A/B result, and its status (KEPT-ON, FAILED-OFF, DEAD, PENDING).
   - Each row proposes the flag's fate: fold it into the code, or quarantine it.
3. **`COUPLING_MAP.md`:** every place where one family's decision reads another family's state (`rate_total`, fam_budget/fam_caps, `joint_struct`, class budgets, NMS, cooldowns). Each place is paired with the measured cases where the coupling cost hits.
4. **`MIGRATION_PLAN.md`:** refactor steps that build can take one at a time. Each step is identity-checkable (OFF ≡ parent byte-for-byte), so M1 cannot move during the refactor.
5. **`PORT_PLAN_V2.md`:** how the kept path maps onto MQL5, with a parity harness. It says which `mql5/*.mqh` modules of the zone era are reused and which are retired.

Walls:
- Read-only on engine files. It writes only `research/perception/arch/*`.
- No A/B runs of its own. It may run read-only counts on the cache, through `heavy_run.py` if they are heavy.
- No model fits. HOLD sealed. The book only through `book_loader`.

Timebox: 6 hours.

Build implements `MIGRATION_PLAN` only after the current §66.3 A/B round closes. It does so step by step, with EVAL-AUDIT checking identity at each step.

**§67.4 BOX-LAB, after it scores its pre-registered lvfree predictions: a second birth channel for episode containers** (DR-BOX recommendation 3). Reach is the largest loss pool: 68/119 goldens never get an edge-matching candidate.

Candidate triggers, all causal and all described in the book:
- the Asia/session range box;
- the post-spike absorption base;
- the first sideways block after a leg of at least N bars.

Method:
- State each rule and its parameters in the ledger before measuring.
- Count offline and ruler-exact:
  - reach on the 68 unreachable goldens;
  - reach on all 119;
  - births and live objects per panel.
- Hand off a spec in REQUESTS.md only if a rule adds reach at no more than about 1 extra birth per panel.
- At most 2 variants (§3.7).

**§67.5 Rulings archive.** R0–R50 have been moved verbatim to `research/perception/LEAD_RULINGS_ARCHIVE_R00-R50.md`, and nothing was deleted. This file now starts at R51 and keeps a pointer line. Citations such as "R34 §34.5" or "R58" are still valid and resolve in the archive.

**§67.6 Unchanged:**
- R66 §66.3 (the lvfree A/B) runs first.
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- A/B/C stays deferred.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`. Never end a job early.

## Ruling 68 (03:40Z 23/09) - first arm ever to meet M1 on all three families; its keep is blocked by one fixture; build fixes the UIP birth semantics (no test edits); BOX-LAB resumes on the reach work

**§68.1 The result.** `uip2_lvfree` at `23504c93` was measured by build at 03:27Z and verified independently by EVAL-AUDIT at 03:33Z (own scorer, OFF-identity 1728/1728 against the C-2 parent):

| | uip2_lvfree | C-2 parent | v0 bar (M1) |
|---|---|---|---|
| box@1 | **16/119 (.134)** | 10/119 | .134 → met (tie) |
| level@1 | **7/76 (.092)** | 8/76 | .066 → met |
| line@2 | **20/193 (.104)** | 20/193 | .093 → met |
| clutter median | **4.33** | 4.33 | ≤ 5.0 → met |
| margin | 111/179 | 114/179 | — |
| births per panel | 1.0 | — | — |

- **This is the first arm in the programme to meet M1 on all three families at the author's ink.**
- Option C row (information only): strict 2.33, loose 3.78. Both pass.
- **BOX-LAB's pre-registration came true.** It predicted V1 level 7–8/76 and V2 box 16–18/119. The level mechanism of R66 is understood, not guessed.
- **V2 `uip2_lvfree_pb` is retired.** Its row and flip set are identical to V1 (+0/−0), so pullback writes add nothing on TUNE. The simpler arm stands.
- **Caveat.** Box ties v0 exactly, so the box margin is zero. EVAL-AUDIT reports confidence intervals for all four rows in the gate pack (§68.4).

**§68.2 One thing blocks the keep: `test_pullback_end_box_birth`.**
- **The suite of record** is the unmodified `tests/test_engine.py` as collected: 72 tests. On it, both arms score 71/72.
  - The named seven fixtures are cured.
  - `test_pullback_end_box_birth` fails, because the UIP persistent object is not a BOX birth inside that fixture's envelope.
- **Build's "67/67"** used a different test selection. Build logs which tests its selection left out and why, and from now on reports the suite of record.
- **§3.4 applies:** a failure outside the known seven blocks a keep. Fixtures and tests are the Owner's; nobody edits them.

**§68.3 Build, now: one targeted fix, "UIP birth semantics".**
- **V3 `uip2_lvfree_pbbirth`** = `uip2_lvfree`, plus one change. While the panel has no UIP object yet, a `pullback_end` candidate may BIRTH the UIP object as a BOX birth, with the event reason recorded, at the moment v0's route would. After the birth, rewrites stay rd-only, exactly as V1.
- **Rules:**
  - State the parameters before measuring.
  - A second variant is allowed only if V3 misses, and it must be stated before it is measured (§3.7).
  - No test, fixture, ruler or spec edits.
- **Report:** the M1 row, the suite of record, OFF-identity, and one `result_row.py` row. Heavy runs go through `heavy_run.py`.
- **Keep** if the keep rule passes and the suite of record shows no failure outside the known seven (ideally 72/72).
- **If the fixture cannot pass without breaking M1,** this becomes a spec-vs-author conflict for the Owner, like the earlier fixture debt. Build writes it up in `FIXTURE_CONFLICT.md`. `uip2_lvfree` stays the candidate meanwhile.

**§68.4 On a keep:**
- Build logs "STABLE C-3 <hash>" with the full canonical check.
- EVAL-AUDIT verifies it and writes `GATE_PACK_C3_<hash>.md`. The pack holds the M1 row with CIs against v0, the option-C row, the suite of record and the flip lists.
- Only after that does the Lead prepare the Owner's next steps under Decision C (R34):
  - the human-ceiling kit (already rendered and held);
  - the M2 blind-precision pack on the new STABLE.

**§68.5 BOX-LAB resumes.** The keeper had short-paused it at 03:22Z because its queue was empty. The queue now:
1. Log the scored pre-registration in the ledger as a hit.
2. Write the §66.4 episode-anchored `build_start` spec in REQUESTS.md, with parameters stated.
3. §67.4: the episode-container birth channel, counted offline and ruler-exact on the 68 unreachable goldens and on all 119, with births per panel.
4. Answer ARCH's data questions.

Loop; never end the turn with work left in the queue.

**§68.6 Lane state:**
- DR-BOX is closed: report done, session `checkered-puffin` kept.
- ARCH runs on (R67 §67.3).
- Every measured arm gets a `result_row.py` row (R67 §67.2). The Lead backfilled the lvfree rows.

**§68.7 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`. Never end a job early.

## Ruling 69 (03:50Z 23/09) - the Owner asks for first-principles research on what drawing lines like a professional really is; DR-LINE is queued to start when build's R68 work closes; essence-first becomes standing practice for every family

**§69.1 The Owner's words** (about 03:45Z): "tìm hiểu bản chất vẽ line như 1 protrader là gì sau khi devin xong phần việc của nó trong phiên đang làm, bản chất > cách lượng hóa mà vẫn đúng và có thể cải thiện tính chủ quan của con người,... đừng để anh phải nhắc nhở về mấy cái cỏn con này".

In English: once Devin finishes the work of its current session, research what drawing a line like a pro trader really is. The essence comes before the quantification, and the quantification must stay true to it while improving on human subjectivity. And: do not make the Owner remind the Lead of things like this.

**The Lead's reading.** This research belonged in the plan without being asked. DR-BOX asked the box version of the question only after the Owner requested it, and nobody asked it for lines or levels. From now on the Lead schedules essence-first research for each object family on its own initiative.

**§69.2 A new lane, DR-LINE** (fresh Devin session, prompt `_scratch/tools/drline_prompt.md`, timebox 6 hours). It writes `research/perception/deepresearch/DR_LINE_LOG.md` and `DR_LINE_ESSENCE.md`.

Scope: sloped lines, horizontal levels, and box edges where the same principle applies.

Stages:
- **E1:** first principles from Volman (book_loader only), other professionals, and academic evidence.
- **E2:** from principles to causal, scale-invariant definitions. Name which human choices are principled and which are arbitrary.
- **E3:** measure three things:
  - (a) fidelity to the golden lines and levels, on TUNE panels, with the ruler;
  - (b) consistency, where the machine can beat human subjectivity: stability, flicker, determinism;
  - (c) validity on DESIGN 2016–2021: reaction at the drawn lines against matched controls, designed with the R01/R02 lessons, and reported as descriptive if the control is not identifiable.
- **E4:** proposals as flagged experiments with stated parameters, plus suggested metrics for the Owner.
- **E5:** a 10-line Vietnamese summary for the Owner.

Walls:
- research and read-only counts only;
- no engine edits;
- no model fits and no OCR;
- no outcomes, PnL or setups;
- nothing from the BOOK window except fidelity;
- heavy runs through `heavy_run.py`.

**§69.3 When it starts.** As the Owner asked, DR-LINE starts after the current session's work closes, meaning build's R68 work. That is the first of:
- "STABLE C-3 <hash>" logged and verified by EVAL-AUDIT;
- `FIXTURE_CONFLICT.md` written for the Owner;
- build's current job ending.

The Lead launches it at the first check after any of these.

**§69.4 Standing practice, essence first.** Before more tuning on any object family, there is one first-principles research note for that family, with principles, definitions and metrics.
- Boxes: DR-BOX (done).
- Lines and levels: DR-LINE.
- Brackets and markers: after DR-LINE.

The Lead schedules these without being asked. The ARCH lane (R67) folds each note's principles into ARCH_V2 when the note lands.

**§69.5 Unchanged:**
- R68 runs first: build's V3 birth-semantics fix, then the keep.
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`. Never end a job early.

## Ruling 70 (04:15Z 23/09) - the fixture clause is withdrawn (its premise was wrong); how STABLE C-3 is chosen; ARCH's drafts go to a neutral review before any refactor

**§70.1 Correction.** The clause in R66 §66.3 and R68 §68.2 ("a failing `test_pullback_end_box_birth` blocks a keep") rested on a wrong premise. The Lead assumed the parent passed that test. EVAL-AUDIT showed at 03:36Z that it does not:
- **The parent `evb_off`** scores 65/72, failing the named seven. `test_pullback_end_box_birth` is one of the seven.
- **`uip2_lvfree`** cures six of the seven and scores 71/72, with no new failure.

The clause is withdrawn. Under §3.4 ("no new failure outside the known seven"), **`uip2_lvfree` passes the keep rule**.

Build's earlier "67/67" is explained: the suite runner collected `PA_Pro/tests/` instead of the perception suite. Build has fixed that (03:56Z). The suite of record stays `research/perception/tests/`, which collects 72 tests.

**§70.2 How STABLE C-3 is chosen.** V3 `uip2_pbbirth` at `8361fe85` is in EVAL-AUDIT's verification now.
- **V3 becomes STABLE C-3** if the verification shows both:
  - an M1 row no worse than `uip2_lvfree` in any family, with clutter ≤ 5.0;
  - the suite of record at 72/72.
- **Otherwise `uip2_lvfree` becomes STABLE C-3.**

Either way:
- build logs "STABLE C-3 <hash>" as soon as the verdict lands;
- EVAL-AUDIT verifies it, and writes `GATE_PACK_C3_<hash>.md` with CIs against v0, the option-C row, the suite of record and the flip lists;
- both write `result_row.py` rows.

**§70.3 ARCH.** The five deliverables (ARCH_V2, FLAG_LEDGER, COUPLING_MAP, MIGRATION_PLAN, PORT_PLAN_V2; done 04:01Z) are accepted as **drafts**.

A neutral **ARCH-REVIEW** lane (fresh session, read-only, 2 hours) checks them:
- (a) every code claim against the files (file:line);
- (b) every measured claim against the logs;
- (c) each Phase A and Phase B step for identity safety, with a verdict OK / FIX / BLOCK per step;
- (d) whether the event box and the display arbiter keep the author's economy.

It writes `research/perception/arch/ARCH_REVIEW.md`. Build starts Phase A only after both of these:
- STABLE C-3 is logged and verified;
- the review returns OK (or FIX-applied) for A1–A6.

Every step stays OFF ≡ parent byte-for-byte, with EVAL-AUDIT checking identity at each step.

**§70.4 BOX-LAB.**
- The UIP write-selection bound is closed: "youngest" is optimal at 14/46 ruler-exact reachable, and no causal state rule does better.
- The remaining lever is generation for the 68 unreachable goldens (the episode-container channel, R67 §67.4), within 2 variants.

**§70.5 DR-LINE** launches as soon as STABLE C-3 is logged (R69 §69.3).

**§70.6 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`. Never end a job early.

## Ruling 71 (04:35Z 23/09) - STABLE C-3 is the first stable build to meet M1; the next gates are the Owner's M2 and ceiling; migration waits for the review; BOX-LAB gets a reach queue; DR-LINE is running

**§71.1 STABLE C-3 = `1a5502129b4c1554`.** It is `uip2_pbbirth` folded into the defaults. Build logged it at 04:17Z. EVAL-AUDIT verified it at 04:29Z: the default engine is byte-identical on 198/198 panels, and the suite of record passes 72/72. Pack: `evalcheck/GATE_PACK_C3_1a550212.md`.

| family | C-3 | v0 | difference vs v0 (day-bootstrap CI) |
|---|---|---|---|
| box@1 | .134 (16/119) | .134 | +0.000 [−0.104, +0.104] |
| level@1 | .092 (7/76) | .066 | +0.050 [−0.028, +0.133] |
| line@2 | .104 (20/193) | .093 | +0.015 [−0.040, +0.070] |

- Clutter 4.33; margin 110/179.
- Option C (information only): strict 2.33, loose 3.89.

**The honest reading:**
- M1 is met on point estimates, which is the rule the Owner set (R34).
- Statistically, C-3 cannot be told apart from v0 on any family.
- BOX precision is 0.041.
- The Owner's blind precision check (M2) is therefore the real test of whether the drawings look right.
- **A/B/C** (R63/R64) is no longer needed for M1: the box gap closed under today's ruler. The Owner is told this; he may still raise it.

**§71.2 Process flag.** Build landed MIGRATION A1 (the kernel extraction) at 04:24Z. At that time neither R70 §70.3 gate had closed: C-3 was not yet verified, and ARCH_REVIEW had not reported.
- A1 is accepted, because EVAL-AUDIT's 198/198 identity run covers it.
- **From now on no migration step lands before ARCH_REVIEW.md gives it OK or FIX-applied.**
- If A2 is already complete, it may stand only if it passes identity 198/198 plus the suite of record and EVAL-AUDIT verifies it.
- Nothing past A2 lands until the review returns.

**§71.3 Build, while the review runs:**
1. A per-bar speed check of C-3. The persistent object must not bring back the F1 slowdown. Measure bars per second over 55 DESIGN days, through `heavy_run.py`, and log it with the F1 baseline beside it.
2. Keep the result rows current.
3. Take BOX-LAB hand-offs if any arrive.

**§71.4 EVAL-AUDIT: prepare the Owner's two tasks on C-3.**
- **(a) The M2 blind-precision pack,** built per `M2_PACK_PLAN.md`:
  - about 102 items: engine objects of C-3, golden controls and negative controls;
  - randomised, blind;
  - the answer key stored outside the pack.
- **(b) The human-ceiling kit** (`research/perception/ceiling_kit/`, already rendered). Refresh it only if anything in it depends on the engine.
- **Delivery:**
  - PNGs and a manifest in `research/perception/owner_pack/`;
  - Vietnamese instructions;
  - the time each task takes.
- The Lead builds the Owner-facing page from the pack. HOLD stays sealed.

**§71.5 BOX-LAB: the reach queue.** It was short-paused twice with an empty queue; this gives it one. Reach is the largest loss pool (68/119 goldens). Every item below is a pre-registered, offline, ruler-exact count with at most 2 variants, reporting both reach and ink (births and live objects per panel):
1. **Finish the episode-container channel:**
   - EC-A: Asia/session range box;
   - EC-B: post-spike absorption base (already +3/68 at 1.48 births/panel).
2. **The 13 "height above 34 pips" goldens:** one envelope stated in ABR instead of fixed pips.
3. **The 17 "edges never paired" goldens:** one pairing tolerance, stated up front.

Hand off a combined spec to build only if it adds reach at no more than about 1 extra birth per panel.

**§71.6 DR-LINE** was launched at 04:31Z (job `20260923043144-00817e`, 6-hour timebox), per R69.

**§71.7 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`. Never end a job early.

## Ruling 72 (05:25Z 23/09) - migration Phase A is accepted with a mechanical gate from now on; the ARCH author revises the plan (rev2) and the reviewer re-checks it; Phase B stays closed; BOX-LAB rests until a new generation idea exists

**§72.1 Phase A outcome.**
- **Landed:** A1–A5 on tree `2d497427`. Build's own check shows the output byte-identical to C-3 on 623/623 cached TUNE windows, and the suite of record at 72/72.
- **Reverted:** A6, which ARCH_REVIEW BLOCKed: it changes iteration order, so it is not a pure move. Family-major retire order may come back later only as a measured arm.
- **Timing:** build disclosed that A2 landed before R71 and A3–A6 before it had read R71 (REQUESTS §24).
- **Why the steps are kept:** EVAL-AUDIT verified identity through A4 at 04:54Z, and build then applied the review's FIX notes for A1–A5 (REQUESTS §25).
- **Still owed:** EVAL-AUDIT verifies tree `2d497427` independently (§72.5).

**§72.2 A mechanical gate replaces prose gates.**
- The file is `research/perception/arch/MIGRATION_GATE.md`. **Only the Lead writes it.**
- A structural engine step (any MIGRATION_PLAN step, or any refactor of engine files that is not a flagged experiment) may land only if the file lists that step as OPEN.
- Build reads the file before every such landing.
- A landing without OPEN is reverted and logged with a line starting "ESCALATE:".
- Today the gate is: Phase A CLOSED (done); A6 is not a migration step; Phase B ALL CLOSED.

**§72.3 The ARCH author revises the plan (rev2).** Resume session `bedecked-streetcar`; timebox 2 hours.
- **Absorb all nine fixes** in `ARCH_REVIEW.md` ("Fixes required before build continues"):
  - stale cites and the two missing channels;
  - the unbounded scans and `_ttl`;
  - the EventBox spec corrected to C-3 (`pb_birth`, the direct `_birth` path, the per-run latch and its reset);
  - FLAG_LEDGER recounted (49/21, `ev_uip_pb_birth`);
  - A6 filed as a measured arm;
  - emission-point and payload specs for B6/B7;
  - measured caps and determinism rules (rounding, `id()`, geometry keys) for the port.
- **Decide the arbiter.** Name the metric it is meant to move (recall@k, clutter, or both) and a measured gate for it. If no ruler-visible metric exists, drop the arbiter from the critical path.
- **Fold in the essence findings:**
  - DR-BOX: the freshest structure wins, and reach is the main loss.
  - DR-LINE (interim): the author's line is the boundary of the newest structure, and the defended-veto is the binding constraint on line reach. For levels, "which zone and when price approaches" matters more than whether a defended price exists.
- **Backup:** if B2/B3/B5–B7 cannot be made identity-safe as specified, propose the smallest safe path instead (for example B1 + B4 only, with the EventBox promotion as a measured arm) and say what it gives up.
- **Output:** the five files updated in place, each with a "rev2 changes" section at the top, and a final line `REV2 DONE <time>` in ARCH_LOG.md.

**§72.4 Re-review.** After `REV2 DONE`, the reviewer (session `melodic-wolverine`) re-checks rev2 and gives OK / FIX / BLOCK for each B step. The Lead opens gate steps only on OK.

**§72.5 EVAL-AUDIT:**
- (a) An independent identity check of tree `2d497427` against C-3: the full canonical set, objects + cand_log + events, and the suite of record.
- (b) Extend the identity oracle's canonical tuple with score / priority / touches (A0 note), as an evalcheck-owned harness change, before any arbiter-related step.
- (c) Continue `owner_pack/`. The answer key stays outside the pack.

**§72.6 Build, while gated:**
- no engine structure changes;
- answer ARCH questions;
- keep the C-3 level-miss anatomy (05:16Z) available to DR-LINE;
- keep the rows current.

Measured experiments still follow the normal keep rule when a ruling asks for one.

**§72.7 BOX-LAB rests; the keeper's pause stays.** Its R71 queue is done:
- EC-Bv2 adds +3/68 reach at 1.48 births per panel, which is above the budget of about 1 extra birth per panel, so it is not handed off.
- The envelope and pairing items came out negative.

The remaining 65 unreachable goldens are a pure generation problem. BOX-LAB resumes when DR-LINE or ARCH rev2 names a new generation idea to test.

**§72.8 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`. Never end a job early.

## Ruling 73 (06:10Z 23/09) - DR-LINE is accepted; build runs its line/level experiments as flagged arms; BOX-LAB gets one essence-derived generation job; DR-MARK starts; the Owner page goes live

**§73.1 DR-LINE accepted** (`deepresearch/DR_LINE_ESSENCE.md`, 05:25Z). Adopted as evidence:
- A pro line is the **defended edge of the newest structure**, not a fit (P1, P6). Freshest-anchor selection (`young_a@2` 0.18-0.30) beats every quality ranker (0.04-0.12). Same finding as DR-BOX.
- The **hard defended-veto** (`lines.py:181-203`) is the binding reach constraint: golden-line reach 0.22 -> 0.56 without it. Relaxing legality explodes candidates (median 203-760 per panel), so **economy must live in selection, not legality**.
- About 32% of golden lines stay unreachable even with every gate relaxed: an anchor-pool gap (including named-leg extremes).
- **Levels:** a defended origin exists near 85% of golden levels, but also near 74-83% of placebo prices. The level question is *which origin and when*. `ndef_dist@2` reaches 0.32 LC / 0.23 MINI vs engine births 0.19 / 0.07.
- **Stability:** the engine is deterministic (0/198 differ), but ±0.3-pip jitter keeps only 0.48-0.57 of matched lines and M15 keeps 0.19. It also makes about 3 silent re-anchors per panel (P8/P9 violation).
- **Descriptive validity on DESIGN:** a genuine return to a defended price exits on the defended side 0.88, vs 0.72 for a hover crossing of the same price. More prior defences give a stronger bounce. Descriptive only (CTRL0 empty; n_def confounds with congestion).
- **Proposed metrics M3 (stability), M4 (churn), M5 (snapshot fidelity)** are the Owner's call. The Lead has asked him. Until he decides they are reported as INFO only and never gate a keep.

**§73.2 Build queue: flagged experiments.** They follow the normal keep rule and are not governed by MIGRATION_GATE.md.
- **Parent:** the current tree `2d497427` (= C-3, 623/623).
- Every arm: flag OFF == parent (623/623 canonical + suite 72/72); one `result_row.py` row per measured arm; heavy runs via `heavy_run.py --lane build`.
- **Keep rule (unchanged):** target family up; other M1 families lose at most 1; clutter ≤ 5.0.
- **Always report:** births per panel per family, and the median line/level candidates per panel before salience (explosion watch).
- Run the items in this order. A kept arm becomes the parent of the next item.

**L-1 Line reach + operative selection** (EX1 + EX2 shipped together as one mechanism, because relaxation without selection floods the budget). Two variants, parameters fixed now:
- **V1:** `line.over_veto_mode="close_only"` (veto only in-span closes more than 2·tol past the violated side; wick pokes are teases) plus `line.rank="young_a"`.
- **V2:** `line.over_veto_mode="soft"` (no reject; score `nt - 0.5·over_all/tol`, with `over_all` on pivots and closes, like the lab's `worst_c`) plus `line.rank="young_a"`.
- `young_a` = prefer the chord whose first anchor is freshest; ties broken by `nt`. It applies at BOTH selection points: the chord `_eval` proposes (`lines.py:234-236`) and the line ordering in salience (`salience.py:276-283`).
- `min_touch_events=3` and `tol` unchanged.
- Target: line@2 ≥ 21/193.
- INFO: the ±0.3-pip jitter keep-rate for lines (`DR_LINE_consistency.py`).

**L-2 Level birth = nearest defended origin** (EX5).
- **V1:** `level.def_nearest=true`. `_trigger` fires only if the origin is the nearest same-side `n_def≥2` origin to the close.
- **V2:** V1 plus `level.def_ret24_req=true`, using the current `def_ret24_bars` default. State its value in the row note.
- Target: level@1 ≥ 8/76.

**L-3 Revision as ink** (EX4), run after L-1.
- **V1:** `line.reanchor_ink=true`. On a qualifying re-anchor the old line closes and goes to context ink under the existing extension grammar; the new chord is born as a sibling.
- **V2:** `line.reanchor_log="revise"`. Objects stay identical; an explicit `revise` event carries the old and new geometry. Verdict INFO (objects unchanged by design).
- Target for V1: line up, clutter ≤ 5.0.

**L-4 Zone-stable anchors** (EX3). INFO only until the Owner rules on M3, because its value is stability, which M1 does not score.
- **V1:** `line.anchor_snap=0.5·tol`.
- **V2:** `swing.prom_snap=true`. This touches swings that boxes also use, so report all three families.
- Record recall and jitter/M15 keep-rates. No keep.

A kept arm makes a **C-4 candidate** only. It becomes STABLE only by a Lead ruling after an EVAL-AUDIT verification.

**§73.3 BOX-LAB resumes for one bounded job: box reach, read-only ladder first** (prompt `_scratch/tools/boxlab_r73_prompt.md`, about 3 hours).
- **The idea is DR-LINE's lesson carried over to boxes:** hard legality gates, not selection, cause the reach loss. A pro's box edge is a zone that survives wick pokes that close back inside (spec §0, P5, P10).
- **Step 1, edge-definition check (read-only).** Inside each golden box's own time span, which edge does the author actually draw? Compare three definitions:
  - (a) the raw extreme;
  - (b) drop-one-outlier;
  - (c) the two-touch cluster edge: the most extreme price touched by at least 2 wicks within tol.

  Split the results into the 68 unreachable goldens and the 51 reachable ones.
- **Step 2, gate ladder (read-only).** List every hard gate that rejects, kills or redraws a box candidate, with file:line. Measure reach with each gate relaxed alone, then cumulatively, plus the median candidates per panel (a ladder like DR-LINE E3a).
- **Step 3, variants.** At most 2, and only if steps 1-2 show at least +5/68 headroom. State the parameters before measuring and ship each variant with youngest-born selection.
- **Hand-off.** Hand off to build only if reach improves by ≥ +5/68 at ≤ about 1 extra birth per panel.
- **Already done in R71, not repeated:** the envelope and pairing items (both negative).
- The keeper's `pause box-lab` stays: the Lead launches this job directly, so no double launch can happen.

**§73.4 DR-MARK starts** (R69 §69.4, prompt `_scratch/tools/drmark_prompt.md`, 6-hour timebox, read-only). It is the essence note for the event grammar:
- BRACKET (M / W / SHS middle sections);
- LABEL_TF (tease / false pokes);
- SQUEEZE ellipses;
- FALSE_EXT ticks.

It follows the same E1-E5 structure as DR-LINE. It changes no metric.

**§73.5 The Owner page is live.** One artifact holds two tasks:
- (1) The ceiling drawing: 10 panels from `ceiling_kit/`, drawn only up to τ.
- (2) The blind M2 set: 102 items from `owner_pack/`. Answers are yes / no / cant_tell. The page tells the Owner to judge as if standing at the dashed decision line.

Answers go to the page database. When the Owner finishes, the Lead exports them to `owner_pack/ANSWERS.md` and `ceiling_kit/owner_drawings/`. **EVAL-AUDIT scores them against the key**, which stays outside the pack. The Lead never sees the scoring before EVAL-AUDIT reports.

**§73.6 ARCH re-review is running:** job `20260923060300-cce0c3` (melodic-wolverine), launched 06:03Z. Gate steps open only on its OK.

**§73.7 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`, never in parallel. Never end a job early.

## Ruling 74 (06:35Z 23/09) - the Owner orders a multi-expert practice atlas built with NotebookLM, plus a catalogue of existing drawing indicators

**§74.1 The Owner's order (23/09).** Build an in-depth synthesis of how professionals draw and recognise price action, from reputable sources: videos, Forex Factory, Reddit, X, and public Discord material. Use a NotebookLM notebook named "Price Action". Also find existing drawing indicators, or suggestions for them.

**§74.2 New lane PA-ATLAS.** Fresh Devin session, prompt `_scratch/tools/pa_atlas_prompt.md`, 8-hour timebox.
- **Tool:** the NotebookLM CLI `nlm` 0.11.4. The MCP v2.0 server cannot create notebooks or add YouTube, so it is the fallback.
- **Steps:**
  - (1) sources, tiered (T1 published practitioners, T2 long-running public threads and educators, T3 Reddit/X), each URL verified;
  - (2) the NotebookLM notebook plus a structured Q1-Q10 question set per object type, each claim verified against its cited passage;
  - (3) `practice/PRACTICE_ATLAS.md`: a rule × expert matrix and machine-ready rule candidates, each with at most 2 flagged variants for build;
  - (4) `practice/INDICATORS.md`: existing tools, with causal vs repainting stated, plus clean-room specs for the top 3. If time allows, bake them off on TUNE with the ruler (verdict INFO).

**§74.3 Auth.** Both NotebookLM tools on the Owner's PC were unauthenticated at 06:30Z. The Lead opened `nlm login` on his desktop, and the Owner logged in himself. `nlm login --check` was valid at 06:34Z. Neither the Lead nor Devin handles credentials.
- **Backup** if the session expires: the lane does sources and indicators first, records `ESCALATE:`, and re-checks every 30 minutes.

**§74.4 Walls specific to this lane:**
- no book text uploaded anywhere;
- no paywall bypass;
- no joining or scraping Discord;
- no account logins;
- no public sharing of the notebook;
- at most 40 NotebookLM queries a day, leaving at least 10 for the Owner;
- quotes of at most 15 words.

**§74.5 Link to the other lanes.** Rule candidates from the atlas enter the build queue only through a Lead ruling, after the R73 L-items. A candidate that contradicts DR-BOX or DR-LINE is flagged, not silently adopted.

## Ruling 75 (07:08Z 23/09) - the R73 line/level arms all fail M1 and stay OFF; build diagnoses the cross-family loss before any new variant; gate opens B1 and B5 (B4 after its patch); DR-MARK resumes; canonical set defined

**§75.1 R73 build results.** Verified independently by EVAL-AUDIT at 07:03Z. All flags stay OFF, and C-3 is unchanged.

| arm | box | level | line | clutter | verdict |
|---|---|---|---|---|---|
| L-1 V1 close_only+young_a | 16 | 2 (−5) | 19 (−1) | 4.00 | FAIL; new suite fail `test_squeeze_between_line_and_ema` |
| L-1 V2 soft+young_a | 16 | 2 (−5) | 14 (−6) | 4.00 | FAIL; plus `test_slope_rule_no_rising_top_li…` |
| L-2 V1 def_nearest | 16 | 4 (−3) | 19 (−1) | 4.33 | FAIL |
| L-2 V2 +ret24 | 16 | 5 (−2) | 19 (−1) | 4.33 | FAIL |
| L-3 V1 reanchor_ink | 16 | 4 (−3) | 10 (−10) | 4.00 | FAIL |
| L-3 V2 reanchor_log | identical | | | | INFO (revise events only) |

L-4 (anchor snap) still runs, as INFO only.

**§75.2 What the failures teach** (the Lead's reading):
- **(a) Families compete.** More or different line births in L-1 cost 5 level hits. A lab bound measured on one family in isolation does not transfer when the families share structure and budget.
- **(b) The level deficit is on the generation side.** The right level is not live at τ, so restricting which origin may fire only cuts recall.
- **(c) Revision as new ink throws away evidence.** The sibling restarts at `n_touches = 0` while the matched line was usually the revised one.

The DR-LINE facts stand. What failed is converting them one family at a time.

**New standing rule.** From now on, any essence- or lab-derived arm must come with a **joint offline estimate for all three families** before it is built:
- which hits it may gain;
- which hits it may displace, and through which coupling path.

**§75.3 Build queue** (in order):
1. **L-1 cross-family anatomy.** Read-only, from caches.
   - For the 5 level hits lost under L-1 V1, name what took each one's place: which object, which budget or cap, which structure-competition path, with file:line.
   - Also: did the extra line births change any level candidate's birth time or state?
   - Output: `boxlab/REQUESTS.md` §27 plus a PERCEPTION_LOG entry.
   - Then propose at most 2 isolation variants with every parameter stated (for example: levels exempt from line-driven structure competition, like lvfree did for UIP). **Do not run them** until a Lead ruling approves them.
2. **L-4** as ordered in R73 (INFO).
3. **Migration landings per MIGRATION_GATE** (updated below): B1 and B5 are OPEN; B4 opens after the REQ §26 patch. Each landing needs:
   - flag OFF == parent on the canonical set (§75.6), plus suite 72/72;
   - an EVAL-AUDIT verification before the next step lands.
4. **Port-plan R-1.** Add an in-run peak pool-occupancy probe (`max len(pool)` per family). Measure it on the canonical set before any MQL5 cap is fixed.

**§75.4 The A3 pickle fix is accepted.** Build fixed `FamilyPipe.__getattr__` infinite recursion on unpickle (06:37Z). It is a load-path bug in a landed step, so it gets no gate entry.
- EVAL-AUDIT verifies tree `2e8a70072cc9aa2a` independently: flags OFF == C-3 on the canonical set, plus suite 72/72.
- Until then, arms may be measured on it but not kept.

**§75.5 Gate decision** (ARCH_REVIEW_REV2, 06:15Z):
- **B1 shadow views: OPEN.**
- **B5 EventBox relocation: OPEN.**
- **B4 pinned dispatch: OPEN only after** the two literal-order patches in REQ §26 are written into the B4 spec (ev_box_birth call site + is_structural guard; maintain×3 + squeeze_scan + `_pressure_update`).
- **B6, B7: CLOSED (FIX).** The ARCH author applies the clarifications when next resumed; the reviewer rechecks.
- **B2, B3:** measured arms C1 and C3, not gate items.
- A6 stays CLOSED.

**§75.6 Canonical set, defined once** (review R-5):
- the 623 cached TUNE windows as listed by EVAL-AUDIT at 05:37Z (`evalcheck/VERIFY_LOG.md`);
- "byte-identical" means objects + cand_log + events, plus score / priority / touches once §72.5b has landed.

The older 576- and 1728-check conventions are retired.

**§75.7 DR-MARK resumes.** Session `jagged-vessel` ended its turn after 26 of 360 minutes while it waited for the heavy lock. That is not allowed.
- `heavy_run.py` already waits up to 180 minutes by itself; do light work in the meantime.
- The same 6-hour mandate continues from its HANDOVER and the pre-registered E3c.
- **Ruler findings for the Owner (the ruler is his; no change is made without him):**
  - `_fam_letter` can never match golden `WW`/`MM` against engine `Ww`/`Mm`, which makes 11 bracket goldens unmatchable;
  - LABEL_TF matching does not compare the T/F letter.

**§75.8 BOX-LAB: clean negative accepted.**
- **Useful essence confirmation:** defended-cluster edges match the author's box edges 62–65% per edge, vs 41–44% for raw extremes.
- **The 68-wall is a pairing and generation problem.** The two defended edges never arrive paired in one causal candidate; it is not the gates.
- BOX-LAB rests until PA-ATLAS publishes `practice/INDICATORS.md`. It then tests the best causal range or box detectors from that catalogue as generators on the 68: lab reach at no more than about 1 extra birth per panel, at most 2 variants.

**§75.9 Status of the other work:**
- **Owner page:** live, and its db write path is verified (panel 9.11a has one box saved at 06:20Z).
- **PA-ATLAS:** running. Notebook "Price Action" `de998a77` created; 63 sources listed and 21 ingested. Forex Factory is blocked by Cloudflare and brookstradingcourse by a paywall; both are reported, not bypassed.

**§75.10 Unchanged:**
- M1, M2, the ruler, the fixtures, the thresholds and the spec are the Owner's.
- HOLD stays sealed. No model fits on the Owner's PC. Heavy runs go through `heavy_run.py`, never in parallel. Never end a job early.

## Ruling 76 (07:40Z 23/09) - the Owner delegates his two tasks: an independent AI draws the ceiling panels, and two blind AI judges score the M2 pack; results are proxies (M2-AI, AI-ceiling), scored by EVAL-AUDIT against the key

**§76.1 The Owner's order (23/09, translated):** "for the scoring page, let Devin draw and you judge". The Owner owns M2 and the ceiling check (R34), so he may delegate them. The Lead records what the delegation changes:
- **M2 was defined as the Owner's blind precision.** The result of this delegation is labelled **M2-AI**. It is a proxy, not the Owner's judgement.
- **The ceiling check was meant to measure a second human against the author.** An AI annotator gives an **AI-ceiling reference**, not a human ceiling.
- The Owner's page stays live, so he can still do either part later. Final thresholds remain his.

**§76.2 Who drew and who judged, and why not Devin.**
- **The problem with Devin:** it works on the Owner's PC, where the golden set, the engine caches and the answer key (`evalcheck/_owner_judge_key/`) all sit. A drawing or a judgement made there could be contaminated even by accident.
- **What the Lead did instead:** used fresh AI sessions in the Lead's cloud sandbox. They were given only:
  - the 10 ceiling PNG/JSON files;
  - the 102 item PNGs;
  - a one-page rubric in the Lead's own words from spec v1 (`RUBRIC.md`).

  Nothing else exists on that machine: no golden set, no engine, no key.
- **Ceiling annotator:** one fresh session (prompt `DRAW_PROMPT.md`). It drew 16 objects on 10 panels, all at or before τ.
- **Judge A = the Lead (Linh):** judged all 102 items blind before seeing Judge B.
  - Result: yes 38 / no 56 / cant_tell 8.
- **Judge B:** one fresh session with no project history (prompt `JUDGE_PROMPT.md`).
  - Result: yes 28 / no 71 / cant_tell 3.
- **Agreement:** 73/102, Cohen's κ = 0.45 on three classes and 0.51 on yes vs not-yes. That is moderate agreement, which is itself a measure of how subjective the task is.
- **Files:**
  - `owner_pack/ai_judges/`: `answers_linh.csv`, `answers_judgeB.csv`, `RUBRIC.md`, `JUDGE_PROMPT.md`;
  - `ceiling_kit/ai_drawings/`: `ceiling_<panel>.json` + `_overlay.png`, and `DRAW_PROMPT.md`.

**§76.3 EVAL-AUDIT scores against the key.** The key never leaves evalcheck, and the Lead sees only the aggregates.

(a) **M2-AI, per judge:**
- precision on the 48 engine items = yes / (yes + no), with cant_tell reported separately and also counted as no;
- yes-rate on engine hits vs on engine false positives (11 / 37).

(b) **Judge validity**, pre-registered by the Lead before any score is seen:
- yes-rate on the 30 golden controls, and no-rate on the 24 negatives;
- a judge is called **credible** only if golden yes-rate ≥ 0.60 **and** negative no-rate ≥ 0.80.
- A non-credible judge's M2-AI is reported but marked uninformative.
- This is a methodology check only. It sets no M2 threshold.

(c) **Inter-judge κ**, recomputed. Also report where both judges agree against the key.

(d) **AI-ceiling:**
- Convert `ceiling_kit/ai_drawings/*.json` to golden-comparable objects: box → BOX family; line → PATTERN_LINE; level → LEVEL family. Times are chart-clock minutes and prices come from the panel maps.
- Score them against the golden objects of those 10 panels with `eval_v2.py` (imported, never copied), at the author's budget per family.
- Score C-3 on the same 10 panels for comparison.
- Report per family and per panel. With n = 10, everything is descriptive and CIs are given.

(e) **Output:** `evalcheck/M2AI_REPORT.md` plus one `result_row.py` row with verdict INFO.

**§76.4 Unchanged:**
- M1, M2 (the Owner's own blind precision), the ruler, the fixtures, the thresholds and the spec are the Owner's.
- M2-AI does not replace M2 unless the Owner says so after he sees the report.

## Ruling 77 (08:02Z 23/09) - the Owner's critique of the drawings: what the Lead accepts, what the author's own data contradicts, and DR-RULES, which measures each rule against the author before anything is built

**§77.1 The Owner's input (23/09, about 07:50Z).**
- **What he said** (translated): "the drawings are not right at all, badly wrong". He then sent 10 chart images and a critique report, `owner_pack/owner_critique_20260923.md`, which is now stored verbatim.
- **Which drawings the 10 images are:**
  - Images 1-6 are the **AI-ceiling overlays** (orange): 9.66c, 9.38a, 9.25b, 9.24c, 9.23c, 9.19a. An independent AI session drew them under R76. They are not the engine.
  - Images 7-10 are **M2 pack items** (blue): p102, p101, p100, p099. The pack mixes engine objects, golden controls and deliberate negatives. The Lead does not know which class each one is.
- **The report's claims:**
  - four principles: the EMA as the dynamic axis, build-up before a break, no drawing in "daylight" (price far from the EMA), and a compact block;
  - ten per-image critiques;
  - five "fatal errors";
  - a four-step block-break rule, including execution.
- **The Owner's verdict on the 4 pack items is "no" for all four.** The Lead's own R76 answers were p099 yes, p100 no, p101 yes, p102 no.

**§77.2 The Lead's review.**

(a) **Accepted as real gaps, to be tested:**
- **The EMA25 relation is missing as a drawing gate.** The engine computes EMA25 and uses it only as a soft score (`ema_guide` in boxes.py) and as "dominant pressure" for the setup layer (spec §4). The author reads every structure against the EMA. Neither the Lead's R76 rubric nor PA-ATLAS covers it.
- **Impulse legs, news spikes and shock bars inside a box.** Spec §2 already says "never drawn: news spikes or clean trend legs, emit STAND_ASIDE". Whether `stand_aside()` actually stops drawing has never been measured.
- **Zombie levels and lines.** Spec §3.2 (p89) says an edge broken back and forth without resolution is deleted, and PA-ATLAS consensus item 6 says a zone tested 4-5 times weakens. Whether the engine applies this to levels and lines has never been measured.
- **Box edges on single spikes, and a box start that spans a swing break.** This is consistent with the BOX-LAB R73 finding: the author's edges sit on the defended wick cluster in 62-65% of cases, against 41-44% for raw extremes.
- **Rubric v1 (the Lead's) had none of these criteria.** R76's M2-AI votes, the Lead's included, are marked "rubric v1: no EMA, impulse or zombie criteria". The R76 judge-validity check still runs and will show how much that cost.
- **The AI-ceiling is a weak reference.** The Owner rejects 6 of its 6 overlays. EVAL-AUDIT still scores it (R76 §76.3 d), but it will not be used to set any threshold.

(b) **Rejected or unproven as stated:**
- **"20 EMA".** Volman's charts use EMA25 (spec §1, book p47). We keep EMA25.
- **"A box longer than 20 bars is a fatal error; a block is 5-15 bars."** The author's own boxes contradict this. The Lead made a quick read-only count on the TUNE golden (77 of 119 boxes parsed; HOLD untouched):
  - median width is 20 bars; p75 is 39 and p90 is 70;
  - only 40 of 77 are ≤ 20 bars, and 23 of 77 are ≤ 15;
  - spec §3.1 gives the casebook's typical width as 18-36 bars.

  A hard cap would delete about half of Volman's own boxes. The report merges two objects: the **range box**, and the small **build-up block** inside or at its end. Spec §3.7 already says "nested is best". The block is kept as a concept; the cap is not.
- **The same count on height:** median 14 pips, p90 22, **none above 34**. A box of 55-65 pips is outside the author's envelope and outside the engine's own 6-34 envelope. EVAL-AUDIT will say whose p100 is.
- **"Trade only horizontals plus the EMA; drop diagonals."** The author draws 193 lines on TUNE, and the line family is part of M1. This is rejected for perception; the atlas records the same dispute (Brandt vs Brooks, Grimes and DeMark).
- **The report's numbers** (1.5-2 pips to the EMA, 2.5·ATR, 5-15 bars, 2 closes through) are proposals, not measurements. Each one is measured against the author before use. Where a report number is kept, it is only a reference point.
- **Execution** (stop order, SL/TP, 1:1-1:2) is outside perception. It is kept for the setup layer.
- **p101's "W ghost far from price" is partly a rendering issue.** A BRACKET is a time span, not a price level (spec §2), and the book draws it just above the tops or just below the lows. Our renderer puts it at a fixed band at the bottom of the plot. That is a fix for the renderer (§77.5), not the engine.

**§77.3 New lane DR-RULES (fresh researcher session, read-only). Prompt: `_scratch/tools/dr_rules_prompt.md`.** One question: which of the Owner's rules does the author himself obey, and how many of the engine's false objects would each rule remove?

- **Part A - book check** (book_loader only; quotes ≤ 15 words). For each rule below, and for "daylight", the EMA period, build-up and block size: page evidence for, against, or silent.
- **Part B - author compliance** on the TUNE golden only; HOLD stays sealed. Units: ABR (engine `abr`) and EMA25 (engine `ema`). Each measure is taken over bars ≤ min(t1, τ).

| id | rule (pass = the object would be allowed) | variants |
|---|---|---|
| C1 | EMA near the box/level: distance from EMA25 at the object's last bar ≤ τ to the band [bot, top] ≤ d (0 if inside) | d = 0.5, 1.0 ABR (report's 2 pips as reference) |
| C2 | EMA not steep: \|EMA25[t] − EMA25[t−10]\| / (10·ABR) ≤ s at the object's last bar | s = author q95, q90 |
| C3 | no shock bar inside the span: no bar with range ≥ m·ABR | m = 2.5, 3.0 |
| C4 | no impulse inside the span: no run of ≤ 6 same-direction bars with net move ≥ r·ABR | r = 3, 4 |
| C5 | box width ≤ W bars | W = author q95, q90 (report's 20 as reference) |
| C6 | each box edge sits on a cluster (≥ 2 extremes within tol), not a lone wick; BOX-LAB's definition, imported | one definition |
| C7 | not a zombie: side switches of the close across the level or line (beyond ±tol) between birth and τ ≤ n | n = 2, 3 |
| C8 | not superseded: no confirmed swing extreme of the same polarity, born after the level, lies beyond it by ≥ k·ABR | k = 1, 2 |

Per family (BOX: C1-C6; LEVEL: C1, C2, C7, C8; LINE: C2, C7), report the pass-rate on the author's objects, with a CI.

- **Part C - C-3 split.** On the canonical 623 windows (R75 §75.6), report the pass-rate of each rule on C-3's matched objects (hits that would be lost) and on its unmatched objects (false objects removed), per family, at budget.
- **Part D - joint 3-family estimate** (R75 rule). Use a first-order replay of selection from cand_log with the rule as a filter, through the existing replay path (the one used for `_l1_anatomy.py`). Import it; do not write a new selector. Report per family: hits at budget, clutter, and what fills each freed slot. Any engine run goes through `heavy_run.py --lane dr-rules`.
- **Part E - pack features without the key.** Compute C1-C8 for every one of the 102 pack objects from the item geometry. Write `DR_RULES_pack_features.csv` (seq, rule values). The key stays in evalcheck; if the only file that holds the geometry also holds the class, DR-RULES must not open it and writes ESCALATE instead.
- **Part F (if time allows)** - apply the same rules to the PA-ATLAS baselines (`bl_tdlines_k2`, `bl_donchian_alt`). The question: do the Owner's rules cut their clutter while keeping their hits?
- **Pre-registered verdict per rule** (the Lead fixes it now, before any number):
  - **BUILD-CANDIDATE:** author compliance ≥ 0.90 in its family, **and** it removes ≥ 20% of C-3's unmatched objects in that family, **and** the first-order estimate keeps every other family within −1 hit and clutter ≤ 5.0.
  - **TRADER-ONLY:** author compliance < 0.90. It is not built. It goes to the Owner as a target question: follow the author or follow the rule.
  - **INFO:** anything else.
- **Output:** `research/perception/deepresearch/DR_RULES.md`, `DR_RULES_LOG.md`, `DR_RULES_*.py` and `.jsonl`, and one `result_row.py` row with verdict INFO. It ends with a 10-line Vietnamese summary for the Owner.
- **Timebox:** 4 hours.

**§77.4 EVAL-AUDIT additions** (after the R76 work and the 2e8a7007 identity check):
- (a) **Verify the three PA-ATLAS baseline rows:**
  - `bl_tdlines_k2` line@2 29/193, clutter 6.67;
  - `bl_donchian_alt` level@1 16/76, clutter 10.33;
  - `bl_darvas_n7` box@1 2/119.

  Recompute each with `eval_v2.py`, check that the budget accounting is identical to C-3's, and check prefix invariance on 5 panels.
- (b) **Join `DR_RULES_pack_features.csv` with the key.** Report each rule's pass-rate by class (golden / negative / engine hit / engine false positive) as aggregates only.
- (c) **Report the class of p099-p102** in the Owner's report. The Owner has already judged those four in the open, so they leave his blind pack, which drops to 98 items. His "no" on each is recorded as his answer for that item.

**§77.5 Build lane addition** (after the B1/B5 landings and the L-1 anatomy): the renderer (`render.py`, `ceiling_render.py`) draws a BRACKET just beyond the formation's extreme, below the lows for W and above the tops for M, at an offset of about 0.5·ABR. It is not drawn at a fixed band of the plot. This is render-only: engine output and the ruler are untouched, so tests must stay byte-identical.

**§77.6 Sequencing:**
- **BOX-LAB** stays paused until DR-RULES Parts B-D are done for the box family. It then resumes with INDICATORS.md plus the DR-RULES verdicts.
- **No build arm** comes from this ruling until DR-RULES reports and the Lead rules on it (R78).
- **DR-MARK and PA-ATLAS are complete:**
  - DR-MARK: DR_MARK_ESSENCE.md; proposals P1-P7 wait for R78.
  - PA-ATLAS: PRACTICE_ATLAS.md, INDICATORS.md, 3 baselines; candidates BX-1, LN-1 and LV-1 wait for R78.

**§77.7 Unchanged:** M1, M2, the ruler, fixtures, thresholds and the spec belong to the Owner. The target question (§77.3, TRADER-ONLY) goes to him with numbers, not as the Lead's decision.

## Ruling 78 (09:15Z 23/09) - DR-RULES read: the Owner's rules cannot delete objects without deleting the engine's hits; the engine's boxes are the wrong shape; the AI stand-ins failed; next come objective generators (H0), box-shape transforms (S1) and trade tags (TT)

**§78.1 Results received** (all verified by EVAL-AUDIT unless marked):

**DR-RULES** (`deepresearch/DR_RULES.md`, 08:56Z)
- Part E was escalated correctly. EVAL-AUDIT bridged it at 09:05Z.
- EVAL-AUDIT recounted Parts B and C at 09:07Z, and the recount matches.

**M2AI_REPORT** (`evalcheck/M2AI_REPORT.md`)
- Both AI judges fail the validity gates pre-registered in R76:
  - Linh: golden yes-rate .533, negative no-rate .792;
  - Judge B: golden yes-rate .267.
- Both judges said yes to the engine's false objects at least as often as to its hits.
- The AI ceiling agrees with the golden set on 1/28 objects; C-3 gets 4/28 on the same 10 panels.
- The four items the Owner judged in the open (key classes):
  - p099: engine false object;
  - p100: **golden**, a box the author drew himself;
  - p101: deliberate negative;
  - p102: engine false object.
- The Owner was right on 3 of 4; his one miss is the author's own box. The Lead's R76 answers were right on 1 of 4.

**PA-ATLAS baselines** reproduce exactly and use the same budget accounting (08:29Z):
- TD lines k2: line@2 29/193;
- Donchian-alt: level@1 16/76;
- Darvas: box 2/119.

**Build lane**
- B1 landed and was verified (08:13Z); B5 landed and was verified (08:42Z).
- Tree `2e8a7007` has been verified independently.
- The bracket renderer (R77 §77.5) is done: render-only, and the tree is unchanged.
- Current tree: `bbdee030`.

**§78.2 The Lead's reading.**

(a) **Correction to R77.**
- **The verdict rule was wrong.** R77 §77.3 bounded hit loss only in the families a rule does not target. That contradicts the standing keep rule (R75: no family loses more than 1). Under the correct rule, **none of the 8 rules passes as a hard filter on C-3**:
  - C5@q95 costs 14 of 16 box hits;
  - C8@1 costs 4 of 7 level hits;
  - C8@2 costs 2 of 7 level hits.

  The "BUILD-CANDIDATE" labels in DR_RULES.md §G are void. DR-RULES reported the in-family costs openly, which is exactly what made this correction possible.
- **R77 §77.2(b) "no author box above 34 pips" is withdrawn.** The count covered only the 50 of 119 boxes whose prices were parsed. p100 is a golden box about 55 pips tall.

(b) **Why the rules cannot filter C-3: its hits have the same faults as its misses.**

| rule | pass-rate on C-3 hits | pass-rate on C-3 false objects |
|---|---|---|
| C3@2.5 | .12 | .09 |
| C4@3 | .00 | .02 |
| C5@q95 | .06 | .03 |
| C6 | .06 | .01 |

- The engine's box "hits" are loose overlaps. They are long-lived boxes that contain impulse legs and shock bars, and the ruler still matches them (time IoU ≥ 0.5, edges within ±3 pips).
- The cause is **lifetime, not congestion width**. On the containment window, C5w removes only .04 of the false objects. The congestion part is shaped like the author's; the drawn box then keeps living.
- This is the concrete, measured reason the Owner sees "badly wrong" boxes.

(c) **The author does not follow the Owner's rules either.**
- He obeys C2 (flat EMA, .95), C5@q95 (.95) and C8 (1.00).
- He obeys C1 only for boxes (.82; levels .37).
- He partly obeys C3 (.70-.83) and C4 (.60-.90).
- His edges trim spikes: C6 strict is .34, because his edges sit inside the outermost cluster.
- On full history, his levels cross prices that have already been woven through: C7f@2 is .46.
- p100 shows the conflict directly: the Owner rejected Volman's own box.

(d) **Generation, not selection, is where levels and lines are lost.**
- Freed slots almost never recover a hit (fills_matched ≈ 0).
- The simple objective generators, built on "newest defended extreme", beat the engine:
  - Donchian-alt levels: 16/76 against 7/76.
  - The same levels with the EMA filter C1@1.0: still 16/76, and level clutter falls from 10.33 to 2.50.
  - TD lines k2: 29/193 against 20/193.
- **Caveat:** the author's levels pass C1@1.0 only 37% of the time. As the level generator improves, that filter will cap it.

(e) **The AI cannot stand in for the Owner's eye.**
- R76's delegation is void as a measurement: the judges are not credible and the AI ceiling agrees with the golden set on 1/28.
- M2 remains the Owner's own blind precision. The pack now has 98 items.

**§78.3 Design the Lead proposes: two layers. The Owner's decision is needed only for what M2 judges.**
- **Structure layer.** It draws what the author draws. The target stays M1 against the golden set.
- **Trade-tag layer.** It computes the Owner's rules as facts on every object (spec §4 style). An object with no tag is "tradeable".
  - Tags never delete structure, so M1 is untouched.
  - A "trade view" shows only tradeable objects.
- **The Owner's call:** does M2 judge the full chart or the trade view? Until he answers, M2 stays as defined (R34).

**§78.4 Work orders.**

Keep rule for every arm below, fixed now:
- the target family's hits ≥ parent;
- every family ≥ parent − 1;
- total clutter ≤ 5.0 (published census method);
- causal: prefix invariance holds on 20 panels.

Each arm also reports the Owner-rule pass-rates (C1-box, C3w@3.0, C4w@4, C6g, C7f@2, C8a@1) on its objects, as an M2-facing diagnostic.

(1) **H0 - hybrid generators** (offline, cache-only). Resume PA-ATLAS session `absorbed-mistake`; prompt `_scratch/tools/h0_hybrid_prompt.md`; timebox 150'.
- Compose per panel: C-3 boxes at box@1, plus
  - H0-a: C-3 lines + Donchian-alt levels filtered by C1@1.0;
  - H0-b: TD k2 lines filtered by C7@2 + C-3 levels;
  - H0-c: both substitutions.
- Score the full M1 row with `eval_v2.py` (imported, never copied): box, level, line, bracket and total clutter.
- Check prefix invariance on 20 panels per source.
- One `result_row.py` row per arm, verdict INFO.
- This is an estimate. Only the build lane can later turn a passing arm into flagged pipe sources, after an ARCH note.

(2) **S1 - box shape transforms** (offline, on C-3's cached box objects at τ). Resume DR-RULES session `delicate-ravioli`; prompt `_scratch/tools/s1_boxshape_prompt.md`; timebox 150'.
- S1-a, **left-edge reset:** move t_left to the first bar after the last impulse run (≥ 4·ABR within ≤ 6 same-direction bars) or shock bar (≥ 3·ABR) inside the drawn span. Edges unchanged.
- S1-b, **age cap:** t_left ≥ τ − 75 bars (the author's q95). Edges unchanged.
- Score box hits with `eval_v2.py`. Other families are unchanged by construction, so clutter is unchanged. Also report how many C-3 boxes become Owner-clean.
- If either arm passes, the build lane implements it as a flag: `box_left_reset` or `box_max_drawn_age`, OFF ≡ parent.

(3) **TT - trade tags** (build lane, observability only).
- Compute per live object at each bar:
  - box: `daylight` (C1 > 1.0·ABR), `steep` (C2 > q95 for the family), `shock_inside` (C3w@3.0), `impulse_inside` (C4w@4), `lone_edge` (not C6g);
  - level: `steep`, `zombie` (C7f@2), `superseded` (C8a@1);
  - line: `steep`, `zombie` (C7s@2).
- Take the definitions and q95 thresholds from `DR_RULES_measure.py` (import, never copy).
- Where they are stored: snapshot facts, excluded from `canonical()`, behind the flag `trade_tags=0`.
- Tests:
  - one synthetic unit test per tag;
  - OFF ≡ parent on 623/623;
  - with the flag ON, canonical is also identical, because tags never change objects.
- Report the tradeable fraction of C-3 objects per family.
- EVAL-AUDIT verifies it.

(4) **Sequencing.**
- BOX-LAB stays paused until S1 reports.
- The DR-MARK proposals (P1-P7) and the PA-ATLAS candidates (BX-1, LN-1, LV-1) wait for H0 and S1.
- H0 and S1 are light; their only heavy steps go through `heavy_run.py`, never in parallel.

**§78.5 Unchanged:**
- M1, M2, the ruler, fixtures, thresholds and the spec belong to the Owner.
- Two questions go to him with this ruling:
  - (i) whether M2 judges the full chart or the trade view (§78.3);
  - (ii) whether he will judge the 98-item pack himself, since the AI stand-in failed.

## Ruling 79 (09:44Z 23/09) - the Owner's decision: M2 becomes his blind precision on a trade-view pack (M2-TV)

**§79.1 The Owner's decision** (23/09, about 09:40Z; translated: "OK, I agree"), answering the proposal in R78 §78.3 and §78.5:
- **Official M2 = the Owner's blind precision on a new trade-view pack, M2-TV.**
  - The pack shows only objects that carry no R78 trade tag.
  - It replaces the 98-item pack, which is retired unjudged and kept for the record.
- **The M2 threshold stays .60** (R34), applied to M2-TV.
- **M1 is unchanged.** The structure layer is still scored against the author.

**§79.2 M2-TV pack spec.**
- **Who builds it:** EVAL-AUDIT only. The key stays sealed in `evalcheck/_owner_judge_key/`, and the Lead sees aggregates only.
- **Plan first:** EVAL-AUDIT writes `evalcheck/M2_TV_PLAN.md`, and the Lead approves it before any rendering.
- **Engine under test:**
  - C-3 plus whatever flags R80 approves (S1 and/or H0, if they pass the R78 keep rule and are verified);
  - otherwise C-3 alone.
  - Either way, `trade_tags=1` decides eligibility.
- **Items: 50, TUNE only, HOLD sealed, fixed seed, one object per image:**
  - **30 engine items:** tradeable objects at golden-decision τ.
    - At least 6 per family (box, level, line); the rest proportional to the engine's tradeable output.
    - At most 1 item per panel per family.
  - **10 golden controls:** author objects that the same tags mark tradeable, stratified by family.
  - **10 deliberate negatives:** built from tradeable engine objects by the M2_PACK_PLAN.md methods (shift, stretch, spike anchor).
  - **Excluded:** the panels of p099-p102.
- **Rendering:**
  - the R77 renderer with the new bracket placement, and EMA25 visible;
  - **no bars after τ** (a change from the 98-item pack, which showed them): the Owner judges only what was knowable;
  - objects are clipped at τ;
  - one blue object and a dashed "now" line.
- **Scoring:**
  - **M2-TV** = yes / (yes + no) on the 30 engine items, with a Wilson CI;
  - a sensitivity with cant_tell counted as no;
  - golden yes-rate and negative no-rate reported descriptively (the Owner is the metric of record, so they are not a validity gate on him);
  - per-family precision.
- **Page:** the Lead publishes it by updating the Owner's existing page (same link). The M2 section is replaced by the 50 items; the ceiling section stays optional. Answers go to the page db; EVAL-AUDIT scores them.

**§79.3 Order:**
1. TT verified by EVAL-AUDIT.
2. H0 and S1 report; R80 names the engine under test.
3. EVAL-AUDIT writes M2_TV_PLAN.md; the Lead approves it.
4. EVAL-AUDIT renders the items.
5. The Lead publishes the page; the Owner judges.
6. EVAL-AUDIT scores and writes `evalcheck/M2_TV_REPORT.md`.

**§79.4 Unchanged:** M1, the ruler, fixtures and the spec. The .60 threshold is the Owner's (R34) and stays.

## Ruling 80 (10:10Z 23/09) - the Owner's order: Gemini reviews charts and verifications (G-REVIEW), and nothing about the drawings reaches the Owner before it passes that review

**§80.1 The Owner's order** (23/09, about 10:05Z; translated): "from now on, chart review and verification go to Gemini 3.8 extended; it catches mistakes so they get fixed. I have said it many times and you have not improved."

The Lead accepts the diagnosis. Until now, every chart check before the Owner rested on the Lead's own eye or on AI stand-ins. R78 measured them:
- the Lead matched the key on 1 of 4 items;
- both R76 judges were not credible.

So the loop "Owner complains → Lead fixes → Owner complains again" had no independent critic in it. From now on it does.

**§80.2 The reviewer.**
- **Model:** Gemini 3.8 Flash with "Tư duy mở rộng" (extended thinking), in the Owner's own Chrome, on the Owner's account.
- **Operator:** the Lead drives it through the browser. There is one Gemini chat per review round.
- **What it sees:**
  - rendered PNGs only;
  - `review/REVIEW_PROMPT.md` (§80.4).
- **What it never sees:** the golden set, the key, book pages or text, the engine code, or result numbers. Its judgement is visual and independent, like the Owner's.
- **Role in the separation of duties:** builder ≠ ruler ≠ reviewer. EVAL-AUDIT stays the ruler (numbers). Gemini is the chart reviewer (the eye).

**§80.3 What goes through G-REVIEW:**

(a) **Every arm that changes what is drawn** (S1, H0, TT's trade view, and everything after), before the Lead rules KEEP:
- 12 fixed review panels are rendered for the parent and for the arm, side by side;
- Gemini judges each panel;
- the Lead may rule KEEP only if Gemini's fatal count on the arm is not higher than on the parent **and** M1 passes.

(b) **Every page or pack before it reaches the Owner**, M2-TV included. This is a render check only: the instructions must be readable, the object visible, there must be no bars after τ, and brackets must be placed correctly. Gemini never judges the M2-TV items themselves, so the Owner's blind test stays his.

(c) **Verifications** (the Owner's "kiểm định"). Each research conclusion that changes direction goes to Gemini as plain text (the claim, the numbers and the logic; no book text, no golden) with one question: "what is wrong or unproven here?" DR-RULES-type conclusions and R-rulings that choose between arms are included.

**§80.4 REVIEW_PROMPT.md** (the Lead writes it; it goes in the device repo):
- **The rubric, v2:**
  - Volman's grammar (spec v1 §2-3);
  - the Owner's principles (critique of 23/09): EMA25 relation, build-up, no drawing in daylight or on a steep EMA, no box across an impulse or shock bar, no zombie levels or lines, edges on clusters;
  - what the author himself does (DR-RULES Part B), so that Gemini does not demand stricter rules than Volman: boxes up to about 75 bars, edges trimmed inside spikes, levels often far from the EMA.
- **Output per panel:** verdict ok / flawed / fatal; each error with its object, what is wrong and the concrete fix. At the end, the error classes ranked by frequency.

**§80.5 Triage.** Nothing is dismissed without a number. Every Gemini finding goes into `review/GEMINI_<round>.md` verbatim, and the Lead classifies it in a triage table:

| class | action |
|---|---|
| render bug | build ticket, render-only |
| engine shape (edges, span, lifetime) | an S-type arm with parameters stated, measured by M1 + G-REVIEW |
| engine selection or generation (wrong object, missing object) | an H- or L-type arm, or a research question |
| disagreement with the author | measured first (DR-RULES style), then goes to the Owner as a target question, never silently dropped |

Round n+1 re-renders the **same 12 panels** in the same Gemini chat and asks "which of your round-n findings are fixed, which remain, which are new?".

**§80.6 G-KIT (render tool, new Devin job, prompt `_scratch/tools/gkit_prompt.md`).**
- One CLI renders the full live chart at τ for any arm. Arms come from engine flags, or from an object-override jsonl so that offline arms (S1, H0) can be rendered too.
- Rendering: EMA25, no bars after τ, the R77 bracket placement, and each object family in the book grammar.
- It also defines the 12 fixed review panels: TUNE, fixed seed, 4 box-led, 4 level-led and 4 line-led, none from the p099-p102 panels.
- Output folder: `review/sets/<arm>/`.
- **Calibration, once:** the first round also carries p099-p102, blind and mixed in, so we know how Gemini compares with the Owner (3/4) and the key. This is descriptive and gates nothing.

**§80.7 Consequences for earlier rulings:**
- R79 §79.3 gets a new step: Gemini render-checks the M2-TV page (§80.3b) before the Lead publishes it.
- The decision on H0/S1 and the engine for M2-TV moves to **R81** and also needs G-REVIEW (§80.3a).

**§80.8 Unchanged:**
- M1, M2 (the Owner's own judging), the ruler, fixtures, thresholds and the spec.
- Gemini is a reviewer, not a metric, and not a replacement for the Owner's blind judging.

## Ruling 81 (10:59Z 23/09) - G-REVIEW round 1: Gemini matches the Owner on 4/4 calibration items and rejects 9/12 C-3 panels as fatal; triage into TT-2 (trade-view tags), S1-b review, S1-a', and a box-reach question

**§81.1 Round 1 was done under R80.** The full record is `review/GEMINI_R1.md`: Gemini's text verbatim, the chat links, and the Lead's triage.

**Calibration** (p099-p102, whose key is known):

| item | key | Gemini | Owner | Lead (R76) |
|---|---|---|---|---|
| p099 | engine false object | reject | reject | accept ✗ |
| p102 | engine false object | reject | reject | reject |
| p100 | **golden** (author's own box) | reject | reject | reject |
| p101 | deliberate negative | reject | reject | accept ✗ |

- Gemini agrees with the Owner on 4 of 4, and like him it rejects p100 because the box "swallows the breakout".
- Reading: Gemini approximates the Owner's eye well enough to act as a filter before the Owner sees anything. It does not approximate the author. Where the Owner and the author disagree, Gemini sides with the Owner.

**C-3 on the 12 fixed panels:** ok 1, flawed 2, fatal 9.

**§81.2 Correction to R80 §80.2 (tooling facts, measured 10:35-10:56Z):**
- "Tư duy mở rộng" refused image input 3 times.
- 3.8 Flash and 3.1 Pro both accept images.
- An 8-image follow-up in the same chat was refused. Batches of up to 4 images, each in a fresh chat with a short QA framing, work.

The operating rule is therefore:
- **Image review:** 3.8 Flash, at most 4 images per fresh chat.
- **Second opinion on disputed panels:** 3.1 Pro.
- **Text-only verification (§80.3c):** "Tư duy mở rộng". Not yet tested; the first such check will confirm it works.

**§81.3 Triage** (the full table is in GEMINI_R1.md):
- **E1 (10/12):** sloped lines cut candle bodies or cross congestion, and are not retired after a decisive break.
- **E2 (9/12):** stale or far objects stay on the chart; too many objects.
- **E3 (7/12):** the current congestion near the EMA at "now" is not drawn. This is box reach, i.e. generation.
- **E4 (5/12):** zombie levels.
- **E5 (4/12):** a box swallows an impulse or lives past the breakout.
- **E6 (3/12):** an M/W bracket spans far longer than the middle section.
- **Not accepted:**
  - elipses as high/low markers;
  - levels moved to round numbers;
  - channels;
  - box edges fitted to bodies.

  These contradict the author's grammar (spec §2, §3.1). The last one is kept only as a signal that the edge is wrong.

**§81.4 Decisions on H0 and S1** (both verified by EVAL-AUDIT at 09:37Z):
- **S1-b (age cap at 75 bars):** passes the M1 keep rule (box 16/16, other families identical, clutter 4.33). Under R80 §80.3a it now needs G-REVIEW: render the s1b set, then round 2. If Gemini's fatal count on s1b is not higher than on c3 (9/12), the build lane lands the flag `box_max_drawn_age=75` (OFF ≡ parent).
- **S1-a (left-edge reset after an impulse or shock):** fails the target leg (15/16, one drop). It is the only arm that fully cleans E5 (C3w/C4w reach 100%).
  - One new variant is authorised, **S1-a'**: identical to S1-a, except that when the reset would leave fewer than 3 bars, the object keeps its last 3 bars instead of being dropped.
  - It is an offline estimate by the DR-RULES session.
- **H0 (hybrid generators):** fails the clutter leg (6.00, 7.67 and 10.00 against 5.0), with clean causality and +9 hits in each substituted family.
  - The binding problem is **retention**. This matches E2.
  - **H0-R** (§81.5-4) will apply the TT-2 lifetime tags as die rules to the H0 generators and re-measure M1 and clutter.

**§81.5 Work orders (fixed now):**

(1) **TT-2 (build lane, observability only).** It extends R78 TT with lifetime tags. Parameters are stated and must not be tuned:
- `line_broken` (LINE): since birth, ≥ 2 consecutive closes beyond the line on its non-defended side by more than tol. Once set, it stays set. tol = the engine's edge tol.
- `line_cuts_bodies` (LINE): over [first anchor bar, t], ≥ 2 bars whose real body [min(o,c), max(o,c)] contains the line value with more than tol inside.
- `stale_far` (all families): at t, the distance from the close to the object is more than 3·ABR20, **and** its last touch (price within tol) was more than 24 bars ago.
  - The distance is to the band for a box, to the price for a level, and to the value at t for a line.

**Trade-view hide set** (what `--drop-tagged` hides):
- **Hidden:** daylight (box), steep, shock_inside, impulse_inside, zombie, superseded, line_broken, line_cuts_bodies, stale_far.
- **`lone_edge` stays a fact but does not hide.** The author obeys C6 only 34% of the time, and hiding on it would remove about 99% of the engine's boxes, which would leave M2-TV (R79) with no boxes.

Tests and handover:
- one synthetic test per new tag;
- OFF ≡ parent 623/623;
- ON canonical ≡ OFF;
- report the tradeable fraction per family, with v1 tags alone and with v1 + v2 tags;
- EVAL-AUDIT verifies.

(2) **G-KIT (resume).** Render on the 12 fixed panels:
- `s1b` from `deepresearch/DR_RULES_S1_objects.jsonl` (S1-b objects);
- `tt_view_v1` (the current TT, hide set as in §81.5-1 minus the v2 tags);
- `tt_view_v2` after TT-2 is verified.

Contact sheets for each. The Lead then runs round 2: s1b vs c3, and tt_view vs c3.

(3) **S1-a' (resume DR-RULES session).** Measure it exactly as S1 was measured:
- M1 keep rule;
- owner-clean rates;
- per-hit table;
- the object override jsonl for G-KIT.

(4) **H0-R (after TT-2 is verified; resume the PA-ATLAS session).** Take the H0-a and H0-b generators. An object dies when `stale_far` or `line_broken` (lines) or `zombie` (levels) sets. Re-measure the full M1 row and the published census clutter.

(5) **BOX-LAB stays paused.** E3 (the missing current box, 7/12) is its next question, with GEMINI_R1's named panels as examples. It resumes after round 2, so that at most three research lanes run at a time.

**§81.6 M2-TV:** the engine under test is not named yet. It is named in R82, after round 2 on s1b and tt_view_v2.

**§81.7 Unchanged:** M1, M2, the ruler, fixtures, thresholds and the spec. Gemini is a reviewer, not a metric.

## Ruling 82 (12:31Z 23/09) - G-REVIEW round 2: the reviewer rejects S1-b; S1-a' fails; new arm S2 "the box ends at the breakout"; line_broken stays hidden in the trade view; H0-R starts; M2-TV plan amended; E3 diagnosis

**§82.1 Round 2 on `s1b`.** The record is `review/GEMINI_R2.md` (sha 4A860A8B1E78): the text verbatim, the chat links and the Lead's reading.
- 8 of 12 panels were reviewed: batch A with 3.8 Flash + P2, batch B with 3.1 Pro + P2.
- S1-b adds a **new fatal error on 4 of 8 panels**: 9.10c, 9.33c, 9.36c, 9.40a. On 9.40a the verdict goes from OK in R1 to fatal.
- `review/sets/s1b/_diff.md` confirms the cause on all four. The only changed object is a box whose left edge the cap moved into view:

  | panel | object | left edge |
  |---|---|---|
  | 9.10c | BOX0001 | 20 → 570 min |
  | 9.33c | BOX0001 | 35 → 680 min |
  | 9.36c | BOX0001 | 20 → 710 min |
  | 9.40a | BOX0002 | 50 → 285 min |

  The reviewer names these exact boxes by time (for example "04:45 đến cuối" = 285 min). Under C-3 they start off-screen and show as two horizontal lines. Once capped, they become rectangles that swallow the trend or the breakout.
- **Verdict (§80.3a):** S1-b **fails**. The fatal count rises on the paired panels. The flag `box_max_drawn_age` is **not landed**. Batch C was skipped, because 4 new fatal errors cannot be offset by 4 panels.
- **Protocol note:** R1 used Flash + P1 and R2 used Flash/Pro + P2. The new findings name S1-b's transformed objects, so the prompt change does not explain them. From round 2b on, the c3 control is re-run under the same model and prompt as the arm (§82.8).

**§82.2 S1-a' fails** (EVAL-AUDIT verified at 11:52Z): box 15/16.
- The lost hit (9.58a) is a golden box whose trigger event ends at the drawn right edge. No left-edge rule can cover it.
- **The left-edge family is closed** (S1-a, S1-a', S1-b).
- The lesson from both reviews and the Owner: the error is where a box **ends**, not where it starts. The reviewer asked for the same fix in both rounds and on both models: "phải hủy/cắt ngắn hộp khi nến breakout thoát ra ngoài".

**§82.3 S2: the box ends at the breakout.** Offline estimate by the DR-RULES lane. The definitions are fixed now and are not tuned.
- **Scope:** box-family objects only (the kinds DR_RULES_S1 treats as boxes). Brackets and the other families are untouched.
- **Parent:** C-3 @fa2e52e5 with default flags. OFF ≡ C-3.
- **Edges:** the object's top and bottom as drawn at τ, which is the geometry G-KIT draws. tol = the engine's edge tol, the same one TT-2 `line_broken` uses.
- **Break:** the first run of k consecutive bars j..j+k−1, all inside [drawn left edge, τ], whose closes are all above top + tol (up) or all below bottom − tol (down).
- **Close:** if the break is confirmed by τ (j + k − 1 ≤ τ), the box is closed at τ: it is not ranked, not drawn and not counted in clutter. This is sticky: a later return inside does not reopen it. Causal: bars ≤ τ only.
- **Variants (max 2):** S2-k2 (k = 2) and S2-k3 (k = 3). Nothing else varies.

Measure it exactly like S1, reusing the S1/S1ap measure code by import:
- **M1 row:** box@1 via eval_v2; the other families recomputed; published census clutter.
- **Keep rule:** box ≥ 16, every family ≥ parent − 1, clutter ≤ 5.0, prefix invariance on 20 panels.
- **Per-hit table** for the 16 C-3 box hits: closed or not, and bars from confirmation to τ. List hits gained (another box promoted into the box@1 slot) and hits lost.
- **Counts:** boxes closed per variant; owner-clean tables as in S1.
- **Author compliance:** the share of golden boxes that the same rule would close at their own τ. Does the author keep a box after 2 or 3 closes beyond it?
- **Override for G-KIT:** per variant, for the 12 review panels, in the review/HOWTO.md schema (engine spelling, one row per panel). Each row holds the full drawn set at τ: the c3 objects minus the closed boxes.

**Decision rule (stated now):**
- A variant that passes the M1 keep rule goes to a G-KIT render and G-REVIEW, paired against c3 under the same protocol.
- If both variants pass, only the one with more box hits is reviewed. On a tie, S2-k2 is reviewed, because it is the reviewer's own request.
- It lands (build lane, flag OFF ≡ parent) only if the reviewer's fatal count does not rise (§80.3a).

**§82.4 `line_broken` stays in the trade-view hide set** (the build lane's flag, 28-TT2).
- **Fact** (verified 11:40Z): it would hide 58% of the author's lines, against 11% of the engine's.
- **Reasoning:** the trade view is the Owner's eye, not the author's archive (R79). The Owner and the reviewer both call a line that price has closed through a fatal error (E1, 10/12). The author keeps such lines as history, and the structure layer keeps them too, so M1 is untouched.
- **M2-TV consequence:** golden lines tagged `line_broken` are not eligible for the golden pool. The rule is the same for every class. EVAL-AUDIT reports the eligible golden-line count.
- **Revisit** only if the Owner's M2-TV answers show that he accepts broken lines.

**§82.5 M2-TV plan (`evalcheck/M2_TV_PLAN.md`): amendments and approvals.**
1. **§1 "tradeable" is replaced by:** no tag in `trade_tags.TRADE_VIEW_HIDE`, with the constant imported, never copied as a list.
   - `lone_edge` does not disqualify.
   - `line_broken`, `line_cuts_bodies` and `stale_far` do.
   - The rule is identical for engine, golden and negative items; negatives are re-tagged after mutation.
2. **Open points approved:**
   - seed 20260923;
   - negatives use the audited M2_PACK_PLAN methods (shift / stretch / spike anchor);
   - goldens may share panels with engine items, still at most 1 item per panel per family;
   - τ = the golden-decision τ at which the object entered the pool, with the object clipped there.
3. **Engine under test:** named in R83, after round 2b (tt_view_v2) and the S2 estimate. Only verified candidates are eligible. Today that is C-3 @fa2e52e5 + trade_tags=1; S2 may be added if it lands.
4. **Dry run meanwhile:** EVAL-AUDIT may build and dry-run the pack builder with C-3 @fa2e52e5 + trade_tags=1 as a placeholder.
   - Output is pool counts per family and class only.
   - No PNG in owner_pack, no sealed key, nothing the Owner sees.
   - Once R83 names the engine, the pack is one run.
5. **Before the Owner sees the pack,** Gemini render-checks the page (§80.3b). It does not judge whether the items are true.

**§82.6 H0-R (PA-ATLAS, resume).** TT-2 is verified, so §81.5(4) starts now.
- **Arms:** H0-a (Donchian levels | C1@1.0) and H0-b (TD lines k2 | C7@2), each with die rules. An object dies at the first bar where:
  - `stale_far` sets (all families);
  - `line_broken` sets (lines);
  - `zombie` sets (levels).

  The predicates are imported from `perception/trade_tags.py`.
- **Re-measure:** the full M1 row, published census clutter and prefix invariance on 20 panels.
- **Keep rule:** as in R75/R78, with the target family = the substituted family.
- **Override:** for an arm that passes, write a G-KIT override for the 12 review panels.
- **H0-c** runs only if both a and b pass.

**§82.7 E3: BOX-LAB diagnosis** (read-only, no new generator). It starts when the G-KIT render job ends, so that at most three research lanes run at a time.
1. **The 7 named panels** (9.10c, 9.11b, 9.17b, 9.25a, 9.2b, 9.33c, 9.52a), at the review τ:
   - Does the author have a current box, i.e. one whose right edge is at or near τ?
   - What does the engine hold near price? Classify it as one of:
     - never born;
     - born and killed (by what);
     - live but outranked (by which object);
     - cut by the budget.
2. **All TUNE windows:** the same four-way breakdown over every golden box decision where the author's box is current and the engine misses it.
3. **S2 overlap:** for each "outranked" case, would the outranking box meet S2's close rule (k = 2, k = 3)? This estimates how much of E3 S2 recovers for free.
4. **Output:** `boxlab/E3_DIAG.md`, plus one INFO row.

**§82.8 Round 2b protocol.**
- `tt_view_v2` and the c3 control are reviewed with the same model and the same prompt P2, in the same batches, with a fresh chat per batch.
- The record is `review/GEMINI_R2b.md`, verbatim.
- The Lead's reading is paired: fixed / remain / new.

**§82.9 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds and the spec. Gemini is a reviewer, not a metric.

## Ruling 83 (13:25Z 23/09) - S2 fails and the Lead's definition was wrong; the break rule moves to the trade view (TT-3 `box_broken`); E3 cause found (incumbent monopoly), engine arm Y ordered; H0 closed; M2-TV engine named conditionally; Gemini default recorded

**§83.1 S2 fails** (EVAL-AUDIT verified 12:58Z). Box hits: k2 2/16, k3 4/16; other families identical; census 4.33 → 3.67.
- **The Lead's error, stated plainly.** R82 scanned for the break from the drawn left edge. The engine's left edges reach back into bars where price had not yet entered the band, so the rule read price *arriving* into the zone as a breakout.
  - 57–59% of closures confirm before the box's own birth.
  - Most of the 16 hits "broke" at bar 1–9 of their drawn span.
- **A second error:** R82 removed the box from the structure layer, which is where M1 is measured. A rule about how a chart should look to a trader belongs in the trade view (R78 two-layer design; the same reasoning as `line_broken` in R82 §82.4).
- **What stands:**
  - A break rule does catch the boxes the reviewer calls fatal: 3 of 4 S1-b fatal boxes and all 4 E5 panels.
  - Under the same scan, 14% (k3) to 24% (k2) of the author's own boxes would close, against 86–89% of engine box events. The gap is mostly the engine's long retroactive left edges, which is the E5 geometry itself.

**§83.2 TT-3: `box_broken` (build lane, observability only, same flag `trade_tags`, no new flag).** Parameters are fixed now and are not tuned.
- **Entry bar j0:** the first bar ≥ t_left whose close lies within [bottom − tol_e, top + tol_e]. If there is no such bar by t, the tag cannot fire.
- **Break,** evaluated only on bars in (j0, t]. Either:
  - (i) 3 consecutive closes, all > top + tol_e or all < bottom − tol_e; or
  - (ii) one close beyond an edge by ≥ 3·ABR20 (the R78 shock scale; Gemini's "elephant bar").
- **Behaviour:** sticky; causal (bars ≤ t). `tol_e` is imported from `trade_tags.py`. It is already volatility-scaled, max(1 pip, 0.25·ABR20), which answers Gemini's point e1.
- **Facts written:** `exit_bar` (the first bar of the confirming run, or the shock bar) and `break_clause` ∈ {run3, shock}.
- **Trade view:**
  - `box_broken` joins `TRADE_VIEW_HIDE`, so a broken box is not eligible for M2-TV.
  - For chart pages and review renders, a broken box is drawn **truncated at `exit_bar`, in a faded style**, not hidden. This is the reviewer's own fix ("cắt ngắn hộp") and Gemini's point d.
  - The render option belongs to G-KIT (§83.6).
- **Report** (boxlab/REQUESTS §29-TT3 + PERCEPTION_LOG):
  - share of C-3 live box objects tagged, split by clause;
  - **of the 16 C-3 box hits at their τ, how many are tagged** (the upper bound of what arm Y can lose before replacements);
  - golden compliance with the same entry-anchored rule, per clause;
  - the 4 S1-b fatal boxes and the 4 E5 panels: tagged or not, and `exit_bar`;
  - diagnostic only: boxes with ≥ 3 closes beyond one edge in (j0, t] that never form a run of 3 (Gemini's "creeping trend", b1).
- **Tests:**
  - synthetic cases: approach from below → range → break (tag at the break, not at the approach); a 2-close false break that returns (no tag); a shock close (tag);
  - prefix invariance on 5 panels;
  - OFF ≡ parent 623/623; ON canonical ≡ OFF;
  - full suite green.

**§83.3 E3 cause (BOX-LAB `boxlab/E3_DIAG.md`, read-only, 12:57Z).**
- **The 7 named panels:**
  - On 3 (9.10c, 9.11b, 9.25a) the author has no current box. Those are Owner-eye versus author disagreements, not engine misses.
  - On the other 4, the engine *had* generated the author's box as a candidate (3 edge-matched). In every case an old event/UIP box held the family's single box slot, so the candidate was outranked, expired, or still pending at τ.
- **All 103 box misses on TUNE:**

  | class | n | share |
  |---|---|---|
  | BUDGET_CUT (pending 25, outranked 19, expired 13, rate 2) | 59 | 57% |
  | BORN_KILLED (score floor 18, the incumbent overwrote the matching geometry 11) | 32 | 31% |
  | NEVER_BORN | 8 | 8% |
  | LIVE_OUTRANKED | 4 | 4% |

  - 43 of the 103 had an edge-matched candidate in the log.
- **Reading:** the dominant failure is **incumbent monopoly**, not generation. Under `ev_uip_persist` the incumbent is close-exempt and keeps rewriting itself.

**§83.4 Engine arm Y: the incumbent yields** (build lane, after TT-3 passes its own identity checks; flag `box_yield`, default 0, OFF ≡ parent).
- **When ON:** a live box-family object whose `box_broken` has set is closed (natural death, reason `yield_broken`), including the event/UIP incumbent despite `ev_uip_persist`.
  - The freed slot is then handled by the existing pool rules.
  - No change to scores, ranks, budgets or generation.
- **Variants (max 2), fixed now:**
  - **Y1** = `box_broken` only;
  - **Y2** = `box_broken` OR `stale_far` (the TT-2 predicate).
- **Measure:**
  - the full M1 row (canonical 623);
  - census clutter;
  - prefix invariance on 20 panels;
  - suite;
  - per-hit flips;
  - other families must be identical, or the difference explained;
  - **E3 re-diagnosis** under each variant, `boxlab/e3_diag.py` imported: how many BUDGET_CUT misses become hits.
- **Keep rule:** box ≥ 16, every family ≥ parent − 1, clutter ≤ 5.0.
- **Next step:** the variant that passes (more box hits; on a tie, Y1 as the simpler) goes to G-KIT and G-REVIEW, paired against c3 under the same protocol, and lands only if the fatal count does not rise (§80.3a).

**§83.5 H0 closed** (EVAL-AUDIT verified 13:05Z).
- **H0R-a:** level stays 7/76. All +9 new hits are zombie-killed, so the net gain is zero.
- **H0R-b:** clutter 7.67 under all three census conventions. The clutter is birth churn, not retention.
- **Kept on record:** TD-lines k2 finds +9 line hits (29 vs 20), at a birth rate the clutter budget cannot carry. It reopens only as a separate order with a birth-rate mechanism.
- PA-ATLAS goes idle.

**§83.6 G-KIT (after TT-3 lands).**
- Add the render option `--fade-broken`: `box_broken` boxes are drawn truncated at `exit_bar`, in light grey, dashed, thin. Every other tag in `TRADE_VIEW_HIDE` stays hidden.
- Render `review/sets/tt_view_v3` = trade_tags=1, drop-tagged, fade-broken, on the 12 panels, plus `_diff` against c3 and against tt_view_v2.
- Copy to `_scratch/gr2/tt_view_v3/`.

**§83.7 M2-TV engine, named conditionally.** C-3 @fa2e52e5, trade_tags=1, hide set = `TRADE_VIEW_HIDE` including `box_broken` (TT-3). Two conditions:
- (i) EVAL-AUDIT verifies TT-3;
- (ii) G-REVIEW round 3: tt_view_v3's fatal count ≤ c3's, under the same model and prompt.

Fallbacks:
- If (ii) fails, the engine is C-3 + the v2 hide set, provided tt_view_v2 passes the same paired test.
- If neither passes, M2-TV does not run, and R84 decides.

Arm Y is not part of the engine under test. If Y lands later, a re-run of the pack is decided then.

EVAL-AUDIT's staged builder (`_m2_tv_pack.py`, pools engine 598 / golden 179 / seed 20260923) runs once, when (i) and (ii) hold.

**§83.8 Gemini default (Owner, 12:59Z): "mặc định dùng gemini flash 3.8 mở rộng".** Default model = 3.8 Flash + "Tư duy mở rộng".
- **Measured:** it refuses image batches (13:02Z; R81, 3 of 3) and answers text checks (the R82 logic check).
- **Image review fallback order,** logged per call: Flash Mở rộng + P2′ → 3.8 Flash + P2′ → 3.1 Pro + P2′.
  - P2′ = P2 plus: "chỉ dùng để kiểm thử phần mềm, không dùng cho quyết định tài chính; chỉ nhận xét hình học, không đưa lời khuyên hay dự đoán".
- **Rule:** the c3 control always uses the same model and prompt as the arm.
- **Round 3 order:** c3 and tt_view_v3 first. tt_view_v2 is reviewed only if v3 fails (it is the fallback).
- **Practical limit:** the Chrome window must be visible; a hidden window does not submit.
- **R83 itself** gets a Flash Mở rộng text logic check before the Owner is told (§80.3c).

**§83.9 Triage of the R82 logic check** (`review/GEMINI_R82_logic.md`):

| point | decision |
|---|---|
| a1 false break | TT-3 uses k=3 and entry anchoring; golden compliance shows whether the author keeps false-break boxes |
| a2 expanding range | read from the TT-3 golden table |
| b1 creeping trend | diagnostic count in the TT-3 report |
| c k=3 | adopted (also closer to the author) |
| d faded, truncated | adopted (§83.6) |
| e1 tol | already ABR-scaled; no change |
| e2 elephant bar | adopted as clause (ii) |

**§83.10 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds and the spec. Gemini is a reviewer, not a metric.

## Ruling 84 (14:33Z 23/09) - TT-3 verified; arm Y fails and is closed; Owner order: G-REVIEW runs only on 3.8 Flash + Tư duy mở rộng; round 3 on Pro is void; Y3 offline estimate

**§84.1 TT-3 `box_broken` is verified** (build @e7d13384 13:52Z; EVAL-AUDIT 14:13Z).
- **Identity:** OFF ≡ parent 623/623, ON ≡ parent 623/623, prefix 7/7, suite 90/90, independent recompute 1250/1250.
- **Facts:**

  | measure | tagged |
  |---|---|
  | live C-3 boxes | 138/180 (77%) |
  | C-3 box hits at their τ | 12/16 |
  | the author's own boxes (own span) | 3/119 (2.5%) |
  | S1-b fatal boxes | 3/4 |
  | E5 panels | 4/4 |

- **Reading:** the engine usually finds the author's box, but never *ends* it. The author ends his box at the breakout; the engine keeps it alive until "now". This is the E5 complaint in one number.
- **Semantic note from EVAL-AUDIT:** the tag re-derives when the incumbent rewrites its band (9.42b). It is sticky per geometry version. Accepted.
- **R83 §83.7 condition (i) holds.**
- **M2-TV pool with `box_broken` excluded:** engine 527 (box 55 / level 23 / line 250 / bracket 199). Feasible.

**§84.2 Arm Y fails and is closed** (build 14:09Z; Y1 ≡ Y2).

| family | parent | Y |
|---|---|---|
| box | 16/119 | 7 |
| level | 7/76 | 3 |
| line | 20/193 | 18 |
| bracket | 29/85 | 30 |

- Census clutter 4.67; prefix 55/55.
- Killing broken incumbents removes 14 of the 16 hits. The freed slot gains only 5, because the pool's next-best box rarely has the author's geometry.
- The reviewer's logic check had predicted this ("zone downgrade", `GEMINI_R83_logic.md` point c).
- **Lesson:**
  - A break is a *view* fact (trade view: faded and truncated), not a death sentence.
  - Structural work on E3 must get the right *current* box born and ranked. It must not kill the old one.

**§84.3 Owner order (~14:30Z, verbatim): "cứ dùng 3.8 flash mở rộng, cho tới khi thành công. cấm dùng pro 3.1 hay giảm cấp 3.8 flash vì nó ngu".**
- **G-REVIEW (images and text) runs only on 3.8 Flash + "Tư duy mở rộng".** 3.1 Pro and plain 3.8 Flash are forbidden. This replaces the fallback chain of R83 §83.8.
- **Round 3 as run is void:** 8 panels, c3 and v3, on 3.1 Pro + P4, before the order (`review/GEMINI_R3.md`). It is kept as information only:
  - v3 fixed the named box errors on 9.10c, 9.17b and 9.36c; the reviewer praised the faded box on 9.36c;
  - the fatal tally was 5 against 5;
  - there were ±1-class swings on panels where nothing changed.
- **Protocol for making Flash Mở rộng accept images** (each step logged; the same model throughout):
  1. 1 image + "describe the drawn shapes" (capability test);
  2. 1 image + P4;
  3. 2 images + P4;
  4. 4 images + P4.
- **Rules:**
  - A refusal is retried once in a fresh chat before stepping back.
  - If step 1 fails 3 times in a row on different chats, the Lead reports the evidence to the Owner as a probable capability limit of the mode and does not work around his order.
- **Decision statistic for paired reviews (from round 3 on):**
  - Single-run verdicts swing ±1 class with no object change.
  - An arm is judged on **findings that name objects the arm changed**: fixed / remain / new on those objects.
  - The panel verdict tally is reported but does not decide alone.
  - §80.3a is read as: no *new* fatal finding on a changed object.

**§84.4 M2-TV condition (ii)** waits for round 3 on Flash Mở rộng under §84.3. Unchanged otherwise.
- The pack builder stays staged; nothing is rendered for the Owner.
- If Flash Mở rộng cannot read images (§84.3 rule), the Lead asks the Owner how condition (ii) should be met, rather than choosing a different model.

**§84.5 Y3 offline estimate (BOX-LAB, read-only; no build).** Gemini's recommendation: yield only if broken **and** far/stale. Y1 ≡ Y2 implies every `stale_far` box was also broken, so Y3 = `stale_far` alone. Before any build, measure at the golden-decision τ:
- how many of the 16 C-3 box hits carry `stale_far`;
- how many incumbents in the 59 BUDGET_CUT misses carry `stale_far`, and for each, whether an edge-matched pending candidate existed.

Output: `boxlab/Y3_EST.md` plus an INFO row. A build is ordered only if it loses no hit and frees ≥ 5 edge-matched candidates.

**§84.6 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds and the spec.

## Ruling 85 (15:15Z 23/09) - Y3 estimate read; no build yet (joint-family and path-dependence estimate missing); arm YS "yield without death" fixed with 2 variants

**§85.1 Y3_EST (BOX-LAB, finished 14:56Z; official box 16/119 reproduced)**
- Direct hits lost: **0/16**. No hit is ever `stale_far` between birth and τ.
- Edge-matched candidates freed (upper bound): **11 rows / 10 unique incumbents**. Among the named panels only 9.17b is reached.
- Context:
  - box@1 age at τ: median 119 bars (p25 95, p75 154); lifespan median 271.
  - The author's box length is median 17 bars (DR-RULES).
  - 21/23 (91%) of `box_broken` incumbents are retested at the old band within 24 bars of `exit_bar`.
- BOX-LAB found and fixed its own load bug before reporting (it had loaded the w1 run instead of the τ-keyed run). Accepted, because the official row reproduces.

**§85.2 Lead reading.** The §84.5 numbers pass (0 lost; 11 ≥ 5), but the estimate is incomplete, so no build is ordered.
- (a) **Joint estimate across families (R75 rule) is missing.** This was the Lead's omission in §84.5.
  - Arm Y cost level 7→3 and line 20→18.
  - Y3's kill set is a subset of Y's (Y1 ≡ Y2), so the risk to levels is real and unmeasured.
- (b) **Path dependence.** "0 lost" counts only direct kills. Killing an earlier incumbent lets another candidate take the slot, and that new holder can block a later hit.
- (c) **Expected yield is small.**
  - Y promoted the right box in about 5 of ~50 freed slots, so Y3 is likely +1 or +2 at most.
  - Y3 does not reach 9.33c, 9.2b or 9.52a, where wrong-geometry incumbents sit at price.
- (d) **The real disease is the age of the slot holder.**
  - It is about 7× older than the author's box (119 vs 17 bars).
  - DR-BOX: the author's box is the newest one.
  - Therefore the second variant targets **succession**, not death.

**§85.3 Arm YS "yield without death"** (replaces the Y3 build question; 2 variants, fixed now)
- **Yield:** the incumbent loses the box slot (box@1 and box budget rank) but is **not closed**.
  - It stays live in the structure layer with its facts, so the levels, lines and brackets that derive from or compete with it see the same object.
  - Yield is sticky: a yielded incumbent never regains the slot.
  - If the engine cannot express "demote without close" under the current budget, BOX-LAB states why (file:line) and estimates the close version instead, labelled as such.
- **YS-a:** the incumbent yields at its first `stale_far` onset. This is Gemini's "broken AND far/stale", since `stale_far` ⊂ `box_broken`.
- **YS-b (succession):** a `box_broken` incumbent yields only to a candidate box **born after its `exit_bar`** (the post-breakout consolidation). If no such candidate is live, it keeps the slot.
- Flags default OFF, and OFF ≡ parent.
- **Estimate (BOX-LAB, read-only, `boxlab/YS_EST.md`), per variant:**
  - box hits lost, counting direct losses plus path-dependence at-risk hits as lost;
  - edge-matched candidates freed;
  - at-risk hits per other family (level, line, bracket);
  - the 12 fixed review panels.
- **Build rule (fixed now):** build a variant only if
  - box hits lost = 0,
  - edge-matched candidates freed ≥ 5, and
  - at-risk hits ≤ 1 in each other family.

  If both variants pass: one build with two flags. If neither passes: YS is closed, and E3 moves to birth and rank work.

**§85.4 Retest.** 91% of broken incumbents are retested within 24 bars, which fits the usual price-action reading (an old edge is tested again after the break).
- TT-3 stays as it is: faded and truncated at `exit_bar`.
- Whether the trade view should keep the old edge as a faded line through the retest window is recorded as a **view question for after M2-TV**. It is not ordered now.

**§85.5 G-REVIEW.** Chrome was hidden from 14:31Z until at least 15:11Z, so step 1 of §84.3 has not been attempted. A missing attempt does not count as a failure. M2-TV condition (ii) still waits.

**§85.6 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds, the spec, and HOLD.

## Ruling 86 (16:00Z 23/09) - YS fails both variants and is closed; the slot-release family (Y, Y3, YS) is closed; correction of R85 §85.2(d); arm AD "adopt, don't yield" is fixed with 2 variants for an offline estimate

**§86.1 YS_EST (BOX-LAB, finished 15:41Z; 190 rows).** Both variants fail the R85 gate.

| gate | YS-a | YS-b |
|---|---|---|
| box hits lost = 0 | pass (0) | FAIL (16) |
| edge-matched freed ≥ 5 | FAIL (0) | FAIL (1) |
| at-risk per family ≤ 1 (level / line / bracket) | pass (0 / 1 / 1) | FAIL (6 / 17 / 15) |

- **STEP 0 facts** (with file:line in `YS_EST.md`):
  - The box slot is `famlive_box=1`. It is not shared with level, line or bracket; those families share only the `signal` cap 3 and `budget_hard` 9.
  - Under `ev_uip_lvfree` the persistent UIP incumbent holds only the famlive slot.
  - Box edges seed carried levels (`boxes.py:1211-1223`).
  - "Demote without close" is **not expressible**: it would need a new `yielded` state.
- **YS-a:** Y3's "11 edge-matched frees" was an **overcount**. It counted each incumbent's stale onset independently per row. Under a sticky yield, one onset frees at most one row, so the true figure is 0.
  - R85 §85.2's caution (path dependence, the Y precedent) was correct, and no build was spent.
- **YS-b:** TT-3 fires within a few bars on thin, freshly written UIP bands (9–20 pips; about 59% are born broken). Because a post-exit candidate is almost always pending, every hit object yields before τ, giving succession chains of 5–11 events per panel.

**§86.2 The slot-release family is closed** (Y: kill; Y3: estimate; YS-a / YS-b: yield).
- Freeing the famlive slot never places the author's box, because the successor is chosen by pool score and rarely has the author's geometry.
- Arm Y re-matched only 5 of ~50; YS-b placed no successor with the author's geometry on any of the 12 panels.

**§86.3 Correction of R85 §85.2(d) (Lead error).**
- "The slot holder is ~7× older than the author's box (119 vs 17 bars)" compared **object identity age** (`j_tau − t_birth`, `y3_est.py:329`) with the author's **drawn box length**. These are different quantities.
- The UIP incumbent is a **persistent, rewriting** object (`uip_birth` / `uip_rewrite`): one identity, many band versions. Its *current* band version can be young.
- The claim is withdrawn until the band-version age and the drawn width are measured (§86.4 item 1). The Owner is told.

**§86.4 Arm AD "adopt, don't yield"** (offline estimate by BOX-LAB, read-only; 2 variants fixed now).
- **Reasoning:**
  - The 16 C-3 box hits are the UIP object's *own* rewritten bands at τ. The rewrite mechanism already tracks consolidations some of the time.
  - In the misses, a separate candidate carried the right band while the incumbent kept a wrong one.
  - Adopting the candidate's band into the incumbent's identity:
    - keeps the famlive slot and `lvfree` (no signal or hard-cap cost);
    - keeps the object id, so carried levels keep their parent;
    - uses an existing mechanism (`uip_rewrite`) rather than a new state;
    - has no successor chain.
- **Trigger (both variants).** At bar j a box-family candidate c is suppressed by the famlive slot (pending, BUDGET_CUT or outranked while `fam_n ≥ 1`), and all of the following hold:
  - c was born after the incumbent's last write;
  - `close[j]` lies inside c's band (± `tol_e`);
  - `close[j]` lies outside the incumbent's current band (± `tol_e`).
  - Everything is causal: only information ≤ j is used. No golden, ruler or edge-match information enters the rule.
- **Effect:** the incumbent rewrites to c's band, using uip_rewrite semantics:
  - same id; `t_left` = c.t_left;
  - a new geometry version, with TT-3 facts re-derived per version;
  - c is consumed.
- **AD-a:** the trigger alone.
- **AD-b:** the trigger AND the incumbent's current band version is `box_broken` AND c was born after its `exit_bar`.
- **Estimate per variant** (the ruler's `V2.match` on the simulated band at each golden τ, so these are real hits, not upper bounds):
  - box hits lost;
  - box hits gained;
  - adoptions per panel (churn);
  - cross-family at-risk, via derived levels of the pre-adoption band and any cap interaction under STEP 0;
  - the 12 fixed panels.
- **Build rule (fixed now):** build a variant only if
  - box hits lost = 0,
  - gained ≥ 3 (these are exact ruler matches, not bounds),
  - at-risk ≤ 1 per other family, and
  - the median number of adoptions per panel is ≤ 3.
  - If both variants pass: one build with two flags. If neither passes: E3 goes to birth-side research, i.e. why the UIP's own rewrite picks the wrong band.
- **Diagnostic items in the same job:**
  1. box@1 at τ: identity age, current band-version age, drawn width; compare with the author's box length.
  2. For each E3 miss with an edge-matched candidate: did the UIP incumbent rewrite inside the candidate's pending window? If so, to what band, and which clause of `uip_rewrite` (file:line) declined the candidate's band?

**§86.5 G-REVIEW.** Chrome was hidden from 14:31Z to at least 15:57Z. Step 1 of §84.3 has not been attempted, and one Owner reminder was sent at 15:17Z. M2-TV condition (ii) still waits.

**§86.6 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds, the spec, and HOLD.

## Ruling 87 (16:30Z 23/09) - AD fails both variants and is closed; the R85 correction is settled by measurement; E3 moves to the UIP band-write geometry: arm RW with 2 variants for an offline estimate

**§87.1 AD_EST (BOX-LAB, finished 16:15Z; 88 rows).** Both variants fail the R86 gate, and no threshold is relaxed after the fact.

| gate | AD-a | AD-b |
|---|---|---|
| box hits lost = 0 | FAIL (1) | FAIL (1) |
| gained ≥ 3 (ruler-exact) | FAIL (2) | pass (4) |
| at-risk per family ≤ 1 | pass (0/0/0) | pass (0/0/0) |
| median adoptions per panel ≤ 3 | FAIL (5) | FAIL (4) |

- The shared loss is 9.7b: the band was already golden-correct, and two adoptions moved it away while price roamed.
- No review panel ends with author geometry. The adopted bands are pool candidates, and pool candidates carry the wrong geometry. This is the same wall as §86.2.
- AD-b (net +3) is the nearest miss so far. It is recorded, not built.

**§87.2 R85 §85.2(d) correction, settled** (PART 1a; medians over 119 decisions, hits / misses):

| measure | hits | misses |
|---|---|---|
| identity age | 98 | 129 |
| current band-version age | **2** | **3** |
| drawn width | 24 | 30 |

- The author's box is 17 bars, and the p25 of drawn width is 16–19.
- So the drawn box is about 1.5× the author's length, **not 7×**. The UIP object rewrites almost every few bars.
- "Old slot holder" was the wrong diagnosis. The error is in **where** the UIP writes its band, not in how old it is.

**§87.3 Anatomy of the band write** (PART 1b, plus the Lead's read of `pipes.py:66-141`)
- **24 of the 46 edge-matched misses:** the UIP did rewrite inside the candidate's window, but to its own event geometry.
  - The written band misses the candidate's edges by a median of 0.45 ABR on the hi-edge and 0.95 ABR on the lo-edge (p75 2.81).
- **22 of 46:** no rewrite happened.
  - 9 had no confirmed pivot.
  - 12 were blocked by the range-double pair gate (`SEP ≥ 8` bars, `|Δprice| ≤ DTOL`).
  - 1 was pullback-only.
- **The code explains the edge error.** A range-double band (`pipes.py:82-87`) has:
  - the *defended* edge at the double-top or double-bottom price;
  - the *opposite* edge at the **raw extreme** of the segment (`min low` / `max high`).
  - R73 measured that raw extremes match the author's edge only 41–44% of the time, while the defended-cluster edge matches 62–65% (`trade_tags.cluster_edge`, already a leaf module).
  - **Prediction, stated before measuring:** the opposite-edge error is larger than the defended-edge error.
- **Latent inconsistency.** `pipes.py:70` computes a scale-aware `dtol = max(1.0, 0.25·ABR)`, the project-standard `tol_e`, but the pair test at `pipes.py:79` uses the fixed `DTOL = 2.0`. The computed `dtol` is never used.

**§87.4 Arm RW "write the right band"** (offline estimate by BOX-LAB, read-only; 2 variants fixed now; flags default OFF, and OFF ≡ parent)
- **RW-E (edge):**
  - Every band write *of the UIP object* (birth and `uip_rewrite`) sets the **opposite** edge of a range-double band to `trade_tags.cluster_edge` over the same segment (`pipes.py:81`).
  - If `cluster_edge` returns none, the raw extreme is kept.
  - Unchanged: the defended edge, the trigger, pullback bands, shadow candidates and non-UIP boxes.
- **RW-G (gate):** the pair test at `pipes.py:79` uses the already computed `dtol` (the project-standard `tol_e`) instead of the fixed 2.0.
  - This can widen the gate on volatile days and tighten it on quiet ones. Both directions are measured.
  - Everything else is unchanged.
- **Estimate per variant** (ruler `V2.match` on the simulated box@1 band at each golden τ, so real hits; path dependence included):
  - hits lost, gained and net;
  - rewrites per panel against the parent;
  - cross-family at-risk (any change in births or caps, and carried levels);
  - the 12 fixed panels.
- **Build rule (fixed now):** build a variant only if
  - net box ≥ +3,
  - lost ≤ 2,
  - at-risk ≤ 1 in each other family, and
  - median rewrites per panel ≤ parent + 1.

  The criterion differs from R85/R86, whose arms were add-ons that must not touch existing hits. RW replaces the core write rule, so some reshuffle of existing hits is expected. The gate therefore asks for a real net gain with bounded losses, which is consistent with the M1 keep-rule (box ≥ parent).
  - If both variants pass: one build with two flags, measured separately and together.
  - If neither passes: E3 stops producing arms, and the Lead reports to the Owner with the full anatomy before choosing the next direction.

**§87.5 G-REVIEW.** Chrome has been hidden since 14:31Z (checked at 16:27Z). The Gemini tab id has changed to 1582169072 and its renderer is unresponsive. No attempt has been made. M2-TV condition (ii) still waits.

**§87.6 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds, the spec, and HOLD.

## Ruling 88 (18:41Z 23/09) - RW fails both variants; E3 stops producing arms (per §87.4); Flash Mở rộng refuses candlestick charts 3/3 while reading a control image; two Owner decisions requested; the box family is paused behind M2-TV

**§88.1 RW_EST (BOX-LAB; the first job timed out, the continuation finished at 18:00Z).**
- **Fidelity:** the parent replay of `pipes.py:50-179` reproduces the real C-3 write chain **exactly on 119/119 decisions** (bar and both edges).

| gate | RW-E (cluster opposite edge) | RW-G (`dtol` pair gate) |
|---|---|---|
| net box ≥ +3 | FAIL (−3: lost 4, gained 1) | FAIL (−2: lost 3, gained 1) |
| lost ≤ 2 | FAIL (4) | FAIL (3) |
| at-risk ≤ 1 per family | FAIL (bracket 2) | FAIL (bracket 2) |
| rewrites ≤ parent + 1 | pass (29) | pass (23; 707 writes removed) |

- **The Lead's §87.3 prediction was mostly wrong.**
  - The opposite-edge error is only slightly larger on the miss writes: median 0.62 vs 0.56 ABR against the candidate, 0.85 vs 0.91 against golden.
  - On the 16 hits the defended edge is *larger* (0.23 vs 0.19).
  - The raw extreme is **not** the bottleneck.
- **The `dtol` inconsistency is real but harmless on this corpus.** `dtol < 2.0` on every panel, so RW-G only tightens the gate. None of the 13 DTOL-blocked pivots would pass with `dtol`.
- Both flags are closed. The fixed `DTOL = 2.0` stays (§88.6).

**§88.2 E3 anatomy, final (for the Owner)**
- **Ceiling split of the 119 author boxes:**
  - 16 are hit by C-3.
  - 103 are missed. Under C-3 E3, 43–46 of those misses had an edge-matched candidate somewhere in the pool; the rest never had one.
  - DR-BOX's earlier count under v0 was 68/119 never reached. The two counts use different tolerances and engines, so they are not added together.
- **Ten variants in six arm families were tried on the selection side, and all failed their pre-fixed gates:**
  - S1-b (age cap), S2 (break-close);
  - Y (kill), Y3 (estimate), YS-a / YS-b (yield);
  - AD-a / AD-b (adopt);
  - RW-E / RW-G (band rule).
- **What is established:**
  - The UIP band is rewritten about 29 times per panel. At τ its current version is 2–3 bars old and drawn 24–30 bars wide, against the author's 17.
  - On hits both edges sit within about 0.2 ABR; on misses both edges are about 0.9 ABR off. Neither edge dominates.
  - The candidate pool rarely carries the author's geometry. That is why every slot, adopt or yield mechanism fails: nothing better is waiting in the pool.
- **Asset kept:** an exact offline replay of the UIP writer (`boxlab/rw_est.py`, 119/119). Future band-rule ideas can be screened in minutes before any build.
- **Reading:** the selection side (misses that did have a matching candidate) is exhausted with the current candidate vocabulary. Further gains need a *different notion of the author's box* (reach), not better selection. That is a research question, not an arm.

**§88.3 G-REVIEW evidence** (`review/GEMINI_R3F.md`)
- Chrome was hidden from 14:31Z to about 18:30Z. After that a new tab was visible.
- Step 1 was attempted 3 times on 3 different chats with candlestick panels (one with the axes removed): **refused 3/3**.
- A control image of synthetic geometric shapes was answered correctly. Flash Mở rộng reads images.
- The thinking trace shows it recognised the candlesticks and "price support levels", then refused. This is a **content refusal on financial charts**, not a capability limit.
- Per §84.3 and §84.4, the Lead does not switch model and asks the Owner.

**§88.4 Owner decision 1: how M2-TV condition (ii) is met.** Options:
- **(a) Allowed exception:** 3.1 Pro only for *image* reviews of charts; Flash Mở rộng stays for everything else. Pro answered all four round-3 batches, and its informational verdict found that v3 fixed the named box errors on 3/3 panels.
- **(b)** The Owner looks at the 12 paired panels himself (about 10 minutes).
- **(c)** Waive (ii). M2-TV is itself the Owner's blind look. EVAL-AUDIT's render checks (0/50 undrawable, already validated) cover the mechanics.
- **Lead recommendation: (a),** with (c) as the fallback if the Owner prefers not to use Pro.

**§88.5 Owner decision 2: direction for the box family.**
- **Lead recommendation:** pause box research and run M2-TV first, as soon as (ii) is settled.
- Reasons:
  - M1 already passes.
  - M2-TV is the real test.
  - The Owner's blind verdict tells us whether boxes are what limits usefulness before more research is spent.
- **Alternatives for the Owner:**
  - a reach study, i.e. a new definition of the author's box, such as congestion by bar overlap near a flat EMA (not the double-top pair);
  - DR-BOX recommendation 4: change the objective to own-box precision. This is the Owner's call.

**§88.6 Hygiene.** The unused `dtol` at `pipes.py:70` is recorded as dead code. It is not removed, because the parent is sealed; any cleanup waits for a future build with OFF ≡ parent.

**§88.7 Lanes.** All lanes are idle: BOX-LAB, build, G-KIT, PA-ATLAS and DR-RULES. EVAL-AUDIT holds the staged M2-TV builder. No job runs until the Owner answers.

**§88.8 Unchanged:** M1, M2 (M2-TV, threshold .60), the ruler, fixtures, thresholds, the spec, and HOLD.
