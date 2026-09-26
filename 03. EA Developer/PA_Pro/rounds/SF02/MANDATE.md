# LANE SF - SF02 MANDATE (Lead, 2026-09-21 04:31Z) - 12-hour autonomous box

You are the PA-PRO Setup Factory lane. SF01 is closed: 0/6 survivors, and every verdict was upheld by the Lead (`rounds/SF01/LEAD_RULINGS.md`, Review 3; read it first).

This is a LONG mandate. Work through the queue below without waiting for the Lead. Stop only when the 12-hour box ends or the whole queue, including Q4, is done. "All families done" is NOT a stop condition while queue items remain.

## Why SF02 exists
Two facts from SF01 drive everything here:
1. **The matched-random baseline itself loses.** In the thick cells, at S 11-32 pips, it shows PF 0.86-0.94 and -0.05 to -0.09 R per trade (costs plus intraday flats).
2. **Lift over random is about 0 in every thick cell.** The SF01 entries carry no directional information at M5.

The Lead's QA found two concrete defects:
- **Perception.** Up to 6 armed zones within +-2 x ATR(H1), roughly one zone every 10 pips, so "price is at a zone" is almost always true.
- **Entry location.** The F4-type trigger chases: the entry sits about 12 pips beyond the zone after a thrust bar.

So SF02 climbs blueprint §8 rung 2 (wider geometry and HTF context) and rung 3 (the exit axis), and fixes perception (salient zones, not every zone).

## Walls (hard; unchanged unless stated)
1. **DESIGN data only** (2016-2021, via `pa_sealed` split bounds). Never read CONFIRM-PRE, CONFIRM-VAL, OOS or HOLDOUT bars or outcomes.
2. **The referee (`lib/`) is read-only.**
   - Every SCREEN metric comes from `pa_eval` and is recorded in the ledger.
   - Autopsy metrics computed outside the referee must be labelled DESCRIPTIVE and must use DESIGN bars only.
3. **Pre-registration and revision budget.**
   - Hash every spec into the ledger BEFORE any outcome of that family exists.
   - At most 24 cells per family, and at most 2 post-outcome logic revisions per family.
   - A pre-outcome re-spec driven by census or visual QA is free (Lead Review 2). Keep census reports free of outcome fields so this stays provable.
4. **No rescuing a dead config with hour, day, year or symbol filters.**
5. **At most 2 `pa_slots` held by this lane at once.** The R02 re-executions and an R02-A1 audit job may hold the others. The total cap is 4.
6. **Forbidden actions:**
   - no MT5 trade tools and no terminal launches;
   - no deletes;
   - no git commit or push;
   - no book quotes longer than 15 words;
   - no writes to `02. AlphaFactory/lab/*` or `04. Memory/*`;
   - never touch `rounds/R02/` or `research/arrival/`.
7. **Every timestamp comes from the system clock** (`date -u` or `datetime.now(timezone.utc)`), never typed by hand.
8. **Never block waiting for the Lead.** Write `ASK_LEAD.md` only when you hit a wall, then keep working on the queue.
9. **Logs.**
   - Keep `rounds/SF02/FACTORY_LOG.md` (append-only), with a `## SUMMARY` block at the top that is current at every stage change.
   - Record decisions in `rounds/SF02/DECISIONS.md` (D1, D2, ...).
   - Re-read `rounds/SF02/LEAD_RULINGS.md` (the Lead will create it) at the start of every queue item.

## Queue (in order)

### Q0 - SF01 hygiene (30 min or less)
- **Re-run the F1 screen with the D9 tag fix.**
  - Append "D9-bis" to `rounds/SF01/DECISIONS.md`, with the new ledger trial ids.
  - Note the superseded F1 rows in the SF01 FACTORY_LOG.
  - PF, N and t must come out identical. If any of them changes, STOP this item and write ASK_LEAD, because tags must not change strategy trades.
- **Create `rounds/SF02/`** with `FACTORY_LOG.md` and `DECISIONS.md`.

### Q1 - AUTOPSY of SF01 (DESCRIPTIVE; about 3 hours of wall-clock or less)
**Plan first.**
- Write `rounds/SF02/AUTOPSY_PLAN.md` listing EVERY metric, slice and bin edge you will compute.
- Hash it into the ledger the same way as a spec pre-registration, BEFORE computing anything.
- Anything computed outside the plan must be labelled "unplanned" in the report.
- Use the SF01 signal sets exactly as screened: thick cells, corrected tags, the same matched randoms.

