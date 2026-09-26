# LANE EVAL-AUDIT — MANDATE 2 (Lead, 2026-09-21 17:16Z) — 5-hour box

**EVAL_AUDIT.md is accepted** in Lead Ruling 10 (`research/perception/LEAD_RULINGS.md`). This was rigorous work, and the calibration discipline is exactly what the program needed.

`eval_v2` is now the **official ruler**. The frozen state:
- `eval_v2.py` `04c6f7bdff6459d5`;
- `common.py` `7eddcc85ebf45bb4`;
- `eval.py` `8d016922aecae265`;
- `golden/book_loader.py` `b40c2cab5c2ffe7d`.

You own the ruler. Any change to it goes through a Lead ruling, with E1 and E2 re-run and the new hashes logged.

Your new job: build the shared instruments that make every lane faster and harder to fool. **Order matters. Do not stop early, and do not end the session to ask whether to continue.**

## Walls (unchanged, plus two)
- Write only under `research/perception/evalcheck/`. The one exception is item 6 below.
- TUNE v2 only; bars only through `book_loader`. HOLD is never read. No DESIGN, CONFIRM, OOS or HOLDOUT data. No outcome imports.
- Engine files are read-only: import them and run them, never edit them.
- At most 1 `pa_slots` slot, BelowNormal. No commit, push or delete. Timestamps come from the clock, in UTC.
- **New:** never change the ruler's behaviour without a Lead ruling. Diagnostics and new report columns are fine.
- **New:** log progress in `evalcheck/EVAL_LOG.md` at least every 45 min.

## Queue
1. **FUNNEL** (highest value) → `evalcheck/funnel.py`, `evalcheck/FUNNEL.md`, `evalcheck/labels_<enginehash>.jsonl`.
   - For engine v0 and the current v1:
     - label every candidate in the engine's candidate log (`e.cand_log`, born or not) and every born object as matching golden id X, or none, under eval_v2 rules;
     - candidates carry no drawn span, so use their proposal-time window plus edges;
     - document exactly how each candidate record is converted.
   - Report per type:
     - **the oracle ceiling**: the recall if selection were perfect, meaning any matching candidate counts;
     - the born recall;
     - the gap between them.
   - Report a miss taxonomy for every golden object:
     - never proposed;
     - proposed with wrong geometry;
     - proposed right but not born, with the refusal reason if the engine logs one;
     - born right but a different episode (disjoint containment);
     - born right but closed early;
     - matched.
   - The labels file is what the build lane uses for AUC and separator work. Keep it keyed by engine hash, and re-run it when the hash changes. A cheap `--engine-hash-check` helps.
2. **BOX route diagnostic** (quick) → a section in FUNNEL.md.
   - For every BOX-family pair that passes the edge test, report the containment IoU and the overlap coefficient (intersection / shorter window), and classify it:
     - nested-same-episode: overlap coefficient ≥ 0.5;
     - partial;
     - disjoint: overlap 0.
   - Give counts for v0 and v1, and 5 rendered examples per class.
   - The Lead decides the final BOX rule in Ruling 11 from this table. Do not change `eval_v2` yet.
3. **Compare renders** → `evalcheck/render_compare.py`.
   - Draw one panel with golden v2 objects (solid) and engine objects (dashed, a different colour), each labelled matched / missed / false positive under eval_v2.
   - Use the look of `golden/qa/_render_v2.py`.
   - Render the 12 QA panels for v1 and v0: 9.1a, 9.13c, 9.23c, 9.33b, 9.45b, 9.54a, 9.63c, 9.29a, 9.29b, 9.38a, 9.39a, 9.41b.
   - Output to `evalcheck/renders/<enginehash>/`. The Lead reviews these visually.
4. **Cache** → `evalcheck/cache.py`: per-day bars and ABR, and engine outputs keyed by (engine hash, day, w1).
   - It must be bit-identical to a fresh run. Write a test for that.
   - Report the speed-up for a full 198-panel eval.
5. **Shared known-answer suite** → `evalcheck/kat/`.
   - Hand-built bar fixtures with known right answers, used for both engine and ruler:
     - a clean box with 3 touches per edge;
     - a lone spike poke, which must not become an edge;
     - a false break with close-back, which must yield T/F;
     - a proper break with buildup;
     - a 3-touch up-line;
     - an M bracket;
     - a carried level after a break.
   - Each fixture states the expected objects. The engine test reports pass or fail per fixture and does not gate. The ruler test must pass 100%.
   - One runner script.
6. **Data-wall and ledger self-check** → `evalcheck/walls_check.py`, run from any lane.
   - (a) No code under `research/perception/` or `research/market/` references HOLD file paths, except the sealed hash/ledger code.
   - (b) Perception code reads bars only via `book_loader` and never touches 2010–2015 bars outside the BOOK window.
   - (c) No outcome imports (`pa_fill`, `pa_eval`, `pa_random`, `arrival_outcome`, `phys_resolve`, `fwd_`) in perception code.
   - (d) Ledger lint: every line in `ledger/TRIALS.jsonl` is compact JSON + LF, and `pa_ledger.verify()` is run.
   - (e) **Authorised exception to your write wall, this item only:** in `lib/pa_ledger.py`, add a pinned exception to `verify()` for **edge 365 only**, per market Ruling 4 and REVIEW_3 N1.
     - Accept the stored prev `46a823b5…` iff it equals sha256(raw line 364 with `\r` stripped), and keep propagating the raw hash outbound.
     - Every other edge stays strict.
     - Tests:
       - the real file verifies `(True, None)`;
       - a copy with any other line altered, or a `\r` added anywhere else, fails;
       - the pinned edge with a different stored prev fails.
     - Log it in `evalcheck/EVAL_LOG.md` and as a row in `research/market/DEVIATIONS.md` (D35, "infra: pinned verify exception, Lead Ruling 4").
7. **Line-label sigma.** Coordinate with the LINE-LAB lane.
   - When `research/perception/linelab/LINE_YARDSTICK_AUDIT.md` reports the measured residual of repaired line labels, compare it with `common.prec_sigmas` (repaired lines = 1.5 p).
   - Write a proposal. Do not change anything; the Lead rules.

## End
Final message in Vietnamese, 12 lines or fewer:
- the oracle ceilings vs born recall per type for v0 and v1, and the top miss reasons;
- the BOX route classification;
- which tools landed, with the speed-up;
- the walls-check result.
