# PLAYBOOK - C-round 2 to the P-FREEZE package (Lead, 2026-09-22 12:55Z)

This playbook replaces step-by-step rulings. Every lane runs its queue to the
end, decides its own keeps under section 3, and escalates only for the
reasons in section 8. The Lead checks once an hour and at each round close.
LEAD_RULINGS.md still wins if the two ever conflict, but new rulings will be
rare. Read this file once in full; afterwards re-read only section 1 (state)
and any new ruling.

## 0. BOX RESEARCH ROUND (LEAD_RULINGS R56, 22/09 14:41Z) - read this first

R55's freeze is WITHDRAWN. The Owner: the machine is wrong on boxes, so
research a different approach. C-round 3 is a box research round.
- Engine code is OPEN again. Keep rules: sections 3 and 4, unchanged.
- The goal is still box@1 >= 16/119 with level/line -1 at most and the
  clutter median <= 5.0 (M1 unchanged).
- Queues: R56 s.56.4 (BOX-LAB = BOX RESEARCH: R1 evidence, R2 approaches,
  R3 prototype), s.56.5 (build: K7-K9 verdicts, F1 merge -> STABLE C-2,
  the research dataset, formal A/Bs), s.56.6 (EVAL-AUDIT: verify, F1
  identity, null/CV review, re-measure hand-offs). They replace section 5.
- Section 7's calendar is void: no P-FREEZE date until box >= v0.
- No lane pauses itself or ends early (R55 s.55.7 is withdrawn). Sections
  8 and 9 apply in full.
- HOLD stays sealed. No lane changes M1, M2, a threshold, the ruler, the
  fixtures or the spec.

## 1. State at start (update this section's numbers in your own log, not here)

- STABLE C-1: `9acaa206c8d386dc` (K1-K6).
- C-2 keeps so far (PROVISIONAL until EVAL-AUDIT verifies, section 4.6):
  - K7 `marker.off` (ink-only): headroom parent `81f7503f`; clutter median
    5.00 -> 4.67; panels <= 5.0: 90 -> 103; level +1.
  - K8 `box.cong_pivedge` on K7: default engine `be4eea2686f0b48e`.
- M1 on `be4eea26` (canonical `_m1.py`, ruler eval_v2 `50e11fd5`):

  | family | now | v0 target | gap |
  |---|---|---|---|
  | box@1 | .084 (10/119) | .134 (16/119) | 6 hits short |
  | level@1 | .105 (8/76) | .066 | met |
  | line@2 | .104 (20/193) | .093 | met |
  | clutter median | 4.67 (101/179 panels <= 5.0) | <= 5.0 | met |

- Suite on the default engine: 65/72, all seven failures in the named set
  (section 3.4).

## 2. Goal and finish line

- Goal: box@1 >= 16/119 while level and line stay >= v0 and the clutter
  median stays <= 5.0. Secondary: cure the seven named fixtures.
- Finish line: the FINAL STABLE for the P-FREEZE package, 24/09 05:30Z
  (section 7). After that no engine change; EVAL-AUDIT builds the M2 pack.
- The Owner decides P-FREEZE, M2 and every threshold. No lane changes M1,
  M2, a threshold, the ruler (eval_v2 `50e11fd5`), the fixtures or the spec.

## 3. Keep rules - apply them yourself

Every arm is a same-hash A/B: both arms in ONE process, ONE code state,
params frozen for the run (R36 s.36.7). Report the full M1 row, bracket@1,
the clutter median AND the margin (panels <= 5.0) for both arms.

3.1 Generation or selection keep (s.34.5). ALL of:
  a. the target family's hit count goes up;
  b. no other M1 family loses more than 1 hit;
  c. clutter median <= 5.0;
  d. no new suite failure (3.4);
  e. flag OFF == parent on objects + cand_log + events, 576/576 canonical
     (1728/1728 for anything touching many flags).

3.2 Ink-only keep (s.41.3 + R50 s.50.2). ALL of:
  a. no M1 family loses any hit;
  b. the clutter median does not rise;
  c. the margin rises by at least 5 panels;
  d. no new suite failure; e. flag OFF == parent.

3.3 Fixture-cure keep (R44 s.44.2): the unmodified suite is 72/72 AND
  3.1 or 3.2 passes.

3.4 Suite definitions. The NAMED SEVEN are: test_pullback_end_box_birth,
  test_range_box_double_top, test_false_break_wick_keeps_edge,
  test_break_close_beyond_edge, test_tease_vs_proper_break_class,
  test_tf_relabel, test_reanchor_on_new_double_top.
  - A "new failure" is any failing test OUTSIDE the named seven. It blocks.
  - Re-breaking a named-seven test that the parent had cured is a "fixture
    regression": log it by name. It does not block, but between two arms
    with equal M1 the one without regressions wins.
  - Always list the failing tests by name. Never write only a count.

