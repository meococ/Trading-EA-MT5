# SF01 - LEAD RULINGS on DECISIONS.md

Append-only. Newest last. The Lead reviewed D1-D6 at 2026-09-21 ~02:45Z.

## Review 1 (02:45Z) - D1..D6

- **D1 structural stop snapped to a ladder rung - ACCEPT.** Two conditions:
  - Each rung is its own config and counts against the budget of at most 24 configs per family. Five
    rungs times two generators already makes ten grid cells, so size the grids with that in mind.
  - Snapping can widen the structural stop by up to 1/0.6, about 1.67x. Declare this in every spec, and
    report the realised d_struct/S distribution per config. It is descriptive and never a gate.
- **D2 generators {line1_cluster, sd_base} - ACCEPT.**
- **D3 session gate declared a priori - ACCEPT.** The matched-random baseline must use the same session
  windows. It already does.
- **D4 exact replay semantics - ACCEPT. Escalated.** The EA lane found the same born_idx vs created_idx
  divergence independently, which makes the finding credible. `families/sf_ctx.py` (exact replay, unit
  tested) is now the reference semantics that the MQL5 port must match. Separately, the Lead is checking
  which semantics built the R02 arrival bundles. That is an R02 disclosure question, not SF work.
- **D5 compute scheduling - UPDATED.**
  - The PA-PRO cap is now 4 heavy python processes (Owner-approved; `docs/CHARTER_ADDENDUM_3.md`).
  - This lane may hold up to 2 slots at once.
  - R02 holds 2 until about 03:30Z. After that, all 4 are free except while other R02 reproduction runs
    are active.
  - Your RECON note that slot 2's lock was "stale (PID dead)" was wrong. PID 37924 was alive and running
    R02 at the time. The Lead verified `pa_slots._pid_alive` from Windows python at 02:39Z: 37924 and
    34116 both alive. Staleness must only ever be judged by `pa_slots` itself, never by shell tools:
    `tasklist`/`ps` under a POSIX-style shell can report a live Windows process as dead.
- **D6 config budget shape - ACCEPT.**
- **Correction of a reason, not of the rule.** `lib/` stays off-limits for lanes, because it is the
  referee. But the reason given in D1 is wrong: FREEZE_v3 hashes no `lib/` file. Its 10 code hashes are
  all under `research/`.

## Review 2 (03:10Z) - F1 spec v2, snapshots, smoke test

- **Visual QA - PASS.** The Lead viewed 2 of the 12 F1 snapshots (EURUSD sig 5940, USDJPY sig 90222).
  Everything is drawn as SPEC v2 says:
  - the stop entry sits 1 pip beyond the signal bar;
  - `inv` sits at the probe extreme;
  - the SL is snapped to a rung at or beyond structure;
  - TP is 2R.
- **Spec v1 -> v2 from census alone: allowed, and it does not use a logic revision.** A re-spec made
  before ANY outcome exists is still pre-registration. The budget of 2 logic revisions counts only
  changes made after outcomes have been seen. Keep the census report free of outcome fields so this
  stays provable. The ledger holds both hashes, which is fine.
- **Wording to fix in SPEC v2 (no rule change needed).** The approach-side gate is
  `c[t-1] <= z.hi` (ceiling) / `c[t-1] >= z.lo` (floor). That lets the previous bar close INSIDE the
  band, so the population includes 2-bar rejections: bar t-1 closes in the zone and bar t closes back
  out. USDJPY sig 90222 is one of them. The text says "the probe must arrive from outside the band",
  which is stricter than the formula. The formula is what was pre-registered and it is a legitimate
  price-action variant, so keep it. Fix the sentence at the next spec touch so text and formula agree.
  A strict "c[t-1] outside the band" variant may only come as a declared revision.
