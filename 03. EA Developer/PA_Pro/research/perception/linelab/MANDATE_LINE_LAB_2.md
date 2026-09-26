# LANE LINE-LAB — MANDATE 2: integrate (Lead, 2026-09-21 18:04Z) — 4-hour box

**L1–L4 are accepted** (Lead Ruling 12). This is the best-run lane of the day. The work was honest (the "only `age_min` passes" flag included) and fast, and the lab beats both engines: v2 recall 0.141 vs v0 0.109 and v1 0.076; trusted-subset recall 0.170.

**You now integrate your own L4 into the engine** (Ruling 12 §12.3). The build lane is told not to touch the files you own.

## You own, during integration
- `research/perception/lines.py`;
- the `pattern_line` and `context_line` sections of `params_v1_1.json`. Edit them **str_replace-style only**, never as a whole-file rewrite, because the build lane edits other sections of the same file. Each param leaf keeps its provenance entry;
- new test files for lines under the engine's test folder. Follow the existing layout: find where `test_engine*.py` / `test_v1*.py` live.

Everything else stays read-only: `engine.py`, `salience.py`, `boxes.py` and the other engine files, `eval.py`, `evalcheck/`, and golden.
- If a change needs salience, for example a line ink budget, write it to `linelab/REQUESTS.md`. The Lead rules and the build lane implements.
- Log in `linelab/INTEGRATION_LOG.md`, not DECISIONS.md, so two lanes do not write one file at once. Use one DECISIONS-style entry per change: what changed, the params with provenance, metric deltas, and the engine hash before and after.

## Queue
**L5 — Port L4 items 1–7** into `lines.py`: open trigger, leg/session anchors, over 2·tol, drift ×2, span 360, ≥ 3 touch events, and anti-churn with stale retirement at 60 bars. Also:
- port T1/T2 into the engine test suite;
- keep **all** existing engine tests green, and report the counts before and after.

**L6 — Measure with the full engine**, which is what counts, on all 198 TUNE panels under the official ruler (`eval_v2` `50e11fd5`).
- PATTERN_LINE recall and precision, trusted-subset recall, ink per panel.
- **Every other type too.** The line change must not regress BOX/BRACKET/LEVEL through salience interplay.
- Clutter.
- Record the engine hash. Add a row with EVAL-AUDIT's `evalcheck/scoreboard.py` once it exists.
- If salience caps cut your lines hard, quantify it (lines proposed vs born vs refused by which gate), and file the request in REQUESTS.md.

**L7 — Coverage.** Your ceiling: about 57% of golden lines are expressible below 4 p, and about 23% have no anchor pair below 8 p. Attack the expressible-but-missed part first:
- named-bar anchors from the book's own anchor vocabulary;
- a θ1 terminal anchor that needs no confirmation (L2: the last touch is wick-only 48% of the time);
- session extremes.

Use a ROUND_n.md per round, with measured deltas. Report the change in the v1 funnel oracle for PATTERN_LINE as well; EVAL-AUDIT has it at 0.40.

**L8 — Selection.** Use `age_min` in the birth score, since it is the only fold-stable feature.
- Report the AUC of the combined score on EVAL-AUDIT's funnel prefix labels (`evalcheck/labels_*`, and `cand_right`).
- Keep the honest flag: if nothing else passes, say so.

## Discipline
- Re-read `LEAD_RULINGS.md` and `linelab/LEAD_NOTE_*.md` at the start of every round, and log "rulings read up to R_n at HH:MMZ".
- Log every ≤ 45 min, with clock times.
- No deletes. `pa_slots` ≤ 1. TUNE only; HOLD never read. No commit or push.
- **Never end the session to ask; when the queue is done, continue L7/L8.**

## End
Final message in Vietnamese, 12 lines or fewer:
- full-engine PATTERN_LINE recall/precision/trusted/ink before and after;
- the effect on other types;
- test counts;
- the coverage and selection results;
- any salience requests.
