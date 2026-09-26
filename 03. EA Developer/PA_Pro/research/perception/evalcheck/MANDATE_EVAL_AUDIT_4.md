# LANE EVAL-AUDIT — MANDATE 4 (Lead, 2026-09-21 18:43Z) — 5-hour box

Mandate 3 is **accepted** (Lead Ruling 13). BOX_CEILING, SNAPSHOT, SCOREBOARD and VERIFY_LOG are exactly the instruments the program needed. The breaches were corrected in the log, not erased; that is the right way.

**The question now:** on 22/09 (from about 01:00Z) the Owner decides whether to keep or adjust the HOLD gates. The Lead will write the recommendation. Your job is to make sure every number in it is measured, reproducible and interpretable.

## Walls (unchanged)
- Write only under `evalcheck/`, and nowhere else.
- TUNE only; HOLD never read.
- Engine files read-only.
- `pa_slots` ≤ 1.
- **No deletes.**
- Log times from the clock in `EVAL_LOG.md`, at least every 45 min.
- Re-read `LEAD_RULINGS.md` at the start of each item.
- **Never end the session to ask.** When the queue is done, keep doing W3 and W5 until the box ends.

## Queue
**W1 — Blind plausibility audit** → `evalcheck/PLAUSIBILITY.md`, `plausibility.py`. This is the most important item.
- **Why:** the golden set is *lesson-selected*. Volman draws what matters for the trade he is discussing, so a valid structure he did not draw counts as a "false positive". The precision gate of ≥ 0.60 is only achievable if most false positives are junk rather than valid-but-undrawn.
- **The sample** (seed 20260921):
  - 90 engine false positives under eval_v2, stratified: 30 from v0 (`63c771d6`), 30 from the current v1, 30 from the LINE-LAB lab engine; spread across BOX, lines, levels and brackets;
  - 30 golden objects as hidden controls;
  - 30 golden misses (golden objects no engine matched).
- **Render** each item as a panel crop, with bars up to the object's decision time τ *plus* the full panel. Show only the item itself, with no label saying where it came from.
- **Judge:** a *fresh* sub-agent (`run_subagent`), blind to the source and to the golden set. It gets only `docs/perception/research/10_NGUYEN_TAC.md` and the item renders.
  - Per item, three answers:
    - **(i)** would a disciplined PA trader in the Volman style plausibly draw this, here, at this time? (yes / no / can't tell);
    - **(ii)** for misses: is it knowable from bars up to τ? (yes / no / can't tell);
    - **(iii)** a one-line reason.
  - Calibrate on the controls: report the judge's "yes" rate on golden controls. If it is < 0.8, the judge is unreliable, so say so.
- **Report:**
  - the plausible-FP rate per engine and type;
  - **a plausibility-adjusted precision estimate**: precision if plausible FPs counted as right, with a CI;
  - the knowable share of misses;
  - 10 example crops per class.
- The Lead uses this to decide whether the precision gate measures junk or lesson-selection.

**W2 — Gate-feasibility data pack** → `evalcheck/GATE_PACK.md`. Tables only; the Lead writes the recommendation. At the current hashes, and for the BOX-LAB and LINE-LAB prototypes if they exist:
- for each gated type (BOX, PATTERN_LINE, LEVEL_CARRIED, T/F, clutter), and v0 / v1 / labs:
  - cumulative recall/precision;
  - snapshot recall/precision/live clutter;
  - oracle ceiling;
  - trusted-subset recall;
  - W1's plausibility-adjusted precision;
- **the gap to each gate**;
- **the history**: the scoreboard rows through the day;
- **per-panel distributions** (not just medians) of live clutter at τ and of golden objects per panel;
- **CIs** for recall and precision: bootstrap by panel, 1,000 resamples, seed 20260921;
- **a reproducibility block**: exact commands, and all ruler and engine hashes.

**W3 — VERIFY_LOG, continuous.** Verify every builder claim as it lands, CONFIRMED or DISPUTED with numbers:
- build lane: zombie retirement, REQ-1 (b), LEVEL_CARRIED, separator;
- BOX-LAB: X3 oracle and born recall, re-run on its prototype;
- LINE-LAB: L7 and L8.

Add a scoreboard row for every new engine hash you see.

**W4 — Walls check upgrade (Ruling 13 §13.7).** Replace file-level exemptions with positive checks:
- the file imports `book_loader` or `evalcheck/cache.py`;
- it has no direct parquet or csv bar paths;
- HOLD-string matches are ignored only on comment or docstring lines.

Add tests showing that a planted violation in an exempted-pattern file is caught. Re-run on the whole repo and log the result.

**W5 — Nightly continuity.** When W1–W4 are done, keep:
- verifying (W3);
- adding scoreboard rows;
- re-rendering the 12 QA panels in `rv/` for each new v1 hash.

**At about 00:30Z,** refresh GATE_PACK.md with the latest hashes so the Lead's 01:00Z pack uses current numbers.

## End
Final message in Vietnamese, 12 lines or fewer:
- the W1 judge calibration and the plausible-FP rates;
- plausibility-adjusted precision with CI;
- the knowable share of misses;
- the GATE_PACK headline gaps;
- what was verified.