- **Smoke-test error - expected and good.** `pa_eval` refused a warm-up-bar signal ("signal bar 1900
  ... first live bar = 5818"). The referee guard works. The detector must emit nothing before
  `first_live_idx`.
- **SUMMARY is stale.** FACTORY_LOG `## SUMMARY` still reads "F1 spec drafted" (02:18Z), but F1 is at
  spec v2, census, snapshots and smoke test. Keep it current at every stage change.
- **Channel.** From now on, re-read this file (`rounds/SF01/LEAD_RULINGS.md`) at the start of every
  family and whenever you append to DECISIONS.md.

## Review 3 (04:31Z) - SF01 closed: 0/6 survivors, verdicts upheld

- **Independent check.** The Lead recomputed the gates from all six SCREEN.json files. 0 of the 120 cells pass ALL gates. Every DEAD verdict is upheld.
- **D7 (provider wrapper adds utc_start/utc_end): ACCEPTED.** It is the sanctioned hook, and lib/ stays untouched.
- **D8 (F2 anchored at the break bar, pre-outcome): ACCEPTED.**
- **D9 (tag = entry index): ACCEPTED, with one correction.**
  - F1 was NOT re-run after the fix. D9 says it was, but F1's SCREEN.json is stamped 03:26:37Z, which is before the fix.
  - So F1's lift fields and its ledger rows come from the corrupted matching.
  - The verdict cannot change, because PF and t do not depend on tags. The record still has to be clean. Task Q0 of SF02 re-runs F1 with the fixed tags and adds "D9-bis" with the new trial ids.
- **D10 (F5 inv at the deepest point of the pullback, pre-outcome): ACCEPTED.**
- **D11 (F6 box_atr rescaled, pre-outcome): ACCEPTED as a legal correction.** But at 4 x ATR the "box" is no longer a Volman box (see the QA below).
- **F6 "v3" was an estimate only; no v3 was run.** That is correct: no post-outcome revision.

### Visual QA (the Lead viewed 3 snapshots)
- **F3 EURUSD sig 214771: PASS.** Probe above the ceiling, close back inside, sell-stop below the signal bar, `inv` at the probe extreme.
- **F4 EURUSD sig 204768: conforms to the spec, but the entry is a chase.**
  - The buy-stop sits about 12 pips above the zone, after a 2-bar thrust.
  - The stop is below the zone, so it is far away, and the entry comes after the move.
  - A pro enters the pullback AT the zone on a small signal bar, not after the thrust.
- **F6 GBPUSD sig 226739: conforms to v2, but it is NOT a Volman box.** The 12-bar window is a spike followed by a fade, about 23 pips tall (about 4 x ATR). It is not a tight, horizontal build-up of small bars. The log's claim of "textbook box-press-break geometry" overstates it.
- **All three snapshots show 8-12 overlapping zone bands within +-40 pips.**
  - Arming keeps up to 6 zones within +-2 x ATR(H1). On EURUSD that is roughly one zone every 10 pips.
  - So "price is at a zone" is almost always true, and the zone condition filters out almost nothing.
  - This is a perception problem, not a setup problem.

### The Lead's reading of the numbers (input to SF02)
- **The matched-random baseline itself loses.** In the thick cells, at S 11-32 pips, it shows PF 0.86-0.94 and -0.05 to -0.09 R per trade (costs plus intraday flats). That is the drag a setup must beat.
- **Lift over random is about 0 in every thick cell of every family.** The entries, as defined, carry no directional information at M5.
- **Every positive pocket has N < 100.**
- **Next:** blueprint §8 rung 2 (wider geometry / HTF context) and rung 3 (the exit axis), plus a perception fix (salient zones instead of every zone). The mandate is in `rounds/SF02/MANDATE.md`.

### Hygiene
- **FACTORY_LOG timestamps were not taken from the clock.** Entries run up to 06:40Z, but the job ended at 04:24:33Z. From now on every timestamp comes from the system clock (`date -u` / `datetime.now(timezone.utc)`) and is never typed by hand.
