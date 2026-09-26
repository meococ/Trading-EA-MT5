# LEAD_DECISIONS_ECON1 — saved verbatim (task T-VPA-ECON-1)

## Lead verdict on T-VPA-DR3: ACCEPTED — F5 fidelity PASS, F6 cadence NORMAL
The Lead recomputed the key numbers:
- Majority vote: 84/120 accepted vs 16/60 rejected. Difference +43.3pp, CI [+28.2, +55.4].
- Dual agreement, using binary agreement: +53.8pp [+37.1, +65.7]. Using your exact-grade definition: +56.0pp. Both pass.
- Lead blind spot-check (file hash 3bdb1a6c…, written before unblinding): accepted A/B 6/12, rejected 0/8. Lead vs grader majority agree on 13/20 cases; all 7 disagreements are graders more lenient (Lead C, graders A/B). So the absolute A/B levels are inflated and only the discrimination holds.
- Cadence is 13.85/week.

Now the detector's frozen code (DR3 prereg SHA A61F06BA…) goes to its first economic test.

## LEAD DECISIONS (binding)
- **G1 — Economic prereg first.** Write and freeze `research/VPA-DR3_ECON1_PREREG.md` (record its SHA256) BEFORE any fill or outcome is computed. It must contain:
  - the signals: DR3-accepted only, code SHA frozen;
  - the order model: stop order 1 pip beyond the signal-bar extreme, valid for V=3 bars, cancelled on invalidation or on session end;
  - the bracket: S=8 / TP=16 pips, fixed, with no break-even, trailing or partials;
  - the same-bar TP+SL rule: conservative, SL first;
  - the fill cost and cost scenarios x1 / x1.5 / x2, taken from `PLAN/COST_FEASIBILITY.md` (c_rt p90) and the repo evidence;
  - the safety flats (news ±20', Friday 20:00 server, daily 22:00 server);
  - the split: DESIGN 2016–2021 ONLY;
  - the metrics and gates below;
  - the matched-random baseline design.
- **G2 — News filter.** Find an existing news calendar in the repo first (research it). If none exists, write `NEWS: NOT AVAILABLE`, run the baseline without it, and report a sensitivity check that excludes the fixed high-impact windows 12:25–12:45 and 13:25–13:45 UTC plus FOMC days if you can derive them.
- **G3 — Gates**, from GOAL.md, the HYP prereg and the G3 lift rule:
  - PF: x1 > 1.30, x1.5 ≥ 1.25, x2 ≥ 1.00;
  - gross PF ≥ 1.10;
  - N ≥ 500 fills;
  - max DD ≤ 6% at 0.5% risk per trade;
  - realised b ≥ 1.70;
  - LIFT: DR3 win rate minus matched-random win rate ≥ +14.1pp at x1 and ≥ +18.2pp at x2, with the lower bound of the 95% CI of the lift > 0.
  - **Matched random:** same session and hour-of-day, same weekday, same month, same direction mix and same bracket. Use K ≥ 20 random entries per signal, and reuse the existing random-baseline tooling where possible.
- **G4 — One run.** Run exactly ONE verdict of the frozen DR3, across the cost scenarios. No parameter changes and no variant runs.
  - An EXPLORATORY section is allowed, clearly labelled and with no effect on the verdict: win rate and PF by feature tercile (room_r, ema_dist_atr, squeeze, lunch, session, PB vs Combi, long vs short, per year). It generates DR4 hypotheses only.
- **G5 — VAL, OOS and HOLDOUT stay sealed.** Do not load them.
- **G6 — Verdicts:**
  - all gates pass → PASS, and the Lead then decides whether to open VAL;
  - any gate fails → FAIL, with a per-gate table. The Lead escalates to the Owner.

## SUGGESTED PARALLEL SPLIT (you orchestrate it)
- **SA1:** fill/exit simulator plus unit tests, with hand-computed fixtures for trigger, expiry, invalidation cancel, same-bar TP/SL, gaps and flats.
- **SA2:** matched-random baseline generator plus tests.
- **SA3:** cost scenarios from the repo evidence (cite the file and line).
- **SA4:** news calendar research, or the fallback windows.
- Main agent: freeze the prereg (after SA3/SA4 give inputs, BEFORE any outcome), join everything, run once, produce the verdict.
- **SA5:** neutral reviewer at the end.

## DELIVERABLES
- `PLAN/econ1/ECON1_RESULTS.md`: gate table per cost scenario, lift with CI, equity/DD summary, per-year table, and the EXPLORATORY section.
- `PLAN/econ1/TRADES_DESIGN.csv`: one row per fill, including exit reason and cost.
- `PLAN/econ1/RANDOM_MATCHED.csv` or a summary.
- `research/REVIEW_ECON1.md`.

## ACCEPTANCE (SELF-CHECK, each PASS/FAIL with evidence)
- [A1] The prereg SHA is quoted, and its mtime is earlier than any outcome file. Show the timeline.
- [A2] Simulator tests pass (verbatim counts). The same-bar SL-first rule and the no-look-ahead fill rule are each tested.
- [A3] The matched-random baseline shows its matching dimensions, and K is stated.
- [A4] The verdict table has every G3 gate, per cost scenario, with the numbers.
- [A5] No VAL, OOS or HOLDOUT data was loaded. Show the date range of every loaded frame.
- [A6] Reviewer VERDICT PASS (≥90% VERIFIED, 0 CRITICAL). The reviewer checks:
  - look-ahead in orders and fills;
  - the prereg-before-outcome order;
  - how costs are applied;
  - random matching;
  - that the numbers can be recomputed from TRADES_DESIGN.csv.
- [A7] The Machine resources rules were followed, and you state how many sub-agents ran in parallel.

## STOP RULES
Anything that would require touching VAL, OOS or HOLDOUT, or changing DR3 → stop and ask.
