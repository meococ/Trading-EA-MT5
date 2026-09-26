# LANE EVAL-AUDIT — MANDATE 3 (Lead, 2026-09-21 18:03Z) — 4-hour box

**Accepted, per Lead Ruling 12.** Mandate 2 and the R11 ruler items are accepted.
- New ruler: `eval_v2` `50e11fd5`, `common` `c6b3fa0d`.
- Gates checked by the Lead.
- `verify()` returns `(True, None)` with a narrow pin.
- Cache 2.8×.
- Known-answer suite 7/7.
- Walls PASS.

**Two breaches (Ruling 12 §12.5). Do not repeat them:**
1. You deleted `labels_v1_504eb8ef53e5c492.jsonl`. No deletes, ever, including your own derived files. That engine state is gone, so the file cannot be rebuilt. Log this as a deviation in `EVAL_LOG.md`.
2. You wrote "~18:00Z" and "~18:05Z" entries into a file saved at 17:57Z. A log time is when something happened, taken from the clock. Correct those two lines with a note; do not erase them.

**Two R11 items are still open:**
- the tagged renders, the legend and the flat copies in `evalcheck/rv/`;
- the D33 UTC note.

Walls are unchanged from mandate 2:
- write only under `evalcheck/`, plus the one D33 note line;
- TUNE only; HOLD never read;
- engine read-only;
- `pa_slots` ≤ 1;
- log in `EVAL_LOG.md` at least every 45 min, with clock times;
- **never end the session to ask; when the queue is done, deepen Z2 and Z5.**

## Queue
**Z1 — BOX ceiling diagnosis** → `evalcheck/BOX_CEILING.md`. Do this first; the new BOX-LAB lane needs it.
- For v0 and the current v1, take every golden BOX with no right proposal under `cand_right()` and find the nearest candidate by edges. Report the distributions of:
  - the lo and hi edge errors, in pips and ABR;
  - the start error vs `build_start` (or `t0`);
  - the proposal time vs `build_end`.
- **Oracle sensitivity table:**
  - edge tol × {1, 1.5, 2};
  - start window {20, 40, 60 min, none};
  - with and without the proposal-time limit;
  - split by precision flag and by whether `build_start` is present or falls back to `t0`.
- **Classify every miss:**
  - no candidate within 2× tol anywhere in the panel;
  - edges right, start wrong;
  - edges right, too late;
  - one edge wrong (which one: the breakout edge or the other);
  - both edges wrong.
- Repeat the same diagnosis in brief for PATTERN_LINE (v1 oracle 0.40) and LEVEL_CARRIED.
- Output one headline: **is the BOX ceiling a generation problem or a rule-strictness problem?**

**Z2 — Snapshot fidelity diagnostic** → `evalcheck/snapshot.py`, `evalcheck/SNAPSHOT.md`. It changes no gate; the Lead and the Owner will use it in a gate-feasibility discussion.
- The golden set is a *retrospective teaching drawing*. The EA needs the *live* picture at the moments that matter.
- For each golden object, take its decision time τ:
  - BOX: `build_end` (the break bar);
  - PATTERN_LINE: its last touch before the break, else `t1`;
  - LEVEL: t0 + 10 min;
  - BRACKET: t1;
  - T/F: its mark time.
- Measure:
  - **snapshot recall**: is there a *live* engine object at τ, with its geometry *as of τ*, that matches it under the R11 rule applied to the state at τ?
  - **snapshot precision**: at each τ, the fraction of live signal-class engine objects that match some golden object alive at τ;
  - **live clutter**: the median live signal objects at τ.
- Report v0, v1, and the LINE-LAB and BOX-LAB prototypes when they exist (import them read-only).
- Compare with the cumulative-ink metrics. Explain in 5 lines what the difference means.

**Z3 — R11 leftovers:**
- tag every engine object in the renders with its type and short id, and add a legend;
- flat copies go to `evalcheck/rv/<hash8>_<panel>.png`, for v0 and the current v1;
- the D33 UTC note in `research/market/DEVIATIONS.md`, exactly as LEAD_NOTE_R11 item 6 says.

**Z4 — SCOREBOARD** → `evalcheck/scoreboard.py`, `evalcheck/SCOREBOARD.md`.
- One append-only row per run, never rewriting history, with:
  - UTC time from the clock;
  - engine name and hash, and ruler hash;
  - recall/precision per gated type;
  - `located`;
  - oracle BOX and LINE;
  - clutter;
  - snapshot recall.
- It must run in ≤ 2 min using the cache.
- Every lane (build, LINE-LAB, BOX-LAB) will call it after each change. Document the one-line command at the top of SCOREBOARD.md.
- Seed it with rows for v0 and the current v1.

**Z5 — Verify the builders' claims.** This is the ruler's job.
- When LINE-LAB integrates lines into the engine (new v1 hash), re-run the bridge and FUNNEL and confirm or refute its claimed deltas.
- When BOX-LAB reports an oracle ceiling or a born recall, re-run it independently with `funnel.py` and `eval_v2` from their prototype.
- Log each check in `evalcheck/VERIFY_LOG.md` as CONFIRMED or DISPUTED, with numbers.

## End
Final message in Vietnamese, 12 lines or fewer:
- the Z1 headline and the top miss class;
- snapshot vs cumulative numbers for v0 and v1;
- what landed;
- the Z5 checks.
