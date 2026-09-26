# REVIEW_ECON1 — neutral review rounds for T-VPA-ECON-1

Reviewer: independent subagent (general), read-only + light python/csv/hash,
cwd `03. EA Developer/EA_VolmanPA`. Two rounds (budget ≤2): round 1 FAIL
(one metadata defect), round 2 PASS after the fix.

## Round 1 — VERDICT: FAIL (6/7 checks PASS)

- CHECK 1 look-ahead in orders/fills: **PASS** — fill window `[starts[sig+1],
  min(starts[sig+1+V], next_end[sig]))`; exit scan from the fill index; SL
  before TP in every M1 bar (`vpa_econ1_sim.py:119-132`); flats use the current
  bar; tests `expiry_no_lookahead` / `same_bar_sl_first` present.
- CHECK 2 prereg before outcome: **FAIL** — the prereg's true SHA256 is
  `644DBCBA91B9859AF598906C8BB9C7D8CAB034CBCE99675554B48938C5BE9663` (mtime
  17:52:06, earlier than every outcome file: ordering sub-check PASS), but the
  string recorded in `vpa_econ1_run.py:29`, `vpa_econ1_explore.py:21`,
  `ECON1_RESULTS.md:3` and `ECON1_METRICS.json:258` was a **63-char
  transcription error** (`…5989068BB…` instead of `…598906C8BB…`). The engine
  SHA (`87D3C735…`) and DR3 code SHA (`73497484…`) sub-checks PASS.
- CHECK 3 costs: **PASS** — `C_RT_P90_PIPS {"EURUSD": 1.0}` cited to
  `COST_FEASIBILITY.md:75`; applied once (`fill = fill_raw + d*c`,
  `vpa_econ1_sim.py:111`); scenarios gross/x1/x1.5/x2; PF monotone decreasing
  with cost (0.992 → 0.795 → 0.720 → 0.667); TRADES_DESIGN.csv cost columns
  all 1.0/1.0.
- CHECK 4 random matching: **PASS** — cell (session, hour, dow, month), K=20,
  direction mix; independent check: all 42,257 rows' cell keys identical between
  `entry_bar_idx` and `src_signal_bar_idx`, 0 mismatches; long share 0.4967 vs
  DR3 0.4914.
- CHECK 5 recompute from TRADES_DESIGN.csv: **PASS** — N 2436, WR 30.17%, PF
  0.795195, b 1.839227, total R −337.49, max DD 84.19%, exit mix
  617/1618/139/61/1/0 — matches the results md to 6 dp.
- CHECK 6 split discipline (G5): **PASS** — y0/y1 = 2016/2021 in every script;
  loaded frame reproduced (440,040 M5 / 2,208,641 M1, 2016-01-03 →
  2021-12-31); no VAL/OOS/HOLDOUT load path.
- CHECK 7 no outcome leakage into the prereg: **PASS** — only definitions and
  thresholds; the observed-value scan found only the word "EXPIRED" in the
  order-model definition.
- Extra finding (not a check): **Thursday/Friday off-by-one** — the weekday
  formula `((t//86400)+4)%7` is Sunday=0, so the `dow == 4` "Friday" veto/flat
  fires on Thursday 20:00 server (all 61 FRIDAY-reason exits are Thursday).
  Inherited from the frozen P1 baseline; DR3 and the matched random use the
  identical rule so the lift is unaffected.

## Post-round-1 fixes (producer, no re-simulation)

1. The prereg SHA corrected in the four artifacts (verified: every
   `644DBCBA…` occurrence is now the full 64-char string; the prereg file itself
   was never edited after the freeze — mtime 17:52:06).
2. `ECON1_RESULTS.md` §6 DEVIATIONS & CORRECTIONS added: the SHA correction;
   the Thursday/Friday deviation + the sensitivity (excluding the 61
   FRIDAY-reason fills → N 2375, WR 29.56%, PF 0.784 vs 0.795 — the deviation is
   slightly favourable to DR3, verdict unchanged; not re-run per G4); the x1-only
   trades CSV; the 115 out-of-session signal bars / matched-subset lift; the
   within-bar fill-bar assumption.

## Round 2 — VERDICT: PASS

- FIX 1 SHA: **PASS** — hash matches, 4/4 artifacts carry the full string, no
  63-char remnant; prereg mtime 17:52:06 < CSVs 17:55:45 < JSON/results 18:04:07.
- FIX 2 deviations section: **PASS** — §6 lines quoted; the verdict table and §2
  numbers unchanged (PF x1 0.795, gross 0.992, N 2436, DD 84.19%, b 1.839,
  lift +0.24pp [−1.61, +2.14]).
- FIX 3 no tampering: **PASS** — TRADES_DESIGN.csv still 2,436 rows, PF
  0.795195/WR 30.17% recomputed identically; JSON scenarios unchanged;
  RANDOM_MATCHED.csv 42,257 rows.

Open issues (round 2): all outcome artifacts are untracked in git, so
"unchanged vs round 1" rests on the round-1 quoted values + exact independent
recompute from the untouched CSVs (agreement to 6 dp); prereg immutability is
evidenced by mtime + content hash only (no VCS history).

Verdict: deliverables accepted; the economic verdict is FAIL (G6), unchanged by
the fixes.
