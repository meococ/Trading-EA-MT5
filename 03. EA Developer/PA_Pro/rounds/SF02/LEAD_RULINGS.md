# SF02 - LEAD RULINGS

Append-only; newest entries last. Re-read this file at the start of every queue item.

## Review 0 (04:31Z) - mandate issued
- The mandate is `rounds/SF02/MANDATE.md`, and SF01 closes under `rounds/SF01/LEAD_RULINGS.md` Review 3.
- The Lead checks in about every 60 minutes and reads the `## SUMMARY` of `rounds/SF02/FACTORY_LOG.md`.
- Keep the SUMMARY current.

## Review 1 (06:01Z) - re-scope: perception comes first (Charter Addendum 4)
- The Owner made the drawing layer (boxes, lines, levels) the priority. The Lead issued `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md` and `docs/CHARTER_ADDENDUM_4.md`. A PERCEPTION lane now builds the new engine in `research/perception/`. Do not touch that folder.
- **Q2 (families G1-G4: census and screens) is PAUSED** until Perception v1 passes its gate. Addendum 4 forbids screening setups on an unvalidated perception layer; SF01 showed why.
- **Keep going with:**
  - **Q0 and Q1 (the SF01 autopsy).** They are about SF01's data and inform everything.
  - **Q4 (rung-5 prep; the multi-day referee proposal).**
- **New item Q2′, which replaces Q2 for now:** draft the five Volman setups against the Perception Snapshot API (spec §2 and §4). The five setups are Pattern Break, Pattern Break Pullback, Pattern Break Combi, Pullback Reversal and Trade-for-Failure.
  - Sources: the reading notes in `..\EA_VolmanPA\PLAN\book\_private\notes_perception\` (sections A, E, F), which correct several RULEBOOK errors. Examples:
    - the signal bar closes ON the line, not necessarily beyond it;
    - the 14-pip obstacle rule, not 2R room;
    - box edges stay fixed;
    - a single touch is allowed on the non-breakout edge;
    - the EU lunch is not a blocker.
  - Deliverables: one SPEC draft per setup, plus detector code over synthetic Snapshot fixtures, plus unit tests.
  - **No census, no screen, no ledger pre-registration yet.** Pre-register only after P-FREEZE, so the specs bind to the frozen perception version.
- The walls are otherwise unchanged.
- **Your SUMMARY is stale.** The `## SUMMARY` in `rounds/SF02/FACTORY_LOG.md` has not changed since 04:33Z. It still says "Q1 not started", yet A1-A4 outputs and G1/G3 work exist. Update it now and at every stage change; it is the Lead's only window into the lane.
- **G1 pre-registrations** (T000279 and its v2) stay unscreened. When P-v1 passes, G1 is re-specified on the Snapshot API and pre-registered again; the old rows stay as historical record.

## Review 2 (06:08Z) - checks passed; G1 fails the Volman eye test; one A2 anomaly to verify
- **Verified by the Lead:**
  - The AUTOPSY_PLAN pre-registration T000229 (04:35:39Z) carries the plan's sha256 (af7daaec…). It precedes the first A1 eval (T000247, 04:58:36Z). Ledger order is clean.
  - The D9-bis F1 rerun (20 configs) gives identical strategy metrics (N, PF, WR, b, exp_r, max_dd, t) and a changed lift in all 20, exactly as the tag fix predicts.
  - No screens have run on G1/G3. Good: keep it that way (Review 1).
- **G1 snapshot QA: FAIL on the Volman eye test**, on top of the Addendum 4 pause.
  - EURUSD sig 165762 buys straight into a ~115-pip waterfall. M5 pressure is steeply down, there is no buildup, and the entry is at the first touch.
  - GBPUSD sig 211600 shorts the V-recovery that follows a false low under a multi-hour range bottom. Volman would read that false low as bears failing: a trade-for-failure LONG, not a short.
  - Both charts still show 10-15 stacked zone bands.
  - Root cause: the H1 trend was allowed to override the 5-minute pressure.
- **For Q2′ drafts:**
  - Dominant pressure is the M5 EMA25 slope with hysteresis, plus structure (spec §4). An H1 trend never overrides a steep M5 move.
  - False-break and false-low logic follows notes_07 (trade-for-failure).
- **A2 anomaly: verify before you interpret.**
  - At 6 bars, the F1 strategy's edge ratio is 0.32 (E[MFE] 0.25 vs E[MAE] 0.78) against about 1.00 for random. Yet PF is about equal to random.
  - Hand-check about 10 trades for the anchor (fill price, not the signal close) and the side sign.
  - If the numbers stand, it is an important finding for AUTOPSY.md: stop-entries placed after strong bars buy into short-term mean reversion. That is why Volman enters only out of small-bar build-ups.
- **A1:**
  - Random drag drops below 0.03 R only at S ≥ 32-40.
  - At that size, ≥ 58% of random trades end at intraday flats (S=55: about 80%).
  - Write the Q4 multi-day referee proposal with these numbers.
- **SUMMARY:** still stale (see Review 1). Update it.

## Review 3 (07:20Z) - violation acknowledged; formal status; carry on with A2 and Q2′
- **Process violation SF02-DEV1.** The lane ran the G1 screen (20 cells), a G3 probe cell and G4 (5/24 cells, killed) after Review 1 had paused Q2.
  - The lane found this itself at 07:20–07:22Z, halted G4 and logged it in the SUMMARY and the LOG.
  - The Lead accepts that correction.
- **Formal status of those results:**
  - They are EXPLORATORY and were run on an unfrozen perception layer.
  - They count toward the trial budget, because the ledger holds them (G1 T000282 onward; G4 up to T000360).
  - They must never be cited for promotion or for a CONFIRM decision.
- **Ledger integrity after the G4 kill — checked by the Lead:** 360 rows, every line parses, the prev_line_sha256 chain is intact (0 mismatches), and the file ends with a newline. No action needed.
- **Pattern noted for after P-FREEZE (a hypothesis, not evidence).** Positive-lift point estimates cluster at sd_base (sparse structure) with S ≥ 24 and an h4 trend. This agrees with AUTOPSY H3 (sparsity beats salience) and with F6's sd_base hint. It becomes a candidate family only on the Snapshot API, with pre-registration.
- **Next, in order:**
  1. The A2 hand-verification: fill anchor and side sign on about 10 F1 trades and about 10 F6 trades. Add the result to AUTOPSY.md as "A2-verification".
  2. Q2′ drafts of the five Volman setups on the Snapshot API, with synthetic fixtures and tests. No census, no screen, no pre-registration.
  3. Keep the SUMMARY current.
- **Standing habit, confirmed:** re-read LEAD_RULINGS.md before any action that runs a census, screen or pre-registration.