3.5 Behaviour-neutral change (performance, pip size, rendering, logging
  outside cand_log/events): TUNE 1728/1728 byte-identical (canonical) +
  suite unchanged. Nothing else.

3.6 Anti-overfitting. Everything is scored on TUNE, where M1 is measured.
  - Prefer one mechanism and at most one or two parameters per arm.
  - State the parameter value BEFORE the A/B, with its reason (a TUNE
    shape statistic, a spec rule, a round number). Never sweep a weight
    and keep the best by M1. A robustness grid AFTER a keep is fine and
    is logged as a robustness note, not a new keep.
  - Every keep names its flipped goldens (miss->hit and hit->miss).

3.7 Stop rule. An item that fails with two variants is closed for this
  round: log the verdict with numbers and move to the next item. Do not
  try a third variant unless a new diagnosis names a different mechanism.

## 4. Mechanics

4.1 The build lane owns the parent chain. After each keep: flip the
  defaults, verify 8/8 default == ON arm, snapshot the engine files to
  `_scratch/freeze_candidates/<hash>/` with SHA256.txt, and log
  "PARENT <hash> = STABLE + K7..Kn".
4.2 Every new arm is measured against the CURRENT parent. When the parent
  moves while your arm runs, re-run the pair at the new hash before you
  claim a keep.
4.3 BOX-LAB hands off through REQUESTS.md: arm name, flag names and values,
  hash, the lab A/B row (both arms), the margin, the identity result and
  the flipped goldens. The build lane runs the formal A/B within 90 min.
4.4 File ownership: build owns every engine file except the flagged box
  code in boxes.py (BOX-LAB). params_v1_1.json: only additive keys with
  default OFF, one writer at a time (take it, write, release in your log).
4.5 Flag-OFF identity is checked when the code is written, before any
  A/B (the s.45.2 lesson), and again in the keep row.
4.6 Provisional keeps. The next arm may build on a provisional keep. When
  EVAL-AUDIT fails a keep: revert it, re-run the arms that depend on it,
  log both.

## 5. Lane queues (work top to bottom; decision tree on every item)

For every item: PASS -> keep (or hand off), log, next item.
FAIL -> log the verdict and the mechanism, next item. Never idle: when the
queue is empty, work your standing backlog (5.x.S).

5.1 BUILD (session longing-animal)
  B1. Conversion-in-place for the named seven (R51 s.51.4.2), time box
      18:00Z. A CONTEXT_RANGE that meets a priority-1 box candidate becomes
      that box (same object, relabel + re-edge, like asia_convert): zero net
      births. Keep per 3.3; if it cures some but not all, keep per 3.1/3.2
      and log which. On fail: add the numbers to FIXTURE_CONFLICT.md.
  B2. Formal A/B of every BOX-LAB hand-off (4.3), before anything else once
      it lands.
  B3. Ink-only arms from your marginal-panel table, one at a time (3.2):
      (i) LABEL_TF births that the freed marker budget re-creates;
      (ii) CONTEXT_LINE only while no structural line is live;
      (iii) LEVEL_CARRIED only when it is the nearest level ahead of price.
      Skip any whose simulation shows an M1 hit loss.
  B4. At 20:30Z: merge the F1 patch (3.5 identity) - see section 7.
  B5. Before your job's timeout (15:40Z): a hand-over line
      "HANDOVER <time> next=<item>". The Lead resumes the session.
  B.S Standing backlog: (a) line slope realism - engine median slope 5.37
      vs author 9.2 pips/h: one flagged arm, keep per 3.1 on line;
      (b) level robustness: list the 8 level hits and the nearest misses;
      (c) M15 notes (lab only, no engine edits): which bar-count params
      need x1/3.