**A1 - Drag curve.**
- Compute exp_R, PF and the exit mix (SL/TP/DAILY/FRIDAY/MIDNIGHT) for matched-random entries through the referee.
- Grid: S in {11,14,18,24,32,40,55,75} pips x tp_mult in {1,1.5,2,3}, per symbol.
- Questions to answer:
  - Where does random drag fall below 0.03 R?
  - How much of TP reach do the intraday flats eat as S grows?

**A2 - Entry information, exit-free.**
- For each family's thick cells and their matched randoms, measure MFE and MAE in ATR(H1) units at horizons 6/12/24/48/96 M5 bars, capped at the day flat.
- Compute the edge ratio E[MFE]/E[MAE], strategy minus random, with day-clustered bootstrap CIs.
- This tells us whether ANY SF01 entry has directional information that the exits threw away.

**A3 - Perception audit.**
- Measure zone density per generator: armed zones within +-1 and +-2 ATR(H1).
- Measure the rank of the triggering zone by strength.
- Define a causal SALIENCE score in the plan, before looking. Suggested components:
  - touches respected with a reaction of at least 1 x ATR(H1);
  - H1/H4 pivot confluence;
  - ref-level confluence;
  - width;
  - age.
- Report lift and exp_R by salience tercile, per family.

**A4 - Context slices.** Declare them in the plan. NEVER use hour, day or year. Candidate slices:
- H1 and H4 trend alignment with the trade side;
- location in the prior-day or H4 range (discount / premium);
- ATR(H1) regime tercile;
- room to the next opposing armed zone, in R;
- entry distance from the zone edge in ATR(M5) (the "chase" metric).

Report every bin, with BH correction over the whole plan.

**Output: `rounds/SF02/AUTOPSY.md`.** It must contain:
- the tables and the total slice count;
- 4 or fewer ranked hypotheses. Each one needs a price-action mechanism, the supporting slices and a falsifiable family sketch;
- this sentence, verbatim: "DESIGN is now seen for these slices; DESIGN screens of these hypotheses are optimistic; promotion requires CONFIRM, opened once by the Lead."

### Q2 - SF02 families (the main work; 4 or fewer, as many as the box allows)
**Candidate directions.** The autopsy decides; for each family, record in DECISIONS which evidence picked it.

- **G1 - HTF-structure pullback.**
  - Uses H1 swing structure and trend.
  - Entry on an M5 or M15 signal bar AT a salient zone edge. No chase: the entry must be within k x ATR(M5) of the edge.
  - S at structure, on rungs suited to each symbol (for example 24-55 pips).
  - Entry gate: room to the opposing salient zone must be at least tp_mult x S.
- **G2 - Salient-zone rejection / trap.** F1/F3 logic restricted to the single most salient zone per side, using a declared salience threshold.
- **G3 - Volman build-up break with a proper box.**
  - Compression measured by percentile: the 12-bar range must be at or below its own rolling 10-20th percentile, AND the mean body must be at most 0.5 x ATR(M5).
  - The box must press against a salient zone, with the trend.
  - Entry by stop order beyond the box; inv at the far side of the box.
- **G4 - Exit-axis variant (rung 3)** of the best of G1-G3. Change only the S and tp_mult grid, never the entry logic.

**Pipeline for each family, in order:**
1. SPEC: mechanism, exact rules, grid of 24 cells or fewer, gates.
2. Ledger pre-registration.
3. Detector plus tests: prefix invariance, future mutation, warm-up.
4. 12 snapshots, plus a WRITTEN QA checklist that must include "not a chase", "box visibly tight", "zone is salient (at most 1 or 2 bands near price)" and "stop at real structure".
5. Census.
6. SCREEN: x1/x1.5/x2, matched random K=20.
7. ROUND_REPORT and verdict.

### Q3 - SURVIVOR protocol
If any cell passes ALL SCREEN gates:
- write `ASK_LEAD.md` with the heading "SURVIVOR <family/cell>" and the SCREEN row;
- continue the queue.

The Lead sends an independent reviewer and decides on CONFIRM. Never open CONFIRM data yourself.

### Q4 - Queue exhausted before the box ends
Write the plan in DECISIONS before acting, then do these as reports only:
- **Rung 5 prep.** Data availability and cost evidence for USDCAD, USDCHF and NZDUSD in the read-only cache.
- **Multi-day referee proposal,** only if A1 shows that intraday flats are the binding constraint. Write it as a proposal only; no code in `lib/`. It must cover swap, weekend gaps, and tests against ECON-1.

## End of the box
- The SUMMARY is current.
- `AUTOPSY.md` exists.
- Every family has a SPEC, a SCREEN and a ROUND_REPORT.
- Your final message is in Vietnamese, 25 lines or fewer: a table of families and verdicts, then the 3 most important findings, then open issues.
