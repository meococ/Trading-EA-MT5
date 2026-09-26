# LANE LEVEL-LAB — MANDATE (Lead, 2026-09-21 19:01Z) — 5-hour box, to about 00:05Z

You are LINE-LAB's session (sprout-duchess), continuing with a new object family. Your mandate 2 is accepted (Lead Ruling 15 §15.1). The lines work was honest and complete, including the L8 negative and your own attribution caveat. **You now take levels**, with the same lab method: audit → anatomy → prototype → integration note.

## Why levels, why now
- **LEVEL_CARRIED is a charter gate: recall ≥ 0.60.** On v1 `ef06f265` the figures are:
  - golden 48;
  - funnel oracle 0.50 (24);
  - born 0.15 (FUNNEL) / 0.125 (SCOREBOARD);
  - precision 0.027.

  Most of the gap is selection. Part of it is your own L5 side effect: `broken_line_edge` candidates now share `rate_level_carried` (§13.3).
- **MINI_LEVEL** is secondary: 31 golden, oracle 0.16.
- **Levels feed boxes.** BOX-LAB's anatomy found that about half of breakout edges were a level before the window (the "pre-existing barrier", §13.4). A good level registry is also an input to BOX-LAB.
- The build lane no longer owns this item (§15.2).

## Walls
- **Write only under `research/perception/levellab/`** (new folder). All engine files stay read-only until the Lead rules on integration:
  - `levels.py`, `lines.py`, `salience.py`, `engine.py`, `boxes.py`;
  - params, `eval.py`, `evalcheck/*`, golden.
- After the integration ruling you will own `levels.py` and the level params (str_replace only, with provenance), as you did for lines.
- **Tools you may run but never edit:** `evalcheck/funnel.py`, `scoreboard.py`, `snapshot.py` and `cache.py`. Their outputs land where the tools put them.
- Bars only via `book_loader` or `evalcheck/cache.py`. TUNE only. HOLD is never read.
- `pa_slots` ≤ 1, BelowNormal. **No deletes**, not even your own files. No commit or push.
- **Logging:**
  - log in `levellab/LEVEL_LOG.md` through `research/perception/tools/logline.py` (Ruling 14 §14.1), at least every 45 min;
  - ack rulings by number;
  - DECISIONS-style entries for any param or code proposal go in `levellab/INTEGRATION_LOG.md`.
- **Deltas** are paired A/B at one code state (§14.2).
- **Features** count only when measured on the **production proposal stream** (§15.1).
- **A failing test in a file you don't own:** log it and notify the owner. Do not debug it (§14.4).

## Queue
**V1 — Yardstick audit** (≤ 45 min) → `levellab/LEVEL_YARDSTICK_AUDIT.md`
- Cover the 48 LEVEL_CARRIED and 31 MINI_LEVEL golden objects. For each, record:
  - price, span and decision time τ;
  - the G-AUDIT repair provenance;
  - the book cue that defines the object, **paraphrased** (quotes ≤ 15 words).
- Explain how `eval_v2` matches a level (price tol, span rule), and whether the rule is fair. For example:
  - does a level born a few bars after the golden start still match?
  - is the pip tolerance sensible against ABR?
- Define a **trusted subset** (flag suspect labels, as Tier-A was for lines).
- A ruler issue goes into the doc as a proposal. The Lead rules, and EVAL-AUDIT implements.

**V2 — Anatomy** (≤ 60 min) → `LEVEL_ANATOMY.md`
- For every trusted golden level, measure **causally** (the origin must exist before the golden start):
  - **origin class:** prior box edge; prior swing extreme (θ1/θ2 pivot); session extreme (Asia H/L, EU/US open range); prior-day H/L; broken line edge; round number; other;
  - **age** at golden start;
  - **prior touches/defences;**
  - **distance from price at τ** (ABR);
  - **zone width;**
  - whether the author **carries** the same level across sub-panels;
  - the **draw moment**: when the level is first knowable, versus its golden start.
- Test the market lane's facts as *drawing* hypotheses. Does the author draw what matters for outcomes?
  - age < 3 h, and first touch (strong effects);
  - S1/S2;
  - Asia H/L;
  - PDH/PDL (unstable);
  - round numbers (no outcome effect; does the author still draw them?).

**V3 — Funnel and salience cut** (≤ 30 min) → `LEVEL_FUNNEL.md`
- Use the current funnel labels. For every right level proposal, record its outcome: born / rate_limited / expired / outranked / nms.
- For `rate_limited`, record which family spent the slots in that window: boxes, lines (`broken_line_edge`), or levels.
- If salience binds, file **REQ-L1** in `levellab/REQUESTS.md` with the measured basis and a variant menu. Cap raises need the same proof as §15.3: a feature that separates right from wrong on the production stream.

**V4 — Prototype** (≤ 2 h, ≤ 4 rounds) → `levellab/levels_lab.py` plus `ROUND_Ln.md` per round
- Build a causal level proposer and selector from V2:
  - only the origin classes the author actually uses;
  - freshness/age;
  - defence count;
  - distance to price.
- **Targets:**
  - LEVEL_CARRIED oracle ≥ 0.70;
  - born recall ≥ 0.35;
  - live levels per decision (snapshot lens) no higher than the current engine's.
- Report the trusted-subset numbers too, and the effect on MINI_LEVEL.

**V5 — Integration note** → `LEVEL_INTEGRATION.md`
- The exact change list for `levels.py` and the level params, plus any salience request, with the expected deltas.
- Then log. The Lead rules on integration.

**V6 — While waiting for the ruling:** MINI_LEVEL with the same method (prototype rounds).

**V7 — Barrier registry note for BOX-LAB** → `levellab/NOTES_FOR_BOXLAB.md`
- Which live levels at time t are credible pre-existing barriers for a box edge, and how to query them causally.
- BOX-LAB reads this note. You do not write in `boxlab/`.

## Discipline
- Re-read `LEAD_RULINGS.md` at the start of every round.
- **Never end the session to ask.** A blocked item is logged, and you take the next one. When V1–V7 are all done early, deepen V4 (more rounds) rather than stopping.
- Stop at about 23:50Z. Your last LEVEL_LOG entry is a one-screen status (§14.5):
  - what is measured, with hashes;
  - what is not measured yet;
  - the next step.

## End
Final message in Vietnamese, ≤ 12 lines:
- oracle and born numbers for LEVEL_CARRIED and MINI_LEVEL, before and after;
- the origin classes;
- the salience cut;
- the integration proposal.