5.2 BOX-LAB (session woolen-bugle)
  X1. Pivot-edge support as ONE box-score term (R51 s.51.5.1). First the
      diagnosis on the 32 score-starved right candidates (below_min_score
      14, outranked 10, rate_limited 8): does "both edges within tol of a
      prior confirmed pivot" separate them from the objects that beat or
      blocked them? Report the counts. If yes: one flag, one weight set by
      a stated rule (3.6), lab A/B on the current parent, hand off if 3.1
      passes in the lab.
  X2. If X1 fails: in-window replacement for rate-limited boxes (the 8):
      a better-scoring box candidate inside the 72-bar rate window replaces
      the box born earlier in that window (lc_score_pick pattern).
  X3. Score-floor diagnosis for the 14 below_min_score: which score terms
      hold them under 5.0? Lab note; an arm only if one term explains most.
  X4. Re-run your covered-but-missed anatomy on every new parent, and keep
      the table current in BOX_LOG.
  X.S Standing backlog: the old-structure level registry design for the 38
      no-edge goldens (sources that beat the null: pivots, close extremes of
      the TRIGGER's window, session high/low) - lab prototype and coverage
      against the density-matched null (section 5.3 E2) - and
      BOX_INTEGRATION.md updates.

5.3 EVAL-AUDIT (session platinum-airedale), from about 14:15Z
  E1. Verify every keep within 60 min of its keep line: own-scorer M1,
      margin, OFF identity, the suite by name. Start with K7 and K8.
  E2. Null review of BOX-LAB's sources: a density-matched null (shift each
      golden only within the price range traded in its lookback) and the
      close_ext circularity check (re-measure on the trigger's window).
  E3. Independent check of the F1 identity claim before the 20:30Z merge.
  E4. Fix the GATE_PACK_C1 carried-debt line (R49 s.49.1).
  E5. The Owner's human-ceiling kit by 23/09 06:00Z (R49 s.49.5.4).
  E6. GATE_PACK_C2 at the round close (section 7).
  E7. The M2 pack on the FINAL STABLE by 24/09 09:00Z (M2_PACK_PLAN.md).
  E.S Standing: hourly wall audit (GATE_PACK_9283b389 sha, test_engine.py,
      evalcheck, HOLD untouched) and a future-timestamp scan of every log.

5.4 SCALE: finish the R48 queue and end. The Lead relaunches it on each
  round's STABLE for the census.

## 6. Box strategy notes (why the queue is ordered this way)

- In C-1, selection gave 6 of 7 box hits; generation 1.
- The covered-but-missed anatomy: 0 boxes are born and then lost; 32 of 46
  right candidates die before birth on score. The next hits are on the
  birth side.
- Pivots are a real edge source (null: .88 vs .34). pivedge (K8) shows high
  pivot-confirmation density lifts salience; X1 applies that to every box
  candidate without new births.
- Clutter headroom is the currency: every box lever spends margin. Buy
  margin with ink-only keeps (B3) before spending it.

## 7. Round calendar (assumes P-FREEZE 25/09 as proposed; the Lead updates
this section only if the Owner changes the date)

- C-2 close: 20:30Z engine code close -> build merges F1 -> EVAL-AUDIT
  1728/1728 identity by 21:15Z -> build logs "STABLE <hash>" by 21:30Z and a
  one-screen status (R43 s.43.4 item 4) -> GATE_PACK_C2 by 22:30Z.
- C-3 opens automatically at 22:30Z 22/09 on STABLE C-2 with this same
  playbook (remaining items first). Close 23/09: code close 10:30Z, STABLE
  11:30Z, GATE_PACK_C3 12:30Z.
- C-4 opens at 12:30Z 23/09. Close 24/09: code close 04:30Z, FINAL STABLE
  05:30Z, GATE_PACK_C4 07:00Z, M2 pack 09:00Z.
- After FINAL STABLE: no engine edits. Lanes write docs only.

## 8. Escalate to the Lead ONLY for these (write a line starting
"ESCALATE:" in your log, stop that item, continue with the others)

1. A wall would be crossed: HOLD, MT5, deletes, edits to fixtures / ruler /
   evalcheck results / GATE_PACK_9283b389, git, W lanes, bars outside the
   TUNE panels or DESIGN 2016-2021.
2. Flag-OFF identity fails and you cannot find the cause in 30 minutes.
3. Anything would change M1, M2, a threshold, the ruler, the fixtures or
   the spec.
4. Two lanes need the same file at the same time.
Everything else: decide by this playbook and log it.

## 9. Hygiene (hard rules)

- EVERY log line is stamped by `research/perception/tools/logline.py` or
  the system clock at the moment of writing. Never type a time by hand and
  never use a planned time. Three lines were stamped in the future today.
- Log at least every 30 minutes, even mid-run.
- Read LEAD_RULINGS.md from the end at every loop; log
  "rulings read up to Rnn".
- pa_slots <= 1 per lane, BelowNormal. evalcheck scripts are imported, never
  run as programs. No deletes: quarantine.
- Never end your job early. When the queue is empty, work the standing
  backlog. Before your job's timeout, write "HANDOVER <time> next=<item>".
- Never stop to ask. The Lead answers escalations at the next hourly check.
